"""
Hermes-AGI Data Models - 统一数据模型定义
提供 Paper、Experience、Hypothesis、TestResult、Discovery 等数据类的统一接口

该模块统一了原本分散在各个模块中的数据类定义，确保数据流类型一致。

使用方式:
    from src.data.models import Hypothesis, HypothesisStatus, TestResult, Discovery
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple


# ============ 枚举定义 ============

class HypothesisStatus(Enum):
    """假说状态枚举"""
    PENDING = "pending"       # 待验证
    VERIFIED = "verified"     # 已验证
    REJECTED = "rejected"     # 已反驳
    REVISED = "revised"       # 已修订


class TestStatus(Enum):
    """测试结果状态枚举"""
    CONFIRMED = "confirmed"       # 证实
    REJECTED = "rejected"        # 证伪
    INCONCLUSIVE = "inconclusive" # 不确定
    REVISED = "revised"          # 需要修订


class DiscoveryStatus(Enum):
    """发现状态枚举"""
    PRELIMINARY = "preliminary"   # 初步发现
    CONFIRMED = "confirmed"       # 已确认
    REJECTED = "rejected"         # 已否定


# ============ 核心数据类 ============

@dataclass
class Hypothesis:
    """
    结构化假说格式 (Structured Hypothesis Format)

    Attributes:
        id: 假说唯一标识
        content: 假说核心内容
        confidence: 置信度 (0-1)
        status: 假说状态
        evidence: 支持证据列表
        source: 假说来源 (literature/data_mining/observation)
    """
    id: str
    content: str
    confidence: float
    status: HypothesisStatus
    evidence: List[str] = field(default_factory=list)
    source: str = ""

    # 扩展字段
    premises: List[str] = field(default_factory=list)        # 支撑前提
    predictions: List[str] = field(default_factory=list)       # 可检验预测
    verification_method: str = ""                             # 验证方法

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "confidence": self.confidence,
            "status": self.status.value if isinstance(self.status, HypothesisStatus) else self.status,
            "evidence": self.evidence,
            "source": self.source,
            "premises": self.premises,
            "predictions": self.predictions,
            "verification_method": self.verification_method
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Hypothesis':
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = HypothesisStatus(status)
        return Hypothesis(
            id=data["id"],
            content=data["content"],
            confidence=data.get("confidence", 0.5),
            status=status,
            evidence=data.get("evidence", []),
            source=data.get("source", ""),
            premises=data.get("premises", []),
            predictions=data.get("predictions", []),
            verification_method=data.get("verification_method", "")
        )


@dataclass
class TestResult:
    """
    测试结果数据类

    Attributes:
        hypothesis_id: 关联的假说ID
        passed: 是否通过
        details: 测试详情
        confidence: 置信度变化
    """
    hypothesis_id: str
    passed: bool
    details: Dict[str, Any]
    confidence: float

    # 扩展字段
    status: TestStatus = TestStatus.INCONCLUSIVE
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    confidence_interval: Optional[Tuple[float, float]] = None
    cross_validation_score: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "passed": self.passed,
            "details": self.details,
            "confidence": self.confidence,
            "status": self.status.value if isinstance(self.status, TestStatus) else self.status,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "confidence_interval": self.confidence_interval,
            "cross_validation_score": self.cross_validation_score
        }

    @staticmethod
    def from_dict(data: Dict) -> 'TestResult':
        status = data.get("status", "inconclusive")
        if isinstance(status, str):
            status = TestStatus(status)
        return TestResult(
            hypothesis_id=data["hypothesis_id"],
            passed=data.get("passed", False),
            details=data.get("details", {}),
            confidence=data.get("confidence", 0.0),
            status=status,
            evidence_for=data.get("evidence_for", []),
            evidence_against=data.get("evidence_against", []),
            confidence_interval=data.get("confidence_interval"),
            cross_validation_score=data.get("cross_validation_score")
        )


@dataclass
class Discovery:
    """
    发现数据类

    Attributes:
        id: 发现唯一标识
        description: 发现描述
        significance: 重要性评分 (0-1)
        source_hypothesis_id: 来源假说ID
        timestamp: 发现时间
    """
    id: str
    description: str
    significance: float
    source_hypothesis_id: str
    timestamp: str

    # 扩展字段
    status: DiscoveryStatus = DiscoveryStatus.PRELIMINARY
    supporting_evidence: List[str] = field(default_factory=list)
    related_discoveries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "significance": self.significance,
            "source_hypothesis_id": self.source_hypothesis_id,
            "timestamp": self.timestamp,
            "status": self.status.value if isinstance(self.status, DiscoveryStatus) else self.status,
            "supporting_evidence": self.supporting_evidence,
            "related_discoveries": self.related_discoveries
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Discovery':
        status = data.get("status", "preliminary")
        if isinstance(status, str):
            status = DiscoveryStatus(status)
        return Discovery(
            id=data["id"],
            description=data["description"],
            significance=data.get("significance", 0.5),
            source_hypothesis_id=data.get("source_hypothesis_id", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            status=status,
            supporting_evidence=data.get("supporting_evidence", []),
            related_discoveries=data.get("related_discoveries", [])
        )


# ============ 兼容性别名 ============

# 为了兼容旧代码，提供别名
ObservationPlan = Dict  # 观测计划类型


# ============ 已有数据类保持兼容 ============

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
    source: str = "unknown"

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
        authors_str = ", ".join(self.authors[:3]) + (" et al." if len(self.authors) > 3 else "")
        return f"{self.title} {authors_str} {self.abstract}"


@dataclass
class Experience:
    """经验记录数据模型"""
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
        try:
            import numpy as np
        except ImportError:
            return self.importance_score

        outcome_scores = {"success": 1.0, "partial": 0.5, "failed": 0.3}
        base_score = outcome_scores.get(self.outcome, 0.5) * self.success_weight

        complexity_weights = {"extreme": 1.5, "high": 1.2, "medium": 1.0, "low": 0.8}
        complexity_weight = complexity_weights.get(self.complexity.lower(), 1.0)
        base_score *= complexity_weight

        access_bonus = min(0.2, 0.1 * np.log(1 + self.access_count))

        try:
            last_access_dt = datetime.fromisoformat(self.last_accessed)
            days_ago = (datetime.now() - last_access_dt).days
            recency_factor = np.exp(-days_ago / 90)
        except:
            recency_factor = 0.5

        final_score = base_score + access_bonus
        final_score *= (0.7 + 0.3 * recency_factor)
        final_score = min(1.0, max(0.0, final_score))

        return round(final_score, 3)

    def record_access(self):
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.importance_score = self.calculate_importance()


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
