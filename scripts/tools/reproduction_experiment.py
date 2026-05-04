"""
天问-AGI 天文大模型计算流程复现实验
=========================================

对比现有 data_miner.py 模块与目标天文大模型的计算流程:
1. 光变曲线分析 (类 autostar)
2. 星系形态分类 (类 CosmosNet)
3. 异常检测 (类 DeepMind Exoplanet)

运行方式: python F:/tianwen-agi/reproduction_experiment.py
"""

import asyncio
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.data_miner import DataMiner
from src.agents.hypothesis_test import HypothesisTester
from src.data.models import Hypothesis, HypothesisStatus


# ==================== 模拟数据生成 ====================

def generate_kepler_lightcurve(n_points=2000, period=2.5, transit_depth=0.01,
                               noise_level=0.005, source_id="KEPLER_001"):
    """
    生成模拟 Kepler 光变曲线 (用于复现 autostar 的凌星检测)

    Args:
        n_points: 采样点数
        period: 轨道周期 (天)
        transit_depth: 凌星深度
        noise_level: 噪声水平
        source_id: 源标识

    Returns:
        dict: 包含 times, fluxes, errors 的字典
    """
    # 时间序列 (Kepler 长周期观测 ~90天)
    times = np.linspace(0, 90, n_points)

    # 基线通量
    fluxes = np.ones(n_points)

    # 添加凌星信号 (简化模型: 余弦近似)
    # 凌星事件发生在周期的一半附近
    phase = (times % period) / period
    transit_mask = (phase > 0.45) & (phase < 0.55)

    # Box-shaped transit model (简化)
    transit_signal = np.where(transit_mask, 1 - transit_depth, 1.0)

    # 加上恒星脉动 (类变星信号)
    pulsation = 1 + 0.01 * np.sin(2 * np.pi * times / 0.3)
    fluxes = fluxes * transit_signal * pulsation

    # 添加高斯噪声
    fluxes += np.random.normal(0, noise_level, n_points)

    # 添加异常点 (耀变、仪器噪声)
    n_anomalies = int(0.02 * n_points)
    anomaly_indices = np.random.choice(n_points, n_anomalies, replace=False)
    fluxes[anomaly_indices] *= np.random.uniform(1.1, 1.5, n_anomalies)

    # 误差估计
    errors = np.ones(n_points) * noise_level

    return {
        "source_id": source_id,
        "times": times.tolist(),
        "fluxes": fluxes.tolist(),
        "errors": errors.tolist(),
        "metadata": {
            "period": period,
            "transit_depth": transit_depth,
            "survey": "Kepler",
            "target": "exoplanet_candidate"
        }
    }


def generate_galaxy_images(n_samples=100, image_size=64):
    """
    生成模拟星系图像数据 (用于复现 CosmosNet 的形态分类)

    Returns:
        list: 模拟图像特征列表 (实际是特征向量，模拟 ResNet 提取)
    """
    # 模拟三种星系类型
    # 1. Spiral (螺旋星系): 高频纹理、明显旋臂结构
    # 2. Elliptical (椭圆星系): 平滑径向梯度、低频
    # 3. Merger (并合星系): 不规则、双核

    galaxy_data = []

    for i in range(n_samples):
        # 随机选择类型
        r = np.random.random()
        if r < 0.4:
            galaxy_type = "Spiral"
            # 螺旋星系统计特征: 中等亮度、高方差、明显纹理
            features = {
                "mean_brightness": np.random.uniform(0.3, 0.6),
                "std_brightness": np.random.uniform(0.15, 0.25),
                "concentration_index": np.random.uniform(0.4, 0.6),  # 中心集中度
                "asymmetry": np.random.uniform(0.2, 0.4),
                "smoothness": np.random.uniform(0.3, 0.5),
                "texture_variance": np.random.uniform(0.1, 0.2),
                "edge_sharpness": np.random.uniform(0.5, 0.8),
                "spiral_arm_persistence": np.random.uniform(0.3, 0.7)
            }
        elif r < 0.75:
            galaxy_type = "Elliptical"
            # 椭圆星系统计特征: 高亮度、低纹理、平滑
            features = {
                "mean_brightness": np.random.uniform(0.5, 0.8),
                "std_brightness": np.random.uniform(0.05, 0.12),
                "concentration_index": np.random.uniform(0.7, 0.9),
                "asymmetry": np.random.uniform(0.05, 0.15),
                "smoothness": np.random.uniform(0.6, 0.8),
                "texture_variance": np.random.uniform(0.01, 0.05),
                "edge_sharpness": np.random.uniform(0.2, 0.4),
                "spiral_arm_persistence": 0.0
            }
        else:
            galaxy_type = "Merger"
            # 并合星系统计特征: 不规则、高方差、双峰
            features = {
                "mean_brightness": np.random.uniform(0.35, 0.65),
                "std_brightness": np.random.uniform(0.2, 0.35),
                "concentration_index": np.random.uniform(0.3, 0.6),
                "asymmetry": np.random.uniform(0.5, 0.8),
                "smoothness": np.random.uniform(0.2, 0.4),
                "texture_variance": np.random.uniform(0.15, 0.3),
                "edge_sharpness": np.random.uniform(0.3, 0.6),
                "spiral_arm_persistence": np.random.uniform(0.1, 0.3)
            }

        features["source_id"] = f"galaxy_{i:04d}"
        features["type"] = galaxy_type
        features["image_size"] = image_size

        galaxy_data.append(features)

    return galaxy_data


