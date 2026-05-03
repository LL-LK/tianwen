"""
天问-AGI 统一日志模块

用法:
    from runtime_logger import get_logger
    logger = get_logger(__name__)
    logger.info("message")
    logger.error("error message", exc_info=True)
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", "")
LOG_FORMAT = os.environ.get(
    "LOG_FORMAT",
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))

_loggers: dict = {}
_logging_initialized = False


def _init_logging():
    global _logging_initialized
    if _logging_initialized:
        return

    root_logger = logging.getLogger("tianwen_agi")
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    if not root_logger.handlers:
        formatter = logging.Formatter(LOG_FORMAT)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        if LOG_FILE:
            log_dir = Path(LOG_FILE).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    _logging_initialized = True


def get_logger(name: str = "tianwen_agi") -> logging.Logger:
    _init_logging()
    if name not in _loggers:
        _loggers[name] = logging.getLogger(f"tianwen_agi.{name}")
    return _loggers[name]
