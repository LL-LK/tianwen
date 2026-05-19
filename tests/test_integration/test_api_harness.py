"""
Tianwen-AGI - Harness API Endpoint Tests

Tests for the Harness API endpoints including:
- Agent registration and management
- Task creation and execution
- Benchmark triggering and monitoring
- Registry operations
"""

import pytest
import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, List
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "src"))

from harness import (
    BaseAgent, AgentConfig, AgentResult, AgentAction, AgentType, AgentCapability,
    BaseTask, TaskConfig, TaskResult, TaskCategory, DifficultyLevel, TaskStatus, TaskInstance,
    HarnessRegistry, HarnessRunner, RunConfig, RunResult
)
from harness.registry import _agent_registry, _task_registry


class MockHarnessAgent(BaseAgent):
    """Mock agent for testing."""

    async def plan(self, task_input: str, context: Dict[str, Any]) -> List[AgentAction]:
        return [AgentAction(action_type="plan", content=f"Planned: {task_input}")]

    async def execute(self, action: AgentAction) -> Any:
        return {"status": "executed", "action": action.content}

    async def respond(self, task_input: str, context: Dict[str, Any]) -> AgentResult:
        await asyncio.sleep(0.01)
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            output=f"Response to: {task_input}",
            actions=[AgentAction(action_type="respond", content=f"Action for: {task_input}")],
            execution_time=0.01
        )


class MockHarnessTask(BaseTask):
    """Mock task for testing."""

    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.status = TaskStatus.PENDING

    async def load_instances(self) -> List[TaskInstance]:
        inst = TaskInstance(
            task_id="harness_task_001",
            config=self.config,
            prompt="Harness test task prompt",
            ground_truth={"answer": 42}
        )
        self._instances.append(inst)
        return self._instances

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        expected = ground_truth.get("answer", 0)
        if output == expected:
            return {"accuracy": 1.0}
        return {"accuracy": 0.0}


class TestHarnessAgentAPI:
    """Test Harness Agent API endpoints."""

    @pytest.mark.asyncio
    async def test_agent_config_creation(self, mock_agent_config):
        """Test agent configuration creation."""
        config = AgentConfig(
            name=mock_agent_config["name"],
            agent_type=AgentType.RESEARCHER,
            capabilities=[AgentCapability.REASONING, AgentCapability.WEB_SEARCH]
        )
        assert config.name == mock_agent_config["name"]
        assert config.agent_type == AgentType.RESEARCHER
        assert config.has_capability(AgentCapability.REASONING)
        assert config.has_capability(AgentCapability.WEB_SEARCH)

    @pytest.mark.asyncio
    async def test_agent_respond_success(self):
        """Test successful agent response."""
        config = AgentConfig(name="TestAgent", agent_type=AgentType.RESEARCHER)
        agent = MockHarnessAgent(config)
        result = await agent.respond("Test input", {"task_id": "test_001"})
        assert result.success
        assert "Test input" in result.output
        assert len(result.actions) == 1

    @pytest.mark.asyncio
    async def test_agent_plan_generation(self):
        """Test agent plan generation."""
        config = AgentConfig(name="TestAgent", agent_type=AgentType.COORDINATOR)
        agent = MockHarnessAgent(config)
        actions = await agent.plan("Plan this task", {"context": "test"})
        assert len(actions) > 0
        assert actions[0].action_type == "plan"

    @pytest.mark.asyncio
    async def test_agent_execution(self):
        """Test agent action execution."""
        config = AgentConfig(name="TestAgent", agent_type=AgentType.EXECUTOR)
        agent = MockHarnessAgent(config)
        action = AgentAction(action_type="execute", content="Run test")
        result = await agent.execute(action)
        assert result["status"] == "executed"
        assert "test" in result["action"]

    @pytest.mark.asyncio
    async def test_agent_registry_operations(self):
        """Test agent registry operations."""
        agents = HarnessRegistry.list_agents()
        assert isinstance(agents, list)
        stats = HarnessRegistry.get_stats()
        assert hasattr(stats, "agent_count")
        assert stats.agent_count >= 0


