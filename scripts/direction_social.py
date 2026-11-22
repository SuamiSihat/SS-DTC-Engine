#!/usr/bin/env python3
"""Social cut for direction videos: 9:16 full-bleed, Vox-style fast edit for TikTok / Instagram Reels.

Usage:
  direction_social.py batches/<batch>/work/social_spec.json [--preview] [--plan-only] [--ambience-stem]

Edit: hook (live clip, headline from frame 1 for the thumbstop, then a short rewind montage back to the start of the
route), steps cut on the music beat, hyperlapse drives (frame-blended, capped at max_speed, trimmed from the start
of the range), landmark callouts (freeze, flash, optional drop of the picture to clear the top UI band, spotlight box
and label), word-group captions with key words in the accent colour, synthesized SFX (no library files), end card.
Geometry: the 16:9 source is cropped to a 608x1080 strip around "cx" (0-1 of the source width) and scaled to
1080x1920; callout boxes are given in source fractions [x0, y0, x1, y1].

--preview writes work/social_preview.jpg (look check) and work/social_preview_safe.jpg (with the safe area) using
estimated VO timing: no TTS calls and no video render.
Writes renders/<stem>_9x16.mp4 and <stem>_9x16_nomusic.mp4 + .timeline.json (check_sync.py, check_layout.py).
"""
import argparse, io, json, math, pathlib, re, subprocess, sys
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import direction_gfx as G
import direction_segments as S
import render_direction as R

FPS = 30; W, H = 1080, 1920; SW, SH = 1920, 1080; CW = 608
SAFE = (120, 270, 960, 1248)
CAP_BOTTOM = 1240
run = R.run


def fq(x):
    return round(x * FPS) / FPS


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


# ---------------- geometry
def x0_of(cx):
    return int(round(min(max(cx * SW - CW / 2, 0), SW - CW)))


def zoom_at(it, tl):
    z0, z1 = it.get("zoom", (1.0, 1.08)); tf = max(it["live"], 0.04)
    z = z0 + (z1 - z0) * min(tl, tf) / tf
    if it["punch"]:
        z += 0.10 * max(0.0, 1 - tl / 0.2) ** 2
    return z


def zoom_expr(it):
    z0, z1 = it.get("zoom", (1.0, 1.08)); tf = max(it["live"], 0.04)
    e = f"{z0:.4f}+{z1 - z0:.4f}*min(t,{tf:.3f})/{tf:.3f}"
    return f"({e}+0.10*pow(max(0,1-t/0.2),2))" if it["punch"] else f"({e})"


def drop_px(it):
    return (it.get("callout") or {}).get("drop", 0)


def drop_at(it, tl):
    """Picture y offset at segment time tl: fixed offset_y plus the callout drop."""
    dr = drop_px(it)
    return it.get("offset_y", 0) + (dr * math.sin(math.pi / 2 * min(1.0, max(0.0, (tl - it["live"]) / 0.22))) if dr else 0.0)


def to_out(sx, sy, it, z, drop=0.0):
    ax, ay = it.get("anchor", (540, 960))
    ox = (sx * SW - x0_of(it.get("cx", 0.5))) * W / CW; oy = sy * H
    return (ox - ax) * z + ax, (oy - ay) * z + ay + it.get("offset_y", 0) + drop


