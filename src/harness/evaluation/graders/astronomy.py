"""
Astronomy Grader - Specialized grading for astronomical tasks

Provides domain-specific grading for astronomy:
- Spectral line identification evaluation
- Photometric measurements with tolerance
- Coordinate matching with spherical geometry
- Redshift measurement with tolerance

This module enhances the base AstronomyGrader with specialized graders
for specific astronomical measurement types.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from harness.evaluation.graders.base import (
    BaseGrader,
    GraderResult,
    GraderRegistry,
    register_grader,
)


# ============================================================================
# Spectral Line Grader
# ============================================================================

@register_grader("spectral_line")
class SpectralLineGrader(BaseGrader):
    """
    Grader for spectral line identification tasks.
    
    Evaluates how well detected spectral lines match reference lines.
    
    Configuration:
        - tolerance_angstrom: Wavelength matching tolerance in Angstrom (default: 1.0)
        - min_match_score: Minimum score for a line to be considered matched (default: 0.8)
    
    Metrics:
        - precision: Fraction of predicted lines that match reference
        - recall: Fraction of reference lines that were found
        - f1: Harmonic mean of precision and recall
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.tolerance_angstrom = self.config.get("tolerance_angstrom", 1.0)
        self.min_match_score = self.config.get("min_match_score", 0.8)
    
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade spectral line identification.
        
        Args:
            prediction: Dict with 'lines' list (wavelengths) or 'wavelengths' list
            reference: Dict with 'lines' list (wavelengths) or 'wavelengths' list
            
        Returns:
            GraderResult with precision, recall, F1 score
        """
        pred_lines = self._extract_lines(prediction)
        ref_lines = self._extract_lines(reference)
        
        if not ref_lines:
            return GraderResult(
                score=0.0 if pred_lines else 1.0,
                passed=False,
                details={"error": "No reference lines provided"},
                metadata={"grader": "spectral_line"},
            )
        
        if not pred_lines:
            return GraderResult(
                score=0.0,
                passed=False,
                details={
                    "pred_lines": 0,
                    "ref_lines": len(ref_lines),
                    "matched": 0,
                },
                metadata={"grader": "spectral_line"},
            )
        
        # Match lines within tolerance
        matched_pred, matched_ref = self._match_lines(pred_lines, ref_lines)
        
        # Calculate metrics
        precision = len(matched_pred) / len(pred_lines) if pred_lines else 0.0
        recall = len(matched_ref) / len(ref_lines) if ref_lines else 0.0
        
        if precision + recall > 0:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = 0.0
        
        # Also consider wavelength accuracy for matched lines
        if matched_pred:
            wavelength_errors = [
                abs(pred_lines[p] - ref_lines[r])
                for p, r in zip(matched_pred, matched_ref)
            ]
            mean_error = np.mean(wavelength_errors)
            accuracy_score = max(0.0, 1.0 - mean_error / self.tolerance_angstrom)
        else:
            accuracy_score = 0.0
        
        # Combined score: F1 for identification + accuracy for matched lines
        combined_score = 0.7 * f1 + 0.3 * accuracy_score
        
        return GraderResult(
            score=combined_score,
            passed=combined_score >= self.threshold,
            details={
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "accuracy_score": accuracy_score,
                "pred_lines": len(pred_lines),
                "ref_lines": len(ref_lines),
                "matched": len(matched_pred),
                "mean_wavelength_error": float(np.mean(wavelength_errors)) if matched_pred else None,
            },
            metadata={
                "grader": "spectral_line",
                "tolerance": self.tolerance_angstrom,
            },
        )
    
    def _extract_lines(self, data: Any) -> List[float]:
        """Extract spectral line wavelengths from data."""
        if isinstance(data, dict):
            if "lines" in data:
                return [float(w) for w in data["lines"]]
            elif "wavelengths" in data:
                return [float(w) for w in data["wavelengths"]]
            elif "predicted_lines" in data:
                return [float(w) for w in data["predicted_lines"]]
        elif isinstance(data, (list, tuple)):
            return [float(w) for w in data]
        return []
    
    def _match_lines(
        self,
        pred_lines: List[float],
        ref_lines: List[float],
    ) -> Tuple[List[int], List[int]]:
        """
        Match predicted lines to reference lines.
        
        Returns:
            Tuple of (matched_pred_indices, matched_ref_indices)
        """
        matched_pred = []
        matched_ref = []
        
        ref_used = set()
        
        for i, pred_wl in enumerate(pred_lines):
            best_match_idx = None
            best_match_error = float('inf')
            
            for j, ref_wl in enumerate(ref_lines):
                if j in ref_used:
                    continue
                
                error = abs(pred_wl - ref_wl)
                if error < best_match_error and error <= self.tolerance_angstrom * self.min_match_score:
                    best_match_error = error
                    best_match_idx = j
            
            if best_match_idx is not None:
                matched_pred.append(i)
                matched_ref.append(best_match_idx)
                ref_used.add(best_match_idx)
        
        return matched_pred, matched_ref


# ============================================================================
# Photometric Grader
# ============================================================================

@register_grader("photometric")
class PhotometricGrader(BaseGrader):
    """
    Grader for photometric measurements.
    
    Evaluates magnitude, color index, and flux measurements.
    
    Configuration:
        - magnitude_tolerance: Tolerance for magnitude comparison (default: 0.1)
        - color_tolerance: Tolerance for color index comparison (default: 0.05)
        - flux_tolerance: Relative tolerance for flux comparison (default: 0.1)
    
    Supports:
        - Direct magnitude comparison
        - Color index (mag1 - mag2) comparison
        - Flux ratio comparison
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.magnitude_tolerance = self.config.get("magnitude_tolerance", 0.1)
        self.color_tolerance = self.config.get("color_tolerance", 0.05)
        self.flux_tolerance = self.config.get("flux_tolerance", 0.1)
    
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade photometric measurement.
        
        Args:
            prediction: Dict with 'magnitude', 'color', 'flux', or filter magnitudes
            reference: Dict with same structure
            
        Returns:
            GraderResult with measurement accuracy
        """
        pred_mag = self._extract_magnitude(prediction)
        ref_mag = self._extract_magnitude(reference)
        
        if pred_mag is None and ref_mag is None:
            return GraderResult(
                score=1.0,
                passed=True,
                details={"message": "No magnitudes to compare"},
                metadata={"grader": "photometric"},
            )
        
        if pred_mag is None or ref_mag is None:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": "Missing magnitude in prediction or reference"},
                metadata={"grader": "photometric"},
            )
        
        # Calculate magnitude error
        mag_error = abs(pred_mag - ref_mag)
        
        # Score based on tolerance
        if mag_error <= self.magnitude_tolerance:
            score = 1.0 - (mag_error / self.magnitude_tolerance) * 0.5
        else:
            score = max(0.0, 0.5 - (mag_error - self.magnitude_tolerance) * 0.1)
        
        # Also try color comparison if available
        pred_color = self._extract_color(prediction)
        ref_color = self._extract_color(reference)
        
        color_details = {}
        if pred_color is not None and ref_color is not None:
            color_error = abs(pred_color - ref_color)
            color_score = max(0.0, 1.0 - color_error / self.color_tolerance)
            color_details = {
                "color": pred_color,
                "ref_color": ref_color,
                "color_error": color_error,
                "color_score": color_score,
            }
            # Combine scores
            score = 0.6 * score + 0.4 * color_score
        
        return GraderResult(
            score=score,
            passed=score >= self.threshold,
            details={
                "magnitude": pred_mag,
                "reference_magnitude": ref_mag,
                "magnitude_error": mag_error,
                **color_details,
            },
            metadata={
                "grader": "photometric",
                "magnitude_tolerance": self.magnitude_tolerance,
            },
        )
    
    def _extract_magnitude(self, data: Any) -> Optional[float]:
        """Extract magnitude from data."""
        if isinstance(data, dict):
            if "magnitude" in data:
                return float(data["magnitude"])
            elif "mag" in data:
                return float(data["mag"])
            elif "Vmag" in data:
                return float(data["Vmag"])
            elif "value" in data:
                return float(data["value"])
            # Check for filter magnitudes
            for key in ["g", "r", "i", "z", "u", "B", "V", "R", "I", "J", "H", "K"]:
                if key in data:
                    return float(data[key])
        elif isinstance(data, (int, float)):
            return float(data)
        return None
    
    def _extract_color(self, data: Any) -> Optional[float]:
        """Extract color index from data."""
        if isinstance(data, dict):
            if "color" in data:
                return float(data["color"])
            elif "B-V" in data:
                return float(data["B-V"])
            elif "g-r" in data:
                return float(data["g-r"])
            elif "u-g" in data:
                return float(data["u-g"])
            elif "r-i" in data:
                return float(data["r-i"])
            elif "i-z" in data:
                return float(data["i-z"])
        return None


# ============================================================================
# Coordinate Grader
# ============================================================================

@register_grader("coordinate")
class CoordinateGrader(BaseGrader):
    """
    Grader for celestial coordinate matching.
    
    Evaluates RA/Dec coordinate predictions using spherical geometry.
    
    Configuration:
        - tolerance_arcsec: Angular tolerance in arcseconds (default: 10.0)
        - use_sexagesimal: Accept sexagesimal format strings (default: True)
    
    Uses the Vincenty formula for accurate angular separation on sphere.
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.tolerance_arcsec = self.config.get("tolerance_arcsec", 10.0)
        self.use_sexagesimal = self.config.get("use_sexagesimal", True)
        self.tolerance_deg = self.tolerance_arcsec / 3600.0  # Convert to degrees
    
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade celestial coordinate prediction.
        
        Args:
            prediction: Dict with 'ra', 'dec' (degrees or sexagesimal strings)
            reference: Dict with 'ra', 'dec' (degrees or sexagesimal strings)
            
        Returns:
            GraderResult with angular separation and accuracy
        """
        pred_ra, pred_dec = self._extract_coordinates(prediction, "pred")
        ref_ra, ref_dec = self._extract_coordinates(reference, "ref")
        
        if ref_ra is None or ref_dec is None:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": "Missing reference coordinates"},
                metadata={"grader": "coordinate"},
            )
        
        if pred_ra is None or pred_dec is None:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": "Missing predicted coordinates"},
                metadata={"grader": "coordinate"},
            )
        
        # Calculate angular separation
        sep_arcsec = self._angular_separation(
            pred_ra, pred_dec, ref_ra, ref_dec
        )
        
        # Calculate score
        if sep_arcsec <= self.tolerance_arcsec:
            score = 1.0 - (sep_arcsec / self.tolerance_arcsec) * 0.5
        else:
            # Beyond tolerance - still give partial credit
            score = max(0.0, 0.5 - (sep_arcsec - self.tolerance_arcsec) / self.tolerance_arcsec * 0.3)
        
        return GraderResult(
            score=score,
            passed=score >= self.threshold and sep_arcsec <= self.tolerance_arcsec,
            details={
                "pred_ra": pred_ra,
                "pred_dec": pred_dec,
                "ref_ra": ref_ra,
                "ref_dec": ref_dec,
                "angular_separation_arcsec": sep_arcsec,
                "tolerance_arcsec": self.tolerance_arcsec,
                "within_tolerance": sep_arcsec <= self.tolerance_arcsec,
            },
            metadata={
                "grader": "coordinate",
                "tolerance_arcsec": self.tolerance_arcsec,
            },
        )
    
    def _extract_coordinates(self, data: Any, prefix: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract RA/Dec from data."""
        if isinstance(data, dict):
            # Try numeric values
            ra = data.get("ra") or data.get("RA")
            dec = data.get("dec") or data.get("DEC")
            
            if ra is not None and dec is not None:
                # Check if sexagesimal
                if isinstance(ra, str) and self.use_sexagesimal:
                    ra = self._parse_ra(ra)
                else:
                    ra = float(ra)
                
                if isinstance(dec, str) and self.use_sexagesimal:
                    dec = self._parse_dec(dec)
                else:
                    dec = float(dec)
                
                return ra, dec
            
            # Try coordinate array [ra, dec]
            if "value" in data and isinstance(data["value"], (list, tuple)):
                coords = data["value"]
                if len(coords) >= 2:
                    return float(coords[0]), float(coords[1])
        
        return None, None
    
    def _parse_ra(self, ra_str: str) -> Optional[float]:
        """Parse RA from sexagesimal string to degrees."""
        try:
            # Handle formats: "10h30m15.5s", "10:30:15.5", "10 30 15.5", "155.56458"
            ra_str = str(ra_str).strip()
            
            # If it looks like decimal degrees already
            if "h" not in ra_str and "m" not in ra_str and ":" not in ra_str:
                try:
                    return float(ra_str)
                except ValueError:
                    pass
            
            # Parse sexagesimal
            import re
            match = re.match(r"(\d+)h\s*(\d+)m\s*([\d.]+)s", ra_str)
            if match:
                h, m, s = match.groups()
                return (float(h) + float(m)/60 + float(s)/3600) * 15
            
            match = re.match(r"(\d+):(\d+):([\d.]+)", ra_str)
            if match:
                h, m, s = match.groups()
                return (float(h) + float(m)/60 + float(s)/3600) * 15
            
            return None
        except Exception:
            return None
    
    def _parse_dec(self, dec_str: str) -> Optional[float]:
        """Parse Dec from sexagesimal string to degrees."""
        try:
            dec_str = str(dec_str).strip()
            
            # If it looks like decimal degrees already (no d, ', ")
            if "d" not in dec_str and "'" not in dec_str and '"' not in dec_str and ":" not in dec_str:
                try:
                    return float(dec_str)
                except ValueError:
                    pass
            
            # Parse sexagesimal
            import re
            match = re.match(r"([+-]?\d+)d\s*(\d+)'?\s*([\d.]+)?\"?", dec_str)
            if match:
                d, m, s = match.groups()
                s = s or "0"
                sign = -1 if d.startswith("-") else 1
                d = abs(float(d))
                return sign * (d + float(m)/60 + float(s)/3600)
            
            match = re.match(r"([+-]?\d+):(\d+):([\d.]+)", dec_str)
            if match:
                d, m, s = match.groups()
                sign = -1 if d.startswith("-") else 1
                d = abs(float(d))
                return sign * (d + float(m)/60 + float(s)/3600)
            
            return None
        except Exception:
            return None
    
    def _angular_separation(
        self,
        ra1: float,
        dec1: float,
        ra2: float,
        dec2: float,
    ) -> float:
        """
        Calculate angular separation between two points in arcseconds.
        
        Uses the Vincenty formula for better accuracy at small angles.
        """
        # Convert to radians
        ra1_rad = np.radians(ra1)
        dec1_rad = np.radians(dec1)
        ra2_rad = np.radians(ra2)
        dec2_rad = np.radians(dec2)
        
        # Calculate separation using haversine formula
        delta_ra = ra2_rad - ra1_rad
        
        sin_dec1 = np.sin(dec1_rad)
        cos_dec1 = np.cos(dec1_rad)
        sin_dec2 = np.sin(dec2_rad)
        cos_dec2 = np.cos(dec2_rad)
        
        cos_delta_ra = np.cos(delta_ra)
        sin_delta_ra = np.sin(delta_ra)
        
        # Calculate angular distance
        y = np.sqrt(
            (cos_dec2 * sin_delta_ra)**2 +
            (cos_dec1 * sin_dec2 - sin_dec1 * cos_dec2 * cos_delta_ra)**2
        )
        x = sin_dec1 * sin_dec2 + cos_dec1 * cos_dec2 * cos_delta_ra
        
        sep_rad = np.arctan2(y, x)
        sep_deg = np.degrees(sep_rad)
        
        return sep_deg * 3600  # Convert to arcseconds


