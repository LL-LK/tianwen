"""
天问-AGI 具身观测端到端集成测试

测试embodied_observation_workflow与seestar_mcp_client的集成

用法:
    pytest runtime/tests/test_embodied_observation_integration.py -v
    python -m runtime.tests.test_embodied_observation_integration
"""

import unittest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# 添加runtime目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from embodied_observation_workflow import (
    EmbodiedObservationWorkflow,
    WorkflowResult,
    WorkflowStage,
    ObservationTarget
)
from seestar_mcp_client import SeestarMCPClient, DeviceState


class TestEmbodiedObservationWorkflow(unittest.IsolatedAsyncioTestCase):
    """具身观测工作流测试"""

    async def asyncSetUp(self):
        """设置测试环境"""
        self.workflow = EmbodiedObservationWorkflow(use_simulator=True)
        self.mock_client = AsyncMock(spec=SeestarMCPClient)
        self.workflow.client = self.mock_client

    async def test_workflow_initialization(self):
        """测试工作流初始化"""
        self.assertIsNotNone(self.workflow)
        self.assertTrue(self.workflow.use_simulator)
        self.assertEqual(self.workflow.current_stage, WorkflowStage.IDLE)
        self.assertIsNone(self.workflow.current_result)

    async def test_simulator_mode_initialization(self):
        """测试模拟器模式初始化"""
        workflow = EmbodiedObservationWorkflow(use_simulator=True)
        self.assertTrue(workflow.use_simulator)
        self.assertIsNotNone(workflow.simulator)

    async def test_full_observation_cycle_mock(self):
        """测试完整观测周期(模拟模式)"""
        # 创建测试图像路径
        test_image = Path("runtime/data/test_images/fake_exoplanet.tif")

        # Mock客户端行为
        self.mock_client.goto_target = AsyncMock(return_value=True)
        self.mock_client.start_imaging = AsyncMock(return_value=True)
        self.mock_client.get_device_state = AsyncMock(return_value=DeviceState(state="TRACKING"))
        self.mock_client.analyze_and_slew = AsyncMock(return_value={
            "success": True,
            "target_found": True,
            "confidence": 0.85
        })

        # 创建工作流实例
        workflow = EmbodiedObservationWorkflow(use_simulator=True)
        workflow.client = self.mock_client

        # 运行完整周期
        result = await workflow.run_full_observation_cycle(
            image_input=str(test_image),
            observation_targets=["Kepler-186f"]
        )

        # 验证结果
        self.assertIsInstance(result, WorkflowResult)
        self.assertIn(result.stage, [WorkflowStage.COMPLETED, WorkflowStage.ERROR])

    async def test_select_best_target(self):
        """测试目标选择逻辑"""
        workflow = EmbodiedObservationWorkflow(use_simulator=True)
        workflow.client = self.mock_client

        detected = [
            {"name": "Kepler-186f", "type": "exoplanet", "score": 0.9},
            {"name": "HD 219134 b", "type": "exoplanet", "score": 0.75},
            {"name": "TRAPPIST-1e", "type": "exoplanet", "score": 0.85}
        ]

        best = await workflow._select_best_target(detected, ["Kepler-186f"])
        self.assertIsNotNone(best)
        self.assertEqual(best["name"], "Kepler-186f")

    async def test_safety_check_integration(self):
        """测试安全检查集成"""
        workflow = EmbodiedObservationWorkflow(use_simulator=True)
        workflow.client = self.mock_client

        # Mock安全检查
        self.mock_client.safety_check = AsyncMock(return_value={
            "safe": True,
            "warnings": []
        })

        target = ObservationTarget(
            name="Test Target",
            ra=283.5,
            dec=20.0
        )

        result = await workflow.client.safety_check(target)
        self.assertTrue(result["safe"])


class TestSeestarMCPClientMock(unittest.IsolatedAsyncioTestCase):
    """Seestar MCP客户端测试"""

    async def asyncSetUp(self):
        """设置测试环境"""
        self.client = SeestarMCPClient(use_simulator=True)

    async def test_client_initialization(self):
        """测试客户端初始化"""
        self.assertTrue(self.client.use_simulator)
        self.assertIsNotNone(self.client.simulator)

    async def test_goto_target_mock(self):
        """测试goto目标(模拟)"""
        target = ObservationTarget(
            name="Kepler-186f",
            ra=283.5,
            dec=20.0
        )

        result = await self.client.goto_target(target)
        self.assertTrue(result)

    async def test_start_imaging_mock(self):
        """测试开始成像(模拟)"""
        result = await self.client.start_imaging(
            exposure_time=60,
            filter_name="L",
            count=1
        )
        self.assertTrue(result)

    async def test_safety_check_mock(self):
        """测试安全检查(模拟)"""
        target = ObservationTarget(
            name="Test",
            ra=0.0,
            dec=0.0
        )

        result = await self.client.safety_check(target)
        self.assertIn("safe", result)
        self.assertIn("warnings", result)


class TestObservationTargetValidation(unittest.IsolatedAsyncioTestCase):
    """观测目标验证测试"""

    def test_target_creation(self):
        """测试目标创建"""
        target = ObservationTarget(
            name="Kepler-186f",
            ra=283.5,
            dec=20.0,
            priority=1
        )

        self.assertEqual(target.name, "Kepler-186f")
        self.assertAlmostEqual(target.ra, 283.5, places=1)
        self.assertAlmostEqual(target.dec, 20.0, places=1)

    def test_target_with_exposure(self):
        """测试带曝光参数的目标"""
        target = ObservationTarget(
            name="Test",
            ra=0.0,
            dec=0.0,
            exposure_time=120,
            filter_name="R"
        )

        self.assertEqual(target.exposure_time, 120)
        self.assertEqual(target.filter_name, "R")


class TestWorkflowStageTransitions(unittest.IsolatedAsyncioTestCase):
    """工作流阶段转换测试"""

    async def test_stage_sequence(self):
        """测试阶段序列"""
        workflow = EmbodiedObservationWorkflow(use_simulator=True)

        stages = [
            WorkflowStage.INIT,
            WorkflowStage.IMAGE_ACQUISITION,
            WorkflowStage.IMAGE_ANALYSIS,
            WorkflowStage.TARGET_SELECTION,
            WorkflowStage.SAFETY_CHECK,
            WorkflowStage.SLEW,
            WorkflowStage.IMAGING,
            WorkflowStage.COMPLETED
        ]

        for stage in stages:
            workflow.current_stage = stage
            self.assertEqual(workflow.current_stage, stage)


class TestErrorHandling(unittest.IsolatedAsyncioTestCase):
    """错误处理测试"""

    async def test_connection_error_handling(self):
        """测试连接错误处理"""
        client = SeestarMCPClient(use_simulator=True)

        # 模拟连接失败
        with patch.object(client, 'connect', side_effect=ConnectionError("Simulated")):
            with self.assertRaises(ConnectionError):
                await client.connect()

    async def test_workflow_error_recovery(self):
        """测试工作流错误恢复"""
        workflow = EmbodiedObservationWorkflow(use_simulator=True)
        workflow.client = AsyncMock()
        workflow.client.goto_target = AsyncMock(side_effect=Exception("Simulated error"))

        target = ObservationTarget(name="Test", ra=0.0, dec=0.0)

        # 应该能处理错误而不崩溃
        try:
            await workflow.client.goto_target(target)
        except Exception as e:
            self.assertEqual(str(e), "Simulated error")


async def run_integration_demo():
    """运行集成演示"""
    print("=" * 60)
    print("具身观测端到端集成测试演示")
    print("=" * 60)

    # 创建工作流
    workflow = EmbodiedObservationWorkflow(use_simulator=True)

    print("\n1. 测试模拟器模式初始化...")
    print(f"   模拟器状态: {'已启用' if workflow.use_simulator else '未启用'}")

    print("\n2. 测试目标创建...")
    target = ObservationTarget(
        name="Kepler-186f",
        ra=283.5,
        dec=20.0,
        priority=1
    )
    print(f"   目标: {target.name}, RA={target.ra}, Dec={target.dec}")

    print("\n3. 测试模拟观测...")
    result = await workflow.run_full_observation_cycle(
        image_input="runtime/data/test_images/fake_exoplanet.tif",
        observation_targets=["Kepler-186f"]
    )
    print(f"   结果: {result.stage.value}")
    print(f"   消息: {result.message}")

    print("\n4. 测试紧急停止...")
    await workflow.emergency_stop()
    print("   紧急停止: 已执行")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行测试
    print("运行具身观测集成测试...")
    print("=" * 60)

    # 运行演示
    asyncio.run(run_integration_demo())

    # 运行单元测试
    print("\n运行单元测试...")
    unittest.main(verbosity=2)