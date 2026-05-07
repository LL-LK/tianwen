"""
天问-AGI 统一配置管理模块
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class LLMConfig:
    """LLM相关配置"""
    minimax_api_key: str = ""
    minimax_group_id: str = ""
    minimax_model: str = "MiniMax-M2.7"
    minimax_endpoint: str = "https://api.minimax.chat/v1"
    deepseek_api_key: str = ""
    deepseek_endpoint: str = "https://api.deepseek.com"
    qwen_endpoint: str = "http://localhost:8000"
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "llama2"


@dataclass
class SecurityConfig:
    """安全相关配置"""
    api_key: str = ""
    cors_origins: List[str] = field(default_factory=list)
    debug: bool = False
    rate_limit_window: int = 60
    rate_limit_max_requests: int = 30


@dataclass
class DatabaseConfig:
    """数据库相关配置"""
    redis_url: str = ""
    chromadb_path: str = "./runtime/data/chroma_db"
    session_ttl: int = 3600


@dataclass
class TelescopeConfig:
    """望远镜相关配置"""
    seestar_endpoint: str = ""
    simulator_enabled: bool = True
    auto_track: bool = True


@dataclass
class WebSocketConfig:
    """WebSocket配置"""
    heartbeat_interval: int = 30
    heartbeat_timeout: int = 60
    max_reconnect_attempts: int = 10


@dataclass
class WorkflowConfig:
    """工作流引擎配置"""
    state_dir: str = "./runtime/data/workflows"
    max_loops: int = 10
    default_timeout: int = 300


@dataclass
class AppSettings:
    """应用配置汇总"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    telescope: TelescopeConfig = field(default_factory=TelescopeConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    version: str = "2.4.0"


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def _get_env(key: str, default: Any = None) -> Any:
        return os.environ.get(key, default)
    
    @staticmethod
    def _get_env_bool(key: str, default: bool = False) -> bool:
        value = os.environ.get(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    @staticmethod
    def _get_env_int(key: str, default: int = 0) -> int:
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            return default
    
    @staticmethod
    def _get_env_list(key: str, separator: str = ",", default: List[str] = None) -> List[str]:
        value = os.environ.get(key, "")
        if not value:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    @classmethod
    def load(cls) -> AppSettings:
        settings = AppSettings()
        
        settings.llm.minimax_api_key = cls._get_env("MINIMAX_API_KEY", "")
        settings.llm.minimax_group_id = cls._get_env("MINIMAX_GROUP_ID", "")
        settings.llm.minimax_model = cls._get_env("MINIMAX_MODEL", "MiniMax-M2.7")
        settings.llm.minimax_endpoint = cls._get_env("MINIMAX_ENDPOINT", "https://api.minimax.chat/v1")
        settings.llm.deepseek_api_key = cls._get_env("DEEPSEEK_API_KEY", "")
        settings.llm.deepseek_endpoint = cls._get_env("DEEPSEEK_ENDPOINT", "https://api.deepseek.com")
        settings.llm.qwen_endpoint = cls._get_env("QWEN_ENDPOINT", "http://localhost:8000")
        settings.llm.ollama_endpoint = cls._get_env("OLLAMA_ENDPOINT", "http://localhost:11434")
        settings.llm.ollama_model = cls._get_env("OLLAMA_MODEL", "llama2")
        
        settings.security.api_key = cls._get_env("API_KEY", "")
        settings.security.cors_origins = cls._get_env_list("CORS_ORIGINS", ",")
        settings.security.debug = cls._get_env_bool("DEBUG", False)
        settings.security.rate_limit_window = cls._get_env_int("RATE_LIMIT_WINDOW", 60)
        settings.security.rate_limit_max_requests = cls._get_env_int("RATE_LIMIT_MAX_REQUESTS", 30)
        
        settings.database.redis_url = cls._get_env("REDIS_URL", "")
        settings.database.chromadb_path = cls._get_env("CHROMADB_PATH", "./runtime/data/chroma_db")
        settings.database.session_ttl = cls._get_env_int("SESSION_TTL", 3600)
        
        settings.telescope.seestar_endpoint = cls._get_env("SEESTAR_ENDPOINT", "")
        settings.telescope.simulator_enabled = cls._get_env_bool("SIMULATOR_ENABLED", True)
        settings.telescope.auto_track = cls._get_env_bool("AUTO_TRACK", True)
        
        settings.websocket.heartbeat_interval = cls._get_env_int("WS_HEARTBEAT_INTERVAL", 30)
        settings.websocket.heartbeat_timeout = cls._get_env_int("WS_HEARTBEAT_TIMEOUT", 60)
        settings.websocket.max_reconnect_attempts = cls._get_env_int("WS_MAX_RECONNECT", 10)
        
        settings.workflow.state_dir = cls._get_env("WORKFLOW_STATE_DIR", "./runtime/data/workflows")
        settings.workflow.max_loops = cls._get_env_int("WORKFLOW_MAX_LOOPS", 10)
        settings.workflow.default_timeout = cls._get_env_int("WORKFLOW_DEFAULT_TIMEOUT", 300)
        
        return settings


settings = ConfigLoader.load()


def get_settings() -> AppSettings:
    return settings


def reload_settings() -> AppSettings:
    global settings
    settings = ConfigLoader.load()
    return settings