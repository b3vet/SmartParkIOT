"""
Main entry point for SmartPark edge node.
"""

import os
import sys
import json
import signal
import logging
from pathlib import Path

from dotenv import load_dotenv

from services.capture import FrameCapture
from services.uploader import FrameUploader
from services.health import HealthMonitor
from services.mqtt_client import MQTTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/smartpark/edge.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SmartParkEdge:
    """Main application controller."""

    def __init__(self, config_path: str = "configs/settings.json"):
        self.config = self._load_config(config_path)
        self.running = False

        # Initialize services
        self.capture = FrameCapture(
            resolution=tuple(self.config['camera']['resolution']),
            capture_interval=self.config['camera']['capture_interval'],
            jpeg_quality=self.config['camera']['jpeg_quality']
        )

        self.uploader = FrameUploader(
            server_url=self.config['server']['url'],
            api_key=os.getenv('API_KEY', ''),
            timeout=self.config['server']['timeout']
        )

        self.health = HealthMonitor(
            report_interval=self.config['health']['report_interval']
        )

        self.mqtt = MQTTClient(
            broker_host=self.config['mqtt']['host'],
            broker_port=self.config['mqtt']['port'],
            node_id=self.config['node_id'],
            username=os.getenv('MQTT_USER'),
            password=os.getenv('MQTT_PASS')
        )

    def _load_config(self, path: str) -> dict:
        """Load configuration from JSON file."""
        config_file = Path(path)
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        else:
            logger.warning(f"Config file not found: {path}, using defaults")
            return self._default_config()

    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            'node_id': 'fass-edge-01',
            'camera': {
                'resolution': [1920, 1080],
                'capture_interval': 1.5,
                'jpeg_quality': 85
            },
            'server': {
                'url': 'http://server-ip:8000',
                'timeout': 10.0
            },
            'mqtt': {
                'host': 'server-ip',
                'port': 1883
            },
            'health': {
                'report_interval': 15.0
            }
        }

    def start(self):
        """Start all services."""
        logger.info("Starting SmartPark Edge Node...")
        self.running = True

        # Initialize camera
        if not self.capture.initialize():
            logger.error("Failed to initialize camera, exiting")
            sys.exit(1)

        # Start capture
        self.capture.start_continuous_capture()

        # Start uploader
        self.uploader.start_upload_worker(self.capture.frame_queue)

        # Connect MQTT
        self.mqtt.connect()

        # Start health monitor with MQTT publishing
        self.health.add_callback(self.mqtt.publish_health)
        self.health.add_callback(self._log_health)
        self.health.start()

        # Set config callback
        self.mqtt.set_config_callback(self._handle_config_update)

        logger.info("SmartPark Edge Node started successfully")

    def _log_health(self, metrics: dict):
        """Log health metrics locally."""
        logger.info(f"Health: CPU={metrics['cpu_percent']}%, "
                   f"Temp={metrics['cpu_temp_c']}C, "
                   f"WiFi={metrics['wifi_rssi_dbm']}dBm")

    def _handle_config_update(self, config: dict):
        """Handle configuration update from server."""
        logger.info(f"Received config update: {config}")
        # Apply config updates (capture interval, etc.)
        if 'capture_interval' in config:
            self.capture.capture_interval = config['capture_interval']
            logger.info(f"Updated capture interval to {config['capture_interval']}s")

    def stop(self):
        """Stop all services."""
        logger.info("Stopping SmartPark Edge Node...")
        self.running = False

        self.health.stop()
        self.uploader.stop()
        self.capture.stop()
        self.mqtt.disconnect()

        logger.info("SmartPark Edge Node stopped")


def main():
    """Main entry point."""
    # Create log directory
    Path('/var/log/smartpark').mkdir(parents=True, exist_ok=True)

    app = SmartParkEdge()

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start application
    app.start()

    # Keep running
    try:
        while app.running:
            signal.pause()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
