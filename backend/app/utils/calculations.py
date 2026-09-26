import math
from typing import Optional


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def calculate_gross_revenue(quantity: float, price_per_quintal: float) -> float:
    return round(quantity * price_per_quintal, 2)


def calculate_net_profit(
    gross_revenue: float,
    transport_cost: float,
    other_costs: float = 0.0,
) -> float:
    return round(gross_revenue - transport_cost - other_costs, 2)


def calculate_transport_cost(distance_km: float, rate_per_km: float, min_cost: float = 50.0) -> float:
    cost = distance_km * rate_per_km
    return round(max(cost, min_cost), 2)
