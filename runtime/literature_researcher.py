"""
天问-AGI 文献调研模块
LiteratureResearcher - arXiv论文搜索、研究现状分析、Gap识别
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlencode
import urllib.request
import urllib.error

# ============ 数据模型 ============

@dataclass
class Paper:
    """论文对象"""
    id: str              # arXiv ID
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published_date: str
    updated_date: str
    citations: int = 0
    pdf_url: str = ""
    arxiv_url: str = ""
    relevance_score: float = 0.0

@dataclass
class Research Gap:
    """研究空白/Gap"""
    id: str
    category: str           # methodology, application, dataset, evaluation
    description: str
    evidence: List[str]     # 支持证据(相关论文)
    opportunity: str        # 研究机会
    priority: str           # high, medium, low

@dataclass
class ResearchState:
    """研究现状分析结果"""
    query: str
    total_results: int
    papers: List[Paper]
    key_themes: List[str]
    research_gaps: List[ResearchGap]
    timeline: Dict[str, int]  # 按年统计论文数量
    top_authors: List[Tuple[str, int]]  # (author, paper_count)
    summary: str = ""

@dataclass
class LiteratureReview:
    """文献综述"""
    title: str
    query: str
    date: str
    sections: Dict[str, str] = field(default_factory=dict)
    references: List[Dict] = field(default_factory=list)
    gaps: List[ResearchGap] = field(default_factory=list)
    future_directions: List[str] = field(default_factory=list)

# ============ arXiv API 客户端 ============

class ArxivAPI:
    """arXiv API 客户端"""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, max_results: int = 50):
        self.max_results = max_results
        self.rate_limit_delay = 3.0  # arXiv建议3秒间隔
        self.last_call_time = 0

    async def _rate_limit(self):
        """速率限制"""
        import time
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_call_time = time.time()

    async def search(self, query: str, max_results: int = None) -> List[Paper]:
        """搜索论文"""
        max_results = max_results or self.max_results

        await self._rate_limit()

        params = {
            'search_query': query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }

        url = f"{self.BASE_URL}?{urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Tianwen-AGI/1.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                xml_content = response.read().decode('utf-8')

            return self._parse_xml(xml_content)

        except urllib.error.HTTPError as e:
            print(f"[ArXiv] HTTP Error: {e.code} - {e.reason}")
            return []
        except Exception as e:
            print(f"[ArXiv] Search error: {e}")
            return []

    async def get_paper_by_id(self, arxiv_id: str) -> Optional[Paper]:
        """根据ID获取单篇论文"""
        await self._rate_limit()

        # 移除arXiv前缀
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
            print(f"[ArXiv] Get paper error: {e}")
            return None

    def _parse_xml(self, xml_content: str) -> List[Paper]:
        """解析arXiv XML响应"""
        papers = []

        # 提取entry块
        entries = re.findall(r'<entry>(.*?)</entry>', xml_content, re.DOTALL)

        for entry in entries:
            try:
                # 提取基本信息
                title = self._extract_tag(entry, 'title')
                abstract = self._extract_tag(entry, 'summary')
                published = self._extract_tag(entry, 'published')
                updated = self._extract_tag(entry, 'updated')
                arxiv_id = self._extract_tag(entry, 'id')

                # 提取作者
                authors = re.findall(r'<name>(.*?)</name>', entry)

                # 提取分类
                categories = re.findall(r'<category term="([^"]+)"', entry)

                # 提取链接
                pdf_url = ""
                for link in re.findall(r'<link[^>]+>', entry):
                    if 'title="pdf"' in link or 'type="application/pdf"' in link:
                        pdf_url = re.search(r'href="([^"]+)"', link)
                        if pdf_url:
                            pdf_url = pdf_url.group(1)
                            break

                if not pdf_url:
                    pdf_match = re.search(r'href="([^"]+pdf[^"]+)"', entry)
                    if pdf_match:
                        pdf_url = pdf_match.group(1)

                papers.append(Paper(
                    id=arxiv_id.split('/')[-1] if '/' in arxiv_id else arxiv_id,
                    title=self._clean_text(title),
                    authors=authors,
                    abstract=self._clean_text(abstract),
                    categories=categories,
                    published_date=published,
                    updated_date=updated,
                    pdf_url=pdf_url,
                    arxiv_url=arxiv_id
                ))

            except Exception as e:
                print(f"[ArXiv] Parse entry error: {e}")
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

# ============ 文献调研器 ============

class LiteratureResearcher:
    """
    文献调研器

    功能:
    - 搜索arXiv论文
    - 分析研究现状
    - 识别研究空白(Gap)
    - 生成文献综述
    """

    def __init__(self):
        self.arxiv = ArxivAPI()
        self._cache: Dict[str, Any] = {}

    async def research(self, topic: str, max_papers: int = 30) -> ResearchState:
        """
        执行完整文献调研

        Args:
            topic: 研究主题/关键词
            max_papers: 最大搜索论文数

        Returns:
            ResearchState: 研究现状分析结果
        """
        print(f"\n🔍 开始文献调研: {topic}")

        # 1. 搜索论文
        papers = await self.arxiv.search(topic, max_results=max_papers)
        print(f"   找到 {len(papers)} 篇相关论文")

        # 2. 提取关键主题
        themes = self._extract_themes(papers)
        print(f"   识别 {len(themes)} 个关键主题")

        # 3. 分析研究空白
        gaps = self._analyze_gaps(papers, themes)
        print(f"   发现 {len(gaps)} 个研究空白")

        # 4. 统计时间线
        timeline = self._analyze_timeline(papers)
        print(f"   时间跨度: {min(timeline.keys()) if timeline else 'N/A'} - {max(timeline.keys()) if timeline else 'N/A'}")

        # 5. 识别高产作者
        top_authors = self._find_top_authors(papers)
        print(f"   高产作者: {top_authors[:3]}")

        # 6. 生成摘要
        summary = self._generate_summary(topic, papers, themes, gaps)

        return ResearchState(
            query=topic,
            total_results=len(papers),
            papers=papers,
            key_themes=themes,
            research_gaps=gaps,
            timeline=timeline,
            top_authors=top_authors,
            summary=summary
        )

    def _extract_themes(self, papers: List[Paper]) -> List[str]:
        """提取关键主题"""
        # 高频词统计
        word_freq: Dict[str, int] = {}

        # 停用词
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'i', 'we', 'you', 'he', 'she', 'it',
            'they', 'their', 'its', 'our', 'my', 'your', 'his', 'her', 'which',
            'what', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'also', 'now', 'paper', 'show'
        }

        for paper in papers:
            # 从标题和摘要提取词
            text = (paper.title + ' ' + paper.abstract).lower()
            words = re.findall(r'[a-z]{4,}', text)

            for word in words:
                if word not in stopwords and word not in ['arxiv', 'http']:
                    word_freq[word] = word_freq.get(word, 0) + 1

        # 取Top 10高频词作为主题
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        themes = [word for word, freq in sorted_words[:10] if freq >= 2]

        return themes

    def _analyze_gaps(self, papers: List[Paper], themes: List[str]) -> List[ResearchGap]:
        """分析研究空白"""
        gaps = []
        gap_id = 1

        # 1. 方法学Gap - 检查是否有多种方法对比
        method_keywords = ['method', 'approach', 'algorithm', 'model', 'network', 'framework']
        has_method_comparison = any(
            any(kw in p.title.lower() for kw in ['compare', 'benchmark', 'evaluation'])
            for p in papers[:10]
        )

        if not has_method_comparison:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="methodology",
                description="缺乏方法对比研究，现有方法缺少标准化基准评测",
                evidence=["大多数论文仅与少数基线对比", "缺少公开的基准数据集和评测协议"],
                opportunity="建立标准评测基准，推动方法公平比较",
                priority="high"
            ))
            gap_id += 1

        # 2. 应用领域Gap - 检查应用场景多样性
        application_keywords = ['astronomy', 'astrophysics', 'space', 'galaxy', 'star', 'planet']
        applications_found = set()
        for paper in papers:
            for cat in paper.categories:
                for app_kw in application_keywords:
                    if app_kw in cat.lower():
                        applications_found.add(cat)

        if len(applications_found) < 3:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="application",
                description=f"应用领域较窄，主要集中在 {applications_found}，跨领域应用不足",
                evidence=[f"仅发现 {len(applications_found)} 个相关分类"],
                opportunity="探索该方法在天文其他领域（如系外行星、宇宙学）的应用",
                priority="medium"
            ))
            gap_id += 1

        # 3. 数据集Gap - 检查是否提供数据集
        has_dataset = any(
            'dataset' in p.title.lower() or 'data' in p.title.lower()
            for p in papers[:5]
        )

        if not has_dataset:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="dataset",
                description="缺乏公开数据集和基准数据，方法复现困难",
                evidence=["论文未提供训练/测试数据集", "结果难以复现验证"],
                opportunity="发布公开数据集，促进方法复现和比较",
                priority="high"
            ))
            gap_id += 1

        # 4. 可解释性Gap - 检查可解释性研究
        explainability_keywords = ['explain', 'interpret', 'understand', 'visualization', 'attention']
        has_explainability = any(
            any(kw in p.title.lower() for kw in explainability_keywords)
            for p in papers
        )

        if not has_explainability:
            gaps.append(ResearchGap(
                id=f"gap-{gap_id}",
                category="evaluation",
                description="缺乏可解释性研究，模型决策过程不透明",
                evidence=["极少论文讨论模型内部机制", "注意力可视化等工作较少"],
                opportunity="增加模型可解释性分析，帮助理解模型行为",
                priority="medium"
            ))
            gap_id += 1

        return gaps

    def _analyze_timeline(self, papers: List[Paper]) -> Dict[str, int]:
        """分析论文发表时间线"""
        timeline: Dict[str, int] = {}

        for paper in papers:
            try:
                year = paper.published_date[:4]
                timeline[year] = timeline.get(year, 0) + 1
            except:
                continue

        return dict(sorted(timeline.items()))

    def _find_top_authors(self, papers: List[Paper], top_n: int = 5) -> List[Tuple[str, int]]:
        """识别高产作者"""
        author_counts: Dict[str, int] = {}

        for paper in papers:
            for author in paper.authors[:5]:  # 只统计前5个作者
                author_counts[author] = author_counts.get(author, 0) + 1

        sorted_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_authors[:top_n]

    def _generate_summary(self, topic: str, papers: List[Paper],
                          themes: List[str], gaps: List[ResearchGap]) -> str:
        """生成研究摘要"""
        lines = [
            f"# {topic} 研究现状摘要",
            "",
            f"## 概述",
            f"本次调研共找到 {len(papers)} 篇相关论文，识别出 {len(themes)} 个关键主题和 {len(gaps)} 个研究空白。",
            "",
            f"## 关键主题",
            ", ".join(themes[:5]),
            "",
            f"## 主要发现",
        ]

        # 添加Gap描述
        for gap in gaps[:3]:
            lines.append(f"- **{gap.category.upper()}:** {gap.description}")

        lines.extend([
            "",
            f"## 建议",
            "1. 优先关注高优先级的Gap",
            "2. 借鉴高产作者的研究思路",
            "3. 关注时间线上的研究趋势"
        ])

        return "\n".join(lines)

    async def generate_review(self, topic: str, max_papers: int = 50) -> LiteratureReview:
        """
        生成完整文献综述

        Args:
            topic: 研究主题
            max_papers: 最大论文数

        Returns:
            LiteratureReview: 文献综述
        """
        research_state = await self.research(topic, max_papers)

        # 构建综述结构
        sections = {
            "abstract": f"本综述系统调研了{topic}领域的研究现状，涵盖{len(research_state.papers)}篇论文。",
            "introduction": self._generate_introduction(research_state),
            "related_work": self._generate_related_work(research_state),
            "research_gaps": self._generate_gaps_section(research_state.research_gaps),
            "future_directions": self._generate_future_directions(research_state.research_gaps),
            "conclusion": self._generate_conclusion(research_state)
        }

        # 构建参考文献
        references = []
        for i, paper in enumerate(research_state.papers[:20], 1):
            references.append({
                "id": i,
                "title": paper.title,
                "authors": ", ".join(paper.authors[:3]) + (" et al." if len(paper.authors) > 3 else ""),
                "venue": "arXiv",
                "year": paper.published_date[:4],
                "url": paper.arxiv_url
            })

        return LiteratureReview(
            title=f"{topic} 文献综述",
            query=topic,
            date=datetime.now().strftime('%Y-%m-%d'),
            sections=sections,
            references=references,
            gaps=research_state.research_gaps,
            future_directions=[g.opportunity for g in research_state.research_gaps]
        )

    def _generate_introduction(self, state: ResearchState) -> str:
        return f"""
