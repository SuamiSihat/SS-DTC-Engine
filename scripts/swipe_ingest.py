#!/usr/bin/env python3
"""Swipe library: turn Telegram swipe-file exports into a searchable, tagged reference library.

Commands:
  ingest <export_dir>   Read a Telegram Desktop HTML export (messages*.html + photos/ video_files/ ...),
                        copy media into the library, add new messages (existing IDs are kept as they are),
                        and auto-tag from the caption (tag_source = auto, needs review).
  sheets                Contact sheets for visual tagging/review: --from/--to ID range, --untagged, or filters.
  search                Filter by tags and caption text. --safe hides anything with a policy risk.
  show <id>             One record in full.
  tag <id> k=v,v ...    Set tags (values must exist in skills/swipe-library/taxonomy.json). --note "..." adds a note.
  refs <id> [<id> ...]  Print an 'inspired_by' block to paste into a batch brief.
  stats                 Counts per tag.

Library: SWIPE_LIBRARY in config.env (e.g. //Ssnas/drm/SS-DTC/swipe-library) or --library.
Layout:  <lib>/index.json (one record per message, keyed by Telegram message ID)
         <lib>/media/<id>_<n>.<ext>   <lib>/sheets/*.jpg
Examples:
  python scripts/swipe_ingest.py ingest "E:/Users/Haru/Downloads/Telegram Desktop/ChatExport_2026-10-22"
  python scripts/swipe_ingest.py search --format vs-stack --market kb-hardsell --safe
  python scripts/swipe_ingest.py tag 1189 format=research-paper-overlay,doctor-explainer funnel=mofu market=sj-t20-en
"""
import argparse, html, json, os, pathlib, re, shutil, sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
TAXONOMY = ROOT / "skills" / "swipe-library" / "taxonomy.json"
TAG_KEYS = ["format", "hook", "funnel", "market", "brand_fit", "policy_risk"]
MEDIA_DIRS = ("photos", "video_files", "files", "voice_messages", "round_video_messages", "stickers")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------- config ----------
def read_env():
    env = {}
    p = ROOT / "config.env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    return env

def library(arg=None):
    lib = arg or os.environ.get("SWIPE_LIBRARY") or read_env().get("SWIPE_LIBRARY")
    if not lib:
        sys.exit("SWIPE_LIBRARY is not set. Add it to config.env (see config.example.env) or pass --library.")
    p = pathlib.Path(lib)
    (p / "media").mkdir(parents=True, exist_ok=True)
    (p / "sheets").mkdir(exist_ok=True)
    return p

def load_index(lib):
    f = lib / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

def save_index(lib, idx):
    f = lib / "index.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(idx.items(), key=lambda kv: int(kv[0]))), ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)

def taxonomy():
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))

# ---------- Telegram HTML parsing ----------
MSG_RE = re.compile(r'<div class="message default clearfix( joined)?" id="message(\d+)">(.*?)(?=<div class="message (?:default|service)|\Z)', re.S)

def parse_export(export_dir):
    export_dir = pathlib.Path(export_dir)
    files = sorted(export_dir.glob("messages*.html"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 1))
    if not files:
        sys.exit(f"No messages*.html in {export_dir}")
    title, author, out = None, None, []
    for f in files:
        src = f.read_text(encoding="utf-8")
        if title is None:
            m = re.search(r'<div class="page_header">.*?<div class="text bold">\s*(.*?)\s*</div>', src, re.S)
            title = html.unescape(m.group(1)).strip() if m else export_dir.name
        for joined, mid, body in MSG_RE.findall(src):
            fm = re.search(r'<div class="from_name">\s*(.*?)\s*</div>', body, re.S)
            if fm:
                author = html.unescape(re.sub(r"<[^>]+>", "", fm.group(1))).strip()
            t = re.search(r'<div class="text">(.*?)</div>', body, re.S)
            raw = t.group(1) if t else ""
            links = [html.unescape(u) for u in re.findall(r'href="(https?://[^"]+)"', raw)]
            text = re.sub(r"<br\s*/?>", "\n", raw)
            text = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
            media = []
            for href in re.findall(r'href="([^"]+)"', body):
                if href.split("/")[0] in MEDIA_DIRS and not href.endswith("_thumb.jpg"):
                    media.append(href)
            d = re.search(r'title="(\d\d)\.(\d\d)\.(\d{4}) (\d\d:\d\d:\d\d)', body)
            date = f"{d.group(3)}-{d.group(2)}-{d.group(1)}T{d.group(4)}" if d else ""
            out.append({"id": mid, "date": date, "author": author, "note": text, "links": links,
                        "media_src": list(dict.fromkeys(media))})
    return title, out

