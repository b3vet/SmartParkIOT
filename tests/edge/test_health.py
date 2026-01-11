"""
Unit tests for health monitor.
"""

import pytest
from unittest.mock import patch, Mock

import sys
sys.path.insert(0, 'edge')

from services.health import HealthMonitor


@pytest.fixture
def health_monitor():
    """Create health monitor for testing."""
    return HealthMonitor(report_interval=1.0)


def test_collect_metrics(health_monitor):
    """Test metrics collection."""
    with patch.object(health_monitor, 'get_cpu_temperature', return_value=45.0):
        with patch.object(health_monitor, 'get_wifi_signal', return_value=-50):
            metrics = health_monitor.collect_metrics()

    assert 'ts_utc' in metrics
    assert 'uptime_s' in metrics
    assert 'cpu_percent' in metrics
    assert 'cpu_temp_c' in metrics
    assert 'mem_total_mb' in metrics
    assert 'mem_used_mb' in metrics
    assert 'mem_percent' in metrics
    assert 'disk_percent' in metrics
    assert 'wifi_rssi_dbm' in metrics


def test_add_callback(health_monitor):
    """Test adding callbacks."""
    callback = Mock()
    health_monitor.add_callback(callback)

    assert callback in health_monitor._callbacks


def test_start_stop(health_monitor):
    """Test start and stop."""
    health_monitor.start()
    assert health_monitor.running is True

    health_monitor.stop()
    assert health_monitor.running is False


@patch('subprocess.run')
def test_get_cpu_temperature(mock_run, health_monitor):
    """Test CPU temperature parsing."""
    mock_run.return_value = Mock(
        stdout="temp=52.5'C\n",
        returncode=0
    )

    temp = health_monitor.get_cpu_temperature()

    assert temp == 52.5


@patch('subprocess.run')
def test_get_cpu_temperature_failure(mock_run, health_monitor):
    """Test CPU temperature when command fails."""
    mock_run.side_effect = Exception("Command failed")

    temp = health_monitor.get_cpu_temperature()

    assert temp == -1.0


@patch('subprocess.run')
def test_get_wifi_signal(mock_run, health_monitor):
    """Test WiFi signal parsing."""
    mock_run.return_value = Mock(
        stdout="wlan0     IEEE 802.11  ESSID:\"TestNetwork\"\n          Mode:Managed  Frequency:2.437 GHz  Access Point: XX:XX:XX:XX:XX:XX\n          Bit Rate=72.2 Mb/s   Tx-Power=31 dBm\n          Retry short limit:7   RTS thr:off   Fragment thr:off\n          Power Management:on\n          Link Quality=70/70  Signal level=-45 dBm",
        returncode=0
    )

    signal = health_monitor.get_wifi_signal()

    assert signal == -45
