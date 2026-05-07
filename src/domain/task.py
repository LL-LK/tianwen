"""
任务领域模型

提供任务相关的核心数据结构和类型定义。
"""

from typing import Optional, Dict, Any, List, Union, Callable
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field, asdict


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class TaskType(Enum):
    """任务类型枚举"""
    OBSERVATION = "OBSERVATION"
    ANALYSIS = "ANALYSIS"
    RESEARCH = "RESEARCH"
    WORKFLOW = "WORKFLOW"
    LEARNING = "LEARNING"
    DATA_MINING = "DATA_MINING"
    COORDINATION = "COORDINATION"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4


@dataclass
class Task:
    """任务模型"""
    id: str
    type: TaskType
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = TaskPriority.NORMAL.value
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
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
            "metadata": self.metadata,
            "tags": self.tags
        }
    
    def update_status(self, new_status: TaskStatus) -> bool:
        """更新任务状态"""
        self.status = new_status
        self.updated_at = datetime.now()
        
        if new_status == TaskStatus.RUNNING and not self.started_at:
            self.started_at = datetime.now()
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.completed_at = datetime.now()
        
        return True
    
    def is_terminal(self) -> bool:
        """是否为终态"""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED
        )
    
    def duration(self) -> Optional[float]:
        """计算任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None


@dataclass
class TaskResult:
    """任务结果模型"""
    task_id: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat(),
            "metrics": self.metrics
        }


@dataclass
class TaskStep:
    """任务步骤模型"""
    id: str
    task_id: str
    name: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    order: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "order": self.order,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class TaskContext:
    """任务上下文"""
    task: Task
    steps: List[TaskStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_step(self, name: str, description: str = None) -> TaskStep:
        """添加步骤"""
        step = TaskStep(
            id=f"{self.task.id}-step-{len(self.steps)}",
            task_id=self.task.id,
            name=name,
            description=description,
            order=len(self.steps)
        )
        self.steps.append(step)
        return step
    
    def update_step(self, step_id: str, **kwargs):
        """更新步骤"""
        for step in self.steps:
            if step.id == step_id:
                for key, value in kwargs.items():
                    if hasattr(step, key):
                        setattr(step, key, value)
                break
    
    def add_history(self, message: str, type: str = "info", data: Dict[str, Any] = None):
        """添加历史记录"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "type": type,
            "message": message,
            "data": data or {}
        })
    
    def get_step(self, step_id: str) -> Optional[TaskStep]:
        """获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_completed_steps(self) -> List[TaskStep]:
        """获取已完成步骤"""
        return [s for s in self.steps if s.status == TaskStatus.COMPLETED]
    
    def get_failed_step(self) -> Optional[TaskStep]:
        """获取失败的步骤"""
        for step in self.steps:
            if step.status == TaskStatus.FAILED:
                return step
        return None


class TaskFactory:
    """任务工厂类"""
    
    @staticmethod
    def create_observation_task(target_name: str, ra: float, dec: float, **kwargs) -> Task:
        """创建观测任务"""
        return Task(
            id=f"obs-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=TaskType.OBSERVATION,
            title=f"观测 {target_name}",
            description=f"观测目标: {target_name} (RA: {ra}, DEC: {dec})",
            metadata={"target_name": target_name, "ra": ra, "dec": dec, **kwargs}
        )
    
    @staticmethod
    def create_analysis_task(name: str, data_source: str, **kwargs) -> Task:
        """创建分析任务"""
        return Task(
            id=f"ana-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=TaskType.ANALYSIS,
            title=f"分析: {name}",
            description=f"分析数据源: {data_source}",
            metadata={"data_source": data_source, **kwargs}
        )
    
    @staticmethod
    def create_research_task(hypothesis: str, **kwargs) -> Task:
        """创建研究任务"""
        return Task(
            id=f"res-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=TaskType.RESEARCH,
            title=f"研究: {hypothesis[:50]}...",
            description=f"研究假说: {hypothesis}",
            metadata={"hypothesis": hypothesis, **kwargs}
        )