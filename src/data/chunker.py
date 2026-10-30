# -*- coding: utf-8 -*-
import re
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

class ChunkMethod(Enum):
    PARAGRAPH = "paragraph"
    ADAPTIVE_MERGE = "adaptive_merge"
    ARBITER_MERGE = "arbiter_merge"
    ARBITER_SPLIT = "arbiter_split"
    MODEL_LIMIT = "model_limit"
    TITLE_GLUE = "title_glue"  # 新增：标题强制粘合

@dataclass
class ChunkResult:
    content: str
    source: str = ""
    title: str = ""
    chunk_type: str = "content"
    start_pos: int = 0
    end_pos: int = 0
    method: str = "unknown"
    split_score: float = 1.0
    metadata: Dict = field(default_factory=dict)

class SmartChunker:
    
    SAFETY_TOKEN_LIMIT = 8000
    SAFETY_OVERLAP = 200          # 硬切时前后 chunk 的重叠字符数，保留上下文
    DEFAULT_BREAKPOINT_PERCENTILE = 15 
    DEFAULT_ARBITER_MARGIN = 0.1 
    MAX_ARBITER_WORKERS = 8

    PARAGRAPH_SEPARATORS = [
        r'\n\s*\n', r'\n#{1,6}\s+', r'\n第[一二三四五六七八九十\d]+[章节篇部]\s*', r'\n\d+[\.\、]\d*\s+'
    ]
    
    def __init__(self, embedding_client=None, llm_client=None,
                 breakpoint_percentile_threshold: int = None,
                 arbiter_margin: float = None,
                 merge_broken_paragraphs: bool = True, **kwargs):
        
        self.embedder = embedding_client
        self.llm = llm_client
        self.percentile_threshold = breakpoint_percentile_threshold or self.DEFAULT_BREAKPOINT_PERCENTILE
        self.arbiter_margin = arbiter_margin or self.DEFAULT_ARBITER_MARGIN
        self.merge_broken_paragraphs = merge_broken_paragraphs
        self.paragraph_patterns = [re.compile(p) for p in self.PARAGRAPH_SEPARATORS]
        self.sentence_end_pattern = re.compile(r'[。！？.!?…）\)」』"\']+\s*$')
        self.new_para_start_pattern = re.compile(r'^([#\d一二三四五六七八九十]|图|表|Abstract)')
        
        # 新增：标题特征正则（匹配 1.1, 第一章, # Title 等）
        self.title_pattern = re.compile(r'^\s*(?:第[一二三四五六七八九十\d]+[章节篇]|[\d\.]+\b|#+|[一二三四五六七八九十]+[、\.])')
        
        self._reset_stats()

    def _reset_stats(self):
        self.stats = {
            "total_chunks": 0, "auto_merges": 0, "arbiter_calls": 0, 
            "arbiter_merges": 0, "safety_splits": 0, "title_glues": 0, # 新增统计
            "dynamic_threshold": 0.0
        }
    
    def chunk(self, text: str, source: str = "", title: str = "",
              remove_frontmatter: bool = True, show_progress: bool = False) -> List[Dict]:
        self._reset_stats()
        text = text.strip()
        if not text: return []
        
        if self.merge_broken_paragraphs:
            text = self._merge_broken_lines(text)
        
        segments = self._split_by_structure(text)
        if len(segments) <= 1:
             return self._format_output([ChunkResult(text, start_pos=0, end_pos=len(text), method=ChunkMethod.PARAGRAPH.value)], source, title)

        chunks = self._hybrid_chunking(segments, show_progress)
        return self._format_output(chunks, source, title)

    # ==================== 核心逻辑 ====================
    
    def _hybrid_chunking(self, segments: List[Tuple[str, int]], show_progress: bool) -> List[ChunkResult]:
        texts = [s[0] for s in segments]
        
        # 1. 批量 Embedding
        try:
            embeddings = self.embedder.embed(texts, show_progress=show_progress)
            embeddings = np.array(embeddings)
        except Exception:
            return [ChunkResult(s[0], start_pos=s[1], method=ChunkMethod.PARAGRAPH.value) for s in segments]
        
        # 2. 向量计算相似度
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings = embeddings / (norms + 1e-9)
        similarities = np.sum(normalized_embeddings[:-1] * normalized_embeddings[1:], axis=1).tolist()
        
        # 3. 计算阈值
        dynamic_threshold = self._calculate_dynamic_threshold(similarities, False)
        upper_bound = dynamic_threshold + self.arbiter_margin
        lower_bound = dynamic_threshold - self.arbiter_margin
        self.stats["dynamic_threshold"] = dynamic_threshold

        # 4. 预扫描任务 (跳过标题粘合的部分，只扫描真正的模糊区)
        arbiter_tasks = [] 
        for i, sim in enumerate(similarities):
            # 如果当前段落是标题，之后会强制合并，不需要浪费 LLM 仲裁
            if self._is_potential_title(texts[i]):
                continue
                
            if lower_bound <= sim <= upper_bound and self.llm:
                text_a = texts[i]
                text_b = texts[i+1]
                arbiter_tasks.append((i, text_a, text_b))

        # 5. 并行仲裁
        arbiter_decisions = {}
        if arbiter_tasks:
            self.stats["arbiter_calls"] = len(arbiter_tasks)
            with ThreadPoolExecutor(max_workers=self.MAX_ARBITER_WORKERS) as executor:
                future_to_idx = {executor.submit(self._ask_arbiter, t[1], t[2]): t[0] for t in arbiter_tasks}
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        decision = future.result()
                        arbiter_decisions[idx] = decision
                        if decision: self.stats["arbiter_merges"] += 1
                    except Exception:
                        arbiter_decisions[idx] = False

        # 6. 快速组装 (引入标题粘合逻辑)
        merged_chunks = []
        current_text = segments[0][0]
        current_start = segments[0][1]
        current_method = ChunkMethod.PARAGRAPH.value  # 跟踪当前块是怎么形成的
        
        for i in range(len(similarities)):
            next_text = segments[i + 1][0]
            next_start = segments[i + 1][1]
            sim = similarities[i]
            
            should_merge = False
            decision_method = ChunkMethod.ADAPTIVE_MERGE.value
            
            # --- 规则优先级判断 ---
            
            # A. 物理安全检查 (最高优先级)
            is_physically_safe = (len(current_text) + len(next_text)) < self.SAFETY_TOKEN_LIMIT
            
            if not is_physically_safe:
                should_merge = False 
            else:
                # B. 小碎片强制粘合
                if len(current_text) < 500 and sim > 0.3:
                    should_merge = True
                    decision_method = ChunkMethod.ADAPTIVE_MERGE.value
                
                # C. 标题粘合检查 (Title Glue)
                elif self._is_potential_title(current_text):
                    should_merge = True
                    decision_method = ChunkMethod.TITLE_GLUE.value
                    self.stats["title_glues"] += 1
                
                # D. 查表决策 (LLM)
                elif i in arbiter_decisions:
                    if arbiter_decisions[i]:
                        should_merge = True
                        decision_method = ChunkMethod.ARBITER_MERGE.value
                    else:
                        should_merge = False
                        decision_method = ChunkMethod.ARBITER_SPLIT.value
                
                # E. 阈值判断
                else:
                    if sim > upper_bound:
                        should_merge = True
                        decision_method = ChunkMethod.ADAPTIVE_MERGE.value
                    else:
                        should_merge = False
                        decision_method = ChunkMethod.ADAPTIVE_MERGE.value

            if should_merge:
                current_text += "\n\n" + next_text
                current_method = decision_method
                if decision_method == ChunkMethod.ADAPTIVE_MERGE.value:
                    self.stats["auto_merges"] += 1
            else:
                # 切分：把 current 输出，记录的 method 是当前块的形成方式
                merged_chunks.append(ChunkResult(
                    content=current_text, start_pos=current_start, end_pos=current_start + len(current_text),
                    method=current_method, split_score=sim
                ))
                current_text = next_text
                current_start = next_start
                current_method = ChunkMethod.PARAGRAPH.value  # 新块初始为 paragraph
        
        # 最后一块
        merged_chunks.append(ChunkResult(
            content=current_text, start_pos=current_start, end_pos=current_start + len(current_text),
            method=current_method
        ))
        
        # 7. 安全兜底
        final_chunks = []
        for chunk in merged_chunks:
            if len(chunk.content) > self.SAFETY_TOKEN_LIMIT:
                self.stats["safety_splits"] += 1
                final_chunks.extend(self._force_safety_split(chunk.content, chunk.start_pos))
            else:
                final_chunks.append(chunk)
                
        self.stats["total_chunks"] = len(final_chunks)
        return final_chunks

    # ==================== 辅助方法 ====================

    def _is_potential_title(self, text: str) -> bool:
        """
        判断一段文本是否像是一个孤立的标题
        条件：
        1. 长度较短 (例如小于 100 字符)
        2. 符合标题正则 (以数字、#、章节开头)
        3. 或者不以标点符号结尾 (说明话没说完)
        """
        # 如果已经合并得很长了，肯定不是单纯的标题
        if len(text) > 100: 
            return False
            
        # 1. 强特征：正则匹配 (1.1, 第一章, # Title)
        if self.title_pattern.match(text):
            return True
            
        # 2. 弱特征：短文本且没有结尾标点 (例如 "农业发展概况")
        if len(text) < 50 and not text.strip()[-1] in '。！？.!?;；':
            return True
            
        return False

    def _format_output(self, chunks, source, title):
        return [{
            "content": c.content,
            "source": source,
            "metadata": {
                "title": title,
                "method": c.method,
                "token_count": len(c.content) 
            }
        } for c in chunks]

    def _ask_arbiter(self, text_a: str, text_b: str) -> bool:
        """
        LLM 裁判逻辑 - 贪婪合并版 (Greedy Merge)
        
        优化思路：
        将 Prompt 的倾向性从 "判断连贯性" 改为 "寻找切分理由"。
        默认倾向于 MERGE，只有当发现了明确的“章节切换”或“话题突变”时才 SPLIT。
        """
        
        # 截取长度稍微缩短一点，让模型更聚焦于接缝处
        snip_a = text_a[-300:].replace("\n", " ")
        snip_b = text_b[:300].replace("\n", " ")
        
        prompt = f"""任务：判断两段文本是否应该合并在一个Chunk中。

【判断标准】：
1. 我们需要构建尽可能长的语义块。
2. 即使两段话在讲不同的细分点（例如从“定义”讲到“作用”），只要属于同一个大主题，必须【MERGE】。
3. 忽略段落换行、列表序号带来的视觉分隔。
4. 只有在遇到以下情况时才回答 SPLIT：
   - 极其明显的话题突变（如：从“小麦种植”突然跳到“拖拉机维修”）。
   - 进入了全新的章节（如：出现“第二章”、“参考文献”等明显标志）。

---
上文片段：...{snip_a}
下文片段：{snip_b}...
---

请回答（MERGE 或 SPLIT）："""

        try: 
            # temperature=0.0 确保结果稳定
            response = self.llm.complete(prompt, max_tokens=5, temperature=0.0).strip().upper()
            
            # 只有明确说 SPLIT 才切分，其他情况（含模棱两可）一律合并
            if "SPLIT" in response:
                return False
            return True # 默认为 MERGE
            
        except Exception as e: 
            # 如果 LLM 调用失败（如网络超时），为了保证信息不碎片化，默认采取合并策略
            # (之前的逻辑是报错就切分，导致碎片，现在改为报错就合并)
            return True
    
    def _calculate_dynamic_threshold(self, similarities, show):
        if not similarities: return 0.5
        return float(np.clip(np.percentile(similarities, self.percentile_threshold), 0.4, 0.8))

    def diagnose(self, text: str):
        # 诊断时也使用并行逻辑，但为了展示细节，这里直接复用 _hybrid_chunking 的逻辑会比较复杂
        # 诊断功能保持原样即可，不影响生产速度
        pass 

    def _split_by_structure(self, text):
        split_points = set([0, len(text)])
        for p in self.paragraph_patterns:
            for m in p.finditer(text): split_points.add(m.start())
        points = sorted(split_points)
        return [(text[p1:p2].strip(), p1) for p1, p2 in zip(points, points[1:]) if text[p1:p2].strip()]

    def _merge_broken_lines(self, text): 
        lines = text.split('\n')
        merged = []
        curr = ""
        for line in lines:
            line = line.strip()
            if not line:
                if curr: merged.append(curr)
                merged.append("")
                curr = ""
                continue
            if curr and not self.sentence_end_pattern.search(curr) and \
               not self.new_para_start_pattern.match(line):
               curr += " " + line   # 修复：添加空格防止文字粘连
            else:
               if curr: merged.append(curr)
               curr = line
        if curr: merged.append(curr)
        return '\n'.join(merged)

    def _force_safety_split(self, text, start): 
        """
        三级安全切分策略：
          Level 1: 按段落边界切（\n\n）—— 语义损失最小
          Level 2: 按句子边界切（。！？.!?）—— 保证句子完整
          Level 3: 按字符硬切 + overlap —— 最后兜底
        """
        limit = self.SAFETY_TOKEN_LIMIT
        
        # 如果文本未超限，直接返回（防御性检查）
        if len(text) <= limit:
            return [ChunkResult(text, start_pos=start, method=ChunkMethod.MODEL_LIMIT.value)]
        
        # ========== Level 1: 按段落边界切分 ==========
        paragraphs = re.split(r'\n\s*\n', text)
        
        # 如果切出的段落都不超限，贪心合并
        if all(len(p) <= limit for p in paragraphs):
            return self._greedy_merge_segments(paragraphs, limit, start, sep="\n\n")
        
        # ========== Level 2: 段落内按句子边界切分 ==========
        # 先把超长段落拆成句子，再统一合并
        all_sentences = []
        for para in paragraphs:
            if len(para) <= limit:
                # 整段不超限，作为一个整体保留（避免不必要的句子拆分）
                all_sentences.append(para)
            else:
                # 超长段落 → 按句末标点切分
                # 匹配中英文句末标点，切分后保留标点在前一段
                sents = re.split(r'(?<=[。！？.!?…])\s*', para)
                sents = [s for s in sents if s.strip()]
                
                if all(len(s) <= limit for s in sents):
                    all_sentences.extend(sents)
                else:
                    # ========== Level 3: 单个句子仍超限 → 硬切 + overlap ==========
                    for sent in sents:
                        if len(sent) <= limit:
                            all_sentences.append(sent)
                        else:
                            all_sentences.extend(self._hard_split_with_overlap(sent, limit))
        
        return self._greedy_merge_segments(all_sentences, limit, start, sep="\n")
    
    def _greedy_merge_segments(self, segments: List[str], limit: int, 
                                base_start: int, sep: str = "\n\n") -> List[ChunkResult]:
        """
        贪心合并：将小段落/句子尽可能塞进一个 chunk，直到接近 limit
        """
        chunks = []
        current = ""
        current_start = base_start
        
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            
            # 计算合并后的长度
            candidate = (current + sep + seg) if current else seg
            
            if len(candidate) <= limit:
                current = candidate
            else:
                # 当前 chunk 已满，保存并开始新 chunk
                if current:
                    chunks.append(ChunkResult(
                        content=current,
                        start_pos=current_start,
                        end_pos=current_start + len(current),
                        method=ChunkMethod.MODEL_LIMIT.value
                    ))
                    current_start += len(current)
                current = seg
        
        # 别忘了最后一段
        if current:
            chunks.append(ChunkResult(
                content=current,
                start_pos=current_start,
                end_pos=current_start + len(current),
                method=ChunkMethod.MODEL_LIMIT.value
            ))
        
        return chunks
    
    def _hard_split_with_overlap(self, text: str, limit: int) -> List[str]:
        """
        最后手段：按字符数硬切，相邻 chunk 之间保留 overlap 上下文
        确保不会因为硬切丢失语义衔接
        """
        overlap = self.SAFETY_OVERLAP
        step = limit - overlap  # 每步前进的有效字符数
        
        if step <= 0:
            step = limit  # 防御：overlap 不应超过 limit
        
        pieces = []
        pos = 0
        while pos < len(text):
            end = min(pos + limit, len(text))
            pieces.append(text[pos:end])
            
            if end >= len(text):
                break
            pos += step  # 下一块从 overlap 区域开始
        
        return pieces
