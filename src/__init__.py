"""
天问-AGI - 全自动天文观测系统

基于 AI Agent 的天文观测自动化平台，集成认知引擎、规划引擎、执行引擎和自我进化系统。
"""

from .engine import CognitiveEngine, PlanningEngine, ExecutionEngine
from .service import LLMService
from .config import get_settings, AppSettings

__version__ = "2.4.0"
__author__ = "Tianwen-AGI Team"

__all__ = [
    "CognitiveEngine", 
    "PlanningEngine", 
    "ExecutionEngine",
    "LLMService",
    "get_settings",
    "AppSettings",
    "__version__", 
    "__author__"
]