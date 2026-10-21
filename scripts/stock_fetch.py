#!/usr/bin/env python3
"""Royalty-free stock b-roll: search, download, import and track licences (see skills/dtc-broll, section 6).

A person always picks the clips. This script only finds candidates, rejects ones that break our rules,
keeps a licence record per clip and logs where each clip was used.

Sources with an API (free keys in config.env, never in git):
  pexels   PEXELS_API_KEY    Pexels License
  pixabay  PIXABAY_API_KEY   Pixabay Content License
Manual sources (download by hand, then `import`): coverr, mixkit.

Library: BROLL_LIBRARY in config.env (e.g. //Ssnas/drm/SS-DTC/broll-library). One folder per source;
each clip <source>-<id>.mp4 has a <source>-<id>.json licence record next to it.

Usage:
  python scripts/stock_fetch.py search "honey pouring" [--sources pexels,pixabay] [--n 6] [--min-dur 2] [--max-dur 12] [--sheet out.jpg]
  python scripts/stock_fetch.py import <folder>        # folder holds the clips + licenses.csv (see below)
  python scripts/stock_fetch.py list [--status ok]
  python scripts/stock_fetch.py use <clip_id> --batch <batch>   # copies into batches/<batch>/work/broll/ and logs the use
  python scripts/stock_fetch.py selftest               # offline test with generated clips and fake API replies

licenses.csv for `import` (one row per clip):
  file,source,url,license,ai_generated,notes
  sunrise.mp4,coverr,https://coverr.co/videos/...,Coverr License,no,
Accepted licences: see ALLOWED_LICENSES. Clips marked AI, Restricted, non-commercial or without a licence are rejected.
"""
import argparse, csv, datetime, json, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOWED_LICENSES = {
    "pexels": ["Pexels License", "CC0"],
    "pixabay": ["Pixabay Content License", "Pixabay License"],
    "coverr": ["Coverr License"],
    "mixkit": ["Mixkit Free License"],
}
BAD_LICENSE_WORDS = ("restricted", "non-commercial", "noncommercial", "personal use", "editorial")
MIN_SHORT_SIDE = 1080   # the final video is 1080x1920; b-roll is rendered at 1080 wide at most
FACE_MIN_FRAC = 0.08    # a detected face larger than 8% of the short side counts as identifiable
UA = "SS-DTC-Engine stock_fetch/1.0"

# ---------------- config
def read_env():
    env = {}
    p = ROOT / "config.env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    return env

def cfg(key, default=""):
    return os.environ.get(key) or read_env().get(key, default)

def library():
    lib = cfg("BROLL_LIBRARY")
    if not lib:
        sys.exit("BROLL_LIBRARY is not set. Add it to config.env (see config.example.env).")
    p = pathlib.Path(lib); p.mkdir(parents=True, exist_ok=True); return p

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# ---------------- HTTP (replaceable in selftest)
def http_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def http_download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)

# ---------------- source adapters -> list of candidate dicts
def pick_file(files):
    """files: list of (w, h, url). Smallest file whose short side is >= MIN_SHORT_SIDE."""
    ok = [f for f in files if f[2] and min(f[0], f[1]) >= MIN_SHORT_SIDE]
    return min(ok, key=lambda f: f[0] * f[1]) if ok else None

def search_pexels(q, n):
    key = cfg("PEXELS_API_KEY")
    if not key or key.startswith("PASTE"):
        print("pexels: PEXELS_API_KEY not set in config.env, skipped"); return []
    out = []
    for orient in ("portrait", "landscape"):
        url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": q, "orientation": orient, "per_page": n, "size": "medium"})
        for v in http_json(url, {"Authorization": key}).get("videos", []):
            f = pick_file([(x.get("width") or 0, x.get("height") or 0, x.get("link")) for x in v.get("video_files", []) if x.get("file_type", "video/mp4") == "video/mp4"])
            out.append({"source": "pexels", "id": str(v["id"]), "page_url": v.get("url", ""), "duration": v.get("duration", 0),
                        "creator": (v.get("user") or {}).get("name", ""), "creator_url": (v.get("user") or {}).get("url", ""),
                        "license": "Pexels License", "file": f, "orientation": orient})
    return out

