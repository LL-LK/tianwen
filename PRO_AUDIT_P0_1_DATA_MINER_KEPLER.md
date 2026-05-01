# PRO审计文档: P0-1 data_miner.py集成Kepler NASA TAP查询
**审计时间**: 2026-05-01 14:45 CST (北京时间)
**优先级**: P0 (立即行动)
**关联Issue**: #15

---

## 一、现状分析

### 1.1 代码审查结果

| 文件 | 行数 | 状态 | 问题 |
|------|------|------|------|
| kepler_exoplanet_client.py | 145 | ⚠️ 框架存在 | search_planets返回空数组 |
| data_miner.py | 58,762字节 | ⚠️ 集成缺失 | 未调用Kepler客户端 |

### 1.2 具体问题

**kepler_exoplanet_client.py**:
```python
# Line 71-72
async def search_planets(...) -> List[Dict]:
    # TODO: 实现NASA Exoplanet Archive TAP查询
    return []  # ← 返回空数组

# Line 92-93
async def get_lightcurve(...) -> tuple:
    return np.array([]), np.array([])  # ← 返回空数据
```

**问题确认**:
- search_planets() 未实现NASA TAP查询
- get_lightcurve() 返回空数据
- 无astroquery或其他TAP客户端依赖

---

## 二、技术方案

### 2.1 NASA Exoplanet Archive TAP API

**API端点**: `https://exoplanetarchive.ipac.caltech.edu/TAP/sync`

**验证结果**: ✅ API可访问
```bash
curl "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+top+3+*+from+ps&format=json"
# 返回: [{"pl_name": "K2-138 g", ...}]
```

**主要数据表**:
| 表名 | 说明 |
|------|------|
| ps | 行星星表 (Planetary Systems) |
| kep_lightcurve | Kepler光变曲线 |
| tess_lightcurve | TESS光变曲线 |

### 2.2 推荐实现方案

**方案A: astroquery (推荐)**
- Stars: 775+
- 维护: astropy团队
- 优势: 已封装TAP查询，直接可用
```python
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive
result = NasaExoplanetArchive.query_region("Kepler-90", radius="0d")
```

**方案B: 直接TAP查询 (备选)**
```python
import httpx
async def search_planets(max_mass: float = None) -> List[Dict]:
    query = "select pl_name, pl_mass, pl_radius from ps"
    if max_mass:
        query += f" where pl_mass < {max_mass}"
    url = f"{API_BASE}/TAP/sync?query={query}&format=json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

---

## 三、实施计划

### 3.1 立即行动 (1-2天)

| 步骤 | 行动 | 说明 |
|------|------|------|
| 1 | 安装astroquery依赖 | `pip install astroquery` |
| 2 | 实现search_planets() | 使用NasaExoplanetArchive |
| 3 | 实现get_lightcurve() | 获取Kepler/TESS光变曲线 |
| 4 | 集成到data_miner.py | 调用Kepler客户端 |

### 3.2 验证清单

| 验证项 | 预期结果 |
|--------|---------|
| search_planets() | 返回系外行星列表 |
| get_lightcurve("Kepler-90 h") | 返回光变曲线数据 |
| data_miner.py集成 | 可查询Kepler数据 |

---

## 四、代码修改建议

### 4.1 kepler_exoplanet_client.py 修改

```python
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive

class KeplerExoplanetClient:
    def __init__(self):
        self.client = NasaExoplanetArchive()

    async def search_planets(self, max_mass: float = None) -> List[Dict]:
        """搜索系外行星 - 使用NASA TAP查询"""
        query = "select top 100 pl_name, pl_mass, pl_radius, pl_orbper from ps"
        if max_mass:
            query += f" where pl_masse < {max_mass}"
        result = self.client.query(query)
        return result.to_dict('records')

    async def get_lightcurve(self, planet_name: str, mission: str = "Kepler") -> tuple:
        """获取光变曲线数据"""
        # 使用MAST API获取光变曲线
        # ...
```

---

## 五、文献来源

| 项目 | URL | 说明 |
|------|-----|------|
| NASA Exoplanet Archive | https://exoplanetarchive.ipac.caltech.edu | TAP API |
| astroquery | https://github.com/astropy/astroquery | 775+ stars |
| NASA Exoplanet Archive Docs | https://exoplanetarchive.ipac.caltech.edu/docs/TAP.html | TAP文档 |

---

## 六、审计结论

| 维度 | 评估 |
|------|------|
| 当前状态 | ⚠️ 框架存在但未实现 |
| 技术可行性 | ✅ API可访问，方案成熟 |
| 实施难度 | 低 - astroquery已封装 |
| 优先级 | P0 - 立即行动 |

**建议**: 使用astroquery库实现，1-2天完成集成

---

**审计状态**: ✅ 完成
**审计人**: Hermes Agent (产品经理视角)
**待办**: 等待Claude实现或指示
