# Calibration Files

This directory contains calibration files for the SmartPark edge node.

## Files

### fass_slots_v1.json
Parking slot polygon definitions. Use `tools/slot_labeler.py` to create or update.

### roi_mask.png
Region of Interest mask image (1920x1080 grayscale).
- White (255) = Region of interest (parking area)
- Black (0) = Masked area (ignore)

**Note:** The included `roi_mask.png` is a placeholder. To create the actual mask:

1. Capture a reference image from the camera:
   ```bash
   libcamera-still -o reference.jpg --width 1920 --height 1080
   ```

2. Open in an image editor (GIMP, Photoshop, etc.)

3. Create a new grayscale layer

4. Paint white over the parking lot area, black everywhere else

5. Save as `roi_mask.png` (grayscale PNG, 1920x1080)

Alternatively, the ROI can be derived from the slot polygons in `fass_slots_v1.json`.
