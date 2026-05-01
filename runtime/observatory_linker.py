"""
天问-AGI 观测指导模块 v1.0
ObservatoryLinker - 将假说验证结果转化为观测计划

基于Issue #15的P0需求设计:
- 研究LSST/ATLAS调度算法
- 与discovery_tracker集成形成完整闭环

功能:
- 接收假说验证结果
- 生成观测计划
- 优先级排序(LSST特征驱动 + ATLAS威胁评分)
- SIMBAD/MPC数据接口
- 望远镜调度接口

用法:
    linker = ObservatoryLinker()
    plan = await linker.link_to_observation("hypo_001")
"""

import asyncio
import json
import uuid
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import httpx
import numpy as np


# ============ 枚举定义 ============

class VerificationState(Enum):
    """验证状态"""
    PENDING = "pending"           # 待验证
    IN_PROGRESS = "in_progress"   # 验证中
    CONFIRMED = "confirmed"       # 已确认
    REJECTED = "rejected"        # 已反驳
    REVISED = "revised"          # 已修订
    INCONCLUSIVE = "inconclusive" # 结果不确定


class ObservationPriority(Enum):
    """观测优先级"""
    CRITICAL = 1   # 紧急 - 需要立即观测
    HIGH = 2       # 高优先级
    MEDIUM = 3     # 中等优先级
    LOW = 4        # 低优先级
    BACKLOG = 5    # 积压项


class TargetType(Enum):
    """目标类型"""
    STAR = "star"
    GALAXY = "galaxy"
    NEBULA = "nebula"
    PLANET = "planet"
    ASTEROID = "asteroid"
    COMET = "comet"
    EXOPLANET = "exoplanet"
    UNKNOWN = "unknown"


@dataclass
class ObservationTarget:
    """观测目标"""
    name: str
    target_type: TargetType
    ra: float = 0.0       # 赤经 (度)
    dec: float = 0.0     # 赤纬 (度)
    magnitude: float = 0.0
    spectral_info: str = ""
    simbad_id: str = ""
    mpc_id: str = ""

    # 观测需求
    min_exposure: float = 0.0  # 最短曝光时间(秒)
    recommended_bands: List[str] = field(default_factory=list)
    multi_wavelength_required: bool = False

    # 来源信息
    source_hypothesis_id: str = ""
    source_discovery_id: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.target_type.value,
            "ra": self.ra,
            "dec": self.dec,
            "magnitude": self.magnitude,
            "spectral_info": self.spectral_info,
            "simbad_id": self.simbad_id,
            "mpc_id": self.mpc_id
        }


@dataclass
class ObservationRequest:
    """观测请求"""
    id: str
    target: ObservationTarget
    priority: ObservationPriority
    priority_score: float  # 0-100计算的优先级分数

    # 验证相关
    hypothesis_id: str
    verification_state: VerificationState
    evidence_gaps: List[str]  # 需要填补的证据缺口

    # 时间约束
    requested_time_start: datetime = None
    requested_time_end: datetime = None
    urgency_hours: float = 24.0  # 多少小时内需要完成

    # 观测参数
    suggested_duration: float = 0.0  # 建议观测时长(分钟)
    suggested_bands: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.id is None:
            self.id = f"obs_req_{uuid.uuid4().hex[:8]}"


@dataclass
class ObservationPlan:
    """观测计划"""
    id: str
    created_at: str
    hypotheses_count: int

    # 观测请求列表
    requests: List[ObservationRequest]

    # 执行信息
    estimated_duration: float  # 总时长(分钟)
    location_name: str = ""
    weather_requirements: str = "clear"

    # 元数据
    priority_distribution: Dict[str, int] = field(default_factory=dict)
    target_distribution: Dict[str, int] = field(default_factory=dict)

    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "hypotheses_count": self.hypotheses_count,
            "requests_count": len(self.requests),
            "estimated_duration": self.estimated_duration,
            "priority_distribution": self.priority_distribution,
            "notes": self.notes
        }


@dataclass
class SimbadResult:
    """SIMBAD查询结果"""
    basic_id: str
    main_id: str
    object_type: str
    ra: float
    dec: float
    coordinates_system: str = "ICRS"
    magnitude: float = 0.0
    spectral_type: str = ""
    parallax: float = 0.0
    pm_ra: float = 0.0  # proper motion RA
    pm_dec: float = 0.0  # proper motion Dec
    radial_velocity: float = 0.0

    # 多波段数据
    flux_data: Dict[str, float] = field(default_factory=dict)

    # 文献关联
    bibliography_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "basic_id": self.basic_id,
            "main_id": self.main_id,
            "type": self.object_type,
            "ra": self.ra,
            "dec": self.dec,
            "magnitude": self.magnitude,
            "spectral_type": self.spectral_type
        }