# ---------------- graphics
def bg_social(out):
    """Navy canvas behind the picture. Only visible while a callout drops the picture down (top UI band)."""
    im = Image.new("RGBA", (W, H), G.NAVY + (255,)); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H; d.line((0, y, W, y), fill=tuple(int(G.NAVY[i] + (G.CNAVY[i] - G.NAVY[i]) * t * .55) for i in range(3)) + (255,))
    lg = Image.open(G.LOGO_DARK).convert("RGBA"); lg = lg.resize((int(lg.width * 78 / lg.height), 78), Image.LANCZOS)
    im.alpha_composite(lg, ((W - lg.width) // 2, 110))
    im.save(out)


def hook_png(top, key, out, cy):
    f1, l1 = G.fit(top, "Poppins-Bold.ttf", 62, 840, max_lines=1, min_size=40)
    f2, l2 = G.fit(key, "Poppins-Black.ttf", 116, 840, max_lines=1, min_size=60)
    pad = 30; h1, h2 = int(f1.size * 1.25), int(f2.size * 1.15)
    w, h = 840 + 2 * pad, h1 + h2 + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); sh = im.copy()
    for img, c1, c2, sc in ((sh, (0, 0, 0, 210), (0, 0, 0, 210), (0, 0, 0, 210)), (im, G.WHITE, G.GOLD, G.NAVY)):
        d = ImageDraw.Draw(img)
        d.text((w / 2, pad + h1 / 2), l1[0], font=f1, fill=c1, anchor="mm", stroke_width=10, stroke_fill=sc)
        d.text((w / 2, pad + h1 + h2 / 2), l2[0], font=f2, fill=c2, anchor="mm", stroke_width=11, stroke_fill=sc)
    sh = sh.filter(ImageFilter.GaussianBlur(14)); sh.alpha_composite(im); sh.save(out)
    x, y = (W - w) // 2, int(cy - h / 2)
    return x, y, (x + pad, y + pad, 840, h - 2 * pad)


def panel_png(it, nsteps, out):
    """Compact step panel: icon tile, 'LANGKAH n / N', head, route progress bar."""
    Wp, pad, tile = 840, 22, 116
    step = it.get("step"); fs = G.font("Poppins-SemiBold.ttf", 28)
    tw = Wp - tile - 3 * pad
    fh, hl = G.fit(it["head"], "Poppins-ExtraBold.ttf", 54, tw, max_lines=1, min_size=34)
    bar = 12 if step else 0
    text_h = (fs.size + 8 if step else 0) + int(fh.size * 1.2)
    Hp = 2 * pad + max(tile, text_h) + (bar + 16 if step else 0)
    im = Image.new("RGBA", (Wp, Hp), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, Wp - 1, Hp - 1), radius=28, fill=G.NAVY + (238,))
    d.rounded_rectangle((pad, pad, pad + tile, pad + tile), radius=22, fill=G.CNAVY + (255,))
    G.icon(d, it.get("icon", "pin"), (pad + 12, pad + 12, pad + tile - 12, pad + tile - 12))
    x = 2 * pad + tile; y = pad + max(0, (tile - text_h) // 2)
    if step:
        d.text((x, y), f"LANGKAH {step} / {nsteps}", font=fs, fill=G.GOLD); y += fs.size + 8
    d.text((x, y), hl[0], font=fh, fill=G.WHITE)
    if step:
        by = Hp - pad - bar; gap = 6; sw = (Wp - 2 * pad - gap * (nsteps - 1)) / nsteps
        for k in range(nsteps):
            x0 = pad + k * (sw + gap)
            d.rounded_rectangle((x0, by, x0 + sw, by + bar), radius=bar // 2,
                                fill=(G.GOLD + (255,)) if k < step else (255, 255, 255, 70))
    im.save(out)
    return Wp, Hp


def caption_png(words, keys, out):
    ks = {norm(k) for k in keys}; size = 70
    while True:
        f = G.font("Poppins-ExtraBold.ttf", size); sp = f.getlength(" ")
        tw = sum(f.getlength(w) for w in words) + sp * (len(words) - 1)
        if tw <= 790 or size <= 44:
            break
        size -= 2
    pad = 22; w, h = int(tw) + 2 * pad, int(size * 1.3) + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = pad
    for wd in words:
        d.text((x, h / 2), wd, font=f, fill=G.GOLD if norm(wd) in ks else G.WHITE, anchor="lm", stroke_width=9, stroke_fill=G.NAVY)
        x += f.getlength(wd) + sp
    im.save(out)
    return (W - w) // 2, CAP_BOTTOM - h, w, h


def label_png(text, out):
    f, l = G.fit(text, "Poppins-ExtraBold.ttf", 46, 780, max_lines=1, min_size=28)
    w, h = int(f.getlength(l[0])) + 56, int(f.size * 1.2) + 28
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=G.GOLD + (255,))
    d.text((w / 2, h / 2), l[0], font=f, fill=G.NAVY, anchor="mm")
    im.save(out)
    return w, h


def spotlight_png(box, out, grow=14):
    im = Image.new("RGBA", (W, H), (2, 12, 40, 150))
    r = (box[0] - grow, box[1] - grow, box[2] + grow, box[3] + grow)
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle(r, radius=26, fill=255)
    im.putalpha(ImageChops.subtract(im.getchannel("A"), m.filter(ImageFilter.GaussianBlur(3))))
    ImageDraw.Draw(im).rounded_rectangle(r, radius=26, outline=G.GOLD + (255,), width=8)
    im.save(out)
    return r


