# 天问-AGI Kepler/TESS 系外行星数据集成

> 模块名称: kepler_exoplanet_client
> 创建时间: 2026-05-01
> 功能: 集成NASA Kepler/TESS API获取系外行星数据并实现凌星信号检测

---

## 一、模块概述

本模块用于从NASA Kepler和TESS望远镜数据中获取系外行星信息，支持凌星信号检测和分析。

### 1.1 数据源

| 数据源 | 说明 | API |
|--------|------|-----|
| NASA Exoplanet Archive | 系外行星目录 | exoplanetarchive.ipac.caltech.edu |
| TESS Science Office | TESS发现行星 | exoplanetsarchive.ipac.caltech.edu |
| Kepler Science Center | 开普勒数据 | exoplanetsarchive.ipac.caltech.edu |

### 1.2 核心能力

- 系外行星目录查询
- 光变曲线数据获取
- 凌星信号检测
- 周期分析

---

## 二、技术实现

### 2.1 KeplerExoplanetClient 类

```python
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

    async def search_planets(
        self,
        max_mass: Optional[float] = None,
        min_radius: Optional[float] = None,
        max_distance: Optional[float] = None
    ) -> List[Dict]:
        """
        搜索系外行星

        参数:
            max_mass: 最大行星质量 (木星质量)
            min_radius: 最小行星半径 (地球半径)
            max_distance: 最大距离 (秒差距)

        返回:
            系外行星列表
        """

    async def get_lightcurve(
        self,
        planet_name: str,
        mission: str = "Kepler"
    ) -> np.ndarray:
        """
        获取光变曲线数据

        参数:
            planet_name: 行星名称 (如 "Kepler-90 h")
            mission: 任务名称 (Kepler/TESS)

        返回:
            光变曲线数据 (时间, 通量)
        """

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
```

### 2.2 TransitSignal 数据类

```python
@dataclass
class TransitSignal:
    """凌星信号"""
    period: float  # 周期 (天)
    epoch: float  # 凌星中心时间
    duration: float  # 持续时间 (小时)
    depth: float  # 凌星深度
    snr: float  # 信噪比
    confidence: str  # 置信度 (HIGH/MEDIUM/LOW)
```

### 2.3 光变曲线分析

```python
class LightCurveAnalyzer:
    """光变曲线分析器"""

    def __init__(self):
        self.transit_finder = BoxLeastSquares(time, flux)

    def find_periodic_transits(
        self,
        time: np.ndarray,
        flux: np.ndarray,
        min_period: float = 0.5,
        max_period: float = 365.0
    ) -> Periodogram:
        """
        寻找周期性凌星信号

        使用BoxLeastSquares周期图
        """

    def compute_phase_folded_curve(
        self,
        time: np.ndarray,
        flux: np.ndarray,
        period: float,
        epoch: float
    ) -> PhaseFoldedLightCurve:
        """
        计算相位折叠光变曲线
        """
```

---

## 三、API端点

### 3.1 NASA Exoplanet Archive TAP接口

```
Base URL: https://exoplanetsarchive.ipac.caltech.edu/TAP/sync
```

**常用查询**:

```sql
-- 系外行星目录
SELECT * FROM ps WHERE pl_mass < 10 AND pl_rade > 1

-- Kepler行星系统
SELECT pl_name, pl_mass, pl_radius, pl_period
FROM ps
WHERE pl_name LIKE 'Kepler-%'

-- TESS发现
SELECT pl_name, pl_disc, pl_facility
FROM ps
WHERE pl_facility = 'TESS'
```

### 3.2 光变曲线数据

```
Light Curve Download API:
https://exoplanetsarchive.ipac.caltech.edu/cgi-bin/DataOverview.py
```

---

## 四、凌星检测算法

### 4.1 BoxLeastSquares (BLS)

```python
def detect_transits_bls(time, flux, period_range=(1, 365)):
    """
    使用BoxLeastSquares算法检测凌星

    1. 计算周期图
    2. 找到最大功率的周期
    3. 提取信号参数
    """
    from astropy.timeseries import BoxLeastSquares

    model = BoxLeastSquares(time, flux)
    periodogram = model.autoperiod(0.2, period_range[1])

    # 找到最佳周期
    best_period = periodogram.period[np.argmax(periodogram.power)]

    # 提取凌星信号
    transit_model = model.evaluate(best_period)
    snr = compute_snr(flux, transit_model)

    return TransitSignal(
        period=best_period,
        epoch=transit_model.transit_time,
        duration=transit_model.duration,
        depth=transit_model.depth,
        snr=snr,
        confidence="HIGH" if snr > 10 else "MEDIUM" if snr > 5 else "LOW"
    )
```

### 4.2 置信度评估

| SNR | 置信度 |
|-----|--------|
| > 10 | HIGH |
| 5-10 | MEDIUM |
| < 5 | LOW |

---

## 五、与天问-AGI的集成

### 5.1 在astro_analyzer.py中集成

```python
# 在AstroAnalyzer中增加方法
async def analyze_kepler_light_curve(
    self,
    planet_name: str
) -> Dict:
    """分析Kepler光变曲线，检测凌星信号"""
    client = KeplerExoplanetClient()

    # 获取光变曲线
    time, flux = await client.get_lightcurve(planet_name, "Kepler")

    # 检测凌星
    signals = await client.detect_transit_signal(time, flux)

    return {
        "planet": planet_name,
        "signals": signals,
        "n_transits": len(signals)
    }
```

### 5.2 在research_loop.py中集成

```python
# 在假说验证阶段，可调用系外行星分析
async def verify_exoplanet_hypothesis(
    self,
    hypothesis: str
) -> VerificationResult:
    """
    验证系外行星相关假说

    1. 解析假说中的行星系统
    2. 获取该系统的Kepler/TESS数据
    3. 检测是否有符合假说的信号
    """
```

---

## 六、使用示例

```python
import asyncio
from kepler_exoplanet_client import KeplerExoplanetClient

async def main():
    client = KeplerExoplanetClient()

    # 搜索质量小于10木星质量的系外行星
    planets = await client.search_planets(max_mass=10.0)
    print(f"找到 {len(planets)} 颗行星")

    # 获取Kepler-90 h的光变曲线
    time, flux = await client.get_lightcurve("Kepler-90 h", "Kepler")

    # 检测凌星信号
    signals = await client.detect_transit_signal(time, flux, snr_threshold=5.0)

    for signal in signals:
        print(f"周期: {signal.period:.2f}天, SNR: {signal.snr:.1f}")

asyncio.run(main())
```

---

## 七、依赖项

```
astropy >= 5.0
numpy >= 1.21
httpx >= 0.24  # 异步HTTP客户端
```

---

## 八、扩展计划

1. **多目标检测**: 同时分析多个行星系统的光变曲线
2. **机器学习增强**: 使用深度学习检测弱信号
3. **自动观测触发**: 当检测到新信号时触发观测调度

---

**模块定义者**: Claude (Anthropic)
**定义时间**: 2026-05-01
**版本**: v1.0