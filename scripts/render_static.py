#!/usr/bin/env python3
"""Render static image ads (posters) from a batch static spec.

Usage: python scripts/render_static.py batches/<batch>/static_spec.json [--only NAME] [--sizes feed,story,square] [--skip-gate]
Spec:  skills/static-ad-designer/references/spec-format.md
Templates: vs-stack, problem-solution, doctor-id
Sizes: feed 1080x1350 (4:5), story 1080x1920 (9:16, Stories/Reels safe zones), square 1080x1080
Writes batches/<batch>/renders/static/<NAME>_<size>.png, static_index.csv and review_sheet.jpg.

Gate (always, before rendering): engine rules for statics (SS Clinic modes, REJAL no doctor, prices only from
prices.json), then scripts/check_brand.py on every line of text. Any BLOCK stops the run.
Colours: role map in skills/static-ad-designer/references/palettes.json -> hex values from brands/<slug>/brand.json.
Fonts: Poppins installed system-wide. Logos: brands/<slug>/design-system/logos/ (SVG rasterised with headless Edge/Chrome).
"""
import argparse, csv, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
PALETTES = ROOT / "skills" / "static-ad-designer" / "references" / "palettes.json"
CACHE = ROOT / "batches" / "_cache" / "logos"
FONT_DIRS = [r"C:\Windows\Fonts", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"), "/usr/share/fonts/truetype/poppins"]
SIZES = {"feed": (1080, 1350), "story": (1080, 1920), "square": (1080, 1080)}
# margins (left, top, right, bottom). Story keeps clear of the top profile bar and bottom reply/CTA bar.
MARGINS = {"feed": (72, 64, 72, 64), "story": (96, 250, 96, 340), "square": (64, 56, 64, 56)}
TEMPLATES = ("vs-stack", "problem-solution", "doctor-id")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------- basics ----------
def font(name, size):
    for d in FONT_DIRS:
        p = pathlib.Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise SystemExit(f"Font not found: {name} (install Poppins system-wide)")

def hex_rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def load_brand(slug):
    bp = ROOT / "brands" / slug / "brand.json"
    if not bp.exists():
        sys.exit(f"BLOCK unknown brand '{slug}'")
    b = json.loads(bp.read_text(encoding="utf-8"))
    pals = json.loads(PALETTES.read_text(encoding="utf-8"))
    if slug not in pals:
        sys.exit(f"BLOCK no static palette for '{slug}' (not an ad brand, or add it to {PALETTES.relative_to(ROOT)})")
    pal = pals[slug]
    col = {}
    for role in ("bg", "text", "accent", "on_accent", "card", "on_card", "chip", "on_chip"):
        key = pal[role]
        if key not in b["colors"]:
            sys.exit(f"palettes.json maps {slug}.{role} to '{key}', which is not in brand.json colors")
        col[role] = hex_rgb(b["colors"][key])
    return b, pal, col

def prices(slug):
    p = ROOT / "brands" / slug / "prices.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

# ---------- logo (supplied files only; SVG rasterised, never retyped) ----------
def find_browser():
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", shutil.which("chromium") or "", shutil.which("google-chrome") or ""):
        if p and pathlib.Path(p).exists():
            return p
    return None

def svg_to_png(svg, out, width=1400):
    br = find_browser()
    if not br:
        return False
    tmp = pathlib.Path(tempfile.mkdtemp())
    page = tmp / "logo.html"
    page.write_text(f'<html><body style="margin:0;background:transparent"><img src="{svg.resolve().as_uri()}" style="width:{width}px;display:block"></body></html>', encoding="utf-8")
    shot = tmp / "shot.png"
    cmd = [br, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
           f"--window-size={width + 40},{width + 40}", f"--screenshot={shot}", page.resolve().as_uri()]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except Exception:
        return False
    if not shot.exists():
        return False
    im = Image.open(shot).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return False
    im.crop(bbox).save(out)
    return True

def logo_image(slug, pal, warn):
    name = pal.get("logo")
    if not name:
        return None
    src = ROOT / "brands" / slug / "design-system" / "logos" / name
    if not src.exists():
        warn.append(f"Logo {name} not found: run scripts/sync_brand_assets.py. Rendered WITHOUT logo.")
        return None
    if src.suffix.lower() == ".png":
        return Image.open(src).convert("RGBA")
    CACHE.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(src.read_bytes()).hexdigest()[:10]
    out = CACHE / f"{src.stem}_{h}.png"
    if not out.exists() and not svg_to_png(src, out):
        warn.append(f"Could not rasterise {name} (no Edge/Chrome). Rendered WITHOUT logo.")
        return None
    return Image.open(out).convert("RGBA")

# ---------- text helpers ----------
NBSP = "\u00a0"
KEEP_TOGETHER = []  # brand names that must never break across lines (set in main from brand.json)

def wrap(draw, text, fnt, maxw):
    text = str(text)
    for k in KEEP_TOGETHER:
        text = text.replace(k, k.replace(" ", NBSP))
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split(" "):
            if not w:
                continue
            t = (cur + " " + w).strip()
            if cur and draw.textlength(t, font=fnt) > maxw:
                lines.append(cur); cur = w
            else:
                cur = t
        lines.append(cur)
    return [l.replace(NBSP, " ") for l in lines]

def fit(draw, text, face, maxw, max_size, min_size, max_lines, max_h=None):
    """Largest font size where the text wraps into <= max_lines and fits max_h."""
    size = max_size
    while True:
        f = font(face, size)
        lines = wrap(draw, text, f, maxw)
        lh = int(size * 1.18)
        ok = len(lines) <= max_lines and all(draw.textlength(l, font=f) <= maxw for l in lines)
        if max_h is not None:
            ok = ok and lh * len(lines) <= max_h
        if ok or size <= min_size:
            return f, lines, lh
        size -= 2

def draw_lines(draw, xy, lines, f, lh, fill, align="left", width=None):
    x, y = xy
    for l in lines:
        if align == "center" and width:
            draw.text((x + (width - draw.textlength(l, font=f)) / 2, y), l, font=f, fill=fill)
        else:
            draw.text((x, y), l, font=f, fill=fill)
        y += lh
    return y

def tick(draw, x, y, s, col, good=True, w=None):
    w = w or max(4, s // 6)
    if good:
        draw.line([(x, y + s * 0.55), (x + s * 0.38, y + s * 0.9), (x + s, y + s * 0.12)], fill=col, width=w, joint="curve")
    else:
        draw.line([(x + s * 0.12, y + s * 0.12), (x + s * 0.88, y + s * 0.88)], fill=col, width=w)
        draw.line([(x + s * 0.88, y + s * 0.12), (x + s * 0.12, y + s * 0.88)], fill=col, width=w)

def paste_fit(canvas, im, box, align="center", halign="center"):
    x0, y0, x1, y1 = box
    im = im.copy(); im.thumbnail((x1 - x0, y1 - y0), Image.LANCZOS)
    x = x0 + (x1 - x0 - im.width) // 2 if halign == "center" else x0
    y = y0 + (y1 - y0 - im.height) // 2 if align == "center" else y1 - im.height
    canvas.alpha_composite(im, (x, y))
    return (x, y, x + im.width, y + im.height)

def rounded_photo(path, w, h, r):
    im = Image.open(path).convert("RGBA")
    scale = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * scale) + 1, int(im.height * scale) + 1), Image.LANCZOS)
    left, top = (im.width - w) // 2, max(0, int((im.height - h) * 0.25))
    im = im.crop((left, top, left + w, top + h))
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), m, m))
    return im

