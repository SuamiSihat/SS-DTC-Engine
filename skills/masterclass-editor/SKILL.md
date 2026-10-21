---
name: masterclass-editor
description: Turn raw doctor or presenter lecture footage into a 5-episode Masterclass educational series + mandatory Series Trailer (containing a highlight clip from every episode), rendered in both 16:9 (1920x1080 full episodes + trailer for course portals / YouTube) and 9:16 (1080x1920 vertical trailer + chapter/episode cutdowns for Reels / TikTok / Shorts), complete with episode/chapter title cards, slide/diagram callouts, and numbered key-takeaway summary cards. Use when the user asks to edit a masterclass, course module, long-form tutorial, or educational lecture series.
---

# Masterclass Editor (5-Episode Series + Mandatory Trailer in 16:9 & 9:16)

Turn raw talking-head lecture footage into a structured Masterclass series (typically **5 episodes**, `EP01`–`EP05`) plus a **mandatory Masterclass Trailer** that features a highlight clip from every episode.
Read the batch brief in `briefs/<batch>.md` first; it names ONE brand slug (load `brand-rules`, default `ssclinic` Educational mode for doctor lectures). Work locally under `batches/<batch>/` (`raw/`, `work/`, `renders/16x9/`, `renders/9x16/`, `qa/`, `deliver/`). Footage and renders stay out of git.

## Series Structure (Default: 5 Episodes + 1 Mandatory Trailer)

A standard Masterclass has **5 episodes** (`EP01` to `EP05`) and **1 Series Trailer** (`EP00_Trailer`):
1. **Masterclass Trailer (MANDATORY, 16:9 + 9:16, `35–60 s`)**:
   - **Rule**: Every Masterclass batch MUST include a trailer containing **at least one highlight clip (`4–8 s`) from each of the 5 episodes** (`EP01` through `EP05`). Never deliver a Masterclass batch without its trailer, and never omit an episode from the trailer.
2. **5 Full Episodes (`EP01`–`EP05`, 16:9 `1920x1080`, `2–12 min` each)**:
   - Each episode is divided into numbered chapters (`Bab 01`, `Bab 02`, ...), supported by side-by-side slide/diagram callouts and closing with a **Numbered Key-Takeaway Summary Card** (`Ringkasan Episod`).
3. **Vertical Cutdowns (`9:16` `1080x1920`, `30–60 s` each)**:
   - Includes the **9:16 Masterclass Trailer** plus standalone 9:16 episode/chapter reels (`EP01`–`EP05`).

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
   - Map each of the 5 episodes into sequential **Chapters** (`work/chapters.json`) and select **1 standout highlight line (`4–8 s`) from each episode** (`EP01`–`EP05`) to form the **Masterclass Trailer**.
3. **Cut (Masterclass pacing + Trailer assembly)**:
   - **Episodes (`EP01`–`EP05`)**: Cut false starts, stumbles, repeated takes, and filler phrases at word boundaries while keeping calm, natural teaching cadence (`0.25–0.40 s` pause between sentences; `0.6–0.8 s` pause at chapter transitions).
   - **Mandatory Trailer (`EP00_Trailer`)**: Assemble the 5 episode highlight clips (`EP01` → `EP05`), snapping every cut to clean word boundaries. Each clip in the trailer uses its own source episode audio (never master/other-clip audio).
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
   - Verify `trailer.clips` contains one entry for **every** episode in `episodes` (`EP01`–`EP05`).
   - Render 16:9 Trailer + 5 Full Episodes to `batches/<batch>/renders/16x9/` (`1920x1080`, `libx264`, `crf 18–20`, `30 fps`).
   - Render 9:16 Trailer + 9:16 Episode/Chapter Cutdowns to `batches/<batch>/renders/9x16/` (`1080x1920`, `libx264`, `crf 20`, `30 fps`).
8. **QA gate**:
   - Re-run `scripts/check_brand.py` on all final text (trailer cards, episode/chapter titles, takeaway cards, slide labels, captions).
   - Verify the Trailer includes all 5 episodes (`EP01`–`EP05`).
   - Run `scripts/check_sync.py` (`sync-qa`, `--max-offset 0.04`) on every 16:9 and 9:16 render (for the Trailer, check each episode segment against its respective raw episode clip).
   - Run `scripts/check_layout.py` on every 9:16 render and verify `ffprobe` resolution (`1920x1080` for 16:9; `1080x1920` for 9:16).
   - Visually inspect a frame grid at every episode badge, chapter card, diagram callout, and takeaway card transition.
