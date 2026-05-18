"""
TianwenAGI Harness - CI/CD配置
Webhook通知、Docker容器配置
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class WebhookConfig:
    """Webhook通知配置"""
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=lambda: {"Content-Type": "application/json"})
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    enabled: bool = True
    events: List[str] = field(default_factory=list)  # "start", "complete", "fail"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "headers": self.headers,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "enabled": self.enabled,
            "events": self.events,
        }


@dataclass
class DockerConfig:
    """Docker容器配置"""
    image: str = "tianwenagi/harness:latest"
    container_name: Optional[str] = None
    volumes: Dict[str, str] = field(default_factory=dict)  # host_path: container_path
    environment: Dict[str, str] = field(default_factory=dict)
    network: str = "bridge"
    memory_limit: Optional[str] = None  # e.g., "4g"
    cpu_limit: Optional[str] = None  # e.g., "2"
    shm_size: Optional[str] = None  # e.g., "2g"
    remove_on_exit: bool = True
    use_gpu: bool = False
    runtime: Optional[str] = None  # e.g., "nvidia"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image": self.image,
            "container_name": self.container_name,
            "volumes": self.volumes,
            "environment": self.environment,
            "network": self.network,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "shm_size": self.shm_size,
            "remove_on_exit": self.remove_on_exit,
            "use_gpu": self.use_gpu,
            "runtime": self.runtime,
        }


@dataclass
class CIConfig:
    """CI/CD整体配置"""
    repository: str = ""
    branch: str = "main"
    commit_sha: str = ""
    run_id: str = ""
    workflow: str = "benchmark"
    event: str = "push"  # push, pull_request, schedule, etc.

    # GitHub Actions相关
    github_token: Optional[str] = None
    github_api_url: str = "https://api.github.com"

    # Webhook通知
    webhooks: List[WebhookConfig] = field(default_factory=list)

    # Docker执行
    docker: DockerConfig = field(default_factory=DockerConfig)

    # 输出设置
    output_format: str = "json"  # json, jsonl
    output_dir: str = "./ci_results"
    artifacts_dir: str = "./artifacts"

    # 并行执行
    parallel: bool = True
    max_workers: int = 4

    # 标记
    labels: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository": self.repository,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "run_id": self.run_id,
            "workflow": self.workflow,
            "event": self.event,
            "docker": self.docker.to_dict(),
            "output_format": self.output_format,
            "output_dir": self.output_dir,
            "artifacts_dir": self.artifacts_dir,
            "parallel": self.parallel,
            "max_workers": self.max_workers,
            "labels": self.labels,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_github_env(cls) -> "CIConfig":
        """从GitHub Actions环境变量创建配置"""
        import os

        config = cls(
            repository=os.environ.get("GITHUB_REPOSITORY", ""),
            branch=os.environ.get("GITHUB_REF_NAME", "main"),
            commit_sha=os.environ.get("GITHUB_SHA", ""),
            run_id=os.environ.get("GITHUB_RUN_ID", ""),
            workflow=os.environ.get("GITHUB_WORKFLOW", "benchmark"),
            event=os.environ.get("GITHUB_EVENT_NAME", "push"),
            github_token=os.environ.get("GITHUB_TOKEN"),
        )

        # 从GITHUB_OUTPUT读取额外变量
        github_output = os.environ.get("GITHUB_OUTPUT", "")
        if github_output:
            try:
                for line in github_output.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key == "benchmark_name":
                            config.metadata["benchmark_name"] = value
            except Exception:
                pass

        return config
