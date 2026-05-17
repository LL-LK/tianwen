"""
API Key Authentication Decorator
Extracted from server.py lines 353-366
"""

import logging
import secrets
from functools import wraps
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")

API_KEY = None


def _init_auth_config():
    """Lazy import of config to avoid circular imports"""
    global API_KEY
    import os
    global API_KEY
    API_KEY = os.environ.get("API_KEY", "")


def require_api_key(f):
    """Decorator to require API key authentication for endpoints"""
    @wraps(f)
    async def decorated(*args, **kwargs):
        global API_KEY
        if API_KEY is None:
            _init_auth_config()

        provided_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        # 开发模式：API_KEY未配置时跳过认证
        if not API_KEY:
            logger.warning("[SECURITY] API_KEY not configured, skipping authentication (development mode)")
            return await f(*args, **kwargs)
        if not provided_key:
            return jsonify({"error": "API Key required", "code": "MISSING_KEY"}), 401
        if not secrets.compare_digest(provided_key, API_KEY):
            return jsonify({"error": "Invalid API Key", "code": "INVALID_KEY"}), 403
        return await f(*args, **kwargs)
    return decorated