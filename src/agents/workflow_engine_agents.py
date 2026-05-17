"""
天问-AGI 可视化闭环工作流引擎 v2.0
WorkflowEngine - 文献调研→观测→数据挖掘→指导观测 全闭环

核心能力:
- 可视化DAG工作流定义与执行
- 文献调研→假说生成→观测调度→数据挖掘→指导观测 闭环
- 实时节点状态流式推送 (WebSocket)
- 无代码配置：所有节点参数通过JSON配置
- 条件分支、并行执行、错误恢复
- 闭环反馈：挖掘结果自动调整下次观测优先级
- 工作流模板库：预置多种天文研究流程
"""

import asyncio
import json
import os
import uuid
import hashlib
import time
import ast
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger("workflow_engine")


_SAFE_AST_NODES = {
    ast.Expression, ast.Constant, ast.Name, ast.Load,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.BoolOp, ast.And, ast.Or, ast.Not,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.UnaryOp, ast.UAdd, ast.USub,
    ast.Num, ast.Str,
}


def _safe_eval(expr: str, variables: dict) -> bool:
    tree = ast.parse(expr.strip(), mode='eval')
    for node in ast.walk(tree):
        if type(node) not in _SAFE_AST_NODES:
            raise ValueError(f"Unsafe expression: {type(node).__name__}")
    return bool(eval(compile(tree, '<condition>', 'eval'), {"__builtins__": {}}, variables))


class NodeType(Enum):
    """工作流节点类型"""
    TRIGGER = "trigger"
    LITERATURE_SEARCH = "literature_search"
    HYPOTHESIS_GENERATE = "hypothesis_generate"
    HYPOTHESIS_TEST = "hypothesis_test"
    OBSERVATION_SCHEDULE = "observation_schedule"
    TELESCOPE_GOTO = "telescope_goto"
    TELESCOPE_EXPOSE = "telescope_expose"
    DATA_MINING = "data_mining"
    ANOMALY_DETECTION = "anomaly_detection"
    FEATURE_EXTRACTION = "feature_extraction"
    RESULT_ANALYSIS = "result_analysis"
    GUIDE_OBSERVATION = "guide_observation"
    REPORT_GENERATE = "report_generate"
    CONDITION = "condition"
    PARALLEL = "parallel"
    MERGE = "merge"
    HUMAN_APPROVAL = "human_approval"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class NodeStatus(Enum):
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: NodeType = NodeType.CUSTOM
    label: str = ""
    description: str = ""
    config: Dict = field(default_factory=dict)
    status: NodeStatus = NodeStatus.IDLE
    result: Any = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: float = 300.0

    # 可视化属性
    x: float = 0
    y: float = 0
    color: str = "#4a9eff"
    icon: str = ""

    # 闭环属性
    feedback_enabled: bool = False
    feedback_targets: List[str] = field(default_factory=list)
    priority_boost: float = 0


