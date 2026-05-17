"""
气象数据采集器 - 移植自 NINA OpenMeteo.cs
来源: nina-develop/NINA.Equipment/Equipment/MyWeatherData/OpenMeteo.cs
功能: 从 Open-Meteo API 获取气象数据，支持离线缓存
API: https://api.open-meteo.com/v1/forecast (无需API key)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import math

logger = logging.getLogger(__name__)

# Open-Meteo API 端点
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# 中国主要天文台站经纬度 (用于离线模式默认位置)
OBSERVATORY_LOCATIONS = {
    "xinglong": {"lat": 40.396, "lon": 117.577, "alt": 896, "name": "兴隆观测站"},
    "shanxian": {"lat": 35.447, "lon": 111.531, "alt": 505, "name": "山西天文台"},
    "kunming": {"lat": 25.029, "lon": 102.797, "alt": 1891, "name": "昆明凤凰山"},
    "nanshan": {"lat": 43.474, "lon": 87.177, "alt": 2080, "name": "新疆南山"},
    "gaomeigu": {"lat": 26.703, "lon": 104.007, "alt": 2000, "name": "云南高美古"},
    "custom": {"lat": 35.678, "lon": 117.031, "alt": 100, "name": "自定义位置"},
}

# 气象数据缓存有效期 (秒)
CACHE_VALIDITY_SECONDS = 600  # Open-Meteo 建议不超过10分钟查询一次


@dataclass
class WeatherData:
    """气象数据结构 - 对齐 NINA IWeatherData 接口"""
    # 时间戳
    timestamp: str = ""
    source: str = "open-meteo"  # 数据来源

    # 核心气象参数 (NINA IWeatherData 对应)
    cloud_cover: float = 0.0       # 云量 (%) 0-100
    dew_point: float = 0.0         # 露点温度 (°C)
    humidity: float = 0.0          # 相对湿度 (%) 0-100
    pressure: float = 1013.25      # 海平面气压 (hPa)
    rain_rate: float = 0.0         # 降雨率 (mm/h)
    sky_brightness: float = 0.0    # 天空亮度 (lux)
    sky_quality: float = 21.0      # 天空质量 (mag/arcsec^2, SQM测量值典型21-22)
    sky_temperature: float = 0.0    # 天空红外温度 (°C)
    star_fwhm: float = 2.5         # 视宁度 (arcsec), 基于Seeing估算
    temperature: float = 15.0       # 环境温度 (°C)
    wind_direction: float = 0.0    # 风向 (度, 0-360)
    wind_gust: float = 0.0         # 阵风速度 (m/s)
    wind_speed: float = 0.0         # 风速 (m/s)

    # Open-Meteo 扩展参数
    cloud_base_height: float = 0.0  # 云底高度 (m)
    visibility: float = 50.0         # 能见度 (km)
    uv_index: float = 0.0           # UV指数
    precipitation_probability: float = 0.0  # 降雨概率 (%)

    # 计算字段
    observation_score: float = 0.0  # 观测质量评分 (0-100)
    is_safe: bool = True            # 是否适合观测

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OpenMeteoCollector:
    """
    Open-Meteo 气象数据采集器
    移植自 NINA OpenMeteo.cs 的核心逻辑

    NINA源码注释:
    // They strongly suggest that the API not be queried more frequent than 10 minutes.
    // updates weather data every 10 minutes.

    来源: nina-develop/NINA.Equipment/Equipment/MyWeatherData/OpenMeteo.cs
    """

    def __init__(self, cache_dir: str = "runtime/data/weather_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_fetch: Optional[datetime] = None
        self._cached_data: Optional[WeatherData] = None
        self._location = OBSERVATORY_LOCATIONS["custom"]

    def set_location(self, lat: float, lon: float, alt: float = 100,
                     name: str = "custom") -> None:
        """设置观测站位置"""
        self._location = {"lat": lat, "lon": lon, "alt": alt, "name": name}
        logger.info(f"气象采集器位置设置为: {name} ({lat:.3f}, {lon:.3f}, {alt}m)")

    def set_observatory(self, observatory_id: str) -> bool:
        """使用预设观测站"""
        if observatory_id in OBSERVATORY_LOCATIONS:
            loc = OBSERVATORY_LOCATIONS[observatory_id]
            self.set_location(loc["lat"], loc["lon"], loc["alt"], loc["name"])
            return True
        return False

    def fetch_current(self, force_refresh: bool = False) -> Optional[WeatherData]:
        """
        获取当前气象数据 (优先API, 回退缓存)

        参数:
            force_refresh: 强制从API刷新，忽略缓存

        返回:
            WeatherData 对象，或缓存数据（网络不可用时）
        """
        # 检查缓存有效性
        if not force_refresh and self._is_cache_valid():
            logger.debug("返回缓存气象数据")
            return self._cached_data

        # 尝试从API获取
        api_data = self._fetch_from_api()
        if api_data:
            self._cached_data = api_data
            self._last_fetch = datetime.now()
            self._save_cache(api_data)
            return api_data

        # 网络不可用，返回缓存
        cached = self._load_cache()
        if cached:
            logger.warning("网络不可用，返回缓存气象数据")
            self._cached_data = cached
            return cached

        # 极端情况：返回默认值
        logger.error("无法获取气象数据，返回默认值")
        return self._default_weather()

    def _fetch_from_api(self) -> Optional[WeatherData]:
        """从 Open-Meteo API 获取数据"""
        try:
            import urllib.request
            import urllib.error

            params = {
                "latitude": self._location["lat"],
                "longitude": self._location["lon"],
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "dew_point_2m",
                    "apparent_temperature",
                    "precipitation",
                    "rain",
                    "showers",
                    "snowfall",
                    "weather_code",
                    "cloud_cover",
                    "cloud_cover_low",
                    "cloud_cover_mid",
                    "cloud_cover_high",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m",
                    "surface_pressure",
                    "visibility",
                ],
                "hourly": [
                    "temperature_2m",
                    "precipitation_probability",
                ],
                "daily": [
                    "sunrise",
                    "sunset",
                    "uv_index_max",
                ],
                "timezone": "Asia/Shanghai",
                "forecast_days": 1,
            }

            url = OPEN_METEO_BASE_URL + "?" + "&".join(
                f"{k}={','.join(v) if isinstance(v, list) else v}"
                for k, v in params.items()
            )

            logger.info(f"从 Open-Meteo API 获取气象数据: {self._location['name']}")

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            return self._parse_open_meteo_response(data)

        except Exception as e:
            logger.error(f"Open-Meteo API 请求失败: {e}")
            return None

    def _parse_open_meteo_response(self, data: Dict) -> WeatherData:
        """
        解析 Open-Meteo API 响应
        移植自 NINA OpenMeteo.cs 的 ParseResponse 逻辑
        """
        current = data.get("current", {})

        # 云量处理: 综合低/中/高层云量
        cloud_low = current.get("cloud_cover_low", 0)
        cloud_mid = current.get("cloud_cover_mid", 0)
        cloud_high = current.get("cloud_cover_high", 0)
        cloud_cover = current.get("cloud_cover", 0)

        # 如果有分层云量数据，使用加权平均
        if cloud_low + cloud_mid + cloud_high > 0:
            # 低云对观测影响最大，权重最高
            total_cloud = cloud_low * 0.5 + cloud_mid * 0.3 + cloud_high * 0.2
            cloud_cover = max(cloud_cover, total_cloud)

        # 露点计算 (Open-Meteo直接提供dew_point_2m)
        dew_point = current.get("dew_point_2m", 0.0)

        # 湿度
        humidity = current.get("relative_humidity_2m", 0.0)

        # 降雨率
        rain = current.get("rain", 0.0)
        showers = current.get("showers", 0.0)
        rain_rate = rain + showers

        # 气压 (hPa)
        pressure = current.get("surface_pressure", 1013.25)

        # 风速/风向/阵风 (m/s)
        wind_speed = current.get("wind_speed_10m", 0.0)
        wind_direction = current.get("wind_direction_10m", 0.0)
        wind_gust = current.get("wind_gust_10m", 0.0)

        # 能见度 (km -> m)
        visibility_km = current.get("visibility", 50000)
        visibility = visibility_km / 1000 if visibility_km > 1000 else visibility_km

        # 温度
        temperature = current.get("temperature_2m", 15.0)

        # 天气代码 -> 估算云量 (如果cloud_cover缺失)
        weather_code = current.get("weather_code", 0)
        if cloud_cover == 0 and weather_code > 0:
            cloud_cover = self._weather_code_to_cloud(weather_code)

        # 估算视宁度 (基于风速和云量)
        star_fwhm = self._estimate_seeing(wind_speed, cloud_cover)

        # 估算天空温度 (简化: 红外天空温度 ≈ 露点 - 20°C 在晴夜)
        sky_temperature = dew_point - 20 if cloud_cover < 30 else temperature - 10

        # 天空亮度估算 (基于云量和月相)
        sky_brightness = self._estimate_sky_brightness(cloud_cover)

        # SQM估算 (天空质量 mag/arcsec^2)
        if cloud_cover < 10:
            sky_quality = 21.5  # 理想黑暗天空
        elif cloud_cover < 30:
            sky_quality = 20.5
        elif cloud_cover < 50:
            sky_quality = 19.0
        else:
            sky_quality = 18.0

        # UV指数
        daily = data.get("daily", {})
        uv_index = daily.get("uv_index_max", [0.0])[0] if daily.get("uv_index_max") else 0.0

        # 降雨概率
        hourly = data.get("hourly", {})
        precip_prob = hourly.get("precipitation_probability", [0])[0] if hourly.get("precipitation_probability") else 0.0

        weather = WeatherData(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="open-meteo",
            cloud_cover=float(cloud_cover),
            dew_point=float(dew_point),
            humidity=float(humidity),
            pressure=float(pressure),
            rain_rate=float(rain_rate),
            sky_brightness=float(sky_brightness),
            sky_quality=float(sky_quality),
            sky_temperature=float(sky_temperature),
            star_fwhm=float(star_fwhm),
            temperature=float(temperature),
            wind_direction=float(wind_direction),
            wind_gust=float(wind_gust),
            wind_speed=float(wind_speed),
            visibility=float(visibility),
            uv_index=float(uv_index),
            precipitation_probability=float(precip_prob),
        )

        # 计算观测评分
        weather.observation_score = self._calc_observation_score(weather)
        weather.is_safe = self._is_safe_for_observation(weather)

        return weather

    def _weather_code_to_cloud(self, code: int) -> float:
        """
        将 WMO weather code 转换为云量估算
        移植自 NINA OpenMeteo.cs 的 WeatherCodeToCloudCover 逻辑

        WMO Code Ref: https://open-meteo.com/en/docs
        """
        # WMO Weather interpretation codes (WW)
        # 0: Clear sky
        # 1, 2, 3: Mainly clear, partly cloudy, overcast
        # 45, 48: Fog
        # 51, 53, 55: Drizzle
        # 61, 63, 65: Rain
        # 71, 73, 75: Snow
        # 80, 81, 82: Rain showers
        # 95, 96, 99: Thunderstorm

        mapping = {
            0: 0.0,
            1: 10.0,
            2: 40.0,
            3: 80.0,
            45: 90.0,
            48: 90.0,
            51: 75.0,
            53: 80.0,
            55: 85.0,
            61: 80.0,
            63: 85.0,
            65: 90.0,
            71: 70.0,
            73: 75.0,
            75: 80.0,
            77: 50.0,
            80: 80.0,
            81: 85.0,
            82: 90.0,
            85: 80.0,
            86: 85.0,
            95: 90.0,
            96: 95.0,
            99: 100.0,
        }
        return mapping.get(code, 50.0)

    def _estimate_seeing(self, wind_speed: float, cloud_cover: float) -> float:
        """
        基于风速和云量估算视宁度 (FWHM, arcsec)
        移植自 NINA 的视宁度估算经验公式

        典型值:
        - 优秀: < 1.5 arcsec
        - 良好: 1.5 - 2.5 arcsec
        - 一般: 2.5 - 3.5 arcsec
        - 差: > 3.5 arcsec
        """
        # 基础视宁度
        base_seeing = 2.0  # arcsec

        # 风速影响 (风速 > 5 m/s 开始影响)
        if wind_speed > 5:
            wind_penalty = (wind_speed - 5) * 0.15
        else:
            wind_penalty = 0

        # 云量影响 (薄云有助于稳定大气)
        if cloud_cover < 20:
            cloud_bonus = -0.2  # 薄云层可以"平滑"大气扰动
        elif cloud_cover > 70:
            _ = (cloud_cover - 70) * 0.05
        else:
            cloud_bonus = 0

        seeing = base_seeing + wind_penalty + cloud_bonus
        return max(1.0, min(6.0, seeing))

    def _estimate_sky_brightness(self, cloud_cover: float,
                                  moon_phase: float = 0.0,
                                  moon_alt: float = 0.0) -> float:
        """
        估算天空亮度 (lux)
        简化模型: 无月晴夜 ~ 0.001 lux, 满月 ~ 0.1 lux, 城市夜空 ~ 1 lux

        NINA源码参考: SkyBrightness.cs
        """
        # 基础亮度 (黑暗晴夜)
        base_brightness = 0.001

        # 云量影响
        if cloud_cover > 0:
            cloud_factor = 1 + cloud_cover * 0.02
            base_brightness *= cloud_factor

        # 月光影响
        if moon_alt > 0:
            moon_factor = 1 + moon_phase * 100 * (moon_alt / 90)
            base_brightness *= moon_factor

        return base_brightness

    def _calc_observation_score(self, weather: WeatherData) -> float:
        """
        计算综合观测质量评分 (0-100)
        对齐 NINA WeatherData.score 计算逻辑
        评分 < 40 建议停止观测

        权重分配:
        - 云量: 30分 (最重要)
        - 视宁度: 25分
        - 风速: 20分
        - 湿度: 15分
        - 天空亮度: 10分
        """
        score = 100.0

        # 云量扣分 (0-30)
        score -= min(30.0, weather.cloud_cover * 0.6)

        # 视宁度扣分 (0-25)
        if weather.star_fwhm > 2.0:
            score -= min(25.0, (weather.star_fwhm - 2.0) * 8.0)

        # 风速扣分 (0-20)
        if weather.wind_speed > 5.0:
            score -= min(20.0, (weather.wind_speed - 5.0) * 4.0)

        # 湿度扣分 (0-15)
        if weather.humidity > 60.0:
            score -= min(15.0, (weather.humidity - 60.0) * 0.75)

        # 天空亮度扣分 (0-10)
        if weather.sky_brightness > 0.01:
            brightness_mag = -2.5 * math.log10(max(weather.sky_brightness, 1e-10))
            # 典型黑暗天空 = 21.5 mag, 每暗1 magnitude加2分
            if brightness_mag < 21.5:
                score -= min(10.0, (21.5 - brightness_mag) * 2.0)

        return max(0.0, min(100.0, score))

    def _is_safe_for_observation(self, weather: WeatherData) -> bool:
        """
        判断是否安全进行观测
        阈值来自 NINA/SWT 论文规范
        """
        # 湿度 >= 80% 禁止
        if weather.humidity >= 80.0:
            return False

        # 风速 >= 10 m/s 禁止
        if weather.wind_speed >= 10.0:
            return False

        # 阵风 >= 15 m/s 禁止
        if weather.wind_gust >= 15.0:
            return False

        # 云量 >= 50% 禁止
        if weather.cloud_cover >= 50.0:
            return False

        # 有降雨禁止
        if weather.rain_rate > 0.0:
            return False

        return True

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效 (10分钟有效期)"""
        if self._cached_data is None or self._last_fetch is None:
            return False
        elapsed = (datetime.now() - self._last_fetch).total_seconds()
        return elapsed < CACHE_VALIDITY_SECONDS

    def _save_cache(self, weather: WeatherData) -> None:
        """保存气象数据到本地缓存"""
        try:
            cache_file = self.cache_dir / "current_weather.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(weather.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存气象缓存失败: {e}")

    def _load_cache(self) -> Optional[WeatherData]:
        """从本地缓存加载气象数据"""
        try:
            cache_file = self.cache_dir / "current_weather.json"
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return WeatherData(**data)
        except Exception as e:
            logger.warning(f"加载气象缓存失败: {e}")
        return None

    def _default_weather(self) -> WeatherData:
        """返回默认气象数据 (完全离线时使用)"""
        return WeatherData(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="default",
            cloud_cover=0.0,
            humidity=50.0,
            temperature=15.0,
            pressure=1013.25,
            star_fwhm=2.5,
            wind_speed=0.0,
            sky_quality=21.0,
            observation_score=75.0,  # 假设中等条件
            is_safe=True,
        )

    def get_hourly_forecast(self, hours: int = 24) -> List[Dict]:
        """
        获取未来小时级天气预报 (用于观测计划规划)

        参数:
            hours: 预报小时数 (最大168小时)

        返回:
            每小时气象数据列表
        """
        try:
            import urllib.request

            params = {
                "latitude": self._location["lat"],
                "longitude": self._location["lon"],
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation_probability",
                    "cloud_cover",
                    "wind_speed_10m",
                    "weather_code",
                ],
                "forecast_hours": hours,
                "timezone": "Asia/Shanghai",
            }

            url = OPEN_METEO_BASE_URL + "?" + "&".join(
                f"{k}={','.join(v) if isinstance(v, list) else v}"
                for k, v in params.items()
            )

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            humidity = hourly.get("relative_humidity_2m", [])
            precip_prob = hourly.get("precipitation_probability", [])
            cloud = hourly.get("cloud_cover", [])
            wind = hourly.get("wind_speed_10m", [])
            weather_codes = hourly.get("weather_code", [])

            forecast = []
            for i, t in enumerate(times):
                forecast.append({
                    "time": t,
                    "temperature": temps[i] if i < len(temps) else 15.0,
                    "humidity": humidity[i] if i < len(humidity) else 50.0,
                    "precipitation_probability": precip_prob[i] if i < len(precip_prob) else 0.0,
                    "cloud_cover": cloud[i] if i < len(cloud) else 0.0,
                    "wind_speed": wind[i] if i < len(wind) else 0.0,
                    "weather_code": weather_codes[i] if i < len(weather_codes) else 0,
                })

            return forecast

        except Exception as e:
            logger.error(f"获取小时预报失败: {e}")
            return []

    def get_best_observation_window(self, target_altitude: float = 30.0) -> Dict[str, Any]:
        """
        基于当前气象预报，找到最佳观测窗口

        参数:
            target_altitude: 目标高度角 (度)

        返回:
            最佳观测时段信息
        """
        hourly = self.get_hourly_forecast(hours=48)

        best_windows = []
        for h in hourly:
            score = 100.0
            score -= min(30.0, h["cloud_cover"] * 0.6)
            score -= min(20.0, h["wind_speed"] * 2.0)
            score -= min(15.0, max(0, h["humidity"] - 60) * 0.75)
            score -= h["precipitation_probability"] * 0.5

            h["observation_score"] = max(0.0, score)
            if score >= 60.0:
                best_windows.append(h)

        return {
            "total_hours_forecast": len(hourly),
            "good_observation_hours": len(best_windows),
            "best_windows": best_windows[:6],  # 最多返回6个最佳窗口
            "location": self._location,
        }


