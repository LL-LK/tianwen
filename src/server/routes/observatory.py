"""
Observatory routes for Hermes-AGI
Extracted from server.py
"""
import logging
import uuid
from quart import jsonify, request
from datetime import datetime

logger = logging.getLogger("hermes_agi")


def register_observatory_routes(app, observatory_state, ws_manager, log_entries, state_bridge=None, conn_manager=None):
    """Register observatory control routes"""

    def _build_observatory_status():
        """构建观测站状态数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "status": observatory_state.get("status", "idle"),
            "current_target": observatory_state.get("current_target", {}),
            "devices": observatory_state.get("devices", {}),
            "queue_size": len(observatory_state.get("queue", [])),
            "weather": observatory_state.get("devices", {}).get("weather", {}),
        }

    @app.route("/api/observatory/status", methods=["GET"])
    async def observatory_status():
        """获取观测站状态"""
        return jsonify(_build_observatory_status())

    @app.route("/api/observatory/queue", methods=["GET"])
    async def observatory_queue():
        """获取观测队列"""
        return jsonify({"queue": observatory_state["queue"]})

    @app.route("/api/observatory/queue", methods=["POST"])
    async def observatory_queue_add():
        """添加观测队列项"""
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
        observatory_state["queue"].append(new_item)
        await ws_manager.broadcast({"type": "queue_update", "data": observatory_state["queue"]})
        return jsonify({"success": True, "item": new_item})

    @app.route("/api/observatory/queue/<item_id>", methods=["DELETE"])
    async def observatory_queue_remove(item_id):
        """移除观测队列项"""
        observatory_state["queue"] = [q for q in observatory_state["queue"] if q["id"] != item_id]
        await ws_manager.broadcast({"type": "queue_update", "data": observatory_state["queue"]})
        return jsonify({"success": True})

    @app.route("/api/observatory/control", methods=["POST"])
    async def observatory_control():
        """控制观测站"""
        data = await request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        action = data.get("action", "")
        valid_actions = ["start", "stop", "pause", "resume"]
        if action not in valid_actions:
            return jsonify({"error": f"无效操作: {action}，支持: {valid_actions}"}), 400

        status_map = {"start": "observing", "stop": "idle", "pause": "paused", "resume": "observing"}
        new_status = status_map[action]
        observatory_state["status"] = new_status
        log_entries.insert(0, {
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": "SYSTEM",
            "message": f"观测站状态变更: {action}"
        })

        realtime_bridge_available = state_bridge is not None and conn_manager is not None

        if realtime_bridge_available:
            state_bridge.update_status(new_status)
            await conn_manager.broadcast({
                "type": "status_update",
                "data": _build_observatory_status(),
            })
        else:
            await ws_manager.broadcast({
                "type": "status_update",
                "data": _build_observatory_status(),
            })
        return jsonify({"success": True, "status": new_status})

    return app