"""
Enhanced Task Base - Abstract task interface for TianwenAGI Harness

This module provides:
- BaseTask abstract class with skill-based workflows
- TaskRegistry for plugin registration (lm-evaluation-harness style)
- Task status management
- NGSS skill integration
- StarWhisperED evaluation format support

Key patterns:
- NGSS skill-based workflow patterns
- Plugin registration for extensibility
- lm-evaluation-harness registry pattern
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Task Status and Result
# ============================================================================

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = auto()
    RUNNING = auto()
    WAITING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    TIMEOUT = auto()


@dataclass
class TaskResult:
    """
    Result from task execution.
    
    Supports StarWhisperED JSONL format.
    """
    task_id: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    label: Optional[str] = None  # Ground truth
    predict: Optional[str] = None  # Prediction
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        """Check if task succeeded."""
        return self.status == TaskStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status.name,
            "output": self.output,
            "error": self.error,
            "metrics": self.metrics,
            "label": self.label,
            "predict": self.predict,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    def to_jsonl(self) -> str:
        """
        Convert to JSONL line for StarWhisperED format.
        
        Format: {"label": "...", "predict": "..."}
        """
        return json.dumps({
            "label": self.label,
            "predict": self.predict,
            "task_id": self.task_id,
            "status": self.status.name,
            "output": self.output,
            "error": self.error,
            "metrics": self.metrics,
            "execution_time": self.execution_time,
        }, ensure_ascii=False)
    
    @classmethod
    def from_jsonl(cls, line: str) -> TaskResult:
        """Create from JSONL line."""
        data = json.loads(line)
        return cls(
            task_id=data.get("task_id", str(uuid.uuid4())),
            status=TaskStatus[data.get("status", "PENDING")],
            output=data.get("output"),
            error=data.get("error"),
            metrics=data.get("metrics", {}),
            label=data.get("label"),
            predict=data.get("predict"),
            execution_time=data.get("execution_time", 0.0),
        )


# ============================================================================
# Task Registry
# ============================================================================

class TaskRegistry:
    """
    Registry for task implementations.
    
    Follows lm-evaluation-harness registry pattern for
    pluggable task registration.
    
    Usage:
        @TaskRegistry.register("my_task")
        class MyTask(BaseTask):
            ...
        
        task = TaskRegistry.get("my_task")
    """
    
    _tasks: Dict[str, type] = {}
    _factories: Dict[str, Callable[..., BaseTask]] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        task_class: Optional[type] = None,
        factory: Optional[Callable[..., BaseTask]] = None,
    ) -> Callable:
        """Register a task class."""
        def decorator(task_cls: type) -> type:
            cls._tasks[name] = task_cls
            logger.info(f"Registered task: {name}")
            return task_cls
        
        if task_class is not None:
            cls._tasks[name] = task_class
            if factory is not None:
                cls._factories[name] = factory
            logger.info(f"Registered task: {name}")
            return task_class
        
        return decorator
    
    @classmethod
    def get(cls, name: str, **kwargs) -> BaseTask:
        """Get a task instance by name."""
        if name not in cls._tasks:
            available = list(cls._tasks.keys())
            raise KeyError(f"Task '{name}' not found. Available: {available}")
        
        if name in cls._factories:
            return cls._factories[name](**kwargs)
        
        return cls._tasks[name](**kwargs)
    
    @classmethod
    def list_tasks(cls) -> List[str]:
        """List all registered task names."""
        return list(cls._tasks.keys())
    
    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if task is registered."""
        return name in cls._tasks


def task_plugin(name: str) -> Callable:
    """
    Decorator to register a task.
    
    Usage:
        @task_plugin("my_task")
        class MyTask(BaseTask):
            ...
    """
    def decorator(cls: type) -> type:
        return TaskRegistry.register(name, cls)
    return decorator


# ============================================================================
# Base Task
# ============================================================================

