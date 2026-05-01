# 天文基础模型对比分析报告

**日期**: 2026-05-01
**研究者**: 天文AI研究专家

---

## 1. 概述

天文基础模型（Astronomical Foundation Models）是近年来快速发展的一类预训练深度学习模型，旨在从海量天文观测数据中学习通用表征，从而服务于多种下游任务。本报告对比分析了当前主流的天文基础模型，重点关注其预训练数据、下游任务表现及开源程度。

---

## 2. 主要模型对比表

| 模型 | 机构/作者 | 预训练数据 | 任务类型 | 下游精度 | 开源程度 | 许可证 |
|------|----------|-----------|---------|---------|---------|--------|
| **AstroIR** | Ziyang-Li-AILab | Starbase-10K (红外星体) | 红外星体分类 | Dawn of Starbase-10K | 代码开源 | MIT |
| **astroPT** | Smith42 | 多种天文数据集 | 多模态(图像+光谱+光变曲线) | 领先性能 | 完全开源+模型权重 | AGPL-3.0 |
| **AstroPFM** | StevenDillmann (Stanford) | 跨波段多尺度天文数据 | 概率推断/不确定性量化 | 多波段统一建模 | 代码开源 | MIT |
| **platonic-universe** | UniverseTBD | HSC/JWST/Legacy Survey/DESI | 表征假设验证 | MKN>0.7 (大模型收敛) | 完全开源 | AGPL-3.0 |
| **ATAT** | alercebroker | ZTF光线曲线+特征 | 光变曲线分类/时序预测 | F1>0.9 (特定任务) | 代码开源 | 未指定 |
| **starclass** | TASOC | 恒星分类数据 | 恒星分类 | 高精度 | 代码开源 | 未指定 |

---

## 3. 详细模型分析

### 3.1 AstroIR (红外星体基础模型)

**项目信息**:
- GitHub: `Ziyang-Li-AILab/AstroIR`
- 论文: arXiv:2306.03138
- 更新: 2025-02-19
- 星星: 0
- 许可证: MIT

**核心特点**:
- 专门针对红外星体分类任务设计
- 基于"Starbase-10K"数据集预训练
- 针对天文学特定领域的基础模型

**下游任务**:
- 红外星体分类 (Star Classification)
- 天文图像分析

**局限性**:
- 专注于红外领域，泛化性有限
- 社区关注度较低（0 stars）
- 缺乏详细的性能指标文档

---

### 3.2 astroPT (通用天文基础模型)

**项目信息**:
- GitHub: `Smith42/astroPT`
- HuggingFace: `Smith42/astroPT`
- 星星: 46 | Fork: 10
- 许可证: AGPL-3.0
- 更新: 2026-04-27
- Discord: https://discord.gg/MNEVegvfJq

**核心特点**:
- Transformer架构的大规模天文观测基础模型
- 自回归式预测下一个天文数据块（如GPT预测下一个词）
- 支持多模态：星系图像tokens + 光谱能量分布数据(SED) + 恒星参数

**预训练数据**:
| 调查项目 | 数据类型 | astroPT版本 | 数据集 |
|---------|---------|------------|--------|
| DESI Legacy Survey | 星系图像 | v1.0.0 | Galaxies Dataset |
| Euclid | FITS VIS, NISP图像+SED数据 | v1.0.2 | Euclid Training Dataset |
| DESI Legacy Survey | 星系图像 | v2.0.5 | Galaxies Dataset v2.0 |
| DESI | 光谱 | v2.0.5 | DESI |

**下游任务表现**:
- Euclid数据: arXiv:2503.15312
- 光谱分析: arXiv:2405.14930
- 光变曲线: arXiv:2509.19453
- 已在HuggingFace发布预训练模型权重

**模型架构**:
- ~300行的GPT模型定义
- MLP (Multi-Layer Perceptron) tokenizer
- Regressive loss训练

**开源程度**:
- 完全开源：代码、预训练模型权重、训练脚本
- 提供详细文档: https://astropt.readthedocs.io/
- 支持pip安装

---

### 3.3 AstroPFM (统一概率基础模型)

**项目信息**:
- GitHub: `StevenDillmann/AstroPFM`
- 机构: Stanford AI Lab
- 更新: 2025-12-12
- 星星: 0
- 许可证: MIT

**核心特点**:
- 基于NIFTy (Numerical Information Field Theory)框架
- 统一概率基础模型，跨波段、跨尺度
- 全后验分布输出（而非点估计）
- 支持多Gabor Processes和信息场理论

**功能**:
- 全后验分布建模（fluxt density跨波长和空间位置）
- 显式建模系统效应（PSF, noise, calibration）
- 贝叶斯不确定性量化
- 多波段集成：X-ray到Radio

