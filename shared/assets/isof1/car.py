"""Detailed isometric F1 car (original livery). Local frame: lx forward (0..30), ly across (0..13), z up."""
import math
import numpy as np
from .engine import col

L_CAR, W_CAR = 30.0, 13.0
LIV = dict(blue='#1f4fd6', blue2='#163aa8', white='#eef0f6', yellow='#f6e04a', carbon='#23252f',
           carbon2='#2e3140', dark='#0c0d12', helmet='#f0503c', ghost='#a8aec0', red='#e8402a')


def parts(fo=0.0):
    """(name, lx, ly, lz, dlx, dly, dlz, material). fo = flap opening 0..1."""
    P = [
        ('floor', 3.5, 1.6, .9, 23, 9.8, .55, 'carbon'), ('floor', 0, 3, .9, 3.6, 7, 1.6, 'carbon'),
        ('body', 8, 2.2, 1.45, 11.5, 8.6, 2.4, 'blue'),                       # sidepods
        ('body', 8, 2.2, 3.85, 11.5, .7, .3, 'white'), ('body', 8, 10.1, 3.85, 11.5, .7, .3, 'white'),
        ('inlet', 19.2, 2.4, 2.1, .4, 2.0, 1.6, 'dark'), ('inlet', 19.2, 8.6, 2.1, .4, 2.0, 1.6, 'dark'),
        ('body', 11.5, 3.9, 1.45, 9.5, 5.2, 3.3, 'blue'),                     # monocoque
        ('body', 20.5, 4.9, 1.6, 5.8, 3.2, 2.3, 'blue'), ('body', 26, 5.3, 1.3, 2.6, 2.4, 1.7, 'yellow'),   # nose
        ('body', 4.5, 4.4, 1.45, 8, 4.2, 4.3, 'blue'),                        # engine cover
        ('body', 4.5, 6.2, 5.75, 6.5, .6, 1.9, 'blue2'),                       # shark fin
        ('body', 9.6, 5.0, 5.75, 3.2, 3.0, 1.4, 'carbon'),                     # airbox
        ('body', 9.6, 5.3, 7.15, 2.6, 2.4, .25, 'yellow'),
        ('body', 12, 3.9, 4.75, 9.5, .5, .25, 'yellow'), ('body', 12, 8.6, 4.75, 9.5, .5, .25, 'yellow'),
        ('helmet', 14.2, 5.5, 4.75, 2.3, 2.0, 1.7, 'helmet'), ('helmet', 15.6, 5.6, 5.4, .8, 1.8, .6, 'dark'),
        ('halo', 15.0, 4.4, 6.25, 3.2, .45, .45, 'carbon'), ('halo', 15.0, 8.15, 6.25, 3.2, .45, .45, 'carbon'),
        ('halo', 17.9, 4.4, 6.25, .5, 4.2, .45, 'carbon'), ('halo', 18.1, 6.3, 4.75, .4, .4, 1.6, 'carbon'),
        ('mirror', 17.5, 2.6, 5.0, 1.0, .9, .6, 'blue'), ('mirror', 17.5, 9.5, 5.0, 1.0, .9, .6, 'blue'),
        ('fw', 26.6, -1.0, .55, 3.2, 15.0, .35, 'carbon'),                    # front wing elements
        ('fw', 26.3 + fo * .3, -1.0, 1.05 + fo * .1, 1.8 + fo * .6, 15.0, .35 - fo * .15, 'white'),
        ('fw', 26.0 + fo * .4, -1.0, 1.55 + fo * .1, 1.2 + fo * .6, 15.0, .3 - fo * .12, 'yellow'),
        ('fw', 25.8, -1.3, .5, 4.2, .35, 2.3, 'carbon'), ('fw', 25.8, 13.95, .5, 4.2, .35, 2.3, 'carbon'),
        ('rw', -.3, .5, 2.2, 3.6, .45, 6.6, 'carbon'), ('rw', -.3, 12.05, 2.2, 3.6, .45, 6.6, 'carbon'),
        ('rw', -.25, .5, 6.0, 3.5, .5, .5, 'yellow'), ('rw', -.25, 12.0, 6.0, 3.5, .5, .5, 'yellow'),
        ('rw', 1.6, 6.2, 2.0, .5, .6, 4.6, 'carbon'),                           # swan neck
        ('rw', .2, .95, 6.5, 3.0, 11.1, .55, 'blue'),                           # main plane
        ('rw', .1 + fo * .2, .95, 7.35 + fo * .55, 1.6 + fo * 1.3, 11.1, .95 - fo * .7, 'white'),    # flap
        ('light', -.05, 6.0, 1.8, .2, 1.0, .7, 'red'),
    ]
    return P


