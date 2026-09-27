from pydantic import BaseModel
from typing import Optional


class WeatherLocation(BaseModel):
    latitude: float
    longitude: float
    timezone: Optional[str] = None


class ForecastDay(BaseModel):
    date: Optional[str] = None
    condition: Optional[str] = None
    rain_probability: Optional[int] = None
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None


class WeatherRequest(BaseModel):
    latitude: float
    longitude: float


class WeatherResponse(BaseModel):
    temperature: Optional[float] = None
    rainfall: Optional[float] = None
    condition: Optional[str] = None
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    weather_risk: str = "unknown"
    data_status: str = "UNAVAILABLE"
    source: str = "unavailable"
    updated_at: Optional[str] = None
    location: Optional[WeatherLocation] = None
    rain_probability: Optional[int] = None
    forecast: list[ForecastDay] = []
    warning: Optional[str] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None
    # Present only on the demo fallback dataset, so the UI can label it.
    demo_label: Optional[str] = None
