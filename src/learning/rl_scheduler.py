"""
强化学习观测调度器 (RL-based Observation Scheduler)

基于强化学习的观测调度算法，使用PPO或DQN优化观测效率。
参考TSI的调度碎片化指标设计。

核心概念:
- 状态空间: 望远镜位置、可见目标列表、时间窗口、已调度目标
- 动作空间: 选择下一个观测目标
- 奖励函数: 观测效率 × 优先级权重 - 调度碎片惩罚

参考TSI的调度碎片化指标:
- idle_operable_hours: 空闲但可操作的小时数
- gap_count/mean/median/p90: 碎片间隙统计
- scheduled_fraction_of_operable: 可操作时间中已调度的比例

作者: 天问-AGI团队
版本: 1.0.0
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time as dt_time
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
from statistics import mean, median

# 尝试从enhanced_observation_scheduler导入必要的类
try:
    from enhanced_observation_scheduler import (
        GeographicLocation,
        ObservationTarget,
        Constraints,
        VisibilityWindow,
        AstronomicalCalculator,
        AstronomicalNightCalculator,
        VisibilityCalculator,
        FragmentationAnalyzer,
        ObservationScorer,
        EnhancedObservationScheduler,
        ObservationType
    )
    HAS_ENHANCED_SCHEDULER = True
except ImportError:
    HAS_ENHANCED_SCHEDULER = False


# ============ 状态空间定义 ============

@dataclass
class SchedulerState:
    """
    调度器状态

    描述了强化学习环境中 agent 所观察到的完整状态

    属性:
        telescope_ra: float - 当前望远镜指向的赤经 (度)
        telescope_dec: float - 当前望远镜指向的赤纬 (度)
        current_time: datetime - 当前时间
        astronomical_night_start: Optional[datetime] - 夜天文开始时间
        astronomical_night_end: Optional[datetime] - 夜天文结束时间
        visible_targets: List[Dict] - 当前可见目标列表
            每个目标是一个字典，包含:
            - name: str - 目标名称
            - ra: float - 赤经
            - dec: float - 赤纬
            - priority: float - 优先级 (0-1)
            - estimated_time: float - 预估观测时间 (分钟)
            - window_start: datetime - 窗口开始时间
            - window_end: datetime - 窗口结束时间
        scheduled_targets: List[Dict] - 已调度的目标列表
        remaining_targets: List[Dict] - 尚未调度的目标列表
        idle_hours: float - 空闲小时数
        gap_count: int - 碎片数量 (间隙数)
        scheduled_fraction: float - 已调度的可操作时间比例
    """

    # 望远镜状态
    telescope_ra: float = 0.0      # 当前赤经 (度)
    telescope_dec: float = 0.0     # 当前赤纬 (度)

    # 时间信息
    current_time: datetime = field(default_factory=datetime.now)
    astronomical_night_start: Optional[datetime] = None
    astronomical_night_end: Optional[datetime] = None

    # 目标信息
    visible_targets: List[Dict] = field(default_factory=list)  # 可见目标列表
    scheduled_targets: List[Dict] = field(default_factory=list)  # 已调度目标
    remaining_targets: List[Dict] = field(default_factory=list)  # 剩余目标

    # 调度统计
    idle_hours: float = 0.0       # 空闲小时数
    gap_count: int = 0            # 碎片数量
    scheduled_fraction: float = 0.0  # 已调度比例

    def to_vector(self) -> List[float]:
        """
        将状态转换为特征向量
        用于神经网络输入

        返回:
            List[float] - 状态特征向量
        """
        # 基础特征: 望远镜位置 (2)
        features = [
            self.telescope_ra / 360.0,  # 归一化赤经
            (self.telescope_dec + 90.0) / 180.0,  # 归一化赤纬
        ]

        # 时间特征 (4)
        if self.astronomical_night_start and self.astronomical_night_end:
            night_duration = (self.astronomical_night_end - self.astronomical_night_start).total_seconds()
            time_elapsed = (self.current_time - self.astronomical_night_start).total_seconds()
            features.extend([
                time_elapsed / max(night_duration, 1.0),  # 夜间时间进度
                night_duration / 3600.0 / 12.0,  # 夜间时长 (归一化)
            ])
        else:
            features.extend([0.0, 0.0])

        # 目标数量特征 (4)
        total_targets = len(self.visible_targets) + len(self.scheduled_targets) + len(self.remaining_targets)
        features.extend([
            len(self.visible_targets) / max(total_targets, 1),
            len(self.scheduled_targets) / max(total_targets, 1),
            len(self.remaining_targets) / max(total_targets, 1),
            self.scheduled_fraction,
        ])

        # 调度效率特征 (3)
        features.extend([
            self.idle_hours / 12.0,  # 归一化空闲时间
            min(self.gap_count, 10) / 10.0,  # 归一化碎片数
            1.0 - self.scheduled_fraction,  # 未调度比例
        ])

        # 可见目标优先级特征 (最高、最低、平均) (3)
        if self.visible_targets:
            priorities = [t.get('priority', 0.5) for t in self.visible_targets]
            features.extend([
                max(priorities),
                min(priorities),
                mean(priorities),
            ])
        else:
            features.extend([0.0, 0.0, 0.0])

        return features

    def get_state_dim(self) -> int:
        """获取状态向量的维度"""
        return len(self.to_vector())


# ============ 动作空间定义 ============

class SchedulerAction(Enum):
    """
    调度动作枚举

    定义了强化学习 agent 可以执行的动作:
    - SELECT_TARGET_NEXT: 选择下一个要观测的目标
    - WAIT_FOR_BETTER: 等待更好的观测时机
    - RESCHEDULE: 重新调度
    - FINISH_SCHEDULING: 完成调度
    """

    SELECT_TARGET_NEXT = "select_target_next"  # 选择下一个目标
    WAIT_FOR_BETTER = "wait_for_better"       # 等待更好的时机
    RESCHEDULE = "reschedule"                 # 重新调度
    FINISH_SCHEDULING = "finish"              # 完成调度

    def to_index(self) -> int:
        """转换为动作索引"""
        return list(SchedulerAction).index(self)


# ============ 奖励函数 ============

def compute_reward(
    action: SchedulerAction,
    state: SchedulerState,
    selected_target: Optional[Dict] = None
) -> float:
    """
    计算奖励函数

    奖励组成:
    1. 观测效率奖励: 优先级 × 可见性窗口长度
    2. 时间连续性奖励: 减少碎片
    3. 完成奖励: 所有目标完成

    惩罚:
    1. 碎片化惩罚: gap越多惩罚越大
    2. 优先级错过惩罚: 高优先级目标等待太久

    参数:
        action: SchedulerAction - 执行的动作
        state: SchedulerState - 当前状态
        selected_target: Optional[Dict] - 选择的目标

    返回:
        float - 奖励值
    """
    reward = 0.0

    if action == SchedulerAction.SELECT_TARGET_NEXT and selected_target:
        # 正奖励: 选择高优先级目标
        priority = selected_target.get('priority', 0.5)
        reward += priority * 10.0

        # 正奖励: 观测效率 (基于预估观测时间)
        observation_time = selected_target.get('estimated_time', 60)
        reward += observation_time / 60.0  # 归一化

        # 正奖励: 如果是紧急目标（窗口即将结束）
        window_end = selected_target.get('window_end')
        if window_end and state.current_time:
            time_left = (window_end - state.current_time).total_seconds() / 60
            if time_left < 30:  # 窗口不足30分钟
                reward += 5.0

        # 负奖励: 如果造成碎片化
        if state.gap_count > 0:
            reward -= state.gap_count * 0.5

        # 正奖励: 如果减少总碎片数（调度更紧凑）
        if state.scheduled_fraction > 0.8:
            reward += 3.0

    elif action == SchedulerAction.WAIT_FOR_BETTER:
        # 负奖励: 等待意味着浪费时间
        reward -= 1.0

        # 但如果是为了更好的目标，可能值得
        if selected_target and selected_target.get('priority', 0) > 0.8:
            reward += 2.0

        # 如果所有高优先级目标都已调度，等待是合理的
        if not any(t.get('priority', 0) > 0.7 for t in state.remaining_targets):
            reward += 1.0

    elif action == SchedulerAction.FINISH_SCHEDULING:
        # 正奖励: 完成调度
        reward += 5.0

        # 额外奖励: 如果调度效率高
        if state.scheduled_fraction > 0.9:
            reward += 10.0

        # 额外奖励: 如果碎片很少
        if state.gap_count == 0:
            reward += 5.0

        # 惩罚: 如果有很多目标没被调度
        if state.remaining_targets:
            reward -= len(state.remaining_targets) * 0.5

    elif action == SchedulerAction.RESCHEDULE:
        # 轻微惩罚: 重新调度意味着之前有问题
        reward -= 2.0

        # 但如果能提高效率，可能值得
        if state.gap_count > 5:
            reward += 3.0  # 补偿碎片化问题

    return reward


# ============ DQN调度器 ============

class DQNScheduler:
    """
    DQN调度器

    使用深度Q网络 (Deep Q-Network) 算法进行调度决策。
    这里使用简化的Q表实现，实际应用中应使用PyTorch或TensorFlow。

    算法特点:
    - 使用epsilon-greedy进行探索/利用权衡
    - 使用经验回放 (Experience Replay) 进行训练
    - 使用目标网络 (Target Network) 提高稳定性

    属性:
        state_dim: int - 状态向量维度
        action_dim: int - 动作空间大小
        learning_rate: float - 学习率
        gamma: float - 折扣因子
        epsilon: float - 探索率
        epsilon_decay: float - 探索率衰减
        epsilon_min: float - 最小探索率
    """

    def __init__(
        self,
        state_dim: int = 16,
        action_dim: int = 4,
        learning_rate: float = 0.001
    ):
        """
        初始化DQN调度器

        参数:
            state_dim: int - 状态向量维度
            action_dim: int - 动作空间大小
            learning_rate: float - 学习率
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate

        # 简化的Q网络 (实际应用中使用PyTorch/TensorFlow)
        # 这里使用模拟的Q表 {state_key: Q_values}
        self.q_table: Dict[str, List[float]] = {}

        # 目标网络Q表 (用于稳定训练)
        self.target_q_table: Dict[str, List[float]] = {}

        # 超参数
        self.gamma = 0.95    # 折扣因子
        self.epsilon = 1.0  # 探索率
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.1

        # 经验回放
        self.memory: List[Tuple[SchedulerState, SchedulerAction, float, SchedulerState, bool]] = []
        self.batch_size = 32
        self.memory_capacity = 10000

        # 训练统计
        self.training_step = 0
        self.update_target_every = 100  # 每100步更新目标网络

    def get_q_values(self, state: SchedulerState) -> List[float]:
        """
        获取Q值

        参数:
            state: SchedulerState - 当前状态

        返回:
            List[float] - 每个动作的Q值
        """
        state_key = self._encode_state(state)

        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0] * self.action_dim

        return self.q_table[state_key]

    def choose_action(self, state: SchedulerState) -> SchedulerAction:
        """
        选择动作 (epsilon-greedy策略)

        参数:
            state: SchedulerState - 当前状态

        返回:
            SchedulerAction - 选择的动作
        """
        if random.random() < self.epsilon:
            # 随机探索
            return random.choice(list(SchedulerAction))
        else:
            # 利用: 选择Q值最大的动作
            q_values = self.get_q_values(state)
            best_action_idx = q_values.index(max(q_values))
            return list(SchedulerAction)[best_action_idx]

    def remember(
        self,
        state: SchedulerState,
        action: SchedulerAction,
        reward: float,
        next_state: SchedulerState,
        done: bool
    ):
        """
        存储经验到回放缓冲区

        参数:
            state: SchedulerState - 当前状态
            action: SchedulerAction - 执行的动作
            reward: float - 获得的奖励
            next_state: SchedulerState - 下一个状态
            done: bool - 是否结束
        """
        self.memory.append((state, action, reward, next_state, done))

        # 如果超过容量，移除最旧的经验
        if len(self.memory) > self.memory_capacity:
            self.memory.pop(0)

    def train_step(self, batch: Optional[List[Tuple]] = None) -> float:
        """
        训练一步

        参数:
            batch: Optional[List[Tuple]] - 可选的批数据，如果不提供则从记忆中采样

        返回:
            float - 本次的TD误差
        """
        if batch is None:
            # 从记忆中随机采样
            if len(self.memory) < self.batch_size:
                return 0.0
            batch = random.sample(self.memory, self.batch_size)

        total_td_error = 0.0

        for state, action, reward, next_state, done in batch:
            state_key = self._encode_state(state)
            next_state_key = self._encode_state(next_state)

            # 获取当前Q值
            if state_key not in self.q_table:
                self.q_table[state_key] = [0.0] * self.action_dim
            if next_state_key not in self.q_table:
                self.q_table[next_state_key] = [0.0] * self.action_dim

            action_idx = action.to_index()

            # Q-learning更新
            current_q = self.q_table[state_key][action_idx]
            max_next_q = max(self.target_q_table.get(next_state_key, [0.0] * self.action_dim))

            # 如果结束，没有未来奖励
            if done:
                td_target = reward
            else:
                td_target = reward + self.gamma * max_next_q

            td_error = td_target - current_q
            self.q_table[state_key][action_idx] += self.learning_rate * td_error
            total_td_error += abs(td_error)

        # 衰减探索率
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        # 定期更新目标网络
        self.training_step += 1
        if self.training_step % self.update_target_every == 0:
            self._update_target_network()

        return total_td_error / len(batch) if batch else 0.0

    def _update_target_network(self):
        """更新目标网络"""
        self.target_q_table = {k: v[:] for k, v in self.q_table.items()}

    def _encode_state(self, state: SchedulerState) -> str:
        """
        编码状态为字符串键

        用于Q表的键值

        参数:
            state: SchedulerState - 状态

        返回:
            str - 编码后的状态键
        """
        # 使用简化的编码：位置 + 可见目标数 + 已调度目标数
        return f"{state.telescope_ra:.0f}_{state.telescope_dec:.0f}_{len(state.visible_targets)}_{len(state.scheduled_targets)}"

    def save(self, path: str):
        """
        保存Q表到文件

        参数:
            path: str - 保存路径
        """
        import json
        data = {
            'q_table': {k: v for k, v in self.q_table.items()},
            'epsilon': self.epsilon,
            'training_step': self.training_step
        }
        with open(path, 'w') as f:
            json.dump(data, f)

    def load(self, path: str):
        """
        从文件加载Q表

        参数:
            path: str - 加载路径
        """
        import json
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.q_table = data.get('q_table', {})
            self.epsilon = data.get('epsilon', 0.1)
            self.training_step = data.get('training_step', 0)
        except FileNotFoundError:
            pass  # 如果文件不存在，使用默认初始化


