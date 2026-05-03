# Vector Memory Semantic Search - Implementation Proposal

## Summary

Implemented `get_similar_experiences()` method for semantic similarity search in vector memory, enabling improved context retrieval for task execution.

## Background

The Tianwen-AGI system has vector-based memory stores (`SimpleVectorStore`) in both `vector_memory.py` and `memory_persistence.py`. While `VectorMemory.search_similar_experiences()` exists, the `PersistentMemory` class lacked a dedicated semantic similarity search method for task context retrieval. This limits the RAG (Retrieval Augmented Generation) capabilities.

## Changes Made

### File: `runtime/memory_persistence.py`

Added `get_similar_experiences(query, k, min_score)` method to `PersistentMemory`:

```python
def get_similar_experiences(self, query: str, k: int = 5, min_score: float = 0.5) -> List[Dict]:
    """
    获取语义相似的经验用于任务上下文检索

    Args:
        query: 查询文本（任务描述、问题或需求）
        k: 返回结果数量
        min_score: 最小相似度分数阈值

    Returns:
        List[Dict]: 相似经验列表，包含task_description、solution、skills_used等
    """
```

Features:
- Uses `all-MiniLM-L6-v2` embeddings via `SentenceTransformer`
- Cosine similarity scoring with configurable threshold (`min_score=0.5`)
- Returns formatted results including `task_description`, `solution`, `skills_used`, `type`, `outcome`, `score`, `id`
- Results sorted by similarity score (descending)
- Fallback to text search when embedder not loaded

Also added `get_similar_experiences()` wrapper to `MemoryIntegratedAgent`.

## Technical Details

### Embedding Model
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Loaded via `sentence_transformers.SentenceTransformer`

### Similarity Calculation
- Cosine similarity: `dot(a,b) / (norm(a) * norm(b))`
- Score range: 0.0 to 1.0 (1.0 = identical)

### Threshold
- Default `min_score=0.5` filters low-similarity results
- Can be adjusted per use case

## Usage Example

```python
from runtime.memory_persistence import PersistentMemory

memory = PersistentMemory(memory_dir="./memory")

# 记录经验
memory.record_success(
    task="使用CNN进行星系形态分类",
    solution="使用ResNet50预训练模型+迁移学习",
    skills=["DeepLearning", "ComputerVision"],
)

# 获取相似经验
similar = memory.get_similar_experiences(
    query="图像分类任务", k=5, min_score=0.5
)
for exp in similar:
    print(f"Score: {exp['score']:.3f}")
    print(f"Task: {exp['task_description']}")
    print(f"Solution: {exp['solution']}")
```

## Integration with RAG

The method integrates with the existing RAG pipeline:

1. **Context Retrieval**: When processing a task, `get_similar_experiences()` retrieves relevant past experiences
2. **Skill Suggestion**: Returns `skills_used` from similar successful tasks
3. **Solution Hints**: Returns `solution` text from similar experiences
4. **Fallback**: Works without embedder via simple text matching

## Dependencies

- `sentence-transformers>=2.2.0`
- `numpy>=1.21.0`
- `torch>=1.9.0` (optional, for better embedding quality)

## Open Questions / Future Work

1. **Cross-encoder reranking**: Implement `search_similar_experiences()` with cross-encoder for more precise ranking
2. **Hybrid search**: Combine semantic similarity with keyword matching for better recall
3. **Experience pruning**: Add decay mechanism to reduce weight of old experiences
4. **ChromaDB integration**: Leverage `vector_rag.py`'s `ChromaVectorStore` for scalability
5. **BM25 ranking**: Add sparse retrieval complement to dense semantic search
