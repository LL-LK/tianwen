"""MultiAgentCoordinator - 多Agent协调器核心类"""

import logging
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Lazy imports for backward compatibility with coordinator.py
def _get_dependencies():
    """Lazy load dependencies to avoid circular imports"""
    from .coordinator.types_enums import AgentRole, AgentMode, AgentCapability, VLAAction, VLAActionType
    from .coordinator.infrastructure import ResearchAgent, Script, PerformanceFeedback
    from .coordinator.types_enums import ScriptLibrary, IterativeLearning
    return AgentRole, AgentMode, AgentCapability, VLAAction, VLAActionType, ResearchAgent, Script, PerformanceFeedback, ScriptLibrary, IterativeLearning

# Re-export for convenience
try:
    from .coordinator.types_enums import AgentRole, AgentMode, AgentCapability, VLAAction, VLAActionType
    from .coordinator.infrastructure import ResearchAgent, Script, PerformanceFeedback
    from .coordinator.types_enums import ScriptLibrary, IterativeLearning
except ImportError:
    pass


class MultiAgentCoordinator:
    """
    多Agent协调器

    功能:
    - 创建和管理Agent团队
    - 分配任务和协调合作
    - 处理Agent间对话
    - 冲突检测和解决
    - 共识机制
    - 剧本/演出管理 (Issue #36)
    - Qwen3-style模式切换
    - 迭代学习 (孰能生巧/举一反三)

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

        # 天文大舞台: 剧本库 (Issue #36)
        self.script_library = ScriptLibrary()
        self.iterative_learning = IterativeLearning()

        # VLA集成支持 (Issue #29)
        self.vla_coordinator: Optional['VLACoordinator'] = None

        # 过拟合检测集成 (Issue #13)
        self.overfit_callbacks: List[Callable] = []

        # 安全协调器
        self.safety_coordinator: Optional['SafetyCoordinator'] = None

        # 默认剧本
        self._init_default_scripts()

    def _init_default_scripts(self):
        """初始化默认剧本"""
        # 默认研究剧本
        research_script = Script(
            name="research_workflow",
            description="标准研究工作流剧本",
            required_roles=[
                AgentRole.RESEARCHER,       # 生
                AgentRole.HYPOTHESIS_GENERATOR,  # 旦
                AgentRole.DATA_ANALYST,    # 净
                AgentRole.COORDINATOR       # 丑
            ],
            stages=["planning", "research", "hypothesis", "analysis", "review", "decision"],
            transitions={
                "planner": "researcher",
                "researcher": "hypothesis_generator",
                "hypothesis_generator": "data_analyst",
                "data_analyst": "coordinator"
            },
            success_criteria={
                "completion_rate": 0.8,
                "hypothesis_quality": 0.7
            }
        )
        self.script_library.add_script(research_script)

    def set_agent_mode(self, agent_id: str, mode: AgentMode):
        """
        设置Agent运行模式 (Qwen3-style切换)

        参数:
            agent_id: Agent ID
            mode: 运行模式 (THINKING/NON_THINKING)
        """
        agent = self.agents.get(agent_id)
        if agent:
            agent.set_mode(mode)

    def execute_performance(
        self,
        script_name: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行演出 (剧本驱动的任务执行)

        参数:
            script_name: 剧本名称
            task: 任务数据

        返回:
            演出结果
        """
        script = self.script_library.get_script(script_name)
        if not script:
            return {"success": False, "error": f"Script {script_name} not found"}

        # 创建演出反馈
        feedback = PerformanceFeedback(
            script_name=script_name,
            role=AgentRole.COORDINATOR,  # 协调者主导
            success=False
        )

        try:
            # 执行各阶段
            for stage in script.stages:
                # 每个阶段根据角色分配任务
                pass  # 简化的演出执行

            feedback.success = True
            script.increment_performance(True)

        except Exception as e:
            feedback.success = False
            feedback.issues.append(str(e))
            script.increment_performance(False)

        # 学习反馈
        self.script_library.learn_from_feedback(feedback)

        return {
            "success": feedback.success,
            "script": script_name,
            "performance_count": script.performance_count,
            "success_rate": script.success_rate
        }

    def record_observation(self, observation: Dict[str, Any]):
        """
        记录观察数据 (举一反三素材)

        参数:
            observation: 观察数据
        """
        # 将观察数据传递给迭代学习
        self.iterative_learning.on_task_complete(
            task_type=observation.get("type", "unknown"),
            result={"success": observation.get("success", True)},
            context=observation
        )

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
        创建完整的研究团队 - 天文大舞台阵容

        默认团队配置 (生旦净末丑):
        - COORDINATOR (丑): 协调整个研究流程
        - RESEARCHER (生): 文献调研
        - HYPOTHESIS_GENERATOR (旦): 假说生成
        - DATA_ANALYST (净): 数据分析
        - OBSERVATION_EXECUTOR (末): 观测执行

        参数:
            team_name: 团队名称

        返回:
            以角色名称为键的Agent字典

        示例:
            team = coordinator.create_research_team("天文研究团队")
            researcher = team["researcher"]  # 生
        """
        team = {}

        # 丑 - 协调者 (chou) - 负责整体协调和决策
        team["coordinator"] = self.create_agent(
            name=f"{team_name}_Coordinator",
            role=AgentRole.COORDINATOR,
            expertise=["project_management", "coordination", "decision_making"]
        )

        # 生 - 研究者 (sheng) - 负责文献调研和信息收集
        team["researcher"] = self.create_agent(
            name=f"{team_name}_Researcher",
            role=AgentRole.RESEARCHER,
            expertise=["literature_review", "data_analysis", "information_synthesis"]
        )

        # 旦 - 假说生成者 (dan) - 负责生成研究假说
        team["hypothesis_generator"] = self.create_agent(
            name=f"{team_name}_HypothesisGenerator",
            role=AgentRole.HYPOTHESIS_GENERATOR,
            expertise=["creative_thinking", "scientific_reasoning", "hypothesis_formation"]
        )

        # 净 - 数据分析师 (jing) - 负责数据分析 (新增)
        team["data_analyst"] = self.create_agent(
            name=f"{team_name}_DataAnalyst",
            role=AgentRole.DATA_ANALYST,
            expertise=["statistical_analysis", "data_visualization", "pattern_recognition"]
        )

        # 末 - 观测执行者 (mo) - 负责观测执行
        team["observation_executor"] = self.create_agent(
            name=f"{team_name}_ObservationExecutor",
            role=AgentRole.OBSERVATION_EXECUTOR,
            expertise=["observation_planning", "telescope_operations", "data_capture"]
        )

        # 评审者 - 负责评审和反馈 (保留用于兼容)
        team["reviewer"] = self.create_agent(
            name=f"{team_name}_Reviewer",
            role=AgentRole.REVIEWER,
            expertise=["critical_analysis", "quality_assurance", "peer_review"]
        )

        # VLA Agent - 具身智能协调 (Issue #29)
        team["vla_agent"] = self.create_agent(
            name=f"{team_name}_VLA",
            role=AgentRole.VLA_AGENT,
            expertise=["visual_grounding", "action_planning", "embodied_ai", "robotics"]
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
        """获取团队统计信息 - 包含天文大舞台统计"""
        stats = {
            "team_id": self.team_id,
            "total_agents": len(self.agents),
            "pending_tasks": len(self.pending_tasks),
            "completed_tasks": len(self.completed_tasks),
            "messages_in_queue": len(self.message_queue),
            "agents": {}
        }

        # Agent详细信息
        for agent_id, agent in self.agents.items():
            stats["agents"][agent_id] = {
                "name": agent.name,
                "role": agent.role.value,
                "theatrical_role": agent.role.theatrical_name,  # 生旦净末丑
                "mode": agent.mode.value,  # thinking/non_thinking
                "messages_count": len(agent.conversation_history),
                "is_active": agent.is_active,
                "skill_level": agent.skill_level,  # 孰能生巧
                "performance_count": agent.performance_count
            }

        # 天文大舞台统计
        script_stats = self.script_library.get_statistics()
        learning_stats = self.iterative_learning.get_statistics()
        stats["theater"] = {
            "scripts": script_stats,
            "learning": learning_stats
        }

        return stats

    def clear_completed_tasks(self):
        """清空已完成任务记录"""
        self.completed_tasks = []


