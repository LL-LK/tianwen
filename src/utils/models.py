"""
Hermes-AGI Data Models - 统一数据模型定义
提供 Paper、Experience 等数据类的统一接口

该模块统一了原本分散在 vector_memory.py、memory_persistence.py 和
literature_researcher.py 中的数据类定义。
"""

from typing import Dict, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


@dataclass
class Paper:
    """论文数据模型 - 统一表示学术论文"""
    id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published_date: str
    updated_date: str
    citations: int = 0
    pdf_url: str = ""
    arxiv_url: str = ""
    relevance_score: float = 0.0
    related_ids: List[str] = field(default_factory=list)
    source: str = "unknown"  # 数据来源: arxiv, openalex, semantic_scholar

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "categories": self.categories,
            "published_date": self.published_date,
            "updated_date": self.updated_date,
            "citations": self.citations,
            "pdf_url": self.pdf_url,
            "arxiv_url": self.arxiv_url,
            "relevance_score": self.relevance_score,
            "related_ids": self.related_ids,
            "source": self.source,
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Paper':
        return Paper(**data)

    def to_search_text(self) -> str:
        """转换为搜索文本"""
        authors_str = ", ".join(self.authors[:3]) + (" et al." if len(self.authors) > 3 else "")
        return f"{self.title} {authors_str} {self.abstract}"


@dataclass
class Experience:
    """
    经验记录数据模型

    重要性评分 (importance_score):
    - 0.0-0.3: 低重要性，常规经验
    - 0.3-0.6: 中等重要性
    - 0.6-0.8: 高重要性
    - 0.8-1.0: 极高重要性

    计算因素:
    - 任务复杂度 (complexity)
    - 结果质量 (outcome)
    - 使用频率 (access_count)
    - 时间衰减 (recency)
    """
    id: str
    type: str  # 'success' | 'failure' | 'pattern'
    task_description: str
    solution: str
    skills_used: List[str]
    entities: List[Dict] = field(default_factory=list)
    intent: str = ""
    complexity: str = "medium"
    outcome: str = ""  # 'success' | 'partial' | 'failed'
    lessons_learned: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # 重要性评分系统
    importance_score: float = 0.5
    access_count: int = 0
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    success_weight: float = 1.0

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'Experience':
        return Experience(**data)

    def calculate_importance(self) -> float:
        """计算重要性评分"""
        try:
            import numpy as np
        except ImportError:
            return self.importance_score

        # 1. 基础分数 (outcome质量)
        outcome_scores = {"success": 1.0, "partial": 0.5, "failed": 0.3}
        base_score = outcome_scores.get(self.outcome, 0.5) * self.success_weight

        # 2. 复杂度加权
        complexity_weights = {"extreme": 1.5, "high": 1.2, "medium": 1.0, "low": 0.8}
        complexity_weight = complexity_weights.get(self.complexity.lower(), 1.0)
        base_score *= complexity_weight

        # 3. 使用频率加成
        access_bonus = min(0.2, 0.1 * np.log(1 + self.access_count))

        # 4. 时间衰减因子
        try:
            last_access_dt = datetime.fromisoformat(self.last_accessed)
            days_ago = (datetime.now() - last_access_dt).days
            recency_factor = np.exp(-days_ago / 90)
        except Exception:
            recency_factor = 0.5

        final_score = base_score + access_bonus
        final_score *= (0.7 + 0.3 * recency_factor)
        final_score = min(1.0, max(0.0, final_score))

        return round(final_score, 3)

    def record_access(self):
        """记录一次访问，更新重要性"""
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.importance_score = self.calculate_importance()


# 简单版本 Experience (用于 memory_persistence.py 的兼容版本)
@dataclass
class SimpleExperience:
    """简化版经验记录"""
    id: str
    type: str
    task_description: str
    solution: str
    skills_used: List[str]
    entities: List[Dict] = field(default_factory=list)
    intent: str = ""
    complexity: str = "medium"
    outcome: str = ""
    lessons_learned: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'SimpleExperience':
        return SimpleExperience(**data)


class HypothesisStatus(Enum):
    """假说状态枚举"""
    PENDING = "pending"
    TESTING = "testing"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Hypothesis:
    """假说数据模型 - 结构化科学假说"""
    id: str
    content: str
    confidence: float = 0.5
    status: HypothesisStatus = HypothesisStatus.PENDING
    evidence: List[str] = field(default_factory=list)
    source: str = ""
    premises: List[str] = field(default_factory=list)
    predictions: List[str] = field(default_factory=list)
    verification_method: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def statement(self) -> str:
        return self.content

    @statement.setter
    def statement(self, value: str):
        self.content = value

    @property
    def properties(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "statement": self.content,
            "confidence": self.confidence,
            "status": self.status.value,
            "evidence": self.evidence,
            "source": self.source,
            "premises": self.premises,
            "predictions": self.predictions,
            "verification_method": self.verification_method,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'Hypothesis':
        status = data.pop('status', 'pending')
        if isinstance(status, str):
            status = HypothesisStatus(status)
        return Hypothesis(status=status, **data)
