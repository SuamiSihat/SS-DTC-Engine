---
name: doctor-reel-vox
description: Edit a real doctor's talking-head raw into a full-length educational reel with blueprint hook, Vox-style overlays, premium subs and a neutral end card (the DRA / SS Clinic "Chp 4" house look). Runs in SS Clinic Educational mode. Use when the brief asks for a full-length doctor reel, a "Vox" reel, or the DRA series look.
---

# Doctor reel, Vox template (SS Clinic Educational mode)

Origin: the approved "DRA - SocMed Chp 4" clips 6-9 (Head of Creative; editor Aliff). Visual numbers are in `references/render-spec.md`.
This version is **integrated into the DTC engine and runs in SS Clinic Educational mode**. Where the original template and the engine
rules conflict, the engine and `brands/ssclinic/brand.json` win (decision: Head of Creative, 2026-11-02). Load `brand-rules` first.

## Pipeline
0. **Brand gate**: `scripts/check_brand.py` on the brief, then again on the final hook and caption text. A BLOCK stops the batch.
1. **Prep**: read `briefs/<batch>.md` (copy `briefs/_TEMPLATE-doctor-reel.md`). Work under `batches/<batch>/` (raw/, work/, renders/, qa/, deliver/). Probe each raw (ffprobe).
2. **Disclaimer card**: raws contain the team's blue "DISCLAIMER: INI ADALAH EDUKASI TENTANG KESIHATAN LELAKI" card. Detect it per frame (render-spec section 2). Hook ends at the card; body starts after it.
3. **Transcript**: if the team's CapCut timeline for the clip exists, use its human-checked captions. Otherwise Whisper (Malay, word timestamps, the engine's existing model). Re-run unclear chunks in `ms` and `en`. Words you are unsure of stay as heard and go in the report.
4. **Gate the words (Educational)**: run every spoken line, hook line and caption through `check_brand.py`. Anything BLOCK or REVIEW is listed for a person (see "Human decisions"). Never rewrite the doctor's words and never disguise a flagged word.
5. **Plan**: hook scene, tear, 5-9 scene overlays on concrete spoken visuals, each 1.0-6 s, never across the card (render-spec section 3).
6. **Overlay images**: only as the brief approves (see "Overlays"). Present-day, modern Malaysian settings, no text, no logos.
7. **Render** 1080x1920, 30 fps, 3 parallel parts max (render-spec section 4). Sound-effects version only.
8. **End card**: neutral Educational end card, never `outro2026` (see "End card").
9. **QA**: `scripts/check_sync.py <final> <raw>` must PASS (+0.000 s), `scripts/check_layout.py`, frame grid every 3 s. Do not report an unperformed check as passed.
10. **Package** with `ad-packaging`. Copy to the NAS only after a person signs off. Append lessons to `lessons.md`.

## Standing rules (kept from the original template)
- **Keep the full raw length.** No trims, jump cuts or silence removal. Final length = full raw + end card.
- Captions come from the doctor's real speech. Simple, premium subs only.
- Overlays are present-day only: modern Malaysian people, KL condos, offices, clinics. No vintage, archival or kampung looks.
- Imagery is tasteful and non-explicit: everyone fully clothed, no visible phone screens, condom packets sealed and unbranded, no logos.
- Edit one video, report, wait for feedback before the rest of the raws.
- Report in short plain language with a numbered list of what to check.

## SS Clinic Educational overrides (these replace the original template)
| Original template | Educational mode |
| --- | --- |
| End on `outro2026` ("Kami Check dan Rawat / Chat Consultant") plus "Tekan link di bio / WhatsApp kami" | Neutral end card, no clinic CTA, link, booking line or offer |
| Keep spoken clinic lines ("di SS Klinik", "cepat-cepat datang ke klinik") | Flag as BLOCK for a person; do not ship until decided |
| "mati pucuk" kept as spoken (2026-10-21 override) | Banned term in brand.json: BLOCK for a person. Compliant alternatives: "Penurunan tenaga lelaki", "Kesihatan intim lelaki" |
| Treatment names kept and flagged | Same, plus "Treatment-specific taglines until regulatory review": REVIEW for a person |
| Avoid-list overlay imagery allowed | Brand `avoid` applies: no distressed men, no pill bottles, no cure/speed claims in on-screen text |
| Hook sticker may show a man gripping his head | Hook sticker is a calm, neutral pose (thinking, listening, looking at the camera). No distressed openers |
| Editorial grade on the doctor | Off by default (`doctor_grade: false`). Grade, grain and bloom stay on the hook scene and overlays. A person may switch it on per brief |
| No lower third | Lower third "Dr Rak, Men's Health Doctor" (`doctor_lower_third` in brand.json) from the card end for about 4 s, inside safe zones |
| Hook caps like "CEPAT LEMBIK?" | "cepat" is a review term. Keep only if it is the doctor's real line and a person approves |

