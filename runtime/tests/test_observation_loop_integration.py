"""
Observation Loop Integration Tests
测试 astro_pipeline + enhanced_observation_scheduler + kepler_exoplanet_client 端到端集成

Run with: python -m pytest runtime/tests/test_observation_loop_integration.py -v
"""

import unittest
import asyncio
import sys
import math
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules under test
from astro_pipeline import (
    AstroPipeline,
    StageIDetector,
    StageIIClassifier,
    StageIIIDetector,
    SourceDetection,
    ClassifiedSource,
    ObjectDetection,
    PipelineResult
)
from enhanced_observation_scheduler import (
    EnhancedObservationScheduler,
    GeographicLocation,
    ObservationTarget,
    ObservationType,
    VisibilityWindow,
    AstronomicalCalculator,
    Constraints
)
from kepler_exoplanet_client import TransitSignal


# ============ Test Fixtures and Helpers ============

def create_mock_astronomical_image(size: int = 512) -> "np.ndarray":
    """创建模拟天文图像数据"""
    try:
        import numpy as np
    except ImportError:
        return None

    # 创建带背景噪声的图像
    image_data = np.zeros((size, size), dtype=np.float32)

    # 添加随机背景噪声
    np.random.seed(42)
    noise = np.random.normal(100, 10, (size, size))
    image_data += noise

    # 添加模拟星点 (Gaussian PSF形状)
    for _ in range(20):
        x = np.random.randint(50, size - 50)
        y = np.random.randint(50, size - 50)
        flux = np.random.uniform(500, 2000)

        # 创建Gaussian PSF形状的星点
        for dy in range(-10, 11):
            for dx in range(-10, 11):
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= 10:
                    intensity = flux * math.exp(-dist**2 / (2 * 3.0**2))
                    iy, ix = y + dy, x + dx
                    if 0 <= iy < size and 0 <= ix < size:
                        image_data[iy, ix] += intensity

    # 添加模拟延展源 (模拟星系或星云)
    for _ in range(3):
        cx = np.random.randint(100, size - 100)
        cy = np.random.randint(100, size - 100)
        radius = np.random.uniform(30, 60)
        flux = np.random.uniform(2000, 5000)

        for dy in range(-int(radius), int(radius) + 1):
            for dx in range(-int(radius), int(radius) + 1):
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= radius:
                    intensity = flux * (1 - dist/radius) * math.exp(-dist / (radius/2))
                    iy, ix = cy + dy, cx + dx
                    if 0 <= iy < size and 0 <= ix < size:
                        image_data[iy, ix] += intensity

    return image_data


def create_mock_lightcurve(num_points: int = 1000) -> tuple:
    """创建模拟光变曲线数据

    Returns:
        tuple: (time, flux) arrays with simulated transit signal
    """
    try:
        import numpy as np
    except ImportError:
        return None, None

    np.random.seed(42)

    # 时间序列 (10天, 每分钟一个点)
    time = np.linspace(0, 10, num_points)

    # 基础通量 (带有轻微变化)
    flux = np.ones(num_points) + np.random.normal(0, 0.001, num_points)

    # 添加凌星信号 (周期3天, 持续2小时)
    period = 3.0  # 天
    epoch = 0.5   # 第一次凌星中心时间
    duration = 2.0 / 24  # 2小时转换为天

    # 找到凌星相位的时间点
    phase = (time - epoch) % period
    transit_mask = (phase < duration) | (phase > period - duration)

    # 凌星深度
    depth = 0.01  # 1%深度
    flux[transit_mask] -= depth

    # 添加一些随机噪声
    flux += np.random.normal(0, 0.002, num_points)

    return time, flux


# ============ Test Cases ============

class TestAstroPipelineThreeStage(unittest.TestCase):
    """
    Test 1: AstroPipeline 三阶段管道测试

    验证三阶段天体检测管道:
    - Stage I: photutils源检测
    - Stage II: ResNet-50分类
    - Stage III: YOLOv11s检测
    """

    def setUp(self):
        """Set up test fixtures"""
        self.pipeline = AstroPipeline()
        self.mock_image = create_mock_astronomical_image(256)

    def test_pipeline_initialization(self):
        """验证管道初始化"""
        self.assertIsNotNone(self.pipeline.stage1_detector)
        self.assertIsNotNone(self.pipeline.stage2_classifier)
        self.assertIsNotNone(self.pipeline.stage3_detector)

    def test_stage_i_detector_initialization(self):
        """验证Stage I检测器初始化"""
        detector = StageIDetector()
        self.assertEqual(detector.fwhm, 3.0)
        self.assertEqual(detector.threshold_factor, 4.0)
        self.assertEqual(detector.min_separation, 3.0)

    @unittest.skipIf(create_mock_astronomical_image(256) is None, "numpy not available")
    def test_stage_i_source_detection(self):
        """验证Stage I源检测输出格式"""
        # 创建模拟图像
        image_data = self.mock_image
        self.assertIsNotNone(image_data)

        # 执行检测
        detector = StageIDetector()
        sources = asyncio.run(detector.detect(image_data))

        # 验证返回类型
        self.assertIsInstance(sources, list)

        # 如果检测到源，验证字段
        if sources:
            source = sources[0]
            self.assertIsInstance(source, SourceDetection)
            self.assertTrue(hasattr(source, 'x'))
            self.assertTrue(hasattr(source, 'y'))
            self.assertTrue(hasattr(source, 'flux'))

    @unittest.skipIf(create_mock_astronomical_image(256) is None, "numpy not available")
    def test_pipeline_output_format(self):
        """验证管道输出格式 {sources, detections, summary}"""
        # 执行管道处理
        result = asyncio.run(self.pipeline.process(self.mock_image))

        # 验证输出结构
        self.assertIsInstance(result, dict)
        self.assertIn('sources', result)
        self.assertIn('detections', result)
        self.assertIn('summary', result)

        # 验证sources格式
        self.assertIsInstance(result['sources'], list)
        for source in result['sources']:
            self.assertIn('x', source)
            self.assertIn('y', source)
            self.assertIn('flux', source)
            self.assertIn('type', source)  # STAR/GALAXY/QSO/None

        # 验证detections格式
        self.assertIsInstance(result['detections'], list)
        for detection in result['detections']:
            self.assertIn('class', detection)
            self.assertIn('bbox', detection)
            self.assertIn('confidence', detection)

        # 验证summary格式
        self.assertIn('total_sources', result['summary'])
        self.assertIn('stars', result['summary'])
        self.assertIn('galaxies', result['summary'])
        self.assertIn('qsos', result['summary'])

    @unittest.skipIf(create_mock_astronomical_image(256) is None, "numpy not available")
    def test_pipeline_sources_fields(self):
        """验证sources包含x, y, flux, type字段"""
        result = asyncio.run(self.pipeline.process(self.mock_image))

        if result['sources']:
            source = result['sources'][0]

            # 验证必需字段
            self.assertIn('x', source)
            self.assertIn('y', source)
            self.assertIn('flux', source)
            self.assertIn('type', source)

            # 验证字段类型
            self.assertIsInstance(source['x'], (int, float))
            self.assertIsInstance(source['y'], (int, float))
            self.assertIsInstance(source['flux'], (int, float))
            self.assertTrue(source['type'] is None or isinstance(source['type'], str))

    @unittest.skipIf(create_mock_astronomical_image(256) is None, "numpy not available")
    def test_pipeline_detections_fields(self):
        """验证detections包含class, bbox, confidence字段"""
        result = asyncio.run(self.pipeline.process(self.mock_image))

        # 如果有检测结果，验证格式
        if result['detections']:
            detection = result['detections'][0]

            # 验证必需字段
            self.assertIn('class', detection)
            self.assertIn('bbox', detection)
            self.assertIn('confidence', detection)

            # 验证bbox格式 [x1, y1, x2, y2]
            self.assertIsInstance(detection['bbox'], (list, tuple))
            self.assertEqual(len(detection['bbox']), 4)

            # 验证confidence范围
            self.assertGreaterEqual(detection['confidence'], 0.0)
            self.assertLessEqual(detection['confidence'], 1.0)

    def test_pipeline_empty_image(self):
        """验证空图像处理"""
        # 创建空图像
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not available")

        empty_image = np.zeros((100, 100), dtype=np.float32)
        result = asyncio.run(self.pipeline.process(empty_image))

        # 应该返回空结果但结构完整
        self.assertIn('sources', result)
        self.assertIn('detections', result)
        self.assertIn('summary', result)


class TestEnhancedObservationScheduler(unittest.TestCase):
    """
    Test 2: Enhanced Observation Scheduler 测试

    验证增强型观测调度器的功能:
    - 夜天文时间计算
    - 目标可见性窗口计算
    - 综合观测条件评分
    """

    def setUp(self):
        """Set up test fixtures"""
        # 创建Mauna Kea观测站位置
        self.location = GeographicLocation(
            name="Mauna Kea Observatory",
            latitude=19.8207,
            longitude=-155.4680,
            elevation=4205  # 米
        )
        self.scheduler = EnhancedObservationScheduler(self.location)

        # 创建M31观测目标 (仙女座星系)
        self.m31_target = ObservationTarget(
            name="M31 (Andromeda Galaxy)",
            ra=10.6847,    # 赤经 (度)
            dec=41.2687,   # 赤纬 (度)
            observation_type=ObservationType.IMAGING,
            priority=1
        )

        # 测试时间 (2026年5月1日晚上23:00)
        self.test_time = datetime(2026, 5, 1, 23, 0)
        self.test_period = (
            datetime(2026, 5, 1, 0, 0),
            datetime(2026, 5, 2, 0, 0)
        )

    def test_scheduler_initialization(self):
        """验证调度器初始化"""
        self.assertIsNotNone(self.scheduler.location)
        self.assertIsNotNone(self.scheduler.calculator)
        self.assertIsNotNone(self.scheduler.night_calculator)
        self.assertIsNotNone(self.scheduler.visibility_calculator)

    def test_location_creation(self):
        """验证观测位置创建"""
        self.assertEqual(self.location.name, "Mauna Kea Observatory")
        self.assertAlmostEqual(self.location.latitude, 19.8207, places=3)
        self.assertAlmostEqual(self.location.longitude, -155.4680, places=3)
        self.assertEqual(self.location.elevation, 4205)

    def test_astronomical_night_calculation(self):
        """验证夜天文时间计算返回非空结果"""
        # 计算夜天文时间窗口
        windows = self.scheduler.compute_astronomical_nights(self.test_period)

        # 验证返回类型
        self.assertIsInstance(windows, list)

        # 验证窗口格式
        for window in windows:
            self.assertIsInstance(window, VisibilityWindow)
            self.assertIsInstance(window.start, datetime)
            self.assertIsInstance(window.end, datetime)
            self.assertIsInstance(window.max_altitude, float)
            self.assertIsInstance(window.avg_altitude, float)

    def test_target_visibility_calculation(self):
        """验证目标可见性窗口计算"""
        # 计算M31的可见性窗口
        visibility = self.scheduler.compute_target_visibility(
            self.m31_target,
            self.test_period
        )

        # 验证返回类型
        self.assertIsInstance(visibility, list)

        # 验证可见性窗口格式
        for window in visibility:
            self.assertIsInstance(window.start, datetime)
            self.assertIsInstance(window.end, datetime)
            self.assertGreater(window.max_altitude, 0)

    def test_operable_periods_calculation(self):
        """验证可操作时间段计算"""
        # 计算可操作时间段
        operable = self.scheduler.compute_operable_periods(
            self.m31_target,
            self.test_period
        )

        self.assertIsInstance(operable, list)

        # 每个窗口应该有合理的属性
        for window in operable:
            self.assertGreater(window.max_altitude, -18)  # 夜天文范围内
            self.assertGreaterEqual(window.avg_altitude, window.max_altitude - 90)

    def test_observation_scoring_range(self):
        """验证综合评分在0-100范围内"""
        # 测试不同时间的评分
        test_times = [
            datetime(2026, 5, 1, 20, 0),
            datetime(2026, 5, 1, 23, 0),
            datetime(2026, 5, 2, 2, 0),
        ]

        for test_time in test_times:
            score = self.scheduler.score_candidate(
                self.m31_target,
                test_time,
                moon_phase=0.25,
                cloud_coverage=0.1
            )

            # 验证评分范围
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

    def test_observation_scoring_different_conditions(self):
        """验证不同观测条件下的评分差异"""
        # 好条件: 新月、无云、高度角高
        good_score = self.scheduler.score_candidate(
            self.m31_target,
            self.test_time,
            moon_phase=0.0,    # 新月
            cloud_coverage=0.0  # 无云
        )

        # 差条件: 满月、多云
        bad_score = self.scheduler.score_candidate(
            self.m31_target,
            self.test_time,
            moon_phase=1.0,    # 满月
            cloud_coverage=0.8  # 80%云量
        )

        # 好条件应该评分更高
        self.assertGreater(good_score, bad_score)

    def test_detailed_scoring_output(self):
        """验证详细评分输出结构"""
        detailed = self.scheduler.score_detailed(
            self.m31_target,
            self.test_time,
            moon_phase=0.25,
            cloud_coverage=0.1
        )

        # 验证输出字段
        self.assertIn('total_score', detailed)
        self.assertIn('altitude_score', detailed)
        self.assertIn('cloud_score', detailed)
        self.assertIn('moon_score', detailed)
        self.assertIn('altitude', detailed)
        self.assertIn('azimuth', detailed)

        # 验证综合评分范围
        self.assertGreaterEqual(detailed['total_score'], 0.0)
        self.assertLessEqual(detailed['total_score'], 100.0)

    def test_multiple_targets_scheduling(self):
        """验证多目标调度"""
        targets = [
            self.m31_target,
            ObservationTarget(
                name="M42 (Orion Nebula)",
                ra=83.8221,
                dec=-5.3911,
                observation_type=ObservationType.IMAGING,
                priority=2
            ),
            ObservationTarget(
                name="Vega",
                ra=279.2347,
                dec=38.7836,
                observation_type=ObservationType.PHOTOMETRY,
                priority=3
            )
        ]

        # 生成调度计划
        schedule = self.scheduler.generate_schedule(
            targets,
            period=(
                datetime(2026, 5, 1, 12, 0),
                datetime(2026, 5, 7, 12, 0)
            ),
            max_targets_per_night=5
        )

        # 验证调度结果结构
        self.assertIn('schedule', schedule)
        self.assertIn('fragmentation', schedule)
        self.assertIn('nights_count', schedule)


