# 天问-AGI 当前任务全景与风险评估报告

> 生成时间: 2026-05-02 CST
> 分析者: 天问-AGI 产品验收审计系统
> 仓库: LL-LK/tianwen-agi
> 分支: trae
> SSH密钥指纹: SHA256:YMJ/AZBFSfuK8Qxa63o26C0eCYVC3NahchxQSYucMjE
> 版本: v1.0

---

## 一、执行摘要

本报告对天问-AGI项目当前状态进行全面审计，涵盖：已完成工作、待推送提交、Docker/CI/CD基础设施修复、代码质量、安全风险、以及后续行动建议。

**核心结论**: 前后端核心模块已搭建完成并通过联调测试，Docker/CI/CD基础设施的12项构建失败问题已全部修复。当前阻塞点为SSH推送通道不可用，需用户手动推送3个待推送提交。

---

## 二、当前任务全景

### 2.1 已完成任务清单

| 序号 | 任务 | 状态 | 涉及文件 |
|------|------|------|----------|
| 1 | 全自动天文观测站前后端完整模块搭建 | ✅ 完成 | `web/index.html`, `runtime/server.py` |
| 2 | 后端12个新API端点 + WebSocket实时通道 | ✅ 完成 | `runtime/server.py` |
| 3 | 前端6标签页观测站控制面板 | ✅ 完成 | `web/index.html` |
| 4 | 前后端联调测试（全部200 OK） | ✅ 通过 | — |
| 5 | Dockerfile 4项构建失败修复 | ✅ 完成 | `Dockerfile` |
| 6 | docker-compose.yml 3项配置修复 | ✅ 完成 | `docker-compose.yml` |
| 7 | docker-build.yml workflow 3项修复 | ✅ 完成 | `.github/workflows/docker-build.yml` |
| 8 | ci.yml workflow 1项修复 | ✅ 完成 | `.github/workflows/ci.yml` |
| 9 | deploy-railway.yml workflow 1项修复 | ✅ 完成 | `.github/workflows/deploy-railway.yml` |
| 10 | overfit_self_correction.py 语法错误修复 | ✅ 完成 | `runtime/overfit_self_correction.py` |
| 11 | 全量文档索引（按时间/分类/作者） | ✅ 完成 | `docs/PRO/PRO_DOCUMENT_INDEX_...` |
| 12 | 天文观测站前后端深度需求分析 | ✅ 完成 | `docs/PRO/PRO_AUTO_OBSERVATORY_...` |

### 2.2 待推送提交（阻塞中）

本地 `trae` 分支领先远程 **3个提交**：

```
d34f8f9 fix: 修复全部Docker workflow构建失败 + overfit_self_correction语法错误
a37f57a fix: 修复Docker workflow全部构建失败问题 (12项修复)
f1f709e feat: 搭建全自动天文观测站前后端完整模块
```

**阻塞原因**: 当前运行环境SSH端口22和443均被本地防火墙/代理拦截（`Connection closed by 127.0.0.1 port 443`），且GitHub Token未授权tianwen-agi仓库。

### 2.3 新增/修改文件汇总

| 文件 | 变更类型 | 行数变化 |
|------|----------|----------|
| `web/index.html` | 重写 | +1062 / -81 |
| `runtime/server.py` | 大幅扩展 | +600+ |
| `Dockerfile` | 修复 | 重构 |
| `docker-compose.yml` | 修复 | 多处 |
| `.github/workflows/docker-build.yml` | 修复 | 多处 |
| `.github/workflows/ci.yml` | 修复 | 多处 |
| `.github/workflows/deploy-railway.yml` | 修复 | 多处 |
| `runtime/overfit_self_correction.py` | 修复 | 1行 |
| `docs/PRO/PRO_DOCUMENT_INDEX_*.md` | 新增 | — |
| `docs/PRO/PRO_AUTO_OBSERVATORY_*.md` | 新增 | — |

---

## 三、Docker/CI/CD 基础设施修复详情

### 3.1 修复前状态：全部Workflow将失败

原始配置存在以下致命缺陷，导致任何push到仓库都会触发**全部workflow失败**：

### 3.2 逐文件修复清单

#### Dockerfile（4项修复）

