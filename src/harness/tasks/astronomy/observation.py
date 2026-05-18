"""
TianwenAGI Harness - 天文任务定义
天文领域专用任务：观测、分析、发现等
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import yaml
import json

from ..core.task import BaseTask, TaskConfig, TaskCategory, DifficultyLevel, TaskInstance
from ..registry import register_task


@register_task("transient_observation")
class TransientObservationTask(BaseTask):
    """瞬变源观测任务"""

    async def load_instances(self) -> List[TaskInstance]:
        """加载瞬变观测任务"""
        instances = [
            TaskInstance(
                task_id="tobs_001",
                config=self.config,
                prompt="""观测目标: AT2022lrq (ZTF22aa)
天文类型: 疑难瞬变源
观测要求:
1. 查询SIMBAD确定宿主星系
2. 查询NED获取红移
3. 查询TNS获取历史报告
4. 制定观测计划（曝光时间、滤光片）
5. 评估再亮可能性

请给出完整的观测计划。""",
                ground_truth={
                    "has_host": True,
                    "has_redshift": True,
                    "has_tns_report": True,
                    "reobservation_likely": True
                }
            ),
            TaskInstance(
                task_id="tobs_002",
                config=self.config,
                prompt="""快速响应任务: 探测到新的光学瞬变
目标名: OT J123456.7+012345
发现时间: 2024-01-15 20:30 UTC
发现亮度: r'=18.2 mag
请执行:
1. 立即查询SIMBAD确认是否为已知天体
2. 查询TNS确认是否为新发现
3. 评估是否为伪造/伪影
4. 如为真实瞬变，制定后续观测策略""",
                ground_truth={"is_real_transient": True}
            ),
        ]
        self._instances = instances
        return instances

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        """验证观测任务输出"""
        score = 0.0
        details = {}

        if isinstance(output, str):
            output_lower = output.lower()
            # 检查关键要素
            if "simbad" in output_lower or "host" in output_lower:
                score += 0.2
                details["has_simbad_query"] = True
            if "ned" in output_lower or "redshift" in output_lower:
                score += 0.2
                details["has_ned_query"] = True
            if "tns" in output_lower or "report" in output_lower:
                score += 0.2
                details["has_tns_query"] = True
            if "observation" in output_lower or "plan" in output_lower:
                score += 0.2
                details["has_plan"] = True
            if "conclusion" in output_lower or "result" in output_lower:
                score += 0.2
                details["has_conclusion"] = True

        return {"accuracy": score, "details": details}


@register_task("spectral_analysis")
class SpectralAnalysisTask(BaseTask):
    """光谱分析任务"""

    async def load_instances(self) -> List[TaskInstance]:
        instances = [
            TaskInstance(
                task_id="spec_001",
                config=self.config,
                prompt="""分析以下光谱数据，识别天体类型:
光谱范围: 4000-7000 Angstrom
主要特征:
- H-alpha 发射线 (6563 Å)
- H-beta 发射线 (4861 Å)
- [OIII] 5007 Å 发射线
- 宽发射线特征

请判断:
1. 是否为发射线星系?
2. 如果是，确定其类型(Starburst/Seyfert/LINER等)
3. 估算红移
4. 给出置信度""",
                ground_truth={
                    "type": "emission_line_galaxy",
                    "subtype": "seyfert_2",
                    "has_redshift": True
                }
            ),
        ]
        self._instances = instances
        return instances

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        score = 0.0
        if isinstance(output, str):
            output_lower = output.lower()
            if ground_truth.get("type") in output_lower:
                score += 0.5
            if "redshift" in output_lower or "z =" in output_lower:
                score += 0.3
            if ground_truth.get("subtype", "") in output_lower:
                score += 0.2
        return {"accuracy": score}


@register_task("catalog_query")
class CatalogQueryTask(BaseTask):
    """星表查询任务"""

    async def load_instances(self) -> List[TaskInstance]:
        instances = [
            TaskInstance(
                task_id="catq_001",
                config=self.config,
                prompt="""查询目标: M31 (仙女座星系)
请执行以下星表查询:
1. SIMBAD: 获取M31的基本信息（类型、距离、坐标）
2. NED: 获取M31的精确红移和距离模数
3. VizieR: 查询2MASS图像
4. 汇总所有结果""",
                ground_truth={"known_object": True, "distance_known": True}
            ),
            TaskInstance(
                task_id="catq_002",
                config=self.config,
                prompt="""未知天体识别任务:
目标名: PSN J12345678+01234567
发现时间: 2024-03-10
发现亮度: g'=19.8 mag

请执行:
1. SIMBAD查询确认是否为已知天体
2. 如果未知，查询TNS确认是否为新发现
3. 评估是否需要触发后续观测""",
                ground_truth={"is_known": False, "is_new": True}
            ),
        ]
        self._instances = instances
        return instances

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        return {"accuracy": 1.0 if ground_truth.get("distance_known") else 0.0}


@register_task("real_bogus")
class RealBogusTask(BaseTask):
    """Real-Bogus分类任务"""

    async def load_instances(self) -> List[TaskInstance]:
        instances = [
            TaskInstance(
                task_id="rb_001",
                config=self.config,
                prompt="""Real-Bogus分类任务:
候选体: ZTF22aahfuqm
图像特征:
- PSF fit: 0.5 arcsec
- FWHM: 2.1 arcsec
- Elongation: 1.2
- 偏移: 0.3 arcsec from host
- Motion: None detected (upper limit 0.2 mas/yr)
- ML score: 0.73

请判断: Real (真实变源) 还是 Bogus (伪影/人造)?""",
                ground_truth={"classification": "Real", "confidence": 0.85}
            ),
        ]
        self._instances = instances
        return instances

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        score = 0.0
        if isinstance(output, str):
            output_lower = output.lower()
            expected = ground_truth.get("classification", "").lower()
            if expected in output_lower:
                score = ground_truth.get("confidence", 0.5)
        return {"accuracy": score}


@register_task("observation_planning")
class ObservationPlanningTask(BaseTask):
    """观测计划任务"""

    async def load_instances(self) -> List[TaskInstance]:
        instances = [
            TaskInstance(
                task_id="oplan_001",
                config=self.config,
                prompt="""为以下目标制定观测计划:
目标: Kepler-186f (系外行星)
观测窗口: 2024-06-01 至 2024-06-30
望远镜: 0.5m 光学望远镜
可用滤光片: B, V, R, I
 moonlight: 需要避开

请制定:
1. 目标坐标和最佳观测时间
2. 曝光时间和帧数
3. 滤光片选择
4. 预计信噪比
5. 备选目标(如果有)""",
                ground_truth={"has_coordinates": True, "has_exposure": True}
            ),
        ]
        self._instances = instances
        return instances

    async def validate(self, output: Any, ground_truth: Any) -> Dict[str, float]:
        score = 0.0
        if isinstance(output, str):
            output_lower = output.lower()
            if ground_truth.get("has_coordinates") and ("coord" in output_lower or "ra" in output_lower):
                score += 0.3
            if ground_truth.get("has_exposure") and ("expos" in output_lower or "time" in output_lower):
                score += 0.3
            if "filter" in output_lower:
                score += 0.2
            if "snr" in output_lower or "signal" in output_lower:
                score += 0.2
        return {"accuracy": score}
