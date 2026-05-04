# PRO文档: 全自动离线天文观测望远镜实施计划

## Issue: #78 - [P0] 全自动离线天文观测望远镜实施计划 - 线下完整闭环

**创建时间**: 2026-05-03 20:30 CST  
**优先级**: P0  
**状态**: OPEN

---

## 一、仓库现状全面总结

### 1.1 已完成工作

| 模块 | 状态 | 说明 |
|------|------|------|
| Issue #63 NASA TAP数据接入 | P0完成 | runtime/kepler_exoplanet_client.py实现，NASA Exoplanet Archive查询 |
| Issue #64 seestar-mcp对接 | P0完成 | runtime/observatory_linker.py + runtime/seestar_mcp_client.py (1209行) |
| Issue #65 Railway后端部署 | P0完成 | 部署到 https://tianwen-agi-production-fa3e.up.railway.app/ |
| Issue #66 Cloudflare前端部署 | P0完成 | 部署到 https://tianwen-agi.pages.dev/ |
| Issue #44 LONGCAT_API_KEY | 已识别 | /api/chat端点配置问题，需配置API Key |
| Issue #45-47 安全修复 | 已修复待验证 | sandbox.py注入、server.py配置、CI测试 |
| Issue #48 httpx依赖 | 已修复 | requirements.txt已添加 |
| Issue #70 Session持久化 | P1完成 | Redis集成实现 |
| Issue #71 WebSocket增强 | P1完成 | 心跳检测与断线重连 |
| Issue #72 pre-commit hooks | P1完成 | .pre-commit-config.yaml配置 |
| Discussion #42 | 验收不通过 | 2.0/10评分，安全灾难+数据造假 |
| Discussion #55/56 | 战略分析 | 与StarWhisper Telescope论文对标，25%完成度 |

### 1.2 未完成/严重缺失工作

| 模块 | 当前完成度 | 关键缺失 |
|------|-----------|---------|
| 硬件控制接口 | ~15% | 无实际INDI/pyINDI连接，无ASCOM真实驱动集成 |
| 观测调度算法 | ~25% | 无真实时间分配公式，无六原则调度实现 |
| 气象监控 | 0% | 完全缺失，无法判断观测条件 |
| Real-Bogus分类 | 0% | 完全缺失，无法判断天体真实性 |
| N.I.N.A.插件集成 | 0% | 无X-OPSTEP数据管道 |
| Astrometry.net对接 | 0% | 无天体测量解析 |
| SExtractor/HOTPANTS | 0% | 无图像叠加处理 |
| 星表精化 | 0% | 无Dec filtering，无NGC/IC/ESO过滤去重 |
| 本地LLM (Ollama) | 0% | 无离线LLM fallback |

### 1.3 Discussion #56 代码级审计结果

```
模块                     业务逻辑完成度
observation_scheduler.py    ~25%
observation_executor.py     ~15%
observatory_linker.py        ~20%
astro_pipeline.py           ~30%
Weather monitoring           0%
Real-Bogus classification    0%
```

---

## 二、全自动离线观测望远镜实施计划

### 2.1 架构目标

实现完全线下(无需互联网)的全自动天文观测闭环:

```
用户输入目标列表
    -> AI调度规划(本地Ollama)
    -> 气象判断(本地气象站数据)
    -> 望远镜控制(INDI/ASCOM)
    -> 相机拍摄(N.I.N.A.插件)
    -> 数据处理(Astrometry+SExtractor)
    -> 实时分类(Real-Bogus CNN)
    -> 自动重拍/报告生成
```

### 2.2 分阶段实施计划(24周)

#### Phase 1: 硬件接口层 (Week 1-4)

| 任务 | 依赖 | 优先级 | 验证方式 |
|------|------|--------|---------|
| 1.1 安装pyINDI库 | Linux INDI Server | P0 | pip install pyindi-client |
| 1.2 实现INDI望远镜GOTO | pyINDI | P0 | 指向M31，验证实际转向 |
| 1.3 实现INDI相机曝光控制 | pyINDI | P0 | 成功拍摄FIT文件 |
| 1.4 实现INDI dome/roof控制 | pyINDI | P1 | 开合响应测试 |
| 1.5 实现ASCOM Alpaca桥接 | Windows ASCOM | P1 | Windows环境测试 |
| 1.6 望远镜状态监控循环 | INDI | P0 | 实时位置/状态显示 |

