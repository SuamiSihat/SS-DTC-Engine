---
name: template-builder
description: Create and manage reusable design templates for static ads and carousels without editing Python code. Define layouts as JSON, validate them, preview with placeholder content, and render with real content and brand colours. Use when creating new ad formats or extending the design system.
---

# Template builder

Define reusable design templates as JSON so new ad formats can be created without editing Python. The renderer reads the template, fills slots with content, and outputs branded images.

Tools: `scripts/template_builder.py` (Pillow renderer), templates in `assets/templates/`.

## 1. Template format

A template is a JSON file in `assets/templates/<name>.json`:

```json
{
  "name": "feature-grid",
  "description": "2x2 grid of features with icons and labels",
  "version": 1,
  "canvas": {
    "feed": [1080, 1350],
    "story": [1080, 1920],
    "square": [1080, 1080]
  },
  "regions": {
    "header": {"feed": [0, 0, 1080, 200], "story": [0, 0, 1080, 280], "square": [0, 0, 1080, 180]},
    "grid":   {"feed": [60, 240, 960, 1050], "story": [60, 320, 960, 1400], "square": [60, 220, 960, 860]},
    "footer": {"feed": [0, 1100, 1080, 1350], "story": [0, 1500, 1080, 1920], "square": [0, 900, 1080, 1080]}
  },
  "elements": [
    {"type": "rect", "region": "header", "color_role": "primary", "corner_radius": 0},
    {"type": "text", "region": "header", "slot": "headline", "font_weight": "Bold", "font_size_pct": 4.5, "color_role": "text_on_primary", "align": "center", "max_lines": 2, "highlight": true},
    {"type": "accent_bar", "region": "header", "x": 0, "w": 12, "color_role": "accent"},
    {"type": "grid_cells", "region": "grid", "cols": 2, "rows": 2, "gap": 20, "slot": "features", "cell_elements": [
      {"type": "text", "slot": "icon", "font_size_pct": 6, "color_role": "accent", "align": "center"},
      {"type": "text", "slot": "label", "font_weight": "SemiBold", "font_size_pct": 3, "color_role": "text", "align": "center", "max_lines": 2}
    ]},
    {"type": "image", "region": "footer", "slot": "logo", "fit": "contain", "max_height_pct": 60}
  ]
}
```

## 2. Key concepts

### Colour roles (not hex values)

Templates reference roles, not colours. The renderer maps roles to the brand's `brand.json` palette:

| Role | Maps to | Fallback |
|---|---|---|
| `primary` | First colour in brand `colors` | `#022057` (navy) |
| `accent` | Second colour / accent in `colors` | `#F4A261` (gold) |
| `background` | Lightest colour in `colors` | `#FFFFFF` |
| `text` | Darkest colour in `colors` | `#0A0A0A` |
| `text_on_primary` | White or black, whichever has better contrast on primary | `#FFFFFF` |
| `text_secondary` | 60% opacity of `text` | `#666666` |

### Responsive regions

Each region has coordinates per canvas size (`feed`, `story`, `square`). The renderer picks the right coordinates for the requested size. This way one template works for all three formats.

Region coordinates: `[x, y, x2, y2]` (top-left to bottom-right in pixels).

### Font size as percentage

`font_size_pct` is a percentage of canvas height. Example: 4.5% of 1350 px (feed) = 60 px. This keeps text proportional across sizes.

### `*keyword*` highlighting

When `"highlight": true`, words wrapped in `*` render in the `accent` colour. Same syntax as `render_batch.py`.

## 3. Built-in templates

Ship these in `assets/templates/`:

| Template | Description |
|---|---|
| `vs-stack` | Ours vs alternative — 2 columns side by side |
| `problem-solution` | Problem → arrow → solution card with points |
| `doctor-id` | Doctor photo + name/title + real quote |
| `feature-grid` | 2×2 grid of feature icons + labels |
| `quote-card` | Large quote text + attribution + accent |
| `stat-highlight` | Big number + label + context line |

## 4. Usage

```
# List all templates
python scripts/template_builder.py --list

# Scaffold a new template
python scripts/template_builder.py --scaffold my-new-template

# Validate a template
python scripts/template_builder.py assets/templates/feature-grid.json --validate

# Preview with placeholder content
python scripts/template_builder.py assets/templates/feature-grid.json --preview --brand drmitring --size all

# Render with real content
python scripts/template_builder.py assets/templates/feature-grid.json \
  --render content_spec.json --brand drmitring --output-dir renders/static/ --size all
```

### Content spec (for `--render`)

```json
{
  "headline": "Kenapa *Ring*?",
  "features": [
    {"icon": "✓", "label": "Tiada Ubat"},
    {"icon": "✓", "label": "Mudah Digunakan"},
    {"icon": "✓", "label": "Tahan Lama"},
    {"icon": "✓", "label": "Selamat"}
  ],
  "logo": "brands/drmitring/logos/wordmark.png"
}
```

## 5. Creating new templates

1. Run `--scaffold <name>` to get a starter JSON with common regions.
2. Edit the regions and elements to define your layout.
3. Run `--validate` to check for errors (missing fields, overlapping regions, unreasonable font sizes).
4. Run `--preview` to see the layout with placeholder text.
5. Iterate until the layout looks right.
6. Save to `assets/templates/` and use in batches.

The AI or a human can create templates. No Python editing required.

## 6. Validation rules

`--validate` checks:
- All required fields present (`name`, `canvas`, `regions`, `elements`)
- Regions don't exceed canvas dimensions
- `font_size_pct` is between 1.0 and 10.0
- `color_role` values are valid role names
- `slot` names in elements are unique per region
- Every `region` referenced by an element exists
- No two non-transparent elements fully overlap in the same region
