from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Farmer, FarmerCrop
from app.schemas.farmer import (
    FarmerProfileCreate, FarmerProfileUpdate, FarmerProfileResponse,
    FarmerCropCreate, FarmerCropResponse,
)
from app.core.dependencies import get_current_user
from app.utils.language import is_supported_language

router = APIRouter()


@router.post("/profile", response_model=FarmerProfileResponse)
async def create_profile(
    request: FarmerProfileCreate,
    current_user: Farmer = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.language and not is_supported_language(request.language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {request.language}",
        )

    current_user.name = request.name
    if request.age is not None:
        current_user.age = request.age
    if request.language:
        current_user.language = request.language
    if request.village is not None:
        current_user.village = request.village
    if request.latitude is not None:
        current_user.latitude = request.latitude
    if request.longitude is not None:
        current_user.longitude = request.longitude

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{farmer_id}", response_model=FarmerProfileResponse)
async def get_farmer_profile(
    farmer_id: int,
    current_user: Farmer = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found",
        )
    return farmer


@router.put("/{farmer_id}", response_model=FarmerProfileResponse)
async def update_farmer_profile(
    farmer_id: int,
    request: FarmerProfileUpdate,
    current_user: Farmer = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != farmer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own profile",
        )

    if request.language and not is_supported_language(request.language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {request.language}",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/{farmer_id}/crops", response_model=FarmerCropResponse)
async def add_farmer_crop(
    farmer_id: int,
    request: FarmerCropCreate,
    current_user: Farmer = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != farmer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add crops to your own profile",
        )

    crop = FarmerCrop(
        farmer_id=farmer_id,
        crop_name=request.crop_name.lower(),
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.get("/{farmer_id}/crops", response_model=list[FarmerCropResponse])
async def get_farmer_crops(
    farmer_id: int,
    current_user: Farmer = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crops = db.query(FarmerCrop).filter(FarmerCrop.farmer_id == farmer_id).all()
    return crops
