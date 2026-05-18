"""
Base Protocol Layer - Abstract protocol definitions for TianwenAGI Harness

This module provides:
- Protocol abstract base class using Protocol ABC
- Registry pattern for protocol registration (lm-evaluation-harness style)
- Plugin support for extensible protocols
- Message and result data classes

Key Patterns:
- StarWhisperED JSONL format: {"label": "...", "predict": "..."}
- NGSS Skill-based workflow patterns
- lm-evaluation-harness registry pattern
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
)
from enum import Enum, auto
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# ============================================================================
# Data Classes - Protocol Communication
# ============================================================================

class MessageRole(Enum):
    """Message role in protocol communication."""
    SYSTEM = auto()
    USER = auto()
    ASSISTANT = auto()
    TOOL = auto()
    OBSERVATION = auto()


@dataclass
class Message:
    """Protocol message structure following StarWhisperED JSONL format."""
    role: MessageRole
    content: str
    label: Optional[str] = None  # For evaluation: ground truth
    predict: Optional[str] = None  # For evaluation: model prediction
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL serialization."""
        return {
            "role": self.role.name.lower(),
            "content": self.content,
            "label": self.label,
            "predict": self.predict,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "msg_id": self.msg_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        """Create from dictionary."""
        return cls(
            role=MessageRole[data["role"].upper()],
            content=data["content"],
            label=data.get("label"),
            predict=data.get("predict"),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            msg_id=data.get("msg_id", str(uuid.uuid4())),
        )


@dataclass
class ProtocolResult:
    """Result of protocol execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metrics": self.metrics,
            "messages": [m.to_dict() for m in self.messages],
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


@dataclass
class ProtocolSpec:
    """Specification for a protocol."""
    name: str
    version: str
    description: str
    skills: List[str] = field(default_factory=list)  # NGSS skills
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "skills": self.skills,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "config": self.config,
        }


# ============================================================================
# Protocol Registry - lm-evaluation-harness style
# ============================================================================

class ProtocolRegistry:
    """
    Registry for protocol implementations.
    
    Follows lm-evaluation-harness registry pattern for extensible
    protocol registration and discovery.
    
    Usage:
        @ProtocolRegistry.register("my_protocol")
        class MyProtocol(BaseProtocol):
            ...
        
        # Or manually register:
        ProtocolRegistry.register("my_protocol", MyProtocol)
        
        # Get protocol:
        protocol = ProtocolRegistry.get("my_protocol")
    """
    
    _registry: Dict[str, type] = {}
    _specs: Dict[str, ProtocolSpec] = {}
    _factories: Dict[str, Callable[..., BaseProtocol]] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        protocol_class: Optional[type] = None,
        spec: Optional[ProtocolSpec] = None,
        factory: Optional[Callable[..., BaseProtocol]] = None,
    ) -> Callable:
        """
        Register a protocol class.
        
        Can be used as decorator or called directly.
        
        Args:
            name: Protocol name for registration
            protocol_class: Protocol class to register
            spec: Protocol specification
            factory: Optional factory function for instantiation
        """
        def decorator(protocol_cls: type) -> type:
            cls._registry[name] = protocol_cls
            if spec is not None:
                cls._specs[name] = spec
            if factory is not None:
                cls._factories[name] = factory
            logger.info(f"Registered protocol: {name}")
            return protocol_cls
        
        if protocol_class is not None:
            # Direct registration
            cls._registry[name] = protocol_class
            if spec is not None:
                cls._specs[name] = spec
            if factory is not None:
                cls._factories[name] = factory
            logger.info(f"Registered protocol: {name}")
            return protocol_class
        
        return decorator
    
    @classmethod
    def get(cls, name: str, **kwargs) -> BaseProtocol:
        """
        Get a protocol instance by name.
        
        Args:
            name: Protocol name
            **kwargs: Arguments to pass to protocol constructor
            
        Returns:
            Protocol instance
            
        Raises:
            KeyError: If protocol not found
        """
        if name not in cls._registry:
            available = list(cls._registry.keys())
            raise KeyError(
                f"Protocol '{name}' not found. Available: {available}"
            )
        
        # Use factory if available, otherwise instantiate directly
        if name in cls._factories:
            return cls._factories[name](**kwargs)
        
        return cls._registry[name](**kwargs)
    
    @classmethod
    def get_spec(cls, name: str) -> Optional[ProtocolSpec]:
        """Get protocol specification."""
        return cls._specs.get(name)
    
    @classmethod
    def list_protocols(cls) -> List[str]:
        """List all registered protocol names."""
        return list(cls._registry.keys())
    
    @classmethod
    def list_with_specs(cls) -> Dict[str, ProtocolSpec]:
        """List all protocols with their specifications."""
        return dict(cls._specs)
    
    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a protocol is registered."""
        return name in cls._registry
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a protocol."""
        if name in cls._registry:
            del cls._registry[name]
            cls._specs.pop(name, None)
            cls._factories.pop(name, None)
            logger.info(f"Unregistered protocol: {name}")
            return True
        return False


# ============================================================================
# Base Protocol - Abstract interface
# ============================================================================

T = TypeVar("T")


class BaseProtocol(ABC, Generic[T]):
    """
    Abstract base class for all protocols.
    
    This defines the interface that all protocol implementations
    must follow for loose coupling and plugin support.
    
    Attributes:
        spec: Protocol specification
        config: Protocol configuration
        
    Methods:
        initialize: Set up the protocol
        execute: Execute the protocol with given input
        validate: Validate input/output data
        get_metrics: Get evaluation metrics
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize protocol.
        
        Args:
            config: Protocol configuration dictionary
        """
        self.config = config or {}
        self.spec: Optional[ProtocolSpec] = None
        self._initialized = False
        self._execution_count = 0
    
    @property
    def name(self) -> str:
        """Get protocol name."""
        return self.__class__.__name__
    
    @property
    def is_initialized(self) -> bool:
        """Check if protocol is initialized."""
        return self._initialized
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the protocol.
        
        This method should set up any resources needed by the protocol.
        Called once before any execution.
        """
        self._initialized = True
    
    @abstractmethod
    def execute(self, input_data: T) -> ProtocolResult:
        """
        Execute the protocol.
        
        Args:
            input_data: Input data for execution
            
        Returns:
            ProtocolResult with execution results
        """
        self._execution_count += 1
    
    @abstractmethod
    def validate(self, data: Any) -> bool:
        """
        Validate data against protocol schema.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True
    
    def get_metrics(self) -> Dict[str, float]:
        """
        Get protocol execution metrics.
        
        Returns:
            Dictionary of metric name to value
        """
        return {
            "execution_count": self._execution_count,
            "initialized": float(self._initialized),
        }
    
    def reset(self) -> None:
        """Reset protocol state."""
        self._execution_count = 0
    
    def __repr__(self) -> str:
        return f"<{self.name}Protocol(config={self.config})>"


# ============================================================================
# Protocol Plugin Decorator
# ============================================================================

def protocol_plugin(
    name: str,
    spec: Optional[ProtocolSpec] = None,
) -> Callable[[type], type]:
    """
    Decorator to register a protocol as a plugin.
    
    Usage:
        @protocol_plugin("my_astronomy_protocol", spec=ProtocolSpec(...))
        class MyAstronomyProtocol(BaseProtocol):
            ...
    """
    def decorator(cls: type) -> type:
        ProtocolRegistry.register(name, cls, spec=spec)
        return cls
    return decorator


# ============================================================================
# Utility Functions
# ============================================================================

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    Load JSONL file in StarWhisperED format.
    
    Format: {"label": "...", "predict": "..."}
    
    Args:
        file_path: Path to JSONL file
        
    Returns:
        List of parsed dictionaries
    """
    results = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def save_jsonl(data: List[Dict[str, Any]], file_path: str) -> None:
    """
    Save data to JSONL file in StarWhisperED format.
    
    Args:
        data: List of dictionaries to save
        file_path: Output file path
    """
    with open(file_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
