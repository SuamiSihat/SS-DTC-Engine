#!/usr/bin/env python3
"""Animated overlay clips (slide-in, scale-pop, typewriter, counter, wipe, transitions).

Usage:
  motion.py slide-in work/headline.mov --text "Bukan *Ubat*" --direction left --duration 3.0
  motion.py counter-tick work/counter.mov --from 0 --to 15000 --label "Unit Terjual"
  motion.py transition work/trans.mov --style push --direction left --duration 0.4
  motion.py batch work/spec.json --work batches/b01/work/ --out batches/b01/work/motion/
  motion.py --demo --out work/motion_demo/
Generates PNG sequences at 30 fps, encodes to transparent MOV (qtrle).
"""
import argparse, json, math, os, pathlib, subprocess, sys, tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
FPS = 30
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


def hex_rgba(h):
    h = h.lstrip("#")
    if len(h) == 8:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)


def _ease_in_out(t):
    return t * t * (3 - 2 * t)


def _ease_out_back(t, overshoot=1.05):
    s = (overshoot - 1.0) * 3.5
    t1 = t - 1.0
    return 1.0 + t1 * t1 * (s * t1 + s + t1)


def load_brand_colors(slug):
    bp = ROOT / "brands" / slug / "brand.json"
    if not bp.exists():
        return {}
    return json.loads(bp.read_text(encoding="utf-8")).get("colors", {})


def parse_highlight(text, color, accent):
    """Split text on *word* markers. Odd segments get accent color."""
    segments = text.split("*")
    parts = []
    for i, seg in enumerate(segments):
        if not seg:
            continue
        parts.append((seg, accent if i % 2 == 1 else color))
    return parts if parts else [(text, color)]


def gen_slide_in(width, height, text, font_name, font_size, color, bg_color,
                direction="left", entrance=0.3, exit_dur=0.2, duration=3.0, accent=None):
    """Generate slide-in animation frames as RGBA PIL Images."""
    from PIL import Image, ImageDraw
    fnt = _font(font_name, font_size)
    n_frames = int(duration * FPS)
    ent_f = int(entrance * FPS)
    exit_f = int(exit_dur * FPS)
    frames = []
    for i in range(n_frames):
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        # Entrance / exit offset
        if i < ent_f:
            t = _ease_in_out(i / max(1, ent_f))
        elif i >= n_frames - exit_f:
            t = _ease_in_out((n_frames - 1 - i) / max(1, exit_f))
        else:
            t = 1.0
        if direction == "left":
            ox = int(-width * (1 - t))
            oy = 0
        elif direction == "right":
            ox = int(width * (1 - t))
            oy = 0
        else:  # up/down
            ox = 0
            oy = int((-height if direction == "up" else height) * (1 - t))
        # Background
        bg = hex_rgba(bg_color) if isinstance(bg_color, str) else bg_color
        draw.rounded_rectangle([ox, oy, ox + width, oy + height], radius=12, fill=bg)
        # Text
        clr = hex_rgba(color) if isinstance(color, str) else color
        acc = hex_rgba(accent) if accent and isinstance(accent, str) else clr
        parts = parse_highlight(text, clr[:3], acc[:3])
        tx, ty = ox + 24, oy + (height - font_size) // 2
        for seg_text, seg_color in parts:
            draw.text((tx, ty), seg_text, fill=seg_color, font=fnt)
            bbox = fnt.getbbox(seg_text)
            tx += bbox[2] - bbox[0]
        frames.append(im)
    return frames


def gen_scale_pop(width, height, text, font_name, font_size, color, bg_color,
                  entrance=0.25, exit_dur=0.2, overshoot=1.05, duration=3.0, accent=None):
    from PIL import Image, ImageDraw
    fnt = _font(font_name, font_size)
    n_frames = int(duration * FPS)
    ent_f = int(entrance * FPS)
    exit_f = int(exit_dur * FPS)
    frames = []
    for i in range(n_frames):
        if i < ent_f:
            s = _ease_out_back(i / max(1, ent_f), overshoot)
        elif i >= n_frames - exit_f:
            s = _ease_in_out((n_frames - 1 - i) / max(1, exit_f))
        else:
            s = 1.0
        s = max(0.01, s)
        sw, sh = int(width * s), int(height * s)
        chip = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(chip)
        bg = hex_rgba(bg_color) if isinstance(bg_color, str) else bg_color
        draw.rounded_rectangle([0, 0, sw, sh], radius=max(1, int(12 * s)), fill=bg)
        clr = hex_rgba(color) if isinstance(color, str) else color
        acc = hex_rgba(accent) if accent and isinstance(accent, str) else clr
        parts = parse_highlight(text, clr[:3], acc[:3])
        tx = max(1, int(24 * s))
        ty = (sh - int(font_size * s)) // 2
        sfnt = _font(font_name, max(8, int(font_size * s)))
        for seg_text, seg_color in parts:
            draw.text((tx, ty), seg_text, fill=seg_color, font=sfnt)
            bbox = sfnt.getbbox(seg_text)
            tx += bbox[2] - bbox[0]
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        px = (width - sw) // 2
        py = (height - sh) // 2
        im.paste(chip, (px, py), chip)
        frames.append(im)
    return frames


