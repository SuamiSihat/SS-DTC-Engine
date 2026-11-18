---
name: color-grade
description: Apply color grading, LUTs and per-clip correction to video renders. Supports brand-default grades, skin-tone protection, and A/B preview. Use before the editorial look filter or standalone on any MP4.
---

# Color grade

General-purpose colour correction and grading. The existing `look_filter.py` is one specific artistic look (editorial grain/bloom); this skill provides the underlying correction layer.

Tools: `scripts/color_grade.py` (ffmpeg filter chain), LUTs in `brands/<slug>/luts/` or `assets/luts/`.

## 1. What it does

| Feature | How |
|---|---|
| **LUT application** | `.cube` 3D LUT via ffmpeg `lut3d`. Per-brand LUTs in `brands/<slug>/luts/`, generic ones in `assets/luts/`. |
| **Exposure** | Brightness adjustment via `eq=brightness`. Range −0.3 to +0.3. |
| **Contrast** | Contrast curve via `eq=contrast`. Range 0.8 to 1.3. |
| **White balance / temperature** | Shift via `colorbalance` (warm = more red/yellow shadows, cool = more blue shadows). Range −500 K to +500 K (mapped to colorbalance values). |
| **Saturation** | Via `eq=saturation`. Range 0.5 to 1.5. |
| **Skin-tone protection** | Grade everything except the ~15–45° hue range (warm skin tones). Uses ffmpeg `hue` masking: extract skin-tone pixels, apply grade to the rest, merge. |
| **A/B preview** | Extract a frame, show original left / graded right, save as PNG for quick review. |

## 2. Presets

| Preset | Exposure | Contrast | Saturation | Temperature | Notes |
|---|---|---|---|---|---|
| `neutral` | 0 | 1.0 | 1.0 | 0 | Minimal — only the brand LUT if any |
| `warm` | +0.03 | 1.02 | 1.05 | +200 K | Friendly, approachable |
| `cool` | 0 | 1.03 | 0.95 | −200 K | Clinical, professional |
| `cinematic` | −0.02 | 1.08 | 0.90 | +100 K | Crushed blacks, desaturated highlights |
| `bright-clean` | +0.08 | 0.98 | 0.95 | 0 | Lifted shadows, airy |

## 3. Rules

- **Applied BEFORE the editorial look** (`look_filter.py`). Order: raw → colour grade → editorial look → overlays/captions.
- **Never changes the cut, audio, or captions**. Only pixel values.
- **Product shots**: skip grading on product close-ups. The lime-green ring, blue MENSS ring, and packaging colours must stay accurate. If the timeline marks a segment as `mode: "split"` (hook C) or the spec marks it as a product shot, pass it through ungraded.
- **Skin tones**: always enable `--protect-skin` on doctor footage. The doctor's skin must look natural, never orange or grey.
- **Brand defaults**: `brands/<slug>/brand.json` may have a `"grade"` key: `{"lut": "brand_warm.cube", "preset": "warm", "protect_skin": true}`. Load it with `--brand <slug>`.
- **One grade per batch**: pick the grade at the test render, freeze it, apply to all clips. Don't grade each clip differently (consistency across the ad set).

## 4. Usage

```
# Apply a preset
python scripts/color_grade.py renders/DMR01_A.mp4 --preset warm --protect-skin

# Apply a LUT
python scripts/color_grade.py renders/DMR01_A.mp4 --lut brands/drmitring/luts/dmr_warm.cube

# Brand default grade
python scripts/color_grade.py renders/DMR01_A.mp4 --brand drmitring

# Manual adjustment
python scripts/color_grade.py renders/DMR01_A.mp4 --exposure 0.05 --contrast 1.05 --saturation 1.1 --temperature 150

# A/B preview frame
python scripts/color_grade.py renders/DMR01_A.mp4 --preview review/grade_ab.png --preview-time 5.0

# Output filter chain only (for embedding in render_batch.py)
python scripts/color_grade.py --chain --preset cinematic --protect-skin

# Self-test
python scripts/color_grade.py --selftest
```

Output: `<name>_graded.mp4` (or `--output` path). Original file untouched.

## 5. Integration with render_batch.py

Use `--chain` mode to get the filter string, then insert it into the ffmpeg graph in `render_batch.py` before the overlay stage:

```python
import color_grade
grade_chain = color_grade.grade_chain(preset="warm", protect_skin=True)
# insert into vf list before overlays
```

Or run as a post-process on each rendered MP4 before QA.

## 6. LUT management

- Place `.cube` files in `brands/<slug>/luts/` (brand-specific) or `assets/luts/` (shared).
- Name convention: `<brand>_<mood>.cube` (e.g., `dmr_warm.cube`, `ssclinic_clinical.cube`).
- The script searches brand LUT dir first, then `assets/luts/`.
- Never commit large LUT packs to git; `.gitignore` already covers `assets/luts/*.cube`.
