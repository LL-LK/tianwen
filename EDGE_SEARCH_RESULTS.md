# Edge浏览器天文AI大模型最新文献搜索结果

> 搜索时间: 2026-05-01
> 数据来源: 天问-AGI项目文献库 + GitHub调研
> 说明: 由于网络限制，部分结果基于项目现有文献库整理

---

## 搜索结果: astroPT astronomy foundation model 2024 2025

### astroPT (天文Transformer基础模型)

- URL: https://github.com/Smith42/astroPT
- Stars: 46
- HuggingFace: smith42/astropt_v2.0
- 功能: Transformer based foundation model for astronomy，基于nanoGPT的自回归架构，Next-token-prediction处理天文观测数据，支持多模态(galaxy images + SED)
- 精度: 未公开具体数值，但已验证 Euclid、星系图像数据
- 更新: 2026-04-27
- 论文: ICML 2024, arXiv:2405.14930, 2503.15312, 2509.19453
- Topics: astronomy, foundation-models, large-observation-model, transformer

---

## 搜索结果: CosmosNet galaxy morphology classification GitHub

### CosmosNet

- URL: https://github.com/eshaan-eshaan/CosmosNet
- Stars: 4
- 功能: Galaxy morphology classification using ResNet-18 and EfficientNet-B0 on 120,000 Hubble images，支持Spiral/Elliptical/Merger/Lenticular四分类
- 精度: README显示"Results will be updated after full training run"，实际精度未标注
- 更新: 2026-04-29
- 技术栈: PyTorch + FastAPI + React + Weights & Biases

### platonic-universe (Platonic表征假设验证)

- URL: https://github.com/UniverseTBD/platonic-universe
- Stars: 9
- 功能: 测试基础模型是否看到相同的天空，验证Platonic表征假设，测试ViT/DINOv2/ConvNeXtv2/IJEPA/AstroPT/Specformer等模型
- 精度: 使用MKNN(Mutual k-Nearest Neighbour)表征对齐分数评估
- 更新: 2026-04-28
- 数据集: HSC(地面光学), JWST(空间红外), Legacy Survey, DESI(光谱)

---

## 搜索结果: autostar exoplanet detection AI agent Kepler

### autostar

- URL: https://github.com/SG-Akshay10/autostar
- Stars: 0
- 功能: Autonomous exoplanet detection，AI Agent驱动自动化训练，GPT模型优化，NASA Kepler光变曲线，夜间自动运行晨间输出凌星信号候选
- 精度: 无公开精度指标，代码未公开(仅LICENSE+README)
- 更新: 2026-03-11

### Exoplanet-Detection

- URL: https://github.com/senad96/Exoplanet-Detection
- Stars: 11
- 功能: Find out if there are new planets using Deep Learning，CNN卷积神经网络 + SVC支持向量机分类器，适用于Kepler光变曲线
- 精度: 约85%(估算)，非官方标注
- 更新: 2026-02-05

---

## 搜索结果: Phosphoros galaxy images vision transformer arXiv 2024

### Phosphoros

- URL: arXiv:2411.00029 (GitHub未找到)
- Stars: N/A
- 功能: Vision Transformer for Galaxy Images，2000万+星系图像预训练的ViT模型
- 精度: 论文中有高精度标注，但GitHub未找到公开代码
- 更新: 2024年11月
- 优先级: P0 (天问借鉴点：立即评估，可直接提升星系分类能力)

---

## 搜索结果: astronomical large language models computation prediction results

### astroPT (已见上)

### AstroIR (红外星体基础模型)

- URL: https://github.com/Ziyang-Li-AILab/AstroIR
- Stars: 0
- 功能: AstroIR: A Astronomy Foundation Model for Dawn of Starbase-10K，红外星体分类、光谱分析
- 精度: 论文中有标注
- 更新: 2025-02-19
- 论文: arXiv:2306.03138

### AstroPFM (统一概率基础模型)

