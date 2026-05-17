"""
天问-AGI 增强型观测调度引擎 (Enhanced Observation Scheduler)
参考TSI调度算法设计

核心功能:
1. 夜天文时间计算（太阳地平线以下18度）
2. 目标可见性窗口计算
3. 调度碎片化分析
4. 综合观测条件评分
"""

import math
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time as dt_time
from typing import List, Optional, Tuple, Dict, Any
from statistics import mean, median
from enum import Enum

# 尝试导入astropy，如果不可用则使用内置计算
try:
    from astropy.coordinates import EarthLocation, AltAz, SkyCoord
    from astropy.time import Time
    from astropy import units as u
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

# 尝试导入skyfield作为备选
try:
    from skyfield.api import Topos, Loader, JulianDate
    from skyfield.timelib import Time as SkyfieldTime
    HAS_SKYFIELD = True
except ImportError:
    HAS_SKYFIELD = False


# ============ 核心数据结构 ============

@dataclass
class GeographicLocation:
    """观测站位置"""
    name: str
    latitude: float  # 纬度 (度)
    longitude: float  # 经度 (度)
    elevation: float  # 海拔 (米)

    def to_skyfield(self) -> 'Topos':
        """转换为skyfield位置对象"""
        if HAS_SKYFIELD:
            return Topos(
                latitude_degrees=self.latitude,
                longitude_degrees=self.longitude,
                elevation_m=self.elevation
            )
        raise ImportError("skyfield not available")

    def to_astropy(self) -> 'EarthLocation':
        """转换为astropy位置对象"""
        if HAS_ASTROPY:
            return EarthLocation(
                lat=self.latitude * u.deg,
                lon=self.longitude * u.deg,
                height=self.elevation * u.m
            )
        raise ImportError("astropy not available")


@dataclass
class Constraints:
    """观测约束"""
    min_altitude: float = 30.0  # 最低高度角 (度)
    min_azimuth: Optional[float] = None  # 最小方位角 (度)
    max_azimuth: Optional[float] = None  # 最大方位角 (度)
    min_duration: timedelta = field(default_factory=lambda: timedelta(minutes=30))


@dataclass
class VisibilityWindow:
    """可见性窗口"""
    start: datetime
    end: datetime
    max_altitude: float  # 窗口内最高高度角
    avg_altitude: float  # 窗口内平均高度角

    @property
    def duration(self) -> timedelta:
        """窗口持续时间"""
        return self.end - self.start

    def __repr__(self) -> str:
        return (f"VisibilityWindow(start={self.start.isoformat()}, "
                f"end={self.end.isoformat()}, max_alt={self.max_altitude:.1f}°, "
                f"avg_alt={self.avg_altitude:.1f}°)")


class ObservationType(Enum):
    """观测类型枚举"""
    PHOTOMETRY = "photometry"  # 光度测量
    SPECTROSCOPY = "spectroscopy"  # 光谱观测
    IMAGING = "imaging"  # 成像
    VISUAL = "visual"  # 目视


@dataclass
class ObservationTarget:
    """观测目标"""
    name: str
    ra: float  # 赤经 (度)
    dec: float  # 赤纬 (度)
    observation_type: ObservationType = ObservationType.IMAGING
    priority: int = 1  # 优先级 1-5
    min_altitude: float = 30.0  # 目标特定最低高度角
    catalog_id: Optional[str] = None


@dataclass
class FragmentationMetrics:
    """调度碎片化指标"""
    idle_operable_hours: float  # 空闲可操作小时数
    gap_count: int  # 间隙数量
    gap_mean: timedelta  # 间隙平均时长
    gap_median: timedelta  # 间隙中位数时长
    gap_p90: timedelta  # 间隙90分位时长
    scheduled_fraction: float  # 已调度比例

    def __str__(self) -> str:
        return (f"FragmentationMetrics(idle_hours={self.idle_operable_hours:.2f}, "
                f"gaps={self.gap_count}, scheduled_fraction={self.scheduled_fraction:.2%})")


@dataclass
class MoonPhase:
    """月相信息"""
    phase: float  # 0-1, 0=新月，1=满月
    illumination: float  # 亮度 0-1
    altitude: float  # 高度角
    azimuth: float  # 方位角
    distance: float  # 与目标的角距离


# ============ 天文计算引擎 ============

