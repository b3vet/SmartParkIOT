# Manual Testing - SmartPark Server

## Prerequisites

1. Server running locally:
   ```bash
   cd server
   source ../devEnv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Supporting services (PostgreSQL, MQTT) running via Docker:
   ```bash
   cd server
   docker compose --env-file .env.docker up postgres mqtt -d
   ```

---

## Basic Health Checks (no authentication required)

### Root Endpoint
```bash
curl http://localhost:8000/
```
**Expected:**
```json
{"service":"SmartPark API","version":"1.0.0","status":"running"}
```

### Health Check
```bash
curl http://localhost:8000/api/v1/health/
```
**Expected:**
```json
{"status":"healthy","service":"SmartPark API","timestamp":"2026-01-12T..."}
```

### Model Info
```bash
curl http://localhost:8000/api/v1/health/model
```
**Expected:**
```json
{"model_path":"ml/yolov8l.pt","device":"cpu","model_version":"..."}
```

### Frame Statistics
```bash
curl http://localhost:8000/api/v1/health/frames
```
**Expected:**
```json
{"period_hours":1,"total_frames":0,"average_inference_ms":0,"average_detections":0}
```

### Node Health (with node_id)
```bash
curl "http://localhost:8000/api/v1/health/node/test-node?hours=1"
```
**Expected:**
```json
{"node_id":"test-node","status":"no_data","records":[]}
```

---

## Parking Summary (no authentication required)

### Get Parking Summary
```bash
curl http://localhost:8000/api/v1/frames/summary
```
**Expected:**
```json
{"free_count":0,"occupied_count":0,"unknown_count":55,"total_slots":55,"ts_utc":"...","roi_version":"v1"}
```

### Get All Slot States
```bash
curl http://localhost:8000/api/v1/frames/slots
```
**Expected:**
```json
{"slots":[{"slot_id":"FASS_001","state":"unknown","confidence":1.0,...}],"summary":{...}}
```

---

## Slot History (no authentication required)

### Recent Slot Changes
```bash
curl http://localhost:8000/api/v1/slots/recent
```
**Expected:**
```json
{"changes":[],"count":0}
```

### Slot Statistics
```bash
curl http://localhost:8000/api/v1/slots/statistics
```
**Expected:**
```json
{"period_hours":24,"total_state_changes":0,"occupied_events":0,"free_events":0,...}
```

### History for Specific Slot
```bash
curl "http://localhost:8000/api/v1/slots/history/FASS_001?hours=24"
```
**Expected:**
```json
{"slot_id":"FASS_001","history":[],"count":0}
```

---

## Frame Upload (requires API key)

### Upload a Test Frame
```bash
curl -X POST http://localhost:8000/api/v1/frames/ \
  -H "X-API-Key: your_secure_api_key" \
  -F "frame=@test1.jpeg" \
  -F "frame_id=1" \
  -F "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -F "node_id=test-node" \
  -F "is_replay=false"
```
**Expected:**
```json
{"status":"success","frame_id":1,"detections":19,"events":0,"inference_time_ms":370.5}
```

### Upload Multiple Frames (to trigger state changes)
The system uses debouncing (3 seconds) to prevent flickering. Send multiple frames to see state transitions:

```bash
# Frame 1
curl -X POST http://localhost:8000/api/v1/frames/ \
  -H "X-API-Key: your_secure_api_key" \
  -F "frame=@test1.jpeg" \
  -F "frame_id=1" \
  -F "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -F "node_id=test-node"

# Frame 2
curl -X POST http://localhost:8000/api/v1/frames/ \
  -H "X-API-Key: your_secure_api_key" \
  -F "frame=@test1.jpeg" \
  -F "frame_id=2" \
  -F "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -F "node_id=test-node"

# Frame 3
curl -X POST http://localhost:8000/api/v1/frames/ \
  -H "X-API-Key: your_secure_api_key" \
  -F "frame=@test1.jpeg" \
  -F "frame_id=3" \
  -F "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -F "node_id=test-node"
```

### Upload Replay Frame (buffered frame from network outage)
```bash
curl -X POST http://localhost:8000/api/v1/frames/ \
  -H "X-API-Key: your_secure_api_key" \
  -F "frame=@test1.jpeg" \
  -F "frame_id=100" \
  -F "timestamp=2026-01-12T10:00:00Z" \
  -F "node_id=test-node" \
  -F "is_replay=true"
```

---

## Quick Test Script

Run all read-only endpoints:

```bash
echo "=== Root ===" && curl -s http://localhost:8000/ | python3 -m json.tool
echo ""
echo "=== Health ===" && curl -s http://localhost:8000/api/v1/health/ | python3 -m json.tool
echo ""
echo "=== Model ===" && curl -s http://localhost:8000/api/v1/health/model | python3 -m json.tool
echo ""
echo "=== Summary ===" && curl -s http://localhost:8000/api/v1/frames/summary | python3 -m json.tool
echo ""
echo "=== Slots ===" && curl -s http://localhost:8000/api/v1/frames/slots | python3 -m json.tool
echo ""
echo "=== Recent Changes ===" && curl -s http://localhost:8000/api/v1/slots/recent | python3 -m json.tool
echo ""
echo "=== Statistics ===" && curl -s http://localhost:8000/api/v1/slots/statistics | python3 -m json.tool
```

---

## Error Responses

### Invalid API Key (401)
```bash
curl -X POST http://localhost:8000/api/v1/frames/ \
  -H "X-API-Key: wrong-key" \
  -F "frame=@test1.jpeg" \
  -F "frame_id=1" \
  -F "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -F "node_id=test-node"
```
**Expected:**
```json
{"detail":"Invalid API key"}
```

### Missing Required Field (422)
```bash
curl -X POST http://localhost:8000/api/v1/frames/ \
  -H "X-API-Key: your_secure_api_key" \
  -F "frame=@test1.jpeg"
```
**Expected:**
```json
{"detail":[{"loc":["body","frame_id"],"msg":"Field required","type":"missing"},...]}
```

---

## Notes

- **API Key**: Update `your_secure_api_key` with the value from `server/.env`
- **Debouncing**: State changes require multiple consistent frames over 3+ seconds
- **Confidence Thresholds**:
  - `enter_threshold = 0.6` (60% overlap to mark occupied)
  - `exit_threshold = 0.4` (below 40% to mark free)
- **Slot States**: `unknown` (initial), `occupied`, `free`
