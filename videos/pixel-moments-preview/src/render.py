"""Original 10 s pixel-art mood piece: rainy bus stop -> dusk pier.
Usage: python render.py video OUT.mp4 | python render.py still OUTDIR t1 t2 ..."""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image

W = H = 216; S = 5; FPS = 30; DUR = 10.0; CUT = 5.0; SR = 44100
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def hx(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


class C:
    def __init__(s): s.a = np.zeros((H, W, 3), np.float32)
    def rect(s, x, y, w, h, c):
        x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h))
        if x1 > x0 and y1 > y0: s.a[y0:y1, x0:x1] = hx(c) if isinstance(c, str) else c
    def px(s, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H: s.a[y, x] = hx(c) if isinstance(c, str) else c
    def line(s, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / max(n, 1); s.px(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)
    def grad(s, y0, y1, cols, x0=0, x1=W):
        """Banded vertical gradient with 4x4 ordered dithering."""
        cols = [hx(c) for c in cols]; n = len(cols) - 1
        ys, xs = np.mgrid[y0:y1, x0:x1]
        t = (ys - y0) / max(1, y1 - y0 - 1) * n + BAYER[ys % 4, xs % 4] - .5
        idx = np.clip(np.round(t), 0, n).astype(int)
        s.a[y0:y1, x0:x1] = np.stack(cols)[idx]
    def glow(s, cx, cy, r, c, k=.55, ry=None):
        """Dithered additive-ish light pool (quantised to 3 steps)."""
        ry = ry or r; c = hx(c)
        ys, xs = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xs - cx) / r) ** 2 + ((ys - cy) / ry) ** 2)
        lv = np.clip(np.floor((1 - d) * 3 + BAYER[ys % 4, xs % 4]), 0, 3) / 3 * k
        s.a[:] = s.a * (1 - lv[..., None]) + c * lv[..., None]
    def spr(s, x, y, rows, pal, flip=False):
        for j, r in enumerate(rows):
            if flip: r = r[::-1]
            for i, ch in enumerate(r):
                if ch in pal: s.px(x + i, y + j, pal[ch])


# ---------- sprites (original) ----------
DAD = ["....hhhh....", "...hhhhhh...", "...hhhhgg...", "...hhhsgs...", "...hhssssk..",
       "....ssssk...", ".....sk.....", "...cccccc...", "..cccccccc..", "..ccccccCcs.",
       "..cccccCCcs.", "..cCccccC...", "..cCccccC...", "..cCccccC...", "..cCcccCC...",
       "..ccccccC...", "..scccccC...", "..scccccC...", "...cccccC...", "...ccccCC...",
       "...ccccCC...", "...pp..pp...", "...pp..pp...", "...pp..pp...", "...pp..pp...",
       "...pp..pp...", "...bb..bbb..", "..bbb..bbbb."]
KID = ["..yyyy..", ".yyyyyy.", ".yyssyy.", ".ysesy..", "..ssy...", ".yyyyyy.",
       "syyyyyY.", ".yyyyyY.", ".yyyyYY.", ".yyyYYY.", "..p..p..", "..p..p..",
       "..rr.rr.", ".rrr.rrr"]
DADP = {'h': '#1a1c24', 'g': '#6f8a92', 's': '#c98f6e', 'k': '#9a6450', 'e': '#2a2028',
        'c': '#2f4a3c', 'C': '#22362d', 'p': '#262a36', 'b': '#15161c'}
KIDP = {'y': '#e2b545', 'Y': '#b6862f', 's': '#e2a882', 'e': '#2a2028', 'p': '#2d3550', 'r': '#b2413e'}
# sitting, seen from behind-left, backlit at sunset
DADS = ["...hhhh...", "..hhhhhh..", "..hhhhhhk.", "..hhhhhhk.", "...hhhhs..", "...cccc...",
        ".cccccccc.", "cccccccccc", "cccCcccccc", "cccCcccccc", "cccCccccCc", ".ccCccccC.",
        ".ccCccccC.", ".cccccccc.", "pppppppppp", ".pp....pp.", ".pp....pp.", ".pp....pp.",
        ".bb....bb."]
