"""
TianwenAGI Harness - EvaluatorAgent
结果评估器：评估执行结果并提供反馈
参考harnessa的PGE架构设计
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
import logging
import asyncio
import numpy as np

from .planner import PlanResult, PlanStep, StepStatus
from .generator import GenerationResult

logger = logging.getLogger("harness.pge.evaluator")


@dataclass
class EvaluationFeedback:
    """评估反馈"""
    step_id: str
    success: bool
    score: float  # 0.0 - 1.0
    feedback: str
    suggestions: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "success": self.success,
            "score": self.score,
            "feedback": self.feedback,
            "suggestions": self.suggestions,
            "metrics": self.metrics,
        }


@dataclass
class ConvergenceResult:
    """收敛检测结果"""
    converged: bool
    current_round: int
    score_history: List[float] = field(default_factory=list)
    delta_threshold: float = 0.01
    min_delta: float = 0.0
    should_refine_plan: bool = False
    refinement_suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if len(self.score_history) >= 2:
            self.min_delta = abs(self.score_history[-1] - self.score_history[-2])

    def to_dict(self) -> Dict:
        return {
            "converged": self.converged,
            "current_round": self.current_round,
            "score_history": self.score_history,
            "min_delta": self.min_delta,
            "delta_threshold": self.delta_threshold,
            "should_refine_plan": self.should_refine_plan,
        }


class EvaluatorAgent(ABC):
    """
    结果评估器基类
    评估执行结果并决定是否继续迭代
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.convergence_threshold = self.config.get("convergence_threshold", 0.01)
        self.max_delta_history = self.config.get("max_delta_history", 5)
        self._metric_handlers: Dict[str, Callable] = {}

    def register_metric(self, name: str, handler: Callable):
        """注册指标处理器"""
        self._metric_handlers[name] = handler

    @abstractmethod
    async def evaluate_result(
        self,
        result: GenerationResult,
        expected: Any = None,
        context: Dict[str, Any] = None
    ) -> EvaluationFeedback:
        """
        评估单个执行结果
        Args:
            result: 执行结果
            expected: 期望结果（可选）
            context: 上下文信息
        Returns:
            EvaluationFeedback: 评估反馈
        """
        pass

    @abstractmethod
    async def evaluate_plan_results(
        self,
        plan: PlanResult,
        results: List[GenerationResult],
        context: Dict[str, Any] = None
    ) -> Dict[str, EvaluationFeedback]:
        """
        评估整个计划的执行结果
        Args:
            plan: 原始计划
            results: 所有步骤的执行结果
            context: 上下文信息
        Returns:
            Dict[str, EvaluationFeedback]: 每步的评估反馈
        """
        pass

    @abstractmethod
    async def check_convergence(
        self,
        current_score: float,
        score_history: List[float],
        round_num: int
    ) -> ConvergenceResult:
        """
        检查是否收敛
        Args:
            current_score: 当前得分
            score_history: 得分历史
            round_num: 当前轮次
        Returns:
            ConvergenceResult: 收敛检测结果
        """
        pass

    async def evaluate_and_converge(
        self,
        plan: PlanResult,
        results: List[GenerationResult],
        score_history: List[float],
        round_num: int,
        context: Dict[str, Any] = None
    ) -> tuple:
        """
        评估并检查收敛
        Returns:
            (feedbacks, convergence_result)
        """
        # 评估结果
        feedbacks = await self.evaluate_plan_results(plan, results, context)

        # 计算总体得分
        if feedbacks:
            current_score = sum(f.score for f in feedbacks.values()) / len(feedbacks)
        else:
            current_score = 0.0

        # 更新历史
        new_history = score_history + [current_score]
        if len(new_history) > self.max_delta_history:
            new_history = new_history[-self.max_delta_history:]

        # 检查收敛
        convergence = await self.check_convergence(current_score, new_history, round_num)

        return feedbacks, convergence


