"""
TianwenAGI Harness - Agent基类与接口
统一Agent接口，参考lm-evaluation-harness的插件化架构
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import uuid
import logging

logger = logging.getLogger("harness.agent")


class AgentType(Enum):
    """Agent类型枚举"""
    COORDINATOR = "coordinator"          # 协调Agent
    RESEARCHER = "researcher"            # 研究Agent
    DATA_ANALYST = "data_analyst"      # 数据分析Agent
    HYPOTHESIS_GENERATOR = "hypothesis_generator"  # 假说生成Agent
    TELESCOPE_CONTROLLER = "telescope_controller"  # 望远镜控制Agent
    LITERATURE_AGENT = "literature_agent"  # 文献调研Agent
    MULTI_MODAL = "multi_modal"        # 多模态Agent
    REAL_BOGUS = "real_bogus"          # Real-Bogus检测Agent
    CUSTOM = "custom"                  # 自定义Agent


class AgentCapability(Enum):
    """Agent能力枚举"""
    WEB_SEARCH = "web_search"           # 网页搜索
    GITHUB_SEARCH = "github_search"    # GitHub搜索
    LITERATURE_SEARCH = "literature_search"  # 文献搜索
    TELESCOPE_CONTROL = "telescope_control"  # 望远镜控制
    DATA_ANALYSIS = "data_analysis"   # 数据分析
    IMAGE_PROCESSING = "image_processing"  # 图像处理
    SPECTROSCOPY = "spectroscopy"       # 光谱处理
    CATALOG_QUERY = "catalog_query"    # 星表查询
    MCP_TOOL_CALL = "mcp_tool_call"    # MCP工具调用
    REASONING = "reasoning"             # 推理能力
    CODE_EXECUTION = "code_execution"   # 代码执行
    MULTI_AGENT = "multi_agent"        # 多Agent协作


@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    agent_type: AgentType
    model: str = "minimax"             # 推理模型
    provider: str = "minimax-cn"       # 模型提供商
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 300                 # 超时秒数
    capabilities: List[AgentCapability] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)  # 可用工具列表
    memory_enabled: bool = True        # 是否启用记忆
    learning_enabled: bool = True      # 是否启用学习
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_capability(self, cap: AgentCapability) -> bool:
        return cap in self.capabilities


@dataclass
class AgentMessage:
    """Agent内部消息"""
    sender_id: str
    receiver_id: Optional[str]          # None表示广播
    content: str
    message_type: str = "text"         # text, json, tool_call, result
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentAction:
    """Agent执行的动作"""
    action_type: str                    # plan, execute, think, tool_call, respond
    content: Any
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None   # 思考过程
    confidence: float = 1.0


@dataclass
class AgentResult:
    """Agent执行结果"""
    agent_id: str
    success: bool
    output: Any
    actions: List[AgentAction] = field(default_factory=list)  # 执行的动作链
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)  # 工具调用记录
    execution_time: float = 0          # 执行时间秒
    tokens_used: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_action(self, action: AgentAction):
        self.actions.append(action)

    def add_tool_call(self, tool_name: str, params: Dict, result: Any):
        self.tool_calls.append({
            "tool": tool_name,
            "params": params,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })


class BaseAgent(ABC):
    """
    Agent基类 - 所有Agent必须实现此接口
    参考lm-evaluation-harness的插件化架构设计
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = str(uuid.uuid4())[:8]
        self._message_history: List[AgentMessage] = []
        self._tool_registry: Dict[str, Callable] = {}
        self._initialized = False

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def agent_type(self) -> AgentType:
        return self.config.agent_type

    @abstractmethod
    async def plan(self, task_input: str, context: Dict[str, Any]) -> List[AgentAction]:
        """
        规划阶段 - 将任务分解为动作序列
        Returns: 动作列表
        """
        pass

    @abstractmethod
    async def execute(self, action: AgentAction) -> Any:
        """
        执行阶段 - 执行单个动作
        Returns: 执行结果
        """
        pass

    @abstractmethod
    async def respond(self, task_input: str, context: Dict[str, Any]) -> AgentResult:
        """
        完整响应 - 规划+执行，返回最终结果
        这是主要入口方法
        """
        pass

    def register_tool(self, name: str, handler: Callable):
        """注册工具处理器"""
        self._tool_registry[name] = handler

    def get_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self._tool_registry.keys())

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """调用工具"""
        if tool_name not in self._tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found. Available: {list(self._tool_registry.keys())}")
        handler = self._tool_registry[tool_name]
        return await handler(**params)

    def send_message(self, receiver_id: str, content: str, msg_type: str = "text", metadata: Dict = None):
        """发送消息给其他Agent"""
        msg = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            content=content,
            message_type=msg_type,
            metadata=metadata or {}
        )
        self._message_history.append(msg)
        return msg

    def receive_message(self, message: AgentMessage):
        """接收消息"""
        self._message_history.append(message)

    def get_message_history(self) -> List[AgentMessage]:
        return self._message_history.copy()

    def clear_history(self):
        """清空消息历史"""
        self._message_history.clear()

    def __repr__(self):
        return f"<{self.__class__.__name__}[{self.agent_type.value}] id={self.agent_id} name={self.name}>"
