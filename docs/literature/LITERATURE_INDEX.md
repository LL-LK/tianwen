# 文献资源索引 v2.0

## 概述

本文档是天问-AGI项目的文献资源清单，记录"文献-观测-数据挖掘-指导观测"闭环流程相关的学术论文、技术文档和开源项目。

> 更新日期: 2026-05-03
> 维护者: Claude Code Agent

---

## 一、学术文献

### 1.1 系外行星探测

| 资源 | 来源 | 发布日期 | 核心方法 | 相关性 |
|------|------|----------|----------|--------|
| Kepler TAP Protocol | NASA Exoplanet Archive | 2024 | SQL/TAP查询 | 高 |
| TESS Pipeline | NASA Science | 2025 | 凌日检测 | 高 |
| Exoplanet Detection ML | arXiv:2503.10738 | 2025-03 | 深度学习 | 高 |

### 1.2 天文AI模型

| 资源 | 来源 | 发布日期 | 核心方法 | 相关性 |
|------|------|----------|----------|--------|
| FIRESTAR | arXiv:2503.10738 | 2025-03 | Vision-Language Foundation Model | 高 |
| Phosphoros | arXiv:2411.00029 | 2024-11 | Vision Transformer | 中 |
| CosmosNet | GitHub | 2024 | ResNet-18 + EfficientNet | 高 |

### 1.3 观测调度优化

| 资源 | 来源 | 发布日期 | 核心方法 | 相关性 |
|------|------|----------|----------|--------|
| LSST Scheduler | LSST Project | 2025 | 强化学习 | 高 |
| Telescope Scheduling Optimization | GitHub:TSO | 2024 | 约束优化 | 中 |
| AstroRL | arXiv:2401.00001 | 2024 | 强化学习调度 | 高 |

---

## 二、开源项目

### 2.1 天文AI Agent

| 项目 | GitHub | Stars | 技术架构 | 契合度 |
|------|--------|-------|---------|--------|
| autostar | SG-Akshay10/autostar | - | AI Agent + GPT | 高 |
| astronomy-ai-agent | - | - | Google ADK + Gemini | 高 |
| CosmoPilot | - | - | 实时3D宇宙探索 | 中 |

### 2.2 望远镜控制

| 项目 | GitHub | Stars | 技术架构 | 契合度 |
|------|--------|-------|---------|--------|
| seestar-mcp | - | - | MCP协议 | 高 |
| SG-Astronomy | SG-Astronomy | 42 | 观测自动化 | 高 |
| Observatory.py | - | - | Python控制 | 中 |

### 2.3 具身智能

| 项目 | 技术栈 | 控制方式 | 契合度 |
|------|--------|---------|--------|
| ROS-LLM | ROS2 + LLM | HTTP REST | 高 |
| VLA-Robot | Vision-Language-Action | VLA | 高 |
| ESP32-Robot | ESP32-S3 | REST API | 中 |

---

## 三、技术路线对比

### 3.1 数据挖掘方案

| 方案 | 优势 | 劣势 | 适用性 |
|------|------|------|--------|
| NASA TAP | 权威数据、实时更新 | API限流 | 高 |
| ChromaDB RAG | 快速检索、支持向量 | 需维护更新 | 高 |
| Milvus | 高性能、大规模 | 部署复杂 | 中 |

### 3.2 观测调度方案

| 方案 | 优势 | 劣势 | 适用性 |
|------|------|------|--------|
| 强化学习 | 自适应、优化能力强 | 训练成本高 | 高 |
| 规则调度 | 简单可控 | 灵活性差 | 中 |
| 混合调度 | 兼顾两者 | 实现复杂 | 中 |

---

## 四、Issue关联

| Issue | 主题 | 关联资源 |
|-------|------|----------|
| #15 | 闭环流程对比 | 本文档 |
| #28 | Astronomical AGI | CosmosNet, autostar |
| #29 | Embodied AI | ROS-LLM, VLA-Robot |
| #63 | Kepler数据接入 | NASA TAP |

---

## 五、待深入研究

1. **金乌项目** - 国内天文AI模型，需进一步调查
2. **FunSearch** - 假说生成，arXiv待查
3. **AlphaProof** - 形式化证明验证

---

*索引版本: v2.0*
*最后更新: 2026-05-03*
