from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MarketResponse(BaseModel):
    id: int
    name: str
    state: str
    district: str
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class NearbyMarketsRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(default=100.0, gt=0, le=500)
    crop: Optional[str] = None


class MarketCompareRequest(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    quantity_unit: str = Field(default="quintal")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class MarketCompareResult(BaseModel):
    market_id: int
    market_name: str
    state: str
    district: str
    price_per_quintal: float
    distance_km: float
    transport_cost: float
    gross_revenue: float
    other_costs: float
    net_profit: float
    data_status: str


class MarketCompareResponse(BaseModel):
    crop: str
    quantity: float
    quantity_unit: str
    markets: List[MarketCompareResult]
    recommended_market_id: int
    recommended_market_name: str
    recommendation_reason: str
