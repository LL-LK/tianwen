"""
Enhanced Research Loop Module - 增强研究闭环模块

提取自 coordinator.py 的集成应用类:
- EnhancedResearchLoop: 增强的研究闭环
- ResearchLoopAdapter: 研究闭环适配器

依赖类:
- MultiAgentCoordinator, CollaborationWorkflow, ConflictResolver (from coordinator_core, workflow)

Author: Tianwen-AGI Team
Date: 2026/05/16
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Lazy imports for backward compatibility


# ============================================================================
# EnhancedResearchLoop - 增强的研究闭环
# ============================================================================

class EnhancedResearchLoop:
    """
    增强的研究闭环 - 集成多Agent协作

    在原有ResearchLoop基础上增加:
    - 多Agent团队管理
    - 对话协作机制
    - 冲突解决
    - 共识决策

    使用示例:
        enhanced_loop = EnhancedResearchLoop()
        await enhanced_loop.initialize_team()
        result = await enhanced_loop.run_collaborative_cycle("宇宙暗能量研究")
    """

    def __init__(self):
        """初始化增强研究闭环"""
        # Lazy import to avoid circular dependency
        from .coordinator_core import MultiAgentCoordinator
        from .workflow import CollaborationWorkflow
        
        self.coordinator = MultiAgentCoordinator()
        self.workflow = CollaborationWorkflow(self.coordinator)
        self.conflict_resolver = ConflictResolver(self.coordinator)
        self.team: Optional[Dict[str, 'ResearchAgent']] = None
        self.cycle_count: int = 0

    async def initialize_team(
        self,
        team_name: str = "TianwenAGI",
        custom_roles: Optional[List['AgentRole']] = None
    ) -> Dict[str, 'ResearchAgent']:
        """
        初始化研究团队

        参数:
            team_name: 团队名称
            custom_roles: 可选的自定义角色列表

        返回:
            Agent字典
        """
        from .coordinator import AgentRole
        
        if custom_roles:
            # 创建自定义团队
            self.team = {}
            role_names = {
                AgentRole.COORDINATOR: "协调者",
                AgentRole.PLANNER: "规划者",
                AgentRole.RESEARCHER: "研究者",
                AgentRole.HYPOTHESIS_GENERATOR: "假说生成者",
                AgentRole.REVIEWER: "评审者"
            }

            for role in custom_roles:
                agent = self.coordinator.create_agent(
                    name=f"{team_name}_{role.value}",
                    role=role,
                    expertise=["research", "analysis"]
                )
                self.team[role.value] = agent
        else:
            # 创建默认团队
            self.team = self.coordinator.create_research_team(team_name)

        return self.team

    async def run_collaborative_cycle(self, topic: str) -> Dict[str, Any]:
        """
        运行协作研究闭环

        参数:
            topic: 研究主题

        返回:
            包含工作流结果和团队统计的字典
        """
        self.cycle_count += 1

        if not self.team:
            await self.initialize_team()

        # 运行工作流
        result = await self.workflow.run_research_workflow(topic)

        # 记录统计
        stats = self.coordinator.get_statistics()
        conflict_stats = self.conflict_resolver.get_conflict_statistics()

        return {
            "cycle_number": self.cycle_count,
            "topic": topic,
            "workflow_result": result,
            "team_statistics": stats,
            "conflict_statistics": conflict_stats
        }

    async def add_agent(
        self,
        name: str,
        role: 'AgentRole',
        expertise: List[str]
    ) -> 'ResearchAgent':
        """
        添加新的Agent到团队

        参数:
            name: Agent名称
            role: Agent角色
            expertise: 专业知识领域

        返回:
            创建的ResearchAgent
        """
        agent = self.coordinator.create_agent(name, role, expertise)
        if self.team is None:
            self.team = {}
        self.team[name] = agent
        return agent

    def get_team_status(self) -> Dict[str, Any]:
        """
        获取团队状态

        返回:
            包含团队状态信息的字典
        """
        return {
            "team_initialized": self.team is not None,
            "cycle_count": self.cycle_count,
            "statistics": self.coordinator.get_statistics() if self.team else {},
            "active_conflicts": len(self.conflict_resolver.get_active_conflicts())
        }

    async def simulate_conflict(self, topic: str) -> Dict[str, Any]:
        """
        模拟冲突场景并演示冲突解决

        参数:
            topic: 冲突相关的议题

        返回:
            冲突解决结果
        """
        if not self.team:
            return {"error": "Team not initialized"}

        agents = list(self.team.values())
        if len(agents) < 2:
            return {"error": "Not enough agents for conflict simulation"}

        # 检测冲突
        agent1 = agents[0]
        agent2 = agents[1] if len(agents) > 1 else agents[0]

        conflict = self.conflict_resolver.detect_conflict(
            agent1_id=agent1.id,
            agent2_id=agent2.id,
            issue=topic,
            conflict_type=ConflictType.METHOD_CONFLICT
        )

        if conflict:
            resolution = await self.conflict_resolver.resolve_conflict(
                conflict,
                strategy="consensus"
            )
            return {
                "conflict_detected": True,
                "conflict_id": conflict.conflict_id,
                "conflict_type": conflict.conflict_type.value,
                "resolution": resolution
            }

        return {
            "conflict_detected": False,
            "message": "No conflict detected"
        }


# ============================================================================
# ResearchLoopAdapter - 研究闭环适配器
# ============================================================================

class ResearchLoopAdapter:
    """
    research_loop.py适配器

    提供与原有ResearchLoop的兼容接口,
    使现有代码可以平滑迁移到多Agent架构
    """

    def __init__(self):
        """初始化适配器"""
        self.enhanced_loop = EnhancedResearchLoop()

    async def initialize(self):
        """初始化增强研究闭环"""
        await self.enhanced_loop.initialize_team()

    async def run_cycle(self, topic: str) -> Dict[str, Any]:
        """
        运行研究闭环 (兼容原有接口)

        参数:
            topic: 研究主题

        返回:
            研究结果
        """
        return await self.enhanced_loop.run_collaborative_cycle(topic)

    def get_coordinator(self) -> 'MultiAgentCoordinator':
        """获取协调器"""
        return self.enhanced_loop.coordinator

    def get_conflict_resolver(self) -> 'ConflictResolver':
        """获取冲突解决器"""
        return self.enhanced_loop.conflict_resolver


# Import ConflictResolver at module level for type hints
from .coordinator import ConflictResolver, ConflictType