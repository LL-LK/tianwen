<p align="center">
  <img src="https://img.shields.io/badge/version-2.4.0-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/python-3.11+-green?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/platform-Railway%20%7C%20Docker%20%7C%20Cloudflare-9cf?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/github/actions/workflow/status/LL-LK/tianwen-agi/ci.yml?branch=main&style=flat-square&label=CI" alt="CI Status">
</p>

<h1 align="center">🔭 天问-AGI (Tianwen-AGI)</h1>
<h3 align="center">全自动天文观测站 · 无人值守自主发现与观测</h3>

<p align="center">
  <b>天问-AGI</b> 是一个基于 AI Agent 的全自动天文观测系统，集成了认知引擎、规划引擎、执行引擎和自我进化系统，支持从假说生成到观测验证的完整科学研究闭环。
</p>

---

## 📑 目录

- [功能特性](#-功能特性)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
  - [环境要求](#环境要求)
  - [本地开发](#本地开发)
  - [Docker 部署](#docker-部署)
  - [Railway 一键部署](#railway-一键部署)
- [Web 界面](#-web-界面)
- [API 文档](#-api-文档)
- [LLM 配置](#-llm-智能对话配置)
- [项目结构](#-项目结构)
- [CI/CD 流程](#-cicd-流程)
- [安全说明](#-安全说明)
- [路线图](#-路线图)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## ✨ 功能特性

### 🧠 AI Agent 引擎

| 引擎 | 功能 | 说明 |
|------|------|------|
| **认知引擎** (CognitiveEngine) | 意图识别、实体提取、复杂度评估 | 理解用户自然语言输入，自动识别观测意图 |
| **规划引擎** (PlanningEngine) | 任务分解、并行规划、风险评估 | 将复杂观测任务拆解为可执行的子任务序列 |
| **执行引擎** (ExecutionEngine) | 技能调度、任务执行、结果汇总 | 执行观测计划并收集各阶段结果 |
| **进化系统** (EvolutionSystem) | 模式学习、经验积累、自我优化 | 基于历史任务持续改进，支持持久化记忆 |

### 🔬 科学研究闭环

```
文献检索 → 假说生成 → 假说检验 → 发现确认 → 观测调度 → 自我进化
   ↑                                                              ↓
   └──────────────────── 持续迭代优化 ────────────────────────────┘
```

- **假说生成**: 基于文献和观测数据自动生成科学假说
- **假说验证**: 支持统计检验、交叉验证、置信区间计算
- **发现确认**: 自动识别新天体、异常现象
- **观测调度**: 智能优先级排序，时间窗口优化

### 🌌 天文观测功能

- **实时星图**: 集成 NASA SkyView API，支持 DSS/2MASS/SDSS 等多种巡天数据
- **天体星表**: 内置 110+ 梅西耶/NGC 天体数据，支持按类型筛选和搜索
- **光变曲线**: 模拟光变曲线数据展示
- **三阶段检测**: 恒星/星系/类星体分类检测流水线
- **观测窗口计算**: 基于目标坐标和观测地纬度计算最佳观测时间

### 🔭 望远镜控制

- **设备管理**: 望远镜 (Seestar S50)、相机 (IMX462)、滤镜轮 (ZWO EFW)、圆顶
- **GOTO 指向**: 输入天体名称自动指向
- **跟踪控制**: 启动/停止跟踪，Plate Solving
- **成像控制**: 可配置曝光时间、帧数、目标
- **气象站**: 云量、湿度、温度、风速、视宁度监测

### 💬 智能对话

- **多供应商支持**: MiniMax、通义千问 (Qwen)、OpenAI 兼容接口
- **API 格式兼容**: 原生格式 / OpenAI 兼容格式 / Anthropic 格式
- **连通性测试**: 一键检测 LLM API 可用性和延迟
- **本地回退**: LLM 不可用时自动切换本地规则回复
- **会话管理**: 支持 Redis 持久化或内存存储，多轮对话上下文保持

### ⚡ 实时通信

- **WebSocket 推送**: 4 个独立频道（观测站状态 / Agent 状态 / 观测数据 / 工作流引擎）
- **心跳检测**: 30 秒间隔心跳，60 秒超时自动断开
- **断线重连**: 自动重连机制，最多 10 次，指数退避
- **事件订阅**: 支持客户端订阅特定事件类型

### 🔧 可视化工作流引擎 (v2.4 新增)

- **DAG 工作流**: 可视化拖拽式工作流定义，支持 20 种节点类型
- **闭环执行**: 文献调研 → 假说生成 → 观测调度 → 数据挖掘 → 指导观测 全闭环
- **7 个预置模板**: 完整研究闭环、快速观测、文献深度调研、异常天体狩猎、多智能体协作、实时天空监控、数据流水线
- **实时推送**: WebSocket 实时推送节点状态和执行进度
- **无代码配置**: 所有节点参数通过 JSON 配置，无需编写代码
- **条件分支**: 支持基于执行结果的条件路由
- **并行执行**: 同层节点自动并行执行
- **错误恢复**: 节点级重试机制，支持断点续传
- **导入/导出**: 工作流 JSON 格式可移植导入导出
- **执行统计**: 成功率、平均耗时、节点分布等统计信息

### 🛡️ 安全与运维

- **API 认证**: X-API-Key 请求头认证，开发模式自动跳过
- **速率限制**: 可配置的时间窗口和最大请求数
- **CORS 控制**: 生产环境白名单域名控制
- **安全响应头**: X-Content-Type-Options, X-Frame-Options, HSTS 等
- **健康检查**: `/api/health` 端点，支持 DEBUG/生产双模式
- **错误分类**: 临时错误自动重试，永久错误快速失败

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Web 前端 (index.html)                     │
│  观测总控台 │ 实时星图 │ 数据面板 │ 研究闭环 │ 告警中心        │
│  望远镜控制 │ 智能对话 │ 系统日志 │ 说明书                    │
└──────────┬──────────────────────────────────┬───────────────┘
           │         HTTP/REST + WebSocket     │
           ▼                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                   Quart API Server (server.py)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ CORS     │ │ Rate     │ │ API Key  │ │ WebSocket     │  │
│  │ Middleware│ │ Limiter  │ │ Auth     │ │ Manager       │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                   HermesAGI Runtime (main.py)                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐ │
│  │ Cognitive  │ │ Planning   │ │ Execution  │ │ Evolution │ │
│  │ Engine     │ │ Engine     │ │ Engine     │ │ System    │ │
│  └────────────┘ └────────────┘ └────────────┘ └───────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │ Retry      │ │ Health     │ │ Error      │               │
│  │ Engine     │ │ Monitor    │ │ Classifier │               │
│  └────────────┘ └────────────┘ └────────────┘               │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                      外部服务集成                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ MiniMax  │ │ Qwen/    │ │ NASA     │ │ ChromaDB      │  │
│  │ LLM API  │ │ OpenAI   │ │ SkyView  │ │ Vector Store  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ Redis    │ │ Neo4j    │ │ Sentence │                    │
│  │ Session  │ │ Graph DB │ │Transform │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 运行时环境 |
| pip | 23.0+ | 包管理器 |
| Docker | 24.0+ | (可选) 容器化部署 |
| Redis | 7.0+ | (可选) 会话持久化 |

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/LL-LK/tianwen-agi.git
cd tianwen-agi

# 2. 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 5. 启动服务
python src/server.py
# 或使用 hypercorn (生产模式)
hypercorn src.server:app --bind 0.0.0.0:5000 --workers 2

# 6. 打开浏览器
# http://localhost:5000
```

### Docker 部署

```bash
# 构建镜像
docker build -t tianwen-agi .

# 运行容器
docker run -d \
  --name tianwen-agi \
  -p 5000:5000 \
  -e MINIMAX_API_KEY=your_key \
  -e MINIMAX_GROUP_ID=your_group_id \
  tianwen-agi

# 使用 Docker Compose (含 ChromaDB)
docker-compose up -d

# 可选: 启动前端 Nginx
docker-compose --profile optional up -d
```

### Railway 一键部署

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

1. 点击上方按钮或 Fork 本仓库
2. 在 Railway 中导入项目
3. 设置环境变量 (MINIMAX_API_KEY 等)
4. 自动部署完成

---

## 🖥 Web 界面

天问-AGI 提供 9 个功能面板，通过顶部标签页切换：

| 面板 | 快捷键 | 功能描述 |
|------|--------|----------|
| 📡 **观测总控台** | `1` | 观测站实时状态、当前目标、设备状态、观测队列管理 |
| 🌌 **实时星图** | `2` | Aladin Lite 集成，NASA SkyView 真实天文图像 |
| 📊 **数据面板** | `3` | 光变曲线图表、最新图像、三阶段天体检测结果 |
| 🔬 **研究闭环** | `4` | 当前研究周期状态、假说置信度、闭环历史记录 |
| 🔔 **告警中心** | `5` | 系统告警列表，支持按类型筛选和已读标记 |
| 🔭 **望远镜控制** | `6` | GOTO 指向、跟踪控制、成像参数、星表浏览、观测窗口计算 |
| 💬 **智能对话** | `7` | LLM 驱动的 AI 助手，支持多轮对话 |
| 📋 **系统日志** | `8` | 实时日志流，按级别筛选 |
| 📖 **说明书** | `9` | 系统功能说明和使用指南 |

**全局快捷键**: `R` 刷新数据 · `T` 连通性检测 · `1-9` 切换面板

---

## 📡 API 文档

### 基础信息

```
Base URL: http://localhost:5000/api
Content-Type: application/json
Authentication: X-API-Key header (生产环境必需)
```

### 观测站 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/observatory/status` | 获取观测站完整状态 |
| `GET` | `/api/observatory/queue` | 获取观测队列 |
| `POST` | `/api/observatory/queue` | 添加观测目标 |
| `DELETE` | `/api/observatory/queue/<id>` | 移除队列项 |
| `POST` | `/api/observatory/control` | 控制观测站 (start/stop/pause/resume) |

**添加观测目标示例**:
```json
{
  "target": "M31",
  "priority": "P1",
  "type": "galaxy",
  "window": "2026-05-04 22:00-04:00",
  "duration": "30min"
}
```

### 设备 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/devices/status` | 获取所有设备状态 |

### 数据 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/data/detections/latest` | 三阶段检测结果 |
| `GET` | `/api/data/images/latest` | 最新图像信息 |
| `GET` | `/api/data/lightcurve?target=M31` | 光变曲线数据 |

### 研究 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/research/status` | 研究闭环状态 |
| `GET` | `/api/research/cycles?page=1&per_page=20` | 历史研究周期 |
| `POST` | `/api/hypothesis/test` | 假说验证 |

**假说验证请求示例**:
```json
{
  "hypothesis": {
    "id": "hypo_abc123",
    "statement": "M31星系核心存在中等质量黑洞",
    "premises": ["恒星运动异常", "X射线辐射增强"],
    "predictions": ["核心恒星速度弥散 > 200 km/s"],
    "verification_method": "光谱观测",
    "confidence": 0.7
  },
  "observation_data": [
    {"wavelength": "H-alpha", "velocity_km_s": 215, "error": 15}
  ],
  "literature_evidence": [
    {"source": "ApJ 2024", "finding": "支持核心黑洞假说"}
  ]
}
```

### 对话 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/chat` | LLM 对话 |
| `POST` | `/api/cognitive` | 认知引擎预览 |
| `POST` | `/api/llm/test` | LLM 连通性测试 |
| `GET` | `/api/sessions` | 会话列表 |
| `GET` | `/api/sessions/<id>` | 会话详情 |

**对话请求示例**:
```json
{
  "message": "M31距离地球多远？",
  "session_id": "optional-session-id",
  "provider": "minimax",
  "config": {
    "api_key": "your-api-key",
    "group_id": "your-group-id",
    "endpoint": "https://api.minimax.chat/v1",
    "model": "MiniMax-M2.7",
    "api_format": "native"
  }
}
```

### 星图 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/skychart/realtime?target=M31&survey=DSS2/color&size=15&pixels=600` | 获取真实星图 |

### 系统 API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/stats/dashboard` | HTML 统计面板 |
| `GET` | `/api/stats/json` | JSON 统计 |
| `GET` | `/api/docs` | 完整 API 文档 |
| `GET` | `/api/alerts?unread=true` | 告警列表 |
| `PUT` | `/api/alerts/<id>/read` | 标记告警已读 |
| `GET` | `/api/logs?level=DISCOVERY&limit=50` | 系统日志 |

### 工作流引擎 API (v2.4)

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/workflow-engine/node-types` | 获取所有节点类型 |
| `GET` | `/api/workflow-engine/templates` | 获取预置模板列表 |
| `POST` | `/api/workflow-engine/templates/<name>/instantiate` | 从模板实例化工作流 |
| `GET` | `/api/workflow-engine/definitions` | 列出所有工作流定义 |
| `POST` | `/api/workflow-engine/definitions` | 创建/更新工作流定义 |
| `GET` | `/api/workflow-engine/definitions/<id>` | 获取工作流详情 |
| `DELETE` | `/api/workflow-engine/definitions/<id>` | 删除工作流 |
| `POST` | `/api/workflow-engine/execute/<id>` | 执行工作流 |
| `GET` | `/api/workflow-engine/status/<id>` | 获取执行状态 |
| `GET` | `/api/workflow-engine/history` | 获取执行历史 |
| `GET` | `/api/workflow-engine/statistics` | 获取引擎统计 |
| `GET` | `/api/workflow-engine/export/<id>` | 导出工作流 JSON |
| `POST` | `/api/workflow-engine/import` | 导入工作流 JSON |
| `POST` | `/api/workflow-engine/cancel/<id>` | 取消执行中的工作流 |

### WebSocket 端点

| 端点 | 说明 | 消息类型 |
|------|------|----------|
| `/ws/observatory` | 观测站实时推送 | status_update, queue_update, new_alert, heartbeat |
| `/ws/agent_status` | Agent 状态推送 | cognitive, planning, execution, evolution |
| `/ws/observation` | 观测状态推送 | device_status, queue_status, heartbeat |
| `/ws/workflow-engine` | 工作流引擎推送 | node_status, execution_progress, loop_event |

**WebSocket 连接示例 (JavaScript)**:
```javascript
const ws = new WebSocket('wss://your-app.railway.app/ws/observatory');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'status_update': updateUI(data.data); break;
    case 'heartbeat': ws.send(JSON.stringify({type: 'pong'})); break;
  }
};

// 心跳保活
setInterval(() => ws.send('ping'), 30000);
```

---

## 🤖 LLM 智能对话配置

### 支持的供应商

| 供应商 | 默认模型 | API 格式 | 注册地址 |
|--------|----------|----------|----------|
| **MiniMax** | MiniMax-M2.7 | 原生 / OpenAI 兼容 | [platform.minimaxi.com](https://platform.minimaxi.com) |
| **通义千问** | qwen-plus | OpenAI 兼容 | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |
| **OpenAI 兼容** | gpt-4o-mini | OpenAI 兼容 | 支持任何 OpenAI 格式供应商 |

### 配置方式

**方式一: 环境变量 (推荐)**
```bash
# .env 文件
MINIMAX_API_KEY=your_api_key_here
MINIMAX_GROUP_ID=your_group_id_here
MINIMAX_MODEL=MiniMax-M2.7
```

**方式二: Web 界面配置**
1. 点击右上角 🔑 按钮
2. 选择供应商并填入 API Key
3. 点击"保存配置"
4. 点击"LLM测试"验证连通性

### 本地回退机制

当 LLM API 不可用时，系统自动切换到本地规则回复，支持以下话题：
- 天体信息查询 (M31、M42 等)
- 望远镜操作帮助
- 假说生成引导
- 数据挖掘说明
- 系统功能介绍

---

## 📁 项目结构

```
tianwen-agi/
├── .github/workflows/          # GitHub Actions CI/CD
│   ├── ci.yml                  # 持续集成 (lint → test → docker-build)
│   ├── docker-build.yml        # Docker 镜像构建并推送到 GHCR
│   └── deploy-railway.yml      # Railway 自动部署
├── src/                        # 后端源码
│   ├── server.py               # Quart API 服务器 (主入口)
│   ├── main.py                 # HermesAGI Agent 运行时
│   ├── reasoning_engine.py     # LLM 推理引擎
│   ├── runtime_logger.py       # 运行时日志系统
│   ├── agents/                 # AI Agent 模块
│   │   ├── coordinator.py      # 协调 Agent
│   │   ├── discovery.py        # 发现 Agent
│   │   ├── hypothesis_gen.py   # 假说生成 Agent
│   │   ├── hypothesis_test.py  # 假说检验 Agent
│   │   ├── observation.py      # 观测 Agent
│   │   ├── literature.py       # 文献检索 Agent
│   │   ├── data_miner.py       # 数据挖掘 Agent
│   │   ├── browser.py          # 浏览器 Agent
│   │   ├── self_review.py      # 自我审查 Agent
│   │   ├── tri_agent.py        # 三体 Agent
│   │   ├── workflow_engine.py  # 可视化闭环工作流引擎
│   │   └── agent_enhancements.py # Agent 增强模块
│   ├── core/                   # 核心引擎
│   │   ├── cognitive.py        # 认知引擎 + 规划引擎
│   │   ├── reasoning.py        # 推理引擎
│   │   └── dream.py            # 梦想引擎
│   ├── astronomy/              # 天文计算模块
│   │   ├── algorithms.py       # 天文算法
│   │   ├── catalog.py          # 天体星表
│   │   ├── sky_chart.py        # 星图生成 (NASA SkyView)
│   │   ├── platesolver.py      # Plate Solving
│   │   ├── sextractor.py       # Source Extractor
│   │   ├── fits_processor.py   # FITS 文件处理
│   │   ├── star_recognizer.py  # 星体识别
│   │   ├── analyzer.py         # 数据分析
│   │   └── pipeline.py         # 处理流水线
│   ├── observation/            # 观测模块
│   │   ├── scheduler.py        # 观测调度器
│   │   ├── enhanced_scheduler.py # 增强调度器
│   │   ├── executor.py         # 观测执行器
│   │   ├── workflow.py         # 观测工作流
│   │   ├── realtime.py         # 实时观测
│   │   └── sky_chart.py        # 星图 API 封装
│   ├── telescope/              # 望远镜控制
│   │   ├── seestar_client.py   # Seestar S50 客户端
│   │   ├── simulator.py        # 望远镜模拟器
│   │   ├── scheduler.py        # 望远镜调度
│   │   ├── mqtt_bridge.py      # MQTT 桥接
│   │   └── linker.py           # 设备连接器
│   ├── research/               # 研究闭环
│   │   ├── hypothesis.py       # 假说模型
│   │   ├── hypothesis_tester.py # 假说检验器
│   │   ├── discovery.py        # 发现引擎
│   │   ├── literature.py       # 文献检索
│   │   ├── linker.py           # 知识链接
│   │   └── loop.py             # 研究循环
│   ├── data/                   # 数据处理
│   │   ├── collector.py        # 数据采集
│   │   ├── processor.py        # 数据处理
│   │   ├── classifier.py       # 数据分类
│   │   ├── miner.py            # 数据挖掘
│   │   ├── analysis.py         # 数据分析
│   │   ├── kepler.py           # Kepler 数据
│   │   └── weather.py          # 气象数据
│   ├── memory/                 # 记忆系统
│   │   ├── persistence.py      # 持久化记忆
│   │   ├── vector.py           # 向量记忆
│   │   ├── vector_store.py     # 向量存储
│   │   ├── rag.py              # RAG 检索
│   │   ├── session.py          # 会话管理
│   │   └── scenario.py         # 场景记忆
│   ├── learning/               # 学习系统
│   │   ├── dream.py            # 梦想学习
│   │   ├── overfit.py          # 过拟合检测
│   │   ├── rl_scheduler.py     # 强化学习调度
│   │   └── skill_integration.py # 技能整合
│   ├── utils/                  # 工具模块
│   │   ├── config.py           # 配置管理
│   │   ├── logger.py           # 日志工具
│   │   ├── sandbox.py          # 代码沙箱
│   │   ├── visualization.py    # 可视化工具
│   │   └── models.py           # 数据模型
│   └── web/                    # Web 服务
│       ├── dashboard.py        # 统计面板
│       ├── bridge.py           # 实时桥接
│       └── session.py          # Web 会话
├── web/                        # 前端静态文件
│   └── index.html              # 单页应用 (SPA)
├── tests/                      # 测试文件
├── Dockerfile                  # Docker 镜像构建
├── docker-compose.yml          # Docker Compose 编排
├── railway.json                # Railway 部署配置
├── requirements.txt            # Python 依赖
├── Procfile                    # Railway 部署配置
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略规则
├── .bandit                     # 安全扫描配置
├── .pre-commit-config.yaml     # Pre-commit 钩子
└── README.md                   # 项目文档
```

---

## 🔄 CI/CD 流程

### GitHub Actions 工作流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  ci.yml      │     │docker-build  │     │ deploy-railway   │
│              │     │  .yml        │     │  .yml            │
├──────────────┤     ├──────────────┤     ├──────────────────┤
│ 1. Lint      │     │ 1. Checkout  │     │ 1. Checkout      │
│   (flake8)   │     │ 2. Docker    │     │ 2. Setup Node.js │
│ 2. Test      │     │    Buildx    │     │ 3. Railway CLI   │
│   (pytest)   │     │ 3. GHCR      │     │ 4. Deploy        │
│ 3. Docker    │     │    Login     │     │ 5. Health Check  │
│    Build     │     │ 4. Build &   │     │                  │
│              │     │    Push      │     │                  │
└──────────────┘     └──────────────┘     └──────────────────┘
 触发: push/PR       触发: push/tag        触发: push/tag
       main,trae          main,trae,v*           main,trae,v*
```

### Docker 镜像

镜像自动推送到 **GitHub Container Registry (GHCR)**:

```bash
# 拉取最新镜像
docker pull ghcr.io/ll-lk/tianwen-agi:latest

# 或指定版本
docker pull ghcr.io/ll-lk/tianwen-agi:main
docker pull ghcr.io/ll-lk/tianwen-agi:v2.3.0
```

---

## 🔒 安全说明

### 已实施的安全措施

- ✅ `.env` 文件已在 `.gitignore` 中排除
- ✅ API Key 使用 `secrets.compare_digest()` 防时序攻击
- ✅ 生产环境强制 HTTPS (HSTS)
- ✅ 安全响应头 (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)
- ✅ CORS 白名单控制
- ✅ 速率限制 (默认 30 次/60 秒)
- ✅ Docker 非 root 用户运行
- ✅ 输入 sanitization (字符串截断)
- ✅ 生产环境隐藏详细错误信息
- ✅ Bandit 安全扫描配置

### 安全建议

1. **生产环境必须设置强 API_KEY**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **设置 DEBUG=false** (生产环境默认)

3. **配置 CORS_ORIGINS** 为你的前端域名

4. **定期轮换 API Key**

5. **不要在代码中硬编码任何密钥**

---

## 🗺 路线图

### v2.4 (已完成 ✅)

- [x] 可视化闭环工作流引擎 (WorkflowEngine)
- [x] 7 个预置工作流模板
- [x] 工作流导入/导出 (JSON)
- [x] 工作流执行统计面板
- [x] WebSocket 工作流实时推送
- [x] Dockerfile 优化 (curl 健康检查、runtime 目录)
- [x] CI/CD 流程完善 (flake8 修复、Railway 部署优化)
- [x] 前后端 CORS 连通性配置

### v2.5 (计划中)

- [ ] 真实望远镜 (Seestar S50) 完整集成
- [ ] Neo4j 图数据库知识图谱
- [ ] 多语言支持 (i18n)
- [ ] PWA 离线支持增强
- [ ] 观测数据导出 (CSV/FITS)

### v2.6 (远期)

- [ ] 多观测站协同
- [ ] 实时天体分类深度学习模型
- [ ] 自动生成观测报告 (PDF)
- [ ] 移动端适配
- [ ] 社区插件系统

---

## 🤝 贡献指南

欢迎贡献！请遵循以下流程：

1. **Fork** 本仓库
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'feat: add amazing feature'`
4. 推送到分支: `git push origin feature/amazing-feature`
5. 创建 **Pull Request**

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

| 类型 | 说明 |
|------|------|
| `feat:` | 新功能 |
| `fix:` | Bug 修复 |
| `docs:` | 文档更新 |
| `refactor:` | 代码重构 |
| `perf:` | 性能优化 |
| `test:` | 测试相关 |
| `chore:` | 构建/工具变更 |

### 代码质量

```bash
# 安装 pre-commit 钩子
pip install pre-commit
pre-commit install

# 运行检查
pre-commit run --all-files
```

---

## 📄 许可证

本项目基于 **MIT License** 开源。

```
MIT License

Copyright (c) 2025-2026 LL-LK

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/LL-LK">LL-LK</a></sub>
  <br>
  <sub>🔭 天问-AGI · 让天文观测智能化</sub>
</p>
