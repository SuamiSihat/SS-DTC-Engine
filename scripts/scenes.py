#!/usr/bin/env python3
"""Generate 25 fps animated motion charts, diagrams, and vector illustrations for Masterclass videos.

Usage:
  python scripts/scenes.py <out_dir> [--fps 25] [--dur 4.2]

Produces for each episode (ep1..ep5):
  <out_dir>/scene_ep<N>_16x9.mp4  (940x828 right-side animated studio board)
  <out_dir>/scene_ep<N>_9x16.mp4  (1080x1920 vertical animated chart cutaway, safe-zone compliant)
"""
import argparse, os, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import illustrations as ill

NAVY, CNAVY, GOLD, AZURE, WHITE = ill.NAVY, ill.CNAVY, ill.GOLD, ill.AZURE, ill.WHITE
MINT, CORAL, SLATE = ill.MINT, ill.CORAL, ill.SLATE
FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/poppins",
]


def font(name, size):
    for d in FONT_DIRS:
        p = pathlib.Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise SystemExit(f"Font not found: {name}")


def render_mp4_frames(out_path, w, h, fps, dur, draw_fn):
    n_frames = max(1, round(dur * fps))
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n_frames):
        prog = min(1.0, i / max(1, int(n_frames * 0.78)))
        img = draw_fn(w, h, prog, i / fps)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed generating {out_path}")


def draw_card_shell(w, h, is_9x16, badge, title, subtitle):
    img = Image.new("RGB", (w, h), NAVY)
    d = ImageDraw.Draw(img)
    if is_9x16:
        # Safe zone box x: 120..960, y: 275..1075 (leaves caption band 1118..1248 clear)
        bx0, by0, bx1, by1 = 120, 275, 960, 1075
    else:
        bx0, by0, bx1, by1 = 0, 0, w - 1, h - 1
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=32, fill=(5, 38, 96), outline=GOLD, width=3)

    max_tw = (bx1 - bx0) - 72
    fb = font("Poppins-Bold.ttf", 22 if is_9x16 else 24)
    tsize = 34 if is_9x16 else 36
    ft = font("Poppins-Bold.ttf", tsize)
    while tsize > 22 and d.textlength(title, font=ft) > max_tw:
        tsize -= 1
        ft = font("Poppins-Bold.ttf", tsize)
    ssize = 22 if is_9x16 else 23
    fs = font("Poppins-Medium.ttf", ssize)
    while ssize > 16 and d.textlength(subtitle, font=fs) > max_tw:
        ssize -= 1
        fs = font("Poppins-Medium.ttf", ssize)

    pw = int(d.textlength(badge, font=fb) + 40)
    d.rounded_rectangle([bx0 + 36, by0 + 28, bx0 + 36 + pw, by0 + 70], radius=21, fill=GOLD)
    d.text((bx0 + 56, by0 + 33), badge, font=fb, fill=NAVY)
    d.text((bx0 + 36, by0 + 82), title, font=ft, fill=WHITE)
    d.text((bx0 + 36, by0 + 130), subtitle, font=fs, fill=SLATE)
    d.rectangle([bx0 + 36, by0 + 168, bx1 - 36, by0 + 171], fill=(25, 75, 145))
    return img, d, (bx0 + 36, by0 + 188, bx1 - 36, by1 - 28)


