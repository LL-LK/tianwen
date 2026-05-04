"""
数据模式管理器 - 控制演示数据与真实数据的切换
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

DATA_DIR = Path(__file__).parent.parent / "data"
DEMO_DIR = DATA_DIR / "demo"
REAL_CONFIG = DATA_DIR / "real_config.json.example"


class DataMode:
    DEMO = "demo"
    REAL = "real"


def get_current_mode() -> str:
    """获取当前数据模式"""
    return os.environ.get("DATA_MODE", DataMode.DEMO)


def is_demo_mode() -> bool:
    """是否为演示模式"""
    return get_current_mode() == DataMode.DEMO


def load_demo_config() -> Dict[str, Any]:
    """加载演示配置"""
    config_path = DEMO_DIR / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_real_config() -> Dict[str, Any]:
    """加载真实配置"""
    if REAL_CONFIG.exists():
        with open(REAL_CONFIG, "r", encoding="utf-8") as f:
            config = json.load(f)
            for key, value in config.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    config[key] = os.environ.get(env_var, "")
            return config
    return {}


def get_sessions_path() -> Path:
    """获取会话文件路径"""
    if is_demo_mode():
        return DEMO_DIR / "sessions.json"
    return DATA_DIR / "sessions.json"


def get_observations_path() -> Path:
    """获取观测数据路径"""
    if is_demo_mode():
        return DEMO_DIR / "sample_observations" / "observations.json"
    return DATA_DIR / "observations.json"


def get_star_catalog_path() -> Path:
    """获取星表数据库路径"""
    if is_demo_mode():
        return DEMO_DIR / "star_catalogs.db"
    return DATA_DIR / "star_catalogs.db"


def get_config() -> Dict[str, Any]:
    """获取当前配置"""
    if is_demo_mode():
        return load_demo_config()
    return load_real_config()
