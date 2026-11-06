"""cozy-sim-room: 15 s seamless ambient loop, no voice, no captions.

Oblique top-down bedroom at night: sim-racing desk with three screens, gamer in a red hoodie on a wheel,
sleeping cat, bed with a plush, window with the city. 270x480 native -> 4x nearest -> 1080x1920, 60 fps.
Every motion uses an integer number of cycles per 15 s, so frame 900 == frame 0.
Usage: python render.py still OUTDIR T... | video OUT.mp4 | loopcheck OUT.mp4
"""
import math, os, subprocess, sys, json
from multiprocessing import Pool
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'assets'))
from audio import sfx                                             # noqa: E402
from ambient import glow, bayer, paste, vgrad, up                 # noqa: E402
import cozyroom as cr                                             # noqa: E402

W0, H0, K = 270, 480, 4
W, H = W0 * K, H0 * K
FPS = 60
DUR = 15.0
P = cr.PAL
BAY = bayer(H0, W0)


def cyc(t, k): return (t * k / DUR) % 1.0
def sn(t, k, ph=0.0): return math.sin(2 * math.pi * k * t / DUR + ph)
def col(c): return np.array(P[c], np.float32)


def R(a, x0, y0, x1, y1, c): a[y0:y1 + 1, x0:x1 + 1] = P[c]


def dith(a, x0, y0, x1, y1, c, lvl=.5):
    """Bayer-dithered fill: lvl of the pixels take colour c (classic pixel-art soft gradient)."""
    m = BAY[y0:y1 + 1, x0:x1 + 1] < lvl
    a[y0:y1 + 1, x0:x1 + 1][m] = P[c]


def shade(a, spr, x, y, dx=2, dy=2, k=.55):
    """Soft drop shadow from a sprite's alpha: full at (dx,dy), dithered half at (dx+1,dy+1)."""
    m = spr[..., 3] > 0
    for ox, oy, kk, lv in ((dx, dy, k, 1.0), (dx + 1, dy + 1, k, .5)):
        ys, xs = np.nonzero(m)
        ys, xs = ys + y + oy, xs + x + ox
        ok = (ys >= 0) & (ys < H0) & (xs >= 0) & (xs < W0)
        ys, xs = ys[ok], xs[ok]
        sel = BAY[ys, xs] < lv
        a[ys[sel], xs[sel]] *= kk


def place(a, spr, x, y, shadow=True):
    if shadow: shade(a, spr, x, y)
    paste(a, spr, x, y)


def box(a, x0, y0, x1, y1, h, top, front, rim):
    """Furniture block in the oblique view: top surface, front face below it, rim light, soft shadow."""
    shade(a, np.ones((y1 - y0 + h + 1, x1 - x0 + 1, 4), np.float32), x0, y0, 2, 3, .55)
    R(a, x0, y0, x1, y1, top); R(a, x0, y1 + 1, x1, y1 + h, front); R(a, x0, y0, x1, y0, rim)
    R(a, x0, y1 + h, x1, y1 + h, '1'); R(a, x0, y1 + 1, x1, y1 + 1, '2')


def blob(w, h, ramp):
    """Soft round object (beanbag): ramp dark->light, lit from the top-left, as a pixel map."""
    rows = []
    for y in range(h):
        r = ''
        for x in range(w):
            u, v = (x - w / 2 + .5) / (w / 2), (y - h / 2 + .5) / (h / 2)
            d = u * u + v * v
            if d > 1: r += '.'; continue
            l = .55 - .45 * (u + v) * .7 - d * .3
            r += ramp[min(len(ramp) - 1, max(0, int(l * len(ramp))))]
        rows.append(r)
    return cr.S(rows)


