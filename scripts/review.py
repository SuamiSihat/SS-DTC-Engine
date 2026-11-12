#!/usr/bin/env python3
"""Generate review packages for human sign-off.

Usage:
  review.py batches/<batch>/ --all
  review.py batches/<batch>/ --contact-sheet
  review.py batches/<batch>/ --html
  review.py batches/<batch>/ --watermark
  review.py --diff <v1.json> <v2.json>
Outputs to batches/<batch>/review/.
"""
import argparse, json, os, pathlib, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/poppins",
]


def _font(name, size):
    from PIL import ImageFont
    for d in FONT_DIRS:
        p = pathlib.Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


def extract_frame(video, time_s, output):
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", str(time_s),
         "-i", str(video), "-frames:v", "1", str(output)],
        capture_output=True,
    )
    return pathlib.Path(output).exists()


def find_renders(batch_dir):
    renders = batch_dir / "renders"
    if not renders.is_dir():
        renders = batch_dir
    mp4s = sorted(renders.rglob("*.mp4"))
    return [f for f in mp4s if "watermark" not in f.stem and "_sfx" not in f.stem]


def parse_qa(batch_dir):
    qa_dir = batch_dir / "qa"
    results = {}
    if not qa_dir.is_dir():
        return results
    for f in qa_dir.iterdir():
        if f.suffix in (".json", ".txt"):
            txt = f.read_text(encoding="utf-8", errors="replace")
            status = "PASS" if "PASS" in txt.upper() else "FAIL" if "FAIL" in txt.upper() else "?"
            results[f.stem] = status
    return results


def make_contact_sheet(batch_dir, output):
    from PIL import Image, ImageDraw
    renders = find_renders(batch_dir)
    if not renders:
        print("SKIP contact sheet: no renders found")
        return None
    import tempfile
    frames = []
    with tempfile.TemporaryDirectory() as td:
        for mp4 in renders:
            dur = probe_duration(mp4)
            t = dur * 0.33 if dur > 0 else 0
            fp = pathlib.Path(td) / f"{mp4.stem}.png"
            extract_frame(mp4, t, fp)
            if fp.exists():
                frames.append((mp4.stem, Image.open(fp)))
    if not frames:
        print("SKIP contact sheet: no frames extracted")
        return None
    thumb_w = 400
    cols = min(4, len(frames))
    rows = (len(frames) + cols - 1) // cols
    label_h = 50
    gap = 8
    # Compute thumb height from first frame aspect ratio
    sample = frames[0][1]
    ratio = sample.height / sample.width
    thumb_h = int(thumb_w * ratio)
    sheet_w = cols * thumb_w + (cols + 1) * gap
    sheet_h = rows * (thumb_h + label_h) + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    lfont = _font("Poppins-Regular.ttf", 18)
    for i, (name, img) in enumerate(frames):
        r, c = divmod(i, cols)
        t = img.copy()
        t.thumbnail((thumb_w, thumb_h))
        x = gap + c * (thumb_w + gap)
        y = gap + r * (thumb_h + label_h + gap)
        sheet.paste(t, (x, y))
        draw.text((x + 4, y + thumb_h + 2), name[:40], fill=(200, 200, 200), font=lfont)
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(output), quality=90)
    print(f"OK contact sheet: {len(frames)} frames -> {output}")
    return output


