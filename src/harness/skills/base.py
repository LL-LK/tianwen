"""
TianwenAGI Harness - BaseSkill
技能基类与定义
提供天文领域专用技能的接口规范
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import logging
import uuid

logger = logging.getLogger("harness.skills.base")


class SkillType(Enum):
    """技能类型"""
    SPECTRAL_ANALYSIS = "spectral_analysis"           # 光谱分析
    OBSERVATION_PLANNING = "observation_planning"      # 观测计划
    CATALOG_QUERY = "catalog_query"                    # 星表查询
    TRANSIENT_DETECTION = "transient_detection"        # 瞬变检测
    IMAGE_PROCESSING = "image_processing"              # 图像处理
    DATA_ANALYSIS = "data_analysis"                   # 数据分析
    LITERATURE_SEARCH = "literature_search"           # 文献搜索
    CODE_GENERATION = "code_generation"                # 代码生成
    TELESCOPE_CONTROL = "telescope_control"           # 望远镜控制
    REASONING = "reasoning"                           # 推理
    CUSTOM = "custom"                                 # 自定义


@dataclass
class SkillConfig:
    """技能配置"""
    name: str
    skill_type: SkillType
    description: str = ""
    version: str = "1.0.0"
    author: str = "TianwenAGI"
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_param(self, key: str, default: Any = None) -> Any:
        """获取参数"""
        return self.parameters.get(key, default)


@dataclass
class SkillResult:
    """技能执行结果"""
    skill_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    artifacts: List[Any] = field(default_factory=list)  # 生成的文件、数据等
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "output": str(self.output)[:200] if self.output else None,
            "error": self.error,
            "execution_time": self.execution_time,
            "metrics": self.metrics,
            "timestamp": self.timestamp,
        }


class BaseSkill(ABC):
    """
    技能基类
    所有具体技能必须实现此接口
    """

    def __init__(self, config: SkillConfig = None):
        self.config = config or SkillConfig(
            name=self.__class__.__name__,
            skill_type=SkillType.CUSTOM,
            description="Base skill"
        )
        self.skill_id = str(uuid.uuid4())[:12]
        self._initialized = False
        self._hooks: Dict[str, Callable] = {}

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def skill_type(self) -> SkillType:
        return self.config.skill_type

    @abstractmethod
    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> SkillResult:
        """
        执行技能
        Args:
            input_data: 输入数据
            context: 执行上下文
        Returns:
            SkillResult: 执行结果
        """
        pass

    async def initialize(self) -> bool:
        """
        初始化技能
        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return True

        try:
            result = await self._initialize_impl()
            self._initialized = result
            return result
        except Exception as e:
            logger.error(f"Skill {self.name} initialization failed: {e}")
            return False

    async def _initialize_impl(self) -> bool:
        """实际初始化逻辑，子类可重写"""
        return True

    async def cleanup(self):
        """清理技能资源"""
        pass

    def register_hook(self, name: str, hook: Callable):
        """注册钩子"""
        self._hooks[name] = hook

    async def _call_hooks(self, name: str, *args, **kwargs):
        """调用钩子"""
        if name in self._hooks:
            hook = self._hooks[name]
            if asyncio.iscoroutinefunction(hook):
                return await hook(*args, **kwargs)
            return hook(*args, **kwargs)

    def get_metadata(self) -> Dict[str, Any]:
        """获取技能元数据"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "type": self.skill_type.value,
            "description": self.config.description,
            "version": self.config.version,
            "author": self.config.author,
        }

    def matches_task(self, task_description: str, task_type: str = None) -> float:
        """
        判断技能是否匹配任务
        Args:
            task_description: 任务描述
            task_type: 任务类型（可选）
        Returns:
            float: 匹配度分数 0.0 - 1.0
        """
        # 默认实现：简单的关键词匹配
        score = 0.0
        desc_lower = task_description.lower()

        # 基于技能类型的匹配
        type_keywords = {
            SkillType.SPECTRAL_ANALYSIS: ["spectrum", "spectral", "wavelength", "flux"],
            SkillType.OBSERVATION_PLANNING: ["observation", "schedule", "telescope", "target"],
            SkillType.CATALOG_QUERY: ["catalog", "query", "database", "search"],
            SkillType.TRANSIENT_DETECTION: ["transient", "detection", "variable", "flare"],
            SkillType.IMAGE_PROCESSING: ["image", "photometry", "filter", "fwhm"],
            SkillType.DATA_ANALYSIS: ["analysis", "statistics", "fit", "model"],
            SkillType.LITERATURE_SEARCH: ["paper", "article", " literature", "search"],
            SkillType.CODE_GENERATION: ["code", "script", "program", "function"],
            SkillType.TELESCOPE_CONTROL: ["telescope", "control", "mount", "pointing"],
        }

        keywords = type_keywords.get(self.skill_type, [])
        for keyword in keywords:
            if keyword.lower() in desc_lower:
                score += 0.2

        # 基于名称的匹配
        name_words = self.name.lower().split()
        for word in name_words:
            if len(word) > 3 and word in desc_lower:
                score += 0.1

        # 基于描述的匹配
        desc_words = self.config.description.lower().split()
        for word in desc_words:
            if len(word) > 4 and word in desc_lower:
                score += 0.05

        return min(score, 1.0)

    def __repr__(self):
        return f"<{self.__class__.__name__}[{self.skill_type.value}] id={self.skill_id}>"


# 导入asyncio
import asyncio
