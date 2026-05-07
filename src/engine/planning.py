"""
规划引擎

负责任务分解、执行计划制定和资源调度。
"""

from typing import Optional, Dict, Any, List, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


class PlanStatus(Enum):
    """计划状态枚举"""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class PlanStep:
    """计划步骤"""
    id: str
    name: str
    description: Optional[str] = None
    status: str = "pending"
    estimated_duration: float = 0.0
    actual_duration: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    order: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def is_ready(self, completed_steps: Set[str]) -> bool:
        """判断步骤是否就绪（依赖都已完成）"""
        return all(dep in completed_steps for dep in self.dependencies)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "dependencies": self.dependencies,
            "resources": self.resources,
            "order": self.order,
            "result": self.result,
            "error": self.error
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    id: str
    task_id: str
    title: str
    description: Optional[str] = None
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_total_duration: float = 0.0
    actual_total_duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, name: str, **kwargs) -> PlanStep:
        """添加步骤"""
        step = PlanStep(
            id=f"{self.id}-step-{len(self.steps)}",
            name=name,
            order=len(self.steps),
            **kwargs
        )
        self.steps.append(step)
        self.estimated_total_duration += step.estimated_duration
        return step
    
    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_ready_steps(self, completed: Set[str]) -> List[PlanStep]:
        """获取就绪的步骤（依赖已完成的步骤）"""
        return [s for s in self.steps if s.status == "pending" and s.is_ready(completed)]
    
    def get_completed_steps(self) -> List[PlanStep]:
        """获取已完成的步骤"""
        return [s for s in self.steps if s.status == "completed"]
    
    def get_failed_step(self) -> Optional[PlanStep]:
        """获取失败的步骤"""
        for step in self.steps:
            if step.status == "failed":
                return step
        return None
    
    def get_step_by_name(self, name: str) -> Optional[PlanStep]:
        """根据名称获取步骤"""
        for step in self.steps:
            if step.name == name:
                return step
        return None
    
    def progress(self) -> float:
        """计算进度百分比"""
        if not self.steps:
            return 0.0
        completed = len([s for s in self.steps if s.status == "completed"])
        return (completed / len(self.steps)) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress(),
            "steps": [s.to_dict() for s in self.steps],
            "estimated_total_duration": self.estimated_total_duration,
            "actual_total_duration": self.actual_total_duration,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata
        }


class TaskTemplate:
    """任务模板"""
    
    TEMPLATES = {
        "observation": {
            "name": "天文观测任务模板",
            "steps": [
                ("验证设备状态", 30, ["telescope"], []),
                ("定位目标天体", 60, ["mount"], []),
                ("设置相机参数", 15, ["camera"], []),
                ("执行图像拍摄", 120, ["camera", "mount"], ["设置相机参数"]),
                ("保存原始数据", 10, ["storage"], ["执行图像拍摄"]),
                ("生成观测报告", 20, [], ["保存原始数据"]),
            ]
        },
        "analysis": {
            "name": "数据分析任务模板",
            "steps": [
                ("加载数据源", 30, ["storage"], []),
                ("数据预处理", 60, ["computing"], ["加载数据源"]),
                ("特征提取", 120, ["computing"], ["数据预处理"]),
                ("模式分析", 180, ["computing"], ["特征提取"]),
                ("结果可视化", 30, ["computing"], ["模式分析"]),
                ("生成分析报告", 30, [], ["结果可视化"]),
            ]
        },
        "research": {
            "name": "科研探索任务模板",
            "steps": [
                ("文献检索", 60, ["database"], []),
                ("构建研究假说", 120, [], ["文献检索"]),
                ("设计验证方案", 60, [], ["构建研究假说"]),
                ("收集实验证据", 300, ["telescope", "computing"], ["设计验证方案"]),
                ("假说验证分析", 180, ["computing"], ["收集实验证据"]),
                ("撰写研究论文", 120, [], ["假说验证分析"]),
            ]
        },
        "exploration": {
            "name": "星空探索任务模板",
            "steps": [
                ("规划巡天区域", 30, ["database"], []),
                ("扫描目标天区", 120, ["telescope"], ["规划巡天区域"]),
                ("目标检测识别", 60, ["computing"], ["扫描目标天区"]),
                ("天体分类标注", 30, ["computing"], ["目标检测识别"]),
                ("生成天体地图", 30, [], ["天体分类标注"]),
            ]
        },
        "learning": {
            "name": "系统学习任务模板",
            "steps": [
                ("收集学习样本", 60, ["database"], []),
                ("数据预处理", 30, ["computing"], ["收集学习样本"]),
                ("模型训练", 300, ["computing"], ["数据预处理"]),
                ("效果评估", 60, ["computing"], ["模型训练"]),
                ("参数优化", 120, ["computing"], ["效果评估"]),
                ("生成训练报告", 30, [], ["参数优化"]),
            ]
        }
    }
    
    @classmethod
    def get_template(cls, task_type: str) -> Optional[Dict]:
        return cls.TEMPLATES.get(task_type)
    
    @classmethod
    def list_templates(cls) -> List[str]:
        return list(cls.TEMPLATES.keys())


