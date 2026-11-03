"""Isometric pixel showcase: 8 original scenes x 4 s, vertical 9:16 (1080x1920).
Usage: python render.py video OUT.mp4 | python render.py still OUTDIR t1 t2 ..."""
import importlib.util, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image

_spec = importlib.util.spec_from_file_location(
    'style_reel', Path(__file__).resolve().parents[2] / 'style-reel' / 'src' / 'render.py')
sr = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(sr)
C, col, hr, BAYER, FONT, text_width = sr.C, sr.col, sr.hr, sr.BAYER, sr.FONT, sr.text_width

W, H, SC = 108, 192, 10
OW, OH = W * SC, H * SC
FPS, SEGD, SR = 30, 4.0, 44100


# ============================== isometric engine ==============================
class Iso:
    """2:1 isometric projection onto a pixel canvas. X runs down-right, Y down-left, Z up."""
    def __init__(s, c, ox, oy, k):
        s.c, s.ox, s.oy, s.k = c, ox, oy, k
        s.items, s.emit = [], []
    def p(s, X, Y, Z=0): return (s.ox + (X - Y) * s.k, s.oy + ((X + Y) / 2 - Z) * s.k)
    def poly(s, pts, cl): return s.c.poly([s.p(*q) for q in pts], cl)
    def box(s, X, Y, Z, dx, dy, dz, top, left, right):
        s.poly([(X, Y + dy, Z), (X + dx, Y + dy, Z), (X + dx, Y + dy, Z + dz), (X, Y + dy, Z + dz)], left)
        s.poly([(X + dx, Y, Z), (X + dx, Y + dy, Z), (X + dx, Y + dy, Z + dz), (X + dx, Y, Z + dz)], right)
        s.poly([(X, Y, Z + dz), (X + dx, Y, Z + dz), (X + dx, Y + dy, Z + dz), (X, Y + dy, Z + dz)], top)
    def qy(s, X0, X1, Y, Z0, Z1, cl): return s.poly([(X0, Y, Z0), (X1, Y, Z0), (X1, Y, Z1), (X0, Y, Z1)], cl)
    def qx(s, X, Y0, Y1, Z0, Z1, cl): return s.poly([(X, Y0, Z0), (X, Y1, Z0), (X, Y1, Z1), (X, Y0, Z1)], cl)
    def qz(s, X0, X1, Y0, Y1, Z, cl): return s.poly([(X0, Y0, Z), (X1, Y0, Z), (X1, Y1, Z), (X0, Y1, Z)], cl)
    def shade(s, pts, k=.55):
        im_m = C(layer=True); im_m.poly([s.p(*q) for q in pts], '#000000')
        s.c.a[im_m.m] *= k
    def glow(s, X, Y, Z, r, cl, k=.6, ry=None): s.c.glow(*s.p(X, Y, Z), r, cl, k, ry)
    def ground(s, fn, xoff=0.0):
        u = (s.c.xs - s.ox) / s.k; v = 2 * (s.c.ys - s.oy) / s.k
        s.c.a[:] = fn((u + v) / 2 + xoff, (v - u) / 2)
    def add(s, depth, fn): s.items.append((depth, fn))
    def draw(s):
        for _, fn in sorted(s.items, key=lambda q: q[0]): fn()
        s.items = []


def tex(X, Y, a, b, n):
    return ((np.floor(X / n) + np.floor(Y / n)) % 2).astype(bool)[..., None] * (col(a) - col(b)) + col(b)


# ============================== props ==============================
CARS = {
    'red':   dict(top='#f07a5a', side='#c8503c', end='#a83e30', stripe='#f6d8a8'),
    'blue':  dict(top='#7aa8f0', side='#3a6ad0', end='#2a4ea8', stripe='#e8f0ff'),
    'mint':  dict(top='#9ae8c8', side='#4ac0a0', end='#34947c', stripe='#ffffff'),
    'yellow': dict(top='#ffe07a', side='#f0b030', end='#c88a20', stripe='#2a2a30'),
    'white': dict(top='#ffffff', side='#d8dce4', end='#aab0bc', stripe='#c8503c'),
}
GLASS, GLASS2 = '#8ac0d8', '#b8e0f0'


