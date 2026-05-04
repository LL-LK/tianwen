"""
天问-AGI 多Agent协作系统

核心概念:
- ResearchAgent: 研究Agent（带角色和专业知识）
- AgentRole: 角色枚举 (生旦净末丑 - THEATRICAL_ROLES)
- Conversation: Agent间对话记录
- ConflictResolution: 冲突解决机制
- VLACoordinator: 视觉-语言-动作模型协调器

参考AutoGen的Agent设计:
- 对话协作
- 角色分工
- 冲突解决

增强功能:
- VLA集成接口 (Issue #29)
- 过拟合检测协同 (Issue #13)
- 硬件安全协调

天文大舞台架构 (Issue #36):
- 生旦净末丑: 角色定义 (sheng-dan-jing-mo-chou)
- 剧本/演出迭代: Script/Performance机制
- Qwen3模式切换: Thinking/Non-thinking模式
- 孰能生巧/举一反三: 迭代学习机制

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
# 第一部分: Agent角色定义 - 生旦净末丑 (Theatrical Roles)
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


# ============================================================================
# 第二部分: 剧本与演出机制 (Script/Performance System)
# ============================================================================

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
# 第三部分: 迭代学习机制 (孰能生巧/举一反三)
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
# 第四部分: 消息类型定义
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
# 第五部分: 多Agent协调器
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
# 第五部分: VLA协调器 (Issue #29 - Embodied AI / VLA集成)
# ============================================================================

class VLACoordinator:
    """
    视觉-语言-动作模型协调器

    功能:
    - 协调VLA模型的观察、规划和执行
    - 与SafetyCoordinator集成确保安全
    - 支持多模态输入处理
    - 动作执行与反馈循环

    Issue #29: Embodied AI - VLA集成
    """

    def __init__(self, coordinator: MultiAgentCoordinator):
        self.coordinator = coordinator
        self.current_action: Optional[VLAAction] = None
        self.action_history: List[VLAAction] = []
        self.vla_model_endpoint: Optional[str] = None
        self.safety_check_required: bool = True

    def set_vla_model(self, endpoint: str):
        """设置VLA模型端点"""
        self.vla_model_endpoint = endpoint

    async def observe_and_plan(
        self,
        observation: Dict[str, Any],
        goal: str,
        safety_context: Optional[Dict] = None
    ) -> VLAAction:
        """
        观察并规划动作

        Args:
            observation: 视觉/传感器观察数据
            goal: 目标描述
            safety_context: 安全上下文

        Returns:
            VLAAction: 规划的动作
        """
        # 创建观察动作
        action = VLAAction(
            action_type=VLAActionType.OBSERVE,
            observation=observation,
            plan="",
            confidence=0.0,
            safety_check_passed=False
        )

        # 如果有VLA模型端点，进行VLA推理
        if self.vla_model_endpoint:
            action = await self._vla_inference(observation, goal)

        # 安全检查
        if self.safety_check_required and safety_context:
            action.safety_check_passed = await self._check_safety(
                action, safety_context
            )

        self.current_action = action
        return action

    async def _vla_inference(
        self,
        observation: Dict[str, Any],
        goal: str
    ) -> VLAAction:
        """调用VLA模型进行推理"""
        import httpx

        # 构建VLA输入
        vla_input = {
            "observation": observation,
            "goal": goal,
            "history": [
                {
                    "action_type": a.action_type.value,
                    "confidence": a.confidence
                }
                for a in self.action_history[-5:]
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.vla_model_endpoint}/vla/plan",
                    json=vla_input
                )
                result = response.json()

                return VLAAction(
                    action_type=VLAActionType(result.get("action_type", "plan")),
                    observation=observation,
                    plan=result.get("plan", ""),
                    confidence=result.get("confidence", 0.0),
                    safety_check_passed=False
                )
        except Exception as e:
            # VLA调用失败，返回基于规则的默认动作
            return VLAAction(
                action_type=VLAActionType.PLAN,
                observation=observation,
                plan=f"Goal: {goal}. Analysis: {str(e)[:100]}",
                confidence=0.5,
                safety_check_passed=True
            )

    async def _check_safety(
        self,
        action: VLAAction,
        context: Dict
    ) -> bool:
        """安全检查"""
        # 检查动作是否涉及危险区域
        dangerous_keywords = ["sun", "laser", "bright"]

        for keyword in dangerous_keywords:
            if keyword.lower() in str(action.observation).lower():
                return False
            if keyword.lower() in action.plan.lower():
                return False

        return True

    async def execute_action(
        self,
        action: VLAAction,
        executor_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        执行动作

        Args:
            action: 要执行的动作
            executor_callback: 可选的执行器回调

        Returns:
            执行结果
        """
        if not action.safety_check_passed:
            return {"success": False, "error": "Safety check failed"}

        action.action_type = VLAActionType.EXECUTE
        self.action_history.append(action)

        if executor_callback:
            result = await executor_callback(action)
        else:
            result = {"success": True, "action": action.plan}

        return result

    def get_action_statistics(self) -> Dict[str, Any]:
        """获取动作统计"""
        if not self.action_history:
            return {"total_actions": 0, "avg_confidence": 0.0}

        confidences = [a.confidence for a in self.action_history]
        return {
            "total_actions": len(self.action_history),
            "avg_confidence": sum(confidences) / len(confidences),
            "recent_actions": len([a for a in self.action_history[-10:]])
        }


