#!/usr/bin/env python3
"""Create and manage reusable JSON design templates for static ads.

Usage:
  template_builder.py --list
  template_builder.py --scaffold my-new-template
  template_builder.py assets/templates/feature-grid.json --validate
  template_builder.py assets/templates/feature-grid.json --preview --brand drmitring --size all
  template_builder.py assets/templates/feature-grid.json --render content.json --brand slug --output-dir renders/
Define layouts as JSON, validate, preview, render with brand colours.
"""
import argparse, json, os, pathlib, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "assets" / "templates"
FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/poppins",
]
CANVAS_SIZES = {"feed": (1080, 1350), "story": (1080, 1920), "square": (1080, 1080)}

VALID_ROLES = {"primary", "accent", "background", "text", "text_on_primary", "text_secondary"}

ROLE_FALLBACKS = {
    "primary": "#022057", "accent": "#F4A261", "background": "#FFFFFF",
    "text": "#0A0A0A", "text_on_primary": "#FFFFFF", "text_secondary": "#666666",
}


def _font(name, size):
    from PIL import ImageFont
    for d in FONT_DIRS:
        p = pathlib.Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _contrast(c1, c2):
    """Simple luminance contrast check."""
    def lum(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    return abs(lum(c1) - lum(c2))


def resolve_palette(brand_slug):
    """Map colour roles to RGB tuples from brand.json."""
    pal = {k: hex_rgb(v) for k, v in ROLE_FALLBACKS.items()}
    if not brand_slug:
        return pal
    bp = ROOT / "brands" / brand_slug / "brand.json"
    if not bp.exists():
        return pal
    b = json.loads(bp.read_text(encoding="utf-8"))
    colors = b.get("colors", {})
    keys = list(colors.keys())
    if keys:
        pal["primary"] = hex_rgb(colors[keys[0]])
    if len(keys) > 1:
        pal["accent"] = hex_rgb(colors[keys[1]])
    if "canvas" in colors:
        pal["background"] = hex_rgb(colors["canvas"])
    if "neutral_black" in colors:
        pal["text"] = hex_rgb(colors["neutral_black"])
    # Compute text_on_primary
    white, black = (255, 255, 255), (0, 0, 0)
    pal["text_on_primary"] = white if _contrast(pal["primary"], white) > _contrast(pal["primary"], black) else black
    pal["text_secondary"] = tuple(int(c * 0.6 + 255 * 0.4) for c in pal["text"])
    return pal


def cmd_list():
    if not TEMPLATES_DIR.is_dir():
        print(f"No templates directory: {TEMPLATES_DIR}")
        return
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            name = t.get("name", f.stem)
            desc = t.get("description", "")
            print(f"  {name:20s} {desc[:60]}")
        except Exception as e:
            print(f"  {f.stem:20s} (error: {e})")


def cmd_scaffold(name):
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    out = TEMPLATES_DIR / f"{name}.json"
    template = {
        "name": name, "description": "", "version": 1,
        "canvas": {"feed": [1080, 1350], "story": [1080, 1920], "square": [1080, 1080]},
        "regions": {
            "header": {"feed": [0, 0, 1080, 200], "story": [0, 0, 1080, 280], "square": [0, 0, 1080, 180]},
            "body": {"feed": [60, 240, 1020, 1100], "story": [60, 320, 1020, 1500], "square": [60, 220, 1020, 860]},
            "footer": {"feed": [0, 1100, 1080, 1350], "story": [0, 1500, 1080, 1920], "square": [0, 900, 1080, 1080]},
        },
        "elements": [
            {"type": "rect", "region": "header", "color_role": "primary"},
            {"type": "text", "region": "header", "slot": "headline", "font_weight": "Bold",
             "font_size_pct": 4.5, "color_role": "text_on_primary", "align": "center",
             "max_lines": 2, "highlight": True},
            {"type": "text", "region": "body", "slot": "body_text", "font_weight": "Regular",
             "font_size_pct": 3.0, "color_role": "text", "align": "left", "max_lines": 5},
            {"type": "image", "region": "footer", "slot": "logo", "fit": "contain",
             "max_height_pct": 60},
        ],
    }
    out.write_text(json.dumps(template, indent=2), encoding="utf-8")
    print(f"OK scaffold -> {out}")


def cmd_validate(template_path):
    t = json.loads(pathlib.Path(template_path).read_text(encoding="utf-8"))
    errors = []
    for field in ("name", "canvas", "regions", "elements"):
        if field not in t:
            errors.append(f"Missing required field: {field}")
    regions = t.get("regions", {})
    canvas = t.get("canvas", {})
    for rname, rcoords in regions.items():
        for sk, cs in canvas.items():
            if sk in rcoords:
                box = rcoords[sk]
                if box[2] > cs[0] or box[3] > cs[1]:
                    errors.append(f"Region '{rname}' exceeds canvas in {sk}")
    slots = set()
    for elem in t.get("elements", []):
        if elem.get("region") and elem["region"] not in regions:
            errors.append(f"Unknown region: {elem['region']}")
        if elem.get("color_role") and elem["color_role"] not in VALID_ROLES:
            errors.append(f"Invalid color_role: {elem['color_role']}")
        fsp = elem.get("font_size_pct")
        if fsp is not None and (fsp < 1.0 or fsp > 10.0):
            errors.append(f"font_size_pct {fsp} out of range 1.0-10.0")
        slot = elem.get("slot")
        if slot:
            key = f"{elem.get('region', '')}:{slot}"
            if key in slots:
                errors.append(f"Duplicate slot '{slot}' in region '{elem.get('region', '')}'")
            slots.add(key)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"FAIL {len(errors)} errors")
        return False
    print("VALID")
    return True


