#!/usr/bin/env python3
"""Doctor reel, Vox template (SS Clinic Educational mode).

Implements skills/doctor-reel-vox/references/render-spec.md.

Subcommands
  detect-card  RAW                       -> prints the disclaimer-card window (spec s2)
  words        RAW CHUNKS.json --card a b -> word timings from chunk transcript (spec s3)
  prep-layers  IMAGE OUTDIR [--sticker]  -> fg/bg parallax layers or a hook sticker (spec s4D)
  render       PLAN.json                 -> full pipeline: 3 parts, audio, end card, assemble, QA

The plan JSON is written per clip in the pipeline's Plan step. See references/render-spec.md
section 3 and the PLAN_EXAMPLE at the bottom of this file. Paths in the plan are relative to the
batch folder (batches/<batch>/), which comes from WORK_ROOT in config.env.
"""
import argparse, json, math, os, pathlib, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO = pathlib.Path(__file__).resolve().parents[1]
W, H, FPS = 1080, 1920, 30
ENCODE = ["-c:v", "libx264", "-preset", "slow", "-crf", "24", "-maxrate", "3.2M",
          "-bufsize", "6.4M", "-pix_fmt", "yuv420p"]
FONT_DIRS = [REPO / "assets" / "fonts", pathlib.Path(r"C:\Windows\Fonts"),
             pathlib.Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")),
             pathlib.Path("/usr/share/fonts/truetype")]
# Combined Reels + TikTok safe area (skills/dtc-reels-editor/references/safe-zones.md)
SAFE = (120, 270, 960, 1248)
LT_Y = 1010  # lower-third centre: inside the safe area, above the subtitle band, below the face
CREAM = (244, 236, 220)
AZURE = (0x21, 0xA1, 0xF7)
TEAL_BOX = (18, 92, 110, 225)


# ---------------------------------------------------------------- config / io
def load_config():
    cfg = {}
    for name in ("config.env", "config.example.env"):
        p = REPO / name
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    cfg.setdefault(k.strip(), v.strip())
    return cfg


def font(name, size, weight=None):
    for d in FONT_DIRS:
        p = d / name
        if p.exists():
            f = ImageFont.truetype(str(p), size)
            if weight is not None:
                f.set_variation_by_axes([weight])
            return f
    raise SystemExit(f"Font not found: {name} (expected in assets/fonts or the system font folders)")


def run(cmd, **kw):
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit(f"Command failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def probe_duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", str(path)]).strip())


def read_frames(path, t0, t1, w=W, h=H):
    """Yield (t, uint8 RGB frame) from t0 to t1, scaled and padded to w x h."""
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={FPS}"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(path), "-t", f"{t1 - t0:.3f}",
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    n, size = 0, w * h * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield t0 + n / FPS, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        n += 1
    p.wait()


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3


def ease_back(p, s=1.70158):
    p = clamp(p) - 1
    return p * p * ((s + 1) * p + s) + 1


def prog(t, a, b):
    return clamp((t - a) / max(1e-6, b - a))


# ---------------------------------------------------------------- s2 disclaimer card
def detect_card(raw):
    """Share of pixels with B>120 and R<60 on a 54x96 downscale; ON when > 0.25."""
    on = []
    for t, f in read_frames(raw, 0, probe_duration(raw), 54, 96):
        r, b = f[..., 0].astype(int), f[..., 2].astype(int)
        on.append((t, ((b > 120) & (r < 60)).mean() > 0.25))
    runs, start = [], None
    for t, v in on + [(on[-1][0] + 1 / FPS, False)]:
        if v and start is None:
            start = t
        elif not v and start is not None:
            runs.append((round(start, 3), round(t, 3)))
            start = None
    runs = [r for r in runs if r[1] - r[0] >= 0.5]
    if not runs:
        raise SystemExit("No disclaimer card found. Check the raw is the team export with the card.")
    return runs[0]


