"""
天问-AGI 发现追踪器 v1.0
DiscoveryTracker - 追踪假说验证结果，形成完整研究闭环

采用 Hermes 建议的架构:
- Neo4j (图数据库): 存储假说关系、验证链条、因果网络
- ChromaDB (向量数据库): 存储文献/观测数据的语义向量

图结构:
  (发现) -[推导]-> (假说) -[验证]-> (结果)
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import os


class Neo4jConnectionError(Exception):
    """Neo4j连接失败异常"""
    pass


class Neo4jOperationError(Exception):
    """Neo4j操作失败异常"""
    pass


class ConnectionPool:
    """
    Neo4j连接池管理
    支持连接复用、健康检查和重试机制
    """

    def __init__(self, uri: str, username: str, password: str,
                 max_retries: int = 3, retry_delay: float = 1.0):
        self.uri = uri.rstrip("/")
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._connected = False
        self._last_check = 0
        self._check_interval = 30  # 30秒检查间隔

    def _get_headers(self) -> Dict:
        import base64
        auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }

    def is_healthy(self) -> bool:
        """检查连接是否健康"""
        now = time.time()
        if now - self._last_check < self._check_interval and self._connected:
            return self._connected

        try:
            import urllib.request

            url = f"{self.uri}/db/neo4j.tx/commit"
            data = json.dumps({
                "statements": [{"statement": "RETURN 1", "parameters": {}}]
            }).encode()

            req = urllib.request.Request(
                url, data=data,
                headers=self._get_headers(),
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                self._connected = response.status == 200
                self._last_check = now
                return self._connected

        except Exception:
            self._connected = False
            self._last_check = now
            return False

    def execute_with_retry(self, data: Dict) -> bool:
        """
        执行请求并支持重试机制
        返回: 是否成功
        抛出: Neo4jConnectionError - 连接失败
              Neo4jOperationError - 操作失败
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                import urllib.request
                import urllib.error

                url = f"{self.uri}/db/neo4j.tx/commit"
                encoded_data = json.dumps(data).encode()

                req = urllib.request.Request(
                    url, data=encoded_data,
                    headers=self._get_headers(),
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        return True

                last_error = f"HTTP {response.status}"

            except urllib.error.URLError as e:
                last_error = f"URLError: {str(e)}"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                last_error = f"Exception: {str(e)}"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))

        raise Neo4jConnectionError(
            f"Neo4j操作失败，已重试{self.max_retries}次。最后错误: {last_error}"
        )

    def mark_failed(self):
        """标记连接失败"""
        self._connected = False


class NodeType(Enum):
    DISCOVERY = "discovery"
    HYPOTHESIS = "hypothesis"
    VERIFICATION = "verification"
    RESULT = "result"
    PAPER = "paper"
    OBSERVATION = "observation"


class RelationType(Enum):
    DERIVES = "derives"           # 推导
    SUPPORTS = "supports"         # 支撑
    REJECTS = "rejects"          # 反驳
    VERIFIES = "verifies"        # 验证
    LEADS_TO = "leads_to"        # 导致


class VerificationOutcome(Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    REVISED = "revised"
    INCONCLUSIVE = "inconclusive"


@dataclass
class GraphNode:
    """图数据库节点"""
    id: str
    type: NodeType
    properties: Dict[str, Any]
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "properties": self.properties,
            "created_at": self.created_at
        }