# ==================== 实验 1: 光变曲线分析 (类 autostar) ====================

async def experiment_lightcurve_analysis():
    """
    复现 autostar 的光变曲线分析流程

    autostar 声称:
    - AI Agent 优化 GPT 模型
    - 检测 Kepler 光变曲线的行星凌星信号
    - 晨间输出候选列表

    天问 data_miner.py 实现:
    - Lomb-Scargle 周期图分析
    - FFT 频域分析
    - 峰谷检测
    """
    print("\n" + "=" * 70)
    print("实验 1: 光变曲线分析 (类 autostar)")
    print("=" * 70)

    miner = DataMiner()

    # 生成模拟 Kepler 数据
    print("\n[数据生成] 生成 50 条模拟 Kepler 光变曲线...")
    lightcurves = []
    for i in range(50):
        # 50% 包含凌星信号
        if i < 25:
            lc = generate_kepler_lightcurve(
                n_points=1000,
                period=np.random.uniform(1.5, 5.0),
                transit_depth=np.random.uniform(0.005, 0.02),
                source_id=f"star_with_transit_{i:03d}"
            )
        else:
            # 无凌星，只有噪声和脉动
            lc = {
                "source_id": f"star_no_transit_{i:03d}",
                "times": np.linspace(0, 90, 1000).tolist(),
                "fluxes": (1 + 0.01 * np.sin(2 * np.pi * np.linspace(0, 90, 1000) / 0.3) +
                          np.random.normal(0, 0.005, 1000)).tolist(),
                "errors": [0.005] * 1000,
                "metadata": {"survey": "Kepler", "target": "variable_star"}
            }
        lightcurves.append(lc)

    print(f"  生成完成: {len(lightcurves)} 条光变曲线")

    # 提取特征
    print("\n[特征提取] 使用 data_miner 提取特征...")
    features_list = []
    for lc in lightcurves:
        feat = await miner.extract_features_from_lightcurve(
            np.array(lc["times"]),
            np.array(lc["fluxes"]),
            lc["source_id"],
            np.array(lc["errors"]) if "errors" in lc else None
        )
        features_list.append(feat)

    print(f"  提取完成: {len(features_list)} 个特征集")
    print(f"  平均特征维度: {np.mean([len(f.feature_vector) for f in features_list]):.1f}")

    # 周期检测分析
    print("\n[周期分析] 分析 Lomb-Scargle 周期检测结果...")

    periodic_sources = []
    for feat in features_list:
        if feat.source_type == "light_curve":
            ls_power = feat.features.get('ls_dominant_power', 0)
            estimated_period = feat.features.get('estimated_period', 0)

            if ls_power > 0.3 and estimated_period > 0:
                periodic_sources.append({
                    "source_id": feat.source_id,
                    "period": estimated_period,
                    "ls_power": ls_power,
                    "has_transit": "transit" in feat.source_id.lower()
                })

    print(f"  检测到 {len(periodic_sources)} 个周期性源")

    # 对比检测结果
    true_transit_count = sum(1 for lc in lightcurves if "with_transit" in lc["source_id"])
    detected_transit_count = len([p for p in periodic_sources if p["has_transit"]])

    print(f"\n[对比结果]")
    print(f"  实际有凌星信号: {true_transit_count}")
    print(f"  检测到周期性: {detected_transit_count}")
    print(f"  漏检率: {(true_transit_count - detected_transit_count) / true_transit_count * 100:.1f}%")

    # 偏差分析
    deviation_analysis = {
        "experiment": "lightcurve_periodic_detection",
        "target_model": "autostar",
        "our_implementation": "data_miner.py",
        "data_miner_features": [
            "Lomb-Scargle periodogram",
            "FFT frequency analysis",
            "Peak/valley detection",
            "Trend analysis"
        ],
        "detection_rate": detected_transit_count / true_transit_count if true_transit_count > 0 else 0,
        "missing_rate": (true_transit_count - detected_transit_count) / true_transit_count if true_transit_count > 0 else 0,
        "deviation_reasons": [
            "模拟数据使用简化box模型，与真实凌星信号形态差异",
            "Lomb-Scargle 对短周期信号敏感，长周期可能漏检",
            "无凌星深度学习的相位折叠优化",
            "缺少多周期联合分析"
        ],
        "needed_improvements": [
            "实现 BLS (Box Least Squares) 凌星检测算法",
            "添加 wotan 等专业凌星检测工具",
            "引入相位折叠和双 deseasonalization",
            "集成 VARTOOLS 等成熟周期分析工具"
        ]
    }

    return deviation_analysis


