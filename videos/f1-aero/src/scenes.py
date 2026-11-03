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


# ---------------------------------------------------------------- full track island
TX, TY, TR, HW = 70.0, 34.0, 10.0, 6.0


def track_sdf(X, Y):
    qx = np.abs(X - TX / 2) - TX / 2 + TR; qy = np.abs(Y - TY / 2) - TY / 2 + TR
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - TR


def track_tex(X, Y):
    d = track_sdf(X, Y)
    a = noise_tex(X, Y, '#62a04a', 10); a[((np.floor(X / 5) + np.floor(Y / 5)) % 2).astype(bool)] *= .94
    corner = (np.abs(X - TX / 2) > TX / 2 - TR - 1) & (np.abs(Y - TY / 2) > TY / 2 - TR - 1)
    grav = corner & (d > HW + 1.5) & (d < HW + 7); a[grav] = noise_tex(X, Y, '#e0cc98', 14)[grav]
    road = np.abs(d) < HW; a[road] = noise_tex(X, Y, '#4c4c58', 8)[road]
    kerb = corner & (np.abs(d) >= HW) & (np.abs(d) < HW + 1.3)
    st = ((np.floor((X + Y) / 2)) % 2).astype(bool); a[kerb & st] = col('#e8402a'); a[kerb & ~st] = col('#f4f4f4')
    a[~corner & (np.abs(d) >= HW) & (np.abs(d) < HW + .5)] = col('#f4f4f4')
    sl = road & (np.abs(X - 22) < 1.2) & (Y > TY - HW)
    a[sl] = np.where(((np.floor(X * 1.6) + np.floor(Y * 1.6)) % 2).astype(bool)[sl][:, None], col('#f4f4f4'), col('#1a1a20'))
    return a


def track_path(s):
    sx, sy, q = TX - 2 * TR, TY - 2 * TR, math.pi * TR / 2
    per = 2 * sx + 2 * sy + 4 * q; s %= per
    segs = [('l', TR, TY, sx, '+x'), ('a', TX - TR, TY - TR, 0), ('l', TX, TY - TR, sy, '-y'), ('a', TX - TR, TR, 1),
            ('l', TX - TR, 0, sx, '-x'), ('a', TR, TR, 2), ('l', 0, TR, sy, '+y'), ('a', TR, TY - TR, 3)]
    for sg in segs:
        ln = sg[3] if sg[0] == 'l' else q
        if s <= ln:
            if sg[0] == 'l':
                _, a, b, _, d = sg
                return {'+x': (a + s, b), '-y': (a, b - s), '-x': (a - s, b), '+y': (a, b + s)}[d] + (d,)
            _, a, b, n = sg; th = s / q * math.pi / 2
            ang = [math.pi / 2, 0, -math.pi / 2, math.pi][n] - th
            dirs = [('+x', '-y'), ('-y', '-x'), ('-x', '+y'), ('+y', '+x')][n]
            return a + TR * math.cos(ang), b + TR * math.sin(ang), dirs[0] if th < math.pi / 4 else dirs[1]
        s -= ln
    return TR, TY, '+x'


def tree(I, X, Y, s=1.0):
    I.box(X + 1.2 * s, Y + 1.2 * s, 0, 1.2 * s, 1.2 * s, 3 * s, '#7a5236')
    I.box(X, Y, 3 * s, 3.6 * s, 3.6 * s, 3 * s, '#3e9a3e'); I.box(X + .6 * s, Y + .6 * s, 6 * s, 2.4 * s, 2.4 * s, 2 * s, '#5ab84e')


