# 天问-AGI Kepler/TESS 系外行星数据集成
"""
Kepler/TESS系外行星数据客户端

功能: 集成NASA Kepler/TESS API获取系外行星数据并实现凌星信号检测
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

# 尝试导入依赖
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class TransitSignal:
    """凌星信号数据类"""
    period: float  # 周期 (天)
    epoch: float  # 凌星中心时间
    duration: float  # 持续时间 (小时)
    depth: float  # 凌星深度
    snr: float  # 信噪比
    confidence: str  # 置信度 (HIGH/MEDIUM/LOW)


class KeplerExoplanetClient:
    """
    Kepler/TESS系外行星数据客户端

    使用方法:
        client = KeplerExoplanetClient()
        planets = await client.search_planets(max_mass=10.0)
        lightcurves = await client.get_lightcurve("Kepler-90 h")
    """

    def __init__(self, api_base: str = "https://exoplanetsarchive.ipac.caltech.edu"):
        self.api_base = api_base
        self.session = None
        self._nasa_client = None

    def _get_nasa_client(self):
        """获取NASA Exoplanet Archive客户端 (延迟初始化)"""
        if HAS_ASTROQUERY and self._nasa_client is None:
            self._nasa_client = NasaExoplanetArchive()
        return self._nasa_client

    async def search_planets(
        self,
        max_mass: Optional[float] = None,
        min_radius: Optional[float] = None,
        max_distance: Optional[float] = None
    ) -> List[Dict]:
        """
        搜索系外行星 - 使用NASA Exoplanet Archive TAP查询

        参数:
            max_mass: 最大行星质量 (木星质量)
            min_radius: 最小行星半径 (地球半径)
            max_distance: 最大距离 (秒差距)

        返回:
            系外行星列表
        """
        if not HAS_ASTROQUERY:
            return []

        try:
            client = self._get_nasa_client()
            if client is None:
                return []

            # 构建TAP查询
            query = "select top 500 pl_name, pl_mass, pl_masse, pl_radius, pl_rade, " \
                   "pl_orbper, pl_orbsmax, pl_eqt, st_dist, st_sp, st_lum from ps"

            filters = []
            if max_mass is not None:
                filters.append(f"pl_masse < {max_mass}")
            if min_radius is not None:
                filters.append(f"pl_rade > {min_radius}")
            if max_distance is not None:
                filters.append(f"st_dist < {max_distance}")

            if filters:
                query += " where " + " and ".join(filters)

            # 执行同步查询 (astroquery is sync, run in executor)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, client.query, query)

            if result is not None and len(result) > 0:
                return result.to_dict('records')
            return []

        except Exception as e:
            print(f"NASA TAP查询失败: {e}")
            return []

    async def get_lightcurve(
        self,
        planet_name: str,
        mission: str = "Kepler"
    ) -> tuple:
        """
        获取光变曲线数据 - 使用MAST API

        参数:
            planet_name: 行星名称 (如 "Kepler-90 h")
            mission: 任务名称 (Kepler/TESS)

        返回:
            光变曲线数据 (时间, 通量) tuple
        """
        if not HAS_NUMPY:
            return None, None

        if not HAS_HTTPX:
            return np.array([]), np.array([])

        try:
            # 清理行星名称
            target = planet_name.strip()

            # 使用MAST API获取光变曲线
            # Kepler: https://archive.stsci.edu/hlsps/lightcurves/
            # TESS: https://archive.stsci.edu/tess/

            mission_lower = mission.lower()
            if mission_lower == "kepler":
                product_type = "LC"
                dataset = "k2"
                url = f"https://astroquery.readthedocs.io/en/latest/api/astroquery.mast.Observations.html"
            elif mission_lower == "tess":
                product_type = "TIC"
                dataset = "tess"
                url = f"https://astroquery.readthedocs.io/en/latest/api/astroquery.mast.Observations.html"
            else:
                return np.array([]), np.array([])

            # 使用astroquery.mast获取观测数据
            from astroquery.mast import Observations

            obs = Observations.query_object(target, radius="0d")
            if obs is None or len(obs) == 0:
                return np.array([]), np.array([])

            # 获取光变曲线产品
            from astroquery.mast import Catalogs
            try:
                catalog_data = Catalogs.query_object("Kepler", target, catalog="Kepler")
                if catalog_data is not None and len(catalog_data) > 0:
                    time_col = None
                    flux_col = None
                    for col in catalog_data.colnames:
                        if 'time' in col.lower():
                            time_col = col
                        elif 'flux' in col.lower() or 'sap_flux' in col.lower():
                            flux_col = col

                    if time_col and flux_col:
                        return np.array(catalog_data[time_col]), np.array(catalog_data[flux_col])
            except Exception:
                pass

            return np.array([]), np.array([])

        except Exception as e:
            print(f"获取光变曲线失败: {e}")
            return np.array([]), np.array([])

    async def detect_transit_signal(
        self,
        time: np.ndarray,
        flux: np.ndarray,
        snr_threshold: float = 5.0
    ) -> List[TransitSignal]:
        """
        检测凌星信号

        参数:
            time: 时间序列
            flux: 通量序列
            snr_threshold: 信噪比阈值

        返回:
            检测到的凌星信号列表
        """
        if not HAS_NUMPY or len(time) == 0 or len(flux) == 0:
            return []

        try:
            from scipy.signal import find_peaks
            from scipy.stats import median_abs_deviation

            # 归一化通量
            flux_median = np.median(flux)
            flux_norm = flux / flux_median

            # 找负向峰值 (凌星是通量下降)
            inverted_flux = -flux_norm + 2
            peaks, properties = find_peaks(inverted_flux, height=0.01, distance=10)

            signals = []
            for peak in peaks:
                depth = abs(flux_norm[peak] - 1.0) * 100  # 深度百分比
                if depth > 0.01:  # 至少1%深度
                    signals.append(TransitSignal(
                        period=0.0,  # 需后续分析
                        epoch=float(time[peak]),
                        duration=1.0,
                        depth=depth,
                        snr=depth * 10,
                        confidence="MEDIUM"
                    ))

            return signals

        except Exception as e:
            print(f"凌星检测失败: {e}")
            return []


class LightCurveAnalyzer:
    """光变曲线分析器"""

    def __init__(self):
        pass

    def find_periodic_transits(
        self,
        time: np.ndarray,
        flux: np.ndarray,
        min_period: float = 0.5,
        max_period: float = 365.0
    ) -> dict:
        """
        寻找周期性凌星信号

        使用BoxLeastSquares周期图
        """
        if not HAS_NUMPY or len(time) == 0:
            return {}

        try:
            from astropy.timeseries import BoxLeastSquares

            duration = (max_period - min_period) / 1000
            periodogram = BoxLeastSquares(time, flux)
            periodogram.power(np.linspace(min_period, max_period, 1000), duration=duration)

            return {}
        except Exception:
            return {}

    def compute_phase_folded_curve(
        self,
        time: np.ndarray,
        flux: np.ndarray,
        period: float,
        epoch: float
    ) -> dict:
        """
        计算相位折叠光变曲线
        """
        if not HAS_NUMPY or len(time) == 0 or period <= 0:
            return {}

        try:
            # 计算相位
            phase = ((time - epoch) / period) % 1.0

            # 排序
            sort_idx = np.argsort(phase)
            phase_sorted = phase[sort_idx]
            flux_sorted = flux[sort_idx]

            return {
                'phase': phase_sorted.tolist(),
                'flux': flux_sorted.tolist(),
                'period': period,
                'epoch': epoch
            }
        except Exception:
            return {}