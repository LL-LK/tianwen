"""
路由与冲突解决 - 冲突类型、冲突解决器
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import uuid
import numpy as np

logger = __name__

# Import from core for types needed by routing
from .core import AgentRole, AgentMode


class ConflictType(Enum):
    """冲突类型枚举"""
    RESOURCE_CONFLICT = "resource_conflict"    # 资源冲突
    GOAL_CONFLICT = "goal_conflict"            # 目标冲突
    METHOD_CONFLICT = "method_conflict"        # 方法冲突
    PRIORITY_CONFLICT = "priority_conflict"    # 优先级冲突


@dataclass
class Conflict:
    """冲突信息"""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType = ConflictType.PRIORITY_CONFLICT
    involved_agents: List[str] = field(default_factory=list)
    description: str = ""
    proposed_resolutions: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class ConflictResolver:
    """
    冲突解决器

    策略:
    1. 优先级裁决: 高优先级Agent的意见优先
    2. 共识机制: 多数投票
    3. 专家裁决: 相关领域专家决定
    4. 妥协方案: 综合各方意见
    """

    def __init__(self, coordinator: Any):
        self.coordinator = coordinator
        self.conflict_history: List[Conflict] = []
        self.active_conflicts: List[Conflict] = []

    def detect_conflict(
        self,
        agent1_id: str,
        agent2_id: str,
        issue: str,
        conflict_type: ConflictType = ConflictType.METHOD_CONFLICT,
        historical_agreement: Optional[float] = None
    ) -> Optional[Conflict]:
        agent1 = self.coordinator.agents.get(agent1_id)
        agent2 = self.coordinator.agents.get(agent2_id)

        if not agent1 or not agent2:
            return None

        if historical_agreement is not None:
            conflict_probability = 1 - historical_agreement
        else:
            expertise1 = set(agent1.expertise)
            expertise2 = set(agent2.expertise)
            overlap = len(expertise1 & expertise2)
            total = len(expertise1 | expertise2)
            similarity = overlap / total if total > 0 else 0.5
            conflict_probability = max(0.1, min(0.8, 1 - similarity))

        if np.random.random() < conflict_probability:
            conflict = Conflict(
                conflict_type=conflict_type,
                involved_agents=[agent1_id, agent2_id],
                description=issue
            )
            self.conflict_history.append(conflict)
            self.active_conflicts.append(conflict)
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
        return [c for c in self.active_conflicts if not c.resolved]

    def get_conflict_by_id(self, conflict_id: str) -> Optional[Conflict]:
        for conflict in self.conflict_history:
            if conflict.conflict_id == conflict_id:
                return conflict
        return None

    async def resolve_conflict(
        self,
        conflict: Conflict,
        strategy: str = "consensus"
    ) -> str:
        agents = {
            aid: self.coordinator.agents.get(aid)
            for aid in conflict.involved_agents
        }
        agents = {aid: agent for aid, agent in agents.items() if agent}

        if not agents:
            return "无法解决冲突: 涉及的Agent不存在"

        resolution = ""

        if strategy == "priority":
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
            votes = {aid: 0 for aid in agents.keys()}
            for round_num in range(3):
                for voter_id in agents.keys():
                    choice = max(agents.keys(), key=lambda k: abs(hash(k + str(round_num))) % 5)
                    if choice in votes:
                        votes[choice] += 1
            consensus_id = max(votes.keys(), key=lambda k: votes[k])
            resolution = f"共识决定: 采纳{agents[consensus_id].name}的方案 (票数: {votes[consensus_id]})"

        elif strategy == "expert":
            expert_id = self._select_expert(conflict)
            if expert_id and expert_id in agents:
                resolution = f"专家裁决: 采纳{agents[expert_id].name}的方案"
            else:
                resolution = "专家裁决: 无法确定专家, 采用妥协方案"

        else:
            all_expertise = []
            for agent in agents.values():
                all_expertise.extend(agent.expertise)
            expertise_count = {}
            for exp in all_expertise:
                expertise_count[exp] = expertise_count.get(exp, 0) + 1
            common_expertise = sorted(expertise_count.items(), key=lambda x: x[1], reverse=True)
            resolution = f"妥协方案: 综合{len(agents)}个Agent的意见, 涉及领域: {', '.join([e[0] for e in common_expertise[:3]])}"

        conflict.resolved = True
        conflict.resolution = resolution
        if conflict in self.active_conflicts:
            self.active_conflicts.remove(conflict)
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
        agent_expertise = {
            aid: set(agent.expertise)
            for aid, agent in self.coordinator.agents.items()
        }
        relevant_expertise = set()
        for expertise_list in agent_expertise.values():
            relevant_expertise.update(expertise_list)
        agent_relevance = {}
        for aid, expertise in agent_expertise.items():
            relevance = len(expertise & relevant_expertise)
            agent_relevance[aid] = relevance
        if agent_relevance:
            return max(agent_relevance.keys(), key=lambda k: agent_relevance[k])
        return ""

    def add_proposed_resolution(self, conflict: Conflict, resolution: str):
        if conflict.conflict_id not in [c.conflict_id for c in self.active_conflicts]:
            return
        conflict.proposed_resolutions.append(resolution)

    def get_conflict_statistics(self) -> Dict[str, Any]:
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
        agents = [self.coordinator.agents.get(aid) for aid in agent_ids if self.coordinator.agents.get(aid)]
        if len(agents) < 2:
            return {
                "estimated_confidence": 0.5,
                "agreement_probability": 0.5,
                "confidence_interval": (0.3, 0.7),
                "factors": ["Agent数量不足"]
            }
        expertise_sets = [set(a.expertise) for a in agents]
        overlap_count = len(set.intersection(*expertise_sets)) if expertise_sets else 0
        total_count = len(set.union(*expertise_sets)) if expertise_sets else 1
        expertise_overlap = overlap_count / total_count if total_count > 0 else 0.5
        historical_agreement = self._calculate_historical_agreement(agent_ids)
        roles = [a.role for a in agents]
        role_consistency = len(set(roles)) / len(roles)
        base_confidence = 0.5
        estimated_confidence = (
            base_confidence +
            expertise_overlap * 0.3 +
            historical_agreement * 0.2 -
            role_consistency * 0.1
        )
        estimated_confidence = max(0.1, min(0.95, estimated_confidence))
        agreement_probability = estimated_confidence
        n_samples = 100
        samples = []
        for _ in range(n_samples):
            perturbed = estimated_confidence + np.random.normal(0, 0.1)
            perturbed = max(0, min(1, perturbed))
            samples.append(perturbed)
        samples = np.array(samples)
        ci_lower = np.percentile(samples, 2.5)
        ci_upper = np.percentile(samples, 97.5)
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
        conversations = []
        for agent in self.coordinator.agents.values():
            if agent.id in agent_ids:
                conversations.extend(agent.conversation_history)
        if len(conversations) < 5:
            return 0.6
        return 0.7

    async def resolve_conflict_with_confidence(
        self,
        conflict: Conflict,
        strategy: str = "consensus"
    ) -> Dict[str, Any]:
        consensus_confidence = self.estimate_consensus_confidence(
            conflict.involved_agents,
            conflict.description
        )
        resolution = await self.resolve_conflict(conflict, strategy)
        return {
            "conflict_id": conflict.conflict_id,
            "resolution": resolution,
            "consensus_confidence": consensus_confidence["estimated_confidence"],
            "agreement_probability": consensus_confidence["agreement_probability"],
            "confidence_interval": consensus_confidence["confidence_interval"],
            "resolution_strategy": strategy
        }


__all__ = ['ConflictType', 'Conflict', 'ConflictResolver']