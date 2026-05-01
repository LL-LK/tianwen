# [PRO Document] 全网AGI/具身/金乌天文大模型研究汇总报告

> 文档类型: 深度研究 + 差距分析 + 机会识别
> 创建日期: 2026-05-01 13:00 CST (北京时间)
> 研究团队: 4-Agent并行搜索
> 目标仓库: git@github.com:LL-LK/tianwen-agi.git
> 状态: 研究完成，待Hermes审计

---

## 一、研究背景与目标

### 1.1 研究任务

用户要求深度搜索以下领域的天文大模型相关文献和开源文件：
1. **AGI (通用人工智能)** - 具身天文应用
2. **具身AI (Embodied AI)** - 天文望远镜控制
3. **金乌/金乌等天文大模型** - 中国天文AI项目
4. **天文AGI综合项目** - 星体识别/星系分类/系外行星

### 1.2 研究方法

4个Agent并行搜索，每个负责一个领域：
- **agi-searcher**: AGI + 天文应用
- **embodied-searcher**: 具身AI + 天文望远镜
- **jinwu-searcher**: 金乌/中国天文AI
- **astro-agi-searcher**: 天文AGI综合

### 1.3 搜索范围

通过GitHub CLI全网搜索，关键词：
- AGI artificial general intelligence astronomical
- embodied AI robot telescope observatory
- 金乌 Jinwu astronomical model
- astronomical AGI star galaxy classification

---

## 二、搜索结果汇总

### 2.1 AGI + 天文应用 (Issue #27)

**GitHub搜索结果**: 未找到AGI+天文结合的项目

**发现的AGI框架**:
| 项目 | Stars | 特点 |
|------|-------|------|
| SuperAGI | 高 | 开发者优先的自主AI Agent框架 |
| big-AGI | 高 | AI套件，多模型聊天，语音，图像 |
| AGiXT | 高 | 动态AI Agent自动化，自适应记忆 |
| AgentForge | 中 | 可扩展AGI框架 |
| ARC-AGI | 高 | 抽象推理语料库，AGI基准 |
| MiniAGI | 中 | 简单通用AI Agent |

**发现的天文库**:
| 项目 | Stars | 特点 |
|------|-------|------|
| astropy | 非常高 | 天文和天文物理核心库 |
| python-skyfield | 高 | 优雅的天文Python库 |
| gammapy | 中 | 伽马射线天文分析 |
| astroML | 中 | 天文机器学习 |

**关键发现**: AGI框架和天文库都有，但**没有项目将两者结合**。这是天问-AGI的差异化机会。

---

### 2.2 具身AI + 天文望远镜控制 (Issue #29)

**GitHub搜索结果**: 未找到具身AI+天文望远镜的直接项目

**发现的具身AI项目**:
| 项目 | Stars | 特点 |
|------|-------|------|
| llm-robot-control | 4 | LLM控制的机器人实验 |
| voice-llm-robot-control | 0 | 语音控制机器人 (ROS+LLM) |
| multimodal-llm-robot-control | 0 | 视觉+NL+LLM实时决策 |
| morphology-generalizable | 0 | GNN+RL+LLM，零样本迁移 |
| llm_robot_control | 0 | VLA多Agent机器人控制 |
| ESP32-Robot | 0 | ESP32-S3具身Agent，REST API控制 |

**发现的天文自动化项目**:
| 项目 | Stars | 特点 |
|------|-------|------|
| chimera | 42 | 最成熟的天文台自动化系统 |

**关键发现**: 
1. 没有专门的"具身AI+天文望远镜"项目
2. chimera (42 stars) 是最成熟的天文自动化，但无LLM集成
3. LLM机器人控制项目日趋活跃，但与天文分离

---

### 2.3 金乌/中国天文AI模型 (Issue #26)

**GitHub搜索结果**: 未找到金乌相关公开仓库

**搜索的关键词**:
- 金乌 Jinwu astronomical model → 0结果
- Tianwen Chinese LLM astronomy → 0结果
- Kuaizhou satellite AI model → 0结果
- Chinese astronomical AI foundation model → 0结果
- Chang'e lunar AI explorer → 0结果

**分析**:
1. **金乌(Jinwu)**: 可能是内部项目或未公开的代码名
2. **快舟(Kuaizhou)**: 中国固体燃料运载火箭，与AI关联度低
3. **天问(Tianwen)**: 本地项目存在，但外部无类似仓库

**结论**: 金乌等中国天文AI项目可能在Gitee、GitCode等国内平台，或尚未公开。

---

### 2.4 天文AGI综合项目 (Issue #28)

**发现的系外行星探测AI**:
| 项目 | 描述 | 关键特点 |
|------|------|---------|
| exoplanet-detection-ml-FINAL | CNN周期性凌星检测 | Kepler/TESS数据，CNN |
| exoplanet-detection-ml | 系外行星检测ML | - |
| kawkeb | 系外行星检测ML模型 | - |

**发现的星系形态分类**:
| 项目 | 描述 | 关键特点 |
|------|------|---------|
| galaxy-classification-neural-networks | 10类星系图像分类 | 神经网络原型 |
| Galaxy_Classification_NN | CNN星系形态分类 | CNN |
| IRN-project | 星系分类 | 神经网络 |

**发现的天文AI Agent**:
| 项目 | 描述 | 关键特点 |
|------|------|---------|
| astronomy-ai-agent | AI天文助手 | Google ADK+Gemini |
| astronomy_ai_agent_with_Langchain | Langchain天文专家 | Langchain |
| CosmoPilot | 实时3D宇宙探索 | AI观星副驾驶 |

