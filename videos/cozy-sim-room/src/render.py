"""cozy-sim-room: 15 s seamless ambient loop, no voice, no captions (v2: reference-style soft light, big furniture).

Oblique top-down bedroom at night: sim-racing desk with three screens, gamer in a red hoodie on a wheel,
sleeping cat, bed with a plush, window with the city. 180x320 native -> 6x nearest -> 1080x1920, 60 fps,
light drawn as smooth full-res falloff over the crisp pixels.
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
from ambient import paste, vgrad, up                 # noqa: E402
import cozyroom as cr                                             # noqa: E402

W0, H0, K = 180, 320, 6          # 6x: finer than the reference's ~8x pixels, objects large like the reference
W, H = W0 * K, H0 * K
FPS = 60
DUR = 15.0
P = cr.PAL


def cyc(t, k): return (t * k / DUR) % 1.0
def sn(t, k, ph=0.0): return math.sin(2 * math.pi * k * t / DUR + ph)
def col(c): return np.array(P[c], np.float32)


def R(a, x0, y0, x1, y1, c): a[y0:y1 + 1, x0:x1 + 1] = P[c]


def dith(a, x0, y0, x1, y1, c, lvl=.5):
    """Flat tonal mix toward colour c (soft painterly shading, no checkerboard)."""
    a[y0:y1 + 1, x0:x1 + 1] = a[y0:y1 + 1, x0:x1 + 1] * (1 - lvl) + col(c) * lvl


def shade(a, spr, x, y, dx=2, dy=2, k=.55):
    """Soft drop shadow from a sprite's alpha: full at (dx,dy), lighter at (dx+1,dy+1)."""
    m = spr[..., 3] > 0
    for ox, oy, kk in ((dx, dy, k), (dx + 1, dy + 1, k ** .5)):
        ys, xs = np.nonzero(m)
        ys, xs = ys + y + oy, xs + x + ox
        ok = (ys >= 0) & (ys < H0) & (xs >= 0) & (xs < W0)
        ys, xs = ys[ok], xs[ok]
        a[ys, xs] *= kk


def prop(name): return cr.prop(name, outline=None)


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
FLOOR = (14, 52, 164, 306)
WIN = (5, 114, 12, 194)          # window glass on the left wall face
SCR = {'chart': (30, 33, 30, 14), 'race': (70, 30, 40, 18), 'garage': (120, 33, 30, 14)}   # x, y, w, h


