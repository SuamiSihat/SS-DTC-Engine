---
name: thumbnail-generator
description: Generate social media thumbnails and cover images for Masterclass episodes (YouTube 16:9), Reels/TikTok covers (9:16), Instagram grid squares (1:1), and course portal hero images. Auto-extracts key frames and composes branded overlays.
---

# Thumbnail generator

Generate branded thumbnails and cover images from video footage or images. Needed for every Masterclass publish and Reels upload.

Tools: `scripts/render_thumbnail.py` (ffmpeg frame extraction + Pillow composition).

## 1. Templates

| Template | Primary use | Default size |
|---|---|---|
| `masterclass-episode` | YouTube / course portal episode thumbnail | 1280×720 (16:9) |
| `masterclass-trailer` | YouTube trailer thumbnail | 1280×720 (16:9) |
| `reel-cover` | Instagram Reels / TikTok cover image | 1080×1920 (9:16) |
| `grid-square` | Instagram grid / Facebook post thumbnail | 1080×1080 (1:1) |
| `course-hero` | Course portal banner | 1920×1080 (16:9) |

## 2. Design elements

- **Key frame**: auto-extracted from the video (best face, no motion blur, good expression) or manually specified by timestamp.
- **Background**: key frame blurred + darkened (Gaussian 30 px, brightness 40%) as a full-bleed background, with the sharp frame overlaid.
- **Episode badge**: rounded rectangle with episode number (`EP03`) in brand accent colour, top-left.
- **Title text**: large Poppins Bold, with drop shadow (2 px offset, 60% opacity black) for readability.
- **Subtitle**: smaller Poppins Medium below the title.
- **Logo**: brand logo in the bottom-right corner, respecting clear-space rules.
- **Brand gradient**: subtle gradient overlay in brand primary colour at 15% opacity along the bottom.

## 3. Auto-frame selection

When `--auto-frame` is used:
1. Extract 10 evenly-spaced frames from the video.
2. Score each frame by sharpness (Laplacian variance — higher = sharper, less motion blur).
3. Optionally score by face detection confidence if OpenCV is available.
4. Pick the frame with the highest combined score.
5. Fall back to 33% of video duration if scoring fails.

## 4. Multi-size generation

From one spec, generate all needed aspect ratios:
- **16:9** (1280×720 or 1920×1080): landscape, face in the right two-thirds, text left.
- **9:16** (1080×1920): portrait, face top half, text below.
- **1:1** (1080×1080): square, face centered, text at bottom.

The face position determines the crop for each ratio. Text repositions automatically.

## 5. Usage

```
# Single thumbnail from video
python scripts/render_thumbnail.py renders/EP03.mp4 \
  --template masterclass-episode --title "Punca Utama ED" --episode 3 \
  --brand ssclinic --sizes 16x9,9x16,1x1 --auto-frame

# Manual frame time
python scripts/render_thumbnail.py renders/EP03.mp4 \
  --template reel-cover --title "3 Fakta Penting" --frame-time 8.5 \
  --brand drmitring --output-dir thumbnails/

# From an image (not video)
python scripts/render_thumbnail.py work/keyframe.png \
  --template grid-square --title "Episod Baru" --brand ssclinic

# Batch: thumbnails for all episodes
python scripts/render_thumbnail.py --batch-spec work/thumbnail_spec.json --output-dir thumbnails/
```

Batch spec:
```json
{
  "brand": "ssclinic",
  "thumbnails": [
    {"source": "renders/16x9/EP01.mp4", "template": "masterclass-episode", "title": "Apa Itu ED?", "episode": 1, "sizes": ["16x9", "1x1"]},
    {"source": "renders/16x9/EP02.mp4", "template": "masterclass-episode", "title": "Punca & Rawatan", "episode": 2, "sizes": ["16x9", "1x1"]}
  ]
}
```

## 6. Output

- Files: `<batch>_<template>_<size>.png` (e.g., `EP03_masterclass-episode_16x9.png`)
- Summary printed: `OK 3 thumbnails: EP03_16x9.png, EP03_9x16.png, EP03_1x1.png`
- Thumbnails go to `batches/<batch>/renders/thumbnails/` or the specified output directory.
