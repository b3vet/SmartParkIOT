"""
Stats sender service for edge node.
Sends processed occupancy data and events to server instead of raw images.
"""

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from queue import Queue, Empty

import requests

logger = logging.getLogger(__name__)


class StatsSender:
    """Sends processed stats and events to server with offline buffering."""

    def __init__(
        self,
        server_url: str,
        api_key: str,
        node_id: str = "fass-edge-01",
        timeout: float = 10.0,
        buffer_db_path: str = "stats_buffer.db"
    ):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.node_id = node_id
        self.timeout = timeout
        self.buffer_db_path = buffer_db_path

        self.events_queue: Queue = Queue(maxsize=100)
        self.running = False
        self._sender_thread: Optional[threading.Thread] = None

        # Statistics
        self._stats = {
            'events_sent': 0,
            'events_failed': 0,
            'events_buffered': 0,
            'events_replayed': 0,
            'summaries_sent': 0
        }

        # Initialize buffer database
        self._init_buffer_db()

    def _init_buffer_db(self):
        """Initialize SQLite buffer for offline storage."""
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            logger.info(f"Buffer database initialized: {self.buffer_db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize buffer database: {e}")

    def send_slot_events(self, events: List[Dict[str, Any]], model_version: str) -> bool:
        """
        Send slot state change events to server.

        Args:
            events: List of slot state change events
            model_version: Version of the inference model

        Returns:
            True if successful, False otherwise
        """
        if not events:
            return True

        payload = {
            'node_id': self.node_id,
            'events': events,
            'model_version': model_version,
            'ts_utc': datetime.now(timezone.utc).isoformat()
        }

        try:
            response = requests.post(
                f"{self.server_url}/api/v2/events",
                json=payload,
                headers={
                    'X-API-Key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                self._stats['events_sent'] += len(events)
                logger.debug(f"Sent {len(events)} events to server")
                return True
            else:
                logger.warning(f"Server returned {response.status_code}: {response.text}")
                self._buffer_events(events, model_version)
                return False

        except requests.RequestException as e:
            logger.error(f"Failed to send events: {e}")
            self._buffer_events(events, model_version)
            return False

    def send_summary(self, summary: Dict[str, Any]) -> bool:
        """
        Send parking lot summary to server.

        Args:
            summary: Parking lot summary data

        Returns:
            True if successful, False otherwise
        """
        payload = {
            'node_id': self.node_id,
            'summary': summary,
            'ts_utc': datetime.now(timezone.utc).isoformat()
        }

        try:
            response = requests.post(
                f"{self.server_url}/api/v2/summary",
                json=payload,
                headers={
                    'X-API-Key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                self._stats['summaries_sent'] += 1
                logger.debug("Sent summary to server")
                return True
            else:
                logger.warning(f"Server returned {response.status_code} for summary")
                return False

        except requests.RequestException as e:
            logger.error(f"Failed to send summary: {e}")
            return False

    def send_health(self, health_data: Dict[str, Any]) -> bool:
        """
        Send node health telemetry to server.

        Args:
            health_data: Health metrics

        Returns:
            True if successful, False otherwise
        """
        payload = {
            'node_id': self.node_id,
            **health_data
        }

        try:
            response = requests.post(
                f"{self.server_url}/api/v2/health",
                json=payload,
                headers={
                    'X-API-Key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.debug("Sent health data to server")
                return True
            else:
                logger.warning(f"Server returned {response.status_code} for health")
                return False

        except requests.RequestException as e:
            logger.error(f"Failed to send health: {e}")
            return False

    def send_processing_log(
        self,
        frame_id: int,
        inference_time_ms: float,
        detections_count: int,
        events_count: int
    ) -> bool:
        """
        Send processing log entry to server.

        Args:
            frame_id: Unique frame identifier
            inference_time_ms: Time taken for inference
            detections_count: Number of vehicle detections
            events_count: Number of state change events

        Returns:
            True if successful, False otherwise
        """
        payload = {
            'node_id': self.node_id,
            'frame_id': frame_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'inference_time_ms': inference_time_ms,
            'detections_count': detections_count,
            'events_count': events_count
        }

        try:
            response = requests.post(
                f"{self.server_url}/api/v2/processing-log",
                json=payload,
                headers={
                    'X-API-Key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=self.timeout
            )

            return response.status_code == 200

        except requests.RequestException as e:
            logger.debug(f"Failed to send processing log: {e}")
            return False

    def _buffer_events(self, events: List[Dict[str, Any]], model_version: str):
        """Buffer events to SQLite for later replay."""
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()

            for event in events:
                payload = json.dumps({
                    'event': event,
                    'model_version': model_version
                })
                cursor.execute(
                    'INSERT INTO event_buffer (event_type, payload, timestamp) VALUES (?, ?, ?)',
                    ('slot_event', payload, datetime.now(timezone.utc).isoformat())
                )

            conn.commit()
            conn.close()
            self._stats['events_buffered'] += len(events)
            logger.info(f"Buffered {len(events)} events for later replay")
        except Exception as e:
            logger.error(f"Failed to buffer events: {e}")
            self._stats['events_failed'] += len(events)

    def replay_buffered_events(self, batch_size: int = 50) -> int:
        """
        Replay buffered events to server.

        Args:
            batch_size: Maximum number of events to replay per call

        Returns:
            Number of events successfully replayed
        """
        replayed = 0

        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, payload FROM event_buffer ORDER BY id LIMIT ?',
                (batch_size,)
            )
            rows = cursor.fetchall()

            if not rows:
                conn.close()
                return 0

            events_to_send = []
            ids_to_delete = []

            for row_id, payload_str in rows:
                try:
                    data = json.loads(payload_str)
                    events_to_send.append(data['event'])
                    ids_to_delete.append(row_id)
                except json.JSONDecodeError:
                    ids_to_delete.append(row_id)

            if events_to_send:
                # Try to send buffered events
                payload = {
                    'node_id': self.node_id,
                    'events': events_to_send,
                    'model_version': 'replay',
                    'ts_utc': datetime.now(timezone.utc).isoformat(),
                    'is_replay': True
                }

                try:
                    response = requests.post(
                        f"{self.server_url}/api/v2/events",
                        json=payload,
                        headers={
                            'X-API-Key': self.api_key,
                            'Content-Type': 'application/json'
                        },
                        timeout=self.timeout
                    )

                    if response.status_code == 200:
                        # Delete successfully sent events
                        cursor.executemany(
                            'DELETE FROM event_buffer WHERE id = ?',
                            [(id,) for id in ids_to_delete]
                        )
                        conn.commit()
                        replayed = len(events_to_send)
                        self._stats['events_replayed'] += replayed
                        logger.info(f"Replayed {replayed} buffered events")

                except requests.RequestException as e:
                    logger.error(f"Failed to replay events: {e}")

            conn.close()

        except Exception as e:
            logger.error(f"Error during replay: {e}")

        return replayed

    def start_background_sender(self):
        """Start background thread for replay and queue processing."""
        if self.running:
            return

        self.running = True
        self._sender_thread = threading.Thread(
            target=self._sender_loop,
            daemon=True
        )
        self._sender_thread.start()
        logger.info("Stats sender background thread started")

    def _sender_loop(self):
        """Background loop for periodic replay."""
        replay_interval = 30  # seconds
        last_replay = time.time()

        while self.running:
            try:
                # Check if it's time to replay buffered events
                if time.time() - last_replay >= replay_interval:
                    self.replay_buffered_events()
                    last_replay = time.time()

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in sender loop: {e}")
                time.sleep(5)

    def stop(self):
        """Stop the background sender."""
        self.running = False
        if self._sender_thread:
            self._sender_thread.join(timeout=5.0)
        logger.info("Stats sender stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get sender statistics."""
        # Get buffer depth
        buffer_depth = 0
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM event_buffer')
            buffer_depth = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

        return {
            **self._stats,
            'buffer_depth': buffer_depth
        }
