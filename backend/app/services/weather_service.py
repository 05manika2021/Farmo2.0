import logging
from datetime import datetime, timezone
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("farmo.weather")


class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    RAIN_KEYWORDS = {"rain", "drizzle", "thunderstorm", "shower"}
    EXTREME_KEYWORDS = {"thunderstorm", "tornado", "hurricane", "cyclone"}

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

    async def get_weather(self, latitude: float, longitude: float) -> dict:
        if not settings.WEATHER_API_KEY:
            return self._unavailable_response(
                note="Weather API key not configured. Please check WEATHER_API_KEY in .env."
            )

        try:
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": settings.WEATHER_API_KEY,
                "units": "metric",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            main = data.get("main", {})
            weather_list = data.get("weather", [])
            rain = data.get("rain", {})
            wind = data.get("wind", {})

            condition = weather_list[0]["description"] if weather_list else None
            temp = main.get("temp")
            humidity = main.get("humidity")
            rainfall_1h = rain.get("1h", 0.0)
            wind_speed = wind.get("speed")

            risk = self._determine_risk(condition, rainfall_1h, temp)
            now = datetime.now(timezone.utc).isoformat()

            return {
                "temperature": temp,
                "rainfall": rainfall_1h,
                "condition": condition,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "weather_risk": risk,
                "data_status": "LIVE",
                "source": "openweathermap",
                "updated_at": now,
            }

        except httpx.TimeoutException:
            logger.warning("Weather API timeout")
            return self._unavailable_response(
                note="Weather service timed out. Please try again later."
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"Weather API HTTP error: {e.response.status_code}")
            if e.response.status_code == 401:
                return self._unavailable_response(
                    note="Invalid weather API key. Please check WEATHER_API_KEY."
                )
            return self._unavailable_response(
                note=f"Weather API error: {e.response.status_code}."
            )
        except Exception as e:
            logger.error(f"Weather API unexpected error: {e}")
            return self._unavailable_response(
                note="Weather service unavailable."
            )

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
            "note": note,
        }


weather_service = WeatherService()
