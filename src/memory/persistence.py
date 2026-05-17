"""
Hermes-AGI Memory Persistence System
记忆持久化系统 - 集成向量记忆到Agent主流程
"""
import logging
logger = logging.getLogger(__name__)

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from sentence_transformers import SentenceTransformer
import hashlib
import shutil

# 从统一模块导入向量存储和经验数据模型
from vector_store import SimpleVectorStore
from data_models import SimpleExperience as Experience

# ============ 持久化记忆系统 ============

class PersistentMemory:
    """持久化记忆系统"""

    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 初始化嵌入模型
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedder_loaded = True
        except Exception as e:
            logger.info(f"[Memory] Failed to load embedder: {e}")
            self.embedder = None
            self.embedder_loaded = False

        # 存储路径
        self.experiences_file = self.memory_dir / "experiences.json"
        self.patterns_file = self.memory_dir / "patterns.json"
        self.task_history_file = self.memory_dir / "task_history.json"

        # 初始化向量存储
        self.experiences_store = SimpleVectorStore(dimension=384)
        self.patterns_store = SimpleVectorStore(dimension=384)

        # 内存中的数据
        self.experiences: List[Dict] = []
        self.patterns: List[Dict] = []
        self.task_history: List[Dict] = []

        # 加载数据
        self._load_all()

    def _generate_id(self, content: str) -> str:
        hash_obj = hashlib.md5(content.encode())
        return hash_obj.hexdigest()[:12]

    def _load_all(self):
        """加载所有数据"""
        # 加载 experiences
        if self.experiences_file.exists():
            try:
                with open(self.experiences_file, 'r', encoding='utf-8') as f:
                    self.experiences = json.load(f)
                # 重建向量索引
                if self.embedder_loaded:
                    for exp in self.experiences:
                        text = f"{exp['task_description']} {exp['solution']} {' '.join(exp.get('skills_used', []))}"
                        embedding = self.embedder.encode(text).tolist()
                        self.experiences_store.add(text, embedding, exp)
                logger.info(f"[Memory] Loaded {len(self.experiences)} experiences")
            except Exception as e:
                logger.info(f"[Memory] Failed to load experiences: {e}")

        # 加载 patterns
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    self.patterns = json.load(f)
                if self.embedder_loaded:
                    for pat in self.patterns:
                        text = f"{pat.get('type', '')} {json.dumps(pat)}"
                        embedding = self.embedder.encode(text).tolist()
                        self.patterns_store.add(text, embedding, pat)
                logger.info(f"[Memory] Loaded {len(self.patterns)} patterns")
            except Exception as e:
                logger.info(f"[Memory] Failed to load patterns: {e}")

        # 加载 task history
        if self.task_history_file.exists():
            try:
                with open(self.task_history_file, 'r', encoding='utf-8') as f:
                    self.task_history = json.load(f)
                logger.info(f"[Memory] Loaded {len(self.task_history)} task history records")
            except Exception as e:
                logger.info(f"[Memory] Failed to load task history: {e}")

    def _save_experiences(self):
        """保存经验"""
        with open(self.experiences_file, 'w', encoding='utf-8') as f:
            json.dump(self.experiences, f, ensure_ascii=False, indent=2)
        self.experiences_store.save(str(self.memory_dir / "vector_experiences.json"))

    def _save_patterns(self):
        """保存模式"""
        with open(self.patterns_file, 'w', encoding='utf-8') as f:
            json.dump(self.patterns, f, ensure_ascii=False, indent=2)
        self.patterns_store.save(str(self.memory_dir / "vector_patterns.json"))

    def _save_task_history(self):
        """保存任务历史"""
        with open(self.task_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.task_history, f, ensure_ascii=False, indent=2)

    def _get_embedding(self, text: str) -> List[float]:
        """获取嵌入"""
        if self.embedder_loaded:
            return self.embedder.encode(text).tolist()
        return [0.0] * 384

    # ============ 经验管理 ============

    def add_experience(self, experience: Experience):
        """添加经验"""
        exp_dict = experience.to_dict()
        self.experiences.append(exp_dict)

        # 添加到向量存储
        if self.embedder_loaded:
            text = f"{experience.task_description} {experience.solution} {' '.join(experience.skills_used)}"
            embedding = self._get_embedding(text)
            self.experiences_store.add(text, embedding, exp_dict)

        self._save_experiences()
        logger.info(f"[Memory] Added experience: {experience.id}")

    def record_success(self, task: str, solution: str, skills: List[str], **kwargs) -> Experience:
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

    def record_failure(self, task: str, error: str, skills: List[str], **kwargs) -> Experience:
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

    def search_experiences(self, query: str, k: int = 5) -> List[Dict]:
        """搜索相似经验"""
        if self.embedder_loaded:
            results = self.experiences_store.search(self._get_embedding(query), k=k)
            return [r['metadata'] for r in results]
        else:
            # 简单的文本搜索
            query_lower = query.lower()
            return [e for e in self.experiences if query_lower in e.get('task_description', '').lower()][:k]

    def get_similar_experiences(self, query: str, k: int = 5, min_score: float = 0.5) -> List[Dict]:
        """
        获取语义相似的经验用于任务上下文检索

        Args:
            query: 查询文本（任务描述、问题或需求）
            k: 返回结果数量
            min_score: 最小相似度分数阈值

        Returns:
            List[Dict]: 相似经验列表，包含task_description、solution、skills_used等
        """
        if not self.embedder_loaded:
            logger.info("[Memory] Embedder not loaded, using fallback text search")
            return self.search_experiences(query, k=k)

        query_embedding = self._get_embedding(query)
        results = self.experiences_store.search(query_embedding, k=k * 2)  # 获取更多以便过滤

        # 过滤低分结果并格式化
        similar_experiences = []
        for r in results:
            if r['score'] >= min_score:
                metadata = r['metadata']
                similar_experiences.append({
                    'task_description': metadata.get('task_description', ''),
                    'solution': metadata.get('solution', ''),
                    'skills_used': metadata.get('skills_used', []),
                    'type': metadata.get('type', ''),
                    'outcome': metadata.get('outcome', ''),
                    'score': r['score'],
                    'id': metadata.get('id', ''),
                })

        return similar_experiences[:k]

    # ============ 任务历史管理 ============

    def add_task_record(self, task_record: Dict):
        """添加任务记录"""
        task_record['timestamp'] = datetime.now().isoformat()
        task_record['id'] = task_record.get('id', self._generate_id(str(task_record)))
        self.task_history.append(task_record)

        # 只保留最近1000条记录
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-1000:]

        self._save_task_history()

    def get_task_history(self, limit: int = 50) -> List[Dict]:
        """获取任务历史"""
        return self.task_history[-limit:]

    def get_failed_tasks(self) -> List[Dict]:
        """获取失败任务"""
        return [t for t in self.task_history if t.get('status') == 'failed']

    # ============ 模式管理 ============

    def add_pattern(self, pattern_type: str, pattern_data: Dict):
        """添加模式"""
        pattern = {**pattern_data, "type": pattern_type, "timestamp": datetime.now().isoformat()}
        self.patterns.append(pattern)

        if self.embedder_loaded:
            text = f"{pattern_type} {json.dumps(pattern_data)}"
            embedding = self._get_embedding(text)
            self.patterns_store.add(text, embedding, pattern)

        self._save_patterns()

    def search_patterns(self, query: str, k: int = 5) -> List[Dict]:
        """搜索模式"""
        if self.embedder_loaded:
            results = self.patterns_store.search(self._get_embedding(query), k=k)
            return [r['metadata'] for r in results]
        return []

    # ============ 统计分析 ============

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.task_history)
        successes = sum(1 for t in self.task_history if t.get('status') == 'completed')
        failures = sum(1 for t in self.task_history if t.get('status') == 'failed')

        # 技能使用统计
        skill_counts: Dict[str, int] = {}
        for exp in self.experiences:
            for skill in exp.get('skills_used', []):
                skill_counts[skill] = skill_counts.get(skill, 0) + 1

        return {
            "total_tasks": total,
            "total_experiences": len(self.experiences),
            "total_patterns": len(self.patterns),
            "success_rate": successes / total if total > 0 else 0,
            "success_count": successes,
            "failure_count": failures,
            "top_skills": sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "embedder_loaded": self.embedder_loaded,
        }

    def get_weekly_summary(self) -> Dict:
        """获取每周摘要"""
        now = datetime.now()
        week_ago = datetime.fromordinal(now.toordinal() - 7)
        week_tasks = [t for t in self.task_history if datetime.fromisoformat(t['timestamp']) > week_ago]

        successes = sum(1 for t in week_tasks if t.get('status') == 'completed')
        failures = sum(1 for t in week_tasks if t.get('status') == 'failed')

        return {
            "period": f"{week_ago.date()} to {now.date()}",
            "total_tasks": len(week_tasks),
            "successes": successes,
            "failures": failures,
            "success_rate": successes / len(week_tasks) if week_tasks else 0,
        }