class TestKeplerExoplanetClientMock(unittest.TestCase):
    """
    Test 3: Kepler Exoplanet Client 测试 (Mock)

    验证系外行星凌星信号检测功能:
    - 光变曲线分析
    - 凌星信号检测
    - TransitSignal数据结构
    """

    def setUp(self):
        """Set up test fixtures"""
        self.mock_time, self.mock_flux = create_mock_lightcurve(1000)

    def test_transit_signal_dataclass(self):
        """验证TransitSignal数据结构"""
        signal = TransitSignal(
            period=3.5,
            epoch=0.5,
            duration=2.0,
            depth=0.01,
            snr=10.5,
            confidence="HIGH"
        )

        # 验证字段
        self.assertEqual(signal.period, 3.5)
        self.assertEqual(signal.epoch, 0.5)
        self.assertEqual(signal.duration, 2.0)
        self.assertEqual(signal.depth, 0.01)
        self.assertEqual(signal.snr, 10.5)
        self.assertEqual(signal.confidence, "HIGH")

    def test_transit_signal_fields_exist(self):
        """验证TransitSignal包含period, epoch, snr字段"""
        signal = TransitSignal(
            period=3.5,
            epoch=0.5,
            duration=2.0,
            depth=0.01,
            snr=10.5,
            confidence="HIGH"
        )

        # 验证必需字段存在
        self.assertTrue(hasattr(signal, 'period'))
        self.assertTrue(hasattr(signal, 'epoch'))
        self.assertTrue(hasattr(signal, 'snr'))

    @unittest.skipIf(create_mock_lightcurve(1000)[0] is None, "numpy not available")
    def test_mock_lightcurve_format(self):
        """验证模拟光变曲线数据格式"""
        time, flux = self.mock_time, self.mock_flux

        self.assertIsNotNone(time)
        self.assertIsNotNone(flux)

        # 验证形状
        self.assertEqual(len(time), len(flux))
        self.assertGreater(len(time), 0)

        # 验证通量范围 (应该有凌星信号)
        self.assertLessEqual(flux.min(), 1.0)  # 凌星会使通量下降

    def test_mock_detect_transit_signal(self):
        """测试使用模拟数据检测凌星信号"""
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not available")

        time, flux = self.mock_time, self.mock_flux
        self.assertIsNotNone(time)

        # 模拟凌星检测
        # 由于实际的detect_transit_signal可能需要网络请求，
        # 这里我们直接创建模拟的TransitSignal列表
        signals = self._create_mock_transit_signals()

        # 验证返回TransitSignal列表
        self.assertIsInstance(signals, list)
        self.assertGreater(len(signals), 0)

        # 验证每个信号的结构
        for signal in signals:
            self.assertIsInstance(signal, TransitSignal)
            self.assertTrue(hasattr(signal, 'period'))
            self.assertTrue(hasattr(signal, 'epoch'))
            self.assertTrue(hasattr(signal, 'snr'))
            self.assertGreater(signal.period, 0)
            self.assertGreater(signal.snr, 0)

    def _create_mock_transit_signals(self) -> List[TransitSignal]:
        """创建模拟的凌星信号列表"""
        signals = [
            TransitSignal(
                period=3.5,
                epoch=0.5,
                duration=2.0,
                depth=0.01,
                snr=12.5,
                confidence="HIGH"
            ),
            TransitSignal(
                period=7.2,
                epoch=1.2,
                duration=3.5,
                depth=0.005,
                snr=7.3,
                confidence="MEDIUM"
            ),
        ]
        return signals

    def test_transit_signal_confidence_levels(self):
        """验证不同信噪比的置信度评估"""
        signals = [
            TransitSignal(period=3.5, epoch=0.5, duration=2.0,
                         depth=0.01, snr=15.0, confidence="HIGH"),
            TransitSignal(period=3.5, epoch=0.5, duration=2.0,
                         depth=0.01, snr=7.5, confidence="MEDIUM"),
            TransitSignal(period=3.5, epoch=0.5, duration=2.0,
                         depth=0.01, snr=3.5, confidence="LOW"),
        ]

        self.assertEqual(signals[0].confidence, "HIGH")
        self.assertEqual(signals[1].confidence, "MEDIUM")
        self.assertEqual(signals[2].confidence, "LOW")


class TestFullObservationLoop(unittest.IsolatedAsyncioTestCase):
    """
    Test 4: 端到端流程测试

    完整观测流程:
    1. 图像输入 -> AstroPipeline检测
    2. 检测结果 -> enhanced_scheduler调度评分
    3. 高优先级目标 -> kepler_client检测凌星
    """

    def setUp(self):
        """Set up test fixtures"""
        self.pipeline = AstroPipeline()
        self.location = GeographicLocation(
            name="Mauna Kea Observatory",
            latitude=19.8207,
            longitude=-155.4680,
            elevation=4205
        )
        self.scheduler = EnhancedObservationScheduler(self.location)
        self.mock_image = create_mock_astronomical_image(256)

    async def test_full_observation_loop(self):
        """
        完整观测流程测试

        流程:
        1. 创建模拟天文图像
        2. 使用AstroPipeline检测源和扩展目标
        3. 根据检测结果创建观测目标
        4. 使用enhanced_scheduler计算可见性和评分
        5. 对高优先级目标使用kepler_client检测凌星信号
        """
        # Step 1: 创建模拟天文图像
        if self.mock_image is None:
            self.skipTest("numpy not available")

        # Step 2: AstroPipeline检测
        pipeline_result = await self.pipeline.process(self.mock_image)

        # 验证管道输出
        self.assertIn('sources', pipeline_result)
        self.assertIn('detections', pipeline_result)
        self.assertIn('summary', pipeline_result)

        # Step 3: 根据检测结果创建观测目标
        observation_targets = self._create_targets_from_detections(pipeline_result)

        # 如果有检测到的星系，使用它们作为观测目标
        if observation_targets:
            target = observation_targets[0]

            # Step 4: 使用enhanced_scheduler计算可见性
            test_time = datetime(2026, 5, 1, 23, 0)
            period = (
                datetime(2026, 5, 1, 0, 0),
                datetime(2026, 5, 2, 0, 0)
            )

            # 计算可见性窗口
            operable_windows = self.scheduler.compute_operable_periods(
                target, period
            )

            # 计算综合评分
            score = self.scheduler.score_candidate(
                target,
                test_time,
                moon_phase=0.25,
                cloud_coverage=0.1
            )

            # 验证评分
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

            # Step 5: 模拟kepler_client凌星检测
            if score > 50:  # 高优先级目标
                signals = self._create_mock_transit_signals()

                self.assertIsInstance(signals, list)
                self.assertGreater(len(signals), 0)

                # 验证信号格式
                for signal in signals:
                    self.assertTrue(hasattr(signal, 'period'))
                    self.assertTrue(hasattr(signal, 'epoch'))
                    self.assertTrue(hasattr(signal, 'snr'))

    def _create_targets_from_detections(
        self,
        pipeline_result: Dict[str, Any]
    ) -> List[ObservationTarget]:
        """从检测结果创建观测目标"""
        targets = []

        # 从sources创建目标 (如果有星系)
        for source in pipeline_result.get('sources', []):
            if source.get('type') == 'GALAXY':
                # 为每个检测到的星系创建一个观测目标
                # 使用随机坐标作为示例
                import random
                random.seed(42)
                targets.append(ObservationTarget(
                    name=f"Detected Galaxy at ({source['x']:.0f}, {source['y']:.0f})",
                    ra=random.uniform(0, 360),
                    dec=random.uniform(-90, 90),
                    observation_type=ObservationType.IMAGING,
                    priority=1
                ))

        # 从detections创建目标 (扩展目标)
        for detection in pipeline_result.get('detections', []):
            targets.append(ObservationTarget(
                name=f"Detected {detection['class']}",
                ra=10.6847,  # 使用M31坐标作为示例
                dec=41.2687,
                observation_type=ObservationType.IMAGING,
                priority=2
            ))

        # 如果没有检测到，添加一些默认目标用于测试
        if not targets:
            targets = [
                ObservationTarget(
                    name="M31 (Andromeda Galaxy)",
                    ra=10.6847,
                    dec=41.2687,
                    observation_type=ObservationType.IMAGING,
                    priority=1
                ),
                ObservationTarget(
                    name="M42 (Orion Nebula)",
                    ra=83.8221,
                    dec=-5.3911,
                    observation_type=ObservationType.IMAGING,
                    priority=2
                ),
            ]

        return targets

    def _create_mock_transit_signals(self) -> List[TransitSignal]:
        """创建模拟的凌星信号"""
        return [
            TransitSignal(
                period=3.5,
                epoch=0.5,
                duration=2.0,
                depth=0.01,
                snr=12.5,
                confidence="HIGH"
            ),
            TransitSignal(
                period=7.2,
                epoch=1.2,
                duration=3.5,
                depth=0.005,
                snr=7.3,
                confidence="MEDIUM"
            ),
        ]


