"""Reusable top-down cozy-room set for car-channel explainers (135x240, x8).

An episode supplies: headline, timed captions, a car sprite and beat curves
(see episodes/*/episode.py). Room, pet, props, lighting and HUD are shared.
Organic rules: no hero object is a clean rectangle (wobble_mask/blob_mask),
every large surface is textured, shading uses 4-tone hue-shifted ramps, loose
props are rotated with nearest neighbour at native resolution, and small
clutter is scattered everywhere.
"""
import math

import numpy as np

from .core import (T, BitmapFont, Camera, Canvas, Palette, Particles, PixelFont,
                   StepClock, angle_index, bake_rotations, blob_mask, cable, cycle,
                   outline, render, rotate_nn, scatter, shade, shake, sprite,
                   texture, tween_int, wobble_mask)

W, H = 135, 240          # native view (x8 = 1080x1920)
WW, WH = 135, 252        # world
SCALE = 8
PAL = Palette("endesga32")
(RUST, ORANGE, CREAM, TAN, WOOD, BROWN, DKBROWN, MAROON, RED, AMBER, GOLD, YELLOW,
 GREEN, DKGREEN, FOREST, TEAL, BLUE, SKY, CYAN, WHITE, LTGREY, GREY, SLATE, DKSLATE,
 NAVY, INK, HOT, PLUM, MAUVE, SALMON, SKIN, SKIN2) = range(32)

# 4-tone ramps: [deep shadow (cooler), shadow, base, highlight (warmer)]
FLOOR = [DKBROWN, BROWN, WOOD, SKIN2]
DESK = [BROWN, WOOD, SKIN2, TAN]
DARKWOOD = [DKBROWN, BROWN, WOOD, SKIN2]
WALL = [INK, NAVY, DKSLATE, SLATE]
PINK = [PLUM, MAUVE, SALMON, SKIN]
BLUEF = [NAVY, BLUE, SKY, CYAN]
RUGR = [NAVY, PLUM, MAUVE, SALMON]
LEAF = [TEAL, FOREST, DKGREEN, GREEN]
GRASS = [FOREST, DKGREEN, GREEN, YELLOW]
CLOTH = [SLATE, GREY, LTGREY, WHITE]
ROAD = [INK, NAVY, DKSLATE, SLATE]
CARD = [BROWN, WOOD, TAN, CREAM]
REDF = [PLUM, MAROON, RED, SALMON]
METAL = [NAVY, SLATE, GREY, LTGREY]
SEAT = [NAVY, PLUM, MAUVE, SALMON]


def _lut(pairs):
    lut = np.arange(256, dtype=np.uint8)
    for s, d in pairs.items():
        lut[s] = d
    return lut


# Lighting = palette swaps inside the same 32 colours. NIGHT steps every tone
# down and cooler, keeping ramp tones distinct so textures survive the dark.
NIGHT = _lut({RUST: MAROON, ORANGE: BROWN, CREAM: GREY, TAN: MAUVE, WOOD: PLUM, BROWN: DKBROWN,
              DKBROWN: INK, MAROON: DKBROWN, RED: MAROON, AMBER: BROWN, GOLD: WOOD, YELLOW: TAN,
              GREEN: DKGREEN, DKGREEN: FOREST, FOREST: TEAL, TEAL: INK, BLUE: DKSLATE, SKY: BLUE,
              CYAN: SKY, WHITE: LTGREY, LTGREY: GREY, GREY: SLATE, SLATE: DKSLATE,
              DKSLATE: NAVY, NAVY: INK, HOT: MAROON, PLUM: NAVY, MAUVE: PLUM, SALMON: MAUVE,
              SKIN: GREY, SKIN2: SLATE})
_LIFT = _lut({INK: NAVY, NAVY: DKSLATE, DKSLATE: SLATE, SLATE: GREY, GREY: LTGREY, LTGREY: WHITE,
              DKBROWN: PLUM, PLUM: MAUVE, MAUVE: SALMON, MAROON: MAUVE, TEAL: FOREST,
              FOREST: DKGREEN, DKGREEN: GREEN, BROWN: SLATE, WOOD: GREY, TAN: LTGREY,
              BLUE: SKY, SKY: CYAN})
MOON = _LIFT[NIGHT]                       # cool moonlight: night lifted one step
WARM = _lut({DKBROWN: BROWN, BROWN: WOOD, WOOD: SKIN2, SKIN2: TAN, PLUM: MAUVE, NAVY: DKSLATE,
             DKSLATE: SLATE, INK: DKBROWN, MAUVE: SALMON, TEAL: FOREST, SLATE: GREY})
SHADOW = _lut({WOOD: BROWN, BROWN: DKBROWN, DKBROWN: INK, PLUM: NAVY, MAUVE: PLUM, DKSLATE: NAVY,
               SLATE: DKSLATE, NAVY: INK, DKGREEN: FOREST, GREEN: DKGREEN, TAN: WOOD,
               CREAM: TAN, GREY: SLATE, LTGREY: GREY, FOREST: TEAL, SKIN2: WOOD, SALMON: MAUVE})

HEAD = PixelFont(size=20)
CAP = PixelFont(size=10)
TINY = BitmapFont()

# ----------------------------------------------------------------- sprites ---
CAR_KEY = {"o": INK, "w": INK, "R": RED, "h": SALMON, "r": MAROON, "c": SKY, "C": CYAN,
           "y": YELLOW, "W": WHITE, "H": HOT}
DEFAULT_CAR = """
..ooooooo..
.oyhRWRryo.
.ohRRWRRro.
wohRRWRRrow
wohcCCCcrow
wohcCCccrow
.ohcccccro.
.ohRRWRRro.
.ohRhWRRro.
.ohcccccro.
wohRRWRRrow
wohRRWRRrow
.oHRRRRRHo.
..ooooooo..
"""


def make_car(art=DEFAULT_CAR, key=None, n=16):
    """Bake n RotSprite angles for a top-down car facing up (0 deg)."""
    return bake_rotations(sprite(art, key or CAR_KEY), n)