# ============ 记忆集成 ============

class MemoryIntegratedAgent:
    """集成持久化记忆的Agent"""

    def __init__(self, base_agent, memory_dir: str = "./memory"):
        self.base_agent = base_agent
        self.memory = PersistentMemory(memory_dir)

    async def process_with_memory(self, user_input: str) -> Any:
        """带记忆处理的流程"""

        # 1. 搜索相似经验作为上下文
        similar_experiences = self.memory.search_experiences(user_input, k=3)

        # 2. 处理请求
        result = await self.base_agent.process(user_input)

        # 3. 记录任务到历史
        task_record = {
            "task_id": result.task_model.id,
            "description": user_input,
            "intent": result.task_model.type.value,
            "skills": result.task_model.required_skills,
            "status": result.status.value,
            "similar_experiences_used": len(similar_experiences),
        }
        self.memory.add_task_record(task_record)

        # 4. 记录经验
        if result.status.value == "completed":
            self.memory.record_success(
                task=user_input,
                solution=result.output[:500],  # 限制长度
                skills=result.task_model.required_skills,
                intent=result.task_model.type.value,
                complexity=result.task_model.complexity,
            )
        elif result.status.value == "failed":
            self.memory.record_failure(
                task=user_input,
                error=result.errors[0] if result.errors else "Unknown error",
                skills=result.task_model.required_skills,
            )

        # 将相似经验附加到结果
        result.similar_experiences = similar_experiences

        return result

    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        return self.memory.get_stats()

    def get_similar_tasks(self, query: str, k: int = 5) -> List[Dict]:
        """获取相似任务"""
        return self.memory.search_experiences(query, k=k)

    def get_similar_experiences(self, query: str, k: int = 5, min_score: float = 0.5) -> List[Dict]:
        """
        获取语义相似的经验用于任务上下文检索（RAG增强）

        Args:
            query: 查询文本（任务描述、问题或需求）
            k: 返回结果数量
            min_score: 最小相似度分数阈值

        Returns:
            List[Dict]: 相似经验列表，按相似度降序排列
        """
        return self.memory.get_similar_experiences(query, k=k, min_score=min_score)

# ============ 示例用法 ============

async def demo():
    print("=" * 50)
    logger.info("Hermes-AGI Persistent Memory Demo")
    print("=" * 50)

    memory = PersistentMemory(memory_dir="./demo_memory")

    # 添加示例数据
    memory.record_success(
        task="创建用户登录API",
        solution="使用JWT实现Token认证，密码用bcrypt加密",
        skills=["Backend", "Security"],
        intent="Execute.Develop",
        complexity="medium"
    )

    memory.record_failure(
        task="高并发秒杀处理",
        error="库存超卖，添加分布式锁解决",
        skills=["Backend", "Database"],
    )

    memory.add_pattern("caching", {"strategy": "Redis cache", "ttl": "1h"})

    # 搜索
    logger.info("\n搜索相似经验: '用户认证'")
    results = memory.search_experiences("用户认证", k=2)
    for r in results:
        logger.info(f"  - [{r['type']}] {r['task_description'][:50]}... (outcome: {r['outcome']})")

    # 统计
    logger.info(f"\n统计: {json.dumps(memory.get_stats(), indent=2, ensure_ascii=False)}")

    # 清理
    if Path("./demo_memory").exists():
        shutil.rmtree("./demo_memory")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())