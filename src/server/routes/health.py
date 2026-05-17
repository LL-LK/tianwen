"""
Health check routes for Hermes-AGI
"""
import os
import asyncio
import logging
from quart import jsonify

logger = logging.getLogger("hermes_agi")

# Lazy imports for circular dependency resolution
_http_client = None

def _get_http_client():
    global _http_client
    if _http_client is None:
        import httpx
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _http_client


def register_health_routes(app, session_store=None, agent=None):
    """Register health check routes"""
    
    @app.route("/api/health", methods=["GET"])
    async def health_check():
        """健康检查"""
        try:
            status = {
                "status": "healthy",
                "version": "2.4.0",
                "service": "Hermes-AGI"
            }
            
            # 检查会话存储
            if session_store:
                try:
                    if hasattr(session_store, 'is_available') and session_store.is_available:
                        status["session_store"] = "redis"
                    elif hasattr(session_store, '_store'):
                        status["session_store"] = "in-memory"
                    else:
                        status["session_store"] = "unknown"
                except Exception as e:
                    status["session_store"] = f"error: {str(e)}"
            
            # 检查API密钥
            status["api_key_configured"] = bool(os.environ.get("API_KEY"))
            status["minimax_configured"] = bool(os.environ.get("MINIMAX_API_KEY"))
            
            # 检查外部依赖
            try:
                client = _get_http_client()
                response = await client.get("https://api.minimax.chat")
                status["minimax_api"] = "reachable" if response.status_code else "error"
            except Exception:
                status["minimax_api"] = "unreachable"
            
            return jsonify(status)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500
    
    @app.route("/api/ping", methods=["GET"])
    async def ping():
        """轻量级Ping检查"""
        return jsonify({"pong": True})
    
    return app