# ---------------------------------------------------------------- s3 word timing
def read_audio(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0, sr


def words_from_chunks(raw, chunks, card):
    """Spread each chunk's words over voiced frames (>-36 dB), card excluded,
    in proportion to (letters + 1.5). chunks = [{start, end, text}]."""
    audio, sr = read_audio(raw)
    hop = sr // 100  # 10 ms frames
    out = []
    for c in chunks:
        a, b = c["start"], c["end"]
        ts = np.arange(a, b, 0.01)
        voiced = []
        for t in ts:
            if card and card[0] <= t < card[1]:
                continue
            seg = audio[int(t * sr): int(t * sr) + hop]
            if len(seg) and 20 * math.log10(np.sqrt((seg ** 2).mean()) + 1e-9) > -36:
                voiced.append(t)
        if not voiced:
            voiced = [t for t in ts if not (card and card[0] <= t < card[1])] or list(ts)
        words = c["text"].split()
        wts = np.array([len(w.strip(".,!?;:")) + 1.5 for w in words])
        edges = np.concatenate([[0], np.cumsum(wts) / wts.sum()]) * len(voiced)
        for i, w in enumerate(words):
            i0 = min(int(edges[i]), len(voiced) - 1)
            i1 = min(max(int(edges[i + 1]) - 1, i0), len(voiced) - 1)
            out.append({"w": w, "s": round(voiced[i0], 3), "e": round(voiced[i1] + 0.01, 3)})
    return out


# ---------------------------------------------------------------- s4D layer prep
def prep_layers(image, outdir, sticker=False, person=True):
    from rembg import remove, new_session
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    img = Image.open(image).convert("RGB")
    small = img.copy()
    small.thumbnail((1024, 1024))
    try:
        sess = new_session("u2net_human_seg" if person else "u2net")
        cut = remove(small, session=sess)
    except MemoryError:
        cut = remove(small, session=new_session("birefnet-general-lite"))
    alpha = np.array(cut.split()[-1].resize(img.size, Image.LANCZOS))
    stem = pathlib.Path(image).stem
    if sticker:
        ys, xs = np.nonzero(alpha > 40)
        box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        rgba = np.dstack([np.array(img), alpha])[box[1]:box[3], box[0]:box[2]].copy()
        h = rgba.shape[0]
        fade = int(h * 0.11)
        ramp = np.linspace(1, 0, fade) ** 1.3
        rgba[h - fade:, :, 3] = (rgba[h - fade:, :, 3] * ramp[:, None]).astype(np.uint8)
        p = outdir / f"{stem}_sticker.png"
        Image.fromarray(rgba).save(p)
        return {"sticker": str(p)}
    a_soft = cv2.GaussianBlur(alpha, (0, 0), 1.2)
    fg = np.dstack([np.array(img), a_soft])
    mask = cv2.dilate((alpha > 40).astype(np.uint8) * 255, np.ones((25, 25), np.uint8))
    bg = cv2.inpaint(np.array(img)[..., ::-1], mask, 12, cv2.INPAINT_TELEA)[..., ::-1]
    pf, pb = outdir / f"{stem}_fg.png", outdir / f"{stem}_bg.png"
    Image.fromarray(fg).save(pf)
    Image.fromarray(bg).save(pb)
    return {"fg": str(pf), "bg": str(pb)}


# ---------------------------------------------------------------- image helpers (float RGB 0..1)
def to_f(a):
    return a.astype(np.float32) / 255.0


def to_u8(f):
    return (np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8)


def lum(f):
    return f[..., 0] * 0.299 + f[..., 1] * 0.587 + f[..., 2] * 0.114


def vignette_map(k, cy=0.45, r=0.72):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H * cy) / (H / 2)) ** 2) / r
    return (1 - k * np.clip(d, 0, 1.6) ** 2)[..., None]


_VIG = None
_RNG = np.random.default_rng(7)


def editorial(f, grain=0.006):
    global _VIG
    if _VIG is None:
        _VIG = vignette_map(0.30)
    l = lum(f)[..., None]
    f = l + (f - l) * 0.86  # keep 86% saturation
    f = (f - 0.5) * 1.06 + 0.49
    f = 0.035 + f * 0.95
    l = lum(f)[..., None]
    f = f + (1 - l) ** 2 * np.array([-0.012, 0.004, 0.018], np.float32) \
          + l ** 2 * np.array([0.022, 0.008, -0.018], np.float32)
    q = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    hi = np.clip(q - 0.72, 0, 1) / 0.28
    hi = cv2.resize(cv2.GaussianBlur(hi, (0, 0), 6), (W, H))
    f = 1 - (1 - f) * (1 - hi * 0.55)
    f = f * _VIG
    f = f + _RNG.normal(0, grain, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)
    return np.clip(f, 0, 1)


def zoom(f, z, anchor=(0.5, 0.5), shift=(0.0, 0.0)):
    if abs(z - 1) < 1e-4 and shift == (0.0, 0.0):
        return f
    ax, ay = anchor[0] * W, anchor[1] * H
    m = np.float32([[z, 0, ax * (1 - z) + shift[0]], [0, z, ay * (1 - z) + shift[1]]])
    return cv2.warpAffine(f, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def zoom_blur(f, amount, n=5):
    """Radial zoom blur: average of n slightly larger copies."""
    if amount <= 0.001:
        return f
    acc = np.zeros_like(f)
    for i in range(n):
        acc += zoom(f, 1 + amount * i / (n - 1))
    return acc / n


def paste(dst, sprite, cx, cy, alpha=1.0, scale=1.0, rot=0.0):
    """Alpha-composite an RGBA uint8 sprite centred at (cx, cy) onto float RGB dst."""
    if alpha <= 0.003:
        return dst
    sp = sprite
    if abs(scale - 1) > 1e-3 or abs(rot) > 1e-3:
        h, w = sp.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
        c, s = abs(m[0, 0]), abs(m[0, 1])
        nw, nh = int(h * s + w * c) + 2, int(h * c + w * s) + 2
        m[0, 2] += nw / 2 - w / 2
        m[1, 2] += nh / 2 - h / 2
        sp = cv2.warpAffine(sp, m, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    h, w = sp.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return dst
    s = sp[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32) / 255.0
    a = s[..., 3:4] * alpha
    dst[ya:yb, xa:xb] = dst[ya:yb, xa:xb] * (1 - a) + s[..., :3] * a
    return dst


# ---------------------------------------------------------------- s4B hook assets
def blueprint_bg():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H / 2) / H) ** 2) * 2
    base = np.array([0.05, 0.09, 0.36], np.float32) * (1.15 - 0.55 * d)[..., None]
    g = np.zeros((H, W), np.float32)
    g[:, (np.arange(W) % 30) == 0] = 0.35
    g[(np.arange(H) % 30) == 0, :] = 0.35
    for o in (0, 1):
        g[:, (np.arange(W) % 90) == o] = 1.0
        g[(np.arange(H) % 90) == o, :] = 1.0
    g = cv2.GaussianBlur(g, (0, 0), 0.8)
    f = base + g[..., None] * np.array([0.30, 0.42, 0.85], np.float32) * 0.55
    f += _RNG.normal(0, 0.015, (H, W, 1)).astype(np.float32)
    return np.clip(f, 0, 1)