def search_pixabay(q, n):
    key = cfg("PIXABAY_API_KEY")
    if not key or key.startswith("PASTE"):
        print("pixabay: PIXABAY_API_KEY not set in config.env, skipped"); return []
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": q, "per_page": max(3, min(200, n * 2)), "safesearch": "true"})
    out = []
    for v in http_json(url).get("hits", []):
        vids = v.get("videos") or {}
        f = pick_file([(x.get("width") or 0, x.get("height") or 0, x.get("url")) for x in vids.values()])
        w = h = 0
        if vids: w, h = max(((x.get("width") or 0, x.get("height") or 0) for x in vids.values()), key=lambda t: t[0] * t[1])
        out.append({"source": "pixabay", "id": str(v["id"]), "page_url": v.get("pageURL", ""), "duration": v.get("duration", 0),
                    "creator": v.get("user", ""), "creator_url": "", "license": "Pixabay Content License", "file": f,
                    "orientation": "portrait" if h > w else "landscape"})
    return out

ADAPTERS = {"pexels": search_pexels, "pixabay": search_pixabay}

# ---------------- checks
def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}"); s = (d.get("streams") or [{}])[0]
    return s.get("width", 0), s.get("height", 0), float((d.get("format") or {}).get("duration", 0) or 0)

def grab_frames(path, k=6):
    w, h, dur = probe(path)
    frames = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(k):
            t = dur * (i + 0.5) / k
            fp = pathlib.Path(td) / f"f{i}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=640:-2", str(fp)])
            if fp.exists(): frames.append(fp.read_bytes())
    return frames

def face_check(path):
    """'ok', 'face' or 'unchecked'. Conservative: any sizeable frontal or profile face fails."""
    try:
        import cv2, numpy as np
    except ImportError:
        return "unchecked"
    if not hasattr(cv2, "CascadeClassifier") or not hasattr(cv2, "data"):
        return "unchecked"  # OpenCV 5 moved Haar cascades out of the main package; a person checks instead
    casc = [cv2.CascadeClassifier(cv2.data.haarcascades + n) for n in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
    for b in grab_frames(path):
        img = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None: continue
        minside = int(min(img.shape[:2]) * FACE_MIN_FRAC)
        for c in casc:
            if len(c.detectMultiScale(img, scaleFactor=1.1, minNeighbors=6, minSize=(minside, minside))):
                return "face"
    return "ok"

def license_problem(source, lic, ai):
    l = (lic or "").strip()
    if not l: return "no licence recorded"
    if any(wd in l.lower() for wd in BAD_LICENSE_WORDS): return f"licence '{l}' is not cleared for ads"
    if l not in ALLOWED_LICENSES.get(source, []): return f"licence '{l}' is not in the accepted list for {source}"
    if str(ai).strip().lower() in ("yes", "y", "true", "1", "ai"): return "AI-generated clip (needs brief approval and budget; not accepted here)"
    return ""

# ---------------- library records
def rec_paths(lib, source, cid):
    d = lib / source; d.mkdir(parents=True, exist_ok=True)
    stem = f"{source}-{cid}"
    return d / f"{stem}.mp4", d / f"{stem}.json"

def finish_record(mp4, rec):
    w, h, dur = probe(mp4)
    rec.update({"width": w, "height": h, "duration": round(dur, 2)})
    problems = []
    if min(w, h) < MIN_SHORT_SIDE: problems.append(f"too small ({w}x{h}); need short side >= {MIN_SHORT_SIDE}")
    fc = face_check(mp4); rec["face_check"] = fc
    if fc == "face": problems.append("identifiable face detected (default rule: no faces in men's health b-roll)")
    rec["problems"] = problems
    rec["status"] = "rejected" if problems else ("needs_face_check" if fc == "unchecked" else "ok")
    return rec

def save(json_path, rec):
    json_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def load_all(lib):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(lib.glob("*/*.json"))]

