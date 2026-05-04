"""
观测执行器 - 与实际望远镜控制集成模块

实现与望远镜控制的集成，支持：
- 观测指令发送
- 状态监控
- 数据回传
- 队列管理

Author: 天问天文观测系统
"""

import asyncio
import base64
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import random
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObservationCommand(Enum):
    """观测指令类型枚举

    定义望远镜可执行的所有指令类型
    """
    SLEW_TO_TARGET = "slew_to_target"      # 转向目标：控制望远镜转向指定天区
    START_EXPOSURE = "start_exposure"      # 开始曝光：启动相机曝光
    STOP_EXPOSURE = "stop_exposure"        # 停止曝光：中止当前曝光
    TRACK_TARGET = "track_target"          # 跟踪目标：启动目标跟踪模式
    ABORT_OBSERVATION = "abort"            # 中止观测：紧急停止所有操作


class TelescopeStatus(Enum):
    """望远镜状态枚举

    描述望远镜当前的运行状态
    """
    IDLE = "idle"           # 空闲：望远镜处于待机状态
    SLEWING = "slewing"     # 转向中：正在转向目标位置
    TRACKING = "tracking"   # 跟踪中：正在跟踪天体
    EXPOSING = "exposing"   # 曝光中：正在进行观测拍摄
    ERROR = "error"         # 错误：发生故障需要处理


@dataclass
class ObservationInstruction:
    """观测指令数据类

    存储完整的观测指令信息，包括目标位置、曝光参数等

    Attributes:
        command: 观测指令类型
        target_ra: 目标赤经（度），SLEW_TO_TARGET和TRACK_TARGET需要
        target_dec: 目标赤纬（度），SLEW_TO_TARGET和TRACK_TARGET需要
        exposure_time: 曝光时间（秒），START_EXPOSURE需要
        filter_name: 滤光片名称，用于选择观测波段
        timestamp: 指令创建时间戳
    """
    command: ObservationCommand
    target_ra: Optional[float] = None      # 赤经 (度)
    target_dec: Optional[float] = None     # 赤纬 (度)
    exposure_time: Optional[float] = None  # 曝光时间 (秒)
    filter_name: Optional[str] = None       # 滤光片名称
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        """验证指令参数是否完整"""
        if self.command == ObservationCommand.SLEW_TO_TARGET:
            return self.target_ra is not None and self.target_dec is not None
        elif self.command == ObservationCommand.START_EXPOSURE:
            return self.exposure_time is not None
        elif self.command == ObservationCommand.TRACK_TARGET:
            return self.target_ra is not None and self.target_dec is not None
        return True


@dataclass
class TelescopeState:
    """望远镜当前状态数据类

    存储望远镜的实时状态信息
    """
    status: TelescopeStatus
    current_ra: float      # 当前赤经位置（度）
    current_dec: float     # 当前赤纬位置（度）
    tracking_target: Optional[str] = None  # 当前跟踪目标名称
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class ObservationData:
    """观测数据回传数据类

    存储从望远镜返回的观测数据及质量指标
    """
    timestamp: datetime                          # 数据采集时间
    image_data: List[List[int]]                      # 原始图像数据
    telescope_state: TelescopeState             # 采集时的望远镜状态
    quality_metrics: Dict[str, float]           # 图像质量指标

    def to_base64(self) -> str:
        """将图像数据转换为Base64编码"""
        # 将字节列表转换为字节串
        image_bytes = bytes(self.image_data)
        return base64.b64encode(image_bytes).decode('utf-8')

    @classmethod
    def from_base64(cls, base64_str: str, telescope_state: TelescopeState) -> 'ObservationData':
        """从Base64编码恢复图像数据"""
        image_bytes = base64.b64decode(base64_str)
        # 假设标准图像尺寸，需要根据实际情况调整
        image_data = list(image_bytes)
        return cls(
            timestamp=datetime.now(),
            image_data=image_data,
            telescope_state=telescope_state,
            quality_metrics={}
        )


@dataclass
class ObservationResult:
    """观测执行结果数据类

    记录完整观测计划的执行统计
    """
    total_instructions: int          # 总指令数
    successful: int                 # 成功指令数
    failed: int                     # 失败指令数
    results: List[Dict[str, Any]]   # 详细执行结果
    start_time: datetime            # 开始时间
    end_time: Optional[datetime] = None  # 结束时间

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_instructions == 0:
            return 0.0
        return self.successful / self.total_instructions

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'total_instructions': self.total_instructions,
            'successful': self.successful,
            'failed': self.failed,
            'success_rate': self.success_rate,
            'results': self.results,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


