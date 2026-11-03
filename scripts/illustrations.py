#!/usr/bin/env python3
"""Vector-style medical & fitness illustrations (2x supersampled Pillow) for Masterclass & DTC videos.

All drawings use brand palette colors from brands/ssclinic/brand.json:
  NAVY  #022057 (2, 32, 87)
  CNAVY #0F4C75 (15, 76, 117)
  GOLD  #F4A261 (244, 162, 97)
  AZURE #21A1F7 (33, 161, 247)
  WHITE #FFFFFF (255, 255, 255)
"""
import math

NAVY = (2, 32, 87)
CNAVY = (15, 76, 117)
GOLD = (244, 162, 97)
AZURE = (33, 161, 247)
MINT = (72, 202, 164)
CORAL = (231, 111, 81)
WHITE = (255, 255, 255)
SLATE = (195, 215, 238)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def draw_ring_gauge(d, cx, cy, r, thickness, frac, col, bg_col=(18, 58, 122)):
    bbox = [cx - r, cy - r, cx + r, cy + r]
    d.arc(bbox, start=0, end=360, fill=bg_col, width=thickness)
    if frac > 0.005:
        d.arc(bbox, start=-90, end=-90 + 360 * min(1.0, frac), fill=col, width=thickness)


def draw_dumbbell(d, cx, cy, sc=1.0, col=GOLD, acc=AZURE):
    """Vector dumbbell icon centered at (cx, cy)."""
    bw = int(84 * sc)
    bh = int(14 * sc)
    d.rounded_rectangle([cx - bw, cy - bh, cx + bw, cy + bh], radius=int(6 * sc), fill=SLATE)
    for side in (-1, 1):
        # Inner plate
        x0 = cx + side * int(48 * sc)
        x1 = cx + side * int(70 * sc)
        lx, rx = min(x0, x1), max(x0, x1)
        d.rounded_rectangle([lx, cy - int(52 * sc), rx, cy + int(52 * sc)], radius=int(8 * sc), fill=col)
        # Outer plate
        x2 = cx + side * int(74 * sc)
        x3 = cx + side * int(92 * sc)
        lx2, rx2 = min(x2, x3), max(x2, x3)
        d.rounded_rectangle([lx2, cy - int(38 * sc), rx2, cy + int(38 * sc)], radius=int(7 * sc), fill=acc)


def draw_protein_plate_icon(d, cx, cy, r, prog=1.0):
    """Illustrated Suku-Suku Separuh high-protein plate with animated macro arcs."""
    p = ease_out(prog)
    # Outer plate rim
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(8, 42, 98), outline=SLATE, width=4)
    ir = int(r * 0.82)
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=(4, 28, 70), outline=(35, 85, 155), width=2)
    # Animated macro segments: Protein (Gold, 40%), Veggies/Fiber (Mint, 35%), Smart Carbs (Azure, 25%)
    bbox = [cx - ir + 12, cy - ir + 12, cx + ir - 12, cy + ir - 12]
    d.arc(bbox, start=-90, end=-90 + int(144 * p), fill=GOLD, width=28)
    d.arc(bbox, start=54, end=54 + int(126 * p), fill=MINT, width=28)
    d.arc(bbox, start=180, end=180 + int(90 * p), fill=AZURE, width=28)
    # Center egg / protein emblem
    er = int(r * 0.28)
    d.ellipse([cx - er, cy - er, cx + er, cy + er], fill=WHITE)
    yr = int(er * 0.55)
    d.ellipse([cx - yr, cy - yr, cx + yr, cy + yr], fill=GOLD)


def draw_step_watch_icon(d, cx, cy, r, prog=1.0):
    """Illustrated sports watch face with animated step progress ring & shoe/footstep emblem."""
    p = ease_out(prog)
    # Watch strap top & bottom
    sw = int(r * 0.52)
    d.rounded_rectangle([cx - sw, cy - int(r * 1.32), cx + sw, cy - int(r * 0.85)], radius=12, fill=(25, 65, 130))
    d.rounded_rectangle([cx - sw, cy + int(r * 0.85), cx + sw, cy + int(r * 1.32)], radius=12, fill=(25, 65, 130))
    # Watch bezel
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(6, 34, 82), outline=AZURE, width=5)
    draw_ring_gauge(d, cx, cy, int(r * 0.82), 20, p * 0.85, GOLD, bg_col=(16, 54, 118))


def draw_moon_recovery_icon(d, cx, cy, r, prog=1.0):
    """Illustrated crescent moon & recovery pulse wave."""
    p = ease_out(prog)
    draw_ring_gauge(d, cx, cy, r, 16, p, AZURE, bg_col=(14, 52, 114))
    mr = int(r * 0.48)
    d.ellipse([cx - mr, cy - mr, cx + mr, cy + mr], fill=GOLD)
    d.ellipse([cx - int(mr * 0.45), cy - int(mr * 0.75), cx + int(mr * 0.95), cy + int(mr * 0.65)], fill=(6, 36, 88))


def draw_balance_scale_icon(d, cx, cy, sc=1.0, prog=1.0):
    """Illustrated calorie balance beam tilting into level equilibrium."""
    p = ease_out(prog)
    tilt_deg = (1.0 - p) * 14.0  # starts tilted 14 deg, levels to 0 deg
    rad = math.radians(tilt_deg)
    arm = int(120 * sc)
    # Pillar & base
    d.rounded_rectangle([cx - int(56 * sc), cy + int(68 * sc), cx + int(56 * sc), cy + int(84 * sc)], radius=8, fill=SLATE)
    d.rectangle([cx - int(8 * sc), cy - int(30 * sc), cx + int(8 * sc), cy + int(70 * sc)], fill=SLATE)
    # Tilted beam
    lx = cx - int(arm * math.cos(rad))
    ly = cy - int(18 * sc) + int(arm * math.sin(rad))
    rx = cx + int(arm * math.cos(rad))
    ry = cy - int(18 * sc) - int(arm * math.sin(rad))
    d.line([(lx, ly), (rx, ry)], fill=GOLD, width=int(10 * sc))
    d.ellipse([cx - int(14 * sc), cy - int(32 * sc), cx + int(14 * sc), cy - int(4 * sc)], fill=AZURE)
    # Left pan (Kalori Masuk) & Right pan (Kalori Keluar)
    pw, ph = int(46 * sc), int(18 * sc)
    for px, py, col in ((lx, ly + int(28 * sc), GOLD), (rx, ry + int(28 * sc), AZURE)):
        d.line([(px, py - int(28 * sc)), (px - pw + 8, py)], fill=SLATE, width=3)
        d.line([(px, py - int(28 * sc)), (px + pw - 8, py)], fill=SLATE, width=3)
        d.pieslice([px - pw, py - ph, px + pw, py + ph], start=0, end=180, fill=col)
