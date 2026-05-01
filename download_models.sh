#!/bin/bash
# 天问-AGI 模型权重下载脚本
# 用法: bash download_models.sh

set -e

MODELS_DIR="runtime/models"
mkdir -p "$MODELS_DIR"

echo "=========================================="
echo "天问-AGI 模型权重下载脚本"
echo "=========================================="

# ResNet-50 天文分类器权重
# 训练于 SDSS DR17 数据集，88.15% 分类准确率
RESNET50_URL="https://github.com/Aniket-k-13/celestial-object-detection/releases/download/v1.0/resnet50_astro_classifier.pth"
RESNET50_FILE="$MODELS_DIR/resnet50_astro_classifier.pth"

echo ""
echo "[1/2] 下载 ResNet-50 天文分类器权重..."
echo "模型: ResNet-50 天体分类 (STAR/GALAXY/QSO)"
echo "精度: 88.15% (SDSS DR17)"
echo "来源: Aniket-k-13/celestial-object-detection"

if [ -f "$RESNET50_FILE" ]; then
    echo "  ✓ ResNet-50 权重已存在: $RESNET50_FILE"
else
    echo "  下载中..."
    curl -L -o "$RESNET50_FILE" "$RESNET50_URL" 2>/dev/null || {
        echo "  ⚠ 下载失败，请手动下载:"
        echo "  URL: $RESNET50_URL"
        echo "  保存到: $RESNET50_FILE"
    }
fi

# YOLOv11s 天文检测器权重
# 训练于 COSMICA 数据集，72.2% mAP@50
YOLO_URL="https://github.com/Aniket-k-13/celestial-object-detection/releases/download/v1.0/yolo11s_astro_detection.pt"
YOLO_FILE="$MODELS_DIR/yolo11s_astro_detection.pt"

echo ""
echo "[2/2] 下载 YOLOv11s 天文检测器权重..."
echo "模型: YOLOv11s 目标检测 (nebula/galaxy/comet/globular_cluster)"
echo "精度: 72.2% mAP@50 (COSMICA)"
echo "来源: Aniket-k-13/celestial-object-detection"

if [ -f "$YOLO_FILE" ]; then
    echo "  ✓ YOLOv11s 权重已存在: $YOLO_FILE"
else
    echo "  下载中..."
    curl -L -o "$YOLO_FILE" "$YOLO_URL" 2>/dev/null || {
        echo "  ⚠ 下载失败，请手动下载:"
        echo "  URL: $YOLO_URL"
        echo "  保存到: $YOLO_FILE"
    }
fi

echo ""
echo "=========================================="
echo "下载完成！"
echo "=========================================="
echo ""
echo "模型文件:"
ls -lh "$MODELS_DIR" 2>/dev/null || echo "  (目录为空或不存在)"
echo ""
echo "下一步:"
echo "  1. 运行测试: python -m pytest runtime/tests/test_observation_loop_integration.py -v"
echo "  2. 集成到观测闭环: 更新 research_loop.py"
echo ""