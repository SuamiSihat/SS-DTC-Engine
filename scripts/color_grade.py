#!/usr/bin/env python3
"""Colour correction and grading via ffmpeg filter chains.

Usage:
  color_grade.py <video.mp4> [--preset warm] [--protect-skin] [--brand slug]
  color_grade.py <video.mp4> --lut path.cube
  color_grade.py <video.mp4> --preview out.png [--preview-time 5.0]
  color_grade.py --chain --preset cinematic --protect-skin
  color_grade.py --selftest
Needs ffmpeg on PATH. LUTs in brands/<slug>/luts/ or assets/luts/.
"""
import argparse, json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

PRESETS = {
    "neutral":      {"exposure": 0,     "contrast": 1.0,  "saturation": 1.0,  "temperature": 0},
    "warm":         {"exposure": 0.03,  "contrast": 1.02, "saturation": 1.05, "temperature": 200},
    "cool":         {"exposure": 0,     "contrast": 1.03, "saturation": 0.95, "temperature": -200},
    "cinematic":    {"exposure": -0.02, "contrast": 1.08, "saturation": 0.90, "temperature": 100},
    "bright-clean": {"exposure": 0.08,  "contrast": 0.98, "saturation": 0.95, "temperature": 0},
}


def find_lut(name, brand=None):
    """Search brand LUT dir first, then assets/luts/."""
    if brand:
        p = ROOT / "brands" / brand / "luts" / name
        if p.exists():
            return p
    p = ROOT / "assets" / "luts" / name
    if p.exists():
        return p
    raw = pathlib.Path(name)
    if raw.exists():
        return raw
    return None


def load_brand_grade(slug):
    """Load grade settings from brands/<slug>/brand.json if present."""
    bp = ROOT / "brands" / slug / "brand.json"
    if not bp.exists():
        return {}
    b = json.loads(bp.read_text(encoding="utf-8"))
    return b.get("grade", {})


def _temp_to_colorbalance(temp_k):
    """Map temperature (-500..+500 K) to ffmpeg colorbalance values."""
    t = max(-500, min(500, temp_k)) / 500.0
    if t >= 0:
        rs, gs, bs = t * 0.15, t * 0.05, -t * 0.10
    else:
        rs, gs, bs = t * 0.10, -t * 0.02, -t * 0.15
    return rs, gs, bs


def grade_chain(preset=None, protect_skin=False, lut=None, brand=None,
                exposure=None, contrast=None, saturation=None, temperature=None):
    """Return an ffmpeg filter_complex fragment with [cg_in] -> [cg_out]."""
    cfg = dict(PRESETS.get("neutral"))
    if preset and preset in PRESETS:
        cfg.update(PRESETS[preset])
    if brand:
        bg = load_brand_grade(brand)
        if bg.get("preset") and bg["preset"] in PRESETS:
            cfg.update(PRESETS[bg["preset"]])
        if bg.get("protect_skin"):
            protect_skin = True
        if bg.get("lut"):
            lut = bg["lut"]
    if exposure is not None:
        cfg["exposure"] = max(-0.3, min(0.3, exposure))
    if contrast is not None:
        cfg["contrast"] = max(0.8, min(1.3, contrast))
    if saturation is not None:
        cfg["saturation"] = max(0.5, min(1.5, saturation))
    if temperature is not None:
        cfg["temperature"] = max(-500, min(500, temperature))

    filters = []
    src = "cg_in"

    lut_path = find_lut(lut, brand) if lut else None
    if lut_path:
        filters.append(f"[{src}]lut3d=file='{lut_path}'[cg_lut]")
        src = "cg_lut"

    eq_parts = []
    if abs(cfg["exposure"]) > 0.001:
        eq_parts.append(f"brightness={cfg['exposure']:.3f}")
    if abs(cfg["contrast"] - 1.0) > 0.001:
        eq_parts.append(f"contrast={cfg['contrast']:.3f}")
    if abs(cfg["saturation"] - 1.0) > 0.001:
        eq_parts.append(f"saturation={cfg['saturation']:.3f}")
    if eq_parts:
        eq_str = ":".join(eq_parts)
        filters.append(f"[{src}]eq={eq_str}[cg_eq]")
        src = "cg_eq"

    if abs(cfg["temperature"]) > 1:
        rs, gs, bs = _temp_to_colorbalance(cfg["temperature"])
        filters.append(
            f"[{src}]colorbalance=rs={rs:.3f}:gs={gs:.3f}:bs={bs:.3f}[cg_wb]"
        )
        src = "cg_wb"

    if protect_skin:
        filters.append(f"[{src}]split=2[cg_skin_a][cg_skin_b]")
        filters.append(
            "[cg_skin_a]colorkey=color=#D2A172:similarity=0.25:blend=0.15,"
            "format=yuva420p[cg_skin_mask]"
        )
        filters.append(
            f"[cg_skin_b][cg_skin_mask]overlay=format=auto[cg_prot]"
        )
        src = "cg_prot"

    filters.append(f"[{src}]format=yuv420p[cg_out]")
    return ";".join(filters) if filters else f"[cg_in]format=yuv420p[cg_out]"


