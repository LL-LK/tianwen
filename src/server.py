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

# ============================================================
# 向下兼容：从子包导入已迁移的路由和中间件
# 2025-05-16 重构：代码迁移至 server/routes/ 和 server/middleware/
# ============================================================
try:
    from server.routes import (
        register_chat_routes, register_system_routes, register_telescope_routes,
        register_workflow_engine_routes, register_websocket_routes,
        register_sessions_routes, register_research_routes, register_skychart_routes,
        register_data_routes, register_observation_routes, register_observatory_routes,
        register_other_routes,
    )
    from server.routes.session_route import register_session_routes
    from server.routes.stats import register_stats_routes
    _SUBPACKAGE_AVAILABLE = True
except ImportError:
    _SUBPACKAGE_AVAILABLE = False

try:
    from server.middleware.cors import add_cors_headers
    from server.middleware.security import require_api_key, require_admin
    from server.middleware.auth import require_auth
    from server.middleware.rate_limit import rate_limit
except ImportError:
    pass

from quart import Quart, jsonify, request, render_template, websocket
import uuid
import json
import time
from threading import Lock
from datetime import datetime
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

def _generate_etag(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()

@app.after_request
async def add_cache_headers(response):
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

from main import HermesAGI
from core.cognitive import CognitiveEngine, PlanningEngine
from web.dashboard import CycleStatisticsDashboard
from research.hypothesis_tester import HypothesisTester
from data.data_mode import get_observations_path
import httpx

try:
    from agents.agent_enhancements import (
        AgentEnhancements, ADSApiClient, SemanticScholarClient,
        FactVerifier, HallucinationDetector, CitationTracker,
        HybridRAG, ToolRegistry, WorkflowOrchestrator
    )
    _ENHANCEMENTS_AVAILABLE = True
except ImportError:
    _ENHANCEMENTS_AVAILABLE = False
    AgentEnhancements = None

_enhancements = AgentEnhancements() if _ENHANCEMENTS_AVAILABLE else None

try:
    from agents.workflow_engine import WorkflowEngine, get_workflow_engine, NodeType, NodeStatus
    _WORKFLOW_ENGINE_AVAILABLE = True
except ImportError:
    _WORKFLOW_ENGINE_AVAILABLE = False
    WorkflowEngine = None

_workflow_engine = get_workflow_engine() if _WORKFLOW_ENGINE_AVAILABLE else None

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

async def call_minimax(message: str, api_key: str = None, group_id: str = None, endpoint: str = None, model: str = None, api_format: str = None, system_prompt: str = None) -> dict:
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

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": message})

    try:
        if api_format == "openai":
            url = f"{endpoint}/chat/completions"
            payload = {
                "model": model,
                "messages": messages,
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
                "messages": messages,
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

async def call_openai_compatible(message: str, api_key: str, endpoint: str, model: str, api_format: str = None, system_prompt: str = None) -> dict:
    """调用OpenAI兼容格式的API (Qwen, OpenAI, 本地部署等)，支持Anthropic格式"""
    if not api_key or not endpoint or not model:
        logger.error(f"[LLM] 配置缺失: api_key={'***' if api_key else 'None'}, endpoint={endpoint}, model={model}")
        return {"error": "API key, endpoint, or model not configured", "content": None}

    api_format = api_format or "openai"
    endpoint = endpoint.rstrip("/")
    client = _get_http_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": message})

    try:
        if api_format == "anthropic":
            url = f"{endpoint}/v1/messages"
            payload = {
                "model": model,
                "messages": messages,
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
                "messages": messages,
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

if _REALTIME_BRIDGE_AVAILABLE:
    @app.before_serving
    async def _start_bridge_tasks():
        asyncio.ensure_future(start_heartbeat_loop(_conn_manager))
        asyncio.ensure_future(start_broadcast_loop(_conn_manager, _state_bridge))
        logger.info("Realtime bridge background tasks started")

@app.before_serving
async def _start_ws_heartbeat():
    asyncio.ensure_future(ws_manager.start_heartbeat_loop())
    logger.info("WebSocket heartbeat loop started")

# ============ 注册子包路由 ============
if _SUBPACKAGE_AVAILABLE:
    @app.before_serving
    async def _register_subpackage_routes():
        from server.routes import register_all_routes
        register_all_routes(app)
        logger.info("All subpackage routes registered")

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

# ============ 设备 API ============

async def _get_telescope_client():
    """懒加载望远镜客户端（延迟初始化避免启动时连接失败）"""
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