@dataclass
class GraphRelation:
    """图数据库关系"""
    id: str
    source_id: str
    target_id: str
    type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class VerificationRecord:
    """验证记录"""
    id: str
    hypothesis_id: str
    outcome: VerificationOutcome
    evidence: List[str]
    method: str
    notes: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class Neo4jStore:
    """
    Neo4j 图数据库存储层
    使用网络请求访问 Neo4j REST API
    支持连接池和重试机制
    """

    def __init__(self, uri: str = None, username: str = "neo4j", password: str = None,
                 max_retries: int = 3):
        self.uri = uri or os.environ.get("NEO4J_URI", "http://localhost:7474")
        self.username = username
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.base_url = self.uri.rstrip("/")
        self.nodes: List[GraphNode] = []
        self.relations: List[GraphRelation] = []
        self.max_retries = max_retries
        # 连接池实例
        self._pool = ConnectionPool(
            uri=self.base_url,
            username=self.username,
            password=self.password,
            max_retries=max_retries
        )

    def _get_headers(self) -> Dict:
        import base64
        auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }

    async def create_node(self, node: GraphNode) -> bool:
        """创建节点，带重试机制，失败时抛出异常"""
        data = {
            "statements": [{
                "statement": """
                    CREATE (n:GOTChallenge {id: $id, type: $type, properties: $props, created_at: $created_at})
                    RETURN n.id
                """,
                "parameters": {
                    "id": node.id,
                    "type": node.type.value,
                    "props": node.properties,
                    "created_at": node.created_at
                }
            }]
        }

        try:
            self._pool.execute_with_retry(data)
        except Neo4jConnectionError as e:
            raise Neo4jConnectionError(f"创建节点失败: {e}")

        self.nodes.append(node)
        return True

    async def create_relation(self, relation: GraphRelation) -> bool:
        """创建关系，带重试机制，失败时抛出异常"""
        data = {
            "statements": [{
                "statement": """
                    MATCH (a), (b)
                    WHERE a.id = $source AND b.id = $target
                    CREATE (a)-[r:REL {type: $type, properties: $props, created_at: $created_at}]->(b)
                    RETURN r.id
                """,
                "parameters": {
                    "source": relation.source_id,
                    "target": relation.target_id,
                    "type": relation.type.value,
                    "props": relation.properties,
                    "created_at": relation.created_at
                }
            }]
        }

        try:
            self._pool.execute_with_retry(data)
        except Neo4jConnectionError as e:
            raise Neo4jConnectionError(f"创建关系失败: {e}")

        self.relations.append(relation)
        return True

    async def get_hypothesis_history(self, hypothesis_id: str) -> List[Dict]:
        """获取假说的完整验证历史"""
        history = []

        for rel in self.relations:
            if rel.target_id == hypothesis_id or rel.source_id == hypothesis_id:
                history.append({
                    "relation": rel.type.value,
                    "from": rel.source_id,
                    "to": rel.target_id,
                    "created_at": rel.created_at,
                    "properties": rel.properties
                })

        return sorted(history, key=lambda x: x["created_at"])

    async def get_discovery_chain(self, discovery_id: str) -> Dict:
        """获取发现→假说→验证→结果的完整链条"""
        chain = {
            "discovery": None,
            "hypotheses": [],
            "verifications": [],
            "final_outcome": None
        }

        for node in self.nodes:
            if node.id == discovery_id:
                chain["discovery"] = node.to_dict()
                break

        for rel in self.relations:
            if rel.source_id == discovery_id and rel.type == RelationType.DERIVES:
                for node in self.nodes:
                    if node.id == rel.target_id:
                        chain["hypotheses"].append(node.to_dict())

        return chain


