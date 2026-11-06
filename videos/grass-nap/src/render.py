"""Grass-nap: seamless 1080x1920 pixel-art loop. Main guy + car buddy napping in a meadow.

python render.py still <t> <out.png>
python render.py video <out.mp4> [audio.wav] [seconds]
"""
import math
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageFilter

import sprites as S
import pix  # noqa: E402
from pix import hexc  # noqa: E402

W, H, SC = 180, 320, 6
FPS = 30
NFRAMES = 613
DUR = NFRAMES / FPS          # 20.433 s, same as the reference; every motion loops on DUR
BEATS = 32                   # music: 8 bars of 4/4 across DUR
BEAT = DUR / BEATS

RAMP = ['#143a37', '#1a4a40', '#225944', '#2c6447', '#386f49', '#447b48', '#548f44',
        '#6aa940', '#83c33f', '#9cd947', '#b2e957', '#c4f26c', '#d6f98a']
GROUNDS = {
    'green': RAMP,
    'autumn': ['#2e2a2c', '#3b2f2a', '#4c3829', '#5d4128', '#714b27', '#875626', '#9e6326',
               '#b5722a', '#c98630', '#d99b3a', '#e5ae47', '#eec05a', '#f5d274'],
}

GUY = (68, 150)
BUDDY = (130, 183)
PLAYER = (114, 133)
HELMET = (60, 112)
MAG = (82, 184)


def tp(t, k=1):
    return 2 * math.pi * k * t / DUR


