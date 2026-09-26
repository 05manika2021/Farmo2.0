from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "Farmo Backend"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./farmo.db"

    SECRET_KEY: str = "farmo-dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440

    DEMO_MODE: bool = True
    DEMO_OTP: str = "123456"
    OTP_EXPIRY_SECONDS: int = 300
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    TWOFACTOR_API_KEY: Optional[str] = None
    TWOFACTOR_SMS_TEMPLATE: str = "OTP"

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_VERIFY_SERVICE_SID: Optional[str] = None

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_TTS_MODEL: str = "gemini-3.8-flash-lite-tts"

    GOOGLE_MAPS_API_KEY: Optional[str] = None

    MAPTILER_API_KEY: Optional[str] = None

    WEATHER_API_KEY: Optional[str] = None

    TRANSPORT_RATE_PER_KM: float = 15.0
    TRANSPORT_MIN_COST: float = 50.0

    CORS_ORIGINS: str = "http://localhost:3000"

    STT_PROVIDER: Optional[str] = None
    TTS_PROVIDER: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_TTS_MODEL: str = "tts-1"
    STT_LANGUAGE: str = "hi"

    GROQ_API_KEY: Optional[str] = None
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"


settings = Settings()
