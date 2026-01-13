"""
YOLOv8m inference engine for edge node vehicle detection.
Runs locally on Raspberry Pi.
"""

import logging
import time
from typing import List, Dict, Any, Optional

import numpy as np
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class InferenceEngine:
    """YOLOv8m-based vehicle detection engine for edge deployment."""

    # Vehicle class IDs in COCO dataset
    VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

    def __init__(
        self,
        model_path: str = "yolov8m.pt",
        device: str = "cpu",
        confidence_threshold: float = 0.5
    ):
        self.model_path = model_path
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.model: Optional[YOLO] = None
        self._model_version = f"yolov8m-edge"

        self._load_model()

    def _load_model(self):
        """Load YOLOv8m model."""
        try:
            logger.info(f"Loading YOLOv8m model from {self.model_path}")
            self.model = YOLO(self.model_path)

            # Warm up model with dummy input
            logger.info("Warming up model...")
            dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model.predict(dummy_input, device=self.device, verbose=False)

            logger.info(f"Model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def detect_vehicles(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect vehicles in an image.

        Args:
            image: PIL Image to process

        Returns:
            Dictionary containing:
            - detections: List of detected vehicles with bboxes
            - inference_time_ms: Time taken for inference
            - image_size: (width, height) of input image
            - model_version: Model identifier
        """
        start_time = time.time()

        # Convert to numpy array
        img_array = np.array(image)

        # Run inference
        results = self.model.predict(
            img_array,
            device=self.device,
            conf=self.confidence_threshold,
            classes=list(self.VEHICLE_CLASSES.keys()),
            verbose=False
        )

        inference_time_ms = (time.time() - start_time) * 1000

        # Process detections
        detections = []
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            for i in range(len(boxes)):
                box = boxes[i]
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

                detections.append({
                    'class_id': class_id,
                    'class_name': self.VEHICLE_CLASSES.get(class_id, 'vehicle'),
                    'confidence': confidence,
                    'bbox': {
                        'x1': bbox[0],
                        'y1': bbox[1],
                        'x2': bbox[2],
                        'y2': bbox[3]
                    },
                    'center': {
                        'x': (bbox[0] + bbox[2]) / 2,
                        'y': (bbox[1] + bbox[3]) / 2
                    }
                })

        return {
            'detections': detections,
            'inference_time_ms': inference_time_ms,
            'image_size': (image.width, image.height),
            'model_version': self._model_version
        }

    def detect_from_array(self, frame_array: np.ndarray, rotate_180: bool = True) -> Dict[str, Any]:
        """
        Detect vehicles directly from numpy array.

        Args:
            frame_array: Numpy array (RGB format)
            rotate_180: If True, rotate image 180° before inference for upside-down cameras

        Returns:
            Same as detect_vehicles, with coordinates transformed back if rotated
        """
        image = Image.fromarray(frame_array)

        if rotate_180:
            # Rotate 180° so model sees right-side-up vehicles
            image_for_inference = image.rotate(180)
            result = self.detect_vehicles(image_for_inference)

            # Transform detection coordinates back to original upside-down frame
            img_width, img_height = image.size
            for det in result['detections']:
                # Flip coordinates: new = image_size - old
                det['center']['x'] = img_width - det['center']['x']
                det['center']['y'] = img_height - det['center']['y']

                # Flip bbox (and swap x1/x2, y1/y2 since they reverse)
                old_x1, old_y1 = det['bbox']['x1'], det['bbox']['y1']
                old_x2, old_y2 = det['bbox']['x2'], det['bbox']['y2']
                det['bbox']['x1'] = img_width - old_x2
                det['bbox']['y1'] = img_height - old_y2
                det['bbox']['x2'] = img_width - old_x1
                det['bbox']['y2'] = img_height - old_y1

            return result
        else:
            return self.detect_vehicles(image)

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'model_path': self.model_path,
            'device': self.device,
            'confidence_threshold': self.confidence_threshold,
            'vehicle_classes': self.VEHICLE_CLASSES,
            'model_version': self._model_version
        }
