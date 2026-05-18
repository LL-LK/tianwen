"""
TianwenAGI Harness - GitHub Actions结果输出
输出JSON/JSONL格式结果用于CI集成
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("harness.ci.github_actions")


class GitHubActionsReporter:
    """
    GitHub Actions结果报告器
    输出JSON/JSONL格式结果，兼容StarWhisperED
    """

    def __init__(self, output_dir: str = "./ci_results", output_format: str = "json"):
        self.output_dir = Path(output_dir)
        self.output_format = output_format  # json, jsonl, or both
        self._run_id = str(uuid.uuid4())[:8]
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def report_start(
        self,
        benchmark_name: str,
        total_tasks: int,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        报告开始状态

        Args:
            benchmark_name: Benchmark名称
            total_tasks: 任务总数
            metadata: 额外元数据

        Returns:
            开始事件数据
        """
        event = {
            "event": "start",
            "run_id": self._run_id,
            "benchmark": benchmark_name,
            "total_tasks": total_tasks,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        self._write_event(event, "start")
        logger.info(f"[{self._run_id}] Benchmark started: {benchmark_name}")
        return event

    def report_task_start(
        self,
        task_id: str,
        task_name: str,
        agent_id: str = None
    ) -> Dict[str, Any]:
        """报告任务开始"""
        event = {
            "event": "task_start",
            "run_id": self._run_id,
            "task_id": task_id,
            "task_name": task_name,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        self._write_event(event, f"task_start_{task_id}")
        return event

    def report_task_complete(
        self,
        task_id: str,
        task_name: str,
        success: bool,
        score: float,
        execution_time: float,
        agent_id: str = None,
        error: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        报告任务完成

        Args:
            task_id: 任务ID
            task_name: 任务名称
            success: 是否成功
            score: 评分
            execution_time: 执行时间
            agent_id: Agent ID
            error: 错误信息
            metadata: 额外元数据

        Returns:
            完成事件数据
        """
        event = {
            "event": "task_complete",
            "run_id": self._run_id,
            "task_id": task_id,
            "task_name": task_name,
            "success": success,
            "score": score,
            "execution_time": execution_time,
            "agent_id": agent_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        self._write_event(event, f"task_complete_{task_id}")
        logger.info(f"[{self._run_id}] Task {task_id} {'passed' if success else 'failed'} (score: {score})")
        return event

    def report_complete(
        self,
        benchmark_name: str,
        total_tasks: int,
        completed_tasks: int,
        failed_tasks: int,
        overall_score: float,
        execution_time: float,
        level_scores: Dict[str, float] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        报告Benchmark完成

        Args:
            benchmark_name: Benchmark名称
            total_tasks: 任务总数
            completed_tasks: 完成数
            failed_tasks: 失败数
            overall_score: 总分
            execution_time: 执行时间
            level_scores: 各级别分数
            metadata: 额外元数据

        Returns:
            完成事件数据
        """
        event = {
            "event": "complete",
            "run_id": self._run_id,
            "benchmark": benchmark_name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "overall_score": overall_score,
            "execution_time": execution_time,
            "level_scores": level_scores or {},
            "success": failed_tasks == 0,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        self._write_event(event, "complete")
        logger.info(
            f"[{self._run_id}] Benchmark complete: {completed_tasks}/{total_tasks} passed "
            f"(score: {overall_score:.4f})"
        )
        return event

    def report_failure(
        self,
        benchmark_name: str,
        error: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """报告失败"""
        event = {
            "event": "failure",
            "run_id": self._run_id,
            "benchmark": benchmark_name,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        self._write_event(event, "failure")
        logger.error(f"[{self._run_id}] Benchmark failed: {error}")
        return event

    def _write_event(self, event: Dict[str, Any], prefix: str = "event"):
        """写入事件到文件"""
        if self.output_format in ["json", "both"]:
            json_path = self.output_dir / f"{prefix}_{self._run_id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(event, f, indent=2, ensure_ascii=False)

        if self.output_format in ["jsonl", "both"]:
            jsonl_path = self.output_dir / f"{self._run_id}.jsonl"
            with open(jsonl_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')

    def write_summary(self, results: List[Dict[str, Any]], filename: str = "summary"):
        """
        写入汇总结果

        Args:
            results: 结果列表
            filename: 文件名前缀
        """
        summary = {
            "run_id": self._run_id,
            "total_events": len(results),
            "timestamp": datetime.now().isoformat(),
            "events": results,
        }

        if self.output_format in ["json", "both"]:
            json_path = self.output_dir / f"{filename}_{self._run_id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

        if self.output_format in ["jsonl", "both"]:
            jsonl_path = self.output_dir / f"{filename}_{self._run_id}.jsonl"
            with open(jsonl_path, 'a', encoding='utf-8') as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')

    def get_output_path(self, prefix: str = "output") -> str:
        """获取输出文件路径"""
        if self.output_format in ["jsonl", "both"]:
            return str(self.output_dir / f"{prefix}_{self._run_id}.jsonl")
        return str(self.output_dir / f"{prefix}_{self._run_id}.json")

    def set_run_id(self, run_id: str):
        """设置运行ID"""
        self._run_id = run_id

    def get_run_id(self) -> str:
        """获取运行ID"""
        return self._run_id
