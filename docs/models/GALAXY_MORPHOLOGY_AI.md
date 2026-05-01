# 星系形态分类AI模型对比分析报告

## 1. 研究概述

星系形态分类是天体物理学研究中的关键任务，传统上依赖天文学家的人工目视分类。随着深度学习技术的发展，基于卷积神经网络(CNN)和视觉Transformer(ViT)的自动化分类方法取得了显著进展。

## 2. GitHub开源项目分析

### 2.1 按星标排序的主要项目

| 项目名 | 作者 | 架构 | 数据集 | 精度 | Stars | License | 代码 | 预训练模型 |
|--------|------|------|--------|------|-------|---------|------|-----------|
| Zoobot | mwalmsley | Bayesian CNN (ResNet) | Galaxy Zoo | ~90% | 123 | GPL-3.0 | Yes | Yes |
| pymorph | vvinuv | 参数估计模型 | 多种星系图像 | N/A | 13 | GPL-2.0 | Yes | No |
| GaMPEN | aritraghsh09 | CNN + Bayesian | Galaxy Zoo | 估计形态参数 | 12 | GPL-3.0 | Yes | No |
| Galaxy-Morphology-CapsNet | RezaKatebi | Capsule Networks | Galaxy Zoo | N/A | 11 | None | Yes | No |
| CosmosNet | eshaan-eshaan | ResNet-18 + EfficientNet-B0 | 120,000 Hubble图像 | N/A | 4 | None | Yes | No |
| LeadingIndiaAI/Galaxy-classifier | LeadingIndiaAI | 自定义CNN (16 filters) | 3,232图像 | 97.38% | 4 | MIT | Yes | No |
| GalacticFlow | luwo9 | Normalizing Flows | Galaxy Zoo | N/A | 6 | MIT | Yes | No |
| galaxy_morphology_mcp | weinaike | MCP Server工具 | Galaxy Zoo | N/A | 4 | None | Yes | No |
| GalaxyEfficientNets | obi-wan-shinobi | EfficientNet | Galaxy Zoo | N/A | 8 | None | Yes | No |
| Galaxy-Morphology-Classification | Deepi-boobi02 | VGG16/ResNet50/EfficientNetB0 | Galaxy Zoo 2 | N/A | 0 | None | Yes | No |
| galaxy-morphology-classification | NethumDinusara | 自定义CNN (5类) | 高维天文图像 | 82% | 0 | None | Yes | No |
| ResNet34-Based-... | priyanisabde15 | ResNet34 + Machine Unlearning | Galaxy Zoo | N/A | 2 | MIT | Yes | No |
| galaxyCNN | klaykulik | CNN | Galaxy Zoo | N/A | 3 | None | Yes | No |

### 2.2 重点项目详细分析

#### Zoobot (mwalmsley/zoobot) - 最受欢迎项目
- **架构**: Bayesian CNN (基于ResNet)
- **数据集**: Galaxy Zoo (综合)
- **特性**:
  - 提供不确定性估计
  - 支持迁移学习
  - 完整的训练/推理流程
- **许可**: GPL-3.0
- **链接**: https://github.com/mwalmsley/zoobot

#### CosmosNet (eshaan-eshaan/CosmosNet)
- **架构**: ResNet-18 + EfficientNet-B0 (双模型)
- **数据集**: 120,000 Hubble太空望远镜图像
- **技术栈**: PyTorch + FastAPI + React
- **描述**: Galaxy morphology classification using ResNet-18 and EfficientNet-B0 on 120,000 Hubble images
- **链接**: https://github.com/eshaan-eshaan/CosmosNet

#### LeadingIndiaAI/Galaxy-classifier
- **架构**: 自定义CNN (16 filters, 3 hidden layers)
- **数据集**: 3,232星系图像
- **分类**: Elliptical, Spiral, Irregular (3类)
- **精度**: 测试集准确率97.38%
- **许可**: MIT
- **链接**: https://github.com/LeadingIndiaAI/Galaxy-classifier

#### GaMPEN (aritraghsh09/GaMPEN)
- **架构**: CNN + Spatial Transformer Networks
- **功能**: 估计星系形态参数的贝叶斯后验分布
- **主题**: astrophysics, deep-neural-networks, galaxy-morphology, pytorch, uncertainty-neural-networks
- **链接**: http://gampen.ghosharitra.com/

