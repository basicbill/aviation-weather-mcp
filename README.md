# Aviation Weather MCP Server

A hosted MCP (Model Context Protocol) server that gives Claude direct access to real-time aviation weather data from [aviationweather.gov](https://aviationweather.gov) — no web searching needed.

## Features

- **METARs** — Current airport weather observations worldwide
- **TAFs** — Terminal aerodrome forecasts (24-30 hour forecasts)
- **PIREPs** — Pilot reports of in-flight conditions (turbulence, icing, etc.)
- **SIGMETs/AIRMETs** — Aviation weather warnings and advisories
- **Station Info** — Airport/station lookup with coordinates and elevation

## Data Source

All data comes from the **Aviation Weather Center (AWC)** API at aviationweather.gov. This is the official FAA/NWS source — free, no API key required.

## How It Works

This server uses:
- **FastMCP** (Python) for MCP protocol handling
- **Streamable HTTP** transport for remote access
- **Render** for hosting (always-on web service)

Once deployed, add it as a custom connector in Claude Chat and Claude can directly query aviation weather data.

## Setup

### Deploy to Render

1. Push this repo to GitHub
2. Create a **Web Service** on [render.com](https://render.com)
3. Connect to this GitHub repo
4. Configure:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
5. Deploy

### Add to Claude Chat

1. Go to Claude Chat Settings → Connectors
2. Click "Add custom connector"
3. Enter your Render URL + `/mcp` (e.g., `https://your-app.onrender.com/mcp`)
4. Name it "Aviation Weather" or similar
5. Start asking Claude about METARs, TAFs, and PIREPs!

## Example Prompts

Once connected, try asking Claude:
- "What's the current METAR for KJFK?"
- "Get the TAF for Tucson International (KTUS)"
- "Are there any PIREPs for turbulence near Chicago?"
- "Show me current SIGMETs for convection"
- "What's the weather at KORD, KLAX, and KSFO?"

## Tools Reference

| Tool | Description |
|------|-------------|
| `get_metar` | Current observations for airport(s) |
| `get_taf` | Terminal forecast for airport(s) |
| `get_pireps` | Pilot reports near a station or nationwide |
| `get_airsigmet` | Current SIGMETs and AIRMETs |
| `get_station_info` | Station details and coordinates |

## Development

Run locally:
```bash
pip install -r requirements.txt
python server.py
```

Server starts on `http://localhost:8000/mcp`

## License

MIT

## Author

Built by a retired corporate pilot who wanted Claude to speak aviation weather natively. 🛩️
