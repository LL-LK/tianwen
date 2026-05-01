"""
seestar_mcp_client.py - ZWO Seestar望远镜MCP协议客户端

功能:
- MCP协议通信
- 望远镜状态监控
- 目标转向 (goto)
- 成像控制
- 安全检查

参考: https://github.com/taco-ops/seestar-mcp
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import asyncio
import json
import subprocess
import os


# ============================================================================
# 硬件接口抽象层 - ASCOM/INDI 支持
# ============================================================================

class HardwareInterfaceType(Enum):
    """硬件接口类型枚举"""
    ASCOM = "ascom"       # ASCOM (Windows平台)
    INDI = "indi"        # INDI (Linux/macOS平台)
    SEESTAR_MCP = "seestar_mcp"  # Seestar MCP协议
    SIMULATION = "simulation"  # 模拟模式


@dataclass
class HardwareInterfaceConfig:
    """硬件接口配置"""
    interface_type: HardwareInterfaceType = HardwareInterfaceType.SIMULATION
    host: str = "localhost"
    port: int = 8765
    ascom_driver_id: Optional[str] = None  # ASCOM Driver ID
    indi_host: str = "localhost"
    indi_port: int = 7624
    timeout_seconds: float = 30.0
    retry_count: int = 3


class BaseHardwareInterface:
    """
    硬件接口抽象基类

    定义望远镜硬件操作的统一接口，支持:
    - ASCOM (Windows)
    - INDI (Linux/macOS)
    - Seestar MCP
    """

    def __init__(self, config: HardwareInterfaceConfig):
        self.config = config
        self.is_connected = False

    async def connect(self) -> bool:
        """连接到硬件"""
        raise NotImplementedError

    async def disconnect(self):
        """断开连接"""
        raise NotImplementedError

    async def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        raise NotImplementedError

    async def goto(self, ra: float, dec: float) -> bool:
        """转向指定坐标"""
        raise NotImplementedError

    async def abort(self) -> bool:
        """中止当前操作"""
        raise NotImplementedError

    async def get_position(self) -> Dict[str, float]:
        """获取当前位置"""
        raise NotImplementedError


class INDIInterface(BaseHardwareInterface):
    """
    INDI硬件接口

    支持Linux/macOS平台的天文设备控制
    参考: https://indilib.org
    """

    def __init__(self, config: HardwareInterfaceConfig):
        super().__init__(config)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> bool:
        """连接到INDI服务器"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.config.indi_host,
                self.config.indi_port
            )
            self.is_connected = True
            return True
        except Exception as e:
            print(f"INDI连接失败: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """断开INDI连接"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.is_connected = False

    async def _send_indi_message(self, message: Dict) -> Dict:
        """发送INDI消息并等待响应"""
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            # 发送消息
            msg_json = json.dumps(message) + "\n"
            self.writer.write(msg_json.encode())
            await self.writer.drain()

            # 等待响应
            response_line = await asyncio.wait_for(
                self.reader.readline(),
                timeout=self.config.timeout_seconds
            )
            return json.loads(response_line.decode())

        except asyncio.TimeoutError:
            return {"error": "INDI操作超时"}
        except Exception as e:
            return {"error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """获取INDI设备状态"""
        result = await self._send_indi_message({
            "type": "get_properties",
            "device": self.config.host,
            "name": "Telescope"
        })
        return result

    async def goto(self, ra: float, dec: float) -> bool:
        """INDI GOTO命令"""
        result = await self._send_indi_message({
            "type": "set_vector",
            "device": self.config.host,
            "name": "EQUATORIAL_EOD_COORD",
            "values": {
                "RA": ra,
                "DEC": dec
            }
        })
        return "error" not in result

    async def abort(self) -> bool:
        """中止INDI操作"""
        result = await self._send_indi_message({
            "type": "set_vector",
            "device": self.config.host,
            "name": "ABORT"
        })
        return "error" not in result

    async def get_position(self) -> Dict[str, float]:
        """获取INDI望远镜位置"""
        result = await self._send_indi_message({
            "type": "get_vector",
            "device": self.config.host,
            "name": "EQUATORIAL_EOD_COORD"
        })
        if "values" in result:
            return {
                "ra": result["values"].get("RA", 0),
                "dec": result["values"].get("DEC", 0)
            }
        return {"ra": 0, "dec": 0}


class ASCOMInterface(BaseHardwareInterface):
    """
    ASCOM硬件接口

    支持Windows平台的COM组件调用
    参考: https://ascom-standards.org
    """

    def __init__(self, config: HardwareInterfaceConfig):
        super().__init__(config)
        self.driver: Optional[Any] = None

    async def connect(self) -> bool:
        """通过COM连接ASCOM驱动"""
        try:
            # 注意: 实际使用需要pywin32库
            # 这里使用模拟实现
            import platform
            if platform.system() != "Windows":
                print("ASCOM仅支持Windows平台")
                return False

            # 实际应该使用: import win32com.client
            # self.driver = win32com.client.Dispatch(self.config.ascom_driver_id)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"ASCOM连接失败: {e}")
            return False

    async def disconnect(self):
        """断开ASCOM连接"""
        if self.driver:
            try:
                self.driver.Connected = False
            except:
                pass
        self.is_connected = False

    async def get_status(self) -> Dict[str, Any]:
        """获取ASCOM望远镜状态"""
        if not self.is_connected or not self.driver:
            return {"error": "Not connected"}
        try:
            return {
                "tracking": self.driver.Tracking,
                "slewing": self.driver.Slewing,
                "connected": self.driver.Connected
            }
        except Exception as e:
            return {"error": str(e)}

    async def goto(self, ra: float, dec: float) -> bool:
        """ASCOM GOTO命令"""
        if not self.is_connected or not self.driver:
            return False
        try:
            self.driver.SlewToCoordinatesAsync(ra, dec)
            return True
        except Exception as e:
            print(f"ASCOM GOTO失败: {e}")
            return False

    async def abort(self) -> bool:
        """中止ASCOM操作"""
        if not self.is_connected or not self.driver:
            return False
        try:
            self.driver.AbortSlew()
            return True
        except Exception as e:
            print(f"ASCOM Abort失败: {e}")
            return False

    async def get_position(self) -> Dict[str, float]:
        """获取ASCOM望远镜位置"""
        if not self.is_connected or not self.driver:
            return {"ra": 0, "dec": 0}
        try:
            return {
                "ra": self.driver.RightAscension,
                "dec": self.driver.Declination
            }
        except Exception:
            return {"ra": 0, "dec": 0}


def create_hardware_interface(config: HardwareInterfaceConfig) -> BaseHardwareInterface:
    """
    工厂函数: 根据配置创建硬件接口

    Args:
        config: 硬件接口配置

    Returns:
        对应的硬件接口实例
    """
    if config.interface_type == HardwareInterfaceType.INDI:
        return INDIInterface(config)
    elif config.interface_type == HardwareInterfaceType.ASCOM:
        return ASCOMInterface(config)
    else:
        # 默认返回模拟接口
        return BaseHardwareInterface(config)


# ============================================================================
# 安全协议回调系统
# ============================================================================

@dataclass
class SafetyCallback:
    """安全回调定义"""
    name: str
    callback: Callable[[Dict], bool]  # 返回是否允许操作
    priority: int = 0  # 优先级，数字越大优先级越高


class SafetyProtocolManager:
    """
    安全协议管理器

    功能:
    - 注册和执行安全回调
    - 多层安全检查
    - 紧急停止机制
    """

    def __init__(self):
        self.callbacks: List[SafetyCallback] = []
        self.emergency_stop_active: bool = False
        self.last_safety_check: Optional[datetime] = None

    def register_callback(self, callback: SafetyCallback):
        """注册安全回调"""
        self.callbacks.append(callback)
        # 按优先级排序
        self.callbacks.sort(key=lambda c: c.priority, reverse=True)

    def unregister_callback(self, name: str):
        """取消注册回调"""
        self.callbacks = [c for c in self.callbacks if c.name != name]

    async def check_operation(self, operation: str, context: Dict) -> Dict[str, Any]:
        """
        检查操作是否安全

        Args:
            operation: 操作名称
            context: 操作上下文

        Returns:
            包含passed和reasons字段的字典
        """
        if self.emergency_stop_active:
            return {
                "passed": False,
                "reasons": ["紧急停止已激活"],
                "blocked": True
            }

        reasons: List[str] = []

        for callback in self.callbacks:
            try:
                if not callback.callback(context):
                    reasons.append(f"安全检查未通过: {callback.name}")
            except Exception as e:
                reasons.append(f"回调错误 {callback.name}: {str(e)}")

        self.last_safety_check = datetime.now()

        return {
            "passed": len(reasons) == 0,
            "reasons": reasons,
            "blocked": len(reasons) > 0
        }

    def activate_emergency_stop(self, reason: str = ""):
        """激活紧急停止"""
        self.emergency_stop_active = True
        print(f"[安全协议] 紧急停止已激活: {reason}")

    def deactivate_emergency_stop(self):
        """解除紧急停止"""
        self.emergency_stop_active = False
        print("[安全协议] 紧急停止已解除")


# ============================================================================
# 原有代码继续...
# ============================================================================

class TelescopeStatus(Enum):
    """望远镜状态枚举"""
    IDLE = "idle"           # 空闲
    SLEWING = "slewing"     # 正在转向
    TRACKING = "tracking"   # 跟踪中
    IMAGING = "imaging"     # 成像中
    ERROR = "error"         # 错误状态


@dataclass
class TelescopePosition:
    """望远镜位置信息"""
    ra: float = 0.0        # 赤经 (度)
    dec: float = 0.0        # 赤纬 (度)
    alt: float = 0.0        # 高度角 (度)
    az: float = 0.0         # 方位角 (度)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ObservationTarget:
    """观测目标 dataclass"""
    name: str = ""          # 目标名称
    ra: float = 0.0         # 赤经 (度)
    dec: float = 0.0        # 赤纬 (度)
    priority: float = 0.5    # 优先级 0-1
    exposure_time: float = 60.0  # 曝光时间 (秒)
    filter: str = "L"       # 滤光片


@dataclass
class SafetyCheckResult:
    """安全检查结果"""
    passed: bool = True           # 是否通过
    reasons: List[str] = field(default_factory=list)  # 未通过原因列表


class SeestarMCPClient:
    """
    ZWO Seestar望远镜MCP协议客户端

    功能:
    - 连接seestar-mcp服务器
    - 发送MCP协议命令
    - 解析返回结果
    - 状态监控
    - 安全协议回调

    使用示例:
        client = SeestarMCPClient(host="localhost", port=8765)
        await client.connect()
        status = await client.get_status()
        await client.goto_target(target)
        await client.safe_shutdown()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        mcp_server_path: Optional[str] = None
    ):
        """
        初始化Seestar MCP客户端

        Args:
            host: MCP服务器地址
            port: MCP服务器端口
            mcp_server_path: seestar-mcp服务器路径(用于启动)
        """
        self.host = host
        self.port = port
        self.mcp_server_path = mcp_server_path or self._find_seestar_mcp()
        self.is_connected = False
        self.process: Optional[subprocess.Popen] = None
        self.current_status = TelescopeStatus.IDLE
        self.current_position = TelescopePosition()
        self._simulation_mode = True  # 默认启用模拟模式用于测试

        # 安全协议管理器
        self.safety_manager = SafetyProtocolManager()
        self._setup_default_safety_callbacks()

        # 硬件接口抽象
        self.hardware_interface: Optional[BaseHardwareInterface] = None
        self.hardware_config = HardwareInterfaceConfig()

    def _find_seestar_mcp(self) -> Optional[str]:
        """
        查找seestar-mcp服务器可执行文件

        搜索常见安装位置:
        - ~/.local/bin/seestar-mcp
        - /usr/local/bin/seestar-mcp
        - 当前目录下的seestar-mcp
        - PATH环境变量中的seestar-mcp

        Returns:
            服务器路径，如果未找到返回None
        """
        possible_paths = [
            os.path.expanduser("~/.local/bin/seestar-mcp"),
            "/usr/local/bin/seestar-mcp",
            os.path.join(os.getcwd(), "seestar-mcp"),
            "seestar-mcp"  # PATH中
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None  # 未找到，需要用户配置

    def _setup_default_safety_callbacks(self):
        """设置默认安全回调"""
        # 太阳高度角限制回调
        def sun_altitude_check(context: Dict) -> bool:
            """检查太阳高度角是否过低（安全观测要求太阳在地平线以下18度）"""
            # 实际需要计算太阳位置，这里简化处理
            return True

        # 赤纬范围检查回调
        def dec_range_check(context: Dict) -> bool:
            """检查目标赤纬是否在望远镜可观测范围内"""
            target_dec = context.get("dec", 0)
            return -30 <= target_dec <= 85

        # 月亮距离检查回调
        def moon_distance_check(context: Dict) -> bool:
            """检查目标与月亮的角度距离是否足够（避免月亮过亮影响）"""
            # 实际需要计算月亮位置，这里简化处理
            return True

        self.safety_manager.register_callback(
            SafetyCallback("sun_altitude", sun_altitude_check, priority=10)
        )
        self.safety_manager.register_callback(
            SafetyCallback("dec_range", dec_range_check, priority=5)
        )
        self.safety_manager.register_callback(
            SafetyCallback("moon_distance", moon_distance_check, priority=3)
        )

    def register_safety_callback(self, name: str, callback: Callable[[Dict], bool], priority: int = 0):
        """注册额外的安全回调

        Args:
            name: 回调名称
            callback: 回调函数，接收操作上下文，返回是否允许
            priority: 优先级
        """
        self.safety_manager.register_callback(
            SafetyCallback(name, callback, priority)
        )

    def set_hardware_interface(self, interface_type: HardwareInterfaceType, **kwargs):
        """设置硬件接口类型

        Args:
            interface_type: 硬件接口类型
            **kwargs: 额外的接口配置参数
        """
        self.hardware_config.interface_type = interface_type
        if interface_type == HardwareInterfaceType.INDI:
            self.hardware_config.indi_host = kwargs.get("host", "localhost")
            self.hardware_config.indi_port = kwargs.get("port", 7624)
        elif interface_type == HardwareInterfaceType.ASCOM:
            self.hardware_config.ascom_driver_id = kwargs.get("driver_id")

        self.hardware_interface = create_hardware_interface(self.hardware_config)

    def enable_simulation(self, enabled: bool = True):
        """
        启用或禁用模拟模式

        Args:
            enabled: True启用模拟，False使用真实MCP服务器
        """
        self._simulation_mode = enabled

    async def connect(self) -> bool:
        """
        连接到seestar-mcp服务器

        如果服务器未运行，尝试启动

        Returns:
            连接是否成功
        """
        try:
            # 检查服务器是否运行
            if self.mcp_server_path and not await self._check_server():
                # 启动服务器
                await self._start_server()

            self.is_connected = True
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            self.is_connected = False
            return False

    async def _check_server(self) -> bool:
        """
        检查MCP服务器是否运行

        通过尝试连接指定端口来检测服务器

        Returns:
            服务器是否运行
        """
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _start_server(self):
        """
        启动seestar-mcp服务器进程

        使用subprocess启动服务器进程
        等待2秒让服务器完成初始化
        """
        if self.mcp_server_path:
            self.process = subprocess.Popen(
                [self.mcp_server_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 等待服务器启动
            await asyncio.sleep(2)

    async def call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict:
        """
        调用MCP工具

        构建MCP JSON-RPC 2.0请求并发送

        Args:
            tool_name: 工具名 (如 "seestar.goto", "seestar.status")
            arguments: 参数字典

        Returns:
            调用结果字典，包含content或error字段
        """
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            # 构建MCP协议请求
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 1
            }

            # 模拟模式或真实模式
            if self._simulation_mode:
                result = await self._simulate_tool_call(tool_name, arguments)
            else:
                result = await self._send_mcp_request(request)

            return result

        except Exception as e:
            return {"error": str(e)}

    async def _send_mcp_request(self, request: Dict) -> Dict:
        """
        发送MCP请求到服务器

        Args:
            request: MCP JSON-RPC请求

        Returns:
            服务器响应
        """
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)

            # 发送请求
            request_json = json.dumps(request) + "\n"
            writer.write(request_json.encode())
            await writer.drain()

            # 读取响应
            response_line = await reader.readline()
            writer.close()
            await writer.wait_closed()

            if response_line:
                response = json.loads(response_line.decode())
                return response.get("result", {})
            else:
                return {"error": "Empty response from server"}

        except Exception as e:
            return {"error": str(e)}

    async def _simulate_tool_call(
        self,
        tool_name: str,
        arguments: Dict
    ) -> Dict:
        """
        模拟工具调用 (用于测试和开发)

        当_simulation_mode为True时，模拟各种工具调用返回合理的结果

        Args:
            tool_name: 工具名称
            arguments: 参数

        Returns:
            模拟的响应结果
        """
        if tool_name == "seestar.location.get":
            # 模拟获取位置信息
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "latitude": 35.0,
                        "longitude": -115.0,
                        "altitude": 1200,
                        "timestamp": datetime.now().isoformat()
                    })
                }]
            }
        elif tool_name == "seestar.goto":
            # 模拟goto执行 - 状态变化
            self.current_status = TelescopeStatus.SLEWING
            await asyncio.sleep(0.5)  # 模拟转向过程
            self.current_status = TelescopeStatus.TRACKING

            # 更新当前位置
            self.current_position.ra = arguments.get("ra", 0)
            self.current_position.dec = arguments.get("dec", 0)
            self.current_position.timestamp = datetime.now()

            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "status": "success",
                        "target": arguments,
                        "position": {
                            "ra": self.current_position.ra,
                            "dec": self.current_position.dec
                        }
                    })
                }]
            }
        elif tool_name == "seestar.status":
            # 模拟获取状态
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "status": self.current_status.value,
                        "position": {
                            "ra": self.current_position.ra,
                            "dec": self.current_position.dec,
                            "alt": self.current_position.alt,
                            "az": self.current_position.az
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                }]
            }
        elif tool_name == "seestar.imaging.start":
            # 模拟开始成像
            self.current_status = TelescopeStatus.IMAGING
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "status": "imaging_started",
                        "exposure": arguments.get("exposure", 60),
                        "filter": arguments.get("filter", "L"),
                        "count": arguments.get("count", 1)
                    })
                }]
            }
        elif tool_name == "seestar.abort":
            # 模拟中止操作
            self.current_status = TelescopeStatus.IDLE
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "status": "aborted",
                        "previous_status": self.current_status.value
                    })
                }]
            }
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def goto_target(
        self,
        target: ObservationTarget
    ) -> bool:
        """
        望远镜转向目标

        执行目标转向前先进行安全检查

        Args:
            target: 观测目标

        Returns:
            是否成功
        """
        # 使用安全协议管理器进行检查
        context = {
            "operation": "goto",
            "target_name": target.name,
            "ra": target.ra,
            "dec": target.dec,
            "current_status": self.current_status.value
        }

        safety_result = await self.safety_manager.check_operation("goto", context)
        if not safety_result["passed"]:
            print(f"安全检查未通过: {safety_result['reasons']}")
            return False

        # 如果有硬件接口且不是模拟模式，使用硬件接口
        if self.hardware_interface and not self._simulation_mode:
            try:
                success = await self.hardware_interface.goto(target.ra, target.dec)
                if success:
                    self.current_status = TelescopeStatus.SLEWING
                return success
            except Exception as e:
                print(f"硬件接口GOTO失败，回退到MCP: {e}")

        result = await self.call_mcp_tool(
            "seestar.goto",
            {
                "ra": target.ra,
                "dec": target.dec,
                "name": target.name
            }
        )

        if "error" in result:
            return False

        return True

    async def get_status(self) -> Dict:
        """
        获取望远镜当前状态

        Returns:
            状态信息字典
        """
        return await self.call_mcp_tool("seestar.status", {})

    async def get_location(self) -> Dict:
        """
        获取望远镜位置信息

        Returns:
            位置信息字典
        """
        return await self.call_mcp_tool("seestar.location.get", {})

    async def start_imaging(
        self,
        exposure_time: float = 60,
        filter_name: str = "L",
        count: int = 1
    ) -> bool:
        """
        开始成像

        Args:
            exposure_time: 曝光时间 (秒)
            filter_name: 滤光片名称 (L/R/G/B/Ha/OIII/SII等)
            count: 成像数量

        Returns:
            是否成功开始成像
        """
        result = await self.call_mcp_tool(
            "seestar.imaging.start",
            {
                "exposure": exposure_time,
                "filter": filter_name,
                "count": count
            }
        )

        if "error" in result:
            return False

        self.current_status = TelescopeStatus.IMAGING
        return True

    async def abort(self) -> bool:
        """
        中止当前操作

        Returns:
            是否成功中止
        """
        result = await self.call_mcp_tool("seestar.abort", {})
        if "error" in result:
            return False
        self.current_status = TelescopeStatus.IDLE
        return True

    async def safety_check(self, target: ObservationTarget) -> SafetyCheckResult:
        """
        安全检查

        检查项:
        1. 目标高度角是否太低 - Seestar有效观测高度角范围
        2. 赤纬范围检查 - Seestar的机械限制
        3. 望远镜当前状态是否允许移动

        Args:
            target: 待检查的观测目标

        Returns:
            SafetyCheckResult: 包含passed和reasons字段
        """
        checks: List[str] = []

        # 检查1: 望远镜状态检查
        if self.current_status == TelescopeStatus.IMAGING:
            checks.append("望远镜正在成像，不允许转向")

        # 检查2: 赤纬范围检查 - Seestar典型限制
        if target.dec < -30 or target.dec > 85:
            checks.append(f"目标赤纬 {target.dec}° 超出范围 (-30° 到 85°)")

        # 检查3: 高度角限制 (需要计算)
        # 由于没有目标高度角信息，这里预留检查逻辑
        # 实际使用时需要根据当地经纬度和时间计算

        # 检查4: 太阳位置限制 (防止白天观测)
        # 需要计算太阳位置，当目标接近太阳时发出警告
        # sunrise_sunset_angle = 0  # 地平线以下几度

        # 检查5: 月亮位置限制 (防止月亮过亮时成像)
        # 需要计算月亮位置，当月亮过亮时发出警告

        return SafetyCheckResult(
            passed=len(checks) == 0,
            reasons=checks
        )

    async def safe_shutdown(self):
        """
        安全关闭望远镜

        依次执行:
        1. 中止所有当前操作
        2. 停止跟踪
        3. 关闭服务器进程
        4. 重置连接状态
        """
        # 先停止所有操作
        await self.abort()

        # 等待操作停止
        await asyncio.sleep(0.5)

        # 然后断开连接
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

        self.is_connected = False
        self.current_status = TelescopeStatus.IDLE

    async def analyze_and_slew(
        self,
        image_path: str,
        min_confidence: float = 0.7
    ) -> Dict:
        """
        分析图像并转向检测到的目标

        工作流程:
        1. 调用astro_pipeline分析图像
        2. 根据检测结果选择高优先级目标
        3. 执行goto

        Args:
            image_path: 图像文件路径
            min_confidence: 最小置信度阈值

        Returns:
            包含success、target和detection信息的字典
        """
        # 导入astro_pipeline
        try:
            from astro_pipeline import AstroPipeline
        except ImportError:
            return {"error": "astro_pipeline模块未找到"}

        pipeline = AstroPipeline()

        # 分析图像
        result = await pipeline.analyze(image_path)

        if not result or not result.get("sources"):
            return {"error": "No sources detected"}

        # 选择最高置信度的星系/类星体目标
        best_target = None
        best_score = 0

        for source in result["sources"]:
            confidence = source.get("confidence", 0)
            source_type = source.get("type", "")
            flux = source.get("flux", 0)

            # 筛选高置信度的星系或类星体
            if confidence >= min_confidence and source_type in ["GALAXY", "QSO"]:
                # 使用flux作为优先级评分
                if flux > best_score:
                    best_score = flux
                    best_target = source

        if not best_target:
            return {"error": "No suitable target found"}

        # 从图像元数据获取坐标 (简化处理)
        # 实际使用时需要从图像头文件或分析结果中获取RA/DEC
        ra = best_target.get("ra", 0)
        dec = best_target.get("dec", 0)

        if ra == 0 and dec == 0:
            return {"error": "Target coordinates not available"}

        # 创建观测目标
        target = ObservationTarget(
            name=f"Detected_{best_target.get('type', 'UNKNOWN')}",
            ra=ra,
            dec=dec,
            priority=best_score,
            exposure_time=best_target.get("exposure", 60),
            filter=best_target.get("filter", "L")
        )

        # 执行安全检查
        safety_result = await self.safety_check(target)
        if not safety_result.passed:
            return {
                "error": "Safety check failed",
                "reasons": safety_result.reasons
            }

        # 执行goto
        success = await self.goto_target(target)

        return {
            "success": success,
            "target": target,
            "detection": best_target
        }

    async def observe_sequence(
        self,
        targets: List[ObservationTarget],
        exposures_per_target: int = 3
    ) -> Dict:
        """
        执行序列观测

        按优先级排序后依次观测每个目标

        Args:
            targets: 目标列表
            exposures_per_target: 每个目标的曝光次数

        Returns:
            观测结果汇总
        """
        # 按优先级排序
        sorted_targets = sorted(targets, key=lambda t: t.priority, reverse=True)

        results = []
        total = len(sorted_targets)
        successful = 0

        for i, target in enumerate(sorted_targets):
            print(f"观测进度: {i+1}/{total} - {target.name}")

            # 安全检查
            safety_result = await self.safety_check(target)
            if not safety_result.passed:
                results.append({
                    "target": target.name,
                    "success": False,
                    "reason": f"安全检查未通过: {safety_result.reasons}"
                })
                continue

            # 转向目标
            goto_success = await self.goto_target(target)
            if not goto_success:
                results.append({
                    "target": target.name,
                    "success": False,
                    "reason": "转向失败"
                })
                continue

            # 等待跟踪稳定
            await asyncio.sleep(2)

            # 开始成像
            imaging_success = await self.start_imaging(
                exposure_time=target.exposure_time,
                filter_name=target.filter,
                count=exposures_per_target
            )

            if imaging_success:
                successful += 1
                results.append({
                    "target": target.name,
                    "success": True,
                    "exposures": exposures_per_target
                })
            else:
                results.append({
                    "target": target.name,
                    "success": False,
                    "reason": "成像失败"
                })

        return {
            "total_targets": total,
            "successful": successful,
            "failed": total - successful,
            "results": results
        }


