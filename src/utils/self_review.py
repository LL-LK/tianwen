"""
Hermes-AGI Self-Review System
自我复盘系统 - 定期分析任务表现并给出改进建议
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

# ============ 复盘数据模型 ============

@dataclass
class ReviewPeriod:
    """复盘周期"""
    start_date: str
    end_date: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    avg_execution_time: float
    top_skills_used: List[tuple]
    common_failure_reasons: List[tuple]
    suggestions: List[str]
    patterns_identified: List[Dict]

@dataclass
class WeeklyReview:
    """周复盘报告"""
    week_number: int
    year: int
    period: str
    stats: Dict
    successes: List[Dict]
    failures: List[Dict]
    skill_performance: Dict[str, Dict]
    top_patterns: List[Dict]
    improvements: List[str]
    next_week_goals: List[str]

# ============ 自我复盘系统 ============

class SelfReviewSystem:
    """自我复盘系统"""

    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.task_history_file = self.memory_dir / "task_history.json"
        self.reviews_file = self.memory_dir / "reviews.json"

        self.task_history: List[Dict] = []
        self.reviews: List[Dict] = []

        self._load_data()

    def _load_data(self):
        """加载数据"""
        if self.task_history_file.exists():
            try:
                with open(self.task_history_file, 'r', encoding='utf-8') as f:
                    self.task_history = json.load(f)
            except Exception:
                self.task_history = []

        if self.reviews_file.exists():
            try:
                with open(self.reviews_file, 'r', encoding='utf-8') as f:
                    self.reviews = json.load(f)
            except Exception:
                self.reviews = []

    def _save_data(self):
        """保存数据"""
        with open(self.task_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.task_history, f, ensure_ascii=False, indent=2)

        with open(self.reviews_file, 'w', encoding='utf-8') as f:
            json.dump(self.reviews, f, ensure_ascii=False, indent=2)

    def _get_date_range(self, days: int = 7) -> tuple:
        """获取日期范围"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date

    def _filter_by_date(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """按日期筛选任务"""
        filtered = []
        for task in self.task_history:
            try:
                task_time = datetime.fromisoformat(task.get('timestamp', ''))
                if start_date <= task_time <= end_date:
                    filtered.append(task)
            except Exception:
                continue
        return filtered

    # ============ 统计分析 ============

    def calculate_stats(self, tasks: List[Dict]) -> Dict:
        """计算统计数据"""
        if not tasks:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "success_rate": 0,
                "avg_time": 0
            }

        total = len(tasks)
        completed = sum(1 for t in tasks if t.get('status') == 'completed')
        failed = sum(1 for t in tasks if t.get('status') == 'failed')

        # 计算技能使用
        skill_counts = defaultdict(int)
        for task in tasks:
            for skill in task.get('skills', []):
                skill_counts[skill] += 1

        top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # 失败原因分析
        failure_reasons = defaultdict(int)
        for task in tasks:
            if task.get('status') == 'failed':
                reason = task.get('error', 'Unknown')
                failure_reasons[reason] += 1

        common_failures = sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "top_skills": top_skills,
            "common_failures": common_failures,
            "skill_counts": dict(skill_counts)
        }

    def identify_patterns(self, tasks: List[Dict]) -> List[Dict]:
        """识别模式"""
        patterns = []

        # 模式1: 特定技能组合的成功率
        skill_combo_success = defaultdict(lambda: {"success": 0, "total": 0})
        for task in tasks:
            skills_key = tuple(sorted(task.get('skills', [])))
            skill_combo_success[skills_key]["total"] += 1
            if task.get('status') == 'completed':
                skill_combo_success[skills_key]["success"] += 1

        for combo, stats in skill_combo_success.items():
            if stats["total"] >= 2:  # 至少出现2次
                rate = stats["success"] / stats["total"]
                patterns.append({
                    "type": "skill_combo",
                    "description": f"{' + '.join(combo)}",
                    "success_rate": rate,
                    "sample_size": stats["total"],
                    "recommendation": "推荐使用" if rate > 0.8 else "需要优化" if rate < 0.5 else "观察中"
                })

        # 模式2: 复杂度与成功率
        complexity_stats = defaultdict(lambda: {"success": 0, "total": 0})
        for task in tasks:
            complexity = task.get('complexity', 'medium')
            complexity_stats[complexity]["total"] += 1
            if task.get('status') == 'completed':
                complexity_stats[complexity]["success"] += 1

        for complexity, stats in complexity_stats.items():
            rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            patterns.append({
                "type": "complexity",
                "description": f"{complexity}复杂度任务",
                "success_rate": rate,
                "sample_size": stats["total"],
                "recommendation": "符合预期" if 0.6 <= rate <= 0.9 else "需要关注"
            })

        return patterns

    # ============ 复盘生成 ============

    def generate_weekly_review(self) -> WeeklyReview:
        """生成周复盘报告"""
        start_date, end_date = self._get_date_range(days=7)
        tasks = self._filter_by_date(start_date, end_date)

        # 计算统计数据
        stats = self.calculate_stats(tasks)

        # 分类成功和失败任务
        successes = [t for t in tasks if t.get('status') == 'completed'][-5:]  # 最近5个
        failures = [t for t in tasks if t.get('status') == 'failed'][-5:]

        # 技能表现
        skill_performance = {}
        for skill in stats.get('skill_counts', {}).keys():
            skill_tasks = [t for t in tasks if skill in t.get('skills', [])]
            skill_completed = sum(1 for t in skill_tasks if t.get('status') == 'completed')
            skill_performance[skill] = {
                "total_uses": len(skill_tasks),
                "success_rate": skill_completed / len(skill_tasks) if skill_tasks else 0
            }

        # 识别模式
        patterns = self.identify_patterns(tasks)

        # 生成改进建议
        suggestions = []
        if stats['success_rate'] < 0.7:
            suggestions.append("任务成功率偏低，建议简化任务分解策略")
        if len(failures) > stats['total'] * 0.3:
            suggestions.append("失败率较高，需要加强错误处理机制")
        if patterns:
            low_performing = [p for p in patterns if p.get('success_rate', 1) < 0.5]
            if low_performing:
                suggestions.append(f"技能组合 {[p['description'] for p in low_performing]} 成功率较低，建议优化")

        # 下周目标
        next_week_goals = [
            "保持任务成功率在85%以上",
            "优化失败率高的技能组合",
            "总结本周经验，更新技能文档"
        ]

        # 计算周数
        week_number = end_date.isocalendar()[1]
        year = end_date.year

        review = WeeklyReview(
            week_number=week_number,
            year=year,
            period=f"{start_date.date()} 至 {end_date.date()}",
            stats=stats,
            successes=successes,
            failures=failures,
            skill_performance=skill_performance,
            top_patterns=patterns[:5],
            improvements=suggestions,
            next_week_goals=next_week_goals
        )

        return review

    def generate_monthly_review(self) -> Dict:
        """生成月复盘报告"""
        start_date, end_date = self._get_date_range(days=30)
        tasks = self._filter_by_date(start_date, end_date)
        stats = self.calculate_stats(tasks)
        patterns = self.identify_patterns(tasks)

        # 趋势分析
        weekly_breakdown = []
        for week_offset in range(4):
            week_start = end_date - timedelta(days=7*(week_offset+1))
            week_end = week_start + timedelta(days=7)
            week_tasks = self._filter_by_date(week_start, week_end)
            week_stats = self.calculate_stats(week_tasks)
            weekly_breakdown.append({
                "week": f"Week {4-week_offset}",
                "success_rate": week_stats['success_rate'],
                "total_tasks": week_stats['total']
            })

        return {
            "period": f"{start_date.date()} 至 {end_date.date()}",
            "summary": stats,
            "patterns": patterns,
            "weekly_trend": weekly_breakdown,
            "monthly_goals_achieved": stats['success_rate'] > 0.8,
            "recommendations": [
                "继续优化成功率低于80%的技能组合",
                "增加使用频率高且稳定的技能",
                "建立更完善的任务分解模板"
            ]
        }

    # ============ 自动复盘触发 ============

    def check_and_trigger_review(self) -> Optional[WeeklyReview]:
        """检查是否需要触发复盘（每周日检查）"""
        today = datetime.now()
        if today.weekday() == 6:  # 周日
            # 检查是否已做过本周复盘
            week_number = today.isocalendar()[1]
            recent_reviews = [r for r in self.reviews if r.get('week_number') == week_number]
            if not recent_reviews:
                review = self.generate_weekly_review()
                self.save_review(review)
                return review
        return None

    def save_review(self, review: WeeklyReview):
        """保存复盘报告"""
        review_dict = {
            "week_number": review.week_number,
            "year": review.year,
            "period": review.period,
            "stats": review.stats,
            "successes": review.successes,
            "failures": review.failures,
            "skill_performance": review.skill_performance,
            "patterns": review.top_patterns,
            "improvements": review.improvements,
            "next_week_goals": review.next_week_goals,
            "generated_at": datetime.now().isoformat()
        }
        self.reviews.append(review_dict)
        self._save_data()

    def get_latest_review(self) -> Optional[Dict]:
        """获取最新复盘"""
        if self.reviews:
            return self.reviews[-1]
        return None

    def get_review_history(self, limit: int = 4) -> List[Dict]:
        """获取复盘历史"""
        return self.reviews[-limit:]