class TestHarnessTaskAPI:
    """Test Harness Task API endpoints."""

    @pytest.mark.asyncio
    async def test_task_config_creation(self, mock_task_config):
        """Test task configuration creation."""
        config = TaskConfig(
            name=mock_task_config["name"],
            category=TaskCategory.ASTRONOMY_OBSERVATION,
            description=mock_task_config["description"],
            difficulty=DifficultyLevel.LEVEL_2
        )
        assert config.name == mock_task_config["name"]
        assert config.category == TaskCategory.ASTRONOMY_OBSERVATION
        assert config.difficulty == DifficultyLevel.LEVEL_2

    @pytest.mark.asyncio
    async def test_task_instance_loading(self):
        """Test task instance loading."""
        config = TaskConfig(name="TestTask", category=TaskCategory.GENERAL, description="")
        task = MockHarnessTask(config)
        instances = await task.load_instances()
        assert len(instances) == 1
        assert instances[0].task_id == "harness_task_001"
        assert instances[0].ground_truth["answer"] == 42

    @pytest.mark.asyncio
    async def test_task_validation_success(self):
        """Test task validation with correct output."""
        config = TaskConfig(name="TestTask", category=TaskCategory.GENERAL, description="")
        task = MockHarnessTask(config)
        scores = await task.validate(42, {"answer": 42})
        assert scores["accuracy"] == 1.0

    @pytest.mark.asyncio
    async def test_task_validation_failure(self):
        """Test task validation with incorrect output."""
        config = TaskConfig(name="TestTask", category=TaskCategory.GENERAL, description="")
        task = MockHarnessTask(config)
        scores = await task.validate(0, {"answer": 42})
        assert scores["accuracy"] == 0.0

    @pytest.mark.asyncio
    async def test_task_status_transitions(self):
        """Test task status transitions."""
        config = TaskConfig(name="TestTask", category=TaskCategory.GENERAL, description="")
        task = MockHarnessTask(config)
        assert task.status == TaskStatus.PENDING
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED


class TestHarnessRunnerAPI:
    """Test Harness Runner API endpoints."""

    @pytest.mark.asyncio
    async def test_runner_initialization(self, mock_harness_config):
        """Test runner initialization."""
        config = RunConfig(
            max_concurrent_agents=mock_harness_config["max_concurrent_agents"],
            max_concurrent_tasks=mock_harness_config["max_concurrent_tasks"],
            retry_on_failure=mock_harness_config["retry_on_failure"]
        )
        runner = HarnessRunner(config)
        assert runner.config == config
        assert runner.run_id is not None
        assert len(runner.run_id) > 0

    @pytest.mark.asyncio
    async def test_runner_single_task_execution(self):
        """Test single task execution through runner."""
        agent_config = AgentConfig(name="TestAgent", agent_type=AgentType.RESEARCHER)
        agent = MockHarnessAgent(agent_config)

        task_config = TaskConfig(name="TestTask", category=TaskCategory.GENERAL, description="")
        task = MockHarnessTask(task_config)
        instances = await task.load_instances()

        runner = HarnessRunner(RunConfig())
        runner._agents[agent.agent_id] = agent

        result = await runner.execute_single_task(instances[0], agent, evaluator=None)
        assert result.task_id == "harness_task_001"
        assert result.agent_id == agent.agent_id
        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_runner_config_options(self):
        """Test runner configuration options."""
        config = RunConfig(
            max_concurrent_agents=8,
            max_concurrent_tasks=16,
            retry_on_failure=True,
            timeout_seconds=600
        )
        assert config.max_concurrent_agents == 8
        assert config.max_concurrent_tasks == 16
        assert config.retry_on_failure is True
        assert config.timeout_seconds == 600

    @pytest.mark.asyncio
    async def test_run_result_structure(self):
        """Test run result structure."""
        result = RunResult(
            run_id="test_run_001",
            total_tasks=5,
            completed_tasks=4,
            failed_tasks=1,
            pass_rate=0.8,
            execution_time=120.5
        )
        assert result.run_id == "test_run_001"
        assert result.total_tasks == 5
        assert result.completed_tasks == 4
        assert result.failed_tasks == 1
        assert result.pass_rate == 0.8

    @pytest.mark.asyncio
    async def test_runner_agent_assignment(self):
        """Test runner assigns agents correctly."""
        agent_config = AgentConfig(name="TestAgent", agent_type=AgentType.RESEARCHER)
        agent = MockHarnessAgent(agent_config)

        runner = HarnessRunner(RunConfig())
        runner._agents[agent.agent_id] = agent

        assert agent.agent_id in runner._agents
        assert runner._agents[agent.agent_id] == agent


