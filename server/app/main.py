"""
FastAPI application for SmartPark server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import frames, slots, health
from app.services.inference import InferenceEngine
from app.services.mqtt_publisher import MQTTPublisher
from app.models.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting SmartPark Server...")

    # Initialize database
    init_db()

    # Initialize inference engine
    app.state.inference_engine = InferenceEngine(
        model_path=settings.model_path,
        device=settings.inference_device
    )

    # Initialize MQTT publisher
    app.state.mqtt_publisher = MQTTPublisher(
        host=settings.mqtt_host,
        port=settings.mqtt_port
    )
    app.state.mqtt_publisher.connect()

    logger.info("SmartPark Server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down SmartPark Server...")
    app.state.mqtt_publisher.disconnect()


app = FastAPI(
    title="SmartPark API",
    description="FASS Parking Lot Occupancy Detection API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(frames.router, prefix="/api/v1/frames", tags=["frames"])
app.include_router(slots.router, prefix="/api/v1/slots", tags=["slots"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SmartPark API",
        "version": "1.0.0",
        "status": "running"
    }
