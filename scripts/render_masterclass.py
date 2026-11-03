#!/usr/bin/env python3
"""Render Masterclass Series (EP00 Trailer + EP01..EP05) in both 16:9 and 9:16 formats.

Usage:
  python scripts/render_masterclass.py batches/masterclass-hairul/work/spec_masterclass.json [--only EP00] [--format both|16x9|9x16]

Outputs:
  batches/<batch>/renders/16x9/<slug>_16x9.mp4 (+ .timeline.json, .srt, .vtt)
  batches/<batch>/renders/9x16/<slug>_9x16.mp4 (+ .timeline.json, .srt)
"""
import argparse, json, os, pathlib, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAVY, CNAVY, GOLD, AZURE, WHITE = (2, 32, 87), (15, 76, 117), (244, 162, 97), (33, 161, 247), (255, 255, 255)
SLATE = (210, 225, 242)
FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/poppins",
]

# 9:16 constants (1080x1920)
W9, H9 = 1080, 1920
SAFE9_L, SAFE9_T, SAFE9_R, SAFE9_B = 120, 270, 960, 1248
SAFE9_W = SAFE9_R - SAFE9_L  # 840
CAP9_BOTTOM = SAFE9_B
CAP9_SIZE = 68

# 16:9 constants (1920x1080)
W16, H16 = 1920, 1080
SAFE16_L, SAFE16_T, SAFE16_R, SAFE16_B = 60, 60, 1860, 1020
SPK16_X, SPK16_Y, SPK16_W, SPK16_H, SPK16_R = 80, 76, 780, 828, 32
BRD16_X, BRD16_Y, BRD16_W, BRD16_H = 900, 76, 940, 828
CAP16_BOTTOM = 1012
CAP16_SIZE = 42


def font(name, size):
    for d in FONT_DIRS:
        p = pathlib.Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise SystemExit(f"Font not found: {name}")


def rgb_to_ass(c, alpha=0):
    return "&H%02X%02X%02X%02X" % (alpha, c[2], c[1], c[0])


def make_gradient(w, h, c0=NAVY, c1=CNAVY):
    img = Image.new("RGB", (w, h), c0)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def wrap_plain(draw, text, fnt, maxw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        cand = " ".join(cur + [w])
        if cur and draw.textlength(cand, font=fnt) > maxw:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def wrap_tokens(draw, words, fnt, maxw):
    lines, cur = [], []
    for w in words:
        t = " ".join(x[0] for x in cur + [w])
        if cur and draw.textlength(t, font=fnt) > maxw:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


# ---------- 9:16 Overlays (strictly inside 840px width & <=146px height) ----------
def make_9x16_headline(path, text, max_h=144):
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    toks = []
    for part in re.split(r"(\*[^*]+\*)", text):
        if not part:
            continue
        key = part.startswith("*")
        for w in part.strip("*").split():
            toks.append((w, key))
    maxw = SAFE9_W - 76
    for sz in (46, 42, 38, 34):
        fnt = font("Poppins-Bold.ttf", sz)
        lines = wrap_tokens(d0, toks, fnt, maxw)
        if len(lines) <= 2:
            break
    lh = int(sz * 1.24)
    pad = 18
    h = min(max_h, lh * len(lines) + pad * 2)
    img = Image.new("RGBA", (SAFE9_W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, SAFE9_W - 1, h - 1], radius=28, fill=NAVY + (238,))
    d.rectangle([0, 20, 10, h - 20], fill=GOLD + (255,))
    y = (h - lh * len(lines)) // 2
    for line in lines:
        wtot = sum(d.textlength(w + " ", font=fnt) for w, _ in line) - d.textlength(" ", font=fnt)
        x = (SAFE9_W - wtot) / 2
        for w, key in line:
            d.text((x, y), w, font=fnt, fill=(GOLD if key else WHITE) + (255,))
            x += d.textlength(w + " ", font=fnt)
        y += lh
    img.save(path)
    return img.size


def make_9x16_lower_third(path, name, title):
    fn, ft = font("Poppins-Bold.ttf", 44), font("Poppins-Medium.ttf", 28)
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w = min(SAFE9_W, int(max(d0.textlength(name, font=fn), d0.textlength(title, font=ft)) + 84))
    h = 128
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=24, fill=NAVY + (238,))
    d.rectangle([0, 18, 10, h - 18], fill=GOLD + (255,))
    d.text((36, 14), name, font=fn, fill=WHITE + (255,))
    d.text((36, 74), title, font=ft, fill=SLATE + (255,))
    img.save(path)
    return img.size


def make_9x16_callout(path, title, sub):
    ft, fs = font("Poppins-Bold.ttf", 34), font("Poppins-Medium.ttf", 26)
    h = 136
    img = Image.new("RGBA", (SAFE9_W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, SAFE9_W - 1, h - 1], radius=26, fill=NAVY + (240,))
    d.rectangle([0, 18, 12, h - 18], fill=GOLD + (255,))
    d.text((34, 16), title, font=ft, fill=GOLD + (255,))
    lines = wrap_plain(d, sub, fs, SAFE9_W - 60)
    y = 64
    for ln in lines[:2]:
        d.text((34, y), ln, font=fs, fill=WHITE + (255,))
        y += 32
    img.save(path)
    return img.size


