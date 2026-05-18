"""
TianwenAGI Harness - 天文AI Agent评测框架核心
基于lm-evaluation-harness架构 + GAIA分级评测 + 天文领域专用设计
"""
from .core.agent import BaseAgent, AgentResult, AgentConfig, AgentType, AgentCapability, AgentAction
from .core.task import BaseTask, TaskResult, TaskConfig, TaskCategory, DifficultyLevel, TaskStatus, TaskInstance
from .core.evaluator import BaseEvaluator, EvaluationResult, EvaluationConfig, MetricType, MetricScore, AstronomicspecificEvaluator
from .registry import HarnessRegistry, register_agent, register_task, register_evaluator, register_tool
from .runner import HarnessRunner, RunConfig, RunResult

__all__ = [
    "BaseAgent", "AgentResult", "AgentConfig", "AgentType", "AgentCapability", "AgentAction",
    "BaseTask", "TaskResult", "TaskConfig", "TaskCategory", "DifficultyLevel", "TaskStatus", "TaskInstance",
    "BaseEvaluator", "EvaluationResult", "EvaluationConfig", "MetricType", "MetricScore", "AstronomicspecificEvaluator",
    "HarnessRegistry", "register_agent", "register_task", "register_evaluator", "register_tool",
    "HarnessRunner", "RunConfig", "RunResult",
]
