#!/usr/bin/env python3
"""Suggest b-roll per sentence from the transcript (see skills/dtc-broll). Suggestions only; a person decides.

Usage: python scripts/broll_suggest.py batches/<batch>/work/spec.json [--only 001] [--product ring,mit]
Reads each clip's Whisper words JSON and kept segments, splits the kept speech into sentences, tags each one by simple Malay/English
keyword rules and writes work/broll_plan_<id>.md. It never writes claims, numbers or reviews: numbers must come from the brief or
prices.json, and a quote popup needs the real review text.
"""
import argparse, json, pathlib, re

RULES = [  # (type, keywords, suggestion)
    ("quote", r"\b(ulasan|review|testimoni|komen|feedback|mesej|pelanggan (kata|tulis|cakap)|dia (kata|tulis))\b", "Quote popup with the REAL review text (needs the source from the brief or proof folder, names blurred)"),
    ("myth", r"\b(mitos|fakta|betul ke|benarkah|myth|fact)\b", "Mitos / Fakta two-state card"),
    ("number", r"(\d|%|\b(peratus|ribu|juta|kali|bulan|minggu|tahun|hari|percent)\b)", "Number or chart card: use only figures given in the brief or prices.json"),
    ("steps", r"\b(langkah|cara|pertama|kedua|ketiga|kemudian|mula-mula|step|first|then)\b", "Animated step diagram"),
    ("concept", r"\b(saraf|darah|hormon|tekanan|stres|stress|tidur|aliran|otot|tenaga|nerve|blood|hormone|sleep)\b", "Abstract concept animation (scripts/scenes.py); no anatomy imagery"),
    ("metaphor", r"\b(seperti|ibarat|umpama|bagaikan)\b", "Metaphor visual: fruit metaphors only"),
]

def sentences(words):
    out, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > 0.6 or re.search(r"[.?!]$", cur[-1]["w"])):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--only"); ap.add_argument("--product", default="")
    a = ap.parse_args()
    spec_path = pathlib.Path(a.spec); spec = json.loads(spec_path.read_text(encoding="utf-8"))
    batch = spec_path.resolve().parent.parent if spec_path.parent.name == "work" else spec_path.resolve().parent
    prod = [p.strip().lower() for p in a.product.split(",") if p.strip()]
    rules = RULES + ([("product", r"\b(" + "|".join(map(re.escape, prod)) + r")\b", "Product shot or live-site b-roll")] if prod else [])
    for clip in spec["clips"]:
        if a.only and clip["id"] != a.only: continue
        wp = pathlib.Path(clip["words"]); wp = wp if wp.is_absolute() else batch / wp
        data = json.loads(wp.read_text(encoding="utf-8"))
        words = [{"w": w["word"].strip(), "s": w["start"], "e": w["end"]} for sg in data["segments"] for w in sg.get("words", [])]
        rows = []
        for s0, e0 in clip["segments"]:
            kept = [w for w in words if s0 <= (w["s"] + w["e"]) / 2 <= e0]
            for sent in sentences(kept):
                text = " ".join(w["w"] for w in sent); low = text.lower()
                hits = [(t, sug) for t, kw, sug in rules if re.search(kw, low)]
                rows.append((sent[0]["s"], sent[-1]["e"], text, hits))
        lines = [f"# B-roll suggestions, clip {clip['id']}", "", "Suggestions from keyword rules, not decisions. A person confirms each item. Source times in seconds.", "",
                 "| Source time | Sentence | Tag | Suggestion |", "|---|---|---|---|"]
        for s, e, text, hits in rows:
            if hits:
                lines.append(f"| {s:.1f}-{e:.1f} | {text} | {', '.join(t for t, _ in hits)} | {'; '.join(sg for _, sg in hits)} |")
            else:
                lines.append(f"| {s:.1f}-{e:.1f} | {text} | none | Keep the doctor on screen |")
        n = sum(1 for r in rows if r[3])
        lines += ["", f"{n} of {len(rows)} sentences have a suggestion. Density rule: about 3-5 items per 23-30 s master, 1.5-3 s each."]
        out = batch / "work" / f"broll_plan_{clip['id']}.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8"); print("wrote", out)

if __name__ == "__main__":
    main()