# ---------- EP01: Protein Plate Illustration + Animated Macro & Muscle Bar Chart ----------
def draw_ep1(w, h, prog, t_sec):
    is_9x16 = h > w
    img, d, (x0, y0, x1, y1) = draw_card_shell(
        w, h, is_9x16,
        "GRAFIK ANALISIS • EPISOD 01",
        "IMPAK PROTEIN PADA OTOT & TENAGA",
        "Perbandingan Diet Kurang Protein vs Tinggi Protein",
    )
    p = ill.ease_out(prog)
    # Left/Top: Illustrated High-Protein Plate
    cx = x0 + 150
    cy = y0 + 145
    ill.draw_protein_plate_icon(d, cx, cy, 115, prog=p)

    # Legend next to plate
    fl = font("Poppins-Bold.ttf", 24)
    fm = font("Poppins-Medium.ttf", 21)
    lx = cx + 145
    ly = y0 + 48
    for col, lbl, val in (
        (GOLD, "Sumber Protein Utama", f"{int(round(40 * p))}% Hidangan"),
        (MINT, "Sayuran & Serat", f"{int(round(35 * p))}% Hidangan"),
        (AZURE, "Karbohidrat Ikut Aktiviti", f"{int(round(25 * p))}% Hidangan"),
    ):
        d.rounded_rectangle([lx, ly, lx + 22, ly + 22], radius=6, fill=col)
        d.text((lx + 34, ly - 4), lbl, font=fl, fill=WHITE)
        d.text((lx + 34, ly + 26), val, font=fm, fill=col)
        ly += 70

    # Bottom: Animated Horizontal Bar Chart (Muscle & Metabolism Retention)
    by = y0 + 310
    d.text((x0, by), "KADAR KEKAL OTOT & TENAGA HARIAN (%)", font=fl, fill=GOLD)
    by += 44
    bars = [
        ("Diet Kurang Protein (Makan Ikut Nafsu)", 0.34, CORAL),
        ("Tambah 2 Ketul Ayam / Ikan / Telur", 0.78, AZURE),
        ("Tinggi Protein + Latihan Beban", 0.94, GOLD),
    ]
    max_bw = (x1 - x0) - 110
    for label, target, col in bars:
        cur_v = target * p
        d.text((x0, by), label, font=fm, fill=WHITE)
        by += 30
        d.rounded_rectangle([x0, by, x0 + max_bw, by + 32], radius=12, fill=(12, 52, 114))
        bw = max(16, int(max_bw * cur_v))
        d.rounded_rectangle([x0, by, x0 + bw, by + 32], radius=12, fill=col)
        pct = f"{int(round(cur_v * 100))}%"
        d.text((x0 + bw + 14, by + 1), pct, font=fl, fill=col)
        by += 52
    return img


# ---------- EP02: Age 40+ Muscle & Testosterone Line Chart + Dumbbell Illustration ----------
def draw_ep2(w, h, prog, t_sec):
    is_9x16 = h > w
    img, d, (x0, y0, x1, y1) = draw_card_shell(
        w, h, is_9x16,
        "CARTA METABOLISME • EPISOD 02",
        "JISIM OTOT & HORMON SELEPAS UMUR 40",
        "Kardio Sahaja vs Gabungan Latihan Beban (2–4x Seminggu)",
    )
    p = ill.ease_out(prog)
    # Top right dumbbell vector illustration
    ill.draw_dumbbell(d, x1 - 115, y0 + 55, sc=0.95, col=GOLD, acc=AZURE)
    fm = font("Poppins-Medium.ttf", 20)
    d.rounded_rectangle([x0, y0 + 14, x0 + 26, y0 + 34], radius=5, fill=GOLD)
    d.text((x0 + 36, y0 + 10), "Latihan Beban 2–4x/Minggu (Otot Kekal)", font=fm, fill=WHITE)
    d.rounded_rectangle([x0, y0 + 52, x0 + 26, y0 + 72], radius=5, fill=CORAL)
    d.text((x0 + 36, y0 + 48), "Kardio Sahaja / Tanpa Beban (Otot Susut)", font=fm, fill=SLATE)

    # Chart axes
    gx0, gy0, gx1, gy1 = x0 + 54, y0 + 125, x1 - 30, y1 - 55
    gw, gh = gx1 - gx0, gy1 - gy0
    d.rounded_rectangle([gx0, gy0, gx1, gy1], radius=16, fill=(4, 28, 72), outline=(25, 75, 145), width=2)
    for frac, ylbl in ((0.15, "100%"), (0.50, "75%"), (0.85, "50%")):
        ly = int(gy0 + gh * frac)
        d.line([(gx0, ly), (gx1, ly)], fill=(18, 56, 118), width=2)
        d.text((x0, ly - 12), ylbl, font=fm, fill=SLATE)

    for xf, xlbl in ((0.08, "Umur 30"), (0.36, "Umur 40"), (0.64, "Umur 50"), (0.90, "Umur 60")):
        lx = int(gx0 + gw * xf)
        d.text((lx - 36, gy1 + 10), xlbl, font=fm, fill=SLATE)

    # Plot curves up to progress p
    n_pts = max(2, int(40 * p))
    pts_good, pts_bad = [], []
    for i in range(n_pts):
        u = (i / 39.0) * p
        px = int(gx0 + 30 + (gw - 60) * u)
        # Good curve stays 95% -> 88%
        yg = gy0 + gh * (0.16 + 0.12 * u)
        # Bad curve drops 95% -> 52%
        yb = gy0 + gh * (0.16 + 0.68 * (u ** 1.35))
        pts_good.append((px, int(yg)))
        pts_bad.append((px, int(yb)))

    if len(pts_bad) >= 2:
        d.line(pts_bad, fill=CORAL, width=6)
        d.line(pts_good, fill=GOLD, width=7)
        gx_end, gy_end = pts_good[-1]
        bx_end, by_end = pts_bad[-1]
        d.ellipse([gx_end - 9, gy_end - 9, gx_end + 9, gy_end + 9], fill=GOLD, outline=WHITE, width=2)
        d.ellipse([bx_end - 9, by_end - 9, bx_end + 9, by_end + 9], fill=CORAL, outline=WHITE, width=2)
    return img


