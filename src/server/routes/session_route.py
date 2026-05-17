"""
Session routes for Hermes-AGI
"""
import os
import asyncio
import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")


def register_session_routes(app, session_store, require_api_key):
    """Register session management routes"""
    
    @app.route("/api/session", methods=["GET"])
    @require_api_key
    async def get_session():
        """获取当前会话"""
        session_id = request.args.get("session_id")
        if not session_id:
            return jsonify({"error": "session_id required"}), 400
        
        session = await session_store.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify(session)
    
    @app.route("/api/session", methods=["POST"])
    @require_api_key
    async def create_session():
        """创建新会话"""
        data = await request.get_json() or {}
        session_id = data.get("session_id")
        user_id = data.get("user_id", "default")
        
        if not session_id:
            return jsonify({"error": "session_id required"}), 400
        
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "messages": [],
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", "")
        }
        
        await session_store.set(session_id, session)
        return jsonify(session), 201
    
    @app.route("/api/sessions", methods=["GET"])
    @require_api_key
    async def list_sessions():
        """列出所有会话"""
        sessions = await session_store.all()
        
        # 过滤条件
        user_id = request.args.get("user_id")
        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]
        
        return jsonify({
            "sessions": sessions,
            "total": len(sessions)
        })
    
    @app.route("/api/session/<session_id>", methods=["GET"])
    @require_api_key
    async def get_session_by_id(session_id):
        """通过ID获取会话"""
        session = await session_store.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        return jsonify(session)
    
    @app.route("/api/session/<session_id>", methods=["DELETE"])
    @require_api_key
    async def delete_session(session_id):
        """删除会话"""
        deleted = await session_store.delete(session_id)
        if not deleted:
            return jsonify({"error": "Session not found"}), 404
        return jsonify({"success": True, "session_id": session_id})
    
    return app
