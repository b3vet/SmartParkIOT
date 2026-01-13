# Calibration Files

This directory contains parking slot polygon definitions used by the occupancy processor.

## Files

- `fass_slots_v1.json` - Version 1 of the FASS parking lot slot definitions (55 slots)

## Creating New Calibration

1. Capture a reference image from the camera:
   ```bash
   python -c "from picamera2 import Picamera2; p = Picamera2(); p.start(); import time; time.sleep(2); p.capture_file('reference.jpg'); p.stop()"
   ```

2. Run the slot labeler tool on a machine with GUI:
   ```bash
   python tools/slot_labeler.py reference.jpg calibration/fass_slots_v2.json
   ```

3. Validate the calibration on the Pi:
   ```bash
   python tools/overlay_check.py calibration/fass_slots_v2.json
   ```

4. Update `configs/settings.json` to use the new calibration file.

## File Format

```json
{
  "roi_version": "v1",
  "image_size": [2048, 1536],
  "created_by": "slot_labeler",
  "slots": [
    {
      "slot_id": "FASS_001",
      "poly": [[x1, y1], [x2, y2], [x3, y3], [x4, y4], ...]
    },
    ...
  ]
}
```