# ---------- EP03: Step Counter Watch Illustration + Animated Step Bar Chart ----------
def draw_ep3(w, h, prog, t_sec):
    is_9x16 = h > w
    img, d, (x0, y0, x1, y1) = draw_card_shell(
        w, h, is_9x16,
        "JEJAK AKTIVITI (NEAT) • EPISOD 03",
        "SASARAN LANGKAH HARIAN & PEMBAKARAN KALORI",
        "Tingkatkan Pergerakan Harian Secara Berperingkat",
    )
    p = ill.ease_out(prog)
    cx, cy = x0 + 135, y0 + 150
    ill.draw_step_watch_icon(d, cx, cy, 108, prog=p)
    f_big = font("Poppins-Bold.ttf", 36)
    f_sm = font("Poppins-Bold.ttf", 18)
    steps_now = int(round(2000 + 6000 * p))
    st_txt = f"{steps_now:,}"
    d.text((cx - d.textlength(st_txt, font=f_big) / 2, cy - 26), st_txt, font=f_big, fill=WHITE)
    d.text((cx - d.textlength("LANGKAH", font=f_sm) / 2, cy + 18), "LANGKAH", font=f_sm, fill=GOLD)

    # Right/Bottom vertical bar chart of daily step tiers
    bx0 = cx + 155
    by0, by1 = y0 + 40, y1 - 55
    bw_area = x1 - bx0
    bh_area = by1 - by0
    tiers = [
        ("Duduk\nPejabat", 2000, CORAL),
        ("Mula\nAktif", 4500, SLATE),
        ("Sasaran\nHarian", 7000, AZURE),
        ("Aktif\nOptimum", 10000, GOLD),
    ]
    col_w = bw_area // len(tiers)
    fv = font("Poppins-Bold.ttf", 21)
    fl = font("Poppins-Medium.ttf", 19)
    for i, (lbl, val, col) in enumerate(tiers):
        frac = (val / 10000.0) * p
        bar_h = max(14, int((bh_area - 60) * frac))
        bx = bx0 + i * col_w + 16
        bw = col_w - 32
        d.rounded_rectangle([bx, by1 - 36 - (bh_area - 60), bx + bw, by1 - 36], radius=12, fill=(10, 46, 104))
        d.rounded_rectangle([bx, by1 - 36 - bar_h, bx + bw, by1 - 36], radius=12, fill=col)
        vtxt = f"{int(round(val * p / 100) * 100):,}"
        d.text((bx + (bw - d.textlength(vtxt, font=fv)) / 2, by1 - 36 - bar_h - 30), vtxt, font=fv, fill=col)
        for li, ln in enumerate(lbl.split("\n")):
            d.text((bx + (bw - d.textlength(ln, font=fl)) / 2, by1 - 28 + li * 22), ln, font=fl, fill=WHITE)
    return img


# ---------- EP04: Sleep & Recovery Hormone Balance Diagram ----------
def draw_ep4(w, h, prog, t_sec):
    is_9x16 = h > w
    img, d, (x0, y0, x1, y1) = draw_card_shell(
        w, h, is_9x16,
        "KESEIMBANGAN HORMON • EPISOD 04",
        "TIDUR 6–8 JAM VS HORMON STRES (KORTISOL)",
        "Impak Recovery Kepada Penurunan Lemak & Tenaga",
    )
    p = ill.ease_out(prog)
    cx, cy = x0 + 130, y0 + 145
    ill.draw_moon_recovery_icon(d, cx, cy, 105, prog=p)

    fl = font("Poppins-Bold.ttf", 25)
    fm = font("Poppins-Medium.ttf", 21)
    lx = cx + 140
    d.text((lx, y0 + 50), f"SASARAN TIDUR: {int(round(6 + 2 * p))} JAM SEMALAM", font=fl, fill=GOLD)
    d.text((lx, y0 + 90), "• Kurangkan hormon stres (kortisol)", font=fm, fill=WHITE)
    d.text((lx, y0 + 126), "• Pulihkan tisu otot selepas latihan beban", font=fm, fill=WHITE)
    d.text((lx, y0 + 162), "• Selera makan & metabolisme lebih terkawal", font=fm, fill=AZURE)

    # Dual comparison bars at bottom
    by = y0 + 295
    d.text((x0, by), "PERBANDINGAN PROFIL HORMON & RECOVERY", font=fl, fill=GOLD)
    by += 42
    max_bw = (x1 - x0) - 110
    rows = [
        ("Kurang Tidur (<5 Jam): Tahap Stres Kortisol", 0.88, CORAL),
        ("Tidur 6–8 Jam + Brisk Walk: Kortisol Terkawal", 0.28, MINT),
        ("Tidur 6–8 Jam + Recovery: Pemulihan Otot & Tenaga", 0.94, GOLD),
    ]
    for label, target, col in rows:
        cur_v = target * p
        d.text((x0, by), label, font=fm, fill=WHITE)
        by += 30
        d.rounded_rectangle([x0, by, x0 + max_bw, by + 32], radius=12, fill=(12, 52, 114))
        bw = max(16, int(max_bw * cur_v))
        d.rounded_rectangle([x0, by, x0 + bw, by + 32], radius=12, fill=col)
        d.text((x0 + bw + 14, by + 1), f"{int(round(cur_v * 100))}%", font=fl, fill=col)
        by += 52
    return img