## End card (Educational)
- Plain SS Clinic end card: clinic logo from `brands/ssclinic/logos/` (never retype the wordmark), brand navy, Poppins SemiBold.
- One neutral line: "Jumpa doktor untuk pemeriksaan jika ada simptom".
- 4-6 s, no button, no phone number, no QR, no "link di bio". Posting from the SS Clinic page and the clinic logo are confirmed acceptable (2026-10-21).

## Overlays
- AI images only if the brief sets `ai_overlays: approved` with a budget note. Never present generated imagery as proof or as the doctor.
- Never an AI-generated or acted doctor. Any "doctor taking a BP" or "doctor at a machine" scene shows a doctor: do not generate it. Use licensed stock (`dtc-broll` section 6, `scripts/stock_fetch.py`) or a fruit/object metaphor instead, or skip the scene.
- 3D medical renders (artery, neurons, hormone molecule) are allowed only where the brief lists them. They must be non-explicit and carry no claim.
- Stock: free clips only, 1080p or 720p, licence record kept by `stock_fetch.py`.

## Decision log
- 2026-11-03 (Head of Creative): keep the DRA Chp 4 hook lines as spoken: "MORNING ERECTION" / "ERECTION" (clip 6),
  "CEPAT LEMBIK?" (clip 9), and the clip 8 hook sticker. These pass the brand gate (0 BLOCK; "cepat" is a REVIEW term,
  now decided). New clips still get every BLOCK/REVIEW line sent for a decision.
- 2026-11-03: Dr Rak consent confirmed; claims signed off by SS Clinic per batch before posting (brands/ssclinic/brand.json).

## Human decisions (do not decide alone)
- Any spoken or on-screen line flagged BLOCK or REVIEW above (clinic CTA, "mati pucuk", treatment names, "cepat").
- SS Clinic sign-off of each batch before posting (consent for Dr Rak is on file; the gate blocks any doctor without one).
- Whether AI overlays and 3D medical renders are approved for the batch.
- Turning the doctor grade on.
- Sign-off before launch.

## Renderer
`scripts/render_doctor_reel.py` (plan format: `python scripts/render_doctor_reel.py plan-example`).
- `detect-card RAW` gives the card window; `words RAW chunks.json --card a b --out work/<clip>_words.json` gives word timings;
  `prep-layers IMAGE work/layers [--sticker] [--object]` cuts parallax layers or the hook sticker.
- `render work/plan.json` renders 3 parts in parallel, mixes SFX, adds the Educational end card, assembles, then runs
  `check_sync.py`, writes a `.timeline.json` and runs `check_layout.py` (with a face track from `face_track.py`),
  and saves a frame grid and a hook-caption crop to `qa/`. Results go to `qa/<name>_qa.json`.
- Fonts: Gelasio and Instrument Serif are in `assets/fonts/` (OFL). Missing Google Fonts are downloaded there without asking.
- End-card logo comes from `brand.json` `logo_files.on_dark_background`, found under `DESIGN_SYSTEM_ROOT`. The wordmark is never retyped.

## Known gaps
- The renderer has only been run on a synthetic smoke clip. The DRA Chp 4 raws and approved renders are not available
  (confirmed 2026-11-03), so there is no side-by-side reference. The first real Dr Rak clip is the look check:
  render ONE clip, send the frame grid and hook-caption crop, and wait for the Head of Creative's OK before the rest.
- CapCut project export (original template section 4) is not ported yet. Add it only after the renderer works.
- The cloud session branch `batch/dra-chp4-01` never reached GitHub (403), so the original render code is not recoverable. Rebuild from the spec.
