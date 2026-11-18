---
name: auto-reframe
description: Intelligent smooth camera reframing using face tracking — smooth pan/zoom (Ken Burns), 16:9 to 9:16 auto-conversion, and product-follow zoom. Replaces hard wide/tight cuts with buttery camera movement.
---

# Auto-reframe

Smooth, intelligent camera reframing driven by face tracking data. Replaces the current binary wide/tight hard cuts with animated crop windows that follow the speaker.

Tools: `scripts/auto_reframe.py` (numpy/scipy interpolation + ffmpeg crop), `scripts/face_track.py` (existing face tracker).

## 1. Reframe modes

| Mode | Behaviour | Use for |
|---|---|---|
| `smooth-follow` | Gentle pan/zoom following the face, ≤5% frame movement per second | Default for DTC Reels, Masterclass 9:16 |
| `dynamic` | Faster tracking, up to 15% movement per second, more zoom variation | `energy` variant style |
| `lock` | Find the best single crop and hold it (no movement) | Static compositions, product close-ups |
| `portrait-convert` | 16:9 → 9:16 conversion with face tracking | Masterclass landscape-to-vertical |

## 2. How it works

1. **Load face track**: `work/facetrack_<id>.json` (existing, from `scripts/face_track.py`) gives normalized face center (fx, fy) at 0.5 s intervals.
2. **Interpolate to 30 fps**: cubic spline interpolation (scipy) for smooth per-frame positions.
3. **Smooth**: moving average with configurable window (default 2.0 s). Removes jitter from the face tracker.
4. **Clamp pan speed**: limit horizontal/vertical movement to `max_pan_speed` per frame. Prevents jerky motion.
5. **Calculate crop window**: per frame, set the crop rectangle centered on the smoothed face position, with the target aspect ratio and zoom level.
6. **Render**: ffmpeg `crop` filter with per-frame expressions, then `scale` to output size.

## 3. Zoom behaviour

- **smooth-follow**: zoom varies 1.0–1.3×. Zoom in when face is still (emphasise), zoom out when face moves (context). Smooth transitions.
- **dynamic**: zoom varies 1.0–1.5×. More aggressive zoom on emphasis moments.
- **lock**: single zoom level, best fit for the face.
- **portrait-convert**: zoom set to fill the 9:16 frame from 16:9 source. Typically 1.5–2.0× depending on face position.

## 4. Constraints

- **Never crop outside the source frame**. Clamp the crop window to source dimensions.
- **Face inside safe zones**: after reframe, the face must land inside the safe area (x 120–960, y 270–1248 at 1080×1920).
- **Minimum zoom 1.0×** (never zoom out past original), maximum 2.0×.
- **Pan speed**: `smooth-follow` ≤5% per second, `dynamic` ≤15% per second.
- **No audio change**: reframe is video-only. Audio passes through.

## 5. Product-follow zoom

When the doctor raises a product (detected by lime-colour tracking in `render_batch.py`), smoothly punch in to ~1.75× instead of a hard cut. The spec marks product-raise moments:

```json
{"t": 12.5, "event": "product_raise", "target_zoom": 1.75, "ease_dur": 0.6}
```

The reframe script applies a smooth zoom to 1.75× over 0.6 s, holds while the product is shown, then eases back.

## 6. Usage

```
# Smooth reframe for Reels
python scripts/auto_reframe.py renders/DMR01_A.mp4 \
  --face-track work/facetrack_001.json --mode smooth-follow \
  --target-size 1080x1920

# 16:9 to 9:16 conversion
python scripts/auto_reframe.py renders/16x9/EP03.mp4 \
  --face-track work/facetrack_ep03.json --mode portrait-convert \
  --target-size 1080x1920

# Lock mode (single best crop)
python scripts/auto_reframe.py renders/DMR01_A.mp4 \
  --face-track work/facetrack_001.json --mode lock

# Export keyframes (for render_batch.py integration)
python scripts/auto_reframe.py renders/DMR01_A.mp4 \
  --face-track work/facetrack_001.json --mode smooth-follow \
  --keyframes-out work/reframe_001.json

# Preview: show crop rectangle on a frame
python scripts/auto_reframe.py renders/DMR01_A.mp4 \
  --face-track work/facetrack_001.json --mode smooth-follow \
  --preview review/reframe_preview.png --preview-time 5.0

# Filter chain only
python scripts/auto_reframe.py --chain --mode smooth-follow \
  --face-track work/facetrack_001.json --target-size 1080x1920
```

## 7. Integration

- **render_batch.py**: use `--keyframes-out` to export keyframe data, then embed the crop filter in the render graph instead of the current hard wide/tight switch.
- **Masterclass 9:16**: use `portrait-convert` mode instead of manual center-crop.
- **Variant mode**: `energy` style uses `dynamic` mode; `story` uses `smooth-follow`; `clean` can use either.

## 8. Keyframe export format

```json
[
  {"t": 0.0, "x": 120, "y": 80, "w": 840, "h": 1493, "zoom": 1.0},
  {"t": 0.033, "x": 122, "y": 81, "w": 838, "h": 1489, "zoom": 1.01},
  ...
]
```

One entry per frame (30 fps). `x, y, w, h` are the crop rectangle in source pixel coordinates. `zoom` is informational.