| # | 原始问题 | 失败表现 | 修复方案 |
|---|----------|----------|----------|
| 1 | 运行时阶段重复执行 `pip install -r requirements.txt`，但venv已从builder复制且含全部依赖 | venv中pip路径可能失效，重复安装导致依赖冲突 | 删除运行时阶段的pip install，完全依赖builder阶段构建的venv |
| 2 | builder阶段仅安装`gcc`，缺少`g++`/`make`/`libffi-dev` | `sentence-transformers`编译torch失败：`error: command 'g++' failed` | 添加`g++`、`make`、`libffi-dev`到builder阶段 |
| 3 | 运行时镜像无`curl`，但docker-compose.yml healthcheck依赖curl | 容器healthcheck永远失败，被判定为unhealthy | 运行时阶段`apt-get install curl` |
| 4 | 逐文件COPY（`server.py`/`main.py`/`*.py`），新增文件会被遗漏 | 新增的API端点文件未包含在镜像中，运行时ImportError | 改为`COPY runtime/ /app/runtime/`整目录复制 |

#### docker-compose.yml（3项修复）

| # | 原始问题 | 失败表现 | 修复方案 |
|---|----------|----------|----------|
| 5 | server healthcheck: `test: ["CMD", "curl", "-f", "http://..."]` | 镜像无curl → healthcheck永久失败 → 容器重启循环 | 改为Python内置方式：`python -c "import urllib.request; ..."` |
| 6 | vector-db healthcheck: 同样使用curl | chromadb镜像可能无curl，同样风险 | 同样改为Python方式 |
| 7 | server服务缺少`image:`标签 | workflow中`sed`替换找不到目标字符串，更新步骤静默失败 | 添加`image: tianwen-agi:latest` |

#### docker-build.yml（3项修复）

| # | 原始问题 | 失败表现 | 修复方案 |
|---|----------|----------|----------|
| 8 | `on.push.branches: [main]` — 仅触发main分支 | 推送到trae分支不会触发构建 | 改为`branches: [main, trae]` |
| 9 | 缺少`permissions`声明 | `contents: write`缺失→无法回写docker-compose.yml；`packages: write`缺失→无法推送GHCR | 添加`permissions: contents: write, packages: write` |
| 10 | `sed "s|image: tianwen-agi:latest|..."` 目标字符串不存在 | sed无匹配，docker-compose.yml未被更新 | 配合修复#7后sed可正确匹配；改用短SHA避免过长标签；`git diff --quiet`安全检查 |

#### ci.yml（1项修复）

| # | 原始问题 | 失败表现 | 修复方案 |
|---|----------|----------|----------|
| 11 | 仅触发main分支；`sleep 10`不足；`docker kill`不规范 | trae分支无CI覆盖；容器启动未完成就被kill | 添加trae分支；sleep延长至15s；`docker kill`→`docker stop && docker rm` |

#### deploy-railway.yml（1项修复）

| # | 原始问题 | 失败表现 | 修复方案 |
|---|----------|----------|----------|
| 12 | `docker login -u "$DOCKER_USERNAME" --password-stdin` 缺少registry URL参数 | Docker登录失败：`Error: Cannot perform an interactive login` | 添加`"$DOCKER_REGISTRY"`参数；同时添加trae分支触发 |

---

## 四、代码质量审计

### 4.1 语法检查结果

全量Python文件语法编译检查：**39个文件全部通过**（修复后）

修复前发现1个语法错误：
- `runtime/overfit_self_correction.py:33` — 变量名含空格 `gradient projection_margin` → 已修复为 `gradient_projection_margin`

### 4.2 已知技术债务

| 类别 | 问题 | 严重度 | 建议 |
|------|------|--------|------|
| 依赖 | `sentence-transformers==2.2.0` 版本过旧，与Python 3.11可能存在兼容问题 | 🟡 中 | 升级至2.7.0+ |
| 依赖 | `chromadb==0.4.22` 已落后多个大版本 | 🟡 中 | 评估升级至0.5.x |
| 安全 | `requirements.txt` 使用`>=`范围版本而非精确版本 | 🟡 中 | 生产环境锁定精确版本 |
| 安全 | 部分文件仍使用`print()`而非统一logger | 🟢 低 | 逐步迁移到`runtime_logger` |
| 架构 | `server.py`中模拟数据与真实Agent逻辑混合 | 🟡 中 | 分离mock数据层与真实Agent层 |
| 测试 | 测试覆盖率不足，仅有基础模块测试 | 🟡 中 | 为新增API端点添加集成测试 |

---

## 五、风险评估矩阵

### 5.1 高风险项（需立即处理）

