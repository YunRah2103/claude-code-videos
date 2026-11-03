"""Original 10 s pixel-art mood piece: rainy bus stop -> walk on the beach at dusk.
Usage: python render.py video OUT.mp4 | python render.py still OUTDIR t1 t2 ..."""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image
import sprites as SPR

W = H = 180; S = 6; FPS = 30; DUR = 10.0; CUT = 5.0; SR = 44100
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

# ================= scene 1: rain at the bus stop =================
DADF = P(H='#23222a', h='#46424f', S='#d49c7c', s='#a86c58', G='#17171d', L='#b98c76', e='#17171d',
         B='#4b3934', o='#6a3434', F='#8a6a50', f='#5e4434', J='#5b705f', j='#3d4c42', K='#7f9580',
         T='#94c6c8', t='#6a9ca2', U='#2b2620', P='#3a4762', p='#28324a', X='#1d1d24', x='#44444f')
KIDR = P(y='#efc24a', Y='#b98a2e', H='#5a3a2a', S='#ecb494', s='#ba7c64', k='#ba7c64', e='#2a2028',
         J='#efc24a', j='#b98a2e', P='#3a4566', p='#2a3350', X='#c8463e', x='#8e2e2e')
R1 = rng(7)
BLD, x = [], -4
while x < W:
    w = int(R1.integers(9, 22)); BLD.append((x, w, int(R1.integers(26, 70)))); x += w + int(R1.integers(0, 3))
