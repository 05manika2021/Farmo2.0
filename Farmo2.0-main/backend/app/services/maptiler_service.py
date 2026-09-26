from typing import Optional

import httpx

from app.core.config import settings

MAPTILER_GEOCODING_BASE = "https://api.maptiler.com/geocoding"

SUPPORTED_LANGUAGES = {"en", "hi", "pa", "gu", "mr", "bn"}
DEFAULT_LANGUAGE = "en"
INDIA_COUNTRY_CODE = "IN"

_SETTLEMENT_TYPES = {"municipality", "locality", "place", "neighbourhood", "microhood", "village", "town", "city"}
_DISTRICT_TYPES = {"subregion", "county", "district"}
_STATE_TYPES = {"region", "state"}
_COUNTRY_TYPES = {"country"}


def _normalize_language(language: Optional[str]) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    code = language.strip().lower()
    if code in SUPPORTED_LANGUAGES:
        return code
    return DEFAULT_LANGUAGE


def _feature_name(feature: dict) -> Optional[str]:
    return feature.get("place_name") or feature.get("text") or None


def _feature_type(feature: dict) -> Optional[str]:
    place_type = feature.get("place_type")
    if isinstance(place_type, list) and place_type:
        return place_type[0]
    if isinstance(place_type, str):
        return place_type
    props = feature.get("properties") or {}
    designation = props.get("place_designation") or feature.get("place_designation")
    if isinstance(designation, str) and designation:
        return designation
    return None


def _normalize_feature(feature: dict, latitude: Optional[float] = None, longitude: Optional[float] = None) -> dict:
    """Normalize a single MapTiler feature into Farmo location fields (null when unknown)."""
    name = _feature_name(feature)
    ftype = _feature_type(feature)
    props = feature.get("properties") or {}
    country_code = (props.get("country_code") or "").upper() or None

    village = None
    locality = None
    district = None
    state = None
    country = None

    if ftype in _COUNTRY_TYPES:
        country = name
    elif ftype in _STATE_TYPES:
        state = name
    elif ftype in _DISTRICT_TYPES:
        district = name
    elif ftype in _SETTLEMENT_TYPES:
        village = name
        if ftype in {"municipality", "locality"}:
            locality = name

    context = feature.get("context") or []
    for item in context:
        item_type = item.get("kind") or item.get("place_designation") or _feature_type(item)
        item_name = item.get("text") or item.get("place_name") or item.get("name")
        if not item_name:
            continue
        if item_type in _COUNTRY_TYPES or item_type == "country":
            country = country or item_name
        elif item_type in _STATE_TYPES or item_type in {"region", "state"}:
            state = state or item_name
        elif item_type in _DISTRICT_TYPES or item_type in {"county", "district", "subregion"}:
            district = district or item_name
        elif item_type in _SETTLEMENT_TYPES:
            if not village:
                village = item_name
            if not locality and item_type in {"municipality", "locality"}:
                locality = item_name

    if country_code == INDIA_COUNTRY_CODE and not country:
        country = "India"

    coords = feature.get("geometry", {}).get("coordinates") or []
    if latitude is None and len(coords) >= 2:
        try:
            longitude = float(coords[0])
            latitude = float(coords[1])
        except (TypeError, ValueError):
            pass

    display_name = name
    return {
        "latitude": latitude,
        "longitude": longitude,
        "village": village,
        "locality": locality,
        "district": district,
        "state": state,
        "country": country,
        "display_name": display_name,
        "formatted_address": display_name,
        "country_code": country_code,
    }


class MapTilerService:
    def is_configured(self) -> bool:
        return bool(getattr(settings, "MAPTILER_API_KEY", None))

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        language: Optional[str] = None,
    ) -> dict:
        lang = _normalize_language(language)

        if not self.is_configured():
            return {
                "latitude": latitude,
                "longitude": longitude,
                "village": None,
                "locality": None,
                "district": None,
                "state": None,
                "country": None,
                "display_name": None,
                "formatted_address": None,
                "source": "manual",
                "data_status": "UNAVAILABLE",
                "note": "MapTiler API key not configured. Please enter village manually.",
            }

        url = f"{MAPTILER_GEOCODING_BASE}/{longitude},{latitude}.json"
        params = {
            "key": settings.MAPTILER_API_KEY,
            "language": lang,
            "country": INDIA_COUNTRY_CODE,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "village": None,
                "locality": None,
                "district": None,
                "state": None,
                "country": None,
                "display_name": None,
                "formatted_address": None,
                "source": "manual",
                "data_status": "UNAVAILABLE",
                "note": "Geocoding service timed out. Please enter village manually.",
            }
        except Exception:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "village": None,
                "locality": None,
                "district": None,
                "state": None,
                "country": None,
                "display_name": None,
                "formatted_address": None,
                "source": "manual",
                "data_status": "UNAVAILABLE",
                "note": "Geocoding service unavailable. Please enter village manually.",
            }

        features = data.get("features") or []
        if not features:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "village": None,
                "locality": None,
                "district": None,
                "state": None,
                "country": None,
                "display_name": None,
                "formatted_address": None,
                "source": "manual",
                "data_status": "UNAVAILABLE",
                "note": "Could not determine location from coordinates.",
            }

        # Merge all layers (country/region/subregion/locality) from reverse results.
        merged = {
            "latitude": latitude,
            "longitude": longitude,
            "village": None,
            "locality": None,
            "district": None,
            "state": None,
            "country": None,
            "display_name": None,
            "formatted_address": None,
            "country_code": None,
        }
        for feature in features:
            normalized = _normalize_feature(feature)
            for key in ("village", "locality", "district", "state", "country", "display_name", "country_code"):
                if not merged.get(key) and normalized.get(key):
                    merged[key] = normalized[key]
            if not merged["formatted_address"] and normalized.get("formatted_address"):
                merged["formatted_address"] = normalized["formatted_address"]

        merged["source"] = "maptiler"
        merged["data_status"] = "LIVE"
        return merged

    async def forward_geocode(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 5,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> list[dict]:
        if not self.is_configured():
            return []
        if not query or not query.strip():
            return []

        lang = _normalize_language(language)
        url = f"{MAPTILER_GEOCODING_BASE}/{query.strip()}.json"
        params = {
            "key": settings.MAPTILER_API_KEY,
            "language": lang,
            "country": INDIA_COUNTRY_CODE,
            "limit": max(1, min(int(limit), 10)),
        }
        if latitude is not None and longitude is not None:
            params["proximity"] = f"{longitude},{latitude}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        results = []
        for feature in data.get("features") or []:
            results.append(_normalize_feature(feature))
        return results


maptiler_service = MapTilerService()