# ---------- auto tags (first pass from the caption; a person or Claude confirms) ----------
AUTO = {
    "format": [
        (r"before.?(&|and)?.?af?te?r", "before-after"), (r"\bvs\b|versus|comparison|perbandingan|easy hard|\bmudah\b.*\bsusah\b", "vs-stack"),
        (r"problem.{0,15}solution|masalah.{0,20}solution", "problem-solution"), (r"carousel|slides|sliding", "carousel"),
        (r"infographic", "infographic"), (r"screenshot", "chat-screenshot"), (r"whatsapp blast|catalog", "whatsapp-blast"),
        (r"landing ?page", "landing-page"), (r"quiz|kuiz", "quiz-funnel"), (r"podcast", "podcast"),
        (r"whiteboard|conteng|lukis|handwritten|sketch", "whiteboard"), (r"research paper|journal", "research-paper-overlay"),
        (r"\bpov\b", "pov"), (r"3rd party|third party|shoulder", "third-party-view"), (r"candid", "candid"),
        (r"\bugc\b|paid review|testimoni", "ugc-review"), (r"animation|animasi", "animation"),
        (r"\bai\b|ai generated|sora|seedance|nano banana|generative|veo|kling", "ai-faceless"), (r"character", "ai-character"),
        (r"\bmeme\b", "meme"), (r"explainer|explaining|terangkan", "doctor-explainer"), (r"ranking", "ranking"),
        (r"\bemail\b", "email"), (r"packaging|kotak|bentuk chocolate", "packaging"), (r"booth|expo|pop ?up booth", "booth-event"),
        (r"b2b|investor|partner|dealer|distribut|franchis|hiring|\bhrd\b|licensing", "b2b"), (r"artikel|article", "article-style"),
        (r"question|soalan|q ?& ?a", "qa-format"), (r"poster|static", "static-poster"),
    ],
    "hook": [
        (r"imagine", "imagine-if"), (r"big words|technical|jargon|teknikal", "big-technical-word"), (r"public figure", "public-figure"),
        (r"merokok|vape|smok", "call-out"), (r"bukan salah|not your fault|normalkan", "not-your-fault"),
        (r"pattern interrupt", "pattern-interrupt"), (r"story ?telling|cerita", "story"), (r"humou?r|lawak|parody|babun", "humor"),
        (r"i use to depend|used to depend", "used-to-depend"), (r"fast forward", "fast-forward"),
    ],
    "funnel": [(r"\btofu\b", "tofu"), (r"retargeting|\bmofu\b|educat|explainer", "mofu"), (r"direct|hard ?sell|\bbofu\b|booking", "bofu"),
               (r"b2b|investor|dealer|distribut|franchis|hiring|\bhrd\b|partnership", "b2b")],
    "market": [(r"\bkb\b|kelantan|kota bharu", "kb-hardsell"), (r"\bt20\b|\bt10\b|english|longevity|stem ?cell|high earner|\bceo|leaders|sophisticated", "sj-t20-en"),
               (r"isteri|\bwife|wives", "wives"), (r"international|global", "international")],
    "brand_fit": [(r"\bdmr\b|mit ring", "drmitring"), (r"menss", "menss"), (r"rejal", "rejal"), (r"mensculine", "mensculine"),
                  (r"clinic|klinik|shockwave|p.?shots?\b|stem ?cell|screening", "ssclinic"), (r"\bapps?\b|ss tech|mfx", "ss-apps"),
                  (r"wellness|\bhrd\b|training", "ss-wellness"), (r"ecom|tiktok shop|marketplace", "ss-ecom")],
    "policy_risk": [(r"overclaim", "overclaim"), (r"talent as doctor|as real doctor", "fake-doctor"),
                    (r"prank|counterfeit|\bfake\b|clickbait", "deceptive"), (r"pornhub|uncensored|mencarut", "explicit")],
}

def auto_tags(note):
    t = " " + note.lower() + " "
    tags = {k: [] for k in TAG_KEYS}
    for k, rules in AUTO.items():
        for pat, val in rules:
            if re.search(pat, t) and val not in tags[k]:
                tags[k].append(val)
    if "ssclinic" in tags["brand_fit"]:
        if "before-after" in tags["format"]: tags["policy_risk"].append("before-after-clinic")
        if "ugc-review" in tags["format"]: tags["policy_risk"].append("testimonial-clinic")
    return tags

