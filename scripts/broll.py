#!/usr/bin/env python3
"""B-roll helpers for render_batch.py (see skills/dtc-broll).

Review / testimonial quote popup: the real review text, shown word by word in time with the doctor's reading.
Spec (per clip): "broll": [{"kind": "quote", "src": [start_s, end_s], "text": "<verbatim review text>", "by": "Pelanggan, WhatsApp"}]
The text must be the real review supplied in the brief or proof folder. This module never writes or edits a review.
Captions are hidden while a popup is on screen (the popup shows the same words).
"""
import pathlib
from PIL import Image, ImageDraw

MAX_LINES = 3
DIM = (170, 185, 210)


def map_t(items, src_t):
    """Source time -> programme time through the kept clip items (None if the time is not kept)."""
    t = 0.0
    for it in items:
        if it["type"] == "clip":
            if it["s"] - 0.02 <= src_t <= it["e"] + 0.02:
                return t + max(0.0, src_t - it["s"])
            t += it["e"] - it["s"]
        else:
            t += it["dur"]
    return None


def in_split(items, t_out):
    t = 0.0
    for it in items:
        d = (it["e"] - it["s"]) if it["type"] == "clip" else it["dur"]
        if it["type"] == "clip" and it.get("mode") == "split" and t <= t_out <= t + d:
            return True
        t += d
    return False


def make_quote_cards(rb, text, by, prefix):
    """One PNG per word (that word gold, spoken words white, upcoming words dim). Returns (paths, (w, h), words)."""
    words = text.split()
    if not words:
        raise SystemExit("quote text is empty")
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    pad, indent = 34, 64
    cw = rb.SAFE_W
    maxw = cw - pad * 2 - indent
    for size in (46, 42, 38, 34):
        fnt = rb.font("Poppins-Medium.ttf", size)
        lines, cur = [], []
        for i, w in enumerate(words):
            t = " ".join(words[j] for j in cur + [i])
            if cur and d0.textlength(t, font=fnt) > maxw:
                lines.append(cur); cur = [i]
            else:
                cur.append(i)
        if cur: lines.append(cur)
        if len(lines) <= MAX_LINES:
            break
    else:
        raise SystemExit(f"quote too long for the popup ({len(words)} words). Use only the exact part the doctor reads.")
    lh = int(size * 1.35)
    fby = rb.font("Poppins-Medium.ttf", 30)
    ch = pad + lh * len(lines) + (44 if by else 0) + pad - 6
    fq = rb.font("Poppins-Bold.ttf", 96)
    paths = []
    for k in range(len(words)):
        img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=32, fill=rb.NAVY + (236,))
        d.rectangle([0, 24, 12, ch - 24], fill=rb.GOLD + (255,))
        d.text((pad, pad - 22), "“", font=fq, fill=rb.GOLD + (255,))
        y = pad
        for L in lines:
            x = pad + indent
            for i in L:
                col = rb.GOLD if i == k else (rb.WHITE if i < k else DIM)
                d.text((x, y), words[i], font=fnt, fill=col + (255,))
                x += d.textlength(words[i] + " ", font=fnt)
            y += lh
        if by:
            d.text((pad + indent, y + 2), by, font=fby, fill=(190, 205, 230, 255))
        p = f"{prefix}_{k:02d}.png"
        img.save(p)
        paths.append(p)
    return paths, (cw, ch), words


def apply_quotes(rb, clip, words, items, ovs, ass, work, tag):
    """Adds quote popup overlays to ovs and returns the caption list without the words the popup replaces."""
    for qi, b in enumerate(clip.get("broll", [])):
        if b.get("kind") != "quote":
            continue
        s, e = b["src"]
        t0, t1 = map_t(items, s), map_t(items, e)
        if t0 is None or t1 is None or t1 <= t0 + 0.3:
            print(f"  quote {qi}: not inside this version's kept clips, skipped")
            continue
        if in_split(items, t0) or in_split(items, t1):
            print(f"  quote {qi}: falls in the hook C card layout, skipped (face would be covered)")
            continue
        paths, (w, h), qwords = make_quote_cards(rb, b["text"], b.get("by", ""), str(work / f"quote_{clip['id']}_{tag}_{qi}"))
        n = len(qwords)
        src_w = rb.words_between(words, s, e)
        times = []
        for k in range(n + 1):
            if len(src_w) == n and k < n:
                tk = map_t(items, src_w[k]["s"])
                times.append(tk if tk is not None else t0 + (t1 - t0) * k / n)
            else:
                times.append(t0 + (t1 - t0) * k / n)
        times[0], times[-1] = t0, t1
        for k in range(1, n):
            times[k] = min(max(times[k], times[k - 1] + 0.05), t1 - 0.05 * (n - k))
        y = rb.SAFE_B - 12 - h
        for k, pth in enumerate(paths):
            ovs.append({"png": pth, "x": rb.OVL_X, "y": y, "start": times[k], "end": times[k + 1],
                        "fi": 0.15 if k == 0 else 0, "fo": 0.15 if k == n - 1 else 0, "kind": "quote"})
        ass = [x for x in ass if not (x["e"] > t0 and x["s"] < t1)]
        # the popup has priority: end headlines / lower thirds that would overlap it, drop those that start inside it
        for o in [o for o in ovs if o.get("kind") != "quote" and o["start"] < t1 and o["end"] > t0]:
            if o["start"] < t0 - 0.3:
                o["end"] = t0
            else:
                ovs.remove(o)
                print(f"  quote {qi}: removed overlay {pathlib.Path(o['png']).name} that started inside the popup")
    return ass
