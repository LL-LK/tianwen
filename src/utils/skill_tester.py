"""
技能测试系统 - 重导出模块

本模块从 learning.skill_tester 导入所有公共API，保持向后兼容。
原始实现位于 src/learning/skill_tester.py
"""

from learning.skill_tester import (
    TestStatus,
    TestCase,
    TestResult,
    SkillTestReport,
    OutputValidator,
    SkillTestCases,
    SkillTester,
    demo,
    create_user,
    get_user,
)

__all__ = [
    "TestStatus",
    "TestCase",
    "TestResult",
    "SkillTestReport",
    "OutputValidator",
    "SkillTestCases",
    "SkillTester",
    "demo",
    "create_user",
    "get_user",
]
