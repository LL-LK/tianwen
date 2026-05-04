"""
天问-AGI Session持久化模块
SessionStore - Redis-backed会话管理与分布式锁

Issue #70

功能:
- RedisSessionStore: Redis-backed session管理
- SessionSerializer: JSON序列化/反序列化
- DistributedLock: 基于Redis的分布式锁

依赖:
    pip install redis
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import threading

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger("session_store")

# ============ 类型定义 ============

class SessionStatus(Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


@dataclass
class SessionData:
    """会话数据结构"""
    session_id: str
    created_at: str
    updated_at: str
    last_accessed: str
    user_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed": self.last_accessed,
            "user_id": self.user_id,
            "status": self.status.value,
            "data": self.data,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionData":
        return cls(
            session_id=d["session_id"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            last_accessed=d["last_accessed"],
            user_id=d.get("user_id"),
            status=SessionStatus(d.get("status", "active")),
            data=d.get("data", {}),
            metadata=d.get("metadata", {})
        )


@dataclass
class LockResult:
    """锁结果"""
    acquired: bool
    lock_id: Optional[str] = None
    expires_at: Optional[float] = None
    message: str = ""


# ============ JSON序列化器 ============

class SessionSerializer:
    """
    Session数据序列化/反序列化
    """

    @staticmethod
    def serialize(data: Dict[str, Any]) -> str:
        """序列化会话数据为JSON字符串"""
        return json.dumps(data, ensure_ascii=False, default=str)

    @staticmethod
    def deserialize(data: str) -> Dict[str, Any]:
        """反序列化JSON字符串为会话数据"""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Failed to deserialize session data: {data[:100]}")
            return {}

    @staticmethod
    def serialize_datetime(dt: datetime) -> str:
        """序列化datetime为ISO格式字符串"""
        return dt.isoformat()

    @staticmethod
    def deserialize_datetime(dt_str: str) -> datetime:
        """反序列化ISO格式字符串为datetime"""
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            return datetime.now()


# ============ 分布式锁 ============

class DistributedLock:
    """
    基于Redis的分布式锁

    功能:
    - 互斥锁获取
    - 锁自动过期
    - 锁续期
    - 原子性释放
    """

    LOCK_PREFIX = "lock:"

    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_timeout = 30  # 默认锁超时时间(秒)
        self.default_retry = 3  # 默认重试次数
        self.default_retry_delay = 0.1  # 默认重试延迟(秒)

    def acquire(
        self,
        resource: str,
        lock_id: Optional[str] = None,
        timeout: Optional[int] = None,
        retry: int = 3,
        retry_delay: float = 0.1
    ) -> LockResult:
        """
        获取锁

        Args:
            resource: 资源标识
            lock_id: 锁标识(默认生成UUID)
            timeout: 锁超时时间(秒)
            retry: 重试次数
            retry_delay: 重试延迟(秒)

        Returns:
            锁结果
        """
        if not lock_id:
            lock_id = str(uuid.uuid4())

        if timeout is None:
            timeout = self.default_timeout

        lock_key = f"{self.LOCK_PREFIX}{resource}"

        for attempt in range(retry):
            # 尝试设置锁 (NX: 不存在时设置, EX: 超时时间)
            acquired = self.redis.set(
                lock_key,
                lock_id,
                nx=True,
                ex=timeout
            )

            if acquired:
                expires_at = time.time() + timeout
                logger.info(f"Lock acquired: {resource} [{lock_id}] expires at {expires_at}")
                return LockResult(
                    acquired=True,
                    lock_id=lock_id,
                    expires_at=expires_at,
                    message="Lock acquired successfully"
                )

            # 等待后重试
            if attempt < retry - 1:
                time.sleep(retry_delay)

        return LockResult(
            acquired=False,
            message=f"Failed to acquire lock after {retry} attempts"
        )

    def release(self, resource: str, lock_id: str) -> bool:
        """
        释放锁 (Lua脚本保证原子性)

        Args:
            resource: 资源标识
            lock_id: 锁标识

        Returns:
            是否成功释放
        """
        lock_key = f"{self.LOCK_PREFIX}{resource}"

        # Lua脚本: 只有锁值匹配时才删除
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = self.redis.eval(lua_script, 1, lock_key, lock_id)
            if result:
                logger.info(f"Lock released: {resource} [{lock_id}]")
                return True
            else:
                logger.warning(f"Lock release failed: {resource} [{lock_id}] - not owned")
                return False
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False

    def extend(
        self,
        resource: str,
        lock_id: str,
        additional_time: int
    ) -> bool:
        """
        延长锁的持有时间

        Args:
            resource: 资源标识
            lock_id: 锁标识
            additional_time: 延长时间(秒)

        Returns:
            是否成功延长
        """
        lock_key = f"{self.LOCK_PREFIX}{resource}"

        # Lua脚本: 只有锁值匹配时才延长
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        try:
            result = self.redis.eval(lua_script, 1, lock_key, lock_id, additional_time)
            return bool(result)
        except Exception as e:
            logger.error(f"Lock extend error: {e}")
            return False

    def is_locked(self, resource: str) -> bool:
        """检查资源是否被锁定"""
        lock_key = f"{self.LOCK_PREFIX}{resource}"
        return self.redis.exists(lock_key) > 0

    def get_lock_info(self, resource: str) -> Optional[Dict[str, Any]]:
        """获取锁信息"""
        lock_key = f"{self.LOCK_PREFIX}{resource}"
        lock_data = self.redis.get(lock_key)

        if lock_data:
            ttl = self.redis.ttl(lock_key)
            return {
                "resource": resource,
                "lock_id": lock_data.decode() if isinstance(lock_data, bytes) else lock_data,
                "ttl": ttl
            }
        return None


# ============ Session存储 ============

class RedisSessionStore:
    """
    Redis-backed Session管理

    功能:
    - Session CRUD操作
    - 过期自动清理
    - 分布式访问支持
    - Session数据序列化
    """

    SESSION_PREFIX = "session:"
    SESSION_INDEX_KEY = "session:index"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 86400 * 7,  # 默认7天过期
        key_prefix: str = "hermes:"
    ):
        """
        初始化Redis Session存储

        Args:
            host: Redis主机地址
            port: Redis端口
            db: 数据库编号
            password: Redis密码
            default_ttl: 默认Session过期时间(秒)
            key_prefix: 键前缀
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

        self.redis: Optional[redis.Redis] = None
        self._lock: DistributedLock = None
        self._connected = False
        self._local_cache: Dict[str, SessionData] = {}
        self._cache_enabled = False
        self._cache_lock = threading.Lock()

        # 文件备份相关
        self._backup_dir = Path("backups/sessions")
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def connect(self) -> bool:
        """建立Redis连接"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis module not available, using file-based fallback")
            self._cache_enabled = True
            self._connected = False
            return False

        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # 测试连接
            self.redis.ping()
            self._lock = DistributedLock(self.redis)
            self._connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, using file-based fallback")
            self._cache_enabled = True
            self._connected = False
            return False

    def disconnect(self):
        """断开Redis连接"""
        if self.redis:
            self.redis.close()
        self._connected = False
        logger.info("Disconnected from Redis")

    @property
    def is_connected(self) -> bool:
        """检查是否已连接Redis"""
        return self._connected

    @property
    def lock(self) -> DistributedLock:
        """获取分布式锁实例"""
        return self._lock

    def _make_key(self, session_id: str) -> str:
        """生成完整的键名"""
        return f"{self.key_prefix}{self.SESSION_PREFIX}{session_id}"

    def _make_index_key(self) -> str:
        """生成索引键名"""
        return f"{self.key_prefix}{self.SESSION_INDEX_KEY}"

    # ============ Session CRUD ============

    def create(
        self,
        user_id: Optional[str] = None,
        initial_data: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> SessionData:
        """
        创建新Session

        Args:
            user_id: 用户ID
            initial_data: 初始数据
            ttl: 过期时间(秒)

        Returns:
            新建的Session数据
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()

        session = SessionData(
            session_id=session_id,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            last_accessed=now.isoformat(),
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            data=initial_data or {},
            metadata={"ttl": ttl or self.default_ttl}
        )

        if self._connected:
            self._save_to_redis(session)
            self._add_to_index(session_id)
        else:
            self._save_to_file(session)

        logger.info(f"Session created: {session_id}")
        return session

    def get(self, session_id: str) -> Optional[SessionData]:
        """
        获取Session

        Args:
            session_id: Session ID

        Returns:
            Session数据或None
        """
        # 先检查本地缓存
        with self._cache_lock:
            if session_id in self._local_cache:
                return self._local_cache[session_id]

        if self._connected:
            return self._load_from_redis(session_id)
        else:
            return self._load_from_file(session_id)

    def update(
        self,
        session_id: str,
        data: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        更新Session数据

        Args:
            session_id: Session ID
            data: 要更新的数据
            merge: 是否合并现有数据

        Returns:
            是否成功
        """
        session = self.get(session_id)
        if not session:
            logger.warning(f"Session not found for update: {session_id}")
            return False

        if merge:
            session.data.update(data)
        else:
            session.data = data

        session.updated_at = datetime.now().isoformat()
        session.last_accessed = session.updated_at

        if self._connected:
            self._save_to_redis(session)
        else:
            self._save_to_file(session)

        logger.info(f"Session updated: {session_id}")
        return True

    def delete(self, session_id: str) -> bool:
        """
        删除Session

        Args:
            session_id: Session ID

        Returns:
            是否成功
        """
        if self._connected:
            result = self._delete_from_redis(session_id)
        else:
            result = self._delete_from_file(session_id)

        if result:
            # 从本地缓存移除
            with self._cache_lock:
                self._local_cache.pop(session_id, None)
            self._remove_from_index(session_id)
            logger.info(f"Session deleted: {session_id}")

        return result

    def touch(self, session_id: str) -> bool:
        """
        更新Session的最后访问时间

        Args:
            session_id: Session ID

        Returns:
            是否成功
        """
        session = self.get(session_id)
        if not session:
            return False

        session.last_accessed = datetime.now().isoformat()

        if self._connected:
            self._save_to_redis(session)
        else:
            self._save_to_file(session)

        return True

    def exists(self, session_id: str) -> bool:
        """检查Session是否存在"""
        if self._connected:
            key = self._make_key(session_id)
            return self.redis.exists(key) > 0
        else:
            return self._session_file(session_id).exists()

    # ============ Redis操作 ============

    def _save_to_redis(self, session: SessionData):
        """保存Session到Redis"""
        key = self._make_key(session.session_id)
        ttl = session.metadata.get("ttl", self.default_ttl)

        data = SessionSerializer.serialize(session.to_dict())
        self.redis.setex(key, ttl, data)

        # 更新本地缓存
        with self._cache_lock:
            self._local_cache[session.session_id] = session

    def _load_from_redis(self, session_id: str) -> Optional[SessionData]:
        """从Redis加载Session"""
        key = self._make_key(session_id)
        data = self.redis.get(key)

        if not data:
            return None

        try:
            session_dict = SessionSerializer.deserialize(data)
            session = SessionData.from_dict(session_dict)

            # 更新本地缓存
            with self._cache_lock:
                self._local_cache[session_id] = session

            return session
        except Exception as e:
            logger.error(f"Failed to load session from Redis: {e}")
            return None

    def _delete_from_redis(self, session_id: str) -> bool:
        """从Redis删除Session"""
        key = self._make_key(session_id)
        return self.redis.delete(key) > 0

    def _add_to_index(self, session_id: str):
        """添加Session到索引"""
        index_key = self._make_index_key()
        self.redis.sadd(index_key, session_id)

    def _remove_from_index(self, session_id: str):
        """从索引移除Session"""
        index_key = self._make_index_key()
        self.redis.srem(index_key, session_id)

    # ============ 文件持久化 (Fallback) ============

    def _session_file(self, session_id: str) -> Path:
        """获取Session文件路径"""
        return self._backup_dir / f"{session_id}.json"

    def _save_to_file(self, session: SessionData):
        """保存Session到文件"""
        filepath = self._session_file(session.session_id)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

        # 更新本地缓存
        with self._cache_lock:
            self._local_cache[session.session_id] = session

    def _load_from_file(self, session_id: str) -> Optional[SessionData]:
        """从文件加载Session"""
        filepath = self._session_file(session_id)

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_dict = json.load(f)

            session = SessionData.from_dict(session_dict)

            # 检查是否过期
            last_accessed = datetime.fromisoformat(session.last_accessed)
            ttl = session.metadata.get("ttl", self.default_ttl)
            if (datetime.now() - last_accessed).total_seconds() > ttl:
                # 已过期，删除
                self._delete_from_file(session_id)
                return None

            # 更新本地缓存
            with self._cache_lock:
                self._local_cache[session_id] = session

            return session
        except Exception as e:
            logger.error(f"Failed to load session from file: {e}")
            return None

    def _delete_from_file(self, session_id: str) -> bool:
        """从文件删除Session"""
        filepath = self._session_file(session_id)

        if filepath.exists():
            filepath.unlink()
            return True
        return False

    # ============ 批量操作 ============

    def list_sessions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[SessionData]:
        """列出所有Session"""
        sessions = []

        if self._connected:
            index_key = self._make_index_key()
            session_ids = self.redis.srandmember(index_key, limit + offset)

            for sid in session_ids[offset:offset + limit]:
                session = self._load_from_redis(sid)
                if session:
                    sessions.append(session)
        else:
            # 从文件加载
            for filepath in sorted(self._backup_dir.glob("*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        session_dict = json.load(f)
                    sessions.append(SessionData.from_dict(session_dict))
                except Exception:
                    continue

        return sessions[offset:offset + limit]

    def cleanup_expired(self) -> int:
        """清理所有过期Session"""
        cleaned = 0

        if self._connected:
            index_key = self._make_index_key()
            session_ids = self.redis.smembers(index_key)

            for sid in session_ids:
                session = self._load_from_redis(sid)
                if session:
                    last_accessed = datetime.fromisoformat(session.last_accessed)
                    ttl = session.metadata.get("ttl", self.default_ttl)

                    if (datetime.now() - last_accessed).total_seconds() > ttl:
                        self.delete(sid)
                        cleaned += 1
        else:
            for filepath in list(self._backup_dir.glob("*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        session_dict = json.load(f)

                    session = SessionData.from_dict(session_dict)
                    last_accessed = datetime.fromisoformat(session.last_accessed)
                    ttl = session.metadata.get("ttl", self.default_ttl)

                    if (datetime.now() - last_accessed).total_seconds() > ttl:
                        filepath.unlink()
                        cleaned += 1
                except Exception:
                    continue

        logger.info(f"Cleaned up {cleaned} expired sessions")
        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        if self._connected:
            index_key = self._make_index_key()
            total = self.redis.scard(index_key)

            return {
                "backend": "redis",
                "host": self.host,
                "port": self.port,
                "total_sessions": total,
                "connected": True
            }
        else:
            total = len(list(self._backup_dir.glob("*.json")))

            return {
                "backend": "file",
                "backup_dir": str(self._backup_dir),
                "total_sessions": total,
                "connected": False
            }


# ============ 便捷函数 ============

def create_session_store(
    redis_url: Optional[str] = None,
    **kwargs
) -> RedisSessionStore:
    """
    创建Session存储实例的便捷函数

    用法:
        store = create_session_store(redis_url="redis://localhost:6379/0")
        store.connect()
    """
    store = RedisSessionStore(**kwargs)

    if redis_url:
        # 解析redis:// URL
        import urllib.parse
        parsed = urllib.parse.urlparse(redis_url)

        store.host = parsed.hostname or "localhost"
        store.port = parsed.port or 6379
        store.db = int(parsed.path.lstrip("/") or 0)
        store.password = parsed.password

    store.connect()
    return store


if __name__ == "__main__":
    async def test():
        print("Testing RedisSessionStore...")

        # 创建存储实例
        store = create_session_store()

        print(f"Connected: {store.is_connected}")
        print(f"Backend: {store.get_stats()}")

        # 创建Session
        session = store.create(
            user_id="test_user",
            initial_data={"name": "Test User", "role": "admin"}
        )
        print(f"Created session: {session.session_id}")

        # 获取Session
        loaded = store.get(session.session_id)
        print(f"Loaded session: {loaded.data if loaded else None}")

        # 更新Session
        store.update(session.session_id, {"last_login": datetime.now().isoformat()})
        updated = store.get(session.session_id)
        print(f"Updated data: {updated.data if updated else None}")

        # 删除Session
        store.delete(session.session_id)
        print(f"Exists after delete: {store.exists(session.session_id)}")

        # 清理过期
        cleaned = store.cleanup_expired()
        print(f"Cleaned expired: {cleaned}")

    import asyncio
    asyncio.run(test())