def draw_highlight_text(draw, xy, text, font, color, accent):
    x, y = xy
    for i, seg in enumerate(text.split("*")):
        if not seg:
            continue
        c = accent if i % 2 == 1 else color
        draw.text((x, y), seg, fill=c, font=font)
        bbox = font.getbbox(seg)
        x += bbox[2] - bbox[0]


def render_template(template, content, pal, size_key, output):
    """Render a single template+content combination to an image."""
    from PIL import Image, ImageDraw
    canvas = template["canvas"][size_key]
    W, H = canvas[0], canvas[1]
    bg = pal.get("background", (255, 255, 255))
    im = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(im)
    regions = template.get("regions", {})
    for elem in template.get("elements", []):
        rname = elem.get("region", "")
        rbox = regions.get(rname, {}).get(size_key)
        if not rbox:
            continue
        x1, y1, x2, y2 = rbox
        etype = elem.get("type", "")
        role = elem.get("color_role", "text")
        color = pal.get(role, pal["text"])
        if etype == "rect":
            cr = elem.get("corner_radius", 0)
            if cr:
                draw.rounded_rectangle([x1, y1, x2, y2], radius=cr, fill=color)
            else:
                draw.rectangle([x1, y1, x2, y2], fill=color)
        elif etype == "accent_bar":
            bx = x1 + elem.get("x", 0)
            bw = elem.get("w", 8)
            draw.rectangle([bx, y1, bx + bw, y2], fill=color)
        elif etype == "text":
            slot = elem.get("slot", "")
            text = content.get(slot, f"[{slot}]")
            fsp = elem.get("font_size_pct", 3.0)
            fs = max(12, int(H * fsp / 100))
            weight = elem.get("font_weight", "Regular")
            fnt = _font(f"Poppins-{weight}.ttf", fs)
            align = elem.get("align", "left")
            if align == "center":
                bbox = fnt.getbbox(text.replace("*", ""))
                tw = bbox[2] - bbox[0]
                tx = x1 + (x2 - x1 - tw) // 2
            else:
                tx = x1 + 12
            ty = y1 + (y2 - y1 - fs) // 2
            if elem.get("highlight") and "*" in text:
                draw_highlight_text(draw, (tx, ty), text, fnt, color, pal["accent"])
            else:
                draw.text((tx, ty), text.replace("*", ""), fill=color, font=fnt)
        elif etype == "image":
            slot = elem.get("slot", "")
            img_path = content.get(slot)
            if img_path and pathlib.Path(img_path).exists():
                logo = Image.open(img_path).convert("RGBA")
                max_h = int((y2 - y1) * elem.get("max_height_pct", 60) / 100)
                logo.thumbnail((x2 - x1, max_h))
                lx = x1 + (x2 - x1 - logo.width) // 2
                ly = y1 + (y2 - y1 - logo.height) // 2
                im.paste(logo, (lx, ly), logo)
        elif etype == "grid_cells":
            slot = elem.get("slot", "")
            items = content.get(slot, [])
            cols_n = elem.get("cols", 2)
            rows_n = elem.get("rows", 2)
            gap = elem.get("gap", 20)
            cw = (x2 - x1 - gap * (cols_n - 1)) // cols_n
            ch = (y2 - y1 - gap * (rows_n - 1)) // rows_n
            for gi, item in enumerate(items[:cols_n * rows_n]):
                gr, gc = divmod(gi, cols_n)
                cx = x1 + gc * (cw + gap)
                cy = y1 + gr * (ch + gap)
                for ce in elem.get("cell_elements", []):
                    cs = ce.get("slot", "")
                    ct = item.get(cs, f"[{cs}]")
                    cfsp = ce.get("font_size_pct", 3.0)
                    cfs = max(12, int(H * cfsp / 100))
                    cfnt = _font(f"Poppins-{ce.get('font_weight', 'Regular')}.ttf", cfs)
                    crole = ce.get("color_role", "text")
                    cc = pal.get(crole, pal["text"])
                    draw.text((cx + 8, cy + 8), ct, fill=cc, font=cfnt)
                    cy += cfs + 4
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    im.save(str(output))
    return output


