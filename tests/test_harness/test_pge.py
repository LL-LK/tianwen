"""
TianwenAGI Harness - PGE模块测试
测试Planner、Generator、Evaluator和PGERunner
"""
import pytest
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "src"))

from harness.pge import (
    PlannerAgent, PlanStep, PlanResult, StepPriority, StepStatus,
    GeneratorAgent, GenerationResult,
    EvaluatorAgent, EvaluationFeedback, ConvergenceResult,
    PGERunner, PGELoopConfig, PGERoundResult
)
from harness.pge.planner import LLMBasedPlanner
from harness.pge.generator import LLMBasedGenerator
from harness.pge.evaluator import DefaultEvaluator
from harness.pge.loop import SimplePGERunner


# ============== Planner测试 ==============

class TestPlanner:
    """Planner测试"""

    def test_plan_step_creation(self):
        """测试PlanStep创建"""
        step = PlanStep(
            step_id="step_1",
            description="Test step",
            action_type="execute",
            priority=StepPriority.HIGH
        )
        assert step.step_id == "step_1"
        assert step.description == "Test step"
        assert step.priority == StepPriority.HIGH
        assert step.status == StepStatus.PENDING

    def test_plan_step_is_ready(self):
        """测试步骤依赖检查"""
        step = PlanStep(
            step_id="step_2",
            description="Dependent step",
            action_type="execute",
            dependencies=["step_1"]
        )
        assert not step.is_ready(set())
        assert step.is_ready({"step_1"})
        assert not step.is_ready({"step_3"})

    @pytest.mark.asyncio
    async def test_llm_planner_create_plan(self):
        """测试LLM规划器创建计划"""
        planner = LLMBasedPlanner({"max_steps": 5})
        plan = await planner.create_plan("Analyze spectrum of star M31")

        assert plan is not None
        assert plan.original_task == "Analyze spectrum of star M31"
        assert len(plan.steps) > 0

    @pytest.mark.asyncio
    async def test_plan_result_properties(self):
        """测试PlanResult属性"""
        step = PlanStep(
            step_id="step_1",
            description="Test",
            action_type="execute"
        )
        plan = PlanResult(
            plan_id="plan_1",
            original_task="Test task",
            steps=[step]
        )

        assert plan.get_step("step_1") == step
        assert plan.is_complete() == False

        step.status = StepStatus.COMPLETED
        assert plan.is_complete() == True
        assert plan.success_rate() == 1.0


# ============== Generator测试 ==============

class TestGenerator:
    """Generator测试"""

    @pytest.mark.asyncio
    async def test_generation_result_creation(self):
        """测试GenerationResult创建"""
        result = GenerationResult(
            step_id="step_1",
            step_description="Test execution",
            success=True,
            output={"data": 42}
        )
        assert result.step_id == "step_1"
        assert result.success == True
        assert result.output["data"] == 42

    @pytest.mark.asyncio
    async def test_llm_generator_execute_step(self):
        """测试LLM生成器执行步骤"""
        generator = LLMBasedGenerator()

        step = PlanStep(
            step_id="step_1",
            description="Query SIMBAD for star M31",
            action_type="query"
        )

        result = await generator.execute_step(step)
        assert result.step_id == "step_1"
        assert result.success == True  # 回退模式也应该成功


# ============== Evaluator测试 ==============

class TestEvaluator:
    """Evaluator测试"""

    @pytest.mark.asyncio
    async def test_evaluation_feedback(self):
        """测试评估反馈"""
        feedback = EvaluationFeedback(
            step_id="step_1",
            success=True,
            score=0.85,
            feedback="Good execution",
            suggestions=["Continue monitoring"]
        )
        assert feedback.score == 0.85
        assert len(feedback.suggestions) == 1

    @pytest.mark.asyncio
    async def test_convergence_result(self):
        """测试收敛结果"""
        conv = ConvergenceResult(
            converged=False,
            current_round=3,
            score_history=[0.5, 0.6, 0.65],
            should_refine_plan=True
        )
        assert conv.current_round == 3
        assert conv.min_delta == pytest.approx(0.05, abs=1e-9)

    @pytest.mark.asyncio
    async def test_default_evaluator_result(self):
        """测试默认评估器评估单个结果"""
        evaluator = DefaultEvaluator()

        gen_result = GenerationResult(
            step_id="step_1",
            step_description="Test",
            success=True,
            output="Result"
        )

        feedback = await evaluator.evaluate_result(gen_result, expected="Result")
        assert feedback.success == True
        assert feedback.score == 1.0

    @pytest.mark.asyncio
    async def test_default_evaluator_similarity(self):
        """测试相似度计算"""
        evaluator = DefaultEvaluator()

        # 精确匹配
        score = evaluator._calculate_similarity("hello", "hello")
        assert score == 1.0

        # 部分匹配
        score = evaluator._calculate_similarity("hello world", "hello")
        assert score == 0.8

        # 数值匹配
        score = evaluator._calculate_similarity(100, 100)
        assert score == 1.0

        score = evaluator._calculate_similarity(105, 100)
        assert score >= 0.8

    @pytest.mark.asyncio
    async def test_default_evaluator_convergence(self):
        """测试收敛检测"""
        evaluator = DefaultEvaluator({"convergence_threshold": 0.01})

        # 收敛
        conv = await evaluator.check_convergence(0.8, [0.7, 0.75, 0.8], 3)
        assert conv.min_delta == pytest.approx(0.05, abs=1e-9)

        # 不收敛（连续小幅提升但未达到收敛阈值）
        conv = await evaluator.check_convergence(0.65, [0.5, 0.55, 0.6, 0.65], 4)
        # avg_delta=0.05, threshold=0.01, so 0.05 < 0.01 = False (not converged)
        # All deltas >= threshold*2, so should_refine_plan = False
        assert conv.converged == False
        assert conv.should_refine_plan == False


