"""
TianwenAGI Harness - 分布式配置
集群和worker节点配置
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class SchedulingStrategy(Enum):
    """调度策略"""
    ROUND_ROBIN = "round_robin"           # 轮询
    LEAST_LOADED = "least_loaded"         # 最低负载优先
    RANDOM = "random"                     # 随机分配
    PRIORITY = "priority"                  # 优先级优先
    AFFINITY = "affinity"                 # 亲和性调度


@dataclass
class WorkerConfig:
    """单个Worker节点配置"""
    worker_id: str
    name: str
    host: str = "localhost"
    port: int = 8765
    capacity: int = 1                        # 同时执行任务数
    enabled: bool = True
    tags: List[str] = field(default_factory=list)  # 标签，用于亲和性调度
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 资源限制
    max_memory_mb: int = 2048
    max_cpu_percent: int = 100
    max_gpu: int = 0

    # 连接配置
    connect_timeout: int = 30
    heartbeat_interval: int = 10
    max_consecutive_failures: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "capacity": self.capacity,
            "enabled": self.enabled,
            "tags": self.tags,
            "metadata": self.metadata,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_gpu": self.max_gpu,
        }

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class ClusterConfig:
    """集群配置"""
    cluster_id: str = "default"
    name: str = "TianwenAGI Cluster"

    # Worker节点列表
    workers: List[WorkerConfig] = field(default_factory=list)

    # 调度配置
    scheduling_strategy: SchedulingStrategy = SchedulingStrategy.ROUND_ROBIN
    max_concurrent_tasks: int = 10
    task_timeout: int = 300                  # 任务超时(秒)
    worker_timeout: int = 60                 # Worker无响应超时(秒)

    # 故障处理
    retry_on_worker_failure: bool = True
    max_retries_per_task: int = 2
    failover_enabled: bool = True

    # 监控
    enable_monitoring: bool = True
    metrics_interval: int = 30

    # 分布式执行
    result_aggregation: str = "collect"      # collect, reduce
    checkpoint_enabled: bool = True

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "worker_count": len(self.workers),
            "scheduling_strategy": self.scheduling_strategy.value,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "task_timeout": self.task_timeout,
            "retry_on_worker_failure": self.retry_on_worker_failure,
            "enable_monitoring": self.enable_monitoring,
        }

    def get_worker(self, worker_id: str) -> Optional[WorkerConfig]:
        """获取指定Worker配置"""
        for w in self.workers:
            if w.worker_id == worker_id:
                return w
        return None

    def get_enabled_workers(self) -> List[WorkerConfig]:
        """获取所有启用的Worker"""
        return [w for w in self.workers if w.enabled]


@dataclass
class DistributedConfig:
    """分布式执行整体配置"""
    mode: str = "local"                     # local, distributed, hybrid

    # 集群配置
    cluster: ClusterConfig = field(default_factory=ClusterConfig)

    # 本地执行配置（当mode为local或hybrid时）
    local_workers: int = 2                  # 本地worker数量
    local_queue_size: int = 100

    # 消息队列配置
    mq_type: str = "redis"                 # redis, rabbitmq, in_memory
    mq_url: Optional[str] = None            # 如 "redis://localhost:6379"
    mq_queue_name: str = "tianwen_tasks"
    mq_result_key: str = "tianwen_results"

    # Redis特定配置
    redis_max_connections: int = 50

    # 任务队列配置
    task_queue_size: int = 1000
    result_store_type: str = "memory"        # memory, redis, file

    # 异步执行
    async_execution: bool = True
    worker_sleep_interval: float = 0.1

    # 监控和日志
    log_level: str = "INFO"
    enable_progress: bool = True

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "cluster": self.cluster.to_dict(),
            "local_workers": self.local_workers,
            "mq_type": self.mq_type,
            "mq_queue_name": self.mq_queue_name,
            "task_queue_size": self.task_queue_size,
            "async_execution": self.async_execution,
        }

    @classmethod
    def from_cluster_config(cls, cluster_config: ClusterConfig) -> "DistributedConfig":
        """从集群配置创建分布式配置"""
        config = cls()
        config.cluster = cluster_config
        config.mode = "distributed"
        return config

    @classmethod
    def local_only(cls, num_workers: int = 2) -> "DistributedConfig":
        """创建仅本地执行的配置"""
        config = cls()
        config.mode = "local"
        config.local_workers = num_workers
        return config
