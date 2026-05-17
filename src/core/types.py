"""
Core Types - 核心类型定义
提供 Hypothesis、HypothesisStatus 等核心枚举和类的统一接口

所有模块应从本模块导入 Hypothesis 和 HypothesisStatus，避免循环依赖。

使用方式:
    from src.core.types import Hypothesis, HypothesisStatus
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


# ============ 枚举定义 ============

class HypothesisStatus(Enum):
    """假说状态枚举"""
    PENDING = "pending"       # 待验证
    VERIFIED = "verified"     # 已验证
    REJECTED = "rejected"     # 已反驳
    REVISED = "revised"       # 已修订


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