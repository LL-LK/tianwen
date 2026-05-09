"""
telescope_simulator.py - 望远镜模拟器

完整模拟望远镜控制流程，为Plan A（实践准备）提供完整的操作练习环境。

功能:
- 模拟Seestar S50望远镜的完整控制流程
- GOTO指向、跟踪、曝光控制
- Plate Solving (星图匹配定位)
- 状态上报、错误处理
- 观测窗口计算

Author: Tianwen-AGI
参考: seestar-mcp, INDI Protocol
"""

import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class TelescopeStatus(Enum):
    """望远镜状态"""
    IDLE = "idle"
    GOTO_IN_PROGRESS = "goto_in_progress"
    TRACKING = "tracking"
    EXPOSING = "exposing"
    PARKING = "parking"
    ERROR = "error"


class MountType(Enum):
    """望远镜类型"""
    SEESTAR_S50 = "seestar_s50"
    GENERIC = "generic"


@dataclass
class Coordinates:
    """天球坐标"""
    ra: float      # 赤经 (度, 0-360)
    dec: float     # 赤纬 (度, -90到+90)
    
    def __str__(self):
        return f"RA={self.ra:.4f}°, Dec={self.dec:.4f}°"
    
    def to_equatorial(self) -> Dict[str, float]:
        """转为赤道坐标字典"""
        # 转换为时角格式
        ra_hours = self.ra / 15.0
        ra_min = (ra_hours % 1) * 60
        ra_sec = (ra_min % 1) * 60
        return {
            "ra_hms": f"{int(ra_hours):02d}h {int(ra_min):02d}m {ra_sec:.1f}s",
            "dec_dms": f"{'+' if self.dec >= 0 else ''}{self.dec:.4f}°"
        }


@dataclass
class TelescopeState:
    """望远镜完整状态"""
    status: TelescopeStatus = TelescopeStatus.IDLE
    current_coords: Coordinates = field(default_factory=lambda: Coordinates(0, 0))
    target_coords: Optional[Coordinates] = None
    pointing_error: float = 0.0  # 指向误差(角分)
    tracking_enabled: bool = False
    exposure_count: int = 0
    total_exposure_time: float = 0.0  # 秒
    last_error: str = ""
    uptime_hours: float = 0.0
    temperature: float = 20.0  # 摄氏度
    humidity: int = 50  # 百分比
    battery_level: int = 100  # 百分比
    

@dataclass  
class ImagingResult:
    """成像结果"""
    timestamp: str
    target_name: str
    exposure_sec: float
    frame_count: int
    image_data_base64: str  # 模拟图像数据
    file_path: str
    success: bool
    error_msg: str = ""


