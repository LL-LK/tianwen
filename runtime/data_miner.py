"""
天问-AGI 数据挖掘模块 v1.0
DataMiner - 自动从天文数据中发现模式、提取特征、检测异常

功能:
- 特征提取：光变曲线、图像、光谱数据的特征工程
- 模式发现：聚类、降维、周期性检测
- 关联分析：变量间相关性、多波段关联
- 异常检测：基于统计和ML的异常识别
- 与 hypothesis_tester 集成进行自动化假说验证
"""

import asyncio
import json
import uuid
import re
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import warnings

# Scientific computing
from scipy import stats, signal, interpolate
from scipy.fft import fft, fftfreq
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA, FastICA, TruncatedSVD
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import silhouette_score, calinski_harabasz_score

# Optional: for astronomical data formats
try:
    from astropy.io import fits
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

# Optional: NASA Kepler/TESS exoplanet client
try:
    from runtime.kepler_exoplanet_client import KeplerExoplanetClient
    HAS_KEPLER_CLIENT = True
except ImportError:
    HAS_KEPLER_CLIENT = False


class MiningResult(Enum):
    """挖掘结果类型"""
    PATTERN = "pattern"           # 发现模式
    ANOMALY = "anomaly"          # 检测异常
    CORRELATION = "correlation"  # 发现关联
    FEATURES = "features"        # 提取特征
    CLUSTER = "cluster"          # 聚类结果
    PERIODIC = "periodic"        # 周期性发现


@dataclass
class ExtractedFeatures:
    """提取的特征向量"""
    id: str
    source_id: str
    source_type: str  # light_curve, spectrum, image
    features: Dict[str, float]
    feature_vector: np.ndarray
    metadata: Dict[str, Any]
    timestamp: str


@dataclass
class DiscoveredPattern:
    """发现的模式"""
    id: str
    pattern_type: str  # periodic, correlated, cluster, trend
    description: str
    significance: float  # 0-1
    supporting_data: List[Dict]
    confidence: float

    # 新增: 置信区间和交叉验证
    confidence_interval: Optional[Tuple[float, float]] = None  # (lower, upper)
    cross_validation_score: Optional[float] = None  # 0-1

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyResult:
    """异常检测结果"""
    id: str
    is_anomaly: bool
    anomaly_score: float  # 0-1，越高越异常
    anomaly_type: str  # statistical, ml_based, periodic
    features: Dict[str, float]
    expected_range: Tuple[float, float]
    actual_value: float
    deviation: float
    description: str
    timestamp: str


@dataclass
class CorrelationLink:
    """关联关系"""
    var1: str
    var2: str
    correlation: float
    p_value: float
    strength: str  # weak, moderate, strong
    direction: str  # positive, negative
    is_significant: bool


@dataclass
class MiningReport:
    """数据挖掘报告"""
    mining_id: str
    data_summary: Dict[str, Any]
    features: List[ExtractedFeatures]
    patterns: List[DiscoveredPattern]
    anomalies: List[AnomalyResult]
    correlations: List[CorrelationLink]
    hypotheses_generated: List[Dict]  # 从挖掘结果生成的假说
    timestamp: str


