"""
状态管理 - Agent状态、消息、脚本、反馈等数据结构
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable, Set
from enum import Enum
import uuid

# Import enums from core
from .core import AgentMode, AgentRole, VLAActionType, AgentCapability, MessageType

logger = __name__


@dataclass
class ResearchAgent:
    """
    研究Agent

    属性:
    - id: Agent唯一标识
    - name: Agent名称
    - role: Agent角色 (生旦净末丑)
    - mode: 运行模式 (THINKING/NON_THINKING - Qwen3风格)
    - expertise: 专业知识领域
    - capabilities: 可执行的能力
    - conversation_history: 对话历史
    - is_active: 是否活跃
    - skill_level: 技能等级 (孰能生巧)
    - performance_count: 演出次数
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    mode: AgentMode = AgentMode.NON_THINKING  # Qwen3-style mode
    expertise: List[str] = field(default_factory=list)
    capabilities: List[AgentCapability] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)
    is_active: bool = True
    skill_level: float = 1.0  # 技能等级 (1.0为基础)
    performance_count: int = 0  # 演出次数

    def set_mode(self, mode: AgentMode):
        """设置运行模式 (Qwen3-style切换)"""
        self.mode = mode

    def should_use_thinking(self) -> bool:
        """判断是否使用thinking模式"""
        # 复杂角色使用thinking模式
        return self.role.mode == AgentMode.THINKING or self.mode == AgentMode.THINKING

    def increment_performance(self, success: bool):
        """记录演出完成 (孰能生巧)"""
        self.performance_count += 1
        # 成功则提升技能等级
        if success:
            self.skill_level = min(10.0, self.skill_level + 0.1)

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        添加对话消息

        参数:
            role: 消息角色 ("user", "assistant", "system")
            content: 消息内容
            metadata: 附加元数据
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })

    def get_recent_messages(self, n: int = 10) -> List[Dict]:
        """
        获取最近n条消息

        参数:
            n: 消息数量

        返回:
            最近n条消息的列表
        """
        return self.conversation_history[-n:]

    def get_all_messages(self) -> List[Dict]:
        """获取所有对话历史"""
        return self.conversation_history

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []


@dataclass
class AgentMessage:
    """
    Agent消息

    属性:
    - id: 消息ID
    - type: 消息类型 (MessageType)
    - sender: 发送者ID
    - receiver: 接收者ID
    - content: 消息内容
    - metadata: 元数据
    - timestamp: 时间戳
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.QUERY
    sender: str = ""
    receiver: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


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


__all__ = [
    'ResearchAgent',
    'AgentMessage',
    'Script',
    'PerformanceFeedback',
]
