#!/usr/bin/env python3
"""SuamiSihat logo intro ("ta-dum" sting, Netflix style) for Masterclass videos only.

render_masterclass.py calls prepend(..., in_place=True) on every render; this CLI is for re-runs and tests.
Never use it on Reels ads, statics or doctor reels.

Usage:
  render_intro.py build [--size 1920x1080] [--fps 25] [--sheet]
      One intro mp4, cached in batches/_cache/intro/. --sheet also writes a contact sheet to review.
  render_intro.py prepend <final.mp4> [...] [--in-place | --suffix _intro --out-dir DIR]
      Builds an intro matching each file (size, fps) and puts it in front. <stem>.timeline.json, .srt and .vtt
      are shifted by the intro length, so check_sync.py --timeline still works. Files that already have the
      intro (timeline "intro" key) are skipped. Run sync-qa on every result before delivery.
  render_intro.py --selftest

Logo: the official SVG from the SuamiSihat Design System (logo_suamisihat_primary_dark.svg), never retyped.
Its three paths (wordmark, white S, blue arc) animate separately on the same pixel grid; shapes and colours
are never changed and the hold frame is the exact lockup. No blur, shadow, outline, rotation or recolour
(see the Design System "logo don'ts"). Sound is synthesised here, so no licensed sting is needed.
"""
import argparse, hashlib, json, math, pathlib, re, shutil, subprocess, sys, tempfile, wave
from fractions import Fraction
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "batches" / "_cache" / "intro"
SR = 48000
T = 3.0                 # intro length in seconds (rounded to whole frames)
TA, TD = 0.20, 0.95     # "ta" = mark appears, "dum" = bloom + lockup slides open
SLIDE, FADE = 0.65, 0.5
GLOW_RGB = np.array([109, 198, 236], np.float32) / 255  # #6dc6ec, the logo's own light blue
LOUDNESS = -16.0        # LUFS for the sting (finals are loudnormed to about -14)
PAD = 6
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_config():
    cfg = {}
    for name in ("config.env", "config.example.env"):
        p = ROOT / name
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    cfg.setdefault(k.strip(), v.strip())
    return cfg


def find_logo(override=None, variant="primary_dark"):
    if override:
        p = pathlib.Path(override)
        if not p.exists():
            sys.exit(f"BLOCK logo not found: {p}")
        return p
    name = f"logo_suamisihat_{variant}.svg"
    roots = [ROOT / "brands" / "suamisihat" / "design-system" / "logos"]
    ds = load_config().get("DESIGN_SYSTEM_ROOT")
    for base in ([pathlib.Path(ds)] if ds else []) + [ROOT.parent / "ss-assets"]:
        roots += [base / "static" / "public" / "brand" / "logos" / "00_logo_suamisihat",
                  base / "static" / "public" / "brand" / "logos"]
    for r in roots:
        if (r / name).exists():
            return r / name
    sys.exit(f"BLOCK {name} not found (DESIGN_SYSTEM_ROOT or ../ss-assets). Never retype the logo; pass --logo.")


# ---------- rasterise (headless Edge/Chrome, same grid for every part) ----------
def find_browser():
    sys.path.insert(0, str(ROOT / "scripts"))
    from render_static import find_browser as fb
    return fb()


def screenshot(svg_text, width, br):
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "l.svg").write_text(svg_text, encoding="utf-8")
    page = tmp / "l.html"
    page.write_text(f'<html><body style="margin:0;background:transparent"><img src="{(tmp / "l.svg").as_uri()}" '
                    f'style="width:{width}px;display:block"></body></html>', encoding="utf-8")
    shot = tmp / "s.png"
    subprocess.run([br, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--default-background-color=00000000", f"--window-size={width + 40},{width + 40}",
                    f"--screenshot={shot}", page.as_uri()], capture_output=True, timeout=90)
    if not shot.exists():
        sys.exit("BLOCK could not rasterise the logo SVG (headless Edge/Chrome failed)")
    im = Image.open(shot).convert("RGBA")
    im.load()
    shutil.rmtree(tmp, ignore_errors=True)
    return im


