"""
MQTT client for telemetry publishing and config updates.
Publishes slot state changes, summaries, and node health to MQTT broker.
"""

import json
import logging
import threading
from typing import Optional, Callable, Dict, Any

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client wrapper for SmartPark edge node v2."""

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        node_id: str = "fass-edge-01",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.node_id = node_id
        self.username = username
        self.password = password

        self.client = mqtt.Client(client_id=f"smartpark-v2-{node_id}")
        self.connected = False
        self._config_callback: Optional[Callable] = None

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Set credentials if provided
        if username and password:
            self.client.username_pw_set(username, password)

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection event."""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.broker_host}")
            # Subscribe to config topic
            client.subscribe(f"su/parking/fass/config", qos=1)
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection event."""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (rc={rc})")

    def _on_message(self, client, userdata, msg):
        """Handle incoming messages."""
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received message on {msg.topic}: {payload}")

            if 'config' in msg.topic and self._config_callback:
                self._config_callback(payload)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_health(self, metrics: dict):
        """Publish health metrics."""
        topic = f"su/parking/fass/node_health"
        payload = {
            'node_id': self.node_id,
            **metrics
        }
        self.client.publish(topic, json.dumps(payload), qos=0)

    def publish_slot_state(self, event: Dict[str, Any]):
        """Publish slot state change event."""
        topic = f"su/parking/fass/slot/{event['slot_id']}/state"
        payload = {
            'node_id': self.node_id,
            **event
        }
        self.client.publish(topic, json.dumps(payload), qos=1)
        logger.debug(f"Published slot state: {event['slot_id']} -> {event['state']}")

    def publish_summary(self, summary: Dict[str, Any]):
        """Publish lot summary."""
        topic = "su/parking/fass/summary"
        payload = {
            'node_id': self.node_id,
            **summary
        }
        self.client.publish(topic, json.dumps(payload), qos=0)

    def publish_inference_stats(self, stats: Dict[str, Any]):
        """Publish inference statistics."""
        topic = f"su/parking/fass/inference_stats"
        payload = {
            'node_id': self.node_id,
            **stats
        }
        self.client.publish(topic, json.dumps(payload), qos=0)

    def publish_capture_stats(self, stats: dict):
        """Publish capture statistics."""
        topic = f"su/parking/fass/capture_stats"
        payload = {
            'node_id': self.node_id,
            **stats
        }
        self.client.publish(topic, json.dumps(payload), qos=0)

    def set_config_callback(self, callback: Callable):
        """Set callback for config updates."""
        self._config_callback = callback

    def disconnect(self):
        """Disconnect from broker."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT client disconnected")
