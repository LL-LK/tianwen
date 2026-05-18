"""
Graders Module - Pluggable grading system for TianwenAGI Harness

Provides extensible grading components following:
- StarWhisperED JSONL format: {"label": "...", "predict": "..."}
- lm-evaluation-harness registry pattern
- NGSS skill-based evaluation

Specialized graders:
- exact_match: Exact string/value matching
- partial_match: Partial matching with threshold
- astronomy: Domain-specific astronomy grading
  - spectral_line: Spectral line identification
  - photometric: Magnitude and color measurements
  - coordinate: Sky coordinate matching
  - redshift: Redshift measurement
"""

from harness.evaluation.graders.base import (
    BaseGrader,
    GraderRegistry,
    GraderResult,
    BatchGraderResult,
    register_grader,
)

from harness.evaluation.graders.exact_match import ExactMatchGrader
from harness.evaluation.graders.partial_match import PartialMatchGrader

# Astronomy graders - specialized domain-specific graders
from harness.evaluation.graders.astronomy import (
    AstronomyGrader,
    SpectralLineGrader,
    PhotometricGrader,
    CoordinateGrader,
    RedshiftGrader,
)

__all__ = [
    # Base
    "BaseGrader",
    "GraderRegistry",
    "GraderResult",
    "BatchGraderResult",
    "register_grader",
    # Standard graders
    "ExactMatchGrader",
    "PartialMatchGrader",
    # Astronomy graders
    "AstronomyGrader",
    "SpectralLineGrader",
    "PhotometricGrader",
    "CoordinateGrader",
    "RedshiftGrader",
]