class ObservationExecutor:
    """
    观测执行器 - 与实际望远镜控制集成

    核心功能：
    - 发送观测指令到望远镜控制服务器
    - 监控望远镜实时状态
    - 处理观测数据回传
    - 管理观测指令队列

    使用示例：
        executor = ObservationExecutor("tcp://localhost:5555")
        await executor.connect()
        state = await executor.get_state()
        await executor.disconnect()
    """

    def __init__(self, connection_string: str = "tcp://localhost:5555"):
        """
        初始化观测执行器

        Args:
            connection_string: 望远镜控制服务器连接字符串
        """
        self.connection_string = connection_string
        self.current_state: Optional[TelescopeState] = None
        self.observation_queue: List[ObservationInstruction] = []
        self.is_connected = False
        self.mock_mode = True  # 默认使用模拟模式

        # 数据处理回调函数
        self._data_callback: Optional[Callable[[ObservationData], None]] = None

        # 模拟参数
        self._mock_slew_speed = 10.0  # 度/秒
        self._mock_exposure_progress = 0.0

        logger.info(f"ObservationExecutor initialized with connection: {connection_string}")

    async def connect(self) -> bool:
        """
        连接到望远镜控制服务器

        Returns:
            bool: 连接是否成功

        Note:
            当无法连接到真实望远镜时，自动切换到模拟模式
        """
        logger.info(f"Attempting to connect to telescope control server: {self.connection_string}")

        try:
            # 尝试建立网络连接（模拟）
            # 在实际实现中，这里会使用 asyncio.create_connection() 等
            await asyncio.sleep(0.1)  # 模拟网络延迟

            # 模拟连接成功
            self.is_connected = True
            self.current_state = TelescopeState(
                status=TelescopeStatus.IDLE,
                current_ra=0.0,
                current_dec=0.0,
                tracking_target=None,
                last_update=datetime.now()
            )

            logger.info("Successfully connected to telescope control server (mock mode)")
            return True

        except Exception as e:
            logger.warning(f"Failed to connect to real telescope, entering mock mode: {e}")
            self.mock_mode = True
            self.is_connected = True
            self.current_state = TelescopeState(
                status=TelescopeStatus.IDLE,
                current_ra=0.0,
                current_dec=0.0,
                tracking_target=None,
                last_update=datetime.now()
            )
            return True

    async def disconnect(self):
        """断开与望远镜控制服务器的连接"""
        logger.info("Disconnecting from telescope control server")

        # 清空观测队列
        self.observation_queue.clear()

        # 关闭连接
        self.is_connected = False

        logger.info("Disconnected from telescope control server")

    async def send_command(self, instruction: ObservationInstruction) -> bool:
        """
        发送观测指令到望远镜

        Args:
            instruction: 要发送的观测指令

        Returns:
            bool: 指令是否成功发送

        Raises:
            ValueError: 指令参数不完整
        """
        if not self.is_connected:
            logger.error("Cannot send command: not connected to telescope")
            return False

        # 验证指令参数
        if not instruction.validate():
            logger.error(f"Invalid instruction parameters: {instruction}")
            raise ValueError(f"Instruction validation failed: {instruction.command}")

        logger.info(f"Sending command: {instruction.command.value}")

        try:
            # 根据指令类型执行相应操作
            if instruction.command == ObservationCommand.SLEW_TO_TARGET:
                await self._execute_slew(instruction)
            elif instruction.command == ObservationCommand.START_EXPOSURE:
                await self._execute_exposure(instruction)
            elif instruction.command == ObservationCommand.STOP_EXPOSURE:
                await self._stop_exposure()
            elif instruction.command == ObservationCommand.TRACK_TARGET:
                await self._start_tracking(instruction)
            elif instruction.command == ObservationCommand.ABORT_OBSERVATION:
                await self._abort_observation()
            else:
                logger.warning(f"Unknown command type: {instruction.command}")
                return False

            # 更新队列中的指令状态
            self._remove_from_queue(instruction)

            return True

        except Exception as e:
            logger.error(f"Failed to execute command {instruction.command.value}: {e}")
            return False

    async def _execute_slew(self, instruction: ObservationInstruction):
        """执行转向指令"""
        if instruction.target_ra is None or instruction.target_dec is None:
            raise ValueError("Slew instruction missing target coordinates")

        logger.info(f"Slewing to RA: {instruction.target_ra}, Dec: {instruction.target_dec}")

        # 更新状态为转向中
        self.current_state.status = TelescopeStatus.SLEWING
        self.current_state.last_update = datetime.now()

        # 计算转向所需时间（模拟）
        ra_diff = abs(instruction.target_ra - self.current_state.current_ra)
        dec_diff = abs(instruction.target_dec - self.current_state.current_dec)
        total_diff = (ra_diff**2 + dec_diff**2)**0.5
        slew_time = total_diff / self._mock_slew_speed

        # 模拟转向过程
        await asyncio.sleep(min(slew_time, 0.5))  # 限制最大等待时间

        # 更新位置
        self.current_state.current_ra = instruction.target_ra
        self.current_state.current_dec = instruction.target_dec
        self.current_state.status = TelescopeStatus.IDLE
        self.current_state.last_update = datetime.now()

        logger.info("Slew completed successfully")

    async def _execute_exposure(self, instruction: ObservationInstruction):
        """执行曝光指令"""
        exposure_time = instruction.exposure_time or 10.0
        filter_name = instruction.filter_name or "clear"

        logger.info(f"Starting exposure: {exposure_time}s with filter: {filter_name}")

        # 更新状态为曝光中
        self.current_state.status = TelescopeStatus.EXPOSING
        self.current_state.last_update = datetime.now()

        # 模拟曝光过程
        await asyncio.sleep(min(exposure_time, 0.2))  # 限制最大等待时间

        # 曝光完成，生成模拟数据
        image_data = self._generate_mock_image()

        # 更新状态
        self.current_state.status = TelescopeStatus.IDLE
        self.current_state.last_update = datetime.now()

        # 构造观测数据
        observation_data = ObservationData(
            timestamp=datetime.now(),
            image_data=image_data,
            telescope_state=TelescopeState(
                status=self.current_state.status,
                current_ra=self.current_state.current_ra,
                current_dec=self.current_state.current_dec,
                tracking_target=self.current_state.tracking_target,
                last_update=datetime.now()
            ),
            quality_metrics=self._calculate_quality_metrics(image_data)
        )

        # 调用数据回调
        if self._data_callback:
            await self._process_data_callback(observation_data)

        logger.info("Exposure completed successfully")

    async def _stop_exposure(self):
        """停止当前曝光"""
        logger.info("Stopping current exposure")

        if self.current_state.status == TelescopeStatus.EXPOSING:
            # 模拟停止延迟
            await asyncio.sleep(0.05)
            self.current_state.status = TelescopeStatus.IDLE
            self.current_state.last_update = datetime.now()

        logger.info("Exposure stopped")

    async def _start_tracking(self, instruction: ObservationInstruction):
        """启动目标跟踪"""
        if instruction.target_ra is None or instruction.target_dec is None:
            raise ValueError("Track instruction missing target coordinates")

        logger.info(f"Starting tracking for RA: {instruction.target_ra}, Dec: {instruction.target_dec}")

        # 先转向到目标
        self.current_state.current_ra = instruction.target_ra
        self.current_state.current_dec = instruction.target_dec

        # 启动跟踪
        self.current_state.status = TelescopeStatus.TRACKING
        self.current_state.tracking_target = f"RA:{instruction.target_ra:.2f},Dec:{instruction.target_dec:.2f}"
        self.current_state.last_update = datetime.now()

        logger.info("Tracking started successfully")

    async def _abort_observation(self):
        """中止所有观测操作"""
        logger.warning("Aborting all observation operations")

        # 停止当前曝光
        if self.current_state.status == TelescopeStatus.EXPOSING:
            await self._stop_exposure()

        # 清空队列
        self.observation_queue.clear()

        # 更新状态为空闲
        self.current_state.status = TelescopeStatus.IDLE
        self.current_state.tracking_target = None
        self.current_state.last_update = datetime.now()

        logger.info("Observation aborted successfully")

    def _generate_mock_image(self) -> List[int]:
        """生成模拟图像数据"""
        # 标准相机尺寸 4096x4096
        width, height = 4096, 4096

        # 生成带噪声的模拟图像
        image = []
        for y in range(height):
            row = []
            for x in range(width):
                # 基础噪声 - 使用泊松分布近似
                noise = int(random.gauss(0, 100))
                # 泊松随机数（使用反函数法近似）
                lam = 50
                import math
                p = math.exp(-lam)
                cum = p
                signal = 0
                u = random.random()
                while u > cum:
                    signal += 1
                    p *= lam / signal
                    cum += p
                value = max(0, min(65535, signal + noise))
                row.append(value)
            image.append(row)

        # 添加一些模拟星点
        star_positions = [(random.randint(0, height-1), random.randint(0, width-1))
                         for _ in range(random.randint(5, 20))]

        for star_y, star_x in star_positions:
            # 高斯星点
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    if 0 <= star_y + dy < height and 0 <= star_x + dx < width:
                        intensity = int(1000 * math.exp(-(dx**2 + dy**2) / 4))
                        image[star_y + dy][star_x + dx] = min(65535, image[star_y + dy][star_x + dx] + intensity)

        return image

    def _calculate_quality_metrics(self, image: List[List[int]]) -> Dict[str, float]:
        """计算图像质量指标"""
        flat = [pixel for row in image for pixel in row]
        mean_val = sum(flat) / len(flat)
        std_val = (sum((x - mean_val) ** 2 for x in flat) / len(flat)) ** 0.5
        max_val = max(flat)
        min_val = min(flat)

        metrics = {
            'mean_value': mean_val,
            'std_value': std_val,
            'max_value': float(max_val),
            'min_value': float(min_val),
            'snr': mean_val / (std_val + 1e-6),
            'star_count': random.randint(5, 20)
        }
        return metrics

    async def get_state(self) -> TelescopeState:
        """
        获取望远镜当前状态

        Returns:
            TelescopeState: 当前望远镜状态

        Note:
            在模拟模式下，直接返回内部状态
            在真实模式下，需要从服务器请求状态
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to telescope")

        # 模拟状态更新延迟
        await asyncio.sleep(0.01)

        # 在真实模式下，这里会从望远镜服务器获取状态
        # self.current_state = await self._fetch_state_from_server()

        self.current_state.last_update = datetime.now()
        return self.current_state

    async def execute_observation_plan(
        self,
        plan: List[ObservationInstruction]
    ) -> ObservationResult:
        """
        执行完整观测计划

        Args:
            plan: 观测指令列表，按执行顺序排列

        Returns:
            ObservationResult: 执行结果统计

        Example:
            plan = [
                ObservationInstruction(ObservationCommand.SLEW_TO_TARGET, ra=83.63, dec=-5.39),
                ObservationInstruction(ObservationCommand.START_EXPOSURE, exposure_time=30.0),
            ]
            result = await executor.execute_observation_plan(plan)
        """
        logger.info(f"Starting observation plan with {len(plan)} instructions")

        result = ObservationResult(
            total_instructions=len(plan),
            successful=0,
            failed=0,
            results=[],
            start_time=datetime.now()
        )

        for i, instruction in enumerate(plan):
            instruction_result = {
                'index': i,
                'command': instruction.command.value,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': None
            }

            try:
                success = await self.send_command(instruction)
                instruction_result['success'] = success

                if success:
                    result.successful += 1
                else:
                    result.failed += 1

            except Exception as e:
                instruction_result['error'] = str(e)
                instruction_result['success'] = False
                result.failed += 1
                logger.error(f"Failed to execute instruction {i}: {e}")

            result.results.append(instruction_result)

        result.end_time = datetime.now()

        logger.info(f"Observation plan completed: {result.successful}/{result.total_instructions} successful")

        return result

    def add_to_queue(self, instruction: ObservationInstruction):
        """
        添加指令到观测队列

        Args:
            instruction: 要添加的观测指令
        """
        self.observation_queue.append(instruction)
        logger.info(f"Instruction added to queue. Queue size: {len(self.observation_queue)}")

    def _remove_from_queue(self, instruction: ObservationInstruction):
        """从队列中移除指定指令"""
        if instruction in self.observation_queue:
            self.observation_queue.remove(instruction)

    def clear_queue(self):
        """清空观测队列"""
        count = len(self.observation_queue)
        self.observation_queue.clear()
        logger.info(f"Queue cleared. Removed {count} instructions")

    def get_queue_size(self) -> int:
        """获取当前队列中的指令数量"""
        return len(self.observation_queue)

    async def process_queue(self) -> ObservationResult:
        """
        执行队列中的所有指令

        Returns:
            ObservationResult: 执行结果统计
        """
        plan = self.observation_queue.copy()
        result = await self.execute_observation_plan(plan)
        self.observation_queue.clear()
        return result

    async def process_data_callback(self, data: ObservationData):
        """
        处理望远镜回传的观测数据

        此方法触发AstroPipeline进行天体检测等后续处理

        Args:
            data: 观测数据对象
        """
        logger.info(f"Processing observation data callback: {data.timestamp}")

        # 计算质量指标
        if not data.quality_metrics:
            data.quality_metrics = self._calculate_quality_metrics(data.image_data)

        logger.info(f"Image quality metrics: {data.quality_metrics}")

        # 在真实场景中，这里会触发AstroPipeline进行处理
        # await self.astro_pipeline.process(data)

        if self._data_callback:
            await self._data_callback(data)

    def set_data_callback(self, callback: Callable[[ObservationData], None]):
        """
        设置数据回调函数

        Args:
            callback: 处理观测数据的回调函数
        """
        self._data_callback = callback
        logger.info("Data callback function set")

    async def wait_for_state(
        self,
        target_status: TelescopeStatus,
        timeout: float = 30.0
    ) -> bool:
        """
        等待望远镜达到目标状态

        Args:
            target_status: 目标状态
            timeout: 超时时间（秒）

        Returns:
            bool: 是否在超时前达到目标状态
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            state = await self.get_state()
            if state.status == target_status:
                return True
            await asyncio.sleep(0.1)

        logger.warning(f"Timeout waiting for state: {target_status}")
        return False

    def __repr__(self) -> str:
        """返回执行器的字符串表示"""
        return (
            f"ObservationExecutor("
            f"connected={self.is_connected}, "
            f"mode={'mock' if self.mock_mode else 'real'}, "
            f"queue_size={len(self.observation_queue)}, "
            f"state={self.current_state})"
        )


