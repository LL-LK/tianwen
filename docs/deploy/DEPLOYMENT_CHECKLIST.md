# Tianwen-AGI Deployment Checklist

## Pre-Deployment Checks

### Repository Checks
- [ ] Code is committed to GitHub repository
- [ ] All sensitive data (.env, credentials) are in .gitignore
- [ ] No hardcoded API keys in source code

### Environment Variables
- [ ] DeepSeek API key obtained and ready
- [ ] Qwen endpoint configured (if using)
- [ ] All required environment variables documented

### Docker Configuration
- [ ] Dockerfile builds successfully locally
- [ ] docker-compose.yml tested locally (if using)
- [ ] Health check endpoint responds correctly
- [ ] PORT variable is properly handled

### Code Quality
- [ ] All Python imports work correctly
- [ ] No syntax errors in runtime/server.py
- [ ] Health endpoint returns proper JSON structure
- [ ] Required packages listed in requirements.txt

---

## Deployment Steps

### 1. Prepare Railway Account
- [ ] Log in to Railway at https://railway.app
- [ ] Account is verified and has billing set up (or using free tier)

### 2. Create Railway Project
- [ ] Click "New Project"
- [ ] Select "Deploy from GitHub"
- [ ] Authorize GitHub access
- [ ] Select tianwen-agi repository

### 3. Configure Project Settings
- [ ] Set build command (if needed)
- [ ] Set start command: `python runtime/server.py`
- [ ] Configure health check path: `/api/health`
- [ ] Configure health check port: `5000`

### 4. Add Environment Variables
- [ ] Add `DEEPSEEK_API_KEY`
- [ ] Add `QWEN_ENDPOINT` (if needed)
- [ ] Verify `PORT` is set to `5000`

### 5. Deploy
- [ ] Trigger initial deployment
- [ ] Wait for build to complete
- [ ] Wait for service to start

---

## Post-Deployment Verification

### Health Check Verification
- [ ] Access https://your-app.railway.app/api/health
- [ ] Response status is "ok"
- [ ] All dependencies show as initialized
- [ ] System resources are reported

### Functional Testing
- [ ] Test POST /api/chat endpoint
- [ ] Test GET /api/sessions endpoint
- [ ] Test GET /api/cognitive endpoint (preview mode)
- [ ] Test GET /api/evolution/stats endpoint

### Performance Verification
- [ ] Response time is acceptable
- [ ] Memory usage is within limits
- [ ] No memory leaks during extended use

### Security Verification
- [ ] API key is not exposed in responses
- [ ] Health endpoint does not leak sensitive info
- [ ] CORS is configured appropriately

---

## Rollback Procedures

### Quick Rollback (Railway)
1. Navigate to Railway project dashboard
2. Click on the previous working deployment
3. Click "Redeploy" button
4. Confirm rollback

### Rollback via GitHub
1. Identify last working commit hash
2. Push a revert commit or checkout previous commit
3. Railway auto-deploys the previous state

### Emergency Rollback
If the service is unresponsive:
1. Log in to Railway dashboard
2. Navigate to the working deployment
3. Click "Edit" then "Redeploy"
4. Wait for redeployment to complete

### Manual Rollback (SSH access)
```bash
# Not available on Railway hobby tier
# Requires Railway Pro plan for SSH access
```

---

## Monitoring

### Railway Dashboard
- [ ] Monitor deployment logs
- [ ] Monitor resource usage (CPU, Memory)
- [ ] Set up deployment notifications

### Application Monitoring
- [ ] Monitor /api/health endpoint
- [ ] Set up external monitoring (optional)
- [ ] Configure alert thresholds

### Logs
- [ ] Know how to access Railway deployment logs
- [ ] Know how to search logs for errors
- [ ] Set log retention expectations

---

## Contacts & Escalation

- Railway Support: https://railway.app/help
- Documentation: https://docs.railway.app
- Status Page: https://railway.app/status
