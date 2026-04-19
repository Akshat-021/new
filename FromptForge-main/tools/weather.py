"""
Tool: weather
Returns current weather data for a city using the open-meteo.com API (free, no key needed).
First resolves the city name to lat/lon via the Open-Meteo geocoding API, then fetches weather.
"""

import json
import ssl
import urllib.request
import urllib.parse
from typing import Any

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# ── Ollama tool schema ──────────────────────────────────────────────────────
weather_schema = {
    "type": "function",
    "function": {
        "name": "weather",
        "description": (
            "Get the current weather (temperature, wind speed, humidity, weather code) "
            "for any city in the world. Uses the free Open-Meteo API — no API key required."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city, e.g. 'London', 'New York', 'Mumbai'.",
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units: 'celsius' (default) or 'fahrenheit'.",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["city"],
        },
    },
}

# WMO weather interpretation codes → human-readable labels
_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm + heavy hail",
}


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "PromptForge/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
        return json.loads(resp.read().decode())


def weather_tool(city: str, units: str = "celsius") -> dict[str, Any]:
    """
    Fetch live weather for *city*.

    Returns a dict with keys:
        success, city, latitude, longitude, temperature, temperature_unit,
        wind_speed_kmh, relative_humidity_pct, weather_description, error
    """
    try:
        # Step 1 — Geocode city
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
        )
        geo = _fetch_json(geo_url)
        results = geo.get("results")
        if not results:
            return {"success": False, "city": city, "error": f"City '{city}' not found"}

        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]
        resolved_city = f"{loc.get('name', city)}, {loc.get('country', '')}"

        # Step 2 — Fetch weather
        temp_unit = "fahrenheit" if units == "fahrenheit" else "celsius"
        weather_url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode({
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "temperature_unit": temp_unit,
                "wind_speed_unit": "kmh",
                "timezone": "auto",
            })
        )
        data = _fetch_json(weather_url)
        current = data.get("current", {})
        wmo_code = current.get("weather_code", -1)

        return {
            "success": True,
            "city": resolved_city,
            "latitude": lat,
            "longitude": lon,
            "temperature": current.get("temperature_2m"),
            "temperature_unit": "°C" if units == "celsius" else "°F",
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "relative_humidity_pct": current.get("relative_humidity_2m"),
            "weather_description": _WMO_CODES.get(wmo_code, f"Code {wmo_code}"),
            "error": None,
        }

    except Exception as e:  # noqa: BLE001
        return {"success": False, "city": city, "error": str(e)}
