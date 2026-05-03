"""
天问-AGI 数据管道模块 v1.0
Data Pipeline - 端到端数据分析管道

功能:
- PipelineOrchestrator: 管道编排器，协调整个数据处理流程
- DataCleaner: 数据清洗组件，处理缺失值、异常值、格式转换
- ReportGenerator: 报告生成组件，生成结构化分析报告

管道流程:
1. 数据获取 (fetch_data)
2. 数据清洗 (clean_data)
3. 数据分析 (analyze_data)
4. 报告生成 (generate_report)

Author: 天问-AGI
"""

from __future__ import annotations

import asyncio
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback

# 数值计算
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# 数据验证
try:
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# ============ 枚举和常量 ============

class PipelineStage(Enum):
    """管道阶段枚举"""
    FETCH = "fetch"
    CLEAN = "clean"
    ANALYZE = "analyze"
    REPORT = "report"


class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"    # 无缺失、无异常
    GOOD = "good"             # 少量缺失/异常，已处理
    FAIR = "fair"             # 中等质量，需要注意
    POOR = "poor"             # 需要大量清洗


class CleaningStrategy(Enum):
    """清洗策略"""
    DROP = "drop"             # 删除缺失/异常记录
    FILL = "fill"             # 填充缺失值
    INTERPOLATE = "interpolate"  # 插值填充
    FLAG = "flag"             # 标记但保留


# ============ 数据模型 ============

@dataclass
class PipelineConfig:
    """管道配置"""
    name: str = "data_pipeline"
    version: str = "1.0.0"

    # 清洗配置
    missing_threshold: float = 0.3       # 缺失率阈值，超过则删除列
    outlier_sigma: float = 3.0           # 异常值判定sigma倍数
    fill_method: str = "mean"           # 填充方法: mean, median, mode, forward, backward

    # 分析配置
    analysis_methods: List[str] = field(default_factory=lambda: ["statistical", "correlation"])
    confidence_level: float = 0.95       # 置信水平

    # 报告配置
    report_format: str = "json"         # json, markdown, html
    include_raw_data: bool = False      # 报告中是否包含原始数据摘要
    include_charts: bool = False        # 报告中是否包含图表数据


@dataclass
class DataRecord:
    """数据记录"""
    id: str
    timestamp: str
    source: str
    values: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality: DataQuality = DataQuality.GOOD
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'DataRecord':
        return DataRecord(**data)


@dataclass
class CleaningResult:
    """清洗结果"""
    cleaned_data: List[DataRecord]
    removed_count: int = 0
    filled_count: int = 0
    flagged_count: int = 0
    quality_score: float = 1.0
    issues_found: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AnalysisResult:
    """分析结果"""
    summary: Dict[str, Any]
    statistics: Dict[str, Any]
    correlations: Dict[str, Any]
    patterns: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    timestamp: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PipelineReport:
    """管道执行报告"""
    pipeline_name: str
    status: str  # success, partial, failed
    stages_completed: List[str]
    data_quality: DataQuality
    processing_time: float

    # 各阶段结果
    fetch_summary: Dict[str, Any] = field(default_factory=dict)
    clean_summary: Dict[str, Any] = field(default_factory=dict)
    analyze_summary: Dict[str, Any] = field(default_factory=dict)
    report_summary: Dict[str, Any] = field(default_factory=dict)

    # 最终产物
    cleaned_data: Optional[List[Dict]] = None
    analysis_result: Optional[Dict] = None
    report_content: Optional[str] = None

    # 错误信息
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


# ============ DataCleaner 组件 ============

