"""
Interactive tool to define parking slot polygons.
Run on a development machine with GUI support.

Usage:
    python slot_labeler.py <image_path> [output_path]

Example:
    python slot_labeler.py reference_midday.jpg calibration/fass_slots_v1.json
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np


class SlotLabeler:
    """Interactive slot labeling tool."""

    def __init__(self, image_path: str, output_path: str = "fass_slots_v1.json"):
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        self.output_path = output_path
        self.slots = []
        self.current_polygon = []
        self.slot_counter = 1

        cv2.namedWindow("Slot Labeler", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Slot Labeler", self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_polygon.append([x, y])
            self.redraw()
        elif event == cv2.EVENT_RBUTTONDOWN:
            if len(self.current_polygon) >= 4:
                self.save_current_polygon()
            self.current_polygon = []
            self.redraw()

    def save_current_polygon(self):
        """Save the current polygon as a slot."""
        slot_id = f"FASS_{self.slot_counter:03d}"
        self.slots.append({
            "slot_id": slot_id,
            "poly": self.current_polygon.copy()
        })
        print(f"Saved {slot_id} with {len(self.current_polygon)} points")
        self.slot_counter += 1

    def redraw(self):
        """Redraw the display with all slots and current polygon."""
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

        # Draw instructions
        instructions = [
            "Left-click: Add point",
            "Right-click: Save polygon (4+ pts)",
            "s: Save to file",
            "u: Undo last slot",
            "q: Quit"
        ]
        for i, text in enumerate(instructions):
            cv2.putText(display, text, (10, 25 + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        cv2.imshow("Slot Labeler", display)

    def run(self):
        """Run the interactive labeling tool."""
        print("=" * 50)
        print("Slot Labeler - Interactive Tool")
        print("=" * 50)
        print("Instructions:")
        print("  Left-click: Add point to current polygon")
        print("  Right-click: Save polygon and start new (need 4+ points)")
        print("  's': Save to file")
        print("  'u': Undo last slot")
        print("  'q': Quit")
        print("=" * 50)

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
        """Save slots configuration to JSON file."""
        output = {
            "roi_version": "v1",
            "image_size": [self.image.shape[1], self.image.shape[0]],
            "created_by": "slot_labeler",
            "slots": self.slots
        }

        # Create output directory if needed
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Saved {len(self.slots)} slots to {self.output_path}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python slot_labeler.py <image_path> [output_path]")
        print("Example: python slot_labeler.py reference.jpg calibration/fass_slots_v1.json")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "fass_slots_v1.json"

    try:
        labeler = SlotLabeler(image_path, output_path)
        labeler.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
