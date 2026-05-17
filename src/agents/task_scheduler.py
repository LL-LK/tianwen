"""
Task Scheduling Module - 任务调度模块

提取自 coordinator.py 的任务调度类:
- TaskDecomposer: 任务分解器
- ParallelScheduler: 并行调度器
- ParallelCoordinator: 并行协调器

依赖类:
- SubTask, TaskDecompositionResult

Author: Tianwen-AGI Team
Date: 2026/05/16
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set

logger = logging.getLogger(__name__)

# Lazy imports for backward compatibility with coordinator.py
# These are imported inside methods to avoid circular dependencies


# ============================================================================
# 子任务和结果类
# ============================================================================

@dataclass
class SubTask:
    """
    子任务 - 任务分解后的执行单元

    属性:
    - id: 子任务唯一标识
    - name: 子任务名称
    - description: 子任务描述
    - assigned_agent_id: 分配的Agent ID
    - status: 任务状态
    - dependencies: 依赖的子任务ID列表
    - result: 执行结果
    - error: 错误信息
    - priority: 优先级 (1-10)
    - estimated_time: 预估执行时间(秒)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    assigned_agent_id: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    priority: int = 5
    estimated_time: float = 1.0

    def is_ready(self, completed_task_ids: Set[str]) -> bool:
        """检查依赖是否满足"""
        return all(dep_id in completed_task_ids for dep_id in self.dependencies)


@dataclass
class TaskDecompositionResult:
    """任务分解结果"""
    original_task: str
    subtasks: List[SubTask]
    parallel_groups: List[List[str]]  # 可以并行执行的子任务组
    total_estimated_time: float
    risks: List[str] = field(default_factory=list)


# ============================================================================
# TaskDecomposer - 任务分解器
# ============================================================================

