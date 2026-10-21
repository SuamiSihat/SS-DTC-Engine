#!/usr/bin/env python3
"""Render ad versions (A master, B cold open, C topic visual) from a batch spec.

Usage: python scripts/render_batch.py batches/<batch>/spec.json [--only 001] [--versions ABC] [--preview 20]
Spec: see skills/dtc-reels-editor/references/spec-format.md
Needs ffmpeg on PATH, Pillow. Fonts: Poppins installed system-wide. Writes renders/<name>.mp4 and
renders/<name>.timeline.json (used by check_sync.py --timeline).
"""
import argparse, json, os, pathlib, re, subprocess, sys, types
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import look_filter
import broll
LOOK = None  # set in main() from spec["look"]; None = no film look (default)
W, H = 1080, 1920
# Safe area for Instagram Reels + TikTok at 1080x1920 (see skills/dtc-broll, references/safe-zones.md)
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 120, 960, 270, 1248
SAFE_W = SAFE_R - SAFE_L            # 840
OVL_X = SAFE_L                      # overlay left edge
OVL_Y = 925                         # headline / lower third: below the doctor's chin, above the caption band
HEAD_Y_TOP = 285                    # hook C headline sits in the top panel, inside the top margin
CAP_BOTTOM = SAFE_B                 # captions end here
CAP_SIZE = 70
HEAD_BOTTOM_MAX = 1105               # headline/lower third must end above the caption band
def head_y(h): return min(OVL_Y, HEAD_BOTTOM_MAX - h)
# Hook C layout: headline on navy at the top, doctor in a rounded card so the face stays inside the safe area
CARD_W, CARD_H, CARD_X, CARD_Y, CARD_R = 864, 860, 108, 480, 40
CARD_MASK = None  # set in main()
def make_card_mask(path):
    m = Image.new("L", (CARD_W, CARD_H), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=CARD_R, fill=255)
    m.save(path)
