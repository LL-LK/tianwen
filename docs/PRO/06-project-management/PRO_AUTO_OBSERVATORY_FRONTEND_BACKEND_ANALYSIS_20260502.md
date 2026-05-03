# 天问-AGI 全自动天文观测站 — 前后端深度需求分析与改造方案

> 生成时间: 2026-05-02 CST (北京时间)
> 分析者: 天问-AGI 产品验收审计系统
> 仓库: LL-LK/tianwen-agi
> 分支: trae
> 版本: v1.0

---

## 一、核心命题

**天问-AGI 的终极形态是：一个无需人工干预、自主完成"发现→分析→验证→观测→报告"完整闭环的全自动天文观测站。**

当前系统已具备核心的 AI 推理和研究闭环能力，但前端界面仍停留在"聊天机器人"阶段，后端 API 也以文本交互为主。要实现真正的全自动天文观测站，前后端都需要进行根本性的改造。

---

## 二、现有功能全景盘点

### 2.1 已完成的运行时模块

| 模块 | 文件 | 功能 | 成熟度 |
|------|------|------|--------|
| 研究闭环 | `research_loop.py` | 文献→假说→验证→发现→进化 | ⭐⭐⭐⭐ |
| 天体检测管道 | `astro_pipeline.py` | 三阶段检测(DAOStarFinder→ResNet→YOLOv11) | ⭐⭐⭐⭐ |
| 全自动观测站 | `auto_observatory.py` | 8步工作流编排 | ⭐⭐⭐ |
| 观测调度器 | `observation_scheduler.py` | 目标优先级+时间窗口+天气 | ⭐⭐⭐ |
| 发现追踪器 | `discovery_tracker.py` | 闭环成功率统计 | ⭐⭐⭐ |
| 开普勒系外行星 | `kepler_exoplanet_client.py` | NASA TAP凌星信号检测 | ⭐⭐⭐ |
| 数据挖掘器 | `data_miner.py` | SIMBAD/MPC/WISE/Chandra多源 | ⭐⭐⭐ |
| 天文台链接器 | `observatory_linker.py` | 虚拟/真实望远镜桥接 | ⭐⭐⭐ |
| Seestar MCP | `seestar_mcp_client.py` | 智能望远镜MCP协议 | ⭐⭐⭐ |
| 具身观测工作流 | `embodied_observation_workflow.py` | 物理设备控制 | ⭐⭐⭐ |
| 文献检索 | `literature_researcher.py` | ChromaDB向量检索+OpenAlex | ⭐⭐⭐⭐ |
| 假说检验 | `hypothesis_tester.py` | 统计假设检验 | ⭐⭐⭐ |
| 统计面板 | `cycle_statistics_dashboard.py` | HTML统计面板 | ⭐⭐⭐ |
| 天体分析器 | `astro_analyzer.py` | 光变曲线/光谱分析 | ⭐⭐⭐ |
| 恒星识别器 | `star_recognizer.py` | 星图匹配 | ⭐⭐⭐ |
| 天体数据采集 | `astro_data_collector.py` | 多源数据采集 | ⭐⭐⭐ |

### 2.2 当前后端 API 端点

| 端点 | 方法 | 功能 | 类型 |
|------|------|------|------|
| `/api/chat` | POST | 文本对话 | 文本 |
| `/api/cognitive` | POST | 认知引擎预览 | 文本 |
| `/api/sessions` | GET | 会话列表 | 文本 |
| `/api/sessions/<id>` | GET | 会话详情 | 文本 |
| `/api/evolution/stats` | GET | 进化统计 | JSON |
| `/api/health` | GET | 健康检查 | JSON |
| `/api/stats/dashboard` | GET | HTML统计面板 | HTML |
| `/api/stats/json` | GET | JSON统计 | JSON |

### 2.3 当前前端界面

| 组件 | 功能 | 适用性 |
|------|------|--------|
| 引擎状态面板 | 显示4个引擎状态 | 基础 |
| 聊天框 | 文本对话交互 | 不适合天文站 |
| 快捷测试按钮 | 代码生成/架构设计等 | 不适合天文站 |
| 消息展示 | 文本+简单格式化 | 不适合天文站 |

---

## 三、全自动天文观测站界面需求分析

### 3.1 界面设计原则

