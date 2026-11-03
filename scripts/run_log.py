"""Run log for every batch: wall time per step, outputs per raw, Claude tokens.

Writes batches/<batch>/qa/run_log.json (git-ignored) and a readable RUN LOG.md
into the batch deliver folder (local, and the NAS one if given).

  python scripts/run_log.py start  <batch> --workflow reels|masterclass|static
  python scripts/run_log.py time   <batch> <label> -- <command ...>   # times one step
  python scripts/run_log.py end    <batch> [--deliver //Ssnas/drm/SS-DTC/deliver/<batch>] [--session <file.jsonl>]
  python scripts/run_log.py report                                   # all batches, averages

Tokens are read from Claude Code session logs (~/.claude/projects/<repo>*/*.jsonl)
inside the run's time window. Runs done in the Claude chat app keep no local
log, so tokens show as "not recorded".
"""
import argparse, datetime as dt, json, os, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
VIDEO = {".mp4", ".mov"}
IMAGE = {".png", ".jpg", ".jpeg"}
TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def now():
    return dt.datetime.now(dt.timezone.utc).astimezone()


def log_path(batch):
    p = ROOT / "batches" / batch / "qa" / "run_log.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load(batch):
    p = log_path(batch)
    if not p.exists():
        sys.exit(f"No run log for '{batch}'. Run: python scripts/run_log.py start {batch} --workflow ...")
    return json.loads(p.read_text(encoding="utf-8"))


def save(batch, d):
    log_path(batch).write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def git_commit():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
        return round(float(out), 1)
    except (OSError, ValueError):
        return None


def scan(folder):
    """Video and image files under a folder (skips work/cache folders)."""
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        return []
    items = []
    for f in sorted(folder.rglob("*")):
        ext = f.suffix.lower()
        if not f.is_file() or any(p in ("work", "_cache", "assets") for p in f.parts):
            continue
        if ext in VIDEO:
            items.append({"file": str(f.relative_to(folder)), "kind": "video",
                          "seconds": duration(f), "mb": round(f.stat().st_size / 1e6, 1)})
        elif ext in IMAGE and "review_sheet" not in f.name:
            items.append({"file": str(f.relative_to(folder)), "kind": "image",
                          "mb": round(f.stat().st_size / 1e6, 2)})
    return items


def fmt_s(sec):
    sec = int(round(sec or 0))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"


def session_dirs():
    base = pathlib.Path.home() / ".claude" / "projects"
    key = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT)).lower()
    if not base.is_dir():
        return []
    return [d for d in base.iterdir() if d.is_dir() and d.name.lower().startswith(key)]


def parse_ts(s):
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def tokens(t0, t1, files=None):
    """Sum Claude usage (deduplicated per message) between t0 and t1."""
    if files is None:
        files = [f for d in session_dirs() for f in d.rglob("*.jsonl")
                 if dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc) >= t0]
    total = {k: 0 for k in TOKEN_KEYS}
    seen, sessions, models = set(), set(), set()
    for f in files:
        for line in open(f, encoding="utf-8", errors="ignore"):
            if '"usage"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            ts = parse_ts(d.get("timestamp"))
            msg = d.get("message") or {}
            if not ts or not (t0 <= ts <= t1) or not isinstance(msg, dict) or not msg.get("usage"):
                continue
            mid = msg.get("id") or line[:120]
            if mid in seen:
                continue
            seen.add(mid)
            sessions.add(pathlib.Path(f).stem)
            if msg.get("model"):
                models.add(msg["model"])
            for k in TOKEN_KEYS:
                v = msg["usage"].get(k)
                if isinstance(v, int):
                    total[k] += v
    if not seen:
        return None
    total["turns"] = len(seen)
    total["sessions"] = sorted(sessions)
    total["models"] = sorted(models)
    return total


def cmd_start(a):
    raw_dir = pathlib.Path(a.raw) if a.raw else ROOT / "batches" / a.batch / "raw"
    raws = [r for r in scan(raw_dir) if r["kind"] == "video"]
    d = {"batch": a.batch, "workflow": a.workflow, "start": now().isoformat(timespec="seconds"),
         "commit": git_commit(), "host": os.environ.get("COMPUTERNAME", ""),
         "raw_dir": str(raw_dir), "raws": len(raws),
         "raw_seconds": round(sum(r["seconds"] or 0 for r in raws), 1), "steps": []}
    save(a.batch, d)
    print(f"run log started: {a.batch} ({a.workflow}), {d['raws']} raw clips, {fmt_s(d['raw_seconds'])} of footage")


def cmd_time(a):
    if not a.command:
        sys.exit("Give the command after --")
    d = load(a.batch)
    t = time.time()
    rc = subprocess.run(a.command).returncode
    sec = round(time.time() - t, 1)
    d["steps"].append({"label": a.label, "seconds": sec, "exit": rc,
                       "finished": now().isoformat(timespec="seconds")})
    save(a.batch, d)
    print(f"[run_log] {a.label}: {fmt_s(sec)} (exit {rc})")
    sys.exit(rc)


