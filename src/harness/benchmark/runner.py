"""
TianwenAGI Harness - Benchmark执行器
执行完整基准评测套件
"""
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..core import (
    BaseAgent, AgentConfig, AgentType, AgentCapability,
    BaseTask, TaskConfig, TaskInstance, TaskResult, TaskStatus,
    BaseEvaluator, EvaluationConfig, EvaluationResult, MetricType,
)
from ..runner import HarnessRunner, RunConfig
from ..registry import HarnessRegistry
from .config import BenchmarkConfig, BenchmarkTaskConfig, BenchmarkEvaluatorConfig, OutputFormat, BenchmarkLevel

logger = logging.getLogger("harness.benchmark.runner")


@dataclass
class BenchmarkResult:
    """Benchmark执行结果"""
    benchmark_name: str
    benchmark_version: str
    run_id: str
    start_time: str
    end_time: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    level_1_passed: int = 0
    level_2_passed: int = 0
    level_3_passed: int = 0
    task_results: List[TaskResult] = field(default_factory=list)
    evaluation_results: List[EvaluationResult] = field(default_factory=list)
    overall_score: float = 0.0
    level_scores: Dict[str, float] = field(default_factory=dict)
    total_execution_time: float = 0.0
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_summary(self):
        """计算汇总统计"""
        if self.task_results:
            self.completed_tasks = sum(1 for r in self.task_results if r.success)
            self.failed_tasks = self.total_tasks - self.completed_tasks

            if self.total_tasks > 0:
                self.overall_score = sum(r.score for r in self.task_results) / self.total_tasks

        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.total_execution_time = (end - start).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_name": self.benchmark_name,
            "benchmark_version": self.benchmark_version,
            "run_id": self.run_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "level_1_passed": self.level_1_passed,
            "level_2_passed": self.level_2_passed,
            "level_3_passed": self.level_3_passed,
            "overall_score": self.overall_score,
            "level_scores": self.level_scores,
            "total_execution_time": self.total_execution_time,
            "success": self.success,
            "error": self.error,
            "timestamp": self.start_time,
        }

    def to_jsonl_dict(self) -> Dict[str, Any]:
        """JSONL格式输出 (StarWhisperED兼容)"""
        return {
            "run_id": self.run_id,
            "benchmark": self.benchmark_name,
            "version": self.benchmark_version,
            "timestamp": self.start_time,
            "status": "success" if self.success else "failed",
            "total": self.total_tasks,
            "passed": self.completed_tasks,
            "failed": self.failed_tasks,
            "score": self.overall_score,
            "level_scores": self.level_scores,
            "execution_time": self.total_execution_time,
        }