1. **信息密度优先** — 天文数据天然多维，需要高信息密度布局
2. **实时性** — 观测状态、设备状态需要秒级更新
3. **可操作性** — 虽然是"全自动"，但需要人工监控和干预入口
4. **专业性** — 面向天文学者，使用专业术语和可视化
5. **响应式** — 支持桌面(主控台)、平板(移动观测)、手机(告警通知)

### 3.2 必需界面模块

#### 模块 A: 观测总控台 (Observation Command Center)

```
┌─────────────────────────────────────────────────────────┐
│  🏠 天问-AGI 全自动天文观测站          2026-05-02 22:30 CST │
├────────────────────┬────────────────────────────────────┤
│  系统状态          │  当前观测目标                        │
│  ┌──────────────┐  │  ┌──────────────────────────────┐  │
│  │ 观测中 🟢    │  │  │ M31 仙女座星系               │  │
│  │ 运行时间: 72h │  │  │ RA: 00h42m44s Dec: +41°16'  │  │
│  │ 发现数: 3    │  │  │ 曝光: 300s × 12帧            │  │
│  │ 假说数: 15   │  │  │ 进度: ████████░░ 78%         │  │
│  └──────────────┘  │  └──────────────────────────────┘  │
├────────────────────┴────────────────────────────────────┤
│  观测队列 (Observation Queue)                            │
│  ┌──────┬──────────┬──────────┬──────┬──────┬────────┐  │
│  │ 优先级│ 目标     │ 类型     │ 窗口  │ 时长  │ 状态   │  │
│  ├──────┼──────────┼──────────┼──────┼──────┼────────┤  │
│  │ P0   │ SN2024X  │ 超新星   │ 22:30│ 15min│ 进行中 │  │
│  │ P1   │ HD209458 │ 系外行星 │ 23:00│ 120min│ 等待中 │  │
│  │ P2   │ NGC2244  │ 星团     │ 01:00│ 30min│ 等待中 │  │
│  └──────┴──────────┴──────────┴──────┴──────┴────────┘  │
└─────────────────────────────────────────────────────────┘
```

**核心功能:**
- 系统整体状态一览（观测中/空闲/故障）
- 当前目标详情（坐标、曝光参数、进度）
- 观测队列管理（拖拽排序、优先级调整）
- 一键紧急停止
- 设备健康状态（望远镜、相机、滤镜轮、圆顶）

#### 模块 B: 实时星图 (Live Sky Chart)

```
┌──────────────────────────────────────────┐
│  🌌 实时星图 (Live Sky Chart)             │
│  ┌────────────────────────────────────┐  │
│  │                                    │  │
│  │     ★ 当前目标 (M31)               │  │
│  │     ○ 队列目标                     │  │
│  │     ◉ 历史目标                     │  │
│  │     ── 地平线                      │  │
│  │     ·· 银河                        │  │
│  │                                    │  │
│  │         [Aladin Lite / WWT 嵌入]   │  │
│  │                                    │  │
│  └────────────────────────────────────┘  │
│  视场: 2°×1.5°  |  极限星等: 18.5       │
│  [放大] [缩小] [居中当前] [显示网格]     │
└──────────────────────────────────────────┘
```

**核心功能:**
- 嵌入 Aladin Lite 或 WorldWide Telescope
- 实时显示当前望远镜指向
- 叠加 SIMBAD/NED 已知天体标记
- 显示观测队列目标位置
- 地平线/天光亮度/月相叠加

#### 模块 C: 数据可视化面板 (Data Visualization)

