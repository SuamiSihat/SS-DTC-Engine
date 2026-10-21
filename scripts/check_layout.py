#!/usr/bin/env python3
"""Layout QA for a rendered ad: safe area, doctor's face, 1080x1920 output (see skills/dtc-broll).

Usage: python scripts/check_layout.py batches/<batch>/renders/<name>.timeline.json [more.timeline.json ...] [--facetrack work/facetrack_001.json]
Reads the layout recorded by render_batch.py and the face track from scripts/face_track.py.
Checks every overlay and the caption band every 0.25 s: inside the safe area, not on the face box.
Face box = the tracked face centre, about 400 px wide, 240 px above and 200 px below at wide framing (scaled for tight and card framing).
Exit code 1 if any file fails. Only reports what it checked; it does not replace watching the video.
"""
import json, pathlib, re, subprocess, sys

W, H = 1080, 1920
HW, UP, DOWN = 200, 240, 200
TIGHT = 1.22
CROP = 1 / TIGHT
X0, Y0 = (1 - CROP) * 0.5, (1 - CROP) * 0.05


def face_at(ft, t):
    ts = ft["t"]
    i = min(range(len(ts)), key=lambda k: abs(ts[k] - t))
    return ft["fx"][i], ft["fy"][i]


def face_box(mode, fx, fy, card):
    if mode == "tight":
        cx, cy, sc = (fx - X0) / CROP * W, (fy - Y0) / CROP * H, TIGHT
    elif mode == "split":
        cx0, cy0, cw, ch = card
        crop_frac = (1080 / 1920) * (ch / cw)
        cx, cy, sc = cx0 + fx * cw, cy0 + (fy - 0.03) / crop_frac * ch, cw / W
    else:
        cx, cy, sc = fx * W, fy * H, 1.0
    return (cx - HW * sc, cy - UP * sc, cx + HW * sc, cy + DOWN * sc)


def inter(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def main():
    args = sys.argv[1:]
    ftpath = None
    if "--facetrack" in args:
        i = args.index("--facetrack"); ftpath = pathlib.Path(args[i + 1]); del args[i:i + 2]
    if not args:
        print(__doc__); return 2
    bad = 0
    for tl in args:
        tlp = pathlib.Path(tl); d = json.loads(tlp.read_text(encoding="utf-8"))
        lay = d.get("layout")
        issues = []
        mp4 = tlp.with_name(d["file"])
        if mp4.exists():
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip()
            if r != f"{W},{H}": issues.append(f"output size {r}, must be {W},{H}")
        else:
            issues.append("mp4 not found, size not checked")
        if not lay:
            issues.append("no layout in timeline (render with the current render_batch.py)")
        else:
            sx0, sy0, sx1, sy1 = lay["safe"]
            rects = [(o["name"], (o["x"], o["y"], o["x"] + o["w"], o["y"] + o["h"]), o["start"], o["end"]) for o in lay["overlays"]]
            cb = lay["caption_band"]
            rects.append(("captions", tuple(cb), 0.0, d["total"]))
            for name, r, a, b in rects:
                if r[0] < sx0 or r[2] > sx1 or r[1] < sy0 or r[3] > sy1:
                    issues.append(f"{name}: outside the safe area {tuple(round(v) for v in r)}")
            items = [i for i in d["items"] if i.get("mode")]
            ft = None
            if ftpath is None and items:
                m = re.search(r"(\d+)$", pathlib.Path(items[0]["src"]).stem)
                cand = tlp.parent.parent / "work" / f"facetrack_{m.group(1)}.json" if m else None
                if cand and cand.exists(): ft = json.loads(cand.read_text(encoding="utf-8"))
            elif ftpath:
                ft = json.loads(ftpath.read_text(encoding="utf-8"))
            if ft is None:
                issues.append("no face track found, face overlap NOT checked (run scripts/face_track.py)")
            else:
                hits = {}
                t = 0.0
                while t < d["total"]:
                    it = next((i for i in items if i["out_start"] <= t < i["out_start"] + i["dur"]), None)
                    if it:
                        fx, fy = face_at(ft, it["src_start"] + (t - it["out_start"]))
                        fb = face_box(it["mode"], fx, fy, lay.get("card", [108, 480, 864, 860]))
                        for name, r, a, b in rects:
                            if a <= t <= b and not (name == "captions" and any(h0 <= t <= h1 for h0, h1 in lay.get("captions_hidden", []))):
                                if inter(r, fb):
                                    k = re.sub(r"_\d+\.png$", ".png", name)
                                    hits.setdefault(k, []).append(t)
                    t += 0.25
                for k, ts in hits.items():
                    issues.append(f"{k}: covers the face at {ts[0]:.2f}-{ts[-1]:.2f} s ({len(ts)} samples)")
        status = "PASS" if not [i for i in issues if not i.startswith(("mp4 not found", "no face track"))] else "FAIL"
        print(f"{status}  {tlp.name}")
        for i in issues: print("   -", i)
        if status == "FAIL": bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
