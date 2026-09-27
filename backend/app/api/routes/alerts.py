from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.services.price_service import price_service
from app.services.market_service import market_service
from app.services.recommendation_service import recommendation_service
from app.services.weather_service import weather_service

router = APIRouter()

SUPPORTED_LANGUAGES = ("en", "hi", "pa", "gu", "mr", "bn")

# DEMO location - the same one the chat fallback uses when the app has no
# coordinates, so alerts stay answerable in DEMO_MODE.
DEMO_FALLBACK_LAT = 22.7196
DEMO_FALLBACK_LON = 75.8577

TITLES = {
    "weather": {
        "en": "Weather alert",
        "hi": "\u092e\u094c\u0938\u092e \u091a\u0947\u0924\u093e\u0935\u0928\u0940",
        "pa": "\u092e\u094c\u0938\u092e \u091a\u0947\u0924\u093e\u0935\u0928\u0940",
        "gu": "\u0939\u0935\u093e\u092e\u093e\u0928 \u091a\u0947\u0924\u0935\u0923\u0940",
        "mr": "\u0939\u0935\u093e\u092e\u093e\u0928 \u0938\u0942\u091a\u0928\u093e",
        "bn": "\u0986\u09ac\u09b9\u09be\u0993\u09df\u09be \u09b8\u09a4\u09b0\u09cd\u0915\u0924\u09be",
    },
    "market": {
        "en": "Market price alert",
        "hi": "\u092c\u093e\u091c\u093c\u093e\u0930 \u092d\u093e\u0935 \u091a\u0947\u0924\u093e\u0935\u0928\u0940",
        "pa": "\u092e\u0971\u0902\u0921\u0940 \u092d\u093e\u0905 \u091a\u0947\u0924\u093e\u0935\u0928\u0940",
        "gu": "\u092c\u091c\u093e\u0930 \u092d\u093e\u0935 \u091a\u0947\u0924\u0935\u0923\u0940",
        "mr": "\u092c\u093e\u091c\u093e\u0930 \u092d\u093e\u0935 \u0938\u0942\u091a\u0928\u093e",
        "bn": "\u09ac\u09be\u099c\u09be\u09b0 \u09a6\u09be\u09ae \u09b8\u09a4\u09b0\u09cd\u0915\u0924\u09be",
    },
    "sell": {
        "en": "Sell / Wait advice",
        "hi": "\u092c\u0947\u091a\u0947\u0902 / \u0930\u0941\u0915\u0947\u0902 \u0938\u0932\u093e\u0939",
        "pa": "\u0935\u0947\u091a\u094b / \u0930\u0941\u0915\u094b \u0938\u0932\u093e\u0939",
        "gu": "\u0935\u0947\u091a\u094b / \u0930\u093e\u0939\u094b \u0938\u0932\u093e\u0939",
        "mr": "\u0935\u093f\u0915\u093e / \u0925\u093e\u0902\u092c\u093e \u0938\u0932\u094d\u0932\u093e",
        "bn": "\u09ac\u09bf\u0995\u09cd\u09b0\u09bf / \u0985\u09aa\u09c7\u0915\u09cd\u09b7\u09be \u09aa\u09b0\u09be\u09ae\u09b0\u09cd\u09a4",
    },
}

