# -*- coding: utf-8 -*-
"""
客户端模块 - LLM和Embedding
从hybrid-rag集成

修复点：
1. chat_async / complete_async 由"假异步(同步阻塞)"改为真异步（asyncio.to_thread），不再阻塞事件循环
2. 新增 chat_stream / complete_stream / astream_chat 流式接口，支持真流式 SSE
3. 修复 MODELS 中 qwen3-next / qwen3-32b 的 model 为空字符串的配置错误
4. 修复 bge-small-zh-v1.5 用 large 顶替、维度错误的配置；维度修正为 512
5. EmbeddingClient 增加模型加载缓存，避免多次重复下载/加载
"""

import os
import asyncio
import threading
import numpy as np
from typing import List, Dict, Iterator, AsyncIterator
from openai import OpenAI
import torch


class LLMClient:
    """
    LLM客户端

    支持多种模型配置：
    - 阿里云百炼(DashScope)
    - OpenAI兼容接口
    - DeepSeek
    """

    MODELS = {
        "qwen-flash": {
            "base_url": "",
            "model": "qwen-flash",
            "env_key": "DASHSCOPE_API_KEY",
            "description": "极速、超低成本"
        },
        "qwen-plus": {
            "base_url": "",
            "model": "qwen-plus",
            "env_key": "DASHSCOPE_API_KEY",
            "description": "平衡性能"
        },
        "qwen-max": {
            "base_url": "",
            "model": "qwen-max",
            "env_key": "DASHSCOPE_API_KEY",
            "description": "最强性能"
        },
        "deepseek-v3.2-exp": {
            "base_url": "",
            "model": "deepseek-v3.2-exp",
            "env_key": "DASHSCOPE_API_KEY",
            "description": "DeepSeek对话"
        },
        "qwen3-next": {
            "base_url": "https://api-inference.modelscope.cn/v1",
            "model": "Qwen/Qwen3-30B-A3B-Instruct-2507",
            "env_key": "LLM_API_KEY",
            "description": "开源优越"
        },
        "qwen3-32b": {
            "base_url": "https://api-inference.modelscope.cn/v1",
            "model": "Qwen/Qwen3-32B",
            "env_key": "LLM_API_KEY",
            "description": "开源高效"
        }
    }

    def __init__(self, model: str = "qwen3-next", api_key: str = None, base_url: str = None):
        if model in self.MODELS:
            preset = self.MODELS[model]
            self.model = preset["model"]
            self.base_url = base_url or preset["base_url"]
            env_key = preset.get("env_key", "DASHSCOPE_API_KEY")
            self.api_key = api_key or os.getenv(env_key, "")
            self.description = preset["description"]
        else:
            self.model = model
            # 自定义模型：base_url 依次取 显式参数 → LLM_API_URL 环境变量；
            # 若仍未配置则置空（不发请求），避免误连 OpenAI 默认地址导致密钥外泄/请求失败
            self.base_url = base_url or os.getenv("LLM_API_URL", "") or ""
            # 自定义模型优先取 LLM_API_KEY（项目主密钥），兼容 DASHSCOPE_API_KEY
            self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
            self.description = "自定义模型"

        if not self.api_key:
            print(f"警告: 未设置API密钥，LLM功能将不可用")
            self.client = None
        elif not self.base_url:
            print(f"警告: 自定义模型 '{self.model}' 未配置 base_url（请设置 LLM_API_URL），LLM功能将不可用")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, messages: List[Dict], max_tokens: int = 4096, temperature: float = 0.7) -> str:
        """发送聊天请求（同步）"""
        if not self.client:
            raise RuntimeError("LLM客户端未初始化（缺少API密钥）")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    def complete(self, prompt: str, **kwargs) -> str:
        """简单补全（同步）"""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    async def chat_async(self, messages: List[Dict], max_tokens: int = 4096, temperature: float = 0.7) -> str:
        """异步聊天（真异步：在线程池中执行，不阻塞事件循环）"""
        return await asyncio.to_thread(self.chat, messages, max_tokens, temperature)

    async def complete_async(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """异步补全（真异步）"""
        return await asyncio.to_thread(
            self.chat, [{"role": "user", "content": prompt}], max_tokens, temperature
        )

    def chat_stream(self, messages: List[Dict], max_tokens: int = 4096, temperature: float = 0.7) -> Iterator[str]:
        """流式聊天（同步生成器），逐增量产出文本片段"""
        if not self.client:
            raise RuntimeError("LLM客户端未初始化（缺少API密钥）")

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def complete_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """流式补全（同步生成器）"""
        yield from self.chat_stream([{"role": "user", "content": prompt}], **kwargs)

    async def astream_chat(self, messages: List[Dict], max_tokens: int = 4096, temperature: float = 0.7) -> AsyncIterator[str]:
        """
        异步流式聊天：
        在独立守护线程中迭代同步生成器，通过 asyncio.Queue 回传主事件循环。
        避免阻塞事件循环，同时支持真流式。
        """
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                for text in self.chat_stream(messages, max_tokens, temperature):
                    queue.put_nowait(("token", text))
                queue.put_nowait(("end", None))
            except Exception as e:  # noqa: BLE001
                queue.put_nowait(("error", str(e)))

        threading.Thread(target=_run, daemon=True).start()

        while True:
            kind, payload = await queue.get()
            if kind == "token":
                yield payload
            elif kind == "error":
                raise RuntimeError(payload)
            else:
                return

    def __repr__(self):
        return f"LLMClient(model={self.model}, {self.description})"


# 模型加载缓存：同一模型只下载/加载一次
_embedder_cache = {}


class EmbeddingClient:
    """
    Embedding客户端

    特性:
    - 支持 FP16 半精度加速
    - 支持 Instruction (指令前缀)
    - 自动 GPU/CPU 检测
    - 模块级缓存，避免重复下载/加载
    """

    MODELS = {
        "Qwen3-Embedding": {
            "name": "Qwen/Qwen3-Embedding-8B",
            "modelscope_name": "Qwen/Qwen3-Embedding-8B",
            "dimension": 4096,
            "description": "Qwen3-Embedding-8B 双语嵌入",
            "query_instruction": "Represent this query for retrieving relevant documents: ",
            "doc_instruction": ""
        },
        "bge-m3": {
            "name": "BAAI/bge-m3",
            "modelscope_name": "BAAI/bge-m3",
            "dimension": 1024,
            "description": "BGE-M3 多语言（100+语言）",
            "query_instruction": "",
            "doc_instruction": ""
        },
        "bge-large-zh-v1.5": {
            "name": "BAAI/bge-large-zh-v1.5",
            "modelscope_name": "BAAI/bge-large-zh-v1.5",
            "dimension": 1024,
            "description": "BGE 中文专用",
            "query_instruction": "为这个句子生成表示以用于检索相关文章：",
            "doc_instruction": ""
        },
        "bge-small-zh-v1.5": {
            "name": "BAAI/bge-small-zh-v1.5",
            "modelscope_name": "BAAI/bge-small-zh-v1.5",
            "dimension": 512,
            "description": "BGE 中文 small（512维）",
            "query_instruction": "为这个句子生成表示以用于检索相关文章：",
            "doc_instruction": ""
        }
    }

    def __init__(self, model: str = "Qwen3-Embedding", use_fp16: bool = True):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.use_fp16 = use_fp16 and (self.device == "cuda")

        if model in self.MODELS:
            info = self.MODELS[model]
            self.model_name = info["name"]
            self.modelscope_name = info.get("modelscope_name", info["name"])
            self._dimension = info["dimension"]
            self.description = info["description"]
            self.default_query_instruction = info.get("query_instruction", "")
            self.default_doc_instruction = info.get("doc_instruction", "")
        else:
            self.model_name = model
            self.modelscope_name = model
            self._dimension = None
            self.description = "自定义模型"
            self.default_query_instruction = ""
            self.default_doc_instruction = ""

        print(f"Loading Embedding Model: {self.model_name} on {self.device} (FP16={self.use_fp16})...")

        # 命中缓存则直接复用，避免重复下载/加载（创空间冷启动关键）
        if self.model_name in _embedder_cache:
            self.model = _embedder_cache[self.model_name]
            if self._dimension is None:
                self._dimension = self.model.get_sentence_embedding_dimension()
            print(f"✅ 复用已加载的 Embedding 模型缓存: {self.model_name}")
        else:
            self._load_model()

    def _load_model(self):
        """加载模型（首次）"""
        try:
            # 优先使用ModelScope加载
            try:
                from modelscope import snapshot_download
                print(f"尝试从ModelScope下载模型: {self.modelscope_name}")
                model_path = snapshot_download(self.modelscope_name)
                print(f"模型下载成功: {model_path}")

                print(f"正在加载SentenceTransformer模型...")
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_path, trust_remote_code=True, device=self.device)
                print(f"SentenceTransformer模型加载成功")
            except Exception as e:
                print(f"ModelScope加载失败: {e}")
                print(f"警告: 创空间环境无法从HuggingFace下载模型，Embedding功能将不可用")
                raise RuntimeError(f"Embedding模型加载失败: {e}")

            if self.use_fp16:
                self.model.half()

            if self._dimension is None:
                self._dimension = self.model.get_sentence_embedding_dimension()

            # 写入缓存
            _embedder_cache[self.model_name] = self.model

            print(f"Embedding模型初始化完成，维度: {self._dimension}")

        except Exception as e:
            raise RuntimeError(f"Embedding模型加载失败: {e}")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts, batch_size: int = None,
              show_progress: bool = True,
              normalize: bool = True,
              max_length: int = 512,
              instruction: str = "") -> np.ndarray:
        """生成文本向量"""
        if isinstance(texts, str):
            texts = [texts]

        if instruction:
            texts = [f"{instruction}{t}" for t in texts]

        texts = [t[:max_length] if len(t) > max_length else t for t in texts]

        if batch_size is None:
            if self.device == "cpu":
                batch_size = 16
            elif self._dimension >= 4096:
                batch_size = 4 if not self.use_fp16 else 16
            elif self._dimension >= 1024:
                batch_size = 16 if not self.use_fp16 else 64
            else:
                batch_size = 64

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress and len(texts) > 10,
                normalize_embeddings=normalize,
                convert_to_numpy=True
            )
            return np.array(embeddings, dtype=np.float32)

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print(f"  ⚠️ GPU显存不足，自动降级为逐条处理...")
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                embeddings = self.model.encode(
                    texts,
                    batch_size=1,
                    show_progress_bar=show_progress,
                    normalize_embeddings=normalize,
                    convert_to_numpy=True
                )
                return np.array(embeddings, dtype=np.float32)
            raise

    def embed_query(self, text: str) -> np.ndarray:
        """专门用于查询的 Embedding (自动带指令)"""
        return self.embed([text], show_progress=False, instruction=self.default_query_instruction)[0]

    def embed_documents(self, texts: List[str], **kwargs) -> np.ndarray:
        """专门用于文档入库的 Embedding"""
        return self.embed(texts, instruction=self.default_doc_instruction, **kwargs)

    def similarity(self, text1: str, text2: str) -> float:
        """计算相似度"""
        emb1 = self.embed([text1], show_progress=False)[0]
        emb2 = self.embed([text2], show_progress=False)[0]
        return float(np.dot(emb1, emb2))


def get_llm(model: str = "qwen3-next") -> LLMClient:
    """获取LLM客户端"""
    return LLMClient(model)


def get_embedder(model: str = "bge-m3") -> EmbeddingClient:
    """获取Embedding客户端"""
    return EmbeddingClient(model)