# ---------- commands ----------
def cmd_ingest(a):
    lib = library(a.library)
    idx = load_index(lib)
    title, msgs = parse_export(a.export_dir)
    src_root = pathlib.Path(a.export_dir)
    added = skipped = copied = 0
    for m in msgs:
        if not m["note"] and not m["media_src"]:
            continue  # empty service-like message
        if m["id"] in idx and not a.refresh_media:
            skipped += 1; continue
        media, kinds = [], []
        for n, rel in enumerate(m["media_src"]):
            sp = src_root / rel
            if not sp.exists():
                continue
            dst = lib / "media" / f"{m['id']}_{n}{sp.suffix.lower()}"
            if not dst.exists():
                shutil.copy2(sp, dst); copied += 1
            thumb = src_root / (rel + "_thumb.jpg")
            if thumb.exists() and not (lib / "media" / (dst.name + "_thumb.jpg")).exists():
                shutil.copy2(thumb, lib / "media" / (dst.name + "_thumb.jpg"))
            media.append(f"media/{dst.name}"); kinds.append(rel.split("/")[0])
        if m["id"] in idx:
            idx[m["id"]]["media"], idx[m["id"]]["media_kinds"] = media, kinds
            continue
        idx[m["id"]] = {"id": m["id"], "date": m["date"], "author": m["author"], "note": m["note"], "links": m["links"],
                        "media": media, "media_kinds": kinds, "source": title, "tags": auto_tags(m["note"]),
                        "tag_source": "auto", "reviewed": False, "notes": []}
        added += 1
    save_index(lib, idx)
    print(f"{title}: {len(msgs)} messages read, {added} added, {skipped} already in library, {copied} media files copied.")
    print(f"Library: {lib}  ({len(idx)} records). Auto tags are a first pass: review with 'sheets' + 'tag'.")

def match(r, a):
    for k in TAG_KEYS:
        want = getattr(a, k, None)
        if want and not set(want.split(",")) & set(r["tags"].get(k, [])):
            return False
    if getattr(a, "safe", False) and [x for x in r["tags"].get("policy_risk", []) if x != "none"]:
        return False
    if getattr(a, "text", None) and a.text.lower() not in r["note"].lower():
        return False
    if getattr(a, "untagged", False) and r.get("reviewed"):
        return False
    if getattr(a, "media_only", False) and not r["media"]:
        return False
    i = int(r["id"])
    if getattr(a, "from_id", None) and i < a.from_id: return False
    if getattr(a, "to_id", None) and i > a.to_id: return False
    return True

def short_tags(r):
    return " ".join(f"{k}={','.join(v)}" for k, v in r["tags"].items() if v)

def cmd_search(a):
    lib = library(a.library); idx = load_index(lib)
    hits = [r for r in idx.values() if match(r, a)]
    for r in hits[-a.limit:] if a.limit else hits:
        mark = "" if r.get("reviewed") else " (auto)"
        print(f"#{r['id']} {r['date'][:10]} [{len(r['media'])} media]{mark}  {short_tags(r)}")
        if r["note"]:
            print("    " + r["note"].replace("\n", " / ")[:160])
    print(f"\n{len(hits)} match(es).")

def cmd_show(a):
    lib = library(a.library); idx = load_index(lib)
    r = idx.get(str(a.id)) or sys.exit(f"#{a.id} not in library")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    for m in r["media"]:
        print("file:", lib / m)

def cmd_tag(a):
    lib = library(a.library); idx = load_index(lib); tx = taxonomy()
    r = idx.get(str(a.id)) or sys.exit(f"#{a.id} not in library")
    for kv in a.pairs:
        if "=" not in kv:
            sys.exit(f"Expected key=value, got '{kv}'")
        k, v = kv.split("=", 1)
        if k not in TAG_KEYS:
            sys.exit(f"Unknown tag key '{k}'. Keys: {', '.join(TAG_KEYS)}")
        vals = [x.strip() for x in v.split(",") if x.strip()]
        bad = [x for x in vals if x not in tx[k]]
        if bad:
            sys.exit(f"Not in taxonomy for {k}: {', '.join(bad)}. Add them to {TAXONOMY.relative_to(ROOT)} first.")
        r["tags"][k] = vals
    if a.note:
        r["notes"].append({"date": datetime.now().strftime("%Y-%m-%d"), "by": a.by, "text": a.note})
    r["tag_source"], r["reviewed"] = a.by, True
    save_index(lib, idx)
    print(f"#{r['id']}: {short_tags(r)}")

