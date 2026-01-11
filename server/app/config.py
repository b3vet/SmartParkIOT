"""
Application configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://smartpark:password@localhost:5432/smartpark"

    # MQTT
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    # API Security
    api_key: str = "development-key"

    # Inference
    model_path: str = "ml/yolov8l.pt"
    inference_device: str = "cpu"  # or "cuda:0" for GPU
    confidence_threshold: float = 0.5

    # Slots
    slots_config_path: str = "calibration/fass_slots_v1.json"

    # Debounce
    debounce_seconds: float = 3.0
    enter_threshold: float = 0.6
    exit_threshold: float = 0.4

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
