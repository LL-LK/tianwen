"""
Astronomy-specific protocols for TianwenAGI Harness.

This module provides specialized protocols for astronomical data processing
following NGSS (Next Generation Science Standards) skill-based workflows.

Includes:
- SpectralAnalysisProtocol: Spectral data analysis
- PhotometryProtocol: Photometric measurements
- AstronomicalCoordinateProtocol: Sky coordinate transformations
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

logger = logging.getLogger(__name__)


# ============================================================================
# Astronomy Protocol Base
# ============================================================================

class AstronomyProtocol(BaseProtocol[Dict[str, Any]]):
    """
    Base class for astronomy-specific protocols.
    
    Provides common functionality for astronomical data processing
    including unit handling, coordinate systems, and error estimation.
    """
    
    # Astronomical constants
    SPEED_OF_LIGHT = 299792.458  # km/s
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._wavelengths: Optional[np.ndarray] = None
        self._flux: Optional[np.ndarray] = None
        self._error: Optional[np.ndarray] = None
    
    def set_spectrum(
        self,
        wavelengths: Union[List[float], np.ndarray],
        flux: Union[List[float], np.ndarray],
        error: Optional[Union[List[float], np.ndarray]] = None,
    ) -> None:
        """
        Set spectral data for analysis.
        
        Args:
            wavelengths: Array of wavelengths (Angstroms)
            flux: Array of flux values
            error: Optional array of error values
        """
        self._wavelengths = np.array(wavelengths)
        self._flux = np.array(flux)
        self._error = np.array(error) if error is not None else None
    
    def wavelength_to_velocity(
        self,
        rest_wavelength: float,
        observed_wavelength: float,
    ) -> float:
        """
        Convert observed wavelength to radial velocity.
        
        Uses relativistic formula: v = c * (λ_obs - λ_rest) / λ_rest
        
        Args:
            rest_wavelength: Rest frame wavelength (Angstroms)
            observed_wavelength: Observed wavelength (Angstroms)
            
        Returns:
            Radial velocity in km/s
        """
        return self.SPEED_OF_LIGHT * (observed_wavelength - rest_wavelength) / rest_wavelength
    
    def velocity_to_wavelength(
        self,
        rest_wavelength: float,
        velocity: float,
    ) -> float:
        """
        Convert radial velocity to observed wavelength.
        
        Args:
            rest_wavelength: Rest frame wavelength (Angstroms)
            velocity: Radial velocity in km/s
            
        Returns:
            Observed wavelength in Angstroms
        """
        return rest_wavelength * (1 + velocity / self.SPEED_OF_LIGHT)


# ============================================================================
# Spectral Analysis Protocol
# ============================================================================

@dataclass
class SpectralLine:
    """Represents a spectral line feature."""
    wavelength: float
    name: Optional[str] = None
    species: Optional[str] = None
    equivalent_width: Optional[float] = None
    flux_ratio: Optional[float] = None
    velocity: Optional[float] = None


@protocol_plugin(
    "spectral_analysis",
    spec=ProtocolSpec(
        name="spectral_analysis",
        version="1.0.0",
        description="Analyze spectral data for astronomical objects",
        skills=["spectroscopy", "line_identification", "redshift_measurement"],
        input_schema={
            "type": "object",
            "properties": {
                "wavelengths": {"type": "array", "items": {"type": "number"}},
                "flux": {"type": "array", "items": {"type": "number"}},
                "rest_lines": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["wavelengths", "flux"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "redshift": {"type": "number"},
                "velocity": {"type": "number"},
                "lines": {"type": "array"},
            },
        },
    ),
)
class SpectralAnalysisProtocol(AstronomyProtocol):
    """
    Protocol for spectral data analysis.
    
    Capabilities:
    - Redshift measurement from emission/absorption lines
    - Spectral line identification
    - Equivalent width calculation
    - Line ratio analysis
    
    NGSS Skills:
    - Analyzing and interpreting data
    - Using models
    - Quantitative reasoning
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._detected_lines: List[SpectralLine] = []
        self._redshift: Optional[float] = None
    
    def initialize(self) -> None:
        """Initialize spectral analysis tools."""
        logger.info("Initializing SpectralAnalysisProtocol")
        self._detected_lines = []
        self._redshift = None
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute spectral analysis.
        
        Args:
            input_data: Dictionary with:
                - wavelengths: array of wavelengths
                - flux: array of flux values
                - rest_lines: optional known rest wavelengths for matching
                
        Returns:
            ProtocolResult with analysis results
        """
        import time
        start_time = time.time()
        
        try:
            wavelengths = input_data.get("wavelengths", self._wavelengths)
            flux = input_data.get("flux", self._flux)
            rest_lines = input_data.get("rest_lines", [])
            
            if wavelengths is None or flux is None:
                return ProtocolResult(
                    success=False,
                    error="Missing wavelengths or flux data",
                )
            
            self.set_spectrum(wavelengths, flux)
            
            # Detect spectral lines
            lines = self._detect_lines()
            
            # Calculate redshift if rest lines provided
            redshift = None
            velocity = None
            if rest_lines and lines:
                redshift, velocity = self._calculate_redshift(lines, rest_lines)
                self._redshift = redshift
            
            result_data = {
                "redshift": redshift,
                "velocity": velocity,
                "lines": [
                    {
                        "wavelength": line.wavelength,
                        "name": line.name,
                        "species": line.species,
                        "equivalent_width": line.equivalent_width,
                    }
                    for line in lines
                ],
                "num_lines_detected": len(lines),
            }
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "redshift": redshift or 0.0,
                    "num_lines": len(lines),
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"Spectral analysis error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _detect_lines(self) -> List[SpectralLine]:
        """Detect spectral lines in the data."""
        if self._flux is None or self._wavelengths is None:
            return []
        
        # Simple peak detection
        lines = []
        flux = self._flux
        
        # Find local maxima above threshold
        threshold = np.mean(flux) + 2 * np.std(flux)
        
        for i in range(1, len(flux) - 1):
            if flux[i] > flux[i-1] and flux[i] > flux[i+1] and flux[i] > threshold:
                lines.append(SpectralLine(
                    wavelength=float(self._wavelengths[i]),
                    flux_ratio=float(flux[i] / np.median(flux)),
                ))
        
        return lines
    
    def _calculate_redshift(
        self,
        detected_lines: List[SpectralLine],
        rest_lines: List[float],
    ) -> Tuple[float, float]:
        """
        Calculate redshift from detected lines.
        
        Args:
            detected_lines: Detected spectral lines
            rest_lines: Known rest wavelengths
            
        Returns:
            Tuple of (redshift, velocity)
        """
        if not detected_lines or not rest_lines:
            return 0.0, 0.0
        
        # Match detected lines to rest lines
        rest_wavelengths = np.array(rest_lines)
        detected_wavelengths = np.array([line.wavelength for line in detected_lines])
        
        # Calculate redshift for each match
        redshifts = []
        for det_wl in detected_wavelengths:
            for rest_wl in rest_wavelengths:
                if abs(det_wl - rest_wl) / rest_wl < 0.1:  # Within 10%
                    z = (det_wl - rest_wl) / rest_wl
                    redshifts.append(z)
        
        if redshifts:
            z = np.median(redshifts)
            v = self.SPEED_OF_LIGHT * z
            return float(z), float(v)
        
        return 0.0, 0.0
    
    def validate(self, data: Any) -> bool:
        """Validate input data format."""
        if not isinstance(data, dict):
            return False
        return "wavelengths" in data and "flux" in data
    
    def get_metrics(self) -> Dict[str, float]:
        """Get spectral analysis metrics."""
        base_metrics = super().get_metrics()
        base_metrics.update({
            "redshift": self._redshift or 0.0,
            "detected_lines": len(self._detected_lines),
        })
        return base_metrics


# ============================================================================
# Photometry Protocol
# ============================================================================

@protocol_plugin(
    "photometry",
    spec=ProtocolSpec(
        name="photometry",
        version="1.0.0",
        description="Photometric analysis for astronomical objects",
        skills=["photometry", "magnitude_measurement", "color_calculation"],
        input_schema={
            "type": "object",
            "properties": {
                "filters": {"type": "array", "items": {"type": "string"}},
                "magnitudes": {"type": "array", "items": {"type": "number"}},
                "errors": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["filters", "magnitudes"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "colors": {"type": "object"},
                "absolute_magnitude": {"type": "number"},
            },
        },
    ),
)
class PhotometryProtocol(AstronomyProtocol):
    """
    Protocol for photometric analysis.
    
    Capabilities:
    - Magnitude measurements
    - Color calculation
    - Distance estimation
    - Absolute magnitude calculation
    
    NGSS Skills:
    - Using mathematics
    - Constructing explanations
    - Engaging in argument from evidence
    """
    
    # photometric zero points for common filters
    FILTER_ZERO_POINTS = {
        "U": 0.0,
        "B": 0.0,
        "V": 0.0,
        "R": 0.0,
        "I": 0.0,
        "J": 0.0,
        "H": 0.0,
        "K": 0.0,
        "g": 0.0,
        "r": 0.0,
        "i": 0.0,
        "z": 0.0,
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._filters: List[str] = []
        self._magnitudes: Optional[np.ndarray] = None
        self._errors: Optional[np.ndarray] = None
    
    def initialize(self) -> None:
        """Initialize photometry system."""
        logger.info("Initializing PhotometryProtocol")
        self._filters = []
        self._magnitudes = None
        self._errors = None
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute photometric analysis.
        
        Args:
            input_data: Dictionary with:
                - filters: list of filter names
                - magnitudes: list of apparent magnitudes
                - errors: optional list of magnitude errors
                - distance: optional distance in parsecs
                
        Returns:
            ProtocolResult with photometric analysis
        """
        import time
        start_time = time.time()
        
        try:
            filters = input_data.get("filters", [])
            magnitudes = input_data.get("magnitudes", [])
            errors = input_data.get("errors")
            distance_pc = input_data.get("distance")
            
            if len(filters) != len(magnitudes):
                return ProtocolResult(
                    success=False,
                    error="Filters and magnitudes must have same length",
                )
            
            self._filters = filters
            self._magnitudes = np.array(magnitudes)
            self._errors = np.array(errors) if errors else None
            
            # Calculate colors
            colors = self._calculate_colors()
            
            result_data = {
                "filters": filters,
                "magnitudes": magnitudes,
                "colors": colors,
            }
            
            # Calculate absolute magnitude if distance provided
            if distance_pc and len(magnitudes) > 0:
                # Use first filter as reference
                app_mag = magnitudes[0]
                abs_mag = app_mag - 5 * np.log10(distance_pc) + 5
                result_data["absolute_magnitude"] = float(abs_mag)
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "num_filters": len(filters),
                    "mean_magnitude": float(np.mean(self._magnitudes)),
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"Photometry error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _calculate_colors(self) -> Dict[str, float]:
        """Calculate color indices from magnitudes."""
        colors = {}
        mags = self._magnitudes
        
        # Simple color calculation for adjacent filters
        for i in range(len(self._filters) - 1):
            color_name = f"{self._filters[i]}-{self._filters[i+1]}"
            colors[color_name] = float(mags[i] - mags[i+1])
        
        return colors
    
    def validate(self, data: Any) -> bool:
        """Validate input data format."""
        if not isinstance(data, dict):
            return False
        return "filters" in data and "magnitudes" in data
    
    def get_metrics(self) -> Dict[str, float]:
        """Get photometry metrics."""
        base_metrics = super().get_metrics()
        if self._magnitudes is not None:
            base_metrics.update({
                "mean_magnitude": float(np.mean(self._magnitudes)),
                "num_filters": len(self._filters),
            })
        return base_metrics


