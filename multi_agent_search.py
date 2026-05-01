"""
天问-AGI 多Agent并行搜索架构 v1.0
MultiAgentSearch - 3-Agent并行搜索协调器

基于Hermes评审建议实现:
- 3-Agent并行: arxiv_searcher + github_searcher + data_searcher
- 向量去重 + LLM路由
- 分层验证机制
- 故障隔离

用法:
    coordinator = MultiAgentSearchCoordinator()
    results = await coordinator.search_all("系外行星探测")
"""

import asyncio
import uuid
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import time

# 浏览器搜索模块
try:
    from browser_search import BrowserSearch, SearchResult, SearchTarget
    BROWSER_SEARCH_AVAILABLE = True
except ImportError:
    BROWSER_SEARCH_AVAILABLE = False
    SearchResult = None
    SearchTarget = None

# 向量数据库 (可选)
try:
    from langchain.vectorstores import Chroma
    from langchain.embeddings import OpenAIEmbeddings
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False


class AgentStatus(Enum):
    """Agent状态"""
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentResult:
    """Agent执行结果"""
    agent_id: str
    agent_type: str
    status: AgentStatus
    results: List[Any] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = ""


@dataclass
class SearchQuery:
    """搜索查询"""
    query_id: str
    text: str
    target: Optional[str] = None  # arxiv, github, nasa, None=全部
    max_results: int = 5
    filters: Dict[str, Any] = field(default_factory=dict)


class VectorDeduplicator:
    """
    向量去重器
    
    使用简单哈希去重，避免重复搜索结果
    """
    
    def __init__(self):
        self.seen_hashes: set = set()
        self.seen_urls: set = set()
    
    def add(self, result: SearchResult) -> bool:
        """
        添加结果，返回是否重复
        
        Args:
            result: 搜索结果
            
        Returns:
            True if duplicate, False if new
        """
        # URL去重
        if result.url in self.seen_urls:
            return True
        
        # 标题哈希去重
        title_hash = hashlib.md5(result.title.encode()).hexdigest()
        if title_hash in self.seen_hashes:
            return True
        
        # 记录
        self.seen_hashes.add(title_hash)
        self.seen_urls.add(result.url)
        
        return False
    
    def reset(self):
        """重置去重状态"""
        self.seen_hashes.clear()
        self.seen_urls.clear()


class LLMRouter:
    """
    LLM路由 - 智能分发查询到最佳Agent
    
    基于查询类型路由到对应Agent
    """
    
    # 关键词到目标的映射
    KEYWORD_MAPPING = {
        "arxiv": ["paper", "arxiv", "research", "publication", "论文", "学术"],
        "github": ["github", "code", "repository", "代码", "开源"],
        "nasa": ["nasa", "space", "telescope", "观测", "望远镜", "卫星"],
        "simbad": ["simbad", "star", "galaxy", "恒星", "星系", "天体"],
        "exoplanet": ["exoplanet", "kepler", "transit", "系外行星", "凌星"]
    }
    
    @classmethod
    def route(cls, query: str) -> List[str]:
        """
        路由查询到对应目标
        
        Args:
            query: 搜索查询文本
            
        Returns:
            目标列表，如 ["arxiv", "github", "nasa"]
        """
        query_lower = query.lower()
        targets = set()
        
        for target, keywords in cls.KEYWORD_MAPPING.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    targets.add(target)
        
        # 默认返回全部
        if not targets:
            targets = {"arxiv", "github", "nasa"}
        
        return list(targets)


class QualityFilter:
    """
    质量过滤器
    
    过滤低质量或无关结果
    """
    
    MIN_TITLE_LENGTH = 10
    MIN_SNIPPET_LENGTH = 20
    
    # 无关关键词
    IRRELEVANT_KEYWORDS = [
        "spam", "advertisement", "sponsored",
        "click here", "buy now", "sign up free"
    ]
    
    @classmethod
    def is_relevant(cls, result: SearchResult) -> bool:
        """
        判断结果是否相关
        
        Args:
            result: 搜索结果
            
        Returns:
            True if relevant
        """
        # 标题太短
        if len(result.title) < cls.MIN_TITLE_LENGTH:
            return False
        
        # snippet太短
        if len(result.snippet) < cls.MIN_SNIPPET_LENGTH:
            return False
        
        # 包含无关关键词
        snippet_lower = result.snippet.lower()
        for keyword in cls.IRRELEVANT_KEYWORDS:
            if keyword in snippet_lower:
                return False
        
        return True
    
    @classmethod
    def filter(cls, results: List[SearchResult]) -> List[SearchResult]:
        """
        过滤结果
        
        Args:
            results: 搜索结果列表
            
        Returns:
            过滤后的结果
        """
        return [r for r in results if cls.is_relevant(r)]


