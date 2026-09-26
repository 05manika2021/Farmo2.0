import pytest


def test_sell_wait_returns_valid_recommendation(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] in ["SELL_NOW", "WAIT", "SELL_IN_ANOTHER_MARKET"]
    assert len(data["reason"]) > 0
    assert len(data["factors"]) > 0
    assert len(data["uncertainty"]) > 0
    assert data["data_status"] == "DEMO"
    assert data["best_market_name"] is not None
    assert data["best_market_net_profit"] is not None


def test_sell_wait_factors_have_required_fields(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
        },
    )
    data = response.json()
    for factor in data["factors"]:
        assert "factor" in factor
        assert "impact" in factor
        assert "detail" in factor
        assert factor["impact"] in ["positive", "negative", "neutral"]


def test_sell_wait_no_storage_forces_sell_now(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": False,
        },
    )
    data = response.json()
    assert data["recommendation"] in ["SELL_NOW", "SELL_IN_ANOTHER_MARKET"]
    storage_factors = [f for f in data["factors"] if f["factor"] == "Storage"]
    assert len(storage_factors) > 0
    assert storage_factors[0]["impact"] == "negative"


def test_sell_wait_with_storage_allows_wait(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
        },
    )
    data = response.json()
    storage_factors = [f for f in data["factors"] if f["factor"] == "Storage"]
    assert len(storage_factors) > 0
    assert storage_factors[0]["impact"] == "positive"


def test_sell_wait_deterministic(client):
    payload = {
        "crop": "onion",
        "quantity": 5,
        "quantity_unit": "quintal",
        "latitude": 22.7196,
        "longitude": 75.8577,
        "storage_available": True,
    }
    r1 = client.post("/api/v1/recommendations/sell-wait", json=payload)
    r2 = client.post("/api/v1/recommendations/sell-wait", json=payload)
    assert r1.json()["recommendation"] == r2.json()["recommendation"]
    assert r1.json()["reason"] == r2.json()["reason"]


def test_sell_wait_different_crops(client):
    for crop in ["onion", "tomato", "potato"]:
        response = client.post(
            "/api/v1/recommendations/sell-wait",
            json={
                "crop": crop,
                "quantity": 5,
                "quantity_unit": "quintal",
                "latitude": 22.7196,
                "longitude": 75.8577,
                "storage_available": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation"] in ["SELL_NOW", "WAIT", "SELL_IN_ANOTHER_MARKET"]


def test_sell_wait_unknown_crop(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "nonexistent_crop_xyz",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "WAIT"
    assert "No current market data" in data["reason"]


def test_sell_wait_uncertainty_mentions_limitations(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
        },
    )
    data = response.json()
    uncertainty = data["uncertainty"].lower()
    assert "transport" in uncertainty or "distance" in uncertainty
    assert "weather" in uncertainty or "demand" in uncertainty


def test_sell_wait_factors_include_price_trend(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
        },
    )
    data = response.json()
    factor_names = [f["factor"] for f in data["factors"]]
    assert "Current Price" in factor_names
    assert "Price Trend" in factor_names
    assert "Transport Cost" in factor_names


# ─── Sell/Wait with Weather Data ─────────────────────────────────────

def test_sell_wait_with_weather_high_risk(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
            "weather_risk": "high",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] in ["SELL_NOW", "WAIT", "SELL_IN_ANOTHER_MARKET"]
    assert data["weather_risk"] == "high"
    weather_factors = [f for f in data["factors"] if f["factor"] == "Weather Risk"]
    assert len(weather_factors) == 1
    assert weather_factors[0]["impact"] == "negative"
    assert "severe" in weather_factors[0]["detail"].lower() or "consider selling" in weather_factors[0]["detail"].lower()


def test_sell_wait_with_weather_moderate_risk(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
            "weather_risk": "moderate",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["weather_risk"] == "moderate"
    weather_factors = [f for f in data["factors"] if f["factor"] == "Weather Risk"]
    assert len(weather_factors) == 1
    assert weather_factors[0]["impact"] == "negative"


def test_sell_wait_with_weather_low_risk(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
            "weather_risk": "low",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["weather_risk"] == "low"
    weather_factors = [f for f in data["factors"] if f["factor"] == "Weather Risk"]
    assert len(weather_factors) == 1
    assert weather_factors[0]["impact"] == "positive"


# ─── Sell/Wait without Weather Data ──────────────────────────────────

def test_sell_wait_without_weather_data(client):
    response = client.post(
        "/api/v1/recommendations/sell-wait",
        json={
            "crop": "onion",
            "quantity": 5,
            "quantity_unit": "quintal",
            "latitude": 22.7196,
            "longitude": 75.8577,
            "storage_available": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["weather_risk"] is None
    weather_factors = [f for f in data["factors"] if f["factor"] == "Weather Risk"]
    assert len(weather_factors) == 0


def test_sell_wait_without_weather_deterministic(client):
    payload = {
        "crop": "onion",
        "quantity": 5,
        "quantity_unit": "quintal",
        "latitude": 22.7196,
        "longitude": 75.8577,
        "storage_available": True,
    }
    r1 = client.post("/api/v1/recommendations/sell-wait", json=payload)
    r2 = client.post("/api/v1/recommendations/sell-wait", json=payload)
    assert r1.json()["recommendation"] == r2.json()["recommendation"]
    assert r1.json()["reason"] == r2.json()["reason"]


# ─── Sell/Wait: Weather does NOT override net profit ─────────────────

def test_sell_wait_weather_does_not_change_net_profit(client):
    payload = {
        "crop": "onion",
        "quantity": 5,
        "quantity_unit": "quintal",
        "latitude": 22.7196,
        "longitude": 75.8577,
        "storage_available": True,
    }
    r1 = client.post("/api/v1/recommendations/sell-wait", json=payload)
    r2 = client.post("/api/v1/recommendations/sell-wait", json={**payload, "weather_risk": "high"})
    assert r1.json()["best_market_net_profit"] == r2.json()["best_market_net_profit"]
    assert r1.json()["best_market_name"] == r2.json()["best_market_name"]
