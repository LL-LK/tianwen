"""
天问-AGI 统一错误处理模块

提供：
- 统一的错误代码体系
- 可追溯的错误链
- HTTP状态码映射
- 错误上下文管理
"""

from typing import Dict, Any, Optional, List, Callable, Type
from enum import Enum
from functools import wraps
import traceback
import logging


class ErrorCode(Enum):
    """错误代码枚举"""
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    
    REQUEST_ERROR = "REQUEST_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    
    AUTH_ERROR = "AUTH_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_API_KEY = "INVALID_API_KEY"
    MISSING_API_KEY = "MISSING_API_KEY"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    
    RESOURCE_ERROR = "RESOURCE_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_NOT_AVAILABLE = "RESOURCE_NOT_AVAILABLE"
    
    LLM_ERROR = "LLM_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_CONFIG_ERROR = "LLM_CONFIG_ERROR"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_RESPONSE_PARSE_ERROR = "LLM_RESPONSE_PARSE_ERROR"
    
    TELESCOPE_ERROR = "TELESCOPE_ERROR"
    TELESCOPE_OFFLINE = "TELESCOPE_OFFLINE"
    TELESCOPE_BUSY = "TELESCOPE_BUSY"
    TELESCOPE_NOT_CONNECTED = "TELESCOPE_NOT_CONNECTED"
    TELESCOPE_GUIDING_ERROR = "TELESCOPE_GUIDING_ERROR"
    
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    NODE_EXECUTION_FAILED = "NODE_EXECUTION_FAILED"
    INVALID_WORKFLOW = "INVALID_WORKFLOW"
    WORKFLOW_TIMEOUT = "WORKFLOW_TIMEOUT"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"
    
    DATA_ERROR = "DATA_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    
    OBSERVATION_ERROR = "OBSERVATION_ERROR"
    IMAGING_ERROR = "IMAGING_ERROR"
    STACKING_ERROR = "STACKING_ERROR"
    
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_CONFLICT = "AGENT_CONFLICT"
    
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


HTTP_STATUS_CODES: Dict[ErrorCode, int] = {
    ErrorCode.UNKNOWN_ERROR: 500,
    
    ErrorCode.REQUEST_ERROR: 400,
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.MISSING_PARAMETER: 400,
    ErrorCode.INVALID_PARAMETER: 400,
    
    ErrorCode.AUTH_ERROR: 401,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.INVALID_API_KEY: 403,
    ErrorCode.MISSING_API_KEY: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    
    ErrorCode.RESOURCE_ERROR: 404,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.RESOURCE_CONFLICT: 409,
    ErrorCode.RESOURCE_NOT_AVAILABLE: 503,
    
    ErrorCode.LLM_ERROR: 500,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.LLM_CONFIG_ERROR: 500,
    ErrorCode.LLM_UNAVAILABLE: 503,
    ErrorCode.LLM_RATE_LIMITED: 429,
    ErrorCode.LLM_RESPONSE_PARSE_ERROR: 422,
    
    ErrorCode.TELESCOPE_ERROR: 500,
    ErrorCode.TELESCOPE_OFFLINE: 503,
    ErrorCode.TELESCOPE_BUSY: 409,
    ErrorCode.TELESCOPE_NOT_CONNECTED: 503,
    ErrorCode.TELESCOPE_GUIDING_ERROR: 500,
    
    ErrorCode.WORKFLOW_ERROR: 500,
    ErrorCode.NODE_EXECUTION_FAILED: 500,
    ErrorCode.INVALID_WORKFLOW: 400,
    ErrorCode.WORKFLOW_TIMEOUT: 504,
    ErrorCode.WORKFLOW_CANCELLED: 499,
    
    ErrorCode.DATA_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.CACHE_ERROR: 500,
    ErrorCode.DATA_VALIDATION_ERROR: 422,
    
    ErrorCode.OBSERVATION_ERROR: 500,
    ErrorCode.IMAGING_ERROR: 500,
    ErrorCode.STACKING_ERROR: 500,
    
    ErrorCode.AGENT_ERROR: 500,
    ErrorCode.AGENT_TIMEOUT: 504,
    ErrorCode.AGENT_CONFLICT: 409,
    
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.QUOTA_EXCEEDED: 429,
}


