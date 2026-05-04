"""
天问-AGI 天体检测管道
AstroPipeline - 三阶段天体检测与分类管道

Stage I:   photutils源检测 (DAOStarFinder)
Stage II:  ResNet-50分类 (STAR/GALAXY/QSO)
Stage III: YOLOv11s检测 (nebula/globular_cluster/comet/galaxy)

Author: 天问-AGI
"""

from __future__ import annotations

import asyncio
import base64
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math
import json

if TYPE_CHECKING:
    import torch

# 尝试导入图像处理库
try:
    import numpy as np
    from astropy.stats import sigma_clipped_stats
    from photutils.detection import DAOStarFinder
    HAS_ASTROLIBS = True
except ImportError:
    HAS_ASTROLIBS = False

try:
    import cv2
    from PIL import Image
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# ============ 类型定义 ============

class SourceType(Enum):
    """源类型枚举"""
    STAR = "STAR"
    GALAXY = "GALAXY"
    QSO = "QSO"
    UNKNOWN = None


class DetectionClass(Enum):
    """检测类别枚举 (YOLOv11)"""
    NEBULA = "nebula"
    GLOBULAR_CLUSTER = "globular_cluster"
    COMET = "comet"
    GALAXY = "galaxy"


# ============ 数据模型 ============

@dataclass
class SourceDetection:
    """Stage I 检测到的单个源"""
    x: float          # X坐标 (质心)
    y: float          # Y坐标 (质心)
    flux: float       # 流量
    sharpness: float  # 清晰度 (判断点源的重要指标)
    roundness: float  # 圆度 (区分点源和延展源)
    peak: float       # 峰值强度


@dataclass
class ClassifiedSource:
    """Stage II 分类后的源"""
    x: float
    y: float
    flux: float
    source_type: Optional[str]  # STAR/GALAXY/QSO/None
    confidence: float = 0.0


@dataclass
class ObjectDetection:
    """Stage III 检测到的目标"""
    class_name: str
    bbox: Tuple[float, float, float, float]  # [x1, y1, x2, y2]
    confidence: float


@dataclass
class PipelineResult:
    """管道最终输出结果"""
    sources: List[Dict[str, Any]]      # Stage I+II 源列表
    detections: List[Dict[str, Any]]    # Stage III 检测列表
    summary: Dict[str, Any]             # 统计摘要

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "sources": self.sources,
            "detections": self.detections,
            "summary": self.summary
        }


# ============ Stage I: photutils源检测 ============

