from typing import List
from sqlalchemy.orm import Session
from app.db.models import Market, MarketPrice
from app.services.transport_service import transport_service
from app.utils.calculations import haversine_distance, calculate_gross_revenue, calculate_net_profit


class ProfitService:
    def calculate_for_all_markets(
        self,
        crop: str,
        quantity: float,
        quantity_unit: str,
        farmer_lat: float,
        farmer_lon: float,
        db: Session,
    ) -> dict:
        markets = db.query(Market).filter(Market.is_active == True).all()
        results = []

        for market in markets:
            latest_price = (
                db.query(MarketPrice)
                .filter(
                    MarketPrice.market_id == market.id,
                    MarketPrice.crop_name == crop.lower(),
                )
                .order_by(MarketPrice.price_date.desc())
                .first()
            )

            if not latest_price:
                continue

            distance = haversine_distance(farmer_lat, farmer_lon, market.latitude, market.longitude)
            transport = transport_service.estimate(
                origin_lat=farmer_lat,
                origin_lon=farmer_lon,
                market_lat=market.latitude,
                market_lon=market.longitude,
                quantity=quantity,
                quantity_unit=quantity_unit,
            )

            gross_revenue = calculate_gross_revenue(quantity, latest_price.price_per_quintal)
            other_costs = 0.0
            net_profit = calculate_net_profit(gross_revenue, transport["estimated_transport_cost"], other_costs)

            results.append({
                "market_id": market.id,
                "market_name": market.name,
                "state": market.state,
                "district": market.district,
                "price_per_quintal": latest_price.price_per_quintal,
                "distance_km": distance,
                "transport_cost": transport["estimated_transport_cost"],
                "gross_revenue": gross_revenue,
                "other_costs": other_costs,
                "net_profit": net_profit,
                "data_status": latest_price.data_status,
            })

        results.sort(key=lambda x: x["net_profit"], reverse=True)

        return {
            "crop": crop,
            "quantity": quantity,
            "quantity_unit": quantity_unit,
            "markets": results,
        }


profit_service = ProfitService()
