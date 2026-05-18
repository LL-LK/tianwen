"""
TianwenAGI Harness - CI/CD执行器
Docker容器化执行Benchmark
"""
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .config import CIConfig, WebhookConfig, DockerConfig
from .github_actions import GitHubActionsReporter

logger = logging.getLogger("harness.ci.runner")


@dataclass
class CIResult:
    """CI执行结果"""
    run_id: str
    config: CIConfig
    success: bool
    start_time: str
    end_time: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    overall_score: float = 0.0
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "success": self.success,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "overall_score": self.overall_score,
            "error": self.error,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
        }


class CIRunner:
    """
    CI/CD执行器
    支持Docker容器化执行、Webhook通知
    """

    def __init__(self, config: CIConfig):
        self.config = config
        self.run_id = str(uuid.uuid4())[:8]
        self._reporter: Optional[GitHubActionsReporter] = None
        self._docker_available: bool = self._check_docker()
        self._results: List[CIResult] = []

    def _check_docker(self) -> bool:
        """检查Docker是否可用"""
        import shutil
        return shutil.which("docker") is not None

    async def run_benchmark(
        self,
        benchmark_config_path: str,
        agent_configs: List[Dict[str, Any]],
        output_path: str = None
    ) -> CIResult:
        """
        运行Benchmark（本地或Docker中）

        Args:
            benchmark_config_path: Benchmark配置文件路径
            agent_configs: Agent配置列表
            output_path: 输出路径

        Returns:
            CIResult结果
        """
        result = CIResult(
            run_id=self.run_id,
            config=self.config,
            success=False,
            start_time=datetime.now().isoformat(),
        )

        try:
            # 创建reporter
            self._reporter = GitHubActionsReporter(
                output_dir=self.config.output_dir,
                output_format=self.config.output_format
            )
            self._reporter.set_run_id(self.run_id)

            # 加载Benchmark配置
            from ..benchmark import BenchmarkLoader, BenchmarkRunner, BenchmarkConfig
            benchmark_config = BenchmarkLoader.load_from_file(benchmark_config_path)

            # 通知开始
            self._reporter.report_start(
                benchmark_name=benchmark_config.name,
                total_tasks=benchmark_config.total_tasks,
                metadata={"config": benchmark_config.to_dict()}
            )

            # 准备Agent配置
            from ..core import AgentConfig, AgentType
            agent_cfg_list = []
            for ac in agent_configs:
                agent_type = AgentType(ac.get("agent_type", "researcher"))
                agent_cfg = AgentConfig(
                    name=ac.get("name", "CI-Agent"),
                    agent_type=agent_type,
                    capabilities=ac.get("capabilities", []),
                    tools=ac.get("tools", []),
                )
                agent_cfg_list.append(agent_cfg)

            # 运行Benchmark
            if self.config.docker.image and self._docker_available:
                # Docker模式
                benchmark_result = await self._run_in_docker(benchmark_config, agent_cfg_list)
            else:
                # 本地模式
                benchmark_runner = BenchmarkRunner(benchmark_config)
                benchmark_result = await benchmark_runner.run(agent_cfg_list)

            # 更新结果
            result.total_tasks = benchmark_result.total_tasks
            result.completed_tasks = benchmark_result.completed_tasks
            result.failed_tasks = benchmark_result.failed_tasks
            result.overall_score = benchmark_result.overall_score
            result.success = benchmark_result.success

            # 生成artifacts
            if output_path:
                result.artifacts.append(output_path)
            else:
                artifacts_dir = Path(self.config.artifacts_dir)
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                artifact_path = artifacts_dir / f"benchmark_results_{self.run_id}.json"
                with open(artifact_path, 'w') as f:
                    json.dump(benchmark_result.to_dict(), f, indent=2)
                result.artifacts.append(str(artifact_path))

            # 通知完成
            self._reporter.report_complete(
                benchmark_name=benchmark_config.name,
                total_tasks=result.total_tasks,
                completed_tasks=result.completed_tasks,
                failed_tasks=result.failed_tasks,
                overall_score=result.overall_score,
                execution_time=benchmark_result.total_execution_time,
                level_scores=benchmark_result.level_scores,
            )

            # 发送Webhook通知
            await self._send_webhook_notifications("complete", result)

            logger.info(f"[{self.run_id}] CI benchmark complete: {result.completed_tasks}/{result.total_tasks} passed")

        except Exception as e:
            result.error = str(e)
            result.success = False
            logger.error(f"[{self.run_id}] CI benchmark failed: {e}")

            self._reporter.report_failure(
                benchmark_name=getattr(self, '_benchmark_name', 'unknown'),
                error=str(e)
            )
            await self._send_webhook_notifications("fail", result)

        finally:
            result.end_time = datetime.now().isoformat()
            self._results.append(result)

        return result

    async def _run_in_docker(
        self,
        benchmark_config,
        agent_configs: List
    ):
        """在Docker容器中运行"""
        import docker

        docker_config = self.config.docker
        client = docker.from_env()

        # 构建容器挂载卷
        volumes = {
            str(Path.cwd()): {"bind": "/workspace", "mode": "ro"},
        }
        for host_path, container_path in docker_config.volumes.items():
            volumes[host_path] = {"bind": container_path, "mode": "rw"}

        # 设置环境变量
        environment = {
            "BENCHMARK_CONFIG": "/workspace/benchmark.yaml",
            "OUTPUT_DIR": "/workspace/results",
        }
        environment.update(docker_config.environment)

        # GPU支持
        device_requests = []
        if docker_config.use_gpu:
            device_requests.append(
                docker.types.DeviceRequest(
                    count=-1,
                    capabilities=[["gpu"]]
                )
            )

        try:
            # 拉取镜像
            logger.info(f"Pulling Docker image: {docker_config.image}")
            client.images.pull(docker_config.image)

            # 运行容器
            container = client.containers.run(
                docker_config.image,
                command="python -m harness.benchmark.run",
                volumes=volumes,
                environment=environment,
                network=docker_config.network,
                mem_limit=docker_config.memory_limit,
                cpu_period=docker_config.cpu_limit,
                shm_size=docker_config.shm_size,
                device_requests=device_requests,
                detach=True,
                remove=docker_config.remove_on_exit,
                name=docker_config.container_name or f"harness-{self.run_id}",
            )

            # 等待容器完成
            logger.info(f"Container {container.short_id} started, waiting for completion...")
            result = container.wait()

            # 获取日志
            logs = container.logs().decode('utf-8')
            logger.debug(f"Container logs: {logs}")

            # 检查结果
            if result['StatusCode'] != 0:
                raise RuntimeError(f"Container exited with code {result['StatusCode']}: {logs}")

            # 读取结果文件
            output_file = Path("results") / f"{benchmark_config.name}_{self.run_id}.json"
            if output_file.exists():
                with open(output_file, 'r') as f:
                    return json.load(f)

            raise RuntimeError("No result file found in container output")

        finally:
            # 清理容器
            try:
                container.remove(force=True)
            except Exception:
                pass

    async def _send_webhook_notifications(self, event: str, result: CIResult):
        """发送Webhook通知"""
        for webhook in self.config.webhooks:
            if not webhook.enabled:
                continue
            if event not in webhook.events:
                continue

            try:
                await self._send_webhook(webhook, result, event)
            except Exception as e:
                logger.error(f"Failed to send webhook to {webhook.url}: {e}")

    async def _send_webhook(
        self,
        webhook: WebhookConfig,
        result: CIResult,
        event: str
    ):
        """发送单个Webhook"""
        import aiohttp

        payload = {
            "event": event,
            "run_id": result.run_id,
            "timestamp": datetime.now().isoformat(),
            "result": result.to_dict(),
        }

        async with aiohttp.ClientSession() as session:
            for attempt in range(webhook.retry_count):
                try:
                    async with session.request(
                        webhook.method,
                        webhook.url,
                        json=payload,
                        headers=webhook.headers,
                        timeout=aiohttp.ClientTimeout(total=webhook.timeout)
                    ) as response:
                        if response.status < 400:
                            logger.info(f"Webhook sent successfully to {webhook.url}")
                            return
                        logger.warning(f"Webhook returned status {response.status}")
                except Exception as e:
                    if attempt == webhook.retry_count - 1:
                        raise
                    await asyncio.sleep(webhook.retry_delay)

    def get_results(self) -> List[CIResult]:
        """获取所有结果"""
        return self._results

    def get_latest_result(self) -> Optional[CIResult]:
        """获取最新结果"""
        return self._results[-1] if self._results else None
