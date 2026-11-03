"""Original pixel-art car journey: neon rain city -> desert sunset -> snowy forest -> coast.
Usage: python render.py video OUT.mp4 | python render.py still OUTDIR t1 t2 ..."""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image

W = H = 135; S = 8; FPS = 30; DUR = 16.0; SR = 44100
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
YS, XS = np.mgrid[0:H, 0:W]


def hx(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
def col(c): return hx(c) if isinstance(c, str) else np.asarray(c, np.float32)


class C:
    def __init__(s, layer=False):
        s.a = np.zeros((H, W, 3), np.float32); s.m = np.zeros((H, W), bool) if layer else None
    def rect(s, x, y, w, h, c):
        x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h))
        if x1 > x0 and y1 > y0:
            s.a[y0:y1, x0:x1] = col(c)
            if s.m is not None: s.m[y0:y1, x0:x1] = True
    def px(s, x, y, c): s.rect(round(x), round(y), 1, 1, c)
    def line(s, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n; s.px(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, c)
    def grad(s, y0, y1, cols, x0=0, x1=W):
        cs = np.stack([col(c) for c in cols]); n = len(cols) - 1
        ys, xs = YS[y0:y1, x0:x1], XS[y0:y1, x0:x1]
        t = (ys - y0) / max(1, y1 - y0 - 1) * n + BAYER[ys % 4, xs % 4] - .5
        s.a[y0:y1, x0:x1] = cs[np.clip(np.round(t), 0, n).astype(int)]
    def glow(s, cx, cy, r, c, k=.55, ry=None):
        ry = ry or r
        d = np.sqrt(((XS - cx) / r) ** 2 + ((YS - cy) / ry) ** 2)
        lv = np.clip(np.floor((1 - d) * 3 + BAYER[YS % 4, XS % 4]), 0, 3) / 3 * k
        s.a[:] = s.a * (1 - lv[..., None]) + col(c) * lv[..., None]
    def spr(s, x, y, rows, pal, flip=False):
        for j, r in enumerate(rows):
            if flip: r = r[::-1]
            for i, ch in enumerate(r):
                if ch in pal: s.px(x + i, y + j, pal[ch])


def light(L, mul, rims, dark=1.0):
    """Tint a character layer, add 1px rim lights: rims = [(side, colour, strength)]."""
    a = L.a * np.array(mul, np.float32) * dark; m = L.m
    for side, c, k in rims:
        edge = m & ~np.roll(m, side, axis=1)
        a[edge] = a[edge] * (1 - k) + col(c) * k
    return a


def comp(bg, L, a):
    bg.a[L.m] = a[L.m]


def P(**kw): return {k: hx(v) for k, v in kw.items()}


rng = np.random.default_rng


# ---------------- the car: original boxy 80s wagon, side view, facing right ----------------
def build_car():
    Wc, Hc = 50, 13
    g = [['.'] * Wc for _ in range(Hc)]
    def put(x, y, ch):
        if 0 <= x < Wc and 0 <= y < Hc: g[y][x] = ch
    # greenhouse (rows 0-5): long wagon roof, raked windscreen at the front
    for r in range(6):
        x0, x1 = 6 - (r > 3), 33 + r * 2
        for x in range(x0, x1 + 1): put(x, r, 'R')
        if r == 0: continue
        for x in range(x0 + 1, x1 - 1): put(x, r, 'w')
        for px in (16, 17, 26): put(px, r, 'R')          # B / C pillars
        put(x1 - 1, r, 'R')
    for x in range(7, 33): put(x, 0, 'h')                 # roof highlight
    for r in range(1, 6):                                 # glass sheen diagonals
        put(20 + r, 6 - r, 'W'); put(9 + r, 6 - r, 'W'); put(29 + r, 6 - r, 'W')
    put(36, 4, 'k'); put(37, 4, 'k')                      # roof rack / mirror
    # body (rows 6-12)
    for r in range(6, 13):
        x0 = 1 if r > 6 else 3; x1 = 48 if r > 7 else 46
        for x in range(x0, x1 + 1): put(x, r, 'R')
    for x in range(3, 47): put(x, 6, 'h')
    for x in range(2, 48): put(x, 9, 'T')                 # side trim stripe
    for x in range(1, 49): put(x, 11, 'r')
    for x in range(1, 49): put(x, 12, 'k')
    for r in range(6, 11): put(17, r, 'd'); put(31, r, 'd')
    put(20, 8, 'c'); put(21, 8, 'c'); put(34, 8, 'c'); put(35, 8, 'c')
    put(47, 7, 'Y'); put(48, 7, 'Y'); put(48, 8, 'Y'); put(47, 8, 'y')    # headlight
    put(1, 7, 'L'); put(1, 8, 'L'); put(2, 7, 'L')                         # tail light
    for r in (10, 11): put(49, r, 'c'); put(0, r, 'c')                     # bumpers
    # wheel arches
    for cx in WHEELS:
        for r in range(7, 13):
            for x in range(cx - 7, cx + 8):
                if (x - cx) ** 2 + (r - 13) ** 2 < 36: put(x, r, 'a')
    return ["".join(r) for r in g]


WHEELS = (11, 39)
CAR = None
CARPAL = P(R='#c8503c', h='#ec8a68', r='#8e3430', k='#2a2228', w='#3a5a6a', W='#7aa6b4', T='#f0d8a8',
           d='#8e3430', c='#d8dce0', Y='#fff4c8', y='#e8c070', L='#ff4a4a', a='#151218')


def draw_car(c, x0, y0, t, mul, rim, night):
    global CAR
    CAR = CAR or build_car()
    L = C(layer=True)
    L.spr(x0, y0, CAR, CARPAL)
    for cx in WHEELS:                                    # rotating wheels
        wx, wy = x0 + cx, y0 + 13
        for y in range(-4, 5):
            for x in range(-4, 5):
                d2 = x * x + y * y
                if d2 <= 18: L.px(wx + x, wy + y, '#1c1a20' if d2 > 6 else '#9aa0a8' if d2 > 1 else '#d8dce0')
        a = t * 22
        for k in range(3):
            ang = a + k * 2.094
            L.px(wx + round(math.cos(ang) * 2), wy + round(math.sin(ang) * 2), '#4a4a54')
    a = L.a * np.array(mul, np.float32)
    m = L.m
    for side, cl, k in rim:
        e = m & ~np.roll(m, side, axis=1) if abs(side) == 1 else m & ~np.roll(m, side // 2, axis=0)
        a[e] = a[e] * (1 - k) + col(cl) * k
    if night:   # lights keep full brightness
        for (lx, ly) in ((47, 7), (48, 7), (48, 8)): a[y0 + ly, x0 + lx] = col('#fff8e0')
        for (lx, ly) in ((1, 7), (1, 8), (2, 7)): a[y0 + ly, x0 + lx] = col('#ff5050')
    c.a[m] = a[m]
    return L


# ---------------- helpers ----------------
def hr(k, seed=1):
    return ((k * 73856093) ^ (seed * 19349663) ^ (k * k * 83492791)) % 10007 / 10007


def scroll(off, gap, seed, fn, pad=40):
    """Call fn(x, rand, k) for repeating objects spaced `gap` apart, scrolled by `off`."""
    k0 = int(math.floor((off - pad) / gap))
    for k in range(k0, k0 + int((W + 2 * pad) / gap) + 2):
        fn(k * gap - off, hr(k, seed), k)


def ridge(c, off, y, amp, freq, colr, seed, y1=None, hi=None):
    for x in range(W):
        u = (x + off) * freq
        hh = amp * (.55 * math.sin(u + seed) + .3 * math.sin(u * 2.3 + seed * 3) + .15 * math.sin(u * 5.1))
        top = int(y - hh)
        c.rect(x, top, 1, (y1 or H) - top, colr)
        if hi: c.px(x, top, hi)


def pine(c, x, base, h, body, shade, snow=None):
    w = h * .42
    for j in range(int(h)):
        f = j / h; tier = (j % max(3, int(h / 4))) / max(3, int(h / 4))
        hw = max(.5, w * f * (.75 + .35 * tier))
        y = base - h + j
        c.rect(round(x - hw), y, round(hw), 1, body); c.rect(round(x), y, round(hw), 1, shade)
        if snow and tier < .34 and j > 1: c.rect(round(x - hw), y, max(1, round(hw * 1.2)), 1, snow)
    c.rect(round(x) - 1, base, 2, 2, shade)


V = 95.0                  # road scroll speed px/s
CARX, CARY = 40, 97       # car sprite origin
ROAD0, ROAD1 = 104, 121


# ================= environments =================
def road(c, top_col, cols, dash, s, edge='#d8d0b8', dash_gap=30):
    c.grad(ROAD0, ROAD1, cols)
    c.rect(0, ROAD0, W, 1, top_col)
    scroll(s, dash_gap, 3, lambda x, r, k: c.rect(x, 112, 12, 1, dash))
    c.rect(0, ROAD1 - 1, W, 1, edge)


# ---- 1. neon city in the rain ----
NEON = ['#ff5fa2', '#4fe0e8', '#ffb347', '#9a7bff']
RAIN = np.c_[np.random.default_rng(1).random((110, 3))]


def env_city(t):
    c = C(); s = V * t
    c.grad(0, 80, ['#0a1420', '#0f1e2e', '#162a3c', '#1e3a4c', '#2a4a5a'])
    def far(x, r, k):
        h = 24 + r * 34; w = 12 + int(r * 10)
        c.rect(x, 82 - h, w, h, '#132536')
        for j in range(int(h // 5)):
            for i in range(w // 4):
                if hr(k * 97 + j * 13 + i, 5) > .78: c.px(x + 2 + i * 4, 82 - h + 3 + j * 5, '#c9a660' if hr(k + j, 9) > .4 else '#5d8f98')
    scroll(s * .12, 16, 11, far)
    c.glow(67, 84, 90, '#2f5e70', .3, 12)
    def mid(x, r, k):
        h = 36 + r * 30; w = 26 + int(r * 12)
        c.rect(x, 104 - h, w, h, '#1a2c3a'); c.rect(x + w - 3, 104 - h, 3, h, '#142430')
        for j in range(int(h // 6) - 1):
            for i in range(w // 6):
                if hr(k * 31 + j * 7 + i, 4) > .6: c.rect(x + 3 + i * 6, 104 - h + 4 + j * 6, 3, 2, '#e8c47a' if hr(k + i, 2) > .5 else '#3a5868')
        if r > .35:   # neon sign
            nc = NEON[k % 4]; on = not (r > .8 and math.sin(t * 13 + k) > .7)
            sx, sy = x + 4, 104 - h + 6 + int(r * 10)
            c.rect(sx - 1, sy - 1, 14, 7, '#0e1820')
            if on:
                c.glow(sx + 6, sy + 2, 14, nc, .35, 9)
                c.rect(sx, sy, 12, 1, nc); c.rect(sx, sy + 4, 12, 1, nc); c.rect(sx, sy, 1, 5, nc); c.rect(sx + 11, sy, 1, 5, nc)
                c.rect(sx + 3, sy + 2, 6, 1, nc)
    scroll(s * .45, 34, 21, mid)
    road(c, '#3c5a66', ['#1c2c36', '#16242c', '#121e26'], '#5a7a82', s, '#2a3c44')
    # wet reflections of lamps + neon
    def lamp(x, r, k):
        c.rect(x, 64, 2, ROAD0 - 64, '#0e1a22'); c.rect(x, 62, 8, 2, '#0e1a22')
        c.glow(x + 7, 66, 9, '#ffd98a', .85); c.rect(x + 5, 64, 4, 1, '#fff1c4')
        c.glow(x + 8, ROAD0 + 6, 22, '#f2c46d', .35, 6)
        for y in range(ROAD0 + 2, ROAD1, 2):
            c.rect(x + 6 + int(math.sin(y + t * 9)), y, 4, 1, '#c8a560' if (y // 2) % 2 else '#8a7a50')
    scroll(s, 70, 7, lamp)
    # sidewalk foreground
    c.grad(ROAD1, H, ['#22323a', '#1a2830', '#141e26'])
    c.rect(0, ROAD1, W, 1, '#4a646c')
    scroll(s * 1.3, 18, 9, lambda x, r, k: c.rect(x, ROAD1 + 1, 1, H - ROAD1, '#121c22'))
    def post(x, r, k):
        c.rect(x, ROAD1 - 6, 2, 14, '#2a3a42'); c.rect(x, ROAD1 - 6, 2, 1, '#6a8a92')
    scroll(s * 1.3, 46, 13, post)
    def fx(c):
        for i, (rx, ry, z) in enumerate(RAIN):
            y = (ry * H + t * (160 + 80 * z)) % (H + 10) - 5; x = (rx * W - t * (60 + 40 * z)) % W
            c.line(x, y, x + 2 + z * 2, y + 3 + z * 3, '#4f7a88' if z < .6 else '#86b2c0')
        # spray from the rear wheel
        for i in range(8):
            ph = (t * 4 + i / 8) % 1
            c.px(CARX + 6 - ph * 18, CARY + 15 - math.sin(ph * 3) * 5 + i % 2, '#7aa6b4')
    return c, dict(mul=(.62, .78, .92), rim=[(-2, '#ff7ab8', .45), (1, '#4fe0e8', .3)], night=True,
                   pool='#0a1218', fx=fx, refl=.35)


# ---- 2. desert at sunset ----
def env_desert(t):
    c = C(); s = V * t
    c.grad(0, 80, ['#3a2c5a', '#6a3c6e', '#b8546a', '#ec7a5c', '#f6a860', '#ffd28a'])
    for j in range(13):
        hw = int(math.sqrt(max(0, 169 - (13 - j) ** 2))); c.rect(96 - hw, 66 + j, hw * 2, 1, '#fff0c0')
    c.glow(96, 76, 60, '#ffd28a', .35, 26)
    for i in range(5):
        y = 18 + i * 9; x = (i * 53 - t * 2) % (W + 60) - 30
        c.rect(x, y, 26 + i * 4, 1, '#f6a08a'); c.rect(x + 6, y + 1, 14 + i * 3, 1, '#d8707a')
    ridge(c, s * .05, 78, 6, .03, '#7a4a7a', 2, hi='#a8607a')
    def mesa(x, r, k):
        h = 14 + r * 14; w = 30 + int(r * 30)
        c.rect(x, 86 - h, w, h, '#a84a4a'); c.rect(x - 3, 86 - h + 3, w + 6, h - 3, '#a84a4a')
        c.rect(x, 86 - h, w, 1, '#e88a62'); c.rect(x + w - 6, 86 - h, 6, h, '#7a3444')
        for j in range(3): c.rect(x - 3, 86 - h + 6 + j * 4, w + 6, 1, '#8e3e4a')
    scroll(s * .15, 70, 31, mesa)
    ridge(c, s * .3, 92, 4, .05, '#c8704a', 7, 104, '#f0a060')
    def cactus(x, r, k):
        if r < .45: return
        h = 10 + r * 10; b = 103
        c.rect(x, b - h, 3, h, '#3a5040'); c.rect(x, b - h, 1, h, '#6a8458')
        c.rect(x - 4, b - h * .6, 4, 2, '#3a5040'); c.rect(x - 4, b - h * .6 - 5, 2, 5, '#3a5040')
        c.rect(x + 3, b - h * .45, 3, 2, '#3a5040'); c.rect(x + 4, b - h * .45 - 4, 2, 4, '#3a5040')
    scroll(s * .6, 26, 41, cactus)
    road(c, '#b88a6a', ['#5a4a52', '#4e4048', '#44383e'], '#f0c050', s, '#d8b088')
    def pole(x, r, k):
        c.rect(x, 52, 2, ROAD0 - 52, '#4a2a2e'); c.rect(x - 5, 55, 12, 1, '#4a2a2e')
        for d in (-4, 5):
            for i in range(60):
                c.px(x + d + i, 56 + math.sin(i / 60 * math.pi) * 5, '#5a3036')
    scroll(s, 60, 17, pole)
    c.grad(ROAD1, H, ['#d88a5a', '#c8704a', '#a85a44'])
    def rock(x, r, k):
        c.rect(x, ROAD1 + 2 + int(r * 8), 3 + int(r * 4), 2, '#7a4038'); c.px(x, ROAD1 + 2 + int(r * 8), '#f0a070')
    scroll(s * 1.35, 9, 5, rock)
    def fx(c):
        for i in range(26):   # dust trail
            ph = (t * 1.6 + i / 26) % 1
            x = CARX + 2 - ph * 60; y = CARY + 13 - ph * 10 + math.sin(i * 3.1) * 3 * ph
            if ph < .95: c.glow(x, y, 2 + ph * 6, '#e8b088', .55 * (1 - ph))
    return c, dict(mul=(1.0, .82, .78), rim=[(1, '#ffe0a0', .6), (2, '#ffcc88', .35)], night=False,
                   pool='#5a3a3a', fx=fx, refl=0)


# ---- 3. snowy pine forest, blue hour ----
SNOW = np.random.default_rng(2).random((130, 3))


def env_snow(t):
    c = C(); s = V * t
    c.grad(0, 84, ['#141c3a', '#1e2c52', '#2e4270', '#4a6290', '#7a90b8', '#a8b8d4'])
    for i in range(30):
        c.px(hr(i, 3) * W, hr(i, 4) * 40, '#c8d4f0' if math.sin(t * 3 + i) > -.3 else '#5a6a90')
    c.glow(104, 20, 6, '#f0f4ff', .95); c.glow(104, 20, 18, '#9ab0e0', .3)
    ridge(c, s * .04, 70, 10, .025, '#5a6c98', 4, hi='#c8d4ec')
    scroll(s * .15, 7, 51, lambda x, r, k: pine(c, x, 86, 12 + r * 10, '#4a5a86', '#3e4c78', '#a8b8d8'))
    c.rect(0, 86, W, 18, '#c8d4ec')
    scroll(s * .4, 12, 61, lambda x, r, k: pine(c, x, 100, 20 + r * 14, '#2c3a5c', '#22304e', '#b8c8e4'))
    c.grad(98, ROAD0, ['#d8e2f2', '#b8c8e0'])
    road(c, '#e8eef8', ['#4a5068', '#3e4458', '#363c4e'], '#8a90a4', s, '#e8eef8')
    for x in range(W):                                   # snow on road edges
        if hr(int(x + s) // 2, 8) > .5: c.px(x, ROAD0 + 1, '#c8d0e0')
    c.grad(ROAD1, H, ['#f0f4fa', '#d0dcec', '#a8b8d4'])
    def fx(c):
        c.glow(CARX + 70, CARY + 10, 34, '#fff4d0', .4, 9)    # headlight beam
        scroll(s * 1.6, 90, 71, lambda x, r, k: pine(c, x, H + 4, 46 + r * 16, '#0e1424', '#0a0e1a', '#5a6a8c') if r > .6 else None)
        for rx, ry, z in SNOW:
            y = (ry * H + t * (14 + 22 * z)) % H; x = (rx * W - t * (40 + 70 * z) + math.sin(t * 2 + ry * 9) * 3) % W
            c.rect(x, y, 1 + (z > .8), 1 + (z > .8), '#f4f8ff' if z > .4 else '#a8b8d8')
        for i in range(10):
            ph = (t * 3 + i / 10) % 1
            c.px(CARX + 4 - ph * 16, CARY + 14 - math.sin(ph * 3) * 4, '#f0f4ff')
    return c, dict(mul=(.62, .7, .95), rim=[(2, '#e8f0ff', .55), (1, '#9ab0e0', .3)], night=True,
                   pool='#6a7894', fx=fx, refl=0)


# ---- 4. coast road, golden morning ----
def env_coast(t):
    c = C(); s = V * t
    c.grad(0, 70, ['#5a8ab8', '#7aa4c8', '#a8c0d4', '#e8d0b8', '#f8dca8'])
    c.glow(30, 64, 30, '#fff4d0', .55, 18); c.glow(30, 64, 6, '#fffbe8', .95)
    for i in range(7):
        y = 12 + i * 7; x = (i * 61 - t * (3 + i)) % (W + 70) - 35; w = 20 + i * 5
        c.rect(x, y, w, 2, '#f4ece0'); c.rect(x + 4, y - 1, w - 10, 1, '#fff8f0'); c.rect(x + 2, y + 2, w - 4, 1, '#c8b8b8')
    c.grad(70, 101, ['#4a7aa4', '#3a6a96', '#2e5a88', '#244e78'])
    for j in range(0, 26, 2):
        for k in range(3):
            ph = math.sin(t * 2.5 + j * 1.9 + k * 2.3)
            if ph > .3: c.rect(30 + math.sin(j * 2.7 + k * 5) * (3 + j * .9), 70 + j, 2 + int(ph * 3), 1, '#fff0c8')
    scroll(s * .05, 160, 81, lambda x, r, k: (c.rect(x, 62, 40, 9, '#5a7a6a'), c.rect(x + 30, 52, 4, 10, '#f0ece4'),
                                              c.rect(x + 30, 55, 4, 2, '#c84a4a'), c.rect(x + 29, 50, 6, 2, '#3a4a4a')))
    for i in range(16):
        y = 74 + (i * 5) % 20; x = (i * 37 - s * .08) % W
        c.rect(x, y, 3 + i % 3, 1, '#7aa8cc')
    ridge(c, s * .5, 100, 3, .07, '#6a8a4a', 3, ROAD0, '#a8c46a')
    def flowers(x, r, k):
        c.px(x, 99 + int(r * 4), '#f0e070' if r > .5 else '#f4a0b8')
    scroll(s * .5, 5, 91, flowers)
    road(c, '#d8d0c0', ['#6a6670', '#5e5a64', '#545058'], '#f4f0e4', s, '#e8e0d0')
    def rail(x, r, k):
        c.rect(x, ROAD1 - 2, 2, 8, '#8a8a92'); c.rect(x, ROAD1 - 2, 1, 8, '#d8d8e0')
    scroll(s * 1.25, 16, 15, rail)
    c.grad(ROAD1, H, ['#7a9a5a', '#5a7a44', '#44603a'])
    c.rect(0, ROAD1 + 1, W, 2, '#c8ccd4'); c.rect(0, ROAD1 + 3, W, 1, '#6a6a72')
    def grass(x, r, k):
        for i in range(3): c.line(x + i * 2, H, x + i * 2 + (r - .5) * 4, H - 6 - r * 6 - i, '#3a5a30' if i % 2 else '#7aa050')
    scroll(s * 1.5, 11, 25, grass)
    def fx(c):
        for i in range(4):
            x_ = (120 - t * 10 + i * 13) % (W + 20) - 10; y_ = 26 + i * 5 + math.sin(t * 1.8 + i) * 2
            fl = int(t * 6 + i) % 2
            for dx, dy in ((0, 0), (-1, -fl), (1, -fl), (-2, fl - 1), (2, fl - 1)): c.px(x_ + dx, y_ + dy, '#3a4a5a')
    return c, dict(mul=(1.0, .95, .9), rim=[(-1, '#fff0c8', .55), (2, '#fff4d8', .35)], night=False,
                   pool='#3a3a40', fx=fx, refl=0)


ENVS = [env_city, env_desert, env_snow, env_coast]
SEG = DUR / len(ENVS)
TUN_L = 84


def hill_top(x, x0, x1):
    u = (x - (x0 - 30)) / (x1 - x0 + 60)
    return ROAD0 - 34 - 46 * math.sin(math.pi * min(1, max(0, u))) ** .7 + 2 * math.sin(x * .4)


def tunnel_bg(c, x0, x1, t, style):
    """Rock hill behind/around the tunnel (drawn into the env background)."""
    rock, face, cap = style
    for x in range(max(0, int(x0) - 30), min(W, int(x1) + 30)):
        top = int(hill_top(x, x0, x1))
        if top >= ROAD0: continue
        c.rect(x, top, 1, ROAD0 - top, rock)
        c.rect(x, top, 1, 2, cap)
        for y in range(top + 3, ROAD0, 5):
            if hr(int(x - x0) // 6 * 31 + y, 5) > .55: c.rect(x, y, 1, 1, face)


def tunnel(c, x0, x1, t, style):
    rock, face, cap = style
    xa, xb = max(0, int(x0)), min(W, int(x1))
    if xb > xa:
        c.a[ROAD0 - 30:ROAD1 + 2, xa:xb] = col('#16141c')
        c.a[ROAD0 - 30:ROAD0 - 20, xa:xb] = col('#100e14')
        c.a[ROAD0:ROAD1, xa:xb] = col('#26242c')
        for x in range(xa, xb):
            if int(x + V * t) % 22 < 5:
                c.a[ROAD0 - 29, x] = col('#ffc060'); c.a[ROAD0 - 28, x] = col('#a87038')
            if int(x + V * t) % 30 < 12: c.a[ROAD0 + 8, x] = col('#5a5860')
        c.a[ROAD1:H, xa:xb] = col('#100e14')
    for xp, sgn in ((x0, 1), (x1 - 5, -1)):      # concrete portal frames
        c.rect(xp, ROAD0 - 34, 5, ROAD1 - ROAD0 + 36, '#8a8690'); c.rect(xp + (4 if sgn > 0 else 0), ROAD0 - 34, 1, ROAD1 - ROAD0 + 36, '#4a4650')
        c.rect(xp - 2, ROAD0 - 36, 9, 3, '#b8b4bc')


TSTYLE = [('#2e3a44', '#46566a', '#5a7a6a'), ('#8e4a40', '#b8644a', '#e8a070'), ('#4a5470', '#6a7894', '#eef4ff')]


def frame(t):
    k = min(len(ENVS) - 1, int(t // SEG))
    c, look = ENVS[k](t)
    tun = None
    for b in range(1, len(ENVS)):
        Tb = b * SEG
        xin = CARX + 24 - TUN_L / 2 + V * (Tb - t); xout = xin + TUN_L
        if xout > -30 and xin < W + 30:
            A, la = ENVS[b - 1](t); B, lb = ENVS[b](t)
            xi, xo = int(max(0, min(W, xin))), int(max(0, min(W, xout)))
            c.a[:, :xi] = A.a[:, :xi]; c.a[:, xo:] = B.a[:, xo:]
            tunnel_bg(c, xin, xout, t, TSTYLE[b - 1])
            tunnel(c, xin, xout, t, TSTYLE[b - 1])
            mid = CARX + 24
            look = la if mid < xin else lb if mid >= xout else dict(mul=(.45, .42, .5), rim=[(2, '#ffb050', .6)],
                                                                         night=True, pool='#000000', fx=None, refl=0)
            tun = (xin, xout, la, lb)
    # car
    bump = -1 if math.sin(t * 9.0) + math.sin(t * 5.3) > 1.5 else 0
    c.glow(CARX + 25, CARY + 17, 26, look['pool'], .55, 2.5)
    if look['night']:
        c.glow(CARX + 58, CARY + 14, 24, '#fff0c0', .3, 4)
    if look.get('refl'):
        tmp = C(); tmp.a[:] = c.a
        Lr = draw_car(tmp, CARX, CARY + bump, t, look['mul'], look['rim'], look['night'])
        ys, xs = np.nonzero(Lr.m)
        for y, x in zip(ys, xs):
            ry = 2 * (CARY + 17) - y
            if ry < H and ry % 2: c.a[ry, x] = c.a[ry, x] * .65 + tmp.a[y, x] * look['refl']
    draw_car(c, CARX, CARY + bump, t, look['mul'], look['rim'], look['night'])
    if tun:   # effects only on their own side of the tunnel
        xin, xout, la, lb = tun
        for lk, lo, hi in ((la, 0, xin), (lb, xout, W)):
            if lk.get('fx') and hi > lo:
                tmp = C(); tmp.a[:] = c.a; lk['fx'](tmp)
                a0, a1 = int(max(0, lo)), int(min(W, hi))
                c.a[:, a0:a1] = tmp.a[:, a0:a1]
        # exhaust lamp streaks over the car inside the tunnel
    elif look.get('fx'):
        look['fx'](c)
    a = c.a * max(0, min(1, t / .6, (DUR - t) / .8))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W * S, H * S), Image.NEAREST)


# ---------------- audio ----------------
def audio(path):
    n = int(SR * DUR); tt = np.arange(n) / SR; r = np.random.default_rng(3)
    noise = r.standard_normal(n)
    lp = lambda x, k: np.convolve(x, np.ones(k) / k, 'same')
    seg = lambda i: np.clip(np.minimum((tt - i * SEG + .4) / .4, (i * SEG + SEG + .4 - tt) / .4), 0, 1)
    f0 = 52 + 3 * np.sin(tt * .7)
    ph = np.cumsum(f0) / SR
    engine = (np.sin(2 * np.pi * ph) * .5 + np.sign(np.sin(2 * np.pi * ph * 2)) * .08) * .12
    engine = lp(engine, 12) + lp(noise, 60) * .25
    rain = lp(noise, 3) * .05 * seg(0)
    wind = lp(noise, 120) * (1 + np.sin(tt * .9)) * .9 * seg(1)
    snow = lp(noise, 300) * 1.4 * seg(2)
    waves = lp(noise, 90) * (1.2 + np.sin(tt * 1.3)) * 1.0 * seg(3)
    gull = sum(np.sin(2 * np.pi * (1800 - 600 * ((tt - s) * 4)) * (tt - s)) * np.exp(-((tt - s - .12) / .08) ** 2)
               for s in (13.2, 13.5)) * .03
    whoosh = sum(lp(noise, 20) * np.exp(-((tt - b * SEG) / .45) ** 2) * .5 for b in (1, 2, 3))
    tri = lambda f: 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * tt))
    music = np.zeros(n); beat = .25
    chords = [(220, 277.2, 329.6), (185, 233.1, 277.2), (146.8, 185, 220), (164.8, 207.7, 246.9)]
    for i in range(int(DUR / beat)):
        s0 = i * beat; ch = chords[(i // 8) % 4]; f = ch[[0, 1, 2, 1, 2, 1, 0, 2][i % 8]] * 2
        m = (tt >= s0) & (tt < s0 + beat)
        music[m] += tri(f)[m] * np.exp(-(tt[m] - s0) * 7) * .05
        if i % 8 == 0:
            m2 = (tt >= s0) & (tt < s0 + beat * 8)
            music[m2] += tri(ch[0] / 2)[m2] * .03
    mix = engine + rain + wind + snow + waves + gull + whoosh + music
    mix *= np.clip(np.minimum(tt / .6, (DUR - tt) / .9), 0, 1)
    mix = np.clip(mix / max(1e-6, np.abs(mix).max()) * .8, -1, 1)
    st = (np.c_[mix, mix] * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: frame(float(s)).save(out / f'f_{s}.png')
    else:
        out = Path(sys.argv[2]); out.parent.mkdir(parents=True, exist_ok=True)
        wav = out.with_suffix('.wav'); audio(wav)
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                              '-s', f'{W * S}x{H * S}', '-r', str(FPS), '-i', '-', '-i', str(wav),
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
                              '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out)],
                             stdin=subprocess.PIPE)
        for i in range(int(DUR * FPS)):
            p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
