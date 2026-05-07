"""
规划引擎 - 负责任务分解、执行计划制定和资源调度
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.logger import get_logger
from .cognitive import TaskModel


class PlanStatus(Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class PlanStep:
    id: str
    name: str
    description: Optional[str] = None
    status: str = "pending"
    estimated_duration: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    order: int = 0


@dataclass
class ExecutionPlan:
    id: str
    task_id: str
    title: str
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    estimated_total_duration: float = 0.0
    
    def add_step(self, name: str, **kwargs) -> PlanStep:
        step = PlanStep(
            id=f"{self.id}-step-{len(self.steps)}",
            name=name,
            order=len(self.steps),
            **kwargs
        )
        self.steps.append(step)
        self.estimated_total_duration += step.estimated_duration
        return step
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status.value,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "status": step.status,
                    "estimated_duration": step.estimated_duration,
                    "order": step.order
                }
                for step in self.steps
            ],
            "estimated_total_duration": self.estimated_total_duration
        }


class PlanningEngine:
    """规划引擎"""
    
    def __init__(self):
        self.logger = get_logger("planning-engine")
        
        self.task_templates = {
            "observation": [
                ("验证设备状态", 30, ["telescope"], []),
                ("定位目标", 60, ["mount"], []),
                ("设置拍摄参数", 15, ["camera"], []),
                ("执行拍摄", 60, ["camera", "mount"], ["设置拍摄参数"]),
                ("保存图像", 10, [], ["执行拍摄"]),
            ],
            "analysis": [
                ("加载数据", 30, ["database"], []),
                ("预处理", 60, ["computing"], ["加载数据"]),
                ("特征提取", 120, ["computing"], ["预处理"]),
                ("分析计算", 180, ["computing"], ["特征提取"]),
                ("生成报告", 30, [], ["分析计算"]),
            ],
            "research": [
                ("检索文献", 60, ["database"], []),
                ("构建假说", 120, [], ["检索文献"]),
                ("设计实验", 60, [], ["构建假说"]),
                ("收集证据", 300, ["telescope"], ["设计实验"]),
                ("验证假说", 120, ["computing"], ["收集证据"]),
            ],
        }
    
    def create_plan(self, task_model: TaskModel) -> ExecutionPlan:
        plan_id = f"plan-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        plan = ExecutionPlan(
            id=plan_id,
            task_id=f"task-{plan_id}",
            title=task_model.title
        )
        
        template = self.task_templates.get(task_model.type, [])
        
        for name, duration, resources, dependencies in template:
            plan.add_step(
                name=name,
                estimated_duration=duration,
                resources=resources,
                dependencies=dependencies
            )
        
        plan.status = PlanStatus.ACTIVE
        
        self.logger.info(f"Created plan: {plan.title} with {len(plan.steps)} steps")
        
        return plan