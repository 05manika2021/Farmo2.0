import pytest


def test_nearby_markets(client):
    response = client.get(
        "/api/v1/markets/nearby",
        params={
            "latitude": 22.7196,
            "longitude": 75.8577,
            "radius_km": 200,
            "crop": "onion",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    for market in data["markets"]:
        assert "distance_km" in market
        assert market["distance_km"] <= 200


def test_market_compare(client):
    response = client.post(
        "/api/v1/markets/compare",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "onion"
    assert len(data["markets"]) > 0
    assert "recommended_market_id" in data
    assert "recommendation_reason" in data

    profits = [m["net_profit"] for m in data["markets"]]
    assert profits == sorted(profits, reverse=True)


def test_price_trend(client):
    markets_resp = client.get(
        "/api/v1/markets/nearby",
        params={"latitude": 22.7196, "longitude": 75.8577, "radius_km": 200, "crop": "onion"},
    )
    market_id = markets_resp.json()["markets"][0]["id"]

    response = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": market_id, "days": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "onion"
    assert data["trend"] in ["increasing", "decreasing", "stable"]
    assert len(data["history"]) > 0
