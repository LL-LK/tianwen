"""
TianwenAGI Harness - 分布式执行器
协调分布式任务执行
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

from .config import DistributedConfig, ClusterConfig, WorkerConfig, SchedulingStrategy
from .worker import WorkerNode, WorkerStatus, WorkerMetrics
from .scheduler import TaskScheduler, TaskAssignment

logger = logging.getLogger("harness.distributed.runner")


@dataclass
class DistributedResult:
    """分布式执行结果"""
    run_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    overall_score: float = 0.0
    total_execution_time: float = 0.0
    worker_results: Dict[str, Any] = field(default_factory=dict)
    task_results: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "overall_score": self.overall_score,
            "total_execution_time": self.total_execution_time,
            "success": self.success,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class DistributedRunner:
    """
    分布式执行器
    协调多个Worker节点执行任务
    """

    def __init__(self, config: Optional[DistributedConfig] = None):
        self.config = config or DistributedConfig()
        self.run_id = str(uuid.uuid4())[:8]

        self._scheduler: Optional[TaskScheduler] = None
        self._workers: Dict[str, WorkerNode] = {}
        self._running = False
        self._result_store: Optional[Callable] = None

    async def initialize(self):
        """初始化分布式执行器"""
        logger.info(f"Initializing DistributedRunner {self.run_id}")

        # 创建调度器
        self._scheduler = TaskScheduler(self.config.cluster)

        # 注册Worker节点
        await self._register_workers()

        self._running = True
        logger.info(f"DistributedRunner initialized with {len(self._workers)} workers")

    async def _register_workers(self):
        """注册所有Worker节点"""
        if self.config.mode == "local":
            # 本地模式：创建本地Worker
            for i in range(self.config.local_workers):
                worker_id = f"local-worker-{i:03d}"
                worker_config = WorkerConfig(
                    worker_id=worker_id,
                    name=worker_id,
                    capacity=1,
                    enabled=True
                )
                worker = WorkerNode(worker_config)
                await worker.start()
                self._workers[worker_id] = worker
                await self._scheduler.register_worker(worker)

        else:
            # 分布式模式：使用配置的Worker
            for worker_config in self.config.cluster.get_enabled_workers():
                worker = WorkerNode(worker_config)
                await worker.start()
                self._workers[worker_config.worker_id] = worker
                await self._scheduler.register_worker(worker)

    async def shutdown(self):
        """关闭分布式执行器"""
        logger.info("Shutting down DistributedRunner...")

        self._running = False

        # 关闭所有Worker
        for worker in self._workers.values():
            await worker.stop()

        self._workers.clear()

        # 关闭调度器
        if self._scheduler:
            await self._scheduler.shutdown()

        logger.info("DistributedRunner shutdown complete")

    async def run_tasks(
        self,
        tasks: List[Dict[str, Any]],
        task_executor: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None
    ) -> DistributedResult:
        """
        分布式运行任务

        Args:
            tasks: 任务列表
            task_executor: 任务执行器
            progress_callback: 进度回调函数

        Returns:
            DistributedResult: 执行结果
        """
        if not self._running:
            await self.initialize()

        start_time = time.time()
        result = DistributedResult(
            run_id=self.run_id,
            total_tasks=len(tasks),
            completed_tasks=0,
            failed_tasks=0
        )

        try:
            logger.info(f"Starting distributed execution of {len(tasks)} tasks")

            # 调度所有任务
            task_assignments = await self._scheduler.schedule_batch([
                {
                    "task_id": t.get("task_id", f"task-{i}"),
                    "task_data": t.get("task_data", t),
                    "priority": t.get("priority", 0),
                    "tags": t.get("tags")
                }
                for i, t in enumerate(tasks)
            ])

            # 并行执行任务
            async def execute_task(task_info: Dict[str, Any], idx: int) -> Dict[str, Any]:
                task_id = task_info.get("task_id", f"task-{idx}")
                task_data = task_info.get("task_data", {})

                # 使用调度器执行
                if task_executor:
                    return await task_executor(task_id, task_data)
                else:
                    return await self._scheduler.execute_on_assigned(task_id, task_data)

            # 使用信号量控制并发
            semaphore = asyncio.Semaphore(self.config.cluster.max_concurrent_tasks)

            async def bounded_execute(task_info: Dict[str, Any], idx: int):
                async with semaphore:
                    return await execute_task(task_info, idx)

            # 执行所有任务
            task_coroutines = [
                bounded_execute(t, i)
                for i, t in enumerate(tasks)
            ]

            results = await asyncio.gather(
                *task_coroutines,
                return_exceptions=True
            )

            # 处理结果
            task_results = []
            completed = 0
            failed = 0

            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    task_results.append({
                        "task_id": tasks[i].get("task_id", f"task-{i}"),
                        "success": False,
                        "error": str(r)
                    })
                    failed += 1
                else:
                    task_results.append(r)
                    if r.get("success", False):
                        completed += 1
                    else:
                        failed += 1

                # 进度回调
                if progress_callback:
                    await progress_callback(i + 1, len(tasks))

            result.task_results = task_results
            result.completed_tasks = completed
            result.failed_tasks = failed

            # 计算总体评分
            if completed + failed > 0:
                result.overall_score = completed / (completed + failed)

            result.total_execution_time = time.time() - start_time
            result.success = failed == 0

            # 收集Worker结果
            result.worker_results = await self._collect_worker_results()

            logger.info(
                f"Distributed execution complete: {completed}/{len(tasks)} succeeded "
                f"in {result.total_execution_time:.2f}s"
            )

        except Exception as e:
            result.error = str(e)
            logger.error(f"Distributed execution failed: {e}")

        return result

    async def run_tasks_async(
        self,
        tasks: List[Dict[str, Any]],
        callback: Optional[Callable] = None
    ) -> str:
        """
        异步运行任务（不阻塞）

        Args:
            tasks: 任务列表
            callback: 完成回调函数

        Returns:
            run_id: 运行ID
        """
        if not self._running:
            await self.initialize()

        run_id = f"async-{uuid.uuid4().hex[:8]}"

        async def execute():
            result = await self.run_tasks(tasks)
            if callback:
                await callback(result)

        asyncio.create_task(execute())
        return run_id

    async def _collect_worker_results(self) -> Dict[str, Any]:
        """收集所有Worker的结果"""
        results = {}
        for worker_id, worker in self._workers.items():
            status = await worker.get_status()
            results[worker_id] = {
                "status": status["status"],
                "metrics": status["metrics"],
            }
        return results

    async def get_status(self) -> Dict[str, Any]:
        """获取执行器状态"""
        return {
            "run_id": self.run_id,
            "running": self._running,
            "mode": self.config.mode,
            "worker_count": len(self._workers),
            "scheduler": self._scheduler.get_stats() if self._scheduler else {},
        }

    async def scale_workers(self, count: int):
        """扩展Worker数量（仅本地模式）"""
        if self.config.mode != "local":
            logger.warning("Can only scale workers in local mode")
            return

        current_count = len(self._workers)

        if count > current_count:
            # 增加Worker
            for i in range(current_count, count):
                worker_id = f"local-worker-{i:03d}"
                worker_config = WorkerConfig(
                    worker_id=worker_id,
                    name=worker_id,
                    capacity=1,
                    enabled=True
                )
                worker = WorkerNode(worker_config)
                await worker.start()
                self._workers[worker_id] = worker
                await self._scheduler.register_worker(worker)
                logger.info(f"Scaled up: added worker {worker_id}")

        elif count < current_count:
            # 减少Worker
            workers_to_remove = list(self._workers.values())[count:]
            for worker in workers_to_remove:
                await worker.stop()
                await self._scheduler.unregister_worker(worker.worker_id)
                del self._workers[worker.worker_id]
                logger.info(f"Scaled down: removed worker {worker.worker_id}")

    def get_worker_metrics(self) -> List[WorkerMetrics]:
        """获取所有Worker的指标"""
        return [w.metrics for w in self._workers.values()]

    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成"""
        try:
            while self._running:
                # 检查是否所有Worker都空闲
                all_idle = all(
                    w.status == WorkerStatus.IDLE
                    for w in self._workers.values()
                )
                if all_idle:
                    return True

                await asyncio.sleep(0.5)

        except asyncio.TimeoutError:
            return False

        return True

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
        return False