# 全局单例
_global_collector: Optional[OpenMeteoCollector] = None


def get_weather_collector() -> OpenMeteoCollector:
    """获取全局气象采集器单例"""
    global _global_collector
    if _global_collector is None:
        _global_collector = OpenMeteoCollector()
    return _global_collector


if __name__ == "__main__":
    # 测试气象采集
    logging.basicConfig(level=logging.INFO)

    collector = OpenMeteoCollector()

    # 设置兴隆观测站
    collector.set_observatory("xinglong")

    # 获取当前数据
    weather = collector.fetch_current()
    if weather:
        logger.info(f"\n=== 气象数据 ({weather.source}) ===")
        logger.info(f"  温度: {weather.temperature:.1f}°C")
        logger.info(f"  湿度: {weather.humidity:.1f}%")
        logger.info(f"  云量: {weather.cloud_cover:.1f}%")
        logger.info(f"  风速: {weather.wind_speed:.1f} m/s")
        logger.info(f"  气压: {weather.pressure:.1f} hPa")
        logger.info(f"  视宁度: {weather.star_fwhm:.2f} arcsec")
        logger.info(f"  观测评分: {weather.observation_score:.1f}/100")
        logger.info(f"  安全观测: {'是' if weather.is_safe else '否'}")

    # 获取最佳观测窗口
    windows = collector.get_best_observation_window()
    logger.info("\n=== 48小时预报 ===")
    logger.info(f"  良好观测小时数: {windows['good_observation_hours']}/{windows['total_hours_forecast']}")
    for w in windows.get("best_windows", [])[:3]:
        logger.info(f"  {w['time']}: 云量{w['cloud_cover']:.0f}%, 风速{w['wind_speed']:.1f}m/s, 评分{w['observation_score']:.0f}")
