# Railway Deployment Guide for Tianwen-AGI

## Prerequisites

Before deploying to Railway, ensure you have:

- Railway account (https://railway.app)
- GitHub account with access to the Tianwen-AGI repository
- DeepSeek API key (for LLM inference)
- Optional: Qwen endpoint configuration

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API authentication key | Yes |
| `QWEN_ENDPOINT` | Qwen API endpoint | No (defaults to Alibaba DashScope) |
| `PORT` | Server port (Railway sets this automatically) | No (auto-detected) |

---

## Railway Project Setup

### Step 1: Create New Railway Project

1. Log in to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"** button
3. Select **"Deploy from GitHub"**
4. Authorize Railway to access your GitHub account
5. Select the `tianwen-agi` repository

### Step 2: Configure Build Settings

1. In the project settings, set the following:
   - **Build Command**: `docker-compose build` or leave blank (uses Dockerfile)
   - **Start Command**: `docker-compose up` or `python runtime/server.py`

2. For single-service deployment (recommended):
   - **Start Command**: `python runtime/server.py`

### Step 3: Configure Environment Variables

1. Navigate to **Variables** tab in project settings
2. Add the following variables:

```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
QWEN_ENDPOINT=https://dashscope.aliyuncs.com/api/v1
PORT=5000
```

---

## GitHub Connection Steps

### Option A: Automatic Deployment (Recommended)

1. Push your code to GitHub
2. Railway automatically detects the `Dockerfile` and `docker-compose.yml`
3. Enable **Automatic Deployments** in Railway project settings
4. Every push to `main` branch triggers a new deployment

### Option B: Manual Deployment

1. Connect GitHub repository in Railway
2. Click **Deploy** button on the project dashboard
3. Select the branch to deploy

---

## Health Check Verification

The application exposes a health endpoint at `/api/health`.

### Local Testing

```bash
# Start the server locally
python runtime/server.py

# Check health endpoint
curl http://localhost:5000/api/health
```

### Railway Health Check Configuration

In Railway, configure the health check:

- **Health Check Path**: `/api/health`
- **Health Check Port**: `5000`
- **Timeout**: 30 seconds

### Expected Health Response

```json
{
  "status": "ok",
  "version": "2.2.0",
  "timestamp": "2026-05-01T12:00:00.000Z",
  "system": {
    "memory": { ... },
    "cpu": { ... },
    "process": { ... }
  },
  "dependencies": {
    "agent_initialized": true,
    "cognitive_engine": true,
    "planning_engine": true,
    "execution_engine": true,
    "evolution_system": true
  }
}
```

---

## Railway-Specific Configuration

### Using Dockerfile (Recommended)

The existing `Dockerfile` is optimized for Railway:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY runtime/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "runtime/server.py"]
```

### Railway Detection

Railway automatically detects:
- Dockerfile for container builds
- `docker-compose.yml` for multi-service deployments
- `runtime/requirements.txt` for Python dependencies

### Multi-Service Deployment (with ChromaDB)

For deployments requiring vector search:

1. Deploy using `docker-compose.yml`
2. Railway will provision both `server` and `vector-db` services
3. Ensure `CHROMA_HOST` and `CHROMA_PORT` are set correctly

### Single-Service Deployment (Simpler)

For basic chat functionality without vector search:

1. Set start command: `python runtime/server.py`
2. ChromaDB dependency is optional in this mode

---

## Troubleshooting

### Container Fails to Start

1. Check logs in Railway dashboard
2. Verify environment variables are set correctly
3. Ensure `PORT` variable matches container expose port

### Health Check Fails

1. Verify the server is listening on `0.0.0.0` (not `localhost`)
2. Check that `PORT` environment variable is set
3. Verify `/api/health` endpoint returns 200

### Out of Memory Errors

1. Upgrade Railway plan to higher memory tier
2. Reduce model cache size
3. Disable optional features

### Dependency Installation Fails

1. Check `runtime/requirements.txt` for invalid packages
2. Ensure packages are available on PyPI
3. Try building with longer timeout

### Common Error Messages

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError` | Check requirements.txt is copied correctly |
| `Connection refused` | Verify PORT environment variable |
| `Health check timeout` | Increase health check timeout in Railway settings |

---

## Notes

- Railway automatically sets the `PORT` environment variable
- The health endpoint requires `psutil` package (included in requirements.txt)
- ChromaDB requires persistent storage for production use
- DeepSeek API key should never be committed to GitHub
