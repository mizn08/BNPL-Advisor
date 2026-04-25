"""
Main FastAPI application
Z.AI - Economic Empowerment & Decision Intelligence
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.core.config import settings
from app.db import engine, Base
from app.models import (
    CompanyProfile,
    Transaction,
    FinancialDocument,
    BNPLRecommendation,
    AnalysisReport,
)
from app.api.endpoints import (
    health_router,
    sme_router,
    advisor_router,
    dashboard_router,
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug: {settings.DEBUG}")
    
    # Create database tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="BNPL Advisor for SMEs backend powered by FastAPI and Z.AI GLM",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(sme_router, prefix=settings.API_PREFIX)
app.include_router(advisor_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)

import os

# Check if it's flattened on GitHub (2 folders up)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

# If not there, fall back to the original local path (3 folders up)
if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"

# API info endpoint (available at /api/v1/info for debugging)
@app.get("/api/info", tags=["root"])
async def api_info():
    """API info endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX,
    }

# Serve frontend - index.html at root
@app.get("/", tags=["frontend"])
async def serve_frontend():
    """Serve the single-page SME Advisor frontend."""
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not built yet")
    return FileResponse(index_file)

# Mount static files AFTER explicit routes so they don't override API paths
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
