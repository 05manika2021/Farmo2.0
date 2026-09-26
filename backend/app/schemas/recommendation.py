from pydantic import BaseModel, Field
from typing import Optional, List


class SellWaitRequest(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    quantity_unit: str = Field(default="quintal")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    storage_available: bool = Field(default=True)
    weather_risk: Optional[str] = Field(default=None, description="Weather risk: low, moderate, high, unknown")


class RecommendationFactor(BaseModel):
    factor: str
    impact: str
    detail: str


class SellWaitResponse(BaseModel):
    recommendation: str
    reason: str
    factors: List[RecommendationFactor]
    uncertainty: str
    data_status: str
    best_market_name: Optional[str] = None
    best_market_net_profit: Optional[float] = None
    weather_risk: Optional[str] = None
