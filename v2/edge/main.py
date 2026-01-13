"""
Main entry point for SmartPark Edge Node v2.
Runs inference locally on the Pi and sends processed stats to server.
"""

import os
import sys
import signal
import logging
import threading
import time
from pathlib import Path
from queue import Empty
from datetime import datetime, timezone

from dotenv import load_dotenv
from PIL import Image

from services.capture import FrameCapture
from services.inference import InferenceEngine
from services.occupancy import OccupancyProcessor
from services.stats_sender import StatsSender
from services.health import HealthMonitor
from services.mqtt_client import MQTTClient
from services.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/smartpark/edge-v2.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SmartParkEdgeV2:
    """Main application controller for edge node v2 with local inference."""

    def __init__(self, config_path: str = "configs/settings.json"):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load()
        self.running = False

        # Initialize services
        logger.info("Initializing services...")

        # Camera capture
        self.capture = FrameCapture(
            resolution=self.config.camera.resolution,
            capture_interval=self.config.camera.capture_interval
        )

        # Local inference engine (YOLOv8m)
        self.inference = InferenceEngine(
            model_path=self.config.inference.model_path,
            device=self.config.inference.device,
            confidence_threshold=self.config.inference.confidence_threshold
        )

        # Occupancy processor (pass capture resolution for polygon scaling)
        self.occupancy = OccupancyProcessor(
            slots_config_path=self.config.occupancy.slots_config_path,
            debounce_seconds=self.config.occupancy.debounce_seconds,
            enter_threshold=self.config.occupancy.enter_threshold,
            exit_threshold=self.config.occupancy.exit_threshold,
            capture_resolution=tuple(self.config.camera.resolution)
        )

        # Stats sender (replaces image uploader)
        self.stats_sender = StatsSender(
            server_url=self.config.server.url,
            api_key=self.config_manager.get_api_key(),
            node_id=self.config.node_id,
            timeout=self.config.server.timeout,
            buffer_db_path=self.config.buffer.db_path
        )

        # Health monitor
        self.health = HealthMonitor(
            report_interval=self.config.health.report_interval
        )

        # MQTT client
        mqtt_user, mqtt_pass = self.config_manager.get_mqtt_credentials()
        self.mqtt = MQTTClient(
            broker_host=self.config.mqtt.host,
            broker_port=self.config.mqtt.port,
            node_id=self.config.node_id,
            username=mqtt_user,
            password=mqtt_pass
        )

        # Processing thread
        self._processing_thread = None

        # Statistics
        self._inference_stats = {
            'total_frames': 0,
            'total_detections': 0,
            'total_events': 0,
            'avg_inference_ms': 0.0,
            'last_inference_ms': 0.0
        }

    def start(self):
        """Start all services."""
        logger.info("Starting SmartPark Edge Node v2...")
        self.running = True

        # Initialize camera
        if not self.capture.initialize():
            logger.error("Failed to initialize camera, exiting")
            sys.exit(1)

        # Start capture
        self.capture.start_continuous_capture()

        # Start stats sender background thread
        self.stats_sender.start_background_sender()

        # Connect MQTT
        self.mqtt.connect()

        # Start health monitor
        self.health.add_callback(self._publish_health)
        self.health.add_callback(self._send_health_to_server)
        self.health.start()

        # Set config callback
        self.mqtt.set_config_callback(self._handle_config_update)

        # Start processing thread
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self._processing_thread.start()

        logger.info("SmartPark Edge Node v2 started successfully")
        logger.info(f"Model: {self.config.inference.model_path}")
        logger.info(f"Device: {self.config.inference.device}")
        logger.info(f"Slots loaded: {len(self.occupancy.slots)}")

    def _processing_loop(self):
        """Main processing loop: capture -> inference -> occupancy -> send."""
        logger.info("Processing loop started")

        while self.running:
            try:
                # Get frame from queue
                frame_data = self.capture.frame_queue.get(timeout=1.0)

                # Convert numpy array to PIL Image for inference
                frame_array = frame_data['array']
                frame_id = frame_data['frame_id']
                timestamp = frame_data['timestamp']

                # Run local inference
                inference_result = self.inference.detect_from_array(frame_array)
                detections = inference_result['detections']
                inference_time_ms = inference_result['inference_time_ms']

                # Debug: Log detection details
                logger.info(f"Frame {frame_id}: Detected {len(detections)} vehicles in {inference_time_ms:.0f}ms")
                for i, det in enumerate(detections):
                    logger.info(f"  Vehicle {i+1}: {det['class_name']} at center ({det['center']['x']:.0f}, {det['center']['y']:.0f}), "
                               f"bbox=({det['bbox']['x1']:.0f},{det['bbox']['y1']:.0f})-({det['bbox']['x2']:.0f},{det['bbox']['y2']:.0f}), "
                               f"conf={det['confidence']:.2f}")

                # Process detections through occupancy processor
                events = self.occupancy.process_detections(detections, timestamp)

                # Update statistics
                self._update_inference_stats(
                    inference_time_ms,
                    len(detections),
                    len(events)
                )

                # Send events to server
                if events:
                    model_version = inference_result.get('model_version', 'yolov8m')
                    self.stats_sender.send_slot_events(events, model_version)

                    # Also publish to MQTT
                    for event in events:
                        self.mqtt.publish_slot_state(event)

                # Send summary periodically (every frame for now)
                summary = self.occupancy.get_summary()
                self.mqtt.publish_summary(summary)
                self.stats_sender.send_summary(summary)  # Also send to server via HTTP

                # Send processing log to server
                self.stats_sender.send_processing_log(
                    frame_id=frame_id,
                    inference_time_ms=inference_time_ms,
                    detections_count=len(detections),
                    events_count=len(events)
                )

                # Log processing info
                logger.debug(
                    f"Frame {frame_id}: {len(detections)} detections, "
                    f"{len(events)} events, {inference_time_ms:.1f}ms"
                )

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Processing error: {e}")
                time.sleep(0.1)

    def _update_inference_stats(self, inference_time_ms: float, detections: int, events: int):
        """Update running inference statistics."""
        self._inference_stats['total_frames'] += 1
        self._inference_stats['total_detections'] += detections
        self._inference_stats['total_events'] += events
        self._inference_stats['last_inference_ms'] = inference_time_ms

        # Update running average
        total = self._inference_stats['total_frames']
        current_avg = self._inference_stats['avg_inference_ms']
        self._inference_stats['avg_inference_ms'] = (
            (current_avg * (total - 1) + inference_time_ms) / total
        )

    def _publish_health(self, metrics: dict):
        """Publish health metrics to MQTT."""
        # Add inference stats to health
        health_with_inference = {
            **metrics,
            'inference_stats': self._inference_stats.copy(),
            'sender_stats': self.stats_sender.get_stats(),
            'capture_stats': self.capture.get_stats()
        }
        self.mqtt.publish_health(health_with_inference)

        # Log locally
        logger.info(
            f"Health: CPU={metrics['cpu_percent']}%, "
            f"Temp={metrics['cpu_temp_c']}C, "
            f"WiFi={metrics['wifi_rssi_dbm']}dBm, "
            f"Frames={self._inference_stats['total_frames']}, "
            f"Avg inference={self._inference_stats['avg_inference_ms']:.1f}ms"
        )

    def _send_health_to_server(self, metrics: dict):
        """Send health metrics to server."""
        health_data = {
            **metrics,
            'buffer_depth': self.stats_sender.get_stats().get('buffer_depth', 0)
        }
        self.stats_sender.send_health(health_data)

    def _handle_config_update(self, config: dict):
        """Handle configuration update from server."""
        logger.info(f"Received config update: {config}")

        # Apply config updates dynamically
        if 'capture_interval' in config:
            self.capture.capture_interval = config['capture_interval']
            logger.info(f"Updated capture interval to {config['capture_interval']}s")

        if 'confidence_threshold' in config:
            self.inference.confidence_threshold = config['confidence_threshold']
            logger.info(f"Updated confidence threshold to {config['confidence_threshold']}")

    def stop(self):
        """Stop all services."""
        logger.info("Stopping SmartPark Edge Node v2...")
        self.running = False

        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)

        self.health.stop()
        self.stats_sender.stop()
        self.capture.stop()
        self.mqtt.disconnect()

        logger.info("SmartPark Edge Node v2 stopped")


def main():
    """Main entry point."""
    # Create log directory
    Path('/var/log/smartpark').mkdir(parents=True, exist_ok=True)

    app = SmartParkEdgeV2()

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
