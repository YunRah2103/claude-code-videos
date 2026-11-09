"""Stick duel teaser: pixel-meadow sword fight, 1280x720 @30fps, 10.1 s.

usage: python render.py still OUTDIR t1 t2 ...   |   python render.py video OUT.mp4
"""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'new-car-trap' / 'src'))
import sfx  # noqa: E402  (reuse whoosh/boom/thump)

DUR = 10.1
FPS, W, H, PX = 30, 1280, 720, 4
ACTION = 5.1              # reference cuts to near-black here; music keeps running
GROUND = 632
INK = (16, 16, 18)
GREEN, GREEN_D = (46, 150, 96), (30, 110, 70)
RED, RED_D = (200, 72, 60), (150, 48, 42)
WHITE = (250, 250, 246)


def ss(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, k): return a + (b - a) * k


def piece(t, pts):
    if t <= pts[0][0]: return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1: return lerp(v0, v1, (t - t0) / (t1 - t0))
    return pts[-1][1]


# ---------------------------------------------------------------- background (320x180 pixel art)
def build_bg():
    w, h = W // PX, H // PX
    rnd = np.random.default_rng(3)
    img = Image.new('RGB', (w, h))
    px = img.load()
    for y in range(h):                                   # sky gradient
        k = min(1, y / 95)
        c = tuple(int(lerp(a, b, k)) for a, b in zip((132, 196, 236), (222, 240, 244)))
        for x in range(w): px[x, y] = c
    d = ImageDraw.Draw(img)
    # cumulus clouds: shade layer then lit layer offset up-left, blocky
    blobs = [(120, 40, 26), (100, 55, 22), (145, 30, 22), (160, 52, 20), (80, 66, 16), (130, 62, 20),
             (235, 40, 22), (262, 28, 24), (290, 44, 22), (310, 30, 18), (250, 62, 18), (205, 66, 14),
             (60, 74, 12), (180, 70, 12)]
    blobs = [(x + rnd.normal(0, r * .5), y + rnd.normal(0, r * .4), r * rnd.uniform(.5, .8)) for x, y, r in blobs for _ in range(3)] + blobs
    for x, y, r in blobs: d.ellipse([x - r, y - r * .8, x + r, y + r * .8], fill=(196, 208, 214))
    for x, y, r in blobs: d.ellipse([x - r * .82 - 3, y - r * .7 - 4, x + r * .7 - 3, y + r * .55 - 4], fill=(246, 248, 246))
    for x, y, r in blobs[::3]: d.ellipse([x - r * .3, y - r * .2, x + r * .5, y + r * .5], fill=(220, 228, 232))
    # far mountains
    for x in range(w):
        m = 70 + 12 * math.sin(x / 26) + 6 * math.sin(x / 9 + 1) + 3 * math.sin(x / 4.3) - 10 * math.exp(-((x - 25) / 30) ** 2)
        m2 = 86 + 7 * math.sin(x / 17 + 2) + 3 * math.sin(x / 6)
        for y in range(int(m), h):
            c = (128, 186, 164) if y < m + 2 else ((96, 160, 140) if rnd.random() > .08 else (112, 174, 152))
            if y > m + 4 and math.sin(x / 7 + y / 5) > .7: c = (80, 140, 124)
            px[x, y] = c
        for y in range(int(m2), h):
            c = (88, 156, 124) if y < m2 + 2 else ((66, 132, 108) if rnd.random() > .08 else (76, 146, 116))
            px[x, y] = c
    # right bush hills with curl outlines
    for cx, cy, r in [(250, 92, 26), (285, 84, 30), (318, 90, 26), (226, 100, 18), (300, 100, 22)]:
        d.ellipse([cx - r, cy - r * .7, cx + r, cy + r * .7], fill=(70, 160, 70))
    for cx, cy, r in [(250, 92, 26), (285, 84, 30), (318, 90, 26), (226, 100, 18)]:
        d.arc([cx - r * .6, cy - r * .5, cx + r * .4, cy + r * .3], 180, 330, fill=(46, 120, 52))
        d.ellipse([cx - r * .6, cy - r * .62, cx + r * .1, cy - r * .3], fill=(120, 200, 90))
    for cx, cy, r in [(40, 100, 20), (10, 104, 16), (80, 104, 14)]:
        d.ellipse([cx - r, cy - r * .6, cx + r, cy + r * .6], fill=(68, 146, 96))
    # tree
    d.rectangle([202, 40, 211, 116], fill=(98, 72, 44)); d.rectangle([202, 40, 204, 116], fill=(126, 94, 58))
    d.line([(206, 70), (220, 58)], fill=(98, 72, 44), width=2); d.line([(206, 80), (192, 70)], fill=(98, 72, 44), width=2)
    for cx, cy, r, c in [(206, 20, 15, (40, 120, 40)), (190, 32, 13, (40, 120, 40)), (222, 34, 13, (40, 120, 40)),
                         (206, 44, 14, (40, 120, 40)), (194, 70, 10, (40, 120, 40)), (220, 62, 10, (40, 120, 40)),
                         (206, 84, 8, (40, 120, 40)),
                         (204, 16, 11, (70, 168, 56)), (190, 28, 9, (70, 168, 56)), (220, 30, 9, (70, 168, 56)),
                         (206, 40, 10, (70, 168, 56)), (194, 66, 7, (70, 168, 56)), (219, 58, 7, (70, 168, 56)),
                         (201, 12, 6, (110, 204, 76)), (187, 25, 5, (110, 204, 76)), (216, 26, 5, (110, 204, 76)),
                         (202, 36, 5, (110, 204, 76)), (191, 63, 4, (110, 204, 76)), (216, 55, 4, (110, 204, 76))]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    for _ in range(160):  # leaf speckle
        x, y = rnd.integers(178, 236), rnd.integers(4, 92)
        if px[x, y][1] > 110 and px[x, y][0] < 120: px[x, y] = (34, 104, 36) if rnd.random() < .5 else (140, 220, 96)
    # meadow
    for y in range(104, h):
        k = (y - 104) / (h - 104)
        for x in range(w):
            c = (lerp(132, 70, k), lerp(206, 160, k), lerp(74, 52, k))
            band = 150 + x * 0.03 + 3 * math.sin(x / 30)          # light dirt path
            if band < y < band + 8 - 4 * abs(math.sin(x / 50)):
                c = (206, 222, 140) if (x + y) % 7 else (184, 168, 112)
            px[x, y] = tuple(int(v) for v in c)
    for x in range(w):                                     # hedge row hides horizon seam
        top = 100 + 3 * math.sin(x / 5) + 2 * math.sin(x / 13)
        for y in range(int(top), 109): px[x, y] = (58, 140, 62) if y < top + 2 else (44, 118, 54)
    for _ in range(1300):                                  # grass blades
        x, y = rnd.integers(0, w), rnd.integers(106, h)
        c = (90, 170, 56) if rnd.random() < .6 else (176, 230, 112)
        if y > 162: c = (52, 132, 48) if rnd.random() < .6 else (110, 190, 70)
        px[x, y] = c
        if y + 1 < h: px[x, y + 1] = c
    for _ in range(260):                                   # flowers, denser near the bottom
        x, y = rnd.integers(0, w), int(h - abs(rnd.normal(0, 22)))
        if 108 < y < h:
            px[x, y] = [(230, 70, 60), (250, 210, 80), (236, 150, 200), (250, 250, 240), (180, 120, 230)][rnd.integers(5)]
    for _ in range(140):
        x, y = rnd.integers(0, w), rnd.integers(160, h)
        px[x, y] = (40, 120, 46)
    big = np.asarray(img.resize((W, H), Image.Resampling.NEAREST)).astype(np.float32)
    lum = big.mean(axis=2, keepdims=True)
    dark = (big * 0.18 + lum * 0.10) + np.array([16, 22, 34], np.float32)   # desaturated night tint
    return big, dark


# ---------------------------------------------------------------- fighters
P = {  # hip-relative joints, facing right: head neck eF hF eB hB kF fF kB fB, sword angle
    'stand':  [(4, -48), (2, -36), (10, -24), (20, -16), (-6, -24), (-10, -10), (8, 18), (6, 38), (-6, 18), (-10, 38), -30],
    'crouch': [(18, -38), (12, -28), (22, -16), (32, -10), (0, -18), (-10, -8), (18, 8), (26, 26), (-14, 12), (-30, 26), 8],
    'run1':   [(14, -46), (10, -35), (16, -22), (26, -24), (-4, -26), (-16, -16), (16, 10), (10, 30), (-8, 20), (-26, 26), -40],
    'run2':   [(14, -46), (10, -35), (18, -22), (28, -28), (-6, -24), (-14, -12), (-4, 18), (-20, 28), (14, 12), (14, 30), -50],
    'windup': [(6, -46), (3, -35), (6, -48), (-6, -58), (-8, -24), (-14, -12), (12, 14), (18, 32), (-10, 16), (-20, 32), -150],
    'slash':  [(20, -40), (14, -30), (30, -22), (44, -14), (0, -22), (-12, -18), (20, 10), (30, 28), (-16, 14), (-34, 28), 20],
    'dash':   [(40, -24), (30, -20), (46, -14), (60, -12), (16, -18), (4, -8), (18, 6), (26, 22), (-20, 10), (-44, 20), 2],
    'spin':   [(0, -42), (0, -31), (18, -30), (34, -32), (-18, -28), (-34, -24), (10, 10), (4, 26), (-10, 10), (-4, 26), 0],
    'jump':   [(6, -44), (4, -34), (4, -48), (-4, -60), (-10, -26), (-18, -18), (14, 2), (4, 14), (-6, 6), (-16, 16), -120],
    'knock':  [(-22, -30), (-16, -22), (4, -30), (14, -40), (-28, -18), (-34, -6), (14, 4), (28, 12), (4, 10), (18, 22), -60],
}
SCALE = 1.75

#        t     x     yoff  pose      face
GK = [(0.00, 240, 0, 'windup', 1), (0.12, 270, 0, 'slash', 1), (0.20, 330, 0, 'dash', 1), (0.32, 470, 0, 'dash', 1),
      (0.48, 420, 0, 'slash', 1), (0.66, 380, 0, 'crouch', 1), (0.80, 80, 0, 'crouch', 1), (1.10, 100, 0, 'stand', 1),
      (1.25, 150, 0, 'run', 1), (1.80, 400, 0, 'windup', 1), (1.98, 440, 0, 'slash', 1), (2.14, 470, 0, 'dash', 1),
      (2.45, 470, 0, 'slash', 1), (2.65, 500, 0, 'crouch', 1), (2.85, 490, 0, 'spin', 1), (3.40, 560, 0, 'spin', 1),
      (3.48, 600, -100, 'jump', 1), (3.66, 640, -40, 'slash', 1), (3.82, 760, 0, 'crouch', -1), (4.36, 780, 0, 'crouch', -1),
      (4.46, 580, 0, 'dash', -1), (4.62, 560, 0, 'slash', -1), (4.80, 510, 0, 'windup', -1), (4.95, 490, 0, 'dash', -1),
      (5.10, 470, 0, 'slash', -1)]
RK = [(0.00, 820, 0, 'crouch', -1), (0.30, 700, 0, 'crouch', -1), (0.50, 660, 0, 'windup', -1), (0.66, 640, 0, 'slash', -1),
      (0.80, 980, 0, 'crouch', -1), (1.10, 960, 0, 'stand', -1), (1.25, 920, 0, 'run', -1), (1.70, 700, 0, 'windup', -1),
      (1.90, 560, 0, 'dash', -1), (1.98, 520, 0, 'slash', -1), (2.20, 600, 0, 'crouch', -1), (2.40, 540, 0, 'windup', -1),
      (2.52, 500, 0, 'slash', -1), (2.80, 680, 0, 'crouch', -1), (3.40, 760, 0, 'crouch', -1), (3.50, 720, -150, 'jump', -1),
      (3.64, 640, -20, 'slash', -1), (3.80, 680, -40, 'knock', -1), (4.00, 650, -110, 'knock', -1), (4.36, 610, -30, 'knock', -1),
      (4.46, 360, 0, 'crouch', 1), (4.62, 390, 0, 'slash', 1), (4.80, 430, 0, 'dash', 1), (5.10, 460, 0, 'slash', 1)]


def pose_pts(name, t):
    if name == 'run':
        k = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 4.5)
        a, b = P['run1'], P['run2']
        return [((lerp(p[0], q[0], k), lerp(p[1], q[1], k)) if isinstance(p, tuple) else lerp(p, q, k)) for p, q in zip(a, b)]
    if name == 'spin':
        a = t * 22
        base = P['spin']
        out = []
        for p in base[:-1]:
            out.append((p[0] * math.cos(a) if p[1] < 0 else p[0], p[1]))
        return out + [math.degrees(a) % 360]
    return P[name]


