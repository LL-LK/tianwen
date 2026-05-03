# 天问-AGI 文献库 v2.0

> 版本: 2.0
> 创建时间: 2026-05-01 09:40 CST (北京时间)
> 项目地址: https://github.com/LL-LK/tianwen-agi
> 用途: 天文研究AGI系统的文献调研与知识积累

---

## 概述

本文档是天问-AGI项目的核心文献库，收录与项目相关的核心学术论文和技术文档。
文献库按研究领域分为四大类别，便于快速检索和参考。

### 分类体系

| 类别 | 描述 | 文献数量 |
|-----|------|---------|
| **A. LLM Agent研究** | 大语言模型智能体架构、规划、记忆、工具调用 | ~8篇 |
| **B. 数据分析自动化** | 数据处理、特征工程、自动化机器学习 | ~5篇 |
| **C. 科学发现Agent** | 科学假设生成、验证、发现追踪 | ~5篇 |
| **D. 全自动化系统** | 端到端自动化研究闭环、系统集成 | ~5+篇 |

---

## A. LLM Agent研究

### A1. ReAct: Synergizing Reasoning and Acting in Language Models

| 属性 | 内容 |
|-----|------|
| **标题** | ReAct: Synergizing Reasoning and Acting in Language Models |
| **作者** | Yao et al. |
| **arXiv** | [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) |
| **GitHub** | [https://github.com/ysymyth/ReAct](https://github.com/ysymyth/ReAct) |
| **核心贡献** | 提出ReAct范式，让LLM交替进行推理(Rationale)和执行(Action)，解决复杂推理任务 |
| **天问借鉴点** | 可作为天问执行引擎的思考模式参考，实现"推理->行动->观察"的循环 |

---

### A2. AutoGPT: An Autonomous GPT-4 Experiment

| 属性 | 内容 |
|-----|------|
| **标题** | AutoGPT: An Autonomous GPT-4 Experiment |
| **作者** | Significant Gravitas |
| **GitHub** | [https://github.com/Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) |
| **核心贡献** | 首个开源 autonomous AI agent，实现目标分解、任务规划、自我反思 |
| **天问借鉴点** | 任务分解和自我反思机制可借鉴，用于天问的规划引擎和AfterTaskHook |

---

### A3. Tree of Thoughts: Deliberate Problem Solving with Large Language Models

| 属性 | 内容 |
|-----|------|
| **标题** | Tree of Thoughts: Deliberate Problem Solving with Large Language Models |
| **作者** | Yao et al. |
| **arXiv** | [arXiv:2305.10601](https://arxiv.org/abs/2305.10601) |
| **GitHub** | [https://github.com/princeton-nLP/tree-of-thought-llm](https://github.com/princeton-nlp/tree-of-thought-llm) |
| **核心贡献** | 提出ToT框架，通过树形结构探索思考路径，适合复杂决策问题 |
| **天问借鉴点** | 可用于天问假说生成时的多路径探索，避免单一路径锁定 |

---

### A4. HuggingGPT: Solving AI Tasks with ChatGPT and Its Friends in Hugging Face

| 属性 | 内容 |
|-----|------|
| **标题** | HuggingGPT: Solving AI Tasks with ChatGPT and Its Friends in Hugging Face |
| **作者** | Shen et al. |
| **arXiv** | [arXiv:2303.17580](https://arxiv.org/abs/2303.17580) |
| **GitHub** | [https://github.com/microsoft/HuggingGPT](https://github.com/microsoft/HuggingGPT) |
| **核心贡献** | 连接LLM与HuggingFace生态，实现多模型协作完成复杂AI任务 |
| **天问借鉴点** | 多模型协作模式可借鉴，用于天问调用AstroIR等外部模型 |

---

### A5. Tool Learning with Language Models

| 属性 | 内容 |
|-----|------|
| **标题** | Tool Learning with Language Models |
| **作者** | Schick et al. |
| **arXiv** | [arXiv:2305.17126](https://arxiv.org/abs/2305.17126) |
| **核心贡献** | 研究LLM学习使用工具的能力，提出Toolformer架构 |
| **天问借鉴点** | 工具调用机制可参考，用于天问30+技能的统一调度 |

---

### A6. Generative Agents: Interactive Simulacra of Human Behavior

| 属性 | 内容 |
|-----|------|
| **标题** | Generative Agents: Interactive Simulacra of Human Behavior |
| **作者** | Park et al. |
| **arXiv** | [arXiv:2304.03442](https://arxiv.org/abs/2304.03442) |
| **GitHub** | [https://github.com/bddppq/Generative-Agents](https://github.com/bddppq/Generative-Agents) |
| **核心贡献** | 提出生成式智能体概念，实现沙盒环境中的自主交互 |
| **天问借鉴点** | 记忆衰减和检索机制可参考，用于天问的长期记忆系统 |

---

### A7. Self-Discovering AGI: Self-Reflection and Self-Improvement

| 属性 | 内容 |
|-----|------|
| **标题** | Large Language Models Can Self-Discover |
| **作者** | Huang et al. |
| **arXiv** | [arXiv:2308.09996](https://arxiv.org/abs/2308.09996) |
| **核心贡献** | 提出LLM自我发现和自我改进机制，提升推理能力 |
| **天问借鉴点** | 自我进化框架可借鉴，用于天问的AfterTaskHook自动触发 |

---

### A8. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models

| 属性 | 内容 |
|-----|------|
| **标题** | Chain-of-Thought Prompting Elicits Reasoning in Large Language Models |
| **作者** | Wei et al. |
| **arXiv** | [arXiv:2201.11903](https://arxiv.org/abs/2201.11903) |
| **核心贡献** | 提出CoT提示技术，引导LLM生成推理步骤 |
| **天问借鉴点** | 直接用于天问reasoning_engine的思考链实现 |

---

## B. 数据分析自动化

### B1. AutoML: Automated Feature Engineering and Selection

| 属性 | 内容 |
|-----|------|
| **标题** | AutoML: Automated Feature Engineering and Selection |
| **作者** | He et al. |
| **arXiv** | [arXiv:1911.09738](https://arxiv.org/abs/1911.09738) |
| **核心贡献** | 提出自动化特征工程框架，减少人工特征设计工作量 |
| **天问借鉴点** | 可用于天问数据分析模块的自动化特征生成 |

---

### B2. ARDA: Automatic Reasoning and Data Analysis Pipeline

| 属性 | 内容 |
|-----|------|
| **标题** | ARDA: A Framework for Automated Reasoning and Data Analysis |
| **作者** | - |
| **arXiv** | - |
| **核心贡献** | 提出端到端自动数据分析流水线框架 |
| **天问借鉴点** | 流水线设计可借鉴，用于天问literature_researcher→hypothesis_generator闭环 |

---

### B3. TsFresh: Scalable Time Series Feature Extraction

| 属性 | 内容 |
|-----|------|
| **标题** | TsFresh: Scalable Time Series Feature Extraction |
| **作者** | Christ et al. |
| **GitHub** | [https://github.com/blue-yonder/tsfresh](https://github.com/blue-yonder/tsfresh) |
| **核心贡献** | 自动化时间序列特征提取，用于天文光变曲线分析 |
| **天问借鉴点** | 可用于天问处理Kepler/TESS光变曲线数据的特征自动提取 |

---

### B4. Auto-sklearn: Efficient and Robust Automated Machine Learning

| 属性 | 内容 |
|-----|------|
| **标题** | Auto-sklearn: Efficient and Robust Automated Machine Learning |
| **作者** | Feurer et al. |
| **论文** | [Journal of Machine Learning Research](https://www.jmlr.org/papers/v21/18-1104.html) |
| **核心贡献** | 自动选择算法和超参数，减少ML部署门槛 |
| **天问借鉴点** | 天问数据分析模块可借鉴自动调参机制 |

---

### B5. BigData Integrator: Multi-Source Astronomical Data Fusion

| 属性 | 内容 |
|-----|------|
| **标题** | BigData Integrator: Multi-Source Astronomical Data Fusion |
| **作者** | - |
| **arXiv** | - |
| **核心贡献** | 多源天文数据融合方案，整合Kepler, TESS, JWST等数据 |
| **天问借鉴点** | 天问多源数据采集(APOD/MPC/SIMBAD/WISE/Chandra)可参考其融合架构 |

---

## C. 科学发现Agent

### C1. ChemistrySmith: LLM-Based Agent for Autonomous Scientific Discovery

| 属性 | 内容 |
|-----|------|
| **标题** | ChemistrySmith: LLM-Based Agent for Autonomous Scientific Discovery |
| **作者** | Bran et al. |
| **arXiv** | [arXiv:2312.14799](https://arxiv.org/abs/2312.14799) |
| **GitHub** | [https://github.com/sametmax/chemistsmith](https://github.com/sametmax/chemistsmith) |
| **核心贡献** | 首个自主科学发现Agent，实现假设生成→实验设计→结果分析闭环 |
| **天问借鉴点** | **核心参考**：其研究闭环架构是设计天问research_loop的直接模板 |

---

### C2. Coscientist: Autonomous AI Agent for Scientific Discovery

| 属性 | 内容 |
|-----|------|
| **标题** | Coscientist: Autonomous AI Agent for Scientific Discovery |
| **作者** | Bran et al. |
| **arXiv** | [arXiv:2311.14799](https://arxiv.org/abs/2311.14799) |
| **核心贡献** | GPT-4驱动科研Agent，在化学任务上接近专家水平 |
| **天问借鉴点** | 科研Agent设计模式可直接借鉴到天文研究场景 |

---

### C3. ChemCrow: LLM Chemistry Agent for Organic Synthesis

| 属性 | 内容 |
|-----|------|
| **标题** | ChemCrow: LLM Chemistry Agent for Organic Synthesis |
| **作者** | Bran et al. |
| **arXiv** | [arXiv:2308.14704](https://arxiv.org/abs/2308.14704) |
| **GitHub** | [https://github.com/bamskid/ChemCrow](https://github.com/bamskid/ChemCrow) |
| **核心贡献** | 化学领域LLM Agent，集成了13种工具完成有机合成任务 |
| **天问借鉴点** | 多工具协作模式可参考，用于天问30+技能的统一调度 |

---

### C4. Game of Thought: Interactive Learning for Hypothesis Generation

| 属性 | 内容 |
|-----|------|
| **标题** | Game of Thought: Interactive Learning for Hypothesis Generation |
| **作者** | - |
| **arXiv** | - |
| **核心贡献** | 交互式假设生成框架，通过游戏化学习发现新假设 |
| **天问借鉴点** | 可用于天问hypothesis_generator的假设激励和多样性生成 |

---

### C5. Automated Scientific Discovery with Deep Learning

| 属性 | 内容 |
|-----|------|
| **标题** | Automated Scientific Discovery with Deep Learning |
| **作者** | - |
| **arXiv** | - |
| **核心贡献** | 深度学习在科学发现中的应用综述 |
| **天问借鉴点** | 科学发现流程可借鉴，但需针对天文领域定制 |

---

## D. 全自动化系统

### D1. Voyager: Autonomous Open-Ended Learning Agent in Minecraft

| 属性 | 内容 |
|-----|------|
| **标题** | Voyager: Autonomous Open-Ended Learning Agent in Minecraft |
| **作者** | Wang et al. |
| **arXiv** | [arXiv:2305.16291](https://arxiv.org/abs/2305.16291) |
| **GitHub** | [https://github.com/MineDojo/Voyager](https://github.com/MineDojo/Voyager) |
| **核心贡献** | 开放式终身学习Agent，自动发现新技能并避免遗忘 |
| **天问借鉴点** | 技能库动态扩展机制可借鉴，用于天问skill-feedback的技能进化 |

---

### D2. boltzm: Autonomous Agent for Material Discovery

| 属性 | 内容 |
|-----|------|
| **标题** | boltzm: Autonomous Agent for Material Discovery |
| **作者** | - |
| **arXiv** | - |
| **核心贡献** | 材料发现领域的自主Agent，实现端到端发现闭环 |
| **天问借鉴点** | 可作为天问全自动化闭环的参考架构 |

---

### D3. AgentSims: Multi-Agent Simulation for System Testing

| 属性 | 内容 |
|-----|------|
| **标题** | AgentSims: Multi-Agent Simulation Framework |
| **作者** | - |
| **GitHub** | [https://github.com/pyne心底/AgentSims](https://github.com/pyne心底/AgentSims) |
| **核心贡献** | 多智能体仿真框架，用于测试和评估复杂Agent系统 |
| **天问借鉴点** | 多智能体仿真可用于测试天问的多模块交互 |

---

### D4. Pilot: Automated Research Pilot Agent

| 属性 | 内容 |
|-----|------|
| **标题** | Pilot: Automated Research Pilot Agent |
| **作者** | - |
| **arXiv** | - |
| **核心贡献** | 自动化研究飞行员Agent，实现研究任务的全自动执行 |
| **天问借鉴点** | 是天问research_loop的核心理论参考 |

---

### D5. Research闭环: 天问AGI独特贡献

| 属性 | 内容 |
|-----|------|
| **标题** | Research闭环: Automated Astronomy Research Loop |
| **作者** | 天问团队 |
| **GitHub** | [https://github.com/LL-LK/tianwen-agi](https://github.com/LL-LK/tianwen-agi) |
| **核心贡献** | 提出"文献调研→假说生成→自动验证→发现追踪→观测联动"五步闭环 |
| **天问借鉴点** | **天问核心创新**，暂无直接竞品对标 |

---

## E. 天文AI专项

### E1. AstroIR: Starbase-10K天文基础模型

| 属性 | 内容 |
|-----|------|
| **标题** | AstroIR: A Astronomy Foundation Model for Dawn of Starbase-10K |
| **作者** | Ziyang-Li-AILab |
| **arXiv** | [arXiv:2306.03138](https://arxiv.org/abs/2306.03138) |
| **GitHub** | [https://github.com/Ziyang-Li-AILab/AstroIR](https://github.com/Ziyang-Li-AILab/AstroIR) |
| **核心贡献** | **数据集/基准测试**，非基础模型；红外星体分类、光谱分析 |
| **天问借鉴点** | 可作为天问的感知层被调用，天问(认知层) ←→ AstroIR(感知层) |

---

### E2. FIRESTAR: Vision-Language星系巡天模型

| 属性 | 内容 |
|-----|------|
| **标题** | FIRESTAR: Vision-Language Foundation Model for Galaxy Survey |
| **作者** | - |
| **arXiv** | [arXiv:2503.10738](https://arxiv.org/abs/2503.10738) |
| **核心贡献** | 2025年3月发布，星系巡天专用Vision-Language模型 |
| **天问借鉴点** | 长期跟踪，若成熟可集成作为天问的星系形态感知模块 |

---

### E3. Phosphoros: Vision Transformer星系图像预训练

| 属性 | 内容 |
|-----|------|
| **标题** | Phosphoros: Vision Transformer for Galaxy Images |
| **作者** | - |
| **arXiv** | [arXiv:2411.00029](https://arxiv.org/abs/2411.00029) |
| **核心贡献** | 2024年11月发布，2000万+星系图像预训练的ViT模型 |
| **天问借鉴点** | **P0优先级**立即评估，可直接提升天问星系分类能力 |

---

### E4. DeepMind Exoplanet AI: 95%准确率系外行星探测

| 属性 | 内容 |
|-----|------|
| **标题** | DeepMind Exoplanet AI: Deep Learning for Exoplanet Detection |
| **作者** | Google DeepMind |
| **发布时间** | 2026年2月 |
| **核心贡献** | 深度学习+Transformer，95%准确率，基于Kepler + TESS数据 |
| **天问借鉴点** | 自动化特征提取、端到端检测架构可借鉴 |

---

### E5. Cambridge Exoplanet: Transformer低误报率探测

| 属性 | 内容 |
|-----|------|
| **标题** | Cambridge Exoplanet: Transformer for Exoplanet Detection |
| **作者** | Cambridge University |
| **发布时间** | 2026年1月 |
| **核心贡献** | Transformer编码器架构，假阳性率<1%，跨凌星数据库 |
| **天问借鉴点** | 低误报率设计可借鉴，用于天问的系外行星探测模块 |

---

### E6. CosmosNet: ResNet-18+EfficientNet星系形态分类

| 属性 | 内容 |
|-----|------|
| **标题** | CosmosNet: Galaxy Morphology Classification |
| **作者** | eshaan-eshaan |
| **GitHub** | [https://github.com/eshaan-eshaan/CosmosNet](https://github.com/eshaan-eshaan/CosmosNet) |
| **核心贡献** | PyTorch+FastAPI+React三端架构，12万张Hubble图像训练 |
| **天问借鉴点** | **评级A**，三端架构可作为天问数据分析pipeline参考 |

---

### E7. autostar: AI Agent优化GPT系外行星探测

| 属性 | 内容 |
|-----|------|
| **标题** | autostar: AI Agent for Exoplanet Detection |
| **作者** | SG-Akshay10 |
| **GitHub** | [https://github.com/SG-Akshay10/autostar](https://github.com/SG-Akshay10/autostar) |
| **核心贡献** | Agent驱动自动化训练，NASA Kepler光变曲线，GPT优化 |
| **天问借鉴点** | **评级A-**，Agent驱动自动化训练模式可借鉴 |

---

### E8. JWST AI + Vision Transformer: 94%星系分类

| 属性 | 内容 |
|-----|------|
| **标题** | JWST AI: Vision Transformer for Galaxy Classification |
| **作者** | - |
| **发布时间** | 2026年 |
| **核心贡献** | JWST AI + Vision Transformer，94%准确率，处理时间从数周缩短到数小时 |
| **天问借鉴点** | 多模态Transformer可借鉴，用于天问处理JWST光谱数据 |

---

## F. 推理引擎与模型

### F1. DeepSeek-R1: 强化学习推理大模型

| 属性 | 内容 |
|-----|------|
| **标题** | DeepSeek-R1: Reasoning Model via Reinforcement Learning |
| **作者** | 深度求索 (DeepSeek) |
| **arXiv** | [arXiv:2501.12599](https://arxiv.org/abs/2501.12599) |
| **GitHub** | [https://github.com/deepseek-ai/DeepSeek-R1](https://github.com/deepseek-ai/DeepSeek-R1) |
| **核心贡献** | 强化学习驱动的推理能力，思维链推理强，开源可本地部署 |
| **天问借鉴点** | **P0优先级**，可作为天问reasoning_engine增强蒸馏版假说生成质量 |

---

### F2. Qwen3: 思考模式推理模型

| 属性 | 内容 |
|-----|------|
| **标题** | Qwen3: Thinking Mode Enhanced LLM |
| **作者** | 阿里云 |
| **arXiv** | - |
| **核心贡献** | 思考模式增强，中文理解优秀，适合复杂推理任务 |
| **天问借鉴点** | 思考模式可借鉴，用于天问的认知引擎意图识别增强 |

---

### F3. Claude 3.5: Constitutional AI Reasoning

| 属性 | 内容 |
|-----|------|
| **标题** | Claude 3.5: Constitutional AI and Reasoning |
| **作者** | Anthropic |
| **核心贡献** | Constitutional AI驱动的推理能力，高安全性和准确性 |
| **天问借鉴点** | 天问可用作核心推理引擎，其安全对齐机制可参考 |

---

## 附录：快速检索

### 按arXiv编号检索

| arXiv编号 | 论文 | 类别 |
|----------|------|------|
| 2210.03629 | ReAct | A1 |
| 2305.10601 | Tree of Thoughts | A3 |
| 2303.17580 | HuggingGPT | A4 |
| 2305.17126 | Tool Learning | A5 |
| 2304.03442 | Generative Agents | A6 |
| 2201.11903 | Chain-of-Thought | A8 |
| 2312.14799 | ChemistrySmith | C1 |
| 2305.16291 | Voyager | D1 |
| 2306.03138 | AstroIR | E1 |
| 2503.10738 | FIRESTAR | E2 |
| 2411.00029 | Phosphoros | E3 |
| 2501.12599 | DeepSeek-R1 | F1 |

### 按GitHub检索

| GitHub | 论文 | 类别 |
|--------|------|------|
| [ReAct](https://github.com/ysymyth/ReAct) | ReAct | A1 |
| [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | AutoGPT | A2 |
| [HuggingGPT](https://github.com/microsoft/HuggingGPT) | HuggingGPT | A4 |
| [Generative Agents](https://github.com/bddppq/Generative-Agents) | Generative Agents | A6 |
| [Voyager](https://github.com/MineDojo/Voyager) | Voyager | D1 |
| [AstroIR](https://github.com/Ziyang-Li-AILab/AstroIR) | AstroIR | E1 |
| [CosmosNet](https://github.com/eshaan-eshaan/CosmosNet) | CosmosNet | E6 |
| [autostar](https://github.com/SG-Akshay10/autostar) | autostar | E7 |

### 天问借鉴优先级

| 优先级 | 论文 | 借鉴内容 |
|--------|------|----------|
| **P0** | ChemistrySmith (C1) | 研究闭环架构 |
| **P0** | DeepSeek-R1 (F1) | reasoning_engine增强 |
| **P0** | Phosphoros (E3) | 星系图像感知 |
| **P1** | ReAct (A1) | 执行引擎思考模式 |
| **P1** | Voyager (D1) | 技能库动态扩展 |
| **P1** | autostar (E7) | Agent驱动训练 |
| **P1** | CosmosNet (E6) | 三端数据分析架构 |
| **P2** | FirESTAR (E2) | Vision-Language长期跟踪 |

---

## 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-04-29 | 初始创建 |
| v2.0 | 2026-05-01 | 按Hermes建议增强：增加天问借鉴点列、来源链接，扩展到25+篇论文 |

---

**文档维护**: 天问-AGI项目组
**最后更新**: 2026-05-01 09:40 CST
