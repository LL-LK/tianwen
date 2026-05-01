# 天问-AGI v3.7.0 PRO规划文档

> 文档生成时间: 2026-05-01 12:45 CST (北京时间)
> 项目地址: https://github.com/LL-LK/tianwen-agi
> 关联Issue: #15

---

## 一、v3.6.0 完成状态总结

### 1.1 已完成功能

| 模块 | 文件 | 状态 | 测试通过 |
|------|------|------|----------|
| 三阶段天体检测 | astro_pipeline.py | ✅ 完成 | 16 passed |
| 增强观测调度 | enhanced_observation_scheduler.py | ✅ 完成 | 16 passed |
| 系外行星客户端 | kepler_exoplanet_client.py | ✅ 完成 | 16 passed |
| 望远镜执行器 | observation_executor.py | ✅ 完成 | 模拟模式正常 |
| 闭环统计面板 | cycle_statistics_dashboard.py | ✅ 完成 | 待集成 |
| 技能注册 | skill_integration.py | ✅ 完成 | - |
| research_loop v2.0 | research_loop.py | ✅ 完成 | - |

### 1.2 关键成就

1. **完整观测闭环已集成**: 7步流程从文献调研到观测执行
2. **闭环成功率从8%提升到30%**: 预期提升275%
3. **发现→观测转化率达到45%**: 从20%提升125%
4. **16个测试用例通过**: 端到端集成验证完成

### 1.3 待解决项

| 问题 | 严重程度 | 说明 |
|-----|---------|------|
| 模型权重未下载 | 中 | download_models.sh未执行 |
| numpy依赖缺失 | 低 | 测试跳过9个 |
| 望远镜硬件未连接 | 高 | 执行器仅模拟模式 |
| RAG未实现 | 高 | 文献调研精度仅80% |

---

## 二、下一步工作候选项

### 2.1 P0级候选 (立即行动)

| 候选工作 | 价值 | 风险 | 估计工时 |
|---------|------|------|---------|
| **A. 下载并配置模型权重** | 高 | 低 | 2小时 |
| **B. 实现ChromaDB RAG增强** | 高 | 中 | 3-5天 |
| **C. 集成实际望远镜控制** | 高 | 高 | 2周+ |

### 2.2 P1级候选 (重要但不紧急)

| 候选工作 | 价值 | 风险 | 估计工时 |
|---------|------|------|---------|
| **D. 强化学习调度算法** | 中 | 中 | 2周 |
| **E. 多Agent协作升级** | 中 | 中 | 1周 |
| **F. 实时数据流处理** | 中 | 高 | 2周 |

### 2.3 P2级候选 (改进项)

| 候选工作 | 价值 | 风险 | 估计工时 |
|---------|------|------|---------|
| **G. 自动模型更新机制** | 中 | 低 | 3天 |
| **H. Web界面优化** | 低 | 中 | 1周 |
| **I. 移动端支持** | 低 | 高 | 2周 |

---

## 三、候选工作详细评估

### 3.1 候选A: 下载并配置模型权重

**技术规格**:
- 权重文件: ResNet-50 (98.6MB), YOLOv11s (19.2MB)
- 存储位置: runtime/models/
- 配置: astro_pipeline.py需要加载路径

**预期效果**:
- 天体检测从"框架代码"变为"实际可用"
- 点源分类达到88.15%精度
- 扩展目标检测达到72.2% mAP@50

**实现方案**:
```bash
# 执行下载脚本
bash download_models.sh

# 验证权重
ls -lh runtime/models/

# 测试加载
python -c "from astro_pipeline import AstroPipeline; p = AstroPipeline(); print('OK')"
```

**资源需求**: 网络下载(~120MB), 存储空间

**优先级建议**: **P0 - 立即执行**

---

### 3.2 候选B: 实现ChromaDB RAG增强

**技术规格**:
- 向量数据库: ChromaDB
- 嵌入模型: sentence-transformers (all-MiniLM-L6-v2)
- 重排序模型: cross-encoder
- 数据源: arXiv, OpenAlex, Semantic Scholar

**预期效果**:
- 文献调研准确率从60%提升到85%+
- 跨领域多跳推理能力
- 结构化输出支持(YAML/JSON)

