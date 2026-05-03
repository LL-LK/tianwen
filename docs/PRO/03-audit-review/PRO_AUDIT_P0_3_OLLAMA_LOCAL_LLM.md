# PRO审计文档: P0-3 Ollama本地LLM集成减少API依赖
**审计时间**: 2026-05-01 14:58 CST (北京时间)
**优先级**: P0 (立即行动)
**关联Issue**: #31

---

## 一、现状分析

### 1.1 代码审查结果

| 文件 | 行数 | 状态 | 问题 |
|------|------|------|------|
| multi_agent_coordinator.py | 1575 | ⚠️ 框架完整 | 无LLM API调用 |
| agent.md | 185 | ⚠️ 架构定义 | 依赖外部API |
| runtime/models/ | - | ⚠️ 仅视觉模型 | 无LLM模型 |

### 1.2 当前架构问题

**问题1: 无本地LLM支持**
```python
# multi_agent_coordinator.py 只有框架，无实际LLM调用
# ResearchAgent只有对话历史存储，没有实际模型调用
class ResearchAgent:
    conversation_history: List[Dict] = field(default_factory=list)

    def add_message(self, role: str, content: str, ...):
        # 只存储对话，不调用LLM
        self.conversation_history.append({...})
```

**问题2: 完全依赖外部API**
- 当前架构依赖外部LLM API
- 无本地模型推理能力
- 网络中断将导致系统瘫痪

**问题3: models/目录只有视觉模型**
```
runtime/models/
├── resnet50_astro_classifier.pth    (104MB)
└── yolo11s_astro_detection.pt        (21MB)
```
无任何LLM模型文件。

---

## 二、技术方案

### 2.1 Ollama介绍

**Ollama**: 本地LLM推理框架
- 官网: https://ollama.com
- GitHub: https://github.com/ollama/ollama
- 支持模型: Llama 2, Mistral, Vicuna, Qwen等
- API兼容OpenAI格式

### 2.2 Ollama优势

| 特性 | 外部API | Ollama本地 |
|------|---------|------------|
| 成本 | 按token计费 | 一次性硬件成本 |
| 延迟 | 取决于网络 | 本地无网络延迟 |
| 隐私 | 数据上传云端 | 完全本地处理 |
| 可用性 | 依赖网络 | 完全独立 |
| 定制 | 受限 | 可微调自定义 |

### 2.3 推荐模型

| 模型 | 参数量 | 内存需求 | 适用场景 |
|------|--------|---------|---------|
| llama2 | 7B | 8GB | 通用对话 |
| mistral | 7B | 8GB | 通用推理 |
| qwen2.5 | 7B | 8GB | 中文优化 |
| solar | 10.7B | 12GB | 性能优先 |

### 2.4 集成架构

```python
# 新建 runtime/llm_client.py
import ollama

class OllamaLLMClient:
    """Ollama本地LLM客户端"""

    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=base_url)

    async def chat(self, messages: List[Dict]) -> str:
        """聊天接口 - 兼容OpenAI格式"""
        response = self.client.chat(model=self.model, messages=messages)
        return response['message']['content']

    async def complete(self, prompt: str, max_tokens: int = 512) -> str:
        """补全接口"""
        response = self.client.generate(model=self.model, prompt=prompt)
        return response['response']
```

---

## 三、实施计划

### 3.1 立即行动 (1-3天)

| 步骤 | 行动 | 说明 |
|------|------|------|
| 1 | 安装Ollama | `curl -fsSL https://ollama.com/install.sh` |
| 2 | 下载模型 | `ollama pull llama2` |
| 3 | 创建llm_client.py | 实现Ollama客户端 |
| 4 | 修改multi_agent_coordinator | 集成本地LLM |
| 5 | 添加fallback机制 | API不可用时切换 |

### 3.2 验证清单

| 验证项 | 预期结果 |
|--------|---------|
| Ollama服务启动 | `curl http://localhost:11434` 返回版本 |
| 模型推理 | 成功生成文本响应 |
| Fallback机制 | API恢复后自动切换 |
| 性能对比 | 响应时间改善 |

---

## 四、文献来源

| 项目 | URL | 说明 |
|------|-----|------|
| Ollama官网 | https://ollama.com | 官方安装和使用 |
| Ollama GitHub | https://github.com/ollama/ollama | 开源项目 |
| Ollama模型库 | https://ollama.com/library | 可用模型列表 |

---

## 五、用户环境信息

| 项目 | 值 |
|------|---|
| Ollama安装路径 | C:\Users\22140\AppData\Local\Programs\Ollama |
| WSL访问路径 | /mnt/c/Users/22140/AppData/Local/Programs/Ollama |

## 六、审计结论

| 维度 | 评估 |
|------|------|
| 当前状态 | ❌ 无本地LLM，完全依赖外部API |
| 技术可行性 | ✅ Ollama已安装，只需集成 |
| 实施难度 | 低 - 框架已存在，Ollama已就绪 |
| 优先级 | P0 - 独立闭环核心依赖 |

**建议**:
1. Ollama已在用户机器安装，立即可用
2. 创建统一的LLM客户端接口
3. 实现API fallback机制
4. 优先用于简单推理任务

---

**审计状态**: ✅ 完成
**审计人**: Hermes Agent (产品经理视角)
**待办**: 等待Claude实现或指示
