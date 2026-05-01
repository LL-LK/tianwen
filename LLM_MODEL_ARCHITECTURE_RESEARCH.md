# LLM Model Architecture Research - 2026-05-01

## 1. Mixture of Experts (MoE) Architectures

### Key Projects

| Project | GitHub | Stars | Description |
|---------|-------|-------|-------------|
| Grok-1 | xai-org/grok-1 | 50k+ | 314B MoE model |
| Mixtral 8x7B | mistralai/mistral-src | 20k+ | 8 experts, 2 active per token |
| DeepSeek-V2 | deepseek-ai/DeepSeek-V2 | 15k+ | 236B, aux-loss-free balancing |
| Qwen-MoE | QwenLM/Qwen | 30k+ | Alibaba MoE variants |

### MoE Architecture

```
Standard Transformer: x → Attention → FFN → output
MoE Transformer:      x → Attention → MoE(x) → output
  where MoE(x):
    router(x) = Softmax(W_r · x)
    top_k = SelectTopK(router, k)
    output = Σ_i(top_k[i] · Expert_i(x))
```

## 2. Multi-Model Coexistence Systems

| Project | Stars | Description |
|---------|-------|-------------|
| LlamaIndex | 30k+ | Multi-model composition and routing |
| LangGraph | 20k+ | Dynamic model selection |
| AutoGen | 30k+ | Microsoft multi-agent conversation |
| CrewAI | 15k+ | Role-based agent assignment |

## 3. Model Routing & Orchestration

| Project | Stars | Description |
|---------|-------|-------------|
| vLLM | 35k+ | PagedAttention, dynamic batching |
| TGI | 10k+ | HuggingFace inference server |
| LitServe | 8k+ | Flexible routing |

## 4. Dynamic Model Loading

| Project | Stars | Description |
|---------|-------|-------------|
| llama.cpp | 60k+ | GGUF format, CPU/GPU hybrid |
| ExLlamaV2 | 5k+ | Advanced quantization |

## 5. Model Fusion Techniques

| Tool | Stars | Purpose |
|------|-------|---------|
| mergekit | 3k+ | Model merging toolkit |
| LLMmerge | 500+ | Weight averaging |

## 6. Key Research Papers

1. "Mixtral of Experts" - arXiv:2401.04088
2. "DeepSeek-V2" - Improved MoE with aux-loss-free balancing
3. "Model Soup" - arXiv:2303.05499
4. "Task Arithmetic" - arXiv:2212.04089

## 7. Summary

| Category | Top Projects | Stars |
|----------|--------------|-------|
| MoE | Grok-1, Mixtral, DeepSeek-V2 | 50k, 20k, 15k |
| Routing | vLLM, TGI, LangGraph | 35k, 10k, 20k |
| Dynamic Loading | llama.cpp, ExLlamaV2 | 60k, 5k |
| Fusion | mergekit | 3k+ |
| Multi-model | LlamaIndex, AutoGen, CrewAI | 30k, 30k, 15k |
