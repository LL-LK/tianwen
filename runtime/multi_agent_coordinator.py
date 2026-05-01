"""
天问-AGI 多Agent协作系统

核心概念:
- ResearchAgent: 研究Agent（带角色和专业知识）
- AgentRole: 角色枚举 (PLANNER/EXECUTOR/REVIEWER/COORDINATOR)
- Conversation: Agent间对话记录
- ConflictResolution: 冲突解决机制

参考AutoGen的Agent设计:
- 对话协作
- 角色分工
- 冲突解决

Author: Tianwen-AGI Team
Date: 2026/05/01
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import uuid
import numpy as np


# ============================================================================
# 第一部分: Agent角色定义
# ============================================================================

class AgentRole(Enum):
    """Agent角色枚举"""
    COORDINATOR = "coordinator"      # 协调者 - 分配任务、协调合作
    PLANNER = "planner"              # 规划者 - 制定研究计划
    EXECUTOR = "executor"            # 执行者 - 执行具体任务
    REVIEWER = "reviewer"            # 评审者 - 评估结果、提出建议
    RESEARCHER = "researcher"        # 研究者 - 文献调研
    HYPOTHESIS_GENERATOR = "hypothesis_generator"  # 假说生成
    OBSERVATION_SPECIALIST = "observation_specialist"  # 观测专家


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
class ResearchAgent:
    """
    研究Agent

    属性:
    - id: Agent唯一标识
    - name: Agent名称
    - role: Agent角色
    - expertise: 专业知识领域
    - capabilities: 可执行的能力
    - conversation_history: 对话历史
    - is_active: 是否活跃
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    expertise: List[str] = field(default_factory=list)
    capabilities: List[AgentCapability] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)
    is_active: bool = True

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


# ============================================================================
# 第二部分: 消息类型定义
# ============================================================================

class MessageType(Enum):
    """消息类型枚举"""
    TASK_ASSIGNMENT = "task_assignment"      # 任务分配
    RESULT_REPORT = "result_report"           # 结果报告
    QUERY = "query"                           # 查询
    SUGGESTION = "suggestion"                # 建议
    CRITIQUE = "critique"                    # 批评
    COORDINATION = "coordination"            # 协调
    CONFLICT = "conflict"                     # 冲突


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


# ============================================================================
# 第三部分: 多Agent协调器
# ============================================================================

