---
name: masterclass-editor
description: Turn raw doctor or presenter lecture footage into a 5-episode Masterclass educational series + mandatory 3-act Series Trailer (16:9) and Teaser (9:16) cut audio-first from real lines across every episode, rendered in both 16:9 (1920x1080 full episodes + trailer for course portals / YouTube) and 9:16 (1080x1920 teaser + chapter/episode cutdowns for Reels / TikTok / Shorts), complete with episode/chapter title cards, slide/diagram callouts, and numbered key-takeaway summary cards. Use when the user asks to edit a masterclass, course module, long-form tutorial, educational lecture series, or a trailer/teaser for one.
---

# Masterclass Editor (5-Episode Series + Mandatory Trailer in 16:9 & 9:16)

Turn raw talking-head lecture footage into a structured Masterclass series (typically **5 episodes**, `EP01`–`EP05`) plus a **mandatory Masterclass Trailer** (16:9) and **Teaser** (9:16) cut as a 3-act mini-movie from real lines across every episode.
Read the batch brief in `briefs/<batch>.md` first; it names ONE brand slug (load `brand-rules`, default `ssclinic` Educational mode for doctor lectures). Work locally under `batches/<batch>/` (`raw/`, `work/`, `renders/16x9/`, `renders/9x16/`, `qa/`, `deliver/`). Footage and renders stay out of git.

## Series Structure (Default: 5 Episodes + 1 Mandatory Trailer)

A standard Masterclass has **5 episodes** (`EP01` to `EP05`) and **1 Series Trailer** (`EP00_Trailer`):
1. **Masterclass Trailer (MANDATORY, 16:9 `60–90 s`) + 9:16 Teaser (`25–40 s`)**:
   - **Rule**: Every Masterclass batch MUST include a trailer containing **at least one real spoken line from each of the 5 episodes** (`EP01` through `EP05`). Never deliver a Masterclass batch without its trailer, and never omit an episode from it.
   - The trailer is cut as a 3-act mini-movie in **arc order**, not episode order. Read `references/trailer-craft.md` before planning any trailer.
2. **5 Full Episodes (`EP01`–`EP05`, 16:9 `1920x1080`, `2–12 min` each)**:
   - Each episode is divided into numbered chapters (`Bab 01`, `Bab 02`, ...), supported by side-by-side slide/diagram callouts and closing with a **Numbered Key-Takeaway Summary Card** (`Ringkasan Episod`).
3. **Vertical Cutdowns (`9:16` `1080x1920`, `30–60 s` each)**:
   - Includes the **9:16 Masterclass Teaser** (`EP00_Teaser`, its own cut, not a crop of the 16:9 trailer) plus standalone 9:16 episode/chapter reels (`EP01`–`EP05`).

---

## Pipeline

0. **Brand & compliance gate**:
   - Load `brand-rules` (`brands/<slug>/brand.json` and `brands/<slug>/README.md`).
   - Run `python scripts/sync_brand_assets.py` so logos and doctor status are current.
   - Run `python scripts/check_brand.py --brand <slug> --texts batches/<batch>/work/texts.txt [--doctor "<doctor name>"]` on all planned series/episode/chapter titles, trailer hooks, slide callouts, takeaway bullets, and captions. Any `BLOCK` stops the batch immediately.
1. **Prep & contact sheet**:
   - Read the brief and inspect every raw episode clip (`EP01`–`EP05`). Generate a contact sheet before planning cuts.
2. **Transcribe & 5-episode mapping**:
   - Transcribe all episode clips with Whisper (Malay or English per brief, word-level timestamps) into `work/transcripts/`.
   - Map each of the 5 episodes into sequential **Chapters** (`work/chapters.json`).
   - **Trailer breakdown** (`references/trailer-craft.md` §2): log every usable spoken sentence from all episodes into `work/trailer_linebank.json` (tags, promise, `resolves`, `standalone`) and the usable shots into `work/trailer_visualbank.json`. Select trailer lines from the banks, not by scrubbing episodes.
3. **Cut (Masterclass pacing + Trailer assembly)**:
   - **Episodes (`EP01`–`EP05`)**: Cut false starts, stumbles, repeated takes, and filler phrases at word boundaries while keeping calm, natural teaching cadence (`0.25–0.40 s` pause between sentences; `0.6–0.8 s` pause at chapter transitions).
   - **Mandatory Trailer (`EP00_Trailer`) + Teaser (`EP00_Teaser`)**: Cut **audio first** (`work/trailer_audio_map.json`: music cue, dialogue lines, moments, hard stop), then fill picture. Follow the 3-act arc, the line–moment–line rhythm and the "nothing resolves" rule with the meaning gate (`references/trailer-craft.md` §3–6). Snap every line to clean word boundaries; each line uses its own source episode audio (never master/other-clip audio). Cut two versions (A story-led, B style-led) for review.
