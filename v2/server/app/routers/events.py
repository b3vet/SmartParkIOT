"""
Event receiver endpoints for SmartPark v2.
Receives processed events from edge nodes.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db, SlotState, NodeHealth, ProcessingLog, LotSummary
from app.models.schemas import (
    SlotEventsRequest,
    SlotEventsResponse,
    SummaryRequest,
    SummaryResponse,
    HealthRequest,
    HealthResponse,
    ProcessingLogRequest,
    ProcessingLogResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header."""
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@router.post("/events", response_model=SlotEventsResponse)
async def receive_slot_events(
    request: Request,
    data: SlotEventsRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Receive slot state change events from edge node.

    This endpoint receives processed occupancy events that were detected
    by the edge node's local inference.
    """
    # Demo: Log raw JSON payload
    logger.info(f"\n{'='*60}\n[SLOT EVENTS]\n{json.dumps(data.model_dump(), indent=2)}\n{'='*60}")

    events_stored = 0

    for event in data.events:
        try:
            # Parse timestamp
            ts_utc = datetime.fromisoformat(event.ts_utc.replace('Z', '+00:00'))

            # Create database record
            slot_state = SlotState(
                slot_id=event.slot_id,
                state=event.state,
                previous_state=event.previous_state,
                confidence=event.confidence,
                ts_utc=ts_utc,
                dwell_s=event.dwell_s,
                roi_version=event.roi_version,
                model_version=data.model_version,
                node_id=data.node_id
            )
            db.add(slot_state)
            events_stored += 1

            # Publish to MQTT
            mqtt_publisher = request.app.state.mqtt_publisher
            mqtt_publisher.publish_slot_state({
                'slot_id': event.slot_id,
                'state': event.state,
                'previous_state': event.previous_state,
                'confidence': event.confidence,
                'ts_utc': event.ts_utc,
                'dwell_s': event.dwell_s,
                'roi_version': event.roi_version,
                'node_id': data.node_id
            })

        except Exception as e:
            logger.error(f"Error storing event for slot {event.slot_id}: {e}")

    db.commit()

    logger.info(f"Received {len(data.events)} events from {data.node_id}, stored {events_stored}")

    return SlotEventsResponse(
        status="success",
        events_received=len(data.events),
        events_stored=events_stored
    )


@router.post("/summary", response_model=SummaryResponse)
async def receive_summary(
    request: Request,
    data: SummaryRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Receive parking lot summary from edge node.
    """
    # Demo: Log raw JSON payload
    logger.info(f"\n{'='*60}\n[SUMMARY]\n{json.dumps(data.model_dump(), indent=2)}\n{'='*60}")

    try:
        # Parse timestamp
        ts_utc = datetime.fromisoformat(data.summary.ts_utc.replace('Z', '+00:00'))

        # Store summary snapshot
        summary = LotSummary(
            node_id=data.node_id,
            ts_utc=ts_utc,
            free_count=data.summary.free_count,
            occupied_count=data.summary.occupied_count,
            unknown_count=data.summary.unknown_count,
            total_slots=data.summary.total_slots,
            roi_version=data.summary.roi_version
        )
        db.add(summary)
        db.commit()

        # Publish to MQTT
        mqtt_publisher = request.app.state.mqtt_publisher
        mqtt_publisher.publish_summary({
            'node_id': data.node_id,
            'free_count': data.summary.free_count,
            'occupied_count': data.summary.occupied_count,
            'unknown_count': data.summary.unknown_count,
            'total_slots': data.summary.total_slots,
            'ts_utc': data.summary.ts_utc,
            'roi_version': data.summary.roi_version
        })

        return SummaryResponse(status="success")

    except Exception as e:
        logger.error(f"Error storing summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health", response_model=HealthResponse)
async def receive_health(
    request: Request,
    data: HealthRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Receive health telemetry from edge node.
    """
    # Demo: Log raw JSON payload
    logger.info(f"\n{'='*60}\n[HEALTH]\n{json.dumps(data.model_dump(), indent=2)}\n{'='*60}")

    try:
        # Parse timestamp
        ts_utc = datetime.fromisoformat(data.ts_utc.replace('Z', '+00:00'))

        # Store health record
        health = NodeHealth(
            node_id=data.node_id,
            ts_utc=ts_utc,
            uptime_s=data.uptime_s,
            cpu_percent=data.cpu_percent,
            cpu_temp_c=data.cpu_temp_c,
            mem_used_mb=data.mem_used_mb,
            mem_percent=data.mem_percent,
            wifi_rssi_dbm=data.wifi_rssi_dbm,
            buffer_depth=data.buffer_depth
        )
        db.add(health)
        db.commit()

        # Publish to MQTT
        mqtt_publisher = request.app.state.mqtt_publisher
        mqtt_publisher.publish_node_health({
            'node_id': data.node_id,
            'ts_utc': data.ts_utc,
            'uptime_s': data.uptime_s,
            'cpu_percent': data.cpu_percent,
            'cpu_temp_c': data.cpu_temp_c,
            'mem_percent': data.mem_percent,
            'wifi_rssi_dbm': data.wifi_rssi_dbm,
            'buffer_depth': data.buffer_depth
        })

        return HealthResponse(status="success")

    except Exception as e:
        logger.error(f"Error storing health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/processing-log", response_model=ProcessingLogResponse)
async def receive_processing_log(
    data: ProcessingLogRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Receive processing log entry from edge node.
    """
    # Demo: Log raw JSON payload
    logger.info(f"\n{'='*60}\n[PROCESSING LOG]\n{json.dumps(data.model_dump(), indent=2)}\n{'='*60}")

    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))

        # Store processing log
        log = ProcessingLog(
            frame_id=data.frame_id,
            node_id=data.node_id,
            timestamp=timestamp,
            inference_time_ms=data.inference_time_ms,
            detections_count=data.detections_count,
            events_count=data.events_count
        )
        db.add(log)
        db.commit()

        return ProcessingLogResponse(status="success")

    except Exception as e:
        logger.error(f"Error storing processing log: {e}")
        raise HTTPException(status_code=500, detail=str(e))
