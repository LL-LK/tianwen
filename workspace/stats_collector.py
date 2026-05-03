#!/usr/bin/env python3
"""
文献-观测-数据挖掘-指导观测 闭环流程统计追踪系统
Statistics Collector for Literature-Observation-Data Mining-Observation Guidance Loop
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from enum import Enum


class ProcessStage(Enum):
    """流程阶段枚举"""
    RESOURCE_COLLECTION = "resource_collection"      # 资源搜集
    RESOURCE_INTEGRATION = "resource_integration"    # 资源整合
    ISSUE_PUBLISHING = "issue_publishing"             # Issue发布
    DOCUMENT_GENERATION = "document_generation"       # 文档生成


@dataclass
class ResourceStats:
    """资源搜集统计"""
    search_count: int = 0                    # 搜索次数
    result_count: int = 0                   # 结果总数
    selected_count: int = 0                  # 筛选后数量
    selection_rate: float = 0.0              # 筛选率 (selected/result)

    def calculate_selection_rate(self):
        if self.result_count > 0:
            self.selection_rate = self.selected_count / self.result_count
        return self.selection_rate


@dataclass
class IntegrationStats:
    """资源整合统计"""
    file_count: int = 0                      # 文件数
    commit_count: int = 0                    # 提交次数
    metadata_completeness: float = 0.0       # 元数据完整度 (0-1)

    def calculate_metadata_score(self, total_fields: int, filled_fields: int) -> float:
        if total_fields > 0:
            self.metadata_completeness = filled_fields / total_fields
        return self.metadata_completeness


@dataclass
class IssueStats:
    """Issue发布统计"""
    related_issue_count: int = 0             # 相关Issue数
    new_issue_count: int = 0                 # 新建Issue数
    response_time_hours: float = 0.0         # 平均响应时间(小时)

    def calculate_response_time(self, responses: List[Dict]) -> float:
        if not responses:
            return 0.0
        total_hours = sum(r.get('response_hours', 0) for r in responses)
        self.response_time_hours = total_hours / len(responses)
        return self.response_time_hours


@dataclass
class DocumentStats:
    """文档生成统计"""
    analysis_doc_count: int = 0              # 分析文档数
    tech_route_coverage: float = 0.0          # 技术路线覆盖度 (0-1)
    document_types: List[str] = field(default_factory=list)  # 文档类型列表

    def calculate_coverage(self, covered_routes: int, total_routes: int) -> float:
        if total_routes > 0:
            self.tech_route_coverage = covered_routes / total_routes
        return self.tech_route_coverage


@dataclass
class ProcessStats:
    """流程统计"""
    stage: str = ""                           # 当前阶段
    start_time: Optional[str] = None         # 开始时间
    end_time: Optional[str] = None            # 结束时间
    duration_minutes: float = 0.0             # 持续时间(分钟)
    status: str = "pending"                  # 状态: pending/running/completed/failed
    resources: Dict = field(default_factory=dict)  # 资源使用

    def calculate_duration(self) -> float:
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration_minutes = (end - start).total_seconds() / 60
        return self.duration_minutes


@dataclass
class QualityMetrics:
    """质量指标"""
    accuracy: float = 0.0                     # 准确率
    recall: float = 0.0                       # 召回率
    f1_score: float = 0.0                    # F1分数
    completeness: float = 0.0                 # 完整性
    timeliness: float = 0.0                   # 时效性

    def calculate_f1(self) -> float:
        if self.accuracy + self.recall > 0:
            self.f1_score = 2 * (self.accuracy * self.recall) / (self.accuracy + self.recall)
        return self.f1_score


@dataclass
class LoopStats:
    """完整闭环统计"""
    loop_id: str = ""                         # 闭环ID
    loop_name: str = ""                       # 闭环名称
    created_at: str = ""                      # 创建时间

    # 子模块统计
    resource_stats: Dict = field(default_factory=dict)
    integration_stats: Dict = field(default_factory=dict)
    issue_stats: Dict = field(default_factory=dict)
    document_stats: Dict = field(default_factory=dict)

    # 整体质量
    quality_metrics: Dict = field(default_factory=dict)

    # 元数据
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        result = asdict(self)
        return {k: v for k, v in result.items() if v}


class StatsCollector:
    """统计收集器主类"""

    def __init__(self, workspace_path: str = "F:/tianwen-agi/workspace"):
        self.workspace_path = workspace_path
        self.stats_data: Dict[str, LoopStats] = {}
        self.current_loop: Optional[LoopStats] = None

    def create_loop(self, loop_id: str, loop_name: str) -> LoopStats:
        """创建新的闭环统计"""
        loop = LoopStats(
            loop_id=loop_id,
            loop_name=loop_name,
            created_at=datetime.now().isoformat()
        )
        self.stats_data[loop_id] = loop
        self.current_loop = loop
        return loop

    def update_resource_stats(self, loop_id: str,
                             search_count: int = 0,
                             result_count: int = 0,
                             selected_count: int = 0) -> ResourceStats:
        """更新资源搜集统计"""
        stats = ResourceStats(
            search_count=search_count,
            result_count=result_count,
            selected_count=selected_count
        )
        stats.calculate_selection_rate()

        if loop_id in self.stats_data:
            self.stats_data[loop_id].resource_stats = asdict(stats)

        return stats

    def update_integration_stats(self, loop_id: str,
                                file_count: int = 0,
                                commit_count: int = 0,
                                metadata_completeness: float = 0.0) -> IntegrationStats:
        """更新资源整合统计"""
        stats = IntegrationStats(
            file_count=file_count,
            commit_count=commit_count,
            metadata_completeness=metadata_completeness
        )

        if loop_id in self.stats_data:
            self.stats_data[loop_id].integration_stats = asdict(stats)

        return stats

    def update_issue_stats(self, loop_id: str,
                          related_issue_count: int = 0,
                          new_issue_count: int = 0,
                          response_time_hours: float = 0.0) -> IssueStats:
        """更新Issue发布统计"""
        stats = IssueStats(
            related_issue_count=related_issue_count,
            new_issue_count=new_issue_count,
            response_time_hours=response_time_hours
        )

        if loop_id in self.stats_data:
            self.stats_data[loop_id].issue_stats = asdict(stats)

        return stats

    def update_document_stats(self, loop_id: str,
                              analysis_doc_count: int = 0,
                              tech_route_coverage: float = 0.0,
                              document_types: List[str] = None) -> DocumentStats:
        """更新文档生成统计"""
        if document_types is None:
            document_types = []

        stats = DocumentStats(
            analysis_doc_count=analysis_doc_count,
            tech_route_coverage=tech_route_coverage,
            document_types=document_types
        )

        if loop_id in self.stats_data:
            self.stats_data[loop_id].document_stats = asdict(stats)

        return stats

    def update_quality_metrics(self, loop_id: str,
                              accuracy: float = 0.0,
                              recall: float = 0.0,
                              completeness: float = 0.0,
                              timeliness: float = 0.0) -> QualityMetrics:
        """更新质量指标"""
        metrics = QualityMetrics(
            accuracy=accuracy,
            recall=recall,
            completeness=completeness,
            timeliness=timeliness
        )
        metrics.calculate_f1()

        if loop_id in self.stats_data:
            self.stats_data[loop_id].quality_metrics = asdict(metrics)

        return metrics

    def add_metadata(self, loop_id: str, key: str, value: any):
        """添加元数据"""
        if loop_id in self.stats_data:
            self.stats_data[loop_id].metadata[key] = value

    def generate_json_report(self, loop_id: str = None) -> str:
        """生成JSON格式报告"""
        if loop_id:
            data = self.stats_data.get(loop_id)
            if data:
                return json.dumps(data.to_dict(), indent=2, ensure_ascii=False)
            return "{}"

        # 返回所有闭环统计
        all_stats = {k: v.to_dict() for k, v in self.stats_data.items()}
        return json.dumps(all_stats, indent=2, ensure_ascii=False)

    def generate_markdown_report(self, loop_id: str = None) -> str:
        """生成Markdown格式报告"""
        lines = ["# 文献-观测-数据挖掘-指导观测 闭环统计报告\n"]
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        if loop_id:
            stats = self.stats_data.get(loop_id)
            if not stats:
                return "未找到指定闭环统计"

            lines.append(self._format_single_loop_markdown(stats))
        else:
            lines.append("## 全部闭环统计\n")
            for lid, stats in self.stats_data.items():
                lines.append(f"### 闭环: {stats.loop_name} ({lid})\n")
                lines.append(self._format_single_loop_markdown(stats))
                lines.append("---\n")

        return "\n".join(lines)

    def _format_single_loop_markdown(self, stats: LoopStats) -> str:
        """格式化单个闭环的Markdown报告"""
        lines = []

        lines.append(f"**闭环ID**: {stats.loop_id}")
        lines.append(f"**闭环名称**: {stats.loop_name}")
        lines.append(f"**创建时间**: {stats.created_at}\n")

        # 资源搜集统计
        if stats.resource_stats:
            lines.append("## 资源搜集统计")
            r = stats.resource_stats
            lines.append(f"- 搜索次数: {r.get('search_count', 0)}")
            lines.append(f"- 结果总数: {r.get('result_count', 0)}")
            lines.append(f"- 筛选后数量: {r.get('selected_count', 0)}")
            lines.append(f"- 筛选率: {r.get('selection_rate', 0):.2%}\n")

        # 资源整合统计
        if stats.integration_stats:
            lines.append("## 资源整合统计")
            i = stats.integration_stats
            lines.append(f"- 文件数: {i.get('file_count', 0)}")
            lines.append(f"- 提交次数: {i.get('commit_count', 0)}")
            lines.append(f"- 元数据完整度: {i.get('metadata_completeness', 0):.2%}\n")

        # Issue发布统计
        if stats.issue_stats:
            lines.append("## Issue发布统计")
            iss = stats.issue_stats
            lines.append(f"- 相关Issue数: {iss.get('related_issue_count', 0)}")
            lines.append(f"- 新建Issue数: {iss.get('new_issue_count', 0)}")
            lines.append(f"- 平均响应时间: {iss.get('response_time_hours', 0):.1f} 小时\n")

        # 文档生成统计
        if stats.document_stats:
            lines.append("## 文档生成统计")
            d = stats.document_stats
            lines.append(f"- 分析文档数: {d.get('analysis_doc_count', 0)}")
            lines.append(f"- 技术路线覆盖度: {d.get('tech_route_coverage', 0):.2%}")
            lines.append(f"- 文档类型: {', '.join(d.get('document_types', []))}\n")

        # 质量指标
        if stats.quality_metrics:
            lines.append("## 质量指标")
            q = stats.quality_metrics
            lines.append(f"- 准确率: {q.get('accuracy', 0):.2%}")
            lines.append(f"- 召回率: {q.get('recall', 0):.2%}")
            lines.append(f"- F1分数: {q.get('f1_score', 0):.2%}")
            lines.append(f"- 完整性: {q.get('completeness', 0):.2%}")
            lines.append(f"- 时效性: {q.get('timeliness', 0):.2%}\n")

        return "\n".join(lines)

    def save_json_report(self, filepath: str = None, loop_id: str = None):
        """保存JSON报告到文件"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.workspace_path, f"stats_report_{timestamp}.json")

        content = self.generate_json_report(loop_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def save_markdown_report(self, filepath: str = None, loop_id: str = None):
        """保存Markdown报告到文件"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.workspace_path, f"stats_report_{timestamp}.md")

        content = self.generate_markdown_report(loop_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def load_stats(self, filepath: str) -> bool:
        """从文件加载统计"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for loop_id, loop_data in data.items():
                stats = LoopStats(**loop_data)
                self.stats_data[loop_id] = stats

            return True
        except Exception as e:
            print(f"加载失败: {e}")
            return False

    def get_summary(self) -> Dict:
        """获取统计摘要"""
        total_loops = len(self.stats_data)

        summary = {
            "total_loops": total_loops,
            "total_searches": 0,
            "total_results": 0,
            "total_selected": 0,
            "total_files": 0,
            "total_commits": 0,
            "total_issues": 0,
            "total_documents": 0,
            "avg_selection_rate": 0.0,
            "avg_metadata_completeness": 0.0
        }

        if total_loops > 0:
            for stats in self.stats_data.values():
                if stats.resource_stats:
                    summary["total_searches"] += stats.resource_stats.get('search_count', 0)
                    summary["total_results"] += stats.resource_stats.get('result_count', 0)
                    summary["total_selected"] += stats.resource_stats.get('selected_count', 0)

                if stats.integration_stats:
                    summary["total_files"] += stats.integration_stats.get('file_count', 0)
                    summary["total_commits"] += stats.integration_stats.get('commit_count', 0)

                if stats.issue_stats:
                    summary["total_issues"] += stats.issue_stats.get('new_issue_count', 0)

                if stats.document_stats:
                    summary["total_documents"] += stats.document_stats.get('analysis_doc_count', 0)

            if summary["total_results"] > 0:
                summary["avg_selection_rate"] = summary["total_selected"] / summary["total_results"]

            total_completeness = sum(
                s.integration_stats.get('metadata_completeness', 0)
                for s in self.stats_data.values()
            )
            summary["avg_metadata_completeness"] = total_completeness / total_loops

        return summary


def demo():
    """演示统计收集器用法"""
    collector = StatsCollector()

    # 创建闭环统计
    loop1 = collector.create_loop("loop_001", "系外行星文献调研")

    # 更新资源搜集统计
    collector.update_resource_stats(
        loop_id="loop_001",
        search_count=10,
        result_count=500,
        selected_count=50
    )

    # 更新资源整合统计
    collector.update_integration_stats(
        loop_id="loop_001",
        file_count=25,
        commit_count=8,
        metadata_completeness=0.85
    )

    # 更新Issue统计
    collector.update_issue_stats(
        loop_id="loop_001",
        related_issue_count=5,
        new_issue_count=2,
        response_time_hours=4.5
    )

    # 更新文档统计
    collector.update_document_stats(
        loop_id="loop_001",
        analysis_doc_count=3,
        tech_route_coverage=0.75,
        document_types=["调研报告", "技术路线图", "观测计划"]
    )

    # 更新质量指标
    collector.update_quality_metrics(
        loop_id="loop_001",
        accuracy=0.92,
        recall=0.88,
        completeness=0.90,
        timeliness=0.95
    )

    # 添加自定义元数据
    collector.add_metadata("loop_001", "researcher", "天问-AGI")
    collector.add_metadata("loop_001", "domain", "系外行星探测")

    # 生成报告
    print("=== JSON报告 ===")
    print(collector.generate_json_report("loop_001"))

    print("\n=== Markdown报告 ===")
    print(collector.generate_markdown_report("loop_001"))

    # 保存报告
    json_path = collector.save_json_report()
    md_path = collector.save_markdown_report()
    print(f"\n报告已保存至:\n  JSON: {json_path}\n  MD: {md_path}")

    # 打印摘要
    print("\n=== 统计摘要 ===")
    summary = collector.get_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    demo()