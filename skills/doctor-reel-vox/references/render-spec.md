# Render spec: doctor reel, Vox template

Source: the approved DRA Chp 4 template (clips 6-9). Educational-mode changes are marked **[EDU]**. Everything else is the approved look.
Renderer to build: `scripts/render_doctor_reel.py` (Python numpy/OpenCV/PIL frames piped to ffmpeg libx264).

## 1. Canvas and files
- 1080x1920, 30 fps. Read the source with ffmpeg rawvideo.
- Raws are the team's exports with captions hidden. Each has the disclaimer card and sometimes a glitch transition into it.
- Layout: `batches/<batch>/raw/`, `work/` (transcript, plan, overlay images, layers), `renders/`, `qa/`, `deliver/`. Paths come from `config.env`, never hard-coded user paths.

## 2. Disclaimer card detection
Per frame, downscaled to 54x96: share of pixels with B>120 and R<60. Card is ON when the share is >0.25. Examples: clip 6 7.5-9.6 s; clip 7 5.05-7.2 s; clip 8 8.75-11.0 s (blur just before); clip 9 3.8-5.667 s (raw glitch from about 3.45 s).

## 3. Plan fields (per clip)
- `CARD`: detected window. `HOOK_END = CARD[1]`: body and body font start right after the card.
- `HOOK_CAPS`: lines spoken before the card, each split into (top line, KEYWORD).
- `HOOK_SCENE`: blueprint scene, starts on the second hook line, ends before the card.
- `TEAR`: 0.37-0.4 s, from the end of the hook scene, finishing before the card or any raw glitch.
- `SCENES`: 5-9 overlays on concrete spoken visuals, 1.0-6 s each, aligned to phrase timings, never across the card. Each has a mode: `photo` (parallax) or `flat` (3D/abstract).
- Word timing: VAD frames above -36 dB inside each chunk, card window excluded, words spread over voiced frames in proportion to (letters + 1.5).

## 4. Rendering
- Render in 3 parallel parts (for example 0-24, 24-48, 48-end), never more than 3 processes. Start background jobs detached with stdin closed. Do not kill processes by command-line pattern.
- Encode: `libx264 -preset slow -crf 24 -maxrate 3.2M -bufsize 6.4M -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart`.
- Partial revision: a hook-only change re-renders only 0 to about 24 s and reassembles.

### A. Speaker treatment
- `editorial()`: desaturate 0.86; contrast `(f-0.5)*1.06+0.49`; lift blacks `0.035 + f*0.95`; split tone shadows `(1-lum)^2 * [-0.012, 0.004, 0.018]`, highlights `lum^2 * [0.022, 0.008, -0.018]`; bloom (highlights >0.72 at quarter res, blur 6, screen 0.55); vignette k=0.30 (centre at 45% height, radius 0.72). Grain amplitude 0.006.
- **[EDU]** Applied to the doctor only when the brief sets `doctor_grade: true`. Default off. Never on disclaimer-card frames.
- Hook punch-in: z 1.0 to 1.10 over the first 1.2 s (ease-out cubic) before the hook scene, then 1.06. Anchor at 22% height.

### B. Hook (copied from the reference podcast hook)
- **Blueprint background**: navy base (0.05, 0.09, 0.36) with radial falloff 1.15 - 0.55*d; grid lines every 90 px (2 px, value 1.0) and every 30 px (1 px, 0.35), blur 0.8; grid tint (0.30, 0.42, 0.85) x 0.55; noise 0.015.
- **Sticker**: B&W (luma 0.3/0.59/0.11, contrast 1.25), thick white die-cut edge (MaxFilter 15), soft blue glow (180, 215, 255) blur 14 / 0.6, drop shadow offset (8, 14) blur 10 / 0.55. Fit 860x900 centred at x=540, y=700. Pop in with ease-back over 0.45 s plus 3% slow grow, rotate +/-2 degrees, float +/-8 px. **[EDU]** calm neutral pose only.
- **"?" stickers**: Poppins Black 120/140 px, white with blue glow, pop in at +0.35/0.55/0.75/0.95 s at (150,380), (930,430), (140,980), (940,940), wobble +/-4 degrees.
- Whip in: 0.12 s crossfade from the speaker plus radial zoom blur.
- **Torn-paper wipe** (0.37-0.4 s) reveals the speaker or card: multi-sine jagged edge rising bottom to top, 14 px cream (244, 236, 220) paper band.
- **Two-tier hook captions** (final glow values = v3 minus 25%):
  - Top line: Gelasio Bold (wght 700), 72 px, white. Glow (235, 245, 255) r16 / k0.64, shadow 0.85.
  - KEYWORD: Poppins Bold 70 px UPPERCASE, azure #21A1F7. Glow (70, 170, 255) r18 / k0.94 plus wide halo (60, 160, 255) blur 26 x 0.675 underneath. Re-composite crisp letters on top. Pad canvas 60 px so the halo never clips.
  - Spacing: keyword cap-top sits 16 px under the top-line baseline.
  - Position: block centre y about 1240 on the blueprint scene, about 1120 on the speaker, with a dark horizontal scrim (Gaussian sigma 170, 0.45) behind it on the speaker.
  - Animation: top line fades and rises 12 px over 0.18 s; keyword scales 1.12 to 1.0 over 0.2 s, delayed 0.12 s.
  - Hook captions stop at the disclaimer card.
  - Keep inside the safe zones (`dtc-reels-editor/references/safe-zones.md`).

