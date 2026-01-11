# FASS SmartPark-IoT Project Summary

## Overview

**Project Name:** FASS SmartPark-IoT
**Course:** CS 48007 / CS 58007 - Internet of Things Sensing Systems
**Institution:** Sabanci University
**Target Site:** Tuzla Campus - FASS Parking Lot
**Date:** January 2026

---

## 1. Project Aim

The FASS SmartPark-IoT project aims to build a **deployable IoT sensing system** that monitors parking slot occupancy in real-time at the FASS parking lot. The system will:

- **Detect per-slot occupancy** (occupied/free/unknown) using computer vision and machine learning
- **Publish event-driven telemetry** to a cloud server via MQTT
- **Provide a live dashboard** showing parking lot status, historical data, and system health
- **Operate 24/7** with reliability features including store-and-forward buffering and automatic recovery

### Primary Objectives

| Objective | Description |
|-----------|-------------|
| Real-time Monitoring | Detect and report parking slot occupancy changes within 1-2 seconds |
| Cloud-based Inference | Run YOLOv8-large model on cloud server for accurate vehicle detection |
| Operational Reliability | Ensure continuous operation with health monitoring and automatic recovery |
| Visual Dashboard | Provide live parking lot visualization with Grafana |

### Scope

**In-Scope:**
- Single parking lot monitoring (FASS lot)
- All visible parking slots from camera viewpoint
- Per-slot occupancy detection via ML
- Cloud-hosted inference and storage
- Live dashboard with historical analytics
- Health telemetry and remote configuration

**Out-of-Scope:**
- Mobile application
- Reservation/payment systems
- License plate recognition
- Multi-lot campus-wide rollout (unless time permits)

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASS PARKING LOT                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Raspberry Pi 4                                │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │   │
│  │  │ Pi Camera    │───>│ Capture      │───>│ Frame Upload (HTTP)  │  │   │
│  │  │ Module v2/v3 │    │ Service      │    │ Every 1-2 seconds    │  │   │
│  │  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │   │
│  │                                                      │              │   │
│  │  ┌──────────────┐    ┌──────────────┐               │              │   │
│  │  │ Health       │───>│ MQTT Client  │───────────────┼──────────────┼───┼──> Wi-Fi
│  │  │ Monitor      │    │              │               │              │   │
│  │  └──────────────┘    └──────────────┘               │              │   │
│  │                                                      │              │   │
│  │  Power: AC Adapter (5V 3A)                          │              │   │
│  └─────────────────────────────────────────────────────┼──────────────┘   │
└────────────────────────────────────────────────────────┼──────────────────┘
                                                         │
                                                    Wi-Fi│Internet
                                                         │
┌────────────────────────────────────────────────────────┼──────────────────┐
│                         CLOUD SERVER (VPS)             │                  │
│  ┌─────────────────────────────────────────────────────┴───────────────┐  │
│  │                         FastAPI Server                               │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │  │
│  │  │ Frame        │───>│ YOLOv8-large │───>│ Occupancy            │  │  │
│  │  │ Receiver     │    │ Inference    │    │ Processor            │  │  │
│  │  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │  │
│  └─────────────────────────────────────────────────────┼───────────────┘  │
│                                                         │                  │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┴────────────┐   │
│  │ Mosquitto    │    │ PostgreSQL   │<───│ Event Storage            │   │
│  │ MQTT Broker  │    │ Database     │    │ (slot states, telemetry) │   │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         Grafana Dashboard                         │   │
│  │  - Live parking lot map                                          │   │
│  │  - Occupancy history charts                                      │   │
│  │  - Node health metrics                                           │   │
│  │  - Alerts and notifications                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Location | Responsibilities |
|-----------|----------|------------------|
| Pi Camera Module v2/v3 | Edge (Pi) | Capture high-resolution frames of parking lot |
| Capture Service | Edge (Pi) | Frame acquisition, timestamping, compression |
| Frame Uploader | Edge (Pi) | HTTP POST frames to cloud server every 1-2s |
| Health Monitor | Edge (Pi) | Collect and report node metrics (CPU, temp, memory) |
| MQTT Client | Edge (Pi) | Publish health telemetry, receive config updates |
| FastAPI Server | Cloud | Receive frames, coordinate inference pipeline |
| YOLOv8-large | Cloud | Vehicle detection in uploaded frames |
| Occupancy Processor | Cloud | Map detections to slots, debounce, generate events |
| PostgreSQL | Cloud | Store events, telemetry, configuration |
| MQTT Broker | Cloud | Message routing between components |
| Grafana | Cloud | Visualization and alerting |

