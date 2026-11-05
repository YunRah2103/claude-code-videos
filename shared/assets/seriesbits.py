"""Pixel props for the tyres-black / seatbelt-pretensioner / catalytic-theft 'car stuff, explained' series.

Small RGBA sprites on a pixel grid; scale with pixanim.grid.up(img, s) (nearest). Callout pills: carbits.pill();
poll sticker: overlays.poll().
    tyre(rot, light, wear)       side-on tyre: tread blocks + 5-spoke rim turning by rot deg; light=1 unfilled pale rubber
    rubber_block(t, k)           rubber cross-section; k 0..1 fills it with jiggling carbon-black particles (and darkens it)
    sun(t), shield(tick)         pixel sun with turning rays; blue shield with a white tick
    wear_bar(frac, col)          horizontal tread-life bar
    buckle(fire, t)              seatbelt buckle + pretensioner tube cutaway; fire 0..1 lights the charge and drives the piston
    exhaust(t, glow)             exhaust line side view: pipe, catalytic converter cut open (honeycomb glowing), silencer
    metal_tile(kind, t)          ingot tile for 'platinum' / 'palladium' / 'rhodium', with a moving shine stripe
    seat(), RETRACTOR; motor(t)  car seat side view (belt exit anchor); electric belt motor with a spinning gear
    thief(t)                     dark crouching silhouette (no face, no detail) working a saw; blur it in the scene
Anchors (grid units): EXH_CAT (catalytic converter centre), BUCKLE_TOP (where the webbing leaves the buckle).
"""
import math, random
from functools import lru_cache
from PIL import Image, ImageDraw
from pixanim.grid import outline

NAVY = (26, 26, 46, 255)


def _img(w, h): return Image.new('RGBA', (w, h), (0, 0, 0, 0))


# ------------------------------------------------------------------ tyres
TYRE_DARK = ((34, 34, 40), (52, 52, 60), (86, 86, 98), (20, 20, 24))
TYRE_LIGHT = ((206, 190, 156), (228, 214, 184), (246, 238, 216), (166, 150, 118))


def tyre(rot=0.0, light=0.0, wear=0.0, r=24):
    """rot: rolling angle (deg); light 0 = black carbon-filled tyre, 1 = pale unfilled rubber; wear 0..1 flattens the tread."""
    pal = [tuple(int(a + (b - a) * light) for a, b in zip(d, l)) for d, l in zip(TYRE_DARK, TYRE_LIGHT)]
    base, side, hi, deep = pal
    n = 2 * r + 6; c = n / 2; img = _img(n, n); d = ImageDraw.Draw(img)
    depth = max(0.0, 3.0 * (1 - wear))
    for k in range(20):                                             # tread blocks around the edge
        a = math.radians(rot + k * 18); a2 = a + math.radians(10)
        p = [(c + (r - 1) * math.cos(a), c + (r - 1) * math.sin(a)), (c + (r + depth) * math.cos(a), c + (r + depth) * math.sin(a)),
             (c + (r + depth) * math.cos(a2), c + (r + depth) * math.sin(a2)), (c + (r - 1) * math.cos(a2), c + (r - 1) * math.sin(a2))]
        d.polygon(p, fill=base)
    d.ellipse((c - r, c - r, c + r, c + r), fill=base)
    d.ellipse((c - r + 3, c - r + 3, c + r - 3, c + r - 3), fill=side)
    d.arc((c - r + 3, c - r + 3, c + r - 3, c + r - 3), 200, 260, fill=hi, width=2)   # sidewall sheen
    for k in range(20):                                             # grooves between blocks
        a = math.radians(rot + k * 18 - 4)
        d.line((c + (r - 3) * math.cos(a), c + (r - 3) * math.sin(a), c + (r + depth) * math.cos(a), c + (r + depth) * math.sin(a)), fill=deep)
    rr = r * 0.56                                                   # silver rim + spokes
    d.ellipse((c - rr, c - rr, c + rr, c + rr), fill=(176, 182, 194), outline=(96, 100, 112))
    d.ellipse((c - rr + 2, c - rr + 2, c + rr - 2, c + rr - 2), fill=(58, 60, 70))
    for k in range(5):
        a = math.radians(rot + k * 72)
        for w in (-0.16, 0, 0.16):
            d.line((c, c, c + (rr - 2) * math.cos(a + w), c + (rr - 2) * math.sin(a + w)), fill=(214, 220, 230))
    d.ellipse((c - 3, c - 3, c + 3, c + 3), fill=(236, 240, 248), outline=(96, 100, 112))
    return outline(img)