### C. Body subtitles
- Doctor on screen: Poppins SemiBold 54 px, white, soft shadow 0.9, centred y=1150.
- Over a Vox overlay: Instrument Serif Italic 66 px, cream (244, 236, 220) on a teal (18, 92, 110, alpha 225) box, padding 18 px, centred y=1130.
- Grouping: at most 26 characters and 5 words per subtitle, break at punctuation. Shows from its first word to the next group's start, held at most 0.45 s past its last word. Fade and rise 8 px over 0.15 s.
- **[EDU]** Lower third "Dr Rak, Men's Health Doctor" for about 4 s from `CARD[1]`, inside safe zones, off the face.

### D. Vox overlays (2.5D)
- Photo parallax: bg layer pushes `push=(z0, z1)` (typically 1.02-1.06 to 1.10-1.20) with drift x0.6; fg layer pushes z + `fg_extra`*p (0.04-0.06) with drift x1.4. Drift typically (0, -20..-40) or (+/-20-30, 0).
- Flat mode (3D renders): push only, (1.0, 1.12-1.16) or reverse (1.10-1.12 to 1.0).
- Film texture: flicker 3%, light-leak sweep (warm (1, 0.62, 0.32), Gaussian width 260, 0.10), gate weave +/-1.5 px, vignette.
- In/out: 0.18 s radial zoom-blur crossfade at both ends.
- Layer prep: `rembg` (`u2net_human_seg` for people, `u2net` for objects; on this PC use `birefnet-general-lite` with the image downscaled to 1024 px if the default runs out of memory). fg = image + alpha (Gaussian blur 1.2); bg = `cv2.inpaint` TELEA radius 12 over alpha>40 dilated 25x25. Hook sticker: crop to bbox, fade bottom 10-12% of alpha (power 1.3); crop the bottom 20% if clothing shows.

### E. End card
- **[EDU]** Neutral SS Clinic end card per SKILL.md. The original `outro2026` and its "Tekan link di bio / WhatsApp kami" hint are not used.

## 5. Audio
- Light SFX under the voice: whoosh (0.42 s low-passed noise) gain 0.07 at hook-scene start and each scene start, all at -0.12 s; paper tear gain 0.09 at `TEAR[0]`; 4 pops (320 to 1400 Hz chirp) gain 0.035 at hook-scene start + 0.35/0.55/0.75/0.95 s.
- Mix then `loudnorm=I=-14:TP=-1.5:LRA=11` at 48 kHz. End card audio loudnormed the same way.
- Sound-effects version only; no no-SFX render unless asked. Doctor audio is never altered.

## 6. Assemble
Concat parts (`-c copy`), then ffmpeg filter_complex: raw video padded and trimmed to exactly the raw duration with its own audio, then concat with the end card (scaled 1080x1920, 30 fps). Final length = raw + end card. Then QA: `check_sync.py` PASS at +0.000 s (limit 0.04), `check_layout.py`, frame grid every 3 s, full-res crop of hook captions (glow not clipped, letters crisp).

## 7. Report
What changed, length, sync result, then numbered items to check: uncertain words, flagged BLOCK/REVIEW lines, flagged treatment names, which images are AI-generated and where they are saved, consent and claims status.

## 8. Reference clip configs (DRA Chp 4)
| Clip | Raw length | Card | Hook scene / tear | Hook caps (top / KEYWORD) |
| --- | --- | --- | --- | --- |
| 6 | 70.495 s | 7.5-9.6 | 2.6-6.8 / 6.8-7.2 | "Mitos atau / FAKTA?", "Tadi ada / SOALAN", "Kalau masih ada / MORNING ERECTION", "maksudnya masalah / ERECTION", "/ TAK SERIUS?" |
| 7 | 59.48 s | 5.05-7.2 | 2.05-4.65 / 4.65-5.05 | "Doktor, kenapa saya / BOLEH KERAS", "bila / SEORANG DIRI,", "tapi dengan wife / SUSAH NAK MAINTAIN?" |
| 8 | 66.82 s | 8.75-11.0 | 1.65-5.25 / 5.25-5.65 | "Cuba bayangkan / TENGAH BERSAMA", "tapi you kuat fikir / ADA STRES", "ada masalah / HARI TU", "lepas tu tiba-tiba / KERAS TU HILANG", "Boleh berlaku / TAK BENDA NI?" |
| 9 | 52.24 s | 3.8-5.667 (glitch from 3.45) | 1.067-3.05 / 3.05-3.42 | "Betul ke / KONDOM", "boleh menyebabkan zakar / CEPAT LEMBIK?" |

These are historical test configs for matching the approved look. Under Educational mode several hook lines above need a person's review (explicit anatomy words, "cepat", distressed hook sticker in clip 8). Scene lists per clip are in the original template; rebuild scenes from the new transcript, not from these.
