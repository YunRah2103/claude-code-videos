"""Reusable top-down cozy-room set for car-channel explainers.

An episode supplies: headline, timed captions, a car sprite, and a few beat
times (see episodes/*/episode.py). The room, pet, props, lighting and HUD are
shared. All drawing is native-resolution palette indices (pixelkit.core).
"""
import math

import numpy as np

from .core import (T, BitmapFont, Camera, Canvas, Palette, Particles, PixelFont,
                   StepClock, angle_index, bake_rotations, cycle, outline, render,
                   shake, sprite, still, tween_int)

W, H = 180, 320          # native view (x6 = 1080x1920)
WW, WH = 180, 340        # world
PAL = Palette("endesga32")
(RUST, ORANGE, CREAM, TAN, WOOD, BROWN, DKBROWN, MAROON, RED, AMBER, GOLD, YELLOW,
 GREEN, DKGREEN, FOREST, TEAL, BLUE, SKY, CYAN, WHITE, LTGREY, GREY, SLATE, DKSLATE,
 NAVY, INK, HOT, PLUM, MAUVE, SALMON, SKIN, SKIN2) = range(32)


def _lut(pairs):
    lut = np.arange(256, dtype=np.uint8)
    for s, d in pairs.items():
        lut[s] = d
    return lut


# Lighting = palette swaps (index remaps inside the same 32 colours).
NIGHT = _lut({RUST: MAROON, ORANGE: BROWN, CREAM: GREY, TAN: SLATE, WOOD: PLUM, BROWN: DKBROWN,
              DKBROWN: INK, MAROON: DKBROWN, RED: MAROON, AMBER: BROWN, GOLD: WOOD, YELLOW: TAN,
              GREEN: DKGREEN, DKGREEN: FOREST, FOREST: TEAL, TEAL: INK, BLUE: DKSLATE, SKY: BLUE,
              CYAN: SKY, WHITE: LTGREY, LTGREY: GREY, GREY: SLATE, SLATE: DKSLATE,
              DKSLATE: NAVY, NAVY: INK, HOT: MAROON, PLUM: NAVY, MAUVE: PLUM, SALMON: MAUVE,
              SKIN: SLATE, SKIN2: PLUM})
# Moonlight: cool but brighter than NIGHT.
MOON = _lut({RUST: MAROON, ORANGE: SKIN2, CREAM: LTGREY, TAN: GREY, WOOD: SLATE, BROWN: PLUM,
             DKBROWN: NAVY, MAROON: PLUM, RED: MAUVE, AMBER: SKIN2, GOLD: SALMON, YELLOW: CREAM,
             GREEN: GREEN, DKGREEN: DKGREEN, FOREST: FOREST, TEAL: DKSLATE, BLUE: BLUE, SKY: SKY,
             PLUM: DKSLATE, MAUVE: MAUVE, SALMON: SALMON, SKIN: LTGREY, SKIN2: GREY})
# Warm lamp core: one step brighter/warmer.
WARM = _lut({DKBROWN: BROWN, BROWN: WOOD, WOOD: SKIN2, SKIN2: TAN, PLUM: MAUVE, NAVY: DKSLATE,
             DKSLATE: SLATE, INK: DKBROWN, MAUVE: SALMON, TEAL: FOREST})
SHADOW = _lut({WOOD: BROWN, BROWN: DKBROWN, DKBROWN: INK, PLUM: NAVY, MAUVE: PLUM, DKSLATE: NAVY,
               SLATE: DKSLATE, NAVY: INK, DKGREEN: FOREST, GREEN: DKGREEN, TAN: WOOD,
               CREAM: TAN, GREY: SLATE, LTGREY: GREY, FOREST: TEAL})

HEAD = PixelFont(size=20)
CAP = PixelFont(size=10)
TINY = BitmapFont()

