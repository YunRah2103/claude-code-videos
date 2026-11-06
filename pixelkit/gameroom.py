"""Gamer-room wallpaper set (135x240 native, x8), an original pixel scene that
follows the composition and mood of the user's reference loop: tall top-down
room, console shelf, three glowing monitors, a cheering player, a dog on a
purple rug, plushies on a beanbag, bed, window light beam with dust, posters
and boxes. Every object is drawn here in code. No characters, logos or
artwork from the reference are reproduced.
"""
import math

import numpy as np

from .core import (T, Canvas, StepClock, blob_mask, cable, cycle, nick_edges, outline, pattern,
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
    1 px gap every `gap` px: calm construction detail that also breaks flat
    areas and long straight edges."""
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


def tex(w, h, base, seam=None, step=9, vertical=True, gap=16, rim=None):
    """Face texture: base colour, optional seams, optional dashed rim row 0."""
    c = Canvas(w, h, base)
    if seam is not None:
        _seams(c, 0, 0, w, h, seam, step, gap, vertical)
    if rim is not None:
        for x in range(w):
            c.px(x, 0, rim if x % 7 else base)
    return c


# ------------------------------------------------------------------ 3D set ---
from .persp import Persp                                    # noqa: E402

CAM = Persp(W, H, 67, 122, 150)
FX0, FY0, FX1, FY1, HW = 20, 40, 114, 206, 40               # floor rect, wall height


def _hull(pts):
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p_ in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p_) <= 0:
            lo.pop()
        lo.append(p_)
    for p_ in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p_) <= 0:
            up.pop()
        up.append(p_)
    return lo[:-1] + up[:-1]


WIN = (88, 148, 8, 32)                                       # window on the left wall: y0, y1, z0, z1
PATCH = [(21, 98), (21, 150), (64, 202), (84, 176)]          # where the window light lands


def build(seed=7):
    r = np.random.default_rng(seed)
    cam = CAM
    c = Canvas(W, H, INK)
    fw, fd = FX1 - FX0, FY1 - FY0
    # --- walls (textured faces in perspective)
    back = tex(fw, HW, TEAL, INK, step=10, gap=7, rim=NAVY)
    back.rect(0, 24, 22, 9, NAVY); back.rect(72, 24, 22, 9, NAVY)
    for y in (25, 27, 29, 31):
        for x0 in (1, 73):
            for xs in range(x0, x0 + 20, 7):
                back.rect(xs, y, 5, 1, INK)
    back.rect(22, 24, 50, 9, BLUE)
    _seams(back, 22, 24, 72, 33, NAVY, step=9, gap=5)
    back.rect(0, 36, fw, 4, NAVY)
    for x in range(0, fw, 6):
        back.px(x, 36, DKSLATE)
    cam.warp(c, back.a, "y", FY0, FX0, FX1, 0, HW)
    left = tex(fd, HW, NAVY, INK, step=12, gap=7, rim=DKSLATE)
    wy0, wy1, wz0, wz1 = WIN
    left.rect(wy0 - FY0 - 1, HW - wz1 - 1, wy1 - wy0 + 2, wz1 - wz0 + 2, GREY)
    left.rect(wy0 - FY0, HW - wz1, wy1 - wy0, wz1 - wz0, INK)
    cam.warp(c, left.a, "x", FX0, FY0, FY1, 0, HW)
    right = tex(fd, HW, DKSLATE, NAVY, step=12, gap=7, rim=SLATE)
    for (u0, u1, ramp) in ((14, 34, [BROWN, WOOD, TAN, CREAM]), (50, 72, [DKBROWN, MAROON, RED, SALMON]),
                           (90, 108, [NAVY, SLATE, GREY, LTGREY])):
        right.rect(u0, 7, u1 - u0, 22, ramp[0])
        right.rect(u0 + 1, 8, u1 - u0 - 2, 20, ramp[2])
        right.rect(u0 + 2, 10, u1 - u0 - 4, 2, ramp[3])
        right.rect(u0 + 2, 15, u1 - u0 - 4, 7, ramp[1])
        right.rect(u0 + 4, 17, 4, 3, ramp[3])
        for v in (7, 28):
            for u in range(u0 + 3, u1 - 2, 6):
                right.px(u, v, ramp[1])                      # tape notches break the frame
        for u in (u0, u1 - 1):
            for v in range(9, 28, 6):
                right.px(u, v, ramp[1])
    cam.warp(c, right.a, "x", FX1, FY0, FY1, 0, HW)
    front = tex(fw, HW, INK, NAVY, step=10, gap=7, rim=NAVY)
    cam.warp(c, front.a, "y", FY1, FX0, FX1, 0, HW)
    # --- floor: dark planks with contact shadow along the walls
    fl = tex(fw, fd, DKBROWN, INK, step=9, gap=16)
    for k, x in enumerate(range(0, fw, 9)):
        for y in range(18 + k * 13 % 40, fd, 40):
            fl.rect(x, y, 8, 1, INK)
    for x in range(fw):
        if x % 6:
            fl.px(x, 0, INK); fl.px(x, 1, INK if x % 3 else DKBROWN); fl.px(x, fd - 1, INK)
    for y in range(fd):
        if y % 6:
            fl.px(0, y, INK); fl.px(fw - 1, y, INK); fl.px(1, y, INK if y % 3 else DKBROWN)
    c.blit(fl.a, FX0, FY0)
    # --- shelf + four consoles on the back wall
    cam.box(c, 28, 40, 106, 44, 25, 27, SLATE, DKSLATE, NAVY, hi=GREY, line=NAVY)
    for i, (x0, ramp) in enumerate(((31, LIGHTR), (50, LIGHTR), (69, GREYR), (88, GREYR))):
        face = tex(14, 6, ramp[2], rim=ramp[3])
        face.rect(2, 3, 10, 1, ramp[0])
        face.px(3, 1, (RED, GREEN, RED, DKGREEN)[i]); face.px(5, 1, (BLUE, GREEN, RED, DKGREEN)[i])
        cam.box(c, x0, 40, x0 + 14, 43, 27, 33, tex(14, 3, ramp[3]).a, face.a, ramp[0], hi=ramp[3])
    # --- desk with drawers, monitors, keyboard, mug, lamp, handheld
    top = tex(86, 15, PLUM, DKBROWN, step=5, vertical=False, gap=13)
    front = tex(86, 13, DKBROWN, INK, step=11, gap=6, rim=PLUM)
    front.rect(3, 3, 22, 1, INK); front.rect(3, 8, 22, 1, INK)
    front.rect(12, 5, 4, 1, MAUVE); front.rect(12, 10, 4, 1, MAUVE)
    cam.box(c, 24, 40, 110, 55, 0, 13, top.a, front.a, INK, hi=MAUVE, line=DKBROWN, ao=INK)
    for (x0, x1, y0, z1) in ((28, 50, 41, 26), (54, 84, 41, 25), (88, 100, 42, 23)):
        cam.box(c, x0, y0, x1, y0 + 2, 13, z1, INK, INK, INK, hi=NAVY)
    kb = tex(20, 3, DKSLATE, NAVY, step=3, gap=40)
    cam.box(c, 56, 47, 76, 50, 13, 14, kb.a, NAVY, NAVY, hi=SLATE)
    cam.box(c, 36, 48, 40, 52, 13, 18, MAROON, LTGREY, GREY, hi=WHITE)
    cam.box(c, 100, 44, 104, 48, 13, 21, AMBER, WOOD, BROWN)
    cam.box(c, 104, 49, 110, 53, 13, 14, DKSLATE, SLATE, SLATE, hi=GREY)
    # --- chair (seat + backrest); the player is drawn per frame between them
    cam.box(c, 56, 58, 76, 70, 0, 8, tex(20, 12, DKSLATE, NAVY, step=5, gap=40).a, NAVY, INK, hi=SLATE,
            line=NAVY, ao=INK)
    # --- rug (flat, banded) and two small things by the bed
    rug = shade(wobble_mask(36, 84, r, 1, (8, 15), (2, 3)), RUG, line=RUG[0])
    for y in range(6, 80, 10):
        for x in range(3, 33):
            if (x + y) % 11 and rug[y, x] != T:
                rug[y, x] = DKBROWN
    for y in range(2, 82):
        if y % 10 != 1 and rug[y, 3] != T:
            rug[y, 3] = MAUVE
    c.blit(rug, 34, 94)
    c.blit(rotate_nn(sprite("KKKKK\nKrKbK\nKKKKK", {"K": NAVY, "r": RED, "b": BLUE}), 25), 72, 150)
    c.blit(rotate_nn(sprite("sss\nsSs\n.ss", {"s": SLATE, "S": DKSLATE}), -40), 64, 182)
    # --- beanbag with the bear on top
    bag = blob_mask(28, 20, r, 2)
    bx, by = cam.extrude(c, bag, 80, 58, 0, 7, TEAL, shade(bag, BEAN))
    c.blit(bear(), bx + 4, by - 9)
    # --- bed: frame, quilted mattress, pillow, handheld
    cam.box(c, 76, 84, 112, 136, 0, 6, BROWN, BROWN, DKBROWN, hi=WOOD, line=DKBROWN, ao=INK)
    quilt = tex(34, 48, DKSLATE, NAVY, step=10, gap=40)
    _seams(quilt, 0, 0, 34, 48, NAVY, step=10, vertical=False, gap=40)
    for y in range(48):
        quilt.px(0, y, BLUE if y % 6 else DKSLATE)
    cam.box(c, 77, 86, 111, 134, 6, 12, quilt.a, NAVY, NAVY, hi=BLUE, line=INK)
    cam.box(c, 82, 87, 106, 95, 12, 15, tex(24, 8, GREY, SLATE, step=6, gap=40).a, SLATE, SLATE, hi=LTGREY)
    cam.box(c, 86, 104, 98, 108, 12, 13, DKSLATE, SLATE, SLATE, hi=GREY)
    # --- front: game box, pizza box, two crates (north faces show: they are below centre)
    cover = tex(22, 20, MAROON, rim=RED)
    cover.rect(0, 9, 22, 2, CREAM)
    cover.poly([(6, 7), (11, 2), (16, 7), (13, 7), (11, 5), (9, 7)], fill=CREAM)
    cam.box(c, 26, 178, 48, 198, 0, 2, cover.a, DKBROWN, INK, line=DKBROWN, ao=INK)
    pz = tex(40, 20, GREY, SLATE, step=20, gap=40, rim=LTGREY)
    pz.ellipse(10, 6, 10, 8, line=MAROON)
    cam.box(c, 72, 176, 112, 196, 0, 3, pz.a, SLATE, DKSLATE, hi=LTGREY, line=SLATE, ao=INK)
    crate_top = tex(24, 14, MAROON, DKBROWN, step=4, vertical=False, gap=9)
    crate_side = tex(24, 12, DKBROWN, MAROON, step=3, vertical=False, gap=9, rim=RED)
    cam.box(c, 52, 192, 76, 206, 0, 12, crate_top.a, crate_side.a, INK, hi=RED, line=DKBROWN, ao=INK)
    g_top = tex(24, 16, FOREST, TEAL, step=6, gap=9)
    g_side = tex(24, 16, TEAL, INK, step=6, gap=9, rim=FOREST)
    cam.box(c, 88, 190, 112, 206, 0, 16, g_top.a, g_side.a, INK, hi=DKGREEN, line=TEAL, ao=INK)
    return c


# ------------------------------------------------------------------- scene ---
GAMERS = {p: gamer(p) for p in ("down", "up", "up2")}
DOGS = {(t, b): dog(t, b) for t in (0, 1) for b in (0, 1)}


class GameRoom:
    """10 s seamless loop in true top-down perspective. Every cycle divides 10 s."""

    def __init__(self, duration=10.0, holds=(3, 3, 2, 4, 3, 3, 2, 4, 3, 3)):
        self.room = build()
        self.clock = StepClock(duration, 30, holds)
        self.dur = duration
        cam = CAM
        wy0, wy1, wz0, wz1 = WIN
        win = [cam.P(FX0, wy0, wz1), cam.P(FX0, wy1, wz1), cam.P(FX0, wy1, wz0), cam.P(FX0, wy0, wz0)]
        self.shaft = self._mask(_hull(win + PATCH))          # light volume in the air
        self.patch = self._mask(PATCH)                         # where it lands
        self.lamp = self._circle(*cam.P(102, 46, 21), 6)
        dt = [cam.P(24, 44, 13), cam.P(110, 44, 13), cam.P(110, 55, 13), cam.P(24, 55, 13)]
        self.deskglow = self._mask(dt)
        rng = np.random.default_rng(3)
        self.motes = [(int(rng.integers(10, 80)), int(rng.integers(70, 190)), int(rng.integers(1, 3)))
                      for _ in range(12)]
        self.city = [(wy0 + 2 + int(rng.integers(0, wy1 - wy0 - 4)), wz0 + 2 + int(rng.integers(0, wz1 - wz0 - 4)))
                     for _ in range(16)]
        # backrest drawn per frame on top of the player
        self.backrest = Canvas(W, H, T)
        CAM.box(self.backrest, 56, 68, 76, 71, 8, 20, DKSLATE, NAVY, INK, hi=SLATE)

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
        pose = ("down", "up", "up2", "up", "up2")[cycle(t, (3.2, 0.6, 0.3, 0.6, 0.3))]
        c.blit(self.backrest.a, 0, 0)
        c.blit(GAMERS[pose], 52, 33)
        c.blit(DOGS[(cycle(t, (0.6, 0.4)), cycle(t, (1.2, 0.8)))], 36, 92)
        c.blit(PINK_PLUSH, 60, 88)
        # light: shaft through the air (soft), patch on the floor (bright), lamp, desk glow
        base = c.a.copy()
        a = np.where(self.shaft, BEAM_SOFT[base], base)
        a = np.where(self.patch, BEAM[base], a)
        a = np.where(self.deskglow, PGLOW[base], a)
        a = np.where(self.lamp, WARM[base], a)
        c.a = a
        self._emissive(c, step, t)
        nick_edges(c.a, PAL.lut)            # chip any ruler-straight perspective edge
        return c

    def _screen(self, c, img, x0, x1, y, z0, z1):
        CAM.warp(c, img, "y", y, x0, x1, z0, z1)

    def _emissive(self, c, step, t):
        # left monitor: hills, clouds drifting (period 10 s)
        scr = Canvas(20, 11, SKY)
        scr.rect(0, 7, 20, 4, DKGREEN)
        scr.poly([(0, 8), (5, 5), (10, 8), (14, 6), (19, 8), (19, 10), (0, 10)], fill=GREEN)
        off = int(t * 2) % 20
        for cx in (off, (off + 11) % 20):
            scr.rect(cx, 2, 4, 1, WHITE); scr.rect(cx + 1, 1, 2, 1, WHITE)
        self._screen(c, scr.a, 29, 49, 43, 14, 25)
        # centre monitor: game screen, 4 scenes x 2.5 s
        k = cycle(t, (2.5, 2.5, 2.5, 2.5))
        g = Canvas(28, 10, LTGREY)
        for i in range(4):
            g.rect(2 + i * 6 + k, 2 + (i + k) % 2, 4, 3, (WHITE, GREY, SLATE, WHITE)[i])
        g.rect(1 + 6 * k, 7, 10, 1, DKSLATE)
        for x in range(1, 28, 5):
            g.px(x, 0, WHITE); g.px(x + 2, 9, GREY)
        self._screen(c, g.a, 55, 83, 43, 14, 24)
        # right monitor: purple UI
        side = Canvas(10, 8, PLUM)
        side.rect(1, 1, 8, 2, MAUVE); side.rect(1, 4 + (step // 6) % 3, 5, 1, SALMON)
        self._screen(c, side.a, 89, 99, 44, 14, 22)
        # handheld screen on the bed, lamp bulb, console LEDs
        hx, hy = CAM.P(92, 106, 13)
        c.rect(int(hx) - 2, int(hy) - 1, 4, 2, SKY if (step // 8) % 2 else CYAN)
        lx, ly = CAM.P(102, 46, 21)
        c.px(int(lx), int(ly), GOLD)
        # window: city lights through the blinds (one blinks every 2.5 s)
        bl = cycle(t, (2.5, 2.5, 2.5, 2.5))
        for i, (y, z) in enumerate(self.city):
            if i == bl * 3:
                continue
            px, py = CAM.P(FX0, y, z)
            c.px(int(px), int(py), GOLD if (y + z) % 3 else CREAM)
        wy0, wy1, wz0, wz1 = WIN
        for z in range(wz0 + 2, wz1, 3):
            CAM.dashed(c, CAM.P(FX0, wy0, z), CAM.P(FX0, wy1, z), DKSLATE, on=9, off=1)
        # dust motes drifting down the light shaft; 60 px per 10 s keeps the loop seamless
        for i, (x0, y0, spd) in enumerate(self.motes):
            kk = (int(t * 6) * spd) % 60
            x, y = x0 + kk // 3, y0 + kk
            if 0 <= y < H and 0 <= x < W and self.shaft[y, x]:
                c.px(x, y, CREAM if i % 3 else TAN)

    def render(self, out, master=None, native_dir=None):
        return render(self.frame, self.clock, PAL, out, SCALE, master, native_dir)


PINK_PLUSH = pink_plush()
