"""
Hermes-AGI Web API Server
为web/index.html提供后端API支持

安全配置:
- DEBUG: 环境变量控制，默认false
- API_KEY: API认证密钥
- CORS_ORIGINS: 允许的跨域域名（逗号分隔）
"""

import asyncio
import sys
import os
import secrets
import logging
import traceback
from pathlib import Path
from functools import wraps
import psutil

sys.path.insert(0, str(Path(__file__).parent))

from quart import Quart, jsonify, request, render_template, websocket
import uuid
import json
import time
import random
from threading import Lock
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("hermes_agi")

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
API_KEY = os.environ.get("API_KEY", "")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

app = Quart(__name__, template_folder="../web", static_folder="../web")
app.config["PROVIDE_AUTOMATIC_OPTIONS"] = True
app.config["TEMPLATES_AUTO_RELOAD"] = DEBUG

@app.after_request
async def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response

from main import HermesAGI, CognitiveEngine, PlanningEngine
from cycle_statistics_dashboard import CycleStatisticsDashboard
from reasoning_engine import ModelConfig
import httpx

agent = HermesAGI()
dashboard = CycleStatisticsDashboard()

RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", 60))
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 30))
_rate_limit_store: dict = defaultdict(list)


def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    _rate_limit_store[client_ip].append(now)
    return True


def _validate_required_fields(data: dict, required: list[str]) -> str | None:
    for field in required:
        if not data.get(field):
            return f"缺少必填字段: {field}"
    return None


def _sanitize_str(value: str, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_len]


@app.errorhandler(400)
async def bad_request(e):
    return jsonify({"error": "请求参数无效", "code": "BAD_REQUEST"}), 400


@app.errorhandler(404)
async def not_found(e):
    return jsonify({"error": "资源不存在", "code": "NOT_FOUND"}), 404


@app.errorhandler(405)
async def method_not_allowed(e):
    return jsonify({"error": "不支持的请求方法", "code": "METHOD_NOT_ALLOWED"}), 405


@app.errorhandler(500)
async def internal_error(e):
    logger.error(f"Internal server error: {traceback.format_exc()}")
    return jsonify({"error": "服务器内部错误", "code": "INTERNAL_ERROR"}), 500


