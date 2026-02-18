"""
Aviation Weather MCP Server
Provides METARs, TAFs, PIREPs, and SIGMETs/AIRMETs from aviationweather.gov
for use as a Claude Chat custom connector.
"""

import json
import logging
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)

AWC_BASE = "https://aviationweather.gov/api/data"
USER_AGENT = "aviation-weather-mcp/1.0 (Claude Chat Connector)"
REQUEST_TIMEOUT = 15.0

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------


mcp = FastMCP(
    "aviation_weather_mcp",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
)

# ---------------------------------------------------------------------------
# Shared HTTP helper
# ---------------------------------------------------------------------------

async def _awc_get(endpoint: str, params: dict) -> dict | list | str:
    """Make a GET request to the aviationweather.gov API."""
    url = f"{AWC_BASE}/{endpoint}"
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=headers)

        if resp.status_code == 204:
            return {"message": "No data available for this request."}
        if resp.status_code == 400:
            return {"error": f"Bad request – check your parameters. Details: {resp.text.strip()}"}
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return resp.json()
        return resp.text.strip()


def _handle_error(e: Exception) -> str:
    """Consistent error formatting."""
    if isinstance(e, httpx.HTTPStatusError):
        return f"Error: API returned status {e.response.status_code}. {e.response.text[:300]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request to aviationweather.gov timed out. Try again."
    return f"Error: {type(e).__name__}: {str(e)}"

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="get_metar",
    annotations={
        "title": "Get METAR Observations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_metar(
    ids: str,
    hours: Optional[float] = None,
    format: Optional[str] = "json",
) -> str:
    """Fetch current METAR observations for one or more airports.

    Args:
        ids: ICAO station identifiers, comma-separated (e.g. 'KTUS', 'KORD,KJFK,KLAX').
              Also accepts 3-letter IATA codes with a K prefix for US airports.
        hours: Hours of history to retrieve (e.g. 2.0 for last 2 hours).
               Omit for latest observation only.
        format: Output format – 'json' (default, decoded fields), 'raw' (raw METAR text),
                'geojson', 'csv', or 'xml'.

    Returns:
        METAR data in the requested format. JSON format includes decoded fields such as
        temperature, dewpoint, wind, visibility, clouds, altimeter, flight category, and
        the raw observation text.
    """
    try:
        params = {"ids": ids, "format": format or "json"}
        if hours is not None:
            params["hours"] = hours
        data = await _awc_get("metar", params)
        return json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="get_taf",
    annotations={
        "title": "Get Terminal Aerodrome Forecast",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_taf(
    ids: str,
    format: Optional[str] = "json",
) -> str:
    """Fetch the current TAF (Terminal Aerodrome Forecast) for one or more airports.

    A TAF is a concise forecast of expected weather conditions within 5 statute miles
    of an airport, typically covering 24-30 hours.

    Args:
        ids: ICAO station identifiers, comma-separated (e.g. 'KTUS', 'KORD,KJFK').
        format: Output format – 'json' (default, includes decoded forecast periods),
                'raw' (raw TAF text), 'geojson', 'csv', or 'xml'.

    Returns:
        TAF data including forecast periods with wind, visibility, clouds, and weather
        conditions. JSON format includes the raw TAF and decoded forecast change groups.
    """
    try:
        params = {"ids": ids, "format": format or "json"}
        data = await _awc_get("taf", params)
        return json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="get_pireps",
    annotations={
        "title": "Get Pilot Reports (PIREPs)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_pireps(
    id: Optional[str] = None,
    distance: Optional[int] = 200,
    age: Optional[float] = 2.0,
    format: Optional[str] = "json",
) -> str:
    """Fetch Pilot Reports (PIREPs) and Aircraft Reports (AIREPs).

    PIREPs are pilot-submitted reports of actual in-flight weather conditions
    including turbulence, icing, cloud layers, and other hazards.

    Args:
        id: Center station ICAO identifier to search around (e.g. 'KORD').
            If omitted, returns recent PIREPs for the entire US.
        distance: Search radius in statute miles from the station (default 200, max ~600).
        age: Maximum age of reports in hours (default 2.0).
        format: Output format – 'json' (default), 'raw', 'geojson', or 'xml'.

    Returns:
        PIREP data including report type (UA/UUA), location, altitude, turbulence,
        icing, sky conditions, temperature, wind, and remarks.
    """
    try:
        params = {"format": format or "json"}
        if id:
            params["id"] = id
        if distance is not None:
            params["distance"] = distance
        if age is not None:
            params["age"] = age
        data = await _awc_get("pirep", params)
        return json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="get_airsigmet",
    annotations={
        "title": "Get SIGMETs and AIRMETs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_airsigmet(
    format: Optional[str] = "json",
    hazard: Optional[str] = None,
) -> str:
    """Fetch current SIGMETs (Significant Meteorological Information) and AIRMETs.

    SIGMETs warn of severe weather hazardous to all aircraft (severe turbulence,
    severe icing, volcanic ash, etc.). AIRMETs advise of conditions that may be
    hazardous to smaller aircraft.

    Args:
        format: Output format – 'json' (default), 'raw', 'geojson', or 'xml'.
        hazard: Filter by hazard type. Options include:
                'conv' (convection/thunderstorms), 'turb' (turbulence),
                'ice' (icing), 'ifr' (IFR conditions), 'mtw' (mountain wave),
                'ash' (volcanic ash). Omit for all current advisories.

    Returns:
        Active SIGMETs and AIRMETs with hazard type, severity, affected area,
        altitude range, and valid times.
    """
    try:
        params = {"format": format or "json"}
        if hazard:
            params["hazard"] = hazard
        data = await _awc_get("airsigmet", params)
        return json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="get_station_info",
    annotations={
        "title": "Get Station Information",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_station_info(
    ids: str,
    format: Optional[str] = "json",
) -> str:
    """Look up weather station information by ICAO identifier.

    Useful for finding station names, coordinates, elevation, and whether
    a station issues METARs and/or TAFs.

    Args:
        ids: ICAO station identifiers, comma-separated (e.g. 'KTUS,KORD').
        format: Output format – 'json' (default), 'geojson', or 'xml'.

    Returns:
        Station details including name, country, latitude, longitude, elevation,
        and available data types.
    """
    try:
        params = {"ids": ids, "format": format or "json"}
        data = await _awc_get("stationinfo", params)
        return json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Aviation Weather MCP server")
    mcp.run(transport="streamable-http")
