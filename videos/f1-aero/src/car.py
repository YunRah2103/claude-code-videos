"""Detailed isometric F1 car (original livery). Local frame: lx forward (0..30), ly across (0..13), z up."""
import math
import numpy as np
from engine import col

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


def to_world(d, X0, Y0, lx, ly, dlx, dly):
    if d == '+x': return X0 + lx, Y0 + ly, dlx, dly
    if d == '-x': return X0 + L_CAR - lx - dlx, Y0 + W_CAR - ly - dly, dlx, dly
    if d == '+y': return X0 + W_CAR - ly - dly, Y0 + lx, dly, dlx
    return X0 + ly, Y0 + L_CAR - lx - dlx, dly, dlx


def pt(d, X0, Y0, lx, ly):
    X, Y, _, _ = to_world(d, X0, Y0, lx, ly, 0, 0); return X, Y


def car_at(cx, cy, d):
    return (cx - L_CAR / 2, cy - W_CAR / 2) if d[1] == 'x' else (cx - W_CAR / 2, cy - L_CAR / 2)


def tyre(I, d, X0, Y0, lxc, side, r, w, Z, t, ghost, spin=16, squash=0.0):
    """Cylinder drawn as stacked discs, sidewall stripe, rim and spinning spokes on the outer face."""
    ax = d[1] == 'x'
    asc = d in ('+x', '-y')                     # larger ly is nearer the camera
    zc = Z + r - squash
    offs = sorted(np.linspace(-w / 2, w / 2, 9), reverse=not asc)
    for i, off in enumerate(offs):
        X, Y = pt(d, X0, Y0, lxc, side + off)
        cl = col(LIV['ghost'] if ghost else '#18191f') * (1.0 + .45 * (i / 8))
        if ax: I.circle_y(X, Y, zc, r, cl)
        else: I.circle_x(X, Y, zc, r, cl)
    X, Y = pt(d, X0, Y0, lxc, side + offs[-1])
    if (side > 6.5) != asc: return              # the visible face is the inner one: no rim detail
    circ = I.circle_y if ax else I.circle_x
    if ghost:
        circ(X, Y, zc, r * .55, '#d8dce4'); return
    circ(X, Y, zc, r * .86, '#e8402a' if w > 3 else '#f6e04a'); circ(X, Y, zc, r * .76, '#22232a')
    circ(X, Y, zc, r * .56, '#9aa0ac'); circ(X, Y, zc, r * .42, '#5a5e6a')
    a = t * spin
    for k in range(5):
        an = a + k * 1.2566
        p0 = (X + math.cos(an) * r * .14, Y, zc + math.sin(an) * r * .14) if ax else (X, Y + math.cos(an) * r * .14, zc + math.sin(an) * r * .14)
        p1 = (X + math.cos(an) * r * .5, Y, zc + math.sin(an) * r * .5) if ax else (X, Y + math.cos(an) * r * .5, zc + math.sin(an) * r * .5)
        I.line(p0, p1, '#c8ccd6')
    circ(X, Y, zc, r * .14, '#f6e04a', 8)


def f1(I, X0, Y0, d, t, Z=0.0, hi=(), flap=0.0, squash=0.0, ghost=False, spin=16, shadow=True, glow_hi=True):
    ax = d[1] == 'x'
    if shadow:
        k = .62 + min(.3, Z * .04)
        q = [pt(d, X0, Y0, lx, ly) for lx, ly in ((2, 1), (28, 1), (28, 12), (2, 12))]
        I.shadow([(x, y, 0) for x, y in q], k)
    pulse = .5 + .5 * math.sin(t * 10)
    items = []
    for name, lx, ly, lz, dlx, dly, dlz, mat in parts(flap):
        X, Y, dx, dy = to_world(d, X0, Y0, lx, ly, dlx, dly)
        z = Z + lz - squash
        items.append((X + dx / 2 + Y + dy / 2 + z * .05, 'box', (name, X, Y, z, dx, dy, dlz, mat)))
    for name, lxc, side, r, w in TYRES:
        X, Y = pt(d, X0, Y0, lxc, side)
        items.append((X + Y + .5 + (1.5 if side > 6.5 else -1.5) * 0, 'tyre', (name, lxc, side, r, w)))
    for _, kind, a in sorted(items, key=lambda q: q[0]):
        if kind == 'tyre':
            name, lxc, side, r, w = a
            tyre(I, d, X0, Y0, lxc, side, r, w, Z if Z > 1 else 0, t, ghost, spin, squash * .3)
            continue
        name, X, Y, z, dx, dy, dz, mat = a
        base = LIV['ghost'] if ghost else LIV[mat]
        if name in hi and not ghost:
            base = tuple(np.clip(col(base) * (1 - .55 * pulse) + col('#ffe86a') * .55 * pulse, 0, 255))
        I.box(X, Y, z, dx, dy, dz, base, edges=not ghost)
    if hi and glow_hi and not ghost:
        for name, lx, ly, lz, dlx, dly, dlz, mat in parts(flap):
            if name in hi:
                X, Y, dx, dy = to_world(d, X0, Y0, lx, ly, dlx, dly)
                I.glow(X + dx / 2, Y + dy / 2, Z + lz + dlz / 2, 10, '#ffe86a', .12 + .1 * pulse)
                break
