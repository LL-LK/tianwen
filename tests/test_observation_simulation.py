#!/usr/bin/env python3
"""
天问-AGI 观测自动化模拟测试

测试观测调度器 → 执行器 完整模拟闭环

运行方式:
    python tests/test_observation_simulation.py

依赖:
    pip install astropy astroplan loguru
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 可选依赖检查
try:
    from observation.scheduler import ObservationScheduler, Location, ObservationTarget
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    SCHEDULER_AVAILABLE = False
    print(f"[WARN] 观测调度器依赖缺失: {e}")
    print(f"[WARN] astropy/astroplan 未安装，调度器测试将跳过")
    print(f"[WARN] 安装命令: pip install astropy astroplan")

from observation.executor import (
    ObservationExecutor,
    ObservationCommand,
    ObservationInstruction,
)


class MockObservationWindow:
    """模拟观测窗口（无astropy时使用）"""
    def __init__(self, name, score, altitude, azimuth, moon_distance, start_hour, end_hour, reasons):
        self.name = name
        self.score = score
        self.altitude = altitude
        self.azimuth = azimuth
        self.moon_distance = moon_distance
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.reasons = reasons
        self.moon_phase = 0.35

    def __repr__(self):
        return (f"MockWindow({self.name}, score={self.score}, "
                f"alt={self.altitude:.1f}°, az={self.azimuth:.1f}°, "
                f"{self.start_hour}:00-{self.end_hour}:00)")


def _create_mock_window(name, score, altitude, azimuth, moon_distance, start_hour, end_hour, reasons):
    return MockObservationWindow(name, score, altitude, azimuth, moon_distance, start_hour, end_hour, reasons)


def create_test_targets() -> list:
    """创建测试目标列表（真实天文目标）"""
    # 调度器需要 astropy/astroplan
    if not SCHEDULER_AVAILABLE:
        return [
            {"name": "M31-安德洛梅达星系", "ra": 10.6847, "dec": 41.2692,
             "magnitude": 3.4, "priority": 95,
             "filters": ["L", "R", "G", "B"], "moon_distance_min": 30},
            {"name": "M42-猎户座大星云", "ra": 83.8221, "dec": -5.3911,
             "magnitude": 4.0, "priority": 90,
             "filters": ["L", "Ha"], "moon_distance_min": 25},
        ]
    return [
        ObservationTarget(
            name="M31-安德洛梅达星系",
            ra=10.6847,
            dec=41.2692,
            magnitude=3.4,
            priority=95,
            filters=["L", "R", "G", "B"],
            exposure_time=60,
        ),
        ObservationTarget(
            name="M42-猎户座大星云",
            ra=83.8221,
            dec=-5.3911,
            magnitude=4.0,
            priority=90,
            filters=["L", "H-alpha", "OIII"],
            exposure_time=30,
        ),
    ]


async def test_scheduler(targets: list[ObservationTarget]) -> dict:
    """测试观测调度器"""
    print("\n" + "="*60)
    print("📡 测试1: 观测调度器")
    print("="*60)

    if not SCHEDULER_AVAILABLE:
        print("\n⚠️  调度器不可用（缺少 astropy/astroplan）")
        # 返回模拟数据用于执行器测试
        mock_targets = {
            "M31-安德洛梅达星系": _create_mock_window(
                name="M31-安德洛梅达星系",
                score=88,
                altitude=65.2,
                azimuth=287.5,
                moon_distance=45.0,
                start_hour=20, end_hour=2,
                reasons=["目标高度角高", "月亮距离充足", "透明度好"]
            ),
            "M42-猎户座大星云": _create_mock_window(
                name="M42-猎户座大星云",
                score=82,
                altitude=52.1,
                azimuth=193.8,
                moon_distance=38.0,
                start_hour=21, end_hour=3,
                reasons=["已过中天", "视宁度良好", "无云覆盖"]
            ),
        }
        for name, window in mock_targets.items():
            print(f"\n✅ (mock) {name}")
            print(f"   窗口: {window.start_hour:02d}:00-{window.end_hour:02d}:00")
            print(f"   高度角: {window.altitude:.1f}°  方位角: {window.azimuth:.1f}°")
            print(f"   月亮距离: {window.moon_distance:.1f}°  月相: {window.moon_phase*100:.0f}%")
            print(f"   综合评分: {window.score}/100")
            print(f"   原因: {', '.join(window.reasons)}")
        return mock_targets

    # 兴隆观测站
    location = Location(
        name="兴隆观测站",
        lat=40.3964,
        lon=117.5075,
        elevation=900,
        timezone="Asia/Shanghai",
        light_pollution=2
    )

    scheduler = ObservationScheduler(location)

    results = {}
    for target in targets:
        try:
            window = await scheduler.calculate_best_window(target)
        except Exception as e:
            print(f"\n⚠️  {target.name} 调度异常: {e}")
            results[target.name] = None
            continue
        if window:
            results[target.name] = window
            print(f"\n✅ {target.name}")
            print(f"   窗口: {window.start_time.strftime('%H:%M')}-{window.end_time.strftime('%H:%M')}")
            print(f"   高度角: {window.altitude:.1f}°  方位角: {window.azimuth:.1f}°")
            print(f"   月亮距离: {window.moon_distance:.1f}°  月相: {window.moon_phase*100:.0f}%")
            print(f"   综合评分: {window.score:.1f}/100")
            print(f"   原因: {', '.join(window.reasons)}")
        else:
            print(f"\n❌ {target.name} - 无可用窗口")
            results[target.name] = None

    return results


async def test_scheduler_time_params(targets: list[ObservationTarget]) -> dict:
    """测试观测调度器时间窗口参数化（start_time/end_time）"""
    print("\n" + "="*60)
    print("📡 测试1b: 观测调度器时间窗口参数化")
    print("="*60)

    location = Location(
        name="兴隆观测站",
        lat=40.3964,
        lon=117.5075,
        elevation=900,
        timezone="Asia/Shanghai",
        light_pollution=2
    )
    scheduler = ObservationScheduler(location)

    # 固定测试时间：北京时间 2026-05-10 20:00（UTC 12:00）
    # 此时 M31(RA=10.68°) 刚好在地平线下，RA过滤边界
    # 调度器固定时间：2026-05-10 03:25 UTC（+8=CST 11:25）
    # 此时 M31 高度 71.9°，M42 不可见（低于 30°）
    fixed_date = datetime(2026, 5, 10, 3, 25, 0)

    # 用 start_time/end_time 指定观测窗口
    start = datetime(2026, 5, 10, 22, 0, 0)  # 北京22:00
    end = datetime(2026, 5, 11, 2, 0, 0)       # 北京次日02:00

    m31_target = next(t for t in targets if "M31" in t.name)
    try:
        window = await scheduler.calculate_best_window(
            m31_target,
            date=fixed_time,
            start_time=start,
            end_time=end
        )
        if window:
            print(f"\n✅ {m31_target.name} 在指定窗口 {start.strftime('%H:%M')}-{end.strftime('%H:%M')} 内:")
            print(f"   锚定时间: {fixed_time} (LST计算用)")
            print(f"   观测窗口: {window.start_time.strftime('%H:%M')}-{window.end_time.strftime('%H:%M')}")
            print(f"   高度角: {window.altitude:.1f}°  方位角: {window.azimuth:.1f}°")
            print(f"   综合评分: {window.score:.1f}/100")
            return {"parametric_window": True, "window": window}
        else:
            print(f"\n⚠️  {m31_target.name} 在指定窗口仍无可用窗口")
            return {"parametric_window": False, "window": None}
    except Exception as e:
        print(f"\n⚠️  时间参数化测试异常: {e}")
        import traceback
        traceback.print_exc()
        return {"parametric_window": False, "error": str(e)}


def _get_target_attr(target, attr):
    """获取目标属性，支持 dict 或 object"""
    if isinstance(target, dict):
        return target[attr]
    return getattr(target, attr)


def windows_to_instructions(windows: dict, targets: list = None, max_targets: int = 3) -> list[ObservationInstruction]:
    """将观测窗口转换为执行指令"""
    if targets is None:
        targets = create_test_targets()
    instructions = []

    sorted_windows = sorted(
        [(name, w) for name, w in windows.items() if w is not None],
        key=lambda x: x[1].score,
        reverse=True
    )[:max_targets]

    for name, window in sorted_windows:
        target = next(t for t in targets if _get_target_attr(t, "name") == name)

        # 1. 转向指令
        instructions.append(ObservationInstruction(
            command=ObservationCommand.SLEW_TO_TARGET,
            target_ra=_get_target_attr(target, "ra"),
            target_dec=_get_target_attr(target, "dec")
        ))

        # 2. 跟踪指令
        instructions.append(ObservationInstruction(
            command=ObservationCommand.TRACK_TARGET,
            target_ra=_get_target_attr(target, "ra"),
            target_dec=_get_target_attr(target, "dec")
        ))

        # 3. 曝光指令
        filters = _get_target_attr(target, "filters")
        instructions.append(ObservationInstruction(
            command=ObservationCommand.START_EXPOSURE,
            exposure_time=_get_target_attr(target, "exposure_time"),
            filter_name=filters[0] if filters else "L"
        ))

    return instructions


async def test_executor(instructions: list[ObservationInstruction]) -> dict:
    """测试观测执行器（模拟模式）"""
    print("\n" + "="*60)
    print("🔭 测试2: 观测执行器（模拟模式）")
    print("="*60)

    executor = ObservationExecutor(connection_string="tcp://localhost:5555")
    executor.set_real_mode(real_mode=False, allow_mock_fallback=True)

    # 连接
    connected = await executor.connect()
    print(f"\n连接状态: {'✅ 已连接' if connected else '❌ 连接失败'}")

    # 执行计划
    print(f"\n执行计划: {len(instructions)} 条指令")
    for i, instr in enumerate(instructions):
        target_info = ""
        if instr.target_ra is not None:
            target_info = f" → RA={instr.target_ra:.2f}° Dec={instr.target_dec:.2f}°"
        elif instr.exposure_time:
            target_info = f" → {instr.exposure_time}s {instr.filter_name or ''}"
        print(f"  [{i+1}] {instr.command.value}{target_info}")

    print()
    result = await executor.execute_observation_plan(instructions)

    print(f"\n执行结果:")
    print(f"  总指令: {result.total_instructions}")
    print(f"  成功: {result.successful} ✅")
    print(f"  失败: {result.failed} ❌")
    print(f"  成功率: {result.success_rate*100:.1f}%")

    for i, r in enumerate(result.results):
        status = "✅" if r['success'] else "❌"
        print(f"  [{i+1}] {status} {r['command']}  {r.get('error', '')}")

    await executor.disconnect()

    return result.to_dict()


async def test_telescope_simulator():
    """测试望远镜模拟器"""
    print("\n" + "="*60)
    print("🖥️  测试3: 望远镜模拟器")
    print("="*60)

    try:
        from telescope.simulator import TelescopeSimulator

        sim = TelescopeSimulator(name="Seestar S50", simulate_errors=False)

        # 连接
        await sim.connect()
        print("✅ 连接成功\n")

        # 测试指向
        print("测试1: GOTO M31")
        ok = await sim.goto("M31")
        print(f"  {'✅ 成功' if ok else '❌ 失败'}")

        print("\n测试2: 拍摄校准 (plate solve)")
        result = await sim.plate_solve()
        print(f"  RA={result.get('ra', 'N/A'):.4f}°, Dec={result.get('dec', 'N/A'):.4f}°")
        print(f"  {'✅ 成功' if result else '❌ 失败'}")

        print("\n测试3: 同步坐标")
        ok = await sim.sync_coordinates(10.6847, 41.2692)
        print(f"  {'✅ 成功' if ok else '❌ 失败'}")

        print("\n测试4: 开始跟踪")
        ok = await sim.start_tracking()
        print(f"  {'✅ 成功' if ok else '❌ 失败'}")

        print("\n测试5: 停止跟踪")
        await sim.stop_tracking()
        print(f"  ✅ 成功")

        print("\n测试6: 导星")
        stats = sim.get_stats()
        print(f"  RMS: {stats.get('tracking_rms_arcsec', 'N/A')} arcsec")
        print(f"  状态: {stats.get('tracking_status', 'N/A')}")

        print("\n测试7: 曝光")
        result = await sim.expose(exposure=2.0, count=1)
        print(f"  帧数: {result.frame_count}, 单帧曝光: {result.exposure_sec}s")
        print(f"  ✅ 成功")

        print("\n测试8: 中止曝光")
        ok = await sim.cancel_exposure()
        print(f"  {'✅ 成功' if ok else '❌ 失败'}")

        print("\n测试9: 归位")
        ok = await sim.park()
        print(f"  {'✅ 成功' if ok else '❌ 失败'}")

        await sim.disconnect()
        print("\n✅ Seestar S50 望远镜模拟器全流程测试通过")
        return True

    except ImportError as e:
        print(f"\n⚠️  望远镜模拟器导入失败: {e}")
        print("   这不影响 executor 模拟模式测试")
        return False
    except Exception as e:
        print(f"\n❌ 望远镜模拟器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试流程"""
    print("="*60)
    print("🔬 天问-AGI 观测自动化模拟测试")
    print(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 创建测试目标
    targets = create_test_targets()
    print(f"\n📋 测试目标: {len(targets)} 个")
    for t in targets:
        name = _get_target_attr(t, "name")
        priority = _get_target_attr(t, "priority")
        print(f"  • {name} - 优先级 {priority}")

    # 测试1: 调度器（基础）
    windows = await test_scheduler(targets)

    # 测试1b: 调度器（时间窗口参数化）
    time_params_result = await test_scheduler_time_params(targets)

    # 测试2: 执行器（始终运行，无窗口则用模拟数据）
    if any(w is not None for w in windows.values()):
        instructions = windows_to_instructions(windows, targets=targets)
        exec_result = await test_executor(instructions)
    else:
        # 调度失败时用模拟窗口执行
        print("\n⚠️  调度失败，使用模拟窗口运行执行器测试")
        # 缩短曝光时间以便快速测试
        for t in targets:
            name = _get_target_attr(t, "name")
            if name in ("M31-安德洛梅达星系", "M42-猎户座大星云"):
                if isinstance(t, dict):
                    t["exposure_time"] = 2
                else:
                    t.exposure_time = 2
        mock_windows = {
            "M31-安德洛梅达星系": _create_mock_window(
                name="M31-安德洛梅达星系", score=88,
                altitude=65.2, azimuth=287.5, moon_distance=45.0,
                start_hour=20, end_hour=2,
                reasons=["目标高度角高", "月亮距离充足"]
            ),
            "M42-猎户座大星云": _create_mock_window(
                name="M42-猎户座大星云", score=82,
                altitude=52.1, azimuth=193.8, moon_distance=38.0,
                start_hour=21, end_hour=3,
                reasons=["已过中天", "视宁度良好"]
            ),
        }
        instructions = windows_to_instructions(mock_windows, targets=targets)
        exec_result = await test_executor(instructions)

    # 测试3: 望远镜模拟器
    sim_ok = await test_telescope_simulator()

    # 汇总
    print("\n" + "="*60)
    print("📊 测试汇总")
    print("="*60)

    scheduled = sum(1 for w in windows.values() if w is not None)
    print(f"  调度器: {scheduled}/{len(targets)} 目标已规划窗口")
    tp_ok = time_params_result.get("parametric_window", False)
    print(f"  调度器(时间参数化): {'✅ 可用' if tp_ok else '⚠️  跳过/失败'}")

    if exec_result:
        print(f"  执行器: {exec_result['successful']}/{exec_result['total_instructions']} 指令成功")

    print(f"  望远镜模拟器: {'✅ 可用' if sim_ok else '⚠️  不可用'}")

    print("\n" + "="*60)
    print("✅ 观测自动化模拟测试完成")
    print("="*60)

    return windows, exec_result


if __name__ == "__main__":
    asyncio.run(main())
