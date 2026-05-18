"""
TianwenAGI Harness - 结果存储
存储和管理任务执行结果
"""
import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("harness.queue.result_store")


@dataclass
class StoredResult:
    """存储的结果"""
    result_id: str
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    score: float = 0.0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "score": self.score,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredResult":
        """从字典创建"""
        return cls(
            result_id=data["result_id"],
            task_id=data["task_id"],
            success=data["success"],
            output=data.get("output"),
            error=data.get("error"),
            score=data.get("score", 0.0),
            execution_time=data.get("execution_time", 0.0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class ResultStore:
    """
    结果存储
    支持内存、Redis和文件存储
    """

    def __init__(
        self,
        store_type: str = "memory",
        base_dir: str = "./results",
        redis_url: Optional[str] = None,
        ttl: int = 3600
    ):
        """
        初始化结果存储

        Args:
            store_type: 存储类型 ("memory", "file", "redis")
            base_dir: 文件存储基础目录
            redis_url: Redis连接URL
            ttl: 结果TTL（秒）
        """
        self.store_type = store_type
        self.base_dir = Path(base_dir)
        self.redis_url = redis_url
        self.ttl = ttl

        self._results: Dict[str, StoredResult] = {}
        self._lock = asyncio.Lock()
        self._redis_client = None

        # 文件存储初始化
        if store_type == "file":
            self.base_dir.mkdir(parents=True, exist_ok=True)

        # Redis存储初始化
        if store_type == "redis":
            asyncio.create_task(self._init_redis())

    async def _init_redis(self):
        """初始化Redis客户端"""
        try:
            import redis.asyncio as redis
            self._redis_client = redis.from_url(self.redis_url or "redis://localhost:6379")
            await self._redis_client.ping()
            logger.info("Redis connection established")
        except ImportError:
            logger.warning("redis-py not installed, falling back to memory storage")
            self.store_type = "memory"
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, falling back to memory storage")
            self.store_type = "memory"

    async def store(
        self,
        task_id: str,
        success: bool,
        output: Any = None,
        error: Optional[str] = None,
        score: float = 0.0,
        execution_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        result_id: Optional[str] = None
    ) -> StoredResult:
        """
        存储结果

        Args:
            task_id: 任务ID
            success: 是否成功
            output: 输出结果
            error: 错误信息
            score: 评分
            execution_time: 执行时间
            metadata: 元数据
            result_id: 结果ID（可选，自动生成）

        Returns:
            StoredResult: 存储的结果
        """
        result = StoredResult(
            result_id=result_id or str(uuid.uuid4()),
            task_id=task_id,
            success=success,
            output=output,
            error=error,
            score=score,
            execution_time=execution_time,
            metadata=metadata or {}
        )

        async with self._lock:
            if self.store_type == "memory":
                self._results[result.result_id] = result

            elif self.store_type == "file":
                await self._store_to_file(result)

            elif self.store_type == "redis":
                await self._store_to_redis(result)

        logger.debug(f"Stored result for task {task_id}")
        return result

    async def get(self, result_id: str) -> Optional[StoredResult]:
        """获取结果"""
        async with self._lock:
            if self.store_type == "memory":
                return self._results.get(result_id)

            elif self.store_type == "file":
                return await self._get_from_file(result_id)

            elif self.store_type == "redis":
                return await self._get_from_redis(result_id)

        return None

    async def get_by_task_id(self, task_id: str) -> Optional[StoredResult]:
        """通过任务ID获取结果"""
        async with self._lock:
            if self.store_type == "memory":
                for result in self._results.values():
                    if result.task_id == task_id:
                        return result

            elif self.store_type == "file":
                return await self._get_from_file_by_task(task_id)

            elif self.store_type == "redis":
                # 在Redis中需要遍历查找
                keys = await self._redis_client.keys(f"result:*")
                for key in keys:
                    data = await self._redis_client.get(key)
                    if data:
                        result_data = json.loads(data)
                        if result_data.get("task_id") == task_id:
                            return StoredResult.from_dict(result_data)

        return None

    async def get_all(self, limit: int = 100) -> List[StoredResult]:
        """获取所有结果"""
        results = []

        async with self._lock:
            if self.store_type == "memory":
                results = list(self._results.values())[:limit]

            elif self.store_type == "file":
                results = await self._get_all_from_file(limit)

            elif self.store_type == "redis":
                keys = await self._redis_client.keys("result:*")
                for key in keys[:limit]:
                    data = await self._redis_client.get(key)
                    if data:
                        results.append(StoredResult.from_dict(json.loads(data)))

        return results

    async def delete(self, result_id: str) -> bool:
        """删除结果"""
        async with self._lock:
            if self.store_type == "memory":
                if result_id in self._results:
                    del self._results[result_id]
                    return True
                return False

            elif self.store_type == "file":
                return await self._delete_from_file(result_id)

            elif self.store_type == "redis":
                key = f"result:{result_id}"
                deleted = await self._redis_client.delete(key)
                return deleted > 0

        return False

    async def update(
        self,
        result_id: str,
        **kwargs
    ) -> Optional[StoredResult]:
        """更新结果"""
        result = await self.get(result_id)

        if not result:
            return None

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(result, key):
                setattr(result, key, value)

        result.updated_at = datetime.now().isoformat()

        # 重新存储
        async with self._lock:
            if self.store_type == "memory":
                self._results[result_id] = result

            elif self.store_type == "file":
                await self._store_to_file(result)

            elif self.store_type == "redis":
                await self._store_to_redis(result)

        return result

    async def clear(self):
        """清空所有结果"""
        async with self._lock:
            if self.store_type == "memory":
                self._results.clear()

            elif self.store_type == "file":
                for f in self.base_dir.glob("result_*.json"):
                    f.unlink()

            elif self.store_type == "redis":
                keys = await self._redis_client.keys("result:*")
                if keys:
                    await self._redis_client.delete(*keys)

        logger.info("Result store cleared")

    def count(self) -> int:
        """获取结果数量"""
        if self.store_type == "memory":
            return len(self._results)
        elif self.store_type == "file":
            return len(list(self.base_dir.glob("result_*.json")))
        elif self.store_type == "redis":
            # 需要同步查询
            return 0  # 简化处理
        return 0

    # 文件存储方法

    def _get_file_path(self, result_id: str) -> Path:
        """获取结果文件路径"""
        return self.base_dir / f"result_{result_id}.json"

    async def _store_to_file(self, result: StoredResult):
        """存储到文件"""
        file_path = self._get_file_path(result.result_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    async def _get_from_file(self, result_id: str) -> Optional[StoredResult]:
        """从文件读取"""
        file_path = self._get_file_path(result_id)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return StoredResult.from_dict(data)
        return None

    async def _get_from_file_by_task(self, task_id: str) -> Optional[StoredResult]:
        """通过任务ID从文件读取"""
        for file_path in self.base_dir.glob("result_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("task_id") == task_id:
                        return StoredResult.from_dict(data)
            except Exception:
                continue
        return None

    async def _get_all_from_file(self, limit: int) -> List[StoredResult]:
        """从文件读取所有结果"""
        results = []
        for file_path in self.base_dir.glob("result_*.json"):
            if len(results) >= limit:
                break
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append(StoredResult.from_dict(data))
            except Exception:
                continue
        return results

    async def _delete_from_file(self, result_id: str) -> bool:
        """从文件删除"""
        file_path = self._get_file_path(result_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    # Redis存储方法

    async def _store_to_redis(self, result: StoredResult):
        """存储到Redis"""
        key = f"result:{result.result_id}"
        await self._redis_client.setex(
            key,
            self.ttl,
            json.dumps(result.to_dict())
        )

    async def _get_from_redis(self, result_id: str) -> Optional[StoredResult]:
        """从Redis读取"""
        key = f"result:{result_id}"
        data = await self._redis_client.get(key)
        if data:
            return StoredResult.from_dict(json.loads(data))
        return None

    async def export_to_jsonl(self, file_path: str) -> int:
        """
        导出结果到JSONL文件

        Args:
            file_path: 输出文件路径

        Returns:
            导出的结果数量
        """
        results = await self.get_all(limit=10000)
        count = 0

        with open(file_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + '\n')
                count += 1

        logger.info(f"Exported {count} results to {file_path}")
        return count

    async def import_from_jsonl(self, file_path: str) -> int:
        """
        从JSONL文件导入结果

        Args:
            file_path: 输入文件路径

        Returns:
            导入的结果数量
        """
        count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    result = StoredResult.from_dict(data)
                    await self.store(
                        task_id=result.task_id,
                        success=result.success,
                        output=result.output,
                        error=result.error,
                        score=result.score,
                        execution_time=result.execution_time,
                        metadata=result.metadata,
                        result_id=result.result_id
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to import result: {e}")

        logger.info(f"Imported {count} results from {file_path}")
        return count
