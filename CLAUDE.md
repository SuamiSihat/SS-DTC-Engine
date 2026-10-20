# Project rules (DMR Reels Engine)

You turn raw doctor talking-head footage into Meta-ready Reels ads. Use the skills (source in `skills/`, installed to `.claude/skills/` by `python scripts/install_skills.py`).
Start with `dtc-reels-editor`; it calls the others (including `dtc-broll` for b-roll, review popups and safe zones).

Always:
- Read the batch brief in `briefs/` first. If a required field is missing, ask once, then proceed.
- Render on local disk under `batches/<batch>/`. Copy to NAS only at the packaging step.
- Hook audio comes from the hook's own clip, never the master's.
- Run `sync-qa` on EVERY final file. Do not deliver anything that fails.
- One brand per batch (slug in the brief). Load `brand-rules`; run `scripts/check_brand.py` first and on final text. A BLOCK stops the batch.
- Prices and unit-sold numbers come from `brands/<slug>/prices.json`, never typed by hand.
- Captions are word-by-word from the doctor's real speech. Never invent claims.
- When finished, send ALL files, not samples, plus a short note of what to confirm.
- Never write API keys or passwords into the repo.

Human decisions (do not decide alone): doctor consent and claims sign-off for brands other than DMR (brand owner), blurring customer names,
risky hook wording, final price confirmation, sign-off before launch.
