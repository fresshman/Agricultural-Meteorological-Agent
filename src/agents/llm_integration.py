# -*- coding: utf-8 -*-
"""
大语言模型集成和RAG问答
"""
from typing import List, Dict, Optional, Tuple
from src.models import UserType
from src.utils.clients import LLMClient as RealLLMClient, EmbeddingClient
from src.data import VectorDatabase, SmartChunker, TextCleaner
from config.settings import settings, USER_TYPES


class LLMClient(RealLLMClient):
    """大语言模型客户端（继承自实际实现，复用父类真异步 / 流式接口）"""
    pass


class RAGEngine:
    """RAG检索增强生成引擎"""

    def __init__(
        self,
        llm_client: LLMClient,
        vector_db_path: str = None,
        embedding_model: str = None
    ):
        self.llm = llm_client
        self.vector_db_path = vector_db_path or settings.VECTOR_DB_PATH
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL

        try:
            self.embedder = EmbeddingClient(self.embedding_model)
            self.vector_db = VectorDatabase(
                embedding_client=self.embedder,
                db_path=self.vector_db_path
            )
            # 修复RAG空转：若向量库为空（首次部署/无索引），自动从 docs 目录建库
            self._auto_build_if_empty()
        except Exception as e:
            print(f"警告: 向量数据库初始化失败: {e}")
            self.embedder = None
            self.vector_db = None

    def _auto_build_if_empty(self):
        """向量库为空且存在知识文档时，自动构建索引，保证检索可用"""
        try:
            stats = self.vector_db.get_statistics()
            if stats.get("total_documents", 0) > 0 and stats.get("faiss_vectors", 0) > 0:
                print(f"  已加载知识库: {stats['total_documents']} 文档, "
                      f"{stats['faiss_vectors']} 向量")
                return

            print("  检测到向量库为空，尝试自动构建知识库...")
            from src.data.kb_builder import build_knowledge_base
            build_knowledge_base(self.vector_db, embedder=self.embedder, verbose=True)
        except Exception as e:
            print(f"  自动建库失败（不影响主流程，可运行 python -m src.data.kb_builder 手动构建）: {e}")

    
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, any]]:
        """
        检索知识库
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            检索结果列表
        """
        if not self.vector_db:
            return []
        
        try:
            results = self.vector_db.search_hybrid(query, top_k=top_k)
            return [
                {
                    "content": doc.content,
                    "source": doc.source,
                    "score": score,
                    "keywords": doc.keywords
                }
                for doc, score in results
            ]
        except Exception as e:
            print(f"检索失败: {e}")
            return []
    
    async def generate_answer(
        self,
        query: str,
        context: str,
        user_type: UserType = UserType.FARMER
    ) -> str:
        """
        生成回答
        
        Args:
            query: 用户问题
            context: 上下文信息
            user_type: 用户类型
        
        Returns:
            生成的回答
        """
        user_config = USER_TYPES.get(user_type.value, USER_TYPES["普通农户"])
        output_style = user_config["输出风格"]
        detail_level = user_config["详细程度"]
        
        system_prompt = f"""你是一个专业的农业气象智能助手，负责为农户提供精准、可落地的农事决策建议。

核心原则：
1. 准确性优先：所有建议必须有明确的气象依据和农业标准依据
2. 语言接地气：使用农户口语化表达，避免专业晦涩术语
3. 可执行性强：建议必须具体可操作，明确时间、用量、方式
4. 容错兜底：标注风险等级和适用范围，不输出绝对化结论

输出风格：{output_style}
详细程度：{detail_level}

禁止事项：
- 杜绝虚假、模糊、专业晦涩的输出内容
- 不输出绝对化结论（如"一定会"、"绝对安全"等）
- 不提供无依据的建议

请基于提供的上下文信息回答用户问题，确保回答通俗、可落地、有依据。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"上下文信息：\n{context}\n\n用户问题：{query}"}
        ]
        
        return await self.llm.chat_async(messages, temperature=0.3)
    
    async def chat(
        self,
        query: str,
        history: List[Dict[str, str]] = None,
        user_type: UserType = UserType.FARMER,
        top_k: int = 5
    ) -> Tuple[str, List[Dict]]:
        """
        RAG问答主流程
        
        Args:
            query: 用户问题
            history: 对话历史
            user_type: 用户类型
            top_k: 检索结果数量
        
        Returns:
            (回答, 参考来源)
        """
        search_results = await self.search(query, top_k=top_k)
        
        context = "\n\n".join([
            f"【资料{i+1}】\n{result['content']}"
            for i, result in enumerate(search_results)
        ])
        
        answer = await self.generate_answer(query, context, user_type)
        
        return answer, search_results


class PromptBuilder:
    """提示词构建器"""
    
    @staticmethod
    def build_system_prompt(user_type: UserType) -> str:
        """
        构建系统提示词
        
        Args:
            user_type: 用户类型
        
        Returns:
            系统提示词
        """
        user_config = USER_TYPES.get(user_type.value, USER_TYPES["普通农户"])
        
        base_prompt = """你是农业气象智能体，专注于为农户提供精准、可落地的农事决策辅助服务。

