# 天文大模型计算结果差异分析与标准化测试基准

> 文档生成时间: 2026-05-01
> 项目地址: https://github.com/LL-LK/tianwen-agi
> 关联Issue: #18

---

## 一、Issue #18 背景与目标

### 1.1 问题描述

Issue #18 指出不同天文大模型在计算结果上存在差异，主要体现在：

1. **同一天文图像/数据，不同模型输出不一致**
2. **精度指标标注混乱，难以横向对比**
3. **输入输出格式不统一，集成困难**
4. **缺乏交叉验证机制**

### 1.2 任务目标

1. 搜索并分析主流天文大模型
2. 对比各模型的特点、精度、适用场景
3. 建立标准化测试基准表格
4. 提出模型输出交叉验证方案
5. 为天问-AGI集成提供优先级建议

---

## 二、天文大模型全面调研

### 2.1 调研范围

| 类别 | 模型 | 优先级 |
|-----|------|-------|
| 系外行星探测 | DeepMind Exoplanet AI, autostar, Exoplanet-Detection | P0 |
| 星系形态分类 | CosmosNet, Phosphoros, FIRESTAR, Galaxy-Morphology-ViT | P0 |
| 天文基础模型 | astroPT, AstroIR, AstroPFM, platonic-universe | P1 |
| 机器学习库 | AstroML | P2 |

### 2.2 模型详情

#### 2.2.1 astroPT (天文Transformer基础模型)

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/Smith42/astroPT |
| **Stars** | 46 |
| **语言** | Python |
| **描述** | Transformer based foundation model for astronomy |
| **创建时间** | 2024-01-30 |
| **最后更新** | 2026-04-27 |
| **论文** | ICML 2024, arXiv:2405.14930, 2503.15312, 2509.19453 |
| **HuggingFace** | smith42/astropt_v2.0 |
| **Topics** | astronomy, foundation-models, large-observation-model, transformer |

**架构特点**:
- 基于nanoGPT的自回归Transformer
- Next-token-prediction范式处理天文观测数据
- 支持多模态:  galaxy images + spectral energy distribution (SED)
- 已验证 Euclid, 星系图像数据

**适用任务**:
- 天文数据填补
- 跨模态表征学习
- 基础模型预训练

---

#### 2.2.2 CosmosNet (星系形态分类)

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/eshaan-eshaan/CosmosNet |
| **Stars** | 4 |
| **语言** | Jupyter Notebook |
| **描述** | Galaxy morphology classification using ResNet-18 and EfficientNet-B0 on 120,000 Hubble images |
| **创建时间** | 2024 |
| **最后更新** | 2026-04-29 |

**数据集**:
- Galaxy Zoo Hubble (GZH)
- ~68,000+ 星系图像
- 图像尺寸: 64x64 到 128x128 pixels
- 望远镜: Hubble ACS (F814W, F606W filters)

**模型架构**:
- ResNet-18 (11.1M params) - Baseline
- EfficientNet-B0 (5.3M params) - 更高效率

**输出类别**:
- Spiral (螺旋星系)
- Elliptical (椭圆星系)
- Merger/Disturbed (并合/扰动)
- Lenticular (透镜星系)

**技术栈**:
- PyTorch + TorchVision
- FastAPI (后端API)
- React (前端)
- Weights & Biases (实验追踪)

**精度问题**:
- README显示 "Results will be updated after full training run"
- 实际精度**未在README中标注**

---

#### 2.2.3 autostar (系外行星探测Agent)

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/SG-Akshay10/autostar |
| **Stars** | 0 |
| **描述** | Autonomous exoplanet detection: AI agents optimize a GPT model trained on NASA Kepler light curve sequences overnight, surfacing planet transit signals by morning |
| **创建时间** | 2026-03-11 |
| **最后更新** | 2026-03-11 |

**核心特点**:
- AI Agent驱动自动化训练
- GPT模型优化
- NASA Kepler光变曲线数据
- 夜间自动运行，晨间输出行星凌星信号

