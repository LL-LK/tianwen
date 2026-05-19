"""
Visual Test Configuration for Tianwen-AGI
视觉测试配置 - Playwright截图对比测试基础设置
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import pytest

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not available. Install with: pip install playwright && playwright install chromium")


# Test configuration
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
BASELINE_DIR = SCREENSHOT_DIR / "baseline"
CURRENT_DIR = SCREENSHOT_DIR / "current"
DIFF_DIR = SCREENSHOT_DIR / "diff"

# Responsive breakpoints for layout testing
VIEWPORTS = {
    "mobile": {"width": 375, "height": 812},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1280, "height": 800},
    "wide": {"width": 1920, "height": 1080},
}

# Color scheme modes
COLOR_SCHEMES = ["light", "dark"]


@pytest.fixture(scope="session")
def screenshot_dirs():
    """Create and return screenshot directories."""
    for dir_path in [SCREENSHOT_DIR, BASELINE_DIR, CURRENT_DIR, DIFF_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
    return {
        "screenshot_dir": SCREENSHOT_DIR,
        "baseline_dir": BASELINE_DIR,
        "current_dir": CURRENT_DIR,
        "diff_dir": DIFF_DIR,
    }


@pytest.fixture(scope="session")
def browser_config():
    """Browser configuration for visual tests."""
    return {
        "headless": True,
        "viewport": {"width": 1280, "height": 800},
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    }


@pytest.fixture(scope="function")
def page(browser_config):
    """Provide a fresh page for each test."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=browser_config["headless"])
        context = browser.new_context(
            viewport=browser_config["viewport"],
            device_scale_factor=browser_config["device_scale_factor"],
            is_mobile=browser_config["is_mobile"],
            has_touch=browser_config["has_touch"],
        )
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.fixture(scope="function")
def page_with_theme(page):
    """Provide a page with theme switching capability."""
    def set_theme(theme: str):
        """Switch between light and dark mode."""
        if theme == "dark":
            page.emulate_media(color_scheme="dark")
        else:
            page.emulate_media(color_scheme="light")

    page.set_theme = set_theme
    yield page

    # Reset to default
    page.emulate_media(color_scheme=None)


@pytest.fixture(scope="function")
def responsive_page(browser_config):
    """Provide a page factory for responsive testing."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available")

    def _create_page_with_viewport(viewport_name: str) -> Page:
        """Create a page with specific viewport."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=browser_config["headless"])
            viewport = VIEWPORTS.get(viewport_name, VIEWPORTS["desktop"])
            context = browser.new_context(
                viewport=viewport,
                device_scale_factor=1,
                is_mobile=viewport_name == "mobile",
                has_touch=viewport_name == "mobile",
            )
            page = context.new_page()
            yield page
            context.close()
            browser.close()

    return _create_page_with_viewport


@pytest.fixture
def base_url():
    """Base URL for the application under test."""
    # Default to local development server
    return os.environ.get("TEST_BASE_URL", "http://localhost:3000")


def compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of a file for comparison."""
    if not file_path.exists():
        return ""
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def compute_screenshot_hash(screenshot_bytes: bytes) -> str:
    """Compute MD5 hash of screenshot bytes."""
    return hashlib.md5(screenshot_bytes).hexdigest()


def compare_screenshots(
    baseline_path: Path,
    current_path: Path,
    diff_path: Optional[Path] = None,
    threshold: float = 0.05,
) -> Dict[str, Any]:
    """
    Compare two screenshots and return comparison results.
    
    Uses file size comparison as primary method.
    For more accurate comparison, consider using imagehash library.
    
    Args:
        baseline_path: Path to baseline screenshot
        current_path: Path to current screenshot
        diff_path: Optional path to save diff image
        threshold: Acceptable size difference ratio (default 5%)
    
    Returns:
        Dict with comparison results including:
        - identical: bool
        - size_diff_ratio: float
        - baseline_size: int
        - current_size: int
        - message: str
    """
    result = {
        "identical": False,
        "size_diff_ratio": 0.0,
        "baseline_size": 0,
        "current_size": 0,
        "message": "",
    }

    if not baseline_path.exists():
        result["message"] = "Baseline screenshot not found"
        return result

    if not current_path.exists():
        result["message"] = "Current screenshot not found"
        return result

    baseline_size = baseline_path.stat().st_size
    current_size = current_path.stat().st_size

    result["baseline_size"] = baseline_size
    result["current_size"] = current_size

    if baseline_size == 0:
        result["message"] = "Baseline file is empty"
        return result

    size_diff = abs(current_size - baseline_size)
    result["size_diff_ratio"] = size_diff / baseline_size

    if result["size_diff_ratio"] <= threshold:
        result["identical"] = True
        result["message"] = f"Screenshots are identical (diff ratio: {result['size_diff_ratio']:.2%})"
    else:
        result["message"] = f"Screenshot changed (diff ratio: {result['size_diff_ratio']:.2%})"

    return result


@pytest.fixture
def screenshot_comparer(screenshot_dirs):
    """Fixture that provides screenshot comparison utility."""
    def compare(name: str, baseline_subdir: str = "") -> Dict[str, Any]:
        """Compare current screenshot with baseline."""
        baseline_dir = BASELINE_DIR / baseline_subdir if baseline_subdir else BASELINE_DIR
        current_path = CURRENT_DIR / f"{name}.png"
        baseline_path = baseline_dir / f"{name}.png"

        return compare_screenshots(baseline_path, current_path)

    return compare


def save_screenshot(page: Page, name: str, full_page: bool = False) -> Path:
    """
    Save screenshot to current directory.
    
    Args:
        page: Playwright page object
        name: Screenshot name (without extension)
        full_page: Whether to capture full scrollable page
    
    Returns:
        Path to saved screenshot
    """
    screenshot_path = CURRENT_DIR / f"{name}.png"
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    
    page.screenshot(path=str(screenshot_path), full_page=full_page)
    return screenshot_path


def save_baseline_screenshot(page: Page, name: str, full_page: bool = False) -> Path:
    """
    Save screenshot to baseline directory.
    
    Args:
        page: Playwright page object
        name: Screenshot name (without extension)
        full_page: Whether to capture full scrollable page
    
    Returns:
        Path to saved screenshot
    """
    baseline_path = BASELINE_DIR / f"{name}.png"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    
    page.screenshot(path=str(baseline_path), full_page=full_page)
    return baseline_path
