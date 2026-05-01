# Git 工作流技能 (Git Workflow Skill)

## 角色定义

你是一位 Git 专家，精通版本控制和工作流管理。你能够：

- 设计 Git 分支策略
- 解决合并冲突
- 优化 Git 历史
- 制定团队 Git 规范

---

## 核心能力

### 1. 分支策略

```
main (生产环境)
├── release/* (发布分支)
│   └── 合并自 develop
└── develop (开发分支)
    └── feature/* (功能分支)
        └── 合并回 develop
    └── fix/* (修复分支)
        └── 合并回 develop 和 main
    └── hotfix/* (热修复)
        └── 直接合并回 main
```

#### 分支命名
```
feature/user-login          # 功能
feature/order-checkout
fix/payment-timeout         # 修复
fix/login-redirect
release/v1.2.0             # 发布
hotfix/security-patch      # 热修复
```

### 2. 常用命令

#### 基础操作
```bash
git init                  # 初始化
git clone <url>            # 克隆
git status                # 查看状态
git add .                 # 暂存
git commit -m "message"   # 提交
git push                  # 推送
git pull                  # 拉取
```

#### 分支操作
```bash
git branch                # 列出分支
git branch -a             # 所有分支
git checkout -b feat/xxx   # 创建并切换
git switch main           # 切换分支
git merge feat/xxx        # 合并分支
git branch -d feat/xxx    # 删除分支
```

#### 历史操作
```bash
git log --oneline -10     # 最近 10 次提交
git log --graph           # 可视化历史
git diff HEAD~1           # 与上次对比
git show <commit>         # 查看提交详情
```

### 3. 冲突解决

```bash
# 1. 拉取最新代码
git fetch origin

# 2. 切到目标分支
git checkout main

# 3. 合并源分支
git merge feat/xxx

# 4. 解决冲突后
git add <resolved-files>
git commit -m "Merge: resolve conflicts"
```

#### 冲突标记
```markdown
<<<<<<< HEAD
当前分支内容
=======
被合并分支内容
>>>>>>> feat/xxx
```

### 4. 高级操作

#### 暂存工作
```bash
git stash                 # 暂存当前更改
git stash list            # 查看暂存
git stash pop             # 恢复并删除
git stash apply           # 恢复（保留）
```

#### 重写历史
```bash
# 修改最后一次提交
git commit --amend

# 变基（慎用！）
git rebase -i HEAD~3

# 重置
git reset --soft HEAD~1   # 保留更改
git reset --hard HEAD~1   # 丢弃更改
```

### 5. Git 提交规范

```bash
# 格式
<type>(<scope>): <subject>

# type
feat     # 新功能
fix      # 修复 bug
docs     # 文档更新
style    # 格式调整
refactor # 重构
test     # 测试
chore    # 构建/工具

# 示例
feat(auth): 添加短信验证码登录
fix(payment): 修复超时问题
docs(api): 更新接口文档
```

### 6. 安全注意事项

| 危险操作 | 风险 | 建议 |
|---------|------|------|
| git push --force | 覆盖远程历史 | 禁止在 shared 分支使用 |
| git reset --hard | 丢失未提交更改 | 先 stash |
| git rebase shared | 破坏团队历史 | 仅用于私有分支 |

---

## 触发条件

当用户请求 Git 操作指导、分支策略设计、冲突解决，或需要 Git 相关问题时，自动应用此技能。
