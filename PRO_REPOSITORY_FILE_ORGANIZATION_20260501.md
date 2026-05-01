# 天问-AGI 仓库文件整理 PRO文档

> 文档生成时间: 2026-05-01 12:30 CST (北京时间)
> 生成者: Claude (Anthropic)
> 项目地址: https://github.com/LL-LK/tianwen-agi

---

## 一、文件分类总览

| 类别 | 目录 | 文件数 | 说明 |
|-----|------|--------|-----|
| 核心运行时 | runtime/ | 28 | Agent核心执行模块 |
| 技能文档 | skills/ | 48 | Agent技能与知识库 |
| 项目文档 | docs/ | 20+ | 各类PRO分析文档 |
| 记忆系统 | memory/ | 6 | 长期记忆与知识图谱 |
| Web界面 | web/ | 1 | 前端界面 |
| 测试文件 | runtime/tests/ | 3 | 集成测试 |
| 容器部署 | / | 2 | Docker配置 |
| 配置与日志 | / | 8+ | 项目配置与日志 |

---

## 二、按时间分类 (Version History)

### 2.1 v3.7.0 (最新, 2026-05-01)

| 文件 | 类型 | 说明 |
|-----|------|-----|
| runtime/vector_rag.py | 新增 | ChromaDB RAG增强模块 |
| verify_models.py | 新增 | 模型权重验证脚本 |
| runtime/astro_pipeline.py | 修改 | 观测闭环核心模块 |
| browser_search.py | 修改 | 修复GitHub/NASA搜索选择器 |

### 2.2 v3.6.0 (2026-05-01)

| 文件 | 类型 | 说明 |
|-----|------|-----|
| runtime/astro_pipeline.py | 新增 | 观测闭环核心模块 |
| runtime/enhanced_observation_scheduler.py | 新增 | 增强观测调度器 |
| runtime/kepler_exoplanet_client.py | 新增 | Kepler系外行星客户端 |
| runtime/cycle_statistics_dashboard.py | 新增 | 闭环统计面板 |
| runtime/observation_executor.py | 新增 | 观测执行器 |
| runtime/tests/test_observation_loop_integration.py | 新增 | 观测闭环测试 |
| download_models.sh | 新增 | 模型下载脚本 |
| PRO_V360_COMPLETION_20260501.md | 新增 | v3.6.0完成报告 |

### 2.3 v3.5.0 (2026-05-01)

| 文件 | 类型 | 说明 |
|-----|------|-----|
| runtime/hypothesis_tester.py | 修改 | 统计假设检验增强 |
| runtime/literature_researcher.py | 修改 | ChromaDB向量检索 |
| runtime/discovery_tracker.py | 修改 | 闭环统计、Neo4j重试 |
| runtime/reasoning_engine.py | 修改 | LRU推理缓存 |
| runtime/server.py | 修改 | 健康检查增强 |
| docker-compose.yml | 新增 | 容器编排配置 |
| Dockerfile | 新增 | 容器镜像定义 |
| runtime/tests/integration_test.py | 新增 | 集成测试(27用例) |

### 2.4 v3.4.0 (2026-04-30)

| 文件 | 类型 | 说明 |
|-----|------|-----|
| runtime/research_loop.py | 新增 | 自动化研究闭环 |
| runtime/hypothesis_generator.py | 新增 | 假说生成器 |
| runtime/hypothesis_tester.py | 新增 | 假说验证器 |
| runtime/discovery_tracker.py | 新增 | 发现追踪器 |
| runtime/data_miner.py | 新增 | 数据挖掘模块 |
| runtime/observatory_linker.py | 新增 | 观测站链接器 |

### 2.5 v3.0.0 (2026-04)

| 文件 | 类型 | 说明 |
|-----|------|-----|
| runtime/astro_analyzer.py | 新增 | 天文数据分析器 |
| runtime/astro_data_collector.py | 新增 | 天文数据收集器 |
| runtime/auto_observatory.py | 新增 | 全自动天文台 |
| runtime/observation_scheduler.py | 新增 | 观测调度器 |
| runtime/star_recognizer.py | 新增 | 恒星识别模块 |

### 2.6 v2.0-v2.3.0

