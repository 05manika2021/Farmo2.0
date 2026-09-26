from pydantic import BaseModel, Field
from typing import Optional, List


class TransportEstimateRequest(BaseModel):
    origin_latitude: float = Field(..., ge=-90, le=90)
    origin_longitude: float = Field(..., ge=-180, le=180)
    market_latitude: float = Field(..., ge=-90, le=90)
    market_longitude: float = Field(..., ge=-180, le=180)
    quantity: float = Field(..., gt=0)
    quantity_unit: str = Field(default="quintal")


class TransportEstimateResponse(BaseModel):
    distance_km: float
    estimated_transport_cost: float
    currency: str = "INR"
    status: str = "estimated"
    assumptions: List[str]


class ProfitCalculateRequest(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    quantity_unit: str = Field(default="quintal")
    farmer_latitude: float = Field(..., ge=-90, le=90)
    farmer_longitude: float = Field(..., ge=-180, le=180)


class MarketProfitResult(BaseModel):
    market_id: int
    market_name: str
    price_per_quintal: float
    distance_km: float
    transport_cost: float
    gross_revenue: float
    other_costs: float
    net_profit: float
    data_status: str


class ProfitCalculateResponse(BaseModel):
    crop: str
    quantity: float
    quantity_unit: str
    markets: List[MarketProfitResult]
