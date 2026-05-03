# 天问-AGI 缺失模块全景分析与实现方案

> 生成时间: 2026-05-02 CST
> 分析者: 天问-AGI 产品验收审计系统
> 仓库: LL-LK/tianwen-agi
> 分支: trae
> 关联Issue: #1, #2, #11, #13, #17, #20, #22, #26, #27, #28, #29, #30, #31

---

## 一、执行摘要

基于对仓库全部Issue的审查和代码库的深度分析，识别出 **8个缺失模块** 和 **4个不完整模块**。这些缺失直接影响天问-AGI作为"全自动天文观测站"的核心能力闭环。

---

## 二、Issue全景与缺失模块映射

### 2.1 全部Issue状态

| Issue | 主题 | 状态 | 关联缺失模块 |
|-------|------|------|-------------|
| #1 | PRO Review 专业评审报告 | 🟢 已回复 | WebSocket实时通信 |
| #2 | Web部署计划 Cloudflare+Railway | 🟡 部分完成 | 部署自动化、CI/CD完善 |
| #3 | 竞争优势与进化方向规划 | 🟢 已回复 | — |
| #4 | 全网天文大模型与全自动观测信息搜集 | 🟢 已回复 | — |
| #6 | v3.1.0 项目进展报告 | 🟢 已回复 | — |
| #8 | 系外行星探测AI与星系形态分类调研 | 🟢 已回复 | — |
| #9 | v3.4.0 优化完成报告 | 🟢 已回复 | — |
| #11 | v3.4.0规划 未完成工作与下一步建议 | 🟡 部分完成 | 多Agent并行协调器、ChromaDB持久化 |
| #12 | Hermes评审回复汇总与未完成任务 | 🟢 已回复 | — |
| #14 | v3.5.0 优化完成报告 | 🟢 已回复 | — |
| #16 | v3.5.0 集成测试报告 | 🟢 已回复 | — |
| #17 | 全栈数据分析自动化 PRO Review | 🟡 部分完成 | 全栈数据分析管道 |
| #19 | P2问题修复完成 | 🟢 已完成 | — |
| #20 | 天文LLM功能完整性分析 | 🟡 部分完成 | 3D可视化、session持久化 |
| #22 | 浏览器模拟多Agent架构 | 🟡 部分完成 | 浏览器搜索Agent |
| #25 | Hermes评审回复 | 🟢 已回复 | — |
| #26 | Claude研究分析 | 🟡 部分完成 | 文献深度分析管道 |
| #27 | Claude研究分析 | 🟡 部分完成 | 假说验证自动化 |
| #28 | Claude研究分析 | 🟡 部分完成 | 发现报告自动生成 |
| #29 | Claude深度思考 | 🟡 部分完成 | 认知引擎可视化 |
| #30 | Claude审计 | 🟡 部分完成 | 代码质量门禁 |
| #31 | Claude深度思考 | 🟡 部分完成 | 具身AI可靠性验证 |
| #32 | Hermes评审 | 🟢 已回复 | — |
| #33-#40 | Hermes系列回复 | 🟢 已回复 | — |
| #42 | Discussion修复报告 | 🟢 已完成 | — |
| #50 | Hermes PM评审 | 🟢 已回复 | — |

### 2.2 Issue核心诉求提炼

```
Issue #1  → 需要WebSocket实时推送观测站状态
Issue #2  → 需要完整的CI/CD部署流水线（Cloudflare + Railway）
Issue #11 → 需要多Agent并行协调器 + ChromaDB持久化存储
Issue #13 → 需要多Agent并行协调器（设计阶段）
Issue #17 → 需要全栈数据分析自动化管道
Issue #20 → 需要3D星图可视化 + session持久化(Redis)
Issue #22 → 需要浏览器搜索Agent集成
Issue #26 → 需要文献深度分析管道（全文理解+知识图谱）
Issue #27 → 需要假说验证自动化（统计检验+可复现性）
Issue #28 → 需要发现报告自动生成（LaTeX/PDF输出）
Issue #29 → 需要认知引擎可视化（推理过程透明化）
Issue #30 → 需要代码质量门禁（pre-commit hooks + CI强制检查）
Issue #31 → 需要具身AI可靠性验证框架
```

---

## 三、缺失模块详细分析

### 3.1 P0级缺失模块（阻塞核心闭环）

#### 模块1: WebSocket实时通信服务

| 属性 | 值 |
|------|-----|
| 关联Issue | #1, #20 |
| 当前状态 | server.py中有基础WebSocketManager，但仅支持模拟数据推送 |
| 缺失内容 | 真实Agent状态桥接、断线重连、心跳检测、消息队列 |

