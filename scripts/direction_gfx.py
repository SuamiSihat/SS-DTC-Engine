"""Graphics for render_direction.py: step panels, icons, captions, logo pill, ring, 9:16 background, end card.
All sizes are in output pixels. Brand palette from brands/ssclinic/brand.json (navy 60, white/clinical navy 30, gold 10)."""
import os, pathlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_DIRS = [pathlib.Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")), pathlib.Path(r"C:\Windows\Fonts"),
             ROOT / "assets" / "fonts"]
NAVY = (2, 32, 87); CNAVY = (15, 76, 117); GOLD = (244, 162, 97); WHITE = (255, 255, 255); SOFT = (214, 228, 243)
LOGO_DARK = ROOT / "brands" / "ssclinic" / "design-system" / "logos" / "logo_ssc_primary_dark.png"

# layout per format: safe area, panel box, video box, caption band
LAYOUT = {
    "16x9": {"size": (1920, 1080), "safe": (60, 60, 1860, 1020), "panel": (60, 60), "video": (0, 0, 1920, 1080),
             "cap": (140, 1012), "cap_w": 1640, "cap_font": 44},
    "9x16": {"size": (1080, 1920), "safe": (120, 270, 960, 1248), "panel": (120, 280), "panel_wh": (840, 240),
             "video": (0, 530, 1080, 608), "cap": (120, 1248), "cap_w": 840, "cap_font": 44},
}


def font(name, size):
    for d in FONT_DIRS:
        p = d / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise SystemExit(f"font {name} not found (install Poppins)")


def wrap(text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(text, name, size, width, max_lines=1, min_size=24):
    while size > min_size:
        f = font(name, size)
        lines = wrap(text, f, width)
        if len(lines) <= max_lines and all(f.getlength(l) <= width for l in lines):
            return f, lines
        size -= 2
    f = font(name, min_size)
    return f, wrap(text, f, width)


def icon(d, kind, box, col=GOLD):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0; cx, cy = x0 + w / 2, y0 + h / 2; lw = max(6, int(w * 0.11))
    if kind == "straight":
        d.line((cx, y1 - h * .1, cx, y0 + h * .38), fill=col, width=lw)
        d.polygon([(cx, y0 + h * .08), (cx - w * .26, y0 + h * .42), (cx + w * .26, y0 + h * .42)], fill=col)
    elif kind in ("left", "right"):
        s = -1 if kind == "left" else 1; sx = cx - s * w * .18
        d.line((sx, y1 - h * .1, sx, cy - h * .05), fill=col, width=lw)
        d.line((sx - s * lw / 2 + s * 0, cy - h * .05, cx + s * w * .12, cy - h * .05), fill=col, width=lw)
        tx = cx + s * w * .40
        d.polygon([(tx, cy - h * .05), (cx + s * w * .08, cy - h * .32), (cx + s * w * .08, cy + h * .22)], fill=col)
    elif kind == "roundabout":
        r = w * .30
        d.arc((cx - r, cy - r, cx + r, cy + r), 120, 400, fill=col, width=lw)
        d.polygon([(cx - r * .5 - w * .16, cy + r * .87), (cx - r * .5 + w * .10, cy + r * .87 - h * .16), (cx - r * .5 + w * .08, cy + r * .87 + h * .14)], fill=col)
        d.line((cx, y1 - h * .04, cx, cy + r), fill=col, width=lw)
    elif kind == "ev":
        d.polygon([(cx + w * .08, y0 + h * .08), (cx - w * .26, cy + h * .06), (cx - w * .02, cy + h * .06), (cx - w * .10, y1 - h * .08),
                   (cx + w * .26, cy - h * .08), (cx + w * .02, cy - h * .08)], fill=col)
    elif kind == "parking":
        d.rounded_rectangle((x0 + w * .14, y0 + h * .14, x1 - w * .14, y1 - h * .14), radius=int(w * .12), outline=col, width=lw)
        f = font("Poppins-Bold.ttf", int(h * .5)); d.text((cx, cy + h * .02), "P", font=f, fill=col, anchor="mm")
    elif kind == "lift":
        d.polygon([(cx, y0 + h * .10), (cx - w * .26, y0 + h * .42), (cx + w * .26, y0 + h * .42)], fill=col)
        d.polygon([(cx, y1 - h * .10), (cx - w * .26, y1 - h * .42), (cx + w * .26, y1 - h * .42)], fill=col)
    elif kind == "check":
        r = w * .38; d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=lw)
        d.line((cx - r * .45, cy + r * .02, cx - r * .1, cy + r * .38, cx + r * .5, cy - r * .35), fill=col, width=lw, joint="curve")
    elif kind == "phone":
        d.rounded_rectangle((cx - w * .22, y0 + h * .06, cx + w * .22, y1 - h * .06), radius=int(w * .1), outline=col, width=lw)
        d.line((cx - w * .07, y1 - h * .2, cx + w * .07, y1 - h * .2), fill=col, width=lw)
    else:  # pin
        r = w * .24; py = y0 + h * .36
        d.ellipse((cx - r, py - r, cx + r, py + r), fill=col)
        d.polygon([(cx - r * .86, py + r * .5), (cx + r * .86, py + r * .5), (cx, y1 - h * .08)], fill=col)
        d.ellipse((cx - r * .4, py - r * .4, cx + r * .4, py + r * .4), fill=CNAVY)


