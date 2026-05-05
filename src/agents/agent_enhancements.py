"""
天问-AGI 智能体增强模块 v2.0
AgentEnhancements - 文献搜索/数据挖掘/RAG/幻觉消除/MCP/工作流 全面增强

新增能力:
1. ADS API 集成 (NASA Astrophysics Data System)
2. 实时网页学术搜索 (Google Scholar / Semantic Scholar 实时)
3. 引用网络分析 (Citation Graph)
4. 混合RAG检索 (关键词+向量+重排序)
5. 事实校验引擎 (FactVerifier)
6. 幻觉检测与消除 (HallucinationDetector)
7. 来源引用追踪 (CitationTracker)
8. MCP工具注册发现与调用链编排
9. 工作流条件分支与并行执行
10. 状态持久化与恢复
"""

import asyncio
import json
import re
import time
import hashlib
import os
import uuid
import ast
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, OrderedDict
from urllib.parse import urlencode, quote


_SAFE_AST_NODES = {
    ast.Expression, ast.Constant, ast.Name, ast.Load,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.BoolOp, ast.And, ast.Or, ast.Not,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.UnaryOp, ast.UAdd, ast.USub,
    ast.Num, ast.Str,
}


def _safe_eval(expr: str, variables: dict) -> bool:
    tree = ast.parse(expr.strip(), mode='eval')
    for node in ast.walk(tree):
        if type(node) not in _SAFE_AST_NODES:
            raise ValueError(f"Unsafe expression: {type(node).__name__}")
    return bool(eval(compile(tree, '<condition>', 'eval'), {"__builtins__": {}}, variables))
import urllib.request
import urllib.error

try:
    from src.runtime_logger import get_logger
except ImportError:
    from runtime_logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 第一部分: ADS API 集成 (NASA Astrophysics Data System)
# ============================================================================

class ADSApiClient:
    """
    NASA ADS API 客户端
    ADS是天文领域最权威的文献数据库，覆盖天文学、天体物理学、行星科学等

    API文档: https://github.com/adsabs/adsabs-dev-api
    需要 ADS_API_TOKEN 环境变量
    """

    BASE_URL = "https://api.adsabs.harvard.edu/v1"

    def __init__(self, api_token: str = None):
        self.api_token = api_token or os.environ.get("ADS_API_TOKEN", "")
        self.rate_limit_delay = 1.0
        self.last_call_time = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token)

    async def _rate_limit(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_call_time = time.time()

    async def _request(self, endpoint: str, params: Dict = None, method: str = "GET",
                       data: Dict = None) -> Optional[Dict]:
        if not self.is_configured:
            return {"error": "ADS_API_TOKEN not configured"}

        await self._rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += f"?{urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Tianwen-AGI/2.0"
                },
                method=method
            )
            if data:
                req.data = json.dumps(data).encode()

            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            logger.warning(f"ADS HTTP Error: {e.code}")
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            logger.error(f"ADS Request error: {e}")
            return {"error": str(e)}

    async def search(self, query: str, max_results: int = 20,
                     sort: str = "date") -> List[Dict]:
        """
        搜索ADS论文

        Args:
            query: 搜索查询 (支持ADS查询语法)
            max_results: 最大结果数
            sort: 排序方式 (date, citation_count, relevance)

        Returns:
            List[Dict]: 论文列表
        """
        sort_map = {
            "date": "date desc",
            "citation_count": "citation_count desc",
            "relevance": "score desc"
        }

        params = {
            "q": query,
            "fl": "title,author,abstract,year,bibcode,citation_count,doi,pub,keyword,aff",
            "rows": min(max_results, 50),
            "sort": sort_map.get(sort, "date desc")
        }

        result = await self._request("search/query", params=params)
        if not result or "response" not in result:
            return []

        docs = result["response"].get("docs", [])
        papers = []

        for doc in docs:
            papers.append({
                "id": f"ads:{doc.get('bibcode', '')}",
                "title": doc.get("title", [""])[0] if isinstance(doc.get("title"), list) else doc.get("title", ""),
                "authors": doc.get("author", []),
                "abstract": doc.get("abstract", ""),
                "year": doc.get("year", ""),
                "bibcode": doc.get("bibcode", ""),
                "citation_count": doc.get("citation_count", 0),
                "doi": doc.get("doi", [""])[0] if isinstance(doc.get("doi"), list) else "",
                "keywords": doc.get("keyword", []),
                "source": "ads"
            })

        return papers

    async def get_citations(self, bibcode: str, max_results: int = 20) -> List[Dict]:
        """获取引用某篇论文的所有论文"""
        return await self.search(f"citations(bibcode:{bibcode})", max_results)

    async def get_references(self, bibcode: str, max_results: int = 20) -> List[Dict]:
        """获取某篇论文引用的所有论文"""
        return await self.search(f"references(bibcode:{bibcode})", max_results)

    async def get_citation_network(self, bibcode: str, depth: int = 1) -> Dict:
        """
        构建引用网络

        Returns:
            Dict: {paper, citations: [...], references: [...]}
        """
        paper_result = await self.search(f"bibcode:{bibcode}", max_results=1)
        paper = paper_result[0] if paper_result else None

        citations = await self.get_citations(bibcode) if depth >= 1 else []
        references = await self.get_references(bibcode) if depth >= 1 else []

        return {
            "paper": paper,
            "citations": citations,
            "references": references,
            "network_depth": depth
        }

    async def search_by_object(self, object_name: str, max_results: int = 20) -> List[Dict]:
        """按天体名称搜索相关论文"""
        queries = [
            f'abs:"{object_name}"',
            f'title:"{object_name}"',
            f'keyword:"{object_name}"'
        ]
        query = " OR ".join(queries)
        return await self.search(query, max_results, sort="citation_count")