@lru_cache(1)
def _particles():
    rnd = random.Random(7)
    return [(rnd.uniform(3, 77), rnd.uniform(3, 41), rnd.random(), rnd.uniform(0, 6.28), rnd.choice((1, 2, 2, 3))) for _ in range(150)]


def rubber_block(t=0.0, k=1.0, w=80, h=44):
    """Cut-open slab of tread rubber; k 0..1 = how much carbon black has gone in (particles pop in, the rubber darkens)."""
    img = _img(w + 2, h + 2); d = ImageDraw.Draw(img)
    pale, dark = (196, 176, 140), (58, 56, 62)
    col = tuple(int(a + (b - a) * min(1, k * 1.2)) for a, b in zip(pale, dark))
    d.rectangle((1, 1, w, h), fill=col)
    for x in range(1, w, 12): d.rectangle((x, 1, x + 7, 4), fill=tuple(max(0, v - 18) for v in col))   # tread blocks on top
    for x, y, p, ph, s in _particles():
        if p > k or x > w - 3 or y > h - 3: continue
        jx, jy = round(math.sin(t * 7 + ph)), round(math.cos(t * 6 + ph * 1.3))
        px, py = int(x) + jx, int(y) + jy; d.rectangle((px, py, px + s - 1, py + s - 1), fill=(10, 10, 12))
        if s > 1: d.point((px, py), fill=(110, 110, 124))
    return outline(img)


def sun(t=0.0, r=12):
    n = 2 * r + 16; c = n / 2; img = _img(n, n); d = ImageDraw.Draw(img)
    for k in range(10):
        a = math.radians(t * 40 + k * 36); l = r + 4 + 2 * (k % 2)
        d.line((c + (r + 1) * math.cos(a), c + (r + 1) * math.sin(a), c + l * math.cos(a), c + l * math.sin(a)), fill=(255, 196, 40), width=2)
    d.ellipse((c - r, c - r, c + r, c + r), fill=(255, 208, 60))
    d.ellipse((c - r + 2, c - r + 2, c + r - 4, c + r - 4), fill=(255, 232, 120))
    return outline(img)


def shield(tick=1.0):
    img = _img(24, 28); d = ImageDraw.Draw(img)
    d.polygon([(1, 2), (12, 0), (22, 2), (22, 13), (12, 26), (1, 13)], fill=(56, 132, 230))
    d.polygon([(4, 4), (12, 2), (19, 4), (19, 12), (12, 22), (4, 12)], fill=(92, 168, 250))
    d.line((4, 4, 12, 2), fill=(170, 214, 255))
    if tick > 0: d.line([(7, 12), (11, 16), (11 + 6 * min(1, tick * 2 - 1) if tick > 0.5 else 11, 16 - 8 * max(0, tick * 2 - 1))], fill=(255, 255, 255), width=2)
    return outline(img)


def wear_bar(frac, col=(90, 220, 120), w=60):
    img = _img(w + 4, 9); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w + 3, 8), fill=(20, 21, 28), outline=(90, 96, 112))
    f = max(0, min(1, frac))
    if f > 0: d.rectangle((2, 2, 2 + round((w - 1) * f), 6), fill=col); d.line((2, 2, 2 + round((w - 1) * f), 2), fill=(255, 255, 255, 140))
    return outline(img)


# ------------------------------------------------------------------ seatbelt
BUCKLE_TOP = (20, 6)