```
┌──────────────────────────────────────────┐
│  📊 实时数据                              │
│  ┌────────────────┬───────────────────┐  │
│  │  光变曲线       │  最新图像          │  │
│  │  ╱╲  ╱╲       │  ┌─────────────┐  │  │
│  │ ╱  ╲╱  ╲╱╲   │  │             │  │  │
│  │╱          ╲╱  │  │  FITS预览   │  │  │
│  │                │  │             │  │  │
│  └────────────────│  └─────────────┘  │  │
│  ┌────────────────┴───────────────────┐  │
│  │  检测结果                           │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │ 源检测: 234个 (Stage I)       │  │  │
│  │  │ 分类: STAR:180 GALAXY:45 QSO:9│  │  │
│  │  │ YOLO检测: nebula:2 comet:1   │  │  │
│  │  └──────────────────────────────┘  │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

**核心功能:**
- 光变曲线实时绘制（Plotly.js）
- FITS 图像预览（JS9/FITS.js 嵌入）
- 检测结果统计图表
- 光谱数据展示
- 历史数据对比

#### 模块 D: 研究闭环状态 (Research Loop Status)

```
┌──────────────────────────────────────────┐
│  🔬 研究闭环 Cycle #42                     │
│  ┌────────────────────────────────────┐  │
│  │ 文献检索 ████████████ ✅ 完成       │  │
│  │ 假说生成 ████████████ ✅ 完成 (5个) │  │
│  │ 假说检验 ██████░░░░░░ 🔄 进行中     │  │
│  │ 发现确认 ░░░░░░░░░░░░ ⏳ 等待       │  │
│  │ 观测调度 ░░░░░░░░░░░░ ⏳ 等待       │  │
│  │ 自我进化 ░░░░░░░░░░░░ ⏳ 等待       │  │
│  └────────────────────────────────────┘  │
│  当前假说: "M31旋臂中存在未编目HII区"     │
│  置信度: 67.3%  |  预计完成: 23:15       │
└──────────────────────────────────────────┘
```

**核心功能:**
- 研究闭环步骤可视化
- 当前假说和置信度展示
- 发现历史时间线
- 进化记录

#### 模块 E: 告警与通知 (Alerts & Notifications)

```
┌──────────────────────────────────────────┐
│  🔔 告警中心                               │
│  ┌────────────────────────────────────┐  │
│  │ 🆕 22:28 可能发现新瞬变源 SN2024X  │  │
│  │ ⚠️ 22:15 云量增加至40%，建议暂停   │  │
│  │ ✅ 22:00 M31观测完成，12帧入库      │  │
│  │ ℹ️ 21:45 假说检验通过 (p<0.01)     │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

**核心功能:**
- 发现告警（新天体、瞬变事件）
- 系统告警（天气、设备故障）
- 进度通知（观测完成、假说验证）
- 支持 Web Push / 邮件 / 微信通知

#### 模块 F: 系统日志 (System Log)

```
┌──────────────────────────────────────────┐
│  📋 系统日志                    [自动滚动] │
│  ┌────────────────────────────────────┐  │
│  │ 22:28:15 [DISCOVERY] 新瞬变源检测  │  │
│  │ 22:28:10 [ASTROPIPE] Stage III完成 │  │
│  │ 22:27:55 [SCHEDULER] 目标切换至SN  │  │
│  │ 22:27:30 [CAMERA] 曝光300s完成     │  │
│  │ 22:22:30 [TELESCOPE] 指向M31       │  │
│  └────────────────────────────────────┘  │
│  [全部] [发现] [观测] [系统] [错误]       │
└──────────────────────────────────────────┘
```

---

## 四、当前前端 vs 需求 — 差距分析

| 需求模块 | 当前状态 | 差距 | 优先级 |
|----------|---------|------|--------|
| 观测总控台 | ❌ 不存在 | 需全新开发 | P0 |
| 实时星图 | ❌ 不存在 | 需集成 Aladin Lite | P0 |
| 数据可视化 | ❌ 不存在 | 需集成 Plotly.js + JS9 | P0 |
| 研究闭环状态 | ❌ 不存在 | 需全新开发 | P0 |
| 告警通知 | ❌ 不存在 | 需全新开发 | P1 |
| 系统日志 | ❌ 不存在 | 需全新开发 | P1 |
| 引擎状态面板 | ✅ 存在但简陋 | 需增强 | P1 |
| 聊天交互 | ✅ 存在 | 保留作为AI助手入口 | P2 |

**结论：当前前端界面完全不满足全自动天文观测站的需求。** 现有的 `web/index.html` 是一个聊天机器人界面，需要完全重构为专业的天文观测控制台。

---

## 五、后端改造方案

### 5.1 核心问题

当前后端 API 设计围绕"文本对话"展开，缺少以下关键能力：

1. **实时数据推送** — 观测状态、图像数据需要 WebSocket
2. **观测数据 API** — 光变曲线、FITS图像、检测结果
3. **设备控制 API** — 望远镜、相机、滤镜轮
4. **告警系统** — 发现通知、异常告警
5. **模块间深度集成** — 各 runtime 模块独立运行，缺少统一编排

### 5.2 新增 API 端点

#### 5.2.1 观测控制 (Observation Control)

