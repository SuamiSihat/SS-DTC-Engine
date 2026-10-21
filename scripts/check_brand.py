#!/usr/bin/env python3
"""Brand and claims gate. Run BEFORE rendering and again on final captions/hooks.

Usage:
  check_brand.py --brand drmitring --texts texts.txt [--doctor] [--json]
  texts.txt: one overlay/caption/hook line per line (or a .json list of strings).
Exit code: 0 = clean (REVIEW items still need a human), 1 = BLOCK found.

BLOCK  = term literally banned by the brand guideline, brand not allowed for ads,
         or doctor shown without a consent ref (when enforced).
REVIEW = inferred risky wording (e.g. Malay equivalents of banned claims). A person decides.
This is a keyword screen, not legal or regulatory review."""
import argparse, json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import policy_rules

def load_texts(p):
    p = pathlib.Path(p)
    if p.suffix == ".json":
        return [str(x) for x in json.loads(p.read_text(encoding="utf-8"))]
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def hit(term, text):
    t = term.strip().lower()
    if not t: return False
    return re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text.lower()) is not None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--texts")
    ap.add_argument("--doctor", nargs="?", const="", default=None, metavar="NAME", help="a doctor appears in the videos; give the doctor's name, e.g. --doctor \"Dr Amir\"")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-policy", action="store_true", help="skip the Meta / Malaysia keyword screen (policy_rules.py)")
    a = ap.parse_args()

    bp = ROOT / "brands" / a.brand / "brand.json"
    if not bp.exists():
        print(f"BLOCK unknown brand '{a.brand}' (no {bp})"); sys.exit(1)
    b = json.loads(bp.read_text(encoding="utf-8"))
    out = []  # (level, message)

    if not b.get("ads_allowed", True):
        out.append(("BLOCK", f"{b['name']} is not an advertisable product brand ({b.get('note','see guideline')})."))
    if a.doctor is not None:
        allowed = b.get("doctor_allowed_in_ads", "")
        appointed = [d.lower() for d in b.get("appointed_doctors", [])]
        if str(allowed).upper().startswith("NO"):
            out.append(("BLOCK", f"{b['name']} guideline: {allowed}"))
        elif b["gate"].get("require_appointed_doctor"):
            if not a.doctor.strip():
                out.append(("BLOCK", "Give the doctor's name: --doctor \"<name>\". Only SuamiSihat-appointed doctors may appear."))
            elif a.doctor.strip().lower() not in appointed:
                out.append(("BLOCK", f"'{a.doctor}' is not in appointed_doctors for {b['name']} ({', '.join(b.get('appointed_doctors', [])) or 'none listed'}). Only SuamiSihat-appointed doctors may appear."))
        else:
            snap_p = ROOT / "brands" / a.brand / "design-system-snapshot.json"
            snap = json.loads(snap_p.read_text(encoding="utf-8")) if snap_p.exists() else {}
            doc = snap.get("doctor") or {}
            ref = doc.get("consentRef") or b.get("doctor_consent_ref")
            if not snap:
                out.append(("REVIEW", "No design-system snapshot: run scripts/sync_brand_assets.py so doctor consent is read from the design system."))
            if b["gate"].get("enforce_doctor_consent", True) and not ref:
                out.append(("BLOCK", f"Doctor used but no written-consent reference (design-system status: {doc.get('status', 'unknown')}). Guideline: {allowed}"))
    if b.get("standing_notice"):
        out.append(("INFO", b["standing_notice"]))
    if str(b.get("claims_status", "")).startswith("TBC"):
        out.append(("REVIEW", f"Claims review is TBC for {b['name']}: every claim needs regulatory sign-off before publishing."))

    for t in (load_texts(a.texts) if a.texts else []):
        for term in b.get("banned_terms", []):
            if hit(term, t): out.append(("BLOCK", f"banned term '{term}' in: {t}"))
        for term in b.get("review_terms", []):
            if hit(term, t): out.append(("REVIEW", f"risky wording '{term}' in: {t}"))

    if not a.no_policy:
        btype = b.get("type", "product")
        for t in (load_texts(a.texts) if a.texts else []):
            for rid, why, m in policy_rules.scan(t, btype):
                out.append(("REVIEW", f"[policy:{rid}] '{m}' in: {t}\n         why: {why}"))
        if a.texts:
            out.append(("INFO", "Policy screen is a keyword check against skills/dtc-reels-editor/references/meta-policy.md (not legal advice). Ads on sexual or men's health products must be targeted 18+."))
        if btype == "service" and a.doctor is not None:
            out.append(("REVIEW", "Doctor-led ad for a clinic service: MAB services guideline 4.2 and the MMC guideline on dissemination of information limit promoting a practitioner. Brand owner and clinic compliance adviser must confirm."))

    if a.json:
        print(json.dumps([{"level": l, "msg": m} for l, m in out], indent=2, ensure_ascii=False))
    else:
        for l, m in out: print(f"{l}: {m}")
        print(f"\n{sum(l=='BLOCK' for l,_ in out)} BLOCK, {sum(l=='REVIEW' for l,_ in out)} REVIEW for brand '{a.brand}'.")
    sys.exit(1 if any(l == "BLOCK" for l, _ in out) else 0)

if __name__ == "__main__":
    main()
