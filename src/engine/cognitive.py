"""
认知引擎 - 负责意图识别、任务建模和高级推理
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.logger import get_logger


class IntentType(Enum):
    OBSERVE = "OBSERVE"
    ANALYZE = "ANALYZE"
    RESEARCH = "RESEARCH"
    EXPLORE = "EXPLORE"
    LEARN = "LEARN"
    UNKNOWN = "UNKNOWN"


@dataclass
class Intent:
    type: IntentType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_text: Optional[str] = None


@dataclass
class TaskModel:
    title: str
    description: str
    type: str
    priority: int = 0
    estimated_duration: Optional[float] = None
    required_resources: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class CognitiveEngine:
    """认知引擎"""
    
    def __init__(self, llm_service=None):
        self.logger = get_logger("cognitive-engine")
        self.llm_service = llm_service
        
        self.intent_patterns = {
            IntentType.OBSERVE: [
                "观测", "拍摄", "拍照", "看", "寻找", "定位", "指向",
                "observe", "image", "photograph", "capture", "point"
            ],
            IntentType.ANALYZE: [
                "分析", "处理", "识别", "检测", "计算", "测量",
                "analyze", "process", "identify", "detect", "calculate"
            ],
            IntentType.RESEARCH: [
                "研究", "探索", "发现", "假说", "验证", "理论",
                "research", "hypothesis", "discover", "explore", "verify"
            ],
            IntentType.EXPLORE: [
                "探索", "漫游", "浏览", "搜索", "扫描",
                "explore", "roam", "browse", "scan", "search"
            ],
            IntentType.LEARN: [
                "学习", "训练", "改进", "优化", "进化",
                "learn", "train", "improve", "optimize", "evolve"
            ]
        }
    
    def recognize_intent(self, text: str) -> Intent:
        text_lower = text.lower()
        matched_type = IntentType.UNKNOWN
        max_confidence = 0.0
        matched_patterns = []
        
        for intent_type, patterns in self.intent_patterns.items():
            count = sum(1 for pattern in patterns if pattern.lower() in text_lower)
            if count > 0:
                confidence = min(count / len(patterns), 1.0)
                if confidence > max_confidence:
                    max_confidence = confidence
                    matched_type = intent_type
                    matched_patterns = [p for p in patterns if p.lower() in text_lower]
        
        if matched_type == IntentType.UNKNOWN:
            max_confidence = 0.3
        
        return Intent(
            type=matched_type,
            confidence=max_confidence,
            parameters={"matched_patterns": matched_patterns},
            raw_text=text
        )
    
    async def analyze_and_model(self, text: str) -> TaskModel:
        intent = self.recognize_intent(text)
        
        type_mapping = {
            IntentType.OBSERVE: "observation",
            IntentType.ANALYZE: "analysis",
            IntentType.RESEARCH: "research",
            IntentType.EXPLORE: "exploration",
            IntentType.LEARN: "learning",
            IntentType.UNKNOWN: "unknown"
        }
        
        title = self._generate_task_title(intent)
        description = f"基于意图 {intent.type.value} 的任务"
        
        task_model = TaskModel(
            title=title,
            description=description,
            type=type_mapping[intent.type],
            priority=self._calculate_priority(intent)
        )
        
        self.logger.info(f"Task modeled: {task_model.title} (type: {task_model.type}, priority: {task_model.priority})")
        
        return task_model
    
    def _generate_task_title(self, intent: Intent) -> str:
        if intent.type == IntentType.OBSERVE:
            return "观测任务"
        elif intent.type == IntentType.ANALYZE:
            return "数据分析任务"
        elif intent.type == IntentType.RESEARCH:
            return "科研探索任务"
        elif intent.type == IntentType.EXPLORE:
            return "星空探索任务"
        elif intent.type == IntentType.LEARN:
            return "系统学习任务"
        return "未知任务"
    
    def _calculate_priority(self, intent: Intent) -> int:
        priority = 0
        if intent.confidence > 0.8:
            priority += 2
        elif intent.confidence > 0.5:
            priority += 1
        return priority