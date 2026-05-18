"""
TianwenAGI Harness - Benchmark加载器
从YAML/JSON配置文件加载任务
"""
import json
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .config import (
    BenchmarkConfig, BenchmarkTaskConfig, BenchmarkEvaluatorConfig,
    BenchmarkLevel, OutputFormat
)

logger = logging.getLogger("harness.benchmark.loader")


class BenchmarkLoader:
    """Benchmark配置加载器"""

    @staticmethod
    def load_from_file(file_path: str) -> BenchmarkConfig:
        """
        从YAML/JSON文件加载Benchmark配置

        Args:
            file_path: 配置文件路径

        Returns:
            BenchmarkConfig对象
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Benchmark config file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif path.suffix == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {path.suffix}")

        return BenchmarkLoader.load_from_dict(data)

    @staticmethod
    def load_from_dict(data: Dict[str, Any]) -> BenchmarkConfig:
        """
        从字典加载Benchmark配置

        Args:
            data: 配置字典

        Returns:
            BenchmarkConfig对象
        """
        # 解析任务列表
        tasks = []
        for task_data in data.get('tasks', []):
            tasks.append(BenchmarkLoader._parse_task(task_data))

        # 解析评测器配置
        eval_data = data.get('evaluator', {})
        evaluator = BenchmarkEvaluatorConfig(
            grading_type=eval_data.get('grading_type', 'automatic'),
            metrics=eval_data.get('metrics', []),
            tolerance=eval_data.get('tolerance', 0.05),
            timeout=eval_data.get('timeout', 300),
            verbose=eval_data.get('verbose', True),
            save_intermediate=eval_data.get('save_intermediate', True),
            custom_grader=eval_data.get('custom_grader'),
            metadata=eval_data.get('metadata', {}),
        )

        # 解析输出格式
        output_format_str = data.get('output_format', 'json')
        try:
            output_format = OutputFormat(output_format_str)
        except ValueError:
            output_format = OutputFormat.JSON

        # 解析级别
        def parse_level(level_str: str) -> BenchmarkLevel:
            level_str = str(level_str).upper()
            if level_str in ['1', 'LEVEL_1']:
                return BenchmarkLevel.LEVEL_1
            elif level_str in ['2', 'LEVEL_2']:
                return BenchmarkLevel.LEVEL_2
            elif level_str in ['3', 'LEVEL_3']:
                return BenchmarkLevel.LEVEL_3
            return BenchmarkLevel.LEVEL_1

        config = BenchmarkConfig(
            name=data.get('name', 'Unnamed Benchmark'),
            version=data.get('version', '1.0.0'),
            description=data.get('description', ''),
            tasks=tasks,
            evaluator=evaluator,
            output_format=output_format,
            output_dir=data.get('output_dir', './results'),
            parallel=data.get('parallel', True),
            max_workers=data.get('max_workers', 4),
            retry_failed=data.get('retry_failed', True),
            max_retries=data.get('max_retries', 2),
            timeout_per_task=data.get('timeout_per_task', 600),
            metadata=data.get('metadata', {}),
        )

        logger.info(f"Loaded benchmark '{config.name}' with {len(tasks)} tasks")
        return config

    @staticmethod
    def _parse_task(task_data: Dict[str, Any]) -> BenchmarkTaskConfig:
        """解析单个任务配置"""
        # 解析难度级别
        difficulty_str = task_data.get('difficulty', 'level_1')
        difficulty_str = str(difficulty_str).upper()
        if difficulty_str in ['1', 'LEVEL_1']:
            difficulty = BenchmarkLevel.LEVEL_1
        elif difficulty_str in ['2', 'LEVEL_2']:
            difficulty = BenchmarkLevel.LEVEL_2
        elif difficulty_str in ['3', 'LEVEL_3']:
            difficulty = BenchmarkLevel.LEVEL_3
        else:
            difficulty = BenchmarkLevel.LEVEL_1

        return BenchmarkTaskConfig(
            task_id=task_data.get('task_id', task_data.get('id', '')),
            name=task_data.get('name', 'Unnamed Task'),
            category=task_data.get('category', 'general'),
            description=task_data.get('description', ''),
            difficulty=difficulty,
            max_steps=task_data.get('max_steps', 10),
            time_limit=task_data.get('time_limit', 300),
            tools=task_data.get('tools', []),
            optional_tools=task_data.get('optional_tools', []),
            few_shot_examples=task_data.get('few_shot_examples', []),
            grading_type=task_data.get('grading_type', 'automatic'),
            prompt_template=task_data.get('prompt_template', task_data.get('prompt', '')),
            ground_truth=task_data.get('ground_truth'),
            reference_data=task_data.get('reference_data', {}),
            hints=task_data.get('hints', []),
            metadata=task_data.get('metadata', {}),
        )

    @staticmethod
    def load_multiple(file_paths: List[str]) -> List[BenchmarkConfig]:
        """加载多个Benchmark配置"""
        configs = []
        for path in file_paths:
            try:
                config = BenchmarkLoader.load_from_file(path)
                configs.append(config)
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")
        return configs

    @staticmethod
    def load_directory(directory: str, pattern: str = "*.yaml") -> List[BenchmarkConfig]:
        """
        加载目录下所有匹配的Benchmark配置

        Args:
            directory: 目录路径
            pattern: 文件匹配模式

        Returns:
            BenchmarkConfig列表
        """
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        configs = []
        for file_path in path.glob(pattern):
            try:
                config = BenchmarkLoader.load_from_file(str(file_path))
                configs.append(config)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        # 也检查JSON文件
        for file_path in path.glob("*.json"):
            if file_path not in [Path(p) for p in path.glob("*.yaml")]:
                try:
                    config = BenchmarkLoader.load_from_file(str(file_path))
                    configs.append(config)
                except Exception as e:
                    logger.error(f"Failed to load {file_path}: {e}")

        return configs

    @staticmethod
    def save_to_file(config: BenchmarkConfig, file_path: str):
        """
        保存Benchmark配置到文件

        Args:
            config: BenchmarkConfig对象
            file_path: 输出文件路径
        """
        path = Path(file_path)
        data = config.to_dict()
        data['tasks'] = [t.to_dict() for t in config.tasks]
        data['evaluator'] = config.evaluator.to_dict()

        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved benchmark config to {file_path}")