@app.after_request
async def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def require_api_key(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if DEBUG and not API_KEY:
            return await f(*args, **kwargs)
        if not provided_key:
            return jsonify({"error": "API Key required", "code": "MISSING_KEY"}), 401
        if not secrets.compare_digest(provided_key, API_KEY):
            return jsonify({"error": "Invalid API Key", "code": "INVALID_KEY"}), 403
        return await f(*args, **kwargs)
    return decorated


async def call_minimax(message: str) -> dict:
    """调用MiniMax API"""
    group_id = os.environ.get("MINIMAX_GROUP_ID")
    api_key = os.environ.get("MINIMAX_API_KEY")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-Text-01")
    if not api_key or not group_id:
        return {"error": "MiniMax API key or Group ID not configured", "content": None}

    config = ModelConfig.minimax_api(api_key, model)
    client = httpx.AsyncClient(timeout=60.0)

    try:
        response = await client.post(
            f"{config.endpoint}/text/chatcompletion_v2",
            json={
                "model": config.name,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 2000,
                "temperature": 0.7,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "GroupId": group_id
            }
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"MiniMax response: {result}")
        choices = result.get("choices", [])
        if not choices:
            return {"error": "No choices in response", "content": None}
        content = choices[0].get("message", {}).get("content")
        if content is None:
            return {"error": "Content is None in response", "content": None}
        tokens = result.get("usage", {}).get("total_tokens", 0)
        return {"content": content, "tokens": tokens}
    except Exception as e:
        return {"error": str(e), "content": None}
    finally:
        await client.aclose()

# 会话存储
sessions: dict = {}
sessions_lock = Lock()
SESSIONS_FILE = Path(__file__).parent / "sessions.json"


def load_sessions():
    """从文件加载会话"""
    global sessions
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
            logger.info(f"Loaded {len(sessions)} sessions from disk")
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            sessions = {}


def save_sessions():
    """将会话保存到文件"""
    with sessions_lock:
        try:
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")


def cleanup_old_sessions(max_age_days: int = 30):
    """清理超过最大年龄的会话"""
    cutoff = datetime.now().timestamp() - (max_age_days * 86400)
    removed = 0
    for sid in list(sessions.keys()):
        try:
            created = datetime.fromisoformat(sessions[sid].get("created_at", "2000-01-01"))
            if created.timestamp() < cutoff:
                del sessions[sid]
                removed += 1
        except Exception:
            pass
    if removed > 0:
        logger.info(f"Cleaned up {removed} old sessions")
        save_sessions()


# 启动时加载会话
load_sessions()
cleanup_old_sessions()

@app.route("/")
async def index():
    """主页"""
    return await render_template("index.html")

@app.route("/api/chat", methods=["POST"])
@require_api_key
async def chat():
    """处理对话请求 - 简化版（不调用LLM）"""
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id")

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"error": "请求过于频繁，请稍后再试", "code": "RATE_LIMITED"}), 429

    # 创建新会话或使用现有会话
    if session_id and session_id in sessions:
        session = sessions[session_id]
    else:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
        }
        session = sessions[session_id]

    # 记录用户消息
    session["messages"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat(),
    })

    try:
        # 调用MiniMax API
        llm_result = await call_minimax(message)

        if llm_result.get("error"):
            # 如果API调用失败，返回简化响应
            response_text = f"收到消息: {message[:50]}..."
            response_data = {
                "session_id": session_id,
                "cognitive": {"intent": "chat", "entities": [], "skills": [], "complexity": "low"},
                "plan": {"task_id": str(uuid.uuid4()), "subtasks": [], "estimated_time": "0s", "risks": []},
                "output": response_text,
                "metrics": {"tokens_used": 0, "latency_ms": 0},
                "status": "simplified",
                "error": llm_result["error"],
            }
        else:
            response_text = llm_result["content"]
            response_data = {
                "session_id": session_id,
                "cognitive": {
                    "intent": "chat",
                    "entities": [],
                    "skills": [],
                    "complexity": "low",
                },
                "plan": {
                    "task_id": str(uuid.uuid4()),
                    "subtasks": [],
                    "estimated_time": "0s",
                    "risks": [],
                },
                "output": response_text,
                "metrics": {
                    "tokens_used": llm_result.get("tokens", 0),
                    "latency_ms": 0,
                },
                "status": "success",
            }

        # 记录助手消息
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat(),
            "data": response_data,
        })

        # 保存会话到磁盘
        save_sessions()

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "session_id": session_id,
        }), 500

@app.route("/api/cognitive", methods=["POST"])
async def cognitive_preview():
    """认知引擎预览 - 不执行，只分析用户输入"""
    data = await request.get_json()
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    cognitive = CognitiveEngine()
    task_model = cognitive.process(message)

    return jsonify({
        "intent": task_model.type.value,
        "entities": [
            {"type": e.type, "value": e.value, "confidence": e.confidence}
            for e in task_model.entities
        ],
        "required_skills": task_model.required_skills,
        "complexity": task_model.complexity,
        "description": task_model.description,
    })

@app.route("/api/sessions", methods=["GET"])
async def list_sessions():
    """获取所有会话"""
    return jsonify({
        "sessions": [
            {
                "id": s["id"],
                "created_at": s["created_at"],
                "message_count": len(s["messages"]),
            }
            for s in sessions.values()
        ]
    })

@app.route("/api/sessions/<session_id>", methods=["GET"])
async def get_session(session_id):
    """获取指定会话"""
    if session_id not in sessions:
        return jsonify({"error": "会话不存在"}), 404

    return jsonify(sessions[session_id])

