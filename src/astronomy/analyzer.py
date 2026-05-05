"""
天问-AGI 天文数据分析模块
AstroAnalyzer - 自动处理、分析和可视化天文数据
"""

import asyncio
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

# ============ 分析数据类型 ============

@dataclass
class TimeSeriesData:
    """时间序列数据"""
    timestamps: List[str]
    values: List[float]
    label: str
    unit: str

@dataclass
class StatisticalSummary:
    """统计摘要"""
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    count: int
    trend: str  # increasing, decreasing, stable, fluctuating

@dataclass
class AnomalyDetection:
    """异常检测结果"""
    is_anomaly: bool
    score: float  # 0-1，越高越异常
    timestamp: str
    value: float
    expected_value: float
    deviation: float
    reason: str

@dataclass
class TrendAnalysis:
    """趋势分析"""
    direction: str  # up, down, stable
    slope: float  # 变化率
    confidence: float  # 0-1
    forecast: List[float]  # 预测值
    changepoints: List[str]  # 转折点

# ============ 天文数据分析器 ============

class AstroAnalyzer:
    """天文数据分析器"""

    def __init__(self):
        self.data_cache: Dict[str, Any] = {}

    # ============ 基础统计分析 ============

    def calculate_statistics(self, values: List[float], label: str = "", unit: str = "") -> StatisticalSummary:
        """计算基础统计"""
        if not values:
            return StatisticalSummary(0, 0, 0, 0, 0, 0, "stable")

        mean_val = statistics.mean(values)
        median_val = statistics.median(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0

        # 判断趋势
        if len(values) >= 3:
            first_third = statistics.mean(values[:len(values)//3])
            last_third = statistics.mean(values[-len(values)//3:])
            diff_pct = (last_third - first_third) / (first_third + 0.001) * 100

            if diff_pct > 10:
                trend = "increasing"
            elif diff_pct < -10:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "fluctuating"

        return StatisticalSummary(
            mean=round(mean_val, 4),
            median=round(median_val, 4),
            std_dev=round(std_val, 4),
            min=round(min(values), 4),
            max=round(max(values), 4),
            count=len(values),
            trend=trend
        )

    def detect_anomalies(self, values: List[float], timestamps: List[str],
                          method: str = "iqr") -> List[AnomalyDetection]:
        """检测异常值"""
        anomalies = []

        if len(values) < 4:
            return anomalies

        if method == "iqr":
            # 四分位距法
            sorted_vals = sorted(values)
            q1_idx = len(sorted_vals) // 4
            q3_idx = 3 * len(sorted_vals) // 4
            q1 = sorted_vals[q1_idx]
            q3 = sorted_vals[q3_idx]
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            expected = statistics.mean(values)

            for i, val in enumerate(values):
                if val < lower_bound or val > upper_bound:
                    deviation = abs(val - expected) / (std_val if (std_val := statistics.stdev(values)) > 0 else 1)
                    anomalies.append(AnomalyDetection(
                        is_anomaly=True,
                        score=min(1.0, deviation / 3),
                        timestamp=timestamps[i],
                        value=val,
                        expected_value=expected,
                        deviation=deviation,
                        reason=f"超出正常范围 [{lower_bound:.2f}, {upper_bound:.2f}]"
                    ))

        elif method == "zscore":
            # Z分数法
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values)

            if std_val > 0:
                for i, val in enumerate(values):
                    z_score = abs((val - mean_val) / std_val)
                    if z_score > 2.5:
                        anomalies.append(AnomalyDetection(
                            is_anomaly=True,
                            score=min(1.0, (z_score - 2.5) / 2),
                            timestamp=timestamps[i],
                            value=val,
                            expected_value=mean_val,
                            deviation=z_score,
                            reason=f"Z分数 {z_score:.2f} 超过阈值2.5"
                        ))

        return anomalies

    def analyze_trend(self, values: List[float], forecast_periods: int = 3) -> TrendAnalysis:
        """分析数据趋势"""
        if len(values) < 2:
            return TrendAnalysis("stable", 0, 0, [], [])

        # 简单线性回归
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # 计算置信度（基于R²）
        ss_res = sum((values[i] - (y_mean + slope * (x[i] - x_mean))) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 判断方向
        if abs(slope) < 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "up"
        else:
            direction = "down"

        # 预测
        forecast = []
        last_value = values[-1]
        for i in range(forecast_periods):
            predicted = last_value + slope * (i + 1)
            forecast.append(round(predicted, 4))

        # 查找转折点（简化版）
        changepoints = []
        for i in range(1, n - 1):
            if (values[i] > values[i-1] and values[i] > values[i+1]) or \
               (values[i] < values[i-1] and values[i] < values[i+1]):
                changepoints.append(i)

        return TrendAnalysis(
            direction=direction,
            slope=round(slope, 6),
            confidence=round(r_squared, 4),
            forecast=forecast,
            changepoints=changepoints[:5]  # 最多5个
        )

    # ============ 天文专用分析 ============

    def analyze_star_brightness(self, magnitude_data: List[float],
                                 timestamps: List[str]) -> Dict:
        """分析恒星亮度变化"""
        stats = self.calculate_statistics(magnitude_data, "视星等", "mag")
        anomalies = self.detect_anomalies(magnitude_data, timestamps)
        trend = self.analyze_trend(magnitude_data)

        # 亮度变化分析
        if len(magnitude_data) >= 2:
            max_change = max(abs(magnitude_data[i] - magnitude_data[i-1])
                            for i in range(1, len(magnitude_data)))
        else:
            max_change = 0

        # 判断是否可能是变星
        is_variable = stats.std_dev > 0.1 or len(anomalies) > 0

        return {
            "statistics": {
                "mean_magnitude": stats.mean,
                "median_magnitude": stats.median,
                "variation_range": stats.max - stats.min,
                "standard_deviation": stats.std_dev,
                "trend": stats.trend
            },
            "variable_star_analysis": {
                "is_variable_star": is_variable,
                "max_single_change": round(max_change, 3),
                "anomaly_count": len(anomalies)
            },
            "trend": {
                "direction": trend.direction,
                "slope": trend.slope,
                "confidence": trend.confidence,
                "forecast": trend.forecast
            },
            "anomalies": [
                {
                    "timestamp": a.timestamp,
                    "value": a.value,
                    "score": a.score,
                    "reason": a.reason
                }
                for a in anomalies[:5]
            ]
        }

    def analyze_observation_quality(self, seeing_data: List[float],
                                     cloud_cover_data: List[int],
                                     timestamps: List[str]) -> Dict:
        """分析观测质量"""
        seeing_stats = self.calculate_statistics(seeing_data, "视宁度", "arcsec")
        cloud_stats = self.calculate_statistics(
            [float(x) for x in cloud_cover_data], "云量", "%"
        )

        # 计算综合观测评分
        quality_scores = []
        for seeing, cloud in zip(seeing_data, cloud_cover_data):
            # 视宁度评分 (1=100分, 5=0分)
            seeing_score = max(0, 100 - (seeing - 1) * 25)
            # 云量评分
            cloud_score = max(0, 100 - cloud)
            # 综合评分
            combined = seeing_score * 0.6 + cloud_score * 0.4
            quality_scores.append(combined)

        overall_quality = statistics.mean(quality_scores) if quality_scores else 0

        # 质量等级
        if overall_quality >= 80:
            quality_level = "excellent"
        elif overall_quality >= 60:
            quality_level = "good"
        elif overall_quality >= 40:
            quality_level = "fair"
        else:
            quality_level = "poor"

        return {
            "overall_quality_score": round(overall_quality, 1),
            "quality_level": quality_level,
            "seeing": {
                "mean": seeing_stats.mean,
                "median": seeing_stats.median,
                "best": seeing_stats.min,
                "worst": seeing_stats.max,
                "trend": seeing_stats.trend
            },
            "cloud_cover": {
                "mean": cloud_stats.mean,
                "median": cloud_stats.median,
                "clearest": cloud_stats.min,
                "cloudiest": cloud_stats.max,
                "trend": cloud_stats.trend
            },
            "recommendation": self._get_observation_recommendation(overall_quality, seeing_stats, cloud_stats)
        }

    def _get_observation_recommendation(self, quality: float,
                                          seeing: StatisticalSummary,
                                          cloud: StatisticalSummary) -> str:
        """获取观测建议"""
        recommendations = []

        if quality >= 80:
            recommendations.append("今晚观测条件极佳，适合进行高分辨率摄影")
        elif quality >= 60:
            recommendations.append("观测条件良好，可以进行常规观测")
        elif quality >= 40:
            recommendations.append("观测条件一般，建议选择明亮天体")
        else:
            recommendations.append("观测条件较差，建议推迟观测计划")

        if seeing.mean > 3:
            recommendations.append("视宁度较差，不适合高分辨率观测")

        if cloud.mean > 50:
            recommendations.append("云量较多，建议等待更晴朗的夜晚")

        return "; ".join(recommendations)

    def analyze_meteor_shower(self, hourly_counts: List[int],
                               timestamps: List[str],
                               expected_peak: str) -> Dict:
        """分析流星雨"""
        stats = self.calculate_statistics(hourly_counts, "流星数", "count/hour")

        # 计算峰值
        peak_hour_idx = hourly_counts.index(max(hourly_counts)) if hourly_counts else 0
        peak_hour = timestamps[peak_hour_idx] if timestamps else ""

        # 峰值强度
        if not hourly_counts:
            peak_intensity = "unknown"
        elif max(hourly_counts) >= 100:
            peak_intensity = "extraordinary"
        elif max(hourly_counts) >= 50:
            peak_intensity = "high"
        elif max(hourly_counts) >= 20:
            peak_intensity = "moderate"
        else:
            peak_intensity = "low"

        # 爆发检测
        anomalies = self.detect_anomalies(hourly_counts, timestamps, method="zscore")
        outburst_detected = len([a for a in anomalies if a.score > 0.5]) > 0

        return {
            "peak_analysis": {
                "observed_peak_hour": peak_hour,
                "expected_peak": expected_peak,
                "peak_intensity": peak_intensity,
                "max_hourly_rate": max(hourly_counts) if hourly_counts else 0
            },
            "activity_summary": {
                "mean_hourly_rate": round(stats.mean, 1),
                "total_count": sum(hourly_counts) if hourly_counts else 0,
                "activity_trend": stats.trend
            },
            "outburst_detection": {
                "detected": outburst_detected,
                "anomaly_count": len(anomalies)
            }
        }

    def compare_targets(self, targets: List[Dict[str, Any]]) -> Dict:
        """比较多个观测目标"""
        if not targets:
            return {}

        comparison = {
            "count": len(targets),
            "by_type": defaultdict(list),
            "by_magnitude": {},
            "recommendations": []
        }

        # 按类型分组
        for target in targets:
            obj_type = target.get("type", "unknown")
            comparison["by_type"][obj_type].append(target.get("name", ""))

        # 按亮度排序
        sorted_targets = sorted(targets, key=lambda x: x.get("magnitude", 99))
        comparison["brightest"] = sorted_targets[0] if sorted_targets else {}
        comparison["faintest"] = sorted_targets[-1] if sorted_targets else {}

        # 建议
        if targets:
            best = min(targets, key=lambda x: x.get("magnitude", 99))
            comparison["recommendations"].append({
                "type": "brightest_target",
                "target": best.get("name", ""),
                "reason": f"视星等 {best.get('magnitude', 'N/A')}，最适合观测"
            })

        return comparison

    # ============ 报告生成 ============

    def generate_data_report(self, analysis_results: Dict, title: str = "天文数据分析报告") -> str:
        """生成数据分析报告"""
        lines = [
            "=" * 60,
            f"📊 {title}",
            "=" * 60,
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # 递归打印分析结果
        def print_dict(d: Any, indent: int = 0):
            prefix = "  " * indent
            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, (dict, list)) and value:
                        lines.append(f"{prefix}**{key}:**")
                        print_dict(value, indent + 1)
                    elif isinstance(value, float):
                        lines.append(f"{prefix}{key}: {value:.4f}")
                    else:
                        lines.append(f"{prefix}{key}: {value}")
            elif isinstance(d, list):
                for item in d[:10]:  # 最多显示10项
                    if isinstance(item, dict):
                        lines.append(f"{prefix}- {item.get('name', item)}")
                    else:
                        lines.append(f"{prefix}- {item}")

        print_dict(analysis_results)

        lines.append("=" * 60)
        return "\n".join(lines)

    def generate_visualization_data(self, data: List[float], timestamps: List[str],
                                     chart_type: str = "line") -> Dict:
        """生成可视化数据（用于前端图表）"""
        # 生成等间距的x轴标签
        step = max(1, len(timestamps) // 10)
        tick_labels = [timestamps[i] if i < len(timestamps) else ""
                      for i in range(0, len(timestamps), step)]

        return {
            "type": chart_type,
            "labels": tick_labels,
            "datasets": [{
                "data": data[::step] if step > 1 else data,
                "label": "数值",
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
            }]
        }

# ============ 示例用法 ============

def demo():
    print("=" * 60)
    print("天问-AGI 天文数据分析模块演示")
    print("=" * 60)

    analyzer = AstroAnalyzer()

    # 1. 恒星亮度分析
    print("\n⭐ 分析恒星亮度变化...")
    magnitudes = [4.2, 4.1, 4.3, 4.0, 4.5, 4.2, 4.1, 4.3, 5.0, 4.2]
    timestamps = [f"2026-04-{28+i:02d} {h:02d}:00" for i, h in enumerate([20]*5 + [22]*5)]
    brightness_result = analyzer.analyze_star_brightness(magnitudes, timestamps)
    print(f"   平均星等: {brightness_result['statistics']['mean_magnitude']}")
    print(f"   变星判定: {brightness_result['variable_star_analysis']['is_variable_star']}")
    print(f"   趋势: {brightness_result['trend']['direction']}")

    # 2. 观测质量分析
    print("\n🌤️ 分析观测质量...")
    seeing = [2.1, 1.8, 2.3, 2.0, 1.5, 2.2, 2.4, 1.9, 2.0, 2.1]
    cloud = [15, 20, 10, 25, 30, 18, 22, 12, 20, 15]
    quality_result = analyzer.analyze_observation_quality(seeing, cloud, timestamps)
    print(f"   综合评分: {quality_result['overall_quality_score']}/100")
    print(f"   质量等级: {quality_result['quality_level']}")
    print(f"   建议: {quality_result['recommendation']}")

    # 3. 流星雨分析
    print("\n☄️ 分析英仙座流星雨...")
    hourly_rates = [5, 12, 25, 45, 68, 95, 82, 55, 30, 15, 8, 3]
    meteor_timestamps = [f"2026-08-12 {h:02d}:00" for h in range(20, 32, 1)[:12]]
    meteor_result = analyzer.analyze_meteor_shower(hourly_rates, meteor_timestamps, "2026-08-12 22:00")
    print(f"   峰值强度: {meteor_result['peak_analysis']['peak_intensity']}")
    print(f"   最高小时率: {meteor_result['peak_analysis']['max_hourly_rate']}")
    print(f"   爆发检测: {'是' if meteor_result['outburst_detection']['detected'] else '否'}")

    # 4. 生成报告
    print("\n" + "=" * 60)
    report = analyzer.generate_data_report(
        {
            "brightness_analysis": brightness_result,
            "observation_quality": quality_result,
            "meteor_shower": meteor_result
        },
        "综合天文数据分析报告"
    )
    print(report)

if __name__ == "__main__":
    demo()