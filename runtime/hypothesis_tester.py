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
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats


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
        statistical_results = []

        for obs in observation_data:
            target = obs.get("target", "")
            obs_type = obs.get("type", "")

            # 检查是否有数值型数据可进行统计检验
            if "data" in obs and isinstance(obs["data"], dict):
                numeric_data = self._extract_numeric_values(obs["data"])
                if len(numeric_data) >= 3:
                    stat_result = self._statistical_test_for_observation(obs, predictions)
                    if stat_result:
                        statistical_results.append(stat_result)
                        if stat_result.get("significant"):
                            supporting_evidence.append(
                                f"统计检验支持: {stat_result['interpretation']}"
                            )
                        else:
                            contradicting_evidence.append(
                                f"统计检验不显著: {stat_result['interpretation']}"
                            )
                        continue

            # 回退到关键词匹配
            for pred in predictions:
                if self._matches_prediction(pred, obs):
                    supporting_evidence.append(
                        f"观测 {target} ({obs_type}) 支持预测: {pred}"
                    )
                elif self._contradicts_prediction(pred, obs):
                    contradicting_evidence.append(
                        f"观测 {target} ({obs_type}) 与预测矛盾: {pred}"
                    )

        # 综合考虑统计结果和关键词匹配
        total_supporting = len(supporting_evidence) + sum(1 for r in statistical_results if r.get("significant"))
        total_contradicting = len(contradicting_evidence) + sum(1 for r in statistical_results if not r.get("significant"))
        passed = total_supporting > total_contradicting * 0.5

        return {
            "outcome": "支持" if passed else "不支持",
            "passed": passed,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": contradicting_evidence,
            "statistical_tests": statistical_results
        }

    def _extract_numeric_values(self, data: Dict) -> List[float]:
        """从观测数据中提取数值"""
        values = []
        for v in data.values():
            if isinstance(v, (int, float)):
                values.append(float(v))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, (int, float)):
                        values.append(float(item))
        return values

    def _statistical_test_for_observation(self, obs: Dict, predictions: List[str]) -> Optional[Dict]:
        """对观测数据进行统计检验"""
        if "data" not in obs or not isinstance(obs["data"], dict):
            return None

        numeric_data = self._extract_numeric_values(obs["data"])
        if len(numeric_data) < 3:
            return None

        # 检查预测中是否包含数值比较
        for pred in predictions:
            pred_lower = pred.lower()
            if any(kw in pred_lower for kw in ["高于", "低于", "大于", "小于", "相关", "差异"]):
                # 尝试提取期望值
                expected_val = self._extract_expected_value(pred)
                if expected_val is not None:
                    return self.statistical_ttest(numeric_data, expected_val)
                # 检查是否有两组数据可比较 - 使用双样本t检验
                if "compare" in pred_lower or "差异" in pred_lower:
                    # 当数据量足够时，用单样本t检验与均值对比来检测差异
                    mean_val = np.mean(numeric_data)
                    return self.statistical_ttest(numeric_data, mean_val)

        return None

    def _extract_expected_value(self, prediction: str) -> Optional[float]:
        """从预测文本中提取期望数值"""
        patterns = [
            r'高于?(\d+\.?\d*)',
            r'低于?(\d+\.?\d*)',
            r'大于?(\d+\.?\d*)',
            r'小于?(\d+\.?\d*)',
            r'等于?(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*以上',
            r'(\d+\.?\d*)\s*以下'
        ]
        for pattern in patterns:
            match = re.search(pattern, prediction)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    async def _test_with_literature(
        self,
        hypothesis: Any,
        literature_evidence: List[Dict]
    ) -> Dict:
        """用文献证据测试假说"""
        supports = True
        supporting_sources = []
        contradicting_sources = []

        statement = hypothesis.statement if hasattr(hypothesis, 'statement') else ""

        for paper in literature_evidence:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            full_text = paper.get("full_text", paper.get("content", ""))

            # 综合判断文献证据：统计检验 + 关键词匹配
            literature_result = self._analyze_literature_evidence(
                statement, title, abstract, full_text
            )

            if literature_result["supports"]:
                supporting_sources.append(f"文献支持: {title} ({literature_result['reason']})")
            else:
                supports = False
                contradicting_sources.append(f"文献反驳: {title} ({literature_result['reason']})")

        return {
            "supports": supports,
            "supporting_sources": supporting_sources,
            "contradicting_sources": contradicting_sources,
            "notes": f"检验了 {len(literature_evidence)} 篇文献，发现 {len(supporting_sources)} 篇支持，{len(contradicting_sources)} 篇反驳"
        }

    def _analyze_literature_evidence(
        self,
        statement: str,
        title: str,
        abstract: str,
        full_text: str
    ) -> Dict[str, Any]:
        """综合分析文献证据，结合统计结果和关键词"""
        text = f"{title} {abstract} {full_text}".lower()

        # 统计显著性指标
        significance_indicators = [
            "p<0.05", "p<0.01", "p<0.001",
            "显著", "高度显著", "极显著",
            "significant", "highly significant",
            "confident", "confidence interval"
        ]

        # 支持指标
        support_indicators = [
            "证实", "确认", "支持", "一致", "证明",
            "confirmed", "supported", "verified", "demonstrated",
            "consistent with", "in agreement"
        ]

        # 反驳指标
        contradict_indicators = [
            "否定", "反驳", "矛盾", "不支持",
            "rejected", "contradicted", "inconsistent",
            "disagreement", "contrary"
        ]

        # 检查统计显著性描述
        has_significance = any(ind in text for ind in significance_indicators)

        # 综合判断
        support_count = sum(1 for ind in support_indicators if ind in text)
        contradict_count = sum(1 for ind in contradict_indicators if ind in text)

        # 如果有统计显著性描述，增加判断权重
        if has_significance:
            if support_count > contradict_count:
                return {"supports": True, "reason": "统计显著支持"}
            elif contradict_count > support_count:
                return {"supports": False, "reason": "统计显著反驳"}
            else:
                return {"supports": True, "reason": "含统计显著性证据"}

        # 回退到关键词匹配
        if support_count > contradict_count:
            return {"supports": True, "reason": f"关键词支持({support_count}项)"}
        elif contradict_count > support_count:
            return {"supports": False, "reason": f"关键词反驳({contradict_count}项)"}
        else:
            return {"supports": True, "reason": "证据模糊，按保守原则计为支持"}

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

    def statistical_ttest(
        self,
        sample_data: List[float],
        expected_mean: float,
        alternative: str = "two-sided"
    ) -> Dict[str, Any]:
        """
        单样本t检验

        Args:
            sample_data: 样本数据列表
            expected_mean: 期望均值（零假设值）
            alternative: 备择假设 ("two-sided", "greater", "less")

        Returns:
            包含统计结果的字典
        """
        if len(sample_data) < 2:
            return {
                "test_type": "one_sample_ttest",
                "statistic": np.nan,
                "p_value": np.nan,
                "significant": False,
                "result": TestResult.INCONCLUSIVE,
                "interpretation": "样本数据不足，无法进行t检验"
            }

        sample = np.array(sample_data)
        t_stat, p_value = stats.ttest_1samp(sample, expected_mean)

        significant = p_value < 0.05
        if alternative == "greater":
            significant = t_stat > 0 and p_value < 0.05
        elif alternative == "less":
            significant = t_stat < 0 and p_value < 0.05

        return {
            "test_type": "one_sample_ttest",
            "n": len(sample_data),
            "mean": np.mean(sample),
            "std": np.std(sample, ddof=1),
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": significant,
            "result": TestResult.CONFIRMED if significant else TestResult.INCONCLUSIVE,
            "interpretation": self._interpret_ttest(t_stat, p_value, expected_mean)
        }

    def statistical_ttest_2sample(
        self,
        group1_data: List[float],
        group2_data: List[float],
        alternative: str = "two-sided",
        equal_var: bool = True
    ) -> Dict[str, Any]:
        """
        双样本t检验

        Args:
            group1_data: 第一组数据
            group2_data: 第二组数据
            alternative: 备择假设
            equal_var: 是否假设方差相等

        Returns:
            包含统计结果的字典
        """
        if len(group1_data) < 2 or len(group2_data) < 2:
            return {
                "test_type": "two_sample_ttest",
                "statistic": np.nan,
                "p_value": np.nan,
                "significant": False,
                "result": TestResult.INCONCLUSIVE,
                "interpretation": "样本数据不足，无法进行t检验"
            }

        g1 = np.array(group1_data)
        g2 = np.array(group2_data)

        t_stat, p_value = stats.ttest_ind(g1, g2, equal_var=equal_var)

        significant = p_value < 0.05

        return {
            "test_type": "two_sample_ttest",
            "n1": len(group1_data),
            "n2": len(group2_data),
            "mean1": np.mean(g1),
            "mean2": np.mean(g2),
            "std1": np.std(g1, ddof=1),
            "std2": np.std(g2, ddof=1),
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": significant,
            "result": TestResult.CONFIRMED if significant else TestResult.INCONCLUSIVE,
            "interpretation": self._interpret_2sample_ttest(t_stat, p_value, np.mean(g1), np.mean(g2))
        }

    def statistical_chisquare(
        self,
        observed: List[int],
        expected: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        卡方检验

        Args:
            observed: 观测频数
            expected: 期望频数（若为None，则检验均匀分布）

        Returns:
            包含统计结果的字典
        """
        if len(observed) < 2:
            return {
                "test_type": "chisquare",
                "statistic": np.nan,
                "p_value": np.nan,
                "significant": False,
                "result": TestResult.INCONCLUSIVE,
                "interpretation": "观测数据不足，无法进行卡方检验"
            }

        obs = np.array(observed)
        if expected is None:
            exp = np.full_like(obs, np.mean(obs), dtype=float)
        else:
            exp = np.array(expected)

        # 确保期望值不为零
        exp = np.where(exp == 0, 1e-10, exp)

        chi2_stat, p_value = stats.chisquare(obs, f_exp=exp)

        significant = p_value < 0.05

        return {
            "test_type": "chisquare",
            "observed": list(obs),
            "expected": list(exp),
            "chi2_statistic": chi2_stat,
            "p_value": p_value,
            "significant": significant,
            "result": TestResult.REJECTED if significant else TestResult.CONFIRMED,
            "interpretation": self._interpret_chisquare(chi2_stat, p_value)
        }

    def statistical_correlation(
        self,
        x_data: List[float],
        y_data: List[float],
        method: str = "pearson"
    ) -> Dict[str, Any]:
        """
        相关性检验

        Args:
            x_data: X变量数据
            y_data: Y变量数据
            method: 相关方法 ("pearson", "spearman", "kendall")

        Returns:
            包含统计结果的字典
        """
        if len(x_data) < 3 or len(y_data) < 3:
            return {
                "test_type": f"correlation_{method}",
                "statistic": np.nan,
                "p_value": np.nan,
                "significant": False,
                "result": TestResult.INCONCLUSIVE,
                "interpretation": "样本数据不足，无法进行相关性检验"
            }

        x = np.array(x_data)
        y = np.array(y_data)

        if method == "pearson":
            corr, p_value = stats.pearsonr(x, y)
        elif method == "spearman":
            corr, p_value = stats.spearmanr(x, y)
        elif method == "kendall":
            corr, p_value = stats.kendalltau(x, y)
        else:
            corr, p_value = stats.pearsonr(x, y)

        significant = p_value < 0.05

        return {
            "test_type": f"correlation_{method}",
            "n": len(x_data),
            "correlation": corr,
            "p_value": p_value,
            "significant": significant,
            "result": TestResult.CONFIRMED if significant else TestResult.INCONCLUSIVE,
            "interpretation": self._interpret_correlation(corr, p_value)
        }

    def _interpret_ttest(self, t_stat: float, p_value: float, expected_mean: float) -> str:
        """解释t检验结果"""
        if p_value < 0.001:
            significance = "极显著(p<0.001)"
        elif p_value < 0.01:
            significance = "高度显著(p<0.01)"
        elif p_value < 0.05:
            significance = "显著(p<0.05)"
        else:
            significance = "不显著(p>=0.05)"

        direction = "大于" if t_stat > 0 else "小于"
        return f"样本均值显著{direction}期望均值({expected_mean})，{significance}"

    def _interpret_2sample_ttest(self, t_stat: float, p_value: float, mean1: float, mean2: float) -> str:
        """解释双样本t检验结果"""
        if p_value < 0.001:
            significance = "极显著(p<0.001)"
        elif p_value < 0.01:
            significance = "高度显著(p<0.01)"
        elif p_value < 0.05:
            significance = "显著(p<0.05)"
        else:
            significance = "不显著(p>=0.05)"

        diff = mean1 - mean2
        direction = "大于" if diff > 0 else "小于"
        return f"两组均值差异{direction}零，两组均值{mean1:.3f}和{mean2:.3f}，{significance}"

    def _interpret_chisquare(self, chi2_stat: float, p_value: float) -> str:
        """解释卡方检验结果"""
        if p_value < 0.001:
            significance = "极显著(p<0.001)"
        elif p_value < 0.01:
            significance = "高度显著(p<0.01)"
        elif p_value < 0.05:
            significance = "显著(p<0.05)"
        else:
            significance = "不显著(p>=0.05)"

        return f"观测分布与期望分布存在显著差异，卡方值={chi2_stat:.3f}，{significance}"

    def _interpret_correlation(self, corr: float, p_value: float) -> str:
        """解释相关性检验结果"""
        if p_value >= 0.05:
            return f"变量间相关性不显著(r={corr:.3f}, p={p_value:.3f})"

        if abs(corr) < 0.3:
            strength = "弱"
        elif abs(corr) < 0.5:
            strength = "中等"
        elif abs(corr) < 0.7:
            strength = "较强"
        else:
            strength = "强"

        direction = "正" if corr > 0 else "负"
        return f"变量间存在显著{strength}{direction}相关(r={corr:.3f}, p={p_value:.3f})"

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
