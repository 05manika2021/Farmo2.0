from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    language: str = Field(default="hi")
    farmer_id: Optional[int] = None
    crop: Optional[str] = None
    quantity: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    language: str
    intent: str
    context_used: List[str]
    data_status: str
    source: str