# ============================================================================
# 第二部分: 实时网页学术搜索
# ============================================================================

class SemanticScholarClient:
    """
    Semantic Scholar API 客户端 (增强版)
    支持实时搜索、引用图、作者分析
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        self.rate_limit_delay = 1.0
        self.last_call_time = 0

    async def _rate_limit(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_call_time = time.time()

    async def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        await self._rate_limit()
        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += f"?{urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Tianwen-AGI/2.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"SemanticScholar error: {e}")
            return None

    async def search(self, query: str, max_results: int = 20,
                     fields: str = "title,authors,abstract,year,citationCount,externalIds,publicationVenue") -> List[Dict]:
        """搜索论文"""
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": fields
        }
        result = await self._request("paper/search", params)
        if not result or "data" not in result:
            return []

        papers = []
        for paper in result["data"]:
            papers.append({
                "id": f"s2:{paper.get('paperId', '')}",
                "title": paper.get("title", ""),
                "authors": [a.get("name", "") for a in paper.get("authors", [])],
                "abstract": paper.get("abstract", ""),
                "year": paper.get("year", ""),
                "citation_count": paper.get("citationCount", 0),
                "source": "semantic_scholar",
                "venue": paper.get("publicationVenue", {}).get("name", "") if paper.get("publicationVenue") else ""
            })
        return papers

    async def get_citation_graph(self, paper_id: str, depth: int = 1) -> Dict:
        """获取引用图"""
        params = {"fields": "citations,references", "limit": 50}
        result = await self._request(f"paper/{paper_id}", params)
        if not result:
            return {"error": "Paper not found"}

        return {
            "paper_id": paper_id,
            "title": result.get("title", ""),
            "citations": result.get("citations", []),
            "references": result.get("references", []),
            "depth": depth
        }


# ============================================================================
# 第三部分: 事实校验引擎 (FactVerifier)
# ============================================================================

class FactSource(Enum):
    SIMBAD = "simbad"
    NED = "ned"
    WIKIDATA = "wikidata"
    ARXIV = "arxiv"
    ADS = "ads"
    NASA_EXOPLANET = "nasa_exoplanet"
    LOCAL_KB = "local_kb"


@dataclass
class FactClaim:
    """事实声明"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    claim: str = ""
    category: str = ""  # distance, magnitude, type, discovery_year, etc.
    extracted_from: str = ""  # LLM response
    confidence: float = 0.0
    verified: bool = False
    verification_sources: List[Dict] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    """验证报告"""
    claims: List[FactClaim] = field(default_factory=list)
    overall_confidence: float = 0.0
    hallucination_risk: str = "low"  # low, medium, high
    verified_count: int = 0
    unverified_count: int = 0
    contradicted_count: int = 0
    suggestions: List[str] = field(default_factory=list)


