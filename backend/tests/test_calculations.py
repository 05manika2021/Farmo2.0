import pytest
from app.utils.calculations import (
    haversine_distance,
    calculate_gross_revenue,
    calculate_net_profit,
    calculate_transport_cost,
)


def test_haversine_distance():
    dist = haversine_distance(22.7196, 75.8577, 22.9676, 76.0534)
    assert dist > 0
    assert dist < 100


def test_calculate_gross_revenue():
    revenue = calculate_gross_revenue(5, 2500)
    assert revenue == 12500.0


def test_calculate_net_profit():
    profit = calculate_net_profit(12500, 1500, 0)
    assert profit == 11000.0


def test_calculate_transport_cost():
    cost = calculate_transport_cost(50, 15.0, 50.0)
    assert cost == 750.0


def test_calculate_transport_cost_minimum():
    cost = calculate_transport_cost(1, 15.0, 50.0)
    assert cost == 50.0