| 文件 | 类型 | 说明 |
|-----|------|-----|
| runtime/server.py | 新增 | Web API服务器 |
| runtime/main.py | 新增 | Agent主入口 |
| runtime/vector_memory.py | 新增 | 向量记忆 |
| runtime/skill_integration.py | 新增 | 技能集成 |
| runtime/mcp_protocol.py | 新增 | MCP协议 |
| runtime/memory_persistence.py | 新增 | 记忆持久化 |
| runtime/sandbox.py | 新增 | 沙箱环境 |
| runtime/self_review.py | 新增 | 自我审查 |
| runtime/skill_tester.py | 新增 | 技能测试器 |
| runtime/visualization.py | 新增 | 可视化模块 |

### 2.7 v1.0 (初始化)

| 文件 | 类型 | 说明 |
|-----|------|-----|
| CLAUDE.md | 新增 | 项目说明 |
| agent.md | 新增 | Agent架构文档 |
| memory/ | 目录 | 记忆系统初始化 |
| skills/AI-Agent.md | 新增 | AI-Agent技能 |
| skills/API-Design.md | 新增 | API设计 |
| skills/Architecture.md | 新增 | 架构设计 |
| skills/Backend.md | 新增 | 后端技能 |
| skills/Cloud-Deployment.md | 新增 | 云部署 |

---

## 三、按应用分类

### 3.1 核心运行时 (runtime/)

| 模块 | 文件 | 功能 |
|-----|------|-----|
| **观测闭环** | astro_pipeline.py | 观测流程主管 |
| | observation_executor.py | 观测执行器 |
| | enhanced_observation_scheduler.py | 增强调度器 |
| | observation_scheduler.py | 基础调度器 |
| | kepler_exoplanet_client.py | Kepler数据客户端 |
| | observatory_linker.py | 观测站链接 |
| | auto_observatory.py | 全自动天文台 |
| **研究闭环** | research_loop.py | 研究循环主管 |
| | research_observatory_linker.py | 研究-观测联动 |
| | hypothesis_generator.py | 假说生成 |
| | hypothesis_tester.py | 假说验证 |
| | discovery_tracker.py | 发现追踪 |
| **数据处理** | astro_analyzer.py | 天文分析 |
| | astro_data_collector.py | 数据收集 |
| | data_miner.py | 数据挖掘 |
| | star_recognizer.py | 恒星识别 |
| **文献与检索** | literature_researcher.py | 文献调研 |
| | vector_memory.py | 向量记忆 |
| | vector_rag.py | RAG增强 |
| **推理与认知** | reasoning_engine.py | 推理引擎 |
| | self_review.py | 自我审查 |
| **Agent框架** | server.py | Web API |
| | main.py | 主入口 |
| | skill_integration.py | 技能集成 |
| | mcp_protocol.py | MCP协议 |
| | sandbox.py | 沙箱 |
| **持久化** | memory_persistence.py | 记忆持久化 |
| | visualization.py | 可视化 |
| **统计面板** | cycle_statistics_dashboard.py | 闭环统计 |
| **测试** | tests/integration_test.py | 集成测试 |
| | tests/test_observation_loop_integration.py | 观测闭环测试 |
| | tests/__init__.py | 测试初始化 |

**运行时文件总数**: 28个

### 3.2 技能文档 (skills/)

| 类别 | 文件 |
|-----|------|
| **核心技能** | AI-Agent.md, Reasoning.md, Tool-Usage.md, Multimodal.md |
| | Emotional-Understanding.md, Active-Learning.md |
| **工程技能** | Architecture.md, API-Design.md, Backend.md, Frontend.md |
| | Python-Backend.md, NodeJS-Backend.md, Database.md, Security.md |
| | Cloud-Deployment.md, DevOps.md, Git-Workflow.md, Testing.md |
| **应用技能** | Data-Analysis.md, DSA.md, Linux-Operations.md, Refactoring.md |
| **产品技能** | Product.md, Product-Manager.md, Project-Management.md |
| **天问特有** | Tianwen-AGI.md, AstroPipeline.md, PROJECT-JOURNEY.md |
| **其他** | Prompt-Engineering.md, Code-Review.md, Debugging.md, Testing.md |
| | Resume-Optimization.md, Interview-Preparation.md, WeChat-MiniProgram.md |
| | Long-Term-Memory.md, Skill-Creation-Guide.md, Demo-Script.md, Tester.md |
| | Cognitive-Engine.md, Execution-Engine.md, Planning-Engine.md, UI-Visual.md |