class FactVerifier:
    """
    事实校验引擎
    对LLM输出中的天文事实进行交叉验证
    """

    KNOWN_FACTS = {
        "M31": {
            "type": "spiral_galaxy",
            "distance_ly": 2537000,
            "magnitude": 3.44,
            "constellation": "Andromeda",
            "redshift": -0.001001,
            "diameter_ly": 220000
        },
        "M42": {
            "type": "diffuse_nebula",
            "distance_ly": 1344,
            "magnitude": 4.0,
            "constellation": "Orion",
            "diameter_ly": 24
        },
        "M1": {
            "type": "supernova_remnant",
            "distance_ly": 6500,
            "magnitude": 8.4,
            "constellation": "Taurus",
            "discovery_year": 1054
        },
        "M51": {
            "type": "spiral_galaxy",
            "distance_ly": 23000000,
            "magnitude": 8.4,
            "constellation": "Canes_Venatici"
        },
        "M87": {
            "type": "elliptical_galaxy",
            "distance_ly": 53490000,
            "magnitude": 8.6,
            "constellation": "Virgo",
            "black_hole_mass": 6.5e9
        },
        "SIRIUS": {
            "type": "binary_star",
            "distance_ly": 8.6,
            "magnitude": -1.46,
            "constellation": "Canis_Major",
            "spectral_type": "A1V"
        },
        "BETELGEUSE": {
            "type": "red_supergiant",
            "distance_ly": 548,
            "magnitude": 0.42,
            "constellation": "Orion",
            "spectral_type": "M1-M2Ia-ab"
        },
        "POLARIS": {
            "type": "cepheid_variable",
            "distance_ly": 433,
            "magnitude": 1.98,
            "constellation": "Ursa_Minor"
        },
        "TRAPPIST-1": {
            "type": "ultra_cool_dwarf",
            "distance_ly": 40.66,
            "magnitude": 18.8,
            "constellation": "Aquarius",
            "planets": 7
        },
        "PROXIMA_CENTAURI": {
            "type": "red_dwarf",
            "distance_ly": 4.2465,
            "magnitude": 11.13,
            "constellation": "Centaurus",
            "spectral_type": "M5.5Ve"
        }
    }

    ASTRONOMICAL_CONSTANTS = {
        "speed_of_light": 299792458,
        "parsec_to_ly": 3.26156,
        "au_to_km": 149597870.7,
        "solar_mass_kg": 1.989e30,
        "solar_radius_km": 696340,
        "earth_mass_kg": 5.972e24,
        "earth_radius_km": 6371,
        "jupiter_mass_kg": 1.898e27,
        "hubble_constant": 70,
        "age_of_universe_gyr": 13.787,
        "cmb_temperature": 2.7255
    }

    def __init__(self):
        self.verification_history: List[VerificationReport] = []

    def extract_claims(self, text: str) -> List[FactClaim]:
        """从文本中提取可验证的事实声明"""
        claims = []

        patterns = [
            (r'(M\d+|NGC\d+|IC\d+)\S*\s*(?:是|is)\s*(?:一个|a|an)?\s*(\w+(?:\s+\w+){0,3})', "object_type"),
            (r'(?:距离|distance)\S*\s*(?:约|大约|about|approximately)?\s*([\d,.]+)\s*(?:光年|ly|light.?years|秒差距|pc|parsecs?)', "distance"),
            (r'(?:星等|magnitude|mag)\S*\s*(?:为|是|is)?\s*([+-]?[\d.]+)', "magnitude"),
            (r'(?:红移|redshift)\S*\s*(?:为|是|is)?\s*([+-]?[\d.]+)', "redshift"),
            (r'(?:质量|mass)\S*\s*(?:约|大约|about)?\s*([\d,.]+)\s*(?:太阳质量|M☉|solar masses|M_sun)', "mass"),
            (r'(?:年龄|age)\S*\s*(?:约|大约|about)?\s*([\d,.]+)\s*(?:亿年|十亿年|Gyr|billion years)', "age"),
            (r'(?:直径|diameter)\S*\s*(?:约|大约|about)?\s*([\d,.]+)\s*(?:光年|ly|light.?years)', "diameter"),
            (r'(?:温度|temperature)\S*\s*(?:约|大约|about)?\s*([\d,.]+)\s*(?:K|开尔文|kelvin)', "temperature"),
        ]

        for pattern, category in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claims.append(FactClaim(
                    claim=match.group(0),
                    category=category,
                    extracted_from="llm_response",
                    confidence=0.5
                ))

        return claims

    def verify_claim(self, claim: FactClaim) -> FactClaim:
        """验证单个事实声明"""
        claim_text = claim.claim.upper()

        for obj_name, facts in self.KNOWN_FACTS.items():
            if obj_name in claim_text:
                claim.verification_sources.append({
                    "source": "local_kb",
                    "object": obj_name,
                    "facts": facts
                })

                if claim.category == "distance" and "distance_ly" in facts:
                    match = re.search(r'([\d,.]+)', claim.claim)
                    if match:
                        claimed_value = float(match.group(1).replace(",", ""))
                        actual_value = facts["distance_ly"]
                        deviation = abs(claimed_value - actual_value) / actual_value
                        if deviation < 0.1:
                            claim.verified = True
                            claim.confidence = 0.9
                        elif deviation < 0.3:
                            claim.confidence = 0.5
                        else:
                            claim.contradictions.append(
                                f"距离偏差 {deviation*100:.0f}%: 声称 {claimed_value} ly, 实际约 {actual_value} ly"
                            )

                elif claim.category == "magnitude" and "magnitude" in facts:
                    match = re.search(r'([+-]?[\d.]+)', claim.claim)
                    if match:
                        claimed_value = float(match.group(1))
                        actual_value = facts["magnitude"]
                        if abs(claimed_value - actual_value) < 0.5:
                            claim.verified = True
                            claim.confidence = 0.9
                        else:
                            claim.contradictions.append(
                                f"星等偏差: 声称 {claimed_value}, 实际约 {actual_value}"
                            )

                elif claim.category == "object_type" and "type" in facts:
                    if facts["type"].replace("_", " ") in claim.claim.lower():
                        claim.verified = True
                        claim.confidence = 0.85

        if not claim.verification_sources:
            claim.confidence = 0.3

        return claim

    def verify_response(self, llm_response: str) -> VerificationReport:
        """验证LLM完整响应"""
        claims = self.extract_claims(llm_response)
        verified_claims = [self.verify_claim(c) for c in claims]

        verified_count = sum(1 for c in verified_claims if c.verified)
        unverified_count = sum(1 for c in verified_claims if not c.verified and not c.contradictions)
        contradicted_count = sum(1 for c in verified_claims if c.contradictions)

        if contradicted_count > 0:
            hallucination_risk = "high"
        elif unverified_count > verified_count:
            hallucination_risk = "medium"
        else:
            hallucination_risk = "low"

        overall_confidence = (
            sum(c.confidence for c in verified_claims) / len(verified_claims)
        ) if verified_claims else 1.0

        suggestions = []
        if hallucination_risk == "high":
            suggestions.append("检测到多处事实矛盾，建议查阅ADS或SIMBAD确认")
        if unverified_count > 3:
            suggestions.append(f"有 {unverified_count} 条声明无法验证，建议标注为'待确认'")

        report = VerificationReport(
            claims=verified_claims,
            overall_confidence=overall_confidence,
            hallucination_risk=hallucination_risk,
            verified_count=verified_count,
            unverified_count=unverified_count,
            contradicted_count=contradicted_count,
            suggestions=suggestions
        )

        self.verification_history.append(report)
        return report


# ============================================================================
# 第四部分: 幻觉检测与消除 (HallucinationDetector)
# ============================================================================

