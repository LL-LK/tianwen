"""
TianwenAGI Harness - Benchmark配置
基准评测配置数据结构，参考GAIA Benchmark分级设计
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class OutputFormat(Enum):
    """输出格式"""
    JSON = "json"
    JSONL = "jsonl"  # StarWhisperED兼容格式
    BOTH = "both"


class BenchmarkLevel(Enum):
    """Benchmark难度级别"""
    LEVEL_1 = "level_1"   # <5步: 基础天文问答、星表查询
    LEVEL_2 = "level_2"  # 5-10步: 观测计划、数据分析
    LEVEL_3 = "level_3"  # >10步: 论文复现、新发现识别


@dataclass
class BenchmarkTaskConfig:
    """Benchmark任务配置"""
    task_id: str
    name: str
    category: str
    description: str
    difficulty: BenchmarkLevel = BenchmarkLevel.LEVEL_1
    max_steps: int = 10
    time_limit: int = 300
    tools: List[str] = field(default_factory=list)
    optional_tools: List[str] = field(default_factory=list)
    few_shot_examples: List[Dict[str, str]] = field(default_factory=list)
    grading_type: str = "automatic"
    prompt_template: str = ""
    ground_truth: Any = None
    reference_data: Dict[str, Any] = field(default_factory=dict)
    hints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "difficulty": self.difficulty.value,
            "max_steps": self.max_steps,
            "time_limit": self.time_limit,
            "tools": self.tools,
            "optional_tools": self.optional_tools,
            "grading_type": self.grading_type,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkEvaluatorConfig:
    """Benchmark评测器配置"""
    grading_type: str = "automatic"
    metrics: List[str] = field(default_factory=list)
    tolerance: float = 0.05
    timeout: int = 300
    verbose: bool = True
    save_intermediate: bool = True
    custom_grader: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grading_type": self.grading_type,
            "metrics": self.metrics,
            "tolerance": self.tolerance,
            "timeout": self.timeout,
            "verbose": self.verbose,
            "save_intermediate": self.save_intermediate,
            "custom_grader": self.custom_grader,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkConfig:
    """Benchmark套件配置"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    tasks: List[BenchmarkTaskConfig] = field(default_factory=list)
    evaluator: BenchmarkEvaluatorConfig = field(default_factory=BenchmarkEvaluatorConfig)
    output_format: OutputFormat = OutputFormat.JSON
    output_dir: str = "./results"
    parallel: bool = True
    max_workers: int = 4
    retry_failed: bool = True
    max_retries: int = 2
    timeout_per_task: int = 600
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "task_count": len(self.tasks),
            "evaluator": self.evaluator.to_dict(),
            "output_format": self.output_format.value,
            "output_dir": self.output_dir,
            "parallel": self.parallel,
            "max_workers": self.max_workers,
            "retry_failed": self.retry_failed,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }

    def get_tasks_by_level(self, level: BenchmarkLevel) -> List[BenchmarkTaskConfig]:
        """按级别获取任务"""
        return [t for t in self.tasks if t.difficulty == level]

    def get_tasks_by_category(self, category: str) -> List[BenchmarkTaskConfig]:
        """按类别获取任务"""
        return [t for t in self.tasks if t.category == category]

    @property
    def level_1_count(self) -> int:
        return len(self.get_tasks_by_level(BenchmarkLevel.LEVEL_1))

    @property
    def level_2_count(self) -> int:
        return len(self.get_tasks_by_level(BenchmarkLevel.LEVEL_2))

    @property
    def level_3_count(self) -> int:
        return len(self.get_tasks_by_level(BenchmarkLevel.LEVEL_3))

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)
