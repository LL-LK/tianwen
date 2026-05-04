# 天问-AGI (Tianwen-AGI) / Hermes-AGI

全自动天文观测站 —— 基于多智能体协作的 AI 天文研究系统。

## 项目简介

天问-AGI 是一个**全自动天文观测与研究系统**，通过多个 AI Agent 协作，实现从观测计划制定、数据采集、文献研究、假说生成与验证到新发现追踪的完整科研闭环。

### 核心范式

```
观测 → 数据挖掘 → 文献研究 → 假说生成 → 假说验证 → 发现追踪 → 自我进化
  ↑                                                              ↓
  └──────────────────── 闭环自动迭代 ─────────────────────────────┘
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **多智能体协作** | 3+ Agent 协同工作（数据挖掘/文献研究/观测执行/假说验证） |
| **全自动观测** | 自动制定观测计划、调度望远镜、采集数据 |
| **文献研究** | 自动检索 arXiv/SAO/NASA ADS 论文，提取关键信息 |
| **假说引擎** | 从数据中自动生成科学假说，贝叶斯推断验证 |
| **发现追踪** | 追踪新发现，评估科学意义，生成报告 |
| **Web 控制台** | 实时 WebSocket 推送，3D 星图可视化，全功能 API |
| **向量记忆** | 基于 ChromaDB 的语义搜索，持久化知识图谱 |
| **自我进化** | 从成功/失败中学习，优化策略参数 |

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Web 前端 (web/)                       │
│  实时仪表盘 │ 3D星图 │ 观测控制 │ 假说管理 │ 发现日志    │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket / REST API
┌──────────────────────┴──────────────────────────────────┐
│                  API Server (server.py)                  │
│  Quart 异步框架 │ WebSocket 实时推送 │ CORS 安全配置     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│              核心引擎 (main.py / CognitiveEngine)        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 数据挖掘 │ │ 文献研究 │ │ 假说生成 │ │ 假说验证 │   │
│  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 观测执行 │ │ 发现追踪 │ │ 自我审查 │ │ 技能集成 │   │
│  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                   基础设施层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 向量记忆 │ │ 知识图谱 │ │ 会话存储 │ │ 日志系统 │   │
│  │ ChromaDB │ │ NetworkX │ │  Redis   │ │  Logger  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
tianwen-agi/
│
├── src/                          # 核心源码
│   ├── main.py                   # 主入口，HermesAGI 核心类
│   ├── server.py                 # Web API 服务器 (Quart)
│   │
│   ├── core/                     # 核心引擎
│   │   ├── reasoning.py          # 推理引擎 (LLM 调用)
│   │   └── cognitive.py          # 认知引擎
│   │
│   ├── agents/                   # 智能体
│   │   ├── data_miner.py         # 数据挖掘 Agent
│   │   ├── literature.py         # 文献研究 Agent
│   │   ├── hypothesis_gen.py     # 假说生成 Agent
│   │   ├── hypothesis_test.py    # 假说验证 Agent
│   │   ├── observation.py        # 观测执行 Agent
│   │   ├── discovery.py          # 发现追踪 Agent
│   │   ├── self_review.py        # 自我审查 Agent
│   │   └── coordinator.py        # 多智能体协调器
│   │
│   ├── telescope/                # 望远镜控制
│   │   ├── simulator.py          # 望远镜模拟器
│   │   ├── seestar_client.py     # Seestar MCP 客户端
│   │   └── scheduler.py          # 观测调度器
│   │
│   ├── astronomy/                # 天文算法
│   │   ├── algorithms.py         # 天文计算
│   │   ├── star_recognizer.py    # 星图识别
│   │   ├── fits_processor.py     # FITS 文件处理
│   │   └── platesolver.py        # 天测定位
│   │
│   ├── observation/              # 观测工作流
│   │   ├── workflow.py           # 观测工作流引擎
│   │   ├── executor.py           # 观测执行器
│   │   └── realtime.py           # 实时数据处理
│   │
│   ├── research/                 # 研究工具
│   │   ├── literature.py         # 文献检索
│   │   ├── loop.py               # 研究循环
│   │   └── linker.py             # 研究-观测连接器
│   │
│   ├── data/                     # 数据处理
│   │   ├── models.py             # 统一数据模型
│   │   ├── pipeline.py           # 数据管道
│   │   ├── analysis.py           # 数据分析
│   │   └── kepler_client.py      # Kepler/TESS 客户端
│   │
│   ├── memory/                   # 记忆系统
│   │   ├── vector.py             # 向量记忆 (ChromaDB)
│   │   ├── vector_store.py       # 向量存储
│   │   ├── persistence.py        # 持久化记忆
│   │   ├── scenario.py           # 场景记忆
│   │   └── rag.py                # RAG 检索增强
│   │
│   ├── learning/                 # 学习与进化
│   │   ├── rl_scheduler.py       # 强化学习调度
│   │   ├── overfit_correction.py # 过拟合自校正
│   │   └── skill_tester.py       # 技能测试
│   │
│   ├── web/                      # Web 服务
│   │   ├── dashboard.py          # 统计仪表盘
│   │   ├── bridge.py             # 实时桥接
│   │   └── session.py            # 会话管理
│   │
│   └── utils/                    # 工具
│       ├── logger.py             # 日志系统
│       ├── models.py             # 模型配置
│       └── sandbox.py            # 沙箱执行
│
├── web/                          # 前端静态文件
│   ├── index.html                # 主控制台
│   ├── manifest.json             # PWA 清单
│   ├── sw.js                     # Service Worker
│   └── 3d/                       # 3D 可视化
│       ├── orbit_viewer.html     # 轨道查看器
│       └── skychart3d.html       # 3D 星图
│
├── tests/                        # 测试套件
│   ├── test_runtime_modules.py   # 单元测试
│   ├── integration_test.py       # 集成测试
│   ├── test_observation_loop.py  # 观测循环测试
│   └── test_embodied.py          # 具身观测测试
│
├── scripts/                      # 工具脚本
│   ├── init_star_catalog.py      # 星表初始化
│   ├── start_ollama_network.bat  # Ollama 网络启动
│   └── tools/                    # 辅助工具
│       ├── browser_search.py     # 浏览器搜索
│       ├── download_models.sh    # 模型下载
│       ├── multi_agent_search.py # 多智能体搜索
│       ├── reproduction.py       # 复现实验
│       └── verify_models.py      # 模型验证
│
├── docs/                         # 文档
│   ├── PRO/                      # 专业分析文档
│   ├── deploy/                   # 部署文档
│   ├── issues/                   # Issue 回复
│   ├── literature/               # 文献索引
│   ├── models/                   # 模型分析
│   ├── reports/                  # 报告
│   ├── research/                 # 研究文档
│   └── search-results/           # 搜索结果
│
├── data/                         # 数据文件
│   ├── star_catalogs.db          # 星表数据库
│   └── sessions.json             # 会话数据
│
├── memory/                       # 运行时记忆
│   ├── evolution-log.md          # 进化日志
│   ├── knowledge-graph.md        # 知识图谱
│   ├── learned-patterns.md       # 学习模式
│   ├── skill-feedback.md         # 技能反馈
│   ├── task-history.md           # 任务历史
│   └── user-preferences.md       # 用户偏好
│
├── deploy/                       # 部署配置
│   └── cloudflare/               # Cloudflare Workers
│       ├── functions/api/        # API 代理
│       └── api-proxy.js          # 代理脚本
│
├── .github/workflows/            # CI/CD
│   ├── ci.yml                    # 持续集成
│   ├── deploy-railway.yml        # Railway 部署
│   └── docker-build.yml          # Docker 构建
│
├── Dockerfile                    # Docker 镜像
├── docker-compose.yml            # Docker Compose
├── .dockerignore                 # Docker 忽略
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git 忽略
├── .pre-commit-config.yaml       # Pre-commit 配置
└── README.md                     # 本文件
```