def buckle(fire=0.0, t=0.0):
    """Buckle with its pretensioner tube cut open below it. fire 0..1: the charge flashes, gas fills the tube, the piston
    drives down and the buckle (with the webbing) is pulled down a few pixels."""
    img = _img(44, 80); d = ImageDraw.Draw(img)
    pull = round(6 * min(1, fire * 1.6))
    d.rectangle((15, 6 + pull - 10, 25, 22 + pull), fill=(70, 80, 104))                 # webbing + tongue going up
    for y in range(-4 + pull + int(t * 30) % 4, 20 + pull, 4): d.line((16, y, 24, y), fill=(84, 96, 124))
    d.rectangle((12, 18 + pull, 28, 26 + pull), fill=(196, 202, 214)); d.rectangle((16, 20 + pull, 24, 24 + pull), fill=(90, 96, 110))  # tongue
    d.rounded_rectangle((8, 24 + pull, 32, 44 + pull), 3, fill=(36, 37, 44)); d.rectangle((10, 26 + pull, 30, 28 + pull), fill=(60, 62, 72))
    d.rectangle((15, 34 + pull, 25, 38 + pull), fill=(232, 52, 63)); d.point((16, 35 + pull), fill=(255, 140, 140))     # red release button
    d.rectangle((19, 44 + pull, 21, 52), fill=(150, 156, 170))                         # cable to the piston
    d.rectangle((13, 48, 27, 76), fill=(120, 126, 140)); d.rectangle((15, 50, 25, 74), fill=(30, 31, 38))   # tube (cut open)
    py = 52 + round(14 * min(1, fire * 1.6))                                             # piston
    if fire > 0:                                                                         # gas behind the piston
        g = min(1, fire * 3); d.rectangle((15, py + 3, 25, 70), fill=(255, int(150 + 80 * g), 60, int(120 + 100 * (1 - fire))))
    d.rectangle((15, py, 25, py + 3), fill=(214, 220, 230))
    glow = max(0.0, 1 - abs(fire - 0.15) * 4) if fire > 0 else 0.0                       # the charge at the bottom
    d.rectangle((14, 70, 26, 77), fill=(255, int(120 + 135 * glow), int(40 + 160 * glow)) if glow > 0 else (196, 60, 40))
    d.rectangle((16, 72, 18, 75), fill=(255, 220, 120) if glow > 0 else (240, 120, 90))
    return outline(img)


# ------------------------------------------------------------------ exhaust + catalytic converter
EXH_CAT = (92, 20)


def exhaust(t=0.0, glow=0.0):
    img = _img(190, 40); d = ImageDraw.Draw(img); y = 20
    steel, steel_hi, steel_sh = (150, 154, 166), (196, 202, 214), (92, 96, 108)
    d.rectangle((0, y - 4, 186, y + 4), fill=steel); d.line((0, y - 4, 186, y - 4), fill=steel_hi); d.line((0, y + 4, 186, y + 4), fill=steel_sh)
    for x in (30, 150):                                                                  # flanges
        d.rectangle((x, y - 7, x + 3, y + 7), fill=steel_sh)
    cx = EXH_CAT[0]                                                                      # catalytic converter body (cut open)
    d.rounded_rectangle((cx - 26, y - 14, cx + 26, y + 14), 6, fill=(170, 174, 186), outline=(92, 96, 108))
    for x in range(cx - 22, cx + 23, 6): d.line((x, y - 14, x, y - 12), fill=(110, 114, 126))   # heat-shield ribs
    hot = (min(255, int(120 + 135 * glow)), int(70 + 120 * glow), int(40 + 20 * glow))
    d.rectangle((cx - 20, y - 9, cx + 20, y + 9), fill=(40, 30, 28))
    for gx in range(cx - 19, cx + 20, 4):                                                # honeycomb channels
        for gy in range(y - 8, y + 8, 4):
            f = 0.6 + 0.4 * math.sin(t * 8 + gx * 0.4 + gy * 0.7)
            d.rectangle((gx, gy, gx + 2, gy + 2), fill=tuple(int(v * (0.55 + 0.45 * f * glow)) for v in hot) if glow > 0 else (96, 90, 84))
    d.rounded_rectangle((150, y - 10, 182, y + 10), 4, fill=(132, 136, 148), outline=(92, 96, 108))   # silencer
    d.line((152, y - 8, 180, y - 8), fill=steel_hi)
    d.rectangle((182, y - 3, 189, y + 3), fill=(70, 72, 80))                            # tailpipe
    return outline(img)


