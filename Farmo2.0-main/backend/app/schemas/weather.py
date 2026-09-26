from pydantic import BaseModel
from typing import Optional


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
    note: Optional[str] = None
