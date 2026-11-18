---
name: product-concept-photo
description: Make concept product photos (studio, lifestyle, luxury, hero banners, Shopify/Meta/TikTok Shop sets) by placing the REAL product cut-out into an AI-generated scene (AWS Bedrock Nova Canvas or Stability Inpaint), with the product pixels checked unchanged. Use when the user asks for product photos, concept shots, scene/lifestyle images or listing images for any SuamiSihat product brand.
---

# Product concept photo
Renderer: `scripts/render_concepts.py` (rembg cut-out + Bedrock + Pillow). Spec format: `references/spec-format.md`. Prompts: `references/prompt-library.json` (ids 1-60, 15 categories x 4, presets, placements, negatives).

The product is never generated. The engine only makes the scene around the real cut-out, then the original product pixels are pasted back and compared: any changed opaque product pixel = REJECT.

## Steps
1. Read the brief. One brand per batch. The brief must approve AI imagery and give a budget; if not, ask.
2. Collect real product photos (front, box, out of box, top-down, unboxing...). Read the text printed on the pack against `brand.json` and list it as `pack_text` (the keyword gate cannot see pack text).
3. Write `batches/<batch>/concept_spec.json` (`references/spec-format.md`). Pick shots with a `preset`, `prompts` (ids or `"all"`) or `categories`. Put the brief's budget in `budget_usd`.
4. Dry run first: `python scripts/render_concepts.py batches/<batch>/concept_spec.json --dry-run`. Fix every BLOCK; list REVIEW items on the human review note. Check the skipped list (missing source photos or props) and the "too small" list.
5. Test the pipeline with `--engine mock` (no API call, no cost), then render: `--engine nova|stability`, `--res 2k|4k`, `--only 36,57` for a subset, `--workers N`. To choose an engine, `--benchmark 3` renders 3 shots with both.
6. Send the review sheets (`review_sheet_NN.jpg`) and `review_notes.md`, not single images. Every image has `ai_scene=yes` in `concept_index.csv`.

## Spec fields read by the script
| Field | Use |
|---|---|
| `ai_imagery` | Must be `"approved"` or the gate BLOCKs. |
| `product` | Neutral description (shape, colour, material, real size; no claims), under 300 characters. |
| `pack_text` | List of text printed on the real pack; screened as REVIEW. |
| `preset` / `prompts` / `categories` | Shot selection (presets: `quick`, `shopify-listing`, `shopify-sales`, `meta-feed`, `meta-story`, `tiktok-shop`, `marketplace`, `editorial`). Default: all prompts. |
| `palette_hint`, `props`, `light`, `negative_extra` | Fill the prompt placeholders. `props` only from `brand.json` product_facts; prompts that need props are skipped without it. |
| `seed` | Base seed (default 1000). |
| `budget_usd` | BLOCK if the estimate is over it (needs `COST_*` in `config.env`). |
| `overrides` | Per prompt id: `scene`, `extra`, `aspect`, `place`, `angle`, `grade`, `seed`, `flags`. |

Source photos go in `sources`, keyed by role (`front`, `box`, `out`, `top`, `unboxing`, `lowkey`, `hires`), each a path or `{"file", "angle", "light"}`.

Auth: `AWS_BEARER_TOKEN_BEDROCK` (and `AWS_REGION`) in `config.env`, or `AWS_PROFILE` with boto3. Never in git.

## Rules
- Real product only. Never scale it up, stretch, rotate or retouch it. If a source is too small for the size, supply a larger photo, use `--res 2k` or `--skip-small`.
- 9:16 shots keep the product out of the story UI (top 250 / bottom 340 px at 1080x1920).
- Never present a concept image as a real customer, result or proof. Check whether Meta needs the "AI info" label for the placement.
- SS Clinic: only a physical item named in the brief; no doctor, treatment or clinic claim in the scene.
- No people or doctors are generated. Prompts with hands are flagged: check fingers, grip and that nothing crosses the product.

## Outputs
`batches/<batch>/renders/concepts/`: `<NAME>_<aspect>.png` masters, `delivery/<NAME>_<aspect>.jpg` (Meta sizes), `concept_index.csv`, `review_sheet_NN.jpg`, `review_notes.md`. Work files in `batches/<batch>/work/concepts/`. Names are `<BRAND>-C<cat>-<id>` (e.g. `DMR-C09-36`).

## Known gaps
- Tested only with `--engine mock` and `--dry-run` (2026-11-18). The first real Nova / Stability run is the look and cost check: run `--benchmark 3` and send the sheets before a full batch.
- `COST_*` prices are not set yet, so the budget check stays a REVIEW item until they are.
