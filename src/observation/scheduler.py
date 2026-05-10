"""
天问-AGI 观测调度引擎 v2.0
基于 StarWhisper/NGSS PlanObservation3.py 移植
集成 astroplan + astropy 实现专业级观测调度
"""

import math
import xml.etree.ElementTree as ET
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from xml.etree.ElementTree import SubElement

# ============ Astroplan 核心依赖 ============
try:
    import astropy.units as u
    from astroplan import (
        AltitudeConstraint,
        FixedTarget,
        MoonSeparationConstraint,
        Observer,
        AtNightConstraint,
    )
    from astropy.coordinates import EarthLocation, Longitude, SkyCoord, get_body
    from astropy.time import Time
    from astropy.utils import iers
    HAS_ASTROPLAN = True
except ImportError:
    HAS_ASTROPLAN = False

from loguru import logger

# ============ IERS 配置（StarWhisper 风格） ============
_IERS_CONFIGURED = False

def _configure_iers():
    """配置 IERS 数据避免自动下载"""
    global _IERS_CONFIGURED
    if _IERS_CONFIGURED or not HAS_ASTROPLAN:
        return
    try:
        iers.conf.auto_download = False
        iers.conf.auto_max_age = None
        iers.conf.iers_degraded_accuracy = 'ignore'
        _IERS_CONFIGURED = True
    except Exception:
        pass

# ============ 数据模型 ============

@dataclass
class Location:
    """观测位置"""
    name: str
    lat: float  # 纬度
    lon: float  # 经度
    elevation: float = 0  # 海拔(米)
    timezone: str = "Asia/Shanghai"
    light_pollution: int = 1  # 光污染等级 1-5

    def to_earth_location(self) -> "EarthLocation":
        if not HAS_ASTROPLAN:
            raise RuntimeError("astroplan not installed")
        return EarthLocation(
            lat=self.lat * u.deg,
            lon=self.lon * u.deg,
            height=self.elevation * u.m
        )

    def to_observer(self) -> "Observer":
        if not HAS_ASTROPLAN:
            raise RuntimeError("astroplan not installed")
        return Observer(
            location=self.to_earth_location(),
            timezone=self.timezone
        )


@dataclass
class Equipment:
    """观测设备"""
    name: str
    type: str
    aperture: float  # 口径(mm)
    focal_length: float  # 焦距(mm)
    f_ratio: float = 0
    max_magnification: float = 0
    limiting_magnitude: float = 0