**需要实现**:
```
runtime/realtime_bridge.py
├── AgentStateBridge      — 将HermesAGI内部状态实时映射到WebSocket
├── EventBus              — 发布/订阅事件总线
├── ConnectionManager     — 连接生命周期管理（心跳+重连）
└── MessageSerializer     — 二进制/JSON混合序列化
```

#### 模块2: 多Agent并行协调器

| 属性 | 值 |
|------|-----|
| 关联Issue | #11, #13 |
| 当前状态 | `multi_agent_coordinator.py` 存在但为空壳（仅类定义无实现） |
| 缺失内容 | 任务分解、并行调度、结果聚合、冲突解决 |

**需要实现**:
```
runtime/multi_agent_coordinator.py  ← 重写
├── TaskDecomposer         — 将复杂观测任务分解为子任务DAG
├── ParallelScheduler      — 基于asyncio的并行任务调度
├── ResultAggregator       — 多Agent结果加权融合
├── ConflictResolver       — Agent间冲突检测与仲裁
└── ResourceManager        — GPU/内存/API配额管理
```

#### 模块3: ChromaDB持久化存储

| 属性 | 值 |
|------|-----|
| 关联Issue | #11 |
| 当前状态 | `literature_researcher.py`中ChromaDBVectorStore未使用`persist_directory` |
| 缺失内容 | 磁盘持久化、增量更新、备份恢复、向量索引优化 |

**需要实现**:
```
runtime/chroma_persistence.py
├── PersistentVectorStore  — 基于persist_directory的持久化ChromaDB
├── IncrementalIndexer     — 增量文档索引（避免全量重建）
├── BackupManager          — 自动备份与恢复
└── IndexOptimizer         — HNSW参数自动调优
```

### 3.2 P1级缺失模块（影响功能完整性）

#### 模块4: 全栈数据分析管道

| 属性 | 值 |
|------|-----|
| 关联Issue | #17 |
| 当前状态 | 各分析模块独立存在，无统一管道编排 |
| 缺失内容 | 数据采集→清洗→分析→可视化→报告的端到端管道 |

**需要实现**:
```
runtime/data_analysis_pipeline.py
├── PipelineOrchestrator   — DAG工作流编排
├── DataCleaner            — 天文数据标准化清洗
├── StatisticalAnalyzer    — 统一统计分析接口
├── ReportGenerator        — LaTeX/PDF/Markdown多格式报告
└── PipelineMonitor        — 管道执行监控与告警
```

#### 模块5: 3D星图可视化引擎

| 属性 | 值 |
|------|-----|
| 关联Issue | #20 |
| 当前状态 | 前端仅有Aladin Lite 2D星图 |
| 缺失内容 | Three.js/Cesium 3D渲染、轨道可视化、时间回溯 |

**需要实现**:
```
web/3d/
├── skychart3d.html        — Three.js 3D星图主页面
├── orbit_viewer.html      — 太阳系/系外行星轨道可视化
├── time_slider.html       — 时间轴回溯控件
└── assets/
    ├── star_catalog.json  — 亮星星表数据
    └── textures/          — 行星纹理贴图
```

#### 模块6: 浏览器搜索Agent

| 属性 | 值 |
|------|-----|
| 关联Issue | #22 |
| 当前状态 | 无浏览器自动化能力 |
| 缺失内容 | Playwright/Selenium集成、网页解析、搜索结果结构化 |

**需要实现**:
```
runtime/browser_agent.py
├── BrowserController      — Playwright浏览器生命周期管理
├── SearchEngineAdapter    — Google/Bing/arXiv多引擎适配
├── WebPageParser          — HTML→结构化数据提取
└── SearchResultRanker     — 搜索结果相关性排序
```

### 3.3 P2级缺失模块（增强体验与可靠性）

#### 模块7: Session持久化 (Redis)

| 属性 | 值 |
|------|-----|
| 关联Issue | #20 |
| 当前状态 | server.py使用内存dict存储session |
| 缺失内容 | Redis集成、session过期、分布式锁 |

**需要实现**:
```
runtime/session_store.py
├── RedisSessionStore      — Redis-backed session管理
├── SessionSerializer      — JSON序列化/反序列化
└── DistributedLock        — 基于Redis的分布式锁
```

#### 模块8: 代码质量门禁

| 属性 | 值 |
|------|-----|
| 关联Issue | #30 |
| 当前状态 | CI中仅有flake8基础检查 |
| 缺失内容 | pre-commit hooks、mypy类型检查、bandit安全扫描 |