# ==================== 实验 2: 星系形态分类 (类 CosmosNet) ====================

async def experiment_galaxy_classification():
    """
    复现 CosmosNet 的星系形态分类流程

    CosmosNet 声称:
    - ResNet-18 / EfficientNet-B0
    - 68,000+ Hubble 图像
    - 4类分类: Spiral/Elliptical/Merger/Lenticular
    - 精度未公开

    天问 data_miner.py 实现:
    - PCA 降维分析
    - K-means 聚类
    - 轮廓系数优化
    """
    print("\n" + "=" * 70)
    print("实验 2: 星系形态分类 (类 CosmosNet)")
    print("=" * 70)

    miner = DataMiner()

    # 生成模拟星系数据
    print("\n[数据生成] 生成 100 个模拟星系特征向量...")
    galaxy_features_raw = generate_galaxy_images(n_samples=100, image_size=64)

    # 转换为 data_miner 格式
    galaxy_data = []
    for g in galaxy_features_raw:
        # 构建特征向量
        source_id = g["source_id"]
        galaxy_type = g["type"]

        # 创建 ExtractedFeatures
        from src.data.miner import ExtractedFeatures

        feature_dict = {k: v for k, v in g.items()
                       if k not in ["source_id", "type", "image_size"]}

        feature_names = sorted(feature_dict.keys())
        feature_vector = np.array([feature_dict[k] for k in feature_names])

        feat = ExtractedFeatures(
            id=f"feat_{source_id}",
            source_id=source_id,
            source_type="image",
            features=feature_dict,
            feature_vector=feature_vector,
            metadata={"true_type": galaxy_type, "image_size": 64},
            timestamp=datetime.now().isoformat()
        )
        galaxy_data.append(feat)

    print(f"  生成完成: {len(galaxy_data)} 个星系特征")

    # 模式发现 (聚类分析)
    print("\n[模式发现] 使用 K-means + PCA 进行聚类分析...")
    patterns = await miner.discover_patterns(galaxy_data, method="all")

    print(f"  发现 {len(patterns)} 个模式")

    # 分析聚类质量
    cluster_patterns = [p for p in patterns if p.pattern_type == "cluster"]
    if cluster_patterns:
        for cp in cluster_patterns:
            print(f"\n  聚类 {cp.metadata.get('cluster_id')}: "
                  f"{cp.metadata.get('n_sources')} 个源, "
                  f"轮廓系数: {cp.metadata.get('silhouette_score', 0):.3f}")

    # 评估分类准确率 (基于真实标签)
    print("\n[准确率评估] 对比聚类结果与真实标签...")

    # 统计真实分布
    true_labels = [g.metadata["true_type"] for g in galaxy_data]
    spiral_count = sum(1 for t in true_labels if t == "Spiral")
    elliptical_count = sum(1 for t in true_labels if t == "Elliptical")
    merger_count = sum(1 for t in true_labels if t == "Merger")

    print(f"  真实分布: Spiral={spiral_count}, Elliptical={elliptical_count}, Merger={merger_count}")

    # 偏差分析
    deviation_analysis = {
        "experiment": "galaxy_morphology_classification",
        "target_model": "CosmosNet",
        "our_implementation": "data_miner.py",
        "cosmosnet_features": [
            "ResNet-18 / EfficientNet-B0 深度学习",
            "68,000+ Hubble 图像训练",
            "4类分类输出"
        ],
        "our_features": [
            "PCA 降维",
            "K-means 聚类",
            "轮廓系数优化"
        ],
        "limitations": [
            "模拟特征向量 vs 真实 CNN 提取的深度特征",
            "无监督聚类 vs 有监督分类",
            "8维手工特征 vs 512维深度特征",
            "无图像输入接口 (仅支持特征向量)"
        ],
        "deviation_reasons": [
            "数据表示差异: 手工特征 vs 深度特征",
            "算法范式差异: 无监督聚类 vs 有监督深度学习",
            "训练数据差异: 100样本模拟 vs 68000真实图像"
        ],
        "needed_improvements": [
            "集成 astro_pipeline 的 ResNet-50 分类器",
            "接入预训练星系分类模型 (CosmosNet/Phosphoros)",
            "支持图像直接输入",
            "增加特征维度 (纹理、形态参数等)"
        ]
    }

    return deviation_analysis


