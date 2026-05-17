"""
天问-AGI 文献调研模块 v2.1
LiteratureResearcher - 多数据源完整研究闭环实现

功能:
- 多数据源论文搜索 (arXiv, OpenAlex, Semantic Scholar)
- arXiv论文搜索与爬取
- 研究现状深度分析
- Gap识别与研究机会发现
- 研究假说生成
- 与天文观测系统联动
- ChromaDB向量存储接口 (预留RAG增强)
- 多种格式导出
"""
import logging
logger = logging.getLogger(__name__)

import asyncio
import json
import re
import math
import os
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlencode
import urllib.request
import urllib.error

from src.utils.logger import get_logger

logger = get_logger(__name__)

# PDF解析 - pdfplumber用于表格和文本提取
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# ============ 数据模型 ============

# 从统一模块导入 Paper 数据模型
from src.utils.models import Paper

@dataclass
class ResearchGap:
    """研究空白/Gap"""
    id: str
    category: str           # methodology, application, dataset, evaluation, theory
    description: str
    evidence: List[str]
    opportunity: str
    priority: str           # high, medium, low
    supporting_papers: List[str] = field(default_factory=list)

@dataclass
class ResearchHypothesis:
    """研究假说"""
    id: str
    hypothesis: str         # 假说内容 "如果...那么..."
    based_on: str           # 基于什么
    evidence: List[str]     # 支撑证据
    testable: bool          # 是否可验证
    related_gap: str        # 关联的Gap
    suggested_method: str   # 建议验证方法

@dataclass
class ResearchState:
    """研究现状分析结果"""
    query: str
    total_results: int
    papers: List[Paper]
    key_themes: List[str]
    research_gaps: List[ResearchGap]
    timeline: Dict[str, int]
    top_authors: List[Tuple[str, int]]
    paper_clusters: List[List[int]] = field(default_factory=list)  # 论文聚类
    trend_direction: str = "stable"  # rising, declining, stable
    summary: str = ""
    sources_used: List[str] = field(default_factory=list)  # 使用的数据源

@dataclass
class LiteratureReview:
    """文献综述"""
    title: str
    query: str
    date: str
    sections: Dict[str, str] = field(default_factory=dict)
    references: List[Dict] = field(default_factory=list)
    gaps: List[ResearchGap] = field(default_factory=list)
    hypotheses: List[ResearchHypothesis] = field(default_factory=list)
    future_directions: List[str] = field(default_factory=list)

@dataclass
class ObservatoryLink:
    """观测站联动数据"""
    relevant_targets: List[str] = field(default_factory=list)
    suggested_observations: List[Dict] = field(default_factory=list)
    data_requirements: List[str] = field(default_factory=list)

# ============ ChromaDB向量存储接口 (预留RAG增强) ============

# 从统一模块导入向量存储实现

# ============ arXiv API 客户端 ============

