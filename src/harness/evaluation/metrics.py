"""
Enhanced Evaluation Metrics for TianwenAGI Harness

This module provides comprehensive metrics for model evaluation including:
- Classification reports (precision, recall, F1)
- Confusion matrix analysis
- StarWhisperED JSONL format support
- lm-evaluation-harness style metric registry

Key format: {"label": "...", "predict": "..."}
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Metric Registry - lm-evaluation-harness style
# ============================================================================

class MetricRegistry:
    """
    Registry for evaluation metrics.
    
    Follows lm-evaluation-harness pattern for extensible metric registration.
    
    Usage:
        @MetricRegistry.register("my_metric")
        class MyMetric(Metric):
            ...
        
        # Or register function:
        MetricRegistry.register_function("accuracy", accuracy_fn)
    """
    
    _metrics: Dict[str, type] = {}
    _functions: Dict[str, Callable] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        metric_class: Optional[type] = None,
        func: Optional[Callable] = None,
    ) -> Callable:
        """Register a metric class or function."""
        def decorator(metric_cls: type) -> type:
            cls._metrics[name] = metric_cls
            logger.info(f"Registered metric: {name}")
            return metric_cls
        
        if metric_class is not None:
            cls._metrics[name] = metric_class
            logger.info(f"Registered metric: {name}")
            return metric_class
        
        if func is not None:
            cls._functions[name] = func
            logger.info(f"Registered metric function: {name}")
            return func
        
        return decorator
    
    @classmethod
    def get(cls, name: str) -> Union[type, Callable]:
        """Get a metric by name."""
        if name in cls._metrics:
            return cls._metrics[name]
        if name in cls._functions:
            return cls._functions[name]
        raise KeyError(f"Metric '{name}' not found")
    
    @classmethod
    def list_metrics(cls) -> List[str]:
        """List all registered metrics."""
        return list(cls._metrics.keys())
    
    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if metric exists."""
        return name in cls._metrics or name in cls._functions


# ============================================================================
# Base Metric Interface
# ============================================================================