@dataclass
class MpcResult:
    """MPC查询结果"""
    designation: str
    name: str
    orbit_type: str  # MBA, NEO, Comet, etc.

    # 轨道根数
    semi_major_axis: float = 0.0
    eccentricity: float = 0.0
    inclination: float = 0.0
    long_asc_node: float = 0.0
    arg_perihelion: float = 0.0
    mean_anomaly: float = 0.0

    # 观测数据
    observation_count: int = 0
    arc_years: str = ""
    last_observation: str = ""

    # 威胁评估
    potentially_hazardous: bool = False
    impact_probability: float = 0.0  # 如果是NEO

    def to_dict(self) -> Dict:
        return {
            "designation": self.designation,
            "name": self.name,
            "orbit_type": self.orbit_type,
            "potentially_hazardous": self.potentially_hazardous
        }


# ============ 优先级计算器 ============

class PriorityCalculator:
    """
    观测优先级计算器
    结合LSST特征驱动调度 + ATLAS威胁评分机制
    """

    # 优先级权重配置
    WEIGHTS = {
        "scientific_impact": 0.30,    # 科学影响力
        "verification_urgency": 0.25,  # 验证紧迫性
        "observability": 0.20,        # 可观测性
        "resource_efficiency": 0.15,  # 资源效率
        "cost_risk": 0.10            # 成本风险
    }

    # 验证状态优先级乘数
    VERIFICATION_MULTIPLIERS = {
        VerificationState.REJECTED: 2.0,      # 验证失败需要立即跟进
        VerificationState.INCONCLUSIVE: 1.5,  # 不确定需要更多数据
        VerificationState.REVISED: 1.3,       # 修订后需要重新验证
        VerificationState.IN_PROGRESS: 1.2,
        VerificationState.PENDING: 1.0,
        VerificationState.CONFIRMED: 0.5       # 已确认不需要观测
    }

    @classmethod
    def calculate(
        cls,
        hypothesis_confidence: float,
        scientific_impact: float,
        verification_state: VerificationState,
        observability_score: float,
        resource_cost: float
    ) -> float:
        """
        计算综合优先级分数

        Args:
            hypothesis_confidence: 假说置信度 (0-1)
            scientific_impact: 科学影响力评分 (0-1)
            verification_state: 当前验证状态
            observability_score: 可观测性评分 (0-100)
            resource_cost: 资源成本估计 (0-1, 越高成本越高)

        Returns:
            float: 优先级分数 (0-100)
        """
        # 科学价值基础分
        scientific_value = (
            hypothesis_confidence * 0.4 +
            scientific_impact * 0.6
        )

        # 验证紧迫性
        verification_multiplier = cls.VERIFICATION_MULTIPLIERS.get(
            verification_state, 1.0
        )
        verification_score = min(1.0, scientific_value * verification_multiplier)

        # 可观测性调整
        observability_factor = observability_score / 100.0

        # 资源效率
        resource_factor = max(0.1, 1.0 - resource_cost * 0.5)

        # 综合计算
        raw_priority = (
            scientific_value * cls.WEIGHTS["scientific_impact"] +
            verification_score * cls.WEIGHTS["verification_urgency"] +
            observability_factor * cls.WEIGHTS["observability"] +
            resource_factor * cls.WEIGHTS["resource_efficiency"]
        )

        # 成本风险调整
        cost_risk = resource_cost * cls.WEIGHTS["cost_risk"]

        final_priority = (raw_priority - cost_risk) * 100

        return max(0.0, min(100.0, final_priority))

    @classmethod
    def get_priority_level(cls, score: float) -> ObservationPriority:
        """根据分数确定优先级等级"""
        if score >= 90:
            return ObservationPriority.CRITICAL
        elif score >= 70:
            return ObservationPriority.HIGH
        elif score >= 50:
            return ObservationPriority.MEDIUM
        elif score >= 30:
            return ObservationPriority.LOW
        else:
            return ObservationPriority.BACKLOG

    @classmethod
    def calculate_with_confidence(
        cls,
        hypothesis_confidence: float,
        scientific_impact: float,
        verification_state: VerificationState,
        observability_score: float,
        resource_cost: float,
        uncertainty: float = 0.1
    ) -> Dict[str, Any]:
        """
        计算优先级分数及置信区间

        Args:
            hypothesis_confidence: 假说置信度 (0-1)
            scientific_impact: 科学影响力评分 (0-1)
            verification_state: 当前验证状态
            observability_score: 可观测性评分 (0-100)
            resource_cost: 资源成本估计 (0-1)
            uncertainty: 输入不确定性 (默认0.1)

        Returns:
            Dict containing:
            - priority_score: 优先级分数
            - confidence_interval: (lower, upper) 置信区间
            - confidence: 预测置信度
        """
        # 计算多个扰动样本
        n_samples = 100
        scores = []

        for _ in range(n_samples):
            # 添加扰动模拟不确定性传播
            perturbed_confidence = hypothesis_confidence + np.random.normal(0, uncertainty)
            perturbed_confidence = max(0, min(1, perturbed_confidence))

            perturbed_impact = scientific_impact + np.random.normal(0, uncertainty)
            perturbed_impact = max(0, min(1, perturbed_impact))

            perturbed_observability = observability_score + np.random.normal(0, 5)
            perturbed_observability = max(0, min(100, perturbed_observability))

            perturbed_cost = resource_cost + np.random.normal(0, uncertainty / 2)
            perturbed_cost = max(0, min(1, perturbed_cost))

            score = cls.calculate(
                perturbed_confidence, perturbed_impact,
                verification_state, perturbed_observability, perturbed_cost
            )
            scores.append(score)

        # 计算置信区间
        scores = np.array(scores)
        priority_score = cls.calculate(
            hypothesis_confidence, scientific_impact,
            verification_state, observability_score, resource_cost
        )

        ci_lower = np.percentile(scores, 2.5)
        ci_upper = np.percentile(scores, 97.5)

        # 置信度：样本一致性越高，置信度越高
        score_std = np.std(scores)
        confidence = max(0, 1 - score_std / 50)  # 归一化

        return {
            "priority_score": priority_score,
            "confidence_interval": (float(ci_lower), float(ci_upper)),
            "confidence": float(confidence),
            "uncertainty_estimate": float(score_std)
        }

    @classmethod
    def cross_validate_priority(
        cls,
        hypothesis_confidence: float,
        scientific_impact: float,
        verification_state: VerificationState,
        observability_score: float,
        resource_cost: float
    ) -> Dict[str, Any]:
        """
        使用多种方法交叉验证优先级

        Returns:
            Dict containing:
            - primary_score: 主方法分数
            - alternative_scores: 替代方法分数
            - agreement: 一致性分数 (0-1)
            - consensus: 共识优先级
        """
        # 方法1: 原始加权计算
        score1 = cls.calculate(
            hypothesis_confidence, scientific_impact,
            verification_state, observability_score, resource_cost
        )

        # 方法2: 简化模型 (只用科学价值)
        scientific_value = (hypothesis_confidence * 0.4 + scientific_impact * 0.6)
        score2 = scientific_value * 100

        # 方法3: 保守估计 (用最小权重)
        weights_min = {
            "scientific_impact": 0.2,
            "verification_urgency": 0.15,
            "observability": 0.1,
            "resource_efficiency": 0.1,
            "cost_risk": 0.05
        }
        raw_priority = (
            scientific_value * weights_min["scientific_impact"] +
            scientific_value * 0.8 * weights_min["verification_urgency"] +
            (observability_score / 100) * weights_min["observability"] +
            0.5 * weights_min["resource_efficiency"]
        )
        score3 = (raw_priority - resource_cost * weights_min["cost_risk"]) * 100

        scores = [score1, score2, score3]

        # 计算一致性
        mean_score = np.mean(scores)
        std_score = np.std(scores)

        # 一致性分数：标准差越小，一致性越高
        agreement = max(0, 1 - std_score / 30)

        # 共识：平均值
        consensus = (score1 + score2 + score3) / 3

        return {
            "primary_score": score1,
            "alternative_scores": {"simplified": score2, "conservative": score3},
            "agreement": float(agreement),
            "consensus": float(consensus),
            "method_used": "weighted_cross_validation"
        }