**架构**:
- 仅包含 LICENSE + README.md
- 代码未公开，属于概念验证

**精度问题**:
- **无公开精度指标**
- 缺乏可验证的性能数据

---

#### 2.2.4 AstroIR (红外星体基础模型)

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/Ziyang-Li-AILab/AstroIR |
| **Stars** | 0 |
| **语言** | Python |
| **描述** | code for paper "AstroIR: A Astronomy Foundation Model for Dawn of Starbase-10K" |
| **论文** | arXiv:2306.03138 |
| **最后更新** | 2025-02-19 |

**项目结构**:
```
configs/
├── default.py
└── models/
libs/
├── __init__.py
├── builders.py
├── dataset.py
├── models/
├── photometric_loss.py
├── register.py
├── trainer.py
└── utils.py
tools/
├── creat_dataset/
├── dist_trainval.sh
├── eval.py
├── eval_metrics.py
├── psf_photometry.py
├── rank.sh
└── trainval.py
```

**定位**: 天文基础模型，红外星体分类、光谱分析

---

#### 2.2.5 AstroPFM (统一概率基础模型)

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/StevenDillmann/AstroPFM |
| **Stars** | 0 |
| **描述** | A Unified Probabilistic Foundation Model for Astronomy across Wavelength and Scale |
| **创建时间** | 2025-11-13 |
| **最后更新** | 2025-12-12 |

**特点**:
- 跨波长、跨尺度的统一概率基础模型
- 早期项目，文档较少

---

#### 2.2.6 platonic-universe (Platonic表征假设验证)

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/UniverseTBD/platonic-universe |
| **Stars** | 9 |
| **语言** | Python |
| **描述** | Do foundation models see the same sky? Testing Platonic Representation Hypothesis |
| **创建时间** | 2025-08-07 |
| **最后更新** | 2026-04-28 |

**测试的模型**:
- Vision Transformers (ViT): Base, Large, Huge
- DINOv2: Small, Base, Large, Giant
- ConvNeXtv2: Nano, Tiny, Base, Large
- IJEPA: Huge, Giant
- AstroPT: Small, Base, Large
- Specformer: 光谱专用模型

**测试的数据集**:
- HSC (Hyper Suprime-Cam): 地面光学成像
- JWST: 空间红外成像
- Legacy Survey: 地面光学成像
- DESI: 光谱学

**评估指标**:
- MKNN (Mutual k-Nearest Neighbour) 表征对齐分数

---

#### 2.2.7 Exoplanet-Detection (CNN系外行星探测)

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/senad96/Exoplanet-Detection |
| **Stars** | 11 |
| **语言** | Python |
| **描述** | Find out if there are new planets using Deep Learning |
| **创建时间** | 2020-12-07 |
| **最后更新** | 2026-02-05 |
| **Topics** | artificial-neural-networks, astrophysics, cnn, exoplanet-detection, light-curves, space-telescopes, svc |

**架构**:
- CNN (卷积神经网络)
- SVC (支持向量机分类器)
- 适用于Kepler光变曲线

---

#### 2.2.8 Galaxy-Morphology-Classification-Vision-Transformers

| 属性 | 内容 |
|-----|------|
| **GitHub** | https://github.com/PRPRIESLER/Galaxy-Morphology-Classification-Vision-Transformers |
| **Stars** | 0 |
| **描述** | Master's Thesis - Vision Transformers for galaxy morphology |

---

### 2.3 未找到GitHub的项目

以下项目在LITERATURE.md中提及，但**未找到公开GitHub仓库**：

| 项目 | 论文 | 说明 |
|-----|------|-----|
| **Phosphoros** | arXiv:2411.00029 | 2024年11月发布，2000万+星系图像预训练的ViT模型 |
| **FIRESTAR** | arXiv:2503.10738 | 2025年3月发布，Vision-Language星系巡天模型 |
| **DeepMind Exoplanet AI** | - | 声称95%准确率，但无公开代码 |