class BaseTask(ABC):
    """
    Abstract base class for all tasks.
    
    Tasks represent units of work that can be executed by agents.
    They support:
    - Skill-based workflow execution
    - NGSS-aligned evaluation
    - Plugin architecture
    - StarWhisperED format
    
    Attributes:
        task_id: Unique task identifier
        name: Task name
        status: Current task status
        required_skills: Set of required skill names
        
    Methods:
        setup: Prepare task resources
        execute: Execute the task
        validate: Validate task output
        get_result: Get task result
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        required_skills: Optional[List[str]] = None,
    ):
        """
        Initialize base task.
        
        Args:
            config: Task configuration dictionary
            required_skills: List of skill names required to execute
        """
        self.config = config or {}
        self.task_id = str(uuid.uuid4())
        self.name = self.config.get("name", self.__class__.__name__)
        self._status = TaskStatus.PENDING
        self._required_skills: Set[str] = set(required_skills or [])
        self._result: Optional[TaskResult] = None
        self._metadata: Dict[str, Any] = {}
    
    @property
    def status(self) -> TaskStatus:
        """Get current task status."""
        return self._status
    
    @property
    def required_skills(self) -> Set[str]:
        """Get required skills."""
        return self._required_skills.copy()
    
    @property
    def result(self) -> Optional[TaskResult]:
        """Get task result if available."""
        return self._result
    
    def add_required_skill(self, skill_name: str) -> None:
        """Add a required skill."""
        self._required_skills.add(skill_name)
    
    def _set_status(self, status: TaskStatus) -> None:
        """Internal status setter."""
        logger.debug(f"Task {self.task_id}: {self._status.name} -> {status.name}")
        self._status = status
    
    def setup(self) -> None:
        """
        Set up task resources.
        
        Called once before any execution.
        """
        self._status = TaskStatus.PENDING
        logger.info(f"Task {self.task_id}: Setup complete")
    
    @abstractmethod
    def execute(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute the task.
        
        Args:
            input_data: Task input data
            context: Optional execution context
            
        Returns:
            TaskResult with execution results
        """
        self._set_status(TaskStatus.RUNNING)
    
    def validate(self, output: Any) -> bool:
        """
        Validate task output.
        
        Args:
            output: Task output to validate
            
        Returns:
            True if valid, False otherwise
        """
        return output is not None
    
    def cancel(self) -> None:
        """Cancel task execution."""
        self._set_status(TaskStatus.CANCELLED)
        logger.info(f"Task {self.task_id}: Cancelled")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get task metadata."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self._status.name,
            "required_skills": list(self._required_skills),
            **self._metadata,
        }
    
    def __repr__(self) -> str:
        return f"<{self.name}Task(id={self.task_id[:8]}, status={self._status.name})>"


# ============================================================================
# Task Templates
# ============================================================================

@dataclass
class TaskTemplate:
    """
    Template for creating tasks.
    
    Provides a factory for creating configured tasks.
    """
    name: str
    task_class: type
    config_template: Dict[str, Any] = field(default_factory=dict)
    required_skills: List[str] = field(default_factory=list)
    description: str = ""
    
    def create(self, **overrides) -> BaseTask:
        """
        Create a task instance from template.
        
        Args:
            **overrides: Config values to override
            
        Returns:
            Task instance
        """
        config = {**self.config_template, **overrides}
        task = self.task_class(config=config)
        
        for skill in self.required_skills:
            task.add_required_skill(skill)
        
        return task
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "task_class": self.task_class.__name__,
            "config_template": self.config_template,
            "required_skills": self.required_skills,
            "description": self.description,
        }


# ============================================================================
# Batch Task Runner
# ============================================================================

class BatchTaskRunner:
    """
    Runs multiple tasks in batch.
    
    Provides parallel execution and aggregation of results.
    """
    
    def __init__(
        self,
        tasks: List[BaseTask],
        max_workers: int = 4,
    ):
        """
        Initialize batch runner.
        
        Args:
            tasks: List of tasks to run
            max_workers: Maximum parallel workers
        """
        self.tasks = tasks
        self.max_workers = max_workers
        self.results: List[TaskResult] = []
    
    def run_all(
        self,
        inputs: List[Any],
        contexts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[TaskResult]:
        """
        Run all tasks.
        
        Args:
            inputs: List of inputs for each task
            contexts: Optional list of contexts
            
        Returns:
            List of TaskResults
        """
        if len(inputs) != len(self.tasks):
            raise ValueError("Number of inputs must match number of tasks")
        
        contexts = contexts or [None] * len(self.tasks)
        results = []
        
        for task, input_data, context in zip(self.tasks, inputs, contexts):
            try:
                result = task.execute(input_data, context)
                results.append(result)
            except Exception as e:
                results.append(TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                ))
        
        self.results = results
        return results
    
    def aggregate_results(self) -> Dict[str, Any]:
        """
        Aggregate all results.
        
        Returns:
            Dictionary with aggregated metrics
        """
        if not self.results:
            return {}
        
        total = len(self.results)
        completed = sum(1 for r in self.results if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in self.results if r.status == TaskStatus.FAILED)
        
        # Aggregate metrics
        all_metrics = {}
        for result in self.results:
            for key, value in result.metrics.items():
                if key not in all_metrics:
                    all_metrics[key] = []
                all_metrics[key].append(value)
        
        aggregated = {
            "total": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "aggregated_metrics": {
                key: sum(values) / len(values) if values else 0
                for key, values in all_metrics.items()
            },
        }
        
        return aggregated
