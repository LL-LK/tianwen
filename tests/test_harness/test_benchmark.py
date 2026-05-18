"""
TianwenAGI Harness - Phase 2测试
测试Benchmark和CI/CD模块
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from harness.benchmark import (
    BenchmarkConfig, BenchmarkTaskConfig, BenchmarkEvaluatorConfig, OutputFormat, BenchmarkLevel,
    BenchmarkLoader, BenchmarkRunner, BenchmarkResult
)
from harness.ci import (
    CIConfig, WebhookConfig, DockerConfig,
    GitHubActionsReporter, CIRunner
)
from harness.core import AgentConfig, AgentType


# ============== Benchmark Config Tests ==============

class TestBenchmarkConfig:
    """Benchmark配置测试"""

    def test_benchmark_config_creation(self):
        """测试BenchmarkConfig创建"""
        config = BenchmarkConfig(
            name="Test Benchmark",
            version="1.0.0",
            description="A test benchmark",
            parallel=True,
            max_workers=4
        )
        assert config.name == "Test Benchmark"
        assert config.version == "1.0.0"
        assert config.parallel is True
        assert config.max_workers == 4

    def test_benchmark_config_to_dict(self):
        """测试BenchmarkConfig序列化"""
        config = BenchmarkConfig(name="Test")
        data = config.to_dict()
        assert data["name"] == "Test"
        assert "task_count" in data

    def test_get_tasks_by_level(self):
        """测试按级别获取任务"""
        config = BenchmarkConfig(
            name="Test",
            tasks=[
                BenchmarkTaskConfig(
                    task_id="t1", name="T1", category="cat",
                    description="desc", difficulty=BenchmarkLevel.LEVEL_1
                ),
                BenchmarkTaskConfig(
                    task_id="t2", name="T2", category="cat",
                    description="desc", difficulty=BenchmarkLevel.LEVEL_2
                ),
                BenchmarkTaskConfig(
                    task_id="t3", name="T3", category="cat",
                    description="desc", difficulty=BenchmarkLevel.LEVEL_3
                ),
            ]
        )
        assert config.level_1_count == 1
        assert config.level_2_count == 1
        assert config.level_3_count == 1
        assert config.total_tasks == 3


class TestBenchmarkTaskConfig:
    """Benchmark任务配置测试"""

    def test_task_config_creation(self):
        """测试任务配置创建"""
        task = BenchmarkTaskConfig(
            task_id="test_001",
            name="Test Task",
            category="astronomy",
            description="A test task",
            difficulty=BenchmarkLevel.LEVEL_2,
            max_steps=8,
            tools=["catalog_query", "web_search"]
        )
        assert task.task_id == "test_001"
        assert task.name == "Test Task"
        assert task.difficulty == BenchmarkLevel.LEVEL_2
        assert len(task.tools) == 2

    def test_task_config_to_dict(self):
        """测试任务配置序列化"""
        task = BenchmarkTaskConfig(
            task_id="t1", name="T1", category="cat", description="desc"
        )
        data = task.to_dict()
        assert data["task_id"] == "t1"
        assert data["difficulty"] == "level_1"


# ============== Benchmark Loader Tests ==============

class TestBenchmarkLoader:
    """Benchmark加载器测试"""

    def test_load_from_dict(self):
        """测试从字典加载"""
        data = {
            "name": "Test Benchmark",
            "version": "1.0.0",
            "tasks": [
                {
                    "task_id": "task_001",
                    "name": "Test Task",
                    "category": "astronomy",
                    "description": "A test task",
                    "difficulty": "level_1"
                }
            ],
            "evaluator": {
                "grading_type": "automatic",
                "metrics": ["accuracy"]
            }
        }
        config = BenchmarkLoader.load_from_dict(data)
        assert config.name == "Test Benchmark"
        assert len(config.tasks) == 1
        assert config.tasks[0].task_id == "task_001"

    def test_load_from_yaml_file(self):
        """测试从YAML文件加载"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
name: "YAML Test Benchmark"
version: "1.0.0"
tasks:
  - task_id: "yaml_task_001"
    name: "YAML Task"
    category: "astronomy"
    description: "Loaded from YAML"
    difficulty: "level_2"