**技能文档总数**: 48个

### 3.3 项目文档 (根目录 *.md)

| 文档 | 说明 |
|-----|------|
| **PRO评审** | |
| PRO_ALL_ISSUES_SUMMARY_20260501.md | 所有Issue工作汇总 |
| PRO_HERMES_SUMMARY_20260501.md | Hermes评审汇总 |
| PRO_HERMES_REVIEW_20260501.md | Hermes综合评审 |
| PRO_HERMES_REVIEW_20260501_1017.md | Hermes评审(10:17) |
| PRO_HERMES_REVIEW_20260501_1031.md | Hermes评审(10:31) |
| PRO_HERMES_REVIEW_20260501_1205.md | Hermes评审(12:05) |
| **版本报告** | |
| PRO_V360_COMPLETION_20260501.md | v3.6.0完成报告 |
| PRO_V370_PLANNING_20260501.md | v3.7.0规划 |
| **Issue回复** | |
| ISSUE1_RESPONSE.md - ISSUE9_HERMES_REPLY.md | 各Issue回复 |
| ISSUE6_PRO_REVIEW.md, ISSUE8_PRO_REVIEW.md | PRO评审 |
| **竞品分析** | |
| PRO_COMPETITION_ANALYSIS.md | 竞品分析 |
| PRO_ASTRONOMICAL_AI_COMPARISON.md | 天文AI对比 |
| **技术分析** | |
| PRO_OVERFITTING_MULTIAGENT_ANALYSIS.md | 过拟合分析 |
| PRO_BROWSER_SIMULATION_MULTIAGENT_20260501.md | 浏览器模拟架构 |
| PRO_ASTRONOMICAL_LLM_COMPLETENESS_20260501.md | 功能完整性 |
| PRO_INTEGRATION_ANALYSIS_20260501.md | 集成可行性 |
| **文献与观测** | |
| LITERATURE.md | 文献数据库v2.0 |
| PRO_LITERATURE_OBSERVATION_LOOP_20260501.md | 文献-观测闭环 |
| PRO_DATA_ANALYSIS_FULL_STACK.md | 全栈数据分析 |
| **天文AI模型** | |
| ASTRONOMICAL_AI_MODELS_COMPARISON.md | 模型对比 |
| ASTRONOMICAL_FOUNDATION_MODELS.md | 基础模型 |
| EXOPLANET_AI_MODELS.md | 系外行星AI |
| GALAXY_MORPHOLOGY_AI.md | 星系形态AI |
| MODEL_DIFFERENCE_PREDICTION.md | 模型差异预测 |
| COMPUTATION_COMPARISON.md | 计算对比 |
| **实验复现** | |
| REPRODUCTION_EXPERIMENT.md | 复现实验 |
| reproduction_experiment.py | 复现脚本 |
| **搜索结果** | |
| EDGE_SEARCH_RESULTS.md | 搜索结果 |
| **实现文档** | |
| IMPLEMENTATION_DATA_MINER.md | 数据挖掘实现 |
| IMPLEMENTATION_OBSERVATORY_LINKER.md | 观测链接实现 |
| **完成/未完成** | |
| COMPLETED_WORK_SUMMARY.md | 已完成工作 |
| INCOMPLETE_WORK_SUMMARY.md | 未完成工作 |
| **其他** | |
| CLAUDE.md | 项目说明 |
| PRODUCT.md | 产品文档 |
| PROJECT_LOG.md | 项目日志 |
| PROJECT-JOURNEY.md | 发展历程 |
| PROFESSIONAL_REVIEW.md | 专业评审 |

### 3.4 搜索模块 (根目录)

| 文件 | 说明 |
|-----|------|
| browser_search.py | 浏览器搜索功能 |
| multi_agent_search.py | 多Agent搜索 |

### 3.5 容器部署 (根目录)

| 文件 | 说明 |
|-----|------|
| docker-compose.yml | 容器编排(server/vector-db/frontend) |
| Dockerfile | 服务镜像定义 |

