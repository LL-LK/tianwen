"""
TianwenAGI Harness - 增强模块测试
测试Protocols、Metrics、Graders等新模块
"""
import pytest
import json
import asyncio
from typing import Dict, List, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.evaluation.metrics import (
    MetricRegistry, Metric, ClassificationMetrics,
    EvaluationResult, load_jsonl_predictions, compute_metrics
)
from harness.evaluation.graders import (
    ExactMatchGrader, PartialMatchGrader, AstronomyGrader
)


class TestMetrics:
    """评测指标测试"""

    def test_metric_registry(self):
        """测试指标注册表"""
        assert "classification" in MetricRegistry.list_metrics()
        assert MetricRegistry.exists("classification")

    def test_classification_metrics(self):
        """测试分类指标"""
        metric = ClassificationMetrics()

        predictions = ["A", "B", "A", "A", "B"]
        references = ["A", "B", "A", "B", "B"]

        # Basic compute
        score = metric.compute(predictions, references)
        assert 0.0 <= score <= 1.0

        # Detailed compute
        detailed = metric.detailed_compute(predictions, references)
        assert "accuracy" in detailed
        assert "per_class" in detailed

    def test_evaluation_result(self):
        """测试评估结果"""
        result = EvaluationResult(
            task_name="test_task",
            metric_values={"accuracy": 0.9, "f1": 0.85},
            detailed_metrics={},
            predictions=["A", "B"],
            references=["A", "B"],
            num_samples=2,
            execution_time=1.5
        )

        assert result.task_name == "test_task"
        assert result.metric_values["accuracy"] == 0.9

        # Test serialization
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["task_name"] == "test_task"

    def test_load_jsonl_predictions(self):
        """测试JSONL格式加载 - StarWhisperED格式"""
        # 创建临时JSONL文件
        test_file = "/tmp/test_predictions.jsonl"
        with open(test_file, "w") as f:
            f.write('{"label": "TYPE = \'Eclipsing_Binary\'", "predict": "TYPE = \'Eclipsing_Binary\'"}\n')
            f.write('{"label": "TYPE = \'Delta_Sct\'", "predict": "TYPE = \'Gamma_Dor\'"}\n')
            f.write('{"label": "TYPE = \'Delta_Sct\'", "predict": "TYPE = \'Delta_Sct\'"}\n')

        refs, preds = load_jsonl_predictions(test_file)

        assert len(refs) == 3
        assert len(preds) == 3
        # Check first prediction is correct, second is wrong, third is correct
        assert preds[0] == refs[0]  # Correct
        assert preds[1] != refs[1]  # Wrong
        assert preds[2] == refs[2]  # Correct

        os.remove(test_file)