class DataCleaner:
    """
    数据清洗组件

    功能:
    - 处理缺失值
    - 检测和处理异常值
    - 格式转换和标准化
    - 数据类型验证

    使用示例:
        cleaner = DataCleaner(config)
        result = await cleaner.clean(raw_data)
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._stats = {
            "total_records": 0,
            "missing_values": {},
            "outliers": {},
            "type_errors": {}
        }

    async def clean(self, data: Union[List[Dict], List[DataRecord]]) -> CleaningResult:
        """
        清洗数据

        Args:
            data: 原始数据列表

        Returns:
            CleaningResult: 包含清洗后数据和统计信息
        """
        if not data:
            return CleaningResult(cleaned_data=[], removed_count=0)

        # 转换为DataRecord格式
        records = self._normalize_records(data)
        self._stats["total_records"] = len(records)

        # Step 1: 处理缺失值
        records, missing_info = await self._handle_missing_values(records)
        self._stats["missing_values"] = missing_info

        # Step 2: 检测和处理异常值
        records, outlier_info = await self._handle_outliers(records)
        self._stats["outliers"] = outlier_info

        # Step 3: 类型验证和转换
        records, type_info = await self._validate_types(records)
        self._stats["type_errors"] = type_info

        # Step 4: 计算质量分数
        quality_score = self._calculate_quality_score(records)

        # 构建清洗结果
        result = CleaningResult(
            cleaned_data=records,
            removed_count=len(data) - len(records),
            filled_count=sum(missing_info.values()) if missing_info else 0,
            flagged_count=sum(outlier_info.values()) if outlier_info else 0,
            quality_score=quality_score,
            issues_found=self._collect_issues(missing_info, outlier_info, type_info),
            statistics={
                "missing_by_column": missing_info,
                "outliers_by_column": outlier_info,
                "type_issues_by_column": type_info,
                "total_processed": len(data),
                "final_count": len(records)
            }
        )

        return result

    def _normalize_records(self, data: Union[List[Dict], List[DataRecord]]) -> List[DataRecord]:
        """将输入数据标准化为DataRecord列表"""
        records = []
        for item in data:
            if isinstance(item, DataRecord):
                records.append(item)
            elif isinstance(item, dict):
                # 补全必要字段
                record_dict = {
                    "id": item.get("id", str(uuid.uuid4())),
                    "timestamp": item.get("timestamp", datetime.now().isoformat()),
                    "source": item.get("source", "unknown"),
                    "values": item.get("values", item),
                    "metadata": item.get("metadata", {}),
                    "quality": DataQuality.GOOD,
                    "issues": []
                }
                records.append(DataRecord(**record_dict))
        return records

    async def _handle_missing_values(
        self,
        records: List[DataRecord]
    ) -> Tuple[List[DataRecord], Dict[str, int]]:
        """
        处理缺失值

        策略:
        - 如果某列缺失率超过阈值，删除该列
        - 否则使用配置的方法填充
        """
        if not records:
            return [], {}

        # 分析每列的缺失情况
        columns = set()
        for record in records:
            columns.update(record.values.keys())

        missing_counts = {col: 0 for col in columns}
        total = len(records)

        for record in records:
            for col in columns:
                if col not in record.values or record.values[col] is None:
                    missing_counts[col] += 1

        # 计算缺失率
        missing_rates = {col: count / total for col, count in missing_counts.items()}

        # 确定需要删除的列
        columns_to_drop = [
            col for col, rate in missing_rates.items()
            if rate > self.config.missing_threshold
        ]

        # 填充其他列的缺失值
        fill_method = self.config.fill_method
        filled_counts = {}

        if fill_method == "drop":
            # 删除包含缺失值的记录
            cleaned = [
                r for r in records
                if all(r.values.get(col) is not None for col in columns if col not in columns_to_drop)
            ]
        else:
            cleaned = records.copy()
            for col in columns:
                if col in columns_to_drop:
                    continue

                if missing_counts[col] > 0:
                    # 收集非空值
                    values = [r.values.get(col) for r in cleaned if col in r.values and r.values[col] is not None]

                    if not values:
                        continue

                    # 计算填充值
                    if fill_method == "mean" and HAS_NUMPY:
                        fill_value = float(np.mean([v for v in values if isinstance(v, (int, float))]))
                    elif fill_method == "median":
                        fill_value = sorted(values)[len(values) // 2]
                    elif fill_method == "mode":
                        from collections import Counter
                        fill_value = Counter(values).most_common(1)[0][0]
                    elif fill_method == "forward":
                        fill_value = None
                        for r in cleaned:
                            if col in r.values and r.values[col] is not None:
                                fill_value = r.values[col]
                                break
                    elif fill_method == "backward":
                        fill_value = None
                        for r in reversed(cleaned):
                            if col in r.values and r.values[col] is not None:
                                fill_value = r.values[col]
                                break
                    else:
                        fill_value = values[0] if values else None

                    # 应用填充
                    if fill_method in ("forward", "backward"):
                        filled = []
                        last_val = None
                        iter_records = cleaned if fill_method == "forward" else reversed(cleaned)

                        for r in iter_records:
                            if col in r.values and r.values[col] is not None:
                                last_val = r.values[col]
                                filled.append(r)
                            else:
                                if last_val is not None:
                                    r.values[col] = last_val
                                    filled.append(r)
                                else:
                                    filled.append(r)

                        if fill_method == "forward":
                            cleaned = filled
                        else:
                            cleaned = list(reversed(filled))
                    else:
                        for r in cleaned:
                            if col not in r.values or r.values[col] is None:
                                r.values[col] = fill_value

                    filled_counts[col] = missing_counts[col]

        # 记录被删除的列信息
        for col in columns_to_drop:
            for r in cleaned:
                r.issues.append(f"column_removed:{col}")

        return cleaned, missing_counts

    async def _handle_outliers(
        self,
        records: List[DataRecord]
    ) -> Tuple[List[DataRecord], Dict[str, int]]:
        """
        检测和处理异常值

        使用sigma原则检测异常值
        """
        if not records or not HAS_NUMPY:
            return records, {}

        # 找出数值列
        numeric_columns = []
        sample_record = records[0] if records else None
        if sample_record:
            for col, val in sample_record.values.items():
                if isinstance(val, (int, float)):
                    numeric_columns.append(col)

        outlier_counts = {}
        cleaned = records.copy()

        for col in numeric_columns:
            # 收集值
            values = []
            for r in cleaned:
                if col in r.values and isinstance(r.values[col], (int, float)):
                    values.append(r.values[col])

            if len(values) < 3:
                continue

            # 计算统计量
            mean = np.mean(values)
            std = np.std(values)

            if std == 0:
                continue

            # 检测异常值
            threshold = self.config.outlier_sigma * std
            outliers = []

            for r in cleaned:
                if col in r.values and isinstance(r.values[col], (int, float)):
                    if abs(r.values[col] - mean) > threshold:
                        outliers.append(r.id)

            if outliers:
                outlier_counts[col] = len(outliers)

                # 标记或移除异常值
                for r in cleaned:
                    if r.id in outliers:
                        r.issues.append(f"outlier:{col}")
                        r.quality = DataQuality.FAIR

        return cleaned, outlier_counts

    async def _validate_types(
        self,
        records: List[DataRecord]
    ) -> Tuple[List[DataRecord], Dict[str, int]]:
        """验证和转换数据类型"""
        type_issues = {}

        for r in records:
            for col, val in r.values.items():
                # 检查类型一致性
                if val is None:
                    continue

                # 类型检查（简化版本）
                if isinstance(val, str):
                    # 尝试转换为数值
                    if col.endswith("_num") or col.endswith("_count"):
                        try:
                            r.values[col] = float(val)
                        except (ValueError, TypeError):
                            pass

        return records, type_issues

    def _calculate_quality_score(self, records: List[DataRecord]) -> float:
        """计算数据质量分数"""
        if not records:
            return 0.0

        total_issues = sum(len(r.issues) for r in records)
        max_issues = len(records) * 5  # 假设每条记录最多5个问题

        score = 1.0 - (total_issues / max_issues) if max_issues > 0 else 1.0
        return max(0.0, score)

    def _collect_issues(
        self,
        missing: Dict[str, int],
        outliers: Dict[str, int],
        types: Dict[str, int]
    ) -> List[str]:
        """收集所有发现的问题"""
        issues = []
        for col, count in missing.items():
            if count > 0:
                issues.append(f"missing:{col}={count}")
        for col, count in outliers.items():
            if count > 0:
                issues.append(f"outlier:{col}={count}")
        for col, count in types.items():
            if count > 0:
                issues.append(f"type_error:{col}={count}")
        return issues


# ============ ReportGenerator 组件 ============

class ReportGenerator:
    """
    报告生成组件

    功能:
    - 生成结构化分析报告
    - 支持多种输出格式 (JSON, Markdown, HTML)
    - 包含数据质量评估
    - 包含统计摘要和可视化数据
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

    async def generate(
        self,
        analysis_result: AnalysisResult,
        cleaning_result: Optional[CleaningResult] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PipelineReport:
        """
        生成分析报告

        Args:
            analysis_result: 数据分析结果
            cleaning_result: 数据清洗结果
            metadata: 额外元数据

        Returns:
            PipelineReport: 结构化报告
        """
        report_content = ""

        # 生成报告内容
        if self.config.report_format == "markdown":
            report_content = self._generate_markdown(analysis_result, cleaning_result, metadata)
        elif self.config.report_format == "html":
            report_content = self._generate_html(analysis_result, cleaning_result, metadata)
        else:
            report_content = self._generate_json(analysis_result, cleaning_result, metadata)

        # 构建报告摘要
        report_summary = self._build_summary(analysis_result, cleaning_result, metadata)

        # 创建最终报告
        report = PipelineReport(
            pipeline_name=self.config.name,
            status="success",
            stages_completed=["fetch", "clean", "analyze", "report"],
            data_quality=self._determine_quality(cleaning_result),
            processing_time=metadata.get("processing_time", 0) if metadata else 0,
            report_summary=report_summary,
            report_content=report_content,
            metadata=metadata or {}
        )

        return report

    def _generate_json(
        self,
        analysis: AnalysisResult,
        cleaning: Optional[CleaningResult],
        metadata: Optional[Dict]
    ) -> str:
        """生成JSON格式报告"""
        report_dict = {
            "pipeline": self.config.name,
            "version": self.config.version,
            "generated_at": datetime.now().isoformat(),
            "analysis": analysis.to_dict(),
            "cleaning": cleaning.to_dict() if cleaning else None,
            "metadata": metadata or {}
        }
        return json.dumps(report_dict, indent=2, ensure_ascii=False)

    def _generate_markdown(
        self,
        analysis: AnalysisResult,
        cleaning: Optional[CleaningResult],
        metadata: Optional[Dict]
    ) -> str:
        """生成Markdown格式报告"""
        lines = [
            f"# {self.config.name} 分析报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**版本**: {self.config.version}",
            "",
            "---",
            "",
            "## 数据质量摘要",
            ""
        ]

        if cleaning:
            lines.extend([
                f"- 原始记录数: {cleaning.statistics.get('total_processed', 'N/A')}",
                f"- 清洗后记录数: {cleaning.statistics.get('final_count', 'N/A')}",
                f"- 质量分数: {cleaning.quality_score:.2%}",
                f"- 发现问题: {len(cleaning.issues_found)} 项",
                ""
            ])

        lines.extend([
            "## 统计分析摘要",
            ""
        ])

        if analysis.statistics:
            for key, value in analysis.statistics.items():
                lines.append(f"- **{key}**: {value}")

        lines.extend([
            "",
            "## 关联分析",
            ""
        ])

        if analysis.correlations:
            lines.append("| 变量对 | 相关系数 |")
            lines.append("|--------|----------|")
            for pair, corr in list(analysis.correlations.items())[:10]:
                lines.append(f"| {pair} | {corr:.4f} |")

        lines.extend([
            "",
            "## 发现的模式",
            ""
        ])

        for i, pattern in enumerate(analysis.patterns, 1):
            lines.append(f"{i}. **{pattern.get('type', 'unknown')}**: {pattern.get('description', 'N/A')}")

        lines.extend([
            "",
            "## 异常检测",
            ""
        ])

        if analysis.anomalies:
            lines.append("| ID | 类型 | 分数 | 描述 |")
            lines.append("|----|------|------|------|")
            for anomaly in analysis.anomalies[:10]:
                lines.append(f"| {anomaly.get('id', 'N/A')} | {anomaly.get('type', 'N/A')} | {anomaly.get('score', 0):.2f} | {anomaly.get('description', 'N/A')} |")
        else:
            lines.append("*未检测到显著异常*")

        lines.extend([
            "",
            "---",
            f"*报告生成: {self.config.name}*"
        ])

        return "\n".join(lines)

    def _generate_html(
        self,
        analysis: AnalysisResult,
        cleaning: Optional[CleaningResult],
        metadata: Optional[Dict]
    ) -> str:
        """生成HTML格式报告"""
        markdown = self._generate_markdown(analysis, cleaning, metadata)

        # 简单的Markdown转HTML
        html = markdown.replace("# ", "<h1>").replace("## ", "<h2>").replace("### ", "<h3>")
        html = html.replace("</h1>", "</h1>\n").replace("</h2>", "</h2>\n").replace("</h3>", "</h3>\n")

        # 粗体和斜体
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # 列表
        html = re.sub(r"^- ", "<li>", html)
        html = re.sub(r"(</li>)\n", r"\1", html)

        # 表格
        lines = html.split("\n")
        new_lines = []
        in_table = False

        for line in lines:
            if line.startswith("|"):
                if not in_table:
                    new_lines.append("<table>")
                    in_table = True
                new_lines.append(line.replace("|", "<td>").replace("-", "") + "</td>")
            else:
                if in_table:
                    new_lines.append("</table>")
                    in_table = False
                new_lines.append(line)

        if in_table:
            new_lines.append("</table>")

        html = "\n".join(new_lines)
        html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{self.config.name}</title></head><body>{html}</body></html>"

        return html

    def _build_summary(
        self,
        analysis: AnalysisResult,
        cleaning: Optional[CleaningResult],
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """构建报告摘要"""
        summary = {
            "total_records": cleaning.statistics.get("final_count", 0) if cleaning else 0,
            "quality_score": cleaning.quality_score if cleaning else 1.0,
            "patterns_found": len(analysis.patterns),
            "anomalies_found": len(analysis.anomalies),
            "correlations_analyzed": len(analysis.correlations) if analysis.correlations else 0
        }

        if analysis.statistics:
            summary["key_metrics"] = list(analysis.statistics.keys())[:5]

        return summary

    def _determine_quality(self, cleaning: Optional[CleaningResult]) -> DataQuality:
        """确定数据质量等级"""
        if not cleaning:
            return DataQuality.GOOD

        score = cleaning.quality_score

        if score >= 0.95:
            return DataQuality.EXCELLENT
        elif score >= 0.80:
            return DataQuality.GOOD
        elif score >= 0.60:
            return DataQuality.FAIR
        else:
            return DataQuality.POOR


# ============ PipelineOrchestrator 组件 ============

class PipelineOrchestrator:
    """
    端到端数据管道编排器

    协调整个数据分析流程:
    1. 数据获取 (fetch_data)
    2. 数据清洗 (clean_data)
    3. 数据分析 (analyze_data)
    4. 报告生成 (generate_report)

    使用示例:
        orchestrator = PipelineOrchestrator(config)
        result = await orchestrator.run_pipeline(input_data)
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.cleaner = DataCleaner(self.config)
        self.reporter = ReportGenerator(self.config)
        self._stage_handlers = {}

    async def run_pipeline(self, input_data: Any) -> PipelineReport:
        """
        执行完整的数据管道

        Args:
            input_data: 输入数据，可以是:
                - Dict: 单条数据记录
                - List[Dict]: 数据记录列表
                - str: 数据源标识符
                - 文件路径

        Returns:
            PipelineReport: 包含所有阶段结果的报告
        """
        start_time = datetime.now()
        report = PipelineReport(
            pipeline_name=self.config.name,
            status="running",
            stages_completed=[],
            data_quality=DataQuality.GOOD,
            processing_time=0
        )

        try:
            # Stage 1: 数据获取
            raw_data = await self.fetch_data(input_data)
            report.stages_completed.append(PipelineStage.FETCH.value)
            report.fetch_summary = self._summarize_data(raw_data)

            if not raw_data:
                raise ValueError("No data fetched from input")

            # Stage 2: 数据清洗
            cleaning_result = await self.clean_data(raw_data)
            report.stages_completed.append(PipelineStage.CLEAN.value)
            report.clean_summary = cleaning_result.to_dict()

            if not cleaning_result.cleaned_data:
                raise ValueError("All data filtered during cleaning")

            # Stage 3: 数据分析
            analysis_result = await self.analyze_data(cleaning_result.cleaned_data)
            report.stages_completed.append(PipelineStage.ANALYZE.value)
            report.analyze_summary = analysis_result.to_dict()

            # Stage 4: 报告生成
            pipeline_report = await self.generate_report(analysis_result, cleaning_result)
            report.stages_completed.append(PipelineStage.REPORT.value)
            report.report_summary = pipeline_report.report_summary
            report.report_content = pipeline_report.report_content

            # 最终状态
            report.status = "success"
            report.cleaned_data = [r.to_dict() for r in cleaning_result.cleaned_data]
            report.analysis_result = analysis_result.to_dict()

        except Exception as e:
            report.status = "failed"
            report.errors.append(f"{type(e).__name__}: {str(e)}")
            report.warnings.append(traceback.format_exc())

        finally:
            end_time = datetime.now()
            report.processing_time = (end_time - start_time).total_seconds()
            report.data_quality = self._estimate_quality(report)

        return report

    async def fetch_data(self, input_data: Any) -> List[Dict]:
        """
        获取数据

        支持多种输入格式:
        - Dict/List: 直接返回
        - str: 尝试作为文件路径读取
        - 数据源标识符: 从配置的数据源获取

        Args:
            input_data: 输入数据

        Returns:
            List[Dict]: 数据记录列表
        """
        # 如果已经是列表或字典，直接返回
        if isinstance(input_data, list):
            return input_data if input_data else []
        elif isinstance(input_data, dict):
            return [input_data]

        # 如果是字符串，尝试作为文件路径
        if isinstance(input_data, str):
            return await self._fetch_from_file(input_data)

        # 其他类型返回空
        return []

    async def _fetch_from_file(self, file_path: str) -> List[Dict]:
        """从文件读取数据"""
        try:
            path = file_path
            with open(path, 'r', encoding='utf-8') as f:
                if path.endswith('.json'):
                    data = json.load(f)
                    return data if isinstance(data, list) else [data]
                elif path.endswith('.csv'):
                    # 简单的CSV解析
                    lines = f.readlines()
                    if not lines:
                        return []

                    headers = lines[0].strip().split(',')
                    records = []
                    for line in lines[1:]:
                        values = line.strip().split(',')
                        record = {headers[i]: values[i] for i in range(min(len(headers), len(values)))}
                        records.append(record)
                    return records
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

        return []

    async def clean_data(self, raw_data: List[Dict]) -> CleaningResult:
        """
        清洗数据

        委托给DataCleaner组件
        """
        return await self.cleaner.clean(raw_data)

    async def analyze_data(self, clean_data: List[DataRecord]) -> AnalysisResult:
        """
        分析数据

        执行统计分析、关联分析、模式发现等
        """
        # 提取数值数据
        numeric_data = {}
        all_keys = set()

        for record in clean_data:
            all_keys.update(record.values.keys())

        for key in all_keys:
            values = []
            for record in clean_data:
                if key in record.values and isinstance(record.values[key], (int, float)):
                    values.append(record.values[key])

            if values:
                numeric_data[key] = values

        # 计算统计量
        statistics = {}
        for key, values in numeric_data.items():
            if HAS_NUMPY and len(values) > 0:
                statistics[key] = {
                    "mean": float(np.mean(values)),
                    "median": float(np.median(values)),
                    "std": float(np.std(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "count": len(values)
                }

        # 计算相关性
        correlations = {}
        keys = list(numeric_data.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                if HAS_NUMPY:
                    corr = np.corrcoef(numeric_data[keys[i]], numeric_data[keys[j]])[0, 1]
                    if not np.isnan(corr):
                        correlations[f"{keys[i]}__{keys[j]}"] = float(corr)

        # 简单的模式检测
        patterns = []
        anomalies = []

        # 检测周期性模式（如果有足够的数据点）
        for key, values in numeric_data.items():
            if len(values) >= 10:
                # 检查是否存在异常值
                if HAS_NUMPY:
                    mean = np.mean(values)
                    std = np.std(values)
                    for i, v in enumerate(values):
                        if abs(v - mean) > 2 * std:
                            anomalies.append({
                                "id": f"anomaly_{key}_{i}",
                                "type": "statistical",
                                "score": abs(v - mean) / std if std > 0 else 0,
                                "description": f"{key}的值{v:.2f}偏离均值{mean:.2f}超过2σ",
                                "feature": key,
                                "value": v
                            })

        # 检测趋势模式
        for key, values in numeric_data.items():
            if len(values) >= 5:
                if HAS_NUMPY:
                    # 简单线性趋势检测
                    x = np.arange(len(values))
                    slope = np.polyfit(x, values, 1)[0]

                    if abs(slope) > 0.1 * np.mean(values):
                        patterns.append({
                            "type": "trend",
                            "description": f"{key}呈现{'上升' if slope > 0 else '下降'}趋势",
                            "significance": min(1.0, abs(slope) / np.mean(values)),
                            "slope": float(slope)
                        })

        return AnalysisResult(
            summary={
                "total_records": len(clean_data),
                "numeric_features": len(numeric_data),
                "patterns_found": len(patterns),
                "anomalies_found": len(anomalies)
            },
            statistics=statistics,
            correlations=correlations,
            patterns=patterns,
            anomalies=anomalies,
            timestamp=datetime.now().isoformat()
        )

    async def generate_report(
        self,
        analysis_result: AnalysisResult,
        cleaning_result: Optional[CleaningResult] = None
    ) -> PipelineReport:
        """
        生成报告

        委托给ReportGenerator组件
        """
        return await self.reporter.generate(
            analysis_result,
            cleaning_result,
            metadata={"processing_time": self.config.outlier_sigma}  # 复用字段存储时间
        )

    def _summarize_data(self, data: List) -> Dict[str, Any]:
        """生成数据摘要"""
        return {
            "record_count": len(data),
            "first_record": data[0] if data else None,
            "keys": list(data[0].keys()) if data and isinstance(data[0], dict) else []
        }

    def _estimate_quality(self, report: PipelineReport) -> DataQuality:
        """估计数据质量"""
        if report.status == "failed":
            return DataQuality.POOR

        if not report.clean_summary:
            return DataQuality.FAIR

        cleaning_result = report.clean_summary
        quality_score = cleaning_result.get("quality_score", 0.5)

        if quality_score >= 0.95:
            return DataQuality.EXCELLENT
        elif quality_score >= 0.80:
            return DataQuality.GOOD
        elif quality_score >= 0.60:
            return DataQuality.FAIR
        else:
            return DataQuality.POOR


# ============ 便捷函数 ============

async def run_data_pipeline(
    input_data: Any,
    config: Optional[PipelineConfig] = None
) -> PipelineReport:
    """
    运行数据管道的便捷函数

    Args:
        input_data: 输入数据
        config: 管道配置

    Returns:
        PipelineReport: 执行报告
    """
    orchestrator = PipelineOrchestrator(config)
    return await orchestrator.run_pipeline(input_data)


# ============ 测试代码 ============

async def test_pipeline():
    """测试管道执行"""
    print("=" * 60)
    print("数据管道测试")
    print("=" * 60)

    # 创建测试数据
    test_data = []
    for i in range(100):
        record = {
            "id": f"record_{i}",
            "timestamp": datetime.now().isoformat(),
            "source": "test_sensor",
            "values": {
                "temperature": np.random.normal(25, 2) if HAS_NUMPY else 25,
                "humidity": np.random.normal(60, 5) if HAS_NUMPY else 60,
                "pressure": np.random.normal(1013, 10) if HAS_NUMPY else 1013,
                "reading": i * 10 + np.random.normal(0, 5) if HAS_NUMPY else i * 10
            }
        }
        # 添加一些缺失值和异常值
        if i % 20 == 0:
            record["values"]["temperature"] = None
        if i == 50:
            record["values"]["humidity"] = 200  # 异常值
        test_data.append(record)

    print(f"生成测试数据: {len(test_data)} 条记录")

    # 创建管道配置
    config = PipelineConfig(
        name="test_pipeline",
        version="1.0.0",
        missing_threshold=0.3,
        outlier_sigma=3.0,
        fill_method="mean",
        report_format="markdown"
    )

    # 运行管道
    orchestrator = PipelineOrchestrator(config)
    report = await orchestrator.run_pipeline(test_data)

    # 输出结果
    print("\n" + "=" * 60)
    print("管道执行结果")
    print("=" * 60)
    print(f"状态: {report.status}")
    print(f"完成阶段: {report.stages_completed}")
    print(f"处理时间: {report.processing_time:.3f}秒")
    print(f"数据质量: {report.data_quality.value}")
    print(f"清洗后记录数: {len(report.cleaned_data) if report.cleaned_data else 0}")

    print("\n报告内容:")
    print("-" * 40)
    if report.report_content:
        print(report.report_content[:1000])

    return report


async def test_with_missing_data():
    """测试缺失数据处理"""
    print("\n" + "=" * 60)
    print("测试缺失数据处理")
    print("=" * 60)

    # 创建包含大量缺失值的数据
    test_data = []
    for i in range(50):
        record = {
            "id": f"record_{i}",
            "timestamp": datetime.now().isoformat(),
            "source": "sensor_a",
            "values": {
                "value_a": np.random.normal(100, 10) if HAS_NUMPY else 100,
                "value_b": np.random.normal(50, 5) if HAS_NUMPY else 50,
                "value_c": None if i % 5 == 0 else (np.random.normal(75, 8) if HAS_NUMPY else 75)
            }
        }
        test_data.append(record)

    config = PipelineConfig(fill_method="mean", missing_threshold=0.5)
    cleaner = DataCleaner(config)
    result = await cleaner.clean(test_data)

    print(f"原始记录: {len(test_data)}")
    print(f"清洗后: {len(result.cleaned_data)}")
    print(f"质量分数: {result.quality_score:.2%}")
    print(f"发现的问题: {result.issues_found}")

    return result


if __name__ == "__main__":
    print("天问-AGI 数据管道模块")
    print("=" * 60)

    # 运行测试
    asyncio.run(test_pipeline())
    asyncio.run(test_with_missing_data())

    print("\n测试完成!")