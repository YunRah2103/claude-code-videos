"""Pixel style reel for car videos / TikTok explainers: 10 original styles x 5 s, vertical 9:16.
Usage: python render.py video OUT.mp4 | python render.py still OUTDIR t1 t2 ..."""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

W, H = 108, 192; S = 10; FPS = 30; SEGD = 5.0; SR = 44100
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
YS, XS = np.mgrid[0:H, 0:W]


def hx(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
def col(c): return hx(c) if isinstance(c, str) else np.asarray(c, np.float32)


class C:
    """Pixel canvas at any resolution (default 108x192)."""
    def __init__(s, layer=False, w=None, h=None):
        s.w, s.h = w or W, h or H
        s.a = np.zeros((s.h, s.w, 3), np.float32); s.m = np.zeros((s.h, s.w), bool) if layer else None
        s.ys, s.xs = np.mgrid[0:s.h, 0:s.w]
    def rect(s, x, y, w, h, c):
        x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(s.w, int(x + w)), min(s.h, int(y + h))
        if x1 > x0 and y1 > y0:
            s.a[y0:y1, x0:x1] = col(c)
            if s.m is not None: s.m[y0:y1, x0:x1] = True
    def px(s, x, y, c): s.rect(round(x), round(y), 1, 1, c)
    def line(s, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n; s.px(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, c)
    def grad(s, y0, y1, cols, x0=0, x1=None, dither=True):
        x1 = s.w if x1 is None else x1; y0, y1 = max(0, int(y0)), min(s.h, int(y1))
        if y1 <= y0: return
        cs = np.stack([col(c) for c in cols]); n = len(cols) - 1
        ys, xs = s.ys[y0:y1, x0:x1], s.xs[y0:y1, x0:x1]
        t = (ys - y0) / max(1, y1 - y0 - 1) * n + ((BAYER[ys % 4, xs % 4] - .5) if dither else 0)
        s.a[y0:y1, x0:x1] = cs[np.clip(np.round(t), 0, n).astype(int)]
    def glow(s, cx, cy, r, c, k=.55, ry=None, steps=3):
        ry = ry or r
        d = np.sqrt(((s.xs - cx) / r) ** 2 + ((s.ys - cy) / ry) ** 2)
        lv = np.clip(np.floor((1 - d) * steps + BAYER[s.ys % 4, s.xs % 4]), 0, steps) / steps * k
        s.a[:] = s.a * (1 - lv[..., None]) + col(c) * lv[..., None]
    def poly(s, pts, c):
        im = Image.new('L', (s.w, s.h), 0); ImageDraw.Draw(im).polygon([tuple(map(float, p)) for p in pts], fill=1)
        m = np.asarray(im, bool); s.a[m] = col(c)
        if s.m is not None: s.m |= m
        return m
    def disc(s, cx, cy, r, c, ymax=None):
        for y in range(max(0, int(cy - r)), min(s.h, int(cy + r) + 1, ymax or s.h)):
            hw = math.sqrt(max(0, r * r - (y - cy) ** 2)); s.rect(round(cx - hw), y, round(2 * hw), 1, c)
    def spr(s, x, y, rows, pal, flip=False):
        for j, row in enumerate(rows):
            if flip: row = row[::-1]
            for i, ch in enumerate(row):
                if ch in pal: s.px(x + i, y + j, pal[ch])


def dilate(m):
    d = m.copy(); d[1:] |= m[:-1]; d[:-1] |= m[1:]; d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]; return d


def edge_in(m): return m & dilate(~m)


def stamp(dst, L, outline=None, line_only=None):
    """Composite a layer; optional dark outer outline, or line-art mode (fill black, inner edge in colour)."""
    m = L.m
    if line_only:
        dst.a[m] = col('#000000') if line_only[1] is None else col(line_only[1]); dst.a[edge_in(m)] = col(line_only[0]); return
    if outline: dst.a[dilate(m) & ~m] = col(outline)
    dst.a[m] = L.a[m]


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


def draw_car(c, x0, y0, t, mul, rim, night, pal=None):
    global CAR
    CAR = CAR or build_car()
    L = C(layer=True, w=c.w, h=c.h)
    L.spr(x0, y0, CAR, pal or CARPAL)
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


def scroll(off, gap, seed, fn, pad=40, w=None):
    """Call fn(x, rand, k) for repeating objects spaced `gap` apart, scrolled by `off`."""
    k0 = int(math.floor((off - pad) / gap))
    for k in range(k0, k0 + int(((w or W) + 2 * pad) / gap) + 2):
        fn(k * gap - off, hr(k, seed), k)


def ridge(c, off, y, amp, freq, colr, seed, y1=None, hi=None):
    for x in range(c.w):
        u = (x + off) * freq
        hh = amp * (.55 * math.sin(u + seed) + .3 * math.sin(u * 2.3 + seed * 3) + .15 * math.sin(u * 5.1))
        top = int(y - hh)
        c.rect(x, top, 1, (y1 or c.h) - top, colr)
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


V = 80.0
CARX, CARY = 29, 139
ROAD0, ROAD1 = 146, 162


def road(c, top_col, cols, dash, s, edge='#d8d0b8', dash_gap=30):
    c.grad(ROAD0, ROAD1, cols)
    c.rect(0, ROAD0, W, 1, top_col)
    scroll(s, dash_gap, 3, lambda x, r, k: c.rect(x, (ROAD0 + ROAD1) // 2, 12, 1, dash))
    c.rect(0, ROAD1 - 1, W, 1, edge)


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'new-car-trap' / 'src'))
from pix import FONT, text_width   # reuse the project's pixel font
from PIL import ImageFilter

HZ = 122   # default horizon


def disc(c, cx, cy, r, colr, ymax=H):
    for y in range(max(0, int(cy - r)), min(H, int(cy + r) + 1, ymax)):
        hw = math.sqrt(max(0, r * r - (y - cy) ** 2)); c.rect(round(cx - hw), y, round(2 * hw), 1, colr)


def puff(c, x, y, w, h, z, t, cols, speed=2):
    hl, mid, sh = cols
    x = (x + t * (speed + 2 * z)) % (W + 120) - 60
    bl = [(x + k, y - h * .5 * abs(math.sin(k * .3 + z * 9)), h * (.6 + .5 * abs(math.sin(k * .21 + z * 5))))
          for k in range(0, w, 4)]
    for bx, by, r in bl: disc(c, bx, by + 1, r, sh, y + h + 1)
    for bx, by, r in bl: disc(c, bx - .5, by - 1, r - .5, mid, y + h - 1)
    for bx, by, r in bl: disc(c, bx - 1, by - 2.5, r - 1.8, hl, y + h - 3)


def sun(c, cx, cy, r, cols, t=0, stripes=False, ymax=H):
    n = len(cols)
    for y in range(int(cy - r), min(int(cy + r) + 1, ymax)):
        f = (y - (cy - r)) / (2 * r)
        if stripes and f > .45:
            g = int((y - cy * 0 + t * 6) % 7)
            if g < 1 + int((f - .45) * 8): continue
        hw = math.sqrt(max(0, r * r - (y - cy) ** 2))
        c.rect(round(cx - hw), y, round(2 * hw), 1, cols[min(n - 1, int(f * n))])


def stars(c, t, n=40, ymax=100, seed=3, cols=('#e8ecff', '#7a84b0')):
    for i in range(n):
        tw = math.sin(t * 3 + i * 1.7)
        c.px(hr(i, seed) * W, hr(i, seed + 1) * ymax, cols[0] if tw > -.2 else cols[1])


def quantize(a, pal, dither=True, lo=None, hi=None):
    """Map an RGB frame onto a small palette by luminance (contrast-stretched), ordered dithering."""
    lum = (a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11) / 255
    lo = np.percentile(lum, 3) if lo is None else lo; hi = np.percentile(lum, 97) if hi is None else hi
    lum = np.clip((lum - lo) / max(1e-3, hi - lo), 0, 1)
    n = len(pal); d = BAYER[YS % 4, XS % 4] if dither else .5
    idx = np.clip(np.floor(lum * (n - 1) + d), 0, n - 1).astype(int)
    return np.stack([col(p) for p in pal])[idx]


# ---------------------------------------------------------------- 01 NEON RAIN
NEON = ['#ff4fa0', '#3fe6f0', '#ffb347', '#a07bff']
RAIN = np.random.default_rng(1).random((120, 3))


def s_neon(t):
    c = C(); s = V * t
    c.grad(0, 130, ['#070d18', '#0c1626', '#122236', '#1a3046', '#24405a'])
    def far(x, r, k):
        h = 50 + r * 60; w = 12 + int(r * 10)
        c.rect(x, 132 - h, w, h, '#101e2e')
        for j in range(int(h // 5)):
            for i in range(w // 4):
                if hr(k * 97 + j * 13 + i, 5) > .8: c.px(x + 2 + i * 4, 132 - h + 3 + j * 5, '#c9a660' if hr(k + j, 9) > .4 else '#4d7f90')
    scroll(s * .1, 15, 11, far)
    c.glow(54, 130, 80, '#2f5e78', .3, 16)
    def mid(x, r, k):
        h = 70 + r * 50; w = 24 + int(r * 10); b = ROAD0
        c.rect(x, b - h, w, h, '#162636'); c.rect(x + w - 3, b - h, 3, h, '#101c28')
        for j in range(int(h // 7) - 1):
            for i in range(w // 6):
                if hr(k * 31 + j * 7 + i, 4) > .62: c.rect(x + 3 + i * 6, b - h + 5 + j * 7, 3, 2, '#e8c47a' if hr(k + i, 2) > .5 else '#2f4e60')
        nc = NEON[k % 4]; on = not (r > .7 and math.sin(t * 15 + k) > .6)
        sx, sy = x + w - 6, b - h + 10
        c.rect(sx, sy, 5, 30, '#0a1018')
        if on:
            c.glow(sx + 2, sy + 15, 9, nc, .45, 22)
            c.rect(sx, sy, 5, 1, nc); c.rect(sx, sy + 29, 5, 1, nc); c.rect(sx, sy, 1, 30, nc); c.rect(sx + 4, sy, 1, 30, nc)
            for j in range(4): c.rect(sx + 2, sy + 4 + j * 7, 1, 4, nc)
    scroll(s * .4, 30, 21, mid)
    road(c, '#3c5a66', ['#1a2832', '#141f28', '#101a22'], '#5a7a82', s, '#2a3c44')
    def lamp(x, r, k):
        c.rect(x, 96, 2, ROAD0 - 96, '#0c161e'); c.rect(x, 94, 8, 2, '#0c161e')
        c.glow(x + 7, 98, 8, '#ffd98a', .9); c.rect(x + 5, 96, 4, 1, '#fff1c4')
        c.glow(x + 8, ROAD0 + 6, 18, '#f2c46d', .35, 5)
        for y in range(ROAD0 + 2, ROAD1, 2): c.rect(x + 6 + int(math.sin(y + t * 9)), y, 4, 1, '#c8a560' if (y // 2) % 2 else '#8a7a50')
    scroll(s, 64, 7, lamp)
    c.grad(ROAD1, H, ['#1a2830', '#141e26', '#0e161c', '#0a1016'])
    c.rect(0, ROAD1, W, 1, '#4a646c')
    for y in range(ROAD1 + 3, H, 3):      # puddle reflections of the neon
        for k in range(3):
            x = (k * 41 + 13 - s * 1.3) % (W + 30) - 15
            c.rect(x + math.sin(y * .7 + t * 6) * 2, y, 8, 1, NEON[k] if (y // 3) % 2 else '#24384a')
    def fx(c):
        for rx, ry, z in RAIN:
            y = (ry * H + t * (180 + 90 * z)) % (H + 10) - 5; x = (rx * W - t * (50 + 40 * z)) % W
            c.line(x, y, x + 2 + z * 2, y + 3 + z * 4, '#4a7488' if z < .6 else '#8ab6c4')
        for i in range(8):
            ph = (t * 4 + i / 8) % 1
            c.px(CARX + 6 - ph * 18, CARY + 15 - math.sin(ph * 3) * 5 + i % 2, '#7aa6b4')
    return c, dict(mul=(.62, .78, .92), rim=[(-2, '#ff7ab8', .5), (1, '#4fe6f0', .35)], night=True, pool='#05090e', fx=fx, refl=.35)


# ---------------------------------------------------------------- 06 SIXTEEN-BIT SUNNY (also base for POCKET GREEN)
CLOUD_SUNNY = [(hr(i, 61) * (W + 120) - 60, 20 + int(hr(i, 62) * 70), 16 + int(hr(i, 63) * 24), 4 + int(hr(i, 64) * 3), hr(i, 65)) for i in range(9)]


def s_sunny(t, windmill=False):
    c = C(); s = V * t
    c.grad(0, 132, ['#2a6ae0', '#3a86ee', '#5aa4f6', '#82c2fa', '#b4dcfc', '#d8eefc'])
    for q in CLOUD_SUNNY: puff(c, *q, t, ('#ffffff', '#e4eefa', '#a8bee0'))
    def mtn(x, r, k):
        h = 30 + r * 22; w = h * 1.6
        for j in range(int(h)):
            hw = w / 2 * j / h; y = 132 - h + j
            c.rect(x - hw, y, hw, 1, '#7a9ad0'); c.rect(x, y, hw, 1, '#6484c0')
            if j < h * .25: c.rect(x - hw, y, hw * 2, 1, '#f4f8ff' if j % 3 else '#d4e0f4')
    scroll(s * .06, 46, 81, mtn)
    ridge(c, s * .15, 128, 5, .05, '#5aa84a', 2, hi='#8ad06a')
    if windmill:
        def mill(x, r, k):
            if r < .55: return
            c.rect(x - 2, 104, 5, 26, '#e8e0d0'); c.rect(x + 1, 104, 2, 26, '#b8ae9a'); c.rect(x - 3, 102, 7, 3, '#c84a3a')
            a = t * 2.2 + k
            for i in range(4):
                ang = a + i * math.pi / 2; c.line(x, 104, x + math.cos(ang) * 11, 104 + math.sin(ang) * 11, '#5a4a3a')
        scroll(s * .25, 50, 33, mill)
    ridge(c, s * .3, 138, 6, .045, '#3e9a3a', 5, ROAD0, '#6ac85a')
    def tree(x, r, k):
        if r < .35: return
        b = ROAD0 - 1; h = 10 + r * 8
        c.rect(x, b - h * .45, 2, h * .45, '#6a4a2a')
        disc(c, x + 1, b - h * .6, h * .42, '#2a7a34'); disc(c, x, b - h * .68, h * .32, '#4aa844'); c.px(x - 1, b - h * .8, '#9ade6a')
    scroll(s * .7, 18, 41, tree)
    road(c, '#a8b0b8', ['#6a7078', '#5e646c', '#545a62'], '#ffffff', s, '#d8dce0')
    c.grad(ROAD1, H, ['#5ac84a', '#44b03c', '#369a34', '#2a8030'])
    def flower(x, r, k):
        y = ROAD1 + 4 + int(r * 26); c.px(x, y, ['#ff5a6a', '#ffe04a', '#ffffff', '#ff9ad8'][k % 4]); c.px(x, y + 1, '#2a7a34')
    scroll(s * 1.3, 5, 9, flower)
    def fence(x, r, k):
        c.rect(x, ROAD1 + 1, 2, 8, '#f4e8d0'); c.rect(x, ROAD1 + 1, 2, 1, '#ffffff')
    scroll(s * 1.3, 12, 19, fence)
    c.rect(0, ROAD1 + 3, W, 1, '#e8dcc4')
    return c, dict(mul=(1, 1, 1), rim=[(2, '#ffffff', .35), (1, '#fff4c0', .3)], night=False, pool='#3a4048', fx=None)


# ======================================================================================
#  Ten structurally different pixel styles. Each returns an RGB array at its own size.
# ======================================================================================
def finish_side(c, look, t):
    """Side-view car on a 108x192 scene (used by CLASSIC 16-BIT and SOFT CINEMATIC)."""
    bump = -1 if math.sin(t * 9.0) + math.sin(t * 5.3) > 1.5 else 0
    c.glow(CARX + 25, CARY + 17, 26, look['pool'], .55, 2.5)
    if look['night']: c.glow(CARX + 58, CARY + 14, 22, '#fff0c0', .3, 4)
    if look.get('refl'):
        tmp = C(); tmp.a[:] = c.a
        Lr = draw_car(tmp, CARX, CARY + bump, t, look['mul'], look['rim'], look['night'])
        for y, x in zip(*np.nonzero(Lr.m)):
            ry = 2 * (CARY + 17) - y
            if ry < H and ry % 2: c.a[ry, x] = c.a[ry, x] * .65 + tmp.a[y, x] * look['refl']
    draw_car(c, CARX, CARY + bump, t, look['mul'], look['rim'], look['night'])
    if look.get('fx'): look['fx'](c)
    return c.a


def wheel(c, x, y, r, t, tire, rim, hub, spoke=None, spin=22):
    c.disc(x, y, r, tire); c.disc(x, y, r * .55, rim); c.px(x, y, hub)
    if spoke:
        for k in range(3):
            a = t * spin + k * 2.094
            c.px(x + round(math.cos(a) * r * .45), y + round(math.sin(a) * r * .45), spoke)


# ---------------------------------------------------------------- 01 PICO TINY  (27x48, flat, huge pixels)
PICO_CAR = ["...RRRRR...", "..RwwRwwR..", "LRRRRRRRRRY", "rrrrrrrrrrr"]


def st_pico(t):
    c = C(w=27, h=48); s = t * 22
    for (y0, y1, cl) in ((0, 10, '#241a44'), (10, 17, '#4e2a62'), (17, 23, '#93426c'), (23, 28, '#d8665c'), (28, 33, '#f6a65a')):
        c.rect(0, y0, 27, y1 - y0, cl)
    for i in range(6):
        if math.sin(t * 2.5 + i * 2) > -.2: c.px(hr(i, 2) * 27, hr(i, 3) * 12, '#f4e6ff')
    c.disc(18, 29, 3.2, '#ffe8a6', ymax=33)
    ridge(c, s * .2, 32, 2, .35, '#3a2348', 4, 34)
    c.rect(0, 34, 27, 5, '#2a2030'); c.rect(0, 34, 27, 1, '#5a4060')
    scroll(s, 7, 1, lambda x, r, k: c.rect(x, 36, 3, 1, '#f0b060'), w=27)
    c.rect(0, 39, 27, 9, '#1a1424')
    scroll(s * 1.3, 5, 4, lambda x, r, k: c.px(x, 41 + int(r * 6), '#3a2a46'), w=27)
    scroll(s, 16, 8, lambda x, r, k: (c.rect(x, 22, 1, 12, '#140e1c'), c.rect(x - 2, 23, 5, 1, '#140e1c')), w=27)
    b = -1 if (t * 3) % 1 < .12 else 0
    c.spr(8, 30 + b, PICO_CAR, P(R='#e05a48', w='#8ad0e0', L='#ff3a3a', Y='#fff0a0', r='#8a2a30'))
    for wx in (10, 16):
        c.px(wx, 34 + b, '#0e0a14'); c.px(wx + 1, 34 + b, '#0e0a14' if int(t * 10) % 2 else '#6a6070')
    c.px(20, 31 + b, '#fff6c8'); c.px(21, 32 + b, '#a88a5a')
    if int(t * 6) % 3 == 0: c.px(6 - (t * 6) % 3, 33 + b, '#6a5a7a')
    return c.a


# ---------------------------------------------------------------- 02 CHUNKY 8-BIT  (54x96, flat colours, black outlines)
CHUNKY_CAR = ["......RRRRRRRRR.........", ".....RwwwwRwwwwR........", "....RwwwwwRwwwwwR.......",
              "..RRRRRRRRRRRRRRRRRRR...", ".RhhhhhhhhhhhhhhhhhhhhR.", "LRRRRRRRRRRRRRRRRRRRRRRY",
              "RRRRRRRRRRRRRRRRRRRRRRRR", "rrrrrrrrrrrrrrrrrrrrrrrr"]
INK = '#101018'


def st_chunky(t):
    c = C(w=54, h=96); s = t * 40
    c.rect(0, 0, 54, 74, '#6aa0fc')
    L = C(layer=True, w=54, h=96); L.disc(44, 14, 5, '#ffe45a'); stamp(c, L, INK)
    def cloud(x, r, k):
        L = C(layer=True, w=54, h=96); y = 10 + int(r * 22)
        L.disc(x, y, 4, '#ffffff'); L.disc(x + 5, y - 2, 5, '#ffffff'); L.disc(x + 10, y, 4, '#ffffff'); L.rect(x, y, 11, 4, '#ffffff')
        L.rect(x + 1, y + 3, 9, 1, '#bcd8fc'); stamp(c, L, INK)
    scroll(s * .15, 30, 3, cloud, w=54)
    def hill(x, r, k, base=74, cl='#3cb43c', dk='#2a8a2a', size=1.0):
        L = C(layer=True, w=54, h=96); rr = (9 + r * 7) * size
        L.disc(x, base, rr, cl); L.rect(x - rr, base, rr * 2, 2, cl)
        L.px(x - 2, base - rr + 3, dk); L.px(x + 2, base - rr + 5, dk); L.px(x, base - rr + 7, dk)
        stamp(c, L, INK)
    scroll(s * .3, 26, 5, lambda x, r, k: hill(x, r, k, 72, '#8ad86a', '#5ab84a', 1.3), w=54)
    scroll(s * .6, 19, 7, lambda x, r, k: hill(x, r, k, 74, '#3cb43c', '#2a8a2a', .75) if r > .3 else None, w=54)
    c.rect(0, 74, 54, 10, '#7c7c84'); c.rect(0, 74, 54, 1, INK); c.rect(0, 83, 54, 1, INK)
    scroll(s, 12, 3, lambda x, r, k: c.rect(x, 79, 5, 1, '#f8f8f8'), w=54)
    c.rect(0, 84, 54, 12, '#d8a050')
    scroll(s * 1.2, 6, 11, lambda x, r, k: (c.rect(x, 86 + (k % 2) * 5, 3, 1, '#a86a30'), c.px(x + 1, 87 + (k % 2) * 5, '#f0c070')), w=54)
    def sign(x, r, k):
        if r < .6: return
        L = C(layer=True, w=54, h=96); L.rect(x, 64, 1, 10, '#a86a30'); L.rect(x - 3, 60, 7, 5, '#f8f8f8'); L.rect(x - 2, 62, 5, 1, '#e8402a')
        stamp(c, L, INK)
    scroll(s, 37, 13, sign, w=54)
    b = -1 if (t * 3) % 1 < .1 else 0
    L = C(layer=True, w=54, h=96)
    L.spr(14, 66 + b, CHUNKY_CAR, P(R='#e8402a', h='#ff8a6a', r='#a02818', w='#a8e0f8', L='#ffd800', Y='#fff8c0'))
    for wx in (19, 32): wheel(L, wx, 74 + b, 2.6, t, '#202020', '#a0a0a8', '#f8f8f8', '#202020', 18)
    stamp(c, L, INK)
    for i in range(3):
        ph = (t * 2 + i / 3) % 1
        c.disc(12 - ph * 10, 72 - ph * 4, 1 + ph * 1.5, '#f8f8f8' if ph < .6 else '#c8c8d0')
    return c.a


# ---------------------------------------------------------------- 03 CLASSIC 16-BIT  (108x192, saturated, soft shading)
def st_classic(t):
    c, look = s_sunny(t); return finish_side(c, look, t)


# ---------------------------------------------------------------- 04 SOFT CINEMATIC (108x192, no outlines, dithered light)
def st_soft(t):
    c, look = s_neon(t); return finish_side(c, look, t)


# ---------------------------------------------------------------- 05 HD PIXEL  (216x384, fine pixels, many shades)
def lerp_cols(cols, n):
    cs = [col(x) for x in cols]; out = []
    for i in range(n):
        f = i / (n - 1) * (len(cs) - 1); j = min(int(f), len(cs) - 2); u = f - j
        out.append(cs[j] * (1 - u) + cs[j + 1] * u)
    return out


def hd_car(c, x0, y0, t):
    L = C(layer=True, w=c.w, h=c.h)
    body = L.poly([(1, 15), (4, 13), (72, 13), (92, 15), (95, 18), (95, 26), (92, 28), (4, 28), (1, 26)], '#c8503c')
    shade = {13: '#ffb08a', 14: '#f08a68', 15: '#e06a50', 20: '#f6e0b0', 21: '#d85a44', 22: '#b84638', 23: '#b84638',
             24: '#9a3830', 25: '#8a3030', 26: '#6a2428', 27: '#3a1a20', 28: '#2a1418'}
    pts = lambda P_: [(x0 + x, y0 + y) for x, y in P_]
    L.a[:] = 0; L.m[:] = False
    m = L.poly(pts([(1, 15), (4, 13), (72, 13), (92, 15), (95, 18), (95, 26), (92, 28), (4, 28), (1, 26)]), '#c8503c')
    for dy, cl in shade.items():
        row = y0 + dy
        if 0 <= row < c.h: L.a[row][m[row]] = col(cl)
    cab = L.poly(pts([(10, 13), (12, 3), (16, 1), (58, 1), (62, 2), (73, 13)]), '#c8503c')
    L.a[cab & (c.ys <= y0 + 1)] = col('#ff9a78')
    glass = lerp_cols(['#c8e4ee', '#7aa6b8', '#3a5a6e', '#24384a'], 10)
    for P_ in ([(13, 12), (15, 4), (18, 3), (30, 3), (30, 12)], [(33, 3), (48, 3), (48, 12), (33, 12)],
               [(51, 3), (58, 3), (61, 4), (70, 12), (51, 12)]):
        g = L.poly(pts(P_), '#3a5a6e')
        for j in range(10):
            row = y0 + 3 + j
            if 0 <= row < c.h: L.a[row][g[row]] = glass[j]
        for k in range(3):
            for j in range(9): L.px(x0 + P_[0][0] + 6 + k * 4 + j * .6, y0 + 12 - j, '#e8f6fa') if k != 1 else None
    for xx in (31, 49): L.line(x0 + xx, y0 + 13, x0 + xx, y0 + 25, '#6a2428')
    for xx in (36, 54): L.rect(x0 + xx, y0 + 17, 4, 1, '#f0d8c8')
    L.rect(x0 + 18, y0, 36, 1, '#3a3038'); L.px(x0 + 20, y0 + 1, '#3a3038'); L.px(x0 + 50, y0 + 1, '#3a3038')
    L.rect(x0 + 91, y0 + 16, 4, 4, '#fff6d8'); L.rect(x0 + 91, y0 + 20, 4, 1, '#ffa040'); L.rect(x0 + 1, y0 + 15, 3, 5, '#ff4040')
    L.rect(x0 + 89, y0 + 24, 7, 3, '#d8dce4'); L.rect(x0 + 89, y0 + 24, 7, 1, '#ffffff'); L.rect(x0, y0 + 24, 7, 3, '#d8dce4')
    L.rect(x0 + 68, y0 + 10, 3, 3, '#8a3030')
    for wx in (22, 74):
        L.disc(x0 + wx, y0 + 27, 10.5, '#1a1218', ymax=y0 + 29)
        cx, cy = x0 + wx, y0 + 27
        L.disc(cx, cy, 8, '#1c1a20'); L.disc(cx, cy, 7, '#2a2830'); L.disc(cx, cy, 5, '#a0a6b0'); L.disc(cx - .6, cy - .6, 4, '#c8ccd4')
        L.disc(cx, cy, 1.6, '#5a5a64')
        for k in range(5):
            a = t * 9 + k * 1.2566
            L.line(cx + math.cos(a) * 1.6, cy + math.sin(a) * 1.6, cx + math.cos(a) * 4.5, cy + math.sin(a) * 4.5, '#6a6e78')
    a = L.a.copy(); m = L.m
    e = m & ~np.roll(m, 1, axis=1); a[e] = a[e] * .4 + col('#ffd8a0') * .6       # warm rim from the sun
    e = m & ~np.roll(m, 1, axis=0); a[e] = a[e] * .5 + col('#ffe0b0') * .5
    c.a[m] = a[m]


def st_hd(t):
    c = C(w=216, h=384); s = t * 150
    c.grad(0, 262, lerp_cols(['#1e2a5a', '#3a4a86', '#7a6aa8', '#c886a0', '#f4a888', '#ffd09a', '#ffe8b8'], 22))
    c.glow(150, 238, 120, '#ffd8a0', .35, 70, steps=6); c.glow(150, 238, 40, '#fff0c8', .6, steps=6)
    c.disc(150, 238, 13, '#fff8e0')
    for i in range(10):
        y = 40 + i * 17 + int(hr(i, 5) * 8); x = (hr(i, 6) * 400 - t * (4 + i * .6)) % 340 - 60; w = 50 + hr(i, 7) * 60
        c.rect(x, y, w, 3, '#e8a8a8' if y > 120 else '#9a86b8'); c.rect(x + 8, y - 2, w * .6, 2, '#c896b0' if y > 120 else '#7a6aa0')
        c.rect(x + 4, y + 3, w - 10, 1, '#ffd0a0' if y > 120 else '#b8a0c8')
    for i, (y, cl, snow, amp, p) in enumerate([(232, '#9a88b8', '#f4e6f0', 46, .03), (246, '#7a6a9e', '#e8d0e0', 34, .06),
                                                (258, '#5a5280', None, 24, .1), (270, '#433e66', None, 16, .16)]):
        for x in range(216):
            u = (x + s * p) * (.018 + i * .006)
            hh = amp * (.55 * abs(math.sin(u + i)) + .3 * abs(math.sin(u * 2.3 + i * 3)) + .15 * math.sin(u * 5.1))
            top = int(y - hh); c.rect(x, top, 1, 300 - top, cl)
            if snow:
                for j in range(int(hh * .28)):
                    if hr(x * 31 + j, i) > j / (hh * .28) * .9: c.px(x, top + j, snow)
            if (x + int(s * p)) % 7 == 0 and not snow: c.px(x, top, '#f4b8a0')
    def pine2(x, r, k, base, h, body, shade):
        pine(c, x, base, h, body, shade); c.line(x - 1, base - h + 2, x - h * .38, base - 2, '#e89a7a')
    scroll(s * .3, 6, 21, lambda x, r, k: pine2(x, r, k, 286, 14 + r * 10, '#2e3050', '#262844'), w=216)
    scroll(s * .5, 9, 23, lambda x, r, k: pine2(x, r, k, 292, 20 + r * 14, '#1e2238', '#181a2c') if r > .25 else None, w=216)
    c.grad(286, 292, ['#3a3a52', '#2e2e44'])
    c.grad(292, 326, lerp_cols(['#5a5468', '#48445a', '#3a3648'], 6))
    c.rect(0, 292, 216, 1, '#c8a090'); c.rect(0, 324, 216, 2, '#e8d8c8')
    for i in range(160):
        x = (hr(i, 8) * 216 - s) % 216; c.px(x, 294 + hr(i, 9) * 30, '#6a6478' if i % 2 else '#34303e')
    scroll(s, 44, 3, lambda x, r, k: c.rect(x, 308, 20, 2, '#f0e6d0'), w=216)
    c.grad(326, 384, lerp_cols(['#6a7a3a', '#4a5e2c', '#344624', '#22301a'], 8))
    def blade(x, r, k):
        h = 6 + r * 14; sw = math.sin(t * 2 + k) * 1.5
        c.line(x, 384, x + sw + (r - .5) * 4, 384 - h - (k % 3) * 6, '#8aa04a' if r > .5 else '#5a7a34')
        if r > .82: c.px(x + sw, 384 - h - 3, '#f4e070' if k % 2 else '#f0a0b8')
    scroll(s * 1.4, 2, 31, blade, w=216)
    def post(x, r, k):
        c.rect(x, 318, 3, 18, '#d8d0c0'); c.rect(x, 318, 3, 2, '#ffffff'); c.rect(x + 2, 320, 1, 16, '#9a9080')
    scroll(s * 1.2, 40, 15, post, w=216)
    b = -1 if math.sin(t * 9) + math.sin(t * 5.3) > 1.5 else 0
    c.glow(108, 320, 56, '#1a1420', .6, 4, steps=4)
    hd_car(c, 60, 285 + b, t)
    for i in range(18):
        ph = (t * .25 + i / 18) % 1
        x = (hr(i, 41) * 216 - ph * 80) % 216; y = 180 + hr(i, 42) * 160 - ph * 30
        if math.sin(t * 5 + i) > 0: c.px(x, y, '#fff0c0')
    return c.a


# ---------------------------------------------------------------- 06 FLAT MINIMAL  (flat shapes, hard bands, no dither)
FLATPAL = P(R='#f6b26b', h='#f6b26b', r='#d9844a', k='#2e2a40', w='#3e3a5c', W='#3e3a5c', T='#f6b26b', d='#d9844a',
            c='#2e2a40', Y='#fff3d6', y='#fff3d6', L='#e05a5a', a='#2e2a40')


def st_flat(t):
    c = C(); s = V * t
    c.grad(0, 130, ['#3e3a6a', '#7a4a7e', '#c86a7e', '#ef9f8a', '#f6c9a0'], dither=False)
    c.disc(70, 100, 17, '#fff3d6')
    def mtn(x, r, k, base, hgt, lit, dark):
        h = hgt + r * hgt * .6; w = h * 1.4
        c.poly([(x - w / 2, base), (x, base - h), (x + w / 2, base)], lit); c.poly([(x, base - h), (x + w / 2, base), (x + w * .1, base)], dark)
    scroll(s * .08, 50, 3, lambda x, r, k: mtn(x, r, k, 132, 34, '#b86a86', '#9a5474'), w=W, pad=60)
    scroll(s * .2, 36, 5, lambda x, r, k: mtn(x, r, k, 140, 22, '#7a4a78', '#643e66'), w=W, pad=60)
    c.rect(0, 138, W, ROAD0 - 138, '#4a3a68')
    def tri(x, r, k):
        if r < .35: return
        h = 10 + r * 12; c.poly([(x - h * .3, ROAD0), (x, ROAD0 - h), (x + h * .3, ROAD0)], '#2e2a50')
    scroll(s * .55, 11, 7, tri, w=W)
    c.rect(0, ROAD0, W, ROAD1 - ROAD0, '#2e2a40')
    scroll(s, 26, 3, lambda x, r, k: c.rect(x, (ROAD0 + ROAD1) // 2, 10, 1, '#fff3d6'))
    c.rect(0, ROAD1, W, H - ROAD1, '#3a3456'); c.rect(0, ROAD1 + 10, W, 1, '#4a4268')
    for i in range(3):
        x = (20 + i * 9 + t * 6) % (W + 20) - 10; y = 50 + i * 4 + math.sin(t * 2 + i) * 2; f = int(t * 4 + i) % 2
        c.px(x, y, '#3e3a6a'); c.px(x - 1, y - f, '#3e3a6a'); c.px(x + 1, y - f, '#3e3a6a')
    b = -1 if math.sin(t * 9) + math.sin(t * 5.3) > 1.5 else 0
    c.rect(CARX + 4, CARY + 17, 44, 1, '#221e30')
    draw_car(c, CARX, CARY + b, t, (1, 1, 1), [], False, pal=FLATPAL)
    return c.a


# ---------------------------------------------------------------- 07 1-BIT LINE ART  (outlines only, two colours)
LINE, BG1 = '#eaf2ff', '#06070e'


def st_line(t):
    c = C(); s = V * t
    c.a[:] = col(BG1)
    stars(c, t, 30, 100, 9, (LINE, '#3a4060'))
    L = C(layer=True); L.disc(74, 44, 12, '#ffffff'); stamp(c, L, line_only=(LINE, BG1))
    for dx, dy, rr in ((-4, -3, 2.5), (4, 3, 2), (-1, 5, 1.5)):
        L = C(layer=True); L.disc(74 + dx, 44 + dy, rr, '#ffffff'); c.a[edge_in(L.m)] = col(LINE)
    for i, (y, amp, p) in enumerate(((120, 18, .05), (132, 10, .12))):
        L = C(layer=True); ridge(L, s * p, y, amp, .04 + i * .02, '#ffffff', 3 + i, ROAD0); stamp(c, L, line_only=(LINE, BG1))
    L = C(layer=True)
    scroll(s * .45, 9, 51, lambda x, r, k: pine(L, x, ROAD0, 14 + r * 14, '#ffffff', '#ffffff'), w=W)
    stamp(c, L, line_only=(LINE, BG1))
    def pole(x, r, k):
        c.rect(x, 96, 1, ROAD0 - 96, LINE); c.rect(x - 4, 99, 9, 1, LINE)
        for d in (-4, 4):
            for i in range(54): c.px(x + d + i, 100 + math.sin(i / 54 * math.pi) * 5, LINE)
    scroll(s, 54, 17, pole)
    c.rect(0, ROAD0, W, ROAD1 - ROAD0, BG1); c.rect(0, ROAD0, W, 1, LINE); c.rect(0, ROAD1 - 1, W, 1, LINE)
    scroll(s, 26, 3, lambda x, r, k: c.rect(x, (ROAD0 + ROAD1) // 2, 10, 1, LINE))
    for y in range(ROAD1 + 4, H, 6):                                   # hatched ground
        scroll(s * (1 + (y - ROAD1) / 60), 9, y, lambda x, r, k: c.line(x, y, x + 3, y - 3, LINE) if r > .3 else None)
    b = -1 if math.sin(t * 9) + math.sin(t * 5.3) > 1.5 else 0
    tmp = C(); Lc = draw_car(tmp, CARX, CARY + b, t, (1, 1, 1), [], False)
    lum = tmp.a.sum(2)
    det = Lc.m & ((np.abs(lum - np.roll(lum, 1, 0)) > 120) | (np.abs(lum - np.roll(lum, 1, 1)) > 120))
    c.a[Lc.m] = col(BG1); c.a[edge_in(Lc.m) | det] = col(LINE)
    for i in range(6):                                                 # speed lines
        ph = (t * 3 + i / 6) % 1; y = CARY + 2 + i * 2
        c.rect(CARX - 6 - ph * 50, y, 6 + i % 3 * 3, 1, LINE)
    return c.a


# ---------------------------------------------------------------- 08 TOP-DOWN  (camera above, road scrolls vertically)
TOP_CAR = ["...YRRRRRRY...", "..RRhhhhhhRR..", ".RhhhhhhhhhhR.", ".RRRRRRRRRRRR.", "kRRRRRRRRRRRRk",
           "kRwwwwwwwwwwRk", "kRwWwwwwwwwwRk", "RRwwwwwwwwwwRR", ".RRhhhhhhhhRR.", ".RRhhhhhhhhRR.",
           ".RRhkhhhhkhRR.", ".RRhhhhhhhhRR.", ".RRhkhhhhkhRR.", ".RRhhhhhhhhRR.", ".RwwwwwwwwwwR.",
           ".RwwwwwwwwwwR.", "kRRRRRRRRRRRRk", "kRRRRRRRRRRRRk", "kRrrrrrrrrrrRk", ".LrrrrrrrrrrL."]
TOPPAL = P(R='#c8503c', h='#f08a68', r='#8e3430', k='#1a1820', w='#3a5a6e', W='#a8d0e0', Y='#fff6c8', L='#ff3a3a')
BLUEPAL = P(R='#3a6ad0', h='#7aa4f0', r='#24448e', k='#1a1820', w='#2a3a5a', W='#a8d0e0', Y='#fff6c8', L='#ff3a3a')


def st_top(t):
    c = C(); s = t * 130
    gy = c.ys
    wy = ((gy - s) // 1) % 260
    river = (wy > 150) & (wy < 186)
    grass = np.where(((c.xs // 6 + (gy - s.__floor__()) // 6) % 2) == 0, 0, 1)
    c.a[:] = np.where(grass[..., None] == 0, col('#56a844'), col('#4c9a3c'))
    c.a[river] = col('#2e78b8')
    rip = river & (((c.xs + (gy - s) * 0 + (t * 20)) % 9 < 1.2) & (gy % 5 == 0))
    c.a[rip] = col('#8ac8f0')
    c.a[river & ((wy == 151) | (wy == 185))] = col('#d8c890')
    c.rect(30, 0, 48, H, '#5a5a66'); c.rect(30, 0, 2, H, '#f0f0f0'); c.rect(76, 0, 2, H, '#f0f0f0')
    for y in range(H):
        if ((y - s) % 24) < 12: c.px(54, y, '#f6d24a'); c.px(53, y, '#f6d24a')
        if river[y, 0]: c.px(28, y, '#8a6a4a'); c.px(79, y, '#8a6a4a'); c.px(27, y, '#5a4030'); c.px(80, y, '#5a4030')
    for i in range(30):
        y = (hr(i, 3) * 400 + s) % 400 - 100; x = 33 + hr(i, 4) * 42; c.px(x, y, '#666672')
    def tree(y, r, k, x):
        if river[int(min(H - 1, max(0, y))), 0]: return
        rr = 5 + r * 4
        c.disc(x + 3, y + 3, rr, '#3a7030'); c.disc(x, y, rr, '#2e8a34'); c.disc(x - 1.5, y - 1.5, rr * .65, '#46a83e')
        c.disc(x - 2.5, y - 2.5, rr * .3, '#7ad060')
    for side, x0 in ((0, 12), (1, 96)):
        for k in range(-2, 12):
            y = k * 26 - (-s % 26) + side * 13 - 26
            kk = k + int(s // 26)
            if hr(kk, side + 5) > .35: tree(y, hr(kk, side + 7), kk, x0 + (hr(kk, side + 9) - .5) * 14)
    oy = (t * 260) % 700 - 200
    if -30 < oy < H:
        flip = [row[::-1] for row in TOP_CAR[::-1]]
        c.rect(37, oy + 2, 14, 20, '#46464e'); c.spr(35, oy, flip, BLUEPAL)
    b = int(math.sin(t * 9) + math.sin(t * 5.3) > 1.5)
    c.rect(60, 122, 14, 20, '#46464e')
    c.spr(58, 120 + b, TOP_CAR, TOPPAL)
    return c.a


# ---------------------------------------------------------------- 09 ISOMETRIC  (2:1 iso, voxel-ish boxes)
IK, IOX, IOY = 1.6, 50, 104


def iso(X, Y, Z): return (IOX + (X - Y) * IK, IOY + ((X + Y) / 2 - Z) * IK)


def ibox(c, X, Y, Z, dx, dy, dz, top, left, right):
    c.poly([iso(X, Y + dy, Z), iso(X + dx, Y + dy, Z), iso(X + dx, Y + dy, Z + dz), iso(X, Y + dy, Z + dz)], left)
    c.poly([iso(X + dx, Y, Z), iso(X + dx, Y + dy, Z), iso(X + dx, Y + dy, Z + dz), iso(X + dx, Y, Z + dz)], right)
    c.poly([iso(X, Y, Z + dz), iso(X + dx, Y, Z + dz), iso(X + dx, Y + dy, Z + dz), iso(X, Y + dy, Z + dz)], top)


def i_tree(c, X, Y):
    c.poly([iso(X - 2, Y + 2, 0), iso(X + 9, Y + 2, 0), iso(X + 9, Y + 9, 0), iso(X - 2, Y + 9, 0)], '#3a6a2e')
    ibox(c, X + 2, Y + 2, 0, 2, 2, 6, '#8a5a3a', '#6a4028', '#4e2e1e')
    ibox(c, X, Y, 6, 6, 6, 5, '#7ac85a', '#4a9a3a', '#3a7a2e')
    ibox(c, X + 1, Y + 1, 11, 4, 4, 3, '#9ae070', '#5aae44', '#448a36')


def i_house(c, X, Y, k):
    wall, wl, wr = [('#f0e0c8', '#e0c8a8', '#c8ac8a'), ('#c8e0f0', '#a8c8e0', '#8aacc8'), ('#f0c8c8', '#e0a8a8', '#c88a8a')][k % 3]
    ibox(c, X, Y, 0, 14, 12, 10, wall, wl, wr)
    for wx in (3, 9):
        c.poly([iso(X + wx, Y + 12, 4), iso(X + wx + 2.5, Y + 12, 4), iso(X + wx + 2.5, Y + 12, 7), iso(X + wx, Y + 12, 7)], '#4a6a8a')
    c.poly([iso(X + 14, Y + 4, 0), iso(X + 14, Y + 7, 0), iso(X + 14, Y + 7, 6), iso(X + 14, Y + 4, 6)], '#6a4a3a')
    ym = Y + 6
    c.poly([iso(X - 1, Y + 13, 10), iso(X + 15, Y + 13, 10), iso(X + 15, ym, 16), iso(X - 1, ym, 16)], '#c84a3a')
    c.poly([iso(X + 15, Y - 1, 10), iso(X + 15, Y + 13, 10), iso(X + 15, ym, 16)], wr)
    c.poly([iso(X - 1, ym, 16), iso(X + 15, ym, 16), iso(X + 15, ym - .6, 16), iso(X - 1, ym - .6, 16)], '#e86a50')


def i_car(c, t, bz):
    X, Y = 0, 0
    c.poly([iso(-1, 0, 0), iso(23, 0, 0), iso(23, 13, 0), iso(-1, 13, 0)], '#3a3a40')
    ibox(c, X, Y, 2 + bz, 22, 11, 5, '#e86a50', '#c8503c', '#a83e30')
    ibox(c, X + 5, Y + 1, 7 + bz, 11, 9, 4, '#e86a50', '#c8503c', '#a83e30')
    c.poly([iso(6, 10, 7.6 + bz), iso(10, 10, 7.6 + bz), iso(10, 10, 10.4 + bz), iso(6, 10, 10.4 + bz)], '#8ac0d8')
    c.poly([iso(11, 10, 7.6 + bz), iso(15, 10, 7.6 + bz), iso(15, 10, 10.4 + bz), iso(11, 10, 10.4 + bz)], '#8ac0d8')
    c.poly([iso(16, 2, 7.6 + bz), iso(16, 9, 7.6 + bz), iso(16, 9, 10.4 + bz), iso(16, 2, 10.4 + bz)], '#b8e0f0')
    c.poly([iso(0, 11, 4.2 + bz), iso(22, 11, 4.2 + bz), iso(22, 11, 4.8 + bz), iso(0, 11, 4.8 + bz)], '#f6d8a8')
    for wx in (5, 17):
        pts = [iso(wx + 2.6 * math.cos(a), 11.1, 2.4 + 2.6 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 14)]
        c.poly(pts, '#1c1a20')
        a = t * 14; c.px(*iso(wx + 1.2 * math.cos(a), 11.2, 2.4 + 1.2 * math.sin(a)), '#9aa0a8')
    for yy in (1.5, 8.5):
        c.poly([iso(22, yy, 4.5 + bz), iso(22, yy + 1.5, 4.5 + bz), iso(22, yy + 1.5, 5.6 + bz), iso(22, yy, 5.6 + bz)], '#fff6c8')


def st_iso(t):
    c = C(); s = t * 18
    u = (c.xs - IOX) / IK; v = 2 * (c.ys - IOY) / IK
    Xw = (u + v) / 2 + s; Y = (v - u) / 2
    chk = ((np.floor(Xw / 8) + np.floor(Y / 8)) % 2).astype(bool)
    a = np.where(chk[..., None], col('#78c050'), col('#6ab448'))
    side = ((Y > -11) & (Y < -5)) | ((Y > 18) & (Y < 24))
    a[side] = np.where(((np.floor(Xw / 4) + np.floor(Y / 4)) % 2).astype(bool)[side][:, None], col('#e8d8b8'), col('#dccaa8'))
    a[((Y >= -5) & (Y < -4)) | ((Y >= 17) & (Y < 18))] = col('#f4f0e8')
    road = (Y >= -4) & (Y < 17); a[road] = col('#5a5a66')
    a[road & (np.abs(Y - 6.5) < .5) & ((Xw % 14) < 7)] = col('#f6e6a0')
    c.a[:] = a
    objs = []
    for k in range(int(s // 30) - 3, int(s // 30) + 6):
        X = k * 30 - s
        if hr(k, 3) > .3: objs.append((X - 30 + 6, lambda X=X: i_house(c, X - 30, -36, k)))
        objs.append((X + 10 - 16 + 3, lambda X=X: i_tree(c, X + 10, -16)))
        if hr(k, 5) > .45: objs.append((X + 4 + 28 + 3, lambda X=X: i_tree(c, X + 4, 28)))
        if hr(k, 7) > .4: objs.append((X + 18 + 40 + 6, lambda X=X, k=k: i_house(c, X + 18, 34, k + 1)))
        objs.append((X + 22 - 8, lambda X=X: ibox(c, X + 22, -8, 0, 1, 1, 12, '#c8c8d0', '#9a9aa8', '#7a7a88')))
    bz = .6 if math.sin(t * 9) + math.sin(t * 5.3) > 1.5 else 0
    objs.append((0 + 11 + 6, lambda: i_car(c, t, bz)))
    for _, fn in sorted(objs, key=lambda o: o[0]): fn()
    return c.a


# ---------------------------------------------------------------- 10 RACER 3D  (behind-the-car pseudo-3D road)
REAR = ["........RRRRRRRRRRRR........", ".......RwwwwwwwwwwwwR.......", "......RwwwwwwwwwwwwwwR......",
        ".....RwwwwwwwwwwwwwwwwR.....", ".....RRRRRRRRRRRRRRRRRR.....", "..RRRRRRRRRRRRRRRRRRRRRRRR..",
        ".RhhhhhhhhhhhhhhhhhhhhhhhhR.", "RLLLLRRRRRRRRRRRRRRRRRRLLLLR", "RLLLLRRRRRRccccccRRRRRRLLLLR",
        "RRRRRRRRRRRccccccRRRRRRRRRRR", "rrrrrrrrrrrrrrrrrrrrrrrrrrrr", "kkkkkkkkkkkkkkkkkkkkkkkkkkkk",
        "kkkk....................kkkk", "kkkk....................kkkk"]
RHZ = 96


def st_racer(t):
    c = C(); sp = 16
    cv = .9 * math.sin(t * .55 + .6)
    c.grad(0, RHZ, ['#1a2a6a', '#4a3a8a', '#a04a8a', '#f07a7a', '#ffb070', '#ffe0a0'])
    c.disc(54 - cv * 30, 82, 20, '#fff2c0', ymax=RHZ); c.glow(54 - cv * 30, 86, 50, '#ffc890', .35, 20)
    ridge(c, cv * 60 + t * 2, RHZ, 12, .05, '#6a3a7a', 4, RHZ + 1, '#c86a8a')
    ridge(c, cv * 120 + t * 4, RHZ, 6, .09, '#3a2456', 8, RHZ + 1)
    def center(p): return 54 + cv * 38 * (1 - p) ** 2 - cv * 4
    for y in range(RHZ, H):
        p = (y - RHZ + 1) / (H - RHZ); z = 1 / p
        band = int(z * 2.2 + t * sp) % 2
        cx = center(p); hw = 3 + p * 74; rb = hw * .14
        c.rect(0, y, W, 1, '#4aa04a' if band else '#3e8e40')
        c.rect(cx - hw - rb, y, hw * 2 + rb * 2, 1, '#f4f4f4' if band else '#d83a3a')
        c.rect(cx - hw, y, hw * 2, 1, '#6a6a74' if band else '#62626c')
        if band: c.rect(cx - hw * .03, y, max(1, hw * .06), 1, '#f4f4f4')
    objs = []
    for i in range(16):
        z = (i * 1.3 - t * sp / 2.2 * 1.3 / 1.3) % (16 * 1.3) + .6
        p = 1 / z
        if p > 1: continue
        y = RHZ - 1 + p * (H - RHZ); side = 1 if i % 2 else -1
        x = center(p) + side * (3 + p * 74) * 1.5
        objs.append((p, x, y, i))
    for p, x, y, i in sorted(objs):
        h = 70 * p
        if i % 4 < 2:
            c.line(x, y, x + 6 * p * (1 if i % 3 else -1), y - h, '#6a4a3a'); c.line(x + 1, y, x + 1 + 6 * p, y - h, '#4a3428')
            tx, ty = x + 6 * p, y - h
            for k in range(6):
                ang = -math.pi * .9 + k * .55
                for d in range(int(22 * p) + 1):
                    c.px(tx + math.cos(ang) * d, ty + math.sin(ang) * d + d * d * .03 / max(p, .2), '#2e7a4a' if d % 2 else '#4aa060')
        else:
            c.rect(x - 1, y - h * .5, max(1, 2 * p), h * .5, '#8a8a96')
            c.rect(x - 14 * p, y - h * .8, 28 * p, 12 * p, '#2a6ad0'); c.rect(x - 12 * p, y - h * .8 + 4 * p, 24 * p, max(1, 2 * p), '#f4f4f4')
    sway = int(round(-cv * 3)); b = -1 if math.sin(t * 9) + math.sin(t * 5.3) > 1.5 else 0
    cx = 40 + sway
    c.glow(54 + sway, 175, 20, '#20202a', .6, 3)
    c.spr(cx, 160 + b, REAR, P(R='#c8503c', h='#f08a68', r='#8e3430', k='#1a1820', w='#2a3a4e', L='#ff4a4a', c='#f0e8d0'))
    c.glow(cx + 3, 168 + b, 6, '#ff4a4a', .35); c.glow(cx + 25, 168 + b, 6, '#ff4a4a', .35)
    for i in range(4):
        ph = (t * 3 + i / 4) % 1
        c.disc(cx + 3 - ph * 3, 173 + b + ph * 4, 1 + ph * 3, '#c8c0c8' if ph < .5 else '#9a92a0')
    return c.a


STYLES = [('PICO TINY', st_pico), ('CHUNKY 8-BIT', st_chunky), ('CLASSIC 16-BIT', st_classic),
          ('SOFT CINEMATIC', st_soft), ('HD PIXEL', st_hd), ('FLAT MINIMAL', st_flat), ('1-BIT LINE ART', st_line),
          ('TOP-DOWN', st_top), ('ISOMETRIC', st_iso), ('RACER 3D', st_racer)]
DUR = SEGD * len(STYLES)
OW, OH = 1080, 1920


def big(k, t):
    a = STYLES[k][1](t)
    sc = OW // a.shape[1]
    return np.repeat(np.repeat(np.clip(a, 0, 255), sc, 0), sc, 1)


def label(img, k, lt):
    num, name = f'{k + 1:02d}', STYLES[k][0]
    shown = name[:max(0, int(lt * 22))]
    L = C(layer=True)
    def text(s, x, y, colr):
        for ch in s:
            g = FONT[ch]
            for j, row in enumerate(g):
                for i, b_ in enumerate(row):
                    if b_ == '1': L.px(x + i, y + j, colr)
            x += len(g[0]) + 1
    nx = (W - text_width(num)) // 2; x0 = (W - text_width(name)) // 2
    text(num, nx + 1, 15, '#000000'); text(num, nx, 14, '#ffd36a')
    if shown: text(shown, x0 + 1, 25, '#000000'); text(shown, x0, 24, '#ffffff')
    img[120:330] = img[120:330] * .55
    m = np.repeat(np.repeat(L.m, 10, 0), 10, 1); a = np.repeat(np.repeat(L.a, 10, 0), 10, 1)
    img[m] = a[m]
    return img


def frame(t):
    k = min(len(STYLES) - 1, int(t // SEGD)); lt = t - k * SEGD
    a = big(k, t)
    if k < len(STYLES) - 1 and lt > SEGD - .3:            # chunky pixel dissolve into the next style
        f = (lt - (SEGD - .3)) / .3
        b = big(k + 1, t)
        gy, gx = np.mgrid[0:OH // 60, 0:OW // 60]
        m = np.repeat(np.repeat(BAYER[gy % 4, gx % 4] < f, 60, 0), 60, 1)[..., None]
        a = np.where(m, b, a)
    a = label(a.astype(np.float32), k, lt)
    a = a * max(0, min(1, t / .4, (DUR - t) / .6))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------- audio: engine + lo-fi chiptune bed + per-style ambience ----------------
def audio(path):
    n = int(SR * DUR); tt = np.arange(n) / SR; r = np.random.default_rng(3); noise = r.standard_normal(n)
    lp = lambda x, k: np.convolve(x, np.ones(k) / k, 'same')
    seg = lambda i: np.clip(np.minimum((tt - i * SEGD + .3) / .3, (i * SEGD + SEGD + .3 - tt) / .3), 0, 1)
    ph = np.cumsum(52 + 3 * np.sin(tt * .7)) / SR
    engine = lp(np.sin(2 * np.pi * ph) * .5 + np.sign(np.sin(4 * np.pi * ph)) * .08, 12) * .12 + lp(noise, 60) * .2
    amb = (lp(noise, 3) * .05 * seg(0) + lp(noise, 120) * .8 * (seg(1) + seg(4)) + lp(noise, 300) * 1.3 * (seg(6) + seg(9))
           + lp(noise, 90) * (1 + np.sin(tt * 1.3)) * .9 * seg(8))
    whoosh = sum(lp(noise, 16) * np.exp(-((tt - b * SEGD) / .3) ** 2) * .6 for b in range(1, len(STYLES)))
    tri = lambda f: 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * tt))
    sq = lambda f: np.sign(np.sin(2 * np.pi * f * tt))
    music = np.zeros(n); beat = .25
    chords = [(220, 277.2, 329.6), (185, 233.1, 277.2), (146.8, 185, 220), (164.8, 207.7, 246.9)]
    for i in range(int(DUR / beat)):
        s0 = i * beat; ch = chords[(i // 8) % 4]; f = ch[[0, 1, 2, 1, 2, 1, 0, 2][i % 8]] * 2
        m = (tt >= s0) & (tt < s0 + beat)
        lead = sq(f) * .35 if 4 <= (i * beat) // SEGD % 10 <= 4 or (i * beat) // SEGD in (3, 7) else tri(f)
        music[m] += lead[m] * np.exp(-(tt[m] - s0) * 7) * .05
        if i % 2 == 0: music[m] += (np.exp(-(tt[m] - s0) * 30) * np.sin(2 * np.pi * 55 * (tt[m] - s0))) * .12  # kick
        if i % 8 == 0:
            m2 = (tt >= s0) & (tt < s0 + beat * 8); music[m2] += tri(ch[0] / 2)[m2] * .03
    mix = engine + amb + whoosh + music
    mix *= np.clip(np.minimum(tt / .5, (DUR - tt) / .8), 0, 1)
    mix = np.clip(mix / max(1e-6, np.abs(mix).max()) * .8, -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.c_[mix, mix] * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: frame(float(s)).save(out / f'f_{s}.png')
    else:
        out = Path(sys.argv[2]); out.parent.mkdir(parents=True, exist_ok=True)
        wav = out.with_suffix('.wav'); audio(wav)
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                              '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-', '-i', str(wav),
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
                              '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out)],
                             stdin=subprocess.PIPE)
        for i in range(int(DUR * FPS)):
            p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
