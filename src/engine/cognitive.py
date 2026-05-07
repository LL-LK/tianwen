"""
认知引擎

负责意图识别、任务建模和参数提取。
"""

from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import re


class IntentType(Enum):
    """意图类型枚举"""
    OBSERVE = "OBSERVE"
    ANALYZE = "ANALYZE"
    RESEARCH = "RESEARCH"
    EXPLORE = "EXPLORE"
    LEARN = "LEARN"
    COORDINATE = "COORDINATE"
    UNKNOWN = "UNKNOWN"


class Confidence(Enum):
    """置信度级别"""
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


@dataclass
class Intent:
    """意图模型"""
    type: IntentType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    matched_keywords: List[str] = field(default_factory=list)
    reasoning: str = ""
    
    def is_confident(self, threshold: float = 0.5) -> bool:
        """判断是否足够置信"""
        return self.confidence >= threshold


@dataclass
class TaskModel:
    """任务模型"""
    title: str
    description: str
    type: str
    priority: int = 1
    estimated_duration: Optional[float] = None
    required_resources: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternMatcher:
    """模式匹配器"""
    
    def __init__(self):
        self.intent_patterns = {
            IntentType.OBSERVE: {
                "keywords": [
                    "观测", "拍摄", "拍照", "看", "寻找", "定位", "指向",
                    "observe", "image", "photograph", "capture", "point", "观测目标"
                ],
                "weight": 1.0
            },
            IntentType.ANALYZE: {
                "keywords": [
                    "分析", "处理", "识别", "检测", "计算", "测量", "评估",
                    "analyze", "process", "identify", "detect", "calculate", "分析数据"
                ],
                "weight": 1.0
            },
            IntentType.RESEARCH: {
                "keywords": [
                    "研究", "探索", "发现", "假说", "验证", "理论", "科学",
                    "research", "hypothesis", "discover", "explore", "verify"
                ],
                "weight": 1.0
            },
            IntentType.EXPLORE: {
                "keywords": [
                    "探索", "漫游", "浏览", "搜索", "扫描", "巡天",
                    "explore", "roam", "browse", "scan", "search", "survey"
                ],
                "weight": 1.0
            },
            IntentType.LEARN: {
                "keywords": [
                    "学习", "训练", "改进", "优化", "进化", "提升",
                    "learn", "train", "improve", "optimize", "evolve"
                ],
                "weight": 1.0
            },
            IntentType.COORDINATE: {
                "keywords": [
                    "协调", "协作", "配合", "协同", "调度", "管理",
                    "coordinate", "collaborate", "coordinate", "schedule"
                ],
                "weight": 1.0
            }
        }
        
        self.entity_patterns = {
            "target_name": [
                r"(?:M|NGC|IC|星云|星系|星团)\s*[\d]+",
                r"[A-Z][a-z]+\s*[A-Z]?\d*",
            ],
            "coordinates": [
                r"RA[:\s]*[\d.]+\s*[h°]",
                r"DEC[:\s]*[+-]?[\d.]+\s*[°']",
                r"[\d.]+\s*h\s*[\d.]+\s*m",
            ],
            "exposure": [
                r"(\d+(?:\.\d+)?)\s*(?:秒|s|second)",
                r"曝光\s*(\d+)",
            ],
            "count": [
                r"(\d+)\s*(?:张|帧|次|frames?)",
                r"数量\s*(\d+)",
            ]
        }
    
    def match_intent(self, text: str) -> Intent:
        """匹配意图"""
        text_lower = text.lower()
        best_match = IntentType.UNKNOWN
        max_score = 0.0
        matched_kw = []
        
        for intent_type, pattern_info in self.intent_patterns.items():
            score = 0.0
            type_matched = []
            
            for keyword in pattern_info["keywords"]:
                if keyword.lower() in text_lower:
                    score += 1.0
                    type_matched.append(keyword)
            
            if score > 0:
                normalized_score = min(score / len(pattern_info["keywords"]), 1.0) * pattern_info["weight"]
                
                if normalized_score > max_score:
                    max_score = normalized_score
                    best_match = intent_type
                    matched_kw = type_matched
        
        if best_match == IntentType.UNKNOWN and max_score == 0:
            max_score = 0.3
        
        return Intent(
            type=best_match,
            confidence=max_score,
            raw_text=text,
            matched_keywords=matched_kw,
            reasoning=self._generate_reasoning(best_match, matched_kw)
        )
    
    def _generate_reasoning(self, intent: IntentType, keywords: List[str]) -> str:
        """生成推理说明"""
        if intent == IntentType.UNKNOWN:
            return "未识别到明确意图，使用默认设置"
        
        kw_str = ", ".join(keywords) if keywords else "无"
        return f"基于关键词 [{kw_str}] 识别为 {intent.value} 意图"
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """提取实体"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities[entity_type] = match.group(1) if match.groups() else match.group()
                    break
        
        return entities


class CognitiveEngine:
    """认知引擎"""
    
    def __init__(self, llm_service=None):
        self.logger = logging.getLogger("cognitive-engine")
        self.llm_service = llm_service
        self.pattern_matcher = PatternMatcher()
        
        self.type_mapping = {
            IntentType.OBSERVE: "observation",
            IntentType.ANALYZE: "analysis",
            IntentType.RESEARCH: "research",
            IntentType.EXPLORE: "exploration",
            IntentType.LEARN: "learning",
            IntentType.COORDINATE: "coordination",
            IntentType.UNKNOWN: "unknown"
        }
        
        self.resource_mapping = {
            IntentType.OBSERVE: ["telescope", "camera", "mount"],
            IntentType.ANALYZE: ["computing", "storage"],
            IntentType.RESEARCH: ["database", "computing"],
            IntentType.EXPLORE: ["telescope", "computing"],
            IntentType.LEARN: ["computing", "storage"],
            IntentType.COORDINATE: ["scheduler"],
            IntentType.UNKNOWN: []
        }
    
    def recognize_intent(self, text: str) -> Intent:
        """识别用户意图"""
        return self.pattern_matcher.match_intent(text)
    
    def extract_parameters(self, text: str, intent: Intent) -> Dict[str, Any]:
        """提取参数"""
        params = self.pattern_matcher.extract_entities(text)
        params["intent_confidence"] = intent.confidence
        params["matched_keywords"] = intent.matched_keywords
        return params
    
    def model_task(self, intent: Intent, params: Dict[str, Any]) -> TaskModel:
        """构建任务模型"""
        task_type = self.type_mapping[intent.type]
        resources = self.resource_mapping[intent.type]
        
        title = self._generate_title(intent, params)
        description = self._generate_description(intent, params)
        priority = self._calculate_priority(intent, params)
        
        return TaskModel(
            title=title,
            description=description,
            type=task_type,
            priority=priority,
            required_resources=resources,
            metadata={
                "intent": intent.type.value,
                "confidence": intent.confidence,
                "raw_params": params
            }
        )
    
    def _generate_title(self, intent: Intent, params: Dict[str, Any]) -> str:
        """生成任务标题"""
        if intent.type == IntentType.OBSERVE:
            target = params.get("target_name", "未知目标")
            return f"观测任务: {target}"
        elif intent.type == IntentType.ANALYZE:
            return "数据分析任务"
        elif intent.type == IntentType.RESEARCH:
            return "科研探索任务"
        elif intent.type == IntentType.EXPLORE:
            return "星空探索任务"
        elif intent.type == IntentType.LEARN:
            return "系统学习任务"
        elif intent.type == IntentType.COORDINATE:
            return "协调调度任务"
        return "通用任务"
    
    def _generate_description(self, intent: Intent, params: Dict[str, Any]) -> str:
        """生成任务描述"""
        parts = [f"意图类型: {intent.type.value}"]
        
        if params.get("target_name"):
            parts.append(f"目标: {params['target_name']}")
        if params.get("coordinates"):
            parts.append(f"坐标: {params['coordinates']}")
        if params.get("exposure"):
            parts.append(f"曝光: {params['exposure']}秒")
        if params.get("count"):
            parts.append(f"数量: {params['count']}张")
        
        return "; ".join(parts)
    
    def _calculate_priority(self, intent: Intent, params: Dict[str, Any]) -> int:
        """计算任务优先级"""
        priority = 1
        
        if intent.confidence >= 0.7:
            priority += 1
        
        if params.get("urgent") or "紧急" in params.get("matched_keywords", []):
            priority += 2
        
        if intent.type == IntentType.OBSERVE:
            if params.get("count", 0) > 10:
                priority += 1
        
        return min(priority, 5)
    
    async def analyze_and_model(self, text: str) -> TaskModel:
        """完整的分析和建模流程"""
        intent = self.recognize_intent(text)
        params = self.extract_parameters(text, intent)
        task_model = self.model_task(intent, params)
        
        self.logger.info(
            f"Task modeled: {task_model.title} | "
            f"Type: {task_model.type} | "
            f"Priority: {task_model.priority} | "
            f"Confidence: {intent.confidence:.2f}"
        )
        
        return task_model


import logging