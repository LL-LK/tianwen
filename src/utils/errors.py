"""
天问-AGI 统一错误处理模块
"""

from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(Enum):
    """错误代码枚举"""
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_API_KEY = "INVALID_API_KEY"
    MISSING_API_KEY = "MISSING_API_KEY"
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_NOT_AVAILABLE = "RESOURCE_NOT_AVAILABLE"
    LLM_ERROR = "LLM_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_CONFIG_ERROR = "LLM_CONFIG_ERROR"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    TELESCOPE_ERROR = "TELESCOPE_ERROR"
    TELESCOPE_OFFLINE = "TELESCOPE_OFFLINE"
    TELESCOPE_BUSY = "TELESCOPE_BUSY"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    NODE_EXECUTION_FAILED = "NODE_EXECUTION_FAILED"
    INVALID_WORKFLOW = "INVALID_WORKFLOW"
    DATA_ERROR = "DATA_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    RATE_LIMITED = "RATE_LIMITED"


class TianwenError(Exception):
    """天问-AGI 基础异常类"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}
        self.retryable = retryable
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "detail": self.detail,
                "retryable": self.retryable
            }
        }


class ValidationError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.INVALID_REQUEST, message, detail)


class AuthError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.UNAUTHORIZED, message, detail)


class ForbiddenError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.FORBIDDEN, message, detail)


class NotFoundError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.NOT_FOUND, message, detail)


class LLMError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None, retryable: bool = False):
        super().__init__(ErrorCode.LLM_ERROR, message, detail, retryable)


class TelescopeError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.TELESCOPE_ERROR, message, detail)


class WorkflowError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.WORKFLOW_ERROR, message, detail)


class DatabaseError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.DATABASE_ERROR, message, detail)


class RateLimitError(TianwenError):
    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(ErrorCode.RATE_LIMITED, message, detail)


class ErrorHandler:
    @staticmethod
    def handle(error: Exception) -> Dict[str, Any]:
        if isinstance(error, TianwenError):
            return error.to_dict()
        return {
            "error": {
                "code": ErrorCode.UNKNOWN_ERROR.value,
                "message": str(error),
                "detail": {},
                "retryable": False
            }
        }
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        if isinstance(error, TianwenError):
            return error.retryable
        import socket
        if isinstance(error, (socket.timeout, ConnectionError)):
            return True
        return False


HTTP_STATUS_CODES = {
    ErrorCode.UNKNOWN_ERROR: 500,
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.MISSING_PARAMETER: 400,
    ErrorCode.INVALID_PARAMETER: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.INVALID_API_KEY: 403,
    ErrorCode.MISSING_API_KEY: 401,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.RESOURCE_CONFLICT: 409,
    ErrorCode.RESOURCE_NOT_AVAILABLE: 503,
    ErrorCode.LLM_ERROR: 500,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.LLM_CONFIG_ERROR: 500,
    ErrorCode.LLM_UNAVAILABLE: 503,
    ErrorCode.TELESCOPE_ERROR: 500,
    ErrorCode.TELESCOPE_OFFLINE: 503,
    ErrorCode.TELESCOPE_BUSY: 409,
    ErrorCode.WORKFLOW_ERROR: 500,
    ErrorCode.NODE_EXECUTION_FAILED: 500,
    ErrorCode.INVALID_WORKFLOW: 400,
    ErrorCode.DATA_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.CACHE_ERROR: 500,
    ErrorCode.RATE_LIMITED: 429,
}


def get_http_status_code(error: TianwenError) -> int:
    return HTTP_STATUS_CODES.get(error.code, 500)