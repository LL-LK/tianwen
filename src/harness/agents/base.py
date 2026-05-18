"""
Enhanced Agent Base - Abstract agent interface for TianwenAGI Harness

This module provides:
- BaseAgent abstract class with skill-based workflows
- AgentRegistry for plugin registration (lm-evaluation-harness style)
- Agent state management
- Message passing interface
- NGSS skill integration

Key patterns:
- NGSS skill-based workflow patterns
- Plugin registration for extensibility
- StarWhisperED evaluation format support
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Agent State and Messages
# ============================================================================

class AgentState(Enum):
    """Agent execution states."""
    IDLE = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    WAITING = auto()
    COMPLETED = auto()
    ERROR = auto()
    TERMINATED = auto()


@dataclass
class AgentMessage:
    """
    Message passed between agents or to/from agent.
    
    Follows StarWhisperED format with label/predict for evaluation.
    """
    role: str  # "system", "user", "assistant", "tool"
    content: str
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    label: Optional[str] = None  # Ground truth for evaluation
    predict: Optional[str] = None  # Model prediction for evaluation
    metadata: Dict[str, Any] = field(default_factory=dict)
    attachments: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "msg_id": self.msg_id,
            "timestamp": self.timestamp.isoformat(),
            "label": self.label,
            "predict": self.predict,
            "metadata": self.metadata,
            "attachments": self.attachments,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentMessage:
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            msg_id=data.get("msg_id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            label=data.get("label"),
            predict=data.get("predict"),
            metadata=data.get("metadata", {}),
            attachments=data.get("attachments", []),
        )


# ============================================================================
# Skill Definition (NGSS-aligned)
# ============================================================================

@dataclass
class Skill:
    """
    Represents a skill for NGSS-style workflow.
    
    Skills define what an agent can do and are used for
    skill-based routing and evaluation.
    """
    name: str
    description: str
    category: str
    level: int = 1  # 1-5 proficiency level
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "level": self.level,
            "prerequisites": self.prerequisites,
            "metadata": self.metadata,
        }


# ============================================================================
# Agent Registry
# ============================================================================

class AgentRegistry:
    """
    Registry for agent implementations.
    
    Follows lm-evaluation-harness registry pattern for
    pluggable agent registration.
    
    Usage:
        @AgentRegistry.register("my_agent")
        class MyAgent(BaseAgent):
            ...
        
        agent = AgentRegistry.get("my_agent")
    """
    
    _agents: Dict[str, type] = {}
    _factories: Dict[str, Callable[..., BaseAgent]] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        agent_class: Optional[type] = None,
        factory: Optional[Callable[..., BaseAgent]] = None,
    ) -> Callable:
        """Register an agent class."""
        def decorator(agent_cls: type) -> type:
            cls._agents[name] = agent_cls
            logger.info(f"Registered agent: {name}")
            return agent_cls
        
        if agent_class is not None:
            cls._agents[name] = agent_class
            if factory is not None:
                cls._factories[name] = factory
            logger.info(f"Registered agent: {name}")
            return agent_class
        
        return decorator
    
    @classmethod
    def get(cls, name: str, **kwargs) -> BaseAgent:
        """Get an agent instance by name."""
        if name not in cls._agents:
            available = list(cls._agents.keys())
            raise KeyError(f"Agent '{name}' not found. Available: {available}")
        
        if name in cls._factories:
            return cls._factories[name](**kwargs)
        
        return cls._agents[name](**kwargs)
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """List all registered agent names."""
        return list(cls._agents.keys())
    
    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if agent is registered."""
        return name in cls._agents


def agent_plugin(name: str) -> Callable:
    """
    Decorator to register an agent.
    
    Usage:
        @agent_plugin("my_agent")
        class MyAgent(BaseAgent):
            ...
    """
    def decorator(cls: type) -> type:
        return AgentRegistry.register(name, cls)
    return decorator


