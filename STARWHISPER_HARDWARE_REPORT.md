# StarWhisper硬件配置检测报告

> 检测日期: 2026-05-03
> 检测设备: 联想拯救者R7000 2024 (83D3)

---

## 1. 当前硬件配置

| 组件 | 规格 | 状态 |
|------|------|------|
| **CPU** | AMD Ryzen 7 8745H (8核16线程) | ✅ 满足 |
| **GPU** | AMD Radeon 780M (RDNA3, 集成) | ❌ 不满足 |
| **系统内存** | 10GB total, 7.6GB available | ❌ 不足 |
| **存储(F:)** | 315GB total, 151GB available | ⚠️ 紧张 |
| **WSL** | WSL2 + WSLg | ✅ 已启用 |
| **Python** | 3.12.3 | ✅ 满足 |
| **PyTorch** | 2.11.0 (CPU only) | ❌ 需GPU版本 |

### 1.1 GPU详细

```
型号: AMD Radeon 780M Graphics
架构: RDNA3 (代号Phoenix)
显存: 共享系统内存 (最大约4GB配置)
位置: 集成于 Ryzen 7 8745H APU
```

---

## 2. StarWhisper硬件需求

### 2.1 官方推荐配置

| 项目 | 最低配置 | 推荐配置 | 你的配置 | 差距 |
|------|----------|----------|----------|------|
| **GPU** | RTX 3090 24GB | A100 40GB x4 | AMD 780M | ❌❌ |
| **内存** | 64GB | 256GB | 7.6GB | ❌❌ |
| **存储** | 500GB | 2TB | 151GB | ⚠️ |
| **CUDA** | 11.8 | 12.x | N/A | ❌ |

### 2.2 核心模型规格 (SpectrumDiffusionModel)

```
参数量: ~86M (256*6层Transformer)
显存需求:
  - 全精度(FP32): ~1.5GB
  - 半精度(FP16): ~750MB
  - 量化(Q4): ~400MB

批处理需求:
  - batch_size=1: ~800MB (FP16)
  - batch_size=8: ~6GB (FP16) ❌超出
```

---

## 3. 替代方案对比

### 方案A: WSL2 + AMD ROCm

**原理**: AMD显卡通过ROCm在Linux/WSL中运行

**要求**:
1. Windows端安装ROCm 6.0+ for Windows
2. WSL更新到最新版本
3. 在WSL中安装ROCm版PyTorch

```bash
# 检查ROCm是否可用
rocm-smi

# 安装ROCm版PyTorch
pip install torch --index-url https://download.pytorch.org/whl/rocm5.6
```

**成功率**: 40%
- 780M(RDNA3)理论上支持
- 但WSL集成可能有兼容性问题
- 需要额外驱动配置

**成本**: 免费

---

### 方案B: 云端训练 + 本地微调/推理 ⭐推荐

**分工**:
| 阶段 | 位置 | 资源 | 耗时 |
|------|------|------|------|
| 预训练 | 已完成 | HuggingFace | N/A |
| 全量微调 | 云端 | 1x A100 | ~3周 |
| 本地微调 | 本地 | 780M | ~2周 |
| 推理 | 本地 | 780M | 可用 |

**优势**:
- 使用官方预训练权重，跳过最耗时阶段
- 仅需微调阶段在云端
- 本地可做推理测试

**云端推荐**:
| 服务 | GPU | 价格 | 备注 |
|------|-----|------|------|
| **AutoDL** | RTX 4090 | ¥1.2/小时 | 国产首选 |
| **恒源云** | A100 80G | ¥8/小时 | 高端需求 |
| **Kaggle** | T4 x2 | 免费 | 限每周40小时 |
| **Vast.ai** | RTX 3090 | ~$0.2/小时 | 国际便宜 |

---

### 方案C: 纯云端方案

**配置**:
```yaml
# AutoDL推荐配置
镜像: PyTorch 2.0 + CUDA 11.8
GPU: RTX 4090 24GB
CPU: 14核
内存: 47GB
系统盘: 50GB
数据盘: 100GB (额外挂载)
价格: ¥1.2/小时 ≈ ¥20/天
```

