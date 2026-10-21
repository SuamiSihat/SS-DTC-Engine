---
name: dtc-reels-editor
description: Turn raw talking-head footage into Meta-ready Reels videos (masters, hook versions and funnel/style variants) for any SuamiSihat brand (Dr. MIT Ring, MENSS, REJAL, SS Clinic, Mensculine). Use when the user asks to run a batch, edit doctor or presenter clips, make hooks or variants, or produce ad creatives from a brief in briefs/.
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
5. **Design**: call `dtc-broll` for b-roll, review quote popups and safe-zone placement. Hook headline, word-by-word captions with the keyword in lime, claim chips ("Bukan ubat / Bukan minyak" style), b-roll from the brand's live site (brands/<slug>/README.md) or the licensed stock library (`dtc-broll` section 6), name tag, offer card with prices from `brands/<slug>/prices.json`.
6. **Hooks**: 3 per master (A master, B cold open, C topic visual, D proof). Cut the doctor out (compare cutout models, pick cleanest edges) and place him over the topic-matched background (`hook-backgrounds`). Hook audio is the hook's own clip.
7. **Render** 1080x1920 MP4. Send ALL hook notes before starting the batch render; do not restart renders mid-way.
8. **QA**: frame grid check, `scripts/check_layout.py` (safe area, face, 1080x1920), then `sync-qa` on every file. Fix and re-run until 100% pass.
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
- SS Clinic: read the content mode from the brief (Educational by default, or KOL ad). Educational videos never end with a clinic CTA, offer or testimonial; KOL ads need a KKLIU number per posting and never show a real doctor. See `references/meta-policy.md` section 1a.
- Never disguise flagged words with creative spelling, emojis or code words. Pick a different real line.

- Output is always 1080x1920, never 2K or 4K. Captions, lower thirds and popups stay inside the safe zones and off the doctor's face (`dtc-broll`).

## SS Editorial look (finishing layer)
A soft archival film finish: grain, highlight bloom, light neutral B&W, gate weave, vignette. It never changes the cut, the words, the claims or the prices.
- **Turn on** with `"look": "editorial"` in `work/spec.json` (optional `"look_preset": "bw_broll"`). Off by default, so existing specs render as before. Settings live in `brands/<slug>/look.json`; tune them in the first test render, then freeze them.
- **Implementation**: `scripts/look_filter.py` (ffmpeg chain, used by `render_batch.py`). `look/browser-reference/` is the original WebGL reference (`picture.js` etc.) for the exact look; it is not part of the render path.
- **Where it applies**: inserts and b-roll only (today the split panel in hook C). Never on the doctor or the product ring. Lime/brand accent stays in colour. B&W only on b-roll, hook C backgrounds and proof transitions.
- **Unchanged**: 23-30 s masters, real-speech word-by-word captions with the brand keyword colour, brand colour rules (for example never white text on lime), prices from `prices.json`, each clip's own audio, no music unless the brief asks (then also deliver a version without it).
- **B-roll**: brand live-site first. No AI-generated shots unless the brief approves them and a budget. Never present generated imagery as proof. Fruit metaphors only, no anatomy imagery.
- **Test first**: render one master and one hook (`--only`, `--preview`) with the look on and review in motion before the batch: grain not sliding or repeating, both sides of cuts, caption legibility at phone size, product still tracking, sync and sound, no black or frozen frames. Then run `check_sync.py` as usual. Do not report an unperformed check as passed.
- **Fonts**: `render_batch.py` loads Poppins from the Windows font folders; make sure the brand's real fonts from `brands/<slug>/brand.json` are installed before a batch.

Rendering: build `work/spec.json` (see `references/spec-format.md`) and run `scripts/render_batch.py`; verify each file with `check_sync.py --timeline`.

See `references/` for beat plans, Meta policy notes and safe zones. Fill those in from the first batch and
your own Meta policy review; do not treat the stubs as final.

## Variant mode: funnel x hook x style (PLANNED)
Status: agreed direction 2026-10-21. `render_batch.py` does not read these fields yet; today it renders versions A, B, C (and D where built). Until the code lands, plan variants in the batch note and render them as separate versions by hand.

Goal: up to 10 videos from one source clip, each a different combination of funnel stage, hook and style. Hooks and styles are chosen from the source video and its topic, never forced to fill a quota.

**Funnel stages**
- TOFU: needs a strong standalone line (a real question, myth or surprising point). 23-30 s. Soft close, no price.
- MOFU: needs about 15 s or more of continuous explanation. 23-30 s. Diagram b-roll, "learn more" close.
- BOFU: needs a product line. 15-20 s. Offer card from `prices.json`. Product brands only; never on SS Clinic Educational videos.

**Hooks**: A master, B cold open, C topic visual, D proof, myth/fakta card, question hook (a question the speaker really asks). Proof (D) only with a real proof source and never on SS Clinic.

**Styles** (only those listed for the brand/product in `brands/<slug>/brand.json` -> `product_rules`):
- `clean`: today's default; clean cuts, clear audio, brand look.
- `energy`: more punch-ins, speed ramps and SFX hits on b-roll only. The speaker's audio and speech speed are never altered (sync-qa).
- `story`: follows the speaker's own problem, reason, answer order; slower pace, fewer b-roll items. Fits MOFU.
- `faceless`: product and b-roll led over the speaker's real audio. Needs a rule change in `dtc-broll` (no full-frame cover over the doctor today); use only where the brand allows it (REJAL first).
The SS Editorial look stays a separate on/off finishing layer on any style.

**Selection rules**
1. Tag every kept sentence (`broll_suggest.py` tags: quote, myth, number, steps, concept, metaphor, product).
2. Build each funnel stage only if the footage supports it (rules above). If it does not, make fewer variants and say why in the batch note. Never pad to 10.
3. Pick hooks from real lines that suit the stage; pick styles from the brand's allowed list, preferring `energy` for TOFU, `story` for MOFU and `clean` for BOFU when the footage fits.
4. Every variant still passes the brand gate, `check_layout.py` and sync-qa, and gets its own row in Ad Index.csv.

**Editing elements adopted**
- Micro-SFX on b-roll entries, chips and key numbers via `scripts/sound_design.py`, low level.
- Background music only when the brief asks, at about -18 to -22 dB under the voice, and always also deliver a version without music.
- Tighter breath gaps at word boundaries in the Cut step.
- Loop ending: close on a real line that leads back into the opening line.

**Elements rejected (conflict with rules)**: frustrated or distressed openers, invented charts or statistics, before/after, inflation or engine metaphors for devices, non-brand fonts and palettes, creative spelling to dodge moderation, testosterone or energy claims for REJAL.