# ============================================================================
# 安全协调器
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
        print(f"[SafetyCoordinator] 紧急停止激活: {reason}")

    def add_restricted_region(self, region: Dict):
        """添加限制区域"""
        self.global_safety_state["restricted_regions"].append(region)


# ============================================================================
# 第六部分: 协作工作流
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
# 第六部分: 任务分解与并行调度 (Issue #61)
# ============================================================================

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


class TaskDecomposer:
    """
    任务分解器 - 将复杂任务分解为并行子任务

    功能:
    - 分析任务复杂度
    - 识别可并行的子任务
    - 构建依赖图
    - 生成执行计划

    使用示例:
        decomposer = TaskDecomposer(coordinator)
        result = decomposer.decompose("分析太阳系行星轨道数据")
        for group in result.parallel_groups:
            # 每组可以并行执行
            await scheduler.schedule([subtasks[i] for i in group])
    """

    def __init__(self, coordinator: 'MultiAgentCoordinator'):
        self.coordinator = coordinator

        # 任务模式库 - 不同类型任务的分解模板
        self.task_patterns = {
            "research": {
                "subtasks": ["文献调研", "数据分析", "假说生成", "验证实验", "结论整理"],
                "parallel_pairs": [["文献调研", "数据分析"], ["假说生成", "验证实验"]]
            },
            "observation": {
                "subtasks": ["目标规划", "设备检查", "数据采集", "数据处理", "结果分析"],
                "parallel_pairs": [["目标规划", "设备检查"]]
            },
            "analysis": {
                "subtasks": ["数据收集", "数据清洗", "统计分析", "可视化", "报告生成"],
                "parallel_pairs": [["数据收集", "数据清洗"]]
            },
            "development": {
                "subtasks": ["需求分析", "架构设计", "编码实现", "测试验证", "部署上线"],
                "parallel_pairs": [["需求分析", "架构设计"]]
            }
        }

        # 技能到Agent角色的映射
        self.skill_role_mapping = {
            "文献调研": AgentRole.RESEARCHER,
            "数据分析": AgentRole.DATA_ANALYST,
            "假说生成": AgentRole.HYPOTHESIS_GENERATOR,
            "验证实验": AgentRole.OBSERVATION_EXECUTOR,
            "结论整理": AgentRole.COORDINATOR,
            "目标规划": AgentRole.PLANNER,
            "设备检查": AgentRole.OBSERVATION_EXECUTOR,
            "数据采集": AgentRole.OBSERVATION_EXECUTOR,
            "数据处理": AgentRole.DATA_ANALYST,
            "结果分析": AgentRole.RESEARCHER,
            "数据收集": AgentRole.RESEARCHER,
            "数据清洗": AgentRole.DATA_ANALYST,
            "统计分析": AgentRole.DATA_ANALYST,
            "可视化": AgentRole.DATA_ANALYST,
            "报告生成": AgentRole.COORDINATOR,
            "需求分析": AgentRole.PLANNER,
            "架构设计": AgentRole.PLANNER,
            "编码实现": AgentRole.EXECUTOR,
            "测试验证": AgentRole.REVIEWER,
            "部署上线": AgentRole.EXECUTOR
        }

    def decompose(self, task: str, task_type: Optional[str] = None) -> TaskDecompositionResult:
        """
        分解任务为并行子任务

        参数:
            task: 原始任务描述
            task_type: 任务类型 (可选, 自动推断)

        返回:
            TaskDecompositionResult: 包含分解后的子任务和并行组
        """
        # 自动推断任务类型
        if task_type is None:
            task_type = self._infer_task_type(task)

        # 获取任务模式
        pattern = self.task_patterns.get(task_type, {
            "subtasks": ["任务规划", "任务执行", "结果验证", "总结报告"],
            "parallel_pairs": [["任务规划", "任务执行"]]
        })

        # 生成子任务
        subtasks = []
        subtask_id_base = f"SUB-{uuid.uuid4().hex[:8]}"

        for i, subtask_name in enumerate(pattern["subtasks"]):
            role = self.skill_role_mapping.get(subtask_name, AgentRole.EXECUTOR)

            # 构建依赖关系
            dependencies = []
            if i > 0 and i - 1 < len(subtasks):
                # 默认依赖前一个任务
                dependencies = [subtasks[i - 1].id]

            subtask = SubTask(
                id=f"{subtask_id_base}-{i + 1}",
                name=subtask_name,
                description=f"{subtask_name}: {task}",
                priority=min(10, 5 + (len(pattern["subtasks"]) - i)),
                estimated_time=self._estimate_subtask_time(subtask_name),
                dependencies=dependencies
            )
            subtasks.append(subtask)

        # 分析并行组
        parallel_groups = self._analyze_parallel_groups(subtasks, pattern.get("parallel_pairs", []))

        # 评估风险
        risks = self._assess_risks(subtasks)

        return TaskDecompositionResult(
            original_task=task,
            subtasks=subtasks,
            parallel_groups=parallel_groups,
            total_estimated_time=sum(s.estimated_time for s in subtasks),
            risks=risks
        )

    def _infer_task_type(self, task: str) -> str:
        """推断任务类型"""
        task_lower = task.lower()

        type_keywords = {
            "research": ["研究", "调研", "分析", "探索"],
            "observation": ["观测", "观察", "监测", "探测"],
            "analysis": ["分析", "处理", "统计", "计算"],
            "development": ["开发", "实现", "编写", "构建", "设计"]
        }

        for type_name, keywords in type_keywords.items():
            if any(kw in task_lower for kw in keywords):
                return type_name

        return "research"  # 默认类型

    def _estimate_subtask_time(self, subtask_name: str) -> float:
        """预估子任务执行时间"""
        time_estimates = {
            "文献调研": 5.0,
            "数据分析": 4.0,
            "假说生成": 3.0,
            "验证实验": 6.0,
            "结论整理": 2.0,
            "目标规划": 2.0,
            "设备检查": 3.0,
            "数据采集": 5.0,
            "数据处理": 4.0,
            "结果分析": 3.0,
            "数据收集": 4.0,
            "数据清洗": 3.0,
            "统计分析": 4.0,
            "可视化": 2.0,
            "报告生成": 2.0,
            "需求分析": 3.0,
            "架构设计": 4.0,
            "编码实现": 8.0,
            "测试验证": 5.0,
            "部署上线": 3.0
        }
        return time_estimates.get(subtask_name, 3.0)

    def _analyze_parallel_groups(
        self,
        subtasks: List[SubTask],
        parallel_pairs: List[List[str]]
    ) -> List[List[str]]:
        """分析可并行的任务组"""
        if not parallel_pairs:
            # 默认: 相邻任务如果无依赖可以并行
            groups = []
            current_group = []
            for i, subtask in enumerate(subtasks):
                if i > 0 and not subtask.dependencies:
                    current_group.append(subtask.id)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [subtask.id]
            if current_group:
                groups.append(current_group)
            return groups

        # 使用预定义的并行对
        groups = []
        for pair in parallel_pairs:
            group = []
            for subtask in subtasks:
                if subtask.name in pair:
                    group.append(subtask.id)
            if len(group) > 1:
                groups.append(group)

        # 添加单独的任务
        assigned = set()
        for group in groups:
            assigned.update(group)

        for subtask in subtasks:
            if subtask.id not in assigned:
                groups.append([subtask.id])

        return groups

    def _assess_risks(self, subtasks: List[SubTask]) -> List[str]:
        """评估任务风险"""
        risks = []

        if len(subtasks) > 7:
            risks.append("任务较多，可能需要分批执行")

        # 检查关键路径
        critical_skills = {"验证实验", "编码实现", "架构设计"}
        critical = [s for s in subtasks if s.name in critical_skills]
        if len(critical) > 2:
            risks.append("关键任务较多，建议密切监控")

        # 检查依赖深度
        max_depth = self._calculate_dependency_depth(subtasks)
        if max_depth > 4:
            risks.append("依赖链较长，任务延迟可能影响整体")

        return risks

    def _calculate_dependency_depth(self, subtasks: List[SubTask]) -> int:
        """计算依赖深度"""
        depth_map = {}

        def get_depth(subtask_id: str) -> int:
            if subtask_id in depth_map:
                return depth_map[subtask_id]

            subtask = next((s for s in subtasks if s.id == subtask_id), None)
            if not subtask or not subtask.dependencies:
                depth_map[subtask_id] = 1
                return 1

            max_child_depth = max(get_depth(d) for d in subtask.dependencies)
            depth_map[subtask_id] = max_child_depth + 1
            return depth_map[subtask_id]

        return max(get_depth(s.id) for s in subtasks) if subtasks else 0


