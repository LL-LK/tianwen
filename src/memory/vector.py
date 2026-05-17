"""
Hermes-AGI Vector Memory System
向量记忆系统 - 支持语义搜索和相似任务检索
使用ChromaDB作为向量数据库

增强功能:
- 集成sentence-transformers进行语义嵌入
- 支持论文/文献的向量表示和搜索
- 与literature_researcher.py无缝集成
- RAG能力增强
"""
import logging
logger = logging.getLogger(__name__)

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from sentence_transformers import SentenceTransformer
import hashlib
import numpy as np

# 从统一模块导入向量存储和数据模型
from .vector_store import SimpleVectorStore, BaseVectorStore
from src.data.models import Paper, Experience

# ============ 向量记忆系统 ============

class VectorMemory:
    """向量记忆系统"""

    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 初始化嵌入模型
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # 初始化向量存储
        self.experiences_store = SimpleVectorStore(dimension=384)
        self.patterns_store = SimpleVectorStore(dimension=384)

        # 加载已有数据
        self._load_stores()

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入"""
        embedding = self.embedder.encode(text)
        return embedding.tolist()

    def _generate_id(self, content: str) -> str:
        """生成唯一ID"""
        hash_obj = hashlib.md5(content.encode())
        return hash_obj.hexdigest()[:12]

    def _load_stores(self):
        """加载存储"""
        experiences_file = self.memory_dir / "vector_experiences.json"
        patterns_file = self.memory_dir / "vector_patterns.json"

        if experiences_file.exists():
            try:
                self.experiences_store.load(str(experiences_file))
                logger.info(f"[VectorMemory] Loaded {self.experiences_store.count()} experiences")
            except Exception as e:
                logger.info(f"[VectorMemory] Failed to load experiences: {e}")

        if patterns_file.exists():
            try:
                self.patterns_store.load(str(patterns_file))
                logger.info(f"[VectorMemory] Loaded {self.patterns_store.count()} patterns")
            except Exception as e:
                logger.info(f"[VectorMemory] Failed to load patterns: {e}")

    def _save_stores(self):
        """保存存储"""
        experiences_file = self.memory_dir / "vector_experiences.json"
        patterns_file = self.memory_dir / "vector_patterns.json"

        self.experiences_store.save(str(experiences_file))
        self.patterns_store.save(str(patterns_file))

    # ============ 经验管理 ============

    def add_experience(self, experience: Experience):
        """添加经验"""
        # 创建搜索文本
        search_text = f"{experience.task_description} {experience.solution} {' '.join(experience.skills_used)}"

        # 获取嵌入
        embedding = self._get_embedding(search_text)

        # 添加到向量存储
        self.experiences_store.add(
            text=search_text,
            embedding=embedding,
            metadata=experience.to_dict()
        )

        # 保存
        self._save_stores()

    def search_similar_experiences(self, query: str, k: int = 5) -> List[Dict]:
        """搜索相似经验"""
        query_embedding = self._get_embedding(query)
        results = self.experiences_store.search(query_embedding, k=k)
        return results

    def add_pattern(self, pattern_type: str, pattern_data: Dict):
        """添加模式"""
        search_text = f"{pattern_type} {json.dumps(pattern_data)}"
        embedding = self._get_embedding(search_text)

        self.patterns_store.add(
            text=search_text,
            embedding=embedding,
            metadata={**pattern_data, "type": pattern_type}
        )

        self._save_stores()

    def search_patterns(self, query: str, k: int = 5) -> List[Dict]:
        """搜索模式"""
        query_embedding = self._get_embedding(query)
        return self.patterns_store.search(query_embedding, k=k)

    # ============ 便捷方法 ============

    def record_success(self, task: str, solution: str, skills: List[str], **kwargs):
        """记录成功经验"""
        exp = Experience(
            id=self._generate_id(task + solution),
            type="success",
            task_description=task,
            solution=solution,
            skills_used=skills,
            outcome="success",
            **kwargs
        )
        self.add_experience(exp)
        return exp

    def record_failure(self, task: str, error: str, skills: List[str], **kwargs):
        """记录失败经验"""
        exp = Experience(
            id=self._generate_id(task + error),
            type="failure",
            task_description=task,
            solution=error,
            skills_used=skills,
            outcome="failed",
            **kwargs
        )
        self.add_experience(exp)
        return exp

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_experiences": self.experiences_store.count(),
            "total_patterns": self.patterns_store.count(),
        }

# ============ 增强型向量记忆系统（RAG增强）============

class EnhancedVectorMemory:
    """
    增强型向量记忆系统

    专为RAG和文献检索设计的功能:
    - 论文向量化存储和语义搜索
    - 支持批量添加论文
    - 与literature_researcher.py无缝集成
    - 异步API设计
    """

    # 默认嵌入模型
    DEFAULT_MODEL = 'all-MiniLM-L6-v2'
    # 向量维度 (all-MiniLM-L6-v2 输出384维)
    DIMENSION = 384

    def __init__(self, memory_dir: str = "./paper_memory", model_name: str = None):
        """
        初始化增强型向量记忆

        Args:
            memory_dir: 论文向量存储目录
            model_name: sentence-transformers模型名称，默认all-MiniLM-L6-v2
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 初始化嵌入模型
        self.model_name = model_name or self.DEFAULT_MODEL
        self.embedder = SentenceTransformer(self.model_name)

        # 论文向量存储
        self.papers_store = SimpleVectorStore(dimension=self.DIMENSION)

        # 元数据索引 (paper_id -> metadata)
        self.metadata_index: Dict[str, Dict] = {}

        # 加载已有数据
        self._load_papers_store()

    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本嵌入向量"""
        return self.embedder.encode(text)

    def _paper_to_search_text(self, paper: Paper) -> str:
        """将论文转换为搜索文本"""
        authors_str = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors_str += " et al."
        return f"{paper.title} {authors_str} {paper.abstract}"

    def _load_papers_store(self):
        """加载论文向量存储"""
        papers_file = self.memory_dir / "papers_vectors.json"

        if papers_file.exists():
            try:
                self.papers_store.load(str(papers_file))

                # 重建元数据索引
                for metadata in self.papers_store.metadata:
                    if "paper_id" in metadata:
                        self.metadata_index[metadata["paper_id"]] = metadata

                logger.info(f"[EnhancedVectorMemory] Loaded {self.papers_store.count()} paper embeddings")
            except Exception as e:
                logger.info(f"[EnhancedVectorMemory] Failed to load papers: {e}")

    def _save_papers_store(self):
        """保存论文向量存储"""
        papers_file = self.memory_dir / "papers_vectors.json"
        self.papers_store.save(str(papers_file))

    # ============ 核心API ============

    async def add_paper_embedding(self, paper: Paper) -> None:
        """
        为论文生成并存储向量

        Args:
            paper: Paper对象，包含title, authors, abstract等

        Returns:
            None
        """
        # 生成搜索文本
        search_text = self._paper_to_search_text(paper)

        # 生成嵌入向量
        embedding = self._get_embedding(search_text)

        # 构建元数据
        metadata = {
            "paper_id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "categories": paper.categories,
            "published_date": paper.published_date,
            "citations": paper.citations,
            "arxiv_url": paper.arxiv_url,
            "pdf_url": paper.pdf_url,
            "relevance_score": paper.relevance_score,
            "indexed_at": datetime.now().isoformat(),
        }

        # 添加到向量存储
        self.papers_store.add(
            text=search_text,
            embedding=embedding.tolist(),
            metadata=metadata
        )

        # 更新索引
        self.metadata_index[paper.id] = metadata

        # 保存
        self._save_papers_store()

        logger.info(f"[EnhancedVectorMemory] Added embedding for paper: {paper.title[:50]}...")

    async def add_papers_batch(self, papers: List[Paper]) -> int:
        """
        批量添加论文向量

        Args:
            papers: Paper对象列表

        Returns:
            成功添加的数量
        """
        if not papers:
            return 0

        # 批量生成搜索文本
        search_texts = [self._paper_to_search_text(paper) for paper in papers]

        # 批量生成嵌入向量 (更高效)
        try:
            embeddings = self.embedder.encode(search_texts)
            if len(embeddings.shape) == 1:
                embeddings = embeddings.reshape(1, -1)
        except Exception as e:
            logger.error(f"[EnhancedVectorMemory] Batch embedding error: {e}")
            # Fallback to sequential processing
            added_count = 0
            for paper in papers:
                try:
                    await self.add_paper_embedding(paper)
                    added_count += 1
                except Exception as ex:
                    logger.info(f"[EnhancedVectorMemory] Failed to add paper {paper.id}: {ex}")
            return added_count

        # 批量添加到向量存储
        added_count = 0
        for i, paper in enumerate(papers):
            try:
                metadata = {
                    "paper_id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "categories": paper.categories,
                    "published_date": paper.published_date,
                    "citations": paper.citations,
                    "arxiv_url": paper.arxiv_url,
                    "pdf_url": paper.pdf_url,
                    "relevance_score": paper.relevance_score,
                    "indexed_at": datetime.now().isoformat(),
                }

                self.papers_store.add(
                    text=search_texts[i],
                    embedding=embeddings[i].tolist(),
                    metadata=metadata
                )

                self.metadata_index[paper.id] = metadata
                added_count += 1

            except Exception as e:
                logger.info(f"[EnhancedVectorMemory] Failed to add paper {paper.id}: {e}")

        # 保存
        self._save_papers_store()
        logger.info(f"[EnhancedVectorMemory] Batch added {added_count} papers")

        return added_count

    async def search_similar_papers(self, query: str, top_k: int = 5) -> List[Paper]:
        """
        语义搜索相似论文

        Args:
            query: 查询文本（可以是问题、关键词或描述）
            top_k: 返回结果数量

        Returns:
            Paper对象列表，按相似度降序排列
        """
        # 生成查询向量
        query_embedding = self._get_embedding(query)

        # 搜索
        results = self.papers_store.search(query_embedding.tolist(), k=top_k)

        # 转换为Paper对象
        papers = []
        for result in results:
            try:
                metadata = result["metadata"]
                paper = Paper(
                    id=metadata.get("paper_id", ""),
                    title=metadata.get("title", ""),
                    authors=metadata.get("authors", []),
                    abstract=metadata.get("abstract", ""),
                    categories=metadata.get("categories", []),
                    published_date=metadata.get("published_date", ""),
                    updated_date=metadata.get("updated_date", ""),
                    citations=metadata.get("citations", 0),
                    pdf_url=metadata.get("pdf_url", ""),
                    arxiv_url=metadata.get("arxiv_url", ""),
                    relevance_score=result["score"],
                )
                papers.append(paper)
            except Exception as e:
                logger.info(f"[EnhancedVectorMemory] Failed to parse paper result: {e}")

        return papers

    async def search_by_embedding(self, embedding: np.ndarray, top_k: int = 5) -> List[Paper]:
        """
        基于已有向量搜索相似论文

        Args:
            embedding: 查询向量（numpy数组）
            top_k: 返回结果数量

        Returns:
            Paper对象列表，按相似度降序排列
        """
        # 确保embedding是列表
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        # 搜索
        results = self.papers_store.search(embedding, k=top_k)

        # 转换为Paper对象
        papers = []
        for result in results:
            try:
                metadata = result["metadata"]
                paper = Paper(
                    id=metadata.get("paper_id", ""),
                    title=metadata.get("title", ""),
                    authors=metadata.get("authors", []),
                    abstract=metadata.get("abstract", ""),
                    categories=metadata.get("categories", []),
                    published_date=metadata.get("published_date", ""),
                    updated_date=metadata.get("updated_date", ""),
                    citations=metadata.get("citations", 0),
                    pdf_url=metadata.get("pdf_url", ""),
                    arxiv_url=metadata.get("arxiv_url", ""),
                    relevance_score=result["score"],
                )
                papers.append(paper)
            except Exception as e:
                logger.info(f"[EnhancedVectorMemory] Failed to parse paper result: {e}")

        return papers

    async def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """
        根据ID获取论文

        Args:
            paper_id: 论文ID

        Returns:
            Paper对象或None
        """
        if paper_id not in self.metadata_index:
            return None

        metadata = self.metadata_index[paper_id]
        return Paper(
            id=metadata.get("paper_id", ""),
            title=metadata.get("title", ""),
            authors=metadata.get("authors", []),
            abstract=metadata.get("abstract", ""),
            categories=metadata.get("categories", []),
            published_date=metadata.get("published_date", ""),
            updated_date=metadata.get("updated_date", ""),
            citations=metadata.get("citations", 0),
            pdf_url=metadata.get("pdf_url", ""),
            arxiv_url=metadata.get("arxiv_url", ""),
            relevance_score=metadata.get("relevance_score", 0.0),
        )

    async def get_paper_count(self) -> int:
        """获取已索引的论文数量"""
        return self.papers_store.count()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_papers": self.papers_store.count(),
            "model": self.model_name,
            "dimension": self.DIMENSION,
            "memory_dir": str(self.memory_dir),
        }

    # ============ 与literature_researcher集成 ============

    async def index_research_state(self, research_state) -> int:
        """
        从LiteratureResearcher的ResearchState索引论文

        Args:
            research_state: LiteratureResearcher.research()返回的ResearchState对象

        Returns:
            索引的论文数量
        """
        return await self.add_papers_batch(research_state.papers)

    async def search_and_rank(
        self,
        query: str,
        papers: List[Paper],
        top_k: int = 5
    ) -> List[Tuple[Paper, float]]:
        """
        在给定论文集中搜索并排序

        Args:
            query: 查询文本
            papers: 候选论文列表（通常来自LiteratureResearcher.research()）
            top_k: 返回数量

        Returns:
            (Paper, score)元组列表，按分数降序
        """
        # 为所有论文生成向量（如果尚未生成）
        if not self.papers_store.count():
            await self.add_papers_batch(papers)

        # 语义搜索
        results = await self.search_similar_papers(query, top_k=top_k * 2)

        # 与候选集交叉，过滤并重新排序
        paper_ids = {p.id for p in papers}
        ranked: List[Tuple[Paper, float]] = []

        for paper in results:
            if paper.id in paper_ids:
                ranked.append((paper, paper.relevance_score))

        # 按分数排序
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked[:top_k]

# ============ 集成到Agent ============

class MemoryIntegratedAgent:
    """集成向量记忆的Agent"""

    def __init__(self, base_agent, memory_dir: str = "./memory"):
        self.base_agent = base_agent
        self.memory = VectorMemory(memory_dir)

    async def process_with_memory(self, user_input: str) -> Any:
        """带记忆处理的流程"""

        # 1. 搜索相似经验
        similar = self.memory.search_similar_experiences(user_input, k=3)
        if similar:
            logger.info(f"\n[Memory] Found {len(similar)} similar experiences")
            for s in similar[:1]:
                logger.info(f"  - {s['metadata'].get('task_description', 'N/A')[:50]}...")

        # 2. 处理请求
        result = await self.base_agent.process(user_input)

        # 3. 记录经验
        if result.status.value == "completed":
            self.memory.record_success(
                task=user_input,
                solution=result.output[:200],
                skills=result.task_model.required_skills,
                intent=result.task_model.type.value,
                complexity=result.task_model.complexity,
            )

        return result

# ============ 便捷函数 ============

def create_enhanced_memory(memory_dir: str = "./paper_memory") -> EnhancedVectorMemory:
    """创建增强型向量记忆实例"""
    return EnhancedVectorMemory(memory_dir=memory_dir)


# ============ 示例用法 ============

async def demo_enhanced():
    """演示增强型向量记忆"""
    print("=" * 60)
    logger.info("EnhancedVectorMemory RAG Demo")
    print("=" * 60)

    # 创建增强型向量记忆
    memory = EnhancedVectorMemory(memory_dir="./demo_paper_memory")

    # 创建示例论文
    sample_papers = [
        Paper(
            id="2024.12345",
            title="Deep Learning for Galaxy Classification",
            authors=["Zhang Wei", "Li Ming", "Wang Fang"],
            abstract="We propose a novel deep learning approach for automated galaxy morphology classification. Our method achieves 95% accuracy on the Galaxy Zoo dataset.",
            categories=["astro-ph.GA", "cs.CV"],
            published_date="2024-01-15",
            updated_date="2024-01-20",
            citations=45,
            arxiv_url="https://arxiv.org/abs/2024.12345"
        ),
        Paper(
            id="2024.23456",
            title="Transformer-based Star catalogs Classification",
            authors=["Chen Jian", "Liu Yang"],
            abstract="This paper presents a transformer architecture for stellar classification from photometric data. We demonstrate improved performance over traditional CNN methods.",
            categories=["astro-ph.SR", "cs.LG"],
            published_date="2024-02-10",
            updated_date="2024-02-15",
            citations=32,
            arxiv_url="https://arxiv.org/abs/2024.23456"
        ),
        Paper(
            id="2024.34567",
            title="Graph Neural Networks for Exoplanet Detection",
            authors=["Wang Lei", "Zhou Jing", "Huang Yun"],
            abstract="We introduce a GNN-based method for detecting exoplanet candidates from transit light curves. Our approach shows robustness to noise and missing data.",
            categories=["astro-ph.EP", "cs.AI"],
            published_date="2024-03-05",
            updated_date="2024-03-10",
            citations=28,
            arxiv_url="https://arxiv.org/abs/2024.34567"
        ),
    ]

    # 添加论文
    logger.info("\n📚 Indexing sample papers...")
    count = await memory.add_papers_batch(sample_papers)
    logger.info(f"   Indexed {count} papers")

    # 语义搜索
    logger.info("\n🔍 Search: 'machine learning for astronomical objects'")
    results = await memory.search_similar_papers(
        "machine learning for astronomical objects",
        top_k=3
    )
    for i, paper in enumerate(results, 1):
        logger.info(f"\n   [{i}] {paper.title}")
        logger.info(f"       Score: {paper.relevance_score:.3f}")
        logger.info(f"       Authors: {', '.join(paper.authors[:2])}")
        logger.info(f"       Abstract: {paper.abstract[:80]}...")

    # 基于向量搜索
    logger.info("\n🔍 Search by embedding...")
    query_emb = memory._get_embedding("deep learning for star classification")
    results = await memory.search_by_embedding(query_emb, top_k=2)
    for paper in results:
        logger.info(f"   - {paper.title} (score: {paper.relevance_score:.3f})")

    # 统计
    logger.info(f"\n📊 Stats: {memory.get_stats()}")

    # 清理演示目录
    import shutil
    if Path("./demo_paper_memory").exists():
        shutil.rmtree("./demo_paper_memory")


async def demo_integration():
    """演示与LiteratureResearcher集成"""
    logger.debug("\n" + "=" * 60)
    logger.info("Integration with LiteratureResearcher Demo")
    print("=" * 60)

    # 这个演示展示了如何将两个模块结合使用
    from literature_researcher import LiteratureResearcher, Paper as LRPaper

    researcher = LiteratureResearcher()
    memory = EnhancedVectorMemory(memory_dir="./demo_integration_memory")

    # 模拟从researcher获取论文
    logger.info("\n📥 Simulating LiteratureResearcher workflow...")

    # 创建兼容的Paper对象
    lr_papers = [
        LRPaper(
            id=f"sim-{i}",
            title=f"Research Paper on Topic {i}",
            authors=[f"Author {j}" for j in range(3)],
            abstract=f"This is an abstract for research paper number {i}...",
            categories=["cs.AI"],
            published_date="2024-01-01",
            updated_date="2024-01-02",
        )
        for i in range(5)
    ]

    # 转换为EnhancedVectorMemory使用的Paper
    papers = [
        Paper(
            id=p.id,
            title=p.title,
            authors=p.authors,
            abstract=p.abstract,
            categories=p.categories,
            published_date=p.published_date,
            updated_date=p.updated_date,
            citations=p.citations,
            arxiv_url=p.arxiv_url,
        )
        for p in lr_papers
    ]

    # 索引
    await memory.add_papers_batch(papers)

    # 搜索
    results = await memory.search_similar_papers("artificial intelligence research", top_k=3)
    logger.info(f"\n🔍 Found {len(results)} relevant papers")

    # 清理
    import shutil
    if Path("./demo_integration_memory").exists():
        shutil.rmtree("./demo_integration_memory")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_enhanced())
    asyncio.run(demo_integration())