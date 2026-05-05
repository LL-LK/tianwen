#!/bin/sh
set -e

PORT="${PORT:-5000}"

echo "[entrypoint] Starting Tianwen-AGI on port ${PORT}"

exec hypercorn src.server:app \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --backlog 512 \
    --keep-alive 5 \
    --graceful-timeout 30
