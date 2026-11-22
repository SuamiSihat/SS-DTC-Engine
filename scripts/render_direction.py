#!/usr/bin/env python3
"""Direction / wayfinding video: route footage + TTS voice-over + step panels + captions + end card.

Usage:
  render_direction.py batches/<batch>/work/direction_spec.json [--formats 16x9,9x16,wa] [--tts-only] [--plan-only]
Steps (cached in work/): edge-tts VO per shot, vidstab on the source, then per format: one segment per shot,
concat, audio = source ambience at 1x (low, same in-point as the picture) + VO, loudnorm -16 LUFS.
Optional spec "music": {"path", "start", "rel_db" (under VO, default -9), "duck_threshold", "duck_ratio"} adds a
VO-ducked bed and also writes renders/<stem>_<fmt>_nomusic.mp4 (same picture, no music).
Writes renders/<stem>_<fmt>.mp4 + .timeline.json (layout for check_layout.py, items for check_sync.py).
The VO text is sent to Microsoft's online TTS service (edge-tts); only the script lines leave the machine.
Optional spec "tts": {"engine": "azure" | "elevenlabs", ...} uses Azure AI Speech or ElevenLabs instead (see tts_engines.py;
needs that provider's key in the environment). Optional spec "accent": "#RRGGBB" replaces the gold accent colour.
"""
import argparse, asyncio, json, pathlib, re, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import direction_gfx as G
import tts_engines as T

FPS = 30


def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        print("FAIL:", " ".join(map(str, cmd))[:400]); print(r.stderr[-2000:]); sys.exit(1)
    return r.stdout


def dur_of(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).strip())


# ---------------- TTS
async def _tts(text, voice, rate, mp3, pitch="+0Hz", words=False):
    """edge-tts to mp3. Returns sentence times; with words=True also word times (sentences rebuilt from the words)."""
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary" if words else "SentenceBoundary")
    sents = []
    with open(mp3, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"].endswith("Boundary"):
                sents.append([ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7, ch["text"]])
    if not words:
        return sents
    ws, out, k = sents, [], 0
    for s in [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]:
        n = len(s.split()); grp = ws[k:k + n] or ws[-1:]; k += n
        out.append([grp[0][0], grp[-1][1], s])
    return out, ws


def tts_all(spec, work, lines=None, sub="tts"):
    d = work / sub; d.mkdir(exist_ok=True)
    if lines is None:
        lines = [(f"vo_{i:02d}", s["vo"]) for i, s in enumerate(spec["shots"]) if s.get("vo")]
        lines.append(("vo_end", spec["endcard"]["vo"]))
    cfg = spec.get("tts") or {"engine": "edge"}
    cloud = cfg.get("engine") in ("elevenlabs", "azure")
    out = {}
    for key, text in lines:
        say = text
        for k, v in spec.get("say_replace", {}).items():
            say = say.replace(k, v)
        mp3, meta = d / f"{key}.mp3", d / f"{key}.json"
        want = {"say": say, "tts": cfg} if cloud else {"say": say, "voice": spec["voice"], "rate": spec.get("rate", "+0%")}
        if not cloud and (cfg.get("pitch") or cfg.get("words")):  # extra keys only when used, so older caches stay valid
            want.update(pitch=cfg.get("pitch", "+0Hz"), words=bool(cfg.get("words")))
        m = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        if not mp3.exists() or {k: m.get(k) for k in want} != want:
            if cloud:
                sents, words = T.synth(cfg["engine"], say, cfg, mp3)
                m = dict(want, sents=sents, say_words=words)
            elif want.get("words"):
                sents, words = asyncio.run(_tts(say, spec["voice"], want["rate"], mp3, want["pitch"], words=True))
                m = dict(want, sents=sents, say_words=words)
            else:
                m = dict(want, sents=asyncio.run(_tts(say, spec["voice"], want["rate"], mp3, want.get("pitch", "+0Hz"))))
            if m.get("say_words"):  # cut the trailing silence the engine adds (edge-tts: about 1 s) so shots stay tight
                end = m["say_words"][-1][1] + 0.15
                if dur_of(mp3) - end > 0.2:
                    tmp = mp3.with_suffix(".trim.mp3")
                    run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-t", f"{end:.3f}", "-af", "afade=t=out:st=%.3f:d=0.08" % (end - 0.08),
                         "-c:a", "libmp3lame", "-q:a", "2", tmp])
                    tmp.replace(mp3)
            m["dur"] = dur_of(mp3)
            meta.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
        sw = m.get("say_words") or [[a, b, w] for a, b, s in m["sents"] for w in s.split()]
        out[key] = dict(m, text=text, mp3=mp3, words=T.map_words(text, sw, m["dur"]))
    who = {"elevenlabs": f"ElevenLabs {cfg.get('voice_id')} ({cfg.get('model', T.DEFAULT_MODEL)})",
           "azure": f"Azure {cfg.get('voice')}"}.get(cfg.get("engine"), f"{spec.get('voice')} {spec.get('rate', '+0%')} {cfg.get('pitch', '')}".strip())
    print(f"TTS: {len(out)} lines, {sum(v['dur'] for v in out.values()):.1f}s of voice ({who})")
    return out


