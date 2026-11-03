"""Environments, smoke and 3D props for the F1 explainer."""
import math
import numpy as np
from engine import (C, col, hr, BAYER, W, H, Iso, Light, tex, noise_tex, diorama, backdrop, blend, ease, lerp)
import car as CAR

GOLD = Light(top=1.06, left=.80, right=.58, tint=(1.06, .96, .86))
LAB = Light(top=1.0, left=.80, right=.60, tint=(.92, 1.0, 1.1))
SUNSET_BG = ['#1c2448', '#3a3a6e', '#8a5a7e', '#e08a6a', '#f6c08a']
LAB_BG = ['#0c1220', '#132036', '#1a2c48', '#16243c']


# ---------------------------------------------------------------- smoke streamlines
def body_h(lx, ly):
    if not (0 <= lx <= 30 and .5 <= ly <= 12.5): return 0.0
    if lx < 3.6: return 8.6
    if lx < 13: return 6.2 if 4 < ly < 9 else 4.3
    if lx < 18.5: return 6.9 if 4 < ly < 9 else 4.3
    if lx < 21: return 5.0 if 4 < ly < 9 else 4.0
    if lx < 26.5: return 4.0 if 4.5 < ly < 8.5 else 1.0
    return 2.0


def smoke(I, t, X0=0.0, Y0=0.0, Z=0.0, lanes=None, speed=34, trail=9, cl='#e6f8ff', alpha=.75, mode='over',
          when='front'):
    """Smoke trails flowing toward -X past a car at (X0, Y0) facing +X."""
    if lanes is None:
        lanes = {'over': [(-2, 2.5), (2.5, 2.0), (4.5, 2.0), (6.5, 2.0), (8.5, 2.0), (10.5, 2.0), (15, 2.5)],
                 'under': [(3, .5), (5, .5), (7, .5), (9, .5)],
                 'front': [(-2.5, 1.2), (1.5, 1.0), (6.5, 1.5), (11.5, 1.0), (15.5, 1.2)],
                 'rear': [(2.5, 3.0), (5, 3.0), (8, 3.0), (10.5, 3.0)],
                 'wake': [(2.5, 2.0), (5, 2.0), (6.5, 2.0), (8, 2.0), (10.5, 2.0)]}[mode]
    for li, (ly0, zb) in enumerate(lanes):
        far = ly0 < 1
        if (when == 'front') == far: continue
        for i in range(8):
            head = 52 - ((t * speed + i * 8.5 + li * 3.1) % 72)
            for j in range(int(trail * 4)):
                u = j / (trail * 4); lx = head + u * trail
                ly, z = ly0, zb
                h = body_h(lx, ly)
                if mode == 'under':
                    if 3 < lx < 27: z = .5
                    else: z = .5 + abs(min(lx - 3, 27 - lx, 0)) * .15
                else:
                    look = max(body_h(lx + d, ly) for d in (0, 1.5, 3))
                    z = max(zb, look + 1.0 + .25 * (look > 0)) if look else zb
                    if mode == 'front' and 19 < lx < 30 and (ly0 < 2 or ly0 > 11):
                        ly = ly0 + (-1 if ly0 < 6.5 else 1) * 1.8 * math.sin(min(1, (30 - lx) / 6) * math.pi / 2)
                    if mode == 'rear' and lx < 4.5:
                        z = 9.2 + (4.5 - lx) * 1.4
                    if mode == 'wake' and lx < 1:
                        amp = min(3.5, -lx * .35)
                        ly = ly0 + amp * math.sin(lx * .9 + t * 8 + li)
                        z = max(zb, 5.5) + amp * math.cos(lx * .9 + t * 8 + li)
                a = alpha * (1 - u) * (.35 + .65 * (1 - abs(u - .15)))
                x_, y_ = I.p(X0 + lx, Y0 + ly, Z + z)
                blend(I.c, x_, y_, cl, min(1, a))


# ---------------------------------------------------------------- 3D arrow
def arrow3d(I, X, Y, z_tip, length, mat='#ff4a3a', w=1.6):
    hd = w * 1.6
    I.box(X - w / 2, Y - w / 2, z_tip + hd * 1.1, w, w, length, mat)
    n = 6
    for j in range(n):
        s = (n - j) / n * hd
        I.box(X - s / 2, Y - s / 2, z_tip + j * hd * .19, s, s, hd * .19, mat, edges=False)


