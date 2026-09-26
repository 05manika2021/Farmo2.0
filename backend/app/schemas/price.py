from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CurrentPriceResponse(BaseModel):
    market_id: int
    market_name: str
    crop_name: str
    price_per_quintal: float
    price_unit: str
    price_date: datetime
    source: Optional[str] = None
    data_status: str


class PriceHistoryQuery(BaseModel):
    crop: str = Field(..., min_length=1)
    market_id: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class PriceHistoryEntry(BaseModel):
    date: str
    price: float


class PriceTrendResponse(BaseModel):
    crop: str
    market_id: int
    market_name: str
    current_price: float
    trend: str
    history: List[PriceHistoryEntry]
    data_status: str
