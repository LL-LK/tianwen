"""
工厂类 - Agent创建、团队组建
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any, Callable
import uuid

from .core import AgentMode, AgentRole, AgentCapability
from .state import ResearchAgent, Script, PerformanceFeedback

logger = __name__


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
        """从演出反馈学习 (举一反三)"""
        self.feedback_history.append(feedback)
        script = self.scripts.get(feedback.script_name)
        if script:
            script.increment_performance(feedback.success)
            for suggestion in feedback.suggestions:
                script.add_improvement_hint(suggestion)
        if feedback.observations:
            self._detect_novel_pattern(feedback)

    def _detect_novel_pattern(self, feedback: PerformanceFeedback) -> bool:
        """检测新模式用于剧本生成"""
        if len(feedback.observations) >= 5:
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


class AgentFactory:
    """Agent工厂类 - 创建和配置Agent"""

    @staticmethod
    def create_research_agent(
        name: str,
        role: AgentRole,
        expertise: Optional[List[str]] = None,
        capabilities: Optional[List[AgentCapability]] = None
    ) -> ResearchAgent:
        """创建研究Agent"""
        agent = ResearchAgent(
            id=str(uuid.uuid4()),
            name=name,
            role=role,
            mode=role.mode,  # 根据角色自动设置模式
            expertise=expertise or [],
            capabilities=capabilities or []
        )
        return agent

    @staticmethod
    def create_team(
        team_name: str,
        roles: List[AgentRole]
    ) -> Dict[str, ResearchAgent]:
        """创建Agent团队"""
        team = {}
        for role in roles:
            agent = AgentFactory.create_research_agent(
                name=f"{team_name}_{role.value}",
                role=role
            )
            team[role.value] = agent
        return team


__all__ = ['ScriptLibrary', 'AgentFactory']