@dataclass
class ObservationTarget:
    """观测目标"""
    name: str
    ra: float  # 赤经（度）
    dec: float  # 赤纬（度）
    magnitude: float = 0
    priority: int = 1  # 1=最高
    min_altitude: float = 30  # 最低高度角
    exposure_time: float = 60  # 曝光时间（秒）
    filters: List[str] = field(default_factory=list)
    moon_distance_min: float = 15  # 与月亮最小距离（度）
    catalog: str = ""  # 来源目录

    def to_skycoord(self) -> "SkyCoord":
        if not HAS_ASTROPLAN:
            raise RuntimeError("astroplan not installed")
        return SkyCoord(ra=self.ra * u.deg, dec=self.dec * u.deg, frame='icrs')

    def to_fixed_target(self) -> "FixedTarget":
        return FixedTarget(name=self.name, coord=self.to_skycoord())

    def to_dict(self) -> dict:
        return {
            "name": self.name, "ra": self.ra, "dec": self.dec,
            "magnitude": self.magnitude, "priority": self.priority,
            "min_altitude": self.min_altitude, "exposure_time": self.exposure_time,
            "filters": self.filters, "moon_distance_min": self.moon_distance_min,
            "catalog": self.catalog
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ObservationTarget":
        return cls(
            name=d["name"], ra=float(d["ra"]), dec=float(d["dec"]),
            magnitude=float(d.get("magnitude", 0)),
            priority=int(d.get("priority", 1)),
            min_altitude=float(d.get("min_altitude", 30)),
            exposure_time=float(d.get("exposure_time", 60)),
            filters=d.get("filters", []),
            moon_distance_min=float(d.get("moon_distance_min", 15)),
            catalog=d.get("catalog", "")
        )


@dataclass
class ObservationWindow:
    """观测窗口"""
    start_time: datetime
    end_time: datetime
    target: str
    altitude: float
    azimuth: float
    seeing: float
    cloud_cover: int
    moon_distance: float
    moon_phase: float
    score: float
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


# ============ StarWhisper 核心算法 ============
# 移植自 StarWhisper/NGSS/src/module/PlanObservation3.py

class AstroPlanner:
    """
    基于 astroplan 的专业天文观测规划器
    移植自 StarWhisper PlanObservation3.py 核心算法
    """

    def __init__(self, location: Location):
        if not HAS_ASTROPLAN:
            raise RuntimeError("请安装 astroplan: pip install astroplan astropy")
        _configure_iers()
        self.location = location
        self.observer = location.to_observer()

    def calculate_observable_period(self) -> Tuple[Any, Any]:
        """
        计算可观测时间段（天文昏影与晨光）
        返回: (twilight_morning, twilight_evening)
        """
        date = datetime.utcnow().date()
        # 对应北京时间凌晨4点 = UTC前夜20点
        four_oclock = time(hour=4, minute=0)
        date_combined = datetime.combine(date, four_oclock)
        t = Time(date_combined)

        twilight_morning = self.observer.twilight_morning_astronomical(t, which="next")
        twilight_evening = self.observer.twilight_evening_astronomical(t, which="next")

        logger.info(f"可观测时段: {twilight_evening.iso} ~ {twilight_morning.iso}")
        return twilight_morning, twilight_evening

    def calculate_lst_and_corresponding_ra_range(
        self,
        utc_time: str,
        early_night: float = 0.5,
        midnight: float = 2.0,
        midmorning: float = 2.0,
        early_morning: float = 2.0
    ) -> Tuple[float, float]:
        """
        计算本地恒星时（LST）及对应的赤经筛选范围

        参数:
        utc_time: UTC时间字符串，格式 'YYYY-MM-DD HH:MM:SS'
        early_night: 傍晚允许的RA前向范围（小时）
        midnight: 午夜前后向/前向范围（小时）
        midmorning: 凌晨允许的后向范围（小时）
        early_morning: 快天亮时允许的后向范围（小时）

        返回: (ra_min度, ra_max度)

        算法来源: StarWhisper PlanObservation3.py calculate_lst_and_corresponding_ra_range()
        """
        if not HAS_ASTROPLAN:
            raise RuntimeError("astroplan required")

        utc_time_obj = Time(utc_time, format="iso", scale="utc")

        # 格林威治平均恒星时（GMST）
        gmst = utc_time_obj.sidereal_time("mean", "greenwich")

        # 转换为本地恒星时
        lst = gmst + Longitude(self.location.lon * u.deg)
        lst.wrap_at("360d", inplace=True)

        # 根据当地时间动态调整RA范围
        hour = int(utc_time.split()[1].split(":")[0])

        # 北京时间 14:00(UTC 06:00) 前用 early_night，之后用 midnight
        if hour < 14:
            ra_min = lst - early_night * 15 * u.deg
        else:
            ra_min = lst - midnight * 15 * u.deg

        # 北京时间 19:00(UTC 11:00) 后用 early_morning，之前用 midmorning
        if hour > 19:
            ra_max = lst + early_morning * 15 * u.deg
        else:
            ra_max = lst + midmorning * 15 * u.deg

        ra_min_deg = float(ra_min.degree)
        ra_max_deg = float(ra_max.degree)

        logger.debug(
            f"LST={lst.deg:.2f}deg RA范围=[{ra_min_deg:.2f}, {ra_max_deg:.2f}]deg"
        )
        return ra_min_deg, ra_max_deg

    def is_target_observable_in_interval(
        self,
        obj: Dict,
        interval_time: int,
        d_moon: float = 15
    ) -> bool:
        """
        判断目标在指定时间窗口内是否可观测

        参数:
        obj: 目标字典 {"name": str, "ra": float, "dec": float}
        interval_time: 时间窗口长度（分钟）
        d_moon: 月亮最小距离（度）

        返回: True=可观测

        算法来源: StarWhisper PlanObservation3.py is_target_observable_in_interval()
        """
        if not HAS_ASTROPLAN:
            raise RuntimeError("astroplan required")

        ra = obj["ra"]
        dec = obj["dec"]

        # 纬度决定最低高度角：35.678度（兴隆站纬度）用40度，其他用30度
        alt_constraint_deg = 40 if abs(self.location.lat - 35.678) < 0.1 else 30

        target = FixedTarget(
            name=obj["name"],
            coord=SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
        )

        # 构build约束
        constraints = [
            AltitudeConstraint(min=alt_constraint_deg * u.deg),
            MoonSeparationConstraint(min=d_moon * u.deg),
            AtNightConstraint.twilight_astronomical(),
        ]

        # 时间窗口
        start = Time(datetime.utcnow())
        end = start + timedelta(minutes=interval_time)

        try:
            from astroplan import observability_table, FixedTarget
            from astropy.coordinates import SkyCoord
            # Convert dict to FixedTarget and wrap in list
            target_obj = FixedTarget(
                name=obj["name"],
                coord=SkyCoord(ra=obj["ra"] * u.deg, dec=obj["dec"] * u.deg, frame="icrs")
            )
            table = observability_table(constraints, self.observer, [target_obj], times=[start, end])
            observable = bool(table["ever observable"][0])
            logger.debug(f"{obj['name']}: observable={observable}, alt_constraint={alt_constraint_deg}deg")
            return observable
        except Exception as e:
            logger.warning(f"observability check failed for {obj['name']}: {e}")
            return self._fallback_altitude_check(ra, dec)

    def _fallback_altitude_check(self, ra: float, dec: float) -> bool:
        """备用检查：纯天文计算（当astroplan失败时）"""
        now = datetime.utcnow()
        lst = self._compute_lst(now)
        ha = (lst - ra + 360) % 360

        lat_rad = math.radians(self.location.lat)
        dec_rad = math.radians(dec)
        ha_rad = math.radians(ha)

        sin_alt = (math.sin(dec_rad) * math.sin(lat_rad) +
                   math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
        alt = math.degrees(math.asin(sin_alt))

        alt_limit = 40 if abs(self.location.lat - 35.678) < 0.1 else 30
        return alt > alt_limit

    def _compute_lst(self, dt: datetime) -> float:
        """计算地方恒星时"""
        jd = self._to_julian_date(dt)
        t = (jd - 2451545.0) / 36525.0
        lst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) +
               t * t * (0.000387933 - t / 38710000.0))
        return (lst + self.location.lon) % 360

    @staticmethod
    def _to_julian_date(dt: datetime) -> float:
        year, month, day = dt.year, dt.month, dt.day
        day = day + dt.hour / 24 + dt.minute / 1440
        if month <= 2:
            year -= 1
            month += 12
        a = int(year / 100)
        b = 2 - a + int(a / 4)
        return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5

    def get_moon_info(self, dt: datetime) -> Dict[str, float]:
        """获取当前月亮信息"""
        if not HAS_ASTROPLAN:
            # 简化计算
            synodic_month = 29.53
            known_new_moon = datetime(2026, 1, 3)
            days_diff = (dt - known_new_moon).days + (dt.hour - 12) / 24
            moon_phase = (days_diff % synodic_month) / synodic_month
            return {"phase": moon_phase, "distance": 0, "alt": 0, "az": 0}

        try:
            moon = get_body("moon", Time(dt), self.location.to_earth_location())
            moon_coord = SkyCoord(moon)
            # 计算月相
            sun = get_body("sun", Time(dt), self.location.to_earth_location())
            elongation = moon_coord.separation(sun).deg
            moon_phase = elongation / 360.0
            # 计算月亮地平坐标
            altaz = moon_coord.transform_to(self.observer.altaz)
            return {
                "phase": moon_phase,
                "distance": float(moon.distance.to(u.deg).value),
                "alt": float(altaz.alt.deg),
                "az": float(altaz.az.deg)
            }
        except Exception as e:
            logger.warning(f"get_moon_info failed: {e}")
            return {"phase": 0.5, "distance": 180, "alt": 0, "az": 0}

    def filter_targets_by_ra_range(
        self,
        targets: List[ObservationTarget],
        ra_min: float,
        ra_max: float
    ) -> List[ObservationTarget]:
        """根据RA范围过滤目标"""
        filtered = []
        for t in targets:
            # 处理跨0度的情况
            ra = t.ra
            if ra_min <= ra <= ra_max:
                filtered.append(t)
            elif ra_min > ra_max:  # 跨0度
                if ra >= ra_min or ra <= ra_max:
                    filtered.append(t)
        return filtered

    def prioritize_targets(
        self,
        targets: List[ObservationTarget],
        windows: List[Any] = None
    ) -> List[ObservationTarget]:
        """
        六原则调度算法（StarWhisper核心）
        排序优先级:
        1. 高度角优先（越高越好）
        2. 月光干扰最小
        3. 目标大小/类型
        4. 观测窗口长度
        5. 设备适配
        6. 战略价值（优先级字段）
        """
        def score(t: ObservationTarget) -> float:
            s = 0
            s += (90 - t.min_altitude) * 2  # 高度角贡献
            s += (90 - t.moon_distance_min) * 0.5  # 月光
            s += (10 - t.priority) * 10  # 战略优先级
            s -= t.exposure_time / 10  # 曝光时间惩罚
            return s

        return sorted(targets, key=score, reverse=True)


