---
name: sound-design
description: Add micro-SFX (whoosh, pop, impact, swipe) and optional music beds with auto-ducking to rendered video ads. Use after the main render to polish audio, or when the brief requests background music. Called by dtc-reels-editor step 7 and variant mode energy style.
---

# Sound design

Add low-level sound effects and optional music beds to finished renders. Voice is king — SFX sit underneath, never on top.

Tools: `scripts/sound_design.py` (ffmpeg mix), `assets/sfx/` (SFX library by category).

## 1. SFX categories

| Category | Folder | When | Level |
|---|---|---|---|
| `whoosh` | `assets/sfx/whoosh/` | B-roll entrance and exit | −20 dB |
| `pop` | `assets/sfx/pop/` | Chip reveal, quote popup entrance, lower-third entrance | −22 dB |
| `impact` | `assets/sfx/impact/` | Number counter land, stat reveal, myth/fakta stamp | −18 dB |
| `swipe` | `assets/sfx/swipe/` | Segment transition, hook cut | −22 dB |
| `ambient` | `assets/sfx/ambient/` | Soft room-tone fill for silence gaps > 0.4 s | −28 dB |
| `rise` | `assets/sfx/rise/` | Counter tick-up, price reveal build-up | −20 dB |

Place WAV or MP3 files (mono or stereo, 48 kHz preferred) in the category folders. The script picks randomly from available files; name files descriptively (`whoosh_soft_01.wav`).

## 2. Rules

- **Level**: SFX are always −18 to −22 dB relative to the voice peak. The `--sfx-level` flag adjusts the global SFX bus.
- **Timing**: SFX are timed to timeline JSON events — overlay `start`/`end` times and segment boundaries. Each SFX aligns to the visual event it supports.
- **Voice untouched**: SFX go on a separate mix bus. The original voice+audio track is passed through bit-for-bit. After mixing, `check_sync.py` must still pass.
- **Density**: 3–6 SFX per 25 s master is plenty. More sounds busy, not professional. Skip events that are < 0.8 s apart.
- **No SFX on speech**: never layer an SFX over the speaker's words. Only on visual events (b-roll, overlay, transition).
- **Brand prefs**: `brands/<slug>/brand.json` may have `"sfx_prefs": {"style": "minimal"|"punchy", "exclude": ["impact"]}`. Respect them.

## 3. Music beds

Music only when the brief explicitly asks. Always deliver **two versions**: with music and without.

- Source: royalty-free tracks from the batch `work/music/` folder (human selects). Never auto-fetch.
- Level: −18 to −22 dB under the voice (configurable via `--music-level`).
- **Auto-ducking**: ffmpeg `sidechaincompress` ducks music when voice is present. Threshold −30 dB, ratio 6:1, attack 0.01 s, release 0.5 s.
- Fade in 1.5 s from start, fade out 2.0 s to end.
- Loop if the track is shorter than the video.

## 4. Usage

```
# SFX only
python scripts/sound_design.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json

# SFX + music
python scripts/sound_design.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json \
  --music work/music/chill_beat.mp3 --music-level -20

# Dry run (print plan, no render)
python scripts/sound_design.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json --dry-run

# Custom SFX level
python scripts/sound_design.py renders/DMR01_A.mp4 renders/DMR01_A.timeline.json --sfx-level -22
```

Output files:
- `<name>_sfx.mp4` — SFX added, no music
- `<name>_sfx_music.mp4` — SFX + music (only if `--music`)
- The original `<name>.mp4` is never modified.

## 5. Integration

- **In dtc-reels-editor**: run after step 7 (render), before step 8 (QA). QA runs on the `_sfx` file.
- **In variant mode (`energy`)**: the energy style adds SFX automatically; other styles add SFX only if the brief asks.
- **In render_batch.py**: call `sound_design.py` as a post-process, or import `sound_design.build_sfx_plan()` to get the event list.

## 6. QA

After adding SFX, re-run `check_sync.py` on the `_sfx.mp4` against the raw source. SFX must not shift the voice. If sync fails, the SFX mix is wrong — check that the original audio track was passed through, not re-encoded.
