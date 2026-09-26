from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.schemas.market import (
    MarketResponse, NearbyMarketsRequest, MarketCompareRequest,
    MarketCompareResponse, MarketCompareResult,
)
from app.services.market_service import market_service
from app.services.profit_service import profit_service

router = APIRouter()


def _generate_comparison_reason(markets: list, crop: str) -> str:
    if len(markets) == 1:
        return (
            f"{markets[0]['market_name']} is the only market with current "
            f"{crop} data. No comparison available."
        )

    best = markets[0]
    highest_price_market = max(markets, key=lambda m: m["price_per_quintal"])

    if best["market_id"] == highest_price_market["market_id"]:
        return (
            f"{best['market_name']} has the highest mandi price "
            f"(INR {best['price_per_quintal']:.0f}/quintal) and also provides the "
            f"highest expected net profit of INR {best['net_profit']:.0f} after "
            f"estimated transport costs."
        )

    price_diff = highest_price_market["price_per_quintal"] - best["price_per_quintal"]
    profit_diff = best["net_profit"] - highest_price_market["net_profit"]

    return (
        f"Although {highest_price_market['market_name']} has a higher mandi price "
        f"(INR {highest_price_market['price_per_quintal']:.0f}/quintal vs "
        f"INR {best['price_per_quintal']:.0f}/quintal), {best['market_name']} provides "
        f"higher expected net profit of INR {best['net_profit']:.0f} after estimated "
        f"transport costs, compared to INR {highest_price_market['net_profit']:.0f} at "
        f"{highest_price_market['market_name']}."
    )


@router.get("/nearby")
async def get_nearby_markets(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=100.0, gt=0, le=500),
    crop: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    results = market_service.get_nearby_markets(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        crop=crop,
        db=db,
    )
    return {
        "markets": [
            {
                "id": r["market"].id,
                "name": r["market"].name,
                "state": r["market"].state,
                "district": r["market"].district,
                "latitude": r["market"].latitude,
                "longitude": r["market"].longitude,
                "location_name": r["market"].location_name,
                "distance_km": r["distance_km"],
            }
            for r in results
        ],
        "count": len(results),
    }


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: int, db: Session = Depends(get_db)):
    market = market_service.get_market_by_id(market_id, db)
    if not market:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market not found",
        )
    return market


@router.post("/compare", response_model=MarketCompareResponse)
async def compare_markets(
    request: MarketCompareRequest,
    db: Session = Depends(get_db),
):
    profit_data = profit_service.calculate_for_all_markets(
        crop=request.crop,
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
        farmer_lat=request.latitude,
        farmer_lon=request.longitude,
        db=db,
    )

    if not profit_data["markets"]:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data available for {request.crop}",
        )

    best = profit_data["markets"][0]

    reason = _generate_comparison_reason(profit_data["markets"], request.crop)

    return MarketCompareResponse(
        crop=request.crop,
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
        markets=[
            MarketCompareResult(**m) for m in profit_data["markets"]
        ],
        recommended_market_id=best["market_id"],
        recommended_market_name=best["market_name"],
        recommendation_reason=reason,
    )