## 快速开始

### 环境要求

- Python 3.10+
- pip
- (可选) Docker / Ollama

### 安装

```bash
# 1. 克隆项目
git clone https://github.com/LL-LK/tianwen-agi.git
cd tianwen-agi

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key 等配置

# 5. 初始化星表
python scripts/init_star_catalog.py

# 6. 启动服务
python src/server.py

# 7. 打开浏览器
# http://localhost:5000
```

### Docker 部署

```bash
docker-compose up -d
```

## Web 前端功能

| 功能模块 | 说明 |
|----------|------|
| **实时仪表盘** | 系统状态、Agent 活跃度、资源使用 |
| **观测控制** | 制定观测计划、调度望远镜、查看实时图像 |
| **3D 星图** | WebGL 交互式星图，支持目标搜索和轨道可视化 |
| **假说管理** | 查看/创建/验证科学假说，贝叶斯后验概率 |
| **文献研究** | 论文检索、摘要提取、引用分析 |
| **发现日志** | 新发现追踪、科学意义评估、报告导出 |
| **系统设置** | API Key 配置、模型选择、观测站参数 |

## API 接口文档

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 系统健康检查 |

### 系统状态

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 获取系统完整状态 |
| GET | `/api/status/agents` | 获取所有 Agent 状态 |
| GET | `/api/status/resources` | 获取系统资源使用 |

### 观测管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/observation/plan` | 获取观测计划 |
| POST | `/api/observation/plan` | 创建观测计划 |
| GET | `/api/observation/current` | 获取当前观测 |
| POST | `/api/observation/start` | 开始观测 |
| POST | `/api/observation/stop` | 停止观测 |
| GET | `/api/observation/history` | 观测历史 |
| GET | `/api/observation/image/<id>` | 获取观测图像 |

### 望远镜控制

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/telescope/status` | 望远镜状态 |
| POST | `/api/telescope/goto` | 指向目标 |
| POST | `/api/telescope/park` | 归位 |
| GET | `/api/telescope/capabilities` | 设备能力 |

### 数据挖掘

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/data/mining/start` | 开始数据挖掘 |
| GET | `/api/data/mining/status` | 挖掘状态 |
| GET | `/api/data/mining/results` | 挖掘结果 |
| GET | `/api/data/catalogs` | 可用星表列表 |
| POST | `/api/data/query` | 查询星表数据 |