def flash_png(out):
    Image.new("RGBA", (W, H), (255, 255, 255, 120)).save(out)


def rewind_png(s=260):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=G.NAVY + (215,))
    for tip in (70, 130):
        d.polygon([(tip, s / 2), (tip + 60, s / 2 - 55), (tip + 60, s / 2 + 55)], fill=G.GOLD)
    return im


def groups(words, maxw=3, maxc=18):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= maxw or sum(len(x[2]) + 1 for x in cur) + len(w[2]) > maxc):
            out.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.,?!:;]$", w[2]):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    res = []
    for k, g in enumerate(out):
        nxt = out[k + 1][0][0] if k + 1 < len(out) else g[-1][1] + 0.3
        res.append((g[0][0], max(nxt, g[-1][1]), [x[2] for x in g]))
    return res


# ---------------- plan
def plan(spec, vo):
    m = spec.get("music") or {}
    bp = 60.0 / m.get("bpm", 130); mst = m.get("start", 0.0); b0 = m.get("beat0", 0.0)

    def snap(e):  # next beat of the music bed at or after output time e
        return b0 + math.ceil((e + mst - b0) / bp - 1e-6) * bp - mst if m.get("bpm") else e

    shots = [dict(spec["hook"], _vo="hook", hook=True)] + [dict(s, _vo=f"vo_{i:02d}") for i, s in enumerate(spec["shots"])]
    t, items = 0.0, []
    for i, s in enumerate(shots):
        v = vo.get(s["_vo"]) if s.get("vo") else None
        hold = (s.get("callout") or {}).get("hold", 0.0); rw = (s.get("rewind") or {}).get("dur", 0.0)
        vo_at = s.get("vo_at", 0.08 if i == 0 else 0.12)
        need = max(s.get("min", 1.0), 0.5 + hold + rw, (vo_at + v["dur"] + 0.15) if v else 0.0)
        dur = fq(snap(t + need) - t)
        while dur < need - 1e-6:
            dur = fq(dur + 1 / FPS)
        live = round(dur - hold - rw, 4)
        a, b, pad = s["in"], s["out"], 0.0
        if s.get("speed"):
            sp = s["speed"]; b = min(a + live * sp, s.get("limit", a + live * sp)); pad = live - (b - a) / sp
        else:
            sp = (b - a) / live; mx = s.get("max_speed", spec.get("max_speed", 16))
            if sp > mx:
                a, sp = b - live * mx, mx
            elif sp < 1:
                sp, pad = 1.0, live - (b - a)
        it = dict(s)
        it.update({"idx": i, "in": round(a, 3), "out": round(b, 3), "out_start": round(t, 4), "dur": dur, "live": live,
                   "hold": hold, "rw": rw, "speed": round(sp, 4), "pad": round(max(pad, 0.0), 3), "vo": v, "vo_at": vo_at,
                   "punch": i > 0 and s.get("punch", True)})
        items.append(it); t = round(t + dur, 4)
    ec = spec["endcard"]; ev = vo.get("vo_end") if ec.get("vo") else None
    ed = fq(max(ec.get("plan", 4.5), (ev["dur"] + 1.0) if ev else 0.0))
    end = dict(idx="end", out_start=round(t, 4), dur=ed, vo=ev, vo_at=0.35)
    return items, end, round(t + ed, 4)


def estimate_vo(spec):
    """Preview only: VO length and word times estimated from the text (about 14 characters per second)."""
    def est(text):
        dur = 0.3 + len(text) / 14.0; ws = text.split(); tot = sum(len(w) + 1 for w in ws); t, out = 0.0, []
        for w in ws:
            l = dur * (len(w) + 1) / tot; out.append([t, t + l, w]); t += l
        return {"text": text, "dur": dur, "words": out, "mp3": None, "sents": []}
    vo = {"hook": est(spec["hook"]["vo"])}
    vo.update({f"vo_{i:02d}": est(s["vo"]) for i, s in enumerate(spec["shots"]) if s.get("vo")})
    if spec["endcard"].get("vo"):
        vo["vo_end"] = est(spec["endcard"]["vo"])
    return vo


