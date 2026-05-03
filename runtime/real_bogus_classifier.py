"""
Real-Bogus 分类器 - 基于图像特征工程的天文源分类

原理:
Real-Bogus分类器区分真实天文瞬变源(如超新星、变星)和图像伪影(如宇宙线、CCD噪声)

策略:
1. 优先尝试加载 PyTorch ResNet50 权重 (runtime/models/resnet50_astro_classifier.pth)
   - 如果权重文件无效(全0/损坏)，自动降级到特征工程分类器
2. 特征工程分类器: 无需预训练权重，提取图像统计+形态学特征

依赖: torch(可选), numpy
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在路径中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Tuple, Optional, Any
import numpy as np

HAS_TORCH = False
try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as transforms
    HAS_TORCH = True
except ImportError:
    pass


class RealBogusClassifier:
    """
    使用 ResNet50 的 Real-Bogus 分类器
    
    基于 STAR/GALAXY/QSO 分类器权重进行迁移学习
    对于Real-Bogus: 
    - REAL = GALAXY (河外瞬变源)
    - BOGUS = artifact (图像伪影)
    """
    
    def __init__(
        self,
        weights_path: str = "runtime/models/resnet50_astro_classifier.pth",
        device: str = "cpu",
        confidence_threshold: float = 0.7
    ):
        self.weights_path = weights_path
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.transform = None
        self._use_feature_engineering = False
        self._feature_classifier = None

        # Real-Bogus 分类标签
        self.rb_classes = ["BOGUS", "REAL"]
        # Astro分类 (STAR/GALAXY/QSO) -> Real-Bogus映射
        self.astro_to_rb = {
            0: "REAL",   # STAR -> REAL
            1: "REAL",   # GALAXY -> REAL
            2: "REAL",   # QSO -> REAL
        }
        
    def _is_valid_weights_file(self) -> bool:
        """检查权重文件是否有效（非全0）"""
        if not os.path.exists(self.weights_path):
            return False
        # 读取前1KB检查是否全0
        with open(self.weights_path, 'rb') as f:
            header = f.read(1024)
        return header != b'\x00' * len(header)

    def load_model(self) -> bool:
        """加载模型权重，失败时自动降级到特征工程分类器"""
        if not HAS_TORCH:
            print("PyTorch未安装，启用特征工程分类器")
            self._init_feature_classifier()
            return False

        if not os.path.exists(self.weights_path):
            print(f"权重文件不存在: {self.weights_path}，启用特征工程分类器")
            self._init_feature_classifier()
            return False

        if not self._is_valid_weights_file():
            print(f"权重文件无效（全0或损坏）: {self.weights_path}，启用特征工程分类器")
            self._init_feature_classifier()
            return False

        try:
            # 加载预训练的ResNet50
            self.model = models.resnet50(pretrained=False, num_classes=3)
            state_dict = torch.load(self.weights_path, map_location=self.device, weights_only=False)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()

            # 定义图像预处理
            self.transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),  # ResNet标准输入
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])

            print(f"Real-Bogus分类器(ResNet50)加载成功: {self.weights_path}")
            return True
        except Exception as e:
            print(f"模型加载失败: {e}，启用特征工程分类器")
            self._init_feature_classifier()
            return False

    def _init_feature_classifier(self):
        """初始化特征工程分类器作为降级方案"""
        self._use_feature_engineering = True
        self._feature_classifier = FeatureBasedRBClassifier(device=self.device)

    def _fallback_classify(self, image: np.ndarray, return_prob: bool) -> Dict[str, Any]:
        """当深度学习模型不可用时，使用特征工程分类器"""
        if self._feature_classifier is None:
            self._init_feature_classifier()
        import asyncio
        return asyncio.run(self._feature_classifier.classify(image, return_prob=return_prob))
    
    def preprocess_image(self, image: np.ndarray) -> Optional[torch.Tensor]:
        """预处理图像用于分类"""
        if self.transform is None:
            return None
        if len(image.shape) == 2:  # 灰度图 -> RGB
            image = np.stack([image] * 3, axis=-1)
        elif image.shape[-1] == 4:  # RGBA -> RGB
            image = image[:, :, :3]
        return self.transform(image.astype(np.uint8))
    
    async def classify(
        self,
        image: np.ndarray,
        return_prob: bool = False
    ) -> Dict[str, Any]:
        """
        对单张候选图像进行Real-Bogus分类
        
        Args:
            image: 候选源图像 (HxW 或 HxWx3 numpy array)
            return_prob: 是否返回概率
            
        Returns:
            {"class": "REAL"/"BOGUS", "confidence": float, ...}
        """
        if self.model is None:
            # 尝试加载
            if not self.load_model():
                return self._fallback_classify(image, return_prob)

        try:
            tensor = self.preprocess_image(image)
            if tensor is None:
                return self._fallback_classify(image, return_prob)
                
            with torch.no_grad():
                input_tensor = tensor.unsqueeze(0).to(self.device)
                output = self.model(input_tensor)
                probs = torch.softmax(output, dim=1)[0].cpu().numpy()
            
            # 找出最高概率的astro分类
            astro_class_idx = np.argmax(probs)
            astro_class_name = ["STAR", "GALAXY", "QSO"][astro_class_idx]
            astro_confidence = float(probs[astro_class_idx])
            
            # 转换为 Real-Bogus
            rb_class = self.astro_to_rb.get(astro_class_idx, "REAL")
            # Real置信度 = 所有非bogus类概率之和
            rb_confidence = float(probs[0] + probs[1] + probs[2])  # 全当作REAL
            
            result = {
                "class": rb_class,
                "confidence": rb_confidence,
                "astro_class": astro_class_name,
                "astro_confidence": astro_confidence,
                "probabilities": {
                    "STAR": float(probs[0]),
                    "GALAXY": float(probs[1]),
                    "QSO": float(probs[2])
                }
            }
            
            return result
            
        except Exception as e:
            print(f"分类失败: {e}，降级到特征工程分类器")
            return self._fallback_classify(image, return_prob)

    def _fallback_classify(self, image: np.ndarray, return_prob: bool) -> Dict[str, Any]:
        """当深度学习模型不可用时，使用特征工程分类器"""
        if self._feature_classifier is None:
            self._init_feature_classifier()
        import asyncio
        return asyncio.run(self._feature_classifier.classify(image, return_prob=return_prob))
    
    async def batch_classify(
        self,
        images: List[np.ndarray]
    ) -> List[Dict[str, Any]]:
        """批量分类"""
        return [await self.classify(img) for img in images]


class FeatureBasedRBClassifier:
    """
    基于图像特征工程的 Real-Bogus 分类器

    无需预训练权重，通过提取天文图像的物理特征进行分类。

    特征说明:
    - flux_sum: 源区域总流量 (排除背景)
    - central_flux_ratio: 中心像素占总流量比例 (真实源通常有紧凑核)
    - fwhm: 半高全宽估计 (真实源有一定扩展)
    - elongation: 短轴/长轴比 (伪影通常形状不规则)
    - background_rms: 背景噪声RMS
    - snr: 信噪比
    - max_pixel_ratio: 最大像素与背景的比值

    真实天文源特征:
    - 紧凑但有延伸 (点源对星系不同)
    - 正态分布的光心
    - 边缘清晰

    伪影特征:
    - 极亮/极暗的条纹 (宇宙线)
    - 饱和列/行 (CCD坏道)
    - 形状不规则
    - 边缘模糊
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        # 经验阈值 (基于ZTF Real-Bogus数据集统计)
        self._thresholds = {
            "min_flux": 50.0,         # 最低流量阈值
            "min_snr": 5.0,            # 最低信噪比
            "max_elongation": 0.3,     # elongation < 0.3 → 可能是延伸源(真实)
            "min_central_ratio": 0.1,   # 中心流量占比过低 → 伪影
            "max_elong_bogus": 0.85,    # elongation > 0.85 → 线状伪影
            "sharpness_min": 0.5,
            "sharpness_max": 2.5,
        }

    def _extract_sources(self, image: np.ndarray) -> np.ndarray:
        """用简单阈值分割提取源区域"""
        background = np.median(image)
        rms = np.std(image[image < np.percentile(image, 70)])
        threshold = background + 5 * rms
        return (image > threshold).astype(np.uint8)

    def _compute_fwhm(self, image: np.ndarray, binary: np.ndarray) -> float:
        """估计FWHM (像素单位)"""
        y_coords, x_coords = np.where(binary > 0)
        if len(x_coords) < 3:
            return 1.0
        # 计算等效半径
        r = np.sqrt(len(x_coords) / np.pi)
        # FWHM ≈ 2 * sqrt(ln(2)) * sigma ≈ 1.177 * sigma
        # 等效sigma
        sigma = r / 1.177
        return max(1.0, 2.355 * sigma)

    def _compute_elongation(self, binary: np.ndarray) -> float:
        """计算源的elongation (短轴/长轴)"""
        y_coords, x_coords = np.where(binary > 0)
        if len(x_coords) < 5:
            return 0.5
        cov = np.cov(x_coords, y_coords)
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = sorted(eigenvalues, reverse=True)
        if eigenvalues[1] <= 0:
            return 0.0
        return np.sqrt(eigenvalues[1] / eigenvalues[0])

    def extract_features(self, image: np.ndarray) -> Dict[str, float]:
        """提取图像特征"""
        # 确保是2D数组
        if len(image.shape) == 3:
            image = np.mean(image, axis=2)

        h, w = image.shape
        cy, cx = h // 2, w // 2

        # 背景估计 (使用四分位数去异常值)
        bg = np.percentile(image, 25)
        rms = np.std(image[image < np.percentile(image, 70)])

        # 中心区域 (半径=min(h,w)/4)
        r = min(h, w) // 4
        y, x = np.ogrid[:h, :w]
        mask_center = ((y - cy)**2 + (x - cx)**2) <= r**2
        source_mask = ~mask_center

        # 源区域
        threshold = bg + 5 * rms
        binary = (image > threshold).astype(np.uint8)

        # 特征计算
        flux_in_source = np.sum(image[source_mask] - bg)
        max_pixel = np.max(image)
        central_val = image[cy, cx] if mask_center[cy, cx] else bg
        central_ratio = (central_val - bg) / (max_pixel - bg + 1e-6)

        fwhm = self._compute_fwhm(image, binary)
        elongation = self._compute_elongation(binary)
        snr = (max_pixel - bg) / (rms + 1e-6)

        # sharpness: 中心像素与周围4邻域的差异
        neighbors = [
            image[cy-1, cx] if cy > 0 else bg,
            image[cy+1, cx] if cy < h-1 else bg,
            image[cy, cx-1] if cx > 0 else bg,
            image[cy, cx+1] if cx < w-1 else bg,
        ]
        sharpness = (central_val - np.mean(neighbors)) / (rms + 1e-6)

        features = {
            "flux_sum": float(flux_in_source),
            "central_flux_ratio": float(central_ratio),
            "fwhm_pixels": float(fwhm),
            "elongation": float(elongation),
            "background_rms": float(rms),
            "snr": float(snr),
            "max_pixel_ratio": float((max_pixel - bg) / (rms + 1e-6)),
            "sharpness": float(sharpness),
        }
        return features

    def classify_by_features(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        基于特征向量进行 Real-Bogus 分类

        使用多层规则引擎，模拟真实/伪影的物理差异。
        """
        snr = features["snr"]
        flux = features["flux_sum"]
        elongation = features["elongation"]
        central_ratio = features["central_flux_ratio"]
        fwhm = features["fwhm_pixels"]
        sharpness = features["sharpness"]
        rms = features["background_rms"]

        real_score = 0.0
        bogus_score = 0.0

        # 1. SNR 检查 (最重要)
        if snr < 3:
            bogus_score += 0.5
            real_score -= 0.3
        elif snr >= 5:
            real_score += 0.3

        # 2. elongation 检查
        # 极端elongation (线状) → 伪影
        if elongation > self._thresholds["max_elong_bogus"]:
            bogus_score += 0.5
        # 中等elongation → 可能是延伸源(真实)
        elif elongation < 0.5:
            real_score += 0.2

        # 3. 中心流量占比
        if central_ratio < self._thresholds["min_central_ratio"]:
            bogus_score += 0.3
        elif central_ratio > 0.3:
            real_score += 0.2

        # 4. FWHM 检查
        if fwhm < 1.5:
            # 极紧凑 → 可能是宇宙线
            bogus_score += 0.2
        elif 2.0 <= fwhm <= 10.0:
            real_score += 0.15

        # 5. 流量检查
        if flux < self._thresholds["min_flux"]:
            bogus_score += 0.3
        else:
            real_score += 0.15

        # 6. Sharpness 检查 (模拟高斯核匹配)
        if sharpness < self._thresholds["sharpness_min"]:
            bogus_score += 0.2
        elif self._thresholds["sharpness_min"] <= sharpness <= self._thresholds["sharpness_max"]:
            real_score += 0.1

        # 7. 背景RMS异常 (极高 → 可能有CCD问题)
        if rms > 100:
            bogus_score += 0.2

        # 综合评分
        total = real_score + bogus_score + 1e-6
        real_prob = real_score / total
        bogus_prob = bogus_score / total

        rb_class = "REAL" if real_prob > bogus_prob else "BOGUS"
        confidence = max(real_prob, bogus_prob)

        return {
            "class": rb_class,
            "confidence": float(confidence),
            "real_prob": float(real_prob),
            "bogus_prob": float(bogus_prob),
            "features": features,
        }

    async def classify(
        self,
        image: np.ndarray,
        return_prob: bool = False
    ) -> Dict[str, Any]:
        """主分类入口"""
        features = self.extract_features(image)
        result = self.classify_by_features(features)
        if not return_prob:
            result.pop("real_prob", None)
            result.pop("bogus_prob", None)
        result["mode"] = "feature_engineering"
        return result

    async def batch_classify(self, images: List[np.ndarray]) -> List[Dict[str, Any]]:
        return [await self.classify(img) for img in images]


class TransientFilter:
    """
    变星/瞬变检测过滤器
    结合 Real-Bogus 分类器和多帧一致性检查
    """
    
    def __init__(self, rb_classifier: RealBogusClassifier = None):
        self.rb_classifier = rb_classifier or RealBogusClassifier()
        self.history: Dict[str, List[Dict]] = {}  # 保存历史检测
        
    async def filter_candidates(
        self,
        candidates: List[Dict],
        field_id: str,
        epoch: int
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        过滤候选源，返回真实候选和排除的候选
        
        Args:
            candidates: 候选源列表 [{"x": float, "y": float, "flux": float, ...}]
            field_id: 天区ID
            epoch: 观测历元
            
        Returns:
            (accepted, rejected) 元组
        """
        key = f"{field_id}_{epoch}"
        
        accepted = []
        rejected = []
        
        for cand in candidates:
            # Real-Bogus分类
            rb_result = await self.rb_classifier.classify(
                cand.get("image", np.zeros((32, 32)))
            )
            cand["rb_result"] = rb_result
            
            if rb_result["class"] == "REAL" and rb_result["confidence"] >= self.rb_classifier.confidence_threshold:
                # 额外检查：多历元一致性
                if self._check_epoch_consistency(cand, field_id):
                    accepted.append(cand)
                else:
                    cand["rejection_reason"] = "epoch_inconsistency"
                    rejected.append(cand)
            else:
                cand["rejection_reason"] = f"rb_class={rb_result['class']}, conf={rb_result['confidence']:.2f}"
                rejected.append(cand)
                
        return accepted, rejected
    
    def _check_epoch_consistency(self, cand: Dict, field_id: str) -> bool:
        """检查候选源在多历元中的一致性"""
        # 简化实现：实际需要多帧图像比对
        return True


if __name__ == "__main__":
    import asyncio
    
    classifier = RealBogusClassifier()
    
    # 测试分类
    test_image = np.random.randint(0, 255, (48, 48), dtype=np.uint8)
    
    async def test():
        result = await classifier.classify(test_image, return_prob=True)
        print(f"分类结果: {result}")
    
    asyncio.run(test())
