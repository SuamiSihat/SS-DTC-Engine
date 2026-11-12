#!/usr/bin/env python3
"""Render Meta carousel ads (1080x1080 swipeable slides) from a spec JSON.

Usage:
  render_carousel.py batches/<batch>/carousel_spec.json
  render_carousel.py batches/<batch>/carousel_spec.json --only C01
  render_carousel.py batches/<batch>/carousel_spec.json --review-only
Reads brand colours/fonts from brands/<slug>/brand.json. Runs check_brand on all text.
Outputs PNGs, review_sheet.jpg, carousel_index.csv.
"""
import argparse, csv, json, os, pathlib, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
SLIDE_SIZE = (1080, 1080)
FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/poppins",
]


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


def load_brand(slug):
    bp = ROOT / "brands" / slug / "brand.json"
    if not bp.exists():
        sys.exit(f"BLOCK unknown brand '{slug}'")
    b = json.loads(bp.read_text(encoding="utf-8"))
    colors = b.get("colors", {})
    keys = list(colors.keys())
    primary = hex_rgb(colors[keys[0]]) if keys else (2, 32, 87)
    accent = hex_rgb(colors[keys[1]]) if len(keys) > 1 else (244, 162, 97)
    bg = hex_rgb(colors.get("canvas", colors.get(keys[-1], "#FBFBFB"))) if keys else (251, 251, 251)
    text = hex_rgb(colors.get("neutral_black", colors.get(keys[0], "#1C1C1C"))) if keys else (28, 28, 28)
    return b, {"primary": primary, "accent": accent, "bg": bg, "text": text}


def load_prices(slug):
    p = ROOT / "brands" / slug / "prices.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def find_logo(slug):
    logo_dir = ROOT / "brands" / slug / "logos"
    if not logo_dir.is_dir():
        logo_dir = ROOT / "brands" / slug / "design-system" / "logos"
    if logo_dir.is_dir():
        for ext in (".png", ".jpg", ".jpeg"):
            for f in logo_dir.iterdir():
                if f.suffix.lower() == ext:
                    return f
    return None


