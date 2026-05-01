# 天问-AGI 未完成工作汇总

> 生成时间: 2026-05-01 11:05 CST (北京时间)
> 关联Issue: #2 (Web部署), #11 (v3.4.0规划), #12 (未完成任务同步)
> 分析者: Claude Agent

---

## 一、P0优先级未完成项 (必须立即解决)

### 1.1 闭环成功率统计面板

| 属性 | 内容 |
|-----|------|
| **名称** | 闭环成功率统计面板 (R0) |
| **来源** | Issue #11 (v3.4.0规划) |
| **优先级** | P0 |
| **状态** | 🔴 未解决 |
| **阻塞原因** | 无法量化研究闭环成功率，无法针对性优化 |
| **建议解决方式** | 在 `discovery_tracker.py` 增加 `get_cycle_statistics()` 方法，建立Neo4j统计面板，追踪假说→验证→发现的全流程成功率 |

### 1.2 Web部署 Phase 1 待执行

| 属性 | 内容 |
|-----|------|
| **名称** | Web部署 (Phase 1简化方案) |
| **来源** | Issue #2 |
| **优先级** | P0 |
| **状态** | ❌ 未开始 |
| **阻塞原因** | 依赖 Issue #1 (集成测试) 未完成 |
| **具体任务** | 1. 完成 `/api/health` 端点增强 (DB/API/依赖检查) |
|                   2. Railway后端部署 (环境变量: DEEPSEEK_API_KEY, QWEN_ENDPOINT, SESSION_SECRET) |
|                   3. Cloudflare Pages前端部署 |
|                   4. 创建 docker-compose.yml (当前0%完成) |
| **建议解决方式** | 1. 先完成 Issue #1 集成测试验证 |
|                   2. 参考 ISSUE2_HERMES_REPLY.md 的四阶段计划 (D+1 到 D+5) |
|                   3. Railway冷启动风险应对: 备选 Render 平台 |

---

## 二、P1优先级未完成项 (重要)

### 2.1 本地文献数据库缺失

| 属性 | 内容 |
|-----|------|
| **名称** | 本地文献数据库 |
| **来源** | Issue #6评审 (v3.1.0进展报告) |
| **优先级** | P1 |
| **状态** | 🔴 不存在 (声明的 LITERATURE.md 文件不存在) |
| **阻塞原因** | 无法积累研究知识，文献调研缺少持久化存储 |
| **建议解决方式** | 创建 Markdown 格式文献库，初始20篇论文，4个分类 (恒星/星系/星云/系外行星) |

### 2.2 ChromaDB向量检索未实现

| 属性 | 内容 |
|-----|------|
| **名称** | ChromaDB向量检索集成 |
| **来源** | Issue #9评审 (v3.4.0优化报告) |
| **优先级** | P1 |
| **状态** | ⚠️ 接口存在但 NotImplementedError |
| **阻塞原因** | `literature_researcher.py` 中 ChromaDBVectorStore 所有方法抛出 NotImplementedError |
| **建议解决方式** | 1. 集成 sentence-transformers (all-MiniLM-L6-v2, 384维) |
|                   2. 实现 ChromaDBVectorStore 或继续使用 SimpleVectorStore |
|                   3. v3.5.0 计划升级到 ChromaDB |

### 2.3 Neo4j连接验证缺失

| 属性 | 内容 |
|-----|------|
| **名称** | Neo4j连接重试机制 |
| **来源** | Issue #6评审 |
| **优先级** | P1 |
| **状态** | ⚠️ 静默失败，无重试机制 |
| **阻塞原因** | 图数据库连接未验证，网络请求会静默失败 |
| **建议解决方式** | 添加连接池和 tenacity 重试机制 (v3.5.0 已实现) |

### 2.4 统计假设检验精度低

| 属性 | 内容 |
|-----|------|
| **名称** | 统计假设检验实现 |
| **来源** | Issue #6评审 |
| **优先级** | P1 |
| **状态** | ⚠️ 仅用关键词匹配，精度低 |
| **阻塞原因** | hypothesis_tester.py 缺少真实的统计检验 |
| **建议解决方式** | 集成 scipy.stats 进行 t检验/卡方检验 (v3.5.0 已实现统计模块) |

### 2.5 多任务并行优化

| 属性 | 内容 |
|-----|------|
| **名称** | 多任务并行优化 (≤3并行) |
| **来源** | Issue #3 (竞品分析) |
| **优先级** | P1 |
| **状态** | ⚠️ 设计完成，实现待验证 |
| **阻塞原因** | 上下文溢出风险，需独立Neo4j session隔离 |
| **建议解决方式** | 实现 ParallelTaskManager: ≤3并行任务、独立session、超时监控 |

---

## 三、P2优先级未完成项 (改进)

### 3.1 全栈数据分析 (ML异常检测)

