"""
Hermes-AGI Vector Store - 统一向量存储基类
提供 SimpleVectorStore 和 ChromaDBVectorStore 的统一接口

该模块统一了原本分散在 vector_memory.py、memory_persistence.py 和
literature_researcher.py 中的向量存储实现。
"""

import json
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from dataclasses import dataclass, field


class BaseVectorStore(ABC):
    """向量存储基类"""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    @abstractmethod
    def add(self, text: str, embedding: List[float], metadata: Dict = None):
        """添加向量"""
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], k: int = 5) -> List[Dict]:
        """搜索相似向量"""
        pass

    @abstractmethod
    def count(self) -> int:
        """返回向量数量"""
        pass

    @abstractmethod
    def save(self, path: str):
        """保存到文件"""
        pass

    @abstractmethod
    def load(self, path: str):
        """从文件加载"""
        pass

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)


class SimpleVectorStore(BaseVectorStore):
    """
    简单向量存储实现 - 基于余弦相似度

    支持:
    - 向量添加和语义搜索
    - 持久化存储
    - 基于文件的数据恢复
    """

    def __init__(self, dimension: int = 384):
        super().__init__(dimension)
        self.vectors: List[List[float]] = []
        self.metadata: List[Dict] = []
        self.texts: List[str] = []

    def add(self, text: str, embedding: List[float], metadata: Dict = None):
        """添加向量"""
        self.vectors.append(embedding)
        self.texts.append(text)
        self.metadata.append(metadata or {})

    def search(self, query_embedding: List[float], k: int = 5) -> List[Dict]:
        """搜索相似向量"""
        scores = []
        for i, vec in enumerate(self.vectors):
            score = self._cosine_similarity(query_embedding, vec)
            scores.append((i, score))

        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:k]:
            results.append({
                "text": self.texts[idx],
                "score": float(score),
                "metadata": self.metadata[idx],
            })
        return results

    def count(self) -> int:
        return len(self.vectors)

    def save(self, path: str):
        """保存到文件"""
        data = {
            "dimension": self.dimension,
            "vectors": self.vectors,
            "metadata": self.metadata,
            "texts": self.texts,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self, path: str):
        """从文件加载"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.dimension = data["dimension"]
        self.vectors = data["vectors"]
        self.metadata = data["metadata"]
        self.texts = data["texts"]


# 向后兼容别名
VectorStore = SimpleVectorStore


# ============================================================================
# ChromaDBVectorStore - 从 vector_rag.py 导入或创建封装
# ============================================================================

try:
    from vector_rag import ChromaVectorStore as _ChromaVectorStore, HAS_CHROMADB, HAS_SENTENCE_TRANSFORMERS, DEFAULT_EMBEDDING_MODEL

    class ChromaDBVectorStore:
        """
        ChromaDB向量存储包装器 - 提供统一的接口

        功能:
        - 基于ChromaDB的向量存储和相似性检索
        - RAG增强的文献调研功能
        - 支持增量索引和备份恢复
        """

        def __init__(
            self,
            persist_directory: str = "runtime/data/chroma_db",
            embedding_model: str = DEFAULT_EMBEDDING_MODEL
        ):
            self._store = _ChromaVectorStore(persist_directory, embedding_model)
            self._is_initialized = False

        async def initialize(self) -> bool:
            """初始化向量存储"""
            result = await self._store.initialize()
            self._is_initialized = result
            return result

        async def add_documents(
            self,
            documents: List[str],
            metadatas: List[Dict],
            ids: List[str],
            skip_existing: bool = True
        ) -> bool:
            """添加文档到向量存储"""
            return await self._store.add_documents(documents, metadatas, ids, skip_existing)

        async def similarity_search(
            self,
            query: str,
            n_results: int = 5,
            filter_metadata: Optional[Dict] = None
        ) -> List[Dict]:
            """相似性搜索"""
            return await self._store.similarity_search(query, n_results, filter_metadata)

        async def delete_documents(self, ids: List[str]) -> bool:
            """删除指定ID的文档"""
            return await self._store.delete_documents(ids)

        async def get_collection_stats(self) -> Dict:
            """获取集合统计信息"""
            return await self._store.get_collection_stats()

        @property
        def is_initialized(self) -> bool:
            """检查是否已初始化"""
            return self._is_initialized

        def get_backup_manager(self):
            """获取备份管理器"""
            return self._store.get_backup_manager()

        def get_incremental_indexer(self):
            """获取增量索引器"""
            return self._store.get_incremental_indexer()

except ImportError:
    # 如果 vector_rag 不可用，提供降级实现
    HAS_CHROMADB = False

    class ChromaDBVectorStore:
        """ChromaDB向量存储 - 降级版本（ChromaDB未安装）"""

        def __init__(self, persist_directory: str = "runtime/data/chroma_db",
                     embedding_model: str = "all-MiniLM-L6-v2"):
            self._persist_directory = persist_directory
            self._embedding_model = embedding_model
            self._is_initialized = False
            print("警告: ChromaDB未安装，使用降级版本。功能将受限。")

        async def initialize(self) -> bool:
            self._is_initialized = False
            return False

        async def add_documents(self, documents, metadatas, ids, skip_existing=True) -> bool:
            return False

        async def similarity_search(self, query, n_results=5, filter_metadata=None) -> List[Dict]:
            return []

        async def delete_documents(self, ids: List[str]) -> bool:
            return False

        async def get_collection_stats(self) -> Dict:
            return {"error": "ChromaDB未安装"}

        @property
        def is_initialized(self) -> bool:
            return self._is_initialized

        def get_backup_manager(self):
            return None

        def get_incremental_indexer(self):
            return None