def build_static():
    a = np.zeros((H0, W0, 3), np.float32); a[:] = P['1']
    em = np.zeros((H0, W0), np.float32)
    dith(a, 0, 0, W0 - 1, H0 - 1, 'z', .35)                           # dark teal-green surroundings
    # walls: caps, back wall face, side wall faces
    R(a, 2, 2, 177, 7, '2'); R(a, 2, 7, 177, 7, '4')
    R(a, 14, 8, 164, 51, '3')
    for x in range(17, 164, 7): R(a, x, 10, x, 47, '2')
    dith(a, 14, 8, 164, 16, '2', .5)
    R(a, 14, 8, 164, 8, '4'); R(a, 14, 48, 164, 51, '2'); R(a, 14, 48, 164, 48, '4')
    for (x0, x1) in ((3, 13), (165, 177)):
        R(a, x0, 8, x1, 312, '2'); dith(a, x0, 8, x1, 312, '1', .3); R(a, x0, 8, x1, 8, '3')
    R(a, 13, 8, 13, 312, '1'); R(a, 165, 8, 165, 312, '1')
    R(a, 12, 52, 12, 306, '3'); R(a, 166, 52, 166, 306, '3')
    # floor planks
    x0, y0, x1, y1 = FLOOR
    R(a, x0, y0, x1, y1, '4')
    rng = np.random.default_rng(4)
    for i, x in enumerate(range(x0, x1 + 1, 8)):
        R(a, x, y0, x, y1, '3')
        if i % 3 == 1: dith(a, x + 1, y0, min(x + 7, x1), y1, '3', .45)
        elif i % 3 == 2: dith(a, x + 1, y0, min(x + 7, x1), y1, '5', .2)
        for yy in range(y0 + int(rng.integers(8, 40)), y1, int(rng.integers(36, 60))):
            R(a, x + 1, yy, min(x + 7, x1), yy, '3')
    dith(a, x0, y0, x1, y1, 'z', .22)                                 # green cast of the reference floor
    for d, lv in ((0, .7), (1, .45), (2, .25), (3, .1)):
        dith(a, x0 + d, y0, x0 + d, y1, '2', lv); dith(a, x1 - d, y0, x1 - d, y1, '2', lv); dith(a, x0, y0 + d, x1, y0 + d, '2', lv)
    R(a, 2, 307, 177, 319, '1'); R(a, 2, 307, 177, 307, '3')
    R(a, 22, 305, 62, 309, '5'); R(a, 22, 305, 62, 305, '6')
    # rug (big, under the cat)
    R(a, 18, 126, 100, 202, 'b'); R(a, 20, 128, 98, 200, 'c'); R(a, 23, 131, 95, 197, 'b')
    R(a, 23, 131, 95, 197, 'L'); dith(a, 23, 131, 95, 197, 'b', .45)
    for xx in range(24, 95, 4): a[133, xx] = P['L']; a[195, xx] = P['L']
    for yy in range(127, 202, 2): a[yy, 16] = P['F']; a[yy, 102] = P['F']
    # doormat with an original wave pattern
    R(a, 22, 280, 62, 298, 'l'); R(a, 24, 282, 60, 296, 'm')
    for xx in range(26, 59):
        a[285 + int(round(1.5 * math.sin(xx * .6))), xx] = P['o']; a[292 + int(round(1.5 * math.sin(xx * .6 + 3))), xx] = P['o']
    # back wall: photo, console shelf with LED
    R(a, 158, 10, 162, 18, 'G'); R(a, 159, 11, 164, 17, 'h'); R(a, 159, 15, 164, 17, 'A'); a[12, 162] = P['q']
    shelf, _ = cr.console_shelf(140)
    shade(a, shelf, 16, 6, 0, 3, .6); paste(a, shelf, 16, 6)
    # monitors
    for name, (sx, sy, sw, sh) in SCR.items():
        m = cr.monitor(sw, sh); shade(a, m, sx - 3, sy - 3, 1, 3, .5); paste(a, m, sx - 3, sy - 3)
        em[sy:sy + sh, sx:sx + sw] = 1
    # desk (top + front face, purple rim on the lip)
    R(a, 16, 52, 162, 72, 'b'); dith(a, 16, 52, 162, 72, '3', .45)
    for yy in (58, 66): dith(a, 16, yy, 162, yy, '2', .4)
    R(a, 16, 73, 162, 73, 'd'); R(a, 16, 74, 162, 78, '2'); R(a, 16, 78, 162, 78, '1'); R(a, 16, 52, 162, 52, '2')
    for d, lv in ((0, .7), (1, .45), (2, .2)): dith(a, 16, 79 + d, 162, 79 + d, '1', lv)
    # under-desk fronts: drawer unit, PC tower
    R(a, 18, 79, 38, 94, '3'); R(a, 18, 79, 38, 79, '5'); R(a, 18, 86, 38, 86, '2'); R(a, 26, 82, 30, 83, 'F'); R(a, 26, 89, 30, 90, 'F')
    shade(a, np.ones((22, 19, 4), np.float32), 144, 79, 2, 3, .6)
    R(a, 144, 79, 162, 100, '1'); R(a, 145, 80, 161, 99, '2'); R(a, 144, 79, 162, 79, '4')
    # desk items
    for name, x, y in (('lamp', 18, 53), ('keyboard', 28, 61), ('mouse', 49, 62), ('notes', 54, 54), ('figure', 62, 54),
                       ('cases', 44, 53), ('phone', 113, 62), ('headphones', 138, 60), ('can', 154, 54), ('remote', 104, 63),
                       ('drink', 150, 64), ('books', 20, 64)):
        place(a, prop(name), x, y)
    R(a, 82, 64, 98, 68, '2'); R(a, 82, 64, 98, 64, '5')            # wheel base clamp
    place(a, cr.mug(), 126, 53)
    # left wall: plate, key hook; window frame + sill
    R(a, 5, 60, 12, 65, 'G'); R(a, 6, 61, 11, 64, 'k'); R(a, 7, 62, 10, 63, 'i')
    R(a, 5, 262, 11, 263, 'E'); a[264, 6] = P['p']; a[265, 6] = P['p']
    R(a, 3, 110, 13, 198, '5'); R(a, 3, 110, 13, 110, '7'); R(a, 4, 111, 13, 197, '4')
    em[WIN[1]:WIN[3] + 1, WIN[0]:WIN[2] + 1] = 1
    R(a, 3, 198, 14, 200, '6')
    # right wall: posters
    for kind, y in (('track', 58), ('sunset', 132), ('blue', 222)):
        pst = cr.poster(kind); shade(a, pst, 166, y, 1, 2, .6); paste(a, pst, 166, y)
    # bed (big, head at the top, against the right wall)
    shade(a, np.ones((112, 60, 4), np.float32), 106, 104, 3, 4, .5)
    R(a, 106, 104, 163, 216, 'm'); R(a, 106, 104, 163, 107, 'n'); R(a, 106, 104, 163, 104, 'o')
    R(a, 108, 108, 162, 213, 'G'); dith(a, 108, 108, 162, 213, 'F', .25)
    for (px, pw) in ((111, 25), (139, 24)):                          # pillows
        R(a, px, 111, px + pw, 128, 'H'); R(a, px, 126, px + pw, 128, 'G'); R(a, px, 111, px + pw, 111, 'G')
        dith(a, px + 2, 119, px + pw - 2, 125, 'G', .35)
    for xx in range(108, 163):                                       # messy blanket
        top = 146 + int(round(4 * math.sin(xx * .19) + 2 * math.sin(xx * .57)))
        R(a, xx, top, xx, 212, 'g'); a[top, xx] = P['i']; a[top + 1, xx] = P['h']; a[top + 2, xx] = P['h']
    for fx in (118, 131, 147, 159):
        for yy in range(154, 211):
            xx = fx + int(round(2 * math.sin(yy * .1 + fx)))
            if 108 <= xx < 163: a[yy, xx] = P['a']; a[yy, xx - 1] = P['h']
    dith(a, 108, 140, 162, 212, 'b', .3)
    for k in range(12): R(a, 108, 204 - k, 108 + 11 - k, 204 - k, 'G')
    R(a, 106, 216, 163, 219, 'l')
    place(a, cr.plush(), 114, 112)
    place(a, prop('cap'), 150, 165); place(a, prop('remote'), 128, 186); place(a, prop('phone'), 146, 152)
    # furniture: dresser, low bookshelf, shoe rack, beanbag, toy race track, cushion, open box
    box(a, 14, 218, 36, 240, 6, '5', '3', '7')
    R(a, 16, 243, 34, 243, '2'); R(a, 23, 242, 27, 242, 'F')
    box(a, 148, 232, 163, 282, 6, 'n', 'm', 'o')
    for yy in range(235, 280, 11):
        for k, c in enumerate('vjqAiwMp'):
            if 149 + k * 2 < 162: R(a, 149 + k * 2, yy, 150 + k * 2, yy + 7, c)
        R(a, 149, yy + 9, 162, yy + 9, 'l')
    box(a, 70, 296, 104, 301, 3, '6', '4', '7')
    place(a, blob(30, 22, 'cdef'), 40, 210)
    track(a, 62, 240, 54, 26)
    place(a, blob(22, 14, 'ghij'), 96, 272)
    place(a, prop('box'), 120, 252); R(a, 122, 253, 132, 255, 'l'); place(a, prop('tyre'), 124, 248, shadow=False)
    for name, x, y in (
        ('bin', 42, 86), ('paper', 50, 92), ('paper', 38, 98), ('paper', 56, 100), ('can', 114, 94), ('plant', 124, 86),
        ('controller', 66, 184), ('yarn', 86, 176), ('car_red', 78, 140), ('car_blue', 24, 184), ('bowl', 20, 206), ('bowl2', 28, 207),
        ('snack', 86, 204), ('drink', 102, 210), ('chips', 98, 222),
        ('lamp', 16, 211), ('plant', 27, 210), ('hoodie', 46, 208), ('tee', 72, 216), ('sock', 60, 230),
        ('tyre', 15, 250), ('toolbox', 24, 256), ('cone', 40, 254), ('helmet', 14, 268), ('flag', 30, 270),
        ('car_yel', 66, 244), ('car_red', 104, 254),
        ('basket', 120, 222), ('jeans', 134, 226), ('sock', 112, 232),
        ('car_blue', 150, 224), ('figure', 160, 226),
        ('trainer', 72, 288), ('trainer', 82, 289), ('trainer', 92, 287), ('slipper', 108, 292), ('umbrella', 5, 282),
        ('backpack', 42, 268), ('skate', 116, 266), ('bottle', 58, 272), ('hoodie', 74, 268), ('cases', 54, 252)):
        place(a, prop(name), x, y)
    for bx, by in ((120, 290), (135, 290), (150, 290), (127, 281), (142, 281)):
        place(a, prop('box'), bx, by)
    place(a, prop('pizza'), 135, 275)
    return a, em


