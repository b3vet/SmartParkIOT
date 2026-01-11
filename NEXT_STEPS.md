# Next Steps

## 1. Server Deployment

### 1.1 Prepare VPS
```bash
ssh root@your-vps-ip
adduser smartpark && usermod -aG sudo smartpark
```

### 1.2 Install Docker
```bash
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker smartpark
```

### 1.3 Configure Environment
```bash
cd server
cp .env.example .env
# Edit .env with production values:
# DB_PASSWORD=<secure-password>
# API_KEY=<secure-api-key>
# GRAFANA_PASSWORD=<secure-password>
```

### 1.4 Start Services
```bash
docker compose up -d
docker ps  # Verify all containers running
```

### 1.5 Verify Server
```bash
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/api/v1/frames/summary
```

---

## 2. Raspberry Pi Setup

### 2.1 Flash OS
- Download Raspberry Pi OS Lite (64-bit)
- Flash to SD card with Raspberry Pi Imager
- Enable SSH and configure Wi-Fi during imaging

### 2.2 Initial Configuration
```bash
ssh pi@raspberrypi.local
passwd  # Change default password
sudo hostnamectl set-hostname fass-smartpark-edge
sudo raspi-config  # Enable Camera, set timezone to Europe/Istanbul
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-picamera2 libcamera-apps
```

### 2.3 Verify Camera
```bash
libcamera-hello --list-cameras
libcamera-still -o test.jpg
```

---

## 3. Edge Software Deployment

### 3.1 Clone and Setup
```bash
cd ~
mkdir smartpark && cd smartpark
# Copy edge/ directory contents here
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.2 Configure Edge
```bash
cp configs/.env.example configs/.env
# Edit configs/.env:
# API_KEY=<same-key-as-server>

# Edit configs/settings.json:
# Set server.url to http://<VPS-IP>:8000
# Set mqtt.host to <VPS-IP>
```

### 3.3 Test Edge
```bash
source venv/bin/activate
python main.py  # Ctrl+C to stop after verifying connection
```

### 3.4 Install Systemd Service
```bash
sudo cp systemd/smartpark-edge.service /etc/systemd/system/
sudo mkdir -p /var/log/smartpark
sudo chown pi:pi /var/log/smartpark
sudo systemctl daemon-reload
sudo systemctl enable smartpark-edge
sudo systemctl start smartpark-edge
```

---

## 4. Calibration

### 4.1 Capture Reference Frames
```bash
libcamera-still -o reference_morning.jpg --width 1920 --height 1080
libcamera-still -o reference_midday.jpg --width 1920 --height 1080
scp reference_*.jpg user@dev-machine:~/
```

### 4.2 Define Slot Polygons (on dev machine)
```bash
cd tools
python slot_labeler.py reference_midday.jpg ../calibration/fass_slots_v1.json
# Left-click: add point | Right-click: save polygon | 's': save file | 'q': quit
```

### 4.3 Validate Calibration
```bash
# On Pi with display or via VNC:
python tools/overlay_check.py calibration/fass_slots_v1.json
# Or static validation:
python tools/overlay_check.py calibration/fass_slots_v1.json --image reference_midday.jpg
```

### 4.4 Deploy Calibration
```bash
# Copy to both edge and server:
scp calibration/fass_slots_v1.json pi@edge:~/smartpark/calibration/
scp calibration/fass_slots_v1.json server:~/smartpark/server/calibration/
```

---

## 5. Verification

### 5.1 Check Edge Status
```bash
sudo systemctl status smartpark-edge
journalctl -u smartpark-edge -f
```

### 5.2 Check Server Logs
```bash
docker logs smartpark-api -f
```

### 5.3 Verify Data Flow
```bash
# Check frames being processed
curl http://<VPS-IP>:8000/api/v1/frames/summary

# Check slot states
curl http://<VPS-IP>:8000/api/v1/frames/slots

# Subscribe to MQTT
docker exec -it smartpark-mqtt mosquitto_sub -t 'su/parking/fass/#' -v
```

### 5.4 Access Grafana
- URL: `http://<VPS-IP>:3000`
- Login: admin / <GRAFANA_PASSWORD>
- Dashboard: SmartPark > FASS SmartPark - Parking Overview

---

## 6. Stability Test (60 min)

Record every 10 minutes:
- [ ] Frame rate: 0.5-1 fps
- [ ] CPU temp: <70°C (`vcgencmd measure_temp`)
- [ ] Memory: <80% (`free -h`)
- [ ] Wi-Fi: >-70 dBm (`iwconfig wlan0`)
- [ ] No errors in logs

---

## 7. Network Outage Test

```bash
# Disconnect
sudo ip link set wlan0 down
# Wait 2 minutes
sudo ip link set wlan0 up
# Verify buffer replay
sqlite3 ~/smartpark/upload_buffer.db "SELECT COUNT(*) FROM frame_buffer"
```

Success: buffered frames replayed, no events lost.

---

## 8. Production Hardening

### 8.1 Log Rotation
```bash
sudo nano /etc/logrotate.d/smartpark
```
```
/var/log/smartpark/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

### 8.2 Health Check Cron
```bash
crontab -e
# Add:
*/5 * * * * /home/pi/smartpark/scripts/health_check.sh
```

### 8.3 Firewall (Server)
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # API
sudo ufw allow 1883/tcp  # MQTT
sudo ufw allow 3000/tcp  # Grafana
sudo ufw enable
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start edge | `sudo systemctl start smartpark-edge` |
| Stop edge | `sudo systemctl stop smartpark-edge` |
| Edge logs | `journalctl -u smartpark-edge -f` |
| Start server | `docker compose up -d` |
| Stop server | `docker compose down` |
| API logs | `docker logs smartpark-api -f` |
| DB access | `docker exec -it smartpark-postgres psql -U smartpark` |
| Summary | `curl http://localhost:8000/api/v1/frames/summary` |
