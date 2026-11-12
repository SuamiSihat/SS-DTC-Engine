#!/usr/bin/env python3
"""Generate branded thumbnails from video or images.

Usage:
  render_thumbnail.py renders/EP03.mp4 --template masterclass-episode --title "Punca Utama ED" --episode 3 --brand ssclinic --sizes 16x9,9x16,1x1 --auto-frame
  render_thumbnail.py renders/EP03.mp4 --template reel-cover --title "3 Fakta" --frame-time 8.5 --brand drmitring
  render_thumbnail.py work/keyframe.png --template grid-square --title "Episod Baru" --brand ssclinic
  render_thumbnail.py --batch-spec work/thumbnail_spec.json --output-dir thumbnails/
Templates: masterclass-episode, masterclass-trailer, reel-cover, grid-square, course-hero
"""
import argparse, json, os, pathlib, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/poppins",
]

TEMPLATE_SIZES = {
    "masterclass-episode": (1280, 720),
    "masterclass-trailer": (1280, 720),
    "reel-cover": (1080, 1920),
    "grid-square": (1080, 1080),
    "course-hero": (1920, 1080),
}

SIZE_MAP = {
    "16x9": (1280, 720), "9x16": (1080, 1920), "1x1": (1080, 1080),
    "16x9_hd": (1920, 1080),
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


def load_brand(slug):
    bp = ROOT / "brands" / slug / "brand.json"
    if not bp.exists():
        return {}, (2, 32, 87), (244, 162, 97)
    b = json.loads(bp.read_text(encoding="utf-8"))
    colors = b.get("colors", {})
    keys = list(colors.keys())
    primary = hex_rgb(colors[keys[0]]) if keys else (2, 32, 87)
    accent = hex_rgb(colors[keys[1]]) if len(keys) > 1 else (244, 162, 97)
    return b, primary, accent


def find_logo(slug):
    for d in ("logos", "design-system/logos"):
        ld = ROOT / "brands" / slug / d
        if ld.is_dir():
            for ext in (".png", ".jpg"):
                for f in ld.iterdir():
                    if f.suffix.lower() == ext:
                        return f
    return None


def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


def extract_frame(video, time_s, output):
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", str(time_s),
         "-i", str(video), "-frames:v", "1", str(output)],
        capture_output=True,
    )
    return pathlib.Path(output).exists()


def score_sharpness(img_path):
    """Score frame sharpness using Laplacian variance."""
    try:
        import cv2
        import numpy as np
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        return float(cv2.Laplacian(img, cv2.CV_64F).var())
    except ImportError:
        # Fallback: use PIL edge detection approximation
        try:
            from PIL import Image, ImageFilter
            im = Image.open(img_path).convert("L")
            edges = im.filter(ImageFilter.FIND_EDGES)
            import statistics
            pixels = list(edges.getdata())
            return statistics.variance(pixels) if len(pixels) > 1 else 0.0
        except Exception:
            return 0.0


def auto_select_frame(video, n_candidates=10):
    """Extract n candidates, score by sharpness, return best time."""
    dur = probe_duration(video)
    if dur <= 0:
        return 0.0
    import tempfile
    best_t, best_score = dur * 0.33, 0.0
    with tempfile.TemporaryDirectory() as td:
        for i in range(n_candidates):
            t = dur * (i + 1) / (n_candidates + 1)
            fp = pathlib.Path(td) / f"cand_{i:02d}.png"
            if extract_frame(video, t, fp):
                sc = score_sharpness(fp)
                if sc > best_score:
                    best_score = sc
                    best_t = t
    return best_t


