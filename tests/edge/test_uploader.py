"""
Unit tests for frame uploader.
"""

import pytest
import tempfile
import sqlite3
from unittest.mock import Mock, patch
from queue import Queue

import sys
sys.path.insert(0, 'edge')

from services.uploader import FrameUploader


@pytest.fixture
def uploader():
    """Create uploader with temporary buffer."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        buffer_path = f.name

    return FrameUploader(
        server_url="http://localhost:8000",
        api_key="test-key",
        timeout=5.0,
        buffer_db_path=buffer_path
    )


def test_init_buffer_db(uploader):
    """Test buffer database initialization."""
    conn = sqlite3.connect(uploader.buffer_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='frame_buffer'")
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == 'frame_buffer'


def test_buffer_frame(uploader):
    """Test frame buffering."""
    frame = {
        'frame_id': 1,
        'timestamp': '2026-01-15T10:00:00Z',
        'data': b'test_image_data'
    }

    uploader._buffer_frame(frame)

    conn = sqlite3.connect(uploader.buffer_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT frame_id, timestamp, data FROM frame_buffer")
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == 1
    assert result[1] == '2026-01-15T10:00:00Z'
    assert result[2] == b'test_image_data'


def test_get_stats(uploader):
    """Test stats retrieval."""
    stats = uploader.get_stats()

    assert 'uploaded' in stats
    assert 'failed' in stats
    assert 'buffered' in stats
    assert 'replayed' in stats
    assert 'buffer_count' in stats


@patch('requests.Session.post')
def test_upload_success(mock_post, uploader):
    """Test successful upload."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    frame = {
        'frame_id': 1,
        'timestamp': '2026-01-15T10:00:00Z',
        'data': b'test_image_data'
    }

    result = uploader.upload_frame(frame)

    assert result is True
    assert uploader._stats['uploaded'] == 1


@patch('requests.Session.post')
def test_upload_failure_buffers(mock_post, uploader):
    """Test that failed uploads are buffered."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    frame = {
        'frame_id': 1,
        'timestamp': '2026-01-15T10:00:00Z',
        'data': b'test_image_data'
    }

    result = uploader.upload_frame(frame)

    assert result is False
    assert uploader._stats['buffered'] == 1