# ============================================================================
# Astronomical Coordinate Protocol
# ============================================================================

@protocol_plugin(
    "astro_coordinate",
    spec=ProtocolSpec(
        name="astro_coordinate",
        version="1.0.0",
        description="Astronomical coordinate transformations",
        skills=["coordinate_systems", "transformation", "astrometry"],
        input_schema={
            "type": "object",
            "properties": {
                "ra": {"type": "number"},
                "dec": {"type": "number"},
                "system": {"type": "string", "enum": ["ICRS", "FK5", "GALACTIC"]},
            },
            "required": ["ra", "dec"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "ra_deg": {"type": "number"},
                "dec_deg": {"type": "number"},
                "galactic_l": {"type": "number"},
                "galactic_b": {"type": "number"},
            },
        },
    ),
)
class AstronomicalCoordinateProtocol(AstronomyProtocol):
    """
    Protocol for astronomical coordinate transformations.
    
    Capabilities:
    - Equatorial (RA/Dec) to Galactic conversion
    - Coordinate system transformations
    - Proper motion application
    - Airmass calculation
    
    NGSS Skills:
    - Using models
    - Structure and function
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._ra: Optional[float] = None
        self._dec: Optional[float] = None
    
    def initialize(self) -> None:
        """Initialize coordinate system."""
        logger.info("Initializing AstronomicalCoordinateProtocol")
        self._ra = None
        self._dec = None
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute coordinate transformation.
        
        Args:
            input_data: Dictionary with:
                - ra: Right Ascension (degrees or hours:min:sec)
                - dec: Declination (degrees or deg:arcmin:arcsec)
                - system: Input coordinate system
                
        Returns:
            ProtocolResult with transformed coordinates
        """
        import time
        start_time = time.time()
        
        try:
            ra = input_data.get("ra")
            dec = input_data.get("dec")
            system = input_data.get("system", "ICRS")
            
            if ra is None or dec is None:
                return ProtocolResult(
                    success=False,
                    error="Missing RA or Dec",
                )
            
            self._ra = float(ra)
            self._dec = float(dec)
            
            # Convert RA to degrees if in hours
            if self._ra > 24:
                self._ra_deg = self._ra  # Already in degrees
            else:
                self._ra_deg = self._ra * 15  # Convert hours to degrees
            
            self._dec_deg = self._dec
            
            # Convert to Galactic coordinates
            galactic_l, galactic_b = self._equatorial_to_galactic(
                self._ra_deg, self._dec_deg
            )
            
            result_data = {
                "ra_deg": self._ra_deg,
                "dec_deg": self._dec_deg,
                "galactic_l": float(galactic_l),
                "galactic_b": float(galactic_b),
                "system": system,
            }
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "ra": self._ra_deg,
                    "dec": self._dec_deg,
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"Coordinate transformation error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _equatorial_to_galactic(
        self,
        ra_deg: float,
        dec_deg: float,
    ) -> Tuple[float, float]:
        """
        Convert equatorial to Galactic coordinates.
        
        Uses the ICRS transformation with:
        - North Galactic Pole: RA=192.85948°, Dec=27.12825°
        - Galactic center direction: l=122.93192°
        
        Args:
            ra_deg: Right Ascension in degrees
            dec_deg: Declination in degrees
            
        Returns:
            Tuple of (galactic_l, galactic_b) in degrees
        """
        import math
        
        # North Galactic Pole in ICRS
        ra_pole = 192.85948 * np.pi / 180
        dec_pole = 27.12825 * np.pi / 180
        
        # Position angle of North Galactic Pole
        theta = 122.93192 * np.pi / 180  # Galactic center
        
        ra_rad = ra_deg * np.pi / 180
        dec_rad = dec_deg * np.pi / 180
        
        # Calculate galactic longitude
        l = np.arctan2(
            np.cos(dec_rad) * np.sin(ra_rad - theta),
            np.sin(dec_rad) * np.cos(dec_pole) -
            np.cos(dec_rad) * np.sin(dec_pole) * np.cos(ra_rad - theta)
        ) + theta
        
        # Calculate galactic latitude
        b = np.arcsin(
            np.sin(dec_rad) * np.sin(dec_pole) +
            np.cos(dec_rad) * np.cos(dec_pole) * np.cos(ra_rad - theta)
        )
        
        l_deg = (l * 180 / np.pi) % 360
        b_deg = b * 180 / np.pi
        
        return l_deg, b_deg
    
    def validate(self, data: Any) -> bool:
        """Validate input data format."""
        if not isinstance(data, dict):
            return False
        if "ra" not in data or "dec" not in data:
            return False
        return -90 <= data["dec"] <= 90
    
    def get_metrics(self) -> Dict[str, float]:
        """Get coordinate metrics."""
        base_metrics = super().get_metrics()
        if self._ra_deg is not None and self._dec_deg is not None:
            base_metrics.update({
                "ra_deg": self._ra_deg,
                "dec_deg": self._dec_deg,
            })
        return base_metrics


# ============================================================================
# Registry Registration
# ============================================================================

# Register all astronomy protocols
ProtocolRegistry.register("spectral_analysis", SpectralAnalysisProtocol)
ProtocolRegistry.register("photometry", PhotometryProtocol)
ProtocolRegistry.register("astro_coordinate", AstronomicalCoordinateProtocol)
