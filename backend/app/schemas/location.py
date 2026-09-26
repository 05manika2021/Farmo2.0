from pydantic import BaseModel, Field
from typing import Optional


class ReverseGeocodeRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    language: Optional[str] = None


class ReverseGeocodeResponse(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    village: Optional[str] = None
    locality: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    display_name: Optional[str] = None
    formatted_address: Optional[str] = None
    source: str = "manual"
    data_status: str = "UNAVAILABLE"
    note: Optional[str] = None
