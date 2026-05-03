# [TODO] 本地LLM优化 + NASA SkyView废弃替代方案

**状态**: Pending (线下记录，待处理)
**线上Issue**: https://github.com/LL-LK/tianwen-agi/issues/80
**创建时间**: 2026-05-03

---

## 问题摘要

1. **NASA SkyView API v4.1 已废弃** - `/api/v4.1/process` 返回404
2. **本地8B模型推理极慢** - qwen3-vl:8b 延迟30-100秒，AMD 780M iGPU无法加速
3. **19.8GB内存对8B模型不足** - 内存紧张，多任务易OOM

## 线下仓库的待办事项

- [ ] 测试 Aladin Lite API 替代 SkyView
- [ ] 将默认模型切换为 llama3.2:1b
- [ ] 集成 Groq API 处理复杂推理
- [ ] Real-Bogus 改用传统ML方案
- [ ] 安装 astrometry-net + SExtractor
- [ ] 推送所有 git 变更

## 成本参考

| 方案 | 月成本 | 适用场景 |
|------|--------|----------|
| 保持现状 | ¥0 | 不推荐（体验差）|
| Groq API | ¥15-50 | 日常使用 |
| AutoDL RTX 4090 | ¥100-300 | 长期任务 |
| SSD升级 | ¥200-600 | 无实际帮助 |

## 备注

- Issue评论时避免Unicode字符（->等），用ASCII替代
- Ollama路径: `/mnt/c/Users/22140/AppData/Local/Programs/Ollama/ollama.exe`
- NASA SkyView新接口: `/current/cgi/query.pl` (CGI，非REST)
