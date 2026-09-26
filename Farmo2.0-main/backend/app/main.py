import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.seed import init_db, seed_demo_data
from app.api.routes import (
    health, auth, farmers, location, markets,
    prices, profit, recommendations, chat, voice, weather,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# httpx logs full request URLs at INFO, which for MapTiler / 2Factor /
# OpenAI includes the API key (and OTP) as a query/path segment.
for _noisy in ("httpx", "httpcore", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logger = logging.getLogger("farmo")

SECRET_SETTING_NAMES = (
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "TWOFACTOR_API_KEY",
    "MAPTILER_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "WEATHER_API_KEY",
)


def redact_secrets(text: str) -> str:
    """Replace any configured credential found in text with ***."""
    for name in SECRET_SETTING_NAMES:
        secret = getattr(settings, name, None)
        if isinstance(secret, str) and len(secret) >= 8:
            text = text.replace(secret, "***")
    return text

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Farmo - AI-native agricultural market intelligence platform for Indian farmers",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception: %s",
        redact_secrets("".join(traceback.format_exception(exc))),
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            },
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found.",
            },
        },
    )


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Farmo backend...")
    init_db()
    logger.info("Database initialized.")
    seed_demo_data()
    logger.info("Demo data seeded (if empty).")
    logger.info(f"Demo mode: {settings.DEMO_MODE}")
    logger.info(f"Gemini configured: {bool(settings.GEMINI_API_KEY)}")
    logger.info(f"Google Maps configured: {bool(settings.GOOGLE_MAPS_API_KEY)}")


API_V1 = settings.API_V1_PREFIX

app.include_router(health.router, prefix=API_V1, tags=["Health"])
app.include_router(auth.router, prefix=f"{API_V1}/auth", tags=["Authentication"])
app.include_router(farmers.router, prefix=f"{API_V1}/farmers", tags=["Farmers"])
app.include_router(location.router, prefix=f"{API_V1}/location", tags=["Location"])
app.include_router(markets.router, prefix=f"{API_V1}/markets", tags=["Markets"])
app.include_router(prices.router, prefix=f"{API_V1}/prices", tags=["Prices"])
app.include_router(profit.router, prefix=f"{API_V1}/profit", tags=["Profit"])
app.include_router(recommendations.router, prefix=f"{API_V1}/recommendations", tags=["Recommendations"])
app.include_router(chat.router, prefix=f"{API_V1}/chat", tags=["Chat"])
app.include_router(weather.router, prefix=f"{API_V1}/weather", tags=["Weather"])
app.include_router(voice.router, prefix=f"{API_V1}/voice", tags=["Voice"])