def noise(w, h, cell, seed):
    r = np.random.default_rng(seed).random((h // cell + 3, w // cell + 3))
    im = Image.fromarray((r * 255).astype(np.uint8)).resize(((w // cell + 3) * cell, (h // cell + 3) * cell), Image.BICUBIC)
    return np.asarray(im, np.float32)[cell:cell + h, cell:cell + w] / 255.0


def fbm(w, h, seed):
    return 0.5 * noise(w, h, 40, seed) + 0.3 * noise(w, h, 14, seed + 1) + 0.2 * noise(w, h, 5, seed + 2)


# ---------------------------------------------------------------- static layers

def light_field():
    """0 = deep tree shade, 1 = full sun. Same composition as the reference wallpaper."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    # diagonal shadow edge: from upper-left (x~22) sweeping to the lower-right (y~225)
    edge_y = 122 + 0.6 * x + 10 * np.sin(x / 13.0) + 6 * np.sin(x / 5.0)
    edge_x = 22 + 4 * np.sin(y / 11.0)
    d = np.minimum(edge_y - y, x - edge_x)               # >0 inside shade
    d = np.where(y < 72, np.minimum(d, (x - 8) * 0.6 + (72 - y) * 0.15), d)
    n = fbm(W, H, 7)
    L = 1 / (1 + np.exp((d + (n - 0.5) * 26) / 7.0))
    # sunny upper-left glade and bright bottom
    L = np.maximum(L, np.clip(1 - np.hypot(x / 70, y / 70), 0, 1) * 0.75)
    L = np.maximum(L, np.clip((y - 250) / 50, 0, 1) * 0.95)
    # darker under the trunk (top-right)
    L *= 1 - 0.35 * np.clip(1 - np.hypot((x - 175) / 70, (y - 30) / 90), 0, 1)
    L = 0.28 + 0.72 * L
    return np.clip(L, 0, 1), n


def _limb(g, pts, w0, w1, body, top, rim):
    n = len(pts) - 1
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for k in range(steps):
            u = (i + k / steps) / n
            x = x0 + (x1 - x0) * k / steps; y = y0 + (y1 - y0) * k / steps
            w = w0 + (w1 - w0) * u
            g.disc(x, y, w, body)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for k in range(steps):
            u = (i + k / steps) / n
            x = x0 + (x1 - x0) * k / steps; y = y0 + (y1 - y0) * k / steps
            w = w0 + (w1 - w0) * u
            g.disc(x - w * 0.35, y - w * 0.45, w * 0.45, top)
            g.px(int(x - w * 0.75), int(y + w * 0.55), rim)


def tree(img):
    g = S.Grid(W, H)
    rng = np.random.default_rng(3)
    # trunk down the right side, roots fanning into the grass
    _limb(g, [(176, -4), (168, 40), (160, 80), (150, 108)], 16, 4, '#0d1d1a', '#152b25', '#2fd39a')
    _limb(g, [(176, 60), (172, 95), (166, 120)], 9, 2, '#0d1d1a', '#152b25', '#2fd39a')
    _limb(g, [(158, 70), (145, 90), (137, 104)], 5, 1.5, '#0d1d1a', '#152b25', '#2fd39a')
    # big mossy limb sweeping in from the top-left
    _limb(g, [(-10, 12), (28, 14), (66, 24), (100, 42), (122, 66)], 15, 5, '#28382a', '#465a36', '#7ff0b0')
    _limb(g, [(156, -6), (144, 22), (130, 52)], 9, 3, '#17271f', '#2a4031', '#3fe0a6')
    # bark grooves on the limb
    for k in range(4):
        for x in range(0, 118):
            y = 12 + x * 0.12 + (x / 118) ** 2 * 45 - 6 + k * 3 + math.sin(x / 7 + k) * 1.2
            if (x + k * 9) % 17 < 10 and g.g[int(y)][x] is not None:
                g.px(x, int(y), '#1e2c22' if k % 2 else '#3a4d30')
    # bark grooves
    for k in range(5):
        for y in range(0, 95):
            x = int(172 - y * 0.18 + k * 3 - 6 + 1.5 * math.sin((y + k * 4) / 6))
            if (y + k * 7) % 19 < 11 and g.g[min(H - 1, y)][min(W - 1, x)] is not None:
                g.px(x, y, '#1b3a31')
    # glowing teal leaves + moss clumps
    for _ in range(55):
        x = int(rng.integers(60, 160)); y = int(rng.integers(0, 24))
        c = ['#2fd3a8', '#62f0d6', '#1f9a7a', '#7cf7a0'][int(rng.integers(0, 4))]
        g.px(x, y, c)
        if rng.random() < 0.5:
            g.px(x + 1, y, c); g.px(x, y + 1, c)
    for _ in range(25):
        x = int(rng.integers(0, 110)); y = int(rng.integers(2, 16))
        if g.g[y][x] is not None:
            g.px(x, y, '#6f8c3e')
    img.alpha_composite(g.image(outline=True, oc=(10, 22, 18, 255)))


FLOWER_KINDS = ('daisy', 'butter', 'puff', 'violet', 'clover')


@lru_cache(None)
def flower_head(kind):
    g = S.Grid(13, 13)
    if kind == 'daisy':
        for (cx, cy) in ((6, 2.5), (9.3, 4.8), (8.2, 8.6), (3.8, 8.6), (2.7, 4.8)):
            g.disc(cx, cy, 2.1, '#fbfdf6')
        g.disc(6, 6, 2.6, '#fbfdf6')
        for (cx, cy) in ((8.2, 8.6), (3.8, 8.6)):
            g.px(int(cx), int(cy) + 1, '#d3e2c4')
        g.disc(6, 6, 1.6, '#ffd34d'); g.px(6, 6, '#f2a93b'); g.px(7, 7, '#f2a93b'); g.px(5, 5, '#fff3a6')
    elif kind == 'butter':
        for (cx, cy) in ((6, 3), (9, 5.5), (7.8, 8.8), (4.2, 8.8), (3, 5.5)):
            g.disc(cx, cy, 1.7, '#ffd84a')
        g.disc(6, 6.4, 2, '#ffd84a'); g.px(6, 6, '#f59b2b'); g.px(5, 5, '#fff3a8'); g.px(6, 3, '#fff3a8')
        g.px(8, 9, '#f0b23a'); g.px(4, 9, '#f0b23a')
    elif kind == 'puff':
        g.disc(6, 6, 3.6, '#d7f2b0'); g.disc(6, 6, 2.4, '#effcd8'); g.disc(5.5, 5.5, 1.1, '#ffffff')
    elif kind == 'violet':
        for (cx, cy) in ((6, 4), (8, 6), (6, 8), (4, 6)):
            g.disc(cx, cy, 1.3, '#b7a6ff')
        g.px(6, 6, '#fff3a0'); g.px(6, 3, '#e0d8ff'); g.px(7, 8, '#8f7de6'); g.px(5, 8, '#8f7de6')
    else:  # sprig: a little three-blade grass sprout
        for (x, y) in ((6, 4), (6, 5), (6, 6), (6, 7), (6, 8), (4, 6), (5, 7), (8, 5), (7, 7), (3, 5), (9, 4)):
            g.px(x, y, '#4fb447')
        g.px(6, 3, '#8be070'); g.px(3, 4, '#8be070'); g.px(9, 3, '#8be070')
        return g.image(outline=False)
    return g.image(outline=True, oc=(24, 70, 38, 255))


def plant_base(g, x, y, kind, rng, dark):
    leaf = '#2d8a3a' if not dark else '#1f5e38'
    leafhi = '#5ec24c' if not dark else '#32804c'
    if kind == 'clover':
        return
    g.rect(x, y, x, y + 5, leaf)
    for s in (-1, 1):
        if rng.random() < 0.85:
            for i in range(5):
                lx = x + s * (1 + i); ly = y + 4 - (1 if 1 <= i <= 3 else 0)
                g.px(lx, ly, leaf); g.px(lx, ly + 1, leaf)
                if 1 <= i <= 3: g.px(lx, ly - 1, leafhi if i == 2 else leaf)


@lru_cache(None)
def layout(ground='green'):
    """Background (static) + list of animated flower heads."""
    ramp = GROUNDS[ground]
    L, n = light_field()
    rng = np.random.default_rng(11)
    lv = L + (fbm(W, H, 21) - 0.5) * 0.18
    idx = np.clip((lv * (len(ramp) - 1)).round().astype(int), 0, len(ramp) - 1)
    patch = (noise(W, H, 9, 31) * 0.6 + noise(W, H, 4, 32) * 0.4) > 0.66      # darker grass clumps
    idx = np.where(patch & (L > 0.55), idx - 2, idx)
    idx = np.clip(idx, 0, len(ramp) - 1)
    rgb = np.array([hexc(c)[:3] for c in ramp], np.uint8)[idx]
    bg = Image.fromarray(rgb, 'RGB').convert('RGBA')
    g = S.Grid(W, H)
    # grass tufts and specks, coloured from the local ramp tone
    for _ in range(1800):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        i = int(idx[y, x])
        up = ramp[min(len(ramp) - 1, i + 1)]; dn = ramp[max(0, i - 1)]
        r = rng.random()
        if r < 0.45:
            g.px(x, y, up); g.px(x - 1, y - 1, up); g.px(x + 1, y - 1, up)
        elif r < 0.8:
            g.px(x, y, dn); g.px(x + 1, y, dn)
        else:
            g.px(x, y, up)
    for _ in range(700):                                    # bright pollen specks in the sun
        x, y = int(rng.integers(0, W)), int(rng.integers(120, H))
        if L[y, x] > 0.75:
            g.px(x, y, '#effbd0')
    bg.alpha_composite(g.image(outline=False))
    tree(bg)
    # pebbles / crystals
    g = S.Grid(W, H)
    for (x, y, c) in ((80, 38, '#b69ad6'), (68, 52, '#9c84c4'), (143, 263, '#d6b8f0'), (128, 266, '#c6a8e8'), (157, 316, '#c7a9ec')):
        g.rect(x - 4, y - 2, x + 4, y + 2, c); g.rect(x - 3, y - 3, x + 3, y + 3, c)
        g.rect(x - 2, y - 2, x + 1, y - 1, '#efe3ff'); g.rect(x - 3, y + 2, x + 3, y + 3, '#7d6aa8')
    bg.alpha_composite(g.image(outline=True, oc=(40, 60, 50, 255)))
    # flowers: denser in the sun, avoiding the nappers
    keep = [(GUY, 34), (BUDDY, 30), (PLAYER, 18), (HELMET, 16), (MAG, 18)]
    heads = []
    stems = S.Grid(W, H)
    tries = 0
    centers = [(int(rng.integers(0, W)), int(rng.integers(20, H))) for _ in range(26)]
    while len(heads) < 70 and tries < 40000:
        tries += 1
        cx0, cy0 = centers[int(rng.integers(0, len(centers)))]
        x, y = int(cx0 + rng.normal(0, 13)), int(cy0 + rng.normal(0, 10))
        if not (4 <= x < W - 4 and 8 <= y < H - 4):
            continue
        if x > 128 + y * 0.2 and y < 125:
            continue
        if any(math.hypot(x - cx, y - cy) < r for (cx, cy), r in keep):
            continue
        if any(abs(x - hx) < 11 and abs(y - hy) < 11 for hx, hy, *_ in heads):
            continue
        lt = L[y, x]
        if rng.random() > 0.18 + 0.82 * lt:
            continue
        r = rng.random()
        if lt < 0.5:
            kind = 'violet' if r < 0.35 else 'butter' if r < 0.6 else 'daisy' if r < 0.8 else 'clover'
        else:
            kind = 'daisy' if r < 0.4 else 'butter' if r < 0.62 else 'puff' if r < 0.78 else 'clover'
        plant_base(stems, x, y + 4, kind, rng, lt < 0.5)
        heads.append((x, y, kind, float(rng.random()), lt < 0.4))
    bg.alpha_composite(stems.image(outline=False))
    return bg, heads, L


# ---------------------------------------------------------------- dynamic pieces

def wind(t, x, y):
    tq = math.floor(t * 10) / 10                         # pixel-art 10 fps sway
    gust = 0.55 + 0.45 * math.sin(tp(tq, 3) + 1.0)
    return round(1.15 * gust * math.sin(tp(tq, 9) - x * 0.05 - y * 0.02))


def dapple(t):
    """Hard-edged sun flecks dropping through the leaves (native-res mask)."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    a = tp(t, 2); b = tp(t, 3)
    f = (np.sin(x * 0.13 + 1.6 * math.sin(a) + y * 0.05) * np.sin(y * 0.11 - 1.2 * math.cos(b) + x * 0.04)
         + 0.6 * np.sin((x + y) * 0.07 + 1.3 * math.sin(a + 1)))
    return f > 0.95


@lru_cache(None)
def static_shadowed(ground='green'):
    """Background with soft contact shadows under the sprites."""
    bg, heads, L = layout(ground)
    a = np.asarray(bg, np.float32).copy()
    for spr, (cx, cy), k in ((S.guy_lying(), GUY, 0.62), (S.car_buddy(-15), BUDDY, 0.6),
                             (S.walkman(0), PLAYER, 0.7), (S.helmet(), HELMET, 0.66), (S.magazine(0), MAG, 0.75)):
        m = np.asarray(spr)[..., 3] > 0
        x0 = cx - spr.width // 2 + 2; y0 = cy - spr.height // 2 + 2
        for dy in range(m.shape[0]):
            for dx in range(m.shape[1]):
                if m[dy, dx] and 0 <= y0 + dy < H and 0 <= x0 + dx < W:
                    a[y0 + dy, x0 + dx, :3] *= k
    return Image.fromarray(a.astype(np.uint8), 'RGBA'), heads, L


def place(img, spr, c):
    img.alpha_composite(spr, (c[0] - spr.width // 2, c[1] - spr.height // 2))


def cable(img, a, b, t):
    g = S.Grid(W, H)
    n = 40
    for i in range(n + 1):
        u = i / n
        x = a[0] + (b[0] - a[0]) * u + 5 * math.sin(u * math.pi) + 2 * math.sin(u * 7)
        y = a[1] + (b[1] - a[1]) * u + 4 * math.sin(u * math.pi * 2)
        g.px(int(round(x)), int(round(y)), '#18231f')
    img.alpha_composite(g.image(outline=False))


def ear_point(spr, c):
    a = np.asarray(spr)
    ys, xs = np.where(np.all(a[..., :3] == hexc(S.CUP)[:3], axis=2))
    i = np.argmax(xs + ys * 0.3)
    return (c[0] - spr.width // 2 + int(xs[i]) + 1, c[1] - spr.height // 2 + int(ys[i]))


FLIPS = (2.2, 8.9, 14.6)
R = np.random.default_rng(5)
SPARK_LIST = [(float(R.uniform(0, DUR)), int(R.integers(4, W - 4)), int(R.integers(10, H - 6))) for _ in range(46)]
MOTES = [(float(R.uniform(0, 1)), float(R.uniform(0, 140)), float(R.uniform(0, 200)), int(R.integers(1, 3))) for _ in range(70)]
FALL = [(float(R.uniform(0, 1)), float(R.uniform(-30, W)), int(R.integers(1, 3)), float(R.uniform(0, 6.3))) for _ in range(22)]
FLIES = [(float(R.uniform(10, W - 10)), float(R.uniform(30, H - 20)), int(R.integers(1, 4)), int(R.integers(1, 4)), float(R.uniform(0, 6.3))) for _ in range(26)]
BFLY = [((150, 250), (26, 18), (2, 3), '#fff1a0', '#c99a2a'), ((40, 70), (30, 22), (3, 2), '#a8d8ff', '#4a7fc0')]

MOODS = {
    'day':    dict(ground='green', warm=(255, 212, 0), glow=0.85, rays=0.3, dap=(1.22, (18, 22, 4)), gain=(0.9, 0.98, 0.92),
                   lift=(0, 0, 0), sat=1.25, con=1.04, fall='petal', motes=26, bfly=2, clouds=0.13, night=0, title='SUNNY DAY'),
    'golden': dict(ground='green', warm=(255, 140, 30), glow=1.05, rays=0.6, dap=(1.25, (40, 18, 0)), gain=(1.08, 0.86, 0.72),
                   lift=(34, 4, 46), sat=1.18, con=1.14, fall='petal', motes=70, bfly=1, clouds=0.1, night=0, title='GOLDEN HOUR'),
    'autumn': dict(ground='autumn', warm=(255, 176, 60), glow=0.8, rays=0.35, dap=(1.2, (30, 18, 0)), gain=(1.0, 0.94, 0.86),
                   lift=(10, 0, 10), sat=1.12, con=1.1, fall='leaf', motes=20, bfly=0, clouds=0.14, night=0, title='AUTUMN'),
    'night':  dict(ground='green', warm=(110, 160, 255), glow=0.55, rays=0.2, dap=(1.15, (10, 22, 46)), gain=(0.2, 0.28, 0.5),
                   lift=(2, 6, 22), sat=0.85, con=1.1, fall=None, motes=0, bfly=0, clouds=0.0, night=1, title='NIGHT'),
}


def _put(a, x, y, c, k=1.0):
    if 0 <= x < W and 0 <= y < H:
        a[y, x, :3] = a[y, x, :3] * (1 - k) + np.array(c, np.float32) * k


def _shade(a, x, y, k=0.72):
    if 0 <= x < W and 0 <= y < H:
        a[y, x, :3] *= k


PETAL = [((0, 0), (1, 0), (0, 1)), ((0, 0), (1, 1)), ((0, 0), (1, 0)), ((1, 0), (0, 1))]
LEAF = [((1, 0), (0, 1), (1, 1), (2, 1), (1, 2)), ((0, 0), (1, 1), (2, 2), (1, 0), (2, 1)), ((0, 1), (1, 1), (2, 1), (1, 0))]


def native(t, mood='day'):
    M = MOODS[mood]
    bg, heads, L = static_shadowed(M['ground'])
    img = bg.copy()
    for (x, y, kind, ph, dark) in heads:
        hd = flower_head(kind)
        dx = wind(t, x, y) if kind != 'clover' else wind(t, x, y) // 2
        img.alpha_composite(hd, (x - 6 + dx, y - 6))
    beat = (t / BEAT) % 1.0
    glow = 0.45 + 0.55 * math.exp(-beat * 3.5)
    spool = int(t * 8) % 6
    place(img, S.helmet(), HELMET)
    page = 0
    for f in FLIPS:
        k = int((t - f) / 0.1)
        if 0 <= k < 5:
            page = k + 1
    place(img, S.magazine(page), MAG)
    place(img, S.walkman(spool, round(glow, 1)), PLAYER)
    guy = S.guy_lying()
    place(img, guy, GUY)
    snore = 1 if (t % (DUR / 5)) / (DUR / 5) > 0.82 else 0
    place(img, S.car_buddy(-15, snore), BUDDY)
    wm = S.walkman(0)
    cable(img, ear_point(guy, GUY), (PLAYER[0] - wm.width // 2 + 0, PLAYER[1] + 12), t)
    a = np.asarray(img, np.float32).copy()
    m = dapple(t) & (L < 0.85)
    gk, add = M['dap']
    a[m, :3] = a[m, :3] * gk + np.array(add, np.float32)
    if not M['night']:
        for (t0, x, y) in SPARK_LIST:
            age = (t - t0) % DUR
            if age < 0.6:
                s = 1 if age < 0.15 or age > 0.45 else 2
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)) + ((((2, 0), (-2, 0), (0, 2), (0, -2)) if s == 2 else ())):
                    _put(a, x + dx, y + dy, (250, 255, 225) if (dx, dy) == (0, 0) or s == 1 else (205, 240, 170))
    warm_mote = (255, 236, 170) if mood != 'golden' else (255, 214, 140)
    for (ph, x0, y0, k) in MOTES[:M['motes']]:
        u = (t / DUR * k + ph) % 1.0
        x = int(x0 + 30 * u + 3 * math.sin(tp(t, 4) + ph * 6)) % W
        y = int(y0 + 50 * u) % 230
        if (int(t * 6 + ph * 10) % 5) != 0:
            _put(a, x, y, warm_mote, 0.9)
    # falling petals / leaves, with ground shadows that sell the height
    if M['fall']:
        shapes = PETAL if M['fall'] == 'petal' else LEAF
        cols = (((255, 214, 226), (255, 244, 248)) if M['fall'] == 'petal'
                else ((224, 96, 40), (240, 170, 50), (196, 60, 40)))
        for i, (ph, x0, k, wob) in enumerate(FALL):
            u = (t / DUR * k + ph) % 1.0
            x = int(x0 + 70 * u + 7 * math.sin(tp(t, 3 * k) + wob))
            y = int(-12 + (H + 24) * u)
            shp = shapes[(int(t * 8) + i) % len(shapes)]
            for (dx, dy) in shp:
                _shade(a, x + dx + 5, y + dy + 8, 0.74)
            for (dx, dy) in shp:
                _put(a, x + dx, y + dy, cols[i % len(cols)])
    for bi in range(M['bfly']):
        (cx, cy), (ax, ay), (k1, k2), c1, c2 = BFLY[bi]
        x = int(cx + ax * math.sin(tp(t, k1) + bi) + 4 * math.sin(tp(t, 11)))
        y = int(cy + ay * math.sin(tp(t, k2) + 0.7) + 2 * math.sin(tp(t, 23)))
        flap = int(t * 14) % 2
        wing = ((-2, -1), (-1, -1), (-2, 0), (-1, 0), (1, -1), (2, -1), (1, 0), (2, 0), (-1, 1), (1, 1)) if flap else ((-1, -1), (-1, 0), (1, -1), (1, 0))
        for (dx, dy) in wing + ((0, -1), (0, 0), (0, 1)):
            _shade(a, x + dx + 6, y + dy + 9, 0.72)
        for (dx, dy) in wing:
            _put(a, x + dx, y + dy, hexc(c1)[:3] if abs(dx) < 2 or not flap else hexc(c2)[:3])
        for dy in (-1, 0, 1):
            _put(a, x, y + dy, (40, 30, 30))
    if M['night']:
        for (x0, y0, k1, k2, ph) in FLIES:
            x = int(x0 + 9 * math.sin(tp(t, k1) + ph)); y = int(y0 + 7 * math.sin(tp(t, k2) + ph * 2))
            br = 0.5 + 0.5 * math.sin(tp(t, 5 + k1) + ph)
            if br > 0.25:
                _put(a, x, y, (236, 255, 140), min(1, br + 0.2))
    return np.clip(a[..., :3], 0, 255).astype(np.uint8)


@lru_cache(None)
def overlays():
    y, x = np.mgrid[0:1920, 0:1080].astype(np.float32)
    glow = np.clip(1 - np.hypot(x / 900, y / 820), 0, 1) ** 1.15                     # sun, top-left
    rays = (np.clip(np.sin((x * 0.8 - y * 0.6) / 70.0) * 0.5 + 0.5, 0, 1) ** 6
            + 0.6 * np.clip(np.sin((x * 0.8 - y * 0.6) / 37.0 + 1.3) * 0.5 + 0.5, 0, 1) ** 10) * np.clip(1 - np.hypot(x / 1300, y / 1250), 0, 1)
    vig = np.clip(np.hypot((x - 540) / 760, (y - 1010) / 1150), 0, 1) ** 2.2
    topshade = np.clip(1 - y / 900, 0, 1) * np.clip((x - 300) / 780, 0, 1)
    tilt = np.clip((np.abs(y - 980) - 560) / 380, 0, 1) ** 1.5                        # diorama depth of field
    return glow, rays, vig, topshade, tilt


def clouds(t):
    y, x = np.mgrid[0:60, 0:34].astype(np.float32)
    v = (np.sin(x * 0.21 + y * 0.07 - tp(t, 1)) + np.sin(x * 0.13 - y * 0.16 - tp(t, 2) + 1.7)
         + 0.6 * np.sin(y * 0.19 + x * 0.05 + tp(t, 1) + 0.4))
    m = np.clip((v - 0.6) / 1.2, 0, 1)
    m = m * m * (3 - 2 * m)
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((1080, 1920), Image.BICUBIC)
    return np.asarray(im, np.float32) / 255


def lightmap(t, M):
    """Additive local light (night): fireflies, LCD glow, fog lights. Quarter-res, blurred."""
    lm = np.zeros((480, 270, 3), np.float32)
    def splat(x, y, r, c, k):
        x, y = x * 1.5, y * 1.5
        r *= 1.5
        x0, x1 = int(max(0, x - 3 * r)), int(min(270, x + 3 * r)); y0, y1 = int(max(0, y - 3 * r)), int(min(480, y + 3 * r))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        lm[y0:y1, x0:x1] += np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (r * r))[..., None] * np.array(c, np.float32) * k
    beat = (t / BEAT) % 1.0
    splat(PLAYER[0], PLAYER[1] - 8, 16, (60, 230, 255), 0.55 + 0.45 * math.exp(-beat * 3.5))
    splat(BUDDY[0] - 12, BUDDY[1] + 9, 7, (255, 210, 110), 0.8)
    splat(BUDDY[0] + 13, BUDDY[1] + 3, 7, (255, 210, 110), 0.8)
    for (x0, y0, k1, k2, ph) in FLIES:
        x = x0 + 9 * math.sin(tp(t, k1) + ph); y = y0 + 7 * math.sin(tp(t, k2) + ph * 2)
        br = 0.5 + 0.5 * math.sin(tp(t, 5 + k1) + ph)
        splat(x, y, 4.5, (190, 255, 90), max(0, br - 0.15))
    return np.asarray(Image.fromarray(np.clip(lm, 0, 255).astype(np.uint8)).resize((1080, 1920), Image.BILINEAR), np.float32)


def frame(t, mood='day'):
    M = MOODS[mood]
    a = native(t, mood)
    big = a.repeat(SC, 0).repeat(SC, 1).astype(np.float32)
    glow, rays, vig, topshade, tilt = overlays()
    pulse = 1 + 0.03 * math.sin(tp(t, 7))
    warm = np.array(M['warm'], np.float32)
    k = (M['glow'] * glow + M['rays'] * rays * (0.75 + 0.25 * math.sin(tp(t, 2)))) * pulse
    big = big * (1 - k[..., None] * 0.55) + warm * k[..., None] * 0.55
    if M['clouds']:
        big *= (1 - M['clouds'] * clouds(t))[..., None]
    big *= (1 - 0.2 * vig - 0.12 * topshade)[..., None] * (1 + 0.025 * math.sin(tp(t, 7)))
    out = np.clip(big, 0, 255)
    im = Image.fromarray(out.astype(np.uint8))
    small = im.resize((270, 480), Image.BILINEAR)
    bl = np.asarray(small.filter(ImageFilter.GaussianBlur(6)).resize((1080, 1920), Image.BILINEAR), np.float32)
    soft = np.asarray(small.filter(ImageFilter.GaussianBlur(1.2)).resize((1080, 1920), Image.BILINEAR), np.float32)
    out = out + (soft - out) * (0.5 * tilt)[..., None]
    out = out * 0.86 + np.maximum(bl - 70, 0) * 0.34
    m = out.mean(2, keepdims=True)
    out = m + (out - m) * M['sat']
    out = 128 + (out - 128) * M['con']
    lum = np.clip(out.mean(2, keepdims=True) / 255, 0, 1)
    out = out * np.array(M['gain'], np.float32) + np.array(M['lift'], np.float32) * (1 - lum)
    if M['night']:
        out += lightmap(t, M) * 1.3
    g = np.random.default_rng(int(t * FPS)).standard_normal((480, 270)).astype(np.float32)
    out += np.asarray(Image.fromarray(((g * 20) + 128).clip(0, 255).astype(np.uint8)).resize((1080, 1920), Image.NEAREST), np.float32)[..., None] * 0.12 - 128 * 0.12
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- showcase reel

ORDER = ('day', 'golden', 'autumn', 'night')
SEG = DUR / 2
XF = 1.0


@lru_cache(None)
def title_img(text):
    tw = pix.text_width(text)
    g = S.Grid(tw + 4, 11)
    g.text(2, 2, text, '#fffaf0')
    im = g.image(outline=True, oc=(20, 30, 26, 255))
    return im.resize((im.width * 12, im.height * 12), Image.NEAREST)


def showcase_frame(t, titles=True):
    i = min(len(ORDER) - 1, int(t // SEG))
    f = frame(t, ORDER[i]).astype(np.float32)
    lt = t - i * SEG
    if i + 1 < len(ORDER) and lt > SEG - XF / 2:
        w = (lt - (SEG - XF / 2)) / XF
        f = f * (1 - w) + frame(t, ORDER[i + 1]) * w
    elif i > 0 and lt < XF / 2:
        w = 0.5 + lt / XF
        f = frame(t, ORDER[i - 1]) * (1 - w) + f * w
    ta = min(1, max(0, (lt - 0.7) / 0.4)) * min(1, max(0, (3.4 - lt) / 0.5))
    if ta > 0 and titles:
        ti = title_img(MOODS[ORDER[i]]['title'])
        arr = np.asarray(ti, np.float32)
        x0 = (1080 - ti.width) // 2; y0 = 1690
        al = arr[..., 3:4] / 255 * ta
        f[y0:y0 + ti.height, x0:x0 + ti.width] = f[y0:y0 + ti.height, x0:x0 + ti.width] * (1 - al) + arr[..., :3] * al
    return np.clip(f, 0, 255).astype(np.uint8)


DAYNIGHT = ((0.0, 'day'), (8.0, 'day'), (16.0, 'golden'), (23.0, 'golden'), (32.0, 'night'))   # time -> mood keys


def daynight_frame(t):
    """Sunny day slowly sinking into golden hour, then night (no text)."""
    for (t0, m0), (t1, m1) in zip(DAYNIGHT, DAYNIGHT[1:]):
        if t < t1:
            if m0 == m1:
                return frame(t, m0)
            w = (t - t0) / (t1 - t0)
            w = w * w * (3 - 2 * w)
            return np.clip(frame(t, m0) * (1 - w) + frame(t, m1).astype(np.float32) * w, 0, 255).astype(np.uint8)
    return frame(t, DAYNIGHT[-1][1])


def _work(args):
    kind, i = args
    t = i / FPS
    if kind == 'daynight':
        return daynight_frame(t).tobytes()
    return (frame(t, kind) if kind in MOODS else showcase_frame(t, kind != 'showcase_clean')).tobytes()


def video(path, audio=None, secs=DUR, kind='day'):
    from multiprocessing import Pool
    n = int(round(secs * FPS))
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920', '-r', str(FPS), '-i', '-']
    if audio:
        cmd += ['-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, buf in enumerate(pool.imap(_work, [(kind, i) for i in range(n)], chunksize=4)):
            p.stdin.write(buf)
            if i % 120 == 0:
                print(f'frame {i}/{n}', flush=True)
    p.stdin.close()
    sys.exit(p.wait())


if __name__ == '__main__':
    if sys.argv[1] == 'still':
        mood = sys.argv[4] if len(sys.argv) > 4 else 'day'
        t = float(sys.argv[2])
        f = showcase_frame(t) if mood == 'showcase' else daynight_frame(t) if mood == 'daynight' else frame(t, mood)
        Image.fromarray(f).save(sys.argv[3])
    elif sys.argv[1] == 'video':
        kind = sys.argv[5] if len(sys.argv) > 5 else 'day'
        video(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None,
              float(sys.argv[4]) if len(sys.argv) > 4 else DUR, kind)
