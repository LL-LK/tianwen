"""
TianwenAGI Harness - SkillRegistry
技能注册表，支持运行时注册和动态任务-技能匹配
"""
from typing import Dict, List, Any, Optional, Type, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio

from .base import BaseSkill, SkillConfig, SkillResult, SkillType

logger = logging.getLogger("harness.skills.registry")


# 全局技能注册表
_skill_registry: Dict[str, BaseSkill] = {}
_skill_classes: Dict[str, Type[BaseSkill]] = {}
_skill_tags: Dict[str, List[str]] = {}  # skill_name -> tags


@dataclass
class MatchResult:
    """技能匹配结果"""
    skill_name: str
    skill: BaseSkill
    score: float
    match_type: str = "default"  # exact, type, keyword, fallback
    metadata: Dict[str, Any] = field(default_factory=dict)


def register_skill(name: str = None, skill_type: SkillType = None, tags: List[str] = None):
    """
    技能注册装饰器
    Usage:
        @register_skill("my_skill", SkillType.DATA_ANALYSIS)
        class MySkill(BaseSkill):
            ...
    """
    def decorator(cls):
        nonlocal name, tags
        if name is None:
            name = cls.__name__.lower()
        if skill_type is not None:
            cls._skill_type = skill_type

        # 注册类
        _skill_classes[name] = cls

        # 如果有实例，也注册实例
        # (延迟实例化到首次获取时)

        # 注册标签
        if tags:
            _skill_tags[name] = tags

        logger.info(f"Registered skill class: {name}")
        return cls

    return decorator


