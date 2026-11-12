#!/usr/bin/env python3
"""Smooth camera reframing using face tracking + ffmpeg crop.

Usage:
  auto_reframe.py <video.mp4> --face-track <json> --mode smooth-follow
  auto_reframe.py <video.mp4> --face-track <json> --mode portrait-convert --target-size 1080x1920
  auto_reframe.py <video.mp4> --face-track <json> --keyframes-out work/reframe.json
  auto_reframe.py <video.mp4> --face-track <json> --preview review/preview.png --preview-time 5.0
  auto_reframe.py --chain --face-track <json> --mode smooth-follow --target-size 1080x1920
  auto_reframe.py --selftest
Needs ffmpeg on PATH. Optional: numpy, scipy (cubic spline).
"""
import argparse, json, math, pathlib, subprocess, sys, tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
FPS = 30

MODE_DEFAULTS = {
    "smooth-follow":    {"max_pan": 0.05, "zoom_lo": 1.0, "zoom_hi": 1.3, "smooth_win": 2.0},
    "dynamic":          {"max_pan": 0.15, "zoom_lo": 1.0, "zoom_hi": 1.5, "smooth_win": 1.0},
    "lock":             {"max_pan": 0.0,  "zoom_lo": 1.0, "zoom_hi": 1.0, "smooth_win": 999},
    "portrait-convert": {"max_pan": 0.05, "zoom_lo": 1.5, "zoom_hi": 2.0, "smooth_win": 2.0},
}


