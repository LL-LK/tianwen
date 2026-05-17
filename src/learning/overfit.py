"""
Hermes-AGI Overfitting Self-Correction System
基于 RL + GEPA 的过拟合自我纠正机制

功能:
1. 过拟合检测 - 监控思维模式多样性
2. 情景记忆 - GEPA风格的记忆机制
3. RL奖励纠正 - 强化学习驱动的自我优化
4. 多样性保护 - 防止思维模式单一化

Issue #13 增强:
- 与多Agent系统集成
- 过拟合信号跨Agent传播
- 协同纠正机制
"""
import logging
logger = logging.getLogger(__name__)

import math
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from typing import Deque


# ============ 过拟合检测配置 ============

@dataclass
class OverfitConfig:
    """过拟合检测配置"""
    diversity_threshold: float = 0.7      # 多样性阈值 (余弦相似度 > 此值 = 过拟合)
    memory_capacity: int = 1000           # 情景记忆容量
    gradient_projection_margin: float = 0.2  # 梯度投影边界
    rl_discount_factor: float = 0.99       # RL折扣因子
    rl_lr: float = 0.01                   # RL学习率
    overfit_alert_threshold: float = 0.85  # 过拟合警报阈值
    self_correction_strength: float = 0.3  # 自我纠正强度


# ============ 情景记忆 (GEPA风格) ============

@dataclass
class EpisodicEntry:
    """情景记忆条目"""
    task_type: str
    task_complexity: str
    skills_used: List[str]
    thought_pattern: List[float]  # 向量化思维模式
    success: bool
    reward: float
    timestamp: str
    model_source: str = "hermes"  # 记录思维来源 (claude/openclaw/gemini/hermes)


class EpisodicMemory:
    """
    GEPA风格的情景记忆
    - 保留过去任务的关键经验
    - 避免灾难性遗忘
    - 支持梯度投影
    """

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.entries: List[EpisodicEntry] = []
        self.gradient_memory: List[Dict] = []  # 存储历史梯度方向

    def store(self, entry: EpisodicEntry):
        """存储经验到情景记忆"""
        self.entries.append(entry)

        # 容量管理
        if len(self.entries) > self.capacity:
            # 保留最重要的记忆 (成功率高的 + 最近的)
            self._prune_entries()

    def _prune_entries(self):
        """剪枝低价值记忆"""
        # 简单策略: 保留最近的70% + 成功率高的25%
        half = self.capacity // 2
        recent = self.entries[-half:]
        successful = [e for e in self.entries if e.success][:half // 2]
        self.entries = recent + successful

    def get_recent(self, k: int = 50) -> List[EpisodicEntry]:
        """获取最近的k条记忆"""
        return self.entries[-k:]

    def get_by_task_type(self, task_type: str) -> List[EpisodicEntry]:
        """按任务类型检索记忆"""
        return [e for e in self.entries if e.task_type == task_type]

    def compute_gradient_protection(
        self,
        new_gradient: List[float],
        old_params: List[float]
    ) -> List[float]:
        """
        GEPA核心: 梯度投影
        将新梯度投影到不干扰旧知识的方向
        """
        if not self.gradient_memory:
            return new_gradient

        # 计算历史梯度的平均方向
        avg_historical = [
            sum(g[i] for g in self.gradient_memory) / len(self.gradient_memory)
            for i in range(len(new_gradient))
        ]

        # 计算新梯度在历史方向上的投影
        dot_product = sum(n * a for n, a in zip(new_gradient, avg_historical))
        norm_squared = sum(a * a for a in avg_historical) + 1e-8

        # 投影分量
        projection = [avg * (dot_product / norm_squared) for avg in avg_historical]

        # 正交分量 (新梯度的原始部分减去投影)
        orthogonal = [new_gradient[i] - projection[i] for i in range(len(new_gradient))]

        # 混合: 保留正交部分,衰减投影部分 (避免干扰旧知识)
        protected = [
            orthogonal[i] * 0.8 + projection[i] * 0.2
            for i in range(len(new_gradient))
        ]

        return protected

    def record_gradient(self, gradient: List[float]):
        """记录梯度用于后续保护"""
        self.gradient_memory.append(gradient)
        # 保持梯度历史不过长
        if len(self.gradient_memory) > 100:
            self.gradient_memory = self.gradient_memory[-100:]


# ============ 思维多样性检测器 ============

class DiversityGuard:
    """
    确保Hermes不会过度趋同于某一特定思维模式
    监控思维模式多样性,检测过拟合信号
    """

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.thought_history: Deque[List[float]] = deque(maxlen=100)
        self.diversity_scores: Deque[float] = deque(maxlen=50)
        self.overfit_signals: List[str] = []

    def compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1)) + 1e-8
        norm2 = math.sqrt(sum(b * b for b in vec2)) + 1e-8
        return dot / (norm1 * norm2)

    def compute_diversity(self, new_thought: List[float]) -> float:
        """计算新思维与历史的多样性 (1 - avg_similarity)"""
        if len(self.thought_history) < 5:
            return 1.0  # 样本不足时假设多样

        similarities = [
            self.compute_similarity(new_thought, h)
            for h in self.thought_history
        ]
        avg_sim = sum(similarities) / len(similarities)

        diversity = 1.0 - avg_sim
        self.diversity_scores.append(diversity)

        return diversity

    def check_overfit(self, new_thought: List[float]) -> Tuple[bool, float, str]:
        """
        检查是否过拟合
        Returns: (is_overfitting, confidence, reason)
        """
        diversity = self.compute_diversity(new_thought)
        self.thought_history.append(new_thought)

        # 检测信号
        if diversity < self.threshold:
            # 计算连续低多样性次数
            recent_low = sum(1 for d in self.diversity_scores if d < self.threshold)

            if recent_low >= 5:
                return True, 0.9, "连续5次以上思维多样性低于阈值"
            elif recent_low >= 3:
                return True, 0.7, "连续3次以上思维多样性偏低"
            else:
                return True, 0.5, f"当前多样性 {diversity:.2f} 低于阈值 {self.threshold}"

        return False, diversity, "多样性正常"

    def get_overfit_trend(self) -> float:
        """获取过拟合趋势 (0-1, 越高越危险)"""
        if len(self.diversity_scores) < 10:
            return 0.0

        recent = list(self.diversity_scores)[-10:]
        avg = sum(recent) / len(recent)

        # 反转: 低多样性 = 高过拟合趋势
        return max(0.0, 1.0 - avg)


