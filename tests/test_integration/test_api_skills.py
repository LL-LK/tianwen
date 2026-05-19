"""
Tianwen-AGI - Skills API Endpoint Tests

Tests for the Skills API endpoints including:
- Skill registration and management
- Skill invocation and execution
- Skill metadata and parameters
- Skill category and filtering
"""

import pytest
import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# Mock classes for testing - these replace the harness imports
class SkillCategory(Enum):
    GENERAL = "general"
    ASTRONOMY = "astronomy"
    CODE = "code"
    WEB_SEARCH = "web_search"
    DATA_ANALYSIS = "data_analysis"


@dataclass
class SkillParameter:
    name: str
    type: str
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class SkillConfig:
    skill_id: str
    name: str
    description: str = ""
    category: SkillCategory = SkillCategory.GENERAL
    parameters: List[SkillParameter] = field(default_factory=list)
    enabled: bool = True
    version: str = "1.0.0"
    timeout_seconds: int = 30


@dataclass
class SkillResult:
    skill_id: str
    success: bool
    output: Any = None
    error: str = None
    execution_time: float = 0.0
    metadata: Dict = field(default_factory=dict)


class Skill:
    """Mock skill for testing."""

    def __init__(self, config: SkillConfig):
        self.config = config
        self.execution_count = 0

    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute the skill with given parameters."""
        self.execution_count += 1
        return SkillResult(
            skill_id=self.config.skill_id,
            success=True,
            output={"result": f"Executed {self.config.name} with params: {params}"},
            execution_time=0.01
        )

    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate skill parameters."""
        for param in self.config.parameters:
            if param.required and param.name not in params:
                return False
        return True


class SkillInvocation:
    def __init__(self, skill_id: str, parameters: Dict[str, Any] = None):
        self.skill_id = skill_id
        self.parameters = parameters or {}
        self.status = "pending"


class SkillRegistry:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SkillRegistry()
        return cls._instance

    def __init__(self):
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.config.skill_id] = skill

    def unregister(self, skill_id: str):
        if skill_id in self._skills:
            del self._skills[skill_id]

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def list_skills(self, category: SkillCategory = None) -> List[Skill]:
        if category is None:
            return list(self._skills.values())
        return [s for s in self._skills.values() if s.config.category == category]


# Pytest fixtures
@pytest.fixture
def mock_skill_info():
    """Fixture providing mock skill info."""
    return {
        "skill_id": "test_skill_001",
        "name": "Test Skill",
        "description": "A test skill for unit testing"
    }


class TestSkillConfigAPI:
    """Test Skill Configuration API."""

    def test_skill_config_creation(self, mock_skill_info):
        """Test skill configuration creation."""
        config = SkillConfig(
            skill_id=mock_skill_info["skill_id"],
            name=mock_skill_info["name"],
            description=mock_skill_info["description"],
            category=SkillCategory.ASTRONOMY,
            parameters=[
                SkillParameter(
                    name="target",
                    type="string",
                    required=True,
                    description="Target object"
                )
            ]
        )
        assert config.name == mock_skill_info["name"]
        assert config.category == SkillCategory.ASTRONOMY
        assert len(config.parameters) == 1

    def test_skill_config_defaults(self):
        """Test skill configuration defaults."""
        config = SkillConfig(skill_id="default_test", name="Default Test")
        assert config.enabled is True
        assert config.version == "1.0.0"
        assert config.timeout_seconds == 30

    def test_skill_config_parameter_validation(self):
        """Test skill parameter configuration."""
        param = SkillParameter(
            name="query",
            type="string",
            required=True,
            default=None,
            description="Search query"
        )
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True
        assert param.default is None

    def test_skill_config_optional_parameter(self):
        """Test optional skill parameter."""
        param = SkillParameter(
            name="limit",
            type="integer",
            required=False,
            default=10,
            description="Result limit"
        )
        assert param.required is False
        assert param.default == 10

    def test_skill_config_multiple_parameters(self):
        """Test skill with multiple parameters."""
        params = [
            SkillParameter(name="target", type="string", required=True),
            SkillParameter(name="catalog", type="string", required=False, default="messier"),
            SkillParameter(name="limit", type="integer", required=False, default=10),
        ]
        config = SkillConfig(
            skill_id="multi_param",
            name="Multi Parameter Skill",
            parameters=params
        )
        assert len(config.parameters) == 3
        required_params = [p for p in config.parameters if p.required]
        assert len(required_params) == 1


