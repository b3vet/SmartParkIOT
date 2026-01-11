"""
Frame upload and processing endpoints.
"""

import io
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db, FrameLog, SlotState as SlotStateDB
from app.services.occupancy import OccupancyProcessor

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize occupancy processor
occupancy_processor = OccupancyProcessor(
    slots_config_path=settings.slots_config_path,
    debounce_seconds=settings.debounce_seconds,
    enter_threshold=settings.enter_threshold,
    exit_threshold=settings.exit_threshold
)


def verify_api_key(request: Request):
    """Verify API key from header."""
    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/")
async def upload_frame(
    request: Request,
    frame: UploadFile = File(...),
    frame_id: int = Form(...),
    timestamp: str = Form(...),
    node_id: str = Form(...),
    is_replay: bool = Form(False),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """
    Upload a frame for processing.

    - Receives JPEG frame from edge node
    - Runs YOLOv8 inference
    - Maps detections to parking slots
    - Publishes state changes via MQTT
    """
    try:
        # Read image
        contents = await frame.read()
        image = Image.open(io.BytesIO(contents))

        # Parse timestamp
        frame_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Run inference
        inference_engine = request.app.state.inference_engine
        detection_result = inference_engine.detect_vehicles(image)

        # Process occupancy
        events = occupancy_processor.process_detections(
            detection_result['detections'],
            frame_timestamp
        )

        # Store events in database
        for event in events:
            slot_state = SlotStateDB(
                slot_id=event['slot_id'],
                state=event['state'],
                confidence=event['confidence'],
                ts_utc=frame_timestamp,
                dwell_s=event.get('dwell_s', 0),
                roi_version=event.get('roi_version', 'v1'),
                model_version=detection_result.get('model_version')
            )
            db.add(slot_state)

        # Log frame
        frame_log = FrameLog(
            frame_id=frame_id,
            node_id=node_id,
            timestamp=frame_timestamp,
            inference_time_ms=detection_result['inference_time_ms'],
            detections_count=len(detection_result['detections']),
            is_replay=is_replay
        )
        db.add(frame_log)
        db.commit()

        # Publish events via MQTT
        mqtt_publisher = request.app.state.mqtt_publisher
        for event in events:
            mqtt_publisher.publish_slot_state(event)

        # Publish summary periodically
        summary = occupancy_processor.get_summary()
        mqtt_publisher.publish_summary(summary)

        return {
            "status": "success",
            "frame_id": frame_id,
            "detections": len(detection_result['detections']),
            "events": len(events),
            "inference_time_ms": detection_result['inference_time_ms']
        }

    except Exception as e:
        logger.error(f"Frame processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary():
    """Get current parking lot summary."""
    return occupancy_processor.get_summary()


@router.get("/slots")
async def get_all_slots():
    """Get current state of all slots."""
    return {
        "slots": occupancy_processor.get_all_states(),
        "summary": occupancy_processor.get_summary()
    }