## 引言

{state.query}是当前研究的重要方向。本综述基于{state.total_results}篇arXiv论文，系统分析该领域的研究现状、关键方法和开放问题。

### 关键统计
- 论文总数: {state.total_results}
- 关键主题: {', '.join(state.key_themes[:5])}
- 高产作者: {', '.join([a[0] for a in state.top_authors[:3]])}
- 时间跨度: {min(state.timeline.keys()) if state.timeline else 'N/A'} - {max(state.timeline.keys()) if state.timeline else 'N/A'}

### 研究趋势
{self._format_timeline(state.timeline)}
"""

    def _generate_related_work(self, state: ResearchState) -> str:
        papers_text = []
        for paper in state.papers[:5]:
            papers_text.append(f"### {paper.title}\n- 作者: {', '.join(paper.authors[:3])}\n- 摘要: {paper.abstract[:200]}...\n")

        return f"## 相关工作\n\n" + "\n\n".join(papers_text)

    def _generate_gaps_section(self, gaps: List[ResearchGap]) -> str:
        gaps_text = []
        for gap in gaps:
            gaps_text.append(f"""
### {gap.id}. {gap.category.upper()} Gap [{gap.priority}]

**描述**: {gap.description}

**证据**:
{chr(10).join(f'- {e}' for e in gap.evidence)}

