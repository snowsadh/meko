from fastapi import APIRouter
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": True,
            "memory_configured": bool(settings.meko_product_api_key),
            "model_configured": bool(settings.openai_api_key)}