def vo_lines(spec):
    lines = [("hook", spec["hook"]["vo"])] + [(f"vo_{i:02d}", s["vo"]) for i, s in enumerate(spec["shots"]) if s.get("vo")]
    return lines + ([("vo_end", spec["endcard"]["vo"])] if spec["endcard"].get("vo") else [])


# ---------------- layers (shared by render and preview)
def build_layers(it, wd, nsteps):
    """[(png, x, y, (t0, t1) or None, (name, (x, y, w, h)) or None)] in segment time; reg rect = what check_layout sees."""
    i, d = it["idx"], it["live"] + it["hold"]
    L, top = [], []
    co = it.get("callout")
    if co:
        tf = it["live"]; z = zoom_at(it, tf); dr = drop_px(it)
        bx0, by0 = to_out(co["box"][0], co["box"][1], it, z, dr); bx1, by1 = to_out(co["box"][2], co["box"][3], it, z, dr)
        box = tuple(int(v) for v in (bx0, by0, bx1, by1))
        sp = wd / f"spot_{i:02d}.png"; r = spotlight_png(box, sp)
        L.append((sp, 0, 0, (tf + 0.22, d), ("callout_box", (r[0] - 4, r[1] - 4, r[2] - r[0] + 8, r[3] - r[1] + 8))))
        lp = wd / f"label_{i:02d}.png"; lw, lh = label_png(co["label"], lp)
        lx = int(min(max((box[0] + box[2]) / 2 - lw / 2, SAFE[0]), SAFE[2] - lw))
        ly = r[3] + 24 if r[3] + 24 + lh <= SAFE[3] else r[1] - 24 - lh
        L.append((lp, lx, ly, (tf + 0.3, d), ("callout_label", (lx, ly, lw, lh))))
        fp = wd / "flash.png"
        if not fp.exists():
            flash_png(fp)
        top.append((fp, 0, 0, (tf, tf + 0.067), None))
    if it.get("hook"):
        p = wd / "hook.png"; x, y, reg = hook_png(it["top"], it["key"], p, it.get("text_cy", 1010))
        L.append((p, x, y, (0, it["live"]), ("hook_headline", reg)))
    else:
        if it.get("head"):
            p = wd / f"panel_{i:02d}.png"; w, h = panel_png(it, nsteps, p)
            L.append((p, 120, 284, (0, it["live"]) if co else None, ("panel", (120, 284, w, h))))
        if it.get("vo"):
            for k, (a, b, ws) in enumerate(groups(it["vo"]["words"])):
                a2, b2 = it["vo_at"] + a, min(d, it["vo_at"] + b)
                if b2 > a2:
                    p = wd / f"cap_{i:02d}_{k}.png"; x, y, w, h = caption_png(ws, it.get("keys", []), p)
                    L.append((p, x, y, (a2, b2), None))
    return L + top


# ---------------- frames
def grab(stab, t):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i", str(stab), "-frames:v", "1", "-f", "image2pipe",
                        "-c:v", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(b)).convert("RGB")


def frame_out(fr, it, z):
    x0 = x0_of(it.get("cx", 0.5)); im = fr.crop((x0, 0, x0 + CW, SH))
    zw, zh = 2 * int(W * z / 2), 2 * int(H * z / 2); im = im.resize((zw, zh), Image.LANCZOS)
    ax, ay = it.get("anchor", (540, 960)); cx, cy = int((zw - W) * ax / W), int((zh - H) * ay / H)
    return im.crop((cx, cy, cx + W, cy + H))


def compose(it, tl, stab, bg, layers):
    st = it["in"] + min(tl, it["live"] - it["pad"]) * it["speed"] if tl < it["live"] else it["out"] - 0.04
    cv = bg.copy(); cv.paste(frame_out(grab(stab, st), it, zoom_at(it, tl)), (0, int(drop_at(it, tl))))
    for p, x, y, en, _ in layers:
        if en is None or en[0] <= tl <= en[1]:
            cv.alpha_composite(Image.open(p).convert("RGBA"), (max(0, x), max(0, y)))
    return cv


def endcard_png(spec, stab, wd):
    still, ep = wd / "still.png", wd / "endcard.png"
    grab(stab, spec["endcard"]["still_at"]).save(still); G.endcard("9x16", spec["endcard"], still, ep)
    return ep


