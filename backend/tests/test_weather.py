import pytest
from unittest.mock import patch, AsyncMock
import httpx


OPEN_METEO_RESPONSE = {
    "timezone": "Asia/Kolkata",
    "current": {
        "temperature_2m": 29.8,
        "relative_humidity_2m": 49,
        "precipitation": 0.0,
        "weather_code": 0,
        "wind_speed_10m": 14.9,
    },
    "daily": {
        "time": ["2026-09-27", "2026-09-28", "2026-09-29"],
        "weather_code": [0, 61, 95],
        "precipitation_probability_max": [0, 4, 2],
        "temperature_2m_max": [33.0, 31.0, 30.0],
        "temperature_2m_min": [22.0, 21.0, 20.0],
    },
}


def _mock_client(response_payload=None, side_effect=None):
    client = AsyncMock()
    if side_effect is not None:
        client.get = AsyncMock(side_effect=side_effect)
    else:
        client.get = AsyncMock(return_value=AsyncMock(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: response_payload,
        ))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ─── Weather API Success ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_success():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_PROVIDER = "open-meteo"
        with patch("app.services.weather_service.httpx.AsyncClient",
                   return_value=_mock_client(OPEN_METEO_RESPONSE)):
            result = await svc.get_weather(22.7196, 75.8577)

    assert result["temperature"] == 29.8
    assert result["condition"] == "Clear sky"
    assert result["humidity"] == 49
    assert result["wind_speed"] == 14.9
    assert result["rainfall"] == 0.0
    assert result["data_status"] == "LIVE"
    assert result["source"] == "open-meteo"
    assert result["weather_risk"] == "low"
    assert result["updated_at"] is not None

    # Structured payload required by the AI experience spec.
    assert result["location"]["latitude"] == 22.7196
    assert result["location"]["longitude"] == 75.8577
    assert result["location"]["timezone"] == "Asia/Kolkata"
    assert result["rain_probability"] == 0
    assert len(result["forecast"]) == 3
    assert result["forecast"][1]["condition"] == "Slight rain"
    assert result["timestamp"] == result["updated_at"]
    # Day 3 forecasts a thunderstorm -> deterministic warning.
    assert "Thunderstorm" in result["warning"]


# ─── Weather API Failure ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_api_failure():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_PROVIDER = "open-meteo"
        mock_settings.DEMO_MODE = False
        with patch("app.services.weather_service.httpx.AsyncClient",
                   return_value=_mock_client(side_effect=httpx.TimeoutException("timeout"))):
            result = await svc.get_weather(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "unavailable"
    assert result["weather_risk"] == "unknown"
    assert result["note"] is not None


# ─── Weather Provider Disabled ────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_provider_disabled():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_PROVIDER = "disabled"
        mock_settings.DEMO_MODE = False
        result = await svc.get_weather(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["weather_risk"] == "unknown"
    assert "provider is disabled" in result["note"].lower()


# ─── Weather API Unauthorized ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_api_unauthorized():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_PROVIDER = "open-meteo"
        mock_settings.DEMO_MODE = False
        mock_response = AsyncMock()
        mock_response.status_code = 401
        http_error = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=AsyncMock(),
            response=mock_response,
        )
        with patch("app.services.weather_service.httpx.AsyncClient",
                   return_value=_mock_client(side_effect=http_error)):
            result = await svc.get_weather(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert "401" in result["note"]


# ─── Weather Risk Determination ───────────────────────────────────────

def test_weather_risk_high_for_thunderstorm():
    from app.services.weather_service import WeatherService
    svc = WeatherService()
    assert svc._determine_risk("thunderstorm", 0.0, 25.0) == "high"


def test_weather_risk_moderate_for_rain():
    from app.services.weather_service import WeatherService
    svc = WeatherService()
    assert svc._determine_risk("light rain", 2.0, 25.0) == "moderate"


def test_weather_risk_moderate_for_high_rainfall():
    from app.services.weather_service import WeatherService
    svc = WeatherService()
    assert svc._determine_risk("overcast clouds", 10.0, 25.0) == "moderate"


def test_weather_risk_low_for_clear():
    from app.services.weather_service import WeatherService
    svc = WeatherService()
    assert svc._determine_risk("clear sky", 0.0, 28.0) == "low"


def test_weather_risk_moderate_for_extreme_temp():
    from app.services.weather_service import WeatherService
    svc = WeatherService()
    assert svc._determine_risk("clear sky", 0.0, 45.0) == "moderate"


# ─── Weather Route (HTTP) ────────────────────────────────────────────

def test_weather_route_provider_disabled(client):
    # conftest runs with DEMO_MODE=true, so a disabled provider must degrade
    # to the labelled demo dataset instead of leaving the farmer with nothing.
    response = client.get("/api/v1/weather?latitude=22.7196&longitude=75.8577")
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] == "DEMO"
    assert data["demo_label"] == "DEMO WEATHER"
    assert data["temperature"] == 28.0
    assert data["forecast"]
    assert "provider is disabled" in data["note"].lower()


def test_weather_route_unavailable_when_demo_mode_off(client):
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_PROVIDER = "disabled"
        mock_settings.DEMO_MODE = False
        response = client.get("/api/v1/weather?latitude=22.7196&longitude=75.8577")
        assert response.status_code == 200
        data = response.json()
        assert data["data_status"] == "UNAVAILABLE"
        assert data["weather_risk"] == "unknown"
        assert data["forecast"] == []


# ─── Demo weather fallback ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_api_failure_falls_back_to_demo_in_demo_mode():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_PROVIDER = "open-meteo"
        mock_settings.DEMO_MODE = True
        with patch("app.services.weather_service.httpx.AsyncClient",
                   return_value=_mock_client(side_effect=httpx.TimeoutException("timeout"))):
            result = await svc.get_weather(22.7196, 75.8577)

    assert result["data_status"] == "DEMO"
    assert result["demo_label"] == "DEMO WEATHER"
    assert result["temperature"] == 28.0
    assert result["condition"] == "Partly cloudy"
    assert result["rain_probability"] == 30
    assert result["wind_speed"] == 12.0
    assert result["source"] == "demo_weather"
    assert result["note"] is not None


def test_demo_weather_helper_is_always_labelled_demo():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    result = svc.get_demo_weather(22.7196, 75.8577)
    assert result["data_status"] == "DEMO"
    assert result["demo_label"] == "DEMO WEATHER"
    assert result["location"]["latitude"] == 22.7196
