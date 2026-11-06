"""Gamer-room wallpaper set (135x240 native, x8), an original pixel scene that
follows the composition and mood of the user's reference loop: tall top-down
room, console shelf, three glowing monitors, a cheering player, a dog on a
purple rug, plushies on a beanbag, bed, window light beam with dust, posters
and boxes. Every object is drawn here in code. No characters, logos or
artwork from the reference are reproduced.
"""
import math

import numpy as np

from .core import (T, Canvas, StepClock, blob_mask, cable, cycle, outline, pattern,
                   render, rotate_nn, shade, sprite, texture, wobble_mask)
from .cozyroom import (PAL, PGLOW, WARM, _grow, _lut,
                       AMBER, BLUE, BROWN, CREAM, CYAN, DKBROWN, DKGREEN, DKSLATE, FOREST,
                       GOLD, GREEN, GREY, HOT, INK, LTGREY, MAROON, MAUVE, NAVY, ORANGE, PLUM,
                       RED, RUST, SALMON, SKIN, SKIN2, SKY, SLATE, TAN, TEAL, WHITE, WOOD,
                       YELLOW)

W, H, SCALE = 135, 240, 8

# ramps: [deep (cool), shadow, base, highlight (warm)]
GREYR = [NAVY, DKSLATE, SLATE, GREY]
LIGHTR = [DKSLATE, SLATE, GREY, LTGREY]
CARPET = [INK, INK, DKBROWN, PLUM]
RUG = [INK, DKBROWN, PLUM, MAUVE]
INDIGO = [INK, NAVY, DKSLATE, BLUE]
DOG = [DKBROWN, BROWN, WOOD, SKIN2]
BEAN = [INK, TEAL, FOREST, DKGREEN]
PINKR = [PLUM, MAUVE, SALMON, SKIN]
CRATE = [INK, DKBROWN, BROWN, WOOD]
GREEN_CRATE = [INK, INK, TEAL, FOREST]
SHELF = [INK, INK, TEAL, FOREST]

# moonlit beam: lifts and desaturates whatever it crosses
BEAM = _lut({INK: NAVY, NAVY: DKSLATE, DKBROWN: DKSLATE, PLUM: SLATE, MAUVE: GREY, TEAL: DKSLATE,
             FOREST: SLATE, DKSLATE: SLATE, SLATE: GREY, GREY: LTGREY, BROWN: SLATE,
             WOOD: GREY, SKIN2: LTGREY, BLUE: SLATE, MAROON: PLUM, DKGREEN: SLATE})


BEAM_SOFT = _lut({INK: NAVY, DKBROWN: NAVY, TEAL: NAVY, NAVY: DKSLATE, PLUM: DKSLATE, MAUVE: SLATE,
                  BROWN: DKSLATE, WOOD: SLATE, FOREST: DKSLATE, DKGREEN: DKSLATE, BLUE: DKSLATE,
                  MAROON: PLUM, SLATE: GREY})


def _prop(mask, ramp, kind="dots", line=INK):
    a = shade(mask, ramp, line=line)
    if kind:
        pattern(a, ramp, kind, a == ramp[2])
    return a


# ------------------------------------------------------------- characters ---
def gamer(pose):
    """Player seen from behind in a chair: messy auburn hair, maroon hoodie.
    pose: 'down' (hands on keys), 'up', 'up2' (cheering)."""
    c = Canvas(28, 24, T)
    hands = {"down": ((8, 2), (18, 2)), "up": ((1, 0), (25, 0)), "up2": ((2, 1), (24, 0))}[pose]
    for (sx, (hx, hy)) in ((8, hands[0]), (20, hands[1])):
        c.line(sx, 13, hx + 1, hy + 2, SKIN2)
        c.line(sx + (1 if sx < 14 else -1), 13, hx + (2 if sx < 14 else 0), hy + 2, WOOD)
        c.rect(hx, hy, 3, 3, SKIN2)
        if pose != "down":
            c.px(hx + (0 if sx < 14 else 2), hy - 1, SKIN2)           # spread fingers
            c.px(hx + 1, hy - 1, SKIN2)
    body = shade(blob_mask(18, 11, np.random.default_rng(2), 1), [DKBROWN, MAROON, RED, SALMON])
    c.blit(body, 5, 11)
    c.ellipse(9, 4, 10, 10, fill=RUST)
    c.ellipse(10, 4, 7, 5, fill=ORANGE)                                 # hair shine
    for (x, y) in ((11, 3), (14, 2), (16, 4), (9, 8), (18, 9)):
        c.px(x, y, RUST)
    c.px(9, 9, SKIN2); c.px(19, 9, SKIN2)                              # ears
    c.line(10, 12, 18, 12, DKBROWN)                                     # headphone band
    return outline(c.a.copy(), INK)