def panel(fmt, shot, out):
    """Step panel: icon tile + 'LANGKAH n' + head + sub on a solid navy panel."""
    L = LAYOUT[fmt]
    big = fmt == "9x16"
    tile = 176 if big else 150; pad = 32 if big else 26
    if big:
        W, H = L["panel_wh"]
    else:
        W, H = 1180, tile + 2 * pad
    tw = W - tile - 3 * pad
    step = None
    if shot.get("step"):
        step = f"LANGKAH {shot['step']}" + (f" / {shot['nsteps']}" if shot.get("nsteps") else "")
    fs = font("Poppins-SemiBold.ttf", 30 if big else 28)
    hs, ss = (62, 36) if big else (58, 36)
    while True:  # shrink until the text block fits the panel (9:16 panel height is fixed)
        fh, hl = fit(shot["head"], "Poppins-Bold.ttf", hs, tw, max_lines=1, min_size=44 if big else 40)
        if len(hl) > 1:
            fh, hl = fit(shot["head"], "Poppins-Bold.ttf", hs, tw, max_lines=2, min_size=34)
        fsub, sl = fit(shot.get("sub", ""), "Poppins-Medium.ttf", ss, tw, max_lines=2 if big else 1, min_size=24)
        lh_h, lh_s = int(fh.size * 1.12), int(fsub.size * 1.25)
        block = (fs.size + 10 if step else 0) + lh_h * len(hl) + (6 + lh_s * len(sl) if sl and sl[0] else 0)
        if not big or block <= H - 2 * pad or hs <= 34:
            break
        hs, ss = hs - 2, max(24, ss - 1)
    if not big:
        H = max(H, block + 2 * pad)
        W = min(W, int(tile + 3 * pad + max([fh.getlength(l) for l in hl] + [fsub.getlength(l) for l in sl] + [fs.getlength(step or "")])) + 8)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=30, fill=NAVY + (240,))
    ty = (H - tile) // 2
    d.rounded_rectangle((pad, ty, pad + tile, ty + tile), radius=24, fill=CNAVY + (255,))
    icon(d, shot.get("icon", "pin"), (pad + 14, ty + 14, pad + tile - 14, ty + tile - 14))
    x = pad * 2 + tile; y = (H - block) // 2
    if step:
        d.text((x, y), step, font=fs, fill=GOLD); y += fs.size + 10
    for l in hl:
        d.text((x, y), l, font=fh, fill=WHITE); y += lh_h
    if sl and sl[0]:
        y += 6
        for l in sl:
            d.text((x, y), l, font=fsub, fill=SOFT); y += lh_s
    im.save(out)
    return W, H


def caption(fmt, text, out):
    """Burned-in subtitle chunk on a solid navy box; returns (x, y, w, h) in output pixels."""
    L = LAYOUT[fmt]; f = font("Poppins-SemiBold.ttf", L["cap_font"]); maxw = L["cap_w"] - 48
    lines = wrap(text, f, maxw)[:2]
    lh = int(f.size * 1.25); w = int(max(f.getlength(l) for l in lines)) + 48; h = lh * len(lines) + 22
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=16, fill=NAVY + (225,))
    for i, l in enumerate(lines):
        d.text((w / 2, 11 + i * lh + lh / 2), l, font=f, fill=WHITE, anchor="mm")
    im.save(out)
    cx0, bottom = L["cap"]
    return (cx0 + (L["cap_w"] - w) // 2, bottom - h, w, h)


def logo_pill(out, height=60):
    lg = Image.open(LOGO_DARK).convert("RGBA"); lg = lg.resize((int(lg.width * height / lg.height), height), Image.LANCZOS)
    pw, ph = lg.width + 48, height + 36
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), radius=ph // 2, fill=NAVY + (235,))
    im.alpha_composite(lg, (24, 18)); im.save(out)
    return pw, ph


def ring(out, r, lw=9):
    s = 2 * r + 4 * lw; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((2 * lw, 2 * lw, s - 2 * lw, s - 2 * lw), outline=GOLD + (255,), width=lw)
    im.save(out)
    return s