def has_alpha(path):
    im = Image.open(path)
    return im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 250

# ---------- shared frame: logo top, footer (price chip, CTA, sign-off) ----------
class Frame:
    def __init__(self, size, col, market):
        self.W, self.H = SIZES[size]; self.size = size; self.col = col
        self.im = Image.new("RGBA", (self.W, self.H), col["bg"] + (255,))
        self.d = ImageDraw.Draw(self.im)
        l, t, r, b = MARGINS[size]
        self.L, self.T, self.R, self.B = l, t, self.W - r, self.H - b
        self.cw = self.R - self.L
        # market density: KB = big and dense (hard-sell), T20 = calmer, smaller type
        self.k = {"kb-hardsell": 1.12, "sj-t20-en": 0.86}.get(market, 1.0)
        self.market = market

    def s(self, px):
        base = px * (self.W / 1080)
        if self.size == "square": base *= 0.86
        return int(base * self.k)

    def logo(self, logo):
        if logo is None:
            return self.T
        h = self.s(64) if self.size != "square" else self.s(54)
        box = (self.L, self.T, self.L + int(self.cw * 0.42), self.T + h)
        paste_fit(self.im, logo, box, halign="left")
        return self.T + h + self.s(36)

    def footer(self, price=None, cta=None, signoff="", legal=""):
        """Draws from the bottom up. Returns the y where the body must end."""
        y = self.B; c = self.col
        if legal:
            f = font("Poppins-Regular.ttf", self.s(20)); lines = wrap(self.d, legal, f, self.cw)
            y -= int(self.s(20) * 1.3) * len(lines)
            draw_lines(self.d, (self.L, y), lines, f, int(self.s(20) * 1.3), c["text"])
            y -= self.s(10)
        if signoff:
            f = font("Poppins-Medium.ttf", self.s(22)); y -= self.s(30)
            self.d.text((self.L, y), signoff, font=f, fill=c["text"]); y -= self.s(18)
        if price or cta:
            bh = self.s(96); y -= bh
            x = self.L
            if price:
                fp = font("Poppins-ExtraBold.ttf", self.s(46)); fo = font("Poppins-Medium.ttf", self.s(24))
                pw = self.d.textlength(price["now"], font=fp)
                ow = self.d.textlength(price["was"], font=fo) if price.get("was") else 0
                w = int(max(pw, ow) + self.s(48))
                self.d.rounded_rectangle([x, y, x + w, y + bh], self.s(18), fill=c["chip"])
                if price.get("was"):
                    ty = y + self.s(8)
                    self.d.text((x + self.s(24), ty), price["was"], font=fo, fill=c["on_chip"])
                    sy = ty + self.s(18); self.d.line([(x + self.s(22), sy), (x + self.s(26) + ow, sy)], fill=c["on_chip"], width=max(2, self.s(3)))
                    self.d.text((x + self.s(24), y + self.s(34)), price["now"], font=fp, fill=c["on_chip"])
                else:
                    self.d.text((x + self.s(24), y + (bh - self.s(56)) / 2), price["now"], font=fp, fill=c["on_chip"])
                x += w + self.s(18)
            if cta:
                f, lines, lh = fit(self.d, cta, "Poppins-Bold.ttf", self.R - x - self.s(48), self.s(38), self.s(22), 2, bh - self.s(16))
                self.d.rounded_rectangle([x, y, self.R, y + bh], self.s(18), fill=c["accent"])
                th = lh * len(lines)
                draw_lines(self.d, (x + self.s(24), y + (bh - th) / 2 - self.s(4)), lines, f, lh, c["on_accent"])
            y -= self.s(28)
        return y