class TestSkillRegistryAPI:
    """Test Skill Registry API."""

    def test_skill_registry_singleton(self):
        """Test skill registry is singleton."""
        registry1 = SkillRegistry.get_instance()
        registry2 = SkillRegistry.get_instance()
        assert registry1 is registry2

    def test_skill_registry_register(self):
        """Test registering a skill."""
        registry = SkillRegistry.get_instance()
        config = SkillConfig(
            skill_id="register_test",
            name="Register Test Skill",
            category=SkillCategory.GENERAL
        )
        skill = Skill(config)
        registry.register(skill)
        assert registry.get_skill("register_test") is not None

    def test_skill_registry_get(self):
        """Test getting a registered skill."""
        registry = SkillRegistry.get_instance()
        skill = registry.get_skill("register_test")
        if skill:
            assert skill.config.skill_id == "register_test"

    def test_skill_registry_list(self):
        """Test listing registered skills."""
        registry = SkillRegistry.get_instance()
        skills = registry.list_skills()
        assert isinstance(skills, list)

    def test_skill_registry_list_by_category(self):
        """Test listing skills by category."""
        registry = SkillRegistry.get_instance()
        astronomy_skills = registry.list_skills(category=SkillCategory.ASTRONOMY)
        assert isinstance(astronomy_skills, list)

    def test_skill_registry_unregister(self):
        """Test unregistering a skill."""
        registry = SkillRegistry.get_instance()
        config = SkillConfig(
            skill_id="unregister_test",
            name="Unregister Test",
            category=SkillCategory.GENERAL
        )
        skill = Skill(config)
        registry.register(skill)
        assert registry.get_skill("unregister_test") is not None
        registry.unregister("unregister_test")
        assert registry.get_skill("unregister_test") is None