```python
# 观测会话管理
GET    /api/observatory/status          # 观测站整体状态
POST   /api/observatory/start           # 启动观测会话
POST   /api/observatory/stop            # 停止观测会话
POST   /api/observatory/pause           # 暂停观测
POST   /api/observatory/resume          # 恢复观测

# 观测队列
GET    /api/observatory/queue           # 获取观测队列
POST   /api/observatory/queue           # 添加目标到队列
PUT    /api/observatory/queue/<id>      # 修改队列项优先级
DELETE /api/observatory/queue/<id>      # 移除队列项
POST   /api/observatory/queue/reorder   # 重新排序

# 当前目标
GET    /api/observatory/current-target  # 当前观测目标详情
```

#### 5.2.2 设备状态 (Device Status)

```python
GET    /api/devices/status              # 所有设备状态
GET    /api/devices/telescope           # 望远镜状态
GET    /api/devices/camera              # 相机状态
GET    /api/devices/filter-wheel        # 滤镜轮状态
GET    /api/devices/dome                # 圆顶状态
GET    /api/devices/weather             # 气象站数据
```

#### 5.2.3 数据服务 (Data Service)

```python
# 图像数据
GET    /api/data/images/latest          # 最新FITS图像预览
GET    /api/data/images/<id>            # 指定图像
GET    /api/data/images/<id>/fits       # 原始FITS下载
GET    /api/data/images/<id>/thumbnail  # 缩略图

# 光变曲线
GET    /api/data/lightcurve/<target>    # 目标光变曲线数据
GET    /api/data/lightcurve/<target>/plot  # 光变曲线图(SVG/PNG)

# 光谱
GET    /api/data/spectrum/<target>      # 光谱数据

# 检测结果
GET    /api/data/detections/latest      # 最新检测结果
GET    /api/data/detections/<cycle_id>  # 指定周期检测结果
```

#### 5.2.4 研究闭环 (Research Loop)

```python
GET    /api/research/status             # 当前闭环状态
GET    /api/research/cycles             # 历史闭环列表
GET    /api/research/cycles/<id>        # 指定闭环详情
GET    /api/research/hypotheses         # 当前假说列表
GET    /api/research/discoveries        # 发现列表
POST   /api/research/trigger            # 手动触发新闭环
```

#### 5.2.5 告警系统 (Alert System)

```python
GET    /api/alerts                      # 告警列表
GET    /api/alerts/unread-count         # 未读告警数
PUT    /api/alerts/<id>/read            # 标记已读
POST   /api/alerts/subscribe            # 订阅告警(Web Push)
```

#### 5.2.6 星图数据 (Sky Chart Data)

```python
GET    /api/skychart/targets            # 所有目标坐标(JSON)
GET    /api/skychart/current-fov        # 当前视场范围
GET    /api/skychart/nearby-objects     # 视场内已知天体
```

### 5.3 WebSocket 实时通道

```python
# WebSocket 端点
WS     /ws/observatory                  # 观测站实时状态推送

# 推送消息类型
{
    "type": "status_update",            # 状态更新
    "type": "exposure_progress",        # 曝光进度
    "type": "new_image",                # 新图像就绪
    "type": "detection_alert",          # 检测告警
    "type": "queue_update",             # 队列更新
    "type": "device_status",            # 设备状态
    "type": "research_progress",        # 研究进度
    "type": "log_entry",                # 日志条目
    "type": "weather_update",           # 天气更新
}
```

### 5.4 后端架构调整

#### 当前架构问题

```
当前: server.py (Quart) → 直接调用各 runtime 模块
问题:
1. 模块间耦合松散，缺少统一编排
2. 无 WebSocket 支持
3. 无后台任务调度
4. 无持久化状态管理
```

#### 建议架构

```
server.py (Quart + WebSocket)
    ├── /api/*          REST API 路由
    ├── /ws/*           WebSocket 路由
    ├── observatory_service.py   观测站核心服务(新增)
    │   ├── auto_observatory.py  工作流编排
    │   ├── observation_scheduler.py
    │   ├── discovery_tracker.py
    │   └── ...
    ├── device_service.py        设备管理服务(新增)
    │   ├── seestar_mcp_client.py
    │   ├── observatory_linker.py
    │   └── ...
    ├── data_service.py          数据服务(新增)
    │   ├── astro_pipeline.py
    │   ├── astro_analyzer.py
    │   └── ...
    └── research_service.py      研究闭环服务(新增)
        ├── research_loop.py
        ├── literature_researcher.py
        └── ...
```

