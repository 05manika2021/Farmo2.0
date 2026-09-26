from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Market, MarketPrice
from app.utils.calculations import haversine_distance


class MarketService:
    def get_nearby_markets(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        crop: Optional[str],
        db: Session,
    ) -> List[dict]:
        markets = db.query(Market).filter(Market.is_active == True).all()
        results = []

        for market in markets:
            distance = haversine_distance(latitude, longitude, market.latitude, market.longitude)
            if distance <= radius_km:
                market_data = {
                    "market": market,
                    "distance_km": distance,
                }
                if crop:
                    latest_price = (
                        db.query(MarketPrice)
                        .filter(
                            MarketPrice.market_id == market.id,
                            MarketPrice.crop_name == crop.lower(),
                        )
                        .order_by(MarketPrice.price_date.desc())
                        .first()
                    )
                    if latest_price:
                        market_data["has_price"] = True
                        market_data["price_per_quintal"] = latest_price.price_per_quintal
                    else:
                        market_data["has_price"] = False
                results.append(market_data)

        results.sort(key=lambda x: x["distance_km"])
        return results

    def get_market_by_id(self, market_id: int, db: Session) -> Optional[Market]:
        return db.query(Market).filter(Market.id == market_id).first()

    def get_all_active_markets(self, db: Session) -> List[Market]:
        return db.query(Market).filter(Market.is_active == True).all()


market_service = MarketService()
