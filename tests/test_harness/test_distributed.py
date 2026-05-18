"""
TianwenAGI Harness - Phase 4 Distributed Tests
测试分布式执行模块
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from harness.distributed import (
    DistributedConfig, WorkerConfig, ClusterConfig, SchedulingStrategy,
    WorkerNode, WorkerStatus, WorkerMetrics,
    TaskScheduler, TaskAssignment,
    DistributedRunner, DistributedResult
)


class TestWorkerConfig:
    """Worker配置测试"""

    def test_worker_config_creation(self):
        """测试Worker配置创建"""
        config = WorkerConfig(
            worker_id="worker-001",
            name="Test Worker",
            host="localhost",
            port=8765,
            capacity=2
        )
        assert config.worker_id == "worker-001"
        assert config.capacity == 2
        assert config.endpoint == "localhost:8765"

    def test_worker_config_to_dict(self):
        """测试Worker配置序列化"""
        config = WorkerConfig(worker_id="w1", name="W1")
        data = config.to_dict()
        assert data["worker_id"] == "w1"
        assert "host" in data
        assert config.endpoint == "localhost:8765"


class TestClusterConfig:
    """集群配置测试"""

    def test_cluster_config_creation(self):
        """测试集群配置创建"""
        config = ClusterConfig(
            cluster_id="cluster-001",
            name="Test Cluster",
            scheduling_strategy=SchedulingStrategy.ROUND_ROBIN
        )
        assert config.cluster_id == "cluster-001"
        assert config.scheduling_strategy == SchedulingStrategy.ROUND_ROBIN

    def test_get_enabled_workers(self):
        """测试获取启用的Worker"""
        config = ClusterConfig(
            workers=[
                WorkerConfig(worker_id="w1", name="W1", enabled=True),
                WorkerConfig(worker_id="w2", name="W2", enabled=False),
            ]
        )
        enabled = config.get_enabled_workers()
        assert len(enabled) == 1
        assert enabled[0].worker_id == "w1"


class TestDistributedConfig:
    """分布式配置测试"""

    def test_config_creation(self):
        """测试配置创建"""
        config = DistributedConfig(
            mode="local",
            local_workers=4
        )
        assert config.mode == "local"
        assert config.local_workers == 4

    def test_local_only(self):
        """测试本地模式配置"""
        config = DistributedConfig.local_only(num_workers=4)
        assert config.mode == "local"
        assert config.local_workers == 4


class TestWorkerMetrics:
    """Worker指标测试"""

    def test_metrics_creation(self):
        """测试指标创建"""
        metrics = WorkerMetrics(
            worker_id="worker-001",
            tasks_completed=10,
            tasks_failed=2
        )
        assert metrics.worker_id == "worker-001"
        assert metrics.tasks_completed == 10
        assert metrics.tasks_failed == 2

    def test_metrics_to_dict(self):
        """测试指标序列化"""
        metrics = WorkerMetrics(worker_id="w1")
        data = metrics.to_dict()
        assert data["worker_id"] == "w1"
        assert "tasks_completed" in data


class TestWorkerNode:
    """Worker节点测试"""

    @pytest.mark.asyncio
    async def test_worker_initialization(self):
        """测试Worker初始化"""
        config = WorkerConfig(worker_id="w1", name="Worker 1")
        worker = WorkerNode(config)
        assert worker.worker_id == "w1"
        assert worker.status == WorkerStatus.IDLE

    @pytest.mark.asyncio
    async def test_worker_start_stop(self):
        """测试Worker启动停止"""
        config = WorkerConfig(worker_id="w1", name="Worker 1")
        worker = WorkerNode(config)
        await worker.start()
        assert worker.status in (WorkerStatus.IDLE, WorkerStatus.BUSY)

        await worker.stop()
        assert worker.status == WorkerStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_worker_execute_task(self):
        """测试Worker执行任务"""
        config = WorkerConfig(worker_id="w1", name="Worker 1")
        worker = WorkerNode(config)
        await worker.start()

        result = await worker.execute_task(
            task_id="task-001",
            task_data={"command": "echo test"}
        )

        assert result["task_id"] == "task-001"
        assert "success" in result

        await worker.stop()

    @pytest.mark.asyncio
    async def test_worker_health_check(self):
        """测试Worker健康检查"""
        config = WorkerConfig(worker_id="w1", name="Worker 1")
        worker = WorkerNode(config)
        await worker.start()

        is_healthy = await worker.health_check()
        assert is_healthy is True

        await worker.stop()


class TestTaskAssignment:
    """任务分配测试"""

    def test_assignment_creation(self):
        """测试分配创建"""
        assignment = TaskAssignment(
            task_id="task-001",
            worker_id="worker-001",
            priority=2
        )
        assert assignment.task_id == "task-001"
        assert assignment.priority == 2

    def test_assignment_to_dict(self):
        """测试分配序列化"""
        assignment = TaskAssignment(task_id="t1", worker_id="w1")
        data = assignment.to_dict()
        assert data["task_id"] == "t1"


class TestTaskScheduler:
    """任务调度器测试"""

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self):
        """测试调度器初始化"""
        config = ClusterConfig()
        scheduler = TaskScheduler(config)
        assert scheduler is not None

    @pytest.mark.asyncio
    async def test_register_worker(self):
        """测试注册Worker"""
        config = ClusterConfig()
        scheduler = TaskScheduler(config)

        worker_config = WorkerConfig(worker_id="w1", name="Worker 1")
        worker = WorkerNode(worker_config)
        await worker.start()

        await scheduler.register_worker(worker)

        assert "w1" in scheduler._workers
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_schedule_task(self):
        """测试任务调度"""
        config = ClusterConfig()
        scheduler = TaskScheduler(config)

        worker_config = WorkerConfig(worker_id="w1", name="Worker 1")
        worker = WorkerNode(worker_config)
        await worker.start()
        await scheduler.register_worker(worker)

        assignment = await scheduler.schedule_task(
            task_id="task-001",
            task_data={"command": "test"}
        )

        assert assignment is not None
        assert assignment.worker_id == "w1"

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_schedule_batch(self):
        """测试批量调度"""
        config = ClusterConfig()
        scheduler = TaskScheduler(config)

        worker_config = WorkerConfig(worker_id="w1", name="Worker 1")
        worker = WorkerNode(worker_config)
        await worker.start()
        await scheduler.register_worker(worker)

        tasks = [
            {"task_id": f"task-{i}", "task_data": {}}
            for i in range(3)
        ]

        assignments = await scheduler.schedule_batch(tasks)
        assert len(assignments) == 3

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计"""
        config = ClusterConfig()
        scheduler = TaskScheduler(config)

        stats = scheduler.get_stats()
        assert "total_workers" in stats
        assert stats["total_workers"] == 0


