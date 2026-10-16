#!/usr/bin/env python3
"""Environment self-test. Run after setup. Reports what is missing; does not install anything."""
import shutil, importlib, subprocess, sys

def cmd_ok(name, args=("-version",)):
    p = shutil.which(name)
    if not p: return False, "not found on PATH"
    try:
        out = subprocess.run([name, *args], capture_output=True, text=True, timeout=20)
        return True, (out.stdout or out.stderr).splitlines()[0][:70] if (out.stdout or out.stderr) else p
    except Exception as e:
        return False, str(e)

def mod_ok(name):
    try:
        m = importlib.import_module(name); return True, getattr(m, "__version__", "ok")
    except Exception as e:
        return False, "missing"

checks = [
    ("ffmpeg", cmd_ok("ffmpeg")), ("ffprobe", cmd_ok("ffprobe")),
    ("node", cmd_ok("node", ("--version",))), ("git", cmd_ok("git", ("--version",))),
    ("numpy", mod_ok("numpy")), ("scipy", mod_ok("scipy")), ("cv2 (opencv)", mod_ok("cv2")),
    ("whisper (openai-whisper or faster_whisper)", mod_ok("whisper") if mod_ok("whisper")[0] else mod_ok("faster_whisper")),
    ("rembg (cutouts)", mod_ok("rembg")),
]
bad = 0
for name, (ok, info) in checks:
    print(f"{'OK  ' if ok else 'MISS'} {name}: {info}")
    bad += (not ok)
print("\nAll good." if not bad else f"\n{bad} item(s) missing. Fix them, or ask Claude Code to install them.")
sys.exit(1 if bad else 0)