# ---------------- render
def render_seg(it, stab, bgp, layers, out):
    d = it["live"] + it["hold"]; ax, ay = it.get("anchor", (540, 960)); ze = zoom_expr(it)
    g = S.Graph(d)
    g.cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{it['in']:.3f}", "-t", f"{it['out'] - it['in']:.3f}", "-i", str(stab)]; g.n_in = 1
    b = g.input(bgp, loop=True)
    ch = f"[0:v]crop={CW}:{SH}:{x0_of(it.get('cx', 0.5))}:0,setpts=(PTS-STARTPTS)/{it['speed']}"
    if it["speed"] > 3:
        ch += f",tmix=frames={min(6, max(2, round(it['speed'] / 2.5)))}"
    ch += (f",fps={FPS},tpad=stop_mode=clone:stop_duration={it['pad'] + it['hold'] + 0.2:.3f},"
           f"scale=w='2*trunc({W}*{ze}/2)':h='2*trunc({H}*{ze}/2)':eval=frame:flags=bicubic,"
           f"crop={W}:{H}:x='(iw-{W})*{ax}/{W}':y='(ih-{H})*{ay}/{H}'")
    if it["punch"]:
        ch += ",gblur=sigma=14:enable='lt(t,0.067)',gblur=sigma=6:enable='between(t,0.067,0.134)'"
    ch += ",unsharp=5:5:0.5,format=rgba[vid]"
    dr = drop_px(it); off = it.get("offset_y", 0)
    yx = f"'{off}+{dr}*sin(PI/2*min(1,max(0,(t-{it['live']:.3f})/0.22)))'" if dr else str(off)
    g.fc += [ch, f"[{b}:v]format=rgba[bg]", f"[bg][vid]overlay=x=0:y={yx}[v0]"]; g.cur = "v0"
    for p, x, y, en, _ in layers:
        g.overlay(p, x, y, en)
    g.fc.append(f"[{g.cur}]format=yuv420p[out]")
    run(g.cmd + ["-filter_complex", ";".join(g.fc), "-map", "[out]", "-t", f"{d:.3f}", "-r", str(FPS),
                 "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-an", out])


