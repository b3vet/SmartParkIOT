"""
Unit tests for inference engine.
"""

import pytest
from PIL import Image
import numpy as np

# Skip import if ultralytics not available (for CI environments)
try:
    from app.services.inference import InferenceEngine
    INFERENCE_AVAILABLE = True
except ImportError:
    INFERENCE_AVAILABLE = False


@pytest.fixture
def inference_engine():
    """Create inference engine for testing."""
    if not INFERENCE_AVAILABLE:
        pytest.skip("Inference engine not available")
    return InferenceEngine(model_path="yolov8l.pt", device="cpu")


@pytest.mark.skipif(not INFERENCE_AVAILABLE, reason="Inference not available")
def test_detect_empty_image(inference_engine):
    """Test detection on empty parking lot image."""
    # Create blank image
    image = Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))
    result = inference_engine.detect_vehicles(image)

    assert 'detections' in result
    assert 'inference_time_ms' in result
    assert len(result['detections']) == 0


@pytest.mark.skipif(not INFERENCE_AVAILABLE, reason="Inference not available")
def test_detection_format(inference_engine):
    """Test detection output format."""
    image = Image.fromarray(np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8))
    result = inference_engine.detect_vehicles(image)

    assert 'detections' in result
    assert 'inference_time_ms' in result
    assert 'image_size' in result
    assert 'model_version' in result

    for detection in result['detections']:
        assert 'class_id' in detection
        assert 'class_name' in detection
        assert 'confidence' in detection
        assert 'bbox' in detection
        assert 'center' in detection


@pytest.mark.skipif(not INFERENCE_AVAILABLE, reason="Inference not available")
def test_model_info(inference_engine):
    """Test model info retrieval."""
    info = inference_engine.get_model_info()

    assert 'model_path' in info
    assert 'device' in info
    assert 'confidence_threshold' in info
    assert 'vehicle_classes' in info