def logo_layers(svg, width):
    """Full lockup size plus each path as (name, RGBA crop, (x, y) in lockup pixels). Cached per SVG + width."""
    src = svg.read_bytes()
    cdir = CACHE / f"layers_{hashlib.sha1(src + str(width).encode()).hexdigest()[:12]}"
    meta = cdir / "layers.json"
    if meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        return tuple(m["size"]), [(p["name"], Image.open(cdir / f"{p['name']}.png").convert("RGBA"), tuple(p["xy"]))
                                  for p in m["parts"]]
    text = src.decode("utf-8")
    paths = list(re.finditer(r"<path\b[^>]*/>", text))
    if len(paths) != 3 or "<g" in text or "transform=" in text:
        sys.exit(f"BLOCK unexpected SVG structure in {svg.name} ({len(paths)} paths; expected wordmark + 2 mark paths)")
    br = find_browser()
    if not br:
        sys.exit("BLOCK no Edge/Chrome to rasterise the logo SVG")
    full = screenshot(text, width, br)
    bb = full.getchannel("A").getbbox()
    full = full.crop(bb)
    head = text[:paths[0].start()]
    raw = [screenshot(head + p.group(0) + "</svg>", width, br).crop(bb) for p in paths]
    boxes = [im.getchannel("A").getbbox() for im in raw]
    word = max(range(3), key=lambda i: boxes[i][0])
    marks = [i for i in range(3) if i != word]  # document order: white S, then blue arc
    names = {word: "word", marks[0]: "mark_a", marks[1]: "mark_b"}
    comp = Image.new("RGBA", full.size)
    for im in raw:
        comp.alpha_composite(im)
    diff = np.abs(np.asarray(comp, np.int16)[..., 3] - np.asarray(full, np.int16)[..., 3]).mean()
    if diff > 1.0:
        sys.exit(f"BLOCK logo parts do not rebuild the lockup (alpha diff {diff:.2f})")
    cdir.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, im in enumerate(raw):
        x0, y0, x1, y1 = boxes[i]
        crop = im.crop((x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD))
        crop.save(cdir / f"{names[i]}.png")
        parts.append((names[i], crop, (x0 - PAD, y0 - PAD)))
    meta.write_text(json.dumps({"svg": str(svg), "size": list(full.size),
                                "parts": [{"name": n, "xy": list(xy)} for n, _, xy in parts]}), encoding="utf-8")
    return full.size, parts


# ---------- animation ----------
def ramp(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)

def ease_out_cubic(x):
    return 1 - (1 - x) ** 3