class TaskDecomposer:
    """
    任务分解器 - 将复杂任务分解为并行子任务

    功能:
    - 分析任务复杂度
    - 识别可并行的子任务
    - 构建依赖图
    - 生成执行计划

    使用示例:
        decomposer = TaskDecomposer(coordinator)
        result = decomposer.decompose("分析太阳系行星轨道数据")
        for group in result.parallel_groups:
            # 每组可以并行执行
            await scheduler.schedule([subtasks[i] for i in group])
    """

    def __init__(self, coordinator: 'MultiAgentCoordinator'):
        self.coordinator = coordinator

        # 任务模式库 - 不同类型任务的分解模板
        self.task_patterns = {
            "research": {
                "subtasks": ["文献调研", "数据分析", "假说生成", "验证实验", "结论整理"],
                "parallel_pairs": [["文献调研", "数据分析"], ["假说生成", "验证实验"]]
            },
            "observation": {
                "subtasks": ["目标规划", "设备检查", "数据采集", "数据处理", "结果分析"],
                "parallel_pairs": [["目标规划", "设备检查"]]
            },
            "analysis": {
                "subtasks": ["数据收集", "数据清洗", "统计分析", "可视化", "报告生成"],
                "parallel_pairs": [["数据收集", "数据清洗"]]
            },
            "development": {
                "subtasks": ["需求分析", "架构设计", "编码实现", "测试验证", "部署上线"],
                "parallel_pairs": [["需求分析", "架构设计"]]
            }
        }

        # 技能到Agent角色的映射
        self.skill_role_mapping = {
            "文献调研": "researcher",
            "数据分析": "data_analyst",
            "假说生成": "hypothesis_generator",
            "验证实验": "observation_executor",
            "结论整理": "coordinator",
            "目标规划": "planner",
            "设备检查": "observation_executor",
            "数据采集": "observation_executor",
            "数据处理": "data_analyst",
            "结果分析": "researcher",
            "数据收集": "researcher",
            "数据清洗": "data_analyst",
            "统计分析": "data_analyst",
            "可视化": "data_analyst",
            "报告生成": "coordinator",
            "需求分析": "planner",
            "架构设计": "planner",
            "编码实现": "executor",
            "测试验证": "reviewer",
            "部署上线": "executor"
        }

    def _get_agent_role_enum(self, role_name: str):
        """获取AgentRole枚举"""
        from .coordinator import AgentRole
        role_mapping = {
            "researcher": AgentRole.RESEARCHER,
            "data_analyst": AgentRole.DATA_ANALYST,
            "hypothesis_generator": AgentRole.HYPOTHESIS_GENERATOR,
            "observation_executor": AgentRole.OBSERVATION_EXECUTOR,
            "coordinator": AgentRole.COORDINATOR,
            "planner": AgentRole.PLANNER,
            "executor": AgentRole.EXECUTOR,
            "reviewer": AgentRole.REVIEWER,
        }
        return role_mapping.get(role_name, AgentRole.EXECUTOR)

    def _select_agent_for_task(self, task: 'SubTask'):
        """为任务选择最合适的Agent (内部使用)"""
        role_name = self.skill_role_mapping.get(task.name, "executor")
        role = self._get_agent_role_enum(role_name)
        return self.coordinator.get_agent_by_role(role)

    def decompose(self, task: str, task_type: Optional[str] = None) -> TaskDecompositionResult:
        """
        分解任务为并行子任务

        参数:
            task: 原始任务描述
            task_type: 任务类型 (可选, 自动推断)

        返回:
            TaskDecompositionResult: 包含分解后的子任务和并行组
        """
        # 自动推断任务类型
        if task_type is None:
            task_type = self._infer_task_type(task)

        # 获取任务模式
        pattern = self.task_patterns.get(task_type, {
            "subtasks": ["任务规划", "任务执行", "结果验证", "总结报告"],
            "parallel_pairs": [["任务规划", "任务执行"]]
        })

        # 生成子任务
        subtasks = []
        subtask_id_base = f"SUB-{uuid.uuid4().hex[:8]}"

        for i, subtask_name in enumerate(pattern["subtasks"]):
            role_name = self.skill_role_mapping.get(subtask_name, "executor")
            role_enum = self._get_agent_role_enum(role_name)

            # 构建依赖关系
            dependencies = []
            if i > 0 and i - 1 < len(subtasks):
                # 默认依赖前一个任务
                dependencies = [subtasks[i - 1].id]

            subtask = SubTask(
                id=f"{subtask_id_base}-{i + 1}",
                name=subtask_name,
                description=f"{subtask_name}: {task}",
                priority=min(10, 5 + (len(pattern["subtasks"]) - i)),
                estimated_time=self._estimate_subtask_time(subtask_name),
                dependencies=dependencies
            )
            subtasks.append(subtask)

        # 分析并行组
        parallel_groups = self._analyze_parallel_groups(subtasks, pattern.get("parallel_pairs", []))

        # 评估风险
        risks = self._assess_risks(subtasks)

        return TaskDecompositionResult(
            original_task=task,
            subtasks=subtasks,
            parallel_groups=parallel_groups,
            total_estimated_time=sum(s.estimated_time for s in subtasks),
            risks=risks
        )

    def _infer_task_type(self, task: str) -> str:
        """推断任务类型"""
        task_lower = task.lower()

        type_keywords = {
            "research": ["研究", "调研", "分析", "探索"],
            "observation": ["观测", "观察", "监测", "探测"],
            "analysis": ["分析", "处理", "统计", "计算"],
            "development": ["开发", "实现", "编写", "构建", "设计"]
        }

        for type_name, keywords in type_keywords.items():
            if any(kw in task_lower for kw in keywords):
                return type_name

        return "research"  # 默认类型

    def _estimate_subtask_time(self, subtask_name: str) -> float:
        """预估子任务执行时间"""
        time_estimates = {
            "文献调研": 5.0,
            "数据分析": 4.0,
            "假说生成": 3.0,
            "验证实验": 6.0,
            "结论整理": 2.0,
            "目标规划": 2.0,
            "设备检查": 3.0,
            "数据采集": 5.0,
            "数据处理": 4.0,
            "结果分析": 3.0,
            "数据收集": 4.0,
            "数据清洗": 3.0,
            "统计分析": 4.0,
            "可视化": 2.0,
            "报告生成": 2.0,
            "需求分析": 3.0,
            "架构设计": 4.0,
            "编码实现": 8.0,
            "测试验证": 5.0,
            "部署上线": 3.0
        }
        return time_estimates.get(subtask_name, 3.0)

    def _analyze_parallel_groups(
        self,
        subtasks: List[SubTask],
        parallel_pairs: List[List[str]]
    ) -> List[List[str]]:
        """分析可并行的任务组"""
        if not parallel_pairs:
            # 默认: 相邻任务如果无依赖可以并行
            groups = []
            current_group = []
            for i, subtask in enumerate(subtasks):
                if i > 0 and not subtask.dependencies:
                    current_group.append(subtask.id)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [subtask.id]
            if current_group:
                groups.append(current_group)
            return groups

        # 使用预定义的并行对
        groups = []
        for pair in parallel_pairs:
            group = []
            for subtask in subtasks:
                if subtask.name in pair:
                    group.append(subtask.id)
            if len(group) > 1:
                groups.append(group)

        # 添加单独的任务
        assigned = set()
        for group in groups:
            assigned.update(group)

        for subtask in subtasks:
            if subtask.id not in assigned:
                groups.append([subtask.id])

        return groups

    def _assess_risks(self, subtasks: List[SubTask]) -> List[str]:
        """评估任务风险"""
        risks = []

        if len(subtasks) > 7:
            risks.append("任务较多，可能需要分批执行")

        # 检查关键路径
        critical_skills = {"验证实验", "编码实现", "架构设计"}
        critical = [s for s in subtasks if s.name in critical_skills]
        if len(critical) > 2:
            risks.append("关键任务较多，建议密切监控")

        # 检查依赖深度
        max_depth = self._calculate_dependency_depth(subtasks)
        if max_depth > 4:
            risks.append("依赖链较长，任务延迟可能影响整体")

        return risks

    def _calculate_dependency_depth(self, subtasks: List[SubTask]) -> int:
        """计算依赖深度"""
        depth_map = {}

        def get_depth(subtask_id: str) -> int:
            if subtask_id in depth_map:
                return depth_map[subtask_id]

            subtask = next((s for s in subtasks if s.id == subtask_id), None)
            if not subtask or not subtask.dependencies:
                depth_map[subtask_id] = 1
                return 1

            max_child_depth = max(get_depth(d) for d in subtask.dependencies)
            depth_map[subtask_id] = max_child_depth + 1
            return depth_map[subtask_id]

        return max(get_depth(s.id) for s in subtasks) if subtasks else 0