def fighter_state(keys, t):
    i = max(j for j, k in enumerate(keys) if k[0] <= t) if t >= keys[0][0] else 0
    a = keys[i]
    b = keys[min(i + 1, len(keys) - 1)]
    span = max(1e-6, b[0] - a[0])
    u = (t - a[0]) / span if b is not a else 0
    km = 1 - (1 - min(1, u)) ** 2.2                       # ease-out movement: snappy anime feel
    x, y = lerp(a[1], b[1], km), lerp(a[2], b[2], km)
    kp = ss((t - a[0]) / min(0.1, span)) if b is not a else 0
    pa, pb = pose_pts(a[3], t), pose_pts(b[3], t)
    pts = [((lerp(p[0], q[0], kp), lerp(p[1], q[1], kp)) if isinstance(p, tuple) else lerp(p, q, kp)) for p, q in zip(pa, pb)]
    face = a[4] if u < 0.999 else b[4]
    vx = (b[1] - a[1]) / span * (1 - km + 0.2) if b is not a else 0
    return x, y, pts, face, vx


def draw_fighter(d, keys, t, cloak):
    x, yoff, pts, f, vx = fighter_state(keys, t)
    foot = max(pts[7][1], pts[9][1])
    hip = (x, GROUND - foot * SCALE + yoff)
    J = [(hip[0] + p[0] * SCALE * f, hip[1] + p[1] * SCALE) for p in pts[:-1]]
    head, neck, eF, hF, eB, hB, kF, fF, kB, fB = J
    sw = math.radians(pts[-1])
    swv = (math.cos(sw) * f, math.sin(sw))
    flap = math.sin(t * 40) * 4
    trail = -f * (34 + min(60, abs(vx) * 0.04))
    if cloak == 'red':     # long cape behind body
        d.polygon([(neck[0] - f * 2, neck[1] - 4), (neck[0] + f * 6, neck[1] + 2),
                   (hip[0] + trail * .5, hip[1] + 26 + flap), (hip[0] + trail, hip[1] + 10 - flap),
                   (hip[0] + trail * .8, hip[1] - 10)], fill=RED)
        d.polygon([(neck[0], neck[1] - 2), (hip[0] + trail * .5, hip[1] + 26 + flap),
                   (hip[0] + trail * .25, hip[1] + 18)], fill=RED_D)
    lw = 7
    for a, b in [(hip, kB), (kB, fB), (neck, eB), (eB, hB)]:
        d.line([a, b], fill=INK, width=lw)
    d.line([hip, neck], fill=INK, width=lw + 1)
    if cloak == 'green':   # poncho over torso + trailing scarf
        d.polygon([(neck[0] + f * 8, neck[1] - 2), (neck[0] - f * 8, neck[1] - 2),
                   (hip[0] + trail * .6, hip[1] + 12 + flap), (hip[0] + f * 14, hip[1] + 10)], fill=GREEN)
        d.polygon([(neck[0] - f * 4, neck[1] - 4), (neck[0] + trail * .9, neck[1] - 10 + flap),
                   (neck[0] + trail * .7, neck[1] + 4)], fill=GREEN_D)
    for a, b in [(hip, kF), (kF, fF), (neck, eF), (eF, hF)]:
        d.line([a, b], fill=INK, width=lw)
    for p in J[1:]:
        d.ellipse([p[0] - 3.5, p[1] - 3.5, p[0] + 3.5, p[1] + 3.5], fill=INK)
    r = 11
    d.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=INK)
    tip = (hF[0] + swv[0] * 62, hF[1] + swv[1] * 62)
    d.line([hF, tip], fill=WHITE, width=4)
    d.line([(hF[0] - swv[0] * 8, hF[1] - swv[1] * 8), (hF[0] + swv[0] * 6, hF[1] + swv[1] * 6)], fill=(60, 50, 40), width=6)
    return hip, hF, tip


# ---------------------------------------------------------------- effects
def crescent(d, cx, cy, r, a0, a1, w, col, n=28):
    outer, inner = [], []
    for i in range(n + 1):
        k = i / n
        a = math.radians(lerp(a0, a1, k))
        th = w * math.sin(math.pi * k) ** 0.8
        outer.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8))
        inner.append((cx + math.cos(a) * (r - th), cy + math.sin(a) * (r - th) * 0.8))
    d.polygon(outer + inner[::-1], fill=col)


def slash(d, g, cx, cy, r, a0, sweep, u, col=WHITE, w=14):
    """Crescent that sweeps in (u 0..0.4) then thins out (0.4..1)."""
    if not 0 <= u <= 1: return
    head = a0 + sweep * min(1, u / 0.35)
    tail = a0 + sweep * max(0, (u - 0.35) / 0.65)
    ww = w * (1 - max(0, u - 0.5) * 1.6)
    if abs(head - tail) < 3 or ww < 1: return
    crescent(d, cx, cy, r, tail, head, ww, col)
    crescent(g, cx, cy, r, tail, head, ww * 2.2, col)