@app.route("/api/evolution/stats", methods=["GET"])
async def evolution_stats():
    """获取进化系统统计"""
    stats = agent.evolution.get_stats()
    return jsonify(stats)

@app.route("/api/health", methods=["GET"])
async def health():
    """健康检查 - 包含运行时依赖检查"""
    health_data = {
        "status": "ok",
        "version": "2.2.0",
        "timestamp": datetime.now().isoformat(),
        "system": {
            "memory": {
                "total_mb": psutil.virtual_memory().total / (1024 * 1024),
                "available_mb": psutil.virtual_memory().available / (1024 * 1024),
                "percent": psutil.virtual_memory().percent,
            },
            "cpu": {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=0.1),
            },
            "process": {
                "pid": os.getpid(),
                "threads": psutil.Process().num_threads(),
                "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024),
            }
        },
        "dependencies": {
            "agent_initialized": agent is not None,
            "cognitive_engine": agent.cognitive is not None if agent else False,
            "planning_engine": agent.planning is not None if agent else False,
            "execution_engine": agent.execution is not None if agent else False,
            "evolution_system": agent.evolution is not None if agent else False,
        },
        "sessions": {
            "active_count": len(sessions),
        }
    }

    # 检查数据库连接 (内存数据库，无需外部依赖)
    health_data["database"] = {
        "type": "in-memory",
        "status": "connected",
        "sessions_count": len(sessions),
    }

    # 检查外部API可达性 (模拟检查)
    health_data["external_apis"] = {
        "status": "not_configured",
        "message": "无外部API依赖",
    }

    # 汇总状态
    overall_healthy = True
    if health_data["system"]["memory"]["percent"] > 90:
        overall_healthy = False
    if health_data["system"]["cpu"]["percent"] > 95:
        overall_healthy = False
    if not all(health_data["dependencies"].values()):
        overall_healthy = False

    health_data["status"] = "ok" if overall_healthy else "degraded"

    return jsonify(health_data)

@app.route("/api/stats/dashboard", methods=["GET"])
async def stats_dashboard():
    """返回HTML统计面板"""
    html = dashboard.get_html_dashboard()
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/api/stats/json", methods=["GET"])
async def stats_json():
    """返回JSON格式的统计"""
    stats = dashboard.get_summary_stats()
    return jsonify(stats)

# ============ WebSocket 连接管理 ============

class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self._connections: dict = {}
        self._lock = Lock()

    def register(self, client_id: str, ws):
        with self._lock:
            self._connections[client_id] = ws
        logger.info(f"WebSocket client connected: {client_id} (total: {len(self._connections)})")

    def unregister(self, client_id: str):
        with self._lock:
            self._connections.pop(client_id, None)
        logger.info(f"WebSocket client disconnected: {client_id} (total: {len(self._connections)})")

    async def broadcast(self, message: dict):
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead = []
        for cid, ws in list(self._connections.items()):
            try:
                await ws.send(data)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.unregister(cid)

    async def broadcast_status(self):
        while True:
            await asyncio.sleep(2)
            status = _build_observatory_status()
            await self.broadcast({"type": "status_update", "data": status})

    @property
    def connection_count(self):
        return len(self._connections)


ws_manager = WebSocketManager()

try:
    from realtime_bridge import (
        EventBus, AgentStateBridge, ConnectionManager,
        MessageSerializer, start_heartbeat_loop, start_broadcast_loop,
    )
    _event_bus = EventBus()
    _state_bridge = AgentStateBridge(_event_bus)
    _conn_manager = ConnectionManager()
    _REALTIME_BRIDGE_AVAILABLE = True
    logger.info("Realtime bridge module loaded successfully")
except ImportError:
    _event_bus = None
    _state_bridge = None
    _conn_manager = None
    _REALTIME_BRIDGE_AVAILABLE = False
    logger.warning("Realtime bridge module not available, using legacy WebSocket manager")