BODIES = {
    "weather": {
        "en": "DEMO WEATHER: rain chance {rain}% today, {condition}. Keep covered produce dry.",
        "hi": "DEMO WEATHER: \u0906\u091c \u092c\u093e\u0930\u093f\u0936 \u0915\u0940 \u0938\u0902\u092d\u093e\u0935\u0928\u093e {rain}% \u0939\u0948, {condition}. \u092b\u0938\u0932 \u0922\u0915\u0915\u0930 \u0930\u0916\u0947\u0902\u0964",
        "pa": "DEMO WEATHER: \u0a05\u0a71\u0a1c \u0a2e\u0a40\u0a02\u0a39 \u0a26\u0a40 \u0a38\u0a70\u0a2d\u0a3e\u0a35\u0a28\u0a3e {rain}% \u0a39\u0a48, {condition}. \u0a2b\u0a3c\u0a38\u0a32 \u0a22\u0a47\u0a16 \u0a15\u0a47 \u0a30\u0a39\u0a4b\u0964",
        "gu": "DEMO WEATHER: \u0a06\u0a1c\u0a47 \u0a35\u0a30\u0a38\u0a3e\u0a26\u0a40 \u0a36\u0a15\u0a4d\u092f\u0a24\u0a3e {rain}% \u0a1b\u0a47, {condition}. \u0aaa\u0a3e\u0a15 \u0a22\u0a3e\u0a02\u0a15\u0a40 \u0a30\u0a3e\u0a16\u0a4b.",
        "mr": "DEMO WEATHER: \u0906\u091c \u092a\u093e\u090a\u0938\u093e\u091a\u0940 \u0936\u0915\u094d\u092f\u0924\u093e {rain}% \u0906\u0939\u0947, {condition}. \u092a\u0940\u0915 \u091d\u093e\u0915\u0942\u0928 \u0920\u0947\u0935\u093e \u0930\u093e\u0939\u093e\u0964",
        "bn": "DEMO WEATHER: \u0986\u099c \u09ac\u09c3\u09b7\u09cd\u099f\u09bf\u09b0 \u09b8\u09ae\u09cd\u09ad\u09be\u09ac\u09a8\u09be {rain}% \u09b9\u09df, {condition}. \u09ab\u09b8\u09b2 \u099d\u09c7\u0995\u09c7 \u09b0\u09be\u0996\u09c1\u09a8\u0964",
    },
    "market_up": {
        "en": "{market}: {crop} rose {pct}% in 7 days, now \u20b9{price} per quintal.",
        "hi": "{market}: {crop} \u0915\u093e \u092d\u093e\u0935 7 \u0926\u093f\u0928\u094b\u0902 \u092e\u0947\u0902 {pct}% \u092c\u0922\u0915\u0930 \u0905\u092c \u20b9{price} \u092a\u094d\u0930\u0924\u093f \u0915\u094d\u0935\u093f\u0902\u091f\u0932 \u0939\u094b \u0917\u092f\u093e\u0964",
        "pa": "{market}: {crop} \u0a26\u0a3e 7 \u0a26\u0a3f\u0a28\u0a3e\u0a02 \u0a35\u0a3f\u0a71\u0a1a {pct}% \u0a35\u0a27\u0a4d\u200d\u0a17\u0a3c\u0a3f\u0a06, \u0a39\u0a41\u0a71 \u0a17\u0a47 \u20b9{price} \u0a2a\u0a4d\u0a30\u0a24\u0a40 \u0a15\u0a4d\u0a35\u0a3f\u0a71\u0a02\u0a1f\u0a32\u0964",
        "gu": "{market}: {crop} \u0a28\u0a3e 7 \u0a26\u0a3f\u0a28\u0a4b\u0a02 \u0a2e\u0a3e\u0a02 {pct}% \u0a35\u0a27\u0a4d\u0a17\u0a4d\u0a2f\u0a41\u0a02, \u0a39\u0a2e\u0a23\u0a47 \u20b9{price} \u0a2a\u0a4d\u0a30\u0a24\u0a40 \u0a15\u0a4d\u0a35\u0a3f\u0a7e\u0a1f\u0a32.",
        "mr": "{market}: {crop} \u091a\u094d\u092f\u093e 7 \u0926\u093f\u0935\u0938\u093e\u092d\u093e\u0924 {pct}% \u0935\u093e\u0921\u0932\u0947\u0964 \u0906\u0924\u093e \u20b9{price} \u092a\u094d\u0930\u0924\u0940 \u0915\u094d\u0935\u093f\u0902\u091f\u0932\u093e.",
        "bn": "{market}: {crop} \u09b0 \u09ad\u09be\u09ac 7 \u09a6\u09bf\u09a8 \u09ae\u09bf\u09df {pct}% \u09ac\u09be\u0993\u09b2\u09cb, \u098f\u0996\u09a8 \u20b9{price} \u09aa\u09cd\u09b0\u09a4\u09bf \u0995\u09cd\u09ac\u09bf\u099f\u09be\u09b2\u0964",
    },
    "market_down": {
        "en": "{market}: {crop} fell {pct}% in 7 days, now \u20b9{price} per quintal.",
        "hi": "{market}: {crop} \u0915\u093e \u092d\u093e\u0935 7 \u0926\u093f\u0928\u094b\u0902 \u092e\u0947\u0902 {pct}% \u0917\u093f\u0930 \u0917\u092f\u093e, \u0905\u092c \u20b9{price} \u092a\u094d\u0930\u0924\u093f \u0915\u094d\u0935\u093f\u0902\u091f\u0932 \u0939\u094b \u0917\u092f\u093e\u0964",
        "pa": "{market}: {crop} \u0a26\u0a3e 7 \u0a26\u0a3f\u0a28\u0a3e\u0a02 \u0a35\u0a3f\u0a71\u0a1a {pct}% \u0a18\u0a1f\u0a17\u0a40\u0a06, \u0a39\u0a41\u0a71 \u0a17\u0a47 \u20b9{price} \u0a2a\u0a4d\u0a30\u0a24\u0a40 \u0a15\u0a4d\u0a35\u0a3f\u0a71\u0a02\u0a1f\u0a32\u0964",
        "gu": "{market}: {crop} \u0a28\u0a3e 7 \u0a26\u0a3f\u0a28\u0a4b\u0a02 \u0a2e\u0a3e\u0a02 {pct}% \u0a18\u0a1f\u0a4d\u0a2f\u0a41\u0a02, \u0a39\u0a2e\u0a23\u0a47 \u20b9{price} \u0a2a\u0a4d\u0a30\u0a24\u0a40 \u0a15\u0a4d\u0a35\u0a3f\u0a7e\u0a1f\u0a32.",
        "mr": "{market}: {crop} \u091a\u094d\u092f\u093e 7 \u0926\u093f\u0935\u0938\u093e\u092d\u093e\u0924 {pct}% \u0916\u093e\u0932\u0932\u0947\u0964 \u0906\u0924\u093e \u20b9{price} \u092a\u094d\u0930\u0924\u0940 \u0915\u094d\u0935\u093f\u0902\u091f\u0932\u093e.",
        "bn": "{market}: {crop} \u09b0 \u09ad\u09be\u09ac 7 \u09a6\u09bf\u09a8 \u09ae\u09bf\u09df {pct}% \u0995\u09ae\u09c7, \u098f\u0996\u09a8 \u20b9{price} \u09aa\u09cd\u09b0\u09a4\u09bf \u0995\u09cd\u09ac\u09bf\u099f\u09be\u09b2\u0964",
    },
    "market_flat": {
        "en": "{market}: {crop} is steady at \u20b9{price} per quintal over 7 days.",
        "hi": "{market}: {crop} \u0915\u093e \u092d\u093e\u0935 7 \u0926\u093f\u0928\u094b\u0902 \u0938\u0947 \u20b9{price} \u092a\u094d\u0930\u0924\u093f \u0915\u094d\u0935\u093f\u0902\u091f\u0932 \u0938\u094d\u0925\u093f\u0930 \u0939\u0948\u0964",
        "pa": "{market}: {crop} \u0a26\u0a3e 7 \u0a26\u0a3f\u0a28\u0a3e\u0a02 \u0a24\u0a4b\u0a02 \u20b9{price} \u0a2a\u0a4d\u0a30\u0a24\u0a40 \u0a15\u0a4d\u0a35\u0a3f\u0a71\u0a02\u0a1f\u0a32 \u0a38\u0a4d\u0a25\u0a3f\u0a30 \u0a39\u0a48\u0964",
        "gu": "{market}: {crop} \u0a28\u0a3e 7 \u0a26\u0a3f\u0a28\u0a4b\u0a02 \u0a38\u0a4d\u0a25\u0a3f\u0a30 \u20b9{price} \u0a2a\u0a4d\u0a30\u0a24\u0a40 \u0a15\u0a4d\u0a35\u0a3f\u0a7e\u0a1f\u0a32 \u0a39\u0a4b\u0a2f\u0a4b \u0a30\u0a39\u0a4d\u0a2f\u0a4b \u0a1b\u0a47.",
        "mr": "{market}: {crop} \u091a\u094d\u092f\u093e 7 \u0926\u093f\u0935\u0938\u093e\u092d\u093e\u0924 \u20b9{price} \u092a\u094d\u0930\u0924\u0940 \u0915\u094d\u0935\u093f\u0902\u091f\u0932\u093e \u0938\u094d\u0925\u093f\u0930 \u0906\u0939\u0947.",
        "bn": "{market}: {crop} \u09b0 \u09ad\u09be\u09ac 7 \u09a6\u09bf\u09a8 \u20b9{price} \u09aa\u09cd\u09b0\u09a4\u09bf \u0995\u09cd\u09ac\u09bf\u099f\u09be\u09ac\u09c7 \u09b8\u09cd\u09a5\u09bf\u09b0 \u09b0\u09be\u0996\u09be\u09df\u0964",
    },
    "sell": {
        "en": "{decision}: {market} gives the best net profit of \u20b9{net} for {qty} quintal of {crop}.",
        "hi": "{decision}: {market} \u092a\u0930 {qty} \u0915\u094d\u0935\u093f\u0902\u091f\u0932 {crop} \u0915\u0947 \u0932\u093f\u090f \u0938\u092c\u0938\u0947 \u0905\u091a\u094d\u091b\u093e \u0928\u093f\u0915\u094d\u0937 \u0932\u093e\u092d \u20b9{net} \u0939\u0948\u0964",
        "pa": "{decision}: {market} \u0a24\u0a47 {qty} \u0a15\u0a4d\u0a35\u0a3f\u0a02\u0a1f\u0a32 {crop} \u0a32\u0a08 \u0a38\u0a2d\u0a24\u0a4b \u0a05\u0a1a\u0a4d\u0a1b\u0a3e \u0a28\u0a3f\u0a15\u0a32 \u0a32\u0a3e\u0a2d \u20b9{net} \u0a26\u0a47\u0a02\u0a26\u0a3e \u0a39\u0a48\u0964",
        "gu": "{decision}: {market} \u0a24\u0a47 {qty} \u0a15\u0a4d\u0a35\u0a3f\u0a7e\u0a1f\u0a32 {crop} \u0aae\u0a3e\u0a1f\u0a47 \u0ab8\u0ac2\u0a2d\u0a24 \u0aa8\u0a2b \u0a32\u0a3e\u0a2d \u20b9{net} \u0a06\u0a6a\u0a47 \u0a1b\u0a47.",
        "mr": "{decision}: {market} \u0935\u0930 {qty} \u0915\u094d\u0935\u093f\u0902\u091f\u0932 {crop} \u0938\u093e\u0920\u0940 \u0938\u0930\u094d\u0935\u093e\u0927\u093f\u0915 \u0928\u0941\u0915\u0938\u0932 \u0932\u093e\u092d \u20b9{net} \u0926\u0947\u0924\u094b\u0964",
        "bn": "{decision}: {market} {qty} \u0995\u09cd\u09ac\u09bf\u099f\u09be\u09b2 {crop} \u09b0 \u099c\u09a8\u09cd\u09af \u09b8\u09cd\u09ac\u09be\u09a5\u09a4\u09ae \u09b2\u09be\u09ad \u09b8\u0982\u0995\u09c7 \u20b9{net}\u0964",
    },
}

