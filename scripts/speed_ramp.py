#!/usr/bin/env python3
"""Add speed ramps to b-roll segments in video ads (ffmpeg setpts).

Usage:
  speed_ramp.py <video.mp4> <timeline.json> [--segments 2,4|broll] [--ramp-type punch-in]
  speed_ramp.py --chain --ramp-type punch-in --speed 1.3 --segment-dur 2.5
Never changes speaker footage or audio speed. Needs ffmpeg on PATH.
"""
import argparse, json, math, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

RAMP_DEFAULTS = {
    "punch-in":       {"speed": 1.3, "zone_start": 0.0, "zone_end": 0.3},
    "slow-reveal":    {"speed": 0.6, "zone_start": 0.25, "zone_end": 0.75},
    "snap-back":      {"speed": 1.5, "zone_start": 0.0, "zone_end": 1.0},
    "freeze-moment":  {"speed": 0.0, "freeze_dur": 0.4},
}


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return 3 * t * t - 2 * t * t * t


def build_setpts_expr(ramp_type, speed, segment_dur, freeze_at=None, freeze_dur=0.4):
    """Return an ffmpeg setpts expression for the given ramp type."""
    if ramp_type == "freeze-moment":
        ft = freeze_at if freeze_at is not None else segment_dur * 0.5
        return (
            f"if(between(T,{ft:.3f},{ft + freeze_dur:.3f}),"
            f"{ft:.3f}/TB,"
            f"if(gt(T,{ft + freeze_dur:.3f}),"
            f"(T-{freeze_dur:.3f})/TB,"
            f"PTS))"
        )
    if ramp_type == "punch-in":
        zone_end = segment_dur * 0.3
        inv = 1.0 / speed
        return (
            f"if(lt(T,{zone_end:.3f}),"
            f"PTS*{inv:.4f},"
            f"PTS*{inv:.4f}+PTS*(1-{inv:.4f})*smoothstep((T-{zone_end:.3f})/({segment_dur:.3f}-{zone_end:.3f})))"
        )
    if ramp_type == "slow-reveal":
        s1 = segment_dur * 0.25
        s2 = segment_dur * 0.75
        inv = 1.0 / speed
        return (
            f"if(lt(T,{s1:.3f}),PTS,"
            f"if(lt(T,{s2:.3f}),PTS*{inv:.4f},"
            f"PTS))"
        )
    if ramp_type == "snap-back":
        mid = segment_dur * 0.5
        inv = 1.0 / speed
        return (
            f"if(lt(T,{mid:.3f}),"
            f"PTS*{inv:.4f},"
            f"PTS*(2-{inv:.4f}))"
        )
    return "PTS"


def ramp_chain(ramp_type, speed=None, segment_dur=2.5, freeze_at=None, freeze_dur=0.4):
    """Return ffmpeg filter string for a speed ramp (for embedding in other scripts)."""
    cfg = dict(RAMP_DEFAULTS.get(ramp_type, {}))
    if speed is not None:
        cfg["speed"] = speed
    spd = cfg.get("speed", 1.3)
    expr = build_setpts_expr(ramp_type, spd, segment_dur, freeze_at, freeze_dur)
    return f"setpts={expr}"


def find_broll_segments(timeline):
    """Return indices of b-roll segments (not wide/tight speaker segments)."""
    items = timeline.get("items", [])
    indices = []
    for i, it in enumerate(items):
        mode = it.get("mode", "")
        if mode not in ("wide", "tight") and it.get("type", "") != "speaker":
            indices.append(i)
    return indices


def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


