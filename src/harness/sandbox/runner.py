"""
TianwenAGI Harness - Sandbox执行器
在隔离容器中运行Agent评测任务
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Awaitable

from .config import SandboxConfig, ResourceLimits
from .container import DockerContainer, ContainerStatus, ContainerMetrics

logger = logging.getLogger("harness.sandbox.runner")


@dataclass
class SandboxResult:
    """沙箱执行结果"""
    sandbox_id: str
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    exit_code: int = 0
    execution_time: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    container_metrics: Optional[ContainerMetrics] = None
    logs: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "metrics": self.metrics,
            "logs": self.logs,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class SandboxRunner:
    """
    沙箱运行器
    在隔离的Docker容器中执行Agent任务
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._containers: Dict[str, DockerContainer] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running = False

    @property
    def max_concurrent(self) -> int:
        return self.config.max_concurrent_containers

    async def initialize(self):
        """初始化运行器"""
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_containers)
        self._running = True
        logger.info(f"SandboxRunner initialized with {self.config.max_concurrent_containers} max concurrent")

    async def cleanup(self):
        """清理所有容器"""
        logger.info("Cleaning up sandbox containers...")
        cleanup_tasks = []

        for sandbox_id, container in self._containers.items():
            cleanup_tasks.append(self._cleanup_container(sandbox_id, container))

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._containers.clear()
        self._running = False
        logger.info("SandboxRunner cleanup complete")

    async def _cleanup_container(self, sandbox_id: str, container: DockerContainer):
        """清理单个容器"""
        try:
            if container.is_running:
                await container.stop()
            await container.remove()
            logger.debug(f"Cleaned up container {sandbox_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup container {sandbox_id}: {e}")

    async def run_task(
        self,
        task_id: str,
        command: str | List[str],
        environment: Optional[Dict[str, str]] = None,
        sandbox_id: Optional[str] = None,
        wait_for_output: bool = True,
        timeout: Optional[int] = None
    ) -> SandboxResult:
        """
        在沙箱中运行单个任务

        Args:
            task_id: 任务ID
            command: 要执行的命令
            environment: 环境变量
            sandbox_id: 沙箱ID（用于复用已有容器）
            wait_for_output: 是否等待输出
            timeout: 超时时间（秒）

        Returns:
            SandboxResult: 执行结果
        """
        timeout = timeout or self.config.resources.timeout
        sandbox_id = sandbox_id or f"sandbox-{uuid.uuid4().hex[:8]}"

        result = SandboxResult(
            sandbox_id=sandbox_id,
            task_id=task_id,
            success=False
        )

        start_time = time.time()
        container = None

        async with self._semaphore:
            try:
                # 复用已有容器或创建新容器
                if sandbox_id in self._containers:
                    container = self._containers[sandbox_id]
                    if not container.is_running:
                        await container.start()
                else:
                    container = DockerContainer(self.config, name=sandbox_id)
                    await container.create()
                    await container.start()
                    self._containers[sandbox_id] = container

                # 在容器中执行命令
                exec_result = await asyncio.wait_for(
                    container.exec_run(
                        command=command,
                        environment=environment
                    ),
                    timeout=timeout
                )

                result.exit_code = exec_result["exit_code"]
                result.output = exec_result["output"]
                result.error = exec_result["error"] if exec_result["exit_code"] != 0 else None
                result.success = exec_result["exit_code"] == 0 and not exec_result["error"]

                # 获取资源使用统计
                result.container_metrics = await container.get_stats()

                # 获取日志
                result.logs = await container.get_logs()

            except asyncio.TimeoutError:
                result.error = f"Task execution timeout after {timeout}s"
                result.success = False
                logger.warning(f"Task {task_id} timed out")

            except Exception as e:
                result.error = str(e)
                result.success = False
                logger.error(f"Task {task_id} failed: {e}")

            finally:
                result.execution_time = time.time() - start_time

        return result

    async def run_tasks(
        self,
        tasks: List[Dict[str, Any]],
        task_executor: Optional[Callable] = None,
        continue_on_error: bool = True
    ) -> List[SandboxResult]:
        """
        批量运行任务

        Args:
            tasks: 任务列表，每项包含 task_id, command, environment
            task_executor: 自定义任务执行器（可选）
            continue_on_error: 遇到错误是否继续

        Returns:
            List[SandboxResult]: 结果列表
        """
        if not self._running:
            await self.initialize()

        logger.info(f"Running {len(tasks)} tasks in sandbox...")

        async def execute_task(task: Dict[str, Any]) -> SandboxResult:
            task_id = task.get("task_id", f"task-{uuid.uuid4().hex[:8]}")
            command = task.get("command")
            environment = task.get("environment")
            timeout = task.get("timeout")

            if task_executor:
                return await task_executor(task_id, command, environment, timeout)
            else:
                return await self.run_task(task_id, command, environment, timeout=timeout)

        if continue_on_error:
            results = await asyncio.gather(
                *[execute_task(t) for t in tasks],
                return_exceptions=True
            )
            # 处理异常结果
            processed_results = []
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    processed_results.append(SandboxResult(
                        sandbox_id="error",
                        task_id=tasks[i].get("task_id", f"task-{i}"),
                        success=False,
                        error=str(r)
                    ))
                else:
                    processed_results.append(r)
            return processed_results
        else:
            results = []
            for task in tasks:
                result = await execute_task(task)
                results.append(result)
                if not result.success:
                    break
            return results

    async def run_agent(
        self,
        task_id: str,
        agent_script: str,
        input_data: Dict[str, Any],
        sandbox_id: Optional[str] = None
    ) -> SandboxResult:
        """
        在沙箱中运行Agent脚本

        Args:
            task_id: 任务ID
            agent_script: Agent脚本路径或内容
            input_data: 输入数据
            sandbox_id: 沙箱ID

        Returns:
            SandboxResult: 执行结果
        """
        import json

        # 构建执行命令
        command = [
            "python", "-c",
            f"""
import json
import sys
input_data = json.loads(sys.stdin.read())
exec({repr(agent_script)})
"""
        ]

        environment = {
            "TW_TASK_ID": task_id,
            "TW_INPUT": json.dumps(input_data),
        }

        return await self.run_task(
            task_id=task_id,
            command=command,
            environment=environment,
            sandbox_id=sandbox_id
        )

    async def get_container_status(self, sandbox_id: str) -> Optional[ContainerStatus]:
        """获取容器状态"""
        container = self._containers.get(sandbox_id)
        return container.status if container else None

    async def get_container_metrics(self, sandbox_id: str) -> Optional[ContainerMetrics]:
        """获取容器资源使用指标"""
        container = self._containers.get(sandbox_id)
        return await container.get_stats() if container else None

    def get_active_containers(self) -> List[str]:
        """获取当前活跃的容器ID列表"""
        return [
            sandbox_id for sandbox_id, container in self._containers.items()
            if container.is_running
        ]

    async def scale_containers(self, count: int) -> List[str]:
        """
        预创建指定数量的容器

        Args:
            count: 容器数量

        Returns:
            容器ID列表
        """
        logger.info(f"Scaling to {count} containers...")

        async def create_container(i: int) -> Optional[str]:
            sandbox_id = f"sandbox-prescale-{i:03d}"
            try:
                container = DockerContainer(self.config, name=sandbox_id)
                await container.create()
                await container.start()
                self._containers[sandbox_id] = container
                return sandbox_id
            except Exception as e:
                logger.warning(f"Failed to create container {sandbox_id}: {e}")
                return None

        tasks = [create_container(i) for i in range(count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        container_ids = [r for r in results if r and not isinstance(r, Exception)]
        logger.info(f"Scaled to {len(container_ids)} containers")
        return container_ids

    def get_stats(self) -> Dict[str, Any]:
        """获取运行统计"""
        total = len(self._containers)
        running = sum(1 for c in self._containers.values() if c.is_running)

        return {
            "total_containers": total,
            "running_containers": running,
            "max_concurrent": self.max_concurrent,
            "config": {
                "image": self.config.image,
                "resources": self.config.resources.to_dict(),
            }
        }

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        return False
