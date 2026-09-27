from typing import Optional

from fastapi import APIRouter, Query
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
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    language: Optional[str] = None,
):
    return await _run_reverse_geocode(latitude, longitude, language)


@router.post("/reverse-geocode", response_model=ReverseGeocodeResponse)
async def reverse_geocode_post(request: ReverseGeocodeRequest):
    return await _run_reverse_geocode(
        request.latitude, request.longitude, request.language
    )