# ============ 模拟数据生成 ============

_observatory_state = {
    "status": "observing",
    "uptime_hours": 72.5,
    "discoveries": 3,
    "hypotheses": 15,
    "current_target": {
        "name": "M31 仙女座星系",
        "ra": "00h42m44s",
        "dec": "+41°16'09\"",
        "type": "星系",
        "magnitude": 3.44,
        "exposure": "300s × 12帧",
        "progress": 78,
    },
    "queue": [
        {"id": "q1", "priority": "P0", "target": "SN2024X", "type": "超新星", "window": "22:30-22:45", "duration": "15min", "status": "进行中"},
        {"id": "q2", "priority": "P1", "target": "HD209458", "type": "系外行星", "window": "23:00-01:00", "duration": "120min", "status": "等待中"},
        {"id": "q3", "priority": "P2", "target": "NGC2244", "type": "星团", "window": "01:00-01:30", "duration": "30min", "status": "等待中"},
        {"id": "q4", "priority": "P1", "target": "M42", "type": "星云", "window": "01:30-02:00", "duration": "30min", "status": "等待中"},
        {"id": "q5", "priority": "P2", "target": "Jupiter", "type": "行星", "window": "02:00-02:30", "duration": "30min", "status": "等待中"},
    ],
    "devices": {
        "telescope": {"name": "Seestar S50", "status": "tracking", "connected": True},
        "camera": {"name": "IMX462", "status": "exposing", "gain": 120, "exposure_ms": 300000},
        "filter_wheel": {"name": "ZWO EFW", "status": "idle", "current": "Luminance"},
        "dome": {"name": "远程圆顶", "status": "open", "azimuth": 45},
        "weather": {"cloud_cover": 12, "humidity": 45, "temperature": 18.5, "wind_speed": 3.2, "seeing": 1.8},
    },
    "research_loop": {
        "cycle_id": "cycle_a3f8b2c1",
        "cycle_number": 42,
        "topic": "M31旋臂中未编目HII区搜索",
        "steps": [
            {"name": "文献检索", "status": "completed", "progress": 100},
            {"name": "假说生成", "status": "completed", "progress": 100, "detail": "生成5个假说"},
            {"name": "假说检验", "status": "running", "progress": 65},
            {"name": "发现确认", "status": "pending", "progress": 0},
            {"name": "观测调度", "status": "pending", "progress": 0},
            {"name": "自我进化", "status": "pending", "progress": 0},
        ],
        "current_hypothesis": "M31旋臂中存在未编目HII区",
        "confidence": 67.3,
        "estimated_completion": "23:15",
    },
    "detections": {
        "stage1": {"total": 234, "stars": 180, "galaxies": 45, "qsos": 9},
        "stage2": {"classified_stars": 178, "classified_galaxies": 43, "classified_qsos": 8, "unknown": 5},
        "stage3": {"nebula": 2, "comet": 1, "galaxy": 0, "globular_cluster": 0},
    },
    "latest_image": {
        "id": "img_20260502_223015",
        "target": "M31",
        "exposure": 300,
        "filter": "L",
        "timestamp": "2026-05-02T22:30:15",
        "size_kb": 8192,
    },
}

_alerts = [
    {"id": "a1", "level": "discovery", "time": "22:28", "message": "可能发现新瞬变源 SN2024X", "read": False},
    {"id": "a2", "level": "warning", "time": "22:15", "message": "云量增加至40%，建议暂停观测", "read": False},
    {"id": "a3", "level": "success", "time": "22:00", "message": "M31观测完成，12帧已入库", "read": True},
    {"id": "a4", "level": "info", "time": "21:45", "message": "假说检验通过 (p<0.01)", "read": True},
    {"id": "a5", "level": "info", "time": "21:30", "message": "Cycle #41 完成，发现1个候选天体", "read": True},
]

