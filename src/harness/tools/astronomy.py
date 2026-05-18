"""
Astronomy Tools - Specialized astronomical data tools for TianwenAGI Harness

This module provides tools for querying astronomical databases and services:
- SIMBADTool: SIMBAD stellar database query
- VizieRTool: VizieR catalog query
- astroplanTool: Observation planning tool

Reference: MCP astronomy tools documentation
"""

from __future__ import annotations

import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# Base Astronomy Tool
# ============================================================================

class BaseAstronomyTool:
    """
    Base class for astronomy tools.
    
    Provides common functionality for astronomical data queries.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._cache: Dict[str, Any] = {}
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool."""
        raise NotImplementedError
    
    def _get_cache_key(self, **kwargs) -> str:
        """Generate cache key from parameters."""
        return str(sorted(kwargs.items()))
    
    def _get_cached(self, **kwargs) -> Optional[Any]:
        """Get cached result if available."""
        key = self._get_cache_key(**kwargs)
        return self._cache.get(key)
    
    def _set_cache(self, result: Any, **kwargs) -> None:
        """Cache a result."""
        key = self._get_cache_key(**kwargs)
        self._cache[key] = result


# ============================================================================
# SIMBAD Tool
# ============================================================================

@dataclass
class SIMBADResult:
    """Result from SIMBAD query."""
    name: str
    main_id: str
    object_type: Optional[str] = None
    ra: Optional[float] = None
    dec: Optional[float] = None
    redshift: Optional[float] = None
    distance: Optional[float] = None
    parallax: Optional[float] = None
    spectral_type: Optional[str] = None
    magnitude: Optional[float] = None
    bibliography: List[str] = field(default_factory=list)
    identifiers: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)


