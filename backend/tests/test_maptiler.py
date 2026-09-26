import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.services.maptiler_service import (
    MapTilerService,
    _normalize_language,
    _normalize_feature,
)


def _mock_client(json_data, status_code=200, raise_exc=None):
    response = MagicMock()
    response.status_code = status_code
    if raise_exc is not None:
        response.raise_for_status = MagicMock(side_effect=raise_exc)
    else:
        response.raise_for_status = MagicMock(return_value=None)
    response.json = MagicMock(return_value=json_data)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


INDIA_FEATURES = {
    "type": "FeatureCollection",
    "features": [
        {
            "id": "municipality.1",
            "type": "Feature",
            "text": "Bhiwani",
            "place_name": "Bhiwani, Haryana, India",
            "place_type": ["municipality"],
            "properties": {"country_code": "in", "place_designation": "municipality"},
            "geometry": {"type": "Point", "coordinates": [76.13, 28.79]},
            "context": [
                {"text": "Bhiwani District", "kind": "district", "place_designation": "district"},
                {"text": "Haryana", "kind": "region", "place_designation": "region"},
                {"text": "India", "kind": "country", "place_designation": "country"},
            ],
        },
        {
            "id": "region.1",
            "type": "Feature",
            "text": "Haryana",
            "place_name": "Haryana, India",
            "place_type": ["region"],
            "properties": {"country_code": "in"},
            "geometry": {"type": "Point", "coordinates": [76.0, 29.0]},
        },
        {
            "id": "country.1",
            "type": "Feature",
            "text": "India",
            "place_name": "India",
            "place_type": ["country"],
            "properties": {"country_code": "in"},
            "geometry": {"type": "Point", "coordinates": [79.0, 22.0]},
        },
    ],
}


# ─── Missing key ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_maptiler_reverse_missing_key():
    svc = MapTilerService()
    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = None
        result = await svc.reverse_geocode(22.7196, 75.8577)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "manual"
    assert result["village"] is None
    assert "maptiler api key not configured" in result["note"].lower()
    assert result["latitude"] == 22.7196
    assert result["longitude"] == 75.8577


# ─── Reverse geocode success + normalization ─────────────────────────

@pytest.mark.asyncio
async def test_maptiler_reverse_success():
    svc = MapTilerService()
    mock_client = _mock_client(INDIA_FEATURES)

    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = "test-key"
        with patch("app.services.maptiler_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.reverse_geocode(28.79, 76.13, language="hi")

    assert result["data_status"] == "LIVE"
    assert result["source"] == "maptiler"
    assert result["village"] == "Bhiwani, Haryana, India"
    assert result["state"] == "Haryana"
    assert result["country"] == "India"
    assert result["latitude"] == 28.79
    assert result["longitude"] == 76.13
    assert result["display_name"] is not None

    # India filter + language param on the request
    call_args = mock_client.get.call_args
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert params["country"] == "IN"
    assert params["language"] == "hi"
    assert "28.79" in call_args.args[0] or "76.13" in call_args.args[0]


# ─── Reverse geocode no result ───────────────────────────────────────

@pytest.mark.asyncio
async def test_maptiler_reverse_no_result():
    svc = MapTilerService()
    mock_client = _mock_client({"type": "FeatureCollection", "features": []})

    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = "test-key"
        with patch("app.services.maptiler_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.reverse_geocode(0.0, 0.0)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "manual"
    assert result["village"] is None
    assert "could not determine" in result["note"].lower()


# ─── Reverse geocode API failure (timeout) ───────────────────────────

@pytest.mark.asyncio
async def test_maptiler_reverse_api_failure_timeout():
    svc = MapTilerService()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = "test-key"
        with patch("app.services.maptiler_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.reverse_geocode(22.7, 75.8)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "manual"
    assert "timed out" in result["note"].lower()


# ─── Reverse geocode API failure (HTTP error) ────────────────────────

@pytest.mark.asyncio
async def test_maptiler_reverse_api_failure_http_error():
    svc = MapTilerService()
    mock_client = _mock_client({}, status_code=403, raise_exc=httpx.HTTPStatusError(
        "forbidden", request=MagicMock(), response=MagicMock(status_code=403)
    ))

    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = "test-key"
        with patch("app.services.maptiler_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.reverse_geocode(22.7, 75.8)

    assert result["data_status"] == "UNAVAILABLE"
    assert result["source"] == "manual"
    assert "unavailable" in result["note"].lower()


# ─── Forward geocode success ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_maptiler_forward_success():
    svc = MapTilerService()
    mock_client = _mock_client(INDIA_FEATURES)

    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = "test-key"
        with patch("app.services.maptiler_service.httpx.AsyncClient", return_value=mock_client):
            results = await svc.forward_geocode("Bhiwani", language="en", limit=5)

    assert len(results) == 3
    assert results[0]["display_name"] == "Bhiwani, Haryana, India"
    call_args = mock_client.get.call_args
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert params["country"] == "IN"
    assert params["limit"] == 5


# ─── Forward geocode missing key ─────────────────────────────────────

@pytest.mark.asyncio
async def test_maptiler_forward_missing_key():
    svc = MapTilerService()
    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = None
        results = await svc.forward_geocode("Bhiwani")

    assert results == []


# ─── Forward geocode empty query ─────────────────────────────────────

@pytest.mark.asyncio
async def test_maptiler_forward_empty_query():
    svc = MapTilerService()
    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = "test-key"
        results = await svc.forward_geocode("   ")

    assert results == []


# ─── Language normalization ──────────────────────────────────────────

def test_normalize_language_supported():
    assert _normalize_language("hi") == "hi"
    assert _normalize_language("PA") == "pa"
    assert _normalize_language("bn") == "bn"


def test_normalize_language_unsupported_falls_back_to_en():
    assert _normalize_language("xx") == "en"
    assert _normalize_language(None) == "en"
    assert _normalize_language("") == "en"


# ─── Response normalization: missing fields stay null ────────────────

def test_normalize_feature_missing_fields_null():
    feature = {
        "type": "Feature",
        "text": "Somewhere",
        "place_name": "Somewhere",
        "place_type": ["locality"],
        "properties": {},
        "geometry": {"type": "Point", "coordinates": [75.8, 22.7]},
        "context": [],
    }
    result = _normalize_feature(feature)

    assert result["village"] == "Somewhere"
    assert result["district"] is None
    assert result["state"] is None
    assert result["country"] is None
    assert result["display_name"] == "Somewhere"
    assert result["latitude"] == 22.7
    assert result["longitude"] == 75.8


def test_normalize_feature_india_country_code():
    feature = {
        "type": "Feature",
        "text": "Haryana",
        "place_name": "Haryana",
        "place_type": ["region"],
        "properties": {"country_code": "in"},
        "geometry": {"type": "Point", "coordinates": [76.0, 29.0]},
        "context": [],
    }
    result = _normalize_feature(feature)
    assert result["state"] == "Haryana"
    assert result["country"] == "India"
    assert result["village"] is None


# ─── is_configured ───────────────────────────────────────────────────

def test_is_configured():
    svc = MapTilerService()
    with patch("app.services.maptiler_service.settings") as mock_settings:
        mock_settings.MAPTILER_API_KEY = "abc"
        assert svc.is_configured() is True
        mock_settings.MAPTILER_API_KEY = ""
        assert svc.is_configured() is False
        mock_settings.MAPTILER_API_KEY = None
        assert svc.is_configured() is False
