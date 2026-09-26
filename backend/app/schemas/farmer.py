from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FarmerCropCreate(BaseModel):
    crop_name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    quantity_unit: str = Field(default="quintal", max_length=20)


class FarmerCropResponse(BaseModel):
    id: int
    crop_name: str
    quantity: float
    quantity_unit: str

    class Config:
        from_attributes = True


class FarmerProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=1, le=120)
    language: str = Field(default="hi", max_length=5)
    village: Optional[str] = Field(None, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FarmerProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=1, le=120)
    language: Optional[str] = Field(None, max_length=5)
    village: Optional[str] = Field(None, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FarmerProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    age: Optional[int] = None
    language: str
    village: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    crops: List[FarmerCropResponse] = []

    class Config:
        from_attributes = True