def bg_9x16(footer, out, card=None):
    """Static navy canvas for 9:16. Logo (top) and footer (bottom) sit outside the Reels safe area: decorative only,
    every instruction is inside the safe area."""
    W, H = LAYOUT["9x16"]["size"]; im = Image.new("RGBA", (W, H), NAVY + (255,)); d = ImageDraw.Draw(im)
    for y in range(H):  # gentle navy -> clinical navy gradient
        t = y / H; d.line((0, y, W, y), fill=tuple(int(NAVY[i] + (CNAVY[i] - NAVY[i]) * t * .55) for i in range(3)) + (255,))
    lg = Image.open(LOGO_DARK).convert("RGBA"); lg = lg.resize((int(lg.width * 84 / lg.height), 84), Image.LANCZOS)
    im.alpha_composite(lg, ((W - lg.width) // 2, 150))
    if card:  # location card in the lower area (useful on WhatsApp; redundant with the end card if Reels UI covers it)
        x0, y0, x1 = 120, 1330, 960
        fh = font("Poppins-Bold.ttf", 46); fl = font("Poppins-Medium.ttf", 34)
        lines = [(card[0], fh, WHITE)] + [(l, fl, SOFT) for l in card[1:]]
        h = 60 + sum(int(f.size * 1.4) for _, f, _ in lines)
        d.rounded_rectangle((x0, y0, x1, y0 + h), radius=30, fill=CNAVY + (255,))
        icon(d, "pin", (x0 + 30, y0 + 34, x0 + 120, y0 + 124))
        y = y0 + 30
        for t, f, c in lines:
            l = wrap(t, f, x1 - x0 - 190)[0]
            d.text((x0 + 150, y), l, font=f, fill=c); y += int(f.size * 1.4)
    else:
        d.text((W / 2, 1330), footer, font=font("Poppins-Medium.ttf", 34), fill=SOFT, anchor="mm")
    im.convert("RGB").save(out)


def endcard(fmt, ec, still, out):
    W, H = LAYOUT[fmt]["size"]; sx0, sy0, sx1, sy1 = LAYOUT[fmt]["safe"]
    bg = Image.open(still).convert("RGB")
    s = max(W / bg.width, H / bg.height); bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H)).filter(ImageFilter.GaussianBlur(22))
    im = bg.convert("RGBA"); im.alpha_composite(Image.new("RGBA", (W, H), NAVY + (222,)))
    d = ImageDraw.Draw(im); big = fmt == "9x16"
    cw = (sx1 - sx0) if big else 860; x = sx0 if big else 110
    lgh = 96 if big else 104
    lg = Image.open(LOGO_DARK).convert("RGBA"); lg = lg.resize((int(lg.width * lgh / lg.height), lgh), Image.LANCZOS)
    y = (sy0 + 20) if big else 190
    im.alpha_composite(lg, ((W - lg.width) // 2 if big else x, y)); y += lgh + (50 if big else 46)
    # clinic-door still: right half on 16:9, below the safe area on 9:16 (decorative)
    ph = Image.open(still).convert("RGB")
    pw_, ph_ = (860, 484) if not big else (840, 472)
    ph = ph.resize((pw_, ph_), Image.LANCZOS)
    mask = Image.new("L", (pw_, ph_), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw_ - 1, ph_ - 1), radius=28, fill=255)
    pxy = (W - 60 - pw_, (H - ph_) // 2) if not big else (120, 1300)
    im.paste(ph, pxy, mask)
    rows = [(ec["name"], "Poppins-Bold.ttf", 64 if big else 70, WHITE, 2), (ec["where"], "Poppins-SemiBold.ttf", 38 if big else 38, GOLD, 2),
            (ec["address"], "Poppins-Medium.ttf", 36 if big else 36, WHITE, 4), (ec["parking"], "Poppins-Regular.ttf", 32, SOFT, 3)]
    if ec.get("hours"):
        rows.append((ec["hours"], "Poppins-Regular.ttf", 30, SOFT, 2))
    for text, fn, size, col, ml in rows:
        f, lines = fit(text, fn, size, cw, max_lines=ml, min_size=24)
        for l in lines:
            d.text(((W - f.getlength(l)) / 2 if big else x, y), l, font=f, fill=col); y += int(f.size * 1.3)
        y += 22
    # phone block on a clinical navy panel
    fl = font("Poppins-Medium.ttf", 30 if big else 32); fp = font("Poppins-Bold.ttf", 64 if big else 70)
    bw = int(max(fl.getlength(ec["phone_label"]), fp.getlength(ec["phone"]) + 110)) + 70; bh = 190
    bx = (W - bw) // 2 if big else x; by = max(y + 10, sy1 - bh - 10) if big else y + 16
    by = min(by, sy1 - bh)
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=28, fill=CNAVY + (255,))
    d.text((bx + 35, by + 26), ec["phone_label"], font=fl, fill=SOFT)
    icon(d, "phone", (bx + 30, by + 84, bx + 110, by + 164), GOLD)
    d.text((bx + 125, by + 78), ec["phone"], font=fp, fill=WHITE)
    im.convert("RGB").save(out)
