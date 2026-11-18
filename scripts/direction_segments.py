"""Per-format segment rendering for render_direction.py (one ffmpeg call per shot, then concat)."""
import pathlib, subprocess, sys
import direction_gfx as G

FPS = 30


def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        print("FAIL:", " ".join(map(str, cmd))[:400]); print(r.stderr[-2000:]); sys.exit(1)
    return r.stdout


class Graph:
    def __init__(self, dur):
        self.cmd, self.fc, self.n_in, self.cur, self.n, self.dur = [], [], 0, None, 0, dur

    def input(self, path, loop=False):
        self.cmd += (["-loop", "1", "-t", f"{self.dur:.3f}"] if loop else []) + ["-i", str(path)]
        self.n_in += 1
        return self.n_in - 1

    def overlay(self, png, x, y, en=None, fade=False):
        k = self.input(png, loop=True)
        self.fc.append(f"[{k}:v]format=rgba" + (",fade=in:st=0:d=0.25:alpha=1" if fade else "") + f"[o{self.n}]")
        e = f":enable='between(t,{en[0]:.3f},{en[1]:.3f})'" if en else ""
        self.fc.append(f"[{self.cur}][o{self.n}]overlay={int(x)}:{int(y)}{e}[v{self.n + 1}]")
        self.cur = f"v{self.n + 1}"; self.n += 1


def render_format(fmt, spec, bd, stab, items, end, chunks_fn):
    L = G.LAYOUT[fmt]; W, H = L["size"]; vx, vy, vw, vh = L["video"]; sc = vw / 640
    wd = bd / "work" / f"seg_{fmt}"; wd.mkdir(parents=True, exist_ok=True)
    ovl, segs, prev = [], [], None
    ns = max((it.get("step") or 0) for it in items)
    if fmt == "9x16":
        bgp = wd / "bg.png"; G.bg_9x16(spec["footer"], bgp, spec.get("bg_card"))
    else:
        lp = wd / "logo.png"; lw, lh = G.logo_pill(lp); lxy = (L["safe"][2] - lw, L["safe"][1])
        ovl.append({"name": "logo.png", "x": lxy[0], "y": lxy[1], "w": lw, "h": lh, "start": 0.0, "end": end["out_start"]})
    for it in items:
        i, d, t0 = it["idx"], it["dur"], it["out_start"]
        g = Graph(d)
        g.cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{it['in']:.3f}", "-t", f"{it['out'] - it['in']:.3f}", "-i", str(stab)]
        g.n_in = 1
        chain = (f"[0:v]setpts=(PTS-STARTPTS)/{it['speed']},fps={FPS},"
                 f"tpad=stop_mode=clone:stop_duration={it['pad'] + it['freeze'] + 0.1:.3f},"
                 f"scale={vw}:{vh}:flags=lanczos,unsharp=5:5:0.6,format=rgba")
        if fmt == "9x16":
            b = g.input(bgp, loop=True)
            g.fc += [chain + "[vid]", f"[{b}:v]format=rgba[bg]", f"[bg][vid]overlay={vx}:{vy}[v0]"]
        else:
            g.fc.append(chain + "[v0]")
        g.cur = "v0"
        if it.get("ring"):
            rx, ry, rr = it["ring"]; rp = wd / f"ring_{i:02d}.png"; s = G.ring(rp, int(rr * sc))
            x, y = vx + rx * sc - s / 2, vy + ry * sc - s / 2
            g.overlay(rp, x, y, (d - it["freeze"], d))
            ovl.append({"name": rp.name, "x": int(x), "y": int(y), "w": s, "h": s, "start": t0 + d - it["freeze"], "end": t0 + d})
        pp = wd / f"panel_{i:02d}.png"; pw, ph = G.panel(fmt, dict(it, nsteps=ns), pp); px, py = L["panel"]
        key = (it.get("step"), it.get("icon"), it["head"], it.get("sub"))
        g.overlay(pp, px, py, fade=key != prev); prev = key
        ovl.append({"name": pp.name, "x": px, "y": py, "w": pw, "h": ph, "start": t0, "end": t0 + d})
        if fmt == "16x9":
            g.overlay(lp, *lxy)
        if it.get("vo"):
            for k, (a, b, txt) in enumerate(chunks_fn(it["vo"]["text"], it["vo"]["sents"], it["vo"]["dur"])):
                cp = wd / f"cap_{i:02d}_{k}.png"; x, y, w, h = G.caption(fmt, txt, cp)
                g.overlay(cp, x, y, (it["vo_at"] + a, min(d, it["vo_at"] + b)))
        last = ",fade=in:st=0:d=0.3" if i == 0 else ""
        g.fc.append(f"[{g.cur}]format=yuv420p{last}[out]")
        seg = wd / f"seg_{i:02d}.mp4"
        run(g.cmd + ["-filter_complex", ";".join(g.fc), "-map", "[out]", "-t", f"{d:.3f}", "-r", str(FPS),
                     "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-an", seg])
        segs.append(seg)
    # end card
    still = wd / "still.png"
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(spec["endcard"]["still_at"]), "-i", stab, "-frames:v", "1", still])
    ep = wd / "endcard.png"; G.endcard(fmt, spec["endcard"], still, ep)
    ed = end["dur"]; seg = wd / "seg_end.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{ed:.3f}", "-i", ep, "-vf",
         f"fade=in:st=0:d=0.4,fade=out:st={ed - 0.6:.3f}:d=0.6,format=yuv420p", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-an", seg])
    segs.append(seg)
    lst = wd / "concat.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), encoding="utf-8")
    vid = wd / "video.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid])
    layout = {"safe": list(L["safe"]), "overlays": ovl,
              "caption_band": [L["cap"][0], L["cap"][1] - (110 if fmt == "16x9" else 132), L["cap"][0] + L["cap_w"], L["cap"][1]],
              "captions_hidden": [[end["out_start"], end["out_start"] + ed]]}
    return vid, layout


