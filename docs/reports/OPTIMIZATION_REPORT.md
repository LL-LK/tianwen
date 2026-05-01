# 天问-AGI 核心模块优化报告

**日期**: 2026/05/01
**优化原则**: 基于深度思考结论 - 可验证的可靠性、验证驱动学习、3-Agent架构、ChromaDB共享向量记忆、交叉验证机制

---

## 一、问题分析

### 1.1 discovery_tracker.py (25572字节)

**问题列表**:
1. **精度虚标**: `get_statistics()` 中的 `success_rate` 是单一数值估计，无置信区间
2. **缺少交叉验证**: 闭环成功率计算无多模型交叉验证
3. **缺少置信度报告**: 所有统计指标无不确定性量化
4. **无模型差异预测**: 无法预测不同假说验证结果的一致性

### 1.2 data_miner.py (48714字节)

**问题列表**:
1. **精度虚标**: `DiscoveredPattern.confidence` 是单一 float，无置信区间
2. **缺少交叉验证**: 聚类、PCA 等模式发现无交叉验证
3. **缺少置信度报告**: 异常分数、相关系数均无不确定性量化
4. **无验证驱动学习**: 挖掘结果无法根据验证反馈自我优化

### 1.3 observatory_linker.py (38323字节)

**问题列表**:
1. **精度虚标**: `PriorityCalculator.calculate()` 返回单一分数，无置信区间
2. **缺少交叉验证**: 优先级计算无多方法交叉验证
3. **缺少置信度报告**: `observability_score` 默认 70.0，无不确定性
4. **无验证驱动学习**: 观测优先级无法根据验证结果调整

### 1.4 hypothesis_tester.py (28894字节)

**问题列表**:
1. **精度虚标**: `TestReport.confidence_change` 是单一 float
2. **缺少交叉验证**: 验证结果无多方法交叉验证
3. **缺少置信度报告**: t检验等统计检验无置信区间
4. **无验证反馈**: 验证结果无法反馈到假说生成

### 1.5 multi_agent_coordinator.py (46369字节)

**问题列表**:
1. **精度虚标**: 冲突检测使用随机概率 (30%)
2. **缺少交叉验证**: 冲突解决策略无交叉验证
3. **缺少置信度报告**: 共识决策无置信度报告
4. **无模型差异预测**: 无法预测不同Agent意见的一致性

---

## 二、修改内容详细说明

### 2.1 discovery_tracker.py 修改

**新增类和字段**:

```python
@dataclass
class ConfidenceInterval:
    """置信区间"""
    lower: float
    upper: float
    confidence: float = 0.95

    def to_dict(self) -> Dict:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "width": self.upper - self.lower
        }

    def contains(self, value: float) -> bool:
        return self.lower <= value <= self.upper

@dataclass
class VerificationRecord:
    # ... 原有字段 ...
    confidence_interval: Optional[ConfidenceInterval] = None
    cross_validation_score: Optional[float] = None
```

**新增方法**:

1. `record_verification()` - 增强支持交叉验证结果计算置信区间
2. `cross_validate_hypothesis()` - 对假说验证结果进行交叉验证
3. `predict_model_disagreement()` - 预测不同模型的分歧程度
4. `get_validation_consensus()` - 获取验证共识报告
5. `update_hypothesis_confidence()` - 根据新证据更新假说置信度 (验证驱动学习)
6. `report_validation_uncertainty()` - 报告假说验证的不确定性

### 2.2 data_miner.py 修改

**新增字段**:

```python
@dataclass
class DiscoveredPattern:
    # ... 原有字段 ...
    confidence_interval: Optional[Tuple[float, float]] = None
    cross_validation_score: Optional[float] = None
```

**新增方法**:

1. `cross_validate_patterns()` - 对发现的模式进行交叉验证
2. `_bootstrap_confidence_interval()` - 使用Bootstrap方法计算置信区间
3. `_kfold_confidence_interval()` - 使用K折交叉验证计算置信区间
4. `_calculate_cross_validation_score()` - 计算交叉验证一致性分数
5. `update_confidence_from_verification()` - 根据验证结果更新模式置信度 (验证驱动学习)
6. `predict_pattern_reliability()` - 预测模式的可靠性
7. `get_pattern_confidence_report()` - 获取模式置信度综合报告

### 2.3 hypothesis_tester.py 修改

**新增字段**:

```python
@dataclass
class TestReport:
    # ... 原有字段 ...
    confidence_interval: Optional[Tuple[float, float]] = None
    cross_validation_score: Optional[float] = None
    statistical_confidence: Optional[Dict[str, Any]] = None
```

**新增方法**:

1. `_compute_verification_confidence()` - 计算验证的置信区间和交叉验证分数
2. `get_verification_confidence_report()` - 获取验证置信度综合报告
3. `update_confidence_from_feedback()` - 根据反馈更新假说置信度 (验证驱动学习)

### 2.4 observatory_linker.py 修改

**新增方法**:

1. `PriorityCalculator.calculate_with_confidence()` - 计算优先级分数及置信区间
2. `PriorityCalculator.cross_validate_priority()` - 使用多种方法交叉验证优先级

**关键特性**:
- 使用Monte Carlo方法传播不确定性
- 100次扰动采样计算置信区间
- 三种替代方法进行交叉验证

### 2.5 multi_agent_coordinator.py 修改

**修改方法**:

1. `detect_conflict()` - 改进为基于历史一致性和专业领域重叠度计算冲突概率

**新增方法**:

1. `estimate_consensus_confidence()` - 估计共识决策的置信度
2. `_calculate_historical_agreement()` - 计算Agent间的历史一致性
3. `resolve_conflict_with_confidence()` - 解决冲突并返回置信度信息

---

## 三、预期效果

### 3.1 可验证的可靠性
- 所有精度报告现在包含置信区间，用户可验证精度声明
- 避免"精度虚标"问题

### 3.2 验证驱动学习
- 假说验证结果反馈到置信度计算
- 模式发现置信度根据历史验证成功率校准
- 优先级计算根据验证结果调整

### 3.3 交叉验证机制
- 关键决策使用多方法交叉验证
- 共识机制包含置信度报告
- 模型差异可被预测和报告

### 3.4 3-Agent架构强化
- **DataAgent** (data_miner.py): 负责数据挖掘，报告带置信区间
- **AnalysisAgent** (hypothesis_tester.py): 负责分析验证，包含交叉验证
- **ExecutionAgent** (observatory_linker.py): 负责执行决策，包含不确定性传播

---

## 四、修改文件清单

| 文件 | 修改类型 | 主要变更 |
|------|---------|---------|
| `discovery_tracker.py` | 增强 | 添加ConfidenceInterval类、交叉验证方法、自我进化逻辑 |
| `data_miner.py` | 增强 | 添加模式置信区间、Bootstrap/K折验证、验证反馈更新 |
| `observatory_linker.py` | 增强 | 添加优先级置信区间计算、Monte Carlo不确定性传播、交叉验证 |
| `hypothesis_tester.py` | 增强 | 添加统计检验置信区间、验证置信度报告、反馈更新 |
| `multi_agent_coordinator.py` | 增强 | 添加共识置信度估计、历史一致性计算、冲突解决置信度 |

---

## 五、测试建议

1. **精度验证测试**: 使用已知数据集验证置信区间覆盖
   - 期望: 95%置信区间应覆盖约95%的真实值

2. **交叉验证测试**: 对比单模型 vs 交叉验证结果一致性
   - 期望: 交叉验证分数 > 0.7 表示高一致性

3. **自我进化测试**: 验证置信度随验证反馈的演变
   - 期望: 正确验证后置信度上升，错误验证后置信度下降

4. **冲突检测测试**: 验证基于历史一致性的冲突概率
   - 期望: 高历史一致性 -> 低冲突概率