def streak(d, g, x0, x1, y, h, col, a=255):
    d.ellipse([min(x0, x1), y - h / 2, max(x0, x1), y + h / 2], fill=col + (a,))
    g.ellipse([min(x0, x1) - 30, y - h * 1.6, max(x0, x1) + 30, y + h * 1.6], fill=col + (a,))


def fire_arc(d, g, cx, cy, rx, ry, a0, a1, w, u):
    for k, (col, ww) in enumerate([((226, 50, 40), w * 1.4), ((255, 150, 50), w * .8), ((255, 232, 120), w * .35)]):
        pts = []
        for i in range(31):
            a = math.radians(lerp(a0, a1, i / 30))
            jit = math.sin(i * 1.7 + u * 30) * w * 0.15
            pts.append((cx + math.cos(a) * (rx + jit), cy + math.sin(a) * (ry + jit)))
        d.line(pts, fill=col, width=max(1, int(ww)), joint='curve')
        if k == 0: g.line(pts, fill=(255, 90, 40), width=int(ww * 2.5), joint='curve')


def puff(d, x, y, r, col, a):
    if a <= 0 or r <= 0: return
    sh = tuple(int(c * .8) for c in col)
    d.ellipse([x - r, y - r * .7, x + r, y + r * .75], fill=sh + (int(a),))
    d.ellipse([x - r * .9, y - r * .8, x + r * .7, y + r * .45], fill=col + (int(a),))


def particles(d, g, cx, cy, spread, u, n, seed, col=(232, 52, 44)):
    rr = np.random.default_rng(seed)
    for _ in range(n):
        ang, sp, sz = rr.uniform(0, 2 * math.pi), rr.uniform(.3, 1), rr.uniform(4, 10)
        x = cx + math.cos(ang) * spread * sp * (0.3 + u)
        y = cy + math.sin(ang) * spread * sp * 0.6 * (0.3 + u) - 30 * u
        s = sz * (1 - u * 0.7)
        d.ellipse([x - s, y - s, x + s, y + s], fill=col)
        g.ellipse([x - s * 2, y - s * 2, x + s * 2, y + s * 2], fill=col)


def bolt(d, g, x0, y0, x1, y1, seed, col=(80, 255, 170)):
    rr = np.random.default_rng(seed)
    pts = [(x0, y0)]
    for i in range(1, 7):
        k = i / 7
        pts.append((lerp(x0, x1, k) + rr.uniform(-22, 22), lerp(y0, y1, k) + rr.uniform(-22, 22)))
    pts.append((x1, y1))
    g.line(pts, fill=col, width=14)
    d.line(pts, fill=col, width=5)
    d.line(pts, fill=(220, 255, 240), width=2)


def spikes(d, g, cx, cy, u, seed):
    rr = np.random.default_rng(seed)
    for _ in range(14):
        a = rr.uniform(-160, -20)
        ln = rr.uniform(60, 190) * math.sin(math.pi * min(1, u * 1.4)) + 1
        bx = cx + rr.uniform(-70, 70)
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        tip = (bx + dx * ln, cy + dy * ln)
        for col, w in [((220, 40, 36), 16), ((255, 140, 50), 8), ((255, 230, 120), 3)]:
            d.polygon([(bx - w * dy, cy + w * dx), (bx + w * dy, cy - w * dx), tip], fill=col)
        g.line([(bx, cy), tip], fill=(255, 80, 40), width=24)


