"""
Runtime Module Unit Tests
测试 vector_memory, vector_rag, literature_researcher, discovery_tracker 的核心功能

Run with: python -m pytest runtime/tests/test_runtime_modules.py -v
"""

import pytest
import unittest
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules under test
from vector_memory import (
    VectorMemory,
    EnhancedVectorMemory,
    SimpleVectorStore,
    Paper,
    Experience
)
from literature_researcher import (
    Paper as LRPaper,
    ChromaDBVectorStore,
    LiteratureResearcher,
    ArxivAPI
)


class TestSimpleVectorStore(unittest.TestCase):
    """Test SimpleVectorStore from vector_memory.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.store = SimpleVectorStore(dimension=384)
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_vectors.json")

    def tearDown(self):
        """Clean up temp files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_vector_store_initialization(self):
        """Test vector store initializes with correct dimension"""
        self.assertEqual(self.store.dimension, 384)
        self.assertEqual(self.store.count(), 0)

    def test_add_and_search(self):
        """Test adding vectors and searching"""
        # Add a vector
        self.store.add(
            text="test document",
            embedding=[0.1] * 384,
            metadata={"id": "test-1"}
        )

        self.assertEqual(self.store.count(), 1)

        # Search
        results = self.store.search([0.1] * 384, k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "test document")

    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        # Identical vectors
        vec1 = [1.0, 0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0, 0.0]
        self.assertAlmostEqual(self.store._cosine_similarity(vec1, vec2), 1.0, places=5)

        # Orthogonal vectors
        vec3 = [0.0, 1.0, 0.0, 0.0]
        self.assertAlmostEqual(self.store._cosine_similarity(vec1, vec3), 0.0, places=5)

    def test_save_and_load(self):
        """Test vector store persistence"""
        # Add vectors
        self.store.add(text="doc1", embedding=[0.1] * 384, metadata={"id": "1"})
        self.store.add(text="doc2", embedding=[0.2] * 384, metadata={"id": "2"})

        # Save
        self.store.save(self.temp_file)
        self.assertTrue(os.path.exists(self.temp_file))

        # Load into new store
        new_store = SimpleVectorStore(dimension=384)
        new_store.load(self.temp_file)

        self.assertEqual(new_store.count(), 2)


class TestExperience(unittest.TestCase):
    """Test Experience dataclass from vector_memory.py"""

    def test_experience_creation(self):
        """Test Experience can be created with all fields"""
        exp = Experience(
            id="exp-001",
            type="success",
            task_description="Test task",
            solution="Test solution",
            skills_used=["python", "testing"],
            outcome="success"
        )

        self.assertEqual(exp.id, "exp-001")
        self.assertEqual(exp.type, "success")
        self.assertEqual(exp.outcome, "success")

    def test_experience_to_dict(self):
        """Test Experience serialization"""
        exp = Experience(
            id="exp-002",
            type="failure",
            task_description="Failed task",
            solution="Error occurred",
            skills_used=["debugging"],
            outcome="failed"
        )

        data = exp.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["id"], "exp-002")
        self.assertEqual(data["type"], "failure")

    def test_experience_from_dict(self):
        """Test Experience deserialization"""
        data = {
            "id": "exp-003",
            "type": "pattern",
            "task_description": "Pattern task",
            "solution": "Solution pattern",
            "skills_used": ["pattern matching"],
            "entities": [],
            "intent": "pattern_recognition",
            "complexity": "high",
            "outcome": "success",
            "lessons_learned": "Found a pattern",
            "timestamp": datetime.now().isoformat()
        }

        exp = Experience.from_dict(data)
        self.assertEqual(exp.id, "exp-003")
        self.assertEqual(exp.type, "pattern")


