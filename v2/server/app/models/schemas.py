"""
Pydantic schemas for request/response validation.
SmartPark Server v2 - receives processed events from edge nodes.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# Event schemas (received from edge)

class SlotEventItem(BaseModel):
    """Single slot state change event."""
    slot_id: str
    state: str
    previous_state: str
    confidence: float
    ts_utc: str
    dwell_s: int = 0
    roi_version: str = "v1"


class SlotEventsRequest(BaseModel):
    """Request for posting slot events from edge."""
    node_id: str
    events: List[SlotEventItem]
    model_version: str
    ts_utc: str
    is_replay: bool = False


class SlotEventsResponse(BaseModel):
    """Response for slot events submission."""
    status: str
    events_received: int
    events_stored: int


# Summary schemas

class SummaryItem(BaseModel):
    """Parking lot summary."""
    free_count: int
    occupied_count: int
    unknown_count: int
    total_slots: int
    ts_utc: str
    roi_version: str = "v1"


class SummaryRequest(BaseModel):
    """Request for posting summary from edge."""
    node_id: str
    summary: SummaryItem
    ts_utc: str


class SummaryResponse(BaseModel):
    """Response for summary submission."""
    status: str


# Health schemas

class HealthRequest(BaseModel):
    """Health data from edge node."""
    node_id: str
    ts_utc: str
    uptime_s: int
    cpu_percent: float
    cpu_temp_c: float
    mem_used_mb: int
    mem_percent: float
    wifi_rssi_dbm: int
    buffer_depth: int = 0


class HealthResponse(BaseModel):
    """Response for health submission."""
    status: str


# Processing log schemas

class ProcessingLogRequest(BaseModel):
    """Processing log entry from edge."""
    node_id: str
    frame_id: int
    timestamp: str
    inference_time_ms: float
    detections_count: int
    events_count: int


class ProcessingLogResponse(BaseModel):
    """Response for processing log submission."""
    status: str


# Query response schemas

class SlotStateResponse(BaseModel):
    """Schema for slot state response."""
    slot_id: str
    state: str
    confidence: float
    ts_utc: str
    dwell_s: int
    previous_state: Optional[str] = None

    class Config:
        from_attributes = True


class NodeHealthResponse(BaseModel):
    """Schema for node health response."""
    node_id: str
    ts_utc: datetime
    uptime_s: int
    cpu_percent: float
    cpu_temp_c: float
    mem_used_mb: int
    mem_percent: float
    wifi_rssi_dbm: int
    buffer_depth: int

    class Config:
        from_attributes = True


class LotSummaryResponse(BaseModel):
    """Schema for lot summary response."""
    free_count: int
    occupied_count: int
    unknown_count: int
    total_slots: int
    ts_utc: str
    roi_version: str
