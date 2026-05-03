# PRO文档: Ollama本地LLM集成 v1.0

**项目**: Tianwen-AGI
**日期**: 2026-05-01
**状态**: ✅ 已完成
**优先级**: P0 (核心依赖)

---

## 一、概述

### 1.1 目标
将Ollama本地LLM推理框架集成到Tianwen-AGI推理引擎，支持多种开源模型在本地运行，减少对外部API的依赖。

### 1.2 背景
- 当前Tianwen-AGI依赖外部LLM API
- 网络中断将导致系统无法工作
- 用户已安装Ollama (路径: C:\Users\22140\AppData\Local\Programs\Ollama)
- 需要实现本地模型fallback机制

---

## 二、技术方案

### 2.1 Ollama简介
- 官网: https://ollama.com
- 支持模型: Llama2, Mistral, Qwen2.5, Solar等
- API端点: http://localhost:11434
- 兼容OpenAI格式 (部分)

### 2.2 支持的模型 (通过Ollama)

| 模型 | 参数量 | 内存需求 | 适用场景 |
|------|--------|---------|---------|
| llama2 | 7B | 8GB | 通用对话 |
| mistral | 7B | 8GB | 通用推理 |
| qwen2.5 | 7B | 8GB | 中文优化 |
| solar | 10.7B | 12GB | 性能优先 |

### 2.3 架构设计

```
ReasoningEngine
├── QwenAdapter (远程API)
├── DeepSeekAdapter (远程API)
└── OllamaAdapter (本地模型) ← 新增
    ├── chat() - 对话接口
    ├── think() - 推理接口
    ├── analyze() - 分析接口
    └── list_models() - 列出可用模型

ModelConfig.ollama(model, endpoint) - 工厂方法
```

---

## 三、代码变更

### 3.1 新增OllamaAdapter类
```python
class OllamaAdapter(BaseAdapter):
    """Ollama本地LLM适配器"""
    def __init__(self, config: ModelConfig):
        self.client = httpx.AsyncClient(timeout=120.0)

    async def think(self, prompt, system_prompt, max_tokens, temperature, thinking)
    async def analyze(self, content, analysis_type)
    @staticmethod
    def list_models(endpoint) -> List[Dict]
```

### 3.2 ModelConfig工厂方法
```python
@classmethod
def ollama(cls, model: str = "llama2", endpoint: str = "http://localhost:11434"):
    return cls(name=model, endpoint=endpoint, model_type="ollama")
```

### 3.3 ReasoningEngine更新
- 添加 `self.ollama: Optional[OllamaAdapter]`
- `configure()` 新增 `ollama_config` 参数
- `think()` 新增 force_model="ollama"
- 模型选择优先级调整: LOW复杂度优先使用Ollama

---

## 四、使用方法

### 4.1 基础用法
```python
from reasoning_engine import ReasoningEngine, ModelConfig

engine = ReasoningEngine()
await engine.configure(
    ollama_config=ModelConfig.ollama("llama2", "http://localhost:11434")
)

# 自动选择模型 (根据复杂度)
result = await engine.think("太阳系有几个行星？")

# 强制使用Ollama
result = await engine.think("问题", force_model="ollama")
```

### 4.2 列出可用模型
```python
models = OllamaAdapter.list_models("http://localhost:11434")
# [{'name': 'llama2', 'size': 3826793565}, ...]
```

---

## 五、验证清单

| 验证项 | 状态 | 说明 |
|--------|------|------|
| Ollama服务运行 | ⏳ 待验证 | curl http://localhost:11434 |
| 本地模型推理 | ⏳ 待验证 | python -m reasoning_engine |
| Fallback机制 | ⏳ 待验证 | Ollama不可用时切换 |

---

## 六、依赖

无新增依赖 - 使用httpx (已有)

---

## 七、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| Ollama未启动 | 实现API fallback到远程模型 |
| 模型未下载 | 提示用户运行 `ollama pull llama2` |
| 内存不足 | 选择更小的模型 (7B) |

---

**文档状态**: ✅ 完成
**变更文件**:
- runtime/reasoning_engine.py (已修改)