DECISIONS = {
    "SELL_NOW": {
        "en": "Sell now",
        "hi": "\u0905\u092d\u0940 \u092c\u0947\u091a\u0947\u0902",
        "pa": "\u0939\u0941\u0971\u0928\u0947 \u0935\u0947\u091a\u094b",
        "gu": "\u0939\u09ae\u0923\u093e\u0902 \u0935\u0947\u091a\u094b",
        "mr": "\u0906\u0924\u094d\u0924\u093e \u0935\u093f\u0915\u093e",
        "bn": "\u098f\u0996\u09a8\u0987 \u09ac\u09bf\u0995\u09cd\u09b0\u09bf \u0995\u09b0\u09c1\u09a8",
    },
    "WAIT": {
        "en": "Wait",
        "hi": "\u0930\u0941\u0915\u0947\u0902",
        "pa": "\u0930\u0941\u0915\u094b",
        "gu": "\u0930\u093e\u0939\u094b",
        "mr": "\u0925\u093e\u0902\u092c\u093e",
        "bn": "\u0985\u09aa\u09c7\u0915\u09cd\u09b7\u09be \u0995\u09b0\u09c1\u09a8",
    },
    "SELL_IN_ANOTHER_MARKET": {
        "en": "Sell in another market",
        "hi": "\u0926\u0942\u0938\u0930\u0940 \u092e\u0902\u0921\u0940 \u092e\u0947\u0902 \u092c\u0947\u091a\u0947\u0902",
        "pa": "\u0926\u0942\u0938\u0930\u0940 \u092e\u0971\u0902\u0921\u0940 \u0a35\u0a3f\u0a71\u0a1a \u0a2c\u0a47\u0a1a\u0a4b",
        "gu": "\u092c\u0940\u091c\u0940 \u092c\u091c\u093e\u0930 \u092e\u093e\u0902 \u0935\u0947\u091a\u094b",
        "mr": "\u0926\u0942\u0938\u0930\u0940 \u092c\u093e\u091c\u093e\u0930\u093e\u0924 \u0935\u093f\u0915\u093e",
        "bn": "\u0985\u09a8\u09cd\u09af \u09ac\u09be\u099c\u09be\u09b0\u09c7 \u09ac\u09bf\u0995\u09cd\u09b0\u09bf \u0995\u09b0\u09c1\u09a8",
    },
}