# ============================================================================
# Base Agent
# ============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Provides:
    - State management
    - Skill-based workflow execution
    - Message passing
    - Plugin architecture
    - StarWhisperED evaluation format support
    
    Attributes:
        name: Agent name
        state: Current agent state
        skills: Set of agent skills
        config: Agent configuration
        
    Methods:
        initialize: Set up agent resources
        execute: Execute agent task
        get_state: Get current state
        add_skill: Register a skill
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        skills: Optional[List[Skill]] = None,
    ):
        """
        Initialize base agent.
        
        Args:
            config: Agent configuration dictionary
            skills: List of skills the agent possesses
        """
        self.config = config or {}
        self.name = self.config.get("name", self.__class__.__name__)
        self._state = AgentState.IDLE
        self._skills: Dict[str, Skill] = {}
        self._history: List[AgentMessage] = []
        self._metadata: Dict[str, Any] = {}
        
        # Register skills
        if skills:
            for skill in skills:
                self._skills[skill.name] = skill
        
        # Agent-specific initialization
        self._initialized = False
    
    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state
    
    @property
    def skills(self) -> Set[str]:
        """Get set of skill names."""
        return set(self._skills.keys())
    
    @property
    def skill_list(self) -> List[Skill]:
        """Get list of skills."""
        return list(self._skills.values())
    
    @property
    def history(self) -> List[AgentMessage]:
        """Get message history."""
        return self._history.copy()
    
    def _set_state(self, new_state: AgentState) -> None:
        """Internal state setter with logging."""
        logger.debug(f"{self.name}: {self._state.name} -> {new_state.name}")
        self._state = new_state
    
    def get_state(self) -> AgentState:
        """Get current state (alias for property)."""
        return self._state
    
    def add_skill(self, skill: Skill) -> None:
        """
        Add a skill to the agent.
        
        Args:
            skill: Skill to add
        """
        self._skills[skill.name] = skill
        logger.info(f"{self.name}: Added skill '{skill.name}'")
    
    def has_skill(self, skill_name: str) -> bool:
        """Check if agent has a skill."""
        return skill_name in self._skills
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(skill_name)
    
    def initialize(self) -> None:
        """
        Initialize agent resources.
        
        Called once before any task execution.
        """
        self._set_state(AgentState.INITIALIZING)
        self._initialized = True
        self._set_state(AgentState.IDLE)
        logger.info(f"{self.name}: Initialized")
    
    @abstractmethod
    def execute(
        self,
        task: Union[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """
        Execute agent task.
        
        Args:
            task: Task description or task dictionary
            context: Optional execution context
            
        Returns:
            AgentMessage with execution result
        """
        self._set_state(AgentState.RUNNING)
    
    def execute_with_skills(
        self,
        task: str,
        required_skills: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """
        Execute task requiring specific skills.
        
        Args:
            task: Task description
            required_skills: List of required skill names
            context: Optional execution context
            
        Returns:
            AgentMessage with result or error
        """
        # Check if agent has required skills
        missing_skills = [s for s in required_skills if not self.has_skill(s)]
        if missing_skills:
            return AgentMessage(
                role="assistant",
                content=f"Missing required skills: {missing_skills}",
                metadata={"error": "missing_skills", "missing": missing_skills},
            )
        
        return self.execute(task, context)
    
    def add_to_history(self, message: AgentMessage) -> None:
        """
        Add a message to agent history.
        
        Args:
            message: Message to add
        """
        self._history.append(message)
    
    def clear_history(self) -> None:
        """Clear message history."""
        self._history.clear()
    
    def get_history_jsonl(self) -> str:
        """
        Get history in JSONL format.
        
        Format: {"label": "...", "predict": "..."}
        
        Returns:
            JSONL string
        """
        lines = []
        for msg in self._history:
            lines.append(json.dumps({
                "role": msg.role,
                "content": msg.content,
                "label": msg.label,
                "predict": msg.predict,
                "metadata": msg.metadata,
            }, ensure_ascii=False))
        return "\n".join(lines)
    
    def reset(self) -> None:
        """Reset agent state and history."""
        self._set_state(AgentState.IDLE)
        self._history.clear()
        self._metadata.clear()
        logger.info(f"{self.name}: Reset")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get agent metadata."""
        return {
            "name": self.name,
            "state": self._state.name,
            "skills": list(self._skills.keys()),
            "num_messages": len(self._history),
            "initialized": self._initialized,
            **self._metadata,
        }
    
    def __repr__(self) -> str:
        return f"<{self.name}Agent(state={self._state.name}, skills={len(self._skills)})>"


# ============================================================================
# Agent Plugin Decorator
# ============================================================================

def agent_plugin_decorator(name: str):
    """
    Decorator to register an agent as a plugin.
    
    Usage:
        @agent_plugin_decorator("astronomy_agent")
        class AstronomyAgent(BaseAgent):
            ...
    """
    def decorator(cls: type) -> type:
        AgentRegistry.register(name, cls)
        return cls
    return decorator
