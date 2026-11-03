---
name: swipe-library
description: Search, tag and cite the team's swipe file (Telegram "Swipe Files, Inspirasi Content, Meta Ads..." exports) so briefs and creatives can say "make it like #1189". Use when a brief has inspired_by IDs, when the user asks for references or ideas for a format, hook or market, or when a new Telegram export needs ingesting.
---

# Swipe library
The swipe file is the team's saved ads, posters, hooks and landing pages, with the Head of Creative's notes.
`scripts/swipe_ingest.py` turns Telegram Desktop exports into `SWIPE_LIBRARY/index.json` (one record per message ID,
media copied as `media/<id>_<n>.<ext>`). Message IDs are the shared language: "#1189" means the same swipe for everyone.

## Ingest a new export
1. In Telegram Desktop: channel > Export chat history > HTML, photos + videos on.
2. `python scripts/swipe_ingest.py ingest "<export folder>"`. Existing IDs are never overwritten, so re-exporting the whole channel is safe.
3. New records get **auto tags** from the caption (`tag_source: auto`, `reviewed: false`). They are a first pass only.

## Review tags (Claude does this with vision; a person can too)
1. `python scripts/swipe_ingest.py sheets --untagged --from <id>` makes contact sheets labelled with IDs.
2. Look at each sheet. For every swipe, set the tags from what the image actually shows plus the caption:
   `python scripts/swipe_ingest.py tag 1189 format=research-paper-overlay,doctor-explainer hook=big-technical-word funnel=mofu market=sj-t20-en brand_fit=ssclinic policy_risk=none --note "doctor + paper + moving highlight"`
3. Values must exist in `taxonomy.json`. A new pattern gets a new value there first (with a one-line meaning), never an ad-hoc tag.
4. `policy_risk` is mandatory on review. Use the team's own flags (overclaim #696, actor as doctor #747, counterfeit trick #824, Pornhub colouring #889, prank story #925) as the standard.

## Use in a batch
- Find references: `python scripts/swipe_ingest.py search --format vs-stack --market kb-hardsell --safe`
  (`--safe` hides anything with a policy risk; `--text` searches captions.)
- Put the chosen IDs in the brief (`inspired_by`), then paste the table from `python scripts/swipe_ingest.py refs <ids>` into the brief.
- Take the **format, structure and hook mechanism**, never the other brand's words, images, characters or claims.
  Copy is written fresh for our brand and passes `check_brand.py` like any other line.
- If a reference carries a policy risk, say in the brief which element is NOT being taken.
- Swipes tagged `fake-doctor`, `deceptive` or `explicit` are never used as a reference for production, only as "don't".
- SS Clinic: `before-after-clinic`, `testimonial-clinic` and `competitor-comparison` swipes cannot be followed in either content mode.

## Where things map in the engine
| Swipe format | Engine path |
| --- | --- |
| vs-stack, problem-solution, doctor-id-poster | `static-ad-designer` (`scripts/render_static.py`) |
| talking-head, doctor-explainer, podcast | `dtc-reels-editor` / `masterclass-editor` |
| research-paper-overlay, doctor-pip-broll, whiteboard, ranking, qa-format | planned: `authority-overlays` (not built yet; note it on the brief) |
| ai-faceless, ai-character, pov, candid | planned: `ai-scene-generator` (not built yet) |
| quiz-funnel, landing-page, whatsapp-blast | planned: `funnel-assets` (not built yet) |

Media and index live on the NAS (`SWIPE_LIBRARY`), never in git.
