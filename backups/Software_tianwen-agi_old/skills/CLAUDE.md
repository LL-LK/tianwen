# Skills 技能索引

> Hermes-AGI 通用智能体技能库 - 持续进化中

---

## 核心引擎 (3)

| 技能 | 文件 | 作用 |
|-----|------|-----|
| 认知引擎 | [Cognitive-Engine.md](./Cognitive-Engine.md) | 理解用户输入、意图识别、实体提取 |
| 规划引擎 | [Planning-Engine.md](./Planning-Engine.md) | 任务分解、依赖分析、执行规划 |
| 执行引擎 | [Execution-Engine.md](./Execution-Engine.md) | 技能调用、结果验证、输出整合 |

---

## 调度与进化 (3)

| 技能 | 文件 | 作用 |
|-----|------|-----|
| 产品经理 | [Product-Manager.md](./Product-Manager.md) | 协调所有技能的核心调度中枢 |
| 自我进化 | [Self-Evolution.md](./Self-Evolution.md) | 持续学习、自我优化、策略改进 |
| 长期记忆 | [Long-Term-Memory.md](./Long-Term-Memory.md) | 知识持久化、知识图谱、检索 |

---

## 总索引 (1)

| 技能 | 文件 | 作用 |
|-----|------|-----|
| **Hermes-AGI** | [Hermes-AGI.md](./Hermes-AGI.md) | 统一接口、完整能力矩阵 |

---

## 开发技能 (8)

| 技能 | 文件 | 触发关键词 |
|-----|------|-----------|
| UI 视觉设计 | [UI-Visual.md](./UI-Visual.md) | 界面设计、视觉规范、CSS 样式 |
| 前端开发 | [Frontend.md](./Frontend.md) | React、Vue、TypeScript、前端组件 |
| React 开发 | [React.md](./React.md) | React 18、Hooks、状态管理、性能优化 |
| Node.js 后端 | [NodeJS-Backend.md](./NodeJS-Backend.md) | Fastify、Prisma、TypeScript、API |
| Python 后端 | [Python-Backend.md](./Python-Backend.md) | FastAPI、Django、异步编程 |
| 数据库设计 | [Database.md](./Database.md) | SQL、PostgreSQL、表设计、索引 |
| API 设计 | [API-Design.md](./API-Design.md) | RESTful、接口规范、响应格式 |
| 微信小程序 | [WeChat-MiniProgram.md](./WeChat-MiniProgram.md) | 微信小程序、云开发、微信支付 |

---

## 质量保障 (6)

| 技能 | 文件 | 触发关键词 |
|-----|------|-----------|
| 代码审查 | [Code-Review.md](./Code-Review.md) | 代码审查、review、PR 检查 |
| 代码重构 | [Refactoring.md](./Refactoring.md) | 重构、代码改进、坏味道 |
| 测试技能 | [Testing.md](./Testing.md) | 单元测试、集成测试、E2E |
| 安全审查 | [Security.md](./Security.md) | 安全漏洞、XSS、注入、OWASP |
| 调试排错 | [Debugging.md](./Debugging.md) | bug、调试、问题定位 |
| 数据结构算法 | [DSA.md](./DSA.md) | 算法、排序、树、图、动态规划 |

---

## 架构与运维 (5)

| 技能 | 文件 | 触发关键词 |
|-----|------|-----------|
| 架构设计 | [Architecture.md](./Architecture.md) | 系统架构、微服务、技术选型 |
| DevOps | [DevOps.md](./DevOps.md) | CI/CD、Docker、K8s |
| Linux 运维 | [Linux-Operations.md](./Linux-Operations.md) | Linux、Shell、服务器管理 |
| 云服务部署 | [Cloud-Deployment.md](./Cloud-Deployment.md) | 阿里云、腾讯云、ECS、RDS |
| Git 工作流 | [Git-Workflow.md](./Git-Workflow.md) | Git、分支策略、合并冲突 |

---

## AI 相关 (2)

| 技能 | 文件 | 触发关键词 |
|-----|------|-----------|
| 提示词工程 | [Prompt-Engineering.md](./Prompt-Engineering.md) | 提示词、ChatGPT、Claude、AI 交互 |
| AI Agent 设计 | [AI-Agent.md](./AI-Agent.md) | Agent、多智能体、工具调用、ReAct |

---

## 数据与分析 (1)

| 技能 | 文件 | 触发关键词 |
|-----|------|-----------|
| 全栈数据分析 | [Data-Analysis.md](./Data-Analysis.md) | 数据分析、Python、统计分析、机器学习 |

---

## 产品与项目管理 (2)

| 技能 | 文件 | 触发关键词 |
|-----|------|-----------|
| 产品需求分析 | [Product.md](./Product.md) | 需求分析、用户故事、PRD |
| 项目管理 | [Project-Management.md](./Project-Management.md) | 项目规划、Sprint、敏捷开发 |

---

## 职业发展 (2)

| 技能 | 文件 | 触发关键词 |
|-----|------|-----------|
| 简历优化 | [Resume-Optimization.md](./Resume-Optimization.md) | 简历优化、技术简历、STAR 法则 |
| 面试准备 | [Interview-Preparation.md](./Interview-Preparation.md) | 面试题、算法、系统设计 |

---

## 辅助文档

| 文档 | 说明 |
|-----|------|
| [Skill-Creation-Guide.md](./Skill-Creation-Guide.md) | 技能创建指南与经验总结 |

---

## 架构层级

```
┌─────────────────────────────────────────────────┐
│            Hermes-AGI 统一接口                    │
├─────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ 认知引擎 │  │ 规划引擎 │  │   执行引擎      │ │
│  └─────────┘  └─────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │     Product-Manager 调度中枢              │  │
│  └──────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│  开发技能 │ 质量保障 │ 架构运维 │ 数据 │ AI  │  │
├─────────────────────────────────────────────────┤
│  自我进化系统 │ 长期记忆系统                      │
└─────────────────────────────────────────────────┘
```

---

## 版本记录

| 日期 | 版本 | 更新内容 |
|-----|------|---------|
| 2026/04/28 | v1.0.0 | 初始创建，17个技能 |
| 2026/04/28 | v1.1.0 | 扩展至 26 个技能 |
| 2026/04/29 | v2.0.0 | AGI架构升级，33个技能，3大核心引擎 |
