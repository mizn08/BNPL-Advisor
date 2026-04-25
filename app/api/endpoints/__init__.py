"""API endpoints module"""
from .health import router as health_router
from .sme import router as sme_router
from .advisor import router as advisor_router
from .dashboard import router as dashboard_router

__all__ = [
    "health_router",
    "sme_router",
    "advisor_router",
    "dashboard_router",
]
