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
    c.blit(_prop(blob_mask(18, 16, np.random.default_rng(8), 1), GREYR, "dots", line=None), 2, 5)
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
def build(seed=7):
    r = np.random.default_rng(seed)
    c = Canvas(W, H, INK)
    pattern(c.a, [INK, NAVY], "dots", delta=1)
    # back wall + console shelf
    c.blit(_prop(wobble_mask(124, 18, r, 1, (8, 15), (2, 3)), SHELF, "dots", line=None), 5, 8)
    c.blit(shade(wobble_mask(124, 3, r, 1, (8, 15), (1, 1), "b"), GREYR), 5, 23)
    consoles = [(22, 13, 18, 10, LIGHTR), (44, 12, 18, 11, LIGHTR), (69, 11, 17, 12, GREYR),
                (95, 12, 17, 11, [INK, NAVY, DKSLATE, SLATE])]
    for i, (x, y, w, h, ramp) in enumerate(consoles):
        c.blit(_prop(wobble_mask(w, h, r, 1, (3, 7), (1, 2)), ramp, "weave"), x, y)
        c.rect(x + 3, y + h - 3, w - 6, 1, ramp[0])
    c.px(27, 17, RED); c.px(30, 17, BLUE); c.px(33, 17, GREEN)        # face buttons
    for yy in (15, 17, 19):
        c.rect(48, yy, 10, 1, SLATE)                                  # vents
    c.rect(73, 13, 9, 2, INK); c.px(74, 19, RED); c.px(77, 19, RED)   # cart slot
    c.ellipse(100, 14, 7, 7, line=DKGREEN)                             # power ring
    cable(c, [(40, 20), (42, 24), (45, 21)], INK)
    cable(c, [(86, 20), (90, 25), (95, 21)], INK)
    cable(c, [(12, 19), (16, 24), (22, 20)], INK)
    # vent band with backlit window strip
    for x0, x1 in ((10, 26), (90, 125)):
        g = np.where(((np.mgrid[0:8, 0:x1 - x0][0] + np.mgrid[0:8, 0:x1 - x0][1]) % 2) == 0, INK, NAVY)
        c.a[26:34, x0:x1] = g
    c.rect(26, 26, 64, 8, NAVY)
    pattern(c.a[26:34, 26:90], [NAVY, BLUE], "weave", delta=1)
    # desk
    desk = wobble_mask(104, 38, r, 1, (8, 15), (2, 3))
    c.blit(_prop(desk, [INK, DKBROWN, PLUM, SLATE], "grain"), 15, 34)    # purple-lit desk
    for y in (60, 66):
        c.line(25, y, 42, y, NAVY); c.rect(32, y + 2, 3, 1, SLATE)   # drawers
    # monitors (bezels; screens are emissive)
    c.blit(rotate_nn(shade(wobble_mask(24, 14, r, 1, (3, 6), (1, 1)), [INK, INK, INK, NAVY]), -6), 20, 35)
    c.blit(shade(wobble_mask(32, 11, r, 1, (3, 6), (1, 1)), [INK, INK, INK, NAVY]), 45, 35)
    c.blit(rotate_nn(shade(wobble_mask(14, 12, r, 1, (3, 6), (1, 1)), [INK, INK, INK, NAVY]), 28), 79, 39)
    # desk props: keyboard, mouse, mug, figure, handheld, snack
    kb = shade(wobble_mask(20, 4, r, 1, (3, 6), (1, 1)), [INK, NAVY, DKSLATE, SLATE], line=INK)
    c.blit(kb, 52, 49)
    c.blit(sprite(".ooo.\noWWWo\noWCWo\n.ooo.", {"o": INK, "W": WHITE, "C": MAROON}), 38, 50)
    c.blit(sprite("oo\noW\noo", {"o": INK, "W": LTGREY}), 75, 51)
    c.blit(sprite(".o.\noAo\noGo\noGo\nooo", {"o": INK, "A": AMBER, "G": PLUM}), 96, 41)
    c.blit(_prop(wobble_mask(8, 11, r, 1, (2, 4), (1, 1)), LIGHTR, None), 107, 46)
    c.rect(109, 48, 4, 3, DKSLATE); c.px(109, 53, INK); c.px(111, 54, INK)
    c.blit(rotate_nn(sprite("RRRR\nRYYR\nRRRR", {"R": RED, "Y": GOLD}), 20), 26, 50)
    cable(c, [(76, 52), (82, 58), (88, 52)], INK)
    # chair
    c.blit(_prop(blob_mask(20, 14, r, 1), [INK, NAVY, DKSLATE, SLATE], "weave"), 50, 62)
    c.blit(_prop(blob_mask(14, 6, r, 1), [INK, NAVY, DKSLATE, SLATE], None), 53, 74)
    # main floor (carpet) + right floor
    fm = wobble_mask(84, 150, r, 1, (8, 15), (2, 3))
    c.blit(_prop(fm, CARPET, "weave", line=None), 28, 72)
    pattern(c.a[72:222, 28:112], CARPET, "dots", (c.a[72:222, 28:112] == PLUM), delta=-1)
    # lower floor reads olive: checker-mix dark brown with teal (no olive in the palette)
    yy, xx = np.mgrid[0:H, 0:W]
    olive = (yy >= 136) & (yy < 222) & (c.a == DKBROWN) & ((xx + yy) % 2 == 0)
    olive &= np.pad(fm, ((72, H - 72 - fm.shape[0]), (28, W - 28 - fm.shape[1])))
    c.a[olive] = TEAL
    # bean bag + plushies
    c.blit(_prop(blob_mask(30, 22, r, 2), BEAN, "weave"), 78, 62)
    c.blit(bear(), 81, 52)
    # purple rug
    rug = _prop(wobble_mask(36, 84, r, 1, (8, 15), (2, 3)), RUG, "weave")
    for y in range(2, 82, 2):
        rug[y, 0] = SALMON if rug[y, 0] != T else T
    c.blit(rotate_nn(rug, -3), 36, 88)
    # bed
    c.blit(_prop(wobble_mask(40, 52, r, 1, (8, 15), (2, 3)), [INK, DKBROWN, BROWN, WOOD], "grain"), 76, 82)
    bl = shade(wobble_mask(38, 44, r, 2, (6, 12), (2, 4), "tlbr"), INDIGO, line=INK)
    pattern(bl, INDIGO, "quilt", bl == INDIGO[2])
    c.blit(bl, 74, 92)
    c.blit(_prop(blob_mask(26, 10, r, 1), LIGHTR, "weave", line=DKSLATE), 84, 84)
    c.blit(rotate_nn(_prop(wobble_mask(14, 6, r, 1, (3, 5), (1, 1)), [INK, NAVY, DKSLATE, SLATE], None), -8), 84, 101)
    for (x0, y0, x1, y1) in ((78, 112, 88, 124), (96, 120, 108, 128)):
        c.line(x0, y0, x1, y1, NAVY); c.line(x0 + 1, y0, x1 + 1, y1, BLUE)
    c.blit(pink_plush(), 64, 80)
    # right wall + posters
    c.blit(_prop(wobble_mask(24, 180, r, 1, (8, 15), (0, 0), "l"), [INK, NAVY, DKSLATE, SLATE], "dots", line=None), 116, 40)
    posters = [(112, 54, 12, 24, [DKBROWN, BROWN, WOOD, TAN], 6), (113, 84, 11, 26, GREYR, -4),
               (112, 114, 12, 20, [INK, DKBROWN, MAROON, RED], 3), (114, 142, 10, 14, GREYR, -6),
               (113, 160, 11, 18, [INK, PLUM, MAUVE, SALMON], 5)]
    for (x, y, w, h, ramp, ang) in posters:
        pc = _prop(wobble_mask(w, h, r, 1, (3, 7), (1, 1)), ramp, "dots", line=DKSLATE)
        pc[3:5, 2:w - 2] = np.where(pc[3:5, 2:w - 2] != T, ramp[0], T)         # title bar
        pc[h // 2:h // 2 + 3, 3:w - 3] = np.where(pc[h // 2:h // 2 + 3, 3:w - 3] != T, ramp[1], T)
        c.blit(rotate_nn(pc, ang), x, y)
    # left wall + window with blinds + city lights (lights are emissive)
    c.blit(_prop(wobble_mask(30, 200, r, 1, (8, 15), (0, 0), "r"), [INK, INK, NAVY, DKSLATE], "dots", line=None), -6, 34)
    c.blit(shade(wobble_mask(20, 66, r, 1, (6, 12), (1, 2)), GREYR, line=INK), 3, 86)
    c.rect(5, 89, 15, 59, INK)
    # beanbag chair + radiator bottom-left
    c.blit(_prop(blob_mask(18, 20, r, 2), [INK, PLUM, MAUVE, SALMON], "weave"), 9, 174)
    c.blit(_prop(wobble_mask(4, 22, r, 1, (3, 6), (1, 1)), GREYR, None), 9, 186)
    # floor clutter (clustered by the bed and the rug)
    for (spr, x, y, a) in (
            (sprite("KKKKK\nKrKbK\nKKKKK", {"K": NAVY, "r": RED, "b": BLUE}), 92, 140, 25),
            (sprite("WW\nWL", {"W": LTGREY, "L": GREY}), 60, 176, 0),
            (sprite("ooo\noRo\nooo", {"o": INK, "R": MAROON}), 64, 132, 30),
            (sprite("sss\nsSs\n.ss", {"s": SLATE, "S": DKSLATE}), 82, 150, -40),
            (sprite("RG\nBY", {"R": RED, "G": GREEN, "B": BLUE, "Y": GOLD}), 36, 185, 0)):
        c.blit(rotate_nn(spr, a), x, y)
    c.blit(_prop(blob_mask(14, 8, r, 2), [INK, NAVY, BLUE, DKSLATE], None), 34, 102)   # hoodie on floor
    # bottom: game box on a mat, pizza box, crates, front edge
    c.blit(rotate_nn(_prop(wobble_mask(30, 32, r, 1, (6, 12), (2, 3)), GREYR, "dots"), -4), 22, 192)
    gb = Canvas(20, 22, MAROON)
    gb.rect(0, 0, 20, 9, RED); gb.rect(0, 11, 20, 11, DKBROWN)
    gb.poly([(4, 7), (10, 1), (16, 7), (13, 7), (10, 4), (7, 7)], fill=CREAM)           # chevron
    gb.line(3, 19, 9, 13, SALMON); gb.line(9, 13, 15, 19, SALMON)
    pattern(gb.a, [DKBROWN, MAROON, RED], "dots", delta=1)
    c.blit(rotate_nn(gb.a, -4), 28, 197)
    pz = _prop(wobble_mask(42, 26, r, 1, (8, 14), (2, 3)), GREYR, "weave")
    c.blit(rotate_nn(pz, -6), 76, 178)
    c.ellipse(90, 186, 13, 9, line=MAROON); c.line(93, 190, 99, 188, MAROON)          # stamp
    c.blit(_prop(wobble_mask(26, 16, r, 1, (6, 12), (1, 2)), [INK, DKBROWN, MAROON, RED], "weave"), 60, 214)
    for y in range(217, 228, 3):
        c.rect(63 + (y % 2), y, 18, 1, RED)
    c.blit(_prop(wobble_mask(22, 20, r, 1, (6, 12), (1, 2)), CRATE, "grain"), 87, 210)
    c.blit(_prop(wobble_mask(24, 24, r, 1, (6, 12), (1, 2)), GREEN_CRATE, "grain"), 108, 206)
    c.blit(shade(wobble_mask(W + 6, 14, r, 1, (8, 15), (0, 0), "t"), [INK, INK, TEAL, FOREST]), -3, 230)
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
        self.pools = [(beam, BEAM), (lamp, WARM)]
        self.rings = [(_grow(beam, 5) & ~beam & sparse, BEAM), (_grow(lamp, 3) & ~lamp & check, WARM)]
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
        for m, lut in self.pools + self.rings:
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