class TestPaperVectorMemory(unittest.TestCase):
    """Test Paper-related functionality in vector_memory.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_paper_creation(self):
        """Test Paper dataclass can be created"""
        paper = Paper(
            id="paper-001",
            title="Deep Learning for Astronomy",
            authors=["Zhang Wei", "Li Ming"],
            abstract="This paper presents...",
            categories=["astro-ph", "cs.LG"],
            published_date="2024-01-01",
            updated_date="2024-01-02",
            citations=42
        )

        self.assertEqual(paper.id, "paper-001")
        self.assertEqual(paper.title, "Deep Learning for Astronomy")
        self.assertEqual(len(paper.authors), 2)

    def test_paper_to_search_text(self):
        """Test Paper.to_search_text()"""
        paper = Paper(
            id="paper-002",
            title="Machine Learning",
            authors=["Author A", "Author B", "Author C", "Author D"],
            abstract="Abstract text here",
            categories=["cs.AI"],
            published_date="2024-01-01",
            updated_date="2024-01-02"
        )

        search_text = paper.to_search_text()

        self.assertIn("Machine Learning", search_text)
        self.assertIn("Author A", search_text)
        self.assertIn("Author B", search_text)
        self.assertIn("et al.", search_text)
        self.assertIn("Abstract text here", search_text)

    def test_enhanced_vector_memory_stats(self):
        """Test EnhancedVectorMemory.get_stats()"""
        memory = EnhancedVectorMemory(memory_dir=self.temp_dir)

        stats = memory.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_papers", stats)
        self.assertIn("model", stats)
        self.assertIn("dimension", stats)
        self.assertEqual(stats["dimension"], 384)
        self.assertEqual(stats["total_papers"], 0)

    @pytest.mark.asyncio
    async def test_add_paper_embedding(self):
        """Test adding single paper to EnhancedVectorMemory"""
        memory = EnhancedVectorMemory(memory_dir=self.temp_dir)

        paper = Paper(
            id="test-paper-001",
            title="Test Paper",
            authors=["Test Author"],
            abstract="Test abstract content",
            categories=["cs.AI"],
            published_date="2024-01-01",
            updated_date="2024-01-02"
        )

        await memory.add_paper_embedding(paper)

        self.assertEqual(memory.papers_store.count(), 1)
        self.assertIn("test-paper-001", memory.metadata_index)

    @pytest.mark.asyncio
    async def test_search_similar_papers(self):
        """Test searching similar papers"""
        memory = EnhancedVectorMemory(memory_dir=self.temp_dir)

        # Add papers
        papers = [
            Paper(
                id=f"test-{i}",
                title=f"Paper about topic {i}",
                authors=["Author A"],
                abstract=f"Abstract content for topic {i}",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02"
            )
            for i in range(3)
        ]

        await memory.add_papers_batch(papers)

        # Search
        results = await memory.search_similar_papers("machine learning", top_k=2)

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 2)

    @pytest.mark.asyncio
    async def test_get_paper_by_id(self):
        """Test retrieving paper by ID"""
        memory = EnhancedVectorMemory(memory_dir=self.temp_dir)

        paper = Paper(
            id="retrieve-test-001",
            title="Retrieve Test Paper",
            authors=["Author X"],
            abstract="Retrieve abstract",
            categories=["cs.AI"],
            published_date="2024-01-01",
            updated_date="2024-01-02"
        )

        await memory.add_paper_embedding(paper)

        # Retrieve
        retrieved = await memory.get_paper_by_id("retrieve-test-001")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Retrieve Test Paper")


class TestChromaDBVectorStorePersistence(unittest.TestCase):
    """Test ChromaDBVectorStore persistence in literature_researcher.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.store = ChromaDBVectorStore(collection_name="test_persistence")
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_store.json")

    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test ChromaDBVectorStore initialization"""
        self.assertEqual(self.store.collection_name, "test_persistence")
        self.assertEqual(self.store.dimension, 384)
        self.assertEqual(len(self.store.vectors), 0)

    def test_cosine_similarity(self):
        """Test cosine similarity in ChromaDBVectorStore"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(self.store._cosine_similarity(vec1, vec2), 1.0, places=5)

        vec3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(self.store._cosine_similarity(vec1, vec3), 0.0, places=5)

    def test_save_and_load(self):
        """Test ChromaDBVectorStore save/load"""
        # Create test papers
        papers = [
            LRPaper(
                id=f"persist-{i}",
                title=f"Persisted Paper {i}",
                authors=["Author A"],
                abstract=f"Abstract {i}",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="test"
            )
            for i in range(3)
        ]

        # Add papers (using fallback since sentence-transformers may not be installed)
        import asyncio
        asyncio.run(self.store.add_papers(papers))

        # Save
        result = self.store.save(self.temp_file)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.temp_file))

        # Load into new store
        new_store = ChromaDBVectorStore(collection_name="loaded_store")
        load_result = new_store.load(self.temp_file)
        self.assertTrue(load_result)

        # Verify (using sync check since we used fallback)
        self.assertEqual(len(new_store.vectors), 3)
        self.assertEqual(len(new_store.texts), 3)

    @pytest.mark.asyncio
    async def test_add_papers_fallback(self):
        """Test add_papers with fallback (no sentence-transformers)"""
        papers = [
            LRPaper(
                id=f"fallback-{i}",
                title=f"Fallback Paper {i}",
                authors=["Author B"],
                abstract=f"Test abstract {i}",
                categories=["cs.LG"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="test"
            )
            for i in range(2)
        ]

        result = await self.store.add_papers(papers)
        self.assertTrue(result)
        self.assertEqual(len(self.store.vectors), 2)

    @pytest.mark.asyncio
    async def test_search_similar_fallback(self):
        """Test search_similar with fallback"""
        papers = [
            LRPaper(
                id=f"search-{i}",
                title=f"Search Paper {i}",
                authors=["Author C"],
                abstract=f"Machine learning abstract {i}",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="test"
            )
            for i in range(3)
        ]

        await self.store.add_papers(papers)

        # Search
        results = await self.store.search_similar("deep learning", top_k=2)

        self.assertIsInstance(results, list)
        for paper in results:
            self.assertIsInstance(paper, LRPaper)
            self.assertTrue(hasattr(paper, 'relevance_score'))

    @pytest.mark.asyncio
    async def test_delete_paper(self):
        """Test deleting a paper"""
        papers = [
            LRPaper(
                id="delete-test-1",
                title="Delete Test 1",
                authors=["Author"],
                abstract="Test",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="test"
            ),
            LRPaper(
                id="delete-test-2",
                title="Delete Test 2",
                authors=["Author"],
                abstract="Test",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="test"
            )
        ]

        await self.store.add_papers(papers)
        self.assertEqual(len(self.store.vectors), 2)

        # Delete one
        result = await self.store.delete_paper("delete-test-1")
        self.assertTrue(result)
        self.assertEqual(len(self.store.vectors), 1)

    @pytest.mark.asyncio
    async def test_get_collection_stats(self):
        """Test getting collection statistics"""
        papers = [
            LRPaper(
                id=f"stats-{i}",
                title=f"Stats Paper {i}",
                authors=["Author"],
                abstract="Test abstract",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="test"
            )
            for i in range(5)
        ]

        await self.store.add_papers(papers)

        stats = await self.store.get_collection_stats()

        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["total_papers"], 5)
        self.assertEqual(stats["dimension"], 384)