class TelescopeSimulator:
    """
    望远镜模拟器
    
    完整模拟Seestar S50望远镜的操作流程，包括:
    1. 连接/断开
    2. GOTO指向
    3. Plate Solving校准
    4. 跟踪控制
    5. 曝光成像
    6. 状态监控
    
    使用示例:
        sim = TelescopeSimulator()
        await sim.connect()
        await sim.goto("M31")
        await sim.start_tracking()
        result = await sim.expose(exposure=30, count=5)
        await sim.park()
    """
    
    # Seestar S50 规格参数
    SPECS = {
        "aperture": 50,           # mm
        "focal_length": 250,      # mm
        "f_ratio": 5.0,
        "sensor": "IMX462",       # 索尼星光摄
        "resolution": "1920x1080",  # pixels
        "pixel_size": 2.9,        # microns
        "mount_type": "alt-az",   # 目地式支架
        "weight": 2.5,            # kg
        "max_goto_speed": 5,      # deg/sec
    }
    
    # 内置目标星表 (与realtime_sky_chart.py共享)
    CATALOG = {
        "M31": {"ra": 10.6847, "dec": 41.2687, "name": "仙女座星系", "type": "galaxy", "mag": 3.4},
        "M42": {"ra": 83.8221, "dec": -5.3911, "name": "猎户座大星云", "type": "nebula", "mag": 4.0},
        "M51": {"ra": 202.4696, "dec": 47.1953, "name": "涡旋星系", "type": "galaxy", "mag": 8.4},
        "M81": {"ra": 148.8883, "dec": 69.0653, "name": "波德星系", "type": "galaxy", "mag": 6.9},
        "M101": {"ra": 210.8023, "dec": 54.3494, "name": "风车星系", "type": "galaxy", "mag": 7.9},
        "M104": {"ra": 189.9975, "dec": -11.6236, "name": "草帽星系", "type": "galaxy", "mag": 8.0},
        "M1":  {"ra": 83.6282, "dec": 22.0145, "name": "蟹状星云", "type": "nebula", "mag": 8.4},
        "M8":  {"ra": 270.9214, "dec": -24.3865, "name": "礁湖星云", "type": "nebula", "mag": 6.0},
        "M57": {"ra": 283.3961, "dec": 33.0285, "name": "环状星云", "type": "nebula", "mag": 8.8},
        "M13": {"ra": 250.4238, "dec": 36.4603, "name": "武仙座球状星团", "type": "globular_cluster", "mag": 5.8},
        "M45": {"ra": 56.8711, "dec": 24.1053, "name": "昴宿星团", "type": "cluster", "mag": 1.6},
        "NGC224": {"ra": 10.6847, "dec": 41.2687, "name": "仙女座星系", "type": "galaxy", "mag": 3.4},
        "NGC5139": {"ra": 201.2983, "dec": -47.4797, "name": "半人马座Omega", "type": "globular_cluster", "mag": 3.9},
        "NGC7000": {"ra": 314.6750, "dec": 44.3625, "name": "北美洲星云", "type": "nebula", "mag": 4.0},
    }
    
    def __init__(self, name: str = "Seestar S50", simulate_errors: bool = False):
        """
        初始化模拟器
        
        Args:
            name: 望远镜名称
            simulate_errors: 是否模拟错误（用于测试错误处理）
        """
        self.name = name
        self.simulate_errors = simulate_errors
        self.state = TelescopeState()
        self.connected = False
        self._running = False
        
        # 观测统计
        self.stats = {
            "total_gotos": 0,
            "total_exposures": 0,
            "total_frames": 0,
            "successful_slew": 0,
            "failed_slew": 0,
            "plate_solves": 0,
        }
    
    # ============ 连接控制 ============
    
    async def connect(self) -> bool:
        """
        连接望远镜模拟器
        
        Returns:
            bool: 连接是否成功
        """
        print(f"[{self.name}] 连接中...")
        await asyncio.sleep(1.0)  # 模拟连接延迟
        
        self.connected = True
        self.state = TelescopeState()
        self._running = True
        print(f"[{self.name}] 连接成功!")
        print(f"  型号: {self.name}")
        print(f"  规格: f/{self.SPECS['f_ratio']}, {self.SPECS['focal_length']}mm焦距")
        print(f"  传感器: {self.SPECS['sensor']} {self.SPECS['resolution'][0]}x{self.SPECS['resolution'][1]}")
        
        return True
    
    async def disconnect(self):
        """断开望远镜连接"""
        if self.state.status == TelescopeStatus.EXPOSING:
            print(f"[{self.name}] 曝光中，请先停止...")
            return False
        
        await self.park()
        self.connected = False
        self._running = False
        print(f"[{self.name}] 已断开连接")
        return True
    
    async def get_status(self) -> TelescopeState:
        """获取望远镜状态"""
        return self.state
    
    # ============ GOTO 控制 ============
    
    async def goto(self, target: str) -> bool:
        """
        GOTO指向目标
        
        Args:
            target: 目标名称(如M31)或坐标"RA,Dec"
            
        Returns:
            bool: 是否成功
        """
        if not self.connected:
            print(f"[{self.name}] 未连接!")
            return False
        
        # 解析目标
        coords = self._parse_target(target)
        if coords is None:
            print(f"[{self.name}] 无法识别目标: {target}")
            return False
        
        self.state.target_coords = coords
        self.state.status = TelescopeStatus.GOTO_IN_PROGRESS
        
        print(f"[{self.name}] GOTO: {target}")
        print(f"  目标坐标: {coords}")
        
        # 计算角距离
        if self.state.current_coords:
            sep = self._angular_separation(
                self.state.current_coords.ra, self.state.current_coords.dec,
                coords.ra, coords.dec
            )
            print(f"  角距离: {sep:.2f}°")
            
            # 估算转动时间 (最大5°/秒)
            slew_time = min(sep / self.SPECS["max_goto_speed"], 30)
        else:
            slew_time = 3.0
        
        print(f"  预计转动时间: {slew_time:.1f}秒")
        
        # 模拟转动过程
        for i in range(int(slew_time * 2)):
            await asyncio.sleep(0.5)
            progress = (i + 1) / (slew_time * 2)
            
            # 模拟在转动过程中坐标逐渐接近目标
            self.state.current_coords = Coordinates(
                ra=self._lerp(self.state.current_coords.ra if self.state.current_coords else 0, coords.ra, progress),
                dec=self._lerp(self.state.current_coords.dec if self.state.current_coords else 0, coords.dec, progress)
            )
            
            if i % 4 == 0:
                print(f"  进度: {progress*100:.0f}% - {self.state.current_coords}")
        
        # 完成GOTO
        self.state.current_coords = coords
        self.state.status = TelescopeStatus.IDLE
        self.state.pointing_error = random.uniform(0.1, 2.0)  # 模拟指向误差
        
        self.stats["total_gotos"] += 1
        self.stats["successful_slew"] += 1
        
        print(f"[{self.name}] GOTO完成! 指向误差: {self.state.pointing_error:.2f}'")
        
        # 模拟错误
        if self.simulate_errors and random.random() < 0.1:
            self.state.last_error = "GOTO限位触发"
            self.state.status = TelescopeStatus.ERROR
            self.stats["failed_slew"] += 1
            return False
        
        return True
    
    async def abort_goto(self):
        """中断GOTO"""
        if self.state.status == TelescopeStatus.GOTO_IN_PROGRESS:
            print(f"[{self.name}] 中断GOTO...")
            self.state.status = TelescopeStatus.IDLE
            self.stats["failed_slew"] += 1
            return True
        return False
    
    # ============ Plate Solving ============
    
    async def plate_solve(self) -> Optional[Dict[str, float]]:
        """
        执行Plate Solving (星图匹配定位)
        
        确定当前指向的精确坐标，用于校准GOTO误差。
        
        Returns:
            Dict: 包含ra, dec, rotation, scale等校准参数，失败返回None
        """
        if not self.connected:
            return None
        
        print(f"[{self.name}] Plate Solving...")
        
        # 模拟曝光获取星图
        await asyncio.sleep(2.0)
        
        # 模拟成功/失败 (95%成功率)
        if self.simulate_errors and random.random() < 0.05:
            print(f"[{self.name}] Plate Solving 失败: 星图匹配失败")
            return None
        
        # 计算实际指向误差
        error_ra = random.uniform(-0.01, 0.01)  # 度
        error_dec = random.uniform(-0.01, 0.01)
        
        # 视场角 (度)
        res_parts = self.SPECS["resolution"].split("x")
        sensor_width_pixels = float(res_parts[0])
        fov = (sensor_width_pixels * self.SPECS["pixel_size"] / 1000) / self.SPECS["focal_length"] * 57.3
        
        result = {
            "ra": self.state.current_coords.ra + error_ra,
            "dec": self.state.current_coords.dec + error_dec,
            "rotation": random.uniform(-5, 5),
            "scale": fov,
            "stars_matched": random.randint(15, 50),
            "solve_time": random.uniform(1.5, 3.0),
            "rms_error": random.uniform(0.5, 2.0),  # 角秒
        }
        
        # 更新状态
        self.state.current_coords = Coordinates(ra=result["ra"], dec=result["dec"])
        self.state.pointing_error = result["rms_error"] / 60.0  # 转换为角分
        
        self.stats["plate_solves"] += 1
        
        print(f"[{self.name}] Plate Solving 完成!")
        print(f"  匹配星数: {result['stars_matched']}")
        print(f"  RMS误差: {result['rms_error']:.2f}\"")
        print(f"  校准后坐标: {self.state.current_coords}")
        
        return result
    
    async def sync_coordinates(self, ra: float, dec: float):
        """
        同步坐标（手动校准）
        
        Args:
            ra: 正确的赤经
            dec: 正确的赤纬
        """
        print(f"[{self.name}] 同步坐标: RA={ra}, Dec={dec}")
        self.state.current_coords = Coordinates(ra=ra, dec=dec)
        self.state.pointing_error = 0.0
        print(f"[{self.name}] 坐标同步完成")
        return True
    
    # ============ 跟踪控制 ============
    
    async def start_tracking(self) -> bool:
        """
        开始跟踪
        
        Returns:
            bool: 是否成功
        """
        if self.state.status == TelescopeStatus.GOTO_IN_PROGRESS:
            print(f"[{self.name}] GOTO进行中，请等待")
            return False
        
        print(f"[{self.name}] 开始跟踪: {self.state.current_coords}")
        self.state.tracking_enabled = True
        self.state.status = TelescopeStatus.TRACKING
        
        # 模拟跟踪漂移
        asyncio.create_task(self._tracking_drift())
        
        return True
    
    async def stop_tracking(self):
        """停止跟踪"""
        self.state.tracking_enabled = False
        self.state.status = TelescopeStatus.IDLE
        print(f"[{self.name}] 停止跟踪")
    
    async def _tracking_drift(self):
        """模拟跟踪漂移"""
        while self.state.tracking_enabled and self._running:
            await asyncio.sleep(10)
            
            if self.state.tracking_enabled:
                # 模拟微小的漂移
                drift_ra = random.uniform(-0.0001, 0.0001)  # 度/10秒
                drift_dec = random.uniform(-0.0001, 0.0001)
                
                new_ra = self.state.current_coords.ra + drift_ra
                new_dec = self.state.current_coords.dec + drift_dec
                
                self.state.current_coords = Coordinates(ra=new_ra, dec=new_dec)
                
                # 更新指向误差
                self.state.pointing_error += abs(drift_ra) * 60  # 转换为角分
    
    # ============ 曝光成像 ============
    
    async def expose(
        self, 
        exposure: float = 30.0, 
        count: int = 1,
        target: Optional[str] = None
    ) -> ImagingResult:
        """
        执行曝光成像
        
        Args:
            exposure: 单帧曝光时间(秒)
            count: 帧数
            target: 目标名称(可选)
            
        Returns:
            ImagingResult: 成像结果
        """
        if not self.connected:
            return ImagingResult(
                timestamp=datetime.now().isoformat(),
                target_name=target or "unknown",
                exposure_sec=exposure,
                frame_count=0,
                image_data_base64="",
                file_path="",
                success=False,
                error_msg="未连接"
            )
        
        self.state.status = TelescopeStatus.EXPOSING
        print(f"[{self.name}] 开始曝光: {exposure}秒 x {count}帧")
        
        # 如果没有指定目标，从当前坐标查找最近的目标
        if target is None and self.state.current_coords:
            target = self._find_nearest_target()
        
        timestamp = datetime.now().isoformat()
        frames = []
        
        for i in range(count):
            print(f"  帧 {i+1}/{count}...", end="", flush=True)
            
            # 模拟曝光时间
            await asyncio.sleep(min(exposure, 5.0))  # 最大模拟5秒
            
            # 生成模拟图像数据 (简化的base64小图像)
            frame = self._generate_simulated_frame(exposure, i)
            frames.append(frame)
            
            self.stats["total_frames"] += 1
            self.state.exposure_count += 1
            self.state.total_exposure_time += exposure
            
            print(f" 完成")
        
        self.state.status = TelescopeStatus.TRACKING if self.state.tracking_enabled else TelescopeStatus.IDLE
        
        # 合并帧 (这里简化处理)
        combined = frames[0] if frames else ""
        
        result = ImagingResult(
            timestamp=timestamp,
            target_name=target or "unknown",
            exposure_sec=exposure,
            frame_count=count,
            image_data_base64=combined,
            file_path=f"/captures/{target or 'unknown'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fits",
            success=True
        )
        
        self.stats["total_exposures"] += 1
        
        print(f"[{self.name}] 曝光完成: {count}帧, 保存至 {result.file_path}")
        
        return result
    
    def _generate_simulated_frame(self, exposure: float, frame_num: int) -> str:
        """生成模拟帧数据 (返回简化的base64图像描述)"""
        import base64
        
        # 简化的图像头信息
        header = f"SIMDATA: exposure={exposure}s frame={frame_num} time={datetime.now().isoformat()}".encode()
        return base64.b64encode(header).decode()
    
    async def cancel_exposure(self):
        """取消当前曝光"""
        if self.state.status == TelescopeStatus.EXPOSING:
            print(f"[{self.name}] 取消曝光...")
            self.state.status = TelescopeStatus.IDLE
            return True
        return False
    
    # ============ 望远镜停车 ============
    
    async def park(self) -> bool:
        """
        望远镜停车 (归位)
        
        Returns:
            bool: 是否成功
        """
        if self.state.tracking_enabled:
            await self.stop_tracking()
        
        if self.state.status == TelescopeStatus.EXPOSING:
            await self.cancel_exposure()
        
        print(f"[{self.name}] 望远镜归位中...")
        self.state.status = TelescopeStatus.PARKING
        
        await asyncio.sleep(2.0)
        
        self.state.status = TelescopeStatus.IDLE
        print(f"[{self.name}] 望远镜已归位")
        
        return True
    
    # ============ 工具方法 ============
    
    def _parse_target(self, target: str) -> Optional[Coordinates]:
        """解析目标字符串为坐标"""
        target = target.strip().upper()
        
        # 查星表
        if target in self.CATALOG:
            obj = self.CATALOG[target]
            return Coordinates(ra=obj["ra"], dec=obj["dec"])
        
        # 尝试解析为 RA,Dec 格式
        try:
            parts = target.replace(',', ' ').split()
            if len(parts) >= 2:
                ra = float(parts[0])
                dec = float(parts[1])
                return Coordinates(ra=ra, dec=dec)
        except ValueError:
            pass
        
        return None
    
    def _find_nearest_target(self) -> str:
        """查找最近的目标"""
        if not self.state.current_coords:
            return "unknown"
        
        min_sep = float('inf')
        nearest = "unknown"
        
        for name, obj in self.CATALOG.items():
            sep = self._angular_separation(
                self.state.current_coords.ra, self.state.current_coords.dec,
                obj["ra"], obj["dec"]
            )
            if sep < min_sep:
                min_sep = sep
                nearest = name
        
        return nearest
    
    @staticmethod
    def _angular_separation(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
        """计算角距离(度)"""
        ra1_rad = math.radians(ra1)
        dec1_rad = math.radians(dec1)
        ra2_rad = math.radians(ra2)
        dec2_rad = math.radians(dec2)
        
        cos_sep = (math.sin(dec1_rad) * math.sin(dec2_rad) + 
                   math.cos(dec1_rad) * math.cos(dec2_rad) * math.cos(ra2_rad - ra1_rad))
        cos_sep = max(-1.0, min(1.0, cos_sep))
        
        return math.degrees(math.acos(cos_sep))
    
    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        """线性插值"""
        return a + (b - a) * max(0, min(1, t))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "total_exposure_time": self.state.total_exposure_time,
            "current_status": self.state.status.value,
            "pointing_error_arcmin": self.state.pointing_error,
        }
    
    def __repr__(self):
        return f"TelescopeSimulator(name={self.name}, connected={self.connected}, status={self.state.status.value})"