def compose_thumbnail(keyframe_path, title, subtitle, episode, brand_slug,
                      target_w, target_h, template, output):
    """Compose a branded thumbnail image."""
    from PIL import Image, ImageDraw, ImageFilter
    brand_data, primary, accent = load_brand(brand_slug) if brand_slug else ({}, (2, 32, 87), (244, 162, 97))
    # Load key frame
    kf = Image.open(keyframe_path).convert("RGB")
    # Background: blurred + darkened
    bg = kf.copy()
    bg = bg.resize((target_w, target_h))
    bg = bg.filter(ImageFilter.GaussianBlur(30))
    from PIL import ImageEnhance
    bg = ImageEnhance.Brightness(bg).enhance(0.4)
    im = bg.copy()
    draw = ImageDraw.Draw(im)
    # Overlay sharp key frame
    kf_copy = kf.copy()
    if target_w / target_h > 1:  # landscape
        # Face in right 2/3
        kf_h = target_h
        kf_w = int(kf_copy.width * kf_h / kf_copy.height)
        kf_copy = kf_copy.resize((kf_w, kf_h))
        paste_x = target_w - kf_w
        im.paste(kf_copy, (max(0, paste_x), 0))
    elif target_w / target_h < 1:  # portrait
        # Face top half
        kf_w = target_w
        kf_h = int(kf_copy.height * kf_w / kf_copy.width)
        kf_copy = kf_copy.resize((kf_w, kf_h))
        im.paste(kf_copy, (0, 0))
    else:  # square
        kf_copy = kf_copy.resize((target_w, target_h))
        im.paste(kf_copy, (0, 0))
    # Gradient overlay at bottom
    grad_h = target_h // 3
    for yi in range(grad_h):
        alpha = int(255 * 0.15 * yi / grad_h)
        y = target_h - grad_h + yi
        draw.rectangle([0, y, target_w, y + 1], fill=(*primary, alpha))
    # Episode badge
    if episode is not None:
        badge_text = f"EP{episode:02d}"
        bfont = _font("Poppins-Bold.ttf", 28)
        bb = bfont.getbbox(badge_text)
        bw, bh = bb[2] - bb[0] + 24, bb[3] - bb[1] + 12
        draw.rounded_rectangle([20, 20, 20 + bw, 20 + bh], radius=8, fill=accent)
        draw.text((32, 22), badge_text, fill=(255, 255, 255), font=bfont)
    # Title
    tfont = _font("Poppins-Bold.ttf", max(24, target_h // 12))
    if target_w / target_h > 1:  # landscape: text left
        tx, ty = 40, target_h - 160
    elif target_w / target_h < 1:  # portrait: text below
        tx, ty = 40, target_h * 2 // 3
    else:  # square: bottom center
        tx, ty = 40, target_h - 180
    # Drop shadow
    draw.text((tx + 2, ty + 2), title, fill=(0, 0, 0, 153), font=tfont)
    draw.text((tx, ty), title, fill=(255, 255, 255), font=tfont)
    # Subtitle
    if subtitle:
        sfont = _font("Poppins-Medium.ttf", max(18, target_h // 20))
        draw.text((tx + 2, ty + tfont.size + 12), subtitle, fill=(0, 0, 0, 100), font=sfont)
        draw.text((tx, ty + tfont.size + 10), subtitle, fill=(220, 220, 220), font=sfont)
    # Logo bottom-right
    logo_path = find_logo(brand_slug) if brand_slug else None
    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((target_w // 5, target_h // 8))
        lx = target_w - logo.width - 20
        ly = target_h - logo.height - 20
        im.paste(logo, (lx, ly), logo)
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    im.save(str(output))
    return output


def generate_thumbnail(source, template, title, subtitle, episode, brand,
                       sizes, auto_frame, frame_time, output_dir):
    """High-level: extract frame + compose for each requested size."""
    import tempfile
    src = pathlib.Path(source)
    out_dir = pathlib.Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    is_video = src.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv", ".webm")
    results = []
    if is_video:
        if auto_frame:
            ft = auto_select_frame(src)
        elif frame_time is not None:
            ft = frame_time
        else:
            ft = probe_duration(src) * 0.33
        kf_path = out_dir / f"{src.stem}_keyframe.png"
        extract_frame(src, ft, kf_path)
    else:
        kf_path = src
    for size_str in sizes:
        if size_str in SIZE_MAP:
            tw, th = SIZE_MAP[size_str]
        elif size_str in TEMPLATE_SIZES:
            tw, th = TEMPLATE_SIZES[size_str]
        else:
            tw, th = TEMPLATE_SIZES.get(template, (1280, 720))
        fname = f"{src.stem}_{template}_{size_str}.png"
        out = out_dir / fname
        compose_thumbnail(kf_path, title or "", subtitle, episode, brand,
                          tw, th, template, out)
        results.append(out)
        print(f"OK {fname}")
    return results


def run_batch_spec(spec_path, output_dir):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    brand = spec.get("brand", "")
    out_dir = pathlib.Path(output_dir)
    total = 0
    for item in spec.get("thumbnails", []):
        sizes = item.get("sizes", ["16x9"])
        r = generate_thumbnail(
            source=item["source"], template=item.get("template", "masterclass-episode"),
            title=item.get("title", ""), subtitle=item.get("subtitle"),
            episode=item.get("episode"), brand=brand,
            sizes=sizes, auto_frame=item.get("auto_frame", True),
            frame_time=item.get("frame_time"), output_dir=out_dir,
        )
        total += len(r)
    print(f"OK {total} thumbnails -> {out_dir}")


def main():
    p = argparse.ArgumentParser(description="Generate branded thumbnails")
    p.add_argument("source", nargs="?", help="Video or image source")
    p.add_argument("--template", default="masterclass-episode",
                   choices=list(TEMPLATE_SIZES.keys()))
    p.add_argument("--title", default="")
    p.add_argument("--subtitle", default=None)
    p.add_argument("--episode", type=int, default=None)
    p.add_argument("--brand", default=None)
    p.add_argument("--sizes", default="16x9", help="Comma-separated: 16x9,9x16,1x1")
    p.add_argument("--auto-frame", action="store_true")
    p.add_argument("--frame-time", type=float, default=None)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--batch-spec", default=None, help="Batch spec JSON")
    a = p.parse_args()
    if a.batch_spec:
        run_batch_spec(a.batch_spec, a.output_dir or "thumbnails/")
        return
    if not a.source:
        p.error("need <source> or --batch-spec")
    out_dir = a.output_dir
    if not out_dir:
        out_dir = str(pathlib.Path(a.source).parent / "thumbnails")
    sizes = a.sizes.split(",")
    generate_thumbnail(a.source, a.template, a.title, a.subtitle, a.episode,
                       a.brand, sizes, a.auto_frame, a.frame_time, out_dir)


if __name__ == "__main__":
    main()
