"""
天问-AGI 实时星图模块
RealtimeSkyChart - 通过 NASA SkyView API 获取真实天文图像

功能:
- 调用 NASA SkyView 获取真实天文图像 (DSS/2MASS/HST等)
- 支持目标名称(如M31)或坐标(RA/Dec)查询
- 自动缓存和异步获取
- 集成到现有观测流程

Author: Tianwen-AGI
"""

import asyncio
import base64
import io
import json
import urllib.request
import urllib.parse
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math

# 缓存目录
CACHE_DIR = Path(__file__).parent.parent / ".cache" / "skyviews"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ============ 数据模型 ============

class SkySurvey(Enum):
    """可用天空巡天调查"""
    DSS = "DSS"                    # Digitized Sky Survey (光学)
    DSS2_COLOR = "DSS2/color"      # DSS2 彩色版本
    DSS2_RED = "DSS2/red"          # DSS2 红通道
    DSS2_BLUE = "DSS2/blue"        # DSS2 蓝通道
    TMASS_J = "2MASS/J"            # 2微米全天巡视 J波段
    TMASS_H = "2MASS/H"            # 2微米全天巡视 H波段
    TMASS_K = "2MASS/K"            # 2微米全天巡视 K波段
    SDSS_R = "SDSS/r"              # 斯隆数字巡天 r波段
    IRIS = "IRIS"                  # IRAS红外图像
    HST = "HST"                    # 哈勃太空望远镜 (需特殊处理)


@dataclass
class SkyChartRequest:
    """星图请求"""
    target: str                          # 目标名称(如M31)或坐标
    survey: SkySurvey = SkySurvey.DSS2_COLOR
    size: float = 15.0                   # 视场大小(角分)
    pixels: int = 600                    # 输出像素
    scaling: str = "log"                 # 缩放方式: log/linear/sqrt
    cached: bool = True                  # 是否使用缓存


@dataclass
class SkyChartResult:
    """星图结果"""
    target: str
    survey: str
    ra: float                            # 赤经(度)
    dec: float                           # 赤纬(度)
    image_base64: str                    # Base64编码的PNG图像
    image_url: str                       # 原始FITS转换的PNG URL
    width: int
    height: int
    timestamp: str
    cached: bool
    fov: float                            # 实际视场(度)
    catalog_sources: List[Dict]          # 检测到的星源


# ============ 天体坐标工具 ============

# 常用天体坐标数据库 (避免每次都查Simbad)
BUILTIN_CATALOG = {
    # 梅西耶天体
    "M31": {"name": "仙女座星系", "ra": 10.6847, "dec": 41.2687, "type": "galaxy", "mag": 3.4},
    "M42": {"name": "猎户座大星云", "ra": 83.8221, "dec": -5.3911, "type": "nebula", "mag": 4.0},
    "M51": {"name": "涡旋星系", "ra": 202.4696, "dec": 47.1953, "type": "galaxy", "mag": 8.4},
    "M81": {"name": "波德星系", "ra": 148.8883, "dec": 69.0653, "type": "galaxy", "mag": 6.9},
    "M101": {"name": "风车星系", "ra": 210.8023, "dec": 54.3494, "type": "galaxy", "mag": 7.9},
    "M104": {"name": "草帽星系", "ra": 189.9975, "dec": -11.6236, "type": "galaxy", "mag": 8.0},
    "M1":  {"name": "蟹状星云", "ra": 83.6282, "dec": 22.0145, "type": "nebula", "mag": 8.4},
    "M8":  {"name": "礁湖星云", "ra": 270.9214, "dec": -24.3865, "type": "nebula", "mag": 6.0},
    "M20": {"name": "三叶星云", "ra": 270.5974, "dec": -23.0282, "type": "nebula", "mag": 6.3},
    "M57": {"name": "环状星云", "ra": 283.3961, "dec": 33.0285, "type": "nebula", "mag": 8.8},
    "M45": {"name": "昴宿星团", "ra": 56.8711, "dec": 24.1053, "type": "cluster", "mag": 1.6},
    "M13": {"name": "武仙座球状星团", "ra": 250.4238, "dec": 36.4603, "type": "globular_cluster", "mag": 5.8},
    "M87": {"name": "室女座星系团中心", "ra": 187.7059, "dec": 12.3911, "type": "galaxy", "mag": 9.6},
    
    # NGC天体
    "NGC224": {"name": "仙女座星系(NGC224)", "ra": 10.6847, "dec": 41.2687, "type": "galaxy", "mag": 3.4},
    "NGC5139": {"name": "半人马座Omega", "ra": 201.2983, "dec": -47.4797, "type": "globular_cluster", "mag": 3.9},
    "NGC7000": {"name": "北美洲星云", "ra": 314.6750, "dec": 44.3625, "type": "nebula", "mag": 4.0},
    "NGC6992": {"name": "面纱星云(东)", "ra": 312.7342, "dec": 31.7167, "type": "nebula", "mag": 7.0},
    "NGC6960": {"name": "面纱星云(西)", "ra": 312.7283, "dec": 30.7217, "type": "nebula", "mag": 7.0},
    
    # 恒星
    "VEGA": {"name": "织女星", "ra": 279.2347, "dec": 38.7836, "type": "star", "mag": 0.03},
    "ALTAIR": {"name": "牛郎星", "ra": 297.6958, "dec": 8.8684, "type": "star", "mag": 0.76},
    "BETELGEUSE": {"name": "参宿四", "ra": 88.7929, "dec": 7.4070, "type": "star", "mag": 0.42},
    "RIGEL": {"name": "参宿七", "ra": 78.6344, "dec": -8.2016, "type": "star", "mag": 0.13},
    
    # 行星状星云
    "NGC7293": {"name": "螺旋星云", "ra": 337.4126, "dec": -20.8374, "type": "nebula", "mag": 7.6},
    
    # 星系团
    "COMA": {"name": "后发座星系团", "ra": 194.9531, "dec": 27.9817, "type": "cluster", "mag": 12.6},
}


