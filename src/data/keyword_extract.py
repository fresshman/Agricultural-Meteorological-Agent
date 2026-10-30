# -*- coding: utf-8 -*-
"""
关键词提取模块 (v2 - 两阶段策略)

核心思想：
  阶段1 (文档级): 在整篇文档上用 TF-IDF 建立高质量候选关键词池
  阶段2 (Chunk级): 对每个 chunk，用 KeyBERT 思想（语义相似度）从候选池中筛选关键词

优势：
  - 文档级统计基础大，TF-IDF 更稳定
  - chunk 级语义匹配保证关键词与内容的相关性
  - 中文分词：jieba + 自动发现专业术语（基于 PMI 互信息）
"""

import re
import os
from typing import List, Tuple, Set, Dict, Optional
from collections import Counter
import numpy as np
import math

# ==================== Jieba 初始化与权限修复 ====================
try:
    import jieba
    import jieba.analyse

    # 权限修复逻辑
    _CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    _CACHE_PATH = os.path.join(_CURRENT_DIR, "jieba.cache")
    jieba.dt.cache_file = _CACHE_PATH

    import logging
    jieba.setLogLevel(logging.ERROR)

    try:
        jieba.initialize()
        HAS_JIEBA = True
    except Exception as e:
        print(f"⚠️  警告: jieba 缓存写入失败 ({e})，切换为无缓存模式。")
        HAS_JIEBA = True

except ImportError:
    HAS_JIEBA = False
    print("⚠️  警告: 未找到 jieba 库。")