9. **Package**:
   - Organise into:
     - `deliver/<batch>/00-Trailer/` (`<PREFIX>_EP00_Trailer_16x9.mp4` + `.srt`/`.vtt` and `<PREFIX>_EP00_Trailer_9x16.mp4`)
     - `deliver/<batch>/16x9-Episodes/` (`EP01`–`EP05` full 16:9 MP4s + `.srt`/`.vtt` + `chapters.txt`)
     - `deliver/<batch>/9x16-Cutdowns/` (`EP01`–`EP05` 9:16 vertical MP4s)
     - `deliver/<batch>/Masterclass Index.csv`
   - Copy to NAS only after human sign-off.
10. **Learn**:
    - Append any new production or compliance lessons to `lessons.md`.

---

## Mandatory Masterclass Trailer Structure (`35–60 s`, 16:9 & 9:16)

Every Masterclass series (usually 5 episodes) must have a trailer built from real spoken moments across all 5 episodes:

| Beat | Time (approx.) | Visual & Overlay | Audio |
| --- | --- | --- | --- |
| **1. Cold-Open Hook** | `0.0–3.5 s` | Strongest single question/statement from the series + Doctor Lower Third (`Dr Rak, Men's Health Doctor`, MMC 6.3) | Clip's own real speech |
| **2. Series Title Card** | `3.5–6.5 s` | `SUAMISIHAT MASTERCLASS · 5 EPISOD`, Series Title, Presenter Name & Title, Official Brand Logo | Breath pause / subtle transition |
| **3. Episode 01 Clip** | `6.5–13.5 s` | Highlight clip from **EP01** + on-screen badge `EPISOD 01 · [EP01 Title]` | EP01 source audio |
| **4. Episode 02 Clip** | `13.5–20.5 s` | Highlight clip from **EP02** + on-screen badge `EPISOD 02 · [EP02 Title]` | EP02 source audio |
| **5. Episode 03 Clip** | `20.5–27.5 s` | Highlight clip from **EP03** + on-screen badge `EPISOD 03 · [EP03 Title]` | EP03 source audio |
| **6. Episode 04 Clip** | `27.5–34.5 s` | Highlight clip from **EP04** + on-screen badge `EPISOD 04 · [EP04 Title]` | EP04 source audio |
| **7. Episode 05 Clip** | `34.5–41.5 s` | Highlight clip from **EP05** + on-screen badge `EPISOD 05 · [EP05 Title]` | EP05 source audio |
| **8. 5-Episode Curriculum Card** | `41.5–46.0 s` | Numbered summary card (`01`–`05`) listing all 5 episode titles (`5 Topik Utama Dalam Siri Ini`) | Final spoken wrap-up or hold |
| **9. Neutral End Card** | `46.0–49.0 s` | Brand logo + neutral educational close (`Jumpa doktor untuk pemeriksaan jika ada simptom`) | Clean tail |

*Note: If a Masterclass has $N$ episodes (default $N=5$), the trailer must include one highlight clip from all $N$ episodes in sequence.*

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
| **Target duration** | Trailer: `35–60 s` · Episodes (×5): `2–12 min` each | Trailer: `35–60 s` · Cutdowns: `30–60 s` each |

---

## Hard Compliance Rules (MMC V2/2025, MAB & Brand Rules)

1. **Mandatory 5-episode trailer**: Every Masterclass batch must produce a trailer containing a real clip from each episode (`EP01`–`EP05`).
2. **Doctor identification (MMC Guideline V2/2025 6.3)**: Whenever a real doctor teaches, identify them clearly on screen with a lower third (e.g. `Dr Rak, Men's Health Doctor`) in the Trailer, at the start of each of the 5 episodes, and in every standalone 9:16 cutdown.
3. **No patient solicitation on doctor videos (MMC 3.2, 6.5; MAB 12/2007 amended 1/2025; Act 290 s.4A)**:
   - For **SS Clinic** (`ssclinic` Educational mode): real SS Clinic doctors (`appointed_doctors` in `brands/ssclinic/brand.json`) may teach evidence-based men's health topics, carry the SS Clinic logo on the end card, and be posted on the clinic page.
   - Never include a clinic CTA (*"Datang ke SS Clinic"*, *"Kami Check & Rawat"*, *"SS Clinic boleh bantu"*), booking link, promo code, price, offer, or patient testimonial in either the Trailer or the Episodes. Close with a neutral health message such as *"Jumpa doktor untuk pemeriksaan jika ada simptom"*.
4. **No live-site copy bleed**: Do not copy restricted marketing phrases from `menss.co`, `rejal.co`, or `suamisihat.clinic` into Masterclass slides, trailer cards, or takeaway cards. Every text layer must pass `scripts/check_brand.py`.
5. **Audio sync**: Each episode clip in the Trailer and each cut in the Episodes uses its own synchronized source audio. Never alter the doctor's speech speed. Every rendered 16:9 and 9:16 file must pass `scripts/check_sync.py`.