---

## 3. Development Approach

### Technology Stack

**Edge (Raspberry Pi 4):**
- Python 3.11+
- Picamera2 (Pi Camera interface)
- paho-mqtt (MQTT client)
- requests/httpx (HTTP uploads)
- psutil (system metrics)
- systemd (service management)

**Cloud Server:**
- Python 3.11+ with FastAPI
- Ultralytics YOLOv8-large
- PostgreSQL 15+
- Mosquitto MQTT Broker
- Grafana 10+
- Docker/Docker Compose

### Development Phases

```
Phase 1: Foundation
├── Hardware setup (Pi + Camera)
├── Basic frame capture
├── Cloud infrastructure setup
└── Development environment

Phase 2: Core Pipeline
├── Frame upload service
├── YOLOv8 inference integration
├── Slot mapping and calibration
└── Occupancy detection logic

Phase 3: Telemetry & Storage
├── MQTT integration
├── PostgreSQL schema design
├── Event persistence
└── Health monitoring

Phase 4: Dashboard & Ops
├── Grafana setup
├── Live map visualization
├── Historical charts
└── Alerting configuration

Phase 5: Reliability & Testing
├── Store-and-forward buffering
├── Outage recovery testing
├── Performance optimization
└── Field deployment
```

### Repository Structure

```
fass-smartpark-iot/
├── edge/                          # Raspberry Pi code
│   ├── services/
│   │   ├── capture.py            # Frame capture from Pi Camera
│   │   ├── uploader.py           # HTTP frame upload to server
│   │   ├── health.py             # System health monitoring
│   │   └── config.py             # Configuration management
│   ├── calibration/
│   │   ├── fass_slots_v1.json    # Slot polygon definitions
│   │   └── roi_mask.png          # Region of interest mask
│   ├── configs/
│   │   ├── camera_config.json    # Camera settings
│   │   └── mqtt_config.json      # MQTT connection settings
│   ├── systemd/                   # Service unit files
│   └── requirements.txt
│
├── server/                        # Cloud server code
│   ├── app/
│   │   ├── main.py               # FastAPI application
│   │   ├── inference.py          # YOLOv8 inference engine
│   │   ├── occupancy.py          # Slot occupancy processor
│   │   ├── models.py             # Database models
│   │   └── mqtt_handler.py       # MQTT message handling
│   ├── ml/
│   │   └── yolov8l.pt            # YOLOv8-large weights
│   ├── docker-compose.yaml       # Container orchestration
│   ├── Dockerfile
│   └── requirements.txt
│
├── dashboard/                     # Grafana configuration
│   ├── provisioning/
│   │   ├── dashboards/
│   │   └── datasources/
│   └── dashboards/
│       └── parking_lot.json      # Main dashboard definition
│
├── docs/                          # Documentation
│   ├── ProjectSummary.md
│   └── ProjectImplementationPlan.md
│
└── tests/                         # Test suites
    ├── edge/
    └── server/
```

---

## 4. Execution Plan

### Hardware Requirements

| Item | Specification | Purpose |
|------|---------------|---------|
| Raspberry Pi 4 | 4GB+ RAM, 64GB+ microSD (A2) | Edge compute node |
| Pi Camera Module | v2 or v3 (8MP) | Video capture |
| Power Supply | 5V 3A official adapter | Reliable Pi power |
| Enclosure | No need (indoors) | Protection from elements |
| Mount | Wall/pole mount, vibration-resistant | Stable camera positioning |
| Cloud VPS | 4+ vCPU, 8GB+ RAM, GPU recommended | Server hosting |

### Deployment Steps

1. **Site Survey**
   - Select optimal camera mount position
   - Ensure FOV covers all visible parking slots
   - Note lighting conditions (shadows, glare)
   - Measure Wi-Fi signal strength

2. **Hardware Setup**
   - Assemble Pi with camera module
   - Install in weatherproof enclosure
   - Mount at selected location
   - Connect power and verify Wi-Fi