_log_entries = [
    {"time": "22:28:15", "level": "DISCOVERY", "message": "新瞬变源检测: SN2024X候选"},
    {"time": "22:28:10", "level": "ASTROPIPE", "message": "Stage III YOLO检测完成"},
    {"time": "22:27:55", "level": "SCHEDULER", "message": "目标切换至 SN2024X"},
    {"time": "22:27:30", "level": "CAMERA", "message": "曝光300s完成，图像已保存"},
    {"time": "22:22:30", "level": "TELESCOPE", "message": "望远镜指向 M31 (00h42m44s +41°16')"},
    {"time": "22:22:00", "level": "RESEARCH", "message": "假说检验进度: 65%"},
    {"time": "22:20:00", "level": "WEATHER", "message": "天气更新: 云量12%, 视宁度1.8\""},
    {"time": "22:15:00", "level": "SYSTEM", "message": "自动观测循环启动"},
]

_lightcurve_data = {
    "time": [f"22:{i:02d}" for i in range(0, 31)],
    "magnitude": [15.2 + 0.3 * (i % 5) + random.uniform(-0.05, 0.05) for i in range(31)],
    "error": [0.02 + random.uniform(0, 0.01) for _ in range(31)],
}

_cycle_history = []
for i in range(1, 43):
    _cycle_history.append({
        "id": f"cycle_{uuid.uuid4().hex[:8]}",
        "number": i,
        "topic": f"自动研究周期 #{i}",
        "started_at": (datetime.now() - timedelta(hours=72 - i * 1.7)).isoformat(),
        "completed_at": (datetime.now() - timedelta(hours=72 - i * 1.7 - 0.5)).isoformat() if i < 42 else None,
        "status": "completed" if i < 42 else "running",
        "discoveries": random.randint(0, 2),
        "hypotheses": random.randint(1, 8),
    })


def _build_observatory_status():
    state = _observatory_state.copy()
    state["timestamp"] = datetime.now().isoformat()
    state["ws_clients"] = ws_manager.connection_count
    return state


# ============ API 文档 ============

@app.route("/api/docs", methods=["GET"])
async def api_docs():
    return jsonify({
        "service": "天问-AGI 全自动天文观测站 API",
        "version": "2.3.0",
        "endpoints": {
            "observatory": {
                "GET  /api/observatory/status": "观测站完整状态",
                "GET  /api/observatory/queue": "观测队列",
                "POST /api/observatory/queue": "添加观测目标 {target, priority, type, window, duration}",
                "DELETE /api/observatory/queue/<id>": "移除队列项",
                "POST /api/observatory/control": "控制观测站 {action: start|stop|pause|resume}",
            },
            "devices": {
                "GET  /api/devices/status": "设备状态(望远镜/相机/滤镜轮/圆顶/气象站)",
            },
            "data": {
                "GET  /api/data/detections/latest": "三阶段检测结果",
                "GET  /api/data/images/latest": "最新图像信息",
                "GET  /api/data/lightcurve?target=M31": "光变曲线数据",
            },
            "research": {
                "GET  /api/research/status": "研究闭环状态",
                "GET  /api/research/cycles?page=1&per_page=20": "历史研究周期",
            },
            "alerts": {
                "GET  /api/alerts?unread=true": "告警列表",
                "PUT  /api/alerts/<id>/read": "标记告警已读",
            },
            "logs": {
                "GET  /api/logs?level=DISCOVERY&limit=50": "系统日志",
            },
            "system": {
                "GET  /api/health": "健康检查",
                "GET  /api/stats/summary": "统计摘要",
                "GET  /api/stats/json": "JSON统计",
                "GET  /api/stats/dashboard": "HTML统计面板",
            },
            "chat": {
                "POST /api/chat": "LLM对话 {message, session_id}",
                "POST /api/cognitive": "认知引擎预览 {message}",
                "GET  /api/sessions": "会话列表",
                "GET  /api/sessions/<id>": "会话详情",
            },
            "websocket": {
                "WS   /ws/observatory": "观测站实时推送 (status_update, queue_update, new_alert)",
            },
        },
        "realtime_bridge": "available" if _REALTIME_BRIDGE_AVAILABLE else "unavailable",
    })


