"""
SQLAlchemy database models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SlotState(Base):
    """Parking slot state changes."""
    __tablename__ = "slot_states"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(String(50), index=True, nullable=False)
    state = Column(String(20), nullable=False)  # occupied, free, unknown
    confidence = Column(Float, nullable=False)
    ts_utc = Column(DateTime, nullable=False, index=True)
    dwell_s = Column(Integer, default=0)
    roi_version = Column(String(20), default="v1")
    model_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class NodeHealth(Base):
    """Edge node health telemetry."""
    __tablename__ = "node_health"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String(50), index=True, nullable=False)
    ts_utc = Column(DateTime, nullable=False, index=True)
    uptime_s = Column(Integer)
    cpu_percent = Column(Float)
    cpu_temp_c = Column(Float)
    mem_used_mb = Column(Integer)
    mem_percent = Column(Float)
    wifi_rssi_dbm = Column(Integer)
    buffer_depth = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class FrameLog(Base):
    """Log of received frames."""
    __tablename__ = "frame_logs"

    id = Column(Integer, primary_key=True, index=True)
    frame_id = Column(Integer, index=True)
    node_id = Column(String(50), index=True)
    timestamp = Column(DateTime, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    inference_time_ms = Column(Float)
    detections_count = Column(Integer)
    is_replay = Column(Boolean, default=False)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
