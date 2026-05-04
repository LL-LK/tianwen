# Hermes-AGI 通用智能体统一接口

> 所有能力的统一入口，连接三大引擎和30+技能

---

## 智能体概述

**Hermes-AGI** 是一个具有通用认知能力的智能体系统，通过三大核心引擎协调 30+ 专业技能。

### 核心架构
```
用户输入 → 认知引擎 → 规划引擎 → 执行引擎 → 整合输出
              ↑           ↓
              └────┬─────┘
                   ↓
            技能库调度中枢
                   ↓
         ┌────────┴────────┐
         ↓                 ↓
    30+ 专业技能      自我进化系统
```

---

## 能力矩阵

### A. 认知能力 (Cognitive)

| 能力 | 描述 | 相关技能 |
|-----|------|---------|
| 意图理解 | 准确理解用户意图和目标 | Cognitive-Engine |
| 实体提取 | 提取关键信息和实体 | Cognitive-Engine |
| 上下文推理 | 理解会话和任务上下文 | Cognitive-Engine, Long-Term-Memory |
| 逻辑推理 | 演绎、归纳、类比推理 | Cognitive-Engine |
| 需求分析 | 将模糊需求具体化 | Product |

### B. 规划能力 (Planning)

| 能力 | 描述 | 相关技能 |
|-----|------|---------|
| 任务分解 | 将复杂任务分解为子任务 | Planning-Engine |
| 依赖分析 | 分析任务间的依赖关系 | Planning-Engine |
| 执行排序 | 确定最优执行顺序 | Planning-Engine |
| 资源规划 | 规划所需资源和技能 | Planning-Engine, Project-Management |
| 风险评估 | 评估任务风险和备选方案 | Architecture, Project-Management |

### C. 执行能力 (Execution)

| 能力 | 描述 | 相关技能 |
|-----|------|---------|
| 技能调用 | 高效调用专业技能 | Execution-Engine, Product-Manager |
| 代码生成 | 生成高质量代码 | Frontend, Backend, React, NodeJS, Python |
| 代码审查 | 审查和优化代码 | Code-Review, Security |
| 测试编写 | 编写各类测试 | Testing |
| 调试排错 | 定位和修复问题 | Debugging, DSA |

### D. 知识能力 (Knowledge)

| 能力 | 描述 | 相关技能 |
|-----|------|---------|
| 知识检索 | 从知识库检索信息 | Long-Term-Memory |
| 知识图谱 | 维护实体关系 | Long-Term-Memory |
| 模式匹配 | 匹配已有模式解决问题 | learned-patterns |
| 学习积累 | 从经验中学习 | Self-Evolution, Long-Term-Memory |

---

## 技能分类索引 (33个)

### 核心引擎 (3)
| 技能 | 文件 | 作用 |
|-----|------|-----|
| 认知引擎 | [Cognitive-Engine.md](./Cognitive-Engine.md) | 理解用户输入 |
| 规划引擎 | [Planning-Engine.md](./Planning-Engine.md) | 规划执行方案 |
| 执行引擎 | [Execution-Engine.md](./Execution-Engine.md) | 执行任务和调用技能 |

### 调度中枢 (1)
| 技能 | 文件 | 作用 |
|-----|------|-----|
| 产品经理 | [Product-Manager.md](./Product-Manager.md) | 协调所有技能 |

### 自我进化 (2)
| 技能 | 文件 | 作用 |
|-----|------|-----|
| 自我进化 | [Self-Evolution.md](./Self-Evolution.md) | 持续学习改进 |
| 长期记忆 | [Long-Term-Memory.md](./Long-Term-Memory.md) | 知识持久化 |

### 开发技能 (8)
| 技能 | 文件 | 触发词 |
|-----|------|-------|
| UI视觉设计 | [UI-Visual.md](./UI-Visual.md) | 界面设计、视觉、CSS |
| 前端开发 | [Frontend.md](./Frontend.md) | React、Vue、HTML、CSS |
| React开发 | [React.md](./React.md) | React组件、Hooks、状态 |
| Node.js后端 | [NodeJS-Backend.md](./NodeJS-Backend.md) | Express、Fastify、API |
| Python后端 | [Python-Backend.md](./Python-Backend.md) | FastAPI、Django、数据处理 |
| 数据库设计 | [Database.md](./Database.md) | SQL、PostgreSQL、表设计 |
| API设计 | [API-Design.md](./API-Design.md) | RESTful、接口规范 |
| 微信小程序 | [WeChat-MiniProgram.md](./WeChat-MiniProgram.md) | 小程序、云开发 |