def chunks(text, sents, dur, maxc=56):
    """Caption chunks (start, end, text) relative to VO start, from displayed text and TTS sentence times."""
    disp = [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]
    if len(sents) == len(disp):
        times = [(a, b) for a, b, _ in sents]
    else:
        tot, t, times = sum(map(len, disp)), 0.0, []
        for s in disp:
            l = dur * len(s) / tot; times.append((t, t + l)); t += l
    out = []
    for s, (a, b) in zip(disp, times):
        parts = [s]
        if len(s) > maxc:
            cs = [m.start() for m in re.finditer(r", ", s)]
            if cs:
                i = min(cs, key=lambda c: abs(c - len(s) / 2)); parts = [s[:i + 1], s[i + 2:]]
            else:
                w = s.split(); parts = [" ".join(w[:len(w) // 2]), " ".join(w[len(w) // 2:])]
        tot, t = sum(map(len, parts)), a
        for p in parts:
            l = (b - a) * len(p) / tot; out.append([t, t + l, p]); t += l
    for i in range(len(out) - 1):
        out[i][1] = out[i + 1][0]
    if out:
        out[-1][1] += 0.35
    return out


# ---------------- stabilise + plan
def stabilise(spec, bd):
    st = spec.get("stabilise") or {}
    out = bd / "work" / "stab.mp4"
    if out.exists():
        return out
    src = spec["source"]
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"vidstabdetect=shakiness={st.get('shakiness', 5)}:accuracy=15:result=work/stab.trf",
         "-f", "null", "-"], cwd=bd)
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf",
         f"vidstabtransform=input=work/stab.trf:smoothing={st.get('smoothing', 15)}:zoom={st.get('zoom', 5)}:optzoom=0:interpol=bicubic",
         "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-an", "work/stab.mp4"], cwd=bd)
    print("stabilised ->", out.name)
    return out


def plan(spec, vo):
    t, items = 0.0, []
    for i, s in enumerate(spec["shots"]):
        src_len, fr = s["out"] - s["in"], s.get("freeze", 0.0)
        base = src_len / s["speed"] + fr if "speed" in s else s["plan"]
        v = vo.get(f"vo_{i:02d}")
        dur = round(max(base, v["dur"] + spec.get("vo_pad", 0.65)) if v else base, 3)
        pic = dur - fr; speed = src_len / pic; pad = 0.0
        if speed < 1:
            speed, pad = 1.0, pic - src_len
        items.append(dict(s, idx=i, out_start=round(t, 3), dur=dur, speed=round(speed, 4), pad=round(pad, 3), freeze=fr,
                          vo=v, vo_at=0.2))
        t += dur
    ev = vo["vo_end"]; ed = round(max(spec["endcard"].get("plan", 6), ev["dur"] + 1.6), 3)
    end = dict(idx="end", out_start=round(t, 3), dur=ed, vo=ev, vo_at=0.6)
    return items, end, round(t + ed, 3)


def timeline(name, size, total, items, end, raw_abs, layout):
    tl = [{"type": "clip", "mode": "broll", "src": raw_abs, "src_start": it["in"], "out_start": it["out_start"], "dur": it["dur"],
           "speed": it["speed"], "note": "picture sped up; ambience audio at 1x from src_start"} for it in items]
    tl.append({"type": "card", "name": "endcard", "out_start": end["out_start"], "dur": end["dur"]})
    vo = [{"line": it["vo"]["text"], "start": round(it["out_start"] + it["vo_at"], 3), "dur": round(it["vo"]["dur"], 3),
           "shot_end": round(it["out_start"] + it["dur"], 3), "mp3": str(pathlib.Path(it["vo"]["mp3"]).resolve())}
          for it in items + [end] if it.get("vo")]
    return {"file": name, "size": list(size), "total": total, "items": tl, "vo": vo, "layout": layout}


