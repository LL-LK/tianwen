# 天问-AGI 数据挖掘模块实现报告

> 文档类型: 技术实现文档
> 创建日期: 2026-05-01
> 关联Issue: #15
> 状态: 已完成

---

## 一、背景与需求

### 1.1 Issue #15 问题陈述

Issue #15 指出天问-AGI 缺少数据挖掘能力，这是实现"文献调研 → 假说生成 → 假说验证 → 发现追踪 → 数据挖掘 → 指导观测"完整闭环的关键缺失环节。

### 1.2 竞品分析

| 项目 | 技术特点 | 借鉴点 |
|------|---------|--------|
| **CosmosNet** | ResNet-18 + EfficientNet-B0，12万张Hubble图像，PyTorch+FastAPI+React | CNN特征提取pipeline，Galaxy Zoo数据集处理 |
| **autostar** | AI Agent + GPT优化，NASA Kepler光变曲线 | 凌星信号检测，AI Agent驱动的模式发现 |

### 1.3 需求分析

天问-AGI 需要一个数据挖掘模块，能够：
- 从天文数据（光变曲线、光谱等）提取特征
- 发现隐藏模式（聚类、周期性等）
- 检测异常天体
- 与 HypothesisTester 集成生成和验证假说

---

## 二、架构设计

### 2.1 模块位置

```
runtime/data_miner.py  (新建)
```

### 2.2 核心组件

```
DataMiner
├── 特征提取 (Feature Extraction)
│   ├── extract_features_from_lightcurve()  - 光变曲线特征
│   └── extract_features_from_spectrum()   - 光谱特征
├── 模式发现 (Pattern Discovery)
│   ├── discover_cluster_patterns()         - K-means聚类
│   ├── discover_pca_patterns()            - PCA降维
│   └── discover_periodic_patterns()        - 周期检测
├── 关联分析 (Correlation Analysis)
│   └── find_correlations()                 - 变量相关性
├── 异常检测 (Anomaly Detection)
│   ├── _detect_iforest_anomalies()        - Isolation Forest
│   ├── _detect_dbscan_anomalies()         - DBSCAN
│   └── _detect_statistical_anomalies()     - 统计方法
└── 假说生成 (Hypothesis Generation)
    └── _generate_hypotheses_from_results() - 从挖掘结果生成假说
```

### 2.3 数据类型支持

| 数据类型 | 特征维度 | 特定分析 |
|---------|---------|---------|
| **light_curve** | 20+ 特征 | FFT频域、Lomb-Scargle周期图、峰谷检测 |
| **spectrum** | 10+ 特征 | 发射/吸收线计数、等效宽度、谱指数 |

---

## 三、功能实现

### 3.1 特征提取

#### 光变曲线特征

```python
# 基本统计
mean_flux, median_flux, std_flux, min_flux, max_flux, flux_range
cv (变异系数), time_span, mean_dt

# 频域特征 (FFT)
dominant_freq, dominant_power, mean_top_freq, spectral_entropy, spectral_centroid

# 周期特征 (Lomb-Scargle)
ls_dominant_freq, ls_dominant_power, estimated_period

# 趋势特征
trend_slope, trend_r_squared, trend_p_value, relative_trend

# 峰谷特征
n_peaks, mean_peak_flux, peak_flux_std, n_valleys, mean_valley_flux, peak_valley_ratio
```

#### 光谱特征

```python
# 基本统计
mean_intensity, std_intensity, max_intensity, snr

# 谱线特征
n_emission_lines, n_absorption_lines, equivalent_width

# 连续谱特征
wavelength_range, spectral_index
```

### 3.2 模式发现

#### 聚类分析

- 使用 K-means + 轮廓系数确定最优聚类数
- 发现相似天体群
- 每个聚类生成候选假说

#### PCA 降维

- 提取主成分，解释方差 > 10% 的保留
- 识别极端样本
- 生成候选假说

#### 周期性检测（借鉴 autostar）

- Lomb-Scargle 周期图分析
- DBSCAN 聚类相似周期
- 发现共享周期信号的天体群

### 3.3 关联分析

- Pearson/Spearman/Kendall 相关方法
- 两两变量相关性检验
- 强相关（|r| > 0.5）生成候选假说

### 3.4 异常检测

