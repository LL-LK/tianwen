# PRO审计文档: P1-2 ChromaDB RAG本地文献增强
**审计时间**: 2026-05-01 15:12 CST (北京时间)
**优先级**: P1 (重要)
**关联Issue**: #31

---

## 一、现状分析

### 1.1 代码审查结果

| 文件 | 行数 | 状态 | 问题 |
|------|------|------|------|
| vector_rag.py | 795 | ⚠️ 框架完整 | 依赖可能未安装 |
| vector_memory.py | 795 | ⚠️ 框架完整 | 使用SimpleVectorStore替代 |
| literature_researcher.py | 84576字节 | ❌ 未集成 | 未使用任何RAG模块 |

### 1.2 当前架构问题

**问题1: ChromaDB依赖未安装**
```python
# vector_rag.py
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False  # ← 可能为False
```

**问题2: 未与literature_researcher集成**
```python
# literature_researcher.py - 没有导入vector_rag或vector_memory
# 这意味着文献调研没有RAG增强功能
```

**问题3: 使用SimpleVectorStore替代**
```python
# vector_memory.py
class SimpleVectorStore:
    """简单的向量存储实现 - 基于余弦相似度"""
    # 这是一个基础实现，功能有限
```

### 1.3 期望 vs 实际

| 期望功能 | 实际状态 |
|---------|---------|
| ChromaDB向量存储 | 使用SimpleVectorStore |
| sentence-transformers嵌入 | 有代码但可能未安装 |
| RAG增强文献调研 | 未集成 |
| 本地文献检索 | 只有基础搜索 |

---

## 二、技术方案

### 2.1 推荐架构

**完整ChromaDB RAG架构**:
```
文献输入 → 分块 → sentence-transformers嵌入 → ChromaDB存储
                                                    ↓
用户查询 → 嵌入 → ChromaDB相似性检索 → 上下文组装 → LLM生成
```

### 2.2 实施步骤

**方案A: 完整ChromaDB集成 (推荐)**
```bash
pip install chromadb sentence-transformers
```

```python
# literature_researcher.py 新增
from vector_rag import ChromaRAGClient

class LiteratureResearcher:
    def __init__(self):
        self.rag = ChromaRAGClient()

    async def research_with_rag(self, query: str):
        # RAG增强的文献调研
        results = await self.rag.search(query, top_k=10)
        context = self._build_context(results)
        return await self.llm.generate(context + query)
```

**方案B: 增强SimpleVectorStore (备选)**
```python
# 改进vector_memory.py的SimpleVectorStore
# 添加持久化、更快的相似性搜索
```

---

## 三、实施计划

### 3.1 立即行动 (2-3天)

| 步骤 | 行动 | 说明 |
|------|------|------|
| 1 | 安装依赖 | pip install chromadb sentence-transformers |
| 2 | 验证ChromaDB | import chromadb; client = chromadb.Client() |
| 3 | 集成到literature_researcher | 添加RAG搜索方法 |
| 4 | 索引现有文献 | 对LITERATURE.md等内容建立向量索引 |
| 5 | 测试RAG效果 | 对比有无RAG的搜索结果质量 |

### 3.2 验证清单

| 验证项 | 预期结果 |
|--------|---------|
| ChromaDB安装成功 | import chromadb 无报错 |
| sentence-transformers安装 | from sentence_transformers import SentenceTransformer |
| literature_researcher集成 | research_with_rag()方法可用 |
| 向量索引创建 | 现有文献成功建立索引 |
| RAG搜索效果 | 语义相似结果优于关键词搜索 |

---

## 四、文献来源

| 项目 | URL | 说明 |
|------|-----|------|
| ChromaDB | https://www.trychroma.com/ | 向量数据库 |
| sentence-transformers | https://github.com UKPLab/sentence-transformers | 句子嵌入模型 |
| ChromaDB GitHub | https://github.com/chroma-core/chroma | 开源向量数据库 |

---

## 五、审计结论

| 维度 | 评估 |
|------|------|
| 当前状态 | ⚠️ RAG框架存在但未集成 |
| 技术可行性 | ✅ ChromaDB成熟，方案清晰 |
| 实施难度 | 低 - 只需安装依赖并集成 |
| 优先级 | P1 - 重要但可延后 |

**建议**:
1. 安装完整ChromaDB依赖
2. 将vector_rag集成到literature_researcher
3. 优先对LITERATURE.md建立向量索引
4. 验证RAG搜索效果

---

**审计状态**: ✅ 完成
**审计人**: Hermes Agent (产品经理视角)
**待办**: 等待Claude实现或指示