def main():
    import direction_segments as S
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--formats", default="16x9,9x16,wa")
    ap.add_argument("--tts-only", action="store_true")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--ambience-stem", action="store_true", help="QA: write renders/<stem>_ambience_only.m4a + timeline (no VO) for check_sync --timeline")
    a = ap.parse_args()
    sp = pathlib.Path(a.spec).resolve(); bd = sp.parent.parent; work = bd / "work"
    spec = json.loads(sp.read_text(encoding="utf-8"))
    if spec.get("accent"):
        G.set_accent(spec["accent"])
    raw_abs = str((bd / spec["source"]).resolve())
    vo = tts_all(spec, work, sub=spec.get("tts_dir", "tts"))
    if a.tts_only:
        return
    items, end, total = plan(spec, vo)
    (work / "plan.json").write_text(json.dumps({"total": total, "shots": [{k: it[k] for k in ("idx", "in", "out", "out_start", "dur", "speed", "pad")}
                                                for it in items], "end": {k: end[k] for k in ("out_start", "dur")}}, indent=1), encoding="utf-8")
    print(f"plan: {len(items)} shots + end card, total {total:.1f}s (work/plan.json)")
    if a.plan_only:
        return
    if a.ambience_stem:
        rd = bd / "qa"; rd.mkdir(exist_ok=True)
        mix = S.build_audio(spec, bd, [dict(it, vo=None) for it in items], dict(end, vo=None), total)
        stem = rd / f"{spec['out_stem']}_ambience_only.m4a"; mix.replace(stem)
        stem.with_suffix(".timeline.json").write_text(json.dumps(timeline(stem.name, (0, 0), total, items, end, raw_abs, None), indent=1, ensure_ascii=False), encoding="utf-8")
        print("OK", stem.name)
        return
    stab = stabilise(spec, bd)
    mix = S.build_audio(spec, bd, items, end, total, music=bool(spec.get("music")))
    dry = S.build_audio(spec, bd, items, end, total, out_name="mix_nomusic.m4a") if spec.get("music") else None
    rd = bd / "renders"; rd.mkdir(exist_ok=True)
    fmts = a.formats.split(",")
    for fmt in [f for f in ("16x9", "9x16") if f in fmts or (f == "9x16" and "wa" in fmts)]:
        vid, layout = S.render_format(fmt, spec, bd, stab, items, end, chunks)
        out = rd / f"{spec['out_stem']}_{fmt}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "20",
             "-preset", "slow", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest",
             "-movflags", "+faststart", out])
        size = G.LAYOUT[fmt]["size"]
        out.with_suffix(".timeline.json").write_text(json.dumps(timeline(out.name, size, total, items, end, raw_abs, layout), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"OK {out.name} {size[0]}x{size[1]} {dur_of(out):.1f}s")
        if dry:  # same picture, VO + ambience only (sound-design rule: deliver with and without music)
            nm = rd / f"{spec['out_stem']}_{fmt}_nomusic.mp4"
            run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", dry, "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest",
                 "-movflags", "+faststart", nm])
            nm.with_suffix(".timeline.json").write_text(json.dumps(timeline(nm.name, size, total, items, end, raw_abs, layout), indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"OK {nm.name} (no music)")
        if fmt == "9x16" and "wa" in fmts:
            k = 720 / 1080
            lw = {"safe": [round(v * k) for v in layout["safe"]], "caption_band": [round(v * k) for v in layout["caption_band"]],
                  "captions_hidden": layout["captions_hidden"],
                  "overlays": [dict(o, x=round(o["x"] * k), y=round(o["y"] * k), w=round(o["w"] * k), h=round(o["h"] * k)) for o in layout["overlays"]]}
            for src, suf in [(out, "")] + ([(nm, "_nomusic")] if dry else []):
                wa = rd / f"{spec['out_stem']}_WhatsApp_720x1280{suf}.mp4"
                wa_scale(src, wa)
                wa.with_suffix(".timeline.json").write_text(json.dumps(timeline(wa.name, (720, 1280), total, items, end, raw_abs, lw), indent=1, ensure_ascii=False), encoding="utf-8")
                print(f"OK {wa.name} 720x1280 {wa.stat().st_size / 1e6:.1f} MB")


def wa_scale(src, dst):
    """WhatsApp copy (about 10 MB for 1:45): 720x1280, 1 Mbit/s, AAC 96k."""
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-crf", "23",
         "-preset", "slow", "-maxrate", "1000k", "-bufsize", "2000k", "-profile:v", "high", "-level", "3.1", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", dst])


if __name__ == "__main__":
    main()
