---
name: dtc-broll
description: Plan and place b-roll, review/testimonial quote popups, safe-zone captions and lower thirds on DTC Reels ads, all at 1080x1920. Use in dtc-reels-editor step 5 (Design) for every master and hook.
---

# DTC b-roll director

Called by `dtc-reels-editor` at the Design step, after transcripts and cuts exist. Output is a `broll` plan per clip inside `work/spec.json` plus any assets, never a change to the cut or the words.

Tools (all in `scripts/`):
- `broll_suggest.py spec.json [--only 001] [--product ring,mit]` writes `work/broll_plan_<id>.md`: each kept sentence tagged (quote, myth, number, steps, concept, metaphor, product) with a suggested b-roll. Keyword rules only, so a person confirms each item.
- `broll.py` (used by `render_batch.py`) renders the quote popup from `"broll": [{"kind": "quote", "src": [start_s, end_s], "text": "<verbatim review>", "by": "Pelanggan, WhatsApp"}]` in the clip spec. Words light up in time with the speech, captions are hidden while it shows, a headline or lower third that overlaps it is ended early, and it is skipped in the hook C card layout.
- `check_layout.py renders/<name>.timeline.json ...` checks the safe area, the face and the 1080x1920 size from the layout `render_batch.py` records. Run it on every file in QA, next to `sync-qa`.
- `stock_fetch.py` finds royalty-free stock clips (Pexels, Pixabay by API; Coverr, Mixkit by manual import), keeps a licence record per clip in the NAS b-roll library and logs each use. See section 6.

## 1. When b-roll is used
B-roll exists to support or enhance what the doctor is saying at that moment. Every item is tied to a spoken phrase (word timestamps from `work/transcripts/`). No phrase, no b-roll. If the explanation is already clear on the doctor, add nothing.

| What is being said | B-roll |
|---|---|
| Doctor reads or quotes a review or testimonial | **Quote popup** (see section 2) |
| A concept or mechanism | Animated motion or diagram (`scripts/scenes.py`, `scripts/illustrations.py`) |
| A number, comparison, trend | Simple animated chart from real numbers in the brief or `prices.json` |
| A process or steps | Animated step diagram |
| A product or ingredient | Product shot or live-site b-roll (`brands/<slug>/README.md`) |
| A myth vs fact | Two-state card (Mitos / Fakta) |
| Proof (units sold, WhatsApp feedback) | Screenshot with customer names blurred (hook D) |
| A metaphor | Fruit metaphors only |

Rules:
- Density: about 3-5 items per 23-30 s master, 1.5-3 s each, at least 1 s of clean doctor between items. Longer clips get fewer, not more.
- Never cover the doctor's mouth for long. The doctor's voice stays the audio; b-roll has no audio of its own (low-level micro-SFX on entrances are allowed).
- Speed ramps only inside b-roll. Never change the speed of the speaker's footage or audio.
- No pills, no anatomy imagery, no distressed people, no before/after body claims, no invented facts, figures or sources. Abstract and calm, brand colours from `brands/<slug>/brand.json`.
- Types: animated motion, image, diagram, chart, screenshot, live-site clip, stock clip (section 6). Pick by topic, not by what is easiest.
- AI-generated imagery only if the brief approves it and a budget. Never present generated imagery as proof or as a real customer.

## 2. Review / testimonial quote popup
Trigger: the doctor is reading out a review, testimonial or customer message.
- The popup text is the real review text, verbatim, from a source supplied in the brief or the proof folder. If no source is supplied, do not create a popup and ask the human for it. Never write or paraphrase a review yourself.
- Show the exact words being read, highlighted word-by-word in time with the speech, in a quote card: quote marks, short text (max about 140 characters, trimmed only at sentence or clause edges, never changing words), and attribution as first name or initials only.
- Customer names, phone numbers and profile photos are blurred or removed. Source type (WhatsApp, Google review) may be shown only if real.
- Compliance: Malaysian MAB guidelines ban patient testimonials for clinic services, so never use a quote popup on SS Clinic content, in either mode (Educational or KOL ad). See `skills/dtc-reels-editor/references/meta-policy.md`.
- Brand gate and `check_brand.py` run on the popup text like any caption. Health claims inside a testimonial still count as claims: flag risky ones to the human.
- Entrance 0.2 s, hold while read, exit 0.2 s. Place per section 3.

## 3. Layout, face and safe zones (1080x1920)
Subtitles, lower thirds, popups and b-roll must not cover the doctor's face and must stay inside the safe margins for Instagram Reels and TikTok.

Safe area (union of Reels and TikTok, from third-party guides that cite platform ad guidance; not an official Meta/TikTok spec, re-verify each quarter, see `references/safe-zones.md`):
- Top: keep clear 270 px (y < 270 is unsafe).
- Bottom: keep clear 672 px (y > 1248 is unsafe). If the ad has a disclaimer, keep 768 px clear (y > 1152).
- Left and right: keep 120 px clear (x from 120 to 960). On TikTok the right 300 px wide column from y = 840 down holds action buttons: no text there.
- Safe rectangle: x 120-960, y 270-1248. Prefer y 300-1150 for text.

Face rule: use the face track (`work/facetrack_<id>.json`, centre fx, fy per 0.5 s from `scripts/face_track.py`). The no-go box is 400 px wide, 240 px above and 200 px below the face centre at wide framing (scaled 1.22x for tight shots and 0.8x in the hook C card); `check_layout.py` uses exactly this box. It is conservative: a FAIL is a reason to look at the frame, and a person decides when the frame is clearly fine. If the face track is missing for a clip, run it first.

