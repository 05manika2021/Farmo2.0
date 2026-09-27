from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.schemas.price import CurrentPriceResponse, PriceTrendResponse, PriceHistoryEntry
from app.services.price_service import price_service
from app.services.market_service import market_service

router = APIRouter()


@router.get("/current")
async def get_current_price(
    crop: str = Query(..., min_length=1),
    market_id: Optional[int] = Query(default=None),
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=100.0, gt=0, le=500),
    db: Session = Depends(get_db),
):
    if market_id:
        price = price_service.get_current_price(crop, market_id, db)
        if not price:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No current price for {crop} at market {market_id}",
            )
        market = market_service.get_market_by_id(market_id, db)
        return {
            "prices": [
                {
                    "market_id": price.market_id,
                    "market_name": market.name if market else "Unknown",
                    "crop_name": price.crop_name,
                    "price_per_quintal": price.price_per_quintal,
                    "price_unit": price.price_unit,
                    "price_date": price.price_date.isoformat(),
                    "source": price.source,
                    "data_status": price.data_status,
                }
            ]
        }

    if latitude is not None and longitude is not None:
        nearby = market_service.get_nearby_markets(latitude, longitude, radius_km, crop, db)
        results = []
        for r in nearby:
            if r.get("has_price"):
                price = price_service.get_current_price(crop, r["market"].id, db)
                if price:
                    results.append({
                        "market_id": price.market_id,
                        "market_name": r["market"].name,
                        "crop_name": price.crop_name,
                        "price_per_quintal": price.price_per_quintal,
                        "price_unit": price.price_unit,
                        "price_date": price.price_date.isoformat(),
                        "source": price.source,
                        "data_status": price.data_status,
                        "distance_km": r["distance_km"],
                    })
        return {"prices": results}

    prices = price_service.get_current_prices_for_crop(crop, db)
    return {
        "prices": [
            {
                "market_id": p.market_id,
                "market_name": "Unknown",
                "crop_name": p.crop_name,
                "price_per_quintal": p.price_per_quintal,
                "price_unit": p.price_unit,
                "price_date": p.price_date.isoformat(),
                "source": p.source,
                "data_status": p.data_status,
            }
            for p in prices
        ]
    }


@router.get("/trend", response_model=PriceTrendResponse)
async def get_price_trend(
    crop: str = Query(..., min_length=1),
    market_id: int = Query(...),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    market = market_service.get_market_by_id(market_id, db)
    if not market:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market not found",
        )

    trend_data = price_service.get_price_trend(crop, market_id, days, db)
    current_row = price_service.get_current_price(crop, market_id, db)

    return PriceTrendResponse(
        crop=crop,
        market_id=market_id,
        market_name=market.name,
        current_price=trend_data["current_price"],
        trend=trend_data["trend"],
        history=[
            PriceHistoryEntry(date=h["date"], price=h["price"])
            for h in trend_data["history"]
        ],
        data_status=(current_row.data_status if current_row else "DEMO"),
    )


@router.get("/history")
async def get_price_history(
    crop: str = Query(..., min_length=1),
    market_id: int = Query(...),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    history = price_service.get_price_history(crop, market_id, start_date, end_date, db)
    return {
        "crop": crop,
        "market_id": market_id,
        "history": [
            {
                "date": h.price_date.strftime("%Y-%m-%d"),
                "price": h.price_per_quintal,
                "source": h.source,
            }
            for h in history
        ],
    }
