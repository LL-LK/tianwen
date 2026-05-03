"""
天问-AGI 自动化研究闭环 v1.0
ResearchLoop - 自动执行"文献调研→假说生成→验证→学习"全流程

实现 Hermes 建议的 P0 优先级：
- 自动化触发机制 (after_task 钩子)
- 完整闭环验证演示

用法:
    loop = ResearchLoop()
    result = await loop.run_full_cycle("开普勒-186f")
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class CycleResult:
    """完整闭环结果"""
    topic: str
    cycle_id: str
    started_at: str
    completed_at: str = ""
    literature_review: Any = None
    hypotheses: List[Any] = field(default_factory=list)
    test_reports: List[Any] = field(default_factory=list)
    discoveries: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    success: bool = False


class AfterTaskHook:
    """
    自动化触发钩子 - Hermes P0 优先级

    在每次任务完成后自动触发：
    1. 结果评估
    2. 模式提取
    3. 知识更新
    4. 自我进化
    """

    def __init__(self, research_loop=None):
        self.research_loop = research_loop
        self.task_history: List[Dict] = []
        self.trigger_conditions = {
            "task_completed": True,
            "hypothesis_generated": True,
            "verification_completed": True,
            "discovery_made": True
        }

    async def on_task_complete(self, task_result: Dict) -> bool:
        """
        任务完成时自动触发的钩子

        Args:
            task_result: 任务结果，包含 task_id, output, success 等

        Returns:
            bool - 是否触发了后续行动
        """
        task_id = task_result.get("task_id", "unknown")
        success = task_result.get("success", False)
        output = task_result.get("output", "")

        print(f"[Hook] 任务 {task_id} 完成: success={success}")

        # 记录任务历史
        self.task_history.append({
            "task_id": task_id,
            "success": success,
            "output": str(output)[:200],
            "timestamp": datetime.now().isoformat()
        })

        # 触发自我复盘
        triggered = await self._trigger_self_review(task_result)

        return triggered

    async def _trigger_self_review(self, task_result: Dict) -> bool:
        """触发自我复盘"""
        # 检查是否需要复盘
        needs_review = (
            not task_result.get("success", True) or
            self._is_significant_task(task_result)
        )

        if needs_review:
            print(f"[Hook] 触发自我复盘 for {task_result.get('task_id')}")
            # 提取教训
            lesson = self._extract_lesson(task_result)
            if lesson:
                await self._update_knowledge_base(lesson)
                return True

        return False

    def _is_significant_task(self, task_result: Dict) -> bool:
        """判断是否是需要复盘的重要任务"""
        significant_keywords = ["假说", "验证", "发现", "观测", "研究", "分析"]
        output = str(task_result.get("output", "")).lower()

        return any(kw in output for kw in significant_keywords)

    def _extract_lesson(self, task_result: Dict) -> Optional[str]:
        """从任务结果中提取教训"""
        if task_result.get("success"):
            return None

        task_id = task_result.get("task_id", "")
        error = task_result.get("error", "")

        return f"任务 {task_id} 失败: {error[:100] if error else '未知原因'}"

    async def _update_knowledge_base(self, lesson: str) -> bool:
        """更新知识库"""
        print(f"[Hook] 更新知识库: {lesson}")
        # 这里可以集成 memory_persistence.py 来持久化
        return True

    async def on_hypothesis_generated(self, hypothesis: Any) -> bool:
        """假说生成时自动触发"""
        print(f"[Hook] 假说生成: {hypothesis.id if hasattr(hypothesis, 'id') else 'unknown'}")

        # 立即触发验证（如果配置了自动验证）
        if self.research_loop and self.research_loop.auto_verify:
            print("[Hook] 触发自动验证")
            return True

        return False

    async def on_verification_complete(self, test_report: Any) -> bool:
        """验证完成时自动触发"""
        result = test_report.overall_result.value if hasattr(test_report, 'overall_result') else "unknown"
        print(f"[Hook] 验证完成: {result}")

        # 如果是重要发现，触发学习
        if result == "confirmed" and hasattr(test_report, 'evidence_for'):
            print("[Hook] 发现被证实，触发知识更新")
            await self._update_from_discovery(test_report)
            return True

        return False

    async def _update_from_discovery(self, test_report: Any) -> bool:
        """从发现中学习"""
        print("[Hook] 从验证结果中提取模式")
        return True

    def get_statistics(self) -> Dict:
        """获取钩子统计"""
        total = len(self.task_history)
        successful = sum(1 for t in self.task_history if t.get("success"))

        return {
            "total_tasks": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0
        }


class ResearchLoop:
    """
    自动化研究闭环 - 完整流程自动执行

    工作流程:
    1. 文献调研 (literature_researcher)
    2. 假说生成 (hypothesis_generator)
    3. 假说验证 (hypothesis_tester)
    4. 追踪记录 (discovery_tracker)
    5. 指导观测 (research_observatory_linker)
    """

    def __init__(
        self,
        literature_researcher=None,
        hypothesis_generator=None,
        hypothesis_tester=None,
        discovery_tracker=None,
        linker=None
    ):
        self.literature_researcher = literature_researcher
        self.hypothesis_generator = hypothesis_generator
        self.hypothesis_tester = hypothesis_tester
        self.discovery_tracker = discovery_tracker
        self.linker = linker
        self.hook = AfterTaskHook(self)
        self.auto_verify = True  # 自动验证开关
        self.cycle_history: List[CycleResult] = []

    async def run_full_cycle(self, topic: str, targets: Optional[List[str]] = None) -> CycleResult:
        """
        运行完整的研究闭环

        Args:
            topic: 研究主题
            targets: 可选的观测目标列表

        Returns:
            CycleResult - 完整闭环结果
        """
        cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now().isoformat()

        print(f"\n{'='*60}")
        print(f"[ResearchLoop] 开始闭环: {topic}")
        print(f"{'='*60}\n")

        result = CycleResult(
            topic=topic,
            cycle_id=cycle_id,
            started_at=started_at
        )

        try:
            # ========== 步骤1: 文献调研 ==========
            print(f"[Step 1/5] 文献调研: {topic}")
            if self.literature_researcher:
                result.literature_review = await self.literature_researcher.research(
                    topic, max_papers=20
                )
                print(f"  → 获取了 {len(result.literature_review.papers) if result.literature_review else 0} 篇论文")

            # ========== 步骤2: 假说生成 ==========
            print(f"\n[Step 2/5] 假说生成")
            if self.hypothesis_generator and result.literature_review:
                result.hypotheses = await self.hypothesis_generator.generate_from_research(
                    result.literature_review
                )
                print(f"  → 生成了 {len(result.hypotheses)} 个假说")

                # 触发钩子
                for hypo in result.hypotheses:
                    await self.hook.on_hypothesis_generated(hypo)

            # ========== 步骤3: 假说验证 ==========
            print(f"\n[Step 3/5] 假说验证")
            for hypo in result.hypotheses[:3]:  # 限制验证数量
                if self.hypothesis_tester:
                    report = await self.hypothesis_tester.test_hypothesis(hypo)
                    result.test_reports.append(report)
                    print(f"  → {hypo.id}: {report.overall_result.value}")

                    # 触发钩子
                    await self.hook.on_verification_complete(report)

            # ========== 步骤4: 追踪记录 ==========
            print(f"\n[Step 4/5] 追踪记录")
            if self.discovery_tracker:
                for hypo in result.hypotheses:
                    await self.discovery_tracker.track_hypothesis(hypo)

                    # 记录验证结果
                    for report in result.test_reports:
                        if report.hypothesis_id == hypo.id:
                            from discovery_tracker import VerificationOutcome
                            outcome = VerificationOutcome.CONFIRMED if report.overall_result.value == "confirmed" else VerificationOutcome.REJECTED
                            await self.discovery_tracker.record_verification(
                                hypothesis_id=hypo.id,
                                outcome=outcome,
                                evidence=report.evidence_for + report.evidence_against,
                                method=report.test_cases[0].test_method if report.test_cases else "unknown"
                            )

                stats = await self.discovery_tracker.get_statistics()
                print(f"  → 追踪统计: {stats}")

            # ========== 步骤5: 指导观测 ==========
            print(f"\n[Step 5/5] 指导观测")
            if self.linker and targets:
                linked_plan = await self.linker.link(topic, targets)
                result.discoveries = linked_plan.gap_filled_targets
                print(f"  → 调整了 {len(linked_plan.linked_observations)} 个观测目标优先级")

            result.success = True
            result.completed_at = datetime.now().isoformat()

        except Exception as e:
            print(f"\n[Error] 闭环执行出错: {e}")
            result.success = False
            result.completed_at = datetime.now().isoformat()

        # 记录到历史
        self.cycle_history.append(result)

        print(f"\n{'='*60}")
        print(f"[ResearchLoop] 闭环完成: {'成功' if result.success else '失败'}")
        print(f"{'='*60}\n")

        return result

    def get_cycle_summary(self) -> Dict:
        """获取闭环历史摘要"""
        total = len(self.cycle_history)
        successful = sum(1 for c in self.cycle_history if c.success)

        total_hypotheses = sum(len(c.hypotheses) for c in self.cycle_history)
        total_verifications = sum(len(c.test_reports) for c in self.cycle_history)

        return {
            "total_cycles": total,
            "successful_cycles": successful,
            "success_rate": successful / total if total > 0 else 0,
            "total_hypotheses_generated": total_hypotheses,
            "total_verifications": total_verifications,
            "hook_statistics": self.hook.get_statistics()
        }


async def demo():
    """
    演示完整闭环 - 验证 Hermes P0 优先级

    给一个具体天体，看系统能否自动完成：
    调研 → 假说生成 → 验证计划
    """
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     天问-AGI 自动化研究闭环验证 (Hermes P0 优先级)         ║
    ║                                                              ║
    ║     目标: 开普勒-186f (潜在宜居系外行星)                    ║
    ║     验证: 系统能否自动完成调研→假说→验证全流程              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    from literature_researcher import LiteratureResearcher
    from hypothesis_generator import HypothesisGenerator
    from hypothesis_tester import HypothesisTester
    from discovery_tracker import DiscoveryTracker
    from research_observatory_linker import ResearchObservatoryLinker

    # 初始化各模块
    researcher = LiteratureResearcher()
    hypo_gen = HypothesisGenerator()
    tester = HypothesisTester()
    tracker = DiscoveryTracker()
    linker = ResearchObservatoryLinker()

    # 创建研究闭环
    loop = ResearchLoop(
        literature_researcher=researcher,
        hypothesis_generator=hypo_gen,
        hypothesis_tester=tester,
        discovery_tracker=tracker,
        linker=linker
    )
    loop.auto_verify = True

    # 运行完整闭环
    result = await loop.run_full_cycle(
        "Kepler-186f habitability exoplanet",
        targets=["Kepler-186f", "TRAPPIST-1e"]
    )

    # 输出总结
    print("\n" + "="*60)
    print("闭环验证结果")
    print("="*60)
    print(f"主题: {result.topic}")
    print(f"成功: {result.success}")
    print(f"生成假说: {len(result.hypotheses)}")
    print(f"执行验证: {len(result.test_reports)}")
    print(f"发现: {result.discoveries}")

    summary = loop.get_cycle_summary()
    print(f"\n总体统计:")
    print(f"  闭环成功率: {summary['success_rate']:.0%}")
    print(f"  钩子触发统计: {summary['hook_statistics']}")

    return result


if __name__ == "__main__":
    asyncio.run(demo())