KIDS = ["..hhhh..", ".hhhhhh.", ".hhhhhhk", "..hhhhs.", "..tttt..", ".tttttt.", "tttTtttt",
        "tttTtttt", ".ttTttt.", "pppppppp", ".pp..pp.", ".pp..pp.", ".rr..rr."]
DADSP = {'h': '#1b1a26', 'k': '#e7a48a', 's': '#a8655a', 'c': '#3a3348', 'C': '#2a2536',
         'p': '#252334', 'b': '#151420'}
KIDSP = {'h': '#2a2230', 'k': '#f0b494', 's': '#a8655a', 't': '#b84a5a', 'T': '#8e3446',
         'p': '#2b2e48', 'r': '#e9d6a8'}


def rng(seed): return np.random.default_rng(seed)


# ---------- scene 1: rain at the bus stop ----------
R = rng(7)
SKY1 = R.integers(0, 4, 0)
BLD = []
x = -4
while x < W:
    w = int(R.integers(10, 26)); h = int(R.integers(30, 80)); BLD.append((x, w, h)); x += w + int(R.integers(0, 3))
WIN = [(bx + 2 + i * 4, 150 - bh + 4 + j * 5, R.random()) for bx, bw, bh in BLD
       for i in range((bw - 3) // 4) for j in range((bh - 8) // 5)]
DROPS = np.c_[R.random(150) * W, R.random(150) * H, R.random(150)]
PUDDLES = [(40, 190, 22), (120, 178, 30), (175, 200, 18)]


def scene1(t):
    c = C()
    c.grad(0, 150, ['#0b1c24', '#0f2630', '#14323c', '#1b3f48', '#24505a'])
    for bx, bw, bh in BLD:  # far skyline
        c.rect(bx, 150 - bh, bw, bh, '#112a33')
        c.rect(bx + bw - 2, 150 - bh, 2, bh, '#0d222a')
    for wx, wy, r in WIN:
        if r > .82:
            on = r > .97 and math.sin(t * 3 + r * 50) > .6
            c.px(wx, wy, '#6e98a0' if on else ('#d8b36a' if r > .9 else '#5d8790'))
    # pylon
    for k in range(4):
        c.line(18 + k, 40, 8, 150, '#0e2129') if k == 0 else None
    c.line(22, 40, 8, 150, '#0e2129'); c.line(22, 40, 36, 150, '#0e2129')
    for y in range(55, 150, 14):
        f = (y - 40) / 110; c.line(22 - 14 * f, y, 22 + 14 * f, y + 10, '#0e2129')
    c.rect(10, 52, 25, 1, '#0e2129'); c.line(0, 60, 10, 52, '#0e2129'); c.line(34, 52, W, 46, '#0e2129')
    # haze band
    c.glow(108, 150, 160, '#2d5a63', .35, 18)
    # street
    c.grad(150, 168, ['#1a2e34', '#22383e', '#1a2e34'])
    c.rect(0, 166, W, 2, '#3c5458'); c.rect(0, 168, W, 2, '#0c171b')
    c.grad(170, H, ['#0c1a20', '#102229', '#13282f'])
    for k in range(0, W, 24): c.rect(k + (int(t * 0) % 24), 196, 10, 1, '#2a4148')
    # bus shelter (right)
    sx = 150
    c.rect(sx, 108, 60, 4, '#1c2b30'); c.rect(sx, 112, 60, 1, '#4a6a70')
    c.rect(sx + 2, 113, 2, 53, '#1c2b30'); c.rect(sx + 56, 113, 2, 53, '#1c2b30')
    c.rect(sx + 4, 116, 52, 38, '#29474f'); c.rect(sx + 4, 116, 52, 1, '#3f6670')
    c.rect(sx + 36, 118, 18, 30, '#a6d6cc'); c.rect(sx + 38, 120, 14, 26, '#cfeee2')
    c.rect(sx + 40, 124, 10, 8, '#e48a6a'); c.rect(sx + 41, 134, 8, 2, '#3c6a72')
    c.rect(sx + 8, 148, 24, 3, '#1a2a2f')
    c.glow(sx + 45, 133, 26, '#8fd0c4', .4, 34)
    # bus stop sign
    c.rect(140, 100, 1, 66, '#1a2b30'); c.rect(136, 96, 9, 11, '#d7d9cf'); c.rect(137, 97, 7, 3, '#2f6b9a')
    c.rect(138, 102, 5, 1, '#33464c'); c.rect(138, 104, 5, 1, '#33464c')
    # street lamp (left)
    c.rect(58, 70, 2, 96, '#14232a'); c.rect(58, 68, 14, 2, '#14232a'); c.rect(68, 70, 7, 3, '#14232a')
    fl = .5 + .04 * math.sin(t * 40) * (math.sin(t * 1.7) > .9)
    c.glow(71, 72, 14, '#ffd98a', .9)
    c.rect(69, 73, 5, 1, '#fff1c4')
    c.glow(72, 162, 44, '#f2c46d', fl, 26)
    # wet reflections of lamp and sign
    for y in range(172, H, 2):
        wob = int(2 * math.sin(y * .7 + t * 6))
        k = 1 - (y - 172) / 50
        if k > 0 and (y // 2 + int(t * 8)) % 3:
            c.rect(68 + wob, y, 7, 1, (hx('#f2c46d') * k + c.a[y, 70] * (1 - k)))
            c.rect(sx + 40 + wob, y, 10, 1, (hx('#8fd0c4') * k * .7 + c.a[y, sx + 44] * (1 - k * .7)))
    # passing car (2.0 -> 4.4 s)
    if 1.6 < t < 4.6:
        cx = -60 + (t - 1.6) / 3.0 * (W + 120)
        cy = 172
        c.glow(cx + 62, cy + 8, 40, '#fff0c0', .5, 9)
        c.rect(cx, cy, 52, 10, '#1e2c33'); c.rect(cx + 10, cy - 7, 28, 7, '#1e2c33')
        c.rect(cx + 13, cy - 5, 10, 5, '#5f8a92'); c.rect(cx + 25, cy - 5, 10, 5, '#4a747c')
        c.rect(cx, cy + 3, 52, 1, '#3c5a62'); c.rect(cx + 48, cy + 2, 4, 3, '#fff3c8')
        c.rect(cx, cy + 2, 3, 3, '#e04a4a')
        for wx in (cx + 8, cx + 38):
            c.rect(wx, cy + 9, 8, 4, '#0a1014'); c.rect(wx + 3, cy + 10, 2, 2, '#6a7d82')
        for y in range(cy + 14, min(H, cy + 30), 2):
            c.rect(cx + 2, y, 3, 1, '#7a3434'); c.rect(cx + 48, y, 4, 1, '#c8b47a')
    # puddles + ripples
    for px_, py, pw in PUDDLES:
        if py < 170: continue
        c.rect(px_, py, pw, 3, '#1c3a44'); c.rect(px_ + 2, py - 1, pw - 4, 1, '#1c3a44')
    for i in range(18):
        ph = (t * 1.3 + i * .37) % 1
        px_, py, pw = PUDDLES[i % 3]
        if py < 170: px_, py, pw = 30, 186, 120
        rx = px_ + (i * 37 % pw); r = int(ph * 4)
        if ph < .8: c.px(rx - r, py + 1, '#4e7e88'); c.px(rx + r, py + 1, '#4e7e88')
    # characters under umbrella
    dx, dy = 96, 138
    c.glow(dx + 8, 166, 20, '#0a1418', .45, 3)
    c.spr(dx, dy, DAD, DADP)
    hop = max(0., math.sin((t % 1.6) / 1.6 * math.pi * 2)) * 4 if 0.8 < t < 4.0 else 0
    ky = 152 - round(hop)
    c.spr(dx - 8, ky, KID, KIDP)
    c.px(dx + 1, 154, '#c98f6e')  # dad's hand meets kid's
    if 0.8 < t < 4.0 and (t % 1.6) / 1.6 > .5 and (t % 1.6) / 1.6 < .75:
        f = ((t % 1.6) / 1.6 - .5) * 4
        for s_ in (-1, 1):
            for k in range(3):
                c.px(dx - 4 + s_ * (2 + k + 4 * f), 165 - 3 * math.sin(f * math.pi) - k % 2, '#7fb0ba')
    # umbrella
    ux, uy = dx + 10, 120
    c.line(dx + 10, 147, ux, uy, '#2a2a30')
    for j in range(9):
        hw = int(math.sqrt(max(0, 81 - (8 - j) ** 2)) * 2.3)
        c.rect(ux - hw, uy + j, hw * 2, 1, '#9c3c44' if j < 7 else '#7a2c36')
        if j < 7: c.rect(ux - hw, uy + j, max(1, hw // 2), 1, '#b85458')
    for k in range(-20, 21, 10):
        c.rect(ux + k - 1, uy + 9 - (k == 0), 2, 1, '#6a2430')
    c.px(ux, uy - 1, '#2a2a30')
    # rain
    for i, (rx, ry, z) in enumerate(DROPS):
        y = (ry + t * (180 + 140 * z)) % (H + 20) - 10
        x_ = (rx - t * 30 * (1 + z)) % W - (y - ry) * 0
        ln = 3 + int(z * 4)
        col = '#3d6670' if z < .6 else '#6a98a2'
        if ux - 21 < x_ < ux + 21 and uy < y < 166:
            continue  # sheltered under umbrella
        c.line(x_, y, x_ - ln * .35, y + ln, col)
    for i in range(8):  # splashes on umbrella
        ph = (t * 3 + i * .29) % 1
        if ph < .3: c.px(ux - 18 + i * 5, uy - 1 - int(ph * 6), '#a6ccd2')
    return c


# ---------- scene 2: dusk on the pier ----------
R2 = rng(11)
CLOUDS = []
for k in range(26):
    cy = int(R2.integers(10, 105)); CLOUDS.append((R2.random() * (W + 80) - 40, cy,
                                                  int(R2.integers(14, 44)), int(R2.integers(3, 7)), R2.random()))
CLOUDS.sort(key=lambda q: q[1])
BIRDS = [(R2.random() * 30, R2.random() * 14) for _ in range(5)]


def disc(c, cx, cy, r, col, ymax):
    x0, x1, y0, y1 = int(cx - r), int(cx + r) + 1, int(cy - r), min(int(cy + r) + 1, ymax)
    for y in range(max(0, y0), min(H, y1)):
        hw = math.sqrt(max(0, r * r - (y - cy) ** 2))
        c.rect(round(cx - hw), y, round(2 * hw), 1, col)


def cloud(c, x, y, w, h, z, t):
    x = (x + t * (2 + 3 * z)) % (W + 80) - 40
    hl, mid, sh = ('#f8cfae', '#e09a90', '#9a6680') if y > 60 else ('#eab0a6', '#b07c92', '#635a80')
    blobs = [(x + k, y - h * .5 * abs(math.sin(k * .3 + z * 9)), h * (.6 + .5 * abs(math.sin(k * .21 + z * 5))))
             for k in range(0, w, 4)]
    base = y + h
    for bx, by, r in blobs: disc(c, bx, by + 1, r, sh, base + 1)
    for bx, by, r in blobs: disc(c, bx - .5, by - 1, r - .5, mid, base - 1)
    for bx, by, r in blobs: disc(c, bx - 1, by - 2.5, r - 1.8, hl, base - 3)


def scene2(t):
    c = C()
    HZ = 124
    c.grad(0, HZ, ['#2b3f5c', '#3e4f6e', '#6a5d7e', '#a96f85', '#df8f86', '#f2b38d', '#f8d39e'])
    c.glow(62, HZ, 60, '#ffe2a8', .5, 24)
    for q in CLOUDS: cloud(c, *q, t)
    # sun
    for j in range(10):
        hw = int(math.sqrt(max(0, 100 - (10 - j) ** 2)))
        c.rect(62 - hw, HZ - 10 + j, hw * 2, 1, '#fff2c8')
    # far hills
    for x in range(W):
        hh = int(6 + 4 * math.sin(x * .05) + 3 * math.sin(x * .13 + 1))
        if x > 120: c.rect(x, HZ - hh, 1, hh, '#6a4f72')
        hh2 = int(3 + 2 * math.sin(x * .09 + 2))
        c.rect(x, HZ - hh2, 1, hh2, '#523f60')
    # water
    c.grad(HZ, H, ['#5a5878', '#3f4a6a', '#2c3a58', '#1f2c46', '#18233a'])
    for j in range(0, H - HZ, 2):  # sun glitter path
        y = HZ + j; spread = 6 + j * .5
        for k in range(4):
            ph = math.sin(t * 2.5 + j * 1.7 + k * 2.1)
            if ph > .2:
                xx = 62 + math.sin(j * 3.1 + k * 7) * spread
                c.rect(xx, y, 2 + int(ph * 4 * (1 - j / 120)), 1, '#f6c79a' if j < 30 else '#d49088')
    for i in range(30):  # gentle wave dashes
        y = HZ + 6 + (i * 13) % (H - HZ - 6)
        x_ = (i * 47 + t * (6 + i % 4)) % (W + 20) - 10
        c.rect(x_, y, 4 + i % 5, 1, '#55607e' if y < 170 else '#2f3f60')
    # birds
    for i, (bx, by) in enumerate(BIRDS):
        x_ = 20 + bx + t * 14; y_ = 40 + by + math.sin(t * 2 + i) * 2
        flap = int(t * 6 + i) % 2
        c.px(x_, y_, '#3a2c44'); c.px(x_ - 1, y_ - flap, '#3a2c44'); c.px(x_ + 1, y_ - flap, '#3a2c44')
        c.px(x_ - 2, y_ - 1 + flap, '#3a2c44'); c.px(x_ + 2, y_ - 1 + flap, '#3a2c44')
    # pier (from right), with posts + reflections
    PY = 156
    for px_ in range(96, W, 22):
        c.rect(px_, PY + 4, 4, 40, '#2a1f2e'); c.rect(px_ + 3, PY + 4, 1, 40, '#3d2c3a')
        for y in range(PY + 44, min(H, PY + 60), 2):
            c.rect(px_ + int(math.sin(y + t * 5)), y, 4, 1, '#1c2236')
    c.rect(90, PY, W - 90, 5, '#5a3e44')
    for k in range(90, W, 5): c.rect(k, PY, 1, 5, '#47313a')
    c.rect(90, PY, W - 90, 1, '#e8a68a'); c.rect(90, PY + 5, W - 90, 1, '#2a1f2e')
    c.rect(200, PY - 14, 3, 14, '#3a2a34'); c.rect(200, PY - 14, 1, 14, '#c88878')  # mooring post
    c.rect(186, PY - 4, 8, 4, '#4a3a5a'); c.rect(186, PY - 4, 8, 1, '#e0a08a')  # tackle box
    # bucket
    c.rect(176, PY - 6, 6, 6, '#6e7f92'); c.rect(176, PY - 6, 6, 1, '#d8b0a0')
    # figures (sitting at pier edge, looking at the sun)
    dx, dy = 104, PY - 14
    sw = int(math.sin(t * 3) > 0)
    c.spr(dx, dy, DADS, DADSP)
    kx = 124; ky = PY - 8
    c.spr(kx, ky, KIDS, KIDSP)
    c.px(kx + 1 + sw, ky + 12, '#e9d6a8'); c.px(kx + 5 - sw, ky + 12, '#e9d6a8')
    if 2.5 < t < 4.6:  # kid points at the sun
        c.line(kx + 1, ky + 6, kx - 5, ky + 1, '#b84a5a'); c.px(kx - 6, ky, '#f0b494')
    # fishing rod + line + bobber
    hx_, hy_ = dx + 1, dy + 9
    tipx, tipy = dx - 28, dy - 24 + math.sin(t * 1.3)
    c.line(hx_, hy_, tipx, tipy, '#2a2030')
    bob = math.sin(t * 2.2) * 1.2 + (2 if 3.2 < t % 5 < 3.5 else 0)
    bx, by = 60, 150 + bob
    for k in range(14):  # sagging line
        f = k / 13; c.px(tipx + (bx - tipx) * f, tipy + (by - tipy) * f + math.sin(f * math.pi) * 6, '#d6a99a')
    c.px(bx, by - 1, '#f3e6c8'); c.px(bx, by, '#d04848')
    r = int((t * 3) % 6)
    c.px(bx - r - 1, 151, '#8f86a6'); c.px(bx + r + 1, 151, '#8f86a6')
    # warm rim light on figures' sun side
    c.glow(62, HZ, 120, '#ff9a7a', .12, 70)
    # fireflies / dust
    for i in range(6):
        x_ = 140 + 60 * math.sin(i * 2.3 + t * .4); y_ = 120 + 20 * math.sin(i * 1.7 + t * .7)
        if math.sin(t * 4 + i) > .3: c.px(x_, y_, '#ffe6a0')
    return c


def frame(t):
    if t < CUT - .35: a = scene1(t).a
    elif t > CUT + .35: a = scene2(t - CUT).a
    else:  # pixel-dissolve transition through Bayer threshold
        f = (t - (CUT - .35)) / .7
        A, B = scene1(t).a, scene2(t - CUT).a
        ys, xs = np.mgrid[0:H, 0:W]
        m = (BAYER[(ys // 2) % 4, (xs // 2) % 4] < f)[..., None]
        a = np.where(m, B, A)
    fade = min(1, t / .5, (DUR - t) / .6)
    a = a * max(0, fade)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return img.resize((W * S, H * S), Image.NEAREST)


# ---------- audio: rain -> waves, soft triangle chiptune ----------
def audio(path):
    n = int(SR * DUR); tt = np.arange(n) / SR; r = rng(3)
    noise = r.standard_normal(n)
    rain = np.convolve(noise, np.ones(3) / 3, 'same') * .05
    patter = (r.random(n) > .9993) * r.standard_normal(n) * .5
    patter = np.convolve(patter, np.exp(-np.arange(200) / 30), 'same') * .12
    env1 = np.clip((CUT + .3 - tt) / .6, 0, 1)
    car = np.convolve(noise, np.ones(40) / 40, 'same') * np.exp(-((tt - 3.0) / .55) ** 2) * .9
    wave_ = np.convolve(noise, np.ones(90) / 90, 'same') * (1.2 + np.sin(tt * 1.3)) * 1.2
    env2 = np.clip((tt - CUT + .3) / .6, 0, 1)
    gull = sum(np.sin(2 * np.pi * (1800 - 600 * ((tt - s) * 4)) * (tt - s)) *
               np.exp(-((tt - s - .12) / .08) ** 2) for s in (6.6, 6.9)) * .02
    tri = lambda f: 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * tt))
    music = np.zeros(n); beat = .3
    chords = [(220, 261.6, 329.6), (174.6, 220, 261.6), (196, 246.9, 293.7), (164.8, 207.7, 246.9)]
    for i in range(int(DUR / beat)):
        s0 = i * beat; ch = chords[(i // 8) % 4]; f = ch[[0, 1, 2, 1][i % 4]] * 2
        seg = (tt >= s0) & (tt < s0 + beat)
        music[seg] += tri(f)[seg] * np.exp(-(tt[seg] - s0) * 6) * .06
        if i % 8 == 0:
            seg2 = (tt >= s0) & (tt < s0 + beat * 8)
            music[seg2] += tri(ch[0] / 2)[seg2] * .035
    mix = (rain + patter) * env1 + car + wave_ * env2 + gull + music
    mix *= np.clip(np.minimum(tt / .5, (DUR - tt) / .8), 0, 1)
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
