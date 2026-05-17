"""
核心类型定义 - Agent角色、枚举、基础数据结构
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable, Set
from enum import Enum
import uuid

logger = __name__


class AgentMode(Enum):
    """Qwen3-style Agent运行模式 - 思维模式切换"""
    THINKING = "thinking"      # 复杂推理模式 (生旦净主演)
    NON_THINKING = "non_thinking"  # 高效执行模式 (末丑配合)


class AgentRole(Enum):
    """Agent角色枚举 - 生旦净末丑"""
    # 生 (sheng) - 文献调研，正面主角
    RESEARCHER = "researcher"  # 生: 研究者/文献调研

    # 旦 (dan) - 假说生成，细腻创作
    HYPOTHESIS_GENERATOR = "hypothesis_generator"  # 旦: 假说生成

    # 净 (jing) - 数据分析，性格鲜明 (新增)
    DATA_ANALYST = "data_analyst"  # 净: 数据分析师

    # 末 (mo) - 观测执行，配合主演
    OBSERVATION_EXECUTOR = "observation_executor"  # 末: 观测执行

    # 丑 (chou) - 协调控制，灵活调度
    COORDINATOR = "coordinator"  # 丑: 协调者

    # 传统角色兼容 (保留用于向后兼容)
    PLANNER = "planner"              # 规划者
    EXECUTOR = "executor"            # 执行者
    REVIEWER = "reviewer"            # 评审者
    OBSERVATION_SPECIALIST = "observation_specialist"  # 观测专家
    VLA_AGENT = "vla_agent"          # VLA Agent

    @property
    def theatrical_name(self) -> str:
        """获取角色的戏曲名称"""
        theatrical_names = {
            AgentRole.RESEARCHER: "生",
            AgentRole.HYPOTHESIS_GENERATOR: "旦",
            AgentRole.DATA_ANALYST: "净",
            AgentRole.OBSERVATION_EXECUTOR: "末",
            AgentRole.COORDINATOR: "丑",
        }
        return theatrical_names.get(self, self.value)

    @property
    def mode(self) -> AgentMode:
        """获取角色对应的默认运行模式"""
        # 生旦净需要复杂推理 -> thinking模式
        thinking_roles = {
            AgentRole.RESEARCHER,
            AgentRole.HYPOTHESIS_GENERATOR,
            AgentRole.DATA_ANALYST,
        }
        return AgentMode.THINKING if self in thinking_roles else AgentMode.NON_THINKING


class VLAActionType(Enum):
    """VLA动作类型"""
    OBSERVE = "observe"              # 视觉观察
    PLAN = "plan"                   # 动作规划
    EXECUTE = "execute"             # 执行动作
    EVALUATE = "evaluate"          # 评估结果
    CORRECT = "correct"             # 纠正错误


@dataclass
class VLAAction:
    """VLA动作"""
    action_type: VLAActionType
    observation: Dict[str, Any]     # 观察数据
    plan: str = ""                  # 动作计划
    confidence: float = 0.0        # 置信度
    safety_check_passed: bool = False


@dataclass
class AgentCapability:
    """
    Agent能力定义

    属性:
    - name: 能力名称
    - description: 能力描述
    - skill_functions: 可调用的技能函数名列表
    """
    name: str
    description: str
    skill_functions: List[str]  # 可调用的技能函数名


class MessageType(Enum):
    """Agent间消息类型"""
    QUERY = "query"                  # 查询
    RESPONSE = "response"            # 响应
    OBSERVATION = "observation"      # 观察
    ACTION = "action"               # 动作
    FEEDBACK = "feedback"           # 反馈
    COORDINATION = "coordination"    # 协调
    CONFLICT = "conflict"            # 冲突
    SUGGESTION = "suggestion"        # 建议
    CRITIQUE = "critique"            # 批评


__all__ = [
    'AgentMode',
    'AgentRole',
    'VLAActionType',
    'VLAAction',
    'AgentCapability',
    'MessageType',
]