def track(t, k=1.3, cam=(84, 168), speed=52, labels_cb=None, extra_cars=()):
    c = C(w=W, h=H); backdrop(c, SUNSET_BG, t, '#ffe6c0')
    I = Iso(c, cam[0], cam[1], k, GOLD)
    X0, X1, Y0, Y1 = -16, 86, -16, 52
    diorama(I, X0, Y0, X1, Y1, 12, track_tex)
    for i in range(6):                                                     # tyre barriers at the corners
        for (bx, by) in ((TX + HW + 6, 4 + i * 1.9), (-HW - 8, TY - 4 - i * 1.9)):
            I.add(bx + by, lambda bx=bx, by=by, i=i: I.box(bx, by, 0, 1.8, 1.8, 2.2, '#1c1c22' if i % 2 else '#e8402a'))
    I.add(TY + 9 + 30, lambda: [I.box(8, TY + 9 + j * 2.4, j * 2.2, 54, 2.4, 2.2, '#8a90a2') for j in range(4)])
    I.add(-HW - 6, lambda: I.box(12, -HW - 12, 0, 46, 5, 6, '#e8e8f0'))
    I.add(-HW - 5.5, lambda: [I.box(14 + g * 9, -HW - 7, .5, 6, .3, 4, '#2a3040') for g in range(5)])
    I.add(22 + TY + 6, lambda: (I.box(21, TY + HW + 1, 0, 1, 1, 9, '#c8ccd8'), I.box(21, TY - HW - 2, 0, 1, 1, 9, '#c8ccd8'),
                                I.box(21, TY - HW - 2, 9, 1, 2 * HW + 4, 1.5, '#1c1c24')))
    for kk, (X, Y) in enumerate(((30, 14), (40, 18), (24, 20), (48, 12), (-12, -12), (80, -12), (82, 46), (-12, 44), (60, 20))):
        I.add(X + Y, lambda X=X, Y=Y, kk=kk: tree(I, X, Y, .9 + .3 * hr(kk, 3)))
    x, y, d = track_path(t * speed)
    cx0, cy0 = CAR.car_at(x, y, d)
    I.add(x + y, lambda: CAR.f1(I, cx0, cy0, d, t, spin=20))
    I.draw()
    for i in range(70):                                                    # crowd
        if hr(i, 9) > .25:
            px_, py_ = I.p(8.5 + hr(i, 3) * 53, TY + 9.5 + (i % 4) * 2.4, (i % 4) * 2.2 + 2.3)
            c.px(px_, py_, ['#f04a4a', '#f6d84a', '#4a8af0', '#f4f4f4', '#3ac860'][(i + int(t * 6 * (hr(i, 2) > .8))) % 5])
    for gx in (14, 23, 32, 41, 50):
        I.glow(gx + 3, -HW - 7, 2.5, 4, '#ffd98a', .5)
    if labels_cb: labels_cb(I)
    return c, I


# ---------------------------------------------------------------- corner island
def corner_tex(X, Y):
    R = 15
    a = noise_tex(X, Y, '#62a04a', 10); a[((np.floor(X / 5) + np.floor(Y / 5)) % 2).astype(bool)] *= .94
    q = (X > 0) & (Y < R); rr = np.hypot(X, Y - R)
    d = np.minimum(np.minimum(np.where(X <= 0, np.abs(Y), 1e9), np.where(q, np.abs(rr - R), 1e9)), np.where(Y >= R, np.abs(X - R), 1e9))
    grav = (X > 0) & (Y < R) & (rr > R + HW + 1.2) | (X > 0) & (Y < -HW - 1.2) | (X > R + HW + 1.2) & (Y < R + 6)
    grav &= (X < R + HW + 16) & (Y > -HW - 18)
    a[grav] = noise_tex(X, Y, '#e0cc98', 14)[grav]
    road = d < HW; a[road] = noise_tex(X, Y, '#4c4c58', 8)[road]
    kerb = q & (d >= HW) & (d < HW + 1.3)
    st = ((np.floor((X + Y) / 2)) % 2).astype(bool); a[kerb & st] = col('#e8402a'); a[kerb & ~st] = col('#f4f4f4')
    return a


def corner_path(s):
    R = 15; q = math.pi * R / 2
    if s < 0: return s, 0.0, '+x'
    if s < q:
        th = s / R; return R * math.sin(th), R - R * math.cos(th), '+x' if th < math.pi / 4 else '+y'
    return float(R), R + (s - q), '+y'


def corner(t, lt):
    c = C(w=W, h=H); backdrop(c, SUNSET_BG, t, '#ffe6c0')
    I = Iso(c, 104, 150, 2.1, GOLD)
    diorama(I, -46, -26, 40, 48, 10, corner_tex)
    for i in range(7): I.add(40 + i, lambda i=i: I.box(36, -20 + i * 2, 0, 2, 2, 2.4, '#1c1c22' if i % 2 else '#e8402a'))
    gx = -44 + 52 * min(lt, 1.15) + max(0, min(lt, 2.3) - 1.15) * 22 * (1 - (min(lt, 2.3) - 1.15) / 2.3)
    wig = math.sin(lt * 16) * 1.4 * (1.2 < lt < 2.3)
    gd = '+x'
    s = -44 + 40 * max(0, lt - .55)
    x, y, d = corner_path(s)
    X0, Y0 = CAR.car_at(x, y, d); gX, gY = CAR.car_at(gx, wig, gd)
    I.add(gx + wig, lambda: CAR.f1(I, gX, gY, gd, t, ghost=True))
    I.add(x + y + .1, lambda: CAR.f1(I, X0, Y0, d, t))
    I.draw()
    if lt > 1.2:
        for i in range(10):
            ph = (lt * 2.5 + i / 10) % 1
            px_, py_ = I.p(gx - 16 - ph * 8, 6.5 + (i - 5) * 1.5, 1 + ph * 4)
            c.disc(px_, py_, 1 + ph * 3, col('#e8d8b0') * (1 - ph * .3))
    return c, I, (gx, wig), (x, y)


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
