"""
Protocols Module - Communication protocols for TianwenAGI Harness

This module provides a extensible protocol abstraction layer following
lm-evaluation-harness registry patterns and NGSS skill-based workflows.
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

__all__ = [
    "BaseProtocol",
    "ProtocolRegistry",
    "ProtocolSpec", 
    "Message",
    "ProtocolResult",
    "AstronomyProtocol",
    "SpectralAnalysisProtocol",
    "PhotometryProtocol",
    "AstronomicalCoordinateProtocol",
]
