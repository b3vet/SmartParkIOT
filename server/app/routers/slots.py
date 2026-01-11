"""
Slot state endpoints.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db, SlotState as SlotStateDB

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/history/{slot_id}")
async def get_slot_history(
    slot_id: str,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get historical state changes for a specific slot."""
    since = datetime.utcnow() - timedelta(hours=hours)

    states = db.query(SlotStateDB).filter(
        SlotStateDB.slot_id == slot_id,
        SlotStateDB.ts_utc >= since
    ).order_by(desc(SlotStateDB.ts_utc)).all()

    return {
        "slot_id": slot_id,
        "history": [
            {
                "state": s.state,
                "confidence": s.confidence,
                "ts_utc": s.ts_utc.isoformat(),
                "dwell_s": s.dwell_s
            }
            for s in states
        ],
        "count": len(states)
    }


@router.get("/recent")
async def get_recent_changes(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get most recent state changes across all slots."""
    states = db.query(SlotStateDB).order_by(
        desc(SlotStateDB.ts_utc)
    ).limit(limit).all()

    return {
        "changes": [
            {
                "slot_id": s.slot_id,
                "state": s.state,
                "confidence": s.confidence,
                "ts_utc": s.ts_utc.isoformat(),
                "dwell_s": s.dwell_s,
                "roi_version": s.roi_version
            }
            for s in states
        ],
        "count": len(states)
    }


@router.get("/statistics")
async def get_slot_statistics(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get occupancy statistics for the time period."""
    since = datetime.utcnow() - timedelta(hours=hours)

    states = db.query(SlotStateDB).filter(
        SlotStateDB.ts_utc >= since
    ).all()

    # Calculate statistics
    total_changes = len(states)
    occupied_events = sum(1 for s in states if s.state == "occupied")
    free_events = sum(1 for s in states if s.state == "free")

    # Average dwell time for occupied slots
    dwell_times = [s.dwell_s for s in states if s.state == "free" and s.dwell_s > 0]
    avg_dwell = sum(dwell_times) / len(dwell_times) if dwell_times else 0

    # Get unique slots
    unique_slots = len(set(s.slot_id for s in states))

    return {
        "period_hours": hours,
        "total_state_changes": total_changes,
        "occupied_events": occupied_events,
        "free_events": free_events,
        "unique_slots_with_activity": unique_slots,
        "average_dwell_seconds": round(avg_dwell, 1),
        "since": since.isoformat()
    }