# ---------- templates ----------
def t_vs_stack(fr, ad, top, bottom, assets):
    c, d = fr.col, fr.d
    if ad.get("eyebrow"):
        f = font("Poppins-SemiBold.ttf", fr.s(26)); d.text((fr.L, top), ad["eyebrow"].upper(), font=f, fill=c["accent"]); top += fr.s(46)
    f, lines, lh = fit(d, ad["headline"], "Poppins-ExtraBold.ttf", fr.cw, fr.s(84), fr.s(44), 3)
    top = draw_lines(d, (fr.L, top), lines, f, lh, c["text"]) + fr.s(30)
    cols = ad["columns"]; avail = bottom - top
    if len(cols) == 2:
        gap = fr.s(22); w = (fr.cw - gap) // 2; pad = fr.s(28)
        n = max(len(x.get("items", [])) for x in cols)
        goods = [colm.get("verdict", "good" if i == len(cols) - 1 else "bad") == "good" for i, colm in enumerate(cols)]
        # titles first, so both columns share one item grid (rows line up across the columns)
        title_fit = [fit(d, colm["title"], "Poppins-ExtraBold.ttf", w - 2 * pad, fr.s(46), fr.s(26), 2) for colm in cols]
        title_h = max(lh * len(ls) for _, ls, lh in title_fit)
        y_items = top + pad + title_h + fr.s(32)
        ph = min(fr.s(240), int(avail * 0.30)) if assets.get("product") is not None else 0
        ib = bottom - pad - (ph + fr.s(14) if ph else 0)
        row_h = min((ib - y_items) / max(n, 1), fr.s(130))
        for i, colm in enumerate(cols):
            good = goods[i]
            x0 = fr.L + i * (w + gap); x1 = x0 + w
            if good:
                d.rounded_rectangle([x0, top, x1, bottom], fr.s(28), fill=c["accent"]); fg = c["on_accent"]
            else:
                d.rounded_rectangle([x0, top, x1, bottom], fr.s(28), outline=c["text"], width=max(2, fr.s(3))); fg = c["text"]
            ft, tl, tlh = title_fit[i]
            draw_lines(d, (x0 + pad, top + pad), tl, ft, tlh, fg)
            ly = top + pad + title_h + fr.s(10)
            d.line([(x0 + pad, ly), (x1 - pad, ly)], fill=fg, width=max(2, fr.s(2)))
            if good and ph:
                paste_fit(fr.im, assets["product"], (x0 + pad, bottom - pad - ph, x1 - pad, bottom - pad), align="bottom")
            y = y_items; ms = fr.s(30)
            for it in colm.get("items", []):
                fi, il, ilh = fit(d, it, "Poppins-SemiBold.ttf", w - 2 * pad - ms - fr.s(14), fr.s(32), fr.s(18), 3, int(row_h - fr.s(8)))
                tick(d, x0 + pad, y + fr.s(4), ms, fg, good)
                draw_lines(d, (x0 + pad + ms + fr.s(14), y), il, fi, ilh, fg)
                y += row_h
    else:
        gap = fr.s(14); rh = (avail - gap * (len(cols) - 1)) / len(cols)
        y = top
        for i, colm in enumerate(cols):
            good = colm.get("verdict", "good" if i == len(cols) - 1 else "bad") == "good"
            y1 = int(y + rh)
            if good:
                d.rounded_rectangle([fr.L, int(y), fr.R, y1], fr.s(24), fill=c["accent"]); fg = c["on_accent"]
            else:
                d.rounded_rectangle([fr.L, int(y), fr.R, y1], fr.s(24), outline=c["text"], width=max(2, fr.s(3))); fg = c["text"]
            pad = fr.s(26); ms = min(fr.s(40), int(rh * 0.45))
            tick(d, fr.L + pad, int(y + (rh - ms) / 2), ms, fg, good)
            tx = fr.L + pad + ms + fr.s(22); tw = fr.R - pad - tx
            label = colm["title"] + (("\n" + colm["items"][0]) if colm.get("items") else "")
            ft, tl, tlh = fit(d, label, "Poppins-Bold.ttf", tw, fr.s(40), fr.s(20), 3, int(rh - fr.s(16)))
            draw_lines(d, (tx, y + (rh - tlh * len(tl)) / 2), tl, ft, tlh, fg)
            y = y1 + gap

