"""
Coordinator Types and Enums - Extracted basic types from coordinator.py

This module contains fundamental type definitions that have no external dependencies.
These types are extracted to enable cleaner code organization and potential reuse.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Enums - Basic enumerations
# ============================================================================

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


class MessageType(Enum):
    """消息类型枚举"""
    TASK_ASSIGNMENT = "task_assignment"      # 任务分配
    RESULT_REPORT = "result_report"           # 结果报告
    QUERY = "query"                           # 查询
    SUGGESTION = "suggestion"                # 建议
    CRITIQUE = "critique"                    # 批评
    COORDINATION = "coordination"            # 协调
    CONFLICT = "conflict"                     # 冲突


class ConflictType(Enum):
    """冲突类型枚举"""
    RESOURCE_CONFLICT = "resource_conflict"    # 资源冲突 - 多个Agent竞争同一资源
    GOAL_CONFLICT = "goal_conflict"            # 目标冲突 - Agent目标不一致
    METHOD_CONFLICT = "method_conflict"        # 方法冲突 - 使用不同的方法达成目标
    PRIORITY_CONFLICT = "priority_conflict"    # 优先级冲突 - 任务优先级意见不一致


# ============================================================================
# Dataclasses - Basic data structures
# ============================================================================

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


@dataclass
class AgentMessage:
    """
    Agent间消息

    属性:
    - id: 消息唯一标识
    - sender_id: 发送者ID
    - receiver_id: 接收者ID (None表示广播)
    - message_type: 消息类型
    - content: 消息内容
    - timestamp: 时间戳
    - in_reply_to: 回复的消息ID
    - metadata: 附加元数据
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: Optional[str] = None  # None表示广播
    message_type: MessageType = MessageType.QUERY
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    in_reply_to: Optional[str] = None  # 回复的消息ID
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_broadcast(self) -> bool:
        """是否为广播消息"""
        return self.receiver_id is None

    def __repr__(self) -> str:
        return f"AgentMessage(from={self.sender_id}, to={self.receiver_id}, type={self.message_type.value})"


@dataclass
class Conflict:
    """
    冲突信息

    属性:
    - conflict_id: 唯一标识
    - conflict_type: 冲突类型
    - involved_agents: 参与的Agent ID列表
    - description: 冲突描述
    - proposed_resolutions: 提出的解决方案列表
    - resolved: 是否已解决
    - resolution: 最终解决方案
    """
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType = ConflictType.PRIORITY_CONFLICT
    involved_agents: List[str] = field(default_factory=list)
    description: str = ""
    proposed_resolutions: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Script:
    """
    剧本 - 任务执行模板 (Issue #36)

    属性:
    - name: 剧本名称
    - description: 剧本描述
    - required_roles: 需要角色列表
    - stages: 演出阶段列表
    - transitions: 角色切换条件
    - success_criteria: 成功标准
    - improvement_hints: 改进提示 (演出后填充)
    - performance_count: 演出次数 (孰能生巧)
    - success_rate: 成功率
    """
    name: str
    description: str = ""
    required_roles: List[AgentRole] = field(default_factory=list)
    stages: List[str] = field(default_factory=list)  # e.g., ["planning", "research", "hypothesis", "review"]
    transitions: Dict[str, str] = field(default_factory=dict)  # role -> next_role
    success_criteria: Dict[str, float] = field(default_factory=dict)  # metric -> threshold
    improvement_hints: List[str] = field(default_factory=list)
    performance_count: int = 0
    success_rate: float = 0.0

    def increment_performance(self, success: bool):
        """演出完成记录 (孰能生巧)"""
        self.performance_count += 1
        # 更新成功率
        current_successes = self.success_rate * (self.performance_count - 1)
        if success:
            current_successes += 1
        self.success_rate = current_successes / self.performance_count

    def add_improvement_hint(self, hint: str):
        """添加改进提示"""
        self.improvement_hints.append(hint)


@dataclass
class PerformanceFeedback:
    """
    演出反馈 (Issue #36)

    属性:
    - script_name: 剧本名称
    - role: 执行角色
    - success: 是否成功
    - metrics: 评分指标
    - issues: 发现问题
    - suggestions: 改进建议
    - observations: 观察数据 (举一反三素材)
    """
    script_name: str
    role: AgentRole
    success: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    observations: List[Dict] = field(default_factory=list)  # 用于举一反三
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SubTask:
    """
    子任务 - 任务分解后的执行单元

    属性:
    - id: 子任务唯一标识
    - name: 子任务名称
    - description: 子任务描述
    - assigned_agent_id: 分配的Agent ID
    - status: 任务状态
    - dependencies: 依赖的子任务ID列表
    - result: 执行结果
    - error: 错误信息
    - priority: 优先级 (1-10)
    - estimated_time: 预估执行时间(秒)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    assigned_agent_id: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    priority: int = 5
    estimated_time: float = 1.0

    def is_ready(self, completed_task_ids: Set[str]) -> bool:
        """检查依赖是否满足"""
        return all(dep_id in completed_task_ids for dep_id in self.dependencies)


@dataclass
class TaskDecompositionResult:
    """任务分解结果"""
    original_task: str
    subtasks: List[SubTask]
    parallel_groups: List[List[str]]  # 可以并行执行的子任务组
    total_estimated_time: float
    risks: List[str] = field(default_factory=list)