# ---------------- contact sheet
def contact_sheet(recs, lib, out):
    from PIL import Image, ImageDraw
    cells = []
    for r in recs:
        fr = grab_frames(lib / r["source"] / r["file"], k=1)
        if not fr: continue
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t: t.write(fr[0])
        im = Image.open(t.name).convert("RGB"); im.thumbnail((360, 360)); os.unlink(t.name)
        cells.append((r, im))
    if not cells: return None
    cols = 4; cw, ch = 380, 420; rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    for i, (r, im) in enumerate(cells):
        x, y = (i % cols) * cw + 10, (i // cols) * ch + 10
        sheet.paste(im, (x, y))
        col = (120, 220, 120) if r["status"] == "ok" else (240, 200, 80) if r["status"] == "needs_face_check" else (240, 90, 90)
        d.text((x, y + 365), f"{r['clip_id']}  {r['duration']}s  {r['width']}x{r['height']}", fill=(230, 230, 230))
        d.text((x, y + 382), f"{r['status']}" + (f": {r['problems'][0][:40]}" if r["problems"] else ""), fill=col)
    out = pathlib.Path(out); out.parent.mkdir(parents=True, exist_ok=True); sheet.save(out, quality=88)
    return out

# ---------------- commands
def cmd_search(a):
    lib = library(); recs = []
    for src in [s.strip() for s in a.sources.split(",") if s.strip()]:
        if src not in ADAPTERS: print(f"unknown source '{src}' (API sources: {', '.join(ADAPTERS)})"); continue
        try:
            cands = ADAPTERS[src](a.query, a.n)
        except Exception as e:
            print(f"{src}: search failed: {e}"); continue
        kept = 0
        for c in cands:
            if kept >= a.n: break
            if not (a.min_dur <= (c["duration"] or 0) <= a.max_dur): continue
            if not c["file"]: print(f"{src}-{c['id']}: no file with short side >= {MIN_SHORT_SIDE}, skipped"); continue
            mp4, js = rec_paths(lib, src, c["id"])
            if js.exists():
                recs.append(json.loads(js.read_text(encoding="utf-8"))); kept += 1; continue
            try:
                http_download(c["file"][2], mp4)
            except Exception as e:
                print(f"{src}-{c['id']}: download failed: {e}"); continue
            rec = {"clip_id": f"{src}-{c['id']}", "source": src, "file": mp4.name, "page_url": c["page_url"],
                   "creator": c["creator"], "creator_url": c["creator_url"], "license": c["license"], "ai_generated": "no",
                   "query": a.query, "downloaded": now(), "used_in": [], "notes": ""}
            lp = license_problem(src, rec["license"], "no")
            rec = finish_record(mp4, rec)
            if lp: rec["problems"].append(lp); rec["status"] = "rejected"
            if rec["status"] == "rejected" and not a.keep_rejected: mp4.unlink(missing_ok=True); rec["file_deleted"] = True
            save(js, rec); recs.append(rec); kept += 1
            print(f"{rec['clip_id']}: {rec['status']}" + (f" ({'; '.join(rec['problems'])})" if rec["problems"] else ""))
    show = [r for r in recs if not r.get("file_deleted")]
    sheet = a.sheet or str(lib / "_sheets" / (re.sub(r"[^a-z0-9]+", "-", a.query.lower()).strip("-") + ".jpg"))
    if show:
        p = contact_sheet(show, lib, sheet); print("contact sheet:", p)
    print(f"{sum(r['status']=='ok' for r in recs)} ok, {sum(r['status']=='needs_face_check' for r in recs)} need a face check, "
          f"{sum(r['status']=='rejected' for r in recs)} rejected. A person picks; then run `use`.")

def cmd_import(a):
    lib = library(); folder = pathlib.Path(a.folder); lc = folder / "licenses.csv"
    if not lc.exists(): sys.exit(f"{lc} not found. Columns: file,source,url,license,ai_generated,notes")
    with open(lc, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        src = (row.get("source") or "").strip().lower(); fn = (row.get("file") or "").strip()
        p = folder / fn
        if src not in ALLOWED_LICENSES: print(f"{fn}: unknown source '{src}', skipped"); continue
        if not p.exists(): print(f"{fn}: file not found, skipped"); continue
        lp = license_problem(src, row.get("license"), row.get("ai_generated"))
        if lp: print(f"{fn}: REJECTED, {lp}"); continue
        if not (row.get("url") or "").strip(): print(f"{fn}: REJECTED, source page URL missing (needed as licence proof)"); continue
        cid = re.sub(r"[^a-z0-9]+", "-", (pathlib.Path(urllib.parse.urlparse(row["url"]).path).name or p.stem).lower()).strip("-")[:60] or p.stem
        mp4, js = rec_paths(lib, src, cid)
        if js.exists(): print(f"{fn}: already in library as {src}-{cid}"); continue
        shutil.copy2(p, mp4)
        rec = {"clip_id": f"{src}-{cid}", "source": src, "file": mp4.name, "page_url": row["url"].strip(), "creator": "",
               "creator_url": "", "license": row["license"].strip(), "ai_generated": (row.get("ai_generated") or "no").strip(),
               "query": "", "downloaded": now(), "used_in": [], "notes": (row.get("notes") or "").strip()}
        rec = finish_record(mp4, rec)
        if rec["status"] == "rejected" and not a.keep_rejected: mp4.unlink(missing_ok=True); rec["file_deleted"] = True
        save(js, rec)
        print(f"{rec['clip_id']}: {rec['status']}" + (f" ({'; '.join(rec['problems'])})" if rec["problems"] else ""))

def cmd_list(a):
    lib = library()
    for r in load_all(lib):
        if a.status and r["status"] != a.status: continue
        print(f"{r['clip_id']:<34} {r['status']:<17} {r.get('duration',0):>5}s {r.get('width',0)}x{r.get('height',0)}  used {len(r['used_in'])}x  {r['license']}  {r['page_url']}")

def cmd_use(a):
    lib = library(); src = a.clip_id.split("-", 1)[0]
    js = lib / src / f"{a.clip_id}.json"
    if not js.exists(): sys.exit(f"{a.clip_id} not in library")
    rec = json.loads(js.read_text(encoding="utf-8"))
    if rec["status"] != "ok" and not (rec["status"] == "needs_face_check" and a.face_checked_by):
        sys.exit(f"{a.clip_id} status is '{rec['status']}'. Only 'ok' clips can be used"
                 + ("; for needs_face_check pass --face-checked-by <name> after looking at it." if rec["status"] == "needs_face_check" else "."))
    if a.face_checked_by: rec["face_check"] = f"checked by {a.face_checked_by} {now()}"; rec["status"] = "ok"
    dest = ROOT / "batches" / a.batch / "work" / "broll"; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(lib / src / rec["file"], dest / rec["file"])
    prior = len(rec["used_in"])
    rec["used_in"].append({"batch": a.batch, "date": now()}); save(js, rec)
    print(f"copied to {dest / rec['file']}" + (f"  (NOTE: already used {prior}x; avoid overusing one clip)" if prior >= 2 else ""))

# ---------------- selftest (offline)
def selftest():
    global http_json, http_download
    td = pathlib.Path(tempfile.mkdtemp()); os.environ["BROLL_LIBRARY"] = str(td / "lib")
    os.environ["PEXELS_API_KEY"] = "test"; os.environ["PIXABAY_API_KEY"] = "test"
    def mk(name, w, h, d=4):
        p = td / name
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={w}x{h}:rate=30:duration={d}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", str(p)], check=True)
        return p
    good, small = mk("good.mp4", 1080, 1920), mk("small.mp4", 540, 960)
    def fake_json(url, headers=None):
        if "pexels" in url:
            if "landscape" in url: return {"videos": []}
            return {"videos": [
                {"id": 1, "url": "https://www.pexels.com/video/1/", "duration": 4, "user": {"name": "A", "url": "u"},
                 "video_files": [{"width": 1080, "height": 1920, "link": "file://good", "file_type": "video/mp4"},
                                 {"width": 540, "height": 960, "link": "file://small", "file_type": "video/mp4"}]},
                {"id": 2, "url": "https://www.pexels.com/video/2/", "duration": 4, "user": {"name": "B"},
                 "video_files": [{"width": 540, "height": 960, "link": "file://small", "file_type": "video/mp4"}]},
                {"id": 3, "url": "https://www.pexels.com/video/3/", "duration": 40, "user": {"name": "C"},
                 "video_files": [{"width": 1080, "height": 1920, "link": "file://good", "file_type": "video/mp4"}]}]}
        return {"hits": [{"id": 9, "pageURL": "https://pixabay.com/videos/x-9/", "duration": 4, "user": "D",
                          "videos": {"large": {"url": "file://good", "width": 1080, "height": 1920}, "small": {"url": "file://small", "width": 540, "height": 960}}}]}
    def fake_dl(url, dest): shutil.copy2(good if url.endswith("good") else small, dest)
    http_json, http_download = fake_json, fake_dl
    ns = argparse.Namespace(query="test honey", sources="pexels,pixabay", n=6, min_dur=2, max_dur=12, sheet=None, keep_rejected=False)
    cmd_search(ns)
    lib = pathlib.Path(os.environ["BROLL_LIBRARY"]); recs = {r["clip_id"]: r for r in load_all(lib)}
    assert recs["pexels-1"]["status"] in ("ok", "needs_face_check"), recs["pexels-1"]
    assert "pexels-2" not in recs and "pexels-3" not in recs, "low-res and too-long clips must be skipped"
    assert recs["pixabay-9"]["width"] == 1080
    imp = td / "manual"; imp.mkdir(); shutil.copy2(good, imp / "a.mp4"); shutil.copy2(good, imp / "b.mp4"); shutil.copy2(good, imp / "c.mp4")
    (imp / "licenses.csv").write_text("file,source,url,license,ai_generated,notes\n"
        "a.mp4,coverr,https://coverr.co/videos/sunrise-abc,Coverr License,no,\n"
        "b.mp4,coverr,https://coverr.co/videos/ai-xyz,Coverr License,yes,\n"
        "c.mp4,mixkit,https://mixkit.co/free-stock-video/r-1/,Mixkit Restricted License,no,\n", encoding="utf-8")
    cmd_import(argparse.Namespace(folder=str(imp), keep_rejected=False))
    recs = {r["clip_id"]: r for r in load_all(lib)}
    assert "coverr-sunrise-abc" in recs and "coverr-ai-xyz" not in recs and not any(k.startswith("mixkit") for k in recs), recs.keys()
    print("SELFTEST PASS:", ", ".join(f"{k}={v['status']}" for k, v in recs.items()))
    shutil.rmtree(td)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("query"); s.add_argument("--sources", default="pexels,pixabay")
    s.add_argument("--n", type=int, default=6, help="max clips kept per source"); s.add_argument("--min-dur", type=float, default=2)
    s.add_argument("--max-dur", type=float, default=12); s.add_argument("--sheet"); s.add_argument("--keep-rejected", action="store_true")
    i = sp.add_parser("import"); i.add_argument("folder"); i.add_argument("--keep-rejected", action="store_true")
    l = sp.add_parser("list"); l.add_argument("--status")
    u = sp.add_parser("use"); u.add_argument("clip_id"); u.add_argument("--batch", required=True); u.add_argument("--face-checked-by")
    sp.add_parser("selftest")
    a = ap.parse_args()
    {"search": cmd_search, "import": cmd_import, "list": cmd_list, "use": cmd_use, "selftest": lambda _: selftest()}[a.cmd](a)

if __name__ == "__main__":
    main()