**关键发现**: 
- 很多窄ML项目，但**没有真AGI推理能力**
- 基本上是"给定数据→输出结果"的模式
- 缺乏自主推理、规划、多步决策能力

---

## 三、核心差距分析

### 3.1 AGI + 天文差距

```
当前状态:
  AGI框架 (SuperAGI等) ← → 天文库 (astropy等)
              ↓
         没有结合

天问-AGI的机会:
  将AGI推理能力融入天文数据处理
  实现: 自主规划观测 → 数据获取 → 分析 → 假说生成 → 验证
```

### 3.2 具身AI + 望远镜差距

```
当前状态:
  具身AI项目 ← → 天文台自动化
  (llm-robot-control等)    (chimera等)
              ↓
         没有结合

天问-AGI的机会:
  将LLM推理融入望远镜控制
  实现: 自然语言控制望远镜 → 自主导航 → 智能调度
```

### 3.3 精度代差分析

| 类型 | 当前行业水平 | 天问-AGI | 代差 |
|------|-------------|----------|------|
| AGI推理能力 | 框架已有 | 框架已有 | 框架级 |
| 天文数据处理 | 窄ML | 功能完整度42% | ~58% |
| 望远镜控制 | chimera等 | 自动化已有 | 类似 |
| LLM集成 | 分离 | 部分集成 | 部分 |
| 真AGI+天文 | **空白** | **空白** | **巨大机会** |

---

## 四、深度思考与建议

### 4.1 核心洞察

**洞察1: 真正的机会是"真AGI+天文数据"**
> 现有项目都是"窄AI"：给定输入→输出结果
> 但缺乏: 自主推理、多步规划、上下文理解、持续学习
> 天问-AGI应该填补这个空白

**洞察2: 具身AI是望远镜控制的未来**
> REST API控制模式已被ESP32-Robot验证
> ROS2+Gazebo仿真已有多项目支持
> LLM+视觉+控制的融合是趋势

**洞察3: 中国天文AI项目可能不在GitHub**
> 金乌等可能在国内平台(Gitee/GitCode)
> 或尚未公开，属于内部项目

### 4.2 行动建议

| 优先级 | 行动项 | 说明 |
|--------|--------|------|
| **P0** | 填补AGI+天文空白 | 将AGI框架与天文库结合 |
| **P0** | 具身AI望远镜集成 | 参考chimera+llm-robot-control |
| **P1** | 4-Agent并行协调器 | 实现真AGI推理 |
| **P1** | 向量记忆检索 | 提升上下文理解 |
| **P2** | 过拟合自纠正 | RL+GEPA叠加 |

### 4.3 技术栈确认

| 组件 | Stars | 用途 |
|------|-------|------|
| SuperAGI | 高 | AGI框架参考 |
| chimera | 42 | 天文台自动化参考 |
| llm-robot-control | 4 | 具身AI控制参考 |
| astropy | 非常高 | 天文计算核心 |
| Ollama | 170,437 | 本地LLM推理 |

---

## 五、新建Issue汇总

| Issue # | 主题 | 关联研究 |
|---------|------|---------|
| #26 | Jinwu和的中国天文AI模型 | 金乌搜索 |
| #27 | AGI天文应用 | AGI+天文 |
| #28 | 天文AGI综合 | 星系分类/系外行星 |
| #29 | 具身AI天文台应用 | 望远镜控制 |

---

## 六、结论

### 6.1 核心结论

1. **AGI+天文**: 巨大空白机会 - 没有项目将真AGI推理与天文数据结合
2. **具身AI+望远镜**: 空白机会 - 没有LLM控制的成熟天文台项目
3. **金乌等中国项目**: 未找到公开仓库 - 可能在内部或国内平台
4. **天文AGI**: 都是窄ML - 缺乏自主推理、多步规划能力

### 6.2 天问-AGI的差异化定位

```
竞争对手: 窄ML项目 (星系分类CNN、凌星检测ML等)
天问-AGI: 真AGI + 天文数据 + 望远镜控制 + 自主推理
差异化:   完整闭环 (调研→假说→验证→观测→学习)
```

---

## 七、文献来源

### 7.1 AGI框架参考

| 项目 | URL | Stars |
|------|-----|-------|
| SuperAGI | github.com/TransformerOptimus/SuperAGI | 高 |
| big-AGI | github.com/enricoros/big-AGI | 高 |
| AGiXT | github.com/Josh-XT/AGiXT | 高 |
| AgentForge | github.com/DataBassGit/AgentForge | 中 |

### 7.2 具身AI参考

| 项目 | URL | Stars |
|------|-----|-------|
| llm-robot-control | github.com/AlbertaBeef/llm-robot-control | 4 |
| chimera | github.com/astroufsc/chimera | 42 |
| ESP32-Robot | github.com/beixiangbei/ESP32-Robot | 0 |

### 7.3 天文AGI参考

| 项目 | URL | 特点 |
|------|-----|------|
| astronomy-ai-agent | github.com/sejalsksagar/astronomy-ai-agent | Google ADK+Gemini |
| CosmoPilot | github.com/anshhhcodes/CosmoPilot | 3D宇宙探索 |
| exoplanet-detection-ml-FINAL | github.com/ZeelMPatel/exoplanet-detection-machine-learning-FINAL | CNN凌星检测 |

---

**文档状态**: 研究完成，待审计
**下一步**: 发送到Issue #26, #27, #28, #29 等待Hermes审计

---

*研究团队: 4-Agent并行搜索 (agi-searcher, embodied-searcher, jinwu-searcher, astro-agi-searcher)*
*创建时间: 2026-05-01 13:00 CST*