class MultiAgentCoordinator:
    """
    多Agent协调器

    功能:
    - 创建和管理Agent团队
    - 分配任务和协调合作
    - 处理Agent间对话
    - 冲突检测和解决
    - 共识机制

    使用示例:
        coordinator = MultiAgentCoordinator()
        team = coordinator.create_research_team("MyTeam")
        task_id = await coordinator.assign_task(
            agent_id=team["planner"].id,
            task={"description": "制定研究计划"},
            priority=5
        )
    """

    def __init__(self):
        """初始化协调器"""
        self.agents: Dict[str, ResearchAgent] = {}
        self.message_queue: List[AgentMessage] = []
        self.pending_tasks: List[Dict] = []
        self.completed_tasks: List[Dict] = []
        self.team_id: str = str(uuid.uuid4())
        self.workflow_history: List[Dict] = []

    def create_agent(
        self,
        name: str,
        role: AgentRole,
        expertise: List[str],
        capabilities: Optional[List[AgentCapability]] = None
    ) -> ResearchAgent:
        """
        创建单个Agent

        参数:
            name: Agent名称
            role: Agent角色
            expertise: 专业知识领域列表
            capabilities: 可选的能力列表

        返回:
            创建的ResearchAgent实例
        """
        agent = ResearchAgent(
            name=name,
            role=role,
            expertise=expertise,
            capabilities=capabilities or []
        )
        self.agents[agent.id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Optional[ResearchAgent]:
        """根据ID获取Agent"""
        return self.agents.get(agent_id)

    def get_agent_by_role(self, role: AgentRole) -> Optional[ResearchAgent]:
        """根据角色获取第一个匹配的Agent"""
        for agent in self.agents.values():
            if agent.role == role:
                return agent
        return None

    def get_agents_by_role(self, role: AgentRole) -> List[ResearchAgent]:
        """根据角色获取所有匹配的Agent"""
        return [agent for agent in self.agents.values() if agent.role == role]

    def create_research_team(
        self,
        team_name: str = "ResearchTeam"
    ) -> Dict[str, ResearchAgent]:
        """
        创建完整的研究团队

        默认团队配置:
        - Coordinator: 协调整个研究流程
        - Planner: 制定研究计划
        - Researcher: 文献调研
        - HypothesisGenerator: 假说生成
        - Reviewer: 评审和反馈

        参数:
            team_name: 团队名称

        返回:
            以角色名称为键的Agent字典

        示例:
            team = coordinator.create_research_team("天文研究团队")
            planner = team["planner"]
        """
        team = {}

        # 协调者 - 负责整体协调和决策
        team["coordinator"] = self.create_agent(
            name=f"{team_name}_Coordinator",
            role=AgentRole.COORDINATOR,
            expertise=["project_management", "coordination", "decision_making"]
        )

        # 规划者 - 负责制定研究计划
        team["planner"] = self.create_agent(
            name=f"{team_name}_Planner",
            role=AgentRole.PLANNER,
            expertise=["strategic_planning", "goal_setting", "resource_allocation"]
        )

        # 研究者 - 负责文献调研和信息收集
        team["researcher"] = self.create_agent(
            name=f"{team_name}_Researcher",
            role=AgentRole.RESEARCHER,
            expertise=["literature_review", "data_analysis", "information_synthesis"]
        )

        # 假说生成者 - 负责生成研究假说
        team["hypothesis_generator"] = self.create_agent(
            name=f"{team_name}_HypothesisGenerator",
            role=AgentRole.HYPOTHESIS_GENERATOR,
            expertise=["creative_thinking", "scientific_reasoning", "hypothesis_formation"]
        )

        # 评审者 - 负责评审和反馈
        team["reviewer"] = self.create_agent(
            name=f"{team_name}_Reviewer",
            role=AgentRole.REVIEWER,
            expertise=["critical_analysis", "quality_assurance", "peer_review"]
        )

        return team

    async def assign_task(
        self,
        agent_id: str,
        task: Dict,
        priority: int = 5
    ) -> str:
        """
        分配任务给Agent

        参数:
            agent_id: 目标Agent的ID
            task: 任务描述字典, 包含:
                - description: 任务描述
                - context: 可选的上下文信息
                - expected_output: 期望输出
            priority: 优先级 (1-10, 10最高)

        返回:
            任务ID (UUID字符串)
        """
        task_id = str(uuid.uuid4())
        agent = self.agents.get(agent_id)

        if not agent:
            raise ValueError(f"Agent with id {agent_id} not found")

        task_record = {
            "task_id": task_id,
            "agent_id": agent_id,
            "agent_name": agent.name,
            "description": task.get("description", ""),
            "context": task.get("context", ""),
            "expected_output": task.get("expected_output", ""),
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None
        }

        self.pending_tasks.append(task_record)

        # 发送任务分配消息
        message = AgentMessage(
            sender_id="coordinator",
            receiver_id=agent_id,
            message_type=MessageType.TASK_ASSIGNMENT,
            content=f"新任务 [{priority}级]: {task.get('description', '')}",
            metadata={"task_id": task_id, "priority": priority}
        )
        self.message_queue.append(message)

        # 通知Agent
        agent.add_message(
            "system",
            f"收到新任务: {task.get('description', '')}",
            metadata={"task_id": task_id, "type": "task_assignment"}
        )

        return task_id

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict] = None
    ):
        """
        更新任务状态

        参数:
            task_id: 任务ID
            status: 新状态 ("pending", "in_progress", "completed", "failed")
            result: 可选的执行结果
        """
        for task in self.pending_tasks:
            if task["task_id"] == task_id:
                task["status"] = status
                if status == "in_progress" and not task["started_at"]:
                    task["started_at"] = datetime.now().isoformat()
                if status == "completed":
                    task["completed_at"] = datetime.now().isoformat()
                    task["result"] = result
                    # 移动到已完成列表
                    self.pending_tasks.remove(task)
                    self.completed_tasks.append(task)
                return

        # 如果在已完成列表中找到
        for task in self.completed_tasks:
            if task["task_id"] == task_id:
                task["status"] = status
                if result:
                    task["result"] = result
                return

    async def get_agent_result(self, agent_id: str, task_id: str) -> Optional[Dict]:
        """
        获取Agent执行结果

        参数:
            agent_id: Agent的ID
            task_id: 任务ID

        返回:
            任务结果字典, 如果未找到返回None
        """
        # 在已完成任务中查找
        for task in self.completed_tasks:
            if task["task_id"] == task_id and task["agent_id"] == agent_id:
                return task.get("result")
        return None

    def send_message(
        self,
        sender_id: str,
        receiver_id: Optional[str],
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict] = None
    ) -> AgentMessage:
        """
        发送消息

        参数:
            sender_id: 发送者ID
            receiver_id: 接收者ID (None表示广播)
            message_type: 消息类型
            content: 消息内容
            metadata: 附加元数据

        返回:
            创建的AgentMessage实例
        """
        message = AgentMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            metadata=metadata or {}
        )
        self.message_queue.append(message)

        # 更新发送者和接收者的对话历史
        sender = self.agents.get(sender_id)
        if sender:
            sender.add_message("assistant", content, {"message_id": message.id, "type": message_type.value})

        if receiver_id:
            receiver = self.agents.get(receiver_id)
            if receiver:
                receiver.add_message("user", content, {"message_id": message.id, "type": message_type.value})

        return message

    def broadcast_message(
        self,
        sender_id: str,
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict] = None
    ) -> List[AgentMessage]:
        """广播消息给所有Agent"""
        messages = []
        for agent_id in self.agents.keys():
            if agent_id != sender_id:  # 不发给自己
                msg = self.send_message(
                    sender_id=sender_id,
                    receiver_id=agent_id,
                    message_type=message_type,
                    content=content,
                    metadata=metadata
                )
                messages.append(msg)
        return messages

    def get_pending_tasks(self, agent_id: Optional[str] = None) -> List[Dict]:
        """
        获取待处理任务

        参数:
            agent_id: 可选的Agent ID过滤

        返回:
            任务列表
        """
        if agent_id:
            return [t for t in self.pending_tasks if t["agent_id"] == agent_id]
        return self.pending_tasks

    def get_statistics(self) -> Dict[str, Any]:
        """获取团队统计信息"""
        return {
            "team_id": self.team_id,
            "total_agents": len(self.agents),
            "pending_tasks": len(self.pending_tasks),
            "completed_tasks": len(self.completed_tasks),
            "messages_in_queue": len(self.message_queue),
            "agents": {
                agent_id: {
                    "name": agent.name,
                    "role": agent.role.value,
                    "messages_count": len(agent.conversation_history),
                    "is_active": agent.is_active
                }
                for agent_id, agent in self.agents.items()
            }
        }

    def clear_completed_tasks(self):
        """清空已完成任务记录"""
        self.completed_tasks = []


