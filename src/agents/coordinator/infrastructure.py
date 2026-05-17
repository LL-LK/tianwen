"""
基础设施类 (G3组) - 提取自 coordinator.py

包含:
- ScriptLibrary: 剧本库管理
- IterativeLearning: 迭代学习机制
- ConflictResolver: 冲突解决器
- SafetyCoordinator: 安全协调器

Author: Tianwen-AGI Team
Date: 2026/05/16
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import numpy as np

from .types_enums import ConflictType, Conflict, Script, PerformanceFeedback

logger = logging.getLogger(__name__)


# ============================================================================
# ScriptLibrary - 剧本库管理
# ============================================================================

class ScriptLibrary:
    """
    剧本库 - 管理所有剧本 (Issue #36)

    功能:
    - 剧本注册和查找
    - 剧本进化 (从演出反馈学习)
    - 自动生成新剧本
    """

    def __init__(self):
        self.scripts: Dict[str, Script] = {}
        self.feedback_history: List[PerformanceFeedback] = []

    def add_script(self, script: Script):
        """注册新剧本"""
        self.scripts[script.name] = script

    def get_script(self, name: str) -> Optional[Script]:
        """获取剧本"""
        return self.scripts.get(name)

    def learn_from_feedback(self, feedback: PerformanceFeedback):
        """
        从演出反馈学习 (举一反三)

        1. 更新对应剧本的成功率
        2. 收集改进提示
        3. 检测新模式用于生成新剧本
        """
        self.feedback_history.append(feedback)

        script = self.scripts.get(feedback.script_name)
        if script:
            script.increment_performance(feedback.success)
            for suggestion in feedback.suggestions:
                script.add_improvement_hint(suggestion)

        # 检测新模式 (举一反三)
        if feedback.observations:
            self._detect_novel_pattern(feedback)

    def _detect_novel_pattern(self, feedback: PerformanceFeedback) -> bool:
        """检测新模式用于剧本生成"""
        # 如果收集到足够观察，可能生成新剧本
        if len(feedback.observations) >= 5:
            # 这里简化处理，实际应该用更复杂的模式识别
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取剧本库统计"""
        total_performances = sum(s.performance_count for s in self.scripts.values())
        avg_success_rate = (
            sum(s.success_rate for s in self.scripts.values()) / len(self.scripts)
            if self.scripts else 0
        )
        return {
            "total_scripts": len(self.scripts),
            "total_performances": total_performances,
            "average_success_rate": avg_success_rate,
            "feedback_count": len(self.feedback_history)
        }


# ============================================================================
# IterativeLearning - 迭代学习机制
# ============================================================================

class IterativeLearning:
    """
    迭代学习机制 (Issue #36)

    两种学习模式:
    1. 孰能生巧: 单一任务越做越好
    2. 举一反三: 学会一类任务的通用方法

    学习维度:
    - skill_improvement: 技能提升
    - pattern_generalization: 模式泛化
    - script_optimization: 剧本优化
    """

    def __init__(self):
        self.skill_library: Dict[str, Dict] = {}  # task_type -> skill_data
        self.pattern_cache: Dict[str, Any] = {}    # pattern -> generalized_method
        self.learning_history: List[Dict] = []

    def on_task_complete(
        self,
        task_type: str,
        result: Dict[str, Any],
        context: Optional[Dict] = None
    ):
        """
        任务完成后的学习

        1. 孰能生巧 - 更新此类任务的专用技能
        2. 举一反三 - 提取通用模式
        """
        # 1. 孰能生巧 - 更新技能
        self._update_skill(task_type, result)

        # 2. 举一反三 - 提取模式
        if context:
            general_pattern = self._extract_pattern(task_type, context)
            if general_pattern:
                self._add_to_skill_library(task_type, general_pattern)

        # 记录学习历史
        self.learning_history.append({
            "task_type": task_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

    def _update_skill(self, task_type: str, result: Dict[str, Any]):
        """更新技能 (孰能生巧)"""
        if task_type not in self.skill_library:
            self.skill_library[task_type] = {
                "count": 0,
                "success_rate": 0.0,
                "avg_quality": 0.0,
                "best_practices": []
            }

        skill = self.skill_library[task_type]
        skill["count"] += 1

        # 更新成功率
        success = result.get("success", False)
        prev_successes = skill["success_rate"] * (skill["count"] - 1)
        if success:
            prev_successes += 1
        skill["success_rate"] = prev_successes / skill["count"]

        # 更新质量
        quality = result.get("quality", 0.0)
        if quality > 0:
            prev_quality_sum = skill["avg_quality"] * (skill["count"] - 1)
            skill["avg_quality"] = (prev_quality_sum + quality) / skill["count"]

        # 记录最佳实践
        if result.get("best_practice"):
            skill["best_practices"].append(result["best_practice"])
            # 只保留最近10个最佳实践
            skill["best_practices"] = skill["best_practices"][-10:]

    def _extract_pattern(self, task_type: str, context: Dict) -> Optional[Dict]:
        """提取通用模式 (举一反三)"""
        # 简化实现：检查是否有足够样本
        skill = self.skill_library.get(task_type, {})
        if skill.get("count", 0) >= 3:
            # 样本足够，尝试提取模式
            return {
                "task_type": task_type,
                "common_steps": context.get("steps", []),
                "key_decisions": context.get("decisions", []),
                "success_factors": context.get("factors", [])
            }
        return None

    def _add_to_skill_library(self, task_type: str, pattern: Dict):
        """添加到技能库"""
        self.pattern_cache[task_type] = pattern

    def get_skill(self, task_type: str) -> Optional[Dict]:
        """获取技能"""
        return self.skill_library.get(task_type)

    def get_best_practice(self, task_type: str) -> Optional[str]:
        """获取最佳实践"""
        skill = self.skill_library.get(task_type)
        if skill and skill["best_practices"]:
            return skill["best_practices"][-1]  # 返回最新的最佳实践
        return None

    def suggest_improvement(self, task_type: str) -> List[str]:
        """建议改进 (基于学习历史)"""
        skill = self.skill_library.get(task_type, {})
        suggestions = []

        if skill.get("success_rate", 1.0) < 0.7:
            suggestions.append("成功率较低，建议复习最佳实践")

        if skill.get("count", 0) < 5:
            suggestions.append("样本不足，建议多加练习 (孰能生巧)")

        if not skill.get("best_practices"):
            suggestions.append("缺乏最佳实践记录，建议总结经验")

        return suggestions

    def get_statistics(self) -> Dict[str, Any]:
        """获取学习统计"""
        return {
            "total_task_types": len(self.skill_library),
            "total_patterns": len(self.pattern_cache),
            "learning_events": len(self.learning_history),
            "most_practiced": max(
                self.skill_library.items(),
                key=lambda x: x[1].get("count", 0)
            )[0] if self.skill_library else None
        }


# ============================================================================
# ConflictResolver - 冲突解决器
# ============================================================================

class ConflictResolver:
    """
    冲突解决器

    策略:
    1. 优先级裁决: 高优先级Agent的意见优先
    2. 共识机制: 多数投票
    3. 专家裁决: 相关领域专家决定
    4. 妥协方案: 综合各方意见

    使用示例:
        resolver = ConflictResolver(coordinator)
        conflict = resolver.detect_conflict(agent1.id, agent2.id, "研究方法选择")
        resolution = await resolver.resolve_conflict(conflict, strategy="consensus")
    """

    def __init__(self, coordinator: MultiAgentCoordinator = None):
        """
        初始化冲突解决器

        参数:
            coordinator: MultiAgentCoordinator实例 (延迟导入，可为None)
        """
        # 延迟导入避免循环依赖
        from .coordinator import MultiAgentCoordinator
        self._coordinator = coordinator
        self.conflict_history: List[Conflict] = []
        self.active_conflicts: List[Conflict] = []

    @property
    def coordinator(self) -> MultiAgentCoordinator:
        """延迟加载coordinator"""
        if self._coordinator is None:
            from .coordinator import MultiAgentCoordinator
            self._coordinator = MultiAgentCoordinator()
        return self._coordinator

    @coordinator.setter
    def coordinator(self, value: MultiAgentCoordinator):
        self._coordinator = value

    def detect_conflict(
        self,
        agent1_id: str,
        agent2_id: str,
        issue: str,
        conflict_type: ConflictType = ConflictType.METHOD_CONFLICT,
        historical_agreement: Optional[float] = None
    ) -> Optional[Conflict]:
        """
        检测冲突

        Args:
            agent1_id: 第一个Agent的ID
            agent2_id: 第二个Agent的ID
            issue: 冲突问题描述
            conflict_type: 冲突类型
            historical_agreement: 历史一致性分数 (0-1, 来自跨验证)

        返回:
            Conflict对象, 如果未检测到冲突返回None
        """
        # 检查两个Agent是否都存在
        agent1 = self.coordinator.agents.get(agent1_id)
        agent2 = self.coordinator.agents.get(agent2_id)

        if not agent1 or not agent2:
            return None

        # 计算冲突概率 (基于历史一致性)
        if historical_agreement is not None:
            # 使用历史一致性计算冲突概率
            conflict_probability = 1 - historical_agreement
        else:
            # 基于Agent专业领域重叠度估计冲突概率
            expertise1 = set(agent1.expertise)
            expertise2 = set(agent2.expertise)
            overlap = len(expertise1 & expertise2)
            total = len(expertise1 | expertise2)
            similarity = overlap / total if total > 0 else 0.5

            # 相似度高但结论不同 = 高冲突概率
            conflict_probability = max(0.1, min(0.8, 1 - similarity))

        # 基于冲突概率决定是否检测到冲突
        if np.random.random() < conflict_probability:
            conflict = Conflict(
                conflict_type=conflict_type,
                involved_agents=[agent1_id, agent2_id],
                description=issue
            )

            self.conflict_history.append(conflict)
            self.active_conflicts.append(conflict)

            # 通知涉及的Agent
            for aid in [agent1_id, agent2_id]:
                agent = self.coordinator.agents.get(aid)
                if agent:
                    agent.add_message(
                        "system",
                        f"检测到冲突: {issue}",
                        metadata={"conflict_id": conflict.conflict_id, "type": "conflict_detected"}
                    )

            return conflict

        return None

    def get_active_conflicts(self) -> List[Conflict]:
        """获取所有活跃冲突"""
        return [c for c in self.active_conflicts if not c.resolved]

    def get_conflict_by_id(self, conflict_id: str) -> Optional[Conflict]:
        """根据ID获取冲突"""
        for conflict in self.conflict_history:
            if conflict.conflict_id == conflict_id:
                return conflict
        return None

    async def resolve_conflict(
        self,
        conflict: Conflict,
        strategy: str = "consensus"
    ) -> str:
        """
        解决冲突

        参数:
            conflict: Conflict对象
            strategy: 解决策略
                - "priority": 优先级裁决
                - "consensus": 共识机制 (多数投票)
                - "expert": 专家裁决
                - "compromise": 妥协方案

        返回:
            解决方案描述字符串
        """
        agents = {
            aid: self.coordinator.agents.get(aid)
            for aid in conflict.involved_agents
        }

        # 过滤掉不存在的Agent
        agents = {aid: agent for aid, agent in agents.items() if agent}

        if not agents:
            return "无法解决冲突: 涉及的Agent不存在"

        resolution = ""

        if strategy == "priority":
            # 优先级裁决
            # 角色优先级: COORDINATOR > PLANNER > REVIEWER > others
            role_priority = {
                AgentRole.COORDINATOR: 7,
                AgentRole.PLANNER: 6,
                AgentRole.REVIEWER: 5,
                AgentRole.EXECUTOR: 4,
                AgentRole.RESEARCHER: 4,
                AgentRole.HYPOTHESIS_GENERATOR: 4,
                AgentRole.OBSERVATION_SPECIALIST: 4
            }

            winner_id = max(
                agents.keys(),
                key=lambda aid: role_priority.get(agents[aid].role, 0)
            )

            resolution = f"优先级裁决: 采纳{agents[winner_id].name}的方案"

        elif strategy == "consensus":
            # 共识机制 - 多数投票 (模拟)
            votes = {aid: 0 for aid in agents.keys()}

            # 模拟3轮投票
            for round_num in range(3):
                # 每轮随机投票给某个Agent
                for voter_id in agents.keys():
                    # 随机选择被投票者 (倾向于自己观点一致的)
                    choice = max(agents.keys(), key=lambda k: abs(hash(k + str(round_num))) % 5)
                    if choice in votes:
                        votes[choice] += 1

            consensus_id = max(votes.keys(), key=lambda k: votes[k])
            resolution = f"共识决定: 采纳{agents[consensus_id].name}的方案 (票数: {votes[consensus_id]})"

        elif strategy == "expert":
            # 专家裁决 - 选择最相关的专家
            expert_id = self._select_expert(conflict)
            if expert_id and expert_id in agents:
                resolution = f"专家裁决: 采纳{agents[expert_id].name}的方案"
            else:
                resolution = "专家裁决: 无法确定专家, 采用妥协方案"

        else:  # compromise
            # 妥协方案 - 综合各方意见
            all_expertise = []
            for agent in agents.values():
                all_expertise.extend(agent.expertise)

            expertise_count = {}
            for exp in all_expertise:
                expertise_count[exp] = expertise_count.get(exp, 0) + 1

            common_expertise = sorted(expertise_count.items(), key=lambda x: x[1], reverse=True)

            resolution = f"妥协方案: 综合{len(agents)}个Agent的意见, 涉及领域: {', '.join([e[0] for e in common_expertise[:3]])}"

        # 更新冲突状态
        conflict.resolved = True
        conflict.resolution = resolution

        # 从活跃冲突中移除
        if conflict in self.active_conflicts:
            self.active_conflicts.remove(conflict)

        # 通知涉及的Agent
        for aid in conflict.involved_agents:
            agent = self.coordinator.agents.get(aid)
            if agent:
                agent.add_message(
                    "system",
                    f"冲突已解决: {resolution}",
                    metadata={"conflict_id": conflict.conflict_id, "type": "conflict_resolved"}
                )

        return resolution

    def _select_expert(self, conflict: Conflict) -> str:
        """
        选择最相关的专家

        参数:
            conflict: Conflict对象

        返回:
            专家Agent的ID, 如果没有找到返回空字符串
        """
        # 获取所有Agent的专业领域
        agent_expertise = {
            aid: set(agent.expertise)
            for aid, agent in self.coordinator.agents.items()
        }

        # 分析冲突类型对应的专业领域
        relevant_expertise = set()
        for expertise_list in agent_expertise.values():
            relevant_expertise.update(expertise_list)

        # 计算每个Agent的相关度
        agent_relevance = {}
        for aid, expertise in agent_expertise.items():
            # 计算与相关领域的交集大小
            relevance = len(expertise & relevant_expertise)
            agent_relevance[aid] = relevance

        # 选择相关度最高的Agent
        if agent_relevance:
            return max(agent_relevance.keys(), key=lambda k: agent_relevance[k])

        return ""

    def add_proposed_resolution(self, conflict: Conflict, resolution: str):
        """为冲突添加提议的解决方案"""
        if conflict.conflict_id not in [c.conflict_id for c in self.active_conflicts]:
            return

        conflict.proposed_resolutions.append(resolution)

    def get_conflict_statistics(self) -> Dict[str, Any]:
        """获取冲突解决统计信息"""
        resolved_count = len([c for c in self.conflict_history if c.resolved])
        unresolved_count = len(self.active_conflicts)

        type_stats = {}
        for ct in ConflictType:
            count = len([c for c in self.conflict_history if c.conflict_type == ct])
            type_stats[ct.value] = count

        return {
            "total_conflicts": len(self.conflict_history),
            "resolved": resolved_count,
            "unresolved": unresolved_count,
            "by_type": type_stats
        }

    def estimate_consensus_confidence(
        self,
        agent_ids: List[str],
        decision_topic: str
    ) -> Dict[str, Any]:
        """
        估计共识决策的置信度

        Args:
            agent_ids: 参与的Agent ID列表
            decision_topic: 决策主题

        Returns:
            Dict containing:
            - estimated_confidence: 估计置信度 (0-1)
            - agreement_probability: 同意概率
            - confidence_interval: (lower, upper) 置信区间
            - factors: 影响置信度的因素
        """
        agents = [self.coordinator.agents.get(aid) for aid in agent_ids if self.coordinator.agents.get(aid)]

        if len(agents) < 2:
            return {
                "estimated_confidence": 0.5,
                "agreement_probability": 0.5,
                "confidence_interval": (0.3, 0.7),
                "factors": ["Agent数量不足"]
            }

        # 因素1: Agent专业领域的重叠度
        expertise_sets = [set(a.expertise) for a in agents]
        overlap_count = len(set.intersection(*expertise_sets)) if expertise_sets else 0
        total_count = len(set.union(*expertise_sets)) if expertise_sets else 1
        expertise_overlap = overlap_count / total_count if total_count > 0 else 0.5

        # 因素2: 历史一致性 (如果有历史记录)
        historical_agreement = self._calculate_historical_agreement(agent_ids)

        # 因素3: Agent角色一致性
        roles = [a.role for a in agents]
        role_consistency = len(set(roles)) / len(roles)  # 角色越多样化，可能越难达成共识

        # 计算估计置信度
        base_confidence = 0.5
        estimated_confidence = (
            base_confidence +
            expertise_overlap * 0.3 +
            historical_agreement * 0.2 -
            role_consistency * 0.1
        )
        estimated_confidence = max(0.1, min(0.95, estimated_confidence))

        # 估计同意概率
        agreement_probability = estimated_confidence

        # 计算置信区间 (模拟多次采样)
        n_samples = 100
        samples = []
        for _ in range(n_samples):
            # 添加扰动
            perturbed = estimated_confidence + np.random.normal(0, 0.1)
            perturbed = max(0, min(1, perturbed))
            samples.append(perturbed)

        samples = np.array(samples)
        ci_lower = np.percentile(samples, 2.5)
        ci_upper = np.percentile(samples, 97.5)

        # 因素列表
        factors = []
        if expertise_overlap > 0.5:
            factors.append("专业领域高度重叠 (+0.2)")
        elif expertise_overlap < 0.2:
            factors.append("专业领域重叠低 (-0.1)")

        if historical_agreement > 0.7:
            factors.append("历史一致性高 (+0.15)")
        elif historical_agreement < 0.4:
            factors.append("历史一致性低 (-0.1)")

        if role_consistency > 0.7:
            factors.append("角色多样性高 (-0.05)")

        return {
            "estimated_confidence": round(estimated_confidence, 3),
            "agreement_probability": round(agreement_probability, 3),
            "confidence_interval": (round(ci_lower, 3), round(ci_upper, 3)),
            "factors": factors,
            "expertise_overlap": round(expertise_overlap, 3),
            "historical_agreement": round(historical_agreement, 3)
        }

    def _calculate_historical_agreement(self, agent_ids: List[str]) -> float:
        """计算Agent间的历史一致性"""
        # 获取这些Agent的历史对话
        conversations = []
        for agent in self.coordinator.agents.values():
            if agent.id in agent_ids:
                conversations.extend(agent.conversation_history)

        if len(conversations) < 5:
            return 0.6  # 默认中等一致性

        # 检查历史消息的一致性 (简单模拟)
        # 实际应该检查决策结果的一致性
        return 0.7  # 模拟值

    async def resolve_conflict_with_confidence(
        self,
        conflict: Conflict,
        strategy: str = "consensus"
    ) -> Dict[str, Any]:
        """
        解决冲突并返回置信度信息

        Returns:
            Dict containing resolution and confidence metrics
        """
        # 首先估计共识置信度
        consensus_confidence = self.estimate_consensus_confidence(
            conflict.involved_agents,
            conflict.description
        )

        # 执行冲突解决
        resolution = await self.resolve_conflict(conflict, strategy)

        return {
            "conflict_id": conflict.conflict_id,
            "resolution": resolution,
            "consensus_confidence": consensus_confidence["estimated_confidence"],
            "agreement_probability": consensus_confidence["agreement_probability"],
            "confidence_interval": consensus_confidence["confidence_interval"],
            "resolution_strategy": strategy
        }


# ============================================================================
# SafetyCoordinator - 安全协调器
# ============================================================================

class SafetyCoordinator:
    """
    多Agent安全协调器

    功能:
    - 协调多个Agent的安全操作
    - 维护全局安全状态
    - 紧急停止机制
    """

    def __init__(self):
        self.global_safety_state: Dict[str, Any] = {
            "emergency_stop": False,
            "max_velocity": 1.0,
            "restricted_regions": []
        }
        self.agent_safety_states: Dict[str, bool] = {}

    async def check_agent_operation(
        self,
        agent_id: str,
        operation: str,
        context: Dict
    ) -> bool:
        """
        检查Agent操作是否安全

        Args:
            agent_id: Agent ID
            operation: 操作名称
            context: 操作上下文

        Returns:
            是否允许操作
        """
        if self.global_safety_state["emergency_stop"]:
            return False

        # 检查速度限制
        if "velocity" in context:
            if context["velocity"] > self.global_safety_state["max_velocity"]:
                return False

        # 检查限制区域
        position = context.get("position", {})
        for region in self.global_safety_state["restricted_regions"]:
            if self._is_in_region(position, region):
                return False

        self.agent_safety_states[agent_id] = True
        return True

    def _is_in_region(
        self,
        position: Dict[str, float],
        region: Dict
    ) -> bool:
        """检查位置是否在区域内"""
        lat = position.get("lat", 0)
        lon = position.get("lon", 0)

        return (region["min_lat"] <= lat <= region["max_lat"] and
                region["min_lon"] <= lon <= region["max_lon"])

    def activate_emergency_stop(self, reason: str):
        """激活紧急停止"""
        self.global_safety_state["emergency_stop"] = True
        logger.info(f"[SafetyCoordinator] 紧急停止激活: {reason}")

    def add_restricted_region(self, region: Dict):
        """添加限制区域"""
        self.global_safety_state["restricted_regions"].append(region)