class AstronomicalCalculator:
    """
    天文计算引擎
    提供太阳位置、目标可见性等核心天文计算
    支持astropy和skyfield两种计算方式
    """

    def __init__(self, location: GeographicLocation):
        self.location = location

        # 初始化计算引擎
        if HAS_ASTROPY:
            self.astro_location = location.to_astropy()
            self.calculator = self._compute_with_astropy
        elif HAS_SKYFIELD:
            self.ephem_loader = Loader('/tmp/skyfield_data')
            self.sf_location = location.to_skyfield()
            self.calculator = self._compute_with_skyfield
        else:
            # 回退到内置计算
            self.calculator = self._compute_builtin

    def _compute_with_astropy(
        self,
        ra: float,
        dec: float,
        time: datetime
    ) -> Tuple[float, float]:
        """使用astropy计算高度角和方位角"""
        try:
            # 创建目标坐标
            target = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')

            # 创建时间
            astropy_time = Time(time)

            # 创建地平坐标系
            altaz = AltAz(location=self.astro_location, obstime=astropy_time)

            # 转换为地平坐标
            target_altaz = target.transform_to(altaz)

            alt = target_altaz.alt.deg
            az = target_altaz.az.deg

            return float(alt), float(az)
        except Exception:
            return self._compute_builtin(ra, dec, time)

    def _compute_with_skyfield(
        self,
        ra: float,
        dec: float,
        time: datetime
    ) -> Tuple[float, float]:
        """使用skyfield计算高度角和方位角"""
        try:
            # 加载星历表
            eph = self.ephem_loader('de421.bsp')

            # 创建时间
            jd = self._to_julian_date(time)

            # 创建观测位置
            apparent = eph['earth'].at(jd).observe(
                SkyCoord(ra=ra, dec=dec, unit='deg')
            )

            # 计算高度角和方位角
            alt, az, distance = apparent.apparent().altaz()

            return float(alt.degrees), float(az.degrees)
        except Exception:
            return self._compute_builtin(ra, dec, time)

    def _compute_builtin(
        self,
        ra: float,
        dec: float,
        time: datetime
    ) -> Tuple[float, float]:
        """
        内置高度角/方位角计算
        使用简化算法进行计算
        """
        # 计算儒略日
        jd = self._to_julian_date(time)

        # 计算地方恒星时
        lst = self._local_sidereal_time(jd, self.location.longitude)

        # 计算时角
        ha = lst - ra
        if ha < 0:
            ha += 360
        ha_rad = math.radians(ha)

        lat_rad = math.radians(self.location.latitude)
        dec_rad = math.radians(dec)

        # 计算高度角
        sin_alt = (math.sin(dec_rad) * math.sin(lat_rad) +
                   math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
        alt = math.degrees(math.asin(max(-1, min(1, sin_alt))))

        # 计算方位角
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
        day = dt.day + dt.hour / 24 + dt.minute / 1440 + dt.second / 86400

        if month <= 2:
            year -= 1
            month += 12

        a = int(year / 100)
        b = 2 - a + int(a / 4)

        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
        return jd

    @staticmethod
    def _local_sidereal_time(jd: float, lon: float) -> float:
        """计算地方恒星时"""
        t = (jd - 2451545.0) / 36525.0
        lst = (280.46061837 +
               360.98564736629 * (jd - 2451545.0) +
               t * t * (0.000387933 - t / 38710000.0))
        lst = (lst + lon) % 360
        return lst

    def compute_altitude_azimuth(
        self,
        ra: float,
        dec: float,
        time: datetime
    ) -> Tuple[float, float]:
        """计算目标的高度角和方位角"""
        return self.calculator(ra, dec, time)

    def compute_sun_position(self, time: datetime) -> Tuple[float, float]:
        """
        计算太阳的位置（高度角和方位角）
        使用Meeus算法计算太阳黄经，再转换为地平坐标
        """
        # 计算儒略日
        jd = self._to_julian_date(time)

        # 计算太阳黄经（Meeus算法简化版）
        n = jd - 2451545.0  # J2000.0以来的天数
        L = (280.460 + 0.9856474 * n) % 360  # 太阳黄经
        g = math.radians((357.528 + 0.9856003 * n) % 360)  # 平近点角
        lambda_sun = L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)  # 太阳黄经

        # 简化的太阳赤纬计算
        epsilon = 23.439  # 黄赤交角
        sun_dec = math.degrees(math.asin(math.sin(math.radians(lambda_sun)) *
                                         math.sin(math.radians(epsilon))))

        # 太阳赤经
        sun_ra = math.degrees(math.atan2(
            math.cos(math.radians(epsilon)) * math.sin(math.radians(lambda_sun)),
            math.cos(math.radians(lambda_sun))
        )) % 360

        return self.calculator(sun_ra, sun_dec, time)

    def compute_moon_position(self, time: datetime) -> Tuple[float, float, float]:
        """
        计算月亮位置
        返回: (高度角, 方位角, 月相 0-1)
        """
        # 简化月亮位置计算
        days_since_j2000 = self._to_julian_date(time) - 2451545.0

        # 月亮平均近点角
        moon_mean_anomaly = (134.963 + 13.064992 * days_since_j2000) % 360
        moon_mean_anomaly_rad = math.radians(moon_mean_anomaly)

        # 月亮黄经
        moon_lon = (218.317 + 13.176396 * days_since_j2000) % 360

        # 修正太阳对月亮的影响
        sun_mean_anomaly = (357.529 + 0.9856003 * days_since_j2000) % 360
        moon_lon = moon_lon - 1.274 * math.sin(math.radians(moon_mean_anomaly - 2 * sun_mean_anomaly))
        moon_lon = moon_lon + 0.658 * math.sin(2 * (math.radians(moon_lon) - math.radians(sun_mean_anomaly)))

        # 月亮黄纬
        moon_lat = 5.128 * math.sin(math.radians(moon_lon))

        # 月亮赤纬
        epsilon = 23.439
        moon_dec = math.degrees(math.asin(
            math.sin(math.radians(moon_lat)) * math.cos(math.radians(epsilon)) +
            math.cos(math.radians(moon_lat)) * math.sin(math.radians(epsilon)) *
            math.sin(math.radians(moon_lon))
        ))

        # 月亮赤经
        moon_ra = math.degrees(math.atan2(
            math.cos(math.radians(epsilon)) * math.sin(math.radians(moon_lon)) -
            math.sin(math.radians(moon_lat)) * math.sin(math.radians(epsilon)),
            math.cos(math.radians(moon_lat)) * math.cos(math.radians(moon_lon))
        )) % 360

        alt, az = self.calculator(moon_ra, moon_dec, time)

        # 计算月相
        known_new_moon = datetime(2026, 1, 3, 12, 0, 0)
        synodic_month = 29.53059
        days_diff = (time - known_new_moon).total_seconds() / 86400
        moon_phase = (days_diff % synodic_month) / synodic_month

        # 月亮照明度
        illumination = (1 - math.cos(2 * math.pi * moon_phase)) / 2

        return alt, az, moon_phase

    def compute_moon_distance_and_phase(
        self,
        target_ra: float,
        target_dec: float,
        time: datetime
    ) -> MoonPhase:
        """
        计算目标与月亮的距离和月相信息
        """
        moon_alt, moon_az, moon_phase = self.compute_moon_position(time)

        target_alt, target_az = self.calculator(target_ra, target_dec, time)

        # 计算角距离
        alt_diff = math.radians(target_alt - moon_alt)
        az_diff = math.radians(target_az - moon_az)

        cos_dist = (math.sin(math.radians(target_alt)) * math.sin(math.radians(moon_alt)) +
                    math.cos(math.radians(target_alt)) * math.cos(math.radians(moon_alt)) *
                    math.cos(az_diff))
        distance = math.degrees(math.acos(max(-1, min(1, cos_dist))))

        illumination = (1 - math.cos(2 * math.pi * moon_phase)) / 2

        return MoonPhase(
            phase=moon_phase,
            illumination=illumination,
            altitude=moon_alt,
            azimuth=moon_az,
            distance=distance
        )


# ============ 夜天文计算 ============