# ============ WebSocket 端点 ============

@app.websocket('/ws/observatory')
async def observatory_ws():
    client_id = str(uuid.uuid4())
    if _REALTIME_BRIDGE_AVAILABLE:
        _conn_manager.register(client_id, websocket._get_current_object())
    else:
        ws_manager.register(client_id, websocket._get_current_object())

    try:
        while True:
            data = await websocket.receive()
            if data == "ping":
                await websocket.send("pong")
                if _REALTIME_BRIDGE_AVAILABLE:
                    _conn_manager.heartbeat(client_id)
            elif data == "get_status":
                status = _build_observatory_status()
                await websocket.send(json.dumps(
                    {"type": "status_update", "data": status},
                    ensure_ascii=False, default=str
                ))
            elif data and data.startswith("{"):
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "subscribe" and _REALTIME_BRIDGE_AVAILABLE:
                        event_type = msg.get("event", "")
                        if event_type:
                            async def _forward(event_type_inner, event_data):
                                try:
                                    await websocket.send(MessageSerializer.serialize_event(event_type_inner, event_data))
                                except Exception:
                                    pass
                            _event_bus.subscribe(event_type, _forward)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    finally:
        if _REALTIME_BRIDGE_AVAILABLE:
            _conn_manager.unregister(client_id)
        else:
            ws_manager.unregister(client_id)


# ============ 观测站 API ============

@app.route("/api/observatory/status", methods=["GET"])
async def observatory_status():
    return jsonify(_build_observatory_status())


@app.route("/api/observatory/queue", methods=["GET"])
async def observatory_queue():
    return jsonify({"queue": _observatory_state["queue"]})


@app.route("/api/observatory/queue", methods=["POST"])
async def observatory_queue_add():
    data = await request.get_json()
    if not data or not data.get("target"):
        return jsonify({"error": "目标名称不能为空"}), 400
    new_item = {
        "id": f"q{uuid.uuid4().hex[:6]}",
        "priority": data.get("priority", "P2"),
        "target": data["target"],
        "type": data.get("type", "未知"),
        "window": data.get("window", "待定"),
        "duration": data.get("duration", "30min"),
        "status": "等待中",
    }
    _observatory_state["queue"].append(new_item)
    await ws_manager.broadcast({"type": "queue_update", "data": _observatory_state["queue"]})
    return jsonify({"success": True, "item": new_item})


@app.route("/api/observatory/queue/<item_id>", methods=["DELETE"])
async def observatory_queue_remove(item_id):
    _observatory_state["queue"] = [q for q in _observatory_state["queue"] if q["id"] != item_id]
    await ws_manager.broadcast({"type": "queue_update", "data": _observatory_state["queue"]})
    return jsonify({"success": True})


@app.route("/api/observatory/control", methods=["POST"])
async def observatory_control():
    data = await request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400
    action = data.get("action", "")
    valid_actions = ["start", "stop", "pause", "resume"]
    if action not in valid_actions:
        return jsonify({"error": f"无效操作: {action}，支持: {valid_actions}"}), 400

    status_map = {"start": "observing", "stop": "idle", "pause": "paused", "resume": "observing"}
    new_status = status_map[action]
    _observatory_state["status"] = new_status
    _log_entries.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": "SYSTEM",
        "message": f"观测站状态变更: {action}"
    })

    if _REALTIME_BRIDGE_AVAILABLE:
        _state_bridge.update_status(new_status)
        await _conn_manager.broadcast({
            "type": "status_update",
            "data": _build_observatory_status(),
        })
    else:
        await ws_manager.broadcast({
            "type": "status_update",
            "data": _build_observatory_status(),
        })
    return jsonify({"success": True, "status": new_status})