### 文献研究

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/literature/search` | 搜索论文 |
| GET | `/api/literature/paper/<id>` | 获取论文详情 |
| GET | `/api/literature/recent` | 最新论文 |
| POST | `/api/literature/analyze` | 分析论文 |

### 假说管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/hypothesis/list` | 假说列表 |
| POST | `/api/hypothesis/generate` | 生成假说 |
| GET | `/api/hypothesis/<id>` | 假说详情 |
| POST | `/api/hypothesis/<id>/test` | 验证假说 |
| PUT | `/api/hypothesis/<id>/status` | 更新假说状态 |

### 发现追踪

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/discovery/list` | 发现列表 |
| GET | `/api/discovery/<id>` | 发现详情 |
| POST | `/api/discovery/evaluate` | 评估发现 |

### 记忆系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/memory/knowledge` | 知识图谱 |
| POST | `/api/memory/search` | 语义搜索 |
| GET | `/api/memory/evolution` | 进化日志 |
| GET | `/api/memory/patterns` | 学习模式 |

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sessions` | 会话列表 |
| POST | `/api/sessions` | 创建会话 |
| GET | `/api/sessions/<id>` | 会话详情 |
| DELETE | `/api/sessions/<id>` | 删除会话 |

### WebSocket 端点

| 路径 | 说明 |
|------|------|
| `/ws/observatory` | 观测站实时数据推送 |
| `/ws/agent_status` | Agent 状态实时更新 |
| `/ws/observation` | 观测过程实时推送 |

## 核心模块详解

### 1. HermesAGI (main.py)

系统主控制器，负责初始化所有 Agent、管理生命周期、协调工作流。

```python
from main import HermesAGI

agent = HermesAGI()
await agent.initialize()
status = await agent.get_status()
```

### 2. CognitiveEngine (推理引擎)

封装 LLM 调用，支持多种模型后端（OpenAI / Ollama / 本地模型）。

```python
from reasoning_engine import ModelConfig

config = ModelConfig(
    model="gpt-4",
    temperature=0.7,
    max_tokens=4096
)
```

### 3. DataMiner (数据挖掘)

从 Kepler/TESS/GAIA 等星表挖掘数据，支持 SQL 查询和批量导出。

### 4. LiteratureResearcher (文献研究)

自动检索 arXiv、SAO/NASA ADS、CrossRef，提取摘要和关键发现。

### 5. HypothesisGenerator (假说生成)

基于观测数据和文献证据，使用 LLM 自动生成可验证的科学假说。

### 6. HypothesisTester (假说验证)

贝叶斯推断框架，支持 FDR 控制、交叉验证、效应量计算。

### 7. ObservationExecutor (观测执行)

管理望远镜观测流程：指向 → 对焦 → 曝光 → 图像采集 → 数据处理。

### 8. VectorMemory (向量记忆)

基于 ChromaDB 的语义搜索系统，支持论文嵌入、相似度检索、知识图谱构建。

## 部署指南

### Railway

```bash
# 自动从 GitHub 部署，设置环境变量：
# - DEBUG=false
# - API_KEY=your_secret_key
# - REDIS_URL=redis://...
```

### Cloudflare Workers

API 代理和静态资源加速，配置见 `deploy/cloudflare/`。

### Docker

```bash
docker build -t tianwen-agi .
docker run -p 5000:5000 \
  -e API_KEY=your_key \
  -v $(pwd)/memory:/app/memory \
  -v $(pwd)/data:/app/data \
  tianwen-agi
```

## 开发指南

### 运行测试

```bash
# 单元测试
python -m pytest tests/test_runtime_modules.py -v

# 集成测试
python -m pytest tests/integration_test.py -v

# 全部测试
python -m pytest tests/ -v
```

### 代码规范

- Python 3.10+ 类型注解
- 异步优先 (asyncio/Quart)
- 统一数据模型 (data_models.py)
- 结构化日志 (runtime_logger.py)

## 常见问题

**Q: 如何接入真实望远镜？**
A: 配置 Seestar MCP 客户端 (`seestar_mcp_client.py`)，或通过 ASCOM 驱动连接。

**Q: 支持哪些 LLM？**
A: OpenAI GPT-4、Ollama 本地模型（Llama3/Qwen2）、Claude API。

**Q: 数据存储在哪里？**
A: 向量数据在 ChromaDB（`memory/`），星表在 SQLite（`data/star_catalogs.db`），会话可选 Redis。

**Q: 如何离线运行？**
A: 使用 Ollama 本地模型 + 离线星表数据，完全无需网络。

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v3.8 | 2026-05 | 项目结构重组，文档完善 |
| v3.7 | 2026-04 | 假说验证 v2.0，贝叶斯推断 |
| v3.6 | 2026-04 | 多智能体协调器，实时桥接 |
| v3.5 | 2026-03 | 向量记忆，ChromaDB 集成 |

## 许可证

MIT License