def _cat(awake, frame):
    """Procedural top-down tabby cat, one pre-drawn sprite per pose."""
    c = Canvas(22, 17, T)
    if not awake:
        c.ellipse(3, 2 - frame, 18, 13 + frame, fill=AMBER)
        c.ellipse(5, 4 - frame, 13, 7, fill=GOLD)                 # lit back
        for x in (9, 12, 15, 18):
            c.line(x, 3 - frame, x - 1, 6, RUST)
        c.line(19, 11, 14, 14, ORANGE); c.line(19, 12, 14, 15, ORANGE)
        c.line(14, 14, 9, 14, ORANGE); c.line(14, 15, 9, 15, ORANGE)
        c.px(8, 14, CREAM); c.px(8, 15, CREAM)
        c.ellipse(1, 7, 10, 8, fill=GOLD)
        c.poly([(2, 8), (2, 5), (5, 7)], fill=AMBER)
        c.poly([(7, 7), (9, 5), (10, 8)], fill=AMBER)
        c.px(3, 7, SALMON); c.px(8, 7, SALMON)
        c.line(3, 11, 4, 11, RUST); c.line(7, 11, 8, 11, RUST)
        c.px(5, 12, SALMON); c.px(6, 12, SALMON)
        c.px(16, 9, ORANGE); c.px(17, 10, ORANGE)                  # belly shade
    else:
        c.ellipse(4, 6, 12, 9, fill=AMBER)
        c.ellipse(5, 7, 7, 4, fill=GOLD)
        for x in (7, 10, 13):
            c.line(x, 9, x, 11, RUST)
        c.ellipse(5, 1, 10, 8, fill=GOLD)
        c.poly([(5, 3), (6, 0), (8, 2)], fill=AMBER)
        c.poly([(14, 3), (13, 0), (11, 2)], fill=AMBER)
        c.px(6, 1, SALMON); c.px(13, 1, SALMON)
        if frame == 2:
            c.line(7, 4, 8, 4, INK); c.line(11, 4, 12, 4, INK)
        else:
            c.rect(7, 3, 2, 2, GREEN); c.px(8, 4, INK)
            c.rect(11, 3, 2, 2, GREEN); c.px(11, 4, INK)
        c.px(9, 6, SALMON); c.px(10, 6, SALMON)
        tx = [17, 18, 16][frame % 3]
        c.line(15, 12, tx, 14, ORANGE); c.px(tx, 15, ORANGE)
    return outline(c.a.copy(), INK)


CATS = {(aw, f): _cat(aw, f) for aw in (0, 1) for f in (0, 1, 2)}

PLANT = sprite("""
..g..G..
.gGgGgg.
gGgYgGgG
.GgGgGg.
.gG.Gg..
..tTTt..
.tTTTTt.
.tTTTTt.
..tttt..
""", {"g": GREEN, "G": DKGREEN, "Y": YELLOW, "t": RUST, "T": ORANGE})

MUG = sprite("""
.ooo..
oWCWoo
oWWWo.o
oLWLoo
.ooo..
""", {"o": INK, "W": WHITE, "C": CREAM, "L": LTGREY})

SNEAKER = sprite("""
.ooo.
oWWWo
oBBWo
oBBLo
oBBWo
.ooo.
""", {"o": INK, "W": WHITE, "B": BLUE, "L": LTGREY})

CONE = sprite("""
..o..
.oAo.
.oWo.
oAAAo
ooooo
""", {"o": INK, "A": AMBER, "W": WHITE})

# Small clutter (3-8 px). Rotated randomly when scattered.
CLUTTER = [
    sprite("WWo\nWLo", {"W": WHITE, "L": LTGREY, "o": GREY}),                       # paper ball
    sprite("RRR\nrRr", {"R": RED, "r": MAROON}),                                    # lego brick
    sprite("YY\nGY", {"Y": GOLD, "G": AMBER}),                                       # coin
    sprite("ooo\noWo\noRo\nooo", {"o": INK, "W": LTGREY, "R": RED}),                 # soda can
    sprite("TTTTTp", {"T": GOLD, "p": SALMON}),                                      # pencil
    sprite("sss\nsSs\nsss\n.ss", {"s": LTGREY, "S": GREY}),                          # sock
    sprite("KKKK\nKcKK\nKKKK", {"K": DKSLATE, "c": RED}),                            # game cart
    sprite("c.c\n.c.", {"c": TAN}),                                                  # crumbs
    sprite("ppp\npPp\nppp", {"p": CREAM, "P": TAN}),                                 # sticky note
]


def _prop(mask, ramp, rng, kind="noise", density=0.06, line=INK):
    a = shade(mask, ramp, line=line)
    texture(a, ramp, rng, kind, density)
    return a


def pizza_box(rng):
    m = wobble_mask(16, 15, rng, depth=1, seg=(3, 6), chip=(1, 2))
    c = Canvas(18, 17, T)
    c.a = _prop(m, CARD, rng, "specks", 0.05)
    c.line(3, 3, 13, 3, WOOD)            # lid crease
    c.line(3, 4, 3, 12, WOOD)
    c.ellipse(5, 6, 7, 6, fill=RED)      # logo stain
    c.px(7, 8, CREAM); c.px(9, 7, GOLD)
    return rotate_nn(c.a, 27)


def tshirt(rng, ramp=BLUEF):
    m = blob_mask(14, 11, rng, 2)
    m[0:3, 4:10] = False                 # neckline
    m[1:4, 0:3] = True
    m[1:4, 11:14] = True                 # sleeves
    return _prop(m, ramp, rng, "wrinkle", 0.12)


def laptop(rng):
    m = wobble_mask(16, 11, rng, depth=1, seg=(3, 6), chip=(1, 1))
    c = Canvas(18, 13, T)
    c.a = shade(m, METAL, line=INK)
    c.rect(3, 2, 12, 5, NAVY)
    c.line(4, 3, 8, 3, SKY); c.line(4, 5, 7, 5, CYAN)
    for x in range(3, 15, 2):
        c.px(x, 9, SLATE)
    return c.a



DENIM = [NAVY, DKSLATE, BLUE, SKY]
BLACKJ = [INK, NAVY, DKSLATE, SLATE]
HAIR = [INK, INK, DKBROWN, BROWN]
ARM = [BROWN, WOOD, SKIN2, TAN]


def jeans(rng, ramp=DENIM):
    m = np.zeros((16, 10), bool)
    m[:4] = True
    m[3:, 0:4] = True
    m[3:, 6:10] = True
    m &= wobble_mask(10, 16, rng, 1, (2, 4), (1, 1))
    a = _prop(m, ramp, rng, "wrinkle", 0.15)
    a[1, 2:9] = np.where(a[1, 2:9] != T, ramp[1], T)          # waistband seam
    return a


