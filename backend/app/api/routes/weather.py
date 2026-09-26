from fastapi import APIRouter
from app.schemas.weather import WeatherRequest, WeatherResponse
from app.services.weather_service import weather_service

router = APIRouter()


@router.get("", response_model=WeatherResponse)
async def get_weather(latitude: float, longitude: float):
    result = await weather_service.get_weather(latitude, longitude)
    return WeatherResponse(**result)