def make_review_html(batch_dir, output):
    renders = find_renders(batch_dir)
    qa = parse_qa(batch_dir)
    batch_name = batch_dir.name
    sections = []
    for mp4 in renders:
        name = mp4.stem
        dur = probe_duration(mp4)
        qa_status = qa.get(name, qa.get(f"sync_{name}", "?"))
        rel = mp4.relative_to(batch_dir) if mp4.is_relative_to(batch_dir) else mp4
        sections.append(f"""
    <div class="section">
      <h2>{name}</h2>
      <video controls width="480" src="{rel}"></video>
      <p>Duration: {dur:.1f}s | QA: <span class="badge {'pass' if qa_status=='PASS' else 'fail'}">{qa_status}</span></p>
      <details><summary>Comments</summary><textarea rows="3" cols="60"></textarea></details>
    </div>""")
    checklist = """
    <h2>Human Decisions Checklist</h2>
    <label><input type="checkbox"> Customer names blurred</label><br>
    <label><input type="checkbox"> Prices match prices.json and live site</label><br>
    <label><input type="checkbox"> Hook wording approved</label><br>
    <label><input type="checkbox"> Sound check (voice clear, SFX level OK)</label><br>
    <label><input type="checkbox"> Doctor consent on file</label><br>
    <label><input type="checkbox"> SS Clinic content mode confirmed</label><br>
    <label><input type="checkbox"> KKLIU number present (if KOL mode)</label><br>"""
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Review: {batch_name}</title>
<style>
  body {{ background: #1a1a1a; color: #eee; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
  .section {{ background: #222; padding: 16px; margin: 12px 0; border-radius: 8px; }}
  video {{ border-radius: 4px; }}
  .badge {{ padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
  .pass {{ background: #2a7a2a; }}
  .fail {{ background: #7a2a2a; }}
  textarea {{ width: 100%; background: #333; color: #eee; border: 1px solid #555; }}
  details {{ margin-top: 8px; }}
  label {{ display: block; margin: 4px 0; }}
</style></head><body>
<h1>Review: {batch_name}</h1>
{''.join(sections)}
{checklist}
</body></html>"""
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(output).write_text(html, encoding="utf-8")
    print(f"OK review HTML: {len(renders)} videos -> {output}")
    return output


def make_watermarked(batch_dir, output_dir):
    renders = find_renders(batch_dir)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_name = batch_dir.name
    count = 0
    for mp4 in renders:
        out = output_dir / f"{mp4.stem}_wm.mp4"
        vf = (f"drawtext=text='REVIEW COPY - {batch_name}':"
              "fontsize=36:fontcolor=white@0.3:x=(w-text_w)/2:y=(h-text_h)/2:"
              "borderw=1:bordercolor=black@0.2,"
              f"drawtext=text='REVIEW COPY - {batch_name}':"
              "fontsize=36:fontcolor=white@0.3:x=(w-text_w)/2-300:y=(h-text_h)/2-400:"
              "borderw=1:bordercolor=black@0.2,"
              "scale=-2:720")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error",
               "-i", str(mp4), "-vf", vf,
               "-c:v", "libx264", "-crf", "28", "-preset", "fast",
               "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            count += 1
        else:
            sys.stderr.write(f"FAIL watermark {mp4.name}: {r.stderr[-500:]}\n")
    print(f"OK watermarked: {count}/{len(renders)} -> {output_dir}")
    return count


def make_review_notes(batch_dir, output):
    renders = find_renders(batch_dir)
    qa = parse_qa(batch_dir)
    batch_name = batch_dir.name
    lines = [f"# Review Notes \u2014 {batch_name}\n", "## Human decisions required"]
    lines.append("- [ ] Customer names blurred in all review popups")
    lines.append("- [ ] Prices confirmed")
    lines.append("- [ ] Hook wording approved")
    lines.append("- [ ] Sound check: voice clear, music level OK")
    lines.append("- [ ] Doctor consent on file")
    lines.append("- [ ] SS Clinic mode: Educational / KOL confirmed")
    lines.append("- [ ] KKLIU number confirmed (KOL mode only)")
    lines.append("\n## QA results")
    for mp4 in renders:
        status = qa.get(mp4.stem, "?")
        lines.append(f"- {mp4.stem}: {status}")
    lines.append("\n## Comments\n(write here)\n")
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(output).write_text("\n".join(lines), encoding="utf-8")
    print(f"OK review notes -> {output}")
    return output


def run_diff(v1_path, v2_path):
    v1 = json.loads(pathlib.Path(v1_path).read_text(encoding="utf-8"))
    v2 = json.loads(pathlib.Path(v2_path).read_text(encoding="utf-8"))
    items1 = {it.get("src", f"seg{i}"): it for i, it in enumerate(v1.get("items", []))}
    items2 = {it.get("src", f"seg{i}"): it for i, it in enumerate(v2.get("items", []))}
    added = set(items2) - set(items1)
    removed = set(items1) - set(items2)
    common = set(items1) & set(items2)
    print(f"Segments: {len(items1)} -> {len(items2)}")
    if added:
        print(f"  Added: {', '.join(added)}")
    if removed:
        print(f"  Removed: {', '.join(removed)}")
    for k in sorted(common):
        d1, d2 = items1[k].get("dur", 0), items2[k].get("dur", 0)
        if abs(d1 - d2) > 0.01:
            print(f"  {k}: duration {d1:.2f}s -> {d2:.2f}s")
    ov1 = v1.get("layout", {}).get("overlays", [])
    ov2 = v2.get("layout", {}).get("overlays", [])
    if len(ov1) != len(ov2):
        print(f"Overlays: {len(ov1)} -> {len(ov2)}")


def main():
    p = argparse.ArgumentParser(description="Generate review packages")
    p.add_argument("batch_dir", nargs="?", help="Batch directory")
    p.add_argument("--contact-sheet", action="store_true")
    p.add_argument("--html", action="store_true")
    p.add_argument("--watermark", action="store_true")
    p.add_argument("--all", action="store_true")
    p.add_argument("--diff", nargs=2, metavar=("V1", "V2"), help="Diff two timeline JSONs")
    a = p.parse_args()
    if a.diff:
        run_diff(a.diff[0], a.diff[1])
        return
    if not a.batch_dir:
        p.error("need batch_dir or --diff")
    bd = pathlib.Path(a.batch_dir)
    review_dir = bd / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    if a.all or a.contact_sheet:
        make_contact_sheet(bd, review_dir / "contact_sheet.jpg")
    if a.all or a.html:
        make_review_html(bd, review_dir / "review.html")
    if a.all or a.watermark:
        make_watermarked(bd, review_dir / "watermarked")
    if a.all:
        make_review_notes(bd, review_dir / "review_notes.md")
    if not any([a.all, a.contact_sheet, a.html, a.watermark]):
        print("Specify --all, --contact-sheet, --html, or --watermark")


if __name__ == "__main__":
    main()
