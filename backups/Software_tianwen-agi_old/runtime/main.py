"""
Hermes-AGI Agent Runtime
运行时主入口 - 整合认知、规划、执行引擎
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

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

# ============ 自我进化系统 ============

class EvolutionSystem:
    """自我进化系统 - 持续学习和优化"""

    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = memory_dir
        self.task_history: List[Dict] = []
        self.patterns: List[Dict] = []

    def after_task(self, result: ExecutionResult):
        """任务完成后的自我进化钩子"""
        # 记录任务执行
        self._record_task(result)

        # 提取模式
        if result.status == TaskStatus.COMPLETED:
            self._extract_success_pattern(result)
        else:
            self._analyze_failure(result)

    def _record_task(self, result: ExecutionResult):
        """记录任务"""
        record = {
            'date': datetime.now().isoformat(),
            'task_id': result.task_model.id,
            'type': result.task_model.type.value,
            'skills': result.task_model.required_skills,
            'status': result.status.value,
            'duration': result.metrics.get('duration', 0),
            'subtask_count': len(result.plan.subtasks),
        }
        self.task_history.append(record)

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

    def _analyze_failure(self, result: ExecutionResult):
        """分析失败原因"""
        for error in result.errors:
            print(f"[Evolution] 失败分析: {error}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.task_history)
        if total == 0:
            return {'total_tasks': 0, 'success_rate': 0}

        successes = sum(1 for r in self.task_history if r['status'] == 'completed')
        return {
            'total_tasks': total,
            'success_rate': successes / total,
            'patterns_count': len(self.patterns),
        }

# ============ 主Agent类 ============

class HermesAGI:
    """Hermes-AGI 智能体主类"""

    def __init__(self, skill_dir: str = "./skills", memory_dir: str = "./memory"):
        self.cognitive = CognitiveEngine()
        self.planning = PlanningEngine()
        self.execution = ExecutionEngine(skill_dir)
        self.evolution = EvolutionSystem(memory_dir)

    async def process(self, user_input: str) -> ExecutionResult:
        """处理用户输入的完整流程"""
        start_time = datetime.now()

        # 1. 认知引擎 - 理解输入
        task_model = self.cognitive.process(user_input)

        # 2. 规划引擎 - 制定计划
        plan = self.planning.create_plan(task_model)

        # 3. 执行引擎 - 执行任务
        await self.execution.execute_plan(plan)

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()

        # 4. 构建结果
        result = ExecutionResult(
            status=TaskStatus.COMPLETED,
            output=self._format_output(plan),
            task_model=task_model,
            plan=plan,
            metrics={'duration': duration, 'subtasks_completed': len(plan.subtasks)}
        )

        # 5. 自我进化 - 学习经验
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
        lines.append(f"\n### 统计")
        lines.append(f"- 总任务数: {len(plan.subtasks)}")
        lines.append(f"- 预估时间: {plan.estimated_time}")
        if plan.risks:
            lines.append(f"- 风险提示: {'; '.join(plan.risks)}")
        return "\n".join(lines)

# ============ CLI入口 ============

async def main():
    """CLI入口"""
    import sys

    agent = HermesAGI()

    if len(sys.argv) > 1:
        # 命令行模式
        user_input = " ".join(sys.argv[1:])
        print(f"\n[Hermes-AGI] 收到任务: {user_input}\n")

        result = await agent.process(user_input)

        print(result.output)
        print(f"\n[Hermes-AGI] 执行完成，耗时 {result.metrics.get('duration', 0):.2f}秒")

        # 显示进化统计
        stats = agent.evolution.get_stats()
        print(f"\n[Evolution] 统计: {stats['total_tasks']}个任务, 成功率{stats.get('success_rate', 0)*100:.0f}%")
    else:
        # 交互模式
        print("Hermes-AGI Agent Runtime")
        print("=" * 40)
        print("输入任务描述，或输入 'quit' 退出")
        print()

        while True:
            try:
                user_input = input("用户> ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                if not user_input:
                    continue

                print()
                result = await agent.process(user_input)
                print(result.output)
                print()

            except KeyboardInterrupt:
                print("\n再见!")
                break

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())