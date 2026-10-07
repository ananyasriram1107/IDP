from fastapi import APIRouter

from app.models.health import HealthStatus
from app.services.health_service import check_health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    return await check_health()