# ---------- Full-Screen Cards (16:9 and 9:16) ----------
def make_series_card(path, size, logo_png, kicker, title, subtitle):
    w, h = size
    img = make_gradient(w, h)
    d = ImageDraw.Draw(img)
    logo = Image.open(logo_png).convert("RGBA")
    lw = 360 if w > h else 520
    lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    ly = 130 if w > h else 360
    img.paste(logo, ((w - lw) // 2, ly), logo)

    fk = font("Poppins-Bold.ttf", 34 if w > h else 36)
    ft = font("Poppins-Bold.ttf", 64 if w > h else 56)
    fs = font("Poppins-Medium.ttf", 34 if w > h else 32)

    ky = ly + lh + (55 if w > h else 75)
    kw = int(d.textlength(kicker, font=fk) + 64)
    d.rounded_rectangle([(w - kw) // 2, ky, (w + kw) // 2, ky + 62], radius=31, fill=GOLD)
    d.text(((w - d.textlength(kicker, font=fk)) / 2, ky + 8), kicker, font=fk, fill=NAVY)

    ty = ky + 100
    tlines = wrap_plain(d, title, ft, w - 220)
    for ln in tlines:
        d.text(((w - d.textlength(ln, font=ft)) / 2, ty), ln, font=ft, fill=WHITE)
        ty += int(ft.size * 1.22)

    ty += 24
    slines = wrap_plain(d, subtitle, fs, w - 220)
    for ln in slines:
        d.text(((w - d.textlength(ln, font=fs)) / 2, ty), ln, font=fs, fill=SLATE)
        ty += int(fs.size * 1.3)

    img.save(path)


def make_chapter_card(path, size, ep_badge, chap_num, chap_title, points):
    w, h = size
    img = make_gradient(w, h)
    d = ImageDraw.Draw(img)
    pad_x = 180 if w > h else 110
    top_y = 150 if w > h else 420

    fb = font("Poppins-Bold.ttf", 30)
    ft = font("Poppins-Bold.ttf", 58 if w > h else 50)
    fp = font("Poppins-Medium.ttf", 32 if w > h else 30)

    badge_txt = f"{ep_badge}  •  {chap_num}"
    bw = int(d.textlength(badge_txt, font=fb) + 56)
    d.rounded_rectangle([pad_x, top_y, pad_x + bw, top_y + 58], radius=29, fill=GOLD)
    d.text((pad_x + 28, top_y + 9), badge_txt, font=fb, fill=NAVY)

    y = top_y + 92
    for ln in wrap_plain(d, chap_title, ft, w - pad_x * 2):
        d.text((pad_x, y), ln, font=ft, fill=WHITE)
        y += int(ft.size * 1.22)

    y += 30
    d.rectangle([pad_x, y, pad_x + 160, y + 6], fill=GOLD)
    y += 36
    for i, pt in enumerate(points, 1):
        d.rounded_rectangle([pad_x, y, w - pad_x, y + 78], radius=20, fill=(8, 48, 108))
        d.rounded_rectangle([pad_x + 16, y + 14, pad_x + 76, y + 64], radius=14, fill=GOLD)
        num_s = f"0{i}"
        d.text((pad_x + 46 - d.textlength(num_s, font=fb) / 2, y + 18), num_s, font=fb, fill=NAVY)
        d.text((pad_x + 98, y + 19), pt, font=fp, fill=WHITE)
        y += 96

    img.save(path)


def make_summary_card(path, size, kicker, title, items):
    w, h = size
    img = make_gradient(w, h)
    d = ImageDraw.Draw(img)
    pad_x = 160 if w > h else 100
    top_y = 110 if w > h else 330

    fk = font("Poppins-Bold.ttf", 28)
    ft = font("Poppins-Bold.ttf", 52 if w > h else 46)
    fn = font("Poppins-Bold.ttf", 32)
    fp = font("Poppins-Medium.ttf", 31 if w > h else 28)

    kw = int(d.textlength(kicker, font=fk) + 52)
    d.rounded_rectangle([pad_x, top_y, pad_x + kw, top_y + 52], radius=26, fill=GOLD)
    d.text((pad_x + 26, top_y + 8), kicker, font=fk, fill=NAVY)

    y = top_y + 74
    d.text((pad_x, y), title, font=ft, fill=WHITE)
    y += int(ft.size * 1.35)

    box_h = 92 if len(items) <= 3 else 78
    gap = 20 if len(items) <= 3 else 14
    for i, item in enumerate(items, 1):
        d.rounded_rectangle([pad_x, y, w - pad_x, y + box_h], radius=22, fill=(8, 48, 108))
        d.rectangle([pad_x, y + 16, pad_x + 10, y + box_h - 16], fill=GOLD)
        num_s = f"0{i}"
        d.rounded_rectangle([pad_x + 26, y + (box_h - 50) // 2, pad_x + 88, y + (box_h + 50) // 2], radius=14, fill=GOLD)
        d.text((pad_x + 57 - d.textlength(num_s, font=fn) / 2, y + (box_h - 50) // 2 + 4), num_s, font=fn, fill=NAVY)
        lines = wrap_plain(d, item, fp, (w - pad_x * 2) - 130)
        ty = y + (box_h - len(lines) * 36) // 2
        for ln in lines[:2]:
            d.text((pad_x + 110, ty), ln, font=fp, fill=WHITE)
            ty += 36
        y += box_h + gap

    img.save(path)


def make_end_card(path, size, logo_png, line, cta):
    w, h = size
    img = make_gradient(w, h)
    d = ImageDraw.Draw(img)
    logo = Image.open(logo_png).convert("RGBA")
    lw = 540 if w > h else 720
    lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    ly = 220 if w > h else 620
    img.paste(logo, ((w - lw) // 2, ly), logo)

    f1 = font("Poppins-Bold.ttf", 68 if w > h else 64)
    f2 = font("Poppins-Medium.ttf", 38 if w > h else 36)
    y1 = ly + lh + (70 if w > h else 90)
    for ln in wrap_plain(d, line, f1, w - 160):
        d.text(((w - d.textlength(ln, font=f1)) / 2, y1), ln, font=f1, fill=GOLD)
        y1 += int(f1.size * 1.2)
    y2 = y1 + 24
    for ln in wrap_plain(d, cta, f2, w - 160):
        d.text(((w - d.textlength(ln, font=f2)) / 2, y2), ln, font=f2, fill=WHITE)
        y2 += int(f2.size * 1.25)
    img.save(path)


# ---------- 16:9 Split-Screen Right-Side Slide Board (940x828 at x=900, y=76) ----------
def make_16x9_board(path, ep_badge, ep_title, chap_num, slide_title, points, speaker):
    img = Image.new("RGBA", (BRD16_W, BRD16_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, BRD16_W - 1, BRD16_H - 1], radius=32, fill=(5, 38, 96, 242))
    d.rounded_rectangle([2, 2, BRD16_W - 3, BRD16_H - 3], radius=31, outline=GOLD + (90,), width=2)

    fb = font("Poppins-Bold.ttf", 24)
    fe = font("Poppins-Medium.ttf", 24)
    ft = font("Poppins-Bold.ttf", 38)
    fn = font("Poppins-Bold.ttf", 28)
    fp = font("Poppins-Medium.ttf", 27)
    fs_n = font("Poppins-Bold.ttf", 28)
    fs_t = font("Poppins-Medium.ttf", 22)

    # Top pill
    pill = f"{ep_badge}  •  {chap_num}"
    pw = int(d.textlength(pill, font=fb) + 44)
    d.rounded_rectangle([40, 36, 40 + pw, 82], radius=23, fill=GOLD + (255,))
    d.text((62, 42), pill, font=fb, fill=NAVY + (255,))

    # Episode title sub-kicker
    d.text((40, 98), ep_title, font=fe, fill=SLATE + (255,))

    # Slide callout title
    y = 142
    for ln in wrap_plain(d, slide_title, ft, BRD16_W - 80)[:2]:
        d.text((40, y), ln, font=ft, fill=WHITE + (255,))
        y += 48
    y += 10
    d.rectangle([40, y, 180, y + 5], fill=GOLD + (255,))
    y += 28

    # 3 numbered bullet cards
    for i, pt in enumerate(points[:3], 1):
        bh = 128
        d.rounded_rectangle([40, y, BRD16_W - 40, y + bh], radius=22, fill=(10, 56, 128, 255))
        d.rectangle([40, y + 20, 48, y + bh - 20], fill=GOLD + (255,))
        num_s = f"0{i}"
        d.rounded_rectangle([66, y + 36, 124, y + 92], radius=14, fill=GOLD + (255,))
        d.text((95 - d.textlength(num_s, font=fn) / 2, y + 43), num_s, font=fn, fill=NAVY + (255,))
        plines = wrap_plain(d, pt, fp, BRD16_W - 200)
        py = y + (bh - len(plines) * 34) // 2
        for ln in plines[:2]:
            d.text((144, py), ln, font=fp, fill=WHITE + (255,))
            py += 34
        y += bh + 20

    # Footer speaker bar inside board
    fy = BRD16_H - 108
    d.rounded_rectangle([40, fy, BRD16_W - 40, BRD16_H - 28], radius=18, fill=(2, 24, 68, 255))
    d.rectangle([40, fy + 14, 48, BRD16_H - 42], fill=AZURE + (255,))
    d.text((68, fy + 10), speaker["name"], font=fs_n, fill=WHITE + (255,))
    d.text((68, fy + 44), speaker["title"], font=fs_t, fill=SLATE + (255,))

    img.save(path)
    return img.size


# ---------- Words, Captions & Sidecars ----------
def load_words(path):
    data = json.load(open(path, encoding="utf-8"))
    out = []
    for s in data["segments"]:
        for w in s.get("words", []):
            out.append({"w": w["word"].strip(), "s": w["start"], "e": w["end"]})
    return out


def clean(w):
    return re.sub(r"[^\w']", "", w.lower())


def words_between(words, s, e):
    return [dict(w) for w in words if s <= (w["s"] + w["e"]) / 2 <= e]


def snap(words, s, e, pre=0.06, post=0.10):
    ws = words_between(words, s, e)
    if not ws:
        return s, e
    a = ws[0]["s"] - pre
    b = ws[-1]["e"] + post
    prev = [w for w in words if w["e"] <= ws[0]["s"] and w is not ws[0]]
    nxt = [w for w in words if w["s"] >= ws[-1]["e"] and w is not ws[-1]]
    if prev:
        a = max(a, (prev[-1]["e"] + ws[0]["s"]) / 2)
    if nxt:
        b = min(b, (nxt[0]["s"] + ws[-1]["e"]) / 2)
    return max(0.0, a), b


def apply_fixes(words, fixes):
    out = []
    for w in words:
        w = dict(w)
        k = clean(w["w"])
        if k in fixes:
            tail = re.sub(r"[\w']", "", w["w"])
            w["w"] = fixes[k] + tail
        out.append(w)
    return out


def group_words(words, max_words, max_px, fnt):
    groups, cur = [], []
    for w in words:
        too_wide = bool(cur) and fnt.getlength(" ".join(x["w"] for x in cur + [w])) > max_px
        if cur and (
            len(cur) >= max_words
            or too_wide
            or w["s"] - cur[-1]["e"] > 0.45
            or re.search(r"[.?!,]$", cur[-1]["w"])
        ):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_ass_9x16(path, words, fixes):
    words = apply_fixes(words, fixes)
    fnt = font("Poppins-Bold.ttf", CAP9_SIZE)
    groups = group_words(words, 3, SAFE9_W - 70, fnt)
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W9}
PlayResY: {H9}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,Poppins,{CAP9_SIZE},{rgb_to_ass(WHITE)},{rgb_to_ass(WHITE)},{rgb_to_ass(NAVY,0x28)},{rgb_to_ass(NAVY,0x28)},-1,0,0,0,100,100,0,0,3,18,0,2,{SAFE9_L},{W9-SAFE9_R},{H9-CAP9_BOTTOM},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    def t(x):
        x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = []
    for gi, g in enumerate(groups):
        for i, w in enumerate(g):
            start = w["s"] if i else g[0]["s"]
            end = g[i + 1]["s"] if i + 1 < len(g) else min(g[-1]["e"] + 0.12, groups[gi + 1][0]["s"] if gi + 1 < len(groups) else 1e9)
            txt = ""
            for j, x in enumerate(g):
                col = rgb_to_ass(GOLD) if j == i else rgb_to_ass(WHITE)
                txt += "{\\c%s}%s " % (col, x["w"])
            lines.append(f"Dialogue: 0,{t(start)},{t(end)},Cap,,0,0,0,,{txt.strip()}")
    pathlib.Path(path).write_text(hdr + "\n".join(lines) + "\n", encoding="utf-8")
    return groups


def build_ass_16x9(path, words, fixes):
    words = apply_fixes(words, fixes)
    fnt = font("Poppins-SemiBold.ttf", CAP16_SIZE)
    groups = group_words(words, 8, 1520, fnt)
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W16}
PlayResY: {H16}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,Poppins,{CAP16_SIZE},{rgb_to_ass(WHITE)},{rgb_to_ass(WHITE)},{rgb_to_ass(NAVY,0x20)},{rgb_to_ass(NAVY,0x20)},-1,0,0,0,100,100,0,0,3,14,0,2,140,140,{H16-CAP16_BOTTOM},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    def t(x):
        x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = []
    for gi, g in enumerate(groups):
        start = g[0]["s"]
        end = min(g[-1]["e"] + 0.15, groups[gi + 1][0]["s"] if gi + 1 < len(groups) else 1e9)
        txt = " ".join(x["w"] for x in g)
        lines.append(f"Dialogue: 0,{t(start)},{t(end)},Cap,,0,0,0,,{txt}")
    pathlib.Path(path).write_text(hdr + "\n".join(lines) + "\n", encoding="utf-8")
    return groups


def write_srt_vtt(groups, srt_path, vtt_path=None):
    def ts_srt(x):
        x = max(0.0, x)
        ms = int(round((x % 1) * 1000))
        s = int(x) % 60
        m = (int(x) // 60) % 60
        h = int(x) // 3600
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def ts_vtt(x):
        return ts_srt(x).replace(",", ".")

    srt_lines, vtt_lines = [], ["WEBVTT\n"]
    for i, g in enumerate(groups, 1):
        s = g[0]["s"]
        e = min(g[-1]["e"] + 0.15, groups[i][0]["s"] if i < len(groups) else g[-1]["e"] + 0.15)
        txt = " ".join(x["w"] for x in g)
        srt_lines.append(f"{i}\n{ts_srt(s)} --> {ts_srt(e)}\n{txt}\n")
        vtt_lines.append(f"{ts_vtt(s)} --> {ts_vtt(e)}\n{txt}\n")
    pathlib.Path(srt_path).write_text("\n".join(srt_lines), encoding="utf-8")
    if vtt_path:
        pathlib.Path(vtt_path).write_text("\n".join(vtt_lines), encoding="utf-8")


# ---------- Face-safe 9:16 overlay Y placement ----------
def load_ft(work_dir, src):
    m = re.search(r"(\d+)$", pathlib.Path(src).stem)
    if not m:
        return None
    p = work_dir / f"facetrack_{m.group(1)}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def choose_safe_y_9x16(items, work_dir, start, end, h):
    """Choose Y in [272, 1112 - h] that has zero intersection with tracked face_box."""
    candidates = [274, 960, 945, 970, 285]
    for cy_cand in candidates:
        if cy_cand < SAFE9_T or cy_cand + h > 1115:
            continue
        rect = (SAFE9_L, cy_cand, SAFE9_R, cy_cand + h)
        ok = True
        t = start
        while t <= end:
            it = next((i for i in items if i.get("type") == "clip" and i["out_start"] <= t < i["out_start"] + i["dur"]), None)
            if it:
                ft = load_ft(work_dir, it["src"])
                if ft:
                    ts = ft["t"]
                    st = it.get("src_start", it.get("s", 0.0)) + (t - it["out_start"])
                    idx = min(range(len(ts)), key=lambda k: abs(ts[k] - st))
                    fx, fy = ft["fx"][idx], ft["fy"][idx]
                    cx, cy = fx * W9, fy * H9
                    fb = (cx - 200, cy - 240, cx + 200, cy + 200)
                    if min(rect[2], fb[2]) > max(rect[0], fb[0]) and min(rect[3], fb[3]) > max(rect[1], fb[1]):
                        ok = False
                        break
            t += 0.20
        if ok:
            return cy_cand
    return 274


# ---------- FFmpeg Renderers ----------
def render_9x16(name, items, overlays, brolls, ass_words, fixes, out_dir, work, fps):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
    inputs, vf, seg_labels = [], [], []
    t_out = 0.0
    timeline = []
    for it in items:
        idx = len(inputs)
        if it["type"] == "clip":
            nfr = max(1, round((it["e"] - it["s"]) * fps))
            d = nfr / fps
            cmd += ["-ss", f"{it['s']:.3f}", "-t", f"{d + 0.25:.3f}", "-i", it["src"]]
            inputs.append(1)
            lab = f"v{idx}"
            base = f"[{idx}:v:0]setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop=3,trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p"
            vf.append(f"{base},scale={W9}:{H9}:flags=lanczos,setsar=1[{lab}]")
            vf.append(
                f"[{idx}:a:0]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                f"apad=whole_dur={d:.5f},atrim=0:{d:.5f},asetpts=PTS-STARTPTS,"
                f"afade=t=in:st=0:d=0.02,afade=t=out:st={max(0,d-0.04):.3f}:d=0.04[a{idx}]"
            )
            timeline.append({
                "out_start": round(t_out, 3),
                "dur": round(d, 3),
                "src": it["src"],
                "src_start": round(it["s"], 3),
                "mode": "wide",
            })
        else:
            nfr = max(1, round(it["dur"] * fps))
            d = nfr / fps
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{d:.3f}", "-i", it["png"]]
            inputs.append(1)
            cmd += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            inputs.append(1)
            lab = f"v{idx}"
            vf.append(f"[{idx}:v]trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.25[{lab}]")
            vf.append(f"[{idx+1}:a]aformat=channel_layouts=stereo,atrim=0:{d:.5f},asetpts=PTS-STARTPTS[a{idx}]")
        seg_labels.append((lab, f"a{idx}"))
        t_out += d

    total = t_out
    vf.append("".join(f"[{v}][{a}]" for v, a in seg_labels) + f"concat=n={len(seg_labels)}:v=1:a=1[vc][ac]")
    cur = "vc"
    for b_idx, br in enumerate(brolls):
        i = len(inputs)
        dur = br["end"] - br["start"]
        nfr = max(1, round(dur * fps))
        cmd += ["-ss", f"{br['s']:.3f}", "-t", f"{dur + 0.25:.3f}", "-i", br["src"]]
        inputs.append(1)
        vf.append(
            f"[{i}:v:0]setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop=3,trim=end_frame={nfr},"
            f"scale={W9}:{H9}:force_original_aspect_ratio=increase:flags=lanczos,crop={W9}:{H9},setsar=1,format=rgba,"
            f"fade=t=in:st=0:d=0.22:alpha=1,fade=t=out:st={max(0,dur-0.22):.3f}:d=0.22:alpha=1,"
            f"setpts=PTS+{br['start']:.3f}/TB[br{b_idx}]"
        )
        vf.append(f"[{cur}][br{b_idx}]overlay=0:0:eof_action=pass:enable='between(t,{br['start']:.3f},{br['end']:.3f})',format=yuv420p[vb{b_idx}]")
        cur = f"vb{b_idx}"

    for k, ov in enumerate(overlays):
        i = len(inputs)
        dur = ov["end"] - ov["start"]
        cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", ov["png"]]
        inputs.append(1)
        fi, fo = ov.get("fi", 0.2), ov.get("fo", 0.2)
        fades = (f"fade=t=in:st=0:d={fi}:alpha=1," if fi > 0 else "") + (f"fade=t=out:st={max(0,dur-fo):.3f}:d={fo}:alpha=1," if fo > 0 else "")
        vf.append(f"[{i}:v]format=rgba,{fades}setpts=PTS+{ov['start']:.3f}/TB[ov{k}]")
        vf.append(f"[{cur}][ov{k}]overlay={ov['x']}:{ov['y']}:eof_action=pass:enable='between(t,{ov['start']:.3f},{ov['end']:.3f})'[vo{k}]")
        cur = f"vo{k}"

    ass_path = work / f"{name}.ass"
    groups = build_ass_9x16(ass_path, ass_words, fixes)
    write_srt_vtt(groups, out_dir / f"{name}.srt")
    vf.append(f"[{cur}]ass={ass_path.name}[vf]")

    out = out_dir / f"{name}.mp4"
    cmd += [
        "-filter_complex", ";".join(vf), "-map", "[vf]", "-map", "[ac]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-maxrate", "9M", "-bufsize", "18M",
        "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        str(out),
    ]
    run_cwd = os.getcwd()
    os.chdir(work)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        os.chdir(run_cwd)
    if r.returncode:
        sys.stderr.write(r.stderr[-4000:])
        raise SystemExit(f"ffmpeg failed for {name}")

    ovl = []
    for ov in overlays:
        w_, h_ = Image.open(ov["png"]).size
        ovl.append({
            "name": pathlib.Path(ov["png"]).name,
            "kind": ov.get("kind", "overlay"),
            "x": ov["x"], "y": ov["y"], "w": w_, "h": h_,
            "start": round(ov["start"], 3), "end": round(ov["end"], 3),
        })
    broll_meta = [{"src": b["src"], "kind": b.get("kind", "camera"), "src_start": round(b["s"], 3), "out_start": round(b["start"], 3), "dur": round(b["end"] - b["start"], 3)} for b in brolls]
    layout = {
        "safe": [SAFE9_L, SAFE9_T, SAFE9_R, SAFE9_B],
        "overlays": ovl,
        "caption_band": [SAFE9_L, CAP9_BOTTOM - 130, SAFE9_R, CAP9_BOTTOM],
        "captions_hidden": [],
    }
    (out_dir / f"{name}.timeline.json").write_text(
        json.dumps({"file": out.name, "size": [W9, H9], "total": round(total, 3), "items": timeline, "broll_cuts": broll_meta, "layout": layout}, indent=2),
        encoding="utf-8",
    )
    return out, total


def render_16x9(name, items, overlays, brolls, ass_words, fixes, out_dir, work, fps, bg_png, spk_mask_png):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
    inputs, vf, seg_labels = [], [], []
    t_out = 0.0
    timeline = []
    for it in items:
        idx = len(inputs)
        if it["type"] == "clip":
            nfr = max(1, round((it["e"] - it["s"]) * fps))
            d = nfr / fps
            cmd += ["-ss", f"{it['s']:.3f}", "-t", f"{d + 0.25:.3f}", "-i", it["src"]]
            inputs.append(1)
            bg_i = len(inputs)
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{d + 0.1:.3f}", "-i", str(bg_png)]
            inputs.append(1)
            mk_i = len(inputs)
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{d + 0.1:.3f}", "-i", str(spk_mask_png)]
            inputs.append(1)

            lab = f"v{idx}"
            base = f"[{idx}:v:0]setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop=3,trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p"
            if it.get("mode") == "tight":
                crop_expr = f"crop=iw*0.82:iw*0.82*{SPK16_H}/{SPK16_W}:iw*0.09:ih*0.10"
            else:
                crop_expr = f"crop=iw:iw*{SPK16_H}/{SPK16_W}:0:ih*0.06"
            vf.append(f"{base},{crop_expr},scale={SPK16_W}:{SPK16_H}:flags=lanczos,setsar=1,format=rgba[spkr{idx}]")
            vf.append(f"[{mk_i}:v]fps={fps},trim=end_frame={nfr},setpts=PTS-STARTPTS,format=gray[mk{idx}]")
            vf.append(f"[spkr{idx}][mk{idx}]alphamerge[spkm{idx}]")
            vf.append(f"[{bg_i}:v]fps={fps},trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[bg{idx}]")
            vf.append(f"[bg{idx}][spkm{idx}]overlay={SPK16_X}:{SPK16_Y}:shortest=1,format=yuv420p[{lab}]")
            vf.append(
                f"[{idx}:a:0]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                f"apad=whole_dur={d:.5f},atrim=0:{d:.5f},asetpts=PTS-STARTPTS,"
                f"afade=t=in:st=0:d=0.02,afade=t=out:st={max(0,d-0.04):.3f}:d=0.04[a{idx}]"
            )
            timeline.append({
                "out_start": round(t_out, 3),
                "dur": round(d, 3),
                "src": it["src"],
                "src_start": round(it["s"], 3),
                "mode": it.get("mode", "wide"),
            })
        else:
            nfr = max(1, round(it["dur"] * fps))
            d = nfr / fps
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{d:.3f}", "-i", it["png"]]
            inputs.append(1)
            cmd += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            inputs.append(1)
            lab = f"v{idx}"
            vf.append(f"[{idx}:v]trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.25[{lab}]")
            vf.append(f"[{idx+1}:a]aformat=channel_layouts=stereo,atrim=0:{d:.5f},asetpts=PTS-STARTPTS[a{idx}]")
        seg_labels.append((lab, f"a{idx}"))
        t_out += d

    total = t_out
    vf.append("".join(f"[{v}][{a}]" for v, a in seg_labels) + f"concat=n={len(seg_labels)}:v=1:a=1[vc][ac]")
    cur = "vc"
    for k, ov in enumerate(overlays):
        i = len(inputs)
        dur = ov["end"] - ov["start"]
        cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", ov["png"]]
        inputs.append(1)
        fi, fo = ov.get("fi", 0.2), ov.get("fo", 0.2)
        fades = (f"fade=t=in:st=0:d={fi}:alpha=1," if fi > 0 else "") + (f"fade=t=out:st={max(0,dur-fo):.3f}:d={fo}:alpha=1," if fo > 0 else "")
        vf.append(f"[{i}:v]format=rgba,{fades}setpts=PTS+{ov['start']:.3f}/TB[ov{k}]")
        vf.append(f"[{cur}][ov{k}]overlay={ov['x']}:{ov['y']}:eof_action=pass:enable='between(t,{ov['start']:.3f},{ov['end']:.3f})'[vo{k}]")
        cur = f"vo{k}"

    for b_idx, br in enumerate(brolls):
        i = len(inputs)
        dur = br["end"] - br["start"]
        nfr = max(1, round(dur * fps))
        cmd += ["-ss", f"{br['s']:.3f}", "-t", f"{dur + 0.25:.3f}", "-i", br["src"]]
        inputs.append(1)
        if br.get("target") == "board":
            vf.append(
                f"[{i}:v:0]setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop=3,trim=end_frame={nfr},"
                f"scale={BRD16_W}:{BRD16_H}:flags=lanczos,setsar=1,format=rgba,"
                f"fade=t=in:st=0:d=0.22:alpha=1,fade=t=out:st={max(0,dur-0.22):.3f}:d=0.22:alpha=1,"
                f"setpts=PTS+{br['start']:.3f}/TB[br{b_idx}]"
            )
            vf.append(f"[{cur}][br{b_idx}]overlay={BRD16_X}:{BRD16_Y}:eof_action=pass:enable='between(t,{br['start']:.3f},{br['end']:.3f})'[vb{b_idx}]")
        else:
            bm_i = len(inputs)
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur + 0.1:.3f}", "-i", str(spk_mask_png)]
            inputs.append(1)
            vf.append(
                f"[{i}:v:0]setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop=3,trim=end_frame={nfr},"
                f"scale={SPK16_W}:{SPK16_H}:force_original_aspect_ratio=increase:flags=lanczos,crop={SPK16_W}:{SPK16_H},setsar=1,format=rgba[brv{b_idx}]"
            )
            vf.append(f"[{bm_i}:v]fps={fps},trim=end_frame={nfr},setpts=PTS-STARTPTS,format=gray[brm{b_idx}]")
            vf.append(
                f"[brv{b_idx}][brm{b_idx}]alphamerge,"
                f"fade=t=in:st=0:d=0.22:alpha=1,fade=t=out:st={max(0,dur-0.22):.3f}:d=0.22:alpha=1,"
                f"setpts=PTS+{br['start']:.3f}/TB[br{b_idx}]"
            )
            vf.append(f"[{cur}][br{b_idx}]overlay={SPK16_X}:{SPK16_Y}:eof_action=pass:enable='between(t,{br['start']:.3f},{br['end']:.3f})'[vb{b_idx}]")
        cur = f"vb{b_idx}"

    ass_path = work / f"{name}.ass"
    groups = build_ass_16x9(ass_path, ass_words, fixes)
    write_srt_vtt(groups, out_dir / f"{name}.srt", out_dir / f"{name}.vtt")
    vf.append(f"[{cur}]ass={ass_path.name}[vf]")

    out = out_dir / f"{name}.mp4"
    cmd += [
        "-filter_complex", ";".join(vf), "-map", "[vf]", "-map", "[ac]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-maxrate", "9M", "-bufsize", "18M",
        "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        str(out),
    ]
    run_cwd = os.getcwd()
    os.chdir(work)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        os.chdir(run_cwd)
    if r.returncode:
        sys.stderr.write(r.stderr[-4000:])
        raise SystemExit(f"ffmpeg failed for {name}")

    ovl = []
    for ov in overlays:
        w_, h_ = Image.open(ov["png"]).size
        ovl.append({
            "name": pathlib.Path(ov["png"]).name,
            "kind": ov.get("kind", "overlay"),
            "x": ov["x"], "y": ov["y"], "w": w_, "h": h_,
            "start": round(ov["start"], 3), "end": round(ov["end"], 3),
        })
    broll_meta = [{"src": b["src"], "kind": b.get("kind", "camera"), "src_start": round(b["s"], 3), "out_start": round(b["start"], 3), "dur": round(b["end"] - b["start"], 3)} for b in brolls]
    layout = {
        "safe": [SAFE16_L, SAFE16_T, SAFE16_R, SAFE16_B],
        "overlays": ovl,
        "caption_band": [140, CAP16_BOTTOM - 70, W16 - 140, CAP16_BOTTOM],
        "captions_hidden": [],
    }
    (out_dir / f"{name}.timeline.json").write_text(
        json.dumps({"file": out.name, "size": [W16, H16], "total": round(total, 3), "items": timeline, "broll_cuts": broll_meta, "layout": layout}, indent=2),
        encoding="utf-8",
    )
    return out, total


def resolve_src(batch, src_root, rel):
    if str(rel).startswith("work/"):
        return str(batch / rel)
    return str(src_root / rel)


# ---------- Builders for Trailer & Episodes ----------
def build_trailer(spec, batch, work, out16, out9, logo, bg16, mask16, fmt):
    tr = spec["trailer"]
    fps = spec["fps"]
    fixes = {k.lower(): v for k, v in spec.get("fixes", {}).items()}
    src_root = pathlib.Path(spec["source_root"])
    spk = spec["speaker"]

    # Cards
    sc16 = work / "tr_series_16x9.png"
    sc9 = work / "tr_series_9x16.png"
    make_series_card(sc16, (W16, H16), logo, tr["series_card"]["kicker"], tr["series_card"]["title"], tr["series_card"]["subtitle"])
    make_series_card(sc9, (W9, H9), logo, tr["series_card"]["kicker"], tr["series_card"]["title"], tr["series_card"]["subtitle"])

    cc16 = work / "tr_curr_16x9.png"
    cc9 = work / "tr_curr_9x16.png"
    make_summary_card(cc16, (W16, H16), tr["curriculum_card"]["kicker"], tr["curriculum_card"]["title"], tr["curriculum_card"]["items"])
    make_summary_card(cc9, (W9, H9), tr["curriculum_card"]["kicker"], tr["curriculum_card"]["title"], tr["curriculum_card"]["items"])

    ec16 = work / "tr_end_16x9.png"
    ec9 = work / "tr_end_9x16.png"
    make_end_card(ec16, (W16, H16), logo, tr["end_card"]["line"], tr["end_card"]["cta"])
    make_end_card(ec9, (W9, H9), logo, tr["end_card"]["line"], tr["end_card"]["cta"])

    for cur_fmt in ("16x9", "9x16"):
        if fmt not in ("both", cur_fmt):
            continue
        is16 = cur_fmt == "16x9"
        items, ovs, brolls, ass = [], [], [], []
        t = 0.0

        # 1. Cold open
        co = tr["cold_open"]
        w_co = load_words(batch / co["words"])
        s, e = snap(w_co, co["s"], co["e"])
        d = max(1, round((e - s) * fps)) / fps
        e = s + d
        items.append({"type": "clip", "src": str(src_root / co["src"]), "s": s, "e": e, "mode": "tight", "out_start": t, "dur": d})
        for w in words_between(w_co, s, e):
            ass.append({"w": w["w"], "s": t + (w["s"] - s), "e": t + (w["e"] - s)})
        if is16:
            brd = work / "tr_brd_co.png"
            make_16x9_board(brd, "TRAILER SIRI MASTERCLASS", spec["series_title"], " PENGENALAN", "5 ASAS KESIHATAN LELAKI SIBUK", tr["curriculum_card"]["items"][:3], spk)
            ovs.append({"png": str(brd), "x": BRD16_X, "y": BRD16_Y, "start": t + 0.1, "end": t + d - 0.1})
        else:
            hl = work / "tr_hl_co_9x16.png"
            _, hh = make_9x16_headline(hl, co["headline"])
            y_pos = choose_safe_y_9x16(items, work, t + 0.15, t + d - 0.15, hh)
            ovs.append({"png": str(hl), "x": SAFE9_L, "y": y_pos, "start": t + 0.15, "end": t + d - 0.15})
        t += d

        # 2. Series Title Card
        sc_dur = round(tr["series_card"]["dur"] * fps) / fps
        items.append({"type": "card", "png": str(sc16 if is16 else sc9), "dur": sc_dur, "out_start": t})
        t += sc_dur

        # 3. Highlights from all 5 episodes (EP01..EP05)
        for h_idx, hl_spec in enumerate(tr["highlights"]):
            w_hl = load_words(batch / hl_spec["words"])
            s, e = snap(w_hl, hl_spec["s"], hl_spec["e"])
            d = max(1, round((e - s) * fps)) / fps
            e = s + d
            mode = "wide" if h_idx % 2 == 0 else "tight"
            items.append({"type": "clip", "src": str(src_root / hl_spec["src"]), "s": s, "e": e, "mode": mode, "out_start": t, "dur": d})
            for w in words_between(w_hl, s, e):
                ass.append({"w": w["w"], "s": t + (w["s"] - s), "e": t + (w["e"] - s)})
            if is16:
                brd = work / f"tr_brd_ep{hl_spec['ep']}.png"
                make_16x9_board(brd, hl_spec["badge"], spec["series_subtitle"], f"SOROTAN EP 0{hl_spec['ep']}", hl_spec["headline"].replace("*", ""), hl_spec["points"], spk)
                ovs.append({"png": str(brd), "x": BRD16_X, "y": BRD16_Y, "start": t + 0.1, "end": t + d - 0.1})
                if "broll" in hl_spec:
                    br = hl_spec["broll"]
                    bs = t + 1.4
                    be = min(t + d - 0.4, bs + 3.0)
                    brolls.append({"src": resolve_src(batch, src_root, br["src"]), "s": br["s"], "start": bs, "end": be, "kind": br.get("kind", "stock"), "target": "speaker"})
                if "motion_16x9" in hl_spec:
                    ms = t + max(2.2, d - 4.4)
                    me = t + d - 0.2
                    brolls.append({"src": resolve_src(batch, src_root, hl_spec["motion_16x9"]), "s": 0.0, "start": ms, "end": me, "kind": "motion_chart", "target": "board"})
            else:
                hp = work / f"tr_hl_ep{hl_spec['ep']}_9x16.png"
                _, hh = make_9x16_headline(hp, hl_spec["headline"])
                y_pos = choose_safe_y_9x16(items, work, t + 0.15, t + min(d - 0.15, 3.8), hh)
                ovs.append({"png": str(hp), "x": SAFE9_L, "y": y_pos, "start": t + 0.15, "end": t + min(d - 0.15, 3.8)})
                if "broll" in hl_spec:
                    br = hl_spec["broll"]
                    bs = t + 3.9
                    be = min(t + d - 0.3, bs + 2.6)
                    if be > bs + 0.8:
                        brolls.append({"src": resolve_src(batch, src_root, br["src"]), "s": br["s"], "start": bs, "end": be, "kind": br.get("kind", "stock")})
                if "motion_9x16" in hl_spec and d > 6.8:
                    ms = t + 6.6
                    me = t + d - 0.2
                    if me > ms + 1.2:
                        brolls.append({"src": resolve_src(batch, src_root, hl_spec["motion_9x16"]), "s": 0.0, "start": ms, "end": me, "kind": "motion_chart"})
            t += d

        # 4. 5-Episode Curriculum Summary Card
        cc_dur = round(tr["curriculum_card"]["dur"] * fps) / fps
        items.append({"type": "card", "png": str(cc16 if is16 else cc9), "dur": cc_dur, "out_start": t})
        t += cc_dur

        # 5. End Card
        ec_dur = round(tr["end_card"]["dur"] * fps) / fps
        items.append({"type": "end", "png": str(ec16 if is16 else ec9), "dur": ec_dur, "out_start": t})
        t += ec_dur

        rname = f"{tr['slug']}_{cur_fmt}"
        print(f"Rendering {rname} ...", flush=True)
        if is16:
            out, tot = render_16x9(rname, items, ovs, brolls, ass, fixes, out16, work, fps, bg16, mask16)
        else:
            out, tot = render_9x16(rname, items, ovs, brolls, ass, fixes, out9, work, fps)
        print(f"  -> {out.name} ({tot:.1f}s, {len(brolls)} visual cuts)", flush=True)


def build_episode(ep, spec, batch, work, out16, out9, logo, bg16, mask16, lt9_png, lt9_h, fmt):
    fps = spec["fps"]
    fixes = {k.lower(): v for k, v in spec.get("fixes", {}).items()}
    src_root = pathlib.Path(spec["source_root"])
    spk = spec["speaker"]
    eid = ep["id"]

    # Summary & End cards
    sum16 = work / f"{eid}_sum_16x9.png"
    sum9 = work / f"{eid}_sum_9x16.png"
    make_summary_card(sum16, (W16, H16), f"RINGKASAN {ep['badge']}", f"3 AMALAN UTAMA — {ep['title'].upper()}", ep["takeaways"])
    make_summary_card(sum9, (W9, H9), f"RINGKASAN {ep['badge']}", "3 AMALAN UTAMA EPISOD INI", ep["takeaways"])

    ec16 = work / f"{eid}_end_16x9.png"
    ec9 = work / f"{eid}_end_9x16.png"
    make_end_card(ec16, (W16, H16), logo, ep["end_card"]["line"], ep["end_card"]["cta"])
    make_end_card(ec9, (W9, H9), logo, ep["end_card"]["line"], ep["end_card"]["cta"])

    # ---- 16:9 Full Episode ----
    if fmt in ("both", "16x9"):
        items, ovs, brolls, ass = [], [], [], []
        t = 0.0

        # Episode Title Opener Card (1.8s)
        op16 = work / f"{eid}_open_16x9.png"
        make_series_card(op16, (W16, H16), logo, ep["badge"], ep["title"].upper(), spec["series_subtitle"])
        op_dur = round(1.8 * fps) / fps
        items.append({"type": "card", "png": str(op16), "dur": op_dur, "out_start": t})
        t += op_dur

        for c_idx, ch in enumerate(ep["chapters"]):
            # Chapter Bumper Card (1.5s)
            ch_png = work / f"{eid}_ch{c_idx+1}_16x9.png"
            make_chapter_card(ch_png, (W16, H16), ep["badge"], ch["num"], ch["title"], ch["slide_points"])
            ch_dur = round(1.5 * fps) / fps
            items.append({"type": "card", "png": str(ch_png), "dur": ch_dur, "out_start": t})
            t += ch_dur

            ch_start = t
            for sg in ch["segments"]:
                w_sg = load_words(batch / sg["words"])
                s, e = snap(w_sg, sg["s"], sg["e"])
                d = max(1, round((e - s) * fps)) / fps
                e = s + d
                items.append({"type": "clip", "src": str(src_root / sg["src"]), "s": s, "e": e, "mode": sg.get("mode", "wide"), "out_start": t, "dur": d})
                for w in words_between(w_sg, s, e):
                    ass.append({"w": w["w"], "s": t + (w["s"] - s), "e": t + (w["e"] - s)})
                t += d
            ch_end = t

            brd = work / f"{eid}_brd_ch{c_idx+1}.png"
            make_16x9_board(brd, ep["badge"], ep["title"], ch["num"], ch["slide_title"], ch["slide_points"], spk)
            ovs.append({"png": str(brd), "x": BRD16_X, "y": BRD16_Y, "start": ch_start + 0.08, "end": ch_end - 0.08})

            if "broll" in ch:
                br = ch["broll"]
                ch_len = ch_end - ch_start
                bs = ch_start + min(br.get("offset", 6.0), max(1.5, ch_len - br["dur"] - 0.5))
                be = min(ch_end - 0.3, bs + br["dur"])
                if be > bs + 1.0:
                    brolls.append({"src": resolve_src(batch, src_root, br["src"]), "s": br["s"], "start": bs, "end": be, "kind": br.get("kind", "camera"), "target": "speaker"})

            if "motion_16x9" in ch:
                ch_len = ch_end - ch_start
                ms = ch_start + min(12.0, max(2.0, ch_len * 0.42))
                me = min(ch_end - 0.4, ms + 4.2)
                if me > ms + 1.5:
                    brolls.append({"src": resolve_src(batch, src_root, ch["motion_16x9"]), "s": 0.0, "start": ms, "end": me, "kind": "motion_chart", "target": "board"})

        # Key-Takeaway Summary Card (3.0s)
        s_dur = round(3.0 * fps) / fps
        items.append({"type": "card", "png": str(sum16), "dur": s_dur, "out_start": t})
        t += s_dur

        # End Card
        e_dur = round(ep["end_card"]["dur"] * fps) / fps
        items.append({"type": "end", "png": str(ec16), "dur": e_dur, "out_start": t})
        t += e_dur

        rname16 = f"{ep['slug']}_16x9"
        print(f"Rendering {rname16} ...", flush=True)
        out, tot = render_16x9(rname16, items, ovs, brolls, ass, fixes, out16, work, fps, bg16, mask16)
        print(f"  -> {out.name} ({tot:.1f}s, {len(brolls)} visual cuts)", flush=True)

    # ---- 9:16 Vertical Cutdown ----
    if fmt in ("both", "9x16"):
        items, ovs, brolls, ass = [], [], [], []
        t = 0.0
        seg_windows = []
        for sg in ep["short_segments"]:
            w_sg = load_words(batch / sg["words"])
            s, e = snap(w_sg, sg["s"], sg["e"])
            d = max(1, round((e - s) * fps)) / fps
            e = s + d
            seg_windows.append((t, t + d))
            items.append({"type": "clip", "src": str(src_root / sg["src"]), "s": s, "e": e, "mode": "wide", "out_start": t, "dur": d})
            for w in words_between(w_sg, s, e):
                ass.append({"w": w["w"], "s": t + (w["s"] - s), "e": t + (w["e"] - s)})
            t += d

        for br in ep.get("short_brolls", []):
            si = min(br["seg"], len(seg_windows) - 1)
            sw_s, sw_e = seg_windows[si]
            bs = sw_s + min(br.get("offset", 5.5), max(1.0, (sw_e - sw_s) - br["dur"] - 0.4))
            be = min(sw_e - 0.25, bs + br["dur"])
            if be > bs + 1.0:
                brolls.append({"src": resolve_src(batch, src_root, br["src"]), "s": br["s"], "start": bs, "end": be, "kind": br.get("kind", "camera")})

        # Hook Headline (0.2s .. 3.4s)
        hl9 = work / f"{eid}_hl_9x16.png"
        _, hh = make_9x16_headline(hl9, f"{ep['badge']}: {ep['hook_headline']}")
        hy = choose_safe_y_9x16(items, work, 0.2, 3.4, hh)
        ovs.append({"png": str(hl9), "x": SAFE9_L, "y": hy, "start": 0.2, "end": 3.4})

        # Speaker Lower Third (3.8s .. 7.6s)
        lty = choose_safe_y_9x16(items, work, 3.8, 7.6, lt9_h)
        ovs.append({"png": str(lt9_png), "x": SAFE9_L, "y": lty, "start": 3.8, "end": 7.6})

        # Callout Cards during body segments
        for c_idx, co in enumerate(ep.get("short_callouts", [])):
            si = min(co["start_seg"], len(seg_windows) - 1)
            cs = max(8.0, seg_windows[si][0] + 0.4)
            ce = min(seg_windows[si][1] - 0.3, cs + 4.8)
            if ce > cs + 1.2:
                cp = work / f"{eid}_co{c_idx+1}_9x16.png"
                _, ch_h = make_9x16_callout(cp, co["title"], co["sub"])
                cy_pos = choose_safe_y_9x16(items, work, cs, ce, ch_h)
                ovs.append({"png": str(cp), "x": SAFE9_L, "y": cy_pos, "start": cs, "end": ce})

        # Key-Takeaway Summary Card (2.8s)
        s_dur = round(2.8 * fps) / fps
        items.append({"type": "card", "png": str(sum9), "dur": s_dur, "out_start": t})
        t += s_dur

        # End Card
        e_dur = round(ep["end_card"]["dur"] * fps) / fps
        items.append({"type": "end", "png": str(ec9), "dur": e_dur, "out_start": t})
        t += e_dur

        rname9 = f"{ep['slug']}_9x16"
        print(f"Rendering {rname9} ...", flush=True)
        out, tot = render_9x16(rname9, items, ovs, brolls, ass, fixes, out9, work, fps)
        print(f"  -> {out.name} ({tot:.1f}s, {len(brolls)} B-roll cuts)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--only", help="EP00, EP01, EP02, EP03, EP04, or EP05")
    ap.add_argument("--format", default="both", choices=["both", "16x9", "9x16"])
    a = ap.parse_args()

    spec_path = pathlib.Path(a.spec).resolve()
    spec = json.load(open(spec_path, encoding="utf-8"))
    batch = spec_path.parent.parent if spec_path.parent.name == "work" else spec_path.parent
    work = batch / "work"
    out16 = batch / "renders" / "16x9"
    out9 = batch / "renders" / "9x16"
    work.mkdir(parents=True, exist_ok=True)
    out16.mkdir(parents=True, exist_ok=True)
    out9.mkdir(parents=True, exist_ok=True)

    logo = ROOT / "brands" / spec["brand"] / "design-system" / "logos" / "logo_ssc_primary_dark.png"

    # Shared 16:9 canvas background & speaker rounded mask
    bg16 = work / "bg_16x9_studio.png"
    bg_img = make_gradient(W16, H16)
    bd = ImageDraw.Draw(bg_img)
    bd.rounded_rectangle([SPK16_X - 4, SPK16_Y - 4, SPK16_X + SPK16_W + 3, SPK16_Y + SPK16_H + 3], radius=SPK16_R + 3, outline=GOLD, width=3)
    bg_img.save(bg16)

    mask16 = work / "spk_mask_16x9.png"
    m = Image.new("L", (SPK16_W, SPK16_H), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, SPK16_W - 1, SPK16_H - 1], radius=SPK16_R, fill=255)
    m.save(mask16)

    # Shared 9:16 lower third
    lt9_png = work / "lt_9x16.png"
    _, lt9_h = make_9x16_lower_third(lt9_png, spec["speaker"]["name"], spec["speaker"]["title"])

    if not a.only or a.only.upper() == "EP00":
        build_trailer(spec, batch, work, out16, out9, logo, bg16, mask16, a.format)

    for ep in spec["episodes"]:
        if a.only and ep["id"].upper() != a.only.upper():
            continue
        build_episode(ep, spec, batch, work, out16, out9, logo, bg16, mask16, lt9_png, lt9_h, a.format)


if __name__ == "__main__":
    main()