class ArxivAPI:
    """arXiv API 客户端"""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, max_results: int = 50):
        self.max_results = max_results
        self.rate_limit_delay = 3.0
        self.last_call_time = 0

    async def _rate_limit(self):
        import time
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_call_time = time.time()

    async def search(self, query: str, max_results: int = None,
                     sort_by: str = "relevance") -> List[Paper]:
        """搜索论文"""
        max_results = max_results or self.max_results

        await self._rate_limit()

        # 优化查询语法
        search_query = self._optimize_query(query)

        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': 'descending'
        }

        url = f"{self.BASE_URL}?{urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Tianwen-AGI/1.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                xml_content = response.read().decode('utf-8')

            return self._parse_xml(xml_content)

        except urllib.error.HTTPError as e:
            logger.warning(f"ArXiv HTTP Error: {e.code} - {e.reason}")
            return []
        except Exception as e:
            logger.error(f"ArXiv Search error: {e}")
            return []

    async def search_by_author(self, author: str, max_results: int = 30) -> List[Paper]:
        """按作者搜索"""
        return await self.search(f"au:{author}", max_results, sort_by="submittedDate")

    async def get_paper_by_id(self, arxiv_id: str) -> Optional[Paper]:
        """根据ID获取单篇论文"""
        await self._rate_limit()

        clean_id = arxiv_id.replace('arXiv:', '').strip()

        params = {
            'id_list': clean_id,
            'max_results': 1
        }

        url = f"{self.BASE_URL}?{urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Tianwen-AGI/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                xml_content = response.read().decode('utf-8')

            papers = self._parse_xml(xml_content)
            return papers[0] if papers else None

        except Exception as e:
            logger.error(f"ArXiv Get paper error: {e}")
            return None

    async def get_related_papers(self, arxiv_id: str, max_results: int = 5) -> List[Paper]:
        """获取相关论文"""
        paper = await self.get_paper_by_id(arxiv_id)
        if not paper or not paper.categories:
            return []

        # 使用主要分类搜索相关论文
        cat = paper.categories[0]
        return await self.search(f"cat:{cat}", max_results)

    def _optimize_query(self, query: str) -> str:
        """优化查询语法"""
        # 如果包含 AND/OR/NOT 或前缀，假设用户已优化
        if any(op in query.upper() for op in ['AND', 'OR', 'NOT', 'TI:', 'AU:', 'ABS:', 'CAT:']):
            return query

        # 添加 ALL: 前缀确保搜索标题、作者、摘要
        terms = query.split()
        if len(terms) == 1:
            return f"ALL:{query}"
        else:
            return " AND ".join(f"ALL:{term}" for term in terms)

    def _parse_xml(self, xml_content: str) -> List[Paper]:
        """解析arXiv XML响应"""
        papers = []

        entries = re.findall(r'<entry>(.*?)</entry>', xml_content, re.DOTALL)

        for entry in entries:
            try:
                title = self._extract_tag(entry, 'title')
                abstract = self._extract_tag(entry, 'summary')
                published = self._extract_tag(entry, 'published')
                updated = self._extract_tag(entry, 'updated')
                arxiv_id = self._extract_tag(entry, 'id')

                authors = re.findall(r'<name>(.*?)</name>', entry)
                categories = re.findall(r'<category term="([^"]+)"', entry)

                # 提取链接
                pdf_url = ""
                for link in re.findall(r'<link[^>]+>', entry):
                    if 'title="pdf"' in link or 'type="application/pdf"' in link:
                        pdf_match = re.search(r'href="([^"]+)"', link)
                        if pdf_match:
                            pdf_url = pdf_match.group(1)
                            break

                if not pdf_url:
                    pdf_match = re.search(r'href="([^"]+pdf[^"]+)"', entry)
                    if pdf_match:
                        pdf_url = pdf_match.group(1)

                # 提取相关论文链接
                related_ids = []
                for link in re.findall(r'<link[^>]+>', entry):
                    if 'rel="related"' in link:
                        href_match = re.search(r'href="([^"]+)"', link)
                        if href_match:
                            related_url = href_match.group(1)
                            paper_id = related_url.split('/')[-1]
                            related_ids.append(paper_id)

                papers.append(Paper(
                    id=f"arxiv:{arxiv_id.split('/')[-1] if '/' in arxiv_id else arxiv_id}",
                    title=self._clean_text(title),
                    authors=authors,
                    abstract=self._clean_text(abstract),
                    categories=categories,
                    published_date=published,
                    updated_date=updated,
                    pdf_url=pdf_url,
                    arxiv_url=arxiv_id,
                    related_ids=related_ids[:5],
                    source="arxiv"
                ))

            except Exception as e:
                logger.warning(f"ArXiv Parse entry error: {e}")
                continue

        return papers

    def _extract_tag(self, text: str, tag: str) -> str:
        """提取XML标签内容"""
        match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
        return match.group(1) if match else ""

    def _clean_text(self, text: str) -> str:
        """清理XML文本"""
        text = text.replace('\n', ' ').replace('  ', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


# ============ OpenAlex API 客户端 ============

class OpenAlexClient:
    """
    OpenAlex API 客户端

    OpenAlex是一个免费、开放的学术论文索引，覆盖2亿+学术论文。
    API文档: https://api.openalex.org
    """

    BASE_URL = "https://api.openalex.org"

    def __init__(self, max_results: int = 50):
        self.max_results = min(max_results, 100)  # OpenAlex默认最大100
        self.rate_limit_delay = 0.1  # OpenAlex建议每秒最多10次请求
        self.last_call_time = 0

    async def _rate_limit(self):
        """速率限制"""
        import time
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_call_time = time.time()

    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        发送HTTP请求

        Args:
            endpoint: API端点
            params: 查询参数

        Returns:
            Dict: 响应JSON
        """
        await self._rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += f"?{urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Tianwen-AGI/1.0 (mailto:tianwen@example.com)',
                    'Accept': 'application/json'
                }
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))

        except urllib.error.HTTPError as e:
            logger.error(f"[OpenAlex] HTTP Error: {e.code} - {e.reason}")
            return None
        except Exception as e:
            logger.error(f"[OpenAlex] Request error: {e}")
            return None

    async def search(self, query: str, max_results: int = None) -> List[Paper]:
        """
        搜索论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            List[Paper]: 论文列表
        """
        max_results = max_results or self.max_results

        # OpenAlex使用search参数
        params = {
            'search': query,
            'per_page': min(max_results, 100),
            'sort': 'relevance_score:desc',
            'filter': 'doc_type:article'  # 只搜索文章
        }

        result = await self._make_request('works', params)
        if not result or 'results' not in result:
            return []

        papers = []
        for work in result['results']:
            try:
                paper = self._parse_work(work)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.error(f"[OpenAlex] Parse work error: {e}")
                continue

        return papers

    async def get_paper_by_id(self, openalex_id: str) -> Optional[Paper]:
        """
        根据OpenAlex ID获取论文

        Args:
            openalex_id: OpenAlex论文ID (如 W2893096882)

        Returns:
            Optional[Paper]: 论文对象
        """
        # 确保ID格式正确
        clean_id = openalex_id.replace('https://openalex.org/', '').strip()

        result = await self._make_request(f'works/{clean_id}')
        if not result:
            return None

        return self._parse_work(result)

    async def get_papers_by_doi(self, doi: str) -> Optional[Paper]:
        """
        根据DOI获取论文

        Args:
            doi: DOI标识符

        Returns:
            Optional[Paper]: 论文对象
        """
        # OpenAlex支持DOI检索
        params = {
            'filter': f'doi:{doi}',
            'per_page': 1
        }

        result = await self._make_request('works', params)
        if not result or 'results' not in result or len(result['results']) == 0:
            return None

        return self._parse_work(result['results'][0])

    def _parse_work(self, work: Dict) -> Optional[Paper]:
        """
        解析OpenAlex论文数据

        Args:
            work: OpenAlex论文JSON

        Returns:
            Optional[Paper]: 论文对象
        """
        try:
            # 提取ID
            openalex_id = work.get('id', '').replace('https://openalex.org/', '')

            # 提取标题
            title = work.get('title', '')

            # 提取作者
            authors = []
            for author in work.get('authorships', []):
                author_name = author.get('author', {}).get('display_name', '')
                if author_name:
                    authors.append(author_name)

            # 提取摘要
            abstract = work.get('abstract_inverted_index', '')
            if isinstance(abstract, dict):
                # 重建摘要文本
                abstract = self._reconstruct_abstract(abstract)
            else:
                abstract = abstract or ''

            # 提取分类
            categories = []
            for topic in work.get('topics', []):
                topic_name = topic.get('display_name', '')
                if topic_name:
                    categories.append(topic_name)

            # 提取日期
            publication_date = work.get('publication_date', '')
            updated_date = work.get('updated_date', '')

            # 提取引用数
            citations = work.get('cited_by_count', 0)

            # 提取链接
            pdf_url = ''
            best_oa_location = work.get('best_oa_location', {})
            if best_oa_location:
                pdf_url = best_oa_location.get('pdf_url', '')

            arxiv_url = ''
            for loc in work.get('locations', []):
                source = loc.get('source', {})
                if source and 'arxiv' in str(source).lower():
                    arxiv_url = loc.get('landing_page_url', '')
                    break

            return Paper(
                id=f"openalex:{openalex_id}",
                title=title,
                authors=authors,
                abstract=abstract,
                categories=categories,
                published_date=publication_date,
                updated_date=updated_date,
                citations=citations,
                pdf_url=pdf_url,
                arxiv_url=arxiv_url,
                source="openalex"
            )

        except Exception as e:
            logger.error(f"[OpenAlex] Parse error: {e}")
            return None

    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """
        从倒排索引重建摘要文本

        Args:
            inverted_index: OpenAlex倒排索引格式

        Returns:
            str: 摘要文本
        """
        if not inverted_index:
            return ''

        # 按位置排序重建
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))

        words.sort(key=lambda x: x[0])
        return ' '.join([w[1] for w in words])


# ============ Semantic Scholar API 客户端 ============

class SemanticScholarClient:
    """
    Semantic Scholar API 客户端

    提供引用网络分析和学术论文检索。
    API文档: https://api.semanticscholar.org
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, max_results: int = 50, api_key: str = None):
        """
        初始化Semantic Scholar客户端

        Args:
            max_results: 最大结果数
            api_key: API Key (可选，免费申请)
        """
        self.max_results = min(max_results, 100)
        self.api_key = api_key
        self.rate_limit_delay = 1.0  # 无API Key限流更严格
        self.last_call_time = 0

    async def _rate_limit(self):
        """速率限制"""
        import time
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_call_time = time.time()

    async def _make_request(self, endpoint: str, params: Dict = None,
                            fields: List[str] = None) -> Optional[Dict]:
        """
        发送HTTP请求

        Args:
            endpoint: API端点
            params: 查询参数
            fields: 返回字段列表

        Returns:
            Dict: 响应JSON
        """
        await self._rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"

        # 构建查询参数
        query_params = {}
        if params:
            query_params.update(params)
        if fields:
            query_params['fields'] = ','.join(fields)

        if query_params:
            url += f"?{urlencode(query_params)}"

        headers = {
            'User-Agent': 'Tianwen-AGI/1.0',
            'Accept': 'application/json'
        }
        if self.api_key:
            headers['x-api-key'] = self.api_key

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))

        except urllib.error.HTTPError as e:
            logger.error(f"[SemanticScholar] HTTP Error: {e.code} - {e.reason}")
            return None
        except Exception as e:
            logger.error(f"[SemanticScholar] Request error: {e}")
            return None

    async def search(self, query: str, max_results: int = None) -> List[Paper]:
        """
        搜索论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            List[Paper]: 论文列表
        """
        max_results = max_results or self.max_results

        # 指定返回字段
        fields = [
            'paperId', 'title', 'abstract', 'year', 'citationCount',
            'authors', 'externalIds', 'url', 'openAccessPdf'
        ]

        params = {
            'query': query,
            'limit': min(max_results, 100),
            'offset': 0
        }

        result = await self._make_request('paper/search', params, fields)
        if not result or 'data' not in result:
            return []

        papers = []
        for paper_data in result['data']:
            try:
                paper = self._parse_paper(paper_data)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.error(f"[SemanticScholar] Parse paper error: {e}")
                continue

        return papers

    async def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """
        根据Semantic Scholar ID获取论文

        Args:
            paper_id: 论文ID

        Returns:
            Optional[Paper]: 论文对象
        """
        fields = [
            'paperId', 'title', 'abstract', 'year', 'citationCount',
            'authors', 'externalIds', 'url', 'openAccessPdf', 'venue'
        ]

        result = await self._make_request(f'paper/{paper_id}', fields=fields)
        if not result:
            return None

        return self._parse_paper(result)

    async def get_paper_references(self, paper_id: str, limit: int = 50) -> List[Paper]:
        """
        获取论文的参考文献

        Args:
            paper_id: 论文ID
            limit: 参考文献数量限制

        Returns:
            List[Paper]: 参考文献列表
        """
        fields = [
            'paperId', 'title', 'abstract', 'year', 'citationCount',
            'authors', 'externalIds'
        ]

        params = {
            'limit': min(limit, 100),
            'offset': 0
        }

        result = await self._make_request(
            f'paper/{paper_id}/references',
            params,
            fields
        )

        if not result or 'data' not in result:
            return []

        papers = []
        for ref_data in result['data']:
            citing_paper = ref_data.get('citedPaper', {})
            if citing_paper:
                try:
                    paper = self._parse_paper(citing_paper)
                    if paper:
                        papers.append(paper)
                except Exception:
                    continue

        return papers

    async def get_paper_citations(self, paper_id: str, limit: int = 50) -> List[Paper]:
        """
        获取论文的被引情况

        Args:
            paper_id: 论文ID
            limit: 引用数量限制

        Returns:
            List[Paper]: 引用列表
        """
        fields = [
            'paperId', 'title', 'abstract', 'year', 'citationCount',
            'authors', 'externalIds'
        ]

        params = {
            'limit': min(limit, 100),
            'offset': 0
        }

        result = await self._make_request(
            f'paper/{paper_id}/citations',
            params,
            fields
        )

        if not result or 'data' not in result:
            return []

        papers = []
        for cit_data in result['data']:
            citing_paper = cit_data.get('citingPaper', {})
            if citing_paper:
                try:
                    paper = self._parse_paper(citing_paper)
                    if paper:
                        papers.append(paper)
                except Exception:
                    continue

        return papers

    async def get_citation_network(self, paper_id: str, depth: int = 1) -> Dict[str, Any]:
        """
        获取论文的引用网络

        Args:
            paper_id: 论文ID
            depth: 网络深度

        Returns:
            Dict: 引用网络数据
        """
        network = {
            'center': paper_id,
            'references': [],
            'citations': [],
            'depth': depth
        }

        # 获取参考文献
        refs = await self.get_paper_references(paper_id, limit=20)
        network['references'] = [p.id for p in refs]

        # 获取被引情况
        cits = await self.get_paper_citations(paper_id, limit=20)
        network['citations'] = [p.id for p in cits]

        return network

    def _parse_paper(self, paper_data: Dict) -> Optional[Paper]:
        """
        解析Semantic Scholar论文数据

        Args:
            paper_data: 论文JSON

        Returns:
            Optional[Paper]: 论文对象
        """
        try:
            # 提取ID
            paper_id = paper_data.get('paperId', '')

            # 提取标题
            title = paper_data.get('title', '')

            # 提取作者
            authors = []
            for author in paper_data.get('authors', []):
                author_name = author.get('name', '')
                if author_name:
                    authors.append(author_name)

            # 提取摘要
            abstract = paper_data.get('abstract', '') or ''

            # 提取分类 (从venue获取)
            categories = []
            venue = paper_data.get('venue', '')
            if venue:
                categories.append(venue)

            # 提取日期
            year = paper_data.get('year')
            publication_date = str(year) + '-01-01' if year else ''
            updated_date = ''

            # 提取引用数
            citations = paper_data.get('citationCount', 0)

            # 提取链接
            pdf_url = ''
            oa_pdf = paper_data.get('openAccessPdf', {})
            if oa_pdf:
                pdf_url = oa_pdf.get('url', '')

            external_ids = paper_data.get('externalIds', {})
            arxiv_url = ''
            if 'ArXiv' in external_ids:
                arxiv_url = f"https://arxiv.org/abs/{external_ids['ArXiv']}"

            return Paper(
                id=f"semantic_scholar:{paper_id}",
                title=title,
                authors=authors,
                abstract=abstract,
                categories=categories,
                published_date=publication_date,
                updated_date=updated_date,
                citations=citations,
                pdf_url=pdf_url,
                arxiv_url=arxiv_url,
                source="semantic_scholar"
            )

        except Exception as e:
            logger.error(f"[SemanticScholar] Parse error: {e}")
            return None


