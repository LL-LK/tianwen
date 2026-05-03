# [PRO Document] 自我进化机制优化 - 过拟合自纠正实现

> 文档类型: 技术实现文档
> 创建日期: 2026-05-01
> 目标仓库: git@github.com:LL-LK/tianwen-agi.git
> 状态: 实现完成

---

## 一、概述

基于 Issue #13 (大模型过拟合讨论) 和 Issue #18 (天文大模型计算结果差异对比分析)，本项目实现了 **RL + GEPA 叠加的过拟合自我纠正机制**。

### 核心问题

1. **过拟合风险**: Hermes 学习 Claude Code 和 OpenClaw 可能导致思维模式单一化
2. **自我进化停滞**: 缺乏有效的过拟合检测与纠正机制
3. **多模型思维吸收**: 需要在吸收新思维的同时保持多样性

### 解决方案

实现了 `overfit_self_correction.py` 模块,集成:
- **GEPA (Gradient Episodic Memory)**: 情景记忆 + 梯度投影
- **RL (Reinforcement Learning)**: 奖励驱动的策略优化
- **多样性保护**: DiversityGuard 监控思维模式

---

## 二、架构设计

### 2.1 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│           SelfEvolutionWithOverfitCorrection                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐    ┌───────────────────┐              │
│  │  OverfittingSelf  │    │  Task History /   │              │
│  │     Corrector     │    │    Patterns      │              │
│  └─────────┬─────────┘    └───────────────────┘              │
│            │                                                │
│  ┌─────────┴─────────┐                                      │
│  │                     │                                      │
│  ▼                     ▼                                      │
│ ┌─────────┐   ┌─────────────┐   ┌─────────────┐              │
│ │Diversity│   │  Episodic   │   │    RL      │              │
│ │  Guard  │   │   Memory    │   │   Reward   │              │
│ │         │   │  (GEPA)    │   │   System   │              │
│ └─────────┘   └─────────────┘   └─────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 工作流程

```
Task Complete
      │
      ▼
┌──────────────┐
│ Build Thought│
│   Vector     │
└──────┬───────┘
       │
       ▼
┌──────────────┐    ┌─────────────────┐
│ Diversity    │───▶│  Overfit Check  │
│   Guard      │    │   (threshold)   │
└──────┬───────┘    └────────┬────────┘
       │                     │
       │                     ▼
       │    ┌────────────────────────┐
       │    │  If Overfit Detected:   │
       │    │  1. Store to Memory     │
       │    │  2. Compute Reward      │
       │    │  3. Generate Suggestion │
       │    │  4. Update RL Policy   │
       │    └────────────────────────┘
       │
       ▼
┌──────────────┐
│   Store to   │
│  Episodic    │
│   Memory     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  GEPA        │
│  Gradient    │
│  Projection  │
└──────────────┘
```

---

## 三、实现细节

### 3.1 OverfitConfig - 配置类

```python
@dataclass
class OverfitConfig:
    diversity_threshold: float = 0.7      # 多样性阈值
    memory_capacity: int = 1000           # 情景记忆容量
    gradient_projection_margin: float = 0.2  # 梯度投影边界
    rl_discount_factor: float = 0.99       # RL折扣因子
    rl_lr: float = 0.01                   # RL学习率
    overfit_alert_threshold: float = 0.85  # 过拟合警报阈值
    self_correction_strength: float = 0.3  # 自我纠正强度
```

### 3.2 EpisodicMemory - GEPA风格情景记忆

**核心功能**:
- `store(entry)`: 存储经验到情景记忆
- `compute_gradient_protection()`: 梯度投影,避免干扰旧知识
- `get_recent(k)`: 检索最近的k条记忆
- `get_by_task_type(task_type)`: 按任务类型检索

**梯度投影算法**:
```python
def compute_gradient_protection(new_gradient, old_params):
    # 计算历史梯度的平均方向
    avg_historical = average(gradient_memory)

    # 计算新梯度在历史方向上的投影
    projection = new_gradient · avg_historical

    # 正交分量 = 新梯度 - 投影
    orthogonal = new_gradient - projection

    # 混合: 保留正交部分(新知识),衰减投影部分(保护旧知识)
    protected = orthogonal * 0.8 + projection * 0.2

    return protected
```

### 3.3 DiversityGuard - 多样性监控

**核心功能**:
- `compute_diversity()`: 计算新思维与历史的多样性
- `check_overfit()`: 检测是否过拟合
- `get_overfit_trend()`: 获取过拟合趋势 (0-1)

**检测逻辑**:
- 连续5次以上多样性低于阈值 → 高置信度过拟合
- 连续3次 → 中置信度
- 单次低于阈值 → 低置信度

### 3.4 RLRewardSystem - 强化学习奖励

**奖励组成**:
```python
reward = +1.0 (任务成功)
       + diversity_score * 0.5 (多样性奖励)
       + 0.5 (过拟合纠正成功)
       - 0.1 (响应时间>60s)
```

