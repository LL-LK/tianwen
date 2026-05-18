"""
TianwenAGI Harness - Phase 4 Queue Tests
测试任务队列和结果存储模块
"""
import pytest
import asyncio
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from harness.queue import (
    TaskQueue, QueueEntry, QueueStats,
    ResultStore, StoredResult
)


class TestQueueEntry:
    """队列条目测试"""

    def test_entry_creation(self):
        """测试条目创建"""
        entry = QueueEntry(
            task_id="task-001",
            task_data={"cmd": "test"},
            priority=2
        )
        assert entry.task_id == "task-001"
        assert entry.priority == 2
        assert entry.status == "pending"

    def test_entry_is_high_priority(self):
        """测试高优先级检查"""
        low = QueueEntry(task_id="t1", task_data={}, priority=0)
        high = QueueEntry(task_id="t2", task_data={}, priority=3)

        assert not low.is_high_priority
        assert high.is_high_priority

    def test_entry_to_dict(self):
        """测试条目序列化"""
        entry = QueueEntry(task_id="t1", task_data={})
        data = entry.to_dict()
        assert data["task_id"] == "t1"
        assert data["status"] == "pending"


class TestQueueStats:
    """队列统计测试"""

    def test_stats_creation(self):
        """测试统计创建"""
        stats = QueueStats(
            total_enqueued=100,
            total_dequeued=90,
            total_completed=85,
            total_failed=5
        )
        assert stats.total_enqueued == 100
        assert stats.total_completed == 85

    def test_stats_to_dict(self):
        """测试统计序列化"""
        stats = QueueStats()
        data = stats.to_dict()
        assert "total_enqueued" in data


class TestTaskQueue:
    """任务队列测试"""

    @pytest.mark.asyncio
    async def test_queue_initialization(self):
        """测试队列初始化"""
        queue = TaskQueue(maxsize=10)
        assert queue.maxsize == 10
        assert queue.is_empty

    @pytest.mark.asyncio
    async def test_enqueue(self):
        """测试入队"""
        queue = TaskQueue()

        entry = await queue.enqueue(
            task_id="task-001",
            task_data={"cmd": "test"},
            priority=1
        )

        assert entry.task_id == "task-001"
        assert not queue.is_empty

    @pytest.mark.asyncio
    async def test_dequeue(self):
        """测试出队"""
        queue = TaskQueue()

        await queue.enqueue(task_id="task-001", task_data={})
        entry = await queue.dequeue()

        assert entry is not None
        assert entry.task_id == "task-001"

    @pytest.mark.asyncio
    async def test_priority_queue(self):
        """测试优先级队列"""
        queue = TaskQueue(enable_priority=True)

        await queue.enqueue(task_id="low", task_data={}, priority=0)
        await queue.enqueue(task_id="high", task_data={}, priority=3)
        await queue.enqueue(task_id="normal", task_data={}, priority=1)

        # 高优先级应该先出队
        first = await queue.dequeue()
        assert first.task_id == "high"

    @pytest.mark.asyncio
    async def test_mark_completed(self):
        """测试标记完成"""
        queue = TaskQueue()

        await queue.enqueue(task_id="task-001", task_data={})
        entry = await queue.dequeue()

        await queue.mark_completed(entry.task_id, result={"output": "done"})

        stats = queue.stats
        assert stats.total_completed == 1

    @pytest.mark.asyncio
    async def test_mark_failed(self):
        """测试标记失败"""
        queue = TaskQueue()

        await queue.enqueue(task_id="task-001", task_data={})
        entry = await queue.dequeue()

        await queue.mark_failed(entry.task_id, error="Test error")

        stats = queue.stats
        assert stats.total_failed == 1

    @pytest.mark.asyncio
    async def test_cancel(self):
        """测试取消任务"""
        queue = TaskQueue()

        await queue.enqueue(task_id="task-001", task_data={})
        entry = await queue.dequeue()

        cancelled = await queue.cancel(entry.task_id)
        assert cancelled is True

    @pytest.mark.asyncio
    async def test_get_entry(self):
        """测试获取条目"""
        queue = TaskQueue()

        await queue.enqueue(task_id="task-001", task_data={})
        entry = await queue.get_entry("task-001")

        assert entry is not None
        assert entry.task_id == "task-001"

    @pytest.mark.asyncio
    async def test_batch_dequeue(self):
        """测试批量出队"""
        queue = TaskQueue()

        for i in range(5):
            await queue.enqueue(task_id=f"task-{i}", task_data={})

        batch = await queue.batch_dequeue(batch_size=3)
        assert len(batch) == 3

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空队列"""
        queue = TaskQueue()

        for i in range(3):
            await queue.enqueue(task_id=f"task-{i}", task_data={})

        await queue.clear()
        assert queue.is_empty

    @pytest.mark.asyncio
    async def test_to_dict(self):
        """测试队列序列化"""
        queue = TaskQueue(maxsize=10)
        data = queue.to_dict()

        assert "stats" in data
        assert data["maxsize"] == 10  # maxsize is included in to_dict


class TestStoredResult:
    """存储结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = StoredResult(
            result_id="result-001",
            task_id="task-001",
            success=True,
            output="test output",
            score=0.95
        )
        assert result.result_id == "result-001"
        assert result.success is True
        assert result.score == 0.95

    def test_result_to_dict(self):
        """测试结果序列化"""
        result = StoredResult(
            result_id="r1",
            task_id="t1",
            success=True
        )
        data = result.to_dict()
        assert data["result_id"] == "r1"
        assert data["success"] is True

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "result_id": "r1",
            "task_id": "t1",
            "success": True,
            "score": 0.9
        }
        result = StoredResult.from_dict(data)
        assert result.result_id == "r1"
        assert result.score == 0.9