# ---------------------------------------------------------------- wind-tunnel lab
def lab_floor(X, Y):
    a = noise_tex(X, Y, '#3a4052', 6)
    a[(np.abs(X % 6) < .18) | (np.abs(Y % 6) < .18)] = col('#465066')
    r = np.hypot(X - 15, Y - 6.5)
    ring = (r > 18) & (r < 19); a[ring] = col('#5adcf0')
    a[(r < 18)] = (a[(r < 18)] * .85 + col('#2a3040') * .15)
    edge = (X > 44) | (Y > 30)
    st = ((np.floor((X + Y) / 2)) % 2).astype(bool)
    a[edge & st] = col('#f6c84a'); a[edge & ~st] = col('#2a2a30')
    return a


def lab(t, cam=(74, 159), k=4.0, fan=True):
    c = C(w=W, h=H); backdrop(c, LAB_BG, t, '#7ae8ff')
    I = Iso(c, cam[0], cam[1], k, LAB)
    X0, X1, Y0, Y1 = -14, 46, -10, 32
    # back walls
    I.poly([(X0, Y0, 0), (X1, Y0, 0), (X1, Y0, 30), (X0, Y0, 30)], I.lit('#2a3244', 'left'))
    I.poly([(X0, Y0, 0), (X0, Y1, 0), (X0, Y1, 30), (X0, Y0, 30)], I.lit('#2a3244', 'right'))
    for x in range(int(X0), int(X1), 8): I.line((x, Y0, 0), (x, Y0, 30), I.lit('#323c52', 'left'))
    for y in range(int(Y0), int(Y1), 8): I.line((X0, y, 0), (X0, y, 30), I.lit('#323c52', 'right'))
    for z in (9, 18): I.line((X0, Y0, z), (X1, Y0, z), I.lit('#3a4660', 'left')); I.line((X0, Y0, z), (X0, Y1, z), I.lit('#3a4660', 'right'))
    I.qy(X0, X1, Y0 + .05, 21, 21.7, '#7ae8ff'); I.qx(X0 + .05, Y0, Y1, 21, 21.7, '#7ae8ff')
    if fan:                                                    # big fan on the far wall
        cx, cz = 6.5, 11.5
        I.circle_x(X0 + .1, cx, cz, 8.5, '#1a2030', 28); I.circle_x(X0 + .15, cx, cz, 7.8, '#242c3e', 28)
        for b in range(6):
            a = t * 9 + b * 1.047
            I.poly([(X0 + .2, cx, cz), (X0 + .2, cx + 7.4 * math.cos(a), cz + 7.4 * math.sin(a)),
                    (X0 + .2, cx + 7.4 * math.cos(a + .35), cz + 7.4 * math.sin(a + .35))], '#4a5670')
        I.circle_x(X0 + .25, cx, cz, 1.4, '#7ae8ff', 12)
    diorama(I, X0, Y0, X1, Y1, 7, lab_floor, strata=('#3a4052', '#2e3444', '#262b38', '#1f232e', '#191c25'))
    I.glow(15, 6.5, 0, 46, '#5adcf0', .16, 30)
    return c, I


# ---------------------------------------------------------------- straight road diorama (scrolling)
def road_tex(scroll):
    def g(X, Y):
        Xs = X + scroll
        a = noise_tex(Xs, Y, '#62a04a', 10); a[((np.floor(Xs / 6) + np.floor(Y / 6)) % 2).astype(bool)] *= .94
        road = (Y > -9) & (Y < 22); a[road] = noise_tex(Xs, Y, '#4c4c58', 8)[road]
        a[road & (np.abs(Y - 6.5) < 3)] *= .9                               # rubbered racing line
        for y0 in (-9, 20.6):
            k = (Y >= y0) & (Y < y0 + 1.4); st = ((np.floor(Xs / 3)) % 2).astype(bool)
            a[k & st] = col('#e8402a'); a[k & ~st] = col('#f4f4f4')
        a[road & (np.abs(Y - 6.5) < .25) & ((Xs % 14) < 7)] = col('#d8d8e0')
        return a
    return g


