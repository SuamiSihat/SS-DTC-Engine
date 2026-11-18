#!/usr/bin/env python3
"""Add micro-SFX and optional music beds to rendered video ads.

Usage:
  sound_design.py <video.mp4> <timeline.json> [--sfx-level -20] [--music path.mp3]
  sound_design.py --selftest
Needs ffmpeg on PATH. SFX library in assets/sfx/<category>/.
"""
import argparse, json, math, os, pathlib, random, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SFX_DIR = ROOT / "assets" / "sfx"
CATEGORIES = ("whoosh", "pop", "impact", "swipe", "ambient", "rise")
DEFAULT_LEVELS = {"whoosh": -20, "pop": -22, "impact": -18, "swipe": -22, "ambient": -28, "rise": -20}


def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


def pick_sfx(category):
    d = SFX_DIR / category
    if not d.is_dir():
        return None
    files = [f for f in d.iterdir() if f.suffix.lower() in (".wav", ".mp3", ".ogg", ".flac")]
    return random.choice(files) if files else None


def build_sfx_plan(timeline, sfx_level_offset=0):
    events = []
    overlays = timeline.get("layout", {}).get("overlays", [])
    for ov in overlays:
        kind = ov.get("kind", "overlay")
        t = ov.get("start", 0)
        if kind == "quote":
            events.append({"t": t, "cat": "pop", "label": f"quote popup @ {t:.1f}s"})
        elif kind in ("headline", "lower_third", "chip"):
            events.append({"t": t, "cat": "pop", "label": f"{kind} entrance @ {t:.1f}s"})
    items = timeline.get("items", [])
    for i, it in enumerate(items):
        if i > 0:
            events.append({"t": it["out_start"], "cat": "swipe", "label": f"segment cut @ {it['out_start']:.1f}s"})
    events.sort(key=lambda e: e["t"])
    filtered = []
    prev_t = -1.0
    for ev in events:
        if ev["t"] - prev_t >= 0.8:
            filtered.append(ev)
            prev_t = ev["t"]
    for ev in filtered:
        ev["level"] = DEFAULT_LEVELS.get(ev["cat"], -20) + sfx_level_offset
        ev["sfx"] = pick_sfx(ev["cat"])
    return filtered


def render_sfx(video, plan, output, music=None, music_level=-20, ducking_thresh=-30):
    if not plan and not music:
        print(f"SKIP {video.name}: no SFX events and no music")
        return None
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", str(video)]
    filter_parts = []
    input_idx = 1
    sfx_labels = []
    for i, ev in enumerate(plan):
        if ev["sfx"] is None:
            continue
        cmd += ["-i", str(ev["sfx"])]
        lab = f"sfx{i}"
        vol_db = ev["level"]
        delay_ms = max(0, int(ev["t"] * 1000))
        filter_parts.append(
            f"[{input_idx}:a]volume={vol_db}dB,adelay={delay_ms}|{delay_ms},apad=whole_dur=0.01[{lab}]"
        )
        sfx_labels.append(f"[{lab}]")
        input_idx += 1
    music_label = None
    if music:
        cmd += ["-i", str(music)]
        midx = input_idx
        input_idx += 1
        vid_dur = probe_duration(video)
        filter_parts.append(
            f"[{midx}:a]aloop=loop=-1:size=2e+09,atrim=0:{vid_dur:.3f},"
            f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(0, vid_dur - 2.0):.3f}:d=2.0,"
            f"volume={music_level}dB[mraw]"
        )
        filter_parts.append(
            "[0:a]aformat=channel_layouts=stereo[voice_sc]"
        )
        filter_parts.append(
            f"[mraw][voice_sc]sidechaincompress=threshold={ducking_thresh}dB:"
            "ratio=6:attack=0.01:release=0.5[mducked]"
        )
        music_label = "[mducked]"
    mix_inputs = ["[0:a]"] + sfx_labels
    if music_label:
        mix_inputs.append(music_label)
    n = len(mix_inputs)
    if n == 1 and not music:
        print(f"SKIP {video.name}: no usable SFX files found")
        return None
    mix_str = "".join(mix_inputs) + f"amix=inputs={n}:duration=first:dropout_transition=0[aout]"
    filter_parts.append(mix_str)
    cmd += ["-filter_complex", ";".join(filter_parts)]
    cmd += ["-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-movflags", "+faststart", str(output)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:] + "\n")
        print(f"FAIL {output.name}: ffmpeg error")
        return None
    return output


