"""
天问-AGI - 全自动天文观测系统

基于 AI Agent 的天文观测自动化平台，集成认知引擎、规划引擎、执行引擎和自我进化系统。

架构分层：
- config: 统一配置管理
- domain: 领域模型层
- engine: 核心引擎层（认知、规划、执行）
- service: 服务层（LLM、数据、望远镜）
"""

__version__ = "2.4.0"
__author__ = "Tianwen-AGI Team"

from .engine import (
    CognitiveEngine, 
    PlanningEngine, 
    ExecutionEngine,
    Intent,
    IntentType,
    TaskModel,
    ExecutionPlan,
    PlanStep,
    PlanStatus,
    ExecutionState,
    ExecutionStatus
)

from .domain import (
    Task,
    TaskStatus,
    TaskType,
    TaskPriority,
    TaskResult,
    TaskStep,
    TaskContext,
    TaskFactory
)

from .service import (
    LLMService,
    ModelProvider,
    ModelCapability
)

from .config import (
    get_settings,
    AppSettings,
    settings
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    
    # Engines
    "CognitiveEngine",
    "PlanningEngine", 
    "ExecutionEngine",
    
    # Engine models
    "Intent",
    "IntentType",
    "TaskModel",
    "ExecutionPlan",
    "PlanStep",
    "PlanStatus",
    "ExecutionState",
    "ExecutionStatus",
    
    # Domain models
    "Task",
    "TaskStatus",
    "TaskType",
    "TaskPriority",
    "TaskResult",
    "TaskStep",
    "TaskContext",
    "TaskFactory",
    
    # Services
    "LLMService",
    "ModelProvider",
    "ModelCapability",
    
    # Config
    "get_settings",
    "AppSettings",
    "settings"
]