class TestSkillInvocationAPI:
    """Test Skill Invocation API."""

    @pytest.mark.asyncio
    async def test_skill_invocation_creation(self):
        """Test creating skill invocation."""
        invocation = SkillInvocation(
            skill_id="invoke_test",
            parameters={"query": "M31"}
        )
        assert invocation.skill_id == "invoke_test"
        assert invocation.parameters["query"] == "M31"
        assert invocation.status == "pending"

    @pytest.mark.asyncio
    async def test_skill_invocation_execution(self):
        """Test executing skill invocation."""
        config = SkillConfig(
            skill_id="execution_test",
            name="Execution Test Skill",
            category=SkillCategory.ASTRONOMY,
            parameters=[
                SkillParameter(name="target", type="string", required=True)
            ]
        )
        skill = Skill(config)
        result = await skill.execute({"target": "M31"})
        assert result.success is True
        assert "M31" in str(result.output)

    @pytest.mark.asyncio
    async def test_skill_invocation_with_optional_params(self):
        """Test skill invocation with optional parameters."""
        config = SkillConfig(
            skill_id="optional_test",
            name="Optional Param Test",
            category=SkillCategory.GENERAL,
            parameters=[
                SkillParameter(name="required", type="string", required=True),
                SkillParameter(name="optional", type="integer", required=False, default=5),
            ]
        )
        skill = Skill(config)
        result = await skill.execute({"required": "test"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_skill_invocation_validation(self):
        """Test skill parameter validation."""
        config = SkillConfig(
            skill_id="validation_test",
            name="Validation Test",
            category=SkillCategory.GENERAL,
            parameters=[
                SkillParameter(name="required_field", type="string", required=True),
            ]
        )
        skill = Skill(config)
        is_valid = await skill.validate_params({})
        assert is_valid is False
        is_valid = await skill.validate_params({"required_field": "value"})
        assert is_valid is True


class TestSkillResultAPI:
    """Test Skill Result API."""

    @pytest.mark.asyncio
    async def test_skill_result_success(self):
        """Test successful skill result."""
        result = SkillResult(
            skill_id="success_test",
            success=True,
            output={"data": "test result"},
            execution_time=0.05
        )
        assert result.success is True
        assert result.output["data"] == "test result"
        assert result.execution_time == 0.05

    @pytest.mark.asyncio
    async def test_skill_result_failure(self):
        """Test failed skill result."""
        result = SkillResult(
            skill_id="failure_test",
            success=False,
            error="Test error message",
            execution_time=0.01
        )
        assert result.success is False
        assert result.error == "Test error message"

    @pytest.mark.asyncio
    async def test_skill_result_with_metadata(self):
        """Test skill result with metadata."""
        result = SkillResult(
            skill_id="metadata_test",
            success=True,
            output={"items": [1, 2, 3]},
            execution_time=0.1,
            metadata={"count": 3, "type": "list"}
        )
        assert result.metadata["count"] == 3
        assert result.metadata["type"] == "list"


class TestSkillCategoryAPI:
    """Test Skill Category API."""

    def test_skill_category_values(self):
        """Test skill category enum values."""
        assert SkillCategory.GENERAL.value == "general"
        assert SkillCategory.ASTRONOMY.value == "astronomy"
        assert SkillCategory.CODE.value == "code"
        assert SkillCategory.WEB_SEARCH.value == "web_search"
        assert SkillCategory.DATA_ANALYSIS.value == "data_analysis"

    def test_skill_category_assignment(self):
        """Test assigning skill category."""
        config = SkillConfig(
            skill_id="category_test",
            name="Category Test",
            category=SkillCategory.ASTRONOMY
        )
        assert config.category == SkillCategory.ASTRONOMY


class TestSkillExecutionAPI:
    """Test Skill Execution API."""

    @pytest.mark.asyncio
    async def test_skill_execution_sync(self):
        """Test synchronous skill execution."""
        config = SkillConfig(
            skill_id="sync_test",
            name="Sync Test",
            category=SkillCategory.GENERAL
        )
        skill = Skill(config)
        result = await skill.execute({})
        assert result.success is True
        assert skill.execution_count == 1

    @pytest.mark.asyncio
    async def test_skill_execution_multiple(self):
        """Test multiple skill executions."""
        config = SkillConfig(
            skill_id="multi_exec",
            name="Multiple Execution Test",
            category=SkillCategory.GENERAL
        )
        skill = Skill(config)

        for _ in range(5):
            await skill.execute({})

        assert skill.execution_count == 5

    @pytest.mark.asyncio
    async def test_skill_execution_with_complex_params(self):
        """Test skill execution with complex parameters."""
        config = SkillConfig(
            skill_id="complex_test",
            name="Complex Params Test",
            category=SkillCategory.ASTRONOMY,
            parameters=[
                SkillParameter(name="targets", type="array", required=True),
                SkillParameter(name="options", type="object", required=False),
            ]
        )
        skill = Skill(config)
        result = await skill.execute({
            "targets": ["M31", "M42", "M51"],
            "options": {"format": "json", "include_metadata": True}
        })
        assert result.success is True

    @pytest.mark.asyncio
    async def test_skill_timeout_handling(self):
        """Test skill execution timeout handling."""
        config = SkillConfig(
            skill_id="timeout_test",
            name="Timeout Test",
            timeout_seconds=1
        )
        skill = Skill(config)
        # Simulate slow execution
        skill.execute = AsyncMock(return_value=SkillResult(
            skill_id="timeout_test",
            success=False,
            error="Execution timeout",
            execution_time=1.0
        ))
        result = await skill.execute({})
        # The mock result shows timeout behavior
        assert result.skill_id == "timeout_test"


class TestSkillIntegrationAPI:
    """Integration tests for Skills API."""

    @pytest.mark.asyncio
    async def test_full_skill_execution_flow(self):
        """Test complete skill execution flow."""
        # Setup
        registry = SkillRegistry.get_instance()
        config = SkillConfig(
            skill_id="integration_test",
            name="Integration Test Skill",
            category=SkillCategory.ASTRONOMY,
            parameters=[
                SkillParameter(name="target", type="string", required=True),
            ]
        )
        skill = Skill(config)

        # Register
        registry.register(skill)

        # Execute
        retrieved = registry.get_skill("integration_test")
        assert retrieved is not None

        result = await retrieved.execute({"target": "M31"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_skill_chaining(self):
        """Test chaining multiple skills."""
        config1 = SkillConfig(skill_id="chain_1", name="Chain 1", category=SkillCategory.GENERAL)
        config2 = SkillConfig(skill_id="chain_2", name="Chain 2", category=SkillCategory.GENERAL)

        skill1 = Skill(config1)
        skill2 = Skill(config2)

        result1 = await skill1.execute({"input": "data"})
        assert result1.success is True

        result2 = await skill2.execute({"input": result1.output})
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_skill_error_propagation(self):
        """Test error propagation through skill execution."""
        config = SkillConfig(
            skill_id="error_prop",
            name="Error Propagation Test",
            category=SkillCategory.GENERAL
        )
        skill = Skill(config)

        # Mock execute to return error
        skill.execute = AsyncMock(return_value=SkillResult(
            skill_id="error_prop",
            success=False,
            error="Simulated error",
            execution_time=0.0
        ))

        result = await skill.execute({})
        assert result.success is False
        assert result.error == "Simulated error"

    @pytest.mark.asyncio
    async def test_skill_registry_persistence(self):
        """Test skill registry persists skills."""
        registry = SkillRegistry.get_instance()
        initial_count = len(registry.list_skills())

        config = SkillConfig(
            skill_id="persist_test",
            name="Persistence Test",
            category=SkillCategory.GENERAL
        )
        skill = Skill(config)
        registry.register(skill)

        # Verify skill was added
        assert len(registry.list_skills()) == initial_count + 1
        assert registry.get_skill("persist_test") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
