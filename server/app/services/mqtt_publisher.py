"""
MQTT publisher for slot state events and summaries.
"""

import json
import logging
from typing import Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """MQTT publisher for SmartPark server."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.client = mqtt.Client(client_id="smartpark-server")
        self.connected = False

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        # Set credentials if provided
        if username and password:
            self.client.username_pw_set(username, password)

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection event."""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.host}")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection event."""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (rc={rc})")

    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_slot_state(self, event: dict):
        """Publish slot state change event."""
        topic = f"su/parking/fass/slot/{event['slot_id']}/state"
        self.client.publish(topic, json.dumps(event), qos=1)
        logger.debug(f"Published slot state: {event['slot_id']} -> {event['state']}")

    def publish_summary(self, summary: dict):
        """Publish lot summary."""
        topic = "su/parking/fass/summary"
        self.client.publish(topic, json.dumps(summary), qos=0)

    def publish_node_health(self, health: dict):
        """Publish node health (received from edge, stored and republished)."""
        topic = f"su/parking/fass/node/{health.get('node_id', 'unknown')}/health"
        self.client.publish(topic, json.dumps(health), qos=0)

    def disconnect(self):
        """Disconnect from broker."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT publisher disconnected")
