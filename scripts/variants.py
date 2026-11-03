#!/usr/bin/env python3
"""Variant mode for render_batch.py: funnel x hook x style (skills/dtc-reels-editor/SKILL.md, Variant mode).

A clip in the batch spec may list up to 10 variants:
  {"id": "TOFU-B-energy", "funnel": "TOFU", "hook": "B", "style": "energy",
   "segments": [[s, e], ...],        # optional: the source ranges for THIS variant (default: the clip's segments)
   "product": "care_cream",          # brands with product_rules: which product's allowed styles apply
   "price_ref": "Alpha Starter (2 ring)",   # BOFU only: product name from brands/<slug>/prices.json
   "end_line": "...", "cta": "..."}  # optional close text (else funnel default / spec end_card)

check_plan() is the gate: it returns a list of BLOCK strings and never pads or invents variants.
Styles change framing and cut rhythm only. The speaker's audio and speech speed are never altered.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_VARIANTS = 10
FUNNEL_LEN = {"TOFU": (23.0, 30.0), "MOFU": (23.0, 30.0), "BOFU": (15.0, 20.0)}
HOOKS = {"A", "B", "C", "D"}
KNOWN_STYLES = {"clean", "energy", "story", "faceless"}
PUNCH_MIN = 4.0  # energy: split segments longer than this into a wide/tight pair at a word boundary


def brand_json(slug):
    return json.loads((ROOT / "brands" / slug / "brand.json").read_text(encoding="utf-8"))


def allowed_styles(slug, product=None):
    """Styles the brand/product lists in brand.json product_rules; 'clean' (today's default) if none listed."""
    pr = brand_json(slug).get("product_rules") or {}
    if product:
        return set(pr.get(product, {}).get("styles", ["clean"]))
    if pr:
        return set().union(*(set(v.get("styles", [])) for v in pr.values() if isinstance(v, dict))) or {"clean"}
    return {"clean"}


def price_names(slug):
    p = ROOT / "brands" / slug / "prices.json"
    if not p.exists():
        return None
    return [x["name"] for x in json.loads(p.read_text(encoding="utf-8")).get("products", [])]


def seg_len(segs, fps=30):
    return sum(max(1, round((e - s) * fps)) / fps for s, e in segs)


def check_plan(spec, clip, snap=None, words=None):
    """Gate the clip's variants. Returns (ok_variants, blocks)."""
    slug, mode = spec["brand"], spec.get("mode", "educational")
    vs = clip.get("variants") or []
    blocks, ok, seen = [], [], set()
    if len(vs) > MAX_VARIANTS:
        blocks.append(f"clip {clip['id']}: {len(vs)} variants, the cap is {MAX_VARIANTS}")
    for v in vs[:MAX_VARIANTS]:
        tag = f"clip {clip['id']} {v.get('id', '?')}"
        f, h, st = v.get("funnel"), v.get("hook"), v.get("style", "clean")
        bad = []
        if f not in FUNNEL_LEN:
            bad.append(f"funnel '{f}' must be TOFU, MOFU or BOFU")
        if h not in HOOKS:
            bad.append(f"hook '{h}' must be one of A, B, C, D")
        elif h in ("B", "C") and h not in clip.get("hooks", {}):
            bad.append(f"hook {h} has no entry in clip.hooks")
        elif h == "D":
            if slug == "ssclinic":
                bad.append("proof hook (D) is never used on SS Clinic")
            else:
                bad.append("proof hook (D) needs a real proof source; not built in render_batch.py yet")
        if st not in KNOWN_STYLES:
            bad.append(f"style '{st}' unknown")
        elif st == "faceless":
            bad.append("style 'faceless' needs the dtc-broll full-frame rule change first")
        elif st not in allowed_styles(slug, v.get("product")):
            bad.append(f"style '{st}' not allowed for {slug}{'/' + v['product'] if v.get('product') else ''} "
                       f"(allowed: {', '.join(sorted(allowed_styles(slug, v.get('product'))))})")
        if f == "BOFU":
            if slug == "ssclinic":
                bad.append("BOFU is never used on SS Clinic")
            names = price_names(slug)
            if not v.get("price_ref"):
                bad.append("BOFU needs price_ref (prices are never typed)")
            elif names is None or v["price_ref"] not in names:
                bad.append(f"price_ref '{v['price_ref']}' not in brands/{slug}/prices.json")
        if v.get("price") or v.get("offer"):
            bad.append("literal price/offer field: use price_ref")
        key = (f, h, st)
        if key in seen:
            bad.append(f"duplicate combination {f}/{h}/{st}")
        seen.add(key)
        segs = v.get("segments") or clip["segments"]
        if snap and words is not None:
            segs = [snap(words, s, e) for s, e in segs]
        if f in FUNNEL_LEN:
            lo, hi = FUNNEL_LEN[f]
            L = seg_len(segs, spec.get("fps", 30))
            if h == "B" and "B" in clip.get("hooks", {}):
                s, e = clip["hooks"]["B"]["segment"]
                L += e - s
            if not (lo - 0.5 <= L <= hi + 0.5):
                bad.append(f"{f} body is {L:.1f} s, must be {lo:.0f}-{hi:.0f} s (pick other segments; never pad)")
        if bad:
            blocks += [f"BLOCK {tag}: {b}" for b in bad]
        else:
            ok.append(dict(v, segments=segs))
    return ok, blocks


def style_modes(style, segs, words_between=None, words=None, opener=False):
    """Return [(s, e, mode)] for the body. Modes: wide | tight (split is set by hook C)."""
    out = []
    if style == "story":
        return [(s, e, "wide") for s, e in segs]
    if style == "energy":
        k = 0
        for s, e in segs:
            cut = None
            if e - s > PUNCH_MIN and words_between and words is not None:
                ws = words_between(words, s, e)
                mid = s + (e - s) / 2
                gaps = [w["e"] for w in ws if s + 1.5 < w["e"] < e - 1.5]
                if gaps:
                    cut = min(gaps, key=lambda x: abs(x - mid))
            parts = [(s, cut), (cut, e)] if cut else [(s, e)]
            for a, b in parts:
                out.append((a, b, ("wide", "tight")[k % 2]))
                k += 1
        return out
    return [(s, e, ("wide", "tight")[k % 2]) for k, (s, e) in enumerate(segs)]  # clean: today's rhythm


def close_text(spec, v):
    ec = spec["end_card"]
    if v.get("end_line") or v.get("cta"):
        return v.get("end_line", ec["line"]), v.get("cta", ec.get("cta", ""))
    if v["funnel"] == "BOFU":
        return ec["line"], ec.get("cta", "")
    return ec["line"], ("" if spec["brand"] == "ssclinic" else v.get("cta", ""))  # TOFU/MOFU: soft close, no price
