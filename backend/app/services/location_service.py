import httpx
from typing import Optional
from app.core.config import settings
from app.services.maptiler_service import maptiler_service


def _manual_result(note: str, latitude: Optional[float] = None, longitude: Optional[float] = None) -> dict:
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
        "note": note,
    }


class LocationService:
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        language: Optional[str] = None,
    ) -> dict:
        # Primary: MapTiler Cloud Geocoding (India-filtered, localized)
        maptiler_result = None
        if maptiler_service.is_configured():
            maptiler_result = await maptiler_service.reverse_geocode(
                latitude, longitude, language
            )
            if maptiler_result.get("data_status") == "LIVE":
                return maptiler_result

        # Fallback: Google Maps Geocoding (existing provider)
        google_result = await self._google_reverse_geocode(latitude, longitude)
        if google_result.get("data_status") == "LIVE":
            return google_result

        # Prefer a concrete "no result" note over a generic provider error
        for candidate in (maptiler_result, google_result):
            if candidate and candidate.get("note") and (
                "could not determine" in candidate["note"].lower()
                or "not configured" in candidate["note"].lower()
            ):
                candidate["latitude"] = latitude
                candidate["longitude"] = longitude
                return candidate

        if maptiler_result:
            maptiler_result["latitude"] = latitude
            maptiler_result["longitude"] = longitude
            return maptiler_result
        if google_result.get("note"):
            google_result["latitude"] = latitude
            google_result["longitude"] = longitude
            return google_result
        return _manual_result(
            "Geocoding API key not configured. Please enter village manually.",
            latitude,
            longitude,
        )

    async def _google_reverse_geocode(self, latitude: float, longitude: float) -> dict:
        if not settings.GOOGLE_MAPS_API_KEY:
            return _manual_result(
                "Google Maps API key not configured. Please enter village manually.",
                latitude,
                longitude,
            )

        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": settings.GOOGLE_MAPS_API_KEY,
                "language": "en",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                return _manual_result(
                    "Could not determine location from coordinates.",
                    latitude,
                    longitude,
                )

            result = data["results"][0]
            address_components = result.get("address_components", [])
            formatted_address = result.get("formatted_address", "")

            village = None
            locality = None
            district = None
            state = None
            country = None

            for component in address_components:
                types = component.get("types", [])
                long_name = component.get("long_name", "")
                if "sublocality_level_1" in types or "locality" in types:
                    village = village or long_name
                    locality = locality or long_name
                elif "administrative_area_level_2" in types:
                    district = district or long_name
                elif "administrative_area_level_1" in types:
                    state = state or long_name
                elif "country" in types:
                    country = country or long_name

            return {
                "latitude": latitude,
                "longitude": longitude,
                "village": village,
                "locality": locality,
                "district": district,
                "state": state,
                "country": country,
                "display_name": formatted_address or None,
                "formatted_address": formatted_address,
                "source": "google_maps",
                "data_status": "LIVE",
            }

        except httpx.TimeoutException:
            return _manual_result(
                "Geocoding service timed out. Please enter village manually.",
                latitude,
                longitude,
            )
        except Exception:
            return _manual_result(
                "Geocoding service unavailable. Please enter village manually.",
                latitude,
                longitude,
            )


location_service = LocationService()
