# =============================================================================
# Stage 1: Builder - Install dependencies and prepare wheels
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first
COPY requirements.txt /app/

# Install Python dependencies in user space
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# =============================================================================
# Stage 2: Runtime - Minimal image with runtime user
# =============================================================================
FROM python:3.11-slim

# Create non-root user for security (CIS Docker Benchmark)
RUN groupadd -g 1000 pyapp && useradd -u 1000 -g pyapp -m pyapp

WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=builder /app/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy only necessary files (multi-stage optimization)
COPY requirements.txt /app/
COPY src /app/src
COPY web /app/web

# Install runtime dependencies only
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create cache directory and set permissions for non-root user
RUN mkdir -p /app/src/.cache/skyviews && chown -R pyapp:pyapp /app/src/.cache

# Switch to non-root user
USER pyapp

# Expose port
EXPOSE 5000

# Health check (CIS Docker Benchmark)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

# Run as non-root user
CMD ["python", "src/server.py"]