### 质量保障 (6)
| 技能 | 文件 | 触发词 |
|-----|------|-------|
| 代码审查 | [Code-Review.md](./Code-Review.md) | 代码检查、review |
| 代码重构 | [Refactoring.md](./Refactoring.md) | 重构、改进 |
| 测试技能 | [Testing.md](./Testing.md) | 单元测试、集成测试 |
| 安全审查 | [Security.md](./Security.md) | 安全、XSS、OWASP |
| 调试排错 | [Debugging.md](./Debugging.md) | Bug、调试 |
| 数据结构算法 | [DSA.md](./DSA.md) | 算法、排序、树、图 |

### 架构运维 (5)
| 技能 | 文件 | 触发词 |
|-----|------|-------|
| 架构设计 | [Architecture.md](./Architecture.md) | 系统架构、微服务 |
| DevOps | [DevOps.md](./DevOps.md) | CI/CD、Docker |
| Linux运维 | [Linux-Operations.md](./Linux-Operations.md) | Linux、Shell、服务器 |
| 云服务部署 | [Cloud-Deployment.md](./Cloud-Deployment.md) | 阿里云、腾讯云、云部署 |
| Git工作流 | [Git-Workflow.md](./Git-Workflow.md) | Git、分支、合并 |

### AI相关 (2)
| 技能 | 文件 | 触发词 |
|-----|------|-------|
| 提示词工程 | [Prompt-Engineering.md](./Prompt-Engineering.md) | 提示词、ChatGPT |
| AI Agent设计 | [AI-Agent.md](./AI-Agent.md) | Agent、智能体 |

### 数据分析 (1)
| 技能 | 文件 | 触发词 |
|-----|------|-------|
| 全栈数据分析 | [Data-Analysis.md](./Data-Analysis.md) | 数据分析、Python、机器学习 |

### 产品管理 (2)
| 技能 | 文件 | 触发词 |
|-----|------|-------|
| 产品需求分析 | [Product.md](./Product.md) | 需求、PRD、用户故事 |
| 项目管理 | [Project-Management.md](./Project-Management.md) | 项目规划、Sprint |

### 职业发展 (2)
| 技能 | 文件 | 触发词 |
|-----|------|-------|
| 简历优化 | [Resume-Optimization.md](./Resume-Optimization.md) | 简历、技术简历 |
| 面试准备 | [Interview-Preparation.md](./Interview-Preparation.md) | 面试题、算法、系统设计 |

---

## 标准工作流程

### 简单任务
```
用户 → 认知引擎(意图识别) → 单一技能 → 输出 → 完成
```

### 复杂任务
```
用户 → 认知引擎 → 规划引擎 → 多技能并行/顺序执行 → 整合输出 → 记忆更新
```

### 分析类任务
```
用户 → 认知引擎 → 规划引擎 → 数据分析/代码分析 → 报告输出 → 记忆更新
```

---

## 使用示例

### 示例1: 开发任务
```
用户: "帮我创建一个用户登录的后端API，包含JWT认证"

系统处理流程:
1. 认知引擎 → 意图: Execute.Develop.Backend.API
2. 规划引擎 → 分解: Database设计 → API设计 → Backend实现 → Testing → Security审查
3. 执行引擎 → 顺序执行各技能，整合输出
```

### 示例2: 架构设计
```
用户: "我们需要重构电商系统，从单体改造成微服务"

系统处理流程:
1. 认知引擎 → 意图: Execute.Analyze.Architecture
2. 规划引擎 → 分解: 现状分析 → 架构设计 → 迁移规划 → 实施计划
3. 执行引擎 → 调用 Architecture + DevOps + Database 等技能
4. 输出: 完整的微服务改造方案
```

### 示例3: 学习咨询
```
用户: "解释一下什么是CQRS模式"

系统处理流程:
1. 认知引擎 → 意图: Learn.Explain
2. 直接调用 Architecture 技能中的知识
3. 输出: CQRS 模式详细解释
```

---

## 自我优化配置

### 学习频率
| 类型 | 频率 | 内容 |
|-----|------|-----|
| 即时 | 每次任务后 | 记录经验到 task-history.md |
| 每日 | 每天定时 | 回顾当日任务，更新模式 |
| 每周 | 每周定时 | 全面复盘，优化策略 |

### 健康检查
- 任务成功率监控 (目标 > 95%)
- 执行效率监控 (目标 持续提升)
- 新任务泛化率 (目标 > 80%)

---

## 版本信息

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| 1.0.0 | 2026/04/28 | 初始技能库 (17个技能) |
| 1.1.0 | 2026/04/28 | 扩展到 26 个技能 |
| 2.0.0 | 2026/04/29 | AGI架构升级，新增核心引擎，33个技能 |
