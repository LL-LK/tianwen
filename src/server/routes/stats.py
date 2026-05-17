"""
Statistics routes for Hermes-AGI
"""
import os
import asyncio
import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")


def register_stats_routes(app, ws_manager, observatory_state, dashboard_data, require_api_key):
    """Register statistics routes"""
    
    @app.route("/api/stats/dashboard", methods=["GET"])
    @require_api_key
    async def stats_dashboard():
        """统计仪表板数据"""
        try:
            stats = {
                "total_requests": 0,
                "active_connections": len(ws_manager.clients),
                "sessions": 0,
                "timestamp": None
            }
            
            if dashboard_data:
                stats.update(dashboard_data.get("stats", {}))
            
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Stats dashboard error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/stats/json", methods=["GET"])
    @require_api_key
    async def stats_json():
        """JSON格式统计数据"""
        try:
            stats = {
                "active_clients": len(ws_manager.clients),
                "subscriptions": {k: len(v) for k, v in ws_manager._subscriptions.items()},
                "dashboard": dashboard_data or {}
            }
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Stats JSON error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/stats/summary", methods=["GET"])
    @require_api_key
    async def stats_summary():
        """统计摘要"""
        try:
            summary = {
                "clients": ws_manager.list_clients(),
                "total_clients": len(ws_manager.clients),
                "active_subscriptions": list(ws_manager._subscriptions.keys())
            }
            return jsonify(summary)
        except Exception as e:
            logger.error(f"Stats summary error: {e}")
            return jsonify({"error": str(e)}), 500
    
    return app