# ============================================================================
# ParallelScheduler - 并行调度器
# ============================================================================

class ParallelScheduler:
    """
    并行调度器 - 管理多Agent并行执行

    功能:
    - 调度多Agent并行执行子任务
    - 监控执行状态
    - 处理任务完成和失败
    - 汇总执行结果

    使用示例:
        scheduler = ParallelScheduler(coordinator)
        results = await scheduler.schedule(decomposition_result.subtasks)
    """

    def __init__(self, coordinator: 'MultiAgentCoordinator'):
        self.coordinator = coordinator
        self.active_tasks: Dict[str, SubTask] = {}
        self.completed_tasks: Dict[str, SubTask] = {}
        self.failed_tasks: Dict[str, SubTask] = {}

    async def schedule(self, subtasks: List[SubTask]) -> List[SubTask]:
        """
        并行调度子任务执行

        参数:
            subtasks: 子任务列表

        返回:
            执行完成的子任务列表
        """
        import asyncio

        # 初始化任务状态
        for task in subtasks:
            task.status = "pending"
            self.active_tasks[task.id] = task

        # 按依赖分组执行
        completed_ids: Set[str] = set()
        all_completed: List[SubTask] = []

        while self.active_tasks:
            # 找出所有可执行的任务（依赖已满足）
            ready_tasks = [
                task for task in self.active_tasks.values()
                if task.is_ready(completed_ids)
            ]

            if not ready_tasks:
                # 没有可执行的任务，可能有循环依赖
                break

            # 并行执行所有就绪的任务
            async def execute_single(task: SubTask) -> SubTask:
                return await self._execute_task(task)

            # 等待所有任务完成
            results = await asyncio.gather(
                *[execute_single(t) for t in ready_tasks],
                return_exceptions=True
            )

            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    # 处理异常
                    continue

                task = result
                if task.status == "completed":
                    completed_ids.add(task.id)
                    self.completed_tasks[task.id] = task
                    del self.active_tasks[task.id]
                    all_completed.append(task)
                elif task.status == "failed":
                    self.failed_tasks[task.id] = task
                    del self.active_tasks[task.id]

        return all_completed

    async def schedule_parallel_groups(
        self,
        subtasks: List[SubTask],
        parallel_groups: List[List[str]]
    ) -> List[SubTask]:
        """
        按并行组调度任务

        参数:
            subtasks: 所有子任务
            parallel_groups: 并行组 (每组内的任务可并行)

        返回:
            执行完成的子任务列表
        """
        import asyncio

        subtask_map = {s.id: s for s in subtasks}
        all_completed: List[SubTask] = []
        completed_ids: Set[str] = set()

        for group in parallel_groups:
            # 获取组内任务
            group_tasks = [subtask_map[tid] for tid in group if tid in subtask_map]

            # 过滤掉依赖未满足的任务
            ready_tasks = [t for t in group_tasks if t.is_ready(completed_ids)]

            if not ready_tasks:
                continue

            # 并行执行组内任务
            async def execute_single(task: SubTask) -> SubTask:
                return await self._execute_task(task)

            results = await asyncio.gather(
                *[execute_single(t) for t in ready_tasks],
                return_exceptions=True
            )

            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    continue

                task = result
                if task.status == "completed":
                    completed_ids.add(task.id)
                    self.completed_tasks[task.id] = task
                    all_completed.append(task)
                elif task.status == "failed":
                    self.failed_tasks[task.id] = task

        return all_completed

    async def _execute_task(self, task: SubTask) -> SubTask:
        """执行单个子任务"""
        import asyncio

        # 分配Agent
        if not task.assigned_agent_id:
            agent = self._select_agent_for_task(task)
            if agent:
                task.assigned_agent_id = agent.id

        task.status = "running"

        try:
            # 模拟任务执行
            # 实际应该调用Agent的执行能力
            await asyncio.sleep(task.estimated_time * 0.1)  # 模拟执行

            # 更新任务状态
            task.status = "completed"
            task.result = f"Task {task.name} completed successfully"

            # 更新Agent性能
            if task.assigned_agent_id:
                agent = self.coordinator.get_agent(task.assigned_agent_id)
                if agent:
                    agent.increment_performance(success=True)
                    agent.add_message(
                        "system",
                        f"完成任务: {task.name}",
                        metadata={"task_id": task.id, "status": "completed"}
                    )

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

            # 更新Agent性能
            if task.assigned_agent_id:
                agent = self.coordinator.get_agent(task.assigned_agent_id)
                if agent:
                    agent.increment_performance(success=False)

        return task

    def _select_agent_for_task(self, task: SubTask):
        """为任务选择最合适的Agent"""
        # 使用TaskDecomposer的技能角色映射
        decomposer = TaskDecomposer(self.coordinator)
        role_name = decomposer.skill_role_mapping.get(task.name, "executor")
        role_enum = decomposer._get_agent_role_enum(role_name)

        # 查找对应角色的Agent
        agent = self.coordinator.get_agent_by_role(role_enum)
        return agent

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "total_tasks": len(self.completed_tasks) + len(self.failed_tasks) + len(self.active_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "active": len(self.active_tasks),
            "success_rate": (
                len(self.completed_tasks) /
                (len(self.completed_tasks) + len(self.failed_tasks))
                if (len(self.completed_tasks) + len(self.failed_tasks)) > 0
                else 0.0
            )
        }


