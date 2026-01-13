# SmartPark IoT v2 - Edge Inference Architecture

This is version 2 of the SmartPark parking lot occupancy detection system.
The key difference from v1 is that **inference runs on the edge node** (Raspberry Pi)
instead of the server.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        EDGE NODE (Raspberry Pi)                  │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌─────────────┐ │
│  │  Camera  │──▶│ YOLOv8m  │──▶│ Occupancy │──▶│ Stats Sender│ │
│  │ Capture  │   │ Inference│   │ Processor │   │  (HTTP/MQTT)│ │
│  └──────────┘   └──────────┘   └───────────┘   └─────────────┘ │
│                                                        │        │
│  ┌──────────┐   ┌──────────┐                          │        │
│  │  Health  │──▶│   MQTT   │──────────────────────────┤        │
│  │ Monitor  │   │  Client  │                          │        │
│  └──────────┘   └──────────┘                          │        │
│                                                        │        │
└────────────────────────────────────────────────────────│────────┘
                                                         │
                              Events & Stats             │
                              (JSON over HTTP)           ▼
┌─────────────────────────────────────────────────────────────────┐
│                           SERVER (VPS)                           │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ FastAPI App  │──▶│  PostgreSQL  │   │     MQTT Broker      │ │
│  │ (Event Recv) │   │   Database   │   │    (Mosquitto)       │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│         │                   │                     │              │
│         └───────────────────┴─────────────────────┘              │
│                                                                  │
│                        Query Endpoints                           │
│                   (Same as v1 for compatibility)                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Changes from v1

| Component | v1 | v2 |
|-----------|----|----|
| Inference | Server (YOLOv8l) | Edge (YOLOv8m) |
| Data sent | JPEG images (~100KB each) | Events only (~1KB) |
| Bandwidth | High (~1MB/minute) | Low (~10KB/minute) |
| Latency | 2-3 seconds | <1 second |
| Offline | Buffers images | Buffers events |
| Server load | High (GPU inference) | Low (storage only) |

## Port Mapping (v1 vs v2)

v2 uses different ports to run alongside v1:

| Service | v1 Port | v2 Port |
|---------|---------|---------|
| API | 8000 | 8001 |
| MQTT | 1883 | 1884 |
| MQTT WebSocket | 9001 | 9002 |
| Grafana | 3000 | 3001 |
| PostgreSQL DB | smartpark | smartpark_v2 |

## Directory Structure

```
v2/
├── edge/                    # Raspberry Pi code
│   ├── main.py             # Main orchestrator
│   ├── services/
│   │   ├── capture.py      # Camera frame capture
│   │   ├── inference.py    # YOLOv8m local inference
│   │   ├── occupancy.py    # Slot state processor
│   │   ├── stats_sender.py # HTTP event sender
│   │   ├── health.py       # System monitoring
│   │   ├── mqtt_client.py  # MQTT telemetry
│   │   └── config_manager.py
│   ├── configs/
│   │   └── settings.json
│   ├── calibration/
│   │   └── fass_slots_v1.json
│   ├── systemd/
│   │   └── smartpark-edge-v2.service
│   └── requirements.txt
│
├── server/                  # Server code
│   ├── app/
│   │   ├── main.py         # FastAPI application
│   │   ├── config.py       # Settings
│   │   ├── models/         # Database & schemas
│   │   ├── routers/        # API endpoints
│   │   └── services/       # MQTT publisher
│   ├── calibration/
│   ├── docker-compose.yaml
│   ├── Dockerfile
│   └── requirements.txt
│
├── tools/                   # Development utilities
│   ├── slot_labeler.py     # Create slot polygons
│   └── overlay_check.py    # Validate calibration
│
├── .env.example
└── README.md
```

## Quick Start

### Server Setup

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   nano .env
   ```

2. Start the services:
   ```bash
   cd server
   docker-compose up -d
   ```

3. Check server health:
   ```bash
   curl http://localhost:8001/api/v1/health/
   ```

### Edge Node Setup

1. Install dependencies on Raspberry Pi:
   ```bash
   cd edge
   pip install -r requirements.txt
   ```

2. Download YOLOv8m model:
   ```bash
   python -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"
   ```

3. Configure settings:
   ```bash
   nano configs/settings.json
   # Update server URL and MQTT host
   ```

4. Create `.env` file:
   ```bash
   echo "API_KEY=your_api_key" > .env
   ```

5. Run manually:
   ```bash
   python main.py
   ```

6. Or install as service:
   ```bash
   sudo cp systemd/smartpark-edge-v2.service /etc/systemd/system/
   sudo systemctl enable smartpark-edge-v2
   sudo systemctl start smartpark-edge-v2
   ```

## API Endpoints

### Event Receiver (v2)

- `POST /api/v2/events` - Receive slot state change events
- `POST /api/v2/summary` - Receive lot summary
- `POST /api/v2/health` - Receive node health
- `POST /api/v2/processing-log` - Receive processing statistics

### Query Endpoints (v1/v2 compatible)

- `GET /api/v1/slots/history/{slot_id}` - Slot state history
- `GET /api/v1/slots/recent` - Recent state changes
- `GET /api/v1/slots/statistics` - Occupancy statistics
- `GET /api/v1/slots/current` - Current lot status
- `GET /api/v1/health/` - Server health
- `GET /api/v1/health/node/{node_id}` - Edge node health
- `GET /api/v1/health/nodes` - List all nodes
- `GET /api/v1/health/processing` - Processing statistics

## MQTT Topics

Same as v1 for compatibility:

- `su/parking/fass/slot/{slot_id}/state` - Per-slot state changes
- `su/parking/fass/summary` - Lot summary
- `su/parking/fass/node_health` - Node health metrics
- `su/parking/fass/config` - Remote configuration updates

## Model Selection

v2 uses YOLOv8m (medium) by default for edge inference. Options:

| Model | Size | Pi 4 Inference | Accuracy |
|-------|------|----------------|----------|
| yolov8n | 6MB | ~100ms | Good |
| yolov8s | 22MB | ~200ms | Better |
| yolov8m | 52MB | ~400ms | Best (recommended) |

To change model, update `configs/settings.json`:
```json
{
  "inference": {
    "model_path": "yolov8s.pt"
  }
}
```