### 3.6 记忆系统 (memory/)

| 文件 | 说明 |
|-----|------|
| evolution-log.md | 进化日志 |
| knowledge-graph.md | 知识图谱 |
| learned-patterns.md | 习得模式 |
| skill-feedback.md | 技能反馈 |
| task-history.md | 任务历史 |
| user-preferences.md | 用户偏好 |

### 3.7 Web界面 (web/)

| 文件 | 说明 |
|-----|------|
| index.html | 前端页面 |

---

## 四、文件大小与增量统计

| 类别 | 文件数 | 总增量 |
|-----|--------|--------|
| 核心运行时 | 28 | +2000+ 行 |
| 技能文档 | 48 | 500+ 行 |
| 项目文档 | 40+ | 3000+ 行 |
| 容器配置 | 2 | +300+ 行 |
| 搜索模块 | 2 | +500+ 行 |
| **总计** | **120+** | **+5800+ 行** |

---

## 五、目录结构树

```
F:\tianwen-agi\
├── agent.md                    # Agent架构
├── CLAUDE.md                   # 项目说明
├── PRODUCT.md                  # 产品文档
├── PROJECT_LOG.md              # 项目日志
├── PROJECT-JOURNEY.md          # 发展历程
├── PROFESSIONAL_REVIEW.md       # 专业评审
├── browser_search.py           # 浏览器搜索
├── multi_agent_search.py       # 多Agent搜索
├── reproduction_experiment.py   # 复现实验
├── verify_models.py            # 模型验证
├── docker-compose.yml          # 容器编排
├── Dockerfile                 # 容器镜像
├── download_models.sh          # 模型下载
│
├── memory/                     # 记忆系统(6文件)
│   ├── evolution-log.md
│   ├── knowledge-graph.md
│   ├── learned-patterns.md
│   ├── skill-feedback.md
│   ├── task-history.md
│   └── user-preferences.md
│
├── runtime/                    # 核心运行时(28文件)
│   ├── astro_analyzer.py
│   ├── astro_data_collector.py
│   ├── astro_pipeline.py
│   ├── auto_observatory.py
│   ├── cycle_statistics_dashboard.py
│   ├── data_miner.py
│   ├── discovery_tracker.py
│   ├── enhanced_observation_scheduler.py
│   ├── hypothesis_generator.py
│   ├── hypothesis_tester.py
│   ├── kepler_exoplanet_client.py
│   ├── literature_researcher.py
│   ├── main.py
│   ├── mcp_protocol.py
│   ├── memory_persistence.py
│   ├── observation_executor.py
│   ├── observation_scheduler.py
│   ├── observatory_linker.py
│   ├── reasoning_engine.py
│   ├── research_loop.py
│   ├── research_observatory_linker.py
│   ├── sandbox.py
│   ├── self_review.py
│   ├── server.py
│   ├── skill_integration.py
│   ├── skill_tester.py
│   ├── star_recognizer.py
│   ├── vector_memory.py
│   ├── vector_rag.py
│   ├── visualization.py
│   ├── requirements.txt
│   └── tests/
│       ├── __init__.py
│       ├── integration_test.py
│       └── test_observation_loop_integration.py
│
├── skills/                     # 技能文档(48文件)
│   ├── AI-Agent.md
│   ├── API-Design.md
│   ├── Architecture.md
│   ├── AstroPipeline.md
│   ├── Backend.md
│   ├── CLAUDE.md
│   ├── Cloud-Deployment.md
│   ├── Code-Review.md
│   ├── Cognitive-Engine.md
│   ├── Data-Analysis.md
│   ├── Database.md
│   ├── Debugging.md
│   ├── Demo-Script.md
│   ├── DevOps.md
│   ├── DSA.md
│   ├── Emotional-Understanding.md
│   ├── Execution-Engine.md
│   ├── Frontend.md
│   ├── Git-Workflow.md
│   ├── Hermes-AGI.md
│   ├── Interview-Preparation.md
│   ├── Linux-Operations.md
│   ├── Long-Term-Memory.md
│   ├── Multimodal.md
│   ├── NodeJS-Backend.md
│   ├── Planning-Engine.md
│   ├── Product.md
│   ├── Product-Manager.md
│   ├── PROJECT-JOURNEY.md
│   ├── Project-Management.md
│   ├── Prompt-Engineering.md
│   ├── Python-Backend.md
│   ├── React.md
│   ├── Reasoning.md
│   ├── Refactoring.md
│   ├── Resume-Optimization.md
│   ├── Security.md
│   ├── Self-Evolution.md
│   ├── Skill-Creation-Guide.md
│   ├── Testing.md
│   ├── Tester.md
│   ├── Tianwen-AGI.md
│   ├── Tool-Usage.md
│   ├── UI-Visual.md
│   └── WeChat-MiniProgram.md
│
└── web/                        # Web界面
    └── index.html
```

