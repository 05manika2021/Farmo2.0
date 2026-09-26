from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import MarketPrice, PriceHistory


class PriceService:
    def get_current_price(
        self, crop: str, market_id: int, db: Session
    ) -> Optional[MarketPrice]:
        return (
            db.query(MarketPrice)
            .filter(
                MarketPrice.market_id == market_id,
                MarketPrice.crop_name == crop.lower(),
            )
            .order_by(MarketPrice.price_date.desc())
            .first()
        )

    def get_current_prices_for_crop(
        self, crop: str, db: Session
    ) -> List[MarketPrice]:
        return (
            db.query(MarketPrice)
            .filter(MarketPrice.crop_name == crop.lower())
            .all()
        )

    def get_price_history(
        self,
        crop: str,
        market_id: int,
        start_date: Optional[str],
        end_date: Optional[str],
        db: Session,
    ) -> List[PriceHistory]:
        query = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.market_id == market_id,
                PriceHistory.crop_name == crop.lower(),
            )
            .order_by(PriceHistory.price_date.asc())
        )

        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(PriceHistory.price_date >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(PriceHistory.price_date <= end_dt)

        return query.all()

    def get_price_trend(
        self, crop: str, market_id: int, days: int, db: Session
    ) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        history = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.market_id == market_id,
                PriceHistory.crop_name == crop.lower(),
                PriceHistory.price_date >= cutoff,
            )
            .order_by(PriceHistory.price_date.asc())
            .all()
        )

        if not history:
            return {
                "trend": "stable",
                "history": [],
                "current_price": 0,
            }

        prices = [h.price_per_quintal for h in history]
        current_price = prices[-1] if prices else 0

        if len(prices) < 2:
            return {
                "trend": "stable",
                "history": [
                    {"date": h.price_date.strftime("%Y-%m-%d"), "price": h.price_per_quintal}
                    for h in history
                ],
                "current_price": current_price,
            }

        first_half = prices[: len(prices) // 2]
        second_half = prices[len(prices) // 2 :]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        diff_pct = ((avg_second - avg_first) / avg_first) * 100 if avg_first > 0 else 0

        if diff_pct > 5:
            trend = "increasing"
        elif diff_pct < -5:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "history": [
                {"date": h.price_date.strftime("%Y-%m-%d"), "price": h.price_per_quintal}
                for h in history
            ],
            "current_price": current_price,
        }


price_service = PriceService()
