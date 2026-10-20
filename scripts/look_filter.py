#!/usr/bin/env python3
"""SS Editorial look as an ffmpeg filter chain (bloom, light B&W, film grain, weave, vignette).

An ffmpeg approximation of look/browser-reference/picture.js for the Python/ffmpeg render path.
Used on inserts and b-roll only, never on the speaker or the product (see skills/dtc-reels-editor).
Settings live in brands/<slug>/look.json. Demo: python scripts/look_filter.py --demo out.mp4
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
W, H = 1080, 1920
DEFAULTS = {
    "grade": "film",      # clean | film | bw
    "grain": 0.04,        # grain std (0-1 of full range), inserts only. 0 = off
    "bloom": 0.40,        # 0-1, highlight glow
    "bloom_thr": 0.62,    # bright-pass threshold
    "vignette": 0.35,     # 0-1
    "weave": 1.0,         # gate weave in px, 0 = off
    "fade": 0.25,         # archive fade: lifted blacks / lowered whites, 0-1
}

def load_look(brand, name=None):
    cfg = dict(DEFAULTS)
    p = ROOT / "brands" / brand / "look.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        cfg.update(d.get("presets", {}).get(name or d.get("default", "insert"), {}))
    return cfg

def look_chain(cfg, w=W, h=H, fps=30):
    """Return a filter_complex fragment with input [lk_in] and output [lk_out] (yuv420p, same size)."""
    c = {**DEFAULTS, **cfg}
    f = []
    src = "lk_in"
    if c["weave"] > 0:
        m = max(2, int(round(c["weave"] * 2 + 2))); a = c["weave"]
        f.append(f"[{src}]crop=iw-{m*2}:ih-{m*2}:{m}+{a:.2f}*sin(n*0.37)+{a*0.5:.2f}*sin(n*1.31+1.7):{m}+{a:.2f}*cos(n*0.29+0.4)+{a*0.5:.2f}*sin(n*1.07+2.3),scale={w}:{h}:flags=bicubic,setsar=1[lk_w]")
        src = "lk_w"
    if c["grade"] == "bw":
        f.append(f"[{src}]hue=s=0,curves=all='0/0.055 0.5/0.52 1/0.985'[lk_g]"); src = "lk_g"
    elif c["grade"] == "film":
        f.append(f"[{src}]eq=saturation=0.9,curves=r='0/0.01 1/1':b='0/0.02 1/0.98'[lk_g]"); src = "lk_g"
    if c["bloom"] > 0:
        f.append(f"[{src}]split=2[lk_a][lk_b]")
        f.append(f"[lk_b]curves=all='0/0 {c['bloom_thr']:.2f}/0 1/1',scale={w//4}:{h//4},gblur=sigma=4.5:steps=2,scale={w}:{h}[lk_bl]")
        f.append(f"[lk_a][lk_bl]blend=all_mode=screen:all_opacity={min(1.0, c['bloom']*0.8):.2f}[lk_c]"); src = "lk_c"
    if c["fade"] > 0:
        lo, hi = 0.03 * c["fade"] / 0.25, 1 - 0.03 * c["fade"] / 0.25
        f.append(f"[{src}]curves=all='0/{lo:.3f} 1/{hi:.3f}'[lk_f]"); src = "lk_f"
    if c["vignette"] > 0:
        f.append(f"[{src}]vignette=angle={0.35 + 0.5*c['vignette']:.2f}:mode=forward[lk_v]"); src = "lk_v"
    if c["grain"] > 0:
        amp = int(round(c["grain"] * 255 * 1.73))  # uniform noise amplitude for the requested std
        f.append(f"[{src}]noise=alls={amp}:allf=t,format=yuv420p[lk_out]")
    else:
        f.append(f"[{src}]format=yuv420p[lk_out]")
    return ";".join(f)

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--demo":
        out = sys.argv[2]
        brand = sys.argv[3] if len(sys.argv) > 3 else None
        cfg = load_look(brand) if brand else {}
        fc = "[0:v]format=yuv420p,setsar=1[lk_in];" + look_chain(cfg)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s={W}x{H}:r=30:d=2",
               "-filter_complex", fc, "-map", "[lk_out]", "-c:v", "libx264", "-crf", "20", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        sys.stderr.write(r.stderr[-2000:]); sys.exit(r.returncode)
    print(__doc__)

if __name__ == "__main__":
    main()
