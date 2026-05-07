"""
执行引擎 - 负责任务执行、技能调度和结果收集
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from ..utils.logger import get_logger
from .planning import ExecutionPlan, PlanStep


class ExecutionStatus(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ExecutionState:
    status: ExecutionStatus = ExecutionStatus.IDLE
    current_step: Optional[int] = None
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ExecutionEngine:
    """执行引擎"""
    
    def __init__(self):
        self.logger = get_logger("execution-engine")
        self.state = ExecutionState()
        
        self.skills = {
            "validate_telescope": self._skill_validate_telescope,
            "locate_target": self._skill_locate_target,
            "set_camera_params": self._skill_set_camera_params,
            "capture_image": self._skill_capture_image,
            "save_data": self._skill_save_data,
            "load_data": self._skill_load_data,
            "process_data": self._skill_process_data,
            "analyze_data": self._skill_analyze_data,
            "generate_report": self._skill_generate_report,
        }
    
    async def execute_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        self.state.status = ExecutionStatus.RUNNING
        self.state.started_at = datetime.now()
        
        results = []
        errors = []
        
        self.logger.info(f"Starting plan execution: {plan.id}")
        
        try:
            for idx, step in enumerate(plan.steps):
                self.state.current_step = idx
                self.state.progress = (idx + 1) / len(plan.steps) * 100
                
                self.logger.info(f"Executing step {idx + 1}/{len(plan.steps)}: {step.name}")
                
                try:
                    result = await self._execute_step(step)
                    results.append({
                        "step_id": step.id,
                        "name": step.name,
                        "status": "completed",
                        "result": result
                    })
                except Exception as e:
                    errors.append({
                        "step_id": step.id,
                        "name": step.name,
                        "error": str(e)
                    })
                    self.logger.error(f"Step {step.name} failed: {e}")
                    break
            
            if errors:
                self.state.status = ExecutionStatus.FAILED
                self.state.error = f"Execution failed: {len(errors)} errors"
                return {
                    "success": False,
                    "plan_id": plan.id,
                    "errors": errors,
                    "results": results
                }
            else:
                self.state.status = ExecutionStatus.COMPLETED
                return {
                    "success": True,
                    "plan_id": plan.id,
                    "results": results
                }
        
        finally:
            self.state.completed_at = datetime.now()
    
    async def _execute_step(self, step: PlanStep) -> Any:
        skill_name = self._map_step_to_skill(step.name)
        
        if skill_name in self.skills:
            return await self.skills[skill_name](step)
        else:
            return {"message": f"Step '{step.name}' executed"}
    
    def _map_step_to_skill(self, step_name: str) -> str:
        mapping = {
            "验证设备状态": "validate_telescope",
            "定位目标": "locate_target",
            "设置拍摄参数": "set_camera_params",
            "执行拍摄": "capture_image",
            "保存图像": "save_data",
            "保存数据": "save_data",
            "加载数据": "load_data",
            "预处理": "process_data",
            "特征提取": "process_data",
            "分析计算": "analyze_data",
            "生成报告": "generate_report",
        }
        return mapping.get(step_name, step_name.lower().replace(" ", "_"))
    
    async def _skill_validate_telescope(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(1)
        return {"status": "validated", "message": "望远镜设备状态正常"}
    
    async def _skill_locate_target(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(2)
        return {"status": "located", "message": "目标定位完成"}
    
    async def _skill_set_camera_params(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(1)
        return {"status": "configured", "message": "相机参数设置完成"}
    
    async def _skill_capture_image(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(5)
        return {"status": "captured", "images": ["image_001.fits"]}
    
    async def _skill_save_data(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(1)
        return {"status": "saved", "message": "数据保存完成"}
    
    async def _skill_load_data(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(2)
        return {"status": "loaded", "message": "数据加载完成"}
    
    async def _skill_process_data(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(3)
        return {"status": "processed", "message": "数据处理完成"}
    
    async def _skill_analyze_data(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(4)
        return {"status": "analyzed", "message": "数据分析完成"}
    
    async def _skill_generate_report(self, step: PlanStep) -> Dict[str, Any]:
        await asyncio.sleep(2)
        return {"status": "generated", "report_path": "report.pdf"}