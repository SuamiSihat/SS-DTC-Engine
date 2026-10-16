---
name: dtc-reels-editor
description: Turn raw talking-head doctor footage into Meta-ready Reels ads (masters plus hook versions) for Dr MIT Ring. Use when the user asks to run a batch, edit doctor clips, make hooks, or produce ad creatives from a brief in briefs/.
---

# DTC Reels editor (orchestrator)

Run one batch end to end. Read the brief in `briefs/<batch>.md` first; it names one brand slug (load `brand-rules`). Work under `batches/<batch>/`
(raw/, work/, renders/, qa/, deliver/). Footage and renders stay out of git.

## Pipeline
0. **Brand gate**: `brand-rules` + `scripts/check_brand.py`. A BLOCK stops the batch.
1. **Prep**: read brief, `brand-rules`, `references/` files. Make a contact sheet of every raw clip so you can see the footage before planning cuts.
2. **Transcribe**: Whisper, Malay, word timestamps, all clips. Save to `work/transcripts/`.
3. **Cut**: drop repeated and filler phrases at word boundaries. Target 23-30 s masters (raw clips are ~26-36 s). Save the cut list to `work/cuts/`.
4. **Frame**: wide and tight cuts per sentence. Track the lime product/ring by colour (ignore the plant) and punch in about 1.75x when the doctor raises it.
5. **Design**: hook headline, word-by-word captions with the keyword in lime, claim chips ("Bukan ubat / Bukan minyak" style), b-roll from the brand's live site (brands/<slug>/README.md), name tag, offer card with prices from `brands/<slug>/prices.json`.
6. **Hooks**: 3 per master (A master, B cold open, C topic visual, D proof). Cut the doctor out (compare cutout models, pick cleanest edges) and place him over the topic-matched background (`hook-backgrounds`). Hook audio is the hook's own clip.
7. **Render** 1080x1920 MP4. Send ALL hook notes before starting the batch render; do not restart renders mid-way.
8. **QA**: frame grid check, then `sync-qa` on every file. Fix and re-run until 100% pass.
9. **Package** with `ad-packaging` (folders, names, Ad Index.csv). Copy to the NAS deliver folder only after a person signs off.
10. **Learn**: append new lessons to `lessons.md` and update the relevant skill.

## Hard rules
- Never invent claims or captions; captions come from real speech.
- Never type prices; read `brands/<slug>/prices.json`.
- Never deliver a file that failed sync-qa or the brand gate.
- Re-run `check_brand.py` on the final captions and hook text before packaging.
- Send all files, not samples, with a short list of what the human must confirm
  (customer-name blur, risky hooks, prices, sound check).
- Hand compliance decisions (see CLAUDE.md) back to the human.

See `references/` for beat plans, Meta policy notes and safe zones. Fill those in from the first batch and
your own Meta policy review; do not treat the stubs as final.
