"""
Skills Tab Tests for Tianwen-AGI Frontend

Tests the Skill Registry, search, and filtering functionality.
"""

import pytest


@pytest.mark.playwright
@pytest.mark.ui
class TestSkillsTab:
    """Test suite for Skills Tab functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        # Navigate to skills tab before each test
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="skills"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_skills_tab_switch(self):
        """Test that Skills tab can be activated."""
        skills_panel = await self.page.query_selector("#panel-skills.active")
        assert skills_panel is not None, "Skills panel should be active"

    @pytest.mark.asyncio
    async def test_skills_title_displayed(self):
        """Test that Skills tab title is displayed correctly."""
        title = await self.page.query_selector("#panel-skills .card-title")
        assert title is not None, "Skills title should exist"
        title_text = await title.text_content()
        assert "Skill" in title_text or "技能" in title_text

    @pytest.mark.asyncio
    async def test_skill_registry_list_exists(self):
        """Test that skill registry list exists."""
        registry = await self.page.query_selector("#skillRegistryList")
        assert registry is not None, "Skill registry list should exist"

    @pytest.mark.asyncio
    async def test_skill_cards_exist(self):
        """Test that skill category cards are displayed."""
        cards = await self.page.query_selector_all("#skillRegistryList .card")
        assert len(cards) >= 4, "Should have at least 4 skill category cards"

    @pytest.mark.asyncio
    async def test_refresh_button_exists(self):
        """Test that refresh button exists."""
        refresh_btn = await self.page.query_selector("#panel-skills button:has-text('刷新')")
        assert refresh_btn is not None, "Refresh button should exist"

    @pytest.mark.asyncio
    async def test_search_input_exists(self):
        """Test that search input field exists."""
        search_input = await self.page.query_selector("#skillSearchInput")
        assert search_input is not None, "Search input should exist"

    @pytest.mark.asyncio
    async def test_search_button_exists(self):
        """Test that search button exists."""
        search_btn = await self.page.query_selector("#panel-skills button:has-text('搜索')")
        assert search_btn is not None, "Search button should exist"


@pytest.mark.playwright
@pytest.mark.ui
class TestSkillCategories:
    """Test suite for skill category display."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="skills"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_astronomy_skills_category_exists(self):
        """Test that astronomy skills category is displayed."""
        astro_category = await self.page.query_selector("#skillRegistryList:has-text('天文技能')")
        assert astro_category is not None, "Astronomy skills category should exist"

    @pytest.mark.asyncio
    async def test_agent_skills_category_exists(self):
        """Test that agent skills category is displayed."""
        agent_category = await self.page.query_selector("#skillRegistryList:has-text('Agent技能')")
        assert agent_category is not None, "Agent skills category should exist"

    @pytest.mark.asyncio
    async def test_grading_skills_category_exists(self):
        """Test that grading skills category is displayed."""
        grading_category = await self.page.query_selector("#skillRegistryList:has-text('评测技能')")
        assert grading_category is not None, "Grading skills category should exist"

    @pytest.mark.asyncio
    async def test_tool_skills_category_exists(self):
        """Test that tool skills category is displayed."""
        tool_category = await self.page.query_selector("#skillRegistryList:has-text('工具技能')")
        assert tool_category is not None, "Tool skills category should exist"

    @pytest.mark.asyncio
    async def test_specific_astronomy_skills_listed(self):
        """Test that specific astronomy skills are listed."""
        content = await self.page.text_content("#panel-skills")
        astronomy_skills = [
            "SpectralAnalysisProtocol", "PhotometryProtocol",
            "AstronomicalCoordinateProtocol", "FITSProcessor"
        ]
        for skill in astronomy_skills:
            assert skill in content, f"{skill} should be listed in astronomy skills"

    @pytest.mark.asyncio
    async def test_specific_agent_skills_listed(self):
        """Test that specific agent skills are listed."""
        content = await self.page.text_content("#panel-skills")
        agent_skills = [
            "CoordinatingAgent", "DiscoveryAgent",
            "HypothesisGenAgent", "ObservationAgent"
        ]
        for skill in agent_skills:
            assert skill in content, f"{skill} should be listed in agent skills"


@pytest.mark.playwright
@pytest.mark.ui
class TestSkillSearch:
    """Test suite for skill search and filtering."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="skills"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_search_input_accepts_text(self):
        """Test that search input accepts text input."""
        search_input = await self.page.query_selector("#skillSearchInput")
        assert search_input is not None
        await search_input.fill("Astronomy")
        value = await search_input.input_value()
        assert "Astronomy" in value, "Search input should accept and retain text"

    @pytest.mark.asyncio
    async def test_search_button_triggers_action(self):
        """Test that search button can be clicked."""
        search_input = await self.page.query_selector("#skillSearchInput")
        await search_input.fill("FITS")
        search_btn = await self.page.query_selector("#panel-skills button:has-text('搜索')")
        await search_btn.click()
        await self.page.wait_for_timeout(500)
        # Just verify no error occurred

    @pytest.mark.asyncio
    async def test_search_placeholder_displayed(self):
        """Test that search input has placeholder text."""
        search_input = await self.page.query_selector("#skillSearchInput")
        placeholder = await search_input.get_attribute("placeholder")
        assert placeholder is not None and len(placeholder) > 0, "Search input should have placeholder"

    @pytest.mark.asyncio
    async def test_refresh_button_triggers_action(self):
        """Test that refresh button triggers an action."""
        refresh_btn = await self.page.query_selector("#panel-skills button:has-text('刷新')")
        await refresh_btn.click()
        await self.page.wait_for_timeout(500)
        # Verify panel still has content
        cards = await self.page.query_selector_all("#skillRegistryList .card")
        assert len(cards) >= 4


@pytest.mark.playwright
@pytest.mark.ui
class TestSkillRegistry:
    """Test suite for skill registry content."""

    @pytest.fixture(autouse=True)
    async def setup(self, page_with_timeout, base_url):
        """Set up test fixture."""
        self.page = page_with_timeout
        self.base_url = base_url
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_selector(".tab-nav")
        await self.page.click('.tab-btn[data-tab="skills"]')
        await self.page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_skill_list_items_exist(self):
        """Test that skill list items exist in categories."""
        list_items = await self.page.query_selector_all("#skillRegistryList li")
        assert len(list_items) > 0, "Should have skill list items"

    @pytest.mark.asyncio
    async def test_grading_skills_included(self):
        """Test that grading skills are included."""
        content = await self.page.text_content("#panel-skills")
        grading_skills = ["ExactMatchGrader", "PartialMatchGrader", "AstronomyGrader"]
        for skill in grading_skills:
            assert skill in content, f"{skill} should be listed"

    @pytest.mark.asyncio
    async def test_tool_skills_included(self):
        """Test that tool skills are included."""
        content = await self.page.text_content("#panel-skills")
        tool_skills = ["MCPTools", "GitHubSearch", "WebSearch", "CatalogQuery"]
        for skill in tool_skills:
            assert skill in content, f"{skill} should be listed"

    @pytest.mark.asyncio
    async def test_multiple_skill_categories_displayed(self):
        """Test that multiple skill categories are displayed in grid."""
        cards = await self.page.query_selector_all("#skillRegistryList .card")
        assert len(cards) >= 4, "Should display multiple skill categories"

    @pytest.mark.asyncio
    async def test_skill_category_headers_exist(self):
        """Test that skill category headers exist."""
        headers = await self.page.query_selector_all("#skillRegistryList h4")
        assert len(headers) >= 4, "Should have category headers"
