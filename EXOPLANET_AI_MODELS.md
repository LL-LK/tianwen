# 系外行星探测AI模型对比分析报告

## 1. 研究背景

系外行星探测是天文信息学的核心课题之一。NASA Kepler太空望远镜自2009年发射以来，收集了数千颗恒星的光变曲线数据，用于探测凌星（transit）信号。传统方法依赖人工筛选假阳性（如食双星、背景污染物），效率低下。近年来，深度学习、Transformer和AI Agent技术被广泛应用于这一领域，显著提升了探测效率和准确率。

---

## 2. 主要模型对比

| 模型 | 机构/作者 | 数据集 | 精度指标 | 架构 | 代码可用性 |
|------|-----------|--------|----------|------|------------|
| **senad96/Exoplanet-Detection** | - | Kepler (Kaggle, 5087样本, 3198维) | CNN: 100%准确率(5/5颗系外行星) | CNN + SVC | 开源 |
| **piyarshah/Kepler-Exoplanet-Detection** | FLAME University | Kepler TPF数据 | KNN+DTW: 95%准确率, F1=0.78; 2D CNN: **99.2%准确率**, AUC=0.97 | 层级KNN+DTW + 2D CNN | 开源 |
| **kbhujbal/NASA_exoplanet_detection_using_CNN_transfromer** | - | Kepler KOI | 5折交叉验证, Focal Loss处理类别不平衡 | CNN-Transformer混合架构 (双尺度CNN分支 + Transformer编码器) | 开源 |
| **savula13/Exoplanet-Detection** | - | TESS | 多视图Transformer (全局+局部相位折叠) | CNN基线 + Supervised Transformer + Semi-supervised | 开源 |
| **loreloc/exoplanet-detection** | - | Kepler KOI | Auto-Tuned Random Forest | Random Forest + Hyperband超参优化 | 开源 |
| **nmscannell/exoplanet-detection** | - | Kepler | 神经网络分类 | 神经网络 | 开源 |
| **SG-Akshay10/autostar** | - | NASA Kepler光变曲线 | AI Agent优化GPT模型 | GPT + AI Agent | 暂无stars |

---

## 3. 详细模型分析

### 3.1 senad96/Exoplanet-Detection (CNN/SVC)

- **技术架构**: 使用高斯滤波(sigma=5)去噪后进行FFT频域转换,CNN和SVC双模型对比
- **数据集**: Kaggle Kepler标记时序数据, 5087颗恒星, 维度3198, 正样本<1%
- **性能**: CNN在测试集100%检测到5颗系外行星; SVC仅正确预测1颗
- **输出**: 二分类(是/否系外行星)
- **语言**: Python

### 3.2 piyarshah/Kepler-Exoplanet-Detection (KNN+DTW / 2D CNN)

- **技术架构**: 
  - 层级KNN + DTW (动态时间规整) 相似性学习
  - 2D CNN处理相位折叠图像
- **数据处理**: 目标像素文件(TPF) -> 背景扣除 -> 平场改正 -> 孔径测光 -> PCA去噪
- **性能**: 
  - KNN+DTW: 95%准确率, F1=0.78
  - 2D CNN: **99.2%准确率**, AUC=0.97
- **数学模型**: 凌星深度公式 $\frac{\Delta F}{F} = (\frac{R_p}{R_s})^2$
- **语言**: Jupyter Notebook

### 3.3 kbhujbal/NASA_exoplanet_detection_using_CNN_transfromer (混合架构)

- **技术架构**: 三分支并行结构
  - Global View CNN: 4层1D CNN, [16,32,64,128], kernel=5
  - Local View CNN: 3层1D CNN, [16,32,64], kernel=3
  - Transformer分支: 4层Transformer编码器, d=64, heads=8, 正弦位置编码
- **损失函数**: Focal Loss (alpha=0.25, gamma=2.0) 应对类别不平衡
- **数据增强**: 循环时间偏移、高斯噪声、通量缩放
- **不确定性量化**: Monte Carlo Dropout
- **可解释性**: Grad-CAM + SHAP + Transformer注意力可视化
- **数据集**: Kepler Exoplanet Search Results (Kaggle)
- **验证方式**: 5折分层交叉验证 + 早停

