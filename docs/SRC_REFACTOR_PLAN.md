# 天问-AGI src/ 架构重构方案
> 版本: v1.0 | 状态: 提案 | 日期: 2026-05-09

---

## 一、现状问题诊断

### 1.1 同名不同内容问题（18组）

模块在多个目录重复，但职责边界不清晰：

| 模块 | 位置A | 位置B | 问题 |
|------|-------|-------|------|
| `discovery.py` | agents/ | research/ | 两套独立发现系统 |
| `literature.py` | agents/ | research/ | 两套文献调研系统 |
| `linker.py` | research/ | telescope/ | 望远镜链接逻辑分散 |
| `pipeline.py` | astronomy/ | data/ | 天体检测 vs 数据分析 |
| `enhanced_scheduler.py` | observation/ | telescope/ | 调度算法重复 |
| `scheduler.py` | observation/ | telescope/ | 调度器重复 |
| `rl_scheduler.py` | learning/ | observation/ | 强化学习调度重复 |
| `analyzer.py` | astronomy/ | data/ | 分析逻辑重复 |
| `sky_chart.py` | astronomy/ | observation/ | 天球图生成重复 |
| `mcp.py` | agents/ | utils/ | MCP 客户端重复 |
| `self_review.py` | agents/ | utils/ | 自我复盘重复 |
| `skill_integration.py` | learning/ | utils/ | 技能注册重复 |
| `skill_tester.py` | learning/ | utils/ | 技能测试重复 |
| `session.py` | memory/ | web/ | 会话管理重复 |
| `models.py` | data/ | utils/ | 模型定义重复 |
| `dream.py` | core/ | learning/ | 梦境/幻想系统重复 |

### 1.2 架构层问题

**问题A: 三引擎定位不清**
- `src/core/` 只有 `cognitive.py` 和 `reasoning.py`，缺少 `execution.py`
- `src/agents/tri_agent.py` 可能是三引擎的另一种实现
- CLAUDE.md 描述的 `runtime/` 目录不存在

**问题B: agents/ 职责混乱**
`src/agents/` 混合了:
- 领域Agent: `literature.py`, `hypothesis_gen.py`, `observation.py`, `discovery.py`, `data_miner.py`
- 运行时引擎: `coordinator.py`, `workflow_engine.py`
- 基础设施: `browser.py`, `mcp.py`, `agent_enhancements.py`

**问题C: observation/ vs research/ 边界模糊**
- observation/ 已有 `workflow.py`, research/ 又有 `loop.py`，功能重叠
- 望远镜执行器在 `observation/executor.py` 和 `telescope/` 都有

**问题D: telescope/ vs observation/ 职责不清**
- 望远镜抽象层 (`telescope/linker.py`, `mcp_client.py`, `seestar_client.py`) 
- 望远镜调度器 (`telescope/scheduler.py`, `enhanced_scheduler.py`)
- 观测执行器 (`observation/executor.py`)
- 三者关系未理清

**问题E: CLAUDE.md 与实际代码脱节**
- CLAUDE.md 说 `runtime/` 目录存在，包含 `reasoning_engine.py`, `vector_memory.py`
- 实际代码在 `src/core/`, `src/memory/`, `src/reasoning_engine.py` (根目录)

---

## 二、重构目标

1. **清晰的分层架构**: 输入层 → 认知层 → 规划层 → 执行层 → 输出层
2. **单一职责**: 每个模块只在一个地方存在
3. **统一入口**: CLAUDE.md 与实际代码结构一致
4. **可导航性**: 新人能快速理解代码组织

---

## 三、目标架构

### 3.1 目录结构