def selftest():
    print("Selftest: generating test tone...")
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        tone = td / "tone.wav"
        vid = td / "test.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "sine=frequency=440:duration=5", "-ar", "48000", str(tone)
        ], check=True)
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "color=c=black:s=1080x1920:d=5:r=30", "-i", str(tone),
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
            "-shortest", str(vid)
        ], check=True)
        tl = {"items": [{"out_start": 0, "dur": 2.5, "src": str(vid), "src_start": 0, "mode": "wide"},
                        {"out_start": 2.5, "dur": 2.5, "src": str(vid), "src_start": 2.5, "mode": "wide"}],
              "layout": {"overlays": [{"kind": "headline", "start": 1.0, "end": 3.0}]}}
        plan = build_sfx_plan(tl)
        print(f"  Plan: {len(plan)} events")
        for ev in plan:
            ev["sfx"] = tone
        out = td / "test_sfx.mp4"
        result = render_sfx(vid, plan, out)
        if result and result.exists():
            dur = probe_duration(result)
            ok = abs(dur - 5.0) < 0.5
            print(f"  Output duration: {dur:.2f}s")
            print(f"SELFTEST {'PASS' if ok else 'FAIL'}")
            return 0 if ok else 1
        print("SELFTEST FAIL: no output")
        return 1


def main():
    p = argparse.ArgumentParser(description="Add SFX and music to rendered video ads")
    p.add_argument("video", nargs="?", help="Input MP4")
    p.add_argument("timeline", nargs="?", help="Timeline JSON")
    p.add_argument("--sfx-level", type=int, default=0, help="Global SFX level offset in dB (e.g. -2)")
    p.add_argument("--music", type=str, default=None, help="Music bed file path")
    p.add_argument("--music-level", type=int, default=-20, help="Music level in dB")
    p.add_argument("--ducking-threshold", type=int, default=-30, help="Ducking threshold in dB")
    p.add_argument("--no-sfx", action="store_true", help="Skip SFX, music only")
    p.add_argument("--no-music", action="store_true", help="Skip music, SFX only")
    p.add_argument("--dry-run", action="store_true", help="Print plan without rendering")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.video or not a.timeline:
        p.error("need <video.mp4> and <timeline.json>")
    video = pathlib.Path(a.video)
    tl_path = pathlib.Path(a.timeline)
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    plan = [] if a.no_sfx else build_sfx_plan(tl, a.sfx_level)
    music = pathlib.Path(a.music) if a.music and not a.no_music else None
    if a.dry_run:
        print(f"SFX plan for {video.name}: {len(plan)} events")
        for ev in plan:
            sfx_name = ev["sfx"].name if ev["sfx"] else "(none)"
            print(f"  {ev['t']:6.2f}s  {ev['cat']:8s}  {ev['level']:+d} dB  {sfx_name}  {ev['label']}")
        if music:
            print(f"Music: {music.name} @ {a.music_level} dB, ducking @ {a.ducking_threshold} dB")
        return
    stem = video.stem
    out_dir = video.parent
    sfx_out = out_dir / f"{stem}_sfx.mp4"
    result = render_sfx(video, plan, sfx_out, music=music, music_level=a.music_level,
                        ducking_thresh=a.ducking_threshold)
    if result:
        sfx_count = sum(1 for ev in plan if ev["sfx"])
        has_music = "yes" if music else "no"
        print(f"OK {result.name}: {sfx_count} SFX events, music: {has_music}")
    if music:
        nomusic_out = out_dir / f"{stem}_nomusic.mp4"
        render_sfx(video, plan, nomusic_out, music=None)
        if nomusic_out.exists():
            print(f"OK {nomusic_out.name}: {sum(1 for ev in plan if ev['sfx'])} SFX events, music: no")


if __name__ == "__main__":
    main()