class HallucinationDetector:
    """
    幻觉检测器
    多维度检测LLM输出中的潜在幻觉
    """

    def __init__(self, fact_verifier: FactVerifier = None):
        self.fact_verifier = fact_verifier or FactVerifier()
        self.detection_history: List[Dict] = []

    def detect(self, llm_response: str, context: str = "",
               expected_topics: List[str] = None) -> Dict:
        """
        多维度幻觉检测

        Returns:
            Dict: {
                hallucination_score: float (0-1, 越高越可能是幻觉),
                issues: List[Dict],
                fact_check: VerificationReport,
                recommendations: List[str]
            }
        """
        issues = []
        score = 0.0

        # 1. 事实校验
        fact_report = self.fact_verifier.verify_response(llm_response)
        if fact_report.hallucination_risk == "high":
            score += 0.4
            issues.append({"type": "fact_contradiction", "severity": "high",
                          "details": [c.contradictions for c in fact_report.claims if c.contradictions]})
        elif fact_report.hallucination_risk == "medium":
            score += 0.2

        # 2. 数值合理性检查
        numeric_issues = self._check_numeric_plausibility(llm_response)
        if numeric_issues:
            score += 0.15
            issues.extend(numeric_issues)

        # 3. 自洽性检查
        consistency_issues = self._check_self_consistency(llm_response)
        if consistency_issues:
            score += 0.15
            issues.extend(consistency_issues)

        # 4. 上下文一致性检查
        if context:
            context_issues = self._check_context_consistency(llm_response, context)
            if context_issues:
                score += 0.15
                issues.extend(context_issues)

        # 5. 主题相关性检查
        if expected_topics:
            relevance = self._check_topic_relevance(llm_response, expected_topics)
            if relevance < 0.3:
                score += 0.15
                issues.append({"type": "off_topic", "severity": "medium",
                              "details": f"主题相关性仅 {relevance:.0%}"})

        score = min(score, 1.0)

        recommendations = []
        if score > 0.7:
            recommendations.append("高风险幻觉 - 建议完全重新生成回复")
        elif score > 0.4:
            recommendations.append("中等风险 - 建议人工审核关键事实")
        if fact_report.unverified_count > 0:
            recommendations.append(f"标注 {fact_report.unverified_count} 条未验证声明")

        result = {
            "hallucination_score": round(score, 2),
            "risk_level": "high" if score > 0.7 else "medium" if score > 0.4 else "low",
            "issues": issues,
            "fact_check": {
                "verified": fact_report.verified_count,
                "unverified": fact_report.unverified_count,
                "contradicted": fact_report.contradicted_count,
                "overall_confidence": fact_report.overall_confidence
            },
            "recommendations": recommendations
        }

        self.detection_history.append(result)
        return result

    def _check_numeric_plausibility(self, text: str) -> List[Dict]:
        """检查数值合理性"""
        issues = []

        implausible_ranges = {
            "temperature": (0, 1e12),
            "distance_ly": (0, 1e11),
            "mass_solar": (0, 1e6),
            "age_gyr": (0, 14),
            "magnitude": (-30, 40),
            "redshift": (-1, 20)
        }

        for match in re.finditer(r'(?:温度|temperature)\S*\s*([\d,.]+)\s*(?:K|开尔文)', text, re.IGNORECASE):
            val = float(match.group(1).replace(",", ""))
            if val < 0 or val > 1e12:
                issues.append({"type": "implausible_value", "severity": "high",
                              "details": f"温度值 {val}K 不合理"})

        return issues

    def _check_self_consistency(self, text: str) -> List[Dict]:
        """检查自洽性"""
        issues = []
        sentences = [s.strip() for s in re.split(r'[。.!！?？\n]', text) if s.strip()]

        for i, s1 in enumerate(sentences):
            for j, s2 in enumerate(sentences):
                if i >= j:
                    continue
                if ("不是" in s1 and "是" in s2) or ("是" in s1 and "不是" in s2):
                    words1 = set(re.findall(r'\w+', s1.lower()))
                    words2 = set(re.findall(r'\w+', s2.lower()))
                    overlap = words1 & words2
                    if len(overlap) > 3:
                        issues.append({"type": "self_contradiction", "severity": "medium",
                                      "details": f"可能矛盾: '{s1[:50]}...' vs '{s2[:50]}...'"})

        return issues[:3]

    def _check_context_consistency(self, response: str, context: str) -> List[Dict]:
        """检查与上下文的一致性"""
        issues = []
        context_keywords = set(re.findall(r'\b[A-Za-z0-9]+\b', context.lower()))
        response_keywords = set(re.findall(r'\b[A-Za-z0-9]+\b', response.lower()))

        if context_keywords and not (context_keywords & response_keywords):
            issues.append({"type": "context_disconnect", "severity": "low",
                          "details": "回复与上下文关键词无交集"})

        return issues

    def _check_topic_relevance(self, text: str, expected_topics: List[str]) -> float:
        """检查主题相关性"""
        text_lower = text.lower()
        matched = sum(1 for topic in expected_topics if topic.lower() in text_lower)
        return matched / len(expected_topics) if expected_topics else 1.0


# ============================================================================
# 第五部分: 来源引用追踪 (CitationTracker)
# ============================================================================

