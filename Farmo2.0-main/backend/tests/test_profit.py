import pytest


def test_profit_calculation_onion_5_quintal(client):
    response = client.post(
        "/api/v1/profit/calculate",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "farmer_latitude": 22.7196,
            "farmer_longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "onion"
    assert data["quantity"] == 5
    assert len(data["markets"]) > 0

    for market in data["markets"]:
        expected_gross = 5 * market["price_per_quintal"]
        assert market["gross_revenue"] == expected_gross
        expected_net = expected_gross - market["transport_cost"] - market["other_costs"]
        assert market["net_profit"] == expected_net
        assert market["data_status"] == "DEMO"


def test_profit_sorted_by_net_profit(client):
    response = client.post(
        "/api/v1/profit/calculate",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "farmer_latitude": 22.7196,
            "farmer_longitude": 75.8577,
        },
    )
    data = response.json()
    profits = [m["net_profit"] for m in data["markets"]]
    assert profits == sorted(profits, reverse=True)


def test_profit_different_crops(client):
    for crop in ["onion", "tomato", "potato"]:
        response = client.post(
            "/api/v1/profit/calculate",
            json={
                "crop": crop,
                "quantity": 5,
                "quantity_unit": "quintal",
                "farmer_latitude": 22.7196,
                "farmer_longitude": 75.8577,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["crop"] == crop
        assert len(data["markets"]) > 0