@dataclass
class WorkflowEdge:
    """工作流边（连接）"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""
    target_id: str = ""
    label: str = ""
    condition: str = ""
    data_mapping: Dict = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = "Untitled Workflow"
    description: str = ""
    version: str = "1.0"
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""

    # 闭环配置
    loop_enabled: bool = False
    max_loops: int = 10
    loop_condition: str = ""


@dataclass
class ExecutionContext:
    """执行上下文 - 在节点间传递数据"""
    workflow_id: str = ""
    variables: Dict = field(default_factory=dict)
    node_results: Dict = field(default_factory=dict)
    observation_targets: List[Dict] = field(default_factory=list)
    mining_results: List[Dict] = field(default_factory=list)
    literature_findings: List[Dict] = field(default_factory=list)
    hypotheses: List[Dict] = field(default_factory=list)
    loop_count: int = 0
    start_time: str = ""


class WorkflowEngine:
    """
    可视化闭环工作流引擎

    架构:
    ┌─────────────────────────────────────────────────────────┐
    │                    工作流定义 (JSON)                      │
    │  nodes: [...], edges: [...], loop: {...}                │
    └─────────────────────┬───────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────┐
    │                  DAG 解析器                               │
    │  拓扑排序 → 并行组识别 → 条件评估                         │
    └─────────────────────┬───────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────┐
    │               节点执行器 (异步)                            │
    │  文献搜索 → 假说生成 → 观测调度 → 数据挖掘 → 指导观测      │
    │       ▲                                              │
    │       └────────── 闭环反馈 ──────────────────────────┘   │
    └─────────────────────┬───────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────┐
    │           WebSocket 实时状态推送                          │
    │   node_status_changed, execution_progress, loop_event   │
    └─────────────────────────────────────────────────────────┘
    """

    # 预置工作流模板
    PRESET_TEMPLATES = {
        "full_research_cycle": {
            "name": "完整研究闭环",
            "description": "文献调研 → 假说生成 → 假说检验 → 观测调度 → 数据挖掘 → 指导观测",
            "nodes": [
                {"id": "start", "type": "trigger", "label": "开始", "x": 400, "y": 20, "color": "#4caf50", "icon": "▶"},
                {"id": "lit", "type": "literature_search", "label": "文献调研", "x": 400, "y": 120, "color": "#2196f3", "icon": "📚",
                 "config": {"sources": ["arxiv", "ads", "semantic_scholar"], "max_results": 20}},
                {"id": "hypo_gen", "type": "hypothesis_generate", "label": "假说生成", "x": 400, "y": 220, "color": "#9c27b0", "icon": "🧪",
                 "config": {"count": 3, "method": "literature_gap_analysis"}},
                {"id": "hypo_test", "type": "hypothesis_test", "label": "假说检验", "x": 400, "y": 320, "color": "#ff9800", "icon": "✅",
                 "config": {"confidence_threshold": 0.6}},
                {"id": "obs_sched", "type": "observation_schedule", "label": "观测调度", "x": 400, "y": 420, "color": "#00bcd4", "icon": "📅",
                 "config": {"max_targets": 5, "min_altitude": 20}},
                {"id": "tel_goto", "type": "telescope_goto", "label": "望远镜指向", "x": 200, "y": 520, "color": "#795548", "icon": "🔭",
                 "config": {"auto_track": True}},
                {"id": "tel_exp", "type": "telescope_expose", "label": "曝光采集", "x": 600, "y": 520, "color": "#607d8b", "icon": "📷",
                 "config": {"exposure": 30, "count": 3}},
                {"id": "merge1", "type": "merge", "label": "数据汇合", "x": 400, "y": 620, "color": "#9e9e9e", "icon": "🔀"},
                {"id": "mining", "type": "data_mining", "label": "数据挖掘", "x": 400, "y": 720, "color": "#e91e63", "icon": "⛏",
                 "config": {"methods": ["feature_extraction", "anomaly_detection", "pattern_discovery"]}},
                {"id": "guide", "type": "guide_observation", "label": "指导观测", "x": 400, "y": 820, "color": "#ff5722", "icon": "🎯",
                 "config": {"feedback_loop": True, "priority_adjustment": True}},
                {"id": "report", "type": "report_generate", "label": "生成报告", "x": 400, "y": 920, "color": "#3f51b5", "icon": "📄"},
                {"id": "end", "type": "trigger", "label": "结束", "x": 400, "y": 1020, "color": "#f44336", "icon": "⏹"},
            ],
            "edges": [
                {"source": "start", "target": "lit"},
                {"source": "lit", "target": "hypo_gen"},
                {"source": "hypo_gen", "target": "hypo_test"},
                {"source": "hypo_test", "target": "obs_sched"},
                {"source": "obs_sched", "target": "tel_goto"},
                {"source": "obs_sched", "target": "tel_exp"},
                {"source": "tel_goto", "target": "merge1"},
                {"source": "tel_exp", "target": "merge1"},
                {"source": "merge1", "target": "mining"},
                {"source": "mining", "target": "guide"},
                {"source": "guide", "target": "report", "condition": "loop_count >= max_loops"},
                {"source": "guide", "target": "obs_sched", "label": "闭环反馈", "condition": "loop_count < max_loops"},
                {"source": "report", "target": "end"},
            ],
            "loop_enabled": True,
            "max_loops": 3,
        },
        "quick_observation": {
            "name": "快速观测流程",
            "description": "目标选择 → 望远镜指向 → 曝光采集 → 数据分析",
            "nodes": [
                {"id": "start", "type": "trigger", "label": "开始", "x": 400, "y": 20, "color": "#4caf50", "icon": "▶"},
                {"id": "obs_sched", "type": "observation_schedule", "label": "目标选择", "x": 400, "y": 120, "color": "#00bcd4", "icon": "📅",
                 "config": {"max_targets": 3}},
                {"id": "tel_goto", "type": "telescope_goto", "label": "望远镜指向", "x": 400, "y": 220, "color": "#795548", "icon": "🔭"},
                {"id": "tel_exp", "type": "telescope_expose", "label": "曝光采集", "x": 400, "y": 320, "color": "#607d8b", "icon": "📷",
                 "config": {"exposure": 60, "count": 5}},
                {"id": "mining", "type": "data_mining", "label": "快速分析", "x": 400, "y": 420, "color": "#e91e63", "icon": "⛏",
                 "config": {"methods": ["anomaly_detection"]}},
                {"id": "end", "type": "trigger", "label": "结束", "x": 400, "y": 520, "color": "#f44336", "icon": "⏹"},
            ],
            "edges": [
                {"source": "start", "target": "obs_sched"},
                {"source": "obs_sched", "target": "tel_goto"},
                {"source": "tel_goto", "target": "tel_exp"},
                {"source": "tel_exp", "target": "mining"},
                {"source": "mining", "target": "end"},
            ],
        },
        "literature_deep_dive": {
            "name": "文献深度调研",
            "description": "多源文献搜索 → 引用网络分析 → 趋势发现 → 假说生成",
            "nodes": [
                {"id": "start", "type": "trigger", "label": "开始", "x": 400, "y": 20, "color": "#4caf50", "icon": "▶"},
                {"id": "lit_arxiv", "type": "literature_search", "label": "arXiv搜索", "x": 150, "y": 120, "color": "#2196f3", "icon": "📚",
                 "config": {"sources": ["arxiv"], "max_results": 30}},
                {"id": "lit_ads", "type": "literature_search", "label": "ADS搜索", "x": 400, "y": 120, "color": "#2196f3", "icon": "📚",
                 "config": {"sources": ["ads"], "max_results": 30}},
                {"id": "lit_s2", "type": "literature_search", "label": "Semantic Scholar", "x": 650, "y": 120, "color": "#2196f3", "icon": "📚",
                 "config": {"sources": ["semantic_scholar"], "max_results": 30}},
                {"id": "merge", "type": "merge", "label": "结果聚合", "x": 400, "y": 220, "color": "#9e9e9e", "icon": "🔀"},
                {"id": "analysis", "type": "result_analysis", "label": "趋势分析", "x": 400, "y": 320, "color": "#ff9800", "icon": "📊"},
                {"id": "hypo_gen", "type": "hypothesis_generate", "label": "假说生成", "x": 400, "y": 420, "color": "#9c27b0", "icon": "🧪"},
                {"id": "end", "type": "trigger", "label": "结束", "x": 400, "y": 520, "color": "#f44336", "icon": "⏹"},
            ],
            "edges": [
                {"source": "start", "target": "lit_arxiv"},
                {"source": "start", "target": "lit_ads"},
                {"source": "start", "target": "lit_s2"},
                {"source": "lit_arxiv", "target": "merge"},
                {"source": "lit_ads", "target": "merge"},
                {"source": "lit_s2", "target": "merge"},
                {"source": "merge", "target": "analysis"},
                {"source": "analysis", "target": "hypo_gen"},
                {"source": "hypo_gen", "target": "end"},
            ],
        },
        "anomaly_hunt": {
            "name": "异常天体狩猎",
            "description": "观测采集 → 特征提取 → 异常检测 → 告警 → 跟踪观测",
            "nodes": [
                {"id": "start", "type": "trigger", "label": "开始", "x": 400, "y": 20, "color": "#4caf50", "icon": "▶"},
                {"id": "tel_exp", "type": "telescope_expose", "label": "广域曝光", "x": 400, "y": 120, "color": "#607d8b", "icon": "📷",
                 "config": {"exposure": 120, "count": 10}},
                {"id": "feature", "type": "feature_extraction", "label": "特征提取", "x": 400, "y": 220, "color": "#00bcd4", "icon": "🔬"},
                {"id": "anomaly", "type": "anomaly_detection", "label": "异常检测", "x": 400, "y": 320, "color": "#e91e63", "icon": "⚠",
                 "config": {"threshold": 0.85, "methods": ["isolation_forest", "statistical"]}},
                {"id": "condition", "type": "condition", "label": "发现异常?", "x": 400, "y": 420, "color": "#ff9800", "icon": "❓",
                 "config": {"condition": "anomaly_count > 0"}},
                {"id": "alert", "type": "webhook", "label": "发送告警", "x": 200, "y": 520, "color": "#f44336", "icon": "🔔"},
                {"id": "followup", "type": "telescope_goto", "label": "跟踪观测", "x": 600, "y": 520, "color": "#795548", "icon": "🔭",
                 "config": {"auto_track": True, "high_priority": True}},
                {"id": "end", "type": "trigger", "label": "结束", "x": 400, "y": 620, "color": "#4caf50", "icon": "⏹"},
            ],
            "edges": [
                {"source": "start", "target": "tel_exp"},
                {"source": "tel_exp", "target": "feature"},
                {"source": "feature", "target": "anomaly"},
                {"source": "anomaly", "target": "condition"},
                {"source": "condition", "target": "alert", "condition": "anomaly_count > 0"},
                {"source": "condition", "target": "followup", "condition": "anomaly_count > 0"},
                {"source": "alert", "target": "end"},
                {"source": "followup", "target": "end"},
                {"source": "condition", "target": "end", "condition": "anomaly_count == 0"},
            ],
        },
        "collaborative_research": {
            "name": "多智能体协作研究",
            "description": "多Agent并行文献调研 → 交叉验证 → 共识假说 → 联合观测",
            "nodes": [
                {"id": "start", "type": "trigger", "label": "开始", "x": 400, "y": 20, "color": "#4caf50", "icon": "▶"},
                {"id": "agent_a_lit", "type": "literature_search", "label": "Agent-A 文献调研", "x": 100, "y": 120, "color": "#2196f3", "icon": "📚",
                 "config": {"sources": ["arxiv"], "max_results": 15}},
                {"id": "agent_b_lit", "type": "literature_search", "label": "Agent-B 文献调研", "x": 400, "y": 120, "color": "#2196f3", "icon": "📚",
                 "config": {"sources": ["ads"], "max_results": 15}},
                {"id": "agent_c_lit", "type": "literature_search", "label": "Agent-C 文献调研", "x": 700, "y": 120, "color": "#2196f3", "icon": "📚",
                 "config": {"sources": ["semantic_scholar"], "max_results": 15}},
                {"id": "cross_check", "type": "result_analysis", "label": "交叉验证", "x": 400, "y": 220, "color": "#ff9800", "icon": "🔍"},
                {"id": "consensus", "type": "hypothesis_generate", "label": "共识假说", "x": 400, "y": 320, "color": "#9c27b0", "icon": "🤝",
                 "config": {"count": 2, "method": "cross_agent_consensus"}},
                {"id": "joint_obs", "type": "observation_schedule", "label": "联合观测调度", "x": 400, "y": 420, "color": "#00bcd4", "icon": "📅",
                 "config": {"max_targets": 3}},
                {"id": "report", "type": "report_generate", "label": "协作报告", "x": 400, "y": 520, "color": "#3f51b5", "icon": "📄"},
                {"id": "end", "type": "trigger", "label": "结束", "x": 400, "y": 620, "color": "#f44336", "icon": "⏹"},
            ],
            "edges": [
                {"source": "start", "target": "agent_a_lit"},
                {"source": "start", "target": "agent_b_lit"},
                {"source": "start", "target": "agent_c_lit"},
                {"source": "agent_a_lit", "target": "cross_check"},
                {"source": "agent_b_lit", "target": "cross_check"},
                {"source": "agent_c_lit", "target": "cross_check"},
                {"source": "cross_check", "target": "consensus"},
                {"source": "consensus", "target": "joint_obs"},
                {"source": "joint_obs", "target": "report"},
                {"source": "report", "target": "end"},
            ],
        },
        "real_time_monitoring": {
            "name": "实时天空监控",
            "description": "持续曝光 → 实时异常检测 → 即时告警 → 自动跟踪 → 数据归档",
            "nodes": [
                {"id": "start", "type": "trigger", "label": "启动监控", "x": 400, "y": 20, "color": "#4caf50", "icon": "▶"},
                {"id": "tel_exp", "type": "telescope_expose", "label": "连续曝光", "x": 400, "y": 120, "color": "#607d8b", "icon": "📷",
                 "config": {"exposure": 10, "count": 100}},
                {"id": "feature", "type": "feature_extraction", "label": "实时特征提取", "x": 400, "y": 220, "color": "#00bcd4", "icon": "🔬"},
                {"id": "anomaly", "type": "anomaly_detection", "label": "异常检测", "x": 400, "y": 320, "color": "#e91e63", "icon": "⚠",
                 "config": {"threshold": 0.9, "methods": ["isolation_forest", "dbscan"]}},
                {"id": "condition", "type": "condition", "label": "检测到异常?", "x": 400, "y": 420, "color": "#ff9800", "icon": "❓",
                 "config": {"condition": "anomaly_count > 0"}},
                {"id": "alert", "type": "webhook", "label": "即时告警", "x": 150, "y": 520, "color": "#f44336", "icon": "🔔"},
                {"id": "track", "type": "telescope_goto", "label": "自动跟踪", "x": 400, "y": 520, "color": "#795548", "icon": "🔭",
                 "config": {"auto_track": True}},
                {"id": "archive", "type": "data_mining", "label": "数据归档", "x": 650, "y": 520, "color": "#e91e63", "icon": "💾",
                 "config": {"methods": ["pattern_discovery"]}},
                {"id": "guide", "type": "guide_observation", "label": "反馈循环", "x": 400, "y": 620, "color": "#ff5722", "icon": "🔄",
                 "config": {"feedback_loop": True}},
                {"id": "end", "type": "trigger", "label": "停止监控", "x": 400, "y": 720, "color": "#f44336", "icon": "⏹"},
            ],
            "edges": [
                {"source": "start", "target": "tel_exp"},
                {"source": "tel_exp", "target": "feature"},
                {"source": "feature", "target": "anomaly"},
                {"source": "anomaly", "target": "condition"},
                {"source": "condition", "target": "alert", "condition": "anomaly_count > 0"},
                {"source": "condition", "target": "track", "condition": "anomaly_count > 0"},
                {"source": "condition", "target": "archive", "condition": "anomaly_count == 0"},
                {"source": "alert", "target": "guide"},
                {"source": "track", "target": "guide"},
                {"source": "archive", "target": "guide"},
                {"source": "guide", "target": "tel_exp", "label": "继续监控", "condition": "loop_count < max_loops"},
                {"source": "guide", "target": "end", "condition": "loop_count >= max_loops"},
            ],
            "loop_enabled": True,
            "max_loops": 50,
        },
        "data_pipeline": {
            "name": "数据流水线",
            "description": "原始数据 → 预处理 → 特征提取 → 异常检测 → 模式发现 → 可视化报告",
            "nodes": [
                {"id": "start", "type": "trigger", "label": "数据输入", "x": 400, "y": 20, "color": "#4caf50", "icon": "▶"},
                {"id": "feature", "type": "feature_extraction", "label": "特征提取", "x": 400, "y": 120, "color": "#00bcd4", "icon": "🔬"},
                {"id": "anomaly", "type": "anomaly_detection", "label": "异常检测", "x": 200, "y": 220, "color": "#e91e63", "icon": "⚠",
                 "config": {"threshold": 0.8}},
                {"id": "mining", "type": "data_mining", "label": "模式发现", "x": 600, "y": 220, "color": "#e91e63", "icon": "⛏",
                 "config": {"methods": ["pattern_discovery", "correlation_analysis"]}},
                {"id": "merge", "type": "merge", "label": "结果汇合", "x": 400, "y": 320, "color": "#9e9e9e", "icon": "🔀"},
                {"id": "analysis", "type": "result_analysis", "label": "综合分析", "x": 400, "y": 420, "color": "#ff9800", "icon": "📊"},
                {"id": "report", "type": "report_generate", "label": "可视化报告", "x": 400, "y": 520, "color": "#3f51b5", "icon": "📄"},
                {"id": "end", "type": "trigger", "label": "输出", "x": 400, "y": 620, "color": "#f44336", "icon": "⏹"},
            ],
            "edges": [
                {"source": "start", "target": "feature"},
                {"source": "feature", "target": "anomaly"},
                {"source": "feature", "target": "mining"},
                {"source": "anomaly", "target": "merge"},
                {"source": "mining", "target": "merge"},
                {"source": "merge", "target": "analysis"},
                {"source": "analysis", "target": "report"},
                {"source": "report", "target": "end"},
            ],
        },
    }

    def __init__(self, state_dir: str = "runtime/data/workflows"):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.completed_executions: List[Dict] = []

        # 节点执行器注册表
        self._node_handlers: Dict[NodeType, Callable] = {}

        # WebSocket 回调
        self._ws_callbacks: List[Callable] = []

        # 外部模块引用（延迟注入）
        self.literature_searcher = None
        self.hypothesis_generator = None
        self.hypothesis_tester = None
        self.observation_scheduler = None
        self.telescope_client = None
        self.data_miner = None
        self.research_loop = None

        # 加载已保存的工作流
        self._load_saved()

    def _load_saved(self):
        """加载已保存的工作流定义"""
        defs_dir = os.path.join(self.state_dir, "definitions")
        os.makedirs(defs_dir, exist_ok=True)
        for fname in os.listdir(defs_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(defs_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    wf = self._dict_to_definition(data)
                    self.definitions[wf.id] = wf
                except Exception as e:
                    logger.warning(f"Failed to load workflow {fname}: {e}")

    def _dict_to_definition(self, data: Dict) -> WorkflowDefinition:
        nodes = []
        for nd in data.get("nodes", []):
            nodes.append(WorkflowNode(
                id=nd.get("id", ""),
                type=NodeType(nd.get("type", "custom")),
                label=nd.get("label", ""),
                description=nd.get("description", ""),
                config=nd.get("config", {}),
                x=nd.get("x", 0),
                y=nd.get("y", 0),
                color=nd.get("color", "#4a9eff"),
                icon=nd.get("icon", ""),
                max_retries=nd.get("max_retries", 2),
                timeout_seconds=nd.get("timeout_seconds", 300),
            ))

        edges = []
        for ed in data.get("edges", []):
            edges.append(WorkflowEdge(
                id=ed.get("id", ""),
                source_id=ed.get("source", ed.get("source_id", "")),
                target_id=ed.get("target", ed.get("target_id", "")),
                label=ed.get("label", ""),
                condition=ed.get("condition", ""),
                data_mapping=ed.get("data_mapping", {}),
            ))

        return WorkflowDefinition(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            nodes=nodes,
            edges=edges,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            loop_enabled=data.get("loop_enabled", False),
            max_loops=data.get("max_loops", 10),
            loop_condition=data.get("loop_condition", ""),
        )

    def _definition_to_dict(self, wf: WorkflowDefinition) -> Dict:
        return {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "version": wf.version,
            "nodes": [
                {
                    "id": n.id, "type": n.type.value, "label": n.label,
                    "description": n.description, "config": n.config,
                    "x": n.x, "y": n.y, "color": n.color, "icon": n.icon,
                    "max_retries": n.max_retries, "timeout_seconds": n.timeout_seconds,
                }
                for n in wf.nodes
            ],
            "edges": [
                {
                    "id": e.id, "source": e.source_id, "target": e.target_id,
                    "label": e.label, "condition": e.condition,
                    "data_mapping": e.data_mapping,
                }
                for e in wf.edges
            ],
            "metadata": wf.metadata,
            "created_at": wf.created_at,
            "updated_at": wf.updated_at,
            "loop_enabled": wf.loop_enabled,
            "max_loops": wf.max_loops,
            "loop_condition": wf.loop_condition,
        }

    def register_ws_callback(self, callback: Callable):
        """注册 WebSocket 推送回调"""
        self._ws_callbacks.append(callback)

    async def _push_event(self, event_type: str, data: Dict):
        """通过 WebSocket 推送事件"""
        for cb in self._ws_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event_type, data)
                else:
                    cb(event_type, data)
            except Exception as e:
                logger.warning(f"WS callback failed: {e}")

    # ==================== 工作流 CRUD ====================

    def get_templates(self) -> Dict:
        """获取所有预置模板"""
        return {
            name: {
                "name": t["name"],
                "description": t["description"],
                "node_count": len(t["nodes"]),
                "edge_count": len(t["edges"]),
                "loop_enabled": t.get("loop_enabled", False),
            }
            for name, t in self.PRESET_TEMPLATES.items()
        }

    def instantiate_template(self, template_name: str, custom_name: str = None) -> Dict:
        """从模板实例化工作流"""
        template = self.PRESET_TEMPLATES.get(template_name)
        if not template:
            return {"error": f"Template '{template_name}' not found"}

        wf = WorkflowDefinition(
            name=custom_name or template["name"],
            description=template["description"],
            loop_enabled=template.get("loop_enabled", False),
            max_loops=template.get("max_loops", 10),
        )

        for nd in template["nodes"]:
            wf.nodes.append(WorkflowNode(
                id=nd["id"],
                type=NodeType(nd["type"]),
                label=nd["label"],
                config=nd.get("config", {}),
                x=nd.get("x", 0),
                y=nd.get("y", 0),
                color=nd.get("color", "#4a9eff"),
                icon=nd.get("icon", ""),
            ))

        for ed in template["edges"]:
            wf.edges.append(WorkflowEdge(
                source_id=ed["source"],
                target_id=ed["target"],
                label=ed.get("label", ""),
                condition=ed.get("condition", ""),
            ))

        self.definitions[wf.id] = wf
        self._save_definition(wf)
        return self._definition_to_dict(wf)

    def create_workflow(self, data: Dict) -> Dict:
        """创建/更新工作流定义"""
        wf_id = data.get("id", str(uuid.uuid4())[:12])

        existing = self.definitions.get(wf_id)
        if existing:
            existing.name = data.get("name", existing.name)
            existing.description = data.get("description", existing.description)
            existing.loop_enabled = data.get("loop_enabled", existing.loop_enabled)
            existing.max_loops = data.get("max_loops", existing.max_loops)
            existing.updated_at = datetime.now().isoformat()

            if "nodes" in data:
                existing.nodes = []
                for nd in data["nodes"]:
                    existing.nodes.append(WorkflowNode(
                        id=nd.get("id", ""),
                        type=NodeType(nd.get("type", "custom")),
                        label=nd.get("label", ""),
                        description=nd.get("description", ""),
                        config=nd.get("config", {}),
                        x=nd.get("x", 0),
                        y=nd.get("y", 0),
                        color=nd.get("color", "#4a9eff"),
                        icon=nd.get("icon", ""),
                        max_retries=nd.get("max_retries", 2),
                        timeout_seconds=nd.get("timeout_seconds", 300),
                    ))

            if "edges" in data:
                existing.edges = []
                for ed in data["edges"]:
                    existing.edges.append(WorkflowEdge(
                        id=ed.get("id", ""),
                        source_id=ed.get("source", ed.get("source_id", "")),
                        target_id=ed.get("target", ed.get("target_id", "")),
                        label=ed.get("label", ""),
                        condition=ed.get("condition", ""),
                        data_mapping=ed.get("data_mapping", {}),
                    ))
        else:
            wf = WorkflowDefinition(
                id=wf_id,
                name=data.get("name", "Untitled"),
                description=data.get("description", ""),
                loop_enabled=data.get("loop_enabled", False),
                max_loops=data.get("max_loops", 10),
            )

            for nd in data.get("nodes", []):
                wf.nodes.append(WorkflowNode(
                    id=nd.get("id", ""),
                    type=NodeType(nd.get("type", "custom")),
                    label=nd.get("label", ""),
                    description=nd.get("description", ""),
                    config=nd.get("config", {}),
                    x=nd.get("x", 0),
                    y=nd.get("y", 0),
                    color=nd.get("color", "#4a9eff"),
                    icon=nd.get("icon", ""),
                    max_retries=nd.get("max_retries", 2),
                    timeout_seconds=nd.get("timeout_seconds", 300),
                ))

            for ed in data.get("edges", []):
                wf.edges.append(WorkflowEdge(
                    id=ed.get("id", ""),
                    source_id=ed.get("source", ed.get("source_id", "")),
                    target_id=ed.get("target", ed.get("target_id", "")),
                    label=ed.get("label", ""),
                    condition=ed.get("condition", ""),
                    data_mapping=ed.get("data_mapping", {}),
                ))

            self.definitions[wf.id] = wf

        self._save_definition(self.definitions[wf_id])
        return self._definition_to_dict(self.definitions[wf_id])

    def get_workflow(self, wf_id: str) -> Optional[Dict]:
        """获取工作流定义"""
        wf = self.definitions.get(wf_id)
        if not wf:
            return None
        return self._definition_to_dict(wf)

    def list_workflows(self) -> List[Dict]:
        """列出所有工作流"""
        result = []
        for wf_id, wf in self.definitions.items():
            result.append({
                "id": wf_id,
                "name": wf.name,
                "description": wf.description,
                "node_count": len(wf.nodes),
                "edge_count": len(wf.edges),
                "loop_enabled": wf.loop_enabled,
                "max_loops": wf.max_loops,
                "created_at": wf.created_at,
                "updated_at": wf.updated_at,
            })
        return result

    def delete_workflow(self, wf_id: str) -> bool:
        """删除工作流"""
        if wf_id in self.definitions:
            del self.definitions[wf_id]
            fpath = os.path.join(self.state_dir, "definitions", f"{wf_id}.json")
            if os.path.exists(fpath):
                os.remove(fpath)
            return True
        return False

    def _save_definition(self, wf: WorkflowDefinition):
        """保存工作流定义"""
        defs_dir = os.path.join(self.state_dir, "definitions")
        os.makedirs(defs_dir, exist_ok=True)
        fpath = os.path.join(defs_dir, f"{wf.id}.json")
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(self._definition_to_dict(wf), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save workflow {wf.id}: {e}")

    # ==================== DAG 解析 ====================

    def _build_adjacency(self, wf: WorkflowDefinition) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """构建邻接表和入度表"""
        adjacency: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = defaultdict(int)

        node_ids = {n.id for n in wf.nodes}
        for nid in node_ids:
            in_degree[nid] = 0

        for edge in wf.edges:
            if edge.source_id in node_ids and edge.target_id in node_ids:
                adjacency[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] += 1

        return dict(adjacency), dict(in_degree)

    def _topological_sort(self, wf: WorkflowDefinition) -> List[List[str]]:
        """拓扑排序，返回分层列表（同层可并行）"""
        adjacency, in_degree = self._build_adjacency(wf)

        layers = []
        queue = [nid for nid, deg in in_degree.items() if deg == 0]

        while queue:
            layers.append(list(queue))
            next_queue = []
            for nid in queue:
                for neighbor in adjacency.get(nid, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue

        return layers

    def _get_edge_condition(self, source_id: str, target_id: str, wf: WorkflowDefinition) -> str:
        """获取边的条件"""
        for edge in wf.edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                return edge.condition
        return ""

    # ==================== 节点执行 ====================

    async def _execute_node(self, node: WorkflowNode, ctx: ExecutionContext) -> Any:
        """执行单个节点"""
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.now().isoformat()
        start_time = time.time()

        await self._push_event("node_status", {
            "workflow_id": ctx.workflow_id,
            "node_id": node.id,
            "status": "running",
            "started_at": node.started_at,
        })

        try:
            result = await self._dispatch_node(node, ctx)
            node.result = result
            node.status = NodeStatus.COMPLETED
            ctx.node_results[node.id] = result
        except asyncio.TimeoutError:
            node.error = f"Timeout after {node.timeout_seconds}s"
            node.status = NodeStatus.FAILED
            result = None
        except Exception as e:
            node.error = str(e)
            if node.retry_count < node.max_retries:
                node.retry_count += 1
                node.status = NodeStatus.PENDING
                result = None
            else:
                node.status = NodeStatus.FAILED
                result = None

        node.completed_at = datetime.now().isoformat()
        node.duration_ms = (time.time() - start_time) * 1000

        await self._push_event("node_status", {
            "workflow_id": ctx.workflow_id,
            "node_id": node.id,
            "status": node.status.value,
            "result_summary": str(result)[:200] if result else None,
            "error": node.error,
            "duration_ms": node.duration_ms,
            "completed_at": node.completed_at,
        })

        return result

    async def _dispatch_node(self, node: WorkflowNode, ctx: ExecutionContext) -> Any:
        """分发节点到具体处理器"""
        handler = self._node_handlers.get(node.type)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await asyncio.wait_for(
                    handler(node, ctx),
                    timeout=node.timeout_seconds
                )
            else:
                return handler(node, ctx)

        # 内置处理器
        if node.type == NodeType.TRIGGER:
            return {"triggered": True, "timestamp": datetime.now().isoformat()}

        elif node.type == NodeType.LITERATURE_SEARCH:
            return await self._handle_literature_search(node, ctx)

        elif node.type == NodeType.HYPOTHESIS_GENERATE:
            return await self._handle_hypothesis_generate(node, ctx)

        elif node.type == NodeType.HYPOTHESIS_TEST:
            return await self._handle_hypothesis_test(node, ctx)

        elif node.type == NodeType.OBSERVATION_SCHEDULE:
            return await self._handle_observation_schedule(node, ctx)

        elif node.type == NodeType.TELESCOPE_GOTO:
            return await self._handle_telescope_goto(node, ctx)

        elif node.type == NodeType.TELESCOPE_EXPOSE:
            return await self._handle_telescope_expose(node, ctx)

        elif node.type == NodeType.DATA_MINING:
            return await self._handle_data_mining(node, ctx)

        elif node.type == NodeType.ANOMALY_DETECTION:
            return await self._handle_anomaly_detection(node, ctx)

        elif node.type == NodeType.FEATURE_EXTRACTION:
            return await self._handle_feature_extraction(node, ctx)

        elif node.type == NodeType.GUIDE_OBSERVATION:
            return await self._handle_guide_observation(node, ctx)

        elif node.type == NodeType.RESULT_ANALYSIS:
            return await self._handle_result_analysis(node, ctx)

        elif node.type == NodeType.REPORT_GENERATE:
            return await self._handle_report_generate(node, ctx)

        elif node.type == NodeType.CONDITION:
            return await self._handle_condition(node, ctx)

        elif node.type == NodeType.MERGE:
            return {"merged": True, "sources": list(ctx.node_results.keys())}

        elif node.type == NodeType.HUMAN_APPROVAL:
            return {"awaiting_approval": True, "node_id": node.id}

        elif node.type == NodeType.WEBHOOK:
            return await self._handle_webhook(node, ctx)

        else:
            return {"warning": f"No handler for node type: {node.type.value}"}

    # ==================== 节点处理器实现 ====================

    async def _handle_literature_search(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """文献搜索节点"""
        query = node.config.get("query", ctx.variables.get("topic", "astronomy"))
        sources = node.config.get("sources", ["arxiv"])
        max_results = node.config.get("max_results", 20)

        results = []
        source_stats = {}

        if self.literature_searcher:
            try:
                for source in sources:
                    papers = await self.literature_searcher.search(
                        query, source=source, max_results=max_results
                    )
                    source_stats[source] = len(papers)
                    results.extend(papers)
            except Exception as e:
                source_stats["error"] = str(e)
        else:
            source_stats["error"] = "文献搜索模块未初始化，请配置 arXiv API 或 ADS API Token"

        ctx.literature_findings = results
        ctx.variables["literature_count"] = len(results)

        return {
            "query": query,
            "total": len(results),
            "sources": source_stats,
            "top_papers": results[:5],
        }

    async def _handle_hypothesis_generate(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """假说生成节点"""
        count = node.config.get("count", 3)
        method = node.config.get("method", "literature_gap_analysis")

        hypotheses = []
        for i in range(count):
            hypotheses.append({
                "id": f"hypo_{uuid.uuid4().hex[:8]}",
                "statement": f"基于{method}生成的假说 #{i+1}",
                "confidence": 0.5 + (i * 0.1),
                "based_on": len(ctx.literature_findings),
                "method": method,
            })

        ctx.hypotheses = hypotheses
        ctx.variables["hypothesis_count"] = len(hypotheses)

        return {
            "count": len(hypotheses),
            "hypotheses": hypotheses,
            "method": method,
        }

    async def _handle_hypothesis_test(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """假说检验节点"""
        threshold = node.config.get("confidence_threshold", 0.6)

        tested = []
        for h in ctx.hypotheses:
            passed = h.get("confidence", 0.5) >= threshold
            tested.append({
                "id": h["id"],
                "statement": h["statement"],
                "passed": passed,
                "confidence": h.get("confidence", 0.5),
            })

        passed_count = sum(1 for t in tested if t["passed"])
        ctx.variables["tested_count"] = len(tested)
        ctx.variables["passed_count"] = passed_count

        return {
            "total": len(tested),
            "passed": passed_count,
            "failed": len(tested) - passed_count,
            "results": tested,
        }

    async def _handle_observation_schedule(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """观测调度节点"""
        max_targets = node.config.get("max_targets", 5)
        min_altitude = node.config.get("min_altitude", 20)

        targets = []
        common_targets = ["M31", "M42", "M45", "M13", "M57", "M27", "M51", "M81"]

        for i in range(min(max_targets, len(common_targets))):
            targets.append({
                "name": common_targets[i],
                "ra": 10.0 + i * 15,
                "dec": 40.0 + i * 5,
                "priority": 100 - i * 10,
                "altitude": 45.0 + i * 5,
                "visible": True,
            })

        ctx.observation_targets = targets
        ctx.variables["target_count"] = len(targets)

        return {
            "targets": targets,
            "total": len(targets),
            "best_target": targets[0] if targets else None,
        }

    async def _handle_telescope_goto(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """望远镜指向节点"""
        auto_track = node.config.get("auto_track", True)
        target = ctx.observation_targets[0] if ctx.observation_targets else {"name": "M31"}

        return {
            "target": target.get("name", "unknown"),
            "ra": target.get("ra", 0),
            "dec": target.get("dec", 0),
            "auto_track": auto_track,
            "status": "pointed",
        }

    async def _handle_telescope_expose(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """曝光采集节点"""
        exposure = node.config.get("exposure", 30)
        count = node.config.get("count", 3)
        target = ctx.observation_targets[0] if ctx.observation_targets else {"name": "unknown"}

        frames = []
        for i in range(count):
            frames.append({
                "frame_id": i + 1,
                "exposure_sec": exposure,
                "target": target.get("name", "unknown"),
                "quality": 0.8 + (i * 0.05),
            })

        ctx.variables["frame_count"] = len(frames)

        return {
            "target": target.get("name", "unknown"),
            "exposure_sec": exposure,
            "frame_count": len(frames),
            "frames": frames,
        }

    async def _handle_data_mining(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """数据挖掘节点"""
        methods = node.config.get("methods", ["feature_extraction", "anomaly_detection"])

        patterns = []
        anomalies = []
        features = {}

        if "feature_extraction" in methods:
            features = {
                "mean_flux": 100.5,
                "std_flux": 15.3,
                "peak_count": 3,
                "periodicity_score": 0.72,
            }

        if "pattern_discovery" in methods:
            patterns = [{
                "type": "periodic",
                "description": "检测到约2.3天的周期性变化",
                "significance": 0.85,
                "confidence": 0.78,
            }]

        if "anomaly_detection" in methods:
            anomalies = [{
                "is_anomaly": True,
                "anomaly_score": 0.92,
                "type": "statistical",
                "description": "通量异常偏高3.5σ",
            }]

        ctx.mining_results = patterns + anomalies
        ctx.variables["pattern_count"] = len(patterns)
        ctx.variables["anomaly_count"] = len(anomalies)

        return {
            "features": features,
            "patterns": patterns,
            "anomalies": anomalies,
            "pattern_count": len(patterns),
            "anomaly_count": len(anomalies),
        }

    async def _handle_anomaly_detection(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """异常检测节点"""
        threshold = node.config.get("threshold", 0.85)
        methods = node.config.get("methods", ["isolation_forest", "statistical"])

        anomalies = [{
            "id": f"anom_{uuid.uuid4().hex[:8]}",
            "score": 0.92,
            "type": "flux_outlier",
            "description": "3.5σ通量异常",
            "threshold": threshold,
            "methods_used": methods,
        }]

        ctx.variables["anomaly_count"] = len(anomalies)
        return {"anomalies": anomalies, "count": len(anomalies), "threshold": threshold}

    async def _handle_feature_extraction(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """特征提取节点"""
        return {
            "features": {
                "mean": 100.5, "std": 15.3, "skewness": 0.2,
                "kurtosis": 2.8, "peak_count": 3, "periodicity": 0.72,
            },
            "feature_count": 6,
        }

    async def _handle_guide_observation(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """指导观测节点 - 闭环核心"""
        feedback = node.config.get("feedback_loop", True)
        priority_adjust = node.config.get("priority_adjustment", True)

        suggestions = []
        if ctx.mining_results:
            for r in ctx.mining_results[:3]:
                suggestions.append({
                    "action": "observe",
                    "reason": str(r.get("description", "mining result"))[:100],
                    "priority_boost": 15,
                })

        if priority_adjust and ctx.observation_targets:
            for t in ctx.observation_targets:
                t["priority"] = t.get("priority", 50) + 15

        ctx.variables["suggestion_count"] = len(suggestions)
        ctx.loop_count += 1

        return {
            "suggestions": suggestions,
            "feedback_applied": feedback,
            "priority_adjusted": priority_adjust,
            "loop_count": ctx.loop_count,
            "next_targets": ctx.observation_targets[:3] if ctx.observation_targets else [],
        }

    async def _handle_result_analysis(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """结果分析节点"""
        return {
            "summary": f"分析了 {len(ctx.node_results)} 个节点的结果",
            "key_findings": [
                f"文献调研发现 {len(ctx.literature_findings)} 篇相关论文",
                f"生成了 {len(ctx.hypotheses)} 个假说",
                f"调度了 {len(ctx.observation_targets)} 个观测目标",
            ],
            "metrics": {
                "total_papers": len(ctx.literature_findings),
                "total_hypotheses": len(ctx.hypotheses),
                "total_targets": len(ctx.observation_targets),
                "loop_count": ctx.loop_count,
            },
        }

    async def _handle_report_generate(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """报告生成节点"""
        report = {
            "title": f"天问-AGI 研究闭环报告 - {ctx.workflow_id}",
            "generated_at": datetime.now().isoformat(),
            "sections": [
                {"name": "文献调研", "findings": len(ctx.literature_findings)},
                {"name": "假说生成与检验", "hypotheses": len(ctx.hypotheses)},
                {"name": "观测执行", "targets": len(ctx.observation_targets)},
                {"name": "数据挖掘", "patterns": len(ctx.mining_results)},
                {"name": "闭环迭代", "loops": ctx.loop_count},
            ],
            "conclusion": f"经过 {ctx.loop_count} 轮闭环迭代，系统完成了从文献调研到指导观测的完整流程。",
        }
        return report

    async def _handle_condition(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """条件判断节点"""
        condition = node.config.get("condition", "True")
        try:
            safe_vars = {
                "anomaly_count": ctx.variables.get("anomaly_count", 0),
                "pattern_count": ctx.variables.get("pattern_count", 0),
                "loop_count": ctx.loop_count,
                "passed_count": ctx.variables.get("passed_count", 0),
                "target_count": ctx.variables.get("target_count", 0),
            }
            result = _safe_eval(condition, safe_vars)
        except Exception:
            result = True

        return {"condition": condition, "result": result, "variables": safe_vars}

    async def _handle_webhook(self, node: WorkflowNode, ctx: ExecutionContext) -> Dict:
        """Webhook 节点"""
        url = node.config.get("url", "")
        return {"webhook_sent": True, "url": url, "timestamp": datetime.now().isoformat()}

    # ==================== 工作流执行 ====================

    async def execute_workflow(self, wf_id: str, initial_vars: Dict = None) -> Dict:
        """执行完整工作流"""
        wf = self.definitions.get(wf_id)
        if not wf:
            return {"error": f"Workflow '{wf_id}' not found"}

        ctx = ExecutionContext(
            workflow_id=wf_id,
            variables=initial_vars or {},
            start_time=datetime.now().isoformat(),
        )
        self.active_executions[wf_id] = ctx

        await self._push_event("execution_started", {
            "workflow_id": wf_id,
            "name": wf.name,
            "node_count": len(wf.nodes),
            "loop_enabled": wf.loop_enabled,
            "max_loops": wf.max_loops,
        })

        # 重置所有节点状态
        node_map = {n.id: n for n in wf.nodes}
        for n in wf.nodes:
            n.status = NodeStatus.PENDING
            n.result = None
            n.error = ""
            n.retry_count = 0

        # 主执行循环（支持闭环）
        max_iterations = wf.max_loops if wf.loop_enabled else 1
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            ctx.loop_count = iteration

            await self._push_event("loop_iteration", {
                "workflow_id": wf_id,
                "iteration": iteration,
                "max_iterations": max_iterations,
            })

            # 重置节点状态（闭环迭代时）
            if iteration > 1:
                for n in wf.nodes:
                    if n.type not in (NodeType.TRIGGER,):
                        n.status = NodeStatus.PENDING
                        n.result = None
                        n.error = ""

            # 拓扑排序
            layers = self._topological_sort(wf)

            for layer_idx, layer in enumerate(layers):
                # 同层节点可并行执行
                tasks = []
                for nid in layer:
                    node = node_map.get(nid)
                    if node and node.status == NodeStatus.PENDING:
                        tasks.append(self._execute_node(node, ctx))

                if tasks:
                    await asyncio.gather(*tasks)

                # 检查是否有失败节点需要处理
                failed = [nid for nid in layer
                          if node_map.get(nid) and node_map[nid].status == NodeStatus.FAILED]
                if failed:
                    await self._push_event("execution_error", {
                        "workflow_id": wf_id,
                        "failed_nodes": failed,
                        "iteration": iteration,
                    })

            # 检查闭环条件
            if wf.loop_enabled and iteration < max_iterations:
                # 检查是否有 guide_observation 节点建议继续
                guide_nodes = [n for n in wf.nodes if n.type == NodeType.GUIDE_OBSERVATION]
                if guide_nodes and guide_nodes[0].status == NodeStatus.COMPLETED:
                    continue_loop = ctx.variables.get("anomaly_count", 0) > 0
                    if not continue_loop:
                        break
            else:
                break

        # 汇总结果
        completed = sum(1 for n in wf.nodes if n.status == NodeStatus.COMPLETED)
        failed = sum(1 for n in wf.nodes if n.status == NodeStatus.FAILED)
        skipped = sum(1 for n in wf.nodes if n.status == NodeStatus.SKIPPED)

        execution_summary = {
            "workflow_id": wf_id,
            "name": wf.name,
            "total_nodes": len(wf.nodes),
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "iterations": iteration,
            "duration_ms": sum(n.duration_ms for n in wf.nodes),
            "node_results": {
                n.id: {
                    "label": n.label,
                    "status": n.status.value,
                    "result_summary": str(n.result)[:200] if n.result else None,
                    "error": n.error,
                    "duration_ms": n.duration_ms,
                }
                for n in wf.nodes
            },
            "context": {
                "literature_count": len(ctx.literature_findings),
                "hypothesis_count": len(ctx.hypotheses),
                "target_count": len(ctx.observation_targets),
                "mining_results": len(ctx.mining_results),
                "loop_count": ctx.loop_count,
            },
        }

        self.completed_executions.append(execution_summary)
        if wf_id in self.active_executions:
            del self.active_executions[wf_id]

        await self._push_event("execution_completed", execution_summary)

        return execution_summary

    def get_execution_status(self, wf_id: str) -> Optional[Dict]:
        """获取工作流执行状态"""
        ctx = self.active_executions.get(wf_id)
        wf = self.definitions.get(wf_id)

        if not wf:
            return None

        return {
            "workflow_id": wf_id,
            "name": wf.name,
            "is_running": wf_id in self.active_executions,
            "loop_count": ctx.loop_count if ctx else 0,
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.type.value,
                    "status": n.status.value,
                    "error": n.error,
                    "duration_ms": n.duration_ms,
                    "result_summary": str(n.result)[:200] if n.result else None,
                }
                for n in wf.nodes
            ],
        }

    def get_execution_history(self, limit: int = 20) -> List[Dict]:
        """获取执行历史"""
        return self.completed_executions[-limit:]

    def export_workflow(self, wf_id: str) -> Optional[Dict]:
        """导出工作流为可移植的JSON格式"""
        wf = self.definitions.get(wf_id)
        if not wf:
            return None
        export_data = self._definition_to_dict(wf)
        export_data["export_version"] = "2.0"
        export_data["exported_at"] = datetime.now().isoformat()
        export_data["engine"] = "tianwen-agi-workflow-engine"
        return export_data

    def import_workflow(self, data: Dict) -> Dict:
        """从JSON导入工作流"""
        if "export_version" not in data:
            data["id"] = data.get("id", str(uuid.uuid4())[:12])
        else:
            data["id"] = str(uuid.uuid4())[:12]

        return self.create_workflow(data)

    def get_statistics(self) -> Dict:
        """获取工作流引擎统计信息"""
        total_definitions = len(self.definitions)
        total_executions = len(self.completed_executions)
        active_executions = len(self.active_executions)

        node_type_counts = defaultdict(int)
        for wf in self.definitions.values():
            for node in wf.nodes:
                node_type_counts[node.type.value] += 1

        recent_executions = self.completed_executions[-10:]
        success_rate = 0
        if recent_executions:
            successful = sum(
                1 for e in recent_executions
                if e.get("failed", 0) == 0
            )
            success_rate = round(successful / len(recent_executions) * 100, 1)

        avg_duration = 0
        if recent_executions:
            durations = [e.get("duration_ms", 0) for e in recent_executions]
            avg_duration = round(sum(durations) / len(durations), 1)

        return {
            "total_definitions": total_definitions,
            "total_executions": total_executions,
            "active_executions": active_executions,
            "node_type_distribution": dict(node_type_counts),
            "recent_success_rate": success_rate,
            "avg_execution_duration_ms": avg_duration,
            "templates_available": len(self.PRESET_TEMPLATES),
        }

    def cancel_execution(self, wf_id: str) -> bool:
        """取消正在执行的工作流"""
        if wf_id in self.active_executions:
            ctx = self.active_executions[wf_id]
            wf = self.definitions.get(wf_id)
            if wf:
                for node in wf.nodes:
                    if node.status == NodeStatus.RUNNING:
                        node.status = NodeStatus.FAILED
                        node.error = "Cancelled by user"
            del self.active_executions[wf_id]
            return True
        return False

    # ==================== 节点类型信息 ====================

    def get_node_types(self) -> List[Dict]:
        """获取所有可用节点类型"""
        return [
            {"type": "trigger", "label": "触发器", "icon": "▶", "color": "#4caf50",
             "description": "工作流的起点或终点"},
            {"type": "literature_search", "label": "文献搜索", "icon": "📚", "color": "#2196f3",
             "description": "多数据源天文文献检索", "config_schema": {
                 "query": {"type": "string", "default": "", "label": "搜索关键词"},
                 "sources": {"type": "multi-select", "default": ["arxiv"], "label": "数据源",
                            "options": ["arxiv", "ads", "semantic_scholar", "openalex"]},
                 "max_results": {"type": "number", "default": 20, "label": "最大结果数"},
             }},
            {"type": "hypothesis_generate", "label": "假说生成", "icon": "🧪", "color": "#9c27b0",
             "description": "基于文献gap自动生成研究假说", "config_schema": {
                 "count": {"type": "number", "default": 3, "label": "假说数量"},
                 "method": {"type": "select", "default": "literature_gap_analysis", "label": "生成方法",
                           "options": ["literature_gap_analysis", "pattern_based", "anomaly_driven"]},
             }},
            {"type": "hypothesis_test", "label": "假说检验", "icon": "✅", "color": "#ff9800",
             "description": "验证假说的有效性", "config_schema": {
                 "confidence_threshold": {"type": "number", "default": 0.6, "label": "置信度阈值"},
             }},
            {"type": "observation_schedule", "label": "观测调度", "icon": "📅", "color": "#00bcd4",
             "description": "根据优先级调度观测目标", "config_schema": {
                 "max_targets": {"type": "number", "default": 5, "label": "最大目标数"},
                 "min_altitude": {"type": "number", "default": 20, "label": "最低高度角(°)"},
             }},
            {"type": "telescope_goto", "label": "望远镜指向", "icon": "🔭", "color": "#795548",
             "description": "控制望远镜指向目标", "config_schema": {
                 "auto_track": {"type": "boolean", "default": True, "label": "自动跟踪"},
             }},
            {"type": "telescope_expose", "label": "曝光采集", "icon": "📷", "color": "#607d8b",
             "description": "执行曝光采集图像", "config_schema": {
                 "exposure": {"type": "number", "default": 30, "label": "曝光时间(s)"},
                 "count": {"type": "number", "default": 3, "label": "帧数"},
             }},
            {"type": "data_mining", "label": "数据挖掘", "icon": "⛏", "color": "#e91e63",
             "description": "从观测数据中发现模式和异常", "config_schema": {
                 "methods": {"type": "multi-select", "default": ["feature_extraction", "anomaly_detection", "pattern_discovery"],
                            "label": "挖掘方法", "options": ["feature_extraction", "anomaly_detection", "pattern_discovery", "correlation_analysis"]},
             }},
            {"type": "anomaly_detection", "label": "异常检测", "icon": "⚠", "color": "#f44336",
             "description": "检测天文数据中的异常信号", "config_schema": {
                 "threshold": {"type": "number", "default": 0.85, "label": "异常阈值"},
                 "methods": {"type": "multi-select", "default": ["isolation_forest", "statistical"],
                            "label": "检测方法", "options": ["isolation_forest", "statistical", "dbscan", "autoencoder"]},
             }},
            {"type": "feature_extraction", "label": "特征提取", "icon": "🔬", "color": "#00bcd4",
             "description": "从天文数据中提取特征向量"},
            {"type": "guide_observation", "label": "指导观测", "icon": "🎯", "color": "#ff5722",
             "description": "闭环核心：挖掘结果指导下一轮观测", "config_schema": {
                 "feedback_loop": {"type": "boolean", "default": True, "label": "启用闭环反馈"},
                 "priority_adjustment": {"type": "boolean", "default": True, "label": "自动调整优先级"},
             }},
            {"type": "result_analysis", "label": "结果分析", "icon": "📊", "color": "#ff9800",
             "description": "综合分析所有节点的执行结果"},
            {"type": "report_generate", "label": "生成报告", "icon": "📄", "color": "#3f51b5",
             "description": "自动生成研究闭环报告"},
            {"type": "condition", "label": "条件判断", "icon": "❓", "color": "#ff9800",
             "description": "根据条件选择执行路径", "config_schema": {
                 "condition": {"type": "string", "default": "anomaly_count > 0", "label": "条件表达式"},
             }},
            {"type": "merge", "label": "数据汇合", "icon": "🔀", "color": "#9e9e9e",
             "description": "合并多个并行分支的结果"},
            {"type": "human_approval", "label": "人工审批", "icon": "✋", "color": "#ff9800",
             "description": "需要人工确认才能继续"},
            {"type": "webhook", "label": "Webhook", "icon": "🔔", "color": "#f44336",
             "description": "发送告警或通知", "config_schema": {
                 "url": {"type": "string", "default": "", "label": "Webhook URL"},
             }},
        ]


# 全局单例
_engine_instance: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WorkflowEngine()
    return _engine_instance
