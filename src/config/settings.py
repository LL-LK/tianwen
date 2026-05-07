"""
天问-AGI 统一配置管理模块

提供类型安全的配置管理，支持：
- 环境变量读取
- 配置验证
- 敏感信息脱敏
- 运行时重载
"""

import os
from typing import Optional, Dict, Any, List, Union, Callable
from dataclasses import dataclass, field
from pathlib import Path
from functools import lru_cache
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


ENV_PREFIX = "TIANWEN_"


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
    
    def get_active_providers(self) -> List[str]:
        """获取已配置的服务提供商"""
        providers = []
        if self.minimax_api_key:
            providers.append("minimax")
        if self.deepseek_api_key:
            providers.append("deepseek")
        if self.qwen_endpoint:
            providers.append("qwen")
        if self.ollama_endpoint:
            providers.append("ollama")
        return providers


@dataclass
class SecurityConfig:
    """安全相关配置"""
    api_key: str = ""
    cors_origins: List[str] = field(default_factory=list)
    debug: bool = False
    rate_limit_window: int = 60
    rate_limit_max_requests: int = 30
    
    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        if self.debug and not os.environ.get("DEBUG", ""):
            logging.warning("Debug mode is enabled in production")
        return errors


@dataclass
class DatabaseConfig:
    """数据库相关配置"""
    redis_url: str = ""
    chromadb_path: str = "./runtime/data/chroma_db"
    session_ttl: int = 3600
    
    def validate(self) -> List[str]:
        errors = []
        if self.chromadb_path:
            path = Path(self.chromadb_path)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create chromadb directory: {e}")
        return errors


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
    
    def validate(self) -> List[str]:
        errors = []
        if self.heartbeat_interval <= 0:
            errors.append("heartbeat_interval must be positive")
        if self.heartbeat_timeout <= self.heartbeat_interval:
            errors.append("heartbeat_timeout should be greater than heartbeat_interval")
        return errors


@dataclass
class WorkflowConfig:
    """工作流引擎配置"""
    state_dir: str = "./runtime/data/workflows"
    max_loops: int = 10
    default_timeout: int = 300
    
    def validate(self) -> List[str]:
        errors = []
        if self.max_loops <= 0:
            errors.append("max_loops must be positive")
        if self.default_timeout <= 0:
            errors.append("default_timeout must be positive")
        return errors


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
    app_name: str = "tianwen-agi"
    
    def validate(self) -> Dict[str, List[str]]:
        """验证所有配置项"""
        all_errors = {}
        
        for name, config in [
            ("security", self.security),
            ("database", self.database),
            ("websocket", self.websocket),
            ("workflow", self.workflow),
        ]:
            if hasattr(config, "validate"):
                errors = config.validate()
                if errors:
                    all_errors[name] = errors
        
        if not self.llm.get_active_providers():
            all_errors["llm"] = ["No LLM provider is configured"]
        
        return all_errors
    
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return os.environ.get("ENV", "development") == "production"


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def _get_env(key: str, default: Any = None, prefix: str = ENV_PREFIX) -> Any:
        """获取环境变量"""
        full_key = f"{prefix}{key}"
        return os.environ.get(full_key, os.environ.get(key, default))
    
    @staticmethod
    def _get_env_bool(key: str, default: bool = False, prefix: str = ENV_PREFIX) -> bool:
        """获取布尔类型环境变量"""
        full_key = f"{prefix}{key}"
        value = os.environ.get(full_key, os.environ.get(key, str(default))).lower()
        return value in ("true", "1", "yes", "on", "enabled")
    
    @staticmethod
    def _get_env_int(key: str, default: int = 0, prefix: str = ENV_PREFIX) -> int:
        """获取整数类型环境变量"""
        full_key = f"{prefix}{key}"
        value = os.environ.get(full_key, os.environ.get(key, str(default)))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def _get_env_list(
        key: str, 
        separator: str = ",", 
        default: List[str] = None,
        prefix: str = ENV_PREFIX
    ) -> List[str]:
        """获取列表类型环境变量"""
        full_key = f"{prefix}{key}"
        value = os.environ.get(full_key, os.environ.get(key, ""))
        if not value:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    @classmethod
    def load(cls, skip_validation: bool = False) -> AppSettings:
        """加载所有配置"""
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
        
        settings.app_name = cls._get_env("APP_NAME", "tianwen-agi")
        
        if not skip_validation:
            errors = settings.validate()
            if errors:
                error_msg = "; ".join(f"{k}: {v}" for k, v in errors.items())
                raise ValueError(f"Configuration validation failed: {error_msg}")
        
        return settings


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """获取配置实例（带缓存）"""
    return ConfigLoader.load()


# 全局配置实例
settings = get_settings()


def reload_settings() -> AppSettings:
    """重新加载配置（清除缓存）"""
    get_settings.cache_clear()
    return get_settings()


def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """脱敏敏感信息"""
    if not value or len(value) <= visible_chars:
        return "***"
    return value[:visible_chars] + "***"


def get_masked_settings() -> Dict[str, Any]:
    """获取脱敏后的配置（用于日志）"""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "debug": settings.security.debug,
        "llm_providers": settings.llm.get_active_providers(),
        "database": {
            "chromadb_path": settings.database.chromadb_path,
            "session_ttl": settings.database.session_ttl,
        },
        "telescope": {
            "simulator_enabled": settings.telescope.simulator_enabled,
            "auto_track": settings.telescope.auto_track,
        },
    }