### 3.4 savula13/Exoplanet-Detection (Transformer多视图)

- **技术架构**: 
  - CNN基线 (全局通量)
  - Supervised Transformer (双视图: 全局+局部相位)
  - Pseudo-Labeled Transformer (半监督)
  - SSL Reconstruction Transformer (自监督预训练+微调)
- **输入**: 相位折叠光变曲线, flux + centroid双通道
- **优势**: 利用未标记数据扩展训练集
- **数据集**: TESS

### 3.5 loreloc/exoplanet-detection (Auto-Tuned Random Forest)

- **技术架构**: Random Forest + Hyperband自动超参优化
- **数据集**: NASA KOI (Kepler Objects of Interest)
- **目标**: 减少假阳性率, 自动判断特征重要性
- **语言**: Python

### 3.6 SG-Akshay10/autostar (AI Agent + GPT)

- **技术描述**: 自主系外行星探测系统, AI Agent优化GPT模型, 基于NASA Kepler光变曲线序列
- **创新点**: 声称可在一夜之间完成GPT训练并发现凌星信号
- **当前状态**: 新项目(2026-03), 无stars

---

## 4. 数据集来源

| 数据集 | 来源 | 描述 |
|--------|------|------|
| Kepler KOI | Kaggle NASA | Kepler目标兴趣对象标记数据 |
| Kepler TPF | MAST档案 | 目标像素文件,需预处理提取光变曲线 |
| TESS | NASA | 更新的系外行星巡天数据 |
| Kepler Labelled Time Series | Kaggle | 5087颗恒星,3198维时序数据 |

---

## 5. 关键发现

### 5.1 架构趋势
1. **混合架构成为主流**: CNN-Transformer组合(如kbhujbal的项目)结合局部特征提取和全局序列建模
2. **多视图学习**: 全局视图(完整轨道相位) + 局部视图(凌星结构) 双分支设计
3. **Transformer应用**: 逐步替代传统RNN/LSTM处理时序光变曲线
4. **AI Agent探索**: autostar项目尝试用AI Agent自动优化GPT模型

### 5.2 类别不平衡处理
- 训练数据正样本普遍<1%
- 解决方案: Focal Loss, SMOTE, 数据增强

### 5.3 可解释性需求
- 注意力可视化(Transformer attention maps)
- Grad-CAM热力图
- SHAP值分析
- Monte Carlo Dropout不确定性量化

### 5.4 缺失项目说明
- **DeepMind Exoplanet AI**: 网传95%准确率项目,但未在GitHub找到对应仓库
- **Cambridge Exoplanet Transformer**: 网传假阳性率<1%项目,未找到对应仓库

---

## 6. 性能对比总结

| 模型 | 准确率 | F1 | AUC | 特殊优势 |
|------|--------|-----|-----|----------|
| senad96 CNN | 100%* | - | - | 频域分析 |
| piyarshah 2D CNN | **99.2%** | - | 0.97 | 光学预处理流程 |
| piyarshah KNN+DTW | 95% | 0.78 | - | 相似性学习 |
| kbhujbal混合 | 5折CV | - | - | 可解释性+不确定性 |
| loreloc RF | - | - | - | AutoML超参优化 |

*注: senad96测试集仅5颗系外行星样本,100%准确率参考意义有限

---

## 7. 建议

1. **高精度场景**: 采用piyarshah的2D CNN或kbhujbal的CNN-Transformer混合架构
2. **可解释性需求**: 选择kbhujbal的项目,支持Grad-CAM/SHAP/注意力可视化
3. **轻量级部署**: loreloc的Auto-Tuned Random Forest,便于生产环境部署
4. **新研究方向**: autostar的AI Agent + GPT方法值得追踪

---

*报告生成时间: 2026/05/01*  
*数据来源: GitHub搜索 + 项目README分析*