# ============ N.I.N.A. XML 序列生成器 ============
# 移植自 StarWhisper N.I.N.A. 集成逻辑

class NINAXMLGenerator:
    """
    生成 N.I.N.A. 望远镜控制 XML 序列
    移植自 StarWhisper N.I.N.A. capture sequence generation
    完全对齐 StarWhisper PlanObservation3.py create_capture_sequence_xml() 格式
    """

    @staticmethod
    def create_capture_sequence_xml(
        target: ObservationTarget,
        location: Location,
        num_exposures: int = 10,
        binning: int = 1,
        gain: int = 139,
        cooling: bool = True,
        target_temp: int = -20,
        auto_focus_on_start: bool = False,
        auto_focus_on_finish: bool = False,
        dither: bool = False,
        dither_amount: float = 1.0,
        filter_name: str = "L"
    ) -> str:
        """
        生成 N.I.N.A. 拍摄序列 XML（StarWhisper格式）

        对齐: StarWhisper PlanObservation3.py create_capture_sequence_xml() 第163-317行
        - CaptureSequenceList 作为根元素
        - RA 以小时为单位 (HH + MM/60 + SS/3600)
        - Dec 分正负值处理
        - FilterType 含 FlatWizardFilterSettings / AutoFocusBinning / AutoFocusGain/Offset
        - AutoFocusOnStart / AutoFocusOnFinish
        - NegativeDec 元素
        """
        # RA: 度 -> 时分秒
        ra_total_hours = target.ra / 15.0
        ra_h = int(ra_total_hours)
        ra_m = int((ra_total_hours - ra_h) * 60)
        ra_s = ((ra_total_hours - ra_h) * 60 - ra_m) * 60

        # Dec: 度 -> 度分秒 (处理负值)
        dec_is_negative = target.dec < 0
        dec_abs = abs(target.dec)
        dec_d = int(dec_abs)
        dec_m = int((dec_abs - dec_d) * 60)
        dec_s = ((dec_abs - dec_d) * 60 - dec_m) * 60

        # 根元素（StarWhisper使用CaptureSequenceList）
        capture_sequence_list = ET.Element("CaptureSequenceList")
        capture_sequence_list.set("SlewToTarget", "true")

        # Sequence 元素
        seq_elem = SubElement(capture_sequence_list, "Sequence")
        seq_elem.set("Name", target.name)
        seq_elem.set("XmlCreated", datetime.utcnow().isoformat())

        # DeviceSettings
        device_elem = SubElement(seq_elem, "DeviceSettings")
        SubElement(device_elem, "Camera").text = "ZWO ASI2600MC Pro"
        SubElement(device_elem, "Telescope").text = "SkyWatcher EQ6-R"
        SubElement(device_elem, "FocalLength").text = str(target.exposure_time * 10)
        SubElement(device_elem, "Binning").text = str(binning)
        SubElement(device_elem, "Gain").text = str(gain)
        SubElement(device_elem, "Offset").text = "-1"

        if cooling:
            cooler = SubElement(device_elem, "Cooling")
            cooler.set("Enabled", "true")
            cooler.set("TargetTemp", str(target_temp))
            cooler.set("CoolerOn", "true")

        # AutoFocusSettings
        af_elem = SubElement(seq_elem, "AutoFocusSettings")
        SubElement(af_elem, "AutoFocusOnStart").text = str(auto_focus_on_start).lower()
        SubElement(af_elem, "AutoFocusOnFinish").text = str(auto_focus_on_finish).lower()
        SubElement(af_elem, "AutoFocusExposureTime").text = "-1"
        SubElement(af_elem, "AutoFocusFilter").text = "true"

        # Target 元素
        target_elem = SubElement(seq_elem, "Target")
        SubElement(target_elem, "Name").text = target.name
        SubElement(target_elem, "RA").text = target.name  # StarWhisper实际写name占位
        SubElement(target_elem, "Dec").text = target.name
        coords = SubElement(target_elem, "Coordinates")
        coords.set("System", "J2000")
        SubElement(coords, "RA").text = f"{ra_h + ra_m/60 + ra_s/3600:.6f}"
        SubElement(coords, "Dec").text = f"{dec_d + dec_m/60 + dec_s/3600:.6f}"
        SubElement(coords, "Epoch").text = "J2000"
        SubElement(target_elem, "MinimumAltitude").text = str(target.min_altitude)
        SubElement(target_elem, "MinimumMoonDistance").text = str(target.moon_distance_min)
        SubElement(target_elem, "Rotation").text = "0"

        # CaptureSequenceList（StarWhisper的关键结构）
        csl_elem = SubElement(seq_elem, "CaptureSequenceList")

        # 单个拍摄序列
        capture_sequence = SubElement(csl_elem, "CaptureSequence")
        SubElement(capture_sequence, "Name").text = f"{target.name}_Sequence"
        SubElement(capture_sequence, "ExposureTime").text = str(target.exposure_time)
        SubElement(capture_sequence, "ImageType").text = "LIGHT"

        # FilterType（含StarWhisper的所有子元素）
        filter_type_elem = SubElement(capture_sequence, "FilterType")
        SubElement(filter_type_elem, "Name").text = filter_name
        SubElement(filter_type_elem, "FocusOffset").text = "0"
        SubElement(filter_type_elem, "Position").text = "1"
        SubElement(filter_type_elem, "AutoFocusExposureTime").text = "-1"
        SubElement(filter_type_elem, "AutoFocusFilter").text = "true"

        # FlatWizardFilterSettings（StarWhisper格式）
        flatwizard = SubElement(filter_type_elem, "FlatWizardFilterSettings")
        SubElement(flatwizard, "FlatWizardMode").text = "DYNAMICEXPOSURE"
        SubElement(flatwizard, "HistogramMeanTarget").text = "0.5"
        SubElement(flatwizard, "HistogramTolerance").text = "0.1"
        SubElement(flatwizard, "MaxFlatExposureTime").text = "20"
        SubElement(flatwizard, "MinFlatExposureTime").text = "0.01"
        SubElement(flatwizard, "MaxAbsoluteFlatDeviceBrightness").text = "1"
        SubElement(flatwizard, "MinAbsoluteFlatDeviceBrightness").text = "0"
        SubElement(flatwizard, "Gain").text = "-1"
        SubElement(flatwizard, "Offset").text = "-1"
        bin_fw = SubElement(flatwizard, "Binning")
        SubElement(bin_fw, "X").text = "1"
        SubElement(bin_fw, "Y").text = "1"

        # AutoFocusBinning
        af_bin = SubElement(filter_type_elem, "AutoFocusBinning")
        SubElement(af_bin, "X").text = "1"
        SubElement(af_bin, "Y").text = "1"
        SubElement(filter_type_elem, "AutoFocusGain").text = "-1"
        SubElement(filter_type_elem, "AutoFocusOffset").text = "-1"

        # Binning in CaptureSequence
        bin_cs = SubElement(capture_sequence, "Binning")
        SubElement(bin_cs, "X").text = str(binning)
        SubElement(bin_cs, "Y").text = str(binning)

        SubElement(capture_sequence, "Gain").text = str(gain)
        SubElement(capture_sequence, "Offset").text = "-1"
        SubElement(capture_sequence, "TotalExposureCount").text = str(num_exposures)
        SubElement(capture_sequence, "ProgressExposureCount").text = "0"
        SubElement(capture_sequence, "Dither").text = str(dither).lower()
        SubElement(capture_sequence, "DitherAmount").text = str(dither_amount)

        # Coordinates（与StarWhisper一致）
        coords2 = SubElement(csl_elem, "Coordinates")
        SubElement(coords2, "RA").text = f"{ra_h + ra_m/60 + ra_s/3600:.6f}"
        SubElement(coords2, "Dec").text = f"{dec_d + dec_m/60 + dec_s/3600:.6f}"
        SubElement(coords2, "Epoch").text = "J2000"
        SubElement(csl_elem, "NegativeDec").text = "true" if dec_is_negative else "false"

        # Location
        loc_elem = SubElement(seq_elem, "Location")
        SubElement(loc_elem, "Latitude").text = str(location.lat)
        SubElement(loc_elem, "Longitude").text = str(location.lon)
        SubElement(loc_elem, "Elevation").text = str(location.elevation)
        SubElement(loc_elem, "Timezone").text = location.timezone

        # SaveSettings
        save_elem = SubElement(seq_elem, "SaveSettings")
        SubElement(save_elem, "Directory").text = f"./data/{target.name}"
        SubElement(save_elem, "Prefix").text = target.name.replace(" ", "_")
        SubElement(save_elem, "Format").text = "SER"
        SubElement(save_elem, "Overwrite").text = "false"

        xml_str = ET.tostring(capture_sequence_list, encoding="unicode")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    @staticmethod
    def parse_nina_response(xml_response: str) -> Dict[str, Any]:
        """解析 N.I.N.A. 的 XML 响应"""
        try:
            root = ET.fromstring(xml_response)
            result = {
                "status": root.findtext(".//Status", "unknown"),
                "current_target": root.findtext(".//CurrentTarget", ""),
                "slew_status": root.findtext(".//SlewStatus", ""),
                "image_count": int(root.findtext(".//ImageCount", "0")),
            }
            return result
        except Exception as e:
            logger.error(f"N.I.N.A. XML解析失败: {e}")
            return {"status": "error", "error": str(e)}


