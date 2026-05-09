# 天问-AGI (Tianwen-AGI)

> 天文研究的认知大脑 + 具身智能的认知执行体
> 版本: 3.7.0 | 状态: 活跃开发中
> 路线: 三路并行，观测自动化优先

---

## 智能体概述

- **名称**: 天问-AGI (Tianwen-AGI)
- **版本**: 3.7.0
- **定位**: 天文研究领域的通用认知智能体
- **核心范式**: 认知脑（知识推理）+ 执行肢（望远镜控制）
- **战略路线**: 三路并行 — AGI研究平台 / 观测自动化 / 天文知识引擎

---

## 战略路线图（三路并行）

```
路线A ──── AGI研究平台 ────────── 认知架构 + 多智能体协作（10%资源）
路线B ──── 观测自动化 ★ ──────── 望远镜控制 + 调度优化（50%资源） ← 最高优先
路线C ──── 天文知识引擎 ───────── 文献RAG + 假说生成 + 模式发现（40%资源）
```

详见: `docs/THREE_ROADMAP_20260509.md`

---

## 源码结构（src/）

```
src/
├── agents/              # 多智能体协调层
│   ├── browser.py       # 浏览器自动化
│   ├── coordinator.py   # 智能体协调器
│   ├── data_miner.py   # 数据采集智能体
│   ├── discovery.py     # 发现追踪智能体
│   ├── hypothesis_gen.py    # 假说生成
│   ├── hypothesis_test.py   # 假说验证
│   ├── literature.py    # 文献调研智能体
│   ├── mcp.py           # MCP协议智能体
│   ├── observation.py   # 观测任务智能体
│   ├── self_review.py   # 自我审查
│   ├── tri_agent.py     # 三引擎智能体（认知/规划/执行）
│   └── workflow_engine.py  # 工作流引擎
├── api/
│   └── endpoints/       # REST API 端点
├── astronomy/           # 天文算法核心
│   ├── algorithms.py   # 天文算法库
│   ├── analyzer.py     # 天文图像分析
│   ├── catalog.py      # 星表管理
│   ├── fits_processor.py  # FITS格式处理
│   ├── pipeline.py     # 图像处理管道（三阶段：检测/关联/发现）
│   ├── platesolver.py  # Plate Solving（坐标求解）
│   ├── sextractor.py   # SExtractor图像处理
│   ├── sky_chart.py    # 星图生成
│   └── star_recognizer.py  # 恒星识别
├── config/             # 配置管理
├── core/               # 核心认知引擎
│   ├── cognitive.py    # 认知引擎
│   ├── dream.py        # 梦境/发散思维
│   └── reasoning.py    # 推理引擎
├── data/               # 数据采集与处理
│   ├── analysis.py     # 数据分析
│   ├── astro_pipeline.py  # 天文数据管道
│   ├── classifier.py   # 数据分类器
│   ├── collector.py    # 数据采集器
│   ├── fits.py         # FITS数据处理
│   ├── kepler.py       # Kepler/NASA TAP API
│   ├── kepler_client.py
│   ├── miner.py        # 数据挖掘
│   ├── pipeline.py     # 数据处理管道
│   ├── processor.py    # 数据处理器
│   └── weather.py       # 天气数据
├── domain/             # 领域模型
├── engine/             # 引擎抽象层
├── learning/           # 学习与优化
│   ├── dream.py        # 梦境学习
│   ├── overfit.py      # 过拟合检测
│   ├── overfit_correction.py
│   ├── rl_scheduler.py # 强化学习调度器
│   ├── skill_integration.py
│   └── skill_tester.py
├── memory/             # 记忆系统
│   ├── persistence.py  # 持久化存储
│   ├── rag.py          # RAG 向量检索（ChromaDB）
│   ├── scenario.py     # 场景记忆
│   ├── session.py      # 会话记忆
│   ├── vector.py       # 向量嵌入
│   └── vector_store.py # 向量存储
├── models/             # 预训练模型
│   ├── resnet50_astro_classifier.pth
│   └── yolo11s_astro_detection.pt
├── observation/        # 观测自动化（核心差异化）
│   ├── app.py          # 观测应用
│   ├── auto.py         # 自动观测
│   ├── data_processor.py
│   ├── embodied.py     # 具身智能层
│   ├── enhanced_scheduler.py  # 增强调度器
│   ├── executor.py     # 观测执行器（模拟）
│   ├── realtime.py     # 实时观测
│   ├── rl_scheduler.py # RL调度器
│   ├── scheduler.py    # 综合评分调度器
│   ├── sky_chart.py    # 观测星图
│   └── workflow.py     # 观测工作流
├── research/           # 研究流程
│   ├── discovery.py    # 发现追踪
│   ├── hypothesis.py   # 假说管理
│   ├── hypothesis_tester.py  # 假说验证
│   ├── linker.py       # 知识链接
│   ├── literature.py   # 文献调研
│   └── loop.py         # 研究闭环
├── service/            # 业务服务层
├── telescope/          # 望远镜控制层
│   ├── enhanced_scheduler.py
│   ├── linker.py       # 望远镜抽象（ASCOM/INDI/Seestar）
│   ├── mcp_client.py   # Seestar MCP客户端
│   ├── mqtt_bridge.py  # MQTT望远镜桥接
│   ├── scheduler.py    # 望远镜调度
│   ├── seestar_client.py
│   └── simulator.py    # 望远镜模拟器
├── utils/              # 工具函数
│   ├── config.py
│   ├── logger.py
│   ├── mcp.py
│   ├── models.py
│   ├── sandbox.py
│   ├── self_review.py
│   ├── skill_integration.py
│   ├── skill_tester.py
│   └── visualization.py
└── web/                # Web界面
    ├── bridge.py
    ├── dashboard.py
    ├── session.py
    ├── 3d/
    ├── _headers
    ├── _redirects
    ├── index.html
    └── manifest.json

runtime/                  # 望远镜抽象层
├── observatory_linker.py  # 统一望远镜接口（ASCOM/INDI/Seestar）
└── data/

backend/                  # 后端服务（部署用）
web/                      # 前端静态文件
docs/                     # 文档
```