def cmd_preview(template_path, brand, sizes):
    t = json.loads(pathlib.Path(template_path).read_text(encoding="utf-8"))
    pal = resolve_palette(brand)
    # Placeholder content
    content = {}
    for elem in t.get("elements", []):
        slot = elem.get("slot")
        if slot and slot not in content:
            if elem["type"] == "grid_cells":
                content[slot] = [{cs.get("slot", "item"): f"[{cs.get('slot', 'item')}]" for cs in elem.get("cell_elements", [])} for _ in range(4)]
            else:
                content[slot] = f"[{slot}]"
    out_dir = pathlib.Path(template_path).parent / "previews"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = t.get("name", pathlib.Path(template_path).stem)
    for sk in sizes:
        if sk in t.get("canvas", {}):
            out = out_dir / f"{name}_preview_{sk}.png"
            render_template(t, content, pal, sk, out)
            print(f"OK preview {sk} -> {out}")


def cmd_render(template_path, content_path, brand, output_dir, sizes):
    t = json.loads(pathlib.Path(template_path).read_text(encoding="utf-8"))
    content = json.loads(pathlib.Path(content_path).read_text(encoding="utf-8"))
    pal = resolve_palette(brand)
    out_dir = pathlib.Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = t.get("name", pathlib.Path(template_path).stem)
    for sk in sizes:
        if sk in t.get("canvas", {}):
            out = out_dir / f"{name}_{sk}.png"
            render_template(t, content, pal, sk, out)
            print(f"OK render {sk} -> {out}")


def main():
    p = argparse.ArgumentParser(description="JSON design template builder")
    p.add_argument("template", nargs="?", help="Template JSON path")
    p.add_argument("--list", action="store_true", help="List all templates")
    p.add_argument("--scaffold", metavar="NAME", help="Scaffold a new template")
    p.add_argument("--validate", action="store_true")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--render", metavar="CONTENT", help="Content spec JSON")
    p.add_argument("--brand", default=None)
    p.add_argument("--output-dir", default="renders/static/")
    p.add_argument("--size", default="all", help="feed,story,square or all")
    a = p.parse_args()
    sizes = list(CANVAS_SIZES.keys()) if a.size == "all" else a.size.split(",")
    if a.list:
        cmd_list()
    elif a.scaffold:
        cmd_scaffold(a.scaffold)
    elif a.template and a.validate:
        cmd_validate(a.template)
    elif a.template and a.preview:
        cmd_preview(a.template, a.brand, sizes)
    elif a.template and a.render:
        cmd_render(a.template, a.render, a.brand, a.output_dir, sizes)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
