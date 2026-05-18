"""
TianwenAGI Harness - PlannerAgent
任务规划器：将复杂任务分解为可执行的步骤序列
参考harnessa的PGE架构设计
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import logging
import uuid

logger = logging.getLogger("harness.pge.planner")


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepPriority(Enum):
    """步骤优先级"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class PlanStep:
    """规划步骤"""
    step_id: str
    description: str
    action_type: str  # query, analyze, execute, evaluate, etc.
    dependencies: List[str] = field(default_factory=list)  # step_ids this depends on
    priority: StepPriority = StepPriority.MEDIUM
    status: StepStatus = StepStatus.PENDING
    estimated_duration: float = 0.0  # seconds
    skill_requirements: List[str] = field(default_factory=list)  # required skill names
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None

    def __post_init__(self):
        if not self.step_id:
            self.step_id = str(uuid.uuid4())[:12]

    def is_ready(self, completed_steps: set) -> bool:
        """检查步骤是否准备好执行（依赖都已完成）"""
        return all(dep_id in completed_steps for dep_id in self.dependencies)

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "action_type": self.action_type,
            "dependencies": self.dependencies,
            "priority": self.priority.name,
            "status": self.status.value,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
        }


@dataclass
class PlanResult:
    """规划结果"""
    plan_id: str
    original_task: str
    steps: List[PlanStep]
    total_estimated_duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())[:12]
        self.total_estimated_duration = sum(s.estimated_duration for s in self.steps)

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """获取指定步骤"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_ready_steps(self, completed: set) -> List[PlanStep]:
        """获取可执行的步骤（依赖已满足且未完成）"""
        ready = []
        for step in self.steps:
            if step.status == StepStatus.PENDING and step.is_ready(completed):
                ready.append(step)
        # Sort by priority
        ready.sort(key=lambda s: s.priority.value)
        return ready

    def get_completed_steps(self) -> set:
        """获取已完成的步骤ID集合"""
        return {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}

    def is_complete(self) -> bool:
        """检查计划是否完成"""
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)

    def success_rate(self) -> float:
        """计算成功率"""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return completed / len(self.steps)

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "original_task": self.original_task,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": len(self.steps),
            "completed_steps": len([s for s in self.steps if s.status == StepStatus.COMPLETED]),
            "total_estimated_duration": self.total_estimated_duration,
            "success_rate": self.success_rate(),
            "created_at": self.created_at,
        }


class PlannerAgent(ABC):
    """
    任务规划器基类
    将复杂任务分解为可执行的步骤序列
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_steps = self.config.get("max_steps", 20)
        self.enable_reflection = self.config.get("enable_reflection", True)
        self._hooks: Dict[str, Callable] = {}

    @abstractmethod
    async def create_plan(self, task: str, context: Dict[str, Any] = None) -> PlanResult:
        """
        创建执行计划
        Args:
            task: 原始任务描述
            context: 上下文信息（可选）
        Returns:
            PlanResult: 包含步骤序列的计划
        """
        pass

    @abstractmethod
    async def refine_plan(self, plan: PlanResult, feedback: Dict[str, Any]) -> PlanResult:
        """
        根据反馈优化计划
        Args:
            plan: 原始计划
            feedback: 反馈信息
        Returns:
            PlanResult: 优化后的计划
        """
        pass

    def register_hook(self, name: str, hook: Callable):
        """注册规划钩子"""
        self._hooks[name] = hook

    async def _call_hooks(self, name: str, *args, **kwargs):
        """调用注册的钩子"""
        if name in self._hooks:
            hook = self._hooks[name]
            if asyncio.iscoroutinefunction(hook):
                return await hook(*args, **kwargs)
            return hook(*args, **kwargs)


