"""
天问-AGI 观测调度引擎
ObservationScheduler - 自动计算最佳观测时间并调度设备
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from dataclasses import dataclass
import math

# ============ 观测条件模型 ============

@dataclass
class Location:
    """观测位置"""
    name: str
    lat: float  # 纬度
    lon: float  # 经度
    elevation: float = 0  # 海拔(米)
    timezone: str = "Asia/Shanghai"
    light_pollution: int = 1  # 光污染等级 1-5

@dataclass
class Equipment:
    """观测设备"""
    name: str
    type: str  # telescope, camera, mount
    aperture: float  # 口径(mm)
    focal_length: float  # 焦距(mm)
    f_ratio: float = 0  # 焦比
    max_magnification: float = 0
    limiting_magnitude: float = 0  # 极限星等

@dataclass
class ObservationWindow:
    """观测窗口"""
    start_time: datetime
    end_time: datetime
    target: str  # 目标天体名称
    altitude: float  # 高度角
    azimuth: float  # 方位角
    seeing: float  # 视宁度
    cloud_cover: int  # 云量 %
    moon_distance: float  # 月亮距离
    moon_phase: float  # 月相
    score: float  # 总体评分 0-100
    reasons: List[str] = field(default_factory=list)

@dataclass
class Schedule:
    """观测计划"""
    id: str
    created_at: datetime
    date: str
    location: Location
    targets: List[Dict] = field(default_factory=list)
    windows: List[ObservationWindow] = field(default_factory=list)
    weather_forecast: List[Dict] = field(default_factory=list)
    notes: str = ""

# ============ 天球坐标计算 ============

class CelestialCoordinates:
    """天球坐标计算"""

    @staticmethod
    def equatorial_to_horizontal(ra: float, dec: float,
                                  lat: float, lon: float,
                                  dt: datetime) -> Tuple[float, float]:
        """
        将赤道坐标转换为地平坐标
        ra, dec: 赤经赤纬(度)
        lat, lon: 观测点纬经度(度)
        返回: (高度角, 方位角) 度
        """
        # 计算儒略日
        jd = CelestialCoordinates._to_julian_date(dt)

        # 恒星时
        lst = CelestialCoordinates._local_sidereal_time(jd, lon)

        # 时角
        ha = lst - ra
        if ha < 0:
            ha += 360
        ha_rad = math.radians(ha)

        lat_rad = math.radians(lat)
        dec_rad = math.radians(dec)

        # 高度角
        sin_alt = (math.sin(dec_rad) * math.sin(lat_rad) +
                   math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
        alt = math.degrees(math.asin(sin_alt))

        # 方位角
        cos_az = ((math.sin(dec_rad) - math.sin(math.radians(alt)) * math.sin(lat_rad)) /
                  (math.cos(math.radians(alt)) * math.cos(lat_rad)))
        az = math.degrees(math.acos(max(-1, min(1, cos_az))))

        if math.sin(ha_rad) > 0:
            az = 360 - az

        return round(alt, 2), round(az, 2)

    @staticmethod
    def _to_julian_date(dt: datetime) -> float:
        """转换为儒略日"""
        year = dt.year
        month = dt.month
        day = dt.day + dt.hour/24 + dt.minute/1440

        if month <= 2:
            year -= 1
            month += 12

        a = int(year / 100)
        b = 2 - a + int(a / 4)
        return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5

    @staticmethod
    def _local_sidereal_time(jd: float, lon: float) -> float:
        """计算地方恒星时"""
        t = (jd - 2451545.0) / 36525.0
        lst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + t * t * (0.000387933 - t / 38710000.0)
        lst = (lst + lon) % 360
        return lst

    @staticmethod
    def calculate_moon_position(lat: float, lon: float, dt: datetime) -> Tuple[float, float]:
        """计算月亮位置（简化）"""
        # 简化计算：月亮约27.3天绕地球一周
        days_since_known = (dt - datetime(2026, 1, 1)).days
        moon_lon = (days_since_known * 360 / 27.3) % 360

        # 月亮赤纬简化计算
        moon_dec = 5 * math.sin(math.radians(moon_lon * 2))

        # 转换为地平坐标
        return CelestialCoordinates.equatorial_to_horizontal(
            moon_lon * 15,  # 近似赤经
            moon_dec,
            lat, lon, dt
        )

    @staticmethod
    def calculate_moon_phase(dt: datetime) -> float:
        """计算月相 (0=新月, 0.5=满月, 1=新月)"""
        known_new_moon = datetime(2026, 1, 3)
        synodic_month = 29.53
        days_diff = (dt - known_new_moon).days + (dt.hour - 12) / 24
        return (days_diff % synodic_month) / synodic_month

# ============ 天气分析 ============

class WeatherAnalyzer:
    """天气分析"""

    # 云量与观测评分关系
    CLOUD_SCORE_MAP = {
        0: 100,   # 晴空
        10: 95,
        20: 85,
        30: 70,
        40: 55,
        50: 40,
        60: 25,
        70: 10,
        80: 5,
        90: 0,
        100: 0    # 完全阴天
    }

    # 视宁度评分
    SEEING_SCORE_MAP = {
        1.0: 100,  # 极好
        1.5: 90,
        2.0: 75,
        2.5: 60,
        3.0: 45,
        4.0: 25,
        5.0: 10
    }

    @staticmethod
    def score_from_cloud_cover(cloud_cover: int) -> float:
        """根据云量评分"""
        if cloud_cover <= 30:
            return WeatherAnalyzer.CLOUD_SCORE_MAP.get(cloud_cover, 70)
        return max(0, 50 - cloud_cover)

    @staticmethod
    def score_from_seeing(seeing: float) -> float:
        """根据视宁度评分"""
        if seeing <= 1.0:
            return 100
        if seeing >= 5.0:
            return 5
        return max(5, 100 - (seeing - 1.0) * 25)

    @staticmethod
    def score_from_moon(moon_phase: float, moon_distance: float) -> float:
        """根据月亮条件评分"""
        # 月相越接近满月，影响越大
        moon_brightness = abs(moon_phase - 0.5) * 2  # 0=满月影响最大

        # 月亮距离越近，影响越大
        if moon_distance < 30:
            distance_factor = 0.3
        elif moon_distance < 60:
            distance_factor = 0.6
        elif moon_distance < 90:
            distance_factor = 0.85
        else:
            distance_factor = 1.0

        return moon_brightness * distance_factor * 100

# ============ 观测调度器 ============

class ObservationScheduler:
    """观测调度器"""

    def __init__(self, location: Location = None):
        self.location = location or Location("默认位置", 39.9, 116.4, 50)
        self.coordinates = CelestialCoordinates()
        self.weather = WeatherAnalyzer()

        # 默认设备（7寸牛反）
        self.default_equipment = Equipment(
            name="Celestron NexStar 8SE",
            type=" Schmidt-Cassegrain",
            aperture=203,
            focal_length=2032,
            f_ratio=10,
            max_magnification=400,
            limiting_magnitude=14
        )

    def set_location(self, location: Location):
        """设置观测位置"""
        self.location = location

    def set_equipment(self, equipment: Equipment):
        """设置观测设备"""
        self.default_equipment = equipment

    async def calculate_target_position(self, target_name: str, dt: datetime) -> Optional[Dict]:
        """计算目标天体的位置"""
        # 从星体识别系统获取目标坐标
        from star_recognizer import StarRecognizer
        recognizer = StarRecognizer()
        result = await recognizer.recognize_from_name(target_name)

        if not result.catalog_match:
            return None

        ra = result.catalog_match.ra
        dec = result.catalog_match.dec

        # 转换为地平坐标
        alt, az = self.coordinates.equatorial_to_horizontal(
            ra, dec, self.location.lat, self.location.lon, dt
        )

        return {
            "target": target_name,
            "ra": ra,
            "dec": dec,
            "altitude": alt,
            "azimuth": az,
            "is_visible": alt > 15  # 低于15度受大气干扰大
        }

    async def score_observation_window(self, target: str, dt: datetime,
                                        cloud_cover: int, seeing: float) -> ObservationWindow:
        """评分观测窗口"""
        # 计算目标位置
        target_pos = await self.calculate_target_position(target, dt)
        if not target_pos:
            return ObservationWindow(
                start_time=dt,
                end_time=dt + timedelta(hours=1),
                target=target,
                altitude=0,
                azimuth=0,
                seeing=seeing,
                cloud_cover=cloud_cover,
                moon_distance=0,
                moon_phase=0,
                score=0,
                reasons=["目标未找到"]
            )

        # 计算月亮条件
        moon_alt, moon_az = self.coordinates.calculate_moon_position(
            self.location.lat, self.location.lon, dt
        )
        moon_phase = self.coordinates.calculate_moon_phase(dt)

        # 计算月亮角距离
        moon_distance = math.sqrt(
            (target_pos['altitude'] - moon_alt)**2 +
            (target_pos['azimuth'] - moon_az)**2
        )

        # 计算各项评分
        altitude_score = min(100, target_pos['altitude'] * 3) if target_pos['altitude'] > 0 else 0
        cloud_score = self.weather.score_from_cloud_cover(cloud_cover)
        seeing_score = self.weather.score_from_seeing(seeing)
        moon_score = self.weather.score_from_moon(moon_phase, moon_distance)

        # 综合评分（加权）
        total_score = (
            altitude_score * 0.35 +
            cloud_score * 0.25 +
            seeing_score * 0.20 +
            moon_score * 0.20
        )

        # 生成原因列表
        reasons = []
        if target_pos['altitude'] < 15:
            reasons.append(f"目标高度过低({target_pos['altitude']:.1f}°)")
        if cloud_cover > 30:
            reasons.append(f"云量较多({cloud_cover}%)")
        if seeing > 2.5:
            reasons.append(f"视宁度较差({seeing:.1f}\")")
        if moon_distance < 45:
            reasons.append(f"月亮距离较近({moon_distance:.1f}°)")

        return ObservationWindow(
            start_time=dt,
            end_time=dt + timedelta(hours=1),
            target=target,
            altitude=target_pos['altitude'],
            azimuth=target_pos['azimuth'],
            seeing=seeing,
            cloud_cover=cloud_cover,
            moon_distance=moon_distance,
            moon_phase=moon_phase,
            score=total_score,
            reasons=reasons
        )

    async def generate_schedule(self, targets: List[str], date: datetime,
                                 cloud_cover: int = 20, seeing: float = 2.0) -> Schedule:
        """生成观测计划"""
        schedule_id = f"sch_{date.strftime('%Y%m%d_%H%M%S')}"

        windows = []

        # 评估全天的观测窗口（每小时一个点）
        for hour in range(24):
            dt = datetime(date.year, date.month, date.day, hour)

            for target in targets:
                window = await self.score_observation_window(
                    target, dt, cloud_cover, seeing
                )
                if window.score > 30:  # 只保留30分以上的窗口
                    windows.append(window)

        # 按评分排序
        windows.sort(key=lambda w: w.score, reverse=True)

        # 选择最佳窗口组成计划
        selected_targets = []
        used_hours = set()

        for window in windows:
            hour_key = window.start_time.hour
            if hour_key not in used_hours and len(selected_targets) < 5:
                selected_targets.append({
                    "target": window.target,
                    "time": window.start_time.strftime("%H:%M"),
                    "altitude": window.altitude,
                    "score": window.score
                })
                used_hours.add(hour_key)

        return Schedule(
            id=schedule_id,
            created_at=datetime.now(),
            date=date.strftime('%Y-%m-%d'),
            location=self.location,
            targets=selected_targets,
            windows=windows[:20],  # 保存前20个评分窗口
            notes=f"生成了包含{len(selected_targets)}个目标的天文观测计划"
        )

    async def find_best_nights(self, targets: List[str], days: int = 7) -> List[Dict]:
        """寻找最佳观测夜晚"""
        results = []
        today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

        for day_offset in range(days):
            date = today + timedelta(days=day_offset)

            # 模拟天气预报数据
            # 实际应接入真实天气API
            cloud_cover = 20  # 简化：假设都是好天气
            seeing = 2.0

            # 计算当夜最佳观测时间
            best_windows = []
            for hour in range(18, 24):  # 傍晚6点到午夜
                dt = date.replace(hour=hour)
                for target in targets:
                    window = await self.score_observation_window(target, dt, cloud_cover, seeing)
                    if window.score > 50:
                        best_windows.append(window)

            if best_windows:
                best_windows.sort(key=lambda w: w.score, reverse=True)
                best = best_windows[0]

                results.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "best_target": best.target,
                    "best_time": best.start_time.strftime('%H:%M'),
                    "best_score": best.score,
                    "altitude": best.altitude,
                    "conditions": f"云量{cloud_cover}%/视宁{seeing}\"",
                    "recommendation": "适合观测" if best.score > 70 else "一般"
                })

        return results

    def generate_schedule_report(self, schedule: Schedule) -> str:
        """生成调度报告"""
        lines = [
            "=" * 60,
            f"🔭 天文观测调度报告",
            "=" * 60,
            f"计划ID: {schedule.id}",
            f"创建时间: {schedule.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"观测日期: {schedule.date}",
            f"观测地点: {schedule.location.name}",
            f"  纬度: {schedule.location.lat}°",
            f"  经度: {schedule.location.lon}°",
            f"  海拔: {schedule.location.elevation}m",
            "",
            "-" * 60,
            "📋 推荐观测目标",
            "-" * 60,
        ]

        for i, target in enumerate(schedule.targets, 1):
            lines.append(
                f"  {i}. {target['target']}"
                f"  时间: {target['time']}"
                f"  高度角: {target['altitude']:.1f}°"
                f"  评分: {target['score']:.0f}/100"
            )

        if schedule.windows:
            lines.extend([
                "",
                "-" * 60,
                "📊 评分窗口详情 (Top 10)",
                "-" * 60,
            ])

            for i, window in enumerate(schedule.windows[:10], 1):
                lines.append(
                    f"  {i}. {window.target}"
                    f"  {window.start_time.strftime('%H:%M')}"
                    f"  高度:{window.altitude:.1f}°"
                    f"  评分:{window.score:.0f}"
                )
                if window.reasons:
                    lines.append(f"     问题: {'; '.join(window.reasons[:2])}")

        lines.extend([
            "",
            "=" * 60,
            f"备注: {schedule.notes}",
            "=" * 60,
        ])

        return "\n".join(lines)

# ============ 示例用法 ============

async def demo():
    print("=" * 60)
    print("天问-AGI 观测调度引擎演示")
    print("=" * 60)

    # 创建观测位置（北京）
    location = Location("北京天文馆", 39.9, 116.4, 50)

    scheduler = ObservationScheduler(location)

    # 1. 计算目标位置
    print("\n📍 计算目标天体位置...")
    pos = await scheduler.calculate_target_position("猎户座大星云", datetime.now())
    if pos:
        print(f"   目标: {pos['target']}")
        print(f"   赤经: {pos['ra']:.2f}°")
        print(f"   赤纬: {pos['dec']:.2f}°")
        print(f"   高度角: {pos['altitude']:.2f}°")
        print(f"   方位角: {pos['azimuth']:.2f}°")
        print(f"   可见性: {'可见' if pos['is_visible'] else '不可见'}")

    # 2. 评分观测窗口
    print("\n⭐ 评分观测窗口...")
    window = await scheduler.score_observation_window(
        "织女星", datetime(2026, 4, 29, 22, 0), cloud_cover=15, seeing=2.0
    )
    print(f"   目标: {window.target}")
    print(f"   时间: {window.start_time.strftime('%H:%M')}")
    print(f"   高度角: {window.altitude:.1f}°")
    print(f"   月亮距离: {window.moon_distance:.1f}°")
    print(f"   综合评分: {window.score:.0f}/100")
    if window.reasons:
        print(f"   注意事项: {window.reasons[0] if window.reasons else '无'}")

    # 3. 生成观测计划
    print("\n📅 生成观测计划...")
    targets = ["织女星", "天狼星", "猎户座大星云", "M31", "M45"]
    schedule = await scheduler.generate_schedule(targets, datetime(2026, 4, 29))
    print(f"   计划ID: {schedule.id}")
    print(f"   推荐目标数: {len(schedule.targets)}")

    # 4. 寻找最佳夜晚
    print("\n🌙 寻找未来7天最佳观测夜...")
    best_nights = await scheduler.find_best_nights(targets, 7)
    for night in best_nights:
        print(f"   {night['date']}: {night['best_target']} @ {night['best_time']} (评分:{night['best_score']:.0f})")

    # 5. 生成报告
    print("\n" + "=" * 60)
    report = scheduler.generate_schedule_report(schedule)
    print(report)

if __name__ == "__main__":
    asyncio.run(demo())