TYRES = [('rtyre', 5.2, 0.0, 2.35, 3.2), ('rtyre', 5.2, 13.0, 2.35, 3.2), ('ftyre', 23.0, 0.25, 2.05, 2.7),
         ('ftyre', 23.0, 12.75, 2.05, 2.7)]   # (name, centre lx, side ly, radius, width)
HEAD = {'+x': 0.0, '+y': math.pi / 2, '-x': math.pi, '-y': -math.pi / 2}
VIEW = np.array([1.0, 1.0, 1.25])
LIVERIES = {
    'blue': {}, 'red': dict(blue='#d8302a', blue2='#a82020', yellow='#f4f4f8'),
    'orange': dict(blue='#ff8a1a', blue2='#d06a10', yellow='#1a2a5a'), 'green': dict(blue='#1e8a5a', blue2='#146a44', yellow='#f6e04a'),
    'pink': dict(blue='#f05aa8', blue2='#c03a80', yellow='#7ae8ff'), 'silver': dict(blue='#b8c0cc', blue2='#8a929e', yellow='#2ad0c0'),
}


def car_at(cx, cy, d):
    return (cx - L_CAR / 2, cy - W_CAR / 2) if d[1] == 'x' else (cx - W_CAR / 2, cy - L_CAR / 2)


class Pose:
    def __init__(s, cx, cy, th):
        s.cx, s.cy, s.c, s.s = cx, cy, math.cos(th), math.sin(th)
    def w(s, lx, ly, z):
        a, b = lx - L_CAR / 2, ly - W_CAR / 2
        return (s.cx + a * s.c - b * s.s, s.cy + a * s.s + b * s.c, z)
    def vec(s, fx, fy): return np.array([fx * s.c - fy * s.s, fx * s.s + fy * s.c, 0.0])


def obox(I, P, lx, ly, z, dlx, dly, dz, base, edges=True):
    """Oriented box: cull back faces, shade side faces by their facing, light top edges."""
    cs = [P.w(lx + i * dlx, ly + j * dly, z + k * dz) for k in (0, 1) for j in (0, 1) for i in (0, 1)]
    faces = [((0, 1, 5, 4), P.vec(0, -1)), ((2, 3, 7, 6), P.vec(0, 1)), ((0, 2, 6, 4), P.vec(-1, 0)), ((1, 3, 7, 5), P.vec(1, 0))]
    L = I.L; cb = col(base)
    for idx, n in faces:
        if n @ VIEW <= 0: continue
        nx, ny = max(0, n[0]), max(0, n[1])
        m = (L.left * ny + L.right * nx) / max(1e-6, nx + ny)
        I.poly([cs[i] for i in idx], np.clip(cb * m * L.tint, 0, 255))
        if edges and dz * I.k > 2.5:
            I.line(cs[idx[2]], cs[idx[3]], np.clip(cb * L.top * L.tint * L.edge + 10, 0, 255))
    I.poly([cs[4], cs[5], cs[7], cs[6]], np.clip(cb * L.top * L.tint, 0, 255))