### 5.5 关键新增文件

| 文件 | 功能 | 优先级 |
|------|------|--------|
| `runtime/observatory_service.py` | 观测站核心服务，统一编排所有模块 | P0 |
| `runtime/device_service.py` | 设备管理抽象层 | P0 |
| `runtime/data_service.py` | 数据存取与转换服务 | P0 |
| `runtime/research_service.py` | 研究闭环服务封装 | P0 |
| `runtime/alert_service.py` | 告警管理与分发 | P1 |
| `runtime/websocket_manager.py` | WebSocket 连接管理 | P0 |
| `runtime/state_persistence.py` | 状态持久化(SQLite) | P1 |

### 5.6 server.py 修改要点

```python
# 1. 添加 WebSocket 支持
from quart import websocket

@app.websocket('/ws/observatory')
async def observatory_ws():
    """观测站实时数据推送"""
    client_id = str(uuid.uuid4())
    websocket_manager.register(client_id, websocket._get_current_object())
    try:
        while True:
            # 保持连接，等待客户端消息(心跳)
            data = await websocket.receive()
            if data == "ping":
                await websocket.send("pong")
    except Exception:
        pass
    finally:
        websocket_manager.unregister(client_id)

# 2. 注册新的 API Blueprint
from observatory_routes import observatory_bp
from data_routes import data_bp
from research_routes import research_bp
from device_routes import device_bp
from alert_routes import alert_bp

app.register_blueprint(observatory_bp, url_prefix='/api/observatory')
app.register_blueprint(data_bp, url_prefix='/api/data')
app.register_blueprint(research_bp, url_prefix='/api/research')
app.register_blueprint(device_bp, url_prefix='/api/devices')
app.register_blueprint(alert_bp, url_prefix='/api/alerts')

# 3. 添加后台任务调度
@app.before_serving
async def startup():
    """启动后台任务"""
    app.add_background_task(observatory_service.auto_loop)
    app.add_background_task(alert_service.check_and_notify)
    app.add_background_task(websocket_manager.broadcast_status)

# 4. CORS 配置增强
app = cors(app, allow_origin=CORS_ORIGINS, allow_credentials=True)
```

---

## 六、前端改造方案

### 6.1 技术选型建议

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **纯 HTML/JS/CSS** (当前) | 零依赖，部署简单 | 复杂UI难维护 | ⭐⭐ |
| **Vue.js + Vite** | 渐进式，学习曲线平缓 | 需构建步骤 | ⭐⭐⭐⭐ |
| **React + Next.js** | 生态丰富 | 学习曲线陡峭 | ⭐⭐⭐ |
| **Flutter Web** | 与移动端统一 | 体积大，天文库少 | ⭐⭐ |

**推荐方案: Vue 3 + Vite + TypeScript**，原因：
1. 渐进式框架，可在现有 HTML 基础上逐步迁移
2. 生态中有成熟的天文可视化库封装
3. 构建产物小，适合 Cloudflare Pages 部署
4. 中文社区活跃

### 6.2 前端文件结构