def gen_typewriter(width, height, text, font_name, font_size, color, bg_color,
                   char_delay=0.04, duration=3.0, accent=None):
    from PIL import Image, ImageDraw
    fnt = _font(font_name, font_size)
    n_frames = int(duration * FPS)
    clr = hex_rgba(color) if isinstance(color, str) else color
    bg = hex_rgba(bg_color) if isinstance(bg_color, str) else bg_color
    clean = text.replace("*", "")
    frames = []
    for i in range(n_frames):
        t_sec = i / FPS
        n_chars = min(len(clean), int(t_sec / char_delay))
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        draw.rounded_rectangle([0, 0, width, height], radius=12, fill=bg)
        draw.text((24, (height - font_size) // 2), clean[:n_chars], fill=clr[:3], font=fnt)
        frames.append(im)
    return frames


def gen_counter_tick(width, height, target, label, font_name, font_size, color,
                     bg_color, start_val=0, tick_dur=1.5, duration=3.0):
    from PIL import Image, ImageDraw
    fnt = _font(font_name, font_size)
    lfnt = _font(font_name.replace("Bold", "Regular").replace("ExtraBold", "Regular"),
                 max(16, font_size // 2))
    n_frames = int(duration * FPS)
    tick_frames = int(tick_dur * FPS)
    clr = hex_rgba(color) if isinstance(color, str) else color
    bg = hex_rgba(bg_color) if isinstance(bg_color, str) else bg_color
    frames = []
    for i in range(n_frames):
        frac = _ease_in_out(min(1.0, i / max(1, tick_frames)))
        val = int(start_val + (target - start_val) * frac)
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        draw.rounded_rectangle([0, 0, width, height], radius=16, fill=bg)
        num_str = f"{val:,}"
        nb = fnt.getbbox(num_str)
        nx = (width - (nb[2] - nb[0])) // 2
        draw.text((nx, height // 4), num_str, fill=clr[:3], font=fnt)
        if label:
            lb = lfnt.getbbox(label)
            lx = (width - (lb[2] - lb[0])) // 2
            draw.text((lx, height * 2 // 3), label, fill=clr[:3], font=lfnt)
        frames.append(im)
    return frames


def gen_transition(width, height, style="push", direction="left", duration=0.4):
    from PIL import Image
    n_frames = max(2, int(duration * FPS))
    frames = []
    for i in range(n_frames):
        t = _ease_in_out(i / (n_frames - 1))
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(im)
        if style == "flash":
            alpha = int(255 * (1.0 - abs(2 * t - 1)))
            draw.rectangle([0, 0, width, height], fill=(255, 255, 255, alpha))
        elif style == "push":
            ox = int((-width if direction == "left" else width) * t)
            draw.rectangle([ox, 0, ox + width, height], fill=(0, 0, 0, int(200 * (1 - t))))
        elif style == "zoom-through":
            alpha = int(255 * (1.0 - abs(2 * t - 1)))
            draw.rectangle([0, 0, width, height], fill=(0, 0, 0, alpha))
        elif style == "glitch":
            offset = int(20 * math.sin(t * math.pi * 4))
            for y in range(0, height, 40):
                draw.rectangle([offset, y, width + offset, y + 20],
                               fill=(255, 0, 0, int(120 * (1 - t))))
        frames.append(im)
    return frames


def encode_mov(frames, output, fps=FPS):
    """Encode RGBA PIL frames to transparent MOV via ffmpeg qtrle."""
    if not frames:
        return None
    w, h = frames[0].size
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-",
           "-c:v", "qtrle", "-an", str(output)]
    raw = b"".join(f.tobytes() for f in frames)
    r = subprocess.run(cmd, input=raw, capture_output=True)
    if r.returncode:
        sys.stderr.write(r.stderr.decode(errors="replace")[-1000:] + "\n")
        return None
    return pathlib.Path(output)


def run_batch(spec_path, work_dir, out_dir):
    """Process all animated overlays in a spec JSON."""
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    brand = spec.get("brand", "")
    colors = load_brand_colors(brand) if brand else {}
    items = spec.get("layout", {}).get("overlays", spec.get("overlays", []))
    generated = 0
    for idx, ov in enumerate(items):
        anim = ov.get("animate")
        if not anim:
            continue
        atype = anim.get("type", anim.get("preset", "slide-in"))
        text = ov.get("text", "")
        w = ov.get("w", 840)
        h = ov.get("h", 120)
        dur = (ov.get("end", 3.0) - ov.get("start", 0.0))
        fname = f"motion_{idx:03d}_{atype}.mov"
        font_name = anim.get("font", "Poppins-Bold.ttf")
        font_size = anim.get("font_size", 48)
        color = anim.get("color", "#FFFFFF")
        bg = anim.get("bg", "#022057E8")
        accent = anim.get("accent", colors.get("accent", "#F4A261"))
        if atype == "slide-in":
            frames = gen_slide_in(w, h, text, font_name, font_size, color, bg,
                                  direction=anim.get("direction", "left"),
                                  entrance=anim.get("entrance", 0.3),
                                  exit_dur=anim.get("exit", 0.2),
                                  duration=dur, accent=accent)
        elif atype == "scale-pop":
            frames = gen_scale_pop(w, h, text, font_name, font_size, color, bg,
                                   entrance=anim.get("entrance", 0.25),
                                   exit_dur=anim.get("exit", 0.2),
                                   duration=dur, accent=accent)
        elif atype == "typewriter":
            frames = gen_typewriter(w, h, text, font_name, font_size, color, bg,
                                    char_delay=anim.get("char_delay", 0.04),
                                    duration=dur, accent=accent)
        elif atype == "counter-tick":
            frames = gen_counter_tick(w, h,
                                      target=anim.get("to", 1000),
                                      label=anim.get("label", ""),
                                      font_name=font_name, font_size=font_size,
                                      color=color, bg_color=bg,
                                      start_val=anim.get("from", 0),
                                      tick_dur=anim.get("tick_dur", 1.5),
                                      duration=dur)
        else:
            continue
        mov = encode_mov(frames, out_dir / fname)
        if mov:
            ov["motion_file"] = str(mov)
            generated += 1
    # Write updated spec
    out_spec = out_dir / "spec_motion.json"
    out_spec.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK batch: {generated} motion overlays -> {out_dir}")
    return generated


def run_demo(out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    demos = [
        ("slide-in", lambda: gen_slide_in(840, 120, "Bukan *Ubat*", "Poppins-Bold.ttf", 48,
                                           "#FFFFFF", "#022057E8", duration=2.0, accent="#F4A261")),
        ("scale-pop", lambda: gen_scale_pop(400, 100, "100% *Fizikal*", "Poppins-Bold.ttf", 40,
                                             "#FFFFFF", "#1C1C1CE8", duration=2.0, accent="#F4A261")),
        ("typewriter", lambda: gen_typewriter(840, 80, "Doctor Recommended", "Poppins-Bold.ttf", 44,
                                               "#FFFFFF", "#022057E8", duration=2.0)),
        ("counter", lambda: gen_counter_tick(400, 200, 15000, "Unit Terjual", "Poppins-Bold.ttf", 80,
                                              "#F4A261", "#1C1C1CE8", duration=2.0)),
        ("transition-push", lambda: gen_transition(1080, 1920, "push", "left", 0.4)),
        ("transition-flash", lambda: gen_transition(1080, 1920, "flash", "left", 0.2)),
    ]
    for name, gen_fn in demos:
        frames = gen_fn()
        mov = encode_mov(frames, out_dir / f"demo_{name}.mov")
        status = "OK" if mov else "FAIL"
        print(f"  {status} {name}: {len(frames)} frames")
    print(f"Demo complete -> {out_dir}")


def main():
    p = argparse.ArgumentParser(description="Animated overlay clips for video ads")
    sub = p.add_subparsers(dest="command")
    # slide-in
    si = sub.add_parser("slide-in")
    si.add_argument("output", help="Output MOV path")
    si.add_argument("--text", required=True)
    si.add_argument("--direction", default="left", choices=["left", "right", "up", "down"])
    si.add_argument("--duration", type=float, default=3.0)
    si.add_argument("--font", default="Poppins-Bold.ttf")
    si.add_argument("--size", type=int, default=48)
    si.add_argument("--color", default="#FFFFFF")
    si.add_argument("--bg", default="#022057E8")
    si.add_argument("--width", type=int, default=840)
    si.add_argument("--height", type=int, default=120)
    si.add_argument("--entrance", type=float, default=0.3)
    si.add_argument("--exit", type=float, default=0.2, dest="exit_dur")
    si.add_argument("--accent", default=None)
    # scale-pop
    sp = sub.add_parser("scale-pop")
    sp.add_argument("output")
    sp.add_argument("--text", required=True)
    sp.add_argument("--duration", type=float, default=3.0)
    sp.add_argument("--font", default="Poppins-Bold.ttf")
    sp.add_argument("--size", type=int, default=48)
    sp.add_argument("--color", default="#FFFFFF")
    sp.add_argument("--bg", default="#1C1C1CE8")
    sp.add_argument("--width", type=int, default=400)
    sp.add_argument("--height", type=int, default=100)
    sp.add_argument("--entrance", type=float, default=0.25)
    sp.add_argument("--exit", type=float, default=0.2, dest="exit_dur")
    sp.add_argument("--overshoot", type=float, default=1.05)
    sp.add_argument("--accent", default=None)
    # typewriter
    tw = sub.add_parser("typewriter")
    tw.add_argument("output")
    tw.add_argument("--text", required=True)
    tw.add_argument("--duration", type=float, default=3.0)
    tw.add_argument("--font", default="Poppins-Bold.ttf")
    tw.add_argument("--size", type=int, default=48)
    tw.add_argument("--color", default="#FFFFFF")
    tw.add_argument("--bg", default="#022057E8")
    tw.add_argument("--width", type=int, default=840)
    tw.add_argument("--height", type=int, default=80)
    tw.add_argument("--char-delay", type=float, default=0.04)
    # counter-tick
    ct = sub.add_parser("counter-tick")
    ct.add_argument("output")
    ct.add_argument("--from", type=int, default=0, dest="from_val")
    ct.add_argument("--to", type=int, required=True)
    ct.add_argument("--label", default="")
    ct.add_argument("--duration", type=float, default=3.0)
    ct.add_argument("--font", default="Poppins-Bold.ttf")
    ct.add_argument("--size", type=int, default=80)
    ct.add_argument("--color", default="#F4A261")
    ct.add_argument("--bg", default="#1C1C1CE8")
    ct.add_argument("--width", type=int, default=400)
    ct.add_argument("--height", type=int, default=200)
    ct.add_argument("--tick-dur", type=float, default=1.5)
    # transition
    tr = sub.add_parser("transition")
    tr.add_argument("output")
    tr.add_argument("--style", default="push", choices=["push", "zoom-through", "flash", "glitch"])
    tr.add_argument("--direction", default="left")
    tr.add_argument("--duration", type=float, default=0.4)
    tr.add_argument("--width", type=int, default=1080)
    tr.add_argument("--height", type=int, default=1920)
    # batch
    ba = sub.add_parser("batch")
    ba.add_argument("spec", help="Spec JSON")
    ba.add_argument("--work", default="work/")
    ba.add_argument("--out", default="work/motion/")
    # demo / top-level flags
    p.add_argument("--demo", action="store_true")
    p.add_argument("--out", default="work/motion_demo/", dest="demo_out")
    a = p.parse_args()
    if a.demo:
        run_demo(a.demo_out)
        return
    if a.command == "batch":
        run_batch(a.spec, a.work, a.out)
    elif a.command == "slide-in":
        frames = gen_slide_in(a.width, a.height, a.text, a.font, a.size,
                              a.color, a.bg, a.direction, a.entrance, a.exit_dur,
                              a.duration, a.accent)
        r = encode_mov(frames, a.output)
        print(f"OK {r}" if r else "FAIL")
    elif a.command == "scale-pop":
        frames = gen_scale_pop(a.width, a.height, a.text, a.font, a.size,
                               a.color, a.bg, a.entrance, a.exit_dur,
                               a.overshoot, a.duration, a.accent)
        r = encode_mov(frames, a.output)
        print(f"OK {r}" if r else "FAIL")
    elif a.command == "typewriter":
        frames = gen_typewriter(a.width, a.height, a.text, a.font, a.size,
                                a.color, a.bg, a.char_delay, a.duration)
        r = encode_mov(frames, a.output)
        print(f"OK {r}" if r else "FAIL")
    elif a.command == "counter-tick":
        frames = gen_counter_tick(a.width, a.height, a.to, a.label, a.font,
                                  a.size, a.color, a.bg, a.from_val, a.tick_dur, a.duration)
        r = encode_mov(frames, a.output)
        print(f"OK {r}" if r else "FAIL")
    elif a.command == "transition":
        frames = gen_transition(a.width, a.height, a.style, a.direction, a.duration)
        r = encode_mov(frames, a.output)
        print(f"OK {r}" if r else "FAIL")
    else:
        p.print_help()


if __name__ == "__main__":
    main()