class TestDistributedRunner:
    """分布式运行器测试"""

    @pytest.mark.asyncio
    async def test_runner_initialization(self):
        """测试运行器初始化"""
        config = DistributedConfig.local_only(num_workers=2)
        runner = DistributedRunner(config)
        await runner.initialize()

        assert len(runner._workers) == 2
        assert runner._running is True

        await runner.shutdown()

    @pytest.mark.asyncio
    async def test_run_tasks(self):
        """测试运行任务"""
        config = DistributedConfig.local_only(num_workers=2)
        runner = DistributedRunner(config)
        await runner.initialize()

        tasks = [
            {"task_id": f"task-{i}", "task_data": {"command": f"echo {i}"}}
            for i in range(4)
        ]

        result = await runner.run_tasks(tasks)

        assert result.total_tasks == 4
        assert result.run_id is not None

        await runner.shutdown()

    @pytest.mark.asyncio
    async def test_runner_status(self):
        """测试获取运行状态"""
        config = DistributedConfig.local_only(num_workers=2)
        runner = DistributedRunner(config)
        await runner.initialize()

        status = await runner.get_status()
        assert "run_id" in status
        assert "worker_count" in status

        await runner.shutdown()


class TestDistributedResult:
    """分布式结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = DistributedResult(
            run_id="run-001",
            total_tasks=10,
            completed_tasks=8,
            failed_tasks=2
        )
        assert result.run_id == "run-001"
        assert result.total_tasks == 10
        assert result.completed_tasks == 8

    def test_result_to_dict(self):
        """测试结果序列化"""
        result = DistributedResult(
            run_id="run-001",
            total_tasks=10,
            completed_tasks=8,
            failed_tasks=2
        )
        data = result.to_dict()
        assert data["run_id"] == "run-001"
        assert data["total_tasks"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
