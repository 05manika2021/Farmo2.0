from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.database import engine, Base, SessionLocal
from app.db.models import Market, MarketPrice, PriceHistory
from app.core.config import settings


def init_db():
    Base.metadata.create_all(bind=engine)


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
