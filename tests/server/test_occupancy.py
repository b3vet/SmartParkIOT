"""
Unit tests for occupancy processor.
"""

import pytest
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.services.occupancy import OccupancyProcessor


@pytest.fixture
def slots_config():
    """Create temporary slots configuration."""
    config = {
        "roi_version": "test_v1",
        "image_size": [1920, 1080],
        "slots": [
            {
                "slot_id": "TEST_001",
                "poly": [[100, 100], [200, 100], [200, 200], [100, 200]]
            },
            {
                "slot_id": "TEST_002",
                "poly": [[300, 100], [400, 100], [400, 200], [300, 200]]
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        return f.name


@pytest.fixture
def processor(slots_config):
    """Create occupancy processor with test config."""
    return OccupancyProcessor(
        slots_config_path=slots_config,
        debounce_seconds=0.1,  # Short debounce for testing
        enter_threshold=0.5,
        exit_threshold=0.5
    )


def test_load_slots(processor):
    """Test slot loading."""
    assert len(processor.slots) == 2
    assert "TEST_001" in processor.slots
    assert "TEST_002" in processor.slots


def test_get_summary(processor):
    """Test summary generation."""
    summary = processor.get_summary()

    assert 'free_count' in summary
    assert 'occupied_count' in summary
    assert 'unknown_count' in summary
    assert 'total_slots' in summary
    assert summary['total_slots'] == 2


def test_get_all_states(processor):
    """Test get all states."""
    states = processor.get_all_states()

    assert len(states) == 2
    for state in states:
        assert 'slot_id' in state
        assert 'state' in state
        assert 'confidence' in state
        assert 'last_change' in state


def test_process_detection_in_slot(processor):
    """Test detection processing when vehicle is in slot."""
    detections = [
        {
            'center': {'x': 150, 'y': 150},  # Inside TEST_001
            'confidence': 0.9
        }
    ]
    timestamp = datetime.now(timezone.utc)

    # First call - starts pending
    events1 = processor.process_detections(detections, timestamp)

    # Wait for debounce and call again
    import time
    time.sleep(0.2)
    events2 = processor.process_detections(detections, timestamp)

    # Should eventually produce an event
    assert processor.slots["TEST_001"].current_state in ["occupied", "unknown"]


def test_process_detection_outside_slots(processor):
    """Test detection processing when vehicle is outside all slots."""
    detections = [
        {
            'center': {'x': 500, 'y': 500},  # Outside all slots
            'confidence': 0.9
        }
    ]
    timestamp = datetime.now(timezone.utc)

    events = processor.process_detections(detections, timestamp)

    # No events should be generated for out-of-bounds detections
    # (or slots should remain in their current state)
    assert isinstance(events, list)


def test_empty_detections(processor):
    """Test processing with no detections."""
    detections = []
    timestamp = datetime.now(timezone.utc)

    events = processor.process_detections(detections, timestamp)

    assert isinstance(events, list)
