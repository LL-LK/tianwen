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
├── observatory_linker.py  ← 新增: 观测指导核心模块 (v1.0)
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

已实现 `PriorityCalculator` 类：

```python
class PriorityCalculator:
    WEIGHTS = {
        "scientific_impact": 0.30,
        "verification_urgency": 0.25,
        "observability": 0.20,
        "resource_efficiency": 0.15,
        "cost_risk": 0.10
    }

    VERIFICATION_MULTIPLIERS = {
        VerificationState.REJECTED: 2.0,
        VerificationState.INCONCLUSIVE: 1.5,
        VerificationState.REVISED: 1.3,
        VerificationState.IN_PROGRESS: 1.2,
        VerificationState.PENDING: 1.0,
        VerificationState.CONFIRMED: 0.5
    }
```

---

## 四、SIMBAD/MPC数据接口设计

### 4.1 SIMBAD 接口

SIMBAD (Set of Identifications, Measurements, and Bibliography for Astronomical Data) 提供:

- 目标识别和交叉匹配
- 基本星表数据(坐标、星等、光谱类型)
- 文献引用数据

API端点:
- 基本查询: `https://simbad.cds.unistra.fr/simbad/sim-script`
- 坐标查询: `https://simbad.cds.unistra.fr/simbad/sim-coord`

已实现 `SimbadClient` 类，支持:
- `query_by_name(target_name)`: 通过名称查询
- `query_by_coords(ra, dec, radius)`: 通过坐标查询

### 4.2 MPC 接口

Minor Planet Center (小行星中心) 提供:
- 轨道根数
- 观测数据
- 历表计算

API端点:
- 轨道查询: `https://ssd.jpl.nasa.gov/sbdb.cgi`

已实现 `MpcClient` 类，支持:
- `query_by_name(target_name)`: 小行星名称查询
- `query_near_earth_objects()`: 近地天体查询
- `get_orbital_elements(designation)`: 轨道根数查询

---

## 五、代码实现清单

### 5.1 核心类

| 类名 | 功能 |
|------|------|
| `ObservatoryLinker` | 主入口：假说→观测计划转化 |
| `PriorityCalculator` | 优先级计算：LSST/ATLAS算法 |
| `SimbadClient` | SIMBAD API客户端 |
| `MpcClient` | MPC API客户端 |

### 5.2 数据结构

| 结构 | 说明 |
|------|------|
| `ObservationTarget` | 观测目标(名称、坐标、星等) |
| `ObservationRequest` | 单个观测请求(含优先级) |
| `ObservationPlan` | 完整观测计划 |
| `SimbadResult` | SIMBAD查询结果 |
| `MpcResult` | MPC查询结果 |

### 5.3 关键方法

```python
class ObservatoryLinker:
    async def link_to_observation(hypothesis_id) -> ObservationPlan
    async def generate_observation_plan(hypothesis_ids) -> ObservationPlan
    async def update_plan_priorities(plan, urgent_hypotheses) -> ObservationPlan

    # 内部方法
    async def _get_hypothesis(hypothesis_id) -> Optional[Dict]
    async def _create_observation_request(hypothesis, state) -> Optional[ObservationRequest]
    async def _resolve_target(target_name) -> Optional[ObservationTarget]
```

---

## 六、集成说明

### 6.1 与 discovery_tracker 集成

```python
from observatory_linker import ObservatoryLinker
from discovery_tracker import DiscoveryTracker

# 初始化
linker = ObservatoryLinker(discovery_tracker=DiscoveryTracker())

# 获取待验证假说生成观测计划
plan = await linker.generate_observation_plan(["hypo_001", "hypo_002"])
```

### 6.2 与 observation_scheduler 集成

```python
from observation_scheduler import ObservationScheduler

# 生成时间窗口
scheduler = ObservationScheduler(location)
for request in plan.requests:
    windows = await scheduler.score_observation_window(
        request.target.name,
        datetime.now()
    )
```

### 6.3 与 auto_observatory 集成

```python
# 完整工作流
observatory = AutoObservatory()
linker = ObservatoryLinker()

# 从观测计划获取目标
for request in plan.requests:
    observatory.config["observation_targets"].append(request.target.name)

# 执行观测
await observatory.start_observation()
```

---

## 七、文档更新

### 7.1 skills/Data-Analysis.md

已添加"天文观测指导模块 (ObservatoryLinker)"章节，包含:
- 模块概述
- 核心功能说明
- 优先级算法权重
- SIMBAD/MPC接口说明
- 与DiscoveryTracker集成示例

---

## 八、实施检查清单

- [x] 研究LSST调度策略
- [x] 研究ATLAS实时调度
- [x] 分析discovery_tracker接口
- [x] 设计观测优先级算法
- [x] 定义SIMBAD/MPC接口
- [x] 实现observatory_linker.py (v1.0)
- [x] 更新Data-Analysis.md文档
- [ ] 单元测试覆盖
- [ ] 与observation_scheduler集成测试
- [ ] 与auto_observatory集成测试

---

## 九、后续工作

### 9.1 短期 (v3.6)

1. 添加单元测试覆盖
2. 实现与observation_scheduler的时间窗口对接
3. 添加ATLAS风格的威胁评估(针对NEO)

### 9.2 中期 (v3.7)

1. 实现望远镜调度API接口
2. 添加实时天气数据集成
3. 实现多站协调调度

### 9.3 长期 (v4.0+)

1. 自主发现模式：系统独立提出并验证假说后直接调度观测
2. 跨学科推理：物理、化学、生物多学科数据融合
3. 实时观测联动：直接对接望远镜控制API

---

*文档版本: v1.1*
*更新: 2026-05-01*
*实现: ObservatoryLinker v1.0*