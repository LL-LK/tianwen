"""
Middleware package for server.py
Extracts: cors, security, auth, rate_limit
"""

from .cors import add_cors_headers, add_cache_headers, _generate_etag
from .security import (
    add_security_headers,
    bad_request,
    not_found,
    method_not_allowed,
    internal_error
)
from .auth import require_api_key
from .rate_limit import _check_rate_limit, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX_REQUESTS

__all__ = [
    'add_cors_headers',
    'add_cache_headers',
    '_generate_etag',
    'add_security_headers',
    'bad_request',
    'not_found',
    'method_not_allowed',
    'internal_error',
    'require_api_key',
    '_check_rate_limit',
    'RATE_LIMIT_WINDOW',
    'RATE_LIMIT_MAX_REQUESTS',
]