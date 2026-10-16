#!/usr/bin/env python3
"""Pull the latest brand assets and rules from the SuamiSihat Design System repo into brands/<slug>/.

Reads DESIGN_SYSTEM_ROOT from config.env (e.g. D:/HaNa_Innovation/ssDesignSystem) or --root.
Copies (never edits the source): logos/, pattern.svg, downloads/, metadata.json -> brands/<slug>/design-system/
and writes brands/<slug>/design-system-snapshot.json with the doctor block and consent status.
Also copies docs/claims-review/*.md to brands/_staff/ (staff-only; git-ignored).
check_brand.py reads the snapshot, so doctor consent has ONE source of truth: the design system.

Brand assets are under the SuamiSihat proprietary licence (LICENSE-ASSETS): internal/agency use only,
so copied assets stay out of git (see .gitignore). Re-run this before every batch: always use the latest files."""
import argparse, json, os, pathlib, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLUGS = ["drmitring", "mensculine", "menss", "pertabi", "rejal", "ssclinic"]

def read_env():
    env = {}
    p = ROOT / "config.env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    return env

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--out", help="override output root (default: repo root)")
    a = ap.parse_args()
    root = pathlib.Path(a.root or os.environ.get("DESIGN_SYSTEM_ROOT") or read_env().get("DESIGN_SYSTEM_ROOT", ""))
    out_root = pathlib.Path(a.out) if a.out else ROOT
    if not root.is_dir():
        sys.exit(f"DESIGN_SYSTEM_ROOT not found: '{root}'. Set it in config.env or pass --root.")
    products = root / "static" / "products"
    report = []
    for slug in SLUGS:
        src = products / slug
        dst = out_root / "brands" / slug
        (dst / "design-system").mkdir(parents=True, exist_ok=True)
        if not src.is_dir():
            report.append((slug, "MISSING in design system")); continue
        n = 0
        for sub in ("logos", "downloads"):
            if (src / sub).is_dir():
                shutil.copytree(src / sub, dst / "design-system" / sub, dirs_exist_ok=True)
                n += sum(1 for _ in (src / sub).rglob("*") if _.is_file())
        for f in ("pattern.svg", "metadata.json"):
            if (src / f).exists():
                shutil.copy2(src / f, dst / "design-system" / f); n += 1
        snap = {"slug": slug, "synced_from": str(root), "doctor": None, "claimsReview": None}
        mp = src / "metadata.json"
        if mp.exists():
            md = json.loads(mp.read_text(encoding="utf-8"))
            snap["doctor"] = md.get("doctor")
            snap["claimsReview"] = (md.get("definition") or {}).get("claimsReview")
            snap["avoid"] = (md.get("positioning") or {}).get("avoid")
        (dst / "design-system-snapshot.json").write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
        report.append((slug, f"{n} files, doctor status: {(snap['doctor'] or {}).get('status', 'n/a')}"))
    staff = out_root / "brands" / "_staff"; staff.mkdir(parents=True, exist_ok=True)
    cr = root / "docs" / "claims-review"
    if cr.is_dir():
        for f in cr.glob("*.md"): shutil.copy2(f, staff / f.name)
        report.append(("_staff", "claims-review notes copied (staff only)"))
    for slug, msg in report: print(f"{slug:12} {msg}")

if __name__ == "__main__":
    main()