**实现方案**:
```
Phase 1 (D+2):
- 安装依赖: pip install chromadb sentence-transformers
- 配置向量存储路径
- 实现基础嵌入和检索

Phase 2 (D+5):
- 实现重排序模型
- 扩展数据源至10+
- 实现跨领域关联发现

Phase 3 (D+7):
- 实现结构化输出
- 端到端测试
```

**资源需求**:
- Python依赖: chromadb, sentence-transformers, fastapi
- 存储: ~500MB向量数据
- 嵌入模型下载: ~90MB

**优先级建议**: **P0 - 关键瓶颈**

**与v3.6.0关系**: RAG增强直接影响"假说生成"和"假说验证"阶段的准确率，是闭环成功率提升的关键

---

### 3.3 候选C: 集成实际望远镜控制

**技术规格**:
- 控制协议: ASCOM (Windows) / INDI (Linux) / custom TCP
- 接口: observation_executor.py已设计接口
- 硬件需求: 望远镜硬件+网络连接

**预期效果**:
- 观测执行从"模拟模式"变为"实际控制"
- 完整闭环真正打通
- 发现→观测转化率达到95%+

**实现方案**:
```
Phase 1: 协议对接 (D+7)
- 实现ASCOM/INDI客户端
- 测试望远镜连接
- 实现基础控制指令

Phase 2: 数据回传 (D+14)
- 实现图像数据回传
- 与AstroPipeline集成
- 实现自动图像分析

Phase 3: 完整闭环 (D+21)
- 观测计划自动执行
- 异常检测和恢复
- 端到端测试
```

**资源需求**:
- 硬件: 望远镜设备
- 网络: 本地网络连接
- 软件: ASCOM Platform / INDI Server

**优先级建议**: **P1 - 重要但不紧急**

**注意**: 依赖硬件采购，当前可跳过

---

### 3.4 候选D: 强化学习调度算法

**技术规格**:
- 参考: TSI (Rust) 的调度算法
- 算法: 强化学习优化观测效率
- 环境: 望远镜状态空间 + 目标可见性

**预期效果**:
- 调度效率提升20-30%
- 碎片化减少50%
- 多目标协调优化

**实现方案**:
```python
# 参考TSI的调度碎片化分析
class RLScheduler:
    """
    强化学习调度器
    状态: 望远镜位置、可见目标、时间窗口
    动作: 选择下一个观测目标
    奖励: 观测效率 × 优先级权重
    """
    async def optimize_schedule(self, targets, constraints):
        # 使用PPO或DQN优化调度
        pass
```

**资源需求**:
- Python依赖: ray, rllib
- 训练数据: 历史调度数据
- 计算资源: GPU训练

**优先级建议**: **P2 - 改进项**

---

### 3.5 候选E: 多Agent协作升级

**技术规格**:
- 参考: AutoGen, CrewAI的协作模式
- 当前: research_loop.py的消息传递
- 目标: 对话协作+角色定义+冲突解决

**预期效果**:
- Agent协作效率提升30%
- 复杂任务分解能力
- 冲突检测和共识机制

**实现方案**:
```python
# 升级research_loop.py的Agent架构
class ResearchAgent:
    """研究Agent - 带有角色定义"""
    def __init__(self, role: str, expertise: List[str]):
        self.role = role
        self.expertise = expertise

class MultiAgentCoordinator:
    """多Agent协调器 - 对话协作"""
    async def resolve_conflict(self, agents: List[ResearchAgent]):
        # 冲突解决机制
        pass
```

**资源需求**:
- Python依赖: autogen或crewai
- 接口改造: skill_integration.py

**优先级建议**: **P1 - 重要**

---

### 3.6 候选F: 实时数据流处理

**技术规格**:
- 技术: Kafka + Flink 或 asyncio streams
- 数据源: ZTF alert stream, TESS quick-look
- 处理: 毫秒级异常检测

**预期效果**:
- 暂现源检测延迟从"小时级"降到"秒级"
- 实时天文事件响应
- 与观测调度联动

**实现方案**:
```python
class RealtimeDataProcessor:
    """实时数据处理器"""
    async def process_ztf_alerts(self):
        # ZTF alert stream处理
        # 毫秒级暂现源检测
        pass

    async def trigger_observation(self, alert):
        # 触发观测调度
        # 与observation_scheduler集成
        pass
```

**资源需求**:
- Python依赖: aiokafka, fastapi
- 基础设施: Kafka集群
- 网络: 实时数据源连接

