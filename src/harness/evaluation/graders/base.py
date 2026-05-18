"""
Base Grader - Abstract grader interface for pluggable evaluation

This module provides:
- BaseGrader abstract class
- GraderRegistry for plugin registration
- GraderResult data class
- Decorator for grader registration
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Grader Result
# ============================================================================

@dataclass
class GraderResult:
    """
    Result from grading a single sample or batch.
    
    Attributes:
        score: The computed score (0-1 typically)
        passed: Whether the sample passed the threshold
        details: Additional details about the grading
        feedback: Optional feedback for the prediction
        metadata: Additional metadata
    """
    
    score: float
    passed: Optional[bool] = None
    details: Dict[str, Any] = field(default_factory=dict)
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set passed flag if not provided."""
        if self.passed is None:
            self.passed = self.score >= 0.5
    
    @property
    def is_correct(self) -> bool:
        """Alias for passed."""
        return self.passed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "passed": self.passed,
            "details": self.details,
            "feedback": self.feedback,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class BatchGraderResult:
    """
    Result from grading a batch of samples.
    
    Aggregates individual results and computes aggregate metrics.
    """
    
    results: List[GraderResult]
    task_name: str
    total: int
    passed_count: int
    failed_count: int
    aggregate_score: float
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def accuracy(self) -> float:
        """Compute accuracy."""
        if self.total == 0:
            return 0.0
        return self.passed_count / self.total
    
    @property
    def pass_rate(self) -> float:
        """Alias for accuracy."""
        return self.accuracy
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_name": self.task_name,
            "total": self.total,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "accuracy": self.accuracy,
            "aggregate_score": self.aggregate_score,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_results(
        cls,
        results: List[GraderResult],
        task_name: str,
        execution_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BatchGraderResult:
        """Create from list of individual results."""
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        avg_score = sum(r.score for r in results) / total if total > 0 else 0.0
        
        return cls(
            results=results,
            task_name=task_name,
            total=total,
            passed_count=passed,
            failed_count=total - passed,
            aggregate_score=avg_score,
            execution_time=execution_time,
            metadata=metadata or {},
        )


# ============================================================================
# Grader Registry - lm-evaluation-harness style
# ============================================================================

class GraderRegistry:
    """
    Registry for grader implementations.
    
    Follows lm-evaluation-harness registry pattern for
    pluggable grading system.
    
    Usage:
        @GraderRegistry.register("my_grader")
        class MyGrader(BaseGrader):
            ...
        
        # Get grader:
        grader = GraderRegistry.get("my_grader")
    """
    
    _graders: Dict[str, type] = {}
    _factories: Dict[str, Callable[..., BaseGrader]] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        grader_class: Optional[type] = None,
        factory: Optional[Callable[..., BaseGrader]] = None,
    ) -> Callable:
        """
        Register a grader class.
        
        Args:
            name: Grader name for registration
            grader_class: Grader class to register
            factory: Optional factory function
        """
        def decorator(grader_cls: type) -> type:
            cls._graders[name] = grader_cls
            logger.info(f"Registered grader: {name}")
            return grader_cls
        
        if grader_class is not None:
            cls._graders[name] = grader_class
            if factory is not None:
                cls._factories[name] = factory
            logger.info(f"Registered grader: {name}")
            return grader_class
        
        return decorator
    
    @classmethod
    def get(cls, name: str, **kwargs) -> BaseGrader:
        """
        Get a grader instance by name.
        
        Args:
            name: Grader name
            **kwargs: Arguments to pass to grader constructor
        """
        if name not in cls._graders:
            available = list(cls._graders.keys())
            raise KeyError(
                f"Grader '{name}' not found. Available: {available}"
            )
        
        if name in cls._factories:
            return cls._factories[name](**kwargs)
        
        return cls._graders[name](**kwargs)
    
    @classmethod
    def list_graders(cls) -> List[str]:
        """List all registered grader names."""
        return list(cls._graders.keys())
    
    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a grader is registered."""
        return name in cls._graders


# Decorator for convenience
def register_grader(name: str) -> Callable:
    """
    Decorator to register a grader.
    
    Usage:
        @register_grader("my_grader")
        class MyGrader(BaseGrader):
            ...
    """
    def decorator(cls: type) -> type:
        return GraderRegistry.register(name, cls)
    return decorator


# ============================================================================
# Base Grader
# ============================================================================

class BaseGrader(ABC):
    """
    Abstract base class for all graders.
    
    Graders evaluate predictions against references and produce
    scores and feedback.
    
    Attributes:
        name: Grader name
        config: Grader configuration
        
    Methods:
        grade: Grade a single prediction
        grade_batch: Grade a batch of predictions
        set_threshold: Set passing threshold
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize grader.
        
        Args:
            config: Grader configuration dictionary
        """
        self.config = config or {}
        self._threshold = self.config.get("threshold", 0.5)
        self._name = self.__class__.__name__
    
    @property
    def name(self) -> str:
        """Get grader name."""
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        """Set grader name."""
        self._name = value
    
    @property
    def threshold(self) -> float:
        """Get passing threshold."""
        return self._threshold
    
    def set_threshold(self, threshold: float) -> None:
        """
        Set passing threshold.
        
        Args:
            threshold: Threshold value (0-1)
        """
        self._threshold = max(0.0, min(1.0, threshold))
    
    @abstractmethod
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade a single prediction.
        
        Args:
            prediction: Model prediction
            reference: Ground truth reference
            **kwargs: Additional grader-specific arguments
            
        Returns:
            GraderResult with score and details
        """
        pass
    
    def grade_batch(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> BatchGraderResult:
        """
        Grade a batch of predictions.
        
        Args:
            predictions: List of predictions
            references: List of references
            **kwargs: Additional grader-specific arguments
            
        Returns:
            BatchGraderResult with aggregate results
        """
        import time
        start_time = time.time()
        
        results = []
        for pred, ref in zip(predictions, references):
            result = self.grade(pred, ref, **kwargs)
            results.append(result)
        
        batch_result = BatchGraderResult.from_results(
            results=results,
            task_name=self.name,
            execution_time=time.time() - start_time,
        )
        
        return batch_result
    
    def grade_jsonl(
        self,
        file_path: str,
        label_key: str = "label",
        predict_key: str = "predict",
        **kwargs,
    ) -> BatchGraderResult:
        """
        Grade predictions from JSONL file.
        
        Expected format: {"label": "...", "predict": "..."}
        
        Args:
            file_path: Path to JSONL file
            label_key: Key for ground truth label
            predict_key: Key for prediction
            **kwargs: Additional grader-specific arguments
            
        Returns:
            BatchGraderResult with aggregate results
        """
        predictions = []
        references = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    references.append(data.get(label_key))
                    predictions.append(data.get(predict_key))
        
        return self.grade_batch(predictions, references, **kwargs)
    
    def __repr__(self) -> str:
        return f"<{self.name}Grader(threshold={self._threshold})>"