def apply_ramp(video, timeline, segments, ramp_type, speed, output,
               freeze_at=None, freeze_dur=0.4):
    """Apply speed ramps to specified segments of a rendered video."""
    items = timeline.get("items", [])
    if not items:
        print("SKIP: no items in timeline")
        return None

    cfg = dict(RAMP_DEFAULTS.get(ramp_type, {}))
    if speed is not None:
        cfg["speed"] = speed
    spd = cfg.get("speed", 1.3)

    filter_parts = []
    concat_inputs = []
    warnings = []

    for i, it in enumerate(items):
        seg_start = it.get("out_start", 0)
        seg_dur = it.get("dur", 0)
        label = f"seg{i}"

        if i in segments and seg_dur >= 1.0:
            expr = build_setpts_expr(ramp_type, spd, seg_dur, freeze_at, freeze_dur)
            filter_parts.append(
                f"[0:v]trim=start={seg_start:.3f}:duration={seg_dur:.3f},"
                f"setpts=PTS-STARTPTS,setpts={expr}[v{label}]"
            )
            filter_parts.append(
                f"[0:a]atrim=start={seg_start:.3f}:duration={seg_dur:.3f},"
                f"asetpts=PTS-STARTPTS[a{label}]"
            )
        elif i in segments and seg_dur < 1.0:
            warnings.append(f"WARN segment {i} too short ({seg_dur:.2f}s < 1.0s), skipping ramp")
            filter_parts.append(
                f"[0:v]trim=start={seg_start:.3f}:duration={seg_dur:.3f},"
                f"setpts=PTS-STARTPTS[v{label}]"
            )
            filter_parts.append(
                f"[0:a]atrim=start={seg_start:.3f}:duration={seg_dur:.3f},"
                f"asetpts=PTS-STARTPTS[a{label}]"
            )
        else:
            filter_parts.append(
                f"[0:v]trim=start={seg_start:.3f}:duration={seg_dur:.3f},"
                f"setpts=PTS-STARTPTS[v{label}]"
            )
            filter_parts.append(
                f"[0:a]atrim=start={seg_start:.3f}:duration={seg_dur:.3f},"
                f"asetpts=PTS-STARTPTS[a{label}]"
            )
        concat_inputs.append(f"[v{label}][a{label}]")

    n = len(items)
    filter_parts.append(
        "".join(concat_inputs) + f"concat=n={n}:v=1:a=1[vout][aout]"
    )

    for w in warnings:
        print(w)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-v", "error",
        "-i", str(video),
        "-filter_complex", ";".join(filter_parts),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(output)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:] + "\n")
        print(f"FAIL {output.name}: ffmpeg error")
        return None

    orig_dur = probe_duration(video)
    new_dur = probe_duration(output)
    delta = abs(new_dur - orig_dur)
    if delta > 0.3:
        print(f"WARN duration change {delta:.3f}s exceeds 0.3s limit")
    else:
        print(f"OK {output.name}: duration delta {delta:.3f}s")
    return output


def main():
    p = argparse.ArgumentParser(description="Add speed ramps to b-roll segments")
    p.add_argument("video", nargs="?", help="Input MP4")
    p.add_argument("timeline", nargs="?", help="Timeline JSON")
    p.add_argument("--segments", default="broll",
                   help="Segment indices (comma-sep) or 'broll' for auto-detect")
    p.add_argument("--ramp-type", default="punch-in",
                   choices=["punch-in", "slow-reveal", "snap-back", "freeze-moment"])
    p.add_argument("--speed", type=float, default=None, help="Override speed multiplier")
    p.add_argument("--freeze-at", type=float, default=None, help="Freeze time (s)")
    p.add_argument("--freeze-dur", type=float, default=0.4, help="Freeze duration (s)")
    p.add_argument("--output", type=str, default=None, help="Output path")
    p.add_argument("--dry-run", action="store_true", help="Print plan only")
    p.add_argument("--chain", action="store_true",
                   help="Output filter expression only (for render_batch.py)")
    p.add_argument("--segment-dur", type=float, default=2.5,
                   help="Segment duration for --chain mode")
    a = p.parse_args()

    if a.chain:
        chain = ramp_chain(a.ramp_type, a.speed, a.segment_dur, a.freeze_at, a.freeze_dur)
        print(chain)
        return

    if not a.video or not a.timeline:
        p.error("need <video.mp4> and <timeline.json>")

    video = pathlib.Path(a.video)
    tl = json.loads(pathlib.Path(a.timeline).read_text(encoding="utf-8"))
    items = tl.get("items", [])

    if a.segments == "broll":
        seg_indices = find_broll_segments(tl)
    else:
        seg_indices = [int(x) for x in a.segments.split(",")]

    if a.dry_run:
        print(f"Speed ramp plan for {video.name}:")
        print(f"  Type: {a.ramp_type}, speed: {a.speed or RAMP_DEFAULTS.get(a.ramp_type, {}).get('speed', '?')}")
        print(f"  Segments to ramp: {seg_indices}")
        for i in seg_indices:
            if i < len(items):
                it = items[i]
                dur = it.get("dur", 0)
                skip = " (SKIP < 1.0s)" if dur < 1.0 else ""
                print(f"    [{i}] {it.get('out_start', 0):.2f}s dur={dur:.2f}s "
                      f"mode={it.get('mode', '?')}{skip}")
        return

    output = pathlib.Path(a.output) if a.output else video.with_name(f"{video.stem}_ramped.mp4")
    apply_ramp(video, tl, set(seg_indices), a.ramp_type, a.speed, output,
               a.freeze_at, a.freeze_dur)


if __name__ == "__main__":
    main()
