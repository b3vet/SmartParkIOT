"""
Frame capture service using Pi Camera Module.
Captures frames at configurable intervals for local inference.
"""

import io
import time
import logging
import threading
from queue import Queue, Full
from datetime import datetime, timezone
from typing import Optional, Callable

import numpy as np
from picamera2 import Picamera2
from PIL import Image

logger = logging.getLogger(__name__)


class FrameCapture:
    """Manages camera capture with frame queuing for local inference."""

    def __init__(
        self,
        resolution: tuple[int, int] = (1920, 1080),
        capture_interval: float = 5.0,
        queue_size: int = 5
    ):
        self.resolution = resolution
        self.capture_interval = capture_interval
        self.frame_queue: Queue = Queue(maxsize=queue_size)

        self.camera: Optional[Picamera2] = None
        self.running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._last_capture_time: Optional[float] = None

    def initialize(self) -> bool:
        """Initialize the camera."""
        try:
            self.camera = Picamera2()
            config = self.camera.create_still_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                buffer_count=2
            )
            self.camera.configure(config)
            self.camera.start()
            time.sleep(2)  # Allow camera to warm up
            logger.info(f"Camera initialized at {self.resolution}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

    def capture_frame(self) -> Optional[dict]:
        """
        Capture a single frame and return as numpy array with metadata.

        Returns dict with:
            - frame_id: Unique frame identifier
            - timestamp: ISO format timestamp
            - array: Numpy array (RGB format)
            - resolution: Tuple of (width, height)
        """
        if not self.camera:
            return None

        try:
            # Capture to numpy array (RGB format)
            frame_array = self.camera.capture_array()

            timestamp = datetime.now(timezone.utc)
            self._frame_count += 1
            self._last_capture_time = time.time()

            return {
                'frame_id': self._frame_count,
                'timestamp': timestamp,
                'array': frame_array,
                'resolution': self.resolution
            }
        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            return None

    def start_continuous_capture(self):
        """Start continuous frame capture in background thread."""
        if self.running:
            return

        self.running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self._capture_thread.start()
        logger.info("Continuous capture started")

    def _capture_loop(self):
        """Background capture loop."""
        while self.running:
            start_time = time.time()

            frame = self.capture_frame()
            if frame:
                try:
                    self.frame_queue.put(frame, timeout=1.0)
                except Full:
                    logger.warning("Frame queue full, dropping oldest frame")
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame, timeout=0.1)
                    except Exception:
                        pass

            # Maintain capture interval
            elapsed = time.time() - start_time
            sleep_time = max(0, self.capture_interval - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        """Stop capture and release camera."""
        self.running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=5.0)
        if self.camera:
            self.camera.stop()
            self.camera.close()
        logger.info("Camera capture stopped")

    def get_stats(self) -> dict:
        """Get capture statistics."""
        return {
            'frame_count': self._frame_count,
            'queue_size': self.frame_queue.qsize(),
            'last_capture': self._last_capture_time,
            'running': self.running,
            'resolution': self.resolution,
            'capture_interval': self.capture_interval
        }
