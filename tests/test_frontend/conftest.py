"""
Playwright configuration and fixtures for Tianwen-AGI frontend tests.
"""

import pytest
import asyncio
from pathlib import Path


# Test configuration
FRONTEND_URL = "https://tianwen-agi-production.up.railway.app"
LOCAL_FRONTEND_URL = "http://localhost:3000"
FALLBACK_URL = FRONTEND_URL


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


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def frontend_url():
    """Get the frontend URL for testing."""
    return FALLBACK_URL


@pytest.fixture(scope="session")
def base_url():
    """Base URL for all tests."""
    return FALLBACK_URL


@pytest.fixture
def page_with_timeout(page):
    """Page fixture with custom timeout settings."""
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)
    return page


@pytest.fixture
async def goto_page(page_with_timeout, base_url):
    """Navigate to the base URL and return the page."""
    await page_with_timeout.goto(base_url, wait_until="domcontentloaded")
    return page_with_timeout


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure browser context arguments for headless testing."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "locale": "zh-CN",
    }


class TabSelectors:
    """CSS selectors for frontend tabs."""
    # Tab navigation
    TAB_NAV = ".tab-nav"
    TAB_BTN = ".tab-btn"
    
    # Specific tabs
    COMMAND_TAB = '.tab-btn[data-tab="command"]'
    HARNESS_TAB = '.tab-btn[data-tab="harness"]'
    BENCHMARK_TAB = '.tab-btn[data-tab="benchmark"]'
    SKILLS_TAB = '.tab-btn[data-tab="skills"]'
    ASTRONOMY_TAB = '.tab-btn[data-tab="astronomy"]'
    SKYCHART_TAB = '.tab-btn[data-tab="skychart"]'
    DATA_TAB = '.tab-btn[data-tab="data"]'
    RESEARCH_TAB = '.tab-btn[data-tab="research"]'
    ALERTS_TAB = '.tab-btn[data-tab="alerts"]'
    TELESCOPE_TAB = '.tab-btn[data-tab="telescope"]'
    CHAT_TAB = '.tab-btn[data-tab="chat"]'
    LITERATURE_TAB = '.tab-btn[data-tab="literature"]'
    FACTCHECK_TAB = '.tab-btn[data-tab="factcheck"]'
    WORKFLOW_TAB = '.tab-btn[data-tab="workflow"]'
    LOGS_TAB = '.tab-btn[data-tab="logs"]'
    MANUAL_TAB = '.tab-btn[data-tab="manual"]'
    
    # Tab panels
    PANEL_COMMAND = "#panel-command"
    PANEL_HARNESS = "#panel-harness"
    PANEL_BENCHMARK = "#panel-benchmark"
    PANEL_SKILLS = "#panel-skills"
    PANEL_ASTRONOMY = "#panel-astronomy"


class HarnessSelectors:
    """CSS selectors for Harness tab."""
    CARD_TITLE = "#panel-harness .card-title"
    PGE_LOOP_VISUALIZATION = "#panel-harness .card:has(.card-title:has-text('PGE Loop'))"
    STAT_ITEMS = "#panel-harness .stat-item"
    HARNESS_AGENT_COUNT = "#harnessAgentCount"
    HARNESS_TASK_COUNT = "#harnessTaskCount"
    HARNESS_EVAL_COUNT = "#harnessEvalCount"
    HARNESS_GRADER_COUNT = "#harnessGraderCount"
    HARNESS_PROTO_COUNT = "#harnessProtoCount"
    HARNESS_SKILL_COUNT = "#harnessSkillCount"
    PLAN_ELEMENT = "#panel-harness .card:has-text('Plan')"
    GENERATE_ELEMENT = "#panel-harness .card:has-text('Generate')"
    EVALUATE_ELEMENT = "#panel-harness .card:has-text('Evaluate')"
    ITERATE_ELEMENT = "#panel-harness .card:has-text('Iterate')"


class BenchmarkSelectors:
    """CSS selectors for Benchmark tab."""
    BENCHMARK_SELECTOR = "#benchmarkSelector"
    BENCHMARK_CONFIG = "#benchmarkConfig"
    BENCHMARK_RESULTS = "#benchmarkResults"
    RUN_BUTTON = "#panel-benchmark button:has-text('执行评测')"
    REFRESH_BUTTON = "#panel-benchmark button:has-text('刷新')"
    SELECTOR_OPTIONS = "#benchmarkSelector option"


class SkillsSelectors:
    """CSS selectors for Skills tab."""
    SKILL_SEARCH_INPUT = "#skillSearchInput"
    SEARCH_BUTTON = "#panel-skills button:has-text('搜索')"
    SKILL_REGISTRY_LIST = "#skillRegistryList"
    SKILL_CARDS = "#skillRegistryList .card"
    REFRESH_BUTTON = "#panel-skills button:has-text('刷新')"


class AstronomySelectors:
    """CSS selectors for Astronomy tab."""
    ASTRONOMY_PANEL = "#panel-astronomy"
    FITS_PROTOCOL = "#panel-astronomy .card:has-text('FITS 协议')"
    TIME_DOMAIN_PROTOCOL = "#panel-astronomy .card:has-text('Time-Domain')"
    PHOTOMETRY_PROTOCOL = "#panel-astronomy .card:has-text('Photometry')"
    COORDINATE_PROTOCOL = "#panel-astronomy .card:has-text('Coordinate')"
    CI_STATUS = "#panel-astronomy .stat-item"


@pytest.fixture
def tab_selectors():
    """Return tab selectors."""
    return TabSelectors()


@pytest.fixture
def harness_selectors():
    """Return harness tab selectors."""
    return HarnessSelectors()


@pytest.fixture
def benchmark_selectors():
    """Return benchmark tab selectors."""
    return BenchmarkSelectors()


@pytest.fixture
def skills_selectors():
    """Return skills tab selectors."""
    return SkillsSelectors()


@pytest.fixture
def astronomy_selectors():
    """Return astronomy tab selectors."""
    return AstronomySelectors()


@pytest.fixture
async def navigate_to_tab(page_with_timeout, base_url, tab_selectors):
    """Factory fixture to navigate to a specific tab."""
    async def _navigate(tab_name: str):
        await page_with_timeout.goto(base_url, wait_until="domcontentloaded")
        await page_with_timeout.wait_for_selector(tab_selectors.TAB_NAV, timeout=10000)
        
        tab_mapping = {
            "harness": tab_selectors.HARNESS_TAB,
            "benchmark": tab_selectors.BENCHMARK_TAB,
            "skills": tab_selectors.SKILLS_TAB,
            "astronomy": tab_selectors.ASTRONOMY_TAB,
            "command": tab_selectors.COMMAND_TAB,
            "skychart": tab_selectors.SKYCHART_TAB,
            "data": tab_selectors.DATA_TAB,
            "research": tab_selectors.RESEARCH_TAB,
            "alerts": tab_selectors.ALERTS_TAB,
            "telescope": tab_selectors.TELESCOPE_TAB,
            "chat": tab_selectors.CHAT_TAB,
            "literature": tab_selectors.LITERATURE_TAB,
            "factcheck": tab_selectors.FACTCHECK_TAB,
            "workflow": tab_selectors.WORKFLOW_TAB,
            "logs": tab_selectors.LOGS_TAB,
            "manual": tab_selectors.MANUAL_TAB,
        }
        
        tab_selector = tab_mapping.get(tab_name)
        if tab_selector:
            await page_with_timeout.click(tab_selector)
            await page_with_timeout.wait_for_timeout(500)
        
        return page_with_timeout
    
    return _navigate