4. **Dual-format framing (`16:9` + `9:16`)**:
   - **16:9 (`1920x1080`, 30 fps — Trailer + 5 Full Episodes)**:
     - Base framing: clean wide shot (eyes near upper-third line `y ≈ 360`).
     - Emphasised statements: subtle tight punch-in (`1.25x–1.35x`) on sentence boundaries.
     - Split-screen slide/diagram mode: speaker shifts to the left 60% (`x: 0..1152`) while the right 40% (`x: 1152..1800`) displays the diagram or takeaway card.
   - **9:16 (`1080x1920`, 30 fps — 9:16 Trailer + Episode/Chapter Cutdowns)**:
     - Apply `dtc-broll` safe zones (`x: 120..960`, `y: 270..1248`) and face no-go box (`work/facetrack_<id>.json`).
5. **Visual design (Trailer Cards, Episode/Chapter Cards, Slide Callouts & Key Takeaway Cards)**:
   - Apply the active brand's 60:30:10 palette and fonts (`Poppins` installed system-wide) from `brands/<slug>/brand.json`.
   - Build the Masterclass graphic layers (see **Visual Elements & Trailer Structure** below).
6. **Subtitles & captions**:
   - **16:9 (Trailer + Episodes)**: Export `.srt` and `.vtt` subtitle sidecars AND optionally burn 2-line sentence subtitles in the bottom safe band (`y: 890..1000`, `42 pt` Poppins Medium/SemiBold).
   - **9:16 (Trailer + Cutdowns)**: Word-by-word burned captions (max 3 words per group, `70 pt`, key terms in brand accent colour) inside `y <= 1248`, hidden whenever a lower-area card is shown.
7. **Render**:
   - Build `work/spec_masterclass.json` (see `references/spec-format.md`).
   - Verify `trailer.lines` covers **every** episode in `episodes` (`EP01`–`EP05`) at least once.
   - Render 16:9 Trailer + 5 Full Episodes to `batches/<batch>/renders/16x9/` (`1920x1080`, `libx264`, `crf 18–20`, `30 fps`).
   - Render 9:16 Trailer + 9:16 Episode/Chapter Cutdowns to `batches/<batch>/renders/9x16/` (`1080x1920`, `libx264`, `crf 20`, `30 fps`).
8. **QA gate**:
   - Re-run `scripts/check_brand.py` on all final text (trailer cards, episode/chapter titles, takeaway cards, slide labels, captions).
   - Verify the Trailer includes all 5 episodes (`EP01`–`EP05`).
   - **Trailer craft QA** (`references/trailer-craft.md` §6, §8, §10): every trailer line passes the meaning gate (complete thought, no dropped qualifier, no implied result or clinic service); no episode's key answer is spoken; music stops on the final spoken word; loudness `-14 LUFS` integrated, true peak `<= -1 dBTP`; one sound-off and one eyes-closed review pass logged in `qa/`.
   - Run `scripts/check_sync.py` (`sync-qa`, `--max-offset 0.04`) on every 16:9 and 9:16 render (for the Trailer, check each episode segment against its respective raw episode clip).
   - Run `scripts/check_layout.py` on every 9:16 render and verify `ffprobe` resolution (`1920x1080` for 16:9; `1080x1920` for 9:16).
   - Visually inspect a frame grid at every episode badge, chapter card, diagram callout, and takeaway card transition.
9. **Package**:
   - Organise into:
     - `deliver/<batch>/00-Trailer/` (`<PREFIX>_EP00_Trailer_16x9.mp4` + `.srt`/`.vtt`, `<PREFIX>_EP00_Teaser_9x16.mp4`, and a `_nomusic` version of each)
     - `deliver/<batch>/16x9-Episodes/` (`EP01`–`EP05` full 16:9 MP4s + `.srt`/`.vtt` + `chapters.txt`)
     - `deliver/<batch>/9x16-Cutdowns/` (`EP01`–`EP05` 9:16 vertical MP4s)
     - `deliver/<batch>/Masterclass Index.csv`
   - Copy to NAS only after human sign-off.
10. **Learn**:
    - Append any new production or compliance lessons to `lessons.md`.

---

## Mandatory Masterclass Trailer Structure (16:9 `60–90 s` + 9:16 Teaser `25–40 s`)