# ============ SIMBAD 数据接口 ============

class SimbadClient:
    """
    SIMBAD API 客户端
    用于查询天体基本信息和星表数据
    """

    BASE_URL = "https://simbad.cds.unistra.fr/simbad/sim-script"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def query_by_name(self, target_name: str) -> Optional[SimbadResult]:
        """
        通过名称查询天体

        Args:
            target_name: 天体名称 (如 "M42", "Alpha Centauri")

        Returns:
            SimbadResult 或 None
        """
        # 构建SIMBAD脚本查询
        script = f"""
output console=off
output script=off
set limit 1

format object firm "{basic_id(main_id) %{type}} %{ra} %{dec} %{mag(V)} %{sp}"
query id {target_name}
"""

        try:
            response = await self.client.post(
                self.BASE_URL,
                data={"script": script},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                return self._parse_response(response.text, target_name)

        except Exception as e:
            print(f"[SIMBAD] Query failed for {target_name}: {e}")

        return None

    async def query_by_coords(
        self,
        ra: float,
        dec: float,
        radius: float = 5.0  # 角秒
    ) -> List[SimbadResult]:
        """
        通过坐标查询天体

        Args:
            ra: 赤经 (度)
            dec: 赤纬 (度)
            radius: 搜索半径 (角秒)

        Returns:
            SimbadResult 列表
        """
        script = f"""
output console=off
output script=off
set limit 10

format object firm "{{basic_id(main_id)}} │ {{type}} │ {{ra}} │ {{dec}} │ {{mag(V)}} │ {{sp}}"
query coo {ra} {dec} -unit ra deg -unit dec deg -radius {radius}s
"""

        try:
            response = await self.client.post(
                self.BASE_URL,
                data={"script": script},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                return self._parse_multi_response(response.text)

        except Exception as e:
            print(f"[SIMBAD] Coordinate query failed: {e}")

        return []

    def _parse_response(self, text: str, target_name: str) -> Optional[SimbadResult]:
        """解析SIMBAD响应"""
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        for line in lines:
            parts = [p.strip() for p in line.split("│")]

            if len(parts) >= 4:
                try:
                    basic_id = parts[0] if parts else target_name
                    obj_type = parts[1] if len(parts) > 1 else "unknown"

                    # 尝试解析坐标
                    ra_str = parts[2] if len(parts) > 2 else "0 0 0"
                    dec_str = parts[3] if len(parts) > 3 else "+0 0 0"

                    ra = self._parse_sexagesimal(ra_str) if ":" in ra_str else float(parts[2]) if len(parts) > 2 else 0.0
                    dec = self._parse_sexagesimal(dec_str) if ":" in dec_str else float(parts[3]) if len(parts) > 3 else 0.0

                    mag = float(parts[4]) if len(parts) > 4 and parts[4].replace(".", "").replace("-", "").isdigit() else 0.0

                    return SimbadResult(
                        basic_id=basic_id,
                        main_id=basic_id,
                        object_type=obj_type,
                        ra=ra,
                        dec=dec,
                        magnitude=mag,
                        spectral_info=parts[5] if len(parts) > 5 else ""
                    )

                except (ValueError, IndexError):
                    continue

        return None

    def _parse_multi_response(self, text: str) -> List[SimbadResult]:
        """解析多个结果的响应"""
        results = []
        lines = [l.strip() for l in text.split("\n") if l.strip() and "│" in l]

        for line in lines:
            parts = [p.strip() for p in line.split("│")]
            if len(parts) >= 2:
                result = SimbadResult(
                    basic_id=parts[0],
                    main_id=parts[0],
                    object_type=parts[1] if len(parts) > 1 else "unknown"
                )
                results.append(result)

        return results

    def _parse_sexagesimal(self, sex_str: str) -> float:
        """将60进制字符串转换为度"""
        try:
            parts = sex_str.replace("+", "").split()
            if len(parts) == 3:
                sign = 1 if sex_str.startswith("+") or not sex_str.startswith("-") else -1
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return sign * (hours + minutes / 60.0 + seconds / 3600.0) * 15.0  # RA: 15度/小时
            elif len(parts) == 2:
                sign = 1 if sex_str.startswith("+") or not sex_str.startswith("-") else -1
                degrees = float(parts[0])
                arcminutes = float(parts[1])
                return sign * (degrees + arcminutes / 60.0)
            else:
                return float(sex_str)
        except:
            return 0.0

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# ============ MPC 数据接口 ============

class MpcClient:
    """
    Minor Planet Center API 客户端
    用于查询小行星和彗星的轨道数据
    """

    # 使用NASA SSD的SBDB API
    BASE_URL = "https://ssd.jpl.nasa.gov/sbdb.cgi"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def query_by_name(self, target_name: str) -> Optional[MpcResult]:
        """
        通过名称/编号查询小行星

        Args:
            target_name: 天体名称 (如 "Ceres", "2023 XK1")

        Returns:
            MpcResult 或 None
        """
        params = {
            "format": "json",
            "query": target_name,
            "obj_group": "all",
            "obj_limit": 1,
            "obj_filter": ""
        }

        try:
            response = await self.client.get(
                self.BASE_URL,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_sbdb_response(data)

        except Exception as e:
            print(f"[MPC] Query failed for {target_name}: {e}")

        return None

    async def query_near_earth_objects(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[MpcResult]:
        """
        查询近地天体

        Args:
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            MpcResult 列表
        """
        start = start_date or datetime.now()
        end = end_date or (start + timedelta(days=30))

        params = {
            "format": "json",
            "query": "neo",
            "date_min": start.strftime("%Y-%m-%d"),
            "date_max": end.strftime("%Y-%m-%d"),
            "sort": "distance",
            "limit": 50
        }

        try:
            response = await self.client.get(
                "https://ssd.jpl.nasa.gov/sbdb.cgi",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_neo_list(data)

        except Exception as e:
            print(f"[MPC] NEO query failed: {e}")

        return []

    async def get_orbital_elements(self, designation: str) -> Optional[Dict]:
        """
        获取轨道根数

        Args:
            designation: 天体编号 (如 "433", "Ceres")

        Returns:
            轨道根数字典
        """
        params = {
            "format": "json",
            "sstr": designation,
            "orb": "1"  # 请求完整轨道
        }

        try:
            response = await self.client.get(
                self.BASE_URL,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("orbit", {})

        except Exception as e:
            print(f"[MPC] Orbital elements query failed: {e}")

        return None

    def _parse_sbdb_response(self, data: Dict) -> Optional[MpcResult]:
        """解析SBDB API响应"""
        try:
            orbit = data.get("orbit", {})
            close_appr = data.get("close_approach_data", [])

            # 检查是否为潜在威胁天体
            pha = data.get("potentially_hazardous_asteroid", False)

            return MpcResult(
                designation=data.get("short_name", ""),
                name=data.get("full_name", ""),
                orbit_type=orbit.get("class", "unknown"),
                semi_major_axis=float(orbit.get("a", 0)),
                eccentricity=float(orbit.get("e", 0)),
                inclination=float(orbit.get("i", 0)),
                potentially_hazardous=pha
            )

        except (KeyError, TypeError) as e:
            print(f"[MPC] Parse error: {e}")
            return None

    def _parse_neo_list(self, data: Dict) -> List[MpcResult]:
        """解析近地天体列表"""
        results = []
        neo_list = data.get("neo", [])

        for neo in neo_list:
            try:
                result = MpcResult(
                    designation=neo.get("des", ""),
                    name=neo.get("name", ""),
                    orbit_type="NEO",
                    potentially_hazardous=neo.get("pha", False),
                    impact_probability=neo.get("ip", 0.0)
                )
                results.append(result)

            except (KeyError, TypeError):
                continue

        return results

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# ============ 主模块: ObservatoryLinker ============

class ObservatoryLinker:
    """
    观测指导器 - 将假说验证结果转化为观测计划

    核心功能:
    1. 从discovery_tracker获取需要观测的假说
    2. 查询SIMBAD/MPC获取目标详细信息
    3. 使用LSST/ATLAS算法计算优先级
    4. 生成可执行的观测计划

    使用方法:
        linker = ObservatoryLinker()
        plan = await linker.link_to_observation("hypo_001")
    """

    def __init__(
        self,
        discovery_tracker=None,
        simbad_client: SimbadClient = None,
        mpc_client: MpcClient = None
    ):
        self.discovery_tracker = discovery_tracker
        self.simbad = simbad_client or SimbadClient()
        self.mpc = mpc_client or MpcClient()

        # 优先级计算器
        self.priority_calc = PriorityCalculator()

        # 缓存
        self._simbad_cache: Dict[str, SimbadResult] = {}
        self._mpc_cache: Dict[str, MpcResult] = {}
        self._target_resolution_cache: Dict[str, ObservationTarget] = {}

    async def link_to_observation(
        self,
        hypothesis_id: str,
        location_name: str = "默认位置"
    ) -> Optional[ObservationPlan]:
        """
        将单个假说转化为观测计划

        Args:
            hypothesis_id: 假说ID
            location_name: 观测位置名称

        Returns:
            ObservationPlan 或 None (如果假说不需要观测)
        """
        # 获取假说和验证状态
        hypothesis = await self._get_hypothesis(hypothesis_id)
        if not hypothesis:
            print(f"[Linker] Hypothesis {hypothesis_id} not found")
            return None

        verification_state = await self._get_verification_state(hypothesis_id)

        # 如果假说已确认且置信度高，可能不需要观测
        if verification_state == VerificationState.CONFIRMED and hypothesis.get("confidence", 0) > 0.9:
            print(f"[Linker] Hypothesis {hypothesis_id} already confirmed with high confidence")
            return None

        # 生成观测请求
        request = await self._create_observation_request(hypothesis, verification_state)

        if not request:
            return None

        # 创建计划
        plan = ObservationPlan(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            created_at=datetime.now().isoformat(),
            hypotheses_count=1,
            requests=[request],
            estimated_duration=request.suggested_duration,
            location_name=location_name,
            notes=f"基于假说 {hypothesis_id} 生成的观测计划"
        )

        return plan

    async def generate_observation_plan(
        self,
        hypothesis_ids: List[str],
        location_name: str = "默认位置",
        max_requests: int = 20
    ) -> ObservationPlan:
        """
        批量生成观测计划

        Args:
            hypothesis_ids: 假说ID列表
            location_name: 观测位置名称
            max_requests: 最大请求数量

        Returns:
            ObservationPlan: 包含多个观测请求的计划
        """
        all_requests: List[ObservationRequest] = []

        for hypo_id in hypothesis_ids:
            request = await self.link_to_observation(hypo_id, location_name)
            if request:
                all_requests.append(request)

            if len(all_requests) >= max_requests:
                break

        # 按优先级排序
        all_requests.sort(key=lambda r: r.priority_score, reverse=True)

        # 统计
        priority_dist = defaultdict(int)
        target_dist = defaultdict(int)

        for req in all_requests:
            priority_dist[req.priority.name] += 1
            target_dist[req.target.target_type.value] += 1

        # 计算总时长
        total_duration = sum(r.suggested_duration for r in all_requests)

        plan = ObservationPlan(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            created_at=datetime.now().isoformat(),
            hypotheses_count=len(hypothesis_ids),
            requests=all_requests,
            estimated_duration=total_duration,
            location_name=location_name,
            priority_distribution=dict(priority_dist),
            target_distribution=dict(target_dist),
            notes=f"批量生成的计划，包含 {len(all_requests)} 个观测请求"
        )

        return plan

    async def update_plan_priorities(
        self,
        plan: ObservationPlan,
        new_urgent_hypotheses: List[str] = None
    ) -> ObservationPlan:
        """
        更新计划中的优先级

        用于在计划执行过程中根据新信息调整优先级

        Args:
            plan: 现有观测计划
            new_urgent_hypotheses: 新发现的紧急假说ID列表

        Returns:
            更新后的观测计划
        """
        urgent_set = set(new_urgent_hypotheses or [])

        for req in plan.requests:
            if req.hypothesis_id in urgent_set:
                # 提升优先级
                req.priority = ObservationPriority.CRITICAL
                req.priority_score = min(100.0, req.priority_score * 1.5)
                req.urgency_hours = min(req.urgency_hours, 6.0)  # 最快6小时内

        # 重新排序
        plan.requests.sort(key=lambda r: r.priority_score, reverse=True)

        return plan

    # ============ 内部方法 ============

    async def _get_hypothesis(self, hypothesis_id: str) -> Optional[Dict]:
        """获取假说数据"""
        if self.discovery_tracker:
            try:
                chain = await self.discovery_tracker.get_completion_chain(hypothesis_id)
                if chain:
                    # 从链条中提取假说信息
                    hypotheses = chain.get("hypotheses", [])
                    if hypotheses:
                        return hypotheses[0]
            except Exception as e:
                print(f"[Linker] Failed to get hypothesis: {e}")

        return None

    async def _get_verification_state(self, hypothesis_id: str) -> VerificationState:
        """获取验证状态"""
        if self.discovery_tracker:
            try:
                records = await self.discovery_tracker.get_completion_chain(hypothesis_id)
                verifications = records.get("verifications", [])

                if not verifications:
                    return VerificationState.PENDING

                latest = verifications[-1]
                outcome = latest.get("outcome", "")

                if outcome == "confirmed":
                    return VerificationState.CONFIRMED
                elif outcome == "rejected":
                    return VerificationState.REJECTED
                elif outcome == "revised":
                    return VerificationState.REVISED
                elif outcome == "inconclusive":
                    return VerificationState.INCONCLUSIVE
                else:
                    return VerificationState.IN_PROGRESS

            except Exception as e:
                print(f"[Linker] Failed to get verification state: {e}")

        return VerificationState.PENDING

    async def _create_observation_request(
        self,
        hypothesis: Dict,
        verification_state: VerificationState
    ) -> Optional[ObservationRequest]:
        """创建观测请求"""
        # 解析假说内容提取目标
        target_name = self._extract_target_from_hypothesis(hypothesis)
        if not target_name:
            return None

        # 查询天体数据
        target = await self._resolve_target(target_name, hypothesis.get("id", ""))

        if not target:
            return None

        # 计算优先级
        priority_score = self.priority_calc.calculate(
            hypothesis_confidence=hypothesis.get("confidence", 0.5),
            scientific_impact=hypothesis.get("impact_score", 0.5),
            verification_state=verification_state,
            observability_score=70.0,  # 默认值，实际应由调度器计算
            resource_cost=0.5  # 默认值
        )

        priority = self.priority_calc.get_priority_level(priority_score)

        # 生成证据缺口列表
        evidence_gaps = self._extract_evidence_gaps(hypothesis)

        # 确定推荐波段
        suggested_bands = self._determine_bands(target, evidence_gaps)

        # 估计观测时长
        duration = self._estimate_duration(target, suggested_bands)

        request = ObservationRequest(
            id=f"req_{uuid.uuid4().hex[:8]}",
            target=target,
            priority=priority,
            priority_score=priority_score,
            hypothesis_id=hypothesis.get("id", ""),
            verification_state=verification_state,
            evidence_gaps=evidence_gaps,
            suggested_duration=duration,
            suggested_bands=suggested_bands
        )

        return request

    def _extract_target_from_hypothesis(self, hypothesis: Dict) -> Optional[str]:
        """从假说中提取目标天体名称"""
        statement = hypothesis.get("statement", "")

        # 常见天体名称模式
        patterns = [
            r"M\d+",           # Messier
            r"NGC \d+",        # NGC
            r"IC \d+",         # IC
            r"[A-Z][a-z]+ \d+", # 恒星如 Alpha Centauri
            r"\d+ [A-Z][a-z]+", # 恒星如 51 Pegasi
        ]

        import re
        for pattern in patterns:
            match = re.search(pattern, statement)
            if match:
                return match.group(0)

        # 如果没有匹配，尝试使用ID
        if hypothesis.get("id"):
            return hypothesis["id"]

        return None

    async def _resolve_target(
        self,
        target_name: str,
        hypothesis_id: str = ""
    ) -> Optional[ObservationTarget]:
        """解析目标天体"""
        # 检查缓存
        if target_name in self._target_resolution_cache:
            return self._target_resolution_cache[target_name]

        # 优先查询SIMBAD
        simbad_result = await self._query_simbad(target_name)

        if simbad_result:
            target_type = self._map_simbad_type(simbad_result.object_type)
            target = ObservationTarget(
                name=target_name,
                target_type=target_type,
                ra=simbad_result.ra,
                dec=simbad_result.dec,
                magnitude=simbad_result.magnitude,
                spectral_info=simbad_result.spectral_type,
                simbad_id=simbad_result.basic_id,
                source_hypothesis_id=hypothesis_id
            )
        else:
            # 尝试MPC
            mpc_result = await self._query_mpc(target_name)

            if mpc_result:
                target = ObservationTarget(
                    name=target_name,
                    target_type=TargetType.ASTEROID,
                    mpc_id=mpc_result.designation,
                    source_hypothesis_id=hypothesis_id
                )
            else:
                # 创建通用目标
                target = ObservationTarget(
                    name=target_name,
                    target_type=TargetType.UNKNOWN,
                    source_hypothesis_id=hypothesis_id
                )

        self._target_resolution_cache[target_name] = target
        return target

    async def _query_simbad(self, target_name: str) -> Optional[SimbadResult]:
        """查询SIMBAD"""
        if target_name in self._simbad_cache:
            return self._simbad_cache[target_name]

        result = await self.simbad.query_by_name(target_name)

        if result:
            self._simbad_cache[target_name] = result

        return result

    async def _query_mpc(self, target_name: str) -> Optional[MpcResult]:
        """查询MPC"""
        if target_name in self._mpc_cache:
            return self._mpc_cache[target_name]

        result = await self.mpc.query_by_name(target_name)

        if result:
            self._mpc_cache[target_name] = result

        return result

    def _map_simbad_type(self, simbad_type: str) -> TargetType:
        """映射SIMBAD类型到TargetType"""
        type_lower = simbad_type.lower()

        if "star" in type_lower or "*" in type_lower:
            return TargetType.STAR
        elif "galaxy" in type_lower or "G" in type_lower:
            return TargetType.GALAXY
        elif "neb" in type_lower or "PN" in type_lower or "reflection" in type_lower:
            return TargetType.NEBULA
        elif "planet" in type_lower or "Planet" in type_lower:
            return TargetType.PLANET
        elif "asteroid" in type_lower or "Mb" in type_lower or "Mm" in type_lower:
            return TargetType.ASTEROID
        elif "comet" in type_lower:
            return TargetType.COMET
        else:
            return TargetType.UNKNOWN

    def _extract_evidence_gaps(self, hypothesis: Dict) -> List[str]:
        """提取证据缺口"""
        gaps = []

        # 从假说中提取预测
        predictions = hypothesis.get("predictions", [])
        if not predictions or len(predictions) < 2:
            gaps.append("预测数据不足，需要更多观测验证")

        # 检查验证方法
        method = hypothesis.get("verification_method", "")
        if not method or "待定" in method:
            gaps.append("验证方法未确定")

        # 检查置信度
        confidence = hypothesis.get("confidence", 0.5)
        if confidence < 0.6:
            gaps.append("假说置信度较低，需要更多证据支持")

        return gaps

    def _determine_bands(
        self,
        target: ObservationTarget,
        evidence_gaps: List[str]
    ) -> List[str]:
        """确定推荐观测波段"""
        bands = ["V"]  # 默认光学V波段

        # 根据目标类型添加波段
        if target.target_type == TargetType.NEBULA:
            bands.extend(["R", "I", "H-alpha"])

        elif target.target_type == TargetType.GALAXY:
            bands.extend(["B", "V", "R", "I"])

        elif target.target_type == TargetType.STAR:
            # 检查是否需要多波段测光
            if target.spectral_info:
                bands.extend(["B", "V", "R"])
            else:
                bands = ["V"]

        elif target.target_type == TargetType.ASTEROID:
            bands = ["V", "R"]  # 小行星通常用V和R波段

        # 根据证据缺口调整
        if any("X射线" in gap or "X-ray" in gap for gap in evidence_gaps):
            bands.append("X-ray")

        if any("红外" in gap or "infrared" in gap for gap in evidence_gaps):
            bands.extend(["J", "H", "K"])

        return list(set(bands))  # 去重

    def _estimate_duration(
        self,
        target: ObservationTarget,
        bands: List[str]
    ) -> float:
        """估计观测时长(分钟)"""
        base_duration = 10.0  # 基础时长10分钟

        # 根据目标星等调整
        if target.magnitude > 15:
            base_duration *= 2  # 暗目标需要更长时间
        elif target.magnitude < 10:
            base_duration *= 0.5  # 亮目标可以缩短

        # 根据波段数量调整
        base_duration *= (1 + 0.2 * (len(bands) - 1))

        # 根据目标类型调整
        if target.target_type == TargetType.GALAXY:
            base_duration *= 1.5  # 星系需要更长曝光
        elif target.target_type == TargetType.NEBULA:
            base_duration *= 1.3  # 星云需要较长曝光

        return min(180.0, max(5.0, base_duration))  # 限制在5-180分钟

    async def cleanup(self):
        """清理资源"""
        await self.simbad.close()
        await self.mpc.close()


# ============ 便捷函数 ============

async def quick_link(hypothesis_id: str) -> Optional[ObservationPlan]:
    """
    快速生成观测计划

    用法:
        plan = await quick_link("hypo_001")
    """
    linker = ObservatoryLinker()
    plan = await linker.link_to_observation(hypothesis_id)
    await linker.cleanup()
    return plan


async def batch_link(hypothesis_ids: List[str]) -> ObservationPlan:
    """
    批量生成观测计划

    用法:
        plan = await batch_link(["hypo_001", "hypo_002", "hypo_003"])
    """
    linker = ObservatoryLinker()
    plan = await linker.generate_observation_plan(hypothesis_ids)
    await linker.cleanup()
    return plan


# ============ 示例用法 ============

async def demo():
    """演示观测指导模块"""
    print("=" * 60)
    print("天问-AGI 观测指导模块演示")
    print("=" * 60)

    linker = ObservatoryLinker()

    # 演示1: 模拟一个假说数据
    print("\n[1] 模拟假说验证数据...")

    # 创建模拟的假说
    hypothesis = {
        "id": "hypo_demo_001",
        "statement": "如果M42猎户座大星云存在多波段辐射差异，那么这种差异反映了不同年龄的恒星群体",
        "confidence": 0.65,
        "impact_score": 0.75,
        "verification_method": "对比WISE红外数据与Chandra X射线数据",
        "predictions": ["红外波段强度应与年龄负相关", "X射线热点区域与年轻恒星位置一致"]
    }

    # 生成观测请求
    request = await linker._create_observation_request(
        hypothesis,
        VerificationState.INCONCLUSIVE
    )

    if request:
        print(f"   目标: {request.target.name}")
        print(f"   目标类型: {request.target.target_type.value}")
        print(f"   优先级: {request.priority.name}")
        print(f"   优先级分数: {request.priority_score:.1f}")
        print(f"   建议波段: {', '.join(request.suggested_bands)}")
        print(f"   估计时长: {request.suggested_duration:.0f} 分钟")
        print(f"   证据缺口: {', '.join(request.evidence_gaps) if request.evidence_gaps else '无'}")

    # 演示2: 批量生成计划
    print("\n[2] 批量生成观测计划...")

    hypotheses = [
        {
            "id": f"hypo_{i:03d}",
            "statement": f"假说 {i} 的陈述内容",
            "confidence": 0.5 + (i % 5) * 0.1,
            "impact_score": 0.6 + (i % 3) * 0.1,
            "predictions": ["预测1", "预测2"],
            "verification_method": "多波段观测"
        }
        for i in range(5)
    ]

    requests = []
    for hypo in hypotheses:
        req = await linker._create_observation_request(hypo, VerificationState.PENDING)
        if req:
            requests.append(req)

    print(f"   生成了 {len(requests)} 个观测请求")

    # 优先级分布
    priority_counts = defaultdict(int)
    for req in requests:
        priority_counts[req.priority.name] += 1

    print("   优先级分布:")
    for priority, count in sorted(priority_counts.items()):
        print(f"      {priority}: {count}")

    # 清理
    await linker.cleanup()

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())