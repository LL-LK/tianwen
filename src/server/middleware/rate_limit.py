"""
Rate Limiting Middleware
Extracted from server.py lines 144-146, 300-309
"""

import logging
import os
import time
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger("hermes_agi")

RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", 60))
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 30))
_rate_limit_store: dict = defaultdict(list)


def _check_rate_limit(client_ip: str) -> bool:
    """Check if client IP has exceeded rate limit"""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    _rate_limit_store[client_ip].append(now)
    return True