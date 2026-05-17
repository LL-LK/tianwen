"""
天问-AGI 全自动天文观测站
AutoObservatory - 整合所有模块的全自动化工作流
"""
import logging
logger = logging.getLogger(__name__)

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# ============ 工作流状态 ============

class WorkflowStatus(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    COLLECTING_DATA = "collecting_data"
    ANALYZING = "analyzing"
    SCHEDULING = "scheduling"
    OBSERVING = "observing"
    PROCESSING = "processing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class WorkflowStep:
    """工作流步骤"""
    name: str
    status: str  # pending, running, completed, failed, skipped
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    duration: float = 0

@dataclass
class ObservationSession:
    """观测会话"""
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: str = ""
    targets: List[str] = field(default_factory=list)
    schedule: Optional[Dict] = None
    collected_data: Dict = field(default_factory=dict)
    analysis_results: Dict = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.IDLE
    steps: List[WorkflowStep] = field(default_factory=list)
    report: str = ""

# ============ 导入各子模块 ============

# 为了避免循环导入，使用延迟导入
def get_collector():
    from astro_data_collector import AstroDataCollector
    return AstroDataCollector()

def get_recognizer():
    from star_recognizer import StarRecognizer
    return StarRecognizer()

def get_scheduler():
    from observation_scheduler import ObservationScheduler, Location
    return ObservationScheduler, Location

def get_analyzer():
    from astro_analyzer import AstroAnalyzer
    return AstroAnalyzer()

# ============ 全自动观测站 ============

class AutoObservatory:
    """
    全自动天文观测站

    工作流程：
    1. 初始化 - 加载配置、连接设备
    2. 数据采集 - 从多个API获取天文数据
    3. 数据分析 - 分析天气、天体位置、观测条件
    4. 调度规划 - 计算最佳观测时间和目标
    5. 执行观测 - 按计划执行观测
    6. 数据处理 - 处理采集的数据
    7. 生成报告 - 输出观测报告
    """

    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()

        # 初始化子模块
        self.collector = None
        self.recognizer = None
        self.scheduler = None
        self.analyzer = None

        # 观测会话
        self.current_session: Optional[ObservationSession] = None
        self.session_history: List[ObservationSession] = []

        # 事件回调
        self.event_handlers: Dict[str, List] = {
            "step_start": [],
            "step_complete": [],
            "anomaly_detected": [],
            "observation_started": [],
            "observation_completed": [],
        }

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "location": {
                "name": "默认观测点",
                "lat": 39.9,
                "lon": 116.4,
                "elevation": 50,
                "timezone": "Asia/Shanghai"
            },
            "observation_targets": [
                "猎户座大星云",
                "仙女座星系",
                "昴宿星团",
                "织女星",
                "天狼星"
            ],
            "auto_collect_nasa_data": True,
            "auto_weather_check": True,
            "auto_schedule": True,
            "report_format": "detailed",
            "data_retention_days": 30
        }

    def _emit_event(self, event_name: str, data: Any):
        """触发事件"""
        for handler in self.event_handlers.get(event_name, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"[EventHandler] Error: {e}")

    # ============ 生命周期管理 ============

    async def initialize(self) -> bool:
        """初始化观测站"""
        step = WorkflowStep(name="初始化", status="running")
        step.start_time = datetime.now().isoformat()

        try:
            logger.debug("=" * 60)
            logger.info("🔭 天问-AGI 全自动天文观测站")
            logger.debug("=" * 60)
            logger.info("\n初始化中...")

            # 初始化子模块
            self.collector = get_collector()
            self.recognizer = get_recognizer()
            ObservationScheduler, Location = get_scheduler()
            self.scheduler = ObservationScheduler(
                Location(**self.config["location"])
            )
            self.analyzer = get_analyzer()

            # 延迟加载其他模块
            import importlib
            try:
                from astro_data_collector import AstroDataCollector
                from star_recognizer import StarRecognizer
                from observation_scheduler import ObservationScheduler, Location
                from astro_analyzer import AstroAnalyzer

                self.collector = AstroDataCollector()
                self.recognizer = StarRecognizer()
                self.scheduler = ObservationScheduler(Location(**self.config["location"]))
                self.analyzer = AstroAnalyzer()
            except ImportError as e:
                logger.info(f"   [警告] 部分模块导入失败: {e}")

            step.status = "completed"
            step.end_time = datetime.now().isoformat()
            step.duration = (datetime.fromisoformat(step.end_time) -
                           datetime.fromisoformat(step.start_time)).total_seconds()

            logger.info(f"   ✅ 初始化完成")

            self._emit_event("step_complete", {"step": "initialize", "status": "success"})
            return True

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.end_time = datetime.now().isoformat()
            logger.info(f"   ❌ 初始化失败: {e}")
            return False

    async def shutdown(self):
        """关闭观测站"""
        if self.current_session and self.current_session.status == WorkflowStatus.OBSERVING:
            await self.stop_observation()

        logger.info("\n🔭 观测站已关闭")
        logger.info(f"   历史会话数: {len(self.session_history)}")

    # ============ 数据采集 ============

    async def collect_data(self) -> Dict:
        """采集天文数据"""
        step = WorkflowStep(name="数据采集", status="running")
        step.start_time = datetime.now().isoformat()
        self._emit_event("step_start", {"step": "step_start"})

        logger.info("\n📡 采集天文数据...")

        collected = {
            "timestamp": datetime.now().isoformat(),
            "sources": [],
            "data": {}
        }

        try:
            # 1. 获取NASA每日天文图片
            if self.config.get("auto_collect_nasa_data"):
                logger.info("   📷 获取NASA每日天文图片...")
                apod = await self.collector.get_apod()
                if apod:
                    collected["data"]["apod"] = {
                        "title": apod.get("title"),
                        "url": apod.get("url"),
                        "hdurl": apod.get("hdurl"),
                        "date": apod.get("date")
                    }
                    collected["sources"].append("NASA APOD")
                    logger.info(f"      ✅ {apod.get('title', 'N/A')}")

            # 2. 获取即将发生的天文事件
            logger.info("   📅 获取天文事件...")
            events = await self.collector.get_upcoming_events(30)
            if events:
                collected["data"]["events"] = [
                    {"name": e.name, "type": e.type, "time": e.start_time}
                    for e in events[:10]
                ]
                collected["sources"].append("天文事件日历")
                logger.info(f"      ✅ 获取到 {len(events)} 个事件")

            # 3. 获取近地小行星
            logger.info("   ☄️ 获取近地小行星...")
            asteroids = await self.collector.get_near_earth_asteroids(7)
            if asteroids:
                collected["data"]["asteroids"] = asteroids[:10]
                collected["sources"].append("Minor Planet Center")
                logger.info(f"      ✅ 获取到 {len(asteroids)} 个近地天体")

            # 4. 获取观测条件
            if self.config.get("auto_weather_check"):
                logger.info("   🌤️ 检查观测条件...")
                loc = self.config["location"]
                conditions = await self.collector.get_observation_conditions(
                    loc["lat"], loc["lon"]
                )
                if conditions:
                    collected["data"]["weather"] = {
                        "cloud_cover": conditions.cloud_cover,
                        "humidity": conditions.humidity,
                        "temperature": conditions.temperature,
                        "moon_phase": conditions.moon_phase,
                        "seeing": conditions.seeing
                    }
                    collected["sources"].append("天气API")
                    logger.info(f"      ✅ 云量{conditions.cloud_cover}%, 湿度{conditions.humidity}%")

            step.status = "completed"
            step.end_time = datetime.now().isoformat()
            step.duration = (datetime.fromisoformat(step.end_time) -
                           datetime.fromisoformat(step.start_time)).total_seconds()
            step.result = collected

            logger.info(f"   ✅ 数据采集完成，共 {len(collected['sources'])} 个数据源")

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.end_time = datetime.now().isoformat()
            logger.info(f"   ❌ 数据采集失败: {e}")

        self._emit_event("step_complete", {"step": "data_collection", "status": step.status})
        return collected

    # ============ 目标分析 ============

    async def analyze_targets(self, targets: List[str]) -> Dict:
        """分析观测目标"""
        step = WorkflowStep(name="目标分析", status="running")
        step.start_time = datetime.now().isoformat()

        logger.info("\n🔍 分析观测目标...")

        analysis = {
            "targets": [],
            "recommendations": []
        }

        try:
            for target_name in targets[:10]:  # 最多分析10个
                logger.info(f"   📍 分析 {target_name}...")

                # 识别天体
                result = await self.recognizer.recognize_from_name(target_name)

                if result.confidence > 0:
                    target_info = {
                        "name": result.object_name,
                        "type": result.object_type,
                        "confidence": result.confidence,
                        "position": {
                            "ra": result.features.get("ra"),
                            "dec": result.features.get("dec")
                        },
                        "magnitude": result.catalog_match.magnitude if result.catalog_match else None,
                        "is_visible_now": False  # 稍后计算
                    }
                    analysis["targets"].append(target_info)
                    logger.info(f"      ✅ 类型: {result.object_type}, 星等: {target_info['magnitude']}")
                else:
                    logger.info(f"      ⚠️ 未识别")

            # 生成推荐
            if analysis["targets"]:
                visible_targets = [t for t in analysis["targets"] if t.get("is_visible_now")]
                if visible_targets:
                    analysis["recommendations"].append(
                        f"当前有 {len(visible_targets)} 个目标可见"
                    )
                else:
                    analysis["recommendations"].append("当前无可见目标，建议等待")

            step.status = "completed"
            step.result = analysis

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            logger.info(f"   ❌ 目标分析失败: {e}")

        return analysis

    # ============ 调度规划 ============

    async def create_schedule(self, targets: List[str], date: datetime = None) -> Dict:
        """创建观测计划"""
        step = WorkflowStep(name="调度规划", status="running")
        step.start_time = datetime.now().isoformat()

        logger.info("\n📋 创建观测计划...")

        date = date or datetime.now()

        try:
            schedule = await self.scheduler.generate_schedule(targets, date)
            schedule_dict = {
                "id": schedule.id,
                "date": schedule.date,
                "location": schedule.location.name,
                "targets": schedule.targets,
                "windows_count": len(schedule.windows)
            }

            logger.info(f"   ✅ 计划创建成功")
            logger.info(f"      计划ID: {schedule.id}")
            logger.info(f"      推荐目标: {len(schedule.targets)}个")

            if schedule.targets:
                logger.info("      推荐目标列表:")
                for t in schedule.targets[:3]:
                    logger.info(f"        - {t['target']} @ {t['time']} (评分:{t['score']:.0f})")

            step.status = "completed"
            step.result = schedule_dict

            return schedule_dict

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            logger.info(f"   ❌ 调度规划失败: {e}")
            return {}

    # ============ 执行观测 ============

    async def start_observation(self, targets: List[str] = None,
                                 duration_minutes: int = 60) -> str:
        """开始观测"""
        targets = targets or self.config.get("observation_targets", [])

        session_id = f"obs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_session = ObservationSession(
            id=session_id,
            start_time=datetime.now(),
            location=self.config["location"]["name"],
            targets=targets,
            status=WorkflowStatus.OBSERVING
        )

        self._emit_event("observation_started", {"session_id": session_id})
        logger.debug("\n" + "=" * 60)
        logger.info(f"🔭 开始观测会话: {session_id}")
        logger.debug("=" * 60)

        # 完整工作流
        try:
            # 1. 采集数据
            self.current_session.collected_data = await self.collect_data()

            # 2. 分析目标
            target_analysis = await self.analyze_targets(targets)
            self.current_session.analysis_results["targets"] = target_analysis

            # 3. 创建调度
            schedule = await self.create_schedule(targets)
            self.current_session.schedule = schedule

            # 4. 数据分析
            logger.info("\n📊 执行综合数据分析...")
            if self.current_session.collected_data.get("weather"):
                weather_data = self.current_session.collected_data["weather"]
                seeing_data = [weather_data.get("seeing", 2.0)]
                cloud_data = [weather_data.get("cloud_cover", 20)]

                quality_analysis = self.analyzer.analyze_observation_quality(
                    seeing_data, cloud_data,
                    [datetime.now().isoformat()]
                )
                self.current_session.analysis_results["quality"] = quality_analysis
                logger.info(f"   观测质量: {quality_analysis['overall_quality_score']}/100")

            # 5. 生成报告
            report = await self.generate_report()
            self.current_session.report = report

            self.current_session.status = WorkflowStatus.COMPLETED
            self.current_session.end_time = datetime.now()

            logger.debug("\n" + "=" * 60)
            logger.info("✅ 观测会话完成")
            logger.debug("=" * 60)

        except Exception as e:
            self.current_session.status = WorkflowStatus.FAILED
            logger.info(f"\n❌ 观测失败: {e}")
            self.current_session.report = f"观测失败: {str(e)}"

        # 保存到历史
        self.session_history.append(self.current_session)

        return session_id

    async def stop_observation(self):
        """停止观测"""
        if self.current_session:
            self.current_session.status = WorkflowStatus.PAUSED
            self.current_session.end_time = datetime.now()
            logger.info(f"\n⏸️ 观测已暂停: {self.current_session.id}")

    # ============ 报告生成 ============

    async def generate_report(self) -> str:
        """生成观测报告"""
        if not self.current_session:
            return "无可用数据"

        session = self.current_session
        lines = [
            "=" * 70,
            "🔭 天问-AGI 全自动天文观测报告",
            "=" * 70,
            f"会话ID: {session.id}",
            f"观测地点: {session.location}",
            f"开始时间: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"结束时间: {session.end_time.strftime('%Y-%m-%d %H:%M:%S')}" if session.end_time else "",
            f"状态: {session.status.value}",
            "",
            "-" * 70,
            "📡 数据采集",
            "-" * 70,
        ]

        if session.collected_data:
            sources = session.collected_data.get("sources", [])
            lines.append(f"数据源: {', '.join(sources) if sources else '无'}")

            if session.collected_data.get("apod"):
                apod = session.collected_data["apod"]
                lines.append(f"NASA APOD: {apod.get('title', 'N/A')}")

            if session.collected_data.get("events"):
                events = session.collected_data["events"]
                lines.append(f"天文事件: {len(events)} 个")

            if session.collected_data.get("weather"):
                w = session.collected_data["weather"]
                lines.append(f"天气: 云量{w.get('cloud_cover','N/A')}% | 湿度{w.get('humidity','N/A')}%")

        lines.extend([
            "",
            "-" * 70,
            "📋 观测目标",
            "-" * 70,
        ])

        if session.schedule and session.schedule.get("targets"):
            for t in session.schedule["targets"]:
                lines.append(f"  • {t['target']} @ {t['time']} (评分:{t['score']:.0f})")
        else:
            lines.append("  无计划目标")

        lines.extend([
            "",
            "-" * 70,
            "📊 分析结果",
            "-" * 70,
        ])

        if session.analysis_results.get("quality"):
            q = session.analysis_results["quality"]
            lines.append(f"观测质量评分: {q.get('overall_quality_score', 'N/A')}/100")
            lines.append(f"质量等级: {q.get('quality_level', 'N/A')}")
            lines.append(f"建议: {q.get('recommendation', 'N/A')}")

        if session.analysis_results.get("targets"):
            target_count = len(session.analysis_results["targets"])
            lines.append(f"目标分析: 共 {target_count} 个目标")

        lines.extend([
            "",
            "=" * 70,
            "报告生成时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "天问-AGI 全自动天文观测站 v2.3.0",
            "=" * 70,
        ])

        return "\n".join(lines)

    def get_session_summary(self, session_id: str = None) -> Dict:
        """获取会话摘要"""
        if session_id:
            session = next((s for s in self.session_history if s.id == session_id), None)
        else:
            session = self.current_session

        if not session:
            return {"error": "Session not found"}

        return {
            "id": session.id,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "status": session.status.value,
            "targets_count": len(session.targets),
            "has_report": bool(session.report)
        }

    def get_all_sessions(self) -> List[Dict]:
        """获取所有会话"""
        return [self.get_session_summary(s.id) for s in self.session_history]