class StageIDetector:
    """
    Stage I: 使用photutils进行源检测

    使用DAOStarFinder检测点源，特点：
    - σ-clipped背景估算，消除 outliers
    - Gaussian PSF匹配滤波器 (FWHM=3.0px)
    - 检测阈值 τ = η·σ_bg (η=4.0)

    输出包括：质心坐标(xcentroid, ycentroid)、流量、清晰度、圆度
    """

    def __init__(
        self,
        fwhm: float = 3.0,      # Gaussian PSF 半高全宽 (像素)
        threshold_factor: float = 4.0,  # η 值，检测阈值倍数
        min_separation: float = 3.0    # 最小源间距 (像素)
    ):
        self.fwhm = fwhm
        self.threshold_factor = threshold_factor
        self.min_separation = min_separation

    async def detect(self, image_data: np.ndarray) -> List[SourceDetection]:
        """
        在图像中检测点源

        Args:
            image_data: 2D numpy数组，图像数据

        Returns:
            检测到的源列表
        """
        if not HAS_ASTROLIBS:
            # 如果没有astropy库，返回模拟结果用于测试
            return self._mock_detect(image_data)

        # Step 1: 计算σ-clipped背景统计
        # 使用sigma_clip消除亮源和噪声outliers的影响
        mean, median, std = sigma_clipped_stats(
            image_data,
            sigma=3.0,       # 3σ clipping
            maxiters=5       # 最多迭代5次
        )

        # Step 2: 设置检测阈值
        # τ = η · σ_bg，其中η=4.0, σ_bg是背景标准差
        threshold = self.threshold_factor * std

        # Step 3: 创建DAOStarFinder
        # DAOStarFinder使用差分成像检测源，寻找CNTRD和CROWDED的值
        daofind = DAOStarFinder(
            threshold=threshold,
            fwhm=self.fwhm,
            min_separation=self.min_separation,
            roundlo=-np.inf,   # 允许任意圆度
            roundhi=np.inf,
            sharplo=0.2,       # 清晰度下限 (排除宇宙线)
            sharphi=2.0,       # 清晰度上限 (排除延展源)
            flux葡布=[-1e10, 1e10],  # 流量范围
            brightest=None,   # 保留所有检测
            peakmax=None       # 峰值上限
        )

        # Step 4: 执行源检测
        sources = daofind(image_data - median)  # 减去背景中值

        if sources is None:
            return []

        # Step 5: 转换为内部格式
        detections = []
        for src in sources:
            detections.append(SourceDetection(
                x=float(src['xcentroid']),
                y=float(src['ycentroid']),
                flux=float(src['flux']),
                sharpness=float(src['sharpness']),
                roundness=float(src['roundness1']),  # 或 roundness2
                peak=float(src['peak'])
            ))

        return detections

    def _mock_detect(self, image_data: np.ndarray) -> List[SourceDetection]:
        """
        模拟检测 (当没有安装astropy时用于测试)
        """
        # 简单峰值检测作为mock
        detections = []
        h, w = image_data.shape[:2]

        # 在几个随机位置创建模拟检测
        import random
        random.seed(42)

        for i in range(min(5, int(np.max(image_data) / 100))):
            x = random.uniform(w * 0.2, w * 0.8)
            y = random.uniform(h * 0.2, h * 0.8)
            detections.append(SourceDetection(
                x=x, y=y,
                flux=random.uniform(100, 10000),
                sharpness=random.uniform(0.5, 1.5),
                roundness=random.uniform(0.8, 1.2),
                peak=random.uniform(500, 5000)
            ))

        return detections


# ============ Stage II: ResNet-50分类 ============

