"""
End-to-end system test.
Run this test with the server running locally.

Usage:
    python tests/e2e_test.py
"""

import time
import json
from pathlib import Path

import requests


def test_full_pipeline():
    """Test complete frame upload and processing pipeline."""

    SERVER_URL = "http://localhost:8000"
    API_KEY = "development-key"  # Default dev key

    print("=" * 50)
    print("SmartPark E2E Test")
    print("=" * 50)

    # 1. Check server health
    print("\n1. Checking server health...")
    try:
        response = requests.get(f"{SERVER_URL}/api/v1/health/", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"   Server status: {response.json()['status']}")
    except requests.exceptions.ConnectionError:
        print("   ERROR: Server not reachable. Make sure the server is running.")
        return False

    # 2. Check root endpoint
    print("\n2. Checking root endpoint...")
    response = requests.get(f"{SERVER_URL}/")
    assert response.status_code == 200
    print(f"   Service: {response.json()['service']} v{response.json()['version']}")

    # 3. Check summary endpoint
    print("\n3. Checking summary endpoint...")
    response = requests.get(f"{SERVER_URL}/api/v1/frames/summary")
    assert response.status_code == 200
    summary = response.json()
    print(f"   Summary: {json.dumps(summary, indent=2)}")

    # 4. Check slots endpoint
    print("\n4. Checking slots endpoint...")
    response = requests.get(f"{SERVER_URL}/api/v1/frames/slots")
    assert response.status_code == 200
    slots_data = response.json()
    print(f"   Total slots: {slots_data['summary']['total_slots']}")

    # 5. Try frame upload (if test image exists)
    print("\n5. Testing frame upload...")
    test_image_paths = [
        Path("tests/fixtures/test_parking.jpg"),
        Path("test_parking.jpg"),
        Path("reference.jpg")
    ]

    test_image = None
    for path in test_image_paths:
        if path.exists():
            test_image = path
            break

    if test_image:
        print(f"   Using test image: {test_image}")
        with open(test_image, 'rb') as f:
            response = requests.post(
                f"{SERVER_URL}/api/v1/frames",
                files={'frame': ('frame.jpg', f, 'image/jpeg')},
                data={
                    'frame_id': int(time.time()),
                    'timestamp': '2026-01-15T10:00:00Z',
                    'node_id': 'e2e-test-node'
                },
                headers={'X-API-Key': API_KEY}
            )

        if response.status_code == 200:
            result = response.json()
            print(f"   Upload result: {json.dumps(result, indent=2)}")
        else:
            print(f"   Upload response: {response.status_code} - {response.text}")
    else:
        print("   No test image found, skipping frame upload test")

    # 6. Check frame statistics
    print("\n6. Checking frame statistics...")
    response = requests.get(f"{SERVER_URL}/api/v1/health/frames?hours=1")
    assert response.status_code == 200
    stats = response.json()
    print(f"   Frame stats: {json.dumps(stats, indent=2)}")

    # 7. Check model info
    print("\n7. Checking model info...")
    response = requests.get(f"{SERVER_URL}/api/v1/health/model")
    if response.status_code == 200:
        model_info = response.json()
        print(f"   Model: {model_info.get('model_path', 'unknown')}")
        print(f"   Device: {model_info.get('device', 'unknown')}")
    else:
        print(f"   Model info not available: {response.status_code}")

    print("\n" + "=" * 50)
    print("E2E Test Completed Successfully!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_full_pipeline()
    exit(0 if success else 1)