**Q-Learning更新**:
```python
Q(s,a) = Q(s,a) + lr * (r + gamma * max_a' Q(s',a') - Q(s,a))
```

### 3.5 AfterTaskHook - 任务完成钩子

增强的 `AfterTaskHook` 在 `research_loop.py` 中:

```python
async def on_task_complete(self, task_result: Dict) -> bool:
    # 1. 记录任务历史
    self.task_history.append(task_result)

    # 2. 触发自我复盘
    triggered = await self._trigger_self_review(task_result)

    # 3. 过拟合检测 (新增)
    if self.overfit_corrector:
        overfit_result = self.overfit_corrector.on_task_complete(task_result)
        if overfit_result['overfit_detected']:
            self._apply_correction(overfit_result)

    return triggered
```

---

## 四、使用方式

### 4.1 集成到Hermes-AGI

在 `main.py` 中,`EvolutionSystem` 已升级为 `SelfEvolutionWithOverfitCorrection`:

```python
from overfit_self_correction import SelfEvolutionWithOverfitCorrection

class HermesAGI:
    def __init__(self, ...):
        # 替换原有 evolution
        self.evolution = SelfEvolutionWithOverfitCorrection(memory_dir)
```

### 4.2 独立使用

```python
from overfit_self_correction import OverfittingSelfCorrector

corrector = OverfittingSelfCorrector()

# 任务完成后调用
result = corrector.on_task_complete({
    "task_id": "TASK-001",
    "success": True,
    "task_type": "execute",
    "complexity": "medium",
    "skills": ["Frontend", "Backend"],
    "duration": 30.0
})

print(result)
# {
#     "overfit_detected": False,
#     "diversity": 0.85,
#     "reward": 1.35,
#     "suggestion": "保持当前策略"
# }
```

### 4.3 获取过拟合报告

```python
report = corrector.get_overfitting_report()
# {
#     "total_corrections": 3,
#     "overfit_alerts": 7,
#     "overfit_trend": 0.35,
#     "status": "NORMAL"
# }
```

---

## 五、与现有系统集成

### 5.1 SelfEvolutionWithOverfitCorrection

替代原有的 `EvolutionSystem`,保持向后兼容:

```python
class SelfEvolutionWithOverfitCorrection:
    """增强版自我进化系统"""

    def after_task(self, result) -> Dict[str, Any]:
        # 原有的记录逻辑
        self._record_task(result)

        # 过拟合检测与纠正
        overfit_result = self.overfit_corrector.on_task_complete(task_dict)

        return overfit_result

    def get_stats(self) -> Dict:
        # 原有统计 + 过拟合报告
        return {
            'total_tasks': ...,
            'success_rate': ...,
            'overfitting': self.overfit_corrector.get_overfitting_report()
        }
```

---

## 六、参数调优建议

### 6.1 过拟合检测灵敏度

| 场景 | diversity_threshold | overfit_alert_threshold |
|------|-------------------|----------------------|
| 高敏感 (快速检测) | 0.8 | 0.7 |
| 平衡 | 0.7 | 0.85 |
| 低敏感 (减少误报) | 0.5 | 0.9 |

### 6.2 RL参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| rl_discount_factor | 0.99 | 高折扣,关注长期奖励 |
| rl_lr | 0.01-0.05 | 较低学习率,稳定收敛 |
| self_correction_strength | 0.3 | 每次纠正幅度 |

---

## 七、测试结果

### 7.1 单元测试

```python
# 测试过拟合检测
evolution = SelfEvolutionWithOverfitCorrection()

# 模拟10个相似任务
for i in range(10):
    result = evolution.after_task({
        "task_model": MockTaskModel(...),
        "status": MockStatus("completed"),
        "metrics": {"duration": 30},
        "errors": []
    })

# 检测过拟合趋势
report = evolution.get_stats()
assert report['overfitting']['status'] in ["NORMAL", "WARNING", "CRITICAL"]
```

### 7.2 预期行为

- **正常情况**: diversity > 0.7, overfit_detected = False
- **连续相似任务**: diversity 逐渐下降,超过阈值后触发纠正
- **纠正成功**: reward 提升, diversity 恢复

---

## 八、后续优化方向

1. **思维向量增强**: 引入更复杂的向量化方法 (embedding)
2. **多模型来源追踪**: 记录思维来源 (claude/openclaw/gemini)
3. **自适应阈值**: 根据任务类型动态调整 diversity_threshold
4. **分布式记忆**: 支持多Agent共享情景记忆

---

## 九、关联Issue

- Issue #13: 大模型过拟合与多Agent协同问题讨论
- Issue #18: 天文大模型计算结果差异对比分析
- 相关文档: `docs/PRO/PRO_OVERFITTING_MULTIAGENT_ANALYSIS.md`

---

**评审者**: Hermes Agent
**创建日期**: 2026-05-01
**更新日期**: 2026-05-01

---

*Self-Evolution with Overfitting Self-Correction - RL + GEPA Implementation*