class TestLiteratureResearcher(unittest.TestCase):
    """Test LiteratureResearcher from literature_researcher.py"""

    def test_researcher_initialization(self):
        """Test LiteratureResearcher initialization"""
        researcher = LiteratureResearcher(
            use_arxiv=True,
            use_openalex=False,
            use_semantic_scholar=False
        )

        self.assertTrue(researcher.use_arxiv)
        self.assertFalse(researcher.use_openalex)
        self.assertIsNone(researcher.openalex)
        self.assertIsNotNone(researcher.arxiv)

    def test_sources_used_property(self):
        """Test sources_used property"""
        researcher = LiteratureResearcher(
            use_arxiv=True,
            use_openalex=True,
            use_semantic_scholar=False
        )

        sources = researcher.sources_used
        self.assertIn("arxiv", sources)
        self.assertIn("openalex", sources)

    def test_deduplicate_papers(self):
        """Test paper deduplication"""
        researcher = LiteratureResearcher(use_arxiv=True)

        papers = [
            LRPaper(
                id="arxiv:1234.5678",
                title="Paper 1",
                authors=["Author A"],
                abstract="Abstract 1",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="arxiv"
            ),
            LRPaper(
                id="arxiv:1234.5678",  # Duplicate ID
                title="Paper 1 Duplicate",
                authors=["Author B"],
                abstract="Abstract 1 duplicate",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="arxiv"
            )
        ]

        unique = researcher._deduplicate_papers(papers)
        self.assertEqual(len(unique), 1)


class TestArxivAPI(unittest.TestCase):
    """Test ArxivAPI from literature_researcher.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.arxiv = ArxivAPI(max_results=10)

    def test_initialization(self):
        """Test ArxivAPI initialization"""
        self.assertEqual(self.arxiv.max_results, 10)
        self.assertEqual(self.arxiv.rate_limit_delay, 3.0)

    def test_optimize_query_single_term(self):
        """Test query optimization for single term"""
        query = "deep learning"
        optimized = self.arxiv._optimize_query(query)
        self.assertEqual(optimized, "ALL:deep learning")

    def test_optimize_query_multi_term(self):
        """Test query optimization for multiple terms"""
        query = "deep learning neural network"
        optimized = self.arxiv._optimize_query(query)
        self.assertIn("ALL:deep", optimized)
        self.assertIn("ALL:learning", optimized)
        self.assertIn("ALL:neural", optimized)

    def test_optimize_query_already_optimized(self):
        """Test query optimization skips already optimized queries"""
        query = "ALL:deep AND cat:cs.AI"
        optimized = self.arxiv._optimize_query(query)
        self.assertEqual(optimized, query)

    def test_clean_text(self):
        """Test XML text cleaning"""
        dirty_text = "  Title  \n\n  with  \n  newlines  "
        clean = self.arxiv._clean_text(dirty_text)
        self.assertNotIn("\n", clean)
        self.assertNotIn("  ", clean)


class TestVectorMemoryExperience(unittest.TestCase):
    """Test VectorMemory experience recording"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_vector_memory_initialization(self):
        """Test VectorMemory initialization"""
        memory = VectorMemory(memory_dir=self.temp_dir)

        self.assertEqual(memory.memory_dir, Path(self.temp_dir))
        self.assertIsNotNone(memory.embedder)

    def test_get_stats(self):
        """Test getting VectorMemory stats"""
        memory = VectorMemory(memory_dir=self.temp_dir)

        stats = memory.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_experiences", stats)
        self.assertIn("total_patterns", stats)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])