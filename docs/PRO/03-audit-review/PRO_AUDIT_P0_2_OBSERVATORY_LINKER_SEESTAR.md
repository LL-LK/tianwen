# PRO审计文档: P0-2 observatory_linker.py集成seestar-mcp MCP协议
**审计时间**: 2026-05-01 14:52 CST (北京时间)
**优先级**: P0 (立即行动)
**关联Issue**: #15

---

## 一、现状分析

### 1.1 代码审查结果

| 文件 | 行数 | 状态 | 问题 |
|------|------|------|------|
| seestar_mcp_client.py | 764 | ⚠️ 框架完整 | 未被调用，处于独立状态 |
| observatory_linker.py | 1377 | ❌ 集成缺失 | 未引用seestar_mcp_client |

### 1.2 关键问题

**问题1: 重复的ObservationTarget定义**
```python
# seestar_mcp_client.py (Line 44-52)
@dataclass
class ObservationTarget:
    name: str = ""
    ra: float = 0.0
    dec: float = 0.0
    priority: float = 0.5
    exposure_time: float = 60.0
    filter: str = "L"

# observatory_linker.py (Line 67-98)
@dataclass
class ObservationTarget:
    name: str
    target_type: TargetType  # ← 不同的类型
    ra: float = 0.0
    dec: float = 0.0
    magnitude: float = 0.0
    spectral_info: str = ""
    simbad_id: str = ""
    mpc_id: str = ""
```

**问题2: 无集成调用**
- observatory_linker.py没有import seestar_mcp_client
- 没有调用SeestarMCPClient
- 望远镜控制功能缺失

**问题3: 模拟模式默认启用**
```python
# seestar_mcp_client.py Line 101
self._simulation_mode = True  # 默认启用模拟模式用于测试
```

---

## 二、技术方案

### 2.1 seestar-mcp项目信息

**参考**: https://github.com/taco-ops/seestar-mcp

**MCP协议命令**:
| 命令 | 说明 |
|------|------|
| seestar.goto | 望远镜转向 |
| seestar.status | 获取状态 |
| seestar.location.get | 获取位置 |
| seestar.imaging.start | 开始成像 |
| seestar.abort | 中止操作 |

### 2.2 集成架构

```
observatory_linker.py
    └── SeestarMCPClient (seestar_mcp_client.py)
            ├── MCP Protocol (JSON-RPC 2.0)
            └── Seestar Telescope Hardware
```

---

## 三、实施计划

### 3.1 立即行动 (1-2天)

| 步骤 | 行动 | 说明 |
|------|------|------|
| 1 | 统一ObservationTarget | 合并两个dataclass定义 |
| 2 | 导入seestar_mcp_client | 在observatory_linker中import |
| 3 | 实现望远镜调度 | 调用SeestarMCPClient |
| 4 | 移除模拟模式标志 | 添加配置项 |
| 5 | 测试真实硬件 | 验证MCP通信 |

### 3.2 代码修改建议

**步骤1: 统一数据类型**
```python
# 新建 unified_types.py
from seestar_mcp_client import ObservationTarget as SeestarTarget
from observatory_linker import ObservationTarget, TargetType

# 使用SeestarTarget作为基础，扩展observatory_linker需要的字段
@dataclass
class UnifiedObservationTarget(SeestarTarget):
    target_type: TargetType = TargetType.UNKNOWN
    magnitude: float = 0.0
    spectral_info: str = ""
    simbad_id: str = ""
    mpc_id: str = ""
```

**步骤2: 集成到observatory_linker.py**
```python
# observatory_linker.py 新增
from seestar_mcp_client import SeestarMCPClient, TelescopeStatus

class ObservatoryLinker:
    def __init__(self, ...):
        self.seestar = SeestarMCPClient()
        # ... existing code ...
    
    async def execute_observation(self, request: ObservationRequest) -> bool:
        """执行观测请求"""
        target = self._to_seestar_target(request.target)
        return await self.seestar.goto_target(target)
```

---

## 四、验证清单

| 验证项 | 预期结果 |
|--------|---------|
| 导入seestar_mcp_client | 无命名冲突 |
| SeestarMCPClient实例化 | 成功连接MCP服务器 |
| goto_target() | 望远镜实际转向 |
| 成像命令执行 | 相机开始曝光 |
| 状态监控 | 实时状态更新 |

---

## 五、文献来源

| 项目 | URL | 说明 |
|------|-----|------|
| seestar-mcp | https://github.com/taco-ops/seestar-mcp | ZWO Seestar MCP实现 |
| MCP协议 | https://modelcontextprotocol.io/ | Model Context Protocol |
| ZWO Seestar | https://www.zwoastro.com/seestar | 官方产品页面 |

---

## 六、审计结论

| 维度 | 评估 |
|------|------|
| 当前状态 | ❌ 未集成，代码孤立 |
| 技术可行性 | ✅ MCP协议清晰，代码框架完整 |
| 实施难度 | 中 - 需解决类型冲突 |
| 优先级 | P0 - 立即行动 |

**建议**: 
1. 统一ObservationTarget数据类型
2. 将SeestarMCPClient集成到observatory_linker
3. 添加配置项控制模拟/真实模式

---

**审计状态**: ✅ 完成
**审计人**: Hermes Agent (产品经理视角)
**待办**: 等待Claude实现或指示
