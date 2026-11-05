"""Pixel props for the 'car stuff, explained' under-the-bonnet episodes (oil-dipstick, cold-battery, hot-radiator).

Small RGBA pixel grids like carbits.py; scale with pixanim.grid.up(img, s) (nearest). Screen-space effects draw at full res.
    dipstick(level, glow)        dipstick: yellow loop handle, rod, blade with MIN / MAX notches, oil film up to `level`
    DIP_MIN, DIP_MAX             blade rows of the two marks (for callout anchors: row * s from the sprite top)
    snowflake(), snow(cv, t), frost(cv, k)   snowflake icon, falling screen-space snow, frosted corners
    battery_cutaway(t, rate, cold, charge)   12 V battery cut open: cells, plates, electrolyte, ions drifting at `rate`
    pressure_gauge(frac, glow)   small round gauge: green / amber / red arc, needle at frac 0..1
    radiator(cap, t, hot)        radiator front view with filler neck and cap turned by `cap` degrees
    gear(deg, teeth, r)          flywheel ring gear (starter scene), rotated by deg
    spray(cv, t, t0, x, y)       hot coolant spray: droplets arc up and fall (screen space)
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

INK = (26, 26, 46)
STEEL, STEEL_HI, STEEL_SH = (190, 196, 206), (236, 240, 246), (120, 126, 138)
YELLOW, YELLOW_SH = (255, 210, 63), (200, 150, 20)
OIL, OIL_HI = (196, 130, 20), (250, 190, 70)
ICE, ICE_HI = (150, 210, 255), (235, 248, 255)
RED, AMBER, GREEN = (232, 52, 63), (255, 150, 30), (60, 200, 90)
COOLANT, COOLANT_HI = (90, 230, 110), (200, 255, 190)

# ------------------------------------------------------------------ dipstick (vertical, 14 x 96 grid)
DIP_W, DIP_H = 14, 96
BLADE0 = 52                          # blade starts here (rod above)
DIP_MAX, DIP_MIN = 62, 82            # rows of the two marks


def dipstick(level=0.5, glow=0.0):
    """level: oil film height, 0 = at MIN, 1 = at MAX (values above 1 overfill past MAX). glow 0..1 lights the marks."""
    img = Image.new('RGBA', (DIP_W, DIP_H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx = DIP_W // 2
    d.ellipse((1, 0, 12, 13), outline=INK, width=4); d.ellipse((2, 1, 11, 12), outline=YELLOW, width=2)  # loop handle
    d.arc((2, 1, 11, 12), 200, 300, fill=(255, 240, 160))
    d.rectangle((cx - 2, 12, cx + 1, 20), fill=INK); d.rectangle((cx - 1, 12, cx, 19), fill=YELLOW_SH)
    d.rectangle((cx - 2, 20, cx + 1, BLADE0), fill=INK); d.line((cx - 1, 20, cx - 1, BLADE0), fill=STEEL)
    d.line((cx, 20, cx, BLADE0), fill=STEEL_SH)
    d.rectangle((cx - 3, BLADE0, cx + 2, DIP_H - 2), fill=INK)                    # blade
    d.rectangle((cx - 2, BLADE0, cx + 1, DIP_H - 3), fill=STEEL); d.line((cx - 2, BLADE0, cx - 2, DIP_H - 3), fill=STEEL_HI)
    for y in range(DIP_MAX + 2, DIP_MIN - 1, 3): d.point((cx, y), fill=STEEL_SH); d.point((cx - 1, y + 1), fill=STEEL_SH)
    top = round(DIP_MIN - (DIP_MIN - DIP_MAX) * level)
    if level > -0.9:                                                             # oil film from the tip up
        d.rectangle((cx - 2, max(BLADE0, top), cx + 1, DIP_H - 3), fill=OIL + (230,))
        d.line((cx - 2, max(BLADE0, top), cx - 2, DIP_H - 3), fill=OIL_HI)
    for y, col in ((DIP_MAX, RED), (DIP_MIN, GREEN)):                             # notches
        d.rectangle((cx - 4, y, cx + 3, y + 1), fill=INK); d.line((cx - 2, y, cx + 1, y), fill=col)
    if glow > 0.02:
        g = Image.new('RGBA', img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        for y, col in ((DIP_MAX, RED), (DIP_MIN, GREEN)):
            gd.rectangle((0, y - 2, DIP_W - 1, y + 3), fill=col + (int(170 * glow),))
        img = Image.alpha_composite(g, img)
        d = ImageDraw.Draw(img)
        for y, col in ((DIP_MAX, RED), (DIP_MIN, GREEN)): d.line((cx - 2, y, cx + 1, y), fill=tuple(min(255, c + 90) for c in col))
    return img


# ------------------------------------------------------------------ cold weather
FLAKE = ["0000001000000", "0001001001000", "0000101010000", "0100011100010", "0011001001100", "0001101011000",
         "1111111111111", "0001101011000", "0011001001100", "0100011100010", "0000101010000", "0001001001000", "0000001000000"]


@lru_cache(2)
def snowflake(dark=False):
    img = Image.new('RGBA', (15, 15), (0, 0, 0, 0)); px = img.load()
    for y, row in enumerate(FLAKE):
        for x, c in enumerate(row):
            if c == '1':
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if px[x + 1 + dx, y + 1 + dy][3] == 0: px[x + 1 + dx, y + 1 + dy] = INK + (255,)
    for y, row in enumerate(FLAKE):
        for x, c in enumerate(row):
            if c == '1': px[x + 1, y + 1] = (ICE if (x + y) % 3 else ICE_HI) + (255,)
    return img


def snow(cv, t, n=70, seed=4, s=6, w=1080, h=1920, wind=40):
    """Falling square pixel snow in screen space; defined for any t (negative too), so loops stay seamless."""
    r = np.random.default_rng(seed); d = ImageDraw.Draw(cv)
    for x0, y0, v, k, ph in zip(r.uniform(0, w, n), r.uniform(0, h, n), r.uniform(60, 160, n), r.integers(1, 3, n), r.uniform(0, 6.3, n)):
        x = (x0 + wind * t + 26 * math.sin(t * 1.3 + ph)) % w; y = (y0 + v * t) % h
        x, y, z = round(x / s) * s, round(y / s) * s, s * k
        d.rectangle((x, y, x + z - 1, y + z - 1), fill=(235, 245, 255, 170 + 40 * (k - 1)))


@lru_cache(4)
def _frost_mask(w, h, q):
    m = Image.new('L', (w // 6, h // 6), 0); d = ImageDraw.Draw(m); r = np.random.default_rng(9)
    for cx, cy in ((0, 0), (w // 6, 0), (0, h // 6), (w // 6, h // 6)):
        for _ in range(90):
            a, rr = r.uniform(0, 6.3), r.uniform(0, 60) ** 1.0
            d.point((cx + rr * math.cos(a), cy + rr * math.sin(a)), fill=int(r.uniform(120, 255)))
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=170)
    return m.resize((w, h), Image.NEAREST)


def frost(cv, k=1.0):
    """Icy corners (6 px blocks) faded in by k."""
    if k < 0.02: return
    m = _frost_mask(cv.width, cv.height, 0).point(lambda v: int(v * 0.75 * k))
    cv.paste((215, 238, 255, 255), (0, 0), m)


# ------------------------------------------------------------------ battery cutaway (grid 120 x 84)
BAT_W, BAT_H = 120, 84
CELLS = 6


def battery_cutaway(t=0.0, rate=1.0, cold=0.0, charge=0.6):
    """Lead-acid battery with the front wall cut away: six cells of plates in electrolyte, ions drifting between the
    plates (speed * rate), a blue frost tint by `cold`, and a charge bar on the lid."""
    img = Image.new('RGBA', (BAT_W, BAT_H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for x, col, sign in ((20, RED, '+'), (94, (60, 62, 72), '-')):                # terminals
        d.rectangle((x - 1, 2, x + 9, 13), fill=INK); d.rectangle((x, 3, x + 8, 12), fill=(176, 182, 194))
        d.rectangle((x + 1, 3, x + 7, 5), fill=col)
    d.rectangle((2, 12, BAT_W - 3, 24), fill=INK); d.rectangle((3, 13, BAT_W - 4, 23), fill=(64, 68, 82))     # lid
    d.line((3, 13, BAT_W - 4, 13), fill=(110, 116, 132))
    d.rectangle((40, 16, 80, 20), fill=INK)
    d.rectangle((41, 17, 41 + round(38 * charge), 19), fill=GREEN if charge > 0.35 else AMBER)
    d.rectangle((2, 24, BAT_W - 3, BAT_H - 2), fill=INK); d.rectangle((4, 25, BAT_W - 5, BAT_H - 4), fill=(30, 34, 46))  # case
    cw = (BAT_W - 10) / CELLS
    for c in range(CELLS):
        x0 = round(5 + c * cw); x1 = round(5 + (c + 1) * cw) - 1
        d.rectangle((x0, 30, x1 - 1, BAT_H - 6), fill=(40, 70, 110))                # electrolyte
        d.line((x0, 30, x1 - 1, 30), fill=(90, 140, 190))
        for k in range(4):                                                         # plates: lead / lead dioxide
            px = x0 + 2 + k * 4
            if px + 1 >= x1 - 1: break
            d.rectangle((px, 33, px + 1, BAT_H - 8), fill=(150, 154, 164) if k % 2 else (120, 70, 50))
        if c: d.rectangle((x0 - 1, 26, x0 - 1, BAT_H - 5), fill=(70, 74, 88))
        d.rectangle((x0 + 2, 26, x1 - 3, 28), fill=(150, 154, 164))                 # strap
    r = np.random.default_rng(3); n = 54
    for x0, y0, sp, ph in zip(r.uniform(6, BAT_W - 8, n), r.uniform(34, BAT_H - 8, n), r.uniform(6, 14, n), r.uniform(0, 6.3, n)):
        y = 34 + (y0 - 34 - sp * rate * t) % (BAT_H - 42)
        x = x0 + 1.5 * math.sin(t * 3 * max(rate, 0.15) + ph)
        d.point((x, y), fill=(255, 230, 110) if ph < 3.1 else (180, 240, 255))
    if cold > 0.02:
        tint = Image.new('RGBA', img.size, ICE + (int(90 * cold),)); m = img.split()[3]
        img = Image.composite(Image.alpha_composite(img, tint), img, m)
        d = ImageDraw.Draw(img)
        for x in range(6, BAT_W - 6, 7): d.line((x, 25, x + 2, 25 + (x * 7) % 5), fill=ICE_HI)   # icicles on the lid edge
    return img


# ------------------------------------------------------------------ pressure gauge (grid ~60)
def pressure_gauge(frac=0.0, glow=0.0, r=26):
    n = 2 * r + 10; c = n // 2
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((c - r - 3, c - r - 3, c + r + 3, c + r + 3), fill=INK)
    d.ellipse((c - r - 1, c - r - 1, c + r + 1, c + r + 1), fill=(176, 182, 194)); d.ellipse((c - r + 2, c - r + 2, c + r - 2, c + r - 2), fill=(30, 32, 42))
    rr = r - 6                                                                     # arc: 225 deg (empty) clockwise to -45 (full)
    for a0, a1, col in ((135, 252, GREEN), (252, 333, AMBER), (333, 405, RED)):
        d.arc((c - rr, c - rr, c + rr, c + rr), a0, a1, fill=col, width=4)
    if glow > 0.02:
        d.arc((c - rr - 4, c - rr - 4, c + rr + 4, c + rr + 4), 333, 405, fill=RED + (int(255 * glow),), width=3)
    for k in range(9):
        a = math.radians(225 - 270 * k / 8)
        d.line((c + (rr - 6) * math.cos(a), c - (rr - 6) * math.sin(a), c + (rr - 2) * math.cos(a), c - (rr - 2) * math.sin(a)), fill=(220, 224, 232))
    a = math.radians(225 - 270 * max(0, min(1.02, frac)))
    tip = (c + (rr - 3) * math.cos(a), c - (rr - 3) * math.sin(a))
    d.line((c, c, *tip), fill=(120, 30, 10), width=3); d.line((c, c, *tip), fill=(255, 120, 60), width=1)
    d.ellipse((c - 3, c - 3, c + 3, c + 3), fill=(90, 96, 110))
    d.arc((c - r + 3, c - r + 3, c + r - 3, c + r - 3), 120, 160, fill=(255, 255, 255, 90))
    return img


# ------------------------------------------------------------------ radiator (grid 130 x 100)
RAD_W, RAD_H = 130, 100
CAP_XY = (65, 10)                     # cap centre on the grid


def radiator(cap=0.0, t=0.0, hot=0.0):
    """Radiator front view: top tank, filler neck with a cap turned by `cap` degrees, core fins, bottom tank.
    hot 0..1 lifts a red heat tint on the core."""
    img = Image.new('RGBA', (RAD_W, RAD_H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((4, 18, RAD_W - 5, 30), fill=INK); d.rectangle((5, 19, RAD_W - 6, 29), fill=(70, 74, 88))       # top tank
    d.line((5, 19, RAD_W - 6, 19), fill=(120, 126, 140))
    d.rectangle((57, 12, 73, 19), fill=INK); d.rectangle((58, 13, 72, 18), fill=(150, 156, 168))                 # neck
    d.rectangle((6, 30, RAD_W - 7, RAD_H - 14), fill=INK)
    for x in range(7, RAD_W - 7):                                                                                 # core fins
        col = (128, 134, 148) if x % 3 == 0 else (96, 100, 114) if x % 3 == 1 else (70, 74, 86)
        d.line((x, 31, x, RAD_H - 15), fill=col)
    for y in range(34, RAD_H - 15, 6): d.line((7, y, RAD_W - 8, y), fill=(56, 58, 70))
    d.rectangle((4, RAD_H - 14, RAD_W - 5, RAD_H - 4), fill=INK); d.rectangle((5, RAD_H - 13, RAD_W - 6, RAD_H - 5), fill=(70, 74, 88))
    if hot > 0.02:
        tint = Image.new('RGBA', img.size, (255, 60, 40, 0)); td = ImageDraw.Draw(tint)
        td.rectangle((7, 31, RAD_W - 8, RAD_H - 15), fill=(255, 60, 40, int(80 * hot)))
        img = Image.alpha_composite(img, tint); d = ImageDraw.Draw(img)
    cx, cy = CAP_XY                                                                                               # cap
    d.ellipse((cx - 12, cy - 9, cx + 12, cy + 5), fill=INK); d.ellipse((cx - 11, cy - 8, cx + 11, cy + 3), fill=(210, 214, 222))
    d.ellipse((cx - 7, cy - 6, cx + 7, cy + 1), fill=(176, 182, 194))
    a = math.radians(cap)
    for k in (0, 180):
        b = a + math.radians(k)
        d.line((cx, cy - 2, cx + 13 * math.cos(b), cy - 2 + 5 * math.sin(b)), fill=INK, width=3)
        d.line((cx, cy - 2, cx + 12 * math.cos(b), cy - 2 + 4.6 * math.sin(b)), fill=(236, 240, 246), width=1)
    d.point((cx - 5, cy - 6), fill=(255, 255, 255))
    return img


# ------------------------------------------------------------------ flywheel ring gear
def gear(deg=0.0, teeth=24, r=30, col=(150, 156, 168)):
    n = 2 * r + 12; c = n / 2
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = []
    for k in range(teeth * 4):
        a = math.radians(deg) + 2 * math.pi * k / (teeth * 4)
        rr = r + 4 if (k % 4) in (1, 2) else r
        pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
    d.polygon(pts, fill=INK); d.polygon([(c + (x - c) * 0.93, c + (y - c) * 0.93) for x, y in pts], fill=col)
    d.ellipse((c - r * 0.62, c - r * 0.62, c + r * 0.62, c + r * 0.62), fill=(70, 74, 86))
    for k in range(5):
        a = math.radians(deg) + 2 * math.pi * k / 5
        x, y = c + r * 0.38 * math.cos(a), c + r * 0.38 * math.sin(a)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(40, 42, 52))
    d.ellipse((c - 6, c - 6, c + 6, c + 6), fill=INK); d.ellipse((c - 4, c - 4, c + 4, c + 4), fill=(190, 196, 206))
    return img


# ------------------------------------------------------------------ coolant spray (screen space)
def spray(cv, t, t0, x, y, n=60, seed=8, life=1.1, s=9, rate=1.0, t1=None):
    """Droplets thrown up from (x, y) in a fan, falling under gravity; emitted continuously from t0 (until t1)."""
    if t < t0: return
    r = np.random.default_rng(seed); d = ImageDraw.Draw(cv)
    for i, (vx, vy, ph) in enumerate(zip(r.uniform(-380, 380, n), r.uniform(-1300, -700, n), r.uniform(0, life, n))):
        tb = t0 + ph + life * math.floor((t - t0 - ph) / life)                   # this droplet's latest birth
        if t1 is not None and tb > t1: continue
        a = t - tb
        if a < 0 or a > life: continue
        px, py = x + vx * a, y + vy * a + 1500 * a * a
        k = 2 if i % 4 == 0 else 1
        px, py = round(px / s) * s, round(py / s) * s
        d.rectangle((px, py, px + k * s - 1, py + k * s - 1), fill=(COOLANT_HI if i % 3 == 0 else COOLANT) + (int(255 * (1 - a / life) ** 0.5),))


def steam(cv, t, x, y, n=7, seed=2, rise=520, life=1.6, size=1.0):
    """Looping soft pixel steam column (blocky puffs that rise, grow and fade), defined for any t."""
    r = np.random.default_rng(seed)
    lay = Image.new('L', (cv.width // 6, cv.height // 6), 0); d = ImageDraw.Draw(lay)
    for k, (dx, ph) in enumerate(zip(r.uniform(-30, 30, n), r.uniform(0, life, n))):
        a = ((t + ph) % life) / life
        px, py = (x + dx + 60 * a * math.sin(k + t)) / 6, (y - rise * a) / 6
        rr = (14 + 40 * a) * size / 6
        d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=int(150 * math.sin(math.pi * a)))
    m = lay.resize(cv.size, Image.NEAREST)
    cv.paste((236, 238, 244, 255), (0, 0), m)
