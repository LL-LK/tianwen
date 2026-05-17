"""
天问-AGI 浏览器Agent模块
BrowserAgent - Playwright浏览器自动化搜索

Issue #68

功能:
- BrowserController: Playwright浏览器生命周期管理
- SearchEngineAdapter: 多引擎搜索适配
- WebPageParser: HTML结构化数据提取
- SearchResultRanker: 搜索结果相关性排序

依赖:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import asyncio
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger("browser_agent")

# ============ 类型定义 ============

class SearchEngine(Enum):
    """支持的搜索引擎"""
    ARXIV = "arxiv"
    GITHUB = "github"
    NASA = "nasa"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    GOOGLE_SCHOLAR = "google_scholar"


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    engine: SearchEngine
    query: str
    url: str
    title: str
    snippet: str
    rank: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            "engine": self.engine.value,
            "query": self.query,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "rank": self.rank,
            "metadata": self.metadata,
            "timestamp": self.timestamp or datetime.now().isoformat()
        }


@dataclass
class StealthConfig:
    """反检测配置"""
    webdriver_hidden: bool = True
    canvas_noise: bool = True
    webgl_random: bool = True
    timezone: str = "Asia/Shanghai"

    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ])

    proxy_pool: List[str] = field(default_factory=list)


# ============ 浏览器控制器 ============

class BrowserController:
    """
    Playwright浏览器生命周期管理

    功能:
    - 浏览器启动/关闭
    - Context管理
    - 反检测脚本注入
    """

    def __init__(self, stealth_config: Optional[StealthConfig] = None):
        self.stealth_config = stealth_config or StealthConfig()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        self._initialized = False

    async def initialize(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not installed. Run:\n"
                "  pip install playwright && playwright install chromium"
            )

        if self._initialized:
            return

        self.playwright = await async_playwright().start()

        try:
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-gpu'
                ]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to launch browser: {e}")

        context_options = {
            "user_agent": random.choice(self.stealth_config.user_agents),
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
        }

        if self.stealth_config.proxy_pool:
            proxy = random.choice(self.stealth_config.proxy_pool)
            context_options["proxy"] = {"server": proxy}

        self.context = await self.browser.new_context(**context_options)
        await self.context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

        # 注入反检测脚本
        await self.context.add_init_script(self._get_stealth_script())

        self._initialized = True
        logger.info("BrowserController initialized")

    def _get_stealth_script(self) -> str:
        """生成反检测脚本"""
        return """
        Object.defineProperty(navigator, 'webdriver', {get: () => false});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'zh-CN']});
        """

    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._initialized = False
        logger.info("BrowserController closed")

    async def new_page(self) -> Page:
        """创建新页面"""
        if not self._initialized:
            await self.initialize()
        return await self.context.new_page()

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# ============ 网页解析器 ============

class WebPageParser:
    """
    HTML结构化数据提取

    功能:
    - CSS选择器提取
    - XPath提取
    - 结构化数据转换
    """

    @staticmethod
    async def extract_by_selector(
        page: Page,
        selector: str,
        attr: Optional[str] = None
    ) -> List[str]:
        """通过CSS选择器提取数据"""
        elements = await page.query_selector_all(selector)
        results = []

        for elem in elements:
            if attr:
                value = await elem.get_attribute(attr)
            else:
                value = await elem.inner_text()
            if value:
                results.append(value.strip())

        return results

    @staticmethod
    async def extract_arxiv_results(page: Page, max_results: int = 10) -> List[Dict[str, str]]:
        """提取arXiv搜索结果"""
        results = []

        try:
            await page.wait_for_selector(".arxiv-result", timeout=10000)
            result_elements = await page.query_selector_all(".arxiv-result")

            for elem in result_elements[:max_results]:
                try:
                    title_elem = await elem.query_selector(".list-title")
                    title = await title_elem.inner_text() if title_elem else ""

                    link_elem = await elem.query_selector(".arxiv-result a")
                    url = await link_elem.get_attribute("href") if link_elem else ""

                    abstract_elem = await elem.query_selector(".abstract-short")
                    snippet = await abstract_elem.inner_text() if abstract_elem else ""

                    results.append({
                        "title": title.strip(),
                        "url": url,
                        "snippet": snippet.strip()
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract arXiv results: {e}")

        return results

    @staticmethod
    async def extract_github_results(page: Page, max_results: int = 10) -> List[Dict[str, str]]:
        """提取GitHub搜索结果"""
        results = []

        try:
            await page.wait_for_selector(".repo-list-item", timeout=10000)
            result_elements = await page.query_selector_all("li.repo-list-item")

            for elem in result_elements[:max_results]:
                try:
                    title_elem = await elem.query_selector("a")
                    title = await title_elem.inner_text() if title_elem else ""
                    url = "https://github.com" + await title_elem.get_attribute("href") if title_elem else ""

                    desc_elem = await elem.query_selector("p[class*='mb-1']")
                    snippet = await desc_elem.inner_text() if desc_elem else ""

                    results.append({
                        "title": title.strip(),
                        "url": url,
                        "snippet": snippet.strip()[:200]
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract GitHub results: {e}")

        return results

    @staticmethod
    async def extract_nasa_results(page: Page, max_results: int = 10) -> List[Dict[str, str]]:
        """提取NASA搜索结果"""
        results = []

        try:
            await asyncio.sleep(3)  # 等待动态加载
            result_elements = await page.query_selector_all("[class*='resource-item']")

            if not result_elements:
                result_elements = await page.query_selector_all("a[href*='/dataset/']")

            for elem in result_elements[:max_results]:
                try:
                    title_elem = await elem.query_selector("a")
                    title = await title_elem.inner_text() if title_elem else ""
                    url = await title_elem.get_attribute("href") if title_elem else ""

                    if url and not url.startswith("http"):
                        url = "https://data.nasa.gov" + url

                    results.append({
                        "title": title.strip(),
                        "url": url,
                        "snippet": "NASA开放数据"
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract NASA results: {e}")

        return results


# ============ 搜索引擎适配器 ============

class SearchEngineAdapter:
    """
    多引擎搜索适配

    功能:
    - 统一搜索接口
    - 结果标准化
    - 频率控制
    """

    def __init__(self, controller: BrowserController):
        self.controller = controller
        self.parser = WebPageParser()
        self.request_count = 0
        self.last_request_time = 0
        self.max_requests_per_minute = 10

    def _check_rate_limit(self):
        """检查频率限制"""
        current_time = time.time()
        if current_time - self.last_request_time < 60:
            if self.request_count >= self.max_requests_per_minute:
                wait_time = 60 - (current_time - self.last_request_time)
                time.sleep(wait_time)
                self.request_count = 0
        else:
            self.request_count = 0

        self.request_count += 1
        self.last_request_time = current_time

    async def search_arxiv(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """搜索arXiv"""
        self._check_rate_limit()

        page = await self.controller.new_page()
        results = []

        try:
            search_url = f"https://arxiv.org/search/?searchtype=all&query={query.replace(' ', '+')}&start=0"
            await page.goto(search_url, wait_until="networkidle")

            await asyncio.sleep(random.uniform(0.2, 0.8))
            await page.evaluate("window.scrollBy(0, 300)")

            extracted = await self.parser.extract_arxiv_results(page, max_results)

            for i, item in enumerate(extracted):
                results.append(SearchResult(
                    engine=SearchEngine.ARXIV,
                    query=query,
                    url=item["url"],
                    title=item["title"],
                    snippet=item["snippet"],
                    rank=1.0 / (i + 1),
                    timestamp=datetime.now().isoformat()
                ))

            await asyncio.sleep(random.uniform(5, 15))

        except Exception as e:
            logger.error(f"arXiv search error: {e}")
        finally:
            await page.close()

        return results

    async def search_github(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """搜索GitHub"""
        self._check_rate_limit()

        page = await self.controller.new_page()
        results = []

        try:
            search_url = f"https://github.com/search?q={query.replace(' ', '+')}&type=repositories"
            await page.goto(search_url, wait_until="networkidle")

            await asyncio.sleep(random.uniform(0.2, 0.8))
            await page.evaluate("window.scrollBy(0, 300)")

            extracted = await self.parser.extract_github_results(page, max_results)

            for i, item in enumerate(extracted):
                results.append(SearchResult(
                    engine=SearchEngine.GITHUB,
                    query=query,
                    url=item["url"],
                    title=item["title"],
                    snippet=item["snippet"],
                    rank=1.0 / (i + 1),
                    timestamp=datetime.now().isoformat()
                ))

            await asyncio.sleep(random.uniform(5, 15))

        except Exception as e:
            logger.error(f"GitHub search error: {e}")
        finally:
            await page.close()

        return results

    async def search_nasa(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """搜索NASA"""
        self._check_rate_limit()

        page = await self.controller.new_page()
        results = []

        try:
            search_url = f"https://data.nasa.gov/search?q={query.replace(' ', '%20')}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

            await asyncio.sleep(3)

            extracted = await self.parser.extract_nasa_results(page, max_results)

            for i, item in enumerate(extracted):
                results.append(SearchResult(
                    engine=SearchEngine.NASA,
                    query=query,
                    url=item["url"],
                    title=item["title"],
                    snippet=item["snippet"],
                    rank=1.0 / (i + 1),
                    timestamp=datetime.now().isoformat()
                ))

        except Exception as e:
            logger.error(f"NASA search error: {e}")
        finally:
            await page.close()

        return results

    async def search_all(
        self,
        query: str,
        engines: Optional[List[SearchEngine]] = None,
        max_results_per_engine: int = 5
    ) -> Dict[str, List[SearchResult]]:
        """并行搜索所有指定引擎"""
        if not self.controller.is_initialized:
            await self.controller.initialize()

        if engines is None:
            engines = [SearchEngine.ARXIV, SearchEngine.GITHUB, SearchEngine.NASA]

        tasks = []
        for engine in engines:
            if engine == SearchEngine.ARXIV:
                tasks.append(self.search_arxiv(query, max_results_per_engine))
            elif engine == SearchEngine.GITHUB:
                tasks.append(self.search_github(query, max_results_per_engine))
            elif engine == SearchEngine.NASA:
                tasks.append(self.search_nasa(query, max_results_per_engine))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        all_results = []

        for engine, results_for_engine in zip(engines, results_list):
            if isinstance(results_for_engine, Exception):
                logger.error(f"Search failed for {engine.value}: {results_for_engine}")
                results[engine.value] = []
            else:
                results[engine.value] = results_for_engine
                all_results.extend(results_for_engine)

        results["all"] = all_results
        return results


# ============ 搜索结果排序器 ============

class SearchResultRanker:
    """
    搜索结果相关性排序

    功能:
    - 多维度评分
    - 综合排序
    - 去重
    """

    def __init__(self):
        self.weights = {
            "recency": 0.2,
            "relevance": 0.4,
            "authority": 0.3,
            "completeness": 0.1
        }

    def rank_results(
        self,
        results: List[SearchResult],
        query: str
    ) -> List[SearchResult]:
        """对搜索结果进行相关性排序"""
        if not results:
            return results

        # 计算每个结果的多维度评分
        for result in results:
            result.rank = self._calculate_rank(result, query)

        # 按评分降序排序
        return sorted(results, key=lambda r: r.rank, reverse=True)

    def _calculate_rank(self, result: SearchResult, query: str) -> float:
        """计算单个结果的综合评分"""
        query_terms = query.lower().split()

        # 相关性评分
        relevance = 0.0
        title_lower = result.title.lower()
        snippet_lower = result.snippet.lower()

        for term in query_terms:
            if term in title_lower:
                relevance += 0.5
            if term in snippet_lower:
                relevance += 0.25

        relevance = min(1.0, relevance / max(len(query_terms), 1))

        # 来源权威性评分
        authority = 0.0
        if result.engine == SearchEngine.ARXIV:
            authority = 0.9
        elif result.engine == SearchEngine.GITHUB:
            authority = 0.7
        elif result.engine == SearchEngine.NASA:
            authority = 0.8

        # 完整性评分 (基于snippet长度)
        completeness = min(1.0, len(result.snippet) / 200)

        # 综合评分
        total_rank = (
            relevance * self.weights["relevance"] +
            authority * self.weights["authority"] +
            completeness * self.weights["completeness"]
        )

        return total_rank

    def deduplicate(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """去重"""
        seen_urls = set()
        unique = []

        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique.append(r)

        return unique


# ============ 主入口类 ============

class BrowserAgent:
    """
    浏览器搜索Agent主类

    功能:
    - 生命周期管理
    - 搜索执行
    - 结果处理
    """

    def __init__(self, stealth_config: Optional[StealthConfig] = None):
        self.controller = BrowserController(stealth_config)
        self.adapter = SearchEngineAdapter(self.controller)
        self.ranker = SearchResultRanker()
        self._initialized = False

    async def initialize(self):
        """初始化Agent"""
        if self._initialized:
            return
        await self.controller.initialize()
        self._initialized = True
        logger.info("BrowserAgent initialized")

    async def search(
        self,
        query: str,
        engines: Optional[List[SearchEngine]] = None,
        max_results_per_engine: int = 5,
        ranked: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        执行搜索

        Args:
            query: 搜索关键词
            engines: 要搜索的引擎列表
            max_results_per_engine: 每个引擎的最大结果数
            ranked: 是否对结果进行相关性排序

        Returns:
            搜索结果字典
        """
        if not self._initialized:
            await self.initialize()

        raw_results = await self.adapter.search_all(
            query,
            engines,
            max_results_per_engine
        )

        # 处理结果
        all_results = raw_results.get("all", [])

        # 去重
        all_results = self.ranker.deduplicate(all_results)

        # 排序
        if ranked and all_results:
            all_results = self.ranker.rank_results(all_results, query)

        # 转换为dict
        output = {
            "arxiv": [r.to_dict() for r in raw_results.get("arxiv", [])],
            "github": [r.to_dict() for r in raw_results.get("github", [])],
            "nasa": [r.to_dict() for r in raw_results.get("nasa", [])],
            "all": [r.to_dict() for r in all_results],
            "count": {
                "arxiv": len(raw_results.get("arxiv", [])),
                "github": len(raw_results.get("github", [])),
                "nasa": len(raw_results.get("nasa", [])),
                "total": len(all_results)
            }
        }

        return output

    async def close(self):
        """关闭Agent"""
        await self.controller.close()
        self._initialized = False
        logger.info("BrowserAgent closed")


# ============ 便捷函数 ============

async def quick_search(
    query: str,
    engines: Optional[List[SearchEngine]] = None
) -> Dict[str, List[Dict]]:
    """
    快速搜索 (自动初始化和清理)

    用法:
        results = await quick_search("exoplanet detection")
    """
    agent = BrowserAgent()

    try:
        await agent.initialize()
        return await agent.search(query, engines)
    finally:
        await agent.close()


if __name__ == "__main__":
    async def test():
        logger.info("Testing BrowserAgent...")

        try:
            agent = BrowserAgent()
            await agent.initialize()

            results = await agent.search(
                query="machine learning astronomy",
                max_results_per_engine=3
            )

            logger.info(f"Total results: {results['count']['total']}")
            for engine, items in results.items():
                if engine == "count":
                    continue
                logger.info(f"  {engine}: {len(items)} results")

            await agent.close()

        except Exception as e:
            logger.error(f"Test failed: {e}")

    asyncio.run(test())
