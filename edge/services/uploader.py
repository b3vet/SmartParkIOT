"""
HTTP frame uploader service.
Uploads captured frames to cloud server for ML inference.
"""

import time
import logging
import threading
import sqlite3
from queue import Queue, Empty
from typing import Optional
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class FrameUploader:
    """Handles frame upload to server with retry and buffering."""

    def __init__(
        self,
        server_url: str,
        api_key: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        buffer_db_path: str = "upload_buffer.db"
    ):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.buffer_db_path = buffer_db_path

        self.running = False
        self._upload_thread: Optional[threading.Thread] = None
        self._session: Optional[requests.Session] = None
        self._stats = {
            'uploaded': 0,
            'failed': 0,
            'buffered': 0,
            'replayed': 0
        }

        self._init_session()
        self._init_buffer_db()

    def _init_session(self):
        """Initialize requests session with retry logic."""
        self._session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def _init_buffer_db(self):
        """Initialize SQLite buffer for offline storage."""
        conn = sqlite3.connect(self.buffer_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS frame_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER,
                timestamp TEXT,
                data BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def upload_frame(self, frame: dict) -> bool:
        """Upload a single frame to server."""
        try:
            response = self._session.post(
                f"{self.server_url}/api/v1/frames",
                files={'frame': ('frame.jpg', frame['data'], 'image/jpeg')},
                data={
                    'frame_id': frame['frame_id'],
                    'timestamp': frame['timestamp'],
                    'node_id': 'fass-edge-01'
                },
                headers={'X-API-Key': self.api_key},
                timeout=self.timeout
            )

            if response.status_code == 200:
                self._stats['uploaded'] += 1
                logger.debug(f"Frame {frame['frame_id']} uploaded successfully")
                return True
            else:
                logger.warning(f"Upload failed: {response.status_code} - {response.text}")
                self._buffer_frame(frame)
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Upload error: {e}")
            self._buffer_frame(frame)
            self._stats['failed'] += 1
            return False

    def _buffer_frame(self, frame: dict):
        """Store frame in local buffer for later retry."""
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO frame_buffer (frame_id, timestamp, data) VALUES (?, ?, ?)',
                (frame['frame_id'], frame['timestamp'], frame['data'])
            )
            conn.commit()
            conn.close()
            self._stats['buffered'] += 1
            logger.info(f"Frame {frame['frame_id']} buffered for retry")
        except Exception as e:
            logger.error(f"Failed to buffer frame: {e}")

    def replay_buffered_frames(self) -> int:
        """Attempt to upload buffered frames."""
        replayed = 0
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, frame_id, timestamp, data FROM frame_buffer ORDER BY id LIMIT 100'
            )
            rows = cursor.fetchall()

            for row in rows:
                db_id, frame_id, timestamp, data = row
                frame = {
                    'frame_id': frame_id,
                    'timestamp': timestamp,
                    'data': data
                }

                if self._try_upload_buffered(frame):
                    cursor.execute('DELETE FROM frame_buffer WHERE id = ?', (db_id,))
                    replayed += 1
                    self._stats['replayed'] += 1
                else:
                    # Increment retry count
                    cursor.execute(
                        'UPDATE frame_buffer SET retry_count = retry_count + 1 WHERE id = ?',
                        (db_id,)
                    )
                    break  # Stop on first failure

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Replay error: {e}")

        return replayed

    def _try_upload_buffered(self, frame: dict) -> bool:
        """Try to upload a buffered frame without re-buffering on failure."""
        try:
            response = self._session.post(
                f"{self.server_url}/api/v1/frames",
                files={'frame': ('frame.jpg', frame['data'], 'image/jpeg')},
                data={
                    'frame_id': frame['frame_id'],
                    'timestamp': frame['timestamp'],
                    'node_id': 'fass-edge-01',
                    'is_replay': True
                },
                headers={'X-API-Key': self.api_key},
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False

    def start_upload_worker(self, frame_queue: Queue):
        """Start background upload worker."""
        self.running = True
        self._upload_thread = threading.Thread(
            target=self._upload_loop,
            args=(frame_queue,),
            daemon=True
        )
        self._upload_thread.start()
        logger.info("Upload worker started")

    def _upload_loop(self, frame_queue: Queue):
        """Background upload loop."""
        replay_interval = 30  # Try replay every 30 seconds
        last_replay = time.time()

        while self.running:
            try:
                # Get frame from queue
                frame = frame_queue.get(timeout=1.0)
                self.upload_frame(frame)

                # Periodically try to replay buffered frames
                if time.time() - last_replay > replay_interval:
                    replayed = self.replay_buffered_frames()
                    if replayed > 0:
                        logger.info(f"Replayed {replayed} buffered frames")
                    last_replay = time.time()

            except Empty:
                # No frames to upload, try replay
                if time.time() - last_replay > replay_interval:
                    self.replay_buffered_frames()
                    last_replay = time.time()

    def stop(self):
        """Stop upload worker."""
        self.running = False
        if self._upload_thread:
            self._upload_thread.join(timeout=5.0)
        logger.info("Upload worker stopped")

    def get_stats(self) -> dict:
        """Get upload statistics."""
        # Count buffered frames
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM frame_buffer')
            buffer_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            buffer_count = -1

        return {
            **self._stats,
            'buffer_count': buffer_count
        }
