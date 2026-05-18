"""
Protocols Module - Communication protocols for TianwenAGI Harness

This module provides a extensible protocol abstraction layer following
lm-evaluation-harness registry patterns and NGSS skill-based workflows.

Includes:
- base: Base protocol classes and registry
- astronomy: Astronomy-specific protocols (spectral, photometry, coordinates)
- fits: FITS file handling protocols (spectrum, image, catalog)
- timedomain: Time-domain protocols (transient, variable star, light curve)
"""

from harness.protocols.base import (
    BaseProtocol,
    ProtocolRegistry,
    ProtocolSpec,
    Message,
    ProtocolResult,
)

from harness.protocols.astronomy import (
    AstronomyProtocol,
    SpectralAnalysisProtocol,
    PhotometryProtocol,
    AstronomicalCoordinateProtocol,
)

from harness.protocols.fits import (
    FITSProtocol,
    FITSSpectrumProtocol,
    FITSImageProtocol,
    FITSCatalogProtocol,
    FITSHeader,
    SpectrumData,
    ImageData,
    CatalogEntry,
)

from harness.protocols.timedomain import (
    TimeDomainProtocol,
    TransientProtocol,
    VariableStarProtocol,
    LightCurveProtocol,
    LightCurve,
    LightCurvePoint,
    TransientAlert,
    VariableStarAnalysis,
)

__all__ = [
    # Base
    "BaseProtocol",
    "ProtocolRegistry",
    "ProtocolSpec",
    "Message",
    "ProtocolResult",
    # Astronomy
    "AstronomyProtocol",
    "SpectralAnalysisProtocol",
    "PhotometryProtocol",
    "AstronomicalCoordinateProtocol",
    # FITS
    "FITSProtocol",
    "FITSSpectrumProtocol",
    "FITSImageProtocol",
    "FITSCatalogProtocol",
    "FITSHeader",
    "SpectrumData",
    "ImageData",
    "CatalogEntry",
    # Time Domain
    "TimeDomainProtocol",
    "TransientProtocol",
    "VariableStarProtocol",
    "LightCurveProtocol",
    "LightCurve",
    "LightCurvePoint",
    "TransientAlert",
    "VariableStarAnalysis",
]