class StageIIClassifier:
    """
    Stage II: 使用ResNet-50对检测到的源进行分类

    输入：Stage I检测到的每个点源的32×32px裁剪图像
    分类：STAR (恒星) / GALAXY (星系) / QSO (类星体)

    注意：此为框架代码，需要加载预训练权重才能实际运行
    权重路径: models/resnet50_astro_classifier.pth
    """

    def __init__(self, weights_path: str = "models/resnet50_astro_classifier.pth"):
        self.weights_path = weights_path
        self.model = None
        self.device = "cuda" if HAS_CV2 and len(cv2.cuda.getCudaEnabledDeviceCount()) > 0 else "cpu"
        self.input_size = (32, 32)  # 输入图像尺寸
        self.num_classes = 3  # STAR, GALAXY, QSO
        self.class_names = ["STAR", "GALAXY", "QSO"]

    async def load_model(self):
        """
        加载ResNet-50模型权重

        注意：需要预训练权重文件 models/resnet50_astro_classifier.pth
        该权重应基于AstroNet或类似天体分类数据集训练
        """
        # 框架代码 - 实际加载需要torch和预训练权重
        #
        # import torch
        # import torchvision.models as models
        #
        # self.model = models.resnet50(pretrained=False, num_classes=self.num_classes)
        # self.model.load_state_dict(torch.load(self.weights_path, map_location=self.device))
        # self.model.to(self.device)
        # self.model.eval()

    async def classify_sources(
        self,
        image_data: np.ndarray,
        sources: List[SourceDetection]
    ) -> List[ClassifiedSource]:
        """
        对检测到的源进行分类

        Args:
            image_data: 原始图像数据
            sources: Stage I检测到的源列表

        Returns:
            分类后的源列表
        """
        if not sources:
            return []

        # 如果模型未加载或无astropy库，使用模拟分类
        if self.model is None or not HAS_ASTROLIBS:
            return self._mock_classify(sources)

        classified = []

        for src in sources:
            # 提取32x32裁剪图像
            crop = self._extract_crop(image_data, src.x, src.y, size=32)

            if crop is None:
                classified.append(ClassifiedSource(
                    x=src.x, y=src.y, flux=src.flux,
                    source_type=None, confidence=0.0
                ))
                continue

            # 预处理并推理
            # 框架代码：
            # with torch.no_grad():
            #     input_tensor = self._preprocess(crop)
            #     output = self.model(input_tensor)
            #     probs = torch.softmax(output, dim=1)
            #     pred_class = torch.argmax(probs).item()
            #     confidence = probs[0, pred_class].item()

            # 临时使用基于清晰度的启发式分类
            source_type, confidence = self._heuristic_classify(src)

            classified.append(ClassifiedSource(
                x=src.x, y=src.y, flux=src.flux,
                source_type=source_type, confidence=confidence
            ))

        return classified

    def _extract_crop(
        self,
        image_data: np.ndarray,
        x: float, y: float,
        size: int = 32
    ) -> Optional[np.ndarray]:
        """从图像中提取以(x,y)为中心的裁剪区域"""
        h, w = image_data.shape[:2]
        half = size // 2

        x1 = max(0, int(x) - half)
        y1 = max(0, int(y) - half)
        x2 = min(w, int(x) + half)
        y2 = min(h, int(y) + half)

        if x2 <= x1 or y2 <= y1:
            return None

        crop = image_data[y1:y2, x1:x2]

        # 填充到正方形
        if crop.shape[0] != size or crop.shape[1] != size:
            padded = np.zeros((size, size), dtype=crop.dtype)
            y_offset = (size - crop.shape[0]) // 2
            x_offset = (size - crop.shape[1]) // 2
            padded[y_offset:y_offset+crop.shape[0], x_offset:x_offset+crop.shape[1]] = crop
            return padded

        return crop

    def _preprocess(self, crop: np.ndarray) -> "torch.Tensor":
        """
        图像预处理

        注意：需要torch库
        """
        # 框架代码
        # import torch
        # from torchvision import transforms
        #
        # transform = transforms.Compose([
        #     transforms.ToPILImage(),
        #     transforms.Resize((224, 224)),  # ResNet标准输入尺寸
        #     transforms.ToTensor(),
        #     transforms.Normalize(mean=[0.485, 0.456, 0.406],
        #                          std=[0.229, 0.224, 0.225])
        # ])
        # return transform(crop).unsqueeze(0)

    def _heuristic_classify(
        self,
        src: SourceDetection
    ) -> Tuple[Optional[str], float]:
        """
        基于清晰度和圆度的启发式分类

        用于无权重时的测试
        - 高清晰度 + 高圆度 -> STAR
        - 低清晰度 + 低圆度 -> GALAXY
        - 介于两者之间 -> QSO
        """
        # 清晰度：恒星有最高的清晰度(接近Gaussian PSF)
        # 圆度：恒星是圆形的， 星系是椭圆的
        score = src.sharpness * 0.7 + (1 - abs(src.roundness - 1)) * 0.3

        if score > 1.2:
            return "STAR", min(0.95, 0.7 + score * 0.2)
        elif score < 0.8:
            return "GALAXY", min(0.90, 0.6 + score * 0.3)
        else:
            return "QSO", min(0.85, 0.5 + score * 0.3)

    def _mock_classify(
        self,
        sources: List[SourceDetection]
    ) -> List[ClassifiedSource]:
        """模拟分类结果"""
        import random
        random.seed(42)

        results = []
        for src in sources:
            # 随机分配类型用于测试
            r = random.random()
            if r < 0.5:
                source_type = "STAR"
                confidence = random.uniform(0.7, 0.95)
            elif r < 0.8:
                source_type = "GALAXY"
                confidence = random.uniform(0.6, 0.90)
            else:
                source_type = "QSO"
                confidence = random.uniform(0.5, 0.85)

            results.append(ClassifiedSource(
                x=src.x, y=src.y, flux=src.flux,
                source_type=source_type, confidence=confidence
            ))

        return results


# ============ Stage III: YOLOv11s检测 ============