# ============ 观测窗口计算 ============

def calculate_observation_window(
    target_ra: float, 
    target_dec: float,
    latitude: float = 40.0,  # 默认纬度
    start_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    计算目标的可观测窗口
    
    Args:
        target_ra: 目标赤经 (度)
        target_dec: 目标赤纬 (度)
        latitude: 观测地点纬度 (度)
        start_time: 开始时间 (默认当前时间)
        
    Returns:
        Dict: 包含升起时间、峰值时间、落下时间、最佳观测时段等
    """
    if start_time is None:
        start_time = datetime.now()
    
    # 简化计算: 假设恒星时=RA时，目标在子午线时达到最高点
    # 实际上需要更复杂的天文学计算，这里做简化模拟
    
    local_sidereal = (start_time.hour * 15 + start_time.minute * 0.25) % 360
    
    # 目标时角 = 当地恒星时 - 赤经
    hour_angle = (local_sidereal - target_ra + 360) % 360
    if hour_angle > 180:
        hour_angle -= 360
    
    # 升起/落下判断 (简化: 当高度 > 0时可见)
    # 高度 = arcsin(sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(HA))
    lat_rad = math.radians(latitude)
    dec_rad = math.radians(target_dec)
    ha_rad = math.radians(hour_angle)
    
    altitude = math.degrees(
        math.asin(max(-1, min(1, 
            math.sin(lat_rad) * math.sin(dec_rad) + 
            math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
        )))
    )
    
    # 模拟计算 (实际需要迭代计算)
    rise_time = start_time + timedelta(hours=(12 - hour_angle/15) % 24)
    set_time = start_time + timedelta(hours=(12 + hour_angle/15) % 24)
    transit_time = start_time + timedelta(hours=(360 - target_ra + local_sidereal)/15 % 24)
    
    return {
        "target_ra": target_ra,
        "target_dec": target_dec,
        "current_altitude": altitude,
        "is_visible": altitude > 20,
        "rise_time": rise_time.isoformat(),
        "transit_time": transit_time.isoformat(),
        "set_time": set_time.isoformat(),
        "best_window_start": (transit_time - timedelta(hours=2)).isoformat(),
        "best_window_end": (transit_time + timedelta(hours=2)).isoformat(),
        "max_altitude": 90 - abs(latitude - target_dec),  # 简化
    }


# ============ 测试/演示 ============

async def demo():
    """演示望远镜模拟器的完整操作流程"""
    print("=" * 60)
    print("望远镜模拟器演示 - Plan A 完整操作流程")
    print("=" * 60)
    
    sim = TelescopeSimulator()
    
    # 1. 连接
    print("\n[Step 1] 连接望远镜")
    await sim.connect()
    
    # 2. GOTO目标
    print("\n[Step 2] GOTO指向 M31 (仙女座星系)")
    await sim.goto("M31")
    
    # 3. Plate Solving校准
    print("\n[Step 3] Plate Solving校准")
    solve_result = await sim.plate_solve()
    if solve_result:
        print(f"  校准参数: RA={solve_result['ra']:.4f}, Dec={solve_result['dec']:.4f}")
    
    # 4. 开始跟踪
    print("\n[Step 4] 开始跟踪")
    await sim.start_tracking()
    
    # 5. 曝光成像
    print("\n[Step 5] 执行曝光成像")
    result = await sim.expose(exposure=10, count=3, target="M31")
    print(f"  成像结果: {'成功' if result.success else '失败'}")
    print(f"  保存路径: {result.file_path}")
    
    # 6. 观测窗口计算
    print("\n[Step 6] 计算M31观测窗口")
    obj = TelescopeSimulator.CATALOG["M31"]
    window = calculate_observation_window(obj["ra"], obj["dec"])
    print(f"  当前高度: {window['current_altitude']:.1f}°")
    print(f"  可见性: {'是' if window['is_visible'] else '否'}")
    print(f"  最佳时段: {window['best_window_start']} ~ {window['best_window_end']}")
    
    # 7. 停车
    print("\n[Step 7] 望远镜归位")
    await sim.park()
    
    # 8. 断开连接
    print("\n[Step 8] 断开连接")
    await sim.disconnect()
    
    # 统计
    print("\n" + "=" * 60)
    print("操作统计:")
    stats = sim.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
