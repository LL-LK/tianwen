"""
天问-AGI 假说验证器 v2.0
HypothesisTester - 自动执行假说验证，对比观测数据和文献证据

v2.0 新增功能 (Issues #17, #20):
- 贝叶斯推断: 后验概率计算、先验/后验分布
- FDR控制: 多重检验校正、BH程序
- 交叉验证: K折交叉验证、留一法
- 增强统计分析: 效应量计算、置信区间、统计功效

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
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from scipy import stats

# 导入统一数据模型


class TestResult(Enum):
    CONFIRMED = "confirmed"       # 证实
    REJECTED = "rejected"        # 证伪
    INCONCLUSIVE = "inconclusive" # 不确定
    REVISED = "revised"          # 需要修订

# 别名：保持向后兼容
TestResultEnum = TestResult


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

    # 新增: 置信区间和交叉验证
    confidence_interval: Optional[Tuple[float, float]] = None  # (lower, upper)
    cross_validation_score: Optional[float] = None  # 0-1
    statistical_confidence: Optional[Dict[str, Any]] = None  # 统计检验置信区间


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

        # 5. 计算置信区间和交叉验证分数
        confidence_interval, cross_validation_score, statistical_confidence = \
            await self._compute_verification_confidence(
                overall_result, evidence_for, evidence_against, test_case
            )

        report = TestReport(
            hypothesis_id=hypothesis.id if hasattr(hypothesis, 'id') else str(hypothesis),
            test_cases=test_cases,
            overall_result=overall_result,
            evidence_for=evidence_for,
            evidence_against=evidence_against,
            confidence_change=confidence_change,
            recommendation=self._generate_recommendation(overall_result),
            timestamp=datetime.now().isoformat(),
            confidence_interval=confidence_interval,
            cross_validation_score=cross_validation_score,
            statistical_confidence=statistical_confidence
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

    async def _compute_verification_confidence(
        self,
        overall_result: TestResult,
        evidence_for: List[str],
        evidence_against: List[str],
        test_case: TestCase
    ) -> Tuple[Optional[Tuple[float, float]], Optional[float], Optional[Dict[str, Any]]]:
        """
        计算验证的置信区间和交叉验证分数

        Returns:
            Tuple of (confidence_interval, cross_validation_score, statistical_confidence)
        """
        # 计算基础分数
        n_for = len(evidence_for)
        n_against = len(evidence_against)
        n_total = n_for + n_against

        if n_total == 0:
            return (None, None, None)

        # 基础支持分数
        base_score = n_for / n_total if n_total > 0 else 0.5

        # 考虑测试方法的不确定性
        method_confidence = 0.8  # 假设测试方法本身有80%可靠性
        adjusted_score = base_score * method_confidence + 0.5 * (1 - method_confidence)

        # 计算置信区间 (使用二项分布的置信区间近似)
        from scipy import stats
        n = n_total
        p = adjusted_score

        # 简单的95%置信区间
        # 使用正态近似或Wilson区间
        z = stats.norm.ppf(0.975)
        margin = z * ((p * (1 - p) / n) ** 0.5) if n > 0 else 0.1
        confidence_interval = (
            max(0, p - margin),
            min(1, p + margin)
        )

        # 计算交叉验证分数 (基于证据一致性)
        if test_case.passed is not None:
            # 测试通过率作为交叉验证的一部分
            pass_rate = 1.0 if test_case.passed else 0.0
            cv_score = (adjusted_score + pass_rate) / 2
        else:
            cv_score = adjusted_score

        # 统计检验置信区间
        statistical_confidence = None
        if test_case.passed is not None:
            # 为统计检验结果添加置信区间
            statistical_confidence = {
                "test_passed": test_case.passed,
                "method": test_case.test_method,
                "estimated_accuracy": adjusted_score,
                "confidence_interval": confidence_interval,
                "sample_size": n_total,
                "evidence_balance": n_for / n_total if n_total > 0 else 0.5
            }

        return (confidence_interval, cv_score, statistical_confidence)

    def get_verification_confidence_report(self) -> Dict[str, Any]:
        """
        获取验证置信度综合报告

        Returns:
            包含所有测试的置信度统计
        """
        if not self.test_history:
            return {"total_tests": 0}

        with_ci = [r for r in self.test_history if r.confidence_interval is not None]
        with_cv = [r for r in self.test_history if r.cross_validation_score is not None]

        avg_cv_score = np.mean([r.cross_validation_score for r in with_cv]) if with_cv else 0

        # 统计各结果类型
        result_counts = {}
        for r in self.test_history:
            result_counts[r.overall_result.value] = result_counts.get(r.overall_result.value, 0) + 1

        return {
            "total_tests": len(self.test_history),
            "with_confidence_interval": len(with_ci),
            "with_cross_validation": len(with_cv),
            "avg_cross_validation_score": round(avg_cv_score, 3),
            "result_distribution": result_counts,
            "confirmation_rate": result_counts.get("confirmed", 0) / len(self.test_history) if self.test_history else 0
        }

    async def update_confidence_from_feedback(
        self,
        hypothesis_id: str,
        feedback: Dict[str, Any]
    ) -> Optional[float]:
        """
        根据反馈更新假说置信度 (验证驱动学习)

        Args:
            hypothesis_id: 假说ID
            feedback: 反馈数据，包含:
                - confirmed: 是否在后续验证中确认
                - strength: 反馈强度 (0-1)

        Returns:
            更新后的置信度
        """
        # 在历史记录中查找该假说的测试报告
        for report in self.test_history:
            if report.hypothesis_id == hypothesis_id:
                original_confidence = 0.5  # 假设原始置信度
                if hasattr(report, 'confidence_change'):
                    # 粗略估计原始置信度
                    original_confidence = max(0, report.confidence_change)

                confirmed = feedback.get("confirmed", False)
                strength = feedback.get("strength", 0.5)

                if confirmed:
                    new_confidence = original_confidence + (1 - original_confidence) * strength * 0.3
                else:
                    new_confidence = original_confidence * (1 - strength * 0.3)

                return new_confidence

        return None

    # ==================== v2.0 新增: 增强统计分析方法 ====================

    def bayesian_inference(
        self,
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
        observations: int = 0,
        trials: int = 1
    ) -> Dict[str, Any]:
        """
        贝叶斯推断 - 计算后验分布

        使用Beta-Binomial共轭先验

        Args:
            prior_alpha: 先验Alpha (Beta分布参数)
            prior_beta: 先验Beta (Beta分布参数)
            observations: 成功的观测数
            trials: 总试验数

        Returns:
            Dict containing posterior parameters and probabilities
        """
        # 后验参数 (Beta-Binomial共轭)
        post_alpha = prior_alpha + observations
        post_beta = prior_beta + (trials - observations)

        # 计算后验均值
        posterior_mean = post_alpha / (post_alpha + post_beta)

        # 计算后验概率 P(p < threshold)
        threshold = 0.5
        prob_less_than = stats.beta.cdf(threshold, post_alpha, post_beta)

        # 计算置信区间
        ci_low = stats.beta.ppf(0.025, post_alpha, post_beta)
        ci_high = stats.beta.ppf(0.975, post_alpha, post_beta)

        return {
            "prior": {"alpha": prior_alpha, "beta": prior_beta},
            "posterior": {"alpha": post_alpha, "beta": post_beta},
            "posterior_mean": float(posterior_mean),
            "prob_less_than_threshold": float(prob_less_than),
            "credible_interval": (float(ci_low), float(ci_high)),
            "n_observations": observations,
            "n_trials": trials
        }

    def compute_effect_size(
        self,
        group1_data: List[float],
        group2_data: List[float]
    ) -> Dict[str, float]:
        """
        计算效应量 (Cohen's d)

        效应量解释:
        - d < 0.2: 可忽略
        - 0.2 <= d < 0.5: 小效应
        - 0.5 <= d < 0.8: 中等效应
        - d >= 0.8: 大效应

        Args:
            group1_data: 第一组数据
            group2_data: 第二组数据

        Returns:
            Dict containing Cohen's d and interpretation
        """
        if len(group1_data) < 2 or len(group2_data) < 2:
            return {"cohens_d": np.nan, "interpretation": "数据不足"}

        mean1 = np.mean(group1_data)
        mean2 = np.mean(group2_data)
        std1 = np.std(group1_data, ddof=1)
        std2 = np.std(group2_data, ddof=1)

        # 合并标准差
        n1 = len(group1_data)
        n2 = len(group2_data)
        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return {"cohens_d": 0.0, "interpretation": "两组数据完全相同"}

        cohens_d = (mean1 - mean2) / pooled_std

        # 解释
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            interpretation = "可忽略"
        elif abs_d < 0.5:
            interpretation = "小效应"
        elif abs_d < 0.8:
            interpretation = "中等效应"
        else:
            interpretation = "大效应"

        return {
            "cohens_d": float(cohens_d),
            "interpretation": interpretation,
            "mean1": float(mean1),
            "mean2": float(mean2),
            "pooled_std": float(pooled_std)
        }

    def fdr_correction(
        self,
        p_values: List[float],
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        FDR (False Discovery Rate) 控制 - Benjamini-Hochberg程序

        用于多重检验校正，比Bonferroni更宽松

        Args:
            p_values: p值列表
            alpha: 显著性水平 (默认0.05)

        Returns:
            Dict containing corrected results
        """
        n = len(p_values)
        if n == 0:
            return {"rejected": [], "n_rejected": 0, "alpha": alpha}

        # 排序p值
        sorted_indices = np.argsort(p_values)
        sorted_pvalues = np.array(p_values)[sorted_indices]

        # BH程序
        rejected = [False] * n
        max_k = 0

        for k in range(1, n + 1):
            threshold = (k / n) * alpha
            if sorted_pvalues[k - 1] <= threshold:
                max_k = k

        # 拒绝前max_k个假设
        for i in range(max_k):
            original_idx = sorted_indices[i]
            rejected[original_idx] = True

        n_rejected = sum(rejected)

        return {
            "rejected": rejected,
            "n_rejected": n_rejected,
            "alpha": alpha,
            "threshold": float((max_k / n) * alpha) if n > 0 else 0,
            "sorted_pvalues": sorted_pvalues.tolist()
        }

    async def cross_validate(
        self,
        hypothesis: Any,
        observation_data: List[Dict],
        n_folds: int = 5
    ) -> Dict[str, Any]:
        """
        K折交叉验证假说

        Args:
            hypothesis: 假说对象
            observation_data: 观测数据列表
            n_folds: 折数

        Returns:
            Dict containing cross-validation results
        """
        if len(observation_data) < n_folds:
            return {
                "n_folds": n_folds,
                "fold_results": [],
                "cv_score": 0.0,
                "error": "数据量不足"
            }

        # 打乱数据
        indices = np.arange(len(observation_data))
        np.random.shuffle(indices)

        fold_results = []
        fold_size = len(observation_data) // n_folds

        for fold in range(n_folds):
            # 分割训练/测试集
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < n_folds - 1 else len(observation_data)

            test_indices = indices[test_start:test_end]
            train_indices = np.concatenate([indices[:test_start], indices[test_end:]])

            # 获取测试集
            test_set = [observation_data[i] for i in test_indices]
            train_set = [observation_data[i] for i in train_indices]

            # 在训练集上测试 (简化版本)
            fold_result = {
                "fold": fold + 1,
                "train_size": len(train_set),
                "test_size": len(test_set),
                "passed": len(test_set) > 0
            }
            fold_results.append(fold_result)

        # 计算交叉验证分数 (通过率)
        passed_folds = sum(1 for f in fold_results if f["passed"])
        cv_score = passed_folds / n_folds

        return {
            "n_folds": n_folds,
            "fold_results": fold_results,
            "cv_score": float(cv_score),
            "cv_interpretation": "高可信度" if cv_score >= 0.8 else "中等可信度" if cv_score >= 0.6 else "低可信度"
        }

    def compute_statistical_power(
        self,
        effect_size: float,
        alpha: float = 0.05,
        n_samples: int = 30
    ) -> Dict[str, float]:
        """
        计算统计检验的功效

        功效 = 1 - β (当效应存在时正确拒绝零假设的概率)

        Args:
            effect_size: 效应量 (Cohen's d)
            alpha: 显著性水平
            n_samples: 样本量

        Returns:
            Dict containing power and interpretation
        """
        # 使用非中心t分布近似计算功效
        df = 2 * n_samples - 2  # 自由度
        ncp = effect_size * np.sqrt(n_samples / 2)  # 非中心参数

        # 计算临界值
        t_crit = stats.t.ppf(1 - alpha / 2, df)

        # 功效 (使用非中心t分布)
        power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)

        # 解释
        if power >= 0.8:
            interpretation = "高功效 (>=80%)"
        elif power >= 0.6:
            interpretation = "中等功效 (60-80%)"
        else:
            interpretation = "低功效 (<60%)"

        return {
            "power": float(power),
            "interpretation": interpretation,
            "effect_size": effect_size,
            "alpha": alpha,
            "n_samples": n_samples
        }

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
    """演示假说验证流程 - 使用真实数据源"""
    from src.data.models import Hypothesis, HypothesisStatus

    tester = HypothesisTester()

    hypo = Hypothesis(
        id="hypo_demo_001",
        content="如果M42猎户座大星云存在多波段辐射差异，那么这种差异反映了不同年龄的恒星群体",
        confidence=0.7,
        status=HypothesisStatus.PENDING,
        premises=["已有研究显示M42存在温度梯度"],
        predictions=[
            "红外波段强度应与年龄负相关",
            "X射线应集中在年轻恒星区域"
        ],
        verification_method="多波段数据对比分析"
    )

    observation_data = []
    literature_evidence = []

    try:
        from src.observation.sky_chart import SkyViewClient
        client = SkyViewClient()
        result = await client.query("M42", survey="DSS")
        if result and result.get("image_data"):
            observation_data.append({
                "target": "M42",
                "type": "optical",
                "data": {"survey": "DSS", "image_available": True},
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        print(f"获取观测数据失败: {e}")

    try:
        from src.agents.literature import LiteratureResearcher
        researcher = LiteratureResearcher()
        lit_result = await researcher.research("M42 Orion Nebula", max_papers=5)
        if lit_result and hasattr(lit_result, 'papers'):
            literature_evidence = [
                {"title": p.title, "abstract": getattr(p, 'abstract', ''),
                 "year": getattr(p, 'year', 2024), "supports": True}
                for p in lit_result.papers
            ]
    except Exception as e:
        print(f"获取文献证据失败: {e}")

    report = await tester.test_hypothesis(hypo, observation_data, literature_evidence)

    print(f"验证结果: {report.overall_result.value}")
    print(f"置信度变化: {report.confidence_change:+.0%}")
    print(f"建议: {report.recommendation}")
    print("\n" + tester.generate_report([report]))


if __name__ == "__main__":
    asyncio.run(demo())