Placement order for each overlay (subtitle, lower third, popup, b-roll):
1. Inside the safe rectangle, outside the face no-go zone.
2. Subtitles: below the face if the space between the face and y = 1248 fits the text; otherwise above the face. Max 2 lines, max 3 words per group, keep inside x 120-960.
3. Lower third: same rule, shown only while the doctor is introduced; never at the same time as a subtitle in the same spot.
4. Popup / b-roll: as a panel or card in the free area, or a split layout where the doctor stays fully visible. Never a full-frame cover over the doctor except a deliberate hook (A/B/C) cut.
5. If two things need the same spot, keep the subtitle and move or shorten the other.

Current layout in `render_batch.py` (checked on the Dr Rak test clip):
- Captions: bottom at y 1248, 70 pt, max 840 px wide, 3 words per group.
- Headline and lower third: y 925 (below the chin in wide shots), the headline shrinks to fit 2 lines. Hook B opens on a tight shot, so its headline goes at y 285 above the head.
- Hook C: headline on navy at y 285, the doctor in a rounded card (x 108, y 480, 864 x 860) so the face sits at about y 800-1100. The lower third goes at y 285 after the headline.
- Quote popup: bottom of the safe area (y about 1006 to 1236), captions hidden while it shows.
Known limits: the doctor leaning forward can bring the chin into the caption band for a moment, and the hook B headline sits very close to the hair in the tight opener. Check those frames by eye.

## 4. Output format
- Final video is always 1080x1920, never 2K or 4K. Downscale sources to 1080 wide before compositing; never output above 1920 tall.
- Keep fps equal to the spec (30). Keep the existing x264 settings in `render_batch.py`.
- Check every file with `ffprobe` (width 1080, height 1920) as part of QA; a file that is not 1080x1920 fails.
- B-roll assets are rendered at 1080 wide at most.

## 5. Checks before handing back
- Frame grid at every b-roll, popup and caption change: face not covered, everything inside the safe rectangle, no text clipping.
- Each b-roll item has a spoken phrase it supports and a reason; list them in the batch note.
- Popup text matches the source review word for word.
- Run `sync-qa`, `check_brand.py`, and the 1080x1920 check. Report only checks that were actually run.
- Hand to the human: popup quotes and attributions, blurred names, any risky claim.

## 6. Royalty-free stock footage
Use stock for generic scenes, textures, nature, objects and hands that support a spoken phrase. Brand live-site footage still comes first for the product.

Sources (licences checked 2026-10-21; re-check each quarter):
| Source | How | Licence accepted |
|---|---|---|
| Pexels | API (`PEXELS_API_KEY`) | Pexels License, CC0 |
| Pixabay | API (`PIXABAY_API_KEY`) | Pixabay Content License |
| Coverr | Manual download + `import` | Coverr License, real (non-AI) clips only |
| Mixkit | Manual download + `import` | Mixkit Free License only (never Restricted) |
Not used: sites that mix free and attribution-required or non-commercial licences (e.g. Videvo, Videezy).

Workflow:
1. `python scripts/stock_fetch.py search "<english keywords>"`: downloads candidates (short side at least 1080 px, 2-12 s), rejects low-res and face clips, writes a contact sheet to `<library>/_sheets/`.
2. Manual sources: put the clips and a `licenses.csv` (file, source, url, license, ai_generated, notes) in a folder, then `python scripts/stock_fetch.py import <folder>`. Clips without a source URL or licence, AI clips and Restricted/non-commercial clips are rejected.
3. A person picks from the contact sheet. Then `python scripts/stock_fetch.py use <clip_id> --batch <batch>` copies it to `batches/<batch>/work/broll/` and logs the use. Clips with status `needs_face_check` (OpenCV missing) need `--face-checked-by <name>` after a person looks.
4. `python scripts/stock_fetch.py list` shows every clip, its licence, status and how often it was used. Avoid using one clip in more than 2 batches.

Rules (from the licences and our ad rules):
- No identifiable faces by default. The licences forbid implying a person endorses a product or showing them in a negative way, and a stranger next to men's health content implies he has the condition. Objects, hands, silhouettes, nature, textures. The face check is conservative; a person still looks at every clip.
- No visible logos, brands or recognisable private buildings.
- Stock never stands in for our product, packaging, ingredients sold as ours, or SS Clinic premises (misleading use; MAB for the clinic). Generic honey is a mood shot, not "Madu Tualang".
- Stock is never proof, never a customer and never a before/after.
- AI-generated stock only if the brief approves AI imagery and a budget (same as section 1).
- All other b-roll rules apply: tied to a spoken phrase, fruit metaphors only, no pills, no anatomy, no distressed people, brand colours, editorial look optional.
- Keep the licence record (`<clip>.json`) with the clip forever; it is our proof if a platform or rights holder asks.

## 7. Ideas to consider adding (ask before building)
- Auto b-roll suggestions from the transcript: tag each sentence as concept, number, proof, product or metaphor and propose items.
- Counter or ticker for "units sold" or timeline numbers from `prices.json`.
- Myth / fact stamp card for the "Mitos atau fakta" hooks.
- Highlight ring or arrow that points at the product when it is raised.
- Safe-zone guide overlay in the frame grid so every check is visual.
- Brand tags in the stock library (section 6 tracks licences and reuse; brand tagging is not built yet).
- Subtitle position auto-switch above or below the face from the face track.
- Sound effects on b-roll entrances through `scripts/sound_design.py`, at low level and off by default.