def run_brand_gate(slug, texts):
    gate = ROOT / "scripts" / "check_brand.py"
    if not gate.exists():
        return True
    all_text = "\n".join(texts)
    r = subprocess.run(
        [sys.executable, str(gate), "--brand", slug, "--text", all_text],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if "BLOCK" in (r.stdout + r.stderr):
        print(r.stdout)
        sys.stderr.write(r.stderr)
        return False
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


def draw_dots(draw, n_slides, current, y, width):
    dot_r = 6
    gap = 20
    total_w = n_slides * (dot_r * 2 + gap) - gap
    sx = (width - total_w) // 2
    for i in range(n_slides):
        cx = sx + i * (dot_r * 2 + gap) + dot_r
        fill = (255, 255, 255, 255) if i == current else (255, 255, 255, 100)
        draw.ellipse([cx - dot_r, y - dot_r, cx + dot_r, y + dot_r], fill=fill)


def render_slide(slide, idx, n_slides, pal, brand_data, prices_data, logo_img):
    from PIL import Image, ImageDraw
    W, H = SLIDE_SIZE
    stype = slide.get("type", "point")
    im = Image.new("RGB", (W, H), pal["bg"])
    draw = ImageDraw.Draw(im)
    header_h = 160
    draw.rectangle([0, 0, W, header_h], fill=pal["primary"])
    headline = slide.get("headline", "")
    body = slide.get("body", "")
    number = slide.get("number")
    title_font = _font("Poppins-Bold.ttf", 52)
    body_font = _font("Poppins-Regular.ttf", 36)
    num_font = _font("Poppins-ExtraBold.ttf", 80)
    if stype == "cover":
        draw.rectangle([0, 0, W, H], fill=pal["primary"])
        draw_highlight_text(draw, (80, H // 3), headline, title_font,
                            (255, 255, 255), pal["accent"])
        sub = slide.get("subline", "")
        if sub:
            draw.text((80, H // 3 + 80), sub, fill=(255, 255, 255), font=body_font)
        if idx == 0:
            cue = _font("Poppins-Regular.ttf", 24)
            draw.text((W - 200, H // 2), "Swipe \u2192", fill=(255, 255, 255), font=cue)
    elif stype in ("point", "myth", "fact"):
        draw_highlight_text(draw, (80, 40), headline,
                            _font("Poppins-Bold.ttf", 40), (255, 255, 255), pal["accent"])
        if number is not None:
            draw.text((80, 220), str(number), fill=pal["accent"], font=num_font)
            draw_highlight_text(draw, (200, 240), headline, title_font,
                                pal["text"], pal["accent"])
        else:
            draw_highlight_text(draw, (80, 220), headline, title_font,
                                pal["text"], pal["accent"])
        if body:
            words, lines, line = body.split(), [], ""
            for w in words:
                test = f"{line} {w}".strip()
                if body_font.getbbox(test)[2] > W - 160:
                    lines.append(line)
                    line = w
                else:
                    line = test
            if line:
                lines.append(line)
            for li, ln in enumerate(lines[:3]):
                draw.text((80, 400 + li * 50), ln, fill=pal["text"], font=body_font)
    elif stype == "cta":
        draw.rectangle([0, 0, W, H], fill=pal["primary"])
        draw_highlight_text(draw, (80, 200), headline, title_font,
                            (255, 255, 255), pal["accent"])
        price_ref = slide.get("price_ref")
        if price_ref and prices_data and price_ref in prices_data:
            pfont = _font("Poppins-ExtraBold.ttf", 64)
            draw.text((80, 400), f"RM {prices_data[price_ref]}", fill=pal["accent"], font=pfont)
        if slide.get("logo") and logo_img:
            logo = logo_img.copy()
            logo.thumbnail((300, 120))
            lx, ly = (W - logo.width) // 2, H - 200
            im.paste(logo, (lx, ly), logo if logo.mode == "RGBA" else None)
    elif stype in ("review", "product", "comparison"):
        draw_highlight_text(draw, (80, 40), headline or stype.title(),
                            _font("Poppins-Bold.ttf", 40), (255, 255, 255), pal["accent"])
        if body:
            draw.text((80, 280), body, fill=pal["text"], font=body_font)
    draw_dots(draw, n_slides, idx, H - 40, W)
    return im


def make_review_sheet(images, output):
    from PIL import Image
    cols = min(4, len(images))
    rows = (len(images) + cols - 1) // cols
    thumb = 400
    gap = 10
    sheet_w = cols * thumb + (cols + 1) * gap
    sheet_h = rows * thumb + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), (30, 30, 30))
    for i, img in enumerate(images):
        r, c = divmod(i, cols)
        t = img.copy()
        t.thumbnail((thumb, thumb))
        x = gap + c * (thumb + gap)
        y = gap + r * (thumb + gap)
        sheet.paste(t, (x, y))
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(output), quality=90)
    return output


def render_carousel(spec_path, only=None, review_only=False, skip_gate=False):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    brand_slug = spec["brand"]
    brand_data, pal = load_brand(brand_slug)
    prices_data = load_prices(brand_slug)
    logo_path = find_logo(brand_slug)
    logo_img = None
    if logo_path:
        from PIL import Image
        logo_img = Image.open(logo_path).convert("RGBA")
    batch_dir = pathlib.Path(spec_path).parent
    out_dir = batch_dir / "renders" / "carousel"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Gather all text for brand gate
    all_texts = []
    for car in spec.get("carousels", []):
        for sl in car.get("slides", []):
            for k in ("headline", "body", "subline"):
                if sl.get(k):
                    all_texts.append(sl[k].replace("*", ""))
    if not skip_gate and not run_brand_gate(brand_slug, all_texts):
        sys.exit("BLOCK: brand gate failed")
    all_images = []
    index_rows = []
    prefix = brand_slug.upper()[:3]
    for car in spec.get("carousels", []):
        cid = car["id"]
        if only and cid != only:
            continue
        template = car.get("template", "custom")
        slides = car.get("slides", [])
        for si, slide in enumerate(slides):
            img = render_slide(slide, si, len(slides), pal, brand_data, prices_data, logo_img)
            fname = f"{prefix}-{cid}-{template}_slide{si+1:02d}.png"
            if not review_only:
                img.save(str(out_dir / fname))
            all_images.append(img)
            index_rows.append({
                "File": fname, "Carousel": cid, "Slide": si + 1,
                "Headline": slide.get("headline", ""), "Template": template,
                "Batch": batch_dir.name,
            })
    # Review sheet
    rs = out_dir / "review_sheet.jpg"
    make_review_sheet(all_images, rs)
    print(f"OK review sheet -> {rs}")
    if not review_only:
        idx_path = out_dir / "carousel_index.csv"
        with open(idx_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["File", "Carousel", "Slide", "Headline", "Template", "Batch"])
            w.writeheader()
            w.writerows(index_rows)
        print(f"OK {len(all_images)} slides, {len(spec.get('carousels',[]))} carousels -> {out_dir}")
    return all_images


def main():
    p = argparse.ArgumentParser(description="Render Meta carousel ads")
    p.add_argument("spec", help="carousel_spec.json path")
    p.add_argument("--only", default=None, help="Render only this carousel ID")
    p.add_argument("--review-only", action="store_true", help="Generate review sheet only")
    p.add_argument("--skip-gate", action="store_true", help="Skip brand gate")
    a = p.parse_args()
    render_carousel(a.spec, a.only, a.review_only, a.skip_gate)


if __name__ == "__main__":
    main()