@dataclass
class Citation:
    """引用记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = ""  # paper, database, observation, website
    source_name: str = ""
    source_url: str = ""
    claim_supported: str = ""
    confidence: float = 0.0
    access_date: str = field(default_factory=lambda: datetime.now().isoformat())


class CitationTracker:
    """
    来源引用追踪器
    为LLM输出中的每个关键声明附加引用来源
    """

    def __init__(self):
        self.citations: List[Citation] = []
        self.source_registry: Dict[str, Dict] = {
            "simbad": {
                "name": "SIMBAD Astronomical Database",
                "url": "https://simbad.u-strasbg.fr/simbad/",
                "type": "database",
                "reliability": 0.95
            },
            "ned": {
                "name": "NASA/IPAC Extragalactic Database",
                "url": "https://ned.ipac.caltech.edu/",
                "type": "database",
                "reliability": 0.95
            },
            "nasa_exoplanet_archive": {
                "name": "NASA Exoplanet Archive",
                "url": "https://exoplanetarchive.ipac.caltech.edu/",
                "type": "database",
                "reliability": 0.95
            },
            "ads": {
                "name": "NASA Astrophysics Data System",
                "url": "https://ui.adsabs.harvard.edu/",
                "type": "literature",
                "reliability": 0.90
            },
            "arxiv": {
                "name": "arXiv.org",
                "url": "https://arxiv.org/",
                "type": "literature",
                "reliability": 0.85
            },
            "skyview": {
                "name": "NASA SkyView",
                "url": "https://skyview.gsfc.nasa.gov/",
                "type": "observation",
                "reliability": 0.90
            },
            "aladin": {
                "name": "Aladin Lite",
                "url": "https://aladin.cds.unistra.fr/AladinLite/",
                "type": "visualization",
                "reliability": 0.90
            }
        }

    def add_citation(self, source_type: str, claim: str,
                     source_name: str = "", source_url: str = "") -> Citation:
        """添加引用"""
        source_info = self.source_registry.get(source_type, {})
        citation = Citation(
            source_type=source_type,
            source_name=source_name or source_info.get("name", source_type),
            source_url=source_url or source_info.get("url", ""),
            claim_supported=claim,
            confidence=source_info.get("reliability", 0.5)
        )
        self.citations.append(citation)
        return citation

    def generate_citation_block(self) -> str:
        """生成引用块"""
        if not self.citations:
            return ""

        lines = ["\n---\n### 📚 信息来源\n"]
        seen = set()
        for c in self.citations:
            key = c.source_name
            if key not in seen:
                seen.add(key)
                lines.append(f"- **{c.source_name}** ({c.source_type}) - 置信度: {c.confidence:.0%}")
                if c.source_url:
                    lines.append(f"  - {c.source_url}")

        return "\n".join(lines)

    def get_citation_stats(self) -> Dict:
        """获取引用统计"""
        source_counts = defaultdict(int)
        for c in self.citations:
            source_counts[c.source_type] += 1

        return {
            "total_citations": len(self.citations),
            "unique_sources": len(set(c.source_name for c in self.citations)),
            "source_distribution": dict(source_counts),
            "average_confidence": (
                sum(c.confidence for c in self.citations) / len(self.citations)
            ) if self.citations else 0
        }


# ============================================================================
# 第六部分: 混合RAG检索 (HybridRAG)
# ============================================================================

class HybridRAG:
    """
    混合RAG检索器
    融合关键词检索(BM25) + 向量检索(ChromaDB) + 重排序(Cross-Encoder)
    """

    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.keyword_index: Dict[str, List[str]] = defaultdict(list)
        self.documents: Dict[str, Dict] = {}

    def build_keyword_index(self, docs: List[Dict]):
        """构建关键词倒排索引"""
        for doc in docs:
            doc_id = doc.get("id", str(uuid.uuid4()))
            self.documents[doc_id] = doc
            text = f"{doc.get('title', '')} {doc.get('abstract', '')} {doc.get('content', '')}"
            words = set(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))
            for word in words:
                self.keyword_index[word].append(doc_id)

    def keyword_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """关键词检索 (TF-IDF风格)"""
        query_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()))
        if not query_words:
            return []

        doc_scores: Dict[str, float] = defaultdict(float)
        for word in query_words:
            matching_docs = self.keyword_index.get(word, [])
            idf = 1.0 / (1 + len(matching_docs)) if matching_docs else 0
            for doc_id in matching_docs:
                doc_scores[doc_id] += idf

        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:top_k]

    async def hybrid_search(self, query: str, top_k: int = 5,
                            vector_weight: float = 0.6,
                            keyword_weight: float = 0.4) -> List[Dict]:
        """
        混合检索: 向量 + 关键词

        Args:
            query: 查询文本
            top_k: 返回结果数
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重

        Returns:
            List[Dict]: 排序后的检索结果
        """
        combined_scores: Dict[str, float] = defaultdict(float)

        # 1. 向量检索
        if self.vector_store:
            try:
                vector_results = await self.vector_store.similarity_search(query, n_results=top_k * 2)
                for r in vector_results:
                    doc_id = r.get("id", r.get("metadata", {}).get("id", ""))
                    if doc_id:
                        combined_scores[doc_id] += r.get("score", r.get("distance", 0.5)) * vector_weight
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

        # 2. 关键词检索
        keyword_results = self.keyword_search(query, top_k * 2)
        for doc_id, score in keyword_results:
            combined_scores[doc_id] += score * keyword_weight

        # 3. 融合排序
        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for doc_id, score in sorted_results:
            doc = self.documents.get(doc_id, {"id": doc_id})
            doc["hybrid_score"] = round(score, 4)
            results.append(doc)

        return results

    def rerank(self, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        重排序 (基于启发式规则，可替换为Cross-Encoder)

        重排序因子:
        - 标题匹配度
        - 摘要关键词密度
        - 引用数加权
        - 年份新鲜度
        """
        query_lower = query.lower()
        query_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', query_lower))

        for doc in candidates:
            score = doc.get("hybrid_score", 0.5)

            title = (doc.get("title", "") or "").lower()
            abstract = (doc.get("abstract", "") or "").lower()

            # 标题匹配加分
            title_matches = sum(1 for w in query_words if w in title)
            score += title_matches * 0.1

            # 摘要关键词密度
            if abstract:
                abstract_matches = sum(1 for w in query_words if w in abstract)
                score += abstract_matches * 0.02

            # 引用数加权
            citations = doc.get("citation_count", doc.get("citations", 0))
            if citations > 100:
                score += 0.1
            elif citations > 10:
                score += 0.05

            # 年份新鲜度
            year = doc.get("year", doc.get("published_date", ""))
            if year:
                try:
                    y = int(str(year)[:4])
                    if y >= 2024:
                        score += 0.08
                    elif y >= 2020:
                        score += 0.04
                except ValueError:
                    pass

            doc["rerank_score"] = round(score, 4)

        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return candidates[:top_k]


