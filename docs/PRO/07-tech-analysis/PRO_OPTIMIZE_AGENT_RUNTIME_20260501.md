# PRO_OPTIMIZE_AGENT_RUNTIME_20260501

## Agent Runtime 优化方案

**项目**: Tianwen-AGI
**日期**: 2026-05-01
**类型**: 运行时优化
**关联Issue**: GitHub Issue #1 (核心问题是缺乏实际运行时)

---

## 一、问题分析

### 1.1 核心问题

Issue #1 指出"缺乏实际运行时"，具体表现为：

1. **after_task钩子空转**: `EvolutionSystem.after_task()` 只是简单记录，无实际进化逻辑
2. **错误处理缺失**: 任务失败后无重试机制，无错误分类
3. **状态管理薄弱**: TaskStatus只是枚举，无状态流转跟踪
4. **持久化断连**: 记忆系统与执行流程脱节
5. **无健康检查**: 无法监控运行时健康状态

### 1.2 现状架构

```
main.py: HermesAGI
├── CognitiveEngine (意图识别) ✓
├── PlanningEngine (任务规划) ✓
├── ExecutionEngine (执行) ⚠️  无重试
└── EvolutionSystem (进化) ⚠️  空壳

research_loop.py: AfterTaskHook (更好的实现)
├── on_task_complete() ⚠️  只是打印
├── on_hypothesis_generated() ⚠️  只是打印
└── on_verification_complete() ⚠️  只是打印
```

---

## 二、优化方案

### 2.1 核心目标

- 让after_task钩子真正触发自我进化
- 添加指数退避重试机制
- 实现错误分类与自动恢复
- 集成持久化记忆到执行流程
- 添加运行时健康监控

### 2.2 优化后的架构

```
HermesAGI (主控制器)
├── CognitiveEngine (意图识别) ✓
├── PlanningEngine (任务规划) ✓
├── ExecutionEngine (执行 + 重试)
│   ├── 重试策略 (指数退避)
│   ├── 错误分类器
│   └── 超时控制
├── EvolutionSystem (真实进化)
│   ├── 任务后钩子 (连接记忆)
│   ├── 模式提取器
│   ├── 失败分析器
│   └── 健康监控
└── MemoryIntegrated (持久化)
    ├── 经验存储
    ├── 相似任务检索
    └── 技能统计
```

---

## 三、具体实现

### 3.1 重试引擎 (RetryEngine)

```python
class RetryEngine:
    """指数退避重试引擎"""

    def __init__(self, max_retries=3, base_delay=1.0, max_delay=30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute_with_retry(self, func, *args, **kwargs):
        """带重试的执行"""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except RetryableError as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
        raise MaxRetriesExceeded(last_error)
```

### 3.2 错误分类器 (ErrorClassifier)

```python
class ErrorType(Enum):
    TRANSIENT = "transient"      # 临时错误，可重试
    PERMANENT = "permanent"      # 永久错误，不重试
    UNKNOWN = "unknown"          # 未知错误

class ErrorClassifier:
    """错误分类器"""

    TRANSIENT_PATTERNS = [
        "timeout",
        "connection refused",
        "network error",
        "rate limit"
    ]

    PERMANENT_PATTERNS = [
        "syntax error",
        "invalid parameter",
        "permission denied"
    ]

    def classify(self, error: str) -> ErrorType:
        """分类错误类型"""
        error_lower = error.lower()
        if any(p in error_lower for p in self.TRANSIENT_PATTERNS):
            return ErrorType.TRANSIENT
        if any(p in error_lower for p in self.PERMANENT_PATTERNS):
            return ErrorType.PERMANENT
        return ErrorType.UNKNOWN
```

### 3.3 健康监控器 (HealthMonitor)

```python
class HealthMonitor:
    """运行时健康监控"""

    def __init__(self):
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "retried_tasks": 0,
            "avg_execution_time": 0
        }

    def record_task_start(self):
        self.metrics["total_tasks"] += 1

    def record_task_success(self, duration: float):
        self.metrics["successful_tasks"] += 1
        self._update_avg_time(duration)

    def record_task_failure(self):
        self.metrics["failed_tasks"] += 1

    def record_retry(self):
        self.metrics["retried_tasks"] += 1

    def get_health_score(self) -> float:
        """计算健康分数 (0-1)"""
        total = self.metrics["total_tasks"]
        if total == 0: return 1.0
        success_rate = self.metrics["successful_tasks"] / total
        retry_rate = self.metrics["retried_tasks"] / total
        return success_rate * (1 - retry_rate * 0.5)
```

### 3.4 真实进化的EvolutionSystem

```python
class EvolutionSystem:
    """真实进化的自我进化系统"""

    def __init__(self, memory_dir: str = "./memory"):
        self.memory = PersistentMemory(memory_dir)
        self.health = HealthMonitor()
        self.retry_engine = RetryEngine()

    async def after_task(self, result: ExecutionResult):
        """任务完成后的真实进化"""
        # 1. 记录到记忆系统
        task_record = {
            "task_id": result.task_model.id,
            "type": result.task_model.type.value,
            "skills": result.task_model.required_skills,
            "status": result.status.value,
            "duration": result.metrics.get("duration", 0),
            "errors": result.errors
        }
        self.memory.add_task_record(task_record)

        # 2. 记录经验（成功或失败）
        if result.status == TaskStatus.COMPLETED:
            self.memory.record_success(
                task=result.task_model.description,
                solution=result.output[:500],
                skills=result.task_model.required_skills
            )
        else:
            self.memory.record_failure(
                task=result.task_model.description,
                error=", ".join(result.errors),
                skills=result.task_model.required_skills
            )

        # 3. 提取模式
        self._extract_and_save_pattern(result)

        # 4. 更新健康监控
        if result.status == TaskStatus.COMPLETED:
            self.health.record_task_success(result.metrics.get("duration", 0))
        else:
            self.health.record_task_failure()

    def _extract_and_save_pattern(self, result: ExecutionResult):
        """提取并保存模式"""
        if len(result.plan.subtasks) > 0:
            success_rate = sum(1 for t in result.plan.subtasks
                             if t.status == TaskStatus.COMPLETED) / len(result.plan.subtasks)
            self.memory.add_pattern("subtask_success_rate", {
                "skills": result.task_model.required_skills,
                "rate": success_rate
            })
```

---

## 四、文件修改清单

| 文件 | 修改内容 | 优先级 |
|-----|---------|-------|
| `main.py` | 集成RetryEngine、ErrorClassifier、HealthMonitor；重写EvolutionSystem.after_task | P0 |
| `research_loop.py` | 增强AfterTaskHook连接memory_persistence | P1 |
| `observation_executor.py` | 添加健康检查接口 | P2 |

---

## 五、测试验证

```bash
# 测试重试机制
python -c "
import asyncio
from main import HermesAGI
agent = HermesAGI()
result = asyncio.run(agent.process('创建用户登录API'))
print(f'Success: {result.status}')
print(f'Health score: {agent.evolution.health.get_health_score()}')
"

# 验证记忆持久化
python -c "
from memory_persistence import PersistentMemory
mem = PersistentMemory()
stats = mem.get_stats()
print(f'Total experiences: {stats[\"total_experiences\"]}')
"
```

---

## 六、预期效果

- after_task钩子真正写入记忆系统
- 临时错误自动重试（最多3次，指数退避）
- 健康分数实时反映运行状态
- 相似任务自动检索作为上下文
- 成功率统计完整记录

---

**签名**: Claude Agent (Runtime Optimizer)
**日期**: 2026-05-01