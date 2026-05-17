# system.py - System routes extracted from server.py
# Functions: health, ping, api_docs

import logging
import os
import psutil
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")

# Global references
DEBUG = None
_observatory_state = None
_enhancements = None
agent = None
dashboard = None
sessions = None
_session_store_type = None


def init_system_routes(debug, obs_state, enh, a, dash, sess, store_type):
    """Initialize global references from parent module"""
    global DEBUG, _observatory_state, _enhancements, agent, dashboard, sessions, _session_store_type
    DEBUG = debug
    _observatory_state = obs_state
    _enhancements = enh
    agent = a
    dashboard = dash
    sessions = sess
    _session_store_type = store_type


from datetime import datetime


async def health():
    """健康检查"""
    from quart import jsonify
    
    try:
        agent_ok = agent is not None
        cognitive_ok = agent.cognitive is not None if agent_ok else False
        planning_ok = agent.planning is not None if agent_ok else False
        execution_ok = agent.execution is not None if agent_ok else False
        evolution_ok = agent.evolution is not None if agent_ok else False
    except Exception:
        agent_ok = False
        cognitive_ok = False
        planning_ok = False
        execution_ok = False
        evolution_ok = False

    if DEBUG:
        health_data = {
            "status": "ok",
            "version": "2.4.0",
            "build_id": "trae-perf-20260505",
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
                "agent_initialized": agent_ok,
                "cognitive_engine": cognitive_ok,
                "planning_engine": planning_ok,
                "execution_engine": execution_ok,
                "evolution_system": evolution_ok,
            },
            "sessions": {
                "active_count": len(sessions),
            },
            "database": {
                "type": _session_store_type,
                "status": "connected",
                "sessions_count": len(sessions),
            },
            "external_apis": {
                "minimax_configured": bool(os.environ.get("MINIMAX_API_KEY") and os.environ.get("MINIMAX_GROUP_ID")),
                "deepseek_configured": bool(os.environ.get("DEEPSEEK_API_KEY")),
            }
        }
        if psutil.virtual_memory().percent > 90 or psutil.cpu_percent(interval=0.1) > 95:
            health_data["status"] = "degraded"
    else:
        health_data = {
            "status": "ok",
            "version": "2.4.0",
            "timestamp": datetime.now().isoformat(),
        }
        if psutil.virtual_memory().percent > 90 or psutil.cpu_percent(interval=0.1) > 95:
            health_data["status"] = "degraded"

    return jsonify(health_data)


async def ping():
    """轻量级连通性检测（无系统信息采集，极快响应）"""
    from quart import jsonify
    return jsonify({"status": "ok", "version": "2.4.0", "timestamp": datetime.now().isoformat()})


async def api_docs():
    """API文档"""
    from quart import jsonify
    
    _REALTIME_BRIDGE_AVAILABLE = False
    try:
        from realtime_bridge import RealtimeBridge
        _REALTIME_BRIDGE_AVAILABLE = True
    except ImportError:
        pass
    
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
                "POST /api/hypothesis/test": "假说验证 (需要hypothesis对象，必须提供观测数据和文献证据)",
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
                "WS   /ws/agent_status": "Agent状态实时推送 (cognitive, planning, execution状态)",
                "WS   /ws/observation": "观测状态实时推送 (设备状态, 队列状态)",
            },
        },
        "realtime_bridge": "available" if _REALTIME_BRIDGE_AVAILABLE else "unavailable",
    })


def register_system_routes(app, store_type=None):
    """Register system routes on the provided Quart app"""
    app.add_url_rule('/api/health', 'health', health, methods=['GET'])
    app.add_url_rule('/api/ping', 'ping', ping, methods=['GET'])
    app.add_url_rule('/api/api_docs', 'api_docs', api_docs, methods=['GET'])