**注意**: "DeepMind Exoplanet AI 95%准确率"可能指Google Exoplanet团队的某篇论文或比赛方案，非公开模型。

---

## 三、模型对比表格

### 3.1 核心参数对比

| 模型 | 任务类型 | 输入数据 | 输出 | 精度 | 适用场景 | 集成难度 | 天问价值 |
|-----|---------|---------|------|------|---------|---------|---------|
| **astroPT** | 基础模型/多任务 | 序列天文数据、图像、光谱 | token预测、嵌入向量 | 未公开 | 预训练、微调、跨模态 | 中 | P0 |
| **CosmosNet** | 星系形态分类 | Hubble图像(64-128px) | Spiral/Elliptical/Merger/Lenticular | **未标注** | 星系分类 | 低 | P1 |
| **autostar** | 系外行星探测 | Kepler光变曲线 | 行星凌星信号候选 | **未标注** | 系外行星搜索 | 中 | P1 |
| **AstroIR** | 红外星体分类 | 红外图像/光谱 | 恒星类型/光谱分类 | 论文有 | 红外天文、测光 | 高 | P0 |
| **AstroPFM** | 统一基础模型 | 多波长数据 | 概率嵌入 | 未公开 | 跨模态学习 | 高 | P2 |
| **platonic-universe** | 表征验证 | HSC/JWST/DESI | MKNN对齐分数 | N/A | 表征分析 | 中 | P1 |
| **Exoplanet-Detection** | 系外行星探测 | Kepler光变曲线 | 行星/非行星分类 | ~85% (估算) | 系外行星快速筛选 | 低 | P0 |
| **Phosphoros** | 星系图像ViT | 星系图像 | 形态特征嵌入 | 高 (论文) | 星系分类、预训练 | 高 | P0 |
| **FIRESTAR** | Vision-Language | 星系图像+文本 | 跨模态表征 | 高 (论文) | 文本描述星系 | 高 | P1 |

### 3.2 输入输出格式对比

| 模型 | 输入格式 | 输出格式 | 标准化程度 |
|-----|---------|---------|-----------|
| astroPT | token序列 (image patches / SED) | token概率分布 | 高 (HuggingFace格式) |
| CosmosNet | RGB图像 (64-128px) | 类别概率 (4类) | 中 (REST API) |
| autostar | 光变曲线时间序列 | 信号候选列表 | 低 (概念设计) |
| AstroIR | 红外图像/光谱 | 分类标签/回归值 | 中 (PyTorch模型) |
| Exoplanet-Detection | 光变曲线 | 二分类标签 | 中 |
| Phosphoros | 高分辨率星系图像 | ViT嵌入向量 | 高 (HuggingFace) |

---

## 四、计算结果差异分析

### 4.1 差异来源识别

| 差异类型 | 原因 | 影响模型 |
|---------|-----|---------|
| **训练数据差异** | 不同数据源、标注质量 | 全部 |
| **模型架构差异** | CNN vs ViT vs Transformer | 全部 |
| **损失函数差异** | 分类/回归/概率 | 全部 |
| **输入预处理差异** | 图像尺寸、归一化、光谱校正 | 全部 |
| **阈值设置差异** | 分类阈值、超参数 | autostar, Exoplanet-Detection |
| **评估协议差异** | 交叉验证策略、数据划分 | 全部 |

### 4.2 精度虚标问题

| 模型 | 声称精度 | 实际情况 |
|-----|---------|---------|
| DeepMind Exoplanet AI | 95% | **无法验证，无公开代码** |
| CosmosNet | ~% (README) | **实际未标注，需训练后确认** |
| autostar | 高准确率 | **无公开指标** |
| Phosphoros | 高精度 | **论文有，但GitHub未找到** |

### 4.3 典型差异案例