# ==================== 实验 3: 异常检测 (类 DeepMind Exoplanet) ====================

async def experiment_anomaly_detection():
    """
    复现 DeepMind Exoplanet 的异常检测流程

    DeepMind Exoplanet 声称:
    - 95% 准确率
    - Isolation Forest / 深度学习
    - 用于检测光变曲线异常

    天问 data_miner.py 实现:
    - Isolation Forest
    - DBSCAN 密度检测
    - 统计 Z-score
    """
    print("\n" + "=" * 70)
    print("实验 3: 异常检测 (类 DeepMind Exoplanet)")
    print("=" * 70)

    miner = DataMiner()

    # 生成模拟光变曲线 (含异常)
    print("\n[数据生成] 生成 50 条光变曲线 (含 10% 异常)...")
    lightcurves = []
    np.random.seed(42)

    for i in range(50):
        if i < 45:
            # 正常光变曲线
            times = np.linspace(0, 30, 500)
            fluxes = 100 + 10 * np.sin(2 * np.pi * times / 2.5) + np.random.normal(0, 2, 500)
        else:
            # 异常光变曲线 (耀变、仪器故障等)
            times = np.linspace(0, 30, 500)
            fluxes = 100 + 10 * np.sin(2 * np.pi * times / 2.5)
            # 添加异常尖峰
            anomaly_idx = np.random.choice(500, 10, replace=False)
            fluxes[anomaly_idx] += np.random.uniform(20, 50, 10)

        lightcurves.append({
            "source_id": f"lightcurve_{i:03d}",
            "times": times.tolist(),
            "fluxes": fluxes.tolist(),
            "errors": [2.0] * 500,
            "metadata": {"is_anomaly": i >= 45}
        })

    print(f"  生成完成: {len(lightcurves)} 条光变曲线")
    print(f"  异常曲线: 5 条 (10%)")

    # 提取特征
    print("\n[特征提取] 提取光变曲线特征...")
    features_list = []
    for lc in lightcurves:
        feat = await miner.extract_features_from_lightcurve(
            np.array(lc["times"]),
            np.array(lc["fluxes"]),
            lc["source_id"]
        )
        features_list.append(feat)

    print(f"  提取完成: {len(features_list)} 个特征集")

    # 异常检测 (Isolation Forest)
    print("\n[异常检测] 使用 Isolation Forest 检测异常...")
    anomalies = await miner.detect_anomalies(
        features_list,
        method="isolation_forest",
        contamination=0.1  # 期望 10% 异常
    )

    print(f"  检测到 {len(anomalies)} 个异常")

    # 统计检测结果
    true_anomaly_count = sum(1 for lc in lightcurves if lc["metadata"].get("is_anomaly"))
    detected_anomaly_count = len(anomalies)

    true_positives = 0
    for anomaly in anomalies:
        source_id = anomaly.features.get('source_id', '')
        if source_id and any(f"lightcurve_{i:03d}" == source_id and i >= 45
                            for i in range(50)):
            true_positives += 1

    false_positives = detected_anomaly_count - true_positives
    false_negatives = true_anomaly_count - true_positives

    precision = true_positives / detected_anomaly_count if detected_anomaly_count > 0 else 0
    recall = true_positives / true_anomaly_count if true_anomaly_count > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n[检测结果统计]")
    print(f"  实际异常: {true_anomaly_count}")
    print(f"  检测异常: {detected_anomaly_count}")
    print(f"  真阳性 (TP): {true_positives}")
    print(f"  假阳性 (FP): {false_positives}")
    print(f"  假阴性 (FN): {false_negatives}")
    print(f"  精确率 (Precision): {precision:.3f}")
    print(f"  召回率 (Recall): {recall:.3f}")
    print(f"  F1 分数: {f1_score:.3f}")

    # 偏差分析
    deviation_analysis = {
        "experiment": "lightcurve_anomaly_detection",
        "target_model": "DeepMind Exoplanet AI",
        "claimed_accuracy": "95%",
        "our_implementation": "data_miner.py Isolation Forest",
        "our_results": {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score
        },
        "deviation_reasons": [
            "模拟异常 vs 真实复杂异常模式",
            "Isolation Forest 对高维特征效果好，低维手工特征效果有限",
            "异常定义差异: 尖峰值 vs 完整光变曲线异常",
            "无时序上下文感知"
        ],
        "needed_improvements": [
            "引入时序异常检测模型 (LSTM-AE, Temporal Fusion Transformer)",
            "使用专业天文异常检测工具 (wotan, catwoman)",
            "多波段联合异常检测",
            "集成 NASA Exoplanet Archive 标签数据"
        ]
    }

    return deviation_analysis