**研究机会**: {gap.opportunity}
""")

        return f"## 研究空白\n\n" + "\n".join(gaps_text)

    def _generate_future_directions(self, gaps: List[ResearchGap]) -> str:
        directions = [f"- {gap.opportunity}" for gap in gaps]
        return f"## 未来方向\n\n" + "\n".join(directions)

    def _generate_conclusion(self, state: ResearchState) -> str:
        return f"""
## 结论

本综述对{state.query}领域进行了系统调研。主要发现包括：

1. 该领域共有{state.total_results}篇相关论文
2. 关键主题包括: {', '.join(state.key_themes[:5])}
3. 识别出{len(state.research_gaps)}个研究空白，其中高优先级{sum(1 for g in state.research_gaps if g.priority == 'high')}个

建议后续研究重点关注研究空白，推动领域发展。
"""

    def _format_timeline(self, timeline: Dict[str, int]) -> str:
        if not timeline:
            return "数据不足"

        lines = []
        for year, count in sorted(timeline.items()):
            bar = "█" * min(count, 20)
            lines.append(f"- {year}: {bar} ({count})")

        return "\n".join(lines)

# ============ 便捷函数 ============

async def quick_research(topic: str) -> ResearchState:
    """快速文献调研"""
    researcher = LiteratureResearcher()
    return await researcher.research(topic)

async def generate_review(topic: str) -> LiteratureReview:
    """生成完整综述"""
    researcher = LiteratureResearcher()
    return await researcher.generate_review(topic)

# ============ 示例用法 ============

async def demo():
    print("=" * 60)
    print("天问-AGI 文献调研模块演示")
    print("=" * 60)

    researcher = LiteratureResearcher()

    # 1. 快速调研
    print("\n🔍 快速调研: machine learning in astronomy")
    state = await researcher.research("machine learning astronomy", max_papers=20)

    print(f"\n📊 调研结果:")
    print(f"   论文数: {state.total_results}")
    print(f"   关键主题: {', '.join(state.key_themes[:5])}")
    print(f"   研究空白: {len(state.research_gaps)}")

    print(f"\n📅 时间线:")
    for year, count in sorted(state.timeline.items()):
        print(f"   {year}: {count}篇")

    print(f"\n🔬 研究空白:")
    for gap in state.research_gaps:
        print(f"   [{gap.priority.upper()}] {gap.category}: {gap.description[:50]}...")

    # 2. 生成完整综述
    print("\n\n📝 生成完整文献综述...")
    review = await researcher.generate_review("deep learning galaxy classification")

    print(f"\n{'='*60}")
    print(review.sections['introduction'][:500])
    print(f"\n... (详见完整综述)")

    # 3. 保存为JSON
    review_data = {
        "title": review.title,
        "date": review.date,
        "sections": list(review.sections.keys()),
        "references_count": len(review.references),
        "gaps_count": len(review.gaps)
    }
    print(f"\n💾 综述元数据: {json.dumps(review_data, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(demo())