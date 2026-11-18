---
name: client-review
description: Generate review packages for human sign-off — contact sheets, review HTML pages, watermarked previews, revision diffs and review checklists. Use after QA passes and before ad-packaging to get fast, clear human approval.
---

# Client review

Generate a review package that makes human sign-off fast and clear. Run after QA passes, before `ad-packaging`.

Tools: `scripts/review.py` (ffmpeg + Pillow), output to `batches/<batch>/review/`.

## 1. Review package contents

| Asset | Command | Description |
|---|---|---|
| **Contact sheet** | `--contact-sheet` | Grid of key frames from all renders, labeled with filename, hook, funnel, duration. One image to see everything. |
| **Review HTML** | `--html` | Self-contained HTML page with video players, QA status, checklists and comment areas. |
| **Watermarked previews** | `--watermark` | 720p watermarked copies for sharing before sign-off. |
| **Revision diff** | `--diff v1.json v2.json` | Compare two timeline JSONs — segments added/removed, duration changes, overlay changes. |
| **Review notes** | (auto-generated) | Markdown checklist of every human-decision item. |
| **All of the above** | `--all` | Run everything. |

## 2. Contact sheet

- Extract a key frame from each MP4 in `renders/` (at 33% of duration).
- Arrange in a 4-column grid, each cell ~400 px wide.
- Label each cell: filename, duration, hook type (A/B/C/D or TOFU/MOFU/BOFU parsed from filename), version style.
- Save as `review/contact_sheet.jpg` (JPEG 90% quality).

## 3. Review HTML

A single self-contained HTML file (`review/review.html`) with:
- **Embedded CSS** (dark theme, clean layout). No external dependencies.
- **Video sections**: one per render, with `<video>` player (local file paths), filename, duration, QA status.
- **Side-by-side**: A/B/C/D hook versions shown in a row for easy comparison.
- **QA badges**: sync PASS/FAIL, layout PASS/FAIL, brand-gate PASS/FAIL (parsed from `qa/` reports).
- **Checklist**: checkboxes for every human-decision item:
  - [ ] Customer names blurred
  - [ ] Prices match prices.json and live site
  - [ ] Hook wording approved (list each hook headline)
  - [ ] Sound check (voice clear, SFX level OK)
  - [ ] Doctor consent on file
  - [ ] SS Clinic content mode confirmed
  - [ ] KKLIU number present (if KOL mode)
- **Comment textarea** per video section.
- **Print-friendly**: can be saved as PDF for records.
- JavaScript for expand/collapse sections (inline, no external libs).

## 4. Watermarked previews

- For each MP4 in `renders/`, create a 720p copy in `review/watermarked/`.
- Diagonal text: `REVIEW COPY — [batch name]` in semi-transparent white, repeated across the frame.
- Lower quality (CRF 28) to discourage use as final.

## 5. Revision diff

Compare two versions of a render by their timeline JSONs:
- Segments added / removed / reordered
- Duration change (total and per segment)
- Overlays added / removed / moved
- Print a clean text summary to stdout.

## 6. Review notes template

Auto-generated `review/review_notes.md`:

```markdown
# Review Notes — [batch]

## Human decisions required
- [ ] Customer names blurred in all review popups
- [ ] Prices confirmed: [list prices used]
- [ ] Hook wording approved: [list hook headlines]
- [ ] Sound check: voice clear, music level OK
- [ ] Doctor consent: [doctor name] — on file? Y/N
- [ ] SS Clinic mode: Educational / KOL — confirmed? Y/N
- [ ] KKLIU: [number] — confirmed? Y/N (KOL mode only)

## QA results
- Sync: [PASS/FAIL per file]
- Layout: [PASS/FAIL per file]
- Brand gate: [PASS/FAIL]

## Comments
(write here)
```

## 7. Usage

```
# Everything
python scripts/review.py batches/dmr-batch-05/ --all

# Just contact sheet
python scripts/review.py batches/dmr-batch-05/ --contact-sheet

# Just HTML
python scripts/review.py batches/dmr-batch-05/ --html

# Revision diff
python scripts/review.py --diff renders/DMR01_A.timeline.json renders/DMR01_A_v2.timeline.json
```

## 8. Integration

Run after QA passes, before `ad-packaging`. The review package goes to `batches/<batch>/review/`. The human opens the HTML, checks the boxes, writes comments. Only after sign-off does packaging proceed.
