---
name: carousel-designer
description: Create Meta Carousel ads (swipeable multi-slide, 1080x1080) with story arcs, brand colours and compliance gating. Use when the brief asks for carousels, swipeable ads, or multi-slide image ads for any SuamiSihat brand.
---

# Carousel designer

Create 3–10 slide carousel ads for Meta (Instagram/Facebook). Each slide is 1080×1080. The story arc across slides drives engagement; a single poster does not.

Tools: `scripts/render_carousel.py` (Pillow renderer), `scripts/check_brand.py` (text gate).

## 1. Story arc templates

| Template | Slides | Use for |
|---|---|---|
| `problem-journey` | Problem → 2–3 evidence/explanation → solution → CTA | Pain-point awareness → product |
| `listicle` | Cover → 3–5 numbered points → summary/CTA | Educational, benefits list |
| `myth-fact` | Cover → 2–4 myth/fact pairs → truth summary → product/CTA | Myth-busting hooks |
| `testimonial-wall` | Cover → 3–5 real reviews (names blurred) → product/CTA | Social proof (never SS Clinic) |
| `product-breakdown` | Hero product → 2–4 feature slides → comparison → CTA with price | Product deep-dive |

## 2. Design rules

- **Size**: 1080×1080 per slide (Meta carousel standard).
- **Slide indicator**: small dots at the bottom centre showing current position.
- **Swipe cue**: first slide has a subtle "Swipe →" hint at the right edge.
- **Consistency**: every slide shares the same header bar height, font sizes, brand palette (60:30:10), and layout grid.
- **`*keyword*` highlight**: words wrapped in `*` render in the brand accent colour.
- **Text density**: headline ≤ 8 words (≤ 12 for KB market). Body ≤ 3 lines per slide. Carousel wins by curiosity, not by cramming.
- **Prices**: only via `price_ref` from `brands/<slug>/prices.json`. Never typed by hand.
- **Logo**: last slide (CTA) always has the brand logo from `brands/<slug>/logos/`.

## 3. Brand restrictions

| Brand | Restriction |
|---|---|
| SS Clinic | No `testimonial-wall`, no prices, no offers, no comparison templates. Educational mode = no CTA. KOL mode = KKLIU per ad. |
| REJAL | No doctor slides (food brand, no endorsement). |
| PERTABI | No product carousels (community partner). |
| MENSS Ring / Dr. MIT Ring | Never in the same carousel or batch. |

## 4. Steps

1. Read the brief. One brand per batch.
2. If `inspired_by` in the brief, open those swipes (`swipe-library`) and take the format, not the words.
3. Write `batches/<batch>/carousel_spec.json` (see spec format below).
4. Run `python scripts/render_carousel.py batches/<batch>/carousel_spec.json`. The brand gate runs first on all text. A BLOCK stops the run.
5. Review `renders/carousel/review_sheet.jpg` (all slides side by side). Open individual PNGs only for problems the sheet shows.
6. Hand over PNGs, `carousel_index.csv`, and review notes.

## 5. Spec format

```json
{
  "brand": "drmitring",
  "carousels": [
    {
      "id": "C01",
      "template": "problem-journey",
      "slides": [
        {"type": "cover", "headline": "Kenapa *Ring* Lebih Baik?", "subline": "Swipe untuk tahu"},
        {"type": "point", "number": 1, "headline": "Tiada Ubat", "body": "100% fizikal, tiada kesan sampingan"},
        {"type": "point", "number": 2, "headline": "Mudah Digunakan", "body": "Pakai dan tanggal dalam 5 saat"},
        {"type": "cta", "headline": "Cuba Sekarang", "price_ref": "single_ring", "logo": true}
      ]
    }
  ]
}
```

Slide types: `cover`, `point`, `myth`, `fact`, `review`, `product`, `comparison`, `cta`.

## 6. Naming and packaging

- Files: `<PREFIX>-C01-<template>_slide<NN>.png` (e.g., `DMR-C01-problem-journey_slide01.png`)
- Review sheet: `renders/carousel/review_sheet.jpg`
- Index: `renders/carousel/carousel_index.csv` (columns: File, Carousel, Slide, Headline, Template, Batch)
- Packaging: `ad-packaging` puts carousel sets in their own subfolder, listed in `Ad Index.csv` with `Carousel=yes`.

## 7. Usage

```
python scripts/render_carousel.py batches/<batch>/carousel_spec.json
python scripts/render_carousel.py batches/<batch>/carousel_spec.json --only C01
python scripts/render_carousel.py batches/<batch>/carousel_spec.json --review-only
```
