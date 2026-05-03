# 天问-AGI Pre-commit Hooks 安装与使用指南

> Issue #72 - 代码质量门禁

## 快速开始

### 1. 安装依赖

```bash
# 安装pre-commit
pip install pre-commit

# 或使用项目依赖
pip install -r requirements-dev.txt
```

### 2. 安装Git钩子

```bash
# 在项目根目录执行
cd F:/tianwen-agi
pre-commit install
```

### 3. 运行检查

```bash
# 对所有文件运行检查
pre-commit run --all-files

# 对已暂存的文件运行检查
pre-commit run

# 更新钩子版本
pre-commit autoupdate
```

## 钩子列表

| 钩子 | 用途 | 依赖 |
|------|------|------|
| `black` | Python代码格式化 | 120字符行长 |
| `isort` | 导入语句排序 | 兼容black profile |
| `flake8` | Python代码检查 | 最大行长120 |
| `bandit` | 安全漏洞扫描 | - |
| `mypy` | 类型检查 | types-*包 |
| `shellcheck` | Shell脚本检查 | - |
| `mdformat` | Markdown格式化 | - |
| `hadolint` | Dockerfile检查 | - |
| `prettier` | YAML/JSON格式化 | - |
| `end-of-file-fixer` | 文件末尾换行 | - |
| `trailing-whitespace` | 删除尾随空白 | - |
| `check-merge-conflict` | 检查合并冲突 | - |
| `check-added-large-files` | 检查大文件 | 5MB限制 |

## 配置文件

主配置: `.pre-commit-config.yaml`

项目级忽略: `.pre-commit-ignore`

## CI集成

### GitHub Actions

```yaml
# .github/workflows/pre-commit.yml
name: Pre-commit

on:
  push:
    branches: [main, trae]
  pull_request:
    branches: [main, trae]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: pre-commit/action@v3.0.1
```

### 本地跳过检查

```bash
# 跳过所有钩子
git commit --no-verify -m "Emergency fix"

# 跳过特定钩子
SKIP=black git commit -m "Quick fix"
```

## 常见问题

### Q: 钩子安装失败
```bash
# 清除缓存重新安装
pre-commit clean
pre-commit install
```

### Q: mypy报错过多
在 `.pre-commit-config.yaml` 中添加:
```yaml
args:
  - --disable-error-code=misc
```

### Q: black和isort冲突
确保使用相同的 `line-length=120` 和 `profile=black`

## 版本要求

- Python: >= 3.9
- pre-commit: >= 3.0
- Git: >= 2.30

---

*最后更新: 2026-05-03*
