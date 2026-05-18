"""
TianwenAGI Harness - Evaluator基类与评测系统
多维评测指标，参考GAIA + ResearchBench设计
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import time
import logging

logger = logging.getLogger("harness.evaluator")


class MetricType(Enum):
    """指标类型"""
    # 准确性指标
    ACCURACY = "accuracy"
    F1_SCORE = "f1_score"
    PRECISION = "precision"
    RECALL = "recall"
    EXACT_MATCH = "exact_match"
    PARTIAL_MATCH = "partial_match"

    # 工具使用指标
    TOOL_SUCCESS_RATE = "tool_success_rate"
    TOOL_EFFICIENCY = "tool_efficiency"
    STEP_EFFICIENCY = "step_efficiency"

    # 推理指标
    REASONING_CHAINS = "reasoning_chains"
    ERROR_RECOVERY = "error_recovery"

    # 领域专业性指标
    DOMAIN_ACCURACY = "domain_accuracy"
    CONCEPT_UNDERSTANDING = "concept_understanding"
    SCIENTIFIC_VALIDITY = "scientific_validity"

    # 综合指标
    TASK_COMPLETION_RATE = "task_completion_rate"
    TIME_EFFICIENCY = "time_efficiency"
    TOKEN_EFFICIENCY = "token_efficiency"


@dataclass
class EvaluationConfig:
    """评测配置"""
    metrics: List[MetricType] = field(default_factory=list)
    grading_type: str = "automatic"   # automatic, human, hybrid
    tolerance: float = 0.05          # 数值容差
    timeout: int = 300               # 评测超时
    verbose: bool = True
    save_intermediate: bool = True    # 保存中间结果
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricScore:
    """单个指标得分"""
    name: str
    value: float
    max_value: float = 1.0
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def normalized(self) -> float:
        return self.value / self.max_value if self.max_value > 0 else 0.0


@dataclass
class EvaluationResult:
    """评测结果"""
    task_id: str
    agent_id: str
    success: bool
    overall_score: float = 0.0
    metric_scores: List[MetricScore] = field(default_factory=list)
    pass_count: int = 0
    total_count: int = 0
    execution_time: float = 0
    details: Dict[str, Any] = field(default_factory=dict)
    feedback: str = ""
    suggestions: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metric(self, metric: MetricScore):
        self.metric_scores.append(metric)

    def calculate_overall(self) -> float:
        """计算加权总分"""
        if not self.metric_scores:
            return 0.0

        total_weight = sum(m.weight for m in self.metric_scores)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(m.normalized * m.weight for m in self.metric_scores)
        self.overall_score = weighted_sum / (total_weight / len(self.metric_scores))
        return self.overall_score

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "overall_score": self.overall_score,
            "metrics": {m.name: {"value": m.value, "normalized": m.normalized} for m in self.metric_scores},
            "pass_count": self.pass_count,
            "total_count": self.total_count,
            "execution_time": self.execution_time,
            "feedback": self.feedback,
            "timestamp": self.timestamp,
        }


class BaseEvaluator(ABC):
    """
    评测器基类
    参考lm-evaluation-harness的评分器设计
    """

    def __init__(self, config: EvaluationConfig):
        self.config = config
        self._metric_registry: Dict[MetricType, Callable] = {}

    @abstractmethod
    async def evaluate(
        self,
        task_result: Any,  # TaskResult
        ground_truth: Any,
        reference_data: Dict[str, Any] = None
    ) -> EvaluationResult:
        """执行评测"""
        pass

    @abstractmethod
    async def aggregate(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """聚合多个评测结果"""
        pass

    def register_metric(self, metric_type: MetricType, handler: Callable):
        """注册指标处理器"""
        self._metric_registry[metric_type] = handler

    async def compute_metric(
        self,
        metric_type: MetricType,
        output: Any,
        expected: Any,
        **kwargs
    ) -> MetricScore:
        """计算单个指标"""
        if metric_type not in self._metric_registry:
            logger.warning(f"Metric {metric_type.value} not registered, using default")
            return MetricScore(name=metric_type.value, value=0.0)

        handler = self._metric_registry[metric_type]
        value = await handler(output, expected, **kwargs)
        return MetricScore(name=metric_type.value, value=value)


class AstronomicspecificEvaluator(BaseEvaluator):
    """天文领域专用评测器"""

    def __init__(self, config: EvaluationConfig):
        super().__init__(config)
        self._setup_metrics()

    def _setup_metrics(self):
        """设置天文专用指标"""
        self.register_metric(MetricType.SCIENTIFIC_VALIDITY, self._scientific_validity)
        self.register_metric(MetricType.DOMAIN_ACCURACY, self._domain_accuracy)

    async def _scientific_validity(self, output: Any, expected: Any, **kwargs) -> float:
        """科学有效性评分"""
        # 实现科学有效性检查
        if isinstance(output, str) and isinstance(expected, str):
            # 简单的科学概念匹配
            return 1.0 if output.strip() == expected.strip() else 0.0
        return 0.5

    async def _domain_accuracy(self, output: Any, expected: Any, **kwargs) -> float:
        """领域准确性评分"""
        return 0.0  # 需要具体实现

    async def evaluate(self, task_result: Any, ground_truth: Any, reference_data: Dict = None) -> EvaluationResult:
        """执行天文任务评测"""
        result = EvaluationResult(
            task_id=task_result.task_id if hasattr(task_result, 'task_id') else "unknown",
            agent_id=task_result.agent_id if hasattr(task_result, 'agent_id') else "unknown",
            success=task_result.success if hasattr(task_result, 'success') else False,
        )

        start = time.time()

        # 计算各指标
        for metric_type in self.config.metrics:
            score = await self.compute_metric(metric_type, task_result.output, ground_truth)
            result.add_metric(score)

        result.calculate_overall()
        result.execution_time = time.time() - start

        return result

    async def aggregate(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """聚合评测结果"""
        if not results:
            return {}

        total = len(results)
        pass_count = sum(1 for r in results if r.success)
        avg_score = sum(r.overall_score for r in results) / total

        # 按指标聚合
        metric_aggregates = {}
        for metric_type in MetricType:
            scores = [r.overall_score for r in results]  # 简化
            if scores:
                metric_aggregates[metric_type.value] = {
                    "mean": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores),
                }

        return {
            "total_tasks": total,
            "pass_count": pass_count,
            "pass_rate": pass_count / total if total > 0 else 0,
            "average_score": avg_score,
            "metrics": metric_aggregates,
        }
