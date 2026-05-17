"""
CORS and Cache Middleware
Extracted from server.py lines 48-98
"""

import logging
import hashlib
from quart import request

logger = logging.getLogger("hermes_agi")

# Re-export DEBUG and CORS_ORIGINS from server for import compatibility
DEBUG = None
CORS_ORIGINS = None


def _init_cors_config():
    """Lazy import of config to avoid circular imports"""
    global DEBUG, CORS_ORIGINS
    import os
    global DEBUG, CORS_ORIGINS
    DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")


async def add_cors_headers(response):
    """Add CORS headers, cache control, and gzip support to response"""
    global DEBUG, CORS_ORIGINS
    if DEBUG is None:
        _init_cors_config()

    # 生产环境CORS白名单控制
    origin = request.headers.get("Origin", "")
    if DEBUG or CORS_ORIGINS == "*":
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif CORS_ORIGINS and origin:
        allowed_origins = [o.strip() for o in CORS_ORIGINS.split(",")]
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Max-Age"] = "86400"

    # 缓存控制头
    path = request.path

    # 静态资源缓存策略
    if path.endswith(('.js', '.css', '.png', '.jpg', '.svg', '.ico')):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path == '/' or path.endswith('.html'):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    # API响应不缓存
    elif path.startswith('/api/'):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

    # 压缩支持
    if 'Content-Encoding' not in response.headers:
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' in accept_encoding and response.content_type and 'text' in response.content_type:
            response.headers["Content-Encoding"] = "gzip"

    return response


def _generate_etag(data: str) -> str:
    """Generate ETag for response caching"""
    return hashlib.md5(data.encode()).hexdigest()


async def add_cache_headers(response):
    """Add ETag headers for API response caching"""
    path = request.path
    if path.startswith('/api/') and request.method == 'GET':
        response_data = await response.get_data(as_text=True)
        if response_data:
            etag = _generate_etag(response_data)
            response.headers['ETag'] = f'"{etag}"'
            if_none_match = request.headers.get('If-None-Match', '')
            if if_none_match == f'"{etag}"':
                response.status_code = 304
                await response.set_data('')
    return response