def ease_in_out_cubic(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def ease_out_back(x, s=1.2):
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


class Intro:
    """0.20 s mark punches in (white S, then blue arc) | 0.95 s bloom, lockup slides open while the wordmark
    wipes in | slow push-in on the full lockup | fade to black for the cut into the video."""

    def __init__(self, W, H, fps, svg):
        self.W, self.H, self.fps = W, H, Fraction(fps)
        self.n = max(1, round(T * self.fps))
        self.dur = float(self.n / self.fps)
        self.LW = W * (0.50 if W / H > 1.2 else 0.72)
        (self.SW, self.SH), parts = logo_layers(svg, int(math.ceil(self.LW * 1.75)))
        self.k0 = self.LW / self.SW
        self.parts, inner = {}, {}
        for name, im, (ox, oy) in parts:
            self.parts[name] = (im.convert("RGBa"), ox, oy)
            x0, y0, x1, y1 = im.getchannel("A").getbbox()
            inner[name] = (ox + x0, oy + y0, ox + x1, oy + y1)
        mb = [inner["mark_a"], inner["mark_b"]]
        self.M = ((min(b[0] for b in mb) + max(b[2] for b in mb)) / 2, (min(b[1] for b in mb) + max(b[3] for b in mb)) / 2)
        self.word_x = (inner["word"][0], inner["word"][2])
        self.dx0 = -(self.M[0] - self.SW / 2) * self.k0   # start with the mark alone in the centre
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        sig = 0.9 * self.SH * self.k0
        self.glow = np.exp(-((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / (2 * sig * sig))[..., None]

    def draw(self, img, name, sp, op, g, dx, wipe=None):
        if op <= 0.002:
            return
        im, ox, oy = self.parts[name]
        a = g * self.k0 * sp
        bx = self.W / 2 + g * self.k0 * ((1 - sp) * self.M[0] - self.SW / 2) + g * dx
        by = self.H / 2 + g * self.k0 * ((1 - sp) * self.M[1] - self.SH / 2)
        X0, Y0 = a * ox + bx, a * oy + by
        # whole-pixel target inside the layer (the dropped edge is transparent padding) keeps sub-pixel motion exact
        ix0, iy0 = max(0, math.ceil(X0)), max(0, math.ceil(Y0))
        ix1, iy1 = min(self.W, math.floor(X0 + a * im.width)), min(self.H, math.floor(Y0 + a * im.height))
        if ix1 <= ix0 or iy1 <= iy0:
            return
        box = ((ix0 - X0) / a, (iy0 - Y0) / a, (ix1 - X0) / a, (iy1 - Y0) / a)
        p = np.asarray(im.resize((ix1 - ix0, iy1 - iy0), Image.LANCZOS, box=box), np.float32) / 255  # premultiplied
        f = np.full((1, ix1 - ix0, 1), op, np.float32)
        if wipe is not None:
            wl, wr = (a * self.word_x[0] + bx, a * self.word_x[1] + bx)
            soft = 0.12 * self.LW * g
            edge = wl + (wr - wl + soft) * wipe
            xs = np.arange(ix0, ix1, dtype=np.float32) + 0.5
            f *= np.clip((edge - xs) / soft, 0, 1)[None, :, None]
        reg = img[iy0:iy1, ix0:ix1]
        reg *= 1 - p[..., 3:4] * f
        reg += p[..., :3] * f

    def frame(self, i):
        t = i / float(self.fps)
        g = 1 + 0.05 * (t / self.dur) ** 1.5
        dx = self.dx0 * (1 - ease_in_out_cubic(ramp(t, TD, TD + SLIDE)))
        ga = 0.30 * ramp(t, TD - 0.04, TD + 0.02) * math.exp(-max(0.0, t - TD - 0.02) / 0.45)
        img = self.glow * (ga * GLOW_RGB) if ga > 0.002 else np.zeros((self.H, self.W, 3), np.float32)
        self.draw(img, "mark_a", 1.6 - 0.6 * ease_out_back(ramp(t, TA, TA + 0.6)), ramp(t, TA, TA + 0.22), g, dx)
        self.draw(img, "mark_b", 1.9 - 0.9 * ease_out_back(ramp(t, TA + 0.12, TA + 0.72)), ramp(t, TA + 0.12, TA + 0.34), g, dx)
        self.draw(img, "word", 1.0, ramp(t, TD + 0.05, TD + 0.35), g, dx, wipe=ease_out_cubic(ramp(t, TD + 0.05, TD + SLIDE + 0.1)))
        img *= 1 - ramp(t, self.dur - FADE, self.dur) ** 2
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------- sound: soft knock ("ta"), riser, deep boom + chord ("dum") ----------
def synth_audio(n):
    from scipy.signal import butter, lfilter
    out = np.zeros((n, 2), np.float64)
    rng = np.random.default_rng(7)

    def add(t0, dur, fn):
        i0 = int(round(t0 * SR)); m = min(n - i0, int(dur * SR))
        if m > 0:
            s = fn(np.arange(m) / SR)
            out[i0:i0 + m] += s if s.ndim == 2 else np.stack([s, s], 1)

    def sweep(f0, f1, tau, tt):
        return 2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-tt / tau)) / SR

    def att(tt, a):
        return 1 - np.exp(-tt / a)

    add(TA, 0.6, lambda tt: 0.55 * np.sin(sweep(150, 70, 0.04, tt)) * np.exp(-tt / 0.09) * att(tt, 0.002)
        + 0.06 * rng.standard_normal(len(tt)) * np.exp(-tt / 0.006))
    rs = TA + 0.35
    b, a = butter(2, [300 / (SR / 2), 3000 / (SR / 2)], btype="band")
    add(rs, TD - rs, lambda tt: lfilter(b, a, rng.standard_normal((len(tt), 2)), axis=0)
        * (0.10 * (tt / (TD - rs)) ** 2 * np.minimum(1, (TD - rs - tt) / 0.01))[:, None])

    def dum(tt):
        sub = 0.9 * np.sin(sweep(80, 42, 0.12, tt)) * np.exp(-tt / 0.75) * att(tt, 0.004)
        s = np.stack([sub, sub], 1)
        for f, amp in ((110, .22), (164.81, .16), (220, .14), (329.63, .08), (440, .05)):
            e = amp * att(tt, 0.03) * np.exp(-tt / 1.1)
            s += np.stack([np.sin(2 * np.pi * (f + 0.4) * tt) * e, np.sin(2 * np.pi * (f - 0.4) * tt) * e], 1)
        for f, amp in ((1760, .025), (2637, .015)):
            s += (amp * np.sin(2 * np.pi * f * tt) * att(tt, 0.01) * np.exp(-tt / 0.5))[:, None]
        s += (0.12 * rng.standard_normal(len(tt)) * np.exp(-tt / 0.01))[:, None]
        return s
    add(TD, T, dum)
    k = int(FADE * SR)
    out[-k:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k)))[:, None]
    return out / max(1e-9, np.abs(out).max()) * 0.7


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