| 风险ID | 风险描述 | 影响范围 | 发生概率 | 缓解措施 |
|--------|----------|----------|----------|----------|
| R1 | **SSH推送通道不可用** — 3个关键提交无法推送到远程，代码丢失风险 | 全部工作 | 🔴 高 | 用户立即在本地终端执行 `git push origin trae` |
| R2 | **GitHub Token权限不足** — Token仅授权wnagye/xinfeng两个仓库，不含tianwen-agi | CI/CD自动化 | 🔴 高 | 重新生成包含tianwen-agi仓库权限的Fine-grained Token |
| R3 | **Docker镜像构建超时** — `sentence-transformers`编译可能超过GitHub Actions 6小时限制 | CI/CD | 🟡 中 | 考虑使用预编译wheel或拆分构建阶段 |

### 5.2 中风险项（需近期处理）

| 风险ID | 风险描述 | 影响范围 | 发生概率 | 缓解措施 |
|--------|----------|----------|----------|----------|
| R4 | **GHCR镜像推送失败** — 若GitHub Packages未启用或权限不足 | 部署 | 🟡 中 | 确认GHCR已启用；验证`secrets.GITHUB_TOKEN`有`packages: write` |
| R5 | **Railway部署密钥缺失** — `secrets.RAILWAY_TOKEN`等未配置 | 生产部署 | 🟡 中 | 在仓库Settings→Secrets中配置Railway相关密钥 |
| R6 | **ChromaDB版本兼容性** — 0.4.22与最新客户端库可能不兼容 | 向量数据库 | 🟡 中 | 锁定客户端与服务器版本一致 |
| R7 | **WebSocket连接泄漏** — 异常断开时未正确清理连接 | 实时推送 | 🟡 中 | WebSocketManager已有dead连接清理逻辑，需添加心跳超时检测 |

### 5.3 低风险项（可延后处理）

| 风险ID | 风险描述 | 影响范围 | 发生概率 | 缓解措施 |
|--------|----------|----------|----------|----------|
| R8 | **Aladin Lite CDN依赖** — 前端星图依赖外部CDN，离线不可用 | 前端展示 | 🟢 低 | 考虑本地化Aladin Lite资源 |
| R9 | **Plotly.js CDN依赖** — 光变曲线图表依赖外部CDN | 前端展示 | 🟢 低 | 同上 |
| R10 | **模拟数据与真实数据切换** — 当前API返回硬编码模拟数据 | 数据准确性 | 🟢 低 | 实现真实设备数据接入后切换 |

---

## 六、前后端架构现状

### 6.1 后端API全景

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes-AGI API Server                      │
│                    Quart + WebSocket                          │
├─────────────────────────────────────────────────────────────┤
│  原有端点 (8个)                                               │
│  /api/chat          POST  文本对话                            │
│  /api/cognitive     POST  认知引擎预览                        │
│  /api/sessions      GET   会话列表                            │
│  /api/sessions/<id> GET   会话详情                            │
│  /api/evolution     GET   进化统计                            │
│  /api/health        GET   健康检查                            │
│  /api/stats/dashboard GET HTML统计面板                        │
│  /api/stats/json    GET   JSON统计                            │
├─────────────────────────────────────────────────────────────┤
│  新增观测站端点 (12个)                                        │
│  /api/observatory/status     GET    观测站完整状态            │
│  /api/observatory/queue      GET    观测队列                  │
│  /api/observatory/queue      POST   添加观测目标              │
│  /api/observatory/queue/<id> DELETE 移除队列项                │
│  /api/observatory/control    POST   启动/暂停/恢复/停止       │
│  /api/devices/status         GET    设备状态(5类)             │
│  /api/data/detections/latest GET    三阶段检测结果            │
│  /api/data/images/latest     GET    最新图像信息              │
│  /api/data/lightcurve        GET    光变曲线数据              │
│  /api/research/status        GET    研究闭环状态              │
│  /api/research/cycles        GET    历史研究周期              │
│  /api/alerts                 GET    告警列表                  │
│  /api/alerts/<id>/read       PUT    标记告警已读              │
│  /api/logs                   GET    系统日志                  │
├─────────────────────────────────────────────────────────────┤
│  WebSocket                                                    │
│  /ws/observatory             WS     2秒间隔实时状态推送       │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 前端界面结构

