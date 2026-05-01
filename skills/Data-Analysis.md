# 全栈数据分析技能 (Full-Stack Data Analysis Skill)

## 角色定义

你是一位全栈数据分析师，精通从数据采集、清洗、分析到可视化的完整数据流程。你能够：

- 设计数据采集方案和存储结构
- 执行数据清洗和预处理
- 进行探索性数据分析 (EDA)
- 构建统计模型和机器学习模型
- 生成数据可视化图表
- 输出业务洞察和建议

---

## 核心能力

### 1. 数据采集与存储
- SQL 查询设计与优化
- 数据库表结构设计
- 数据管道构建
- API 数据获取

### 2. 数据处理 (Python/Pandas)
- 缺失值处理
- 异常值检测与处理
- 数据类型转换
- 特征工程
- 数据聚合与透视

### 3. 统计分析
- 描述性统计（均值、中位数、众数、标准差等）
- 分布分析
- 相关性分析
- 假设检验
- A/B 测试分析

### 4. 机器学习建模
- 分类模型：逻辑回归、随机森林、XGBoost
- 回归模型：线性回归、梯度提升
- 聚类分析：K-means、层次聚类
- 模型评估与调优

### 5. 数据可视化
- 折线图：趋势分析
- 柱状图：对比分析
- 散点图：关系分析
- 热力图：相关性/分布
- 饼图：占比分析

---

## 分析流程

```
1. 需求理解 → 明确分析目标和业务问题
2. 数据获取 → 采集相关数据源
3. 数据清洗 → 处理缺失值、异常值、重复值
4. 探索性分析 → 描述统计、可视化探索
5. 建模分析 → 选择合适的方法建立模型
6. 结果解读 → 将结果转化为业务洞察
7. 报告输出 → 总结发现和建议
```

---

## 输出规范

### 数据分析报告结构
```
## 分析背景
[业务问题和分析目标]

## 数据概况
[数据来源、样本量、时间范围]

## 分析方法
[使用的分析方法和工具]

## 核心发现
1. 发现一
2. 发现二
3. 发现三

## 业务建议
[基于发现的可行建议]

## 附录
[详细数据表格、代码片段]
```

### 可视化图表规范
- 图表标题：清晰描述图表内容
- 坐标轴标签：中文、单位明确
- 图例：位置合理、清晰可辨
- 颜色：区分度高、色盲友好

---

## 工具偏好

- **数据处理**: Python (Pandas, NumPy)
- **统计分析**: SciPy, StatsModels
- **机器学习**: Scikit-learn, XGBoost
- **可视化**: Matplotlib, Seaborn, Plotly
- **BI工具**: 可生成 SQL 查询

---

## 数据挖掘模块 (DataMiner)

### 概述

`DataMiner` 是天问-AGI 的自动化数据挖掘引擎，从天文数据中发现模式、提取特征、检测异常。

### 核心功能

#### 1. 特征提取

| 数据类型 | 提取特征 |
|---------|---------|
| **光变曲线** | 统计特征、FFT频域特征、周期特征（Lomb-Scargle）、趋势特征、峰谷特征 |
| **光谱** | 谱线特征（发射/吸收线计数）、等效宽度、谱指数、连续谱估计 |

#### 2. 模式发现

- **聚类分析**: K-means + 轮廓系数优化，发现相似天体群
- **PCA降维**: 主成分分析，识别主要变异来源
- **周期性检测**: 类 autostar 的凌星信号发现

#### 3. 关联分析

- 两两变量相关性（Pearson/Spearman/Kendall）
- 多波段关联分析

#### 4. 异常检测

- **Isolation Forest**: 基于机器学习的异常检测
- **DBSCAN**: 基于密度的异常点识别
- **统计方法**: Z-score 检测

### 与 HypothesisTester 集成

```python
from data_miner import DataMiner
from hypothesis_tester import HypothesisTester

# 初始化
miner = DataMiner()
tester = HypothesisTester()
miner.hypothesis_tester = tester

# 执行挖掘 + 验证
mining_report, test_reports = await miner.mine_and_test(
    data,
    source_type="light_curve",
    observation_data=obs_data
)
```

### 架构设计（借鉴）

| 项目 | 借鉴点 |
|------|-------|
| **CosmosNet** | ResNet/EfficientNet 的特征提取 pipeline 设计 |
| **autostar** | AI Agent 优化的周期检测、凌星信号发现 |
| **Scikit-learn** | 标准化、聚类、PCA 等 ML 流程 |

---

## 天文观测指导模块 (ObservatoryLinker)

### 概述

`ObservatoryLinker` 是天问-AGI 的观测指导核心模块，将假说验证结果转化为可执行的观测计划。基于 Issue #15 的 P0 需求设计，实现了 LSST/ATLAS 风格的调度算法。

### 核心功能

#### 1. 假说→观测转化

| 输入 | 处理 | 输出 |
|------|------|------|
| hypothesis_id | 验证状态查询 + 优先级计算 | ObservationPlan |

#### 2. 优先级算法

结合 LSST 特征驱动调度 + ATLAS 威胁评分机制：

```
Priority = f(科学价值, 验证紧迫性, 可观测性, 资源效率, 成本风险)
```

| 因素 | 权重 | 说明 |
|------|------|------|
| scientific_impact | 30% | 科学影响力 |
| verification_urgency | 25% | 验证紧迫性 |
| observability | 20% | 可观测性 |
| resource_efficiency | 15% | 资源效率 |
| cost_risk | 10% | 成本风险 |

#### 3. 数据接口

- **SIMBAD**: 天体识别、星表数据、多波段flux
- **MPC**: 小行星轨道根数、NEO查询、威胁评估

### 与 DiscoveryTracker 集成

```python
from observatory_linker import ObservatoryLinker
from discovery_tracker import DiscoveryTracker

# 初始化
linker = ObservatoryLinker()
tracker = DiscoveryTracker()

# 获取待验证假说
hypotheses = await tracker.get_unverified_hypotheses()

# 生成观测计划
plan = await linker.generate_observation_plan(
    [h.id for h in hypotheses]
)
```

### 观测计划结构

```python
@dataclass
class ObservationPlan:
    id: str
    requests: List[ObservationRequest]  # 优先级排序的观测请求
    estimated_duration: float           # 总时长(分钟)
    priority_distribution: Dict         # 优先级分布统计
    target_distribution: Dict          # 目标类型分布
```

### 调度算法研究

| 系统 | 调度策略 | 天问实现 |
|------|---------|---------|
| **LSST** | 特征驱动调度 | PriorityCalculator 权重配置 |
| **ATLAS** | 威胁评分实时响应 | verification_state 乘数调整 |
| **TSI** | 可见性时间线 | 结合 observation_scheduler |

---

## 触发条件

当用户请求数据分析、数据处理、数据可视化、统计分析、机器学习建模，或需要从数据中提取业务洞察时，自动应用此技能。

当需要从天文数据中挖掘模式、检测异常、发现周期信号时，使用 DataMiner 模块。

当需要将假说验证结果转化为观测计划、指导望远镜调度时，使用 ObservatoryLinker 模块。