class StageIIIDetector:
    """
    Stage III: 使用YOLOv11s进行扩展目标检测

    输入：全分辨率原始图像
    检测类别：nebula (星云) / globular_cluster (球状星团) /
              comet (彗星) / galaxy (星系)

    注意：此为框架代码，需要加载预训练权重才能实际运行
    权重路径: models/yolo11s_astro_detection.pt
    """

    def __init__(self, weights_path: str = "models/yolo11s_astro_detection.pt"):
        self.weights_path = weights_path
        self.model = None
        self.confidence_threshold = 0.25
        self.iou_threshold = 0.45
        self.class_names = ["nebula", "globular_cluster", "comet", "galaxy"]

    async def load_model(self):
        """
        加载YOLOv11s模型

        注意：需要ultralytics库和预训练权重
        权重应基于扩展天体目标检测数据集训练
        """
        # 框架代码 - 实际加载需要ultralytics
        #
        # from ultralytics import YOLO
        #
        # self.model = YOLO(self.weights_path)
        # self.model.conf = self.confidence_threshold
        # self.model.iou = self.iou_threshold

    async def detect(self, image_data: np.ndarray) -> List[ObjectDetection]:
        """
        在全分辨率图像上检测扩展目标

        Args:
            image_data: 原始图像数据

        Returns:
            检测到的目标列表
        """
        # 如果模型未加载或无CV2，使用模拟检测
        if self.model is None or not HAS_CV2:
            return self._mock_detect(image_data)

        # 实际检测 (框架代码)
        # results = self.model(image_data)
        #
        # detections = []
        # for result in results:
        #     boxes = result.boxes
        #     for box in boxes:
        #         x1, y1, x2, y2 = box.xyxy[0].tolist()
        #         conf = float(box.conf[0])
        #         cls_id = int(box.cls[0])
        #         cls_name = self.class_names[cls_id]
        #
        #         detections.append(ObjectDetection(
        #             class_name=cls_name,
        #             bbox=(x1, y1, x2, y2),
        #             confidence=conf
        #         ))
        #
        # return detections

    def _mock_detect(self, image_data: np.ndarray) -> List[ObjectDetection]:
        """
        模拟检测结果 (用于无权重时测试)
        """
        import random
        random.seed(123)

        h, w = image_data.shape[:2]
        detections = []

        # 随机生成1-3个检测
        num_detections = random.randint(1, 3)

        for _ in range(num_detections):
            # 随机类别
            cls_name = random.choice(self.class_names)

            # 随机边界框
            x1 = random.uniform(w * 0.1, w * 0.3)
            y1 = random.uniform(h * 0.1, h * 0.3)
            x2 = random.uniform(w * 0.5, w * 0.7)
            y2 = random.uniform(h * 0.5, h * 0.7)

            # 确保x2 > x1, y2 > y1
            if x2 <= x1:
                x1, x2 = x2, x1
            if y2 <= y1:
                y1, y2 = y2, y1

            detections.append(ObjectDetection(
                class_name=cls_name,
                bbox=(x1, y1, x2, y2),
                confidence=random.uniform(0.6, 0.95)
            ))

        return detections


# ============ 主管道类 ============

