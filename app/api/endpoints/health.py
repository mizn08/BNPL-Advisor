"""
Health check endpoint
"""
from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings
from app.schemas import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check if the API is running and database is connected",
)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint
    
    Returns:
        HealthCheckResponse: API health status
    """
    return HealthCheckResponse(
        status="healthy",
        version=settings.APP_VERSION,
        database="connected",
        timestamp=datetime.utcnow(),
    )