def glow_layer(rgba, color, radius, k):
    """Return RGBA image: tinted blurred alpha as glow under the original."""
    a = rgba.split()[-1].filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: min(255, int(v * k)))
    g = Image.new("RGBA", rgba.size, color + (0,))
    g.putalpha(a)
    return g


def treat_sticker(path):
    """B&W, die-cut white edge, blue glow, drop shadow, fitted to 860x900."""
    im = Image.open(path).convert("RGBA")
    im.thumbnail((860 - 60, 900 - 60), Image.LANCZOS)
    a = im.split()[-1]
    rgb = np.array(im)[..., :3].astype(np.float32)
    l = rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    l = np.clip((l - 128) * 1.25 + 128, 0, 255)
    bw = Image.fromarray(np.dstack([l, l, l]).astype(np.uint8))
    pad = 60
    cw, ch = im.width + pad * 2, im.height + pad * 2
    a_p = Image.new("L", (cw, ch), 0)
    a_p.paste(a, (pad, pad))
    edge = a_p.filter(ImageFilter.MaxFilter(15))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh.putalpha(edge.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55)))
    out.paste(sh, (8, 14), sh)
    gl = Image.new("RGBA", (cw, ch), (180, 215, 255, 0))
    gl.putalpha(edge.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.6)))
    out = Image.alpha_composite(out, gl)
    white = Image.new("RGBA", (cw, ch), (255, 255, 255, 0))
    white.putalpha(edge)
    out = Image.alpha_composite(out, white)
    body = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    body.paste(bw.convert("RGBA"), (pad, pad), a)
    return np.array(Image.alpha_composite(out, body))


def question_sprite(size):
    f = font("Poppins-Black.ttf", size)
    pad = 40
    tw = int(f.getlength("?")) + pad * 2
    im = Image.new("RGBA", (tw, size + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad, pad // 2), "?", font=f, fill=(255, 255, 255, 255))
    return np.array(Image.alpha_composite(glow_layer(im, (70, 170, 255), 12, 1.2), im))


def hook_caption(top, keyword):
    """Two-tier hook caption as RGBA (v3 glow minus 25%), padded 60 px so the halo never clips."""
    ft = font("Gelasio-VF.ttf", 72, weight=700)
    fk = font("Poppins-Bold.ttf", 70)
    keyword = keyword.upper()
    pad = 60
    tw = max(int(ft.getlength(top)) if top else 0, int(fk.getlength(keyword))) + pad * 2
    top_h = 0
    if top:
        tb = ft.getbbox(top)
        top_h = tb[3]
    kb = fk.getbbox(keyword)
    gap = 16 if top else 0
    hgt = pad * 2 + top_h + gap + (kb[3] - kb[1])
    im = Image.new("RGBA", (tw, hgt), (0, 0, 0, 0))
    lt = Image.new("RGBA", im.size, (0, 0, 0, 0))
    if top:
        ImageDraw.Draw(lt).text(((tw - ft.getlength(top)) / 2, pad), top, font=ft, fill=(255, 255, 255, 255))
    lk = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ky = pad + top_h + gap - kb[1]
    ImageDraw.Draw(lk).text(((tw - fk.getlength(keyword)) / 2, ky), keyword, font=fk, fill=AZURE + (255,))
    # shadow + glows
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(Image.alpha_composite(lt, lk).split()[-1].filter(ImageFilter.GaussianBlur(6))
                .point(lambda v: int(v * 0.85)))
    halo = glow_layer(lk, (60, 160, 255), 26, 0.675)
    layers = [sh, halo, glow_layer(lt, (235, 245, 255), 16, 0.64), glow_layer(lk, (70, 170, 255), 18, 0.94), lt, lk]
    for L in layers:
        im = Image.alpha_composite(im, L)
    split_y = pad + top_h + gap // 2
    a = np.array(im)
    return a[:split_y + 1].copy(), a[split_y:].copy()  # top part, keyword part (animated separately)


def scrim_layer(cy, sigma=170, k=0.45):
    y = np.arange(H, dtype=np.float32)
    return (1 - k * np.exp(-((y - cy) ** 2) / (2 * sigma ** 2)))[:, None, None]


def torn_mask(p, seed=3):
    """Reveal mask rising bottom->top with a multi-sine jagged edge; returns (mask, paper band)."""
    x = np.arange(W, dtype=np.float32)
    edge = sum(a * np.sin(x * fr + ph) for a, fr, ph in
               ((18, 0.011, seed), (9, 0.037, seed * 2.1), (5, 0.093, seed * 0.7), (2.5, 0.21, seed * 3.3)))
    level = H * (1 - ease_out_cubic(p)) + 60 * (1 - p)
    yy = np.arange(H, dtype=np.float32)[:, None]
    e = level + edge[None, :]
    reveal = (yy > e).astype(np.float32)
    band = ((yy > e - 14) & (yy <= e)).astype(np.float32)
    return reveal[..., None], band[..., None]


# ---------------------------------------------------------------- s4C subtitles / lower third
def group_words(words, card_end):
    """At most 26 characters and 5 words per subtitle, break at punctuation."""
    groups, cur = [], []
    for w in (w for w in words if w["s"] >= card_end - 0.01):
        cand = " ".join(x["w"] for x in cur + [w])
        if cur and (len(cand) > 26 or len(cur) >= 5):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w["w"][-1:] in ",.!?;:":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        # shows from its first word to the next group's start, held at most 0.45 s past its last word
        e = g[-1]["e"] + 0.45
        if i + 1 < len(groups):
            e = min(e, groups[i + 1][0]["s"])
        out.append({"text": " ".join(x["w"] for x in g), "s": g[0]["s"], "e": e})
    return out


def fit_width(arr, maxw):
    """Scale a sprite down (never up) so it fits maxw; keeps subtitles inside the safe area."""
    if arr.shape[1] <= maxw:
        return arr
    k = maxw / arr.shape[1]
    return np.array(Image.fromarray(arr).resize((maxw, max(1, int(arr.shape[0] * k))), Image.LANCZOS))


def sub_plain(text):
    f = font("Poppins-SemiBold.ttf", 54)
    pad = 30
    im = Image.new("RGBA", (int(f.getlength(text)) + pad * 2, 54 + pad * 2 + 16), (0, 0, 0, 0))
    t = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(t).text((pad, pad), text, font=f, fill=(255, 255, 255, 255))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(t.split()[-1].filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(v * 0.9)))
    return fit_width(np.array(Image.alpha_composite(Image.alpha_composite(im, sh), t)), SAFE[2] - SAFE[0] + 60)


def sub_boxed(text):
    f = font("InstrumentSerif-Italic.ttf", 66)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + 36, bb[3] - bb[1] + 36
    im = Image.new("RGBA", (w, h), TEAL_BOX)
    ImageDraw.Draw(im).text((18 - bb[0], 18 - bb[1]), text, font=f, fill=CREAM + (255,))
    return fit_width(np.array(im), SAFE[2] - SAFE[0])


def lower_third(name_title):
    name, _, title = name_title.partition(",")
    fn, ft = font("Poppins-Bold.ttf", 44), font("Poppins-Medium.ttf", 30)
    w = int(max(fn.getlength(name), ft.getlength(title.strip()))) + 72
    im = Image.new("RGBA", (w, 132), (10, 30, 70, 210))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8, 132], fill=AZURE + (255,))
    d.text((36, 16), name.strip(), font=fn, fill=(255, 255, 255, 255))
    d.text((36, 80), title.strip(), font=ft, fill=(210, 225, 240, 255))
    return np.array(im)