def dog(tail, breath):
    """Tan dog lying on its side, head up at top-right."""
    c = Canvas(30, 24, T)
    r = np.random.default_rng(5)
    bm = blob_mask(19, 11 + breath, r, 1)
    c.blit(_prop(bm, DOG, None, line=None), 4, 8 - breath)
    c.ellipse(12, 12, 7, 4, fill=CREAM)                                 # chest
    for (x0, y0, x1, y1) in ((16, 17, 12, 22), (18, 17, 16, 23), (7, 16, 3, 21), (9, 17, 7, 22)):
        c.line(x0, y0, x1, y1, WOOD)
        c.px(x1, y1, CREAM)
    c.ellipse(17, 2, 10, 9, fill=SKIN2)                                 # head
    c.ellipse(24, 5, 5, 4, fill=TAN)                                    # snout
    c.px(28, 6, INK); c.px(22, 4, INK)                                  # nose, eye
    c.poly([(17, 3), (19, 1), (21, 4), (19, 8)], fill=BROWN)            # floppy ear
    tx = [(4, 4), (2, 7)][tail]
    c.line(5, 11, tx[0], tx[1], WOOD); c.px(tx[0], tx[1] - 1, CREAM)    # tail
    return outline(c.a.copy(), INK)


def bear():
    """Round grey bear plush (original), sitting."""
    c = Canvas(22, 22, T)
    c.blit(shade(blob_mask(18, 16, np.random.default_rng(8), 1), GREYR), 2, 5)
    c.ellipse(2, 1, 6, 6, fill=SLATE); c.ellipse(14, 1, 6, 6, fill=SLATE)
    c.px(4, 3, GREY); c.px(16, 3, GREY)
    c.ellipse(6, 12, 10, 8, fill=GREY)                                  # belly
    c.ellipse(8, 7, 6, 4, fill=LTGREY)                                  # muzzle
    c.px(7, 6, INK); c.px(14, 6, INK); c.px(10, 8, INK); c.px(11, 8, INK)
    c.line(9, 10, 12, 10, DKSLATE)
    return outline(c.a.copy(), INK)


def pink_plush():
    """Curled jellybean plush with a sleepy face."""
    m = blob_mask(18, 14, np.random.default_rng(11), 1)
    m[3:9, 0:7] &= False
    c = Canvas(20, 16, T)
    c.blit(_prop(m, PINKR, None, line=None), 1, 1)
    c.px(11, 9, INK); c.px(14, 9, INK); c.line(12, 11, 13, 11, PLUM)
    c.px(9, 10, SALMON); c.px(16, 10, SALMON)
    return outline(c.a.copy(), INK)


# --------------------------------------------------------------------- set ---
def _seams(c, x0, y0, x1, y1, col, step=9, gap=16, vertical=True, phase=0):
    """Structural lines (planks, panels, quilt seams) every `step` px with a
    1 px gap every `gap` px. They break flat areas and long edges while
    reading as calm construction detail rather than noise."""
    if vertical:
        for k, x in enumerate(range(x0 + step - 1, x1, step)):
            for y in range(y0, y1):
                if (y + k * 7 + phase) % gap:
                    c.px(x, y, col)
    else:
        for k, y in enumerate(range(y0 + step - 1, y1, step)):
            for x in range(x0, x1):
                if (x + k * 7 + phase) % gap:
                    c.px(x, y, col)


def _solid(mask, ramp):
    """Shaded prop with a selective outline in its own darkest tone."""
    return shade(mask, ramp, line=ramp[0])