class AstroPipeline:
    """
    天体检测三阶段管道

    Stage I:   photutils源检测 (DAOStarFinder)
               -> 检测点源并提取质心、流量等参数

    Stage II:  ResNet-50分类
               -> 对Stage I检测的每个源进行STAR/GALAXY/QSO分类

    Stage III: YOLOv11s检测
               -> 在全图检测扩展目标 (星云、球状星团、彗星、星系)

    输出格式:
    {
        "sources": [{"x": float, "y": float, "flux": float, "type": "STAR"|"GALAXY"|"QSO"|None}],
        "detections": [{"class": str, "bbox": [x1,y1,x2,y2], "confidence": float}],
        "summary": {"total_sources": int, "galaxies": int, "stars": int, "qsos": int}
    }
    """

    def __init__(self):
        self.stage1_detector = StageIDetector()
        self.stage2_classifier = StageIIClassifier(weights_path="runtime/models/resnet50_astro_classifier.pth")
        self.stage3_detector = StageIIIDetector(weights_path="runtime/models/yolo11s_astro_detection.pt")
        self._load_models()

    def _load_models(self):
        """加载模型权重"""
        import os

        resnet_path = self.stage2_classifier.weights_path
        yolo_path = self.stage3_detector.weights_path

        # 尝试加载ResNet-50
        if os.path.exists(resnet_path):
            try:
                import torch
                self.stage2_classifier.model = torch.load(resnet_path, map_location='cpu')
                print(f"ResNet-50权重加载成功: {resnet_path}")
            except Exception as e:
                print(f"ResNet-50权重加载失败，使用模拟模式: {e}")
                self.stage2_classifier.model = None
        else:
            print(f"ResNet-50权重文件不存在: {resnet_path}")
            self.stage2_classifier.model = None

        # 尝试加载YOLOv11s
        if os.path.exists(yolo_path):
            try:
                from ultralytics import YOLO
                self.stage3_detector.model = YOLO(yolo_path)
                print(f"YOLOv11s权重加载成功: {yolo_path}")
            except Exception as e:
                print(f"YOLOv11s权重加载失败，使用模拟模式: {e}")
                self.stage3_detector.model = None
        else:
            print(f"YOLOv11s权重文件不存在: {yolo_path}")
            self.stage3_detector.model = None

    async def initialize(self):
        """初始化管道，加载模型权重"""
        # Stage II & III 需要加载权重
        await self.stage2_classifier.load_model()
        await self.stage3_detector.load_model()

    async def process(
        self,
        image_input: Union[str, bytes, np.ndarray],
        return_images: bool = False
    ) -> Dict[str, Any]:
        """
        处理天文图像

        Args:
            image_input: 图像输入，可以是：
                        - 文件路径 (str): 图像文件路径
                        - Base64字符串 (str): base64编码的图像数据
                        - 原始字节 (bytes): 图像原始数据
                        - numpy数组: 直接的图像数组
            return_images: 是否返回处理后的图像数据

        Returns:
            管道处理结果字典
        """
        # Step 1: 加载/解析图像
        image_data = await self._load_image(image_input)

        if image_data is None:
            return self._empty_result()

        # Step 2: Stage I - 源检测
        stage1_sources = await self.stage1_detector.detect(image_data)

        # Step 3: Stage II - 源分类
        stage2_classified = await self.stage2_classifier.classify_sources(
            image_data, stage1_sources
        )

        # Step 4: Stage III - 扩展目标检测
        stage3_detections = await self.stage3_detector.detect(image_data)

        # Step 5: 构建输出结果
        return self._build_result(stage2_classified, stage3_detections)

    async def _load_image(
        self,
        image_input: Union[str, bytes, np.ndarray]
    ) -> Optional[np.ndarray]:
        """
        加载图像数据

        支持多种输入格式：
        - 文件路径
        - Base64编码
        - 原始字节
        - numpy数组
        """
        if isinstance(image_input, np.ndarray):
            return image_input

        if isinstance(image_input, str):
            # 判断是Base64还是文件路径
            if len(image_input) > 200 and ',' not in image_input:
                # 可能是Base64
                try:
                    return self._decode_base64_image(image_input)
                except Exception:
                    pass

            # 尝试作为文件路径
            path = Path(image_input)
            if path.exists():
                return self._load_image_file(path)

        if isinstance(image_input, bytes):
            return self._decode_bytes_image(image_input)

        return None

    def _load_image_file(self, path: Path) -> Optional[np.ndarray]:
        """从文件加载图像"""
        try:
            if not HAS_CV2:
                # 使用PIL作为后备
                img = Image.open(path)
                return np.array(img)
            else:
                # 使用OpenCV
                img = cv2.imread(str(path))
                if img is not None:
                    # BGR转RGB
                    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except Exception as e:
            print(f"Error loading image from {path}: {e}")

        return None

    def _decode_base64_image(self, b64_str: str) -> Optional[np.ndarray]:
        """解码Base64图像"""
        try:
            # 移除可能的data URI前缀
            if ',' in b64_str:
                b64_str = b64_str.split(',')[1]

            image_data = base64.b64decode(b64_str)
            return self._decode_bytes_image(image_data)
        except Exception as e:
            print(f"Error decoding base64 image: {e}")
            return None

    def _decode_bytes_image(self, image_data: bytes) -> Optional[np.ndarray]:
        """从字节数据解码图像"""
        try:
            if not HAS_CV2:
                img = Image.open(io.BytesIO(image_data))
                return np.array(img)
            else:
                img_array = np.frombuffer(image_data, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is not None:
                    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except Exception as e:
            print(f"Error decoding image bytes: {e}")

        return None

    def _build_result(
        self,
        classified_sources: List[ClassifiedSource],
        detections: List[ObjectDetection]
    ) -> Dict[str, Any]:
        """构建最终输出结果"""
        # 格式化源列表
        sources_list = []
        stars = galaxies = qsos = 0

        for src in classified_sources:
            src_dict = {
                "x": round(src.x, 2),
                "y": round(src.y, 2),
                "flux": round(src.flux, 2),
                "type": src.source_type
            }
            sources_list.append(src_dict)

            # 统计计数
            if src.source_type == "STAR":
                stars += 1
            elif src.source_type == "GALAXY":
                galaxies += 1
            elif src.source_type == "QSO":
                qsos += 1

        # 格式化检测列表
        detections_list = []
        for det in detections:
            detections_list.append({
                "class": det.class_name,
                "bbox": [round(x, 2) for x in det.bbox],
                "confidence": round(det.confidence, 4)
            })

        # 构建摘要
        summary = {
            "total_sources": len(sources_list),
            "stars": stars,
            "galaxies": galaxies,
            "qsos": qsos,
            "extended_objects": len(detections_list)
        }

        return {
            "sources": sources_list,
            "detections": detections_list,
            "summary": summary
        }

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            "sources": [],
            "detections": [],
            "summary": {
                "total_sources": 0,
                "stars": 0,
                "galaxies": 0,
                "qsos": 0,
                "extended_objects": 0
            }
        }


