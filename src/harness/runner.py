"""
TianwenAGI Harness - 多Agent多任务执行引擎
核心Runner，支持并发执行、任务调度、MCP工具集成
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor
import asyncio
import logging
import time
import json
import uuid

from .core import (
    BaseAgent, AgentConfig, AgentResult, AgentAction,
    BaseTask, TaskConfig, TaskResult, TaskInstance,
    BaseEvaluator, EvaluationConfig, EvaluationResult,
    TaskStatus
)
from .registry import HarnessRegistry

logger = logging.getLogger("harness.runner")


@dataclass
class RunConfig:
    """运行配置"""
    max_concurrent_agents: int = 4      # 最大并发Agent数
    max_concurrent_tasks: int = 8       # 最大并发任务数
    agent_timeout: int = 300           # Agent执行超时(秒)
    task_timeout: int = 600            # 任务执行超时(秒)
    timeout_seconds: int = 600          # 全局超时秒数
    retry_on_failure: bool = True       # 失败重试
    max_retries: int = 2              # 最大重试次数
    save_results: bool = True           # 保存结果
    results_dir: str = "./results"     # 结果目录
    verbose: bool = True
    parallel_execution: bool = True    # 并行执行
    enable_learning: bool = True       # 启用学习
    enable_mcp: bool = True            # 启用MCP
    enable_skill: bool = True          # 启用Skill集成
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """运行结果"""
    run_id: str = ""
    config: Optional[RunConfig] = None
    start_time: str = ""
    end_time: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    pass_rate: float = 0.0
    execution_time: float = 0.0
    total_execution_time: float = 0.0
    task_results: List[TaskResult] = field(default_factory=list)
    evaluation_results: List[EvaluationResult] = field(default_factory=list)
    agent_metrics: Dict[str, Any] = field(default_factory=dict)
    overall_score: float = 0.0
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_summary(self):
        if self.task_results:
            self.completed_tasks = sum(1 for r in self.task_results if r.success)
            self.failed_tasks = self.total_tasks - self.completed_tasks
            success_rate = self.completed_tasks / self.total_tasks if self.total_tasks > 0 else 0
            avg_score = sum(r.score for r in self.task_results) / self.total_tasks if self.total_tasks > 0 else 0
            self.overall_score = (success_rate + avg_score) / 2

        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.total_execution_time = (end - start).total_seconds()

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "overall_score": self.overall_score,
            "total_execution_time": self.total_execution_time,
            "success": self.success,
            "timestamp": self.start_time,
        }


class HarnessRunner:
    """
    TianwenAGI Harness 执行引擎
    核心组件：多Agent调度、任务并行执行、MCP工具集成、学习反馈
    """

    def __init__(self, config: RunConfig):
        self.config = config
        self.run_id = str(uuid.uuid4())[:8]
        self._agents: Dict[str, BaseAgent] = {}
        self._tasks: Dict[str, BaseTask] = {}
        self._evaluators: Dict[str, BaseEvaluator] = {}
        self._mcp_tools: Dict[str, Callable] = {}
        self._skill集成: Dict[str, Any] = {}
        self._result_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def initialize(
        self,
        agent_configs: List[AgentConfig],
        task_configs: List[TaskConfig],
        evaluator_configs: List[EvaluationConfig] = None
    ):
        """初始化Runner - 创建Agent和Task实例"""
        logger.info(f"[{self.run_id}] Initializing Harness Runner...")

        # 创建Agents
        for agent_cfg in agent_configs:
            try:
                agent = HarnessRegistry.create_agent(
                    agent_cfg.agent_type.value,
                    config=agent_cfg
                )
                # 注册MCP工具到Agent
                for tool_name in agent_cfg.tools:
                    if tool_name in _mcp_tools:
                        agent.register_tool(tool_name, _mcp_tools[tool_name])
                self._agents[agent.agent_id] = agent
                logger.info(f"  Created agent: {agent.name} [{agent.agent_id}]")
            except Exception as e:
                logger.error(f"  Failed to create agent {agent_cfg.name}: {e}")

        # 创建Tasks
        for task_cfg in task_configs:
            try:
                task = HarnessRegistry.create_task(
                    task_cfg.category.value,
                    config=task_cfg
                )
                self._tasks[task.task_id] = task
                logger.info(f"  Created task: {task.name} [{task.task_id}]")
            except Exception as e:
                logger.error(f"  Failed to create task {task_cfg.name}: {e}")

        # 创建Evaluators
        if evaluator_configs:
            for eval_cfg in evaluator_configs:
                try:
                    evaluator = HarnessRegistry.create_evaluator(
                        eval_cfg.grading_type,
                        config=eval_cfg
                    )
                    self._evaluators[eval_cfg.grading_type] = evaluator
                except Exception as e:
                    logger.error(f"  Failed to create evaluator: {e}")

        logger.info(f"[{self.run_id}] Initialization complete: {len(self._agents)} agents, {len(self._tasks)} tasks")

    async def register_mcp_tools(self, tools: Dict[str, Callable]):
        """注册MCP工具"""
        self._mcp_tools.update(tools)
        # 同步到所有Agent
        for agent in self._agents.values():
            for tool_name, tool_fn in tools.items():
                agent.register_tool(tool_name, tool_fn)
        logger.info(f"Registered {len(tools)} MCP tools")

    async def register_skills(self, skills: Dict[str, Any]):
        """注册Skill"""
        self._skill集成.update(skills)
        logger.info(f"Registered {len(skills)} skills")

    async def execute_single_task(
        self,
        task_instance: TaskInstance,
        agent: BaseAgent,
        evaluator: BaseEvaluator = None
    ) -> TaskResult:
        """执行单个任务"""
        task_result = TaskResult(
            task_id=task_instance.task_id,
            agent_id=agent.agent_id,
            success=False,
            output=None,
            status=TaskStatus.RUNNING
        )

        start_time = time.time()
        retries = 0

        while retries <= self.config.max_retries:
            try:
                # 调用Agent执行
                agent_result: AgentResult = await asyncio.wait_for(
                    agent.respond(task_instance.prompt, {
                        "task_id": task_instance.task_id,
                        "ground_truth": task_instance.ground_truth,
                        "reference_data": task_instance.reference_data,
                        "category": task_instance.config.category.value,
                    }),
                    timeout=self.config.agent_timeout
                )

                task_result.success = agent_result.success
                task_result.output = agent_result.output
                task_result.execution_time = time.time() - start_time
                task_result.tokens_used = agent_result.tokens_used
                task_result.tool_calls = agent_result.tool_calls
                task_result.steps = [{"type": "agent_execution", "actions": len(agent_result.actions)}]

                # 评估
                if evaluator:
                    eval_result = await evaluator.evaluate(
                        task_result,
                        task_instance.ground_truth,
                        task_instance.reference_data
                    )
                    task_result.score = eval_result.overall_score
                    task_result.metrics = {m.name: m.value for m in eval_result.metric_scores}

                task_result.status = TaskStatus.COMPLETED
                break

            except asyncio.TimeoutError:
                task_result.error = f"Timeout after {self.config.agent_timeout}s"
                task_result.status = TaskStatus.TIMEOUT
                logger.warning(f"Task {task_instance.task_id} timeout")
                break

            except Exception as e:
                retries += 1
                task_result.error = str(e)
                logger.error(f"Task {task_instance.task_id} error: {e}")
                if retries > self.config.max_retries:
                    task_result.status = TaskStatus.FAILED
                    break

        return task_result

    async def execute_batch(
        self,
        task_instances: List[TaskInstance],
        agent_configs: List[AgentConfig] = None,
        evaluator: BaseEvaluator = None
    ) -> List[TaskResult]:
        """批量执行任务"""
        if not self._agents and agent_configs:
            await self.initialize(agent_configs, [])

        results = []

        if self.config.parallel_execution:
            # 并行执行
            semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

            async def execute_with_semaphore(task_inst):
                async with semaphore:
                    # 选择Agent（简单轮询）
                    agent = list(self._agents.values())[hash(task_inst.task_id) % len(self._agents)]
                    return await self.execute_single_task(task_inst, agent, evaluator)

            results = await asyncio.gather(
                *[execute_with_semaphore(t) for t in task_instances],
                return_exceptions=True
            )
            # 处理异常结果
            results = [r if isinstance(r, TaskResult) else TaskResult(
                task_id="error",
                agent_id="error",
                success=False,
                error=str(r)
            ) for r in results]
        else:
            # 串行执行
            for task_inst in task_instances:
                agent = list(self._agents.values())[0]
                result = await self.execute_single_task(task_inst, agent, evaluator)
                results.append(result)

        return results

    async def run(
        self,
        tasks: List[TaskInstance],
        agent_configs: List[AgentConfig],
        evaluator: BaseEvaluator = None,
        metadata: Dict[str, Any] = None
    ) -> RunResult:
        """主运行入口"""
        run_result = RunResult(
            run_id=self.run_id,
            config=self.config,
            start_time=datetime.now().isoformat(),
            total_tasks=len(tasks),
        )

        try:
            self._running = True

            # 初始化
            await self.initialize(agent_configs, [], evaluator_configs=[evaluator.config] if evaluator else [])

            # 执行任务
            logger.info(f"[{self.run_id}] Starting execution of {len(tasks)} tasks...")
            task_results = await self.execute_batch(tasks, agent_configs, evaluator)
            run_result.task_results = task_results

            # 评估汇总
            run_result.calculate_summary()

            if evaluator and task_results:
                eval_results = []
                for tr in task_results:
                    instance = next((t for t in tasks if t.task_id == tr.task_id), None)
                    if instance:
                        er = await evaluator.evaluate(tr, instance.ground_truth)
                        eval_results.append(er)
                run_result.evaluation_results = eval_results

            run_result.success = True
            logger.info(f"[{self.run_id}] Execution complete: {run_result.completed_tasks}/{run_result.total_tasks} succeeded")

        except Exception as e:
            run_result.error = str(e)
            logger.error(f"[{self.run_id}] Run failed: {e}")

        finally:
            self._running = False
            run_result.end_time = datetime.now().isoformat()

        return run_result

    def get_status(self) -> Dict:
        """获取运行状态"""
        return {
            "run_id": self.run_id,
            "running": self._running,
            "agents": len(self._agents),
            "tasks": len(self._tasks),
            "config": {
                "max_concurrent_tasks": self.config.max_concurrent_tasks,
                "parallel_execution": self.config.parallel_execution,
                "enable_mcp": self.config.enable_mcp,
                "enable_skill": self.config.enable_skill,
            }
        }


# 快捷函数
async def run_benchmark(
    tasks: List[TaskInstance],
    agent_configs: List[AgentConfig],
    config: RunConfig = None
) -> RunResult:
    """快速运行评测"""
    if config is None:
        config = RunConfig()

    runner = HarnessRunner(config)

    # 创建默认evaluator
    from .core import AstronomicspecificEvaluator, EvaluationConfig
    eval_config = EvaluationConfig()
    evaluator = AstronomicspecificEvaluator(eval_config)

    return await runner.run(tasks, agent_configs, evaluator)
