"""
Health check and node telemetry endpoints.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db, NodeHealth, FrameLog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def health_check(request: Request):
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "SmartPark API",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/node/{node_id}")
async def get_node_health(
    node_id: str,
    hours: int = Query(1, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """Get health telemetry for a specific node."""
    since = datetime.utcnow() - timedelta(hours=hours)

    health_records = db.query(NodeHealth).filter(
        NodeHealth.node_id == node_id,
        NodeHealth.ts_utc >= since
    ).order_by(desc(NodeHealth.ts_utc)).all()

    if not health_records:
        return {
            "node_id": node_id,
            "status": "no_data",
            "records": []
        }

    latest = health_records[0]

    return {
        "node_id": node_id,
        "status": "online" if (datetime.utcnow() - latest.ts_utc).seconds < 60 else "offline",
        "latest": {
            "ts_utc": latest.ts_utc.isoformat(),
            "uptime_s": latest.uptime_s,
            "cpu_percent": latest.cpu_percent,
            "cpu_temp_c": latest.cpu_temp_c,
            "mem_percent": latest.mem_percent,
            "wifi_rssi_dbm": latest.wifi_rssi_dbm,
            "buffer_depth": latest.buffer_depth
        },
        "history": [
            {
                "ts_utc": h.ts_utc.isoformat(),
                "cpu_temp_c": h.cpu_temp_c,
                "cpu_percent": h.cpu_percent,
                "wifi_rssi_dbm": h.wifi_rssi_dbm
            }
            for h in health_records
        ],
        "record_count": len(health_records)
    }


@router.get("/frames")
async def get_frame_statistics(
    hours: int = Query(1, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """Get frame processing statistics."""
    since = datetime.utcnow() - timedelta(hours=hours)

    frames = db.query(FrameLog).filter(
        FrameLog.timestamp >= since
    ).all()

    if not frames:
        return {
            "period_hours": hours,
            "total_frames": 0,
            "average_inference_ms": 0,
            "average_detections": 0
        }

    total_frames = len(frames)
    avg_inference = sum(f.inference_time_ms or 0 for f in frames) / total_frames
    avg_detections = sum(f.detections_count or 0 for f in frames) / total_frames
    replay_count = sum(1 for f in frames if f.is_replay)

    # Calculate frame rate
    if total_frames > 1:
        time_span = (frames[-1].timestamp - frames[0].timestamp).total_seconds()
        fps = total_frames / time_span if time_span > 0 else 0
    else:
        fps = 0

    return {
        "period_hours": hours,
        "total_frames": total_frames,
        "replay_frames": replay_count,
        "average_inference_ms": round(avg_inference, 2),
        "average_detections": round(avg_detections, 2),
        "effective_fps": round(fps, 3),
        "since": since.isoformat()
    }


@router.get("/model")
async def get_model_info(request: Request):
    """Get inference model information."""
    inference_engine = request.app.state.inference_engine
    return inference_engine.get_model_info()
