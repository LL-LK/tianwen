# Tianwen-AGI Frontend Deployment Checklist

## Pre-Deployment Checks

### Repository & Code
- [ ] Code is committed to GitHub repository
- [ ] `web/index.html` exists and is properly formatted
- [ ] No hardcoded credentials or API keys in frontend code
- [ ] `.gitignore` excludes sensitive files

### Backend Coordination
- [ ] Backend API is deployed and accessible
- [ ] Backend health endpoint responds correctly
- [ ] `API_BASE` URL is determined for production
- [ ] CORS is configured on backend for frontend domain

### Environment Configuration
- [ ] `API_BASE` environment variable is ready
- [ ] Backend supports all required endpoints:
  - [ ] `GET /api/health`
  - [ ] `POST /api/chat`
  - [ ] `GET /api/sessions`
  - [ ] `GET /api/cognitive`
  - [ ] `GET /api/evolution/stats`

---

## Build Verification (Pre-Deployment)

### Local Testing
- [ ] Open `web/index.html` in a browser
- [ ] Verify page loads without JavaScript errors
- [ ] Check browser console for any warnings
- [ ] Confirm health check passes locally

### API Connectivity Test
- [ ] Verify chat functionality works with local backend
- [ ] Test quick action buttons (代码生成, 架构设计, etc.)
- [ ] Confirm session persistence works
- [ ] Check cognitive engine indicators animate properly

### Build Output Verification
- [ ] Confirm `web/` directory contains:
  - [ ] `index.html` (main entry point)
  - [ ] Any static assets (CSS, JS, images)
- [ ] No build step required (static HTML)

---

## Cloudflare Setup Steps

### 1. Cloudflare Account Setup
- [ ] Log in to Cloudflare Dashboard
- [ ] Verify email and account is active

### 2. Pages Project Creation
- [ ] Navigate to Workers & Pages > Create Application
- [ ] Select Pages > Connect to Git
- [ ] Authorize GitHub access
- [ ] Select `tianwen-agi` repository
- [ ] Configure project settings:
  - Production branch: `main`
  - Build command: (empty)
  - Build output directory: `/web`

### 3. Environment Variables
- [ ] Go to Settings > Environment Variables
- [ ] Add `API_BASE` for production
- [ ] Value: `https://your-backend.railway.app/api` (your actual backend URL)

### 4. Deploy
- [ ] Save settings
- [ ] Trigger deployment
- [ ] Wait for deployment to complete

---

## Post-Deployment Verification

### Basic Functionality
- [ ] Frontend loads at Cloudflare Pages URL
- [ ] No JavaScript errors in browser console
- [ ] Page title displays correctly: "天问-AGI 智能体"

### Backend Connectivity
- [ ] Browser console shows "Backend connected"
- [ ] Health check succeeds (green engine icons)
- [ ] Chat messages can be sent and responses received

### Feature Verification
- [ ] Quick test buttons work (代码生成, 架构设计, etc.)
- [ ] Engine status indicators show active state
- [ ] Session persistence works across page reloads

### Custom Domain (if configured)
- [ ] Domain resolves correctly
- [ ] SSL certificate is active (green padlock)
- [ ] All functionality works on custom domain

---

## Rollback Procedures

### Quick Rollback on Cloudflare
1. Navigate to Cloudflare Pages dashboard
2. Select the project
3. Go to Deployments
4. Find the previous working deployment
5. Click "Retry deployment" for that version

### Alternative: Revert via Git
1. Identify the last working commit
2. Push a revert commit or checkout previous state
3. Cloudflare automatically redeploys

---

## Monitoring

### Cloudflare Dashboard
- [ ] Monitor deployment status
- [ ] Check for any failed deployments
- [ ] Review build logs if deployment fails

### Application Monitoring
- [ ] Monitor frontend loads correctly
- [ ] Verify backend connectivity remains active
- [ ] Check for any JavaScript errors in production

---

## Contacts & Resources

- Cloudflare Pages Docs: https://developers.cloudflare.com/pages
- Cloudflare Community: https://community.cloudflare.com
- Cloudflare Status: https://www.cloudflarestatus.com

---

## Deployment Summary

| Item | Status |
|------|--------|
| Frontend type | Static HTML |
| Output directory | `/web` |
| Build required | No |
| Environment variables | `API_BASE` |
| Custom domain support | Yes |
| SSL automatic | Yes |