# ============ RL奖励系统 ============

class RLRewardSystem:
    """
    强化学习奖励系统
    - 任务成功 -> 正向奖励
    - 错误率增加 -> 负向奖励
    - 多样性下降 -> 惩罚
    - 过拟合纠正成功 -> 额外奖励
    """

    def __init__(self, config: OverfitConfig):
        self.config = config
        self.reward_history: Deque[float] = deque(maxlen=100)
        self.q_values: Dict[str, float] = {}  # 状态-动作值函数

    def compute_reward(
        self,
        task_success: bool,
        diversity_score: float,
        overfit_corrected: bool,
        response_time: float
    ) -> float:
        """
        综合计算奖励信号

        组成:
        - 任务成功: +1.0
        - 多样性奖励: +diversity_score * 0.5
        - 过拟合纠正成功: +0.5
        - 响应时间惩罚: -0.1 if response_time > 60s
        """
        reward = 0.0

        # 基础成功奖励
        if task_success:
            reward += 1.0
        else:
            reward -= 0.5

        # 多样性奖励 (高多样性 = 高奖励)
        reward += diversity_score * 0.5

        # 过拟合纠正奖励
        if overfit_corrected:
            reward += 0.5

        # 时间惩罚
        if response_time > 60:
            reward -= 0.1

        self.reward_history.append(reward)
        return reward

    def update_q_value(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str
    ):
        """
        Q-learning更新
        Q(s,a) = Q(s,a) + lr * (r + gamma * max_a' Q(s',a') - Q(s,a))
        """
        if state not in self.q_values:
            self.q_values[state] = 0.0

        if next_state not in self.q_values:
            self.q_values[next_state] = 0.0

        lr = self.config.rl_lr
        gamma = self.config.rl_discount_factor

        current_q = self.q_values[state]
        next_max_q = max(self.q_values.get(a, 0.0) for a in ["correct", "preserve", "explore"])

        new_q = current_q + lr * (reward + gamma * next_max_q - current_q)
        self.q_values[state] = new_q

    def get_best_action(self, state: str) -> str:
        """根据当前状态选择最佳动作"""
        actions = ["correct", "preserve", "explore"]
        q_scores = {a: self.q_values.get(f"{state}_{a}", 0.0) for a in actions}
        return max(q_scores, key=q_scores.get)


