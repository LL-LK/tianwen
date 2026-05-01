"""
天问-AGI 研究-观测联动模块 v1.0
ResearchObservatoryLinker - 将文献调研与天文观测调度集成

实现 Hermes 建议的观测-文献联动：
- 文献调研识别研究gap
- 调度优先级根据研究空白自动调整
- 形成完整的"文献调研→假说→验证→指导观测"闭环

用法:
    linker = ResearchObservatoryLinker()
    linked_plan = await linker.link("猎户座大星云恒星形成")
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LinkedObservation:
    """联动观测目标"""
    target: str
    original_priority: float
    adjusted_priority: float
    research_gap: str
    supporting_hypotheses: List[str]
    suggested_observations: List[Dict]
    literature_justification: str


@dataclass
class ResearchObservatoryPlan:
    """研究-观测联动计划"""
    query: str
    literature_review: Any  # LiteratureReview
    hypotheses: List[Any]
    linked_observations: List[LinkedObservation]
    gap_filled_targets: List[str]  # 填补了哪些研究空白
    created_at: str = ""


class ResearchObservatoryLinker:
    """
    研究-观测联动器

    将文献调研结果与观测调度连接：
    1. 分析文献调研识别的研究gap
    2. 生成或获取相关假说
    3. 调整观测优先级以填补研究空白
    4. 生成联动观测计划
    """

    def __init__(self, researcher=None, scheduler=None, hypothesis_generator=None):
        self.researcher = researcher
        self.scheduler = scheduler
        self.hypothesis_generator = hypothesis_generator
        self.gap_priority_boost = 20  # 填补研究gap的优先级提升

    async def link(self, research_topic: str, targets: Optional[List[str]] = None) -> ResearchObservatoryPlan:
        """
        执行研究-观测联动

        Args:
            research_topic: 研究主题
            targets: 可选的观测目标列表

        Returns:
            ResearchObservatoryPlan - 联动计划
        """
        # 1. 文献调研
        print(f"[联动] 开始文献调研: {research_topic}")
        if self.researcher:
            literature_review = await self.researcher.generate_review(
                research_topic, max_papers=30
            )
        else:
            literature_review = None

        # 2. 从文献识别研究gap
        gaps = []
        if literature_review and hasattr(literature_review, 'gaps'):
            gaps = literature_review.gaps

        # 3. 为每个gap生成/获取假说
        hypotheses = []
        if gaps:
            print(f"[联动] 识别到 {len(gaps)} 个研究gap")
            hypotheses = await self._generate_hypotheses_for_gaps(gaps)

        # 4. 联动观测目标
        linked_observations = []
        if targets:
            linked_observations = await self._link_targets_with_gaps(
                targets, gaps, hypotheses
            )

        # 5. 生成计划
        plan = ResearchObservatoryPlan(
            query=research_topic,
            literature_review=literature_review,
            hypotheses=hypotheses,
            linked_observations=linked_observations,
            gap_filled_targets=[lo.target for lo in linked_observations
                              if lo.adjusted_priority > lo.original_priority],
            created_at=datetime.now().isoformat()
        )

        return plan

    async def _generate_hypotheses_for_gaps(self, gaps: List[Any]) -> List[Any]:
        """为研究gap生成假说"""
        if not self.hypothesis_generator:
            return []

        hypotheses = []
        for gap in gaps:
            hypo = await self.hypothesis_generator.generate_scientific_hypothesis(
                topic=f"解决gap: {gap.description}",
                evidence=[f"gap类别: {gap.category}", gap.opportunity],
                prior_knowledge=[f"研究空白优先级: {gap.priority}"]
            )
            hypotheses.append(hypo)

        return hypotheses

    async def _link_targets_with_gaps(
        self,
        targets: List[str],
        gaps: List[Any],
        hypotheses: List[Any]
    ) -> List[LinkedObservation]:
        """将观测目标与研究gap关联"""
        linked = []

        for target in targets:
            original_priority = 50  # 默认优先级

            # 查找与目标相关的gap
            relevant_gaps = self._find_relevant_gaps(target, gaps)
            relevant_hypotheses = self._find_relevant_hypotheses(target, hypotheses)

            # 计算调整后的优先级
            gap_boost = len(relevant_gaps) * self.gap_priority_boost
            adjusted_priority = min(100, original_priority + gap_boost)

            # 生成建议观测
            suggested = self._generate_suggested_observations(target, relevant_gaps)

            linked_obs = LinkedObservation(
                target=target,
                original_priority=original_priority,
                adjusted_priority=adjusted_priority,
                research_gap=", ".join([g.description for g in relevant_gaps]) if relevant_gaps else "无",
                supporting_hypotheses=[h.statement for h in relevant_hypotheses] if relevant_hypotheses else [],
                suggested_observations=suggested,
                literature_justification=self._generate_justification(target, relevant_gaps)
            )

            linked.append(linked_obs)

        return linked

    def _find_relevant_gaps(self, target: str, gaps: List[Any]) -> List[Any]:
        """查找与目标相关的gap"""
        target_lower = target.lower()
        relevant = []

        for gap in gaps:
            # 基于天体名称或类别匹配
            if any(word in gap.description.lower() or word in gap.opportunity.lower()
                   for word in target_lower.split()):
                relevant.append(gap)

        return relevant

    def _find_relevant_hypotheses(self, target: str, hypotheses: List[Any]) -> List[Any]:
        """查找与目标相关的假说"""
        target_lower = target.lower()
        relevant = []

        for hypo in hypotheses:
            statement_lower = hypo.statement.lower() if hasattr(hypo, 'statement') else ""
            if any(word in statement_lower for word in target_lower.split()):
                relevant.append(hypo)

        return relevant

    def _generate_suggested_observations(self, target: str, gaps: List[Any]) -> List[Dict]:
        """生成建议观测列表"""
        suggestions = []

        for gap in gaps:
            if gap.category == "observation" or "多波段" in gap.description:
                suggestions.append({
                    "type": "multi_band",
                    "target": target,
                    "bands": ["optical", "infrared", "xray"],
                    "reason": f"填补研究空白: {gap.description}"
                })
            elif "光谱" in gap.description:
                suggestions.append({
                    "type": "spectroscopy",
                    "target": target,
                    "resolution": "high",
                    "reason": f"填补研究空白: {gap.description}"
                })
            elif "时间序列" in gap.description or "光变" in gap.description:
                suggestions.append({
                    "type": "light_curve",
                    "target": target,
                    "duration": "multi_year",
                    "reason": f"填补研究空白: {gap.description}"
                })

        if not suggestions:
            suggestions.append({
                "type": "standard",
                "target": target,
                "bands": ["optical"],
                "reason": "常规观测"
            })

        return suggestions

    def _generate_justification(self, target: str, gaps: List[Any]) -> str:
        """生成文献依据"""
        if not gaps:
            return f"{target}暂无特定研究空白驱动，基于常规观测优先级"

        justifications = []
        for gap in gaps:
            justifications.append(
                f"gap#{gap.id}: {gap.description} (优先级: {gap.priority})"
            )

        return f"{target}的观测可填补以下研究空白:\n" + "\n".join(justifications)

    async def update_scheduler_priorities(
        self,
        scheduler: Any,
        linked_observations: List[LinkedObservation]
    ) -> Dict[str, float]:
        """
        更新调度器的观测优先级

        Args:
            scheduler: ObservationScheduler 实例
            linked_observations: 联动观测列表

        Returns:
            Dict[str, float] - 目标→新优先级 的映射
        """
        updates = {}

        for lo in linked_observations:
            if lo.adjusted_priority > lo.original_priority:
                updates[lo.target] = lo.adjusted_priority
                print(f"[调度] {lo.target}: {lo.original_priority} → {lo.adjusted_priority} (gap填补)")

        return updates

    def export_plan(self, plan: ResearchObservatoryPlan, format: str = "markdown") -> str:
        """导出联动计划"""
        if format == "markdown":
            lines = ["# 研究-观测联动计划\n"]
            lines.append(f"\n**研究主题**: {plan.query}")
            lines.append(f"**生成时间**: {plan.created_at}\n")

            lines.append("\n## 研究空白分析")
            if plan.literature_review and hasattr(plan.literature_review, 'gaps'):
                for gap in plan.literature_review.gaps[:5]:
                    lines.append(f"- [{gap.priority}] {gap.description}")

            lines.append("\n## 联动观测目标")
            for lo in plan.linked_observations:
                lines.append(f"\n### {lo.target}")
                lines.append(f"- 原始优先级: {lo.original_priority}")
                lines.append(f"- 调整后优先级: {lo.adjusted_priority} (gap填补: +{lo.adjusted_priority - lo.original_priority})")
                lines.append(f"- 研究空白: {lo.research_gap or '无'}")
                lines.append(f"- 文献依据:\n  {lo.literature_justification}")

                if lo.suggested_observations:
                    lines.append("- 建议观测:")
                    for sug in lo.suggested_observations:
                        lines.append(f"  - {sug['type']}: {sug.get('reason', '')}")

            if plan.gap_filled_targets:
                lines.append(f"\n## 填补的研究空白")
                for t in plan.gap_filled_targets:
                    lines.append(f"- {t}")

            return "\n".join(lines)

        else:
            return json.dumps({
                "query": plan.query,
                "created_at": plan.created_at,
                "linked_observations": [
                    {
                        "target": lo.target,
                        "priority_change": lo.adjusted_priority - lo.original_priority,
                        "research_gap": lo.research_gap
                    }
                    for lo in plan.linked_observations
                ]
            }, ensure_ascii=False, indent=2)


async def demo():
    """演示研究-观测联动"""
    from literature_researcher import LiteratureResearcher
    from hypothesis_generator import HypothesisGenerator

    researcher = LiteratureResearcher()
    hypo_gen = HypothesisGenerator()
    linker = ResearchObservatoryLinker(
        researcher=researcher,
        hypothesis_generator=hypo_gen
    )

    # 执行联动
    plan = await linker.link(
        "猎户座大星云恒星形成",
        targets=["M42", "猎户座大星云", "NGC 1977"]
    )

    print("联动计划已生成!")
    print(linker.export_plan(plan))


if __name__ == "__main__":
    asyncio.run(demo())