class TestGraders:
    """评分器测试"""

    def test_exact_match_grader(self):
        """测试精确匹配评分器"""
        grader = ExactMatchGrader()

        # Single prediction/reference - not lists
        result = grader.grade(
            "Eclipsing Binary",
            "Eclipsing Binary"
        )
        assert result.score == 1.0
        assert result.passed is True

    def test_exact_match_with_mismatch(self):
        """测试精确匹配 - 有不匹配"""
        grader = ExactMatchGrader()

        result = grader.grade("A", "C")
        assert result.score == 0.0
        assert result.passed is False

    def test_exact_match_batch(self):
        """测试精确匹配 - 批量"""
        grader = ExactMatchGrader()

        predictions = ["A", "B", "A"]
        references = ["A", "B", "C"]

        result = grader.grade_batch(predictions, references)
        assert result.score == pytest.approx(2/3, rel=0.01)
        assert result.details["correct_count"] == 2

    def test_partial_match_grader(self):
        """测试部分匹配评分器 - 子串模式"""
        grader = PartialMatchGrader()

        # 默认使用fuzzy模式，返回相似度分数
        result1 = grader.grade("The answer is A", "answer is A")
        assert result1.score > 0.8  # 高相似度

        result2 = grader.grade("completely different text", "answer is B")
        assert result2.score < 0.5  # 低相似度

    def test_partial_match_fuzzy(self):
        """测试模糊匹配"""
        grader = PartialMatchGrader()

        # Should handle similar strings
        result = grader.grade("Eclipsing Binary", "Eclipsing Binaries")  # Similar
        assert result.score >= 0.0

    def test_astronomy_grader(self):
        """测试天文专用评分器 - 红移"""
        grader = AstronomyGrader(config={"redshift_tolerance": 0.1})

        result = grader.grade(
            {"redshift": 0.05},
            {"redshift": 0.05},
            task_type="redshift"
        )
        assert result.score == 1.0  # Exact match

    def test_astronomy_grader_within_tolerance(self):
        """测试红移容差 - 评分公式: 1.0 - rel_error/tolerance"""
        grader = AstronomyGrader(config={"redshift_tolerance": 0.1})

        # 8% relative error, tolerance 0.1: score = 1.0 - 0.08/0.1 = 0.2
        result = grader.grade(
            {"redshift": 0.054},  # 8% off
            {"redshift": 0.05},
            task_type="redshift"
        )
        # Score = 1.0 - 0.08/0.1 = 0.2
        assert result.details["relative_error"] == pytest.approx(0.08, rel=0.01)

    def test_astronomy_grader_magnitude(self):
        """测试星等评分 - 评分公式: 1.0 - error/tolerance"""
        grader = AstronomyGrader(config={"magnitude_tolerance": 0.2})

        # 0.15 mag error, tolerance 0.2: score = 1.0 - 0.15/0.2 = 0.25
        result = grader.grade(
            {"magnitude": 15.15},  # 0.15 mag diff
            {"magnitude": 15.0},
            task_type="magnitude"
        )
        # Score = 1.0 - 0.15/0.2 = 0.25
        assert "magnitude_error" in result.details
        assert result.details["magnitude_error"] == pytest.approx(0.15, rel=0.01)


class TestMetricsCompute:
    """指标计算测试"""

    def test_compute_metrics_basic(self):
        """测试基本指标计算"""
        predictions = ["A", "B", "A", "B", "A"]
        references = ["A", "B", "A", "A", "A"]

        result = compute_metrics(predictions, references)
        assert "accuracy" in result

    def test_compute_metrics_with_labels(self):
        """测试带标签的指标计算"""
        predictions = ["A", "B", "C"]
        references = ["A", "B", "C"]
        labels = ["A", "B", "C"]

        result = compute_metrics(predictions, references, labels=labels)
        assert result["accuracy"] == 1.0


class TestProtocols:
    """协议测试"""

    def test_protocol_base_import(self):
        """测试协议基类导入"""
        from harness.protocols.base import (
            BaseProtocol, ProtocolRegistry, Message, ProtocolResult
        )

        assert BaseProtocol is not None
        assert ProtocolRegistry is not None
        assert Message is not None
        assert ProtocolResult is not None

    def test_astronomy_protocols_import(self):
        """测试天文协议导入"""
        from harness.protocols.astronomy import (
            SpectralAnalysisProtocol, PhotometryProtocol,
            AstronomicalCoordinateProtocol, AstronomyProtocol
        )

        assert SpectralAnalysisProtocol is not None
        assert PhotometryProtocol is not None
        assert AstronomicalCoordinateProtocol is not None
        assert AstronomyProtocol is not None


class TestGraderRegistry:
    """评分器注册表测试"""

    def test_exact_match_registered(self):
        """测试精确匹配评分器注册"""
        from harness.evaluation.graders.base import GraderRegistry
        assert "exact_match" in GraderRegistry.list_graders()

    def test_partial_match_registered(self):
        """测试部分匹配评分器注册"""
        from harness.evaluation.graders.base import GraderRegistry
        assert "partial_match" in GraderRegistry.list_graders()

    def test_astronomy_grader_registered(self):
        """测试天文评分器注册"""
        from harness.evaluation.graders.base import GraderRegistry
        assert "astronomy" in GraderRegistry.list_graders()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