class Metric(ABC):
    """
    Abstract base class for evaluation metrics.
    
    All metrics should implement this interface for consistent evaluation.
    """
    
    name: str = "base_metric"
    
    @abstractmethod
    def compute(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> float:
        """Compute the metric value."""
        pass
    
    @abstractmethod
    def detailed_compute(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """Compute detailed metric information."""
        pass


# ============================================================================
# Classification Metrics
# ============================================================================

@dataclass
class ClassificationReport:
    """Detailed classification report."""
    labels: List[str]
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1: Dict[str, float]
    support: Dict[str, int]
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_precision: float
    weighted_recall: float
    weighted_f1: float
    accuracy: float
    confusion_matrix: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "labels": self.labels,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "support": self.support,
            "macro_precision": self.macro_precision,
            "macro_recall": self.macro_recall,
            "macro_f1": self.macro_f1,
            "weighted_precision": self.weighted_precision,
            "weighted_recall": self.weighted_recall,
            "weighted_f1": self.weighted_f1,
            "accuracy": self.accuracy,
        }


class ClassificationMetrics(Metric):
    """
    Comprehensive classification metrics.
    
    Computes:
    - Per-class precision, recall, F1
    - Macro and weighted averages
    - Confusion matrix
    - Support values
    
    Supports StarWhisperED format: {"label": "...", "predict": "..."}
    """
    
    name = "classification_metrics"
    
    def compute(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> float:
        """
        Compute overall F1 score.
        
        Args:
            predictions: List of predicted labels
            references: List of ground truth labels
            **kwargs: Additional arguments
            
        Returns:
            Weighted F1 score
        """
        return float(f1_score(references, predictions, average="weighted"))
    
    def detailed_compute(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Compute detailed classification metrics.
        
        Args:
            predictions: List of predicted labels
            references: List of ground truth labels
            **kwargs: Additional arguments like labels
            
        Returns:
            Dictionary with detailed metrics
        """
        labels = kwargs.get("labels", sorted(set(references + predictions)))
        
        # Get sklearn classification report as dict
        report = classification_report(
            references,
            predictions,
            labels=labels,
            output_dict=True,
            zero_division=0,
        )
        
        # Get confusion matrix
        cm = confusion_matrix(references, predictions, labels=labels)
        
        # Build ClassificationReport object
        class_report = ClassificationReport(
            labels=labels,
            precision={k: report[k]["precision"] for k in labels},
            recall={k: report[k]["recall"] for k in labels},
            f1={k: report[k]["f1-score"] for k in labels},
            support={k: int(report[k]["support"]) for k in labels},
            macro_precision=report["macro avg"]["precision"],
            macro_recall=report["macro avg"]["recall"],
            macro_f1=report["macro avg"]["f1-score"],
            weighted_precision=report["weighted avg"]["precision"],
            weighted_recall=report["weighted avg"]["recall"],
            weighted_f1=report["weighted avg"]["f1-score"],
            accuracy=report["accuracy"],
            confusion_matrix=cm,
        )
        
        return {
            "classification_report": class_report,
            "accuracy": report["accuracy"],
            "macro_f1": report["macro avg"]["f1-score"],
            "weighted_f1": report["weighted avg"]["f1-score"],
            "confusion_matrix": cm.tolist(),
            "per_class": {
                label: {
                    "precision": class_report.precision[label],
                    "recall": class_report.recall[label],
                    "f1": class_report.f1[label],
                    "support": class_report.support[label],
                }
                for label in labels
            },
        }


# Register metric
MetricRegistry.register("classification", ClassificationMetrics)


# ============================================================================
# Confusion Matrix Analysis
# ============================================================================

@dataclass
class ConfusionMatrix:
    """
    Confusion matrix with enhanced analysis.
    
    Provides:
    - Raw confusion matrix
    - Normalized confusion matrix
    - Per-class metrics
    - Visualization data
    """
    
    matrix: np.ndarray
    labels: List[str]
    
    @property
    def n_classes(self) -> int:
        """Number of classes."""
        return len(self.labels)
    
    @property
    def total(self) -> int:
        """Total predictions."""
        return int(self.matrix.sum())
    
    def get_normalized(self, axis: int = 0) -> np.ndarray:
        """
        Get normalized confusion matrix.
        
        Args:
            axis: 0 for row-normalized, 1 for column-normalized
            
        Returns:
            Normalized matrix
        """
        with np.errstate(divide="ignore", invalid="ignore"):
            normalized = np.divide(
                self.matrix,
                self.matrix.sum(axis=axis, keepdims=True),
            )
            normalized = np.nan_to_num(normalized, 0)
        return normalized
    
    def get_per_class_accuracy(self) -> Dict[str, float]:
        """Get per-class accuracy."""
        accuracies = {}
        for i, label in enumerate(self.labels):
            class_total = self.matrix[i].sum()
            if class_total > 0:
                accuracies[label] = float(self.matrix[i, i] / class_total)
            else:
                accuracies[label] = 0.0
        return accuracies
    
    def get_per_class_precision(self) -> Dict[str, float]:
        """Get per-class precision."""
        precisions = {}
        for i, label in enumerate(self.labels):
            col_total = self.matrix[:, i].sum()
            if col_total > 0:
                precisions[label] = float(self.matrix[i, i] / col_total)
            else:
                precisions[label] = 0.0
        return precisions
    
    def get_per_class_recall(self) -> Dict[str, float]:
        """Get per-class recall."""
        recalls = {}
        for i, label in enumerate(self.labels):
            row_total = self.matrix[i].sum()
            if row_total > 0:
                recalls[label] = float(self.matrix[i, i] / row_total)
            else:
                recalls[label] = 0.0
        return recalls
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "matrix": self.matrix.tolist(),
            "labels": self.labels,
            "n_classes": self.n_classes,
            "total": self.total,
            "normalized_row": self.get_normalized(axis=0).tolist(),
            "normalized_col": self.get_normalized(axis=1).tolist(),
            "per_class_accuracy": self.get_per_class_accuracy(),
            "per_class_precision": self.get_per_class_precision(),
            "per_class_recall": self.get_per_class_recall(),
        }


# ============================================================================
# Evaluation Result
# ============================================================================

@dataclass
class EvaluationResult:
    """
    Complete evaluation result.
    
    Aggregates all metrics and provides serialization.
    """
    
    task_name: str
    metric_values: Dict[str, float]
    detailed_metrics: Dict[str, Any]
    predictions: List[Any]
    references: List[Any]
    num_samples: int
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_name": self.task_name,
            "metric_values": self.metric_values,
            "detailed_metrics": self.detailed_metrics,
            "num_samples": self.num_samples,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }
    
    def to_json(self, file_path: Optional[str] = None) -> str:
        """
        Convert to JSON string.
        
        Args:
            file_path: Optional path to save JSON
            
        Returns:
            JSON string
        """
        data = self.to_dict()
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        
        return json_str
    
    @classmethod
    def from_json(cls, json_str: str) -> EvaluationResult:
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(
            task_name=data["task_name"],
            metric_values=data["metric_values"],
            detailed_metrics=data["detailed_metrics"],
            predictions=[],  # Not serialized
            references=[],   # Not serialized
            num_samples=data["num_samples"],
            execution_time=data["execution_time"],
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# Utility Functions
# ============================================================================

def load_jsonl_predictions(
    file_path: str,
    label_key: str = "label",
    predict_key: str = "predict",
) -> Tuple[List[Any], List[Any]]:
    """
    Load predictions from JSONL file in StarWhisperED format.
    
    Format: {"label": "...", "predict": "..."}
    
    Args:
        file_path: Path to JSONL file
        label_key: Key for ground truth label
        predict_key: Key for predicted label
        
    Returns:
        Tuple of (references, predictions)
    """
    references = []
    predictions = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                references.append(data.get(label_key))
                predictions.append(data.get(predict_key))
    
    return references, predictions


def compute_metrics(
    predictions: List[Any],
    references: List[Any],
    metrics: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compute evaluation metrics.
    
    Args:
        predictions: List of predictions
        references: List of ground truth labels
        metrics: List of metric names to compute
        labels: List of all possible labels
        
    Returns:
        Dictionary with metric results
    """
    if len(predictions) != len(references):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions, "
            f"{len(references)} references"
        )
    
    results = {}
    
    # Default metrics
    if metrics is None:
        metrics = ["accuracy", "f1_weighted", "f1_macro"]
    
    # Accuracy
    if "accuracy" in metrics:
        results["accuracy"] = accuracy_score(references, predictions)
    
    # F1 scores
    if "f1_weighted" in metrics:
        results["f1_weighted"] = f1_score(
            references, predictions, average="weighted", labels=labels, zero_division=0
        )
    
    if "f1_macro" in metrics:
        results["f1_macro"] = f1_score(
            references, predictions, average="macro", labels=labels, zero_division=0
        )
    
    if "f1_micro" in metrics:
        results["f1_micro"] = f1_score(
            references, predictions, average="micro", labels=labels, zero_division=0
        )
    
    # Precision
    if "precision_weighted" in metrics:
        results["precision_weighted"] = precision_score(
            references, predictions, average="weighted", labels=labels, zero_division=0
        )
    
    if "precision_macro" in metrics:
        results["precision_macro"] = precision_score(
            references, predictions, average="macro", labels=labels, zero_division=0
        )
    
    # Recall
    if "recall_weighted" in metrics:
        results["recall_weighted"] = recall_score(
            references, predictions, average="weighted", labels=labels, zero_division=0
        )
    
    if "recall_macro" in metrics:
        results["recall_macro"] = recall_score(
            references, predictions, average="macro", labels=labels, zero_division=0
        )
    
    # Confusion matrix
    if "confusion_matrix" in metrics:
        cm = confusion_matrix(references, predictions, labels=labels)
        results["confusion_matrix"] = cm.tolist()
        results["confusion_matrix_obj"] = ConfusionMatrix(cm, labels or [])
    
    # Classification report
    if "classification_report" in metrics:
        class_metrics = ClassificationMetrics()
        results["classification_report"] = class_metrics.detailed_compute(
            predictions, references, labels=labels
        )
    
    return results


# ============================================================================
# Additional Metric Functions
# ============================================================================

@MetricRegistry.register("accuracy")
def accuracy_fn(predictions: List, references: List, **kwargs) -> float:
    """Compute accuracy."""
    return accuracy_score(references, predictions)


@MetricRegistry.register("f1_weighted")
def f1_weighted_fn(predictions: List, references: List, **kwargs) -> float:
    """Compute weighted F1."""
    labels = kwargs.get("labels")
    return f1_score(references, predictions, average="weighted", labels=labels, zero_division=0)


@MetricRegistry.register("f1_macro")
def f1_macro_fn(predictions: List, references: List, **kwargs) -> float:
    """Compute macro F1."""
    labels = kwargs.get("labels")
    return f1_score(references, predictions, average="macro", labels=labels, zero_division=0)


@MetricRegistry.register("precision_weighted")
def precision_weighted_fn(predictions: List, references: List, **kwargs) -> float:
    """Compute weighted precision."""
    labels = kwargs.get("labels")
    return precision_score(references, predictions, average="weighted", labels=labels, zero_division=0)


@MetricRegistry.register("recall_weighted")
def recall_weighted_fn(predictions: List, references: List, **kwargs) -> float:
    """Compute weighted recall."""
    labels = kwargs.get("labels")
    return recall_score(references, predictions, average="weighted", labels=labels, zero_division=0)