def cmd_end(a):
    d = load(a.batch)
    t0, t1 = dt.datetime.fromisoformat(d["start"]), now()
    d["end"] = t1.isoformat(timespec="seconds")
    d["wall_seconds"] = round((t1 - t0).total_seconds())
    out_dir = pathlib.Path(a.deliver) if a.deliver else ROOT / "batches" / a.batch / "deliver"
    if not scan(out_dir):
        out_dir = ROOT / "batches" / a.batch / "renders"
    outs = scan(out_dir)
    d["output_dir"] = str(out_dir)
    d["outputs"] = outs
    d["videos"] = sum(o["kind"] == "video" for o in outs)
    d["images"] = sum(o["kind"] == "image" for o in outs)
    d["tokens"] = tokens(t0, t1, [pathlib.Path(a.session)] if a.session else None)
    save(a.batch, d)
    md = summary_md(d)
    targets = [ROOT / "batches" / a.batch / "qa" / "RUN LOG.md"]
    if a.deliver:
        targets.append(pathlib.Path(a.deliver) / "RUN LOG.md")
    for p in targets:
        if p.parent.is_dir():
            p.write_text(md, encoding="utf-8")
    print(md)


def per_raw(d):
    n = d.get("raws") or 0
    return round(d.get("videos", 0) / n, 1) if n else None


def summary_md(d):
    tk = d.get("tokens")
    n_out = (d.get("videos") or 0) + (d.get("images") or 0)
    lines = [f"# Run log: {d['batch']}", "",
             f"- Workflow: {d['workflow']} | commit {d.get('commit') or '?'} | {d.get('host', '')}",
             f"- Start {d['start']} | end {d.get('end', '?')} | **total {fmt_s(d.get('wall_seconds'))}**",
             f"- Input: {d['raws']} raw clips, {fmt_s(d['raw_seconds'])} of footage",
             f"- Output: {d.get('videos', 0)} videos, {d.get('images', 0)} images"
             + (f" ({per_raw(d)} videos per raw clip)" if per_raw(d) else ""),
             "", "## Steps", "", "| Step | Time | Exit |", "|---|---|---|"]
    lines += [f"| {s['label']} | {fmt_s(s['seconds'])} | {s['exit']} |" for s in d["steps"]] or ["| (none timed) | | |"]
    lines += ["", "## Claude tokens", ""]
    if tk:
        lines += [f"- Turns: {tk['turns']} | sessions: {len(tk['sessions'])} | models: {', '.join(tk['models'])}",
                  f"- Output: {tk['output_tokens']:,} | fresh input: {tk['input_tokens']:,}",
                  f"- Cache write: {tk['cache_creation_input_tokens']:,} | cache read: {tk['cache_read_input_tokens']:,}"]
        if n_out:
            per = (tk["output_tokens"] + tk["input_tokens"] + tk["cache_creation_input_tokens"]) / n_out
            lines.append(f"- Per output file: ~{per:,.0f} output+input+cache-write, "
                         f"~{tk['cache_read_input_tokens'] / n_out:,.0f} cache read")
    else:
        lines.append("- Not recorded (run outside Claude Code, e.g. the chat app).")
    lines += ["", "## Outputs", "", "| File | Length | MB |", "|---|---|---|"]
    lines += [f"| {o['file']} | {o.get('seconds') or ''}{'s' if o.get('seconds') else ''} | {o['mb']} |"
              for o in d.get("outputs", [])]
    return "\n".join(lines) + "\n"


def cmd_report(a):
    rows = []
    for p in sorted((ROOT / "batches").glob("*/qa/run_log.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if "end" not in d:
            continue
        tk = d.get("tokens") or {}
        rows.append((d["batch"], d["workflow"], d["raws"], d.get("videos", 0), d.get("images", 0),
                     fmt_s(d.get("wall_seconds")), tk.get("output_tokens", "-"), tk.get("cache_read_input_tokens", "-")))
    if not rows:
        print("No finished run logs yet.")
        return
    print("| Batch | Workflow | Raws | Videos | Images | Time | Output tok | Cache read |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(f"{x:,}" if isinstance(x, int) else str(x) for x in r) + " |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("batch")
    s.add_argument("--workflow", required=True, choices=["reels", "masterclass", "static", "doctor-reel"])
    s.add_argument("--raw", help="raw footage folder (default batches/<batch>/raw)")
    t = sub.add_parser("time"); t.add_argument("batch"); t.add_argument("label")
    t.add_argument("command", nargs=argparse.REMAINDER)
    e = sub.add_parser("end"); e.add_argument("batch")
    e.add_argument("--deliver", help="deliver folder to scan and write RUN LOG.md into")
    e.add_argument("--session", help="a specific Claude Code session .jsonl to count")
    sub.add_parser("report")
    a = ap.parse_args()
    if a.cmd == "time" and a.command and a.command[0] == "--":
        a.command = a.command[1:]
    {"start": cmd_start, "time": cmd_time, "end": cmd_end, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
