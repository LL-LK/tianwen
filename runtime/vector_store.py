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
