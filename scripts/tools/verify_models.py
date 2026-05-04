"""
模型权重下载和配置验证脚本
"""
import os
import sys

def main():
    print("=" * 60)
    print("天问-AGI 模型配置验证")
    print("=" * 60)

    # 任务1: 验证目录创建
    print("\n[任务1] 验证模型目录...")
    models_dir = "F:/tianwen-agi/runtime/models"
    if os.path.exists(models_dir):
        files = os.listdir(models_dir)
        print(f"  [OK] 模型目录存在: {models_dir}")
        print(f"  [OK] 目录内容: {files}")
    else:
        print(f"  [FAIL] 模型目录不存在: {models_dir}")
        return False

    # 任务2: 验证模型文件
    print("\n[任务2] 验证模型文件...")
    resnet_path = os.path.join(models_dir, "resnet50_astro_classifier.pth")
    yolo_path = os.path.join(models_dir, "yolo11s_astro_detection.pt")

    resnet_exists = os.path.exists(resnet_path)
    yolo_exists = os.path.exists(yolo_path)

    if resnet_exists:
        resnet_size = os.path.getsize(resnet_path) / (1024*1024)
        print(f"  [OK] ResNet-50权重存在: {resnet_path} ({resnet_size:.1f} MB)")
    else:
        print(f"  [FAIL] ResNet-50权重不存在: {resnet_path}")

    if yolo_exists:
        yolo_size = os.path.getsize(yolo_path) / (1024*1024)
        print(f"  [OK] YOLOv11s权重存在: {yolo_path} ({yolo_size:.1f} MB)")
    else:
        print(f"  [FAIL] YOLOv11s权重不存在: {yolo_path}")

    # 任务3: 验证AstroPipeline初始化
    print("\n[任务3] 验证AstroPipeline初始化...")
    try:
        sys.path.insert(0, "F:/tianwen-agi/runtime")
        from src.astronomy.pipeline import AstroPipeline

        pipeline = AstroPipeline()
        print(f"  [OK] AstroPipeline初始化成功")

        # 检查模型加载状态
        if pipeline.stage2_classifier.model is not None:
            print(f"  [OK] ResNet-50模型已加载")
        else:
            print(f"  [INFO] ResNet-50使用模拟模式")

        if pipeline.stage3_detector.model is not None:
            print(f"  [OK] YOLOv11s模型已加载")
        else:
            print(f"  [INFO] YOLOv11s使用模拟模式")

    except Exception as e:
        print(f"  [FAIL] AstroPipeline初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("验证完成!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)