class BaseSearchAgent:
    """搜索Agent基类"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        self.browser: Optional[BrowserSearch] = None
    
    async def initialize(self):
        """初始化Agent"""
        if BROWSER_SEARCH_AVAILABLE:
            self.browser = BrowserSearch()
            await self.browser.initialize()
    
    async def cleanup(self):
        """清理资源"""
        if self.browser:
            await self.browser.close()
    
    async def search(self, query: str, max_results: int = 5) -> AgentResult:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            Agent执行结果
        """
        start_time = time.time()
        self.status = AgentStatus.WORKING
        
        result = AgentResult(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=AgentStatus.WORKING,
            timestamp=datetime.now().isoformat()
        )
        
        try:
            if not self.browser:
                raise RuntimeError("Browser not initialized")
            
            raw_results = await self.browser.search_all(query, max_results)
            
            # 提取本Agent对应的结果
            agent_results = raw_results.get(self.agent_type, [])
            
            # 质量过滤
            filtered = QualityFilter.filter(agent_results)
            
            result.results = filtered
            result.status = AgentStatus.COMPLETED
            
        except Exception as e:
            result.error = str(e)
            result.status = AgentStatus.FAILED
        
        finally:
            result.duration = time.time() - start_time
            self.status = result.status
        
        return result


class ArxivSearchAgent(BaseSearchAgent):
    """arXiv论文搜索Agent"""
    
    def __init__(self):
        super().__init__(
            agent_id=f"arxiv_{uuid.uuid4().hex[:8]}",
            agent_type="arxiv"
        )


class GithubSearchAgent(BaseSearchAgent):
    """GitHub代码搜索Agent"""
    
    def __init__(self):
        super().__init__(
            agent_id=f"github_{uuid.uuid4().hex[:8]}",
            agent_type="github"
        )


class DataSearchAgent(BaseSearchAgent):
    """
    多源数据搜索Agent
    
    搜索: NASA + SIMBAD + WISE + Chandra等天文数据源
    """
    
    def __init__(self):
        super().__init__(
            agent_id=f"data_{uuid.uuid4().hex[:8]}",
            agent_type="nasa"
        )