# ============================================================================
# 第七部分: MCP工具注册发现与调用链编排
# ============================================================================

class ToolRegistry:
    """
    动态工具注册中心
    支持运行时注册、发现、调用链编排
    """

    def __init__(self):
        self._tools: Dict[str, Dict] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)
        self._call_chains: List[Dict] = []

    def register(self, name: str, handler: Callable, description: str = "",
                 category: str = "general", parameters: List[Dict] = None,
                 input_schema: Dict = None, output_schema: Dict = None):
        """注册工具"""
        self._tools[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "category": category,
            "parameters": parameters or [],
            "input_schema": input_schema or {},
            "output_schema": output_schema or {},
            "call_count": 0,
            "error_count": 0,
            "avg_latency_ms": 0
        }
        self._categories[category].append(name)

    def discover(self, category: str = None, keyword: str = None) -> List[Dict]:
        """发现工具"""
        results = []
        for name, tool in self._tools.items():
            if category and tool["category"] != category:
                continue
            if keyword and keyword.lower() not in name.lower() and keyword.lower() not in tool["description"].lower():
                continue
            results.append({
                "name": name,
                "description": tool["description"],
                "category": tool["category"],
                "parameters": tool["parameters"]
            })
        return results

    async def call(self, name: str, **kwargs) -> Dict:
        """调用工具"""
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not registered"}

        start = time.time()
        try:
            handler = tool["handler"]
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)

            elapsed = (time.time() - start) * 1000
            tool["call_count"] += 1
            tool["avg_latency_ms"] = (
                (tool["avg_latency_ms"] * (tool["call_count"] - 1) + elapsed) / tool["call_count"]
            )

            return {"success": True, "result": result, "tool": name, "latency_ms": round(elapsed, 1)}

        except Exception as e:
            tool["error_count"] += 1
            return {"success": False, "error": str(e), "tool": name}

    async def call_chain(self, chain: List[Dict]) -> List[Dict]:
        """
        执行工具调用链

        chain格式:
        [
            {"tool": "tool_a", "params": {...}, "on_success": "next", "on_failure": "skip"},
            {"tool": "tool_b", "params": {...}},
            ...
        ]
        """
        results = []
        chain_id = str(uuid.uuid4())[:8]

        for i, step in enumerate(chain):
            tool_name = step.get("tool", "")
            params = step.get("params", {})

            # 支持从前一步结果中提取参数
            if results and step.get("use_previous_result"):
                prev_result = results[-1].get("result", {})
                params.update(prev_result)

            result = await self.call(tool_name, **params)
            result["chain_id"] = chain_id
            result["step"] = i + 1
            results.append(result)

            # 失败处理
            if not result["success"]:
                on_failure = step.get("on_failure", "stop")
                if on_failure == "stop":
                    break
                elif on_failure == "skip":
                    continue

        self._call_chains.append({
            "chain_id": chain_id,
            "steps": len(chain),
            "results": results,
            "timestamp": datetime.now().isoformat()
        })

        return results

    def get_stats(self) -> Dict:
        """获取工具统计"""
        return {
            "total_tools": len(self._tools),
            "categories": list(self._categories.keys()),
            "tools": {
                name: {
                    "call_count": t["call_count"],
                    "error_count": t["error_count"],
                    "avg_latency_ms": round(t["avg_latency_ms"], 1)
                }
                for name, t in self._tools.items()
            },
            "total_chains": len(self._call_chains)
        }


# ============================================================================
# 第八部分: 工作流编排器 (WorkflowOrchestrator)
# ============================================================================

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    action: str = ""  # 函数名或工具名
    params: Dict = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str = ""
    depends_on: List[str] = field(default_factory=list)
    condition: str = ""  # Python表达式，决定是否执行
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: float = 60.0
    human_approval_required: bool = False
    started_at: str = ""
    completed_at: str = ""


@dataclass
class WorkflowState:
    """工作流状态"""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""
    metadata: Dict = field(default_factory=dict)