class BenchmarkRunner:
    """
    Benchmark执行器
    负责运行完整基准评测套件
    """

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.run_id = str(uuid.uuid4())[:8]
        self._results: List[BenchmarkResult] = []
        self._current_result: Optional[BenchmarkResult] = None

    async def run(
        self,
        agent_configs: List[AgentConfig],
        evaluator_config: BenchmarkEvaluatorConfig = None,
        output_path: str = None
    ) -> BenchmarkResult:
        """
        运行Benchmark

        Args:
            agent_configs: Agent配置列表
            evaluator_config: 评测器配置
            output_path: 输出文件路径

        Returns:
            BenchmarkResult结果
        """
        result = BenchmarkResult(
            benchmark_name=self.config.name,
            benchmark_version=self.config.version,
            run_id=self.run_id,
            start_time=datetime.now().isoformat(),
            total_tasks=len(self.config.tasks),
        )

        self._current_result = result

        try:
            # 创建任务实例
            task_instances = self._create_task_instances()

            # 创建Runner执行任务
            run_config = RunConfig(
                max_concurrent_tasks=self.config.max_workers if self.config.parallel else 1,
                parallel_execution=self.config.parallel,
                retry_on_failure=self.config.retry_failed,
                max_retries=self.config.max_retries,
                task_timeout=self.config.timeout_per_task,
            )

            runner = HarnessRunner(run_config)

            # 初始化Runner
            task_configs = [TaskConfig(
                name=t.name,
                category=t.category,
                description=t.description,
                tools=t.tools,
                max_steps=t.max_steps,
                time_limit=t.time_limit,
                grading_type=t.grading_type,
            ) for t in self.config.tasks]

            await runner.initialize(agent_configs, task_configs)

            # 执行任务
            logger.info(f"[{self.run_id}] Running benchmark '{self.config.name}' with {len(task_instances)} tasks")
            task_results = await runner.execute_batch(task_instances)
            result.task_results = task_results

            # 计算按级别统计
            self._calculate_level_stats(result, task_instances, task_results)

            # 评估
            if evaluator_config:
                eval_config = EvaluationConfig(
                    grading_type=evaluator_config.grading_type,
                    metrics=[MetricType(m) for m in evaluator_config.metrics] if evaluator_config.metrics else [],
                    timeout=evaluator_config.timeout,
                    verbose=evaluator_config.verbose,
                )

                evaluator = HarnessRegistry.create_evaluator(
                    evaluator_config.grading_type,
                    config=eval_config
                )

                for tr in task_results:
                    instance = next((t for t in task_instances if t.task_id == tr.task_id), None)
                    if instance:
                        eval_result = await evaluator.evaluate(tr, instance.ground_truth)
                        result.evaluation_results.append(eval_result)

            result.calculate_summary()
            result.success = True

            logger.info(f"[{self.run_id}] Benchmark complete: {result.completed_tasks}/{result.total_tasks} passed")

        except Exception as e:
            result.error = str(e)
            logger.error(f"[{self.run_id}] Benchmark failed: {e}")

        finally:
            result.end_time = datetime.now().isoformat()
            self._current_result = result
            self._results.append(result)

            # 保存结果
            if output_path or self.config.output_dir:
                self._save_results(result, output_path)

        return result

    def _create_task_instances(self) -> List[TaskInstance]:
        """创建任务实例"""
        instances = []
        for task_config in self.config.tasks:
            instance = TaskInstance(
                task_id=task_config.task_id,
                config=TaskConfig(
                    name=task_config.name,
                    category=task_config.category,
                    description=task_config.description,
                    tools=task_config.tools,
                    max_steps=task_config.max_steps,
                    time_limit=task_config.time_limit,
                    grading_type=task_config.grading_type,
                ),
                prompt=task_config.prompt_template,
                ground_truth=task_config.ground_truth,
                reference_data=task_config.reference_data,
                hints=task_config.hints,
            )
            instances.append(instance)
        return instances

    def _calculate_level_stats(
        self,
        result: BenchmarkResult,
        instances: List[TaskInstance],
        task_results: List[TaskResult]
    ):
        """计算级别统计"""
        level_map = {BenchmarkLevel.LEVEL_1: "level_1", BenchmarkLevel.LEVEL_2: "level_2", BenchmarkLevel.LEVEL_3: "level_3"}

        result.level_scores = {"level_1": 0.0, "level_2": 0.0, "level_3": 0.0}
        level_counts = {"level_1": 0, "level_2": 0, "level_3": 0}

        for instance, task_result in zip(instances, task_results):
            task_config = next((t for t in self.config.tasks if t.task_id == instance.task_id), None)
            if task_config:
                level_key = level_map.get(task_config.difficulty, "level_1")
                level_counts[level_key] += 1

                if task_result.success:
                    if task_config.difficulty == BenchmarkLevel.LEVEL_1:
                        result.level_1_passed += 1
                    elif task_config.difficulty == BenchmarkLevel.LEVEL_2:
                        result.level_2_passed += 1
                    elif task_config.difficulty == BenchmarkLevel.LEVEL_3:
                        result.level_3_passed += 1

                # 累加分数
                result.level_scores[level_key] += task_result.score

        # 计算级别平均分
        for level in ["level_1", "level_2", "level_3"]:
            if level_counts[level] > 0:
                result.level_scores[level] /= level_counts[level]

    def _save_results(self, result: BenchmarkResult, output_path: str = None):
        """保存结果到文件"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.config.output_format in [OutputFormat.JSON, OutputFormat.BOTH]:
            json_path = output_path or str(output_dir / f"{self.config.name}_{self.run_id}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved JSON results to {json_path}")

        if self.config.output_format in [OutputFormat.JSONL, OutputFormat.BOTH]:
            jsonl_path = str(output_dir / f"{self.config.name}_{self.run_id}.jsonl")
            with open(jsonl_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(result.to_jsonl_dict(), ensure_ascii=False) + '\n')
                for tr in result.task_results:
                    f.write(json.dumps(tr.to_dict(), ensure_ascii=False) + '\n')
            logger.info(f"Saved JSONL results to {jsonl_path}")

    def get_results(self) -> List[BenchmarkResult]:
        """获取所有执行结果"""
        return self._results

    def get_latest_result(self) -> Optional[BenchmarkResult]:
        """获取最新执行结果"""
        return self._results[-1] if self._results else None
