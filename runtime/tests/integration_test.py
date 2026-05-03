"""
Integration Tests for Runtime Module
测试 runtime 模块集成:
1. literature_researcher -> vector_memory 数据流
2. vector_memory -> reasoning_engine 数据流
3. server.py API端点

Run with: python -m pytest runtime/tests/integration_test.py -v
"""

import unittest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules under test
from literature_researcher import (
    Paper,
    ChromaDBVectorStore,
    LiteratureResearcher,
    ResearchState
)
from vector_memory import (
    Paper as VMPaper,
    EnhancedVectorMemory,
    VectorMemory
)
from reasoning_engine import (
    ReasoningEngine,
    ReasoningResult,
    ModelConfig,
    Complexity
)


class TestChromaDBVectorStore(unittest.TestCase):
    """Test ChromaDBVectorStore from literature_researcher.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.vector_store = ChromaDBVectorStore(collection_name="test_papers")

        # Create test papers
        self.test_papers = [
            Paper(
                id=f"test-{i}",
                title=f"Test Paper {i}: Machine Learning in Astronomy",
                authors=[f"Author {j}" for j in range(3)],
                abstract=f"This is abstract {i} about machine learning algorithms for astronomical data processing.",
                categories=["astro-ph", "cs.LG"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                citations=10 * i,
                source="test"
            )
            for i in range(5)
        ]

    def test_vector_store_initialization(self):
        """Test vector store can be initialized"""
        self.assertEqual(self.vector_store.collection_name, "test_papers")
        self.assertEqual(self.vector_store.dimension, 384)
        self.assertEqual(len(self.vector_store.vectors), 0)
        self.assertEqual(len(self.vector_store.metadata), 0)

    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        # Identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(self.vector_store._cosine_similarity(vec1, vec2), 1.0, places=5)

        # Orthogonal vectors
        vec3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(self.vector_store._cosine_similarity(vec1, vec3), 0.0, places=5)

        # Negative correlation
        vec4 = [-1.0, 0.0, 0.0]
        self.assertAlmostEqual(self.vector_store._cosine_similarity(vec1, vec4), -1.0, places=5)

    @pytest.mark.asyncio
    async def test_add_papers(self):
        """Test adding papers to vector store"""
        # Use fallback since sentence-transformers may not be installed
        result = await self.vector_store.add_papers(self.test_papers)
        self.assertTrue(result)

        # Check papers were added
        self.assertEqual(len(self.vector_store.vectors), len(self.test_papers))
        self.assertEqual(len(self.vector_store.metadata), len(self.test_papers))
        self.assertEqual(len(self.vector_store.texts), len(self.test_papers))

    @pytest.mark.asyncio
    async def test_search_similar(self):
        """Test searching for similar papers"""
        # First add papers
        await self.vector_store.add_papers(self.test_papers)

        # Search with a query
        results = await self.vector_store.search_similar(
            "machine learning astronomy",
            top_k=3
        )

        # Verify results structure
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)

        for paper in results:
            self.assertIsInstance(paper, Paper)
            self.assertTrue(hasattr(paper, 'relevance_score'))
            self.assertGreaterEqual(paper.relevance_score, 0.0)
            self.assertLessEqual(paper.relevance_score, 1.0)

    @pytest.mark.asyncio
    async def test_delete_paper(self):
        """Test deleting a paper from vector store"""
        # Add papers first
        await self.vector_store.add_papers(self.test_papers)
        initial_count = len(self.vector_store.vectors)

        # Delete one paper
        result = await self.vector_store.delete_paper("test-2")
        self.assertTrue(result)

        # Verify deletion
        self.assertEqual(len(self.vector_store.vectors), initial_count - 1)

    @pytest.mark.asyncio
    async def test_get_collection_stats(self):
        """Test getting collection statistics"""
        await self.vector_store.add_papers(self.test_papers)

        stats = await self.vector_store.get_collection_stats()

        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["total_papers"], len(self.test_papers))
        self.assertEqual(stats["dimension"], 384)
        self.assertEqual(stats["collection_name"], "test_papers")


class TestEnhancedVectorMemory(unittest.TestCase):
    """Test EnhancedVectorMemory from vector_memory.py"""

    def setUp(self):
        """Set up test fixtures with temporary directory"""
        self.test_dir = "./test_paper_memory"
        self.memory = EnhancedVectorMemory(memory_dir=self.test_dir)

        # Create test papers
        self.test_papers = [
            VMPaper(
                id=f"vm-test-{i}",
                title=f"Deep Learning for Galaxy Classification {i}",
                authors=["Zhang Wei", "Li Ming"],
                abstract=f"We propose a novel deep learning approach for automated galaxy morphology classification using CNNs.",
                categories=["astro-ph.GA", "cs.CV"],
                published_date="2024-01-15",
                updated_date="2024-01-20",
                citations=45
            )
            for i in range(3)
        ]

    def tearDown(self):
        """Clean up test directory"""
        import shutil
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def test_memory_initialization(self):
        """Test memory system initialization"""
        self.assertEqual(self.memory.model_name, 'all-MiniLM-L6-v2')
        self.assertEqual(self.memory.DIMENSION, 384)
        self.assertEqual(self.memory.papers_store.count(), 0)

    def test_paper_to_search_text(self):
        """Test paper to search text conversion"""
        paper = self.test_papers[0]
        search_text = self.memory._paper_to_search_text(paper)

        self.assertIn(paper.title, search_text)
        self.assertIn(paper.authors[0], search_text)
        self.assertIn(paper.abstract, search_text)

    @pytest.mark.asyncio
    async def test_add_single_paper(self):
        """Test adding a single paper"""
        paper = self.test_papers[0]
        await self.memory.add_paper_embedding(paper)

        self.assertEqual(self.memory.papers_store.count(), 1)
        self.assertIn(paper.id, self.memory.metadata_index)

    @pytest.mark.asyncio
    async def test_add_papers_batch(self):
        """Test batch adding papers"""
        count = await self.memory.add_papers_batch(self.test_papers)

        self.assertEqual(count, len(self.test_papers))
        self.assertEqual(self.memory.papers_store.count(), len(self.test_papers))

    @pytest.mark.asyncio
    async def test_search_similar_papers(self):
        """Test searching similar papers"""
        # Add papers first
        await self.memory.add_papers_batch(self.test_papers)

        # Search
        results = await self.memory.search_similar_papers(
            "deep learning galaxy classification",
            top_k=2
        )

        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 2)

        for paper in results:
            self.assertIsInstance(paper, VMPaper)
            self.assertGreaterEqual(paper.relevance_score, 0.0)

    @pytest.mark.asyncio
    async def test_get_paper_by_id(self):
        """Test retrieving paper by ID"""
        await self.memory.add_papers_batch(self.test_papers)

        paper = await self.memory.get_paper_by_id("vm-test-1")

        self.assertIsNotNone(paper)
        self.assertEqual(paper.id, "vm-test-1")
        self.assertEqual(paper.title, self.test_papers[1].title)

    def test_get_stats(self):
        """Test getting memory statistics"""
        stats = self.memory.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["model"], 'all-MiniLM-L6-v2')
        self.assertEqual(stats["dimension"], 384)


class TestLiteratureToVectorFlow(unittest.TestCase):
    """Test literature_researcher -> vector_memory data flow"""

    def setUp(self):
        """Set up test fixtures"""
        self.vector_store = ChromaDBVectorStore(collection_name="flow_test")
        self.test_dir = "./test_flow_memory"
        self.enhanced_memory = EnhancedVectorMemory(memory_dir=self.test_dir)

    def tearDown(self):
        """Clean up"""
        import shutil
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_researcher_to_vector_store_flow(self):
        """Test data flow from LiteratureResearcher to ChromaDBVectorStore"""
        # Create papers similar to what LiteratureResearcher would return
        papers = [
            Paper(
                id=f"flow-test-{i}",
                title=f"Research Paper on Topic {i}",
                authors=["Author A", "Author B"],
                abstract=f"This paper discusses research topic {i} with detailed methodology.",
                categories=["cs.AI", "astro-ph"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="arxiv"
            )
            for i in range(3)
        ]

        # Add to ChromaDBVectorStore (simulating LiteratureResearcher.output)
        result = await self.vector_store.add_papers(papers)
        self.assertTrue(result)

        # Verify papers were added
        self.assertEqual(self.vector_store.get_collection_stats()["total_papers"], 3)

        # Search should work
        results = await self.vector_store.search_similar("research topic methodology", top_k=2)
        self.assertIsInstance(results, list)

    @pytest.mark.asyncio
    async def test_paper_type_compatibility(self):
        """Test Paper type compatibility between modules"""
        # Create paper using literature_researcher's Paper
        lr_paper = Paper(
            id="lr-paper-1",
            title="Literature Research Paper",
            authors=["Author X"],
            abstract="Abstract content",
            categories=["cs.AI"],
            published_date="2024-01-01",
            updated_date="2024-01-02",
            source="arxiv"
        )

        # Convert to vector_memory's Paper type
        vm_paper = VMPaper(
            id=lr_paper.id,
            title=lr_paper.title,
            authors=lr_paper.authors,
            abstract=lr_paper.abstract,
            categories=lr_paper.categories,
            published_date=lr_paper.published_date,
            updated_date=lr_paper.updated_date,
            citations=lr_paper.citations
        )

        # Add to EnhancedVectorMemory
        await self.enhanced_memory.add_paper_embedding(vm_paper)

        # Verify
        self.assertEqual(self.enhanced_memory.papers_store.count(), 1)
        retrieved = await self.enhanced_memory.get_paper_by_id("lr-paper-1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Literature Research Paper")


class TestReasoningEngine(unittest.TestCase):
    """Test ReasoningEngine from reasoning_engine.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = ReasoningEngine(cache_enabled=True)

    def test_engine_initialization(self):
        """Test engine initializes correctly"""
        self.assertIsNone(self.engine.qwen)
        self.assertIsNone(self.engine.deepseek)
        self.assertTrue(self.engine.cache_enabled)
        self.assertIsNotNone(self.engine._cache)

    def test_complexity_estimation(self):
        """Test complexity estimation"""
        # Low complexity
        comp = self.engine._estimate_complexity("What is the capital of France?")
        self.assertEqual(comp, Complexity.LOW)

        # High complexity indicators
        comp = self.engine._estimate_complexity("分析人工智能对天文学研究的潜在影响")
        self.assertEqual(comp, Complexity.HIGH)

        # Extreme complexity
        comp = self.engine._estimate_complexity("请证明深度学习的收敛性")
        self.assertEqual(comp, Complexity.EXTREME)

    def test_cache_operations(self):
        """Test LRU cache operations"""
        # Put something in cache
        test_result = ReasoningResult(content="test", model_used="test")
        self.engine._cache.put("test prompt", test_result, "low", "")

        # Get from cache
        cached = self.engine._cache.get("test prompt", "low", "")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.content, "test")

        # Clear cache
        self.engine.clear_cache()
        cached = self.engine._cache.get("test prompt", "low", "")
        self.assertIsNone(cached)

    def test_get_status(self):
        """Test getting engine status"""
        status = self.engine.get_status()

        self.assertIsInstance(status, dict)
        self.assertFalse(status["qwen_configured"])
        self.assertFalse(status["deepseek_configured"])
        self.assertTrue(status["cache_enabled"])
        self.assertIn("available_models", status)

    def test_model_config_creation(self):
        """Test ModelConfig creation"""
        # Qwen local config
        qwen_config = ModelConfig.qwen_local("http://localhost:8000")
        self.assertEqual(qwen_config.name, "qwen")
        self.assertEqual(qwen_config.endpoint, "http://localhost:8000")
        self.assertEqual(qwen_config.model_type, "openai_compatible")

        # DeepSeek API config
        ds_config = ModelConfig.deepseek_api("test-key")
        self.assertEqual(ds_config.name, "deepseek")
        self.assertEqual(ds_config.endpoint, "https://api.deepseek.com")
        self.assertEqual(ds_config.api_key, "test-key")

    @pytest.mark.asyncio
    async def test_think_without_models(self):
        """Test think() method when no models are configured"""
        # This should return an error result since no models are configured
        result = await self.engine.think("test prompt")

        self.assertIsInstance(result, ReasoningResult)
        self.assertIn("错误", result.content)  # Should contain error message

    def test_reasoning_result_structure(self):
        """Test ReasoningResult has correct structure"""
        result = ReasoningResult(
            content="Test content",
            thinking_process="Thinking steps",
            model_used="TestModel",
            complexity="high",
            tokens_used=100,
            latency_ms=500.0
        )

        self.assertEqual(result.content, "Test content")
        self.assertEqual(result.thinking_process, "Thinking steps")
        self.assertEqual(result.model_used, "TestModel")
        self.assertEqual(result.complexity, "high")
        self.assertEqual(result.tokens_used, 100)
        self.assertEqual(result.latency_ms, 500.0)