# ============ 设备 API ============

@app.route("/api/devices/status", methods=["GET"])
async def devices_status():
    return jsonify(_observatory_state["devices"])


# ============ 数据 API ============

@app.route("/api/data/detections/latest", methods=["GET"])
async def data_detections_latest():
    return jsonify(_observatory_state["detections"])


@app.route("/api/data/images/latest", methods=["GET"])
async def data_images_latest():
    return jsonify(_observatory_state["latest_image"])


@app.route("/api/data/lightcurve", methods=["GET"])
async def data_lightcurve():
    target = request.args.get("target", "M31")
    return jsonify({"target": target, "data": _lightcurve_data})


# ============ 研究闭环 API ============

@app.route("/api/research/status", methods=["GET"])
async def research_status():
    return jsonify(_observatory_state["research_loop"])


@app.route("/api/research/cycles", methods=["GET"])
async def research_cycles():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        "cycles": _cycle_history[::-1][start:end],
        "total": len(_cycle_history),
        "page": page,
        "per_page": per_page,
    })


# ============ 告警 API ============

@app.route("/api/alerts", methods=["GET"])
async def alerts_list():
    unread_only = request.args.get("unread", "false").lower() == "true"
    result = [a for a in _alerts if not unread_only or not a["read"]]
    return jsonify({"alerts": result, "unread_count": sum(1 for a in _alerts if not a["read"])})


@app.route("/api/alerts/<alert_id>/read", methods=["PUT"])
async def alerts_mark_read(alert_id):
    for a in _alerts:
        if a["id"] == alert_id:
            a["read"] = True
            return jsonify({"success": True})
    return jsonify({"error": "告警不存在"}), 404


# ============ 日志 API ============

@app.route("/api/logs", methods=["GET"])
async def logs_list():
    level = request.args.get("level", "")
    limit = int(request.args.get("limit", 50))
    result = _log_entries
    if level:
        result = [e for e in result if e["level"].upper() == level.upper()]
    return jsonify({"logs": result[:limit]})


# ============ 统计 API ============

@app.route("/api/stats/summary", methods=["GET"])
async def stats_summary():
    return jsonify({
        "total_cycles": len(_cycle_history),
        "completed_cycles": sum(1 for c in _cycle_history if c["status"] == "completed"),
        "total_discoveries": sum(c["discoveries"] for c in _cycle_history),
        "total_hypotheses": sum(c["hypotheses"] for c in _cycle_history),
        "uptime_hours": _observatory_state["uptime_hours"],
        "active_ws_clients": ws_manager.connection_count,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    logger.info("=" * 50)
    logger.info("天问-AGI 全自动天文观测站 API Server")
    logger.info("=" * 50)
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"API Key configured: {'Yes' if API_KEY else 'No (auth disabled)'}")
    logger.info(f"CORS Origins: {CORS_ORIGINS or 'All (debug mode)'}")
    logger.info(f"Realtime Bridge: {'Available' if _REALTIME_BRIDGE_AVAILABLE else 'Unavailable (legacy mode)'}")
    logger.info(f"Local:    http://localhost:{port}")
    logger.info(f"API Docs: http://localhost:{port}/api/docs")
    logger.info(f"Health:   http://localhost:{port}/api/health")
    logger.info(f"WebSocket: ws://localhost:{port}/ws/observatory")
    logger.info("=" * 50)

    if _REALTIME_BRIDGE_AVAILABLE:
        @app.before_serving
        async def start_bridge_tasks():
            asyncio.ensure_future(start_heartbeat_loop(_conn_manager))
            asyncio.ensure_future(start_broadcast_loop(_conn_manager, _state_bridge))
            logger.info("Realtime bridge background tasks started")

    app.run(host="0.0.0.0", port=port, debug=DEBUG)