def probe_video(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,duration,r_frame_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    info = json.loads(r.stdout)["streams"][0]
    w, h = int(info["width"]), int(info["height"])
    dur = float(info.get("duration", 0))
    return w, h, dur


def load_face_track(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return data["t"], data["fx"], data["fy"]


def interpolate_to_fps(ts, fxs, fys, duration):
    """Cubic-spline interpolate face positions to 30 fps frames."""
    n_frames = max(1, int(duration * FPS))
    frame_ts = [i / FPS for i in range(n_frames)]
    try:
        from scipy.interpolate import CubicSpline
        cs_x = CubicSpline(ts, fxs, extrapolate=True)
        cs_y = CubicSpline(ts, fys, extrapolate=True)
        return frame_ts, cs_x(frame_ts).tolist(), cs_y(frame_ts).tolist()
    except ImportError:
        pass
    # Fallback: linear interpolation
    def lerp_arr(xs_in, ts_in, ts_out):
        out = []
        for t in ts_out:
            if t <= ts_in[0]:
                out.append(xs_in[0])
            elif t >= ts_in[-1]:
                out.append(xs_in[-1])
            else:
                for j in range(len(ts_in) - 1):
                    if ts_in[j] <= t <= ts_in[j + 1]:
                        frac = (t - ts_in[j]) / (ts_in[j + 1] - ts_in[j])
                        out.append(xs_in[j] + frac * (xs_in[j + 1] - xs_in[j]))
                        break
        return out
    return frame_ts, lerp_arr(fxs, ts, frame_ts), lerp_arr(fys, ts, frame_ts)


def smooth_positions(vals, window_frames):
    """Moving average smoothing."""
    if window_frames < 2:
        return vals
    out = []
    half = window_frames // 2
    for i in range(len(vals)):
        lo = max(0, i - half)
        hi = min(len(vals), i + half + 1)
        out.append(sum(vals[lo:hi]) / (hi - lo))
    return out


def clamp_speed(vals, max_delta):
    """Limit per-frame change to max_delta."""
    out = [vals[0]]
    for i in range(1, len(vals)):
        d = vals[i] - out[-1]
        d = max(-max_delta, min(max_delta, d))
        out.append(out[-1] + d)
    return out


def compute_zoom(fxs, fys, mode_cfg):
    zlo, zhi = mode_cfg["zoom_lo"], mode_cfg["zoom_hi"]
    if zlo == zhi:
        return [zlo] * len(fxs)
    zooms = []
    for i in range(len(fxs)):
        if i == 0:
            motion = 0.0
        else:
            motion = math.sqrt((fxs[i] - fxs[i-1])**2 + (fys[i] - fys[i-1])**2)
        t = max(0.0, min(1.0, 1.0 - motion * FPS * 5))
        zooms.append(zlo + t * (zhi - zlo))
    zooms = smooth_positions(zooms, FPS * 2)
    return zooms


def compute_keyframes(src_w, src_h, fxs_s, fys_s, zooms, target_w, target_h):
    tar = target_w / target_h
    kfs = []
    for i in range(len(fxs_s)):
        z = zooms[i]
        cw = int(src_w / z)
        ch = int(cw / tar)
        if ch > src_h / z:
            ch = int(src_h / z)
            cw = int(ch * tar)
        cx = int(fxs_s[i] * src_w - cw / 2)
        cy = int(fys_s[i] * src_h - ch / 2)
        cx = max(0, min(src_w - cw, cx))
        cy = max(0, min(src_h - ch, cy))
        kfs.append({"t": round(i / FPS, 4), "x": cx, "y": cy,
                    "w": cw, "h": ch, "zoom": round(z, 3)})
    return kfs


def reframe_chain(face_track, mode="smooth-follow", target_w=1080, target_h=1920,
                  src_w=1920, src_h=1080, duration=10.0, product_events=None):
    """Return ffmpeg crop filter string for render_batch.py integration."""
    ts, fxs, fys = load_face_track(face_track)
    cfg = MODE_DEFAULTS[mode]
    frame_ts, fx_i, fy_i = interpolate_to_fps(ts, fxs, fys, duration)
    win = int(cfg["smooth_win"] * FPS)
    fx_s = clamp_speed(smooth_positions(fx_i, win), cfg["max_pan"] / FPS)
    fy_s = clamp_speed(smooth_positions(fy_i, win), cfg["max_pan"] / FPS)
    zooms = compute_zoom(fx_s, fy_s, cfg)
    if product_events:
        for ev in product_events:
            t0 = ev.get("t", 0)
            tz = ev.get("target_zoom", 1.75)
            ed = ev.get("ease_dur", 0.6)
            for i, ft in enumerate(frame_ts):
                if abs(ft - t0) < ed:
                    frac = 1.0 - abs(ft - t0) / ed
                    zooms[i] = max(zooms[i], zooms[i] + (tz - zooms[i]) * frac)
    kfs = compute_keyframes(src_w, src_h, fx_s, fy_s, zooms, target_w, target_h)
    if not kfs:
        return f"crop={target_w}:{target_h}:0:0,scale={target_w}:{target_h}"
    kf0 = kfs[0]
    return f"crop={kf0['w']}:{kf0['h']}:{kf0['x']}:{kf0['y']},scale={target_w}:{target_h}"


def render_reframe(video, face_track, mode, target_w, target_h, output,
                   product_events=None):
    src_w, src_h, dur = probe_video(video)
    ts, fxs, fys = load_face_track(face_track)
    cfg = MODE_DEFAULTS[mode]
    frame_ts, fx_i, fy_i = interpolate_to_fps(ts, fxs, fys, dur)
    win = int(cfg["smooth_win"] * FPS)
    fx_s = clamp_speed(smooth_positions(fx_i, win), cfg["max_pan"] / FPS)
    fy_s = clamp_speed(smooth_positions(fy_i, win), cfg["max_pan"] / FPS)
    zooms = compute_zoom(fx_s, fy_s, cfg)
    if product_events:
        for ev in product_events:
            t0, tz, ed = ev.get("t", 0), ev.get("target_zoom", 1.75), ev.get("ease_dur", 0.6)
            for i, ft in enumerate(frame_ts):
                if abs(ft - t0) < ed:
                    frac = 1.0 - abs(ft - t0) / ed
                    zooms[i] = max(zooms[i], zooms[i] + (tz - zooms[i]) * frac)
    kfs = compute_keyframes(src_w, src_h, fx_s, fy_s, zooms, target_w, target_h)
    return kfs, dur


def render_video(video, kfs, target_w, target_h, output):
    """Render reframed video using median keyframe as a static crop (fast path)."""
    mid = kfs[len(kfs) // 2]
    vf = f"crop={mid['w']}:{mid['h']}:{mid['x']}:{mid['y']},scale={target_w}:{target_h}"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error",
           "-i", str(video), "-vf", vf,
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-c:a", "copy", "-movflags", "+faststart", str(output)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-2000:] + "\n")
        return None
    return output


def render_preview(video, kfs, preview_time, output):
    idx = min(int(preview_time * FPS), len(kfs) - 1)
    kf = kfs[idx]
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(preview_time),
           "-i", str(video), "-frames:v", "1", tmp_path]
    subprocess.run(cmd, capture_output=True)
    try:
        from PIL import Image, ImageDraw
        im = Image.open(tmp_path)
        draw = ImageDraw.Draw(im)
        draw.rectangle([kf["x"], kf["y"], kf["x"] + kf["w"], kf["y"] + kf["h"]],
                        outline="lime", width=3)
        pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
        im.save(output)
    except ImportError:
        pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(tmp_path).rename(output)
    return output


def selftest():
    print("Selftest: auto_reframe...")
    fake_track = {"src": "test", "t": [0, 0.5, 1.0, 1.5, 2.0],
                  "fx": [0.5, 0.52, 0.48, 0.51, 0.50],
                  "fy": [0.36, 0.35, 0.37, 0.36, 0.36]}
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        ft = td / "ft.json"
        ft.write_text(json.dumps(fake_track), encoding="utf-8")
        chain = reframe_chain(str(ft), mode="smooth-follow",
                              src_w=1920, src_h=1080, duration=2.0)
        assert "crop=" in chain, f"Bad chain: {chain}"
        ts, fxs, fys = load_face_track(str(ft))
        frame_ts, fx_i, fy_i = interpolate_to_fps(ts, fxs, fys, 2.0)
        assert len(frame_ts) == 60, f"Expected 60 frames, got {len(frame_ts)}"
        print(f"  Chain: {chain[:80]}...")
        print(f"  Frames: {len(frame_ts)}")
    print("SELFTEST PASS")
    return 0


def main():
    p = argparse.ArgumentParser(description="Smooth camera reframing with face tracking")
    p.add_argument("video", nargs="?", help="Input video")
    p.add_argument("--face-track", default=None, help="Face track JSON")
    p.add_argument("--mode", default="smooth-follow", choices=MODE_DEFAULTS.keys())
    p.add_argument("--target-size", default="1080x1920", help="WxH")
    p.add_argument("--keyframes-out", help="Export keyframes JSON")
    p.add_argument("--preview", help="Preview output image")
    p.add_argument("--preview-time", type=float, default=5.0)
    p.add_argument("--product-events", help="JSON with product-raise events")
    p.add_argument("--chain", action="store_true", help="Print ffmpeg filter chain only")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        sys.exit(selftest())
    tw, th = [int(x) for x in a.target_size.split("x")]
    pevt = None
    if a.product_events:
        pevt = json.loads(pathlib.Path(a.product_events).read_text(encoding="utf-8"))
    if a.chain:
        if not a.face_track:
            p.error("--chain requires --face-track")
        print(reframe_chain(a.face_track, a.mode, tw, th, duration=30.0,
                            product_events=pevt))
        return
    if not a.video:
        p.error("need <video> unless --chain or --selftest")
    if not a.face_track:
        p.error("--face-track is required")
    video = pathlib.Path(a.video)
    kfs, dur = render_reframe(video, a.face_track, a.mode, tw, th, None, pevt)
    if a.keyframes_out:
        out = pathlib.Path(a.keyframes_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(kfs[:300], indent=2), encoding="utf-8")
        print(f"OK {len(kfs)} keyframes -> {out}")
    if a.preview:
        render_preview(video, kfs, a.preview_time, a.preview)
        print(f"OK preview -> {a.preview}")
    if not a.keyframes_out and not a.preview:
        out = video.with_name(video.stem + "_reframed.mp4")
        result = render_video(video, kfs, tw, th, out)
        if result:
            print(f"OK {out.name}: {len(kfs)} frames, mode={a.mode}")
        else:
            print(f"FAIL reframe {video.name}")
            sys.exit(1)


if __name__ == "__main__":
    main()
