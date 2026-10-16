#!/usr/bin/env python3
"""Starter sync checker: estimates audio offset between a final video and the raw source
by cross-correlating 16 kHz mono audio. Needs ffmpeg on PATH, numpy, scipy.

Usage:
  check_sync.py final.mp4 raw.mp4 [--max-offset 0.04] [--max-search 5.0]
  check_sync.py --selftest
Note: the final is usually a re-cut of the raw, so this finds the dominant alignment only.
Extend with per-segment checks for heavily cut videos."""
import argparse, subprocess, sys, tempfile, os
import numpy as np
from scipy.signal import fftconvolve

SR = 16000

def load_audio(path, max_s=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    if max_s: cmd[3:3] = ["-t", str(max_s)]
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
    p.add_argument("final", nargs="?"); p.add_argument("raw", nargs="?")
    p.add_argument("--max-offset", type=float, default=0.04)
    p.add_argument("--max-search", type=float, default=5.0)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest: sys.exit(selftest())
    if not (a.final and a.raw): p.error("need final and raw")
    off = best_offset(load_audio(a.raw), load_audio(a.final), a.max_search)
    status = "PASS" if abs(off) <= a.max_offset else "FAIL"
    print(f"{status} {os.path.basename(a.final)}: offset {off:+.3f}s (limit {a.max_offset}s)")
    sys.exit(0 if status == "PASS" else 1)

if __name__ == "__main__":
    main()
