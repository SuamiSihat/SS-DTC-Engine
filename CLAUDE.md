# Project rules (DMR Reels Engine)

You turn raw doctor talking-head footage into Meta-ready Reels ads and structured Masterclass educational series. Use the skills (source in `skills/`, installed to `.claude/skills/` by `python scripts/install_skills.py`).
- For short-form DTC Reels ads / educational Reels: start with `dtc-reels-editor`; it calls the others (including `dtc-broll` for b-roll, review popups and safe zones).
- For Masterclass series (typically **5 episodes** `EP01`–`EP05` + a **mandatory Series Trailer** containing a clip from every episode, rendered in both 16:9 `1920x1080` and 9:16 `1080x1920` with episode/chapter title cards, slide/diagram callouts and numbered key-takeaway cards): start with `masterclass-editor`.

Always:
- Read the batch brief in `briefs/` first. If a required field is missing, ask once, then proceed.
- Render on local disk under `batches/<batch>/`. Copy to NAS only at the packaging step.
- Hook and trailer clip audio comes from each clip's own source video, never another clip's.
- Run `sync-qa` on EVERY final file (including the Masterclass Trailer and every episode/cutdown). Do not deliver anything that fails.
- One brand per batch (slug in the brief). Load `brand-rules`; run `scripts/check_brand.py` first and on final text. A BLOCK stops the batch.
- Prices and unit-sold numbers come from `brands/<slug>/prices.json`, never typed by hand.
- Captions and takeaway bullets are from the doctor's real speech. Never invent claims, statistics or reviews, and never disguise flagged words with creative spelling or emojis.
- SS Clinic: Educational mode (default) = real doctor, no clinic CTA, offer or testimonial. KOL ad mode = KOL only, never a real doctor, KKLIU number per posting. See `brands/ssclinic/README.md`.
- MENSS Ring (blue) and Dr. MIT Ring (green) are separate brands: never in the same batch.
- When finished, send ALL files, not samples, plus a short note of what to confirm.
- Never write API keys or passwords into the repo.

Human decisions (do not decide alone): doctor consent and claims sign-off for brands other than DMR (brand owner), blurring customer names,
risky hook wording, final price confirmation, sign-off before launch, SS Clinic content mode and KKLIU approvals,
any doctor in a product ad (MMC Guideline V2/2025 5.14).
