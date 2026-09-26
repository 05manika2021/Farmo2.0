from typing import Optional

from fastapi import APIRouter
from app.schemas.location import ReverseGeocodeRequest, ReverseGeocodeResponse
from app.services.location_service import location_service

router = APIRouter()


async def _run_reverse_geocode(
    latitude: float,
    longitude: float,
    language: Optional[str] = None,
) -> ReverseGeocodeResponse:
    result = await location_service.reverse_geocode(latitude, longitude, language)
    return ReverseGeocodeResponse(**result)


@router.get("/reverse-geocode", response_model=ReverseGeocodeResponse)
async def reverse_geocode_get(
    latitude: float,
    longitude: float,
    language: Optional[str] = None,
):
    return await _run_reverse_geocode(latitude, longitude, language)


@router.post("/reverse-geocode", response_model=ReverseGeocodeResponse)
async def reverse_geocode_post(request: ReverseGeocodeRequest):
    return await _run_reverse_geocode(
        request.latitude, request.longitude, request.language
    )
