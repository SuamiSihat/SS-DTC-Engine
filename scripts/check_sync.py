#!/usr/bin/env python3
"""Starter sync checker: estimates audio offset between a final video and the raw source
by cross-correlating 16 kHz mono audio. Needs ffmpeg on PATH, numpy, scipy.

Usage:
  check_sync.py final.mp4 raw.mp4 [--max-offset 0.04] [--max-search 5.0]
  check_sync.py --timeline renders/<name>.timeline.json [more.timeline.json ...] [--max-offset 0.04]
  check_sync.py --selftest
"""
import argparse, json, os, pathlib, subprocess, sys
import numpy as np
from scipy.signal import fftconvolve

SR = 16000

def load_audio(path, start_s=None, dur_s=None):
    cmd = ["ffmpeg", "-v", "error"]
    if start_s is not None and start_s > 0:
        cmd += ["-ss", f"{start_s:.4f}"]
    if dur_s is not None and dur_s > 0:
        cmd += ["-t", f"{dur_s:.4f}"]
    cmd += ["-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    data = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(data, dtype=np.float32)

def envelope(x, win=160):
    x = np.abs(x)
    k = np.ones(win) / win
    e = np.convolve(x, k, mode="same")[::win]
    return e - e.mean()

def best_offset(a, b, max_search_s):
    """Signed offset in seconds between a and b (sign shows direction; compare abs value to the limit)."""
    ea, eb = envelope(a), envelope(b)
    step = 160 / SR
    corr = fftconvolve(ea, eb[::-1], mode="full")
    lags = np.arange(-len(eb) + 1, len(ea)) * step
    m = np.abs(lags) <= max_search_s
    i = np.argmax(corr[m])
    return float(lags[m][i])

def check_timeline(tl_path, max_offset, max_search):
    tlp = pathlib.Path(tl_path)
    d = json.loads(tlp.read_text(encoding="utf-8"))
    mp4 = tlp.with_name(d["file"])
    if not mp4.exists():
        print(f"FAIL {tlp.name}: {mp4.name} not found")
        return False
    items = [it for it in d.get("items", []) if it.get("src") and it.get("dur", 0) >= 1.0]
    if not items:
        print(f"FAIL {tlp.name}: no clip segments >= 1.0s in timeline")
        return False
    worst = 0.0
    all_ok = True
    for idx, it in enumerate(items):
        dur = it["dur"]
        pad = min(0.5, max_search)
        src_s = max(0.0, it["src_start"] - pad)
        lead = it["src_start"] - src_s
        a_raw = load_audio(it["src"], start_s=src_s, dur_s=dur + pad * 2)
        a_fin = load_audio(mp4, start_s=it["out_start"], dur_s=dur)
        off = best_offset(a_raw, a_fin, max_search) - lead
        if abs(off) > abs(worst):
            worst = off
        if abs(off) > max_offset:
            all_ok = False
            print(f"  seg {idx+1} ({pathlib.Path(it['src']).name} @ {it['src_start']:.2f}s -> out {it['out_start']:.2f}s): FAIL offset {off:+.3f}s")
    status = "PASS" if all_ok else "FAIL"
    print(f"{status} {mp4.name} ({len(items)} segments): max offset {worst:+.3f}s (limit {max_offset}s)")
    return all_ok

def selftest():
    rng = np.random.default_rng(0)
    base = rng.standard_normal(SR * 12).astype(np.float32)
    base *= (np.sin(np.linspace(0, 60, base.size)) > 0).astype(np.float32)  # bursts
    results = []
    for shift in (0.0, 0.2, 2.0):
        s = int(shift * SR)
        shifted = np.concatenate([np.zeros(s, np.float32), base])[: base.size]
        off = best_offset(base, shifted, 5.0)
        results.append((shift, off))
        print(f"shift {shift:.2f}s -> measured {off:+.3f}s")
    ok = abs(results[0][1]) < 0.04 and abs(results[1][1]) > 0.1 and abs(results[2][1]) > 1.0
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1

def main():
    p = argparse.ArgumentParser()
    p.add_argument("args", nargs="*")
    p.add_argument("--timeline", nargs="+", help="one or more .timeline.json files")
    p.add_argument("--max-offset", type=float, default=0.04)
    p.add_argument("--max-search", type=float, default=5.0)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        sys.exit(selftest())
    tl_files = list(a.timeline or []) + [x for x in a.args if x.endswith(".timeline.json")]
    if tl_files:
        ok = all(check_timeline(f, a.max_offset, a.max_search) for f in tl_files)
        sys.exit(0 if ok else 1)
    if len(a.args) != 2:
        p.error("need final.mp4 and raw.mp4, or --timeline <file.timeline.json>")
    final, raw = a.args
    off = best_offset(load_audio(raw), load_audio(final), a.max_search)
    status = "PASS" if abs(off) <= a.max_offset else "FAIL"
    print(f"{status} {os.path.basename(final)}: offset {off:+.3f}s (limit {a.max_offset}s)")
    sys.exit(0 if status == "PASS" else 1)

if __name__ == "__main__":
    main()
