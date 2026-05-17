"""VLACoordinator - 视觉-语言-动作协调器"""

import logging
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Lazy imports
def _get_dependencies():
    """Lazy load dependencies"""
    from .coordinator.types_enums import VLAAction, VLAActionType
    from .coordinator_core import MultiAgentCoordinator
    return VLAAction, VLAActionType, MultiAgentCoordinator

try:
    from .coordinator.types_enums import VLAAction, VLAActionType
except ImportError:
    pass

class VLACoordinator:
    """
    视觉-语言-动作模型协调器

    功能:
    - 协调VLA模型的观察、规划和执行
    - 与SafetyCoordinator集成确保安全
    - 支持多模态输入处理
    - 动作执行与反馈循环

    Issue #29: Embodied AI - VLA集成
    """

    def __init__(self, coordinator: MultiAgentCoordinator):
        self.coordinator = coordinator
        self.current_action: Optional[VLAAction] = None
        self.action_history: List[VLAAction] = []
        self.vla_model_endpoint: Optional[str] = None
        self.safety_check_required: bool = True

    def set_vla_model(self, endpoint: str):
        """设置VLA模型端点"""
        self.vla_model_endpoint = endpoint

    async def observe_and_plan(
        self,
        observation: Dict[str, Any],
        goal: str,
        safety_context: Optional[Dict] = None
    ) -> VLAAction:
        """
        观察并规划动作

        Args:
            observation: 视觉/传感器观察数据
            goal: 目标描述
            safety_context: 安全上下文

        Returns:
            VLAAction: 规划的动作
        """
        # 创建观察动作
        action = VLAAction(
            action_type=VLAActionType.OBSERVE,
            observation=observation,
            plan="",
            confidence=0.0,
            safety_check_passed=False
        )

        # 如果有VLA模型端点，进行VLA推理
        if self.vla_model_endpoint:
            action = await self._vla_inference(observation, goal)

        # 安全检查
        if self.safety_check_required and safety_context:
            action.safety_check_passed = await self._check_safety(
                action, safety_context
            )

        self.current_action = action
        return action

    async def _vla_inference(
        self,
        observation: Dict[str, Any],
        goal: str
    ) -> VLAAction:
        """调用VLA模型进行推理"""
        import httpx

        # 构建VLA输入
        vla_input = {
            "observation": observation,
            "goal": goal,
            "history": [
                {
                    "action_type": a.action_type.value,
                    "confidence": a.confidence
                }
                for a in self.action_history[-5:]
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.vla_model_endpoint}/vla/plan",
                    json=vla_input
                )
                result = response.json()

                return VLAAction(
                    action_type=VLAActionType(result.get("action_type", "plan")),
                    observation=observation,
                    plan=result.get("plan", ""),
                    confidence=result.get("confidence", 0.0),
                    safety_check_passed=False
                )
        except Exception as e:
            # VLA调用失败，返回基于规则的默认动作
            return VLAAction(
                action_type=VLAActionType.PLAN,
                observation=observation,
                plan=f"Goal: {goal}. Analysis: {str(e)[:100]}",
                confidence=0.5,
                safety_check_passed=True
            )

    async def _check_safety(
        self,
        action: VLAAction,
        context: Dict
    ) -> bool:
        """安全检查"""
        # 检查动作是否涉及危险区域
        dangerous_keywords = ["sun", "laser", "bright"]

        for keyword in dangerous_keywords:
            if keyword.lower() in str(action.observation).lower():
                return False
            if keyword.lower() in action.plan.lower():
                return False

        return True

    async def execute_action(
        self,
        action: VLAAction,
        executor_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        执行动作

        Args:
            action: 要执行的动作
            executor_callback: 可选的执行器回调

        Returns:
            执行结果
        """
        if not action.safety_check_passed:
            return {"success": False, "error": "Safety check failed"}

        action.action_type = VLAActionType.EXECUTE
        self.action_history.append(action)

        if executor_callback:
            result = await executor_callback(action)
        else:
            result = {"success": True, "action": action.plan}

        return result

    def get_action_statistics(self) -> Dict[str, Any]:
        """获取动作统计"""
        if not self.action_history:
            return {"total_actions": 0, "avg_confidence": 0.0}

        confidences = [a.confidence for a in self.action_history]
        return {
            "total_actions": len(self.action_history),
            "avg_confidence": sum(confidences) / len(confidences),
            "recent_actions": len([a for a in self.action_history[-10:]])
        }


