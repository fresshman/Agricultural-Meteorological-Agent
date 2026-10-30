# -*- coding: utf-8 -*-
"""
向量数据库 - FAISS + SQLite版 (最终稳定版)
修复了 FAISS 索引初始化和加载的属性缺失问题
"""
import os
import json
import sqlite3
import numpy as np
import threading
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from .keyword_extract import KeywordExtractor
from collections import Counter

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    print("警告: FAISS未安装，请运行: pip install faiss-cpu")

@dataclass
class Document:
    id: int
    content: str
    source: str
    keywords: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id, 
            "content": self.content, 
            "source": self.source, 
            "keywords": self.keywords, 
            "metadata": self.metadata
        }
    
    @classmethod
    def from_row(cls, row: Tuple) -> "Document":
        """从SQLite行数据构建对象"""
        return cls(
            id=row[0], 
            content=row[1], 
            source=row[2], 
            keywords=json.loads(row[3]) if row[3] else [], 
            metadata=json.loads(row[4]) if row[4] else {}
        )

class FAISSVectorStore:
    def __init__(self, dimension: int, index_type: str = "flat"):
        if not HAS_FAISS: raise RuntimeError("FAISS未安装")
        self.dimension = dimension
        self.index_type = index_type
        self.is_trained = False
        # 【修复关键】必须显式初始化为 None，防止 AttributeError
        self.index = None 
    
    def create_new(self):
        """显式创建新索引"""
        if self.index_type == "flat":
            self.index = faiss.IndexFlatIP(self.dimension)
            self.is_trained = True
        elif self.index_type == "ivf":
            nlist = 100
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT)
        elif self.index_type == "hnsw":
            self.index = faiss.IndexHNSWFlat(self.dimension, 32, faiss.METRIC_INNER_PRODUCT)
            self.is_trained = True
        else:
            # 默认回退到 Flat
            self.index = faiss.IndexFlatIP(self.dimension)
            self.is_trained = True
    
    def add(self, vectors: np.ndarray):
        """
        添加向量到索引
        注意：调用方应确保向量已经过 L2 归一化 (EmbeddingClient 默认 normalize=True)
        """
        # 安全检查
        if self.index is None:
            self.create_new()

        if vectors.dtype != np.float32: vectors = vectors.astype(np.float32)
        # 不再重复归一化：EmbeddingClient.embed() 已默认 normalize=True
        # 如果传入的是未归一化的向量（如外部来源），调用方应自行归一化
        
        if self.index_type == "ivf" and not self.is_trained:
            if len(vectors) >= 100:
                self.index.train(vectors)
                self.is_trained = True
            else:
                self.index = faiss.IndexFlatIP(self.dimension)
                self.is_trained = True
        
        self.index.add(vectors)
    
    def search(self, query_vectors: np.ndarray, top_k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        if self.index is None:
            raise RuntimeError("FAISS 索引未初始化，无法搜索")
            
        if query_vectors.dtype != np.float32: query_vectors = query_vectors.astype(np.float32)
        # 查询向量归一化：EmbeddingClient.embed_query() 已 normalize，
        # 但这里做防御性归一化，确保与入库向量一致
        norms = np.linalg.norm(query_vectors, axis=1, keepdims=True)
        if np.any(norms > 1.01) or np.any(norms < 0.99):
            # 仅在检测到未归一化时才执行（避免不必要的计算）
            faiss.normalize_L2(query_vectors)
        return self.index.search(query_vectors, top_k)
    
    @property
    def total(self) -> int: 
        return self.index.ntotal if self.index else 0
        
    def save(self, path: str): 
        if self.index:
            faiss.write_index(self.index, path)

class VectorDatabase:
    def __init__(self, embedding_client=None, index_type: str = "flat", keyword_method: str = "hybrid", db_path: str = "agri_knowledge"):
        self.embedder = embedding_client
        self.index_type = index_type
        self.keyword_extractor = KeywordExtractor(embedding_client=embedding_client)
        self.vector_store: Optional[FAISSVectorStore] = None
        self.dimension = embedding_client.dimension if embedding_client else None
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 数据库路径初始化
        self.db_path = db_path
        self._init_sqlite()
        
        # 加载现有 FAISS 索引
        self._load_faiss_index()

    def _init_sqlite(self):
        """初始化 SQLite 数据库"""
        self.sqlite_path = f"{self.db_path}.db"
        self.conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                content TEXT,
                source TEXT,
                keywords TEXT,
                metadata TEXT
            )
        ''')

        # FAISS 位置 → SQLite id 的映射表
        # faiss_pos: FAISS 内部的连续序号 (0, 1, 2, ...)
        # sqlite_id: SQLite documents 表中的 id 字段
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faiss_map (
                faiss_pos  INTEGER PRIMARY KEY,
                sqlite_id  INTEGER NOT NULL,
                FOREIGN KEY (sqlite_id) REFERENCES documents(id)
            )
        ''')
        self.conn.commit()
        
        cursor.execute('SELECT MAX(id) FROM documents')
        max_id = cursor.fetchone()[0]
        self._id_counter = (max_id + 1) if max_id is not None else 0

        # 内存映射：list[faiss_pos] = sqlite_id，加速检索时的转换
        # 从数据库恢复，保证重启后状态一致
        cursor.execute('SELECT faiss_pos, sqlite_id FROM faiss_map ORDER BY faiss_pos ASC')
        rows = cursor.fetchall()
        self._faiss_to_sqlite: List[int] = [r[1] for r in rows]

        print(f"数据库连接成功: {self.sqlite_path}, "
              f"文档数: {self._id_counter}, 映射条目: {len(self._faiss_to_sqlite)}")

    def _load_faiss_index(self):
        """加载或初始化 FAISS 索引"""
        index_path = f"{self.db_path}.faiss"
        
        # 尝试多种格式的索引文件
        index_candidates = [
            index_path,  # 标准格式：{db_path}.faiss
            f"{self.db_path}/faiss_index.index",  # 知识库构建脚本格式
            f"{self.db_path}/index.faiss"  # 其他可能格式
        ]
        
        # 1. 尝试从文件加载
        for candidate_path in index_candidates:
            if os.path.exists(candidate_path):
                try:
                    index = faiss.read_index(candidate_path)
                    loaded_dim = index.d
                    self.dimension = loaded_dim
                    
                    self.vector_store = FAISSVectorStore(self.dimension, self.index_type)
                    self.vector_store.index = index
                    self.vector_store.is_trained = True
                    
                    print(f"✅ 成功加载 FAISS 索引: {candidate_path}")
                    print(f"   维度: {self.dimension}, 向量数: {index.ntotal}")

                    # 检测旧库（有 FAISS 向量但映射表为空）
                    if index.ntotal > 0 and len(self._faiss_to_sqlite) == 0:
                        # 尝试从metadata.json加载
                        metadata_path = f"{self.db_path}/metadata.json"
                        if os.path.exists(metadata_path):
                            print(f"   检测到知识库构建脚本格式，正在导入...")
                            self._import_from_metadata(metadata_path)
                        else:
                            print(f"⚠️  检测到旧版数据库：FAISS 有 {index.ntotal} 条向量，但 faiss_map 映射表为空。")
                            print(f"    正在自动重建映射表（假设旧库 faiss_pos == sqlite_id）...")
                            self._rebuild_legacy_map()

                    return
                except Exception as e:
                    print(f"⚠️ 加载 FAISS 索引失败 ({candidate_path}): {e}")
                    continue
        
        # 2. 如果文件不存在，但有维度信息，则新建空索引
        if self.dimension:
            print(f"初始化新的 FAISS 索引 (Dim={self.dimension})...")
            self.vector_store = FAISSVectorStore(self.dimension, self.index_type)
            self.vector_store.create_new()
        else:
            self.vector_store = None

    def _rebuild_legacy_map(self):
        """
        旧版数据库兼容：faiss_map 表为空时，
        按 faiss_pos == sqlite_id 的旧假设重建映射。
        重建后数据库具备完整的映射能力，后续入库也会正常记录。
        """
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id FROM documents ORDER BY id ASC')
            sqlite_ids = [r[0] for r in cursor.fetchall()]

            faiss_total = self.vector_store.total if self.vector_store else 0

            if len(sqlite_ids) != faiss_total:
                print(f"  ❌ SQLite 文档数({len(sqlite_ids)}) ≠ FAISS 向量数({faiss_total})，"
                      f"无法安全重建映射，请手动重新入库。")
                return

            map_data = [(pos, sid) for pos, sid in enumerate(sqlite_ids)]
            cursor.executemany(
                'INSERT OR IGNORE INTO faiss_map (faiss_pos, sqlite_id) VALUES (?, ?)',
                map_data
            )
            self.conn.commit()

            self._faiss_to_sqlite = [sid for _, sid in map_data]
            print(f"  ✅ 映射重建完成，共 {len(map_data)} 条记录。")

    def _import_from_metadata(self, metadata_path: str):
        """
        从知识库构建脚本的metadata.json导入数据到SQLite
        """
        import json
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if not metadata:
                print(f"  ⚠️ metadata.json为空")
                return
            
            with self.lock:
                cursor = self.conn.cursor()
                
                # 导入文档数据
                for i, item in enumerate(metadata):
                    content = item.get("content", "")
                    meta = item.get("metadata", {})
                    source = meta.get("filename", "unknown")
                    keywords = []  # 知识库构建脚本没有关键词
                    
                    # 插入文档
                    cursor.execute(
                        'INSERT INTO documents (id, content, source, keywords, metadata) VALUES (?, ?, ?, ?, ?)',
                        (i, content, source, json.dumps(keywords), json.dumps(meta))
                    )
                    
                    # 插入映射
                    cursor.execute(
                        'INSERT INTO faiss_map (faiss_pos, sqlite_id) VALUES (?, ?)',
                        (i, i)
                    )
                
                self.conn.commit()
                
                # 更新计数器和映射
                self._id_counter = len(metadata)
                self._faiss_to_sqlite = list(range(len(metadata)))
                
                print(f"  ✅ 成功导入 {len(metadata)} 条文档到SQLite")
                
        except Exception as e:
            print(f"  ❌ 导入metadata.json失败: {e}")
            import traceback
            traceback.print_exc()

    def iter_documents(self):
        """遍历所有文档"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, content, source, keywords, metadata FROM documents")
            while True:
                rows = cursor.fetchmany(1000)
                if not rows: break
                for row in rows:
                    yield Document.from_row(row)

    def add_documents(self, chunks: List[Dict], show_progress: bool = True, embed_batch_size: int = None, doc_stopwords: set = None, doc_profile: dict = None) -> List[Document]:
        if not chunks: return []
        
        # 1. 计算向量
        contents = [c["content"] for c in chunks]
        embeddings = None
        if self.embedder:
            if show_progress: print("  生成向量...")
            if hasattr(self.embedder, 'embed_documents'):
                embeddings = self.embedder.embed_documents(contents, batch_size=embed_batch_size, show_progress=show_progress)
            else:
                embeddings = self.embedder.embed(contents, batch_size=embed_batch_size, show_progress=show_progress)
            
            # 延迟初始化 (处理第一次添加的情况)
            if self.vector_store is None:
                self.dimension = embeddings.shape[1]
                self.vector_store = FAISSVectorStore(self.dimension, self.index_type)
                self.vector_store.create_new() # 确保创建

        # 2. 提取关键词 (优先使用 doc_profile 的两阶段策略)
        #    复用步骤1已计算的 chunk embedding，避免 KeyBERT 阶段重复计算
        if show_progress: print("  提取关键词...")
        prepared_docs = []
        for i, chunk in enumerate(chunks):
            chunk_emb = embeddings[i] if embeddings is not None else None
            keywords = self.keyword_extractor.extract(
                chunk["content"], topk=10,
                doc_profile=doc_profile,
                external_stopwords=doc_stopwords,
                chunk_embedding=chunk_emb
            )
            doc_data = {
                "content": chunk["content"],
                "source": chunk.get("source", ""),
                "keywords": keywords,
                "metadata": chunk.get("metadata", {})
            }
            prepared_docs.append(doc_data)

        new_docs_objects = []

        # 3. 写入数据库与索引 (加锁)
        with self.lock:
            cursor = self.conn.cursor()
            start_id = self._id_counter
            sql_data = []
            
            for i, doc_data in enumerate(prepared_docs):
                current_id = start_id + i
                doc_obj = Document(
                    id=current_id,
                    content=doc_data["content"],
                    source=doc_data["source"],
                    keywords=doc_data["keywords"],
                    metadata=doc_data["metadata"]
                )
                new_docs_objects.append(doc_obj)
                
                sql_data.append((
                    current_id,
                    doc_obj.content,
                    doc_obj.source,
                    json.dumps(doc_obj.keywords, ensure_ascii=False),
                    json.dumps(doc_obj.metadata, ensure_ascii=False)
                ))
            
            try:
                cursor.executemany(
                    'INSERT INTO documents (id, content, source, keywords, metadata) VALUES (?, ?, ?, ?, ?)',
                    sql_data
                )

                # 同步写入 faiss_map：新向量的 faiss_pos = 当前 FAISS 大小 + 偏移
                faiss_start_pos = self.vector_store.total if self.vector_store else 0
                map_data = [
                    (faiss_start_pos + i, start_id + i)
                    for i in range(len(prepared_docs))
                ]
                cursor.executemany(
                    'INSERT INTO faiss_map (faiss_pos, sqlite_id) VALUES (?, ?)',
                    map_data
                )

                self.conn.commit()
            except Exception as e:
                print(f"SQLite 写入错误: {e}")
                self.conn.rollback()
                raise
            
            if embeddings is not None:
                self.vector_store.add(embeddings)

            # 同步更新内存映射
            for _, sqlite_id in map_data:
                self._faiss_to_sqlite.append(sqlite_id)

            self._id_counter += len(chunks)
            
        return new_docs_objects
    
    def search(self, query: str = None, top_k: int = 5, query_embedding: 'np.ndarray' = None) -> List[Tuple[Document, float]]:
        """
        向量检索
        
        Args:
            query:           文本查询（会自动 embed）
            top_k:           返回数量
            query_embedding: 直接传入查询向量 (优先级高于 query)，shape=(1,D) 或 (D,)
        """
        if not self.vector_store: return []
        
        # 获取查询向量
        if query_embedding is not None:
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
        elif query and self.embedder:
            if hasattr(self.embedder, 'embed_query'):
                query_embedding = self.embedder.embed_query(query).reshape(1, -1)
            else:
                query_embedding = self.embedder.embed([query], show_progress=False)
        else:
            return []
            
        scores, indices = self.vector_store.search(query_embedding, top_k)
        
        # 用映射表将 FAISS 位置序号转换为 SQLite id
        found_ids = []
        id_score_map = {}
        for score, faiss_pos in zip(scores[0], indices[0]):
            if faiss_pos < 0:
                continue
            faiss_pos = int(faiss_pos)

            # 通过映射表转换
            if faiss_pos < len(self._faiss_to_sqlite):
                sqlite_id = self._faiss_to_sqlite[faiss_pos]
            else:
                # 映射表缺失时降级（兼容极端情况），记录警告
                print(f"  ⚠️  faiss_pos={faiss_pos} 超出映射表范围(len={len(self._faiss_to_sqlite)})，"
                      f"使用直接映射（可能不准确）")
                sqlite_id = faiss_pos

            found_ids.append(sqlite_id)
            # 同一 sqlite_id 可能命中多次（理论上不会），取最高分
            if sqlite_id not in id_score_map or id_score_map[sqlite_id] < float(score):
                id_score_map[sqlite_id] = float(score)
        
        if not found_ids: return []
        
        # 加锁保护 SQLite 读取 (并发安全)
        with self.lock:
            cursor = self.conn.cursor()
            placeholders = ','.join('?' for _ in found_ids)
            query_sql = f'SELECT id, content, source, keywords, metadata FROM documents WHERE id IN ({placeholders})'
            
            cursor.execute(query_sql, found_ids)
            rows = cursor.fetchall()
        
        results = []
        for row in rows:
            doc = Document.from_row(row)
            if doc.id in id_score_map:
                results.append((doc, id_score_map[doc.id]))
            
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def search_hybrid(self, query: str, top_k: int = 5, vector_weight: float = 0.85, keyword_weight: float = 0.15, weighted_keywords: List[Tuple[str, float]] = None, query_embedding: 'np.ndarray' = None) -> List[Tuple[Document, float]]:
        """
        双路召回混合检索:
          路径A: 向量语义召回 (支持传入 HyDE embedding)
          路径B: 关键词独立召回 (SQLite LIKE 模糊匹配)
          融合: 归一化后加权合并, 去重取 Top-K
        """
        # 0. 准备查询关键词
        query_kw_map = {}
        if weighted_keywords:
            for kw, wt in weighted_keywords:
                query_kw_map[kw.lower()] = wt
        elif self.keyword_extractor:
            raw_kws = self.keyword_extractor.extract(query, topk=5)
            for kw in raw_kws:
                query_kw_map[kw.lower()] = 1.0

        total_possible_weight = sum(query_kw_map.values()) or 1.0

        # ===== 路径 A: 向量召回 (可使用 HyDE embedding) =====
        vector_results = self.search(query, top_k * 3, query_embedding=query_embedding)

        # ===== 路径 B: 关键词独立召回 (从 SQLite 中检索) =====
        keyword_doc_ids = set()
        if query_kw_map:
            keyword_doc_ids = self._keyword_recall(query_kw_map, top_k * 3)
        
        # 收集路径 B 中不在路径 A 的文档
        vector_doc_ids = {doc.id for doc, _ in vector_results}
        extra_ids = keyword_doc_ids - vector_doc_ids
        
        extra_docs = []
        if extra_ids:
            extra_docs = self._fetch_documents_by_ids(list(extra_ids))

        # ===== 融合打分 =====
        # 向量分数归一化 (min-max 到 [0, 1])
        all_candidates = {}  # doc_id -> (Document, vec_score_norm, kw_score)
        
        if vector_results:
            vec_scores = [s for _, s in vector_results]
            vec_min, vec_max = min(vec_scores), max(vec_scores)
            vec_range = (vec_max - vec_min) if vec_max > vec_min else 1.0
            
            for doc, raw_score in vector_results:
                norm_score = (raw_score - vec_min) / vec_range
                all_candidates[doc.id] = [doc, norm_score, 0.0]
        
        # 关键词独立召回的文档，向量分数设为 0
        for doc in extra_docs:
            if doc.id not in all_candidates:
                all_candidates[doc.id] = [doc, 0.0, 0.0]

        # 对所有候选文档计算关键词匹配分数 (含子串匹配)
        for doc_id, (doc, vec_norm, _) in all_candidates.items():
            kw_score = self._compute_keyword_score(
                doc.keywords, query_kw_map, total_possible_weight
            )
            all_candidates[doc_id][2] = kw_score

        # 加权融合
        scored = []
        for doc_id, (doc, vec_norm, kw_score) in all_candidates.items():
            final_score = vector_weight * vec_norm + keyword_weight * kw_score
            scored.append((doc, final_score))

        return sorted(scored, key=lambda x: -x[1])[:top_k]

    def _keyword_recall(self, query_kw_map: Dict[str, float], 
                        limit: int) -> set:
        """
        路径 B: 从 SQLite 中用 LIKE 模糊匹配召回文档 ID
        """
        recalled_ids = set()
        if not hasattr(self, 'conn') or not self.conn:
            return recalled_ids
        
        with self.lock:
            cursor = self.conn.cursor()
            for kw in query_kw_map:
                if len(kw) < 2:
                    continue
                try:
                    # 在 keywords JSON 字段中搜索 (LIKE 模糊匹配)
                    cursor.execute(
                        'SELECT id FROM documents WHERE keywords LIKE ? LIMIT ?',
                        (f'%{kw}%', limit)
                    )
                    for row in cursor.fetchall():
                        recalled_ids.add(row[0])
                except Exception:
                    pass
        
        return recalled_ids
    
    def _fetch_documents_by_ids(self, doc_ids: List[int]) -> List[Document]:
        """批量从 SQLite 获取文档"""
        if not doc_ids:
            return []
        
        with self.lock:
            cursor = self.conn.cursor()
            placeholders = ','.join('?' for _ in doc_ids)
            cursor.execute(
                f'SELECT id, content, source, keywords, metadata '
                f'FROM documents WHERE id IN ({placeholders})',
                doc_ids
            )
            return [Document.from_row(row) for row in cursor.fetchall()]
    
    def _compute_keyword_score(self, doc_keywords: List[str],
                               query_kw_map: Dict[str, float],
                               total_possible_weight: float) -> float:
        """
        计算关键词匹配分数, 支持三级匹配:
          1. 精确匹配:   查询词 == 文档词           → 100% 权重
          2. 包含匹配:   查询词 in 文档词 (或反向)  → 70% 权重
          3. 无匹配:                                → 0
        """
        doc_kw_lower = [k.lower() for k in doc_keywords]
        matched_weight = 0.0

        for q_kw, q_wt in query_kw_map.items():
            best_match = 0.0
            
            for d_kw in doc_kw_lower:
                if q_kw == d_kw:
                    # 精确匹配
                    best_match = 1.0
                    break
                elif q_kw in d_kw or d_kw in q_kw:
                    # 包含匹配 (取较长者包含较短者)
                    best_match = max(best_match, 0.7)
            
            matched_weight += q_wt * best_match

        return matched_weight / total_possible_weight

    def save(self, path: str = None):
        target_path = path or self.db_path
        if self.vector_store:
            self.vector_store.save(f"{target_path}.faiss")
            print(f"索引已保存: {target_path}.faiss")
            
    def close(self):
        if self.conn:
            self.conn.close()

    def get_statistics(self) -> Dict:
        with self.lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM documents")
                total_docs = cursor.fetchone()[0]
                cursor.execute("SELECT SUM(LENGTH(content)) FROM documents")
                res = cursor.fetchone()
                total_chars = res[0] if res and res[0] else 0
                cursor.execute("SELECT COUNT(DISTINCT source) FROM documents")
                res = cursor.fetchone()
                source_count = res[0] if res and res[0] else 0
            except Exception:
                total_docs, total_chars, source_count = 0, 0, 0

        # FAISS 统计
        faiss_count = 0
        faiss_dim = self.dimension or 0
        
        if self.vector_store and self.vector_store.index:
            faiss_count = self.vector_store.total
        elif os.path.exists(f"{self.db_path}.faiss"):
            try:
                idx = faiss.read_index(f"{self.db_path}.faiss")
                faiss_count = idx.ntotal
                faiss_dim = idx.d
            except: pass
            
        return {
            "total_documents": total_docs,
            "total_characters": total_chars,
            "unique_sources": source_count,
            "dimension": faiss_dim,
            "index_type": self.index_type,
            "faiss_vectors": faiss_count,
        }

    def get_ingested_sources(self) -> Set[str]:
        """查询已入库的所有 source（文件名）去重集合，用于断点续传"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT source FROM documents")
            return {row[0] for row in cursor.fetchall()}