class KeywordExtractor:
    """
    两阶段关键词提取器
    
    使用流程：
      1. extractor = KeywordExtractor(embedding_client=embedder)
      2. doc_profile = extractor.build_doc_profile(full_text)    # 文档级
      3. keywords = extractor.extract(chunk_text, doc_profile=doc_profile)  # Chunk级
    """

    # ==================== 停用词 ====================
    STOPWORDS_CN = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '都',
        '一', '上', '也', '很', '到', '说', '要', '人', '这', '那',
        '你', '他', '她', '它', '们', '个', '为', '与', '或', '及',
        '等', '能', '会', '可', '年', '月', '日', '时', '分', '秒',
        '中', '对', '把', '被', '让', '给', '向', '从', '自', '但',
        '而', '如', '若', '虽', '因', '所', '以', '于', '其', '之',
        '则', '且', '即', '乃', '故', '亦', '既', '已', '曾', '将',
        '才', '又', '再', '更', '还', '最', '越', '非', '无', '没',
        '进行', '主要', '使用', '可以', '这个', '那个', '因为', '所以',
        '问题', '研究', '分析', '结果', '表明', '方法', '通过', '我们',
        '以及', '对于', '关于', '根据', '目录', '章节', '页码', '部分',
        '内容', '小结', '复习题', '思考题', '概述', '简介', '封面',
        '印张', '印数', '字数', '版次', '书号', '定价', '责任', '编辑',
        '具有', '需要', '这种', '那种', '一些', '一般', '一定', '大量',
        '采用', '认为', '提出', '存在', '发展', '作为', '相关', '不同',
        '其中', '如果', '只有', '由于', '然而', '此外', '同时', '为了',
    }

    STOPWORDS_EN = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'shall',
        'can', 'need', 'dare', 'to', 'of', 'in', 'for', 'on', 'with',
        'at', 'by', 'from', 'as', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'under', 'again', 'further',
        'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
        'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 'just', 'and', 'but', 'if', 'or', 'because', 'until',
        'while', 'although', 'though', 'this', 'that', 'these', 'those',
        'what', 'which', 'who', 'whom', 'whose', 'it', 'its', 'they',
        'them', 'their', 'we', 'us', 'our', 'you', 'your', 'he', 'him',
        'his', 'she', 'her', 'about', 'over', 'also', 'any', 'many',
        'chapter', 'section', 'part', 'page', 'fig', 'figure', 'table',
    }

    STOPWORDS_TECH = {
        'mathrm', 'mathbf', 'mathcal', 'mathit', 'text', 'textit', 'textbf',
        'sim', 'approx', 'times', 'cdot', 'frac', 'sum', 'prod',
        'alpha', 'beta', 'gamma', 'delta', 'theta', 'lambda', 'sigma', 'omega',
        'http', 'https', 'ftp', 'www', 'com', 'cn', 'org', 'net', 'edu', 'gov',
        'html', 'htm', 'php', 'jsp', 'asp',
        'pdf', 'jpg', 'png', 'jpeg', 'gif', 'svg', 'doc', 'docx', 'xls', 'xlsx',
        'openxlab', 'mineru', 'internlm', 'cdn', 'github', 'oss', 'api',
        'result', 'return', 'true', 'false', 'none', 'null', 'undefined',
        'import', 'export', 'class', 'def', 'function', 'var', 'let', 'const',
        'doi', 'issn', 'isbn', 'pp', 'eds', 'editor', 'press', 'university',
        'cip', 'nucleic', 'acids',
    }

    STATIC_STOPWORDS = STOPWORDS_CN | STOPWORDS_EN | STOPWORDS_TECH

    def __init__(self, embedding_client=None):
        """
        Args:
            embedding_client: EmbeddingClient 实例（用于 KeyBERT 阶段的语义匹配）
        """
        self.embedder = embedding_client
        # 语料库级 IDF 表：{词: idf_value}
        # 在 build_corpus_idf() 调用后填充，之后 build_doc_profile 会使用它
        self.corpus_idf: Optional[Dict[str, float]] = None
        self.corpus_df: Dict[str, int] = {}   # 原始 DF 表，支持增量更新
        self.corpus_doc_count: int = 0

    # ================================================================
    #  语料库级 IDF 构建（应在入库前调用一次）
    # ================================================================

    def build_corpus_idf(self, documents: List[str],
                         debug: bool = True) -> Dict[str, float]:
        """
        扫描所有文档，构建真正的 IDF 表。

        同时将 DF 表保存在 self.corpus_df 供增量更新使用。
        """
        n_docs = len(documents)
        if n_docs == 0:
            return {}

        if debug:
            print(f"📊 [IDF构建] 扫描 {n_docs} 篇文档...")

        # 统计每个词出现在多少篇文档中 (Document Frequency)
        df_counter = Counter()

        for doc_text in documents:
            words = self._tokenize(doc_text)
            unique_words = set(w.lower() for w in words 
                              if len(w) >= 2 and w not in self.STATIC_STOPWORDS)
            df_counter.update(unique_words)

        self.corpus_df = dict(df_counter)
        self.corpus_doc_count = n_docs
        self._recompute_idf(debug)
        return self.corpus_idf

    def update_idf(self, new_documents: List[str],
                   debug: bool = True) -> Dict[str, float]:
        """
        增量更新 IDF：只扫描新增文档，合并到已有 DF 表中。
        
        比 build_corpus_idf 快得多——不需要重新读取旧文档。
        """
        if not self.corpus_df:
            # 没有旧表，退回全量构建
            return self.build_corpus_idf(new_documents, debug)

        n_new = len(new_documents)
        if n_new == 0:
            return self.corpus_idf

        if debug:
            print(f"📊 [IDF增量更新] 扫描 {n_new} 篇新文档，"
                  f"合并到已有 {self.corpus_doc_count} 篇的 IDF 表...")

        # 只统计新文档的 DF
        new_df = Counter()
        for doc_text in new_documents:
            words = self._tokenize(doc_text)
            unique_words = set(w.lower() for w in words 
                              if len(w) >= 2 and w not in self.STATIC_STOPWORDS)
            new_df.update(unique_words)

        # 合并到已有 DF
        for word, df in new_df.items():
            self.corpus_df[word] = self.corpus_df.get(word, 0) + df
        
        self.corpus_doc_count += n_new
        self._recompute_idf(debug)
        return self.corpus_idf

    def _recompute_idf(self, debug: bool = False):
        """从 DF 表重新计算 IDF 值"""
        n = self.corpus_doc_count
        idf_dict = {}
        for word, df in self.corpus_df.items():
            idf_dict[word] = math.log(n / (df + 1)) + 1

        self.corpus_idf = idf_dict

        if debug:
            sorted_by_idf = sorted(idf_dict.items(), key=lambda x: x[1])
            print(f"   最普遍的词 (低IDF): {[(w, f'{v:.2f}') for w, v in sorted_by_idf[:10]]}")
            print(f"   最稀有的词 (高IDF): {[(w, f'{v:.2f}') for w, v in sorted_by_idf[-10:]]}")
            print(f"   词表大小: {len(idf_dict)}, 基于 {n} 篇文档")

        if HAS_JIEBA:
            self._set_jieba_custom_idf(idf_dict)

    def _set_jieba_custom_idf(self, idf_dict: Dict[str, float]):
        """将自定义 IDF 写入临时文件，让 jieba.analyse 使用"""
        try:
            idf_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "corpus_idf.txt"
            )
            with open(idf_path, 'w', encoding='utf-8') as f:
                for word, idf_val in idf_dict.items():
                    f.write(f"{word} {idf_val:.6f}\n")
            jieba.analyse.set_idf_path(idf_path)
        except Exception as e:
            print(f"⚠️ 设置 jieba 自定义 IDF 失败: {e}")

    def save_idf(self, path: str):
        """保存 IDF 表到文件（同时保存 DF 表，支持增量更新）"""
        if not self.corpus_idf:
            print("⚠️ IDF 表为空，无法保存")
            return
        import json
        data = {
            "doc_count": self.corpus_doc_count,
            "df": self.corpus_df,      # 保存原始 DF，用于增量更新
            "idf": self.corpus_idf     # 保存计算好的 IDF，加载时直接用
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"✅ IDF 表已保存: {path} ({len(self.corpus_idf)} 词, {self.corpus_doc_count} 篇)")

    def load_idf(self, path: str) -> bool:
        """从文件加载 IDF 表（同时恢复 DF 表以支持增量更新）"""
        import json
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.corpus_idf = data["idf"]
            self.corpus_doc_count = data["doc_count"]
            self.corpus_df = data.get("df", {})  # 兼容旧格式（无 df 字段）
            if HAS_JIEBA:
                self._set_jieba_custom_idf(self.corpus_idf)
            print(f"✅ 已加载 IDF 表: {path} ({len(self.corpus_idf)} 词, "
                  f"基于 {self.corpus_doc_count} 篇文档)")
            return True
        except Exception as e:
            print(f"⚠️ 加载 IDF 失败: {e}")
            return False

    # ================================================================
    #  阶段 1：文档级 — 构建候选关键词档案
    # ================================================================

    def build_doc_profile(self, full_text: str, 
                          max_candidates: int = 200,
                          top_n_stopwords: int = 50,
                          debug: bool = True) -> Dict:
        """
        在整篇文档上构建关键词档案（应在分块前调用一次）

        返回一个 doc_profile 字典，包含：
          - candidates:       List[str]      文档级候选关键词列表
          - candidate_embeds: np.ndarray     候选词的 embedding 矩阵 (N x D)
          - doc_stopwords:    Set[str]       文档级动态停用词
          - discovered_terms: Set[str]       自动发现的专业术语（已注入 jieba）
        """
        if not full_text or not full_text.strip():
            return self._empty_profile()

        # 1. 自动发现专业术语并注入 jieba
        discovered_terms = self._discover_domain_terms(full_text)
        if debug and discovered_terms:
            print(f"🔬 [术语发现] 注入 {len(discovered_terms)} 个专业术语: "
                  f"{list(discovered_terms)[:15]}...")

        # 2. 分词 (用增强后的 jieba)
        words = self._tokenize(full_text)

        # 3. 计算文档级动态停用词
        doc_stopwords = self._compute_doc_stopwords(words, top_n=top_n_stopwords)
        all_stopwords = self.STATIC_STOPWORDS | doc_stopwords

        if debug:
            print(f"🔍 [全局分析] 文档高频停用词 (Top {top_n_stopwords}): "
                  f"{list(doc_stopwords)[:10]}...")

        # 4. 提取文档级候选关键词 (TF-IDF + n-gram)
        candidates = self._extract_doc_candidates(
            full_text, words, all_stopwords, max_candidates, debug
        )

        if debug:
            print(f"📋 [候选池] 共 {len(candidates)} 个候选关键词: "
                  f"{candidates[:15]}...")

        # 5. 预计算候选词 embedding (一次性批量)
        candidate_embeds = None
        if self.embedder and candidates:
            try:
                candidate_embeds = self.embedder.embed(
                    candidates, show_progress=False, instruction="",
                    batch_size=64  # 候选词都是短文本，用大batch
                )
            except Exception as e:
                print(f"⚠️ 候选词 embedding 计算失败: {e}")

        return {
            "candidates": candidates,
            "candidate_embeds": candidate_embeds,
            "doc_stopwords": doc_stopwords,
            "discovered_terms": discovered_terms,
        }

    def _empty_profile(self) -> Dict:
        return {
            "candidates": [],
            "candidate_embeds": None,
            "doc_stopwords": set(),
            "discovered_terms": set(),
        }

    # ================================================================
    #  阶段 2：Chunk级 — 从候选池中筛选关键词 (KeyBERT 思想)
    # ================================================================

    def extract(self, text: str, topk: int = 10,
                doc_profile: Dict = None,
                external_stopwords: Set[str] = None,
                chunk_embedding: 'np.ndarray' = None,
                debug: bool = False) -> List[str]:
        """
        为单个 chunk 提取关键词

        优先使用 KeyBERT 语义匹配（如果有 doc_profile 和 embedder），
        否则降级到 chunk 级 TF-IDF。

        Args:
            text:               chunk 文本
            topk:               返回关键词数量
            doc_profile:        build_doc_profile 的返回值
            external_stopwords: 额外停用词（向后兼容）
            chunk_embedding:    预计算的 chunk embedding (避免重复计算)
            debug:              是否打印调试信息
        """
        if not text or not text.strip():
            return []

        # 合并停用词
        all_stopwords = self.STATIC_STOPWORDS.copy()
        if external_stopwords:
            all_stopwords |= external_stopwords
        if doc_profile and doc_profile.get("doc_stopwords"):
            all_stopwords |= doc_profile["doc_stopwords"]

        # 尝试 KeyBERT 路径
        if (doc_profile
                and doc_profile.get("candidates")
                and doc_profile.get("candidate_embeds") is not None
                and self.embedder):
            keywords = self._extract_keybert(
                text, doc_profile, topk, all_stopwords, debug,
                chunk_embedding=chunk_embedding
            )
            if keywords:
                return keywords

        # 降级：chunk 级 TF-IDF
        if debug:
            print(f"  ↘ 降级到 chunk 级 TF-IDF")
        return self._extract_tfidf_fallback(text, topk, all_stopwords, debug)

    def _extract_keybert(self, text: str, doc_profile: Dict,
                         topk: int, stopwords: Set[str],
                         debug: bool,
                         chunk_embedding: 'np.ndarray' = None) -> List[str]:
        """
        KeyBERT 核心：计算 chunk embedding 与每个候选词 embedding 的余弦相似度，
        取 Top-K 作为该 chunk 的关键词。
        """
        candidates = doc_profile["candidates"]
        candidate_embeds = doc_profile["candidate_embeds"]

        try:
            # 复用已有的 chunk embedding，避免重复计算
            if chunk_embedding is not None:
                c_embed = chunk_embedding
            else:
                c_embed = self.embedder.embed(
                    [text], show_progress=False, instruction=""
                )[0]

            # 余弦相似度
            similarities = self._cosine_similarity_batch(c_embed, candidate_embeds)

            # 用 MMR 筛选，平衡相关性和多样性
            selected = self._mmr_select(
                similarities, candidate_embeds, topk,
                lambda_param=0.6  # 0.6 偏向相关性，0.4 偏向多样性
            )

            keywords = [candidates[i] for i in selected]

            # 中英文比例控制
            is_chinese = self._is_chinese_text(text)
            if is_chinese:
                keywords = self._balance_language(keywords, topk, prefer_chinese=True)

            if debug:
                top5_with_score = [(candidates[i], f"{similarities[i]:.3f}") 
                                   for i in selected[:5]]
                print(f"  🎯 [KeyBERT] Top-5: {top5_with_score}")

            return keywords

        except Exception as e:
            if debug:
                print(f"  ⚠️ KeyBERT 失败: {e}")
            return []

    def _mmr_select(self, doc_similarities: np.ndarray,
                    candidate_embeds: np.ndarray,
                    topk: int,
                    lambda_param: float = 0.6) -> List[int]:
        """
        MMR (Maximal Marginal Relevance) 选择算法

        在保证与 chunk 相关的前提下，尽量选择彼此不相似的关键词，
        避免返回 "小麦赤霉病"、"赤霉病防治"、"小麦赤霉" 这类高度重叠的关键词。

        score(i) = λ * sim(chunk, kw_i) - (1-λ) * max_{j∈selected} sim(kw_i, kw_j)
        """
        n = len(doc_similarities)
        if n == 0:
            return []

        # 预过滤：只考虑相似度 > 0 的候选词（加速）
        valid_mask = doc_similarities > 0.05
        valid_indices = np.where(valid_mask)[0]

        if len(valid_indices) == 0:
            # 全部太低，退回纯排序
            return list(np.argsort(doc_similarities)[::-1][:topk])

        # 预计算候选词之间的相似度矩阵（只算 valid 子集）
        valid_embeds = candidate_embeds[valid_indices]
        norms = np.linalg.norm(valid_embeds, axis=1, keepdims=True) + 1e-9
        normed = valid_embeds / norms
        inter_sim = np.dot(normed, normed.T)  # (M x M)

        valid_doc_sims = doc_similarities[valid_indices]

        selected_local = []  # 在 valid_indices 空间中的索引
        remaining = set(range(len(valid_indices)))

        for _ in range(min(topk, len(valid_indices))):
            best_score = -float('inf')
            best_idx = -1

            for local_idx in remaining:
                relevance = valid_doc_sims[local_idx]

                if selected_local:
                    # 与已选关键词的最大相似度
                    max_redundancy = max(
                        inter_sim[local_idx, s] for s in selected_local
                    )
                else:
                    max_redundancy = 0.0

                score = lambda_param * relevance - (1 - lambda_param) * max_redundancy

                if score > best_score:
                    best_score = score
                    best_idx = local_idx

            if best_idx == -1:
                break

            selected_local.append(best_idx)
            remaining.discard(best_idx)

        # 映射回全局索引
        return [int(valid_indices[i]) for i in selected_local]

    # ================================================================
    #  术语自动发现 (基于 PMI 互信息)
    # ================================================================

    def _discover_domain_terms(self, text: str,
                               min_freq: int = 5,
                               min_pmi: float = 5.0,
                               max_term_len: int = 6) -> Set[str]:
        """
        从文档中自动发现可能的专业术语（2-gram、3-gram），
        并注入 jieba 词典以改善后续分词。

        原理：PMI (Pointwise Mutual Information) + 左右熵过滤
        """
        discovered = set()

        if not HAS_JIEBA:
            return discovered

        # ---- 中文术语发现 ----
        chars = [c for c in text if '\u4e00' <= c <= '\u9fa5']
        if len(chars) < 500:
            return discovered

        total = len(chars)
        unigram_count = Counter(chars)

        # 动态调整 min_freq：文档越长，频率阈值越高
        adaptive_min_freq = max(min_freq, total // 2000)

        # 2-gram PMI
        bigram_count = Counter()
        for i in range(len(chars) - 1):
            bigram_count[chars[i] + chars[i + 1]] += 1

        bigram_candidates = set()
        for bigram, freq in bigram_count.items():
            if freq < adaptive_min_freq:
                continue
            c1, c2 = bigram[0], bigram[1]
            p_bigram = freq / total
            p_c1 = unigram_count[c1] / total
            p_c2 = unigram_count[c2] / total
            if p_c1 == 0 or p_c2 == 0:
                continue
            pmi = math.log2(p_bigram / (p_c1 * p_c2 + 1e-10))
            if pmi >= min_pmi:
                bigram_candidates.add(bigram)

        # 3-gram PMI (仅对 bigram 候选进行扩展，避免全量计算)
        trigram_count = Counter()
        for i in range(len(chars) - 2):
            trigram_count[chars[i] + chars[i + 1] + chars[i + 2]] += 1

        for trigram, freq in trigram_count.items():
            if freq < adaptive_min_freq:
                continue
            # 至少包含一个高PMI bigram子串才考虑
            if (trigram[:2] not in bigram_candidates
                    and trigram[1:] not in bigram_candidates):
                continue
            p_trigram = freq / total
            p_chars = 1.0
            for c in trigram:
                p_chars *= (unigram_count[c] / total)
            if p_chars == 0:
                continue
            pmi = math.log2(p_trigram / (p_chars + 1e-10))
            if pmi >= min_pmi * 0.7:
                bigram_candidates.add(trigram)

        # 过滤：去掉停用词组合和纯虚词
        for term in bigram_candidates:
            if term in self.STATIC_STOPWORDS:
                continue
            # 术语中不应全部由高频单字组成（过滤"的是"、"和在"等）
            if all(unigram_count[c] / total > 0.02 for c in term):
                continue
            discovered.add(term)

        # 限制总数，防止注入过多（取 PMI 最高的 top 200）
        if len(discovered) > 200:
            scored = []
            for term in discovered:
                freq = bigram_count.get(term, 0) or trigram_count.get(term, 0)
                scored.append((term, freq))
            scored.sort(key=lambda x: -x[1])
            discovered = {t for t, _ in scored[:200]}

        # ---- 英文术语发现 ----
        en_terms = re.findall(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b', text
        )
        en_term_counter = Counter(en_terms)
        for term, freq in en_term_counter.items():
            if freq >= adaptive_min_freq:
                discovered.add(term)

        abbrevs = re.findall(r'\b([A-Z]{2,6})\b', text)
        abbrev_counter = Counter(abbrevs)
        for abbr, freq in abbrev_counter.items():
            if freq >= adaptive_min_freq and abbr not in self.STOPWORDS_EN:
                discovered.add(abbr)

        # 注入 jieba 词典
        if HAS_JIEBA:
            for term in discovered:
                if re.search(r'[\u4e00-\u9fa5]', term):
                    jieba.add_word(term, freq=10000)

        return discovered

    # ================================================================
    #  文档级候选词提取
    # ================================================================

    def _extract_doc_candidates(self, full_text: str, words: List[str],
                                stopwords: Set[str],
                                max_candidates: int,
                                debug: bool) -> List[str]:
        """
        在整篇文档上提取候选关键词
        优先使用自建语料库 IDF（如果 build_corpus_idf 已调用）
        """
        candidates_set = set()

        # ---- 来源 1: TF-IDF ----
        if self.corpus_idf:
            # 使用自建 IDF 做真正的 TF-IDF
            tfidf_kws = self._compute_tfidf_with_corpus_idf(
                words, stopwords, max_candidates
            )
            candidates_set.update(tfidf_kws)
        elif HAS_JIEBA:
            # 降级：用 jieba 自带 IDF（不准但聊胜于无）
            tfidf_kws = jieba.analyse.extract_tags(
                full_text, topK=max_candidates, withWeight=False
            )
            for kw in tfidf_kws:
                if self._is_valid_keyword(kw, stopwords):
                    candidates_set.add(kw)

        # ---- 来源 2: TextRank（不依赖 IDF，基于图算法） ----
        if HAS_JIEBA:
            try:
                textrank_kws = jieba.analyse.textrank(
                    full_text, topK=max_candidates // 2, withWeight=False
                )
                for kw in textrank_kws:
                    if self._is_valid_keyword(kw, stopwords):
                        candidates_set.add(kw)
            except Exception:
                pass

        # ---- 来源 3: 高频有效词 ----
        word_freq = Counter(w for w in words if self._is_valid_keyword(w, stopwords))
        for w, freq in word_freq.most_common(max_candidates):
            if freq >= 2:
                candidates_set.add(w)

        # ---- 来源 4: 有效 bigram ----
        if HAS_JIEBA:
            bigrams = self._extract_valid_bigrams(words, stopwords)
            for bg, freq in bigrams.most_common(max_candidates // 2):
                if freq >= 2:
                    candidates_set.add(bg)

        # ---- 来源 5: 英文短语 ----
        en_phrases = self._extract_english_phrases(full_text, stopwords)
        candidates_set |= en_phrases

        # 最终排序：如果有自建 IDF，用 TF-IDF 分数排序；否则用词频
        if self.corpus_idf:
            candidates_list = []
            doc_word_count = Counter(w.lower() for w in words)
            doc_len = len(words) or 1
            for c in candidates_set:
                tf = doc_word_count.get(c.lower(), 0) / doc_len
                idf = self.corpus_idf.get(c.lower(), math.log(self.corpus_doc_count + 1))
                tfidf_score = tf * idf
                candidates_list.append((c, tfidf_score))
        else:
            candidates_list = []
            for c in candidates_set:
                freq = full_text.lower().count(c.lower())
                if freq > 0:
                    candidates_list.append((c, freq))

        candidates_list.sort(key=lambda x: -x[1])
        return [c for c, _ in candidates_list[:max_candidates]]

    def _compute_tfidf_with_corpus_idf(self, words: List[str],
                                        stopwords: Set[str],
                                        topk: int) -> List[str]:
        """用自建语料库 IDF 计算真正的 TF-IDF"""
        # TF: 词在当前文档中的频率
        doc_word_count = Counter(w.lower() for w in words 
                                 if self._is_valid_keyword(w, stopwords))
        doc_len = len(words) or 1

        scored = []
        for word, count in doc_word_count.items():
            tf = count / doc_len
            # 从自建 IDF 表查询，不存在的词给一个高 IDF（稀有词）
            idf = self.corpus_idf.get(word, math.log(self.corpus_doc_count + 1))
            scored.append((word, tf * idf))

        scored.sort(key=lambda x: -x[1])
        return [w for w, _ in scored[:topk]]

    def _extract_valid_bigrams(self, words: List[str],
                               stopwords: Set[str]) -> Counter:
        """提取有效的 bigram 关键词"""
        bigrams = Counter()
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            # 两个词都有效 且 组合长度合理
            if (self._is_valid_keyword(w1, stopwords) 
                    and self._is_valid_keyword(w2, stopwords)):
                combined = w1 + w2
                if 3 <= len(combined) <= 12:
                    bigrams[combined] += 1
        return bigrams

    def _extract_english_phrases(self, text: str,
                                 stopwords: Set[str]) -> Set[str]:
        """提取英文短语和专业术语"""
        phrases = set()

        # 大写开头的多词短语
        for m in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Za-z]+){1,3})\b', text):
            phrase = m.group(1)
            words = phrase.split()
            # 至少有一个非停用词
            if any(w.lower() not in stopwords for w in words):
                phrases.add(phrase)

        # 单个有效英文词（频率>=3）
        en_words = re.findall(r'\b([a-zA-Z]{3,})\b', text)
        en_freq = Counter(w.lower() for w in en_words 
                          if w.lower() not in stopwords)
        for w, freq in en_freq.most_common(50):
            if freq >= 3:
                phrases.add(w)

        return phrases

    # ================================================================
    #  降级方案：Chunk级 TF-IDF
    # ================================================================

    def _extract_tfidf_fallback(self, text: str, topk: int,
                                stopwords: Set[str],
                                debug: bool) -> List[str]:
        """当没有 doc_profile 或 embedder 时的降级方案"""
        keywords = []
        is_chinese = self._is_chinese_text(text)

        if HAS_JIEBA:
            raw_kws = jieba.analyse.extract_tags(text, topK=topk * 3)
            keywords = [kw for kw in raw_kws 
                        if self._is_valid_keyword(kw, stopwords)]

        # 英文补充
        en_words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        en_freq = Counter(w for w in en_words 
                          if self._is_valid_keyword(w, stopwords))
        en_kws = [w for w, _ in en_freq.most_common(topk)]

        if is_chinese:
            max_en = max(1, int(topk * 0.2))
            result = keywords[:topk]
            if len(result) < topk:
                needed = topk - len(result)
                result.extend(en_kws[:min(needed, max_en)])
        else:
            result = keywords + en_kws

        return self._dedupe(result, topk)

    # ================================================================
    #  向后兼容接口
    # ================================================================

    def compute_doc_stopwords(self, full_text: str, top_n: int = 50) -> Set[str]:
        """
        向后兼容：仅计算文档级停用词
        推荐使用 build_doc_profile() 替代
        """
        words = self._tokenize(full_text)
        return self._compute_doc_stopwords(words, top_n)

    # ================================================================
    #  工具方法
    # ================================================================

    def _tokenize(self, text: str) -> List[str]:
        """统一分词入口"""
        if HAS_JIEBA:
            return [w.strip() for w in jieba.lcut(text) if w.strip()]
        else:
            # 无 jieba 时的简单分词：中文按字符对提取，英文按单词
            tokens = []
            # 中文：提取2-4字的连续中文片段
            for m in re.finditer(r'[\u4e00-\u9fa5]{2,}', text):
                word = m.group()
                tokens.append(word)
                # 也生成 bigram 子片段
                if len(word) > 2:
                    for i in range(len(word) - 1):
                        tokens.append(word[i:i+2])
                    if len(word) > 3:
                        for i in range(len(word) - 2):
                            tokens.append(word[i:i+3])
            # 英文
            for m in re.finditer(r'[a-zA-Z]{2,}', text):
                tokens.append(m.group().lower())
            return tokens

    def _compute_doc_stopwords(self, words: List[str], top_n: int) -> Set[str]:
        """从词频统计中提取文档级停用词"""
        counter = Counter(w.lower() for w in words if len(w) > 1)
        doc_stopwords = set()

        for w, _ in counter.most_common(top_n * 2):
            if w not in self.STATIC_STOPWORDS:
                # 停用词应该是短词（2-6字符），长词通常是有意义的术语
                if len(w) > 6:
                    continue
                if re.match(r'^[\u4e00-\u9fa5]+$', w) or re.match(r'^[a-z]+$', w):
                    doc_stopwords.add(w)
                    if len(doc_stopwords) >= top_n:
                        break

        return doc_stopwords

    def _is_valid_keyword(self, word: str, stopwords: Set[str]) -> bool:
        """关键词有效性检查"""
        w = word.lower().strip()
        if len(w) < 2:
            return False
        if w in stopwords:
            return False
        if re.match(r'^[\d\.\-\%\+]+$', w):
            return False
        if not re.search(r'[\u4e00-\u9fa5a-zA-Z]', w):
            return False
        return True

    def _is_chinese_text(self, text: str) -> bool:
        cn_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        return (cn_chars / max(len(text), 1)) > 0.1

    def _balance_language(self, keywords: List[str], topk: int,
                          prefer_chinese: bool = True) -> List[str]:
        """控制中英文关键词比例"""
        if not prefer_chinese:
            return keywords[:topk]

        result = []
        en_count = 0
        max_en = max(1, int(topk * 0.3))

        for kw in keywords:
            has_cn = bool(re.search(r'[\u4e00-\u9fa5]', kw))
            if has_cn:
                result.append(kw)
            else:
                if en_count < max_en:
                    result.append(kw)
                    en_count += 1
            if len(result) >= topk:
                break

        return result

    def _cosine_similarity_batch(self, query: np.ndarray,
                                 candidates: np.ndarray) -> np.ndarray:
        query_norm = query / (np.linalg.norm(query) + 1e-9)
        cand_norm = candidates / (np.linalg.norm(candidates, axis=1, keepdims=True) + 1e-9)
        return np.dot(cand_norm, query_norm)

    def _dedupe(self, keywords: List[str], topk: int) -> List[str]:
        """去重（含子串检测）"""
        seen = set()
        unique = []
        for kw in keywords:
            kw_lower = kw.lower()
            # 检查是否是已选关键词的子串或超串
            is_redundant = False
            for s in seen:
                if kw_lower in s or s in kw_lower:
                    is_redundant = True
                    break
            if not is_redundant:
                seen.add(kw_lower)
                unique.append(kw)
                if len(unique) >= topk:
                    break
        return unique


# ==================== 便捷函数 ====================

def extract_keywords(text: str, topk: int = 10,
                     external_stopwords: Set[str] = None,
                     debug: bool = True, **kwargs) -> List[str]:
    """便捷函数（向后兼容）"""
    extractor = KeywordExtractor(**kwargs)
    return extractor.extract(text, topk, external_stopwords=external_stopwords, debug=debug)
