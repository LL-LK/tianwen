"""
Astronomy Grader - Specialized grading for astronomical tasks

Provides domain-specific grading for astronomy:
- Spectral analysis evaluation
- Coordinate matching with tolerance
- Photometric magnitude comparison
"""

from typing import Any, List, Optional, Tuple
import numpy as np

from harness.evaluation.graders.base import (
    BaseGrader,
    GraderResult,
    GraderRegistry,
    register_grader,
)


@register_grader("astronomy")
class AstronomyGrader(BaseGrader):
    """
    Astronomy-specific grader.
    
    Provides specialized grading for:
    - Redshift comparison with tolerance
    - Coordinate matching (RA/Dec within tolerance)
    - Spectral line identification
    - Photometric measurements
    
    Configuration:
        - redshift_tolerance: Relative tolerance for redshift (default: 0.01)
        - coord_tolerance_deg: Coordinate tolerance in degrees (default: 0.01)
        - magnitude_tolerance: Tolerance for magnitude (default: 0.1)
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.redshift_tolerance = self.config.get("redshift_tolerance", 0.01)
        self.coord_tolerance_deg = self.config.get("coord_tolerance_deg", 0.01)
        self.magnitude_tolerance = self.config.get("magnitude_tolerance", 0.1)
    
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade an astronomy prediction.
        
        Args:
            prediction: Dict with prediction data
            reference: Dict with reference data
            **kwargs: Must include "task_type" one of:
                - "redshift": Redshift comparison
                - "coordinate": RA/Dec comparison
                - "magnitude": Magnitude comparison
                - "spectral_line": Line identification
                
        Returns:
            GraderResult with score
        """
        task_type = kwargs.get("task_type", "redshift")
        
        if isinstance(prediction, dict) and isinstance(reference, dict):
            pred_data = prediction
            ref_data = reference
        else:
            # Assume simple value format
            pred_data = {"value": prediction}
            ref_data = {"value": reference}
        
        if task_type == "redshift":
            return self._grade_redshift(pred_data, ref_data)
        elif task_type == "coordinate":
            return self._grade_coordinate(pred_data, ref_data)
        elif task_type == "magnitude":
            return self._grade_magnitude(pred_data, ref_data)
        elif task_type == "spectral_line":
            return self._grade_spectral_line(pred_data, ref_data)
        else:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": f"Unknown task type: {task_type}"},
                metadata={"grader": "astronomy"},
            )
    
    def _grade_redshift(
        self,
        pred: dict,
        ref: dict,
    ) -> GraderResult:
        """Grade redshift prediction."""
        pred_z = float(pred.get("redshift", pred.get("value", 0)))
        ref_z = float(ref.get("redshift", ref.get("value", 0)))
        
        if ref_z == 0:
            score = 1.0 if pred_z == 0 else 0.0
        else:
            rel_error = abs(pred_z - ref_z) / ref_z
            score = max(0.0, 1.0 - rel_error / self.redshift_tolerance)
            score = 1.0 if score > 1.0 else score
        
        return GraderResult(
            score=score,
            passed=score >= self.threshold,
            details={
                "task_type": "redshift",
                "prediction": pred_z,
                "reference": ref_z,
                "relative_error": abs(pred_z - ref_z) / ref_z if ref_z != 0 else 0,
                "tolerance": self.redshift_tolerance,
            },
            metadata={"grader": "astronomy", "task_type": "redshift"},
        )
    
    def _grade_coordinate(
        self,
        pred: dict,
        ref: dict,
    ) -> GraderResult:
        """Grade coordinate prediction (RA/Dec)."""
        pred_ra = float(pred.get("ra", pred.get("value", [0, 0])[0]))
        pred_dec = float(pred.get("dec", pred.get("value", [0, 0])[1]))
        ref_ra = float(ref.get("ra", ref.get("value", [0, 0])[0]))
        ref_dec = float(ref.get("dec", ref.get("value", [0, 0])[1]))
        
        # Angular separation using spherical law of cosines
        ra_diff = np.radians(pred_ra - ref_ra)
        dec_mean = np.radians((pred_dec + ref_dec) / 2)
        
        sep = np.degrees(
            np.arccos(
                np.cos(np.radians(90 - pred_dec)) *
                np.cos(np.radians(90 - ref_dec)) +
                np.sin(np.radians(90 - pred_dec)) *
                np.sin(np.radians(90 - ref_dec)) *
                np.cos(ra_diff)
            )
        )
        
        score = max(0.0, 1.0 - sep / self.coord_tolerance_deg)
        score = 1.0 if score > 1.0 else score
        
        return GraderResult(
            score=score,
            passed=score >= self.threshold,
            details={
                "task_type": "coordinate",
                "pred_ra": pred_ra,
                "pred_dec": pred_dec,
                "ref_ra": ref_ra,
                "ref_dec": ref_dec,
                "angular_separation_deg": float(sep),
                "tolerance_deg": self.coord_tolerance_deg,
            },
            metadata={"grader": "astronomy", "task_type": "coordinate"},
        )
    
    def _grade_magnitude(
        self,
        pred: dict,
        ref: dict,
    ) -> GraderResult:
        """Grade photometric magnitude prediction."""
        pred_mag = float(pred.get("magnitude", pred.get("value", 0)))
        ref_mag = float(ref.get("magnitude", ref.get("value", 0)))
        
        error = abs(pred_mag - ref_mag)
        score = max(0.0, 1.0 - error / self.magnitude_tolerance)
        score = 1.0 if score > 1.0 else score
        
        return GraderResult(
            score=score,
            passed=score >= self.threshold,
            details={
                "task_type": "magnitude",
                "prediction": pred_mag,
                "reference": ref_mag,
                "error": error,
                "tolerance": self.magnitude_tolerance,
            },
            metadata={"grader": "astronomy", "task_type": "magnitude"},
        )
    
    def _grade_spectral_line(
        self,
        pred: dict,
        ref: dict,
    ) -> GraderResult:
        """Grade spectral line identification."""
        pred_lines = pred.get("lines", pred.get("wavelengths", []))
        ref_lines = ref.get("lines", ref.get("wavelengths", []))
        
        if not pred_lines or not ref_lines:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": "No spectral lines provided"},
                metadata={"grader": "astronomy", "task_type": "spectral_line"},
            )
        
        # Match lines within tolerance (1 Angstrom)
        tolerance = 1.0  # Angstrom
        matched = 0
        
        for pred_wl in pred_lines:
            for ref_wl in ref_lines:
                if abs(pred_wl - ref_wl) <= tolerance:
                    matched += 1
                    break
        
        # Score based on precision and recall
        precision = matched / len(pred_lines) if pred_lines else 0
        recall = matched / len(ref_lines) if ref_lines else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        return GraderResult(
            score=f1,
            passed=f1 >= self.threshold,
            details={
                "task_type": "spectral_line",
                "pred_lines": len(pred_lines),
                "ref_lines": len(ref_lines),
                "matched": matched,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            },
            metadata={"grader": "astronomy", "task_type": "spectral_line"},
        )
    
    def grade_batch(
        self,
        predictions: List[Any],
        references: List[Any],
        **kwargs,
    ) -> GraderResult:
        """Grade a batch of astronomy predictions."""
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have same length")
        
        task_type = kwargs.get("task_type", "redshift")
        scores = []
        all_details = []
        
        for pred, ref in zip(predictions, references):
            result = self.grade(pred, ref, task_type=task_type)
            scores.append(result.score)
            all_details.append(result.details)
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return GraderResult(
            score=avg_score,
            passed=avg_score >= self.threshold,
            details={
                "task_type": task_type,
                "individual_scores": scores,
                "num_samples": len(scores),
            },
            metadata={
                "grader": "astronomy",
                "task_type": task_type,
                "batch_size": len(predictions),
            },
        )


GraderRegistry._factories["astronomy"] = AstronomyGrader