def tyre(I, P, lxc, side, r, w, Z, t, ghost, spin=16, squash=0.0):
    """Cylinder from stacked discs; sidewall stripe, rim and spinning spokes on the outer face."""
    f = P.vec(1, 0); lat = P.vec(0, 1)
    zc = Z + r - squash
    offs = sorted(np.linspace(-w / 2, w / 2, 9), key=lambda o: o * (lat @ VIEW))
    def disc(off, rr, cl, n=18):
        X, Y, _ = P.w(lxc, side + off, 0)
        I.poly([(X + rr * math.cos(a) * f[0], Y + rr * math.cos(a) * f[1], zc + rr * math.sin(a))
                for a in np.linspace(0, 6.283, n)], cl)
    for i, off in enumerate(offs):
        disc(off, r, col(LIV['ghost'] if ghost else '#18191f') * (1.0 + .45 * (i / 8)))
    near = offs[-1]
    outer = near * (side - 6.5) > 0
    if not outer: return
    if ghost: disc(near, r * .55, '#d8dce4'); return
    disc(near, r * .86, '#e8402a' if w > 3 else '#f6e04a'); disc(near, r * .76, '#22232a')
    disc(near, r * .56, '#9aa0ac'); disc(near, r * .42, '#5a5e6a')
    X, Y, _ = P.w(lxc, side + near, 0)
    for k in range(5):
        an = t * spin + k * 1.2566
        p0 = (X + math.cos(an) * r * .14 * f[0], Y + math.cos(an) * r * .14 * f[1], zc + math.sin(an) * r * .14)
        p1 = (X + math.cos(an) * r * .5 * f[0], Y + math.cos(an) * r * .5 * f[1], zc + math.sin(an) * r * .5)
        I.line(p0, p1, '#c8ccd6')
    disc(near, r * .14, '#f6e04a', 8)


def f1h(I, cx, cy, th, t, Z=0.0, hi=(), flap=0.0, squash=0.0, ghost=False, spin=16, shadow=True, glow_hi=True,
        livery='blue'):
    """Draw the car centred at (cx, cy) with heading th (radians, 0 = +X)."""
    P = Pose(cx, cy, th)
    liv = dict(LIV); liv.update(LIVERIES.get(livery, {}))
    if shadow:
        k = .62 + min(.3, Z * .04)
        I.shadow([P.w(lx, ly, 0) for lx, ly in ((2, 1), (28, 1), (28, 12), (2, 12))], k)
    pulse = .5 + .5 * math.sin(t * 10)
    depth = lambda X, Y, z: X + Y + z * .05
    items = []
    for name, lx, ly, lz, dlx, dly, dlz, mat in parts(flap):
        X, Y, _ = P.w(lx + dlx / 2, ly + dly / 2, 0)
        items.append((depth(X, Y, Z + lz), 'box', (name, lx, ly, Z + lz - squash, dlx, dly, dlz, mat)))
    for name, lxc, side, r, w in TYRES:
        X, Y, _ = P.w(lxc, side, 0)
        items.append((depth(X, Y, 0) + .5, 'tyre', (lxc, side, r, w)))
    for _, kind, a in sorted(items, key=lambda q: q[0]):
        if kind == 'tyre':
            lxc, side, r, w = a
            tyre(I, P, lxc, side, r, w, Z if Z > 1 else 0, t, ghost, spin, squash * .3)
            continue
        name, lx, ly, z, dlx, dly, dz, mat = a
        base = liv['ghost'] if ghost else liv[mat]
        if name in hi and not ghost:
            base = tuple(np.clip(col(base) * (1 - .55 * pulse) + col('#ffe86a') * .55 * pulse, 0, 255))
        obox(I, P, lx, ly, z, dlx, dly, dz, base, edges=not ghost)
    if hi and glow_hi and not ghost:
        for name, lx, ly, lz, dlx, dly, dlz, mat in parts(flap):
            if name in hi:
                X, Y, _ = P.w(lx + dlx / 2, ly + dly / 2, 0)
                I.glow(X, Y, Z + lz + dlz / 2, 10, '#ffe86a', .12 + .1 * pulse)
                break


def f1(I, X0, Y0, d, t, **kw):
    """Axis-aligned convenience wrapper: footprint corner (X0, Y0), direction d in {+x,-x,+y,-y}."""
    cx, cy = (X0 + L_CAR / 2, Y0 + W_CAR / 2) if d[1] == 'x' else (X0 + W_CAR / 2, Y0 + L_CAR / 2)
    f1h(I, cx, cy, HEAD[d], t, **kw)