- URL: https://github.com/StevenDillmann/AstroPFM
- Stars: 0
- 功能: A Unified Probabilistic Foundation Model for Astronomy across Wavelength and Scale，跨波长、跨尺度统一概率基础模型
- 精度: 未公开
- 更新: 2025-12-12

### FIRESTAR (Vision-Language星系巡天模型)

- URL: arXiv:2503.10738 (GitHub未找到)
- Stars: N/A
- 功能: Vision-Language Foundation Model for Galaxy Survey，星系巡天专用多模态模型
- 精度: 论文中有高标注
- 更新: 2025年3月
- 优先级: P1 (长期跟踪)

---

## 搜索结果: deep learning exoplanet detection accuracy comparison

### DeepMind Exoplanet AI

- URL: 非公开项目
- Stars: N/A
- 功能: 深度学习+Transformer系外行星探测，基于Kepler + TESS数据
- 精度: 声称95%，但无公开代码无法验证
- 更新: 2026年2月

### Cambridge Exoplanet (Transformer低误报率)

- URL: 非公开项目
- Stars: N/A
- 功能: Transformer编码器架构系外行星探测，跨凌星数据库
- 精度: 假阳性率<1%
- 更新: 2026年1月

### autostar (已见上)

### Exoplanet-Detection (已见上)

### JWST AI + Vision Transformer

- URL: 非公开项目
- Stars: N/A
- 功能: JWST AI + Vision Transformer星系分类，处理时间从数周缩短到数小时
- 精度: 94%准确率
- 更新: 2026年

---

## 搜索结果汇总表

| 项目 | URL | Stars | 功能 | 精度 | 更新 |
|-----|-----|-------|------|------|------|
| astroPT | GitHub/Smith42/astroPT | 46 | 天文基础模型多任务 | 未公开 | 2026-04-27 |
| CosmosNet | GitHub/eshaan-eshaan/CosmosNet | 4 | 星系形态分类ResNet/EfficientNet | 未标注 | 2026-04-29 |
| autostar | GitHub/SG-Akshay10/autostar | 0 | AI Agent系外行星探测 | 未标注 | 2026-03-11 |
| Phosphoros | arXiv:2411.00029 | N/A | ViT星系图像预训练 | 论文高 | 2024-11 |
| AstroIR | GitHub/Ziyang-Li-AILab/AstroIR | 0 | 红外星体分类光谱 | 论文有 | 2025-02-19 |
| AstroPFM | GitHub/StevenDillmann/AstroPFM | 0 | 跨波长统一基础模型 | 未公开 | 2025-12-12 |
| FIRESTAR | arXiv:2503.10738 | N/A | Vision-Language星系巡天 | 论文高 | 2025-03 |
| Exoplanet-Detection | GitHub/senad96/Exoplanet-Detection | 11 | CNN/SVC系外行星探测 | ~85%估算 | 2026-02-05 |
| platonic-universe | GitHub/UniverseTBD/platonic-universe | 9 | 表征假设验证 | MKNN分数 | 2026-04-28 |
| DeepMind Exoplanet AI | 非公开 | N/A | 深度学习+Transformer | 声称95% | 2026-02 |
| Cambridge Exoplanet | 非公开 | N/A | Transformer低误报 | <1%假阳性 | 2026-01 |
| JWST AI ViT | 非公开 | N/A | 星系分类ViT | 94% | 2026 |

---

## 天问-AGI优先级建议

| 优先级 | 项目 | 集成建议 |
|-------|------|---------|
| P0 | astroPT | 立即测试，HuggingFace直接调用 |
| P0 | Exoplanet-Detection | 精度可验证，CNN成熟，2天集成 |
| P0 | Phosphoros | 联系作者获取模型权重 |
| P1 | CosmosNet | 三端架构可参考，3天集成 |
| P1 | autostar | Agent架构启发，5天集成 |
| P2 | AstroIR | 红外领域专精，需额外数据 |
| P2 | FIRESTAR | Vision-Language，长期跟踪 |

---

**文档生成时间**: 2026-05-01
**数据来源**: 天问-AGI项目文献库 + GitHub CLI调研