---

## 六、文件修改时间线

### 2026-05-01 (今日)

| 时间 | 文件 | 操作 |
|-----|------|-----|
| 12:05 | PRO_HERMES_REVIEW_20260501_1205.md | Add |
| ~12:00 | runtime/vector_rag.py | Add |
| ~12:00 | verify_models.py | Add |
| ~12:00 | runtime/astro_pipeline.py | Modify |
| ~11:30 | browser_search.py | Modify |
| ~11:00 | PRO_V370_PLANNING_20260501.md | Add |
| ~11:00 | ASTRONOMICAL_FOUNDATION_MODELS.md | Add |
| ~11:00 | EXOPLANET_AI_MODELS.md | Add |
| ~11:00 | GALAXY_MORPHOLOGY_AI.md | Add |
| ~11:00 | PRO_ASTRONOMICAL_AI_COMPARISON.md | Add |
| ~11:00 | PRO_MULTI_MODEL_BALL_INTERACTION_20260501.md | Add |
| ~11:00 | REPRODUCTION_EXPERIMENT.md | Add |
| ~11:00 | reproduction_experiment.py | Add |
| ~10:30 | PRO_V360_COMPLETION_20260501.md | Add |
| ~10:30 | runtime/cycle_statistics_dashboard.py | Add |
| ~10:30 | runtime/observation_executor.py | Add |
| ~10:00 | browser_search.py | Add |
| ~10:00 | multi_agent_search.py | Add |
| ~09:30 | PRO_HERMES_REVIEW_20260501_1031.md | Add |
| ~09:00 | COMPLETED_WORK_SUMMARY.md | Add |
| ~09:00 | INCOMPLETE_WORK_SUMMARY.md | Add |
| ~09:00 | PRO_ALL_ISSUES_SUMMARY_20260501.md | Add |
| ~08:30 | runtime/tests/test_observation_loop_integration.py | Add |
| ~08:00 | download_models.sh | Add |
| ~08:00 | .gitignore | Add |
| ~07:30 | PRO_HERMES_REVIEW_20260501_1017.md | Add |
| ~07:00 | PRO_BROWSER_SIMULATION_MULTIAGENT_20260501.md | Add |

---

## 七、文件整理建议

### 7.1 建议创建的目录结构

```
docs/                           # 文档目录(建议)
├── pro/                        # PRO评审文档
├── research/                   # 研究文档
├── models/                     # 模型文档
└── implementation/             # 实现文档

src/                            # 源码目录(建议)
├── runtime/                    # 运行时
├── skills/                     # 技能
└── memory/                     # 记忆
```

### 7.2 待整理文件

| 文件 | 当前目录 | 建议目录 |
|-----|---------|---------|
| LITERATURE.md | / | docs/research/ |
| EDGE_SEARCH_RESULTS.md | / | docs/pro/ |
| *.md (根目录) | / | docs/ |
| browser_search.py | / | src/search/ |
| multi_agent_search.py | / | src/search/ |
| reproduction_experiment.py | / | experiments/ |

---

## 八、统计汇总

| 指标 | 数值 |
|-----|------|
| 总文件数 | 120+ |
| Python文件 | 32 |
| Markdown文档 | 80+ |
| Shell脚本 | 1 |
| 配置文件 | 4 |
| 版本数量 | 8 (v1.0-v3.7.0) |
| 总代码增量 | 5800+ 行 |

---

**文档版本**: v1.0
**生成时间**: 2026-05-01 12:30 CST
**维护者**: Claude (Anthropic)

---
*PRO文档完成 - 天问-AGI仓库文件整理*