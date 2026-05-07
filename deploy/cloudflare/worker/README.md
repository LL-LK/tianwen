# Tianwen-AGI Cloudflare Worker 部署指南

## 项目结构

```
deploy/cloudflare/worker/
├── wrangler.toml          # Worker 配置
├── wrangler.jsonc         # Cloudflare Pages 配置（已有）
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts           # 入口 & 路由分发
│   ├── types.ts            # Env 类型定义
│   └── routes/
│       ├── chat.ts         # /api/chat → MiniMax 直连
│       ├── railway-proxy.ts # astronomy API → Railway 代理
│       ├── sessions.ts      # /api/sessions → D1 存储
│       ├── rag.ts          # /api/rag → Vectorize 向量搜索
│       ├── hallucination.ts # /api/hallucination → Workers AI
│       ├── llm-test.ts     # /api/llm/test → MiniMax 连接测试
│       └── ping.ts         # /api/ping → 健康检查
└── migrations/
    └── 001_create_sessions.sql  # D1 Schema
```

## 部署步骤

### 1. 创建 D1 数据库

```bash
cd deploy/cloudflare/worker

# 创建 D1 数据库
wrangler d1 create tianwen-agi-sessions
# 返回 database_id，填入 wrangler.toml 的 [[d1_databases]].database_id

# 执行迁移
wrangler d1 execute tianwen-agi-sessions --remote --file=migrations/001_create_sessions.sql
```

### 2. 创建 Vectorize 向量索引

```bash
# 创建 Vectorize 索引（用于 RAG）
wrangler vectorize create tianwen-agi-rag --dimensions=1024 --metric=cosine
# 返回 index_name，填入 wrangler.toml 的 [[vectorize]].index_name
```

### 3. 设置环境变量

```bash
# 设置 MiniMax API Key
wrangler secret put MINIMAX_API_KEY
# 输入你的 MiniMax API Key (sk-cp-...)

# 设置 Group ID
wrangler secret put MINIMAX_GROUP_ID
# 输入你的 MiniMax Group ID (2047585369045603038)
```

### 4. 修改 wrangler.toml

填入真实的 database_id 和 index_name：

```toml
[[d1_databases]]
binding = "DB"
database_name = "tianwen-agi-sessions"
database_id = "填入上一步返回的 database_id"

[[vectorize]]
binding = "VECTORIZE"
index_name = "tianwen-agi-rag"
```

### 5. 部署 Worker

```bash
wrangler deploy
# 部署成功后会返回 worker URL: https://tianwen-agi-worker.<your-subdomain>.workers.dev
```

### 6. 配置自定义域名（可选）

```bash
wrangler route create --domain=tianwen-agi-api.your-domain.com
```

## API 路由映射

| 路由 | 处理方式 | 说明 |
|------|---------|------|
| `/api/chat` | Worker → MiniMax 直连 | 核心对话功能 |
| `/api/llm/test` | Worker → MiniMax 直连 | LLM 连接测试 |
| `/api/ping` | Worker 本地处理 | 健康检查 |
| `/api/sessions/*` | D1 数据库 | 会话历史存储 |
| `/api/rag/*` | Vectorize | RAG 向量搜索 |
| `/api/hallucination/*` | Workers AI | 幻觉检测 |
| `/api/skychart/*` | → Railway 代理 | 星图（astronomy） |
| `/api/telescope/*` | → Railway 代理 | 望远镜控制（astronomy） |
| `/api/observatory/*` | → Railway 代理 | 天文台控制 |
| `/api/research/*` | → Railway 代理 | 研究模块 |
| `/api/hypothesis/*` | → Railway 代理 | 假设生成/测试 |
| `/api/literature/*` | → Railway 代理 | 文献搜索 |
| `/api/alerts/*` | → Railway 代理 | 告警 |
| `/api/workflow-engine/*` | → Railway 代理 | 工作流引擎 |
| `/api/ws/*` | ❌ 不支持 | WebSocket 需 Railway |

## 前端配置

部署后，将前端 `web/index.html` 中的 `BACKEND_URL` 改为：

```javascript
var BACKEND_URL = 'https://tianwen-agi-worker.<your-subdomain>.workers.dev';
var API_BASE = BACKEND_URL + '/api';
```

## 已知限制

1. **WebSocket 不支持**：Railway 后端的 `/ws/*` 端点无法在 Workers 中代理
2. **CPU 时间限制**：免费版每个请求最多 10ms CPU，复杂 LLM 逻辑需付费版
3. **MiniMax API**：Worker 直接调用，需配置 API Key
4. **Vectorize**：RAG 向量搜索需要预先填充数据

## 监控和调试

```bash
# 查看实时日志
wrangler tail

# 查看部署状态
wrangler deployments list
```