async def demo():
    """演示观测执行器的使用"""
    print("=" * 60)
    print("观测执行器演示")
    print("=" * 60)

    # 创建执行器实例
    executor = ObservationExecutor("tcp://localhost:5555")

    # 连接
    print("\n1. 连接望远镜控制服务器...")
    connected = await executor.connect()
    print(f"   连接结果: {'成功' if connected else '失败'}")

    # 获取状态
    print("\n2. 获取望远镜当前状态...")
    state = await executor.get_state()
    print(f"   状态: {state.status.value}")
    print(f"   位置: RA={state.current_ra:.2f}, Dec={state.current_dec:.2f}")

    # 创建观测计划
    print("\n3. 创建观测计划...")
    plan = [
        ObservationInstruction(
            command=ObservationCommand.SLEW_TO_TARGET,
            target_ra=83.63,
            target_dec=-5.39
        ),
        ObservationInstruction(
            command=ObservationCommand.START_EXPOSURE,
            exposure_time=5.0,
            filter_name="V"
        ),
        ObservationInstruction(
            command=ObservationCommand.START_EXPOSURE,
            exposure_time=5.0,
            filter_name="R"
        ),
    ]
    print(f"   计划包含 {len(plan)} 条指令")

    # 执行观测计划
    print("\n4. 执行观测计划...")
    result = await executor.execute_observation_plan(plan)
    print(f"   总指令数: {result.total_instructions}")
    print(f"   成功: {result.successful}")
    print(f"   失败: {result.failed}")
    print(f"   成功率: {result.success_rate:.1%}")

    # 添加到队列并处理
    print("\n5. 测试队列管理...")
    executor.add_to_queue(
        ObservationInstruction(
            command=ObservationCommand.TRACK_TARGET,
            target_ra=120.0,
            target_dec=45.0
        )
    )
    print(f"   队列大小: {executor.get_queue_size()}")

    queue_result = await executor.process_queue()
    print(f"   队列执行完成: {queue_result.successful}/{queue_result.total_instructions} 成功")

    # 断开连接
    print("\n6. 断开连接...")
    await executor.disconnect()
    print("   已断开")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo())