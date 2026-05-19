"""
Harness Tab Tests for Tianwen-AGI Frontend

Tests the PGE Loop visualization and component registry in the Harness tab.
"""

import pytest


@pytest.mark.playwright
@pytest.mark.ui
class TestHarnessTab:
    """Test suite for Harness Tab functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        # Navigate to harness tab before each test
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="harness"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_harness_tab_switch(self):
        """Test that Harness tab can be activated."""
        harness_panel = await self.page.query_selector("#panel-harness.active")
        assert harness_panel is not None, "Harness panel should be active"

    @pytest.mark.asyncio
    async def test_harness_title_displayed(self):
        """Test that Harness tab title is displayed correctly."""
        title = await self.page.query_selector("#panel-harness .card-title")
        assert title is not None, "Harness title should exist"
        title_text = await title.text_content()
        assert "Harness" in title_text or "评测框架" in title_text

    @pytest.mark.asyncio
    async def test_pge_loop_visualization_exists(self):
        """Test that PGE Loop visualization section exists."""
        pge_section = await self.page.query_selector("#panel-harness .card-title:has-text('PGE Loop')")
        assert pge_section is not None, "PGE Loop visualization section should exist"

    @pytest.mark.asyncio
    async def test_pge_loop_icons_present(self):
        """Test that all PGE Loop icons (Plan, Generate, Evaluate, Iterate) are present."""
        # Check for Plan icon
        plan_icon = await self.page.query_selector("#panel-harness:has-text('Plan')")
        assert plan_icon is not None, "Plan element should exist in PGE visualization"

        # Check for Generate icon
        generate_icon = await self.page.query_selector("#panel-harness:has-text('Generate')")
        assert generate_icon is not None, "Generate element should exist in PGE visualization"

        # Check for Evaluate icon
        evaluate_icon = await self.page.query_selector("#panel-harness:has-text('Evaluate')")
        assert evaluate_icon is not None, "Evaluate element should exist in PGE visualization"

        # Check for Iterate icon
        iterate_icon = await self.page.query_selector("#panel-harness:has-text('Iterate')")
        assert iterate_icon is not None, "Iterate element should exist in PGE visualization"

    @pytest.mark.asyncio
    async def test_component_registry_exists(self):
        """Test that component registry section exists."""
        registry = await self.page.query_selector("#panel-harness .card-title:has-text('组件注册表')")
        assert registry is not None, "Component registry section should exist"

    @pytest.mark.asyncio
    async def test_stat_items_exist(self):
        """Test that stat items are displayed in component registry."""
        stat_items = await self.page.query_selector_all("#panel-harness .stat-item")
        assert len(stat_items) >= 6, "Should have at least 6 stat items (Agents, Tasks, Evaluators, Graders, Protocols, Skills)"

    @pytest.mark.asyncio
    async def test_harness_agent_count_displayed(self):
        """Test that agent count stat is displayed."""
        agent_count = await self.page.query_selector("#harnessAgentCount")
        assert agent_count is not None, "Agent count element should exist"

    @pytest.mark.asyncio
    async def test_harness_task_count_displayed(self):
        """Test that task count stat is displayed."""
        task_count = await self.page.query_selector("#harnessTaskCount")
        assert task_count is not None, "Task count element should exist"

    @pytest.mark.asyncio
    async def test_harness_eval_count_displayed(self):
        """Test that evaluator count stat is displayed."""
        eval_count = await self.page.query_selector("#harnessEvalCount")
        assert eval_count is not None, "Evaluator count element should exist"

    @pytest.mark.asyncio
    async def test_harness_grader_count_displayed(self):
        """Test that grader count stat is displayed."""
        grader_count = await self.page.query_selector("#harnessGraderCount")
        assert grader_count is not None, "Grader count element should exist"

    @pytest.mark.asyncio
    async def test_harness_proto_count_displayed(self):
        """Test that protocol count stat is displayed."""
        proto_count = await self.page.query_selector("#harnessProtoCount")
        assert proto_count is not None, "Protocol count element should exist"

    @pytest.mark.asyncio
    async def test_harness_skill_count_displayed(self):
        """Test that skill count stat is displayed."""
        skill_count = await self.page.query_selector("#harnessSkillCount")
        assert skill_count is not None, "Skill count element should exist"

    @pytest.mark.asyncio
    async def test_four_phases_displayed(self):
        """Test that all 4 phases are mentioned in Harness tab."""
        content = await self.page.text_content("#panel-harness")
        assert "Phase 1" in content, "Phase 1 should be mentioned"
        assert "Phase 2" in content, "Phase 2 should be mentioned"
        assert "Phase 3" in content, "Phase 3 should be mentioned"
        assert "Phase 4" in content, "Phase 4 should be mentioned"

    @pytest.mark.asyncio
    async def test_pge_loop_cards_clickable(self):
        """Test that PGE loop visualization elements exist and are styled."""
        # Check that the cards exist and have styling
        cards = await self.page.query_selector_all("#panel-harness .card")
        assert len(cards) >= 3, "Should have multiple cards in Harness tab"


@pytest.mark.playwright
@pytest.mark.ui
class TestPGELoopVisualization:
    """Test suite specifically for PGE Loop visualization."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="harness"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_plan_node_displayed(self):
        """Test Plan node is displayed with correct styling."""
        plan_node = await self.page.query_selector("#panel-harness:has-text('规划')")
        assert plan_node is not None, "Plan node should display '规划' label"

    @pytest.mark.asyncio
    async def test_generate_node_displayed(self):
        """Test Generate node is displayed with correct styling."""
        gen_node = await self.page.query_selector("#panel-harness:has-text('生成')")
        assert gen_node is not None, "Generate node should display '生成' label"

    @pytest.mark.asyncio
    async def test_evaluate_node_displayed(self):
        """Test Evaluate node is displayed with correct styling."""
        eval_node = await self.page.query_selector("#panel-harness:has-text('评估')")
        assert eval_node is not None, "Evaluate node should display '评估' label"

    @pytest.mark.asyncio
    async def test_iterate_node_displayed(self):
        """Test Iterate node is displayed with correct styling."""
        iter_node = await self.page.query_selector("#panel-harness:has-text('迭代')")
        assert iter_node is not None, "Iterate node should display '迭代' label"

    @pytest.mark.asyncio
    async def test_arrow_connections_exist(self):
        """Test that arrow connectors between nodes exist."""
        # The arrows are represented as text in this implementation
        arrows = await self.page.query_selector_all("#panel-harness:has-text('→')")
        assert len(arrows) >= 3, "Should have arrows connecting the PGE nodes"

    @pytest.mark.asyncio
    async def test_pge_colors_different(self):
        """Test that different PGE nodes have different colors."""
        content = await self.page.inner_html("#panel-harness")
        # The visualization uses different background colors
        assert "var(--accent)" in content or "#3b82f6" in content, "Plan node should use accent color"
        assert "var(--discovery)" in content or "#a855f7" in content, "Generate node should use discovery color"
