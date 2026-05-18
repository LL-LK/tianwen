"""
TianwenAGI Harness - Phase 4 Sandbox Tests
测试Docker隔离执行模块
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from harness.sandbox import (
    SandboxConfig, ResourceLimits, ContainerImage,
    DockerContainer, ContainerStatus, ContainerMetrics,
    SandboxRunner, SandboxResult
)


class TestSandboxConfig:
    """Sandbox配置测试"""

    def test_config_creation(self):
        """测试配置创建"""
        config = SandboxConfig(
            image="python:3.11-slim",
            network_mode="bridge"
        )
        assert config.image == "python:3.11-slim"
        assert config.network_mode == "bridge"

    def test_resource_limits(self):
        """测试资源限制"""
        limits = ResourceLimits(
            memory="4g",
            cpu="2.0",
            gpu=1,
            timeout=600
        )
        assert limits.memory == "4g"
        assert limits.cpu == "2.0"
        assert limits.gpu == 1
        assert limits.timeout == 600

    def test_resource_limits_to_dict(self):
        """测试资源限制序列化"""
        limits = ResourceLimits()
        data = limits.to_dict()
        assert "memory" in data
        assert "cpu" in data
        assert "gpu" in data

    def test_config_from_preset(self):
        """测试从预设创建配置"""
        config = SandboxConfig.from_preset("cpu_small")
        assert config.resources.memory == "1g"

        config = SandboxConfig.from_preset("gpu")
        assert config.resources.gpu == 1

    def test_container_image_enum(self):
        """测试容器镜像枚举"""
        assert ContainerImage.PYTHON_3_11.value == "python:3.11-slim"
        assert ContainerImage.TIANWEN_AGI_LATEST.value == "tianwenagi/harness:latest"


class TestDockerContainer:
    """Docker容器测试"""

    @pytest.mark.asyncio
    async def test_container_initialization(self):
        """测试容器初始化"""
        config = SandboxConfig()
        container = DockerContainer(config, name="test-container")
        assert container.name == "test-container"
        assert container.status == ContainerStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_container_create(self):
        """测试容器创建"""
        config = SandboxConfig()
        container = DockerContainer(config)
        container_id = await container.create()
        assert container_id is not None
        assert container.container_id is not None

    @pytest.mark.asyncio
    async def test_container_start_stop(self):
        """测试容器启动停止"""
        config = SandboxConfig()
        container = DockerContainer(config)
        await container.create()
        await container.start()
        assert container.is_running

        await container.stop()
        assert not container.is_running

    @pytest.mark.asyncio
    async def test_container_context_manager(self):
        """测试容器上下文管理器"""
        config = SandboxConfig()
        async with DockerContainer(config) as container:
            assert container.is_running
        # 容器应该在退出时自动清理


class TestContainerMetrics:
    """容器指标测试"""

    def test_metrics_creation(self):
        """测试指标创建"""
        metrics = ContainerMetrics(
            container_id="test-123",
            cpu_percent=50.0,
            memory_percent=75.0
        )
        assert metrics.container_id == "test-123"
        assert metrics.cpu_percent == 50.0

    def test_metrics_to_dict(self):
        """测试指标序列化"""
        metrics = ContainerMetrics(container_id="test")
        data = metrics.to_dict()
        assert data["container_id"] == "test"
        assert "timestamp" in data


class TestSandboxRunner:
    """Sandbox运行器测试"""

    @pytest.mark.asyncio
    async def test_runner_initialization(self):
        """测试运行器初始化"""
        config = SandboxConfig()
        runner = SandboxRunner(config)
        await runner.initialize()
        assert runner.max_concurrent == config.max_concurrent_containers

    @pytest.mark.asyncio
    async def test_run_single_task(self):
        """测试单任务执行"""
        config = SandboxConfig()
        runner = SandboxRunner(config)
        await runner.initialize()

        result = await runner.run_task(
            task_id="test-001",
            command=["echo", "hello"],
            timeout=10
        )

        assert result.sandbox_id is not None
        assert result.task_id == "test-001"

    @pytest.mark.asyncio
    async def test_run_batch_tasks(self):
        """测试批量任务执行"""
        config = SandboxConfig()
        runner = SandboxRunner(config)
        await runner.initialize()

        tasks = [
            {"task_id": f"task-{i}", "command": ["echo", f"hello-{i}"]}
            for i in range(3)
        ]

        results = await runner.run_tasks(tasks, continue_on_error=True)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_runner_context_manager(self):
        """测试运行器上下文管理器"""
        config = SandboxConfig()
        async with SandboxRunner(config) as runner:
            assert runner._running


class TestSandboxResult:
    """Sandbox结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = SandboxResult(
            sandbox_id="sandbox-001",
            task_id="task-001",
            success=True,
            output="test output"
        )
        assert result.sandbox_id == "sandbox-001"
        assert result.success is True
        assert result.output == "test output"

    def test_result_to_dict(self):
        """测试结果序列化"""
        result = SandboxResult(
            sandbox_id="sandbox-001",
            task_id="task-001",
            success=True
        )
        data = result.to_dict()
        assert data["sandbox_id"] == "sandbox-001"
        assert data["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
