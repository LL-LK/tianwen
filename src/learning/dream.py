"""
梦境引擎 - 重导出模块

本模块从 core.dream 导入所有公共API，保持向后兼容。
原始实现位于 src/core/dream.py
"""

from core.dream import (
    DreamState,
    DreamPattern,
    DreamSession,
    DreamEngine,
    run_dream_analysis,
)

__all__ = [
    "DreamState",
    "DreamPattern",
    "DreamSession",
    "DreamEngine",
    "run_dream_analysis",
]