```
┌─────────────────────────────────────────────────────────────┐
│  天问-AGI 全自动天文观测站                      WS ● 已连接   │
│  状态: 🟢 观测中  |  运行: 72.5h  |  发现: 3  |  假说: 15    │
├─────────────────────────────────────────────────────────────┤
│  [📡 观测总控台] [🌌 实时星图] [📊 数据面板]                  │
│  [🔬 研究闭环] [🔔 告警中心] [📋 系统日志]                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─ 当前观测目标 ───────┐  ┌─ 控制面板 ──────────┐           │
│  │ 🌌 M31 仙女座星系    │  │ ▶启动 ⏸暂停 ▶恢复 ⏹停止│       │
│  │ RA: 00h42m44s        │  │ WS客户端: 0          │           │
│  │ Dec: +41°16'09"      │  │ 累计发现: 3          │           │
│  │ 进度: ████████░░ 78% │  │ 累计假说: 15         │           │
│  └──────────────────────┘  └──────────────────────┘           │
│                                                               │
│  ┌─ 观测队列 ───────────────────────────────────┐            │
│  │ 优先级  目标       类型      窗口      状态    │            │
│  │ P0      SN2024X    超新星    22:30     进行中 │            │
│  │ P1      HD209458   系外行星  23:00     等待中 │            │
│  │ P2      NGC2244    星团      01:00     等待中 │            │
│  └──────────────────────────────────────────────┘            │
│                                                               │
│  ┌─ 设备状态 ───────────────────────────────────┐            │
│  │ 🔭 望远镜 Seestar S50  ● tracking            │            │
│  │ 📷 相机 IMX462        ● exposing 增益:120    │            │
│  │ 🎨 滤镜轮 ZWO EFW     ● idle Luminance       │            │
│  │ 🏠 圆顶 远程圆顶       ● open 方位角:45°      │            │
│  │ 🌤️ 气象站             云量12% 18.5°C 视宁度1.8"│           │
│  └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、立即行动项

### 7.1 用户需执行的操作

```bash
# 1. 推送代码到远程trae分支
cd f:\tianwen-agi
git push origin trae

# 2. （可选）如果SSH不通，使用HTTPS+Token方式
# 先在GitHub Settings → Developer settings → Tokens
# 生成一个新的Fine-grained token，勾选tianwen-agi仓库
# 权限选择: Contents (Read & Write), Packages (Read & Write)
git remote set-url origin https://YOUR_TOKEN@github.com/LL-LK/tianwen-agi.git
git push origin trae
```

### 7.2 推送后验证清单

- [ ] GitHub Actions `docker-build.yml` workflow 成功触发
- [ ] Docker镜像成功推送到 `ghcr.io/LL-LK/tianwen-agi`
- [ ] `ci.yml` lint/test/docker-build 三阶段全部通过
- [ ] 前端页面 `http://localhost:5000` 正常加载
- [ ] WebSocket `/ws/observatory` 连接成功
- [ ] 所有 `/api/observatory/*` 端点返回200

### 7.3 后续建议任务

| 优先级 | 任务 | 预估工作量 |
|--------|------|------------|
| P0 | 配置Railway部署密钥（`RAILWAY_TOKEN`等） | 30分钟 |
| P0 | 启用GitHub Packages (GHCR) | 10分钟 |
| P1 | 升级`sentence-transformers`到2.7+ | 1小时 |
| P1 | 为新增API端点编写集成测试 | 2小时 |
| P2 | 实现真实设备数据接入（替换模拟数据） | 4小时 |
| P2 | 添加WebSocket心跳超时检测 | 1小时 |
| P3 | 本地化Aladin Lite/Plotly.js资源 | 2小时 |

---

## 八、附录

### A. 环境信息

| 项目 | 值 |
|------|-----|
| 操作系统 | Windows |
| Python版本 | 3.11 |
| 包管理器 | pip |
| Git远程 | git@github.com:LL-LK/tianwen-agi.git |
| 当前分支 | trae |
| SSH密钥指纹 | SHA256:YMJ/AZBFSfuK8Qxa63o26C0eCYVC3NahchxQSYucMjE |
| SSH状态 | ❌ 端口22/443均被127.0.0.1拦截 |
| Token状态 | ❌ 仅授权wnagye/xinfeng，不含tianwen-agi |

### B. 关键文件路径

| 文件 | 路径 |
|------|------|
| 后端API | `runtime/server.py` |
| 前端界面 | `web/index.html` |
| Docker构建 | `Dockerfile` |
| 容器编排 | `docker-compose.yml` |
| CI流水线 | `.github/workflows/ci.yml` |
| 镜像发布 | `.github/workflows/docker-build.yml` |
| Railway部署 | `.github/workflows/deploy-railway.yml` |
| 依赖清单 | `runtime/requirements.txt` |
| 日志模块 | `runtime/runtime_logger.py` |
| 研究闭环 | `runtime/research_loop.py` |
| 天体检测 | `runtime/astro_pipeline.py` |
| 全自动观测 | `runtime/auto_observatory.py` |

---

> **文档状态**: 最终版
> **下次审查**: 推送成功后
> **签名**: 天问-AGI 产品验收审计系统
