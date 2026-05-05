"""
具身观测工作流 - 重导出模块

本模块从 observation.workflow 导入所有公共API，保持向后兼容。
原始实现位于 src/observation/workflow.py
"""

from observation.workflow import (
    WorkflowStage,
    WorkflowResult,
    EmbodiedObservationWorkflow,
)

__all__ = [
    "WorkflowStage",
    "WorkflowResult",
    "EmbodiedObservationWorkflow",
]
