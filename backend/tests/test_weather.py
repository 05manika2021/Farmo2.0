import pytest
from unittest.mock import patch, AsyncMock
import httpx


# ─── Weather API Success ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_success():
    from app.services.weather_service import WeatherService

    mock_response = {
        "main": {"temp": 28.5, "humidity": 65},
        "weather": [{"description": "clear sky"}],
        "rain": {"1h": 0.0},
        "wind": {"speed": 3.2},
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=AsyncMock(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: mock_response,
    ))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_API_KEY = "test-key"
        with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.get_weather(22.7196, 75.8577)

    assert result["temperature"] == 28.5
    assert result["condition"] == "clear sky"
    assert result["humidity"] == 65
    assert result["wind_speed"] == 3.2
    assert result["rainfall"] == 0.0
    assert result["data_status"] == "LIVE"
    assert result["source"] == "openweathermap"
    assert result["weather_risk"] == "low"
    assert result["updated_at"] is not None


# ─── Weather API Failure ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_api_failure():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_API_KEY = "test-key"
        with patch("app.services.weather_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await svc.get_weather(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "unavailable"
    assert result["weather_risk"] == "unknown"
    assert result["note"] is not None


# ─── Weather API Missing Key ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_missing_api_key():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_API_KEY = None
        result = await svc.get_weather(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["weather_risk"] == "unknown"
    assert "key not configured" in result["note"].lower()


# ─── Weather API Unauthorized ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_api_unauthorized():
    from app.services.weather_service import WeatherService

    svc = WeatherService()
    with patch("app.services.weather_service.settings") as mock_settings:
        mock_settings.WEATHER_API_KEY = "bad-key"
        with patch("app.services.weather_service.httpx.AsyncClient") as mock_cls:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            http_error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=AsyncMock(),
                response=mock_response,
            )
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=http_error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await svc.get_weather(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert "invalid" in result["note"].lower() or "key" in result["note"].lower()


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

def test_weather_route_no_key(client):
    response = client.get("/api/v1/weather?latitude=22.7196&longitude=75.8577")
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] == "UNAVAILABLE"
    assert data["weather_risk"] == "unknown"
