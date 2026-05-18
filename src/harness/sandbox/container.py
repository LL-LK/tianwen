"""
TianwenAGI Harness - Docker容器管理
基于Docker SDK的容器生命周期管理
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Awaitable

logger = logging.getLogger("harness.sandbox.container")


class ContainerStatus(Enum):
    """容器状态"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"
    UNKNOWN = "unknown"


@dataclass
class ContainerMetrics:
    """容器资源使用指标"""
    container_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # CPU使用
    cpu_percent: float = 0.0
    cpu_user: float = 0.0
    cpu_system: float = 0.0

    # 内存使用
    memory_usage: int = 0           # bytes
    memory_limit: int = 0            # bytes
    memory_percent: float = 0.0

    # 网络IO
    network_rx: int = 0             # bytes
    network_tx: int = 0             # bytes

    # 块设备IO
    block_read: int = 0            # bytes
    block_write: int = 0           # bytes

    # PIDs
    pids: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id,
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_usage": self.memory_usage,
            "memory_limit": self.memory_limit,
            "memory_percent": self.memory_percent,
            "network_rx": self.network_rx,
            "network_tx": self.network_tx,
            "block_read": self.block_read,
            "block_write": self.block_write,
            "pids": self.pids,
        }


class DockerContainer:
    """
    Docker容器管理器
    提供容器的创建、启动、停止、监控等生命周期管理
    """

    def __init__(
        self,
        config,  # SandboxConfig
        container_id: Optional[str] = None,
        name: Optional[str] = None
    ):
        self.config = config
        self.container_id = container_id
        self.name = name or f"tianwen-sandbox-{uuid.uuid4().hex[:8]}"
        self._client = None
        self._container = None
        self._status = ContainerStatus.UNKNOWN
        self._metrics_history: List[ContainerMetrics] = []

    @property
    def status(self) -> ContainerStatus:
        """获取容器当前状态"""
        return self._status

    @property
    def is_running(self) -> bool:
        """检查容器是否运行中"""
        return self._status == ContainerStatus.RUNNING

    async def _get_client(self):
        """获取Docker客户端（延迟初始化）"""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
            except ImportError:
                logger.warning("Docker SDK not installed, using mock mode")
                self._client = None
        return self._client

    async def create(self) -> str:
        """
        创建容器

        Returns:
            container_id: 容器ID
        """
        client = await self._get_client()

        if client is None:
            # Mock模式
            self.container_id = f"mock-{uuid.uuid4().hex[:12]}"
            self._status = ContainerStatus.CREATED
            logger.info(f"[Mock] Container created: {self.container_id}")
            return self.container_id

        try:
            # 构建容器配置
            host_config = self._build_host_config()

            container = client.containers.run(
                image=self.config.image,
                name=self.name,
                detach=True,
                **host_config
            )

            self.container_id = container.id
            self._container = container
            self._status = ContainerStatus.CREATED

            logger.info(f"Container created: {self.container_id}")
            return self.container_id

        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            raise

    def _build_host_config(self) -> Dict[str, Any]:
        """构建Docker主机配置"""
        client = self._client
        if client is None:
            return {}

        import docker

        # 资源限制
        resources = self.config.resources
        mem_limit = self._parse_memory(resources.memory)

        host_config_kwargs = {
            "auto_remove": self.config.auto_remove,
            "network_mode": self.config.network_mode,
            "working_dir": self.config.work_dir,
        }

        # 内存限制
        if mem_limit:
            host_config_kwargs["mem_limit"] = mem_limit

        # CPU限制
        if resources.cpu:
            host_config_kwargs["cpu_period"] = 100000
            host_config_kwargs["cpu_quota"] = int(float(resources.cpu) * 100000)

        # GPU配置
        if resources.gpu > 0:
            host_config_kwargs["runtime"] = "nvidia"
            host_config_kwargs["environment"] = ["NVIDIA_VISIBLE_DEVICES=all"]

        # 共享内存
        if resources.shm_size:
            host_config_kwargs["shm_size"] = resources.shm_size

        # 卷挂载
        if self.config.volumes:
            host_config_kwargs["volumes"] = self.config.volumes

        # 环境变量
        if self.config.environment:
            host_config_kwargs["environment"] = self.config.environment

        # 只读文件系统
        if self.config.read_only:
            host_config_kwargs["read_only"] = True

        # 用户
        if self.config.user:
            host_config_kwargs["user"] = self.config.user

        # 日志配置
        host_config_kwargs["log_driver"] = self.config.log_driver
        host_config_kwargs["log_config"] = docker.types.LogConfig(
            config=self.config.log_options
        )

        host_config = client.api.create_host_config(**host_config_kwargs)
        return {"host_config": host_config}

    def _parse_memory(self, memory_str: str) -> Optional[int]:
        """解析内存字符串为字节数"""
        if not memory_str:
            return None

        units = {
            "b": 1,
            "k": 1024,
            "kb": 1024,
            "m": 1024 ** 2,
            "mb": 1024 ** 2,
            "g": 1024 ** 3,
            "gb": 1024 ** 3,
        }

        for unit, multiplier in units.items():
            if memory_str.lower().endswith(unit):
                try:
                    value = float(memory_str[:-len(unit)])
                    return int(value * multiplier)
                except ValueError:
                    pass

        # 尝试直接解析为整数（字节）
        try:
            return int(memory_str)
        except ValueError:
            return None

    async def start(self) -> bool:
        """
        启动容器

        Returns:
            success: 是否成功启动
        """
        if not self.container_id:
            raise RuntimeError("Container not created")

        client = await self._get_client()

        if client is None:
            self._status = ContainerStatus.RUNNING
            logger.info(f"[Mock] Container started: {self.container_id}")
            return True

        try:
            container = client.containers.get(self.container_id)
            container.start()
            self._container = container
            self._status = ContainerStatus.RUNNING
            logger.info(f"Container started: {self.container_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start container {self.container_id}: {e}")
            raise

    async def stop(self, timeout: int = 10) -> bool:
        """
        停止容器

        Args:
            timeout: 停止超时时间(秒)

        Returns:
            success: 是否成功停止
        """
        if not self.container_id:
            raise RuntimeError("Container not created")

        client = await self._get_client()

        if client is None:
            self._status = ContainerStatus.EXITED
            logger.info(f"[Mock] Container stopped: {self.container_id}")
            return True

        try:
            container = client.containers.get(self.container_id)
            container.stop(timeout=timeout)
            self._container = container
            self._status = ContainerStatus.EXITED
            logger.info(f"Container stopped: {self.container_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop container {self.container_id}: {e}")
            raise

    async def remove(self, force: bool = False) -> bool:
        """
        删除容器

        Args:
            force: 强制删除

        Returns:
            success: 是否成功删除
        """
        if not self.container_id:
            return True

        client = await self._get_client()

        if client is None:
            self._status = ContainerStatus.REMOVING
            logger.info(f"[Mock] Container removed: {self.container_id}")
            self.container_id = None
            return True

        try:
            container = client.containers.get(self.container_id)
            container.remove(force=force)
            self._status = ContainerStatus.REMOVING
            self.container_id = None
            self._container = None
            logger.info(f"Container removed: {self.container_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove container {self.container_id}: {e}")
            raise

    async def exec_run(
        self,
        command: str | List[str],
        work_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        在容器中执行命令

        Args:
            command: 要执行的命令
            work_dir: 工作目录
            environment: 环境变量
            user: 执行用户

        Returns:
            执行结果，包含 exit_code, output, error
        """
        if not self.container_id:
            raise RuntimeError("Container not created")

        client = await self._get_client()

        if client is None:
            # Mock模式
            return {
                "exit_code": 0,
                "output": f"[Mock] Executed: {command}",
                "error": ""
            }

        try:
            container = client.containers.get(self.container_id)

            # 确保容器运行
            if container.status != "running":
                container.start()
                self._status = ContainerStatus.RUNNING

            # 构建执行配置
            exec_config = {
                "detach": False,
                "stdout": True,
                "stderr": True,
            }

            if work_dir:
                exec_config["working_dir"] = work_dir

            exec_environment = dict(self.config.environment)
            if environment:
                exec_environment.update(environment)
            if exec_environment:
                exec_config["environment"] = exec_environment

            if user:
                exec_config["user"] = user

            # 执行命令
            _, exec_output = container.exec_run(command, **exec_config)

            output = exec_output.decode("utf-8") if exec_output else ""

            return {
                "exit_code": 0,
                "output": output,
                "error": ""
            }

        except Exception as e:
            logger.error(f"Failed to exec in container {self.container_id}: {e}")
            return {
                "exit_code": -1,
                "output": "",
                "error": str(e)
            }

    async def get_logs(self, tail: int = 100) -> str:
        """
        获取容器日志

        Args:
            tail: 最近的日志行数

        Returns:
            日志内容
        """
        if not self.container_id:
            return ""

        client = await self._get_client()

        if client is None:
            return "[Mock] Container logs..."

        try:
            container = client.containers.get(self.container_id)
            logs = container.logs(tail=tail).decode("utf-8")
            return logs

        except Exception as e:
            logger.error(f"Failed to get logs for {self.container_id}: {e}")
            return ""

    async def get_stats(self) -> ContainerMetrics:
        """
        获取容器资源使用统计

        Returns:
            容器指标
        """
        metrics = ContainerMetrics(container_id=self.container_id or "unknown")

        client = await self._get_client()

        if client is None:
            return metrics

        try:
            container = client.containers.get(self.container_id)
            stats = container.stats(stream=False)

            # 解析CPU使用
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            cpu_percent = 0.0
            if cpu_stats and precpu_stats:
                cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - \
                            precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                system_delta = cpu_stats.get("system_cpu_usage", 0) - \
                               precpu_stats.get("system_cpu_usage", 0)

                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100.0

            metrics.cpu_percent = cpu_percent

            # 解析内存使用
            mem_stats = stats.get("memory_stats", {})
            metrics.memory_usage = mem_stats.get("usage", 0)
            metrics.memory_limit = mem_stats.get("limit", 0)
            if metrics.memory_limit > 0:
                metrics.memory_percent = (metrics.memory_usage / metrics.memory_limit) * 100.0

            # 网络IO
            networks = stats.get("networks", {})
            if networks:
                rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
                tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())
                metrics.network_rx = rx_bytes
                metrics.network_tx = tx_bytes

            # 块设备IO
            blkio_stats = stats.get("blkio_stats", {})
            if blkio_stats:
                for entry in blkio_stats.get("io_service_bytes_recursive", []):
                    if entry.get("op", "").lower() == "read":
                        metrics.block_read += entry.get("value", 0)
                    elif entry.get("op", "").lower() == "write":
                        metrics.block_write += entry.get("value", 0)

            # PIDs
            metrics.pids = stats.get("pids_stats", {}).get("current", 0)

            self._metrics_history.append(metrics)

        except Exception as e:
            logger.error(f"Failed to get stats for {self.container_id}: {e}")

        return metrics

    async def pause(self) -> bool:
        """暂停容器"""
        if not self.container_id:
            raise RuntimeError("Container not created")

        client = await self._get_client()

        if client is None:
            self._status = ContainerStatus.PAUSED
            return True

        try:
            container = client.containers.get(self.container_id)
            container.pause()
            self._status = ContainerStatus.PAUSED
            return True

        except Exception as e:
            logger.error(f"Failed to pause container {self.container_id}: {e}")
            raise

    async def unpause(self) -> bool:
        """恢复容器"""
        if not self.container_id:
            raise RuntimeError("Container not created")

        client = await self._get_client()

        if client is None:
            self._status = ContainerStatus.RUNNING
            return True

        try:
            container = client.containers.get(self.container_id)
            container.unpause()
            self._status = ContainerStatus.RUNNING
            return True

        except Exception as e:
            logger.error(f"Failed to unpause container {self.container_id}: {e}")
            raise

    async def wait(self, condition: str = "not_running") -> int:
        """
        等待容器达到特定状态

        Args:
            condition: 条件，如 "running", "exited"

        Returns:
            退出码
        """
        if not self.container_id:
            raise RuntimeError("Container not created")

        client = await self._get_client()

        if client is None:
            await asyncio.sleep(0.1)
            return 0

        try:
            container = client.containers.get(self.container_id)
            result = container.wait(condition=condition)
            return result.get("StatusCode", -1)

        except Exception as e:
            logger.error(f"Failed to wait for container {self.container_id}: {e}")
            raise

    def get_metrics_history(self) -> List[ContainerMetrics]:
        """获取历史指标"""
        return self._metrics_history.copy()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.create()
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.config.cleanup_on_exit:
            await self.remove(force=True)
        return False