# ============================================================================
# Redshift Grader
# ============================================================================

@register_grader("redshift")
class RedshiftGrader(BaseGrader):
    """
    Grader for redshift measurements.
    
    Evaluates spectroscopic redshift predictions with appropriate tolerance.
    
    Configuration:
        - tolerance_relative: Relative tolerance (z_err / z) (default: 0.01)
        - tolerance_absolute: Absolute tolerance for low-z (default: 0.001)
        - low_z_threshold: Threshold for 'low-z' regime (default: 0.1)
    
    Notes:
        - For z < low_z_threshold: use absolute tolerance
        - For z >= low_z_threshold: use relative tolerance
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.tolerance_relative = self.config.get("tolerance_relative", 0.01)
        self.tolerance_absolute = self.config.get("tolerance_absolute", 0.001)
        self.low_z_threshold = self.config.get("low_z_threshold", 0.1)
    
    def grade(
        self,
        prediction: Any,
        reference: Any,
        **kwargs,
    ) -> GraderResult:
        """
        Grade redshift measurement.
        
        Args:
            prediction: Dict with 'redshift', 'z', or 'value'
            reference: Dict with same structure
            
        Returns:
            GraderResult with redshift accuracy
        """
        pred_z = self._extract_redshift(prediction, "pred")
        ref_z = self._extract_redshift(reference, "ref")
        
        if ref_z is None:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": "Missing reference redshift"},
                metadata={"grader": "redshift"},
            )
        
        if pred_z is None:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": "Missing predicted redshift"},
                metadata={"grader": "redshift"},
            )
        
        # Calculate error
        abs_error = abs(pred_z - ref_z)
        
        # Determine appropriate tolerance
        if ref_z < self.low_z_threshold:
            # Low redshift: use absolute tolerance
            tolerance = self.tolerance_absolute
            normalized_error = abs_error / self.tolerance_absolute if self.tolerance_absolute > 0 else 0
        else:
            # High redshift: use relative tolerance
            tolerance = ref_z * self.tolerance_relative
            normalized_error = abs_error / tolerance if tolerance > 0 else 0
        
        # Calculate score
        if abs_error <= tolerance:
            score = 1.0 - normalized_error * 0.5
        else:
            score = max(0.0, 0.5 - (abs_error - tolerance) / tolerance * 0.3)
        
        # Additional metrics
        velocity = 299792.458 * (pred_z - ref_z) / (1 + ref_z)  # km/s
        velocity_error = abs(velocity)
        
        return GraderResult(
            score=score,
            passed=score >= self.threshold and abs_error <= tolerance,
            details={
                "redshift": pred_z,
                "reference_redshift": ref_z,
                "absolute_error": abs_error,
                "relative_error": abs_error / ref_z if ref_z != 0 else 0,
                "tolerance": tolerance,
                "velocity_error_km_s": velocity_error,
                "within_tolerance": abs_error <= tolerance,
            },
            metadata={
                "grader": "redshift",
                "tolerance_relative": self.tolerance_relative,
                "tolerance_absolute": self.tolerance_absolute,
            },
        )
    
    def _extract_redshift(self, data: Any, prefix: str) -> Optional[float]:
        """Extract redshift value from data."""
        if isinstance(data, dict):
            for key in ["redshift", "z", "value"]:
                if key in data:
                    try:
                        return float(data[key])
                    except (ValueError, TypeError):
                        continue
        elif isinstance(data, (int, float)):
            return float(data)
        return None


# ============================================================================
# Legacy Astronomy Grader (enhanced)
# ============================================================================

@register_grader("astronomy")
class AstronomyGrader(BaseGrader):
    """
    Astronomy-specific grader.
    
    Provides specialized grading for:
    - Redshift comparison with tolerance
    - Coordinate matching (RA/Dec within tolerance)
    - Magnitude comparison
    - Spectral line identification
    
    This is the main astronomy grader that delegates to specialized graders.
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        
        # Create specialized graders
        self.spectral_line_grader = SpectralLineGrader(config)
        self.photometric_grader = PhotometricGrader(config)
        self.coordinate_grader = CoordinateGrader(config)
        self.redshift_grader = RedshiftGrader(config)
        
        # Legacy tolerance settings (for backward compatibility)
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
        
        if task_type == "redshift":
            return self.redshift_grader.grade(prediction, reference)
        elif task_type == "coordinate":
            return self.coordinate_grader.grade(prediction, reference)
        elif task_type == "magnitude" or task_type == "photometric":
            return self.photometric_grader.grade(prediction, reference)
        elif task_type == "spectral_line":
            return self.spectral_line_grader.grade(prediction, reference)
        else:
            return GraderResult(
                score=0.0,
                passed=False,
                details={"error": f"Unknown task type: {task_type}"},
                metadata={"grader": "astronomy"},
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
        
        grader = self._get_grader_for_type(task_type)
        
        for pred, ref in zip(predictions, references):
            result = grader.grade(pred, ref)
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
    
    def _get_grader_for_type(self, task_type: str) -> BaseGrader:
        """Get the appropriate grader for a task type."""
        if task_type == "redshift":
            return self.redshift_grader
        elif task_type == "coordinate":
            return self.coordinate_grader
        elif task_type == "magnitude" or task_type == "photometric":
            return self.photometric_grader
        elif task_type == "spectral_line":
            return self.spectral_line_grader
        else:
            return self.redshift_grader


# ============================================================================
# Registry Registration
# ============================================================================

# Register all graders
GraderRegistry._factories["spectral_line"] = SpectralLineGrader
GraderRegistry._factories["photometric"] = PhotometricGrader
GraderRegistry._factories["coordinate"] = CoordinateGrader
GraderRegistry._factories["redshift"] = RedshiftGrader
GraderRegistry._factories["astronomy"] = AstronomyGrader