# ============ 便捷函数 ============

async def quick_observation(targets: List[str] = None):
    """快速观测 - 一行命令执行完整工作流"""
    observatory = AutoObservatory()

    logger.info("🚀 启动快速观测...")

    # 初始化
    if not await observatory.initialize():
        logger.info("❌ 初始化失败")
        return

    # 开始观测
    session_id = await observatory.start_observation(targets)

    # 输出报告
    print("\n" + observatory.current_session.report)

    # 关闭
    await observatory.shutdown()

    return session_id

# ============ 示例用法 ============

async def demo():
    """演示全自动观测站"""
    logger.debug("=" * 70)
    logger.info("🌟 天问-AGI 全自动天文观测站 - 完整演示")
    logger.debug("=" * 70)

    # 创建观测站实例
    observatory = AutoObservatory({
        "location": {
            "name": "北京天文馆",
            "lat": 39.9,
            "lon": 116.4,
            "elevation": 50
        },
        "observation_targets": [
            "猎户座大星云",
            "织女星",
            "天狼星",
            "仙女座星系",
            "昴宿星团"
        ],
        "auto_collect_nasa_data": True,
        "auto_weather_check": True
    })

    # 初始化
    init_success = await observatory.initialize()
    if not init_success:
        logger.info("❌ 初始化失败，退出")
        return

    # 执行完整观测流程
    session_id = await observatory.start_observation()

    # 打印报告
    if observatory.current_session:
        print("\n" + observatory.current_session.report)

    # 关闭
    await observatory.shutdown()

    logger.info("\n📊 会话历史:")
    for s in observatory.get_all_sessions():
        logger.info(f"  - {s['id']}: {s['status']} @ {s['start_time'][:10]}")

if __name__ == "__main__":
    asyncio.run(demo())
    # 或者使用快速观测：
    # asyncio.run(quick_observation(["猎户座大星云", "织女星"]))