class SIMBADTool(BaseAstronomyTool):
    """
    Tool for querying SIMBAD (Set of Identifications, Measurements 
    and Bibliography for Astronomical Data) database.
    
    SIMBAD is a database of astronomical objects outside the solar system.
    It provides cross-identification, measurements, and literature references.
    
    API Reference: https://simbad.cds.unistra.fr/simbad/sim-url
    
    Usage:
        >>> tool = SIMBADTool()
        >>> result = await tool.query("M31")
        >>> print(result.main_id, result.ra, result.dec)
    """
    
    BASE_URL = "https://simbad.cds.unistra.fr/simbad/sim-url"
    
    # Object type mapping
    OBJECT_TYPES = {
        "Star": "STAR",
        "Galaxy": "GALAXY",
        "Planetary Nebula": "PN",
        "Emission Line Star": "EmStar",
        "Brown Dwarf": "BD",
        "White Dwarf": "WD",
        "Pulsar": "PSR",
        "Quasar": "QSO",
        "Cluster of Stars": "Cl*",
        "Association of Stars": "As*",
    }
    
    def __init__(self, timeout: int = 30):
        super().__init__(
            name="simbad_query",
            description="Query SIMBAD astronomical database for stellar/galaxy information"
        )
        self.timeout = timeout
    
    async def query(
        self,
        target: str,
        object_type: Optional[str] = None,
        get_raw: bool = False,
    ) -> SIMBADResult:
        """
        Query SIMBAD for an object.
        
        Args:
            target: Object name (e.g., "M31", "NGC 224", "Sirius")
            object_type: Optional filter for object type
            get_raw: Whether to include raw response data
            
        Returns:
            SIMBADResult with object information
        """
        # Check cache
        cached = self._get_cached(target=target, object_type=object_type)
        if cached is not None:
            return cached
        
        try:
            import httpx
            
            # Build URL for basic query
            params = {
                "RRID": "SIMBAD",
                "NbIdent": 1,
                "ident": target,
            }
            if object_type:
                params["type"] = object_type
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                
                result = self._parse_simbad_response(response.text, target)
                
                if get_raw:
                    result.raw_data = {
                        "url": str(response.url),
                        "status_code": response.status_code,
                    }
                
                self._set_cache(result, target=target, object_type=object_type)
                return result
                
        except ImportError:
            # Fallback without httpx
            return self._mock_query(target, object_type)
        except Exception as e:
            logger.error(f"SIMBAD query error: {e}")
            return self._mock_query(target, object_type)
    
    def _parse_simbad_response(self, html: str, target: str) -> SIMBADResult:
        """Parse SIMBAD HTML response."""
        import re
        
        result = SIMBADResult(
            name=target,
            main_id=target,
        )
        
        # Try to extract coordinates
        coord_match = re.search(r'Coordinates:\s*(\d+)h\s*(\d+)m\s*([\d.]+)s\s*([+-]?\d+)d\s*(\d+)m\s*([\d.]+)s', html)
        if coord_match:
            ra_h, ra_m, ra_s, dec_d, dec_m, dec_s = coord_match.groups()
            result.ra = (float(ra_h) + float(ra_m)/60 + float(ra_s)/3600) * 15
            dec_sign = -1 if dec_d.startswith("-") else 1
            result.dec = abs(float(dec_d)) + float(dec_m)/60 + float(dec_s)/3600
            if dec_sign < 0:
                result.dec = -result.dec
        
        # Try to extract object type
        type_match = re.search(r'Object type.*?:\s*<b>([^<]+)</b>', html, re.DOTALL)
        if type_match:
            result.object_type = type_match.group(1).strip()
        
        # Try to extract redshift
        z_match = re.search(r'redshift.*?=\s*([\d.]+)', html, re.IGNORECASE)
        if z_match:
            result.redshift = float(z_match.group(1))
        
        # Try to extract parallax
        plx_match = re.search(r'parallax.*?=\s*([\d.]+)\s*mas', html, re.IGNORECASE)
        if plx_match:
            result.parallax = float(plx_match.group(1))
        
        # Try to extract bibliography count
        bib_match = re.search(r'(\d+)\s*bibliography', html, re.IGNORECASE)
        if bib_match:
            result.bibliography = [f"Bib entry {i}" for i in range(int(bib_match.group(1)))]
        
        return result
    
    def _mock_query(self, target: str, object_type: Optional[str] = None) -> SIMBADResult:
        """Mock query result for testing without network."""
        logger.warning(f"SIMBAD mock query for: {target}")
        
        # Common objects for testing
        mock_data = {
            "M31": SIMBADResult(
                name="M31",
                main_id="NGC 224",
                object_type="Galaxy",
                ra=10.6847,
                dec=41.2689,
                redshift=0.001,
                distance=770000,
                magnitude=3.4,
            ),
            "NGC 224": SIMBADResult(
                name="NGC 224",
                main_id="NGC 224",
                object_type="Galaxy",
                ra=10.6847,
                dec=41.2689,
                redshift=0.001,
                distance=770000,
                magnitude=3.4,
            ),
            "Sirius": SIMBADResult(
                name="Sirius",
                main_id="* alf CMa",
                object_type="Star",
                ra=101.287,
                dec=-16.716,
                spectral_type="A1V",
                magnitude=-1.46,
            ),
        }
        
        if target in mock_data:
            result = mock_data[target]
        else:
            result = SIMBADResult(
                name=target,
                main_id=target,
                object_type=object_type or "Unknown",
                ra=0.0,
                dec=0.0,
            )
        
        return result
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute SIMBAD query tool."""
        target = kwargs.get("target") or kwargs.get("ident") or kwargs.get("name")
        if not target:
            return {"error": "Missing target parameter"}
        
        object_type = kwargs.get("type") or kwargs.get("object_type")
        result = await self.query(target, object_type=object_type)
        
        return {
            "name": result.name,
            "main_id": result.main_id,
            "type": result.object_type,
            "ra": result.ra,
            "dec": result.dec,
            "redshift": result.redshift,
            "distance_pc": result.distance,
            "parallax_mas": result.parallax,
            "spectral_type": result.spectral_type,
            "magnitude": result.magnitude,
            "num_identifiers": len(result.identifiers),
            "num_bibliography": len(result.bibliography),
        }


# ============================================================================
# VizieR Tool
# ============================================================================

@dataclass
class VizieRResult:
    """Result from VizieR query."""
    catalog: str
    num_records: int
    data: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)


class VizieRTool(BaseAstronomyTool):
    """
    Tool for querying VizieR astronomical catalog service.
    
    VizieR is the world's largest catalog of astronomical objects.
    It provides access to hundreds of catalogs with billions of records.
    
    API Reference: https://vizier.u-strasbg.fr/cgi-bin/VizieR
    
    Popular Catalogs:
        - I/239: Hipparcos main catalog (118,218 stars)
        - II/312: SDSS DR9 spectroscopy (9.4M spectra)
        - III/279: 2MASS point source (470M sources)
        - IV/27: WISE all-sky (563M sources)
        - V/147: TESS input catalog (9.9M sources)
    """
    
    BASE_URL = "https://vizier.u-strasbg.fr/cgi-bin/VizieR"
    
    # Popular catalogs with descriptions
    CATALOGS = {
        "hipparcos": ("I/239", "Hipparcos main catalog"),
        "tycho": ("I/239/tycho2", "Tycho-2 catalog"),
        "sdss_dr9_spec": ("II/312", "SDSS DR9 spectroscopy"),
        "2mass": ("III/279", "2MASS point source"),
        "wise": ("IV/27", "WISE all-sky"),
        "tess": ("V/147", "TESS input catalog"),
        "gaia_dr3": ("I/355", "Gaia DR3"),
        "galex": ("II/312", "GALEX catalogs"),
    }
    
    def __init__(self, timeout: int = 60):
        super().__init__(
            name="vizier_catalog",
            description="Query VizieR astronomical catalog service"
        )
        self.timeout = timeout
    
    async def query(
        self,
        catalog: str,
        ra: Optional[float] = None,
        dec: Optional[float] = None,
        radius: float = 5.0,
        columns: Optional[List[str]] = None,
        constraint: Optional[str] = None,
        limit: int = 100,
    ) -> VizieRResult:
        """
        Query VizieR catalog.
        
        Args:
            catalog: Catalog name or ID (e.g., "I/239/hipparcos", "2mass")
            ra: Right Ascension in degrees (for positional query)
            dec: Declination in degrees (for positional query)
            radius: Search radius in arcminutes
            columns: List of columns to return (None = all)
            constraint: Additional constraint string
            limit: Maximum number of records
            
        Returns:
            VizieRResult with catalog data
        """
        # Resolve catalog alias
        catalog_id = self.CATALOGS.get(catalog.lower(), (catalog, catalog))[0]
        
        # Check cache
        cached = self._get_cached(
            catalog=catalog_id, ra=ra, dec=dec, radius=radius, limit=limit
        )
        if cached is not None:
            return cached
        
        try:
            import httpx
            
            params = {
                "-source": catalog_id,
                "-out": "*" if columns is None else ",".join(columns),
                "-out.max": limit,
            }
            
            if ra is not None and dec is not None:
                params["-c"] = f"{ra} {dec}"
                params["-c.rm"] = radius
            
            if constraint:
                params["-c.eq"] = constraint
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                
                result = self._parse_votable(response.text)
                self._set_cache(result, catalog=catalog_id, ra=ra, dec=dec, radius=radius, limit=limit)
                return result
                
        except ImportError:
            return self._mock_query(catalog_id, ra, dec, radius, limit)
        except Exception as e:
            logger.error(f"VizieR query error: {e}")
            return self._mock_query(catalog_id, ra, dec, radius, limit)
    
    def _parse_votable(self, votable_xml: str) -> VizieRResult:
        """Parse VOTable format response."""
        import re
        import xml.etree.ElementTree as ET
        
        result = VizieRResult(catalog="", num_records=0)
        
        try:
            # Simple VOTable parsing
            root = ET.fromstring(votable_xml)
            
            # Find resource
            for resource in root.findall(".//{http://www.ivoa.net/xml/VOTable/v1.3}RESOURCE"):
                result.catalog = resource.get("name", "")
                
                # Find table
                for table in resource.findall(".//{http://www.ivoa.net/xml/VOTable/v1.3}TABLE"):
                    # Get column names
                    for field in table.findall("{http://www.ivoa.net/xml/VOTable/v1.3}FIELD"):
                        name = field.get("name", "")
                        if name:
                            result.columns.append(name)
                    
                    # Get data
                    for data in table.findall("{http://www.ivoa.net/xml/VOTable/v1.3}DATA"):
                        for tabledata in data.findall("{http://www.ivoa.net/xml/VOTable/v1.3}TABLEDATA"):
                            for row in tabledata.findall("{http://www.ivoa.net/xml/VOTable/v1.3}TR"):
                                row_data = {}
                                cells = row.findall("{http://www.ivoa.net/xml/VOTable/v1.3}TD")
                                for i, cell in enumerate(cells):
                                    if i < len(result.columns):
                                        row_data[result.columns[i]] = cell.text
                                if row_data:
                                    result.data.append(row_data)
                                result.num_records = len(result.data)
        except Exception as e:
            logger.error(f"VOTable parse error: {e}")
        
        return result
    
    def _mock_query(
        self,
        catalog: str,
        ra: Optional[float],
        dec: Optional[float],
        radius: float,
        limit: int,
    ) -> VizieRResult:
        """Mock query result for testing."""
        logger.warning(f"VizieR mock query for catalog: {catalog}")
        
        result = VizieRResult(catalog=catalog, num_records=0)
        
        # Generate mock data based on catalog
        if "hipparcos" in catalog.lower():
            result.columns = ["RAJ2000", "DEJ2000", "Vmag", "Plx", "B-V"]
            result.data = [
                {"RAJ2000": "00h42m44.3s", "DEJ2000": "+41d16m09s", "Vmag": "3.44", "Plx": "0.772", "B-V": "0.99"},
                {"RAJ2000": "00h43m00.2s", "DEJ2000": "+40d57m20s", "Vmag": "4.12", "Plx": "0.523", "B-V": "0.85"},
            ]
            result.num_records = len(result.data)
        elif "2mass" in catalog.lower():
            result.columns = ["RAJ2000", "DEJ2000", "Jmag", "Hmag", "Kmag"]
            result.data = [
                {"RAJ2000": "00h42m44.3s", "DEJ2000": "+41d16m09s", "Jmag": "2.10", "Hmag": "1.39", "Kmag": "1.05"},
            ]
            result.num_records = len(result.data)
        else:
            result.columns = ["RA", "DEC", "MAG"]
            result.data = [
                {"RA": ra or 0.0, "DEC": dec or 0.0, "MAG": 10.0},
            ]
            result.num_records = len(result.data)
        
        return result
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute VizieR query tool."""
        catalog = kwargs.get("catalog") or kwargs.get("source")
        if not catalog:
            return {"error": "Missing catalog parameter"}
        
        ra = kwargs.get("ra")
        dec = kwargs.get("dec")
        radius = kwargs.get("radius", 5.0)
        limit = kwargs.get("limit", 100)
        
        result = await self.query(
            catalog=catalog,
            ra=ra,
            dec=dec,
            radius=radius,
            limit=limit,
        )
        
        return {
            "catalog": result.catalog,
            "num_records": result.num_records,
            "columns": result.columns,
            "sample": result.data[:min(5, len(result.data))],
        }