class ChromaStore:
    """
    ChromaDB 向量数据库存储层
    存储文献和观测数据的语义向量
    """

    def __init__(self, persist_directory: str = "./chroma_data"):
        self.persist_directory = persist_directory
        self.collections: Dict[str, List[Dict]] = {
            "papers": [],
            "observations": [],
            "hypotheses": []
        }
        self._vectors: Dict[str, List[float]] = {}

    async def add_paper(self, paper_id: str, title: str, abstract: str,
                        embedding: Optional[List[float]] = None) -> bool:
        """添加论文向量"""
        self.collections["papers"].append({
            "id": paper_id,
            "title": title,
            "abstract": abstract
        })
        if embedding:
            self._vectors[paper_id] = embedding
        return True

    async def add_observation(self, obs_id: str, target: str, data_type: str,
                              embedding: Optional[List[float]] = None) -> bool:
        """添加观测向量"""
        self.collections["observations"].append({
            "id": obs_id,
            "target": target,
            "data_type": data_type
        })
        if embedding:
            self._vectors[obs_id] = embedding
        return True

    async def add_hypothesis(self, hypo_id: str, statement: str,
                             embedding: Optional[List[float]] = None) -> bool:
        """添加假说向量"""
        self.collections["hypotheses"].append({
            "id": hypo_id,
            "statement": statement
        })
        if embedding:
            self._vectors[hypo_id] = embedding
        return True

    async def find_similar_papers(self, query_embedding: List[float],
                                  top_k: int = 5) -> List[Tuple[str, float]]:
        """查找相似论文"""
        results = []
        for paper in self.collections["papers"]:
            pid = paper["id"]
            if pid in self._vectors:
                sim = self._cosine_sim(query_embedding, self._vectors[pid])
                results.append((pid, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class DiscoveryTracker:
    """
    发现追踪器 - 完整研究闭环的核心组件

    功能:
    - 追踪每个假说的生命周期（生成→验证→修订/废弃）
    - 记录验证证据和结果
    - 构建发现→假说→验证→结果的有向图
    - 提供可查询的历史和统计

    用法:
        tracker = DiscoveryTracker()
        await tracker.track_hypothesis(hypothesis)
        await tracker.record_verification(hypothesis_id, outcome, evidence)
        chain = await tracker.get_completion_chain(hypothesis_id)
    """

    def __init__(self, neo4j_uri: str = None, chroma_dir: str = "./chroma_data"):
        self.neo4j = Neo4jStore(uri=neo4j_uri)
        self.chroma = ChromaStore(persist_directory=chroma_dir)
        self.verification_records: List[VerificationRecord] = []

    async def track_discovery(self, discovery_id: str, content: str,
                             source: str = "literature") -> bool:
        """追踪一个新发现"""
        node = GraphNode(
            id=discovery_id,
            type=NodeType.DISCOVERY,
            properties={
                "content": content,
                "source": source
            }
        )
        return await self.neo4j.create_node(node)

    async def track_hypothesis(self, hypothesis: Any) -> bool:
        """追踪一个新假说"""
        if hasattr(hypothesis, 'to_dict'):
            props = hypothesis.to_dict()
        else:
            props = hypothesis

        node = GraphNode(
            id=props["id"],
            type=NodeType.HYPOTHESIS,
            properties=props
        )
        result = await self.neo4j.create_node(node)

        await self.chroma.add_hypothesis(
            props["id"],
            props.get("statement", "")
        )

        return result

    async def link_derivation(self, source_id: str, target_id: str,
                               relation_type: RelationType = RelationType.DERIVES) -> bool:
        """建立推导关系"""
        relation = GraphRelation(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            target_id=target_id,
            type=relation_type
        )
        return await self.neo4j.create_relation(relation)

    async def record_verification(
        self,
        hypothesis_id: str,
        outcome: VerificationOutcome,
        evidence: List[str],
        method: str,
        notes: str = ""
    ) -> VerificationRecord:
        """记录假说验证结果"""
        record = VerificationRecord(
            id=f"ver_{uuid.uuid4().hex[:8]}",
            hypothesis_id=hypothesis_id,
            outcome=outcome,
            evidence=evidence,
            method=method,
            notes=notes
        )

        self.verification_records.append(record)

        ver_node = GraphNode(
            id=record.id,
            type=NodeType.VERIFICATION,
            properties={
                "outcome": outcome.value,
                "evidence": evidence,
                "method": method,
                "notes": notes
            }
        )
        await self.neo4j.create_node(ver_node)

        rel_type = RelationType.VERIFIES
        if outcome == VerificationOutcome.REJECTED:
            rel_type = RelationType.REJECTS
        elif outcome == VerificationOutcome.CONFIRMED:
            rel_type = RelationType.SUPPORTS

        await self.neo4j.create_relation(GraphRelation(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            source_id=hypothesis_id,
            target_id=record.id,
            type=rel_type,
            properties={"outcome": outcome.value}
        ))

        return record

    async def get_completion_chain(self, hypothesis_id: str) -> Dict:
        """获取假说的完整闭环链条"""
        chain = await self.neo4j.get_discovery_chain(hypothesis_id)
        chain["verifications"] = []

        for rec in self.verification_records:
            if rec.hypothesis_id == hypothesis_id:
                chain["verifications"].append({
                    "id": rec.id,
                    "outcome": rec.outcome.value,
                    "evidence": rec.evidence,
                    "method": rec.method,
                    "created_at": rec.created_at
                })

        return chain

    async def get_statistics(self) -> Dict:
        """获取追踪统计"""
        total_hypotheses = len([n for n in self.neo4j.nodes if n.type == NodeType.HYPOTHESIS])
        total_verifications = len(self.verification_records)

        confirmed = len([r for r in self.verification_records
                        if r.outcome == VerificationOutcome.CONFIRMED])
        rejected = len([r for r in self.verification_records
                       if r.outcome == VerificationOutcome.REJECTED])

        return {
            "total_hypotheses": total_hypotheses,
            "total_verifications": total_verifications,
            "confirmed": confirmed,
            "rejected": rejected,
            "success_rate": confirmed / total_verifications if total_verifications > 0 else 0,
            "pending": total_hypotheses - total_verifications
        }

    async def get_cycle_statistics(self) -> Dict[str, Any]:
        """
        获取闭环成功率统计面板

        量化研究闭环效率，提供多维度统计指标，帮助针对性优化研究流程。

        Returns:
            Dict containing:
            - total_hypotheses: 假说总数
            - total_verifications: 验证记录总数
            - cycle_completed: 完成闭环的假说数（已确认或已反驳）
            - cycle_pending: 待验证假说数
            - confirmed: 验证通过数
            - rejected: 验证反驳数
            - revised: 验证后修订数
            - inconclusive: 结果不确定数
            - cycle_completion_rate: 闭环完成率 (完成数/总数)
            - hypothesis_pass_rate: 假说通过率 (确认数/已验证数)
            - cycle_success_rate: 闭环成功率 (确认数/完成闭环数)
            - revision_rate: 修订率 (修订数/已验证数)
            - avg_verification_per_hypothesis: 每假说平均验证次数
            - pending_hypotheses: 待验证假说详情
            - recent_cycles: 最近完成的闭环（最近5个）
        """
        # 基本统计
        all_hypotheses = [n for n in self.neo4j.nodes if n.type == NodeType.HYPOTHESIS]
        total_hypotheses = len(all_hypotheses)

        verification_records = self.verification_records
        total_verifications = len(verification_records)

        # 按结果分类
        confirmed = [r for r in verification_records if r.outcome == VerificationOutcome.CONFIRMED]
        rejected = [r for r in verification_records if r.outcome == VerificationOutcome.REJECTED]
        revised = [r for r in verification_records if r.outcome == VerificationOutcome.REVISED]
        inconclusive = [r for r in verification_records if r.outcome == VerificationOutcome.INCONCLUSIVE]

        confirmed_count = len(confirmed)
        rejected_count = len(rejected)
        revised_count = len(revised)
        inconclusive_count = len(inconclusive)

        # 闭环完成 = 确认或反驳（有了明确结论）
        cycle_completed = confirmed_count + rejected_count
        cycle_pending = total_verifications - cycle_completed

        # 计算各指标
        cycle_completion_rate = cycle_completed / total_verifications if total_verifications > 0 else 0.0
        hypothesis_pass_rate = confirmed_count / total_verifications if total_verifications > 0 else 0.0
        cycle_success_rate = confirmed_count / cycle_completed if cycle_completed > 0 else 0.0
        revision_rate = revised_count / total_verifications if total_verifications > 0 else 0.0

        # 每假说平均验证次数
        hypo_verification_counts: Dict[str, int] = {}
        for rec in verification_records:
            hypo_id = rec.hypothesis_id
            hypo_verification_counts[hypo_id] = hypo_verification_counts.get(hypo_id, 0) + 1

        total_hypo_with_verification = len(hypo_verification_counts)
        avg_verification_per_hypothesis = (
            sum(hypo_verification_counts.values()) / total_hypo_with_verification
            if total_hypo_with_verification > 0 else 0.0
        )

        # 待验证假说详情
        verified_hypo_ids = set(r.hypothesis_id for r in verification_records)
        pending_hypotheses = []
        for hypo in all_hypotheses:
            if hypo.id not in verified_hypo_ids:
                pending_hypotheses.append({
                    "id": hypo.id,
                    "statement": hypo.properties.get("statement", ""),
                    "created_at": hypo.created_at
                })

        # 最近完成的闭环（按时间排序）
        recent_cycles = []
        for rec in sorted(verification_records, key=lambda x: x.created_at, reverse=True):
            if rec.outcome in (VerificationOutcome.CONFIRMED, VerificationOutcome.REJECTED):
                recent_cycles.append({
                    "hypothesis_id": rec.hypothesis_id,
                    "outcome": rec.outcome.value,
                    "method": rec.method,
                    "evidence_count": len(rec.evidence),
                    "created_at": rec.created_at
                })
                if len(recent_cycles) >= 5:
                    break

        return {
            "total_hypotheses": total_hypotheses,
            "total_verifications": total_verifications,
            "cycle_completed": cycle_completed,
            "cycle_pending": cycle_pending,
            "confirmed": confirmed_count,
            "rejected": rejected_count,
            "revised": revised_count,
            "inconclusive": inconclusive_count,
            "cycle_completion_rate": round(cycle_completion_rate, 4),
            "hypothesis_pass_rate": round(hypothesis_pass_rate, 4),
            "cycle_success_rate": round(cycle_success_rate, 4),
            "revision_rate": round(revision_rate, 4),
            "avg_verification_per_hypothesis": round(avg_verification_per_hypothesis, 2),
            "pending_hypotheses": pending_hypotheses,
            "recent_cycles": recent_cycles
        }

    async def find_similar_hypotheses(self, statement: str,
                                       embedding: Optional[List[float]] = None) -> List[Dict]:
        """查找相似假说"""
        if embedding:
            results = await self.chroma.find_similar_papers(embedding)
            return [{"id": r[0], "similarity": r[1]} for r in results]
        return []


async def demo():
    """演示发现追踪流程"""
    from hypothesis_generator import HypothesisGenerator, Hypothesis, HypothesisStatus

    tracker = DiscoveryTracker()

    await tracker.track_discovery(
        "disc_001",
        "M42猎户座大星云存在多波段辐射差异",
        source="astronomy"
    )

    hypo = Hypothesis(
        id="hypo_001",
        statement="如果M42存在多波段辐射差异，那么这种差异反映了不同年龄的恒星群体",
        premises=["已有研究显示M42存在温度梯度"],
        predictions=["红外波段强度应与年龄负相关"],
        verification_method="对比WISE红外数据与Chandra X射线数据",
        confidence=0.7,
        status=HypothesisStatus.PENDING.value
    )

    await tracker.track_hypothesis(hypo)
    await tracker.link_derivation("disc_001", "hypo_001")

    await tracker.record_verification(
        hypothesis_id="hypo_001",
        outcome=VerificationOutcome.CONFIRMED,
        evidence=[
            "WISE红外数据显示年轻恒星集中在星云中心",
            "Chandra X射线确认中心区域高温年轻恒星"
        ],
        method="多波段数据对比分析"
    )

    stats = await tracker.get_statistics()
    print(f"统计: {stats}")

    chain = await tracker.get_completion_chain("hypo_001")
    print(f"\n假说链条: {json.dumps(chain, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