def build(seed=7):
    r = np.random.default_rng(seed)
    c = Canvas(W, H, INK)
    # --- back wall: dark teal panels, shelf, four plain consoles
    c.rect(4, 4, W - 8, 30, TEAL)
    _seams(c, 4, 4, W - 4, 22, INK, step=10)
    c.blit(shade(wobble_mask(W - 6, 3, r, 1, (8, 15), (1, 1), "b"), GREYR), 3, 21)
    for (x, y, w, h, ramp) in ((22, 12, 18, 10, LIGHTR), (45, 11, 18, 11, LIGHTR),
                               (70, 11, 16, 11, GREYR), (94, 12, 18, 10, GREYR)):
        c.blit(_solid(wobble_mask(w, h, r, 1, (4, 8), (1, 2)), ramp), x, y)
        c.rect(x + 3, y + h - 3, w - 6, 1, ramp[1])
    c.px(27, 16, RED); c.px(30, 16, BLUE)
    c.rect(49, 15, 10, 1, SLATE); c.rect(49, 17, 10, 1, SLATE)
    c.rect(74, 14, 8, 2, INK)
    c.ellipse(99, 13, 7, 7, line=FOREST)
    # vent band: short slats either side of a backlit strip
    c.rect(4, 25, W - 8, 9, NAVY)
    for x0 in (8, 94):
        for y in (27, 29, 31):
            for xs in range(x0, x0 + 30, 8):
                c.rect(xs, y, 6, 1, INK)
    c.rect(40, 26, 52, 7, BLUE)
    _seams(c, 40, 26, 92, 33, NAVY, step=9, gap=5)
    # --- desk (plum, plank seams), drawers, monitors, a few props
    c.blit(_solid(wobble_mask(104, 26, r, 1, (8, 15), (2, 3)), [INK, DKBROWN, PLUM, MAUVE]), 15, 34)
    _seams(c, 17, 37, 117, 58, DKBROWN, step=8, vertical=False)
    c.blit(_solid(wobble_mask(20, 11, r, 1, (5, 9), (1, 1)), [DKBROWN, DKBROWN, PLUM, MAUVE]), 22, 47)
    c.rect(30, 52, 4, 1, SALMON)
    c.blit(rotate_nn(shade(wobble_mask(24, 14, r, 1, (4, 7), (1, 1)), [INK, INK, INK, NAVY]), -6), 20, 35)
    c.blit(shade(wobble_mask(32, 11, r, 1, (4, 7), (1, 1)), [INK, INK, INK, NAVY]), 45, 35)
    c.blit(rotate_nn(shade(wobble_mask(14, 12, r, 1, (4, 7), (1, 1)), [INK, INK, INK, NAVY]), 28), 79, 39)
    c.blit(shade(wobble_mask(20, 4, r, 1, (4, 7), (1, 1)), [INK, NAVY, DKSLATE, SLATE], line=INK), 52, 49)
    c.blit(sprite(".ooo.\noWWWo\noWWWo\n.ooo.", {"o": INK, "W": LTGREY}), 99, 47)        # mug
    c.blit(_solid(wobble_mask(7, 10, r, 1, (2, 4), (1, 1)), LIGHTR), 108, 44)              # handheld
    c.rect(110, 46, 3, 3, DKSLATE)
    # chair
    c.blit(_solid(blob_mask(20, 14, r, 1), [INK, NAVY, DKSLATE, SLATE]), 50, 60)
    # --- floor: dark boards (vertical planks) across the room
    c.rect(4, 58, W - 8, 168, DKBROWN)
    _seams(c, 4, 58, W - 4, 226, INK, step=9)
    # right floor half catches more light (the beam does the rest)
    # --- left wall with window (blinds), right wall with three posters
    c.blit(_solid(wobble_mask(14, 194, r, 1, (8, 15), (0, 0), "r"), [INK, INK, NAVY, DKSLATE]), -4, 34)
    c.blit(shade(wobble_mask(17, 62, r, 1, (8, 14), (1, 2)), GREYR, line=NAVY), 2, 86)
    c.rect(4, 89, 13, 56, INK)
    c.blit(_solid(wobble_mask(16, 194, r, 1, (8, 15), (0, 0), "l"), [INK, INK, NAVY, DKSLATE]), 123, 34)
    for (x, y, w, h, ramp, ang) in ((114, 62, 12, 22, [BROWN, WOOD, TAN, CREAM], 5),
                                    (115, 96, 11, 20, [DKBROWN, MAROON, RED, SALMON], -4),
                                    (114, 128, 12, 18, [NAVY, DKSLATE, SLATE, GREY], 3)):
        pc = _solid(wobble_mask(w, h, r, 1, (4, 8), (1, 1)), ramp)
        pc[h // 2:h // 2 + 2, 2:w - 2] = np.where(pc[h // 2:h // 2 + 2, 2:w - 2] != T, ramp[1], T)
        pc[3, 2:w - 3] = np.where(pc[3, 2:w - 3] != T, ramp[3], T)
        c.blit(rotate_nn(pc, ang), x, y)
    # --- beanbag (green), rug (plum with banded stripes), bed (quilted indigo)
    c.blit(_solid(blob_mask(30, 22, r, 2), BEAN), 78, 62)
    c.blit(bear(), 82, 52)
    rug = _solid(wobble_mask(36, 84, r, 1, (8, 15), (2, 3)), RUG)
    for y in range(6, 80, 10):
        rug[y, 3:33] = np.where(rug[y, 3:33] != T, DKBROWN, T)
    for y in range(2, 82):                                  # tasselled border, broken every 10 px
        if y % 10 != 1 and rug[y, 3] != T:
            rug[y, 3] = MAUVE
    rug[2:82, 32] = np.where(rug[2:82, 32] != T, DKBROWN, T)
    c.blit(rotate_nn(rug, -3), 34, 90)
    c.blit(_solid(wobble_mask(42, 52, r, 1, (8, 15), (2, 3)), [INK, DKBROWN, BROWN, WOOD]), 76, 82)
    bl = shade(wobble_mask(40, 44, r, 1, (8, 14), (2, 3), "tlbr"), INDIGO, line=INK)
    for y in range(9, 44, 10):
        bl[y, 2:38] = np.where(bl[y, 2:38] == INDIGO[2], NAVY, bl[y, 2:38])
    for x in range(9, 40, 10):
        bl[2:42, x] = np.where(bl[2:42, x] == INDIGO[2], NAVY, bl[2:42, x])
    c.blit(bl, 76, 92)
    c.blit(_solid(blob_mask(28, 10, r, 1), LIGHTR), 82, 84)
    c.blit(rotate_nn(_solid(wobble_mask(14, 6, r, 1, (3, 5), (1, 1)), [INK, NAVY, DKSLATE, SLATE]), -8), 86, 104)
    c.blit(pink_plush(), 62, 82)
    # --- bottom: game box, pizza box, two crates, front ledge
    gb = _solid(wobble_mask(22, 26, r, 1, (5, 9), (1, 2)), [INK, INK, DKBROWN, MAROON])
    gb[11:13, 2:20] = np.where(gb[11:13, 2:20] != T, CREAM, T)
    c.blit(rotate_nn(gb, -4), 26, 192)
    c.blit(rotate_nn(sprite("..c..\n.ccc.\nccccc", {"c": CREAM}), -4), 33, 198)
    pz = _solid(wobble_mask(40, 24, r, 1, (8, 14), (2, 3)), GREYR)
    pz[8, 2:38] = np.where(pz[8, 2:38] != T, DKSLATE, T)
    pz[9:22, 19] = np.where(pz[9:22, 19] != T, DKSLATE, T)
    c.blit(rotate_nn(pz, -6), 74, 180)
    c.ellipse(83, 192, 9, 7, line=MAROON)
    c.blit(_solid(wobble_mask(24, 16, r, 1, (6, 11), (1, 2)), [INK, INK, DKBROWN, MAROON]), 58, 212)
    _seams(c, 60, 214, 80, 226, DKBROWN, step=4, vertical=False, gap=9)
    c.blit(_solid(wobble_mask(26, 20, r, 1, (6, 11), (1, 2)), [INK, TEAL, FOREST, DKGREEN]), 100, 208)
    _seams(c, 102, 210, 124, 226, TEAL, step=6, gap=9)
    c.blit(shade(wobble_mask(W + 6, 14, r, 1, (8, 15), (0, 0), "t"), [INK, INK, TEAL, FOREST]), -3, 228)
    # two small things only, by the bed (lived-in, not cluttered)
    c.blit(rotate_nn(sprite("KKKKK\nKrKbK\nKKKKK", {"K": NAVY, "r": RED, "b": BLUE}), 25), 92, 142)
    c.blit(rotate_nn(sprite("sss\nsSs\n.ss", {"s": SLATE, "S": DKSLATE}), -40), 70, 150)
    return c


# ------------------------------------------------------------------- scene ---
GAMERS = {p: gamer(p) for p in ("down", "up", "up2")}
DOGS = {(t, b): dog(t, b) for t in (0, 1) for b in (0, 1)}
BEAM_POLY = [(0, 66), (18, 66), (98, 192), (68, 206), (0, 124)]


class GameRoom:
    """10 s seamless loop. Every cycle length divides 10 s."""

    def __init__(self, duration=10.0, holds=(3, 3, 2, 4, 3, 3, 2, 4, 3, 3)):
        self.room = build()
        self.clock = StepClock(duration, 30, holds)
        self.dur = duration
        beam = self._mask(BEAM_POLY)
        desk = self._mask([(14, 32), (120, 32), (118, 58), (16, 58)])
        lamp = self._circle(80, 29, 5)
        check = (np.add.outer(np.arange(H), np.arange(W)) % 2) == 0
        sparse = (np.arange(H)[:, None] % 2 == 0) & (np.arange(W)[None, :] % 2 == 0)
        # translucent light = dither: 50% inside, 25% in a 4 px falloff ring
        # light in two clean cel bands: a soft outer band, then the core
        streak = ~_grow(~beam, 7)                      # brighter streak inside the beam
        self.pools = [(beam, BEAM_SOFT), (streak, BEAM), (lamp, WARM)]
        self.rings = []
        rng = np.random.default_rng(3)
        self.motes = [(int(rng.integers(20, 90)), int(rng.integers(70, 190)), int(rng.integers(1, 3)))
                      for _ in range(12)]
        self.city = [(6 + int(rng.integers(0, 13)), 92 + int(rng.integers(0, 54))) for _ in range(14)]

    @staticmethod
    def _mask(pts):
        c = Canvas(W, H, 0)
        c.poly(pts, fill=1)
        return c.a.astype(bool)

    @staticmethod
    def _circle(cx, cy, rr):
        yy, xx = np.mgrid[0:H, 0:W]
        return (xx - cx) ** 2 + (yy - cy) ** 2 <= rr * rr

    def frame(self, step, t):
        c = self.room.copy()
        # characters (stepped poses, loop-safe cycles)
        pose = ("down", "up", "up2", "up", "up2")[cycle(t, (3.2, 0.6, 0.3, 0.6, 0.3))]
        c.blit(GAMERS[pose], 47, 42)
        c.blit(DOGS[(cycle(t, (0.6, 0.4)), cycle(t, (1.2, 0.8)))], 38, 82)
        # lighting: hard palette-swap pools with dithered falloff
        base = c.a.copy()
        a = base
        for m, lut in self.rings + self.pools:
            a = np.where(m, lut[base], a)
        c.a = a
        self._emissive(c, step, t)
        return c

    def _emissive(self, c, step, t):
        # left monitor: hills with clouds drifting (period 10 s)
        scr = Canvas(20, 9, SKY)
        scr.rect(0, 5, 20, 4, DKGREEN)
        scr.poly([(0, 6), (5, 3), (10, 6), (14, 4), (19, 6), (19, 8), (0, 8)], fill=GREEN)
        off = int(t * 2) % 20
        for cx in (off, (off + 11) % 20):
            scr.rect(cx, 1, 4, 1, WHITE); scr.rect(cx + 1, 0, 2, 1, WHITE)
        c.blit(rotate_nn(scr.a, -6), 22, 37)
        # centre monitor: bright game screen, 4 scenes x 2.5 s
        k = cycle(t, (2.5, 2.5, 2.5, 2.5))
        c.rect(47, 37, 28, 7, LTGREY)
        for i in range(4):
            c.rect(49 + i * 6 + k, 39 + (i + k) % 2, 4, 2, (WHITE, GREY, SLATE, WHITE)[i])
        c.rect(48 + 6 * k, 42, 10, 1, DKSLATE)
        for x in range(49, 75, 8):                           # UI ticks break the screen edges
            c.px(x, 43, GREY); c.px(x + 3, 37, WHITE)
        # right monitor: purple UI
        side = Canvas(10, 8, PLUM)
        side.rect(1, 1, 8, 2, MAUVE); side.rect(1, 4 + (step // 6) % 3, 5, 1, SALMON)
        c.blit(rotate_nn(side.a, 28), 81, 41)
        # magenta LED strip along the desk back (segments, steady)
        for x in range(17, 116):
            if x % 9:
                c.px(x, 34, MAUVE)
        # handheld screen on the bed + desk lamp + console LEDs
        c.rect(88, 102, 5, 2, SKY if (step // 8) % 2 else CYAN)
        c.ellipse(78, 27, 5, 5, fill=AMBER); c.px(79, 28, GOLD)
        c.px(34, 21, GREEN); c.px(57, 21, GREEN); c.px(103, 17, GREEN)
        # window: blinds + city lights (one blinks every 2.5 s)
        for (x, y) in self.city:
            c.px(x, y, GOLD if (x * 3 + y) % 5 else CREAM)
        bl = cycle(t, (2.5, 2.5, 2.5, 2.5))
        x, y = self.city[bl * 3]
        c.px(x, y, NAVY)
        for y in range(90, 148, 3):
            c.rect(5, y, 15, 1, DKSLATE if y % 9 else SLATE)
        # dust motes drifting down the beam; 60 px per 10 s so the loop is seamless
        for i, (x0, y0, spd) in enumerate(self.motes):
            k = (int(t * 6) * spd) % 60
            x, y = x0 + k // 4, y0 + k
            if self.pools[0][0][min(H - 1, y), min(W - 1, x)]:
                c.px(x, y, CREAM if i % 3 else TAN)

    def render(self, out, master=None, native_dir=None):
        return render(self.frame, self.clock, PAL, out, SCALE, master, native_dir)
