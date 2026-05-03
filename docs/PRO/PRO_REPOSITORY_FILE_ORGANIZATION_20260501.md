# 天问-AGI 仓库文件整理 PRO文档 v2.0

> 文档生成时间: 2026-05-01 13:00 CST (北京时间)
> 生成者: Claude (Anthropic)
> 项目地址: https://github.com/LL-LK/tianwen-agi

---

## 一、文件分类总览

| 类别 | 目录 | 文件数 | 说明 |
|-----|------|--------|-----|
| 核心运行时 | runtime/ | 35 | Agent核心执行模块 |
| 技能文档 | skills/ | 48 | Agent技能与知识库 |
| 项目文档 | docs/ | 8 | PRO评审文档(已整理) |
| 根目录文档 | / | 90+ | 各类PRO/Issue文档 |
| 记忆系统 | memory/ | 6 | 长期记忆与知识图谱 |
| Web界面 | web/ | 1 | 前端界面 |
| 测试文件 | runtime/tests/ | 4 | 集成测试 |
| 容器部署 | / | 2 | Docker配置 |
| 搜索模块 | / | 2 | 浏览器/多Agent搜索 |

---

## 二、当前目录结构

```
F:\tianwen-agi\
├── .gitignore
├── CLAUDE.md                      # 项目说明
├── PRODUCT.md                     # 产品文档
├── PROJECT_LOG.md                 # 项目日志
├── PROJECT-JOURNEY.md             # 发展历程
├── PROFESSIONAL_REVIEW.md         # 专业评审
├── agent.md                       # Agent架构
│
├── docs/                          # PRO评审文档(已整理)
│   ├── PRO_ISSUE1_HERMES_REPLY_20260501.md
│   ├── PRO_ISSUE9_HERMES_REPLY_20260501.md
│   ├── PRO_ISSUE11_HERMES_REPLY_20260501.md
│   ├── PRO_ISSUE12_HERMES_REPLY_20260501.md
│   ├── PRO_ISSUE17_HERMES_REPLY_20260501.md
│   ├── PRO_ISSUE18_HERMES_REPLY_20260501.md
│   ├── PRO_ISSUE20_HERMES_REPLY_20260501.md
│   └── PRO_ISSUE14_HERMES_REPLY_20260501.md
│
├── memory/                        # 记忆系统(6文件)
│   ├── evolution-log.md
│   ├── knowledge-graph.md
│   ├── learned-patterns.md
│   ├── skill-feedback.md
│   ├── task-history.md
│   └── user-preferences.md
│
├── runtime/                       # 核心运行时(35文件)
│   ├── astro_analyzer.py
│   ├── astro_data_collector.py
│   ├── astro_pipeline.py
│   ├── auto_observatory.py
│   ├── cycle_statistics_dashboard.py
│   ├── data_miner.py
│   ├── discovery_tracker.py
│   ├── embodied_observation_workflow.py  # 具身观测
│   ├── enhanced_observation_scheduler.py
│   ├── hypothesis_generator.py
│   ├── hypothesis_tester.py
│   ├── kepler_exoplanet_client.py
│   ├── literature_researcher.py
│   ├── main.py
│   ├── mcp_protocol.py
│   ├── memory_persistence.py
│   ├── multi_agent_coordinator.py       # 多Agent协调
│   ├── observation_executor.py
│   ├── observation_scheduler.py
│   ├── observatory_linker.py
│   ├── realtime_data_processor.py      # 实时数据处理
│   ├── reasoning_engine.py
│   ├── requirements.txt
│   ├── research_loop.py
│   ├── research_observatory_linker.py
│   ├── rl_observation_scheduler.py     # 强化学习调度
│   ├── sandbox.py
│   ├── self_review.py
│   ├── seestar_mcp_client.py            # SeeStar MCP
│   ├── server.py
│   ├── skill_integration.py
│   ├── skill_tester.py
│   ├── star_recognizer.py
│   ├── vector_memory.py
│   ├── vector_rag.py
│   ├── visualization.py
│   └── tests/
│       ├── __init__.py
│       ├── integration_test.py
│       ├── test_embodied_observation_integration.py
│       └── test_observation_loop_integration.py
│
├── skills/                         # 技能文档(48文件)
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
│   ├── Tester.md
│   ├── Testing.md
│   ├── Tianwen-AGI.md
│   ├── Tool-Usage.md
│   ├── UI-Visual.md
│   └── WeChat-MiniProgram.md
│
├── web/                           # Web界面
│   └── index.html
│
├── browser_search.py              # 浏览器搜索
├── multi_agent_search.py          # 多Agent搜索
├── reproduction_experiment.py      # 复现实验
├── verify_models.py               # 模型验证
├── download_models.sh             # 模型下载
├── docker-compose.yml             # 容器编排
├── Dockerfile                     # 容器镜像
├── test.txt                       # 测试文件
└── [90+ PRO/Issue文档]            # 根目录Markdown
```

