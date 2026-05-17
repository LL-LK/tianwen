"""
Security Headers and Error Handlers
Extracted from server.py lines 312-350
"""

import logging
import traceback
from quart import jsonify

logger = logging.getLogger("hermes_agi")

DEBUG = None


def _init_security_config():
    """Lazy import of config to avoid circular imports"""
    global DEBUG
    import os
    global DEBUG
    DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")


async def bad_request(e):
    """Handle 400 Bad Request errors"""
    return jsonify({"error": "请求参数无效", "code": "BAD_REQUEST"}), 400


async def not_found(e):
    """Handle 404 Not Found errors"""
    return jsonify({"error": "资源不存在", "code": "NOT_FOUND"}), 404


async def method_not_allowed(e):
    """Handle 405 Method Not Allowed errors"""
    return jsonify({"error": "不支持的请求方法", "code": "METHOD_NOT_ALLOWED"}), 405


async def internal_error(e):
    """Handle 500 Internal Server errors"""
    global DEBUG
    if DEBUG is None:
        _init_security_config()

    # 生产环境：记录详细错误但返回通用消息
    error_trace = traceback.format_exc()
    logger.error(f"Internal server error: {error_trace}")
    if DEBUG:
        return jsonify({
            "error": "服务器内部错误",
            "code": "INTERNAL_ERROR",
            "detail": error_trace
        }), 500
    return jsonify({"error": "服务器内部错误", "code": "INTERNAL_ERROR"}), 500


async def add_security_headers(response):
    """Add security headers to all responses"""
    global DEBUG
    if DEBUG is None:
        _init_security_config()

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response