# ============ 异步接口封装 ============

async def process_astro_image(
    image_input: Union[str, bytes, np.ndarray],
    initialize_models: bool = False
) -> Dict[str, Any]:
    """
    异步处理天文图像的便捷函数

    Args:
        image_input: 图像输入 (文件路径/Base64/字节/数组)
        initialize_models: 是否初始化模型权重

    Returns:
        处理结果字典
    """
    pipeline = AstroPipeline()

    if initialize_models:
        await pipeline.initialize()

    return await pipeline.process(image_input)


# ============ 模拟数据测试 ============

async def test_with_mock_data():
    """
    使用模拟数据测试管道流程

    生成一个模拟的天文图像，包含：
    - 随机分布的点源 (模拟STAR)
    - 一些模糊的延展区域 (模拟GALAXY/NEBULA)
    """
    print("=" * 60)
    print("天体检测管道测试 - 模拟数据")
    print("=" * 60)

    # 创建模拟图像
    h, w = 512, 512
    image_data = np.zeros((h, w), dtype=np.float32)

    # 添加随机背景噪声
    noise = np.random.normal(100, 10, (h, w))
    image_data += noise

    # 添加模拟星点 (明亮的点源)
    np.random.seed(42)
    for _ in range(20):
        x = np.random.randint(50, w - 50)
        y = np.random.randint(50, h - 50)
        flux = np.random.uniform(500, 2000)

        # 创建Gaussian PSF形状的星点
        for dy in range(-10, 11):
            for dx in range(-10, 11):
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= 10:
                    intensity = flux * math.exp(-dist**2 / (2 * 3.0**2))
                    iy, ix = y + dy, x + dx
                    if 0 <= iy < h and 0 <= ix < w:
                        image_data[iy, ix] += intensity

    # 添加模拟延展源 (模拟星系或星云)
    for _ in range(3):
        cx = np.random.randint(100, w - 100)
        cy = np.random.randint(100, h - 100)
        radius = np.random.uniform(30, 60)
        flux = np.random.uniform(2000, 5000)

        for dy in range(-int(radius), int(radius) + 1):
            for dx in range(-int(radius), int(radius) + 1):
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= radius:
                    intensity = flux * (1 - dist/radius) * math.exp(-dist / (radius/2))
                    iy, ix = cy + dy, cx + dx
                    if 0 <= iy < h and 0 <= ix < w:
                        image_data[iy, ix] += intensity

    print(f"\n模拟图像大小: {w}x{h}")
    print(f"图像值范围: [{image_data.min():.1f}, {image_data.max():.1f}]")

    # 创建管道并处理
    pipeline = AstroPipeline()

    print("\n开始处理...")
    start_time = datetime.now()

    # Stage I 检测
    stage1_sources = await pipeline.stage1_detector.detect(image_data)
    print(f"\n[Stage I] 检测到 {len(stage1_sources)} 个点源")

    # Stage II 分类
    stage2_classified = await pipeline.stage2_classifier.classify_sources(
        image_data, stage1_sources
    )
    print("[Stage II] 分类完成")

    # Stage III 检测
    stage3_detections = await pipeline.stage3_detector.detect(image_data)
    print(f"[Stage III] 检测到 {len(stage3_detections)} 个扩展目标")

    # 构建结果
    result = pipeline._build_result(stage2_classified, stage3_detections)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n处理耗时: {elapsed:.3f}秒")

    # 打印结果摘要
    print("\n" + "=" * 60)
    print("处理结果摘要")
    print("=" * 60)

    summary = result["summary"]
    print(f"总源数量: {summary['total_sources']}")
    print(f"  - 恒星 (STAR): {summary['stars']}")
    print(f"  - 星系 (GALAXY): {summary['galaxies']}")
    print(f"  - 类星体 (QSO): {summary['qsos']}")
    print(f"扩展目标: {summary['extended_objects']}")

    print("\n分类源列表:")
    for i, src in enumerate(result["sources"][:5], 1):  # 只显示前5个
        print(f"  {i}. x={src['x']:.1f}, y={src['y']:.1f}, "
              f"flux={src['flux']:.0f}, type={src['type']}")

    if result["detections"]:
        print("\n扩展目标检测:")
        for i, det in enumerate(result["detections"], 1):
            print(f"  {i}. {det['class']} @ {det['bbox']} "
                  f"(conf={det['confidence']:.2f})")

    print("\n" + "=" * 60)
    print("完整JSON输出:")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    return result