def build_audio(spec, bd, items, end, total):
    """Ambience = source audio at 1x from each shot's in-point (keeps the place sound true to the picture), plus VO."""
    out = bd / "work" / "mix.m4a"; gain = spec.get("ambience_gain", 0.35)
    # each segment is cut with input -ss, the same way as the picture (and the sync checker); this WhatsApp AAC
    # lands 1-3 frames (21-62 ms) apart between -ss seeking and a continuous decode + atrim
    ad = bd / "work" / "amb"; ad.mkdir(exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y"]; fc = []; n = len(items)
    for i, it in enumerate(items):
        d = it["dur"]; ns = int(round(d * 48000)); sp = ad / f"a{i:02d}.wav"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{it['in']:.3f}", "-t", f"{d:.3f}", "-i", spec["source"], "-vn", "-ac", "2", "-ar", "48000",
             "-af", f"apad=whole_len={ns},atrim=end_sample={ns},afade=t=in:d=0.12,afade=t=out:st={d - 0.12:.3f}:d=0.12",
             "-c:a", "pcm_s16le", sp], cwd=bd)
        cmd += ["-i", sp]
    fc.append(f"aevalsrc=0|0:d={end['dur']:.3f}:s=48000,aformat=sample_rates=48000:channel_layouts=stereo[aend]")
    fc.append("".join(f"[{i}:a]" for i in range(n)) + f"[aend]concat=n={n + 1}:v=0:a=1,volume={gain}[amb]")
    amb = bd / "work" / "amb.wav"
    run(cmd + ["-filter_complex", ";".join(fc), "-map", "[amb]", "-t", f"{total:.3f}", "-c:a", "pcm_s16le", amb], cwd=bd)
    # VO bus on a silent bed: mixing adelay'd lines straight into the concat chain drifted 30-70 ms, a silent bed is sample exact
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    fc, vos, k = [], [], 1
    for it in items + [end]:
        if it.get("vo"):
            cmd += ["-i", str(it["vo"]["mp3"])]; ms = int(round((it["out_start"] + it["vo_at"]) * 1000))
            fc.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[vo{k}]"); vos.append(f"[vo{k}]"); k += 1
    fc.append("[0:a]" + "".join(vos) + f"amix=inputs={len(vos) + 1}:normalize=0:duration=first[vo]")
    vob = bd / "work" / "vo_bus.wav"
    run(cmd + ["-filter_complex", ";".join(fc), "-map", "[vo]", "-c:a", "pcm_s16le", vob], cwd=bd)
    run(["ffmpeg", "-v", "error", "-y", "-i", amb, "-i", vob, "-filter_complex",
         "[0:a][1:a]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]",
         "-map", "[aout]", "-t", f"{total:.3f}", "-c:a", "aac", "-b:a", "160k", out], cwd=bd)
    return out