# ---------------------------------------------------------------- end-card logo
def find_logo(brand):
    """Clinic logo for a dark background, from brand.json logo_files via DESIGN_SYSTEM_ROOT.
    Never retypes the wordmark: stops if no file is found."""
    ref = brand.get("logo_files", {}).get("on_dark_background", "logo_ssc_primary_dark.svg")
    stem = pathlib.Path(ref.split(" ")[0]).stem
    roots = [REPO / "brands" / "ssclinic" / "logos"]
    ds = load_config().get("DESIGN_SYSTEM_ROOT")
    if ds:
        roots.append(pathlib.Path(ds))
    roots.append(REPO.parent / "ss-assets")
    for r in roots:
        if r.exists():
            hits = sorted(r.rglob(f"{stem}.png"), key=lambda q: (".svelte-kit" in str(q), len(str(q))))
            if hits:
                return hits[0]
    raise SystemExit(f"Clinic logo {stem}.png not found under {', '.join(map(str, roots))}. "
                     "Set DESIGN_SYSTEM_ROOT in config.env. The wordmark is never retyped.")


# ---------------------------------------------------------------- s4D overlays
def load_rgba(path, size=None):
    im = Image.open(path).convert("RGBA")
    if size:
        # cover-fit to size
        s = max(size[0] / im.width, size[1] / im.height)
        im = im.resize((int(im.width * s + 0.5), int(im.height * s + 0.5)), Image.LANCZOS)
        l, t = (im.width - size[0]) // 2, (im.height - size[1]) // 2
        im = im.crop((l, t, l + size[0], t + size[1]))
    return np.array(im)


