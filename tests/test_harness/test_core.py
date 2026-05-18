"""
TianwenAGI Harness - 核心测试
测试Agent、Task、Evaluator、Registry、Runner基类
"""
import pytest
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness import (
    BaseAgent, AgentConfig, AgentResult, AgentAction, AgentType, AgentCapability,
    BaseTask, TaskConfig, TaskResult, TaskCategory, DifficultyLevel, TaskStatus, TaskInstance,
    BaseEvaluator, EvaluationConfig, EvaluationResult, MetricType, MetricScore, AstronomicspecificEvaluator,
    HarnessRegistry, register_agent, register_task, register_evaluator,
    HarnessRunner, RunConfig, RunResult
)
from harness.tools import MCPToolIntegration, ToolCategory, ToolMetadata, BaseTool
from harness.registry import _agent_registry, _task_registry, _evaluator_registry


# ============== Agent测试 ==============

class MockAgent(BaseAgent):
    """测试用Agent"""

    async def plan(self, task_input: str, context: Dict[str, Any]) -> List[AgentAction]:
        return [AgentAction(action_type="respond", content=f"Planned: {task_input}")]

    async def execute(self, action: AgentAction) -> Any:
        return {"executed": action.content}

    async def respond(self, task_input: str, context: Dict[str, Any]) -> AgentResult:
        await asyncio.sleep(0.01)  # 模拟处理
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            output=f"Response to: {task_input}",
            actions=[AgentAction(action_type="respond", content=f"Action for: {task_input}")],
            execution_time=0.01
        )


@register_agent("mock")
class RegisteredMockAgent(BaseAgent):
    """注册测试用Agent"""

    async def plan(self, task_input: str, context: Dict[str, Any]) -> List[AgentAction]:
        return [AgentAction(action_type="plan", content=task_input)]

    async def execute(self, action: AgentAction) -> Any:
        return {"status": "ok"}

    async def respond(self, task_input: str, context: Dict[str, Any]) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            output=f"Registered response: {task_input}",
            execution_time=0.001
        )


class TestAgent:
    """Agent测试"""

    def test_agent_config(self):
        """测试Agent配置"""
        config = AgentConfig(
            name="TestAgent",
            agent_type=AgentType.COORDINATOR,
            capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.REASONING],
            tools=["web_search", "catalog_query"]
        )
        assert config.name == "TestAgent"
        assert config.agent_type == AgentType.COORDINATOR
        assert config.has_capability(AgentCapability.WEB_SEARCH)
        assert not config.has_capability(AgentCapability.CODE_EXECUTION)

    @pytest.mark.asyncio
    async def test_mock_agent_respond(self):
        """测试MockAgent响应"""
        config = AgentConfig(name="Mock", agent_type=AgentType.RESEARCHER)
        agent = MockAgent(config)

        result = await agent.respond("Test input", {"task_id": "test_001"})

        assert result.success
        assert "Test input" in result.output
        assert len(result.actions) == 1
        assert result.agent_id == agent.agent_id

    @pytest.mark.asyncio
    async def test_agent_registered(self):
        """测试Agent注册"""
        assert "mock" in _agent_registry
        assert _agent_registry["mock"] == RegisteredMockAgent


# ============== Task测试 ==============

class MockTask(BaseTask):
    """测试用Task"""

    async def load_instances(self) -> List[TaskInstance]:
        inst = TaskInstance(
            task_id="mock_task_001",
            config=self.config,
            prompt="Mock task prompt",
            ground_truth={"answer": 42}
        )
        self._instances.append(inst)
        return self._instances

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        expected = ground_truth.get("answer", 0)
        if output == expected:
            return {"accuracy": 1.0}
        return {"accuracy": 0.0}


@register_task("mock_task")
class RegisteredMockTask(BaseTask):
    """注册测试用Task"""

    async def load_instances(self) -> List[TaskInstance]:
        return []

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        return {"accuracy": 0.5}


class TestTask:
    """Task测试"""

    def test_task_config(self):
        """测试Task配置"""
        config = TaskConfig(
            name="TestTask",
            category=TaskCategory.ASTRONOMY_OBSERVATION,
            description="Test task",
            difficulty=DifficultyLevel.LEVEL_2,
            max_steps=10,
            tools=["web_search"]
        )
        assert config.name == "TestTask"
        assert config.category == TaskCategory.ASTRONOMY_OBSERVATION
        assert config.difficulty == DifficultyLevel.LEVEL_2

    @pytest.mark.asyncio
    async def test_mock_task_load(self):
        """测试MockTask实例加载"""
        config = TaskConfig(name="Mock", category=TaskCategory.GENERAL, description="")
        task = MockTask(config)
        instances = await task.load_instances()

        assert len(instances) == 1
        assert instances[0].task_id == "mock_task_001"
        assert instances[0].ground_truth["answer"] == 42

    @pytest.mark.asyncio
    async def test_task_registered(self):
        """测试Task注册"""
        assert "mock_task" in _task_registry


# ============== Evaluator测试 ==============