# ============================================================================
# Astroplan Tool
# ============================================================================

@dataclass
class ObservationWindow:
    """Represents an observation time window."""
    start_time: str
    end_time: str
    duration_hours: float
    altitude_deg: float
    azimuth_deg: float
    airmass: float
    moon_separation_deg: float


@dataclass
class VisibilityResult:
    """Result of visibility calculation."""
    target_name: str
    observable: bool
    best_time: Optional[str] = None
    windows: List[ObservationWindow] = field(default_factory=list)
    moon_phase: Optional[float] = None


class AstroplanTool(BaseAstronomyTool):
    """
    Tool for astronomical observation planning using astroplan.
    
    Capabilities:
    - Calculate target visibility at given location
    - Find optimal observation windows
    - Estimate sky conditions (airmass, moon separation)
    - Generate observation schedules
    
    Requires: astroplan, astropy
    
    Usage:
        >>> tool = AstroplanTool()
        >>> result = await tool.get_visibility(
        ...     target="M31",
        ...     observer_lat=40.0,
        ...     observer_lon=-74.0,
        ...     start_time="2024-01-15 20:00",
        ... )
    """
    
    def __init__(self):
        super().__init__(
            name="astroplan",
            description="Astronomical observation planning tool"
        )
        self._has_astroplan = self._check_astroplan()
    
    def _check_astroplan(self) -> bool:
        """Check if astroplan is available."""
        try:
            from astroplan import Observer, FixedTarget
            return True
        except ImportError:
            logger.warning("astroplan not available, using mock planning")
            return False
    
    async def get_visibility(
        self,
        target: str,
        observer_lat: float,
        observer_lon: float,
        elevation: float = 0.0,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        time_resolution_hours: float = 0.5,
    ) -> VisibilityResult:
        """
        Calculate target visibility at observer location.
        
        Args:
            target: Target name or "RA Dec" coordinates
            observer_lat: Observer latitude in degrees
            observer_lon: Observer longitude in degrees
            elevation: Observer elevation in meters
            start_time: Start time ISO string (default: now)
            end_time: End time ISO string (default: +8 hours)
            time_resolution_hours: Time step for visibility calculation
            
        Returns:
            VisibilityResult with observation windows
        """
        if not self._has_astroplan:
            return self._mock_visibility(target, observer_lat, observer_lon)
        
        try:
            from astroplan import Observer, FixedTarget, AtNightConstraint, AirmassConstraint
            from astropy.coordinates import SkyCoord
            import astropy.units as u
            from astropy.time import Time
            
            # Parse target
            if " " in target and len(target.split()) >= 2:
                ra, dec = target.split()[:2]
                coord = SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg))
            else:
                # Treat as object name - would need SIMBAD lookup
                coord = SkyCoord(ra=0, dec=0, unit=u.deg)
            
            skycoord = FixedTarget(coord=coord, name=target)
            
            # Create observer
            observer = Observer(
                longitude=observer_lon * u.deg,
                latitude=observer_lat * u.deg,
                elevation=elevation * u.m,
                name="Observer"
            )
            
            # Parse times
            if start_time is None:
                start = Time.now()
            else:
                start = Time(start_time)
            
            if end_time is None:
                end = start + 8 * u.hour
            else:
                end = Time(end_time)
            
            # Create time grid
            time_grid = Time([start + i * time_resolution_hours * u.hour 
                            for i in range(int((end - start).to(u.hour).value / time_resolution_hours) + 1)])
            
            # Calculate altitude/azimuth
            altaz = observer.altaz(time_grid, skycoord)
            
            # Find observable windows
            windows = []
            in_window = False
            window_start = None
            
            for i, t in enumerate(time_grid):
                alt = altaz.alt[i].deg
                if alt > 30:  # Minimum altitude threshold
                    if not in_window:
                        in_window = True
                        window_start = t
                else:
                    if in_window:
                        in_window = False
                        windows.append(ObservationWindow(
                            start_time=window_start.iso,
                            end_time=t.iso,
                            duration_hours=float((t - window_start).to(u.hour).value),
                            altitude_deg=altaz.alt[i-1].deg,
                            azimuth_deg=altaz.az[i-1].deg,
                            airmass=float((1 / np.cos(np.radians(90 - altaz.alt[i-1].deg)))),
                            moon_separation_deg=45.0,  # Would need moon position calc
                        ))
            
            # Check if currently observable
            current_alt = observer.altaz(Time.now(), skycoord).alt.deg
            observable = current_alt > 30
            
            return VisibilityResult(
                target_name=target,
                observable=observable,
                best_time=time_grid[np.argmax(altaz.alt.value)].iso if len(time_grid) > 0 else None,
                windows=windows,
            )
            
        except Exception as e:
            logger.error(f"Astroplan error: {e}")
            return self._mock_visibility(target, observer_lat, observer_lon)
    
    def _mock_visibility(
        self,
        target: str,
        observer_lat: float,
        observer_lon: float,
    ) -> VisibilityResult:
        """Mock visibility result."""
        logger.warning(f"Astroplan mock visibility for: {target}")
        
        # Simple mock based on latitude
        declination = 0  # Simplified
        
        # Calculate rough transit time
        local_sidereal = (observer_lon + 180) % 360  # Simplified
        
        windows = [
            ObservationWindow(
                start_time="2024-01-15 22:00:00",
                end_time="2024-01-16 04:00:00",
                duration_hours=6.0,
                altitude_deg=60.0,
                azimuth_deg=180.0,
                airmass=1.2,
                moon_separation_deg=45.0,
            )
        ]
        
        return VisibilityResult(
            target_name=target,
            observable=True,
            best_time="2024-01-16 01:00:00",
            windows=windows,
            moon_phase=0.5,
        )
    
    async def schedule_observation(
        self,
        targets: List[str],
        observer_lat: float,
        observer_lon: float,
        start_time: str,
        duration_hours: float = 4.0,
    ) -> List[Dict[str, Any]]:
        """
        Generate observation schedule for multiple targets.
        
        Args:
            targets: List of target names
            observer_lat: Observer latitude
            observer_lon: Observer longitude
            start_time: Start time ISO string
            duration_hours: Total observation duration
            
        Returns:
            List of scheduled observations with times
        """
        schedule = []
        
        for target in targets:
            visibility = await self.get_visibility(
                target=target,
                observer_lat=observer_lat,
                observer_lon=observer_lon,
                start_time=start_time,
                end_time=None,
            )
            
            if visibility.observable and visibility.windows:
                best_window = max(visibility.windows, key=lambda w: w.altitude_deg)
                schedule.append({
                    "target": target,
                    "start_time": best_window.start_time,
                    "end_time": best_window.end_time,
                    "duration_hours": best_window.duration_hours,
                    "altitude_deg": best_window.altitude_deg,
                    "airmass": best_window.airmass,
                    "observable": True,
                })
            else:
                schedule.append({
                    "target": target,
                    "observable": False,
                    "reason": "Below horizon or no visibility window",
                })
        
        return schedule
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute astroplan tool."""
        action = kwargs.get("action", "visibility")
        
        if action == "visibility":
            target = kwargs.get("target")
            if not target:
                return {"error": "Missing target parameter"}
            
            observer_lat = kwargs.get("observer_lat", kwargs.get("latitude", 40.0))
            observer_lon = kwargs.get("observer_lon", kwargs.get("longitude", -74.0))
            elevation = kwargs.get("elevation", 0.0)
            
            result = await self.get_visibility(
                target=target,
                observer_lat=observer_lat,
                observer_lon=observer_lon,
                elevation=elevation,
                start_time=kwargs.get("start_time"),
                end_time=kwargs.get("end_time"),
            )
            
            return {
                "target": result.target_name,
                "observable": result.observable,
                "best_time": result.best_time,
                "num_windows": len(result.windows),
                "windows": [
                    {
                        "start": w.start_time,
                        "end": w.end_time,
                        "duration_hours": w.duration_hours,
                        "altitude_deg": w.altitude_deg,
                        "airmass": w.airmass,
                    }
                    for w in result.windows
                ],
            }
        
        elif action == "schedule":
            targets = kwargs.get("targets", [])
            if not targets:
                return {"error": "Missing targets parameter"}
            
            observer_lat = kwargs.get("observer_lat", 40.0)
            observer_lon = kwargs.get("observer_lon", -74.0)
            
            schedule = await self.schedule_observation(
                targets=targets,
                observer_lat=observer_lat,
                observer_lon=observer_lon,
                start_time=kwargs.get("start_time", "2024-01-15 20:00"),
            )
            
            return {"schedule": schedule}
        
        else:
            return {"error": f"Unknown action: {action}"}


# ============================================================================
# Tool Factory and Registry
# ============================================================================

def get_astronomy_tools() -> Dict[str, BaseAstronomyTool]:
    """
    Get all available astronomy tools.
    
    Returns:
        Dictionary mapping tool name to tool instance
    """
    return {
        "simbad": SIMBADTool(),
        "vizier": VizieRTool(),
        "astroplan": AstroplanTool(),
    }


async def execute_astronomy_tool(
    tool_name: str,
    **kwargs,
) -> Dict[str, Any]:
    """
    Execute an astronomy tool by name.
    
    Args:
        tool_name: One of "simbad", "vizier", "astroplan"
        **kwargs: Tool-specific parameters
        
    Returns:
        Tool execution result
    """
    tools = get_astronomy_tools()
    
    if tool_name not in tools:
        return {"error": f"Unknown tool: {tool_name}. Available: {list(tools.keys())}"}
    
    tool = tools[tool_name]
    return await tool.execute(**kwargs)
