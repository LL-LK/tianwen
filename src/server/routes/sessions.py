"""
Session routes for Hermes-AGI
Extracted from server.py
"""
import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")


def register_sessions_routes(app, session_store, require_api_key):
    """Register session management routes"""

    @app.route("/api/sessions", methods=["GET"])
    @require_api_key
    async def list_sessions():
        """列出所有会话"""
        sessions = await session_store.all()
        user_id = request.args.get("user_id")
        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]
        return jsonify({"sessions": sessions, "total": len(sessions)})

    @app.route("/api/sessions/<session_id>", methods=["GET"])
    @require_api_key
    async def get_session(session_id):
        """通过ID获取会话"""
        session = await session_store.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        return jsonify(session)

    return app