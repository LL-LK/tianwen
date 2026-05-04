"""
embodied_observation_workflow.py - 具身观测工作流

整合天问-AGI的观测闭环模块，实现具身智能天文观测：

组件:
- AstroPipeline: 天体检测 (Stage I/II/III)
- SeestarMCPClient: MCP协议望远镜控制
- EnhancedObservationScheduler: 观测调度
- CycleStatisticsDashboard: 统计面板

参考:
- seestar-mcp: https://github.com/taco-ops/seestar-mcp
- NIGHTWATCH: https://github.com/THOClabs/NIGHTWATCH
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum
import asyncio


class WorkflowStage(Enum):
    """工作流阶段枚举

    定义具身观测工作流的完整生命周期中的各个阶段。
    """
    IMAGE_INPUT = "image_input"              # 图像输入阶段
    DETECTION = "detection"                  # 天体检测阶段
    TARGET_SELECTION = "target_selection"    # 目标选择阶段
    SCHEDULING = "scheduling"                # 观测调度阶段
    TELESCOPE_CONTROL = "telescope_control"   # 望远镜控制阶段
    IMAGING = "imaging"                      # 成像采集阶段
    DATA_RETURN = "data_return"              # 数据回传阶段
    LOOP_OPTIMIZATION = "loop_optimization"   # 循环优化阶段


@dataclass
class WorkflowResult:
    """工作流执行结果数据类

    记录完整观测闭环的执行结果，包括各阶段完成状态、
    检测到的目标、选中的目标、望远镜指令、成像数据等。

    属性:
        success: 工作流是否成功完成
        stages_completed: 已完成的阶段列表
        detected_targets: 检测到的天体目标列表
        selected_target: 被选中的观测目标
        telescope_commands: 发送的望远镜命令列表
        imaging_data: 成像数据列表
        loop_iterations: 循环优化迭代次数
        execution_time_seconds: 总执行时间（秒）
        error_message: 错误信息（如有）
    """
    success: bool = False
    stages_completed: List[WorkflowStage] = field(default_factory=list)
    detected_targets: List[Dict[str, Any]] = field(default_factory=list)
    selected_target: Optional[Dict[str, Any]] = None
    telescope_commands: List[str] = field(default_factory=list)
    imaging_data: List[Dict[str, Any]] = field(default_factory=list)
    loop_iterations: int = 0
    execution_time_seconds: float = 0.0
    error_message: Optional[str] = None


class EmbodiedObservationWorkflow:
    """
    具身观测工作流类

    整合所有观测闭环组件，实现全自动天文观测流程。
    支持从图像输入到望远镜控制的端到端具身观测。

    组件依赖:
        - astro_pipeline: 天体检测Pipeline
        - telescope_client: Seestar MCP望远镜控制客户端
        - scheduler: 增强型观测调度器
        - stats_dashboard: 循环统计面板

    使用示例:
        workflow = EmbodiedObservationWorkflow()
        await workflow.initialize()
        result = await workflow.run_full_observation_cycle(image_input)
    """

    def __init__(self):
        """初始化具身观测工作流"""
        # 组件初始化 - 各组件将在initialize()中延迟加载
        self.astro_pipeline: Optional[Any] = None
        self.telescope_client: Optional[Any] = None
        self.scheduler: Optional[Any] = None
        self.stats_dashboard: Optional[Any] = None

        # 工作流配置参数
        self.config: Dict[str, Any] = {
            "min_detection_confidence": 0.7,    # 最小检测置信度阈值
            "max_loop_iterations": 5,            # 最大循环迭代次数
            "imaging_exposure": 60,              # 单次曝光时间（秒）
            "imaging_count": 3,                  # 曝光帧数
            "simulation_mode": True,             # 模拟模式（用于测试）
            "auto_loop_optimization": True       # 自动循环优化开关
        }

        # 工作流状态标志
        self.is_running: bool = False

        # 已完成阶段的历史记录
        self.stage_history: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """初始化所有组件

        异步初始化工作流所需的各个组件，包括：
        - AstroPipeline: 天体检测Pipeline
        - SeestarMCPClient: 望远镜控制客户端
        - EnhancedObservationScheduler: 观测调度器
        - CycleStatisticsDashboard: 统计面板

        注意:
            如果某个组件导入失败，会记录警告但继续运行，
            该组件功能将被跳过。
        """
        # 初始化astro_pipeline
        try:
            from astro_pipeline import AstroPipeline
            self.astro_pipeline = AstroPipeline()
        except ImportError as e:
            print(f"[警告] AstroPipeline导入失败: {e}")
            self.astro_pipeline = None

        # 初始化telescope_client
        try:
            from seestar_mcp_client import SeestarMCPClient
            self.telescope_client = SeestarMCPClient()
            await self.telescope_client.connect()
        except ImportError as e:
            print(f"[警告] SeestarMCPClient导入失败: {e}")
            self.telescope_client = None
        except Exception as e:
            print(f"[警告] 望远镜连接失败: {e}")
            self.telescope_client = None

        # 初始化scheduler
        try:
            from enhanced_observation_scheduler import EnhancedObservationScheduler
            self.scheduler = EnhancedObservationScheduler()
        except ImportError as e:
            print(f"[警告] EnhancedObservationScheduler导入失败: {e}")
            self.scheduler = None

        # 初始化stats_dashboard
        try:
            from src.web.dashboard import CycleStatisticsDashboard
            self.stats_dashboard = CycleStatisticsDashboard()
        except ImportError as e:
            print(f"[警告] CycleStatisticsDashboard导入失败: {e}")
            self.stats_dashboard = None

    async def run_full_observation_cycle(
        self,
        image_input: Any,  # 图像路径或Base64
        observation_targets: Optional[List[str]] = None
    ) -> WorkflowResult:
        """
        运行完整观测闭环

        执行从图像输入到数据回传的全流程具身观测，
        包括天体检测、目标选择、望远镜控制、成像采集
        和循环优化等阶段。

        Args:
            image_input: 图像输入，可以是图像文件路径或Base64编码的图像数据
            observation_targets: 可选的观测目标列表，用于优先选择特定目标

        Returns:
            WorkflowResult: 包含完整执行结果的工作流结果对象

        工作流阶段:
            1. IMAGE_INPUT - 接收并解析图像输入
            2. DETECTION - 使用AstroPipeline进行天体检测
            3. TARGET_SELECTION - 根据优先级选择最佳观测目标
            4. SCHEDULING - 创建观测计划
            5. TELESCOPE_CONTROL - 控制望远镜指向目标
            6. IMAGING - 执行目标成像
            7. DATA_RETURN - 数据回传
            8. LOOP_OPTIMIZATION - 循环优化
        """
        start_time: datetime = datetime.now()
        result: WorkflowResult = WorkflowResult()

        try:
            self.is_running = True
            self.stage_history = []

            # ========== 阶段1: 图像输入 ==========
            result.stages_completed.append(WorkflowStage.IMAGE_INPUT)
            self._record_stage(WorkflowStage.IMAGE_INPUT, {"status": "completed"})

            # ========== 阶段2: 天体检测 (AstroPipeline) ==========
            if self.astro_pipeline:
                detection_result = await self.astro_pipeline.analyze(image_input)
                result.detected_targets = detection_result.get("sources", [])
                result.stages_completed.append(WorkflowStage.DETECTION)
                self._record_stage(WorkflowStage.DETECTION, {
                    "status": "completed",
                    "sources_found": len(result.detected_targets)
                })
            else:
                # 模拟模式：生成虚拟检测结果
                if self.config.get("simulation_mode", False):
                    result.detected_targets = self._generate_simulated_targets()
                    result.stages_completed.append(WorkflowStage.DETECTION)
                    self._record_stage(WorkflowStage.DETECTION, {
                        "status": "completed",
                        "simulation": True,
                        "sources_found": len(result.detected_targets)
                    })
                else:
                    result.error_message = "AstroPipeline not initialized"
                    return result

            # ========== 阶段3: 目标选择 ==========
            selected = await self._select_best_target(
                result.detected_targets,
                observation_targets
            )
            if not selected:
                result.error_message = "No suitable target found"
                return result

            result.selected_target = selected
            result.stages_completed.append(WorkflowStage.TARGET_SELECTION)
            self._record_stage(WorkflowStage.TARGET_SELECTION, {
                "status": "completed",
                "selected_target": selected.get("name", "unknown")
            })

            # ========== 阶段4: 观测调度 ==========
            if self.scheduler:
                schedule_result = await self._create_observation_schedule(selected)
                result.stages_completed.append(WorkflowStage.SCHEDULING)
                self._record_stage(WorkflowStage.SCHEDULING, {
                    "status": "completed",
                    "schedule": schedule_result
                })

            # ========== 阶段5: 望远镜控制 (Seestar MCP) ==========
            if self.telescope_client:
                goto_success = await self.telescope_client.goto_target(selected)
                if goto_success:
                    cmd = f"GOTO {selected.get('name', 'unknown')}"
                    result.telescope_commands.append(cmd)
                    result.stages_completed.append(WorkflowStage.TELESCOPE_CONTROL)
                    self._record_stage(WorkflowStage.TELESCOPE_CONTROL, {
                        "status": "completed",
                        "command": cmd
                    })
                else:
                    result.error_message = "Telescope goto failed"
                    return result
            else:
                # 模拟模式：模拟望远镜控制
                if self.config.get("simulation_mode", False):
                    cmd = f"GOTO {selected.get('name', 'unknown')}"
                    result.telescope_commands.append(cmd)
                    result.stages_completed.append(WorkflowStage.TELESCOPE_CONTROL)
                    self._record_stage(WorkflowStage.TELESCOPE_CONTROL, {
                        "status": "completed",
                        "simulation": True,
                        "command": cmd
                    })

            # ========== 阶段6: 成像 ==========
            imaging_result = await self._execute_imaging()
            result.imaging_data = imaging_result
            result.stages_completed.append(WorkflowStage.IMAGING)
            self._record_stage(WorkflowStage.IMAGING, {
                "status": "completed",
                "frames_captured": len(imaging_result)
            })

            # ========== 阶段7: 数据回传 ==========
            result.stages_completed.append(WorkflowStage.DATA_RETURN)
            self._record_stage(WorkflowStage.DATA_RETURN, {
                "status": "completed",
                "data_size": len(imaging_result)
            })

            # ========== 阶段8: 循环优化 ==========
            result.loop_iterations = await self._loop_optimization(
                result.detected_targets,
                result.imaging_data
            )
            result.stages_completed.append(WorkflowStage.LOOP_OPTIMIZATION)
            self._record_stage(WorkflowStage.LOOP_OPTIMIZATION, {
                "status": "completed",
                "iterations": result.loop_iterations
            })

            # 成功完成
            result.success = True

        except Exception as e:
            result.error_message = str(e)
            self._record_stage(None, {"status": "error", "message": str(e)})

        finally:
            self.is_running = False
            result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _record_stage(self, stage: Optional[WorkflowStage], data: Dict[str, Any]) -> None:
        """记录阶段执行历史

        Args:
            stage: 工作流阶段
            data: 阶段执行数据
        """
        self.stage_history.append({
            "stage": stage.value if stage else "unknown",
            "timestamp": datetime.now().isoformat(),
            **data
        })

    def _generate_simulated_targets(self) -> List[Dict[str, Any]]:
        """生成模拟天体目标

        在模拟模式下用于生成虚拟的天体检测结果，
        便于测试工作流流程。

        Returns:
            List[Dict]: 模拟的天体目标列表
        """
        return [
            {
                "name": "M31",
                "type": "GALAXY",
                "flux": 0.95,
                "ra": 10.6847,
                "dec": 41.2687,
                "magnitude": 3.4
            },
            {
                "name": "NGC 224",
                "type": "GALAXY",
                "flux": 0.88,
                "ra": 10.6847,
                "dec": 41.2687,
                "magnitude": 4.2
            },
            {
                "name": "M42",
                "type": "NEBULA",
                "flux": 0.82,
                "ra": 83.8221,
                "dec": -5.3911,
                "magnitude": 4.0
            },
            {
                "name": "M51",
                "type": "GALAXY",
                "flux": 0.75,
                "ra": 202.4696,
                "dec": 47.1953,
                "magnitude": 8.4
            },
            {
                "name": "QSO_1234",
                "type": "QSO",
                "flux": 0.71,
                "ra": 185.7275,
                "dec": 5.5643,
                "magnitude": 16.2
            }
        ]

    async def _select_best_target(
        self,
        detected_targets: List[Dict[str, Any]],
        observation_targets: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        选择最佳目标

        根据检测结果和配置优先级选择最佳观测目标。
        优先选择高置信度、高价值的天体（星系 > 类星体 > 星云 > 恒星）。

        Args:
            detected_targets: 检测到的天体列表
            observation_targets: 可选的指定目标列表

        Returns:
            Optional[Dict]: 最佳目标，如果无合适目标则返回None
        """
        if not detected_targets:
            return None

        # 过滤低置信度目标
        min_confidence: float = self.config["min_detection_confidence"]
        high_confidence: List[Dict[str, Any]] = [
            t for t in detected_targets
            if t.get("flux", 0) >= min_confidence
        ]

        if not high_confidence:
            return None

        # 如果有指定目标，优先选择匹配的目标
        if observation_targets:
            for target_name in observation_targets:
                for target in high_confidence:
                    if target.get("name") == target_name:
                        return target

        # 按天体类型优先级选择
        # 优先级: GALAXY > QSO > NEBULA > STAR
        type_priority: Dict[str, int] = {
            "GALAXY": 4,
            "QSO": 3,
            "NEBULA": 2,
            "STAR": 1
        }

        # 按类型优先级和置信度排序
        def target_score(t: Dict[str, Any]) -> tuple:
            type_score: int = type_priority.get(t.get("type", "STAR"), 0)
            flux_score: float = t.get("flux", 0)
            return (type_score, flux_score)

        sorted_targets: List[Dict[str, Any]] = sorted(
            high_confidence,
            key=target_score,
            reverse=True
        )

        return sorted_targets[0] if sorted_targets else None

    async def _create_observation_schedule(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建观测计划

        根据目标特性计算最佳观测时间和曝光参数。

        Args:
            target: 选中的观测目标

        Returns:
            Dict: 包含计划时间和优先级的字典
        """
        if not self.scheduler:
            return {"status": "skipped"}

        # 简化的调度计算
        # 实际应该考虑目标高度、大气透明度、月相等因素
        return {
            "scheduled_time": datetime.now() + timedelta(minutes=5),
            "priority": target.get("priority", 0.5),
            "exposure_time": self.config["imaging_exposure"],
            "frame_count": self.config["imaging_count"],
            "filter": "L"  #  luminance滤镜
        }

    async def _execute_imaging(self) -> List[Dict[str, Any]]:
        """
        执行成像

        控制望远镜执行多次曝光成像。

        Returns:
            List[Dict]: 每次曝光的结果列表
        """
        if not self.telescope_client:
            # 模拟模式
            if self.config.get("simulation_mode", False):
                return await self._simulate_imaging()
            return []

        imaging_results: List[Dict[str, Any]] = []
        exposure_time: int = self.config["imaging_exposure"]
        imaging_count: int = self.config["imaging_count"]

        for i in range(imaging_count):
            success: bool = await self.telescope_client.start_imaging(
                exposure_time=exposure_time,
                filter_name="L",
                count=1
            )

            imaging_results.append({
                "frame": i + 1,
                "success": success,
                "timestamp": datetime.now().isoformat(),
                "exposure": exposure_time,
                "filter": "L"
            })

            # 帧间间隔（除最后一帧外）
            if i < imaging_count - 1:
                await asyncio.sleep(exposure_time)

        return imaging_results

    async def _simulate_imaging(self) -> List[Dict[str, Any]]:
        """
        模拟成像过程

        在模拟模式下生成虚拟的成像结果。

        Returns:
            List[Dict]: 模拟的成像数据列表
        """
        imaging_results: List[Dict[str, Any]] = []
        imaging_count: int = self.config["imaging_count"]
        exposure_time: int = self.config["imaging_exposure"]

        for i in range(imaging_count):
            imaging_results.append({
                "frame": i + 1,
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "exposure": exposure_time,
                "filter": "L",
                "simulation": True,
                "file_path": f"/simulated_data/frame_{i+1}.fits"
            })

            # 模拟曝光间隔
            await asyncio.sleep(1)  # 模拟1秒处理时间

        return imaging_results

    async def _loop_optimization(
        self,
        detected: List[Dict[str, Any]],
        imaging_data: List[Dict[str, Any]]
    ) -> int:
        """
        循环优化

        根据检测结果和成像数据优化观测参数，
        可能触发新一轮观测循环。

        Args:
            detected: 检测到的目标列表
            imaging_data: 已完成的成像数据

        Returns:
            int: 执行的迭代次数
        """
        iterations: int = 0

        if not self.config.get("auto_loop_optimization", False):
            return iterations

        if self.stats_dashboard:
            # 更新统计面板
            self.stats_dashboard.record_stage_result(
                "image_detection",
                len(detected) > 0,
                len(detected) * 0.1  # 模拟处理时间
            )
            self.stats_dashboard.record_stage_result(
                "imaging",
                all(d.get("success", False) for d in imaging_data),
                len(imaging_data) * self.config["imaging_exposure"] * 0.1
            )

        # 简化的循环优化逻辑
        # 实际应该基于以下因素决定是否继续循环：
        # - 信噪比是否达标
        # - 目标是否仍在视场中
        # - 望远镜指向是否需要修正

        return iterations

    async def emergency_stop(self) -> None:
        """
        紧急停止

        在发生异常时安全停止所有观测活动，
        包括停止成像、归位望远镜等操作。
        """
        if self.telescope_client:
            try:
                await self.telescope_client.safe_shutdown()
            except Exception as e:
                print(f"[警告] 望远镜安全关闭失败: {e}")
        self.is_running = False

    def get_workflow_status(self) -> Dict[str, Any]:
        """
        获取工作流状态

        返回当前工作流的运行状态和组件初始化情况。

        Returns:
            Dict: 包含is_running、components和config的状态字典
        """
        return {
            "is_running": self.is_running,
            "components": {
                "astro_pipeline": self.astro_pipeline is not None,
                "telescope_client": self.telescope_client is not None,
                "scheduler": self.scheduler is not None,
                "stats_dashboard": self.stats_dashboard is not None
            },
            "config": self.config,
            "stage_history": self.stage_history
        }

    def get_stage_history(self) -> List[Dict[str, Any]]:
        """
        获取阶段执行历史

        Returns:
            List[Dict]: 各阶段执行的详细历史记录
        """
        return self.stage_history

    async def run_batch_observations(
        self,
        image_inputs: List[Any],
        observation_targets: Optional[List[str]] = None
    ) -> List[WorkflowResult]:
        """
        批量运行观测

        顺序执行多个图像的观测流程。

        Args:
            image_inputs: 图像输入列表
            observation_targets: 可选的观测目标列表

        Returns:
            List[WorkflowResult]: 每个图像的观测结果列表
        """
        results: List[WorkflowResult] = []

        for image_input in image_inputs:
            result: WorkflowResult = await self.run_full_observation_cycle(
                image_input,
                observation_targets
            )
            results.append(result)

            # 如果某次观测失败，是否继续
            # 目前设计为继续执行下一帧

        return results

    def __repr__(self) -> str:
        """工作流对象的字符串表示"""
        component_status = ", ".join([
            f"{k}: {v}" for k, v in self.get_workflow_status()["components"].items()
        ])
        return f"EmbodiedObservationWorkflow({component_status})"
