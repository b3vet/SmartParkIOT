"""
YOLOv8 inference engine for vehicle detection.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class InferenceEngine:
    """YOLOv8-based vehicle detection engine."""

    # Vehicle class IDs in COCO dataset
    VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

    def __init__(
        self,
        model_path: str = "yolov8l.pt",
        device: str = "cpu",
        confidence_threshold: float = 0.5
    ):
        self.model_path = model_path
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.model: Optional[YOLO] = None

        self._load_model()

    def _load_model(self):
        """Load YOLOv8 model."""
        try:
            logger.info(f"Loading YOLOv8 model from {self.model_path}")
            self.model = YOLO(self.model_path)

            # Warm up model
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
            'model_version': f"yolov8l-{self.model_path.split('/')[-1]}"
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'model_path': self.model_path,
            'device': self.device,
            'confidence_threshold': self.confidence_threshold,
            'vehicle_classes': self.VEHICLE_CLASSES
        }