# ============================================================================
# 第四部分: 冲突解决机制
# ============================================================================

class ConflictType(Enum):
    """冲突类型枚举"""
    RESOURCE_CONFLICT = "resource_conflict"    # 资源冲突 - 多个Agent竞争同一资源
    GOAL_CONFLICT = "goal_conflict"            # 目标冲突 - Agent目标不一致
    METHOD_CONFLICT = "method_conflict"        # 方法冲突 - 使用不同的方法达成目标
    PRIORITY_CONFLICT = "priority_conflict"    # 优先级冲突 - 任务优先级意见不一致


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

    def __init__(self, coordinator: MultiAgentCoordinator):
        """
        初始化冲突解决器

        参数:
            coordinator: MultiAgentCoordinator实例
        """
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
# 第五部分: 协作工作流
# ============================================================================

class CollaborationWorkflow:
    """
    协作工作流

    定义研究团队的协作流程:
    1. Planner制定计划 - 分析任务, 制定研究计划
    2. Researcher执行调研 - 收集文献和数据
    3. HypothesisGenerator生成假说 - 基于调研结果生成假说
    4. Reviewer评审 - 评审假说的可行性和创新性
    5. Coordinator协调决策 - 综合各方意见做出最终决策

    使用示例:
        workflow = CollaborationWorkflow(coordinator)
        result = await workflow.run_research_workflow("黑洞信息悖论研究")
    """

    def __init__(self, coordinator: MultiAgentCoordinator):
        """
        初始化协作工作流

        参数:
            coordinator: MultiAgentCoordinator实例
        """
        self.coordinator = coordinator
        self.workflow_id = str(uuid.uuid4())
        self.current_workflow_log: List[Dict] = []

    async def run_research_workflow(
        self,
        topic: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        运行完整的研究工作流

        参数:
            topic: 研究主题
            context: 可选的上下文信息

        返回:
            工作流执行结果字典, 包含:
            - workflow_id: 工作流ID
            - topic: 研究主题
            - steps_completed: 完成的步骤数
            - log: 执行日志
            - final_decision: 最终决策
            - agent_outputs: 各Agent的输出
        """
        self.current_workflow_log = []
        agent_outputs = {}

        # Step 1: Planner制定研究计划
        planner = self.coordinator.get_agent_by_role(AgentRole.PLANNER)
        if planner:
            planner.add_message(
                "system",
                f"请为研究主题'{topic}'制定详细的研究计划，包括目标、方法和时间表"
            )
            self.current_workflow_log.append({
                "step": "planning",
                "agent": planner.name,
                "agent_id": planner.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["planner"] = {
                "response": f"针对'{topic}'的研究计划已制定",
                "key_points": ["文献调研", "数据分析", "假说验证"]
            }
        else:
            self.current_workflow_log.append({
                "step": "planning",
                "status": "skipped",
                "reason": "Planner not found"
            })

        # Step 2: Researcher执行文献调研
        researcher = self.coordinator.get_agent_by_role(AgentRole.RESEARCHER)
        if researcher:
            researcher.add_message(
                "system",
                f"请对'{topic}'进行深入的文献调研，收集相关论文和最新进展"
            )
            self.current_workflow_log.append({
                "step": "research",
                "agent": researcher.name,
                "agent_id": researcher.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["researcher"] = {
                "response": f"关于'{topic}'的文献调研已完成",
                "sources_found": 25,
                "key_papers": ["论文A", "论文B", "论文C"]
            }
        else:
            self.current_workflow_log.append({
                "step": "research",
                "status": "skipped",
                "reason": "Researcher not found"
            })

        # Step 3: HypothesisGenerator生成假说
        hypo_gen = self.coordinator.get_agent_by_role(AgentRole.HYPOTHESIS_GENERATOR)
        if hypo_gen:
            hypo_gen.add_message(
                "system",
                f"基于调研结果，请生成3-5个可检验的研究假说"
            )
            self.current_workflow_log.append({
                "step": "hypothesis_generation",
                "agent": hypo_gen.name,
                "agent_id": hypo_gen.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["hypothesis_generator"] = {
                "response": f"已生成关于'{topic}'的假说",
                "hypotheses": [
                    "假说1: 某种现象的原因是...",
                    "假说2: 在特定条件下会发生...",
                    "假说3: 两个变量之间存在关联..."
                ]
            }
        else:
            self.current_workflow_log.append({
                "step": "hypothesis_generation",
                "status": "skipped",
                "reason": "HypothesisGenerator not found"
            })

        # Step 4: Reviewer评审
        reviewer = self.coordinator.get_agent_by_role(AgentRole.REVIEWER)
        if reviewer:
            reviewer.add_message(
                "system",
                f"请评审生成的研究假说，提供反馈和建议，评估其可行性和创新性"
            )
            self.current_workflow_log.append({
                "step": "review",
                "agent": reviewer.name,
                "agent_id": reviewer.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["reviewer"] = {
                "response": "假说评审完成",
                "evaluation": {
                    "feasibility": 8,
                    "innovation": 7,
                    "significance": 9
                },
                "suggestions": ["需要更多实验验证", "考虑更多边界条件"]
            }
        else:
            self.current_workflow_log.append({
                "step": "review",
                "status": "skipped",
                "reason": "Reviewer not found"
            })

        # Step 5: Coordinator协调决策
        coordinator_agent = self.coordinator.get_agent_by_role(AgentRole.COORDINATOR)
        if coordinator_agent:
            coordinator_agent.add_message(
                "system",
                "请综合各方意见，分析假说的可行性和创新性，做出最终决策"
            )
            self.current_workflow_log.append({
                "step": "coordination",
                "agent": coordinator_agent.name,
                "agent_id": coordinator_agent.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["coordinator"] = {
                "response": "决策已形成",
                "decision": "推荐假说1和假说3进入下一阶段验证"
            }
        else:
            self.current_workflow_log.append({
                "step": "coordination",
                "status": "skipped",
                "reason": "Coordinator not found"
            })

        # 记录工作流历史
        workflow_record = {
            "workflow_id": self.workflow_id,
            "topic": topic,
            "steps_completed": len([s for s in self.current_workflow_log if s["status"] == "completed"]),
            "log": self.current_workflow_log,
            "final_decision": "基于团队协作的深入研究结论",
            "agent_outputs": agent_outputs,
            "context": context or {}
        }

        self.coordinator.workflow_history.append(workflow_record)

        return workflow_record

    async def run_parallel_workflow(
        self,
        topic: str,
        parallel_agents: List[AgentRole]
    ) -> Dict[str, Any]:
        """
        运行并行工作流 - 多个Agent同时执行任务

        参数:
            topic: 研究主题
            parallel_agents: 并行执行的Agent角色列表

        返回:
            并行工作流执行结果
        """
        import asyncio

        self.current_workflow_log = []
        results = {}

        # 创建并发任务
        tasks = []

        async def execute_agent_task(role: AgentRole, task_desc: str):
            agent = self.coordinator.get_agent_by_role(role)
            if agent:
                agent.add_message("system", task_desc)
                await asyncio.sleep(0.1)  # 模拟处理时间
                return {
                    "role": role.value,
                    "agent": agent.name,
                    "status": "completed",
                    "output": f"{role.value}完成{topic}相关任务"
                }
            return {"role": role.value, "status": "skipped"}

        # 为每个Agent创建任务
        for role in parallel_agents:
            task_desc = f"请处理'{topic}'相关的{role.value}任务"
            tasks.append(execute_agent_task(role, task_desc))

        # 并发执行
        task_results = await asyncio.gather(*tasks)

        for result in task_results:
            results[result.get("role", "unknown")] = result

        return {
            "workflow_id": self.workflow_id,
            "topic": topic,
            "parallel_results": results,
            "steps_completed": len([r for r in results.values() if r.get("status") == "completed"])
        }

    def get_workflow_history(self) -> List[Dict]:
        """获取工作流执行历史"""
        return self.coordinator.workflow_history


# ============================================================================
# 第六部分: 与research_loop.py集成
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
        self.coordinator = MultiAgentCoordinator()
        self.workflow = CollaborationWorkflow(self.coordinator)
        self.conflict_resolver = ConflictResolver(self.coordinator)
        self.team: Optional[Dict[str, ResearchAgent]] = None
        self.cycle_count: int = 0

    async def initialize_team(
        self,
        team_name: str = "TianwenAGI",
        custom_roles: Optional[List[AgentRole]] = None
    ) -> Dict[str, ResearchAgent]:
        """
        初始化研究团队

        参数:
            team_name: 团队名称
            custom_roles: 可选的自定义角色列表

        返回:
            Agent字典
        """
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
        role: AgentRole,
        expertise: List[str]
    ) -> ResearchAgent:
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
# 第七部分: 模拟数据测试
# ============================================================================

async def run_simulation():
    """
    模拟多Agent协作场景

    展示:
    1. 创建研究团队
    2. 分配任务
    3. 运行工作流
    4. 检测和解决冲突
    """
    print("=" * 60)
    print("天问-AGI 多Agent协作系统 模拟测试")
    print("=" * 60)

    # 创建协调器
    coordinator = MultiAgentCoordinator()
    print("\n[1] 创建多Agent协调器")

    # 创建研究团队
    print("\n[2] 创建研究团队")
    team = coordinator.create_research_team("天文研究团队")

    print(f"    团队成员:")
    for role, agent in team.items():
        print(f"    - {role}: {agent.name} (ID: {agent.id[:8]}...)")

    # 创建冲突解决器
    conflict_resolver = ConflictResolver(coordinator)
    print("\n[3] 初始化冲突解决器")

    # 创建工作流
    workflow = CollaborationWorkflow(coordinator)
    print("\n[4] 初始化协作工作流")

    # 分配任务
    print("\n[5] 分配任务")
    planner = team["planner"]
    task_id = await coordinator.assign_task(
        agent_id=planner.id,
        task={
            "description": "制定2026年天文观测研究计划",
            "context": "包括太阳系行星研究、深空探测等方向",
            "expected_output": "完整的研究计划文档"
        },
        priority=8
    )
    print(f"    任务分配成功: {task_id[:8]}... -> {planner.name}")

    # 运行工作流
    print("\n[6] 运行研究工作流")
    result = await workflow.run_research_workflow("黑洞信息悖论研究")

    print(f"\n    工作流执行结果:")
    print(f"    - 工作流ID: {result['workflow_id'][:8]}...")
    print(f"    - 研究主题: {result['topic']}")
    print(f"    - 完成步骤: {result['steps_completed']}/5")
    print(f"    - 最终决策: {result['final_decision']}")

    # 模拟冲突
    print("\n[7] 模拟冲突场景")
    researcher = team["researcher"]
    hypo_gen = team["hypothesis_generator"]

    conflict = conflict_resolver.detect_conflict(
        agent1_id=researcher.id,
        agent2_id=hypo_gen.id,
        issue="关于黑洞辐射机制的不同解释",
        conflict_type=ConflictType.METHOD_CONFLICT
    )

    if conflict:
        print(f"    检测到冲突: {conflict.conflict_id[:8]}...")
        print(f"    冲突类型: {conflict.conflict_type.value}")
        print(f"    涉及Agent: {researcher.name} vs {hypo_gen.name}")

        # 解决冲突
        resolution = await conflict_resolver.resolve_conflict(
            conflict,
            strategy="consensus"
        )
        print(f"    解决策略: 共识机制")
        print(f"    解决方案: {resolution}")
    else:
        print("    未检测到冲突 (模拟30%概率)")

    # 输出统计信息
    print("\n[8] 团队统计信息")
    stats = coordinator.get_statistics()
    print(f"    总Agent数: {stats['total_agents']}")
    print(f"    待处理任务: {stats['pending_tasks']}")
    print(f"    已完成任务: {stats['completed_tasks']}")
    print(f"    消息队列: {stats['messages_in_queue']}")

    print("\n" + "=" * 60)
    print("模拟测试完成!")
    print("=" * 60)

    return {
        "coordinator": coordinator,
        "team": team,
        "workflow_result": result,
        "statistics": stats
    }


# ============================================================================
# 第八部分: 与research_loop.py兼容的适配器
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

    def get_coordinator(self) -> MultiAgentCoordinator:
        """获取协调器"""
        return self.enhanced_loop.coordinator

    def get_conflict_resolver(self) -> ConflictResolver:
        """获取冲突解决器"""
        return self.enhanced_loop.conflict_resolver


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    import asyncio

    print("天问-AGI 多Agent协作系统")
    print("-" * 40)

    # 运行模拟测试
    result = asyncio.run(run_simulation())

    print("\n" + "-" * 40)
    print("模拟测试结果已返回")