"""
TianwenAGI Harness - Worker节点实现
单个Worker节点处理任务执行
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Awaitable

logger = logging.getLogger("harness.distributed.worker")


class WorkerStatus(Enum):
    """Worker状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class WorkerMetrics:
    """Worker性能指标"""
    worker_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 任务统计
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_running: int = 0

    # 性能指标
    avg_task_duration: float = 0.0       # 平均任务执行时间(秒)
    total_execution_time: float = 0.0     # 总执行时间
    throughput: float = 0.0              # 吞吐量 (tasks/sec)

    # 资源使用
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_utilization: float = 0.0

    # 健康状态
    consecutive_failures: int = 0
    last_heartbeat: str = ""
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "timestamp": self.timestamp,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_running": self.tasks_running,
            "avg_task_duration": self.avg_task_duration,
            "throughput": self.throughput,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "consecutive_failures": self.consecutive_failures,
            "uptime_seconds": self.uptime_seconds,
        }


class WorkerNode:
    """
    Worker节点
    负责从调度器接收任务并执行
    """

    def __init__(
        self,
        config,  # WorkerConfig
        executor: Optional[Callable] = None
    ):
        self.config = config
        self.worker_id = config.worker_id
        self.name = config.name
        self.executor = executor

        self._status = WorkerStatus.IDLE
        self._metrics = WorkerMetrics(worker_id=self.worker_id)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._start_time = time.time()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    @property
    def status(self) -> WorkerStatus:
        return self._status

    @property
    def metrics(self) -> WorkerMetrics:
        return self._metrics

    @property
    def is_available(self) -> bool:
        """检查Worker是否可用"""
        return (
            self._status in (WorkerStatus.IDLE, WorkerStatus.BUSY)
            and self._metrics.consecutive_failures < self.config.max_consecutive_failures
        )

    @property
    def current_load(self) -> int:
        """当前负载（正在执行的任务数）"""
        return len(self._running_tasks)

    async def start(self):
        """启动Worker"""
        logger.info(f"Starting worker {self.worker_id} ({self.name})")
        self._shutdown_event.clear()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._metrics.last_heartbeat = datetime.now().isoformat()

    async def stop(self):
        """停止Worker"""
        logger.info(f"Stopping worker {self.worker_id}")
        self._shutdown_event.set()

        # 取消正在执行的任务
        for task_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled task {task_id}")

        self._running_tasks.clear()

        # 等待心跳任务结束
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        self._status = WorkerStatus.OFFLINE
        logger.info(f"Worker {self.worker_id} stopped")

    async def _heartbeat_loop(self):
        """心跳循环"""
        interval = self.config.heartbeat_interval

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(interval)
                self._metrics.last_heartbeat = datetime.now().isoformat()
                self._update_uptime()
                logger.debug(f"Worker {self.worker_id} heartbeat")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat error for {self.worker_id}: {e}")

    def _update_uptime(self):
        """更新运行时间"""
        self._metrics.uptime_seconds = time.time() - self._start_time

    async def execute_task(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单个任务

        Args:
            task_id: 任务ID
            task_data: 任务数据

        Returns:
            任务结果
        """
        if not self.is_available:
            return {
                "task_id": task_id,
                "success": False,
                "error": f"Worker {self.worker_id} is not available (status: {self._status})"
            }

        self._status = WorkerStatus.BUSY
        self._metrics.tasks_running += 1

        task_start = time.time()
        result = {
            "task_id": task_id,
            "worker_id": self.worker_id,
            "success": False,
            "output": None,
            "error": None,
            "execution_time": 0.0,
        }

        try:
            logger.info(f"Worker {self.worker_id} executing task {task_id}")

            # 创建执行任务
            task = asyncio.create_task(
                self._execute_task_internal(task_id, task_data)
            )
            self._running_tasks[task_id] = task

            # 等待任务完成
            task_result = await task

            # 更新结果
            result.update(task_result)
            result["execution_time"] = time.time() - task_start

            if result["success"]:
                self._metrics.tasks_completed += 1
                self._metrics.consecutive_failures = 0
            else:
                self._metrics.tasks_failed += 1
                self._metrics.consecutive_failures += 1

            # 更新性能指标
            self._update_throughput()

        except asyncio.CancelledError:
            result["error"] = "Task cancelled"
            result["execution_time"] = time.time() - task_start
            self._metrics.tasks_failed += 1
            self._metrics.consecutive_failures += 1
            logger.warning(f"Task {task_id} cancelled on worker {self.worker_id}")

        except Exception as e:
            result["error"] = str(e)
            result["execution_time"] = time.time() - task_start
            self._metrics.tasks_failed += 1
            self._metrics.consecutive_failures += 1
            logger.error(f"Task {task_id} failed on worker {self.worker_id}: {e}")

        finally:
            self._metrics.tasks_running = max(0, self._metrics.tasks_running - 1)
            self._running_tasks.pop(task_id, None)

            # 更新状态
            if self.current_load == 0:
                self._status = WorkerStatus.IDLE
            else:
                self._status = WorkerStatus.BUSY

        return result

    async def _execute_task_internal(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """内部任务执行逻辑"""
        if self.executor:
            # 使用自定义执行器
            output = await self.executor(task_id, task_data)
            return {
                "success": True,
                "output": output,
            }
        else:
            # 默认执行逻辑
            command = task_data.get("command")
            if not command:
                return {
                    "success": False,
                    "error": "No command specified in task data"
                }

            # 模拟执行
            await asyncio.sleep(0.1)  # 模拟处理时间

            return {
                "success": True,
                "output": f"Executed: {command}",
            }

    def _update_throughput(self):
        """更新吞吐量指标"""
        self._metrics.total_execution_time = time.time() - self._start_time

        total_tasks = self._metrics.tasks_completed + self._metrics.tasks_failed
        if self._metrics.total_execution_time > 0:
            self._metrics.throughput = total_tasks / self._metrics.total_execution_time

        # 更新平均任务时长
        if self._metrics.tasks_completed > 0:
            total_duration = self._metrics.avg_task_duration * (self._metrics.tasks_completed - 1)
            # 简化计算
            self._metrics.avg_task_duration = self._metrics.total_execution_time / max(1, self._metrics.tasks_completed)

    async def get_status(self) -> Dict[str, Any]:
        """获取Worker状态"""
        self._update_uptime()
        return {
            "worker_id": self.worker_id,
            "name": self.name,
            "status": self._status.value,
            "is_available": self.is_available,
            "current_load": self.current_load,
            "capacity": self.config.capacity,
            "metrics": self._metrics.to_dict(),
        }

    async def health_check(self) -> bool:
        """健康检查"""
        is_healthy = (
            self.is_available
            and self._metrics.consecutive_failures < self.config.max_consecutive_failures
        )

        if not is_healthy:
            self._status = WorkerStatus.ERROR

        return is_healthy

    def get_capabilities(self) -> Dict[str, Any]:
        """获取Worker能力"""
        return {
            "worker_id": self.worker_id,
            "capacity": self.config.capacity,
            "max_memory_mb": self.config.max_memory_mb,
            "max_cpu_percent": self.config.max_cpu_percent,
            "max_gpu": self.config.max_gpu,
            "tags": self.config.tags,
        }

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False