class TestHarnessRegistryAPI:
    """Test Harness Registry API endpoints."""

    def test_registry_agent_creation(self):
        """Test creating agent through registry."""
        cfg = AgentConfig(name="RegistryTest", agent_type=AgentType.RESEARCHER)
        # Note: This depends on registered agents in the harness
        agents = HarnessRegistry.list_agents()
        assert isinstance(agents, list)

    def test_registry_list_agents(self):
        """Test listing registered agents."""
        agents = HarnessRegistry.list_agents()
        assert isinstance(agents, list)
        # At minimum should have registered mock agents
        for agent_id in agents:
            assert isinstance(agent_id, str)

    def test_registry_stats(self):
        """Test registry statistics."""
        stats = HarnessRegistry.get_stats()
        assert hasattr(stats, "agent_count")
        assert hasattr(stats, "task_count")
        assert hasattr(stats, "evaluator_count")
        assert stats.agent_count >= 0
        assert stats.task_count >= 0

    def test_registry_task_creation(self):
        """Test creating task through registry."""
        tasks = HarnessRegistry.list_tasks()
        assert isinstance(tasks, list)

    def test_registry_list_tasks(self):
        """Test listing registered tasks."""
        tasks = HarnessRegistry.list_tasks()
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_registry_full_run_flow(self):
        """Test complete flow through registry."""
        agent_cfg = AgentConfig(name="FlowTest", agent_type=AgentType.RESEARCHER)
        task_cfg = TaskConfig(name="FlowTask", category=TaskCategory.GENERAL, description="Flow test")

        task = MockHarnessTask(task_cfg)
        instances = await task.load_instances()

        runner = HarnessRunner(RunConfig(max_concurrent_agents=2))
        result = await runner.run(tasks=instances, agent_configs=[agent_cfg])

        assert isinstance(result, RunResult)
        assert result.run_id is not None


class TestHarnessIntegrationAPI:
    """Integration tests for Harness API."""

    @pytest.mark.asyncio
    async def test_full_task_execution_flow(self):
        """Test complete task execution flow."""
        # Setup
        agent_cfg = AgentConfig(
            name="IntegrationTest",
            agent_type=AgentType.RESEARCHER,
            capabilities=[AgentCapability.REASONING]
        )
        task_cfg = TaskConfig(
            name="IntegrationTask",
            category=TaskCategory.ASTRONOMY_OBSERVATION,
            description="Integration test task"
        )

        # Execute
        task = MockHarnessTask(task_cfg)
        instances = await task.load_instances()
        runner = HarnessRunner(RunConfig())

        result = await runner.run(tasks=instances, agent_configs=[agent_cfg])

        # Verify
        assert isinstance(result, RunResult)
        assert result.total_tasks == len(instances)
        assert result.run_id is not None

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self):
        """Test concurrent execution of multiple agents."""
        agent_cfgs = [
            AgentConfig(name=f"Agent{i}", agent_type=AgentType.RESEARCHER)
            for i in range(3)
        ]
        task_cfg = TaskConfig(name="ConcurrentTask", category=TaskCategory.GENERAL, description="")
        task = MockHarnessTask(task_cfg)
        instances = await task.load_instances()

        runner = HarnessRunner(RunConfig(max_concurrent_agents=3))
        result = await runner.run(tasks=instances * 3, agent_configs=agent_cfgs)

        assert result.total_tasks == len(instances) * 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
