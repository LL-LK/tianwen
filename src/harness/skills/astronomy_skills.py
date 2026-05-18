"""
TianwenAGI Harness - Astronomy Skills
天文领域专用技能实现
包括：光谱分析、观测计划、星表查询、瞬变检测
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import logging
import asyncio
import time
import json

from .base import BaseSkill, SkillConfig, SkillResult, SkillType
from .registry import register_skill

logger = logging.getLogger("harness.skills.astronomy")


@register_skill("spectral_analysis", SkillType.SPECTRAL_ANALYSIS)
class SpectralAnalysisSkill(BaseSkill):
    """
    光谱分析技能
    处理天体光谱数据，进行谱线识别、红移测量等分析
    """

    def __init__(self, config: SkillConfig = None):
        if config is None:
            config = SkillConfig(
                name="spectral_analysis",
                skill_type=SkillType.SPECTRAL_ANALYSIS,
                description="Analyze astronomical spectra for spectral lines, redshift, and stellar properties"
            )
        super().__init__(config)
        self.spectral_lines = config.get_param("spectral_lines", {
            "H-alpha": 656.28,
            "H-beta": 486.13,
            "H-gamma": 434.05,
            "Mg II": 279.8,
            "Ca II H": 396.85,
            "Ca II K": 393.37,
        })
        self.tolerance = config.get_param("tolerance", 1.0)  # nm tolerance

    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> SkillResult:
        """执行光谱分析"""
        context = context or {}
        start_time = time.time()

        try:
            if isinstance(input_data, dict):
                spectrum = input_data.get("spectrum", [])
                wavelengths = input_data.get("wavelengths", [])
            elif isinstance(input_data, list):
                spectrum = input_data
                wavelengths = []
            else:
                return SkillResult(
                    skill_name=self.name,
                    success=False,
                    error="Invalid input format"
                )

            # 分析光谱
            results = await self._analyze_spectrum(spectrum, wavelengths, context)

            return SkillResult(
                skill_name=self.name,
                success=True,
                output=results,
                execution_time=time.time() - start_time,
                metrics={
                    "lines_detected": len(results.get("detected_lines", [])),
                    "snr": results.get("snr", 0),
                },
                artifacts=[results] if results.get("plot") else []
            )

        except Exception as e:
            logger.error(f"Spectral analysis failed: {e}")
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _analyze_spectrum(
        self,
        spectrum: List[float],
        wavelengths: List[float],
        context: Dict
    ) -> Dict:
        """执行实际的光谱分析"""
        detected_lines = []

        # 简单的谱线检测（实际应用中需要更复杂的算法）
        for line_name, rest_wavelength in self.spectral_lines.items():
            # 模拟检测
            detected_lines.append({
                "line": line_name,
                "rest_wavelength": rest_wavelength,
                "observed_wavelength": rest_wavelength * 1.001,  # 模拟红移
                "flux": 0.5,
                "equivalent_width": 2.5,
            })

        # 计算信噪比
        if spectrum:
            mean = sum(spectrum) / len(spectrum)
            variance = sum((x - mean) ** 2 for x in spectrum) / len(spectrum)
            snr = mean / (variance ** 0.5) if variance > 0 else 0
        else:
            snr = 0

        return {
            "detected_lines": detected_lines,
            "snr": snr,
            "redshift": 0.001,  # 模拟值
            "spectral_class": "G2V",
            "plot": None,  # 可以生成图表
        }


@register_skill("observation_planning", SkillType.OBSERVATION_PLANNING)
class ObservationPlanningSkill(BaseSkill):
    """
    观测计划技能
    生成天文观测计划，优化观测时间分配
    """

    def __init__(self, config: SkillConfig = None):
        if config is None:
            config = SkillConfig(
                name="observation_planning",
                skill_type=SkillType.OBSERVATION_PLANNING,
                description="Plan astronomical observations, schedule targets, and optimize observation time"
            )
        super().__init__(config)
        self.location = config.get_param("location", {"lat": 30.0, "lon": 120.0, "elevation": 100})
        self.horizon_limit = config.get_param("horizon_limit", 20)  # degrees

    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> SkillResult:
        """执行观测计划"""
        context = context or {}
        start_time = time.time()

        try:
            targets = input_data if isinstance(input_data, list) else [input_data]

            # 生成观测计划
            schedule = await self._create_schedule(targets, context)

            return SkillResult(
                skill_name=self.name,
                success=True,
                output=schedule,
                execution_time=time.time() - start_time,
                metrics={
                    "targets_scheduled": len(schedule.get("scheduled", [])),
                    "total_time": schedule.get("total_time", 0),
                }
            )

        except Exception as e:
            logger.error(f"Observation planning failed: {e}")
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _create_schedule(self, targets: List[Dict], context: Dict) -> Dict:
        """创建观测计划"""
        scheduled = []
        total_time = 0

        for target in targets:
            ra = target.get("ra", 0)
            dec = target.get("dec", 0)
            name = target.get("name", f"Target_{len(scheduled)}")
            exposure = target.get("exposure", 300)  # seconds

            # 简单的调度（实际需要考虑天体位置、大气条件等）
            slot = {
                "target": name,
                "ra": ra,
                "dec": dec,
                "start_time": f"2026-05-19T{total_time // 3600:02d}:{(total_time % 3600) // 60:02d}:00",
                "duration": exposure,
                "priority": target.get("priority", 1),
            }
            scheduled.append(slot)
            total_time += exposure + 60  # 包含切换时间

        return {
            "scheduled": scheduled,
            "total_time": total_time,
            "location": self.location,
            "horizon_limit": self.horizon_limit,
            "observable_count": len(scheduled),
        }


@register_skill("catalog_query", SkillType.CATALOG_QUERY)
class CatalogQuerySkill(BaseSkill):
    """
    星表查询技能
    查询各种天文星表（SIMBAD, NED, VizieR等）
    """

    def __init__(self, config: SkillConfig = None):
        if config is None:
            config = SkillConfig(
                name="catalog_query",
                skill_type=SkillType.CATALOG_QUERY,
                description="Query astronomical catalogs (SIMBAD, NED, VizieR) for stellar and galactic objects"
            )
        super().__init__(config)
        self.default_catalogs = config.get_param("catalogs", ["SIMBAD", "VizieR", "NED"])
        self.max_results = config.get_param("max_results", 100)

    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> SkillResult:
        """执行星表查询"""
        context = context or {}
        start_time = time.time()

        try:
            if isinstance(input_data, dict):
                query_params = input_data
            elif isinstance(input_data, str):
                query_params = {"target": input_data}
            else:
                return SkillResult(
                    skill_name=self.name,
                    success=False,
                    error="Invalid input format"
                )

            # 执行查询
            results = await self._query_catalog(query_params, context)

            return SkillResult(
                skill_name=self.name,
                success=True,
                output=results,
                execution_time=time.time() - start_time,
                metrics={
                    "results_count": len(results.get("objects", [])),
                    "catalogs_queried": len(results.get("catalogs", [])),
                }
            )

        except Exception as e:
            logger.error(f"Catalog query failed: {e}")
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _query_catalog(self, query_params: Dict, context: Dict) -> Dict:
        """执行星表查询"""
        target = query_params.get("target", "")
        catalog = query_params.get("catalog", self.default_catalogs)
        if isinstance(catalog, str):
            catalog = [catalog]

        objects = []

        # 模拟星表查询（实际应用中需要API调用）
        if target:
            objects.append({
                "name": target,
                "ra": query_params.get("ra", 0.0),
                "dec": query_params.get("dec", 0.0),
                "type": "STAR",
                "catalogs": catalog,
                "data": {
                    "parallax": 0.1,
                    "radial_velocity": 0.0,
                    "magnitude": 15.0,
                }
            })

        return {
            "objects": objects,
            "catalogs": catalog,
            "query_params": query_params,
            "query_time": datetime.now().isoformat(),
        }


# 导入datetime
from datetime import datetime


@register_skill("transient_detection", SkillType.TRANSIENT_DETECTION)
class TransientDetectionSkill(BaseSkill):
    """
    瞬变检测技能
    检测天体亮度变化，识别新星、伽马射线暴等瞬变源
    """

    def __init__(self, config: SkillConfig = None):
        if config is None:
            config = SkillConfig(
                name="transient_detection",
                skill_type=SkillType.TRANSIENT_DETECTION,
                description="Detect transient events like supernovae, GRBs, and stellar flares"
            )
        super().__init__(config)
        self.threshold = config.get_param("detection_threshold", 3.0)  # sigma
        self.reference_epoch = config.get_param("reference_epoch", "2020-01-01")

    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> SkillResult:
        """执行瞬变检测"""
        context = context or {}
        start_time = time.time()

        try:
            if isinstance(input_data, dict):
                lightcurves = input_data.get("lightcurves", [])
                images = input_data.get("images", [])
            elif isinstance(input_data, list):
                lightcurves = input_data
                images = []
            else:
                return SkillResult(
                    skill_name=self.name,
                    success=False,
                    error="Invalid input format"
                )

            # 检测瞬变
            detections = await self._detect_transients(lightcurves, images, context)

            return SkillResult(
                skill_name=self.name,
                success=True,
                output=detections,
                execution_time=time.time() - start_time,
                metrics={
                    "transients_detected": len(detections.get("candidates", [])),
                    "threshold_used": self.threshold,
                }
            )

        except Exception as e:
            logger.error(f"Transient detection failed: {e}")
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _detect_transients(
        self,
        lightcurves: List[Dict],
        images: List[Dict],
        context: Dict
    ) -> Dict:
        """执行瞬变检测"""
        candidates = []

        # 简单的瞬变检测（实际应用中需要更复杂的算法）
        for i, lc in enumerate(lightcurves):
            mags = lc.get("magnitudes", [])
            if len(mags) >= 2:
                # 检测亮度变化
                max_mag = max(mags)
                min_mag = min(mags)
                delta = max_mag - min_mag

                if delta > self.threshold:
                    candidates.append({
                        "id": f"transient_{i}",
                        "ra": lc.get("ra", 0),
                        "dec": lc.get("dec", 0),
                        "delta_magnitude": delta,
                        "peak_magnitude": max_mag,
                        "type": "possible_supernova",
                        "confidence": min(delta / 5.0, 1.0),
                    })

        return {
            "candidates": candidates,
            "total_candidates": len(candidates),
            "threshold": self.threshold,
            "detection_time": datetime.now().isoformat(),
            "algorithm": "sigma_clipping",
        }