# ============ PPO调度器 ============

class PPOScheduler:
    """
    PPO调度器

    使用Proximal Policy Optimization (PPO) 算法
    适合连续动作空间，适合多目标优化问题。

    算法特点:
    - 使用clip损失函数限制策略更新幅度
    - 使用GAE (Generalized Advantage Estimation) 计算优势函数
    - 适合连续动作空间

    属性:
        clip_epsilon: float - PPO的clip参数
        gamma: float - 折扣因子
        lambda_gae: float - GAE的lambda参数
        learning_rate: float - 学习率
    """

    def __init__(self):
        """初始化PPO调度器"""
        self.policy_net: Dict[str, Any] = {}  # 策略网络
        self.value_net: Dict[str, float] = {}   # 价值网络

        # PPO超参数
        self.clip_epsilon = 0.2
        self.gamma = 0.99
        self.lambda_gae = 0.95
        self.learning_rate = 3e-4

        # 训练数据
        self.trajectories: List[Dict[str, Any]] = []
        self.batch_size = 64

        # 目标选择策略参数
        self.priority_weight = 0.4
        self.efficiency_weight = 0.3
        self.smoothness_weight = 0.3

    async def optimize_schedule(
        self,
        targets: List[Dict],
        constraints: Dict,
        time_window: Tuple[datetime, datetime]
    ) -> List[Dict]:
        """
        优化调度计划

        参数:
            targets: List[Dict] - 目标列表
                每个目标是一个字典，包含:
                - name: str - 目标名称
                - ra: float - 赤经
                - dec: float - 赤纬
                - priority: float - 优先级 (0-1)
                - estimated_time: float - 预估观测时间 (分钟)
            constraints: Dict - 约束条件
                - min_alt: float - 最低高度角
                - max_gap: float - 最大间隙
                - ...
            time_window: Tuple[datetime, datetime] - 可用时间窗口

        返回:
            List[Dict] - 优化后的调度计划
        """
        # 初始化调度计划
        schedule = []
        current_time = time_window[0]

        # 迭代优化
        for iteration in range(100):  # 最多100次迭代
            # 计算当前状态
            state = self._compute_state(targets, schedule, current_time)

            # 策略选择动作
            action = self._policy(state, targets)

            # 执行动作并获取奖励
            reward = self._execute_and_compute_reward(action, schedule, targets, current_time)

            # 更新当前时间
            if action["action"] == "select" and "target_idx" in action:
                target = targets[action["target_idx"]]
                current_time += timedelta(minutes=target.get("estimated_time", 60))

            # 记录轨迹
            self._record_trajectory(state, action, reward)

            # 更新策略
            if len(self.trajectories) > self.batch_size:
                self._ppo_update()

            # 检查是否完成
            if action["action"] == "finish" or current_time >= time_window[1]:
                break

        return schedule

    def _compute_state(
        self,
        targets: List[Dict],
        schedule: List[Dict],
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        计算当前状态

        参数:
            targets: List[Dict] - 所有目标
            schedule: List[Dict] - 当前调度计划
            current_time: datetime - 当前时间

        返回:
            Dict[str, Any] - 状态字典
        """
        return {
            "time_progress": (current_time - schedule[0]["start"]).total_seconds()
                              if schedule else 0,
            "n_targets": len(targets),
            "n_scheduled": len(schedule),
            "current_ra": schedule[-1]["ra"] if schedule else 0,
            "current_dec": schedule[-1]["dec"] if schedule else 0,
            "remaining_time": 0  # 简化处理
        }

    def _policy(self, state: Dict[str, Any], targets: List[Dict]) -> Dict[str, Any]:
        """
        策略函数 - 输出动作概率

        使用加权评分选择目标

        参数:
            state: Dict[str, Any] - 当前状态
            targets: List[Dict] - 可选目标

        返回:
            Dict[str, Any] - 动作字典
        """
        if not targets:
            return {"action": "finish"}

        # 计算每个目标的评分
        scores = []
        for i, target in enumerate(targets):
            # 检查是否已调度
            if target.get("scheduled", False):
                scores.append(-1.0)
                continue

            priority = target.get("priority", 0.5)
            estimated_time = target.get("estimated_time", 60)

            # 综合评分
            score = (
                self.priority_weight * priority +
                self.efficiency_weight * (estimated_time / 60.0) +
                self.smoothness_weight * (1.0 / (1.0 + target.get("distance_from_last", 1.0)))
            )
            scores.append(score)

        # 选择最高分的目标
        best_idx = scores.index(max(scores))
        if scores[best_idx] < 0:
            return {"action": "finish"}

        return {"action": "select", "target_idx": best_idx}

    def _execute_and_compute_reward(
        self,
        action: Dict[str, Any],
        schedule: List[Dict],
        targets: List[Dict],
        current_time: datetime
    ) -> float:
        """
        执行动作并计算奖励

        参数:
            action: Dict[str, Any] - 动作
            schedule: List[Dict] - 当前调度计划
            targets: List[Dict] - 所有目标
            current_time: datetime - 当前时间

        返回:
            float - 奖励值
        """
        if action["action"] == "select" and "target_idx" in action:
            target = targets[action["target_idx"]]
            target["scheduled"] = True

            # 添加到调度计划
            schedule.append({
                "name": target["name"],
                "ra": target["ra"],
                "dec": target["dec"],
                "start": current_time,
                "end": current_time + timedelta(minutes=target.get("estimated_time", 60)),
                "priority": target.get("priority", 0.5)
            })

            return target.get("priority", 0.5) * 10.0

        return -1.0

    def _record_trajectory(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        reward: float
    ):
        """
        记录轨迹

        参数:
            state: Dict[str, Any] - 状态
            action: Dict[str, Any] - 动作
            reward: float - 奖励
        """
        self.trajectories.append({
            "state": state,
            "action": action,
            "reward": reward,
            "timestamp": datetime.now()
        })

        # 保留最近1000条轨迹
        if len(self.trajectories) > 1000:
            self.trajectories = self.trajectories[-1000:]

    def _ppo_update(self):
        """
        PPO更新

        简化的PPO更新逻辑
        实际应该使用clip loss和value loss
        """
        # 简化的更新：保留最近的数据
        self.trajectories = self.trajectories[-self.batch_size:]


# ============ 调度碎片化分析 ============

@dataclass
class RLFragmentationMetrics:
    """
    强化学习调度碎片化指标

    用于评估调度方案的质量，参考TSI的FragmentationAnalyzer设计

    属性:
        idle_operable_hours: float - 空闲但可操作的小时数
        gap_count: int - 碎片间隙数量
        gap_mean_minutes: float - 间隙平均时长 (分钟)
        gap_median_minutes: float - 间隙中位数时长 (分钟)
        gap_p90_minutes: float - 间隙90分位时长 (分钟)
        scheduled_fraction: float - 已调度的可操作时间比例
    """

    idle_operable_hours: float = 0.0
    gap_count: int = 0
    gap_mean_minutes: float = 0.0
    gap_median_minutes: float = 0.0
    gap_p90_minutes: float = 0.0
    scheduled_fraction: float = 0.0

    def __str__(self) -> str:
        return (
            f"RLFragmentationMetrics(idle_hours={self.idle_operable_hours:.2f}, "
            f"gaps={self.gap_count}, "
            f"gap_mean={self.gap_mean_minutes:.1f}min, "
            f"gap_median={self.gap_median_minutes:.1f}min, "
            f"gap_p90={self.gap_p90_minutes:.1f}min, "
            f"scheduled_fraction={self.scheduled_fraction:.2%})"
        )

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "idle_operable_hours": self.idle_operable_hours,
            "gap_count": self.gap_count,
            "gap_mean_minutes": self.gap_mean_minutes,
            "gap_median_minutes": self.gap_median_minutes,
            "gap_p90_minutes": self.gap_p90_minutes,
            "scheduled_fraction": self.scheduled_fraction
        }


def compute_fragmentation_metrics(
    operable_periods: List[Tuple[datetime, datetime]],
    scheduled_blocks: List[Tuple[datetime, datetime]]
) -> RLFragmentationMetrics:
    """
    计算调度碎片化指标

    参考TSI的FragmentationAnalyzer设计

    算法:
    1. 计算总可操作时间
    2. 计算已调度时间
    3. 找出未调度的间隙
    4. 计算间隙统计指标

    参数:
        operable_periods: List[Tuple[datetime, datetime]] - 可操作时间段列表
        scheduled_blocks: List[Tuple[datetime, datetime]] - 已调度的时间块列表

    返回:
        RLFragmentationMetrics - 碎片化指标
    """
    metrics = RLFragmentationMetrics()

    if not operable_periods:
        return metrics

    # 计算总可操作时间
    total_operable_seconds = sum(
        (end - start).total_seconds()
        for start, end in operable_periods
    )
    metrics.idle_operable_hours = total_operable_seconds / 3600.0

    # 计算调度时间
    scheduled_seconds = sum(
        (end - start).total_seconds()
        for start, end in scheduled_blocks
    )

    # 计算已调度比例
    metrics.scheduled_fraction = (
        scheduled_seconds / total_operable_seconds
        if total_operable_seconds > 0 else 0.0
    )

    # 计算碎片间隙
    all_periods = sorted(operable_periods + scheduled_blocks)
    gaps = []

    for i in range(1, len(all_periods)):
        prev_end = all_periods[i-1][1]
        curr_start = all_periods[i][0]
        gap_minutes = (curr_start - prev_end).total_seconds() / 60

        if gap_minutes > 1:  # 忽略小于1分钟的间隙
            gaps.append(gap_minutes)

    metrics.gap_count = len(gaps)

    if gaps:
        metrics.gap_mean_minutes = sum(gaps) / len(gaps)
        sorted_gaps = sorted(gaps)
        metrics.gap_median_minutes = sorted_gaps[len(gaps) // 2]
        metrics.gap_p90_minutes = sorted_gaps[int(len(gaps) * 0.9)]

    return metrics


# ============ 多目标协调优化器 ============

class MultiObjectiveOptimizer:
    """
    多目标协调优化器

    同时优化:
    - 观测效率 (时间利用率)
    - 科学价值 (优先级加权)
    - 调度平滑性 (碎片最小化)

    使用Pareto优化方法找到最优解集
    """

    def __init__(self):
        """初始化多目标优化器"""
        self.objectives = {
            "efficiency": 0.4,      # 权重: 40%
            "scientific_value": 0.4,  # 权重: 40%
            "smoothness": 0.2       # 权重: 20%
        }

        # 内部状态
        self.best_schedule: List[Dict] = []
        self.best_score = 0.0

    def pareto_optimize(
        self,
        targets: List[Dict],
        constraints: Dict
    ) -> List[Dict]:
        """
        Pareto优化调度

        参数:
            targets: List[Dict] - 目标列表
            constraints: Dict - 约束条件

        返回:
            List[Dict] - Pareto最优调度方案
        """
        # 生成候选调度方案
        candidates = self._generate_candidates(targets, constraints)

        # 计算Pareto前沿
        pareto_front = self._compute_pareto_front(candidates)

        return pareto_front

    def optimize(
        self,
        targets: List[Dict],
        constraints: Dict,
        time_window: Tuple[datetime, datetime]
    ) -> List[Dict]:
        """
        优化调度

        参数:
            targets: List[Dict] - 目标列表
            constraints: Dict - 约束条件
            time_window: Tuple[datetime, datetime] - 时间窗口

        返回:
            List[Dict] - 最优调度方案
        """
        # 使用Pareto优化
        pareto_solutions = self.pareto_optimize(targets, constraints)

        if not pareto_solutions:
            return []

        # 选择最佳方案
        best = max(pareto_solutions, key=lambda c: self._evaluate_candidate(c)["total"])
        return best.get("schedule", [])

    def _generate_candidates(
        self,
        targets: List[Dict],
        constraints: Dict
    ) -> List[Dict]:
        """
        生成候选调度方案

        使用多种策略生成不同的调度方案

        参数:
            targets: List[Dict] - 目标列表
            constraints: Dict - 约束条件

        返回:
            List[Dict] - 候选方案列表
        """
        candidates = []

        # 策略1: 按优先级排序
        by_priority = sorted(targets, key=lambda t: t.get("priority", 0), reverse=True)
        candidates.append({"name": "priority", "schedule": by_priority})

        # 策略2: 按可见性窗口排序
        by_visibility = sorted(targets, key=lambda t: t.get("visibility_window", 0), reverse=True)
        candidates.append({"name": "visibility", "schedule": by_visibility})

        # 策略3: 按位置临近排序 (减少望远镜移动)
        by_position = self._sort_by_position(targets)
        candidates.append({"name": "position", "schedule": by_position})

        # 策略4: 混合策略
        mixed = self._mixed_strategy(targets)
        candidates.append({"name": "mixed", "schedule": mixed})

        return candidates

    def _sort_by_position(self, targets: List[Dict]) -> List[Dict]:
        """
        按位置临近排序

        减少望远镜的移动距离

        参数:
            targets: List[Dict] - 目标列表

        返回:
            List[Dict] - 排序后的目标列表
        """
        if not targets:
            return []

        sorted_targets = [targets[0]]  # 从第一个目标开始
        remaining = targets[1:]

        while remaining:
            last = sorted_targets[-1]
            last_ra = last.get("ra", 0)
            last_dec = last.get("dec", 0)

            # 找到距离最近的下一个目标
            nearest_idx = 0
            nearest_distance = float('inf')

            for i, target in enumerate(remaining):
                ra = target.get("ra", 0)
                dec = target.get("dec", 0)

                # 计算角距离
                distance = math.sqrt((ra - last_ra)**2 + (dec - last_dec)**2)

                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_idx = i

            sorted_targets.append(remaining.pop(nearest_idx))

        return sorted_targets

    def _mixed_strategy(self, targets: List[Dict]) -> List[Dict]:
        """
        混合策略

        综合考虑优先级、位置和观测时间

        参数:
            targets: List[Dict] - 目标列表

        返回:
            List[Dict] - 混合排序后的目标列表
        """
        if not targets:
            return []

        # 计算每个目标的综合评分
        scored = []
        for target in targets:
            priority = target.get("priority", 0.5)
            estimated_time = target.get("estimated_time", 60)

            # 综合评分
            score = priority * 0.5 + (estimated_time / 60.0) * 0.3

            # 位置评分 (假设平均分配)
            position_score = 0.2

            total_score = score + position_score
            scored.append((total_score, target))

        # 按评分排序
        scored.sort(key=lambda x: x[0], reverse=True)

        return [t for _, t in scored]

    def _compute_pareto_front(self, candidates: List[Dict]) -> List[Dict]:
        """
        计算Pareto前沿

        参数:
            candidates: List[Dict] - 候选方案列表

        返回:
            List[Dict] - Pareto最优解集
        """
        pareto: List[Dict] = []

        for candidate in candidates:
            scores = self._evaluate_candidate(candidate)
            is_dominated = False

            for other in pareto:
                if self._dominates(scores, self._evaluate_candidate(other)):
                    is_dominated = True
                    break

            if not is_dominated:
                # 移除被当前解支配的解
                pareto = [p for p in pareto
                         if not self._dominates(self._evaluate_candidate(p), scores)]
                pareto.append(candidate)

        return pareto

    def _evaluate_candidate(self, candidate: Dict) -> Dict[str, float]:
        """
        评估候选方案

        参数:
            candidate: Dict - 候选方案

        返回:
            Dict[str, float] - 各目标评分和总分
        """
        schedule = candidate.get("schedule", [])

        if not schedule:
            return {
                "efficiency": 0.0,
                "scientific_value": 0.0,
                "smoothness": 0.0,
                "total": 0.0
            }

        # 观测效率: 基于调度的时间利用率
        efficiency = min(len(schedule) / 10.0, 1.0)  # 假设最多10个目标

        # 科学价值: 基于优先级
        scientific_value = 0.0
        if schedule:
            priorities = [t.get("priority", 0.5) for t in schedule]
            scientific_value = sum(priorities) / len(priorities)

        # 平滑性: 简化为0.5 (实际应该基于碎片化分析)
        smoothness = 0.5

        # 加权总分
        total = (
            efficiency * self.objectives["efficiency"] +
            scientific_value * self.objectives["scientific_value"] +
            smoothness * self.objectives["smoothness"]
        )

        return {
            "efficiency": efficiency,
            "scientific_value": scientific_value,
            "smoothness": smoothness,
            "total": total
        }

    def _dominates(self, scores1: Dict[str, float], scores2: Dict[str, float]) -> bool:
        """
        判断scores1是否支配scores2

        一个解支配另一个解当且仅当它在所有目标上都不差，且至少在一个目标上更好

        参数:
            scores1: Dict[str, float] - 第一个解的评分
            scores2: Dict[str, float] - 第二个解的评分

        返回:
            bool - 如果scores1支配scores2返回True
        """
        better_count = 0

        for key in ["efficiency", "scientific_value", "smoothness"]:
            if scores1[key] > scores2[key]:
                better_count += 1
            elif scores1[key] < scores2[key]:
                return False

        return better_count > 0


# ============ 强化学习调度器主类 ============

class RLEnhancedScheduler:
    """
    强化学习增强型调度器

    结合DQN/PPO算法和传统调度算法，提供智能调度决策

    主要功能:
    - 状态管理: 跟踪望远镜位置、时间、目标状态
    - 动作选择: 使用DQN或PPO选择最优动作
    - 奖励计算: 根据调度效果计算奖励
    - 碎片化分析: 分析调度方案的碎片化程度
    - 多目标优化: 使用Pareto优化平衡多个目标

    属性:
        location: GeographicLocation - 观测站位置
        dqn_scheduler: DQNScheduler - DQN调度器
        ppo_scheduler: PPOScheduler - PPO调度器
        multi_optimizer: MultiObjectiveOptimizer - 多目标优化器
        fragmentation_analyzer: FragmentationAnalyzer - 碎片化分析器
    """

    def __init__(
        self,
        location: GeographicLocation,
        algorithm: str = "DQN"
    ):
        """
        初始化强化学习调度器

        参数:
            location: GeographicLocation - 观测站位置
            algorithm: str - 算法选择 ("DQN" 或 "PPO")
        """
        self.location = location
        self.algorithm = algorithm.upper()

        # 初始化增强调度器 (如果可用)
        if HAS_ENHANCED_SCHEDULER:
            self.enhanced_scheduler = EnhancedObservationScheduler(location)
        else:
            self.enhanced_scheduler = None

        # 初始化强化学习调度器
        if self.algorithm == "DQN":
            self.rl_scheduler = DQNScheduler(state_dim=16, action_dim=4)
        else:
            self.rl_scheduler = PPOScheduler()

        # 初始化多目标优化器
        self.multi_optimizer = MultiObjectiveOptimizer()

        # 初始化碎片化分析器
        self.fragmentation_analyzer = FragmentationAnalyzer() if HAS_ENHANCED_SCHEDULER else None

        # 内部状态
        self.current_state: Optional[SchedulerState] = None
        self.schedule_history: List[List[Dict]] = []

    def initialize_state(
        self,
        telescope_ra: float,
        telescope_dec: float,
        current_time: datetime,
        astronomical_night: Optional[Tuple[datetime, datetime]] = None
    ) -> SchedulerState:
        """
        初始化调度状态

        参数:
            telescope_ra: float - 望远镜当前赤经
            telescope_dec: float - 望远镜当前赤纬
            current_time: datetime - 当前时间
            astronomical_night: Optional[Tuple[datetime, datetime]] - 夜天文时间窗口

        返回:
            SchedulerState - 初始化后的状态
        """
        self.current_state = SchedulerState(
            telescope_ra=telescope_ra,
            telescope_dec=telescope_dec,
            current_time=current_time,
            astronomical_night_start=astronomical_night[0] if astronomical_night else None,
            astronomical_night_end=astronomical_night[1] if astronomical_night else None
        )

        return self.current_state

    def update_visible_targets(
        self,
        targets: List[ObservationTarget]
    ) -> List[Dict]:
        """
        更新可见目标列表

        参数:
            targets: List[ObservationTarget] - 目标列表

        返回:
            List[Dict] - 可见目标字典列表
        """
        if not self.current_state:
            raise ValueError("State not initialized. Call initialize_state first.")

        visible = []

        for target in targets:
            # 计算目标可见性
            if self.enhanced_scheduler:
                operable = self.enhanced_scheduler.compute_operable_periods(
                    target,
                    (
                        self.current_state.current_time,
                        self.current_state.current_time + timedelta(hours=12)
                    )
                )

                if operable:
                    visible.append({
                        "name": target.name,
                        "ra": target.ra,
                        "dec": target.dec,
                        "priority": target.priority / 5.0,  # 归一化到0-1
                        "estimated_time": 60,  # 默认60分钟
                        "window_start": operable[0].start,
                        "window_end": operable[0].end,
                        "observation_type": target.observation_type.value if hasattr(target, 'observation_type') else "imaging"
                    })
            else:
                # 简化处理
                visible.append({
                    "name": target.name,
                    "ra": target.ra,
                    "dec": target.dec,
                    "priority": target.priority / 5.0 if hasattr(target, 'priority') else 0.5,
                    "estimated_time": 60,
                    "window_start": self.current_state.current_time,
                    "window_end": self.current_state.current_time + timedelta(hours=4),
                    "observation_type": "imaging"
                })

        self.current_state.visible_targets = visible
        self.current_state.remaining_targets = [t for t in visible]

        return visible

    def select_next_target(self) -> Tuple[SchedulerAction, Optional[Dict]]:
        """
        选择下一个要观测的目标

        使用强化学习算法选择最优动作

        返回:
            Tuple[SchedulerAction, Optional[Dict]] - (选择的动作, 选择的目标)
        """
        if not self.current_state:
            raise ValueError("State not initialized. Call initialize_state first.")

        # 使用DQN或PPO选择动作
        if isinstance(self.rl_scheduler, DQNScheduler):
            action = self.rl_scheduler.choose_action(self.current_state)
        else:
            # PPO调度
            action_dict = self.rl_scheduler._policy(
                self.current_state.to_vector(),
                self.current_state.visible_targets
            )
            if action_dict["action"] == "select":
                action = SchedulerAction.SELECT_TARGET_NEXT
            else:
                action = SchedulerAction.FINISH_SCHEDULING

        selected_target = None

        if action == SchedulerAction.SELECT_TARGET_NEXT:
            # 选择最高优先级的可见目标
            if self.current_state.visible_targets:
                # 按优先级排序
                sorted_targets = sorted(
                    self.current_state.visible_targets,
                    key=lambda t: t.get("priority", 0),
                    reverse=True
                )
                selected_target = sorted_targets[0]

                # 从可见目标移到已调度
                self.current_state.visible_targets.remove(selected_target)
                self.current_state.scheduled_targets.append(selected_target)
                self.current_state.remaining_targets.remove(selected_target)

                # 更新望远镜位置
                self.current_state.telescope_ra = selected_target["ra"]
                self.current_state.telescope_dec = selected_target["dec"]

        elif action == SchedulerAction.FINISH_SCHEDULING:
            # 完成调度
            pass

        return action, selected_target

    def compute_reward(
        self,
        action: SchedulerAction,
        selected_target: Optional[Dict] = None
    ) -> float:
        """
        计算当前状态的奖励

        参数:
            action: SchedulerAction - 执行的动作
            selected_target: Optional[Dict] - 选择的目标

        返回:
            float - 奖励值
        """
        if not self.current_state:
            raise ValueError("State not initialized. Call initialize_state first.")

        return compute_reward(action, self.current_state, selected_target)

    def train_step(
        self,
        action: SchedulerAction,
        reward: float,
        next_state: SchedulerState,
        done: bool
    ):
        """
        执行一次训练步骤

        参数:
            action: SchedulerAction - 执行的动作
            reward: float - 获得的奖励
            next_state: SchedulerState - 下一个状态
            done: bool - 是否结束
        """
        if isinstance(self.rl_scheduler, DQNScheduler):
            # 存储经验
            self.rl_scheduler.remember(
                self.current_state,
                action,
                reward,
                next_state,
                done
            )

            # 训练
            td_error = self.rl_scheduler.train_step()

            return td_error

        return 0.0

    def analyze_fragmentation(
        self,
        scheduled_blocks: List[Tuple[datetime, datetime]],
        operable_periods: List[Tuple[datetime, datetime]]
    ) -> RLFragmentationMetrics:
        """
        分析调度碎片化

        参数:
            scheduled_blocks: List[Tuple[datetime, datetime]] - 已调度的时间块
            operable_periods: List[Tuple[datetime, datetime]] - 可操作时间段

        返回:
            RLFragmentationMetrics - 碎片化指标
        """
        return compute_fragmentation_metrics(operable_periods, scheduled_blocks)

    def generate_schedule(
        self,
        targets: List[ObservationTarget],
        period: Tuple[datetime, datetime],
        max_iterations: int = 100
    ) -> Dict[str, Any]:
        """
        生成调度计划

        使用强化学习算法生成优化的调度计划

        参数:
            targets: List[ObservationTarget] - 目标列表
            period: Tuple[datetime, datetime] - 时间段
            max_iterations: int - 最大迭代次数

        返回:
            Dict[str, Any] - 调度结果
        """
        # 初始化
        start_time, end_time = period
        self.initialize_state(
            telescope_ra=0,
            telescope_dec=0,
            current_time=start_time,
            astronomical_night=(start_time, end_time)
        )

        # 更新可见目标
        self.update_visible_targets(targets)

        # 调度历史
        schedule: List[Dict] = []

        # 迭代调度
        for iteration in range(max_iterations):
            if not self.current_state.visible_targets:
                break

            # 选择动作
            action, selected_target = self.select_next_target()

            if action == SchedulerAction.FINISH_SCHEDULING:
                break

            if selected_target:
                # 计算奖励
                reward = self.compute_reward(action, selected_target)

                # 添加到调度计划
                schedule.append({
                    "target": selected_target,
                    "action": action.value,
                    "reward": reward,
                    "iteration": iteration
                })

                # 更新状态
                self.current_state.current_time += timedelta(
                    minutes=selected_target.get("estimated_time", 60)
                )

        # 分析碎片化
        scheduled_blocks = [
            (datetime.fromisoformat(s["target"]["window_start"]),
             datetime.fromisoformat(s["target"]["window_end"]))
            for s in schedule
            if "window_start" in s["target"] and "window_end" in s["target"]
        ]

        fragmentation = self.analyze_fragmentation(
            scheduled_blocks,
            [(start_time, end_time)]
        )

        return {
            "schedule": schedule,
            "fragmentation": fragmentation.to_dict(),
            "total_reward": sum(s["reward"] for s in schedule),
            "n_targets_scheduled": len(schedule)
        }


# ============ 兼容性别名 ============

# 与enhanced_observation_scheduler兼容的别名
RLFragmentationAnalyzer = FragmentationAnalyzer if HAS_ENHANCED_SCHEDULER else None
RLSchedulerState = SchedulerState


# ============ 模拟数据测试 ============

def run_demo():
    """运行演示测试"""
    print("=" * 70)
    print("强化学习观测调度器 (RL-based Observation Scheduler)")
    print("=" * 70)

    # 创建观测位置（冷湖观测站）
    location = GeographicLocation(
        name="冷湖观测站",
        latitude=38.5,
        longitude=93.0,
        elevation=3200
    )
    print(f"\n观测位置: {location.name}")
    print(f"  纬度: {location.latitude}°")
    print(f"  经度: {location.longitude}°")
    print(f"  海拔: {location.elevation}m")

    # 创建强化学习调度器
    print("\n" + "-" * 70)
    print("1. 初始化强化学习调度器")
    print("-" * 70)

    # 测试DQN调度器
    dqn_scheduler = DQNScheduler(state_dim=16, action_dim=4)
    print(f"  DQN调度器初始化完成")
    print(f"    状态维度: {dqn_scheduler.state_dim}")
    print(f"    动作维度: {dqn_scheduler.action_dim}")
    print(f"    初始探索率: {dqn_scheduler.epsilon}")

    # 测试PPO调度器
    ppo_scheduler = PPOScheduler()
    print(f"\n  PPO调度器初始化完成")
    print(f"    Clip epsilon: {ppo_scheduler.clip_epsilon}")
    print(f"    Gamma: {ppo_scheduler.gamma}")

    # 2. 测试状态空间
    print("\n" + "-" * 70)
    print("2. 状态空间测试")
    print("-" * 70)

    state = SchedulerState(
        telescope_ra=180.0,
        telescope_dec=45.0,
        current_time=datetime(2026, 5, 1, 23, 0),
        astronomical_night_start=datetime(2026, 5, 1, 20, 0),
        astronomical_night_end=datetime(2026, 5, 2, 6, 0),
        visible_targets=[
            {"name": "M31", "ra": 10.68, "dec": 41.27, "priority": 0.9, "estimated_time": 60},
            {"name": "M42", "ra": 83.82, "dec": -5.39, "priority": 0.8, "estimated_time": 45},
            {"name": "M51", "ra": 202.47, "dec": 47.19, "priority": 0.6, "estimated_time": 90},
        ],
        scheduled_targets=[],
        remaining_targets=[],
        idle_hours=2.5,
        gap_count=3,
        scheduled_fraction=0.75
    )

    print(f"  状态信息:")
    print(f"    望远镜位置: RA={state.telescope_ra}°, DEC={state.telescope_dec}°")
    print(f"    可见目标数: {len(state.visible_targets)}")
    print(f"    已调度目标数: {len(state.scheduled_targets)}")
    print(f"    碎片数量: {state.gap_count}")
    print(f"    已调度比例: {state.scheduled_fraction:.2%}")
    print(f"  状态向量维度: {state.get_state_dim()}")
    print(f"  状态向量: {[f'{v:.3f}' for v in state.to_vector()[:8]]}...")

    # 3. 测试奖励函数
    print("\n" + "-" * 70)
    print("3. 奖励函数测试")
    print("-" * 70)

    # 测试选择目标奖励
    action1 = SchedulerAction.SELECT_TARGET_NEXT
    reward1 = compute_reward(action1, state, state.visible_targets[0])
    print(f"  选择最高优先级目标: reward = {reward1:.2f}")

    # 测试等待奖励
    action2 = SchedulerAction.WAIT_FOR_BETTER
    reward2 = compute_reward(action2, state, state.visible_targets[0])
    print(f"  等待更好的时机: reward = {reward2:.2f}")

    # 测试完成奖励
    action3 = SchedulerAction.FINISH_SCHEDULING
    reward3 = compute_reward(action3, state)
    print(f"  完成调度: reward = {reward3:.2f}")

    # 4. 测试DQN学习
    print("\n" + "-" * 70)
    print("4. DQN学习测试")
    print("-" * 70)

    # 模拟一些经验
    print("  模拟经验回放...")
    for i in range(10):
        next_state = SchedulerState(
            telescope_ra=random.uniform(0, 360),
            telescope_dec=random.uniform(-90, 90),
            current_time=state.current_time + timedelta(minutes=60),
            visible_targets=state.visible_targets[1:] if i < 3 else [],
            scheduled_targets=state.scheduled_targets + [state.visible_targets[0]] if i < 3 else state.scheduled_targets,
            gap_count=max(0, state.gap_count - 1),
            scheduled_fraction=min(1.0, state.scheduled_fraction + 0.1)
        )
        done = len(next_state.visible_targets) == 0

        dqn_scheduler.remember(
            state,
            SchedulerAction.SELECT_TARGET_NEXT,
            reward1,
            next_state,
            done
        )

    print(f"  记忆容量: {len(dqn_scheduler.memory)}")

    # 训练步骤
    td_error = dqn_scheduler.train_step()
    print(f"  训练TD误差: {td_error:.4f}")
    print(f"  探索率: {dqn_scheduler.epsilon:.4f}")

    # 选择动作测试
    chosen_action = dqn_scheduler.choose_action(state)
    print(f"  选择的动作: {chosen_action.value}")

    # 5. 测试碎片化分析
    print("\n" + "-" * 70)
    print("5. 碎片化分析测试")
    print("-" * 70)

    operable_periods = [
        (datetime(2026, 5, 1, 20, 0), datetime(2026, 5, 2, 6, 0))
    ]

    scheduled_blocks = [
        (datetime(2026, 5, 1, 21, 0), datetime(2026, 5, 1, 22, 30)),
        (datetime(2026, 5, 1, 23, 0), datetime(2026, 5, 2, 0, 30)),
        (datetime(2026, 5, 2, 2, 0), datetime(2026, 5, 2, 3, 30)),
    ]

    fragmentation = compute_fragmentation_metrics(operable_periods, scheduled_blocks)

    print(f"  空闲可操作时间: {fragmentation.idle_operable_hours:.2f} 小时")
    print(f"  间隙数量: {fragmentation.gap_count}")
    print(f"  间隙平均时长: {fragmentation.gap_mean_minutes:.1f} 分钟")
    print(f"  间隙中位数时长: {fragmentation.gap_median_minutes:.1f} 分钟")
    print(f"  间隙90分位时长: {fragmentation.gap_p90_minutes:.1f} 分钟")
    print(f"  已调度比例: {fragmentation.scheduled_fraction:.2%}")

    # 6. 测试多目标优化
    print("\n" + "-" * 70)
    print("6. 多目标优化测试")
    print("-" * 70)

    optimizer = MultiObjectiveOptimizer()

    targets = [
        {"name": "M31", "ra": 10.68, "dec": 41.27, "priority": 0.9, "estimated_time": 60},
        {"name": "M42", "ra": 83.82, "dec": -5.39, "priority": 0.8, "estimated_time": 45},
        {"name": "M51", "ra": 202.47, "dec": 47.19, "priority": 0.6, "estimated_time": 90},
        {"name": "织女星", "ra": 279.23, "dec": 38.78, "priority": 0.7, "estimated_time": 30},
    ]

    constraints = {"min_alt": 30.0}

    # Pareto优化
    pareto_solutions = optimizer.pareto_optimize(targets, constraints)

    print(f"  Pareto最优解数量: {len(pareto_solutions)}")
    for solution in pareto_solutions:
        scores = optimizer._evaluate_candidate(solution)
        print(f"    策略: {solution['name']}")
        print(f"      效率: {scores['efficiency']:.2f}")
        print(f"      科学价值: {scores['scientific_value']:.2f}")
        print(f"      平滑性: {scores['smoothness']:.2f}")
        print(f"      总分: {scores['total']:.2f}")

    # 7. 测试强化学习增强调度器
    print("\n" + "-" * 70)
    print("7. 强化学习增强调度器测试")
    print("-" * 70)

    rl_scheduler = RLEnhancedScheduler(location, algorithm="DQN")

    # 创建测试目标
    observation_targets = [
        ObservationTarget(
            name="M31 (仙女座星系)",
            ra=10.6847,
            dec=41.2687,
            observation_type=ObservationType.IMAGING,
            priority=5
        ),
        ObservationTarget(
            name="M42 (猎户座大星云)",
            ra=83.8221,
            dec=-5.3911,
            observation_type=ObservationType.IMAGING,
            priority=5
        ),
        ObservationTarget(
            name="M51 (漩涡星系)",
            ra=202.4696,
            dec=47.1953,
            observation_type=ObservationType.IMAGING,
            priority=3
        ),
        ObservationTarget(
            name="织女星",
            ra=279.2347,
            dec=38.7836,
            observation_type=ObservationType.PHOTOMETRY,
            priority=4
        ),
    ]

    # 生成调度计划
    period = (
        datetime(2026, 5, 1, 12, 0),
        datetime(2026, 5, 2, 12, 0)
    )

    schedule_result = rl_scheduler.generate_schedule(
        targets=observation_targets,
        period=period,
        max_iterations=20
    )

    print(f"  调度结果:")
    print(f"    调度目标数: {schedule_result['n_targets_scheduled']}")
    print(f"    总奖励: {schedule_result['total_reward']:.2f}")
    print(f"    碎片化指标:")
    for key, value in schedule_result['fragmentation'].items():
        print(f"      {key}: {value}")

    print(f"\n  调度详情:")
    for item in schedule_result['schedule'][:3]:
        target = item['target']
        print(f"    - {target['name']}: RA={target['ra']:.2f}, DEC={target['dec']:.2f}")
        print(f"      优先级: {target['priority']:.2f}, 奖励: {item['reward']:.2f}")

    # 8. 与增强调度器集成测试
    print("\n" + "-" * 70)
    print("8. 与增强调度器集成测试")
    print("-" * 70)

    if HAS_ENHANCED_SCHEDULER:
        print("  使用增强调度器计算夜天文时间...")

        enhanced_scheduler = EnhancedObservationScheduler(location)
        astronomical_windows = enhanced_scheduler.compute_astronomical_nights(period)

        print(f"  夜天文窗口数: {len(astronomical_windows)}")
        if astronomical_windows:
            window = astronomical_windows[0]
            print(f"  第一个窗口: {window.start} - {window.end}")
            print(f"    持续时间: {(window.end - window.start).total_seconds() / 3600:.2f} 小时")

        print("  增强调度器集成成功")
    else:
        print("  增强调度器不可用，跳过集成测试")

    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)

    return {
        "dqn_scheduler": dqn_scheduler,
        "ppo_scheduler": ppo_scheduler,
        "optimizer": optimizer,
        "rl_scheduler": rl_scheduler,
        "fragmentation": fragmentation,
        "schedule_result": schedule_result
    }


if __name__ == "__main__":
    run_demo()
