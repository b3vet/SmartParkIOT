-- SmartPark Database Initialization Script
-- This script is run automatically when PostgreSQL container starts

-- Slot state changes
CREATE TABLE IF NOT EXISTS slot_states (
    id SERIAL PRIMARY KEY,
    slot_id VARCHAR(50) NOT NULL,
    state VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    ts_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    dwell_s INTEGER DEFAULT 0,
    roi_version VARCHAR(20) DEFAULT 'v1',
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_slot_states_slot_id ON slot_states(slot_id);
CREATE INDEX IF NOT EXISTS idx_slot_states_ts_utc ON slot_states(ts_utc);

-- Node health telemetry
CREATE TABLE IF NOT EXISTS node_health (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    ts_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    uptime_s INTEGER,
    cpu_percent FLOAT,
    cpu_temp_c FLOAT,
    mem_used_mb INTEGER,
    mem_percent FLOAT,
    wifi_rssi_dbm INTEGER,
    buffer_depth INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_node_health_node_id ON node_health(node_id);
CREATE INDEX IF NOT EXISTS idx_node_health_ts_utc ON node_health(ts_utc);

-- Frame processing log
CREATE TABLE IF NOT EXISTS frame_logs (
    id SERIAL PRIMARY KEY,
    frame_id INTEGER,
    node_id VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    inference_time_ms FLOAT,
    detections_count INTEGER,
    is_replay BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_frame_logs_node_id ON frame_logs(node_id);
CREATE INDEX IF NOT EXISTS idx_frame_logs_timestamp ON frame_logs(timestamp);

-- Data retention cleanup function
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Keep slot states for 30 days
    DELETE FROM slot_states WHERE ts_utc < NOW() - INTERVAL '30 days';

    -- Keep health data for 7 days
    DELETE FROM node_health WHERE ts_utc < NOW() - INTERVAL '7 days';

    -- Keep frame logs for 7 days
    DELETE FROM frame_logs WHERE timestamp < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smartpark;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smartpark;
