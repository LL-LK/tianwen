"""
Time Domain Astronomy Protocol - Time series analysis for TianwenAGI Harness

This module provides protocols for handling time-domain astronomical data
including transient sources, variable stars, and light curve analysis.

Includes:
- TransientProtocol: Transient source detection and classification
- VariableStarProtocol: Variable star analysis
- LightCurveProtocol: Light curve analysis and fitting

Reference: ZTF, ATLAS, LSST alert streams and time-domain surveys
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from harness.protocols.base import (
    BaseProtocol,
    Message,
    MessageRole,
    ProtocolResult,
    ProtocolSpec,
    ProtocolRegistry,
    protocol_plugin,
)
from harness.protocols.astronomy import AstronomyProtocol

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class LightCurvePoint:
    """A single point in a light curve."""
    time: float
    magnitude: float
    error: Optional[float] = None
    filter: Optional[str] = None
    flux: Optional[float] = None
    flux_error: Optional[float] = None
    catalog: Optional[str] = None
    instrument: Optional[str] = None


@dataclass
class LightCurve:
    """Collection of light curve points."""
    target_name: str
    points: List[LightCurvePoint] = field(default_factory=list)
    ra: Optional[float] = None
    dec: Optional[float] = None
    redshift: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def times(self) -> np.ndarray:
        return np.array([p.time for p in self.points])
    
    @property
    def magnitudes(self) -> np.ndarray:
        return np.array([p.magnitude for p in self.points])
    
    @property
    def errors(self) -> np.ndarray:
        return np.array([p.error if p.error else 0.0 for p in self.points])
    
    @property
    def num_points(self) -> int:
        return len(self.points)


@dataclass
class TransientAlert:
    """Alert data for a transient source."""
    name: str
    ra: float
    dec: float
    discovery_time: float
    discovery_mag: float
    classification: Optional[str] = None
    redshift: Optional[float] = None
    probability: Optional[float] = None
    host: Optional[Dict[str, Any]] = None
    cutouts: Optional[Dict[str, str]] = None  # URLs to reference images
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VariableStarAnalysis:
    """Analysis result for a variable star."""
    target_name: str
    period: Optional[float] = None
    period_error: Optional[float] = None
    amplitude: Optional[float] = None
    mean_mag: Optional[float] = None
    variable_type: Optional[str] = None
    goodness_of_fit: Optional[float] = None


# ============================================================================
# Base Time Domain Protocol
# ============================================================================

class TimeDomainProtocol(AstronomyProtocol):
    """
    Base class for time-domain astronomy protocols.
    
    Provides common functionality for analyzing temporal astronomical data.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._lightcurve: Optional[LightCurve] = None
    
    def set_lightcurve(
        self,
        times: Union[List[float], np.ndarray],
        magnitudes: Union[List[float], np.ndarray],
        errors: Optional[Union[List[float], np.ndarray]] = None,
        filters: Optional[List[str]] = None,
    ) -> LightCurve:
        """
        Set light curve data.
        
        Args:
            times: Array of observation times (MJD)
            magnitudes: Array of magnitudes
            errors: Optional array of magnitude errors
            filters: Optional list of filter names
            
        Returns:
            LightCurve object
        """
        points = []
        for i in range(len(times)):
            point = LightCurvePoint(
                time=float(times[i]),
                magnitude=float(magnitudes[i]),
                error=float(errors[i]) if errors is not None and i < len(errors) else None,
                filter=filters[i] if filters is not None and i < len(filters) else None,
            )
            points.append(point)
        
        self._lightcurve = LightCurve(target_name="", points=points)
        return self._lightcurve


# ============================================================================
# Transient Protocol
# ============================================================================