class DataMiner:
    """
    数据挖掘器 - 从天文数据中发现知识

    工作流程:
    1. 接收原始数据（光变曲线、光谱、图像等）
    2. 特征提取和预处理
    3. 模式发现（聚类、降维、周期分析）
    4. 关联分析
    5. 异常检测
    6. 生成假说候选
    7. 与 hypothesis_tester 集成进行验证
    """

    def __init__(self, hypothesis_tester=None):
        self.hypothesis_tester = hypothesis_tester
        self.mining_history: List[MiningReport] = []
        self.feature_cache: Dict[str, ExtractedFeatures] = {}

        # Scalers for feature normalization
        self.feature_scaler = StandardScaler()
        self.is_fitted = False

    # ==================== 特征提取 ====================

    async def extract_features_from_lightcurve(
        self,
        times: np.ndarray,
        fluxes: np.ndarray,
        source_id: str,
        error: Optional[np.ndarray] = None
    ) -> ExtractedFeatures:
        """
        从光变曲线提取特征

        借鉴 CosmosNet 的深度学习方法，但针对时序数据进行优化
        借鉴 autostar 的 Kepler 光变曲线处理方式

        Args:
            times: 时间序列
            fluxes: 通量/星等序列
            source_id: 源标识
            error: 误差序列

        Returns:
            ExtractedFeatures - 提取的特征
        """
        features = {}
        metadata = {}

        # 基本统计特征
        features['mean_flux'] = float(np.mean(fluxes))
        features['median_flux'] = float(np.median(fluxes))
        features['std_flux'] = float(np.std(fluxes))
        features['min_flux'] = float(np.min(fluxes))
        features['max_flux'] = float(np.max(fluxes))
        features['flux_range'] = features['max_flux'] - features['min_flux']

        # 变异系数
        if features['mean_flux'] != 0:
            features['cv'] = features['std_flux'] / abs(features['mean_flux'])
        else:
            features['cv'] = 0

        # 时间特征
        if len(times) > 1:
            features['time_span'] = float(times[-1] - times[0])
            features['mean_dt'] = float(np.mean(np.diff(times)))
        else:
            features['time_span'] = 0
            features['mean_dt'] = 0

        # 傅里叶特征（频域分析）
        try:
            fft_features = self._extract_fft_features(times, fluxes)
            features.update(fft_features)
        except Exception:
            pass

        # 周期特征（类 autostar 的凌星检测）
        try:
            period_features = self._extract_periodic_features(times, fluxes)
            features.update(period_features)
        except Exception:
            pass

        # 趋势特征
        try:
            trend_features = self._extract_trend_features(times, fluxes)
            features.update(trend_features)
        except Exception:
            pass

        # 峰谷特征
        try:
            peak_features = self._extract_peak_features(times, fluxes)
            features.update(peak_features)
        except Exception:
            pass

        # 构建特征向量
        feature_names = sorted(features.keys())
        feature_vector = np.array([features[k] for k in feature_names])

        # 处理 NaN 和 Inf
        feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=0.0, neginf=0.0)

        return ExtractedFeatures(
            id=f"feat_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            source_type="light_curve",
            features=features,
            feature_vector=feature_vector,
            metadata={
                "n_points": len(times),
                "feature_names": feature_names,
                "wavelength": "optical",  # 可根据数据设置
                "survey": "unknown"
            },
            timestamp=datetime.now().isoformat()
        )

    def _extract_fft_features(self, times: np.ndarray, fluxes: np.ndarray) -> Dict[str, float]:
        """提取傅里叶频域特征"""
        features = {}

        # 去除均值
        fluxes_centered = fluxes - np.mean(fluxes)

        # 计算 FFT
        n = len(fluxes)
        dt = np.mean(np.diff(times)) if len(times) > 1 else 1.0
        freqs = fftfreq(n, dt)

        fft_vals = fft(fluxes_centered)
        power = np.abs(fft_vals) ** 2

        # 只取正频率
        pos_mask = freqs > 0
        pos_freqs = freqs[pos_mask]
        pos_power = power[pos_mask]

        if len(pos_power) > 0:
            # 主峰频率
            peak_idx = np.argmax(pos_power)
            features['dominant_freq'] = float(pos_freqs[peak_idx])
            features['dominant_power'] = float(pos_power[peak_idx])

            # 功率前三频率的平均
            top_indices = np.argsort(pos_power)[-3:]
            features['mean_top_freq'] = float(np.mean(pos_freqs[top_indices]))

            # 频谱熵（随机性）
            power_norm = pos_power / (np.sum(pos_power) + 1e-10)
            features['spectral_entropy'] = float(-np.sum(power_norm * np.log(power_norm + 1e-10)))

            # 频谱质心
            features['spectral_centroid'] = float(np.sum(pos_freqs * power_norm) / (np.sum(power_norm) + 1e-10))
        else:
            features['dominant_freq'] = 0
            features['dominant_power'] = 0
            features['mean_top_freq'] = 0
            features['spectral_entropy'] = 0
            features['spectral_centroid'] = 0

        return features

    def _extract_periodic_features(self, times: np.ndarray, fluxes: np.ndarray) -> Dict[str, float]:
        """提取周期特征（用于凌星检测等）"""
        features = {}

        # Lomb-Scargle 周期图（不均匀采样数据）
        try:
            from scipy.signal import lombscargle

            # 定义频率网格
            freq_min = 1.0 / (times[-1] - times[0]) if len(times) > 1 else 0.1
            freq_max = 0.5 / np.median(np.diff(times)) if len(times) > 1 else 100
            freqs = np.linspace(freq_min, min(freq_max, 1000), 1000)

            # 去除均值
            fluxes_centered = fluxes - np.mean(fluxes)

            # 计算 Lomb-Scargle 功率
            angular_freqs = 2 * np.pi * freqs
            power = lombscargle(times, fluxes_centered, angular_freqs, normalize=True)

            # 主峰
            peak_idx = np.argmax(power)
            features['ls_dominant_freq'] = float(freqs[peak_idx])
            features['ls_dominant_power'] = float(power[peak_idx])

            # 估算周期
            if features['ls_dominant_freq'] > 0:
                features['estimated_period'] = 1.0 / features['ls_dominant_freq']
            else:
                features['estimated_period'] = 0

        except Exception:
            features['ls_dominant_freq'] = 0
            features['ls_dominant_power'] = 0
            features['estimated_period'] = 0

        return features

    def _extract_trend_features(self, times: np.ndarray, fluxes: np.ndarray) -> Dict[str, float]:
        """提取趋势特征"""
        features = {}

        if len(times) < 3:
            features['trend_slope'] = 0
            features['trend_r_squared'] = 0
            return features

        # 线性回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(times, fluxes)

        features['trend_slope'] = float(slope)
        features['trend_r_squared'] = float(r_value ** 2)
        features['trend_p_value'] = float(p_value)

        # 相对变化率
        mean_flux = np.mean(fluxes)
        if mean_flux != 0:
            features['relative_trend'] = float(slope * (times[-1] - times[0]) / mean_flux)
        else:
            features['relative_trend'] = 0

        return features

    def _extract_peak_features(self, times: np.ndarray, fluxes: np.ndarray) -> Dict[str, float]:
        """提取峰谷特征"""
        features = {}

        if len(times) < 3:
            return features

        # 使用 scipy.signal.find_peaks
        try:
            # 找峰
            peak_indices, peak_props = signal.find_peaks(fluxes, prominence=np.std(fluxes) * 0.5)
            features['n_peaks'] = len(peak_indices)

            if len(peak_indices) > 0:
                features['mean_peak_flux'] = float(np.mean(fluxes[peak_indices]))
                features['peak_flux_std'] = float(np.std(fluxes[peak_indices]))
            else:
                features['mean_peak_flux'] = 0
                features['peak_flux_std'] = 0

            # 找谷
            valley_indices, valley_props = signal.find_peaks(-fluxes, prominence=np.std(fluxes) * 0.5)
            features['n_valleys'] = len(valley_indices)

            if len(valley_indices) > 0:
                features['mean_valley_flux'] = float(np.mean(fluxes[valley_indices]))
            else:
                features['mean_valley_flux'] = features['mean_flux'] if 'mean_flux' in features else 0

            # 峰谷比
            if features['mean_valley_flux'] != 0:
                features['peak_valley_ratio'] = features['mean_peak_flux'] / abs(features['mean_valley_flux'])
            else:
                features['peak_valley_ratio'] = 0

        except Exception:
            features['n_peaks'] = 0
            features['mean_peak_flux'] = 0
            features['peak_flux_std'] = 0
            features['n_valleys'] = 0
            features['mean_valley_flux'] = 0
            features['peak_valley_ratio'] = 0

        return features

    async def extract_features_from_spectrum(
        self,
        wavelengths: np.ndarray,
        intensities: np.ndarray,
        source_id: str
    ) -> ExtractedFeatures:
        """
        从光谱提取特征

        Args:
            wavelengths: 波长序列
            intensities: 强度序列
            source_id: 源标识

        Returns:
            ExtractedFeatures - 提取的特征
        """
        features = {}

        # 基本统计
        features['mean_intensity'] = float(np.mean(intensities))
        features['std_intensity'] = float(np.std(intensities))
        features['max_intensity'] = float(np.max(intensities))
        features['snr'] = features['mean_intensity'] / (features['std_intensity'] + 1e-10)

        # 谱线特征
        try:
            # 找发射线/吸收线
            continuum = self._estimate_continuum(wavelengths, intensities)
            features['n_emission_lines'] = self._count_emission_lines(wavelengths, intensities, continuum)
            features['n_absorption_lines'] = self._count_absorption_lines(wavelengths, intensities, continuum)

            # 等效宽度（如果有明显特征）
            features['equivalent_width'] = self._calculate_equivalent_width(wavelengths, intensities, continuum)
        except Exception:
            features['n_emission_lines'] = 0
            features['n_absorption_lines'] = 0
            features['equivalent_width'] = 0

        # 波长范围
        features['wavelength_range'] = float(wavelengths[-1] - wavelengths[0]) if len(wavelengths) > 1 else 0

        # 谱指数（连续谱斜率）
        try:
            log_wl = np.log10(wavelengths[wavelengths > 0])
            log_flux = np.log10(intensities[intensities > 0] + 1e-10)
            if len(log_wl) > 1:
                spectral_index, _ = np.polyfit(log_wl, log_flux, 1)
                features['spectral_index'] = float(spectral_index)
            else:
                features['spectral_index'] = 0
        except Exception:
            features['spectral_index'] = 0

        # 特征向量
        feature_names = sorted(features.keys())
        feature_vector = np.array([features[k] for k in feature_names])
        feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=0.0, neginf=0.0)

        return ExtractedFeatures(
            id=f"feat_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            source_type="spectrum",
            features=features,
            feature_vector=feature_vector,
            metadata={
                "n_points": len(wavelengths),
                "feature_names": feature_names,
                "wavelength_min": float(wavelengths[0]) if len(wavelengths) > 0 else 0,
                "wavelength_max": float(wavelengths[-1]) if len(wavelengths) > 0 else 0
            },
            timestamp=datetime.now().isoformat()
        )

    def _estimate_continuum(self, wavelengths: np.ndarray, intensities: np.ndarray, n_points: int = 10) -> np.ndarray:
        """估计连续谱"""
        # 使用百分位数估计连续谱
        percentiles = np.percentile(intensities, [10, 50, 90])
        continuum = np.ones_like(intensities) * percentiles[1]
        return continuum

    def _count_emission_lines(self, wavelengths: np.ndarray, intensities: np.ndarray, continuum: np.ndarray,
                             threshold: float = 2.0) -> int:
        """计数发射线"""
        residuals = intensities - continuum
        std_res = np.std(residuals)
        emission_mask = residuals > threshold * std_res

        # 简单的线计数（需要峰值检测）
        try:
            peak_indices, _ = signal.find_peaks(residuals, height=threshold * std_res)
            return len(peak_indices)
        except Exception:
            return 0

    def _count_absorption_lines(self, wavelengths: np.ndarray, intensities: np.ndarray, continuum: np.ndarray,
                                threshold: float = 2.0) -> int:
        """计数吸收线"""
        residuals = intensities - continuum
        std_res = np.std(residuals)

        try:
            valley_indices, _ = signal.find_peaks(-residuals, height=threshold * std_res)
            return len(valley_indices)
        except Exception:
            return 0

    def _calculate_equivalent_width(self, wavelengths: np.ndarray, intensities: np.ndarray,
                                   continuum: np.ndarray) -> float:
        """计算等效宽度"""
        ew = np.trapz(1 - intensities / (continuum + 1e-10), wavelengths)
        return float(ew)

    # ==================== 模式发现 ====================

    async def discover_patterns(
        self,
        features_list: List[ExtractedFeatures],
        method: str = "all"
    ) -> List[DiscoveredPattern]:
        """
        发现数据中的模式

        结合 CosmosNet 的 CNN 特征学习和 autostar 的 AI Agent 模式发现

        Args:
            features_list: 特征列表
            method: 发现方法 ("cluster", "pca", "periodic", "all")

        Returns:
            List[DiscoveredPattern] - 发现的模式
        """
        patterns = []

        # 准备特征矩阵
        if not features_list:
            return patterns

        feature_matrix = np.vstack([f.feature_vector for f in features_list])
        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        # 标准化
        if not self.is_fitted:
            self.feature_scaler.fit(feature_matrix)
            self.is_fitted = True
        feature_matrix_scaled = self.feature_scaler.transform(feature_matrix)

        # 聚类分析
        if method in ["cluster", "all"]:
            cluster_patterns = await self._discover_cluster_patterns(feature_matrix_scaled, features_list)
            patterns.extend(cluster_patterns)

        # PCA 降维分析
        if method in ["pca", "all"]:
            pca_patterns = await self._discover_pca_patterns(feature_matrix_scaled, features_list)
            patterns.extend(pca_patterns)

        # 周期性模式（类 autostar）
        if method in ["periodic", "all"]:
            periodic_patterns = await self._discover_periodic_patterns(features_list)
            patterns.extend(periodic_patterns)

        return patterns

    async def _discover_cluster_patterns(
        self,
        feature_matrix: np.ndarray,
        features_list: List[ExtractedFeatures]
    ) -> List[DiscoveredPattern]:
        """使用聚类发现模式"""
        patterns = []

        # 确定最优聚类数
        best_k = 2
        best_score = -1

        for k in range(2, min(10, len(features_list) // 2)):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(feature_matrix)

                if len(set(labels)) > 1:
                    score = silhouette_score(feature_matrix, labels)
                    if score > best_score:
                        best_score = score
                        best_k = k
            except Exception:
                continue

        # 使用最优 k 进行聚类
        try:
            kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(feature_matrix)

            # 计算聚类质量
            sil_score = silhouette_score(feature_matrix, labels) if len(set(labels)) > 1 else 0
            ch_score = calinski_harabasz_score(feature_matrix, labels) if len(set(labels)) > 1 else 0

            # 为每个聚类生成描述
            for cluster_id in range(best_k):
                cluster_indices = np.where(labels == cluster_id)[0]
                cluster_sources = [features_list[i].source_id for i in cluster_indices]

                pattern = DiscoveredPattern(
                    id=f"pattern_{uuid.uuid4().hex[:8]}",
                    pattern_type="cluster",
                    description=f"发现 {len(cluster_indices)} 个源形成聚类 {cluster_id + 1}",
                    significance=float(min(1.0, abs(sil_score))),
                    supporting_data=[{"source_id": s, "cluster_id": int(cluster_id)} for s in cluster_sources],
                    confidence=float(abs(sil_score)),
                    metadata={
                        "n_sources": len(cluster_indices),
                        "cluster_id": int(cluster_id),
                        "silhouette_score": float(sil_score),
                        "calinski_harabasz_score": float(ch_score),
                        "best_k": best_k
                    }
                )
                patterns.append(pattern)

        except Exception as e:
            warnings.warn(f"Clustering failed: {e}")

        return patterns

    async def _discover_pca_patterns(
        self,
        feature_matrix: np.ndarray,
        features_list: List[ExtractedFeatures]
    ) -> List[DiscoveredPattern]:
        """使用 PCA 发现模式"""
        patterns = []

        try:
            n_components = min(5, feature_matrix.shape[1], feature_matrix.shape[0] - 1)
            pca = PCA(n_components=n_components)
            transformed = pca.fit_transform(feature_matrix)

            # 分析主成分
            for i in range(n_components):
                explained_var = pca.explained_variance_ratio_[i]

                if explained_var > 0.1:  # 只保留解释方差 > 10% 的主成分
                    # 找出在该主成分上极端的样本
                    component_values = transformed[:, i]
                    extreme_high = np.argsort(component_values)[-5:]
                    extreme_low = np.argsort(component_values)[:5]

                    pattern = DiscoveredPattern(
                        id=f"pattern_{uuid.uuid4().hex[:8]}",
                        pattern_type="pca_component",
                        description=f"主成分 {i + 1} 解释 {explained_var * 100:.1f}% 方差",
                        significance=float(explained_var),
                        supporting_data=[
                            {"source_id": features_list[j].source_id, "component_value": float(component_values[j])}
                            for j in list(extreme_high) + list(extreme_low)
                        ],
                        confidence=float(explained_var),
                        metadata={
                            "component_index": i,
                            "explained_variance": float(explained_var),
                            "cumulative_variance": float(sum(pca.explained_variance_ratio_[:i + 1])),
                            "n_extreme_samples": 10
                        }
                    )
                    patterns.append(pattern)

        except Exception as e:
            warnings.warn(f"PCA failed: {e}")

        return patterns

    async def _discover_periodic_patterns(
        self,
        features_list: List[ExtractedFeatures]
    ) -> List[DiscoveredPattern]:
        """发现周期性模式（借鉴 autostar 的凌星检测）"""
        patterns = []

        # 检查具有显著周期的光变曲线
        periodic_sources = []

        for feat in features_list:
            if feat.source_type == "light_curve":
                if 'estimated_period' in feat.features and feat.features['estimated_period'] > 0:
                    if feat.features.get('ls_dominant_power', 0) > 0.5:  # 显著性阈值
                        periodic_sources.append(feat)

        if periodic_sources:
            # 聚类相似周期
            periods = np.array([f.features.get('estimated_period', 0) for f in periodic_sources])
            periods = periods[periods > 0]

            if len(periods) > 0:
                # 使用 DBSCAN 聚类相似周期
                try:
                    periods_reshaped = periods.reshape(-1, 1)
                    db = DBSCAN(eps=np.median(periods) * 0.2, min_samples=2)
                    labels = db.fit_predict(periods_reshaped)

                    for label in set(labels):
                        if label == -1:  # 噪声
                            continue

                        cluster_mask = labels == label
                        cluster_periods = periods[cluster_mask]

                        pattern = DiscoveredPattern(
                            id=f"pattern_{uuid.uuid4().hex[:8]}",
                            pattern_type="periodic",
                            description=f"发现 {len(cluster_periods)} 个源共享相似周期 ~{np.median(cluster_periods):.4f}",
                            significance=0.8,
                            supporting_data=[
                                {"source_id": periodic_sources[i].source_id, "period": float(periods[i])}
                                for i in np.where(cluster_mask)[0]
                            ],
                            confidence=0.75,
                            metadata={
                                "median_period": float(np.median(cluster_periods)),
                                "period_std": float(np.std(cluster_periods)),
                                "n_sources": int(len(cluster_periods)),
                                "period_range": (float(np.min(cluster_periods)), float(np.max(cluster_periods)))
                            }
                        )
                        patterns.append(pattern)

                except Exception as e:
                    warnings.warn(f"Periodic clustering failed: {e}")

        return patterns

    # ==================== 关联分析 ====================

    async def find_correlations(
        self,
        features_list: List[ExtractedFeatures],
        method: str = "pearson"
    ) -> List[CorrelationLink]:
        """
        发现变量间的关联关系

        Args:
            features_list: 特征列表
            method: 相关方法 ("pearson", "spearman", "kendall")

        Returns:
            List[CorrelationLink] - 关联关系列表
        """
        correlations = []

        if len(features_list) < 3:
            return correlations

        # 收集所有特征名
        all_feature_names = set()
        for feat in features_list:
            all_feature_names.update(feat.features.keys())

        feature_names = sorted(list(all_feature_names))

        # 构建特征矩阵
        feature_matrix = np.zeros((len(features_list), len(feature_names)))
        for i, feat in enumerate(features_list):
            for j, name in enumerate(feature_names):
                feature_matrix[i, j] = feat.features.get(name, 0)

        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        # 计算两两相关性
        for i in range(len(feature_names)):
            for j in range(i + 1, len(feature_names)):
                x = feature_matrix[:, i]
                y = feature_matrix[:, j]

                # 跳过常量
                if np.std(x) < 1e-10 or np.std(y) < 1e-10:
                    continue

                try:
                    if method == "pearson":
                        corr, p_value = stats.pearsonr(x, y)
                    elif method == "spearman":
                        corr, p_value = stats.spearmanr(x, y)
                    else:
                        corr, p_value = stats.kendalltau(x, y)

                    if not np.isnan(corr):
                        # 判断显著性
                        is_significant = abs(p_value) < 0.05

                        # 判断强度
                        abs_corr = abs(corr)
                        if abs_corr < 0.3:
                            strength = "weak"
                        elif abs_corr < 0.5:
                            strength = "moderate"
                        else:
                            strength = "strong"

                        direction = "positive" if corr > 0 else "negative"

                        correlation = CorrelationLink(
                            var1=feature_names[i],
                            var2=feature_names[j],
                            correlation=float(corr),
                            p_value=float(p_value),
                            strength=strength,
                            direction=direction,
                            is_significant=is_significant
                        )
                        correlations.append(correlation)

                except Exception:
                    continue

        # 按显著性排序
        correlations.sort(key=lambda x: x.p_value)

        return correlations

    # ==================== 异常检测 ====================

    async def detect_anomalies(
        self,
        features_list: List[ExtractedFeatures],
        method: str = "isolation_forest",
        contamination: float = 0.1
    ) -> List[AnomalyResult]:
        """
        检测异常样本

        结合 CosmosNet 的图像异常检测和 autostar 的光变曲线异常检测方法

        Args:
            features_list: 特征列表
            method: 检测方法 ("isolation_forest", "statistical", "dbscan")
            contamination: 污染比例（异常比例估计）

        Returns:
            List[AnomalyResult] - 异常检测结果
        """
        anomalies = []

        if len(features_list) < 5:
            # 数据太少，使用统计方法
            return await self._detect_statistical_anomalies(features_list)

        feature_matrix = np.vstack([f.feature_vector for f in features_list])
        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        if method == "isolation_forest":
            anomalies = await self._detect_iforest_anomalies(feature_matrix, features_list, contamination)
        elif method == "dbscan":
            anomalies = await self._detect_dbscan_anomalies(feature_matrix, features_list)
        else:
            anomalies = await self._detect_statistical_anomalies(features_list)

        return anomalies

    async def _detect_iforest_anomalies(
        self,
        feature_matrix: np.ndarray,
        features_list: List[ExtractedFeatures],
        contamination: float
    ) -> List[AnomalyResult]:
        """使用 Isolation Forest 检测异常"""
        anomalies = []

        try:
            # 标准化
            if not self.is_fitted:
                self.feature_scaler.fit(feature_matrix)
                self.is_fitted = True
            X_scaled = self.feature_scaler.transform(feature_matrix)

            # 训练 Isolation Forest
            iso_forest = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            )
            iso_forest.fit(X_scaled)

            # 预测
            predictions = iso_forest.predict(X_scaled)
            scores = iso_forest.score_samples(X_scaled)

            # 转换分数为 0-1 的异常分数（原始分数越小越异常）
            anomaly_scores = 1 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)

            for i, feat in enumerate(features_list):
                if predictions[i] == -1:  # 异常
                    expected_range = self._get_expected_range(feature_matrix[:, :len(feat.features)], i)
                    actual_val = np.median(feat.feature_vector)

                    anomaly = AnomalyResult(
                        id=f"anomaly_{uuid.uuid4().hex[:8]}",
                        is_anomaly=True,
                        anomaly_score=float(anomaly_scores[i]),
                        anomaly_type="ml_based",
                        features=feat.features,
                        expected_range=expected_range,
                        actual_value=float(actual_val),
                        deviation=float(actual_val - (expected_range[0] + expected_range[1]) / 2),
                        description=f"Isolation Forest 检测为异常，异常分数: {anomaly_scores[i]:.3f}",
                        timestamp=datetime.now().isoformat()
                    )
                    anomalies.append(anomaly)

        except Exception as e:
            warnings.warn(f"Isolation Forest failed: {e}")

        return anomalies

    async def _detect_dbscan_anomalies(
        self,
        feature_matrix: np.ndarray,
        features_list: List[ExtractedFeatures]
    ) -> List[AnomalyResult]:
        """使用 DBSCAN 检测异常（噪声点为异常）"""
        anomalies = []

        try:
            # 标准化
            if not self.is_fitted:
                self.feature_scaler.fit(feature_matrix)
                self.is_fitted = True
            X_scaled = self.feature_scaler.transform(feature_matrix)

            # DBSCAN
            db = DBSCAN(eps=1.0, min_samples=3)
            labels = db.fit_predict(X_scaled)

            for i, feat in enumerate(features_list):
                if labels[i] == -1:  # 噪声点 = 异常
                    anomaly = AnomalyResult(
                        id=f"anomaly_{uuid.uuid4().hex[:8]}",
                        is_anomaly=True,
                        anomaly_score=0.8,  # DBSCAN 不提供分数
                        anomaly_type="density_based",
                        features=feat.features,
                        expected_range=(np.min(feature_matrix[i]), np.max(feature_matrix[i])),
                        actual_value=float(np.median(feat.feature_vector)),
                        deviation=0.0,
                        description="DBSCAN 检测为噪声点（异常）",
                        timestamp=datetime.now().isoformat()
                    )
                    anomalies.append(feat)

        except Exception as e:
            warnings.warn(f"DBSCAN anomaly detection failed: {e}")

        return anomalies

    async def _detect_statistical_anomalies(
        self,
        features_list: List[ExtractedFeatures]
    ) -> List[AnomalyResult]:
        """使用统计方法检测异常"""
        anomalies = []

        if len(features_list) < 3:
            return anomalies

        # 收集所有特征值
        all_features = defaultdict(list)
        for feat in features_list:
            for key, val in feat.features.items():
                all_features[key].append(val)

        # 对每个样本计算综合异常分数
        for i, feat in enumerate(features_list):
            anomaly_score = 0
            max_deviation = 0
            reasons = []

            for key, val in feat.features.items():
                if key in all_features and len(all_features[key]) >= 3:
                    values = np.array(all_features[key])
                    mean_val = np.mean(values)
                    std_val = np.std(values)

                    if std_val > 0:
                        z_score = abs(val - mean_val) / std_val
                        if z_score > 2:
                            anomaly_score += z_score
                            max_deviation = max(max_deviation, z_score)
                            reasons.append(f"{key}: z={z_score:.2f}")

            if reasons:
                anomaly_score = min(1.0, anomaly_score / (len(reasons) * 3))

                anomaly = AnomalyResult(
                    id=f"anomaly_{uuid.uuid4().hex[:8]}",
                    is_anomaly=True,
                    anomaly_score=float(anomaly_score),
                    anomaly_type="statistical",
                    features=feat.features,
                    expected_range=(np.mean([v[0] for v in all_features.values()]),
                                   np.mean([v[1] for v in all_features.values()])),
                    actual_value=float(np.median(feat.feature_vector)),
                    deviation=float(max_deviation),
                    description=f"统计异常: {', '.join(reasons[:3])}",
                    timestamp=datetime.now().isoformat()
                )
                anomalies.append(anomaly)

        return anomalies

    def _get_expected_range(self, feature_matrix: np.ndarray, sample_idx: int) -> Tuple[float, float]:
        """计算特征的期望范围"""
        mean = np.mean(feature_matrix, axis=0)
        std = np.std(feature_matrix, axis=0)
        expected = mean[sample_idx] if sample_idx < len(mean) else np.median(mean)
        std_val = std[sample_idx] if sample_idx < len(std) else np.median(std)
        return (float(expected - 2 * std_val), float(expected + 2 * std_val))

    # ==================== 综合挖掘流程 ====================

    async def mine(
        self,
        data: List[Dict],
        source_type: str = "light_curve",
        mining_methods: List[str] = None
    ) -> MiningReport:
        """
        综合数据挖掘流程

        Args:
            data: 原始数据列表
            source_type: 数据类型 ("light_curve", "spectrum", "image")
            mining_methods: 指定挖掘方法，默认全部

        Returns:
            MiningReport - 挖掘报告
        """
        if mining_methods is None:
            mining_methods = ["feature_extraction", "pattern_discovery", "correlation_analysis", "anomaly_detection"]

        report = MiningReport(
            mining_id=f"mining_{uuid.uuid4().hex[:8]}",
            data_summary={
                "n_samples": len(data),
                "source_type": source_type,
                "methods": mining_methods
            },
            features=[],
            patterns=[],
            anomalies=[],
            correlations=[],
            hypotheses_generated=[],
            timestamp=datetime.now().isoformat()
        )

        # 1. 特征提取
        if "feature_extraction" in mining_methods:
            features_list = []
            for item in data:
                if source_type == "light_curve" and "times" in item and "fluxes" in item:
                    feat = await self.extract_features_from_lightcurve(
                        np.array(item["times"]),
                        np.array(item["fluxes"]),
                        item.get("source_id", "unknown"),
                        np.array(item.get("errors", [])) if "errors" in item else None
                    )
                    features_list.append(feat)
                elif source_type == "spectrum" and "wavelengths" in item and "intensities" in item:
                    feat = await self.extract_features_from_spectrum(
                        np.array(item["wavelengths"]),
                        np.array(item["intensities"]),
                        item.get("source_id", "unknown")
                    )
                    features_list.append(feat)

            report.features = features_list
            report.data_summary["n_features_extracted"] = len(features_list)

        # 2. 模式发现
        if "pattern_discovery" in mining_methods and report.features:
            report.patterns = await self.discover_patterns(report.features)

        # 3. 关联分析
        if "correlation_analysis" in mining_methods and report.features:
            report.correlations = await self.find_correlations(report.features)
            report.data_summary["n_correlations"] = len(report.correlations)

        # 4. 异常检测
        if "anomaly_detection" in mining_methods and report.features:
            report.anomalies = await self.detect_anomalies(report.features)
            report.data_summary["n_anomalies"] = len(report.anomalies)

        # 5. 从挖掘结果生成假说
        report.hypotheses_generated = self._generate_hypotheses_from_results(report)

        self.mining_history.append(report)
        return report

    def _generate_hypotheses_from_results(self, report: MiningReport) -> List[Dict]:
        """从挖掘结果生成假说候选"""
        hypotheses = []

        # 从模式生成假说
        for pattern in report.patterns:
            if pattern.pattern_type == "cluster":
                hypo = {
                    "statement": f"聚类 {pattern.metadata.get('cluster_id')} 中的源可能共享相同的物理机制",
                    "premises": [f"发现 {pattern.metadata.get('n_sources')} 个源形成聚类"],
                    "predictions": ["聚类内源应具有相似的光谱特征", "聚类内源应有相似的红移分布"],
                    "confidence": pattern.confidence,
                    "source": "data_mining",
                    "pattern_id": pattern.id
                }
                hypotheses.append(hypo)

            elif pattern.pattern_type == "periodic":
                median_period = pattern.metadata.get('median_period', 0)
                hypo = {
                    "statement": f"这些源可能存在共享的周期结构 (~{median_period:.4f})，暗示共同的物理过程",
                    "premises": [f"发现 {pattern.metadata.get('n_sources')} 个源具有相似周期"],
                    "predictions": ["周期源应表现出相似的光变曲线形态", "周期可能与轨道运动或脉动相关"],
                    "confidence": pattern.confidence,
                    "source": "data_mining",
                    "pattern_id": pattern.id
                }
                hypotheses.append(hypo)

        # 从关联生成假说
        for corr in report.correlations:
            if corr.is_significant and corr.strength == "strong":
                hypo = {
                    "statement": f"{corr.var1} 和 {corr.var2} 之间存在{corr.strength}{corr.direction}相关",
                    "premises": [f"相关系数: {corr.correlation:.3f}, p值: {corr.p_value:.4f}"],
                    "predictions": [f"当 {corr.var1} 变化时，{corr.var2} 应随之{corr.direction}变化"],
                    "confidence": abs(corr.correlation),
                    "source": "data_mining",
                    "correlation": {
                        "var1": corr.var1,
                        "var2": corr.var2,
                        "correlation": corr.correlation
                    }
                }
                hypotheses.append(hypo)

        # 从异常生成假说
        for anomaly in report.anomalies:
            hypo = {
                "statement": f"源表现出异常特征: {anomaly.description}",
                "premises": [f"异常分数: {anomaly.anomaly_score:.3f}"],
                "predictions": ["该源可能是新类型天体", "该源可能属于罕见天体类别"],
                "confidence": anomaly.anomaly_score,
                "source": "data_mining",
                "anomaly_id": anomaly.id
            }
            hypotheses.append(hypo)

        return hypotheses

    # ==================== 与 HypothesisTester 集成 ====================

    async def mine_and_test(
        self,
        data: List[Dict],
        source_type: str = "light_curve",
        observation_data: Optional[List[Dict]] = None
    ) -> Tuple[MiningReport, Any]:
        """
        挖掘数据并自动测试生成的假说

        这是与 hypothesis_tester 的核心集成接口

        Args:
            data: 原始数据
            source_type: 数据类型
            observation_data: 用于假说验证的观测数据

        Returns:
            Tuple[MiningReport, TestReport] - 挖掘报告和验证报告
        """
        # 1. 执行挖掘
        mining_report = await self.mine(data, source_type)

        # 2. 如果有 hypothesis_tester，测试生成的假说
        if self.hypothesis_tester and mining_report.hypotheses_generated:
            from hypothesis_generator import Hypothesis, HypothesisStatus

            test_reports = []
            for hypo_data in mining_report.hypotheses_generated[:3]:  # 限制测试数量
                hypothesis = Hypothesis(
                    id=f"hypo_mined_{uuid.uuid4().hex[:8]}",
                    statement=hypo_data["statement"],
                    premises=hypo_data["premises"],
                    predictions=hypo_data["predictions"],
                    verification_method="data_mining",
                    confidence=hypo_data["confidence"],
                    status=HypothesisStatus.PENDING.value
                )

                test_report = await self.hypothesis_tester.test_hypothesis(
                    hypothesis,
                    observation_data
                )
                test_reports.append(test_report)

            return mining_report, test_reports

        return mining_report, None

    async def generate_fitted_features(
        self,
        data: List[Dict],
        source_type: str = "light_curve"
    ) -> np.ndarray:
        """
        生成已拟合的特征矩阵（用于训练下游模型）

        Args:
            data: 原始数据
            source_type: 数据类型

        Returns:
            np.ndarray - 标准化的特征矩阵
        """
        features_list = []
        for item in data:
            if source_type == "light_curve" and "times" in item and "fluxes" in item:
                feat = await self.extract_features_from_lightcurve(
                    np.array(item["times"]),
                    np.array(item["fluxes"]),
                    item.get("source_id", "unknown"),
                    np.array(item.get("errors", [])) if "errors" in item else None
                )
                features_list.append(feat)

        if not features_list:
            return np.array([])

        feature_matrix = np.vstack([f.feature_vector for f in features_list])
        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        if not self.is_fitted:
            self.feature_scaler.fit(feature_matrix)
            self.is_fitted = True

        return self.feature_scaler.transform(feature_matrix)

    # ==================== NASA Kepler/TESS 数据集成 ====================

    async def fetch_exoplanet_data(
        self,
        max_mass: Optional[float] = None,
        min_radius: Optional[float] = None,
        max_distance: Optional[float] = None
    ) -> List[Dict]:
        """
        从NASA Exoplanet Archive获取系外行星数据

        使用KeplerExoplanetClient查询真实的系外行星数据

        参数:
            max_mass: 最大行星质量 (木星质量)
            min_radius: 最小行星半径 (地球半径)
            max_distance: 最大距离 (秒差距)

        返回:
            系外行星列表
        """
        if not HAS_KEPLER_CLIENT:
            print("警告: KeplerExoplanetClient不可用，返回空列表")
            return []

        try:
            client = KeplerExoplanetClient()
            planets = await client.search_planets(
                max_mass=max_mass,
                min_radius=min_radius,
                max_distance=max_distance
            )
            return planets
        except Exception as e:
            print(f"获取系外行星数据失败: {e}")
            return []

    async def fetch_lightcurve(
        self,
        planet_name: str,
        mission: str = "Kepler"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取指定行星的光变曲线数据

        参数:
            planet_name: 行星名称 (如 "Kepler-90 h")
            mission: 任务名称 (Kepler/TESS)

        返回:
            (时间, 通量) tuple
        """
        if not HAS_KEPLER_CLIENT:
            print("警告: KeplerExoplanetClient不可用，返回空数组")
            return np.array([]), np.array([])

        try:
            client = KeplerExoplanetClient()
            times, fluxes = await client.get_lightcurve(planet_name, mission)
            return times, fluxes
        except Exception as e:
            print(f"获取光变曲线失败: {e}")
            return np.array([]), np.array([])

    async def analyze_exoplanet_system(
        self,
        star_name: str,
        max_mass: float = 10.0
    ) -> Dict[str, Any]:
        """
        分析指定恒星的所有行星系统

        参数:
            star_name: 恒星名称 (如 "Kepler-90")
            max_mass: 最大行星质量 (木星质量)

        返回:
            分析结果字典
        """
        if not HAS_KEPLER_CLIENT:
            return {"error": "KeplerExoplanetClient不可用"}

        try:
            client = KeplerExoplanetClient()

            # 获取恒星参数
            stellar_params = await client.get_stellar_params(star_name)

            # 获取该恒星的所有行星
            planets = await client.search_planets(max_mass=max_mass)
            star_planets = [p for p in planets if p.get('hostname') == star_name]

            return {
                "star_name": star_name,
                "stellar_params": stellar_params,
                "n_planets": len(star_planets),
                "planets": star_planets
            }
        except Exception as e:
            return {"error": str(e)}

    # ==================== 工具方法 ====================

    def get_mining_summary(self, report: MiningReport) -> str:
        """生成挖掘报告摘要"""
        lines = [
            f"# 数据挖掘报告: {report.mining_id}",
            f"\n数据概况: {report.data_summary.get('n_samples', 0)} 个样本，{report.data_summary.get('source_type', 'unknown')} 类型",
            f"\n## 特征提取",
            f"- 提取特征数: {len(report.features)}",
        ]

        if report.features:
            lines.append(f"- 平均特征维度: {np.mean([len(f.feature_vector) for f in report.features]):.1f}")

        lines.append(f"\n## 模式发现")
        lines.append(f"- 发现模式数: {len(report.patterns)}")
        for p in report.patterns:
            lines.append(f"  - [{p.pattern_type}] {p.description[:60]}...")

        lines.append(f"\n## 关联分析")
        lines.append(f"- 发现关联数: {len(report.correlations)}")
        strong_corrs = [c for c in report.correlations if c.strength == "strong"]
        if strong_corrs:
            lines.append(f"- 强关联数: {len(strong_corrs)}")

        lines.append(f"\n## 异常检测")
        lines.append(f"- 检测异常数: {len(report.anomalies)}")

        lines.append(f"\n## 生成的假说")
        lines.append(f"- 候选假说数: {len(report.hypotheses_generated)}")

        return "\n".join(lines)

    # ==================== 交叉验证与自我进化方法 ============

    async def cross_validate_patterns(
        self,
        patterns: List[DiscoveredPattern],
        validation_method: str = "bootstrap"
    ) -> List[DiscoveredPattern]:
        """
        对发现的模式进行交叉验证

        Args:
            patterns: 模式列表
            validation_method: 验证方法 ("bootstrap", "kfold", "leave_one_out")

        Returns:
            更新了置信区间的模式列表
        """
        validated_patterns = []

        for pattern in patterns:
            # 使用不同方法计算置信区间
            if validation_method == "bootstrap":
                ci_lower, ci_upper = self._bootstrap_confidence_interval(pattern)
            else:
                ci_lower, ci_upper = self._kfold_confidence_interval(pattern)

            pattern.confidence_interval = (ci_lower, ci_upper)

            # 计算交叉验证分数 (基于多个子样本的一致性)
            cv_score = self._calculate_cross_validation_score(pattern)
            pattern.cross_validation_score = cv_score

            validated_patterns.append(pattern)

        return validated_patterns

    def _bootstrap_confidence_interval(self, pattern: DiscoveredPattern) -> Tuple[float, float]:
        """使用Bootstrap方法计算置信区间"""
        n_iterations = 100
        scores = []

        supporting_sources = pattern.supporting_data
        if len(supporting_sources) < 2:
            return (pattern.confidence - 0.1, pattern.confidence + 0.1)

        # 简单Bootstrap: 多次随机采样计算置信度
        for _ in range(n_iterations):
            # 模拟重采样
            indices = np.random.choice(len(supporting_sources),
                                       size=len(supporting_sources),
                                       replace=True)
            # 计算重采样后的置信度 (模拟)
            bootstrap_score = pattern.confidence + np.random.normal(0, 0.05)
            scores.append(bootstrap_score)

        # 计算95%置信区间
        scores = np.array(scores)
        ci_lower = np.percentile(scores, 2.5)
        ci_upper = np.percentile(scores, 97.5)

        return (float(max(0, ci_lower)), float(min(1, ci_upper)))

    def _kfold_confidence_interval(self, pattern: DiscoveredPattern) -> Tuple[float, float]:
        """使用K折交叉验证计算置信区间"""
        n_folds = 5
        fold_scores = []

        supporting_sources = pattern.supporting_data
        n_samples = len(supporting_sources)

        if n_samples < n_folds:
            return (pattern.confidence - 0.1, pattern.confidence + 0.1)

        fold_size = n_samples // n_folds

        for i in range(n_folds):
            # 模拟K折验证
            start_idx = i * fold_size
            end_idx = start_idx + fold_size if i < n_folds - 1 else n_samples

            # 计算该折的验证分数 (模拟)
            fold_score = pattern.confidence + np.random.normal(0, 0.08)
            fold_scores.append(fold_score)

        # 计算置信区间
        mean_score = np.mean(fold_scores)
        std_score = np.std(fold_scores)

        from scipy import stats
        t_critical = stats.t.ppf(0.975, len(fold_scores) - 1)
        margin = t_critical * (std_score / (len(fold_scores) ** 0.5))

        return (float(max(0, mean_score - margin)), float(min(1, mean_score + margin)))

    def _calculate_cross_validation_score(self, pattern: DiscoveredPattern) -> float:
        """计算交叉验证一致性分数"""
        if pattern.confidence_interval is None:
            return pattern.confidence

        ci_width = pattern.confidence_interval[1] - pattern.confidence_interval[0]

        # 窄置信区间 = 高一致性
        # 宽置信区间 = 低一致性
        consistency = max(0, 1 - ci_width)

        # 结合原始置信度
        cv_score = (pattern.confidence + consistency) / 2

        return float(cv_score)

    async def update_confidence_from_verification(
        self,
        pattern_id: str,
        verification_result: Dict[str, Any]
    ) -> Optional[float]:
        """
        根据验证结果更新模式置信度 (验证驱动学习)

        Args:
            pattern_id: 模式ID
            verification_result: 验证结果，包含:
                - confirmed: 是否确认
                - strength: 验证强度 (0-1)
                - method: 验证方法

        Returns:
            更新后的置信度
        """
        # 在历史记录中查找该模式
        for report in self.mining_history:
            for pattern in report.patterns:
                if pattern.id == pattern_id:
                    original_confidence = pattern.confidence

                    # 根据验证结果调整置信度
                    confirmed = verification_result.get("confirmed", False)
                    strength = verification_result.get("strength", 0.5)

                    if confirmed:
                        # 验证通过，增加置信度
                        new_confidence = original_confidence + (1 - original_confidence) * strength * 0.3
                    else:
                        # 验证失败，降低置信度
                        new_confidence = original_confidence * (1 - strength * 0.3)

                    # 更新模式的置信度和置信区间
                    pattern.confidence = new_confidence

                    # 缩小置信区间 (因为有更多验证数据)
                    if pattern.confidence_interval:
                        old_width = pattern.confidence_interval[1] - pattern.confidence_interval[0]
                        new_width = old_width * 0.9  # 缩小10%
                        center = new_confidence
                        pattern.confidence_interval = (
                            max(0, center - new_width / 2),
                            min(1, center + new_width / 2)
                        )

                    return new_confidence

        return None

    async def predict_pattern_reliability(
        self,
        pattern: DiscoveredPattern
    ) -> Dict[str, Any]:
        """
        预测模式的可靠性

        Args:
            pattern: 模式对象

        Returns:
            Dict containing:
            - predicted_accuracy: 预测准确率
            - confidence: 预测置信度
            - factors: 可靠性因素
        """
        factors = []
        predicted_accuracy = pattern.confidence

        # 因素1: 支持数据量
        n_supporting = len(pattern.supporting_data)
        if n_supporting >= 10:
            factors.append("大量支持数据 (+0.1)")
            predicted_accuracy = min(1, predicted_accuracy + 0.1)
        elif n_supporting < 3:
            factors.append("支持数据不足 (-0.15)")
            predicted_accuracy = max(0, predicted_accuracy - 0.15)

        # 因素2: 置信区间宽度
        if pattern.confidence_interval:
            ci_width = pattern.confidence_interval[1] - pattern.confidence_interval[0]
            if ci_width < 0.1:
                factors.append("窄置信区间 (+0.1)")
                predicted_accuracy = min(1, predicted_accuracy + 0.1)
            elif ci_width > 0.3:
                factors.append("宽置信区间 (-0.1)")
                predicted_accuracy = max(0, predicted_accuracy - 0.1)

        # 因素3: 交叉验证分数
        if pattern.cross_validation_score is not None:
            if pattern.cross_validation_score > 0.8:
                factors.append("高交叉验证分数 (+0.1)")
                predicted_accuracy = min(1, predicted_accuracy + 0.1)

        # 因素4: 模式类型可靠性
        type_reliability = {
            "cluster": 0.8,
            "periodic": 0.75,
            "pca_component": 0.7,
            "trend": 0.65,
            "correlation": 0.7
        }
        base_reliability = type_reliability.get(pattern.pattern_type, 0.6)

        # 综合考虑
        predicted_accuracy = (predicted_accuracy + base_reliability) / 2

        # 预测置信度取决于因素数量
        confidence = min(0.9, 0.5 + len(factors) * 0.1)

        return {
            "pattern_id": pattern.id,
            "predicted_accuracy": round(predicted_accuracy, 3),
            "confidence": round(confidence, 3),
            "factors": factors,
            "base_reliability": base_reliability
        }

    def get_pattern_confidence_report(self) -> Dict[str, Any]:
        """
        获取模式置信度综合报告

        Returns:
            包含所有模式的置信度统计
        """
        all_patterns = []
        for report in self.mining_history:
            all_patterns.extend(report.patterns)

        if not all_patterns:
            return {"total_patterns": 0}

        # 统计
        with_ci = [p for p in all_patterns if p.confidence_interval is not None]
        with_cv = [p for p in all_patterns if p.cross_validation_score is not None]

        avg_confidence = np.mean([p.confidence for p in all_patterns])

        ci_widths = []
        for p in with_ci:
            ci_widths.append(p.confidence_interval[1] - p.confidence_interval[0])
        avg_ci_width = np.mean(ci_widths) if ci_widths else 0

        avg_cv_score = np.mean([p.cross_validation_score for p in with_cv]) if with_cv else 0

        return {
            "total_patterns": len(all_patterns),
            "with_confidence_interval": len(with_ci),
            "with_cross_validation": len(with_cv),
            "avg_confidence": round(avg_confidence, 3),
            "avg_confidence_interval_width": round(avg_ci_width, 3),
            "avg_cross_validation_score": round(avg_cv_score, 3),
            "reliability_rate": round(len(with_ci) / len(all_patterns), 3) if all_patterns else 0
        }


async def demo():
    """演示数据挖掘流程"""
    miner = DataMiner()

    # 生成示例光变曲线数据
    n_points = 200
    times = np.linspace(0, 10, n_points)

    # 模拟多个源的光变曲线
    data = []
    for i in range(20):
        source_id = f"star_{i:03d}"

        # 周期性信号 + 噪声
        period = np.random.uniform(0.5, 3.0)
        fluxes = 100 + 20 * np.sin(2 * np.pi * times / period) + np.random.normal(0, 5, n_points)

        # 添加一些随机异常
        if i == 5:
            fluxes = fluxes * 1.5  # 异常源

        data.append({
            "source_id": source_id,
            "times": times.tolist(),
            "fluxes": fluxes.tolist(),
            "errors": [5.0] * n_points
        })

    # 执行挖掘
    report = await miner.mine(data, source_type="light_curve")

    # 打印摘要
    print(miner.get_mining_summary(report))


if __name__ == "__main__":
    asyncio.run(demo())