WIN = [(bx + 2 + i * 4, 110 - bh + 4 + j * 5, R1.random()) for bx, bw, bh in BLD
       for i in range((bw - 3) // 4) for j in range((bh - 8) // 5)]
DROPS = np.c_[R1.random(120) * W, R1.random(120) * H, R1.random(120)]
PUD = [(46, 151, 20), (100, 150, 16)]   # puddles on the sidewalk front (x, y, w)
DX, DFEET = 70, 140                      # dad sprite left x, feet y
KID_FEET = 151


def kid_state(t):
    """Kid runs back and forth in front of dad, jumping into puddles."""
    span, x0 = 92, 22
    d = (t * 30) % (2 * span); fwd = d < span
    x = x0 + (d if fwd else 2 * span - d)
    jump = 0
    for px_, py, pw in PUD:
        c = px_ + pw / 2; u = (x - (c - 10)) / 12  # arc lands in middle of puddle
        if 0 < u < 1: jump = max(jump, 7 * math.sin(math.pi * u))
    return x, not fwd, jump


def scene1(t):
    c = C()
    c.grad(0, 110, ['#0a1a22', '#0e242e', '#12303a', '#183c46', '#20505a'])
    for bx, bw, bh in BLD:
        c.rect(bx, 110 - bh, bw, bh, '#10283a' if bw % 2 else '#112b33')
        c.rect(bx + bw - 2, 110 - bh, 2, bh, '#0c2028')
    for wx, wy, r in WIN:
        if r > .8:
            on = not (r > .96 and math.sin(t * 2 + r * 50) > .5)
            if on: c.px(wx, wy, '#d8b36a' if r > .9 else '#5d8f98')
    # pylon + wires
    for a, b in ((-12, -1), (12, 1)): c.line(150, 18, 150 + a, 110, '#0d2028')
    for y in range(30, 110, 12):
        f = (y - 18) / 92; c.line(150 - 12 * f, y, 150 + 12 * f, y + 9, '#0d2028')
    c.rect(138, 26, 25, 1, '#0d2028'); c.line(0, 34, 138, 26, '#0d2028'); c.line(162, 26, W, 30, '#0d2028')
    c.glow(90, 112, 140, '#2f5e66', .35, 14)
    # back wall / fence line and sidewalk
    c.rect(0, 104, W, 6, '#173138'); c.rect(0, 104, W, 1, '#2a4a50')
    for k in range(0, W, 7): c.rect(k, 98, 1, 6, '#173138')
    c.rect(0, 98, W, 1, '#173138')
    c.grad(110, 152, ['#1b3036', '#20383e', '#24404a', '#1f3a42'])
    for k in range(0, W, 18): c.line(k, 110, k - 10, 152, '#1a2d33')
    c.rect(0, 152, W, 2, '#4a6266'); c.rect(0, 154, W, 2, '#0b161a')
    c.grad(156, H, ['#0b1a20', '#0f2229', '#12272e'])
    for k in range(4, W, 22): c.rect(k, 170, 10, 1, '#2a4148')
    # bus shelter
    sx = 116
    c.rect(sx, 62, 64, 4, '#1a292e'); c.rect(sx, 66, 64, 1, '#557a80')
    c.rect(sx + 2, 67, 2, 75, '#1a292e'); c.rect(sx + 60, 67, 2, 75, '#1a292e')
    c.rect(sx + 4, 70, 56, 52, '#24434b'); c.rect(sx + 4, 70, 56, 1, '#3f6a74')
    c.rect(sx + 38, 74, 20, 40, '#a6d6cc'); c.rect(sx + 40, 76, 16, 36, '#d2f0e4')
    c.rect(sx + 42, 80, 12, 12, '#e98c6c'); c.rect(sx + 44, 82, 4, 4, '#f6c49a')
    c.rect(sx + 42, 96, 12, 2, '#3c6a72'); c.rect(sx + 42, 100, 8, 1, '#5d8f98')
    c.rect(sx + 8, 120, 26, 3, '#15252a'); c.rect(sx + 10, 123, 2, 10, '#15252a'); c.rect(sx + 30, 123, 2, 10, '#15252a')
    c.glow(sx + 48, 96, 30, '#8fd0c4', .38, 42)
    # bus-stop sign
    c.rect(112, 54, 1, 88, '#18292e'); c.rect(108, 48, 9, 12, '#d7d9cf'); c.rect(109, 49, 7, 3, '#2f6b9a')
    c.rect(110, 54, 5, 1, '#33464c'); c.rect(110, 56, 5, 1, '#33464c')
    # street lamp
    c.rect(20, 38, 2, 114, '#13222a'); c.rect(20, 36, 14, 2, '#13222a'); c.rect(30, 38, 7, 3, '#13222a')
    c.glow(33, 40, 13, '#ffd98a', .9); c.rect(31, 41, 5, 1, '#fff1c4')
    c.glow(36, 140, 40, '#f2c46d', .5, 22)
    # puddles (reflect lamp/ad)
    for px_, py, pw in PUD:
        c.rect(px_, py - 1, pw, 3, '#18343e'); c.rect(px_ + 2, py - 2, pw - 4, 1, '#18343e')
        c.rect(px_ + 3, py, 4, 1, '#c8a560' if px_ < 60 else '#7fbcb4')
    for i in range(10):
        ph = (t * 1.4 + i * .41) % 1; px_, py, pw = PUD[i % 2]
        rx = px_ + 2 + (i * 7) % (pw - 4); r = int(ph * 3)
        if ph < .7: c.px(rx - r, py, '#5d929c'); c.px(rx + r, py, '#5d929c')
    # road reflections
    for y in range(158, H, 2):
        wob = int(1.5 * math.sin(y * .7 + t * 6)); k = 1 - (y - 158) / 26
        if k > 0 and (y // 2 + int(t * 8)) % 3:
            c.rect(30 + wob, y, 7, 1, col('#f2c46d') * k + c.a[y, 33] * (1 - k))
            c.rect(sx + 42 + wob, y, 12, 1, col('#8fd0c4') * k * .6 + c.a[y, sx + 46] * (1 - k * .6))
    # passing car on the road
    if 2.4 < t < 5.0:
        cx = W + 20 - (t - 2.4) / 2.2 * (W + 110); cy = 160
        c.glow(cx - 10, cy + 6, 34, '#fff0c0', .45, 7)
        c.rect(cx, cy, 58, 11, '#1c2a31'); c.rect(cx + 14, cy - 8, 30, 8, '#1c2a31')
        c.rect(cx + 17, cy - 6, 12, 6, '#4f7a84'); c.rect(cx + 31, cy - 6, 11, 6, '#5f8a92')
        c.rect(cx, cy + 3, 58, 1, '#3c5a62'); c.rect(cx, cy + 2, 4, 3, '#fff3c8'); c.rect(cx + 55, cy + 2, 3, 3, '#e04a4a')
        for wx in (cx + 8, cx + 42):
            c.rect(wx, cy + 9, 9, 5, '#090f12'); c.rect(wx + 3, cy + 10, 3, 3, '#5a6d72')
    # ---------- characters (own layer, relit) ----------
    L = C(layer=True)
    kx, back, jump = kid_state(t)
    bre = int((t % 2.2) > 1.1)
    rows = list(SPR.DAD_FRONT)
    look = -1 if kx < DX + 6 else 1
    blink = (t % 2.7) < .12
    for j in (8,):
        r = rows[j]
        if blink: r = r.replace('LeL', 'GGG')
        elif look < 0: r = r.replace('LeL', 'eLL')
        else: r = r.replace('LeL', 'LLe')
        rows[j] = r
    # umbrella shaft first (behind hand)
    hxp, hyp = DX + SPR.DAD_HAND[0], DFEET - len(rows) + SPR.DAD_HAND[1] + bre
    ux, uy = DX + 12, 70 + bre
    L.spr(DX, DFEET - len(rows), rows[32:], DADF) if False else None
    lower = rows[32:]; upper = rows[:32]
    top = DFEET - len(rows)
    L.spr(DX, top + 32, lower, DADF)
    L.spr(DX, top + bre, upper, DADF)
    dad_a = light(L, (.78, .9, .98), [(1, '#ffc56e', .55), (-1, '#8fd8cc', .35)])
    # kid
    K = C(layer=True)
    phase = (t * 2.7) % 1
    SPR.person(K, kx, KID_FEET - round(jump), KIDR, 'kid', phase, 'run', flip=back)
    kid_a = light(K, (.86, .92, .96), [(1, '#ffc56e', .5), (-1, '#8fd8cc', .3)])
    # contact shadows
    c.glow(DX + 11, DFEET, 13, '#081217', .55, 2.5)
    c.glow(kx, KID_FEET, 6 - jump * .4, '#081217', .5, 1.6)
    comp(c, L, dad_a)
    # umbrella
    c.line(hxp + .5, hyp, ux, uy, '#2a2a32')
    for j in range(10):
        hw = int(math.sqrt(max(0, 100 - (9 - j) ** 2)) * 2.5)
        cy = uy - 10 + j
        c.rect(ux - hw, cy, hw * 2, 1, '#9c3c44' if j < 8 else '#73283a')
        if j < 8: c.rect(ux - hw, cy, max(1, hw // 2), 1, '#c25a5c')
        if j < 6: c.rect(ux + hw - max(1, hw // 4), cy, max(1, hw // 4), 1, '#7c2c3a')
    for k in (-24, -12, 0, 12, 24): c.rect(ux + k - 1, uy, 3, 1, '#5e2232')
    c.px(ux, uy - 11, '#2a2a32'); c.px(ux, uy - 12, '#2a2a32')
    comp(c, K, kid_a)
    # puddle splash when kid lands
    for px_, py, pw in PUD:
        cxp = px_ + pw / 2; u = (kx - (cxp - 10)) / 12
        if .85 < u < 1.6 or (back and -.6 < u < .15):
            f = min(1, abs(u - (1 if not back else 0)) * 1.6)
            for s_ in (-1, 1):
                for k in range(4):
                    c.px(kx + s_ * (2 + k * 1.5 + 6 * f), py - 1 - 5 * math.sin(f * math.pi) * (1 - k * .2), '#9fd0d6')
    # rain
    for rx, ry, z in DROPS:
        y = (ry + t * (170 + 120 * z)) % (H + 20) - 10; x_ = (rx - t * 25 * (1 + z)) % W
        if ux - 25 < x_ < ux + 25 and uy - 8 < y < DFEET: continue
        ln = 3 + int(z * 4)
        c.line(x_, y, x_ - ln * .3, y + ln, '#3d6670' if z < .6 else '#6a98a2')
    for i in range(8):
        ph = (t * 3 + i * .29) % 1
        if ph < .3: c.px(ux - 21 + i * 6, uy - 9 + abs(i - 3.5) * .0 - int(ph * 6) - (3 if 2 < i < 6 else 1), '#a6ccd2')
    return c


# ================= scene 2: walk on the beach at dusk =================
DADB = P(H='#2a2430', h='#4a3c4c', S='#e0a283', s='#b06e5e', G='#1d1820', L='#f0bca0', e='#1d1820', k='#b06e5e',
         B='#7a5450', o='#6a3434', T='#efe5d2', t='#c2b29e', R='#6f97b4', P='#c24a54', p='#8e3540',
         X='#d89a7c', x='#a8685a', thigh='#c24a54', thigh2='#8e3540', shin='#e0a283', shin2='#a8685a',
         upper='#efe5d2', upper2='#c2b29e', fore='#e0a283', fore2='#a8685a', J='#efe5d2', j='#c2b29e')
KIDB = P(H='#7a4a2c', h='#a8703e', S='#f0b494', s='#c07c66', k='#c07c66', e='#2a2028', T='#e0604c',
         t='#a8483e', W='#f6dcb0', P='#3f5f8a', p='#2e4568', X='#f0b494', x='#c07c66',
         thigh='#3f5f8a', thigh2='#2e4568', shin='#f0b494', shin2='#c07c66', upper='#e0604c',
         upper2='#a8483e', fore='#f0b494', fore2='#c07c66', J='#e0604c', j='#a8483e')
KIDB_SPEC = dict(torso=SPR.KID_TORSO_BEACH, head=SPR.KID_HEAD_BEACH)
DADB_SPEC = dict(torso=SPR.DAD_SHIRT_TORSO)
R2 = rng(11)
CLOUDS = sorted([(R2.random() * (W + 80) - 40, int(R2.integers(8, 82)), int(R2.integers(12, 40)),
                  int(R2.integers(3, 6)), R2.random()) for _ in range(20)], key=lambda q: q[1])
HZ, FEET = 100, 150


def disc(c, cx, cy, r, colr, ymax):
    for y in range(max(0, int(cy - r)), min(H, int(cy + r) + 1, ymax)):
        hw = math.sqrt(max(0, r * r - (y - cy) ** 2)); c.rect(round(cx - hw), y, round(2 * hw), 1, colr)


def cloud(c, x, y, w, h, z, t):
    x = (x + t * (1.5 + 2 * z)) % (W + 120) - 60
    hl, mid, sh = ('#f8cfae', '#e09a90', '#9a6680') if y > 50 else ('#eab0a6', '#b07c92', '#635a80')
    bl = [(x + k, y - h * .5 * abs(math.sin(k * .3 + z * 9)), h * (.6 + .5 * abs(math.sin(k * .21 + z * 5))))
          for k in range(0, w, 4)]
    for bx, by, r in bl: disc(c, bx, by + 1, r, sh, y + h + 1)
    for bx, by, r in bl: disc(c, bx - .5, by - 1, r - .5, mid, y + h - 1)
    for bx, by, r in bl: disc(c, bx - 1, by - 2.5, r - 1.8, hl, y + h - 3)


def walkers(t):
    dxh = 34 + t * 11            # dad hip x
    return dxh, dxh + 13


def scene2(t):
    c = C()
    c.grad(0, HZ, ['#2b3f5c', '#3e4f6e', '#6a5d7e', '#a96f85', '#df8f86', '#f2b38d', '#f8d39e'])
    c.glow(40, HZ, 50, '#ffe2a8', .5, 20)
    for q in CLOUDS: cloud(c, *q, t)
    for j in range(9):
        hw = int(math.sqrt(max(0, 81 - (9 - j) ** 2))); c.rect(40 - hw, HZ - 9 + j, hw * 2, 1, '#fff2c8')
    for x in range(W):
        hh = int(5 + 3 * math.sin(x * .06) + 2 * math.sin(x * .15 + 1))
        if x > 100: c.rect(x, HZ - hh, 1, hh, '#6a4f72')
    # sea
    c.grad(HZ, 128, ['#6a6588', '#4f5578', '#3a4668', '#2c3a5a'])
    for j in range(0, 28, 2):
        y = HZ + j; sp_ = 4 + j * .6
        for k in range(3):
            ph = math.sin(t * 2.5 + j * 1.7 + k * 2.1)
            if ph > .2: c.rect(40 + math.sin(j * 3.1 + k * 7) * sp_, y, 2 + int(ph * 3), 1, '#f6c79a')
    for i in range(16):
        y = HZ + 3 + (i * 7) % 24; x_ = (i * 41 + t * (5 + i % 3)) % (W + 20) - 10
        c.rect(x_, y, 3 + i % 4, 1, '#7a7898')
    # wet sand (mirror of the sky) + dry sand
    c.grad(128, H, ['#8a6a7e', '#a07a80', '#7a5e70', '#5e4a60', '#4a3c52'])
    for y in range(132, 166, 3):
        k = (1 - (y - 132) / 34) * .45; w_ = 3 + (y - 132) * .25
        x_ = 40 - w_ / 2 + 2 * math.sin(y * .8 + t * 3)
        c.rect(x_, y, w_, 1, col('#f6c79a') * k + c.a[y, int(x_)] * (1 - k))
    c.grad(166, H, ['#6a5060', '#5a4456', '#4a3a4c'])
    c.rect(0, 166, W, 1, '#7a5c6a')
    # waves washing in
    for layer in range(2):
        ph = t * .9 + layer * 1.7
        edge = 128 + 6 + 5 * math.sin(ph) + layer * 3
        for x in range(W):
            e = edge + 1.5 * math.sin(x * .12 + ph * 2 + layer) + .8 * math.sin(x * .37 - ph)
            ys = int(128 + layer * 2)
            c.rect(x, ys, 1, int(e) - ys, '#4a5276' if layer else '#556088')
            c.rect(x, int(e), 1, 1, '#f2e2d6' if (x + int(t * 10)) % 5 else '#c8b8c8')
            if (x * 7 + int(t * 6)) % 11 == 0: c.px(x, int(e) - 2, '#d8c8d0')
    # footprints
    dxh, kxh = walkers(t)
    for k in range(40):
        tk = k / 2.0
        if tk < t - .3:
            fx = 34 + tk * 11; c.rect(fx - 1 + (k % 2) * 2, FEET + 1, 3, 1, '#4e3e56')
        tk2 = k / 3.4
        if tk2 < t - .3:
            fx = 47 + tk2 * 11; c.rect(fx + (k % 2), FEET + 3, 2, 1, '#4e3e56')
    # characters
    L = C(layer=True)
    hold = (dxh + 7, FEET - 21)
    SPR.person(L, dxh, FEET, DADB, 'dad', (t * 1.0) % 1, 'walk', hold=hold, spec=DADB_SPEC)
    SPR.person(L, kxh, FEET + 2, KIDB, 'kid', (t * 1.7 + .3) % 1, 'walk', hold=hold, spec=KIDB_SPEC)
    a = light(L, (.95, .84, .86), [(1, '#ffd2a0', .75), (-1, '#6a5a8a', .25)])
    # reflection in wet sand
    ys, xs = np.nonzero(L.m)
    for y, x in zip(ys, xs):
        ry = 2 * FEET + 2 - y
        if FEET < ry < 166 and (ry % 3):
            wx = int(x + math.sin(ry * .9 + t * 5))
            if 0 <= wx < W: c.a[ry, wx] = c.a[ry, wx] * .55 + a[y, x] * .25
    c.glow(dxh + 2, FEET + 1, 9, '#3a2c44', .5, 1.6); c.glow(kxh, FEET + 3, 5, '#3a2c44', .5, 1.3)
    comp(c, L, a)
    # gulls
    for i in range(3):
        x_ = (150 - t * 9 + i * 14) % (W + 20) - 10; y_ = 30 + i * 6 + math.sin(t * 1.6 + i) * 2
        fl = int(t * 5 + i) % 2
        c.px(x_, y_, '#3a2c44'); c.px(x_ - 1, y_ - fl, '#3a2c44'); c.px(x_ + 1, y_ - fl, '#3a2c44')
        c.px(x_ - 2, y_ - 1 + fl * 2 - 1, '#3a2c44'); c.px(x_ + 2, y_ - 1 + fl * 2 - 1, '#3a2c44')
    return c


def frame(t):
    if t < CUT - .35: a = scene1(t).a
    elif t > CUT + .35: a = scene2(t - CUT).a
    else:
        f = (t - (CUT - .35)) / .7
        A, B = scene1(t).a, scene2(t - CUT).a
        m = (BAYER[(YS // 2) % 4, (XS // 2) % 4] < f)[..., None]
        a = np.where(m, B, A)
    a = a * max(0, min(1, t / .5, (DUR - t) / .6))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W * S, H * S), Image.NEAREST)


# ---------- audio: rain -> waves, soft triangle chiptune ----------
def audio(path):
    n = int(SR * DUR); tt = np.arange(n) / SR; r = rng(3)
    noise = r.standard_normal(n)
    rain = np.convolve(noise, np.ones(3) / 3, 'same') * .05
    patter = (r.random(n) > .9993) * r.standard_normal(n) * .5
    patter = np.convolve(patter, np.exp(-np.arange(200) / 30), 'same') * .12
    env1 = np.clip((CUT + .3 - tt) / .6, 0, 1)
    car = np.convolve(noise, np.ones(40) / 40, 'same') * np.exp(-((tt - 3.6) / .6) ** 2) * .9
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