@protocol_plugin(
    "transient",
    spec=ProtocolSpec(
        name="transient",
        version="1.0.0",
        description="Detect and classify transient astronomical sources",
        skills=["transient_detection", "classification", "alert_processing"],
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "ra": {"type": "number"},
                "dec": {"type": "number"},
                "discovery_mjd": {"type": "number"},
                "discovery_mag": {"type": "number"},
                "classification": {"type": "string"},
                "references": {"type": "array"},
            },
            "required": ["name", "ra", "dec", "discovery_mjd"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "transient_type": {"type": "string"},
                "confidence": {"type": "number"},
                "redshift_estimate": {"type": "number"},
                "recommended_followup": {"type": "array"},
            },
        },
    ),
)
class TransientProtocol(TimeDomainProtocol):
    """
    Protocol for transient source detection and classification.
    
    Handles alert data from time-domain surveys like ZTF, ATLAS, and LSST.
    
    Capabilities:
    - Cross-match with known transients
    - Classify transient type (SN Ia, SN CC, AGN, etc.)
    - Estimate redshift from light curve
    - Generate follow-up recommendations
    """
    
    # Transient classification types
    TRANSIENT_TYPES = {
        "SN Ia": "Type Ia Supernova",
        "SN II": "Type II Supernova",
        "SN Ib/c": "Type Ib/c Supernova",
        "SN": "Unknown Type Supernova",
        "AGN": "Active Galactic Nucleus",
        "CV": "Cataclysmic Variable",
        "LBV": "Luminous Blue Variable",
        "He Nova": "Helium Nova",
        "Fe II Nova": "Iron Nova",
        "TDE": "Tidal Disruption Event",
        "Kilonova": "Kilonova",
        "MACHO": "Microlensing Event",
        "ULX": "Ultra-Luminous X-ray Source",
        "FRB": "Fast Radio Burst",
        "GRB": "Gamma-Ray Burst",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._current_transient: Optional[TransientAlert] = None
        self._classification_models: Dict[str, float] = {}
    
    def initialize(self) -> None:
        """Initialize transient detection system."""
        logger.info("Initializing TransientProtocol")
        self._current_transient = None
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute transient detection and classification.
        
        Args:
            input_data: Dictionary with:
                - name: Transient name
                - ra: Right Ascension (degrees)
                - dec: Declination (degrees)
                - discovery_mjd: Discovery time (MJD)
                - discovery_mag: Discovery magnitude
                - classification: Optional classification
                - references: Optional reference observations
                
        Returns:
            ProtocolResult with classification and recommendations
        """
        import time
        start_time = time.time()
        
        try:
            name = input_data.get("name")
            ra = input_data.get("ra")
            dec = input_data.get("dec")
            discovery_mjd = input_data.get("discovery_mjd")
            discovery_mag = input_data.get("discovery_mag")
            classification = input_data.get("classification")
            references = input_data.get("references", [])
            
            if not all([name, ra is not None, dec is not None, discovery_mjd is not None]):
                return ProtocolResult(
                    success=False,
                    error="Missing required fields: name, ra, dec, discovery_mjd",
                )
            
            # Create transient alert object
            transient = TransientAlert(
                name=name,
                ra=float(ra),
                dec=float(dec),
                discovery_time=float(discovery_mjd),
                discovery_mag=float(discovery_mag) if discovery_mag is not None else None,
                classification=classification,
            )
            
            self._current_transient = transient
            
            # Classify if not provided
            if not classification:
                classification, confidence = self._classify_transient(transient, references)
            else:
                confidence = 0.9  # Trust provided classification
            
            # Estimate redshift from magnitude if available
            redshift_estimate = self._estimate_redshift(transient)
            
            # Generate follow-up recommendations
            recommendations = self._generate_followup(transient, classification)
            
            result_data = {
                "name": transient.name,
                "ra": transient.ra,
                "dec": transient.dec,
                "discovery_mjd": transient.discovery_time,
                "discovery_mag": transient.discovery_mag,
                "transient_type": classification,
                "confidence": confidence,
                "redshift_estimate": redshift_estimate,
                "recommended_followup": recommendations,
            }
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "confidence": confidence,
                    "has_classification": classification is not None,
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"Transient detection error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _classify_transient(
        self,
        transient: TransientAlert,
        references: List[Dict],
    ) -> Tuple[Optional[str], float]:
        """
        Classify transient type.
        
        Args:
            transient: Transient alert data
            references: Reference observations
            
        Returns:
            Tuple of (classification, confidence)
        """
        # Simple classification based on available data
        mag = transient.discovery_mag
        
        if mag is not None:
            if mag < 17:
                # Bright transient could be SNe or AGN flare
                if transient.host:
                    return "SN Ia", 0.6
                return "AGN", 0.5
            elif mag < 20:
                # Medium brightness - most SNe, some AGN
                return "SN", 0.5
            else:
                # Faint - could be any transient type
                return "Unknown", 0.3
        
        return "Unknown", 0.2
    
    def _estimate_redshift(self, transient: TransientAlert) -> Optional[float]:
        """Estimate redshift from apparent magnitude."""
        if transient.discovery_mag is None:
            return None
        
        # Very rough estimate assuming typical supernova absolute mag -19
        app_mag = transient.discovery_mag
        abs_mag = -19
        distance_modulus = app_mag - abs_mag
        
        # Distance modulus = 5 * log10(d/10pc), so d = 10 * 10^(dm/5)
        distance_pc = 10 * (10 ** (distance_modulus / 5))
        
        # Very rough redshift estimate (valid for z << 1)
        # For more accurate, would need cosmology calculator
        redshift = distance_pc / 3e9  # Very rough linear approximation
        
        return min(redshift, 0.5)  # Cap at reasonable value
    
    def _generate_followup(
        self,
        transient: TransientAlert,
        classification: Optional[str],
    ) -> List[str]:
        """Generate follow-up recommendations."""
        recommendations = []
        
        if classification in ["SN Ia", "SN II", "SN Ib/c", "SN"]:
            recommendations.append("Spectroscopic observation for redshift confirmation")
            recommendations.append("Multi-band imaging for light curve")
            recommendations.append("Search for host galaxy")
        
        if classification == "AGN":
            recommendations.append("Search for historical variability")
            recommendations.append("Spectroscopic observation for redshift")
            recommendations.append("Radio/X-ray follow-up")
        
        if classification == "TDE":
            recommendations.append("UV/optical spectroscopic observation")
            recommendations.append("X-ray follow-up")
            recommendations.append("Search for nuclear offset")
        
        if classification in ["Kilonova"]:
            recommendations.append("Near-infrared spectroscopy")
            recommendations.append("Search for gravitational wave counterpart")
        
        # Default recommendations
        if not recommendations:
            recommendations.append("Multi-band photometric monitoring")
            recommendations.append("Spectroscopic classification")
        
        return recommendations
    
    def validate(self, data: Any) -> bool:
        """Validate input data."""
        if not isinstance(data, dict):
            return False
        return all(k in data for k in ["name", "ra", "dec", "discovery_mjd"])
    
    def get_metrics(self) -> Dict[str, float]:
        """Get transient detection metrics."""
        base_metrics = super().get_metrics()
        if self._current_transient:
            base_metrics.update({
                "discovery_mag": self._current_transient.discovery_mag or 0.0,
            })
        return base_metrics


# ============================================================================
# Variable Star Protocol
# ============================================================================

@protocol_plugin(
    "variable_star",
    spec=ProtocolSpec(
        name="variable_star",
        version="1.0.0",
        description="Analyze variable star light curves",
        skills=["period_finding", "classification", "light_curve_analysis"],
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "times": {"type": "array", "items": {"type": "number"}},
                "magnitudes": {"type": "array", "items": {"type": "number"}},
                "errors": {"type": "array", "items": {"type": "number"}},
                "filters": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "times", "magnitudes"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "period": {"type": "number"},
                "amplitude": {"type": "number"},
                "mean_mag": {"type": "number"},
                "variable_type": {"type": "string"},
                "goodness_of_fit": {"type": "number"},
            },
        },
    ),
)
class VariableStarProtocol(TimeDomainProtocol):
    """
    Protocol for variable star analysis.
    
    Capabilities:
    - Period finding using Lomb-Scargle algorithm
    - Variable star classification
    - Light curve characterization
    - Amplitude calculation
    """
    
    # Variable star types
    VARIABLE_TYPES = {
        "RR_Lyrae": "RR Lyrae Variable",
        "CEPHEID": "Cepheid Variable",
        "DELTA_SCT": "Delta Scuti Variable",
        "Mira": "Mira Variable",
        "SemiRegular": "Semi-Regular Variable",
        "LongPeriod": "Long-Period Variable",
        "Eclipsing": "Eclipsing Binary",
        "Rotating": "Rotating Variable",
        "Cepheid_Fundamental": "Cepheid (Fundamental)",
        "Cepheid_FirstOvertone": "Cepheid (First Overtone)",
        "W_Uma": "W Ursae Majoris",
        "Beta_Spec": "Beta Cephei Variable",
        "Alpha_Canum": "Alpha Canum Venaticorum",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._analysis: Optional[VariableStarAnalysis] = None
        self._period_range = (0.1, 1000.0)  # Days
    
    def initialize(self) -> None:
        """Initialize variable star analysis."""
        logger.info("Initializing VariableStarProtocol")
        self._analysis = None
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute variable star analysis.
        
        Args:
            input_data: Dictionary with:
                - name: Target name
                - times: Observation times (MJD)
                - magnitudes: Observed magnitudes
                - errors: Optional magnitude errors
                - filters: Optional filter names
                
        Returns:
            ProtocolResult with period and classification
        """
        import time
        start_time = time.time()
        
        try:
            name = input_data.get("name", "Unknown")
            times = input_data.get("times", [])
            magnitudes = input_data.get("magnitudes", [])
            errors = input_data.get("errors")
            filters = input_data.get("filters")
            
            if not times or not magnitudes:
                return ProtocolResult(
                    success=False,
                    error="Missing times or magnitudes",
                )
            
            # Set light curve data
            lc = self.set_lightcurve(times, magnitudes, errors, filters)
            lc.target_name = name
            
            # Calculate basic statistics
            mean_mag = float(np.mean(magnitudes))
            amplitude = self._calculate_amplitude(magnitudes)
            
            # Find period
            period, period_error, gof = self._find_period(times, magnitudes, errors)
            
            # Classify variable type
            var_type = self._classify_variable(period, amplitude, mean_mag)
            
            # Create analysis result
            self._analysis = VariableStarAnalysis(
                target_name=name,
                period=period,
                period_error=period_error,
                amplitude=amplitude,
                mean_mag=mean_mag,
                variable_type=var_type,
                goodness_of_fit=gof,
            )
            
            result_data = {
                "name": name,
                "period_days": period,
                "period_error": period_error,
                "amplitude_mag": amplitude,
                "mean_mag": mean_mag,
                "variable_type": var_type,
                "goodness_of_fit": gof,
                "num_observations": len(times),
            }
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "period": period or 0.0,
                    "amplitude": amplitude,
                    "mean_mag": mean_mag,
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"Variable star analysis error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _calculate_amplitude(self, magnitudes: np.ndarray) -> float:
        """Calculate amplitude of variation."""
        if len(magnitudes) < 2:
            return 0.0
        return float(np.max(magnitudes) - np.min(magnitudes))
    
    def _find_period(
        self,
        times: List[float],
        magnitudes: List[float],
        errors: Optional[List[float]] = None,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Find period using Lomb-Scargle algorithm.
        
        Args:
            times: Observation times
            magnitudes: Magnitudes
            errors: Optional errors
            
        Returns:
            Tuple of (period, period_error, goodness_of_fit)
        """
        try:
            from scipy.signal import lombscargle
            
            t = np.array(times)
            m = np.array(magnitudes)
            
            # Remove mean
            m = m - np.mean(m)
            
            # Frequency grid
            min_freq = 1.0 / self._period_range[1]
            max_freq = 1.0 / self._period_range[0]
            frequencies = np.linspace(min_freq, max_freq, 10000)
            
            # Compute Lomb-Scargle periodogram
            angular_frequencies = 2 * np.pi * frequencies
            
            if errors is not None and len(errors) == len(times):
                weights = 1.0 / np.array(errors)
                weights = weights / np.max(weights)
            else:
                weights = np.ones_like(t)
            
            power = lombscargle(t, m, angular_frequencies, prewhite=0)
            
            # Find best period
            best_idx = np.argmax(power)
            best_freq = frequencies[best_idx]
            best_period = 1.0 / best_freq if best_freq > 0 else None
            
            # Estimate error from peak width
            peak_power = power[best_idx]
            threshold = peak_power / 4
            above_threshold = np.where(power > threshold)[0]
            if len(above_threshold) > 1:
                freq_width = frequencies[above_threshold[-1]] - frequencies[above_threshold[0]]
                period_error = (freq_width / best_freq**2)
            else:
                period_error = best_period * 0.1 if best_period else None
            
            # Goodness of fit (normalized power)
            gof = float(peak_power / np.sum(power)) if np.sum(power) > 0 else 0.0
            
            return best_period, period_error, gof
            
        except ImportError:
            # Fallback without scipy
            return self._simple_period_finding(times, magnitudes)
        except Exception as e:
            logger.warning(f"Period finding error: {e}")
            return None, None, None
    
    def _simple_period_finding(
        self,
        times: List[float],
        magnitudes: List[float],
    ) -> Tuple[Optional[float], None, None]:
        """Simple period finding without scipy."""
        t = np.array(times)
        m = np.array(magnitudes)
        
        # Simple autocorrelation
        dt = np.median(np.diff(t))
        max_lag = min(100, len(t) // 2)
        
        autocorr = []
        for lag in range(1, max_lag):
            corr = np.corrcoef(m[:-lag], m[lag:])[0, 1] if lag < len(m) else 0
            autocorr.append(corr)
        
        if not autocorr:
            return None, None, None
        
        # Find first peak after initial decline
        autocorr = np.array(autocorr)
        peak_idx = np.argmax(autocorr[max_lag//2:]) + max_lag//2
        
        if peak_idx > 0 and peak_idx < len(t):
            period = float(dt * peak_idx)
            if self._period_range[0] < period < self._period_range[1]:
                return period, None, None
        
        return None, None, None
    
    def _classify_variable(
        self,
        period: Optional[float],
        amplitude: float,
        mean_mag: float,
    ) -> str:
        """
        Classify variable star type.
        
        Args:
            period: Period in days
            amplitude: Amplitude in magnitudes
            mean_mag: Mean magnitude
            
        Returns:
            Variable type string
        """
        if period is None:
            return "Unknown"
        
        if period < 1.0:
            # Short period - could be RR Lyrae or Delta Scuti
            if amplitude > 1.0:
                return "RR_Lyrae"
            else:
                return "DELTA_SCT"
        elif period < 10.0:
            # Medium period - Cepheids or W UMa
            if amplitude > 0.1:
                return "CEPHEID"
            else:
                return "W_Uma"
        elif period < 100.0:
            # Longer period
            if amplitude > 2.0:
                return "Mira"
            else:
                return "SemiRegular"
        elif period < 1000.0:
            return "LongPeriod"
        else:
            return "Unknown"
    
    def validate(self, data: Any) -> bool:
        """Validate input data."""
        if not isinstance(data, dict):
            return False
        return "times" in data and "magnitudes" in data
    
    def get_metrics(self) -> Dict[str, float]:
        """Get variable star analysis metrics."""
        base_metrics = super().get_metrics()
        if self._analysis:
            base_metrics.update({
                "period": self._analysis.period or 0.0,
                "amplitude": self._analysis.amplitude or 0.0,
            })
        return base_metrics


# ============================================================================
# Light Curve Protocol
# ============================================================================

@protocol_plugin(
    "lightcurve",
    spec=ProtocolSpec(
        name="lightcurve",
        version="1.0.0",
        description="Analyze astronomical light curves",
        skills=["photometry", "curve_fitting", "time_series"],
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "times": {"type": "array", "items": {"type": "number"}},
                "magnitudes": {"type": "array", "items": {"type": "number"}},
                "errors": {"type": "array", "items": {"type": "number"}},
                "filters": {"type": "array", "items": {"type": "string"}},
                "model": {"type": "string", "enum": ["polynomial", "gaussian", "spline"]},
            },
            "required": ["name", "times", "magnitudes"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "num_points": {"type": "integer"},
                "mean_mag": {"type": "number"},
                "std_mag": {"type": "number"},
                "chi_squared": {"type": "number"},
            },
        },
    ),
)
class LightCurveProtocol(TimeDomainProtocol):
    """
    Protocol for light curve analysis and fitting.
    
    Capabilities:
    - Basic statistics calculation
    - Trend detection
    - Curve fitting (polynomial, gaussian, spline)
    - Outlier detection
    - Multi-band light curve handling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._current_lc: Optional[LightCurve] = None
        self._fitted_params: Dict[str, Any] = {}
    
    def initialize(self) -> None:
        """Initialize light curve analysis."""
        logger.info("Initializing LightCurveProtocol")
        self._current_lc = None
        self._fitted_params = {}
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute light curve analysis.
        
        Args:
            input_data: Dictionary with:
                - name: Target name
                - times: Observation times (MJD)
                - magnitudes: Observed magnitudes
                - errors: Optional magnitude errors
                - filters: Optional filter names
                - model: Optional fitting model ("polynomial", "gaussian", "spline")
                
        Returns:
            ProtocolResult with analysis results
        """
        import time
        start_time = time.time()
        
        try:
            name = input_data.get("name", "Unknown")
            times = input_data.get("times", [])
            magnitudes = input_data.get("magnitudes", [])
            errors = input_data.get("errors")
            filters = input_data.get("filters")
            model = input_data.get("model", "polynomial")
            
            if not times or not magnitudes:
                return ProtocolResult(
                    success=False,
                    error="Missing times or magnitudes",
                )
            
            # Set light curve data
            lc = self.set_lightcurve(times, magnitudes, errors, filters)
            lc.target_name = name
            self._current_lc = lc
            
            # Calculate basic statistics
            stats = self._calculate_statistics(lc)
            
            # Fit model if requested
            fit_results = {}
            if model:
                fit_results = self._fit_lightcurve(times, magnitudes, errors, model)
            
            # Detect outliers
            outliers = self._detect_outliers(lc)
            
            # Detect trends
            trend = self._detect_trend(times, magnitudes)
            
            result_data = {
                "name": name,
                "num_points": lc.num_points,
                "mean_mag": stats["mean"],
                "std_mag": stats["std"],
                "min_mag": stats["min"],
                "max_mag": stats["max"],
                "time_span_days": float(stats["time_span"]),
                "outliers": outliers,
                "trend": trend,
                **fit_results,
            }
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "num_points": lc.num_points,
                    "mean_mag": stats["mean"],
                    "std_mag": stats["std"],
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"Light curve analysis error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _calculate_statistics(self, lc: LightCurve) -> Dict[str, float]:
        """Calculate light curve statistics."""
        mags = lc.magnitudes
        times = lc.times
        
        return {
            "mean": float(np.mean(mags)),
            "std": float(np.std(mags)),
            "min": float(np.min(mags)),
            "max": float(np.max(mags)),
            "median": float(np.median(mags)),
            "time_span": float(np.max(times) - np.min(times)) if len(times) > 1 else 0.0,
        }
    
    def _fit_lightcurve(
        self,
        times: List[float],
        magnitudes: List[float],
        errors: Optional[List[float]],
        model: str,
    ) -> Dict[str, Any]:
        """
        Fit a model to the light curve.
        
        Args:
            times: Observation times
            magnitudes: Magnitudes
            errors: Optional errors
            model: Model type
            
        Returns:
            Dictionary with fit parameters
        """
        t = np.array(times)
        m = np.array(magnitudes)
        
        # Remove mean for fitting
        m_mean = np.mean(m)
        m_centered = m - m_mean
        
        try:
            if model == "polynomial":
                # Fit polynomial
                degree = min(3, len(t) - 1)
                coeffs = np.polyfit(t, m_centered, degree)
                poly = np.poly1d(coeffs)
                
                # Calculate residuals
                residuals = m - (poly(t) + m_mean)
                chi_sq = np.sum((residuals / (errors if errors else 1.0))**2)
                
                self._fitted_params = {
                    "model": "polynomial",
                    "coefficients": coeffs.tolist(),
                    "degree": degree,
                    "chi_squared": float(chi_sq),
                    "dof": len(t) - degree - 1,
                }
                
            elif model == "gaussian":
                # Fit gaussian
                from scipy.optimize import curve_fit
                
                def gaussian(x, amp, mean, sigma):
                    return amp * np.exp(-(x - mean)**2 / (2 * sigma**2))
                
                # Initial guess
                amp_guess = np.max(m_centered) - np.min(m_centered)
                mean_guess = np.mean(t)
                sigma_guess = np.std(t)
                
                try:
                    popt, pcov = curve_fit(
                        gaussian, t, m_centered,
                        p0=[amp_guess, mean_guess, sigma_guess],
                        maxfev=5000
                    )
                    
                    residuals = m - (gaussian(t, *popt) + m_mean)
                    chi_sq = np.sum((residuals / (errors if errors else 1.0))**2)
                    
                    self._fitted_params = {
                        "model": "gaussian",
                        "amplitude": float(popt[0]),
                        "mean": float(popt[1]),
                        "sigma": float(popt[2]),
                        "chi_squared": float(chi_sq),
                    }
                except Exception:
                    self._fitted_params = {"model": "gaussian", "error": "Fit failed"}
            
            elif model == "spline":
                from scipy.interpolate import UnivariateSpline
                
                try:
                    spline = UnivariateSpline(t, m_centered, s=len(t))
                    
                    residuals = m - (spline(t) + m_mean)
                    chi_sq = np.sum((residuals / (errors if errors else 1.0))**2)
                    
                    self._fitted_params = {
                        "model": "spline",
                        "chi_squared": float(chi_sq),
                        "dof": len(t) - spline.get_residual() - 1,
                    }
                except Exception:
                    self._fitted_params = {"model": "spline", "error": "Fit failed"}
            
            else:
                self._fitted_params = {"model": model, "error": "Unknown model"}
                
        except ImportError:
            self._fitted_params = {"error": "scipy not available"}
        except Exception as e:
            self._fitted_params = {"error": str(e)}
        
        return self._fitted_params
    
    def _detect_outliers(self, lc: LightCurve) -> List[int]:
        """
        Detect outliers using sigma clipping.
        
        Returns:
            List of outlier indices
        """
        mags = lc.magnitudes
        
        if len(mags) < 4:
            return []
        
        median = np.median(mags)
        mad = np.median(np.abs(mags - median))
        
        if mad == 0:
            return []
        
        # Modified z-score
        threshold = 3.5
        z_scores = 0.6745 * (mags - median) / mad
        
        outliers = np.where(np.abs(z_scores) > threshold)[0].tolist()
        
        return outliers
    
    def _detect_trend(
        self,
        times: List[float],
        magnitudes: List[float],
    ) -> str:
        """
        Detect trend in light curve.
        
        Returns:
            Trend type: "increasing", "decreasing", "constant", "variable"
        """
        if len(times) < 4:
            return "unknown"
        
        t = np.array(times)
        m = np.array(magnitudes)
        
        # Linear regression
        try:
            coeffs = np.polyfit(t, m, 1)
            slope = coeffs[0]
            
            # Calculate correlation
            corr = np.corrcoef(t, m)[0, 1]
            
            # Threshold for trend detection
            slope_threshold = 0.001  # mag/day
            
            if abs(slope) < slope_threshold:
                return "constant"
            elif slope > 0:
                return "increasing"
            else:
                return "decreasing"
                
        except Exception:
            return "unknown"
    
    def validate(self, data: Any) -> bool:
        """Validate input data."""
        if not isinstance(data, dict):
            return False
        return "times" in data and "magnitudes" in data
    
    def get_metrics(self) -> Dict[str, float]:
        """Get light curve analysis metrics."""
        base_metrics = super().get_metrics()
        if self._current_lc:
            base_metrics.update({
                "num_points": self._current_lc.num_points,
                "mean_mag": float(np.mean(self._current_lc.magnitudes)),
            })
        return base_metrics


# ============================================================================
# Registry Registration
# ============================================================================

# Register all time-domain protocols
ProtocolRegistry.register("transient", TransientProtocol)
ProtocolRegistry.register("variable_star", VariableStarProtocol)
ProtocolRegistry.register("lightcurve", LightCurveProtocol)
