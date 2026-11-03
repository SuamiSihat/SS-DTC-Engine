# Static spec format (`batches/<batch>/static_spec.json`)

```json
{
  "brand": "drmitring",
  "mode": null,
  "market": "kb-hardsell",
  "inspired_by": [1046, 969],
  "sizes": ["feed", "story", "square"],
  "ads": [ { "name": "DMR-S01-VS", "template": "vs-stack", "...": "template fields below" } ]
}
```

Top level
| Field | Required | Notes |
| --- | --- | --- |
| `brand` | yes | one slug; must have an entry in `palettes.json` (PERTABI has none: not an ad brand) |
| `mode` | SS Clinic only | `educational` or `kol_ad` |
| `market` | no | `kb-hardsell`, `sj-t20-en`, `wives`, `general-bm`, `international`; an ad can override it |
| `inspired_by` | no | swipe IDs; an ad can override it; printed in `static_index.csv` |
| `sizes` | no | default `feed`, `story`. `feed` 1080x1350, `story` 1080x1920, `square` 1080x1080 |

Fields every ad can use
| Field | Notes |
| --- | --- |
| `name` | file prefix, e.g. `DMR-S01-VS` |
| `template` | `vs-stack`, `problem-solution`, `doctor-id` |
| `price_ref` | product name exactly as in `brands/<slug>/prices.json`; shows price + struck regular price. Never `price` |
| `cta` | button text (not allowed for SS Clinic Educational) |
| `legal` | small print line (e.g. a neutral close, an illustrative statement) |
| `kkliu` | SS Clinic KOL ads: KKLIU approval number, printed in the small print |
| `product_image` | path relative to the batch folder; transparent PNG cut-out works best |
| `signoff` | `false` to hide the brand sign-off line |
| `market`, `inspired_by` | override the top-level values |
| `inspired_by_risk` | policy risk of the reference, adds a REVIEW note |

`vs-stack`
| Field | Notes |
| --- | --- |
| `eyebrow` | optional small caps line above the headline |
| `headline` | required |
| `columns` | list of `{ "title", "items": [...], "verdict": "good" or "bad" }`. 2 columns = side by side; 3+ = stacked rows (title + first item). Default verdict: last column good |

`problem-solution`
| Field | Notes |
| --- | --- |
| `problem` | required, a question or problem line |
| `solution` | required |
| `points` | up to 4 short ticks |

`doctor-id`
| Field | Notes |
| --- | --- |
| `doctor` | required, must be in `appointed_doctors` where the brand requires it |
| `title`, `org` | lower third second line |
| `quote` | the doctor's real words only |
| `photo` | real photo of that doctor; transparent PNG cut-out sits on a card, a normal photo is cropped into a rounded frame |

Outputs in `batches/<batch>/renders/static/`: `<NAME>_<size>.png`, `static_index.csv`, `review_sheet.jpg`, `review_notes.md`.
The texts screened are saved in `batches/<batch>/work/static_texts.txt`.