def car(I, X, Y, d, t, pal='red', Z=0.0, lights=False, spin=14):
    """Boxy hatchback. d in {'+x','-x','+y','-y'} = travel direction."""
    P = CARS[pal]; ax = d[1] == 'x'; fwd = d[0] == '+'
    dx, dy = (22, 11) if ax else (11, 22)
    I.shade([(X - 1, Y - 1, 0), (X + dx + 1, Y - 1, 0), (X + dx + 1, Y + dy + 1, 0), (X - 1, Y + dy + 1, 0)], .55)
    I.box(X, Y, Z + 2, dx, dy, 5, P['top'], P['side'] if ax else P['end'], P['end'] if ax else P['side'])
    a0, a1 = (4, 15) if fwd else (7, 18)
    if ax: I.box(X + a0, Y + 1, Z + 7, 11, 9, 4, P['top'], P['side'], P['end'])
    else:  I.box(X + 1, Y + a0, Z + 7, 9, 11, 4, P['top'], P['end'], P['side'])
    z0, z1 = Z + 7.6, Z + 10.4
    if ax:   # side windows on Y+ face, end window on X+ face
        I.qy(X + a0 + 1, X + a0 + 5, Y + 10, z0, z1, GLASS); I.qy(X + a0 + 6, X + a0 + 10, Y + 10, z0, z1, GLASS)
        I.qx(X + a0 + 11, Y + 2, Y + 9, z0, z1, GLASS2 if fwd else GLASS)
        I.qy(X, X + 22, Y + 11, Z + 4.2, Z + 4.8, P['stripe'])
    else:
        I.qx(X + 10, Y + a0 + 1, Y + a0 + 5, z0, z1, GLASS); I.qx(X + 10, Y + a0 + 6, Y + a0 + 10, z0, z1, GLASS)
        I.qy(X + 2, X + 9, Y + a0 + 11, z0, z1, GLASS2 if fwd else GLASS)
        I.qx(X + 11, Y, Y + 22, Z + 4.2, Z + 4.8, P['stripe'])
    lamp = '#fff6c8' if fwd else '#ff4a4a'
    for o in (1.5, 8):
        if ax: I.qx(X + 22, Y + o, Y + o + 1.5, Z + 4.4, Z + 5.6, lamp)
        else:  I.qy(X + o, X + o + 1.5, Y + 22, Z + 4.4, Z + 5.6, lamp)
    for w in (5, 17):
        if ax: pts = [(X + w + 2.6 * math.cos(a), Y + 11.1, Z + 2.4 + 2.6 * math.sin(a)) for a in np.linspace(0, 6.283, 14)]
        else:  pts = [(X + 11.1, Y + w + 2.6 * math.cos(a), Z + 2.4 + 2.6 * math.sin(a)) for a in np.linspace(0, 6.283, 14)]
        I.poly(pts, '#1c1a20')
        a = t * spin
        hub = (X + w + 1.2 * math.cos(a), Y + 11.2, Z + 2.4 + 1.2 * math.sin(a)) if ax else (X + 11.2, Y + w + 1.2 * math.cos(a), Z + 2.4 + 1.2 * math.sin(a))
        I.c.px(*I.p(*hub), '#9aa0a8')
    if lights:
        def em():
            for o in (1.5, 8):
                if ax: I.qx(X + 22, Y + o, Y + o + 1.5, Z + 4.4, Z + 5.6, lamp)
                else:  I.qy(X + o, X + o + 1.5, Y + 22, Z + 4.4, Z + 5.6, lamp)
            if fwd:
                if ax: I.glow(X + 34, Y + 5.5, 0, 16, '#fff0c0', .4, 7)
                else:  I.glow(X + 5.5, Y + 34, 0, 16, '#fff0c0', .4, 7)
            else:
                if ax: I.glow(X + 22, Y + 5.5, 4, 5, '#ff4a4a', .45)
                else:  I.glow(X + 5.5, Y + 22, 4, 5, '#ff4a4a', .45)
        I.emit.append(em)


def tree(I, X, Y, snow=False):
    I.shade([(X - 2, Y + 2, 0), (X + 9, Y + 2, 0), (X + 9, Y + 9, 0), (X - 2, Y + 9, 0)], .7)
    I.box(X + 2, Y + 2, 0, 2, 2, 6, '#8a5a3a', '#6a4028', '#4e2e1e')
    if snow:
        I.box(X, Y, 6, 6, 6, 5, '#f4f8ff', '#3a6a5a', '#2e5a4c'); I.box(X + 1, Y + 1, 11, 4, 4, 3, '#ffffff', '#4a7a6a', '#3a6a5a')
    else:
        I.box(X, Y, 6, 6, 6, 5, '#7ac85a', '#4a9a3a', '#3a7a2e'); I.box(X + 1, Y + 1, 11, 4, 4, 3, '#9ae070', '#5aae44', '#448a36')


def palm(I, X, Y, t, k=0):
    I.shade([(X, Y, 0), (X + 10, Y + 4, 0), (X + 12, Y + 8, 0), (X + 2, Y + 4, 0)], .75)
    for j in range(9):
        I.box(X + j * .25, Y, j * 2, 2, 2, 2, '#c89a6a' if j % 2 else '#a87a4a', '#8a6038', '#6a4828')
    cx, cy, cz = X + 3.2, Y + 1, 19
    for i in range(6):
        a = i * 1.047 + math.sin(t * 1.5 + k + i) * .08
        for d in range(1, 9):
            I.c.rect(*I.p(cx + math.cos(a) * d, cy + math.sin(a) * d, cz - d * d * .08), 2, 1, '#3a9a4a' if d % 2 else '#2a7a3a')
    I.c.rect(*I.p(cx, cy, cz + .5), 2, 2, '#6a4a2a')