def cmd_refs(a):
    lib = library(a.library); idx = load_index(lib)
    print("## Inspired by (swipe library)")
    print("| Swipe | Format | Hook | What to take from it | Policy risk |")
    print("| --- | --- | --- | --- | --- |")
    for i in a.ids:
        r = idx.get(str(i))
        if not r:
            print(f"| #{i} | not in library |  |  |  |"); continue
        risk = ",".join(x for x in r["tags"]["policy_risk"] if x != "none") or "none"
        note = r["note"].replace("\n", " ").replace("|", "/")[:90]
        print(f"| #{i} | {','.join(r['tags']['format'])} | {','.join(r['tags']['hook'])} | {note} | {risk} |")
    print(f"\nMedia: {lib / 'media'}  (files start with the swipe ID)")

def cmd_stats(a):
    lib = library(a.library); idx = load_index(lib)
    from collections import Counter
    print(f"{len(idx)} records, {sum(r.get('reviewed', False) for r in idx.values())} reviewed, "
          f"{sum(len(r['media']) for r in idx.values())} media files.")
    for k in TAG_KEYS:
        c = Counter(v for r in idx.values() for v in r["tags"].get(k, []))
        print(f"\n{k}: " + ", ".join(f"{v} {n}" for v, n in c.most_common()))

def cmd_sheets(a):
    from PIL import Image, ImageDraw, ImageFont
    lib = library(a.library); idx = load_index(lib)
    items = []
    for r in idx.values():
        if not match(r, a):
            continue
        for m, kind in zip(r["media"], r["media_kinds"]):
            p = lib / m
            if kind == "photos": items.append((r, p))
            elif kind in ("video_files", "round_video_messages") and (lib / (m + "_thumb.jpg")).exists():
                items.append((r, lib / (m + "_thumb.jpg")))
    if not items:
        sys.exit("No images match.")
    cols, W, H, per = a.cols, 240, 340, a.per_sheet
    try:
        fnt = ImageFont.truetype("arial.ttf", 15)
    except Exception:
        fnt = ImageFont.load_default()
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    outs = []
    for s in range(0, len(items), per):
        chunk = items[s:s + per]; rows = (len(chunk) + cols - 1) // cols
        S = Image.new("RGB", (cols * W, rows * (H + 40)), "white"); d = ImageDraw.Draw(S)
        for i, (r, p) in enumerate(chunk):
            x, y = (i % cols) * W, (i // cols) * (H + 40)
            try:
                im = Image.open(p).convert("RGB"); im.thumbnail((W - 8, H - 8)); S.paste(im, (x + 4, y + 4))
            except Exception as e:
                d.text((x + 6, y + 6), f"unreadable: {e}", fill="red", font=fnt)
            lab = f"#{r['id']}" + ("" if r.get("reviewed") else " auto")
            d.text((x + 4, y + H), lab, fill=(200, 0, 0), font=fnt)
            d.text((x + 4, y + H + 18), ",".join(r["tags"]["format"])[:30], fill=(60, 60, 60), font=fnt)
        out = lib / "sheets" / f"sheet_{stamp}_{s // per + 1:02d}.jpg"
        S.save(out, quality=82); outs.append(out)
    print("\n".join(str(o) for o in outs))
    print(f"{len(items)} images on {len(outs)} sheet(s).")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--library")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest"); p.add_argument("export_dir"); p.add_argument("--refresh-media", action="store_true"); p.set_defaults(fn=cmd_ingest)
    def filters(p):
        for k in TAG_KEYS: p.add_argument("--" + k.replace("_", "-"), dest=k)
        p.add_argument("--text"); p.add_argument("--safe", action="store_true"); p.add_argument("--untagged", action="store_true")
        p.add_argument("--from", dest="from_id", type=int); p.add_argument("--to", dest="to_id", type=int)
        p.add_argument("--media-only", action="store_true")
    p = sub.add_parser("search"); filters(p); p.add_argument("--limit", type=int, default=0); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("sheets"); filters(p); p.add_argument("--cols", type=int, default=6); p.add_argument("--per-sheet", type=int, default=30); p.set_defaults(fn=cmd_sheets)
    p = sub.add_parser("show"); p.add_argument("id"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("tag"); p.add_argument("id"); p.add_argument("pairs", nargs="+"); p.add_argument("--note"); p.add_argument("--by", default="claude"); p.set_defaults(fn=cmd_tag)
    p = sub.add_parser("refs"); p.add_argument("ids", nargs="+"); p.set_defaults(fn=cmd_refs)
    p = sub.add_parser("stats"); p.set_defaults(fn=cmd_stats)
    a = ap.parse_args()
    a.fn(a)

if __name__ == "__main__":
    main()