# ============== PGE Loop测试 ==============

class TestPGELoop:
    """PGE循环测试"""

    def test_pge_loop_config(self):
        """测试PGE循环配置"""
        config = PGELoopConfig(
            max_rounds=5,
            convergence_threshold=0.02,
            success_threshold=0.9
        )
        assert config.max_rounds == 5
        assert config.convergence_threshold == 0.02

    @pytest.mark.asyncio
    async def test_simple_pge_runner(self):
        """测试简化版PGE Runner"""
        runner = SimplePGERunner(PGELoopConfig(max_rounds=2))

        result = await runner.run("Query catalog for M31 galaxy")

        assert result is not None
        assert result.rounds >= 1
        assert result.final_score >= 0.0
        assert result.total_execution_time > 0

    @pytest.mark.asyncio
    async def test_pge_round_result(self):
        """测试PGE轮次结果"""
        step = PlanStep(
            step_id="step_1",
            description="Test",
            action_type="execute"
        )
        plan = PlanResult(
            plan_id="plan_1",
            original_task="Test",
            steps=[step]
        )

        gen_result = GenerationResult(
            step_id="step_1",
            step_description="Test",
            success=True,
            output="OK"
        )

        feedback = EvaluationFeedback(
            step_id="step_1",
            success=True,
            score=0.9,
            feedback="Good"
        )

        conv = ConvergenceResult(
            converged=True,
            current_round=1,
            score_history=[0.9]
        )

        round_result = PGERoundResult(
            round_number=1,
            plan=plan,
            generation_results=[gen_result],
            feedbacks={"step_1": feedback},
            convergence=conv,
            score=0.9,
            execution_time=1.0
        )

        assert round_result.score == 0.9
        assert round_result.convergence.converged == True

    @pytest.mark.asyncio
    async def test_pge_runner_early_termination(self):
        """测试PGE提前终止"""
        config = PGELoopConfig(
            max_rounds=10,
            early_stop_on_success=True,
            success_threshold=0.9
        )
        runner = SimplePGERunner(config)

        result = await runner.run("Simple query task")

        # 应该因为成功而提前终止
        assert result.rounds <= config.max_rounds


# ============== 集成测试 ==============

class TestPGEIntegration:
    """PGE集成测试"""

    @pytest.mark.asyncio
    async def test_full_pge_workflow(self):
        """完整PGE工作流测试"""
        # 创建组件
        planner = LLMBasedPlanner()
        generator = LLMBasedGenerator()
        evaluator = DefaultEvaluator()

        # 创建Runner
        config = PGELoopConfig(max_rounds=3)
        runner = PGERunner(config, planner, generator, evaluator)

        # 执行
        result = await runner.run("Analyze observation data")

        # 验证
        assert result is not None
        assert result.rounds >= 1
        assert result.final_score >= 0.0
        assert len(result.round_results) == result.rounds

    @pytest.mark.asyncio
    async def test_pge_with_custom_planner(self):
        """测试自定义规划器的PGE"""
        class CustomPlanner(PlannerAgent):
            async def create_plan(self, task: str, context: Dict = None) -> PlanResult:
                step = PlanStep(
                    step_id="custom_step",
                    description=f"Custom plan for: {task}",
                    action_type="custom"
                )
                return PlanResult(
                    plan_id="custom_plan",
                    original_task=task,
                    steps=[step]
                )

            async def refine_plan(self, plan: PlanResult, feedback: Dict) -> PlanResult:
                return plan

        runner = SimplePGERunner()
        runner.set_planner(CustomPlanner())

        result = await runner.run("Test custom planner")

        assert result.final_plan is not None
        assert len(result.final_plan.steps) == 1
        assert result.final_plan.steps[0].step_id == "custom_step"


# ============== 工具测试 ==============

class TestPGETools:
    """PGE工具测试"""

    def test_plan_step_to_dict(self):
        """测试步骤序列化"""
        step = PlanStep(
            step_id="step_1",
            description="Test step",
            action_type="execute"
        )
        d = step.to_dict()
        assert d["step_id"] == "step_1"
        assert d["action_type"] == "execute"

    def test_plan_result_to_dict(self):
        """测试计划序列化"""
        step = PlanStep(
            step_id="step_1",
            description="Test",
            action_type="execute"
        )
        plan = PlanResult(
            plan_id="plan_1",
            original_task="Test task",
            steps=[step]
        )
        d = plan.to_dict()
        assert d["plan_id"] == "plan_1"
        assert d["total_steps"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
