"""
Hermes-AGI Server - Main Entry Point
A comprehensive astronomical observation AI system with autonomous research capabilities.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from functools import wraps
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hermes_agi")

# ============ Quart Application ============
from quart import Quart, jsonify, request, render_template, websocket

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
API_KEY = os.environ.get("API_KEY", "")

# Create Quart app
app = Quart(__name__, template_folder="templates", static_folder="static")

# ============ Import Submodules ============
from server.routes.health import register_health_routes
from server.routes.session_route import register_session_routes
from server.routes.stats import register_stats_routes
from server.routes.chat import register_chat_routes
from server.middleware.rate_limit import _check_rate_limit, require_api_key, setup_error_handlers
from server.middleware.cors import setup_cors, setup_cache_headers, setup_security_headers
from server.websocket.manager import ws_manager, HeartbeatConfig

# ============ Session Store ============
_session_store = None

class InMemorySessionStore:
    """简单的内存会话存储"""
    def __init__(self):
        self._store = {}
    
    @property
    def is_available(self):
        return True
    
    async def get(self, session_id: str):
        return self._store.get(session_id)
    
    async def set(self, session_id: str, session: dict):
        self._store[session_id] = session
    
    async def delete(self, session_id: str):
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False
    
    async def exists(self, session_id: str):
        return session_id in self._store
    
    async def all(self):
        return list(self._store.values())


def _init_session_store():
    """初始化会话存储"""
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis
            store = InMemorySessionStore()  # Fallback to in-memory for now
            logger.info("[Session] Using in-memory store (Redis not fully implemented)")
            return store
        except Exception as e:
            logger.warning(f"[Session] Redis unavailable: {e}")
            return InMemorySessionStore()
    else:
        logger.info("[Session] REDIS_URL not set, using in-memory store")
        return InMemorySessionStore()


_session_store = _init_session_store()

# ============ Observatory State ============
observatory_state = {"status": "initializing"}
dashboard_data = {"stats": {}}

# ============ Middleware Setup ============
setup_cors(app)
setup_cache_headers(app)
setup_security_headers(app)
setup_error_handlers(app)

# ============ Register Routes ============
# Health routes
register_health_routes(app, _session_store)

# Session routes
register_session_routes(app, _session_store, require_api_key)

# Stats routes
register_stats_routes(app, ws_manager, observatory_state, dashboard_data, require_api_key)

# Chat routes
register_chat_routes(app, _session_store, require_api_key, _check_rate_limit)

# ============ WebSocket Routes ============
@app.websocket("/ws/agent_status")
async def ws_agent_status():
    """WebSocket for agent status updates"""
    client_id = websocket.cookies.get("client_id", str(id(websocket)))
    user_id = websocket.args.get("user_id")
    
    await ws_manager.connect(client_id, websocket, user_id=user_id)
    
    try:
        await ws_manager.send_to_client(client_id, "connected", {"client_id": client_id})
        
        while True:
            data = await websocket.receive()
            if data:
                text = data.get("text")
                if text:
                    import json
                    msg = json.loads(text)
                    if msg.get("type") == "pong":
                        ws_manager.update_heartbeat(client_id)
                    elif msg.get("type") == "subscribe":
                        event_type = msg.get("event_type")
                        if event_type:
                            ws_manager.subscribe(client_id, event_type)
    except Exception as e:
        logger.error(f"[WS] Agent status error: {e}")
    finally:
        await ws_manager.disconnect(client_id)


@app.websocket("/ws/observation")
async def ws_observation():
    """WebSocket for observation updates"""
    client_id = websocket.cookies.get("client_id", str(id(websocket)))
    session_id = websocket.args.get("session_id")
    
    await ws_manager.connect(client_id, websocket, session_id=session_id)
    
    try:
        await ws_manager.send_to_client(client_id, "connected", {"client_id": client_id})
        
        while True:
            data = await websocket.receive()
            if data:
                text = data.get("text")
                if text:
                    import json
                    msg = json.loads(text)
                    if msg.get("type") == "pong":
                        ws_manager.update_heartbeat(client_id)
                    elif msg.get("type") == "subscribe":
                        event_type = msg.get("event_type")
                        if event_type:
                            ws_manager.subscribe(client_id, event_type)
    except Exception as e:
        logger.error(f"[WS] Observation error: {e}")
    finally:
        await ws_manager.disconnect(client_id)


# ============ Main Entry ============
def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hermes-AGI Server")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"), help="Host to bind")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)), help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Hermes-AGI Server on {args.host}:{args.port}")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug or DEBUG,
        use_reloader=args.reload,
    )


if __name__ == "__main__":
    main()
