from fastapi import APIRouter, Depends
from app.schemas.profit import (
    TransportEstimateRequest, TransportEstimateResponse,
    ProfitCalculateRequest, ProfitCalculateResponse, MarketProfitResult,
)
from app.services.transport_service import transport_service
from app.services.profit_service import profit_service
from app.db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/transport/estimate", response_model=TransportEstimateResponse)
async def estimate_transport(request: TransportEstimateRequest):
    result = transport_service.estimate(
        origin_lat=request.origin_latitude,
        origin_lon=request.origin_longitude,
        market_lat=request.market_latitude,
        market_lon=request.market_longitude,
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
    )
    return TransportEstimateResponse(**result)


@router.post("/calculate", response_model=ProfitCalculateResponse)
async def calculate_profit(
    request: ProfitCalculateRequest,
    db: Session = Depends(get_db),
):
    result = profit_service.calculate_for_all_markets(
        crop=request.crop,
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
        farmer_lat=request.farmer_latitude,
        farmer_lon=request.farmer_longitude,
        db=db,
    )
    return ProfitCalculateResponse(
        crop=result["crop"],
        quantity=result["quantity"],
        quantity_unit=result["quantity_unit"],
        markets=[MarketProfitResult(**m) for m in result["markets"]],
    )