# ---------- EP05: Calorie Balance Scale Illustration + Hidden Sugar Chart ----------
def draw_ep5(w, h, prog, t_sec):
    is_9x16 = h > w
    img, d, (x0, y0, x1, y1) = draw_card_shell(
        w, h, is_9x16,
        "KESEIMBANGAN KALORI • EPISOD 05",
        "KALORI MASUK VS KALORI KELUAR & KONSISTENSI",
        "Elakkan Kalori Tersembunyi & Kekalkan Rutin Bebanan",
    )
    p = ill.ease_out(prog)
    cx, cy = x0 + 155, y0 + 135
    ill.draw_balance_scale_icon(d, cx, cy, sc=1.0, prog=p)

    fl = font("Poppins-Bold.ttf", 22 if is_9x16 else 24)
    fm = font("Poppins-Medium.ttf", 18 if is_9x16 else 20)
    lx = cx + 145
    d.text((lx, y0 + 42), "PRINSIP DEFISIT KALORI SIHAT", font=fl, fill=GOLD)
    d.text((lx, y0 + 82), "1. Kawal kalori minuman manis (teh/kopi tarik)", font=fm, fill=WHITE)
    d.text((lx, y0 + 118), "2. Senaman bebanan 2–4 kali seminggu", font=fm, fill=WHITE)
    d.text((lx, y0 + 154), "3. Protein harian cukup supaya otot kekal", font=fm, fill=AZURE)

    by = y0 + 295
    d.text((x0, by), "IMPAK AMALAN HARIAN KE ATAS PENURUNAN LEMAK", font=fl, fill=GOLD)
    by += 42
    max_bw = (x1 - x0) - 110
    rows = [
        ("Gym Sahaja + Minuman Manis Setiap Hari", 0.25, CORAL),
        ("Lari Jauh Tanpa Jaga Kalori & Protein", 0.42, SLATE),
        ("Jaga Kalori + Bebanan 2–4x + Protein Cukup", 0.95, GOLD),
    ]
    for label, target, col in rows:
        cur_v = target * p
        d.text((x0, by), label, font=fm, fill=WHITE)
        by += 30
        d.rounded_rectangle([x0, by, x0 + max_bw, by + 32], radius=12, fill=(12, 52, 114))
        bw = max(16, int(max_bw * cur_v))
        d.rounded_rectangle([x0, by, x0 + bw, by + 32], radius=12, fill=col)
        d.text((x0 + bw + 14, by + 1), f"{int(round(cur_v * 100))}%", font=fl, fill=col)
        by += 52
    return img


SCENES = {
    "ep1": draw_ep1,
    "ep2": draw_ep2,
    "ep3": draw_ep3,
    "ep4": draw_ep4,
    "ep5": draw_ep5,
}


def build_all(out_dir, fps=25, dur=4.2):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for key, fn in SCENES.items():
        p16 = out / f"scene_{key}_16x9.mp4"
        p9 = out / f"scene_{key}_9x16.mp4"
        print(f"Generating motion chart & illustration {key} (16:9 & 9:16) ...", flush=True)
        render_mp4_frames(p16, 940, 828, fps, dur, fn)
        render_mp4_frames(p9, 1080, 1920, fps, dur, fn)
    print("All 10 animated motion chart/diagram clips generated in", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--dur", type=float, default=4.2)
    a = ap.parse_args()
    build_all(a.out_dir, a.fps, a.dur)
