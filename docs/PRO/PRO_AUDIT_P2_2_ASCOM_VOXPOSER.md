# PRO审计文档: P2-2 强独立闭环ASCOM+VoxPoser
**审计时间**: 2026-05-01 15:30 CST (北京时间)
**优先级**: P2 (中期)
**关联Issue**: #31

---

## 一、现状分析

### 1.1 Issue #31背景

Issue #31讨论"天问-AGI独立闭环能力分析与路线图"，Claude提出强独立闭环架构。

### 1.2 当前架构

| 组件 | 状态 | 说明 |
|------|------|------|
| 本地LLM推理 | ❌ 缺失 | 依赖外部API |
| 本地RAG | ⚠️ 计划中 | ChromaDB待集成 |
| seestar-mcp | ⚠️ 已集成 | MCP协议望远镜控制 |
| ASCOM | ❌ 缺失 | Windows硬件控制 |
| VoxPoser | ❌ 缺失 | 3D跟踪控制 |

### 1.3 强独立闭环架构

```
强独立闭环架构
├── 本地LLM推理层 (vLLM/Ollama)
├── 本地RAG增强 (ChromaDB)
├── 具身控制层 (ASCOM/VoxPoser)
└── 数据层 (Neo4j/Kafka)
```

**Hermes修订方案**:
```
天问-AGI强独立闭环架构 v2
├── 本地LLM推理层 (Ollama先行 → vLLM)
├── 本地RAG增强 (ChromaDB + astroPT)
├── 具身控制层 (seestar-mcp → ASCOM)
└── 数据层 (Neo4j已有 + Kafka备选)
```

---

## 二、技术方案

### 2.1 ASCOM平台

**ASCOM (Astronomy COM)**:
- Windows平台天文设备控制标准
- 支持望远镜、相机、滤镜轮等
- 600+设备驱动

**ASCOM官网**: https://ascom-standards.org/

### 2.2 VoxPoser

**VoxPoser**:
- 来自论文 "VoxPoser: Composable 3D Value Maps for Robotic Manipulation"
- 从RGB-D图像生成3D空间控制
- 适合天文跟踪和定位

### 2.3 seestar-mcp过渡策略

| 阶段 | 方案 | 优势 | 劣势 |
|------|------|------|------|
| 当前 | seestar-mcp | MCP协议，AI友好 | 仅支持Seestar设备 |
| 过渡 | ASCOM + MCP桥接 | 支持更多设备 | 复杂 |
| 最终 | ASCOM原生 | 完整硬件控制 | Windows only |

---

## 三、实施计划

### 3.1 v4.0路线图 (3-6月)

| 阶段 | 行动 | 说明 |
|------|------|------|
| 1 | ASCOM平台集成 | Windows平台天文控制 |
| 2 | VoxPoser 3D跟踪 | 目标跟踪和定位 |
| 3 | 闭环测试 | 完整观测流程验证 |

### 3.2 技术依赖

| 依赖 | 说明 |
|------|------|
| Windows环境 | ASCOM仅Windows |
| ASCOM Platform | 6.0+ |
| .NET Runtime | ASCOM需要 |
| RGB-D相机 | VoxPoser需要 |

### 3.3 验证清单

| 验证项 | 预期结果 |
|--------|---------|
| ASCOM平台安装 | ASCOM Platform 6+ |
| 望远镜控制 | 能控制真实硬件 |
| VoxPoser集成 | 3D目标跟踪 |

---

## 四、文献来源

| 项目 | URL | 说明 |
|------|-----|------|
| ASCOM Standards | https://ascom-standards.org/ | 天文设备控制标准 |
| ASCOM GitHub | https://github.com/ASCOMInitiative | 600+驱动 |
| VoxPoser论文 | https://arxiv.org/abs/2307 | 3D空间控制 |
| seestar-mcp | https://github.com/taco-ops/seestar-mcp | MCP协议 |

---

## 五、审计结论

| 维度 | 评估 |
|------|------|
| 当前状态 | ❌ seestar-mcp过渡阶段 |
| 最终目标 | ASCOM原生 + VoxPoser |
| 实施难度 | 高 - 需Windows硬件环境 |
| 优先级 | P2 - v4.0长期目标 |

**建议**:
1. 当前保持seestar-mcp作为主力
2. v4.0前6个月完成ASCOM桥接
3. VoxPoser作为3D跟踪备选

---

**审计状态**: ✅ 完成
**审计人**: Hermes Agent (产品经理视角)
**路线图**: v4.0 (3-6月)
