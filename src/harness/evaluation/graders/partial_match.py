"""
Partial Match Grader - Flexible matching with tolerance

Provides flexible grading with partial match capabilities:
- Substring matching
- Fuzzy matching with thresholds
- Token-based comparison
"""

import re
from difflib import SequenceMatcher
from typing import Any, List, Optional, Set

from harness.evaluation.graders.base import (
    BaseGrader,
    GraderResult,
    GraderRegistry,
    register_grader,
)


@register_grader("partial_match")
class PartialMatchGrader(BaseGrader):
    """
    Partial match grader with multiple matching strategies.
    
    Strategies:
    - substring: Check if prediction is substring of reference or vice versa
    - fuzzy: Fuzzy string matching with similarity ratio
    - token: Token-based set intersection
    
    Configuration:
        - strategy: Matching strategy ("substring", "fuzzy", "token")
        - similarity_threshold: Minimum similarity for fuzzy match (0-1)
        - token_overlap_ratio: Minimum token overlap for token strategy
    """
    
    STRATEGIES = ["substring", "fuzzy", "token"]
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.strategy = self.config.get("strategy", "fuzzy")
        self.similarity_threshold = self.config.get("similarity_threshold", 0.8)
        self.token_overlap_ratio = self.config.get("token_overlap_ratio", 0.5)
        
        if self.strategy not in self.STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{self.strategy}'. "
                f"Choose from: {self.STRATEGIES}"
            )
    
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade a single partial match prediction.
        
        Args:
            prediction: Predicted text
            reference: Ground truth text
            
        Returns:
            GraderResult with similarity score
        """
        pred_str = str(prediction).lower() if prediction is not None else ""
        ref_str = str(reference).lower() if reference is not None else ""
        
        if self.strategy == "substring":
            score, details = self._substring_match(pred_str, ref_str)
        elif self.strategy == "fuzzy":
            score, details = self._fuzzy_match(pred_str, ref_str)
        elif self.strategy == "token":
            score, details = self._token_match(pred_str, ref_str)
        else:
            score, details = 0.0, {}
        
        return GraderResult(
            score=score,
            passed=score >= self.threshold,
            details=details,
            metadata={"grader": "partial_match", "strategy": self.strategy},
        )
    
    def _substring_match(
        self,
        pred: str,
        ref: str,
    ) -> tuple[float, dict]:
        """
        Substring matching.
        
        Returns 1.0 if either is substring of the other.
        """
        if not pred or not ref:
            return 0.0, {"match_type": "substring", "found": False}
        
        found = pred in ref or ref in pred
        score = 1.0 if found else 0.0
        
        return score, {
            "match_type": "substring",
            "found": found,
            "pred_in_ref": pred in ref,
            "ref_in_pred": ref in pred,
        }
    
    def _fuzzy_match(
        self,
        pred: str,
        ref: str,
    ) -> tuple[float, dict]:
        """
        Fuzzy string matching using SequenceMatcher.
        
        Returns similarity ratio (0-1).
        """
        if not pred or not ref:
            return 0.0, {"match_type": "fuzzy", "ratio": 0.0}
        
        ratio = SequenceMatcher(None, pred, ref).ratio()
        
        return ratio, {
            "match_type": "fuzzy",
            "ratio": ratio,
            "threshold": self.similarity_threshold,
            "meets_threshold": ratio >= self.similarity_threshold,
        }
    
    def _token_match(
        self,
        pred: str,
        ref: str,
    ) -> tuple[float, dict]:
        """
        Token-based matching.
        
        Returns Jaccard similarity of token sets.
        """
        if not pred or not ref:
            return 0.0, {"match_type": "token", "jaccard": 0.0}
        
        # Tokenize
        pred_tokens = set(re.findall(r'\w+', pred.lower()))
        ref_tokens = set(re.findall(r'\w+', ref.lower()))
        
        if not pred_tokens or not ref_tokens:
            return 0.0, {"match_type": "token", "jaccard": 0.0}
        
        # Jaccard similarity
        intersection = pred_tokens & ref_tokens
        union = pred_tokens | ref_tokens
        jaccard = len(intersection) / len(union) if union else 0.0
        
        return jaccard, {
            "match_type": "token",
            "jaccard": jaccard,
            "threshold": self.token_overlap_ratio,
            "pred_tokens": list(pred_tokens),
            "ref_tokens": list(ref_tokens),
            "intersection": list(intersection),
        }
    
    def grade_batch(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> GraderResult:
        """Grade a batch of predictions."""
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have same length")
        
        scores = []
        all_details = []
        
        for pred, ref in zip(predictions, references):
            result = self.grade(pred, ref, **kwargs)
            scores.append(result.score)
            all_details.append(result.details)
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return GraderResult(
            score=avg_score,
            passed=avg_score >= self.threshold,
            details={
                "strategy": self.strategy,
                "individual_scores": scores,
                "num_samples": len(scores),
            },
            metadata={
                "grader": "partial_match",
                "batch_size": len(predictions),
                "similarity_threshold": self.similarity_threshold,
            },
        )


GraderRegistry._factories["partial_match"] = PartialMatchGrader
