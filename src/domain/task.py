"""
任务领域模型
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskType(Enum):
    OBSERVATION = "OBSERVATION"
    ANALYSIS = "ANALYSIS"
    RESEARCH = "RESEARCH"
    WORKFLOW = "WORKFLOW"
    LEARNING = "LEARNING"


@dataclass
class Task:
    id: str
    type: TaskType
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_id": self.parent_id,
            "metadata": self.metadata
        }


@dataclass
class TaskResult:
    task_id: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskStep:
    id: str
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    order: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TaskContext:
    task: Task
    steps: List[TaskStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_step(self, name: str) -> TaskStep:
        step = TaskStep(
            id=f"{self.task.id}-{len(self.steps)}",
            task_id=self.task.id,
            name=name,
            order=len(self.steps)
        )
        self.steps.append(step)
        return step
    
    def update_step(self, step_id: str, **kwargs):
        for step in self.steps:
            if step.id == step_id:
                for key, value in kwargs.items():
                    setattr(step, key, value)
                break
    
    def add_history(self, message: str, type: str = "info"):
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "type": type,
            "message": message
        })