STATIC, EMIS = build_static()

GLYPH = {
    '@': [".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###.", "....."],
    'y': [".....", ".....", "#...#", "#...#", "#...#", ".####", "....#", ".###."],
    'u': [".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#", "....."],
    'b': ["#....", "#....", "####.", "#...#", "#...#", "#...#", "####.", "....."],
    '_': [".....", ".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    'c': [".....", ".....", ".###.", "#....", "#....", "#....", ".###.", "....."],
    'a': [".....", ".....", ".###.", "....#", ".####", "#...#", ".####", "....."],
    'r': [".....", ".....", "#.##.", "##..#", "#....", "#....", "#....", "....."],
    's': [".....", ".....", ".####", "#....", ".###.", "....#", "####.", "....."],
}
HANDLE, SH, SIGN_Y = '@yub_cars', 18, 28      # wall strip of SH rows inserted at SIGN_Y; sign lands at 11-14 % height


def build_band():
    b = np.empty((SH, W0, 3), np.float32); b[:] = P['1']
    b[:, 3:13] = P['2']; b[:, 166:178] = P['2']; b[:, 13] = P['1']; b[:, 165] = P['1']
    b[:, 14:165] = P['3']
    for x in range(17, 165, 7): b[:, x] = P['2']
    em = np.zeros((SH, W0), np.float32)
    w = len(HANDLE) * 6 - 1; x0 = 76 - w // 2
    b[5:SH, x0 - 3:x0 + w + 3] = P['a']; b[5, x0 - 3:x0 + w + 3] = P['b']      # dark acrylic backing
    for i, ch in enumerate(HANDLE):
        for yy, row in enumerate(GLYPH[ch]):
            for xx, c in enumerate(row):
                if c == '#': b[7 + yy, x0 + i * 6 + xx] = P['N']; em[7 + yy, x0 + i * 6 + xx] = 1
    return b, em


BAND, BAND_EM = build_band()


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
    def limb(self, p0, p1, core, edge, hi, sleeve=0):
        n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
        pts = [(p0[0] + (p1[0] - p0[0]) * k / max(1, n - 1), p0[1] + (p1[1] - p0[1]) * k / max(1, n - 1)) for k in range(n)]
        for i, (x, y) in enumerate(pts): self.rect(int(round(x)) - 2, int(round(y)) - 1, int(round(x)) + 1, int(round(y)) + 1, 'G' if i < sleeve else edge)
        for i, (x, y) in enumerate(pts): self.rect(int(round(x)) - 1, int(round(y)) - 1, int(round(x)), int(round(y)), 'H' if i < sleeve else core)
        for (x, y) in pts[sleeve::2]: self.put(x - 1, y - 1, hi)


# The main guy (characters/main-guy): dark messy hair with two cowlicks, silver square glasses, brown skin, white tee.
BACK = ["....l...l.....", "...ll..ll.....", "..llllllllll..", ".llmllllmllll.", ".llllmllllmll.", "llllllllllllll",
        "FlllllmllllllF", "yFllllllllllFy", "xllllllllllllx", ".llllllllllll.", "..llllllllll..", "...lyyyyyyl...",
        "....xyyyyx....", "..GHHHHHHHHG.."]
SIDE = ["....l...l.....", "...ll..ll.....", "..llllllllll..", ".llmllllmlly..", ".llllllllyyy..", "llllllllyyyyy.",
        "lyFFFFFGGGGy..", "lxlllllGH0Gy..", "lllllllFFFFyy.", ".lllllllyyyyy.", "..llllllyywy..", "...lyyyyyty...",
        "....xyyyyx....", "..GHHHHHHHHG.."]
FACE = ["....l...l.....", "...ll..ll.....", "..llllllllll..", ".llmllllllmll.", ".llllllllllll.", "llyllyyyyllyll",
        "lyyyyyyyyyyyyl", "yGGGGGyyGGGGGy", "xGH0yGGGGH0yGx", "xFFFFFyyFFFFFx", "yywyyyyyyyywyy", ".yyytyyyytyyy.",
        "..yyyttttyyy..", "...yyyyyyyy...", "....xyyyyx....", "..GHHHHHHHHG.."]
FACE_OPEN = FACE[:12] + ["..yyytsstyyy.."] + FACE[13:]
FACE_BLINK = FACE[:8] + ["xGyyyGGGGyyyGx", "xFF0FFyyFF0FFx"] + FACE[10:]
TURN = (6.0, 9.6)                # swivels round at 6.0 s, waves, back on the wheel by 9.6 s


def shoulders(g, cx, cy, rx=15.0):
    for y in range(int(cy - 6), int(cy + 7)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / 5.5) ** 2
            if d <= 1: g.put(x, y, 'F' if d > .82 else ('G' if d > .55 or y > cy + 2 else 'H'))


def wheel(g, ang):
    for k in range(48):
        th = 2 * math.pi * k / 48
        for rr, c0 in ((11, 'F'), (10, 'E')):
            g.put(135 + rr * math.cos(th), 105 + rr * .38 * math.sin(th), c0 if math.sin(th) < 0 else 'D')
    for th in (ang, ang + math.pi, ang + math.pi / 2):
        for r in range(1, 10): g.put(135 + r * math.cos(th), 105 + r * .38 * math.sin(th), 'D')
    g.rect(133, 104, 137, 106, '1'); g.put(135 + 10.5 * math.cos(ang - math.pi / 2), 105 + 4 * math.sin(ang - math.pi / 2), 'v')


def gamer(t):
    steer = .55 * sn(t, 6) + .25 * sn(t, 15, 1.0)
    hx = int(round(1.2 * sn(t, 4) + steer * 1.4))
    cx = int(round(.8 * sn(t, 2, .5)))
    turned = TURN[0] + .2 <= t < TURN[1] - .2
    side = TURN[0] <= t < TURN[1] and not turned
    g = CG()
    g.rect(124, 113, 146, 118, '2'); g.rect(124, 113, 146, 113, '3')            # pedal set
    for px in (126, 133, 141): g.rect(px, 114, px + 2, 116, '5')
    if turned:                                                                   # facing the camera, waving
        wheel(g, 0.0)
        g.stamp(cr.CHAIR[:15], 125, 104)                                         # backrest now behind him
        g.stamp(cr.CHAIR[15:], 125, 136)
        g.rect(127, 128, 143, 135, 'H'); g.rect(127, 133, 143, 135, 'G')         # white tee
        shoulders(g, 135, 125)
        g.rect(127, 135, 143, 140, 'D'); g.rect(127, 135, 143, 135, '2')         # black jeans, knees toward us
        for lx in (130, 140):
            g.rect(lx - 2, 140, lx + 2, 145, 'D'); g.rect(lx - 2, 140, lx - 2, 145, 'E')
            g.rect(lx - 3, 146, lx + 2, 148, 'H'); g.rect(lx - 3, 148, lx + 2, 148, 'G')
        g.limb((122, 124), (128, 136), 'y', 'x', 'y', sleeve=4); g.rect(127, 135, 129, 137, 'y')
        waving = 6.55 <= t < 8.95
        blink = 8.2 <= t < 8.3
        g.stamp(FACE_BLINK if blink else (FACE_OPEN if waving else FACE), 128, 109)
        if waving:
            w = int((t - 6.55) / .2) % 2
            g.limb((148, 124), (154, 118), 'y', 'x', 'y', sleeve=4)
            g.limb((154, 118), (155 + 3 * w, 108 - w), 'y', 'x', 'y')
            hxp, hyp = 155 + 3 * w, 107 - w
            g.rect(hxp - 1, hyp - 2, hxp + 1, hyp + 1, 'y'); g.put(hxp - 1, hyp - 3, 'y'); g.put(hxp + 1, hyp - 3, 'y')
        else:
            g.limb((148, 124), (142, 136), 'y', 'x', 'y', sleeve=4); g.rect(141, 135, 143, 137, 'y')
        return cr.S([''.join(r) for r in g.g], outline='1')
    press = 1 if sn(t, 12) > .3 else 0
    for lx in (130, 139):                                                        # legs under the desk
        g.rect(lx - 2, 117, lx + 2, 124, 'D'); g.rect(lx - 1, 117, lx - 1, 124, 'E')
        g.rect(lx - 2, 114 + (press if lx > 135 else 0), lx + 2, 116 + (press if lx > 135 else 0), 'H')
    shoulders(g, 135 + hx * .5, 124.5)
    g.stamp([r.replace('v', 'e').replace('u', 'd') for r in cr.CHAIR], 125 + cx, 126)
    ang = steer * .9
    wheel(g, ang)
    if not side:
        hands = [(135 + 11 * math.cos(math.pi + ang), 105 + 4.2 * math.sin(math.pi + ang)),
                 (135 + 11 * math.cos(ang), 105 + 4.2 * math.sin(ang))]
        for (sx, sy), (hxp, hyp) in zip(((122 + hx * .5, 122), (148 + hx * .5, 122)), hands):
            g.limb((sx, sy), (hxp, hyp + 2), 'y', 'x', 'y', sleeve=4)
            g.rect(int(round(hxp)) - 1, int(round(hyp)) - 1, int(round(hxp)) + 1, int(round(hyp)) + 1, 'y')
            g.put(hxp - 1, hyp - 1, 'x')
    g.stamp(SIDE if side else BACK, 128 + hx, 106)
    return cr.S([''.join(r) for r in g.g], outline='1')


# ------------------------------------------------------------------ screens
def race(t, w, h):
    """Pixel racing game: road scrolls toward the viewer, kerbs, curve sway, player car."""
    s = np.zeros((h, w, 3), np.float32)
    hz = h // 3
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
    s[:4] = P['D']; s[4:] = P['E']
    for y in range(4, h):
        for x in range(w):
            if ((x - w / 2) / (w * .43)) ** 2 + ((y - h * .62) / (h * .34)) ** 2 <= 1: s[y, x] = P['F']
    th = 2 * math.pi * cyc(t, 1)
    c, sn_ = math.cos(th), math.sin(th)
    ch, cw = GCAR_RGBA.shape[:2]
    for y in range(h):
        for x in range(w):
            u, v = (x - w / 2) * 1.5, (y - h * .62) * 3.0            # ellipse floor: squash y by 2
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
LIGHTS = [(int(SKYR.integers(top + 2, WH - 2)), int(SKYR.integers(bx, min(WW, bx + bw))), str(SKYR.choice(list('qpjr'))), int(SKYR.integers(1, 9)))
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
    for y in range(104, 111): R(a, 2, y, 14, y, 'c' if y % 3 else 'b')
    for y in range(111, 206):
        sway = 1.4 * sn(t, 2) * (y - 111) / 95 + .5 * sn(t, 5, y * .05)
        x0 = 9 + int(round(sway))
        for x in range(x0, min(22, x0 + 5 + (y - 111) // 24)):
            a[y, x] = P['d' if (x - x0) % 3 == 0 else ('c' if (x - x0) % 3 == 1 else 'b')]
        a[y, x0] = P['e']                                             # rim light from the window


BEAM = np.zeros((H0, W0), np.float32)
for y in range(H0):
    for x in range(14, 165):
        u = (x - 14) / 105                                             # along the shaft, down-right
        if u > 1: continue
        yc0, yc1 = 112 + u * 60, 198 + u * 90
        if yc0 <= y <= yc1: BEAM[y, x] = (1 - u) ** 1.3 * (1 - .4 * abs((y - (yc0 + yc1) / 2) / ((yc1 - yc0) / 2)))

def blur(x, r):
    """Separable box blur (edge-clamped), run twice for a near-gaussian falloff."""
    for _ in range(2):
        for ax in (0, 1):
            pad = [(0, 0)] * x.ndim; pad[ax] = (r + 1, r)
            c = np.cumsum(np.pad(x, pad, mode='edge'), axis=ax)
            x = (np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)
    return x


def smooth_up(x):
    """Bilinear upscale of a light map to full res, so light falls off smoothly over crisp pixels."""
    return np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(x[..., i]), 'F').resize((W, H), Image.BILINEAR))
                     for i in range(x.shape[2])], -1)