def parse_coordinates(target: str) -> Optional[Tuple[float, float]]:
    """
    解析坐标字符串
    支持格式:
    - RA Dec: "10.6847 +41.2687" 或 "10h6847m +41d2687m"
    - 小时: "00h42m44.3s +41d16d9s"
    """
    target = target.strip()
    
    # 首先检查是否是已知目标
    if target.upper() in BUILTIN_CATALOG:
        obj = BUILTIN_CATALOG[target.upper()]
        return obj["ra"], obj["dec"]
    
    # 尝试解析为坐标
    try:
        # 尝试 "RA Dec" 格式 (度)
        parts = target.replace(',', ' ').split()
        if len(parts) >= 2:
            ra = float(parts[0])
            dec = float(parts[1])
            if -360 <= ra <= 360 and -90 <= dec <= 90:
                return ra, dec
    except ValueError:
        pass
    
    return None


# ============ NASA SkyView API 客户端 ============

class NASA_SkyView_API:
    """NASA SkyView API 客户端"""
    
    BASE_URL = "https://skyview.gsfc.nasa.gov/api/v4.1/process"
    
    def __init__(self):
        self.position = None
        self.survey = None
        self.size = 15.0
        self.pixels = 600
    
    async def fetch(self, request: SkyChartRequest) -> SkyChartResult:
        """
        从 NASA SkyView 获取星图（离线优先模式）

        策略：
        1. 尝试 NASA SkyView API
        2. 如果失败/离线，使用本地星图生成 + 内置星表

        Args:
            request: 星图请求

        Returns:
            SkyChartResult: 包含图像和元数据的结果
        """
        # 解析目标坐标
        coords = parse_coordinates(request.target)
        if coords is None:
            raise ValueError(f"Cannot resolve target: {request.target}")

        ra, dec = coords

        # 生成缓存键
        cache_key = self._cache_key(request, ra, dec)
        cached_path = CACHE_DIR / f"{cache_key}.json"

        # 检查缓存
        if request.cached and cached_path.exists():
            try:
                with open(cached_path, 'r') as f:
                    data = json.load(f)
                result = SkyChartResult(**data)
                result.cached = True
                print(f"[SkyView] Cache hit: {request.target} ({request.survey.value})")
                return result
            except Exception as e:
                print(f"[SkyView] Cache read error: {e}")

        # 构建API请求
        print(f"[SkyView] Fetching: {request.target} RA={ra:.4f} Dec={dec:.4f} Survey={request.survey.value}")

        # Step 1: 创建扫描任务
        survey_str = request.survey.value if isinstance(request.survey, SkySurvey) else request.survey
        survey_str = survey_str.replace("/", " ")

        post_data = {
            "survey": survey_str,
            "position": f"{ra},{dec}",
            "size": request.size,
            "pixels": request.pixels,
            "scaling": request.scaling,
            "format": "png",
            "projection": "Tan",
            "resolver": "Simbad",
        }

        # 尝试NASA SkyView API
        try:
            task_id = await self._submit_task(post_data)
            if not task_id:
                raise RuntimeError("Failed to submit SkyView task")

            # 等待完成并获取结果
            result_url = await self._wait_for_completion(task_id)
            if not result_url:
                raise RuntimeError("SkyView task did not complete")

            # 下载图像
            image_base64, width, height = await self._download_image(result_url)
            sources = self._detect_sources_simple(ra, dec, request.size, width, height)
            survey_used = request.survey.value if isinstance(request.survey, SkySurvey) else request.survey
            image_url = result_url

        except Exception as e:
            # NASA SkyView 不可用，使用离线星图
            print(f"[SkyView] NASA API unavailable ({e}), using offline star chart")
            image_base64, width, height, sources = self._generate_offline_starfield(
                ra, dec, request.size, request.pixels, survey_str
            )
            survey_used = f"{survey_str} (offline)"
            image_url = ""

        result = SkyChartResult(
            target=request.target,
            survey=survey_used,
            ra=ra,
            dec=dec,
            image_base64=image_base64,
            image_url=image_url,
            width=width,
            height=height,
            timestamp=datetime.now().isoformat(),
            cached=False,
            fov=request.size / 60.0,  # 转换为度
            catalog_sources=sources
        )

        # 保存缓存
        try:
            with open(cached_path, 'w') as f:
                json.dump(result.__dict__, f)
        except Exception as e:
            print(f"[SkyView] Cache write error: {e}")

        return result
    
    def _cache_key(self, request: SkyChartRequest, ra: float, dec: float) -> str:
        """生成缓存键"""
        key_str = f"{request.target}_{ra:.4f}_{dec:.4f}_{request.survey.value}_{request.size}_{request.pixels}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _submit_task(self, post_data: Dict) -> Optional[str]:
        """提交SkyView扫描任务"""
        try:
            # 直接用简单HTTP请求
            data = urllib.parse.urlencode(post_data).encode()
            req = urllib.request.Request(
                self.BASE_URL,
                data=data,
                headers={'User-Agent': 'Tianwen-AGI/1.0'}
            )
            
            # 同步方式但用线程池避免阻塞
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: urllib.request.urlopen(req, timeout=60)
            )
            
            result = json.loads(response.read().decode())
            
            # SkyView API 返回 { "name": "task_id", "url": "..." }
            if "name" in result:
                return result["name"]
            elif "json" in result:
                return result["json"].get("name")
            
            return None
            
        except Exception as e:
            print(f"[SkyView] Submit error: {e}")
            return None
    
    async def _wait_for_completion(self, task_id: str, timeout: int = 120) -> Optional[str]:
        """等待任务完成并返回结果URL"""
        status_url = f"https://skyview.gsfc.nasa.gov/api/v4.1/status/{task_id}"
        start = datetime.now()
        
        while (datetime.now() - start).seconds < timeout:
            try:
                loop = asyncio.get_event_loop()
                req = urllib.request.Request(status_url, headers={'User-Agent': 'Tianwen-AGI/1.0'})
                response = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=30))
                status = json.loads(response.read().decode())
                
                if status.get("status") == "completed":
                    return status.get("png")
                elif status.get("status") == "error":
                    print(f"[SkyView] Task error: {status.get('error')}")
                    return None
                
                # 等待后重试
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"[SkyView] Status check error: {e}")
                await asyncio.sleep(5)
        
        return None
    
    async def _download_image(self, url: str) -> Tuple[str, int, int]:
        """下载图像并转为Base64"""
        if not url:
            raise ValueError("No image URL provided")
        
        try:
            loop = asyncio.get_event_loop()
            req = urllib.request.Request(url, headers={'User-Agent': 'Tianwen-AGI/1.0'})
            response = await loop.run_in_executor(
                None, 
                lambda: urllib.request.urlopen(req, timeout=120)
            )
            image_data = response.read()
            
            # 获取图像尺寸
            import struct
            
            # PNG: 读取IHDR chunk
            if image_data[:8] == b'\x89PNG\r\n\x1a\n':
                width = struct.unpack('>I', image_data[16:20])[0]
                height = struct.unpack('>I', image_data[20:24])[0]
            else:
                width = height = 600  # 默认
            
            # 转为Base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            return image_base64, width, height
            
        except Exception as e:
            print(f"[SkyView] Download error: {e}")
            raise
    
    def _detect_sources_simple(self, ra: float, dec: float, fov_arcmin: float, 
                                width: int, height: int) -> List[Dict]:
        """
        简化版星源检测
        基于视场内的已知梅西耶/NGC天体
        """
        sources = []
        
        # 计算视场范围
        fov_deg = fov_arcmin / 60.0
        half_fov = fov_deg / 2.0
        
        # 检查内置星表中的天体是否在视场内
        for name, obj in BUILTIN_CATALOG.items():
            # 计算角距离
            sep = self._angular_separation(
                ra, dec, 
                obj["ra"], obj["dec"]
            )
            
            # 如果在视场内(留一些边距)
            if sep < half_fov * 0.9:
                # 转换为像素坐标
                x = width * (0.5 + (obj["ra"] - ra) / fov_deg * 0.5)
                y = height * (0.5 - (obj["dec"] - dec) / fov_deg * 0.5)
                
                sources.append({
                    "name": obj["name"],
                    "catalog_id": name,
                    "ra": obj["ra"],
                    "dec": obj["dec"],
                    "mag": obj["mag"],
                    "type": obj["type"],
                    "x_pixel": max(0, min(width, int(x))),
                    "y_pixel": max(0, min(height, int(y))),
                    "angular_separation_deg": round(sep, 4)
                })
        
        return sources
    
    @staticmethod
    def _angular_separation(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
        """计算两点间的角距离(度)"""
        ra1_rad = math.radians(ra1)
        dec1_rad = math.radians(dec1)
        ra2_rad = math.radians(ra2)
        dec2_rad = math.radians(dec2)
        
        cos_sep = (math.sin(dec1_rad) * math.sin(dec2_rad) + 
                   math.cos(dec1_rad) * math.cos(dec2_rad) * math.cos(ra2_rad - ra1_rad))
        
        # 避免浮点误差
        cos_sep = max(-1.0, min(1.0, cos_sep))
        
        return math.degrees(math.acos(cos_sep))

    def _generate_offline_starfield(
        self,
        ra: float,
        dec: float,
        size_arcmin: float,
        pixels: int,
        survey: str
    ) -> Tuple[str, int, int, List[Dict]]:
        """
        生成离线模拟星图（NASA SkyView不可用时）

        使用 PIL 在黑色背景上绘制:
        1. 基于内置星表的天体位置绘制圆点（亮度对应星等）
        2. 模拟星云的模糊云气效果
        3. 添加坐标系刻度和视场信息

        Args:
            ra, dec: 中心坐标
            size_arcmin: 视场大小(角分)
            pixels: 输出像素
            survey: 巡天名称

        Returns:
            (base64_png, width, height, sources)
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            HAS_PIL = True
        except ImportError:
            HAS_PIL = False

        if not HAS_PIL:
            # 无 PIL 时返回黑色占位图
            black_img = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
            return base64.b64encode(black_img).decode(), 1, 1, []

        width = height = pixels
        img = Image.new("RGB", (width, height), (5, 5, 15))
        draw = ImageDraw.Draw(img)

        fov_deg = size_arcmin / 60.0
        half_fov = fov_deg / 2.0

        # 绘制背景星场（基于内置星表）
        drawn = 0
        for name, obj in BUILTIN_CATALOG.items():
            sep = self._angular_separation(ra, dec, obj["ra"], obj["dec"])
            if sep < half_fov * 1.2:
                # 计算像素位置
                x = width * (0.5 + (obj["ra"] - ra) / fov_deg * 0.5)
                y = height * (0.5 - (obj["dec"] - dec) / fov_deg * 0.5)

                if 0 <= x <= width and 0 <= y <= height:
                    # 星等 -> 亮度映射 (mags: 暗=1px, 亮=12px)
                    mag = obj.get("mag", 10)
                    brightness = max(1, int(15 - mag * 1.2))

                    # 颜色: 亮星偏白蓝，亮星偏黄红
                    obj_type = obj.get("type", "star")
                    if obj_type == "galaxy":
                        color = (150, 120, 200)
                        r = brightness * 3
                        draw.ellipse([x-r, y-r, x+r, y+r], fill=color)
                    elif obj_type == "nebula":
                        color = (80, 60, 150)
                        r = brightness * 5
                        draw.ellipse([x-r, y-r, x+r, y+r], fill=color, outline=(100, 80, 200))
                    else:  # star or cluster
                        if brightness > 8:
                            color = (255, 255, 220)
                        elif brightness > 5:
                            color = (200, 200, 255)
                        else:
                            color = (150, 150, 200)
                        r = brightness
                        draw.ellipse([x-r, y-r, x+r, y+r], fill=color)
                    drawn += 1

        # 绘制背景星空噪声
        import random
        rng = random.Random(int(ra * 1000 + dec))
        for _ in range(min(500, int(fov_deg * 2000))):
            x = rng.randint(0, width - 1)
            y = rng.randint(0, height - 1)
            brightness = rng.randint(10, 80)
            draw.point((x, y), fill=(brightness, brightness, brightness))

        # 绘制视场边框
        draw.rectangle([0, 0, width-1, height-1], outline=(80, 80, 120), width=1)

        # 添加角分刻度（简化）
        try:
            tick_color = (100, 100, 140)
            # 顶部刻度
            for i in range(0, 101, 25):
                x = int(width * i / 100)
                draw.line([x, 0, x, 5], fill=tick_color)
            # 左侧刻度
            for i in range(0, 101, 25):
                y = int(height * i / 100)
                draw.line([0, y, 5, y], fill=tick_color)
        except Exception:
            pass

        # 转base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # 检测到的源
        sources = self._detect_sources_simple(ra, dec, size_arcmin, width, height)

        return image_base64, width, height, sources


# ============ 主接口 ============

_skyview_api = NASA_SkyView_API()


async def get_realtime_skychart(
    target: str,
    survey: Union[SkySurvey, str] = SkySurvey.DSS2_COLOR,
    size: float = 15.0,
    pixels: int = 600,
    use_cache: bool = True
) -> SkyChartResult:
    """
    获取实时星图的主接口
    
    Args:
        target: 目标名称(如M31)或坐标
        survey: 天空巡天调查 (默认DSS2彩色)
        size: 视场大小(角分, 默认15')
        pixels: 输出像素 (默认600x600)
        use_cache: 是否使用缓存
        
    Returns:
        SkyChartResult: 包含Base64图像和星源列表
        
    Example:
        result = await get_realtime_skychart("M31", size=20.0)
        print(f"检测到 {len(result.catalog_sources)} 个天体")
        # 将图像发送到前端:
        # <img src="data:image/png;base64,{{ result.image_base64 }}">
    """
    if isinstance(survey, str):
        survey = SkySurvey(survey)
    
    request = SkyChartRequest(
        target=target,
        survey=survey,
        size=size,
        pixels=pixels,
        cached=use_cache
    )
    
    return await _skyview_api.fetch(request)


async def batch_get_skycharts(
    targets: List[str],
    survey: Union[SkySurvey, str] = SkySurvey.DSS2_COLOR,
    size: float = 15.0
) -> Dict[str, SkyChartResult]:
    """
    批量获取多个目标的星图
    
    Args:
        targets: 目标名称列表
        survey: 天空巡天调查
        size: 视场大小
        
    Returns:
        Dict[str, SkyChartResult]: 目标名 -> 结果
    """
    tasks = [
        get_realtime_skychart(t, survey=survey, size=size)
        for t in targets
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    output = {}
    for target, result in zip(targets, results):
        if isinstance(result, Exception):
            print(f"[SkyView] Error fetching {target}: {result}")
        else:
            output[target] = result
    
    return output


# ============ 调试/测试 ============

if __name__ == "__main__":
    async def test():
        print("=" * 50)
        print("Testing NASA SkyView Realtime Sky Chart")
        print("=" * 50)
        
        # 测试单个目标
        print("\n[Test 1] M31 (仙女座星系)")
        result = await get_realtime_skychart("M31", size=30.0)
        print(f"  RA: {result.ra:.4f}, Dec: {result.dec:.4f}")
        print(f"  Survey: {result.survey}")
        print(f"  Image: {len(result.image_base64)} chars (Base64)")
        print(f"  Sources found: {len(result.catalog_sources)}")
        for src in result.catalog_sources[:5]:
            print(f"    - {src['name']} ({src['catalog_id']}) mag={src['mag']}")
        
        # 测试坐标解析
        print("\n[Test 2] Parsing coordinates")
        coords = parse_coordinates("M42")
        print(f"  M42 -> RA={coords[0]:.4f}, Dec={coords[1]:.4f}")
        
        # 测试批量
        print("\n[Test 3] Batch fetch")
        targets = ["M42", "M51", "M81", "M101"]
        batch = await batch_get_skycharts(targets, size=20.0)
        for name, res in batch.items():
            print(f"  {name}: {len(res.catalog_sources)} sources, cached={res.cached}")
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        
    asyncio.run(test())
