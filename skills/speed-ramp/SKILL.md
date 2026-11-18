---
name: speed-ramp
description: Add speed ramps (punch-in, slow-reveal, snap-back, freeze-moment) to b-roll segments in video ads. Unblocks the energy variant style. Never changes the speed of the speaker's footage or audio.
---

# Speed ramp

Add speed ramps to b-roll and visual-only segments. This unblocks the `energy` variant style in `scripts/variants.py`.

Tools: `scripts/speed_ramp.py` (ffmpeg `setpts` expressions).

## 1. Core rule

**Never change the speed of the speaker's footage or audio.** Speed ramps apply ONLY to:
- B-roll clips (no dialogue audio)
- Product shots and visual-only inserts
- Transition moments between speaker segments

The speaker's audio track always runs at 1× throughout. Only the video track of b-roll is ramped.

## 2. Ramp types

| Type | Speed | Duration | Feel |
|---|---|---|---|
| `punch-in` | 120–150% on entrance | First 30% of b-roll segment | Energy, momentum |
| `slow-reveal` | 50–70% on key visual | Middle 50% of b-roll segment | Emphasis, weight |
| `snap-back` | Normal → 150% → normal | Across full b-roll segment | Rhythm, snap |
| `freeze-moment` | 0% (freeze frame) | 0.3–0.5 s at a key moment | Pause for impact |

## 3. Ramp curves

All ramps use **ease-in-out** curves (not linear jumps). The ffmpeg `setpts` expression uses a smoothstep function:

- **Ease-in-out**: `PTS * (3*t^2 - 2*t^3)` where `t` is normalized position in the ramp zone.
- **Total duration constraint**: the ramped segment must stay within ±0.3 s of the original duration. Compensate fast sections with slow sections within the same segment.

## 4. Integration with variant mode

In `work/spec.json`, b-roll segments gain a `"ramp"` key:

```json
{
  "type": "broll",
  "src": "work/broll/product_01.mp4",
  "s": 0.0, "e": 2.5,
  "ramp": {"type": "punch-in", "speed": 1.3}
}
```

The `energy` style in `variants.py` auto-adds ramps to b-roll segments:
- B-roll entrances: `punch-in` at 130%
- Product reveals: `slow-reveal` at 60%
- Key stat moments: `freeze-moment` for 0.4 s

Other styles (`clean`, `story`) do not add speed ramps.

## 5. Usage

```
# Ramp specific segments
python scripts/speed_ramp.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json \
  --segments 2,4 --ramp-type punch-in --speed 1.3

# Auto-detect b-roll segments
python scripts/speed_ramp.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json \
  --segments broll --ramp-type punch-in

# Freeze moment
python scripts/speed_ramp.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json \
  --ramp-type freeze-moment --freeze-at 5.0 --freeze-dur 0.4

# Dry run
python scripts/speed_ramp.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json \
  --segments broll --ramp-type snap-back --dry-run

# Filter chain only (for render_batch.py embedding)
python scripts/speed_ramp.py --chain --ramp-type punch-in --speed 1.3 --segment-dur 2.5
```

## 6. Constraints

- Output must pass `check_sync.py` (voice audio unchanged).
- Total duration change ≤ 0.3 s from original.
- Never ramp segments with `mode: "wide"` or `mode: "tight"` (those are speaker segments).
- Ramp only segments tagged as b-roll in the timeline, or explicitly listed with `--segments`.
- If a segment is too short (< 1.0 s), skip the ramp and warn.

## 7. QA

After ramping, verify:
1. `check_sync.py` passes (voice track untouched).
2. Total duration within ±0.3 s.
3. No frozen or black frames at ramp boundaries.
4. B-roll still matches the spoken phrase it supports (ramp didn't shift it out of alignment).