```
src/
├── core/                    # 核心引擎（三引擎）
│   ├── __init__.py
│   ├── cognitive.py         # 认知引擎（已存在）
│   ├── planning.py          # 规划引擎（从 agents/tri_agent.py 提取）
│   ├── execution.py         # 执行引擎（从 agents/ 提取）
│   └── reasoning.py         # 推理引擎（已存在，从 reasoning_engine.py 移入）
│
├── agents/                  # 领域智能体
│   ├── __init__.py
│   ├── literature.py        # 文献调研Agent（合并 agents/ + research/）
│   ├── hypothesis.py        # 假说生成Agent
│   ├── discovery.py         # 发现追踪Agent（合并 agents/ + research/）
│   ├── data_miner.py        # 数据挖掘Agent（保留）
│   ├── self_review.py       # 自我复盘Agent（合并 agents/ + utils/）
│   └── embodied.py          # 具身智能Agent（从 observation/embodied.py 移入）
│
├── observation/             # 观测闭环系统
│   ├── __init__.py
│   ├── scheduler.py         # 观测调度（合并 observation/ + telescope/）
│   ├── enhanced_scheduler.py # 增强调度（合并）
│   ├── workflow.py          # 观测工作流（合并 observation/ + research/loop.py）
│   └── executor.py          # 执行器（保留）
│
├── telescope/               # 望远镜抽象层（仅保留设备控制）
│   ├── __init__.py
│   ├── linker.py            # 望远镜链接（合并 telescope/ + research/linker.py）
│   ├── mcp_client.py        # MCP客户端（保留）
│   ├── seestar_client.py    # Seestar客户端（保留）
│   └── simulator.py         # 望远镜模拟器（保留）
│
├── astronomy/               # 天文算法（仅保留专业算法）
│   ├── __init__.py
│   ├── pipeline.py          # 天体检测管道（保留）
│   ├── analyzer.py          # 天文数据分析（合并 astronomy/ + data/）
│   ├── sky_chart.py         # 天球图（合并 astronomy/ + observation/）
│   ├── platesolver.py       # _plate solving（保留）
│   └── catalog.py           # 星表（保留）
│
├── data/                    # 数据管道（仅保留非天文数据）
│   ├── __init__.py
│   ├── pipeline.py          # 数据分析管道（合并 astronomy/ + data/）
│   ├── kepler_client.py     # Kepler数据客户端（保留）
│   └── weather.py           # 天气数据（保留）
│
├── memory/                  # 记忆系统
│   ├── __init__.py
│   ├── vector.py            # 向量记忆
│   ├── rag.py               # RAG系统
│   ├── persistence.py       # 持久化
│   └── session.py           # 会话管理（合并 memory/ + web/）
│
├── learning/                # 学习进化
│   ├── __init__.py
│   ├── rl_scheduler.py     # 强化学习调度（合并 learning/ + observation/）
│   ├── overfit_correction.py # 过拟合修正
│   └── skill_integration.py # 技能注册（合并 learning/ + utils/）
│
├── api/                     # API层
│   ├── __init__.py
│   └── endpoints/           # 端点（未来扩展）
│
├── web/                     # Web界面（精简）
│   ├── __init__.py
│   ├── dashboard.py         # 仪表板
│   └── bridge.py           # WebSocket桥接
│
├── utils/                   # 工具（精简后）
│   ├── __init__.py
│   ├── mcp.py              # MCP工具（保留，与agents/mcp.py合并）
│   └── models.py            # 模型定义（合并 data/ + utils/）
│
├── main.py                  # 主入口（保留）
└── server.py                 # 服务器（保留）
```

### 3.2 需要删除/归档的模块