def house(I, X, Y, k, snow=False, lit=False, t=0):
    wall, wl, wr = [('#f0e0c8', '#e0c8a8', '#c8ac8a'), ('#c8e0f0', '#a8c8e0', '#8aacc8'), ('#f0c8c8', '#e0a8a8', '#c88a8a')][k % 3]
    I.box(X, Y, 0, 14, 12, 10, wall, wl, wr)
    wins = [(X + wx, X + wx + 2.5) for wx in (3, 9)]
    for a, b in wins: I.qy(a, b, Y + 12, 4, 7, '#4a6a8a')
    I.qx(X + 14, Y + 4, Y + 7, 0, 6, '#6a4a3a')
    ym = Y + 6; roof, ridge = ('#f4f8ff', '#ffffff') if snow else ('#c84a3a', '#e86a50')
    I.poly([(X - 1, Y + 13, 10), (X + 15, Y + 13, 10), (X + 15, ym, 16), (X - 1, ym, 16)], roof)
    I.poly([(X + 15, Y - 1, 10), (X + 15, Y + 13, 10), (X + 15, ym, 16)], wr)
    I.poly([(X - 1, ym, 16), (X + 15, ym, 16), (X + 15, ym - .6, 16), (X - 1, ym - .6, 16)], ridge)
    if snow: I.qy(X - 1, X + 15, Y + 13, 9.4, 10, '#c8d4ec')
    I.box(X + 3, Y + 3, 13, 2, 2, 6, '#8a6a5a', '#6a4a3a', '#5a3a2e')
    if lit:
        def em():
            for a, b in wins:
                I.qy(a, b, Y + 12, 4, 7, '#ffd47a'); I.glow((a + b) / 2, Y + 14, 2, 5, '#ffb850', .35)
        I.emit.append(em)
    for i in range(4):                                                 # chimney smoke
        ph = (t * .5 + i / 4) % 1
        x_, y_ = I.p(X + 4, Y + 4, 20 + ph * 14)
        I.c.disc(x_ + ph * 6, y_, 1 + ph * 2.5, '#d8dce4' if ph < .6 else '#b0b6c4')


def lamp(I, X, Y, h=14, cl='#ffd98a'):
    I.box(X, Y, 0, 1, 1, h, '#4a4a54', '#3a3a44', '#2a2a34'); I.box(X, Y, h, 3, 1, 1, '#4a4a54', '#3a3a44', '#2a2a34')
    I.emit.append(lambda: (I.glow(X + 2.5, Y + .5, h - .5, 4, cl, .9), I.glow(X + 3, Y + 1, 0, 14, cl, .35, 7)))


def tower(I, X, Y, dx, dy, h, cols, k, t, neon=None):
    top, left, right = cols
    I.box(X, Y, 0, dx, dy, h, top, left, right)
    I.box(X + 1, Y + 1, h, dx - 2, dy - 2, 1.5, right, left, right)
    wins = []
    for z in range(4, int(h) - 2, 4):
        for i in range(1, int(dx) - 1, 3):
            if hr(k * 101 + z * 7 + i, 3) > .35: wins.append(('y', X + i, z))
        for j in range(1, int(dy) - 1, 3):
            if hr(k * 103 + z * 5 + j, 4) > .35: wins.append(('x', Y + j, z))
    for side, a, z in wins:
        if side == 'y': I.qy(a, a + 1.6, Y + dy, z, z + 1.8, '#2a3048')
        else: I.qx(X + dx, a, a + 1.6, z, z + 1.8, '#2a3048')
    def em():
        for side, a, z in wins:
            on = hr(int(a * 7 + z * 13) + k, 6) > .3 and not (hr(int(a + z) + k, 9) > .93 and math.sin(t * 9 + a) > 0)
            if not on: continue
            cl = '#ffd47a' if hr(int(a * 3 + z) + k, 8) > .35 else '#7ad8f0'
            if side == 'y': I.qy(a, a + 1.6, Y + dy, z, z + 1.8, cl)
            else: I.qx(X + dx, a, a + 1.6, z, z + 1.8, cl)
        if neon:
            on = math.sin(t * 7 + k) > -.7
            if on:
                I.qy(X + 2, X + dx - 2, Y + dy + .1, h * .55, h * .55 + 3, neon)
                I.glow(X + dx / 2, Y + dy + 2, h * .55 + 1.5, 12, neon, .45, 6)
    I.emit.append(em)


def night(c, mul=(.32, .38, .62)): c.a *= np.array(mul, np.float32)


