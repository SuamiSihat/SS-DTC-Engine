#!/usr/bin/env python3
"""Track speaker face centre (fx, fy in 0..1) every 0.5 s using OpenCV YuNet.

Usage:
  python scripts/face_track.py <video.mp4> <out_facetrack.json>
"""
import json, pathlib, subprocess, sys
import cv2, numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "face_detection_yunet_2026may.onnx"


def track_clip(src_path, out_path, step_s=0.5):
    src = pathlib.Path(src_path)
    tw, th = 360, 640
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (tw, th), 0.6, 0.3, 5000) if MODEL.exists() else None
    fps_val = 1.0 / step_s
    p = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(src),
        "-vf", f"fps={fps_val:.2f},scale={tw}:{th}",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"
    ], capture_output=True)
    frame_bytes = tw * th * 3
    buf = p.stdout or b""
    n_frames = len(buf) // frame_bytes
    ts, fxs, fys = [], [], []
    last_fx, last_fy = 0.50, 0.36
    for i in range(n_frames):
        raw = buf[i * frame_bytes:(i + 1) * frame_bytes]
        img = np.frombuffer(raw, np.uint8).reshape((th, tw, 3))
        fx, fy = last_fx, last_fy
        if det is not None:
            det.setInputSize((tw, th))
            _, faces = det.detect(img)
            if faces is not None and len(faces):
                valid = [f for f in faces if 0.20 <= (f[1] + f[3] * 0.5) / th <= 0.45]
                if valid:
                    best = max(valid, key=lambda f: f[2] * f[3])
                    fx = round(float((best[0] + best[2] * 0.5) / tw), 4)
                    fy = round(float((best[1] + best[3] * 0.5) / th), 4)
                    last_fx, last_fy = fx, fy
        ts.append(round(i * step_s, 2))
        fxs.append(fx)
        fys.append(fy)
    if not ts:
        ts, fxs, fys = [0.0], [0.50], [0.36]
    out = {"src": str(src), "t": ts, "fx": fxs, "fy": fys}
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--batch":
        import re
        out_dir = pathlib.Path(sys.argv[2])
        for c in sys.argv[3:]:
            m = re.search(r"(\d{4,})", pathlib.Path(c).stem)
            cid = m.group(1) if m else pathlib.Path(c).stem
            track_clip(c, out_dir / f"facetrack_{cid}.json")
        print(f"Tracked {len(sys.argv) - 3} clips -> {out_dir}")
        sys.exit(0)
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    track_clip(sys.argv[1], sys.argv[2])

