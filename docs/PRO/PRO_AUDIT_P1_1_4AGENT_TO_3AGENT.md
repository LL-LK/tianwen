# PRO审计文档: P1-1 4-Agent→3-Agent架构重构
**审计时间**: 2026-05-01 15:05 CST (北京时间)
**优先级**: P1 (重要)
**关联Issue**: #20

---

## 一、现状分析

### 1.1 当前Agent架构

**create_research_team()创建5个Agent**:
| Agent | 角色 | 职责 | 问题 |
|-------|------|------|------|
| coordinator | COORDINATOR | 任务分解协调 | 过度设计 |
| planner | PLANNER | 观测计划 | 未对接调度 |
| researcher | RESEARCHER | 文献调研 | 已有literature_researcher.py |
| hypothesis_generator | HYPOTHESIS_GENERATOR | 假说生成 | 未被有效利用 |
| reviewer | REVIEWER | 评审反馈 | 框架存在但调用少 |

### 1.2 Claude建议的3-Agent架构

| Agent | 职责 | 对应模块 |
|-------|------|---------|
| **数据Agent** | Kepler/TESS数据获取 | kepler_exoplanet_client.py |
| **分析Agent** | 数据挖掘+假说验证 | data_miner.py + hypothesis_tester.py |
| **执行Agent** | 望远镜控制+观测执行 | observatory_linker.py + observation_executor.py |

### 1.3 重构原则

**问题**: 5-Agent架构导致:
- 上下文复杂度高
- 角色职责重叠
- 执行效率低下

**目标**: 简化为3-Agent，直接对应3个核心里程碑:
```
M1: 数据挖掘     → 分析Agent
M2: 观测指导     → 执行Agent
M3: 观测执行     → (数据Agent提供数据支持)
```

---

## 二、技术方案

### 2.1 重构后的Agent定义

```python
class AgentRole(Enum):
    """3-Agent架构"""
    DATA_AGENT = "data_agent"      # 数据获取 (原kepler_exoplanet_client)
    ANALYZER_AGENT = "analyzer_agent"  # 分析挖掘 (原data_miner + hypothesis_tester)
    EXECUTOR_AGENT = "executor_agent"  # 执行控制 (原observatory_linker + observation_executor)
```

### 2.2 数据流重构

**重构前 (5-Agent)**:
```
Coordinator → Planner → Researcher → Analyzer → Reviewer
                    (复杂的数据依赖链)
```

**重构后 (3-Agent)**:
```
数据Agent ──→ 分析Agent ──→ 执行Agent
    │              │              │
    ↓              ↓              ↓
Kepler/TESS    假说验证       望远镜控制
```

### 2.3 核心代码修改

**修改multi_agent_coordinator.py**:

```python
# 新增3个Agent角色
class AgentRole(Enum):
    DATA_AGENT = "data_agent"
    ANALYZER_AGENT = "analyzer_agent"
    EXECUTOR_AGENT = "executor_agent"

# 修改create_research_team()
def create_research_team_3(self, team_name: str) -> Dict[str, ResearchAgent]:
    """创建3-Agent研究团队"""
    team = {}

    # 数据Agent - 负责数据获取
    team["data_agent"] = self.create_agent(
        name=f"{team_name}_DataAgent",
        role=AgentRole.DATA_AGENT,
        expertise=["kepler_api", "tess_api", "data_collection"]
    )

    # 分析Agent - 负责数据分析
    team["analyzer_agent"] = self.create_agent(
        name=f"{team_name}_AnalyzerAgent",
        role=AgentRole.ANALYZER_AGENT,
        expertise=["data_mining", "hypothesis_testing", "statistical_analysis"]
    )

    # 执行Agent - 负责观测执行
    team["executor_agent"] = self.create_agent(
        name=f"{team_name}_ExecutorAgent",
        role=AgentRole.EXECUTOR_AGENT,
        expertise=["telescope_control", "scheduling", "observation_execution"]
    )

    return team
```

---

## 三、实施计划

### 3.1 分阶段实施

| 阶段 | 行动 | 说明 |
|------|------|------|
| 1 | 添加新AgentRole枚举 | 保留旧角色用于兼容 |
| 2 | 实现create_research_team_3() | 新3-Agent工厂方法 |
| 3 | 修改任务分配逻辑 | 适配3-Agent数据流 |
| 4 | 添加Agent间通信协议 | 定义消息格式 |
| 5 | 废弃旧5-Agent方法 | 标记为deprecated |

### 3.2 验证清单

| 验证项 | 预期结果 |
|--------|---------|
| 3-Agent团队创建成功 | 3个Agent实例正确创建 |
| 数据流正确流转 | DataAgent → AnalyzerAgent → ExecutorAgent |
| 上下文长度降低 | 比5-Agent减少30%+ |
| 任务完成时间 | 效率提升20%+ |

---

## 四、文献来源

| 项目 | URL | 说明 |
|------|-----|------|
| 天问-AGI Issue #20 | https://github.com/LL-LK/tianwen-agi/issues/20 | 4→3-Agent讨论 |
| PRO_CLAUDE_DEEPTHINK_ISSUE20.md | 本地文档 | Claude深度思考 |

---

## 五、审计结论

| 维度 | 评估 |
|------|------|
| 当前状态 | ⚠️ 5-Agent过度设计 |
| 重构价值 | ✅ 直接对应3个里程碑 |
| 实施难度 | 中 - 需修改核心协调逻辑 |
| 优先级 | P1 - 重要但不紧急 |

**建议**:
1. 保留旧create_research_team()用于兼容
2. 实现新的create_research_team_3()
3. 通过feature flag切换架构
4. 验证后废弃旧方法

---

**审计状态**: ✅ 完成
**审计人**: Hermes Agent (产品经理视角)
**待办**: 等待Claude实现或指示