class MultiAgentSearchCoordinator:
    """
    多Agent搜索协调器
    
    特性:
    - 3-Agent并行搜索
    - 故障隔离 (一个失败不影响其他)
    - 向量去重
    - 质量过滤
    - LLM路由
    """
    
    def __init__(self, max_parallel: int = 3):
        """
        初始化协调器
        
        Args:
            max_parallel: 最大并行Agent数
        """
        self.max_parallel = max_parallel
        self.agents: List[BaseSearchAgent] = []
        self.deduplicator = VectorDeduplicator()
        self.results: Dict[str, AgentResult] = {}
    
    async def initialize(self):
        """初始化所有Agent"""
        self.agents = [
            ArxivSearchAgent(),
            GithubSearchAgent(),
            DataSearchAgent()
        ]
        
        for agent in self.agents:
            await agent.initialize()
    
    async def cleanup(self):
        """清理所有Agent资源"""
        for agent in self.agents:
            await agent.cleanup()
    
    async def _run_agent(
        self, 
        agent: BaseSearchAgent, 
        query: str, 
        max_results: int
    ) -> AgentResult:
        """
        运行单个Agent
        
        Args:
            agent: Agent实例
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            Agent执行结果
        """
        return await agent.search(query, max_results)
    
    async def search_all(
        self, 
        query: str, 
        max_results_per_agent: int = 5,
        use_llm_routing: bool = True
    ) -> Dict[str, Any]:
        """
        并行搜索所有目标
        
        Args:
            query: 搜索查询
            max_results_per_agent: 每个Agent的最大结果数
            use_llm_routing: 是否使用LLM路由
            
        Returns:
            搜索结果字典
        """
        if not self.agents:
            await self.initialize()
        
        # LLM路由决定哪些Agent需要执行
        if use_llm_routing:
            targets = LLMRouter.route(query)
            active_agents = [
                agent for agent in self.agents 
                if agent.agent_type in targets
            ]
        else:
            active_agents = self.agents
        
        # 重置去重器
        self.deduplicator.reset()
        
        # 并行执行 (最多max_parallel个)
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def bounded_search(agent):
            async with semaphore:
                return await self._run_agent(agent, query, max_results_per_agent)
        
        # 启动所有Agent
        tasks = [bounded_search(agent) for agent in active_agents]
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        all_results = []
        for i, result in enumerate(agent_results):
            if isinstance(result, Exception):
                # 异常处理
                self.results[active_agents[i].agent_id] = AgentResult(
                    agent_id=active_agents[i].agent_id,
                    agent_type=active_agents[i].agent_type,
                    status=AgentStatus.FAILED,
                    error=str(result)
                )
            else:
                self.results[result.agent_id] = result
                all_results.extend(result.results)
        
        # 去重
        deduplicated = []
        for result in all_results:
            if not self.deduplicator.add(result):
                deduplicated.append(result)
        
        return {
            "query": query,
            "total_results": len(deduplicated),
            "by_agent": {
                agent.agent_type: [r.to_dict() for r in self.results[agent.agent_id].results]
                for agent in self.agents
                if agent.agent_id in self.results
            },
            "all": [r.to_dict() for r in deduplicated],
            "errors": {
                agent_id: r.error
                for agent_id, r in self.results.items()
                if r.status == AgentStatus.FAILED
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "duration": sum(r.duration for r in self.results.values()),
                "agents_used": len(active_agents)
            }
        }
    
    async def search_single(
        self, 
        agent_type: str, 
        query: str, 
        max_results: int = 5
    ) -> AgentResult:
        """
        搜索单个目标
        
        Args:
            agent_type: Agent类型 (arxiv/github/nasa)
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            Agent执行结果
        """
        if not self.agents:
            await self.initialize()
        
        agent = next(
            (a for a in self.agents if a.agent_type == agent_type),
            None
        )
        
        if not agent:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return await agent.search(query, max_results)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_agents": len(self.agents),
            "active_agents": sum(
                1 for r in self.results.values() 
                if r.status == AgentStatus.WORKING
            ),
            "completed_agents": sum(
                1 for r in self.results.values() 
                if r.status == AgentStatus.COMPLETED
            ),
            "failed_agents": sum(
                1 for r in self.results.values() 
                if r.status == AgentStatus.FAILED
            ),
            "total_duration": sum(r.duration for r in self.results.values()),
            "total_results": sum(len(r.results) for r in self.results.values())
        }


# 便捷函数
async def parallel_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    并行搜索 (自动初始化和清理)
    
    用法:
        results = await parallel_search("exoplanet detection")
    """
    coordinator = MultiAgentSearchCoordinator()
    
    try:
        await coordinator.initialize()
        return await coordinator.search_all(query, max_results)
    finally:
        await coordinator.cleanup()


async def search_with_fallback(
    query: str, 
    max_results: int = 5
) -> Dict[str, Any]:
    """
    带降级的搜索 (浏览器失败时使用API)
    
    用法:
        results = await search_with_fallback("machine learning")
    """
    try:
        # 优先使用浏览器搜索
        return await parallel_search(query, max_results)
    except Exception as e:
        print(f"Browser search failed: {e}")
        print("Fallback to API search...")
        # TODO: 实现API降级
        return {
            "query": query,
            "error": str(e),
            "fallback": "not_implemented"
        }


if __name__ == "__main__":
    # 测试
    async def test():
        print("Testing MultiAgentSearchCoordinator...")
        
        coordinator = MultiAgentSearchCoordinator()
        
        try:
            await coordinator.initialize()
            
            # 测试并行搜索
            results = await coordinator.search_all("machine learning astronomy", max_results_per_agent=3)
            
            print(f"\n=== Search Results ===")
            print(f"Query: {results['query']}")
            print(f"Total results: {results['total_results']}")
            print(f"Agents used: {results['metadata']['agents_used']}")
            print(f"Duration: {results['metadata']['duration']:.2f}s")
            
            print(f"\nBy agent:")
            for agent_type, agent_results in results['by_agent'].items():
                print(f"  {agent_type}: {len(agent_results)} results")
            
            if results['errors']:
                print(f"\nErrors: {results['errors']}")
            
            print(f"\nStatistics:")
            print(f"  {coordinator.get_statistics()}")
            
        finally:
            await coordinator.cleanup()
    
    asyncio.run(test())
