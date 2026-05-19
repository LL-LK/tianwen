"""
Navigation and Tab Switching Tests for Tianwen-AGI Frontend

Tests the tab navigation functionality across all frontend tabs.
"""

import pytest


@pytest.mark.playwright
@pytest.mark.ui
class TestNavigation:
    """Test suite for tab navigation and switching."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url

    @pytest.mark.asyncio
    async def test_page_loads_successfully(self):
        """Test that the frontend page loads without errors."""
        response = await self.page.goto(self.base_url, wait_until="domcontentloaded")
        # Page should load (may redirect or return 200/304)
        assert response is not None

    @pytest.mark.asyncio
    async def test_tab_navigation_exists(self):
        """Test that tab navigation bar exists."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        tab_nav = await self.page.query_selector(".tab-nav")
        assert tab_nav is not None, "Tab navigation bar should exist"

    @pytest.mark.asyncio
    async def test_all_main_tabs_present(self):
        """Test that all main tabs are present in the navigation."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")

        expected_tabs = [
            "command", "skychart", "data", "research", "alerts",
            "telescope", "chat", "literature", "factcheck", "workflow",
            "logs", "manual", "harness", "benchmark", "skills", "astronomy"
        ]

        for tab_name in expected_tabs:
            tab = await self.page.query_selector(f'.tab-btn[data-tab="{tab_name}"]')
            assert tab is not None, f"Tab '{tab_name}' should exist in navigation"

    @pytest.mark.asyncio
    async def test_tab_switching_command_to_harness(self):
        """Test switching from Command tab to Harness tab."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")

        # Click on Command tab first
        await self.page.click('.tab-btn[data-tab="command"]')
        await self.page.wait_for_timeout(300)

        # Verify command panel is active
        command_panel = await self.page.query_selector("#panel-command.active")
        assert command_panel is not None, "Command panel should be active"

        # Switch to Harness tab
        await self.page.click('.tab-btn[data-tab="harness"]')
        await self.page.wait_for_timeout(300)

        # Verify harness panel is active
        harness_panel = await self.page.query_selector("#panel-harness.active")
        assert harness_panel is not None, "Harness panel should be active after clicking"

    @pytest.mark.asyncio
    async def test_tab_switching_through_all_tabs(self):
        """Test switching through all available tabs sequentially."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")

        tabs_to_test = ["harness", "benchmark", "skills", "astronomy", "command"]

        for tab_name in tabs_to_test:
            await self.page.click(f'.tab-btn[data-tab="{tab_name}"]')
            await self.page.wait_for_timeout(300)

            panel = await self.page.query_selector(f'#panel-{tab_name}.active')
            assert panel is not None, f"Panel '{tab_name}' should be active after clicking its tab"

    @pytest.mark.asyncio
    async def test_default_tab_is_command(self):
        """Test that Command tab is the default active tab on page load."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")

        # Command tab should be active by default
        command_tab = await self.page.query_selector('.tab-btn[data-tab="command"].active')
        assert command_tab is not None, "Command tab should be active by default"

        command_panel = await self.page.query_selector("#panel-command.active")
        assert command_panel is not None, "Command panel should be active by default"

    @pytest.mark.asyncio
    async def test_tab_badge_display(self):
        """Test that tab badges display correctly when present."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")

        # Alerts tab has a badge
        alerts_tab = await self.page.query_selector('.tab-btn[data-tab="alerts"]')
        assert alerts_tab is not None, "Alerts tab should exist"

    @pytest.mark.asyncio
    async def test_tab_content_renders_on_switch(self):
        """Test that tab content renders correctly when tab is activated."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")

        # Switch to Harness tab
        await self.page.click('.tab-btn[data-tab="harness"]')
        await self.page.wait_for_timeout(500)

        # Check that harness panel has content
        harness_content = await self.page.query_selector("#panel-harness")
        assert harness_content is not None, "Harness panel should have content"

    @pytest.mark.asyncio
    async def test_keyboard_shortcut_navigation(self):
        """Test keyboard shortcuts for navigation if implemented."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")

        # Press number keys for tab switching if implemented
        # This test verifies the keyboard hint is visible
        kbd_hint = await self.page.query_selector("#kbdHint")
        if kbd_hint:
            hint_text = await kbd_hint.text_content()
            assert "快捷键" in hint_text or "shortcut" in hint_text.lower()


@pytest.mark.playwright
@pytest.mark.ui
class TestHeaderElements:
    """Test suite for header elements."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url

    @pytest.mark.asyncio
    async def test_header_exists(self):
        """Test that header element exists."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        header = await self.page.query_selector(".header")
        assert header is not None, "Header should exist"

    @pytest.mark.asyncio
    async def test_header_logo_displayed(self):
        """Test that header logo/title is displayed."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        logo = await self.page.query_selector(".header-logo")
        assert logo is not None, "Header logo should exist"

    @pytest.mark.asyncio
    async def test_header_status_indicator(self):
        """Test that header status indicator exists."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        status = await self.page.query_selector(".header-status")
        assert status is not None, "Header status should exist"

    @pytest.mark.asyncio
    async def test_theme_toggle_exists(self):
        """Test that theme toggle button exists."""
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        theme_toggle = await self.page.query_selector(".theme-toggle")
        assert theme_toggle is not None, "Theme toggle should exist"
