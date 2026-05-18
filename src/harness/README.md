# TianwenAGI Harness

天文AI Agent评测框架 - 多Agent多任务执行引擎

参考架构: **lm-evaluation-harness** + **GAIA Benchmark** + **StarWhisperED** + **NGSS**

## 架构设计

```
TianwenAGI-Harness/
├── core/                      # 核心基类
│   ├── agent.py              # Agent接口 (BaseAgent)
│   ├── task.py              # Task接口 (BaseTask)
│   └── evaluator.py         # Evaluator接口
├── protocols/                # 协议抽象层 (低耦合)
│   ├── base.py              # BaseProtocol, ProtocolRegistry
│   └── astronomy.py        # 天文专用协议
│       ├── SpectralAnalysisProtocol
│       ├── PhotometryProtocol
│       └── AstronomicalCoordinateProtocol
├── agents/                   # Agent实现
│   └── base.py              # 增强Agent基类
├── tasks/                   # 任务定义
│   ├── base.py              # 增强Task基类
│   └── astronomy/
│       ├── observation.py    # 瞬变观测、观测计划
│       └── ...
├── tools/                   # 工具集成
│   └── __init__.py          # MCP工具、Web搜索、GitHub
├── evaluation/               # 评测系统
│   ├── metrics.py           # 评测指标 (StarWhisperED格式)
│   └── graders/             # 可插拔评分器
│       ├── base.py          # BaseGrader
│       ├── exact_match.py   # 精确匹配
│       ├── partial_match.py  # 部分匹配
│       └── astronomy.py      # 天文专用评分
├── registry.py              # 组件注册表
├── runner.py                # 多Agent多任务执行引擎
└── integrate.py             # 现有系统集成层
```

## 核心设计原则

### 1. 低耦合 (Loose Coupling)
- **Protocol抽象层**: `BaseProtocol`定义统一接口，各协议独立实现
- **Plugin架构**: `@register_*`装饰器，支持运行时注册
- **接口分离**: Agent/Task/Grader通过ABC接口解耦

### 2. 高扩展 (High Extensibility)
- **评分器插件**: `BaseGrader` + `GraderRegistry`支持自定义评分
- **协议插件**: `BaseProtocol` + `ProtocolRegistry`支持自定义天文协议
- **工具插件**: 统一工具接口，支持MCP/GitHub/Web搜索

### 3. 评测格式 (参考StarWhisperED)
```json
{"label": "TYPE = 'Eclipsing_Binary'", "predict": "TYPE = 'Eclipsing_Binary'"}
```

## 核心能力

| 组件 | 能力 |
|------|------|
| **Runner** | 4+并发Agent、8+并发任务、失败重试、超时控制 |
| **Registry** | 装饰器注册 Agent/Task/Evaluator/Grader/Protocol |
| **Protocols** | 天文协议抽象(光谱/测光/坐标) |
| **Graders** | 精确匹配、部分匹配、天文专用评分 |
| **Metrics** | 分类报告、混淆矩阵、sklearn指标 |
| **Tools** | MCP工具、GitHub搜索、Web搜索、天文星表 |

## 评测指标

```python
from harness.evaluation.metrics import ClassificationMetrics, load_jsonl_predictions

# StarWhisperED格式
refs, preds = load_jsonl_predictions("predictions.jsonl")

metric = ClassificationMetrics()
result = metric.detailed_compute(preds, refs)
# result包含: accuracy, per_class, confusion_matrix
```

## 评分器

```python
from harness.evaluation.graders import ExactMatchGrader, AstronomyGrader

# 精确匹配
grader = ExactMatchGrader()
result = grader.grade("Eclipsing Binary", "Eclipsing Binary")

# 天文专用评分
grader = AstronomyGrader(config={"redshift_tolerance": 0.01})
result = grader.grade({"redshift": 0.05}, {"redshift": 0.05}, task_type="redshift")
```

## 天文协议

```python
from harness.protocols.astronomy import SpectralAnalysisProtocol

protocol = SpectralAnalysisProtocol()
result = protocol.execute({"spectrum": data, "task": "classify"})
```

## 任务分级 (参考GAIA)

| Level | 步数 | 示例 |
|-------|------|------|
| Level 1 | <5步 | 基础天文问答、星表查询 |
| Level 2 | 5-10步 | 观测计划、数据分析 |
| Level 3 | >10步 | 论文复现、多源数据综合 |

## 测试

```bash
# 运行所有测试
pytest tests/test_harness/ tests/test_core.py -v

# 53 tests passing
```

## 快速开始

```python
from harness import HarnessRunner, RunConfig
from harness.core import AgentConfig, AgentType
from harness.evaluation.graders import ExactMatchGrader

# 配置
runner = HarnessRunner(RunConfig(
    max_concurrent_agents=4,
    enable_mcp=True,
    enable_skill=True
))

# 注册评分器
runner._evaluators["exact"] = ExactMatchGrader()

# 运行
result = await runner.run(tasks, agent_configs)
```
