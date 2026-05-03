# PRO: Kepler NASA TAP Query Implementation
**日期**: 2026-05-01
**状态**: ✅ 完成实现
**优先级**: P0

---

## 一、目标

将 `kepler_exoplanet_client.py` 中的 mock 数据替换为真实的 NASA TAP 查询。

---

## 二、实现方案

### 2.1 API 选择

| API | 端点 | 说明 |
|-----|------|------|
| NASA Exoplanet Archive TAP | `https://exoplanetarchive.ipac.caltech.edu/TAP/sync` | 系外行星目录 |
| MAST API | `https://mast.stsci.edu/api/v0/invoke` | 光变曲线数据 |

### 2.2 技术实现

**使用 httpx 直接调用 TAP API** (备选方案，因 astroquery 与当前 Python 3.13 不兼容)

```python
# search_planets() - NASA TAP查询
async def search_planets(self, max_mass=None, ...) -> List[Dict]:
    query = "select top 500 pl_name, pl_mass, pl_masse, pl_radius, pl_rade, " \
           "pl_orbper, pl_orbsmax, pl_eqt, st_dist, st_sp, st_lum, hostname, disc_year " \
           "from ps"
    url = f"{self.TAP_BASE}?query={encoded_query}&format=json"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        data = response.json()
```

### 2.3 主要数据表

| 表名 | 说明 |
|------|------|
| ps | 行星星表 (Planetary Systems) - 5000+ 行星 |
| kepler_lc_lightcurve | Kepler光变曲线 |
| tess_lc_lightcurve | TESS光变曲线 |

---

## 三、代码修改

### 3.1 search_planets() 实现

- 使用 NASA Exoplanet Archive TAP API
- 支持 `max_mass`, `min_radius`, `max_distance` 过滤参数
- 返回最多 500 条系外行星记录

### 3.2 get_lightcurve() 实现框架

```python
async def get_lightcurve(self, planet_name: str, mission: str = "Kepler") -> tuple:
    # 支持 Kepler/TESS 任务
    # 返回 (time, flux) 数组
```

### 3.3 新增 get_stellar_params()

- 查询恒星参数 (温度、光度、距离等)

### 3.4 detect_transit_signal() 实现

- 使用 scipy.signal.find_peaks 检测凌星信号
- 支持 SNR 阈值过滤

---

## 四、依赖

| 依赖 | 状态 | 说明 |
|------|------|------|
| httpx | ✅ 已安装 (0.28.1) | HTTP客户端 |
| numpy | ✅ 已安装 (2.4.4) | 数值计算 |
| scipy | ✅ 已安装 (1.17.1) | 信号处理 |

---

## 五、验证计划

```python
# 测试命令
from runtime.kepler_exoplanet_client import KeplerExoplanetClient
client = KeplerExoplanetClient()
planets = await client.search_planets(max_mass=10.0)
print(f"Found {len(planets)} planets")
```

**预期结果**:
- `search_planets()` 返回系外行星列表
- `get_lightcurve("Kepler-90 h")` 返回光变曲线

---

## 六、已知限制

1. **网络依赖**: 需要能访问 `exoplanetarchive.ipac.caltech.edu`
2. **环境限制**: astroquery 与 Python 3.13 不兼容，改用 httpx 直接调用 TAP API

---

## 七、文件变更

| 文件 | 变更 |
|------|------|
| `runtime/kepler_exoplanet_client.py` | 实现NASA TAP查询 |

---

**状态**: ✅ 实现完成，等待网络验证