"""
runtime_logger 兼容模块
重定向到 utils.logger
"""

try:
    from src.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger
