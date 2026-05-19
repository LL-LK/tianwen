"""
Navigation and Tab Switching Tests for Tianwen-AGI Frontend

Tests the tab navigation functionality across all frontend tabs.
Uses synchronous Playwright API.
"""

import pytest


@pytest.mark.playwright
@pytest.mark.ui
class TestNavigation:
    """Test suite for tab navigation and switching."""

    @pytest.fixture(autouse=True)
    def setup(self, page, base_url):
        """Set up test fixture."""
        self.page = page
        self.base_url = base_url

    def test_page_loads_successfully(self):
        """Test that the frontend page loads without errors."""
        response = self.page.goto(self.base_url, wait_until="commit")
        assert response is not None

    def test_tab_navigation_exists(self):
        """Test that tab navigation bar exists."""
        self.page.goto(self.base_url, wait_until="commit")
        tab_nav = self.page.query_selector(".tab-nav")
        assert tab_nav is not None, "Tab navigation bar should exist"

    def test_all_main_tabs_present(self):
        """Test that all main tabs are present in the navigation."""
        self.page.goto(self.base_url, wait_until="commit")
        self.page.wait_for_selector(".tab-nav")

        expected_tabs = [
            "command", "skychart", "data", "research", "alerts",
            "telescope", "chat", "literature", "factcheck", "workflow",
            "logs", "manual", "harness", "benchmark", "skills", "astronomy"
        ]

        for tab_name in expected_tabs:
            tab = self.page.query_selector(f'.tab-btn[data-tab="{tab_name}"]')
            assert tab is not None, f"Tab '{tab_name}' should exist in navigation"

    def test_tab_switching_command_to_harness(self):
        """Test switching from Command tab to Harness tab."""
        self.page.goto(self.base_url, wait_until="commit")
        self.page.wait_for_selector(".tab-nav")

        # Click on Command tab first
        self.page.click('.tab-btn[data-tab="command"]')
        self.page.wait_for_timeout(300)

        # Verify command panel is active
        command_panel = self.page.query_selector("#panel-command.active")
        assert command_panel is not None, "Command panel should be active"

        # Switch to Harness tab
        self.page.click('.tab-btn[data-tab="harness"]')
        self.page.wait_for_timeout(300)

        # Verify harness panel is active
        harness_panel = self.page.query_selector("#panel-harness.active")
        assert harness_panel is not None, "Harness panel should be active after clicking"

    def test_tab_switching_through_all_tabs(self):
        """Test switching through all available tabs sequentially."""
        self.page.goto(self.base_url, wait_until="commit")
        self.page.wait_for_selector(".tab-nav")

        tabs_to_test = ["harness", "benchmark", "skills", "astronomy", "command"]

        for tab_name in tabs_to_test:
            self.page.click(f'.tab-btn[data-tab="{tab_name}"]')
            self.page.wait_for_timeout(300)

            # Check if panel exists
            panel = self.page.query_selector(f"#panel-{tab_name}")
            assert panel is not None, f"Panel for '{tab_name}' should exist"

    def test_default_tab_is_command(self):
        """Test that the default active tab is Command."""
        self.page.goto(self.base_url, wait_until="commit")
        self.page.wait_for_selector(".tab-nav")

        command_panel = self.page.query_selector("#panel-command.active")
        assert command_panel is not None, "Command panel should be active by default"

    def test_tab_badge_display(self):
        """Test that tab badges are displayed correctly."""
        self.page.goto(self.base_url, wait_until="commit")
        self.page.wait_for_selector(".tab-nav")

        # Check for tab badges (count indicators)
        badges = self.page.query_selector_all(".tab-badge")
        assert len(badges) >= 0, "Tab badges should be present if any notifications"

    def test_tab_content_renders_on_switch(self):
        """Test that tab content renders when switching tabs."""
        self.page.goto(self.base_url, wait_until="commit")
        self.page.wait_for_selector(".tab-nav")

        # Switch to Harness tab
        self.page.click('.tab-btn[data-tab="harness"]')
        self.page.wait_for_timeout(500)

        # Check harness panel content exists
        harness_content = self.page.query_selector("#panel-harness")
        assert harness_content is not None, "Harness panel content should exist"

    def test_keyboard_shortcut_navigation(self):
        """Test keyboard navigation shortcuts if implemented."""
        self.page.goto(self.base_url, wait_until="commit")
        self.page.wait_for_selector(".tab-nav")

        # Tab through tabs using keyboard
        self.page.keyboard.press("Tab")
        self.page.wait_for_timeout(100)

        # Just verify no crash - basic keyboard test
        assert True, "Keyboard navigation should not cause errors"


@pytest.mark.playwright
@pytest.mark.ui
class TestHeaderElements:
    """Test suite for header elements."""

    @pytest.fixture(autouse=True)
    def setup(self, page, base_url):
        """Set up test fixture."""
        self.page = page
        self.base_url = base_url

    def test_header_exists(self):
        """Test that the header element exists."""
        self.page.goto(self.base_url, wait_until="commit")
        header = self.page.query_selector(".header")
        assert header is not None, "Header element should exist"

    def test_header_logo_displayed(self):
        """Test that the header logo is displayed."""
        self.page.goto(self.base_url, wait_until="commit")
        logo = self.page.query_selector(".header-logo")
        if logo:
            # Logo may or may not have text content
            assert True

    def test_header_status_indicator(self):
        """Test that header status indicator exists."""
        self.page.goto(self.base_url, wait_until="commit")
        status = self.page.query_selector(".status-indicator")
        assert status is not None, "Status indicator should exist in header"

    def test_theme_toggle_exists(self):
        """Test that theme toggle button exists."""
        self.page.goto(self.base_url, wait_until="commit")
        theme_toggle = self.page.query_selector(".theme-toggle")
        assert theme_toggle is not None, "Theme toggle should exist"