def effects(t, d, g, G, R):
    def win(t0, t1): return (t - t0) / (t1 - t0)
    gx, rx = G[0][0], R[0][0]
    slash(d, g, 250, 520, 70, 200, 200, win(0.0, 0.3), w=16)                     # opening swing
    if 0.18 < t < 0.32: streak(d, g, 260, gx + 40, 540, 18, WHITE, int(255 * (1 - win(0.18, 0.32))))
    if 0.26 < t < 0.5:                                                           # dark flash impact
        u = win(0.26, 0.5)
        streak(d, g, 200, 560, 515, 26 * (1 - u), WHITE)
        slash(d, g, 400, 515, 60, -40, 250, u, w=16)
        slash(d, g, 470, 545, 46, 120, 200, u * 1.2, w=10)
        slash(d, g, 640, 590, 50, 160, 90, u, w=8)
    if 0.56 < t < 0.8:                                                           # fire swirl
        u = win(0.56, 0.8)
        fire_arc(d, g, 470, 500, 140 + 60 * u, 60, 200 + 200 * u, 330 + 200 * u, 22 * (1 - u * .6), u)
        fire_arc(d, g, 560, 470, 110, 90, -60 + 220 * u, 60 + 220 * u, 18 * (1 - u * .6), u)
        streak(d, g, 360, 620, 548, 12 * (1 - u), (255, 220, 120))
        slash(d, g, 640, 560, 48, 140, 150, u, w=10)
    if 0.8 < t < 1.6:                                                            # knockback dust both sides
        u = win(0.8, 1.6)
        for i, (bx, s) in enumerate([(60, 1), (1010, -1)]):
            for j in range(6):
                puff(d, bx + s * (j * 26 - 20 + 14 * math.sin(j * 2.3)) + s * u * 40, 600 - (j % 3) * 22 - u * 20, 40 + 22 * u - j * 2, (238, 242, 238), 230 * (1 - u) ** 1.3)
    if 0.8 < t < 1.0:
        slash(d, g, 120, 520, 56, 220, -200, win(0.8, 1.0), w=12)
    slash(d, g, 300, 520, 50, 200, 180, win(1.32, 1.62), w=12)                   # running swings
    slash(d, g, 870, 540, 52, -20, -180, win(1.40, 1.72), w=12)
    slash(d, g, 560, 530, 54, 20, -200, win(1.70, 2.0), w=12)
    if 1.95 < t < 2.12:                                                          # sword clash spark
        u = win(1.95, 2.12)
        streak(d, g, 420, 560, 520, 30 * (1 - u), WHITE)
        streak(d, g, 470, 510, 500, 0.1 + 50 * (1 - u), WHITE)
    if 2.14 < t < 2.62:                                                          # dark fire dash
        u = win(2.14, 2.62)
        fire_arc(d, g, 420, 520, 90, 46, 120 + 300 * u, 300 + 300 * u, 22, u)
        streak(d, g, 360 + 200 * u, 900, 530, 28 * (1 - u), (255, 214, 120))
        particles(d, g, 470, 540, 120, u, 10, 4)
        slash(d, g, 560, 470, 70, 210, 180, u * 1.3, w=14)
        if t > 2.4: fire_arc(d, g, 500, 520, 50, 120, -110 + 60 * win(2.4, 2.62), 40 + 60 * win(2.4, 2.62), 24, u)
    if 2.6 < t < 2.86:                                                           # big explosion
        u = win(2.6, 2.86)
        r = 60 + 220 * u
        g.ellipse([520 - r * 1.1, 500 - r * .45, 520 + r * 1.1, 500 + r * .45], fill=tuple(int(c * (1 - u)) for c in (255, 190, 60)))
        d.ellipse([520 - r * 1.2, 500 - r * .55, 520 + r * 1.2, 500 + r * .55], fill=(255, 150, 50, int(220 * (1 - u))))
        d.ellipse([520 - r * .8, 500 - r * .3, 520 + r * .8, 500 + r * .3], fill=(255, 238, 150, int(240 * (1 - u))))
        streak(d, g, -40, 1320, 495, 30 * (1 - u), (255, 250, 220))
        fire_arc(d, g, 520, 520, 120, 70, 0 + 200 * u, 300 + 200 * u, 26, u)
    if 2.8 < t < 3.45:                                                           # ring of fire, dust
        u = win(2.8, 3.45)
        cx = lerp(500, 560, u)
        for j in range(5):
            puff(d, cx - 130 + j * 60, 590 - j % 2 * 14, 46 + 20 * u, (176, 140, 96), 190 * (1 - u))
        fire_arc(d, g, cx, 520, 150, 60, 360 * u * 2, 360 * u * 2 + 150, 20 * (1 - u * .5), u)
        fire_arc(d, g, cx, 500, 120, 80, 180 + 360 * u * 2, 300 + 360 * u * 2, 16 * (1 - u * .5), u)
        slash(d, g, cx, 520, 60, 360 * u * 3, 200, (u * 3) % 1, w=12)
        particles(d, g, cx, 520, 160, u, 8, 9)
    slash(d, g, 600, 360, 80, 150, 220, win(3.44, 3.66), w=18)                   # aerial crescent
    if 3.58 < t < 3.84:                                                          # fire crash down
        u = win(3.58, 3.84)
        fire_arc(d, g, 700, 600, 190, 330, 200, 200 + 70 * min(1, u * 2), 34 * (1 - u * .4), u)
        fire_arc(d, g, 690, 600, 150, 300, 205, 205 + 60 * min(1, u * 2), 16, u)
        rr = 80 + 200 * u
        g.ellipse([640 - rr, 590 - 26, 640 + rr, 590 + 26], fill=(255, 220, 90))
        d.ellipse([640 - rr * .8, 590 - 14 * (1 - u), 640 + rr * .8, 590 + 14 * (1 - u)], fill=(255, 236, 140))
        streak(d, g, 440, 860, 592, 16 * (1 - u), (255, 250, 220))
    if 3.78 < t < 4.15:
        spikes(d, g, 720, 600, win(3.78, 4.15), 11)
    if 3.95 < t < 4.45:                                                          # embers + counter slashes
        u = win(3.95, 4.45)
        particles(d, g, 640, 470, 200, u, 14, 21)
        slash(d, g, 690, 560, 50, 160, 160, u * 1.4, w=12)
        slash(d, g, 820, 540, 50, 0, -180, u * 1.2 - 0.2, w=12)
    slash(d, g, 420, 530, 52, -40, 200, win(4.48, 4.72), w=12)                   # final exchange
    slash(d, g, 600, 520, 58, 200, 180, win(4.52, 4.78), w=14)
    if 4.78 < t < ACTION:                                                        # green lightning
        rr = int(t * 30)
        cx = (gx + rx) / 2
        for k in range(3):
            bolt(d, g, cx - 120 + k * 40, 460 + k * 30, cx + 80 - k * 20, 600 - k * 40, rr * 7 + k)
        slash(d, g, cx + 20, 540, 40, 120, 200, win(4.85, 5.1), w=10)


