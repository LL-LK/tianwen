# PRO审计文档: P2-1 vLLM推理优化
**审计时间**: 2026-05-01 15:25 CST (北京时间)
**优先级**: P2 (中期)
**关联Issue**: #31

---

## 一、现状分析

### 1.1 代码审查结果

| 文件 | 状态 | 说明 |
|------|------|------|
| requirements.txt | ⚠️ 无vLLM | 未列出vLLM依赖 |
| runtime/ | ⚠️ 无vLLM | 无vLLM相关代码 |
| GPU配置 | ❌ 未验证 | 需检查CUDA环境 |

### 1.2 vLLM简介

**vLLM**: 高吞吐量LLM推理引擎
- PagedAttention技术
- 支持FasterTransformer后端
- 吞吐量提升2-10倍

### 1.3 用户硬件配置

| 硬件 | 规格 |
|------|------|
| GPU | AMD Radeon 780M (RDNA3) |
| CPU | AMD Ryzen 7 8745H |
| 内存 | 19.8GB |

**问题**: AMD GPU需要ROCm支持，vLLM主要支持NVIDIA CUDA

---

## 二、技术挑战

### 2.1 AMD GPU支持

**vLLM对AMD GPU的支持**:
- vLLM 0.2+ 开始支持AMD ROCm
- 需要 `pip install vllm --index-url https://wheels.rapids.ai/`
- RDNA3架构 (780M) 需要较新ROCm版本

### 2.2 替代方案

| 方案 | AMD支持 | 性能 | 难度 |
|------|---------|------|------|
| vLLM (ROCm) | ⚠️ 实验性 | 高 | 高 |
| Ollama | ✅ 成熟 | 中 | 低 |
| llama.cpp | ✅ 成熟 | 中 | 低 |
| Text Generation Inference | ⚠️ 部分 | 高 | 中 |

---

## 三、实施计划

### 3.1 条件依赖

| 前置条件 | 状态 | 说明 |
|---------|------|------|
| AMD ROCm安装 | ❌ 未验证 | 需要验证 |
| 足够VRAM | ⚠️ 780M=16GB | 7B模型可运行 |
| vLLM AMD构建 | ⚠️ 实验性 | 可能有兼容问题 |

### 3.2 推荐路径

**方案A: Ollama优先 (推荐)**
```bash
# 用户AMD GPU支持好
ollama pull llama2
# 使用Ollama API进行推理
```

**方案B: llama.cpp**
```python
# 使用ctransformers或llama-cpp-python
from llama_cpp import Llama
model = Llama(model_path="./models/llama-7b.gguf")
```

### 3.3 验证清单

| 验证项 | 预期结果 |
|--------|---------|
| ROCm可用 | `rocminfo` 或 `rocm-smi` |
| vLLM安装成功 | pip install vllm |
| 模型推理 | 成功生成响应 |

---

## 四、文献来源

| 项目 | URL | 说明 |
|------|-----|------|
| vLLM | https://github.com/vllm-project/vllm | 高吞吐量LLM推理 |
| vLLM AMD ROCm | https://docs.vllm.ai/en/latest/serving/amd.html | AMD GPU支持 |
| Ollama AMD | https://github.com/ollama/ollama | 本地LLM推理 |

---

## 五、审计结论

| 维度 | 评估 |
|------|------|
| 当前状态 | ❌ 无vLLM实现 |
| 技术可行性 | ⚠️ AMD GPU有限支持 |
| 实施难度 | 高 - ROCm兼容性 |
| 优先级 | P2 - 中期目标 |

**建议**:
1. 优先使用Ollama (更好的AMD支持)
2. vLLM作为NVIDIA GPU备选
3. 验证AMD ROCm环境后再决定

---

**审计状态**: ✅ 完成
**审计人**: Hermes Agent (产品经理视角)
**待办**: 验证AMD ROCm环境 → 决定最终方案