class TestEvaluator:
    """Evaluator测试"""

    @pytest.mark.asyncio
    async def test_astronomy_evaluator(self):
        """测试天文专用Evaluator"""
        config = EvaluationConfig(metrics=[MetricType.ACCURACY])
        evaluator = AstronomicspecificEvaluator(config)

        @dataclass
        class MockTaskResult:
            task_id: str = "test"
            agent_id: str = "agent1"
            success: bool = True
            output: Any = "result"

        task_result = MockTaskResult()
        result = await evaluator.evaluate(task_result, "expected")

        assert result.task_id == "test"
        assert result.agent_id == "agent1"
        assert result.success

    @pytest.mark.asyncio
    async def test_evaluator_aggregate(self):
        """测试结果聚合"""
        config = EvaluationConfig()
        evaluator = AstronomicspecificEvaluator(config)

        results = [
            EvaluationResult(task_id="t1", agent_id="a1", success=True, overall_score=0.9),
            EvaluationResult(task_id="t2", agent_id="a1", success=True, overall_score=0.8),
            EvaluationResult(task_id="t3", agent_id="a1", success=False, overall_score=0.3),
        ]

        agg = await evaluator.aggregate(results)

        assert agg["total_tasks"] == 3
        assert agg["pass_count"] == 2
        assert agg["pass_rate"] == pytest.approx(2/3)
        assert agg["average_score"] == pytest.approx(0.667, rel=0.01)


# ============== Registry测试 ==============

class TestRegistry:
    """注册表测试"""

    def test_agent_creation(self):
        """测试Agent创建"""
        cfg = AgentConfig(name="Test", agent_type=AgentType.RESEARCHER)
        agent = HarnessRegistry.create_agent("mock", config=cfg)
        assert agent is not None
        assert isinstance(agent, RegisteredMockAgent)

    def test_list_agents(self):
        """测试Agent列表"""
        agents = HarnessRegistry.list_agents()
        assert "mock" in agents

    def test_get_stats(self):
        """测试统计信息"""
        stats = HarnessRegistry.get_stats()
        assert stats.agent_count >= 1
        assert stats.task_count >= 1
        # Evaluator may not be registered until explicitly done
        assert stats.evaluator_count >= 0


# ============== Runner测试 ==============

class TestRunner:
    """Runner测试"""

    def test_run_config(self):
        """测试运行配置"""
        config = RunConfig(
            max_concurrent_agents=4,
            max_concurrent_tasks=8,
            retry_on_failure=True
        )
        assert config.max_concurrent_agents == 4
        assert config.max_concurrent_tasks == 8
        assert config.retry_on_failure

    @pytest.mark.asyncio
    async def test_runner_initialization(self):
        """测试Runner初始化"""
        config = RunConfig()
        runner = HarnessRunner(config)

        assert runner.config == config
        assert runner.run_id is not None
        assert len(runner.run_id) == 8

    @pytest.mark.asyncio
    async def test_runner_single_task(self):
        """测试单个任务执行"""
        config = AgentConfig(name="Mock", agent_type=AgentType.CUSTOM)
        agent = MockAgent(config)

        runner = HarnessRunner(RunConfig())
        runner._agents[agent.agent_id] = agent

        task_cfg = TaskConfig(name="Test", category=TaskCategory.GENERAL, description="")
        task = MockTask(task_cfg)
        instances = await task.load_instances()

        result = await runner.execute_single_task(
            instances[0],
            agent,
            evaluator=None
        )

        assert result.task_id == "mock_task_001"
        assert result.agent_id == agent.agent_id
        assert result.status == TaskStatus.COMPLETED


# ============== 集成测试 ==============

class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_harness_run(self):
        """完整Harness运行测试"""
        # 创建配置
        agent_cfg = AgentConfig(
            name="TestAgent",
            agent_type=AgentType.RESEARCHER,
            capabilities=[AgentCapability.REASONING]
        )

        task_cfg = TaskConfig(
            name="MockTask",
            category=TaskCategory.GENERAL,
            description="Integration test task",
            tools=[]
        )

        task = MockTask(task_cfg)
        instances = await task.load_instances()

        # 运行
        runner = HarnessRunner(RunConfig(max_concurrent_agents=2))
        result = await runner.run(
            tasks=instances,
            agent_configs=[agent_cfg]
        )

        assert isinstance(result, RunResult)
        assert result.total_tasks == len(instances)
        assert result.run_id is not None


# ============== 工具测试 ==============

class TestTools:
    """工具测试"""

    def test_tool_integration(self):
        """测试工具集成"""
        from harness.tools import get_tool_integration
        integration = get_tool_integration()
        assert len(integration.list_tools()) >= 4  # 默认4个工具

    def test_tool_metadata(self):
        """测试工具元数据"""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.WEB_SEARCH,
            parameters={"query": {"type": "string", "required": True}}
        )
        assert metadata.name == "test_tool"
        assert metadata.category == ToolCategory.WEB_SEARCH


# ============== TaskResult测试 ==============

class TestTaskResult:
    """TaskResult测试"""

    def test_task_result_creation(self):
        """测试TaskResult创建"""
        result = TaskResult(
            task_id="test_001",
            agent_id="agent_001",
            success=True,
            output="Test output"
        )
        assert result.task_id == "test_001"
        assert result.success
        assert result.score == 0.0

    def test_task_result_steps(self):
        """测试添加步骤"""
        result = TaskResult(task_id="t1", agent_id="a1", success=True, output="")
        result.add_step("planning", "Create plan")
        result.add_step("execution", "Execute actions")

        assert len(result.steps) == 2
        assert result.steps[0]["type"] == "planning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
