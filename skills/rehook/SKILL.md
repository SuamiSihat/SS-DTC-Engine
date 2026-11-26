---
name: rehook
description: Identify, write and edit rehook moments into a Reels ad or Masterclass episode. Use when planning cuts, writing hook/caption lines, or finishing a spec.json — especially for educational or health-awareness videos where viewers are most likely to drop off mid-video.
---

# Rehook

A **rehook** is a mid-video attention reset: a second hook that makes the viewer want to keep watching. It is not a caption style, a transition effect, or another keyword. It must introduce a new reason to continue.

---

## 1. Structure

```
HOOK            → stop the scroll
EXPLANATION 1   → deliver initial value
REHOOK          → renew curiosity before the next point   ← this skill
EXPLANATION 2   → answer the new curiosity
[REHOOK AGAIN]  → optional, before each major new point
FINAL EXPLANATION + CTA
```

For a 23–30 s Reels master there is usually **one rehook**, placed around the 10–15 s mark — after the first point lands but before the viewer has decided to leave.  
For a Masterclass episode (5–15 min) place a rehook at every major chapter transition.

---

## 2. Five techniques (pick the one that fits the transcript)

| Technique | Malay example |
|-----------|---------------|
| Ask a question | "Tapi, bagaimana jika masalah ini berlaku pada lelaki muda?" |
| Reveal something unexpected | "Apa yang ramai tak tahu, masalah ini juga boleh berkait dengan diabetes." |
| Create curiosity | "Namun, ada satu tanda awal yang sering diabaikan." |
| Introduce a misconception | "Ramai fikir ini cuma disebabkan faktor usia. Sebenarnya, tidak semestinya." |
| Promise important information | "Sebab itulah penting untuk anda tahu tiga tanda awal ini." |

**Rules**:
- The rehook line must come from the doctor's real speech. Never invent it.
- If no suitable line exists in the transcript, do not force one — fewer segments is better than a fabricated claim.
- Never disguise flagged words in a rehook line. Run `scripts/check_brand.py` on it.

---

## 3. Identifying rehook candidates in the transcript

After the Cut step, scan `work/transcripts/<clip_id>.json` for lines tagged:
- `myth` — a correction or misconception the doctor addresses ("Ramai fikir…")
- `number` — a surprising statistic or figure
- `steps` — the doctor announces a list ("Ada tiga sebab…")
- `concept` — a topic switch or new angle
- `question` — the doctor asks a question directly

Any of these at the boundary between two explanation blocks is a natural rehook candidate. Pick the one with the highest forward pull (the viewer must stay to hear the answer).

---

## 4. Spec.json — marking rehook points

Add a `"rehooks"` array to the clip object. Each entry gives the **source-clip timestamp** of the rehook line's first word:

```json
{
  "id": "001",
  "segments": [[0.0, 6.2], [6.2, 11.4], [11.4, 13.1], [13.1, 28.5]],
  "rehooks": [
    {"t": 11.4, "technique": "question", "line": "Tapi, bagaimana jika masalah ini berlaku pada lelaki muda?"}
  ],
  ...
}
```

- `t` must align exactly to a word boundary in `work/words/<clip_id>.json`.
- `technique` is one of: `question`, `unexpected`, `curiosity`, `misconception`, `promise`.
- `line` is the verbatim spoken text (used for caption emphasis and brand-gate check).
- Old clips without `"rehooks"` render as before — the field is optional.

For Masterclass, add `"rehook": true` to the chapter entry in `work/chapters.json` at the chapter that opens the new curiosity loop.

### Alternative: typed `structure` array

For richer annotation, use a `"structure"` array on the clip instead of `"rehooks"`:

```json
"structure": [
  {"sequence": 1, "type": "hook",        "start": 0.0,  "end": 5.2,  "line": "..."},
  {"sequence": 2, "type": "explanation", "start": 5.2,  "end": 11.4, "line": "..."},
  {"sequence": 3, "type": "rehook",      "start": 11.4, "end": 13.1, "line": "...", "technique": "curiosity"},
  {"sequence": 4, "type": "explanation", "start": 13.1, "end": 28.5, "line": "..."},
  {"sequence": 5, "type": "cta",         "start": 28.5, "end": 30.0, "line": "..."}
]
```

The renderer reads both formats. Use `"rehooks"` for quick annotation; use `"structure"` when the full narrative flow is documented. Do not use both on the same clip.

---

## 5. Editing effects at a rehook point

The renderer applies these automatically when a `rehooks` entry is found. Each effect is subtle; the message carries the weight, not the edit.

| Layer | What changes |
|-------|-------------|
| **Pause** | 0.3–0.5 s micro-pause inserted before the rehook line (at the word boundary immediately before `t`) |
| **Caption** | The entire rehook line is set in the brand accent colour (not just keywords); font weight bumps one step (Medium → SemiBold) |
| **Framing** | Switch wide↔tight at `t`; if the last segment was tight, go wide, and vice versa |
| **B-roll** | A 1–2 s b-roll cut is placed immediately before the rehook line if a suitable `broll` entry exists; otherwise skip |
| **SFX** | A low-level attention SFX (`scripts/sound_design.py`, level ≤ −24 dB relative to voice) on the rehook entry frame |

Do **not** add jump cuts, speed ramps, or heavy SFX at the rehook — these distract from the message.  
Do **not** alter the doctor's voice speed or pitch.  
Do **not** add music at the rehook unless the brief already calls for background music throughout.

---

## 6. QA checklist

Before packaging, verify every rehook in `qa/rehook_<batch>.txt`:

- [ ] Rehook line is verbatim from the transcript (not paraphrased or invented)
- [ ] `check_brand.py` passes on the rehook line
- [ ] Caption accent colour is correct for the brand (never white text on lime)
- [ ] Micro-pause is audible but not jarring (0.3–0.5 s)
- [ ] Framing switches at the rehook boundary
- [ ] The next explanation segment directly answers the curiosity the rehook creates
- [ ] `sync-qa` still passes after the micro-pause insertion (offset ≤ 40 ms)

---

## 7. Hook vs Rehook summary

| | Hook | Rehook |
|--|------|--------|
| Position | Video opening (0–3 s) | Middle (≈10–15 s for Reels; chapter boundary for Masterclass) |
| Objective | Stop the scroll | Prevent the drop-off |
| Viewer question | Why should I watch? | Why should I keep watching? |
| Source | Hook versions A/B/C/D in spec | Real mid-video line tagged in `"rehooks"` |
| Visual treatment | Full hook background, cutout doctor | Framing switch + caption accent; no background swap |
