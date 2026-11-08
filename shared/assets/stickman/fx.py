"""Bold flat FX for the stickman kit (deterministic, time-based): impact burst, smoke puffs, debris, speed lines, spark pop.
All draw with a vec.Pen in its own units; `age` is seconds since the event.

    burst(P, c, age, r=10)        # yellow/white starburst with dark outline + expanding ring (squash-pop timing)
    smoke(P, c, age, n=9, seed=1, r=4, drift=(6, -3))
    debris(P, c, age, n=10, seed=2, speed=40)
    speed_lines(P, t, box, n=14, seed=3, speed=2.0)
    spark(P, c, age, r=3)         # small charge pop
    ghosts(draw_fn, offsets)      # smear helper: call draw_fn(dx, alpha) for each trailing offset
"""
import math, random
from .vec import INK, hexc, shade, mix

YEL = hexc('#ffc928'); WHITE = (255, 255, 255, 255); ORANGE = hexc('#ff8a3d'); SMOKE = hexc('#d9dcdf')


def _ease(x): return 1 - (1 - min(1, max(0, x))) ** 3


def star(c, r0, r1, n, rot=0.0):
    pts = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r0
        a = rot + i * math.pi / n
        pts.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r))
    return pts


def burst(P, c, age, r=10.0, life=0.42):
    if age < 0 or age > life: return
    k = age / life
    s = (0.35 + 1.15 * _ease(k / 0.35)) * (1 - 0.6 * max(0, (k - 0.55) / 0.45))     # pop up, then shrink away
    ring = r * (0.6 + 1.9 * _ease(k))
    P.arc(c, ring, 0, 360, max(2, 0.7 * P.s * (1 - k)), WHITE[:3] + (int(230 * (1 - k)),))
    P.poly(star(c, r * 0.55 * s, r * 1.05 * s, 9, 0.2 + age * 2), YEL, ow=6)
    P.poly(star(c, r * 0.32 * s, r * 0.62 * s, 9, 0.5 - age * 3), WHITE, ow=0)


def smoke(P, c, age, n=9, seed=1, r=4.0, drift=(6.0, -3.0), life=1.6, col=SMOKE):
    if age < 0 or age > life: return
    rnd = random.Random(seed)
    for i in range(n):
        a = rnd.uniform(-math.pi, math.pi); sp = rnd.uniform(0.4, 1.0); rr = r * rnd.uniform(0.6, 1.25)
        lag = rnd.uniform(0, 0.12)
        k = (age - lag) / (life - lag)
        if k <= 0 or k >= 1: continue
        e = _ease(k * 1.6)
        x = c[0] + math.cos(a) * r * 1.6 * sp * e + drift[0] * k
        y = c[1] + math.sin(a) * r * 0.9 * sp * e + drift[1] * k
        R = rr * (0.4 + 0.9 * e) * (1 - k ** 3)
        if R <= 0.05: continue
        P.circle((x, y), R, shade(col, -0.12 - 0.1 * (i % 3)), ow=0)
        P.circle((x - R * 0.22, y - R * 0.25), R * 0.72, shade(col, 0.1), ow=0)


def debris(P, c, age, n=10, seed=2, speed=40.0, g=60.0, size=1.2, cols=None):
    if age < 0 or age > 1.2: return
    rnd = random.Random(seed); cols = cols or [hexc('#e47c4b'), hexc('#c9ccd2'), YEL, INK]
    for i in range(n):
        a = rnd.uniform(-math.pi * 0.95, -0.05); v = speed * rnd.uniform(0.4, 1.0); sz = size * rnd.uniform(0.6, 1.3)
        x = c[0] + math.cos(a) * v * age; y = c[1] + math.sin(a) * v * age + 0.5 * g * age * age
        rot = age * rnd.uniform(-14, 14)
        pts = [(x + math.cos(rot + q) * sz, y + math.sin(rot + q) * sz * 0.7) for q in (0, 2.3, 4.0)]
        P.poly(pts, cols[i % len(cols)], ow=2)


def speed_lines(P, t, box, n=14, seed=3, speed=2.0, col=(255, 255, 255, 150), w=6):
    x0, y0, x1, y1 = box; rnd = random.Random(seed); span = x1 - x0
    for i in range(n):
        y = rnd.uniform(y0, y1); L = rnd.uniform(0.12, 0.3) * span; ph = rnd.uniform(0, 1)
        x = x1 - ((t * speed + ph) % 1.0) * (span + L)
        P.line([(max(x0, x), y), (min(x1, x + L), y)], w * rnd.uniform(0.6, 1.2), col)


def spark(P, c, age, r=3.0, life=0.35):
    if age < 0 or age > life: return
    k = age / life; s = _ease(k / 0.3) * (1 - k)
    P.poly(star(c, r * 0.4 * s + 0.01, r * s + 0.02, 7, age * 5), ORANGE, ow=4)
    P.poly(star(c, r * 0.2 * s + 0.01, r * 0.55 * s + 0.02, 7, -age * 5), YEL, ow=0)