# ============ PDF解析器 (基于pdfplumber) ============

class PDFParser:
    """
    PDF解析器 - 提取论文PDF中的文本、表格和图表数据

    使用pdfplumber库进行PDF解析，支持:
    - 全文文本提取
    - 表格检测和提取
    - 页面级图像提取 (作为参考)
    - 论文摘要自动生成

    Note:
        需要安装 pdfplumber: pip install pdfplumber
    """

    def __init__(self, cache_dir: str = None):
        """
        初始化PDF解析器

        Args:
            cache_dir: PDF缓存目录，默认为系统临时目录
        """
        self.cache_dir = cache_dir or tempfile.gettempdir()
        self.pdfplumber_available = PDFPLUMBER_AVAILABLE

    async def download_pdf(self, url: str, paper_id: str = None) -> Optional[str]:
        """
        下载PDF到本地缓存

        Args:
            url: PDF URL
            paper_id: 论文ID (用于命名文件)

        Returns:
            str: 本地PDF文件路径，失败返回None
        """
        if not url:
            return None

        paper_id = paper_id or hash(url)
        local_path = os.path.join(self.cache_dir, f"{paper_id}.pdf")

        # 已下载则跳过
        if os.path.exists(local_path):
            return local_path

        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Tianwen-AGI/1.0'}
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                pdf_data = response.read()

            with open(local_path, 'wb') as f:
                f.write(pdf_data)

            logger.info(f"[PDFParser] Downloaded: {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"[PDFParser] Download error: {e}")
            return None

    async def parse_pdf(self, pdf_path: str,
                        extract_tables: bool = True,
                        extract_images: bool = False) -> Dict[str, Any]:
        """
        解析PDF文件

        Args:
            pdf_path: PDF文件路径
            extract_tables: 是否提取表格
            extract_images: 是否提取图像信息

        Returns:
            Dict: 包含text, tables, images, page_count等
        """
        if not self.pdfplumber_available:
            return {
                "error": "pdfplumber not installed. Run: pip install pdfplumber",
                "text": "",
                "tables": [],
                "images": []
            }

        if not os.path.exists(pdf_path):
            return {"error": f"PDF not found: {pdf_path}", "text": "", "tables": [], "images": []}

        result = {
            "text": "",
            "tables": [],
            "images": [],
            "page_count": 0,
            "metadata": {}
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["page_count"] = len(pdf.pages)
                result["metadata"] = pdf.metadata or {}

                all_text = []
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取文本
                    page_text = page.extract_text() or ""
                    if page_text:
                        all_text.append(f"[Page {page_num}]\n{page_text}")

                    # 提取表格
                    if extract_tables:
                        tables = page.extract_tables()
                        for table_idx, table in enumerate(tables):
                            if table:
                                result["tables"].append({
                                    "page": page_num,
                                    "table_index": table_idx,
                                    "data": table
                                })

                    # 提取图像信息
                    if extract_images:
                        images = page.images
                        if images:
                            result["images"].append({
                                "page": page_num,
                                "count": len(images)
                            })

                result["text"] = "\n\n".join(all_text)

        except Exception as e:
            result["error"] = str(e)

        return result

    async def extract_full_text(self, pdf_url: str = None,
                                 pdf_path: str = None,
                                 paper_id: str = None) -> str:
        """
        从PDF提取完整文本

        Args:
            pdf_url: PDF URL (会下载)
            pdf_path: 本地PDF路径 (优先使用)
            paper_id: 论文ID

        Returns:
            str: 提取的文本
        """
        # 确定PDF路径
        target_path = pdf_path
        if not target_path and pdf_url:
            target_path = await self.download_pdf(pdf_url, paper_id)

        if not target_path:
            return ""

        parsed = await self.parse_pdf(target_path, extract_tables=False, extract_images=False)
        return parsed.get("text", "")

    async def extract_tables(self, pdf_url: str = None,
                             pdf_path: str = None,
                             paper_id: str = None) -> List[Dict]:
        """
        从PDF提取所有表格

        Args:
            pdf_url: PDF URL (会下载)
            pdf_path: 本地PDF路径 (优先使用)
            paper_id: 论文ID

        Returns:
            List[Dict]: 表格列表，每个包含page, table_index, data
        """
        target_path = pdf_path
        if not target_path and pdf_url:
            target_path = await self.download_pdf(pdf_url, paper_id)

        if not target_path:
            return []

        parsed = await self.parse_pdf(target_path, extract_tables=True, extract_images=False)
        return parsed.get("tables", [])

    def generate_summary_from_text(self, text: str, max_length: int = 2000) -> str:
        """
        根据提取的文本生成摘要

        通过提取前几段和最后几段来生成伪摘要，
        适合没有原始摘要的PDF论文。

        Args:
            text: PDF文本
            max_length: 最大摘要长度

        Returns:
            str: 生成的摘要
        """
        if not text:
            return ""

        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        # 取开头和结尾的段落
        n = min(3, len(paragraphs))
        intro = paragraphs[:n]
        conclusion = paragraphs[-n:] if len(paragraphs) > n * 2 else []

        # 构建摘要
        summary_parts = intro
        if conclusion and conclusion != intro:
            summary_parts.append("...")
            summary_parts.extend(conclusion)

        summary = " ".join(summary_parts)

        # 截断
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    async def get_full_content(self, paper: "Paper") -> Dict[str, Any]:
        """
        获取论文的完整PDF内容

        Args:
            paper: Paper对象

        Returns:
            Dict: 包含text, tables, summary, metadata
        """
        result = {
            "paper_id": paper.id,
            "title": paper.title,
            "text": "",
            "tables": [],
            "summary": "",
            "metadata": {},
            "pdf_url": paper.pdf_url
        }

        if not paper.pdf_url:
            # 尝试从arxiv_url构建PDF URL
            if paper.arxiv_url and "arxiv.org" in paper.arxiv_url:
                arxiv_id = paper.arxiv_url.split("/")[-1]
                result["pdf_url"] = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        if not result["pdf_url"]:
            return result

        # 提取文本
        text = await self.extract_full_text(
            pdf_url=result["pdf_url"],
            paper_id=paper.id
        )
        result["text"] = text

        # 生成摘要
        if text:
            result["summary"] = self.generate_summary_from_text(text)

        # 提取表格
        tables = await self.extract_tables(
            pdf_url=result["pdf_url"],
            paper_id=paper.id
        )
        result["tables"] = tables

        return result


class PaperPDFAnalyzer:
    """
    论文PDF分析器 - 整合PDF解析和文献调研

    提供对论文PDF的完整分析能力:
    - 下载并解析PDF
    - 提取文本和表格
    - 自动生成摘要
    - 提取关键信息 (方法、数据、结果)
    """

    def __init__(self, cache_dir: str = None):
        """
        初始化分析器

        Args:
            cache_dir: PDF缓存目录
        """
        self.parser = PDFParser(cache_dir=cache_dir)

    async def analyze_paper(self, paper: "Paper") -> Dict[str, Any]:
        """
        分析单篇论文

        Args:
            paper: Paper对象

        Returns:
            Dict: 分析结果
        """
        content = await self.parser.get_full_content(paper)

        return {
            "paper_id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "published_date": paper.published_date,
            "pdf_url": content["pdf_url"],
            "full_text": content["text"],
            "generated_summary": content["summary"],
            "tables": content["tables"],
            "table_count": len(content["tables"]),
            "page_count": content["metadata"].get("page_count", 0),
            "has_pdf": bool(content["text"])
        }

    async def analyze_papers(self, papers: List["Paper"],
                             max_papers: int = 10) -> List[Dict[str, Any]]:
        """
        批量分析论文

        Args:
            papers: 论文列表
            max_papers: 最大分析数量

        Returns:
            List[Dict]: 分析结果列表
        """
        results = []
        for paper in papers[:max_papers]:
            try:
                analysis = await self.analyze_paper(paper)
                results.append(analysis)
            except Exception as e:
                logger.error(f"[PaperPDFAnalyzer] Error analyzing {paper.id}: {e}")
                results.append({
                    "paper_id": paper.id,
                    "title": paper.title,
                    "error": str(e)
                })

        return results


# ============ 文献调研器 v2.1 ============

class LiteratureResearcher:
    """
    文献调研器 v2.1 - 支持多数据源

    增强功能:
    - 多数据源支持 (arXiv, OpenAlex, Semantic Scholar)
    - 深度主题提取 (TF-IDF风格)
    - 论文聚类分析
    - 研究假说生成
    - 与天文观测系统联动
    - ChromaDB向量存储接口 (预留RAG增强)
    - 多种导出格式
    """

    # 科学术语停用词
    COMMON_STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'this', 'that', 'these', 'those', 'i', 'we', 'you', 'he', 'she', 'it',
        'they', 'their', 'its', 'our', 'my', 'your', 'his', 'her', 'which',
        'what', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'also', 'now', 'paper', 'show',
        'propose', 'proposed', 'approach', 'method', 'using', 'based', 'use'
    }

    # 科学术语同义词映射
    SYNONYM_MAP = {
        'nn': 'neural network',
        'cnn': 'convolutional neural network',
        'rnn': 'recurrent neural network',
        'lstm': 'long short-term memory',
        'gru': 'gated recurrent unit',
        'transformer': 'transformer',
        'llm': 'large language model',
        'nlp': 'natural language processing',
        'cv': 'computer vision',
        'ml': 'machine learning',
        'dl': 'deep learning',
        'ai': 'artificial intelligence',
        'mlp': 'multilayer perceptron',
        'gan': 'generative adversarial network',
        'vae': 'variational autoencoder',
        'diffusion': 'diffusion model'
    }

    def __init__(self,
                 use_arxiv: bool = True,
                 use_openalex: bool = False,
                 use_semantic_scholar: bool = False,
                 semantic_scholar_api_key: str = None,
                 max_results_per_source: int = 30):
        """
        初始化文献调研器

        Args:
            use_arxiv: 是否使用arXiv
            use_openalex: 是否使用OpenAlex
            use_semantic_scholar: 是否使用Semantic Scholar
            semantic_scholar_api_key: Semantic Scholar API Key
            max_results_per_source: 每个数据源的最大结果数
        """
        self.use_arxiv = use_arxiv
        self.use_openalex = use_openalex
        self.use_semantic_scholar = use_semantic_scholar
        self.max_results_per_source = max_results_per_source

        # 初始化各数据源客户端
        self.arxiv = ArxivAPI() if use_arxiv else None
        self.openalex = OpenAlexClient() if use_openalex else None
        self.semantic_scholar = SemanticScholarClient(
            api_key=semantic_scholar_api_key
        ) if use_semantic_scholar else None

        self._cache: Dict[str, Any] = {}

    @property
    def sources_used(self) -> List[str]:
        """获取使用的数据源列表"""
        sources = []
        if self.use_arxiv:
            sources.append('arxiv')
        if self.use_openalex:
            sources.append('openalex')
        if self.use_semantic_scholar:
            sources.append('semantic_scholar')
        return sources

    async def search_arxiv(self, query: str, max_results: int = None) -> List[Paper]:
        """
        搜索arXiv论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            List[Paper]: 论文列表
        """
        if not self.arxiv:
            return []

        max_results = max_results or self.max_results_per_source
        return await self.arxiv.search(query, max_results)

    async def search_openalex(self, query: str, max_results: int = None) -> List[Paper]:
        """
        搜索OpenAlex论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            List[Paper]: 论文列表
        """
        if not self.openalex:
            return []

        max_results = max_results or self.max_results_per_source
        return await self.openalex.search(query, max_results)

    async def search_semantic_scholar(self, query: str, max_results: int = None) -> List[Paper]:
        """
        搜索Semantic Scholar论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            List[Paper]: 论文列表
        """
        if not self.semantic_scholar:
            return []

        max_results = max_results or self.max_results_per_source
        return await self.semantic_scholar.search(query, max_results)

    async def search_all(self, query: str, max_results: int = None) -> List[Paper]:
        """
        从所有启用的数据源搜索论文

        Args:
            query: 搜索关键词
            max_results: 每个数据源的最大结果数

        Returns:
            List[Paper]: 所有数据源的论文列表
        """
        max_results = max_results or self.max_results_per_source
        all_papers = []
        tasks = []

        if self.use_arxiv:
            tasks.append(self.search_arxiv(query, max_results))
        if self.use_openalex:
            tasks.append(self.search_openalex(query, max_results))
        if self.use_semantic_scholar:
            tasks.append(self.search_semantic_scholar(query, max_results))

        if not tasks:
            logger.info("[LiteratureResearcher] No data sources enabled")
            return []

        # 并行执行所有搜索任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[LiteratureResearcher] Search error: {result}")
                continue
            if isinstance(result, list):
                all_papers.extend(result)

        # 去重 (基于论文ID)
        unique_papers = self._deduplicate_papers(all_papers)

        logger.info(f"[LiteratureResearcher] Found {len(all_papers)} papers, {len(unique_papers)} unique")
        return unique_papers

    def _deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """
        基于DOI和arXiv ID去重论文

        Args:
            papers: 论文列表

        Returns:
            List[Paper]: 去重后的论文列表
        """
        seen_ids = set()
        seen_dois = set()
        unique_papers = []

        for paper in papers:
            # 优先使用arxiv ID去重
            if 'arxiv:' in paper.id:
                arxiv_id = paper.id.replace('arxiv:', '')
                if arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)

            # 使用DOI去重
            # 从arxiv_url提取DOI (如果有)
            doi = None
            if 'doi.org' in paper.arxiv_url:
                doi = paper.arxiv_url.split('doi.org/')[-1]
            elif paper.pdf_url and 'doi.org' in paper.pdf_url:
                doi = paper.pdf_url.split('doi.org/')[-1]

            if doi:
                if doi in seen_dois:
                    continue
                seen_dois.add(doi)

            unique_papers.append(paper)

        return unique_papers

    async def research(self, topic: str, max_papers: int = 30) -> ResearchState:
        """
        执行完整文献调研

        Args:
            topic: 研究主题/关键词
            max_papers: 最大搜索论文数 (总数量，多源时会分配)

        Returns:
            ResearchState: 研究现状分析结果
        """
        logger.info(f"\n🔍 开始文献调研: {topic}")
        logger.info(f"   使用数据源: {', '.join(self.sources_used) if self.sources_used else '无'}")

        # 1. 搜索论文 (多数据源)
        papers = await self.search_all(topic, max_results=max_papers)
        logger.info(f"   找到 {len(papers)} 篇相关论文 (去重后)")

        if not papers:
            return ResearchState(
                query=topic, total_results=0, papers=[],
                key_themes=[], research_gaps=[],
                timeline={}, top_authors=[], sources_used=self.sources_used
            )

        # 2. 深度主题提取
        themes = self._extract_themes_advanced(papers)
        logger.info(f"   识别 {len(themes)} 个关键主题")

        # 3. 论文聚类
        clusters = self._cluster_papers(papers)
        logger.info(f"   发现 {len(clusters)} 个研究子领域")

        # 4. 分析研究空白
        gaps = self._analyze_gaps_advanced(papers, themes)
        logger.info(f"   发现 {len(gaps)} 个研究空白")

        # 5. 统计时间线
        timeline = self._analyze_timeline(papers)
        logger.info(f"   时间跨度: {min(timeline.keys()) if timeline else 'N/A'} - {max(timeline.keys()) if timeline else 'N/A'}")

        # 6. 识别高产作者
        top_authors = self._find_top_authors(papers)
        logger.info(f"   高产作者: {[a[0] for a in top_authors[:3]]}")

        # 7. 判断趋势
        trend = self._analyze_trend(timeline)
        logger.info(f"   研究趋势: {trend}")

        # 8. 生成摘要
        summary = self._generate_summary_advanced(topic, papers, themes, gaps, trend)

        return ResearchState(
            query=topic,
            total_results=len(papers),
            papers=papers,
            key_themes=themes,
            research_gaps=gaps,
            timeline=timeline,
            top_authors=top_authors,
            paper_clusters=clusters,
            trend_direction=trend,
            summary=summary,
            sources_used=self.sources_used
        )

    def _extract_themes_advanced(self, papers: List[Paper], top_n: int = 15) -> List[str]:
        """高级主题提取 - 结合词频和文档频率"""
        word_doc_freq: Dict[str, int] = {}  # 词在多少篇论文中出现
        word_total_freq: Dict[str, int] = {}  # 词的总出现次数

        # 论文重要词汇权重
        _ = 3.0
        _ = 1.0

        for paper in papers:
            text_lower = (paper.title + ' ' + paper.abstract).lower()
            words = re.findall(r'[a-z]{4,}', text_lower)

            # 统计文档频率
            words_in_paper = set()
            for word in words:
                if word not in self.COMMON_STOPWORDS and word not in ['http', 'arxiv', 'https', 'openalex', 'semantic']:
                    words_in_paper.add(word)
                    word_total_freq[word] = word_total_freq.get(word, 0) + 1

            for word in words_in_paper:
                word_doc_freq[word] = word_doc_freq.get(word, 0) + 1

        # 计算 TF-IDF 风格评分
        n_docs = len(papers)
        theme_scores: Dict[str, float] = {}

        for word in word_doc_freq:
            tf = word_total_freq.get(word, 0)
            idf = math.log(n_docs / (word_doc_freq[word] + 1))
            # 综合评分
            theme_scores[word] = tf * idf * 0.1 + word_doc_freq[word] * 0.5

        # 排序并去重相似词
        sorted_words = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)

        # 合并同义词
        themes = []
        seen_concepts: Set[str] = set()

        for word, score in sorted_words:
            # 检查是否与已有主题概念重复
            is_duplicate = False
            for seen in seen_concepts:
                if word in seen or seen in word:
                    if len(word) > 4 and len(seen) > 4:
                        is_duplicate = True
                        break

            if not is_duplicate and score > 1.0:
                themes.append(word)
                seen_concepts.add(word)
                if len(themes) >= top_n:
                    break

        return themes

    def _cluster_papers(self, papers: List[Paper]) -> List[List[int]]:
        """简单论文聚类 - 基于分类和主题相似性"""
        if len(papers) < 3:
            return [[i] for i in range(len(papers))]

        clusters: List[List[int]] = []
        assigned: Set[int] = set()

        # 按主分类聚类
        cat_groups: Dict[str, List[int]] = {}
        for i, paper in enumerate(papers):
            if paper.categories:
                cat = paper.categories[0]
                if cat not in cat_groups:
                    cat_groups[cat] = []
                cat_groups[cat].append(i)

        for cat, indices in cat_groups.items():
            if len(indices) >= 2:
                clusters.append(indices)
                assigned.update(indices)

        # 未分类的论文按时间聚类
        unassigned = [i for i in range(len(papers)) if i not in assigned]
        if unassigned:
            clusters.append(unassigned)

        return clusters if clusters else [[i] for i in range(len(papers))]

    def _analyze_gaps_advanced(self, papers: List[Paper],
                                themes: List[str]) -> List[ResearchGap]:
        """高级Gap分析"""
        gaps = []
        gap_id = 1

        # 分析论文特征
        titles_lower = [p.title.lower() for p in papers]
        abstracts_lower = [p.abstract.lower() for p in papers]
        _ = ' '.join(titles_lower + abstracts_lower)

        # 1. 方法学Gap - 多样性分析
        method_variations = self._count_method_variations(papers)
        if method_variations < 3:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="methodology",
                description=f"方法多样性不足，仅发现{method_variations}种主要方法范式",
                evidence=["主流方法重复性较高，缺乏方法创新"],
                opportunity="探索新型方法架构或多方法融合",
                priority="high",
                supporting_papers=[p.id for p in papers[:3]]
            ))
            gap_id += 1

        # 2. 评估标准Gap
        has_benchmark = any('benchmark' in t or 'dataset' in t or 'evaluation' in t
                           for t in titles_lower[:5])
        if not has_benchmark:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="evaluation",
                description="缺乏统一的评估基准和标准数据集",
                evidence=["论文使用不同的评估标准", "结果难以直接比较"],
                opportunity="建立公开基准数据集和统一评估协议",
                priority="high",
                supporting_papers=[p.id for p in papers[:2]]
            ))
            gap_id += 1

        # 3. 可解释性Gap
        explainability_mentions = sum(
            1 for t in abstracts_lower
            if any(kw in t for kw in ['interpret', 'explain', 'understand', 'visualiz'])
        )
        if explainability_mentions < len(papers) * 0.2:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="theory",
                description="模型可解释性研究不足，占比不足20%",
                evidence=[f"仅{explainability_mentions}篇涉及可解释性"],
                opportunity="增加模型可解释性分析，提高透明度",
                priority="medium",
                supporting_papers=[p.id for p in papers[:2] if 'interpret' in p.abstract.lower()]
            ))
            gap_id += 1

        # 4. 应用领域Gap
        categories_used = set()
        for p in papers:
            categories_used.update(p.categories)

        if len(categories_used) < 5:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="application",
                description=f"应用领域较集中，仅涉及{len(categories_used)}个领域",
                evidence=[f"涉及分类: {', '.join(list(categories_used)[:5])}"],
                opportunity="拓展到新的应用领域",
                priority="medium",
                supporting_papers=[p.id for p in papers[:2]]
            ))
            gap_id += 1

        # 5. 时间趋势Gap - 识别放缓的领域
        # 如果近期论文减少，说明可能已成熟或冷却

        return gaps

    def _count_method_variations(self, papers: List[Paper]) -> int:
        """统计方法变种数量"""
        method_patterns = [
            (r'neural network|deep learning|cnn|rnn|lstm|transformer', '深度学习'),
            (r'svm|support vector', 'SVM'),
            (r'random forest|decision tree|xgboost', '树模型'),
            (r'linear regression|logistic', '线性模型'),
            (r'gaussian process|kernel', '核方法'),
            (r'evolutionary|genetic algorithm', '进化算法'),
            (r'bayesian|probabilistic', '贝叶斯方法'),
            (r'attention|transformer|bert|gpt', '注意力机制'),
        ]

        found_methods = set()
        for paper in papers[:10]:
            text = (paper.title + ' ' + paper.abstract).lower()
            for pattern, name in method_patterns:
                if re.search(pattern, text):
                    found_methods.add(name)

        return len(found_methods)

    def _analyze_timeline(self, papers: List[Paper]) -> Dict[str, int]:
        """分析论文发表时间线"""
        timeline: Dict[str, int] = {}

        for paper in papers:
            try:
                year = paper.published_date[:4]
                if year.isdigit():
                    timeline[year] = timeline.get(year, 0) + 1
            except Exception:
                continue

        return dict(sorted(timeline.items()))

    def _analyze_trend(self, timeline: Dict[str, int]) -> str:
        """分析研究趋势"""
        if len(timeline) < 2:
            return "stable"

        years = sorted(timeline.keys())
        recent_years = years[-3:] if len(years) >= 3 else years
        older_years = years[:-3] if len(years) >= 4 else years[:-1]

        if not older_years:
            return "stable"

        recent_avg = sum(timeline.get(y, 0) for y in recent_years) / len(recent_years)
        older_avg = sum(timeline.get(y, 0) for y in older_years) / len(older_years)

        if recent_avg > older_avg * 1.3:
            return "rising"
        elif recent_avg < older_avg * 0.7:
            return "declining"
        else:
            return "stable"

    def _find_top_authors(self, papers: List[Paper], top_n: int = 5) -> List[Tuple[str, int]]:
        """识别高产作者"""
        author_counts: Dict[str, int] = {}

        for paper in papers:
            for author in paper.authors[:3]:
                author_counts[author] = author_counts.get(author, 0) + 1

        sorted_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_authors[:top_n]

    def _generate_summary_advanced(self, topic: str, papers: List[Paper],
                                   themes: List[str], gaps: List[ResearchGap],
                                   trend: str) -> str:
        """生成高级研究摘要"""
        # 统计各数据源论文数
        source_counts: Dict[str, int] = {}
        for paper in papers:
            source_counts[paper.source] = source_counts.get(paper.source, 0) + 1

        return f"""# {topic} 研究现状

## 概述
- 论文总数: {len(papers)}
- 数据来源分布: {', '.join([f'{s}:{c}篇' for s,c in source_counts.items()])}
- 关键主题: {', '.join(themes[:8])}
- 研究趋势: {trend}
- 研究空白: {len(gaps)}个 (高优先级: {sum(1 for g in gaps if g.priority == 'high')}个)

## 时间分布
{self._format_timeline(self._analyze_timeline(papers))}

## 主要 Gap
{chr(10).join(f'- [{g.priority.upper()}] {g.category}: {g.description}' for g in gaps[:3])}
"""

    def _format_timeline(self, timeline: Dict[str, int]) -> str:
        if not timeline:
            return "数据不足"
        lines = []
        max_count = max(timeline.values()) if timeline else 1
        for year, count in sorted(timeline.items()):
            bar_len = max(1, int(count / max_count * 20))
            bar = "█" * bar_len
            lines.append(f"{year}: {bar} ({count}篇)")
        return "\n".join(lines)

    # ============ 研究假说生成 ============

    async def generate_hypotheses(self, state: ResearchState) -> List[ResearchHypothesis]:
        """基于研究Gap生成可验证假说"""
        hypotheses = []
        hyp_id = 1

        for gap in state.research_gaps:
            if gap.priority != "high":
                continue

            # 根据Gap类型生成不同假说
            if gap.category == "methodology":
                hypotheses.append(ResearchHypothesis(
                    id=f"hyp-{hyp_id}",
                    hypothesis=f"如果引入多模态融合方法，那么在{gap.description.split('，')[0]}任务上可提升性能",
                    based_on="方法多样性不足，该方向有创新空间",
                    evidence=[f"Gap: {gap.description}", "相关论文方法单一"],
                    testable=True,
                    related_gap=gap.id,
                    suggested_method="设计对比实验，与现有方法在标准基准上比较"
                ))
                hyp_id += 1

            elif gap.category == "evaluation":
                hypotheses.append(ResearchHypothesis(
                    id=f"hyp-{hyp_id}",
                    hypothesis="如果建立统一评估基准，那么可以更客观地比较不同方法的优劣",
                    based_on="缺乏评估标准，研究结果难以复现和比较",
                    evidence=[f"Gap: {gap.description}"],
                    testable=True,
                    related_gap=gap.id,
                    suggested_method="收集公开数据集，制定评估协议，邀请多团队验证"
                ))
                hyp_id += 1

            elif gap.category == "application":
                hypotheses.append(ResearchHypothesis(
                    id=f"hyp-{hyp_id}",
                    hypothesis=f"如果将现有方法应用于{gap.opportunity.split('，')[0]}，可能取得突破",
                    based_on=f"应用领域: {gap.description}",
                    evidence=[f"Gap: {gap.description}", f"机会: {gap.opportunity}"],
                    testable=True,
                    related_gap=gap.id,
                    suggested_method="跨领域实验验证"
                ))
                hyp_id += 1

        return hypotheses

    # ============ 与天文观测系统联动 ============

    def link_to_observatory(self, state: ResearchState) -> ObservatoryLink:
        """将文献调研结果与天文观测系统关联"""
        link = ObservatoryLink()

        # 从主题和Gap中提取观测目标
        for theme in state.key_themes:
            # 天文相关主题词映射
            astronomy_keywords = {
                'galaxy': ['M31', 'M51', 'M81'],
                'star': ['天狼星', '织女星', '大角星'],
                'planet': ['火星', '木星', '土星'],
                'nebula': ['猎户座大星云', '蟹状星云'],
                'supernova': ['SN 1987A'],
                'exoplanet': ['系外行星'],
                'blackhole': ['人马座A*'],
            }

            for kw, targets in astronomy_keywords.items():
                if kw in theme.lower():
                    link.relevant_targets.extend(targets)

        # 识别需要的数据类型
        for gap in state.research_gaps:
            if gap.category == "dataset":
                link.data_requirements.append("多波段观测数据")
            elif gap.category == "application":
                link.data_requirements.append("目标天体的光谱数据")

        # 去重
        link.relevant_targets = list(set(link.relevant_targets))

        return link

    # ============ 完整文献综述生成 ============

    async def generate_review(self, topic: str, max_papers: int = 50) -> LiteratureReview:
        """生成完整文献综述"""
        research_state = await self.research(topic, max_papers)

        if not research_state.papers:
            return LiteratureReview(
                title=f"{topic} 文献综述",
                query=topic,
                date=datetime.now().strftime('%Y-%m-%d')
            )

        # 生成假说
        hypotheses = await self.generate_hypotheses(research_state)

        # 构建综述结构
        sections = {
            "abstract": self._generate_abstract(research_state),
            "introduction": self._generate_introduction(research_state),
            "related_work": self._generate_related_work(research_state),
            "method_analysis": self._generate_method_analysis(research_state),
            "research_gaps": self._generate_gaps_section(research_state.research_gaps),
            "hypotheses": self._generate_hypotheses_section(hypotheses),
            "future_directions": self._generate_future_directions(research_state.research_gaps, hypotheses),
            "conclusion": self._generate_conclusion(research_state, hypotheses)
        }

        # 构建参考文献
        references = []
        for i, paper in enumerate(research_state.papers[:30], 1):
            # 获取作者字符串
            if len(paper.authors) > 3:
                authors_str = ", ".join(paper.authors[:3]) + " et al."
            else:
                authors_str = ", ".join(paper.authors)

            references.append({
                "id": i,
                "title": paper.title,
                "authors": authors_str,
                "venue": paper.source.upper(),
                "year": paper.published_date[:4] if paper.published_date else "N/A",
                "url": paper.arxiv_url or paper.pdf_url,
                "categories": paper.categories[:2],
                "citations": paper.citations
            })

        # 观测站联动
        _ = self.link_to_observatory(research_state)

        return LiteratureReview(
            title=f"{topic} 文献综述",
            query=topic,
            date=datetime.now().strftime('%Y-%m-%d'),
            sections=sections,
            references=references,
            gaps=research_state.research_gaps,
            hypotheses=hypotheses,
            future_directions=[g.opportunity for g in research_state.research_gaps]
        )

    def _generate_abstract(self, state: ResearchState) -> str:
        # 统计各数据源论文数
        source_counts: Dict[str, int] = {}
        for paper in state.papers:
            source_counts[paper.source] = source_counts.get(paper.source, 0) + 1

        return f"""## 摘要

本综述系统调研了"{state.query}"领域的研究现状。通过分析{state.total_results}篇论文（来源：{', '.join([f'{s}:{c}篇' for s,c in source_counts.items()])}），我们发现：

1. **研究趋势**: 该领域呈{state.trend_direction}趋势
2. **关键主题**: {', '.join(state.key_themes[:5])}
3. **主要Gap**: 识别出{len(state.research_gaps)}个研究空白，其中{sum(1 for g in state.research_gaps if g.priority == 'high')}个高优先级

本综述为该领域研究者提供了全面的文献地图和研究机会分析。
"""

    def _generate_introduction(self, state: ResearchState) -> str:
        return f"""
## 引言

### 背景
{state.query}是当前研究的重要方向，在理论和应用层面都有重要价值。

### 数据来源
- 使用数据源: {', '.join(state.sources_used) if state.sources_used else '无'}

### 研究统计
- **论文总数**: {state.total_results}
- **时间跨度**: {min(state.timeline.keys()) if state.timeline else 'N/A'} - {max(state.timeline.keys()) if state.timeline else 'N/A'}
- **关键主题**: {', '.join(state.key_themes[:8])}
- **高产作者**: {', '.join([f"{a[0]}({a[1]}篇)" for a in state.top_authors[:3]])}

### 研究趋势
{self._format_timeline(state.timeline)}

该领域目前呈**{state.trend_direction}**趋势。
"""

    def _generate_related_work(self, state: ResearchState) -> str:
        papers_text = []
        for i, paper in enumerate(state.papers[:5], 1):
            papers_text.append(f"""### [{i}] {paper.title}

- **作者**: {', '.join(paper.authors[:3])}{' et al.' if len(paper.authors) > 3 else ''}
- **来源**: {paper.source.upper()}
- **分类**: {', '.join(paper.categories[:2])}
- **发表**: {paper.published_date[:10]}
- **摘要**: {paper.abstract[:300]}...
""")

        return "## 相关工作\n\n" + "\n\n".join(papers_text)

    def _generate_method_analysis(self, state: ResearchState) -> str:
        method_count = self._count_method_variations(state.papers)

        return f"""
## 方法分析

### 主要方法范式
本领域主要涉及以下方法类型（共{method_count}种）：

{chr(10).join(f'- {name}' for _, name in [
    (r'深度学习', '深度神经网络方法'),
    (r'SVM', '支持向量机方法'),
    (r'树模型', '集成学习树模型'),
    (r'贝叶斯', '概率贝叶斯方法'),
    (r'注意力', '注意力机制方法'),
] if any(re.search(p, ' '.join(p.title for p in state.papers[:10]).lower()) for p in [r'neural', r'svm', r'forest', r'bayes', r'attention']))}

### 论文聚类
发现{len(state.paper_clusters)}个研究子领域/方向。

### 时间分布
{self._format_timeline(state.timeline)}
"""

    def _generate_gaps_section(self, gaps: List[ResearchGap]) -> str:
        if not gaps:
            return "## 研究空白\n\n暂未识别出明显的研究空白。"

        gaps_text = []
        for gap in gaps:
            priority_emoji = "🔴" if gap.priority == "high" else "🟡" if gap.priority == "medium" else "🟢"
            gaps_text.append(f"""
### {priority_emoji} {gap.id}. {gap.category.upper()} Gap [{gap.priority.upper()}]

**描述**: {gap.description}

**证据**:
{chr(10).join(f'- {e}' for e in gap.evidence)}

**研究机会**: {gap.opportunity}
""")

        return "## 研究空白\n\n" + "\n\n".join(gaps_text)

    def _generate_hypotheses_section(self, hypotheses: List[ResearchHypothesis]) -> str:
        if not hypotheses:
            return "## 研究假说\n\n暂无高优先级假说生成。"

        hyp_text = []
        for hyp in hypotheses:
            hyp_text.append(f"""
### {hyp.id}. {hyp.hypothesis}

- **基于**: {hyp.based_on}
- **证据**: {', '.join(hyp.evidence[:2])}
- **可验证性**: {'✅ 是' if hyp.testable else '❌ 否'}
- **验证方法**: {hyp.suggested_method}
- **关联Gap**: {hyp.related_gap}
""")

        return "## 研究假说\n\n" + "\n\n".join(hyp_text)

    def _generate_future_directions(self, gaps: List[ResearchGap],
                                     hypotheses: List[ResearchHypothesis]) -> str:
        directions = []

        for gap in gaps:
            directions.append(f"- **{gap.category}**: {gap.opportunity}")

        for hyp in hypotheses:
            directions.append(f"- **假说验证**: {hyp.hypothesis}")

        return "## 未来方向\n\n" + "\n\n".join(directions)

    def _generate_conclusion(self, state: ResearchState,
                             hypotheses: List[ResearchHypothesis]) -> str:
        return f"""
## 结论

本综述对**{state.query}**领域进行了系统调研。主要发现：

### 核心结论
1. 该领域共有**{state.total_results}**篇相关论文（来源：{', '.join(state.sources_used)}）
2. 关键主题包括: {', '.join(state.key_themes[:5])}
3. 识别出**{len(state.research_gaps)}**个研究空白，其中高优先级**{sum(1 for g in state.research_gaps if g.priority == 'high')}**个
4. 生成了**{len(hypotheses)}**个研究假说

### 建议
1. 优先关注高优先级的Gap
2. 对生成的研究假说进行验证
3. 关注研究趋势，顺应发展方向
4. 借鉴高产作者的研究思路

---
*综述生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*天问-AGI 文献调研模块 v2.1*
"""

    # ============ 导出功能 ============

    def export_to_markdown(self, review: LiteratureReview) -> str:
        """导出为Markdown格式"""
        lines = [
            f"# {review.title}",
            f"\n**日期**: {review.date}",
            f"**查询**: {review.query}",
            "",
            "---",
        ]

        for section_name, content in review.sections.items():
            lines.append(content)
            lines.append("")

        lines.extend([
            "---",
            "## 参考文献",
            ""
        ])

        for ref in review.references:
            lines.append(f"[{ref['id']}] {ref['authors']}. \"{ref['title']}\". {ref['venue']}, {ref['year']}.")

        return "\n".join(lines)

    def export_to_json(self, review: LiteratureReview) -> str:
        """导出为JSON格式"""
        data = {
            "title": review.title,
            "query": review.query,
            "date": review.date,
            "sections": review.sections,
            "references": review.references,
            "gaps": [
                {
                    "id": g.id,
                    "category": g.category,
                    "description": g.description,
                    "priority": g.priority,
                    "opportunity": g.opportunity
                }
                for g in review.gaps
            ],
            "hypotheses": [
                {
                    "id": h.id,
                    "hypothesis": h.hypothesis,
                    "testable": h.testable,
                    "suggested_method": h.suggested_method
                }
                for h in review.hypotheses
            ]
        }

        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_papers_to_csv(self, papers: List[Paper]) -> str:
        """导出论文列表为CSV格式"""
        lines = ["ID,Title,Authors,Categories,Published,Citations,Source,URL"]

        for p in papers:
            authors = "|".join(p.authors[:3])
            cats = "|".join(p.categories)
            lines.append(f'"{p.id}","{p.title[:50]}...","{authors}","{cats}","{p.published_date[:10]}",{p.citations},{p.source},"{p.arxiv_url}"')

        return "\n".join(lines)