class LLMBasedPlanner(PlannerAgent):
    """
    基于LLM的规划器
    使用语言模型进行任务分解
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.model = self.config.get("model", "minimax")
        self.temperature = self.config.get("temperature", 0.7)
        self._llm_handler = None

    def set_llm_handler(self, handler: Callable):
        """设置LLM处理器"""
        self._llm_handler = handler

    async def create_plan(self, task: str, context: Dict[str, Any] = None) -> PlanResult:
        """使用LLM创建计划"""
        context = context or {}

        # 构建提示
        prompt = self._build_planning_prompt(task, context)

        # 调用LLM
        if self._llm_handler:
            response = await self._llm_handler(
                prompt=prompt,
                model=self.model,
                temperature=self.temperature
            )
        else:
            # 简单回退：创建默认计划
            response = self._default_planning(task, context)

        # 解析响应为PlanResult
        plan = self._parse_llm_response(task, response)

        # 调用后置钩子
        await self._call_hooks("post_plan_creation", plan)

        return plan

    async def refine_plan(self, plan: PlanResult, feedback: Dict[str, Any]) -> PlanResult:
        """根据反馈优化计划"""
        # 分析反馈
        failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
        slow_steps = [s for s in plan.steps if s.estimated_duration > 60]  # > 1 minute

        # 构建优化提示
        prompt = self._build_refinement_prompt(plan, feedback, failed_steps, slow_steps)

        if self._llm_handler:
            response = await self._llm_handler(prompt=prompt, model=self.model, temperature=self.temperature)
        else:
            response = self._default_refinement(plan, feedback)

        # 解析并返回优化后的计划
        refined_plan = self._parse_llm_response(plan.original_task, response)
        refined_plan.plan_id = plan.plan_id  # 保持相同plan_id

        return refined_plan

    def _build_planning_prompt(self, task: str, context: Dict) -> str:
        """构建规划提示"""
        return f"""Task: {task}

Context: {context}

Decompose this task into a sequence of executable steps. For each step provide:
1. Description
2. Action type (query, analyze, execute, evaluate, etc.)
3. Dependencies (other step IDs this depends on)
4. Priority (CRITICAL, HIGH, MEDIUM, LOW)
5. Estimated duration in seconds
6. Required skills

Return as a JSON array of steps."""

    def _build_refinement_prompt(self, plan: PlanResult, feedback: Dict, failed: List, slow: List) -> str:
        """构建优化提示"""
        return f"""Original Task: {plan.original_task}

Current Plan:
{[s.to_dict() for s in plan.steps]}

Feedback: {feedback}

Failed Steps: {[s.step_id for s in failed]}
Slow Steps: {[s.step_id for s in slow]}

Refine the plan based on the feedback. Return as a JSON array of steps."""

    def _default_planning(self, task: str, context: Dict) -> str:
        """默认规划（当没有LLM时）"""
        return f'[{{"step_id": "step_1", "description": "Execute: {task}", "action_type": "execute", "dependencies": [], "priority": "MEDIUM", "estimated_duration": 30}}]'

    def _default_refinement(self, plan: PlanResult, feedback: Dict) -> str:
        """默认优化"""
        return f'[{{"step_id": "{plan.steps[0].step_id}", "description": "{plan.steps[0].description}", "action_type": "{plan.steps[0].action_type}", "dependencies": [], "priority": "HIGH", "estimated_duration": 30}}]'

    def _parse_llm_response(self, task: str, response: str) -> PlanResult:
        """解析LLM响应为PlanResult"""
        import json

        steps = []
        try:
            # 尝试解析JSON
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response

            if isinstance(data, list):
                step_list = data
            elif isinstance(data, dict) and "steps" in data:
                step_list = data["steps"]
            else:
                step_list = [data]

            for item in step_list:
                step = PlanStep(
                    step_id=item.get("step_id", str(uuid.uuid4())[:12]),
                    description=item.get("description", ""),
                    action_type=item.get("action_type", "execute"),
                    dependencies=item.get("dependencies", []),
                    priority=StepPriority[item.get("priority", "MEDIUM")],
                    estimated_duration=item.get("estimated_duration", 30),
                    skill_requirements=item.get("skill_requirements", []),
                    parameters=item.get("parameters", {}),
                )
                steps.append(step)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}, using default step")
            # 回退：创建单一默认步骤
            steps.append(PlanStep(
                step_id="step_1",
                description=f"Execute: {task}",
                action_type="execute",
                priority=StepPriority.MEDIUM,
                estimated_duration=30,
            ))

        return PlanResult(
            plan_id=str(uuid.uuid4())[:12],
            original_task=task,
            steps=steps,
        )


# 导入asyncio
import asyncio