| 方法 | 适用场景 | 特点 |
|-----|---------|------|
| **Isolation Forest** | 常规异常检测 | ML-based，污染比例可调 |
| **DBSCAN** | 密度异常 | 噪声点识别，无需预设异常比例 |
| **统计方法** | 小数据集 | Z-score > 2 判定异常 |

---

## 四、与 HypothesisTester 集成

### 4.1 集成接口

```python
async def mine_and_test(
    self,
    data: List[Dict],
    source_type: str = "light_curve",
    observation_data: Optional[List[Dict]] = None
) -> Tuple[MiningReport, Any]:
    """
    挖掘数据并自动测试生成的假说
    """
    # 1. 执行挖掘
    mining_report = await self.mine(data, source_type)

    # 2. 测试生成的假说
    if self.hypothesis_tester and mining_report.hypotheses_generated:
        test_reports = []
        for hypo_data in mining_report.hypotheses_generated[:3]:
            hypothesis = Hypothesis(...)
            test_report = await self.hypothesis_tester.test_hypothesis(
                hypothesis, observation_data
            )
            test_reports.append(test_report)
        return mining_report, test_reports

    return mining_report, None
```

### 4.2 假说生成

从挖掘结果自动生成假说：

| 挖掘结果 | 生成的假说 |
|---------|-----------|
| 聚类模式 | "聚类内源可能共享相同物理机制" |
| 周期模式 | "这些源可能存在共享的周期结构" |
| 强相关 | "var1 和 var2 之间存在强相关" |
| 异常 | "该源可能是新类型天体" |

### 4.3 使用示例

```python
from data_miner import DataMiner
from hypothesis_tester import HypothesisTester

# 初始化
miner = DataMiner()
tester = HypothesisTester()
miner.hypothesis_tester = tester

# 光变曲线数据
data = [
    {
        "source_id": "star_001",
        "times": [0, 1, 2, ...],
        "fluxes": [100, 120, 95, ...],
        "errors": [5, 5, 5, ...]
    },
    ...
]

# 观测数据（用于验证）
observation_data = [...]

# 执行挖掘 + 假说测试
mining_report, test_reports = await miner.mine_and_test(
    data,
    source_type="light_curve",
    observation_data=observation_data
)

# 查看结果
print(mining_report.summary())
print(miner.get_mining_summary(mining_report))
```

---

## 五、技术栈

### 5.1 依赖

```
scipy>=1.10.0
numpy>=1.24.0
scikit-learn>=1.3.0
astropy>=5.0 (optional)
```

### 5.2 核心算法

| 功能 | 算法/库 |
|-----|--------|
| 周期检测 | scipy.signal.lombscargle |
| 聚类 | sklearn.cluster.KMeans, DBSCAN |
| 降维 | sklearn.decomposition.PCA |
| 异常检测 | sklearn.ensemble.IsolationForest |
| 统计检验 | scipy.stats |

---

## 六、文件清单

| 文件 | 说明 |
|-----|------|
| `runtime/data_miner.py` | 数据挖掘模块主文件 |
| `skills/Data-Analysis.md` | 更新文档，添加数据挖掘模块说明 |

---

## 七、测试建议

### 7.1 单元测试

```python
# 测试特征提取
from data_miner import DataMiner
import numpy as np

miner = DataMiner()
times = np.linspace(0, 10, 200)
fluxes = 100 + 20 * np.sin(2 * np.pi * times / 1.5)

feat = await miner.extract_features_from_lightcurve(times, fluxes, "test_star")
assert len(feat.features) > 15
assert feat.source_type == "light_curve"
```

### 7.2 集成测试

```python
# 测试与 HypothesisTester 集成
miner = DataMiner(hypothesis_tester=tester)
report = await miner.mine(data, source_type="light_curve")
assert len(report.hypotheses_generated) > 0
```

---

## 八、后续优化建议

1. **深度学习特征提取**: 借鉴 CosmosNet，使用预训练的 ResNet/EfficientNet 提取天文图像特征
2. **多波段联合分析**: 支持跨波段关联分析
3. **实时异常检测**: 流式数据异常检测
4. **假说优先级排序**: 基于先验概率和挖掘置信度排序候选假说

---

## 九、关联文档

- Issue #15: 数据挖掘 P0 缺失
- `runtime/hypothesis_tester.py`: 假说验证器
- `skills/Data-Analysis.md`: 数据分析技能文档
- `PRO_LITERATURE_OBSERVATION_LOOP_20260501.md`: 闭环流程分析