# ---------- build ----------
def build(W, H, fps, logo=None, sheet=False):
    """Return (intro mp4, exact duration). Re-renders only when the logo, this script, size or fps change."""
    svg = find_logo(logo)
    fps = Fraction(fps).limit_denominator(1001)
    key = hashlib.sha1(svg.read_bytes() + pathlib.Path(__file__).read_bytes() + f"{W}x{H}@{fps}".encode()).hexdigest()[:10]
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"suamisihat_intro_{W}x{H}_{str(fps).replace('/', '-')}fps_{key}.mp4"
    sheet_path = out.with_name(out.stem + "_sheet.jpg")
    dur = float(round(T * fps) / fps)
    if out.exists() and (not sheet or sheet_path.exists()):
        return out, dur
    it = Intro(W, H, fps, svg)
    tmp = pathlib.Path(tempfile.mkdtemp())
    audio = synth_audio(int(round(it.dur * SR)))
    write_wav(tmp / "a.wav", audio)
    lu = loudness(tmp / "a.wav")
    if lu is not None:
        gain = min(10 ** ((LOUDNESS - lu) / 20), 0.89 / np.abs(audio).max())  # peak <= -1 dBFS
        write_wav(tmp / "a.wav", audio * gain)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-i", str(tmp / "a.wav"), "-map", "0:v", "-map", "1:a",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
           "-crf", "16", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", str(fps),
           "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "2", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    picks = {round(x * (it.n - 1)) for x in (0.08, 0.15, 0.25, 0.33, 0.4, 0.5, 0.7, 0.9)} if sheet else set()
    thumbs = []
    for i in range(it.n):
        fr = it.frame(i)
        proc.stdin.write(fr.tobytes())
        if i in picks:
            im = Image.fromarray(fr); im.thumbnail((480, 480)); thumbs.append(im)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit(f"FAIL ffmpeg could not encode {out.name}")
    shutil.rmtree(tmp, ignore_errors=True)
    if thumbs:
        tw, th = thumbs[0].size
        cols = 4
        rows = math.ceil(len(thumbs) / cols)
        sh = Image.new("RGB", (cols * tw + (cols + 1) * 8, rows * th + (rows + 1) * 8), (60, 60, 60))
        for k, im in enumerate(thumbs):
            sh.paste(im, (8 + (k % cols) * (tw + 8), 8 + (k // cols) * (th + 8)))
        sh.save(sheet_path, quality=90)
    lu_txt = f", sting {LOUDNESS:.0f} LUFS" if lu is not None else ""
    print(f"OK intro {out.name}: {W}x{H} @ {fps} fps, {it.n} frames ({dur:.3f}s){lu_txt}" + (f", sheet {sheet_path.name}" if thumbs else ""))
    return out, dur


# ---------- prepend ----------
def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), None)
    if not v:
        sys.exit(f"FAIL {p}: no video stream")
    has_a = any(s["codec_type"] == "audio" for s in j["streams"])
    return int(v["width"]), int(v["height"]), Fraction(v["r_frame_rate"]), has_a, float(j["format"]["duration"])


def shift_timeline(src, dst, d, new_file, intro):
    j = json.loads(src.read_text(encoding="utf-8"))
    sh = lambda x: round(x + d, 3)
    for it in j.get("items", []) + j.get("broll_cuts", []):
        if "out_start" in it:
            it["out_start"] = sh(it["out_start"])
    lay = j.get("layout") if isinstance(j.get("layout"), dict) else {}
    for ov in lay.get("overlays") or []:
        for k in ("start", "end"):
            if k in ov:
                ov[k] = sh(ov[k])
    if lay.get("captions_hidden"):
        hid = []
        for h in lay["captions_hidden"]:
            if isinstance(h, dict):
                h = {k: sh(v) if k in ("start", "end") else v for k, v in h.items()}
            elif isinstance(h, list):
                h = [sh(x) if isinstance(x, (int, float)) else x for x in h]
            hid.append(h)
        lay["captions_hidden"] = hid
    for v in j.get("vo", []):
        for k in ("start", "shot_end"):
            if k in v:
                v[k] = sh(v[k])
    if "total" in j:
        j["total"] = sh(j["total"])
    j["file"] = new_file
    j.setdefault("items", []).insert(0, {"type": "card", "name": "intro", "out_start": 0.0, "dur": round(d, 3)})
    j["intro"] = {"file": intro.name, "dur": round(d, 6)}
    dst.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")


def shift_subs(src, dst, d):
    """Move every SRT/VTT cue time later by d seconds."""
    def rep(m):
        ms = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))) * 1000 + int(m.group(5)) + round(d * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{m.group(4)}{ms % 1000:03d}"
    text = src.read_text(encoding="utf-8")
    dst.write_text(re.sub(r"(\d{2}):(\d{2}):(\d{2})([,.])(\d{3})", rep, text), encoding="utf-8")


def prepend(video, suffix="_intro", out_dir=None, logo=None, in_place=False):
    """Intro + video. in_place replaces the video, its timeline and .srt/.vtt (Masterclass renders)."""
    video = pathlib.Path(video)
    tl = video.with_name(video.stem + ".timeline.json")
    if tl.exists() and "intro" in json.loads(tl.read_text(encoding="utf-8")):
        print(f"SKIP {video.name}: already has the intro")
        return video
    W, H, fps, has_a, vdur = probe(video)
    intro, d = build(W, H, fps, logo)
    if in_place:
        out = video.with_name(video.stem + ".intro_tmp.mp4")
    else:
        od = pathlib.Path(out_dir) if out_dir else video.parent
        od.mkdir(parents=True, exist_ok=True)
        out = od / f"{video.stem}{suffix}.mp4"
        if out.resolve() == video.resolve():
            sys.exit(f"FAIL {out.name}: output would overwrite the input (use --in-place)")
    af = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(intro), "-i", str(video)]
    if not has_a:
        cmd += ["-f", "lavfi", "-t", f"{vdur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    fc = (f"[0:v]trim=0:{d:.6f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v0];"
          f"[0:a]{af},apad=whole_dur={d:.6f},atrim=0:{d:.6f},asetpts=PTS-STARTPTS[a0];"
          f"[1:v]fps={fps},setsar=1,format=yuv420p[v1];[{1 if has_a else 2}:a]{af}[a1];"
          f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"FAIL ffmpeg could not prepend the intro to {video.name}")
    note = "no timeline.json (sync-qa needs one)"
    if in_place:
        if tl.exists():
            shift_timeline(tl, tl, d, video.name, intro)
            note = f"timeline shifted +{d:.3f}s"
        for ext in (".srt", ".vtt"):
            sub = video.with_suffix(ext)
            if sub.exists():
                shift_subs(sub, sub, d)
                note += f", {ext[1:]} shifted"
        out.replace(video)
        out = video
    elif tl.exists():
        shift_timeline(tl, out.with_name(out.stem + ".timeline.json"), d, out.name, intro)
        for ext in (".srt", ".vtt"):
            if video.with_suffix(ext).exists():
                shift_subs(video.with_suffix(ext), out.with_suffix(ext), d)
        note = f"timeline shifted +{d:.3f}s"
    print(f"OK {out.name}: intro {d:.3f}s + {vdur:.2f}s, {note}")
    return out