Built from real spoken lines across all 5 episodes, cut as a 3-act mini-movie in arc order. Full craft rules, music arc and examples: `references/trailer-craft.md`.

| Beat | 16:9 Trailer | 9:16 Teaser | Visual & Overlay | Audio |
| --- | --- | --- | --- | --- |
| **Act I · Hook & problem** | `0–20 s` | `0–6 s` | Cold-open `question`/`myth` line + Doctor Lower Third (`Dr Rak, Men's Health Doctor`, MMC 6.3); 1–2 `stakes` lines with moments between | Each line's own source audio over a near-silent ambient bed |
| **Signature title card** | `~20 s` (`2.5–3.5 s`) | `~6 s` | `[NAMA] MENGAJAR [TOPIK]` + `SUAMISIHAT MASTERCLASS · 5 EPISOD` + series title + brand logo | Single low hit, breath |
| **Act II · Promise** | `20–55 s` | `6–20 s` | Doctor's own promise line (only if recorded), then lines from different episodes, `line → moment → line`; small episode badge on each line | Pulse / swell enters on the turn line |
| **Act III · Climax montage** | `55–80 s` | `20–32 s` | 1-line hits from the remaining episodes cut on the beat; slow b-roll moments; **5-Episode Curriculum Card** (`01`–`05`, topics only, no answers) | Build to crescendo |
| **Sign-off** | last `5–8 s` | last `4–6 s` | Doctor's recorded sign-off (only if recorded) → Neutral End Card (brand logo + `Jumpa doktor untuk pemeriksaan jika ada simptom`) | Music hard-stops on the final spoken word, then room tone |

*Coverage rule: the 16:9 trailer includes at least one real line from all $N$ episodes (default $N=5$), in any order; the curriculum card lists them in order. The 9:16 teaser may cover fewer episodes. No line may resolve an episode's key answer, and every line must pass the meaning gate.*

---

## Visual Elements & Layout Specs

All visual cards use the brand's 60:30:10 colour hierarchy from `brands/<slug>/brand.json` (e.g. for `ssclinic`: 60% Deep Prussian Navy `#022057`, 30% Pure White `#FFFFFF` / Clinical Navy `#0F4C75`, 10% Warm Clinic Gold `#F4A261` accent).

### 1. Series / Episode Title Card (`2.5–3.5 s`)
- **Purpose**: Opens the Trailer (`5 EPISOD`) and each individual Episode (`EPISOD 01 DARIPADA 05`, `EPISOD 02 DARIPADA 05`, ...).
- **Contents**:
  - Top eyebrow tag (`Poppins SemiBold` caps, tracked `+240`, brand accent colour): e.g. `SUAMISIHAT MASTERCLASS · EPISOD 01 / 05`
  - Main episode title (`Poppins Bold / ExtraBold`, white, max 2 lines)
  - Presenter line (`Poppins Medium`): e.g. `Bersama Dr Rak, Men's Health Doctor`
  - Official brand logo from `brands/<slug>/design-system/logos/`.

### 2. Chapter Title Cards (`1.8–2.5 s`) & Episode/Chapter Badges
- **Full Chapter Bumper (`1.8–2.5 s` at each chapter boundary inside an episode)**:
  - Displays `BAB 01` / `CHAPTER 01` in brand accent (`#F4A261` gold or brand accent) above the chapter title in white on a solid brand foundation panel (`#022057` navy or brand dark), with a chapter progress bar along the bottom edge.
- **Trailer Episode Badge (shown on each clip in the Trailer)**:
  - Rounded navy/dark pill with a left gold/accent bar showing `EPISOD 01 · [Title]` (`x: 120, y: 780` in 16:9; `x: 120, y: 925` in 9:16).
- **Persistent Chapter Pill (optional, 16:9 episodes only)**:
  - Small top-left badge (`x: 120, y: 90`, `Poppins Medium 26 pt`) showing `EP01 · Bab 01: Punca Fizikal`. Never used on 9:16 where top UI covers `y < 270`.

### 3. Slide / Diagram Callouts
- Every callout must be anchored to a real spoken explanation (`scripts/broll_suggest.py` tags: `concept`, `steps`, `myth`, `number`, `metaphor`). No spoken phrase = no callout.
- **16:9 Layout (`1920x1080`)**:
  - **60/40 Split Panel**: Speaker framed in left panel (`x: 0..1152`), diagram/slide card on right (`x: 1180..1800, y: 140..840`, rounded radius `32 px`, solid brand card fill with `10%` accent border bar).
