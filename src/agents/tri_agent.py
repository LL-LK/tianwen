"""
天问-AGI 三Agent架构系统 v1.0
Tri-Agent System - 简化自4-Agent架构

架构:
- M1: 数据挖掘Agent (DataMiningAgent) - 文献调研、数据分析
- M2: 观测指导Agent (ObservationGuidanceAgent) - 假说生成、调度规划
- M3: 观测执行Agent (ObservationExecutionAgent) - 望远镜控制、执行

Author: Tianwen-AGI Architecture Team
Date: 2026/05/03
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Agent类型枚举"""
    DATA_MINING = "data_mining"
    OBSERVATION_GUIDANCE = "observation_guidance"
    OBSERVATION_EXECUTION = "observation_execution"


@dataclass
class AgentMessage:
    """Agent间消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: AgentType = AgentType.DATA_MINING
    receiver: Optional[AgentType] = None
    content: str = ""
    message_type: str = "task"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_broadcast(self) -> bool:
        return self.receiver is None


@dataclass
class Task:
    """任务定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType = AgentType.DATA_MINING
    description: str = ""
    priority: int = 0
    status: str = "pending"
    result: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class BaseAgent:
    """Agent基类"""

    def __init__(self, agent_type: AgentType, name: str):
        self.agent_type = agent_type
        self.name = name
        self.tasks: List[Task] = []
        self.message_queue: List[AgentMessage] = []
        self.is_running = False
        self._callbacks: Dict[str, Callable] = {}

    async def receive_message(self, message: AgentMessage):
        """接收消息"""
        self.message_queue.append(message)
        await self.process_message(message)

    async def process_message(self, message: AgentMessage):
        """处理消息 - 子类实现"""
        raise NotImplementedError

    async def send_message(self, message: AgentMessage, coordinator: "TriAgentCoordinator"):
        """发送消息"""
        await coordinator.route_message(message)

    def add_task(self, task: Task):
        """添加任务"""
        self.tasks.append(task)

    async def execute_task(self, task: Task) -> Any:
        """执行任务 - 子类实现"""
        raise NotImplementedError

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "name": self.name,
            "type": self.agent_type.value,
            "task_count": len(self.tasks),
            "message_count": len(self.message_queue),
            "is_running": self.is_running
        }


class DataMiningAgent(BaseAgent):
    """M1: 数据挖掘Agent"""

    def __init__(self):
        super().__init__(AgentType.DATA_MINING, "DataMiningAgent")
        self.research_results: Dict[str, Any] = {}

    async def process_message(self, message: AgentMessage):
        if message.message_type == "task":
            task = Task(agent_type=self.agent_type, description=message.content)
            self.add_task(task)
            result = await self.execute_task(task)
            return AgentMessage(
                sender=self.agent_type,
                receiver=AgentType.OBSERVATION_GUIDANCE,
                content=f"Research complete: {result.get('summary', '')}",
                message_type="result",
                metadata={"task_id": task.id, "result": result}
            )

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        task.status = "running"
        try:
            result = {
                "topic": task.description,
                "literature_count": 0,
                "patterns_found": [],
                "research_gaps": [],
                "summary": f"M1 completed data mining: {task.description[:50]}..."
            }
            task.status = "completed"
            task.result = result
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            return {"error": str(e)}


class ObservationGuidanceAgent(BaseAgent):
    """M2: 观测指导Agent"""

    def __init__(self):
        super().__init__(AgentType.OBSERVATION_GUIDANCE, "ObservationGuidanceAgent")
        self.hypotheses: List[Dict] = []
        self.schedules: List[Dict] = []

    async def process_message(self, message: AgentMessage):
        if message.message_type == "task":
            task = Task(agent_type=self.agent_type, description=message.content)
            self.add_task(task)
            result = await self.execute_task(task)
            return AgentMessage(
                sender=self.agent_type,
                receiver=AgentType.OBSERVATION_EXECUTION,
                content=f"Observation guidance: {result.get('target', '')}",
                message_type="result",
                metadata={"task_id": task.id, "result": result}
            )

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        task.status = "running"
        try:
            result = {
                "target": task.description,
                "hypotheses_generated": len(self.hypotheses),
                "schedule_priority": "high",
                "observation_plan": {
                    "target_name": task.description,
                    "optimal_time": "2026-05-04 02:00:00",
                    "priority": 1
                },
                "summary": f"M2 completed observation guidance: {task.description[:50]}..."
            }
            task.status = "completed"
            task.result = result
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            return {"error": str(e)}


