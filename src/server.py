"""
Hermes-AGI Web API Server
为web/index.html提供后端API支持

安全配置:
- DEBUG: 环境变量控制，默认false
- API_KEY: API认证密钥
- CORS_ORIGINS: 允许的跨域域名（逗号分隔）
"""

import asyncio
import sys
import os
import secrets
import logging
import traceback
import hashlib
from pathlib import Path
from functools import wraps
import psutil
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from quart import Quart, jsonify, request, render_template, websocket
import uuid
import json
import time
import random
from threading import Lock
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("hermes_agi")

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
API_KEY = os.environ.get("API_KEY", "")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

app = Quart(__name__, template_folder="../web", static_folder="../web")
app.config["PROVIDE_AUTOMATIC_OPTIONS"] = True
app.config["TEMPLATES_AUTO_RELOAD"] = DEBUG

@app.after_request
async def add_cors_headers(response):
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

_response_cache: Dict[str, tuple] = {}
_CACHE_MAX_SIZE = 50

def _cache_key(path: str, query_string: str = "") -> str:
    return f"{path}?{query_string}"

def _set_response_cache(key: str, data: str, ttl: int = 5):
    if len(_response_cache) >= _CACHE_MAX_SIZE:
        oldest = min(_response_cache.keys(), key=lambda k: _response_cache[k][1])
        del _response_cache[oldest]
    _response_cache[key] = (data, time.time() + ttl)

def _get_response_cache(key: str) -> Optional[str]:
    entry = _response_cache.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    if entry:
        del _response_cache[key]
    return None

def _generate_etag(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()

@app.after_request
async def add_cache_headers(response):
    path = request.path
    if path.startswith('/api/') and request.method == 'GET':
        response_data = response.get_data(as_text=True)
        if response_data:
            etag = _generate_etag(response_data)
            response.headers['ETag'] = f'"{etag}"'
            if_none_match = request.headers.get('If-None-Match', '')
            if if_none_match == f'"{etag}"':
                response.status_code = 304
                response.set_data('')
    return response

from main import HermesAGI
from core.cognitive import CognitiveEngine, PlanningEngine
from web.dashboard import CycleStatisticsDashboard
from research.hypothesis_tester import HypothesisTester
import httpx

agent = HermesAGI()
dashboard = CycleStatisticsDashboard()
hypothesis_tester = HypothesisTester()

_http_client: httpx.AsyncClient = None

def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _http_client

RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", 60))
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 30))
_rate_limit_store: dict = defaultdict(list)


# ============ Redis Session 存储 (安全修复) ============
# 问题: database.type: in-memory，重启数据丢失，多实例不同步
# 修复: 添加Redis Session持久化支持，通过环境变量REDIS_URL配置

