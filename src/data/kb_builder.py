# -*- coding: utf-8 -*-
"""
知识库构建器
负责将 knowledge_bases/agri_knowledge_docs/*.txt 清洗、分块、向量化并写入
向量数据库，生成 .faiss 索引与 .db 元数据。

用途：
1. 独立运行：python -m src.data.kb_builder
2. 被 RAGEngine 自动调用（向量库为空且存在 docs 目录时）
"""
import os
from pathlib import Path
from typing import List, Dict


def build_knowledge_base(
    vector_db,
    docs_dir: str = None,
    embedder=None,
    verbose: bool = True
) -> Dict:
    """
    清洗 -> 分块 -> 向量化 -> 入库 -> 保存索引

    Args:
        vector_db: VectorDatabase 实例（已初始化）
        docs_dir: 知识文档目录（默认取自 vector_db 同级 docs 目录）
        embedder: Embedding 客户端（用于语义分块与向量化）
        verbose: 是否打印进度

    Returns:
        统计信息
    """
    from .cleaner import TextCleaner
    from .chunker import SmartChunker

    # 定位 docs 目录
    if not docs_dir:
        base = os.path.dirname(vector_db.db_path)
        candidate = os.path.join(base, "agri_knowledge_docs")
        docs_dir = candidate if os.path.isdir(candidate) else None

    if not docs_dir or not os.path.isdir(docs_dir):
        if verbose:
            print(f"⚠️  未找到知识文档目录: {docs_dir}")
        return vector_db.get_statistics()

    doc_files = sorted(Path(docs_dir).rglob("*.txt")) + sorted(
        Path(docs_dir).rglob("*.md")
    )

    if not doc_files:
        if verbose:
            print(f"⚠️  知识文档目录为空: {docs_dir}")
        return vector_db.get_statistics()

    # 这些是手工编写的农技文档，无需书籍级激进清洗（会误删正文）
    # 采用保守配置：只合并断行、规范化空白、过滤过短行，完整保留正文
    cleaner = TextCleaner(
        extract_title=False,
        remove_frontmatter=False,
        remove_toc=False,
        remove_copyright=False,
        remove_headers=False,
        clean_pdf_artifacts=False,
        remove_figure_table=False,
        merge_broken_paragraphs=True,
    )
    chunker = SmartChunker(
        embedding_client=embedder,
        llm_client=None,  # 建库阶段不依赖 LLM 仲裁，保持确定性
        merge_broken_paragraphs=True,
    )

    all_chunks: List[Dict] = []
    stats = {"files": 0, "chunks": 0, "characters": 0}

    for f in doc_files:
        try:
            raw = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            if verbose:
                print(f"❌ 读取失败 {f.name}: {e}")
            continue

        if not raw.strip():
            continue

        # 清洗
        cleaned = cleaner.clean(raw, source=f.name)
        if not cleaned.text or len(cleaned.text) < 20:
            if verbose:
                print(f"  - 清洗后为空/过短，跳过: {f.name}")
            continue

        # 分块
        chunks = chunker.chunk(
            cleaned.text,
            source=f.name,
            title=cleaned.title or cleaned.text[:30].strip(),
            remove_frontmatter=False,  # cleaner 已处理
            show_progress=False,
        )
        for c in chunks:
            c.setdefault("metadata", {})["source_file"] = f.name
            if cleaned.title:
                c["metadata"]["title"] = cleaned.title
            all_chunks.append(c)

        stats["files"] += 1
        stats["chunks"] += len(chunks)
        stats["characters"] += len(cleaned.text)

        if verbose:
            print(f"  ✓ {f.name}: {len(chunks)} chunks, {len(cleaned.text)} 字符")

    if not all_chunks:
        if verbose:
            print("⚠️  无有效分块，知识库未更新")
        return vector_db.get_statistics()

    # 向量化 + 入库
    vector_db.add_documents(all_chunks, show_progress=verbose)
    vector_db.save()

    final = vector_db.get_statistics()
    if verbose:
        print(f"\n✅ 知识库构建完成: {stats['files']} 文件 / "
              f"{stats['chunks']} chunks / 共 {stats['characters']} 字符")
        print(f"   入库文档: {final['total_documents']}, "
              f"向量数: {final['faiss_vectors']}, 维度: {final['dimension']}")

    return final


def main():
    """命令行入口：python -m src.data.kb_builder"""
    import sys
    root = Path(__file__).resolve().parents[2]  # modelscope_space/
    sys.path.insert(0, str(root))

    from src.data.vector_db import VectorDatabase
    from src.utils.clients import EmbeddingClient
    from config.settings import settings

    model = getattr(settings, "EMBEDDING_MODEL", None) or "bge-small-zh-v1.5"
    embedder = EmbeddingClient(model)
    vdb = VectorDatabase(
        embedding_client=embedder,
        db_path=settings.VECTOR_DB_PATH,
        index_type=settings.FAISS_INDEX_TYPE,
    )

    print(f"当前状态: {vdb.get_statistics()}")
    build_knowledge_base(vdb, embedder=embedder, verbose=True)
    vdb.close()


if __name__ == "__main__":
    main()
