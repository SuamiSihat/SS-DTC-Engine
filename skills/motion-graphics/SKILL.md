---
name: motion-graphics
description: Create animated overlay clips (slide-in, scale-pop, typewriter, counter, wipe, transitions) to replace static PNG overlays in video ads. The single biggest visual quality upgrade. Use when designing overlays in dtc-reels-editor step 5 or when the brief asks for animated graphics.
---

# Motion graphics

Replace static PNG overlays with animated transparent video clips. Today `render_batch.py` fades static PNGs in and out; this skill generates short animated clips that ffmpeg overlays instead.

Tools: `scripts/motion.py` (Pillow frame-by-frame + ffmpeg encode), `assets/templates/` (reusable motion presets).

## 1. Animation types

| Type | Use for | Default timing |
|---|---|---|
| `slide-in` | Lower thirds, headlines, claim chips | entrance 0.3 s, exit 0.2 s |
| `scale-pop` | Claim chips, badges, icons | 0→105%→100% in 0.25 s, exit scale to 0% in 0.2 s |
| `typewriter` | Headlines, hook text | char-by-char or word-by-word, 0.04 s per char |
| `counter-tick` | Units sold, price reveal, stats | tick from 0 to target over 1.5–2.0 s |
| `wipe-reveal` | Headlines, product cards | horizontal or vertical wipe, 0.3 s |
| `fade-blur` | Lower thirds, b-roll cards | blur 20 px → 0 px + fade, 0.3 s |

### Transitions (between segments)

| Style | Duration | Description |
|---|---|---|
| `push` | 0.3–0.4 s | Current frame pushes off-screen, next pushes in |
| `zoom-through` | 0.3 s | Zoom into center, cut, zoom out from center |
| `flash` | 0.2 s | White flash at the cut point |
| `glitch` | 0.3 s | RGB split + horizontal offset for 3–4 frames |

## 2. Rules

- **Safe zones**: all animated elements stay inside x 120–960, y 270–1248 at 1080×1920. Face no-go zone still applies.
- **Brand colours**: read from `brands/<slug>/brand.json`. Never hardcode hex.
- **Fonts**: Poppins family, loaded from system font directories.
- **Performance**: generate PNG sequences at 30 fps, encode to transparent MOV (qtrle) or WebM (VP9 alpha). ffmpeg overlays the clip at the correct timestamp.
- **Subtlety**: animations are polish, not distraction. Entrances 0.2–0.4 s, exits 0.15–0.3 s. No spinning, bouncing, or 3D flips.
- **Keyword highlight**: `*word*` syntax renders that word in the brand accent colour (same as render_batch.py).

## 3. Usage

```
# Single animated overlay
python scripts/motion.py slide-in work/headline.mov \
  --text "Bukan *Ubat*" --direction left --duration 3.0 \
  --font Poppins-Bold.ttf --size 60 --color "#FFFFFF" --bg "#022057E8" \
  --width 840 --height 120 --entrance 0.3 --exit 0.2

# Counter animation
python scripts/motion.py counter-tick work/counter.mov \
  --from 0 --to 15000 --label "Unit Terjual" --duration 2.0 \
  --font Poppins-Bold.ttf --size 80 --color "#F4A261"

# Transition
python scripts/motion.py transition work/trans.mov \
  --style push --direction left --duration 0.4 --width 1080 --height 1920

# Batch: generate all motion overlays for a spec
python scripts/motion.py batch work/spec.json --work batches/batch01/work/ --out batches/batch01/work/motion/

# Demo: one example of each type
python scripts/motion.py --demo --out work/motion_demo/
```

## 4. Output format

- **Overlays**: transparent MOV (Animation/qtrle codec) or PNG sequence in a folder. Size matches the overlay region, not the full 1080×1920 canvas.
- **Transitions**: full-frame 1080×1920 transparent MOV.
- All at 30 fps to match the main render.

## 5. Batch spec integration

In `work/spec.json`, overlay entries gain an `"animate"` key:

```json
{
  "kind": "headline",
  "text": "Bukan *Ubat*",
  "x": 120, "y": 925,
  "start": 2.5, "end": 5.5,
  "animate": {"type": "slide-in", "direction": "left", "entrance": 0.3, "exit": 0.2}
}
```

`scripts/motion.py batch` reads the spec, generates each animated overlay to `work/motion/`, and outputs an updated spec with the MOV paths. `render_batch.py` then overlays the MOVs instead of static PNGs.

If `"animate"` is absent, the existing static PNG + fade workflow is used (backward compatible).

## 6. Creating new animation presets

Save a preset JSON to `assets/templates/motion/<name>.json`:

```json
{
  "name": "chip-pop",
  "type": "scale-pop",
  "entrance": 0.25,
  "exit": 0.2,
  "overshoot": 1.05,
  "bg": "primary",
  "color": "text_on_primary",
  "corner_radius": 24,
  "padding": [12, 24]
}
```

Reference it in the spec: `"animate": {"preset": "chip-pop"}`.
