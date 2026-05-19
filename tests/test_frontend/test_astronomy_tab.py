"""
Astronomy Tab Tests for Tianwen-AGI Frontend

Tests the Astronomy Protocols panel and CI/CD integration status.
"""

import pytest


@pytest.mark.playwright
@pytest.mark.ui
class TestAstronomyTab:
    """Test suite for Astronomy Tab functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        # Navigate to astronomy tab before each test
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="astronomy"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_astronomy_tab_switch(self):
        """Test that Astronomy tab can be activated."""
        astronomy_panel = await self.page.query_selector("#panel-astronomy.active")
        assert astronomy_panel is not None, "Astronomy panel should be active"

    @pytest.mark.asyncio
    async def test_astronomy_title_displayed(self):
        """Test that Astronomy tab title is displayed correctly."""
        title = await self.page.query_selector("#panel-astronomy .card-title")
        assert title is not None, "Astronomy title should exist"
        title_text = await title.text_content()
        assert "Astronomy" in title_text or "天文协议" in title_text

    @pytest.mark.asyncio
    async def test_astronomy_protocols_section_exists(self):
        """Test that astronomy protocols section exists."""
        protocols = await self.page.query_selector("#panel-astronomy .card-title:has-text('Astronomy Protocols')")
        assert protocols is not None, "Astronomy Protocols section should exist"


@pytest.mark.playwright
@pytest.mark.ui
class TestFITSProtocol:
    """Test suite for FITS Protocol section."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="astronomy"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_fits_protocol_section_exists(self):
        """Test that FITS protocol section exists."""
        fits = await self.page.query_selector("#panel-astronomy:has-text('FITS 协议')")
        assert fits is not None, "FITS protocol section should exist"

    @pytest.mark.asyncio
    async def test_fits_header_parser_listed(self):
        """Test that FITSHeaderParser is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "FITSHeaderParser" in content, "FITSHeaderParser should be listed"

    @pytest.mark.asyncio
    async def test_fits_image_processor_listed(self):
        """Test that FITSImageProcessor is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "FITSImageProcessor" in content, "FITSImageProcessor should be listed"

    @pytest.mark.asyncio
    async def test_wcs_coordinate_transform_listed(self):
        """Test that WCSCoordinateTransform is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "WCSCoordinateTransform" in content, "WCSCoordinateTransform should be listed"


@pytest.mark.playwright
@pytest.mark.ui
class TestTimeDomainProtocol:
    """Test suite for Time-Domain Protocol section."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="astronomy"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_time_domain_protocol_exists(self):
        """Test that Time-Domain protocol section exists."""
        td = await self.page.query_selector("#panel-astronomy:has-text('Time-Domain')")
        assert td is not None, "Time-Domain protocol section should exist"

    @pytest.mark.asyncio
    async def test_light_curve_processor_listed(self):
        """Test that LightCurveProcessor is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "LightCurveProcessor" in content, "LightCurveProcessor should be listed"

    @pytest.mark.asyncio
    async def test_period_finding_listed(self):
        """Test that PeriodFindingAnalysis is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "PeriodFindingAnalysis" in content, "PeriodFindingAnalysis should be listed"

    @pytest.mark.asyncio
    async def test_transient_detection_listed(self):
        """Test that TransientDetection is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "TransientDetection" in content, "TransientDetection should be listed"


@pytest.mark.playwright
@pytest.mark.ui
class TestPhotometryProtocol:
    """Test suite for Photometry Protocol section."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="astronomy"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_photometry_protocol_exists(self):
        """Test that Photometry protocol section exists."""
        photo = await self.page.query_selector("#panel-astronomy:has-text('Photometry')")
        assert photo is not None, "Photometry protocol section should exist"

    @pytest.mark.asyncio
    async def test_aperture_photometry_listed(self):
        """Test that AperturePhotometry is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "AperturePhotometry" in content, "AperturePhotometry should be listed"

    @pytest.mark.asyncio
    async def test_psf_photometry_listed(self):
        """Test that PSFPhotometry is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "PSFPhotometry" in content, "PSFPhotometry should be listed"

    @pytest.mark.asyncio
    async def test_flux_calibration_listed(self):
        """Test that FluxCalibration is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "FluxCalibration" in content, "FluxCalibration should be listed"


@pytest.mark.playwright
@pytest.mark.ui
class TestCoordinateProtocol:
    """Test suite for Coordinate Protocol section."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="astronomy"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_coordinate_protocol_exists(self):
        """Test that Coordinate protocol section exists."""
        coord = await self.page.query_selector("#panel-astronomy:has-text('Coordinate')")
        assert coord is not None, "Coordinate protocol section should exist"

    @pytest.mark.asyncio
    async def test_ics_coordinate_transform_listed(self):
        """Test that ICRSCoordinateTransform is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "ICRSCoordinateTransform" in content, "ICRSCoordinateTransform should be listed"

    @pytest.mark.asyncio
    async def test_galactic_coordinate_transform_listed(self):
        """Test that GalacticCoordinateTransform is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "GalacticCoordinateTransform" in content, "GalacticCoordinateTransform should be listed"

    @pytest.mark.asyncio
    async def test_altitude_azimuth_calculation_listed(self):
        """Test that AltitudeAzimuthCalculation is listed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "AltitudeAzimuthCalculation" in content, "AltitudeAzimuthCalculation should be listed"


@pytest.mark.playwright
@pytest.mark.ui
class TestCIDashboard:
    """Test suite for CI/CD integration status."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="astronomy"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_ci_status_section_exists(self):
        """Test that CI/CD integration status section exists."""
        ci_section = await self.page.query_selector("#panel-astronomy .card-title:has-text('CI/CD')")
        assert ci_section is not None, "CI/CD integration status section should exist"

    @pytest.mark.asyncio
    async def test_github_actions_status_displayed(self):
        """Test that GitHub Actions status is displayed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "GitHub Actions" in content, "GitHub Actions status should be displayed"

    @pytest.mark.asyncio
    async def test_ci_pipeline_status_displayed(self):
        """Test that CI Pipeline status is displayed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "CI Pipeline" in content, "CI Pipeline status should be displayed"

    @pytest.mark.asyncio
    async def test_tests_count_displayed(self):
        """Test that Tests count is displayed."""
        test_count = await self.page.query_selector("#ciTestCount")
        assert test_count is not None, "Tests count element should exist"
        count_text = await test_count.text_content()
        assert count_text.isdigit(), "Test count should be a number"

    @pytest.mark.asyncio
    async def test_python_files_count_displayed(self):
        """Test that Python files count is displayed."""
        py_count = await self.page.query_selector("#ciPyCount")
        assert py_count is not None, "Python files count element should exist"

    @pytest.mark.asyncio
    async def test_lint_status_displayed(self):
        """Test that Lint status is displayed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "Lint" in content, "Lint status should be displayed"

    @pytest.mark.asyncio
    async def test_docker_build_status_displayed(self):
        """Test that Docker Build status is displayed."""
        content = await self.page.text_content("#panel-astronomy")
        assert "Docker" in content or "Build" in content, "Docker Build status should be displayed"

    @pytest.mark.asyncio
    async def test_ci_stat_items_count(self):
        """Test that correct number of CI stat items are displayed."""
        stat_items = await self.page.query_selector_all("#panel-astronomy .stat-item")
        assert len(stat_items) >= 6, "Should have at least 6 CI status items"