class TestResultStore:
    """结果存储测试"""

    @pytest.mark.asyncio
    async def test_memory_store_initialization(self):
        """测试内存存储初始化"""
        store = ResultStore(store_type="memory")
        assert store.store_type == "memory"

    @pytest.mark.asyncio
    async def test_store_result(self):
        """测试存储结果"""
        store = ResultStore(store_type="memory")

        result = await store.store(
            task_id="task-001",
            success=True,
            output={"data": "test"},
            score=0.95
        )

        assert result.task_id == "task-001"
        assert result.score == 0.95

    @pytest.mark.asyncio
    async def test_get_result(self):
        """测试获取结果"""
        store = ResultStore(store_type="memory")

        stored = await store.store(task_id="task-001", success=True)
        retrieved = await store.get(stored.result_id)

        assert retrieved is not None
        assert retrieved.task_id == "task-001"

    @pytest.mark.asyncio
    async def test_get_by_task_id(self):
        """测试通过任务ID获取结果"""
        store = ResultStore(store_type="memory")

        await store.store(task_id="task-001", success=True)
        result = await store.get_by_task_id("task-001")

        assert result is not None
        assert result.task_id == "task-001"

    @pytest.mark.asyncio
    async def test_get_all(self):
        """测试获取所有结果"""
        store = ResultStore(store_type="memory")

        for i in range(5):
            await store.store(task_id=f"task-{i}", success=True)

        results = await store.get_all()
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_delete(self):
        """测试删除结果"""
        store = ResultStore(store_type="memory")

        stored = await store.store(task_id="task-001", success=True)
        deleted = await store.delete(stored.result_id)

        assert deleted is True

        retrieved = await store.get(stored.result_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update(self):
        """测试更新结果"""
        store = ResultStore(store_type="memory")

        stored = await store.store(task_id="task-001", success=True, score=0.5)
        updated = await store.update(stored.result_id, score=0.9)

        assert updated is not None
        assert updated.score == 0.9

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空存储"""
        store = ResultStore(store_type="memory")

        for i in range(3):
            await store.store(task_id=f"task-{i}", success=True)

        await store.clear()
        assert store.count() == 0

    @pytest.mark.asyncio
    async def test_file_store(self):
        """测试文件存储"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(store_type="file", base_dir=tmpdir)

            await store.store(task_id="task-001", success=True)
            result = await store.get_by_task_id("task-001")

            assert result is not None
            assert result.task_id == "task-001"

    @pytest.mark.asyncio
    async def test_export_import_jsonl(self):
        """测试JSONL导出导入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(store_type="memory")

            for i in range(3):
                await store.store(task_id=f"task-{i}", success=True)

            jsonl_path = f"{tmpdir}/results.jsonl"
            count = await store.export_to_jsonl(jsonl_path)

            assert count == 3

            # 创建新存储并导入
            new_store = ResultStore(store_type="memory")
            import_count = await new_store.import_from_jsonl(jsonl_path)

            assert import_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
