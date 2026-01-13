"""
Validate calibration by overlaying slots on live feed or image.
Run on Raspberry Pi to verify slot alignment.

Usage:
    python overlay_check.py <slots_config_path> [--image <image_path>]

Examples:
    # Live camera feed (on Pi)
    python overlay_check.py calibration/fass_slots_v1.json

    # Static image (on any machine)
    python overlay_check.py calibration/fass_slots_v1.json --image reference.jpg
"""

import json
import sys
import argparse

import cv2
import numpy as np


def validate_overlay_live(slots_path: str):
    """Display live camera feed with slot overlays (Raspberry Pi)."""
    from picamera2 import Picamera2

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
        draw_slots(frame, config)

        cv2.imshow("Calibration Overlay", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("overlay_snapshot.jpg", frame)
            print("Saved overlay_snapshot.jpg")

    picam2.stop()
    cv2.destroyAllWindows()


def validate_overlay_image(slots_path: str, image_path: str):
    """Display static image with slot overlays."""
    # Load slots
    with open(slots_path) as f:
        config = json.load(f)

    # Load image
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"Error: Could not load image: {image_path}")
        sys.exit(1)

    # Draw slots
    draw_slots(frame, config)

    print("Press any key to close, 's' to save")

    cv2.namedWindow("Calibration Overlay", cv2.WINDOW_NORMAL)
    cv2.imshow("Calibration Overlay", frame)

    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == ord('s'):
            cv2.imwrite("overlay_snapshot.jpg", frame)
            print("Saved overlay_snapshot.jpg")
        else:
            break

    cv2.destroyAllWindows()


def draw_slots(frame, config):
    """Draw slot polygons on frame."""
    for slot in config.get('slots', []):
        pts = np.array(slot['poly'], np.int32)
        cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

        # Draw slot ID
        center = pts.mean(axis=0).astype(int)
        cv2.putText(frame, slot['slot_id'], tuple(center),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # Draw info
    cv2.putText(frame, f"ROI Version: {config.get('roi_version', 'unknown')}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(frame, f"Slots: {len(config.get('slots', []))}", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate slot calibration with overlay")
    parser.add_argument("slots_path", help="Path to slots configuration JSON")
    parser.add_argument("--image", "-i", help="Path to image (if not using live camera)")

    args = parser.parse_args()

    try:
        with open(args.slots_path) as f:
            json.load(f)  # Validate JSON
    except FileNotFoundError:
        print(f"Error: Slots config not found: {args.slots_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {args.slots_path}: {e}")
        sys.exit(1)

    if args.image:
        validate_overlay_image(args.slots_path, args.image)
    else:
        try:
            validate_overlay_live(args.slots_path)
        except ImportError:
            print("Error: picamera2 not available. Use --image for static image mode.")
            sys.exit(1)


if __name__ == "__main__":
    main()
