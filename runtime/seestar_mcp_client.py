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
from typing import List, Dict, Optional, Any
from enum import Enum
import asyncio
import json
import subprocess
import os


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
        # 执行安全检查
        safety_result = await self.safety_check(target)
        if not safety_result.passed:
            print(f"安全检查未通过: {safety_result.reasons}")
            return False

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
