"""
Graders Module - Pluggable grading system for TianwenAGI Harness

Provides extensible grading components following:
- StarWhisperED JSONL format: {"label": "...", "predict": "..."}
- lm-evaluation-harness registry pattern
- NGSS skill-based evaluation
"""

from harness.evaluation.graders.base import (
    BaseGrader,
    GraderRegistry,
    GraderResult,
    register_grader,
)

from harness.evaluation.graders.exact_match import ExactMatchGrader
from harness.evaluation.graders.partial_match import PartialMatchGrader
from harness.evaluation.graders.astronomy import AstronomyGrader

__all__ = [
    "BaseGrader",
    "GraderRegistry",
    "GraderResult",
    "register_grader",
    "ExactMatchGrader",
    "PartialMatchGrader",
    "AstronomyGrader",
]
