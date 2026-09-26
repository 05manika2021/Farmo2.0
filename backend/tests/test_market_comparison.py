import pytest


def test_market_compare_sorted_by_net_profit(client):
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
    profits = [m["net_profit"] for m in data["markets"]]
    assert profits == sorted(profits, reverse=True)


def test_market_compare_recommendation_reason(client):
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
    data = response.json()
    reason = data["recommendation_reason"]
    assert len(reason) > 0
    assert "net profit" in reason.lower()


def test_market_compare_highest_price_not_always_recommended(client):
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
    data = response.json()
    best = next(m for m in data["markets"] if m["market_id"] == data["recommended_market_id"])
    highest_price = max(data["markets"], key=lambda m: m["price_per_quintal"])
    if best["market_id"] != highest_price["market_id"]:
        assert highest_price["price_per_quintal"] > best["price_per_quintal"]
        assert best["net_profit"] >= highest_price["net_profit"]


def test_market_compare_nashik_vs_indore(client):
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
    data = response.json()
    markets_by_id = {m["market_id"]: m for m in data["markets"]}
    indore = markets_by_id.get(1)
    nashik = markets_by_id.get(5)
    if indore and nashik:
        assert nashik["price_per_quintal"] > indore["price_per_quintal"]
        assert indore["net_profit"] > nashik["net_profit"]


def test_market_compare_all_markets_have_required_fields(client):
    response = client.post(
        "/api/v1/markets/compare",
        json={
            "crop": "tomato",
            "quantity": 3,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    data = response.json()
    for market in data["markets"]:
        assert "market_id" in market
        assert "market_name" in market
        assert "price_per_quintal" in market
        assert "distance_km" in market
        assert "transport_cost" in market
        assert "gross_revenue" in market
        assert "other_costs" in market
        assert "net_profit" in market
        assert "data_status" in market
        assert market["data_status"] == "DEMO"
        assert market["gross_revenue"] == 3 * market["price_per_quintal"]
        expected_net = market["gross_revenue"] - market["transport_cost"] - market["other_costs"]
        assert abs(market["net_profit"] - expected_net) < 0.01


def test_market_compare_no_data_for_unknown_crop(client):
    response = client.post(
        "/api/v1/markets/compare",
        json={
            "crop": " nonexistent_crop_xyz",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
        },
    )
    assert response.status_code == 404


def test_price_trend_deterministic(client):
    response = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": 1, "days": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trend"] in ["increasing", "decreasing", "stable"]
    assert data["crop"] == "onion"
    assert data["market_name"] == "Indore Mandi"
    assert data["current_price"] > 0
    assert len(data["history"]) > 0


def test_price_trend_same_data_returns_same_result(client):
    r1 = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": 1, "days": 30},
    )
    r2 = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": 1, "days": 30},
    )
    assert r1.json()["trend"] == r2.json()["trend"]
    assert r1.json()["current_price"] == r2.json()["current_price"]


def test_price_trend_history_sorted_ascending(client):
    response = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": 1, "days": 30},
    )
    data = response.json()
    dates = [h["date"] for h in data["history"]]
    assert dates == sorted(dates)


def test_price_trend_different_markets_different_trends(client):
    r1 = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": 1, "days": 30},
    )
    r2 = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": 5, "days": 30},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_price_trend_different_crops(client):
    for crop in ["onion", "tomato", "potato"]:
        response = client.get(
            "/api/v1/prices/trend",
            params={"crop": crop, "market_id": 1, "days": 30},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["trend"] in ["increasing", "decreasing", "stable"]


def test_price_trend_invalid_market(client):
    response = client.get(
        "/api/v1/prices/trend",
        params={"crop": "onion", "market_id": 9999, "days": 30},
    )
    assert response.status_code == 404
