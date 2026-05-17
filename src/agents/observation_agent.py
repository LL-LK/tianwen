"""
观测执行器 - 重导出模块

本模块从 observation.executor 导入所有公共API，保持向后兼容。
原始实现位于 src/observation/executor.py
"""

from observation.executor import (
    ObservationCommand,
    TelescopeStatus,
    ObservationInstruction,
    TelescopeState,
    ObservationData,
    ObservationResult,
    ObservationExecutor,
    demo,
)

__all__ = [
    "ObservationCommand",
    "TelescopeStatus",
    "ObservationInstruction",
    "TelescopeState",
    "ObservationData",
    "ObservationResult",
    "ObservationExecutor",
    "demo",
]
