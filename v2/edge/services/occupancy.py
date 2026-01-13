"""
Parking slot occupancy processor for edge node.
Maps vehicle detections to parking slots with debouncing.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)


@dataclass
class SlotState:
    """State tracking for a single slot."""
    slot_id: str
    polygon: Polygon
    current_state: str = "unknown"  # occupied, free, unknown
    confidence: float = 0.0
    last_change: float = field(default_factory=time.time)
    pending_state: Optional[str] = None
    pending_since: Optional[float] = None
    dwell_start: float = field(default_factory=time.time)


class OccupancyProcessor:
    """Processes vehicle detections to determine slot occupancy."""

    def __init__(
        self,
        slots_config_path: str,
        debounce_seconds: float = 3.0,
        enter_threshold: float = 0.6,
        exit_threshold: float = 0.4,
        capture_resolution: tuple = (1920, 1080)
    ):
        self.debounce_seconds = debounce_seconds
        self.enter_threshold = enter_threshold
        self.exit_threshold = exit_threshold
        self.capture_resolution = capture_resolution

        self.slots: Dict[str, SlotState] = {}
        self._load_slots(slots_config_path)
        self._roi_version = "v1"

    def _load_slots(self, config_path: str):
        """Load slot definitions from JSON file and scale to capture resolution."""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Slots config not found: {config_path}, using empty slots")
                return

            with open(config_path) as f:
                config = json.load(f)

            self._roi_version = config.get('roi_version', 'v1')

            # Get original image size from config and calculate scale factors
            original_size = config.get('image_size', self.capture_resolution)
            scale_x = self.capture_resolution[0] / original_size[0]
            scale_y = self.capture_resolution[1] / original_size[1]

            logger.info(f"Scaling polygons from {original_size} to {self.capture_resolution} "
                       f"(scale: {scale_x:.3f}, {scale_y:.3f})")

            for slot_def in config.get('slots', []):
                slot_id = slot_def['slot_id']
                points = slot_def['poly']

                # Scale polygon points to match capture resolution
                scaled_points = [
                    (p[0] * scale_x, p[1] * scale_y) for p in points
                ]
                polygon = Polygon(scaled_points)

                self.slots[slot_id] = SlotState(
                    slot_id=slot_id,
                    polygon=polygon
                )

            logger.info(f"Loaded {len(self.slots)} slots from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load slots config: {e}")

    def process_detections(
        self,
        detections: List[Dict],
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """
        Process vehicle detections and update slot states.

        Args:
            detections: List of vehicle detections from inference
            timestamp: Frame timestamp

        Returns:
            List of state change events to publish
        """
        current_time = time.time()
        events = []

        # Check which slots contain vehicle centers
        slot_occupancy = {slot_id: False for slot_id in self.slots}
        slot_confidence = {slot_id: 0.0 for slot_id in self.slots}

        for detection in detections:
            center = Point(detection['center']['x'], detection['center']['y'])

            for slot_id, slot_state in self.slots.items():
                if slot_state.polygon.contains(center):
                    slot_occupancy[slot_id] = True
                    slot_confidence[slot_id] = max(
                        slot_confidence[slot_id],
                        detection['confidence']
                    )

        # Update slot states with debouncing
        for slot_id, is_occupied in slot_occupancy.items():
            slot = self.slots[slot_id]
            new_state = "occupied" if is_occupied else "free"
            confidence = slot_confidence[slot_id] if is_occupied else 1.0 - slot_confidence.get(slot_id, 0)

            event = self._update_slot_state(
                slot, new_state, confidence, timestamp, current_time
            )
            if event:
                events.append(event)

        return events

    def _update_slot_state(
        self,
        slot: SlotState,
        new_state: str,
        confidence: float,
        timestamp: datetime,
        current_time: float
    ) -> Optional[Dict[str, Any]]:
        """Update slot state with hysteresis and debouncing."""

        # Apply hysteresis thresholds
        if slot.current_state == "free" and new_state == "occupied":
            if confidence < self.enter_threshold:
                new_state = "free"  # Not confident enough to change
        elif slot.current_state == "occupied" and new_state == "free":
            if confidence < self.exit_threshold:
                new_state = "occupied"  # Not confident enough to change

        # Check if state is changing
        if new_state != slot.current_state:
            # Start or continue debounce period
            if slot.pending_state != new_state:
                slot.pending_state = new_state
                slot.pending_since = current_time
                slot.confidence = confidence
            elif current_time - slot.pending_since >= self.debounce_seconds:
                # Debounce complete, confirm state change
                dwell_s = int(current_time - slot.dwell_start)

                event = {
                    'slot_id': slot.slot_id,
                    'state': new_state,
                    'previous_state': slot.current_state,
                    'confidence': confidence,
                    'ts_utc': timestamp.isoformat(),
                    'dwell_s': dwell_s,
                    'roi_version': self._roi_version
                }

                # Update slot state
                slot.current_state = new_state
                slot.last_change = current_time
                slot.dwell_start = current_time
                slot.pending_state = None
                slot.pending_since = None

                logger.info(f"Slot {slot.slot_id}: {event['previous_state']} -> {new_state}")
                return event
        else:
            # State matches, clear pending
            slot.pending_state = None
            slot.pending_since = None
            slot.confidence = confidence

        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get current lot summary."""
        free_count = sum(1 for s in self.slots.values() if s.current_state == "free")
        occupied_count = sum(1 for s in self.slots.values() if s.current_state == "occupied")
        unknown_count = sum(1 for s in self.slots.values() if s.current_state == "unknown")

        return {
            'free_count': free_count,
            'occupied_count': occupied_count,
            'unknown_count': unknown_count,
            'total_slots': len(self.slots),
            'ts_utc': datetime.now(timezone.utc).isoformat(),
            'roi_version': self._roi_version
        }

    def get_all_states(self) -> List[Dict[str, Any]]:
        """Get current state of all slots."""
        return [
            {
                'slot_id': slot.slot_id,
                'state': slot.current_state,
                'confidence': slot.confidence,
                'last_change': datetime.fromtimestamp(slot.last_change, tz=timezone.utc).isoformat()
            }
            for slot in self.slots.values()
        ]

    def get_roi_version(self) -> str:
        """Get the current ROI version."""
        return self._roi_version
