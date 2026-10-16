---
name: brand-rules
description: Load and enforce the brand guideline for the brand named in a batch brief (Dr. MIT Ring, Mensculine, MENSS, PERTABI, REJAL, SS Clinic). Use at the start of every batch and before delivery, to apply colours, fonts, logo, voice and the claims gate.
---

# Brand rules (multi-brand)
Every batch brief names ONE brand slug (`drmitring`, `mensculine`, `menss`, `pertabi`, `rejal`, `ssclinic`).
Read `brands/<slug>/brand.json` and `brands/<slug>/README.md` before planning. Never mix brands in one batch.

## Source of truth
`scripts/sync_brand_assets.py` copies the latest logos, patterns, doctor-consent status and staff claims notes from the SuamiSihat Design System repo (`DESIGN_SYSTEM_ROOT`). Run it at the start of every batch. Doctor consent comes from the design system's `metadata.json`, not from this repo.

## Gate (run first, and again on final text)
1. List every overlay/caption/hook line you plan to use into `batches/<batch>/work/texts.txt`.
2. `python scripts/check_brand.py --brand <slug> --texts batches/<batch>/work/texts.txt [--doctor "<doctor name>"]`
3. Any BLOCK: stop and tell the human; do not render around it. REVIEW items go to the human review list.
   Hooks and captions come from the doctor's real speech: if a line is flagged, choose a different line from the same transcript, never reword the claim.

## Apply from brand.json
- Colours: only the listed hex values; follow `color_rules` (contrast pairs, 60:30:10).
- Fonts: `fonts`. Install Poppins. Do not substitute.
- Logo: only supplied files from `brands/<slug>/logos/`, never retyped or recoloured; honour clear space and minimum size.
- Graphic device (pattern.svg): follow its rules; keep text on solid panels.
- Photography and b-roll: follow `photography`.
- Voice and `avoid`: follow both.

## Known differences that matter for video
- **Dr. MIT Ring**: always written 'Dr. MIT Ring' (M.I.T. = Male Intimacy Technology). Lime text/captions on black are OK; never white-on-lime; yellow only as the count chip on black; wordmark pill on black. Doctor-led ads are ALLOWED but only with SuamiSihat-appointed doctors (`appointed_doctors` in brand.json); pass the name: `check_brand.py --doctor "Dr Amir"`. Performance wording (erection, hardness, stamina, 'tahan lama') is allowed. 'Patented', 'clinically proven', 'no side effects' and 'andrologically tested' stay screened (BLOCK) because the only test evidence on file (First Article Report AMS-26043) covers material, hardness and dimensions, not efficacy or safety. Decision log: brand.json.
- **SS Clinic**: guideline says do not show or name individual doctors in brand material, no cure/speed claims, no countdowns or 'last slots'. Doctor-led talking-head ads need brand-owner approval first.
- **REJAL**: food, never medicine. No 'ubat', 'kuat', 'tenaga batin', no green, no (R), no AI-rendered packaging.
- **MENSS**: no treatment claims for devices; no size or performance promises.
- **Mensculine**: English-first, no slang. **PERTABI**: not an ad brand (community partner); engine refuses product-ad batches.

All six guidelines mark claims as TBC. For brands other than DMR, doctor consent and claims sign-off come from the brand owner (branding@suamisihat.com).