async def test_with_base64():
    """测试Base64输入格式"""
    print("\n" + "=" * 60)
    print("测试Base64输入格式")
    print("=" * 60)

    # 创建一个小的测试图像
    test_img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

    # 编码为Base64
    if HAS_CV2:
        # BGR转RGB后编码
        img_rgb = cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB)
        _, buffer = cv2.imencode('.png', img_rgb)
        b64_str = base64.b64encode(buffer).decode('utf-8')
    else:
        from PIL import Image
        img_pil = Image.fromarray(test_img)
        buffer = io.BytesIO()
        img_pil.save(buffer, format='PNG')
        b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

    print(f"Base64字符串长度: {len(b64_str)}")

    # 处理
    pipeline = AstroPipeline()
    result = await pipeline.process(b64_str)

    print(f"处理结果: 检测到 {result['summary']['total_sources']} 个源")
    print(json.dumps(result, indent=2))

    return result


# ============ 主入口 ============

if __name__ == "__main__":
    print("天体检测管道 - 测试运行")
    print("=" * 60)

    # 检查依赖
    print("\n依赖检查:")
    print(f"  numpy: {HAS_ASTROLIBS or '模拟模式'}")
    print(f"  astropy/photutils: {HAS_ASTROLIBS}")
    print(f"  cv2: {HAS_CV2}")

    # 运行测试
    asyncio.run(test_with_mock_data())

    # 如果有cv2，测试Base64
    if HAS_CV2:
        asyncio.run(test_with_base64())

    print("\n测试完成!")
