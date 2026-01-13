"""
FastAPI application for SmartPark Server v2.
Receives processed events from edge nodes - no local inference.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import events, slots, health
from app.services.mqtt_publisher import MQTTPublisher
from app.models.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting SmartPark Server v2...")

    # Initialize database
    init_db()

    # Initialize MQTT publisher
    app.state.mqtt_publisher = MQTTPublisher(
        host=settings.mqtt_host,
        port=settings.mqtt_port
    )
    app.state.mqtt_publisher.connect()

    logger.info("SmartPark Server v2 started successfully")
    logger.info("Note: v2 receives processed events from edge nodes (no local inference)")

    yield

    # Shutdown
    logger.info("Shutting down SmartPark Server v2...")
    app.state.mqtt_publisher.disconnect()


app = FastAPI(
    title="SmartPark API v2",
    description="FASS Parking Lot Occupancy Detection API - Edge Inference Version",
    version="2.0.0",
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
# v2 endpoints for receiving events from edge
app.include_router(events.router, prefix="/api/v2", tags=["events"])

# Query endpoints (same paths as v1 for compatibility)
app.include_router(slots.router, prefix="/api/v1/slots", tags=["slots"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])

# Also expose under v2 prefix
app.include_router(slots.router, prefix="/api/v2/slots", tags=["slots-v2"])
app.include_router(health.router, prefix="/api/v2/health", tags=["health-v2"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SmartPark API",
        "version": "2.0.0",
        "status": "running",
        "architecture": "edge-inference",
        "description": "Server receives processed events from edge nodes"
    }