class RedisSessionStore:
    """Redis会话存储，支持持久化和多实例共享"""

    def __init__(self, redis_url: str, ttl: int = 3600):
        self.redis_url = redis_url
        self.ttl = ttl
        self._redis = None
        self._connected = False
        self._connect()

    def _connect(self):
        """建立Redis连接"""
        try:
            import redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            self._redis.ping()
            self._connected = True
            logger.info(f"[Session] Redis connected: {self.redis_url}")
        except ImportError:
            self._connected = False
            self._redis = None
            logger.warning("[Session] redis package not installed, using in-memory store")
        except Exception as e:
            self._connected = False
            self._redis = None
            logger.warning(f"[Session] Redis connection failed, using in-memory store: {e}")

    @property
    def is_available(self) -> bool:
        """检查Redis是否可用"""
        if not self._redis:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            self._connected = False
            return False

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        if not self.is_available:
            return None
        try:
            data = self._redis.get(f"session:{session_id}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"[Session] Redis get failed: {e}")
            return None

    async def set(self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """保存会话"""
        if not self.is_available:
            return False
        try:
            expire = ttl if ttl is not None else self.ttl
            self._redis.setex(f"session:{session_id}", expire, json.dumps(data, ensure_ascii=False, default=str))
            return True
        except Exception as e:
            logger.error(f"[Session] Redis set failed: {e}")
            return False

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        if not self.is_available:
            return False
        try:
            self._redis.delete(f"session:{session_id}")
            return True
        except Exception as e:
            logger.error(f"[Session] Redis delete failed: {e}")
            return False

    async def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        if not self.is_available:
            return False
        try:
            return bool(self._redis.exists(f"session:{session_id}"))
        except Exception:
            return False

    async def all(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话"""
        if not self.is_available:
            return {}
        try:
            keys = self._redis.keys("session:*")
            result = {}
            for key in keys:
                data = self._redis.get(key)
                if data:
                    session_id = key.replace("session:", "")
                    result[session_id] = json.loads(data)
            return result
        except Exception as e:
            logger.error(f"[Session] Redis all failed: {e}")
            return {}


class InMemorySessionStore:
    """内存会话存储（回退方案）"""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(session_id)

    async def set(self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        self._store[session_id] = data
        return True

    async def delete(self, session_id: str) -> bool:
        self._store.pop(session_id, None)
        return True

    async def exists(self, session_id: str) -> bool:
        return session_id in self._store

    async def all(self) -> Dict[str, Dict[str, Any]]:
        return self._store.copy()


# 初始化Session存储
def _init_session_store():
    """根据环境变量初始化会话存储"""
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        store = RedisSessionStore(redis_url)
        if store.is_available:
            logger.info("[Session] Using Redis session store")
            return store
        else:
            logger.warning("[Session] Redis unavailable, falling back to in-memory store")
            return InMemorySessionStore()
    else:
        logger.info("[Session] REDIS_URL not set, using in-memory store")
        return InMemorySessionStore()


_session_store = _init_session_store()
_session_store_type = "redis" if isinstance(_session_store, RedisSessionStore) and _session_store.is_available else "in-memory"


def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    _rate_limit_store[client_ip].append(now)
    return True


def _validate_required_fields(data: dict, required: list[str]) -> str | None:
    for field in required:
        if not data.get(field):
            return f"缺少必填字段: {field}"
    return None


def _sanitize_str(value: str, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_len]


@app.errorhandler(400)
async def bad_request(e):
    return jsonify({"error": "请求参数无效", "code": "BAD_REQUEST"}), 400


@app.errorhandler(404)
async def not_found(e):
    return jsonify({"error": "资源不存在", "code": "NOT_FOUND"}), 404


@app.errorhandler(405)
async def method_not_allowed(e):
    return jsonify({"error": "不支持的请求方法", "code": "METHOD_NOT_ALLOWED"}), 405


@app.errorhandler(500)
async def internal_error(e):
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


@app.after_request
async def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def require_api_key(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
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


async def call_minimax(message: str, api_key: str = None, group_id: str = None, endpoint: str = None, model: str = None, api_format: str = None) -> dict:
    """调用MiniMax API，支持原生格式和OpenAI兼容格式"""
    group_id = group_id or os.environ.get("MINIMAX_GROUP_ID")
    api_key = api_key or os.environ.get("MINIMAX_API_KEY")
    model = model or os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")
    endpoint = endpoint or "https://api.minimax.chat/v1"
    api_format = api_format or "native"

    if not api_key or not group_id:
        logger.error(f"[MiniMax] 配置缺失: api_key={'***' if api_key else 'None'}, group_id={'***' if group_id else 'None'}")
        return {"error": "MiniMax API key 或 Group ID 未配置", "content": None}

    endpoint = endpoint.rstrip("/")
    client = _get_http_client()

    try:
        if api_format == "openai":
            url = f"{endpoint}/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 2000,
                "temperature": 0.7,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        else:
            url = f"{endpoint}/text/chatcompletion_v2"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 2000,
                "temperature": 0.7,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "GroupId": group_id,
            }

        logger.info(f"[MiniMax] 请求: endpoint={endpoint}, model={model}, format={api_format}")
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"[MiniMax] HTTP {response.status_code}: {error_detail}")
            return {"error": f"MiniMax API 返回错误 ({response.status_code}): {error_detail}", "content": None}

        result = response.json()
        logger.info(f"[MiniMax] 响应: {json.dumps(result, ensure_ascii=False)[:300]}")

        if api_format == "openai":
            choices = result.get("choices", [])
            if not choices:
                return {"error": "MiniMax OpenAI格式响应无choices", "content": None}
            content = choices[0].get("message", {}).get("content")
            tokens = result.get("usage", {}).get("total_tokens", 0)
        else:
            choices = result.get("choices", [])
            if not choices:
                return {"error": "MiniMax 原生格式响应无choices", "content": None}
            content = choices[0].get("message", {}).get("content")
            tokens = result.get("usage", {}).get("total_tokens", 0)

        if content is None:
            logger.error(f"[MiniMax] content为None, 完整响应: {json.dumps(result, ensure_ascii=False)[:500]}")
            return {"error": "MiniMax 返回内容为空", "content": None}

        logger.info(f"[MiniMax] 成功: tokens={tokens}, content_len={len(content)}")
        return {"content": content, "tokens": tokens}

    except httpx.TimeoutException:
        logger.error(f"[MiniMax] 请求超时: {endpoint}")
        return {"error": "MiniMax API 请求超时(60s)", "content": None}
    except httpx.ConnectError as e:
        logger.error(f"[MiniMax] 连接失败: {endpoint} - {e}")
        return {"error": f"无法连接到 MiniMax API: {endpoint}", "content": None}
    except Exception as e:
        logger.error(f"[MiniMax] 异常: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return {"error": f"MiniMax调用异常: {type(e).__name__}: {str(e)}", "content": None}


async def call_openai_compatible(message: str, api_key: str, endpoint: str, model: str, api_format: str = None) -> dict:
    """调用OpenAI兼容格式的API (Qwen, OpenAI, 本地部署等)，支持Anthropic格式"""
    if not api_key or not endpoint or not model:
        logger.error(f"[LLM] 配置缺失: api_key={'***' if api_key else 'None'}, endpoint={endpoint}, model={model}")
        return {"error": "API key, endpoint, or model not configured", "content": None}

    api_format = api_format or "openai"
    endpoint = endpoint.rstrip("/")
    client = _get_http_client()

    try:
        if api_format == "anthropic":
            url = f"{endpoint}/v1/messages"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 2000,
                "temperature": 0.7,
            }
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
        else:
            url = f"{endpoint}/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 2000,
                "temperature": 0.7,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

        logger.info(f"[LLM] 请求: endpoint={endpoint}, model={model}, format={api_format}")
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"[LLM] HTTP {response.status_code}: {error_detail}")
            return {"error": f"API 返回错误 ({response.status_code}): {error_detail}", "content": None}

        result = response.json()
        logger.info(f"[LLM] 响应: {json.dumps(result, ensure_ascii=False)[:300]}")

        if api_format == "anthropic":
            content = result.get("content", [{}])[0].get("text") if result.get("content") else None
            input_tokens = result.get("usage", {}).get("input_tokens", 0)
            output_tokens = result.get("usage", {}).get("output_tokens", 0)
            tokens = input_tokens + output_tokens
        else:
            choices = result.get("choices", [])
            if not choices:
                return {"error": "API响应无choices", "content": None}
            content = choices[0].get("message", {}).get("content")
            tokens = result.get("usage", {}).get("total_tokens", 0)

        if content is None:
            logger.error(f"[LLM] content为None, 完整响应: {json.dumps(result, ensure_ascii=False)[:500]}")
            return {"error": "API 返回内容为空", "content": None}

        logger.info(f"[LLM] 成功: tokens={tokens}, content_len={len(content)}")
        return {"content": content, "tokens": tokens, "provider": model}

    except httpx.TimeoutException:
        logger.error(f"[LLM] 请求超时: {endpoint}")
        return {"error": "API 请求超时(60s)", "content": None}
    except httpx.ConnectError as e:
        logger.error(f"[LLM] 连接失败: {endpoint} - {e}")
        return {"error": f"无法连接到 API: {endpoint}", "content": None}
    except Exception as e:
        logger.error(f"[LLM] 异常: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return {"error": f"API调用异常: {type(e).__name__}: {str(e)}", "content": None}

# 会话存储
sessions: dict = {}
sessions_lock = Lock()
SESSIONS_FILE = Path(__file__).parent / "sessions.json"


def load_sessions():
    """从文件加载会话"""
    global sessions
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
            logger.info(f"Loaded {len(sessions)} sessions from disk")
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            sessions = {}


def save_sessions():
    """将会话保存到文件"""
    with sessions_lock:
        try:
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")


def cleanup_old_sessions(max_age_days: int = 30):
    """清理超过最大年龄的会话"""
    cutoff = datetime.now().timestamp() - (max_age_days * 86400)
    removed = 0
    for sid in list(sessions.keys()):
        try:
            created = datetime.fromisoformat(sessions[sid].get("created_at", "2000-01-01"))
            if created.timestamp() < cutoff:
                del sessions[sid]
                removed += 1
        except Exception:
            pass
    if removed > 0:
        logger.info(f"Cleaned up {removed} old sessions")
        save_sessions()


# 启动时加载会话
load_sessions()
cleanup_old_sessions()

@app.route("/")
async def index():
    """主页"""
    return await render_template("index.html")

@app.route("/api/chat", methods=["POST"])
@require_api_key
async def chat():
    """处理对话请求"""
    data = await request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id")
    provider = data.get("provider", "minimax")
    provider_config = data.get("config", {})

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"error": "请求过于频繁，请稍后再试", "code": "RATE_LIMITED"}), 429

    session = await _session_store.get(session_id) if session_id else None
    if not session:
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
        }
    else:
        if not isinstance(session, dict):
            session = {"id": session_id, "created_at": datetime.now().isoformat(), "messages": []}

    session["messages"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat(),
    })

    try:
        llm_result = None
        provider_name = provider

        if provider == "minimax":
            llm_result = await call_minimax(
                message,
                api_key=provider_config.get("api_key"),
                group_id=provider_config.get("group_id"),
                endpoint=provider_config.get("endpoint"),
                model=provider_config.get("model"),
                api_format=provider_config.get("api_format"),
            )
            provider_name = provider_config.get("model", "MiniMax")
        elif provider in ("qwen", "openai"):
            llm_result = await call_openai_compatible(
                message,
                api_key=provider_config.get("api_key"),
                endpoint=provider_config.get("endpoint"),
                model=provider_config.get("model"),
                api_format=provider_config.get("api_format"),
            )
            provider_name = provider_config.get("model", provider)
        else:
            llm_result = await call_minimax(message)
            provider_name = "MiniMax (env)"

        if llm_result.get("error"):
            response_text = _generate_local_response(message)
            response_data = {
                "session_id": session_id,
                "cognitive": {"intent": "chat", "entities": [], "skills": [], "complexity": "low"},
                "plan": {"task_id": str(uuid.uuid4()), "subtasks": [], "estimated_time": "0s", "risks": []},
                "output": response_text,
                "metrics": {"tokens_used": 0, "latency_ms": 0},
                "status": "local_response",
                "note": f"LLM API ({provider_name}) 未配置或不可用，使用本地规则回复",
            }
        else:
            response_text = llm_result["content"]
            response_data = {
                "session_id": session_id,
                "cognitive": {
                    "intent": "chat",
                    "entities": [],
                    "skills": [],
                    "complexity": "low",
                },
                "plan": {
                    "task_id": str(uuid.uuid4()),
                    "subtasks": [],
                    "estimated_time": "0s",
                    "risks": [],
                },
                "output": response_text,
                "metrics": {
                    "tokens_used": llm_result.get("tokens", 0),
                    "latency_ms": 0,
                    "provider": provider_name,
                },
                "status": "success",
            }

        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat(),
            "data": response_data,
        })

        await _session_store.set(session_id, session)

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "session_id": session_id,
        }), 500


@app.route("/api/llm/test", methods=["POST"])
@require_api_key
async def test_llm_connectivity():
    """测试LLM API连通性"""
    data = await request.get_json()
    provider = data.get("provider", "minimax")
    config = data.get("config", {})

    result = {
        "provider": provider,
        "status": "unknown",
        "latency_ms": 0,
        "error": None,
        "details": {},
    }

    start = time.time()

    try:
        if provider == "minimax":
            llm_result = await call_minimax(
                "Hello, this is a connectivity test. Please reply with 'OK'.",
                api_key=config.get("api_key"),
                group_id=config.get("group_id"),
                endpoint=config.get("endpoint"),
                model=config.get("model"),
                api_format=config.get("api_format"),
            )
        else:
            llm_result = await call_openai_compatible(
                "Hello, this is a connectivity test. Please reply with 'OK'.",
                api_key=config.get("api_key"),
                endpoint=config.get("endpoint"),
                model=config.get("model"),
                api_format=config.get("api_format"),
            )

        result["latency_ms"] = round((time.time() - start) * 1000)

        if llm_result.get("error"):
            result["status"] = "error"
            result["error"] = llm_result["error"]
        else:
            result["status"] = "success"
            result["details"] = {
                "content_preview": llm_result.get("content", "")[:100],
                "tokens": llm_result.get("tokens", 0),
            }

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["latency_ms"] = round((time.time() - start) * 1000)

    return jsonify(result)


def _generate_local_response(message: str) -> str:
    """本地规则回复生成器"""
    msg_lower = message.lower()
    
    if any(word in msg_lower for word in ["你好", "hello", "hi", "介绍"]):
        return "你好！我是天问-AGI全自动天文观测站AI助手。我可以帮助你：\n1. 查询天体信息（如M31、NGC224等）\n2. 控制望远镜进行观测\n3. 生成和验证科学假说\n4. 挖掘天文数据\n5. 获取实时星图\n\n请告诉我你需要什么帮助？"
    
    if any(word in msg_lower for word in ["m31", "仙女座", "andromeda"]):
        return "M31（仙女座星系）是距离银河系最近的大型星系，距离约250万光年。它是本星系群中最大的星系之一，包含约1万亿颗恒星。你可以使用 /api/skychart?target=M31 获取它的星图。"
    
    if any(word in msg_lower for word in ["望远镜", "telescope"]):
        return "系统支持望远镜控制功能。当前使用模拟器进行演示，真实望远镜需要配置Seestar S50连接。你可以通过 /api/telescope/status 查看望远镜状态。"
    
    if any(word in msg_lower for word in ["假说", "hypothesis"]):
        return "系统支持科学假说生成和验证。你可以使用 /api/hypothesis/generate 生成假说，使用 /api/hypothesis/test 进行验证。验证需要提供真实观测数据和文献证据。"
    
    if any(word in msg_lower for word in ["数据", "data", "挖掘", "miner"]):
        return "系统内置数据挖掘功能，可以从天文数据中发现模式、提取特征、检测异常。使用 /api/data/miner?target=目标名称 进行查询。"
    
    if any(word in msg_lower for word in ["帮助", "help", "怎么用", "功能"]):
        return "天问-AGI主要功能：\n- 星图查询：GET /api/skychart?target=M31\n- 望远镜控制：GET /api/telescope/status\n- 假说生成：POST /api/hypothesis/generate\n- 假说验证：POST /api/hypothesis/test\n- 数据挖掘：GET /api/data/miner?target=目标\n- 观测数据：GET /api/observation/data\n- 完整文档：GET /api/docs"
    
    return f"我收到了你的消息：'{message[:50]}'。作为本地AI助手，我的功能有限。建议配置 LLM API（如MiniMax）以获得更智能的对话体验。你可以查看 /api/docs 了解系统所有功能。"

@app.route("/api/cognitive", methods=["POST"])
async def cognitive_preview():
    """认知引擎预览 - 不执行，只分析用户输入"""
    data = await request.get_json()
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    cognitive = CognitiveEngine()
    task_model = cognitive.process(message)

    return jsonify({
        "intent": task_model.type.value,
        "entities": [
            {"type": e.type, "value": e.value, "confidence": e.confidence}
            for e in task_model.entities
        ],
        "required_skills": task_model.required_skills,
        "complexity": task_model.complexity,
        "description": task_model.description,
    })

@app.route("/api/sessions", methods=["GET"])
async def list_sessions():
    """获取所有会话"""
    all_sessions = await _session_store.all()
    return jsonify({
        "sessions": [
            {
                "id": s["id"],
                "created_at": s.get("created_at", ""),
                "message_count": len(s.get("messages", [])),
            }
            for s in all_sessions.values()
        ]
    })

@app.route("/api/sessions/<session_id>", methods=["GET"])
async def get_session(session_id):
    """获取指定会话"""
    session = await _session_store.get(session_id)
    if not session:
        return jsonify({"error": "会话不存在"}), 404

    return jsonify(session)

@app.route("/api/evolution/stats", methods=["GET"])
async def evolution_stats():
    """获取进化系统统计"""
    stats = agent.evolution.get_stats()
    return jsonify(stats)

@app.route("/api/health", methods=["GET"])
async def health():
    """健康检查"""
    if DEBUG:
        health_data = {
            "status": "ok",
            "version": "2.3.0",
            "build_id": "trae-perf-20260504",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "memory": {
                    "total_mb": psutil.virtual_memory().total / (1024 * 1024),
                    "available_mb": psutil.virtual_memory().available / (1024 * 1024),
                    "percent": psutil.virtual_memory().percent,
                },
                "cpu": {
                    "count": psutil.cpu_count(),
                    "percent": psutil.cpu_percent(interval=0.1),
                },
                "process": {
                    "pid": os.getpid(),
                    "threads": psutil.Process().num_threads(),
                    "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024),
                }
            },
            "dependencies": {
                "agent_initialized": agent is not None,
                "cognitive_engine": agent.cognitive is not None if agent else False,
                "planning_engine": agent.planning is not None if agent else False,
                "execution_engine": agent.execution is not None if agent else False,
                "evolution_system": agent.evolution is not None if agent else False,
            },
            "sessions": {
                "active_count": len(sessions),
            },
            "database": {
                "type": _session_store_type,
                "status": "connected",
                "sessions_count": len(sessions),
            },
            "external_apis": {
                "minimax_configured": bool(os.environ.get("MINIMAX_API_KEY") and os.environ.get("MINIMAX_GROUP_ID")),
                "deepseek_configured": bool(os.environ.get("DEEPSEEK_API_KEY")),
            }
        }
        if psutil.virtual_memory().percent > 90 or psutil.cpu_percent(interval=0.1) > 95:
            health_data["status"] = "degraded"
    else:
        health_data = {
            "status": "ok",
            "version": "2.3.0",
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                "agent_initialized": agent is not None,
                "cognitive_engine": agent.cognitive is not None if agent else False,
                "planning_engine": agent.planning is not None if agent else False,
                "execution_engine": agent.execution is not None if agent else False,
                "evolution_system": agent.evolution is not None if agent else False,
            },
            "sessions": {
                "active_count": len(sessions),
            },
            "database": {
                "type": _session_store_type,
                "status": "connected",
            }
        }

    if not all(health_data["dependencies"].values()):
        health_data["status"] = "degraded"

    return jsonify(health_data)


@app.route("/api/ping", methods=["GET"])
async def ping():
    """轻量级连通性检测（无系统信息采集，极快响应）"""
    return jsonify({"status": "ok", "version": "2.3.0", "timestamp": datetime.now().isoformat()})

@app.route("/api/stats/dashboard", methods=["GET"])
async def stats_dashboard():
    """返回HTML统计面板"""
    html = dashboard.get_html_dashboard()
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/api/stats/json", methods=["GET"])
async def stats_json():
    """返回JSON格式的统计"""
    stats = dashboard.get_summary_stats()
    return jsonify(stats)

# ============ WebSocket 连接管理 (增强版 - 心跳检测) ============

class HeartbeatConfig:
    """心跳检测配置"""
    HEARTBEAT_INTERVAL = 30  # 发送心跳间隔(秒)
    HEARTBEAT_TIMEOUT = 60   # 心跳超时时间(秒)
    RECONNECT_DELAY = 3       # 重连延迟(秒)
    MAX_RECONNECT_ATTEMPTS = 10  # 最大重连次数


class WebSocketClient:
    """单个WebSocket客户端状态"""
    def __init__(self, client_id: str, ws):
        self.client_id = client_id
        self.ws = ws
        self.last_heartbeat = time.time()
        self.last_message = time.time()
        self.reconnect_attempts = 0
        self.is_alive = True

    def update_heartbeat(self):
        """更新心跳时间戳"""
        self.last_heartbeat = time.time()
        self.last_message = time.time()
        self.is_alive = True

    def check_timeout(self, timeout: float) -> bool:
        """检查是否超时"""
        return (time.time() - self.last_heartbeat) > timeout


class WebSocketManager:
    """WebSocket 连接管理器 (增强版 - 心跳检测与断线重连)"""

    def __init__(self):
        self._connections: dict = {}
        self._lock = Lock()
        self._heartbeat_task = None
        self._config = HeartbeatConfig()

    def register(self, client_id: str, ws):
        with self._lock:
            self._connections[client_id] = WebSocketClient(client_id, ws)
        logger.info(f"WebSocket client connected: {client_id} (total: {len(self._connections)})")

    def unregister(self, client_id: str):
        with self._lock:
            self._connections.pop(client_id, None)
        logger.info(f"WebSocket client disconnected: {client_id} (total: {len(self._connections)})")

    def heartbeat(self, client_id: str):
        """更新客户端心跳"""
        with self._lock:
            if client_id in self._connections:
                self._connections[client_id].update_heartbeat()

    async def broadcast(self, message: dict):
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead = []
        for cid, client in list(self._connections.items()):
            try:
                await client.ws.send(data)
                client.last_message = time.time()
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.unregister(cid)

    async def send_heartbeat(self):
        """发送心跳ping到所有客户端"""
        heartbeat_count = 0
        dead_clients = []

        with self._lock:
            current_time = time.time()
            for cid, client in list(self._connections.items()):
                try:
                    # 检查心跳超时
                    if client.check_timeout(self._config.HEARTBEAT_TIMEOUT):
                        logger.warning(f"Client {cid} heartbeat timeout")
                        client.is_alive = False
                        dead_clients.append(cid)
                        continue

                    # 发送ping
                    await client.ws.send(json.dumps({
                        "type": "heartbeat",
                        "timestamp": current_time,
                        "client_id": cid
                    }))
                    client.last_heartbeat = current_time
                    heartbeat_count += 1
                except Exception:
                    dead_clients.append(cid)

        # 清理断开的客户端
        for cid in dead_clients:
            self.unregister(cid)

        if heartbeat_count > 0:
            logger.debug(f"Heartbeat sent to {heartbeat_count} clients")

    async def start_heartbeat_loop(self):
        """启动心跳循环"""
        while True:
            await asyncio.sleep(self._config.HEARTBEAT_INTERVAL)
            await self.send_heartbeat()

    async def broadcast_status(self):
        while True:
            await asyncio.sleep(2)
            status = _build_observatory_status()
            await self.broadcast({"type": "status_update", "data": status})

    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """获取客户端信息"""
        with self._lock:
            if client_id in self._connections:
                client = self._connections[client_id]
                return {
                    "client_id": client_id,
                    "is_alive": client.is_alive,
                    "last_heartbeat": client.last_heartbeat,
                    "last_message": client.last_message,
                    "uptime_seconds": time.time() - client.last_heartbeat,
                    "reconnect_attempts": client.reconnect_attempts
                }
        return None

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        with self._lock:
            total = len(self._connections)
            alive = sum(1 for c in self._connections.values() if c.is_alive)
            dead = total - alive

            return {
                "total_connections": total,
                "alive_connections": alive,
                "dead_connections": dead,
                "heartbeat_interval": self._config.HEARTBEAT_INTERVAL,
                "heartbeat_timeout": self._config.HEARTBEAT_TIMEOUT
            }

    @property
    def connection_count(self):
        return len(self._connections)


ws_manager = WebSocketManager()

try:
    from realtime_bridge import (
        EventBus, AgentStateBridge, ConnectionManager,
        MessageSerializer, start_heartbeat_loop, start_broadcast_loop,
    )
    _event_bus = EventBus()
    _state_bridge = AgentStateBridge(_event_bus)
    _conn_manager = ConnectionManager()
    _REALTIME_BRIDGE_AVAILABLE = True
    logger.info("Realtime bridge module loaded successfully")
except ImportError:
    _event_bus = None
    _state_bridge = None
    _conn_manager = None
    _REALTIME_BRIDGE_AVAILABLE = False
    logger.warning("Realtime bridge module not available, using legacy WebSocket manager")

# ============ NASA SkyView 星图 API ============
try:
    from observation.sky_chart import NASA_SkyView_API, get_realtime_skychart, parse_coordinates, BUILTIN_CATALOG, SkySurvey
    _SKYCHART_AVAILABLE = True
except ImportError as e:
    logger.warning(f"sky_chart not available: {e}")
    _SKYCHART_AVAILABLE = False

_observatory_state = {
    "status": "idle",
    "uptime_hours": 0,
    "discoveries": 0,
    "hypotheses": 0,
    "current_target": None,
    "queue": [],
    "devices": {
        "telescope": {"name": "Seestar S50", "status": "disconnected", "connected": False},
        "camera": {"name": "IMX462", "status": "idle", "gain": 0, "exposure_ms": 0},
        "filter_wheel": {"name": "ZWO EFW", "status": "idle", "current": "None"},
        "dome": {"name": "远程圆顶", "status": "closed", "azimuth": 0},
        "weather": {"cloud_cover": 0, "humidity": 0, "temperature": 0, "wind_speed": 0, "seeing": 0},
    },
    "research_loop": None,
    "detections": {
        "stage1": {"total": 0, "stars": 0, "galaxies": 0, "qsos": 0},
        "stage2": {"classified_stars": 0, "classified_galaxies": 0, "classified_qsos": 0, "unknown": 0},
        "stage3": {"nebula": 0, "comet": 0, "galaxy": 0, "globular_cluster": 0},
    },
    "latest_image": None,
}

_alerts = []

_log_entries = []

_lightcurve_data = {
    "time": [],
    "magnitude": [],
    "error": [],
}

_cycle_history = []


def _build_observatory_status():
    state = _observatory_state.copy()
    state["timestamp"] = datetime.now().isoformat()
    state["ws_clients"] = ws_manager.connection_count
    return state


# ============ API 文档 ============

@app.route("/api/docs", methods=["GET"])
async def api_docs():
    return jsonify({
        "service": "天问-AGI 全自动天文观测站 API",
        "version": "2.3.0",
        "endpoints": {
            "observatory": {
                "GET  /api/observatory/status": "观测站完整状态",
                "GET  /api/observatory/queue": "观测队列",
                "POST /api/observatory/queue": "添加观测目标 {target, priority, type, window, duration}",
                "DELETE /api/observatory/queue/<id>": "移除队列项",
                "POST /api/observatory/control": "控制观测站 {action: start|stop|pause|resume}",
            },
            "devices": {
                "GET  /api/devices/status": "设备状态(望远镜/相机/滤镜轮/圆顶/气象站)",
            },
            "data": {
                "GET  /api/data/detections/latest": "三阶段检测结果",
                "GET  /api/data/images/latest": "最新图像信息",
                "GET  /api/data/lightcurve?target=M31": "光变曲线数据",
            },
            "research": {
                "GET  /api/research/status": "研究闭环状态",
                "GET  /api/research/cycles?page=1&per_page=20": "历史研究周期",
                "POST /api/hypothesis/test": "假说验证 (需要hypothesis对象，可选提供观测数据和文献证据)",
                "GET  /api/hypothesis/generate-test-data?target=M31&count=5": "生成测试数据",
            },
            "alerts": {
                "GET  /api/alerts?unread=true": "告警列表",
                "PUT  /api/alerts/<id>/read": "标记告警已读",
            },
            "logs": {
                "GET  /api/logs?level=DISCOVERY&limit=50": "系统日志",
            },
            "system": {
                "GET  /api/health": "健康检查",
                "GET  /api/stats/summary": "统计摘要",
                "GET  /api/stats/json": "JSON统计",
                "GET  /api/stats/dashboard": "HTML统计面板",
            },
            "chat": {
                "POST /api/chat": "LLM对话 {message, session_id}",
                "POST /api/cognitive": "认知引擎预览 {message}",
                "GET  /api/sessions": "会话列表",
                "GET  /api/sessions/<id>": "会话详情",
            },
            "websocket": {
                "WS   /ws/observatory": "观测站实时推送 (status_update, queue_update, new_alert)",
                "WS   /ws/agent_status": "Agent状态实时推送 (cognitive, planning, execution状态)",
                "WS   /ws/observation": "观测状态实时推送 (设备状态, 队列状态)",
            },
        },
        "realtime_bridge": "available" if _REALTIME_BRIDGE_AVAILABLE else "unavailable",
    })


# ============ WebSocket 端点 (增强版 - 心跳检测与断线重连) ============

@app.websocket('/ws/observatory')
async def observatory_ws():
    """
    WebSocket端点：观测站实时状态推送

    心跳机制:
    - 客户端应定期发送ping，服务器响应pong
    - 服务器定期发送heartbeat消息检测客户端存活
    - 超时配置: HEARTBEAT_TIMEOUT=60秒

    断线重连:
    - 前端应实现自动重连逻辑 (见web/index.html)
    - 重连延迟: RECONNECT_DELAY=3秒
    - 最大重连次数: MAX_RECONNECT_ATTEMPTS=10
    """
    client_id = str(uuid.uuid4())
    ws = websocket._get_current_object()

    # 创建心跳任务
    heartbeat_task = asyncio.create_task(_heartbeat_loop(client_id, ws))

    if _REALTIME_BRIDGE_AVAILABLE:
        _conn_manager.register(client_id, ws)
    else:
        ws_manager.register(client_id, ws)

    try:
        while True:
            data = await websocket.receive()

            # 心跳响应
            if data == "ping":
                if _REALTIME_BRIDGE_AVAILABLE:
                    _conn_manager.heartbeat(client_id)
                else:
                    ws_manager.heartbeat(client_id)
                await websocket.send("pong")

            # 获取状态
            elif data == "get_status":
                status = _build_observatory_status()
                await websocket.send(json.dumps(
                    {"type": "status_update", "data": status},
                    ensure_ascii=False, default=str
                ))

            # JSON格式消息
            elif data and data.startswith("{"):
                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type", "")

                    if msg_type == "ping":
                        # 客户端JSON格式ping
                        if _REALTIME_BRIDGE_AVAILABLE:
                            _conn_manager.heartbeat(client_id)
                        else:
                            ws_manager.heartbeat(client_id)
                        await websocket.send(json.dumps({"type": "pong", "timestamp": time.time()}))

                    elif msg_type == "pong":
                        # 客户端响应pong
                        if _REALTIME_BRIDGE_AVAILABLE:
                            _conn_manager.heartbeat(client_id)
                        else:
                            ws_manager.heartbeat(client_id)

                    elif msg_type == "subscribe" and _REALTIME_BRIDGE_AVAILABLE:
                        event_type = msg.get("event", "")
                        if event_type:
                            async def _forward(event_type_inner, event_data):
                                try:
                                    await websocket.send(MessageSerializer.serialize_event(event_type_inner, event_data))
                                except Exception:
                                    pass
                            _event_bus.subscribe(event_type, _forward)

                    elif msg_type == "get_client_info":
                        # 获取客户端信息
                        if _REALTIME_BRIDGE_AVAILABLE:
                            info = _conn_manager.get_client_info(client_id)
                        else:
                            info = ws_manager.get_client_info(client_id)
                        await websocket.send(json.dumps({"type": "client_info", "data": info}))

                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    finally:
        heartbeat_task.cancel()
        if _REALTIME_BRIDGE_AVAILABLE:
            _conn_manager.unregister(client_id)
        else:
            ws_manager.unregister(client_id)


async def _heartbeat_loop(client_id: str, ws):
    """客户端心跳循环"""
    while True:
        try:
            await asyncio.sleep(HeartbeatConfig.HEARTBEAT_INTERVAL)
            await ws.send(json.dumps({
                "type": "heartbeat",
                "timestamp": time.time(),
                "client_id": client_id
            }))
        except Exception:
            break


@app.websocket('/ws/agent_status')
async def agent_status_ws():
    """
    WebSocket端点：实时Agent状态推送

    心跳检测:
    - 每30秒发送ping，客户端需响应pong
    - 心跳超时时间: 60秒
    - 客户端信息: GET /api/ws/clients/<client_id>

    断线重连:
    - 客户端应实现自动重连机制
    - 建议重连延迟: 3秒
    - 最大重连次数: 10次
    """
    client_id = str(uuid.uuid4())
    ws = websocket._get_current_object()

    # 创建心跳任务
    heartbeat_task = asyncio.create_task(_heartbeat_loop(client_id, ws))

    ws_manager.register(client_id, ws)

    try:
        while True:
            data = await websocket.receive()

            if data == "ping":
                ws_manager.heartbeat(client_id)
                await websocket.send("pong")

            elif data == "get_status":
                status = _build_observatory_status()
                await websocket.send(json.dumps(
                    {"type": "status_update", "data": status},
                    ensure_ascii=False, default=str
                ))

            elif data and data.startswith("{"):
                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type", "")

                    if msg_type == "subscribe":
                        event_type = msg.get("event", "")
                        if event_type and _REALTIME_BRIDGE_AVAILABLE:
                            async def _forward(event_type_inner, event_data):
                                try:
                                    await websocket.send(MessageSerializer.serialize_event(event_type_inner, event_data))
                                except Exception:
                                    pass
                            _event_bus.subscribe(event_type, _forward)

                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    finally:
        heartbeat_task.cancel()
        ws_manager.unregister(client_id)


# ============ WebSocket管理API ============

@app.route("/api/ws/clients", methods=["GET"])
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


@app.route("/api/ws/clients/<client_id>", methods=["GET"])
async def ws_client_info(client_id):
    """获取指定WebSocket客户端信息"""
    info = ws_manager.get_client_info(client_id)
    if not info:
        return jsonify({"error": "Client not found"}), 404

    return jsonify(info)


@app.route("/api/ws/config", methods=["GET"])
async def ws_config():
    """获取WebSocket配置信息"""
    return jsonify({
        "heartbeat_interval": HeartbeatConfig.HEARTBEAT_INTERVAL,
        "heartbeat_timeout": HeartbeatConfig.HEARTBEAT_TIMEOUT,
        "reconnect_delay": HeartbeatConfig.RECONNECT_DELAY,
        "max_reconnect_attempts": HeartbeatConfig.MAX_RECONNECT_ATTEMPTS,
        "realtime_bridge_available": _REALTIME_BRIDGE_AVAILABLE
    })

    if _REALTIME_BRIDGE_AVAILABLE:
        _conn_manager.register(client_id, ws)
    else:
        ws_manager.register(client_id, ws)

    heartbeat_count = 0
    last_heartbeat = time.time()

    try:
        # 发送连接成功消息
        await websocket.send(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "heartbeat_interval": 30,
        }, ensure_ascii=False, default=str))

        while True:
            try:
                # 30秒心跳检测
                data = await asyncio.wait_for(websocket.receive(), timeout=30)
                last_heartbeat = time.time()
                heartbeat_count += 1

                if data == "ping":
                    await websocket.send("pong")
                    if _REALTIME_BRIDGE_AVAILABLE:
                        _conn_manager.heartbeat(client_id)
                elif data == "pong":
                    # 客户端响应心跳
                    pass
                elif data == "get_status":
                    # 返回Agent完整状态
                    status = _build_agent_status()
                    await websocket.send(json.dumps({
                        "type": "agent_status",
                        "data": status,
                    }, ensure_ascii=False, default=str))
                elif data and data.startswith("{"):
                    try:
                        msg = json.loads(data)
                        msg_type = msg.get("type", "")
                        if msg_type == "ping":
                            await websocket.send(json.dumps({
                                "type": "pong",
                                "timestamp": datetime.now().isoformat(),
                            }, ensure_ascii=False, default=str))
                        elif msg_type == "subscribe":
                            # 订阅特定事件
                            event = msg.get("event", "")
                            if event and _REALTIME_BRIDGE_AVAILABLE:
                                def make_forward(ev):
                                    async def forward(evt_type, data):
                                        try:
                                            await websocket.send(MessageSerializer.serialize_event(evt_type, data))
                                        except Exception:
                                            pass
                                    return forward
                                _event_bus.subscribe(event, make_forward(event))
                    except json.JSONDecodeError:
                        pass
            except asyncio.TimeoutError:
                # 心跳超时，发送ping检测连接
                await websocket.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": int(time.time() - last_heartbeat),
                }, ensure_ascii=False, default=str))

    except Exception:
        pass
    finally:
        if _REALTIME_BRIDGE_AVAILABLE:
            _conn_manager.unregister(client_id)
        else:
            ws_manager.unregister(client_id)


@app.websocket('/ws/observation')
async def observation_ws():
    """
    WebSocket端点：观测状态实时推送
    - 望远镜/相机/滤镜轮状态
    - 观测队列状态
    - 设备健康状态
    """
    client_id = str(uuid.uuid4())
    ws = websocket._get_current_object()

    if _REALTIME_BRIDGE_AVAILABLE:
        _conn_manager.register(client_id, ws)
    else:
        ws_manager.register(client_id, ws)

    try:
        await websocket.send(json.dumps({
            "type": "connected",
            "channel": "observation",
            "timestamp": datetime.now().isoformat(),
        }, ensure_ascii=False, default=str))

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive(), timeout=30)

                if data == "ping":
                    await websocket.send("pong")
                    if _REALTIME_BRIDGE_AVAILABLE:
                        _conn_manager.heartbeat(client_id)
                elif data == "get_observation_status":
                    status = _build_observation_status()
                    await websocket.send(json.dumps({
                        "type": "observation_status",
                        "data": status,
                    }, ensure_ascii=False, default=str))
                elif data == "get_device_status":
                    devices = _observatory_state.get("devices", {})
                    await websocket.send(json.dumps({
                        "type": "device_status",
                        "data": devices,
                    }, ensure_ascii=False, default=str))
                elif data == "get_queue":
                    queue = _observatory_state.get("queue", [])
                    await websocket.send(json.dumps({
                        "type": "queue_status",
                        "data": queue,
                    }, ensure_ascii=False, default=str))
            except asyncio.TimeoutError:
                await websocket.send(json.dumps({
                    "type": "heartbeat",
                    "channel": "observation",
                    "timestamp": datetime.now().isoformat(),
                }, ensure_ascii=False, default=str))
    except Exception:
        pass
    finally:
        if _REALTIME_BRIDGE_AVAILABLE:
            _conn_manager.unregister(client_id)
        else:
            ws_manager.unregister(client_id)


def _build_agent_status():
    """构建Agent状态数据"""
    return {
        "timestamp": datetime.now().isoformat(),
        "cognitive": {
            "status": "active" if agent and agent.cognitive else "inactive",
            "intent": "observation",
            "complexity": "medium",
        },
        "planning": {
            "status": "active" if agent and agent.planning else "inactive",
            "current_task": _observatory_state.get("research_loop", {}).get("topic", "未知"),
            "cycle_id": _observatory_state.get("research_loop", {}).get("cycle_id", "N/A"),
        },
        "execution": {
            "status": _observatory_state.get("status", "idle"),
            "current_target": _observatory_state.get("current_target", {}),
        },
        "evolution": {
            "status": "active" if agent and agent.evolution else "inactive",
            "discoveries": _observatory_state.get("discoveries", 0),
            "hypotheses": _observatory_state.get("hypotheses", 0),
        },
        "ws_clients": ws_manager.connection_count,
    }


def _build_observation_status():
    """构建观测状态数据"""
    return {
        "timestamp": datetime.now().isoformat(),
        "status": _observatory_state.get("status", "idle"),
        "current_target": _observatory_state.get("current_target", {}),
        "devices": _observatory_state.get("devices", {}),
        "queue_size": len(_observatory_state.get("queue", [])),
        "weather": _observatory_state.get("devices", {}).get("weather", {}),
    }


# ============ 观测站 API ============

@app.route("/api/observatory/status", methods=["GET"])
async def observatory_status():
    return jsonify(_build_observatory_status())


@app.route("/api/observatory/queue", methods=["GET"])
async def observatory_queue():
    return jsonify({"queue": _observatory_state["queue"]})


@app.route("/api/observatory/queue", methods=["POST"])
async def observatory_queue_add():
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
    _observatory_state["queue"].append(new_item)
    await ws_manager.broadcast({"type": "queue_update", "data": _observatory_state["queue"]})
    return jsonify({"success": True, "item": new_item})


@app.route("/api/observatory/queue/<item_id>", methods=["DELETE"])
async def observatory_queue_remove(item_id):
    _observatory_state["queue"] = [q for q in _observatory_state["queue"] if q["id"] != item_id]
    await ws_manager.broadcast({"type": "queue_update", "data": _observatory_state["queue"]})
    return jsonify({"success": True})


@app.route("/api/observatory/control", methods=["POST"])
async def observatory_control():
    data = await request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400
    action = data.get("action", "")
    valid_actions = ["start", "stop", "pause", "resume"]
    if action not in valid_actions:
        return jsonify({"error": f"无效操作: {action}，支持: {valid_actions}"}), 400

    status_map = {"start": "observing", "stop": "idle", "pause": "paused", "resume": "observing"}
    new_status = status_map[action]
    _observatory_state["status"] = new_status
    _log_entries.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": "SYSTEM",
        "message": f"观测站状态变更: {action}"
    })

    if _REALTIME_BRIDGE_AVAILABLE:
        _state_bridge.update_status(new_status)
        await _conn_manager.broadcast({
            "type": "status_update",
            "data": _build_observatory_status(),
        })
    else:
        await ws_manager.broadcast({
            "type": "status_update",
            "data": _build_observatory_status(),
        })
    return jsonify({"success": True, "status": new_status})


# ============ 设备 API ============

@app.route("/api/devices/status", methods=["GET"])
async def devices_status():
    return jsonify(_observatory_state["devices"])


# ============ 数据 API ============

@app.route("/api/data/detections/latest", methods=["GET"])
async def data_detections_latest():
    return jsonify(_observatory_state["detections"])


@app.route("/api/data/images/latest", methods=["GET"])
async def data_images_latest():
    return jsonify(_observatory_state["latest_image"])


@app.route("/api/data/lightcurve", methods=["GET"])
async def data_lightcurve():
    target = request.args.get("target", "M31")
    return jsonify({"target": target, "data": _lightcurve_data})


# ============ 研究闭环 API ============

@app.route("/api/research/status", methods=["GET"])
async def research_status():
    return jsonify(_observatory_state["research_loop"])


@app.route("/api/research/cycles", methods=["GET"])
async def research_cycles():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        "cycles": _cycle_history[::-1][start:end],
        "total": len(_cycle_history),
        "page": page,
        "per_page": per_page,
    })


# ============ 假说验证 API ============

@app.route("/api/hypothesis/test", methods=["POST"])
@require_api_key
async def test_hypothesis():
    """
    假说验证端点

    请求体:
    {
        "hypothesis": {
            "id": "hypo_xxx",
            "statement": "如果...那么...",
            "premises": [...],
            "predictions": [...],
            "verification_method": "...",
            "confidence": 0.7
        },
        "observation_data": [...],
        "literature_evidence": [...]
    }

    响应:
    {
        "hypothesis_id": "...",
        "overall_result": "confirmed|rejected|inconclusive|revised",
        "confidence_change": 0.x,
        "evidence_for": [...],
        "evidence_against": [...],
        "recommendation": "...",
        "confidence_interval": [...],
        "cross_validation_score": 0.x,
        "statistical_confidence": {...}
    }
    """
    data = await request.get_json()

    if not data or "hypothesis" not in data:
        return jsonify({"error": "缺少 hypothesis 字段"}), 400

    hypo_data = data["hypothesis"]
    observation_data = data.get("observation_data")
    literature_evidence = data.get("literature_evidence")

    if not observation_data or not literature_evidence:
        return jsonify({
            "error": "缺少必需数据",
            "message": "observation_data 和 literature_evidence 为必填字段",
            "code": "MISSING_REQUIRED_DATA"
        }), 400

    try:
        from research.hypothesis_generator import Hypothesis
        hypo = Hypothesis(
            id=hypo_data.get("id", f"hypo_{uuid.uuid4().hex[:8]}"),
            statement=hypo_data.get("statement", ""),
            premises=hypo_data.get("premises", []),
            predictions=hypo_data.get("predictions", []),
            verification_method=hypo_data.get("verification_method", "待指定"),
            confidence=hypo_data.get("confidence", 0.5),
            status="待验证"
        )
        report = await hypothesis_tester.test_hypothesis(hypo, observation_data, literature_evidence)

        logger.info(f"[HypothesisTest] 验证完成: hypothesis={hypo.id}, result={report.overall_result.value}")

        return jsonify({
            "hypothesis_id": report.hypothesis_id,
            "overall_result": report.overall_result.value,
            "confidence_change": round(report.confidence_change, 3),
            "evidence_for": report.evidence_for,
            "evidence_against": report.evidence_against,
            "recommendation": report.recommendation,
            "timestamp": report.timestamp,
            "confidence_interval": list(report.confidence_interval) if report.confidence_interval else None,
            "cross_validation_score": round(report.cross_validation_score, 3) if report.cross_validation_score else None,
            "statistical_confidence": report.statistical_confidence,
            "test_cases": [
                {
                    "id": tc.id,
                    "test_method": tc.test_method,
                    "passed": tc.passed,
                    "actual_outcome": tc.actual_outcome
                }
                for tc in report.test_cases
            ]
        })
    except Exception as e:
        logger.error(f"[HypothesisTest] 验证失败: {e}")
        return jsonify({"error": f"验证失败: {str(e)}"}), 500


# ============ 告警 API ============

@app.route("/api/alerts", methods=["GET"])
async def alerts_list():
    unread_only = request.args.get("unread", "false").lower() == "true"
    result = [a for a in _alerts if not unread_only or not a["read"]]
    return jsonify({"alerts": result, "unread_count": sum(1 for a in _alerts if not a["read"])})


@app.route("/api/alerts/<alert_id>/read", methods=["PUT"])
async def alerts_mark_read(alert_id):
    for a in _alerts:
        if a["id"] == alert_id:
            a["read"] = True
            return jsonify({"success": True})
    return jsonify({"error": "告警不存在"}), 404


# ============ 日志 API ============

@app.route("/api/logs", methods=["GET"])
async def logs_list():
    level = request.args.get("level", "")
    limit = int(request.args.get("limit", 50))
    result = _log_entries
    if level:
        result = [e for e in result if e["level"].upper() == level.upper()]
    return jsonify({"logs": result[:limit]})


# ============ NASA SkyView 星图 API (Plan B) ============

@app.route("/api/skychart/realtime", methods=["GET"])
async def skychart_realtime():
    """
    获取目标真实星图 (NASA SkyView)
    
    Query Params:
        target: 目标名称 (如 M31, NGC224)
        survey: 巡天调查 (默认 DSS2/color)
        size: 视场大小角分 (默认 15)
        pixels: 图像像素 (默认 600)
    """
    if not _SKYCHART_AVAILABLE:
        return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503
    
    target = request.args.get("target", "M31")
    survey_name = request.args.get("survey", "DSS2/color")
    size = float(request.args.get("size", 15))
    pixels = int(request.args.get("pixels", 600))
    
    try:
        sky_survey = SkySurvey(survey_name)
    except ValueError:
        sky_survey = SkySurvey.DSS2_COLOR
    
    try:
        result = await get_realtime_skychart(
            target=target,
            survey=sky_survey,
            size=size,
            pixels=pixels,
            use_cache=True
        )
        
        output = {
            "success": True,
            "target": result.target,
            "survey": result.survey,
            "ra": result.ra,
            "dec": result.dec,
            "width": result.width,
            "height": result.height,
            "fov_deg": result.fov,
            "image_base64": result.image_base64,
            "sources_count": len(result.catalog_sources),
            "sources": result.catalog_sources[:20],  # 只返回前20个
            "cached": result.cached,
            "timestamp": result.timestamp,
        }
        
        return jsonify(output)
    except Exception as e:
        logger.error(f"SkyChart error: {e}")
        return jsonify({"error": str(e), "code": "SKYCHART_ERROR"}), 500


@app.route("/api/skychart/batch", methods=["GET"])
async def skychart_batch():
    """
    批量获取多个目标星图
    
    Query Params:
        targets: 逗号分隔的目标列表
        survey: 巡天调查
        size: 视场大小角分
    """
    if not _SKYCHART_AVAILABLE:
        return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503
    
    targets_str = request.args.get("targets", "M31,M42,M51")
    survey_name = request.args.get("survey", "DSS2/color")
    size = float(request.args.get("size", 15))
    
    targets = [t.strip() for t in targets_str.split(",") if t.strip()]
    
    try:
        sky_survey = SkySurvey(survey_name)
    except ValueError:
        sky_survey = SkySurvey.DSS2_COLOR
    
    output = {}
    for target in targets:
        try:
            result = await get_realtime_skychart(
                target=target,
                survey=sky_survey,
                size=size,
                pixels=600,
                use_cache=True
            )
            output[target] = {
                "success": True,
                "ra": result.ra,
                "dec": result.dec,
                "fov_deg": result.fov,
                "sources_count": len(result.catalog_sources),
                "cached": result.cached,
            }
        except Exception as e:
            output[target] = {"success": False, "error": str(e)}
    
    return jsonify({
        "results": output,
        "requested": len(targets),
        "successful": sum(1 for v in output.values() if v.get("success"))
    })


@app.route("/api/skychart/coordinates", methods=["GET"])
async def skychart_coordinates():
    """查询目标坐标"""
    if not _SKYCHART_AVAILABLE:
        return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503
    
    target = request.args.get("target", "")
    if not target:
        return jsonify({"error": "未提供目标名称", "code": "NO_TARGET"}), 400
    
    coords = parse_coordinates(target)
    if coords is None:
        return jsonify({
            "error": f"无法解析目标: {target}",
            "code": "TARGET_NOT_FOUND",
            "hint": "请使用梅西耶编号(如M31)或NGC编号(如NGC224)"
        }), 404
    
    catalog_info = BUILTIN_CATALOG.get(target.upper(), {})
    
    return jsonify({
        "target": target,
        "ra": coords[0],
        "dec": coords[1],
        "name": catalog_info.get("name", ""),
        "type": catalog_info.get("type", ""),
        "mag": catalog_info.get("mag", None)
    })


# ============ 通用 API 路由 (前端兼容) ============

@app.route("/api/skychart", methods=["GET"])
async def skychart():
    """获取目标星图 (兼容前端 /api/skychart)"""
    target = request.args.get("target", "M31")
    
    try:
        if _SKYCHART_AVAILABLE:
            result = await get_realtime_skychart(target=target)
            return jsonify({
                "success": True,
                "target": result.target,
                "survey": result.survey,
                "ra": result.ra,
                "dec": result.dec,
                "image_url": result.image_url,
                "cached": result.cached,
                "timestamp": result.timestamp
            })
    except Exception as e:
        logger.warning(f"[SkyChart] NASA API 调用失败: {e}，返回坐标信息")
    
    # 降级：返回坐标信息
    try:
        from observation.sky_chart import parse_coordinates, BUILTIN_CATALOG
        coords = parse_coordinates(target)
        if coords:
            catalog_info = BUILTIN_CATALOG.get(target.upper(), {})
            return jsonify({
                "success": True,
                "target": target,
                "ra": coords[0],
                "dec": coords[1],
                "name": catalog_info.get("name", ""),
                "type": catalog_info.get("type", ""),
                "mag": catalog_info.get("mag"),
                "note": "NASA SkyView API 暂时不可用，返回坐标信息"
            })
    except Exception:
        pass
    
    return jsonify({"error": f"无法解析目标: {target}", "code": "TARGET_NOT_FOUND"}), 404


@app.route("/api/observation/data", methods=["GET"])
async def observation_data():
    """获取观测数据"""
    import json
    
    obs_path = get_observations_path()
    if obs_path.exists():
        with open(obs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({
            "success": True,
            "data": data,
            "source": str(obs_path)
        })
    return jsonify({
        "success": False,
        "data": [],
        "message": "暂无观测数据"
    })


@app.route("/api/hypothesis/generate", methods=["POST"])
async def hypothesis_generate():
    """生成假说 (兼容前端 /api/hypothesis/generate)"""
    try:
        data = await request.get_json()
        topic = data.get("topic", "")
        context = data.get("context", "")
        
        if not topic:
            return jsonify({"error": "topic 为必填字段"}), 400
        
        from research.hypothesis import HypothesisGenerator
        generator = HypothesisGenerator()
        hypotheses = generator.generate(topic, context)
        
        return jsonify({
            "success": True,
            "hypotheses": [h.to_dict() for h in hypotheses],
            "count": len(hypotheses)
        })
    except Exception as e:
        import traceback
        logger.error(f"[HypothesisGenerate] 生成失败: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"假说生成失败: {str(e)}",
            "code": "INTERNAL_ERROR",
            "traceback": traceback.format_exc()
        }), 500


@app.route("/api/data/miner", methods=["GET"])
async def data_miner():
    """数据挖掘 (兼容前端 /api/data/miner)"""
    target = request.args.get("target", "")
    
    if not target:
        return jsonify({"error": "target 为必填参数"}), 400
    
    from agents.data_miner import DataMiner
    miner = DataMiner()
    
    results = await miner.search(target)
    
    return jsonify({
        "success": True,
        "target": target,
        "results": results,
        "count": len(results) if isinstance(results, list) else 0
    })


# ============ 望远镜控制 API ============

_telescope_client = None
_telescope_connection_type = None
_telescope_discovered_devices = []

def _get_telescope_client():
    global _telescope_client
    if _telescope_client is None:
        try:
            from telescope.seestar_client import SeestarMCPClient
            _telescope_client = SeestarMCPClient()
            _telescope_client.enable_simulation(True)
        except ImportError:
            _telescope_client = None
    return _telescope_client

async def _discover_lan_devices(subnet: str = "192.168.1") -> list:
    """局域网设备发现 - 扫描常见望远镜端口"""
    discovered = []
    common_ports = [8765, 7624, 11111, 4030, 80, 8080]
    common_hosts = [
        "seestar.local", "seestar", "telescope.local",
        "stellarmate.local", "asiair.local", "raspberrypi.local"
    ]

    for host in common_hosts:
        for port in common_ports:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=1.0
                )
                writer.close()
                discovered.append({"host": host, "port": port, "method": "mDNS"})
            except Exception:
                pass

    for i in range(1, 20):
        host = f"{subnet}.{i}"
        for port in [8765, 7624]:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=0.3
                )
                writer.close()
                discovered.append({"host": host, "port": port, "method": "IP扫描"})
            except Exception:
                pass

    return discovered

def _detect_serial_ports() -> list:
    """检测串口设备（USB/物理导线连接）"""
    serial_ports = []
    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            serial_ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "vid": port.vid,
                "pid": port.pid,
                "serial_number": port.serial_number,
                "manufacturer": port.manufacturer,
            })
    except ImportError:
        if sys.platform == "win32":
            for i in range(1, 33):
                serial_ports.append({
                    "device": f"COM{i}",
                    "description": f"串口 COM{i}",
                    "hwid": "",
                })
        else:
            import glob
            for pattern in ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.SLAB*", "/dev/cu.*"]:
                for path in glob.glob(pattern):
                    serial_ports.append({
                        "device": path,
                        "description": path,
                        "hwid": "",
                    })
    return serial_ports


@app.route("/api/telescope/status", methods=["GET"])
async def telescope_status():
    """获取望远镜状态"""
    client = _get_telescope_client()
    if client is None:
        return jsonify({"error": "望远镜模块不可用", "code": "MODULE_UNAVAILABLE"}), 503

    if not client.is_connected:
        return jsonify({
            "connected": False,
            "status": "disconnected",
            "connection_type": _telescope_connection_type,
            "discovered_devices": _telescope_discovered_devices,
        })

    try:
        status = await client.get_status()
        pos = client.current_position
        return jsonify({
            "connected": True,
            "status": client.current_status.value,
            "position": {
                "ra": pos.ra,
                "dec": pos.dec,
                "alt": pos.alt,
                "az": pos.az,
            },
            "connection_type": _telescope_connection_type,
            "simulation_mode": client._simulation_mode,
            "raw_status": status,
        })
    except Exception as e:
        return jsonify({"error": str(e), "code": "STATUS_ERROR"}), 500


@app.route("/api/telescope/discover", methods=["GET"])
async def telescope_discover():
    """发现局域网和串口望远镜设备"""
    global _telescope_discovered_devices

    method = request.args.get("method", "all")

    lan_devices = []
    serial_devices = []

    if method in ("all", "lan"):
        subnet = request.args.get("subnet", "192.168.1")
        lan_devices = await _discover_lan_devices(subnet)

    if method in ("all", "serial"):
        serial_devices = _detect_serial_ports()

    _telescope_discovered_devices = {
        "lan": lan_devices,
        "serial": serial_devices,
        "total": len(lan_devices) + len(serial_devices),
    }

    return jsonify(_telescope_discovered_devices)


@app.route("/api/telescope/connect", methods=["POST"])
async def telescope_connect():
    """连接望远镜"""
    global _telescope_connection_type

    data = await request.get_json() or {}
    connection_type = data.get("type", "simulation")
    host = data.get("host", "localhost")
    port = data.get("port", 8765)
    serial_port = data.get("serial_port", None)

    client = _get_telescope_client()
    if client is None:
        return jsonify({"error": "望远镜模块不可用", "code": "MODULE_UNAVAILABLE"}), 503

    try:
        if connection_type == "simulation":
            client.enable_simulation(True)
            client.host = host
            client.port = port
            await client.connect()
            _telescope_connection_type = "simulation"

        elif connection_type == "lan":
            client.enable_simulation(False)
            client.host = host
            client.port = port
            success = await client.connect()
            if not success:
                return jsonify({"error": f"无法连接到 {host}:{port}", "code": "CONNECTION_FAILED"}), 503
            _telescope_connection_type = "lan"

        elif connection_type == "serial":
            client.enable_simulation(False)
            client.host = "serial"
            client.port = 0
            client._serial_port = serial_port
            await client.connect()
            _telescope_connection_type = "serial"

        elif connection_type == "ascom":
            from telescope.seestar_client import HardwareInterfaceType
            client.set_hardware_interface(HardwareInterfaceType.ASCOM, driver_id=data.get("driver_id"))
            client.enable_simulation(False)
            await client.connect()
            _telescope_connection_type = "ascom"

        elif connection_type == "indi":
            from telescope.seestar_client import HardwareInterfaceType
            client.set_hardware_interface(
                HardwareInterfaceType.INDI,
                host=data.get("indi_host", "localhost"),
                port=data.get("indi_port", 7624)
            )
            client.enable_simulation(False)
            await client.connect()
            _telescope_connection_type = "indi"

        else:
            return jsonify({"error": f"不支持的连接类型: {connection_type}", "code": "INVALID_TYPE"}), 400

        return jsonify({
            "success": True,
            "connection_type": _telescope_connection_type,
            "host": host,
            "port": port,
            "simulation_mode": client._simulation_mode,
        })

    except Exception as e:
        logger.error(f"望远镜连接失败: {e}")
        return jsonify({"error": f"连接失败: {str(e)}", "code": "CONNECTION_ERROR"}), 500


@app.route("/api/telescope/disconnect", methods=["POST"])
async def telescope_disconnect():
    """断开望远镜连接"""
    global _telescope_connection_type

    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    try:
        await client.safe_shutdown()
        _telescope_connection_type = None
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e), "code": "DISCONNECT_ERROR"}), 500


@app.route("/api/telescope/goto", methods=["POST"])
async def telescope_goto():
    """
    GOTO指向目标

    Body: {"target": "M31"} 或 {"target": "10.6847,41.2687"}
    """
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    data = await request.get_json()
    if not data or "target" not in data:
        return jsonify({"error": "缺少 target 参数", "code": "MISSING_TARGET"}), 400

    target_str = data["target"].strip()

    try:
        from telescope.seestar_client import ObservationTarget

        if "," in target_str:
            parts = target_str.split(",")
            ra = float(parts[0].strip())
            dec = float(parts[1].strip())
            target_name = data.get("name", f"RA{ra}_DEC{dec}")
        else:
            coords = parse_coordinates(target_str) if _SKYCHART_AVAILABLE else None
            if coords:
                ra, dec = coords
                target_name = target_str
            else:
                return jsonify({"error": f"无法解析目标: {target_str}", "code": "TARGET_NOT_FOUND"}), 404

        target = ObservationTarget(
            name=target_name,
            ra=ra,
            dec=dec,
            priority=data.get("priority", 0.8),
            exposure_time=data.get("exposure_time", 60),
            filter=data.get("filter", "L"),
        )

        success = await client.goto_target(target)
        if success:
            return jsonify({
                "success": True,
                "target": target_name,
                "ra": ra,
                "dec": dec,
                "status": client.current_status.value,
            })
        else:
            return jsonify({"error": "GOTO失败，安全检查未通过或设备错误", "code": "GOTO_FAILED"}), 500

    except Exception as e:
        logger.error(f"望远镜GOTO失败: {e}")
        return jsonify({"error": str(e), "code": "GOTO_ERROR"}), 500


@app.route("/api/telescope/plate_solve", methods=["POST"])
async def telescope_plate_solve():
    """执行Plate Solving校准"""
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    try:
        return jsonify({
            "success": True,
            "message": "Plate Solving功能需要ASTAP/Astrometry.net支持",
            "solved": False,
            "ra": client.current_position.ra,
            "dec": client.current_position.dec,
        })
    except Exception as e:
        return jsonify({"error": str(e), "code": "PLATE_SOLVE_ERROR"}), 500


@app.route("/api/telescope/tracking", methods=["POST"])
async def telescope_tracking():
    """
    望远镜跟踪控制

    Body: {"action": "start"} 或 {"action": "stop"}
    """
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    data = await request.get_json()
    if not data or "action" not in data:
        return jsonify({"error": "缺少 action 参数", "code": "MISSING_ACTION"}), 400

    action = data["action"]

    try:
        if action == "start":
            client.current_status = client.telescope_status_enum().TRACKING if hasattr(client, 'telescope_status_enum') else type(client.current_status).TRACKING
        elif action == "stop":
            await client.abort()
        else:
            return jsonify({"error": f"无效操作: {action}", "code": "INVALID_ACTION"}), 400

        return jsonify({"success": True, "action": action, "status": client.current_status.value})
    except Exception as e:
        return jsonify({"error": str(e), "code": "TRACKING_ERROR"}), 500


@app.route("/api/telescope/expose", methods=["POST"])
async def telescope_expose():
    """
    执行曝光成像

    Body: {"exposure": 30, "count": 3, "target": "M31"}
    """
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    data = await request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空", "code": "EMPTY_BODY"}), 400

    exposure = float(data.get("exposure", 30))
    count = int(data.get("count", 1))
    target_name = data.get("target", "unknown")
    filter_name = data.get("filter", "L")

    try:
        success = await client.start_imaging(
            exposure_time=exposure,
            filter_name=filter_name,
            count=count,
        )

        if success:
            return jsonify({
                "success": True,
                "target": target_name,
                "exposure_sec": exposure,
                "frame_count": count,
                "filter": filter_name,
                "file_path": f"images/{target_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fits",
            })
        else:
            return jsonify({"error": "曝光失败", "code": "EXPOSE_FAILED"}), 500

    except Exception as e:
        logger.error(f"望远镜曝光失败: {e}")
        return jsonify({"error": str(e), "code": "EXPOSE_ERROR"}), 500


@app.route("/api/telescope/window", methods=["GET"])
async def telescope_observation_window():
    """
    计算目标观测窗口
    
    Query Params: target=M31&latitude=40.0
    """
    target_name = request.args.get("target", "M31")
    latitude = float(request.args.get("latitude", 40.0))
    
    coords = parse_coordinates(target_name) if _SKYCHART_AVAILABLE else None
    if not coords:
        # 回退到星表查找
        if _SKYCHART_AVAILABLE:
            catalog_info = BUILTIN_CATALOG.get(target_name.upper(), {})
            coords = (catalog_info.get("ra"), catalog_info.get("dec"))
    
    if not coords or coords[0] is None:
        return jsonify({"error": f"无法解析目标: {target_name}"}), 400
    
    return jsonify({
        "target": target_name,
        "latitude": latitude,
        "ra": coords[0],
        "dec": coords[1],
    })


@app.route("/api/telescope/catalog", methods=["GET"])
async def telescope_catalog():
    """
    获取内置天体星表
    
    Query Params: type=galaxy (可选过滤类型)
    """
    if not _SKYCHART_AVAILABLE:
        return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503
    
    obj_type = request.args.get("type", None)
    
    catalog = {}
    for name, info in BUILTIN_CATALOG.items():
        if obj_type is None or info.get("type") == obj_type:
            catalog[name] = info
    
    return jsonify({
        "count": len(catalog),
        "type_filter": obj_type,
        "catalog": catalog
    })


# ============ 统计 API ============

@app.route("/api/stats/summary", methods=["GET"])
async def stats_summary():
    return jsonify({
        "total_cycles": len(_cycle_history),
        "completed_cycles": sum(1 for c in _cycle_history if c["status"] == "completed"),
        "total_discoveries": sum(c["discoveries"] for c in _cycle_history),
        "total_hypotheses": sum(c["hypotheses"] for c in _cycle_history),
        "uptime_hours": _observatory_state["uptime_hours"],
        "active_ws_clients": ws_manager.connection_count,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    logger.info("=" * 50)
    logger.info("天问-AGI 全自动天文观测站 API Server")
    logger.info("=" * 50)
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"API Key configured: {'Yes' if API_KEY else 'No (auth disabled)'}")
    logger.info(f"CORS Origins: {CORS_ORIGINS or 'All (debug mode)'}")
    logger.info(f"Session Store: {_session_store_type} (REDIS_URL: {'set' if os.environ.get('REDIS_URL') else 'not set'})")
    logger.info(f"Realtime Bridge: {'Available' if _REALTIME_BRIDGE_AVAILABLE else 'Unavailable (legacy mode)'}")
    logger.info(f"Local:    http://localhost:{port}")
    logger.info(f"API Docs: http://localhost:{port}/api/docs")
    logger.info(f"Health:   http://localhost:{port}/api/health")
    logger.info(f"WebSocket: ws://localhost:{port}/ws/observatory")
    logger.info(f"Agent Status WS: ws://localhost:{port}/ws/agent_status")
    logger.info(f"Observation WS: ws://localhost:{port}/ws/observation")
    logger.info("=" * 50)

    if _REALTIME_BRIDGE_AVAILABLE:
        @app.before_serving
        async def start_bridge_tasks():
            asyncio.ensure_future(start_heartbeat_loop(_conn_manager))
            asyncio.ensure_future(start_broadcast_loop(_conn_manager, _state_bridge))
            logger.info("Realtime bridge background tasks started")

    # 启动WebSocket心跳循环
    @app.before_serving
    async def start_ws_heartbeat():
        asyncio.ensure_future(ws_manager.start_heartbeat_loop())
        logger.info("WebSocket heartbeat loop started")

    app.run(host="0.0.0.0", port=port, debug=DEBUG)