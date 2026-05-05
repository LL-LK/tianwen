"""
realtime_observation_workflow.py - 真实API驱动的观测工作流

整合NASA SkyView实时星图API + 望远镜模拟器，形成完整的观测流程:

Phase 1: 目标规划 (Planning)
  - 查询目标坐标
  - 计算观测窗口
  - 评估可见性

Phase 2: 实时星图获取 (SkyChart)
  - 从NASA SkyView获取真实天文图像
  - 自动检测视场内的天体
  - 分析星图质量

Phase 3: 望远镜控制 (Telescope)
  - GOTO指向目标
  - Plate Solving校准
  - 开始跟踪

Phase 4: 成像采集 (Imaging)
  - 执行曝光序列
  - 实时数据处理
  - 保存观测数据

Author: Tianwen-AGI
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ObservationPhase(Enum):
    """观测阶段枚举"""
    PLANNING = "planning"
    SKYCHART = "skychart"
    TELESCOPE = "telescope"
    IMAGING = "imaging"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ObservationTarget:
    """观测目标"""
    name: str
    ra: float           # 赤经 (度)
    dec: float          # 赤纬 (度)
    catalog_name: str = ""   # 星表名称 (如M31)
    object_type: str = ""    # 天体类型
    magnitude: float = 99    # 视星等
    description: str = ""
    
    @property
    def ra_hms(self) -> str:
        """转换为时:分:秒格式"""
        ra_h = self.ra / 15.0
        h = int(ra_h)
        m = int((ra_h - h) * 60)
        s = ((ra_h - h) * 60 - m) * 60
        return f"{h:02d}h {m:02d}m {s:05.2f}s"
    
    @property
    def dec_dms(self) -> str:
        """转换为度:分:秒格式"""
        sign = '+' if self.dec >= 0 else '-'
        dec_abs = abs(self.dec)
        d = int(dec_abs)
        m = int((dec_abs - d) * 60)
        s = ((dec_abs - d) * 60 - m) * 60
        return f"{sign}{d:02d}d {m:02d}m {s:05.2f}s"


@dataclass
class ObservationResult:
    """完整观测结果"""
    target: ObservationTarget
    phases_completed: List[ObservationPhase]
    skychart_data: Optional[Dict] = None
    telescope_state: Optional[Dict] = None
    imaging_result: Optional[Dict] = None
    execution_time_seconds: float = 0.0
    success: bool = False
    error_message: str = ""
    metadata: Dict = field(default_factory=dict)


# ============ 导入依赖模块 ============

def _import_dependencies():
    """延迟导入依赖模块"""
    global SkyChartAPI
    
    try:
        from realtime_sky_chart import NASA_SkyView_API, parse_coordinates, BUILTIN_CATALOG
        SkyChartAPI = NASA_SkyView_API
        return True
    except ImportError:
        print("[RealtimeWorkflow] realtime_sky_chart not available")
        return False


def _import_telescope_simulator():
    """延迟导入望远镜模拟器"""
    try:
        from telescope_simulator import TelescopeSimulator, calculate_observation_window
        return TelescopeSimulator, calculate_observation_window
    except ImportError:
        print("[RealtimeWorkflow] telescope_simulator not available")
        return None, None


# ============ 实时观测工作流 ============

class RealtimeObservationWorkflow:
    """
    实时观测工作流
    
    串联NASA SkyView API和望远镜模拟器，实现完整的天文观测流程。
    
    使用示例:
        workflow = RealtimeObservationWorkflow()
        result = await workflow.run("M31", survey="DSS2/color", exposure=30, frames=5)
    """
    
    def __init__(self):
        self.telescope = None
        self.skychart_api = None
        self.observation_log: List[Dict] = []
        
        # 尝试初始化
        self._skychart_available = _import_dependencies()
        TelescopeSim, self._calc_window = _import_telescope_simulator()
        
        if TelescopeSim:
            self.telescope = TelescopeSim(name="Seestar S50 (Simulated)")
    
    async def run(
        self,
        target: str,
        survey: str = "DSS2/color",
        fov_arcmin: float = 15.0,
        exposure: float = 30.0,
        frames: int = 3,
        use_real_telescope: bool = False,
    ) -> ObservationResult:
        """
        执行完整观测工作流
        
        Args:
            target: 目标名称 (如M31)
            survey: 天空巡天调查
            fov_arcmin: 视场大小 (角分)
            exposure: 单帧曝光时间 (秒)
            frames: 曝光帧数
            use_real_telescope: 是否使用真实望远镜 (默认False，使用模拟器)
            
        Returns:
            ObservationResult: 观测结果
        """
        start_time = datetime.now()
        result = ObservationResult(
            target=ObservationTarget(name=target, ra=0, dec=0),
            phases_completed=[],
            execution_time_seconds=0.0
        )
        
        print("=" * 60)
        print(f"实时观测工作流启动: {target}")
        print(f"配置: survey={survey}, FOV={fov_arcmin}', exp={exposure}s x {frames}帧")
        print("=" * 60)
        
        # Phase 1: 目标规划
        print("\n[Phase 1] 目标规划")
        try:
            target_info = await self._planning_phase(target)
            result.target = target_info
            result.phases_completed.append(ObservationPhase.PLANNING)
            print(f"  目标: {target_info.catalog_name} ({target_info.object_type})")
            print(f"  坐标: RA={target_info.ra:.4f}, Dec={target_info.dec:.4f}")
            print(f"  坐标(格式化): {target_info.ra_hms}, {target_info.dec_dms}")
            print(f"  视星等: mag={target_info.magnitude}")
            
            # 计算观测窗口
            if self._calc_window:
                window = self._calc_window(target_info.ra, target_info.dec)
                print(f"  当前高度: {window['current_altitude']:.1f}°")
                print(f"  可见性: {'良好' if window['is_visible'] else '不可见'}")
        except Exception as e:
            result.error_message = f"规划阶段失败: {e}"
            result.phases_completed.append(ObservationPhase.FAILED)
            return result
        
        # Phase 2: 获取真实星图
        print("\n[Phase 2] 获取NASA SkyView真实星图")
        try:
            skychart = await self._skychart_phase(target, survey, fov_arcmin)
            result.skychart_data = skychart
            result.phases_completed.append(ObservationPhase.SKYCHART)
            print(f"  获取成功: {survey}")
            print(f"  图像尺寸: {skychart.get('width', 0)}x{skychart.get('height', 0)}")
            print(f"  视场: {skychart.get('fov_deg', 0):.2f}°")
            
            sources = skychart.get('catalog_sources', [])
            print(f"  检测到 {len(sources)} 个天体")
            for src in sources[:5]:
                print(f"    - {src['name']} ({src['catalog_id']}) mag={src['mag']}")
                
        except Exception as e:
            print(f"  星图获取失败: {e}")
            result.error_message = f"星图获取失败: {e}"
            # 星图失败不终止工作流，继续望远镜阶段
        
        # Phase 3: 望远镜控制
        print("\n[Phase 3] 望远镜控制")
        try:
            if self.telescope:
                telescope_state = await self._telescope_phase(target, result.target)
                result.telescope_state = telescope_state
                result.phases_completed.append(ObservationPhase.TELESCOPE)
                print(f"  望远镜状态: {telescope_state.get('status', 'unknown')}")
                print(f"  当前坐标: RA={telescope_state.get('ra', 0):.4f}, Dec={telescope_state.get('dec', 0):.4f}")
            else:
                print("  望远镜模拟器不可用，跳过")
        except Exception as e:
            print(f"  望远镜控制失败: {e}")
            # 望远镜失败不终止
        
        # Phase 4: 成像采集
        print("\n[Phase 4] 成像采集")
        try:
            if self.telescope:
                imaging = await self._imaging_phase(exposure, frames, target)
                result.imaging_result = imaging
                result.phases_completed.append(ObservationPhase.IMAGING)
                print(f"  成像结果: {'成功' if imaging.get('success') else '失败'}")
                print(f"  保存路径: {imaging.get('file_path', 'N/A')}")
            else:
                print("  望远镜不可用，跳过成像")
        except Exception as e:
            print(f"  成像失败: {e}")
        
        result.phases_completed.append(ObservationPhase.COMPLETE)
        result.success = True
        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print(f"观测完成! 耗时: {result.execution_time_seconds:.1f}秒")
        print("=" * 60)
        
        return result
    
    async def _planning_phase(self, target_name: str) -> ObservationTarget:
        """Phase 1: 目标规划"""
        from realtime_sky_chart import BUILTIN_CATALOG, parse_coordinates
        
        # 解析坐标
        coords = parse_coordinates(target_name)
        if coords is None:
            raise ValueError(f"无法解析目标: {target_name}")
        
        ra, dec = coords
        
        # 查找星表信息
        catalog_info = BUILTIN_CATALOG.get(target_name.upper(), {})
        
        return ObservationTarget(
            name=target_name,
            ra=ra,
            dec=dec,
            catalog_name=catalog_info.get("name", target_name),
            object_type=catalog_info.get("type", "unknown"),
            magnitude=catalog_info.get("mag", 99),
            description=f"{catalog_info.get('name', '')} - {catalog_info.get('type', '')}"
        )
    
    async def _skychart_phase(
        self, 
        target: str, 
        survey: str, 
        fov_arcmin: float
    ) -> Dict:
        """Phase 2: 获取真实星图"""
        from realtime_sky_chart import get_realtime_skychart, SkySurvey
        
        try:
            sky_survey = SkySurvey(survey)
        except ValueError:
            sky_survey = SkySurvey.DSS2_COLOR
        
        result = await get_realtime_skychart(
            target=target,
            survey=sky_survey,
            size=fov_arcmin,
            pixels=800,
            use_cache=True
        )
        
        return {
            "target": result.target,
            "survey": result.survey,
            "ra": result.ra,
            "dec": result.dec,
            "width": result.width,
            "height": result.height,
            "fov_deg": result.fov,
            "image_base64": result.image_base64[:100] + "...",  # 截断保存
            "image_url": result.image_url,
            "timestamp": result.timestamp,
            "cached": result.cached,
            "catalog_sources": result.catalog_sources,
            "sources_count": len(result.catalog_sources)
        }
    
    async def _telescope_phase(self, target: str, target_info: ObservationTarget) -> Dict:
        """Phase 3: 望远镜控制"""
        if not self.telescope:
            return {"status": "unavailable"}
        
        # 连接望远镜
        if not self.telescope.connected:
            await self.telescope.connect()
        
        # GOTO指向
        success = await self.telescope.goto(target)
        if not success:
            return {"status": "goto_failed", "ra": 0, "dec": 0}
        
        # Plate Solving
        solve_result = await self.telescope.plate_solve()
        
        # 开始跟踪
        await self.telescope.start_tracking()
        
        state = self.telescope.state
        
        return {
            "status": "tracking",
            "ra": state.current_coords.ra,
            "dec": state.current_coords.dec,
            "pointing_error_arcmin": state.pointing_error,
            "tracking_enabled": state.tracking_enabled,
            "plate_solve_stars": solve_result.get("stars_matched", 0) if solve_result else 0,
            "telescope_connected": self.telescope.connected,
            "telescope_specs": self.telescope.SPECS if self.telescope else {}
        }
    
    async def _imaging_phase(
        self, 
        exposure: float, 
        frames: int, 
        target: str
    ) -> Dict:
        """Phase 4: 成像采集"""
        if not self.telescope:
            return {"success": False, "error": "telescope unavailable"}
        
        result = await self.telescope.expose(
            exposure=exposure,
            count=frames,
            target=target
        )
        
        return {
            "success": result.success,
            "target": result.target_name,
            "exposure_sec": result.exposure_sec,
            "frame_count": result.frame_count,
            "file_path": result.file_path,
            "timestamp": result.timestamp,
            "error": result.error_msg
        }
    
    async def shutdown(self):
        """关闭工作流，清理资源"""
        if self.telescope:
            await self.telescope.park()
            await self.telescope.disconnect()
        print("[RealtimeWorkflow] 已关闭")


# ============ 批量观测 ============

async def batch_observation(
    targets: List[str],
    survey: str = "DSS2/color",
    fov_arcmin: float = 15.0,
    exposure: float = 30.0,
    frames: int = 3
) -> Dict[str, ObservationResult]:
    """
    批量观测多个目标
    
    Args:
        targets: 目标列表
        survey: 巡天调查
        fov_arcmin: 视场
        exposure: 曝光时间
        frames: 帧数
        
    Returns:
        Dict[str, ObservationResult]: 目标名 -> 结果
    """
    workflow = RealtimeObservationWorkflow()
    results = {}
    
    print(f"\n开始批量观测: {len(targets)} 个目标")
    print("-" * 40)
    
    for i, target in enumerate(targets):
        print(f"\n[{i+1}/{len(targets)}] 观测 {target}")
        
        try:
            result = await workflow.run(
                target=target,
                survey=survey,
                fov_arcmin=fov_arcmin,
                exposure=exposure,
                frames=frames
            )
            results[target] = result
        except Exception as e:
            print(f"  观测失败: {e}")
            results[target] = ObservationResult(
                target=ObservationTarget(name=target, ra=0, dec=0),
                phases_completed=[ObservationPhase.FAILED],
                success=False,
                error_message=str(e)
            )
        
        # 目标间休息
        if i < len(targets) - 1:
            print(f"  休息5秒...")
            await asyncio.sleep(5)
    
    await workflow.shutdown()
    
    # 汇总
    success_count = sum(1 for r in results.values() if r.success)
    print("\n" + "=" * 60)
    print(f"批量观测完成: {success_count}/{len(targets)} 成功")
    print("=" * 60)
    
    return results


# ============ CLI 测试 ============

async def demo():
    """演示实时观测工作流"""
    print("""
    ================================================
    天问-AGI 实时观测工作流演示
    ================================================
    
    本演示展示完整的天文观测流程:
    1. 目标规划 - 解析目标坐标
    2. 真实星图 - 从NASA SkyView获取
    3. 望远镜控制 - GOTO + Plate Solving
    4. 成像采集 - 曝光序列
    """)
    
    workflow = RealtimeObservationWorkflow()
    
    # 单目标观测
    print("\n>>> 单目标观测演示: M31 (仙女座星系)")
    result = await workflow.run(
        target="M31",
        survey="DSS2/color",
        fov_arcmin=30.0,
        exposure=10.0,
        frames=3
    )
    
    print("\n>>> 结果摘要:")
    print(f"  成功: {result.success}")
    print(f"  完成阶段: {[p.value for p in result.phases_completed]}")
    print(f"  目标: {result.target.catalog_name}")
    print(f"  坐标: {result.target.ra_hms}, {result.target.dec_dms}")
    
    if result.skychart_data:
        print(f"  星图: {result.skychart_data.get('sources_count', 0)} 个天体被检测")
    
    if result.telescope_state:
        print(f"  望远镜: {result.telescope_state.get('status', 'N/A')}")
    
    if result.imaging_result:
        print(f"  成像: {'成功' if result.imaging_result.get('success') else '失败'}")
    
    await workflow.shutdown()


if __name__ == "__main__":
    asyncio.run(demo())
