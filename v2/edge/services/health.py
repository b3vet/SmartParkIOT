"""
System health monitoring service for edge node.
Collects and reports Pi metrics.
"""

import time
import logging
import threading
import subprocess
from datetime import datetime, timezone
from typing import Optional, Callable, List

import psutil

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors system health and reports metrics."""

    def __init__(self, report_interval: float = 15.0):
        self.report_interval = report_interval
        self.running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._start_time = time.time()
        self._callbacks: List[Callable] = []

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

    def add_callback(self, callback: Callable):
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