DIM = [(0, 0), (0.12, 0), (0.2, 0.45), (0.27, 1), (0.78, 1), (0.82, 0), (2.12, 0), (2.18, 1), (2.6, 1),
       (2.66, 0.55), (2.84, 0.15), (2.9, 0), (3.42, 0), (3.47, 1), (4.43, 1), (4.47, 0), (4.85, 0.15),
       (5.0, 0.75), (5.1, 0.8)]
HITS = [0.28, 1.98, 2.62, 3.68, 3.82, 4.98]


def frame(t, bg, dark, tail):
    if t >= ACTION:
        return tail
    dim = piece(t, DIM)
    base = bg * (1 - dim) + dark * dim
    sh = sum(18 * math.exp(-(t - h) * 18) for h in HITS if t >= h)
    ox, oy = int(sh * math.sin(t * 91)), int(sh * 0.6 * math.cos(t * 77))
    img = Image.fromarray(np.roll(base, (oy, ox), (0, 1)).clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    G = draw_fighter(d, GK, t, 'green')
    R = draw_fighter(d, RK, t, 'red')
    fx = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gl = Image.new('RGB', (W, H), (0, 0, 0))
    effects(t, ImageDraw.Draw(fx), ImageDraw.Draw(gl), G, R)
    gl = gl.resize((W // 4, H // 4), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.Resampling.BILINEAR)
    img = Image.alpha_composite(img.convert('RGBA'), fx).convert('RGB')
    out = np.asarray(img).astype(np.float32) + np.asarray(gl).astype(np.float32) * 0.75
    return out.clip(0, 255).astype(np.uint8)


def make_tail():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.35 * (((x - W / 2) / W) ** 2 + ((y - H / 2) / H) ** 2)
    return (np.stack([v * 12, v * 12, v * 10], 2)).astype(np.uint8)


# ---------------------------------------------------------------- audio
SR = sfx.SR
rng = np.random.default_rng(5)


def clang(d=0.6):
    t = sfx.T(d)
    s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * r) for f, a, r in
            [(1870, .5, 9), (2630, .4, 12), (3990, .3, 16), (5120, .25, 20), (940, .3, 7)])
    n = rng.standard_normal(len(t)) * np.exp(-t * 60)
    return sfx.fade(s + n * .6) * .7


def crackle(d=0.6):
    t = sfx.T(d)
    n = rng.standard_normal(len(t)) * (rng.random(len(t)) < 0.02) * 3
    roar = sfx.lp(rng.standard_normal(len(t)), 30) * 3
    return sfx.fade((n + roar) * np.sin(np.pi * t / d)) * .6


def zap(d=0.35):
    t = sfx.T(d)
    sq = np.sign(np.sin(2 * np.pi * (180 + 900 * rng.random(len(t)).cumsum() / len(t)) * t))
    return sfx.fade(sq * np.exp(-t * 6) * (rng.random(len(t)) < .6)) * .35


def music(n):
    t = np.arange(n) / SR
    beat = 60 / 150
    out = np.zeros(n)
    k = 0
    while k * beat / 2 < n / SR:
        i = int(k * beat / 2 * SR)
        if k % 4 == 0 or k % 8 == 3: add(out, i, sfx.thump(0.28) * 0.9)
        if k % 4 == 2:
            sn = rng.standard_normal(int(SR * .18)) * np.exp(-sfx.T(.18) * 22)
            add(out, i, sn * .35)
        hh = np.diff(rng.standard_normal(int(SR * .04)), prepend=0) * np.exp(-sfx.T(.04) * 90)
        add(out, i, hh * .25)
        k += 1
    notes = [55, 55, 65.4, 49, 55, 55, 73.4, 65.4]                 # driving minor bass line
    for j in range(int(n / SR / (beat / 2)) + 1):
        f = notes[j % 8]
        seg = sfx.T(beat / 2)
        saw = 2 * ((seg * f) % 1) - 1
        add(out, int(j * beat / 2 * SR), sfx.lp(saw, 12) * np.exp(-seg * 4) * .35)
    pad = sum(np.sin(2 * np.pi * f * t + np.sin(t * 3) * .5) for f in (220, 261.6, 329.6)) * .05
    return out + pad


def add(buf, i, s):
    j = min(len(buf), i + len(s))
    if i < len(buf): buf[i:j] += s[:j - i]


def audio(path):
    n = int(DUR * SR)
    mus = music(n)
    env = np.ones(n)
    a = int(7.0 * SR)
    env[a:] = np.linspace(1, 0, n - a) ** 1.5
    mix = mus * env * 0.55
    ev = [(0.02, sfx.whoosh(0.3, 10)), (0.18, sfx.whoosh(0.25, 6)), (0.28, clang()), (0.28, sfx.boom(0.8) * .8),
          (0.56, crackle(0.4)), (0.58, sfx.whoosh(0.3, 8)), (0.8, sfx.boom(0.6) * .6), (1.32, sfx.whoosh(0.3, 12)),
          (1.4, sfx.whoosh(0.3, 12)), (1.7, sfx.whoosh(0.3, 10)), (1.98, clang(0.8) * 1.1), (2.14, crackle(0.5)),
          (2.16, sfx.whoosh(0.4, 6)), (2.4, clang(0.4) * .6), (2.62, sfx.boom(1.2) * 1.2), (2.8, crackle(0.65)),
          (2.9, sfx.whoosh(0.25, 8)), (3.1, sfx.whoosh(0.25, 8)), (3.3, sfx.whoosh(0.25, 8)), (3.44, sfx.whoosh(0.3, 10)),
          (3.6, crackle(0.4)), (3.68, sfx.boom(1.0)), (3.82, crackle(0.6)), (3.95, clang(0.5) * .7),
          (4.2, sfx.whoosh(0.25, 10)), (4.48, sfx.whoosh(0.3, 10)), (4.6, clang(0.6)), (4.8, zap()), (4.92, zap()),
          (4.98, sfx.boom(1.4) * .9), (4.98, clang(1.0) * .8)]
    for t0, s in ev:
        add(mix, int(t0 * SR), s * 0.8)
    mix = np.tanh(mix * 1.2) * 0.8
    pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def main():
    mode = sys.argv[1]
    bg, dark = build_bg()
    tail = make_tail()
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]:
            Image.fromarray(frame(float(s), bg, dark, tail)).save(out / f'f_{s}.png')
        return
    dst = Path(sys.argv[2]); dst.parent.mkdir(parents=True, exist_ok=True)
    t_end = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    wav = dst.with_suffix('.wav')
    audio(wav)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-i', str(wav), '-t', str(t_end), '-c:v', 'libx264', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(dst)], stdin=subprocess.PIPE)
    for i in range(int(round(t_end * FPS))):
        p.stdin.write(frame(i / FPS, bg, dark, tail).tobytes())
    p.stdin.close()
    sys.exit(p.wait())


if __name__ == '__main__':
    main()
