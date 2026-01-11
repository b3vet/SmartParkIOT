# FASS SmartPark-IoT - Project Implementation Plan

## Comprehensive Guide to Building the Smart Parking System

**Project:** FASS SmartPark-IoT
**Course:** CS 48007 / CS 58007 - Internet of Things Sensing Systems
**Institution:** Sabanci University
**Version:** 1.0
**Date:** January 2026

---

## Table of Contents

1. [Prerequisites and Environment Setup](#1-prerequisites-and-environment-setup)
2. [Phase 1: Hardware Setup and Configuration](#2-phase-1-hardware-setup-and-configuration)
3. [Phase 2: Edge Software Development](#3-phase-2-edge-software-development)
4. [Phase 3: Cloud Infrastructure Setup](#4-phase-3-cloud-infrastructure-setup)
5. [Phase 4: Server Application Development](#5-phase-4-server-application-development)
6. [Phase 5: Calibration and Slot Mapping](#6-phase-5-calibration-and-slot-mapping)
7. [Phase 6: Dashboard and Visualization](#7-phase-6-dashboard-and-visualization)
8. [Phase 7: Integration and Testing](#8-phase-7-integration-and-testing)
9. [Phase 8: Reliability and Operations](#9-phase-8-reliability-and-operations)
10. [Phase 9: Deployment and Field Testing](#10-phase-9-deployment-and-field-testing)
11. [API Specifications](#11-api-specifications)
12. [Database Schema](#12-database-schema)
13. [Configuration Reference](#13-configuration-reference)
14. [Troubleshooting Guide](#14-troubleshooting-guide)
15. [Maintenance Procedures](#15-maintenance-procedures)

---

## 1. Prerequisites and Environment Setup

### 1.1 Hardware Requirements

#### Edge Node (Raspberry Pi)

| Component | Specification | Notes |
|-----------|---------------|-------|
| Raspberry Pi | Model 4B, 4GB RAM minimum | 8GB recommended for headroom |
| MicroSD Card | 64GB+ Class 10 A2 | Fast read/write essential |
| Pi Camera | Module v2 (8MP) or v3 (12MP) | CSI interface, not USB |
| Power Supply | Official 5V 3A USB-C | Avoid undervoltage |
| Enclosure | IP65 weatherproof | For outdoor deployment |
| Heatsinks | Aluminum with thermal tape | Prevent throttling |
| Mount | Adjustable wall/pole bracket | Stable positioning |

#### Cloud Server (VPS)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 vCPU | 8 vCPU |
| RAM | 8 GB | 16 GB |
| Storage | 50 GB SSD | 100 GB SSD |
| GPU | None (CPU inference) | NVIDIA GPU (T4 or better) |
| Network | 100 Mbps | 1 Gbps |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### 1.2 Software Prerequisites

#### Development Machine

```bash
# Python 3.11+
python3 --version  # Should be 3.11+

# Git
git --version

# Docker and Docker Compose
docker --version
docker-compose --version

# SSH client for Pi access
ssh -V
```

#### Raspberry Pi OS Setup

```bash
# Download Raspberry Pi OS Lite (64-bit) from:
# https://www.raspberrypi.com/software/operating-systems/

# After flashing SD card and first boot:
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-picamera2 \
    libcamera-apps \
    git \
    vim \
    htop \
    wireless-tools

# Enable camera interface
sudo raspi-config
# Navigate: Interface Options → Camera → Enable

# Configure Wi-Fi (if not done during setup)
sudo raspi-config
# Navigate: System Options → Wireless LAN

# Set timezone
sudo timedatectl set-timezone Europe/Istanbul

# Enable SSH (if not enabled)
sudo systemctl enable ssh
sudo systemctl start ssh
```

### 1.3 Project Repository Initialization

```bash
# On development machine
mkdir fass-smartpark-iot
cd fass-smartpark-iot
git init

# Create directory structure
mkdir -p edge/{services,calibration,configs,systemd,tests}
mkdir -p server/{app,ml,tests}
mkdir -p dashboard/{provisioning/{dashboards,datasources},dashboards}
mkdir -p docs tests

# Create initial files
touch edge/requirements.txt
touch server/requirements.txt
touch server/Dockerfile
touch server/docker-compose.yaml
touch README.md
touch .gitignore

# Initialize .gitignore
cat << 'EOF' > .gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/

# ML models (large files)
*.pt
*.onnx

# Environment
.env
*.env.local

# IDE
.vscode/
.idea/

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
EOF

git add .
git commit -m "Initial project structure"
```

---

## 2. Phase 1: Hardware Setup and Configuration

### 2.1 Raspberry Pi Assembly

#### Step 1: Physical Assembly

1. **Install heatsinks** on CPU, RAM, and USB controller
2. **Attach camera module:**
   - Power off Pi completely
   - Lift CSI connector latch gently
   - Insert ribbon cable (blue side facing USB ports)
   - Press latch down firmly
3. **Insert microSD card** with Raspberry Pi OS
4. **Place in enclosure** (leave open during development)

#### Step 2: Initial Boot and Configuration

```bash
# SSH into Pi (find IP via router or use hostname)
ssh pi@raspberrypi.local
# Default password: raspberry (change immediately!)

# Change default password
passwd

# Update system
sudo apt update && sudo apt full-upgrade -y

# Configure hostname
sudo hostnamectl set-hostname fass-smartpark-edge

# Edit hosts file
sudo nano /etc/hosts
# Change 'raspberrypi' to 'fass-smartpark-edge'

# Reboot to apply
sudo reboot
```

#### Step 3: Camera Verification

```bash
# Test camera detection
libcamera-hello --list-cameras

# Expected output:
# Available cameras
# -----------------
# 0 : imx219 [3280x2464] (/base/soc/i2c0mux/i2c@1/imx219@10)
#     Modes: 'SRGGB10_CSI2P' : 640x480 1640x1232 1920x1080 3280x2464

# Capture test image
libcamera-still -o test.jpg

# View image (transfer to dev machine)
scp pi@fass-smartpark-edge.local:~/test.jpg .
```

### 2.2 Wi-Fi Configuration

```bash
# Check Wi-Fi status
iwconfig wlan0

# Configure Wi-Fi for campus network
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

```
# /etc/wpa_supplicant/wpa_supplicant.conf
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=TR

network={
    ssid="CAMPUS_WIFI_SSID"
    psk="WIFI_PASSWORD"
    key_mgmt=WPA-PSK
    priority=1
}
```

```bash
# Restart networking
sudo systemctl restart wpa_supplicant
sudo systemctl restart dhcpcd

# Verify connection
ping -c 4 google.com
```

### 2.3 System Optimization

```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable hciuart
sudo systemctl disable avahi-daemon

# Increase swap (useful for memory-intensive tasks)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Set GPU memory (reduce since we're not using desktop)
sudo raspi-config
# Navigate: Performance Options → GPU Memory → Set to 128

# Enable watchdog
sudo nano /etc/systemd/system.conf
# Uncomment and set:
# RuntimeWatchdogSec=10
# RebootWatchdogSec=10min

sudo systemctl daemon-reload
```

---

## 3. Phase 2: Edge Software Development

### 3.1 Python Environment Setup

```bash
# On Raspberry Pi
cd ~
mkdir smartpark && cd smartpark

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install \
    picamera2 \
    paho-mqtt \
    requests \
    psutil \
    python-dotenv \
    schedule
```

### 3.2 Edge Service Architecture

```
edge/
├── services/
│   ├── __init__.py
│   ├── capture.py          # Camera frame capture
│   ├── uploader.py         # HTTP frame upload to server
│   ├── health.py           # System health monitoring
│   ├── mqtt_client.py      # MQTT communication
│   └── config_manager.py   # Configuration handling
├── calibration/
│   ├── fass_slots_v1.json  # Slot definitions
│   └── roi_mask.png        # Region of interest
├── configs/
│   ├── settings.json       # Main configuration
│   └── .env                # Secrets (not committed)
├── systemd/
│   ├── smartpark-capture.service
│   └── smartpark-health.service
├── main.py                 # Main entry point
└── requirements.txt
```

### 3.3 Capture Service Implementation

```python
# edge/services/capture.py
"""
Frame capture service using Pi Camera Module.
Captures frames at configurable intervals and queues for upload.
"""

import io
import time
import logging
import threading
from queue import Queue, Full
from datetime import datetime, timezone
from typing import Optional, Callable

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

logger = logging.getLogger(__name__)


class FrameCapture:
    """Manages camera capture with frame queuing."""

    def __init__(
        self,
        resolution: tuple[int, int] = (1920, 1080),
        capture_interval: float = 1.5,
        queue_size: int = 10,
        jpeg_quality: int = 85
    ):
        self.resolution = resolution
        self.capture_interval = capture_interval
        self.jpeg_quality = jpeg_quality
        self.frame_queue: Queue = Queue(maxsize=queue_size)

        self.camera: Optional[Picamera2] = None
        self.running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._last_capture_time: Optional[float] = None

    def initialize(self) -> bool:
        """Initialize the camera."""
        try:
            self.camera = Picamera2()
            config = self.camera.create_still_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                buffer_count=2
            )
            self.camera.configure(config)
            self.camera.start()
            time.sleep(2)  # Allow camera to warm up
            logger.info(f"Camera initialized at {self.resolution}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

    def capture_frame(self) -> Optional[dict]:
        """Capture a single frame and return as bytes with metadata."""
        if not self.camera:
            return None

        try:
            # Capture to numpy array
            frame = self.camera.capture_array()

            # Encode to JPEG
            stream = io.BytesIO()
            from PIL import Image
            img = Image.fromarray(frame)
            img.save(stream, format='JPEG', quality=self.jpeg_quality)
            jpeg_bytes = stream.getvalue()

            timestamp = datetime.now(timezone.utc).isoformat()
            self._frame_count += 1
            self._last_capture_time = time.time()

            return {
                'frame_id': self._frame_count,
                'timestamp': timestamp,
                'data': jpeg_bytes,
                'size': len(jpeg_bytes),
                'resolution': self.resolution
            }
        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            return None

    def start_continuous_capture(self):
        """Start continuous frame capture in background thread."""
        if self.running:
            return

        self.running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self._capture_thread.start()
        logger.info("Continuous capture started")

    def _capture_loop(self):
        """Background capture loop."""
        while self.running:
            start_time = time.time()

            frame = self.capture_frame()
            if frame:
                try:
                    self.frame_queue.put(frame, timeout=1.0)
                except Full:
                    logger.warning("Frame queue full, dropping oldest frame")
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame, timeout=0.1)
                    except:
                        pass

            # Maintain capture interval
            elapsed = time.time() - start_time
            sleep_time = max(0, self.capture_interval - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        """Stop capture and release camera."""
        self.running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=5.0)
        if self.camera:
            self.camera.stop()
            self.camera.close()
        logger.info("Camera capture stopped")

    def get_stats(self) -> dict:
        """Get capture statistics."""
        return {
            'frame_count': self._frame_count,
            'queue_size': self.frame_queue.qsize(),
            'last_capture': self._last_capture_time,
            'running': self.running
        }
```

### 3.4 Frame Uploader Implementation

```python
# edge/services/uploader.py
"""
HTTP frame uploader service.
Uploads captured frames to cloud server for ML inference.
"""

import time
import logging
import threading
import sqlite3
from queue import Queue, Empty
from typing import Optional
from pathlib import Path
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class FrameUploader:
    """Handles frame upload to server with retry and buffering."""

    def __init__(
        self,
        server_url: str,
        api_key: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        buffer_db_path: str = "upload_buffer.db"
    ):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.buffer_db_path = buffer_db_path

        self.running = False
        self._upload_thread: Optional[threading.Thread] = None
        self._session: Optional[requests.Session] = None
        self._stats = {
            'uploaded': 0,
            'failed': 0,
            'buffered': 0,
            'replayed': 0
        }

        self._init_session()
        self._init_buffer_db()

    def _init_session(self):
        """Initialize requests session with retry logic."""
        self._session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def _init_buffer_db(self):
        """Initialize SQLite buffer for offline storage."""
        conn = sqlite3.connect(self.buffer_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS frame_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER,
                timestamp TEXT,
                data BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def upload_frame(self, frame: dict) -> bool:
        """Upload a single frame to server."""
        try:
            response = self._session.post(
                f"{self.server_url}/api/v1/frames",
                files={'frame': ('frame.jpg', frame['data'], 'image/jpeg')},
                data={
                    'frame_id': frame['frame_id'],
                    'timestamp': frame['timestamp'],
                    'node_id': 'fass-edge-01'
                },
                headers={'X-API-Key': self.api_key},
                timeout=self.timeout
            )

            if response.status_code == 200:
                self._stats['uploaded'] += 1
                logger.debug(f"Frame {frame['frame_id']} uploaded successfully")
                return True
            else:
                logger.warning(f"Upload failed: {response.status_code} - {response.text}")
                self._buffer_frame(frame)
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Upload error: {e}")
            self._buffer_frame(frame)
            self._stats['failed'] += 1
            return False

    def _buffer_frame(self, frame: dict):
        """Store frame in local buffer for later retry."""
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO frame_buffer (frame_id, timestamp, data) VALUES (?, ?, ?)',
                (frame['frame_id'], frame['timestamp'], frame['data'])
            )
            conn.commit()
            conn.close()
            self._stats['buffered'] += 1
            logger.info(f"Frame {frame['frame_id']} buffered for retry")
        except Exception as e:
            logger.error(f"Failed to buffer frame: {e}")

    def replay_buffered_frames(self) -> int:
        """Attempt to upload buffered frames."""
        replayed = 0
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, frame_id, timestamp, data FROM frame_buffer ORDER BY id LIMIT 100'
            )
            rows = cursor.fetchall()

            for row in rows:
                db_id, frame_id, timestamp, data = row
                frame = {
                    'frame_id': frame_id,
                    'timestamp': timestamp,
                    'data': data
                }

                if self._try_upload_buffered(frame):
                    cursor.execute('DELETE FROM frame_buffer WHERE id = ?', (db_id,))
                    replayed += 1
                    self._stats['replayed'] += 1
                else:
                    # Increment retry count
                    cursor.execute(
                        'UPDATE frame_buffer SET retry_count = retry_count + 1 WHERE id = ?',
                        (db_id,)
                    )
                    break  # Stop on first failure

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Replay error: {e}")

        return replayed

    def _try_upload_buffered(self, frame: dict) -> bool:
        """Try to upload a buffered frame without re-buffering on failure."""
        try:
            response = self._session.post(
                f"{self.server_url}/api/v1/frames",
                files={'frame': ('frame.jpg', frame['data'], 'image/jpeg')},
                data={
                    'frame_id': frame['frame_id'],
                    'timestamp': frame['timestamp'],
                    'node_id': 'fass-edge-01',
                    'is_replay': True
                },
                headers={'X-API-Key': self.api_key},
                timeout=self.timeout
            )
            return response.status_code == 200
        except:
            return False

    def start_upload_worker(self, frame_queue: Queue):
        """Start background upload worker."""
        self.running = True
        self._upload_thread = threading.Thread(
            target=self._upload_loop,
            args=(frame_queue,),
            daemon=True
        )
        self._upload_thread.start()
        logger.info("Upload worker started")

    def _upload_loop(self, frame_queue: Queue):
        """Background upload loop."""
        replay_interval = 30  # Try replay every 30 seconds
        last_replay = time.time()

        while self.running:
            try:
                # Get frame from queue
                frame = frame_queue.get(timeout=1.0)
                self.upload_frame(frame)

                # Periodically try to replay buffered frames
                if time.time() - last_replay > replay_interval:
                    replayed = self.replay_buffered_frames()
                    if replayed > 0:
                        logger.info(f"Replayed {replayed} buffered frames")
                    last_replay = time.time()

            except Empty:
                # No frames to upload, try replay
                if time.time() - last_replay > replay_interval:
                    self.replay_buffered_frames()
                    last_replay = time.time()

    def stop(self):
        """Stop upload worker."""
        self.running = False
        if self._upload_thread:
            self._upload_thread.join(timeout=5.0)
        logger.info("Upload worker stopped")

    def get_stats(self) -> dict:
        """Get upload statistics."""
        # Count buffered frames
        try:
            conn = sqlite3.connect(self.buffer_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM frame_buffer')
            buffer_count = cursor.fetchone()[0]
            conn.close()
        except:
            buffer_count = -1

        return {
            **self._stats,
            'buffer_count': buffer_count
        }
```

### 3.5 Health Monitoring Service

```python
# edge/services/health.py
"""
System health monitoring service.
Collects and reports Pi metrics via MQTT.
"""

import time
import logging
import threading
import subprocess
from datetime import datetime, timezone
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors system health and reports metrics."""

    def __init__(self, report_interval: float = 15.0):
        self.report_interval = report_interval
        self.running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._start_time = time.time()
        self._callbacks: list = []

    def get_cpu_temperature(self) -> float:
        """Get CPU temperature in Celsius."""
        try:
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Output: temp=45.0'C
            temp_str = result.stdout.strip()
            temp = float(temp_str.replace("temp=", "").replace("'C", ""))
            return temp
        except Exception as e:
            logger.warning(f"Failed to get CPU temp: {e}")
            return -1.0

    def get_wifi_signal(self) -> int:
        """Get WiFi signal strength in dBm."""
        try:
            result = subprocess.run(
                ['iwconfig', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            # Parse: Signal level=-45 dBm
            for line in output.split('\n'):
                if 'Signal level' in line:
                    parts = line.split('Signal level=')
                    if len(parts) > 1:
                        signal = parts[1].split()[0]
                        return int(signal.replace('dBm', ''))
            return -100
        except Exception as e:
            logger.warning(f"Failed to get WiFi signal: {e}")
            return -100

    def collect_metrics(self) -> dict:
        """Collect all system metrics."""
        return {
            'ts_utc': datetime.now(timezone.utc).isoformat(),
            'uptime_s': int(time.time() - self._start_time),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_temp_c': self.get_cpu_temperature(),
            'mem_total_mb': psutil.virtual_memory().total // (1024 * 1024),
            'mem_used_mb': psutil.virtual_memory().used // (1024 * 1024),
            'mem_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'wifi_rssi_dbm': self.get_wifi_signal(),
            'load_avg_1m': psutil.getloadavg()[0],
            'net_bytes_sent': psutil.net_io_counters().bytes_sent,
            'net_bytes_recv': psutil.net_io_counters().bytes_recv
        }

    def add_callback(self, callback):
        """Add callback to be called with metrics."""
        self._callbacks.append(callback)

    def start(self):
        """Start health monitoring."""
        self.running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Health monitor started")

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                metrics = self.collect_metrics()
                for callback in self._callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")

            time.sleep(self.report_interval)

    def stop(self):
        """Stop health monitoring."""
        self.running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Health monitor stopped")
```

### 3.6 MQTT Client Service

```python
# edge/services/mqtt_client.py
"""
MQTT client for telemetry publishing and config updates.
"""

import json
import logging
import threading
from typing import Optional, Callable

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client wrapper for SmartPark edge node."""

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        node_id: str = "fass-edge-01",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.node_id = node_id
        self.username = username
        self.password = password

        self.client = mqtt.Client(client_id=f"smartpark-{node_id}")
        self.connected = False
        self._config_callback: Optional[Callable] = None

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Set credentials if provided
        if username and password:
            self.client.username_pw_set(username, password)

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection event."""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.broker_host}")
            # Subscribe to config topic
            client.subscribe(f"su/parking/fass/config", qos=1)
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection event."""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (rc={rc})")

    def _on_message(self, client, userdata, msg):
        """Handle incoming messages."""
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received message on {msg.topic}: {payload}")

            if 'config' in msg.topic and self._config_callback:
                self._config_callback(payload)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_health(self, metrics: dict):
        """Publish health metrics."""
        topic = f"su/parking/fass/node_health"
        payload = {
            'node_id': self.node_id,
            **metrics
        }
        self.client.publish(topic, json.dumps(payload), qos=0)

    def publish_capture_stats(self, stats: dict):
        """Publish capture statistics."""
        topic = f"su/parking/fass/capture_stats"
        payload = {
            'node_id': self.node_id,
            **stats
        }
        self.client.publish(topic, json.dumps(payload), qos=0)

    def set_config_callback(self, callback: Callable):
        """Set callback for config updates."""
        self._config_callback = callback

    def disconnect(self):
        """Disconnect from broker."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT client disconnected")
```

### 3.7 Main Entry Point

```python
# edge/main.py
"""
Main entry point for SmartPark edge node.
"""

import os
import sys
import json
import signal
import logging
from pathlib import Path

from dotenv import load_dotenv

from services.capture import FrameCapture
from services.uploader import FrameUploader
from services.health import HealthMonitor
from services.mqtt_client import MQTTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/smartpark/edge.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SmartParkEdge:
    """Main application controller."""

    def __init__(self, config_path: str = "configs/settings.json"):
        self.config = self._load_config(config_path)
        self.running = False

        # Initialize services
        self.capture = FrameCapture(
            resolution=tuple(self.config['camera']['resolution']),
            capture_interval=self.config['camera']['capture_interval'],
            jpeg_quality=self.config['camera']['jpeg_quality']
        )

        self.uploader = FrameUploader(
            server_url=self.config['server']['url'],
            api_key=os.getenv('API_KEY', ''),
            timeout=self.config['server']['timeout']
        )

        self.health = HealthMonitor(
            report_interval=self.config['health']['report_interval']
        )

        self.mqtt = MQTTClient(
            broker_host=self.config['mqtt']['host'],
            broker_port=self.config['mqtt']['port'],
            node_id=self.config['node_id'],
            username=os.getenv('MQTT_USER'),
            password=os.getenv('MQTT_PASS')
        )

    def _load_config(self, path: str) -> dict:
        """Load configuration from JSON file."""
        config_file = Path(path)
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        else:
            logger.warning(f"Config file not found: {path}, using defaults")
            return self._default_config()

    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            'node_id': 'fass-edge-01',
            'camera': {
                'resolution': [1920, 1080],
                'capture_interval': 1.5,
                'jpeg_quality': 85
            },
            'server': {
                'url': 'http://server-ip:8000',
                'timeout': 10.0
            },
            'mqtt': {
                'host': 'server-ip',
                'port': 1883
            },
            'health': {
                'report_interval': 15.0
            }
        }

    def start(self):
        """Start all services."""
        logger.info("Starting SmartPark Edge Node...")
        self.running = True

        # Initialize camera
        if not self.capture.initialize():
            logger.error("Failed to initialize camera, exiting")
            sys.exit(1)

        # Start capture
        self.capture.start_continuous_capture()

        # Start uploader
        self.uploader.start_upload_worker(self.capture.frame_queue)

        # Connect MQTT
        self.mqtt.connect()

        # Start health monitor with MQTT publishing
        self.health.add_callback(self.mqtt.publish_health)
        self.health.add_callback(self._log_health)
        self.health.start()

        # Set config callback
        self.mqtt.set_config_callback(self._handle_config_update)

        logger.info("SmartPark Edge Node started successfully")

    def _log_health(self, metrics: dict):
        """Log health metrics locally."""
        logger.info(f"Health: CPU={metrics['cpu_percent']}%, "
                   f"Temp={metrics['cpu_temp_c']}C, "
                   f"WiFi={metrics['wifi_rssi_dbm']}dBm")

    def _handle_config_update(self, config: dict):
        """Handle configuration update from server."""
        logger.info(f"Received config update: {config}")
        # Apply config updates (capture interval, etc.)
        if 'capture_interval' in config:
            self.capture.capture_interval = config['capture_interval']
            logger.info(f"Updated capture interval to {config['capture_interval']}s")

    def stop(self):
        """Stop all services."""
        logger.info("Stopping SmartPark Edge Node...")
        self.running = False

        self.health.stop()
        self.uploader.stop()
        self.capture.stop()
        self.mqtt.disconnect()

        logger.info("SmartPark Edge Node stopped")


def main():
    """Main entry point."""
    # Create log directory
    Path('/var/log/smartpark').mkdir(parents=True, exist_ok=True)

    app = SmartParkEdge()

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start application
    app.start()

    # Keep running
    try:
        while app.running:
            signal.pause()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
```

### 3.8 Systemd Service Files

```ini
# edge/systemd/smartpark-edge.service
[Unit]
Description=SmartPark Edge Node Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/smartpark
Environment=PATH=/home/pi/smartpark/venv/bin:/usr/local/bin:/usr/bin
ExecStart=/home/pi/smartpark/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/home/pi/smartpark /var/log/smartpark

[Install]
WantedBy=multi-user.target
```

```bash
# Install systemd service
sudo cp edge/systemd/smartpark-edge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartpark-edge
sudo systemctl start smartpark-edge

# Check status
sudo systemctl status smartpark-edge
journalctl -u smartpark-edge -f
```

---

## 4. Phase 3: Cloud Infrastructure Setup

### 4.1 VPS Initial Setup

```bash
# SSH into VPS
ssh root@your-vps-ip

# Create non-root user
adduser smartpark
usermod -aG sudo smartpark

# Set up SSH key authentication
mkdir -p /home/smartpark/.ssh
# Copy your public key to authorized_keys

# Disable root SSH login
nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
systemctl restart sshd

# Switch to new user
su - smartpark
```

### 4.2 Docker Installation

```bash
# Install Docker
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker smartpark
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 4.3 GPU Setup (Optional but Recommended)

```bash
# For NVIDIA GPU (if available)
# Install NVIDIA drivers
sudo apt install -y nvidia-driver-535

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU access in Docker
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### 4.4 Docker Compose Configuration

```yaml
# server/docker-compose.yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: smartpark-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://smartpark:${DB_PASSWORD}@postgres:5432/smartpark
      - MQTT_HOST=mqtt
      - MQTT_PORT=1883
      - API_KEY=${API_KEY}
    volumes:
      - ./ml:/app/ml:ro
      - frame_uploads:/app/uploads
    depends_on:
      - postgres
      - mqtt
    # Uncomment for GPU support:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: smartpark-postgres
    environment:
      - POSTGRES_USER=smartpark
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=smartpark
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    restart: unless-stopped

  mqtt:
    image: eclipse-mosquitto:2
    container_name: smartpark-mqtt
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/config:/mosquitto/config:ro
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.2.0
    container_name: smartpark-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./dashboard/provisioning:/etc/grafana/provisioning:ro
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
  mosquitto_data:
  mosquitto_log:
  grafana_data:
  frame_uploads:
```

### 4.5 Environment Configuration

```bash
# server/.env
DB_PASSWORD=your_secure_db_password
API_KEY=your_secure_api_key
GRAFANA_PASSWORD=your_grafana_admin_password
```

### 4.6 Mosquitto Configuration

```conf
# server/mosquitto/config/mosquitto.conf
listener 1883
protocol mqtt

# Authentication (optional for initial setup)
allow_anonymous true

# For production, enable authentication:
# allow_anonymous false
# password_file /mosquitto/config/passwd

persistence true
persistence_location /mosquitto/data/

log_dest file /mosquitto/log/mosquitto.log
log_type all
```

---

## 5. Phase 4: Server Application Development

### 5.1 FastAPI Application Structure

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── dependencies.py      # Dependency injection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py      # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── frames.py        # Frame upload endpoints
│   │   ├── slots.py         # Slot state endpoints
│   │   └── health.py        # Health check endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── inference.py     # YOLOv8 inference
│   │   ├── occupancy.py     # Occupancy detection
│   │   └── mqtt_publisher.py
│   └── utils/
│       └── __init__.py
├── ml/
│   └── yolov8l.pt           # YOLOv8-large weights
├── tests/
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt
```

### 5.2 Server Requirements

```txt
# server/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
paho-mqtt==1.6.1
ultralytics==8.1.0
opencv-python-headless==4.9.0.80
numpy==1.26.3
Pillow==10.2.0
aiofiles==23.2.1
```

### 5.3 FastAPI Main Application

```python
# server/app/main.py
"""
FastAPI application for SmartPark server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import frames, slots, health
from app.services.inference import InferenceEngine
from app.services.mqtt_publisher import MQTTPublisher
from app.models.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting SmartPark Server...")

    # Initialize database
    init_db()

    # Initialize inference engine
    app.state.inference_engine = InferenceEngine(
        model_path=settings.model_path,
        device=settings.inference_device
    )

    # Initialize MQTT publisher
    app.state.mqtt_publisher = MQTTPublisher(
        host=settings.mqtt_host,
        port=settings.mqtt_port
    )
    app.state.mqtt_publisher.connect()

    logger.info("SmartPark Server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down SmartPark Server...")
    app.state.mqtt_publisher.disconnect()


app = FastAPI(
    title="SmartPark API",
    description="FASS Parking Lot Occupancy Detection API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(frames.router, prefix="/api/v1/frames", tags=["frames"])
app.include_router(slots.router, prefix="/api/v1/slots", tags=["slots"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SmartPark API",
        "version": "1.0.0",
        "status": "running"
    }
```

### 5.4 Configuration Management

```python
# server/app/config.py
"""
Application configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://smartpark:password@localhost:5432/smartpark"

    # MQTT
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    # API Security
    api_key: str = "development-key"

    # Inference
    model_path: str = "ml/yolov8l.pt"
    inference_device: str = "cpu"  # or "cuda:0" for GPU
    confidence_threshold: float = 0.5

    # Slots
    slots_config_path: str = "calibration/fass_slots_v1.json"

    # Debounce
    debounce_seconds: float = 3.0
    enter_threshold: float = 0.6
    exit_threshold: float = 0.4

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

### 5.5 Database Models

```python
# server/app/models/database.py
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
```

### 5.6 YOLOv8 Inference Engine

```python
# server/app/services/inference.py
"""
YOLOv8 inference engine for vehicle detection.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class InferenceEngine:
    """YOLOv8-based vehicle detection engine."""

    # Vehicle class IDs in COCO dataset
    VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

    def __init__(
        self,
        model_path: str = "yolov8l.pt",
        device: str = "cpu",
        confidence_threshold: float = 0.5
    ):
        self.model_path = model_path
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.model: Optional[YOLO] = None

        self._load_model()

    def _load_model(self):
        """Load YOLOv8 model."""
        try:
            logger.info(f"Loading YOLOv8 model from {self.model_path}")
            self.model = YOLO(self.model_path)

            # Warm up model
            dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model.predict(dummy_input, device=self.device, verbose=False)

            logger.info(f"Model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def detect_vehicles(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect vehicles in an image.

        Args:
            image: PIL Image to process

        Returns:
            Dictionary containing:
            - detections: List of detected vehicles with bboxes
            - inference_time_ms: Time taken for inference
            - image_size: (width, height) of input image
        """
        start_time = time.time()

        # Convert to numpy array
        img_array = np.array(image)

        # Run inference
        results = self.model.predict(
            img_array,
            device=self.device,
            conf=self.confidence_threshold,
            classes=list(self.VEHICLE_CLASSES.keys()),
            verbose=False
        )

        inference_time_ms = (time.time() - start_time) * 1000

        # Process detections
        detections = []
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            for i in range(len(boxes)):
                box = boxes[i]
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

                detections.append({
                    'class_id': class_id,
                    'class_name': self.VEHICLE_CLASSES.get(class_id, 'vehicle'),
                    'confidence': confidence,
                    'bbox': {
                        'x1': bbox[0],
                        'y1': bbox[1],
                        'x2': bbox[2],
                        'y2': bbox[3]
                    },
                    'center': {
                        'x': (bbox[0] + bbox[2]) / 2,
                        'y': (bbox[1] + bbox[3]) / 2
                    }
                })

        return {
            'detections': detections,
            'inference_time_ms': inference_time_ms,
            'image_size': (image.width, image.height),
            'model_version': f"yolov8l-{self.model_path.split('/')[-1]}"
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'model_path': self.model_path,
            'device': self.device,
            'confidence_threshold': self.confidence_threshold,
            'vehicle_classes': self.VEHICLE_CLASSES
        }
```

### 5.7 Occupancy Processing Service

```python
# server/app/services/occupancy.py
"""
Parking slot occupancy processor.
Maps vehicle detections to parking slots with debouncing.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)


@dataclass
class SlotState:
    """State tracking for a single slot."""
    slot_id: str
    polygon: Polygon
    current_state: str = "unknown"  # occupied, free, unknown
    confidence: float = 0.0
    last_change: float = field(default_factory=time.time)
    pending_state: Optional[str] = None
    pending_since: Optional[float] = None
    dwell_start: float = field(default_factory=time.time)


class OccupancyProcessor:
    """Processes vehicle detections to determine slot occupancy."""

    def __init__(
        self,
        slots_config_path: str,
        debounce_seconds: float = 3.0,
        enter_threshold: float = 0.6,
        exit_threshold: float = 0.4
    ):
        self.debounce_seconds = debounce_seconds
        self.enter_threshold = enter_threshold
        self.exit_threshold = exit_threshold

        self.slots: Dict[str, SlotState] = {}
        self._load_slots(slots_config_path)
        self._roi_version = "v1"

    def _load_slots(self, config_path: str):
        """Load slot definitions from JSON file."""
        try:
            with open(config_path) as f:
                config = json.load(f)

            self._roi_version = config.get('roi_version', 'v1')

            for slot_def in config.get('slots', []):
                slot_id = slot_def['slot_id']
                points = slot_def['poly']
                polygon = Polygon(points)

                self.slots[slot_id] = SlotState(
                    slot_id=slot_id,
                    polygon=polygon
                )

            logger.info(f"Loaded {len(self.slots)} slots from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load slots config: {e}")
            raise

    def process_detections(
        self,
        detections: List[Dict],
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """
        Process vehicle detections and update slot states.

        Args:
            detections: List of vehicle detections from inference
            timestamp: Frame timestamp

        Returns:
            List of state change events to publish
        """
        current_time = time.time()
        events = []

        # Check which slots contain vehicle centers
        slot_occupancy = {slot_id: False for slot_id in self.slots}
        slot_confidence = {slot_id: 0.0 for slot_id in self.slots}

        for detection in detections:
            center = Point(detection['center']['x'], detection['center']['y'])

            for slot_id, slot_state in self.slots.items():
                if slot_state.polygon.contains(center):
                    slot_occupancy[slot_id] = True
                    slot_confidence[slot_id] = max(
                        slot_confidence[slot_id],
                        detection['confidence']
                    )

        # Update slot states with debouncing
        for slot_id, is_occupied in slot_occupancy.items():
            slot = self.slots[slot_id]
            new_state = "occupied" if is_occupied else "free"
            confidence = slot_confidence[slot_id] if is_occupied else 1.0 - slot_confidence.get(slot_id, 0)

            event = self._update_slot_state(
                slot, new_state, confidence, timestamp, current_time
            )
            if event:
                events.append(event)

        return events

    def _update_slot_state(
        self,
        slot: SlotState,
        new_state: str,
        confidence: float,
        timestamp: datetime,
        current_time: float
    ) -> Optional[Dict[str, Any]]:
        """Update slot state with hysteresis and debouncing."""

        # Apply hysteresis thresholds
        if slot.current_state == "free" and new_state == "occupied":
            if confidence < self.enter_threshold:
                new_state = "free"  # Not confident enough to change
        elif slot.current_state == "occupied" and new_state == "free":
            if confidence < self.exit_threshold:
                new_state = "occupied"  # Not confident enough to change

        # Check if state is changing
        if new_state != slot.current_state:
            # Start or continue debounce period
            if slot.pending_state != new_state:
                slot.pending_state = new_state
                slot.pending_since = current_time
                slot.confidence = confidence
            elif current_time - slot.pending_since >= self.debounce_seconds:
                # Debounce complete, confirm state change
                dwell_s = int(current_time - slot.dwell_start)

                event = {
                    'slot_id': slot.slot_id,
                    'state': new_state,
                    'previous_state': slot.current_state,
                    'confidence': confidence,
                    'ts_utc': timestamp.isoformat(),
                    'dwell_s': dwell_s,
                    'roi_version': self._roi_version
                }

                # Update slot state
                slot.current_state = new_state
                slot.last_change = current_time
                slot.dwell_start = current_time
                slot.pending_state = None
                slot.pending_since = None

                logger.info(f"Slot {slot.slot_id}: {event['previous_state']} -> {new_state}")
                return event
        else:
            # State matches, clear pending
            slot.pending_state = None
            slot.pending_since = None
            slot.confidence = confidence

        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get current lot summary."""
        free_count = sum(1 for s in self.slots.values() if s.current_state == "free")
        occupied_count = sum(1 for s in self.slots.values() if s.current_state == "occupied")
        unknown_count = sum(1 for s in self.slots.values() if s.current_state == "unknown")

        return {
            'free_count': free_count,
            'occupied_count': occupied_count,
            'unknown_count': unknown_count,
            'total_slots': len(self.slots),
            'ts_utc': datetime.now(timezone.utc).isoformat(),
            'roi_version': self._roi_version
        }

    def get_all_states(self) -> List[Dict[str, Any]]:
        """Get current state of all slots."""
        return [
            {
                'slot_id': slot.slot_id,
                'state': slot.current_state,
                'confidence': slot.confidence,
                'last_change': datetime.fromtimestamp(slot.last_change, tz=timezone.utc).isoformat()
            }
            for slot in self.slots.values()
        ]
```

### 5.8 Frame Upload Router

```python
# server/app/routers/frames.py
"""
Frame upload and processing endpoints.
"""

import io
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db, FrameLog, SlotState as SlotStateDB
from app.services.occupancy import OccupancyProcessor

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize occupancy processor
occupancy_processor = OccupancyProcessor(
    slots_config_path=settings.slots_config_path,
    debounce_seconds=settings.debounce_seconds,
    enter_threshold=settings.enter_threshold,
    exit_threshold=settings.exit_threshold
)


def verify_api_key(request: Request):
    """Verify API key from header."""
    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/")
async def upload_frame(
    request: Request,
    frame: UploadFile = File(...),
    frame_id: int = Form(...),
    timestamp: str = Form(...),
    node_id: str = Form(...),
    is_replay: bool = Form(False),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """
    Upload a frame for processing.

    - Receives JPEG frame from edge node
    - Runs YOLOv8 inference
    - Maps detections to parking slots
    - Publishes state changes via MQTT
    """
    try:
        # Read image
        contents = await frame.read()
        image = Image.open(io.BytesIO(contents))

        # Parse timestamp
        frame_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Run inference
        inference_engine = request.app.state.inference_engine
        detection_result = inference_engine.detect_vehicles(image)

        # Process occupancy
        events = occupancy_processor.process_detections(
            detection_result['detections'],
            frame_timestamp
        )

        # Store events in database
        for event in events:
            slot_state = SlotStateDB(
                slot_id=event['slot_id'],
                state=event['state'],
                confidence=event['confidence'],
                ts_utc=frame_timestamp,
                dwell_s=event.get('dwell_s', 0),
                roi_version=event.get('roi_version', 'v1'),
                model_version=detection_result.get('model_version')
            )
            db.add(slot_state)

        # Log frame
        frame_log = FrameLog(
            frame_id=frame_id,
            node_id=node_id,
            timestamp=frame_timestamp,
            inference_time_ms=detection_result['inference_time_ms'],
            detections_count=len(detection_result['detections']),
            is_replay=is_replay
        )
        db.add(frame_log)
        db.commit()

        # Publish events via MQTT
        mqtt_publisher = request.app.state.mqtt_publisher
        for event in events:
            mqtt_publisher.publish_slot_state(event)

        # Publish summary periodically
        summary = occupancy_processor.get_summary()
        mqtt_publisher.publish_summary(summary)

        return {
            "status": "success",
            "frame_id": frame_id,
            "detections": len(detection_result['detections']),
            "events": len(events),
            "inference_time_ms": detection_result['inference_time_ms']
        }

    except Exception as e:
        logger.error(f"Frame processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary():
    """Get current parking lot summary."""
    return occupancy_processor.get_summary()


@router.get("/slots")
async def get_all_slots():
    """Get current state of all slots."""
    return {
        "slots": occupancy_processor.get_all_states(),
        "summary": occupancy_processor.get_summary()
    }
```

### 5.9 Dockerfile

```dockerfile
# server/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY calibration/ calibration/

# Download YOLOv8 model if not present
RUN python -c "from ultralytics import YOLO; YOLO('yolov8l.pt')" || true

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 6. Phase 5: Calibration and Slot Mapping

### 6.1 Capturing Reference Frames

```bash
# On Raspberry Pi, capture reference frames
# Run at different times of day to capture various lighting conditions

# Morning (7-9 AM)
libcamera-still -o reference_morning.jpg --width 1920 --height 1080

# Midday (12-2 PM)
libcamera-still -o reference_midday.jpg --width 1920 --height 1080

# Afternoon with shadows (4-6 PM)
libcamera-still -o reference_afternoon.jpg --width 1920 --height 1080

# Transfer to development machine
scp pi@fass-smartpark-edge.local:~/reference_*.jpg .
```

### 6.2 Slot Polygon Definition Tool

```python
# tools/slot_labeler.py
"""
Interactive tool to define parking slot polygons.
"""

import json
import cv2
import numpy as np
from pathlib import Path


class SlotLabeler:
    def __init__(self, image_path: str, output_path: str = "fass_slots_v1.json"):
        self.image = cv2.imread(image_path)
        self.output_path = output_path
        self.slots = []
        self.current_polygon = []
        self.slot_counter = 1

        cv2.namedWindow("Slot Labeler", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Slot Labeler", self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_polygon.append([x, y])
            self.redraw()
        elif event == cv2.EVENT_RBUTTONDOWN:
            if len(self.current_polygon) >= 4:
                self.save_current_polygon()
            self.current_polygon = []
            self.redraw()

    def save_current_polygon(self):
        slot_id = f"FASS_{self.slot_counter:03d}"
        self.slots.append({
            "slot_id": slot_id,
            "poly": self.current_polygon.copy()
        })
        print(f"Saved {slot_id} with {len(self.current_polygon)} points")
        self.slot_counter += 1

    def redraw(self):
        display = self.image.copy()

        # Draw saved slots
        for slot in self.slots:
            pts = np.array(slot['poly'], np.int32)
            cv2.polylines(display, [pts], True, (0, 255, 0), 2)
            center = pts.mean(axis=0).astype(int)
            cv2.putText(display, slot['slot_id'], tuple(center),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Draw current polygon
        if self.current_polygon:
            pts = np.array(self.current_polygon, np.int32)
            cv2.polylines(display, [pts], False, (0, 0, 255), 2)
            for pt in self.current_polygon:
                cv2.circle(display, tuple(pt), 5, (0, 0, 255), -1)

        cv2.imshow("Slot Labeler", display)

    def run(self):
        print("Instructions:")
        print("  Left-click: Add point to current polygon")
        print("  Right-click: Save polygon and start new (need 4+ points)")
        print("  's': Save to file")
        print("  'u': Undo last slot")
        print("  'q': Quit")

        self.redraw()

        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self.save_to_file()
            elif key == ord('u'):
                if self.slots:
                    removed = self.slots.pop()
                    self.slot_counter -= 1
                    print(f"Removed {removed['slot_id']}")
                    self.redraw()

        cv2.destroyAllWindows()

    def save_to_file(self):
        output = {
            "roi_version": "v1",
            "image_size": [self.image.shape[1], self.image.shape[0]],
            "slots": self.slots
        }
        with open(self.output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Saved {len(self.slots)} slots to {self.output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python slot_labeler.py <image_path>")
        sys.exit(1)

    labeler = SlotLabeler(sys.argv[1])
    labeler.run()
```

### 6.3 Slot Configuration Format

```json
// calibration/fass_slots_v1.json
{
  "roi_version": "v1",
  "image_size": [1920, 1080],
  "created_at": "2026-01-15T10:00:00Z",
  "created_by": "calibration_tool",
  "notes": "Initial calibration from midday reference frame",
  "slots": [
    {
      "slot_id": "FASS_001",
      "poly": [[100, 200], [250, 200], [250, 350], [100, 350]],
      "row": "A",
      "position": 1
    },
    {
      "slot_id": "FASS_002",
      "poly": [[260, 200], [410, 200], [410, 350], [260, 350]],
      "row": "A",
      "position": 2
    }
    // ... more slots
  ]
}
```

### 6.4 Overlay Validation Tool

```python
# tools/overlay_check.py
"""
Validate calibration by overlaying slots on live feed.
"""

import json
import cv2
import numpy as np
from picamera2 import Picamera2


def validate_overlay(slots_path: str):
    """Display live camera feed with slot overlays."""

    # Load slots
    with open(slots_path) as f:
        config = json.load(f)

    # Initialize camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(
        main={"size": tuple(config['image_size'])}
    ))
    picam2.start()

    print("Press 'q' to quit, 's' to save snapshot")

    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Draw slots
        for slot in config['slots']:
            pts = np.array(slot['poly'], np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

            # Draw slot ID
            center = pts.mean(axis=0).astype(int)
            cv2.putText(frame, slot['slot_id'], tuple(center),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Draw info
        cv2.putText(frame, f"ROI Version: {config['roi_version']}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"Slots: {len(config['slots'])}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Calibration Overlay", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("overlay_snapshot.jpg", frame)
            print("Saved overlay_snapshot.jpg")

    picam2.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    validate_overlay("calibration/fass_slots_v1.json")
```

---

## 7. Phase 6: Dashboard and Visualization

### 7.1 Grafana Data Source Configuration

```yaml
# dashboard/provisioning/datasources/datasources.yaml
apiVersion: 1

datasources:
  - name: PostgreSQL
    type: postgres
    url: postgres:5432
    database: smartpark
    user: smartpark
    secureJsonData:
      password: ${DB_PASSWORD}
    jsonData:
      sslmode: disable
      maxOpenConns: 10
      maxIdleConns: 5
      connMaxLifetime: 14400
    isDefault: true
```

### 7.2 Grafana Dashboard Definition

```json
// dashboard/dashboards/parking_overview.json
{
  "dashboard": {
    "title": "FASS SmartPark - Parking Overview",
    "uid": "fass-parking-overview",
    "timezone": "browser",
    "refresh": "5s",
    "panels": [
      {
        "title": "Current Occupancy",
        "type": "stat",
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
        "targets": [
          {
            "rawSql": "SELECT COUNT(*) FILTER (WHERE state = 'occupied') as value FROM (SELECT DISTINCT ON (slot_id) slot_id, state FROM slot_states ORDER BY slot_id, ts_utc DESC) s",
            "format": "table"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "mode": "percentage",
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 70},
                {"color": "red", "value": 90}
              ]
            }
          }
        }
      },
      {
        "title": "Free Spaces",
        "type": "stat",
        "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
        "targets": [
          {
            "rawSql": "SELECT COUNT(*) FILTER (WHERE state = 'free') as value FROM (SELECT DISTINCT ON (slot_id) slot_id, state FROM slot_states ORDER BY slot_id, ts_utc DESC) s",
            "format": "table"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {"mode": "fixed", "fixedColor": "green"}
          }
        }
      },
      {
        "title": "Occupancy Over Time",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 4, "w": 24, "h": 8},
        "targets": [
          {
            "rawSql": "SELECT time_bucket('5 minutes', ts_utc) AS time, COUNT(*) FILTER (WHERE state = 'occupied') as occupied, COUNT(*) FILTER (WHERE state = 'free') as free FROM slot_states WHERE ts_utc > NOW() - INTERVAL '24 hours' GROUP BY 1 ORDER BY 1",
            "format": "time_series"
          }
        ]
      },
      {
        "title": "Node Health - CPU Temperature",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 12, "w": 12, "h": 6},
        "targets": [
          {
            "rawSql": "SELECT ts_utc as time, cpu_temp_c FROM node_health WHERE ts_utc > NOW() - INTERVAL '1 hour' ORDER BY ts_utc",
            "format": "time_series"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "celsius",
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 60},
                {"color": "red", "value": 75}
              ]
            }
          }
        }
      },
      {
        "title": "WiFi Signal Strength",
        "type": "gauge",
        "gridPos": {"x": 12, "y": 12, "w": 6, "h": 6},
        "targets": [
          {
            "rawSql": "SELECT wifi_rssi_dbm as value FROM node_health ORDER BY ts_utc DESC LIMIT 1",
            "format": "table"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "dBm",
            "min": -100,
            "max": -30,
            "thresholds": {
              "steps": [
                {"color": "red", "value": -100},
                {"color": "yellow", "value": -70},
                {"color": "green", "value": -50}
              ]
            }
          }
        }
      },
      {
        "title": "Recent State Changes",
        "type": "table",
        "gridPos": {"x": 0, "y": 18, "w": 24, "h": 6},
        "targets": [
          {
            "rawSql": "SELECT slot_id, state, confidence, ts_utc, dwell_s FROM slot_states ORDER BY ts_utc DESC LIMIT 20",
            "format": "table"
          }
        ]
      }
    ]
  }
}
```

### 7.3 Dashboard Provisioning

```yaml
# dashboard/provisioning/dashboards/dashboards.yaml
apiVersion: 1

providers:
  - name: 'SmartPark Dashboards'
    orgId: 1
    folder: 'SmartPark'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboards
```

---

## 8. Phase 7: Integration and Testing

### 8.1 Unit Tests

```python
# tests/server/test_inference.py
"""
Unit tests for inference engine.
"""

import pytest
from PIL import Image
import numpy as np
from app.services.inference import InferenceEngine


@pytest.fixture
def inference_engine():
    return InferenceEngine(model_path="yolov8l.pt", device="cpu")


def test_detect_empty_image(inference_engine):
    """Test detection on empty parking lot image."""
    # Create blank image
    image = Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))
    result = inference_engine.detect_vehicles(image)

    assert 'detections' in result
    assert 'inference_time_ms' in result
    assert len(result['detections']) == 0


def test_detection_format(inference_engine):
    """Test detection output format."""
    image = Image.fromarray(np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8))
    result = inference_engine.detect_vehicles(image)

    for detection in result['detections']:
        assert 'class_id' in detection
        assert 'confidence' in detection
        assert 'bbox' in detection
        assert 'center' in detection
```

### 8.2 Integration Tests

```python
# tests/server/test_api.py
"""
API integration tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "SmartPark API"


def test_summary_endpoint(client):
    """Test summary endpoint."""
    response = client.get("/api/v1/frames/summary")
    assert response.status_code == 200
    assert 'free_count' in response.json()
    assert 'occupied_count' in response.json()


def test_unauthorized_upload(client):
    """Test upload without API key."""
    response = client.post("/api/v1/frames/")
    assert response.status_code == 401
```

### 8.3 End-to-End Test Script

```python
# tests/e2e_test.py
"""
End-to-end system test.
"""

import time
import requests
import json
from pathlib import Path


def test_full_pipeline():
    """Test complete frame upload and processing pipeline."""

    SERVER_URL = "http://localhost:8000"
    API_KEY = "test-api-key"

    # Load test image
    test_image_path = Path("tests/fixtures/test_parking.jpg")
    if not test_image_path.exists():
        print("Test image not found, skipping E2E test")
        return

    # Upload frame
    with open(test_image_path, 'rb') as f:
        response = requests.post(
            f"{SERVER_URL}/api/v1/frames",
            files={'frame': ('frame.jpg', f, 'image/jpeg')},
            data={
                'frame_id': 1,
                'timestamp': '2026-01-15T10:00:00Z',
                'node_id': 'test-node'
            },
            headers={'X-API-Key': API_KEY}
        )

    assert response.status_code == 200, f"Upload failed: {response.text}"
    result = response.json()
    print(f"Upload result: {json.dumps(result, indent=2)}")

    # Check summary
    response = requests.get(f"{SERVER_URL}/api/v1/frames/summary")
    assert response.status_code == 200
    summary = response.json()
    print(f"Summary: {json.dumps(summary, indent=2)}")

    # Check slots
    response = requests.get(f"{SERVER_URL}/api/v1/frames/slots")
    assert response.status_code == 200
    slots = response.json()
    print(f"Slots: {json.dumps(slots, indent=2)}")

    print("E2E test passed!")


if __name__ == "__main__":
    test_full_pipeline()
```

---

## 9. Phase 8: Reliability and Operations

### 9.1 Store-and-Forward Implementation

The frame uploader (Section 3.4) already implements store-and-forward using SQLite. Key features:

- Frames buffered locally on upload failure
- Automatic replay on reconnection
- Deduplication by frame_id and timestamp
- Configurable retry limits

### 9.2 Systemd Watchdog Configuration

```ini
# Additional watchdog configuration for edge service
# edge/systemd/smartpark-edge.service

[Service]
# ... previous settings ...

# Watchdog settings
WatchdogSec=60
NotifyAccess=main

# Resource limits
MemoryMax=512M
CPUQuota=80%

# Restart behavior
RestartSec=10
RestartPreventExitStatus=0
SuccessExitStatus=0

[Install]
WantedBy=multi-user.target
```

### 9.3 Health Check Script

```bash
#!/bin/bash
# scripts/health_check.sh
# Run periodically via cron to monitor system health

LOG_FILE="/var/log/smartpark/health_check.log"
ALERT_TEMP=75
ALERT_MEM=90

# Get metrics
CPU_TEMP=$(vcgencmd measure_temp | grep -oP '\d+\.\d+')
MEM_PERCENT=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
WIFI_SIGNAL=$(iwconfig wlan0 2>/dev/null | grep -oP 'Signal level=\K-?\d+')
SERVICE_STATUS=$(systemctl is-active smartpark-edge)

# Log metrics
echo "$(date -Iseconds) temp=$CPU_TEMP mem=$MEM_PERCENT wifi=$WIFI_SIGNAL service=$SERVICE_STATUS" >> $LOG_FILE

# Check thresholds
if (( $(echo "$CPU_TEMP > $ALERT_TEMP" | bc -l) )); then
    echo "ALERT: CPU temperature high: ${CPU_TEMP}C" | logger -t smartpark
fi

if [ "$MEM_PERCENT" -gt "$ALERT_MEM" ]; then
    echo "ALERT: Memory usage high: ${MEM_PERCENT}%" | logger -t smartpark
fi

if [ "$SERVICE_STATUS" != "active" ]; then
    echo "ALERT: Service not running, attempting restart" | logger -t smartpark
    sudo systemctl restart smartpark-edge
fi
```

### 9.4 Log Rotation Configuration

```conf
# /etc/logrotate.d/smartpark
/var/log/smartpark/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 pi pi
    postrotate
        systemctl reload smartpark-edge > /dev/null 2>&1 || true
    endscript
}
```

---

## 10. Phase 9: Deployment and Field Testing

### 10.1 Pre-Deployment Checklist

```markdown
## Hardware Checklist
- [ ] Pi Camera ribbon cable secure
- [ ] Heatsinks properly attached
- [ ] MicroSD card firmly inserted
- [ ] Power supply tested (no undervoltage warnings)
- [ ] Enclosure seals intact
- [ ] Mount hardware complete

## Software Checklist
- [ ] Latest code deployed to Pi
- [ ] Configuration files updated with production values
- [ ] API keys and credentials set in .env
- [ ] Systemd services enabled
- [ ] Log rotation configured

## Network Checklist
- [ ] Wi-Fi credentials configured
- [ ] Server URL reachable from Pi
- [ ] MQTT broker accessible
- [ ] NTP time synchronized

## Calibration Checklist
- [ ] Reference frames captured
- [ ] Slot polygons defined for all visible slots
- [ ] Overlay validation passed
- [ ] Configuration uploaded to server
```

### 10.2 Field Installation Procedure

```markdown
## Installation Steps

1. **Site Preparation**
   - Confirm mounting location
   - Verify power outlet accessibility
   - Test Wi-Fi signal strength at location

2. **Mount Installation**
   - Secure mount bracket to wall/pole
   - Ensure vibration-free attachment
   - Aim camera at parking lot
   - Lock all adjustment screws

3. **Device Setup**
   - Connect camera to Pi (power off)
   - Secure Pi in enclosure
   - Route power cable with drip loop
   - Connect power supply

4. **Initial Verification**
   - Wait for boot (60-90 seconds)
   - Check Wi-Fi connection
   - Verify service status via SSH
   - Check Grafana for incoming data

5. **Calibration Verification**
   - Run overlay check tool
   - Confirm all slots visible
   - Adjust camera if needed
   - Update slot definitions if required

6. **Final Sealing**
   - Close enclosure
   - Secure cable glands
   - Apply weatherproofing if outdoor
   - Document installation with photos
```

### 10.3 Stability Test Protocol

```markdown
## 60-Minute Stability Test

### Preparation
- System running for 10+ minutes
- Normal parking lot activity

### Monitoring During Test
Every 10 minutes, record:
- [ ] Frame upload rate (target: 0.5-1 fps)
- [ ] CPU temperature (target: <70°C)
- [ ] Memory usage (target: <80%)
- [ ] Wi-Fi signal (target: >-70 dBm)
- [ ] Detection count (should vary with lot activity)
- [ ] No errors in logs

### Success Criteria
- No service restarts
- No dropped frames for >60 seconds
- CPU temperature stable
- All slots reporting states
- Dashboard updating in real-time
```

### 10.4 Network Outage Test

```markdown
## Network Outage Simulation

### Procedure
1. Record current slot states
2. Disconnect Pi from Wi-Fi (disable interface)
3. Wait 2 minutes
4. Simulate occupancy changes (if possible)
5. Reconnect Wi-Fi
6. Verify buffered frames are replayed
7. Confirm no events were lost

### Commands
```bash
# Disconnect
sudo ip link set wlan0 down

# Wait 2 minutes...

# Reconnect
sudo ip link set wlan0 up

# Check buffer
sqlite3 /home/pi/smartpark/upload_buffer.db "SELECT COUNT(*) FROM frame_buffer"
```

### Success Criteria
- [ ] Buffer populated during outage
- [ ] Frames replayed on reconnection
- [ ] Replay in correct chronological order
- [ ] No duplicate events in database
- [ ] Dashboard shows continuous timeline
```

---

## 11. API Specifications

### 11.1 Frame Upload Endpoint

```yaml
POST /api/v1/frames
Content-Type: multipart/form-data

Headers:
  X-API-Key: string (required)

Form Data:
  frame: file (required) - JPEG image
  frame_id: integer (required) - Sequential frame identifier
  timestamp: string (required) - ISO-8601 UTC timestamp
  node_id: string (required) - Edge node identifier
  is_replay: boolean (optional) - True if replaying from buffer

Response 200:
  {
    "status": "success",
    "frame_id": 123,
    "detections": 5,
    "events": 2,
    "inference_time_ms": 45.2
  }

Response 401:
  {"detail": "Invalid API key"}

Response 500:
  {"detail": "Error message"}
```

### 11.2 Slots Endpoint

```yaml
GET /api/v1/frames/slots

Response 200:
  {
    "slots": [
      {
        "slot_id": "FASS_001",
        "state": "occupied",
        "confidence": 0.94,
        "last_change": "2026-01-15T10:30:00Z"
      }
    ],
    "summary": {
      "free_count": 45,
      "occupied_count": 30,
      "unknown_count": 0,
      "total_slots": 75,
      "ts_utc": "2026-01-15T10:35:00Z",
      "roi_version": "v1"
    }
  }
```

### 11.3 Summary Endpoint

```yaml
GET /api/v1/frames/summary

Response 200:
  {
    "free_count": 45,
    "occupied_count": 30,
    "unknown_count": 0,
    "total_slots": 75,
    "ts_utc": "2026-01-15T10:35:00Z",
    "roi_version": "v1"
  }
```

---

## 12. Database Schema

### 12.1 Tables

```sql
-- Slot state changes
CREATE TABLE slot_states (
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

CREATE INDEX idx_slot_states_slot_id ON slot_states(slot_id);
CREATE INDEX idx_slot_states_ts_utc ON slot_states(ts_utc);

-- Node health telemetry
CREATE TABLE node_health (
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

CREATE INDEX idx_node_health_node_id ON node_health(node_id);
CREATE INDEX idx_node_health_ts_utc ON node_health(ts_utc);

-- Frame processing log
CREATE TABLE frame_logs (
    id SERIAL PRIMARY KEY,
    frame_id INTEGER,
    node_id VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    inference_time_ms FLOAT,
    detections_count INTEGER,
    is_replay BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_frame_logs_node_id ON frame_logs(node_id);
CREATE INDEX idx_frame_logs_timestamp ON frame_logs(timestamp);
```

### 12.2 Data Retention Policy

```sql
-- Create function to delete old data
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

-- Schedule cleanup (run daily)
-- Use pg_cron extension or external cron job
```

---

## 13. Configuration Reference

### 13.1 Edge Configuration

```json
// edge/configs/settings.json
{
  "node_id": "fass-edge-01",
  "camera": {
    "resolution": [1920, 1080],
    "capture_interval": 1.5,
    "jpeg_quality": 85,
    "rotation": 0,
    "flip_horizontal": false,
    "flip_vertical": false
  },
  "server": {
    "url": "http://YOUR_SERVER_IP:8000",
    "timeout": 10.0,
    "retry_attempts": 3
  },
  "mqtt": {
    "host": "YOUR_SERVER_IP",
    "port": 1883,
    "keepalive": 60
  },
  "health": {
    "report_interval": 15.0
  },
  "buffer": {
    "max_size_mb": 100,
    "replay_batch_size": 50
  }
}
```

### 13.2 Server Configuration

```ini
# server/.env
DATABASE_URL=postgresql://smartpark:YOUR_DB_PASSWORD@postgres:5432/smartpark
MQTT_HOST=mqtt
MQTT_PORT=1883
API_KEY=YOUR_SECURE_API_KEY
MODEL_PATH=ml/yolov8l.pt
INFERENCE_DEVICE=cpu
CONFIDENCE_THRESHOLD=0.5
DEBOUNCE_SECONDS=3.0
ENTER_THRESHOLD=0.6
EXIT_THRESHOLD=0.4
SLOTS_CONFIG_PATH=calibration/fass_slots_v1.json
```

---

## 14. Troubleshooting Guide

### 14.1 Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Camera not detected | `libcamera-hello` fails | Check ribbon cable, enable camera in raspi-config |
| Frame upload fails | 500 errors, timeout | Check server URL, firewall, API key |
| High CPU temperature | >75°C, throttling | Add heatsinks, improve ventilation |
| Wi-Fi disconnects | Intermittent connectivity | Check signal strength, use 2.4GHz band |
| YOLOv8 OOM | Server crashes on inference | Reduce batch size, use smaller model |
| Slots not updating | No events in database | Verify calibration, check detection logs |

### 14.2 Diagnostic Commands

```bash
# Edge node diagnostics
# Check camera
libcamera-hello --list-cameras

# Check service status
sudo systemctl status smartpark-edge
journalctl -u smartpark-edge -f

# Check Wi-Fi
iwconfig wlan0
ping -c 4 google.com

# Check temperature
vcgencmd measure_temp

# Check buffer size
sqlite3 ~/smartpark/upload_buffer.db "SELECT COUNT(*) FROM frame_buffer"

# Server diagnostics
# Check containers
docker ps
docker logs smartpark-api -f

# Check database
docker exec -it smartpark-postgres psql -U smartpark -c "SELECT COUNT(*) FROM slot_states"

# Check MQTT
docker exec -it smartpark-mqtt mosquitto_sub -t '#' -v
```

---

## 15. Maintenance Procedures

### 15.1 Regular Maintenance Schedule

| Task | Frequency | Description |
|------|-----------|-------------|
| Log review | Daily | Check for errors in edge and server logs |
| Dashboard check | Daily | Verify data is flowing and visualizations are correct |
| Calibration review | Weekly | Verify slot overlays still align |
| Storage cleanup | Weekly | Run data retention cleanup |
| System updates | Monthly | Update OS packages, check for security updates |
| Full backup | Monthly | Backup database, configurations, calibration files |

### 15.2 Calibration Update Procedure

```markdown
## When to Recalibrate
- Camera has been moved
- New parking slots painted
- Accuracy degradation observed
- Seasonal changes (sun angle)

## Recalibration Steps
1. Capture new reference frames
2. Create new slot definitions (fass_slots_v2.json)
3. Update roi_version in configuration
4. Run overlay validation
5. Deploy to server calibration folder
6. Monitor for improved accuracy
7. Archive old calibration files
```

### 15.3 Backup and Recovery

```bash
# Backup database
docker exec smartpark-postgres pg_dump -U smartpark smartpark > backup_$(date +%Y%m%d).sql

# Backup calibration
tar -czf calibration_backup_$(date +%Y%m%d).tar.gz calibration/

# Restore database
cat backup_20260115.sql | docker exec -i smartpark-postgres psql -U smartpark smartpark

# Restore calibration
tar -xzf calibration_backup_20260115.tar.gz
```

---

## Appendix A: Quick Reference Commands

```bash
# === Edge Node ===
# Start service
sudo systemctl start smartpark-edge

# Stop service
sudo systemctl stop smartpark-edge

# View logs
journalctl -u smartpark-edge -f

# Check status
sudo systemctl status smartpark-edge

# === Server ===
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View API logs
docker logs smartpark-api -f

# Restart API
docker restart smartpark-api

# Access database
docker exec -it smartpark-postgres psql -U smartpark

# === Monitoring ===
# Check latest slot states
curl http://localhost:8000/api/v1/frames/slots | jq

# Check summary
curl http://localhost:8000/api/v1/frames/summary | jq

# Subscribe to MQTT topics
mosquitto_sub -h localhost -t 'su/parking/fass/#' -v
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| Edge Node | Raspberry Pi device deployed at parking lot |
| Slot | Individual parking space |
| ROI | Region of Interest - parking area within camera view |
| Debounce | Delay before confirming state change to prevent flicker |
| Hysteresis | Different thresholds for enter vs exit to reduce noise |
| Dwell Time | Duration a vehicle stays in a slot |
| MQTT | Message queue protocol for IoT telemetry |
| Store-and-Forward | Buffering messages locally when network unavailable |

---

*Document Version: 1.0*
*Last Updated: January 2026*
*Author: SmartPark Development Team*
