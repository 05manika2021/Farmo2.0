import pytest
from unittest.mock import patch, AsyncMock
import httpx


# ─── Reverse Geocode Success (Google fallback) ───────────────────────

@pytest.mark.asyncio
async def test_reverse_geocode_success():
    from app.services.location_service import LocationService

    mock_response = {
        "status": "OK",
        "results": [{
            "formatted_address": "Indore, Madhya Pradesh, India",
            "address_components": [
                {"long_name": "Indore", "types": ["locality"]},
                {"long_name": "Indore", "types": ["administrative_area_level_2"]},
                {"long_name": "Madhya Pradesh", "types": ["administrative_area_level_1"]},
                {"long_name": "India", "types": ["country"]},
            ],
        }],
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=AsyncMock(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: mock_response,
    ))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    svc = LocationService()
    with patch("app.services.location_service.settings") as mock_settings:
        mock_settings.GOOGLE_MAPS_API_KEY = "test-key"
        with patch("app.services.maptiler_service.maptiler_service.is_configured", return_value=False):
            with patch("app.services.location_service.httpx.AsyncClient", return_value=mock_client):
                result = await svc.reverse_geocode(22.7196, 75.8577)

    assert result["village"] == "Indore"
    assert result["district"] == "Indore"
    assert result["state"] == "Madhya Pradesh"
    assert result["formatted_address"] == "Indore, Madhya Pradesh, India"
    assert result["source"] == "google_maps"
    assert result["data_status"] == "LIVE"


# ─── Reverse Geocode Missing Key ──────────────────────────────────────

@pytest.mark.asyncio
async def test_reverse_geocode_missing_key():
    from app.services.location_service import LocationService

    svc = LocationService()
    with patch("app.services.location_service.settings") as mock_settings:
        mock_settings.GOOGLE_MAPS_API_KEY = None
        with patch("app.services.maptiler_service.maptiler_service.is_configured", return_value=False):
            result = await svc.reverse_geocode(22.7196, 75.8577)

    assert result["village"] is None
    assert result["source"] == "manual"
    assert result["data_status"] == "UNAVAILABLE"
    assert "key not configured" in result["note"].lower()


# ─── Reverse Geocode API Failure ─────────────────────────────────────

@pytest.mark.asyncio
async def test_reverse_geocode_api_failure():
    from app.services.location_service import LocationService

    svc = LocationService()
    with patch("app.services.location_service.settings") as mock_settings:
        mock_settings.GOOGLE_MAPS_API_KEY = "test-key"
        with patch("app.services.maptiler_service.maptiler_service.is_configured", return_value=False):
            with patch("app.services.location_service.httpx.AsyncClient") as mock_cls:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_cls.return_value = mock_client
                result = await svc.reverse_geocode(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "manual"
    assert "timed out" in result["note"].lower()


# ─── Reverse Geocode HTTP Error ──────────────────────────────────────

@pytest.mark.asyncio
async def test_reverse_geocode_http_error():
    from app.services.location_service import LocationService

    svc = LocationService()
    with patch("app.services.location_service.settings") as mock_settings:
        mock_settings.GOOGLE_MAPS_API_KEY = "test-key"
        with patch("app.services.maptiler_service.maptiler_service.is_configured", return_value=False):
            with patch("app.services.location_service.httpx.AsyncClient") as mock_cls:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=Exception("network error"))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_cls.return_value = mock_client
                result = await svc.reverse_geocode(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "manual"


# ─── Reverse Geocode Route (no key) ─────────────────────────────────

def test_reverse_geocode_route_no_key(client):
    response = client.post(
        "/api/v1/location/reverse-geocode",
        json={"latitude": 22.7196, "longitude": 75.8577},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "manual"
    assert data["data_status"] == "UNAVAILABLE"


# ─── Reverse Geocode Empty Results ───────────────────────────────────

@pytest.mark.asyncio
async def test_reverse_geocode_empty_results():
    from app.services.location_service import LocationService

    mock_response = {"status": "ZERO_RESULTS", "results": []}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=AsyncMock(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: mock_response,
    ))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    svc = LocationService()
    with patch("app.services.location_service.settings") as mock_settings:
        mock_settings.GOOGLE_MAPS_API_KEY = "test-key"
        with patch("app.services.maptiler_service.maptiler_service.is_configured", return_value=False):
            with patch("app.services.location_service.httpx.AsyncClient", return_value=mock_client):
                result = await svc.reverse_geocode(0.0, 0.0)

    assert result["village"] is None
    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "manual"


# ─── GET route (frontend contract) ──────────────────────────────────

def test_reverse_geocode_get_route_no_key(client):
    response = client.get(
        "/api/v1/location/reverse-geocode",
        params={"latitude": 22.7196, "longitude": 75.8577, "language": "hi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "manual"
    assert data["data_status"] == "UNAVAILABLE"


def test_reverse_geocode_invalid_coords_rejected(client):
    response = client.post(
        "/api/v1/location/reverse-geocode",
        json={"latitude": 999, "longitude": 0},
    )
    assert response.status_code == 422
