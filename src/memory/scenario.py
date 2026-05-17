"""
天问-AGI 情景记忆系统 v1.0
ScenarioMemory - "情景-情感-意图"三位一体记忆

区别于现有的:
- vector_memory.py: 向量记忆，语义搜索
- memory_persistence.py: 持久化存储

情景记忆系统特点:
- 情景(Scenario): 当前任务的上下文状态
- 情感(Emotion): 用户/系统的情感状态
- 意图(Intent): 隐藏的真实意图

Author: Tianwen-AGI Architecture Team
Date: 2026/05/03
"""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import json
import uuid


class EmotionType(Enum):
    """情感类型枚举"""
    NEUTRAL = "neutral"
    CURIOUS = "curious"          # 好奇 - 探索新领域
    EXCITED = "excited"          # 兴奋 - 发现新目标
    FRUSTRATED = "frustrated"    # 挫折 - 遇到困难
    SATISFIED = "satisfied"      # 满足 - 完成任务
    CONFUSED = "confused"        # 困惑 - 需要澄清


class IntentType(Enum):
    """意图类型枚举"""
    EXPLORE = "explore"          # 探索
    VERIFY = "verify"            # 验证
    UNDERSTAND = "understand"    # 理解
    CREATE = "create"            # 创建
    OPTIMIZE = "optimize"        # 优化


@dataclass
class ScenarioContext:
    """情景上下文"""
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

    # 情景要素
    topic: str = ""                          # 当前话题
    task_state: str = "initial"             # 任务状态: initial/running/completed/failed
    context_data: Dict[str, Any] = field(default_factory=dict)

    # 情感要素
    emotion: EmotionType = EmotionType.NEUTRAL
    emotion_intensity: float = 0.5           # 0-1

    # 意图要素
    intent: IntentType = IntentType.EXPLORE
    intent_confidence: float = 0.5           # 0-1
    hidden_intent: Optional[str] = None      # 隐藏的真实意图

    # 关联记忆
    related_memories: List[str] = field(default_factory=list)  # 关联的记忆ID列表

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp.isoformat(),
            "topic": self.topic,
            "task_state": self.task_state,
            "context_data": self.context_data,
            "emotion": self.emotion.value,
            "emotion_intensity": self.emotion_intensity,
            "intent": self.intent.value,
            "intent_confidence": self.intent_confidence,
            "hidden_intent": self.hidden_intent,
            "related_memories": self.related_memories
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ScenarioContext":
        """从字典创建"""
        ctx = cls()
        ctx.scenario_id = data.get("scenario_id", str(uuid.uuid4()))
        ctx.topic = data.get("topic", "")
        ctx.task_state = data.get("task_state", "initial")
        ctx.context_data = data.get("context_data", {})
        ctx.emotion = EmotionType(data.get("emotion", "neutral"))
        ctx.emotion_intensity = data.get("emotion_intensity", 0.5)
        ctx.intent = IntentType(data.get("intent", "explore"))
        ctx.intent_confidence = data.get("intent_confidence", 0.5)
        ctx.hidden_intent = data.get("hidden_intent")
        ctx.related_memories = data.get("related_memories", [])
        if "timestamp" in data:
            ctx.timestamp = datetime.fromisoformat(data["timestamp"])
        return ctx


@dataclass
class EmotionalResponse:
    """情感反应"""
    emotion: EmotionType
    intensity: float
    trigger_event: str
    timestamp: datetime = field(default_factory=datetime.now)