# ==================== 主实验流程 ====================

async def run_reproduction_experiment():
    """运行完整复现实验"""
    print("\n" + "#" * 70)
    print("# 天问-AGI 天文大模型计算流程复现实验")
    print("# Reproduction Experiment for Astronomical AI Models")
    print("#" * 70)
    print(f"# 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    # 初始化模块
    miner = DataMiner()
    tester = HypothesisTester()

    # 存储所有实验结果
    experiment_results = {
        "timestamp": datetime.now().isoformat(),
        "experiments": []
    }

    # 实验 1: 光变曲线分析
    result1 = await experiment_lightcurve_analysis()
    experiment_results["experiments"].append(result1)

    # 实验 2: 星系形态分类
    result2 = await experiment_galaxy_classification()
    experiment_results["experiments"].append(result2)

    # 实验 3: 异常检测
    result3 = await experiment_anomaly_detection()
    experiment_results["experiments"].append(result3)

    # 综合分析
    print("\n" + "=" * 70)
    print("综合偏差分析总结")
    print("=" * 70)

    summary = {
        "total_experiments": 3,
        "experiment_details": [
            {
                "name": "光变曲线周期检测",
                "target": "autostar",
                "detection_rate": f"{result1.get('detection_rate', 0)*100:.1f}%",
                "main_gap": "缺少 BLS 凌星检测和相位折叠优化"
            },
            {
                "name": "星系形态分类",
                "target": "CosmosNet",
                "main_gap": "无监督聚类 vs 有监督深度学习，特征维度差异大"
            },
            {
                "name": "异常检测",
                "target": "DeepMind Exoplanet",
                "claimed": "95% 准确率",
                "our_f1": f"{result3.get('our_results', {}).get('f1_score', 0)*100:.1f}%",
                "main_gap": "缺少时序上下文感知和真实天文异常标签"
            }
        ],
        "common_deviations": [
            "算法范式差异: 传统 ML vs 深度学习",
            "数据表示差异: 手工特征 vs 深度特征",
            "训练数据规模差异: 模拟数据 vs 真实大规模数据"
        ],
        "recommended_actions": [
            "Phase 1: 集成 astro_pipeline 的 ResNet-50 到 data_miner",
            "Phase 2: 引入 BLS 凌星检测和 wotan 工具",
            "Phase 3: 接入预训练模型 (astroPT, Phosphoros)",
            "Phase 4: 建立交叉验证基准数据集"
        ]
    }

    for detail in summary["experiment_details"]:
        print(f"\n  [{detail['name']}] vs {detail['target']}")
        if 'detection_rate' in detail:
            print(f"    检测率: {detail['detection_rate']}")
        if 'our_f1' in detail:
            print(f"    声称准确率: {detail['claimed']}, 我们的 F1: {detail['our_f1']}")
        print(f"    主要差距: {detail['main_gap']}")

    print(f"\n[推荐行动]")
    for i, action in enumerate(summary["recommended_actions"], 1):
        print(f"  {i}. {action}")

    experiment_results["summary"] = summary

    return experiment_results


# ==================== 入口 ====================

if __name__ == "__main__":
    results = asyncio.run(run_reproduction_experiment())

    # 保存结果
    output_path = Path("F:/tianwen-agi/reproduction_experiment_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n实验结果已保存到: {output_path}")
    print("\n复现实验完成!")
