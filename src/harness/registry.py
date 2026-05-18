"""
TianwenAGI Harness - 组件注册表
基于装饰器的插件化架构，参考lm-evaluation-harness的注册表模式
"""
from typing import Dict, List, Type, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger("harness.registry")


# 全局注册表
_agent_registry: Dict[str, Type] = {}
_task_registry: Dict[str, Type] = {}
_evaluator_registry: Dict[str, Type] = {}
_tool_registry: Dict[str, Callable] = {}
_mcp_server_registry: Dict[str, Any] = {}
_skill_registry: Dict[str, Any] = {}


@dataclass
class RegistryStats:
    """注册表统计"""
    agent_count: int = 0
    task_count: int = 0
    evaluator_count: int = 0
    tool_count: int = 0
    mcp_server_count: int = 0
    skill_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


def register_agent(name: str = None):
    """Agent注册装饰器"""
    def decorator(cls):
        nonlocal name
        if name is None:
            name = cls.__name__.lower()
        if name in _agent_registry:
            logger.warning(f"Agent '{name}' already registered, overwriting")
        _agent_registry[name] = cls
        logger.info(f"Registered agent: {name}")
        return cls
    return decorator


def register_task(name: str = None):
    """Task注册装饰器"""
    def decorator(cls):
        nonlocal name
        if name is None:
            name = cls.__name__.lower()
        if name in _task_registry:
            logger.warning(f"Task '{name}' already registered, overwriting")
        _task_registry[name] = cls
        logger.info(f"Registered task: {name}")
        return cls
    return decorator


def register_evaluator(name: str = None):
    """Evaluator注册装饰器"""
    def decorator(cls):
        nonlocal name
        if name is None:
            name = cls.__name__.lower()
        if name in _evaluator_registry:
            logger.warning(f"Evaluator '{name}' already registered, overwriting")
        _evaluator_registry[name] = cls
        logger.info(f"Registered evaluator: {name}")
        return cls
    return decorator


def register_tool(name: str):
    """工具注册装饰器"""
    def decorator(func: Callable):
        if name in _tool_registry:
            logger.warning(f"Tool '{name}' already registered, overwriting")
        _tool_registry[name] = func
        logger.info(f"Registered tool: {name}")
        return func
    return decorator


class HarnessRegistry:
    """
    Harness组件注册表管理器
    提供统一的注册、查询、实例化接口
    """

    # === Agent管理 ===
    @classmethod
    def register_agent(cls, name: str, agent_class: Type):
        """手动注册Agent"""
        _agent_registry[name] = agent_class

    @classmethod
    def get_agent(cls, name: str) -> Optional[Type]:
        return _agent_registry.get(name)

    @classmethod
    def list_agents(cls) -> List[str]:
        return list(_agent_registry.keys())

    @classmethod
    def create_agent(cls, name: str, **kwargs):
        """创建Agent实例"""
        agent_class = _agent_registry.get(name)
        if agent_class is None:
            raise ValueError(f"Agent '{name}' not found. Available: {list(_agent_registry.keys())}")
        return agent_class(**kwargs)

    # === Task管理 ===
    @classmethod
    def register_task(cls, name: str, task_class: Type):
        _task_registry[name] = task_class

    @classmethod
    def get_task(cls, name: str) -> Optional[Type]:
        return _task_registry.get(name)

    @classmethod
    def list_tasks(cls) -> List[str]:
        return list(_task_registry.keys())

    @classmethod
    def create_task(cls, name: str, **kwargs):
        """创建Task实例"""
        task_class = _task_registry.get(name)
        if task_class is None:
            raise ValueError(f"Task '{name}' not found. Available: {list(_task_registry.keys())}")
        return task_class(**kwargs)

    # === Evaluator管理 ===
    @classmethod
    def register_evaluator(cls, name: str, evaluator_class: Type):
        _evaluator_registry[name] = evaluator_class

    @classmethod
    def get_evaluator(cls, name: str) -> Optional[Type]:
        return _evaluator_registry.get(name)

    @classmethod
    def list_evaluators(cls) -> List[str]:
        return list(_evaluator_registry.keys())

    @classmethod
    def create_evaluator(cls, name: str, **kwargs):
        evaluator_class = _evaluator_registry.get(name)
        if evaluator_class is None:
            raise ValueError(f"Evaluator '{name}' not found. Available: {list(_evaluator_registry.keys())}")
        return evaluator_class(**kwargs)

    # === Tool管理 ===
    @classmethod
    def register_tool(cls, name: str, func: Callable):
        _tool_registry[name] = func

    @classmethod
    def get_tool(cls, name: str) -> Optional[Callable]:
        return _tool_registry.get(name)

    @classmethod
    def list_tools(cls) -> List[str]:
        return list(_tool_registry.keys())

    @classmethod
    async def call_tool(cls, name: str, **kwargs) -> Any:
        """调用工具"""
        tool = _tool_registry.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' not found. Available: {list(_tool_registry.keys())}")
        return await tool(**kwargs)

    # === MCP Server管理 ===
    @classmethod
    def register_mcp_server(cls, name: str, server: Any):
        _mcp_server_registry[name] = server

    @classmethod
    def get_mcp_server(cls, name: str) -> Optional[Any]:
        return _mcp_server_registry.get(name)

    @classmethod
    def list_mcp_servers(cls) -> List[str]:
        return list(_mcp_server_registry.keys())

    # === Skill管理 ===
    @classmethod
    def register_skill(cls, name: str, skill: Any):
        _skill_registry[name] = skill

    @classmethod
    def get_skill(cls, name: str) -> Optional[Any]:
        return _skill_registry.get(name)

    @classmethod
    def list_skills(cls) -> List[str]:
        return list(_skill_registry.keys())

    # === 统计 ===
    @classmethod
    def get_stats(cls) -> RegistryStats:
        return RegistryStats(
            agent_count=len(_agent_registry),
            task_count=len(_task_registry),
            evaluator_count=len(_evaluator_registry),
            tool_count=len(_tool_registry),
            mcp_server_count=len(_mcp_server_registry),
            skill_count=len(_skill_registry),
        )

    @classmethod
    def print_stats(cls):
        """打印注册表统计"""
        stats = cls.get_stats()
        print("=== TianwenAGI Harness Registry ===")
        print(f"  Agents:      {stats.agent_count}")
        print(f"  Tasks:       {stats.task_count}")
        print(f"  Evaluators:  {stats.evaluator_count}")
        print(f"  Tools:       {stats.tool_count}")
        print(f"  MCP Servers: {stats.mcp_server_count}")
        print(f"  Skills:      {stats.skill_count}")
        print(f"  Last Updated: {stats.last_updated}")
