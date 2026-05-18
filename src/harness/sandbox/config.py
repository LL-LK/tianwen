"""
TianwenAGI Harness - Sandbox配置
Docker容器资源限制和镜像配置
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class ContainerImage(Enum):
    """预定义容器镜像"""
    PYTHON_3_11 = "python:3.11-slim"
    PYTHON_3_12 = "python:3.12-slim"
    PYTHON_3_11_FULL = "python:3.11"
    TIANWEN_AGI_LATEST = "tianwenagi/harness:latest"
    TIANWEN_AGI_GPU = "tianwenagi/harness:gpu"
    ASTRO_PYTHON = "astron Foundational/astro-python:latest"


@dataclass
class ResourceLimits:
    """资源限制配置"""
    memory: str = "2g"                    # 内存限制，如 "2g", "512m"
    cpu: str = "1.0"                     # CPU限制，如 "1.0", "0.5"
    gpu: int = 0                          # GPU数量，0表示不使用GPU
    shm_size: str = "64m"                # 共享内存大小
    timeout: int = 300                   # 执行超时(秒)
    max_open_files: int = 1024           # 最大打开文件数
    max_processes: int = 256             # 最大进程数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory": self.memory,
            "cpu": self.cpu,
            "gpu": self.gpu,
            "shm_size": self.shm_size,
            "timeout": self.timeout,
            "max_open_files": self.max_open_files,
            "max_processes": self.max_processes,
        }


@dataclass
class SandboxConfig:
    """Sandbox沙箱配置"""
    # 镜像配置
    image: str = ContainerImage.PYTHON_3_11.value
    image_pull_policy: str = "IfNotPresent"  # Always, IfNotPresent, Never

    # 资源限制
    resources: ResourceLimits = field(default_factory=ResourceLimits)

    # 网络配置
    network_mode: str = "bridge"          # bridge, host, none
    dns: List[str] = field(default_factory=list)

    # 卷挂载
    volumes: Dict[str, str] = field(default_factory=dict)  # host_path: container_path
    work_dir: str = "/workspace"

    # 环境变量
    environment: Dict[str, str] = field(default_factory=dict)

    # 安全配置
    read_only: bool = False
    drop_capabilities: List[str] = field(default_factory=lambda: ["ALL"])
    user: Optional[str] = None             # 用户名或UID，如 "nobody" 或 "65534"

    # 容器生命周期
    auto_remove: bool = True
    restart_policy: str = "no"            # no, always, on-failure

    # 清理配置
    cleanup_on_exit: bool = True

    # 日志配置
    log_driver: str = "json-file"
    log_options: Dict[str, str] = field(default_factory=lambda: {
        "max-size": "10m",
        "max-file": "3"
    })

    # 并行配置
    max_concurrent_containers: int = 4

    # 调试
    debug: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image": self.image,
            "image_pull_policy": self.image_pull_policy,
            "resources": self.resources.to_dict(),
            "network_mode": self.network_mode,
            "dns": self.dns,
            "volumes": self.volumes,
            "work_dir": self.work_dir,
            "environment": self.environment,
            "read_only": self.read_only,
            "drop_capabilities": self.drop_capabilities,
            "user": self.user,
            "auto_remove": self.auto_remove,
            "restart_policy": self.restart_policy,
            "cleanup_on_exit": self.cleanup_on_exit,
            "log_driver": self.log_driver,
            "log_options": self.log_options,
            "max_concurrent_containers": self.max_concurrent_containers,
            "debug": self.debug,
        }

    @classmethod
    def from_preset(cls, preset: str) -> "SandboxConfig":
        """从预设创建配置"""
        presets = {
            "default": cls(),
            "cpu_small": cls(
                resources=ResourceLimits(memory="1g", cpu="0.5", timeout=180)
            ),
            "cpu_medium": cls(
                resources=ResourceLimits(memory="4g", cpu="2.0", timeout=600)
            ),
            "gpu": cls(
                image=ContainerImage.TIANWEN_AGI_GPU.value,
                resources=ResourceLimits(memory="8g", cpu="4.0", gpu=1, timeout=900)
            ),
            "astro": cls(
                image=ContainerImage.ASTRO_PYTHON.value,
                resources=ResourceLimits(memory="4g", cpu="2.0", timeout=600)
            ),
        }
        return presets.get(preset, cls())