"""
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = BenchmarkLoader.load_from_file(temp_path)
            assert config.name == "YAML Test Benchmark"
            assert len(config.tasks) == 1
            assert config.tasks[0].difficulty == BenchmarkLevel.LEVEL_2
        finally:
            os.unlink(temp_path)

    def test_load_from_json_file(self):
        """测试从JSON文件加载"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_content = {
                "name": "JSON Test Benchmark",
                "version": "1.0.0",
                "tasks": [
                    {
                        "task_id": "json_task_001",
                        "name": "JSON Task",
                        "category": "astronomy",
                        "description": "Loaded from JSON",
                        "difficulty": "level_3"
                    }
                ]
            }
            json.dump(json_content, f)
            temp_path = f.name

        try:
            config = BenchmarkLoader.load_from_file(temp_path)
            assert config.name == "JSON Test Benchmark"
            assert config.tasks[0].difficulty == BenchmarkLevel.LEVEL_3
        finally:
            os.unlink(temp_path)

    def test_save_to_file(self):
        """测试保存配置文件"""
        config = BenchmarkConfig(
            name="Save Test",
            tasks=[
                BenchmarkTaskConfig(
                    task_id="save_001", name="Save Task",
                    category="test", description="test"
                )
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"
            BenchmarkLoader.save_to_file(config, str(yaml_path))
            assert yaml_path.exists()

            # 重新加载验证
            loaded = BenchmarkLoader.load_from_file(str(yaml_path))
            assert loaded.name == "Save Test"


# ============== GitHub Actions Reporter Tests ==============

class TestGitHubActionsReporter:
    """GitHub Actions Reporter测试"""

    def test_reporter_creation(self):
        """测试Reporter创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = GitHubActionsReporter(output_dir=tmpdir, output_format="jsonl")
            assert reporter.get_run_id() is not None
            assert reporter.output_format == "jsonl"

    def test_report_start(self):
        """测试报告开始事件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = GitHubActionsReporter(output_dir=tmpdir, output_format="json")
            event = reporter.report_start("Test Benchmark", 10)
            assert event["event"] == "start"
            assert event["benchmark"] == "Test Benchmark"
            assert event["total_tasks"] == 10

    def test_report_task_complete(self):
        """测试报告任务完成事件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = GitHubActionsReporter(output_dir=tmpdir, output_format="json")
            event = reporter.report_task_complete(
                task_id="task_001",
                task_name="Test Task",
                success=True,
                score=0.95,
                execution_time=12.5
            )
            assert event["event"] == "task_complete"
            assert event["success"] is True
            assert event["score"] == 0.95

    def test_report_complete(self):
        """测试报告Benchmark完成事件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = GitHubActionsReporter(output_dir=tmpdir, output_format="jsonl")
            event = reporter.report_complete(
                benchmark_name="Test",
                total_tasks=10,
                completed_tasks=9,
                failed_tasks=1,
                overall_score=0.85,
                execution_time=120.0,
                level_scores={"level_1": 0.9, "level_2": 0.8, "level_3": 0.7}
            )
            assert event["event"] == "complete"
            assert event["completed_tasks"] == 9
            assert event["overall_score"] == 0.85


# ============== CI Config Tests ==============

class TestCIConfig:
    """CI配置测试"""

    def test_ci_config_creation(self):
        """测试CIConfig创建"""
        config = CIConfig(
            repository="org/repo",
            branch="main",
            workflow="benchmark"
        )
        assert config.repository == "org/repo"
        assert config.branch == "main"
        assert config.workflow == "benchmark"

    def test_docker_config_creation(self):
        """测试DockerConfig创建"""
        docker = DockerConfig(
            image="tianwenagi/test:latest",
            memory_limit="4g",
            use_gpu=True
        )
        assert docker.image == "tianwenagi/test:latest"
        assert docker.memory_limit == "4g"
        assert docker.use_gpu is True

    def test_webhook_config_creation(self):
        """测试WebhookConfig创建"""
        webhook = WebhookConfig(
            url="https://example.com/webhook",
            events=["start", "complete"]
        )
        assert webhook.url == "https://example.com/webhook"
        assert "start" in webhook.events
        assert webhook.enabled is True


# ============== Integration Tests ==============

class TestBenchmarkIntegration:
    """Benchmark集成测试"""

    @pytest.mark.asyncio
    async def test_benchmark_runner_initialization(self):
        """测试BenchmarkRunner初始化"""
        config = BenchmarkConfig(
            name="Integration Test",
            tasks=[
                BenchmarkTaskConfig(
                    task_id="int_001",
                    name="Integration Task",
                    category="test",
                    description="Integration test",
                    difficulty=BenchmarkLevel.LEVEL_1
                )
            ]
        )
        runner = BenchmarkRunner(config)
        assert runner.run_id is not None
        assert len(runner.run_id) == 8


class TestCIIntegration:
    """CI集成测试"""

    def test_ci_runner_initialization(self):
        """测试CIRunner初始化"""
        config = CIConfig(
            repository="test/repo",
            workflow="benchmark"
        )
        runner = CIRunner(config)
        assert runner.run_id is not None
        assert runner._docker_available is not None  # Boolean


# ============== Output Format Tests ==============

class TestOutputFormat:
    """输出格式测试"""

    def test_json_format(self):
        """测试JSON格式"""
        config = BenchmarkConfig(
            name="JSON Test",
            output_format=OutputFormat.JSON
        )
        assert config.output_format == OutputFormat.JSON

    def test_jsonl_format(self):
        """测试JSONL格式"""
        config = BenchmarkConfig(
            name="JSONL Test",
            output_format=OutputFormat.JSONL
        )
        assert config.output_format == OutputFormat.JSONL

    def test_both_format(self):
        """测试BOTH格式"""
        config = BenchmarkConfig(
            name="Both Test",
            output_format=OutputFormat.BOTH
        )
        assert config.output_format == OutputFormat.BOTH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
