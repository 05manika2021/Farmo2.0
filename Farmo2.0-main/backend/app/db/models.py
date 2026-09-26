from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Index
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=True)
    language = Column(String(5), nullable=False, default="hi")
    village = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    crops = relationship("FarmerCrop", back_populates="farmer", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="farmer", cascade="all, delete-orphan")


class FarmerCrop(Base):
    __tablename__ = "farmer_crops"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_name = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    quantity_unit = Column(String(20), nullable=False, default="quintal")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    farmer = relationship("Farmer", back_populates="crops")

    __table_args__ = (Index("idx_farmer_crop", "farmer_id", "crop_name"),)


class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True)

    prices = relationship("MarketPrice", back_populates="market")
    price_history = relationship("PriceHistory", back_populates="market")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    crop_name = Column(String(100), nullable=False)
    price_per_quintal = Column(Float, nullable=False)
    price_unit = Column(String(20), nullable=False, default="INR/quintal")
    price_date = Column(DateTime, nullable=False)
    source = Column(String(200), nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    data_status = Column(String(20), nullable=False, default="DEMO")

    market = relationship("Market", back_populates="prices")

    __table_args__ = (
        Index("idx_market_crop_date", "market_id", "crop_name", "price_date"),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    crop_name = Column(String(100), nullable=False)
    price_per_quintal = Column(Float, nullable=False)
    price_date = Column(DateTime, nullable=False)
    source = Column(String(200), nullable=True)

    market = relationship("Market", back_populates="price_history")

    __table_args__ = (
        Index("idx_history_market_crop_date", "market_id", "crop_name", "price_date"),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_name = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    recommendation = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    farmer = relationship("Farmer", back_populates="recommendations")


class OTPRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(15), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