- **9:16 Layout (`1080x1920`)**:
  - Uses the safe-area card (`x: 120..960`, below chin or Hook C split card `y: 480..1340`) so the speaker's face is never covered.
- **Visual rules**:
  - Clean step diagrams, Mitos vs Fakta two-state cards, or calm clinical schematics.
  - Fruit metaphors only; never explicit anatomy, never pill bottles, never distressed men, never invented charts or unverified statistics.

### 4. Numbered Key-Takeaway Summary Cards (`Ringkasan Utama`, `3.0–5.0 s`)
- **When shown**:
  - At the end of each chapter or episode (`Ringkasan Episod 01: 3 Perkara Utama`), and in the Trailer as the **5-Episode Curriculum Card** (`01`–`05`).
  - In 9:16 cutdowns, serves as the high-save/share summary card right before the neutral end card.
- **Content rules**:
  - **100% derived from the speaker's real speech** — never invent advice, numbers, or claims not spoken by the doctor.
  - Keep each bullet concise (`<= 8 words` per bullet, 3–4 items for episode takeaways; 5 items `01`–`05` for the Trailer curriculum card).
  - Format:
    - Header: `RINGKASAN EPISOD` or `5 TOPIK UTAMA SIRI INI` (`Poppins SemiBold` caps, accent colour)
    - Rows: Number badge (`01`..`05` in brand accent pill) + concise point (`Poppins SemiBold`, white on dark panel).

---

## Safe Zones & Technical Standards

| Parameter | 16:9 Full Episodes & 16:9 Trailer | 9:16 Cutdowns & 9:16 Trailer |
| --- | --- | --- |
| **Resolution** | `1920x1080` (exact, verified by `ffprobe`) | `1080x1920` (exact, verified by `ffprobe`) |
| **Frame rate** | `30 fps` (match spec) | `30 fps` (match spec) |
| **Safe area (text/cards)** | `x: 120..1800`, `y: 90..960` | `x: 120..960`, `y: 270..1248` (`y <= 1152` with disclaimer) |
| **Doctor lower third / Ep badge** | `x: 120, y: 780` (`Poppins Bold 48 pt` + `Medium 30 pt`) | `x: 120, y: 925` (below chin, above caption band) |
| **Subtitles / captions** | Sentence subtitles at `y: 890..1000` + `.srt`/`.vtt` files | Word-by-word 3-word groups at bottom `y <= 1248` |
| **Target duration** | Trailer: `60–90 s` (max `120 s`) · Episodes (×5): `2–12 min` each | Teaser: `25–40 s` · Cutdowns: `30–60 s` each |

---

## Hard Compliance Rules (MMC V2/2025, MAB & Brand Rules)

1. **Mandatory 5-episode trailer**: Every Masterclass batch must produce a trailer containing a real spoken line from each episode (`EP01`–`EP05`). No line is cut so that it drops a qualifier, flips its meaning or implies a result (meaning gate, `references/trailer-craft.md` §6). Promise and sign-off lines are used only if the doctor actually recorded them; never assembled from separate words or synthesised.
2. **Doctor identification (MMC Guideline V2/2025 6.3)**: Whenever a real doctor teaches, identify them clearly on screen with a lower third (e.g. `Dr Rak, Men's Health Doctor`) in the Trailer, at the start of each of the 5 episodes, and in every standalone 9:16 cutdown.
3. **No patient solicitation on doctor videos (MMC 3.2, 6.5; MAB 12/2007 amended 1/2025; Act 290 s.4A)**:
   - For **SS Clinic** (`ssclinic` Educational mode): real SS Clinic doctors (`appointed_doctors` in `brands/ssclinic/brand.json`) may teach evidence-based men's health topics, carry the SS Clinic logo on the end card, and be posted on the clinic page.
   - Never include a clinic CTA (*"Datang ke SS Clinic"*, *"Kami Check & Rawat"*, *"SS Clinic boleh bantu"*), booking link, promo code, price, offer, or patient testimonial in either the Trailer or the Episodes. Close with a neutral health message such as *"Jumpa doktor untuk pemeriksaan jika ada simptom"*.
4. **No live-site copy bleed**: Do not copy restricted marketing phrases from `menss.co`, `rejal.co`, or `suamisihat.clinic` into Masterclass slides, trailer cards, or takeaway cards. Every text layer must pass `scripts/check_brand.py`.
5. **Audio sync**: Each episode clip in the Trailer and each cut in the Episodes uses its own synchronized source audio. Never alter the doctor's speech speed. Every rendered 16:9 and 9:16 file must pass `scripts/check_sync.py`.
