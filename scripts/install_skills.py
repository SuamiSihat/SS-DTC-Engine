#!/usr/bin/env python3
"""Copy skills/ into .claude/skills/ so Claude Code loads them as project skills.
Run after cloning, and again after any change to skills/. Safe to re-run (overwrites copies)."""
import pathlib, shutil
ROOT = pathlib.Path(__file__).resolve().parent.parent
src, dst = ROOT / "skills", ROOT / ".claude" / "skills"
dst.mkdir(parents=True, exist_ok=True)
for d in sorted(p for p in src.iterdir() if p.is_dir()):
    shutil.copytree(d, dst / d.name, dirs_exist_ok=True)
    print("installed skill:", d.name)
print(f"\nSkills installed to {dst}. Restart Claude Code in this folder to load them.")
