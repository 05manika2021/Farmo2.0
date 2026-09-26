from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "farmo-backend",
        "version": settings.APP_VERSION,
    }