def straight(t, speed=90, cam=(74, 159), k=4.0, sky=SUNSET_BG):
    c = C(w=W, h=H); backdrop(c, sky, t, '#ffe6c0')
    I = Iso(c, cam[0], cam[1], k, GOLD)
    s = t * speed
    X0, X1, Y0, Y1 = -14, 46, -16, 30
    diorama(I, X0, Y0, X1, Y1, 9, road_tex(s))
    for kk in range(-2, 6):                                    # barrier posts + billboards sliding past
        X = kk * 16 - (s % 16)
        if X0 < X < X1 - 2:
            I.box(X, Y0 + .5, 0, 1, 1, 4.5, '#c8ccd8')
            if kk % 2 == 0: I.box(X - 6, Y0 + .4, 2, 7, .5, 3, ['#e8402a', '#2a6ad0', '#f6c84a'][(kk + int(s // 16)) % 3])
    for kk in range(-2, 8):
        X = kk * 9 - ((s * 1.0) % 9)
        if X0 < X < X1 - 3: I.box(X, Y1 - 2.2, 0, 3, 1.6, 1.6, '#1c1c22' if kk % 2 else '#e8e8f0')
    I.glow(46, -16, 30, 60, '#ffd8a0', .18, 40)
    return c, I


def tree(I, X, Y, s=1.0):
    I.box(X + 1.2 * s, Y + 1.2 * s, 0, 1.2 * s, 1.2 * s, 3 * s, '#7a5236')
    I.box(X, Y, 3 * s, 3.6 * s, 3.6 * s, 3 * s, '#3e9a3e'); I.box(X + .6 * s, Y + .6 * s, 6 * s, 2.4 * s, 2.4 * s, 2 * s, '#5ab84e')


# ---------------------------------------------------------------- floating wing (analogy)
def wing_section(I, fy, t, X0=-2, Y0=-6, span=26, chord=28, Zc=12):
    """Extruded aerofoil; fy=+1 plane wing (lift up), fy=-1 flipped (F1 wing, pushes down)."""
    xs = np.linspace(0, 1, 30)
    yt = .65 * (.2969 * np.sqrt(xs) - .126 * xs - .3516 * xs ** 2 + .2843 * xs ** 3 - .1015 * xs ** 4)
    yc = np.where(xs < .4, .05 / .16 * (.8 * xs - xs ** 2), .05 / .36 * (.2 + .8 * xs - xs ** 2))
    upz = Zc + fy * (yc + yt) * chord; loz = Zc + fy * (yc - yt) * chord
    Xs = X0 + chord - xs * chord                     # leading edge faces +X (into the wind)
    I.shadow([(X0, Y0, 0), (X0 + chord, Y0, 0), (X0 + chord, Y0 + span, 0), (X0, Y0 + span, 0)], .7)
    top = upz if fy > 0 else loz
    for i in range(29):                              # upper surface strips, lit by angle
        slope = (top[i + 1] - top[i])
        shade = 1.0 + max(-.25, min(.25, slope * .5))
        I.poly([(Xs[i], Y0, top[i]), (Xs[i + 1], Y0, top[i + 1]), (Xs[i + 1], Y0 + span, top[i + 1]), (Xs[i], Y0 + span, top[i])],
               np.clip(I.lit('#2f5fe0', 'top') * shade, 0, 255))
    prof = [(Xs[i], Y0 + span, upz[i]) for i in range(30)] + [(Xs[i], Y0 + span, loz[i]) for i in range(29, -1, -1)]
    I.poly(prof, I.lit('#eef0f6', 'left'))
    ln = [I.p(*q) for q in prof]
    for (x0_, y0_), (x1_, y1_) in zip(ln, ln[1:] + ln[:1]): I.c.line(x0_, y0_, x1_, y1_, '#14161e')
    I.line((Xs[0], Y0 + span, upz[0]), (Xs[0], Y0, upz[0]), '#f6e04a')
    I.box(X0 + chord * .45, Y0 + span * .5 - .6, 0, 1.2, 1.2, min(upz.min(), loz.min()), '#3a4258')


def arrow3d_up(I, X, Y, z_base, length, mat='#3ac860', w=1.6):
    I.box(X - w / 2, Y - w / 2, z_base, w, w, length, mat)
    n = 6
    for j in range(n):
        s = (n - j) / n * 2.4
        I.box(X - s / 2, Y - s / 2, z_base + length + j * .45, s, s, .45, mat, edges=False)


def lift_posts(I, Z, X0=0, Y0=0):
    for lx, ly in ((6, 3), (6, 10), (22, 4.5), (22, 8.5)):
        I.box(X0 + lx - .6, Y0 + ly - .6, 0, 1.2, 1.2, Z + 1.0, '#f6c84a')
        I.box(X0 + lx - 1.2, Y0 + ly - 1.2, 0, 2.4, 2.4, .5, '#3a3a44')