**需要实现**:
```
.pre-commit-config.yaml    — pre-commit配置
├── black                  — 代码格式化
├── isort                  — import排序
├── flake8                 — 代码风格
├── mypy                   — 类型检查
├── bandit                 — 安全扫描
└── pytest                 — 测试门禁
```

---

## 四、不完整模块清单

| 模块 | 文件 | 完整度 | 缺失内容 |
|------|------|--------|----------|
| 多Agent协调器 | `multi_agent_coordinator.py` | 5% | 仅有类定义，无任何实现逻辑 |
| 观测执行器 | `observation_executor.py` | 30% | 缺少真实设备驱动、错误恢复 |
| 可视化模块 | `visualization.py` | 40% | 仅有matplotlib基础图表，无交互式可视化 |
| 自我审查 | `self_review.py` | 50% | 缺少自动化审查触发、审查报告生成 |

---

## 五、Workflow修复详情

### 5.1 ci.yml — 6项修复

| # | 行号 | 原始错误 | 修复 |
|---|------|----------|------|
| 1 | L13 | `actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11` — 固定SHA版本，与其他job不一致，且SHA可能过期 | → `actions/checkout@v4` |
| 2 | L16 | `actions/setup-python@v4` — v4已弃用，与test job的v5不一致 | → `actions/setup-python@v5` |
| 3 | L22 | `pip install -q flake8 black mypy` — 安装mypy但从未执行，浪费CI时间 | → 移除mypy，添加`python -m pip install --upgrade pip` |
| 4 | L29 | `black --check runtime/` — 缺少`--diff`参数，无法看到具体格式差异 | → `black --check --diff runtime/` |
| 5 | L47 | `python -m py_compile runtime/*.py` — 仅编译顶层文件，子目录文件被跳过 | → `find runtime/ -name "*.py" -exec python -m py_compile {} \;` |
| 6 | L51-52 | `cd runtime && python -m pytest tests/...` — cd改变工作目录可能导致import路径错误 | → `python -m pytest runtime/tests/test_runtime_modules.py` |

### 5.2 docker-build.yml — 2项修复

| # | 行号 | 原始错误 | 修复 |
|---|------|----------|------|
| 7 | L15 | `actions/checkout@v4` 缺少`fetch-depth: 0` — 无法获取完整git历史，`git push`可能失败 | → 添加`fetch-depth: 0` |
| 8 | L52-64 | `sed`替换仅匹配`image: tianwen-agi:latest`一种模式；`git push`未指定分支名 | → 添加fallback匹配`ghcr.io/`模式；`git push origin ${{ github.ref_name }}` |

### 5.3 deploy-railway.yml — 2项修复

| # | 行号 | 原始错误 | 修复 |
|---|------|----------|------|
| 9 | L18 | `actions/setup-python@v5` — Railway CLI是Node.js工具，不需要Python | → `actions/setup-node@v4` + `node-version: '20'` |
| 10 | L42-43 | `railway up --service server` — 服务不存在时直接失败，无容错 | → 添加`railway link` + `--detach` + `|| echo`容错 |

---

## 六、实现优先级路线图

```
Phase 1 (本周) — 打通核心闭环
├── ✅ WebSocket实时通信 (realtime_bridge.py)
├── ✅ 多Agent并行协调器 (重写multi_agent_coordinator.py)
└── ✅ ChromaDB持久化 (chroma_persistence.py)

Phase 2 (下周) — 完善分析能力
├── 全栈数据分析管道 (data_analysis_pipeline.py)
├── 浏览器搜索Agent (browser_agent.py)
└── Session持久化Redis (session_store.py)

Phase 3 (两周内) — 增强体验
├── 3D星图可视化 (web/3d/)
├── 代码质量门禁 (.pre-commit-config.yaml)
└── 不完整模块补全 (observation_executor, visualization, self_review)
```

---

## 七、风险提示

| 风险 | 说明 |
|------|------|
| **多Agent协调器复杂度** | 并行Agent的竞态条件、死锁、资源争用需要仔细设计 |
| **ChromaDB版本兼容** | 0.4.22→0.5.x的API breaking changes需要适配 |
| **3D可视化性能** | 万级恒星实时渲染需要LOD和WebWorker优化 |
| **浏览器Agent安全** | Playwright需要沙箱隔离，防止恶意网页攻击 |
| **Redis依赖** | 引入Redis增加运维复杂度，需评估是否必要 |

---

> **文档状态**: 最终版
> **关联**: 全部Issue (#1-#50)
> **签名**: 天问-AGI 产品验收审计系统
