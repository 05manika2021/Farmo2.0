import logging
from datetime import datetime, timezone
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("farmo.weather")


class WeatherService:
    """LIVE weather from Open-Meteo (keyless, no API key required)."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    RAIN_KEYWORDS = {"rain", "drizzle", "thunderstorm", "shower"}
    EXTREME_KEYWORDS = {"thunderstorm", "tornado", "hurricane", "cyclone"}

    # WMO weather interpretation codes -> human readable condition text.
    WMO_CODES = {
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
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
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

    def _condition_for_code(self, code) -> str:
        try:
            return self.WMO_CODES.get(int(code), "Unknown")
        except (TypeError, ValueError):
            return "Unknown"

    def _determine_risk(self, condition: Optional[str], rainfall: float, temp: float) -> str:
        if condition:
            lower = condition.lower()
            for kw in self.EXTREME_KEYWORDS:
                if kw in lower:
                    return "high"
            for kw in self.RAIN_KEYWORDS:
                if kw in lower:
                    return "moderate"
        if rainfall and rainfall > 5.0:
            return "moderate"
        if temp and (temp > 42 or temp < 5):
            return "moderate"
        return "low"

    def _build_warning(self, today_condition: str, rain_probability, forecast_conditions) -> Optional[str]:
        """Deterministic warning derived only from fetched weather values."""
        severe = [c for c in forecast_conditions if c and "thunderstorm" in c.lower()]
        if severe:
            return f"{severe[0]} expected. Avoid field work during storms."
        if rain_probability is not None and rain_probability >= 70:
            return f"{rain_probability}% chance of rain today. Cover harvested produce."
        if today_condition and "heavy rain" in today_condition.lower():
            return "Heavy rain expected. Keep harvested produce dry."
        return None

    async def get_weather(self, latitude: float, longitude: float) -> dict:
        provider = (settings.WEATHER_PROVIDER or "").strip().lower()
        if provider != "open-meteo":
            return self._fallback_response(
                latitude=latitude, longitude=longitude,
                note="Weather provider is disabled. Set WEATHER_PROVIDER=open-meteo in .env."
            )

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,precipitation_probability_max,temperature_2m_max,temperature_2m_min",
            "forecast_days": 3,
            "timezone": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            current = data.get("current", {})
            daily = data.get("daily", {})

            temp = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            rainfall = current.get("precipitation", 0.0)
            wind_speed = current.get("wind_speed_10m")
            condition = self._condition_for_code(current.get("weather_code"))

            daily_codes = daily.get("weather_code") or []
            daily_probs = daily.get("precipitation_probability_max") or []
            daily_max = daily.get("temperature_2m_max") or []
            daily_min = daily.get("temperature_2m_min") or []
            daily_dates = daily.get("time") or []

            rain_probability = daily_probs[0] if daily_probs else None

            forecast = []
            for i, code in enumerate(daily_codes):
                forecast.append({
                    "date": daily_dates[i] if i < len(daily_dates) else None,
                    "condition": self._condition_for_code(code),
                    "rain_probability": daily_probs[i] if i < len(daily_probs) else None,
                    "temp_max": daily_max[i] if i < len(daily_max) else None,
                    "temp_min": daily_min[i] if i < len(daily_min) else None,
                })

            risk = self._determine_risk(condition, rainfall, temp)
            warning = self._build_warning(
                condition,
                rain_probability,
                [f["condition"] for f in forecast],
            )
            now = datetime.now(timezone.utc).isoformat()

            return {
                "temperature": temp,
                "rainfall": rainfall,
                "condition": condition,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "weather_risk": risk,
                "data_status": "LIVE",
                "source": "open-meteo",
                "updated_at": now,
                # Structured payload required by the AI experience spec.
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": data.get("timezone"),
                },
                "rain_probability": rain_probability,
                "forecast": forecast,
                "warning": warning,
                "timestamp": now,
            }

        except httpx.TimeoutException:
            logger.warning("Weather API timeout")
            return self._fallback_response(
                latitude=latitude, longitude=longitude,
                note="Weather service timed out. Please try again later."
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"Weather API HTTP error: {e.response.status_code}")
            return self._fallback_response(
                latitude=latitude, longitude=longitude,
                note=f"Weather API error: {e.response.status_code}."
            )
        except Exception as e:
            logger.error(f"Weather API unexpected error: {e}")
            return self._fallback_response(
                latitude=latitude, longitude=longitude,
                note="Weather service unavailable."
            )

    def get_demo_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> dict:
        """Deterministic demo weather, always labelled DEMO (never LIVE)."""
        return self._demo_response(latitude, longitude)

    def _fallback_response(
        self,
        note: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> dict:
        """Live weather unavailable.

        In DEMO_MODE the farmer must still get a usable answer, so a fixed
        deterministic dataset is returned and clearly labelled DEMO. Only when
        DEMO_MODE is off does the request stay UNAVAILABLE.
        """
        if settings.DEMO_MODE:
            return self._demo_response(latitude, longitude, note=note)
        return self._unavailable_response(note=note)

    def _demo_response(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        note: str = "Live weather unavailable - showing demo weather.",
    ) -> dict:
        """Deterministic demo weather. Never presented as live data."""
        now = datetime.now(timezone.utc).isoformat()
        forecast = [
            {"date": None, "condition": "Partly cloudy", "rain_probability": 30,
             "temp_max": 32.0, "temp_min": 22.0},
            {"date": None, "condition": "Partly cloudy", "rain_probability": 20,
             "temp_max": 33.0, "temp_min": 23.0},
            {"date": None, "condition": "Sunny", "rain_probability": 10,
             "temp_max": 34.0, "temp_min": 23.0},
        ]
        return {
            "temperature": 28.0,
            "rainfall": 0.0,
            "condition": "Partly cloudy",
            "humidity": 64.0,
            "wind_speed": 12.0,
            "weather_risk": "low",
            "data_status": "DEMO",
            "source": "demo_weather",
            "updated_at": now,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "timezone": None,
            },
            "rain_probability": 30,
            "forecast": forecast,
            "warning": None,
            "timestamp": now,
            "note": note,
            "demo_label": "DEMO WEATHER",
        }

    def _unavailable_response(self, note: str = "Weather data unavailable.") -> dict:
        return {
            "temperature": None,
            "rainfall": None,
            "condition": None,
            "humidity": None,
            "wind_speed": None,
            "weather_risk": "unknown",
            "data_status": "UNAVAILABLE",
            "source": "unavailable",
            "updated_at": None,
            "location": None,
            "rain_probability": None,
            "forecast": [],
            "warning": None,
            "timestamp": None,
            "note": note,
        }


weather_service = WeatherService()