---

## 三、按应用分类

### 3.1 核心运行时 (runtime/) - 35文件

| 分类 | 文件 | 功能 |
|-----|------|-----|
| **观测闭环** | astro_pipeline.py | 观测流程主管 |
| | observation_executor.py | 观测执行器 |
| | enhanced_observation_scheduler.py | 增强调度器 |
| | observation_scheduler.py | 基础调度器 |
| | rl_observation_scheduler.py | 强化学习调度 |
| | kepler_exoplanet_client.py | Kepler数据客户端 |
| | observatory_linker.py | 观测站链接 |
| | seestar_mcp_client.py | SeeStar MCP客户端 |
| | auto_observatory.py | 全自动天文台 |
| **具身观测** | embodied_observation_workflow.py | 具身观测工作流 |
| **研究闭环** | research_loop.py | 研究循环主管 |
| | research_observatory_linker.py | 研究-观测联动 |
| | hypothesis_generator.py | 假说生成 |
| | hypothesis_tester.py | 假说验证 |
| | discovery_tracker.py | 发现追踪 |
| **多Agent** | multi_agent_coordinator.py | 多Agent协调器 |
| **数据处理** | astro_analyzer.py | 天文分析 |
| | astro_data_collector.py | 数据收集 |
| | data_miner.py | 数据挖掘 |
| | realtime_data_processor.py | 实时数据处理 |
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

### 3.2 技能文档 (skills/) - 48文件

| 分类 | 文件数 |
|-----|--------|
| 核心技能 | 6 |
| 工程技能 | 12 |
| 应用技能 | 4 |
| 产品技能 | 3 |
| 天问特有 | 3 |
| 其他 | 20 |

### 3.3 PRO文档 (根目录 + docs/)

| 类型 | 数量 | 说明 |
|-----|------|-----|
| PRO评审文档 | 50+ | Hermes评审、深度思考、研究报告 |
| Issue回复文档 | 20+ | 各Issue的Hermes回复 |
| 版本报告 | 5+ | v3.4-v3.7完成报告与规划 |
| 技术分析 | 15+ | 竞品分析、过拟合分析等 |
| 天文AI模型 | 5+ | 模型对比、基础模型等 |
| 搜索结果 | 5+ | AGI/具身/金乌搜索结果 |
| 实施文档 | 3+ | 数据挖掘、观测链接实现 |

---

## 四、版本时间线

| 版本 | 日期 | 主要更新 |
|-----|------|---------|
| v3.7.0 | 2026-05-01 | 具身观测、多Agent协调、强化学习调度、实时数据处理 |
| v3.6.0 | 2026-05-01 | 观测闭环、统计面板、ChromaDB RAG |
| v3.5.0 | 2026-05-01 | 统计假设检验、LRU缓存、Docker支持 |
| v3.4.0 | 2026-04-30 | 研究闭环、假说生成验证、发现追踪 |
| v3.0.0 | 2026-04 | 全自动天文站、观测调度 |
| v2.0-v2.3 | 2026-03 | Agent框架、Web API、向量记忆 |
| v1.0 | 2026-02 | 初始化项目 |

---

## 五、文件整理建议

### 5.1 已完成整理
- docs/ 目录创建，8个Issue回复PRO文档已移入

### 5.2 待整理
| 文件类型 | 当前目录 | 建议目录 |
|---------|---------|---------|
| PRO评审文档 | 根目录 | docs/pro/ |
| Issue回复 | 根目录 | docs/issue-replies/ |
| 搜索结果 | 根目录 | docs/search-results/ |
| 模型文档 | 根目录 | docs/models/ |
| browser_search.py | 根目录 | src/search/ |
| multi_agent_search.py | 根目录 | src/search/ |

---

## 六、统计汇总

| 指标 | 数值 |
|-----|------|
| 总文件数 | 150+ |
| Python文件 | 40+ |
| Markdown文档 | 100+ |
| 运行时模块 | 35 |
| 技能文档 | 48 |
| 版本数量 | 8 (v1.0-v3.7.0) |

---

**文档版本**: v2.0
**生成时间**: 2026-05-01 13:00 CST
**维护者**: Claude (Anthropic)

---
*PRO文档完成 - 天问-AGI仓库文件整理v2.0*