METALS = {'platinum': ((214, 222, 236), (170, 180, 200), (246, 250, 255)),
          'palladium': ((188, 186, 178), (142, 140, 134), (232, 230, 222)),
          'rhodium': ((222, 226, 240), (176, 166, 196), (255, 250, 255))}


def metal_tile(kind, t=0.0, shine_at=0.0):
    body, sh, hi = METALS[kind]
    img = _img(40, 26); d = ImageDraw.Draw(img)
    d.polygon([(6, 2), (33, 2), (38, 22), (1, 22)], fill=sh)                             # ingot: top face + front face
    d.polygon([(7, 3), (32, 3), (34, 10), (5, 10)], fill=body)
    d.line((7, 3, 32, 3), fill=hi)
    s = ((t - shine_at) * 1.4) % 1.8                                                     # diagonal shine sweeping across
    if s < 1:
        x = -6 + 50 * s
        d.polygon([(x, 22), (x + 5, 22), (x + 12, 2), (x + 7, 2)], fill=hi + (200,))
    m = Image.new('L', img.size, 0); ImageDraw.Draw(m).polygon([(6, 2), (33, 2), (38, 22), (1, 22)], fill=255)
    clip = _img(40, 26); clip.paste(img, (0, 0), m)
    return outline(clip)


def thief(t=0.0):
    """Crouched silhouette in a hood, one arm sawing back and forth. Flat dark shape, a thin cool rim light, no features."""
    img = _img(34, 34); d = ImageDraw.Draw(img); k = 3 * math.sin(t * 14)
    dark, rim = (12, 12, 18), (70, 90, 130)
    d.ellipse((6, 2, 18, 14), fill=dark)                                                 # hood
    d.polygon([(6, 10), (20, 10), (24, 26), (2, 26)], fill=dark)                          # hunched body
    d.rectangle((2, 24, 26, 32), fill=dark)                                              # crouched legs
    d.line((18, 14, 26 + k, 18), fill=dark, width=3)                                     # sawing arm
    d.line((25 + k, 15, 33 + k, 19), fill=(90, 94, 104), width=1)                        # saw blade
    d.arc((6, 2, 18, 14), 200, 300, fill=rim); d.line((6, 10, 2, 26), fill=rim)
    return img


def seat(col=(54, 58, 72)):
    """Car seat, side view facing right (headrest, reclined back, cushion, runner), 40x56 grid. RETRACTOR = belt exit."""
    img = _img(40, 56); d = ImageDraw.Draw(img)
    hi, sh = tuple(min(255, v + 26) for v in col), tuple(max(0, v - 18) for v in col)
    d.rounded_rectangle((4, 0, 14, 8), 3, fill=col); d.rectangle((8, 8, 10, 11), fill=(150, 156, 170))      # headrest + posts
    d.polygon([(4, 11), (14, 11), (18, 38), (8, 40)], fill=col); d.line((5, 12, 9, 38), fill=hi)        # back
    d.rounded_rectangle((8, 36, 38, 44), 3, fill=col); d.line((10, 37, 36, 37), fill=hi)               # cushion
    d.rectangle((12, 44, 34, 47), fill=sh); d.rectangle((10, 48, 36, 50), fill=(110, 114, 126))        # base + runner
    return outline(img)


RETRACTOR = (6, 10)


def motor(t=0.0):
    """Small electric belt motor: grey can with a spinning gear and a yellow bolt (18x16)."""
    img = _img(30, 20); d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 3, 17, 17), 3, fill=(120, 126, 140)); d.rectangle((3, 5, 15, 7), fill=(170, 176, 190))
    d.polygon([(9, 8), (6, 12), (9, 12), (7, 16), (12, 10), (9, 10), (11, 8)], fill=(255, 217, 59))
    c = (23, 10)
    for k in range(8):
        a = math.radians(t * 720 + k * 45)
        d.line((c[0], c[1], c[0] + 6 * math.cos(a), c[1] + 6 * math.sin(a)), fill=(196, 202, 214), width=2)
    d.ellipse((c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4), fill=(150, 156, 170)); d.point(c, fill=(60, 62, 72))
    return outline(img)