def render_rewind(it, items, stab, wd, out):
    """Rewind montage: frames from the end of the route back to its start (only from ranges already in the cut)."""
    n = max(2, round(it["rw"] * FPS)); rd = wd / "rw"; rd.mkdir(exist_ok=True)
    rngs = [(s["in"], s["out"], s) for s in items[1:]][::-1]; tot = sum(b - a for a, b, _ in rngs); icon = rewind_png()
    for k in range(n):
        q, acc = tot * (k + 0.5) / n, 0.0
        for a, b, s in rngs:
            if q <= acc + (b - a):
                break
            acc += b - a
        im = frame_out(grab(stab, b - (q - acc)), s, 1.0)
        r, gg, bb = im.split(); im = Image.merge("RGB", (ImageChops.offset(r, 12, 0), gg, ImageChops.offset(bb, -12, 0)))
        im = ImageEnhance.Color(im).enhance(0.55).filter(ImageFilter.BoxBlur(2)).convert("RGBA")
        im.alpha_composite(icon, (W // 2 - 130, 630)); im.convert("RGB").save(rd / f"r_{k:03d}.png")
    run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", rd / "r_%03d.png", "-frames:v", str(n), "-r", str(FPS),
         "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out])
    return (W // 2 - 130, 630, 260, 260)


SFX_SRC = {
    "whoosh": "anoisesrc=d=0.5:c=pink:a=0.5,highpass=f=400,lowpass=f=7000,afade=t=in:d=0.32:curve=qsin,afade=t=out:st=0.32:d=0.18",
    "pop": "sine=f=1050:d=0.1,afade=t=out:d=0.1:curve=exp",
    "thump": "sine=f=70:d=0.32,afade=t=out:d=0.32:curve=exp",
    "rewind": "anoisesrc=d=0.6:c=white:a=0.35,bandpass=f=3000:width_type=h:w=2500,tremolo=f=24:d=0.8,afade=t=in:d=0.05,afade=t=out:st=0.45:d=0.15",
}
SFX_DB = {"whoosh": -9, "pop": -12, "thump": -6, "rewind": -10}


def sfx_bus(spec, items, end, total, wd):
    """Synthesized SFX (ffmpeg lavfi, nothing licensed) on a silent bed: whoosh into each cut, rewind, freeze thump, label pop."""
    sd = wd / "sfx"; sd.mkdir(exist_ok=True)
    for k, src in SFX_SRC.items():
        if not (sd / f"{k}.wav").exists():
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-ac", "2", "-ar", "48000", sd / f"{k}.wav"])
    ev = [("pop", 0.02)] + [("whoosh", it["out_start"] - 0.3) for it in items[1:]] + [("whoosh", end["out_start"] - 0.3)]
    for it in items:
        if it.get("rw"):
            ev.append(("rewind", it["out_start"] + it["live"]))
        if it.get("callout"):
            tf = it["out_start"] + it["live"]; ev += [("thump", tf), ("pop", tf + 0.3)]
    off = spec.get("sfx_db", 0)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]; fc, labs = [], []
    for k, (name, t) in enumerate(ev, 1):
        ms = max(0, int(round(t * 1000))); cmd += ["-i", sd / f"{name}.wav"]
        fc.append(f"[{k}:a]volume={SFX_DB[name] + off}dB,adelay={ms}|{ms}[s{k}]"); labs.append(f"[s{k}]")
    fc.append("[0:a]" + "".join(labs) + f"amix=inputs={len(labs) + 1}:normalize=0:duration=first[sfx]")
    out = wd / "sfx_bus.wav"
    run(cmd + ["-filter_complex", ";".join(fc), "-map", "[sfx]", "-c:a", "pcm_s16le", out])
    print(f"SFX: {len(ev)} events (synthesized)")
    return out


def preview(spec, items, end, nsteps, stab, wd):
    bg = Image.open(wd / "bg.png").convert("RGBA")
    tiles = [(items[0], 0.15, "Hook, frame 1"), (items[1], items[1]["live"] * 0.6, "Step + captions")]
    tiles += [(it, it["live"] + it["hold"] - 0.04, "Callout: " + it["callout"]["label"]) for it in items if it.get("callout")]
    tiles += [(items[-1], items[-1]["live"] * 0.7, "Arrival"), (None, 0, "End card")]
    ep = endcard_png(spec, stab, wd); ims = []
    for it, tl, lab in tiles:
        ims.append((Image.open(ep).convert("RGBA") if it is None else compose(it, tl, stab, bg, build_layers(it, wd, nsteps)), lab))
    ims[0][0].convert("RGB").save(wd / "social_cover.jpg", quality=92)
    tw, th, cols = 405, 720, 4; rows = math.ceil(len(ims) / cols)
    for name, safe in (("social_preview.jpg", False), ("social_preview_safe.jpg", True)):
        sheet = Image.new("RGB", (tw * cols, (th + 40) * rows), (20, 20, 20)); d = ImageDraw.Draw(sheet)
        f = G.font("Poppins-SemiBold.ttf", 22)
        for k, (im, lab) in enumerate(ims):
            im = im.copy()
            if safe:
                ImageDraw.Draw(im).rectangle(SAFE, outline=(255, 0, 80, 255), width=5)
            x, y = (k % cols) * tw, (k // cols) * (th + 40)
            sheet.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y + 40)); d.text((x + 10, y + 8), lab, font=f, fill=(255, 255, 255))
        sheet.save(wd / name, quality=88)
    print(f"preview: {len(ims)} frames -> work/social_preview.jpg (+ _safe, social_cover.jpg)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--ambience-stem", action="store_true")
    a = ap.parse_args()
    sp = pathlib.Path(a.spec).resolve(); bd = sp.parent.parent; work = bd / "work"
    spec = json.loads(sp.read_text(encoding="utf-8"))
    if spec.get("accent"):
        G.set_accent(spec["accent"])
    wd = work / "seg_social"; wd.mkdir(exist_ok=True)
    raw_abs = str((bd / spec["source"]).resolve()); stab = work / "stab.mp4"
    vo = estimate_vo(spec) if a.preview else R.tts_all(spec, work, lines=vo_lines(spec), sub=spec.get("tts_dir", "tts_social"))
    items, end, total = plan(spec, vo)
    nsteps = max(it.get("step") or 0 for it in items)
    (work / "social_plan.json").write_text(json.dumps({"total": total, "estimated_vo": a.preview, "shots": [
        {k: it[k] for k in ("idx", "in", "out", "out_start", "dur", "live", "hold", "rw", "speed", "pad")} for it in items],
        "end": {k: end[k] for k in ("out_start", "dur")}}, indent=1), encoding="utf-8")
    print(f"plan: hook + {len(items) - 1} shots + end card, total {total:.1f}s{' (estimated VO)' if a.preview else ''}")
    bgp = wd / "bg.png"; bg_social(bgp)
    if a.preview:
        preview(spec, items, end, nsteps, stab, wd); return
    if a.plan_only:
        return
    if a.ambience_stem:
        rd = bd / "qa"; rd.mkdir(exist_ok=True)
        mix = S.build_audio(spec, bd, [dict(it, vo=None) for it in items], dict(end, vo=None), total)
        stem = rd / f"{spec['out_stem']}_ambience_only.m4a"; mix.replace(stem)
        stem.with_suffix(".timeline.json").write_text(json.dumps(R.timeline(stem.name, (0, 0), total, items, end, raw_abs, None),
                                                                 indent=1, ensure_ascii=False), encoding="utf-8")
        print("OK", stem.name); return
    if not stab.exists():
        stab = R.stabilise(spec, bd)
    segs, ovl, cap_h = [], [], 0
    for it in items:
        layers = build_layers(it, wd, nsteps); t0 = it["out_start"]; d = it["live"] + it["hold"]
        for p, x, y, en, reg in layers:
            if reg:
                rx, ry, rw_, rh = reg[1]
                ovl.append({"name": f"{reg[0]}_{it['idx']:02d}.png", "x": int(rx), "y": int(ry), "w": int(rw_), "h": int(rh),
                            "start": round(t0 + (en[0] if en else 0), 3), "end": round(t0 + (en[1] if en else d), 3)})
            elif "cap_" in p.name:
                cap_h = max(cap_h, Image.open(p).height)
        seg = wd / f"seg_{it['idx']:02d}.mp4"; render_seg(it, stab, bgp, layers, seg); segs.append(seg)
        if it.get("rw"):
            rs = wd / "seg_rewind.mp4"; rx, ry, rw_, rh = render_rewind(it, items, stab, wd, rs); segs.append(rs)
            ovl.append({"name": "rewind_icon.png", "x": rx, "y": ry, "w": rw_, "h": rh,
                        "start": round(t0 + it["live"], 3), "end": round(t0 + it["dur"], 3)})
        print(f"  seg {it['idx']:02d}: {it['dur']:.2f}s at {it['speed']}x")
    ep = endcard_png(spec, stab, wd); ed = end["dur"]; se = wd / "seg_end.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{ed:.3f}", "-i", ep, "-vf",
         f"fade=in:st=0:d=0.2,fade=out:st={ed - 0.4:.3f}:d=0.4,format=yuv420p", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-an", se])
    segs.append(se)
    lst = wd / "concat.txt"; lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), encoding="utf-8")
    vid = wd / "video.mp4"; run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid])
    layout = {"safe": list(SAFE), "overlays": ovl, "caption_band": [SAFE[0], CAP_BOTTOM - (cap_h or 120), SAFE[2], CAP_BOTTOM],
              "captions_hidden": [[end["out_start"], total]]}
    sfx = sfx_bus(spec, items, end, total, work)
    mixes = [("", S.build_audio(spec, bd, items, end, total, music=bool(spec.get("music")), out_name="mix_social.m4a", extra=sfx))]
    if spec.get("music"):
        mixes.append(("_nomusic", S.build_audio(spec, bd, items, end, total, out_name="mix_social_nomusic.m4a", extra=sfx)))
    rd = bd / "renders"; rd.mkdir(exist_ok=True)
    for suf, mix in mixes:
        out = rd / f"{spec['out_stem']}_9x16{suf}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "20",
             "-preset", "slow", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest",
             "-movflags", "+faststart", out])
        out.with_suffix(".timeline.json").write_text(json.dumps(R.timeline(out.name, (W, H), total, items, end, raw_abs, layout),
                                                                indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"OK {out.name} {W}x{H} {R.dur_of(out):.1f}s")


if __name__ == "__main__":
    main()