class DependencyGraph:
    """依赖图分析器"""
    
    def __init__(self, steps: List[PlanStep]):
        self.steps = steps
        self.graph = self._build_graph()
        self.in_degree = self._calculate_in_degree()
    
    def _build_graph(self) -> Dict[str, List[str]]:
        """构建邻接表"""
        graph = defaultdict(list)
        for step in self.steps:
            graph[step.id] = step.dependencies
        return graph
    
    def _calculate_in_degree(self) -> Dict[str, int]:
        """计算入度"""
        in_degree = defaultdict(int)
        for step in self.steps:
            in_degree[step.id] = 0
        for step in self.steps:
            for dep in step.dependencies:
                in_degree[step.id] += 1
        return in_degree
    
    def has_cycle(self) -> bool:
        """检测环"""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.graph:
            if node not in visited:
                if dfs(node):
                    return True
        return False
    
    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        if self.has_cycle():
            return []
        
        in_degree = self.in_degree.copy()
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self.graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result if len(result) == len(self.steps) else []


class PlanningEngine:
    """规划引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger("planning-engine")
        self.templates = TaskTemplate()
    
    def create_plan(self, task_model) -> ExecutionPlan:
        """根据任务模型创建执行计划"""
        plan_id = f"plan-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        plan = ExecutionPlan(
            id=plan_id,
            task_id=getattr(task_model, 'id', f"task-{plan_id}"),
            title=task_model.title,
            description=task_model.description if hasattr(task_model, 'description') else None,
            metadata=getattr(task_model, 'metadata', {})
        )
        
        template = self.templates.get_template(task_model.type)
        if template:
            for name, duration, resources, dependencies in template["steps"]:
                plan.add_step(
                    name=name,
                    estimated_duration=duration,
                    resources=resources,
                    dependencies=dependencies
                )
        else:
            plan.add_step(
                name="执行任务",
                estimated_duration=60,
                resources=[],
                dependencies=[]
            )
        
        validation = self.validate_plan(plan)
        if validation["valid"]:
            plan.status = PlanStatus.VALIDATED
        
        self.logger.info(
            f"Created plan: {plan.title} | "
            f"Steps: {len(plan.steps)} | "
            f"Duration: {plan.estimated_total_duration}s"
        )
        
        return plan
    
    def validate_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """验证计划有效性"""
        errors = []
        warnings = []
        
        if not plan.steps:
            errors.append("计划没有任何步骤")
        
        dep_graph = DependencyGraph(plan.steps)
        
        if dep_graph.has_cycle():
            errors.append("计划存在循环依赖")
        
        sorted_steps = dep_graph.topological_sort()
        if not sorted_steps:
            warnings.append("无法进行拓扑排序，可能存在依赖问题")
        
        step_names = {s.name for s in plan.steps}
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in step_names:
                    errors.append(f"步骤 '{step.name}' 依赖的 '{dep}' 不存在")
        
        for step in plan.steps:
            if step.estimated_duration <= 0:
                warnings.append(f"步骤 '{step.name}' 的预估时长无效")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """优化执行计划"""
        return plan
    
    def estimate_duration(self, plan: ExecutionPlan) -> float:
        """估算执行时长"""
        return plan.estimated_total_duration
    
    def get_critical_path(self, plan: ExecutionPlan) -> List[str]:
        """获取关键路径"""
        dep_graph = DependencyGraph(plan.steps)
        sorted_steps = dep_graph.topological_sort()
        
        if not sorted_steps:
            return []
        
        return sorted_steps


import logging