# ============ 过拟合自我纠正器 (核心) ============

class OverfittingSelfCorrector:
    """
    过拟合自我纠正器
    结合 RL + GEPA 实现迭代自我纠正

    Issue #13 增强:
    - 跨Agent过拟合信号传播
    - 多Agent协同纠正
    - 分布式过拟合检测
    """

    def __init__(self, config: Optional[OverfitConfig] = None):
        self.config = config or OverfitConfig()
        self.episodic_memory = EpisodicMemory(capacity=self.config.memory_capacity)
        self.diversity_guard = DiversityGuard(threshold=self.config.diversity_threshold)
        self.rl_system = RLRewardSystem(self.config)

        self.correction_count = 0
        self.overfit_alerts = 0

        # Issue #13: 多Agent集成
        self.collaborative_callbacks: List[Callable] = []
        self.agent_overfit_states: Dict[str, Dict] = {}  # 记录各Agent的过拟合状态

    def register_collaborative_callback(self, callback: Callable[[Dict], None]):
        """注册协作回调 - 用于多Agent系统通知"""
        self.collaborative_callbacks.append(callback)

    async def notify_other_agents(self, agent_id: str, overfit_state: Dict):
        """
        通知其他Agents过拟合状态

        Issue #13: 实现跨Agent的过拟合信号传播

        Args:
            agent_id: 当前Agent ID
            overfit_state: 过拟合状态
        """
        self.agent_overfit_states[agent_id] = overfit_state

        for callback in self.collaborative_callbacks:
            try:
                callback({
                    "source_agent": agent_id,
                    "overfit_state": overfit_state,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.info(f"[OverfitCorrection] 回调错误: {e}")

    def get_cross_agent_overfit_report(self) -> Dict[str, Any]:
        """
        获取跨Agent过拟合报告

        Issue #13: 多Agent协同的过拟合检测

        Returns:
            包含各Agent过拟合状态的报告
        """
        if not self.agent_overfit_states:
            return {"status": "no_data", "agents": {}}

        avg_trend = sum(
            s.get("overfit_trend", 0)
            for s in self.agent_overfit_states.values()
        ) / len(self.agent_overfit_states)

        return {
            "status": "monitored",
            "agents": self.agent_overfit_states,
            "avg_overfit_trend": avg_trend,
            "critical_agents": [
                agent_id for agent_id, state in self.agent_overfit_states.items()
                if state.get("overfit_trend", 0) > 0.7
            ]
        }

    def on_task_complete(
        self,
        task_result: Dict,
        thought_vector: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        任务完成后的过拟合检测与纠正

        Args:
            task_result: 任务结果
            thought_vector: 思维模式向量 (可选)

        Returns:
            Dict containing:
            - corrected: 是否进行了纠正
            - reward: 奖励信号
            - diversity: 多样性得分
            - overfit_detected: 是否检测到过拟合
            - suggestion: 纠正建议
        """
        task_id = task_result.get("task_id", "unknown")
        success = task_result.get("success", False)
        task_type = task_result.get("task_type", "general")
        complexity = task_result.get("complexity", "medium")

        # 如果没有思维向量,从任务结果构建
        if thought_vector is None:
            thought_vector = self._build_thought_vector(task_result)

        # Step 1: 过拟合检测
        is_overfit, confidence, reason = self.diversity_guard.check_overfit(thought_vector)

        # Step 2: 计算多样性得分
        diversity = 1.0 - confidence if confidence > 1.0 else self.diversity_guard.compute_diversity(thought_vector)

        # Step 3: 存储到情景记忆
        entry = EpisodicEntry(
            task_type=task_type,
            task_complexity=complexity,
            skills_used=task_result.get("skills", []),
            thought_pattern=thought_vector,
            success=success,
            reward=0.0,  # 待计算
            timestamp=datetime.now().isoformat(),
            model_source="hermes"
        )
        self.episodic_memory.store(entry)

        # Step 4: 计算奖励
        reward = self.rl_system.compute_reward(
            task_success=success,
            diversity_score=diversity,
            overfit_corrected=is_overfit,
            response_time=task_result.get("duration", 0)
        )

        # 更新entry的reward
        if self.episodic_memory.entries:
            self.episodic_memory.entries[-1].reward = reward

        # Step 5: 如果检测到过拟合,执行纠正
        corrected = False
        suggestion = ""

        if is_overfit:
            self.overfit_alerts += 1
            suggestion = self._generate_correction_suggestion(task_result, diversity)

            # 如果需要纠正,更新RL系统
            if confidence > self.config.overfit_alert_threshold:
                corrected = True
                self.correction_count += 1

                # RL: 记录纠正状态
                state = f"overfit_{task_type}"
                action = "correct"
                self.rl_system.update_q_value(state, action, reward, f"post_correct_{task_type}")

        # 记录梯度 (用于GEPA投影)
        gradient = self._estimate_gradient(thought_vector, reward)
        self.episodic_memory.record_gradient(gradient)

        return {
            "task_id": task_id,
            "corrected": corrected,
            "reward": reward,
            "diversity": diversity,
            "overfit_detected": is_overfit,
            "overfit_confidence": confidence,
            "overfit_reason": reason,
            "suggestion": suggestion,
            "correction_count": self.correction_count,
            "overfit_alerts": self.overfit_alerts
        }

    def _build_thought_vector(self, task_result: Dict) -> List[float]:
        """从任务结果构建思维向量"""
        # 简化的思维向量: [task_type_hash, complexity_hash, success_flag, skill_count]
        task_type = task_result.get("task_type", "general")
        complexity = task_result.get("complexity", "medium")

        # 简单的哈希映射
        type_val = hash(task_type) % 100 / 100.0
        complexity_val = {"low": 0.3, "medium": 0.6, "high": 0.9}.get(complexity, 0.5)
        success_val = 1.0 if task_result.get("success") else 0.0
        skill_count = len(task_result.get("skills", [])) / 10.0

        return [type_val, complexity_val, success_val, skill_count]

    def _estimate_gradient(self, thought: List[float], reward: float) -> List[float]:
        """估计梯度方向"""
        # 简化: 梯度方向与思维向量成比例,强度与奖励相关
        scale = reward * 0.1
        return [t * scale for t in thought]

    def _generate_correction_suggestion(self, task_result: Dict, diversity: float) -> str:
        """生成纠正建议"""
        suggestions = []

        if diversity < 0.3:
            suggestions.append("严重过拟合: 思维模式高度重复,建议切换到探索模式")
        elif diversity < 0.5:
            suggestions.append("中度过拟合: 尝试不同的技能组合或任务分解策略")

        # 根据任务类型建议
        task_type = task_result.get("task_type", "general")
        if task_type == "execute":
            suggestions.append("执行类任务: 考虑并行化子任务,避免串行思维")
        elif task_type == "learn":
            suggestions.append("学习类任务: 引入多源信息,避免单一模型思维")

        # 技能多样性建议
        skills = task_result.get("skills", [])
        if len(set(skills)) < 2:
            suggestions.append("技能组合单一: 建议引入更多技能进行协作")

        return "; ".join(suggestions) if suggestions else "保持当前策略"

    def get_overfitting_report(self) -> Dict:
        """获取过拟合状态报告"""
        trend = self.diversity_guard.get_overfit_trend()

        return {
            "total_corrections": self.correction_count,
            "overfit_alerts": self.overfit_alerts,
            "overfit_trend": trend,
            "memory_size": len(self.episodic_memory.entries),
            "gradient_memory_size": len(self.episodic_memory.gradient_memory),
            "rl_q_values_count": len(self.rl_system.q_values),
            "status": "CRITICAL" if trend > 0.8 else "WARNING" if trend > 0.5 else "NORMAL"
        }


# ============ 集成到现有系统 ============

class SelfEvolutionWithOverfitCorrection:
    """
    增强版自我进化系统,集成过拟合自我纠正
    替代原有的 EvolutionSystem
    """

    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = memory_dir
        self.overfit_corrector = OverfittingSelfCorrector()

        # 保留原有的任务历史
        self.task_history: List[Dict] = []
        self.patterns: List[Dict] = []

    def after_task(self, result) -> Dict[str, Any]:
        """
        任务完成后的钩子,整合过拟合检测与纠正

        Returns:
            过拟合检测结果
        """
        # 记录任务执行
        self._record_task(result)

        # 构建任务结果字典
        task_result = {
            "task_id": result.task_model.id,
            "success": result.status.value == "completed",
            "task_type": result.task_model.type.value,
            "complexity": result.task_model.complexity,
            "skills": result.task_model.required_skills,
            "duration": result.metrics.get("duration", 0),
            "error": str(result.errors) if result.errors else ""
        }

        # 调用过拟合检测与纠正
        overfit_result = self.overfit_corrector.on_task_complete(task_result)

        # 提取模式 (原有逻辑)
        if result.status.value == "completed":
            self._extract_success_pattern(result)
        else:
            self._analyze_failure(result)

        return overfit_result

    def _record_task(self, result):
        """记录任务"""
        record = {
            'date': datetime.now().isoformat(),
            'task_id': result.task_model.id,
            'type': result.task_model.type.value,
            'skills': result.task_model.required_skills,
            'status': result.status.value,
            'duration': result.metrics.get('duration', 0),
            'subtask_count': len(result.plan.subtasks),
        }
        self.task_history.append(record)

    def _extract_success_pattern(self, result):
        """提取成功模式"""
        pattern = {
            'type': 'success',
            'intent': result.task_model.type.value,
            'skills': result.task_model.required_skills,
            'complexity': result.task_model.complexity,
            'subtask_count': len(result.plan.subtasks),
        }
        self.patterns.append(pattern)

    def _analyze_failure(self, result):
        """分析失败原因"""
        for error in result.errors:
            logger.error(f"[Evolution] 失败分析: {error}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.task_history)
        if total == 0:
            return {'total_tasks': 0, 'success_rate': 0}

        successes = sum(1 for r in self.task_history if r['status'] == 'completed')
        overfit_report = self.overfit_corrector.get_overfitting_report()

        return {
            'total_tasks': total,
            'success_rate': successes / total,
            'patterns_count': len(self.patterns),
            'overfitting': overfit_report
        }


# ============ 使用示例 ============

def demo():
    """演示过拟合自我纠正系统"""
    logger.debug("=" * 60)
    logger.info("Hermes-AGI Overfitting Self-Correction Demo")
    logger.debug("=" * 60)

    # 创建增强版自我进化系统
    evolution = SelfEvolutionWithOverfitCorrection(memory_dir="./demo_memory")

    # 模拟任务执行
    test_tasks = [
        # 正常任务
        {
            "task_id": "TASK-001",
            "success": True,
            "task_type": "execute",
            "complexity": "medium",
            "skills": ["Frontend", "Backend"],
            "duration": 30.0
        },
        # 另一个正常任务
        {
            "task_id": "TASK-002",
            "success": True,
            "task_type": "query",
            "complexity": "low",
            "skills": ["Database"],
            "duration": 15.0
        },
        # 失败的复杂任务
        {
            "task_id": "TASK-003",
            "success": False,
            "task_type": "execute",
            "complexity": "high",
            "skills": ["Architecture"],
            "duration": 120.0
        },
    ]

    logger.info("\n[1] 执行过拟合检测演示:")
    for task in test_tasks:
        result = evolution.after_task({
            "task_model": type('obj', (), {
                "id": task["task_id"],
                "type": type('obj', (), {"value": task["task_type"]})(),
                "complexity": task["complexity"],
                "required_skills": task["skills"]
            })(),
            "status": type('obj', (), {"value": "completed" if task["success"] else "failed"})(),
            "metrics": {"duration": task["duration"]},
            "errors": [] if task["success"] else ["Task failed"]
        })

        logger.info(f"\n  Task: {task['task_id']}")
        logger.info(f"    - Overfit Detected: {result['overfit_detected']}")
        logger.info(f"    - Diversity: {result['diversity']:.3f}")
        logger.info(f"    - Reward: {result['reward']:.3f}")
        if result['suggestion']:
            logger.info(f"    - Suggestion: {result['suggestion']}")

    # 显示整体报告
    logger.info("\n[2] 过拟合状态报告:")
    stats = evolution.get_stats()
    logger.info(f"  Total Tasks: {stats['total_tasks']}")
    logger.info(f"  Success Rate: {stats['success_rate']*100:.1f}%")
    logger.info(f"  Overfitting Status: {stats['overfitting']['status']}")
    logger.info(f"  Total Corrections: {stats['overfitting']['total_corrections']}")
    logger.info(f"  Overfit Trend: {stats['overfitting']['overfit_trend']:.3f}")

    logger.debug("\n" + "=" * 60)
    logger.info("Demo Complete")
    logger.debug("=" * 60)


if __name__ == "__main__":
    demo()