class AstronomicalNightCalculator:
    """
    夜天文时间计算器
    夜天文定义: 太阳中心在地平线以下18度
    """

    # 夜天文定义角度 (太阳中心在地平线以下多少度)
    SUN_DEPRESSION = 18.0

    def __init__(self, calculator: AstronomicalCalculator):
        self.calculator = calculator

    def compute_astronomical_nights(
        self,
        location: GeographicLocation,
        period: Tuple[datetime, datetime]
    ) -> List[VisibilityWindow]:
        """
        计算夜天文时间窗口

        算法:
        1. 在给定时间段内采样太阳位置
        2. 找出太阳高度角刚好等于-SUN_DEPRESSION的时刻（地平线以下18度）
        3. 这些时刻之间就是夜天文时间

        参数:
            location: 观测站位置
            period: 时间段 (开始, 结束)

        返回:
            List[VisibilityWindow]: 夜天文时间窗口列表
        """
        start_time, end_time = period
        windows: List[VisibilityWindow] = []

        # 以10分钟为间隔采样
        sample_interval = timedelta(minutes=10)
        current_time = start_time

        # 记录太阳在地平线以下的连续时间段
        in_astronomical_night = False
        night_start: Optional[datetime] = None
        altitude_samples: List[float] = []

        while current_time <= end_time:
            sun_alt, _ = self.calculator.compute_sun_position(current_time)

            if sun_alt < -self.SUN_DEPRESSION:
                # 太阳在地平线以下18度以下，进入夜天文时间
                if not in_astronomical_night:
                    in_astronomical_night = True
                    night_start = current_time
                    altitude_samples = []
            else:
                # 太阳升起
                if in_astronomical_night and night_start is not None:
                    # 结束当前的夜天文窗口
                    night_end = current_time

                    if len(altitude_samples) > 0:
                        windows.append(VisibilityWindow(
                            start=night_start,
                            end=night_end,
                            max_altitude=max(altitude_samples) if altitude_samples else -18,
                            avg_altitude=mean(altitude_samples) if altitude_samples else -18
                        ))

                    in_astronomical_night = False
                    night_start = None
                    altitude_samples = []

            if in_astronomical_night:
                altitude_samples.append(sun_alt)

            current_time += sample_interval

        # 处理最后一个窗口
        if in_astronomical_night and night_start is not None:
            night_end = end_time
            if len(altitude_samples) > 0:
                windows.append(VisibilityWindow(
                    start=night_start,
                    end=night_end,
                    max_altitude=max(altitude_samples),
                    avg_altitude=mean(altitude_samples)
                ))

        # 合并相邻的窗口（由于采样可能产生的小间隙）
        windows = self._merge_adjacent_windows(windows)

        return windows

    def _merge_adjacent_windows(
        self,
        windows: List[VisibilityWindow],
        gap_threshold: timedelta = timedelta(minutes=30)
    ) -> List[VisibilityWindow]:
        """合并相邻的夜天文窗口（处理小的间隙）"""
        if not windows:
            return []

        merged: List[VisibilityWindow] = [windows[0]]

        for window in windows[1:]:
            last = merged[-1]
            gap = window.start - last.end

            if gap <= gap_threshold:
                # 合并窗口
                combined_start = last.start
                combined_end = max(last.end, window.end)
                combined_max_alt = max(last.max_altitude, window.max_altitude)
                # 简化:使用两个窗口的平均值的平均
                combined_avg_alt = (last.avg_altitude + window.avg_altitude) / 2

                merged[-1] = VisibilityWindow(
                    start=combined_start,
                    end=combined_end,
                    max_altitude=combined_max_alt,
                    avg_altitude=combined_avg_alt
                )
            else:
                merged.append(window)

        return merged

    def is_astronomical_night(self, time: datetime) -> bool:
        """判断给定时间是否处于夜天文时间"""
        sun_alt, _ = self.calculator.compute_sun_position(time)
        return sun_alt < -self.SUN_DEPRESSION

    def get_twilight_times(
        self,
        location: GeographicLocation,
        date: datetime
    ) -> Dict[str, datetime]:
        """
        计算给定日期的各种晨昏时刻

        返回:
            包含以下键的字典:
            - sunrise: 日出时间
            - sunset: 日落时间
            - civil_twilight_start/end: 民用晨昏时刻 (太阳在地平线下6度)
            - nautical_twilight_start/end: 航海晨昏时刻 (太阳在地平线下12度)
            - astronomical_twilight_start/end: 天文晨昏时刻 (太阳在地平线下18度)
        """
        times: Dict[str, datetime] = {}

        # 搜索太阳高度角变化的关键点
        date_start = datetime.combine(date, dt_time(0, 0, 0))
        date_end = datetime.combine(date, dt_time(23, 59, 59))

        sample_interval = timedelta(minutes=1)
        current = date_start

        # 记录太阳高度角的变化
        altitudes: List[Tuple[datetime, float]] = []

        while current <= date_end:
            sun_alt, _ = self.calculator.compute_sun_position(current)
            altitudes.append((current, sun_alt))
            current += sample_interval

        # 找关键点
        for key, threshold in [('sunrise', 0), ('sunset', 0),
                                ('civil_twilight_start', -6), ('civil_twilight_end', -6),
                                ('nautical_twilight_start', -12), ('nautical_twilight_end', -12),
                                ('astronomical_twilight_start', -18), ('astronomical_twilight_end', -18)]:
            times[key] = self._find_crossing_time(altitudes, threshold, key.endswith('_start'))

        return times

    def _find_crossing_time(
        self,
        altitudes: List[Tuple[datetime, float]],
        threshold: float,
        is_start: bool
    ) -> datetime:
        """找到太阳高度角穿过阈值的时间"""
        for i in range(len(altitudes) - 1):
            t1, alt1 = altitudes[i]
            t2, alt2 = altitudes[i + 1]

            if is_start:
                # 寻找从高到低穿过阈值
                if alt1 >= threshold > alt2:
                    return self._interpolate_time(t1, t2, alt1, alt2, threshold)
            else:
                # 寻找从低到高穿过阈值
                if alt1 <= threshold < alt2:
                    return self._interpolate_time(t1, t2, alt1, alt2, threshold)

        # 默认返回中午
        return altitudes[len(altitudes) // 2][0]

    @staticmethod
    def _interpolate_time(
        t1: datetime,
        t2: datetime,
        alt1: float,
        alt2: float,
        threshold: float
    ) -> datetime:
        """线性插值找到精确的穿过时间"""
        if abs(alt2 - alt1) < 0.0001:
            return t1

        ratio = (threshold - alt1) / (alt2 - alt1)
        delta = (t2 - t1).total_seconds() * ratio
        return t1 + timedelta(seconds=delta)


# ============ 可见性周期计算 ============

class VisibilityCalculator:
    """
    目标可见性周期计算器
    计算目标在给定时间段的可见性窗口
    """

    def __init__(self, calculator: AstronomicalCalculator):
        self.calculator = calculator

    def compute_target_visibility(
        self,
        location: GeographicLocation,
        target_ra: float,
        target_dec: float,
        period: Tuple[datetime, datetime],
        constraints: Constraints
    ) -> List[VisibilityWindow]:
        """
        计算目标在给定时间段的可见性窗口

        算法:
        1. 以适当间隔采样，计算每个采样点的高度角
        2. 找出高度角满足约束的连续时间段
        3. 应用方位角约束（如果有）
        4. 过滤短于min_duration的窗口

        参数:
            location: 观测站位置
            target_ra: 赤经 (度)
            target_dec: 赤纬 (度)
            period: 时间段 (开始, 结束)
            constraints: 观测约束

        返回:
            List[VisibilityWindow]: 可见性窗口列表
        """
        start_time, end_time = period
        windows: List[VisibilityWindow] = []

        # 以2分钟为间隔采样（平衡精度和计算量）
        sample_interval = timedelta(minutes=2)
        current_time = start_time

        in_window = False
        window_start: Optional[datetime] = None
        altitude_samples: List[float] = []

        while current_time <= end_time:
            alt, az = self.calculator.compute_altitude_azimuth(
                target_ra, target_dec, current_time
            )

            # 检查约束
            meets_constraints = self._check_constraints(alt, az, constraints)

            if meets_constraints:
                if not in_window:
                    in_window = True
                    window_start = current_time
                    altitude_samples = []
                altitude_samples.append(alt)
            else:
                if in_window and window_start is not None:
                    # 结束当前窗口
                    window_end = current_time
                    window = self._create_visibility_window(
                        window_start, window_end, altitude_samples
                    )
                    if window is not None:
                        windows.append(window)
                    in_window = False
                    window_start = None
                    altitude_samples = []

            current_time += sample_interval

        # 处理最后一个窗口
        if in_window and window_start is not None:
            window_end = end_time
            window = self._create_visibility_window(
                window_start, window_end, altitude_samples
            )
            if window is not None:
                windows.append(window)

        # 合并相邻窗口
        windows = self._merge_adjacent_windows(windows)

        return windows

    def _check_constraints(
        self,
        altitude: float,
        azimuth: float,
        constraints: Constraints
    ) -> bool:
        """检查是否满足约束条件"""
        # 检查高度角约束
        if altitude < constraints.min_altitude:
            return False

        # 检查方位角约束
        if constraints.min_azimuth is not None and constraints.max_azimuth is not None:
            # 处理方位角跨越0度的情况
            if constraints.min_azimuth <= constraints.max_azimuth:
                if not (constraints.min_azimuth <= azimuth <= constraints.max_azimuth):
                    return False
            else:
                # 方位角跨越0度
                if not (azimuth >= constraints.min_azimuth or azimuth <= constraints.max_azimuth):
                    return False

        return True

    def _create_visibility_window(
        self,
        start: datetime,
        end: datetime,
        altitude_samples: List[float]
    ) -> Optional[VisibilityWindow]:
        """创建可见性窗口对象"""
        if len(altitude_samples) < 2:
            return None

        duration = end - start
        if duration < timedelta(minutes=5):  # 最小5分钟
            return None

        return VisibilityWindow(
            start=start,
            end=end,
            max_altitude=max(altitude_samples),
            avg_altitude=mean(altitude_samples)
        )

    def _merge_adjacent_windows(
        self,
        windows: List[VisibilityWindow],
        gap_threshold: timedelta = timedelta(minutes=10)
    ) -> List[VisibilityWindow]:
        """合并相邻的可见性窗口"""
        if not windows:
            return []

        merged: List[VisibilityWindow] = [windows[0]]

        for window in windows[1:]:
            last = merged[-1]
            gap = window.start - last.end

            if gap <= gap_threshold:
                combined_start = last.start
                combined_end = max(last.end, window.end)
                combined_max_alt = max(last.max_altitude, window.max_altitude)
                combined_avg_alt = (last.avg_altitude + window.avg_altitude) / 2

                merged[-1] = VisibilityWindow(
                    start=combined_start,
                    end=combined_end,
                    max_altitude=combined_max_alt,
                    avg_altitude=combined_avg_alt
                )
            else:
                merged.append(window)

        return merged

    def compute_operable_periods(
        self,
        location: GeographicLocation,
        target: ObservationTarget,
        astronomical_windows: List[VisibilityWindow],
        period: Tuple[datetime, datetime]
    ) -> List[VisibilityWindow]:
        """
        计算可操作时间段
        即可见性窗口与夜天文时间的交集

        参数:
            location: 观测站位置
            target: 观测目标
            astronomical_windows: 夜天文时间窗口
            period: 总时间段

        返回:
            List[VisibilityWindow]: 可操作时间段列表
        """
        operable: List[VisibilityWindow] = []

        # 获取目标的可见性窗口
        constraints = Constraints(min_altitude=target.min_altitude)
        visibility_windows = self.compute_target_visibility(
            location, target.ra, target.dec, period, constraints
        )

        # 计算每个可见性窗口与夜天文窗口的交集
        for vis_window in visibility_windows:
            for astro_window in astronomical_windows:
                intersection = self._compute_intersection(vis_window, astro_window)
                if intersection is not None:
                    operable.append(intersection)

        # 合并重叠的窗口
        operable = self._merge_overlapping_windows(operable)

        return operable

    def _compute_intersection(
        self,
        window1: VisibilityWindow,
        window2: VisibilityWindow
    ) -> Optional[VisibilityWindow]:
        """计算两个窗口的交集"""
        start = max(window1.start, window2.start)
        end = min(window1.end, window2.end)

        if start >= end:
            return None

        # 使用两个窗口高度角的最小值/最大值
        max_alt = min(window1.max_altitude, window2.max_altitude)
        avg_alt = (window1.avg_altitude + window2.avg_altitude) / 2

        return VisibilityWindow(
            start=start,
            end=end,
            max_altitude=max_alt,
            avg_altitude=avg_alt
        )

    def _merge_overlapping_windows(
        self,
        windows: List[VisibilityWindow]
    ) -> List[VisibilityWindow]:
        """合并重叠的时间窗口"""
        if not windows:
            return []

        # 按开始时间排序
        sorted_windows = sorted(windows, key=lambda w: w.start)

        merged: List[VisibilityWindow] = [sorted_windows[0]]

        for window in sorted_windows[1:]:
            last = merged[-1]

            if window.start <= last.end:
                # 有重叠，合并
                combined_end = max(last.end, window.end)
                combined_max_alt = max(last.max_altitude, window.max_altitude)
                combined_avg_alt = (last.avg_altitude + window.avg_altitude) / 2

                merged[-1] = VisibilityWindow(
                    start=last.start,
                    end=combined_end,
                    max_altitude=combined_max_alt,
                    avg_altitude=combined_avg_alt
                )
            else:
                merged.append(window)

        return merged


# ============ 调度碎片化分析 ============

class FragmentationAnalyzer:
    """
    调度碎片化分析器
    分析已调度块与可操作时间的关系，计算碎片化指标
    """

    def compute_fragmentation(
        self,
        operable_periods: List[VisibilityWindow],
        scheduled_blocks: List[VisibilityWindow]
    ) -> FragmentationMetrics:
        """
        计算调度碎片化指标

        算法:
        1. 计算总可操作时间
        2. 计算已调度时间
        3. 找出未调度的间隙
        4. 计算间隙统计指标

        参数:
            operable_periods: 可操作时间段列表
            scheduled_blocks: 已调度的时间块列表

        返回:
            FragmentationMetrics: 碎片化指标
        """
        if not operable_periods:
            return FragmentationMetrics(
                idle_operable_hours=0,
                gap_count=0,
                gap_mean=timedelta(0),
                gap_median=timedelta(0),
                gap_p90=timedelta(0),
                scheduled_fraction=0
            )

        # 计算总可操作时间
        total_operable = sum((wp.end - wp.start).total_seconds() for wp in operable_periods)
        total_operable_hours = total_operable / 3600

        # 计算已调度时间
        total_scheduled = sum((sb.end - sb.start).total_seconds() for sb in scheduled_blocks)
        total_scheduled_hours = total_scheduled / 3600

        # 计算已调度比例
        scheduled_fraction = total_scheduled / total_operable if total_operable > 0 else 0

        # 计算间隙
        gaps = self._compute_gaps(operable_periods, scheduled_blocks)

        # 计算间隙统计
        idle_hours = sum(g.total_seconds() for g in gaps) / 3600

        if gaps:
            gap_durations_seconds = [g.total_seconds() for g in gaps]
            gap_mean = timedelta(seconds=mean(gap_durations_seconds))
            gap_median = timedelta(seconds=median(gap_durations_seconds))
            sorted_gaps = sorted(gap_durations_seconds)
            p90_index = int(len(sorted_gaps) * 0.9)
            gap_p90 = timedelta(seconds=sorted_gaps[p90_index] if p90_index < len(sorted_gaps) else sorted_gaps[-1])
        else:
            gap_mean = timedelta(0)
            gap_median = timedelta(0)
            gap_p90 = timedelta(0)

        return FragmentationMetrics(
            idle_operable_hours=idle_hours,
            gap_count=len(gaps),
            gap_mean=gap_mean,
            gap_median=gap_median,
            gap_p90=gap_p90,
            scheduled_fraction=scheduled_fraction
        )

    def _compute_gaps(
        self,
        operable_periods: List[VisibilityWindow],
        scheduled_blocks: List[VisibilityWindow]
    ) -> List[timedelta]:
        """计算未调度的间隙"""
        gaps: List[timedelta] = []

        for operable in operable_periods:
            # 找出与当前可操作时间段重叠的已调度块
            overlapping = [
                sb for sb in scheduled_blocks
                if sb.start < operable.end and sb.end > operable.start
            ]

            if not overlapping:
                # 整个可操作时间段都是间隙
                gaps.append(operable.end - operable.start)
            else:
                # 按开始时间排序
                overlapping.sort(key=lambda x: x.start)

                current_pos = operable.start

                for block in overlapping:
                    if block.start > current_pos:
                        # 有一段间隙
                        gaps.append(block.start - current_pos)
                    current_pos = max(current_pos, block.end)

                # 检查末尾
                if current_pos < operable.end:
                    gaps.append(operable.end - current_pos)

        return gaps


# ============ 综合评分系统 ============

class ObservationScorer:
    """
    观测条件综合评分系统
    计算观测候选目标的综合评分
    """

    def __init__(self, calculator: AstronomicalCalculator):
        self.calculator = calculator

    def score_observation_candidate(
        self,
        target_ra: float,
        target_dec: float,
        time: datetime,
        location: GeographicLocation,
        moon_phase: float = 0.5,
        cloud_coverage: float = 0.0
    ) -> float:
        """
        综合评分观测候选目标

        评分公式:
        - 高度角权重: 35%
        - 云量权重: 25%
        - 月光权重: 20%
        - 观测窗口长度权重: 20%

        参数:
            target_ra: 赤经 (度)
            target_dec: 赤纬 (度)
            time: 观测时间
            location: 观测位置
            moon_phase: 月相 (0-1, 0=新月，1=满月)
            cloud_coverage: 云覆盖率 (0-1)

        返回:
            float: 0-100的评分
        """
        # 计算高度角
        altitude, _ = self.calculator.compute_altitude_azimuth(target_ra, target_dec, time)

        # 计算高度角评分 (越高越好)
        altitude_score = self._score_altitude(altitude)

        # 计算云量评分 (越少越好)
        cloud_score = self._score_cloud_coverage(cloud_coverage)

        # 计算月光评分 (越暗越好)
        moon_score = self._score_moon_light(moon_phase)

        # 计算窗口长度评分 (假设窗口长度为2小时作为满分基准)
        window_length_score = self._score_window_length(timedelta(hours=2))

        # 综合评分
        total_score = (
            altitude_score * 0.35 +
            cloud_score * 0.25 +
            moon_score * 0.20 +
            window_length_score * 0.20
        )

        return round(total_score, 2)

    def score_detailed(
        self,
        target: ObservationTarget,
        time: datetime,
        location: GeographicLocation,
        operable_windows: List[VisibilityWindow],
        moon_phase: float = 0.5,
        cloud_coverage: float = 0.0
    ) -> Dict[str, Any]:
        """
        计算详细的评分分解

        返回:
            包含各项评分和综合评分的字典
        """
        altitude, azimuth = self.calculator.compute_altitude_azimuth(
            target.ra, target.dec, time
        )

        # 获取当前时间所在的窗口
        current_window = None
        for window in operable_windows:
            if window.start <= time <= window.end:
                current_window = window
                break

        # 计算各维度评分
        altitude_score = self._score_altitude(altitude)
        cloud_score = self._score_cloud_coverage(cloud_coverage)
        moon_score = self._score_moon_light(moon_phase)

        # 窗口长度评分
        if current_window:
            window_length = current_window.end - current_window.start
        else:
            window_length = timedelta(hours=1)
        window_score = self._score_window_length(window_length)

        # 高度角变化评分（如果是长期观测）
        stability_score = 100  # 简化处理

        # 综合评分
        total_score = (
            altitude_score * 0.35 +
            cloud_score * 0.25 +
            moon_score * 0.20 +
            window_score * 0.20
        )

        return {
            'total_score': round(total_score, 2),
            'altitude_score': round(altitude_score, 2),
            'azimuth': round(azimuth, 2),
            'altitude': round(altitude, 2),
            'cloud_score': round(cloud_score, 2),
            'moon_score': round(moon_score, 2),
            'window_score': round(window_score, 2),
            'stability_score': stability_score,
            'window_duration_hours': round(window_length.total_seconds() / 3600, 2),
            'moon_phase': moon_phase,
            'cloud_coverage': cloud_coverage
        }

    @staticmethod
    def _score_altitude(altitude: float) -> float:
        """
        高度角评分
        30度以下: 线性下降至0
        30-60度: 线性上升至80
        60-90度: 线性上升至100
        """
        if altitude < 0:
            return 0
        elif altitude < 30:
            return (altitude / 30) * 50
        elif altitude < 60:
            return 50 + ((altitude - 30) / 30) * 30
        else:
            return 80 + ((altitude - 60) / 30) * 20

    @staticmethod
    def _score_cloud_coverage(cloud_coverage: float) -> float:
        """
        云量评分
        0%: 100分
        100%: 0分
        线性关系
        """
        return (1 - cloud_coverage) * 100

    @staticmethod
    def _score_moon_light(moon_phase: float) -> float:
        """
        月光评分
        新月(0): 100分
        满月(1): 0分
        使用余弦函数平滑过渡
        """
        return (math.cos(moon_phase * math.pi) + 1) / 2 * 100

    @staticmethod
    def _score_window_length(window_length: timedelta) -> float:
        """
        窗口长度评分
        2小时以上: 100分
        30分钟以下: 0分
        线性关系
        """
        hours = window_length.total_seconds() / 3600
        if hours <= 0.5:
            return 0
        elif hours >= 2:
            return 100
        else:
            return ((hours - 0.5) / 1.5) * 100


# ============ 主调度器 ============

class EnhancedObservationScheduler:
    """
    增强型观测调度器 v2.0
    整合所有组件，提供完整的调度功能

    v2.0 新增功能 (Issue #15, #31):
    - 基于假说优先级的调度
    - 多目标协调观测
    - 动态调度调整
    """

    def __init__(self, location: GeographicLocation):
        self.location = location
        self.calculator = AstronomicalCalculator(location)
        self.night_calculator = AstronomicalNightCalculator(self.calculator)
        self.visibility_calculator = VisibilityCalculator(self.calculator)
        self.fragmentation_analyzer = FragmentationAnalyzer()
        self.scorer = ObservationScorer(self.calculator)

        # v2.0 新增: 调度状态
        self._scheduled_targets: List[str] = []
        self._hypothesis_priority_map: Dict[str, float] = {}

    def set_hypothesis_priorities(
        self,
        priorities: Dict[str, float]
    ) -> None:
        """
        设置目标优先级映射 (假说ID -> 优先级分数)

        Args:
            priorities: Dict mapping hypothesis_id to priority score (0-100)
        """
        self._hypothesis_priority_map = priorities
        print(f"[Scheduler] 已设置 {len(priorities)} 个假说的优先级")

    def compute_astronomical_nights(
        self,
        period: Tuple[datetime, datetime]
    ) -> List[VisibilityWindow]:
        """计算夜天文时间窗口"""
        return self.night_calculator.compute_astronomical_nights(
            self.location, period
        )

    def compute_target_visibility(
        self,
        target: ObservationTarget,
        period: Tuple[datetime, datetime],
        constraints: Optional[Constraints] = None
    ) -> List[VisibilityWindow]:
        """计算目标可见性"""
        if constraints is None:
            constraints = Constraints(min_altitude=target.min_altitude)

        return self.visibility_calculator.compute_target_visibility(
            self.location, target.ra, target.dec, period, constraints
        )

    def compute_operable_periods(
        self,
        target: ObservationTarget,
        period: Tuple[datetime, datetime]
    ) -> List[VisibilityWindow]:
        """计算可操作时间段"""
        astronomical_windows = self.compute_astronomical_nights(period)
        return self.visibility_calculator.compute_operable_periods(
            self.location, target, astronomical_windows, period
        )

    def analyze_fragmentation(
        self,
        target: ObservationTarget,
        scheduled_blocks: List[VisibilityWindow],
        period: Tuple[datetime, datetime]
    ) -> FragmentationMetrics:
        """分析调度碎片化"""
        operable_periods = self.compute_operable_periods(target, period)
        return self.fragmentation_analyzer.compute_fragmentation(
            operable_periods, scheduled_blocks
        )

    def score_candidate(
        self,
        target: ObservationTarget,
        time: datetime,
        moon_phase: float = 0.5,
        cloud_coverage: float = 0.0
    ) -> float:
        """评分观测候选"""
        return self.scorer.score_observation_candidate(
            target.ra, target.dec, time, self.location, moon_phase, cloud_coverage
        )

    def score_detailed(
        self,
        target: ObservationTarget,
        time: datetime,
        moon_phase: float = 0.5,
        cloud_coverage: float = 0.0
    ) -> Dict[str, Any]:
        """详细评分"""
        operable_windows = self.compute_operable_periods(
            target, (time - timedelta(hours=2), time + timedelta(hours=2))
        )
        return self.scorer.score_detailed(
            target, time, self.location, operable_windows, moon_phase, cloud_coverage
        )

    def generate_schedule(
        self,
        targets: List[ObservationTarget],
        period: Tuple[datetime, datetime],
        moon_phases: Optional[Dict[datetime, float]] = None,
        cloud_coverages: Optional[Dict[datetime, float]] = None,
        max_targets_per_night: int = 5
    ) -> Dict[str, Any]:
        """
        生成观测计划

        参数:
            targets: 目标列表
            period: 时间段
            moon_phases: 每日月相字典
            cloud_coverages: 每日云覆盖率字典
            max_targets_per_night: 每夜最大目标数

        返回:
            包含调度结果的字典
        """
        if moon_phases is None:
            moon_phases = {}
        if cloud_coverages is None:
            cloud_coverages = {}

        # 计算夜天文窗口
        astronomical_windows = self.compute_astronomical_nights(period)

        schedule_results: List[Dict[str, Any]] = []
        all_scheduled_blocks: List[VisibilityWindow] = []

        for astro_window in astronomical_windows:
            night_date = astro_window.start.date()

            # 获取该夜的月相和云量
            moon_phase = moon_phases.get(night_date, 0.5)
            cloud_coverage = cloud_coverages.get(night_date, 0.1)

            # 为每个目标计算可操作时间
            target_windows: List[Tuple[ObservationTarget, VisibilityWindow, float]] = []

            for target in targets:
                operable = self.visibility_calculator.compute_operable_periods(
                    self.location, target, [astro_window],
                    (astro_window.start, astro_window.end)
                )

                for window in operable:
                    score = self.scorer.score_observation_candidate(
                        target.ra, target.dec, window.start,
                        self.location, moon_phase, cloud_coverage
                    )
                    target_windows.append((target, window, score))

            # 按评分排序
            target_windows.sort(key=lambda x: x[2], reverse=True)

            # 选择最高分的目标
            selected_targets: List[Dict[str, Any]] = []
            used_time: List[VisibilityWindow] = []

            for target, window, score in target_windows:
                # 检查时间是否冲突
                if self._has_conflict(window, used_time):
                    continue

                # 检查是否达到最大目标数
                if len(selected_targets) >= max_targets_per_night:
                    break

                selected_targets.append({
                    'target': target,
                    'window': window,
                    'score': score
                })
                used_time.append(window)
                all_scheduled_blocks.append(window)
                self._scheduled_targets.append(target.name)

            if selected_targets:
                schedule_results.append({
                    'date': night_date.isoformat(),
                    'astronomical_night': {
                        'start': astro_window.start.isoformat(),
                        'end': astro_window.end.isoformat(),
                        'duration_hours': (astro_window.end - astro_window.start).total_seconds() / 3600
                    },
                    'conditions': {
                        'moon_phase': moon_phase,
                        'cloud_coverage': cloud_coverage
                    },
                    'scheduled_targets': [
                        {
                            'name': st['target'].name,
                            'ra': st['target'].ra,
                            'dec': st['target'].dec,
                            'observation_type': st['target'].observation_type.value,
                            'window_start': st['window'].start.isoformat(),
                            'window_end': st['window'].end.isoformat(),
                            'max_altitude': st['window'].max_altitude,
                            'score': st['score']
                        }
                        for st in selected_targets
                    ]
                })

        # 计算整体碎片化指标
        if astronomical_windows:
            # 将所有可操作时间合并
            all_operable = []
            for target in targets:
                all_operable.extend(
                    self.visibility_calculator.compute_operable_periods(
                        self.location, target, astronomical_windows,
                        (astronomical_windows[0].start, astronomical_windows[-1].end)
                    )
                )

            fragmentation = self.fragmentation_analyzer.compute_fragmentation(
                all_operable, all_scheduled_blocks
            )
        else:
            fragmentation = FragmentationMetrics(
                idle_operable_hours=0,
                gap_count=0,
                gap_mean=timedelta(0),
                gap_median=timedelta(0),
                gap_p90=timedelta(0),
                scheduled_fraction=0
            )

        return {
            'location': {
                'name': self.location.name,
                'latitude': self.location.latitude,
                'longitude': self.location.longitude,
                'elevation': self.location.elevation
            },
            'period': {
                'start': period[0].isoformat(),
                'end': period[1].isoformat()
            },
            'nights_count': len(schedule_results),
            'fragmentation': {
                'idle_operable_hours': fragmentation.idle_operable_hours,
                'gap_count': fragmentation.gap_count,
                'gap_mean_minutes': fragmentation.gap_mean.total_seconds() / 60,
                'gap_median_minutes': fragmentation.gap_median.total_seconds() / 60,
                'gap_p90_minutes': fragmentation.gap_p90.total_seconds() / 60,
                'scheduled_fraction': fragmentation.scheduled_fraction
            },
            'schedule': schedule_results
        }

    def _has_conflict(
        self,
        window: VisibilityWindow,
        used_windows: List[VisibilityWindow],
        buffer_minutes: int = 30
    ) -> bool:
        """检查时间窗口是否与已使用窗口冲突"""
        buffer = timedelta(minutes=buffer_minutes)

        for used in used_windows:
            if (window.start - buffer < used.end and
                window.end + buffer > used.start):
                return True

        return False

    def get_scheduled_targets(self) -> List[str]:
        """获取已调度的目标列表"""
        return self._scheduled_targets.copy()

    def reset_schedule(self) -> None:
        """重置调度器状态"""
        self._scheduled_targets.clear()
        print("[Scheduler] 调度器已重置")


# ============ 兼容性别名 ============

# 为了与原有observation_scheduler.py兼容
Location = GeographicLocation


# ============ 模拟数据测试 ============

def run_demo():
    """运行演示测试"""
    print("=" * 70)
    print("天问-AGI 增强型观测调度引擎 (TSI算法参考实现)")
    print("=" * 70)

    # 创建观测位置（冷湖观测站）
    location = GeographicLocation(
        name="冷湖观测站",
        latitude=38.5,
        longitude=93.0,
        elevation=3200
    )
    print(f"\n观测位置: {location.name}")
    print(f"  纬度: {location.latitude}°")
    print(f"  经度: {location.longitude}°")
    print(f"  海拔: {location.elevation}m")

    # 创建调度器
    scheduler = EnhancedObservationScheduler(location)

    # 1. 计算夜天文时间
    print("\n" + "-" * 70)
    print("1. 夜天文时间计算")
    print("-" * 70)

    test_date = datetime(2026, 5, 1)
    period = (datetime(2026, 5, 1, 0, 0), datetime(2026, 5, 2, 0, 0))

    astronomical_windows = scheduler.compute_astronomical_nights(period)

    for window in astronomical_windows:
        duration_hours = (window.end - window.start).total_seconds() / 3600
        print(f"  夜天文时间: {window.start.strftime('%H:%M')} - {window.end.strftime('%H:%M')}")
        print(f"    持续时间: {duration_hours:.2f} 小时")
        print(f"    最高太阳高度: {window.max_altitude:.1f}°")

    # 2. 计算目标可见性
    print("\n" + "-" * 70)
    print("2. 目标可见性计算")
    print("-" * 70)

    # 创建测试目标
    targets = [
        ObservationTarget(
            name="M31 (仙女座星系)",
            ra=10.6847,  # 赤经 (度)
            dec=41.2687,  # 赤纬 (度)
            observation_type=ObservationType.IMAGING,
            priority=1
        ),
        ObservationTarget(
            name="M42 (猎户座大星云)",
            ra=83.8221,
            dec=-5.3911,
            observation_type=ObservationType.IMAGING,
            priority=1
        ),
        ObservationTarget(
            name="M51 (漩涡星系)",
            ra=202.4696,
            dec=47.1953,
            observation_type=ObservationType.IMAGING,
            priority=2
        ),
        ObservationTarget(
            name="织女星",
            ra=279.2347,
            dec=38.7836,
            observation_type=ObservationType.PHOTOMETRY,
            priority=3
        )
    ]

    for target in targets:
        operable = scheduler.compute_operable_periods(target, period)

        print(f"\n  目标: {target.name}")
        print(f"    赤经: {target.ra:.2f}°, 赤纬: {target.dec:.2f}°")

        if operable:
            total_hours = sum((w.end - w.start).total_seconds() / 3600 for w in operable)
            print(f"    可操作总时间: {total_hours:.2f} 小时")

            for window in operable[:2]:  # 只显示前两个窗口
                print(f"    窗口: {window.start.strftime('%H:%M')} - {window.end.strftime('%H:%M')}")
                print(f"      最高高度: {window.max_altitude:.1f}°, 平均高度: {window.avg_altitude:.1f}°")
        else:
            print("    无可见窗口")

    # 3. 碎片化分析
    print("\n" + "-" * 70)
    print("3. 调度碎片化分析")
    print("-" * 70)

    # 模拟已调度的时间块
    simulated_scheduled = []
    for astro_window in astronomical_windows[:1]:
        # 假设调度了2个目标
        mid = astro_window.start + (astro_window.end - astro_window.start) / 2
        simulated_scheduled.append(VisibilityWindow(
            start=astro_window.start + timedelta(hours=1),
            end=astro_window.start + timedelta(hours=2, minutes=30),
            max_altitude=60,
            avg_altitude=50
        ))
        simulated_scheduled.append(VisibilityWindow(
            start=astro_window.start + timedelta(hours=3),
            end=astro_window.start + timedelta(hours=4),
            max_altitude=70,
            avg_altitude=55
        ))

    fragmentation = scheduler.fragmentation_analyzer.compute_fragmentation(
        astronomical_windows, simulated_scheduled
    )

    print(f"  空闲可操作时间: {fragmentation.idle_operable_hours:.2f} 小时")
    print(f"  间隙数量: {fragmentation.gap_count}")
    print(f"  间隙平均时长: {fragmentation.gap_mean.total_seconds() / 60:.1f} 分钟")
    print(f"  间隙中位数时长: {fragmentation.gap_median.total_seconds() / 60:.1f} 分钟")
    print(f"  间隙90分位时长: {fragmentation.gap_p90.total_seconds() / 60:.1f} 分钟")
    print(f"  已调度比例: {fragmentation.scheduled_fraction:.1%}")

    # 4. 综合评分
    print("\n" + "-" * 70)
    print("4. 观测条件综合评分")
    print("-" * 70)

    test_time = datetime(2026, 5, 1, 23, 0)
    moon_phase = 0.25  # 弦月
    cloud_coverage = 0.1  # 10%云量

    print(f"  测试时间: {test_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  月相: {moon_phase:.2f} (接近新月)")
    print(f"  云覆盖率: {cloud_coverage:.0%}")

    for target in targets[:2]:
        score = scheduler.score_candidate(target, test_time, moon_phase, cloud_coverage)
        detailed = scheduler.score_detailed(target, test_time, moon_phase, cloud_coverage)

        print(f"\n  目标: {target.name}")
        print(f"    综合评分: {score:.1f}/100")
        print(f"    高度角评分: {detailed['altitude_score']:.1f} (高度: {detailed['altitude']:.1f}°)")
        print(f"    云量评分: {detailed['cloud_score']:.1f}")
        print(f"    月光评分: {detailed['moon_score']:.1f}")
        print(f"    窗口评分: {detailed['window_score']:.1f}")

    # 5. 生成调度计划
    print("\n" + "-" * 70)
    print("5. 生成观测计划")
    print("-" * 70)

    schedule = scheduler.generate_schedule(
        targets=targets,
        period=(
            datetime(2026, 5, 1, 12, 0),
            datetime(2026, 5, 7, 12, 0)
        ),
        moon_phases={
            datetime(2026, 5, 1).date(): 0.25,
            datetime(2026, 5, 2).date(): 0.30,
            datetime(2026, 5, 3).date(): 0.35,
            datetime(2026, 5, 4).date(): 0.40,
            datetime(2026, 5, 5).date(): 0.45,
            datetime(2026, 5, 6).date(): 0.50,
            datetime(2026, 5, 7).date(): 0.55,
        },
        cloud_coverages={
            datetime(2026, 5, 1).date(): 0.1,
            datetime(2026, 5, 2).date(): 0.15,
            datetime(2026, 5, 3).date(): 0.05,
            datetime(2026, 5, 4).date(): 0.2,
            datetime(2026, 5, 5).date(): 0.1,
            datetime(2026, 5, 6).date(): 0.3,
            datetime(2026, 5, 7).date(): 0.1,
        },
        max_targets_per_night=4
    )

    print(f"\n  调度统计:")
    print(f"    覆盖夜数: {schedule['nights_count']}")
    print(f"    总已调度比例: {schedule['fragmentation']['scheduled_fraction']:.1%}")
    print(f"    空闲可操作时间: {schedule['fragmentation']['idle_operable_hours']:.1f} 小时")

    print(f"\n  调度详情:")
    for night in schedule['schedule']:
        print(f"\n    日期: {night['date']}")
        print(f"    夜天文时长: {night['astronomical_night']['duration_hours']:.1f} 小时")
        print(f"    月相: {night['conditions']['moon_phase']:.2f}, 云量: {night['conditions']['cloud_coverage']:.0%}")
        print(f"    调度目标数: {len(night['scheduled_targets'])}")

        for st in night['scheduled_targets']:
            print(f"      - {st['name']}: {st['window_start'].split('T')[1][:5]} - {st['window_end'].split('T')[1][:5]}")
            print(f"        最高高度: {st['max_altitude']:.1f}°, 评分: {st['score']:.1f}")

    # 6. 月亮位置计算
    print("\n" + "-" * 70)
    print("6. 月亮与目标距离计算")
    print("-" * 70)

    for target in targets[:2]:
        moon_info = scheduler.calculator.compute_moon_distance_and_phase(
            target.ra, target.dec, test_time
        )

        print(f"\n  目标: {target.name}")
        print(f"    月亮相位: {moon_info.phase:.2f}")
        print(f"    月亮照明度: {moon_info.illumination:.1%}")
        print(f"    目标-月亮角距离: {moon_info.distance:.1f}°")

    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)

    return schedule


if __name__ == "__main__":
    run_demo()