# ----------------------------------------------------------------- sprites ---
CAR_KEY = {"o": INK, "w": INK, "R": RED, "h": SALMON, "r": MAROON, "c": SKY, "C": CYAN,
           "y": YELLOW, "W": WHITE, "H": HOT}
DEFAULT_CAR = """
...ooooooo...
..oyhRRRRyo..
.ohhRRWRRRro.
.ohRRRWRRRro.
wohRRRWRRRrow
wohcCCCCCcrow
wohcCCCCccrow
.ohcccccccro.
.ohRRRWRRRro.
.ohRRhWRRRro.
.ohRRRWRRRro.
.ohcccccccro.
wohRRRWRRRrow
wohRRRWRRRrow
.oHRRRRRRRHo.
..ooooooooo..
"""


def make_car(art=DEFAULT_CAR, key=None, n=16):
    """Bake n RotSprite angles for a top-down car facing up (0 deg)."""
    return bake_rotations(sprite(art, key or CAR_KEY), n)


def _cat(awake, frame):
    """Procedural top-down tabby cat (pre-drawn per pose, no runtime scaling)."""
    c = Canvas(22, 17, T)
    if not awake:
        c.ellipse(3, 2 - frame, 18, 13 + frame, fill=AMBER)   # curled body, breathing
        for x in (9, 12, 15, 18):
            c.line(x, 3 - frame, x - 1, 6, RUST)              # back stripes
        c.line(19, 11, 14, 14, ORANGE); c.line(19, 12, 14, 15, ORANGE)   # tail wrap
        c.line(14, 14, 9, 14, ORANGE); c.line(14, 15, 9, 15, ORANGE)
        c.px(8, 14, CREAM); c.px(8, 15, CREAM)
        c.ellipse(1, 7, 10, 8, fill=GOLD)                     # head resting on tail
        c.poly([(2, 8), (2, 5), (5, 7)], fill=AMBER)
        c.poly([(7, 7), (9, 5), (10, 8)], fill=AMBER)
        c.px(3, 7, SALMON); c.px(8, 7, SALMON)
        c.line(3, 11, 4, 11, RUST); c.line(7, 11, 8, 11, RUST)   # shut eyes
        c.px(5, 12, SALMON); c.px(6, 12, SALMON)
    else:
        c.ellipse(4, 6, 12, 9, fill=AMBER)                    # sitting body
        for x in (7, 10, 13):
            c.line(x, 9, x, 11, RUST)
        c.ellipse(5, 1, 10, 8, fill=GOLD)                     # head up
        c.poly([(5, 3), (6, 0), (8, 2)], fill=AMBER)          # ears
        c.poly([(14, 3), (13, 0), (11, 2)], fill=AMBER)
        c.px(6, 1, SALMON); c.px(13, 1, SALMON)
        if frame == 2:                                        # blink
            c.line(7, 4, 8, 4, INK); c.line(11, 4, 12, 4, INK)
        else:
            c.rect(7, 3, 2, 2, GREEN); c.px(8, 4, INK)
            c.rect(11, 3, 2, 2, GREEN); c.px(11, 4, INK)
        c.px(9, 6, SALMON); c.px(10, 6, SALMON)               # nose
        tx = [17, 18, 16][frame % 3]
        c.line(15, 12, tx, 14, ORANGE); c.px(tx, 15, ORANGE)  # tail swish
    a = c.a.copy()
    return outline(a, INK)


CATS = {(aw, f): _cat(aw, f) for aw in (0, 1) for f in (0, 1, 2)}

PLANT = sprite("""
..g.G..
.gGgGg.
gGgGgGg
.GgGgG.
..ttt..
.tTTTt.
.tTTTt.
..ttt..
""", {"g": GREEN, "G": DKGREEN, "t": RUST, "T": ORANGE})

MUG = sprite("""
.ooo..
oWWWoo
oWWWo.o
oWWWoo
.ooo..
""", {"o": INK, "W": WHITE})

