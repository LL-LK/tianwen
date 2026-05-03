# 天问-AGI Issue #28 #29 PM评审总结

**评审时间**: 2026-05-01 22:35 CST (北京时间)
**评审者**: Hermes Agent (产品经理视角)
**仓库**: git@github.com:LL-LK/tianwen-agi.git

---

## Issue #28: 天文AGI研究

### 基本信息
| 属性 | 值 |
|------|-----|
| 标题 | [Research] Astronomical AGI - Star Recognition, Galaxy Classification, Exoplanet Detection |
| 状态 | OPEN |
| 作者 | LL-LK |
| 评论数 | 2 |

### 研究发现
- 系外行星探测AI(exoplanet-detection-ml等)都是窄ML
- 星系形态分类都是CNN而非真AGI推理
- 缺乏自主推理、多步规划能力

### 关键差距
| 能力 | 窄ML | 真AGI | 天问机会 |
|------|------|-------|---------|
| 多步规划 | NO | YES | 核心差异化 |
| 自主推理 | NO | YES | 核心差异化 |
| 完整研究闭环 | NO | NO | 天问独有 |

### Hermes评估
- 研究确认: OK
- 差异化机会: 清晰
- 实现状态: 未开始(研究阶段)

### 产品路线图建议
目标: 功能完整度 42% -> 65%

| 能力 | 技术方案 | 优先级 |
|------|---------|--------|
| 多步规划 | ARC-AGI推理引擎 | P0 |
| 完整研究闭环 | 天问闭环集成 | P0 |
| 自主推理 | big-AGI认知架构 | P1 |

### 可靠性: 8/10

---

## Issue #29: 具身智能天文台

### 基本信息
| 属性 | 值 |
|------|-----|
| 标题 | [Research] Embodied AI in Astronomical Observatories |
| 状态 | OPEN |
| 作者 | LL-LK |
| 评论数 | 6 (活跃讨论) |

### 高契合度项目

| 项目 | GitHub | 关键特点 | 契合度 |
|------|--------|---------|--------|
| NIGHTWATCH | THOClabs/NIGHTWATCH | 语音->AI->望远镜闭环,本地AI | 5/5 |
| Chimera | astroufsc/chimera | 天文台自动化框架 | 5/5 |
| seestar-mcp | taco-ops/seestar-mcp | MCP协议,AI Agent控制 | 5/5 |

### v3.8.0实现进度

| 文件 | 行数 | 功能 |
|------|------|------|
| runtime/seestar_mcp_client.py | 764 | MCP协议客户端+ZWO Seestar控制 |
| runtime/embodied_observation_workflow.py | 659 | 完整具身观测工作流 |
| runtime/tests/test_embodied_observation_integration.py | ~300 | 端到端集成测试 |

### 可靠性评估更新
**中等 -> 中高 (★★★☆☆ -> ★★★★☆)**

| 维度 | 评分 | 说明 |
|------|------|------|
| 技术可行性 | 7/10 | NIGHTWATCH验证存在 |
| 硬件兼容性 | 6/10 | seestar-mcp已实现 |
| 安全性 | 5/10 | 需增加保护机制 |
| 泛化能力 | 6/10 | RT-2 VLA提供跨实体 |

### 技术路线图

| 阶段 | 时间 | 目标 |
|------|------|------|
| v3.8.0 | 1-2月 | MCP协议控制望远镜 |
| v3.9.0 | 2-3月 | VLA视觉推理控制 |
| v4.0 | 3-6月 | 完全自主天文台 |

### 三层架构
```
认知层(天问-AGI) -> 控制层(具身接口) -> 执行层(硬件)
```

### 剩余P0问题
1. 真实硬件接口验证(ASCOM/INDI)
2. 实时跟踪控制
3. 3D跟踪(VoxPoser)
4. 安全协议(碰撞检测)

### 可靠性: 7/10

---

## 总结对比

| 维度 | Issue #28 (天文AGI) | Issue #29 (具身智能天文台) |
|------|---------------------|---------------------------|
| 研究状态 | 完成 | 完成 |
| 实现状态 | 未开始 | v3.8.0已开始 |
| 战略价值 | 高 | 极高(未开拓领域) |
| 可靠性 | 8/10 | 7/10 |
| 主要风险 | ARC-AGI集成难度 | 硬件依赖+安全 |

---

## 审计文档

- /home/l2140/PRO_AUDIT_P0_ASTRONOMICAL_AGI.md (Issue #28审计)
- /home/l2140/PRO_AUDIT_P0_EMBODIED_AI_OBSERVATORY.md (Issue #29审计)

## GitHub评论

- Issue #28: https://github.com/LL-LK/tianwen-agi/issues/28#issuecomment-4359846081
- Issue #29: https://github.com/LL-LK/tianwen-agi/issues/29#issuecomment-4359847904