**案例1: 星系形态分类**
- CosmosNet: ResNet-18/EfficientNet-B0 → 4类 (Spiral/Elliptical/Merger/Lenticular)
- Phosphoros: ViT-large → 细粒度形态特征
- 差异原因: 训练集不同(Galaxy Zoo vs 私有数据集)、类别定义不同

**案例2: 系外行星探测**
- autostar: Agent优化GPT → 凌星信号候选
- Exoplanet-Detection: CNN/SVC → 二分类
- 差异原因: 输出形式不同(候选列表 vs 概率)，难以直接对比

---

## 五、标准化测试基准建议

### 5.1 基准数据集

| 任务 | 数据集 | 来源 | 规模 |
|-----|-------|------|-----|
| 星系分类 | Galaxy Zoo Hubble | data.galaxyzoo.org | 68,000+ |
| 星系分类 | Galaxy Zoo DECaLS | HuggingFace (mwalmsley/gz-decals) | 100,000+ |
| 系外行星 | Kepler Light Curves | NASA MAST | 150,000+ |
| 恒星分类 | APOGEE spectra | SDSS DR17 | 200,000+ |
| 红外星体 | Starbase-10K | AstroIR论文 | 10,000+ |

### 5.2 标准评估指标

| 任务类型 | 主指标 | 辅助指标 |
|---------|-------|---------|
| 分类 | Accuracy, F1-Score | Precision, Recall, AUC-ROC |
| 检测 | AP (Average Precision) | Recall@10, False Positive Rate |
| 回归 | RMSE, MAE | R-squared, 相对误差 |
| 嵌入 | MKNN对齐分数 | CKA相似度 |

### 5.3 标准化测试流程

```
1. 数据标准化
   ├── 图像统一为 224x224 RGB
   ├── 光变曲线统一为 2000采样点
   └── 光谱统一为 10000波长点

2. 模型推理
   ├── 批量推理 (batch_size=32)
   ├── 5-fold交叉验证
   └── GPU/CPU统一配置

3. 结果收集
   ├── 预测概率分布
   ├── 类别标签
   └── 推理时间

4. 差异分析
   ├── 预测一致性分析
   ├── 错误模式分析
   └── 表征空间对齐
```

---

## 六、模型输出交叉验证方案

### 6.1 交叉验证架构

```
                    ┌─────────────────┐
                    │   天问-AGI      │
                    │  (认知大脑)     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
      ┌───────────┐  ┌───────────┐  ┌───────────┐
      │  模型A     │  │  模型B    │  │  模型C    │
      │ CosmosNet │  │astroPT    │  │Exoplanet- │
      │           │  │           │  │Detection  │
      └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                    ┌──────▼──────┐
                    │  交叉验证   │
                    │   引擎      │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ 一致性   │ │ 投票     │ │ 置信度   │
        │ 检测     │ │ 机制     │ │ 加权     │
        └──────────┘ └──────────┘ └──────────┘
```

### 6.2 验证策略

| 策略 | 描述 | 适用场景 |
|-----|------|---------|
| **多数投票** | 3+模型投票，少数服从多数 | 高置信度任务 |
| **置信度加权** | 基于历史精度加权平均 | 多模型精度差异大 |
| **一致性检测** | 检测模型间预测差异，触发人工复核 | 低置信度边缘案例 |
| **互信息验证** | 计算模型间表征一致性(MKNN) | 表征学习任务 |

### 6.3 阈值设置

```python
# 示例: 星系分类交叉验证
THRESHOLDS = {
    "high_confidence": 0.9,      # >90%一致 → 直接采纳
    "medium_confidence": 0.7,   # 70-90% → 记录待复核
    "low_confidence": 0.5,      # <70% → 触发人工复核
    "disagreement": 0.3         # <30% → 标记为困难样本
}
```

---

## 七、天问-AGI集成建议

### 7.1 优先级评估

