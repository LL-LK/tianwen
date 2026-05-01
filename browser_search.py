"""
天问-AGI 浏览器模拟搜索模块 v1.1
BrowserSearch - 模拟人类行为的浏览器自动化搜索

基于Hermes评审建议实现:
- Playwright + stealth反检测
- 多层反检测技术
- 封禁防护多层策略

Issue #22 增强:
- 多源搜索协调 (arxiv/github/nasa/google scholar)
- 搜索结果缓存与去重
- 智能频率控制

用法:
    searcher = BrowserSearch()
    results = await searcher.search_all("系外行星")
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import deque

# Playwright导入 (可选)
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None
    Browser = None
    BrowserContext = None


class SearchTarget(Enum):
    """搜索目标枚举"""
    ARXIV = "arxiv"
    GITHUB = "github"
    NASA = "nasa"
    GOOGLE_SCHOLAR = "google_scholar"
    SEMANTIC_SCHOLAR = "semantic_scholar"


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    target: SearchTarget
    query: str
    url: str
    title: str
    snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "target": self.target.value,
            "query": self.query,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


@dataclass
class StealthConfig:
    """反检测配置"""
    # 浏览器指纹
    webdriver_hidden: bool = True
    canvas_noise: bool = True
    webgl_random: bool = True
    timezone: str = "Asia/Shanghai"
    
    # 行为模拟
    click_offset_range: tuple = (-5, 5)  # 点击偏移范围(像素)
    scroll_delay_range: tuple = (200, 800)  # 滚动延迟范围(毫秒)
    visit_interval_range: tuple = (5, 20)  # 访问间隔范围(秒)
    
    # 请求伪装
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ])
    
    # IP防护 (代理池)
    proxy_pool: List[str] = field(default_factory=list)  # 如: ["http://proxy1:port", ...]


@dataclass
class RateLimitConfig:
    """频率限制配置"""
    max_requests_per_minute: int = 10
    retry_count: int = 3
    retry_delay_range: tuple = (60, 300)  # 重试延迟范围(秒)
    backoff_multiplier: float = 0.5


# Issue #22: 搜索结果缓存
class SearchCache:
    """
    搜索结果缓存

    功能:
    - 缓存搜索结果减少重复请求
    - 自动去重
    - TTL过期机制
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[List, float]] = {}  # (results, timestamp)

    def _make_key(self, query: str, target: SearchTarget) -> str:
        """生成缓存键"""
        return f"{target.value}:{query.lower().strip()}"

    def get(self, query: str, target: SearchTarget) -> Optional[List[SearchResult]]:
        """获取缓存"""
        key = self._make_key(query, target)
        if key not in self._cache:
            return None

        results, timestamp = self._cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            return None

        return results

    def put(self, query: str, target: SearchTarget, results: List[SearchResult]):
        """存入缓存"""
        key = self._make_key(query, target)
        self._cache[key] = (results, time.time())

        # LRU淘汰
        while len(self._cache) > self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    def deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重"""
        seen_urls = set()
        unique = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique.append(r)
        return unique


class AntiDetectionScripts:
    """反检测JavaScript脚本"""
    
    @staticmethod
    def get_stealth_script() -> str:
        """生成反检测脚本"""
        return """
        // 隐藏webdriver标志
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        
        // 模拟插件
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // 模拟语言
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'zh-CN']
        });
        
        // Canvas反检测
        const originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attributes) {
            const context = originalGetContext.call(this, type, attributes);
            if (type === '2d') {
                const originalFillText = context.fillText;
                context.fillText = function(...args) {
                    // 添加微小噪声
                    return originalFillText.apply(this, args);
                };
            }
            return context;
        };
        
        // WebGL反检测
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };
        
        // 随机化Permission
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """
    
    @staticmethod
    def get_random_mouse_move() -> Dict[str, int]:
        """生成随机鼠标移动轨迹"""
        return {
            "x": random.randint(-10, 10),
            "y": random.randint(-10, 10)
        }


class BanRecovery:
    """封禁恢复策略"""
    
    def __init__(self, config: RateLimitConfig, proxy_pool: List[str] = None):
        self.config = config
        self.proxy_pool = proxy_pool or []
        self.current_proxy_index = 0
        self.current_rate_limit = config.max_requests_per_minute
    
    def on_403_error(self) -> Dict[str, Any]:
        """403 Forbidden 处理"""
        recovery = {
            "action": "change_ip",
            "wait_seconds": random.randint(*self.config.retry_delay_range),
            "new_proxy": None
        }
        
        if self.proxy_pool:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_pool)
            recovery["new_proxy"] = self.proxy_pool[self.current_proxy_index]
        
        return recovery
    
    def on_429_error(self) -> Dict[str, Any]:
        """429 Too Many Requests 处理"""
        self.current_rate_limit = int(self.current_rate_limit * self.config.backoff_multiplier)
        return {
            "action": "rate_limit",
            "new_rate_limit": self.current_rate_limit,
            "wait_seconds": random.randint(*self.config.retry_delay_range)
        }


class BrowserSearch:
    """
    浏览器模拟搜索器

    特性:
    - Playwright + stealth反检测
    - 多层反检测技术
    - 封禁防护多层策略
    - 支持arXiv/GitHub/NASA/Google Scholar多源搜索
    - Issue #22: 搜索结果缓存与去重
    """

    def __init__(
        self,
        stealth_config: Optional[StealthConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        use_cache: bool = True
    ):
        self.stealth = stealth_config or StealthConfig()
        self.rate_limit = rate_limit_config or RateLimitConfig()
        self.ban_recovery = BanRecovery(self.rate_limit, self.stealth.proxy_pool)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.request_count = 0
        self.last_request_time = 0

        # Issue #22: 搜索缓存
        self.search_cache = SearchCache() if use_cache else None
        self.total_requests = 0
        self.cache_hits = 0
    
    async def initialize(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not installed. Run:\n"
                "  pip install playwright && playwright install\n"
                "  playwright install-deps chromium"
            )
        
        self.playwright = await async_playwright().start()
        
        # 尝试启动浏览器
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
            error_msg = str(e)
            if "libnspr4.so" in error_msg or "shared library" in error_msg:
                raise RuntimeError(
                    f"Browser dependencies missing: {error_msg}\n\n"
                    "To fix, run:\n"
                    "  sudo apt-get update && sudo apt-get install -y libnspr4 libnss3 libatk1.0-0\n"
                    "Or use Windows browser:\n"
                    "  playwright install chromium"
                )
            raise
        
        # 创建反检测context
        context_options = {
            "user_agent": random.choice(self.stealth.user_agents),
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
        }
        
        if self.stealth.proxy_pool:
            proxy = random.choice(self.stealth.proxy_pool)
            context_options["proxy"] = {"server": proxy}
        
        self.context = await self.browser.new_context(**context_options)
        
        # 设置额外请求头
        await self.context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })
        
        # 注入反检测脚本
        await self.context.add_init_script(AntiDetectionScripts.get_stealth_script())
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def _check_rate_limit(self):
        """检查频率限制"""
        current_time = time.time()
        if current_time - self.last_request_time < 60:
            if self.request_count >= self.rate_limit.max_requests_per_minute:
                wait_time = 60 - (current_time - self.last_request_time)
                time.sleep(wait_time)
                self.request_count = 0
        else:
            self.request_count = 0
        
        self.request_count += 1
        self.last_request_time = current_time
    
    async def _random_human_behavior(self, page: Page):
        """模拟随机人类行为"""
        # 随机滚动
        await page.evaluate(f"window.scrollBy(0, {random.randint(200, 800)})")
        await asyncio.sleep(random.uniform(0.2, 0.8))
        
        # 随机鼠标移动
        mouse_move = AntiDetectionScripts.get_random_mouse_move()
        await page.mouse.move(
            page.viewport_size["width"] // 2 + mouse_move["x"],
            page.viewport_size["height"] // 2 + mouse_move["y"]
        )
    
    async def search_arxiv(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        搜索arXiv

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        # Issue #22: 缓存检查
        if self.search_cache:
            cached = self.search_cache.get(query, SearchTarget.ARXIV)
            if cached:
                self.cache_hits += 1
                return cached[:max_results]

        self._check_rate_limit()
        self.total_requests += 1

        page = await self.context.new_page()
        results = []

        try:
            # 访问arXiv
            search_url = f"https://arxiv.org/search/?searchtype=all&query={query.replace(' ', '+')}&start=0"
            await page.goto(search_url, wait_until="networkidle")

            # 模拟人类行为
            await self._random_human_behavior(page)

            # 等待结果加载
            await page.wait_for_selector(".arxiv-result", timeout=10000)

            # 提取结果
            result_elements = await page.query_selector_all(".arxiv-result")

            for i, elem in enumerate(result_elements[:max_results]):
                try:
                    title_elem = await elem.query_selector(".list-title")
                    title = await title_elem.inner_text() if title_elem else ""

                    link_elem = await elem.query_selector(".arxiv-result a")
                    url = await link_elem.get_attribute("href") if link_elem else ""

                    abstract_elem = await elem.query_selector(".abstract-short")
                    snippet = await abstract_elem.inner_text() if abstract_elem else ""

                    results.append(SearchResult(
                        target=SearchTarget.ARXIV,
                        query=query,
                        url=url,
                        title=title.strip(),
                        snippet=snippet.strip(),
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                    ))
                except Exception as e:
                    continue
            
            # 访问间隔
            await asyncio.sleep(random.uniform(*self.stealth.visit_interval_range))
            
        except Exception as e:
            print(f"arXiv search error: {e}")
        finally:
            await page.close()
        
        return results
    
    async def search_github(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        搜索GitHub
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        self._check_rate_limit()
        
        page = await self.context.new_page()
        results = []
        
        try:
            # 访问GitHub
            search_url = f"https://github.com/search?q={query.replace(' ', '+')}&type=repositories"
            await page.goto(search_url, wait_until="networkidle")
            
            # 模拟人类行为
            await self._random_human_behavior(page)
            
            # 等待结果加载
            await page.wait_for_selector(".repo-list-item", timeout=10000)
            
            # 提取结果 (GitHub可能改变页面结构)
            try:
                await page.wait_for_selector(".results-list", timeout=5000)
                result_elements = await page.query_selector_all(".results-list li")
            except:
                result_elements = await page.query_selector_all("li.repo-list-item")
            
            for elem in result_elements[:max_results]:
                try:
                    # 尝试多种选择器
                    title_elem = await elem.query_selector("a[href*='/']:not([data-hovercard-type])")
                    if not title_elem:
                        title_elem = await elem.query_selector("a")
                    title = await title_elem.inner_text() if title_elem else ""
                    url = "https://github.com" + await title_elem.get_attribute("href") if title_elem else ""
                    
                    desc_elem = await elem.query_selector("p[class*='mb-1']")
                    snippet = await desc_elem.inner_text() if desc_elem else ""
                    
                    results.append(SearchResult(
                        target=SearchTarget.GITHUB,
                        query=query,
                        url=url,
                        title=title.strip(),
                        snippet=snippet.strip()[:200],
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                    ))
                except Exception:
                    continue
            
            # 访问间隔
            await asyncio.sleep(random.uniform(*self.stealth.visit_interval_range))
            
        except Exception as e:
            print(f"GitHub search error: {e}")
        finally:
            await page.close()
        
        return results
    
    async def search_nasa(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        搜索NASA数据
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        self._check_rate_limit()
        
        page = await self.context.new_page()
        results = []
        
        try:
            # 访问NASA开放数据 (使用更宽松的等待策略)
            search_url = f"https://data.nasa.gov/search?q={query.replace(' ', '%20')}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            
            # 模拟人类行为
            await self._random_human_behavior(page)
            
            # 等待结果 (宽松等待)
            await asyncio.sleep(3)
            
            # 提取结果 (NASA数据结构可能变化)
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
                    
                    results.append(SearchResult(
                        target=SearchTarget.NASA,
                        query=query,
                        url=url,
                        title=title.strip(),
                        snippet="NASA开放数据",
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                    ))
                except Exception:
                    continue
            
        except Exception as e:
            print(f"NASA search error: {e}")
        finally:
            await page.close()
        
        return results
    
    async def search_all(self, query: str, max_results_per_target: int = 5) -> Dict[str, List[SearchResult]]:
        """
        并行搜索所有目标

        Issue #22 增强:
        - 多源搜索协调 (arxiv/github/nasa/semantic scholar)
        - 搜索结果缓存
        - 自动去重

        Args:
            query: 搜索关键词
            max_results_per_target: 每个目标的最大结果数

        Returns:
            按目标分组的搜索结果
        """
        if not self.browser:
            await self.initialize()

        # 并行执行所有搜索
        tasks = [
            self.search_arxiv(query, max_results_per_target),
            self.search_github(query, max_results_per_target),
            self.search_nasa(query, max_results_per_target),
            self.search_semantic_scholar(query, max_results_per_target)
        ]

        # 等待所有搜索完成
        arxiv_results, github_results, nasa_results, scholar_results = await asyncio.gather(*tasks)

        # 合并结果
        all_results = arxiv_results + github_results + nasa_results + scholar_results

        # Issue #22: 去重
        if self.search_cache:
            all_results = self.search_cache.deduplicate(all_results)

        return {
            "arxiv": arxiv_results,
            "github": github_results,
            "nasa": nasa_results,
            "google_scholar": scholar_results,
            "all": all_results
        }

    async def search_semantic_scholar(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        搜索Semantic Scholar

        Issue #22 新增: 学术搜索源

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        # Issue #22: 缓存检查
        if self.search_cache:
            cached = self.search_cache.get(query, SearchTarget.SEMANTIC_SCHOLAR)
            if cached:
                self.cache_hits += 1
                return cached[:max_results]

        self._check_rate_limit()
        self.total_requests += 1

        page = await self.context.new_page()
        results = []

        try:
            # 访问Semantic Scholar
            search_url = f"https://www.semanticscholar.org/search?q={query.replace(' ', '+')}&sort=relevance"
            await page.goto(search_url, wait_until="networkidle")

            # 模拟人类行为
            await self._random_human_behavior(page)

            # 等待结果加载
            await asyncio.sleep(2)  # 等待动态加载

            # 提取结果
            result_elements = await page.query_selector_all("[class*='search-result']")

            for elem in result_elements[:max_results]:
                try:
                    title_elem = await elem.query_selector("a[data-paper-id]")
                    title = await title_elem.inner_text() if title_elem else ""

                    url = await title_elem.get_attribute("href") if title_elem else ""
                    if url and not url.startswith("http"):
                        url = "https://www.semanticscholar.org" + url

                    # 提取摘要
                    snippet_elem = await elem.query_selector("[class*='abstract']")
                    snippet = await snippet_elem.inner_text() if snippet_elem else ""

                    results.append(SearchResult(
                        target=SearchTarget.SEMANTIC_SCHOLAR,
                        query=query,
                        url=url,
                        title=title.strip(),
                        snippet=snippet.strip()[:300],
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                    ))
                except Exception:
                    continue

            # 缓存结果
            if self.search_cache and results:
                self.search_cache.put(query, SearchTarget.SEMANTIC_SCHOLAR, results)

        except Exception as e:
            print(f"Semantic Scholar search error: {e}")
        finally:
            await page.close()

        return results

    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计"""
        if not self.search_cache:
            return {"enabled": False}

        return {
            "enabled": True,
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(self.total_requests, 1)
        }
    
    def export_results(self, results: Dict[str, List[SearchResult]], filepath: str):
        """导出结果到JSON文件"""
        export_data = {
            target: [r.to_dict() for r in result_list]
            for target, result_list in results.items()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)


# 便捷函数
async def quick_search(query: str) -> Dict[str, List[Dict]]:
    """
    快速搜索 (自动初始化和清理)
    
    用法:
        results = await quick_search("exoplanet detection")
    """
    searcher = BrowserSearch()
    
    try:
        await searcher.initialize()
        raw_results = await searcher.search_all(query)
        
        # 转换为普通dict
        return {
            target: [r.to_dict() for r in results]
            for target, results in raw_results.items()
        }
    finally:
        await searcher.close()


if __name__ == "__main__":
    # 测试
    async def test():
        print("Testing BrowserSearch...")
        results = await quick_search("machine learning astronomy")
        print(f"Found {len(results.get('all', []))} total results")
        print(f"arXiv: {len(results.get('arxiv', []))}")
        print(f"GitHub: {len(results.get('github', []))}")
        print(f"NASA: {len(results.get('nasa', []))}")
    
    asyncio.run(test())