```
web/
├── index.html                    # 入口(重定向到新界面)
├── src/
│   ├── main.ts                   # 应用入口
│   ├── App.vue                   # 根组件
│   ├── router/
│   │   └── index.ts              # 路由配置
│   ├── stores/
│   │   ├── observatory.ts        # 观测站状态(Pinia)
│   │   ├── devices.ts            # 设备状态
│   │   ├── research.ts           # 研究闭环状态
│   │   └── alerts.ts             # 告警状态
│   ├── composables/
│   │   ├── useWebSocket.ts       # WebSocket 连接
│   │   ├── useAladinLite.ts      # Aladin Lite 嵌入
│   │   └── usePlotly.ts          # Plotly.js 封装
│   ├── views/
│   │   ├── CommandCenter.vue     # 观测总控台
│   │   ├── SkyChart.vue          # 实时星图
│   │   ├── DataPanel.vue         # 数据可视化
│   │   ├── ResearchLoop.vue      # 研究闭环
│   │   ├── AlertCenter.vue       # 告警中心
│   │   ├── SystemLog.vue         # 系统日志
│   │   ├── DevicePanel.vue       # 设备管理
│   │   └── Settings.vue          # 设置(含登录)
│   ├── components/
│   │   ├── StatusBadge.vue       # 状态徽章
│   │   ├── TargetCard.vue        # 目标卡片
│   │   ├── ObservationQueue.vue  # 观测队列
│   │   ├── LightCurve.vue        # 光变曲线
│   │   ├── FitsViewer.vue        # FITS查看器
│   │   ├── DetectionResult.vue   # 检测结果
│   │   └── AlertToast.vue        # 告警提示
│   └── assets/
│       └── styles/
│           └── main.css          # 全局样式
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### 6.3 关键第三方库

| 库 | 用途 | 替代方案 |
|----|------|---------|
| `aladin-lite` | 星图嵌入 | WWT WebGL |
| `plotly.js-dist-min` | 光变曲线/图表 | Chart.js |
| `js9` | FITS图像查看 | fits.js |
| `pinia` | 状态管理 | Vuex |
| `vue-router` | 路由 | - |
| `@vueuse/core` | 工具函数(useWebSocket等) | - |

---

## 七、实施路线图

### Phase 1: 后端核心 API (1-2周)

```
□ 创建 observatory_service.py — 统一编排
□ 创建 data_service.py — 数据存取
□ 创建 research_service.py — 闭环封装
□ 创建 websocket_manager.py — WebSocket管理
□ server.py 添加 WebSocket 端点
□ server.py 注册新 API Blueprint
□ 添加后台任务调度
```

### Phase 2: 前端基础框架 (1-2周)

```
□ 初始化 Vue 3 + Vite 项目
□ 搭建路由和状态管理
□ 实现 WebSocket 连接
□ 实现观测总控台 (CommandCenter)
□ 实现观测队列组件
□ 实现系统日志组件
```

### Phase 3: 数据可视化 (1周)

```
□ 集成 Aladin Lite 星图
□ 集成 Plotly.js 光变曲线
□ 集成 JS9 FITS查看器
□ 实现检测结果展示
```

### Phase 4: 告警与完善 (1周)

```
□ 实现告警中心
□ 实现设备管理面板
□ 实现研究闭环可视化
□ 实现设置页面(含登录)
□ 移动端适配
```

---

## 八、当前可立即执行的改进

在不进行大规模重构的前提下，以下改进可以立即在现有代码基础上完成：

### 8.1 后端立即改进

1. **添加 `/api/observatory/status` 端点** — 直接调用 `auto_observatory.py` 获取状态
2. **添加 `/api/research/status` 端点** — 直接调用 `research_loop.py` 获取闭环状态
3. **添加 `/api/data/detections/latest` 端点** — 直接调用 `astro_pipeline.py` 获取检测结果
4. **添加 WebSocket 支持** — Quart 原生支持，只需添加路由

### 8.2 前端立即改进

1. **在现有 `index.html` 中添加"观测站"标签页** — 不重构，先加功能
2. **添加简单的状态轮询** — 用 `setInterval` 轮询 `/api/observatory/status`
3. **添加 FITS 图像预览** — 嵌入 JS9 的 CDN 版本
4. **添加光变曲线** — 嵌入 Plotly.js CDN 版本

---

## 九、总结

| 维度 | 当前状态 | 目标状态 | 差距 |
|------|---------|---------|------|
| 前端界面 | 聊天机器人 | 专业天文观测控制台 | 🔴 巨大 |
| 后端 API | 8个文本端点 | 30+端点 + WebSocket | 🔴 巨大 |
| 模块集成 | 松散独立 | 统一编排服务 | 🟡 中等 |
| 实时性 | 无 | WebSocket秒级推送 | 🔴 巨大 |
| 数据可视化 | 无 | 星图+光变+FITS | 🔴 巨大 |
| 告警系统 | 无 | 多通道通知 | 🟡 中等 |
| 设备控制 | 部分(MCP) | 完整抽象层 | 🟡 中等 |

**核心结论：天问-AGI 的运行时模块（研究闭环、天体检测、观测调度等）已经具备了全自动天文观测站的核心能力，但前后端界面层严重滞后。当前的前端是一个聊天机器人界面，后端 API 也围绕文本交互设计，完全无法承载专业天文观测站的交互需求。需要进行一次系统性的前后端重构，将已有的强大运行时能力通过专业的界面和 API 暴露出来。**

---

**文档版本**: v1.0
**生成时间**: 2026-05-02 CST
**分支**: trae