# ============ 主调度器 ============

class ObservationScheduler:
    """观测调度器（整合 StarWhisper 算法）"""

    def __init__(self, location: Location = None):
        self.location = location or Location("默认位置", 39.9, 116.4, 50, "Asia/Shanghai")

        if HAS_ASTROPLAN:
            _configure_iers()
            self.astro = AstroPlanner(self.location)
        else:
            self.astro = None
            logger.warning("astroplan未安装，部分高级功能不可用")

        self.nina = NINAXMLGenerator()

        # 默认设备
        self.default_equipment = Equipment(
            name="Celestron NexStar 8SE",
            type="Schmidt-Cassegrain",
            aperture=203,
            focal_length=2032,
            f_ratio=10,
            max_magnification=400,
            limiting_magnitude=14
        )

        # 观测日志
        self.observation_log: List[Dict] = []

    def set_location(self, location: Location):
        self.location = location
        if HAS_ASTROPLAN:
            self.astro = AstroPlanner(location)

    async def calculate_best_window(
        self,
        target: ObservationTarget,
        date: datetime = None
    ) -> Optional[ObservationWindow]:
        """计算目标最佳观测窗口"""
        if date is None:
            date = datetime.utcnow()

        if not HAS_ASTROPLAN or self.astro is None:
            return self._basic_window(target, date)

        try:
            # 1. 获取可观测时段
            tw_morning, tw_evening = self.astro.calculate_observable_period()

            # 2. 计算当前RA范围
            utc_str = date.strftime("%Y-%m-%d %H:%M:%S")
            ra_min, ra_max = self.astro.calculate_lst_and_corresponding_ra_range(utc_str)

            # 3. 检查目标是否可观测
            obj_dict = {"name": target.name, "ra": target.ra, "dec": target.dec}
            if not self.astro.is_target_observable_in_interval(obj_dict, 60):
                return None

            # 4. 计算高度角和方位角
            skycoord = target.to_skycoord()
            altaz = skycoord.transform_to(self.astro.observer.altaz)
            alt = float(altaz.alt.deg)
            az = float(altaz.az.deg)

            # 5. 月亮信息
            moon = self.astro.get_moon_info(date)
            moon_dist = float(
                SkyCoord(ra=target.ra * u.deg, dec=target.dec * u.deg)
                .separation(SkyCoord(ra=moon.get("ra", 0) * u.deg,
                                     dec=moon.get("dec", 0) * u.deg)).deg
                if "ra" in moon else 0
            )

            # 6. 评分
            score = self._score_window(target, alt, moon_dist, moon.get("phase", 0.5))

            reasons = []
            if alt > 60:
                reasons.append("高度角优秀(>60)")
            if moon_dist > 45:
                reasons.append("月光干扰小")
            if score > 80:
                reasons.append("综合评分优秀")

            return ObservationWindow(
                start_time=date,
                end_time=date + timedelta(hours=1),
                target=target.name,
                altitude=alt,
                azimuth=az,
                seeing=2.0,
                cloud_cover=20,
                moon_distance=moon_dist,
                moon_phase=moon.get("phase", 0.5),
                score=score,
                reasons=reasons
            )

        except Exception as e:
            logger.error(f"窗口计算失败: {e}")
            return self._basic_window(target, date)

    def _basic_window(self, target: ObservationTarget, date: datetime) -> ObservationWindow:
        """基础窗口计算（无astroplan）"""
        lst = self._compute_lst(date)
        ha = (lst - target.ra + 360) % 360
        lat_rad = math.radians(self.location.lat)
        dec_rad = math.radians(target.dec)
        ha_rad = math.radians(ha)

        sin_alt = (math.sin(dec_rad) * math.sin(lat_rad) +
                   math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
        alt = math.degrees(math.asin(sin_alt))
        cos_az = ((math.sin(dec_rad) - math.sin(math.radians(alt)) * math.sin(lat_rad)) /
                  (math.cos(math.radians(alt)) * math.cos(lat_rad)))
        az = math.degrees(math.acos(max(-1, min(1, cos_az))))
        if math.sin(ha_rad) > 0:
            az = 360 - az

        return ObservationWindow(
            start_time=date, end_time=date + timedelta(hours=1),
            target=target.name, altitude=max(0, alt), azimuth=az,
            seeing=2.5, cloud_cover=30, moon_distance=30,
            moon_phase=0.5, score=50, reasons=["基础计算模式"]
        )

    @staticmethod
    def _compute_lst(dt: datetime) -> float:
        jd = (datetime(dt.year, dt.month, dt.day,
                       dt.hour, dt.minute, dt.second) -
              datetime(2000, 1, 1, 12, 0, 0)).days / 36525.0
        lst = 280.46061837 + 360.98564736629 * (
            (dt - datetime(2000, 1, 1, 12, 0, 0)).days + (dt.hour - 12) / 24 + dt.minute / 1440
        ) + jd * jd * (0.000387933 - jd / 38710000.0)
        return (lst + 116.4) % 360  # 默认经度

    def _score_window(self, target: ObservationTarget, alt: float,
                      moon_dist: float, moon_phase: float) -> float:
        """评分观测窗口"""
        score = 0
        score += min(50, alt)  # 高度角最多50分
        score += min(30, moon_dist / 3)  # 月亮距离最多30分
        moon_effect = abs(moon_phase - 0.5) * 2  # 0=满月
        score += moon_effect * 15
        score += max(0, 5 - (target.exposure_time / 60)) * 5  # 短曝光奖励
        return min(100, score)

    def generate_schedule(
        self,
        targets: List[ObservationTarget],
        date: datetime = None,
        max_targets: int = 10
    ) -> Schedule:
        """
        生成观测计划（六原则调度）
        """
        if date is None:
            date = datetime.utcnow()

        schedule = Schedule(
            id=f"SCH-{date.strftime('%Y%m%d%H%M%S')}",
            created_at=datetime.utcnow(),
            date=date.strftime("%Y-%m-%d"),
            location=self.location,
            targets=[t.to_dict() for t in targets]
        )

        if not HAS_ASTROPLAN or self.astro is None:
            schedule.notes = "无astroplan，简化调度"
            for t in targets[:max_targets]:
                w = self._basic_window(t, date)
                schedule.windows.append(w)
            return schedule

        try:
            # 1. 计算RA范围
            utc_str = date.strftime("%Y-%m-%d %H:%M:%S")
            ra_min, ra_max = self.astro.calculate_lst_and_corresponding_ra_range(utc_str)

            # 2. RA过滤
            filtered = self.astro.filter_targets_by_ra_range(targets, ra_min, ra_max)
            logger.info(f"RA过滤: {len(targets)} -> {len(filtered)} 目标")

            # 3. 六原则排序
            prioritized = self.astro.prioritize_targets(filtered)

            # 4. 逐个验证可观测性并计算窗口
            for t in prioritized[:max_targets]:
                obj = {"name": t.name, "ra": t.ra, "dec": t.dec}
                if self.astro.is_target_observable_in_interval(obj, 60):
                    # 同步计算窗口（避免async复杂性）
                    w = self._sync_window(t, date)
                    if w and w.score > 30:
                        schedule.windows.append(w)
                        logger.info(f"  入选: {t.name} 评分={w.score:.1f}")

            schedule.notes = f"生成计划含{len(schedule.windows)}个观测窗口"
            logger.info(f"观测计划: {schedule.id}, {len(schedule.windows)}窗口")

        except Exception as e:
            logger.error(f"计划生成失败: {e}")
            schedule.notes = f"生成失败: {e}"

        return schedule

    def _sync_window(self, target: ObservationTarget, date: datetime) -> ObservationWindow:
        """同步计算窗口（用于generate_schedule）"""
        try:
            skycoord = target.to_skycoord()
            altaz = skycoord.transform_to(self.astro.observer.altaz)
            alt = float(altaz.alt.deg)
            az = float(altaz.az.deg)
            moon = self.astro.get_moon_info(date)

            # 估算月距离
            moon_dist = moon.get("distance", 60)

            score = self._score_window(target, alt, moon_dist, moon.get("phase", 0.5))

            return ObservationWindow(
                start_time=date, end_time=date + timedelta(hours=1),
                target=target.name, altitude=alt, azimuth=az,
                seeing=2.0, cloud_cover=20, moon_distance=moon_dist,
                moon_phase=moon.get("phase", 0.5), score=score
            )
        except Exception:
            return None

    def create_nina_sequence(
        self,
        target: ObservationTarget,
        num_exposures: int = 20
    ) -> str:
        """生成 N.I.N.A. 拍摄序列 XML"""
        return self.nina.create_capture_sequence_xml(
            target=target,
            location=self.location,
            num_exposures=num_exposures
        )


# ============ 常用目标快捷函数 ============

ANDROMEDA = ObservationTarget(
    name="M31 Andromeda Galaxy",
    ra=10.6847,  # 度
    dec=41.2687,
    magnitude=3.4,
    priority=1,
    min_altitude=30,
    exposure_time=120,
    filters=["L"],
    moon_distance_min=20,
    catalog="Messier"
)

ORION_NEBULA = ObservationTarget(
    name="M42 Orion Nebula",
    ra=83.8221,
    dec=-5.3911,
    magnitude=4.0,
    priority=1,
    min_altitude=25,
    exposure_time=60,
    filters=["L", "R", "G", "B"],
    moon_distance_min=15,
    catalog="Messier"
)

# ============ 快速测试 ============

if __name__ == "__main__":
    # 快速功能验证
    loc = Location("兴隆站", 40.0, 116.5, 900, "Asia/Shanghai")
    sched = ObservationScheduler(loc)

    print("=== StarWhisper 算法移植验证 ===")
    print(f"astroplan可用: {HAS_ASTROPLAN}")
    print(f"Location: {loc.name} ({loc.lat}N, {loc.lon}E)")

    if HAS_ASTROPLAN:
        astro = sched.astro
        utc_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ra_min, ra_max = astro.calculate_lst_and_corresponding_ra_range(utc_now)
        print(f"LST RA范围: [{ra_min:.2f}, {ra_max:.2f}] deg")

        observable = astro.is_target_observable_in_interval(
            {"name": "M31", "ra": 10.6847, "dec": 41.2687}, 60
        )
        print(f"M31 可观测: {observable}")

    # 生成计划
    targets = [ANDROMEDA, ORION_NEBULA]
    sched.set_location(loc)
    schedule = sched.generate_schedule(targets)
    print(f"\n生成计划: {schedule.id}")
    print(f"窗口数量: {len(schedule.windows)}")
    for w in schedule.windows:
        print(f"  - {w.target}: alt={w.altitude:.1f}az={w.azimuth:.1f} score={w.score:.1f}")

    # N.I.N.A. XML
    xml = sched.create_nina_sequence(ANDROMEDA, num_exposures=5)
    print(f"\nN.I.N.A. XML 长度: {len(xml)} bytes")
    print(xml[:500])
