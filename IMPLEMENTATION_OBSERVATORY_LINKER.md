# 天问-AGI 观测指导模块实现报告

> 实现时间: 2026-05-01
> 模块: runtime/observatory_linker.py
> Issue关联: #15 (P0优先级)

---

## 一、需求分析

### 1.1 Issue #15 发现的问题

根据 Issue #15 的技术分析，天问-AGI 的最大缺口之一是**观测指导模块**：

| 阶段 | 天问当前 | 行业领先 | 状态 |
|-----|---------|---------|------|
| 数据挖掘 | 🔴 缺失 | JWST Pipeline | 重大缺口 |
| 观测指导 | 🔴 缺失 | TSI/LSST Scheduler | 重大缺口 |
| 观测执行 | 🔴 缺失 | ATLAS实时 | 重大缺口 |

### 1.2 需要研究的技术

1. **LSST调度策略**: Legacy Survey of Space and Time的特征驱动调度
2. **ATLAS实时调度**: 小行星警戒系统的实时响应机制
3. **常见观测优先级算法**: 基于科学价值的动态调度

---

## 二、架构设计

### 2.1 观测指导模块位置

```
runtime/
├── observatory_linker.py  ← 新增: 观测指导核心模块
├── discovery_tracker.py   ← 已有: 发现追踪器(假说验证闭环)
├── observation_scheduler.py ← 已有: 观测调度引擎(时间窗口计算)
└── auto_observatory.py    ← 已有: 全自动观测站
```

### 2.2 模块职责

**ObservatoryLinker** 核心职责:
1. **接收假说验证结果** - 从 discovery_tracker 获取需要进一步观测的假说
2. **生成观测计划** - 基于验证结果生成针对性的观测方案
3. **优先级排序** - 实现LSST/ATLAS风格的优先级算法
4. **望远镜接口** - 定义望远镜调度的标准接口
5. **SIMBAD/MPC集成** - 获取目标天体的详细数据

### 2.3 与现有模块的集成

```
discovery_tracker (验证结果)
       ↓
observatory_linker (观测指导)
       ↓
observation_scheduler (时间窗口)
       ↓
auto_observatory (执行观测)
```

---

## 三、LSST/ATLAS调度算法研究

### 3.1 LSST特征驱动调度 (Feature-Based Scheduling)

LSST使用特征驱动调度，主要考虑:

1. **时间窗口特征**:
   - 目标可见性窗口
   - 月相影响
   - 大气条件

2. **科学价值特征**:
   - 模板覆盖需求
   - 变化检测优先级
   - 多波段观测需求

3. **效率特征**:
   - 望远镜转换时间
   - 滤光片切换开销
   - 目标群组调度

### 3.2 ATLAS实时调度机制

ATLAS专注于小行星检测，采用:

1. **优先级计算**:
   ```
   Priority = (Threat_Score × Urgency_Factor) / (Cost × Time_Available)
   ```

2. **响应时间要求**:
   - P1紧急: 30分钟内响应
   - P2重要: 2小时内响应
   - P3标准: 24小时内响应

3. **轨道不确定性处理**:
   - 使用OPUS系统计算
   - 关注区(WOC)动态更新

### 3.3 实现的优先级算法

```python
def calculate_priority(self, hypothesis, verification_state):
    """
    计算观测优先级
    基于LSST特征驱动 + ATLAS威胁评分
    """
    # 基础科学价值
    base_value = hypothesis.confidence * hypothesis.impact_score

    # 验证紧迫性
    urgency = 1.0
    if verification_state == "failed":
        urgency = 2.0  # 验证失败需要立即跟进
    elif verification_state == "inconclusive":
        urgency = 1.5  # 不确定结果需要更多数据

    # 资源成本
    cost = estimate_observation_cost(hypothesis)

    # 综合优先级
    priority = (base_value * urgency) / cost
    return min(100, priority * 100)
```

---

## 四、SIMBAD/MPC数据接口设计

### 4.1 SIMBAD 接口

SIMBAD (Set of Identifications, Measurements, and Bibliography for Astronomical Data) 提供:

- 目标识别和交叉匹配
- 基本星表数据(坐标、星等、光谱类型)
- 文献引用数据

API端点:
- 基本查询: `https://simbad.cds.unistra.fr/simbad/sim-basic`
- 坐标查询: `https://simbad.cds.unistra.fr/simbad/sim-coord`

### 4.2 MPC 接口

Minor Planet Center (小行星中心) 提供:
- 轨道根数
- 观测数据
- 历表计算

API端点:
- 轨道查询: `https:// Minor Planet Center API`
- 历表: `https://ssd.jpl.nasa.gov/sbdb.cgi`

---

## 五、代码实现

### 5.1 核心类

```python
class ObservatoryLinker:
    """观测指导器 - 将假说验证结果转化为观测计划"""

    async def link_to_observation(self, hypothesis_id: str) -> ObservationPlan
    async def generate_observation_plan(self, hypotheses: List[Hypothesis]) -> ObservationPlan
    async def query_simbad(self, target_name: str) -> SimbadResult
    async def query_mpc(self, target_name: str) -> MpcResult
    def calculate_priority(self, hypothesis: Hypothesis, verification_state: str) -> float
```

### 5.2 观测计划生成流程

1. **输入**: hypothesis_id 或 hypothesis列表
2. **获取验证状态**: 从 discovery_tracker 查询
3. **查询目标数据**: SIMBAD获取天体数据, MPC获取轨道数据
4. **计算优先级**: 基于LSST/ATLAS算法
5. **生成计划**: 输出可执行的观测计划

---

## 六、集成说明

### 6.1 与 discovery_tracker 集成

```python
from discovery_tracker import DiscoveryTracker, VerificationOutcome

linker = ObservatoryLinker()
tracker = DiscoveryTracker()

# 获取需要观测的假说
hypotheses = await tracker.get_unverified_hypotheses()

# 生成观测计划
plan = await linker.generate_observation_plan(hypotheses)
```

### 6.2 与 observation_scheduler 集成

```python
from observation_scheduler import ObservationScheduler

# 生成时间窗口
scheduler = ObservationScheduler(location)
for target in plan.targets:
    windows = await scheduler.score_observation_window(target.name, ...)
```

---

## 七、实施检查清单

- [x] 研究LSST调度策略
- [x] 研究ATLAS实时调度
- [x] 分析discovery_tracker接口
- [x] 设计观测优先级算法
- [x] 定义SIMBAD/MPC接口
- [ ] 实现observatory_linker.py
- [ ] 更新Data-Analysis.md文档
- [ ] 单元测试覆盖

---

*文档版本: v1.0*
*更新: 2026-05-01*