# ============================== scenes ==============================
def sc_town(t):
    c = C(); I = Iso(c, 50, 104, 1.6); s = t * 18
    def g(X, Y):
        a = tex(X, Y, '#78c050', '#6ab448', 8)
        side = ((Y > -11) & (Y < -5)) | ((Y > 18) & (Y < 24))
        a[side] = tex(X, Y, '#e8d8b8', '#dccaa8', 4)[side]
        a[((Y >= -5) & (Y < -4)) | ((Y >= 17) & (Y < 18))] = col('#f4f0e8')
        road = (Y >= -4) & (Y < 17); a[road] = col('#5a5a66')
        a[road & (np.abs(Y - 6.5) < .5) & ((X % 14) < 7)] = col('#f6e6a0')
        return a
    I.ground(g, s)
    for k in range(int(s // 30) - 3, int(s // 30) + 6):
        X = k * 30 - s
        if hr(k, 3) > .3: I.add(X - 18, lambda X=X, k=k: house(I, X - 30, -36, k, t=t))
        I.add(X - 3, lambda X=X: tree(I, X + 10, -16))
        if hr(k, 5) > .45: I.add(X + 35, lambda X=X: tree(I, X + 4, 28))
        if hr(k, 7) > .4: I.add(X + 58, lambda X=X, k=k: house(I, X + 18, 34, k + 1, t=t))
        I.add(X + 14, lambda X=X: I.box(X + 22, -8, 0, 1, 1, 12, '#c8c8d0', '#9a9aa8', '#7a7a88'))
    bz = .5 if math.sin(t * 9) + math.sin(t * 5.3) > 1.5 else 0
    I.add(17, lambda: car(I, 0, 1, '+x', t, 'red', bz))
    I.draw()
    return c.a


RAIN = np.random.default_rng(4).random((90, 3))


def sc_neon(t):
    c = C(); I = Iso(c, 50, 112, 1.6); s = t * 20
    def g(X, Y):
        a = tex(X, Y, '#3a3e4c', '#34384a', 6)
        road = (Y >= -4) & (Y < 17); a[road] = col('#2a2c38')
        a[road & (np.abs(Y - 6.5) < .4) & ((X % 12) < 6)] = col('#c8c0a0')
        wet = road & (((X * 3 + Y * 7).astype(int) % 23) < 4); a[wet] = col('#3a4058')
        a[((Y >= -5) & (Y < -4)) | ((Y >= 17) & (Y < 18))] = col('#6a6e80')
        return a
    I.ground(g, s)
    pal = [('#3a4a6a', '#2a3450', '#1e263e'), ('#4a3a5a', '#382a48', '#281e36'), ('#2a4a5a', '#1e3846', '#162a36')]
    neon = ['#ff4fa0', '#3fe6f0', '#ffb347', '#a07bff']
    for k in range(int(s // 26) - 3, int(s // 26) + 6):
        X = k * 26 - s
        h = 26 + hr(k, 2) * 30
        I.add(X - 30, lambda X=X, k=k, h=h: tower(I, X - 8, -34, 20, 20, h, pal[k % 3], k, t, neon[k % 4] if hr(k, 4) > .4 else None))
        if hr(k, 6) > .5: I.add(X + 40, lambda X=X: lamp(I, X + 4, 19, 14, '#7ad8f0'))
        I.add(X + 10, lambda X=X: lamp(I, X + 14, -7, 14, '#ffd98a'))
    I.add(17, lambda: car(I, 0, 1, '+x', t, 'mint', 0, lights=True))
    I.draw(); night(c, (.42, .48, .72))
    for e in I.emit: e()
    for k in range(int(s // 26) - 3, int(s // 26) + 6):             # neon reflections on the wet road
        X = k * 26 - s
        x_, y_ = I.p(X, 8, 0)
        if 0 < x_ < W: c.glow(x_, y_, 4, neon[k % 4], .25, 10)
    for rx, ry, z in RAIN:
        y = (ry * H + t * (150 + 70 * z)) % (H + 10) - 5; x = (rx * W - t * 30) % W
        c.line(x, y, x - 1, y + 3 + z * 3, '#5a7a98' if z < .6 else '#9abcd8')
    return c.a


def sc_gas(t):
    c = C(); I = Iso(c, 46, 96, 1.9)
    def g(X, Y):
        a = tex(X, Y, '#c8c4bc', '#bcb8b0', 10)
        grass = (X < -14) | (Y > 34) | (Y < -16); a[grass] = tex(X, Y, '#78b050', '#6aa448', 6)[grass]
        a[(np.abs(Y - 30) < .5) & (X > -14)] = col('#f6e080')
        return a
    I.ground(g)
    I.add(-20, lambda: I.box(-6, -14, 0, 28, 10, 12, '#f4ece0', '#e0d4c0', '#c8b8a0'))
    I.add(-19, lambda: (I.qy(0, 8, -4, 3, 9, '#6a9ac8'), I.qy(10, 14, -4, 0, 8, '#4a6a8a'), I.qy(16, 21, -4, 3, 9, '#6a9ac8'),
                        I.qy(-6, 22, -3.9, 10, 12, '#d8402a')))
    for px_ in (2, 16):
        I.add(px_ + 6, lambda px_=px_: (I.box(px_, 8, 0, 4, 3, 9, '#e8e8f0', '#d8402a', '#a83020'),
                                       I.qy(px_ + .6, px_ + 3.4, 11.1, 5, 8, '#3ae0a0')))
    I.add(3, lambda: [I.box(x, y, 0, 1, 1, 18, '#d8d8e0', '#a8a8b8', '#8a8a9a') for x, y in ((-2, 2), (24, 2))])
    I.add(60, lambda: (I.box(-6, -2, 18, 34, 22, 2.5, '#f4f4f8', '#d8402a', '#a83020'), I.qy(-6, 28, 20, 18, 20.5, '#f4f4f8')))
    I.add(30, lambda: car(I, 6, 16, '+x', 0, 'yellow', 0, spin=0))
    I.draw()
    night(c, (.86, .78, .86))
    for e in I.emit: e()
    I.glow(10, 0, 20, 30, '#fff4e0', .35, 14)
    hx_, hy_ = I.p(18, 11, 6); ex, ey = I.p(15, 16, 6)
    c.line(hx_, hy_, ex, ey, '#1a1a20'); c.line(hx_, hy_ + 1, ex, ey + 1, '#1a1a20')
    for i in range(3):
        ph = (t * .7 + i / 3) % 1
        c.px(*I.p(-4 + i * 9, 30, 22 + ph * 6), '#f8f0d8')
    return c.a


SPARK = np.random.default_rng(9).random((40, 3))


def sc_garage(t):
    c = C(); I = Iso(c, 50, 100, 2.1)
    def g(X, Y):
        a = tex(X, Y, '#5a5e6a', '#52566a', 8)
        a[(np.abs(X - 2) < .5) | (np.abs(X - 26) < .5)] = col('#f6c84a')
        stripe = ((X + Y) % 6 < 3) & (Y > 18) & (Y < 21) & (X > 0) & (X < 28); a[stripe] = col('#f6c84a')
        return a
    I.ground(g)
    I.poly([(-30, -14, 0), (60, -14, 0), (60, -14, 40), (-30, -14, 40)], '#3a3e4c')
    I.poly([(-14, -30, 0), (-14, 60, 0), (-14, 60, 40), (-14, -30, 40)], '#2e3240')
    for z in range(4, 40, 6): I.qy(-30, 60, -14, z, z + .4, '#34384a')
    I.add(-40, lambda: [I.box(-10 + i * 8, -13, 0, 7, 5, 9 + (i % 2) * 3, '#d8402a', '#b83020', '#8a2418') for i in range(3)])
    I.add(-40, lambda: [I.qy(-9 + i * 8, -4 + i * 8, -8, z, z + .4, '#f0d0c0') for i in range(3) for z in (3, 6)])
    I.add(-39, lambda: [I.box(28 + j * 7, -12, k * 1.8, 6, 6, 1.6, '#3a3a42', '#26262c', '#1c1c22')   # tyre stacks
                        for j in range(2) for k in range(4)])
    lift = 3 + 6 * (.5 - .5 * math.cos(min(t, 3.2) / 3.2 * math.pi))
    for px_ in (1, 25):
        I.add(-2 + px_, lambda px_=px_: I.box(px_, 2, 0, 2, 2, 20, '#f6c84a', '#d8a830', '#b88a20'))
    I.add(10, lambda: (I.box(3, 4, lift - 1, 22, 13, 1, '#8a8e9a', '#6a6e7a', '#5a5e6a'), car(I, 3, 5, '+x', t, 'blue', lift, spin=0)))
    I.add(40, lambda: I.box(-12, 24, 0, 6, 4, 12, '#3a6ad0', '#2a4ea8', '#1e3a80'))
    I.draw()
    night(c, (.7, .72, .8))
    I.glow(14, 10, 36, 34, '#fff4d8', .3, 30)
    lx, ly = I.p(14, 10, 38); c.rect(lx - 4, ly, 9, 1, '#f8f8ff'); c.rect(lx, ly - 30, 1, 30, '#2a2a30')
    if 1.0 < t % 4 < 3.6:                                                # sparks from the grinder
        sx, sy = I.p(-10, 26, 8)
        for rx, ry, z in SPARK:
            ph = (t * 2 + rx) % 1
            c.px(sx + (ry - .3) * 30 * ph, sy - 10 * ph + 40 * ph * ph * z, '#ffd060' if z > .4 else '#ff8a30')
        c.glow(sx, sy, 6, '#ffd060', .6)
    return c.a


SNOWF = np.random.default_rng(5).random((120, 3))


def sc_snow(t):
    c = C(); I = Iso(c, 60, 92, 1.6); s = t * 16
    def g(X, Y):
        a = tex(X, Y, '#f4f8ff', '#e6eef8', 8)
        road = (X >= -4) & (X < 17); a[road] = tex(X, Y, '#8a90a4', '#80869a', 3)[road]
        a[road & (((X * 5 + Y * 3).astype(int) % 17) < 3)] = col('#d8e0ee')
        a[road & (np.abs(X - 6.5) < .4) & ((Y % 12) < 6)] = col('#e8e0b8')
        a[(X >= -5) & (X < -4) | (X >= 17) & (X < 18)] = col('#ffffff')
        return a
    u = (c.xs - I.ox) / I.k; v = 2 * (c.ys - I.oy) / I.k
    c.a[:] = g((u + v) / 2, (v - u) / 2 + s)
    for k in range(int(s // 28) - 3, int(s // 28) + 6):
        Y = k * 28 - s
        if hr(k, 3) > .25: I.add(Y - 16, lambda Y=Y, k=k: house(I, -34, Y - 4, k, snow=True, lit=True, t=t))
        I.add(Y - 8, lambda Y=Y: tree(I, -16, Y + 10, snow=True))
        if hr(k, 5) > .3: I.add(Y + 40, lambda Y=Y: tree(I, 26, Y + 4, snow=True))
        if hr(k, 7) > .5: I.add(Y + 50, lambda Y=Y, k=k: house(I, 30, Y + 12, k + 2, snow=True, lit=True, t=t))
    I.add(17, lambda: car(I, 1, 0, '+y', t, 'red', 0, lights=True))
    I.draw(); night(c, (.62, .7, .95))
    for e in I.emit: e()
    for rx, ry, z in SNOWF:
        y = (ry * H + t * (12 + 20 * z)) % H; x = (rx * W + math.sin(t * 1.5 + ry * 9) * 3 - t * 6) % W
        c.rect(x, y, 1 + (z > .8), 1 + (z > .8), '#ffffff' if z > .4 else '#c8d4ec')
    return c.a


def sc_beach(t):
    c = C(); I = Iso(c, 46, 104, 1.6); s = t * 18
    def g(X, Y):
        a = tex(X, Y, '#f4dca0', '#ecd294', 6)
        road = (Y >= -4) & (Y < 17); a[road] = col('#6a6670')
        a[road & (np.abs(Y - 6.5) < .4) & ((X % 14) < 7)] = col('#ffffff')
        a[((Y >= -5) & (Y < -4)) | ((Y >= 17) & (Y < 18))] = col('#e8e4dc')
        shore = 30 + 2.5 * np.sin(X * .2 + t * 1.6)
        sea = Y > shore; a[sea] = col('#3ab0c8')
        a[sea & (Y > shore + 8)] = col('#2a90b8'); a[sea & (Y > shore + 20)] = col('#1e74a0')
        a[(Y > shore - 1) & (Y <= shore + .8)] = col('#ffffff')
        sp = sea & (((X * 2 + Y * 5 + t * 30).astype(int) % 29) == 0); a[sp] = col('#c8f4ff')
        a[(Y < -14)] = tex(X, Y, '#7ac060', '#6ab450', 6)[Y < -14]
        return a
    I.ground(g, s)
    for k in range(int(s // 24) - 3, int(s // 24) + 6):
        X = k * 24 - s
        I.add(X - 8, lambda X=X, k=k: palm(I, X + 4, -12, t, k))
        if hr(k, 4) > .45: I.add(X + 26, lambda X=X, k=k: palm(I, X + 10, 22, t, k + 9))
        if hr(k, 6) > .6:
            I.add(X + 30, lambda X=X: (I.box(X + 2, 24, 0, 1, 1, 9, '#f4f4f4', '#d8d8d8', '#b8b8b8'),
                                       I.poly([(X + 2.5, 24.5, 9), (X - 3, 24.5, 6), (X + 8, 24.5, 6)], '#ff5a6a')))
        if hr(k, 8) > .55:
            I.add(X - 10, lambda X=X: I.box(X + 14, -16, 0, 4, 2, 9, '#ffe07a', '#f0b030', '#c88a20'))
    I.add(17, lambda: car(I, 0, 1, '+x', t, 'white', .5 if math.sin(t * 9) + math.sin(t * 5.3) > 1.5 else 0))
    I.draw()
    for i in range(3):
        x_ = (90 - t * 8 + i * 12) % (W + 20) - 10; y_ = 150 + i * 6 + math.sin(t * 1.8 + i) * 2; f = int(t * 6 + i) % 2
        for dx, dy in ((0, 0), (-1, -f), (1, -f), (-2, f - 1), (2, f - 1)): c.px(x_ + dx, y_ + dy, '#f8f8f8')
    return c.a


def sc_show(t):
    c = C(); I = Iso(c, 54, 100, 2.6)
    def g(X, Y):
        a = tex(X, Y, '#2a2c3a', '#262836', 10)
        r = np.sqrt((X - 11) ** 2 + (Y - 11) ** 2)
        a[r < 17] = col('#3a3e52'); a[(r > 16.4) & (r < 17)] = col('#8a8eb0')
        ang = np.arctan2(Y - 11, X - 11) + t * 1.6
        a[(r < 16) & ((ang * 4 / np.pi) % 2 < .08)] = col('#4a4e66')
        return a
    I.ground(g)
    I.poly([(-40, -20, 0), (70, -20, 0), (70, -20, 50), (-40, -20, 50)], '#1e2030')
    I.poly([(-20, -40, 0), (-20, 70, 0), (-20, 70, 50), (-20, -40, 50)], '#181a28')
    d = ['+x', '+y', '-x', '-y'][int(t * 1.6) % 4]
    X, Y = (0, 5.5) if d[1] == 'x' else (5.5, 0)
    car(I, X, Y, d, t, 'red', 0, spin=0)
    night(c, (.75, .72, .9))
    for sx in (-6, 28):
        x_, y_ = I.p(sx, -20, 46); c.glow(x_, y_, 4, '#ffffff', .9)
        I.glow(11, 11, 0, 30, '#f4eaff', .18, 16)
    for i in range(40):                                                     # floor reflection sparkle
        ph = (t * .8 + i / 40) % 1
        if ph < .15: c.px(*I.p(hr(i, 2) * 30 - 4, hr(i, 3) * 30 - 4, 0), '#ffffff')
    x_, y_ = I.p(-10, -19.9, 6)
    c.rect(x_ - 2, y_ - 14, 26, 14, '#ff4fa0')
    tx = x_
    for ch in 'NEW':
        g_ = FONT[ch]
        for j, row in enumerate(g_):
            for i2, b_ in enumerate(row):
                if b_ == '1': c.px(tx + i2 + 2, y_ - 11 + j, '#ffffff')
        tx += len(g_[0]) + 2
    c.glow(x_ + 11, y_ - 7, 18, '#ff4fa0', .3)
    return c.a


def sc_cross(t):
    c = C(); I = Iso(c, 54, 92, 1.5)
    def g(X, Y):
        a = tex(X, Y, '#78c050', '#6ab448', 8)
        rx = (Y >= -4) & (Y < 17); ry = (X >= -4) & (X < 17)
        a[((Y >= -11) & (Y < -4)) | ((Y >= 17) & (Y < 24)) | ((X >= -11) & (X < -4)) | ((X >= 17) & (X < 24))] = col('#dccaa8')
        a[rx | ry] = col('#5a5a66')
        a[rx & ~ry & (np.abs(Y - 6.5) < .4) & ((X % 12) < 6)] = col('#f6e6a0')
        a[ry & ~rx & (np.abs(X - 6.5) < .4) & ((Y % 12) < 6)] = col('#f6e6a0')
        zx = ry & rx
        a[(rx & ((X > 18) & (X < 23)) | ry & ((Y > 18) & (Y < 23))) & (((X + Y).astype(int) % 3) == 0) & ~zx] = col('#f4f4f4')
        return a
    I.ground(g)
    ph = t % 4; green_x = ph < 2
    for k, (X, Y) in enumerate(((-28, -30), (30, -30), (-30, 30), (30, 28))):
        I.add(X + Y, lambda X=X, Y=Y, k=k: house(I, X, Y, k, t=t) if k != 3 else tree(I, X + 4, Y + 4))
    for X, Y in ((-6, 19), (19, -6)):
        I.add(X + Y + 2, lambda X=X, Y=Y: I.box(X, Y, 0, 1, 1, 14, '#4a4a54', '#3a3a44', '#2a2a34'))
        I.add(X + Y + 2.1, lambda X=X, Y=Y: I.box(X - 1, Y - 1, 14, 3, 3, 6, '#2a2a30', '#1e1e24', '#16161a'))
    if green_x:
        x0 = -60 + (ph / 2) * 120; I.add(x0 + 12, lambda: car(I, x0, 1, '+x', t, 'red'))
        I.add(15 + 20, lambda: car(I, 1, 22, '+y', t, 'yellow', spin=0))
    else:
        y0 = -60 + ((ph - 2) / 2) * 130; I.add(y0 + 12, lambda: car(I, 1, y0, '+y', t, 'yellow'))
        I.add(22 + 6, lambda: car(I, 24, 1, '+x', t, 'red', spin=0))
    I.draw()
    for X, Y, axis in ((-6, 19, 'x'), (19, -6, 'y')):
        go = (axis == 'x') == green_x
        for i, cl in enumerate(('#ff3a3a', '#ffc83a', '#3ae070')):
            on = (i == 2 and go) or (i == 0 and not go)
            x_, y_ = I.p(X + 2, Y + .5, 19 - i * 2)
            c.rect(x_ - 1, y_, 2, 2, cl if on else '#3a3a40')
            if on: c.glow(x_, y_ + 1, 4, cl, .5)
    return c.a


SCENES = [('TOWN DRIVE', sc_town), ('NEON NIGHT', sc_neon), ('GAS STOP', sc_gas), ('THE GARAGE', sc_garage),
          ('SNOW VILLAGE', sc_snow), ('BEACH ROAD', sc_beach), ('SHOWROOM', sc_show), ('CROSSROADS', sc_cross)]
DUR = SEGD * len(SCENES)


# ============================== assembly ==============================
def big(k, t):
    a = np.clip(SCENES[k][1](t % SEGD), 0, 255)
    return np.repeat(np.repeat(a, SC, 0), SC, 1)


def label(img, k, lt):
    num, name = f'{k + 1:02d}', SCENES[k][0]
    shown = name[:max(0, int(lt * 22))]
    L = C(layer=True)
    def text(s_, x, y, cl):
        for ch in s_:
            g_ = FONT[ch]
            for j, row in enumerate(g_):
                for i, b_ in enumerate(row):
                    if b_ == '1': L.px(x + i, y + j, cl)
            x += len(g_[0]) + 1
    nx = (W - text_width(num)) // 2; x0 = (W - text_width(name)) // 2
    text(num, nx + 1, 15, '#000000'); text(num, nx, 14, '#ffd36a')
    if shown: text(shown, x0 + 1, 25, '#000000'); text(shown, x0, 24, '#ffffff')
    img[120:330] *= .55
    m = np.repeat(np.repeat(L.m, SC, 0), SC, 1); a = np.repeat(np.repeat(L.a, SC, 0), SC, 1)
    img[m] = a[m]
    return img


def frame(t):
    k = min(len(SCENES) - 1, int(t // SEGD)); lt = t - k * SEGD
    a = big(k, t)
    if k < len(SCENES) - 1 and lt > SEGD - .3:
        f = (lt - (SEGD - .3)) / .3
        b = big(k + 1, t + .3)
        gy, gx = np.mgrid[0:OH // 60, 0:OW // 60]
        m = np.repeat(np.repeat(BAYER[gy % 4, gx % 4] < f, 60, 0), 60, 1)[..., None]
        a = np.where(m, b, a)
    a = label(a.astype(np.float32), k, lt)
    a = a * max(0, min(1, t / .4, (DUR - t) / .6))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def audio(path):
    n = int(SR * DUR); tt = np.arange(n) / SR; r = np.random.default_rng(3); noise = r.standard_normal(n)
    lp = lambda x, k: np.convolve(x, np.ones(k) / k, 'same')
    seg = lambda i: np.clip(np.minimum((tt - i * SEGD + .3) / .3, (i * SEGD + SEGD + .3 - tt) / .3), 0, 1)
    ph = np.cumsum(52 + 3 * np.sin(tt * .7)) / SR
    engine = lp(np.sin(2 * np.pi * ph) * .5 + np.sign(np.sin(4 * np.pi * ph)) * .08, 12) * .1
    engine *= 1 - .8 * (seg(2) + seg(3) + seg(6))
    amb = (lp(noise, 3) * .05 * seg(1) + lp(noise, 300) * 1.2 * seg(4) + lp(noise, 90) * (1 + np.sin(tt * 1.3)) * .9 * seg(5)
           + lp(noise, 400) * .6 * seg(3))
    sparks = lp(noise, 2) * .06 * seg(3) * (np.sin(tt * 40) > .2) * ((tt % SEGD) > 1) * ((tt % SEGD) < 3.6)
    whoosh = sum(lp(noise, 16) * np.exp(-((tt - b * SEGD) / .3) ** 2) * .6 for b in range(1, len(SCENES)))
    tri = lambda f: 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * tt))
    music = np.zeros(n); beat = .25
    chords = [(261.6, 329.6, 392), (220, 261.6, 329.6), (174.6, 220, 261.6), (196, 246.9, 293.7)]
    for i in range(int(DUR / beat)):
        s0 = i * beat; ch = chords[(i // 8) % 4]; f = ch[[0, 1, 2, 1, 2, 1, 0, 2][i % 8]] * 2
        m = (tt >= s0) & (tt < s0 + beat)
        music[m] += tri(f)[m] * np.exp(-(tt[m] - s0) * 7) * .055
        if i % 2 == 0: music[m] += np.exp(-(tt[m] - s0) * 30) * np.sin(2 * np.pi * 55 * (tt[m] - s0)) * .12
        if i % 4 == 2: music[m] += lp(noise, 2)[m] * np.exp(-(tt[m] - s0) * 40) * .05
        if i % 8 == 0:
            m2 = (tt >= s0) & (tt < s0 + beat * 8); music[m2] += tri(ch[0] / 2)[m2] * .03
    mix = engine + amb + sparks + whoosh + music
    mix *= np.clip(np.minimum(tt / .5, (DUR - tt) / .8), 0, 1)
    mix = np.clip(mix / max(1e-6, np.abs(mix).max()) * .8, -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.c_[mix, mix] * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s_ in sys.argv[3:]: frame(float(s_)).save(out / f'f_{s_}.png')
    else:
        out = Path(sys.argv[2]); out.parent.mkdir(parents=True, exist_ok=True)
        wav = out.with_suffix('.wav'); audio(wav)
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}',
                              '-r', str(FPS), '-i', '-', '-i', str(wav), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart',
                              str(out)], stdin=subprocess.PIPE)
        for i in range(int(DUR * FPS)): p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
