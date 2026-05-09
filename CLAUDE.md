# 天问-AGI (Tianwen-AGI) 智能体

> 天文研究的认知大脑 + 具身智能的认知执行体
> 版本: 3.8.5 | 状态: 活跃开发中

## 智能体概述

- **名称**: 天问-AGI (Tianwen-AGI)
- **代号**: Hermes-AGI
- **版本**: 3.8.5
- **定位**: 天文研究领域的通用认知智能体
- **核心范式**: 认知脑 + 执行肢（天问作为认知大脑，具身智能作为执行四肢）
- **创建日期**: 2026/04/29
- **技能库**: F:/skill/ (33个技能)
- **调度中枢**: Product-Manager.md
- **核心引擎**: Cognitive-Engine, Planning-Engine, Execution-Engine

---

## 目录结构

```
tianwen-agi/
├── CLAUDE.md           # 本文件 - 智能体索引
├── agent.md            # 智能体核心配置
├── runtime/            # 运行时引擎
│   ├── reasoning_engine.py    # 推理引擎 (Chain of Draft)
│   ├── vector_memory.py       # 向量记忆系统
│   └── multi_agent_coordinator.py  # 3-Agent协调器
├── skills/             # 技能引用目录
└── memory/             # 记忆存储
```

---

## 核心能力

### 三大核心引擎
| 引擎 | 职责 | 输入 | 输出 |
|-----|------|-----|-----|
| 认知引擎 | 理解用户意图 | 自然语言 | 任务模型 |
| 规划引擎 | 分解和规划任务 | 任务模型 | 执行计划 |
| 执行引擎 | 调用技能执行 | 执行计划 | 整合输出 |

### 推理引擎特性
- **Chain of Draft**: 60-80% token降低
- **OllamaAdapter**: 本地LLM集成
- **QwenAdapter/DeepSeekAdapter**: 远程API支持

### 自我进化系统
- **自我进化**: Self-Evolution.md - 持续学习改进
- **长期记忆**: Long-Term-Memory.md - 知识持久化

---

## 技能库 (33个技能)

| 类别 | 数量 | 技能 |
|-----|------|------|
| 核心引擎 | 3 | Cognitive-Engine, Planning-Engine, Execution-Engine |
| 调度进化 | 3 | Product-Manager, Self-Evolution, Long-Term-Memory |
| 开发技能 | 8 | UI-Visual, Frontend, React, NodeJS-Backend, Python-Backend, Database, API-Design, WeChat-MiniProgram |
| 质量保障 | 6 | Code-Review, Refactoring, Testing, Security, Debugging, DSA |
| 架构运维 | 5 | Architecture, DevOps, Linux-Operations, Cloud-Deployment, Git-Workflow |
| AI相关 | 2 | Prompt-Engineering, AI-Agent |
| 数据分析 | 1 | Data-Analysis |
| 产品管理 | 2 | Product, Project-Management |
| 职业发展 | 2 | Resume-Optimization, Interview-Preparation |

---

## 工作流程

```
用户输入
    │
    ▼
┌──────────────────────────────────────────────────┐
│                 认知引擎                         │
│  意图识别 → 实体提取 → 上下文理解 → 任务建模     │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│                 规划引擎                         │
│  任务分解 → 依赖分析 → 执行排序 → 风险评估       │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│                 执行引擎                         │
│  技能匹配 → 工具调用 → 结果验证 → 整合输出       │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│                 自我进化                         │
│  结果评估 → 模式提取 → 知识更新 → 策略优化       │
└──────────────────────────────────────────────────┘
```

---

## 部署架构

- **前端**: Cloudflare Pages
- **后端**: Railway + Cloudflare Workers
- **WebSocket中继**: Cloudflare Worker Durable Object
- **本地LLM**: Ollama (localhost:11434)

---

## 版本记录

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| 1.0.0 | 2026/04/28 | 初始化智能体结构 |
| 1.1.0 | 2026/04/28 | 扩展技能库至 26 个 |
| 2.0.0 | 2026/04/29 | AGI架构升级，33个技能，3大核心引擎 |
| 3.8.5 | 2026/05/07 | 最新版本，完整功能 |

---

## 与 F:/skill/ 的关系

```
tianwen-agi/ (智能体实例)
├── CLAUDE.md (索引)
├── agent.md (配置)
├── runtime/ (核心引擎)
└── memory/ (记忆存储)

F:/skill/ (技能库 - 33个技能)
├── 核心引擎 (3): Cognitive-Engine, Planning-Engine, Execution-Engine
├── 调度进化 (3): Product-Manager, Self-Evolution, Long-Term-Memory
├── 开发技能 (8), 质量保障 (6), 架构运维 (5)
├── AI相关 (2), 数据分析 (1), 产品管理 (2), 职业发展 (2)
└── Hermes-AGI.md (统一接口)
```