def hoodie(rng, ramp):
    m = blob_mask(16, 14, rng, 2)
    m[0:3, 5:11] = True                                       # hood
    m[3:9, 0:2] = True
    m[3:9, 14:16] = True                                      # sleeves
    a = _prop(m, ramp, rng, "wrinkle", 0.14)
    a[9, 5:11] = np.where(a[9, 5:11] != T, ramp[0], T)        # pocket
    return a


def towel(rng, ramp):
    a = _prop(wobble_mask(13, 8, rng, 1, (2, 5), (1, 2)), ramp, rng, "weave", 0.1)
    for x in (3, 9):
        a[1:7, x] = np.where(a[1:7, x] != T, ramp[3], T)
    return a


def hanging(rng, ramp, w, h):
    """A garment on a hanger: sloped shoulders, wrinkled body, hook on top."""
    m = wobble_mask(w, h, rng, 1, (2, 5), (1, 2), "lrb")
    m[0, 0] = m[0, -1] = False
    a = np.pad(_prop(m, ramp, rng, "wrinkle", 0.2), ((1, 0), (0, 0)), constant_values=T)
    a[0, w // 2 + 1] = GREY
    return a


GARMENTS = [BLUEF, REDF, LEAF, CLOTH, PINK, CARD, DENIM, BLACKJ, SEAT]


def wardrobe(c, r, avoid):
    """Open wardrobe on the back wall, stuffed with clothes that spill out
    onto the floor in one heap (the room's clutter lives here)."""
    x0, y0, w, h = 9, 3, 38, 33
    _put(c, _prop(wobble_mask(w, h, r, 1, (3, 7), (1, 2)), DARKWOOD, r, "grain", 0.08), x0, y0, avoid)
    iw, ih = w - 8, h - 8
    inner = np.where(wobble_mask(iw, ih, r, 1, (3, 7), (1, 2)), np.uint8(INK), np.uint8(T))
    texture(inner, [INK, NAVY], r, "specks", 0.08)
    c.blit(inner, x0 + 4, y0 + 4)
    c.rect(x0 + 4, y0 + 6, iw, 1, GREY)                       # hanging rail
    x = x0 + 4
    k = 0
    while x < x0 + 4 + iw - 3:                                 # packed hangers
        gw = int(r.integers(4, 7))
        g = hanging(r, GARMENTS[(k * 5 + 2) % len(GARMENTS)], gw, int(r.integers(12, 19)))
        c.blit(rotate_nn(g, float(r.choice([-8, -4, 0, 5, 9]))), x - 1, y0 + 5)
        x += gw - 1
        k += 1
    # stuffed shelf at the bottom of the wardrobe
    for i in range(6):
        b = _prop(blob_mask(int(r.integers(7, 11)), int(r.integers(5, 7)), r, 2),
                  GARMENTS[(i * 4 + 1) % len(GARMENTS)], r, "wrinkle", 0.2)
        c.blit(b, x0 + 3 + i * 5, y0 + h - 10 + int(r.integers(-1, 2)))
    # doors swung open (diagonal planks)
    c.poly([(x0, y0 + 2), (x0 - 6, y0 + 7), (x0 - 8, y0 + h + 4), (x0, y0 + h - 1)], fill=WOOD, line=INK)
    c.poly([(x0 + w - 1, y0 + 2), (x0 + w + 6, y0 + 8), (x0 + w + 8, y0 + h + 5), (x0 + w - 1, y0 + h - 1)],
           fill=WOOD, line=INK)
    c.line(x0 - 5, y0 + 18, x0 - 5, y0 + 21, GOLD)
    c.line(x0 + w + 5, y0 + 19, x0 + w + 5, y0 + 22, GOLD)
    texture(c.a, DARKWOOD, r, "grain", 0.15,
            mask=_poly_mask([(x0 - 7, y0), (x0 + w + 8, y0), (x0 + w + 8, y0 + h + 6), (x0 - 7, y0 + h + 6)])
            & ~_poly_mask([(x0 + 1, y0), (x0 + w - 2, y0), (x0 + w - 2, y0 + h), (x0 + 1, y0 + h)]))
    c.blit(rotate_nn(hoodie(r, BLACKJ), 20), x0 + w - 2, y0 + 4)          # draped over the door
    # the spill: heavy at the wardrobe mouth, thinning out across the floor
    ox, oy = x0 + w // 2, y0 + h + 2
    pieces = [jeans(r), hoodie(r, REDF), tshirt(r, LEAF), towel(r, PINK), jeans(r, BLACKJ),
              tshirt(r, CLOTH), hoodie(r, SEAT), tshirt(r, CARD), towel(r, BLUEF), tshirt(r, REDF),
              jeans(r), tshirt(r, BLUEF), hoodie(r, LEAF)]
    for i, g in enumerate(pieces):
        d = 3 + 2.5 * i ** 0.9
        a = r.uniform(0.15, 2.4)
        g = rotate_nn(g, float(r.integers(-70, 70)))
        px = int(ox + d * math.cos(a) * 1.15 - g.shape[1] // 2)
        py = int(oy - 6 + d * math.sin(a) * 0.9 - g.shape[0] // 2)
        _put(c, g, max(6, px), max(y0 + h - 8, py), avoid)
    # basket overflowing next to the heap
    bk = _prop(blob_mask(15, 11, r, 1), CARD, r, "weave", 0.25)
    _put(c, bk, x0 + w + 4, oy + 6, avoid)
    for i in range(3):
        g = rotate_nn(tshirt(r, GARMENTS[i * 3 % len(GARMENTS)])[:7, :10], float(r.integers(-40, 40)))
        c.blit(g, x0 + w + 4 + i * 3, oy + 2 + i)
    for i, spr in enumerate((CLUTTER[6], CLUTTER[6], SNEAKER)):            # socks + a shoe
        _put(c, rotate_nn(spr, float(r.integers(-60, 60))), ox - 18 + i * 13, oy + 22 + (i % 2) * 4, avoid)


def _coder(pose):
    """Top-down coder seen from behind (main-guy palette: dark messy hair,
    brown skin, white tee, silver glasses). pose: 'a'/'b' typing, 'look'."""
    c = Canvas(20, 19, T)
    lh, rh = {"a": (0, 1), "b": (1, 0), "look": (2, 2)}[pose]
    for (sx, hx, hy) in ((5, 6, 1 + lh), (14, 12, 1 + rh)):            # arms to the keys
        c.line(sx, 10, hx, hy + 1, SKIN2)
        c.line(sx + (1 if sx < 10 else -1), 10, hx + (1 if sx < 10 else -1), hy + 1, WOOD)
        c.rect(hx, hy, 2, 2, SKIN2)
    tee = shade(blob_mask(16, 10, np.random.default_rng(4), 1), CLOTH)
    c.blit(tee, 2, 9)
    c.line(6, 12, 13, 12, LTGREY)                                       # shoulder fold
    if pose == "look":
        c.ellipse(5, 4, 10, 9, fill=INK)
        c.ellipse(4, 7, 6, 6, fill=SKIN2)                               # face turned left
        c.px(4, 9, LTGREY); c.px(5, 9, GREY); c.px(6, 9, LTGREY)        # glasses
        c.px(5, 11, WOOD)
        c.px(9, 5, DKBROWN); c.px(11, 6, DKBROWN)
    else:
        c.ellipse(5, 4, 10, 9, fill=INK)
        c.px(7, 6, DKBROWN); c.px(10, 5, DKBROWN); c.px(12, 7, DKBROWN)  # hair shine
        c.px(4, 8, SKIN2); c.px(15, 8, SKIN2)                            # ears
        c.px(5, 7, LTGREY); c.px(14, 7, LTGREY)                          # glasses arms
    c.px(9, 3, INK); c.px(10, 2, INK); c.px(11, 3, INK)                  # cowlicks
    return outline(c.a.copy(), INK)


CODER = {p: _coder(p) for p in ("a", "b", "look")}


def _code(seed=9, n=60):
    """Fake syntax-highlighted lines: (indent, [(len, colour)], chars)."""
    r = np.random.default_rng(seed)
    out, ind = [], 0
    for _ in range(n):
        toks = [(int(r.integers(2, 5)), MAUVE)] if r.random() < 0.5 else []
        for _ in range(int(r.integers(1, 4))):
            toks.append((int(r.integers(1, 5)), (CYAN, WHITE, GREEN, GOLD, LTGREY)[int(r.integers(0, 5))]))
        while sum(l + 1 for l, _ in toks) + ind > 17:
            toks.pop()
        if not toks:
            toks = [(2, GREY)]
        out.append((ind, toks, sum(l for l, _ in toks)))
        ind = max(0, min(6, ind + int(r.choice([-2, 0, 0, 2]))))
    return out


CODE = _code()

# ------------------------------------------------------------------- room ---
TRACK = dict(cx=67, cy=168, rx=40, ry=22)
LAMP = (121, 42)
NLIGHT = (125, 128)
WINDOW = (0, 70, 8, 48)    # x, y, w, h on the left wall


def _circle_mask(cx, cy, r):
    yy, xx = np.mgrid[0:WH, 0:WW]
    return (xx - cx) ** 2 + ((yy - cy) * 1.3) ** 2 <= r * r


def _poly_mask(pts):
    c = Canvas(WW, WH, 0)
    c.poly(pts, fill=1)
    return c.a.astype(bool)


def _put(c, spr, x, y, avoid):
    """Blit and mark the footprint so scattered clutter keeps clear."""
    c.blit(spr, x, y)
    big = np.zeros((WH + 64, WW + 64), bool)
    big[y + 32:y + 32 + spr.shape[0], x + 32:x + 32 + spr.shape[1]] = spr != T
    avoid |= big[32:32 + WH, 32:32 + WW]


def _dashed(c, x, y0, y1, col, rng, seg=(6, 16)):
    y = y0
    while y < y1:
        k = int(rng.integers(*seg))
        c.rect(x, y, 1, min(k, y1 - y), col)
        y += k + int(rng.integers(1, 3))


def build_room(seed=3):
    """Static world layer, drawn once."""
    r = np.random.default_rng(seed)
    c = Canvas(WW, WH, BROWN)
    avoid = np.zeros((WH, WW), bool)
    floor = np.arange(WH)[:, None] >= 34
    # --- floor: 8 px boards, broken seams, alternating tones, grain
    for k, x0 in enumerate(range(0, WW, 8)):
        base = (BROWN, WOOD, BROWN, BROWN, WOOD)[k % 5]
        c.rect(x0, 34, 8, WH, base)
        _dashed(c, x0 + 7, 34, WH, DKBROWN, r)
        _dashed(c, x0, 34, WH, SKIN2 if base == WOOD else WOOD, r, (4, 12))
        y = 34 - int(r.integers(0, 50))
        while y < WH:                                        # butt joints
            c.rect(x0, y, 7, 1, DKBROWN)
            y += int(r.integers(30, 70))
    texture(c.a, FLOOR, r, "grain", 0.05, mask=floor)
    texture(c.a, FLOOR, r, "noise", 0.02, mask=floor)
    # --- back wall: patterned wallpaper, wobbly baseboard + shadow
    c.rect(0, 0, WW, 34, NAVY)
    for y in range(4, 30, 6):
        for x in range((y // 6) % 2 * 4, WW, 8):
            c.px(x, y, DKSLATE); c.px(x + 1, y + 1, DKSLATE); c.px(x - 1, y + 1, DKSLATE)
            c.px(x, y + 2, DKSLATE)
    texture(c.a[:30], WALL, r, "specks", 0.02)
    c.rect(0, 0, WW, 2, INK)
    for x in range(0, WW, 5):
        c.px(x + int(r.integers(0, 3)), 2, INK)
    bb = wobble_mask(WW, 5, r, depth=1, seg=(4, 9), chip=(0, 0), sides="tb")
    c.blit(shade(bb, WALL), 0, 30)
    sh = wobble_mask(WW, 3, r, depth=1, seg=(3, 8), chip=(0, 0), sides="b")
    m = np.zeros((WH, WW), bool); m[35:38] = sh
    c.remap(SHADOW, m)
    # --- side walls (top faces) with wobbly inner edge
    # (masks run 3 px past the frame so their straight outer bands are off-screen)
    for x0, sides in ((-3, "r"), (WW - 8, "l")):
        a = shade(wobble_mask(11, WH, r, depth=1, seg=(4, 10), chip=(0, 0), sides=sides), WALL)
        texture(a, WALL, r, "specks", 0.05)
        c.blit(a, x0, 0)
    # window frame + curtains + sill
    wx, wy, ww, wh = WINDOW
    c.rect(wx, wy, ww, wh, LTGREY)
    sill = wobble_mask(4, wh - 6, r, 1, (3, 7), (1, 1), "lr")
    c.blit(shade(sill, CLOTH), 8, wy + 3)
    for cy0 in (wy - 9, wy + wh - 4):
        c.blit(_prop(blob_mask(9, 14, r, 2), PINK, r, "wrinkle", 0.25), 3, cy0)
    # radiator
    c.blit(_prop(wobble_mask(5, 18, r, 1, (3, 6), (1, 1)), METAL, r, "specks"), 9, 124)
    for y in range(127, 140, 3):
        c.rect(10, y, 3, 1, SLATE)
    # car poster, rotated, taped corners
    pc = Canvas(19, 14, INK)
    pc.rect(1, 1, 17, 6, SKY); pc.rect(1, 7, 17, 6, DKSLATE)
    pc.poly([(3, 10), (6, 6), (12, 6), (15, 9), (16, 11), (2, 11)], fill=RED)
    pc.rect(7, 7, 4, 1, CYAN); pc.rect(4, 11, 2, 2, INK); pc.rect(12, 11, 2, 2, INK)
    pc.px(8, 3, WHITE); pc.px(13, 2, WHITE)
    pc.rect(0, 0, 2, 2, CREAM); pc.rect(17, 12, 2, 2, CREAM)
    c.blit(rotate_nn(pc.a, -8), 56, 8)
    # sticky notes above the desk + thermometer
    for i, (nx, ny, col, ang) in enumerate(((86, 3, YELLOW, -8), (93, 2, SALMON, 6), (100, 4, CYAN, -4),
                                            (75, 6, YELLOW, 10))):
        n = np.full((5, 5), col, np.uint8)
        n[2, 1:4] = INK if i % 2 else NAVY
        n[3, 1:3] = INK if i % 2 else NAVY
        c.blit(rotate_nn(n, ang), nx, ny)
    c.blit(_prop(wobble_mask(4, 18, r, 1, (3, 6), (1, 1)), CLOTH, r, "specks"), 121, 3)
    c.ellipse(120, 19, 6, 6, fill=RED, line=INK)
    # --- desk (top right): dual monitors, rgb keyboard, mug, cans, duck
    dm = wobble_mask(48, 19, r, depth=1, seg=(3, 7), chip=(1, 3))
    m = np.zeros((WH, WW), bool); m[31:50, 79:127] = dm
    c.remap(SHADOW, m)
    _put(c, _prop(dm, DESK, r, "grain", 0.08), 77, 29, avoid)
    c.blit(shade(wobble_mask(23, 17, r, 1, (3, 6), (1, 1)), [INK, INK, INK, DKSLATE]), 80, 10)
    c.blit(shade(wobble_mask(17, 14, r, 1, (3, 6), (1, 1)), [INK, INK, INK, DKSLATE]), 104, 13)
    c.rect(89, 9, 3, 1, INK); c.px(90, 8, HOT)                        # webcam
    c.rect(90, 27, 4, 3, DKSLATE); c.rect(111, 27, 4, 3, DKSLATE)    # stands
    kb = Canvas(22, 7, T)
    kb.a = shade(wobble_mask(20, 5, r, 1, (3, 6), (1, 1)), ROAD, line=INK)
    c.blit(rotate_nn(kb.a, 5), 86, 34)
    c.blit(sprite("oo\noW\noo", {"o": INK, "W": WHITE}), 109, 39)     # mouse
    cable(c, [(110, 39), (114, 33), (112, 29)], INK)
    c.blit(MUG, 78, 35)
    for i, col in enumerate((GREEN, CYAN)):                            # energy drinks
        c.blit(sprite("ooo\noCo\noWo\nooo", {"o": INK, "C": col, "W": WHITE}), 79 + i * 4, 29)
    c.blit(sprite(".yy.\nyyyo\n.yyy\n.yy.", {"y": YELLOW, "o": ORANGE}), 104, 42)   # rubber duck
    c.blit(rotate_nn(sprite("ppppp\npPPPp\nppppp\npPPpp", {"p": WHITE, "P": LTGREY}), -22), 112, 41)
    c.line(80, 45, 86, 43, GOLD); c.px(86, 43, SALMON)                 # pencil
    c.ellipse(118, 39, 8, 5, fill=SLATE, line=INK)                     # desk lamp
    c.line(121, 39, 120, 33, INK)
    c.poly([(115, 33), (124, 31), (122, 28), (117, 29)], fill=GOLD, line=INK)
    cable(c, [(124, 41), (128, 48), (125, 30)], INK)
    # chair seat, rotated a little
    _put(c, rotate_nn(_prop(blob_mask(18, 14, r, 1), SEAT, r, "weave", 0.06), 12), 89, 50, avoid)
    # --- wardrobe overflowing with clothes (the clutter zone)
    wardrobe(c, r, avoid)
    # --- trash can by the desk with paper balls (small second cluster)
    _put(c, _prop(blob_mask(8, 8, r, 1), METAL, r, "specks"), 66, 40, avoid)
    for i, (dx, dy) in enumerate(((2, -1), (-4, 6), (5, 8), (9, 3), (0, 10))):
        c.blit(rotate_nn(CLUTTER[0], 30.0 * i), 66 + dx, 40 + dy)
    _put(c, pizza_box(r), 58, 54, avoid)
    for i, col in enumerate((GREEN, CYAN, GREEN)):                     # empty energy cans
        can = sprite("ooo\noCo\noCo\nooo", {"o": INK, "C": col})
        c.blit(rotate_nn(can, (90, 0, 60)[i]), 75 + i * 4, 58 + (i % 2) * 3)
    # --- bed (right): frame, rumpled blanket with folds, pillow, laptop, shirt
    _put(c, _prop(wobble_mask(36, 70, r, 1, (4, 9), (1, 2)), DARKWOOD, r, "grain", 0.05), 98, 66, avoid)
    bla = shade(wobble_mask(36, 52, r, depth=2, seg=(3, 7), chip=(2, 4), sides="tlbr"), PINK, line=PLUM)
    texture(bla, PINK, r, "weave", 0.05)
    texture(bla, PINK, r, "wrinkle", 0.06)
    c.blit(bla, 95, 84)
    for (x0, y0, x1, y1) in ((99, 92, 108, 104), (110, 118, 120, 130), (104, 108, 112, 112)):
        c.line(x0, y0, x1, y1, MAUVE); c.line(x0 + 1, y0, x1 + 1, y1, SKIN)
    c.blit(rotate_nn(_prop(blob_mask(26, 13, r, 1), CLOTH, r, "wrinkle", 0.15, line=SLATE), 4), 102, 68)
    c.blit(rotate_nn(laptop(r), 18), 101, 95)
    c.blit(rotate_nn(tshirt(r), -30), 110, 120)
    c.blit(sprite("oCo\noYo\nooo", {"o": INK, "C": CREAM, "Y": YELLOW}), 124, 126)  # night-light
    # --- cat cushion
    _put(c, _prop(blob_mask(26, 18, r, 2), REDF, r, "weave", 0.06), 54, 92, avoid)
    # --- rug (rotated), track with kerbs, cones, tree
    rug = shade(wobble_mask(112, 74, r, depth=1, seg=(3, 7), chip=(2, 3)), RUGR, line=INK)
    texture(rug, RUGR, r, "weave", 0.06)
    for x in range(2, 110, 2):
        rug[0, x] = CREAM
        rug[-1, x] = CREAM
    rug = rotate_nn(rug, -4)
    _put(c, rug, TRACK["cx"] - rug.shape[1] // 2, TRACK["cy"] - rug.shape[0] // 2, avoid)
    cx, cy, rx, ry = TRACK["cx"], TRACK["cy"], TRACK["rx"], TRACK["ry"]
    c.ellipse(cx - rx - 9, cy - ry - 9, 2 * rx + 19, 2 * ry + 19, fill=INK)
    c.ellipse(cx - rx - 8, cy - ry - 8, 2 * rx + 17, 2 * ry + 17, fill=DKSLATE)
    c.ellipse(cx - rx + 8, cy - ry + 8, 2 * rx - 15, 2 * ry - 15, fill=INK)
    c.ellipse(cx - rx + 9, cy - ry + 9, 2 * rx - 17, 2 * ry - 17, fill=DKGREEN)
    tm = np.zeros((WH, WW), bool)
    tm[cy - ry - 10:cy + ry + 11, cx - rx - 10:cx + rx + 11] = True
    texture(c.a, [NAVY, DKSLATE, SLATE], r, "specks", 0.08, mask=tm)
    texture(c.a, GRASS, r, "noise", 0.12, mask=tm)
    for k in range(24):
        a = 2 * math.pi * k / 24
        c.px(cx + rx * math.cos(a), cy + ry * math.sin(a), LTGREY)
    for k in range(40):                                   # red/white kerbs on bends
        a = 2 * math.pi * k / 40
        if abs(math.cos(a)) > 0.75:
            col = RED if k % 2 else WHITE
            c.px(cx + (rx + 8) * math.cos(a), cy + (ry + 8) * math.sin(a), col)
            c.px(cx + (rx - 8) * math.cos(a), cy + (ry - 8) * math.sin(a), col)
    for i in range(5):
        c.rect(cx - 2 + (i % 2) * 2, cy + ry - 5 + i * 2, 2, 2, WHITE if i % 2 else INK)
    c.blit(CONE, cx - 12, cy - 6); c.blit(CONE, cx + 7, cy - 8)
    c.blit(sprite("gg\ngG\ntt", {"g": GREEN, "G": DKGREEN, "t": BROWN}), cx - 3, cy + 2)
    # --- battery charger + cables
    _put(c, _prop(wobble_mask(7, 9, r, 1, (2, 4), (1, 1)), ROAD, r, "specks"), 116, 196, avoid)
    cable(c, [(119, 205), (117, 214), (100, 206), (98, 194)], INK, DKSLATE)
    cable(c, [(122, 196), (126, 170), (126, 134)], INK)
    # --- floor clutter: pizza box, shoes, books, beanbag, bookshelf, clothes
    _put(c, rotate_nn(SNEAKER, 25), 52, 236, avoid)
    _put(c, rotate_nn(SNEAKER, -10), 60, 238, avoid)
    _put(c, rotate_nn(_prop(wobble_mask(12, 4, r, 1, (3, 5), (1, 1)), BLUEF, r, "specks"), 12), 78, 230, avoid)
    _put(c, rotate_nn(_prop(wobble_mask(10, 4, r, 1, (3, 5), (1, 1)), REDF, r, "specks"), -20), 80, 236, avoid)
    _put(c, _prop(blob_mask(28, 24, r, 2), BLUEF, r, "wrinkle", 0.1), 100, 214, avoid)
    _put(c, _prop(wobble_mask(16, 26, r, 1, (3, 7), (1, 2)), DARKWOOD, r, "grain"), 8, 222, avoid)
    for i in range(6):
        c.rect(10 + i * 2, 225 + (i % 3), 2, 7 - (i % 3), (RED, GOLD, GREEN, BLUE, MAUVE, CREAM)[i])
        c.rect(10 + i * 2, 235 + (i % 2), 2, 6 - (i % 2), (BLUE, RED, CREAM, GOLD, SKY, GREEN)[i])
    c.blit(PLANT, 26, 222)
    # front wall cut with a wobbly top
    c.blit(shade(wobble_mask(WW, 9, r, 1, (4, 9), (0, 0), "t"), WALL), 0, WH - 6)
    return c


class Lights:
    def __init__(self):
        self.lamp_in = _circle_mask(*LAMP, 9)
        self.lamp_out = _circle_mask(*LAMP, 18)
        self.nl_in = _circle_mask(*NLIGHT, 7)
        self.nl_out = _circle_mask(*NLIGHT, 13)
        wx, wy, ww, wh = WINDOW
        self.moon = _poly_mask([(8, wy + 2), (8, wy + wh - 2), (50, 166), (66, 146)])
        self.screen = _poly_mask([(86, 30), (110, 30), (114, 62), (82, 62)])

    def apply(self, c, mode, nightlight=True):
        if mode == "day":
            return
        base = c.a.copy()
        c.a = NIGHT[base]
        c.a = np.where(self.moon, MOON[base], c.a)
        c.a = np.where(self.screen, MOON[base], c.a)
        c.a = np.where(self.lamp_out, base, c.a)
        c.a = np.where(self.lamp_in, WARM[base], c.a)
        if nightlight:
            c.a = np.where(self.nl_out, base, c.a)
            c.a = np.where(self.nl_in, WARM[base], c.a)


def rag_panel(v, x, y, w, h, seed, fill=INK, edge=DKSLATE, speck=NAVY):
    """Hand-cut HUD panel: wobbly border, chipped corners, speckled fill."""
    r = np.random.default_rng(seed)
    m = wobble_mask(w, h, r, depth=1, seg=(3, 7), chip=(1, 2))
    a = np.where(m, np.uint8(fill), np.uint8(T))
    yy, xx = np.nonzero(m)
    k = ((xx * 7 + yy * 13) % 19 == 0) | ((xx * 5 + yy * 3) % 29 == 0)
    a[yy[k], xx[k]] = speck
    v.blit(outline(a, edge), x - 1, y - 1)


# ------------------------------------------------------------------- scene ---
class CozyEpisode:
    """Episode = dict(headline, captions, car_art, beats, curves...)."""

    def __init__(self, ep):
        self.ep = ep
        self.room = build_room()
        self.lights = Lights()
        self.cars = make_car(ep.get("car_art", DEFAULT_CAR), ep.get("car_key"))
        self.clock = StepClock(ep["duration"], 30, ep.get("holds", (3, 3, 2, 4, 3, 3, 2, 4, 3, 3)))
        self.snow = Particles(5)
        self.steam = Particles(6)
        self.fx = Particles(7)
        self._sim_step = -1
        self._theta = self._theta_table()

    def _theta_table(self):
        dt, th, out = 1 / 300, math.pi / 2, []
        for i in range(int(self.ep["duration"] * 300) + 2):
            out.append(th)
            th += self.ep["car_speed"](i * dt) * dt
        return out

    def _sim(self, step):
        """Advance particles exactly once per step, deterministically."""
        b = self.ep["beats"]
        wx, wy, ww, wh = WINDOW
        while self._sim_step < step:
            self._sim_step += 1
            s = self._sim_step
            t = self.clock.t(s)
            r = self.snow.rng
            if t > b["snow"]:
                self.snow.emit(r.integers(wx + 1, wx + ww - 1), wy + 1, 0, 1, 60, [WHITE],
                               every=int(r.integers(1, 3)))
            for q in self.snow.p:
                if s % 4 == 0:
                    q["x"] += int(r.integers(-1, 2))
            self.snow.step((wx + 1, wy + 1, wx + ww - 1, wy + wh - 1))
            if s % 2 == 0:
                self.steam.emit(82 + int(self.steam.rng.integers(0, 3)), 33, 0, -1, 6,
                                [WHITE, LTGREY, GREY])
            for q in self.steam.p:
                if q["age"] % 3 == 2:
                    q["x"] += int(self.steam.rng.integers(-1, 2))
            self.steam.step()
            self.fx.step()

    def car_pose(self, t):
        th = self._theta[min(len(self._theta) - 1, int(t * 300))]
        x = TRACK["cx"] + TRACK["rx"] * math.cos(th)
        y = TRACK["cy"] + TRACK["ry"] * math.sin(th)
        vx, vy = -TRACK["rx"] * math.sin(th), TRACK["ry"] * math.cos(th)
        return x, y, math.degrees(math.atan2(vx, -vy))

    def _typed(self, t):
        """Characters typed so far: ~11 chars/s, paused while looking up."""
        b = self.ep["beats"]
        return 64 + int(min(t, b["crank"]) * 11) + int(max(0.0, t - b["crank_end"] - 0.6) * 11)

    def _emissive(self, c, t, step):
        """Light sources drawn AFTER the lighting swap so they stay bright."""
        ep, b = self.ep, self.ep["beats"]
        k = cycle(t, (0.6, 0.4, 0.7, 0.5))
        for i, x in enumerate(range(52, WW - 10, 8)):
            y = 4 + (i % 3 == 1) + (i % 3 == 2) * 2
            c.rect(x, y, 2, 2, (GOLD, HOT, CYAN, GREEN)[(i + k) % 4])
        # left monitor: code being typed (stepped), scrolling, blinking cursor
        c.rect(82, 12, 19, 13, NAVY)
        for yy in range(12, 25, 2):                         # faint scanlines
            c.px(82 + (yy * 5) % 19, yy, DKSLATE)
        typed = self._typed(t)
        line, col_ = 0, typed
        while line < len(CODE) - 1 and col_ > CODE[line][2]:
            col_ -= CODE[line][2]
            line += 1
        first = max(0, line - 5)
        for i, li in enumerate(range(first, line + 1)):
            ind, toks, n = CODE[li]
            x = 83 + ind
            left = col_ if li == line else n
            for ln, cc in toks:
                if left <= 0:
                    break
                c.rect(x, 13 + i * 2, min(ln, left), 1, cc)
                x += ln + 1
                left -= ln
            if li == line and (step // 2) % 2 == 0:
                c.rect(x, 13 + i * 2, 1, 1, WHITE)
        # right monitor: battery graph
        c.rect(106, 15, 13, 10, NAVY)
        level = ep["battery"](t)
        bars = max(0, min(4, int(round(level * 4 / 100))))
        col = GREEN if level > 50 else GOLD if level > 25 else RED
        for i in range(4):
            c.rect(108 + i * 3, 24 - i * 2, 2, 1 + i * 2, col if i < bars else DKSLATE)
        c.text(TINY, f"{int(level):d}", 119, 16, WHITE, align="right")
        # rgb keyboard glow (wave), drawn before the coder's hands
        for i, x in enumerate(range(88, 106, 2)):
            c.px(x, 36 + (x - 86) // 11, (HOT, GOLD, GREEN, CYAN, BLUE, MAUVE)[(i + step) % 6])
            c.px(x + 1, 38 + (x - 86) // 11, (HOT, GOLD, GREEN, CYAN, BLUE, MAUVE)[(i + step + 3) % 6])
        # the coder, lit by the screens at night
        b0 = b["crank"]
        pose = "look" if b0 <= t < b["crank_end"] + 0.6 else ("a", "b")[cycle(t, (0.2, 0.1, 0.3, 0.15, 0.25)) % 2]
        spr = CODER[pose]
        if ep["light"](t, step) == "night":
            spr = np.where(spr == T, T, MOON[spr]).astype(np.uint8)
        c.blit(spr, 86, 35)
        wx, wy, ww, wh = WINDOW
        c.rect(wx + 1, wy + 1, ww - 2, wh - 2, INK)
        c.px(wx + 3, wy + 4, CREAM); c.px(wx + 4, wy + 4, LTGREY); c.px(wx + 3, wy + 5, LTGREY)
        for yy in range(wy + 12, wy + wh, 12):
            c.rect(wx, yy, ww, 1, LTGREY)
        self.snow.draw(c)
        for yy in range(wy + 1, wy + wh - 1):               # frost creeping in
            k = (yy * 7) % 11
            if k < 3:
                c.px(wx + 1, yy, WHITE if k else LTGREY)
            if k in (4, 5, 9):
                c.px(wx + ww - 2, yy, LTGREY if k == 9 else WHITE)
            if k == 6:
                c.px(wx + 2, yy, LTGREY)
        c.rect(wx + 1, wy + wh - 3, ww - 2, 2, WHITE)       # snow on the sill
        c.px(wx + 2, wy + wh - 4, WHITE); c.px(wx + 4, wy + wh - 4, WHITE)
        c.px(119, 199, GREEN if t >= b["charge"] else (RED if t >= b["dying"] else DKSLATE))
        c.px(119, 31, YELLOW)
        c.px(125, 127, YELLOW)
        lvl = tween_int(t, b["night"], b["night"] + 3.0, 14, 3)
        c.rect(122, 19 - lvl, 2, lvl, RED)

    def world(self, step, t):
        ep, b = self.ep, self.ep["beats"]
        self._sim(step)
        c = self.room.copy()
        self.steam.draw(c)
        awake = b["cat_wake"] <= t
        f = cycle(t, (0.9, 0.3, 0.4)) if awake else cycle(t, (1.1, 0.8))
        c.blit(CATS[(int(awake), f if awake else f % 2)], 56 + (1 if awake else 0), 92)
        if not awake:
            zk = int((t * 10) % 18)
            if zk < 12:
                c.text(TINY, "Z", 74 + zk // 4, 90 - zk, WHITE)
        x, y, deg = self.car_pose(t)
        jx = jy = 0
        if b["crank"] <= t < b["crank_end"]:
            jx, jy = shake(step, 1, 11)
            if step % 2 == 0:
                self.fx.emit(x + jx, y + jy, int(self.fx.rng.integers(-1, 2)), -1, 4,
                             [YELLOW, GOLD, ORANGE])
        a, (ox, oy) = self.cars[angle_index(deg, len(self.cars))]
        sx, sy = int(round(x)) - ox + 1, int(round(y)) - oy + 2   # palette-swap shadow
        sub = c.a[sy:sy + a.shape[0], sx:sx + a.shape[1]]
        m = (a != T)[:sub.shape[0], :sub.shape[1]]
        sub[m] = SHADOW[sub[m]]
        c.blit(a, int(round(x)) - ox + jx, int(round(y)) - oy + jy)
        self.fx.draw(c)
        self.lights.apply(c, ep["light"](t, step))
        self._emissive(c, t, step)
        return c

    def hud(self, v, step, t):
        ep = self.ep
        hu = ep.get("headline_until", 2.6)
        if t < hu + 0.4:                       # drops in, holds, then slides out (stepped)
            y0 = tween_int(t, 0.0, 0.5, -50, 12, "out") if t < hu else tween_int(t, hu, hu + 0.4, 12, -52)
            rag_panel(v, 12, y0, W - 24, 44, 21, NAVY, INK, DKSLATE)
            for i, line in enumerate(ep["headline"]):
                col = YELLOW if i == len(ep["headline"]) - 1 else WHITE
                v.text(HEAD, line, W // 2, y0 + 5 + i * 19, col,
                       shadow_c=MAROON if i else INK, align="center")
        for (t0, t1, lines) in ep["captions"]:
            if t0 <= t < t1:
                rag_panel(v, 5, 194, W - 10, 40, 23)
                v.text(TINY, ep.get("tag", "CAR STUFF, EXPLAINED"), W // 2, 227, SLATE, align="center")
                n = int((t - t0) * 40)
                shown = 0
                for i, (txt, col) in enumerate(lines):
                    k = max(0, min(len(txt), n - shown))
                    shown += len(txt)
                    if k:
                        v.text(CAP, txt[:k], W // 2, 198 + i * 14, col, align="center")
        level = ep["battery"](t)
        by = 182
        rag_panel(v, 5, by, 30, 11, 24)
        v.rect(8, by + 2, 17, 7, GREY); v.rect(9, by + 3, 15, 5, INK); v.rect(25, by + 4, 2, 3, GREY)
        segs = max(0, min(5, int(math.ceil(level / 20))))
        col = GREEN if level > 50 else GOLD if level > 25 else RED
        if level <= 25 and (step // 2) % 2:
            col = MAROON
        for i in range(segs):
            v.rect(10 + i * 3, by + 4, 2, 3, col)
        if t >= ep["beats"]["charge"] and (step // 3) % 2 == 0:
            v.text(TINY, "+", 29, by + 3, GREEN)

    def frame(self, step, t):
        w = self.world(step, t)
        b = self.ep["beats"]
        sh = shake(step, 1, 3) if b["crank"] <= t < b["crank_end"] and step % 3 == 0 else (0, 0)
        v = Camera(0, self.ep["camera"](t)).view(w, W, H, sh)
        self.hud(v, step, t)
        return v

    def render(self, out, master=None, native_dir=None):
        return render(self.frame, self.clock, PAL, out, SCALE, master, native_dir)

    def preview(self, path, times=(0.3, 2.0, 4.0, 5.6, 8.0, 10.6, 12.6), zoom=2):
        from PIL import Image
        steps = [self.clock.step_of[min(self.clock.n - 1, int(tt * 30))] for tt in times]
        ims = []
        for s in range(max(steps) + 1):
            f = self.frame(s, self.clock.t(s))
            if s in steps:
                ims.append(Image.fromarray(PAL.to_rgb(f.a)))
        sheet = Image.new("RGB", (W * len(ims), H))
        for i, im in enumerate(ims):
            sheet.paste(im, (i * W, 0))
        sheet = sheet.resize((sheet.width * zoom, sheet.height * zoom), Image.NEAREST)
        sheet.save(path)
        return path