class ParallelScheduler:
    """
    并行调度器 - 管理多Agent并行执行

    功能:
    - 调度多Agent并行执行子任务
    - 监控执行状态
    - 处理任务完成和失败
    - 汇总执行结果

    使用示例:
        scheduler = ParallelScheduler(coordinator)
        results = await scheduler.schedule(decomposition_result.subtasks)
    """

    def __init__(self, coordinator: 'MultiAgentCoordinator'):
        self.coordinator = coordinator
        self.active_tasks: Dict[str, SubTask] = {}
        self.completed_tasks: Dict[str, SubTask] = {}
        self.failed_tasks: Dict[str, SubTask] = {}

    async def schedule(self, subtasks: List[SubTask]) -> List[SubTask]:
        """
        并行调度子任务执行

        参数:
            subtasks: 子任务列表

        返回:
            执行完成的子任务列表
        """
        import asyncio

        # 初始化任务状态
        for task in subtasks:
            task.status = "pending"
            self.active_tasks[task.id] = task

        # 按依赖分组执行
        completed_ids: Set[str] = set()
        all_completed: List[SubTask] = []

        while self.active_tasks:
            # 找出所有可执行的任务（依赖已满足）
            ready_tasks = [
                task for task in self.active_tasks.values()
                if task.is_ready(completed_ids)
            ]

            if not ready_tasks:
                # 没有可执行的任务，可能有循环依赖
                break

            # 并行执行所有就绪的任务
            async def execute_single(task: SubTask) -> SubTask:
                return await self._execute_task(task)

            # 等待所有任务完成
            results = await asyncio.gather(
                *[execute_single(t) for t in ready_tasks],
                return_exceptions=True
            )

            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    # 处理异常
                    continue

                task = result
                if task.status == "completed":
                    completed_ids.add(task.id)
                    self.completed_tasks[task.id] = task
                    del self.active_tasks[task.id]
                    all_completed.append(task)
                elif task.status == "failed":
                    self.failed_tasks[task.id] = task
                    del self.active_tasks[task.id]

        return all_completed

    async def schedule_parallel_groups(
        self,
        subtasks: List[SubTask],
        parallel_groups: List[List[str]]
    ) -> List[SubTask]:
        """
        按并行组调度任务

        参数:
            subtasks: 所有子任务
            parallel_groups: 并行组 (每组内的任务可并行)

        返回:
            执行完成的子任务列表
        """
        import asyncio

        subtask_map = {s.id: s for s in subtasks}
        all_completed: List[SubTask] = []
        completed_ids: Set[str] = set()

        for group in parallel_groups:
            # 获取组内任务
            group_tasks = [subtask_map[tid] for tid in group if tid in subtask_map]

            # 过滤掉依赖未满足的任务
            ready_tasks = [t for t in group_tasks if t.is_ready(completed_ids)]

            if not ready_tasks:
                continue

            # 并行执行组内任务
            async def execute_single(task: SubTask) -> SubTask:
                return await self._execute_task(task)

            results = await asyncio.gather(
                *[execute_single(t) for t in ready_tasks],
                return_exceptions=True
            )

            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    continue

                task = result
                if task.status == "completed":
                    completed_ids.add(task.id)
                    self.completed_tasks[task.id] = task
                    all_completed.append(task)
                elif task.status == "failed":
                    self.failed_tasks[task.id] = task

        return all_completed

    async def _execute_task(self, task: SubTask) -> SubTask:
        """执行单个子任务"""
        import asyncio

        # 分配Agent
        if not task.assigned_agent_id:
            agent = self._select_agent_for_task(task)
            if agent:
                task.assigned_agent_id = agent.id

        task.status = "running"

        try:
            # 模拟任务执行
            # 实际应该调用Agent的执行能力
            await asyncio.sleep(task.estimated_time * 0.1)  # 模拟执行

            # 更新任务状态
            task.status = "completed"
            task.result = f"Task {task.name} completed successfully"

            # 更新Agent性能
            if task.assigned_agent_id:
                agent = self.coordinator.get_agent(task.assigned_agent_id)
                if agent:
                    agent.increment_performance(success=True)
                    agent.add_message(
                        "system",
                        f"完成任务: {task.name}",
                        metadata={"task_id": task.id, "status": "completed"}
                    )

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

            # 更新Agent性能
            if task.assigned_agent_id:
                agent = self.coordinator.get_agent(task.assigned_agent_id)
                if agent:
                    agent.increment_performance(success=False)

        return task

    def _select_agent_for_task(self, task: SubTask) -> Optional[ResearchAgent]:
        """为任务选择最合适的Agent"""
        # 使用TaskDecomposer的技能角色映射
        decomposer = TaskDecomposer(self.coordinator)
        role = decomposer.skill_role_mapping.get(task.name, AgentRole.EXECUTOR)

        # 查找对应角色的Agent
        agent = self.coordinator.get_agent_by_role(role)
        return agent

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "total_tasks": len(self.completed_tasks) + len(self.failed_tasks) + len(self.active_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "active": len(self.active_tasks),
            "success_rate": (
                len(self.completed_tasks) /
                (len(self.completed_tasks) + len(self.failed_tasks))
                if (len(self.completed_tasks) + len(self.failed_tasks)) > 0
                else 0.0
            )
        }