SNEAKER = sprite("""
.ooo.
oWWWo
oRRWo
oRRWo
oRRWo
.ooo.
""", {"o": INK, "W": WHITE, "R": BLUE})

CONE = sprite("""
..o..
.oAo.
.oWo.
oAAAo
ooooo
""", {"o": INK, "A": AMBER, "W": WHITE})


# ------------------------------------------------------------------- room ---
def _circle_mask(cx, cy, r):
    yy, xx = np.mgrid[0:WH, 0:WW]
    return (xx - cx) ** 2 + ((yy - cy) * 1.3) ** 2 <= r * r


def _poly_mask(pts):
    c = Canvas(WW, WH, 0)
    c.poly(pts, fill=1)
    return c.a.astype(bool)


TRACK = dict(cx=90, cy=249, rx=54, ry=30)
LAMP = (160, 74)
NLIGHT = (164, 206)


def build_room(seed=3):
    """Static world layer (drawn once)."""
    r = np.random.default_rng(seed)
    c = Canvas(WW, WH, BROWN)
    # floor planks
    for k, x0 in enumerate(range(-3, WW, 9)):        # vertical boards
        c.rect(x0 + 8, 60, 1, WH, DKBROWN)
        if k % 2:
            c.rect(x0 + 1, 60, 1, WH, WOOD)
        y = 60 - int(r.integers(0, 70))
        while y < WH:
            ln = int(r.integers(50, 95))
            c.rect(x0, y, 9, 1, DKBROWN)                 # butt joint
            for _ in range(3):                          # grain
                gy = y + int(r.integers(3, max(4, ln - 6)))
                c.rect(x0 + int(r.integers(2, 7)), gy, 1, int(r.integers(2, 5)), DKBROWN)
            y += ln
    # back wall
    c.rect(0, 0, WW, 58, NAVY)
    for x in range(4, WW, 8):
        c.rect(x, 4, 1, 52, DKSLATE)
    c.rect(0, 0, WW, 3, INK)
    c.rect(0, 54, WW, 4, DKSLATE)
    c.rect(0, 54, WW, 1, SLATE)
    c.rect(0, 58, WW, 2, INK)
    # side walls (thick, seen from above) + window on the left
    for x0 in (0, WW - 12):
        c.rect(x0, 0, 12, WH, DKSLATE)
        c.rect(x0 + (11 if x0 == 0 else 0), 58, 1, WH, SLATE)
        c.rect(x0 + (0 if x0 == 0 else 11), 0, 1, WH, INK)
    c.rect(1, 112, 10, 60, LTGREY)
    c.rect(2, 113, 8, 58, INK)
    c.rect(2, 141, 8, 1, LTGREY)
    c.rect(11, 110, 3, 64, GREY)          # sill
    c.rect(11, 110, 3, 1, LTGREY)
    # front wall cut
    c.rect(0, WH - 8, WW, 8, INK)
    c.rect(0, WH - 8, WW, 1, DKSLATE)
    # shelf with consoles
    c.rect(18, 40, 66, 2, WOOD); c.rect(18, 42, 66, 1, DKBROWN)
    c.box(20, 32, 16, 8, LTGREY, INK, WHITE, GREY); c.px(33, 35, HOT)
    c.box(38, 33, 14, 7, DKSLATE, INK, SLATE, NAVY); c.rect(41, 36, 8, 1, SKY)
    c.box(54, 30, 9, 10, WHITE, INK, WHITE, LTGREY); c.rect(56, 32, 5, 3, GREEN)
    for i, col in enumerate((RED, BLUE, GOLD, GREEN, MAUVE)):
        c.rect(66 + i * 3, 28 + (i % 2), 2, 12 - (i % 2), col)
    # car poster
    c.box(108, 8, 40, 28, BLUE, INK)
    c.rect(110, 10, 36, 12, SKY)
    c.rect(110, 22, 36, 12, DKSLATE)
    c.poly([(114, 26), (120, 20), (134, 20), (140, 26), (142, 30), (112, 30)], fill=RED)
    c.rect(122, 21, 9, 4, CYAN)
    c.rect(115, 30, 5, 3, INK); c.rect(134, 30, 5, 3, INK)
    c.text(TINY, "GT", 141, 11, WHITE, align="right")
    # clock
    c.ellipse(90, 10, 12, 12, fill=CREAM, line=INK)
    c.line(96, 16, 96, 12, INK); c.line(96, 16, 99, 16, INK)
    # thermometer frame (level drawn per step)
    c.box(157, 10, 5, 30, WHITE, INK)
    c.ellipse(156, 37, 7, 7, fill=RED, line=INK)
    # desk + monitor + keyboard
    c.rect(98, 79, 66, 3, INK)                        # desk shadow edge
    c.box(96, 58, 70, 22, TAN, INK, CREAM, WOOD)
    c.box(114, 42, 36, 20, INK, INK)                  # monitor bezel
    c.rect(130, 62, 4, 3, DKSLATE)
    c.box(116, 68, 28, 6, LTGREY, INK, WHITE, GREY)
    for x in range(118, 142, 3):
        c.px(x, 70, GREY); c.px(x + 1, 72, GREY)
    c.box(147, 69, 4, 5, WHITE, INK)
    c.blit(MUG, 100, 66)
    c.box(104, 62, 7, 4, YELLOW, INK)                 # sticky note
    # desk lamp
    c.ellipse(155, 70, 9, 6, fill=SLATE, line=INK)
    c.line(159, 70, 157, 62, INK)
    c.poly([(151, 62), (163, 60), (161, 56), (153, 57)], fill=GOLD, line=INK)
    # chair
    c.ellipse(120, 84, 22, 18, fill=INK)
    c.ellipse(121, 84, 20, 16, fill=PLUM)
    c.ellipse(124, 86, 14, 10, fill=MAUVE)
    c.rect(122, 102, 18, 4, INK); c.rect(123, 102, 16, 3, PLUM)
    # dresser + plant + backpack
    c.box(16, 52, 30, 26, BROWN, INK, WOOD, DKBROWN)
    for y in (60, 68):
        c.rect(18, y, 26, 1, DKBROWN); c.rect(29, y + 3, 4, 1, GOLD)
    c.blit(PLANT, 34, 44)
    c.box(52, 60, 14, 16, FOREST, INK, DKGREEN, TEAL); c.rect(54, 66, 10, 5, DKGREEN)
    c.rect(56, 58, 6, 2, INK)
    # trash can
    c.ellipse(70, 64, 10, 10, fill=GREY, line=INK); c.ellipse(72, 66, 6, 6, fill=SLATE)
    c.px(74, 67, WHITE)
    # bed
    c.box(122, 112, 46, 86, BROWN, INK, WOOD, DKBROWN)
    c.box(124, 114, 42, 82, MAUVE, INK)
    for y in range(132, 194, 6):
        c.rect(125, y, 40, 2, PLUM)
    c.box(126, 116, 38, 14, WHITE, INK, WHITE, LTGREY)
    c.rect(144, 117, 1, 12, LTGREY)
    c.box(132, 146, 20, 13, DKSLATE, INK, SLATE)      # laptop on bed
    c.rect(134, 148, 16, 8, NAVY); c.rect(136, 150, 6, 1, SKY)
    # night-light plug on right wall
    c.box(164, 202, 4, 6, CREAM, INK)
    # cat bed cushion
    c.ellipse(82, 176, 32, 24, fill=INK)
    c.ellipse(83, 177, 30, 22, fill=RED)
    c.ellipse(86, 180, 24, 16, fill=SALMON)
    # rug + track
    c.box(22, 208, 136, 84, MAUVE, INK)
    c.rect(24, 210, 132, 80, PLUM)
    for x in range(24, 157, 4):
        c.px(x, 207, CREAM); c.px(x, 292, CREAM)
    cx, cy, rx, ry = TRACK["cx"], TRACK["cy"], TRACK["rx"], TRACK["ry"]
    c.ellipse(cx - rx - 8, cy - ry - 8, 2 * rx + 17, 2 * ry + 17, fill=INK)
    c.ellipse(cx - rx - 7, cy - ry - 7, 2 * rx + 15, 2 * ry + 15, fill=DKSLATE)
    c.ellipse(cx - rx + 7, cy - ry + 7, 2 * rx - 13, 2 * ry - 13, fill=INK)
    c.ellipse(cx - rx + 8, cy - ry + 8, 2 * rx - 15, 2 * ry - 15, fill=DKGREEN)
    for k in range(28):
        a = 2 * math.pi * k / 28
        c.px(cx + rx * math.cos(a), cy + ry * math.sin(a), LTGREY)
    for i in range(6):                                 # start line
        c.rect(cx - 2 + (i % 2) * 2, cy + ry - 6 + i * 2, 2, 2, WHITE if i % 2 else INK)
    c.blit(CONE, 76, 245); c.blit(CONE, 98, 243)
    c.rect(84, 253, 12, 1, GREEN); c.rect(80, 239, 3, 3, GREEN)
    # charger box + cable
    c.box(160, 216, 6, 9, DKSLATE, INK, SLATE)
    c.line(162, 225, 160, 236, INK); c.line(160, 236, 150, 240, INK)
    # floor clutter
    c.blit(SNEAKER, 64, 312); c.blit(SNEAKER, 71, 314)
    c.box(98, 302, 16, 10, BLUE, INK, SKY, DKSLATE); c.rect(100, 306, 12, 1, YELLOW)   # books
    c.box(100, 296, 12, 7, RED, INK, SALMON, MAROON)
    c.box(40, 186, 12, 6, INK, INK); c.px(43, 188, RED); c.px(48, 188, BLUE)           # controller
    c.ellipse(134, 300, 30, 26, fill=INK)                                               # bean bag
    c.ellipse(135, 301, 28, 23, fill=BLUE)
    c.ellipse(139, 304, 16, 12, fill=SKY)
    # bookshelf bottom-left
    c.box(14, 300, 18, 30, BROWN, INK, WOOD)
    for y in (308, 318):
        c.rect(15, y, 16, 1, INK)
    for i in range(7):
        col = (RED, GOLD, GREEN, BLUE, MAUVE, CREAM, SKY)[i]
        c.rect(16 + i * 2, 302 + (i % 3), 2, 6 - (i % 3), col)
        c.rect(16 + i * 2, 311 + (i % 2), 2, 7 - (i % 2), (BLUE, RED, CREAM, GOLD, SKY, GREEN, MAUVE)[i])
    c.blit(PLANT, 40, 296)
    # radiator under the window
    c.box(13, 176, 6, 22, LTGREY, INK)
    for y in range(178, 196, 3):
        c.rect(14, y, 4, 1, GREY)
    return c