class TestServerAPI(unittest.TestCase):
    """Test server.py API endpoints"""

    @classmethod
    def setUpClass(cls):
        """Set up test client"""
        # Import quart components
        from quart import Quart
        from quart.testing import Client

        # Create app instance for testing
        from server import app

        cls.client = app.test_client()

    @pytest.mark.asyncio
    async def test_health_endpoint_exists(self):
        """Test /api/health endpoint exists and returns correct structure"""
        response = await self.client.get('/api/health')

        # Should return 200
        self.assertEqual(response.status_code, 200)

        # Parse JSON response
        data = await response.get_json()

        # Verify expected fields
        self.assertIn("status", data)
        self.assertIn("version", data)
        self.assertIn("timestamp", data)
        self.assertIn("system", data)
        self.assertIn("dependencies", data)
        self.assertIn("sessions", data)

        # Verify system info structure
        self.assertIn("memory", data["system"])
        self.assertIn("cpu", data["system"])
        self.assertIn("process", data["system"])

        # Verify dependencies
        deps = data["dependencies"]
        self.assertIn("agent_initialized", deps)
        self.assertIn("cognitive_engine", deps)
        self.assertIn("planning_engine", deps)
        self.assertIn("execution_engine", deps)
        self.assertIn("evolution_system", deps)

    @pytest.mark.asyncio
    async def test_health_timestamp_format(self):
        """Test health endpoint returns valid timestamp"""
        response = await self.client.get('/api/health')
        data = await self.response.get_json()

        # Should be valid ISO format
        try:
            datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            self.fail("Invalid timestamp format")

    @pytest.mark.asyncio
    async def test_sessions_endpoint_exists(self):
        """Test /api/sessions endpoint exists"""
        response = await self.client.get('/api/sessions')
        self.assertEqual(response.status_code, 200)

        data = await response.get_json()
        self.assertIn("sessions", data)
        self.assertIsInstance(data["sessions"], list)