class ObservationExecutionAgent(BaseAgent):
    """M3: 观测执行Agent"""

    def __init__(self):
        super().__init__(AgentType.OBSERVATION_EXECUTION, "ObservationExecutionAgent")
        self.observations: List[Dict] = []
        self.telescope_status = "idle"

    async def process_message(self, message: AgentMessage):
        if message.message_type == "task":
            task = Task(agent_type=self.agent_type, description=message.content)
            self.add_task(task)
            result = await self.execute_task(task)
            return AgentMessage(
                sender=self.agent_type,
                receiver=None,
                content=f"Observation complete: {result.get('status', '')}",
                message_type="result",
                metadata={"task_id": task.id, "result": result}
            )

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        task.status = "running"
        self.telescope_status = "executing"
        try:
            result = {
                "observation_id": str(uuid.uuid4()),
                "target": task.description,
                "status": "completed",
                "data_collected": {"images": 10, "exposure_time": 300, "quality": 0.95},
                "summary": f"M3 completed observation execution: {task.description[:50]}..."
            }
            self.observations.append(result)
            task.status = "completed"
            task.result = result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            result = {"error": str(e)}
        finally:
            self.telescope_status = "idle"
        return result


class TriAgentCoordinator:
    """三Agent协调器"""

    def __init__(self):
        self.agents: Dict[AgentType, BaseAgent] = {
            AgentType.DATA_MINING: DataMiningAgent(),
            AgentType.OBSERVATION_GUIDANCE: ObservationGuidanceAgent(),
            AgentType.OBSERVATION_EXECUTION: ObservationExecutionAgent(),
        }
        self.message_history: List[AgentMessage] = []
        self.task_history: List[Task] = []

    async def route_message(self, message: AgentMessage):
        """路由消息"""
        self.message_history.append(message)
        if message.receiver:
            target = self.agents.get(message.receiver)
            if target:
                await target.receive_message(message)
        else:
            for agent in self.agents.values():
                if agent.agent_type != message.sender:
                    await agent.receive_message(message)

    async def submit_task(self, description: str, agent_type: AgentType = AgentType.DATA_MINING) -> Task:
        """提交任务"""
        task = Task(agent_type=agent_type, description=description, priority=1)
        self.task_history.append(task)
        agent = self.agents.get(agent_type)
        if agent:
            agent.add_task(task)
            message = AgentMessage(
                sender=AgentType.DATA_MINING,
                receiver=agent_type,
                content=description,
                message_type="task",
                metadata={"task_id": task.id}
            )
            await self.route_message(message)
        return task

    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "agents": {at.value: agent.get_status() for at, agent in self.agents.items()},
            "total_messages": len(self.message_history),
            "total_tasks": len(self.task_history),
            "active_tasks": len([t for t in self.task_history if t.status == "running"])
        }

    def get_agent(self, agent_type: AgentType) -> BaseAgent:
        """获取指定Agent"""
        return self.agents.get(agent_type)


async def run_tri_agent_simulation():
    """运行三Agent模拟"""
    logger.info("=" * 60)
    logger.info("Tianwen-AGI Tri-Agent System Simulation")
    logger.info("=" * 60)

    coordinator = TriAgentCoordinator()

    logger.info("[1] Submit research task to M1...")
    task1 = await coordinator.submit_task("Kepler-186f exoplanet research", AgentType.DATA_MINING)
    logger.info(f"Task submitted: {task1.id}")

    await asyncio.sleep(0.1)

    logger.info("[2] System status:")
    status = coordinator.get_system_status()
    for agent_type, agent_status in status["agents"].items():
        logger.info(f"{agent_type}: {agent_status['task_count']} tasks")

    logger.info("[3] M1 data mining complete, submit to M2...")

    logger.info("=" * 60)
    logger.info("Simulation complete")
    logger.info("=" * 60)

    return coordinator.get_system_status()


if __name__ == "__main__":
    result = asyncio.run(run_tri_agent_simulation())
    logger.info(f"Final status: {result}")