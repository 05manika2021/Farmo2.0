from datetime import datetime, timedelta, timezone
import zlib
from sqlalchemy.orm import Session
from app.db.database import engine, Base, SessionLocal
from app.db.models import Market, MarketPrice, PriceHistory
from app.core.config import settings


def init_db():
    Base.metadata.create_all(bind=engine)


def _stable_variation(key: str) -> int:
    """Deterministic variation (unlike hash(), which is salted per process)."""
    return zlib.crc32(key.encode("utf-8")) % 200 - 100


# Crops the UI actually offers (graph/mandi/home tabs) that are not part of
# the original seed_demo_data() set. Base prices are typical Indian mandi
# levels and are DEMO ONLY - never presented as live prices.
DEMO_UI_CROP_BASE_PRICES = {
    "wheat": 2450,
    "cotton": 7200,
    "soybean": 4600,
    "maize": 2100,
}

DEMO_UI_CROP_OFFSETS = {
    "Indore Mandi": {"wheat": 0, "cotton": 0, "soybean": 0, "maize": 0},
    "Dewas Mandi": {"wheat": -35, "cotton": -120, "soybean": -60, "maize": -40},
    "Ujjain Mandi": {"wheat": 25, "cotton": 80, "soybean": 45, "maize": 30},
    "Bhopal Mandi": {"wheat": -60, "cotton": -200, "soybean": -90, "maize": -50},
    "Nashik Mandi": {"wheat": 90, "cotton": 250, "soybean": 130, "maize": 70},
    "Pune Mandi": {"wheat": 140, "cotton": 310, "soybean": 165, "maize": 95},
}

DEMO_HISTORY_DAYS = 90


def seed_ui_demo_crops():
    """Make sure every crop shown in the UI has DEMO prices + long history.

    Idempotent: only seeds (market, crop) pairs that have no MarketPrice yet.
    Writes 90 days of PriceHistory so the 7D / 30D / 90D graph tabs all have
    real points. Every record is marked data_status=DEMO / DEMO_SEED_DATA.
    """
    db = SessionLocal()
    try:
        markets = db.query(Market).all()
        if not markets:
            return

        now = datetime.now(timezone.utc)
        seeded = 0

        for market in markets:
            offsets = DEMO_UI_CROP_OFFSETS.get(market.name, {})
            for crop_name, base_price in DEMO_UI_CROP_BASE_PRICES.items():
                already = (
                    db.query(MarketPrice)
                    .filter(
                        MarketPrice.market_id == market.id,
                        MarketPrice.crop_name == crop_name,
                    )
                    .first()
                )
                if already:
                    continue

                offset = offsets.get(crop_name, 0)
                for days_ago in range(DEMO_HISTORY_DAYS, -1, -1):
                    date = now - timedelta(days=days_ago)
                    variation = (days_ago % 7 - 3) * 25 + _stable_variation(
                        f"{market.name}{crop_name}{days_ago}"
                    )
                    price = float(max(base_price + offset + variation, 500))

                    if days_ago == 0:
                        db.add(
                            MarketPrice(
                                market_id=market.id,
                                crop_name=crop_name,
                                price_per_quintal=price,
                                price_unit="INR/quintal",
                                price_date=date,
                                source="DEMO_SEED_DATA",
                                source_updated_at=date,
                                data_status="DEMO",
                            )
                        )

                    db.add(
                        PriceHistory(
                            market_id=market.id,
                            crop_name=crop_name,
                            price_per_quintal=price,
                            price_date=date,
                            source="DEMO_SEED_DATA",
                        )
                    )
                seeded += 1

        backfilled = _backfill_histories(db, markets, now)

        if seeded or backfilled:
            db.commit()
            print(
                f"Seeded DEMO prices for {seeded} (market, crop) pairs and "
                f"backfilled {backfilled} history rows "
                f"({DEMO_HISTORY_DAYS}-day history)."
            )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _backfill_histories(db: Session, markets: list, now: datetime) -> int:
    """Give every (market, crop) that has a current price a full 90-day series.

    The original demo seed only wrote ~31 rows and left gaps, so the 7D graph
    could come back with a single point. Only missing dates are inserted -
    existing rows are never rewritten.
    """
    market_names = {m.id: m.name for m in markets}
    combos = (
        db.query(
            MarketPrice.market_id,
            MarketPrice.crop_name,
            MarketPrice.price_per_quintal,
        )
        .distinct()
        .all()
    )

    added = 0
    for market_id, crop_name, current_price in combos:
        existing = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.market_id == market_id,
                PriceHistory.crop_name == crop_name,
            )
            .all()
        )
        have = {row.price_date.date() for row in existing}
        market_name = market_names.get(market_id, f"market-{market_id}")

        for days_ago in range(DEMO_HISTORY_DAYS, -1, -1):
            day = (now - timedelta(days=days_ago)).date()
            if day in have:
                continue

            if days_ago == 0:
                price = float(current_price)
            else:
                variation = (days_ago % 7 - 3) * 25 + _stable_variation(
                    f"{market_name}{crop_name}{days_ago}"
                )
                price = float(max((current_price or 0) + variation, 500))

            db.add(
                PriceHistory(
                    market_id=market_id,
                    crop_name=crop_name,
                    price_per_quintal=price,
                    price_date=now - timedelta(days=days_ago),
                    source="DEMO_SEED_DATA",
                )
            )
            added += 1

    return added