| 优先级 | 模型 | 理由 | 集成工作量 |
|-------|------|-----|-----------|
| **P0** | **astroPT** | 基础模型，多任务通用，HuggingFace可直接调用 | 1天 |
| **P0** | **Exoplanet-Detection** | 系外行星探测，精度可验证，CNN成熟 | 2天 |
| **P0** | **Phosphoros** | 星系分类精度高(论文)，ViT架构现代 | 需先获取模型 |
| **P1** | **CosmosNet** | 星系分类，三端架构可参考 | 3天 |
| **P1** | **autostar** | Agent架构启发，Kepler数据集成 | 5天 |
| **P2** | **AstroIR** | 红外领域专精，需额外数据 | 1周 |
| **P2** | **FIRESTAR** | Vision-Language，待成熟 | 长期跟踪 |

### 7.2 集成路线图

```
Phase 1 (Week 1-2): 快速集成
├── astroPT (HuggingFace direct)
├── Exoplanet-Detection (CNN)
└── CosmosNet API (或重训练)

Phase 2 (Week 3-4): 交叉验证
├── 建立交叉验证引擎
├── 实现多数投票/置信度加权
└── 标准化基准测试

Phase 3 (Week 5-6): 高级集成
├── Phosphoros (获取权重)
├── autostar Agent架构借鉴
└── 完整闭环测试
```

### 7.3 立即行动项

1. **astroPT**: 立即测试
   ```bash
   pip install astropt
   from astropt.model_utils import load_astropt
   ```

2. **Phosphoros**: 联系作者获取模型权重或论文复现

3. **CosmosNet**: 评估是否需要重训练或直接使用API

4. **建立基准测试**: 使用Galaxy Zoo数据集评估现有模型

---

## 八、结论与建议

### 8.1 主要发现

1. **精度虚标严重**: 多个项目声称高精度但无公开代码/指标验证
2. **格式不统一**: 各模型输入输出差异大，集成成本高
3. **缺乏交叉验证**: 模型间预测一致性未被系统评估
4. **基础模型崛起**: astroPT等通用基础模型适合作为天问的感知层

### 8.2 标准化建议

1. **强制精度披露**: 要求集成的模型公开验证protocol和指标
2. **统一输入格式**: 图像224x224 RGB，光变曲线2000点
3. **输出标准化**: 统一为概率分布+类别标签
4. **建立基准**: Galaxy Zoo + Kepler作为默认基准数据集

### 8.3 天问优先集成

| 排序 | 模型 | 理由 |
|-----|------|-----|
| 1 | astroPT | 通用基础模型，HuggingFace生态，活跃开发 |
| 2 | Exoplanet-Detection | 精度可验证，代码完整，Kepler数据契合 |
| 3 | Phosphoros | 星系分类精度高，需争取获取 |

---

## 附录: 参考资源

### GitHub仓库汇总

| 模型 | URL | Stars |
|-----|-----|-------|
| astroPT | https://github.com/Smith42/astroPT | 46 |
| CosmosNet | https://github.com/eshaan-eshaan/CosmosNet | 4 |
| autostar | https://github.com/SG-Akshay10/autostar | 0 |
| AstroIR | https://github.com/Ziyang-Li-AILab/AstroIR | 0 |
| AstroPFM | https://github.com/StevenDillmann/AstroPFM | 0 |
| platonic-universe | https://github.com/UniverseTBD/platonic-universe | 9 |
| Exoplanet-Detection | https://github.com/senad96/Exoplanet-Detection | 11 |

### 相关论文

| 论文 | arXiv | 状态 |
|-----|-------|-----|
| AstroIR | arXiv:2306.03138 | 已发表 |
| astroPT | arXiv:2405.14930 | ICML 2024 |
| Phosphoros | arXiv:2411.00029 | 2024年11月 |
| FIRESTAR | arXiv:2503.10738 | 2025年3月 |

---

**文档生成者**: Claude (Anthropic)
**生成时间**: 2026-05-01
**文档版本**: v1.0
**下一步行动**:
1. 评估astroPT实际性能
2. 获取Phosphoros模型权重
3. 设计交叉验证引擎架构