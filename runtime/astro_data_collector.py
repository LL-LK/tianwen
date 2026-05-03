"""
天问-AGI 天文数据收集模块
AstroDataCollector - 集成多源天文数据API
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import urllib.request
import urllib.error

# ============ 数据模型 ============

@dataclass
class AstronomicalObject:
    """天体对象"""
    id: str
    name: str
    type: str  # star, planet, galaxy, nebula, asteroid, comet, etc.
    ra: float  # 赤经 (度)
    dec: float  # 赤纬 (度)
    magnitude: float  # 视星等
    distance: Optional[float] = None  # 距离(光年)
    description: str = ""
    constellation: str = ""
    metadata: Dict = field(default_factory=dict)

@dataclass
class ObservationData:
    """观测数据"""
    source: str
    object_id: str
    timestamp: str
    exposure: Optional[float] = None
    filter: str = ""
    image_url: str = ""
    data_url: str = ""
    thumbnail_url: str = ""
    description: str = ""

@dataclass
class SkyCondition:
    """天空状况"""
    timestamp: str
    location: str
    cloud_cover: int  # 0-100%
    moon_phase: float  # 0-1
    moon_altitude: float  # 度
    seeing: float  # 视宁度(角秒)
    humidity: int  # 0-100%
    temperature: float  # 摄氏度
    wind_speed: float  # m/s

@dataclass
class AstronomicalEvent:
    """天文事件"""
    id: str
    name: str
    type: str  # eclipse, transit, conjunction, meteor, etc.
    start_time: str
    end_time: str
    visibility: str  # good, medium, poor
    description: str
    best_location: str = ""

# ============ API客户端基类 ============

class BaseAstroAPI:
    """天文API基类"""

    def __init__(self, name: str):
        self.name = name
        self.rate_limit_delay = 1.0  # 秒
        self.last_call_time = 0

    async def _rate_limit(self):
        """速率限制"""
        now = datetime.now().timestamp()
        elapsed = now - self.last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_call_time = datetime.now().timestamp()

    async def _fetch_json(self, url: str) -> Optional[Dict]:
        """获取JSON数据"""
        try:
            await self._rate_limit()
            req = urllib.request.Request(url, headers={'User-Agent': 'Tianwen-AGI/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"[{self.name}] Fetch error: {e}")
            return None

    async def _fetch_bytes(self, url: str) -> Optional[bytes]:
        """获取字节数据"""
        try:
            await self._rate_limit()
            req = urllib.request.Request(url, headers={'User-Agent': 'Tianwen-AGI/1.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as e:
            print(f"[{self.name}] Fetch error: {e}")
            return None

# ============ NASA APOD API ============

class NASAAPI(BaseAstroAPI):
    """NASA天文每日图片API"""

    BASE_URL = "https://api.nasa.gov/planetary"

    def __init__(self, api_key: str = "DEMO_KEY"):
        super().__init__("NASA")
        self.api_key = api_key

    async def get_apod(self, date: str = None) -> Optional[Dict]:
        """获取每日天文图片"""
        url = f"{self.BASE_URL}/apod?api_key={self.api_key}"
        if date:
            url += f"&date={date}"
        return await self._fetch_json(url)

    async def get_apod_range(self, start_date: str, end_date: str) -> List[Dict]:
        """获取日期范围内的APOD"""
        url = f"{self.BASE_URL}/apod?api_key={self.api_key}&start_date={start_date}&end_date={end_date}"
        data = await self._fetch_json(url)
        return data if isinstance(data, list) else []

    async def get_apod_archive(self, count: int = 10) -> List[Dict]:
        """获取最近N个APOD"""
        url = f"{self.BASE_URL}/apod?api_key={self.api_key}&count={count}"
        data = await self._fetch_json(url)
        return data if isinstance(data, list) else []

# ============ Minor Planet Center API ============

class MinorPlanetAPI(BaseAstroAPI):
    """小行星中心API - 查询小行星和彗星"""

    BASE_URL = "https://minorplanetcenter.net/web_service"

    async def search_asteroid(self, name: str = None, id: int = None) -> Optional[Dict]:
        """搜索小行星"""
        if id:
            url = f"{self.BASE_URL}/orbit_pb.php?ObjID={id}&format=json"
        elif name:
            url = f"{self.BASE_URL}/search_alc.cgi?target={name}&fmt=json"
        else:
            return None
        return await self._fetch_json(url)

    async def get_near_earth_objects(self, start_date: str, end_date: str) -> List[Dict]:
        """获取近地天体"""
        url = f"{self.BASE_URL}/nearEarthObjects?begin={start_date}&end={end_date}&format=json"
        data = await self._fetch_json(url)
        return data if isinstance(data, list) else []

# ============ SIMBAD API ============

class SIMBADAPI(BaseAstroAPI):
    """SIMBAD天文数据库"""

    BASE_URL = "https://simbad.cds.unistra.fr/simbad/sim-id"

    async def query_object(self, name: str) -> Optional[AstronomicalObject]:
        """查询天体对象"""
        try:
            # 使用Simbad的ConeSearch
            url = f"https://simbad.cds.unistra.fr/simbad/sim-coo?Coord={name.replace(' ', '+')}&Radius=1&Radius.unit=arcmin&format=json"
            data = await self._fetch_json(url)
            if data and 'objects' in data:
                obj = data['objects'][0]
                return AstronomicalObject(
                    id=obj.get('oid', ''),
                    name=obj.get('MAIN_ID', name),
                    type=obj.get('TYPE', 'unknown'),
                    ra=float(obj.get('RA', 0)),
                    dec=float(obj.get('DEC', 0)),
                    magnitude=float(obj.get('V', 99)),
                    description=obj.get('TITLE', '')
                )
        except Exception as e:
            print(f"[SIMBAD] Query error: {e}")
        return None

# ============ 天文事件API ============

class AstronomicalEventAPI(BaseAstroAPI):
    """天文事件API"""

    def __init__(self):
        super().__init__("AstroEvents")

    async def get_upcoming_events(self, days: int = 30) -> List[AstronomicalEvent]:
        """获取未来N天的天文事件"""
        # 内置事件日历
        events = []
        now = datetime.now()

        # 预定义的一些常见事件
        annual_events = [
            {"name": "英仙座流星雨", "type": "meteor", "month": 8, "day": 12, "peak_hour": 22},
            {"name": "双子座流星雨", "type": "meteor", "month": 12, "day": 14, "peak_hour": 2},
            {"name": "日全食", "type": "eclipse", "month": 7, "day": 3, "peak_hour": 12},
            {"name": "月全食", "type": "eclipse", "month": 5, "day": 26, "peak_hour": 19},
            {"name": "金星西大距", "type": "transit", "month": 10, "day": 23, "peak_hour": 6},
            {"name": "木星冲日", "type": "transit", "month": 9, "day": 26, "peak_hour": 0},
        ]

        for event_def in annual_events:
            event_date = datetime(now.year, event_def["month"], event_def["day"], event_def["peak_hour"])
            if event_date < now:
                event_date = datetime(now.year + 1, event_def["month"], event_def["day"], event_def["peak_hour"])

            events.append(AstronomicalEvent(
                id=f"evt_{event_def['name']}_{event_date.strftime('%Y%m%d')}",
                name=event_def["name"],
                type=event_def["type"],
                start_time=event_date.isoformat(),
                end_time=(event_date + timedelta(hours=6)).isoformat(),
                visibility="good",
                description=f"{event_def['name']}将在{event_date.strftime('%Y年%m月%d日')}达到峰值",
                best_location="全球可见" if event_def["type"] == "meteor" else "特定地区"
            ))

        # 过滤30天内的
        filtered = []
        for evt in events:
            evt_time = datetime.fromisoformat(evt.start_time)
            if 0 <= (evt_time - now).days <= days:
                filtered.append(evt)

        return filtered

# ============ 天气API (用于观测条件) ============

class WeatherAPI(BaseAstroAPI):
    """天气API - 用于判断观测条件"""

    def __init__(self):
        super().__init__("Weather")

    async def get_weather(self, lat: float, lon: float) -> Optional[SkyCondition]:
        """获取指定位置的天空状况"""
        # 使用Open-Meteo免费API
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,cloud_cover,wind_speed_10m&forecast_days=1"
            data = await self._fetch_json(url)

            if data and 'current' in data:
                current = data['current']
                # 简化月相计算
                moon_phase = self._calculate_moon_phase()

                return SkyCondition(
                    timestamp=current.get('time', datetime.now().isoformat()),
                    location=f"{lat},{lon}",
                    cloud_cover=current.get('cloud_cover', 0),
                    moon_phase=moon_phase,
                    moon_altitude=45,  # 简化
                    seeing=2.0,  # 简化
                    humidity=current.get('relative_humidity_2m', 50),
                    temperature=current.get('temperature_2m', 20),
                    wind_speed=current.get('wind_speed_10m', 5)
                )
        except Exception as e:
            print(f"[Weather] Error: {e}")
        return None

    def _calculate_moon_phase(self) -> float:
        """计算当前月相 (0-1)"""
        # 简化计算：基于已知的新月日期
        known_new_moon = datetime(2026, 1, 3)  # 假设1月3日是新月
        days_since_new = (datetime.now() - known_new_moon).days
        synodic_month = 29.53
        return (days_since_new % synodic_month) / synodic_month

# ============ 主收集器 ============

class AstroDataCollector:
    """天文数据收集器 - 整合所有数据源"""

    def __init__(self, nasa_api_key: str = "DEMO_KEY"):
        self.nasa = NASAAPI(nasa_api_key)
        self.minor_planet = MinorPlanetAPI()
        self.simbad = SIMBADAPI()
        self.events = AstronomicalEventAPI()
        self.weather = WeatherAPI()

        # 缓存
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache or key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[key]

    def _set_cache(self, key: str, data: Any, minutes: int = 60):
        """设置缓存"""
        self._cache[key] = data
        self._cache_expiry[key] = datetime.now() + timedelta(minutes=minutes)

    async def get_apod(self, date: str = None) -> Optional[Dict]:
        """获取每日天文图片"""
        cache_key = f"apod_{date or 'today'}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        data = await self.nasa.get_apod(date)
        if data:
            self._set_cache(cache_key, data, 60)
        return data

    async def get_apod_gallery(self, count: int = 20) -> List[Dict]:
        """获取APOD图库"""
        cache_key = f"apod_gallery_{count}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        data = await self.nasa.get_apod_archive(count)
        if data:
            self._set_cache(cache_key, data, 30)
        return data

    async def search_celestial_object(self, name: str) -> Optional[AstronomicalObject]:
        """搜索天体对象"""
        cache_key = f"object_{name}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        obj = await self.simbad.query_object(name)
        if obj:
            self._set_cache(cache_key, obj, 60 * 24)  # 24小时缓存
        return obj

    async def get_near_earth_asteroids(self, days: int = 7) -> List[Dict]:
        """获取近地小行星"""
        end_date = datetime.now() + timedelta(days=days)
        end_str = end_date.strftime('%Y-%m-%d')
        start_str = datetime.now().strftime('%Y-%m-%d')

        cache_key = f"neo_{start_str}_{end_str}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        data = await self.minor_planet.get_near_earth_objects(start_str, end_str)
        if data:
            self._set_cache(cache_key, data, 60)
        return data

    async def get_upcoming_events(self, days: int = 30) -> List[AstronomicalEvent]:
        """获取即将发生的天文事件"""
        cache_key = f"events_{days}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        events = await self.events.get_upcoming_events(days)
        self._set_cache(cache_key, events, 60 * 6)  # 6小时缓存
        return events

    async def get_observation_conditions(self, lat: float, lon: float) -> Optional[SkyCondition]:
        """获取观测条件"""
        cache_key = f"weather_{lat:.2f}_{lon:.2f}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        conditions = await self.weather.get_weather(lat, lon)
        if conditions:
            self._set_cache(cache_key, conditions, 15)  # 15分钟缓存
        return conditions

    async def get_daily_astronomy_summary(self) -> Dict:
        """获取每日天文摘要"""
        summary = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "timestamp": datetime.now().isoformat(),
            "apod": None,
            "upcoming_events": [],
            "near_earth_objects": [],
            "observation_tips": []
        }

        # 并行获取数据
        apod_task = self.get_apod()
        events_task = self.get_upcoming_events(7)
        asteroids_task = self.get_near_earth_asteroids(7)

        results = await asyncio.gather(apod_task, events_task, asteroids_task, return_exceptions=True)

        if isinstance(results[0], dict):
            summary["apod"] = {
                "title": results[0].get('title'),
                "url": results[0].get('url'),
                "hdurl": results[0].get('hdurl'),
                "explanation": results[0].get('explanation', '')[:200]
            }

        if isinstance(results[1], list):
            summary["upcoming_events"] = [
                {"name": e.name, "type": e.type, "time": e.start_time}
                for e in results[1][:5]
            ]

        if isinstance(results[2], list):
            summary["near_earth_objects"] = results[2][:5]

        # 生成观测建议
        if summary["upcoming_events"]:
            summary["observation_tips"].append(
                f"本周有{len(summary['upcoming_events'])}个天文事件值得关注"
            )

        return summary

    def save_to_file(self, data: Any, filename: str, subdir: str = "data"):
        """保存数据到文件"""
        data_dir = Path(subdir)
        data_dir.mkdir(parents=True, exist_ok=True)

        filepath = data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(data))
        print(f"[Collector] Data saved to {filepath}")
        return filepath

# ============ 示例用法 ============

async def demo():
    print("=" * 60)
    print("天问-AGI 天文数据收集器演示")
    print("=" * 60)

    collector = AstroDataCollector()

    # 1. 获取每日天文图片
    print("\n📷 获取NASA每日天文图片...")
    apod = await collector.get_apod()
    if apod:
        print(f"   标题: {apod.get('title', 'N/A')}")
        print(f"   日期: {apod.get('date', 'N/A')}")
        print(f"   类型: {apod.get('media_type', 'N/A')}")

    # 2. 获取即将发生的天文事件
    print("\n📅 获取即将发生的天文事件...")
    events = await collector.get_upcoming_events(30)
    for event in events[:5]:
        print(f"   • {event.name} ({event.type}) - {event.start_time[:10]}")

    # 3. 获取观测条件 (北京)
    print("\n🌤️ 获取北京观测条件...")
    conditions = await collector.get_observation_conditions(39.9, 116.4)
    if conditions:
        print(f"   云量: {conditions.cloud_cover}%")
        print(f"   湿度: {conditions.humidity}%")
        print(f"   温度: {conditions.temperature}°C")
        print(f"   月相: {conditions.moon_phase:.2f}")

    # 4. 获取每日天文摘要
    print("\n📊 获取每日天文摘要...")
    summary = await collector.get_daily_astronomy_summary()
    print(f"   日期: {summary['date']}")
    print(f"   事件数: {len(summary['upcoming_events'])}")

    # 5. 保存数据
    print("\n💾 保存数据到文件...")
    collector.save_to_file(summary, f"astronomy_summary_{summary['date']}.json")

if __name__ == "__main__":
    asyncio.run(demo())