def film_texture(f, t, seed):
    rng = np.random.default_rng(int(t * FPS) * 31 + seed)
    f = f * (1 + rng.uniform(-0.03, 0.03))
    sweep = (t * 0.35 + seed * 0.17) % 1.6 - 0.3
    x = np.arange(W, dtype=np.float32)
    leak = np.exp(-((x - sweep * W) ** 2) / (2 * 260 ** 2))[None, :, None] * 0.10
    f = 1 - (1 - f) * (1 - leak * np.array([1, 0.62, 0.32], np.float32))
    dx, dy = rng.uniform(-1.5, 1.5, 2)
    f = cv2.warpAffine(f, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    return np.clip(f * _VIG if _VIG is not None else f, 0, 1)


class Scene:
    def __init__(self, spec, base):
        self.s, self.e = spec["start"], spec["end"]
        self.mode = spec.get("mode", "photo")
        self.push = spec.get("push", [1.04, 1.14] if self.mode == "photo" else [1.0, 1.14])
        self.drift = spec.get("drift", [0, -30])
        self.fg_extra = spec.get("fg_extra", 0.05)
        self.seed = int(self.s * 100)
        if self.mode == "photo" and spec.get("fg"):
            self.bg = to_f(load_rgba(base / spec["bg"], (W, H))[..., :3])
            self.fg = load_rgba(base / spec["fg"], (W, H))
        else:
            self.bg = to_f(load_rgba(base / spec["image"], (W, H))[..., :3])
            self.fg = None

    def active(self, t):
        return self.s <= t < self.e

    def frame(self, t):
        p = prog(t, self.s, self.e)
        z = self.push[0] + (self.push[1] - self.push[0]) * p
        dx, dy = self.drift[0] * p, self.drift[1] * p
        if self.fg is None:
            f = zoom(self.bg, z)
        else:
            f = zoom(self.bg, z, shift=(dx * 0.6, dy * 0.6))
            fg = cv2.warpAffine(self.fg, np.float32([[1, 0, 0], [0, 1, 0]]), (W, H))
            zf = z + self.fg_extra * p
            fgw = cv2.warpAffine(fg, np.float32([[zf, 0, W / 2 * (1 - zf) + dx * 1.4],
                                                 [0, zf, H / 2 * (1 - zf) + dy * 1.4]]), (W, H),
                                 borderValue=(0, 0, 0, 0)).astype(np.float32) / 255
            f = f * (1 - fgw[..., 3:4]) + fgw[..., :3] * fgw[..., 3:4]
        f = editorial(f)  # grade, grain and bloom stay on overlays in every mode
        return film_texture(f, t, self.seed)


# ---------------------------------------------------------------- renderer
class Reel:
    def __init__(self, plan_path):
        self.plan_path = pathlib.Path(plan_path).resolve()
        self.p = json.loads(self.plan_path.read_text(encoding="utf-8"))
        self.base = self.plan_path.parent.parent if self.plan_path.parent.name == "work" else self.plan_path.parent
        self.raw = self.base / self.p["raw"]
        self.dur = probe_duration(self.raw)
        self.card = tuple(self.p["card"])
        self.hook_scene = tuple(self.p["hook_scene"])
        self.tear = tuple(self.p["tear"])
        self.grade = bool(self.p.get("doctor_grade", False))

    # ---- lazy assets (built once per process)
    def build(self):
        p = self.p
        self.bp = blueprint_bg()
        self.sticker = treat_sticker(self.base / p["hook_sticker"]) if p.get("hook_sticker") else None
        self.qs = [question_sprite(sz) for sz in (120, 140, 120, 140)]
        self.caps = [(c["s"], c["e"], hook_caption(c["top"], c["keyword"])) for c in p["hook_caps"]]
        self.scenes = [Scene(s, self.base) for s in p.get("scenes", [])]
        words = json.loads((self.base / p["words"]).read_text(encoding="utf-8"))
        self.subs = [(g["s"], g["e"], sub_plain(g["text"]), sub_boxed(g["text"]))
                     for g in group_words(words, self.card[1])]
        self.lt = lower_third(p.get("lower_third", "Dr Rak, Men's Health Doctor"))
        self.scrim_spk = scrim_layer(1120)
        global _VIG
        _VIG = vignette_map(0.30)

    def speaker(self, t, f):
        f = to_f(f)
        if self.card[0] <= t < self.card[1]:
            return f  # never touch disclaimer-card frames
        if t < self.hook_scene[0]:
            z = 1.0 + 0.10 * ease_out_cubic(t / 1.2)
            f = zoom(f, z, anchor=(0.5, 0.22))
        elif t < self.card[0]:
            f = zoom(f, 1.06, anchor=(0.5, 0.22))
        if self.grade:
            f = editorial(f)
        return f

    def hook_frame(self, t):
        hs = self.hook_scene[0]
        lt = t - hs
        f = self.bp.copy()
        if self.sticker is not None:
            pin = ease_back(lt / 0.45)
            sc = max(0.01, pin) * (1 + 0.03 * prog(t, hs, self.hook_scene[1]))
            rot = 2 * math.sin(lt * 1.3)
            fy = 8 * math.sin(lt * 1.7)
            f = paste(f, self.sticker, 540, 700 + fy, alpha=clamp(lt / 0.1), scale=sc, rot=rot)
        for i, (d, (x, y)) in enumerate(zip((0.35, 0.55, 0.75, 0.95), ((150, 380), (930, 430), (140, 980), (940, 940)))):
            if lt >= d:
                q = ease_back((lt - d) / 0.3)
                f = paste(f, self.qs[i], x, y, alpha=clamp((lt - d) / 0.08), scale=max(0.01, q),
                          rot=4 * math.sin(lt * 2.2 + i))
        return editorial(f)

    def draw_caps(self, t, f, on_blueprint):
        for s, e, (top, key) in self.caps:
            if not (s <= t < min(e, self.card[0])):
                continue
            if not on_blueprint:
                f = f * self.scrim_spk
            lt = t - s
            a = ease_out_cubic(lt / 0.18)
            th, kh = top.shape[0], key.shape[0]
            cy = self.cap_cy(th, kh, on_blueprint)
            y0 = cy - (th + kh) / 2
            f = paste(f, top, 540, y0 + th / 2 + 12 * (1 - a), alpha=a)
            kp = ease_out_cubic((lt - 0.12) / 0.2)
            f = paste(f, key, 540, y0 + th + kh / 2, alpha=clamp((lt - 0.12) / 0.1), scale=1.12 - 0.12 * kp)
        return f

    def cap_cy(self, th, kh, on_blueprint):
        """Spec centre (1240 blueprint / 1120 speaker), moved up if the letters (not the 60 px
        glow padding) would pass the safe-area bottom."""
        cy = 1240 if on_blueprint else 1120
        bottom = cy + (th + kh) / 2 - 60
        return cy - max(0, bottom - SAFE[3])

    def draw_subs(self, t, f):
        boxed = any(sc.active(t) for sc in self.scenes)
        for s, e, plain, box in self.subs:
            if s <= t < e:
                img = box if boxed else plain
                a = ease_out_cubic((t - s) / 0.15)
                f = paste(f, img, 540, (1130 if boxed else 1150) + 8 * (1 - a), alpha=a)
        if self.card[1] <= t < self.card[1] + 4 and not boxed:  # only over the doctor, never over an overlay
            a = min(ease_out_cubic((t - self.card[1]) / 0.25), ease_out_cubic((self.card[1] + 4 - t) / 0.25))
            f = paste(f, self.lt, SAFE[0] + self.lt.shape[1] / 2, LT_Y, alpha=a)
        return f

    def frame(self, t, src):
        spk = self.speaker(t, src)
        hs, he = self.hook_scene
        if hs <= t < self.tear[1]:
            hook = self.hook_frame(t)
            if t < hs + 0.12:  # whip in
                p = (t - hs) / 0.12
                f = zoom_blur(spk, 0.08 * p) * (1 - p) + zoom_blur(hook, 0.08 * (1 - p)) * p
            else:
                f = hook
            if t >= self.tear[0]:
                m, band = torn_mask(prog(t, *self.tear))
                f = f * (1 - m) + spk * m
                f = f * (1 - band) + np.array(CREAM, np.float32) / 255 * band
                return self.draw_caps(t, f, on_blueprint=False)
            return self.draw_caps(t, f, on_blueprint=True)
        for sc in self.scenes:
            if sc.active(t):
                ov = sc.frame(t)
                d_in, d_out = t - sc.s, sc.e - t
                if d_in < 0.18 or d_out < 0.18:
                    p = min(d_in, d_out) / 0.18
                    ov = zoom_blur(spk, 0.08 * p) * (1 - p) + zoom_blur(ov, 0.08 * (1 - p)) * p
                return self.draw_subs(t, ov)
        if t < self.card[0]:
            return self.draw_caps(t, spk, on_blueprint=False)
        if t < self.card[1]:
            return spk
        return self.draw_subs(t, spk)


    # ---- s4 render parts
    def render_part(self, t0, t1, out):
        self.build()
        enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", *ENCODE, str(out)],
                               stdin=subprocess.PIPE)
        for t, src in read_frames(self.raw, t0, t1):
            enc.stdin.write(to_u8(self.frame(t, src)).tobytes())
        enc.stdin.close()
        if enc.wait():
            raise SystemExit(f"Encoder failed for part {out}")

    # ---- s5 audio
    def sfx_track(self, path, sr=48000):
        n = int(self.dur * sr) + sr
        tr = np.zeros(n, np.float32)
        rng = np.random.default_rng(11)

        def add(sig, at, gain):
            i = max(0, int(at * sr))
            j = min(n, i + len(sig))
            tr[i:j] += sig[:j - i] * gain

        L = int(0.42 * sr)
        wn = rng.normal(0, 1, L).astype(np.float32)
        wn = cv2.GaussianBlur(wn.reshape(1, -1), (0, 0), 6).ravel()  # low-pass
        env = np.sin(np.linspace(0, math.pi, L)) ** 2
        whoosh = wn / (np.abs(wn).max() + 1e-9) * env
        tear_n = rng.normal(0, 1, int(0.38 * sr)).astype(np.float32)
        tear = tear_n * np.abs(np.sin(np.linspace(0, 40, len(tear_n)))) * np.linspace(1, 0.3, len(tear_n))
        tear /= np.abs(tear).max() + 1e-9
        tp = np.linspace(0, 0.09, int(0.09 * sr))
        pop = np.sin(2 * math.pi * (320 * tp + (1400 - 320) / (2 * 0.09) * tp ** 2)) * np.exp(-tp * 40)
        hs = self.hook_scene[0]
        add(whoosh, hs - 0.12, 0.07)
        for sc in self.p.get("scenes", []):
            add(whoosh, sc["start"] - 0.12, 0.07)
        add(tear, self.tear[0], 0.09)
        for d in (0.35, 0.55, 0.75, 0.95):
            add(pop, hs + d, 0.035)
        pcm = (np.clip(tr, -1, 1) * 32767).astype(np.int16)
        path.write_bytes(pcm.tobytes())

    # ---- s4E end card
    def end_card(self, out, secs=5.0):
        brand = json.loads((REPO / "brands" / "ssclinic" / "brand.json").read_text(encoding="utf-8"))
        cols = brand.get("colors", {})
        navy = cols.get("deep_prussian_navy") or cols.get("navy") or "#022057"
        navy = tuple(int(navy.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        im = Image.new("RGB", (W, H), navy)
        logo = Image.open(find_logo(brand)).convert("RGBA")
        logo.thumbnail((640, 360), Image.LANCZOS)
        im.paste(logo, ((W - logo.width) // 2, 760 - logo.height // 2), logo)
        f = font("Poppins-SemiBold.ttf", 46)
        line = self.p.get("end_line", "Jumpa doktor untuk pemeriksaan jika ada simptom")
        d = ImageDraw.Draw(im)
        words, rows, cur = line.split(), [], ""
        for w in words:
            if cur and f.getlength(cur + " " + w) > 860:
                rows.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        rows.append(cur)
        for i, r in enumerate(rows):
            d.text(((W - f.getlength(r)) / 2, 1020 + i * 64), r, font=f, fill=(255, 255, 255))
        png = out.with_suffix(".png")
        im.save(png)
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(png), "-f", "lavfi", "-i",
             "anullsrc=r=48000:cl=stereo", "-t", f"{secs}", "-r", str(FPS),
             "-vf", "fade=in:0:9", *ENCODE, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
             "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)])

    # ---- full pipeline
    def render(self):
        name = self.p.get("name", self.raw.stem)
        rd, qd = self.base / "renders", self.base / "qa"
        rd.mkdir(exist_ok=True)
        qd.mkdir(exist_ok=True)
        cuts = self.p.get("parts") or [0, round(self.dur / 3, 2), round(self.dur * 2 / 3, 2)]
        cuts = [c for c in cuts if c < self.dur] + [self.dur]
        procs, parts = [], []
        for i, (a, b) in enumerate(zip(cuts[:-1], cuts[1:])):
            out = rd / f"{name}_part{i}.mp4"
            parts.append(out)
            if self.p.get("reuse_parts_from", 99) <= a and out.exists():
                continue  # partial revision: keep later parts
            procs.append(subprocess.Popen([sys.executable, __file__, "render-part", str(self.plan_path),
                                           f"{a}", f"{b}", str(out)], stdin=subprocess.DEVNULL,
                                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
        for p in procs:
            if p.wait():
                raise SystemExit("A render part failed; see the error above.")
        lst = rd / f"{name}_parts.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        video = rd / f"{name}_video.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)])
        sfx = rd / f"{name}_sfx.pcm"
        self.sfx_track(sfx)
        card = rd / f"{name}_endcard.mp4"
        self.end_card(card)
        final = rd / f"{name}_final.mp4"
        d = f"{self.dur:.3f}"
        fc = (f"[0:v]tpad=stop_mode=clone:stop_duration=1,trim=0:{d},setpts=PTS-STARTPTS,fps={FPS}[v0];"
              f"[1:a]aresample=48000,atrim=0:{d},asetpts=PTS-STARTPTS[va];"
              f"[2:a]atrim=0:{d},asetpts=PTS-STARTPTS[sx];"
              f"[va][sx]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a0];"
              f"[3:v]scale={W}:{H},fps={FPS},setsar=1[v1];[3:a]aresample=48000[a1];"
              f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(self.raw),
             "-f", "s16le", "-ar", "48000", "-ac", "1", "-i", str(sfx), "-i", str(card),
             "-filter_complex", fc, "-map", "[v]", "-map", "[a]", *ENCODE,
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final)])
        return final, self.qa(final, qd, name)

    def write_timeline(self, final):
        """Layout record in the format scripts/check_layout.py reads (text elements only)."""
        self.build_text_only()
        ov = []
        for i, (s, e, (top, key)) in enumerate(self.caps):
            th, kh = top.shape[0], key.shape[0]
            w = max(top.shape[1], key.shape[1]) - 120
            for blue, (a, b) in ((True, (max(s, self.hook_scene[0]), min(e, self.tear[0]))),
                                 (False, (s, min(e, self.card[0])))):
                if b > a:
                    cy = self.cap_cy(th, kh, blue)
                    hgt = th + kh - 120
                    ov.append({"name": f"hook_cap_{i}.png", "x": 540 - w / 2, "y": cy - hgt / 2,
                               "w": w, "h": hgt, "start": a, "end": b})
        lw, lh = self.lt.shape[1], self.lt.shape[0]
        ov.append({"name": "lower_third.png", "x": SAFE[0], "y": LT_Y - lh / 2, "w": lw, "h": lh,
                   "start": self.card[1], "end": self.card[1] + 4})
        bw = max((max(pl.shape[1] - 60, bx.shape[1]) for _, _, pl, bx in self.subs), default=600)
        band = [540 - bw / 2, 1130 - 60, 540 + bw / 2, 1150 + 60]
        total = probe_duration(final)
        tl = {"file": final.name, "size": [W, H], "total": round(total, 3),
              "items": [{"src": str(self.raw), "mode": "wide", "out_start": 0.0, "dur": self.dur, "src_start": 0.0}],
              "layout": {"safe": list(SAFE), "overlays": ov, "caption_band": band,
                         "captions_hidden": [list(self.card), [self.dur, total]]}}
        p = final.with_name(final.stem + ".timeline.json")
        p.write_text(json.dumps(tl, indent=2), encoding="utf-8")
        return p

    def build_text_only(self):
        if not hasattr(self, "caps"):
            self.caps = [(c["s"], c["e"], hook_caption(c["top"], c["keyword"])) for c in self.p["hook_caps"]]
            words = json.loads((self.base / self.p["words"]).read_text(encoding="utf-8"))
            self.subs = [(g["s"], g["e"], sub_plain(g["text"]), sub_boxed(g["text"]))
                         for g in group_words(words, self.card[1])]
            self.lt = lower_third(self.p.get("lower_third", "Dr Rak, Men's Health Doctor"))

    # ---- s6 QA (reports what actually ran; never claims an unrun check)
    def qa(self, final, qd, name):
        res = {}
        tl = self.write_timeline(final)
        ft = self.base / "work" / f"facetrack_{name}.json"
        if not ft.exists() and (REPO / "scripts" / "face_track.py").exists():
            subprocess.run([sys.executable, str(REPO / "scripts" / "face_track.py"), str(self.raw), str(ft)],
                           capture_output=True, stdin=subprocess.DEVNULL)
        lay_args = [str(tl)] + (["--facetrack", str(ft)] if ft.exists() else [])
        for script, args in (("check_sync.py", [str(final), str(self.raw)]), ("check_layout.py", lay_args)):
            sp = REPO / "scripts" / script
            if not sp.exists():
                res[script] = "NOT RUN (script missing)"
                continue
            r = subprocess.run([sys.executable, str(sp), *args], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL)
            res[script] = ("PASS" if r.returncode == 0 else "FAIL") + ": " + (r.stdout + r.stderr).strip()[-400:]
        grid = qd / f"{name}_grid.jpg"
        n = int(probe_duration(final) // 3) + 1
        cols = 6
        run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-vf",
             f"fps=1/3,scale=270:480,tile={cols}x{math.ceil(n / cols)}", "-frames:v", "1", str(grid)])
        res["frame_grid"] = str(grid)
        cap = self.p["hook_caps"][0] if self.p.get("hook_caps") else None
        if cap:
            crop = qd / f"{name}_hookcap_crop.png"
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{cap['s'] + 0.5:.2f}", "-i", str(final), "-frames:v", "1",
                 "-vf", "crop=1080:600:0:900", str(crop)])
            res["hook_caption_crop"] = str(crop)
        (qd / f"{name}_qa.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        return res


# ---------------------------------------------------------------- CLI
PLAN_EXAMPLE = {
    "name": "SSC_DR09",
    "raw": "raw/clip9.mp4",
    "words": "work/clip9_words.json",
    "card": [3.8, 5.667],
    "hook_scene": [1.067, 3.05],
    "tear": [3.05, 3.42],
    "hook_sticker": "work/layers/hook_calm_sticker.png",
    "hook_caps": [
        {"s": 0.0, "e": 1.6, "top": "<top line, real speech>", "keyword": "<KEYWORD>"},
        {"s": 1.6, "e": 3.8, "top": "<top line>", "keyword": "<KEYWORD>"}],
    "scenes": [
        {"start": 9.2, "end": 12.4, "mode": "photo", "fg": "work/layers/s1_fg.png", "bg": "work/layers/s1_bg.png",
         "push": [1.04, 1.16], "drift": [0, -30], "fg_extra": 0.05},
        {"start": 20.0, "end": 22.5, "mode": "flat", "image": "work/stock/artery.png", "push": [1.0, 1.14]}],
    "doctor_grade": False,
    "lower_third": "Dr Rak, Men's Health Doctor",
    "end_line": "Jumpa doktor untuk pemeriksaan jika ada simptom",
    "parts": [0, 24, 48],
    "reuse_parts_from": 99,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("detect-card"); a.add_argument("raw")
    a = sub.add_parser("words"); a.add_argument("raw"); a.add_argument("chunks"); a.add_argument("--card", nargs=2, type=float)
    a.add_argument("--out")
    a = sub.add_parser("prep-layers"); a.add_argument("image"); a.add_argument("outdir")
    a.add_argument("--sticker", action="store_true"); a.add_argument("--object", action="store_true")
    a = sub.add_parser("render"); a.add_argument("plan")
    a = sub.add_parser("render-part"); a.add_argument("plan"); a.add_argument("t0", type=float)
    a.add_argument("t1", type=float); a.add_argument("out")
    sub.add_parser("plan-example")
    x = ap.parse_args()
    if x.cmd == "detect-card":
        print(json.dumps({"card": detect_card(x.raw)}))
    elif x.cmd == "words":
        words = words_from_chunks(x.raw, json.loads(pathlib.Path(x.chunks).read_text(encoding="utf-8")), x.card)
        s = json.dumps(words, ensure_ascii=False, indent=1)
        pathlib.Path(x.out).write_text(s, encoding="utf-8") if x.out else print(s)
    elif x.cmd == "prep-layers":
        print(json.dumps(prep_layers(x.image, x.outdir, x.sticker, not x.object)))
    elif x.cmd == "render":
        final, qa = Reel(x.plan).render()
        print(json.dumps({"final": str(final), "qa": qa}, indent=2, ensure_ascii=False))
    elif x.cmd == "render-part":
        Reel(x.plan).render_part(x.t0, x.t1, pathlib.Path(x.out))
    elif x.cmd == "plan-example":
        print(json.dumps(PLAN_EXAMPLE, indent=2))


if __name__ == "__main__":
    main()