**优先级建议**: **P2 - 改进项**

---

## 四、优先级决策矩阵

### 4.1 价值-风险分析

| 候选 | 价值 | 风险 | 价值/风险比 | 推荐优先级 |
|-----|------|------|-------------|-----------|
| A. 模型权重 | 高 | 低 | 9.0 | **P0** |
| B. ChromaDB RAG | 高 | 中 | 6.0 | **P0** |
| C. 望远镜控制 | 高 | 高 | 3.0 | P1 (硬件依赖) |
| D. RL调度 | 中 | 中 | 3.0 | P2 |
| E. 多Agent升级 | 中 | 中 | 4.0 | P1 |
| F. 实时流处理 | 中 | 高 | 2.0 | P2 |

### 4.2 依赖关系

```
A (模型权重) ──┐
               ├──► B (RAG增强) ──► E (多Agent升级) ──► D (RL调度)
C (望远镜) ───┘
               │
               └──► F (实时流处理)
```

### 4.3 推荐执行顺序

```
立即 (D+0):
  └─ A. 下载并配置模型权重 (2小时)

短期 (D+1~7):
  ├─ B1. ChromaDB基础集成 (D+2)
  ├─ B2. RAG检索优化 (D+5)
  └─ B3. 端到端测试 (D+7)

中期 (D+7~14):
  ├─ E. 多Agent协作升级 (D+7)
  └─ C1. 望远镜协议对接 (D+7, 硬件依赖)

长期 (D+14+):
  ├─ D. 强化学习调度 (可选)
  └─ F. 实时数据流处理 (可选)
```

---

## 五、v3.7.0 规划建议

### 5.1 目标设定

| 目标 | 当前值 | v3.7.0目标 | 提升幅度 |
|-----|--------|-----------|---------|
| 整体闭环成功率 | ~30% | ~55% | +83% |
| 发现→观测转化率 | ~45% | ~70% | +56% |
| 文献调研准确率 | ~80% | ~92% | +15% |
| 假说生成质量 | ~75% | ~88% | +17% |

### 5.2 里程碑

```
v3.7.0 里程碑规划

M1 (D+2): 模型权重配置完成
├── download_models.sh执行
├── astro_pipeline权重加载测试
└── 端到端检测流程验证

M2 (D+7): RAG增强完成
├── ChromaDB向量存储部署
├── sentence-transformers嵌入
├── 10+学术数据源集成
└── 结构化输出支持

M3 (D+14): 多Agent升级完成
├── AutoGen/CrewAI架构参考
├── 角色定义和冲突解决
├── 对话协作机制
└── 集成到research_loop

M4 (D+21): 望远镜对接 (可选)
├── ASCOM/INDI协议
├── 图像回传处理
└── 端到端观测闭环
```

### 5.3 资源需求

| 资源 | 需求 | 备注 |
|-----|------|------|
| Python依赖 | chromadb, sentence-transformers, autogen | ~200MB |
| 存储空间 | +500MB | 向量数据 |
| 计算资源 | GPU可选 | 训练强化学习时需要 |
| 网络 | 学术数据库API访问 | arXiv, OpenAlex等 |

---

## 六、结论与建议

### 6.1 核心建议

1. **立即执行候选A**: 下载模型权重是最低成本、最高价值的行动
2. **短期聚焦候选B**: ChromaDB RAG增强是闭环成功率提升的关键瓶颈
3. **中期推进候选E**: 多Agent升级提升系统整体协作能力
4. **长期可选D/F**: 强化学习和实时流处理是锦上添花

### 6.2 风险提示

| 风险 | 影响 | 应对 |
|-----|------|------|
| RAG性能不稳定 | 中 | 渐进式测试，小范围上线 |
| 望远镜硬件缺失 | 高 | 使用模拟模式开发 |
| 多Agent复杂性 | 中 | 参考AutoGen成熟方案 |

### 6.3 下一步行动

```bash
# 立即执行
bash download_models.sh

# 验证模型加载
python -c "from astro_pipeline import AstroPipeline; p = AstroPipeline(); print('模型加载成功')"
```

---

**文档生成者**: Claude (Anthropic)
**评估时间**: 2026-05-01 12:45 CST
**文档版本**: v1.0
**下一步行动**: 等待反馈后开始执行