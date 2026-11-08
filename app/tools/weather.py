"""
Weather Tool — Provides real-time weather and forecasts using Open-Meteo (100% free, no API key).
"""
from typing import Dict, Any, List
import httpx
from app.models import WeatherRequest, WeatherData

# WMO Weather Interpretation Codes
WEATHER_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


async def get_weather(request: WeatherRequest) -> WeatherData:
    """Fetch current weather + multi-day forecast for any location."""
    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1: Geocode the location name → lat/lon
        geo_resp = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": request.location,
                "count": 1,
                "language": "en",
                "format": "json",
            },
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            raise ValueError(f"Location not found: '{request.location}'")

        loc = geo_data["results"][0]
        lat = loc["latitude"]
        lon = loc["longitude"]
        display_name = f"{loc.get('name', request.location)}, {loc.get('country', '')}"

        # Step 2: Fetch weather
        weather_resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "forecast_days": request.forecast_days,
                "timezone": "auto",
            },
        )
        weather_resp.raise_for_status()
        w = weather_resp.json()

    current = w["current_weather"]
    temp_c = current["temperature"]
    temp_f = round(temp_c * 9 / 5 + 32, 1)
    code = int(current.get("weathercode", 0))

    # Build daily forecast list
    daily = w.get("daily", {})
    forecast = []
    for i, date_str in enumerate(daily.get("time", [])):
        day_code = int(daily["weathercode"][i])
        forecast.append(
            {
                "date": date_str,
                "max_temp_c": daily["temperature_2m_max"][i],
                "min_temp_c": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i] or 0.0,
                "description": WEATHER_CODES.get(day_code, "Unknown"),
            }
        )

    return WeatherData(
        location=display_name.strip(", "),
        latitude=lat,
        longitude=lon,
        current_temperature_c=temp_c,
        current_temperature_f=temp_f,
        wind_speed_kmh=current.get("windspeed", 0.0),
        weather_description=WEATHER_CODES.get(code, "Unknown"),
        forecast=forecast,
    )