#### Phase 2: 气象感知层 (Week 5-8)

| 任务 | 依赖 | 优先级 | 验证方式 |
|------|------|--------|---------|
| 2.1 气象站数据采集 | INDI | P0 | 从Weather Device读取云量/温度/湿度 |
| 2.2 云量实时评分算法 | 气象数据 | P0 | 0-100评分与实际天气对比 |
| 2.3 视宁度估算 | 本地气压/温度 | P1 | 历史数据回归验证 |
| 2.4 月相影响计算 | 天文算法 | P0 | moon_phase + moon_altitude |
| 2.5 综合观测条件评分 | 以上全部 | P0 | 评分低于40分禁止观测 |

#### Phase 3: 调度规划层 (Week 9-14)

| 任务 | 依赖 | 优先级 | 验证方式 |
|------|------|--------|---------|
| 3.1 星表数据离线化 | 预下载Catalog | P0 | 无网络环境下可查询 |
| 3.2 六原则观测调度实现 | 星表 | P0 | 优先级算法实际产出调度表 |
| 3.3 时间窗口计算 | 调度算法 | P0 | 输出每目标最佳观测时段 |
| 3.4 本地Ollama集成 | Ollama安装 | P1 | 本地LLM生成观测计划 |
| 3.5 多目标冲突消解 | 调度算法 | P1 | 同一时间多个目标时正确取舍 |
| 3.6 调度甘特图可视化 | Web UI | P2 | 生成可查看的调度图 |

#### Phase 4: 执行控制层 (Week 15-18)

| 任务 | 依赖 | 优先级 | 验证方式 |
|------|------|--------|---------|
| 4.1 N.I.N.A.插件协议对接 | N.I.N.A. | P0 | 通过HTTP API控制N.I.N.A. |
| 4.2 自动对焦流程 | N.I.N.A. | P0 | Focuser自动调整并验证HFR |
| 4.3 自动导星(guiding) | N.I.N.A. PHD2 | P0 | 导星RMS小于1.5arcsec |
| 4.4 曝光序列执行 | 调度器 | P0 | 按计划执行L/R/G/B曝光 |
| 4.5 拍摄异常自动重试 | 执行器 | P1 | 曝光失败3次后跳过/报告 |
| 4.6 中途目标切换 | 调度器+执行器 | P2 | 气象恶化时切换低优先级目标 |

#### Phase 5: 数据处理层 (Week 19-22)

| 任务 | 依赖 | 优先级 | 验证方式 |
|------|------|--------|---------|
| 5.1 Astrometry.net解析 | 拍摄照片 | P0 | 成功解析WCS坐标 |
| 5.2 SExtractor天体检测 | FITS文件 | P0 | 输出cat文件与已知星表对比 |
| 5.3 图像叠加(HOTPANTS) | 多张FITS | P1 | 成功生成叠加图 |
| 5.4 Real-Bogud CNN分类 | 叠加图 | P0 | 已知天体+随机噪声测试 |
| 5.5 变星/瞬变源检测 | 分类器 | P0 | 与已知变星目录对比 |
| 5.6 数据自动归档 | 处理完成 | P1 | 按日期/目标组织目录结构 |

#### Phase 6: 闭环验证 (Week 23-24)

| 任务 | 依赖 | 优先级 | 验证方式 |
|------|------|--------|---------|
| 6.1 完整观测循环测试 | 以上全部 | P0 | 选定目标->拍摄->处理->报告 |
| 6.2 离线模式测试 | 无网络 | P0 | 完全断网验证所有功能 |
| 6.3 24小时连续运行 | 稳定版本 | P0 | 无内存泄漏/崩溃 |
| 6.4 误差边界测试 | 极端条件 | P1 | 阴天/设备故障/断电恢复 |

---

## 三、关键依赖和技术栈

### 3.1 硬件接口

```
Linux: pyINDI + INDI Server + libASI (ZWO相机)
Windows: ASCOM Platform 7+ + Alpaca
```

### 3.2 核心Python依赖(需添加到requirements.txt)