# ---------- selftest: synthetic clip -> prepend -> check_sync on the shifted timeline ----------
def selftest():
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_sync
    tmp = pathlib.Path(tempfile.mkdtemp())
    raw = tmp / "raw.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=8",
                    "-f", "lavfi", "-i", "anoisesrc=d=8:c=pink:r=48000:a=0.3,volume='if(lt(mod(t,0.7),0.12),1,0.15)':eval=frame",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(raw)], check=True)
    final = tmp / "final.mp4"
    shutil.copy(raw, final)
    (tmp / "final.timeline.json").write_text(json.dumps({"file": "final.mp4", "size": [1080, 1920], "total": 8.0,
        "items": [{"type": "clip", "src": str(raw), "src_start": 1.0, "out_start": 1.0, "dur": 6.0}],
        "layout": {"overlays": [{"start": 1.0, "end": 3.0}], "captions_hidden": [[2.0, 2.5]]}}), encoding="utf-8")
    (tmp / "final.srt").write_text("1\n00:00:01,000 --> 00:00:02,500\nUji\n", encoding="utf-8")
    out = prepend(final, in_place=True)
    prepend(final, in_place=True)  # second run must skip, not stack a second intro
    tl = out.with_name(out.stem + ".timeline.json")
    j = json.loads(tl.read_text(encoding="utf-8"))
    d = j["intro"]["dur"]
    ok = abs(probe(out)[4] - (8.0 + d)) < 0.1 and abs(j["items"][1]["out_start"] - (1.0 + d)) < 0.002
    ok = ok and "00:00:04,000 --> 00:00:05,500" in (tmp / "final.srt").read_text(encoding="utf-8")
    ok = check_sync.check_timeline(tl, 0.04, 1.0) and ok
    shutil.rmtree(tmp, ignore_errors=True)
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    ap = argparse.ArgumentParser(description="SuamiSihat logo intro")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--size", default="1920x1080")
    b.add_argument("--fps", default="25")
    b.add_argument("--sheet", action="store_true")
    b.add_argument("--logo")
    p = sub.add_parser("prepend")
    p.add_argument("videos", nargs="+")
    p.add_argument("--suffix", default="_intro")
    p.add_argument("--out-dir")
    p.add_argument("--in-place", action="store_true", help="replace the video, timeline and subtitles (Masterclass renders)")
    p.add_argument("--logo")
    a = ap.parse_args()
    if a.cmd == "build":
        W, H = (int(x) for x in a.size.lower().split("x"))
        build(W, H, a.fps, a.logo, sheet=a.sheet)
    else:
        for v in a.videos:
            prepend(v, a.suffix, a.out_dir, a.logo, a.in_place)


if __name__ == "__main__":
    main()
