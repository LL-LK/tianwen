"""
Hermes-AGI Web API Server
为web/index.html提供后端API支持
"""

import asyncio
import sys
import psutil
import os
from pathlib import Path

# 添加runtime路径
sys.path.insert(0, str(Path(__file__).parent))

from quart import Quart, jsonify, request, render_template
from quart_cors import cors
import uuid
from datetime import datetime

app = Quart(__name__, template_folder="../web", static_folder="../web")
app = cors(app, allow_origin="*")

# 导入Agent
from main import HermesAGI, CognitiveEngine, PlanningEngine

# 全局Agent实例
agent = HermesAGI()

# 会话存储
sessions: dict = {}

@app.route("/")
async def index():
    """主页"""
    return await render_template("index.html")

@app.route("/api/chat", methods=["POST"])
async def chat():
    """处理对话请求"""
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
        # 处理消息 - 由于HermesAGI是同步的，我们需要用run_in_executor
        loop = asyncio.get_event_loop()
        result = await agent.process(message)

        # 准备响应
        response_data = {
            "session_id": session_id,
            "cognitive": {
                "intent": result.task_model.type.value,
                "entities": [
                    {"type": e.type, "value": e.value, "confidence": e.confidence}
                    for e in result.task_model.entities
                ],
                "skills": result.task_model.required_skills,
                "complexity": result.task_model.complexity,
            },
            "plan": {
                "task_id": result.plan.task_id,
                "subtasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "skill": t.skill,
                        "status": t.status.value,
                        "result": t.result,
                    }
                    for t in result.plan.subtasks
                ],
                "estimated_time": result.plan.estimated_time,
                "risks": result.plan.risks,
            },
            "output": result.output,
            "metrics": result.metrics,
            "status": result.status.value,
        }

        # 记录助手消息
        session["messages"].append({
            "role": "assistant",
            "content": result.output,
            "timestamp": datetime.now().isoformat(),
            "data": response_data,
        })

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

if __name__ == "__main__":
    print("=" * 50)
    print("Hermes-AGI Web API Server")
    print("=" * 50)
    print("Local:    http://localhost:5000")
    print("API Docs: http://localhost:5000/api/health")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)