class ScenarioMemory:
    """
    情景记忆系统

    存储和管理"情景-情感-意图"三位一体的记忆

    使用方法:
        memory = ScenarioMemory()

        # 创建情景
        ctx = memory.create_context(
            topic="开普勒-186f研究",
            emotion=EmotionType.CURIOUS,
            intent=IntentType.EXPLORE
        )

        # 记录情感变化
        memory.record_emotion(ctx.scenario_id, EmotionType.EXCITED, 0.8, "发现新目标")

        # 获取记忆
        memories = memory.get_recent_memories(limit=5)
    """

    def __init__(self, storage_path: str = "./memory/scenario_memory.json"):
        self.storage_path = storage_path
        self.scenarios: Dict[str, ScenarioContext] = {}
        self.emotional_history: List[EmotionalResponse] = []
        self._load_from_disk()

    def _load_from_disk(self):
        """从磁盘加载记忆"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get("scenarios", []):
                    ctx = ScenarioContext.from_dict(item)
                    self.scenarios[ctx.scenario_id] = ctx
                for item in data.get("emotions", []):
                    self.emotional_history.append(EmotionalResponse(
                        emotion=EmotionType(item.get("emotion", "neutral")),
                        intensity=item.get("intensity", 0.5),
                        trigger_event=item.get("trigger_event", ""),
                        timestamp=datetime.fromisoformat(item.get("timestamp", datetime.now().isoformat()))
                    ))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_to_disk(self):
        """保存记忆到磁盘"""
        data = {
            "scenarios": [ctx.to_dict() for ctx in self.scenarios.values()],
            "emotions": [
                {
                    "emotion": r.emotion.value,
                    "intensity": r.intensity,
                    "trigger_event": r.trigger_event,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.emotional_history[-100:]  # 只保留最近100条
            ]
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_context(
        self,
        topic: str,
        emotion: EmotionType = EmotionType.NEUTRAL,
        intent: IntentType = IntentType.EXPLORE,
        context_data: Optional[Dict] = None
    ) -> ScenarioContext:
        """创建情景上下文"""
        ctx = ScenarioContext(
            topic=topic,
            emotion=emotion,
            intent=intent
        )
        if context_data:
            ctx.context_data = context_data

        self.scenarios[ctx.scenario_id] = ctx
        self._save_to_disk()
        return ctx

    def update_emotion(
        self,
        scenario_id: str,
        emotion: EmotionType,
        intensity: float = 0.5
    ):
        """更新情景的情感状态"""
        ctx = self.scenarios.get(scenario_id)
        if ctx:
            ctx.emotion = emotion
            ctx.emotion_intensity = intensity

            # 记录情感历史
            self.emotional_history.append(EmotionalResponse(
                emotion=emotion,
                intensity=intensity,
                trigger_event=f"Scenario update: {scenario_id}"
            ))

            self._save_to_disk()

    def update_intent(
        self,
        scenario_id: str,
        intent: IntentType,
        confidence: float = 0.5,
        hidden_intent: Optional[str] = None
    ):
        """更新情景的意图状态"""
        ctx = self.scenarios.get(scenario_id)
        if ctx:
            ctx.intent = intent
            ctx.intent_confidence = confidence
            if hidden_intent:
                ctx.hidden_intent = hidden_intent
            self._save_to_disk()

    def update_task_state(self, scenario_id: str, state: str):
        """更新任务状态"""
        ctx = self.scenarios.get(scenario_id)
        if ctx:
            ctx.task_state = state
            self._save_to_disk()

    def link_memories(self, scenario_id: str, memory_ids: List[str]):
        """关联记忆"""
        ctx = self.scenarios.get(scenario_id)
        if ctx:
            ctx.related_memories.extend(memory_ids)
            ctx.related_memories = list(set(ctx.related_memories))  # 去重
            self._save_to_disk()

    def record_emotion(
        self,
        scenario_id: str,
        emotion: EmotionType,
        intensity: float,
        trigger_event: str
    ):
        """记录情感变化"""
        self.emotional_history.append(EmotionalResponse(
            emotion=emotion,
            intensity=intensity,
            trigger_event=trigger_event
        ))
        self._save_to_disk()

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioContext]:
        """获取指定情景"""
        return self.scenarios.get(scenario_id)

    def get_recent_memories(self, limit: int = 10) -> List[ScenarioContext]:
        """获取最近的记忆"""
        sorted_scenarios = sorted(
            self.scenarios.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        return sorted_scenarios[:limit]

    def get_by_emotion(self, emotion: EmotionType) -> List[ScenarioContext]:
        """获取特定情感的记忆"""
        return [ctx for ctx in self.scenarios.values() if ctx.emotion == emotion]

    def get_by_intent(self, intent: IntentType) -> List[ScenarioContext]:
        """获取特定意图的记忆"""
        return [ctx for ctx in self.scenarios.values() if ctx.intent == intent]

    def get_emotional_stats(self) -> Dict:
        """获取情感统计"""
        emotion_counts = {}
        for ctx in self.scenarios.values():
            emotion_counts[ctx.emotion.value] = emotion_counts.get(ctx.emotion.value, 0) + 1
        return {
            "total_scenarios": len(self.scenarios),
            "emotion_distribution": emotion_counts,
            "recent_emotions": len(self.emotional_history)
        }

    def infer_hidden_intent(self, scenario_id: str) -> Optional[str]:
        """推断隐藏意图"""
        ctx = self.scenarios.get(scenario_id)
        if not ctx:
            return None

        # 基于情景和情感推断隐藏意图
        if ctx.emotion == EmotionType.CURIOUS and ctx.task_state == "initial":
            return "需要更多探索引导"
        elif ctx.emotion == EmotionType.FRUSTRATED:
            return "需要简化任务或提供更多帮助"
        elif ctx.emotion == EmotionType.EXCITED and ctx.intent == IntentType.EXPLORE:
            return "鼓励深入研究"
        return None


# ============ 便捷函数 =========---

def quick_create_scenario(
    topic: str,
    emotion: str = "curious",
    intent: str = "explore"
) -> ScenarioContext:
    """快速创建情景"""
    memory = ScenarioMemory()
    return memory.create_context(
        topic=topic,
        emotion=EmotionType(emotion),
        intent=IntentType(intent)
    )


if __name__ == "__main__":
    logger.debug("=" * 60)
    logger.info("Tianwen-AGI Scenario Memory System")
    logger.debug("=" * 60)

    memory = ScenarioMemory()

    # 创建情景
    ctx = memory.create_context(
        topic="Kepler-186f exoplanet research",
        emotion=EmotionType.CURIOUS,
        intent=IntentType.EXPLORE,
        context_data={"research_stage": "initial"}
    )
    logger.info(f"\n[1] Created scenario: {ctx.scenario_id}")
    logger.info(f"    Topic: {ctx.topic}")
    logger.info(f"    Emotion: {ctx.emotion.value} ({ctx.emotion_intensity})")
    logger.info(f"    Intent: {ctx.intent.value} ({ctx.intent_confidence})")

    # 模拟情感变化
    memory.record_emotion(ctx.scenario_id, EmotionType.EXCITED, 0.8, "Found interesting data")
    logger.info("\n[2] Recorded emotional change: EXCITED (0.8)")

    # 更新任务状态
    memory.update_task_state(ctx.scenario_id, "running")
    logger.info("\n[3] Updated task state: running")

    # 获取统计
    stats = memory.get_emotional_stats()
    logger.info(f"\n[4] Emotional stats: {stats}")

    logger.debug("\n" + "=" * 60)
    logger.info("Scenario Memory System Demo Complete")
    logger.debug("=" * 60)