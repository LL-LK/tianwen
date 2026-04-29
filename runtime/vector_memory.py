"""
Hermes-AGI Vector Memory System
向量记忆系统 - 支持语义搜索和相似任务检索
使用ChromaDB作为向量数据库
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from sentence_transformers import SentenceTransformer
import hashlib

# 简单的向量数据库实现（不依赖ChromaDB）
class SimpleVectorStore:
    """简单的向量存储实现 - 基于余弦相似度"""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vectors: List[List[float]] = []
        self.metadata: List[Dict] = []
        self.texts: List[str] = []

    def add(self, text: str, embedding: List[float], metadata: Dict = None):
        """添加向量"""
        self.vectors.append(embedding)
        self.texts.append(text)
        self.metadata.append(metadata or {})

    def search(self, query_embedding: List[float], k: int = 5) -> List[Dict]:
        """搜索相似向量"""
        scores = []
        for i, vec in enumerate(self.vectors):
            score = self._cosine_similarity(query_embedding, vec)
            scores.append((i, score))

        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:k]:
            results.append({
                "text": self.texts[idx],
                "score": float(score),
                "metadata": self.metadata[idx],
            })
        return results

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def count(self) -> int:
        return len(self.vectors)

    def save(self, path: str):
        """保存到文件"""
        data = {
            "dimension": self.dimension,
            "vectors": self.vectors,
            "metadata": self.metadata,
            "texts": self.texts,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self, path: str):
        """从文件加载"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.dimension = data["dimension"]
        self.vectors = data["vectors"]
        self.metadata = data["metadata"]
        self.texts = data["texts"]

# ============ 经验记录 ============

@dataclass
class Experience:
    """经验记录"""
    id: str
    type: str  # 'success' | 'failure' | 'pattern'
    task_description: str
    solution: str
    skills_used: List[str]
    entities: List[Dict] = field(default_factory=list)
    intent: str = ""
    complexity: str = "medium"
    outcome: str = ""  # 'success' | 'partial' | 'failed'
    lessons_learned: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'Experience':
        return Experience(**data)

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
                print(f"[VectorMemory] Loaded {self.experiences_store.count()} experiences")
            except Exception as e:
                print(f"[VectorMemory] Failed to load experiences: {e}")

        if patterns_file.exists():
            try:
                self.patterns_store.load(str(patterns_file))
                print(f"[VectorMemory] Loaded {self.patterns_store.count()} patterns")
            except Exception as e:
                print(f"[VectorMemory] Failed to load patterns: {e}")

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
            print(f"\n[Memory] Found {len(similar)} similar experiences")
            for s in similar[:1]:
                print(f"  - {s['metadata'].get('task_description', 'N/A')[:50]}...")

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

# ============ 示例用法 ============

async def demo():
    """演示向量记忆"""
    print("=" * 50)
    print("Hermes-AGI Vector Memory Demo")
    print("=" * 50)

    memory = VectorMemory(memory_dir="./demo_memory")

    # 添加示例经验
    print("\n添加示例经验...")

    memory.record_success(
        task="创建用户登录的后端API",
        solution="使用JWT认证，实现refresh token机制，密码使用bcrypt加密",
        skills=["Backend", "Security"],
        intent="Execute.Develop.Backend.API",
        complexity="medium"
    )

    memory.record_success(
        task="设计电商系统架构",
        solution="采用微服务架构，使用Redis做缓存，MySQL做主存储",
        skills=["Architecture", "Database"],
        intent="Execute.Analyze.Architecture",
        complexity="high"
    )

    memory.record_failure(
        task="处理高并发秒杀",
        error="库存超卖问题，使用分布式锁解决",
        skills=["Backend", "Database"],
        intent="Execute.Develop.Backend.API"
    )

    # 搜索相似经验
    print("\n搜索相似经验: '用户认证和授权'")
    results = memory.search_similar_experiences("用户认证和授权", k=2)
    for r in results:
        print(f"\n  相似度: {r['score']:.3f}")
        print(f"  任务: {r['metadata'].get('task_description', 'N/A')}")
        print(f"  解决方案: {r['metadata'].get('solution', 'N/A')[:100]}...")

    # 搜索模式
    print("\n搜索模式: '微服务'")
    results = memory.search_patterns("微服务", k=2)
    for r in results:
        print(f"  - {r['metadata'].get('type', 'N/A')}: {r['score']:.3f}")

    # 统计
    print(f"\n统计: {memory.get_stats()}")

    # 清理演示目录
    import shutil
    if Path("./demo_memory").exists():
        shutil.rmtree("./demo_memory")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())