# ============ 便捷函数 ============

async def quick_research(topic: str,
                        use_openalex: bool = False,
                        use_semantic_scholar: bool = False) -> ResearchState:
    """
    快速文献调研

    Args:
        topic: 研究主题
        use_openalex: 是否使用OpenAlex
        use_semantic_scholar: 是否使用Semantic Scholar

    Returns:
        ResearchState: 研究状态
    """
    researcher = LiteratureResearcher(
        use_arxiv=True,
        use_openalex=use_openalex,
        use_semantic_scholar=use_semantic_scholar
    )
    return await researcher.research(topic)

async def generate_review(topic: str,
                        use_openalex: bool = False,
                        use_semantic_scholar: bool = False) -> LiteratureReview:
    """
    生成完整综述

    Args:
        topic: 研究主题
        use_openalex: 是否使用OpenAlex
        use_semantic_scholar: 是否使用Semantic Scholar

    Returns:
        LiteratureReview: 文献综述
    """
    researcher = LiteratureResearcher(
        use_arxiv=True,
        use_openalex=use_openalex,
        use_semantic_scholar=use_semantic_scholar
    )
    return await researcher.generate_review(topic)

async def research_and_export(topic: str, format: str = "markdown",
                              use_openalex: bool = False,
                              use_semantic_scholar: bool = False) -> str:
    """调研并导出"""
    researcher = LiteratureResearcher(
        use_arxiv=True,
        use_openalex=use_openalex,
        use_semantic_scholar=use_semantic_scholar
    )
    review = await researcher.generate_review(topic)

    if format == "json":
        return researcher.export_to_json(review)
    else:
        return researcher.export_to_markdown(review)

