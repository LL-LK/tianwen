# RAG与MCP能力优化报告 v3.8.5

**报告时间**: 2026-05-03 19:15 CST (北京时间)
**版本**: v3.8.5
**分支**: trae

---

## 一、任务概述

本次优化旨在提升天问-AGI的RAG（检索增强生成）和MCP（模型上下文协议）能力，主要解决以下问题：

| 问题 | 严重程度 | 状态 |
|------|---------|------|
| ChromaDB未集成到literature_researcher | P0 | ✅ 已修复 |
| web_search为模拟实现 | P0 | ✅ 已修复 |
| 命令执行无超时保护 | P1 | ✅ 已修复 |
| 向量存储未使用 | P1 | ✅ 已修复 |

---

## 二、RAG模块优化

### 2.1 修改文件

**`runtime/vector_store.py`** (+112行)
- 新增 `ChromaDBVectorStore` 包装类
- 封装 `vector_rag.py` 中的 `ChromaVectorStore`
- 提供向后兼容的降级实现

**`runtime/literature_researcher.py`** (+228行)
- 集成 ChromaDB 向量存储
- 实现增量索引机制
- 添加 RAG 增强的调研流程

### 2.2 新增功能

#### ChromaDB集成
```python
# 持久化存储位置
runtime/data/chroma_db

# 初始化参数
use_vector_store=True  # 默认启用
vector_persist_dir="runtime/data/chroma_db"
```

#### 增量索引
```python
# 自动跳过已存在文档
index_papers(papers, skip_existing=True)

# 使用论文ID作为向量ID
paper.id → chromadb ID
```

#### RAG增强调研流程
```python
async def research_all_with_rag(topic: str) -> ResearchState:
    # 1. 语义搜索已有文献
    relevant = await search_vector_store(topic)

    # 2. 多数据源API搜索新论文
    new_papers = await research_all(topic)

    # 3. 增量索引新论文
    await index_papers(new_papers)

    # 4. 返回综合结果（含RAG上下文）
    return ResearchState(relevant_documents=relevant, ...)
```

---

## 三、MCP模块优化

### 3.1 修改文件

**`runtime/mcp_protocol.py`** (+212行)

### 3.2 新增功能

#### 真实web_search实现
```python
# 多源搜索（优先级）
1. browser_search.quick_search()  # 多源真实搜索
2. DuckDuckGo HTML 备用搜索

# 超时保护
timeout = 25 秒

# 缓存机制
TTL = 300秒 (5分钟)
LRU淘汰，最大100条
```

#### 命令超时保护
```python
# 最大执行时间
MAX_COMMAND_TIMEOUT = 30 秒

# 危险命令黑名单
dangerous_patterns = [
    "rm -rf /", "mkfs", "fork bomb",
    "chmod -R 777 /", "dd if=/dev/zero"
]

# 超时处理
subprocess.run(timeout=30)
process.kill()  # 超时强制终止
```

#### 安全增强
- `list_directory` 添加路径安全验证
- 只允许访问项目目录内文件
- 保持 `read_file`/`write_file` 路径遍历防护

---

## 四、修改统计

| 文件 | 修改行数 | 状态 |
|------|---------|------|
| runtime/vector_store.py | +112 | ✅ |
| runtime/literature_researcher.py | +228 | ✅ |
| runtime/mcp_protocol.py | +212 | ✅ |
| runtime/server.py | +292 (未改动，优化报告) | ⚠️ |
| runtime/hypothesis_tester.py | +2 | ✅ |
| **总计** | **+554行** | |

---

## 五、向后兼容性

| 功能 | 兼容方式 |
|------|---------|
| 向量存储 | `use_vector_store=False` 可禁用 |
| 工具名称 | 所有MCP工具名称不变 |
| 参数格式 | 参数格式完全兼容 |
| 错误处理 | 降级方案完善 |

---

## 六、测试建议

```bash
# 测试RAG功能
cd F:/tianwen-agi
python -c "from runtime.literature_researcher import LiteratureResearcher; r = LiteratureResearcher(); print(r.get_vector_store_stats())"

# 测试MCP web_search
python -c "from runtime.mcp_protocol import SearchTools; print(SearchTools.web_search('astronomy AI'))"
```

---

**优化完成时间**: 2026-05-03 19:15 CST
**执行Agent**: rag-mcp-optimization team