FROM python:3.11-slim

RUN groupadd -g 1000 pyapp && useradd -u 1000 -g pyapp -m pyapp

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY web /app/web
COPY docker-entrypoint.sh /app/

RUN chmod +x /app/docker-entrypoint.sh

RUN mkdir -p /app/runtime/data/workflows \
    && mkdir -p /app/runtime/data/chroma_db \
    && mkdir -p /app/src/.cache/skyviews \
    && chown -R pyapp:pyapp /app

ENV DEBUG=false
ENV CORS_ORIGINS="https://tianwen-agi.pages.dev"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=5000

USER pyapp

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:${PORT:-5000}/api/ping || exit 1

CMD ["/app/docker-entrypoint.sh"]
