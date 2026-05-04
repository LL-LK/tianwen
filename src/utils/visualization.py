"""
Hermes-AGI Execution Visualization Components
执行过程可视化组件 - Web界面实时展示
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

# ============ 可视化状态 ============

class EngineState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class EngineStatus:
    """引擎状态"""
    name: str
    state: EngineState
    progress: float = 0  # 0-100
    message: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None

@dataclass
class SubTaskVisual:
    """子任务可视化"""
    id: str
    name: str
    skill: str
    status: str  # pending, running, completed, failed
    progress: float = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result_preview: str = ""

@dataclass
class ExecutionVisualization:
    """执行可视化数据"""
    task_id: str
    user_input: str
    engines: Dict[str, EngineStatus]
    subtasks: List[SubTaskVisual]
    cognitive_output: Dict = field(default_factory=dict)
    planning_output: Dict = field(default_factory=dict)
    execution_output: str = ""
    status: str = "pending"  # pending, running, completed, failed
    total_time: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ============ 可视化追踪器 ============

class ExecutionTracker:
    """执行追踪器"""

    def __init__(self, task_id: str, user_input: str):
        self.task_id = task_id
        self.user_input = user_input
        self.start_time = datetime.now()

        # 初始化引擎状态
        self.engines = {
            "cognitive": EngineStatus("认知引擎", EngineState.IDLE),
            "planning": EngineStatus("规划引擎", EngineState.IDLE),
            "execution": EngineStatus("执行引擎", EngineState.IDLE),
            "evolution": EngineStatus("进化系统", EngineState.IDLE),
        }

        self.subtasks: List[SubTaskVisual] = []
        self.cognitive_output: Dict = {}
        self.planning_output: Dict = {}
        self.execution_output: str = ""
        self.status = "pending"

    def start_cognitive(self):
        """开始认知阶段"""
        self.engines["cognitive"].state = EngineState.PROCESSING
        self.engines["cognitive"].start_time = datetime.now().isoformat()
        self.engines["cognitive"].progress = 0

    def update_cognitive(self, progress: float, message: str = ""):
        """更新认知阶段进度"""
        self.engines["cognitive"].progress = progress
        if message:
            self.engines["cognitive"].message = message

    def complete_cognitive(self, output: Dict):
        """完成认知阶段"""
        self.engines["cognitive"].state = EngineState.COMPLETED
        self.engines["cognitive"].progress = 100
        self.engines["cognitive"].end_time = datetime.now().isoformat()
        self.cognitive_output = output

    def start_planning(self):
        """开始规划阶段"""
        self.engines["planning"].state = EngineState.PROCESSING
        self.engines["planning"].start_time = datetime.now().isoformat()

    def update_planning(self, progress: float, message: str = ""):
        """更新规划阶段进度"""
        self.engines["planning"].progress = progress
        if message:
            self.engines["planning"].message = message

    def complete_planning(self, subtasks: List[SubTaskVisual], output: Dict):
        """完成规划阶段"""
        self.engines["planning"].state = EngineState.COMPLETED
        self.engines["planning"].progress = 100
        self.engines["planning"].end_time = datetime.now().isoformat()
        self.subtasks = subtasks
        self.planning_output = output

    def start_execution(self):
        """开始执行阶段"""
        self.engines["execution"].state = EngineState.PROCESSING
        self.engines["execution"].start_time = datetime.now().isoformat()

    def update_subtask(self, subtask_id: str, status: str, progress: float = 0, result_preview: str = ""):
        """更新子任务状态"""
        for task in self.subtasks:
            if task.id == subtask_id:
                task.status = status
                task.progress = progress
                if status == "running":
                    task.start_time = datetime.now().isoformat()
                elif status in ["completed", "failed"]:
                    task.end_time = datetime.now().isoformat()
                if result_preview:
                    task.result_preview = result_preview
                break

    def complete_execution(self, output: str):
        """完成执行阶段"""
        self.engines["execution"].state = EngineState.COMPLETED
        self.engines["execution"].end_time = datetime.now().isoformat()
        self.execution_output = output

    def start_evolution(self):
        """开始进化阶段"""
        self.engines["evolution"].state = EngineState.PROCESSING
        self.engines["evolution"].start_time = datetime.now().isoformat()

    def complete_evolution(self):
        """完成进化阶段"""
        self.engines["evolution"].state = EngineState.COMPLETED
        self.engines["evolution"].progress = 100
        self.engines["evolution"].end_time = datetime.now().isoformat()

    def set_error(self, engine_name: str, error_message: str):
        """设置错误"""
        self.engines[engine_name].state = EngineState.ERROR
        self.engines[engine_name].message = error_message
        self.status = "failed"

    def get_visualization(self) -> ExecutionVisualization:
        """获取可视化数据"""
        total_time = (datetime.now() - self.start_time).total_seconds()

        return ExecutionVisualization(
            task_id=self.task_id,
            user_input=self.user_input,
            engines={
                name: EngineStatus(
                    name=status.name,
                    state=status.state,
                    progress=status.progress,
                    message=status.message,
                    start_time=status.start_time,
                    end_time=status.end_time
                )
                for name, status in self.engines.items()
            },
            subtasks=self.subtasks,
            cognitive_output=self.cognitive_output,
            planning_output=self.planning_output,
            execution_output=self.execution_output,
            status=self.status,
            total_time=total_time,
            timestamp=datetime.now().isoformat()
        )

    def to_dict(self) -> Dict:
        """转换为字典"""
        vis = self.get_visualization()
        return {
            "task_id": vis.task_id,
            "user_input": vis.user_input,
            "status": vis.status,
            "total_time": f"{vis.total_time:.2f}s",
            "engines": {
                name: {
                    "state": status.state.value,
                    "progress": status.progress,
                    "message": status.message,
                    "time": f"{status.start_time or ''} - {status.end_time or ''}"
                }
                for name, status in vis.engines.items()
            },
            "subtasks": [
                {
                    "id": t.id,
                    "skill": t.skill,
                    "status": t.status,
                    "progress": t.progress,
                    "result_preview": t.result_preview[:50] + "..." if len(t.result_preview) > 50 else t.result_preview
                }
                for t in vis.subtasks
            ],
            "cognitive": vis.cognitive_output,
            "planning": vis.planning_output,
            "timestamp": vis.timestamp
        }

# ============ WebSocket更新器 ============

class VisualizationBroadcaster:
    """可视化数据广播器 - 用于WebSocket实时更新"""

    def __init__(self):
        self.active_trackers: Dict[str, ExecutionTracker] = {}
        self.listeners: List = []  # WebSocket connections

    def create_tracker(self, task_id: str, user_input: str) -> ExecutionTracker:
        """创建追踪器"""
        tracker = ExecutionTracker(task_id, user_input)
        self.active_trackers[task_id] = tracker
        return tracker

    def get_tracker(self, task_id: str) -> Optional[ExecutionTracker]:
        """获取追踪器"""
        return self.active_trackers.get(task_id)

    def remove_tracker(self, task_id: str):
        """移除追踪器"""
        if task_id in self.active_trackers:
            del self.active_trackers[task_id]

    def broadcast_update(self, task_id: str):
        """广播更新 - 发送给所有监听者"""
        tracker = self.get_tracker(task_id)
        if not tracker:
            return

        data = tracker.to_dict()
        for listener in self.listeners:
            try:
                # listener.send_json(data)  # WebSocket发送
                pass
            except:
                pass

    def get_current_state(self, task_id: str) -> Optional[Dict]:
        """获取当前状态"""
        tracker = self.get_tracker(task_id)
        if tracker:
            return tracker.to_dict()
        return None

# ============ 前端可视化组件代码 ============

VISUALIZATION_HTML_COMPONENTS = '''
<!-- 执行过程可视化组件 -->

<!-- 引擎状态卡片 -->
<div class="engine-status-card" id="enginePanel">
    <div class="engine-item" id="cognitiveEngine">
        <div class="engine-icon">🧠</div>
        <div class="engine-name">认知引擎</div>
        <div class="engine-progress-bar">
            <div class="engine-progress-fill" style="width: 0%"></div>
        </div>
        <div class="engine-status-text">待机中</div>
    </div>
    <div class="engine-item" id="planningEngine">
        <div class="engine-icon">📋</div>
        <div class="engine-name">规划引擎</div>
        <div class="engine-progress-bar">
            <div class="engine-progress-fill" style="width: 0%"></div>
        </div>
        <div class="engine-status-text">待机中</div>
    </div>
    <div class="engine-item" id="executionEngine">
        <div class="engine-icon">⚙️</div>
        <div class="engine-name">执行引擎</div>
        <div class="engine-progress-bar">
            <div class="engine-progress-fill" style="width: 0%"></div>
        </div>
        <div class="engine-status-text">待机中</div>
    </div>
    <div class="engine-item" id="evolutionEngine">
        <div class="engine-icon">🧩</div>
        <div class="engine-name">进化系统</div>
        <div class="engine-progress-bar">
            <div class="engine-progress-fill" style="width: 0%"></div>
        </div>
        <div class="engine-status-text">待机中</div>
    </div>
</div>

<!-- 子任务执行面板 -->
<div class="subtask-panel" id="subtaskPanel">
    <h3>📊 执行进度</h3>
    <div class="subtask-list" id="subtaskList">
        <!-- 动态生成 -->
    </div>
</div>

<!-- 时间线面板 -->
<div class="timeline-panel" id="timelinePanel">
    <h3>⏱️ 执行时间线</h3>
    <div class="timeline" id="timeline">
        <!-- 动态生成 -->
    </div>
</div>

<style>
.engine-status-card {
    display: flex;
    gap: 16px;
    padding: 16px;
    background: white;
    border-radius: 12px;
    margin-bottom: 16px;
}

.engine-item {
    flex: 1;
    text-align: center;
    padding: 12px;
    border-radius: 8px;
    background: #f9fafb;
    transition: all 0.3s;
}

.engine-item.processing {
    background: #fef3c7;
}

.engine-item.completed {
    background: #d1fae5;
}

.engine-item.error {
    background: #fee2e2;
}

.engine-icon {
    font-size: 32px;
    margin-bottom: 8px;
}

.engine-progress-bar {
    height: 6px;
    background: #e5e7eb;
    border-radius: 3px;
    margin: 8px 0;
    overflow: hidden;
}

.engine-progress-fill {
    height: 100%;
    background: #3b82f6;
    transition: width 0.3s ease;
}

.engine-status-text {
    font-size: 12px;
    color: #6b7280;
}

.subtask-panel {
    background: white;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
}

.subtask-item {
    display: flex;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid #e5e7eb;
}

.subtask-item:last-child {
    border-bottom: none;
}

.subtask-status {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
}

.subtask-status.pending { background: #e5e7eb; }
.subtask-status.running { background: #fef3c7; }
.subtask-status.completed { background: #d1fae5; }
.subtask-status.failed { background: #fee2e2; }

.timeline-item {
    display: flex;
    padding: 8px 0;
    border-left: 2px solid #e5e7eb;
    margin-left: 8px;
    padding-left: 16px;
    position: relative;
}

.timeline-item::before {
    content: '';
    position: absolute;
    left: -6px;
    top: 12px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #3b82f6;
}
</style>

<script>
// 实时更新引擎状态
function updateEngineStatus(engineName, state, progress, message) {
    const engineEl = document.getElementById(engineName + 'Engine');
    const progressFill = engineEl.querySelector('.engine-progress-fill');
    const statusText = engineEl.querySelector('.engine-status-text');

    progressFill.style.width = progress + '%';
    statusText.textContent = message || state;

    engineEl.className = 'engine-item ' + state;
}

// 更新子任务列表
function updateSubtaskList(subtasks) {
    const listEl = document.getElementById('subtaskList');
    listEl.innerHTML = subtasks.map(task => {
        const statusIcons = {
            pending: '⏳',
            running: '🔄',
            completed: '✅',
            failed: '❌'
        };
        return `
            <div class="subtask-item">
                <div class="subtask-status ${task.status}">${statusIcons[task.status]}</div>
                <div>
                    <div><strong>${task.skill}</strong></div>
                    <div style="font-size: 12px; color: #6b7280;">${task.id}</div>
                </div>
                <div style="margin-left: auto;">
                    ${task.progress}%
                </div>
            </div>
        `;
    }).join('');
}

// 更新执行时间线
function updateTimeline(events) {
    const timelineEl = document.getElementById('timeline');
    timelineEl.innerHTML = events.map(event => `
        <div class="timeline-item">
            <div><strong>${event.engine}</strong></div>
            <div style="font-size: 12px; color: #6b7280;">${event.message}</div>
            <div style="font-size: 12px;">${event.time}</div>
        </div>
    `).join('');
}

// 处理WebSocket消息
// ws.onmessage = function(event) {
//     const data = JSON.parse(event.data);
//     if (data.type === 'progress') {
//         updateEngineStatus(data.engine, data.state, data.progress, data.message);
//         updateSubtaskList(data.subtasks);
//     }
// };
</script>
'''

# ============ 示例用法 ============

def demo():
    """演示可视化"""
    print("=" * 50)
    print("Hermes-AGI Visualization Demo")
    print("=" * 50)

    # 创建追踪器
    tracker = ExecutionTracker("TASK-001", "创建一个用户管理系统")

    # 模拟执行流程
    print("\n1. 开始认知阶段...")
    tracker.start_cognitive()
    tracker.update_cognitive(30, "解析用户意图...")
    tracker.update_cognitive(60, "提取关键实体...")
    tracker.update_cognitive(100, "意图识别完成")
    tracker.complete_cognitive({
        "intent": "Execute.Develop.Fullstack",
        "entities": ["User", "Management"],
        "skills": ["Backend", "Frontend", "Database"]
    })
    print(f"   认知输出: {tracker.cognitive_output}")

    print("\n2. 开始规划阶段...")
    tracker.start_planning()
    from src.core.cognitive import SubTask
    subtasks = [
        SubTaskVisual(id="T1", name="需求分析", skill="Product", status="completed"),
        SubTaskVisual(id="T2", name="架构设计", skill="Architecture", status="completed"),
        SubTaskVisual(id="T3", name="数据库设计", skill="Database", status="running"),
        SubTaskVisual(id="T4", name="后端开发", skill="Backend", status="pending"),
        SubTaskVisual(id="T5", name="前端开发", skill="Frontend", status="pending"),
    ]
    tracker.complete_planning(subtasks, {"estimated_time": "2小时"})
    print(f"   规划了 {len(subtasks)} 个子任务")

    print("\n3. 开始执行阶段...")
    tracker.start_execution()
    tracker.update_subtask("T3", "completed", 100, "数据库设计完成")
    tracker.update_subtask("T4", "running", 50, "实现中...")
    tracker.update_subtask("T4", "completed", 100, "后端API完成")
    tracker.update_subtask("T5", "completed", 100, "前端组件完成")
    tracker.complete_execution("系统开发完成")
    print("   执行完成")

    print("\n4. 开始进化阶段...")
    tracker.start_evolution()
    tracker.complete_evolution()
    print("   经验已记录")

    # 获取最终状态
    state = tracker.to_dict()
    print("\n" + "=" * 50)
    print("执行状态:")
    print(f"  状态: {state['status']}")
    print(f"  总耗时: {state['total_time']}")
    print("\n  引擎状态:")
    for name, info in state['engines'].items():
        print(f"    {name}: {info['state']} ({info['progress']}%)")

    print("\n  子任务:")
    for task in state['subtasks']:
        print(f"    {task['id']} - {task['skill']}: {task['status']}")

    # 生成可视化HTML
    print("\n" + "=" * 50)
    print("可视化HTML组件已生成，可嵌入Web界面")

if __name__ == "__main__":
    demo()