"""
TianwenAGI Harness - 任务调度器
将任务分配给Worker节点
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable

from .config import WorkerConfig, ClusterConfig, SchedulingStrategy
from .worker import WorkerNode, WorkerStatus

logger = logging.getLogger("harness.distributed.scheduler")


@dataclass
class TaskAssignment:
    """任务分配记录"""
    task_id: str
    worker_id: str
    assigned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "assigned_at": self.assigned_at,
            "priority": self.priority,
            "tags": self.tags,
        }


class TaskScheduler:
    """
    任务调度器
    管理任务分配、负载均衡、故障转移
    """

    def __init__(self, config: ClusterConfig):
        self.config = config
        self._workers: Dict[str, WorkerNode] = {}
        self._assignments: Dict[str, TaskAssignment] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._round_robin_index: Dict[str, int] = {}  # worker_id -> index

    async def register_worker(self, worker: WorkerNode):
        """注册Worker节点"""
        self._workers[worker.worker_id] = worker
        self._round_robin_index[worker.worker_id] = 0
        logger.info(f"Registered worker {worker.worker_id} ({worker.name})")

    async def unregister_worker(self, worker_id: str):
        """注销Worker节点"""
        if worker_id in self._workers:
            await self._workers[worker_id].stop()
            del self._workers[worker_id]
            logger.info(f"Unregistered worker {worker_id}")

    async def schedule_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        priority: int = 0,
        tags: Optional[List[str]] = None
    ) -> Optional[TaskAssignment]:
        """
        调度单个任务

        Args:
            task_id: 任务ID
            task_data: 任务数据
            priority: 优先级（数值越大优先级越高）
            tags: 任务标签（用于亲和性调度）

        Returns:
            TaskAssignment: 任务分配信息，如果无法调度则返回None
        """
        worker = await self._select_worker(task_id, tags)

        if not worker:
            logger.warning(f"No available worker for task {task_id}")
            return None

        assignment = TaskAssignment(
            task_id=task_id,
            worker_id=worker.worker_id,
            priority=priority,
            tags=tags or []
        )

        self._assignments[task_id] = assignment

        logger.debug(f"Scheduled task {task_id} to worker {worker.worker_id}")
        return assignment

    async def _select_worker(
        self,
        task_id: str,
        tags: Optional[List[str]] = None
    ) -> Optional[WorkerNode]:
        """选择最佳Worker"""
        available_workers = [
            w for w in self._workers.values()
            if w.is_available and w.current_load < w.config.capacity
        ]

        if not available_workers:
            return None

        strategy = self.config.scheduling_strategy

        if strategy == SchedulingStrategy.ROUND_ROBIN:
            return self._select_round_robin(available_workers)

        elif strategy == SchedulingStrategy.LEAST_LOADED:
            return self._select_least_loaded(available_workers)

        elif strategy == SchedulingStrategy.RANDOM:
            import random
            return random.choice(available_workers)

        elif strategy == SchedulingStrategy.PRIORITY:
            # 基于Worker优先级选择
            return self._select_by_priority(available_workers)

        elif strategy == SchedulingStrategy.AFFINITY:
            # 基于标签亲和性选择
            return self._select_by_affinity(available_workers, tags)

        else:
            return available_workers[0]

    def _select_round_robin(self, workers: List[WorkerNode]) -> WorkerNode:
        """轮询选择"""
        worker_ids = sorted(w.worker_id for w in workers)

        for wid in worker_ids:
            idx = self._round_robin_index.get(wid, 0)
            if idx < len(workers):
                selected = workers[idx % len(workers)]
                self._round_robin_index[wid] = idx + 1
                return selected

        return workers[0]

    def _select_least_loaded(self, workers: List[WorkerNode]) -> WorkerNode:
        """选择负载最低的Worker"""
        return min(workers, key=lambda w: w.current_load)

    def _select_by_priority(self, workers: List[WorkerNode]) -> WorkerNode:
        """基于优先级选择"""
        # 按负载和容量比选择
        def priority_key(w: WorkerNode) -> float:
            load_ratio = w.current_load / max(1, w.config.capacity)
            return load_ratio

        return min(workers, key=priority_key)

    def _select_by_affinity(
        self,
        workers: List[WorkerNode],
        tags: Optional[List[str]] = None
    ) -> WorkerNode:
        """基于标签亲和性选择"""
        if not tags:
            return self._select_least_loaded(workers)

        # 找出标签匹配的Worker
        matching = [
            w for w in workers
            if any(tag in w.config.tags for tag in tags)
        ]

        if matching:
            return self._select_least_loaded(matching)
        else:
            return self._select_least_loaded(workers)

    async def schedule_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[Optional[TaskAssignment]]:
        """
        批量调度任务

        Args:
            tasks: 任务列表，每项包含 task_id, task_data, priority, tags

        Returns:
            分配结果列表
        """
        assignments = []

        for task_info in tasks:
            task_id = task_info.get("task_id", f"task-{uuid.uuid4().hex[:8]}")
            task_data = task_info.get("task_data", {})
            priority = task_info.get("priority", 0)
            tags = task_info.get("tags")

            assignment = await self.schedule_task(task_id, task_data, priority, tags)
            assignments.append(assignment)

        logger.info(f"Scheduled {len(assignments)} tasks")
        return assignments

    async def execute_on_assigned(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        在分配的Worker上执行任务

        Args:
            task_id: 任务ID
            task_data: 任务数据

        Returns:
            执行结果
        """
        assignment = self._assignments.get(task_id)

        if not assignment:
            # 自动调度
            assignment = await self.schedule_task(task_id, task_data)
            if not assignment:
                return {
                    "task_id": task_id,
                    "success": False,
                    "error": "No available worker"
                }

        worker = self._workers.get(assignment.worker_id)

        if not worker or not worker.is_available:
            logger.warning(f"Worker {assignment.worker_id} unavailable, rescheduling")
            # 重新调度
            del self._assignments[task_id]
            return await self.execute_on_assigned(task_id, task_data)

        return await worker.execute_task(task_id, task_data)

    def get_assignment(self, task_id: str) -> Optional[TaskAssignment]:
        """获取任务分配信息"""
        return self._assignments.get(task_id)

    def get_worker_status(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """获取Worker状态"""
        worker = self._workers.get(worker_id)
        return worker._metrics.to_dict() if worker else None

    async def get_all_worker_status(self) -> Dict[str, Any]:
        """获取所有Worker状态"""
        return {
            wid: await w.get_status()
            for wid, w in self._workers.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取调度统计"""
        total_workers = len(self._workers)
        available_workers = sum(1 for w in self._workers.values() if w.is_available)
        total_load = sum(w.current_load for w in self._workers.values())

        return {
            "total_workers": total_workers,
            "available_workers": available_workers,
            "busy_workers": total_workers - available_workers,
            "total_load": total_load,
            "scheduling_strategy": self.config.scheduling_strategy.value,
            "pending_assignments": len(self._assignments),
        }

    async def redistribute_load(self):
        """重新分配负载（用于负载均衡）"""
        logger.info("Redistributing load...")

        # 获取所有任务过载的Worker
        overloaded = [
            w for w in self._workers.values()
            if w.current_load > w.config.capacity
        ]

        # 获取负载不足的Worker
        underutilized = [
            w for w in self._workers.values()
            if w.current_load < w.config.capacity / 2
        ]

        # 简单重分配：将任务从过载Worker移到空闲Worker
        for source in overloaded:
            for target in underutilized:
                if source.current_load <= target.config.capacity - target.current_load:
                    break

    async def shutdown(self):
        """关闭调度器"""
        logger.info("Shutting down scheduler...")

        for worker in self._workers.values():
            await worker.stop()

        self._workers.clear()
        self._assignments.clear()

        logger.info("Scheduler shutdown complete")