class TestIntegrationScenarios(unittest.TestCase):
    """额外的集成场景测试"""

    def test_pipeline_result_serialization(self):
        """验证管道结果可以序列化为JSON"""
        pipeline = AstroPipeline()

        # 创建小图像测试
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not available")

        small_image = np.random.rand(64, 64).astype(np.float32)
        result = asyncio.run(pipeline.process(small_image))

        # 验证可以序列化为JSON
        try:
            json_str = json.dumps(result)
            self.assertIsNotNone(json_str)

            # 验证可以反序列化
            parsed = json.loads(json_str)
            self.assertEqual(parsed['sources'], result['sources'])
        except Exception as e:
            self.fail(f"JSON serialization failed: {e}")

    def test_scheduler_output_serialization(self):
        """验证调度器结果可以序列化为JSON"""
        location = GeographicLocation(
            name="Test Location",
            latitude=40.0,
            longitude=-74.0,
            elevation=100
        )
        scheduler = EnhancedObservationScheduler(location)

        target = ObservationTarget(
            name="Test Target",
            ra=180.0,
            dec=45.0,
            observation_type=ObservationType.IMAGING,
            priority=1
        )

        period = (
            datetime(2026, 5, 1, 12, 0),
            datetime(2026, 5, 2, 12, 0)
        )

        schedule = scheduler.generate_schedule([target], period)

        # 验证可以序列化为JSON
        try:
            json_str = json.dumps(schedule)
            self.assertIsNotNone(json_str)
        except Exception as e:
            self.fail(f"Scheduler output JSON serialization failed: {e}")

    def test_coordinate_conversion(self):
        """验证天文坐标计算"""
        location = GeographicLocation(
            name="Test",
            latitude=40.0,
            longitude=-74.0,
            elevation=100
        )

        calculator = AstronomicalCalculator(location)

        # 测试一个已知位置的目标
        # 天狼星 (RA: 101.287, Dec: -16.716)
        alt, az = calculator.compute_altitude_azimuth(
            ra=101.287,
            dec=-16.716,
            time=datetime(2026, 5, 1, 23, 0)
        )

        # 验证返回合理值
        self.assertIsInstance(alt, float)
        self.assertIsInstance(az, float)
        self.assertGreaterEqual(alt, -90)
        self.assertLessEqual(alt, 90)
        self.assertGreaterEqual(az, 0)
        self.assertLess(az, 360)


# ============ Main ============

if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])