def t_problem_solution(fr, ad, top, bottom, assets):
    c, d = fr.col, fr.d
    avail = bottom - top
    fq, ql, qlh = fit(d, ad["problem"], "Poppins-ExtraBold.ttf", fr.cw, fr.s(80), fr.s(40), 4, int(avail * 0.38))
    top = draw_lines(d, (fr.L, top), ql, fq, qlh, c["text"]) + fr.s(24)
    # arrow
    ax = fr.L + fr.s(30); d.line([(ax, top), (ax, top + fr.s(60))], fill=c["accent"], width=fr.s(8))
    d.polygon([(ax - fr.s(22), top + fr.s(48)), (ax + fr.s(22), top + fr.s(48)), (ax, top + fr.s(80))], fill=c["accent"])
    top += fr.s(100)
    pad = fr.s(32)
    d.rounded_rectangle([fr.L, top, fr.R, bottom], fr.s(30), fill=c["accent"])
    fg = c["on_accent"]
    has_prod = assets.get("product") is not None
    pw = int(fr.cw * 0.40) if has_prod else 0
    tw = fr.cw - 2 * pad - pw
    # measure the text block, then centre it vertically in the card
    fs, sl, slh = fit(d, ad["solution"], "Poppins-ExtraBold.ttf", tw, fr.s(58), fr.s(30), 3)
    pts, block_h = [], slh * len(sl) + fr.s(18)
    for p in ad.get("points", [])[:4]:
        fp, pl, plh = fit(d, p, "Poppins-SemiBold.ttf", tw - fr.s(46), fr.s(32), fr.s(20), 2)
        if top + pad + block_h + plh * len(pl) > bottom - pad: break
        pts.append((fp, pl, plh)); block_h += plh * len(pl) + fr.s(10)
    y = top + max(pad, (bottom - top - block_h) // 2)
    y = draw_lines(d, (fr.L + pad, y), sl, fs, slh, fg) + fr.s(18)
    for fp, pl, plh in pts:
        tick(d, fr.L + pad, y + fr.s(4), fr.s(28), fg, True)
        y = draw_lines(d, (fr.L + pad + fr.s(46), y), pl, fp, plh, fg) + fr.s(10)
    if has_prod:
        paste_fit(fr.im, assets["product"], (fr.R - pad - pw, top + pad, fr.R - pad, bottom - pad))

def t_doctor_id(fr, ad, top, bottom, assets, warn):
    c, d = fr.col, fr.d
    avail = bottom - top
    if ad.get("quote"):
        fq, ql, qlh = fit(d, "\u201c" + ad["quote"] + "\u201d", "Poppins-Bold.ttf", fr.cw, fr.s(56), fr.s(30), 4, int(avail * 0.30))
        top = draw_lines(d, (fr.L, top), ql, fq, qlh, c["text"]) + fr.s(28)
    bar_h = fr.s(150)
    ph_box = (fr.L, top, fr.R, bottom - bar_h + fr.s(24))
    w, h = ph_box[2] - ph_box[0], ph_box[3] - ph_box[1]
    photo = ad.get("photo")
    if photo and pathlib.Path(photo).exists():
        if has_alpha(photo):
            d.rounded_rectangle(ph_box, fr.s(30), fill=c["card"])
            paste_fit(fr.im, Image.open(photo).convert("RGBA"), (ph_box[0], ph_box[1] + fr.s(20), ph_box[2], ph_box[3]), align="bottom")
        else:
            fr.im.alpha_composite(rounded_photo(photo, w, h, fr.s(30)), (ph_box[0], ph_box[1]))
    else:
        d.rounded_rectangle(ph_box, fr.s(30), outline=c["text"], width=fr.s(3))
        f = font("Poppins-SemiBold.ttf", fr.s(30))
        d.text((ph_box[0] + fr.s(30), ph_box[1] + fr.s(30)), "DOCTOR PHOTO MISSING", font=f, fill=c["text"])
        warn.append(f"{ad['name']}: no doctor photo found at '{photo}'. Placeholder rendered; do not deliver.")
    # lower third: name + title (+ org)
    y0 = bottom - bar_h; pad = fr.s(28)
    d.rounded_rectangle([fr.L + fr.s(24), y0, fr.R - fr.s(24), bottom], fr.s(22), fill=c["accent"])
    fn, nl, nlh = fit(d, ad["doctor"], "Poppins-ExtraBold.ttf", fr.cw - 2 * pad - fr.s(48), fr.s(48), fr.s(28), 1)
    draw_lines(d, (fr.L + fr.s(24) + pad, y0 + fr.s(20)), nl, fn, nlh, c["on_accent"])
    sub = ad.get("title", "") + ((" \u00b7 " + ad["org"]) if ad.get("org") else "")
    if sub:
        fs, sl, slh = fit(d, sub, "Poppins-Medium.ttf", fr.cw - 2 * pad - fr.s(48), fr.s(28), fr.s(18), 2)
        draw_lines(d, (fr.L + fr.s(24) + pad, y0 + fr.s(20) + nlh), sl, fs, slh, c["on_accent"])

# ---------- gate ----------
def ad_texts(ad):
    out = []
    for k in ("eyebrow", "headline", "problem", "solution", "quote", "title", "org", "cta", "legal"):
        if ad.get(k): out.append(str(ad[k]).replace("\n", " "))
    for p in ad.get("points", []): out.append(p)
    for colm in ad.get("columns", []):
        out.append(colm["title"]); out += colm.get("items", [])
    return out

def engine_gate(spec, b, slug):
    """Rules the keyword screen cannot see. Returns (blocks, reviews)."""
    blocks, reviews = [], []
    mode = spec.get("mode")
    if slug == "ssclinic" and mode not in ("educational", "kol_ad"):
        blocks.append("SS Clinic: set \"mode\": \"educational\" or \"kol_ad\" in the spec (ask the Head of Creative if unsure).")
    for ad in spec["ads"]:
        n, t = ad.get("name", "?"), ad.get("template")
        if t not in TEMPLATES:
            blocks.append(f"{n}: unknown template '{t}' (have: {', '.join(TEMPLATES)})")
        if ad.get("price") is not None:
            blocks.append(f"{n}: prices are never typed; use \"price_ref\" with a product name from brands/{slug}/prices.json")
        if slug == "ssclinic":
            if t == "vs-stack":
                blocks.append(f"{n}: SS Clinic may not run comparison ads (MAB services guideline; competitor comparisons).")
            if ad.get("price_ref") or ad.get("offer"):
                blocks.append(f"{n}: SS Clinic statics never show prices or offers (MAB 7.0).")
            if mode == "educational" and ad.get("cta"):
                blocks.append(f"{n}: SS Clinic Educational mode has no clinic CTA. Remove 'cta' or use a neutral close in 'legal'.")
            if mode == "kol_ad":
                if t == "doctor-id":
                    blocks.append(f"{n}: SS Clinic KOL ads never show a real doctor.")
                if not ad.get("kkliu"):
                    blocks.append(f"{n}: SS Clinic KOL ad needs a KKLIU approval number ('kkliu') per posting.")
        if t == "doctor-id":
            if slug == "rejal":
                blocks.append(f"{n}: REJAL has no doctor endorsement (food, never medicine).")
            if b.get("type") == "product":
                reviews.append(f"{n}: doctor in a product ad: MMC Guideline V2/2025 5.14 discourages doctors endorsing health products. List on the human review note.")
            reviews.append(f"{n}: confirm the photo is the real, appointed doctor (never AI, never an actor) and consent is on file.")
        if ad.get("product_image"):
            reviews.append(f"{n}: read the text PRINTED on the product image against brand.json banned_terms/avoid "
                           "(the keyword screen cannot see pack art; e.g. a pack line like 'andrologically tested' is screened for DMR).")
        if ad.get("inspired_by_risk"):
            reviews.append(f"{n}: reference swipe has policy risk '{ad['inspired_by_risk']}'. Take the format, not the risky element.")
    return blocks, reviews

def run_check_brand(slug, texts, doctors, work):
    work.mkdir(parents=True, exist_ok=True)
    tf = work / "static_texts.txt"
    tf.write_text("\n".join(texts), encoding="utf-8")
    cmd = [sys.executable, str(ROOT / "scripts" / "check_brand.py"), "--brand", slug, "--texts", str(tf)]
    rc, outs = 0, []
    for doc in (doctors or [None]):
        c = cmd + (["--doctor", doc] if doc else [])
        r = subprocess.run(c, capture_output=True, text=True, encoding="utf-8")
        outs.append(r.stdout.strip()); rc = max(rc, r.returncode)
    return rc, "\n".join(outs)

# ---------- main ----------
def resolve_price(slug, ref):
    pj = prices(slug)
    if not pj:
        sys.exit(f"BLOCK price_ref '{ref}' but brands/{slug}/prices.json does not exist")
    for p in pj["products"]:
        if p["name"].lower() == ref.lower():
            out = {"now": f"RM{p['price_rm']:.2f}"}
            if p.get("regular_price_rm"):
                out["was"] = f"RM{p['regular_price_rm']:.2f}"
            return out
    sys.exit(f"BLOCK price_ref '{ref}' not in brands/{slug}/prices.json ({', '.join(p['name'] for p in pj['products'])})")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec"); ap.add_argument("--only"); ap.add_argument("--sizes")
    ap.add_argument("--skip-gate", action="store_true", help="layout tests only; output is marked NOT FOR DELIVERY")
    a = ap.parse_args()
    sp = pathlib.Path(a.spec); spec = json.loads(sp.read_text(encoding="utf-8"))
    slug = spec["brand"]; b, pal, col = load_brand(slug)
    KEEP_TOGETHER[:] = sorted({x for x in (b.get("name"), (b.get("naming") or {}).get("display")) if x and " " in x}, key=len, reverse=True)
    batch_dir = sp.parent
    ads = [x for x in spec["ads"] if not a.only or x.get("name") == a.only]
    spec_f = dict(spec, ads=ads)
    warn = []

    blocks, reviews = engine_gate(spec_f, b, slug)
    texts = [t for ad in ads for t in ad_texts(ad)]
    doctors = sorted({ad["doctor"] for ad in ads if ad.get("template") == "doctor-id" and ad.get("doctor")})
    rc, report = run_check_brand(slug, texts, doctors, batch_dir / "work")
    print(report)
    for r in reviews: print("REVIEW:", r)
    for x in blocks: print("BLOCK:", x)
    if (blocks or rc) and not a.skip_gate:
        sys.exit("\nGate failed: fix the BLOCK items above (never reword a claim to get around a block). Nothing rendered.")
    if a.skip_gate:
        warn.append("Rendered with --skip-gate: NOT FOR DELIVERY.")

    logo = logo_image(slug, pal, warn)
    sizes = (a.sizes or ",".join(spec.get("sizes", ["feed", "story"]))).split(",")
    out_dir = batch_dir / "renders" / "static"; out_dir.mkdir(parents=True, exist_ok=True)
    rows, files = [], []
    for ad in ads:
        assets = {}
        if ad.get("product_image"):
            pi = (batch_dir / ad["product_image"]) if not pathlib.Path(ad["product_image"]).is_absolute() else pathlib.Path(ad["product_image"])
            if pi.exists(): assets["product"] = Image.open(pi).convert("RGBA")
            else: warn.append(f"{ad['name']}: product_image not found: {pi}")
        if ad.get("photo") and not pathlib.Path(ad["photo"]).is_absolute():
            ad = dict(ad, photo=str(batch_dir / ad["photo"]))
        price = resolve_price(slug, ad["price_ref"]) if ad.get("price_ref") else None
        legal = ad.get("legal", "")
        if ad.get("kkliu"): legal = (legal + "  " if legal else "") + f"KKLIU {ad['kkliu']}"
        for size in sizes:
            fr = Frame(size, col, ad.get("market") or spec.get("market"))
            top = fr.logo(logo)
            bottom = fr.footer(price, ad.get("cta"), pal.get("signoff", "") if ad.get("signoff", True) else "", legal)
            t = ad["template"]
            if t == "vs-stack": t_vs_stack(fr, ad, top, bottom, assets)
            elif t == "problem-solution": t_problem_solution(fr, ad, top, bottom, assets)
            elif t == "doctor-id": t_doctor_id(fr, ad, top, bottom, assets, warn)
            if a.skip_gate:
                f = font("Poppins-Bold.ttf", 28); fr.d.text((20, 12), "TEST - NOT FOR DELIVERY", font=f, fill=(255, 0, 0))
            out = out_dir / f"{ad['name']}_{size}.png"
            fr.im.convert("RGB").save(out, optimize=True)
            files.append(out)
            rows.append({"File": out.name, "Template": t, "Size": f"{fr.W}x{fr.H}", "Headline": ad.get("headline") or ad.get("problem") or ad.get("quote", ""),
                         "Market": fr.market or "", "Inspired by": " ".join(f"#{i}" for i in ad.get("inspired_by", spec.get("inspired_by", []))),
                         "Brand": slug, "Mode": spec.get("mode", ""), "KKLIU": ad.get("kkliu", ""), "Price ref": ad.get("price_ref", "")})
    with open(out_dir / "static_index.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    # review sheet
    th = 560; tiles = []
    for f in files:
        im = Image.open(f); im.thumbnail((int(th * im.width / im.height), th)); tiles.append(im)
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + 20 * (len(tiles) + 1), th + 40), "white")
    x = 20
    for t in tiles:
        sheet.paste(t, (x, 20)); x += t.width + 20
    sheet.save(out_dir / "review_sheet.jpg", quality=85)
    for w_ in dict.fromkeys(warn): print("WARN:", w_)
    notes = ["# Review notes (render_static.py)", "", "## check_brand.py", report, "", "## Engine review items"]
    notes += [f"- {r}" for r in dict.fromkeys(reviews)] or ["- none"]
    notes += ["", "## Warnings"] + ([f"- {w_}" for w_ in dict.fromkeys(warn)] or ["- none"])
    (out_dir / "review_notes.md").write_text("\n".join(notes), encoding="utf-8")
    print(f"\n{len(files)} file(s) in {out_dir}  (static_index.csv, review_sheet.jpg)")

if __name__ == "__main__":
    main()