---

## 核心能力矩阵

| 模块 | 职责 | 成熟度 | 备注 |
|------|------|--------|------|
| 三引擎（认知/规划/执行） | 智能体核心 | ★★★★☆ | 框架完整，待串联 |
| 望远镜控制（INDI/Seestar） | 路线B核心 | ★★★☆☆ | 模拟完成，真实连接待测 |
| 观测调度器 | 路线B核心 | ★★★★☆ | 综合评分算法成熟 |
| 文献RAG（ChromaDB） | 路线C核心 | ★★☆☆☆ | 框架有，落地待做 |
| 假说生成/验证 | 路线C核心 | ★★★☆☆ | 有框架，质量待提升 |
| Plate Solving | 观测后处理 | ★★★☆☆ | 有框架，集成待做 |
| 图像分析管道 | 数据处理 | ★★★☆☆ | 三阶段检测，精度待标定 |
| Kepler/TESS数据 | 数据源 | ★★★☆☆ | NASA TAP API集成 |

---

## 工作流程

```
路线C: 知识引擎                    路线B: 观测自动化
┌──────────────────────┐         ┌──────────────────────┐
│ 文献调研 → 假说生成  │────────▶│ 观测计划制定        │
│      ↑               │         │      ↓               │
│  发现追踪 ← 模式发现 │◀────────│ 望远镜控制/执行    │
└──────────────────────┘         │      ↓               │
                                 │ 图像采集/Plate Solve│
                                 │      ↓               │
                                 │ 图像分析 → 发现报告 │
                                 └──────────────────────┘
```

路线A（三引擎协调）: 调度三大引擎，连接路线B/C

---

## 关键文件索引

| 文档 | 位置 | 用途 |
|------|------|------|
| 三路路线图 | `docs/THREE_ROADMAP_20260509.md` | 战略总纲 |
| src重构方案 | `docs/SRC_REFACTOR_PLAN.md` | 代码架构优化 |
| 产品需求 | `docs/PRODUCT.md` | 产品全景 |
| 归档文档 | `docs/archive/PRO/` | 历史研究文档（83个） |

---

## 版本记录

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| 3.7.0 | 2026-05-09 | 三路路线图，文档归档，src架构重构方案 |
| 3.6.0 | 2026-05-01~08 | 多智能体协作深化，观测自动化框架 |
| 3.0.0 | 2026-04-29 | AGI架构升级 |