核心身份：
- 气象数据驱动 + 农业知识赋能
- 服务对象：普通种植户、农业合作社、基层农技推广人员
- 覆盖全生育期：播种、田间管理、病虫害防控、防灾减灾、收获仓储

核心能力：
1. 精准农事日历与播种决策
2. 田间管理气象指导（灌溉、施肥、植保）
3. 灾害风险预警与应对
4. 收获与仓储气象指导
5. 交互式问答与个性化农技咨询

输出规范：
- 所有建议必须附带明确气象依据、农业标准依据
- 使用农户口语化表达，具体可执行
- 标注风险等级与适用范围，不输出绝对化结论
- 区分用户类型，差异化输出内容深度

工具调用规则：
- weather_query: 查询气象数据
- crop_growth_calculator: 计算作物生长状态
- farm_operation_judge: 判定农事操作适宜度
- disaster_risk_assess: 评估灾害风险
- knowledge_retrieval: 检索农业知识

用户类型：{user_type}
输出风格：{output_style}
详细程度：{detail_level}
关注点：{focus_points}"""
        
        return base_prompt.format(
            user_type=user_type.value,
            output_style=user_config["输出风格"],
            detail_level=user_config["详细程度"],
            focus_points="、".join(user_config["关注点"])
        )
    
    @staticmethod
    def build_intent_recognition_prompt(query: str) -> str:
        """
        构建意图识别提示词
        
        Args:
            query: 用户问题
        
        Returns:
            意图识别提示词
        """
        return f"""请分析用户问题的意图，提取关键信息。

用户问题："{query}"

请识别以下信息（JSON格式）：
{{
    "intent": "意图类型（播种/灌溉/施肥/植保/收获/病虫害/灾害/其他）",
    "crop_type": "作物类型（如果提到）",
    "growth_stage": "生长阶段（如果提到）",
    "location": "地理位置（如果提到）",
    "time": "时间信息（如果提到）",
    "operation": "操作类型（如果提到）",
    "urgency": "紧急程度（高/中/低）"
}}

只输出JSON，不要有其他内容。"""
    
    @staticmethod
    def build_response_prompt(
        structured_result: str,
        weather_data: str,
        user_query: str,
        user_type: UserType
    ) -> str:
        """
        构建回复生成提示词
        
        Args:
            structured_result: 结构化结果
            weather_data: 气象数据
            user_query: 用户问题
            user_type: 用户类型
        
        Returns:
            回复生成提示词
        """
        user_config = USER_TYPES.get(user_type.value, USER_TYPES["普通农户"])
        
        if user_type == UserType.FARMER:
            output_template = """
【通俗化操作指导】

用户问题：{query}

气象情况：{weather}

专业建议：
{result}

操作要点：
1. 具体操作步骤（时间、用量、方式）
2. 注意事项和风险提示
3. 简明易懂的决策依据

💡 小贴士：实用建议，一看就懂，一学就会！
"""
        elif user_type == UserType.LARGE_FARMER:
            output_template = """
【规模化生产方案】

用户问题：{query}

气象数据：{weather}

专业分析：
{result}

生产方案：
1. 操作时机与窗口期
2. 规模化作业组织建议
3. 成本效益分析
4. 风险管控措施
5. 应急预案

📊 数据支撑：气象依据、成本核算、风险评估
"""
        else:  # 农技人员
            output_template = """
【专业技术报告】

用户问题：{query}

气象数据详情：
{weather}

专业分析结果：
{result}

技术要点：
1. 数据依据：气象参数、阈值标准
2. 模型依据：计算方法、参数来源
3. 技术参数：具体数值、单位、精度
4. 适用范围与限制条件
5. 参考标准与文献

📋 技术参数表、模型公式、标准引用
"""
        
        return output_template.format(
            query=user_query,
            weather=weather_data,
            result=structured_result
        )

