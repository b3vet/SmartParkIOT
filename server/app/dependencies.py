"""
Dependency injection for FastAPI application.
"""

from typing import Generator

from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import SessionLocal
from app.services.inference import InferenceEngine
from app.services.occupancy import OccupancyProcessor
from app.services.mqtt_publisher import MQTTPublisher


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Verify API key from request header."""
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return x_api_key


def get_inference_engine(request: Request) -> InferenceEngine:
    """Get inference engine from app state."""
    return request.app.state.inference_engine


def get_occupancy_processor(request: Request) -> OccupancyProcessor:
    """Get occupancy processor from app state."""
    return request.app.state.occupancy_processor


def get_mqtt_publisher(request: Request) -> MQTTPublisher:
    """Get MQTT publisher from app state."""
    return request.app.state.mqtt_publisher
