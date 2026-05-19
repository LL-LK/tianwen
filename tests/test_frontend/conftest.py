"""
Playwright configuration and fixtures for Tianwen-AGI frontend tests.
Uses existing MCP browser at ~/.cache/ms-playwright/chromium-1217
"""

import pytest
from playwright.sync_api import sync_playwright


# Browser executable path (MCP's installed chromium)
CHROMIUM_PATH = "/home/l2140/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome"


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "playwright: mark test as a playwright test"
    )
    config.addinivalue_line(
        "markers", "ui: mark test as a UI test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Test configuration
FRONTEND_URL = "https://tianwen-agi-production.up.railway.app"
LOCAL_FRONTEND_URL = "http://localhost:3000"
FALLBACK_URL = FRONTEND_URL


@pytest.fixture(scope="session")
def browser():
    """Launch Chromium browser for tests using existing MCP browser."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        executable_path=CHROMIUM_PATH
    )
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture(scope="session")
def browser_context(browser):
    """Create a browser context."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        locale="zh-CN",
    )
    yield context
    context.close()


@pytest.fixture
def page(browser_context):
    """Create a new page using browser context."""
    page = browser_context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def frontend_url():
    """Get the frontend URL for testing."""
    return FALLBACK_URL


@pytest.fixture(scope="session")
def base_url():
    """Base URL for all tests."""
    return FALLBACK_URL


class TabSelectors:
    """CSS selectors for frontend tabs."""
    # Tab navigation
    TAB_NAV = ".tab-nav"
    TAB_BTN = ".tab-btn"
    
    # Specific tabs
    COMMAND_TAB = '[data-tab="command"]'
    HARNESS_TAB = '[data-tab="harness"]'
    BENCHMARK_TAB = '[data-tab="benchmark"]'
    SKILLS_TAB = '[data-tab="skills"]'
    ASTRONOMY_TAB = '[data-tab="astronomy"]'
    SKYCHART_TAB = '[data-tab="skychart"]'
    DATA_TAB = '[data-tab="data"]'
    RESEARCH_TAB = '[data-tab="research"]'
    ALERTS_TAB = '[data-tab="alerts"]'
    TELESCOPE_TAB = '[data-tab="telescope"]'
    CHAT_TAB = '[data-tab="chat"]'
    LITERATURE_TAB = '[data-tab="literature"]'
    FACTCHECK_TAB = '[data-tab="factcheck"]'
    WORKFLOW_TAB = '[data-tab="workflow"]'
    LOGS_TAB = '[data-tab="logs"]'
    MANUAL_TAB = '[data-tab="manual"]'
    
    # Header elements
    HEADER = ".header"
    HEADER_LOGO = ".header-logo"
    HEADER_STATUS = ".status-indicator"
    THEME_TOGGLE = ".theme-toggle"
    
    # Harness specific
    HARNESS_PANEL = "#panel-harness"
    PGE_FLOW = ".pge-flow"
    AGENT_STATUS = ".agent-status"
    
    # Benchmark specific
    BENCHMARK_PANEL = "#panel-benchmark"
    BENCHMARK_RUNS = ".benchmark-runs"
    BENCHMARK_CHARTS = ".benchmark-charts"
    
    # Skills specific
    SKILLS_PANEL = "#panel-skills"
    SKILL_CARD = ".skill-card"
    SKILL_SEARCH = ".skill-search"
    
    # Astronomy specific
    ASTRONOMY_PANEL = "#panel-astronomy"
    FITS_VIEWER = ".fits-viewer"
    COORD_DISPLAY = ".coord-display"


@pytest.fixture
def tab_selectors():
    """Fixture for tab selectors."""
    return TabSelectors()
