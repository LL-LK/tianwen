"""
Exact Match Grader - String equality grading

Provides strict equality-based grading for classification tasks.
"""

from typing import Any, List, Optional

from harness.evaluation.graders.base import (
    BaseGrader,
    GraderResult,
    GraderRegistry,
    register_grader,
)


@register_grader("exact_match")
class ExactMatchGrader(BaseGrader):
    """
    Exact match grader.
    
    Compares prediction and reference using strict equality.
    Case-sensitive by default, configurable.
    
    Useful for:
    - Classification with exact labels
    - Multiple choice questions
    - Categorical predictions
    
    Configuration:
        - case_sensitive: Whether comparison is case-sensitive (default: True)
        - normalize_whitespace: Whether to normalize whitespace (default: True)
        - strip: Whether to strip strings (default: True)
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.case_sensitive = self.config.get("case_sensitive", True)
        self.normalize_whitespace = self.config.get("normalize_whitespace", True)
        self.strip = self.config.get("strip", True)
    
    def _preprocess(self, text: str) -> str:
        """Preprocess text before comparison."""
        if self.strip:
            text = text.strip()
        if self.normalize_whitespace:
            text = " ".join(text.split())
        if not self.case_sensitive:
            text = text.lower()
        return text
    
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade a single exact match prediction.
        
        Args:
            prediction: Predicted label
            reference: Ground truth label
            
        Returns:
            GraderResult with score (1.0 for exact match, 0.0 otherwise)
        """
        # Convert to strings
        pred_str = str(prediction) if prediction is not None else ""
        ref_str = str(reference) if reference is not None else ""
        
        # Preprocess
        pred_processed = self._preprocess(pred_str)
        ref_processed = self._preprocess(ref_str)
        
        # Exact match
        is_correct = pred_processed == ref_processed
        score = 1.0 if is_correct else 0.0
        
        return GraderResult(
            score=score,
            passed=is_correct,
            details={
                "prediction": pred_processed,
                "reference": ref_processed,
                "case_sensitive": self.case_sensitive,
            },
            metadata={"grader": "exact_match"},
        )
    
    def grade_batch(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> GraderResult:
        """
        Grade a batch with detailed results.
        
        Returns aggregated GraderResult with per-sample scores.
        """
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have same length")
        
        scores = []
        details = []
        
        for pred, ref in zip(predictions, references):
            result = self.grade(pred, ref, **kwargs)
            scores.append(result.score)
            details.append(result.details)
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return GraderResult(
            score=avg_score,
            passed=avg_score >= self.threshold,
            details={
                "individual_scores": scores,
                "num_samples": len(scores),
                "correct_count": sum(scores),
            },
            metadata={"grader": "exact_match", "batch_size": len(predictions)},
        )


# Register with explicit factory for custom config
GraderRegistry._factories["exact_match"] = ExactMatchGrader
