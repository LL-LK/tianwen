"""
FITS Data Protocol - FITS file handling for TianwenAGI Harness

This module provides protocols for handling FITS (Flexible Image Transport System)
files commonly used in astronomy for storing spectral, image, and catalog data.

Includes:
- FITSSpectrumProtocol: Astronomical spectrum FITS file handling
- FITSImageProtocol: Astronomical image FITS file handling
- FITSCatalogProtocol: Star catalog data handling

FITS Standard Reference: https://fits.gsfc.nasa.gov/
"""

from __future__ import annotations

import logging
import os
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

# FITS header keywords mapping
FITS_KEYWORDS = {
    "SIMPLE": "standard_conform",
    "BITPIX": "data_type",
    "NAXIS": "num_axes",
    "NAXIS1": "axis1_length",
    "NAXIS2": "axis2_length",
    "OBJECT": "object_name",
    "TELESCOP": "telescope",
    "INSTRUME": "instrument",
    "DATE-OBS": "observation_date",
    "EXPTIME": "exposure_time",
    "FILTER": "filter_name",
    "RA": "right_ascension",
    "DEC": "declination",
    "CTYPE1": "axis1_coord_type",
    "CTYPE2": "axis2_coord_type",
    "CRPIX1": "ref_pixel_axis1",
    "CRPIX2": "ref_pixel_axis2",
    "CRVAL1": "ref_coord_axis1",
    "CRVAL2": "ref_coord_axis2",
    "CDELT1": "pixel_scale_axis1",
    "CDELT2": "pixel_scale_axis2",
    "CD1_1": "rotation_matrix_11",
    "CD1_2": "rotation_matrix_12",
    "CD2_1": "rotation_matrix_21",
    "CD2_2": "rotation_matrix_22",
    "BSCALE": "scale_factor",
    "BZERO": "offset_factor",
    "COMMENT": "comment",
    "AUTHOR": "author",
    "REFERENC": "reference",
}


@dataclass
class FITSHeader:
    """Represents a parsed FITS header."""
    keywords: Dict[str, Any] = field(default_factory=dict)
    object_name: Optional[str] = None
    telescope: Optional[str] = None
    instrument: Optional[str] = None
    observation_date: Optional[str] = None
    exposure_time: Optional[float] = None
    filter_name: Optional[str] = None
    right_ascension: Optional[str] = None
    declination: Optional[str] = None
    is_valid: bool = True
    issues: List[str] = field(default_factory=list)

    def get_wcs(self) -> Optional[Dict[str, float]]:
        """Extract WCS information from header."""
        if "CRPIX1" not in self.keywords:
            return None
        
        wcs = {}
        for key in ["CRPIX1", "CRPIX2", "CRVAL1", "CRVAL2", "CDELT1", "CDELT2"]:
            if key in self.keywords:
                wcs[key.lower()] = float(self.keywords[key])
        return wcs if wcs else None


@dataclass
class SpectrumData:
    """Represents spectral data extracted from FITS."""
    wavelengths: np.ndarray
    flux: np.ndarray
    error: Optional[np.ndarray] = None
    header: Optional[FITSHeader] = None
    redshift: Optional[float] = None
    instrument: Optional[str] = None


@dataclass
class ImageData:
    """Represents image data extracted from FITS."""
    data: np.ndarray
    header: FITSHeader
    wcs: Optional[Dict[str, Any]] = None
    shape: Tuple[int, ...] = field(default_factory=lambda: (0, 0))


@dataclass
class CatalogEntry:
    """Represents an entry from an astronomical catalog."""
    ra: float
    dec: float
    magnitude: Optional[float] = None
    name: Optional[str] = None
    catalog_name: Optional[str] = None
    spectral_type: Optional[str] = None
    parallax: Optional[float] = None
    proper_motion_ra: Optional[float] = None
    proper_motion_dec: Optional[float] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Base FITS Protocol
# ============================================================================

