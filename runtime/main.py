"""
Hermes-AGI Agent Runtime v2.0
运行时主入口 - 整合认知、规划、执行引擎
优化: 添加重试机制、错误分类、健康监控、真实after_task进化
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 导入记忆系统
try:
    from memory_persistence import PersistentMemory, Experience
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    PersistentMemory = None
    Experience = None

# ============ 核心数据结构 ============

class IntentType(Enum):
    EXECUTE = "Execute"
    QUERY = "Query"
    LEARN = "Learn"
    COLLABORATE = "Collaborate"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Entity:
    type: str
    value: str
    confidence: float

@dataclass
class TaskModel:
    id: str
    type: IntentType
    description: str
    entities: List[Entity] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    required_skills: List[str] = field(default_factory=list)
    complexity: str = "medium"

@dataclass
class SubTask:
    id: str
    name: str
    skill: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None

@dataclass
class ExecutionPlan:
    task_id: str
    subtasks: List[SubTask]
    parallel_groups: List[List[str]] = field(default_factory=list)
    estimated_time: str = ""
    risks: List[str] = field(default_factory=list)

@dataclass
class ExecutionResult:
    status: TaskStatus
    output: str
    task_model: TaskModel
    plan: ExecutionPlan
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

# ============ 错误分类器 ============

class ErrorType(Enum):
    TRANSIENT = "transient"      # 临时错误，可重试
    PERMANENT = "permanent"      # 永久错误，不重试
    UNKNOWN = "unknown"          # 未知错误

class ErrorClassifier:
    """错误分类器 - 区分可重试和不可重试错误"""

    TRANSIENT_PATTERNS = [
        "timeout", "timed out",
        "connection refused",
        "network error", "network failure",
        "rate limit", "too many requests",
        "service unavailable",
        "temporary failure"
    ]

    PERMANENT_PATTERNS = [
        "syntax error", "parse error",
        "invalid parameter", "invalid argument",
        "permission denied", "unauthorized",
        "not found", "does not exist",
        "type error", "attribute error"
    ]

    def classify(self, error: str) -> ErrorType:
        """分类错误类型"""
        error_lower = error.lower()
        if any(p in error_lower for p in self.TRANSIENT_PATTERNS):
            return ErrorType.TRANSIENT
        if any(p in error_lower for p in self.PERMANENT_PATTERNS):
            return ErrorType.PERMANENT
        return ErrorType.UNKNOWN

    def is_retryable(self, error: str) -> bool:
        """判断错误是否可重试"""
        return self.classify(error) in (ErrorType.TRANSIENT, ErrorType.UNKNOWN)

# ============ 重试引擎 ============

class RetryableError(Exception):
    """可重试的错误"""
    pass

class MaxRetriesExceeded(Exception):
    """超过最大重试次数"""
    pass

class RetryEngine:
    """指数退避重试引擎"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.classifier = ErrorClassifier()
        self.total_retries = 0

    async def execute_with_retry(self, func, *args, **kwargs):
        """带重试的执行"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.total_retries += 1
                return result

            except Exception as e:
                error_msg = str(e)
                last_error = e

                if not self.classifier.is_retryable(error_msg):
                    # 永久错误，不重试
                    raise

                if attempt < self.max_retries:
                    # 计算延迟（指数退避）
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    print(f"[Retry] 尝试 {attempt + 1} 失败，{delay:.1f}秒后重试: {error_msg[:100]}")
                    import asyncio
                    await asyncio.sleep(delay)
                else:
                    break

        raise MaxRetriesExceeded(last_error)

    def get_retry_stats(self) -> Dict:
        return {"total_retries": self.total_retries}

# ============ 健康监控器 ============

class HealthMonitor:
    """运行时健康监控"""

    def __init__(self):
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "retried_tasks": 0,
            "total_execution_time": 0.0
        }
        self.task_durations: List[float] = []

    def record_task_start(self):
        self.metrics["total_tasks"] += 1

    def record_task_success(self, duration: float):
        self.metrics["successful_tasks"] += 1
        self.metrics["total_execution_time"] += duration
        self.task_durations.append(duration)
        # 只保留最近100个duration
        if len(self.task_durations) > 100:
            self.task_durations = self.task_durations[-100:]

    def record_task_failure(self):
        self.metrics["failed_tasks"] += 1

    def record_retry(self):
        self.metrics["retried_tasks"] += 1

    def get_health_score(self) -> float:
        """计算健康分数 (0-1)"""
        total = self.metrics["total_tasks"]
        if total == 0:
            return 1.0

        success_rate = self.metrics["successful_tasks"] / total
        retry_rate = self.metrics["retried_tasks"] / total if total > 0 else 0

        # 健康分数 = 成功率 * (1 - 重试惩罚)
        return success_rate * (1 - retry_rate * 0.3)

    def get_stats(self) -> Dict:
        avg_time = 0
        if self.task_durations:
            avg_time = sum(self.task_durations) / len(self.task_durations)

        return {
            **self.metrics,
            "health_score": self.get_health_score(),
            "avg_execution_time": avg_time
        }

# ============ 认知引擎 ============

class CognitiveEngine:
    """认知引擎 - 理解用户输入"""

    def __init__(self):
        self.intent_patterns = {
            r'(创建|开发|编写|写|实现|制作)': IntentType.EXECUTE,
            r'(查询|搜索|找|获取)': IntentType.QUERY,
            r'(学习|了解|解释|什么是)': IntentType.LEARN,
            r'(审查|评审|讨论|协作)': IntentType.COLLABORATE,
        }

        self.skill_keywords = {
            'Frontend': ['前端', 'react', 'vue', 'html', 'css', '界面'],
            'Backend': ['后端', 'api', '接口', 'server', 'node', 'python'],
            'Database': ['数据库', 'sql', '表', 'db', '存储'],
            'Architecture': ['架构', '微服务', '系统设计'],
            'Testing': ['测试', 'test', '单元测试'],
            'Security': ['安全', 'xss', '注入', '漏洞'],
            'DevOps': ['部署', 'docker', 'ci', 'cd', 'k8s'],
            'DataAnalysis': ['分析', '数据', '统计', 'python'],
            'Product': ['需求', '产品', 'prd', '用户故事'],
        }

    def process(self, user_input: str) -> TaskModel:
        """处理用户输入，返回任务模型"""
        # 生成任务ID
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # 意图识别
        intent = self._recognize_intent(user_input)

        # 实体提取
        entities = self._extract_entities(user_input)

        # 技能匹配
        skills = self._match_skills(user_input)

        # 复杂度评估
        complexity = self._assess_complexity(user_input)

        return TaskModel(
            id=task_id,
            type=intent,
            description=user_input,
            entities=entities,
            required_skills=skills,
            complexity=complexity
        )

    def _recognize_intent(self, text: str) -> IntentType:
        """识别意图类型"""
        for pattern, intent in self.intent_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return intent
        return IntentType.QUERY

    def _extract_entities(self, text: str) -> List[Entity]:
        """提取实体"""
        entities = []
        tech_patterns = {
            'React': r'REACT|react',
            'Vue': r'VUE|vue',
            'Node.js': r'NODE|node\.?js',
            'Python': r'PYTHON|python',
            'PostgreSQL': r'POSTGRES|postgresql',
            'Docker': r'DOCKER|docker',
        }
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, text):
                entities.append(Entity(type="Technology", value=tech, confidence=0.95))

        if re.search(r'\d+[天日周月年]', text):
            entities.append(Entity(type="TimeConstraint", value="有", confidence=0.8))

        return entities

    def _match_skills(self, text: str) -> List[str]:
        """匹配所需技能"""
        matched = []
        text_lower = text.lower()
        for skill, keywords in self.skill_keywords.items():
            if any(kw.lower() in text_lower for kw in keywords):
                matched.append(skill)
        if not matched:
            matched = ['General']
        return matched

    def _assess_complexity(self, text: str) -> str:
        """评估复杂度"""
        complexity_indicators = {
            'high': [r'完整', r'系统', r'复杂', r'微服务'],
            'medium': [r'组件', r'模块', r'api', r'接口'],
            'low': [r'简单', r'单个', r'一个'],
        }
        for level, patterns in complexity_indicators.items():
            if any(re.search(p, text) for p in patterns):
                return level
        return 'medium'

# ============ 规划引擎 ============

class PlanningEngine:
    """规划引擎 - 分解任务并制定执行计划"""

    def __init__(self):
        self.skill_workflows = {
            'Frontend': ['Product', 'UI-Visual', 'Frontend', 'React', 'Testing'],
            'Backend': ['Product', 'Architecture', 'Database', 'API-Design', 'Backend', 'Testing'],
            'Database': ['Database', 'Architecture'],
            'Architecture': ['Product', 'Architecture', 'DevOps'],
            'Testing': ['Testing', 'Code-Review', 'Security'],
            'Security': ['Security', 'Testing', 'Code-Review'],
            'DevOps': ['DevOps', 'Cloud-Deployment', 'Linux-Operations'],
            'DataAnalysis': ['Product', 'DataAnalysis', 'Database'],
            'Product': ['Product', 'Project-Management'],
            'General': ['Product'],
        }

    def create_plan(self, task_model: TaskModel) -> ExecutionPlan:
        """创建执行计划"""
        # 获取主技能工作流
        main_skills = task_model.required_skills
        if not main_skills or main_skills == ['General']:
            main_skills = ['Product']

        # 构建子任务
        subtasks = []
        task_index = 1

        for skill in main_skills:
            workflow = self.skill_workflows.get(skill, ['Product'])
            for w in workflow:
                subtask = SubTask(
                    id=f"{task_model.id}-T{task_index}",
                    name=f"{w}技能执行",
                    skill=w,
                    dependencies=[subtasks[-1].id] if subtasks else []
                )
                subtasks.append(subtask)
                task_index += 1

        # 创建并行组
        parallel_groups = self._create_parallel_groups(subtasks)

        return ExecutionPlan(
            task_id=task_model.id,
            subtasks=subtasks,
            parallel_groups=parallel_groups,
            estimated_time=self._estimate_time(len(subtasks)),
            risks=self._assess_risks(subtasks)
        )

    def _create_parallel_groups(self, subtasks: List[SubTask]) -> List[List[str]]:
        """创建并行执行组"""
        if len(subtasks) <= 2:
            return [[t.id] for t in subtasks]

        groups = []
        for i in range(0, len(subtasks), 2):
            group = [t.id for t in subtasks[i:i+2] if i == 0 or subtasks[i].dependencies]
            if group:
                groups.append(group)
        return groups if groups else [[subtasks[0].id]]

    def _estimate_time(self, subtask_count: int) -> str:
        """预估时间"""
        hours = subtask_count * 0.5
        if hours < 1:
            return f"{int(hours * 60)}分钟"
        return f"{hours:.1f}小时"

    def _assess_risks(self, subtasks: List[SubTask]) -> List[str]:
        """评估风险"""
        risks = []
        if len(subtasks) > 5:
            risks.append("任务较多，可能需要分批执行")
        if any(s.skill in ['Architecture', 'Database'] for s in subtasks):
            risks.append("涉及架构设计，需要充分沟通")
        return risks

# ============ 执行引擎 ============

class ExecutionEngine:
    """执行引擎 - 执行任务和调用技能"""

    def __init__(self, skill_dir: str = "./skills"):
        self.skill_dir = skill_dir
        self.execution_history: List[Dict] = []

    async def execute_plan(self, plan: ExecutionPlan) -> List[SubTask]:
        """执行计划"""
        results = []

        for subtask in plan.subtasks:
            try:
                # 模拟技能执行
                result = await self._execute_skill(subtask)
                subtask.result = result
                subtask.status = TaskStatus.COMPLETED
            except Exception as e:
                subtask.error = str(e)
                subtask.status = TaskStatus.FAILED
                results.append(subtask)
                continue

            results.append(subtask)

        return results

    async def _execute_skill(self, subtask: SubTask) -> str:
        """执行单个技能"""
        # 模拟技能执行
        await self._simulate_delay(0.1)

        skill_outputs = {
            'Product': '需求分析完成 - 产出PRD文档初稿',
            'Architecture': '架构设计完成 - 输出系统架构图',
            'Database': '数据库设计完成 - 生成ER图和DDL',
            'API-Design': 'API设计完成 - 输出接口文档',
            'Backend': '后端开发完成 - 生成代码框架',
            'Frontend': '前端开发完成 - 生成组件代码',
            'React': 'React开发完成 - 生成组件和Hooks',
            'Testing': '测试完成 - 生成测试用例和报告',
            'Code-Review': '代码审查完成 - 提出优化建议',
            'Security': '安全审查完成 - 无高危漏洞',
            'DevOps': 'DevOps配置完成 - CI/CD流水线就绪',
        }

        return skill_outputs.get(subtask.skill, f'{subtask.skill}执行完成')

    async def _simulate_delay(self, seconds: float):
        """模拟延迟"""
        import asyncio
        await asyncio.sleep(seconds)

# ============ 自我进化系统 (真实版) ============

class EvolutionSystem:
    """自我进化系统 - 持续学习和优化 (v2.0)

    与 PersistentMemory 集成，实现真正的自我进化：
    - 任务完成后自动记录经验和模式
    - 连接记忆系统进行长期知识积累
    - 提供健康监控和统计
    """

    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = memory_dir
        self.task_history: List[Dict] = []
        self.patterns: List[Dict] = []
        self.health = HealthMonitor()
        self.retry_engine = RetryEngine()

        # 初始化持久化记忆
        if MEMORY_AVAILABLE:
            try:
                self.memory = PersistentMemory(memory_dir)
                print(f"[Evolution] Connected to PersistentMemory: {memory_dir}")
            except Exception as e:
                print(f"[Evolution] Failed to init PersistentMemory: {e}")
                self.memory = None
        else:
            self.memory = None

    def after_task(self, result: ExecutionResult):
        """任务完成后的自我进化钩子 (真实实现)

        1. 记录任务到历史
        2. 提取成功/失败模式
        3. 更新健康监控
        4. 同步到持久化记忆
        """
        # 记录任务执行
        record = {
            'date': datetime.now().isoformat(),
            'task_id': result.task_model.id,
            'type': result.task_model.type.value,
            'skills': result.task_model.required_skills,
            'status': result.status.value,
            'duration': result.metrics.get('duration', 0),
            'subtask_count': len(result.plan.subtasks),
            'errors': result.errors
        }
        self.task_history.append(record)

        # 更新健康监控
        if result.status == TaskStatus.COMPLETED:
            self.health.record_task_success(result.metrics.get('duration', 0))
        else:
            self.health.record_task_failure()

        # 提取模式并保存
        if result.status == TaskStatus.COMPLETED:
            self._extract_success_pattern(result)
            if self.memory:
                self._record_to_memory_success(result)
        else:
            self._analyze_failure(result)
            if self.memory:
                self._record_to_memory_failure(result)

        # 提取子任务成功率模式
        if len(result.plan.subtasks) > 0:
            success_count = sum(1 for t in result.plan.subtasks
                              if t.status == TaskStatus.COMPLETED)
            rate = success_count / len(result.plan.subtasks)
            self._save_pattern({
                "type": "subtask_success_rate",
                "skills": result.task_model.required_skills,
                "rate": rate,
                "total_subtasks": len(result.plan.subtasks)
            })

    def _record_to_memory_success(self, result: ExecutionResult):
        """记录成功到持久化记忆"""
        if not self.memory:
            return
        try:
            self.memory.record_success(
                task=result.task_model.description,
                solution=result.output[:500] if result.output else "",
                skills=result.task_model.required_skills,
                intent=result.task_model.type.value,
                complexity=result.task_model.complexity
            )
        except Exception as e:
            print(f"[Evolution] Failed to record success: {e}")

    def _record_to_memory_failure(self, result: ExecutionResult):
        """记录失败到持久化记忆"""
        if not self.memory:
            return
        try:
            self.memory.record_failure(
                task=result.task_model.description,
                error=", ".join(result.errors) if result.errors else "Unknown error",
                skills=result.task_model.required_skills
            )
        except Exception as e:
            print(f"[Evolution] Failed to record failure: {e}")

    def _extract_success_pattern(self, result: ExecutionResult):
        """提取成功模式"""
        pattern = {
            'type': 'success',
            'intent': result.task_model.type.value,
            'skills': result.task_model.required_skills,
            'complexity': result.task_model.complexity,
            'subtask_count': len(result.plan.subtasks),
        }
        self.patterns.append(pattern)
        self._save_pattern(pattern)

    def _analyze_failure(self, result: ExecutionResult):
        """分析失败原因"""
        for error in result.errors:
            print(f"[Evolution] 失败分析: {error}")
            self._save_pattern({
                "type": "failure",
                "error_type": ErrorClassifier().classify(error).value,
                "error_message": error[:200],
                "skills": result.task_model.required_skills
            })

    def _save_pattern(self, pattern: Dict):
        """保存模式到记忆系统"""
        if self.memory:
            try:
                self.memory.add_pattern(pattern.get("type", "unknown"), pattern)
            except Exception as e:
                print(f"[Evolution] Failed to save pattern: {e}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.task_history)
        if total == 0:
            return {
                'total_tasks': 0,
                'success_rate': 0,
                'health_score': 1.0,
                'patterns_count': 0
            }

        successes = sum(1 for r in self.task_history if r['status'] == 'completed')
        return {
            'total_tasks': total,
            'success_rate': successes / total,
            'health_score': self.health.get_health_score(),
            'patterns_count': len(self.patterns),
            'health_stats': self.health.get_stats()
        }

    def get_similar_experiences(self, query: str, k: int = 3) -> List[Dict]:
        """获取相似经验"""
        if self.memory:
            return self.memory.search_experiences(query, k=k)
        return []

    async def process_with_hooks(self, func, *args, **kwargs):
        """带钩子处理的执行（用于重试）"""
        return await self.retry_engine.execute_with_retry(func, *args, **kwargs)

# ============ 主Agent类 (增强版) ============

class HermesAGI:
    """Hermes-AGI 智能体主类 (v2.0)

    整合认知、规划、执行、进化系统
    新增: 任务开始记录、重试执行、相似经验上下文
    """

    def __init__(self, skill_dir: str = "./skills", memory_dir: str = "./memory"):
        self.cognitive = CognitiveEngine()
        self.planning = PlanningEngine()
        self.execution = ExecutionEngine(skill_dir)
        self.evolution = EvolutionSystem(memory_dir)
        self.retry_engine = RetryEngine()

    async def process(self, user_input: str) -> ExecutionResult:
        """处理用户输入的完整流程 (v2.0)"""
        start_time = datetime.now()

        # 0. 记录任务开始
        self.evolution.health.record_task_start()

        # 1. 认知引擎 - 理解输入
        task_model = self.cognitive.process(user_input)

        # 2. 规划引擎 - 制定计划
        plan = self.planning.create_plan(task_model)

        # 3. 执行引擎 - 执行任务 (带重试)
        try:
            await self.retry_engine.execute_with_retry(
                self.execution.execute_plan, plan
            )
        except MaxRetriesExceeded as e:
            # 处理重试耗尽的情况
            errors = [f"Max retries exceeded: {str(e)}"]
            for subtask in plan.subtasks:
                if subtask.status != TaskStatus.COMPLETED:
                    subtask.error = subtask.error or "Max retries exceeded"
                    errors.append(f"{subtask.id}: {subtask.error}")
            # 标记失败的子任务
            for subtask in plan.subtasks:
                if subtask.status == TaskStatus.PENDING:
                    subtask.status = TaskStatus.FAILED

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()

        # 4. 构建结果
        failed_subtasks = [t for t in plan.subtasks if t.status == TaskStatus.FAILED]
        if failed_subtasks:
            result = ExecutionResult(
                status=TaskStatus.FAILED,
                output=self._format_output(plan),
                task_model=task_model,
                plan=plan,
                metrics={'duration': duration, 'subtasks_completed': len(plan.subtasks) - len(failed_subtasks)},
                errors=[f"{t.id}: {t.error}" for t in failed_subtasks if t.error]
            )
        else:
            result = ExecutionResult(
                status=TaskStatus.COMPLETED,
                output=self._format_output(plan),
                task_model=task_model,
                plan=plan,
                metrics={'duration': duration, 'subtasks_completed': len(plan.subtasks)}
            )

        # 5. 自我进化 - 学习经验 (真实触发)
        self.evolution.after_task(result)

        return result

    def _format_output(self, plan: ExecutionPlan) -> str:
        """格式化输出"""
        lines = [f"## 执行计划 - {plan.task_id}"]
        lines.append(f"\n### 子任务 ({len(plan.subtasks)}个)")
        lines.append("| ID | 技能 | 状态 |")
        lines.append("|----|------|------|")
        for task in plan.subtasks:
            status_icon = "✅" if task.status == TaskStatus.COMPLETED else "❌" if task.status == TaskStatus.FAILED else "⏳"
            lines.append(f"| {task.id} | {task.skill} | {status_icon} {task.status.value} |")
            if task.result:
                lines.append(f"| | 结果: {task.result} |")
            if task.error:
                lines.append(f"| | 错误: {task.error} |")
        lines.append(f"\n### 统计")
        lines.append(f"- 总任务数: {len(plan.subtasks)}")
        lines.append(f"- 预估时间: {plan.estimated_time}")
        if plan.risks:
            lines.append(f"- 风险提示: {'; '.join(plan.risks)}")
        return "\n".join(lines)

    def get_health_score(self) -> float:
        """获取运行时健康分数"""
        return self.evolution.health.get_health_score()

    def get_similar_tasks(self, query: str, k: int = 3) -> List[Dict]:
        """获取相似任务的经验"""
        return self.evolution.get_similar_experiences(query, k=k)

# ============ CLI入口 ============

async def main():
    """CLI入口"""
    import sys

    agent = HermesAGI()

    if len(sys.argv) > 1:
        # 命令行模式
        user_input = " ".join(sys.argv[1:])
        print(f"\n[Hermes-AGI v2.0] 收到任务: {user_input}\n")

        result = await agent.process(user_input)

        print(result.output)
        print(f"\n[Hermes-AGI] 执行完成")
        print(f"  耗时: {result.metrics.get('duration', 0):.2f}秒")
        print(f"  健康分数: {agent.get_health_score():.2f}")

        # 显示进化统计
        stats = agent.evolution.get_stats()
        print(f"\n[Evolution v2.0] 统计:")
        print(f"  总任务数: {stats['total_tasks']}")
        print(f"  成功率: {stats.get('success_rate', 0)*100:.0f}%")
        print(f"  健康分数: {stats.get('health_score', 0)*100:.0f}%")
        print(f"  模式数: {stats.get('patterns_count', 0)}")

        # 显示健康监控详情
        if 'health_stats' in stats:
            hs = stats['health_stats']
            print(f"\n[HealthMonitor] 详情:")
            print(f"  成功任务: {hs.get('successful_tasks', 0)}")
            print(f"  失败任务: {hs.get('failed_tasks', 0)}")
            print(f"  重试次数: {hs.get('retried_tasks', 0)}")
            print(f"  平均执行时间: {hs.get('avg_execution_time', 0):.2f}秒")
    else:
        # 交互模式
        print("Hermes-AGI Agent Runtime v2.0")
        print("=" * 40)
        print("优化: 重试机制、错误分类、健康监控、真实进化")
        print("输入任务描述，或输入 'quit' 退出")
        print("输入 'health' 查看健康状态")
        print()

        while True:
            try:
                user_input = input("用户> ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                if user_input.lower() == 'health':
                    stats = agent.evolution.get_stats()
                    print(f"\n[健康状态]")
                    print(f"  健康分数: {stats.get('health_score', 0)*100:.0f}%")
                    print(f"  总任务: {stats.get('total_tasks', 0)}")
                    print(f"  成功率: {stats.get('success_rate', 0)*100:.0f}%")
                    print()
                    continue
                if not user_input:
                    continue

                print()
                result = await agent.process(user_input)
                print(result.output)
                print(f"\n健康分数: {agent.get_health_score():.2f}")
                print()

            except KeyboardInterrupt:
                print("\n再见!")
                break

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())