# 学习到的模式

将从实践中学习到的有效模式和解决方案记录下来。

---

## 任务处理模式

### 1. 前端任务模式
```
1. 加载 UI-Visual + Frontend skill
2. 产出视觉规范
3. 实现组件代码
4. 添加测试
5. 代码审查
```

### 2. 后端任务模式
```
1. 加载 Database + Backend + API-Design skill
2. 设计数据模型
3. 设计 API 接口
4. 实现业务逻辑
5. 安全审查
6. 测试
```

### 3. 全栈任务模式
```
1. 加载 Product-Manager skill（调度中枢）
2. 需求分析（Product）
3. 架构设计（Architecture）
4. 接口设计（API-Design）
5. 并行开发（Frontend + Backend）
6. 测试 + 安全审查
7. 部署（DevOps）
```

### 4. 数据分析任务模式
```
1. 加载 Data-Analysis skill
2. 需求理解
3. 数据获取与清洗
4. 探索性分析
5. 建模或统计分析
6. 可视化
7. 产出报告
```

---

## 问题解决模式

### 冲突解决优先级
| 冲突类型 | 优先级裁决 |
|---------|-----------|
| 界面 vs 功能 | 功能优先 |
| 性能 vs 安全 | 安全优先 |
| 进度 vs 质量 | 核心保质量 |
| 后端 vs 前端 | API 为契约 |

### 技能调度优先级
| 紧急度 | 调度策略 |
|-------|---------|
| P0 | 必须完成的技能直接调度 |
| P1 | 重要但可延后的技能加入计划 |
| P2 | 优化类技能按需调度 |

---

## 代码模式

### TypeScript 组件模式
```typescript
// 统一组件结构
interface Props {
  // 属性定义
}

export function ComponentName({ prop1, prop2 }: Props) {
  // 1. 状态
  // 2. 副作用
  // 3. 回调
  // 4. 渲染
  return ( ... );
}
```

### API 响应模式
```typescript
// 统一响应格式
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  pagination?: Pagination;
}

// 错误响应
{
  code: 400,
  message: "参数错误",
  errors: [{ field: "xxx", message: "yyy" }]
}
```

---

## 持续更新

此文件在每次任务完成后根据实际情况更新。
