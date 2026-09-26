from typing import List
from app.core.config import settings
from app.utils.calculations import haversine_distance, calculate_transport_cost


class TransportService:
    def estimate(
        self,
        origin_lat: float,
        origin_lon: float,
        market_lat: float,
        market_lon: float,
        quantity: float,
        quantity_unit: str,
    ) -> dict:
        distance = haversine_distance(origin_lat, origin_lon, market_lat, market_lon)
        cost = calculate_transport_cost(
            distance_km=distance,
            rate_per_km=settings.TRANSPORT_RATE_PER_KM,
            min_cost=settings.TRANSPORT_MIN_COST,
        )

        assumptions = [
            f"Transport rate: INR {settings.TRANSPORT_RATE_PER_KM}/km",
            f"Minimum transport cost: INR {settings.TRANSPORT_MIN_COST}",
            f"Distance calculated using haversine formula (straight-line)",
            f"Actual road distance may be 20-40% longer",
            f"Quantity: {quantity} {quantity_unit}",
        ]

        return {
            "distance_km": distance,
            "estimated_transport_cost": cost,
            "currency": "INR",
            "status": "estimated",
            "assumptions": assumptions,
        }


transport_service = TransportService()