def seed_demo_data():
    db = SessionLocal()
    try:
        existing = db.query(Market).count()
        if existing > 0:
            return

        markets = [
            Market(
                name="Indore Mandi",
                state="Madhya Pradesh",
                district="Indore",
                latitude=22.7196,
                longitude=75.8577,
                location_name="Indore, Madhya Pradesh",
                is_active=True,
            ),
            Market(
                name="Dewas Mandi",
                state="Madhya Pradesh",
                district="Dewas",
                latitude=22.9676,
                longitude=76.0534,
                location_name="Dewas, Madhya Pradesh",
                is_active=True,
            ),
            Market(
                name="Ujjain Mandi",
                state="Madhya Pradesh",
                district="Ujjain",
                latitude=23.1765,
                longitude=75.7885,
                location_name="Ujjain, Madhya Pradesh",
                is_active=True,
            ),
            Market(
                name="Bhopal Mandi",
                state="Madhya Pradesh",
                district="Bhopal",
                latitude=23.2599,
                longitude=77.4126,
                location_name="Bhopal, Madhya Pradesh",
                is_active=True,
            ),
            Market(
                name="Nashik Mandi",
                state="Maharashtra",
                district="Nashik",
                latitude=19.9975,
                longitude=73.7898,
                location_name="Nashik, Maharashtra",
                is_active=True,
            ),
            Market(
                name="Pune Mandi",
                state="Maharashtra",
                district="Pune",
                latitude=18.5204,
                longitude=73.8567,
                location_name="Pune, Maharashtra",
                is_active=True,
            ),
        ]

        db.add_all(markets)
        db.flush()

        crops_base_prices = {
            "onion": 2500,
            "tomato": 3000,
            "potato": 1800,
        }

        market_price_offsets = {
            "Indore Mandi": {"onion": 0, "tomato": 100, "potato": -50},
            "Dewas Mandi": {"onion": -100, "tomato": -200, "potato": 50},
            "Ujjain Mandi": {"onion": 50, "tomato": 150, "potato": -100},
            "Bhopal Mandi": {"onion": -200, "tomato": 50, "potato": 100},
            "Nashik Mandi": {"onion": 300, "tomato": 400, "potato": 200},
            "Pune Mandi": {"onion": 150, "tomato": 350, "potato": 150},
        }

        now = datetime.now(timezone.utc)
        sources = ["DEMO_SEED_DATA"]

        for market in markets:
            offsets = market_price_offsets.get(market.name, {})
            for crop_name, base_price in crops_base_prices.items():
                offset = offsets.get(crop_name, 0)
                for days_ago in range(30, -1, -1):
                    date = now - timedelta(days=days_ago)
                    variation = (days_ago % 7 - 3) * 25 + (hash(f"{market.name}{crop_name}{days_ago}") % 200 - 100)
                    price = base_price + offset + variation
                    price = max(price, 500)

                    if days_ago == 0:
                        current_price = MarketPrice(
                            market_id=market.id,
                            crop_name=crop_name,
                            price_per_quintal=float(price),
                            price_unit="INR/quintal",
                            price_date=date,
                            source="DEMO_SEED_DATA",
                            source_updated_at=date,
                            data_status="DEMO",
                        )
                        db.add(current_price)

                    history = PriceHistory(
                        market_id=market.id,
                        crop_name=crop_name,
                        price_per_quintal=float(price),
                        price_date=date,
                        source="DEMO_SEED_DATA",
                    )
                    db.add(history)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