# ============ 格式化输出 ============

def format_review_report(review: WeeklyReview) -> str:
    """格式化复盘报告为可读文本"""
    lines = [
        "=" * 60,
        f"📊 周复盘报告 - 第{review.week_number}周 ({review.year}年)",
        "=" * 60,
        f"📅 统计周期: {review.period}",
        "",
        "📈 核心指标:",
        f"   总任务数: {review.stats['total']}",
        f"   完成: {review.stats['completed']} | 失败: {review.stats['failed']}",
        f"   成功率: {review.stats['success_rate']*100:.1f}%",
        "",
        "🔥 常用技能:",
    ]

    for skill, count in review.stats.get('top_skills', [])[:5]:
        lines.append(f"   • {skill}: {count}次")

    if review.stats.get('common_failures'):
        lines.extend([
            "",
            "⚠️ 常见失败原因:",
        ])
        for reason, count in review.stats['common_failures'][:3]:
            lines.append(f"   • {reason}: {count}次")

    if review.top_patterns:
        lines.extend([
            "",
            "🔍 模式识别:",
        ])
        for pattern in review.top_patterns[:3]:
            lines.append(f"   • [{pattern['type']}] {pattern['description']}")
            lines.append(f"     成功率: {pattern['success_rate']*100:.1f}% - {pattern['recommendation']}")

    if review.improvements:
        lines.extend([
            "",
            "💡 改进建议:",
        ])
        for i, suggestion in enumerate(review.improvements, 1):
            lines.append(f"   {i}. {suggestion}")

    if review.next_week_goals:
        lines.extend([
            "",
            "🎯 下周目标:",
        ])
        for i, goal in enumerate(review.next_week_goals, 1):
            lines.append(f"   {i}. {goal}")

    lines.append("=" * 60)
    return "\n".join(lines)