# ============ 示例用法 ============

async def demo():
    logger.debug("=" * 70)
    logger.info("天问-AGI 文献调研模块 v2.1 演示 - 多数据源支持")
    logger.debug("=" * 70)

    # 1. 仅使用arXiv (默认)
    logger.info("\n[模式1] 仅使用arXiv")
    researcher = LiteratureResearcher(use_arxiv=True, use_openalex=False, use_semantic_scholar=False)

    logger.info("\n🔍 调研: machine learning astronomy")
    state = await researcher.research("machine learning astronomy", max_papers=20)

    logger.info("\n📊 调研结果:")
    logger.info(f"   论文数: {state.total_results}")
    logger.info(f"   关键主题: {', '.join(state.key_themes[:8])}")
    logger.info(f"   研究空白: {len(state.research_gaps)} (高优先级: {sum(1 for g in state.research_gaps if g.priority == 'high')})")
    logger.info(f"   研究趋势: {state.trend_direction}")
    logger.info(f"   数据源: {', '.join(state.sources_used)}")

    # 2. 多数据源调研
    logger.debug("=" * 70)
    logger.info("\n[模式2] 多数据源调研 (arXiv + OpenAlex)")
    researcher_multi = LiteratureResearcher(
        use_arxiv=True,
        use_openalex=True,
        use_semantic_scholar=False
    )

    logger.info("\n🔍 调研: deep learning galaxy classification")
    state_multi = await researcher_multi.research("deep learning galaxy classification", max_papers=30)

    logger.info("\n📊 多数据源调研结果:")
    logger.info(f"   论文数: {state_multi.total_results}")
    logger.info(f"   数据源: {', '.join(state_multi.sources_used)}")

    # 3. 生成假说
    logger.info("\n\n💡 生成研究假说...")
    hypotheses = await researcher.generate_hypotheses(state)
    logger.info(f"   生成 {len(hypotheses)} 个研究假说")
    for h in hypotheses[:2]:
        logger.info(f"   - {h.hypothesis[:60]}...")

    # 4. 观测站联动
    logger.info("\n\n🔭 观测站联动...")
    obs_link = researcher.link_to_observatory(state)
    if obs_link.relevant_targets:
        logger.info(f"   关联目标: {', '.join(obs_link.relevant_targets)}")
    if obs_link.data_requirements:
        logger.info(f"   数据需求: {', '.join(obs_link.data_requirements)}")

    # 5. 完整综述
    logger.info("\n\n📝 生成完整文献综述...")
    review = await researcher.generate_review("deep learning galaxy classification", max_papers=30)

    logger.info(f"\n{'='*70}")
    logger.info(f"综述标题: {review.title}")
    logger.info(f"参考文献: {len(review.references)} 篇")
    logger.info(f"研究假说: {len(review.hypotheses)} 个")

    # 6. 导出示例
    logger.info("\n\n📤 导出格式示例:")
    md = researcher.export_to_markdown(review)
    logger.info(f"   Markdown: {len(md)} 字符")

    js = researcher.export_to_json(review)
    logger.info(f"   JSON: {len(js)} 字符")

if __name__ == "__main__":
    asyncio.run(demo())
