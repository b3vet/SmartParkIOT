"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SlotStateCreate(BaseModel):
    """Schema for creating a slot state record."""
    slot_id: str
    state: str
    confidence: float
    ts_utc: datetime
    dwell_s: int = 0
    roi_version: str = "v1"
    model_version: Optional[str] = None


class SlotStateResponse(BaseModel):
    """Schema for slot state response."""
    slot_id: str
    state: str
    confidence: float
    last_change: str

    class Config:
        from_attributes = True


class NodeHealthCreate(BaseModel):
    """Schema for creating a node health record."""
    node_id: str
    ts_utc: datetime
    uptime_s: int
    cpu_percent: float
    cpu_temp_c: float
    mem_used_mb: int
    mem_percent: float
    wifi_rssi_dbm: int
    buffer_depth: int = 0


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


class FrameUploadResponse(BaseModel):
    """Schema for frame upload response."""
    status: str
    frame_id: int
    detections: int
    events: int
    inference_time_ms: float


class SummaryResponse(BaseModel):
    """Schema for parking lot summary response."""
    free_count: int
    occupied_count: int
    unknown_count: int
    total_slots: int
    ts_utc: str
    roi_version: str


class SlotsResponse(BaseModel):
    """Schema for all slots response."""
    slots: List[SlotStateResponse]
    summary: SummaryResponse
