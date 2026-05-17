# websocket.py - WebSocket management routes extracted from server.py
# Functions: ws_clients_list, ws_client_info, ws_config

import logging
from quart import jsonify

logger = logging.getLogger("hermes_agi")

# Global reference
ws_manager = None
HeartbeatConfig = None
_REALTIME_BRIDGE_AVAILABLE = False


def init_websocket_routes(wsm, hc, rtb):
    """Initialize global references from parent module"""
    global ws_manager, HeartbeatConfig, _REALTIME_BRIDGE_AVAILABLE
    ws_manager = wsm
    HeartbeatConfig = hc
    _REALTIME_BRIDGE_AVAILABLE = rtb


async def ws_clients_list():
    """获取所有WebSocket客户端信息"""
    stats = ws_manager.get_connection_stats()

    clients = []
    for cid in list(ws_manager._connections.keys()):
        info = ws_manager.get_client_info(cid)
        if info:
            clients.append(info)

    return jsonify({
        "stats": stats,
        "clients": clients
    })


async def ws_client_info(client_id):
    """获取指定WebSocket客户端信息"""
    info = ws_manager.get_client_info(client_id)
    if not info:
        return jsonify({"error": "Client not found"}), 404

    return jsonify(info)


async def ws_config():
    """获取WebSocket配置信息"""
    return jsonify({
        "heartbeat_interval": HeartbeatConfig.HEARTBEAT_INTERVAL,
        "heartbeat_timeout": HeartbeatConfig.HEARTBEAT_TIMEOUT,
        "reconnect_delay": HeartbeatConfig.RECONNECT_DELAY,
        "max_reconnect_attempts": HeartbeatConfig.MAX_RECONNECT_ATTEMPTS,
        "realtime_bridge_available": _REALTIME_BRIDGE_AVAILABLE
    })


def register_websocket_routes(app):
    """Register WebSocket management routes on the given Quart app"""
    @app.route("/ws/clients", methods=["GET"])
    async def ws_clients_list_route():
        return await ws_clients_list()

    @app.route("/ws/clients/<client_id>", methods=["GET"])
    async def ws_client_info_route(client_id):
        return await ws_client_info(client_id)

    @app.route("/ws/config", methods=["GET"])
    async def ws_config_route():
        return await ws_config()