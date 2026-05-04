"""
天问-AGI 假说生成器 v1.0
HypothesisGenerator - 从文献和观测数据生成可验证假说

基于 Hermes 建议的 Structured Hypothesis Format (SHF)
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# 导入统一数据模型
from data_models import Hypothesis, HypothesisStatus


class HypothesisGenerator:
    """
    假说生成器 - 从文献调研和观测数据生成可验证假说

    用法:
        generator = HypothesisGenerator()
        hypotheses = await generator.generate_from_research(research_state)
    """

    def __init__(self):
        self.evidence_patterns = {
            "positive": [
                "确认", "证实", "支持", "一致", "相关",
                "confirmed", "supported", "consistent", "correlated"
            ],
            "negative": [
                "否定", "反驳", "矛盾", "无关", "不一致",
                "rejected", "contradicted", "inconsistent", "unrelated"
            ]
        }

    async def generate_from_research(
        self,
        research_state: Any,
        observations: Optional[List[Dict]] = None
    ) -> List[Hypothesis]:
        """
        从研究现状生成假说列表

        Args:
            research_state: LiteratureResearcher 返回的 ResearchState
            observations: 可选的观测数据列表

        Returns:
            List[Hypothesis] - 生成的假说列表
        """
        hypotheses = []

        # 1. 从研究Gap生成假说
        if hasattr(research_state, 'research_gaps'):
            for gap in research_state.research_gaps:
                hypo = await self._generate_from_gap(gap, research_state)
                if hypo:
                    hypotheses.append(hypo)

        # 2. 从论文聚类生成假说
        if hasattr(research_state, 'paper_clusters'):
            for cluster in research_state.paper_clusters:
                hypo = await self._generate_from_cluster(cluster, research_state)
                if hypo:
                    hypotheses.append(hypo)

        # 3. 结合观测数据生成假说
        if observations:
            for obs in observations:
                hypo = await self._generate_from_observation(obs, research_state)
                if hypo:
                    hypotheses.append(hypo)

        return hypotheses

    async def _generate_from_gap(self, gap: Any, research_state: Any) -> Optional[Hypothesis]:
        """从研究空白生成假说"""
        if not gap.description:
            return None

        hypo_id = f"hypo_gap_{uuid.uuid4().hex[:8]}"

        # 构建If-Then陈述
        statement = f"如果解决'{gap.category}类型'的gap：{gap.description}，那么会产生新的研究机会"

        # 从gap机会生成预测
        predictions = [
            f"该gap的解决将推动{gap.category}方向的发展",
            f"填补后可能发现新的{gap.opportunity}",
        ]

        return Hypothesis(
            id=hypo_id,
            content=statement,
            confidence=0.6,
            status=HypothesisStatus.PENDING,
            evidence=gap.evidence if hasattr(gap, 'evidence') else [],
            source="research_gap",
            premises=[f"研究空白: {gap.description}"],
            predictions=predictions,
            verification_method=f"文献调研 + 专家评审"
        )

    async def _generate_from_cluster(
        self,
        cluster: List[int],
        research_state: Any
    ) -> Optional[Hypothesis]:
        """从论文聚类生成假说"""
        if len(cluster) < 2:
            return None

        papers = [research_state.papers[i] for i in cluster if i < len(research_state.papers)]
        if not papers:
            return None

        hypo_id = f"hypo_cluster_{uuid.uuid4().hex[:8]}"

        # 提取共同主题
        themes = set()
        for paper in papers:
            themes.update(paper.categories)

        statement = (
            f"如果这些论文({len(papers)}篇)代表的研究方向是正确的，"
            f"那么在{', '.join(list(themes)[:2])}领域存在系统性关联"
        )

        return Hypothesis(
            id=hypo_id,
            content=statement,
            confidence=0.7,
            status=HypothesisStatus.PENDING,
            source="paper_cluster",
            premises=[p.title for p in papers],
            predictions=[
                f"该聚类中的论文在主题上具有高相关性",
                f"后续研究应考虑该聚类中论文的联合引用"
            ],
            verification_method="论文共引分析 + 主题建模"
        )

    async def _generate_from_observation(
        self,
        observation: Dict,
        research_state: Any
    ) -> Optional[Hypothesis]:
        """从观测数据生成假说"""
        target = observation.get("target", "")
        data = observation.get("data", {})

        if not target or not data:
            return None

        hypo_id = f"hypo_obs_{uuid.uuid4().hex[:8]}"

        # 基于观测类型生成假说
        obs_type = observation.get("type", "unknown")

        if obs_type == "spectrum":
            statement = (
                f"如果对{target}的光谱分析显示特定模式，"
                f"那么可以推断其物理状态（温度、成分、运动）"
            )
            verification_method = "光谱分析 + 物理建模"
        elif obs_type == "light_curve":
            statement = (
                f"如果{target}的光变曲线显示周期性，"
                f"那么可能存在掩星、脉动或自转效应"
            )
            verification_method = "光变曲线周期分析 + 物理机制建模"
        else:
            statement = f"如果对{target}的观测数据模式成立，那么反映了某种物理现象"
            verification_method = "数据统计分析"

        return Hypothesis(
            id=hypo_id,
            content=statement,
            confidence=0.5,
            status=HypothesisStatus.PENDING,
            source="observation",
            premises=[f"观测目标: {target}", f"观测类型: {obs_type}"],
            predictions=[
                f"该观测支持{target}的某种物理特性",
                f"独立观测应能复现相同模式"
            ],
            verification_method=verification_method
        )

    async def generate_scientific_hypothesis(
        self,
        topic: str,
        evidence: List[str],
        prior_knowledge: Optional[List[str]] = None
    ) -> Hypothesis:
        """
        生成科学假说的高级接口

        Args:
            topic: 假说主题
            evidence: 支撑证据列表
            prior_knowledge: 先验知识列表

        Returns:
            Hypothesis - 结构化假说
        """
        hypo_id = f"hypo_{uuid.uuid4().hex[:8]}"

        statement = f"如果{topic}成立，那么将观察到特定的现象"

        predictions = [
            f"假说成立时，应能预测可观测的现象",
            f"该预测可通过实验/观测验证"
        ]

        # 计算初始置信度
        confidence = min(0.9, 0.3 + 0.1 * len(evidence))

        return Hypothesis(
            id=hypo_id,
            content=statement,
            confidence=confidence,
            status=HypothesisStatus.PENDING,
            source="scientific",
            premises=evidence + (prior_knowledge or []),
            predictions=predictions,
            verification_method="待指定"
        )

    def export_hypotheses(self, hypotheses: List[Hypothesis], format: str = "json") -> str:
        """
        导出假说列表

        Args:
            hypotheses: 假说列表
            format: 输出格式 (json/markdown)

        Returns:
            str - 格式化输出
        """
        if format == "json":
            return json.dumps([h.to_dict() for h in hypotheses], ensure_ascii=False, indent=2)
        elif format == "markdown":
            lines = ["# 假说列表\n"]
            for h in hypotheses:
                lines.append(f"## {h.id}: {h.status}")
                lines.append(f"\n**陈述**: {h.content}")
                lines.append(f"\n**置信度**: {h.confidence:.0%}")
                lines.append(f"\n**前提**:")
                for p in h.premises:
                    lines.append(f"- {p}")
                lines.append(f"\n**预测**:")
                for p in h.predictions:
                    lines.append(f"- {p}")
                lines.append(f"\n**验证方法**: {h.verification_method}")
                lines.append("\n---")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")


# ============ 与观测系统联动示例 ============

async def demo():
    """演示假说生成流程"""
    from literature_researcher import LiteratureResearcher

    # 1. 进行文献调研
    researcher = LiteratureResearcher()
    state = await researcher.research("exoplanet atmosphere characterization", max_papers=20)

    # 2. 生成假说
    generator = HypothesisGenerator()
    hypotheses = await generator.generate_from_research(state)

    print(f"生成了 {len(hypotheses)} 个假说")
    for h in hypotheses[:3]:
        print(f"\n{h.id}: {h.statement}")
        print(f"   置信度: {h.confidence:.0%}")

    # 3. 导出
    print("\n" + generator.export_hypotheses(hypotheses, format="markdown"))


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