# ============================================================================
# ParallelCoordinator - 并行协调器
# ============================================================================

class ParallelCoordinator:
    """
    并行协调器 - 整合任务分解和并行调度

    提供完整的任务分解->调度->汇总流程

    使用示例:
        coordinator = ParallelCoordinator(multi_agent_coordinator)
        result = await coordinator.process_task("分析天文观测数据")
    """

    def __init__(self, multi_agent_coordinator: 'MultiAgentCoordinator'):
        self.coordinator = multi_agent_coordinator
        self.decomposer = TaskDecomposer(multi_agent_coordinator)
        self.scheduler = ParallelScheduler(multi_agent_coordinator)

    async def process_task(
        self,
        task: str,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理完整任务流程

        参数:
            task: 任务描述
            task_type: 任务类型 (可选)

        返回:
            包含执行结果的字典
        """
        # 1. 分解任务
        decomposition = self.decomposer.decompose(task, task_type)

        # 2. 分配Agent角色
        for subtask in decomposition.subtasks:
            agent = self.decomposer._select_agent_for_task(subtask)
            if agent:
                subtask.assigned_agent_id = agent.id

        # 3. 按并行组调度执行
        completed = await self.scheduler.schedule_parallel_groups(
            decomposition.subtasks,
            decomposition.parallel_groups
        )

        # 4. 汇总结果
        summary = self.scheduler.get_execution_summary()

        return {
            "original_task": task,
            "task_type": task_type or self.decomposer._infer_task_type(task),
            "decomposition": {
                "total_subtasks": len(decomposition.subtasks),
                "parallel_groups": len(decomposition.parallel_groups),
                "estimated_time": decomposition.total_estimated_time,
                "risks": decomposition.risks
            },
            "execution": {
                "completed": len(completed),
                "failed": summary["failed"],
                "success_rate": summary["success_rate"]
            },
            "subtasks": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "result": s.result,
                    "agent_id": s.assigned_agent_id
                }
                for s in decomposition.subtasks
            ]
        }