3. **Calibration**
   - Capture reference frames
   - Define slot polygons (fass_slots_v1.json)
   - Create ROI mask
   - Validate with overlay visualization

4. **Cloud Deployment**
   - Provision VPS with GPU support
   - Deploy Docker containers (FastAPI, PostgreSQL, Mosquitto, Grafana)
   - Configure networking and firewall
   - Verify YOLOv8 inference performance

5. **Integration Testing**
   - End-to-end frame upload and inference
   - MQTT telemetry flow
   - Dashboard data display
   - Simulate occupancy changes

6. **Field Validation**
   - 1-hour stability test
   - Network outage simulation
   - Accuracy evaluation
   - Performance tuning

---

## 5. Key Data Flows

### Frame Processing Pipeline

```
Pi Camera → Capture (JPEG) → HTTP POST → FastAPI → YOLOv8 → Occupancy Logic → PostgreSQL
                                                                    ↓
                                                              Event Generation
                                                                    ↓
                                                                Grafana
```

### MQTT Topic Structure

| Topic | QoS | Direction | Purpose |
|-------|-----|-----------|---------|
| `su/parking/fass/node_health` | 0 | Edge → Cloud | Pi health metrics |
| `su/parking/fass/slot/<slot_id>/state` | 1 | Cloud Internal | Slot state events |
| `su/parking/fass/summary` | 0 | Cloud Internal | Lot summary counts |
| `su/parking/fass/config` | 1 | Cloud → Edge | Configuration updates |

### Event Payload Examples

**Slot State Event:**
```json
{
  "slot_id": "FASS_001",
  "state": "occupied",
  "confidence": 0.94,
  "ts_utc": "2026-01-15T14:30:00Z",
  "dwell_s": 3600,
  "roi_version": "v1",
  "model_version": "yolov8l-1.0"
}
```

**Node Health:**
```json
{
  "uptime_s": 86400,
  "fps": 0.5,
  "cpu_temp_c": 52.3,
  "mem_mb": 512,
  "wifi_rssi_dbm": -45,
  "buffer_depth": 0,
  "ts_utc": "2026-01-15T14:30:00Z"
}
```

---

## 6. Success Criteria

### Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Slot Coverage | 100% of visible slots | Visual verification |
| Detection Accuracy | >95% F1 score | Labeled test set |
| Detection Latency | <5 seconds | Event timestamp vs actual |
| False Toggle Rate | <1 per slot per hour | Event log analysis |

### Operational Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| System Uptime | >99% during daylight | Health telemetry |
| Network Outage Recovery | No lost events after 2-min outage | Replay verification |
| Dashboard Latency | <10 seconds end-to-end | Manual observation |
| 24/7 Operation | Functional under parking lot lighting | Night test |

### Deliverables

- **D1:** Site survey + mount plan + sample frame from final viewpoint
- **D2:** Calibration v1 (all visible slots) + overlay validation
- **D3:** Edge pipeline stable for 60 min + basic metrics
- **D4:** Server inference live + events stored in PostgreSQL
- **D5:** Grafana dashboard live + history + health panel
- **D6:** Reliability features + outage tests + evaluation report

---

## 7. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wi-Fi instability | Lost frames, gaps in data | Store-and-forward buffer, retry logic |
| Low light accuracy | Reduced detection at night | Tune confidence thresholds, rely on lot lighting |
| Server downtime | No inference, data loss | Docker restart policies, database persistence |
| Camera drift/movement | Misaligned slot detection | Periodic calibration check, alert on anomaly |
| Pi thermal throttling | Reduced frame rate | Proper ventilation, heatsinks, temp monitoring |
| YOLOv8 GPU memory | Inference failures | Batch size tuning, model optimization |

---

## 8. Team and Responsibilities

This project is developed as part of the CS 48007/CS 58007 IoT Sensing Systems course. Key responsibilities include:

- **Hardware Integration:** Pi setup, camera mounting, enclosure
- **Edge Software:** Capture service, uploader, health monitoring
- **Server Development:** FastAPI, YOLOv8 integration, database
- **Dashboard:** Grafana configuration, visualizations
- **Testing & Evaluation:** Accuracy metrics, reliability tests

---

*Document Version: 1.0*
*Last Updated: January 2026*
