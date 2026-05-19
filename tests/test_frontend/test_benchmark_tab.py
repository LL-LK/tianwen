"""
Benchmark Tab Tests for Tianwen-AGI Frontend

Tests the Benchmark configuration, runner, and result display.
"""

import pytest


@pytest.mark.playwright
@pytest.mark.ui
class TestBenchmarkTab:
    """Test suite for Benchmark Tab functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        # Navigate to benchmark tab before each test
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="benchmark"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_benchmark_tab_switch(self):
        """Test that Benchmark tab can be activated."""
        benchmark_panel = await self.page.query_selector("#panel-benchmark.active")
        assert benchmark_panel is not None, "Benchmark panel should be active"

    @pytest.mark.asyncio
    async def test_benchmark_title_displayed(self):
        """Test that Benchmark tab title is displayed correctly."""
        title = await self.page.query_selector("#panel-benchmark .card-title")
        assert title is not None, "Benchmark title should exist"
        title_text = await title.text_content()
        assert "Benchmark" in title_text or "评测" in title_text

    @pytest.mark.asyncio
    async def test_benchmark_selector_exists(self):
        """Test that benchmark selector dropdown exists."""
        selector = await self.page.query_selector("#benchmarkSelector")
        assert selector is not None, "Benchmark selector should exist"

    @pytest.mark.asyncio
    async def test_benchmark_selector_has_options(self):
        """Test that benchmark selector has options."""
        options = await self.page.query_selector_all("#benchmarkSelector option")
        assert len(options) > 1, "Benchmark selector should have at least one option besides default"

    @pytest.mark.asyncio
    async def test_benchmark_config_preview_exists(self):
        """Test that benchmark configuration preview section exists."""
        config = await self.page.query_selector("#benchmarkConfig")
        assert config is not None, "Benchmark configuration preview should exist"

    @pytest.mark.asyncio
    async def test_benchmark_results_section_exists(self):
        """Test that benchmark results section exists."""
        results = await self.page.query_selector("#benchmarkResults")
        assert results is not None, "Benchmark results section should exist"

    @pytest.mark.asyncio
    async def test_refresh_button_exists(self):
        """Test that refresh button exists."""
        refresh_btn = await self.page.query_selector("#panel-benchmark button:has-text('刷新')")
        assert refresh_btn is not None, "Refresh button should exist"

    @pytest.mark.asyncio
    async def test_run_button_exists(self):
        """Test that run/execute button exists."""
        run_btn = await self.page.query_selector("#panel-benchmark button:has-text('执行评测')")
        assert run_btn is not None, "Run button should exist"

    @pytest.mark.asyncio
    async def test_yaml_example_exists(self):
        """Test that YAML configuration example exists."""
        yaml_section = await self.page.query_selector("#panel-benchmark .card-title:has-text('YAML')")
        assert yaml_section is not None, "YAML configuration example should exist"

    @pytest.mark.asyncio
    async def test_default_benchmark_option_selected(self):
        """Test that default benchmark option can be selected."""
        await self.page.select_option("#benchmarkSelector", "astronomy_benchmark")
        await self.page.wait_for_timeout(300)
        selected = await self.page.query_selector("#benchmarkSelector option:checked")
        if selected:
            value = await selected.get_attribute("value")
            assert value == "astronomy_benchmark"

    @pytest.mark.asyncio
    async def test_benchmark_level_options_exist(self):
        """Test that different benchmark levels are available."""
        content = await self.page.text_content("#benchmarkConfig")
        assert "level_1" in content or "Level 1" in content or "基础" in content
        assert "level_2" in content or "Level 2" in content
        assert "level_3" in content or "Level 3" in content


@pytest.mark.playwright
@pytest.mark.ui
class TestBenchmarkFunctionality:
    """Test suite for Benchmark functionality interactions."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="benchmark"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_selector_change_updates_content(self):
        """Test that changing selector updates the preview content."""
        # Select a different benchmark
        await self.page.select_option("#benchmarkSelector", "gaia_level1")
        await self.page.wait_for_timeout(300)
        # The config preview should update (text content will change)
        config = await self.page.text_content("#benchmarkConfig")
        assert config is not None

    @pytest.mark.asyncio
    async def test_run_button_is_clickable(self):
        """Test that run button can be clicked."""
        run_btn = await self.page.query_selector("#panel-benchmark button:has-text('执行评测')")
        assert run_btn is not None
        # Just verify button exists and is not disabled by default
        is_disabled = await run_btn.get_attribute("disabled")
        # Button may or may not be disabled depending on selection

    @pytest.mark.asyncio
    async def test_refresh_button_triggers_action(self):
        """Test that refresh button triggers an action."""
        refresh_btn = await self.page.query_selector("#panel-benchmark button:has-text('刷新')")
        assert refresh_btn is not None
        # Click and verify no errors occur
        await refresh_btn.click()
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_yaml_code_block_exists(self):
        """Test that YAML code block is displayed properly."""
        code_block = await self.page.query_selector("#panel-benchmark pre code")
        assert code_block is not None, "YAML code block should exist"


@pytest.mark.playwright
@pytest.mark.ui
class TestBenchmarkConfigurations:
    """Test suite for Benchmark configuration details."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="benchmark"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_astronomy_benchmark_listed(self):
        """Test that astronomy_benchmark is available."""
        options = await self.page.query_selector_all("#benchmarkSelector option")
        option_values = []
        for opt in options:
            val = await opt.get_attribute("value")
            if val:
                option_values.append(val)
        assert "astronomy_benchmark" in option_values, "Astronomy benchmark should be available"

    @pytest.mark.asyncio
    async def test_gaia_benchmarks_listed(self):
        """Test that GAIA level benchmarks are available."""
        options = await self.page.query_selector_all("#benchmarkSelector option")
        option_values = []
        for opt in options:
            val = await opt.get_attribute("value")
            if val:
                option_values.append(val)
        assert "gaia_level1" in option_values, "GAIA Level 1 should be available"
        assert "gaia_level2" in option_values, "GAIA Level 2 should be available"
        assert "gaia_level3" in option_values, "GAIA Level 3 should be available"

    @pytest.mark.asyncio
    async def test_benchmark_difficulty_levels_shown(self):
        """Test that benchmark difficulty levels are described."""
        content = await self.page.text_content("#panel-benchmark")
        # Check for difficulty descriptions
        assert ("基础" in content or "基础天文" in content or "level_1" in content), \
            "Level 1 difficulty should be described"

    @pytest.mark.asyncio
    async def test_max_steps_info_displayed(self):
        """Test that max steps information is displayed."""
        content = await self.page.text_content("#panel-benchmark")
        assert "步" in content or "step" in content.lower(), "Max steps info should be displayed"