class ParallelCoordinator:
    """
    并行协调器 - 整合任务分解和并行调度

    提供完整的任务分解->调度->汇总流程

    使用示例:
        coordinator = ParallelCoordinator(multi_agent_coordinator)
        result = await coordinator.process_task("分析天文观测数据")
    """

    def __init__(self, multi_agent_coordinator: 'MultiAgentCoordinator'):
        self.coordinator = multi_agent_coordinator
        self.decomposer = TaskDecomposer(multi_agent_coordinator)
        self.scheduler = ParallelScheduler(multi_agent_coordinator)

    async def process_task(
        self,
        task: str,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理完整任务流程

        参数:
            task: 任务描述
            task_type: 任务类型 (可选)

        返回:
            包含执行结果的字典
        """
        # 1. 分解任务
        decomposition = self.decomposer.decompose(task, task_type)

        # 2. 分配Agent角色
        for subtask in decomposition.subtasks:
            agent = self.decomposer._select_agent_for_task(subtask)
            if agent:
                subtask.assigned_agent_id = agent.id

        # 3. 按并行组调度执行
        completed = await self.scheduler.schedule_parallel_groups(
            decomposition.subtasks,
            decomposition.parallel_groups
        )

        # 4. 汇总结果
        summary = self.scheduler.get_execution_summary()

        return {
            "original_task": task,
            "task_type": task_type or self.decomposer._infer_task_type(task),
            "decomposition": {
                "total_subtasks": len(decomposition.subtasks),
                "parallel_groups": len(decomposition.parallel_groups),
                "estimated_time": decomposition.total_estimated_time,
                "risks": decomposition.risks
            },
            "execution": {
                "completed": len(completed),
                "failed": summary["failed"],
                "success_rate": summary["success_rate"]
            },
            "subtasks": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "result": s.result,
                    "agent_id": s.assigned_agent_id
                }
                for s in decomposition.subtasks
            ]
        }


# ============================================================================
# 第七部分: 与research_loop.py集成
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