def apply_grade(video, output, **kwargs):
    """Grade a video file. Returns output path or None on error."""
    preview = kwargs.pop("preview", None)
    preview_time = kwargs.pop("preview_time", 5.0)

    chain = grade_chain(**kwargs)

    if preview:
        preview_path = pathlib.Path(preview)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-v", "error",
            "-ss", str(preview_time), "-i", str(video), "-frames:v", "1",
            "-vf", "format=yuv420p", str(preview_path.with_suffix(".orig.png"))
        ]
        subprocess.run(cmd, capture_output=True)
        fc = f"[0:v]format=yuv420p,setsar=1[cg_in];{chain}"
        cmd2 = [
            "ffmpeg", "-y", "-hide_banner", "-v", "error",
            "-ss", str(preview_time), "-i", str(video), "-frames:v", "1",
            "-filter_complex", fc, "-map", "[cg_out]", str(preview_path.with_suffix(".graded.png"))
        ]
        subprocess.run(cmd2, capture_output=True)
        try:
            from PIL import Image
            orig = Image.open(str(preview_path.with_suffix(".orig.png")))
            graded = Image.open(str(preview_path.with_suffix(".graded.png")))
            w, h = orig.size
            ab = Image.new("RGB", (w * 2 + 4, h), (40, 40, 40))
            ab.paste(orig, (0, 0))
            ab.paste(graded, (w + 4, 0))
            ab.save(str(preview_path), quality=95)
            preview_path.with_suffix(".orig.png").unlink(missing_ok=True)
            preview_path.with_suffix(".graded.png").unlink(missing_ok=True)
            print(f"OK preview: {preview_path}")
        except ImportError:
            print(f"OK preview frames saved (install Pillow for side-by-side)")
        return None

    out = pathlib.Path(output) if output else video.with_name(f"{video.stem}_graded.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    fc = f"[0:v]format=yuv420p,setsar=1[cg_in];{chain}"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-v", "error",
        "-i", str(video),
        "-filter_complex", fc,
        "-map", "[cg_out]", "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", "-movflags", "+faststart", str(out)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:] + "\n")
        print(f"FAIL {out.name}: ffmpeg error")
        return None
    print(f"OK {out.name}")
    return out


def selftest():
    print("Selftest: generating test video and grading...")
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        src = td / "test.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=s=1080x1920:r=30:d=2",
            "-c:v", "libx264", "-preset", "ultrafast", str(src)
        ], check=True)
        out = td / "test_graded.mp4"
        for preset in PRESETS:
            result = apply_grade(src, out, preset=preset, protect_skin=False)
            if not result or not result.exists():
                print(f"SELFTEST FAIL: preset {preset}")
                return 1
            result.unlink()
        chain = grade_chain(preset="warm", protect_skin=True)
        if not chain or "[cg_out]" not in chain:
            print("SELFTEST FAIL: chain mode")
            return 1
        print("SELFTEST PASS")
        return 0


def main():
    p = argparse.ArgumentParser(description="Colour grading via ffmpeg filter chains")
    p.add_argument("video", nargs="?", help="Input MP4")
    p.add_argument("--preset", choices=list(PRESETS.keys()), help="Grade preset")
    p.add_argument("--lut", help="Path to .cube LUT file")
    p.add_argument("--brand", help="Brand slug (load default grade)")
    p.add_argument("--exposure", type=float, help="Brightness (-0.3 to +0.3)")
    p.add_argument("--contrast", type=float, help="Contrast (0.8 to 1.3)")
    p.add_argument("--saturation", type=float, help="Saturation (0.5 to 1.5)")
    p.add_argument("--temperature", type=float, help="White balance (-500 to +500 K)")
    p.add_argument("--protect-skin", action="store_true", help="Protect skin tones")
    p.add_argument("--preview", help="Save A/B preview PNG instead of grading")
    p.add_argument("--preview-time", type=float, default=5.0, help="Frame time for preview")
    p.add_argument("--output", help="Output path")
    p.add_argument("--chain", action="store_true", help="Print filter chain only")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        sys.exit(selftest())
    if a.chain:
        print(grade_chain(preset=a.preset, protect_skin=a.protect_skin, lut=a.lut,
                          brand=a.brand, exposure=a.exposure, contrast=a.contrast,
                          saturation=a.saturation, temperature=a.temperature))
        return
    if not a.video:
        p.error("need <video.mp4> (or --chain / --selftest)")

    video = pathlib.Path(a.video)
    apply_grade(video, a.output, preset=a.preset, protect_skin=a.protect_skin,
                lut=a.lut, brand=a.brand, exposure=a.exposure, contrast=a.contrast,
                saturation=a.saturation, temperature=a.temperature,
                preview=a.preview, preview_time=a.preview_time)


if __name__ == "__main__":
    main()
