from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


@dataclass(frozen=True)
class WeatherResult:
    temperature_c: float
    humidity_percent: float
    wind_speed_kmh: float
    description: str


WEATHER_CODE_DESCRIPTION: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _parse_float(value: str | None, *, name: str) -> float:
    if value is None:
        raise ValueError(f"Missing required parameter: {name}")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {value}") from exc


def _validate_lat_lon(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90):
        raise ValueError("Latitude out of range (-90..90).")
    if not (-180 <= lon <= 180):
        raise ValueError("Longitude out of range (-180..180).")


def _weather_description(weather_code: int | None) -> str:
    if weather_code is None:
        return "Unknown"
    return WEATHER_CODE_DESCRIPTION.get(int(weather_code), f"Unknown (code {weather_code})")


def fetch_current_weather(*, lat: float, lon: float, timeout_s: int = 10) -> WeatherResult:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
    }

    response = requests.get(url, params=params, timeout=timeout_s)
    response.raise_for_status()
    data: dict[str, Any] = response.json()

    current = data.get("current")
    if not isinstance(current, dict):
        raise RuntimeError("Weather API response missing 'current' field.")

    temperature = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    wind_speed = current.get("wind_speed_10m")
    weather_code = current.get("weather_code")

    if temperature is None or humidity is None or wind_speed is None:
        raise RuntimeError("Weather API response missing required current values.")

    return WeatherResult(
        temperature_c=float(temperature),
        humidity_percent=float(humidity),
        wind_speed_kmh=float(wind_speed),
        description=_weather_description(int(weather_code) if weather_code is not None else None),
    )


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/weather")
def api_weather():
    try:
        lat = _parse_float(request.args.get("lat"), name="lat")
        lon = _parse_float(request.args.get("lon"), name="lon")
        _validate_lat_lon(lat, lon)

        weather = fetch_current_weather(lat=lat, lon=lon)
        return jsonify(
            ok=True,
            temperature_c=weather.temperature_c,
            humidity_percent=weather.humidity_percent,
            wind_speed_kmh=weather.wind_speed_kmh,
            description=weather.description,
            location={"lat": lat, "lon": lon},
        )
    except requests.RequestException:
        return jsonify(ok=False, error="Network error while calling weather API."), 502
    except ValueError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    except Exception:
        return jsonify(ok=False, error="Unexpected error while fetching weather."), 500


@app.get("/api/geocode")
def api_geocode():
    city = (request.args.get("city") or "").strip()
    if not city:
        return jsonify(ok=False, error="Missing required parameter: city"), 400

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 5, "language": "en", "format": "json"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        results = data.get("results") or []

        normalized = []
        for item in results:
            if not isinstance(item, dict):
                continue
            if item.get("latitude") is None or item.get("longitude") is None:
                continue
            normalized.append(
                {
                    "name": item.get("name"),
                    "country": item.get("country"),
                    "admin1": item.get("admin1"),
                    "lat": item.get("latitude"),
                    "lon": item.get("longitude"),
                }
            )

        return jsonify(ok=True, results=normalized)
    except requests.RequestException:
        return jsonify(ok=False, error="Network error while calling geocoding API."), 502
    except Exception:
        return jsonify(ok=False, error="Unexpected error while geocoding the city."), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

