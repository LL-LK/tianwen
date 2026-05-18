"""
TianwenAGI Harness - 天文任务包
"""
from .observation import (
    TransientObservationTask,
    SpectralAnalysisTask,
    CatalogQueryTask,
    RealBogusTask,
    ObservationPlanningTask,
)

__all__ = [
    "TransientObservationTask",
    "SpectralAnalysisTask",
    "CatalogQueryTask",
    "RealBogusTask",
    "ObservationPlanningTask",
]
