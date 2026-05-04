FROM python:3.11-slim

RUN groupadd -g 1000 pyapp && useradd -u 1000 -g pyapp -m pyapp

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY web /app/web

RUN mkdir -p /app/src/.cache/skyviews && chown -R pyapp:pyapp /app

USER pyapp

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

CMD ["python", "src/server.py"]
