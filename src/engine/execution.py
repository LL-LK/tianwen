"""
执行引擎

负责任务执行、技能调度和结果收集。
"""

from typing import Optional, Dict, Any, List, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging


class ExecutionStatus(Enum):
    """执行状态枚举"""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ExecutionState:
    """执行状态"""
    status: ExecutionStatus = ExecutionStatus.IDLE
    current_step_index: Optional[int] = None
    current_step_name: Optional[str] = None
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    cancelled: bool = False


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    step_id: str = ""


class BaseSkill:
    """技能基类"""
    
    name: str = "base_skill"
    description: str = "Base skill"
    required_resources: List[str] = []
    
    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        """执行技能"""
        raise NotImplementedError


class SkillRegistry:
    """技能注册表"""
    
    def __init__(self):
        self._skills: Dict[str, Callable] = {}
        self._register_default_skills()
    
    def _register_default_skills(self):
        """注册默认技能"""
        self.register("validate_telescope", self._validate_telescope)
        self.register("locate_target", self._locate_target)
        self.register("set_camera_params", self._set_camera_params)
        self.register("capture_image", self._capture_image)
        self.register("save_data", self._save_data)
        self.register("load_data", self._load_data)
        self.register("process_data", self._process_data)
        self.register("analyze_data", self._analyze_data)
        self.register("generate_report", self._generate_report)
    
    def register(self, name: str, handler: Callable):
        """注册技能"""
        self._skills[name] = handler
    
    def get(self, name: str) -> Optional[Callable]:
        """获取技能"""
        return self._skills.get(name)
    
    def list_skills(self) -> List[str]:
        """列出所有技能"""
        return list(self._skills.keys())
    
    @staticmethod
    async def _validate_telescope(context: Dict) -> SkillResult:
        """验证望远镜状态"""
        await asyncio.sleep(1)
        return SkillResult(success=True, output={"status": "validated", "message": "望远镜状态正常"})
    
    @staticmethod
    async def _locate_target(context: Dict) -> SkillResult:
        """定位目标"""
        await asyncio.sleep(2)
        target = context.get("target_name", "未知目标")
        return SkillResult(success=True, output={"status": "located", "target": target})
    
    @staticmethod
    async def _set_camera_params(context: Dict) -> SkillResult:
        """设置相机参数"""
        await asyncio.sleep(1)
        return SkillResult(success=True, output={"status": "configured", "params": context.get("params", {})})
    
    @staticmethod
    async def _capture_image(context: Dict) -> SkillResult:
        """拍摄图像"""
        count = context.get("count", 1)
        await asyncio.sleep(5 * count)
        images = [f"image_{i}.fits" for i in range(count)]
        return SkillResult(success=True, output={"status": "captured", "images": images})
    
    @staticmethod
    async def _save_data(context: Dict) -> SkillResult:
        """保存数据"""
        await asyncio.sleep(1)
        return SkillResult(success=True, output={"status": "saved", "path": "/data/saved"})
    
    @staticmethod
    async def _load_data(context: Dict) -> SkillResult:
        """加载数据"""
        await asyncio.sleep(2)
        return SkillResult(success=True, output={"status": "loaded", "records": 100})
    
    @staticmethod
    async def _process_data(context: Dict) -> SkillResult:
        """处理数据"""
        await asyncio.sleep(3)
        return SkillResult(success=True, output={"status": "processed", "records": 100})
    
    @staticmethod
    async def _analyze_data(context: Dict) -> SkillResult:
        """分析数据"""
        await asyncio.sleep(4)
        return SkillResult(success=True, output={"status": "analyzed", "findings": []})
    
    @staticmethod
    async def _generate_report(context: Dict) -> SkillResult:
        """生成报告"""
        await asyncio.sleep(2)
        return SkillResult(success=True, output={"status": "generated", "report_path": "report.pdf"})


