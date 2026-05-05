"""
自我审查系统 - 重导出模块

本模块从 agents.self_review 导入所有公共API，保持向后兼容。
原始实现位于 src/agents/self_review.py
"""

from agents.self_review import (
    ReviewPeriod,
    WeeklyReview,
    SelfReviewSystem,
    format_review_report,
    demo,
)

__all__ = [
    "ReviewPeriod",
    "WeeklyReview",
    "SelfReviewSystem",
    "format_review_report",
    "demo",
]