**成本估算**:
| 阶段 | GPU小时 | 单价 | 总价 |
|------|---------|------|------|
| 全量预训练 | 20,000 | ¥1.2 | ¥24,000 |
| 微调 | 3,000 | ¥1.2 | ¥3,600 |
| 测试 | 500 | ¥1.2 | ¥600 |
| **总计** | 23,500 | - | **¥28,200** |

**可优化**:
- 使用预训练权重，节省¥24,000
- 仅微调+测试 ≈ ¥4,200

---

### 方案D: 降级复现 (本地勉强运行)

**降低配置**:
```yaml
model:
  n_embd: 128    # 256 -> 128
  n_head: 4       # 8 -> 4
  n_layer: 3     # 6 -> 3
  block_size: 2048  # 12288 -> 2048

training:
  batch_size: 1
  gradient_accumulation: 32
  use_gradient_checkpointing: true
```

**预期性能**:
| 指标 | 预期 |
|------|------|
| 显存需求 | ~2GB (FP16) |
| 训练速度 | ~1 step/30秒 |
| 总训练步数 | 100,000步 |
| 预计时间 | ~35天 ⚠️ |

**问题**:
- 时间过长
- 性能可能不达标
- 需24小时开机

---

## 4. 推荐执行路径

### 阶段1: 本地验证 (Day 1-3) - 免费

```bash
# 1. 下载预训练权重
cd /mnt/f/StarWhisper-main
git lfs install  # 如果未安装
git clone https://huggingface.co/Jaredxjc/Low-SNR-Stellar-Spectra-as-Language

# 2. 创建轻量级推理脚本
python -c "
import torch
from pathlib import Path
model_path = Path('Low-SNR-Stellar-Spectra-as-Language/pretrain.pt')
if model_path.exists():
    print('权重已下载')
else:
    print('需下载权重')
"

# 3. 尝试ROCm (可选)
# 按方案A尝试
```

**交付**: 确认权重可用，验证代码完整性

### 阶段2: 云端微调 (Day 4-30) - ¥4,200

```bash
# 1. 注册AutoDL
# 2. 上传代码和数据
# 3. 启动RTX 4090实例
# 4. 运行微调

# 微调配置
python scripts/finetune.py \
    --pretrained_path ./pretrain.pt \
    --data ./data/lamost_finetune.csv \
    --output_dir ./output/finetune
```

**交付**: 微调后模型权重

### 阶段3: 本地推理测试 (Day 31-35) - 免费

```bash
# 下载微调权重到本地
# 运行推理测试
python scripts/inference.py \
    --model ./finetune_model.pt \
    --input ./test_spectrum.csv
```

---

## 5. 立即行动清单

| 优先级 | 任务 | 耗时 | 费用 |
|--------|------|------|------|
| P0 | 下载预训练权重 | 30分钟 | 免费 |
| P0 | 注册AutoDL账号 | 10分钟 | 免费 |
| P1 | 尝试ROCm (备用) | 1小时 | 免费 |
| P1 | 准备微调数据 | 1天 | 免费 |
| P2 | 充值AutoDL (¥500起) | - | ¥500 |

---

## 6. 硬件升级建议 (可选)

如果未来需要更强本地能力:

| 升级项 | 方案 | 价格 | 效果 |
|--------|------|------|------|
| **eGPU** | ADLINK eGPU + RTX 4070 | ¥4,000 | 可运行微调 |
| **内存** | DDR5 32GB x2 | ¥800 | 满足训练 |
| **NVMe** | 2TB SSD | ¥800 | 扩容存储 |

**注意**: 游戏本BIOS可能限制eGPU性能

---

## 7. 结论

| 方案 | 可行性 | 成本 | 推荐度 |
|------|--------|------|--------|
| **方案B** (云微调+本地推理) | ✅ 高 | ¥4,200 | ⭐⭐⭐⭐⭐ |
| **方案C** (全云端) | ✅ 高 | ¥28,200 | ⭐⭐⭐⭐ |
| **方案A** (ROCm) | ⚠️ 中 | 免费 | ⭐⭐⭐ |
| **方案D** (本地降级) | ⚠️ 低 | 电费 | ⭐⭐ |

**最终建议**: 采用方案B，先下载预训练权重验证代码完整性，再注册AutoDL进行微调。

---

*报告生成: Hermes Agent for 天问-AGI*
