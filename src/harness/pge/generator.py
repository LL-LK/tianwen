"""
TianwenAGI Harness - GeneratorAgent
计划执行器：执行规划步骤并返回结果
参考harnessa的PGE架构设计
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import logging
import asyncio
import time

from .planner import PlanStep, StepStatus

logger = logging.getLogger("harness.pge.generator")


@dataclass
class GenerationResult:
    """生成/执行结果"""
    step_id: str
    step_description: str
    success: bool
    output: Any = None
    execution_time: float = 0.0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    intermediate_results: List[Any] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "step_description": self.step_description,
            "success": self.success,
            "output": str(self.output)[:200] if self.output else None,
            "execution_time": self.execution_time,
            "tool_calls": len(self.tool_calls),
            "error": self.error,
            "timestamp": self.timestamp,
        }


class GeneratorAgent(ABC):
    """
    计划执行器基类
    执行规划步骤并返回结果
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 300)
        self.enable_parallel = self.config.get("enable_parallel", False)
        self.max_parallel = self.config.get("max_parallel", 3)
        self._tool_registry: Dict[str, Callable] = {}
        self._skill_registry: Dict[str, Any] = {}
        self._hooks: Dict[str, Callable] = {}

    def register_tool(self, name: str, handler: Callable):
        """注册工具处理器"""
        self._tool_registry[name] = handler

    def register_skill(self, name: str, skill: Any):
        """注册技能处理器"""
        self._skill_registry[name] = skill

    def register_hook(self, name: str, hook: Callable):
        """注册执行钩子"""
        self._hooks[name] = hook

    async def _call_hooks(self, name: str, *args, **kwargs):
        """调用注册的钩子"""
        if name in self._hooks:
            hook = self._hooks[name]
            if asyncio.iscoroutinefunction(hook):
                return await hook(*args, **kwargs)
            return hook(*args, **kwargs)

    @abstractmethod
    async def execute_step(self, step: PlanStep, context: Dict[str, Any] = None) -> GenerationResult:
        """
        执行单个步骤
        Args:
            step: 要执行的步骤
            context: 执行上下文
        Returns:
            GenerationResult: 执行结果
        """
        pass

    async def execute_plan(
        self,
        steps: List[PlanStep],
        context: Dict[str, Any] = None,
        progress_callback: Callable = None
    ) -> List[GenerationResult]:
        """
        执行计划中的所有步骤
        Args:
            steps: 步骤列表
            context: 执行上下文
            progress_callback: 进度回调函数
        Returns:
            List[GenerationResult]: 所有步骤的执行结果
        """
        context = context or {}
        results: List[GenerationResult] = []
        completed_steps: set = set()

        # 按依赖顺序执行
        pending_steps = list(steps)

        while pending_steps:
            # 找出所有可执行的步骤（依赖已满足）
            ready_steps = []
            still_pending = []

            for step in pending_steps:
                if step.is_ready(completed_steps):
                    ready_steps.append(step)
                else:
                    still_pending.append(step)

            if not ready_steps:
                # 没有可执行的步骤，可能是循环依赖
                logger.warning("No ready steps found, breaking to avoid infinite loop")
                break

            # 执行就绪的步骤
            if self.enable_parallel and len(ready_steps) > 1:
                # 并行执行
                batch_results = await self._execute_batch(ready_steps, context)
            else:
                # 串行执行
                batch_results = []
                for step in ready_steps:
                    result = await self._execute_single(step, context)
                    batch_results.append(result)

            # 收集结果
            for result in batch_results:
                results.append(result)
                if result.success:
                    completed_steps.add(result.step_id)
                    # 更新步骤状态
                    for step in steps:
                        if step.step_id == result.step_id:
                            step.status = StepStatus.COMPLETED
                            step.result = result.output
                            break
                else:
                    # 标记失败
                    for step in steps:
                        if step.step_id == result.step_id:
                            step.status = StepStatus.FAILED
                            step.error = result.error
                            break

                # 调用进度回调
                if progress_callback:
                    await self._call_hooks("progress", result, completed_steps, len(steps))

            # 更新待处理步骤
            pending_steps = still_pending

        return results

    async def _execute_batch(self, steps: List[PlanStep], context: Dict) -> List[GenerationResult]:
        """批量并行执行步骤"""
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_with_limit(step: PlanStep):
            async with semaphore:
                return await self._execute_single(step, context)

        results = await asyncio.gather(
            *[execute_with_limit(s) for s in steps],
            return_exceptions=True
        )

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(GenerationResult(
                    step_id=steps[i].step_id,
                    step_description=steps[i].description,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_single(self, step: PlanStep, context: Dict) -> GenerationResult:
        """执行单个步骤"""
        step.status = StepStatus.IN_PROGRESS
        start_time = time.time()

        try:
            # 调用前置钩子
            await self._call_hooks("pre_execute", step)

            # 执行步骤
            result = await asyncio.wait_for(
                self.execute_step(step, context),
                timeout=self.timeout
            )

            result.execution_time = time.time() - start_time

            # 调用后置钩子
            await self._call_hooks("post_execute", result)

            return result

        except asyncio.TimeoutError:
            logger.error(f"Step {step.step_id} timed out after {self.timeout}s")
            return GenerationResult(
                step_id=step.step_id,
                step_description=step.description,
                success=False,
                execution_time=time.time() - start_time,
                error=f"Timeout after {self.timeout}s"
            )

        except Exception as e:
            logger.error(f"Step {step.step_id} failed: {e}")
            return GenerationResult(
                step_id=step.step_id,
                step_description=step.description,
                success=False,
                execution_time=time.time() - start_time,
                error=str(e)
            )


class LLMBasedGenerator(GeneratorAgent):
    """
    基于LLM的执行器
    使用语言模型执行步骤
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.model = self.config.get("model", "minimax")
        self.temperature = self.config.get("temperature", 0.7)
        self._llm_handler = None

    def set_llm_handler(self, handler: Callable):
        """设置LLM处理器"""
        self._llm_handler = handler

    async def execute_step(self, step: PlanStep, context: Dict[str, Any] = None) -> GenerationResult:
        """使用LLM执行步骤"""
        context = context or {}

        # 构建执行提示
        prompt = self._build_execution_prompt(step, context)

        # 调用LLM
        if self._llm_handler:
            try:
                response = await self._llm_handler(
                    prompt=prompt,
                    model=self.model,
                    temperature=self.temperature
                )
                return GenerationResult(
                    step_id=step.step_id,
                    step_description=step.description,
                    success=True,
                    output=response,
                    tool_calls=[{"type": "llm", "model": self.model}]
                )
            except Exception as e:
                return GenerationResult(
                    step_id=step.step_id,
                    step_description=step.description,
                    success=False,
                    error=str(e)
                )
        else:
            # 无LLM时的回退
            return GenerationResult(
                step_id=step.step_id,
                step_description=step.description,
                success=True,
                output=f"Executed: {step.description}",
                metadata={"fallback": True}
            )

    def _build_execution_prompt(self, step: PlanStep, context: Dict) -> str:
        """构建执行提示"""
        return f"""Task: {step.description}
Action Type: {step.action_type}
Parameters: {step.parameters}
Context: {context}

Execute this step and provide the result."""