def _lang(language: Optional[str]) -> str:
    value = (language or "en").lower()
    return value if value in SUPPORTED_LANGUAGES else "en"


def _pick(mapping: dict, key: str, language: str) -> str:
    row = mapping.get(key, {})
    return row.get(language) or row.get("en") or ""


def _alert(alert_id, atype, title, body, status, source, severity):
    return {
        "id": alert_id,
        "type": atype,
        "title": title,
        "body": body,
        "severity": severity,
        "data_status": status,
        "source": source,
    }


@router.get("")
async def get_alerts(
    language: Optional[str] = Query(default=None),
    crop: Optional[str] = Query(default="wheat"),
    quantity: float = Query(default=10, gt=0),
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
    db: Session = Depends(get_db),
):
    """Build the farmer's alerts from data Farmo already computes.

    Nothing new is stored and nothing is pushed: prices come from the DEMO
    price history, advice from the sell/wait engine, weather from the weather
    service. In DEMO_MODE the weather alert uses the deterministic demo
    dataset, so every alert is labelled DEMO.
    """
    lang = _lang(language)

    if latitude is None or longitude is None:
        latitude, longitude = DEMO_FALLBACK_LAT, DEMO_FALLBACK_LON

    alerts = []
    overall_status = "DEMO"

    # 1. Weather ----------------------------------------------------------------
    if settings.DEMO_MODE:
        weather = weather_service.get_demo_weather(latitude, longitude)
    else:
        weather = await weather_service.get_weather(latitude, longitude)

    if weather.get("temperature") is not None:
        rain = weather.get("rain_probability")
        rain = 0 if rain is None else int(rain)
        body = _pick(BODIES, "weather", lang).format(
            rain=rain,
            condition=weather.get("condition") or "Partly cloudy",
        )
        alerts.append(
            _alert(
                "weather",
                "weather",
                _pick(TITLES, "weather", lang),
                body,
                weather.get("data_status", "DEMO"),
                weather.get("source", "demo_weather"),
                "warning" if rain >= 50 else "info",
            )
        )
        if weather.get("data_status") != "DEMO":
            overall_status = weather.get("data_status", "DEMO")

    # 2. Market price trend ------------------------------------------------------
    market_name = None
    if crop:
        nearby = market_service.get_nearby_markets(
            latitude, longitude, 500.0, crop, db
        )
        with_data = [n for n in nearby if n.get("has_price")]
        if with_data:
            nearest = with_data[0]
            market_name = nearest["market"].name
            trend = price_service.get_price_trend(
                crop, nearest["market"].id, 7, db
            )
            history = trend.get("history") or []
            if len(history) >= 2:
                first = history[0]["price"]
                last = history[-1]["price"]
                pct = ((last - first) / first) * 100 if first else 0.0
                if pct > 1:
                    key = "market_up"
                elif pct < -1:
                    key = "market_down"
                else:
                    key = "market_flat"
                alerts.append(
                    _alert(
                        "market",
                        "market",
                        _pick(TITLES, "market", lang),
                        _pick(BODIES, key, lang).format(
                            market=market_name,
                            crop=crop.capitalize(),
                            pct=f"{abs(pct):.1f}",
                            price=f"{int(last)}",
                        ),
                        "DEMO",
                        "DEMO_SEED_DATA",
                        "info",
                    )
                )

    # 3. Sell / Wait -------------------------------------------------------------
    if crop:
        advice = recommendation_service.evaluate_sell_wait(
            crop=crop,
            quantity=quantity,
            quantity_unit="quintal",
            farmer_lat=latitude,
            farmer_lon=longitude,
            storage_available=True,
            db=db,
        )
        decision = advice.get("recommendation")
        if decision and advice.get("best_market_name"):
            alerts.append(
                _alert(
                    "sell",
                    "sell",
                    _pick(TITLES, "sell", lang),
                    _pick(BODIES, "sell", lang).format(
                        decision=_pick(DECISIONS, decision, lang),
                        market=advice["best_market_name"],
                        net=f"{int(advice.get('best_market_net_profit') or 0)}",
                        qty=f"{int(quantity)}",
                        crop=crop.capitalize(),
                    ),
                    "DEMO",
                    "DEMO_SEED_DATA",
                    "warning" if decision == "SELL_NOW" else "info",
                )
            )

    return {
        "alerts": alerts,
        "count": len(alerts),
        "language": lang,
        "data_status": overall_status,
    }
