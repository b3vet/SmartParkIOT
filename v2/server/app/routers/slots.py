"""
Slot state query endpoints for SmartPark v2.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db, SlotState as SlotStateDB, LotSummary

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
                "previous_state": s.previous_state,
                "confidence": s.confidence,
                "ts_utc": s.ts_utc.isoformat(),
                "dwell_s": s.dwell_s,
                "node_id": s.node_id
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
                "previous_state": s.previous_state,
                "confidence": s.confidence,
                "ts_utc": s.ts_utc.isoformat(),
                "dwell_s": s.dwell_s,
                "roi_version": s.roi_version,
                "node_id": s.node_id
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


@router.get("/current")
async def get_current_states(
    db: Session = Depends(get_db)
):
    """
    Get the most recent state for each slot.
    This provides a snapshot of the current parking lot status.
    """
    # Get distinct slot IDs
    from sqlalchemy import func

    # Subquery to get the latest timestamp for each slot
    subquery = db.query(
        SlotStateDB.slot_id,
        func.max(SlotStateDB.ts_utc).label('max_ts')
    ).group_by(SlotStateDB.slot_id).subquery()

    # Join to get full records
    latest_states = db.query(SlotStateDB).join(
        subquery,
        (SlotStateDB.slot_id == subquery.c.slot_id) &
        (SlotStateDB.ts_utc == subquery.c.max_ts)
    ).all()

    slots = [
        {
            "slot_id": s.slot_id,
            "state": s.state,
            "confidence": s.confidence,
            "last_change": s.ts_utc.isoformat(),
            "dwell_s": s.dwell_s
        }
        for s in latest_states
    ]

    # Calculate summary
    free_count = sum(1 for s in slots if s['state'] == 'free')
    occupied_count = sum(1 for s in slots if s['state'] == 'occupied')
    unknown_count = sum(1 for s in slots if s['state'] == 'unknown')

    return {
        "slots": slots,
        "summary": {
            "free_count": free_count,
            "occupied_count": occupied_count,
            "unknown_count": unknown_count,
            "total_slots": len(slots)
        },
        "ts_utc": datetime.utcnow().isoformat()
    }


@router.get("/summary/history")
async def get_summary_history(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get historical lot summary snapshots."""
    since = datetime.utcnow() - timedelta(hours=hours)

    summaries = db.query(LotSummary).filter(
        LotSummary.ts_utc >= since
    ).order_by(desc(LotSummary.ts_utc)).limit(limit).all()

    return {
        "summaries": [
            {
                "ts_utc": s.ts_utc.isoformat(),
                "free_count": s.free_count,
                "occupied_count": s.occupied_count,
                "unknown_count": s.unknown_count,
                "total_slots": s.total_slots,
                "node_id": s.node_id
            }
            for s in summaries
        ],
        "count": len(summaries)
    }
