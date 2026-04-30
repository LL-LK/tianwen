"""
天问-AGI 假说验证器 v1.0
HypothesisTester - 自动执行假说验证，对比观测数据和文献证据

功能:
- 从 hypothesis_generator 接收假说列表
- 自动设计验证实验
- 对比观测数据和文献证据
- 更新假说状态（证实/证伪/修订）
"""

import asyncio
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal, Tuple
from dataclasses import dataclass, field
from enum import Enum


class TestResult(Enum):
    CONFIRMED = "confirmed"       # 证实
    REJECTED = "rejected"        # 证伪
    INCONCLUSIVE = "inconclusive" # 不确定
    REVISED = "revised"          # 需要修订


@dataclass
class TestCase:
    """验证测试用例"""
    id: str
    hypothesis_id: str
    test_method: str
    input_data: Dict[str, Any]
    expected_outcome: str
    actual_outcome: Optional[str] = None
    passed: Optional[bool] = None
    notes: str = ""


@dataclass
class TestReport:
    """验证报告"""
    hypothesis_id: str
    test_cases: List[TestCase]
    overall_result: TestResult
    evidence_for: List[str]
    evidence_against: List[str]
    confidence_change: float  # 置信度变化
    recommendation: str
    timestamp: str = ""


class HypothesisTester:
    """
    假说验证器 - 自动执行假说验证

    工作流程:
    1. 接收待验证假说
    2. 设计测试用例
    3. 获取观测数据或文献证据
    4. 执行对比分析
    5. 输出验证报告
    """

    def __init__(self, astro_analyzer=None, data_collector=None):
        self.astro_analyzer = astro_analyzer
        self.data_collector = data_collector
        self.test_history: List[TestReport] = []

    async def test_hypothesis(
        self,
        hypothesis: Any,
        observation_data: Optional[List[Dict]] = None,
        literature_evidence: Optional[List[Dict]] = None
    ) -> TestReport:
        """
        测试单个假说

        Args:
            hypothesis: Hypothesis 对象
            observation_data: 观测数据列表
            literature_evidence: 文献证据列表

        Returns:
            TestReport - 验证报告
        """
        test_cases = []
        evidence_for = []
        evidence_against = []

        # 1. 设计测试用例
        test_case = await self._design_test_case(hypothesis)
        test_cases.append(test_case)

        # 2. 执行测试
        if observation_data:
            result = await self._test_with_observations(hypothesis, observation_data)
            test_case.actual_outcome = result["outcome"]
            test_case.passed = result["passed"]
            if result["passed"]:
                evidence_for.extend(result["supporting_evidence"])
            else:
                evidence_against.extend(result["contradicting_evidence"])

        if literature_evidence:
            result = await self._test_with_literature(hypothesis, literature_evidence)
            test_case.notes = result.get("notes", "")
            if result.get("supports"):
                evidence_for.extend(result.get("supporting_sources", []))
            else:
                evidence_against.extend(result.get("contradicting_sources", []))

        # 3. 综合判断
        overall_result = self._determine_result(test_case, evidence_for, evidence_against)

        # 4. 计算置信度变化
        confidence_change = self._calculate_confidence_change(
            hypothesis.confidence if hasattr(hypothesis, 'confidence') else 0.5,
            overall_result
        )

        report = TestReport(
            hypothesis_id=hypothesis.id if hasattr(hypothesis, 'id') else str(hypothesis),
            test_cases=test_cases,
            overall_result=overall_result,
            evidence_for=evidence_for,
            evidence_against=evidence_against,
            confidence_change=confidence_change,
            recommendation=self._generate_recommendation(overall_result),
            timestamp=datetime.now().isoformat()
        )

        self.test_history.append(report)
        return report

    async def _design_test_case(self, hypothesis: Any) -> TestCase:
        """设计测试用例"""
        hypothesis_id = hypothesis.id if hasattr(hypothesis, 'id') else "unknown"
        method = hypothesis.verification_method if hasattr(hypothesis, 'verification_method') else "unknown"

        return TestCase(
            id=f"test_{uuid.uuid4().hex[:8]}",
            hypothesis_id=hypothesis_id,
            test_method=method,
            input_data={
                "statement": hypothesis.statement if hasattr(hypothesis, 'statement') else "",
                "predictions": hypothesis.predictions if hasattr(hypothesis, 'predictions') else []
            },
            expected_outcome="; ".join(hypothesis.predictions) if hasattr(hypothesis, 'predictions') else ""
        )

    async def _test_with_observations(
        self,
        hypothesis: Any,
        observation_data: List[Dict]
    ) -> Dict:
        """用观测数据测试假说"""
        predictions = hypothesis.predictions if hasattr(hypothesis, 'predictions') else []
        supporting_evidence = []
        contradicting_evidence = []

        for obs in observation_data:
            target = obs.get("target", "")
            obs_type = obs.get("type", "")

            for pred in predictions:
                # 简单的关键词匹配验证
                if self._matches_prediction(pred, obs):
                    supporting_evidence.append(
                        f"观测 {target} ({obs_type}) 支持预测: {pred}"
                    )
                elif self._contradicts_prediction(pred, obs):
                    contradicting_evidence.append(
                        f"观测 {target} ({obs_type}) 与预测矛盾: {pred}"
                    )

        passed = len(supporting_evidence) > len(contradicting_evidence) * 0.5

        return {
            "outcome": "支持" if passed else "不支持",
            "passed": passed,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": contradicting_evidence
        }

    async def _test_with_literature(
        self,
        hypothesis: Any,
        literature_evidence: List[Dict]
    ) -> Dict:
        """用文献证据测试假说"""
        supports = True
        supporting_sources = []
        contradicting_sources = []

        for paper in literature_evidence:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            statement = hypothesis.statement if hasattr(hypothesis, 'statement') else ""

            if self._literature_supports(statement, title, abstract):
                supporting_sources.append(f"文献支持: {title}")
            elif self._literature_contradicts(statement, title, abstract):
                supports = False
                contradicting_sources.append(f"文献反驳: {title}")

        return {
            "supports": supports,
            "supporting_sources": supporting_sources,
            "contradicting_sources": contradicting_sources,
            "notes": f"检验了 {len(literature_evidence)} 篇文献"
        }

    def _matches_prediction(self, prediction: str, observation: Dict) -> bool:
        """检查观测是否匹配预测"""
        prediction_keywords = re.findall(r'[\w一-鿿]+', prediction.lower())
        obs_text = json.dumps(observation).lower()

        # 检查关键词重叠
        matches = sum(1 for kw in prediction_keywords if kw in obs_text and len(kw) > 2)
        return matches >= min(2, len(prediction_keywords) // 2)

    def _contradicts_prediction(self, prediction: str, observation: Dict) -> bool:
        """检查观测是否与预测矛盾"""
        contradiction_words = ["无", "不存在", "未检测到", "否定", "相反"]
        obs_text = json.dumps(observation).lower()

        has_contradiction = any(word in obs_text for word in contradiction_words)
        has_prediction = self._matches_prediction(prediction, observation)

        return has_contradiction and not has_prediction

    def _literature_supports(self, statement: str, title: str, abstract: str) -> bool:
        """检查文献是否支持假说"""
        support_indicators = ["证实", "确认", "支持", "一致", "证明", "confirmed", "supported"]
        text = f"{title} {abstract}".lower()

        return any(indicator in text for indicator in support_indicators)

    def _literature_contradicts(self, statement: str, title: str, abstract: str) -> bool:
        """检查文献是否反驳假说"""
        contradict_indicators = ["否定", "反驳", "矛盾", "不支持", "rejected", "contradicted"]
        text = f"{title} {abstract}".lower()

        return any(indicator in text for indicator in contradict_indicators)

    def _determine_result(
        self,
        test_case: TestCase,
        evidence_for: List[str],
        evidence_against: List[str]
    ) -> TestResult:
        """综合判断验证结果"""
        if not test_case.passed:
            return TestResult.REJECTED

        if len(evidence_for) > len(evidence_against) * 2:
            return TestResult.CONFIRMED
        elif len(evidence_against) > len(evidence_for) * 2:
            return TestResult.REJECTED
        elif evidence_for and evidence_against:
            return TestResult.REVISED
        else:
            return TestResult.INCONCLUSIVE

    def _calculate_confidence_change(
        self,
        original_confidence: float,
        result: TestResult
    ) -> float:
        """计算置信度变化"""
        if result == TestResult.CONFIRMED:
            return min(0.2, (1 - original_confidence) * 0.5)
        elif result == TestResult.REJECTED:
            return -original_confidence * 0.5
        elif result == TestResult.REVISED:
            return 0
        else:
            return -0.1

    def _generate_recommendation(self, result: TestResult) -> str:
        """生成建议"""
        recommendations = {
            TestResult.CONFIRMED: "假说已得到验证，可以进入下一阶段研究",
            TestResult.REJECTED: "假说被证伪，建议重新审视前提条件",
            TestResult.REVISED: "假说需要修订，建议调整预测或验证方法",
            TestResult.INCONCLUSIVE: "证据不足，建议收集更多数据"
        }
        return recommendations.get(result, "")

    def generate_report(self, reports: List[TestReport], format: str = "markdown") -> str:
        """生成验证报告"""
        if format == "markdown":
            lines = ["# 假说验证报告\n"]
            for report in reports:
                lines.append(f"\n## 假说: {report.hypothesis_id}")
                lines.append(f"\n**验证结果**: {report.overall_result.value}")
                lines.append(f"\n**置信度变化**: {report.confidence_change:+.0%}")
                lines.append(f"\n**建议**: {report.recommendation}")

                if report.evidence_for:
                    lines.append("\n**支持证据**:")
                    for e in report.evidence_for:
                        lines.append(f"- {e}")

                if report.evidence_against:
                    lines.append("\n**反驳证据**:")
                    for e in report.evidence_against:
                        lines.append(f"- {e}")

                lines.append(f"\n**时间**: {report.timestamp}")
                lines.append("\n---")
            return "\n".join(lines)
        else:
            return json.dumps([{
                "hypothesis_id": r.hypothesis_id,
                "result": r.overall_result.value,
                "confidence_change": r.confidence_change,
                "evidence_for": r.evidence_for,
                "evidence_against": r.evidence_against
            } for r in reports], ensure_ascii=False, indent=2)


async def demo():
    """演示假说验证流程"""
    from hypothesis_generator import Hypothesis, HypothesisStatus

    tester = HypothesisTester()

    hypo = Hypothesis(
        id="hypo_demo_001",
        statement="如果M42猎户座大星云存在多波段辐射差异，那么这种差异反映了不同年龄的恒星群体",
        premises=["已有研究显示M42存在温度梯度"],
        predictions=[
            "红外波段强度应与年龄负相关",
            "X射线应集中在年轻恒星区域"
        ],
        verification_method="多波段数据对比分析",
        confidence=0.7,
        status=HypothesisStatus.PENDING.value
    )

    observation_data = [
        {
            "target": "M42中心区域",
            "type": "infrared",
            "data": {"intensity": 0.8, "wavelength": "WISE_12um"}
        },
        {
            "target": "M42中心区域",
            "type": "xray",
            "data": {"intensity": 0.9, "energy": "Chandra_0.5-2keV"}
        }
    ]

    report = await tester.test_hypothesis(hypo, observation_data)

    print(f"验证结果: {report.overall_result.value}")
    print(f"置信度变化: {report.confidence_change:+.0%}")
    print(f"建议: {report.recommendation}")
    print("\n" + tester.generate_report([report]))


if __name__ == "__main__":
    asyncio.run(demo())
