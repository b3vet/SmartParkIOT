"""
Application configuration using Pydantic Settings.
Server v2 - receives processed events from edge nodes.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Database (v2 namespace)
    database_url: str = "postgresql://smartpark:password@localhost:5432/smartpark_v2"

    # MQTT (v2 ports)
    mqtt_host: str = "localhost"
    mqtt_port: int = 1884

    # API Security
    api_key: str = "development-key"

    # Slots (for validation/reference only in v2)
    slots_config_path: str = "calibration/fass_slots_v1.json"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