class DefaultEvaluator(EvaluatorAgent):
    """
    默认评估器
    提供基础的评估和收敛检测实现
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.tolerance = self.config.get("tolerance", 0.05)
        self.patience = self.config.get("patience", 2)  # 连续多少次不提升才认为收敛

    async def evaluate_result(
        self,
        result: GenerationResult,
        expected: Any = None,
        context: Dict[str, Any] = None
    ) -> EvaluationFeedback:
        """评估单个结果"""
        if not result.success:
            return EvaluationFeedback(
                step_id=result.step_id,
                success=False,
                score=0.0,
                feedback="Execution failed",
                suggestions=["Check the error message", "Verify input parameters"]
            )

        # 简单的相似度评估
        if expected is not None:
            score = self._calculate_similarity(result.output, expected)
        else:
            score = 0.8 if result.output else 0.5

        feedback = "Good" if score > 0.7 else "Needs improvement"

        return EvaluationFeedback(
            step_id=result.step_id,
            success=True,
            score=score,
            feedback=feedback,
            suggestions=["Continue"] if score > 0.7 else ["Consider refining approach"],
            metrics={"execution_time": result.execution_time}
        )

    async def evaluate_plan_results(
        self,
        plan: PlanResult,
        results: List[GenerationResult],
        context: Dict[str, Any] = None
    ) -> Dict[str, EvaluationFeedback]:
        """评估所有结果"""
        feedbacks = {}
        expected = context.get("expected") if context else None

        for result in results:
            feedback = await self.evaluate_result(result, expected, context)
            feedbacks[result.step_id] = feedback

        return feedbacks

    async def check_convergence(
        self,
        current_score: float,
        score_history: List[float],
        round_num: int
    ) -> ConvergenceResult:
        """检查收敛"""
        suggestions = []

        if len(score_history) < 2:
            return ConvergenceResult(
                converged=False,
                current_round=round_num,
                score_history=score_history,
                should_refine_plan=False
            )

        # 计算变化
        deltas = [abs(score_history[i] - score_history[i-1]) for i in range(1, len(score_history))]
        avg_delta = sum(deltas) / len(deltas) if deltas else float('inf')
        recent_delta = abs(score_history[-1] - score_history[-2]) if len(score_history) >= 2 else float('inf')

        # 收敛条件
        converged = avg_delta < self.convergence_threshold

        # 检查是否需要重规划
        should_refine = False
        if not converged and len(score_history) >= 3:
            # 连续多次没有显著提升
            if all(d < self.convergence_threshold * 2 for d in deltas[-self.patience:]):
                should_refine = True
                suggestions.append("Score plateau detected, consider refining the plan")

        if current_score < 0.5 and round_num > 2:
            should_refine = True
            suggestions.append("Low score after multiple rounds, consider alternative approach")

        return ConvergenceResult(
            converged=converged,
            current_round=round_num,
            score_history=score_history,
            min_delta=recent_delta,
            should_refine_plan=should_refine,
            refinement_suggestions=suggestions,
            metadata={"avg_delta": avg_delta}
        )

    def _calculate_similarity(self, output: Any, expected: Any) -> float:
        """计算相似度"""
        if output == expected:
            return 1.0

        if isinstance(output, str) and isinstance(expected, str):
            # 简单的字符串相似度
            output_lower = output.lower().strip()
            expected_lower = expected.lower().strip()

            if output_lower == expected_lower:
                return 1.0
            elif expected_lower in output_lower:
                return 0.8
            else:
                # 简单的词重叠
                output_words = set(output_lower.split())
                expected_words = set(expected_lower.split())
                if expected_words:
                    overlap = len(output_words & expected_words) / len(expected_words)
                    return overlap * 0.7  # 降低权重
                return 0.0

        if isinstance(output, (int, float)) and isinstance(expected, (int, float)):
            # 数值相似度
            if expected == 0:
                return 1.0 if output == 0 else 0.0
            diff = abs(output - expected) / abs(expected)
            if diff < self.tolerance:
                return 1.0
            elif diff < self.tolerance * 2:
                return 0.8
            elif diff < 0.5:
                return 0.5

        # 默认相似度
        return 0.5