```txt
# Hardware Control
pyindi-client>=1.2.0        # INDI协议客户端
pyascom>=1.0.0               # ASCOM Alpaca桥接(如有)

# Data Processing
astrometry.net>=0.9.0        # 天体测量(如果可用)
source-extractor>=2.25.0    # SExtractor
hotpants>=5.1.0             # 图像叠加

# Local LLM
ollama>=0.1.0              # 本地LLM推理

# Astronomical Algorithms
astropy>=6.0.0             # 天文计算
ephem>=4.1.0               # 星体位置计算
```

### 3.3 外部工具(必须安装)

| 工具 | 用途 | 平台 |
|------|------|------|
| INDI Server | 望远镜/相机控制守护进程 | Linux |
| N.I.N.A. | 相机/导星/对焦控制 | Windows |
| PHD2 | 导星软件 | Windows |
| ASCOM Platform | Windows硬件抽象 | Windows |
| Astrometry.net | 天体测量解析 | Linux |
| SExtractor | 天体检测测量 | Linux |
| HOTPANTS | 图像叠加 | Linux |

---

## 四、现有模块利用与改造

| 现有文件 | 用途 | 需改造 |
|---------|------|--------|
| runtime/observation_scheduler.py (542行) | 调度算法基础 | 实现六原则调度+时间分配公式 |
| runtime/observation_executor.py (747行) | 执行器基础 | 对接INDI/N.I.N.A.真实指令 |
| runtime/observatory_linker.py (1625行) | 望远镜连接 | 从模拟升级为真实INDI/ASCOM |
| runtime/seestar_mcp_client.py (1209行) | MCP协议 | 对接seestar真实硬件 |
| runtime/auto_observatory.py (641行) | 全自动工作流 | 整合所有模块为闭环 |
| runtime/telescope_simulator.py (723行) | 模拟器 | 可作为离线测试基础 |

---

## 五、未完成任务清单

| Issue | 任务 | 优先级 | 状态 |
|-------|------|--------|------|
| #28 | Multi-step planning (ARC-AGI) | P0 | 研究阶段 |
| #28 | 完整Tianwen闭环集成 | P0 | 25%完成 |
| #29 | ASCOM/INDI硬件接口标准化 | P0 | ~15%完成 |
| #29 | 实时跟踪控制 | P0 | 未实现 |
| #29 | VoxPoser 3D tracking | P1 | 未实现 |
| #29 | Safety collision detection | P1 | 未实现 |
| #31 | Ollama集成(本地LLM) | P0 | 0% |
| #31 | ChromaDB RAG | P1 | 已完成 |
| #53 | Vue 3前端重构 | P1 | 未开始 |
| #64 | seestar-mcp对接(真实硬件) | P0 | 仅模拟器 |
| 新建 | 气象监控系统 | P0 | 0% |
| 新建 | Real-Bogus分类器 | P0 | 0% |
| 新建 | N.I.N.A.插件集成 | P0 | 0% |
| 新建 | Astrometry.net对接 | P0 | 0% |
| 新建 | 离线星表数据 | P0 | 0% |

---

## 六、验证清单

- [ ] runtime/observation_scheduler.py - 六原则调度输出可执行观测计划
- [ ] runtime/observation_executor.py - INDI命令实际控制望远镜转向
- [ ] runtime/observatory_linker.py - 成功读取望远镜位置并解析
- [ ] 气象评分系统 - 输出0-100综合评分
- [ ] 离线星表 - 无网络环境下可查询大于10000天体
- [ ] Real-Bogus分类 - 对已知天体准确率大于90%
- [ ] 完整闭环 - M31目标从调度到报告全流程执行

---

## 七、参考文献

1. StarWhisper Telescope (arXiv:2412.06412v3) - 10望远镜真实部署参考
2. N.I.N.A. Engine Plugin Documentation
3. INDI Library Protocol Specification
4. ASCOM Platform 7 Documentation
5. GEM (Gradient Episodic Memory) - NeurIPS 2017 - 灾难性遗忘解决方案

---

*Plan Created: 2026-05-03 20:30 CST*
*Based on: Discussion #42/#55/#56 analysis + Discussion #56 24-week roadmap*