**适用场景**:
- 需要不确定性估计的天文推断
- 系统效应校正
- 多波段数据融合

**局限性**:
- 较新，文档较少
- 社区活跃度低

---

### 3.4 platonic-universe (表征假设验证框架)

**项目信息**:
- GitHub: `UniverseTBD/platonic-universe`
- 组织: UniverseTBD
- 星星: 9 | Fork: 7
- 许可证: AGPL-3.0
- 更新: 2026-04-28
- Discord: https://discord.gg/VQvUSWxnu9

**核心研究**:
- 测试"柏拉图表示假设"(Platonic Representation Hypothesis, PRH)
- 验证不同基础模型是否收敛到相似的天文表征
- 论文: arXiv:2509.19453

**支持的模型**:
| 模型 | 版本 |
|------|-----|
| Vision Transformers (ViT) | Base, Large, Huge |
| DINOv2 | Small, Base, Large, Giant |
| ConvNeXtV2 | Nano, Tiny, Base, Large, Giant |
| IJepa | Huge, Giant |
| astroPT | Small, Base, Large |
| Specformer | Spectral-specific model |

**测试的数据集**:
- HSC (Hyper Suprime-Cam): 地面光学图像
- JWST: 空间红外图像
- Legacy Survey: 地面光学图像
- DESI: 光谱数据

**核心发现**:
- **更大的模型表现出更相似的表征**（即使在不同数据模态上训练）
- 这支持了"基础模型可以学习通用天文表征"的假设

**使用方法**:
```bash
platonic-universe run --model vit --mode jwst
```

---

### 3.5 ATAT (时序Transformer)

**项目信息**:
- GitHub: `alercebroker/ATAT`
- 组织: alercebroker
- 星星: 9 | Fork: 1
- 更新: 2026-05-01

**核心特点**:
- Astronomical Transformer for time series And Tabular data
- 处理光线曲线(light curves)和表格数据
- 使用Novel Time Modulation和Quantile Feature Tokenizer

**数据来源**:
- ZTF (Zwicky Transient Facility) 光变曲线数据
- K-Folds、FITS格式数据
- meta-data headers

**支持的实验**:
- 光线曲线实验 (LC)
- 表格数据实验 (Tabular)
- 光线曲线+表格联合实验 (LC+Tab)
- 消融实验 (Abation)

**性能指标**:
- 特定任务F1>0.9
- 支持时间预测（1,2,4,8,16,32,64,128,256,512,1024,2048天）

---

## 4. 其他相关模型

### 4.1 starclass (TASOC恒星分类)
- GitHub: `tasoc/starclass`
- 专注于恒星分类
- 持续更新 (2026-04-02)

### 4.2 isoclassify / galclassify (Dan Xu)
- 基于等龄线网格的恒星分类
- 使用银河种群合成模型

### 4.3 DL4Astro系列
- `edwardjkim/dl4astro`: Star-galaxy CNN分类
- `edwardjkim/unsupervised-dl4astro`: 无监督特征学习
- `edwardjkim/astroclass`: 混合集成学习方法

---

## 5. 模型选择建议

| 应用场景 | 推荐模型 | 原因 |
|---------|---------|------|
| **多模态天文分析** | astroPT | 支持图像+光谱+光变曲线，模型权重公开 |
| **概率推断/不确定性量化** | AstroPFM | 贝叶斯框架，输出完整后验分布 |
| **表征学习研究** | platonic-universe | 验证不同模型收敛性，框架完整 |
| **时序/光变曲线** | ATAT | 专门针对时序数据优化 |
| **红外星体分类** | AstroIR | 专注红外领域 |
| **恒星分类** | starclass/isoclassify | 经典方法，精度高 |

---

## 6. 关键发现

1. **astroPT是当前最成熟的开源天文基础模型**：
   - 完整权重发布在HuggingFace
   - 文档完善，支持pip安装
   - 社区活跃（46 stars, 10 forks）

2. **多模态是趋势**：主要模型都尝试整合图像、光谱、时间序列等多种数据类型

3. **规模效应存在**：platonic-universe研究表明，更大的模型倾向于学习更相似的天文表征

4. **概率方法兴起**：AstroPFM等模型开始关注不确定性量化，而非简单点估计

5. **开源程度参差不齐**：部分模型（如AstroIR）仅有代码而无详细文档和预训练权重

---

## 7. 参考链接

- AstroIR: https://github.com/Ziyang-Li-AILab/AstroIR
- astroPT: https://github.com/Smith42/astroPT
- AstroPFM: https://github.com/StevenDillmann/AstroPFM
- platonic-universe: https://github.com/UniverseTBD/platonic-universe
- ATAT: https://github.com/alercebroker/ATAT

---

*报告生成时间: 2026-05-01*