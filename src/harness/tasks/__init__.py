"""
TianwenAGI Harness - 任务包
"""
from .astronomy import (
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