| 文件 | 原因 |
|------|------|
| `src/reasoning_engine.py` | 功能已由 `core/reasoning.py` 替代 |
| `src/runtime_logger.py` | 可并入 `core/` |
| `src/telescope/scheduler.py` | 已并入 `observation/scheduler.py` |
| `src/telescope/enhanced_scheduler.py` | 已并入 `observation/enhanced_scheduler.py` |
| `src/research/linker.py` | 已并入 `telescope/linker.py` |
| `src/research/loop.py` | 已并入 `observation/workflow.py` |
| `src/research/literature.py` | 已并入 `agents/literature.py` |
| `src/research/discovery.py` | 已并入 `agents/discovery.py` |
| `src/agents/literature.py` | 与 `research/literature.py` 合并后替代 |
| `src/agents/discovery.py` | 与 `research/discovery.py` 合并后替代 |
| `src/data/analysis.py` | 已并入 `astronomy/analyzer.py` |
| `src/observation/sky_chart.py` | 已并入 `astronomy/sky_chart.py` |
| `src/observation/rl_scheduler.py` | 已并入 `learning/rl_scheduler.py` |
| `src/learning/dream.py` | 已并入 `core/dream.py` |
| `src/web/session.py` | 已并入 `memory/session.py` |
| `src/utils/self_review.py` | 已并入 `agents/self_review.py` |
| `src/utils/skill_tester.py` | 已并入 `learning/skill_tester.py` |

### 3.3 CLAUDE.md 更新要点

CLAUDE.md 需要完全重写，对齐实际 `src/` 结构：
- 删除 `runtime/` 目录引用
- 确认核心引擎在 `src/core/`
- 确认技能库在 `F:/skill/`（而非项目内）

---

## 四、重构执行计划

### 阶段1: 备份与准备（D+0）
- [ ] 创建 `docs/archive/src-pre-refactor/` 备份当前 src/ 快照
- [ ] 更新 CLAUDE.md 添加重构说明
- [ ] git commit "refactor: start src/ architecture refactoring"

### 阶段2: 合并同名模块（D+1~3）

**合并顺序（按依赖关系）:**

1. **scheduler** (observation + telescope) → `observation/scheduler.py`
2. **enhanced_scheduler** (observation + telescope) → `observation/enhanced_scheduler.py`
3. **linker** (research + telescope) → `telescope/linker.py`
4. **rl_scheduler** (learning + observation) → `learning/rl_scheduler.py`
5. **sky_chart** (astronomy + observation) → `astronomy/sky_chart.py`
6. **analyzer** (astronomy + data) → `astronomy/analyzer.py`
7. **pipeline** (astronomy + data) → 确认已是不同功能，保留
8. **literature** (agents + research) → 需内容对比后合并
9. **discovery** (agents + research) → 需内容对比后合并

**合并原则：**
- 优先保留功能更完整的版本
- 另一个版本的内容追加到尾部，标注 `### [OBSOLETE MERGED]`
- 所有 import 路径同步更新

### 阶段3: 清理删除（D+4~5）
- 删除所有被合并的重复文件
- 运行 `python -m py_compile` 验证语法
- 运行 `python -c "import src"` 验证包结构

### 阶段4: CLAUDE.md 重写（D+6~7）
- 完全重写 `CLAUDE.md`，对齐 `src/` 实际结构
- 添加架构图和模块职责说明

### 阶段5: 测试验证（D+8）
- 运行 `pytest tests/` 验证功能
- 端到端测试观测闭环

---

## 五、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| import 路径断裂 | 运行时错误 | 每个阶段运行 `python -c "import src"` |
| 合并时丢失功能 | 功能退化 | 保留备份，恢复时用 `git checkout` |
| 工作量大 | 进度延迟 | 分阶段执行，每阶段独立 commit |
| 同名但不同功能 | 错误合并 | 合并前先对比文件内容哈希 |

---

## 六、优先级决策

| 模块 | 工作量 | 优先级 | 理由 |
|------|--------|--------|------|
| CLAUDE.md 重写 | 低 | P0 | 入口文档必须准确 |
| scheduler 合并 | 低 | P0 | 高频使用，重复最严重 |
| literature 合并 | 中 | P1 | 核心功能，影响大 |
| discovery 合并 | 中 | P1 | 核心功能，影响大 |
| 其他同名模块 | 低 | P2 | 次要重复 |
| telescope/linker 合并 | 中 | P1 | 望远镜控制核心 |
| CLAUDE.md 重写后的完整清理 | 高 | P2 | 架构完整性 |

---

**文档状态**: 提案，待评审后执行
**下一步**: 提交到 trae 分支，等待确认后开始阶段1