| 属性 | 内容 |
|-----|------|
| **名称** | 全栈数据分析 - ML增强 |
| **来源** | Issue #12, PRO_DATA_ANALYSIS_FULL_STACK.md |
| **优先级** | P2 |
| **状态** | ⏳ 待v3.4.0实现 |
| **阻塞原因** | v3.4.0里程碑任务，当前仅完成基础统计分析 |
| **建议解决方式** | 1. 短期: 集成PyADAP统计检验自动化、Isolation Forest多方法异常检测 |
|                   2. 中期: 实现效应量自动计算 (Cohen's d / η² / r)、Plotly交互式图表 |
|                   3. 参考 PRO_DATA_ANALYSIS_FULL_STACK.md 的六阶段流程图 |

### 3.2 浏览器搜索集成

| 属性 | 内容 |
|-----|------|
| **名称** | 浏览器搜索集成 (Playwright) |
| **来源** | Issue #12, PRO_BROWSER_SIMULATION_MULTIAGENT_20260501.md |
| **优先级** | P2 |
| **状态** | ⏳ 设计完成，实现待启动 |
| **阻塞原因** | WebSearch/WebFetch API返回400错误，需模拟浏览器行为 |
| **建议解决方式** | 1. 集成 Playwright (87K stars) 实现浏览器自动化 |
|                   2. 实现4-Agent并行搜索: arxiv_searcher, scholar_searcher, github_searcher, nasa_searcher |
|                   3. 应用 playwright-stealth 反检测 |
|                   4. 参考 PRO_BROWSER_SIMULATION_MULTIAGENT_20260501.md 的技术方案 |

### 3.3 3D可视化

| 属性 | 内容 |
|-----|------|
| **名称** | 3D可视化 (天文数据多维展示) |
| **来源** | Issue #12, Issue #3 |
| **优先级** | P3 (长期规划) |
| **状态** | ⏳ 列入规划 |
| **阻塞原因** | 长期目标，需要前置的统计数据基础 |
| **建议解决方式** | v4.0目标，使用ThreeJS/WebGL实现天文数据3D可视化 |

### 3.4 AstroIR集成评估

| 属性 | 内容 |
|-----|------|
| **名称** | AstroIR感知层集成 |
| **来源** | Issue #4, PRO_COMPETITION_ANALYSIS.md |
| **优先级** | P2 |
| **状态** | ⚠️ 待集成 (stars=0, forks=0 项目) |
| **阻塞原因** | 需评估作为感知层的可行性，与天问认知层垂直整合 |
| **建议解决方式** | 1. 评估 Phosphoros (P0, 2000万+星系图像预训练) |
|                   2. 评估 FIRESTAR (P0, 星系巡天专用) |
|                   3. 建立 AstroIR → 天问 的垂直整合架构 |

---

## 四、阻塞项与依赖关系

### 4.1 关键依赖链

```
Issue #1 (集成测试未完成)
    ↓ 阻塞
Issue #2 (Web部署无法启动)
    ↓ 阻塞
v3.5.0 生产就绪版本
```

### 4.2 并行可执行任务

| 任务 | 可并行原因 |
|-----|-----------|
| 全栈数据分析 | 不依赖集成测试，与Web部署并行 |
| 浏览器搜索集成 | 不依赖集成测试，独立模块 |
| AstroIR集成评估 | 不依赖集成测试，评估阶段 |

### 4.3 需先完成的前置任务

| 前置任务 | 阻塞的后续任务 |
|---------|---------------|
| Issue #1集成测试 | Web部署 (Issue #2) |
| docker-compose.yml | Railway部署 |
| /api/health端点增强 | Cloudflare前端联调 |

---

## 五、v3.5.0里程碑 (生产就绪版本)

| 里程碑 | 目标 | 截止日期 |
|-------|------|---------|
| M1 | 完成集成测试 (Issue #1收尾) | D+2 |
| M2 | 完成Web部署 (Railway + Cloudflare) | D+3 |
| M3 | 完成Qwen3-32B测试 | D+5 |
| M4 | 完成RAG增强 (ChromaDB实现) | D+8 |

---

## 六、建议行动项 (按优先级)

### 立即执行 (1-2天)

1. **完成 Issue #1 集成测试** - 解除对 Issue #2 的阻塞
2. **创建 docker-compose.yml** - 标准容器编排 (server/vector-db/frontend)
3. **增强 /api/health 端点** - system/dependencies/sessions/database 检查

### 短期规划 (1周)

4. **部署 Railway 后端** - 环境变量配置
5. **部署 Cloudflare 前端** - API Base切换
6. **创建本地文献数据库** - LITERATURE.md 20篇初始论文

### 中期规划 (2周)

7. **完成全栈数据分析** - ML异常检测、统计检验自动化
8. **实现浏览器搜索** - Playwright + 4-Agent并行
9. **完成 ChromaDB 集成** - 向量检索增强

---

*文档生成时间: 2026-05-01 11:05 CST*
*分析依据: ISSUE2_HERMES_REPLY.md, PRO_HERMES_SUMMARY_20260501.md, PRO_DATA_ANALYSIS_FULL_STACK.md, PRO_BROWSER_SIMULATION_MULTIAGENT_20260501.md, PRODUCT.md, ISSUE6_PRO_REVIEW.md, ISSUE9_PRO_REVIEW.md*