"""
天问-AGI 认知引擎与规划引擎
CognitiveEngine - 理解用户输入，意图识别
PlanningEngine - 分解任务并制定执行计划
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


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
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        intent = self._recognize_intent(user_input)
        entities = self._extract_entities(user_input)
        skills = self._match_skills(user_input)
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
        for pattern, intent in self.intent_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return intent
        return IntentType.QUERY

    def _extract_entities(self, text: str) -> List[Entity]:
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
        matched = []
        text_lower = text.lower()
        for skill, keywords in self.skill_keywords.items():
            if any(kw.lower() in text_lower for kw in keywords):
                matched.append(skill)
        if not matched:
            matched = ['General']
        return matched

    def _assess_complexity(self, text: str) -> str:
        complexity_indicators = {
            'high': [r'完整', r'系统', r'复杂', r'微服务'],
            'medium': [r'组件', r'模块', r'api', r'接口'],
            'low': [r'简单', r'单个', r'一个'],
        }
        for level, patterns in complexity_indicators.items():
            if any(re.search(p, text) for p in patterns):
                return level
        return 'medium'


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
        main_skills = task_model.required_skills
        if not main_skills or main_skills == ['General']:
            main_skills = ['Product']

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

        parallel_groups = self._create_parallel_groups(subtasks)

        return ExecutionPlan(
            task_id=task_model.id,
            subtasks=subtasks,
            parallel_groups=parallel_groups,
            estimated_time=self._estimate_time(len(subtasks)),
            risks=self._assess_risks(subtasks)
        )

    def _create_parallel_groups(self, subtasks: List[SubTask]) -> List[List[str]]:
        if len(subtasks) <= 2:
            return [[t.id] for t in subtasks]

        groups = []
        for i in range(0, len(subtasks), 2):
            group = [t.id for t in subtasks[i:i+2] if i == 0 or subtasks[i].dependencies]
            if group:
                groups.append(group)
        return groups if groups else [[subtasks[0].id]]

    def _estimate_time(self, subtask_count: int) -> str:
        hours = subtask_count * 0.5
        if hours < 1:
            return f"{int(hours * 60)}分钟"
        return f"{hours:.1f}小时"

    def _assess_risks(self, subtasks: List[SubTask]) -> List[str]:
        risks = []
        if len(subtasks) > 5:
            risks.append("任务较多，可能需要分批执行")
        if any(s.skill in ['Architecture', 'Database'] for s in subtasks):
            risks.append("涉及架构设计，需要充分沟通")
        return risks