#### GalacticFlow (luwo9/GalacticFlow)
- **架构**: Conditional Normalizing Flows
- **方法**: 生成式模型用于星系形态建模
- **许可**: MIT
- **链接**: https://github.com/luwo9/GalacticFlow

## 3. 学术论文模型

### 3.1 CosmosNet (eshaan-eshaan)
- **架构**: ResNet-18 + EfficientNet-B0
- **数据**: 12万张Hubble图像
- **代码**: https://github.com/eshaan-eshaan/CosmosNet

### 3.2 Phosphoros (arXiv:2411.00029)
- **架构**: Vision Transformer (ViT)
- **预训练数据**: 2000万+星系图像
- **特点**: 大规模预训练视觉Transformer

### 3.3 FIRESTAR (arXiv:2503.10738)
- **架构**: Vision-Language Foundation Model
- **应用**: Galaxy Survey星系巡天
- **特点**: 多模态视觉-语言模型

### 3.4 JWST AI + Vision Transformer
- **精度**: 94%星系分类准确率
- **数据源**: James Webb Space Telescope (JWST)图像

## 4. Galaxy Zoo 数据集相关资源

Galaxy Zoo是星系形态分类最重要的标注数据集，多个开源项目基于此数据集:

| 项目 | 架构 | 特点 |
|------|------|------|
| Zoobot | Bayesian CNN | 不确定性估计，迁移学习 |
| Deepi-boobi02 | VGG16/ResNet50/EfficientNetB0 | 多种架构对比 |
| GaMPEN | CNN + Bayesian | 形态参数估计 |
| GalacticFlow | Normalizing Flows | 生成式方法 |

## 5. 技术架构分析

### 5.1 CNN架构趋势
- **ResNet系列**: 广泛使用， Zoobot采用
- **EfficientNet**: 高效性， CosmosNet和GalaxyEfficientNets采用
- **VGG**: 基础对比模型
- **Capsule Networks**: 空间层次特征学习

### 5.2 新兴架构
- **Vision Transformer (ViT)**: Phosphoros采用，2000万+图像预训练
- **Bayesian CNN**: Zoobot采用，提供不确定性估计
- **Normalizing Flows**: GalacticFlow采用，生成式方法

## 6. 精度对比

| 模型 | 精度 | 条件 |
|------|------|------|
| LeadingIndiaAI/Galaxy-classifier | 97.38% | 3类(椭圆/螺旋/不规则), 3232图像 |
| galaxy-morphology-classification (NethumDinusara) | 82% | 5类, 自定义CNN |
| Zoobot | ~90% | Galaxy Zoo综合分类 |

## 7. 代码与预训练模型可用性

| 分类 | 项目数 | 占比 |
|------|--------|------|
| 有代码 | 13 | 100% |
| 有预训练模型 | 1 (Zoobot) | ~8% |
| 明确许可 | 8 | ~62% |

## 8. 关键发现

1. **Zoobot** 是最成熟的开源项目，提供完整训练流程和预训练模型
2. **CosmosNet** 专门针对Hubble图像，集成了FastAPI和React
3. **Vision Transformer** 架构(Phosphoros)在大规模预训练中表现突出
4. **Bayesian方法** 开始应用于提供不确定性估计
5. **预训练模型可用性较低**，多数项目需要从头训练

## 9. 推荐项目

- **最佳完整解决方案**: Zoobot (mwalmsley/zoobot)
- **Hubble图像专用**: CosmosNet (eshaan-eshaan/CosmosNet)
- **最高精度报告**: LeadingIndiaAI/Galaxy-classifier (97.38%)
- **不确定性估计**: GaMPEN + Zoobot

## 10. 数据来源

- GitHub搜索: `gh search repos "galaxy morphology classification" --limit 20`
- GitHub API: repos信息获取
- 搜索时间: 2026-05-01

## 附录: 相关链接

- Zoobot: https://github.com/mwalmsley/zoobot
- CosmosNet: https://github.com/eshaan-eshaan/CosmosNet
- GalaxyEfficientNets: https://github.com/obi-wan-shinobi/GalaxyEfficientNets
- GaMPEN: https://github.com/aritraghsh09/GaMPEN
- GalacticFlow: https://github.com/luwo9/GalacticFlow
- pymorph: https://github.com/vvinuv/pymorph