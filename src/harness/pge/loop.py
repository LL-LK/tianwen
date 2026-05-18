"""
TianwenAGI Harness - PGERunner
PGE迭代循环：执行Planner-Generator-Evaluator直到收敛或达到最大轮次
参考harnessa的PGE架构设计
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Type
import logging
import asyncio
import time
import uuid

from .planner import PlannerAgent, PlanResult, PlanStep
from .generator import GeneratorAgent, GenerationResult
from .evaluator import EvaluatorAgent, EvaluationFeedback, ConvergenceResult

logger = logging.getLogger("harness.pge.loop")


@dataclass
class PGELoopConfig:
    """PGE循环配置"""
    max_rounds: int = 10                    # 最大迭代轮次
    convergence_threshold: float = 0.01     # 收敛阈值
    convergence_patience: int = 2           # 收敛等待轮次
    enable_plan_refinement: bool = True     # 是否启用计划优化
    early_stop_on_success: bool = True      # 成功后提前停止
    success_threshold: float = 0.9           # 成功阈值
    save_intermediate_results: bool = True  # 保存中间结果
    verbose: bool = True                    # 详细输出
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PGERoundResult:
    """单轮执行结果"""
    round_number: int
    plan: PlanResult
    generation_results: List[GenerationResult]
    feedbacks: Dict[str, EvaluationFeedback]
    convergence: ConvergenceResult
    score: float
    execution_time: float
    refinements_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "round": self.round_number,
            "plan_id": self.plan.plan_id,
            "score": self.score,
            "converged": self.convergence.converged,
            "execution_time": self.execution_time,
            "steps_completed": len([r for r in self.generation_results if r.success]),
            "steps_total": len(self.generation_results),
        }


@dataclass 
class PGEFinalResult:
    """PGE最终结果"""
    task: str
    success: bool
    final_score: float
    rounds: int
    round_results: List[PGERoundResult]
    total_execution_time: float
    final_plan: Optional[PlanResult]
    final_results: List[GenerationResult]
    converged: bool
    early_terminated: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "success": self.success,
            "final_score": self.final_score,
            "rounds": self.rounds,
            "total_execution_time": self.total_execution_time,
            "converged": self.converged,
            "early_terminated": self.early_terminated,
            "timestamp": self.timestamp,
        }


class PGERunner:
    """
    PGE迭代循环执行器
    协调Planner、Generator、Evaluator进行迭代执行
    """

    def __init__(
        self,
        config: PGELoopConfig = None,
        planner: PlannerAgent = None,
        generator: GeneratorAgent = None,
        evaluator: EvaluatorAgent = None
    ):
        self.config = config or PGELoopConfig()
        self.planner = planner
        self.generator = generator
        self.evaluator = evaluator
        self._hooks: Dict[str, Callable] = {}
        self._score_history: List[float] = []

    def set_planner(self, planner: PlannerAgent):
        """设置规划器"""
        self.planner = planner

    def set_generator(self, generator: GeneratorAgent):
        """设置生成器"""
        self.generator = generator

    def set_evaluator(self, evaluator: EvaluatorAgent):
        """设置评估器"""
        self.evaluator = evaluator

    def register_hook(self, name: str, hook: Callable):
        """注册钩子函数"""
        self._hooks[name] = hook

    async def _call_hooks(self, name: str, *args, **kwargs):
        """调用钩子"""
        if name in self._hooks:
            hook = self._hooks[name]
            if asyncio.iscoroutinefunction(hook):
                return await hook(*args, **kwargs)
            return hook(*args, **kwargs)

    async def run(self, task: str, context: Dict[str, Any] = None) -> PGEFinalResult:
        """
        运行PGE循环
        Args:
            task: 要执行的任务
            context: 执行上下文
        Returns:
            PGEFinalResult: 最终结果
        """
        context = context or {}
        start_time = time.time()
        task_id = str(uuid.uuid4())[:12]

        if self.config.verbose:
            logger.info(f"[{task_id}] Starting PGE loop for task: {task[:100]}...")

        round_results: List[PGERoundResult] = []
        current_plan: Optional[PlanResult] = None
        current_results: List[GenerationResult] = []
        converged = False
        early_terminated = False
        error = None

        try:
            for round_num in range(1, self.config.max_rounds + 1):
                round_start = time.time()

                if self.config.verbose:
                    logger.info(f"[{task_id}] Round {round_num}/{self.config.max_rounds}")

                # 调用前置钩子
                await self._call_hooks("pre_round", round_num, current_plan)

                # === PLANNING PHASE ===
                if round_num == 1 or current_plan is None or self.config.enable_plan_refinement:
                    if current_plan is not None and round_num > 1:
                        # 使用上一轮反馈优化计划
                        if self.config.verbose:
                            logger.info(f"[{task_id}] Refining plan from previous round")
                        current_plan = await self._refine_plan(current_plan, round_results[-1])
                    else:
                        # 首次规划
                        current_plan = await self._create_plan(task, context)

                    if current_plan is None or not current_plan.steps:
                        error = "Failed to create plan"
                        break

                # === GENERATION PHASE ===
                current_results = await self._execute_plan(current_plan, context)

                # === EVALUATION PHASE ===
                feedbacks, convergence = await self._evaluate_and_check_convergence(
                    current_plan, current_results, round_num
                )

                # 计算本轮得分
                if feedbacks:
                    round_score = sum(f.score for f in feedbacks.values()) / len(feedbacks)
                else:
                    round_score = 0.0

                self._score_history.append(round_score)

                round_time = time.time() - round_start

                # 记录本轮结果
                round_result = PGERoundResult(
                    round_number=round_num,
                    plan=current_plan,
                    generation_results=current_results,
                    feedbacks=feedbacks,
                    convergence=convergence,
                    score=round_score,
                    execution_time=round_time,
                )
                round_results.append(round_result)

                if self.config.verbose:
                    logger.info(
                        f"[{task_id}] Round {round_num} complete: "
                        f"score={round_score:.4f}, converged={convergence.converged}, "
                        f"time={round_time:.2f}s"
                    )

                # === CONVERGENCE CHECK ===
                if convergence.converged:
                    if self.config.verbose:
                        logger.info(f"[{task_id}] Converged at round {round_num}")
                    converged = True
                    break

                # === EARLY TERMINATION CHECK ===
                if self.config.early_stop_on_success and round_score >= self.config.success_threshold:
                    if self.config.verbose:
                        logger.info(f"[{task_id}] Success threshold reached ({round_score:.4f} >= {self.config.success_threshold})")
                    early_terminated = True
                    break

                # === REFINE PLAN IF NEEDED ===
                if convergence.should_refine_plan and self.config.enable_plan_refinement:
                    if self.config.verbose:
                        logger.info(f"[{task_id}] Applying plan refinements")
                    refinements = convergence.refinement_suggestions
                    round_result.refinements_applied = refinements

                # 调用后置钩子
                await self._call_hooks("post_round", round_num, round_result)

            # 计算最终结果
            final_score = self._score_history[-1] if self._score_history else 0.0
            success = final_score >= self.config.success_threshold or converged

            return PGEFinalResult(
                task=task,
                success=success,
                final_score=final_score,
                rounds=len(round_results),
                round_results=round_results,
                total_execution_time=time.time() - start_time,
                final_plan=current_plan,
                final_results=current_results,
                converged=converged,
                early_terminated=early_terminated,
                metadata={"task_id": task_id}
            )

        except Exception as e:
            logger.error(f"[{task_id}] PGE loop error: {e}")
            error = str(e)
            return PGEFinalResult(
                task=task,
                success=False,
                final_score=self._score_history[-1] if self._score_history else 0.0,
                rounds=len(round_results),
                round_results=round_results,
                total_execution_time=time.time() - start_time,
                final_plan=current_plan,
                final_results=current_results,
                converged=False,
                early_terminated=False,
                error=error,
                metadata={"task_id": task_id}
            )

    async def _create_plan(self, task: str, context: Dict) -> Optional[PlanResult]:
        """创建计划"""
        if self.planner is None:
            # 默认规划器
            from .planner import LLMBasedPlanner
            self.planner = LLMBasedPlanner()

        try:
            plan = await self.planner.create_plan(task, context)
            return plan
        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            return None

    async def _refine_plan(self, plan: PlanResult, last_result: PGERoundResult) -> PlanResult:
        """优化计划"""
        if self.planner is None:
            return plan

        # 构建反馈
        feedback = {
            "last_score": last_result.score,
            "feedbacks": {k: v.to_dict() for k, v in last_result.feedbacks.items()},
            "convergence": last_result.convergence.to_dict(),
        }

        try:
            refined_plan = await self.planner.refine_plan(plan, feedback)
            return refined_plan
        except Exception as e:
            logger.warning(f"Plan refinement failed: {e}, using original plan")
            return plan

    async def _execute_plan(self, plan: PlanResult, context: Dict) -> List[GenerationResult]:
        """执行计划"""
        if self.generator is None:
            # 默认生成器
            from .generator import LLMBasedGenerator
            self.generator = LLMBasedGenerator()

        try:
            results = await self.generator.execute_plan(plan.steps, context)
            return results
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            return []

    async def _evaluate_and_check_convergence(
        self,
        plan: PlanResult,
        results: List[GenerationResult],
        round_num: int
    ) -> tuple:
        """评估并检查收敛"""
        if self.evaluator is None:
            from .evaluator import DefaultEvaluator
            self.evaluator = DefaultEvaluator()

        feedbacks, convergence = await self.evaluator.evaluate_and_converge(
            plan, results, self._score_history, round_num
        )

        return feedbacks, convergence


class SimplePGERunner(PGERunner):
    """
    简化版PGE Runner
    使用默认的Planner、Generator、Evaluator
    """

    def __init__(self, config: PGELoopConfig = None):
        super().__init__(config)
        from .planner import LLMBasedPlanner
        from .generator import LLMBasedGenerator
        from .evaluator import DefaultEvaluator

        self.planner = LLMBasedPlanner()
        self.generator = LLMBasedGenerator()
        self.evaluator = DefaultEvaluator()