class TianwenError(Exception):
    """天问-AGI 基础异常类"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}
        self.retryable = retryable
        self.cause = cause
        self.context = context or {}
        self._log_trace()
    
    def _log_trace(self):
        """记录错误追踪"""
        if self.cause:
            self._trace = "".join(traceback.format_exception(type(self.cause), self.cause, self.cause.__traceback__))
        else:
            self._trace = "".join(traceback.format_exception(type(self), self, self.__traceback__))
    
    @property
    def trace(self) -> str:
        """获取错误追踪"""
        return self._trace
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "detail": self.detail,
                "retryable": self.retryable,
                "context": self.context
            }
        }
    
    def to_user_dict(self) -> Dict[str, Any]:
        """用户友好的错误字典（不包含敏感信息）"""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message
            }
        }
    
    def with_context(self, **kwargs) -> "TianwenError":
        """添加错误上下文"""
        self.context.update(kwargs)
        return self
    
    def with_detail(self, **kwargs) -> "TianwenError":
        """添加错误详情"""
        self.detail.update(kwargs)
        return self


class ValidationError(TianwenError):
    def __init__(
        self, 
        message: str, 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            ErrorCode.INVALID_REQUEST, 
            message, 
            detail,
            cause=cause
        )


class AuthError(TianwenError):
    def __init__(
        self, 
        message: str = "认证失败", 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(ErrorCode.AUTH_ERROR, message, detail, cause=cause)


class ForbiddenError(TianwenError):
    def __init__(
        self, 
        message: str = "权限不足", 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(ErrorCode.FORBIDDEN, message, detail, cause=cause)


class NotFoundError(TianwenError):
    def __init__(
        self, 
        message: str = "资源未找到", 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(ErrorCode.NOT_FOUND, message, detail, cause=cause)


class LLMError(TianwenError):
    def __init__(
        self, 
        message: str = "LLM服务错误", 
        detail: Optional[Dict] = None,
        retryable: bool = True,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            ErrorCode.LLM_ERROR, 
            message, 
            detail,
            retryable=retryable,
            cause=cause
        )


class LLMTimeoutError(LLMError):
    def __init__(self, message: str = "LLM请求超时", cause: Optional[Exception] = None):
        super().__init__(message, retryable=True, cause=cause)
        self.code = ErrorCode.LLM_TIMEOUT


class LLMRateLimitError(LLMError):
    def __init__(self, message: str = "LLM请求频率超限", cause: Optional[Exception] = None):
        super().__init__(message, retryable=True, cause=cause)
        self.code = ErrorCode.LLM_RATE_LIMITED


class TelescopeError(TianwenError):
    def __init__(
        self, 
        message: str = "望远镜控制错误", 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(ErrorCode.TELESCOPE_ERROR, message, detail, cause=cause)


class TelescopeOfflineError(TelescopeError):
    def __init__(self, message: str = "望远镜离线", detail: Optional[Dict] = None):
        super().__init__(message, detail)
        self.code = ErrorCode.TELESCOPE_OFFLINE


class TelescopeBusyError(TelescopeError):
    def __init__(self, message: str = "望远镜忙", detail: Optional[Dict] = None):
        super().__init__(message, detail)
        self.code = ErrorCode.TELESCOPE_BUSY


class WorkflowError(TianwenError):
    def __init__(
        self, 
        message: str = "工作流错误", 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(ErrorCode.WORKFLOW_ERROR, message, detail, cause=cause)


class WorkflowTimeoutError(WorkflowError):
    def __init__(self, message: str = "工作流执行超时", detail: Optional[Dict] = None):
        super().__init__(message, detail)
        self.code = ErrorCode.WORKFLOW_TIMEOUT


class WorkflowCancelledError(WorkflowError):
    def __init__(self, message: str = "工作流已取消", detail: Optional[Dict] = None):
        super().__init__(message, detail)
        self.code = ErrorCode.WORKFLOW_CANCELLED


class DatabaseError(TianwenError):
    def __init__(
        self, 
        message: str = "数据库错误", 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(ErrorCode.DATABASE_ERROR, message, detail, cause=cause)


class RateLimitError(TianwenError):
    def __init__(
        self, 
        message: str = "请求频率超限", 
        detail: Optional[Dict] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(ErrorCode.RATE_LIMITED, message, detail, retryable=True)
        self.retry_after = retry_after


class AgentError(TianwenError):
    def __init__(
        self, 
        message: str = "Agent执行错误", 
        detail: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(ErrorCode.AGENT_ERROR, message, detail, cause=cause)


class AgentTimeoutError(AgentError):
    def __init__(self, message: str = "Agent执行超时", detail: Optional[Dict] = None):
        super().__init__(message, detail)
        self.code = ErrorCode.AGENT_TIMEOUT


class ErrorHandler:
    """错误处理器"""
    
    _logger = logging.getLogger("error-handler")
    
    @classmethod
    def handle(cls, error: Exception, log_level: int = logging.ERROR) -> Dict[str, Any]:
        """统一处理异常"""
        if isinstance(error, TianwenError):
            cls._log(error, log_level)
            return error.to_dict()
        
        cls._logger.log(log_level, f"Unknown error: {error}", exc_info=True)
        return {
            "error": {
                "code": ErrorCode.UNKNOWN_ERROR.value,
                "message": str(error),
                "detail": {},
                "retryable": cls.is_retryable(error)
            }
        }
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """判断错误是否可重试"""
        if isinstance(error, TianwenError):
            return error.retryable
        
        import socket
        if isinstance(error, (socket.timeout, ConnectionError, TimeoutError)):
            return True
        
        return False
    
    @classmethod
    def _log(cls, error: TianwenError, level: int = logging.ERROR):
        """记录错误日志"""
        msg = f"[{error.code.value}] {error.message}"
        if error.context:
            msg += f" | context: {error.context}"
        if error.detail:
            msg += f" | detail: {error.detail}"
        
        cls._logger.log(level, msg)
        if error.cause and level >= logging.WARNING:
            cls._logger.debug(f"Cause: {error.cause}", exc_info=True)


def get_http_status_code(error: TianwenError) -> int:
    """获取HTTP状态码"""
    return HTTP_STATUS_CODES.get(error.code, 500)


def error_handler(
    error_class: Type[TianwenError] = TianwenError,
    log_level: int = logging.ERROR,
    wrap_unknown: bool = True
):
    """错误处理装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except TianwenError:
                raise
            except Exception as e:
                if wrap_unknown:
                    raise error_class(
                        message=str(e),
                        cause=e
                    )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except TianwenError:
                raise
            except Exception as e:
                if wrap_unknown:
                    raise error_class(
                        message=str(e),
                        cause=e
                    )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


class ErrorCollector:
    """错误收集器，用于聚合多个错误"""
    
    def __init__(self):
        self.errors: List[TianwenError] = []
        self.warnings: List[str] = []
    
    def add_error(self, error: TianwenError):
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_errors": self.has_errors(),
            "has_warnings": self.has_warnings(),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }
    
    def raise_if_errors(self):
        """如果存在错误则抛出聚合异常"""
        if self.has_errors():
            raise AggregateError(self.errors, self.warnings)


class AggregateError(TianwenError):
    """聚合错误，包含多个子错误"""
    
    def __init__(self, errors: List[TianwenError], warnings: List[str] = None):
        self.sub_errors = errors
        self.sub_warnings = warnings or []
        
        error_messages = [e.message for e in errors]
        super().__init__(
            ErrorCode.UNKNOWN_ERROR,
            f"Multiple errors occurred: {'; '.join(error_messages)}",
            detail={"error_count": len(errors), "warning_count": len(self.sub_warnings)}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "detail": self.detail,
                "retryable": False,
                "sub_errors": [e.to_dict() for e in self.sub_errors],
                "sub_warnings": self.sub_warnings
            }
        }