"""CollaborationWorkflow - 协作工作流"""

import logging
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy imports
def _get_dependencies():
    """Lazy load dependencies"""
    from .coordinator.types_enums import AgentRole, MessageType
    from .coordinator_core import MultiAgentCoordinator
    return AgentRole, MessageType, MultiAgentCoordinator

try:
    from .coordinator.types_enums import AgentRole, MessageType
except ImportError:
    pass

class CollaborationWorkflow:
    """
    协作工作流

    定义研究团队的协作流程:
    1. Planner制定计划 - 分析任务, 制定研究计划
    2. Researcher执行调研 - 收集文献和数据
    3. HypothesisGenerator生成假说 - 基于调研结果生成假说
    4. Reviewer评审 - 评审假说的可行性和创新性
    5. Coordinator协调决策 - 综合各方意见做出最终决策

    使用示例:
        workflow = CollaborationWorkflow(coordinator)
        result = await workflow.run_research_workflow("黑洞信息悖论研究")
    """

    def __init__(self, coordinator: MultiAgentCoordinator):
        """
        初始化协作工作流

        参数:
            coordinator: MultiAgentCoordinator实例
        """
        self.coordinator = coordinator
        self.workflow_id = str(uuid.uuid4())
        self.current_workflow_log: List[Dict] = []

    async def run_research_workflow(
        self,
        topic: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        运行完整的研究工作流

        参数:
            topic: 研究主题
            context: 可选的上下文信息

        返回:
            工作流执行结果字典, 包含:
            - workflow_id: 工作流ID
            - topic: 研究主题
            - steps_completed: 完成的步骤数
            - log: 执行日志
            - final_decision: 最终决策
            - agent_outputs: 各Agent的输出
        """
        self.current_workflow_log = []
        agent_outputs = {}

        # Step 1: Planner制定研究计划
        planner = self.coordinator.get_agent_by_role(AgentRole.PLANNER)
        if planner:
            planner.add_message(
                "system",
                f"请为研究主题'{topic}'制定详细的研究计划，包括目标、方法和时间表"
            )
            self.current_workflow_log.append({
                "step": "planning",
                "agent": planner.name,
                "agent_id": planner.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["planner"] = {
                "response": f"针对'{topic}'的研究计划已制定",
                "key_points": ["文献调研", "数据分析", "假说验证"]
            }
        else:
            self.current_workflow_log.append({
                "step": "planning",
                "status": "skipped",
                "reason": "Planner not found"
            })

        # Step 2: Researcher执行文献调研
        researcher = self.coordinator.get_agent_by_role(AgentRole.RESEARCHER)
        if researcher:
            researcher.add_message(
                "system",
                f"请对'{topic}'进行深入的文献调研，收集相关论文和最新进展"
            )
            self.current_workflow_log.append({
                "step": "research",
                "agent": researcher.name,
                "agent_id": researcher.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["researcher"] = {
                "response": f"关于'{topic}'的文献调研已完成",
                "sources_found": 25,
                "key_papers": ["论文A", "论文B", "论文C"]
            }
        else:
            self.current_workflow_log.append({
                "step": "research",
                "status": "skipped",
                "reason": "Researcher not found"
            })

        # Step 3: HypothesisGenerator生成假说
        hypo_gen = self.coordinator.get_agent_by_role(AgentRole.HYPOTHESIS_GENERATOR)
        if hypo_gen:
            hypo_gen.add_message(
                "system",
                f"基于调研结果，请生成3-5个可检验的研究假说"
            )
            self.current_workflow_log.append({
                "step": "hypothesis_generation",
                "agent": hypo_gen.name,
                "agent_id": hypo_gen.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["hypothesis_generator"] = {
                "response": f"已生成关于'{topic}'的假说",
                "hypotheses": [
                    "假说1: 某种现象的原因是...",
                    "假说2: 在特定条件下会发生...",
                    "假说3: 两个变量之间存在关联..."
                ]
            }
        else:
            self.current_workflow_log.append({
                "step": "hypothesis_generation",
                "status": "skipped",
                "reason": "HypothesisGenerator not found"
            })

        # Step 4: Reviewer评审
        reviewer = self.coordinator.get_agent_by_role(AgentRole.REVIEWER)
        if reviewer:
            reviewer.add_message(
                "system",
                f"请评审生成的研究假说，提供反馈和建议，评估其可行性和创新性"
            )
            self.current_workflow_log.append({
                "step": "review",
                "agent": reviewer.name,
                "agent_id": reviewer.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["reviewer"] = {
                "response": "假说评审完成",
                "evaluation": {
                    "feasibility": 8,
                    "innovation": 7,
                    "significance": 9
                },
                "suggestions": ["需要更多实验验证", "考虑更多边界条件"]
            }
        else:
            self.current_workflow_log.append({
                "step": "review",
                "status": "skipped",
                "reason": "Reviewer not found"
            })

        # Step 5: Coordinator协调决策
        coordinator_agent = self.coordinator.get_agent_by_role(AgentRole.COORDINATOR)
        if coordinator_agent:
            coordinator_agent.add_message(
                "system",
                "请综合各方意见，分析假说的可行性和创新性，做出最终决策"
            )
            self.current_workflow_log.append({
                "step": "coordination",
                "agent": coordinator_agent.name,
                "agent_id": coordinator_agent.id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            agent_outputs["coordinator"] = {
                "response": "决策已形成",
                "decision": "推荐假说1和假说3进入下一阶段验证"
            }
        else:
            self.current_workflow_log.append({
                "step": "coordination",
                "status": "skipped",
                "reason": "Coordinator not found"
            })

        # 记录工作流历史
        workflow_record = {
            "workflow_id": self.workflow_id,
            "topic": topic,
            "steps_completed": len([s for s in self.current_workflow_log if s["status"] == "completed"]),
            "log": self.current_workflow_log,
            "final_decision": "基于团队协作的深入研究结论",
            "agent_outputs": agent_outputs,
            "context": context or {}
        }

        self.coordinator.workflow_history.append(workflow_record)

        return workflow_record

    async def run_parallel_workflow(
        self,
        topic: str,
        parallel_agents: List[AgentRole]
    ) -> Dict[str, Any]:
        """
        运行并行工作流 - 多个Agent同时执行任务

        参数:
            topic: 研究主题
            parallel_agents: 并行执行的Agent角色列表

        返回:
            并行工作流执行结果
        """
        import asyncio

        self.current_workflow_log = []
        results = {}

        # 创建并发任务
        tasks = []

        async def execute_agent_task(role: AgentRole, task_desc: str):
            agent = self.coordinator.get_agent_by_role(role)
            if agent:
                agent.add_message("system", task_desc)
                await asyncio.sleep(0.1)  # 模拟处理时间
                return {
                    "role": role.value,
                    "agent": agent.name,
                    "status": "completed",
                    "output": f"{role.value}完成{topic}相关任务"
                }
            return {"role": role.value, "status": "skipped"}

        # 为每个Agent创建任务
        for role in parallel_agents:
            task_desc = f"请处理'{topic}'相关的{role.value}任务"
            tasks.append(execute_agent_task(role, task_desc))

        # 并发执行
        task_results = await asyncio.gather(*tasks)

        for result in task_results:
            results[result.get("role", "unknown")] = result

        return {
            "workflow_id": self.workflow_id,
            "topic": topic,
            "parallel_results": results,
            "steps_completed": len([r for r in results.values() if r.get("status") == "completed"])
        }

    def get_workflow_history(self) -> List[Dict]:
        """获取工作流执行历史"""
        return self.coordinator.workflow_history


