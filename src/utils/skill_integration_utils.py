"""
技能集成系统 - 重导出模块

本模块从 learning.skill_integration_learn 导入所有公共API，保持向后兼容。
原始实现位于 src/learning/skill_integration_learn.py
"""

from learning.skill_integration_learn import (
    SkillStatus,
    SkillInput,
    SkillOutput,
    SkillInterface,
    SkillExecution,
    SkillRegistry,
    SkillExecutor,
    SkillChainExecutor,
    create_skill_executor,
    create_chain_executor,
    demo,
)

__all__ = [
    "SkillStatus",
    "SkillInput",
    "SkillOutput",
    "SkillInterface",
    "SkillExecution",
    "SkillRegistry",
    "SkillExecutor",
    "SkillChainExecutor",
    "create_skill_executor",
    "create_chain_executor",
    "demo",
]
