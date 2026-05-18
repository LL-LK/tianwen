"""
TianwenAGI Harness - Task基类与定义
声明式任务配置，参考GAIA Benchmark分级设计
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import uuid
import json
import logging

logger = logging.getLogger("harness.task")


class TaskCategory(Enum):
    """任务类别"""
    ASTRONOMY_OBSERVATION = "astronomy_observation"    # 观测任务
    ASTRONOMY_ANALYSIS = "astronomy_analysis"          # 分析任务
    ASTRONOMY_DISCOVERY = "astronomy_discovery"        # 发现任务
    TRANSIENT_DETECTION = "transient_detection"        # 瞬变检测
    SPECTROSCOPY = "spectroscopy"                     # 光谱分析
    CATALOG_QUERY = "catalog_query"                    # 星表查询
    LITERATURE_RESEARCH = "literature_research"       # 文献调研
    MULTI_AGENT_COLLABORATION = "multi_agent"         # 多Agent协作
    REAL_BOGUS_CLASSIFICATION = "real_bogus"           # Real-Bogus分类
    HYPOTHESIS_GENERATION = "hypothesis_generation"    # 假说生成
    GENERAL = "general"                               # 通用任务


class DifficultyLevel(Enum):
    """任务难度级别 - 参考GAIA Benchmark"""
    LEVEL_1 = 1    # <5步: 基础天文问答、星表查询
    LEVEL_2 = 2    # 5-10步: 观测计划、数据分析
    LEVEL_3 = 3    # >10步: 论文复现、新发现识别


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class TaskConfig:
    """任务配置"""
    name: str
    category: TaskCategory
    description: str
    difficulty: DifficultyLevel = DifficultyLevel.LEVEL_1
    max_steps: int = 10                 # 最大步数
    time_limit: int = 300             # 时间限制(秒)
    tools: List[str] = field(default_factory=list)  # 必需工具
    optional_tools: List[str] = field(default_factory=list)  # 可选工具
    few_shot_examples: List[Dict] = field(default_factory=list)  # Few-shot示例
    grading_type: str = "automatic"   # automatic, human, hybrid
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskInstance:
    """单个任务实例"""
    task_id: str
    config: TaskConfig
    prompt: str                         # 输入提示
    ground_truth: Any = None          # 标准答案
    reference_data: Dict[str, Any] = field(default_factory=dict)  # 参考数据
    validators: List[Callable] = field(default_factory=list)  # 自定义验证器
    hints: List[str] = field(default_factory=list)  # 提示(分级评测用)

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.config.name,
            "category": self.config.category.value,
            "difficulty": self.config.difficulty.value,
            "prompt": self.prompt,
            "tools": self.config.tools,
        }


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    agent_id: str
    success: bool
    output: Any                        # Agent输出
    expected: Any = None               # 期望输出
    score: float = 0.0                 # 评分
    metrics: Dict[str, float] = field(default_factory=dict)  # 各维度指标
    steps: List[Dict[str, Any]] = field(default_factory=list)  # 执行步骤详情
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)  # 工具调用记录
    execution_time: float = 0           # 执行时间
    tokens_used: int = 0
    error: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step_type: str, content: Any, duration: float = 0):
        self.steps.append({
            "type": step_type,
            "content": content,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "score": self.score,
            "metrics": self.metrics,
            "execution_time": self.execution_time,
            "tokens_used": self.tokens_used,
            "status": self.status.value,
            "timestamp": self.timestamp,
        }


class BaseTask(ABC):
    """
    任务基类 - 定义任务接口
    所有具体任务必须实现此接口
    """

    def __init__(self, config: TaskConfig):
        self.config = config
        self.task_id = str(uuid.uuid4())[:12]
        self._instances: List[TaskInstance] = []

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def category(self) -> TaskCategory:
        return self.config.category

    @abstractmethod
    def load_instances(self) -> List[TaskInstance]:
        """加载任务实例"""
        pass

    @abstractmethod
    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        """
        验证输出
        Returns: 指标字典
        """
        pass

    def get_instances(self) -> List[TaskInstance]:
        """获取所有实例"""
        return self._instances.copy()

    def add_instance(self, instance: TaskInstance):
        """添加实例"""
        self._instances.append(instance)

    def __repr__(self):
        return f"<{self.__class__.__name__}[{self.config.category.value}] name={self.name}>"