class FITSProtocol(AstronomyProtocol):
    """
    Base class for FITS file handling protocols.
    
    Provides common functionality for:
    - FITS file reading using astropy.io.fits
    - Header parsing and validation
    - Error handling for malformed files
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._current_file: Optional[str] = None
        self._header: Optional[FITSHeader] = None
        self._has_astropy = self._check_astropy()
    
    def _check_astropy(self) -> bool:
        """Check if astropy is available."""
        try:
            from astropy.io import fits
            return True
        except ImportError:
            logger.warning("astropy not available, FITS support will be limited")
            return False
    
    def _parse_fits_header(self, header_cards: List[Tuple[str, Any, str]]) -> FITSHeader:
        """
        Parse FITS header cards into FITSHeader object.
        
        Args:
            header_cards: List of (keyword, value, comment) tuples from astropy
            
        Returns:
            FITSHeader object
        """
        header = FITSHeader()
        
        for keyword, value, comment in header_cards:
            header.keywords[keyword] = value
            
            if keyword == "OBJECT":
                header.object_name = str(value).strip()
            elif keyword == "TELESCOP":
                header.telescope = str(value).strip()
            elif keyword == "INSTRUME":
                header.instrument = str(value).strip()
            elif keyword == "DATE-OBS":
                header.observation_date = str(value).strip()
            elif keyword == "EXPTIME":
                try:
                    header.exposure_time = float(value)
                except (ValueError, TypeError):
                    pass
            elif keyword == "FILTER":
                header.filter_name = str(value).strip()
            elif keyword == "RA":
                header.right_ascension = str(value).strip()
            elif keyword == "DEC":
                header.declination = str(value).strip()
        
        # Validate required FITS keywords
        if "SIMPLE" not in header.keywords:
            header.issues.append("Missing SIMPLE keyword")
            header.is_valid = False
        elif not header.keywords["SIMPLE"]:
            header.issues.append("SIMPLE not true - not standard FITS")
            header.is_valid = False
        
        return header


# ============================================================================
# FITS Spectrum Protocol
# ============================================================================

@protocol_plugin(
    "fits_spectrum",
    spec=ProtocolSpec(
        name="fits_spectrum",
        version="1.0.0",
        description="Handle astronomical spectrum FITS files",
        skills=["spectroscopy", "data_parsing", "wavelength_calibration"],
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "wavelength_unit": {"type": "string", "default": "Angstrom"},
                "flux_unit": {"type": "string", "default": "erg/s/cm^2/Angstrom"},
            },
            "required": ["file_path"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "wavelengths": {"type": "array"},
                "flux": {"type": "array"},
                "header": {"type": "object"},
                "num_points": {"type": "integer"},
            },
        },
    ),
)
class FITSSpectrumProtocol(FITSProtocol):
    """
    Protocol for handling astronomical spectrum FITS files.
    
    Supports 1D spectra stored in various FITS formats:
    - Simple 1D arrays (NAXIS=1)
    - 2D spectra with wavelength as first dimension (NAXIS=2, with NAXIS1 being wavelength)
    - Multi-spec format (SPECRESP Keyword present)
    
    Capabilities:
    - Read spectrum from FITS file
    - Extract header information
    - Apply wavelength calibration
    - Calculate redshift from known lines
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._spectrum: Optional[SpectrumData] = None
        self._wavelength_zero_point: float = 0.0
        self._wavelength_scale: float = 1.0
    
    def initialize(self) -> None:
        """Initialize spectrum protocol."""
        logger.info("Initializing FITSSpectrumProtocol")
        self._spectrum = None
        self._current_file = None
        self._header = None
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute spectrum extraction from FITS file.
        
        Args:
            input_data: Dictionary with:
                - file_path: Path to FITS file
                - wavelength_unit: Unit for wavelength (default: Angstrom)
                - flux_unit: Unit for flux values
                
        Returns:
            ProtocolResult with spectrum data
        """
        import time
        start_time = time.time()
        
        try:
            file_path = input_data.get("file_path")
            if not file_path:
                return ProtocolResult(
                    success=False,
                    error="Missing file_path",
                )
            
            # Read FITS file
            spectrum = self._read_spectrum(file_path, input_data)
            if spectrum is None:
                return ProtocolResult(
                    success=False,
                    error="Failed to read spectrum from FITS file",
                )
            
            self._spectrum = spectrum
            self._current_file = file_path
            
            result_data = {
                "file_path": file_path,
                "object_name": spectrum.header.object_name if spectrum.header else None,
                "wavelengths": spectrum.wavelengths.tolist(),
                "flux": spectrum.flux.tolist(),
                "num_points": len(spectrum.wavelengths),
                "instrument": spectrum.instrument,
            }
            
            if spectrum.error is not None:
                result_data["error"] = spectrum.error.tolist()
            
            if spectrum.header:
                result_data["header_info"] = {
                    "telescope": spectrum.header.telescope,
                    "instrument": spectrum.header.instrument,
                    "filter": spectrum.header.filter_name,
                    "exposure_time": spectrum.header.exposure_time,
                }
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "num_points": len(spectrum.wavelengths),
                    "mean_flux": float(np.mean(spectrum.flux)),
                    "flux_std": float(np.std(spectrum.flux)),
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"FITS spectrum error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _read_spectrum(self, file_path: str, input_data: Dict[str, Any]) -> Optional[SpectrumData]:
        """Read spectrum data from FITS file."""
        if not self._has_astropy:
            return self._read_spectrum_fallback(file_path)
        
        from astropy.io import fits
        
        try:
            with fits.open(file_path) as hdul:
                # Get primary header
                header = hdul[0].header
                header_cards = [(k, header[k], header.comments[k]) for k in header.keys() if k]
                fits_header = self._parse_fits_header(header_cards)
                
                # Determine data format
                naxis = header.get("NAXIS", 0)
                
                if naxis == 1:
                    # Simple 1D spectrum
                    data = hdul[0].data
                    wavelengths = self._generate_wavelength_array(data.size, header)
                    flux = np.array(data)
                    
                elif naxis == 2:
                    # 2D spectrum - assume first row is 1D spectrum
                    data = hdul[0].data
                    if data is not None and data.size > 0:
                        if len(data.shape) == 2:
                            data = data[0, :]  # Take first row
                        wavelengths = self._generate_wavelength_array(len(data), header)
                        flux = np.array(data)
                    else:
                        return None
                else:
                    logger.warning(f"Unexpected NAXIS value: {naxis}")
                    return None
                
                # Check for error array in second extension
                error = None
                if len(hdul) > 1:
                    try:
                        error = np.array(hdul[1].data)
                    except Exception:
                        pass
                
                return SpectrumData(
                    wavelengths=wavelengths,
                    flux=flux,
                    error=error,
                    header=fits_header,
                    instrument=header.get("INSTRUME"),
                )
                
        except Exception as e:
            logger.error(f"Error reading FITS file with astropy: {e}")
            return self._read_spectrum_fallback(file_path)
    
    def _read_spectrum_fallback(self, file_path: str) -> Optional[SpectrumData]:
        """Fallback spectrum reader without astropy - basic support only."""
        try:
            # Try to read as simple binary table
            with open(file_path, "rb") as f:
                # Skip standard FITS header (up to 2880 byte blocks)
                header_size = 0
                while True:
                    block = f.read(2880)
                    if len(block) < 2880:
                        break
                    header_size += 2880
                    
                    # Check for END keyword
                    if b"END" in block:
                        # Find END and break
                        idx = block.find(b"END")
                        remaining = block[idx + 3:]
                        f.seek(header_size)
                        data = np.fromfile(f, dtype=np.float32)
                        
                        wavelengths = np.arange(len(data), dtype=np.float64)
                        return SpectrumData(
                            wavelengths=wavelengths,
                            flux=data,
                        )
                return None
        except Exception as e:
            logger.error(f"Fallback FITS read failed: {e}")
            return None
    
    def _generate_wavelength_array(self, size: int, header: Any) -> np.ndarray:
        """Generate wavelength array from FITS header."""
        # Try CRPIX, CRVAL, CDELT method (linear)
        try:
            crpix1 = header.get("CRPIX1", 1)
            crval1 = header.get("CRVAL1", 0)
            cdelt1 = header.get("CDELT1", 1)
            
            # Linear wavelength: W = CRVAL1 + (PIX - CRPIX1) * CDELT1
            pixels = np.arange(size) + 1
            wavelengths = crval1 + (pixels - crpix1) * cdelt1
            return wavelengths
        except Exception:
            pass
        
        # Fallback to simple index array
        return np.arange(size, dtype=np.float64)
    
    def validate(self, data: Any) -> bool:
        """Validate input data format."""
        if not isinstance(data, dict):
            return False
        return "file_path" in data
    
    def get_metrics(self) -> Dict[str, float]:
        """Get spectrum metrics."""
        base_metrics = super().get_metrics()
        if self._spectrum is not None:
            base_metrics.update({
                "num_points": len(self._spectrum.wavelengths),
                "mean_flux": float(np.mean(self._spectrum.flux)),
                "flux_range": float(np.max(self._spectrum.flux) - np.min(self._spectrum.flux)),
            })
        return base_metrics


# ============================================================================
# FITS Image Protocol
# ============================================================================

@protocol_plugin(
    "fits_image",
    spec=ProtocolSpec(
        name="fits_image",
        version="1.0.0",
        description="Handle astronomical image FITS files",
        skills=["image_processing", "wcs_calibration", "photometry"],
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "extract_wcs": {"type": "boolean", "default": True},
            },
            "required": ["file_path"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "shape": {"type": "array"},
                "header": {"type": "object"},
                "wcs": {"type": "object"},
                "mean": {"type": "number"},
                "std": {"type": "number"},
            },
        },
    ),
)
class FITSImageProtocol(FITSProtocol):
    """
    Protocol for handling astronomical image FITS files.
    
    Supports 2D image data commonly produced by CCD detectors.
    
    Capabilities:
    - Read image data from FITS
    - Extract WCS (World Coordinate System) information
    - Calculate basic statistics
    - Validate FITS standard compliance
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._image: Optional[ImageData] = None
        self._extract_wcs = True
    
    def initialize(self) -> None:
        """Initialize image protocol."""
        logger.info("Initializing FITSImageProtocol")
        self._image = None
        self._current_file = None
        self._header = None
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute image extraction from FITS file.
        
        Args:
            input_data: Dictionary with:
                - file_path: Path to FITS file
                - extract_wcs: Whether to extract WCS (default: True)
                
        Returns:
            ProtocolResult with image data and metadata
        """
        import time
        start_time = time.time()
        
        try:
            file_path = input_data.get("file_path")
            if not file_path:
                return ProtocolResult(
                    success=False,
                    error="Missing file_path",
                )
            
            self._extract_wcs = input_data.get("extract_wcs", True)
            
            # Read FITS file
            image = self._read_image(file_path)
            if image is None:
                return ProtocolResult(
                    success=False,
                    error="Failed to read image from FITS file",
                )
            
            self._image = image
            self._current_file = file_path
            
            result_data = {
                "file_path": file_path,
                "object_name": image.header.object_name if image.header else None,
                "shape": image.data.shape,
                "num_dimensions": len(image.data.shape),
                "telescope": image.header.telescope if image.header else None,
                "instrument": image.header.instrument if image.header else None,
                "filter": image.header.filter_name if image.header else None,
                "exposure_time": image.header.exposure_time if image.header else None,
                "mean": float(np.mean(image.data)),
                "std": float(np.std(image.data)),
                "min": float(np.min(image.data)),
                "max": float(np.max(image.data)),
            }
            
            if image.wcs:
                result_data["wcs"] = image.wcs
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "shape_0": image.data.shape[0] if len(image.data.shape) > 0 else 0,
                    "shape_1": image.data.shape[1] if len(image.data.shape) > 1 else 0,
                    "mean": float(np.mean(image.data)),
                    "std": float(np.std(image.data)),
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"FITS image error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _read_image(self, file_path: str) -> Optional[ImageData]:
        """Read image data from FITS file."""
        if not self._has_astropy:
            return self._read_image_fallback(file_path)
        
        from astropy.io import fits
        
        try:
            with fits.open(file_path) as hdul:
                header = hdul[0].header
                header_cards = [(k, header[k], header.comments[k]) for k in header.keys() if k]
                fits_header = self._parse_fits_header(header_cards)
                
                # Get data
                data = hdul[0].data
                if data is None:
                    logger.warning("No data in FITS file")
                    return None
                
                # Handle 3D data (e.g., cube) - take first plane
                if len(data.shape) > 2:
                    data = data[0, :, :]
                
                # Convert to float if needed
                if data.dtype != np.float64 and data.dtype != np.float32:
                    data = data.astype(np.float64)
                
                # Extract WCS if requested
                wcs = None
                if self._extract_wcs:
                    wcs = self._extract_wcs_info(header)
                
                return ImageData(
                    data=data,
                    header=fits_header,
                    wcs=wcs,
                    shape=data.shape,
                )
                
        except Exception as e:
            logger.error(f"Error reading FITS image with astropy: {e}")
            return self._read_image_fallback(file_path)
    
    def _read_image_fallback(self, file_path: str) -> Optional[ImageData]:
        """Fallback image reader without astropy."""
        try:
            with open(file_path, "rb") as f:
                # Skip header
                while True:
                    pos = f.tell()
                    block = f.read(2880)
                    if len(block) < 2880:
                        break
                    if b"END" in block:
                        f.seek(pos + 2880)
                        break
                
                # Read image data
                data = np.fromfile(f, dtype=np.float32)
                
                # Try to determine shape (assume square-ish)
                size = len(data)
                side = int(np.sqrt(size))
                if side * side == size:
                    data = data.reshape((side, side))
                else:
                    data = data.reshape((-1, min(side, 1000)))
                
                header = FITSHeader()
                return ImageData(data=data, header=header, shape=data.shape)
                
        except Exception as e:
            logger.error(f"Fallback FITS image read failed: {e}")
            return None
    
    def _extract_wcs_info(self, header: Any) -> Optional[Dict[str, Any]]:
        """Extract WCS information from FITS header."""
        wcs_keywords = [
            "CRPIX1", "CRPIX2",
            "CRVAL1", "CRVAL2", 
            "CDELT1", "CDELT2",
            "CD1_1", "CD1_2", "CD2_1", "CD2_2",
            "CTYPE1", "CTYPE2",
            "CRDER1", "CRDER2",
        ]
        
        wcs = {}
        for kw in wcs_keywords:
            try:
                val = header.get(kw)
                if val is not None:
                    wcs[kw.lower()] = float(val) if isinstance(val, (int, float)) else str(val)
            except Exception:
                pass
        
        return wcs if wcs else None
    
    def validate(self, data: Any) -> bool:
        """Validate input data format."""
        if not isinstance(data, dict):
            return False
        return "file_path" in data
    
    def get_metrics(self) -> Dict[str, float]:
        """Get image metrics."""
        base_metrics = super().get_metrics()
        if self._image is not None:
            base_metrics.update({
                "shape_0": self._image.data.shape[0] if len(self._image.data.shape) > 0 else 0,
                "shape_1": self._image.data.shape[1] if len(self._image.data.shape) > 1 else 0,
                "mean": float(np.mean(self._image.data)),
                "std": float(np.std(self._image.data)),
            })
        return base_metrics


# ============================================================================
# FITS Catalog Protocol
# ============================================================================

@protocol_plugin(
    "fits_catalog",
    spec=ProtocolSpec(
        name="fits_catalog",
        version="1.0.0",
        description="Handle star catalog data in FITS format",
        skills=["catalog_query", "crossmatch", "positional_astronomy"],
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "ra_col": {"type": "string"},
                "dec_col": {"type": "string"},
                "mag_col": {"type": "string"},
            },
            "required": ["file_path"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "num_entries": {"type": "integer"},
                "columns": {"type": "array"},
                "sample": {"type": "array"},
            },
        },
    ),
)
class FITSCatalogProtocol(FITSProtocol):
    """
    Protocol for handling astronomical catalog data in FITS format.
    
    Supports FITS binary tables commonly used for star catalogs
    like Hipparcos, Tycho, and SDSS.
    
    Capabilities:
    - Read catalog from FITS binary table
    - Extract column information
    - Parse coordinate data
    - Filter by position
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._catalog: List[CatalogEntry] = []
        self._columns: List[str] = []
    
    def initialize(self) -> None:
        """Initialize catalog protocol."""
        logger.info("Initializing FITSCatalogProtocol")
        self._catalog = []
        self._columns = []
        super().initialize()
    
    def execute(self, input_data: Dict[str, Any]) -> ProtocolResult:
        """
        Execute catalog reading from FITS file.
        
        Args:
            input_data: Dictionary with:
                - file_path: Path to FITS catalog file
                - ra_col: Name of RA column (default: auto-detect)
                - dec_col: Name of Dec column (default: auto-detect)
                - mag_col: Name of magnitude column (default: auto-detect)
                
        Returns:
            ProtocolResult with catalog data
        """
        import time
        start_time = time.time()
        
        try:
            file_path = input_data.get("file_path")
            if not file_path:
                return ProtocolResult(
                    success=False,
                    error="Missing file_path",
                )
            
            # Read catalog
            catalog, columns = self._read_catalog(file_path, input_data)
            if catalog is None:
                return ProtocolResult(
                    success=False,
                    error="Failed to read catalog from FITS file",
                )
            
            self._catalog = catalog
            self._columns = columns
            
            # Return sample entries
            sample_size = min(10, len(catalog))
            sample = []
            for i in range(sample_size):
                entry = catalog[i]
                sample.append({
                    "ra": entry.ra,
                    "dec": entry.dec,
                    "magnitude": entry.magnitude,
                    "name": entry.name,
                })
            
            result_data = {
                "file_path": file_path,
                "num_entries": len(catalog),
                "columns": columns,
                "sample": sample,
            }
            
            return ProtocolResult(
                success=True,
                data=result_data,
                metrics={
                    "num_entries": len(catalog),
                    "num_columns": len(columns),
                },
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            logger.error(f"FITS catalog error: {e}")
            return ProtocolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    def _read_catalog(self, file_path: str, input_data: Dict[str, Any]) -> Tuple[Optional[List[CatalogEntry]], List[str]]:
        """Read catalog data from FITS file."""
        if not self._has_astropy:
            return self._read_catalog_fallback(file_path)
        
        from astropy.io import fits
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        
        try:
            with fits.open(file_path) as hdul:
                # Handle both single and multiple extension files
                if len(hdul) > 1 and input_data.get("hdu", 1) < len(hdul):
                    hdu = hdul[input_data.get("hdu", 1)]
                else:
                    hdu = hdul[0]
                
                # Get column names
                columns = [col.name for col in hdu.columns]
                
                # Auto-detect coordinate columns
                ra_col = input_data.get("ra_col") or self._detect_column(columns, ["RA", "ra", "RAJ2000", "ALPHA"])
                dec_col = input_data.get("dec_col") or self._detect_column(columns, ["DEC", "dec", "DEJ2000", "DELTA"])
                mag_col = input_data.get("mag_col") or self._detect_column(columns, ["Vmag", "mag", "rmag", "imag"])
                
                if ra_col is None or dec_col is None:
                    logger.warning("Could not detect RA/Dec columns")
                    return [], columns
                
                # Read data
                data = hdu.data
                if data is None:
                    return [], columns
                
                catalog = []
                for row in data:
                    try:
                        ra_val = row[ra_col]
                        dec_val = row[dec_col]
                        
                        # Parse coordinates
                        if isinstance(ra_val, str):
                            # Try SkyCoord for string coordinates
                            try:
                                coord = SkyCoord(ra_val, dec_val, unit=(u.deg, u.deg))
                                ra = coord.ra.deg
                                dec = coord.dec.deg
                            except Exception:
                                continue
                        else:
                            ra = float(ra_val)
                            dec = float(dec_val)
                        
                        # Get magnitude if available
                        mag = None
                        if mag_col and mag_col in row.dtype.names:
                            try:
                                mag = float(row[mag_col])
                            except (ValueError, TypeError):
                                pass
                        
                        entry = CatalogEntry(
                            ra=ra,
                            dec=dec,
                            magnitude=mag,
                        )
                        catalog.append(entry)
                        
                    except Exception as e:
                        continue
                
                return catalog, columns
                
        except Exception as e:
            logger.error(f"Error reading FITS catalog with astropy: {e}")
            return self._read_catalog_fallback(file_path)
    
    def _read_catalog_fallback(self, file_path: str) -> Tuple[Optional[List[CatalogEntry]], List[str]]:
        """Fallback catalog reader without astropy."""
        try:
            from astropy.io import fits
            
            with fits.open(file_path) as hdul:
                if len(hdul) < 2:
                    return [], []
                
                hdu = hdul[1]
                columns = [col.name for col in hdu.columns]
                data = hdu.data
                
                if data is None:
                    return [], columns
                
                catalog = []
                for row in data:
                    try:
                        ra = float(row["RA"] if "RA" in columns else row[0])
                        dec = float(row["DEC"] if "DEC" in columns else row[1])
                        mag = float(row.get("Vmag", row.get("mag", 0)))
                        
                        entry = CatalogEntry(ra=ra, dec=dec, magnitude=mag)
                        catalog.append(entry)
                    except Exception:
                        continue
                
                return catalog, columns
                
        except Exception as e:
            logger.error(f"Fallback FITS catalog read failed: {e}")
            return None, []
    
    def _detect_column(self, columns: List[str], candidates: List[str]) -> Optional[str]:
        """Detect column name from candidates."""
        for col in columns:
            for candidate in candidates:
                if candidate.lower() in col.lower():
                    return col
        return None
    
    def validate(self, data: Any) -> bool:
        """Validate input data format."""
        if not isinstance(data, dict):
            return False
        return "file_path" in data
    
    def get_metrics(self) -> Dict[str, float]:
        """Get catalog metrics."""
        base_metrics = super().get_metrics()
        base_metrics.update({
            "num_entries": len(self._catalog),
            "num_columns": len(self._columns),
        })
        return base_metrics


# ============================================================================
# Registry Registration
# ============================================================================

# Register all FITS protocols
ProtocolRegistry.register("fits_spectrum", FITSSpectrumProtocol)
ProtocolRegistry.register("fits_image", FITSImageProtocol)
ProtocolRegistry.register("fits_catalog", FITSCatalogProtocol)
