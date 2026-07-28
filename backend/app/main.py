"""
Pulsecast API — Main Application

FastAPI application that serves the drought forecasting backend.
Seeds the database on startup, exposes REST endpoints for the frontend.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.services.seeder import seed_database
from app.routers import counties, forecast, evidence

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize DB and ingest NDMA data on startup."""
    logger.info("Starting Pulsecast API...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Ingest published NDMA county bulletins; no synthetic fallback is used.
    await seed_database()
    logger.info("NDMA bulletin ingestion complete")
    
    yield
    
    logger.info("Shutting down Pulsecast API")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Drought phase forecasting API for Kenya's counties. "
        "Uses NDMA's published data and thresholds to project VCI3M trends "
        "and detect threshold crossings weeks before they happen."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(counties.router)
app.include_router(forecast.router)
app.include_router(evidence.router)


@app.get("/")
async def root():
    """API root — health check."""
    return {
        "name": "Pulsecast API",
        "version": "1.0.0",
        "status": "running",
        "description": "Drought phase forecasting for Kenya's counties",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    from app.database import execute_query
    try:
        result = await execute_query("SELECT COUNT(*) as count FROM counties", fetchone=True)
        return {
            "status": "healthy",
            "counties_loaded": result["count"] if result else 0,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
