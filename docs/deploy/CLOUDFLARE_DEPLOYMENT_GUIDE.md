# Cloudflare Pages Deployment Guide for Tianwen-AGI

## Prerequisites

Before deploying to Cloudflare Pages, ensure you have:

- Cloudflare account (https://dash.cloudflare.com)
- GitHub account with access to the Tianwen-AGI repository
- Backend API deployed (Railway or other platform)
- Custom domain (optional)

---

## Project Structure Analysis

The Tianwen-AGI frontend is a **static single-page application** located in `web/index.html`.

- **Build output directory**: `web/`
- **Build command**: None required (pure static HTML)
- **No frontend build system** (no package.json, no Vite/Webpack config)

---

## Cloudflare Pages Setup

### Step 1: Create Cloudflare Pages Project

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Navigate to **Workers & Pages** > **Create Application**
3. Select **Pages** > **Create a project**
4. Click **Connect to Git**

### Step 2: Connect GitHub Repository

1. Authorize Cloudflare to access your GitHub account
2. Select the `tianwen-agi` repository
3. Configure the project:

| Setting | Value |
|---------|-------|
| **Production branch** | `main` (or your preferred branch) |
| **Build command** | (leave empty - static HTML) |
| **Build output directory** | `/web` |

### Step 3: Configure Build Settings

Since the frontend is a static HTML file with no build process:

1. **Build command**: Leave empty
2. **Build output directory**: `/web`
3. Click **Save and Deploy**

---

## Environment Variable Configuration

The frontend requires `API_BASE` to connect to the backend. Since this is a static site, you have two options:

### Option A: Use Cloudflare Pages Environment Variables (Recommended)

1. In Pages project settings, go to **Settings** > **Environment Variables**
2. Add variable:

| Variable | Value | Notes |
|----------|-------|-------|
| `API_BASE` | `https://your-backend.railway.app/api` | Your deployed backend URL |

3. For production environment, set the production value
4. Redeploy to apply changes

### Option B: Modify web/index.html for Production

Update the `API_BASE` in `web/index.html` (line 311):

```javascript
// Production
const API_BASE = 'https://your-backend.railway.app/api';
```

**Note**: Option A is recommended as it allows the same codebase to work across environments.

---

## Custom Domain Setup (Optional)

### Adding Custom Domain

1. In Pages project settings, go to **Custom Domains**
2. Click **Add custom domain**
3. Enter your domain name (e.g., `agi.yourdomain.com`)
4. Cloudflare will automatically configure DNS
5. Wait for SSL certificate provisioning

### Configuring CNAME Record

If using a subdomain:

```
Type: CNAME
Name: agi (or your subdomain)
Value: your-project.pages.dev
Proxy: Enabled (orange cloud)
```

---

## Post-Deployment Verification

### 1. Verify Frontend Loads

1. Access your Cloudflare Pages URL (e.g., `https://tianwen-agi.pages.dev`)
2. Confirm the page loads without errors
3. Check browser console for any JavaScript errors

### 2. Verify Backend Connectivity

1. Open browser developer console (F12)
2. Check for successful health check log: "Backend connected"
3. If you see "Backend not connected", verify:
   - `API_BASE` environment variable is set correctly
   - Backend service is running and accessible
   - CORS is configured on backend

### 3. Test API Communication

1. Enter a test message in the chat interface
2. Verify the response comes back successfully
3. Check that cognitive engine indicators animate properly

---

## Backend API Configuration

The frontend expects the backend to expose these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check - returns system status |
| `/api/chat` | POST | Send chat message - expects `{message, session_id}` |
| `/api/sessions` | GET | List sessions |
| `/api/cognitive` | GET | Get cognitive engine preview |
| `/api/evolution/stats` | GET | Get evolution system statistics |

### Backend Health Response Expected Format

```json
{
  "status": "ok",
  "version": "2.2.0",
  "timestamp": "2026-05-01T12:00:00.000Z",
  "system": { "memory": {}, "cpu": {}, "process": {} },
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

## Troubleshooting

### Frontend Shows "Backend not connected"

1. Verify `API_BASE` environment variable in Cloudflare Pages settings
2. Ensure backend service is running (Railway deployment active)
3. Check browser console for CORS errors
4. Verify `/api/health` endpoint responds from backend

### CORS Errors

If browser shows CORS errors:

1. Ensure backend has CORS headers configured for Cloudflare Pages domain
2. Check that backend allows requests from your custom domain
3. For development, the backend should allow `localhost` and Cloudflare Pages domains

### Static Assets Not Loading

1. Verify all assets use relative paths OR use correct absolute URLs
2. Check that `web/` is set as the output directory
3. Ensure index.html is in the web/ directory root

---

## Deployment Summary

| Item | Value |
|------|-------|
| **Frontend type** | Static HTML (single file) |
| **Output directory** | `/web` |
| **Build command** | None |
| **Required env vars** | `API_BASE` |
| **Domain SSL** | Automatic via Cloudflare |

---

## Related Documentation

- [Frontend Deployment Checklist](./FRONTEND_DEPLOYMENT_CHECKLIST.md)
- [Railway Backend Deployment Guide](./RAILWAY_DEPLOYMENT_GUIDE.md)