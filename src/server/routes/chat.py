# chat.py - Chat routes extracted from server.py
# Functions: chat, safe_chat

import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")

# Global references (set by parent module)
agent = None
dashboard = None
hypothesis_tester = None
_enhancements = None


def init_chat_routes(a, d, h, e):
    """Initialize global references from parent module"""
    global agent, dashboard, hypothesis_tester, _enhancements
    agent = a
    dashboard = d
    hypothesis_tester = h
    _enhancements = e


# Import decorators and utilities from parent context
require_api_key = None
_call_minimax = None
_call_openai_compatible = None
_generate_local_response = None
_session_store = None
_check_rate_limit = None

from uuid import uuid4
from datetime import datetime


async def chat():
    """处理对话请求"""
    from quart import jsonify, request
    
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id")
    provider = data.get("provider", "minimax")
    provider_config = data.get("config", {})
    system_prompt = data.get("system_prompt", "")
    context = data.get("context", "")

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"error": "请求过于频繁，请稍后再试", "code": "RATE_LIMITED"}), 429

    session = await _session_store.get(session_id) if session_id else None
    if not session:
        session_id = str(uuid4())
        session = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
        }
    else:
        if not isinstance(session, dict):
            session = {"id": session_id, "created_at": datetime.now().isoformat(), "messages": []}

    session["messages"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat(),
    })

    try:
        llm_result = None
        provider_name = provider

        if provider == "minimax":
            llm_result = await _call_minimax(
                message,
                api_key=provider_config.get("api_key"),
                group_id=provider_config.get("group_id"),
                endpoint=provider_config.get("endpoint"),
                model=provider_config.get("model"),
                api_format=provider_config.get("api_format"),
                system_prompt=system_prompt,
            )
            provider_name = provider_config.get("model", "MiniMax")
        elif provider in ("qwen", "openai"):
            llm_result = await _call_openai_compatible(
                message,
                api_key=provider_config.get("api_key"),
                endpoint=provider_config.get("endpoint"),
                model=provider_config.get("model"),
                api_format=provider_config.get("api_format"),
                system_prompt=system_prompt,
            )
            provider_name = provider_config.get("model", provider)
        else:
            llm_result = await _call_minimax(message, system_prompt=system_prompt)
            provider_name = "MiniMax (env)"

        if llm_result.get("error"):
            local_result = _generate_local_response(message, system_prompt, context)
            if local_result:
                response_text = local_result["response"]
                note = local_result.get("note", "本地规则回复")
            else:
                response_text = f"我收到了你的消息：'{message[:50]}'。作为本地AI助手，我的功能有限。建议配置 LLM API（如MiniMax）以获得更智能的对话体验。你可以查看 /api/docs 了解系统所有功能。"
                note = "本地规则回复（无匹配规则）"
            response_data = {
                "session_id": session_id,
                "cognitive": {"intent": "chat", "entities": [], "skills": [], "complexity": "low"},
                "plan": {"task_id": str(uuid4()), "subtasks": [], "estimated_time": "0s", "risks": []},
                "output": response_text,
                "metrics": {"tokens_used": 0, "latency_ms": 0},
                "status": "local_response",
                "note": f"LLM API ({provider_name}) 未配置或不可用，使用本地规则回复: {note}",
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
                    "task_id": str(uuid4()),
                    "subtasks": [],
                    "estimated_time": "0s",
                    "risks": [],
                },
                "output": response_text,
                "metrics": {
                    "tokens_used": llm_result.get("tokens", 0),
                    "latency_ms": 0,
                    "provider": provider_name,
                },
                "status": "success",
            }

        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat(),
            "data": response_data,
        })

        await _session_store.set(session_id, session)

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "session_id": session_id,
        }), 500


async def safe_chat():
    """安全对话 - 带幻觉检测和事实校验的对话"""
    from quart import jsonify, request
    
    if not _enhancements:
        return jsonify({"error": "增强模块不可用"}), 503

    data = await request.get_json()
    message = data.get("message", "")
    context = data.get("context", "")
    expected_topics = data.get("expected_topics", None)

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    try:
        safe_result = await _enhancements.safe_chat_response(
            message, context, expected_topics
        )
        return jsonify(safe_result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def register_chat_routes(app):
    """Register chat routes with the Flask/Quart app"""
    from quart import Blueprint
    
    # Create blueprint for chat routes
    chat_bp = Blueprint("chat", __name__, url_prefix="/api")
    
    # Register route handlers
    chat_bp.route("/chat", methods=["POST"])(chat)
    chat_bp.route("/safe-chat", methods=["POST"])(safe_chat)
    
    # Register blueprint with app
    app.register_blueprint(chat_bp)
    
    logger.info("Chat routes registered successfully")