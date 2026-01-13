"""
Health check and node telemetry query endpoints for SmartPark v2.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db, NodeHealth, ProcessingLog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def health_check(request: Request):
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "SmartPark API v2",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/node/{node_id}")
async def get_node_health(
    node_id: str,
    hours: int = Query(1, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """Get health telemetry for a specific edge node."""
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


@router.get("/nodes")
async def list_nodes(
    hours: int = Query(1, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """List all known edge nodes and their status."""
    since = datetime.utcnow() - timedelta(hours=hours)

    # Get distinct node IDs with their latest health
    from sqlalchemy import func

    subquery = db.query(
        NodeHealth.node_id,
        func.max(NodeHealth.ts_utc).label('max_ts')
    ).filter(
        NodeHealth.ts_utc >= since
    ).group_by(NodeHealth.node_id).subquery()

    latest_health = db.query(NodeHealth).join(
        subquery,
        (NodeHealth.node_id == subquery.c.node_id) &
        (NodeHealth.ts_utc == subquery.c.max_ts)
    ).all()

    nodes = []
    for h in latest_health:
        is_online = (datetime.utcnow() - h.ts_utc).seconds < 60
        nodes.append({
            "node_id": h.node_id,
            "status": "online" if is_online else "offline",
            "last_seen": h.ts_utc.isoformat(),
            "cpu_percent": h.cpu_percent,
            "cpu_temp_c": h.cpu_temp_c,
            "buffer_depth": h.buffer_depth
        })

    return {
        "nodes": nodes,
        "count": len(nodes)
    }


@router.get("/processing")
async def get_processing_statistics(
    hours: int = Query(1, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """Get processing statistics from edge nodes."""
    since = datetime.utcnow() - timedelta(hours=hours)

    logs = db.query(ProcessingLog).filter(
        ProcessingLog.timestamp >= since
    ).all()

    if not logs:
        return {
            "period_hours": hours,
            "total_frames": 0,
            "average_inference_ms": 0,
            "average_detections": 0
        }

    total_frames = len(logs)
    avg_inference = sum(l.inference_time_ms or 0 for l in logs) / total_frames
    avg_detections = sum(l.detections_count or 0 for l in logs) / total_frames
    total_events = sum(l.events_count or 0 for l in logs)

    # Calculate frame rate
    if total_frames > 1:
        time_span = (logs[-1].timestamp - logs[0].timestamp).total_seconds()
        fps = total_frames / time_span if time_span > 0 else 0
    else:
        fps = 0

    # Group by node
    by_node = {}
    for log in logs:
        if log.node_id not in by_node:
            by_node[log.node_id] = {
                'frames': 0,
                'total_inference_ms': 0,
                'total_detections': 0,
                'total_events': 0
            }
        by_node[log.node_id]['frames'] += 1
        by_node[log.node_id]['total_inference_ms'] += log.inference_time_ms or 0
        by_node[log.node_id]['total_detections'] += log.detections_count or 0
        by_node[log.node_id]['total_events'] += log.events_count or 0

    node_stats = [
        {
            'node_id': node_id,
            'frames': stats['frames'],
            'avg_inference_ms': round(stats['total_inference_ms'] / stats['frames'], 2),
            'avg_detections': round(stats['total_detections'] / stats['frames'], 2),
            'total_events': stats['total_events']
        }
        for node_id, stats in by_node.items()
    ]

    return {
        "period_hours": hours,
        "total_frames": total_frames,
        "total_events": total_events,
        "average_inference_ms": round(avg_inference, 2),
        "average_detections": round(avg_detections, 2),
        "effective_fps": round(fps, 3),
        "by_node": node_stats,
        "since": since.isoformat()
    }
