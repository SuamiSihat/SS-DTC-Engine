---
name: static-ad-designer
description: Make static image ads (posters) for Meta from a short spec: VS comparison stacks, problem-to-solution posters and doctor-ID credibility posters, in feed 4:5, story 9:16 and square, in the brand's colours and logo, with prices from prices.json and the brand gate. Use when the user asks for posters, statics, image ads or "poster macam ni" for any SuamiSihat brand.
---

# Static ad designer
Renderer: `scripts/render_static.py` (Pillow + Poppins, same stack as the video renderer). Spec format: `references/spec-format.md`.
Colour roles per brand: `references/palettes.json` (maps roles to brand.json colour keys; never type hex values).

## Steps
1. Read the brief. One brand per batch. For SS Clinic the brief must name the content mode; if not, ask.
2. If the brief has `inspired_by`, open those swipes (`swipe-library` skill) and take the format, not the words.
3. Write `batches/<batch>/static_spec.json`. Copy rules:
   - Every line written fresh for this brand, short (headline <= 8 words for feed; KB market can carry more text).
   - Product facts only from `brand.json` `product_facts`; claims only as allowed there. Prices only via `price_ref`.
   - Doctor quotes only from the doctor's real words (transcript or approved script), never invented.
   - 2-4 variants per idea (different headline or template), so Meta has something to test.
4. Run `python scripts/render_static.py batches/<batch>/static_spec.json`. The gate runs first:
   engine rules (below) + `check_brand.py` on every line. A BLOCK stops the run. Never reword a claim to get past a block; choose a different line.
5. Open `renders/static/review_sheet.jpg`. Open a PNG at full size only where the sheet shows a possible problem, or for the
   first render of a new template (token budget, CLAUDE.md). Check: nothing clipped, text readable on a phone,
   logo intact, price matches the live site, nothing inside the story top 250 px / bottom 340 px except background.
6. Hand over the PNGs, `static_index.csv` and `review_notes.md` (REVIEW items for the human).

## Templates
| Template | Use for | Swipe examples |
| --- | --- | --- |
| `vs-stack` | Ours vs the usual alternative. 2 columns side by side, or 3+ options as stacked rows with ours last | #1046, #1268, #932, #1132 |
| `problem-solution` | Problem question, arrow, solution card with up to 4 points and the product (formula #969) | #969, #1280, #1099 |
| `doctor-id` | Doctor photo + name/title lower third + short real quote (credibility) | #741, #1136, #1207 |
Not built yet (add here when built): before/after, recruitment ("looking for 10 men"), chat-screenshot, carousel slides, infographic.

## Market (brief `market` field)
- `kb-hardsell`: bigger type, denser text, price chip and CTA always on (#1153, #1211, #1217).
- `sj-t20-en`: English, calmer, smaller type, more space, no hype words; price optional (#1207, #1222, #1253).
- `wives` / `general-bm`: default sizes.

## Engine rules (render_static.py enforces; check_brand.py screens words)
- SS Clinic: no vs-stack (comparison), no prices or offers, Educational mode = no CTA; KOL mode = no doctor and a KKLIU number per ad.
- REJAL: no doctor-id (food, never medicine).
- Doctor in any product ad: REVIEW item for MMC Guideline V2/2025 5.14; doctor must be in `appointed_doctors`.
- Doctor photos are real photos of the named, consenting doctor. Never AI-generated, never an actor.
- Product images: the text printed on the pack is NOT screened by the keyword check. Read it. Example: the current
  Dr. MIT Ring box prints "ANDROLOGICALLY TESTED", which brand.json screens; the human decides whether that pack shot can run.
- Logos come from `brands/<slug>/design-system/logos/` (run `scripts/sync_brand_assets.py`). SVG is rasterised by headless Edge/Chrome; never retyped.
- Cut out product photos with rembg (`birefnet-general-lite` fits in memory on the studio PC; the default bria model ran out of memory on 2026-10-22).

## Naming and delivery
Names like `DMR-S01-VS` (brand prefix, S + number, template code). Files: `<NAME>_<feed|story|square>.png`.
Packaging: `ad-packaging` skill, statics go in the ad set folder next to the videos, listed in `static_index.csv`.
