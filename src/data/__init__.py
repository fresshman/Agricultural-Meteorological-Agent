# -*- coding: utf-8 -*-
"""数据层导出（延迟加载）。

faiss / jieba 这类重依赖只在真正用到时才导入：
只用 WeatherProcessor 的地方（气象、农场接口）不该被向量库的导入问题连带拖死。
"""
from importlib import import_module

_EXPORTS = {
    "WeatherProcessor": ".weather_processor",
    "VectorDatabase": ".vector_db",
    "Document": ".vector_db",
    "FAISSVectorStore": ".vector_db",
    "SmartChunker": ".chunker",
    "ChunkMethod": ".chunker",
    "ChunkResult": ".chunker",
    "TextCleaner": ".cleaner",
    "CleanResult": ".cleaner",
    "KeywordExtractor": ".keyword_extract",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value
