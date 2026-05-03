# AstroPipeline 技能定义

> 技能名称: AstroPipeline
> 技能类型: 天文图像分析管道
> 创建时间: 2026-05-01
> 关联模块: runtime/astro_pipeline.py

---

## 一、技能概述

AstroPipeline是一个三阶段天文图像分析管道，用于自动检测和分类天体（星系、恒星、类星体）。

### 1.1 技能能力

| 阶段 | 能力 | 说明 |
|-----|------|------|
| **Stage I** | 点源检测 | 使用photutils检测图像中的点源 |
| **Stage II** | 天体分类 | 使用ResNet-50将点源分类为STAR/GALAXY/QSO |
| **Stage III** | 扩展目标检测 | 使用YOLOv11s检测星云、星团、彗星、星系 |

### 1.2 输入输出

**输入**:
- 天文图像文件路径 (str)
- Base64编码图像 (str)
- 原始字节数据 (bytes)
- numpy数组 (np.ndarray)

**输出**:
```json
{
    "sources": [
        {"x": 123.5, "y": 456.7, "flux": 0.85, "type": "GALAXY"}
    ],
    "detections": [
        {"class": "nebula", "bbox": [100, 200, 300, 400], "confidence": 0.92}
    ],
    "summary": {
        "total_sources": 15,
        "galaxies": 5,
        "stars": 8,
        "qsos": 2
    }
}
```

---

## 二、技术架构

### 2.1 Stage I: photutils源检测

**算法**: DAOStarFinder

**处理流程**:
1. Sigma-clipped背景估算
2. Gaussian PSF匹配 (FWHM=3.0px)
3. 检测阈值: τ = 4.0 × σ_bg
4. 流量加权质心估算

**输出**: 点源列表 (质心坐标、流量、清晰度、圆度)

### 2.2 Stage II: ResNet-50分类

**输入**: Stage I检测到的每个点源的32×32px裁剪图像

**分类类别**:
- STAR (恒星)
- GALAXY (星系)
- QSO (类星体)

**模型权重**: `runtime/models/resnet50_astro_classifier.pth`

### 2.3 Stage III: YOLOv11s检测

**输入**: 全分辨率原始图像

**检测类别**:
- nebula (星云)
- globular_cluster (球状星团)
- comet (彗星)
- galaxy (星系)

**模型权重**: `runtime/models/yolo11s_astro_detection.pt`

---

## 三、使用方法

### 3.1 基本调用

```python
from astro_pipeline import AstroPipeline, process_astro_image

# 初始化管道
pipeline = AstroPipeline()

# 处理图像
result = await pipeline.analyze("path/to/image.fits")

# 便捷接口
result = await process_astro_image(image_data)
```

### 3.2 天问-AGI技能链调用

```python
from skill_integration import SkillChainExecutor

executor = SkillChainExecutor()
result = await executor.execute_chain(
    skill_names=["astro_pipeline"],
    initial_input={"image": base64_data}
)
```

### 3.3 参数配置

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `sigma` | float | 4.0 | 检测阈值乘数 |
| `conf` | float | 0.25 | YOLO置信度阈值 |
| `fwhm` | float | 3.0 | PSF半高全宽 (像素) |

---

## 四、依赖项

```
photutils >= 1.9.0
torch >= 2.0
ultralytics >= 8.0
numpy >= 1.21
astropy >= 5.0
```

---

## 五、预期效果

| 指标 | 数值 |
|-----|------|
| 点源分类准确率 | 88.15% |
| 扩展目标检测mAP@50 | 72.2% |
| 处理延迟 | ~1-2秒/图像 |

---

## 六、集成状态

| 组件 | 状态 | 文件 |
|-----|------|------|
| 框架代码 | ✅ 已创建 | runtime/astro_pipeline.py |
| 模型权重 | ⏳ 待下载 | runtime/models/ |
| 技能注册 | ⏳ 待完成 | skills/ |

---

## 七、扩展计划

1. **批量处理优化**: 支持多图像批量分析
2. **结果缓存**: 减少重复计算
3. **星表联动**: 与star_recognizer.py的星表数据库结合
4. **时序分析**: 支持光变曲线分析

---

**技能定义者**: Claude (Anthropic)
**定义时间**: 2026-05-01
**版本**: v1.0