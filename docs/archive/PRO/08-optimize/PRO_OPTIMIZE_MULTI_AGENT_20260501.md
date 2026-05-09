# PRO: Multi-Agent Coordination Optimization

**Date**: 2026-05-01
**Author**: Claude (Anthropic)
**Related Issues**: #13, #15, #20
**Status**: Implemented

---

## 1. 问题分析

### Issue #13: 多Agent并行架构
- 当前架构：3-Agent (arxiv + github + data)
- 问题：上下文卡顿、缺少观测专家角色
- 目标：扩展为4-Agent并行协调

### Issue #15: 闭环流程缺失
- 缺失模块：数据挖掘、观测指导
- 当前闭环成功率：~8%
- 目标：提升到30%+

### Issue #20: 功能完整度评估
- 当前功能完整度：42/100
- P0缺失：数据挖掘、观测指导
- 需要4-Agent并行架构支持

---

## 2. 当前架构分析

### runtime/multi_agent_coordinator.py (v1.0)
```
ArxivSearchAgent ─┐
                  ├─► VectorDeduplicator ─► QualityFilter ─► 结果输出
GithubSearchAgent ┤
DataSearchAgent  ─┘
```

**问题**:
1. 缺少Observation Specialist角色
2. 没有专门的Result Integrator
3. 通信协议简陋
4. 故障隔离不完善

### runtime/multi_agent_search.py
独立搜索协调器，3-Agent并行，与coordinator架构重叠。

---

## 3. GitHub最新模式调研

### 发现的最新框架
| 项目 | 特点 | 借鉴点 |
|-----|------|--------|
| forge-orchestrator | 自进化多Agent编排器 | PR审核、冲突解决 |
| alas | Rust实现并行Agent编排 | 高性能、并发控制 |
| SynapsCLI | 终端原生Agent运行时 | 自主监督 |

---

## 4. 优化方案

### 4.1 架构升级：4-Agent并行

```
                    ┌─────────────────────────────┐
                    │   MultiAgentCoordinator     │
                    │   (Result Integrator)       │
                    └─────────────────────────────┘
                                    │
    ┌───────────────┬───────────────┼───────────────┬───────────────┐
    │               │               │               │               │
    ▼               ▼               ▼               ▼               │
┌─────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐         │
│ arxiv   │   │  github   │   │   data    │   │observing  │         │
│searcher │   │ searcher  │   │ searcher  │   │specialist │         │
└────┬────┘   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘         │
     │              │              │              │                │
     └──────────────┴──────────────┴──────────────┘                │
                              │                                   │
                    ┌─────────▼─────────┐                        │
                    │  Result Integrator │◄───────────────────────┘
                    │  (智能合并+去重)    │
                    └───────────────────┘
```

### 4.2 新增组件

#### ResultIntegrator
```python
class ResultIntegrator:
    """结果整合器 - 合并多Agent结果"""
    - 智能合并相同/相似结果
    - 基于来源置信度加权
    - 生成综合报告
```

#### Communication Protocol
```python
class AgentProtocol:
    """Agent通信协议"""
    - Message types: TASK, RESULT, HEARTBEAT, SYNC
    - Timeout handling
    - Retry mechanism
```

#### Observation Specialist Agent
```python
class ObservationSpecialist(BaseSearchAgent):
    """观测专家Agent - 搜索天文观测数据"""
    - TESS/Kepler API
    - 望远镜可见性
    - 调度优先级
```

### 4.3 4-Agent角色定义

| Agent | 职责 | 数据源 |
|-------|------|-------|
| ArxivSearcher | 学术论文搜索 | arXiv |
| GithubSearcher | 代码/项目搜索 | GitHub |
| DataSearcher | 科学数据搜索 | NASA, SIMBAD |
| ObservationSpecialist | 观测数据/调度 | TESS, Kepler |

---

## 5. 实现状态

### Phase 1: 架构重构 ✅
- [x] 添加ObservationSpecialist Agent
- [x] 实现ResultIntegrator
- [x] 改进通信协议 (LLM路由更新)

### Phase 2: 功能增强
- [x] 4-Agent并行执行 (max_parallel=4)
- [ ] 超时和重试机制 (待实现)
- [ ] 结果智能合并 (ResultIntegrator完成)

### Phase 3: 集成测试
- [ ] 与data_miner.py集成 (待测试)
- [ ] 与research_observatory_linker.py集成 (待测试)
- [ ] 端到端闭环测试 (待测试)

---

## 6. 实际代码变更

### 变更文件
1. `multi_agent_search.py` - 主要优化文件

### 变更内容

#### 1. 新增 ObservationSpecialist Agent
```python
class ObservationSpecialist(BaseSearchAgent):
    """观测专家Agent - 搜索天文观测数据和调度信息"""
    def __init__(self):
        super().__init__(
            agent_id=f"obs_{uuid.uuid4().hex[:8]}",
            agent_type="observation"
        )
```

#### 2. 新增 ResultIntegrator 类
```python
class ResultIntegrator:
    """结果整合器 v2.0 - 智能合并多Agent结果"""
    SOURCE_WEIGHTS = {
        "arxiv": 1.0,
        "github": 0.8,
        "nasa": 1.0,
        "observation": 0.9
    }

    @classmethod
    def integrate(cls, agent_results: Dict[str, AgentResult]) -> Dict[str, Any]:
        # 按来源置信度加权排序
        pass

    @classmethod
    def generate_report(cls, integrated: Dict[str, Any], query: str) -> str:
        # 生成综合报告
        pass
```

#### 3. 4-Agent并行协调器更新
```python
class MultiAgentSearchCoordinator:
    def __init__(self, max_parallel: int = 4):  # 从3改为4
        self.result_integrator = ResultIntegrator()

    async def initialize(self):
        self.agents = [
            ArxivSearchAgent(),
            GithubSearchAgent(),
            DataSearchAgent(),
            ObservationSpecialist()  # v2.0 新增
        ]
```

#### 4. LLM路由更新
```python
KEYWORD_MAPPING = {
    # ...原有...
    "observation": ["observation", "tess", "scheduling", "可见性", "调度"]
}
```

---

## 7. 预期效果

| 指标 | 当前 | 优化后 |
|-----|------|-------|
| Agent数量 | 3 | 4 |
| 并行度 | 3 | 4 |
| 故障隔离 | 基础 | 完善 |
| 结果整合 | 简单去重 | 智能合并+置信度加权 |
| 闭环成功率 | ~8% | ~25-30% |

---

## 8. 待完成工作

1. 超时和重试机制
2. 与 data_miner.py 集成测试
3. 与 research_observatory_linker.py 集成测试
4. 端到端闭环测试

---

## 9. 关联文档

- Issues: #13, #15, #20
- 相关文件:
  - `runtime/multi_agent_coordinator.py` - 研究Agent协作系统
  - `multi_agent_search.py` - 搜索协调器 (已优化)
  - `runtime/data_miner.py` - 数据挖掘模块
  - `runtime/research_observatory_linker.py` - 研究-观测联动