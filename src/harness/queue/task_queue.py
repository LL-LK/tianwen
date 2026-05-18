"""
TianwenAGI Harness - 异步任务队列
支持优先级的异步任务队列
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Awaitable
from heapq import heappush, heappop

logger = logging.getLogger("harness.queue")


class QueuePriority(Enum):
    """队列优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class QueueEntry:
    """队列条目"""
    task_id: str
    task_data: Any
    priority: int = QueuePriority.NORMAL.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_priority(self) -> bool:
        return self.priority >= QueuePriority.HIGH.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class QueueStats:
    """队列统计"""
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_completed: int = 0
    total_failed: int = 0
    current_size: int = 0
    processing_count: int = 0
    avg_processing_time: float = 0.0
    total_processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_enqueued": self.total_enqueued,
            "total_dequeued": self.total_dequeued,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "current_size": self.current_size,
            "processing_count": self.processing_count,
            "avg_processing_time": self.avg_processing_time,
        }


class TaskQueue:
    """
    异步任务队列
    支持优先级、超时、批量处理
    """

    def __init__(
        self,
        maxsize: int = 0,
        enable_priority: bool = True
    ):
        self.maxsize = maxsize
        self.enable_priority = enable_priority

        self._queue: List[QueueEntry] = []
        self._queue_index = 0  # Counter for FIFO tie-breaking in priority queue
        self._processing: Dict[str, QueueEntry] = {}
        self._lock = asyncio.Lock()
        self._stats = QueueStats()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)

    @property
    def stats(self) -> QueueStats:
        return self._stats

    @property
    def qsize(self) -> int:
        """当前队列大小"""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        """队列是否已满"""
        return self.maxsize > 0 and len(self._queue) >= self.maxsize

    async def enqueue(
        self,
        task_id: str,
        task_data: Any,
        priority: int = QueuePriority.NORMAL.value,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueueEntry:
        """
        入队操作

        Args:
            task_id: 任务ID
            task_data: 任务数据
            priority: 优先级
            metadata: 额外元数据

        Returns:
            QueueEntry: 入队的条目
        """
        entry = QueueEntry(
            task_id=task_id,
            task_data=task_data,
            priority=priority,
            metadata=metadata or {}
        )

        async with self._not_full:
            while self.is_full:
                await self._not_full.wait()

            if self.enable_priority:
                # Priority queue insert: negate priority for max-heap behavior (higher priority first)
                # Use (negative_priority, queue_index, entry) so higher priority comes out first
                heappush(self._queue, (-priority, self._queue_index, entry))
                self._queue_index += 1
            else:
                self._queue.append(entry)

            self._stats.total_enqueued += 1
            self._stats.current_size = len(self._queue)

            # 通知等待的消费者
            self._not_empty.notify()

        logger.debug(f"Enqueued task {task_id} with priority {priority}")
        return entry

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[QueueEntry]:
        """
        出队操作

        Args:
            timeout: 超时时间（秒）

        Returns:
            QueueEntry: 出队的条目，如果超时则返回None
        """
        async with self._not_empty:
            if timeout is None:
                # 无限等待
                while self.is_empty:
                    await self._not_empty.wait()
            else:
                # 超时等待
                end_time = time.time() + timeout
                while self.is_empty:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return None
                    await self._not_empty.wait(timeout=remaining)

            entry = heappop(self._queue)[2] if self.enable_priority else self._queue.pop(0)

            entry.status = "processing"
            entry.started_at = datetime.now().isoformat()
            self._processing[entry.task_id] = entry

            self._stats.total_dequeued += 1
            self._stats.current_size = len(self._queue)
            self._stats.processing_count = len(self._processing)

        logger.debug(f"Dequeued task {entry.task_id}")
        return entry

    async def mark_completed(
        self,
        task_id: str,
        result: Any = None
    ):
        """标记任务完成"""
        async with self._lock:
            entry = self._processing.pop(task_id, None)

            if entry:
                entry.status = "completed"
                entry.completed_at = datetime.now().isoformat()
                entry.result = result

                processing_time = (
                    datetime.fromisoformat(entry.completed_at)
                    - datetime.fromisoformat(entry.started_at)
                ).total_seconds()

                self._stats.total_completed += 1
                self._stats.processing_count = len(self._processing)
                self._stats.total_processing_time += processing_time
                self._stats.avg_processing_time = (
                    self._stats.total_processing_time / max(1, self._stats.total_completed)
                )

                logger.debug(f"Task {task_id} completed in {processing_time:.2f}s")

    async def mark_failed(
        self,
        task_id: str,
        error: str
    ):
        """标记任务失败"""
        async with self._lock:
            entry = self._processing.pop(task_id, None)

            if entry:
                entry.status = "failed"
                entry.completed_at = datetime.now().isoformat()
                entry.error = error

                self._stats.total_failed += 1
                self._stats.processing_count = len(self._processing)

                logger.debug(f"Task {task_id} failed: {error}")

    async def get_entry(self, task_id: str) -> Optional[QueueEntry]:
        """获取队列条目"""
        async with self._lock:
            # 检查处理中的任务
            if task_id in self._processing:
                return self._processing[task_id]

            # 检查队列中的任务
            for item in self._queue:
                entry = item[2] if isinstance(item, tuple) else item
                if entry.task_id == task_id:
                    return entry

        return None

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            # 从处理中移除
            if task_id in self._processing:
                entry = self._processing.pop(task_id)
                entry.status = "cancelled"
                entry.completed_at = datetime.now().isoformat()
                self._stats.processing_count = len(self._processing)
                return True

            # 从队列中移除
            for i, item in enumerate(self._queue):
                entry = item[2] if isinstance(item, tuple) else item
                if entry.task_id == task_id:
                    self._queue.pop(i)
                    entry.status = "cancelled"
                    entry.completed_at = datetime.now().isoformat()
                    self._stats.current_size = len(self._queue)
                    return True

        return False

    async def clear(self):
        """清空队列"""
        async with self._lock:
            self._queue.clear()
            self._stats.current_size = 0

    def get_pending_tasks(self) -> List[str]:
        """获取待处理任务ID列表"""
        result = []
        for item in self._queue:
            entry = item[2] if isinstance(item, tuple) else item
            result.append(entry.task_id)
        return result

    def get_processing_tasks(self) -> List[str]:
        """获取处理中任务ID列表"""
        return list(self._processing.keys())

    async def batch_dequeue(
        self,
        batch_size: int,
        timeout: Optional[float] = None
    ) -> List[QueueEntry]:
        """
        批量出队

        Args:
            batch_size: 批量大小
            timeout: 超时时间

        Returns:
            批量条目列表
        """
        entries = []

        first = await self.dequeue(timeout=timeout)
        if first:
            entries.append(first)

            # 继续获取直到达到批量大小
            while len(entries) < batch_size:
                try:
                    entry = await self.dequeue(timeout=0.1)
                    if entry:
                        entries.append(entry)
                    else:
                        break
                except asyncio.TimeoutError:
                    break

        return entries

    async def wait_until_empty(self, timeout: Optional[float] = None):
        """等待队列清空"""
        end_time = time.time() + (timeout or float('inf'))

        async with self._lock:
            while len(self._queue) > 0 or len(self._processing) > 0:
                remaining = end_time - time.time()
                if remaining <= 0:
                    break
                await asyncio.sleep(0.1)

    def to_dict(self) -> Dict[str, Any]:
        """序列化队列状态"""
        return {
            "stats": self._stats.to_dict(),
            "maxsize": self.maxsize,
            "pending_count": len(self._queue),
            "processing_count": len(self._processing),
            "is_empty": self.is_empty,
            "is_full": self.is_full,
        }