BEAM = blur(BEAM, 4)
BEAM_S = np.concatenate([BEAM[:SIGN_Y], np.zeros((SH, W0), np.float32), BEAM[SIGN_Y:H0 - SH]])
YY, XX = np.mgrid[0:H0, 0:W0].astype(np.float32)
VIG = smooth_up(np.repeat((1 - .45 * np.clip((np.hypot((XX - W0 / 2) / W0, (YY - H0 / 2) / H0 * .8) - .25) / .4, 0, 1)
                           ** 1.5)[..., None], 1, 2))


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
    a[26:28, 18:156] = lc; em[26:28, 18:156] = 1
    # window + curtain
    a[WIN[1]:WIN[3] + 1, WIN[0]:WIN[2] + 1] = window(t)
    curtain(a, t)
    # lamp bulb, PC fans, phone, fairy lights
    a[55, 20:23] = P['r']; a[54, 21] = P['r']; em[54:56, 20:23] = 1
    hue = [col('M'), col('e'), col('j'), col('J')]
    for i, fy in enumerate((85, 94)):
        c = hue[int(cyc(t, 3) * 4 + i) % 4]
        for k in range(10):
            th = 2 * math.pi * k / 10 + 2 * math.pi * cyc(t, 30)
            xx, yy = int(round(153 + 3 * math.cos(th))), int(round(fy + 3 * math.sin(th)))
            a[yy, xx] = c if k % 3 else col('H'); em[yy, xx] = 1
    if 5.0 <= t < 6.5: a[64:67, 115:118] = P['k']; em[64:67, 115:118] = 1
    for i in range(12):
        fx = 170 + int(round(6 * i / 11)); fy = 92 + i * 9 + int(2 * math.sin(i * 1.3))
        on = sn(t, (i % 4) + 2, i) > -.3
        a[fy, fx] = P[('q', 'N', 'K')[i % 3]] if on else P['D']; em[fy, fx] = on
    # mug steam
    for i in range(5):
        p = cyc(t + i * DUR / 30, 6)
        sx = 129 + int(round(1.5 * math.sin(p * 8 + i)))
        sy = 52 - int(p * 14)
        if p < .85: a[sy, sx] = a[sy, sx] * (.35 + .5 * p) + col('G') * (.65 - .5 * p)
    # cat (breathing every 2.5 s, tail flicks twice per loop)
    flick = 1 if 3.0 <= t < 3.35 else (-1 if 9.2 <= t < 9.55 else 0)
    c = cr.cat(breath=cyc(t, 6), flick=flick)
    place(a, c, 46, 152)
    # gamer
    gm = gamer(t)
    shade(a, gm, GX - 45, GY - 33, 2, 3, .6); paste(a, gm, GX - 45, GY - 33)

    a = np.concatenate([a[:SIGN_Y], BAND, a[SIGN_Y:H0 - SH]]); em = np.concatenate([em[:SIGN_Y], BAND_EM, em[SIGN_Y:H0 - SH]])
    a[H0 - 3:] = P['1']; em[H0 - 3:] = 0                                            # bottom wall cap
    # ---- light (reference look): muted teal grade, smooth full-res light falloff, bloom on light sources
    m = em > 0
    lum = a.mean(-1, keepdims=True)
    base = a * .6 + lum * np.array([.30, .42, .40], np.float32)
    base[m] = a[m]
    amb = np.array([.5, .6, .72], np.float32) * (1 - e) + np.array([.66, .58, .54], np.float32) * e
    Lm = np.empty((H0, W0, 3), np.float32); Lm[:] = amb
    add = np.empty((H0, W0, 3), np.float32); add[:] = (16, 26, 24)       # room haze
    flick_s = 1 + .05 * sn(t, 30)
    wc = np.array([110, 150, 235], np.float32) * (1 - e) + np.array([255, 185, 110], np.float32) * e

    def light(cx, cy, r, c, k, ry=None, haze=10):
        d = np.sqrt(((XX - cx) / r) ** 2 + ((YY - cy) / (ry or r)) ** 2)
        v = (np.clip(1 - d, 0, 1) ** 2 * k)[..., None] * (np.asarray(c, np.float32) / 255)
        Lm[...] += v; add[...] += v * haze
    light(90, 48 + SH, 110, (200, 95, 255), 1.45 * flick_s, ry=70, haze=30)             # desk + screens, purple neon wash
    light(90, 27, 105, lc, .5 + .15 * led, ry=26)                                    # LED strip
    light(90, 82 + SH, 34, (110, 165, 255), .4 * flick_s, ry=24)                          # screen spill on the gamer
    light(8, 155 + SH, 72, wc, .5 + .3 * e, ry=90)                                        # window
    light(22, 56 + SH, 30, (255, 190, 110), .85, haze=18)
    light(76, 40, 50, (255, 120, 200), .55 * flick_s, ry=22, haze=20)                # @yub_cars neon                                 # desk lamp
    light(153, 90 + SH, 22, hue[int(cyc(t, 3) * 4) % 4], .6)                              # PC fans
    light(130, 56 + SH, 12, (255, 210, 150), .25)                                         # mug
    bc = wc * .6 + np.array([150, 200, 170], np.float32) * .4                     # greenish shaft like the reference
    Lm += BEAM_S[..., None] * (.45 + .35 * e) * bc / 255
    add += BEAM_S[..., None] * (26 + 14 * e) * bc / 255
    for (u0, v0, k, ph) in MOTES:                                                    # dust in the window shaft
        u = (u0 + cyc(t, k)) % 1
        x = int(14 + u * 90); yc0, yc1 = 116 + u * 43, 194 + u * 62
        y = int(yc0 + (yc1 - yc0) * (.5 + .45 * math.sin(2 * math.pi * v0 + ph + 2 * math.pi * cyc(t, 1))))
        y += SH
        if 0 <= y < H0 and 14 <= x < 164 and BEAM_S[y, x] > .05:
            add[y, x] += np.array([255, 235, 200]) * (.5 + .3 * e)
    Lm[m] = .95 + .05 * flick_s; add[m] = 0
    bloom = blur(base * m[..., None] * (.85 + .15 * flick_s), 3)
    out = up(base, K) * smooth_up(Lm) + smooth_up(add + bloom * .9)
    big = np.clip(out * VIG, 0, 255).astype(np.uint8)
    return big.tobytes() if raw else Image.fromarray(big)


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
    for at in (1.25, 3.75, 11.25, 13.75):                            # paddle shifts
        add(clicks, sfx.click(), at, .10)
    for at in (6.0, 9.4):                                            # chair swivel
        add(clicks, sfx.creak(), at, .12)
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
