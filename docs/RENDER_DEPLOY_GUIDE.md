# Render 部署指南 - Tianwen-AGI

## 架构说明

```
用户浏览器
    ↓
Cloudflare Pages (前端) → https://tianwen-agi.pages.dev
    ↓ (API 请求)
Cloudflare Worker (路由/CORS) → tianwen-agi.xxx.workers.dev
    ↓ (代理)
Render (Python 后端) → https://tianwen-agi-backend.onrender.com
```

---

## 前提条件

- [ ] Render 账号 ([render.com](https://render.com))
- [ ] GitHub 账号，仓库 `LL-LK/tianwen-agi` 已连接
- [ ] GitHub Secrets 配置权限

---

## 步骤 1: Render 端配置

### 方式 A: GitHub 自动部署（推荐）

1. 登录 [render.com](https://render.com)

2. 点击 **New +** → **Web Service**

3. 选择 **Configure account** 连接 GitHub

4. 在列表中找到 `LL-LK/tianwen-agi`，点击 **Connect**

5. 配置 Web Service：

   | 配置项 | 值 |
   |--------|-----|
   | Name | `tianwen-agi-backend` |
   | Region | `Oregon` (离 CF 最近) |
   | Branch | `render-deploy` |
   | Root Directory | (留空) |
   | Runtime | `Python` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `hypercorn src.server:app --bind 0.0.0.0:$PORT --workers 1 --keep-alive 5` |
   | Plan | `Starter` ($7/月) |

6. 点击 **Create Web Service**，开始首次部署

7. 等待部署完成（约 3-5 分钟），记录 URL:
   ```
   https://tianwen-agi-backend.onrender.com
   ```

### 方式 B: render-cli 手动部署

```bash
# 安装 render-cli
npm install -g @render/cli

# 登录
render-cli login

# 进入项目目录
cd /mnt/f/tianwen-agi

# 部署（需先在 Render Dashboard 创建好服务获取 service ID）
render-cli deploy --service <SERVICE_ID> --plan starter
```

---

## 步骤 2: 设置环境变量

在 Render Dashboard → 你的 Web Service → **Environment** tab：

### 必需变量

| Key | Value | 说明 |
|-----|-------|------|
| `DEBUG` | `false` | 生产环境关闭调试 |
| `CORS_ORIGINS` | `https://tianwen-agi.pages.dev` | 前端域名 |
| `PYTHONUNBUFFERED` | `1` | 日志实时输出 |
| `PYTHONDONTWRITEBYTECODE` | `1` | 不生成 .pyc |

### 敏感变量（点击 Raw Editor）

| Key | Value | 说明 |
|-----|-------|------|
| `MINIMAX_API_KEY` | `sk-cp-...` | MiniMax API Key |
| `MINIMAX_GROUP_ID` | `2047585369045603038` | MiniMax Group ID |

### 可选变量

| Key | Value | 说明 |
|-----|-------|------|
| `CHROMA_DB_PATH` | `/data/chroma_db` | 向量数据库路径 |

### 持久化磁盘

在 **Disks** tab：
- Name: `data`
- Mount Path: `/data`
- Size: `1GB`

---

## 步骤 3: 配置 GitHub Secrets

在 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions**：

### 新增 Secret

点击 **New repository secret**，添加：

| Secret Name | Value 来源 |
|-------------|-----------|
| `RENDER_API_KEY` | Render Dashboard → Account Settings → API Keys → Create API Key |
| `RENDER_SERVICE_ID` | Render Dashboard → 你的服务 → Settings → General → Service ID |
| `RENDER_BACKEND_URL` | `https://tianwen-agi-backend.onrender.com`（替换为你的实际 URL）|

获取方式：
- `RENDER_API_KEY`: Render → Account Settings → API Keys → Create API Key
- `RENDER_SERVICE_ID`: Render → tianwen-agi-backend → Settings → Service ID (格式: `srv-xxx`)

---

## 步骤 4: 验证部署

### 本地测试 Render 后端

```bash
curl https://tianwen-agi-backend.onrender.com/api/ping
```

预期响应：
```json
{"status": "ok", "timestamp": "2026-05-06T..."}
```

### 测试 Worker 代理

Cloudflare Worker 更新 `RENDER_BACKEND` 后：

```bash
curl https://tianwen-agi.xxx.workers.dev/api/ping
```

或直接访问前端页面测试完整流程。

---

## 步骤 5: 切换生产流量（可选）

当 Render 后端验证稳定后：

### 方式 A: 通过 Railway 保持热备

保留 Railway 作为备份，将 CF Worker 代理目标切换到 Render：

1. Cloudflare Dashboard → Workers & Pages → 你的 Worker
2. Settings → Variables → `RENDER_BACKEND` 设置为 Render URL
3. 测试通过后，Traffic 100% 指向 Render

### 方式 B: 完全切换

1. 在 Render Dashboard 确认服务正常运行
2. Railway → 停止服务（不会删除数据）
3. CF Worker → 确保 `RENDER_BACKEND` 生效

---

## 成本对比

| 平台 | 费用 | 说明 |
|------|------|------|
| Railway | ~$5-20/月 | 按实际使用计费 |
| Render Starter | **$7/月** | 固定费用，1GB 磁盘 |
| CF Worker | **免费** | 100k 请求/天免费额度 |
| CF D1 | **免费** | 5GB 存储 |
| CF Vectorize | **免费** | 100k vectors |

**总计**: $7/月（Render） + Cloudflare 免费额度

---

## 故障排查

### Render 部署失败

```bash
# 查看构建日志
# Render Dashboard → 你的服务 → Logs

# 常见问题：
# 1. requirements.txt 缺少依赖 → 本地测试 pip install
# 2. 端口配置错误 → 确保 PORT 环境变量存在
# 3. 磁盘路径不存在 → /data 需通过 Disks 配置
```

### 后端启动超时

Render Starter Plan 冷启动约 30 秒。如健康检查超时：
- 在 `render.yaml` 增加 `healthCheckPath` 等待时间
- 或临时将健康检查路径改为 `/`（修改 `server.py` 临时兼容）

### CORS 问题

确保 `CORS_ORIGINS` 包含前端地址：
```
https://tianwen-agi.pages.dev
```

### Worker 502

检查：
1. Render 后端是否正常运行 → `https://tianwen-agi-backend.onrender.com/api/ping`
2. Worker `RENDER_BACKEND` 是否正确设置
3. Render 是否允许外部访问 → Settings → Networking → Allow internal services

---

## 回滚方案

如需回滚到 Railway：

1. Railway Dashboard → 重启服务
2. 修改 `wrangler.toml` 中 `RENDER_BACKEND` → `RAILWAY_BACKEND`
3. `wrangler deploy`
4. 或在 CF Dashboard 直接修改变量

---

## 附录: Render vs Railway 对比

| 特性 | Render | Railway |
|------|--------|---------|
| 冷启动 | ~30s | ~10s |
| 磁盘支持 | 有 ($/GB) | 有 ($/GB) |
| 私密环境变量 | 是 | 是 |
| 自动部署 | GitHub 自动 | GitHub 自动 |
| Python 支持 | 原生 | 原生 |
| 免费额度 | $0 | $5/月 |
| 启动超时 | 60s | 30s |
| 社区 | 较小 | 成熟 |