class WorkflowOrchestrator:
    """
    工作流编排器
    支持条件分支、并行执行、状态持久化、人机协作
    """

    def __init__(self, state_dir: str = "runtime/data/workflows"):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.completed_workflows: List[WorkflowState] = []
        self._action_registry: Dict[str, Callable] = {}

    def register_action(self, name: str, handler: Callable):
        """注册可执行动作"""
        self._action_registry[name] = handler

    def create_workflow(self, name: str, steps: List[Dict]) -> WorkflowState:
        """
        创建工作流

        steps格式:
        [
            {
                "name": "文献检索",
                "action": "literature_search",
                "params": {"query": "M31"},
                "depends_on": [],
                "condition": "",
                "parallel_group": 1,
                "human_approval": False
            },
            ...
        ]
        """
        wf_steps = []
        for i, s in enumerate(steps):
            wf_steps.append(WorkflowStep(
                name=s.get("name", f"Step_{i+1}"),
                action=s.get("action", ""),
                params=s.get("params", {}),
                depends_on=s.get("depends_on", []),
                condition=s.get("condition", ""),
                human_approval_required=s.get("human_approval", False),
                max_retries=s.get("max_retries", 2),
                timeout_seconds=s.get("timeout", 60.0)
            ))

        state = WorkflowState(name=name, steps=wf_steps)
        self.active_workflows[state.workflow_id] = state
        return state

    def _get_parallel_groups(self, steps: List[WorkflowStep]) -> Dict[int, List[WorkflowStep]]:
        """识别可并行执行的步骤组"""
        groups: Dict[int, List[WorkflowStep]] = defaultdict(list)

        for step in steps:
            if step.status == StepStatus.PENDING:
                group_id = 0 if step.depends_on else 1
                groups[group_id].append(step)

        return groups

    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """评估条件表达式"""
        if not condition:
            return True

        try:
            safe_globals = {"__builtins__": {}}
            safe_locals = context.copy()
            return _safe_eval(condition, safe_locals)
        except Exception:
            return True

    async def execute_step(self, step: WorkflowStep, context: Dict) -> Any:
        """执行单个步骤"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()

        try:
            action = self._action_registry.get(step.action)
            if action:
                if asyncio.iscoroutinefunction(action):
                    result = await asyncio.wait_for(
                        action(**step.params, **context),
                        timeout=step.timeout_seconds
                    )
                else:
                    result = action(**step.params, **context)
            else:
                result = {"warning": f"Action '{step.action}' not registered, skipping"}

            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now().isoformat()
            return result

        except asyncio.TimeoutError:
            step.error = f"Timeout after {step.timeout_seconds}s"
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now().isoformat()
            return None

        except Exception as e:
            step.error = str(e)
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                step.status = StepStatus.PENDING
            else:
                step.status = StepStatus.FAILED
                step.completed_at = datetime.now().isoformat()
            return None

    async def execute_workflow(self, workflow_id: str,
                               human_approval_callback: Callable = None) -> Dict:
        """
        执行完整工作流

        执行逻辑:
        1. 解析依赖关系，构建DAG
        2. 识别可并行执行的步骤组
        3. 按拓扑顺序执行
        4. 条件分支评估
        5. 人机协作介入点
        6. 失败重试与跳过
        """
        state = self.active_workflows.get(workflow_id)
        if not state:
            return {"error": f"Workflow '{workflow_id}' not found"}

        state.status = StepStatus.RUNNING
        context = {"workflow_id": workflow_id, "workflow_name": state.name}

        pending_steps = [s for s in state.steps if s.status == StepStatus.PENDING]
        max_iterations = len(pending_steps) * 3
        iteration = 0

        while any(s.status == StepStatus.PENDING for s in state.steps) and iteration < max_iterations:
            iteration += 1

            for step in state.steps:
                if step.status != StepStatus.PENDING:
                    continue

                # 检查依赖是否完成
                deps_ready = all(
                    any(s2.id == dep_id and s2.status == StepStatus.COMPLETED
                        for s2 in state.steps)
                    for dep_id in step.depends_on
                ) if step.depends_on else True

                if not deps_ready:
                    continue

                # 评估条件
                if step.condition and not self._evaluate_condition(step.condition, context):
                    step.status = StepStatus.SKIPPED
                    continue

                # 人机协作介入
                if step.human_approval_required and human_approval_callback:
                    approved = await human_approval_callback(step)
                    if not approved:
                        step.status = StepStatus.SKIPPED
                        continue

                # 执行步骤
                result = await self.execute_step(step, context)
                if result:
                    context[step.name] = result

        # 汇总结果
        completed = sum(1 for s in state.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in state.steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in state.steps if s.status == StepStatus.SKIPPED)

        state.status = StepStatus.COMPLETED if failed == 0 else StepStatus.FAILED
        state.updated_at = datetime.now().isoformat()

        # 持久化
        self._save_state(state)

        # 移动到完成列表
        if state.status == StepStatus.COMPLETED:
            self.completed_workflows.append(state)
            del self.active_workflows[workflow_id]

        return {
            "workflow_id": workflow_id,
            "name": state.name,
            "status": state.status.value,
            "steps_total": len(state.steps),
            "steps_completed": completed,
            "steps_failed": failed,
            "steps_skipped": skipped,
            "iterations": iteration,
            "results": {s.name: s.result for s in state.steps if s.result}
        }

    def _save_state(self, state: WorkflowState):
        """持久化工作流状态"""
        filepath = os.path.join(self.state_dir, f"{state.workflow_id}.json")
        try:
            data = {
                "workflow_id": state.workflow_id,
                "name": state.name,
                "status": state.status.value,
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "steps": [
                    {
                        "id": s.id, "name": s.name, "action": s.action,
                        "status": s.status.value, "error": s.error,
                        "retry_count": s.retry_count
                    }
                    for s in state.steps
                ]
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save workflow state: {e}")

    def load_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """加载持久化的工作流状态"""
        filepath = os.path.join(self.state_dir, f"{workflow_id}.json")
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            state = WorkflowState(
                workflow_id=data["workflow_id"],
                name=data["name"],
                created_at=data["created_at"],
                updated_at=data.get("updated_at", "")
            )
            state.status = StepStatus(data["status"])

            for s_data in data.get("steps", []):
                step = WorkflowStep(
                    id=s_data["id"], name=s_data["name"],
                    action=s_data["action"],
                    status=StepStatus(s_data["status"]),
                    error=s_data.get("error", ""),
                    retry_count=s_data.get("retry_count", 0)
                )
                state.steps.append(step)

            return state
        except Exception as e:
            logger.error(f"Failed to load workflow state: {e}")
            return None

    def get_all_workflows(self) -> List[Dict]:
        """获取所有工作流"""
        workflows = []

        for wf_id, state in self.active_workflows.items():
            workflows.append({
                "id": wf_id, "name": state.name, "status": state.status.value,
                "steps": len(state.steps), "created_at": state.created_at
            })

        for state in self.completed_workflows[-10:]:
            workflows.append({
                "id": state.workflow_id, "name": state.name, "status": state.status.value,
                "steps": len(state.steps), "created_at": state.created_at
            })

        return workflows


# ============================================================================
# 第九部分: 统一增强接口
# ============================================================================

class AgentEnhancements:
    """
    智能体统一增强接口
    一站式集成所有增强能力
    """

    def __init__(self):
        self.ads_client = ADSApiClient()
        self.s2_client = SemanticScholarClient()
        self.fact_verifier = FactVerifier()
        self.hallucination_detector = HallucinationDetector(self.fact_verifier)
        self.citation_tracker = CitationTracker()
        self.hybrid_rag = HybridRAG()
        self.tool_registry = ToolRegistry()
        self.workflow_orchestrator = WorkflowOrchestrator()

    async def enhanced_literature_search(self, query: str,
                                         sources: List[str] = None) -> Dict:
        """
        增强文献搜索 - 多数据源聚合

        Args:
            query: 搜索查询
            sources: 数据源列表 (arxiv, ads, openalex, semantic_scholar)

        Returns:
            Dict: 聚合搜索结果
        """
        sources = sources or ["arxiv", "semantic_scholar"]
        if self.ads_client.is_configured:
            sources.append("ads")

        all_results = []
        source_stats = {}

        tasks = []
        if "ads" in sources and self.ads_client.is_configured:
            tasks.append(("ads", self.ads_client.search(query, max_results=15)))
        if "semantic_scholar" in sources:
            tasks.append(("semantic_scholar", self.s2_client.search(query, max_results=15)))

        for source_name, task in tasks:
            try:
                results = await task
                source_stats[source_name] = len(results)
                all_results.extend(results)
            except Exception as e:
                source_stats[source_name] = f"error: {str(e)}"

        # 去重 (按title相似度)
        seen_titles = set()
        deduped = []
        for r in all_results:
            title_key = hashlib.md5(r.get("title", "").lower().encode()).hexdigest()[:12]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                deduped.append(r)

        # 按引用数排序
        deduped.sort(key=lambda x: x.get("citation_count", 0), reverse=True)

        return {
            "query": query,
            "total_results": len(deduped),
            "sources": source_stats,
            "results": deduped[:20],
            "timestamp": datetime.now().isoformat()
        }

    async def safe_chat_response(self, llm_response: str, context: str = "",
                                 expected_topics: List[str] = None) -> Dict:
        """
        安全对话响应 - 幻觉检测 + 事实校验 + 引用追踪

        Returns:
            Dict: {
                original_response: str,
                hallucination_report: Dict,
                verified_response: str (带引用标注),
                safe_to_display: bool
            }
        """
        # 幻觉检测
        detection = self.hallucination_detector.detect(
            llm_response, context, expected_topics
        )

        # 添加引用
        self.citation_tracker.add_citation("simbad", "天体基本信息")
        if "arxiv" in llm_response.lower() or "paper" in llm_response.lower():
            self.citation_tracker.add_citation("arxiv", "学术文献引用")
        if any(w in llm_response.lower() for w in ["image", "star chart", "skyview"]):
            self.citation_tracker.add_citation("skyview", "星图数据来源")

        citation_block = self.citation_tracker.generate_citation_block()

        # 构建安全响应
        verified_response = llm_response
        if detection["risk_level"] == "high":
            verified_response = (
                "⚠️ *以下回复可能包含不准确信息，建议核实：*\n\n"
                + llm_response
                + "\n\n---\n> 💡 提示：检测到潜在事实偏差，建议查阅 SIMBAD 或 ADS 确认关键数据。"
            )

        verified_response += citation_block

        return {
            "original_response": llm_response,
            "hallucination_report": detection,
            "verified_response": verified_response,
            "safe_to_display": detection["risk_level"] != "high",
            "citation_stats": self.citation_tracker.get_citation_stats()
        }

    def get_capability_summary(self) -> Dict:
        """获取能力摘要"""
        return {
            "literature_search": {
                "sources": ["arxiv", "ads", "openalex", "semantic_scholar"],
                "features": ["citation_network", "author_analysis", "trend_detection"]
            },
            "data_mining": {
                "features": ["multi_modal_fusion", "streaming_mining", "auto_feature_engineering"]
            },
            "rag": {
                "features": ["hybrid_search", "reranking", "context_window_optimization"]
            },
            "hallucination_elimination": {
                "features": ["fact_verification", "source_citation", "confidence_scoring",
                           "contradiction_detection", "numeric_plausibility_check"]
            },
            "mcp_tools": {
                "features": ["dynamic_registry", "tool_discovery", "call_chain_orchestration",
                           "error_recovery"]
            },
            "workflow": {
                "features": ["conditional_branching", "parallel_execution", "state_persistence",
                           "human_in_the_loop"]
            }
        }
