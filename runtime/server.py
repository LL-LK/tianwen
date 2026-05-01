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
from pathlib import Path
from functools import wraps
import psutil

# 添加runtime路径
sys.path.insert(0, str(Path(__file__).parent))

from quart import Quart, jsonify, request, render_template
from quart_cors import cors
import uuid
import json
from threading import Lock
from datetime import datetime

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("hermes_agi")

# 配置
DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
API_KEY = os.environ.get("API_KEY", "")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

app = Quart(__name__, template_folder="../web", static_folder="../web")

# 设置配置
app.config["PROVIDE_AUTOMATIC_OPTIONS"] = True
app.config["TEMPLATES_AUTO_RELOAD"] = DEBUG

# CORS配置：仅允许配置的域名
if CORS_ORIGINS:
    app = cors(app, allow_origin=CORS_ORIGINS.split(","))
else:
    # 非调试模式下默认关闭CORS
    if not DEBUG:
        app = cors(app, allow_origin=[])
    else:
        app = cors(app, allow_origin="*")

# 导入Agent
from main import HermesAGI, CognitiveEngine, PlanningEngine
from cycle_statistics_dashboard import CycleStatisticsDashboard
from reasoning_engine import ModelConfig
import httpx

# 全局Agent实例
agent = HermesAGI()
dashboard = CycleStatisticsDashboard()


def require_api_key(f):
    """API Key认证装饰器"""
    @wraps(f)
    async def decorated(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if DEBUG and not API_KEY:
            # 调试模式且未配置Key时跳过认证
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
    if not api_key or not group_id:
        return {"error": "MiniMax API key or Group ID not configured", "content": None}

    config = ModelConfig.minimax_api(api_key)
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
        content = result["choices"][0]["message"]["content"]
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    logger.info("=" * 50)
    logger.info("Hermes-AGI Web API Server")
    logger.info("=" * 50)
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"API Key configured: {'Yes' if API_KEY else 'No (auth disabled)'}")
    logger.info(f"CORS Origins: {CORS_ORIGINS or 'All (debug mode)'}")
    logger.info(f"Local:    http://localhost:{port}")
    logger.info(f"API Docs: http://localhost:{port}/api/health")
    logger.info("=" * 50)

    app.run(host="0.0.0.0", port=port, debug=DEBUG)