NAVY, CNAVY, GOLD, AZURE, WHITE = (2, 32, 87), (15, 76, 117), (244, 162, 97), (33, 161, 247), (255, 255, 255)
FONT_DIRS = [r"C:\Windows\Fonts", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"), "/usr/share/fonts/truetype/poppins"]

def font(name, size):
    for d in FONT_DIRS:
        p = pathlib.Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise SystemExit(f"Font not found: {name} (install Poppins system-wide)")

def rgb_to_ass(c, alpha=0):
    return "&H%02X%02X%02X%02X" % (alpha, c[2], c[1], c[0])

# ---------- overlay images ----------
def wrap(draw, words, fnt, maxw):
    lines, cur = [], []
    for w in words:
        t = " ".join(x[0] for x in cur + [w])
        if cur and draw.textlength(t, font=fnt) > maxw:
            lines.append(cur); cur = [w]
        else:
            cur.append(w)
    if cur: lines.append(cur)
    return lines

def make_headline(path, text, size=60, maxw=SAFE_W - 90):
    """text with *key words* in gold."""
    fnt = font("Poppins-Bold.ttf", size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    toks = []
    for part in re.split(r"(\*[^*]+\*)", text):
        if not part: continue
        key = part.startswith("*")
        for w in part.strip("*").split():
            toks.append((w, key))
    for sz in (size, size - 6, size - 12, size - 16):   # shrink until it fits 2 lines (keeps the caption band clear)
        fnt = font("Poppins-Bold.ttf", sz); lines = wrap(d0, toks, fnt, maxw)
        if len(lines) <= 2: break
    size = sz
    lh = int(size * 1.26); pad = 26
    h = lh * len(lines) + pad * 2
    img = Image.new("RGBA", (SAFE_W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, h - 1], radius=36, fill=NAVY + (232,))
    d.rectangle([0, 28, 12, h - 28], fill=GOLD + (255,))
    y = pad
    for line in lines:
        wtot = sum(d.textlength(w + " ", font=fnt) for w, _ in line) - d.textlength(" ", font=fnt)
        x = (img.width - wtot) / 2
        for w, key in line:
            d.text((x, y), w, font=fnt, fill=(GOLD if key else WHITE) + (255,))
            x += d.textlength(w + " ", font=fnt)
        y += lh
    img.save(path)
    return img.size

def make_lower_third(path, name, title):
    fn, ft = font("Poppins-Bold.ttf", 58), font("Poppins-Medium.ttf", 34)
    w = min(SAFE_W, int(max(ImageDraw.Draw(Image.new("RGBA", (5, 5))).textlength(name, font=fn),
                ImageDraw.Draw(Image.new("RGBA", (5, 5))).textlength(title, font=ft)) + 90))
    img = Image.new("RGBA", (w, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, 159], radius=28, fill=NAVY + (236,))
    d.rectangle([0, 24, 12, 136], fill=GOLD + (255,))
    d.text((44, 18), name, font=fn, fill=WHITE + (255,))
    d.text((44, 92), title, font=ft, fill=(220, 232, 245, 255))
    img.save(path)
    return img.size

def make_endcard(path, logo_png, line, cta):
    img = Image.new("RGB", (W, H), NAVY)
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(NAVY[i] + (CNAVY[i] - NAVY[i]) * t) for i in range(3))
        for x in range(W): px[x, y] = c
    d = ImageDraw.Draw(img)
    logo = Image.open(logo_png).convert("RGBA")
    lw = 800; lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.paste(logo, ((W - lw) // 2, 640), logo)
    f1, f2 = font("Poppins-Bold.ttf", 88), font("Poppins-Medium.ttf", 48)
    for txt, f, y, col in ((line, f1, 930, GOLD), (cta, f2, 1090, WHITE)):
        tw = d.textlength(txt, font=f)
        d.text(((W - tw) / 2, y), txt, font=f, fill=col)
    img.save(path)

# ---------- words and captions ----------
def load_words(path):
    data = json.load(open(path, encoding="utf-8"))
    out = []
    for s in data["segments"]:
        for w in s.get("words", []):
            out.append({"w": w["word"].strip(), "s": w["start"], "e": w["end"]})
    return out

def clean(w): return re.sub(r"[^\w']", "", w.lower())

def words_between(words, s, e):
    return [dict(w) for w in words if s <= (w["s"] + w["e"]) / 2 <= e]

def snap(words, s, e, pre=0.08, post=0.12):
    ws = words_between(words, s, e)
    if not ws: return s, e
    a = ws[0]["s"] - pre; b = ws[-1]["e"] + post
    prev = [w for w in words if w["e"] <= ws[0]["s"] and w is not ws[0]]
    nxt = [w for w in words if w["s"] >= ws[-1]["e"] and w is not ws[-1]]
    if prev: a = max(a, (prev[-1]["e"] + ws[0]["s"]) / 2)
    if nxt: b = min(b, (nxt[0]["s"] + ws[-1]["e"]) / 2)
    return max(0.0, a), b

_cap_font = None
def build_ass(path, words, fixes):
    """words: list with out-timeline s/e. Groups of <=3 words, current word gold."""
    global _cap_font
    if _cap_font is None: _cap_font = font("Poppins-Bold.ttf", CAP_SIZE)
    for w in words:
        k = clean(w["w"])
        if k in fixes:
            tail = re.sub(r"[\w']", "", w["w"])
            w["w"] = fixes[k] + tail
    groups, cur = [], []
    for w in words:
        too_wide = bool(cur) and _cap_font.getlength(" ".join(x["w"] for x in cur + [w])) > SAFE_W - 70
        if cur and (len(cur) >= 3 or too_wide or w["s"] - cur[-1]["e"] > 0.45 or re.search(r"[.?!]$", cur[-1]["w"])):
            groups.append(cur); cur = []
        cur.append(w)
    if cur: groups.append(cur)
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,Poppins,{CAP_SIZE},{rgb_to_ass(WHITE)},{rgb_to_ass(WHITE)},{rgb_to_ass(NAVY,0x30)},{rgb_to_ass(NAVY,0x30)},-1,0,0,0,100,100,0,0,3,20,0,2,{SAFE_L},{W-SAFE_R},{H-CAP_BOTTOM},1

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

# ---------- ffmpeg graph ----------
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:]); raise SystemExit("ffmpeg failed")

def render(name, items, overlays, ass_words, fixes, out_dir, work, fps, preview=None):
    """items: list of dict(type clip|end, src, s, e, mode wide|tight|split, png). overlays: list of dict(png,x,y,start,end)."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
    inputs = []; vf = []; seg_labels = []
    t_out = 0.0; timeline = []
    for it in items:
        idx = len(inputs)
        if it["type"] == "clip":
            nfr = max(1, round((it["e"] - it["s"]) * fps))
            d = nfr / fps  # frame-aligned so audio and video segment lengths are identical
            cmd += ["-ss", f"{it['s']:.3f}", "-t", f"{d + 0.25:.3f}", "-i", it["src"]]; inputs.append(1)
            vi = idx
            lab = f"v{idx}"
            base = f"[{vi}:v:0]setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop=3,trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p"
            if it["mode"] == "wide":
                vf.append(f"{base},scale={W}:{H}:flags=lanczos,setsar=1[{lab}]")
            elif it["mode"] == "tight":
                vf.append(f"{base},crop=iw/1.22:ih/1.22:(iw-iw/1.22)*0.5:(ih-ih/1.22)*0.05,scale={W}:{H}:flags=lanczos,setsar=1[{lab}]")
            else:  # split (hook C): navy background, headline on top, doctor in a rounded card (face inside the safe area)
                g = len(inputs)
                cmd += ["-f", "lavfi", "-t", f"{d + 0.1:.3f}", "-i", f"gradients=s={W}x{H}:c0=0x022057:c1=0x0F4C75:x0=0:y0=0:x1={W}:y1={H}:speed=0.01:type=linear:nb_colors=2"]
                inputs.append(1)
                mk = len(inputs)
                cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{d + 0.1:.3f}", "-i", str(CARD_MASK)]
                inputs.append(1)
                vf.append(f"{base},crop=iw:iw*{CARD_H}/{CARD_W}:0:ih*0.03,scale={CARD_W}:{CARD_H}:flags=lanczos,setsar=1,format=rgba[drp{idx}]")
                vf.append(f"[{mk}:v]fps={fps},trim=end_frame={nfr},setpts=PTS-STARTPTS,format=gray[mk{idx}]")
                vf.append(f"[drp{idx}][mk{idx}]alphamerge[dr{idx}]")
                if LOOK:  # film look on the background only; the doctor stays clean
                    vf.append(f"[{g}:v]fps={fps},trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[lk{idx}_in]")
                    vf.append(look_filter.look_chain(LOOK, W, H, fps).replace("lk_", f"lk{idx}_"))
                    vf.append(f"[lk{idx}_out]null[bg{idx}]")
                else:
                    vf.append(f"[{g}:v]fps={fps},trim=end_frame={nfr},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[bg{idx}]")
                vf.append(f"[bg{idx}][dr{idx}]overlay={CARD_X}:{CARD_Y}:shortest=1,format=yuv420p[{lab}]")
            vf.append(f"[{vi}:a:0]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={d:.5f},atrim=0:{d:.5f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.02,afade=t=out:st={max(0,d-0.04):.3f}:d=0.04[a{idx}]")
            timeline.append({"out_start": round(t_out, 3), "dur": round(d, 3), "src": it["src"], "src_start": round(it["s"], 3), "mode": it["mode"]})
        else:
            d = round(it["dur"] * fps) / fps
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{d:.3f}", "-i", it["png"]]; inputs.append(1)
            cmd += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]; inputs.append(1)
            lab = f"v{idx}"
            vf.append(f"[{idx}:v]trim=end_frame={round(d*fps)},setpts=PTS-STARTPTS,format=yuv420p,setsar=1,fade=t=in:st=0:d=0.3[{lab}]")
            vf.append(f"[{idx+1}:a]aformat=channel_layouts=stereo,atrim=0:{d:.5f},asetpts=PTS-STARTPTS[a{idx}]")
        seg_labels.append((lab, f"a{idx}"))
        t_out += d
    total = t_out
    vf.append("".join(f"[{v}][{a}]" for v, a in seg_labels) + f"concat=n={len(seg_labels)}:v=1:a=1[vc][ac]")
    cur = "vc"
    for k, ov in enumerate(overlays):
        i = len(inputs)
        dur = ov["end"] - ov["start"]
        cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", ov["png"]]; inputs.append(1)
        fi, fo = ov.get("fi", 0.2), ov.get("fo", 0.2)
        fades = (f"fade=t=in:st=0:d={fi}:alpha=1," if fi > 0 else "") + (f"fade=t=out:st={max(0,dur-fo):.3f}:d={fo}:alpha=1," if fo > 0 else "")
        vf.append(f"[{i}:v]format=rgba,{fades}setpts=PTS+{ov['start']:.3f}/TB[ov{k}]")
        vf.append(f"[{cur}][ov{k}]overlay={ov['x']}:{ov['y']}:eof_action=pass:enable='between(t,{ov['start']:.3f},{ov['end']:.3f})'[vo{k}]")
        cur = f"vo{k}"
    ass_path = work / f"{name}.ass"
    build_ass(ass_path, ass_words, fixes)
    vf.append(f"[{cur}]ass={ass_path.name}[vf]")
    out = out_dir / f"{name}.mp4"
    cmd += ["-filter_complex", ";".join(vf), "-map", "[vf]", "-map", "[ac]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p",
            "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart"]
    if preview: cmd += ["-t", str(preview)]
    cmd.append(str(out))
    run_cwd = os.getcwd()
    os.chdir(work)
    try:
        subprocess.run  # noqa
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        os.chdir(run_cwd)
    if r.returncode:
        sys.stderr.write(r.stderr[-4000:]); raise SystemExit(f"ffmpeg failed for {name}")
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    if probe != f"{W},{H}":
        raise SystemExit(f"{name}: output is {probe}, must be {W},{H}")
    ovl = []
    for ov in overlays:
        w_, h_ = Image.open(ov["png"]).size
        ovl.append({"name": pathlib.Path(ov["png"]).name, "kind": ov.get("kind", "overlay"), "x": ov["x"], "y": ov["y"], "w": w_, "h": h_, "start": round(ov["start"], 3), "end": round(ov["end"], 3)})
    hidden = [[o["start"], o["end"]] for o in ovl if o["kind"] == "quote"]
    layout = {"safe": [SAFE_L, SAFE_T, SAFE_R, SAFE_B], "overlays": ovl, "caption_band": [SAFE_L, CAP_BOTTOM - 130, SAFE_R, CAP_BOTTOM], "captions_hidden": hidden,
              "card": [CARD_X, CARD_Y, CARD_W, CARD_H]}
    (out_dir / f"{name}.timeline.json").write_text(json.dumps({"file": out.name, "total": round(total, 3), "items": timeline, "layout": layout}, indent=2), encoding="utf-8")
    return out, total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--only"); ap.add_argument("--versions", default="ABC"); ap.add_argument("--preview", type=float)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    batch = pathlib.Path(a.spec).resolve().parent.parent if pathlib.Path(a.spec).parent.name == "work" else pathlib.Path(a.spec).resolve().parent
    work = batch / "work"; out_dir = batch / "renders"; out_dir.mkdir(exist_ok=True); work.mkdir(exist_ok=True)
    fps = spec.get("fps", 30)
    brand = spec["brand"]
    global LOOK, CARD_MASK
    LOOK = look_filter.load_look(brand, spec.get("look_preset")) if spec.get("look") == "editorial" else None
    logo = ROOT / "brands" / brand / "design-system" / "logos" / "logo_ssc_primary_dark.png"
    if "logo" in spec: logo = ROOT / spec["logo"]
    ec = spec["end_card"]; lt = spec["lower_third"]
    CARD_MASK = work / "cardmask.png"; make_card_mask(CARD_MASK)
    make_endcard(work / "endcard.png", logo, ec["line"], ec["cta"])
    ltw, lth = make_lower_third(work / "lowerthird.png", lt["name"], lt["title"])
    for clip in spec["clips"]:
        if a.only and clip["id"] != a.only: continue
        words = load_words(batch / clip["words"] if not os.path.isabs(clip["words"]) else clip["words"])
        fixes = {k.lower(): v for k, v in clip.get("fixes", {}).items()}
        segs = [snap(words, s, e) for s, e in clip["segments"]]
        n = clip["n"]
        def mk_items(first_mode_split=False, opener=None):
            items = []; ass = []; t = 0.0; modes = ["wide", "tight"]
            seq = ([("opener", opener)] if opener else []) + [("seg", s) for s in segs]
            for k, (kind, sg) in enumerate(seq):
                s, e = sg
                if kind == "opener": mode = "tight"
                elif first_mode_split and k == 0: mode = "split"
                else: mode = modes[(k - (1 if opener else 0)) % 2]
                e = s + max(1, round((e - s) * fps)) / fps
                items.append({"type": "clip", "src": clip["src"], "s": s, "e": e, "mode": mode})
                for w in words_between(words, s, e):
                    ass.append({"w": w["w"], "s": t + (w["s"] - s), "e": t + (w["e"] - s)})
                t += e - s
            items.append({"type": "end", "png": str(work / "endcard.png"), "dur": ec.get("dur", 2.8)})
            return items, ass, t
        name_base = f"{spec['prefix']}{n}"
        versions = {}
        if "A" in a.versions:
            items, ass, body = mk_items()
            hl = work / f"hl_{clip['id']}_A.png"; hw, hh = make_headline(hl, clip["headline"])
            ovs = [{"png": str(hl), "x": OVL_X, "y": head_y(hh), "start": 0.2, "end": 3.4},
                   {"png": str(work / "lowerthird.png"), "x": OVL_X, "y": head_y(lth), "start": 3.8, "end": 7.8}]
            versions["A_Master"] = (items, ovs, ass)
        if "B" in a.versions and "B" in clip.get("hooks", {}):
            hk = clip["hooks"]["B"]; op = snap(words, *hk["segment"])
            items, ass, body = mk_items(opener=op)
            od = op[1] - op[0]
            hl = work / f"hl_{clip['id']}_B.png"; hw, hh = make_headline(hl, hk["headline"])
            ovs = [{"png": str(hl), "x": OVL_X, "y": HEAD_Y_TOP, "start": 0.1, "end": max(1.5, od - 0.1)},  # opener is a tight shot: face top is about y 460, so the headline goes above it
                   {"png": str(work / "lowerthird.png"), "x": OVL_X, "y": head_y(lth), "start": od + 0.5, "end": od + 4.5}]
            versions["B_Hook-ColdOpen"] = (items, ovs, ass)
        if "C" in a.versions and "C" in clip.get("hooks", {}):
            hk = clip["hooks"]["C"]
            items, ass, body = mk_items(first_mode_split=True)
            od = items[0]["e"] - items[0]["s"]
            hl = work / f"hl_{clip['id']}_C.png"; make_headline(hl, hk["headline"], size=72)
            ovs = [{"png": str(hl), "x": OVL_X, "y": HEAD_Y_TOP, "start": 0.1, "end": max(1.5, od - 0.1)},
                   {"png": str(work / "lowerthird.png"), "x": OVL_X, "y": HEAD_Y_TOP, "start": od + 0.4, "end": od + 4.4}]
            versions["C_Hook-TopicVisual"] = (items, ovs, ass)
        for vname, (items, ovs, ass) in versions.items():
            name = f"{name_base}_{vname}"
            print("render", name, flush=True)
            ass = broll.apply_quotes(types.SimpleNamespace(**globals()), clip, words, items, ovs, ass, work, vname[0])
            out, total = render(name, items, ovs, ass, fixes, out_dir, work, fps, a.preview)
            print(f"  -> {out.name} {total:.1f}s", flush=True)

if __name__ == "__main__":
    main()
