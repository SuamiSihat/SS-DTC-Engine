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
   The same command also runs the Meta / Malaysia keyword screen (`scripts/policy_rules.py`, notes in `skills/dtc-reels-editor/references/meta-policy.md`). Its findings are always REVIEW, tagged `[policy:<rule>]`; add `--no-policy` to skip it. Service brands (SS Clinic) get extra rules: superlatives, inducements, testimonials, doctor promotion.
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
- **SS Clinic**: two content modes (decision 2026-10-21, `content_modes` in brand.json). **Educational** (default): real SS Clinic doctor, organic posts, identified with a lower third, neutral close, NO clinic CTA, offer or testimonial. **KOL ad**: hired KOL only, never a real doctor; KKLIU number per posting in the spec; no testimonials about treatment, no discounts, before/after or superlatives. No cure/speed claims, no countdowns or 'last slots' in either mode. If the brief does not name the mode, ask.
- **REJAL**: food, never medicine. No 'ubat', 'kuat', 'tenaga batin', no green, no (R), no AI-rendered packaging. Product: Bawang Lanang + Madu Tualang; no testosterone, energy or stamina claims and no doctor endorsement (`product_rules` in brand.json).
- **MENSS**: no treatment claims for devices; no size or performance promises. Products: Penile Pump, FRESH Wash, MENSS Ring (blue). Per-product angles and styles: `product_rules` in brand.json. MENSS Ring and Dr. MIT Ring (green) never share a batch or video.
- **Mensculine**: English-first, no slang. **PERTABI**: not an ad brand (community partner); engine refuses product-ad batches.

All six guidelines mark claims as TBC. For brands other than DMR, doctor consent and claims sign-off come from the brand owner (branding@suamisihat.com).

Doctors in product ads (Dr. MIT Ring): MMC Guideline V2/2025 5.14 discourages doctors from endorsing health-related products. Keep following the brand decision, and list it on the human review note for every doctor-led product batch.