# ============ 示例用法 ============

def demo():
    """演示复盘系统"""
    print("=" * 50)
    print("Hermes-AGI Self-Review Demo")
    print("=" * 50)

    review_system = SelfReviewSystem(memory_dir="./demo_memory")

    # 添加模拟历史数据
    import shutil
    if Path("./demo_memory").exists():
        shutil.rmtree("./demo_memory")
    Path("./demo_memory").mkdir(parents=True)

    # 模拟任务历史
    for i in range(15):
        review_system.task_history.append({
            "task_id": f"TASK-{i:03d}",
            "description": f"任务{i}描述",
            "skills": ["Backend", "Database"] if i % 3 == 0 else ["Frontend"],
            "status": "completed" if i % 5 != 0 else "failed",
            "timestamp": (datetime.now() - timedelta(days=i)).isoformat(),
            "complexity": "high" if i % 4 == 0 else "medium"
        })

    review_system._save_data()

    # 生成周报
    print("\n生成周复盘报告...")
    review = review_system.generate_weekly_review()
    report = format_review_report(review)
    print(report)

    # 检查自动触发
    print("\n检查自动复盘触发...")
    auto_review = review_system.check_and_trigger_review()
    if auto_review:
        print("已自动触发周复盘!")
    else:
        print("今天不是复盘日，跳过")

    # 清理
    if Path("./demo_memory").exists():
        shutil.rmtree("./demo_memory")

if __name__ == "__main__":
    demo()