def track(a, x0, y0, w, h):
    """Toy race track on a green felt play mat: grey oval with red/white kerbs and a start line."""
    shade(a, np.ones((h + 8, w + 8, 4), np.float32), x0 - 4, y0 - 4, 2, 2, .6)
    R(a, x0 - 4, y0 - 4, x0 + w + 3, y0 + h + 3, 'A'); dith(a, x0 - 4, y0 - 4, x0 + w + 3, y0 + h + 3, 'z', .3)
    R(a, x0 - 4, y0 - 4, x0 + w + 3, y0 - 4, 'B')
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            u, v = (x - x0 - w / 2 + .5) / (w / 2), (y - y0 - h / 2 + .5) / (h / 2)
            d = u * u + v * v
            if .42 < d <= 1: a[y, x] = P['D'] if .49 < d < .92 else P['v' if (x + y) // 2 % 2 else 'H']
    R(a, x0 + w // 2, y0 + 1, x0 + w // 2 + 1, y0 + 5, 'H')


# ------------------------------------------------------------------ static room
FLOOR = (24, 75, 246, 466)
WIN = (8, 162, 19, 248)          # window glass on the left wall face
SCR = {'chart': (54, 50, 44, 22), 'race': (106, 44, 58, 28), 'garage': (170, 50, 44, 22)}   # x, y, w, h


def build_static():
    a = np.zeros((H0, W0, 3), np.float32); a[:] = P['0']
    em = np.zeros((H0, W0), np.float32)
    # walls: caps, back wall face, side wall faces
    R(a, 2, 6, 267, 13, '1'); R(a, 2, 13, 267, 13, '3')
    R(a, 24, 14, 246, 74, '3')
    for x in range(28, 246, 8): R(a, x, 16, x, 70, '2')
    dith(a, 24, 14, 246, 24, '2', .5)
    R(a, 24, 14, 246, 14, '4'); R(a, 24, 71, 246, 74, '2'); R(a, 24, 71, 246, 71, '4')
    for (x0, x1) in ((4, 23), (247, 266)):
        R(a, x0, 14, x1, 470, '2'); dith(a, x0, 14, x1, 470, '1', .25)
        R(a, x0, 14, x1, 14, '3')
    R(a, 0, 6, 3, 479, '1'); R(a, 267, 6, 269, 479, '1')
    R(a, 23, 14, 23, 470, '1'); R(a, 247, 14, 247, 470, '1')
    R(a, 22, 75, 22, 466, '3'); R(a, 248, 75, 248, 466, '3')         # wall-floor rim light
    # floor planks running toward the viewer
    x0, y0, x1, y1 = FLOOR
    R(a, x0, y0, x1, y1, '4')
    rng = np.random.default_rng(4)
    for i, x in enumerate(range(x0, x1 + 1, 10)):
        R(a, x, y0, x, y1, '3')
        if i % 3 == 1: dith(a, x + 1, y0, min(x + 9, x1), y1, '3', .5)
        elif i % 3 == 2: dith(a, x + 1, y0, min(x + 9, x1), y1, '5', .25)
        for yy in range(y0 + int(rng.integers(10, 60)), y1, int(rng.integers(50, 90))):
            R(a, x + 1, yy, min(x + 9, x1), yy, '3')
        for _ in range(6):
            gx, gy = x + int(rng.integers(2, 8)), int(rng.integers(y0, y1))
            R(a, gx, gy, gx, min(gy + 2, y1), '5')
    for d, lv in ((0, .75), (1, .5), (2, .25), (3, .12)):                 # ambient occlusion along walls
        dith(a, x0 + d, y0, x0 + d, y1, '2', lv); dith(a, x1 - d, y0, x1 - d, y1, '2', lv)
        dith(a, x0, y0 + d, x1, y0 + d, '2', lv)
    R(a, 2, 467, 267, 479, '1'); R(a, 2, 467, 267, 467, '3')
    R(a, 44, 465, 104, 469, '5'); R(a, 44, 465, 104, 465, '6')       # door threshold
    # rug
    R(a, 30, 192, 122, 264, 'b'); R(a, 32, 194, 120, 262, 'c'); R(a, 35, 197, 117, 259, 'b')
    for yy in range(201, 256, 9):
        for xx in range(40, 114, 9):
            for k in range(3):
                R(a, xx + k, yy - k, xx + k, yy + k, 'L'); R(a, xx + 6 - k, yy - k, xx + 6 - k, yy + k, 'L')
            a[yy, xx + 3] = P['M']
    dith(a, 35, 197, 117, 259, 'a', .2)
    for yy in range(193, 264, 2): a[yy, 28] = P['G']; a[yy, 124] = P['G']
    # doormat with an original wave pattern
    R(a, 46, 438, 102, 460, 'l'); R(a, 48, 440, 100, 458, 'm')
    for xx in range(50, 99):
        a[444 + int(round(2 * math.sin(xx * .5))), xx] = P['o']; a[453 + int(round(2 * math.sin(xx * .5 + 3))), xx] = P['o']
    dith(a, 48, 440, 100, 458, 'n', .12)
    # back wall: photo frame, vents, console shelf
    R(a, 28, 22, 37, 31, 'G'); R(a, 29, 23, 36, 30, 'h'); R(a, 30, 27, 35, 30, 'A'); a[25, 33] = P['q']
    for vx in (26, 232):
        R(a, vx, 44, vx + 12, 66, '1')
        for yy in range(46, 65, 2): R(a, vx + 1, yy, vx + 11, yy, '2')
    shelf, _ = cr.console_shelf(190)
    shade(a, shelf, 40, 18, 0, 3, .6); paste(a, shelf, 40, 18)
    # monitors
    for name, (sx, sy, sw, sh) in SCR.items():
        m = cr.monitor(sw, sh); shade(a, m, sx - 3, sy - 3, 1, 3, .5); paste(a, m, sx - 3, sy - 3)
        em[sy:sy + sh, sx:sx + sw] = 1
    # desk (top + front face, purple rim on the lip)
    R(a, 30, 76, 240, 106, '3'); dith(a, 30, 76, 240, 106, '4', .18)
    for yy in (82, 91, 99): dith(a, 30, yy, 240, yy, '2', .5)
    R(a, 30, 107, 240, 107, 'd'); R(a, 30, 108, 240, 112, '2'); R(a, 30, 112, 240, 112, '1')
    R(a, 30, 76, 240, 76, '2')
    for d, lv in ((0, .8), (1, .5), (2, .25)): dith(a, 30, 113 + d, 240, 113 + d, '1', lv)
    # under-desk fronts: drawer unit, PC tower
    R(a, 32, 113, 60, 130, '3'); R(a, 32, 113, 60, 113, '5'); R(a, 32, 121, 60, 121, '2'); R(a, 44, 116, 48, 117, 'F'); R(a, 44, 125, 48, 126, 'F')
    R(a, 212, 113, 236, 142, '1'); R(a, 213, 114, 235, 141, '2'); R(a, 212, 113, 236, 113, '4')
    shade(a, np.ones((30, 25, 4), np.float32), 212, 113, 2, 3, .6)
    # desk items
    for name, x, y in (('lamp', 34, 79), ('keyboard', 54, 92), ('mouse', 78, 93), ('notes', 92, 80), ('figure', 102, 81),
                       ('phone', 176, 93), ('headphones', 209, 91), ('can', 226, 80), ('cases', 66, 80), ('books', 42, 94),
                       ('remote', 160, 93), ('drink', 220, 98)):
        place(a, cr.prop(name), x, y)
    R(a, 125, 92, 145, 96, '2'); R(a, 125, 92, 145, 92, '5')          # wheel base clamp
    place(a, cr.mug(), 192, 82)
    # left wall: plate, key hook; window frame
    R(a, 8, 96, 19, 103, 'G'); R(a, 9, 97, 18, 102, 'k'); R(a, 10, 99, 17, 100, 'i')
    R(a, 10, 420, 17, 421, 'E'); a[422, 11] = P['p']; a[423, 11] = P['p']; a[422, 15] = P['F']
    R(a, 6, 158, 21, 252, '5'); R(a, 6, 158, 21, 158, '7'); R(a, 7, 159, 20, 251, '4')
    em[WIN[1]:WIN[3] + 1, WIN[0]:WIN[2] + 1] = 1
    R(a, 5, 253, 22, 255, '6')                                       # sill
    # right wall: posters
    for kind, y in (('track', 92), ('sunset', 190), ('blue', 320)):
        p = cr.poster(kind); shade(a, p, 249, y, 1, 2, .6); paste(a, p, 249, y)
    # bed (head at the top, against the right wall)
    R(a, 168, 148, 245, 302, 'm'); R(a, 168, 148, 245, 151, 'n'); R(a, 168, 148, 245, 148, 'o')
    R(a, 171, 152, 244, 299, 'G'); dith(a, 171, 152, 244, 299, 'F', .2)
    shade(a, np.ones((155, 78, 4), np.float32), 168, 148, 3, 4, .55)
    R(a, 168, 148, 245, 302, 'm'); R(a, 168, 148, 245, 151, 'n'); R(a, 168, 148, 245, 148, 'o')
    R(a, 171, 152, 244, 299, 'G'); dith(a, 171, 152, 244, 299, 'F', .2)
    for (px, pw) in ((176, 30), (210, 30)):                          # pillows
        R(a, px, 156, px + pw, 174, 'H'); R(a, px, 172, px + pw, 174, 'G'); R(a, px, 156, px + pw, 156, 'G')
        dith(a, px + 2, 165, px + pw - 2, 171, 'G', .3)
    # messy blanket: wavy top edge, folds, a corner flipped over
    for xx in range(171, 245):
        top = 196 + int(round(4 * math.sin(xx * .17) + 2 * math.sin(xx * .53)))
        R(a, xx, top, xx, 298, 'h'); a[top, xx] = P['j']; a[top + 1, xx] = P['i']
    for fx in (184, 199, 221, 236):
        for yy in range(205, 296):
            xx = fx + int(round(2 * math.sin(yy * .09 + fx)))
            if 171 <= xx < 245: a[yy, xx] = P['g']; a[yy, xx - 1] = P['i'] if yy % 3 else P['h']
    dith(a, 171, 260, 244, 298, 'g', .25)
    for k in range(14):                                             # flipped corner showing the sheet
        R(a, 171, 286 - k, 171 + 13 - k, 286 - k, 'G')
    R(a, 168, 302, 245, 305, 'l')
    place(a, cr.plush(), 190, 170)
    place(a, cr.prop('cap'), 226, 238); place(a, cr.prop('remote'), 200, 262); place(a, cr.prop('phone'), 214, 214)
    # furniture: dresser, low bookshelf, shoe rack, beanbag, toy race track
    box(a, 24, 300, 54, 330, 8, '5', '3', '7')
    for yy in (333, 336): R(a, 26, yy, 52, yy, '2')
    R(a, 37, 332, 41, 332, 'F'); R(a, 37, 335, 41, 335, 'F')
    box(a, 222, 344, 245, 414, 7, 'n', 'm', 'o')
    for yy in range(348, 410, 12):
        for k, c in enumerate('vjqAiwMp'):
            if 224 + k * 2 < 244: R(a, 224 + k * 2, yy, 225 + k * 2, yy + 8, c)
        R(a, 223, yy + 10, 244, yy + 10, 'l')
    box(a, 112, 448, 156, 456, 4, '6', '4', '7')
    place(a, blob(34, 24, 'cdef'), 64, 298)
    track(a, 96, 330, 74, 40)
    place(a, blob(26, 16, 'ghij'), 134, 386)
    place(a, cr.prop('box'), 100, 384); R(a, 102, 385, 112, 387, 'l'); place(a, cr.prop('tyre'), 104, 380, shadow=False)
    for name, x, y in (
        # around the chair: bin + misses, cans, plant, speaker
        ('bin', 70, 130), ('paper', 82, 140), ('paper', 64, 146), ('paper', 88, 152), ('cable', 96, 126), ('speaker', 58, 118),
        ('can', 152, 148), ('chips', 158, 160), ('plant', 160, 128),
        # rug: controller, yarn, model cars; bowls by the rug
        ('controller', 92, 202), ('yarn', 110, 246), ('car_red', 100, 226), ('car_blue', 40, 244), ('bowl', 34, 270), ('bowl2', 44, 272),
        # snack spot between rug and bed
        ('snack', 136, 228), ('chips', 150, 240), ('drink', 150, 220), ('cases', 138, 260),
        # dresser top + beanbag with the hoodie
        ('lamp', 28, 298), ('plant', 42, 296), ('hoodie', 70, 296), ('tee', 100, 304), ('sock', 58, 328),
        # garage corner: tyre, toolbox, cone, helmet, flag
        ('tyre', 30, 352), ('toolbox', 44, 356), ('cone', 62, 362), ('helmet', 32, 372), ('flag', 50, 376),
        # by the toy track
        ('car_yel', 118, 342), ('car_red', 150, 360), ('books', 176, 338), ('bottle', 172, 352), ('remote', 180, 374),
        # laundry at the foot of the bed
        ('basket', 186, 310), ('jeans', 200, 318), ('sock', 178, 324), ('tee', 206, 330),
        # bookshelf top
        ('car_blue', 226, 338), ('figure', 238, 340),
        # door: trainers, slippers, umbrella, backpack, skateboard
        ('trainer', 116, 438), ('trainer', 126, 440), ('trainer', 140, 437), ('slipper', 146, 440), ('umbrella', 28, 430),
        ('backpack', 30, 408), ('skate', 162, 404), ('bottle', 104, 420),
        # clothes pile + open box of car parts in the middle of the floor
        ('hoodie', 70, 392), ('jeans', 84, 398), ('tee', 64, 404), ('sock', 92, 410), ('cases', 128, 404)):
        place(a, cr.prop(name), x, y)
    # stack of boxes (bottom right) with a pizza box on top
    for bx, by in ((182, 446), (200, 446), (218, 446), (190, 436), (208, 436), (199, 426)):
        place(a, cr.prop('box'), bx, by)
    place(a, cr.prop('pizza'), 203, 420)
    return a, em


STATIC, EMIS = build_static()


# ------------------------------------------------------------------ gamer (char grid -> sprite with outline)
GX, GY = 108, 92                 # grid origin in room coords
GW, GH = 54, 62


class CG:
    def __init__(self): self.g = [['.'] * GW for _ in range(GH)]
    def put(self, x, y, c):
        x, y = int(round(x)) - GX, int(round(y)) - GY
        if 0 <= x < GW and 0 <= y < GH: self.g[y][x] = c
    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): self.put(x, y, c)
    def stamp(self, rows, x, y):
        for j, r in enumerate(rows):
            for i, c in enumerate(r):
                if c != '.': self.put(x + i, y + j, c)
    def limb(self, p0, p1, core, edge, hi):
        n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
        pts = [(p0[0] + (p1[0] - p0[0]) * k / max(1, n - 1), p0[1] + (p1[1] - p0[1]) * k / max(1, n - 1)) for k in range(n)]
        for (x, y) in pts: self.rect(int(round(x)) - 2, int(round(y)) - 1, int(round(x)) + 1, int(round(y)) + 1, edge)
        for (x, y) in pts: self.rect(int(round(x)) - 1, int(round(y)) - 1, int(round(x)), int(round(y)), core)
        for (x, y) in pts[::2]: self.put(x - 1, y - 1, hi)


HEAD = [".....llll.....", "...llmmnmll...", "..lmmnnmmmml..", ".lmmnmmmmmmml.", "FEEEEEEEEEEEEF", "GFlmmnmmmmmlFG",
        "GFlmmmmmmmmlFG", "FElmmmmmmmmlEF", ".ylmmmmmmmmly.", ".xllmmmmmmllx.", "...lllmmlll...", "....xyyyyx....",
        "..tuuuuuuuut..", ".tuvuttttuvut.", "..tttttttttt.."]


def gamer(t):
    steer = .55 * sn(t, 6) + .25 * sn(t, 15, 1.0)
    hx = int(round(1.2 * sn(t, 4) + steer * 1.4))
    cx = int(round(.8 * sn(t, 2, .5)))
    g = CG()
    # pedal plate + legs reaching under the desk
    g.rect(124, 113, 146, 118, '2'); g.rect(124, 113, 146, 113, '3')
    for px in (126, 133, 141): g.rect(px, 114, px + 2, 116, '5')
    press = 1 if sn(t, 12) > .3 else 0
    for lx in (130, 139):
        g.rect(lx - 2, 117, lx + 2, 126, 'h'); g.rect(lx - 1, 117, lx - 1, 126, 'i')
        g.rect(lx - 2, 114 + (press if lx > 135 else 0), lx + 2, 116 + (press if lx > 135 else 0), 'H')
    # shoulders (hoodie), seen from above-behind
    for y in range(124, 135):
        for x in range(117, 154):
            d = ((x - 135 - hx * .5) / 17.5) ** 2 + ((y - 129.5) / 5.5) ** 2
            if d <= 1: g.put(x, y, 'v' if (y < 127 and d > .45) else ('t' if d > .8 else 'u'))
    # chair back over the lower torso (turns 1px)
    g.stamp([r.replace('v', 'e').replace('u', 'd') for r in cr.CHAIR], 125 + cx, 131)
    # wheel ring (turns with steering) and spokes
    ang = steer * .9
    for k in range(48):
        th = 2 * math.pi * k / 48
        for rr, c0 in ((11, 'F'), (10, 'E')):
            g.put(135 + rr * math.cos(th), 101 + rr * .38 * math.sin(th), c0 if math.sin(th) < 0 else 'D')
    for th in (ang, ang + math.pi, ang + math.pi / 2):
        for r in range(1, 10): g.put(135 + r * math.cos(th), 101 + r * .38 * math.sin(th), 'D')
    g.rect(133, 100, 137, 102, '1'); g.put(135 + 10.5 * math.cos(ang - math.pi / 2), 101 + 4 * math.sin(ang - math.pi / 2), 'v')
    # arms + hands on the rim
    hands = [(135 + 11 * math.cos(math.pi + ang), 101 + 4.2 * math.sin(math.pi + ang)),
             (135 + 11 * math.cos(ang), 101 + 4.2 * math.sin(ang))]
    for (sx, sy), (hxp, hyp) in zip(((120 + hx * .5, 127), (150 + hx * .5, 127)), hands):
        g.limb((sx, sy), (hxp, hyp + 2), 'u', 't', 'v')
        g.rect(int(round(hxp)) - 1, int(round(hyp)) - 1, int(round(hxp)) + 1, int(round(hyp)) + 1, 'y')
        g.put(hxp - 1, hyp - 1, 'x')
    g.stamp(HEAD, 128 + hx, 111)
    return cr.S([''.join(r) for r in g.g], outline='0')


# ------------------------------------------------------------------ screens
def race(t, w, h):
    """Pixel racing game: road scrolls toward the viewer, kerbs, curve sway, player car."""
    s = np.zeros((h, w, 3), np.float32)
    hz = 9
    s[:hz] = vgrad(hz, w, [(0, P['g']), (1, P['M'])])
    for x in range(w): s[hz - 1 - int(2 + 2 * math.sin(x * .3) + math.sin(x * .9)):hz, x] = P['b']
    ph = cyc(t, 45)
    curve = 6 * sn(t, 3)
    steer = .55 * sn(t, 6) + .25 * sn(t, 15, 1.0)
    for y in range(hz, h):
        z = 1.0 / (y - hz + 1)
        band = int((z * 30 + ph * 2) * 2) % 2
        k = (y - hz) / (h - hz)
        mid = w / 2 + curve * (1 - k) ** 2 - steer * 4 * k
        half = 3 + k * 26
        s[y, :] = P['A' if band else 'B']
        x0, x1 = int(mid - half), int(mid + half)
        s[y, max(0, x0):min(w, x1)] = P['D']
        for xx in (x0 - 1, x0 - 2, x1, x1 + 1):
            if 0 <= xx < w: s[y, xx] = P['v' if band else 'H']
        if band and 0 <= int(mid) < w: s[y, int(mid)] = P['H']
    car = cr.S(["..uuuu..", ".uvvvvu.", "uukkkkuu", "vuuuuuuv", "1u1111u1", "11....11"], outline=None)
    paste(s, car, w // 2 - 4 + int(round(steer * 2)), h - 7)
    s[1, 2:12] = P['k']; s[1, 2 + int(cyc(t, 15) * 10)] = P['v']       # lap progress bar
    return s


CHART = [math.sin(2 * math.pi * i / 60 * 2) * 3 + math.sin(2 * math.pi * i / 60 * 7 + 1) * 1.6 for i in range(60)]


def chart(t, w, h):
    s = np.zeros((h, w, 3), np.float32); s[:] = P['1']
    for y in range(3, h, 5): s[y, :] = P['2']
    for x in range(3, w, 8): s[:, x] = P['2']
    off = int(cyc(t, 1) * 60)                                        # one tick per 0.25 s, 60 ticks per loop
    pts = [int(round(h / 2 + CHART[(off + i) % 60])) for i in range(w // 2)]
    for i in range(len(pts) - 1):
        for x in (2 * i, 2 * i + 1):
            y0, y1 = sorted((pts[i], pts[i + 1]))
            s[y0:y1 + 1, x] = P['J']
    s[pts[-1] - 1:pts[-1] + 2, w - 3:w - 1] = P['v' if cyc(t, 30) < .5 else 'w']
    for i in range(6):                                               # sector bars along the bottom
        hh = 2 + (i * 7 + off // 4) % 4
        s[h - hh:h, 2 + i * 7:6 + i * 7] = P['e' if i % 2 else 'd']
    s[1, 1:w - 1:3] = P['g']
    return s


GCAR = ["...vvvvvv...", "..vwwvvwwv..", ".vvvvvvvvvv.", "1vvkkkkkkvv1", "1vkkkkkkkkv1", ".vvvvvvvvvv.", ".vuuuuuuuuv.",
        ".vvvvvvvvvv.", ".vvvvvvvvvv.", "1vvkkkkkkvv1", "1vvvvvvvvvv1", ".vvvvvvvvvv.", "..uuuuuuuu..", "..w......w.."]
GCAR_RGBA = cr.S(GCAR, outline=None)


def garage(t, w, h):
    s = np.zeros((h, w, 3), np.float32); s[:] = P['E']
    s[:6] = P['D']; s[0, 4:w - 4:6] = P['H']
    for y in range(6, h):
        for x in range(w):
            if ((x - w / 2) / 19) ** 2 + ((y - 14) / 7.5) ** 2 <= 1: s[y, x] = P['F']
    th = 2 * math.pi * cyc(t, 1)
    c, sn_ = math.cos(th), math.sin(th)
    ch, cw = GCAR_RGBA.shape[:2]
    for y in range(h):
        for x in range(w):
            u, v = (x - w / 2) * 1.0, (y - 14) * 2.0                 # ellipse floor: squash y by 2
            sx, sy = c * u + sn_ * v + cw / 2, -sn_ * u + c * v + ch / 2
            ix, iy = int(math.floor(sx)), int(math.floor(sy))
            if 0 <= ix < cw and 0 <= iy < ch and GCAR_RGBA[iy, ix, 3] > 0: s[y, x] = GCAR_RGBA[iy, ix, :3]
    s[1, w - 6:w - 2] = P['A']
    return s


# ------------------------------------------------------------------ window, curtain, motes
SKYR = np.random.default_rng(9)
WW, WH = WIN[2] - WIN[0] + 1, WIN[3] - WIN[1] + 1
SKY = vgrad(WH, WW, [(0, P['g']), (.55, P['b']), (1, P['L'])])
BLDG = []
x = 0
while x < WW:
    bw, top = int(SKYR.integers(3, 6)), int(SKYR.integers(20, 60))
    BLDG.append((x, bw, top)); x += bw
LIGHTS = [(int(SKYR.integers(top + 2, WH - 2)), int(SKYR.integers(bx, bx + bw)), str(SKYR.choice(list('qpjr'))), int(SKYR.integers(1, 9)))
          for bx, bw, top in BLDG for _ in range(4)]
DROPS = [(int(SKYR.integers(0, WW)), SKYR.random(), int(SKYR.integers(4, 7))) for _ in range(14)]
MOTES = [(SKYR.random(), SKYR.random(), int(SKYR.integers(1, 4)), SKYR.random() * 6.28) for _ in range(22)]


def window(t):
    s = SKY.copy()
    for bx, bw, top in BLDG:
        s[top:, bx:bx + bw] = P['1']; s[top, bx:bx + bw] = P['2']
    for (y, x, c, k) in LIGHTS:
        if sn(t, k, x * 1.7 + y) > -.6: s[y, x] = P[c]
    s[WH - 6, :] = P['D']                                             # street
    for (ev, cc, dirn) in ((3.0, 'q', 1), (10.5, 'v', -1)):          # car lights streak past twice per loop
        p = (t - ev) / 1.1
        if 0 <= p < 1:
            yy = int((p if dirn > 0 else 1 - p) * (WH + 10)) - 5
            for k in range(6):
                y2 = yy - dirn * k
                if 0 <= y2 < WH: s[y2, WW - 3:WW - 1] = P[cc] if k < 2 else P['p' if cc == 'q' else 'u']
    for (x, ph, k) in DROPS:                                          # rain on the glass
        y = int(((ph + cyc(t, k * 2)) % 1) * (WH + 6)) - 3
        for d in range(3):
            if 0 <= y + d < WH: s[y + d, x] = s[y + d, x] * .4 + col('k') * .6
    return s


def curtain(a, t):
    for y in range(152, 160): R(a, 4, y, 23, y, 'c' if y % 3 else 'b')
    for y in range(160, 262):
        sway = 1.6 * sn(t, 2) * (y - 160) / 100 + .6 * sn(t, 5, y * .05)
        x0 = 15 + int(round(sway))
        for x in range(x0, min(29, x0 + 8 + (y - 160) // 30)):
            a[y, x] = P['d' if (x - x0) % 3 == 0 else ('c' if (x - x0) % 3 == 1 else 'b')]
        a[y, x0] = P['e']                                             # rim light from the window


BEAM = np.zeros((H0, W0), np.float32)
for y in range(H0):
    for x in range(24, W0):
        u = (x - 24) / 130                                             # along the shaft, down-right
        if u > 1: continue
        yc0, yc1 = 165 + u * 70, 245 + u * 95
        if yc0 <= y <= yc1 and x <= 246: BEAM[y, x] = (1 - u) ** 1.3 * (1 - .4 * abs((y - (yc0 + yc1) / 2) / ((yc1 - yc0) / 2)))
BEAM = np.floor(BEAM * 4 + BAY) / 4


# ------------------------------------------------------------------ frame
def frame(n, raw=True):
    t = n / FPS
    e = .5 - .5 * math.cos(2 * math.pi * t / DUR)                    # 0 = blue dusk, 1 = warm night
    a = STATIC.copy(); em = EMIS.copy()
    # screens
    for name, fn in (('chart', chart), ('race', race), ('garage', garage)):
        sx, sy, sw, sh = SCR[name]; a[sy:sy + sh, sx:sx + sw] = fn(t, sw, sh)
    # LED strip under the console shelf
    led = .5 + .5 * sn(t, 4)
    lc = col('e') * (1 - led) + col('j') * led
    a[38:40, 42:228] = lc; em[38:40, 42:228] = 1
    # window + curtain
    a[WIN[1]:WIN[3] + 1, WIN[0]:WIN[2] + 1] = window(t)
    curtain(a, t)
    # lamp bulb, PC fans, phone, fairy lights
    a[81:83, 36:39] = P['r']; em[81:83, 36:39] = 1
    hue = [col('M'), col('e'), col('j'), col('J')]
    for i, fy in enumerate((120, 132)):
        c = hue[int(cyc(t, 3) * 4 + i) % 4]
        for k in range(12):
            th = 2 * math.pi * k / 12 + 2 * math.pi * cyc(t, 30)
            xx, yy = int(round(224 + 4 * math.cos(th))), int(round(fy + 4 * math.sin(th)))
            a[yy, xx] = c if k % 3 else col('H'); em[yy, xx] = 1
    if 5.0 <= t < 6.5: a[94:98, 177:180] = P['k']; em[94:98, 177:180] = 1
    for i in range(12):
        fx = 250 + int(round(12 * i / 11)); fy = 150 + i * 13 + int(3 * math.sin(i * 1.3))
        on = sn(t, (i % 4) + 2, i) > -.3
        a[fy, fx] = P[('q', 'N', 'K')[i % 3]] if on else P['D']; em[fy, fx] = on
    # mug steam
    for i in range(5):
        p = cyc(t + i * DUR / 30, 6)
        sx = 196 + int(round(1.5 * math.sin(p * 8 + i)))
        sy = 81 - int(p * 16)
        if p < .85: a[sy, sx] = a[sy, sx] * (.35 + .5 * p) + col('G') * (.65 - .5 * p)
    # cat (breathing every 2.5 s, tail flicks twice per loop)
    flick = 1 if 3.0 <= t < 3.35 else (-1 if 9.2 <= t < 9.55 else 0)
    c = cr.cat(breath=cyc(t, 6), flick=flick)
    place(a, c, 62, 216)
    # gamer
    gm = gamer(t)
    shade(a, gm, GX, GY, 2, 3, .6); paste(a, gm, GX, GY)

    # ---- light: mood grade, dithered glows, window shaft, emissive restore
    amb = np.array([.58, .64, .9], np.float32) * (1 - e) + np.array([.82, .66, .6], np.float32) * e
    lit = a * amb
    flick_s = 1 + .06 * sn(t, 30)
    glow(lit, 135, 60, 110, (150, 110, 255), .38 * flick_s, ry=80)
    glow(lit, 135, 39, 120, tuple(lc), .3 + .1 * led, ry=30)
    glow(lit, 135, 118, 34, (90, 150, 255), .12 * flick_s, ry=24)                # screen spill on the gamer
    wc = np.array([110, 150, 235]) * (1 - e) + np.array([255, 185, 110]) * e
    glow(lit, 14, 205, 70, tuple(wc), .3 + .25 * e, ry=90)
    lit += (BEAM * (.18 + .22 * e))[..., None] * (wc - lit * .3)
    glow(lit, 37, 82, 34, (255, 200, 120), .45)
    glow(lit, 224, 126, 26, tuple(hue[int(cyc(t, 3) * 4) % 4]), .35)
    glow(lit, 196, 86, 12, (255, 220, 160), .2)
    m = em > 0
    lit[m] = a[m] * (.92 + .08 * flick_s)
    for (u0, v0, k, ph) in MOTES:                                    # dust in the window shaft
        u = (u0 + cyc(t, k)) % 1
        x = int(24 + u * 120); yc0, yc1 = 165 + u * 65, 245 + u * 88
        y = int(yc0 + (yc1 - yc0) * (.5 + .45 * math.sin(2 * math.pi * v0 + ph + 2 * math.pi * cyc(t, 1))))
        if 0 <= y < H0 and 24 <= x < 246 and BEAM[y, x] > 0:
            lit[y, x] = lit[y, x] * .4 + np.array([255, 235, 200]) * .6 * (.6 + .4 * e)
    lit = quantise(lit)
    big = up(lit, K)
    return big.tobytes() if raw else Image.fromarray(big)


PAL_N = cr.PAL_ARR
PAL_SQ = (PAL_N ** 2).sum(1)


def quantise(lit):
    """Ordered-dither the lit frame onto the 48-colour master palette."""
    x = np.clip(lit + (BAY[..., None] - .5) * 9, 0, 255).reshape(-1, 3)
    d = PAL_SQ[None] - 2 * x @ PAL_N.T
    return PAL_N[d.argmin(1)].reshape(H0, W0, 3).astype(np.uint8)


# ------------------------------------------------------------------ audio (all periodic: FFT-filtered noise, integer cycles)
def band(x, lo, hi):
    f = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / sfx.SR)
    f[(fr < lo) | (fr > hi)] = 0
    return np.fft.irfft(f, len(x))


def build_audio(path):
    SR = sfx.SR; n = int(SR * DUR); t = np.arange(n) / SR
    rng = np.random.default_rng(21)
    def unit(x): return x / (np.abs(x).max() + 1e-9)
    def add(buf, sig, at, vol):
        i = int(at * SR) % n; idx = (np.arange(len(sig)) + i) % n
        np.add.at(buf, idx, sig * vol)
    L = np.zeros(n); Rr = np.zeros(n)
    room = unit(band(rng.standard_normal(n), 25, 260)) * .10 + unit(band(rng.standard_normal(n), 260, 1500)) * .02
    steer = .55 * np.sin(2 * np.pi * 6 * t / DUR) + .25 * np.sin(2 * np.pi * 15 * t / DUR + 1)
    f0 = 64 + 10 * np.sin(2 * np.pi * 6 * t / DUR) + 4 * np.sin(2 * np.pi * 15 * t / DUR)   # mean 64 Hz * 15 s = whole cycles
    ph = 2 * np.pi * np.cumsum(f0) / SR
    eng = sum(np.sin(h * ph) / h for h in range(1, 7))
    eng = unit(band(eng, 40, 900)) * .07
    tyre = unit(band(rng.standard_normal(n), 120, 520)) * (.035 + .015 * np.abs(steer))
    rain = unit(band(rng.standard_normal(n), 2500, 9000)) * .012
    tap = np.zeros(n)
    for _ in range(int(DUR * 9)):
        d = int(SR * .012); s = rng.standard_normal(d) * np.exp(-np.arange(d) / SR * 400)
        add(tap, s, rng.random() * DUR, .08 + .1 * rng.random())
    tap = band(tap, 1500, 9000)
    purr = np.zeros(n)
    pd = 3.2; tp = np.arange(int(SR * pd)) / SR
    pr = unit(band(np.random.default_rng(5).standard_normal(len(tp)), 40, 220)) * (.5 + .5 * np.sin(2 * np.pi * 26 * tp)) ** 2
    add(purr, pr * np.sin(np.pi * tp / pd) ** 2, 5.2, .22)
    clicks = np.zeros(n)
    for at in (1.25, 3.75, 6.25, 8.75, 11.25, 13.75):                # paddle shifts
        add(clicks, sfx.click(), at, .10)
    for at in (7.0, 7.12, 7.3):                                      # buttons on the wheel
        add(clicks, sfx.click(), at, .05)
    mid = room + eng + tyre + clicks + purr
    L, Rr = mid + rain * 1.4 + tap * 1.3, mid + rain * .7 + tap * .6  # window is on the left
    st = np.stack([L, Rr], 1)
    st = st / np.abs(st).max() * .5
    import wave
    def write(x):
        with wave.open(path, 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    write(st)
    for _ in range(2):                                               # normalise to -20 LUFS
        r = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        I = float(json.loads(r[r.rindex('{'):r.rindex('}') + 1])['input_i'])
        st = st * 10 ** ((-20 - I) / 20); write(st)
    return I


def loopcheck(mp4):
    def grab(sel):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-vf', f'select={sel},scale=108:192:flags=area,format=gray',
                              '-vsync', '0', '-frames:v', '1', '-f', 'rawvideo', '-'], capture_output=True).stdout
        return np.frombuffer(raw, np.uint8).astype(np.float32)
    nf = int(DUR * FPS)
    first, last = grab('eq(n\\,0)'), grab(f'eq(n\\,{nf - 1})')
    def small(img): return np.asarray(Image.fromarray(np.asarray(img)).convert('L').resize((108, 192), Image.BOX), np.float32)
    seam = np.abs(small(frame(nf, raw=False)) - small(frame(0, raw=False))).mean()
    print(f'last-vs-first (mp4, 108x192 grey): {np.abs(last - first).mean():.3f}')
    print(f'frame at t=15.000 (1/60 s after the last) vs frame 0: {seam:.3f}')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[3:]:
            frame(int(round(float(ts) * FPS)), raw=False).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        out = sys.argv[2]
        print('audio -20 LUFS, measured before last gain:', build_audio('mix.wav'))
        nf = int(DUR * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-i', 'mix.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow',
                               '-crf', '17', '-pix_fmt', 'yuv420p', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '192k',
                               '-movflags', '+faststart', '-t', str(DUR), out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(nf), chunksize=8)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{nf}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
    elif mode == 'loopcheck':
        loopcheck(sys.argv[2])