class Lights:
    def __init__(self):
        self.lamp_in = _circle_mask(*LAMP, 12)
        self.lamp_out = _circle_mask(*LAMP, 24)
        self.nl_in = _circle_mask(*NLIGHT, 8)
        self.nl_out = _circle_mask(*NLIGHT, 16)
        self.moon = _poly_mask([(12, 114), (12, 170), (78, 236), (92, 210)])
        self.screen = _poly_mask([(112, 62), (152, 62), (160, 100), (104, 100)])

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


# ------------------------------------------------------------------- scene ---
class CozyEpisode:
    """Episode = dict(headline, captions, car_art, beats, palette swaps...)."""

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

    # car lap angle from a piecewise speed profile, integrated on a fine grid
    def _theta_table(self):
        dt, th, out = 1 / 300, math.pi / 2, []
        for i in range(int(self.ep["duration"] * 300) + 2):
            out.append(th)
            th += self.ep["car_speed"](i * dt) * dt
        return out

    def _sim(self, step):
        """Advance particles exactly once per step, deterministically."""
        b = self.ep["beats"]
        while self._sim_step < step:
            self._sim_step += 1
            s = self._sim_step
            t = self.clock.t(s)
            r = self.snow.rng
            for _ in range(2 if t > b["snow"] else 0):
                self.snow.emit(r.integers(2, 10), 113, 0, 1, 60, [WHITE], every=int(r.integers(1, 3)))
            for q in self.snow.p:
                if s % 4 == 0:
                    q["x"] += int(r.integers(-1, 2))
            self.snow.step((2, 113, 10, 171))
            if s % 2 == 0:
                self.steam.emit(103 + int(self.steam.rng.integers(0, 3)), 64, 0, -1, 7,
                                [WHITE, LTGREY, GREY])
            for q in self.steam.p:
                if q["age"] % 3 == 2:
                    q["x"] += int(self.steam.rng.integers(-1, 2))
            self.steam.step()
            self.fx.step()

    def car_pose(self, t):
        th = self._theta[min(len(self._theta) - 1, int(t * 300))]
        T_ = TRACK
        x = T_["cx"] + T_["rx"] * math.cos(th)
        y = T_["cy"] + T_["ry"] * math.sin(th)
        vx, vy = -T_["rx"] * math.sin(th), T_["ry"] * math.cos(th)
        return x, y, math.degrees(math.atan2(vx, -vy))

    def world(self, step, t):
        ep, b = self.ep, self.ep["beats"]
        self._sim(step)
        c = self.room.copy()
        # string lights: colours cycle with uneven holds
        k = cycle(t, (0.6, 0.4, 0.7, 0.5))
        for i, x in enumerate(range(8, WW - 6, 9)):
            y = 5 + (1 if (i % 4) in (1, 2) else 0) + (1 if i % 4 == 2 else 0)
            c.px(x, y - 1, INK)
            c.rect(x, y, 2, 2, (GOLD, HOT, CYAN, GREEN)[(i + k) % 4])
        # thermometer drops when it gets cold
        lvl = tween_int(t, b["night"], b["night"] + 3.0, 20, 5)
        c.rect(159, 39 - lvl, 1, lvl, RED)
        # monitor: battery graph
        c.rect(116, 44, 32, 16, NAVY)
        level = ep["battery"](t)
        bars = max(0, min(6, int(round(level * 6 / 100))))
        col = GREEN if level > 50 else GOLD if level > 25 else RED
        for i in range(6):
            c.rect(119 + i * 5, 55 - i, 3, 2 + i, col if i < bars else DKSLATE)
        c.text(TINY, f"{int(level):d}%", 147, 46, WHITE, align="right")
        # charger LED
        c.px(163, 219, GREEN if t >= b["charge"] else (RED if t >= b["dying"] else DKSLATE))
        # snow + steam
        self.snow.draw(c)
        self.steam.draw(c)
        # cat
        awake = b["cat_wake"] <= t
        f = (cycle(t, (0.9, 0.3, 0.4)) if awake else cycle(t, (1.1, 0.8)))
        c.blit(CATS[(int(awake), f if awake else f % 2)], 87 + (1 if awake else 0), 178)
        if not awake:
            zk = int((t * 10) % 18)
            if zk < 12:
                c.text(TINY, "Z", 104 + zk // 4, 176 - zk, WHITE)
        # car
        x, y, deg = self.car_pose(t)
        jx = jy = 0
        if b["crank"] <= t < b["crank_end"]:
            jx, jy = shake(step, 1, 11)
            if step % 2 == 0:
                self.fx.emit(x + jx, y + jy, int(self.fx.rng.integers(-1, 2)), -1, 4,
                             [YELLOW, GOLD, ORANGE])
        a, (ox, oy) = self.cars[angle_index(deg, len(self.cars))]
        sh = np.where(a != T, np.uint8(1), np.uint8(0)).astype(bool)
        sx, sy = int(round(x)) - ox + 1, int(round(y)) - oy + 2   # palette-swap shadow
        sub = c.a[sy:sy + a.shape[0], sx:sx + a.shape[1]]
        m = sh[:sub.shape[0], :sub.shape[1]]
        sub[m] = SHADOW[sub[m]]
        c.blit(a, int(round(x)) - ox + jx, int(round(y)) - oy + jy)
        self.fx.draw(c)
        # lighting
        mode = ep["light"](t, step)
        self.lights.apply(c, mode)
        return c

    def hud(self, v, step, t):
        ep = self.ep
        # channel tag
        v.text(TINY, ep.get("tag", "CAR STUFF, EXPLAINED"), W // 2, 4, CREAM, outline_c=INK,
               align="center")
        # headline: big panel drops in on integer steps, then a compact bar
        if t < ep.get("headline_until", 2.6):
            y0 = tween_int(t, 0.0, 0.5, -50, 12, "out")
            v.box(14, y0, W - 28, 44, INK, DKSLATE, NAVY)
            for i, line in enumerate(ep["headline"]):
                col = YELLOW if i == len(ep["headline"]) - 1 else WHITE
                v.text(HEAD, line, W // 2, y0 + 5 + i * 19, col, shadow_c=MAROON if i else DKSLATE,
                       align="center")
        else:
            v.box(30, 11, W - 60, 13, INK, DKSLATE)
            v.text(CAP, " ".join(ep["headline"]), W // 2, 14, YELLOW, align="center")
        # caption box with typewriter reveal (stepped)
        for (t0, t1, lines) in ep["captions"]:
            if t0 <= t < t1:
                v.box(6, 276, W - 12, 40, INK, DKSLATE, NAVY)
                n = int((t - t0) * 40)
                shown = 0
                for i, (txt, col) in enumerate(lines):
                    k = max(0, min(len(txt), n - shown))
                    shown += len(txt)
                    if k:
                        v.text(CAP, txt[:k], W // 2, 282 + i * 15, col, align="center")
        # battery widget
        level = ep["battery"](t)
        by = 262
        v.box(6, by, 40, 13, INK, DKSLATE)
        v.rect(9, by + 2, 21, 9, GREY); v.rect(10, by + 3, 19, 7, INK); v.rect(30, by + 4, 2, 5, GREY)
        segs = max(0, min(5, int(math.ceil(level / 20))))
        col = GREEN if level > 50 else GOLD if level > 25 else RED
        if level <= 25 and (step // 2) % 2:
            col = MAROON
        for i in range(segs):
            v.rect(11 + i * 4, by + 4, 3, 5, col)
        if t >= ep["beats"]["charge"] and (step // 3) % 2 == 0:
            v.text(TINY, "+", 38, by + 4, GREEN)

    def frame(self, step, t):
        w = self.world(step, t)
        cam = Camera(0, self.ep["camera"](t))
        sh = shake(step, 1, 3) if self.ep["beats"]["crank"] <= t < self.ep["beats"]["crank_end"] and step % 3 == 0 else (0, 0)
        v = cam.view(w, W, H, sh)
        self.hud(v, step, t)
        return v

    def render(self, out, master=None, native_dir=None):
        return render(self.frame, self.clock, PAL, out, 6, master, native_dir)

    def preview(self, path, times=(0.3, 2.0, 4.0, 5.6, 8.0, 10.6, 12.6), zoom=2):
        from PIL import Image
        steps = [min(self.clock.step_of[min(self.clock.n - 1, int(tt * 30))], self.clock.steps - 1)
                 for tt in times]
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