class ExecutionEngine:
    """执行引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger("execution-engine")
        self.state = ExecutionState()
        self.skill_registry = SkillRegistry()
        self._cancel_requested = False
        
        self.step_skill_mapping = {
            "验证设备状态": "validate_telescope",
            "定位目标": "locate_target",
            "定位目标天体": "locate_target",
            "设置相机参数": "set_camera_params",
            "设置拍摄参数": "set_camera_params",
            "执行图像拍摄": "capture_image",
            "执行拍摄": "capture_image",
            "保存原始数据": "save_data",
            "保存图像": "save_data",
            "保存数据": "save_data",
            "生成观测报告": "generate_report",
            "生成分析报告": "generate_report",
            "加载数据源": "load_data",
            "加载数据": "load_data",
            "数据预处理": "process_data",
            "预处理": "process_data",
            "特征提取": "process_data",
            "模式分析": "analyze_data",
            "分析计算": "analyze_data",
            "假说验证分析": "analyze_data",
            "结果可视化": "generate_report",
            "文献检索": "load_data",
            "收集实验证据": "capture_image",
            "收集学习样本": "load_data",
            "模型训练": "process_data",
            "效果评估": "analyze_data",
            "参数优化": "process_data",
            "撰写研究论文": "generate_report",
            "规划巡天区域": "load_data",
            "扫描目标天区": "capture_image",
            "目标检测识别": "analyze_data",
            "天体分类标注": "analyze_data",
            "生成天体地图": "generate_report",
        }
    
    def get_skill_for_step(self, step_name: str) -> Optional[str]:
        """获取步骤对应的技能"""
        return self.step_skill_mapping.get(step_name, step_name.lower().replace(" ", "_"))
    
    async def execute_plan(self, plan) -> Dict[str, Any]:
        """执行计划"""
        self.state = ExecutionState()
        self.state.status = ExecutionStatus.RUNNING
        self.state.started_at = datetime.now()
        self._cancel_requested = False
        
        results = []
        errors = []
        completed_steps: Set[str] = set()
        
        self.logger.info(f"Starting plan execution: {plan.title} ({len(plan.steps)} steps)")
        
        try:
            for idx, step in enumerate(plan.steps):
                if self._cancel_requested:
                    self.state.status = ExecutionStatus.CANCELLED
                    self.logger.info("Execution cancelled by user")
                    break
                
                self.state.current_step_index = idx
                self.state.current_step_name = step.name
                self.state.progress = (idx / len(plan.steps)) * 100
                
                self.logger.info(f"Executing step {idx + 1}/{len(plan.steps)}: {step.name}")
                
                start_time = datetime.now()
                
                try:
                    skill_name = self.get_skill_for_step(step.name)
                    context = {"plan": plan, "step": step, "completed_steps": completed_steps}
                    
                    result = await self._execute_skill(skill_name, context)
                    
                    step.status = "completed"
                    step.result = result.output if result.success else None
                    step.error = result.error if not result.success else None
                    step.actual_duration = (datetime.now() - start_time).total_seconds()
                    
                    results.append({
                        "step_id": step.id,
                        "step_name": step.name,
                        "status": "completed",
                        "duration": step.actual_duration,
                        "output": result.output
                    })
                    
                    completed_steps.add(step.name)
                    
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    
                    errors.append({
                        "step_id": step.id,
                        "step_name": step.name,
                        "error": str(e)
                    })
                    
                    self.logger.error(f"Step '{step.name}' failed: {e}")
                    break
            
            self.state.current_step_index = None
            self.state.current_step_name = None
            
            if errors:
                self.state.status = ExecutionStatus.FAILED
                self.state.error = f"{len(errors)} step(s) failed"
            elif not self._cancel_requested:
                self.state.status = ExecutionStatus.COMPLETED
            
            self.state.completed_at = datetime.now()
            self.state.progress = 100.0 if self.state.status == ExecutionStatus.COMPLETED else self.state.progress
            
            plan.status = self._map_status(self.state.status)
            if plan.started_at is None:
                plan.started_at = self.state.started_at
            plan.completed_at = self.state.completed_at
            plan.actual_total_duration = (plan.completed_at - plan.started_at).total_seconds() if plan.started_at else None
            
            return {
                "success": len(errors) == 0 and not self._cancel_requested,
                "plan_id": plan.id,
                "status": self.state.status.value,
                "progress": self.state.progress,
                "completed_steps": len(completed_steps),
                "total_steps": len(plan.steps),
                "results": results,
                "errors": errors,
                "cancelled": self._cancel_requested
            }
        
        except Exception as e:
            self.logger.error(f"Plan execution failed: {e}", exc_info=True)
            self.state.status = ExecutionStatus.FAILED
            self.state.error = str(e)
            return {
                "success": False,
                "plan_id": plan.id,
                "status": "FAILED",
                "error": str(e)
            }
    
    async def _execute_skill(self, skill_name: str, context: Dict) -> SkillResult:
        """执行技能"""
        start_time = datetime.now()
        
        skill = self.skill_registry.get(skill_name)
        if not skill:
            return SkillResult(
                success=False,
                error=f"Skill '{skill_name}' not found",
                execution_time=0.0
            )
        
        try:
            result = await skill(context)
            if isinstance(result, SkillResult):
                result.execution_time = (datetime.now() - start_time).total_seconds()
                return result
            else:
                return SkillResult(
                    success=True,
                    output=result,
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _map_status(self, exec_status: ExecutionStatus) -> str:
        """映射执行状态到计划状态"""
        mapping = {
            ExecutionStatus.COMPLETED: "completed",
            ExecutionStatus.FAILED: "failed",
            ExecutionStatus.CANCELLED: "cancelled",
            ExecutionStatus.PAUSED: "paused",
        }
        return mapping.get(exec_status, "unknown")
    
    def cancel(self):
        """请求取消执行"""
        self._cancel_requested = True
        self.logger.info("Cancellation requested")
    
    def pause(self):
        """暂停执行"""
        if self.state.status == ExecutionStatus.RUNNING:
            self.state.status = ExecutionStatus.PAUSED
            self.logger.info("Execution paused")
    
    def resume(self):
        """恢复执行"""
        if self.state.status == ExecutionStatus.PAUSED:
            self.state.status = ExecutionStatus.RUNNING
            self.logger.info("Execution resumed")
    
    def get_state(self) -> ExecutionState:
        """获取当前执行状态"""
        return self.state
    
    def register_skill(self, name: str, handler: Callable):
        """注册自定义技能"""
        self.skill_registry.register(name, handler)
        self.logger.info(f"Registered custom skill: {name}")
    
    def list_skills(self) -> List[str]:
        """列出所有可用技能"""
        return self.skill_registry.list_skills()