class TestDataFlowIntegration(unittest.TestCase):
    """Integration tests for complete data flows"""

    @pytest.mark.asyncio
    async def test_full_pipeline_literature_to_reasoning(self):
        """Test complete pipeline: literature -> vector -> reasoning"""
        # Step 1: Create papers (simulating literature_researcher output)
        papers = [
            Paper(
                id=f"pipeline-paper-{i}",
                title=f"Research on Topic {i}",
                authors=["Author A"],
                abstract=f"Abstract for research topic {i}",
                categories=["cs.AI"],
                published_date="2024-01-01",
                updated_date="2024-01-02",
                source="test"
            )
            for i in range(2)
        ]

        # Step 2: Store in vector memory
        vector_store = ChromaDBVectorStore(collection_name="pipeline_test")
        await vector_store.add_papers(papers)

        # Verify stored
        stats = await vector_store.get_collection_stats()
        self.assertEqual(stats["total_papers"], 2)

        # Step 3: Search and get relevant papers
        results = await vector_store.search_similar("research topic", top_k=2)
        self.assertIsInstance(results, list)

        # Step 4: Use results with reasoning engine
        engine = ReasoningEngine()

        if results:
            query = f"Analyze paper: {results[0].title}"
            # Engine should handle this gracefully even without models
            result = await engine.think(query)
            self.assertIsInstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_vector_memory_reasoning_flow(self):
        """Test vector_memory -> reasoning_engine data flow"""
        # Create and store papers in EnhancedVectorMemory
        test_dir = "./test_reasoning_flow"

        try:
            memory = EnhancedVectorMemory(memory_dir=test_dir)

            papers = [
                VMPaper(
                    id=f"reasoning-test-{i}",
                    title=f"Paper about ML method {i}",
                    authors=["Researcher A"],
                    abstract=f"This paper presents method {i} for ML applications.",
                    categories=["cs.LG"],
                    published_date="2024-01-01",
                    updated_date="2024-01-02"
                )
                for i in range(2)
            ]

            await memory.add_papers_batch(papers)

            # Search to get context
            results = await memory.search_similar_papers("machine learning method", top_k=2)

            # Use reasoning engine with search results
            engine = ReasoningEngine()

            if results:
                context = f"Found {len(results)} papers. First: {results[0].title}"
                result = await engine.think(f"Summarize this research context: {context}")
                self.assertIsInstance(result, ReasoningResult)
            else:
                self.skipTest("No search results to test with")

        finally:
            import shutil
            if Path(test_dir).exists():
                shutil.rmtree(test_dir)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