class SkillRegistry:
    """
    技能注册表管理器
    提供统一的注册、查询、实例化、动态匹配接口
    """

    @classmethod
    def register(cls, skill: Union[str, Type[BaseSkill]], instance: BaseSkill = None) -> None:
        """
        注册技能
        Args:
            skill: 技能名称或技能类
            instance: 技能实例（如果传类则延迟实例化）
        """
        if isinstance(skill, str):
            name = skill
            if instance is not None:
                _skill_registry[name] = instance
                logger.info(f"Registered skill instance: {name}")
        else:
            # 类
            name = skill.__name__.lower()
            _skill_classes[name] = skill
            logger.info(f"Registered skill class: {name}")

    @classmethod
    def get(cls, name: str, **kwargs) -> Optional[BaseSkill]:
        """
        获取技能实例
        Args:
            name: 技能名称
            **kwargs: 传给技能的参数
        Returns:
            BaseSkill: 技能实例
        """
        # 优先从实例注册表获取
        if name in _skill_registry:
            return _skill_registry[name]

        # 尝试从类注册表获取并实例化
        if name in _skill_classes:
            skill_class = _skill_classes[name]
            instance = skill_class(**kwargs)
            # 缓存实例
            _skill_registry[name] = instance
            return instance

        return None

    @classmethod
    def create(cls, name: str, config: SkillConfig = None, **kwargs) -> Optional[BaseSkill]:
        """
        创建技能实例
        Args:
            name: 技能名称
            config: 技能配置
            **kwargs: 其他参数
        Returns:
            BaseSkill: 新创建的技能实例
        """
        skill = cls.get(name, **kwargs)
        if skill is None:
            logger.warning(f"Skill '{name}' not found in registry")
            return None

        # 应用配置
        if config is not None:
            skill.config = config

        # 初始化
        if hasattr(skill, 'initialize'):
            asyncio.create_task(skill.initialize())

        return skill

    @classmethod
    def list(cls) -> List[str]:
        """列出所有已注册技能名称"""
        all_names = set(_skill_registry.keys()) | set(_skill_classes.keys())
        return sorted(list(all_names))

    @classmethod
    def list_instances(cls) -> List[str]:
        """列出已实例化的技能"""
        return list(_skill_registry.keys())

    @classmethod
    def list_classes(cls) -> List[str]:
        """列出已注册的技能类"""
        return list(_skill_classes.keys())

    @classmethod
    def match(
        cls,
        task_description: str,
        task_type: SkillType = None,
        min_score: float = 0.0,
        limit: int = 5
    ) -> List[MatchResult]:
        """
        动态匹配技能
        Args:
            task_description: 任务描述
            task_type: 任务类型（可选）
            min_score: 最低匹配分数
            limit: 返回数量限制
        Returns:
            List[MatchResult]: 匹配结果列表（按分数降序）
        """
        results: List[MatchResult] = []

        # 获取所有可用技能实例
        all_skills: Dict[str, BaseSkill] = {}

        # 从实例注册表
        for name, skill in _skill_registry.items():
            all_skills[name] = skill

        # 从类注册表（创建临时实例用于匹配）
        for name, skill_class in _skill_classes.items():
            if name not in all_skills:
                try:
                    instance = skill_class()
                    all_skills[name] = instance
                except:
                    pass

        # 计算匹配分数
        for name, skill in all_skills.items():
            score = 0.0
            match_type = "default"
            metadata = {}

            # 1. 精确类型匹配
            if task_type is not None:
                if skill.skill_type == task_type:
                    score = max(score, 0.9)
                    match_type = "type"
                    metadata["type_match"] = True

            # 2. 使用技能的matches_task方法
            skill_score = skill.matches_task(task_description, task_type.value if task_type else None)
            if skill_score > score:
                score = max(score, skill_score)
                match_type = "keyword"

            # 3. 标签匹配
            if name in _skill_tags:
                tags = _skill_tags[name]
                for tag in tags:
                    if tag.lower() in task_description.lower():
                        score = max(score, 0.6)
                        metadata["tag_match"] = tag
                        break

            if score >= min_score:
                results.append(MatchResult(
                    skill_name=name,
                    skill=skill,
                    score=score,
                    match_type=match_type,
                    metadata=metadata
                ))

        # 排序
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    @classmethod
    def match_best(
        cls,
        task_description: str,
        task_type: SkillType = None,
        min_score: float = 0.3
    ) -> Optional[MatchResult]:
        """
        匹配最佳技能
        Returns:
            MatchResult 或 None
        """
        matches = cls.match(task_description, task_type, min_score, limit=1)
        return matches[0] if matches else None

    @classmethod
    async def execute_skill(
        cls,
        name: str,
        input_data: Any,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> SkillResult:
        """
        执行技能
        Args:
            name: 技能名称
            input_data: 输入数据
            context: 执行上下文
            **kwargs: 其他参数
        Returns:
            SkillResult: 执行结果
        """
        skill = cls.get(name, **kwargs)
        if skill is None:
            return SkillResult(
                skill_name=name,
                success=False,
                error=f"Skill '{name}' not found"
            )

        try:
            result = await skill.execute(input_data, context)
            return result
        except Exception as e:
            logger.error(f"Skill {name} execution failed: {e}")
            return SkillResult(
                skill_name=name,
                success=False,
                error=str(e)
            )

    @classmethod
    def unregister(cls, name: str) -> bool:
        """注销技能"""
        removed = False
        if name in _skill_registry:
            del _skill_registry[name]
            removed = True
        if name in _skill_classes:
            del _skill_classes[name]
            removed = True
        if name in _skill_tags:
            del _skill_tags[name]
        return removed

    @classmethod
    def clear(cls):
        """清空注册表"""
        _skill_registry.clear()
        _skill_classes.clear()
        _skill_tags.clear()
        logger.info("Skill registry cleared")

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_instances": len(_skill_registry),
            "total_classes": len(_skill_classes),
            "instance_names": list(_skill_registry.keys()),
            "class_names": list(_skill_classes.keys()),
        }


# 便捷函数
def get_skill(name: str, **kwargs) -> Optional[BaseSkill]:
    """获取技能"""
    return SkillRegistry.get(name, **kwargs)


def list_skills() -> List[str]:
    """列出所有技能"""
    return SkillRegistry.list()


def register_skill_func(name: str, skill: BaseSkill):
    """注册技能实例（函数形式）"""
    SkillRegistry.register(name, skill)
