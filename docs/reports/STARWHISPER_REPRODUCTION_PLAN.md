# StarWhisper 天文大模型复现详细计划

> 目标仓库: https://github.com/Yu-Yang-Li/StarWhisper
> 复现可行性评估: **9.2/10 (高)**
> 报告生成日期: 2026-05-03

---

## 目录

1. [项目概述](#1-项目概述)
2. [复现可行性分析](#2-复现可行性分析)
3. [环境准备清单](#3-环境准备清单)
4. [代码结构详解](#4-代码结构详解)
5. [数据准备流程](#5-数据准备流程)
6. [训练执行计划](#6-训练执行计划)
7. [验证与评估](#7-验证与评估)
8. [风险评估与备选方案](#8-风险评估与备选方案)
9. [时间规划](#9-时间规划)
10. [资源需求汇总](#10-资源需求汇总)

---

## 1. 项目概述

### 1.1 StarWhisper项目组成

StarWhisper是一个多模组天文大模型项目，包含以下核心组件：

| 组件 | 路径 | 功能 | 技术栈 |
|------|------|------|--------|
| **光谱扩散模型** | `Low-SNR-Stellar-Spectra-as-Language/` | 低信噪比恒星光谱token化与生成 | PyTorch, 自研SpectrumDiffusionModel |
| **光变曲线分类** | `StarWhisper_LC/` | 恒星/星系光变曲线分类 | EfficientNet, ConvNeXt, LSTM, Swin |
| **望远镜控制Agent** | `NGSS/` | 司天工程望远镜智能控制 | Python, astropy, astroplan |
| **LLM训练数据** | `LLM_Data/` | 天文知识问答训练数据 | JSON格式 |

### 1.2 核心技术架构

**光谱扩散模型 (SpectrumDiffusionModel)**

基于AO-GPT-MDM (Any-Order GPT as Masked Diffusion Model) 论文实现：

```python
# 核心配置
vocab_size=84        # 词表大小
n_embd=256          # 嵌入维度
n_head=8            # 注意力头数
n_layer=6           # Transformer层数
block_size=12288    # 最大序列长度
cond_dim=128        # 条件嵌入维度
```

关键特性：
- 任意顺序生成 (Any-Order Generation)
- 目标位置感知条件 (WTPE)
- AdaLN条件注入
- Flash Attention支持

### 1.3 复现目标

| 阶段 | 目标 | 优先级 |
|------|------|--------|
| Phase 1 | 环境搭建 + Demo运行 | P0 |
| Phase 2 | 光谱扩散模型预训练 | P0 |
| Phase 3 | 光谱模型微调 (LAMOST) | P1 |
| Phase 4 | 光变曲线分类模型 | P2 |
| Phase 5 | 望远镜Agent集成 | P2 |

---

## 2. 复现可行性分析

### 2.1 资源完整性评估

| 资源类型 | 状态 | 说明 |
|----------|------|------|
| **模型代码** | 已开源 | `src/spectral_lm/model_architecture.py` (659行) |
| **预训练脚本** | 已开源 | `scripts/pretrain.py` (~500行) |
| **微调脚本** | 已开源 | `scripts/finetune.py` (~500行) |
| **数据预处理** | 已开源 | `scripts/preprocess_data.py` (~400行) |
| **词表定义** | 已开源 | `vocab/vocabulary.csv` (148词) |
| **预训练权重** | HuggingFace | Jaredxjc/Low-SNR-Stellar-Spectra-as-Language |
| **训练数据** | 部分开源 | LLM_Data/ (~253MB) |
| **完整文档** | 已开源 | README.md + README_EN.md |

**评分: 9.2/10**

### 2.2 依赖外部资源

| 资源 | 来源 | 获取难度 | 用途 |
|------|------|----------|------|
| LAMOST DR12光谱 | lamost.org | 中 (需注册) | 训练数据 |
| PHOENIX合成光谱 | FTP | 易 | 高质量模板 |
| HuggingFace权重 | huggingface.co | 易 | 预训练起点 |

### 2.3 复现优势

1. **代码完整**: 核心模型、训练脚本、预处理脚本全部开源
2. **权重可用**: HuggingFace有预训练权重
3. **文档详尽**: 英文README数据管道说明完整
4. **架构清晰**: 基于成熟论文 (AO-GPT-MDM)
5. **社区活跃**: GitHub 1.3k+ stars

---

## 3. 环境准备清单

### 3.1 硬件环境

| 组件 | 最低配置 | 推荐配置 | 用途 |
|------|----------|----------|------|
| GPU | RTX 3090 (24GB) | A100 (40GB+) x4 | 训练 |
| CPU | 8核 | 32核 | 数据预处理 |
| 内存 | 64GB | 256GB | 大数据集处理 |
| 存储 | 500GB SSD | 2TB NVMe | 代码+数据+模型 |
| 网络 | 100Mbps | 1Gbps | 数据下载 |

### 3.2 软件环境

#### 3.2.1 操作系统

```bash
# 推荐: Ubuntu 22.04 LTS 或 CentOS Stream 9
lsb_release -a  # 检查系统版本
uname -r        # 检查内核
```

#### 3.2.2 基础依赖

```bash
# Python 3.10+
python3 --version
# 预期输出: Python 3.10.x 或更高

# CUDA 11.8+ (用于PyTorch)
nvcc --version
# 预期输出: Cuda compilation tools, release 11.x

# cuDNN (配合CUDA)
cat /usr/local/cuda/include/cudnn_version.h | grep CUDNN_MAJOR -A 2
```

#### 3.2.3 Python环境创建

```bash
# 使用conda创建独立环境
conda create -n starwhisper python=3.10 -y
conda activate starwhisper

# 或使用venv
python3.10 -m venv starwhisper_env
source starwhisper_env/bin/activate
```

### 3.3 必需Python包

```bash
# PyTorch (CUDA 11.8)
pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118

# 核心依赖
pip install \
    numpy>=1.24.0 \
    pandas>=2.0.0 \
    scikit-learn>=1.3.0 \
    tqdm>=4.65.0 \
    matplotlib>=3.7.0 \
    scipy>=1.11.0

# 天文专用
pip install \
    astropy>=5.3.0 \
    astroplan>=0.9.0 \
    numpy>=1.24.0

# 分布式训练 (可选)
pip install \
    torch.distributed==2.0.1 \
    accelerate>=0.24.0

# 日志与工具
pip install \
    loguru>=0.7.0 \
    icecream>=2.1.0 \
    pyyaml>=6.0

# Jupyter (开发环境)
pip install jupyter notebook ipykernel
python -m ipykernel install --user --name=starwhisper --display-name="StarWhisper"
```

### 3.4 验证安装

```bash
# 创建验证脚本 verify_env.py
python verify_env.py
```

```python
# verify_env.py
import torch
import astropy
import numpy
import pandas

print(f"PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
print(f"Astropy: {astropy.__version__}")
print(f"NumPy: {numpy.__version__}")
print(f"Pandas: {pandas.__version__}")
```

---

## 4. 代码结构详解

### 4.1 目录树

```
StarWhisper-main/
|
|--Low-SNR-Stellar-Spectra-as-Language/     # 光谱LLM核心
|   |--src/
|   |   |--spectral_lm/
|   |   |   |--__init__.py
|   |   |   |--model_architecture.py        # [核心] 模型定义 (659行)
|   |   |
|   |   |--vocab/
|   |   |   |--vocabulary.csv                # [核心] 词表定义 (148词)
|   |   |   |--README.md                     # 词表说明
|   |   |
|   |--scripts/
|   |   |--pretrain.py                      # [核心] 预训练入口
|   |   |--finetune.py                      # [核心] 微调入口
|   |   |--preprocess_data.py               # [核心] 数据预处理
|   |   |
|   |--code/
|   |   |--pylamost-master/                 # LAMOST数据下载
|   |   |   |--pylamost.py
|   |   |   |--lamost_dr12_pipeline.py
|   |   |   |--lamost_dr12_50.py
|   |   |   |--sample-*.py
|   |   |
|   |   |--interpolation&decrease_resolution/  # 光谱重采样
|   |   |   |--CaII.py                       # Ca II红端光谱
|   |   |   |--CaII_300p.py                  # 300像素版本
|   |   |   |--ShowOut/
|   |   |   |   |--interpolation0415.py
|   |   |
|   |   |--lamost_sft_data/                  # LAMOST数据转换
|   |   |   |--lamost_flux_preprocessing.py
|   |   |   |--convert_lamost_to_pretrain_format.py
|   |   |   |--mix_spectra.py
|   |   |   |--run1207.sh
|   |   |
|   |   |--lamost_data_augmentation/         # 数据增强
|   |   |   |--lamost_flux_preprocessing.py
|   |   |   |--convert_lamost_to_pretrain_format.py
|   |   |   |--run.sh
|   |
|   |--data/                                # 输出数据目录 (需创建)
|   |   |--train/                            # 训练集
|   |   |--val/                              # 验证集
|   |
|   |--legacy_pretrain/                      # 遗留代码
|   |   |--model_architecture.py
|   |   |--pretrain_script_legacy.py
|   |   |--launch_slrum_pretrain.sh
|   |
|   |--vocab/                               # 词表
|   |   |--vocabulary.csv
|   |
|   |--examples/                             # 示例
|   |
|   |--requirements.txt                      # 依赖列表
|   |--README.md                             # 中文文档
|   |--README_EN.md                          # 英文文档
|
|--LLM_Data/                                # LLM训练数据
|   |--Astro_en.json                        # 英文天文 (104MB)
|   |--Physic.json                          # 物理 (30MB)
|   |--astro_cn_1.json                      # 中文天文 (21MB x 6)
|   |--astro_cn_2.json
|   |--astro_cn_3.json
|   |--astro_cn_4.json
|   |--astro_cn_5.json
|   |--astro_cn_6.json
|
|--NGSS/                                    # 望远镜控制Agent
|   |--src/
|   |   |--module/
|   |   |   |--PlanObservation3.py          # 观测计划
|   |   |   |--transientDetection.py         # 暂现源检测
|   |   |   |--Data_pipeline.py              # 数据管道
|   |   |   |--SearchPath.py                 # 搜索路径
|   |   |   |--UdpConnect.py                 # UDP通信
|   |   |   |--topic.yaml                    # 主题配置
|   |   |
|   |   |--script/
|   |   |   |--daily_update.py               # 日常更新
|   |   |   |--udp_connect.py                # UDP连接
|   |   |
|   |   |--app/
|   |   |   |--app2.py                       # 应用入口
|   |   |
|   |   |--util/
|   |   |   |--Decorators/
|   |   |   |   |--Logging/
|   |   |   |   |   |--log_func_run_status.py
|   |   |   |   |   |--log_iteration_progress.py
|   |   |   |--util.py
|   |
|   |--observation Schedule/                 # 观测日程
|   |--runningLog/                          # 运行日志
|
|--StarWhisper_LC/                          # 光变曲线分类
|   |--Code/
|   |   |--CNN.py                           # CNN模型
|   |   |--Convnext.py                      # ConvNeXt模型
|   |   |--lstm.py                          # LSTM模型
|   |   |--lstm+attention.py                # LSTM+注意力
|   |   |--swin_transformer.py              # Swin Transformer
|   |   |--get_CWT.py                       # 小波变换
|   |   |--get_image.py                     # 图像生成
|   |
|   |--Result/                              # 结果目录
|
|--example/                                 # 示例图片
    |--StarWhisper.png
    |--StarWhisper3.png
    |--Star-Whisper.png
    |--Sitian.png
    |--Agent.png
    |--Eval.png
    |--Release.png
    |--context.png / context_en.png
    |--图片1.png / 图片2.png / 图片3.png
    |--StarWhisper LC.png
    |--Starwhisper Telescope.png
    |--books.jpg
```

### 4.2 核心文件详解

#### 4.2.1 模型架构 (model_architecture.py)

**文件**: `Low-SNR-Stellar-Spectra-as-Language/src/spectral_lm/model_architecture.py`
**行数**: 659行
**核心类**: `SpectrumDiffusionModel`

```python
class SpectrumDiffusionModel(nn.Module):
    """光谱扩散模型 - AO-GPT风格实现"""
    
    def __init__(
        self,
        vocab_size=84,      # 词表大小
        n_embd=256,        # 嵌入维度
        n_head=8,         # 注意力头数
        n_layer=6,         # Transformer层数
        block_size=12288,  # 最大序列长度
        cond_dim=128,      # 条件维度
        bos_token_id=0,
        eos_token_id=1,
        pad_token_id=2,
        mask_token_id=None
    ):
        # 嵌入层
        self.wte = nn.Embedding(vocab_size, n_embd)  # token嵌入
        self.wpe = nn.Embedding(block_size + 1, n_embd)  # 位置嵌入
        self.wtpe = nn.Embedding(block_size, cond_dim)  # 目标位置嵌入
        self.wnonee = nn.Embedding(1, n_embd)  # [None] token
        
        # Transformer块
        self.blocks = nn.ModuleList([
            DiffusionTransformerBlock(n_embd, n_head, block_size, cond_dim)
            for _ in range(n_layer)
        ])
        
        # 最终层
        self.final_layer = FinalLayer(n_embd, cond_dim)
        
        # 语言模型头
        self.lm_head = nn.Linear(n_embd, vocab_size, bias=True)
```

**关键方法**:

| 方法 | 功能 |
|------|------|
| `forward()` | 主前向传播，支持多种训练模式 |
| `forward_fn()` | 扩散模型核心计算 |
| `generate_parallel()` | 并行去噪生成 |
| `sample_random_orders()` | 结构化随机顺序采样 |
| `add_regression_head()` | 添加参数回归头 |

**训练模式**:

| 模式 | 说明 |
|------|------|
| `AR` | 标准自回归 |
| `Random` | 完全随机顺序 |
| `Random_CL` | 课程学习随机顺序 |
| `param_prediction` | 参数回归任务 |

#### 4.2.2 词表定义 (vocabulary.csv)

**文件**: `Low-SNR-Stellar-Spectra-as-Language/vocab/vocabulary.csv`
**词数**: 148

| token_id | token | 说明 |
|----------|-------|------|
| 0 | `<BOS>` | 序列开始 |
| 1 | `<EOS>` | 序列结束 |
| 2 | `<SEP>` | 分隔符 |
| 3-12 | `T0_tthou` - `T9_tthou` | Teff万位 (温度) |
| 13-22 | `T0_thu` - `T9_thu` | Teff千位 |
| 23-32 | `T0_hun` - `T9_hun` | Teff百位 |
| 33-42 | `T0_ten` - `T9_ten` | Teff十位 |
| 43-52 | `T0_one` - `T9_one` | Teff个位 |
| 53-61 | `L0_hun` - `L8_hun` | logg百位 |
| 62-70 | `L0_ten` - `L8_ten` | logg十位 |
| 71-79 | `L0_one` - `L8_one` | logg个位 |
| 80-81 | `L_pos`, `L_neg` | logg符号 |
| 82-91 | `F0_ten` - `F9_ten` | FeH十位 |
| 92-101 | `F0_one` - `F9_one` | FeH个位 |
| 102-103 | `F_pos`, `F_neg` | FeH符号 |
| 104-143 | `F0_thu` - `F9_one` | flux (4位/像素) |

#### 4.2.3 预训练脚本 (pretrain.py)

**文件**: `Low-SNR-Stellar-Spectra-as-Language/scripts/pretrain.py`
**行数**: ~500行

核心功能：
- 分布式数据并行 (DDP) 支持
- 混合精度训练 (AMP)
- 断点续训
- 早停机制
- 学习率warmup + cosine调度

关键配置：
```python
# 默认配置
config = {
    'vocab_size': 84,
    'n_embd': 256,
    'n_head': 8,
    'n_layer': 6,
    'block_size': 12288,
    'cond_dim': 128,
    'batch_size': 8,
    'learning_rate': 1e-4,
    'warmup_steps': 1000,
    'total_steps': 100000,
}
```

#### 4.2.4 数据预处理 (preprocess_data.py)

**文件**: `Low-SNR-Stellar-Spectra-as-Language/scripts/preprocess_data.py`
**行数**: ~400行

数据格式 (20列):
```python
OUTPUT_COLUMNS = [
    'spectrum_id', 'pixel_idx',
    'Teff_tthou', 'Teff_thu', 'Teff_hun', 'Teff_ten', 'Teff_one',
    'logg_hun', 'logg_ten', 'logg_one', 'logg_sign',
    'FeH_ten', 'FeH_one', 'FeH_sign',
    'flux_thu', 'flux_hun', 'flux_ten', 'flux_one',
    'BOS_token', 'EOS_token', 'SEP_token'
]
```

---

## 5. 数据准备流程

### 5.1 已有数据 (LLM_Data)

**路径**: `/mnt/f/StarWhisper-main/StarWhisper-main/LLM_Data/`

| 文件 | 大小 | 内容 | 用途 |
|------|------|------|------|
| `Astro_en.json` | 104MB | 英文天文Q&A | LLM SFT |
| `Physic.json` | 30MB | 物理Q&A | LLM SFT |
| `astro_cn_1~6.json` | 126MB | 中文天文Q&A | LLM SFT |

**数据格式**:
```json
{
  "prompt": "用户问题",
  "response": "详细回答"
}
```

### 5.2 光谱数据管道

#### 5.2.1 PHOENIX合成光谱

```
来源: https://phoenix.astro.physy.uni-goettingen.de/
协议: FTP anonymous
用途: 高分辨率模板光谱
```

下载步骤：
```bash
# 安装FTP客户端
sudo apt install filezilla  # 或使用lftp

# 连接FTP
ftp ftp.astro.physik.uni-goettingen.de
# anonymous登录
# cd /PHOENIX/hofer_2012/
# mget *Z*.fits
```

#### 5.2.2 LAMOST DR12数据

**注册地址**: https://www.lamost.org/

申请流程：
1. 注册账号
2. 申请数据访问权限
3. 创建PyLAMOST token
4. 下载DR12 CSV目标列表

```bash
# 安装PyLAMOST
cd code/pylamost-master/
pip install -e .

# 配置token
export PYLAMOST_TOKEN="your_token_here"

# 下载示例
python sample-download.py --obsid 123456
```

#### 5.2.3 光谱重采样

```bash
# 1. PHOENIX插值到工作波长
python code/interpolation&decrease_resolution/ShowOut/interpolation0415.py \
    --input /path/to/phoenix \
    --output /path/to/interpolated \
    --resolution 3000

# 2. 降分辨率并加噪声
python code/interpolation&decrease_resolution/CaII.py \
    --input /path/to/interpolated \
    --output /path/to/caii \
    --snr 30 \
    --resolution 3000

# 3. 生成短序列版本 (微调用)
python code/interpolation&decrease_resolution/CaII_300p.py \
    --input /path/to/interpolated \
    --output /path/to/caii_300p \
    --snr 10 \
    --pixels 300
```

#### 5.2.4 LAMOST数据转换

```bash
# 1. 预处理LAMOST通量
python code/lamost_sft_data/lamost_flux_preprocessing.py \
    --input /path/to/lamost \
    --output /path/to/lamost_flux_tokenized.csv

# 2. 转换格式并合并参数
python code/lamost_sft_data/convert_lamost_to_pretrain_format.py \
    --input lamost_flux_tokenized_full.csv \
    --catalog /path/to/dr12_catalog.csv \
    --output lamost_pretrain_format.csv \
    --max_rows 1000000

# 3. 数据增强 (可选)
python code/lamost_data_augmentation/run.sh
```

#### 5.2.5 最终预处理

```bash
# 分割训练/验证集
python scripts/preprocess_data.py \
    --input /path/to/combined_spectra.csv \
    --output_dir ./data \
    --vocab_path ./vocab/vocabulary.csv \
    --train_ratio 0.9 \
    --val_ratio 0.1
```

### 5.3 数据集统计

| 数据集 | 光谱数 | 像素/光谱 | SNR范围 | 用途 |
|--------|--------|-----------|---------|------|
| PHOENIX高分辨 | ~50,000 | 3030 | 无噪声 | 预训练 |
| PHOENIX CaII | ~50,000 | ~300 | 5-100 | 微调 |
| LAMOST DR12 | ~100,000 | 3030 | 1-50 | 微调 |
| LLM_Data | ~500条 | N/A | N/A | LLM SFT |

---

## 6. 训练执行计划

### 6.1 Phase 1: 环境验证 (Day 1-2)

#### 目标
- 完成环境搭建
- 运行demo验证pipeline

#### 执行步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Yu-Yang-Li/StarWhisper.git
cd StarWhisper/Low-SNR-Stellar-Spectra-as-Language

# 2. 创建数据目录
mkdir -p data/train data/val output

# 3. 下载LLM_Data
cp -r /mnt/f/StarWhisper-main/StarWhisper-main/LLM_Data ./LLM_Data

# 4. 运行模型测试
cd src/spectral_lm
python -c "
from model_architecture import SpectrumDiffusionModel
import torch
model = SpectrumDiffusionModel()
x = torch.randint(1, 84, (2, 128))
logits, loss = model(x, mode='AR')
print(f'Model test passed! Loss: {loss.item():.4f}')
"

# 5. 运行预处理脚本测试
cd ../..
python scripts/preprocess_data.py --help
```

#### 验证标准
- [ ] Python环境无报错
- [ ] PyTorch CUDA可用
- [ ] 模型可正常初始化
- [ ] 预处理脚本可执行

### 6.2 Phase 2: 小规模预训练 (Day 3-7)

#### 目标
- 使用小数据集验证训练流程
- 调优超参数

#### 配置

```yaml
# config/pretrain_small.yaml
model:
  vocab_size: 84
  n_embd: 256
  n_head: 8
  n_layer: 6
  block_size: 4096
  cond_dim: 128

training:
  batch_size: 4
  learning_rate: 1e-4
  warmup_steps: 100
  total_steps: 10000
  gradient_accumulation: 4
  max_grad_norm: 1.0
  weight_decay: 0.01

data:
  train_path: ./data/train
  val_path: ./data/val
  num_workers: 4

output:
  checkpoint_dir: ./output/checkpoints
  log_dir: ./output/logs
```

#### 执行命令

```bash
# 单GPU训练
python scripts/pretrain.py \
    --config config/pretrain_small.yaml \
    --device cuda:0

# 多GPU训练
python -m torch.distributed.launch \
    --nproc_per_node=4 \
    scripts/pretrain.py \
    --config config/pretrain_small.yaml \
    --device cuda
```

#### 验证标准
- [ ] 训练loss持续下降
- [ ] Validation loss同步下降
- [ ] GPU利用率 > 60%
- [ ] 无OOM错误

### 6.3 Phase 3: 全量预训练 (Day 8-30)

#### 目标
- 使用完整数据集预训练
- 生成高质量光谱模型

#### 配置

```yaml
# config/pretrain_full.yaml
model:
  vocab_size: 84
  n_embd: 256
  n_head: 8
  n_layer: 6
  block_size: 12288
  cond_dim: 128

training:
  batch_size: 8
  learning_rate: 1e-4
  warmup_steps: 1000
  total_steps: 100000
  gradient_accumulation: 8
  max_grad_norm: 1.0
  weight_decay: 0.01
  early_stopping_patience: 7

data:
  train_path: ./data/train
  val_path: ./data/val
  num_workers: 8

distributed:
  backend: nccl
  world_size: 4

output:
  checkpoint_dir: ./output/checkpoints_full
  log_dir: ./output/logs_full
  save_interval: 5000
```

#### 执行命令

```bash
# 8 GPU集群训练
python -m torch.distributed.launch \
    --nproc_per_node=8 \
    --master_port=29500 \
    scripts/pretrain.py \
    --config config/pretrain_full.yaml \
    --device cuda
```

#### 中期检查点
- Step 25000: 评估模型生成质量
- Step 50000: 保存checkpoint，评估
- Step 75000: 最终评估

### 6.4 Phase 4: 光谱微调 (Day 31-45)

#### 目标
- 使用LAMOST数据微调
- 适应实际观测光谱

#### 执行流程

```bash
# 1. 准备LAMOST微调数据
python code/lamost_sft_data/convert_lamost_to_pretrain_format.py \
    --input /path/to/lamost_flux.csv \
    --catalog /path/to/dr12_catalog.csv \
    --output ./data/lamost_finetune.csv

# 2. 运行微调
python scripts/finetune.py \
    --pretrained_path ./output/checkpoints_full/pretrain_step_100000.pt \
    --config config/finetune_lamost.yaml \
    --data ./data/lamost_finetune.csv \
    --output_dir ./output/finetune_lamost
```

#### SNR课程学习

按论文建议的SNR阶段微调：

| 阶段 | SNR范围 | 序列长度 | 轮次 |
|------|---------|----------|------|
| Stage 1 | 25-30 | ~3030 | 5 |
| Stage 2 | 9-11 | ~303 | 10 |
| Stage 3 | 7-9 | ~303 | 10 |

### 6.5 Phase 5: 光变曲线分类 (Day 46-60)

#### 目标
- 训练StarWhisper_LC分类模型

#### 模型选择

| 模型 | 参数量 | 适用场景 |
|------|--------|----------|
| EfficientNet-B0 | ~5M | 快速原型 |
| ConvNeXt-Tiny | ~28M | 平衡性能 |
| Swin-T | ~28M | 高精度 |
| LSTM+Attention | ~10M | 时序分析 |

#### 执行命令

```bash
# EfficientNet训练
cd StarWhisper_LC/Code
python CNN.py --data_dir ../data --model efficientnet-b0 --epochs 50

# ConvNeXt训练
python Convnext.py --data_dir ../data --model convnext_tiny --epochs 50

# LSTM训练
python lstm+attention.py --data_dir ../data --model lstm_attn --epochs 50
```

### 6.6 Phase 6: Agent集成 (Day 61-75)

#### 目标
- 集成NGSS望远镜控制Agent
- 实现观测自动化

#### 组件

| 组件 | 文件 | 功能 |
|------|------|------|
| 观测计划 | PlanObservation3.py | 生成观测计划 |
| 暂现检测 | transientDetection.py | 响应暂现源 |
| 数据管道 | Data_pipeline.py | 图像数据处理 |
| UDP通信 | UdpConnect.py | 望远镜控制 |

---

## 7. 验证与评估

### 7.1 模型质量评估

#### 7.1.1 光谱生成质量

**指标**:
- Flux RMSE (均方根误差)
- Spectral Angle Mapper (SAM)
- 物理参数预测精度 (Teff, logg, [Fe/H])

**评估脚本**:
```python
# eval_spectrum.py
import torch
from model_architecture import SpectrumDiffusionModel

def evaluate_generation(model, test_data, device='cuda'):
    model.eval()
    with torch.no_grad():
        # 生成样本
        generated = model.generate_parallel(initial_tokens, num_steps=64)
        
        # 计算指标
        rmse = compute_flux_rmse(generated, test_data)
        sam = compute_sam(generated, test_data)
        
        # 参数预测
        pred_params, _ = model(test_data, mode='param_prediction')
        param_rmse = compute_param_rmse(pred_params, true_params)
    
    return {'rmse': rmse, 'sam': sam, 'param_rmse': param_rmse}
```

#### 7.1.2 低SNR性能

测试不同SNR水平下的生成质量：

| SNR | 目标RMSE | 验收标准 |
|-----|----------|----------|
| >30 | <0.05 | 优秀 |
| 10-30 | <0.10 | 良好 |
| 5-10 | <0.20 | 可接受 |
| <5 | <0.30 | 最低标准 |

### 7.2 训练过程监控

#### 7.2.1 Weights & Biases集成

```python
# wandb_config
wandb:
  project: starwhisper-reproduction
  entity: your-username
  name: pretrain-full-run
```

```bash
# 启动wandb监控
export WANDB_API_KEY="your-api-key"
python scripts/pretrain.py --use_wandb --config config/pretrain_full.yaml
```

#### 7.2.2 本地日志

```bash
# 日志目录结构
output/
├── logs/
│   ├── pretrain_20260503_143022.log
│   └── finetune_20260510_090012.log
├── checkpoints/
│   ├── pretrain_step_001000.pt
│   ├── pretrain_step_005000.pt
│   └── pretrain_step_010000.pt
└── tensorboard/
    ├── events.out.tfevents.1234567890
```

### 7.3 复现验收清单

| 阶段 | 验收项 | 标准 | 状态 |
|------|--------|------|------|
| P1 | Demo运行 | 无报错 | [ ] |
| P1 | 模型初始化 | 参数正常 | [ ] |
| P2 | 小规模训练 | Loss下降 | [ ] |
| P2 | 全量预训练 | RMSE<0.10 | [ ] |
| P2 | LAMOST微调 | RMSE<0.08 | [ ] |
| P2 | SNR>10生成 | 物理合理 | [ ] |
| P3 | 光变分类 | Acc>85% | [ ] |
| P3 | Agent集成 | 功能可用 | [ ] |

---

## 8. 风险评估与备选方案

### 8.1 高风险项

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|----------|
| GPU显存不足 | 中 | 高 | 降低batch_size，使用gradient checkpointing |
| 数据下载受阻 | 低 | 高 | 使用代理，预下载数据 |
| 训练不稳定 | 中 | 中 | 调整学习率，增加warmup |
| OOM错误 | 中 | 高 | 启用梯度累积，降低block_size |
| 版本兼容性 | 低 | 中 | 固定PyTorch版本 |

### 8.2 备选方案

#### 8.2.1 显存不足

```yaml
# 低显存配置
training:
  batch_size: 2        # 从8降到2
  gradient_accumulation: 16  # 增加累积
  use_gradient_checkpointing: true  # 启用

model:
  block_size: 4096      # 从12288降到4096
```

#### 8.2.2 使用HuggingFace权重

如果自训练成本过高，可直接使用预训练权重：

```python
from huggingface_hub import hf_hub_download
import torch

# 下载权重
model_path = hf_hub_download(
    repo_id="Jaredxjc/Low-SNR-Stellar-Spectra-as-Language",
    filename="pretrain.pt"
)

# 加载
model = SpectrumDiffusionModel()
state_dict = torch.load(model_path, map_location='cpu')
model.load_state_dict(state_dict)
```

#### 8.2.3 数据不足

如果LAMOST数据获取困难：
1. 使用PHOENIX合成数据为主
2. 申请LAMOST公开样本
3. 使用其他公开光谱数据 (BOSS, SDSS)

---

## 9. 时间规划

### 9.1 详细甘特图

```
Week 1: 环境搭建 + Demo验证
├─ Day 1-2: 环境配置
├─ Day 3-4: 代码研究
└─ Day 5-7: Demo运行

Week 2-3: 小规模训练
├─ Day 8-10: 数据准备
├─ Day 11-14: 小规模训练
└─ Day 15: 结果评估

Week 4-6: 全量预训练
├─ Day 16-20: 全量数据准备
├─ Day 21-35: 全量预训练
└─ Day 36: 中期评估

Week 7-8: LAMOST微调
├─ Day 37-42: LAMOST数据处理
├─ Day 43-49: Stage 1微调 (高SNR)
└─ Day 50-56: Stage 2-3微调 (低SNR)

Week 9-10: 光变曲线分类
├─ Day 57-63: 模型训练
└─ Day 64-70: 评估优化

Week 11: Agent集成
└─ Day 71-75: NGSS集成测试

Buffer: 1周 (Day 76-82)
Total: 12周 (约3个月)
```

### 9.2 里程碑

| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| M1 | Day 7 | 环境可用，Demo运行 |
| M2 | Day 14 | 小规模模型验证 |
| M3 | Day 35 | 全量预训练checkpoint |
| M4 | Day 56 | 微调完成模型 |
| M5 | Day 70 | 分类模型可用 |
| M6 | Day 82 | 完整pipeline |

---

## 10. 资源需求汇总

### 10.1 计算资源

| 阶段 | GPU需求 | 显存 | 时间 | GPU-hours |
|------|---------|------|------|------------|
| Demo | 1x RTX3090 | 24GB | 1小时 | ~1 |
| 小规模 | 1x A100 | 40GB | 1天 | ~100 |
| 全量预训练 | 4x A100 | 160GB | 3周 | ~20,000 |
| 微调 | 1x A100 | 40GB | 2周 | ~3,000 |
| 分类训练 | 1x RTX3090 | 24GB | 3天 | ~200 |
| **总计** | | | ~5周 | ~23,300 |

### 10.2 存储资源

| 数据类型 | 大小 | 说明 |
|----------|------|------|
| 代码 | 100MB | Git仓库 |
| PHOENIX | 50GB | FTP下载 |
| LAMOST | 100GB | 需申请 |
| 训练输出 | 50GB | Checkpoints |
| 中间数据 | 200GB | 处理过程 |
| **总计** | ~400GB | |

### 10.3 人力资源

| 角色 | 工作量 | 说明 |
|------|--------|------|
| 工程师 | 1 FTE | 全程参与 |
| 算法专家 | 0.2 FTE | 关键节点咨询 |
| 运维 | 0.1 FTE | 集群支持 |

### 10.4 预算估算

| 项目 | 单价 | 数量 | 总价 |
|------|------|------|------|
| A100 GPU (云) | $3.5/GPU-hour | 23,000 hours | $80,500 |
| 存储 (云) | $0.1 GB/month | 400GB x 6月 | $240 |
| 网络 | $50/month | 6月 | $300 |
| **总计** | | | **~$81,000** |

---

## 附录

### A. 参考资料

1. **StarWhisper GitHub**: https://github.com/Yu-Yang-Li/StarWhisper
2. **HuggingFace权重**: https://huggingface.co/Jaredxjc/Low-SNR-Stellar-Spectra-as-Language
3. **AO-GPT-MDM论文**: Any-Order GPT as Masked Diffusion Model
4. **LAMOST DR12**: https://www.lamost.org/dr12/
5. **PHOENIX光谱**: https://phoenix.astro.physik.uni-goettingen.de/

### B. 关键脚本路径

```bash
# 模型测试
cd StarWhisper/Low-SNR-Stellar-Spectra-as-Language
python src/spectral_lm/model_architecture.py

# 预训练
python scripts/pretrain.py --config config/pretrain.yaml

# 微调
python scripts/finetune.py --pretrained_path PATH --data DATA

# 数据预处理
python scripts/preprocess_data.py --input DATA --output_dir ./data
```

### C. 联系方式

如有问题，请在StarWhisper GitHub仓库提Issue：
https://github.com/Yu-Yang-Li/StarWhisper/issues

---

*计划版本: v1.0*
*创建日期: 2026-05-03*
*作者: Hermes Agent for 天问-AGI*
