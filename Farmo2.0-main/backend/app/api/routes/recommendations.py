from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.recommendation import SellWaitRequest, SellWaitResponse, RecommendationFactor
from app.services.recommendation_service import recommendation_service

router = APIRouter()


@router.post("/sell-wait", response_model=SellWaitResponse)
async def sell_wait_recommendation(
    request: SellWaitRequest,
    db: Session = Depends(get_db),
):
    result = recommendation_service.evaluate_sell_wait(
        crop=request.crop,
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
        farmer_lat=request.latitude,
        farmer_lon=request.longitude,
        storage_available=request.storage_available,
        db=db,
        weather_risk=request.weather_risk,
    )

    return SellWaitResponse(
        recommendation=result["recommendation"],
        reason=result["reason"],
        factors=[RecommendationFactor(**f) for f in result["factors"]],
        uncertainty=result["uncertainty"],
        data_status=result["data_status"],
        best_market_name=result["best_market_name"],
        best_market_net_profit=result["best_market_net_profit"],
        weather_risk=result.get("weather_risk"),
    )
