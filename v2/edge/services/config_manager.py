"""
Configuration handling service for edge node v2.
Manages loading, validation, and hot-reloading of configuration.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Camera configuration."""
    resolution: tuple[int, int] = (1920, 1080)
    capture_interval: float = 5.0


@dataclass
class InferenceConfig:
    """Inference configuration."""
    model_path: str = "yolov8m.pt"
    device: str = "cpu"
    confidence_threshold: float = 0.5


@dataclass
class OccupancyConfig:
    """Occupancy processor configuration."""
    slots_config_path: str = "calibration/fass_slots_v1.json"
    debounce_seconds: float = 3.0
    enter_threshold: float = 0.6
    exit_threshold: float = 0.4


@dataclass
class ServerConfig:
    """Server configuration."""
    url: str = "http://localhost:8000"
    timeout: float = 10.0


@dataclass
class MQTTConfig:
    """MQTT configuration."""
    host: str = "localhost"
    port: int = 1883


@dataclass
class HealthConfig:
    """Health monitoring configuration."""
    report_interval: float = 15.0


@dataclass
class BufferConfig:
    """Buffer configuration."""
    db_path: str = "stats_buffer.db"
    max_size_mb: int = 100


@dataclass
class AppConfig:
    """Complete application configuration."""
    node_id: str = "fass-edge-01"
    camera: CameraConfig = field(default_factory=CameraConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    occupancy: OccupancyConfig = field(default_factory=OccupancyConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    buffer: BufferConfig = field(default_factory=BufferConfig)


class ConfigManager:
    """Manages application configuration with hot-reload support."""

    def __init__(self, config_path: str = "configs/settings.json"):
        self.config_path = Path(config_path)
        self._config: Optional[AppConfig] = None
        self._callbacks: list[Callable[[AppConfig], None]] = []
        self._raw_config: Dict[str, Any] = {}

    def load(self) -> AppConfig:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    self._raw_config = json.load(f)
                self._config = self._parse_config(self._raw_config)
                logger.info(f"Configuration loaded from {self.config_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file: {e}")
                self._config = AppConfig()
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self._config = AppConfig()
        else:
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self._config = AppConfig()

        return self._config

    def _parse_config(self, raw: Dict[str, Any]) -> AppConfig:
        """Parse raw config dictionary into AppConfig."""
        camera_raw = raw.get('camera', {})
        inference_raw = raw.get('inference', {})
        occupancy_raw = raw.get('occupancy', {})
        server_raw = raw.get('server', {})
        mqtt_raw = raw.get('mqtt', {})
        health_raw = raw.get('health', {})
        buffer_raw = raw.get('buffer', {})

        return AppConfig(
            node_id=raw.get('node_id', 'fass-edge-01'),
            camera=CameraConfig(
                resolution=tuple(camera_raw.get('resolution', [1920, 1080])),
                capture_interval=camera_raw.get('capture_interval', 5.0)
            ),
            inference=InferenceConfig(
                model_path=inference_raw.get('model_path', 'yolov8m.pt'),
                device=inference_raw.get('device', 'cpu'),
                confidence_threshold=inference_raw.get('confidence_threshold', 0.5)
            ),
            occupancy=OccupancyConfig(
                slots_config_path=occupancy_raw.get('slots_config_path', 'calibration/fass_slots_v1.json'),
                debounce_seconds=occupancy_raw.get('debounce_seconds', 3.0),
                enter_threshold=occupancy_raw.get('enter_threshold', 0.6),
                exit_threshold=occupancy_raw.get('exit_threshold', 0.4)
            ),
            server=ServerConfig(
                url=server_raw.get('url', 'http://localhost:8000'),
                timeout=server_raw.get('timeout', 10.0)
            ),
            mqtt=MQTTConfig(
                host=mqtt_raw.get('host', 'localhost'),
                port=mqtt_raw.get('port', 1883)
            ),
            health=HealthConfig(
                report_interval=health_raw.get('report_interval', 15.0)
            ),
            buffer=BufferConfig(
                db_path=buffer_raw.get('db_path', 'stats_buffer.db'),
                max_size_mb=buffer_raw.get('max_size_mb', 100)
            )
        )

    def get_config(self) -> AppConfig:
        """Get current configuration."""
        if self._config is None:
            return self.load()
        return self._config

    def reload(self) -> AppConfig:
        """Reload configuration from file and notify callbacks."""
        old_config = self._config
        new_config = self.load()

        if old_config != new_config:
            logger.info("Configuration changed, notifying callbacks")
            for callback in self._callbacks:
                try:
                    callback(new_config)
                except Exception as e:
                    logger.error(f"Config callback error: {e}")

        return new_config

    def add_reload_callback(self, callback: Callable[[AppConfig], None]):
        """Add callback to be called when config is reloaded."""
        self._callbacks.append(callback)

    def get_api_key(self) -> str:
        """Get API key from environment."""
        return os.getenv('API_KEY', '')

    def get_mqtt_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Get MQTT credentials from environment."""
        return os.getenv('MQTT_USER'), os.getenv('MQTT_PASS')

    def save(self, config: AppConfig):
        """Save configuration to file."""
        raw = {
            'node_id': config.node_id,
            'camera': {
                'resolution': list(config.camera.resolution),
                'capture_interval': config.camera.capture_interval
            },
            'inference': {
                'model_path': config.inference.model_path,
                'device': config.inference.device,
                'confidence_threshold': config.inference.confidence_threshold
            },
            'occupancy': {
                'slots_config_path': config.occupancy.slots_config_path,
                'debounce_seconds': config.occupancy.debounce_seconds,
                'enter_threshold': config.occupancy.enter_threshold,
                'exit_threshold': config.occupancy.exit_threshold
            },
            'server': {
                'url': config.server.url,
                'timeout': config.server.timeout
            },
            'mqtt': {
                'host': config.mqtt.host,
                'port': config.mqtt.port
            },
            'health': {
                'report_interval': config.health.report_interval
            },
            'buffer': {
                'db_path': config.buffer.db_path,
                'max_size_mb': config.buffer.max_size_mb
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(raw, f, indent=2)

        self._config = config
        self._raw_config = raw
        logger.info(f"Configuration saved to {self.config_path}")