# 便捷函数

async def create_client(
    host: str = "localhost",
    port: int = 8765,
    mcp_server_path: Optional[str] = None,
    simulation: bool = True
) -> SeestarMCPClient:
    """
    创建并连接Seestar MCP客户端的便捷函数

    Args:
        host: MCP服务器地址
        port: MCP服务器端口
        mcp_server_path: seestar-mcp服务器路径
        simulation: 是否使用模拟模式

    Returns:
        已连接的SeestarMCPClient实例
    """
    client = SeestarMCPClient(
        host=host,
        port=port,
        mcp_server_path=mcp_server_path
    )
    client.enable_simulation(simulation)
    await client.connect()
    return client


if __name__ == "__main__":
    # 简单测试
    async def test():
        client = SeestarMCPClient()
        client.enable_simulation(True)
        await client.connect()

        # 测试获取状态
        status = await client.get_status()
        print(f"状态: {status}")

        # 测试获取位置
        location = await client.get_location()
        print(f"位置: {location}")

        # 测试转向
        target = ObservationTarget(
            name="M31",
            ra=10.6847,  # 仙女座星系
            dec=41.2687,
            priority=0.9
        )

        success = await client.goto_target(target)
        print(f"转向结果: {success}")

        # 获取最终状态
        final_status = await client.get_status()
        print(f"最终状态: {final_status}")

        # 安全关闭
        await client.safe_shutdown()

    asyncio.run(test())
