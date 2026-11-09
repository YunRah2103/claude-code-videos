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
INK = (18, 24, 32)
GREEN, GREEN_D = (40, 122, 82), (28, 92, 64)
RED, RED_D = (178, 72, 62), (130, 50, 46)
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
    """120x68 pixel painting matching the reference layout, upscaled ~10.7x."""
    w, h = 120, 68
    rnd = np.random.default_rng(3)
    img = Image.new('RGB', (w, h))
    d = ImageDraw.Draw(img)
    px = img.load()
    for y in range(h):
        k = min(1, y / 34)
        d.line([(0, y), (w, y)], fill=tuple(int(lerp(a, b, k)) for a, b in zip((196, 227, 248), (212, 233, 248))))

    def blob(cx, cy, r, c, sy=1.0): d.ellipse([cx - r, cy - r * sy, cx + r, cy + r * sy], fill=c)
    SH, LT, HL = (224, 225, 228), (243, 244, 242), (252, 252, 250)
    left = [(43, 4, 6), (40, 11, 7), (47, 13, 7), (37, 19, 7), (52, 19, 7), (58, 11, 5), (61, 21, 6), (33, 27, 6),
            (45, 26, 8), (56, 28, 7), (28, 31, 5), (64, 30, 4), (38, 33, 5)]
    right = [(96, 2, 6), (90, 9, 6), (100, 9, 7), (85, 17, 6), (96, 18, 8), (106, 15, 7), (114, 8, 7), (119, 17, 6),
             (81, 25, 5), (92, 26, 7), (104, 25, 7), (116, 26, 6), (110, 3, 5)]
    small = [(12, 33, 3), (18, 32, 3), (24, 34, 3), (7, 35, 2)]
    m = Image.new('L', (w, h)); md = ImageDraw.Draw(m)
    for cx, cy, r in left + right + small: md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    M = np.asarray(m) > 0
    for y in range(h):                                       # cumulus shading: lit top-left rims, grey undersides
        for x in range(w):
            if not M[y, x]: continue
            up = M[max(0, y - 2), max(0, x - 1)]
            dn = M[min(h - 1, y + 3), x]
            c = LT if rnd.random() > .04 else SH
            if not up: c = HL
            elif not dn or y > 27: c = SH if rnd.random() > .06 else LT
            px[x, y] = c
    # mountains: back light ridge + front darker ridge, slopes shaded by facing
    sr_ = np.random.default_rng(21)
    base = sr_.standard_normal((h, w // 4 + 3))
    STREAK = np.stack([np.interp(np.arange(w) / 4, np.arange(w // 4 + 3), base[y]) for y in range(h)])
    STREAK += 0.6 * np.sin(np.arange(w)[None, :] / 6 + np.arange(h)[:, None] * 1.3)

    def ridge(xs, ys, light, mid, dark, rim):
        top = np.interp(np.arange(w), xs, ys)
        for x in range(w):
            slope = top[min(w - 1, x + 1)] - top[max(0, x - 1)]
            for y in range(int(top[x]), 52):
                c = mid
                if y < top[x] + 1: c = rim
                elif slope > 0.3 and y < top[x] + 6: c = dark
                elif slope < -0.3 and y < top[x] + 4: c = light
                else:                                        # horizontal brush streaks like the reference
                    v = STREAK[y, x]
                    c = dark if v < -0.55 else (light if v > 0.6 else mid)
                px[x, y] = c
        return top
    t1 = ridge([0, 8, 16, 25, 31, 38, 46, 54, 64, 74, 86, 100, 112, 120], [40, 35, 29, 35, 39, 36, 38, 34, 33, 36, 32, 29, 27, 27],
               (126, 198, 160), (86, 150, 118), (54, 110, 82), (150, 210, 172))
    for x0 in [31, 35, 40, 44, 49, 53, 12, 61]:              # snow streaks hugging the slopes
        for k in range(int(rnd.integers(2, 5))):
            x = x0 + k
            if x < w: px[x, int(t1[x]) + 2 + k // 2] = (248, 250, 247)
    ridge([0, 6, 14, 22, 34, 44, 54, 62, 72, 120], [44, 41, 43, 40, 44, 41, 43, 42, 45, 45],
          (100, 172, 128), (64, 128, 94), (38, 94, 68), (118, 186, 140))
    for x0, ht in [(1, 8), (3, 6), (5, 9)]:                  # cypress trees far left
        d.rectangle([x0, 51 - ht, x0 + 1, 51], fill=(29, 92, 73))
    d.rectangle([14, 47, 30, 51], fill=(44, 120, 70)); d.rectangle([16, 46, 26, 47], fill=(44, 120, 70))
    # right bushes: lumpy cloud-shaped mass with dark outlines and curl strokes
    rr = np.random.default_rng(9)
    bush = [(int(rr.uniform(90, 121)), int(rr.uniform(30, 50)), int(rr.uniform(3, 6))) for _ in range(26)]
    bush = [b for b in bush if b[1] > 26 + (120 - b[0]) * 0.3] + [(118, 28, 5), (112, 31, 5), (105, 35, 5), (98, 40, 5), (92, 45, 4), (110, 46, 6)]
    for cx, cy, r in bush: blob(cx, cy, r + 1, (36, 95, 60))
    for cx, cy, r in bush: blob(cx, cy, r, (82, 195, 91))
    for cx, cy, r in bush: blob(cx - 1, cy - 1, r * .5, (110, 212, 112))
    for cx, cy, r in bush[::2]: d.arc([cx - r, cy - r, cx + r, cy + r], 200, 320, fill=(36, 95, 60))
    d.rectangle([86, 49, 120, 51], fill=(68, 160, 76))
    # tree: irregular leafy canopies
    d.rectangle([76, 27, 80, 52], fill=(110, 82, 48)); d.rectangle([79, 27, 80, 52], fill=(88, 64, 38))
    d.rectangle([74, 51, 82, 52], fill=(88, 64, 38))
    for (x0, x1, y0, y1, n) in [(66, 88, 17, 31, 30), (71, 85, 35, 45, 16)]:
        cm = Image.new('L', (w, h)); cd = ImageDraw.Draw(cm)
        for _ in range(n):                                   # leafy clumps
            a, q = rr.uniform(0, 2 * math.pi), math.sqrt(rr.uniform(0, 1))
            cx = (x0 + x1) / 2 + math.cos(a) * q * (x1 - x0) / 2.3
            cy = (y0 + y1) / 2 + math.sin(a) * q * (y1 - y0) / 2.3
            r = rr.uniform(1.6, 3.0)
            cd.ellipse([cx - r, cy - r * .8, cx + r, cy + r * .8], fill=255)
        C = np.asarray(cm) > 0
        for y in range(y0 - 3, y1 + 3):
            for x in range(x0 - 3, x1 + 3):
                if not C[y, x]: continue
                edge = not (C[y - 1, x] and C[y + 1, x] and C[y, x - 1] and C[y, x + 1])
                if edge and rr.random() < .18: continue      # notched silhouette
                lit = not C[y - 2, x - 1]
                c = (36, 95, 60) if edge else ((92, 200, 80) if lit else (67, 171, 58))
                if not edge and rr.random() < .1: c = (44, 130, 52)
                px[x, y] = c
    # meadow
    rows = [(150, 194, 110), (162, 205, 112), (169, 207, 111), (156, 200, 98), (149, 192, 90), (140, 190, 86), (132, 190, 80),
            (124, 195, 78), (120, 196, 76), (118, 194, 74), (112, 186, 70), (106, 178, 66), (100, 170, 62), (96, 166, 60),
            (92, 160, 58), (86, 152, 56), (80, 146, 54)]
    for y in range(51, h):
        for x in range(w):
            px[x, y] = rows[min(len(rows) - 1, y - 51)]
    for x in range(w):                                       # light path, wavy, rising to the right
        c = 57.5 - x * 0.045 + 1.2 * math.sin(x / 9)
        hw = 1.6 + 1.0 * math.sin(x / 14 + 1)
        for y in range(int(c - hw), int(c + hw) + 1):
            if 51 <= y < h: px[x, y] = (238, 242, 190) if abs(y - c) < hw * .5 else (206, 228, 140)
    for x in range(88, 120):
        y = int(53 - (x - 88) * 0.05)
        px[x, y] = (237, 250, 177)
    for x in range(39, 76):                                  # dirt patch
        for y in range(58, 61):
            if abs(x - 57) / 18 + abs(y - 59) / 2 < 1.1:
                px[x, y] = (186, 160, 112) if (x + y) % 5 else (160, 132, 92)
    for _ in range(160):                                     # grass tufts
        x, y = rnd.integers(0, w), rnd.integers(56, h)
        px[x, y] = (68, 148, 76) if y > 62 else (124, 200, 90)
    for x in range(w):                                       # dark grass fringe at bottom
        for y in range(h - 2 - int(1.5 + 1.5 * math.sin(x / 3)), h): px[x, y] = (60, 136, 60)
    for _ in range(70):                                      # flowers, mostly lower corners
        x = int(rnd.choice([rnd.uniform(0, 30), rnd.uniform(85, 120), rnd.uniform(0, 120)]))
        y = rnd.integers(59, h - 1)
        px[min(w - 1, x), y] = [(230, 60, 50), (250, 220, 60), (236, 160, 210)][rnd.integers(3)]
    big = np.asarray(img.resize((W, H), Image.Resampling.NEAREST)).astype(np.float32)
    lum = big.mean(axis=2, keepdims=True)
    dark = big * 0.07 + lum * 0.06 + np.array([18, 26, 36], np.float32)
    return big, dark



# ---------------------------------------------------------------- fighters
P = {  # hip-relative joints, facing right: head neck eF hF eB hB kF fF kB fB, sword angle
    'stand':  [(10, -44), (7, -33), (16, -22), (26, -16), (-4, -22), (-10, -10), (12, 14), (16, 32), (-8, 14), (-16, 32), -30],
    'crouch': [(24, -32), (17, -23), (28, -12), (40, -8), (4, -14), (-8, -6), (20, 6), (30, 24), (-16, 10), (-34, 24), 8],
    'run1':   [(14, -46), (10, -35), (16, -22), (26, -24), (-4, -26), (-16, -16), (16, 10), (10, 30), (-8, 20), (-26, 26), -40],
    'run2':   [(14, -46), (10, -35), (18, -22), (28, -28), (-6, -24), (-14, -12), (-4, 18), (-20, 28), (14, 12), (14, 30), -50],
    'windup': [(12, -40), (8, -30), (10, -42), (-2, -52), (-6, -20), (-14, -10), (16, 8), (26, 26), (-12, 12), (-26, 26), -150],
    'slash':  [(20, -40), (14, -30), (30, -22), (44, -14), (0, -22), (-12, -18), (20, 10), (30, 28), (-16, 14), (-34, 28), 20],
    'dash':   [(40, -24), (30, -20), (46, -14), (60, -12), (16, -18), (4, -8), (18, 6), (26, 22), (-20, 10), (-44, 20), 2],
    'spin':   [(0, -42), (0, -31), (18, -30), (34, -32), (-18, -28), (-34, -24), (10, 10), (4, 26), (-10, 10), (-4, 26), 0],
    'jump':   [(6, -44), (4, -34), (4, -48), (-4, -60), (-10, -26), (-18, -18), (14, 2), (4, 14), (-6, 6), (-16, 16), -120],
    'knock':  [(-22, -30), (-16, -22), (4, -30), (14, -40), (-28, -18), (-34, -6), (14, 4), (28, 12), (4, 10), (18, 22), -60],
}
SCALE = 1.55
GROUND = 622            # world y of feet; converted to screen via camera

# keyframes measured from the reference every 0.1 s, in SCREEN x
GK = [(0.0, 267, 0, 'windup', 1), (0.1, 240, 0, 'slash', 1), (0.2, 413, 0, 'dash', 1), (0.3, 507, 0, 'dash', 1),
      (0.42, 507, 0, 'dash', 1), (0.5, 533, 0, 'slash', 1), (0.62, 560, 0, 'dash', 1), (0.7, 320, 0, 'crouch', 1),
      (0.8, 307, 0, 'crouch', 1), (0.9, 267, 0, 'crouch', 1), (1.0, 240, 0, 'stand', 1), (1.15, 235, 0, 'stand', 1),
      (1.2, 227, 0, 'crouch', 1), (1.3, 267, 0, 'crouch', 1), (1.4, 307, 0, 'stand', 1), (1.5, 320, 0, 'windup', 1),
      (1.65, 325, 0, 'windup', 1), (1.7, 347, 0, 'slash', 1), (1.8, 347, 0, 'crouch', 1), (1.9, 427, 0, 'windup', 1),
      (2.0, 453, 0, 'dash', 1), (2.1, 480, 0, 'dash', 1), (2.2, 500, 0, 'dash', 1), (2.3, 453, 0, 'slash', 1),
      (2.4, 587, 0, 'dash', 1), (2.5, 453, 0, 'crouch', 1), (2.6, 480, 0, 'slash', 1), (2.7, 533, 0, 'dash', 1),
      (2.8, 587, 0, 'spin', 1), (2.9, 533, 0, 'crouch', 1), (3.0, 587, 0, 'windup', 1), (3.1, 693, 0, 'spin', 1),
      (3.3, 693, 0, 'slash', 1), (3.4, 720, 0, 'windup', 1), (3.5, 720, -30, 'windup', 1), (3.6, 747, -70, 'jump', 1),
      (3.7, 1000, -40, 'slash', 1), (3.8, 1000, 0, 'crouch', -1), (3.9, 880, 0, 'crouch', -1), (4.0, 827, 0, 'crouch', -1),
      (4.1, 773, 0, 'crouch', -1), (4.2, 693, 0, 'crouch', -1), (4.3, 773, 0, 'slash', -1), (4.4, 720, 0, 'crouch', -1),
      (4.5, 720, 0, 'crouch', -1), (4.6, 667, 0, 'windup', -1), (4.7, 693, 0, 'slash', -1), (4.8, 693, 0, 'crouch', -1),
      (4.9, 667, 0, 'dash', -1), (5.0, 667, 0, 'slash', -1), (5.1, 660, 0, 'slash', -1)]
RK = [(0.0, 800, 0, 'crouch', -1), (0.1, 773, 0, 'crouch', -1), (0.2, 747, 0, 'dash', -1), (0.3, 747, 0, 'slash', -1),
      (0.4, 747, 0, 'crouch', -1), (0.6, 760, 0, 'crouch', -1), (0.7, 880, 0, 'slash', -1), (0.8, 933, 0, 'crouch', -1),
      (0.9, 933, 0, 'crouch', -1), (1.0, 960, 0, 'stand', -1), (1.1, 987, 0, 'stand', -1), (1.2, 987, 0, 'crouch', -1),
      (1.3, 1000, 0, 'slash', -1), (1.4, 1000, 0, 'stand', -1), (1.5, 987, 0, 'crouch', -1), (1.6, 960, 0, 'slash', -1),
      (1.7, 1000, 0, 'crouch', -1), (1.8, 960, 0, 'dash', -1), (1.9, 747, 0, 'dash', -1), (2.0, 747, 0, 'slash', -1),
      (2.1, 747, 0, 'crouch', -1), (2.2, 800, 0, 'crouch', -1), (2.3, 827, 0, 'crouch', -1), (2.4, 853, 0, 'windup', -1),
      (2.5, 853, 0, 'slash', -1), (2.6, 800, 0, 'crouch', -1), (2.7, 830, 0, 'knock', -1), (2.8, 773, 0, 'crouch', -1),
      (2.9, 960, 0, 'crouch', -1), (3.0, 960, 0, 'windup', -1), (3.1, 1013, 0, 'crouch', -1), (3.3, 987, 0, 'crouch', -1),
      (3.5, 1000, 0, 'windup', -1), (3.6, 987, 0, 'windup', -1), (3.7, 1060, -60, 'knock', -1), (3.8, 960, -200, 'knock', -1),
      (3.9, 720, -230, 'knock', -1), (4.0, 667, -210, 'knock', -1), (4.1, 640, -170, 'knock', -1), (4.2, 640, -190, 'knock', -1),
      (4.3, 613, -200, 'knock', -1), (4.4, 453, 0, 'crouch', 1), (4.5, 480, 0, 'crouch', 1), (4.6, 453, 0, 'windup', 1),
      (4.7, 453, 0, 'slash', 1), (4.8, 427, 0, 'crouch', 1), (5.1, 427, 0, 'crouch', 1)]



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


def draw_fighter(d, keys, t, cloak, z, gy):
    x, yoff, pts, f, vx = fighter_state(keys, t)
    S = SCALE * z
    foot = max(pts[7][1], pts[9][1])
    hip = (x, gy - foot * S + yoff * z)
    J = [(hip[0] + p[0] * S * f, hip[1] + p[1] * S) for p in pts[:-1]]
    head, neck, eF, hF, eB, hB, kF, fF, kB, fB = J
    sw = math.radians(pts[-1])
    swv = (math.cos(sw) * f, math.sin(sw))
    flap = math.sin(t * 40) * 4 * z
    trail = -f * (40 + min(60, abs(vx) * 0.05)) * z

    def at(p, dx, dy): return (p[0] + f * dx * z, p[1] + dy * z)
    if cloak == 'red':     # long cape behind body
        d.polygon([at(neck, 3, -4), at(neck, -6, 0), (hip[0] + trail, hip[1] + 14 * z - flap),
                   (hip[0] + trail * .7, hip[1] + 34 * z + flap), at(hip, 6, 26), at(hip, 6, 6)], fill=RED)
        d.polygon([at(neck, -2, 0), (hip[0] + trail * .7, hip[1] + 34 * z + flap), at(hip, -4, 22)], fill=RED_D)
    lw = max(9, int(10 * z))
    for a, b in [(hip, kB), (kB, fB), (neck, eB), (eB, hB)]:
        d.line([a, b], fill=INK, width=lw)
    d.line([hip, neck], fill=INK, width=lw + 1)
    if cloak == 'green':   # long coat over torso, flaring behind
        d.polygon([at(neck, 10, -4), at(hip, 18, 6), at(hip, 12, 36 + flap / z), (hip[0] + trail, hip[1] + 22 * z - flap),
                   (hip[0] + trail * .8, hip[1] - 4 * z), at(neck, -9, 0)], fill=GREEN)
        d.polygon([at(neck, -4, 0), (hip[0] + trail, hip[1] + 22 * z - flap), (hip[0] + trail * .8, hip[1] - 4 * z)], fill=GREEN_D)
    for a, b in [(hip, kF), (kF, fF), (neck, eF), (eF, hF)]:
        d.line([a, b], fill=INK, width=lw)
    for p in (neck, eF, hF, kF, fF):
        r = lw / 2
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=INK)
    r = 16 * z
    d.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=INK)
    ln = 64 * z
    tip = (hF[0] + swv[0] * ln, hF[1] + swv[1] * ln)
    d.line([hF, tip], fill=WHITE, width=max(9, int(10 * z)))
    return hip, hF, tip


# ---------------------------------------------------------------- effects (screen coords)
def crescent(d, cx, cy, r, a0, a1, w, col, n=28, sy=0.8):
    outer, inner = [], []
    for i in range(n + 1):
        k = i / n
        a = math.radians(lerp(a0, a1, k))
        th = w * math.sin(math.pi * k) ** 0.8
        outer.append((cx + math.cos(a) * r, cy + math.sin(a) * r * sy))
        inner.append((cx + math.cos(a) * (r - th), cy + math.sin(a) * (r - th) * sy))
    d.polygon(outer + inner[::-1], fill=col)


def slash(d, g, cx, cy, r, a0, sweep, u, col=WHITE, w=14, sy=0.8):
    """Crescent that sweeps in (u 0..0.35) then thins away (0.35..1)."""
    if not 0 <= u <= 1: return
    head = a0 + sweep * min(1, u / 0.35)
    tail = a0 + sweep * max(0, (u - 0.35) / 0.65)
    ww = w * (1 - max(0, u - 0.5) * 1.6)
    if abs(head - tail) < 3 or ww < 1: return
    crescent(d, cx, cy, r, tail, head, ww, col, sy=sy)
    crescent(g, cx, cy, r, tail, head, ww * 2.2, col, sy=sy)


def streak(d, g, x0, x1, y, h, col, a=255):
    if h <= 0.5: return
    d.ellipse([min(x0, x1), y - h / 2, max(x0, x1), y + h / 2], fill=col + (a,))
    g.ellipse([min(x0, x1) - 30, y - h * 1.6, max(x0, x1) + 30, y + h * 1.6], fill=col + (a,))


def fire_arc(d, g, cx, cy, rx, ry, a0, a1, w, u):
    for k, (col, ww) in enumerate([((226, 50, 40), w * 1.4), ((255, 150, 50), w * .8), ((255, 232, 120), w * .35)]):
        pts = []
        for i in range(31):
            a = math.radians(lerp(a0, a1, i / 30))
            taper = math.sin(math.pi * (0.1 + 0.8 * i / 30))
            jit = math.sin(i * 1.7 + u * 30) * w * 0.15
            pts.append((cx + math.cos(a) * (rx + jit), cy + math.sin(a) * (ry + jit)))
        d.line(pts, fill=col, width=max(1, int(ww)), joint='curve')
        if k == 0: g.line(pts, fill=(255, 70, 40), width=int(ww * 2.5), joint='curve')


def fire_line(d, g, p0, p1, w):
    for col, ww in [((226, 50, 40), w), ((255, 150, 50), w * .55), ((255, 232, 120), w * .25)]:
        d.line([p0, p1], fill=col, width=max(1, int(ww)))
    g.line([p0, p1], fill=(255, 70, 40), width=int(w * 2.5))


def puff(d, x, y, r, col, a):
    if a <= 0 or r <= 0: return
    sh = tuple(int(c * .82) for c in col)
    d.ellipse([x - r, y - r * .7, x + r, y + r * .75], fill=sh + (int(a),))
    d.ellipse([x - r * .9, y - r * .8, x + r * .7, y + r * .45], fill=col + (int(a),))


def particles(d, g, cx, cy, spread, u, n, seed, col=(232, 52, 44)):
    rr = np.random.default_rng(seed)
    for _ in range(n):
        ang, sp, sz = rr.uniform(0, 2 * math.pi), rr.uniform(.3, 1), rr.uniform(4, 10)
        x = cx + math.cos(ang) * spread * sp * (0.3 + u)
        y = cy + math.sin(ang) * spread * sp * 0.6 * (0.3 + u) - 30 * u
        s = sz * (1 - u * 0.7)
        d.rectangle([x - s, y - s, x + s, y + s], fill=col)
        g.ellipse([x - s * 2.5, y - s * 2.5, x + s * 2.5, y + s * 2.5], fill=col)


def bolt(d, g, x0, y0, x1, y1, seed, col=(70, 240, 170)):
    rr = np.random.default_rng(seed)
    pts = [(x0, y0)]
    for i in range(1, 7):     # jagged forks with sharp kinks
        k = i / 7
        pts.append((lerp(x0, x1, k) + rr.uniform(-30, 30), lerp(y0, y1, k) + rr.uniform(-40, 40)))
    pts.append((x1, y1))
    j = rr.integers(2, 5)     # side branch
    g.line([pts[j], (pts[j][0] + rr.uniform(-50, 50), pts[j][1] + rr.uniform(30, 70))], fill=col, width=10)
    d.line([pts[j], (pts[j][0] + rr.uniform(-50, 50), pts[j][1] + rr.uniform(30, 70))], fill=col, width=4)
    g.line(pts, fill=col, width=16)
    d.line(pts, fill=col, width=6)
    d.line(pts, fill=(220, 255, 240), width=2)


def spikes(d, g, cx, cy, u, seed):
    rr = np.random.default_rng(seed)
    for _ in range(14):
        a = rr.uniform(-165, -15)
        ln = rr.uniform(100, 260) * math.sin(math.pi * min(1, u * 1.4)) + 1
        bx = cx + rr.uniform(-140, 140)
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        tip = (bx + dx * ln, cy + dy * ln)
        for col, w in [((220, 40, 36), 14), ((255, 140, 50), 7), ((255, 230, 120), 3)]:
            d.polygon([(bx - w * dy, cy + w * dx), (bx + w * dy, cy - w * dx), tip], fill=col)
        g.line([(bx, cy), tip], fill=(255, 70, 40), width=24)


def dust(d, x0, x1, y, u, col, seed, big=1.0, towers=True):
    """Smoky dust: low billows plus curling wave crests (drawn on the soft layer)."""
    rr = np.random.default_rng(seed)
    a = int(255 * min(1, (1 - u) / 0.65) ** 0.8)
    if a <= 0: return
    sh = tuple(int(c * .86) for c in col)
    grow = 0.8 + 0.5 * u
    for _ in range(7):
        x = rr.uniform(x0, x1); yy = y - rr.uniform(0, 60 * big)
        r = rr.uniform(45, 80) * big * grow
        x += (x - (x0 + x1) / 2) * u * 0.3
        d.ellipse([x - r, yy - r * .55, x + r, yy + r * .5], fill=sh + (a,))
        d.ellipse([x - r * .85, yy - r * .65, x + r * .6, yy + r * .25], fill=col + (a,))
    for _ in range(3 if towers else 0):                      # rising billows with curled tops
        x = rr.uniform(x0 + 60, x1 - 60); r = rr.uniform(70, 95) * big * grow
        for k in range(3):
            yy = y - 40 * big - k * r * .42 - u * 30
            xx = x + math.sin(k * 1.3 + seed) * r * .3
            d.ellipse([xx - r * (1 - k * .18), yy - r * .6, xx + r * (1 - k * .18), yy + r * .55], fill=sh + (a,))
            d.ellipse([xx - r * (.95 - k * .18), yy - r * .7, xx + r * (.7 - k * .15), yy + r * .3], fill=col + (a,))
        crescent(d, x + r * .2, y - 40 * big - 1.25 * r - u * 30, r * .6, 170, 380, r * .3, sh + (a,), sy=1.0)


def effects(t, d, g, G, R, sd):
    def win(t0, t1): return (t - t0) / (t1 - t0)
    Y = (255, 220, 120)
    slash(d, g, 200, 505, 48, 100, 160, win(-0.05, 0.15), w=14)
    slash(d, g, 295, 520, 45, 260, 120, win(0.08, 0.25), w=12)
    slash(d, g, 400, 560, 50, -100, 330, win(0.15, 0.32), w=12, sy=2.0)
    if 0.27 < t < 0.4:
        u = win(0.27, 0.4)
        streak(d, g, 300, 580, 505, 44 * (1 - u), WHITE)
        slash(d, g, 430, 490, 40, 200, 200, u, w=14)
        slash(d, g, 560, 560, 50, -60, 120, u, w=8)
    if 0.38 < t < 0.56:
        u = win(0.38, 0.56)
        streak(d, g, 540, 900, 482, 24 * (1 - u), WHITE)
        slash(d, g, 427, 493, 35, 180, 240, u, w=10)
        slash(d, g, 380, 470, 30, 200, 180, u - 0.2, w=8)
        particles(d, g, 420, 500, 120, u, 5, 2, col=WHITE)
    if 0.55 < t < 0.68:
        u = win(0.55, 0.68)
        streak(d, g, 80, 960, 452, 30 * (1 - u * .6), Y)
        fire_arc(d, g, 587, 450, 170, 70, 160 + 80 * u, 380 + 80 * u, 24, u)
        fire_arc(d, g, 640, 470, 110, 90, -40 + 120 * u, 120 + 120 * u, 18, u)
        particles(d, g, 600, 450, 160, u, 12, 6, col=(255, 200, 80))
    if 0.65 < t < 0.78:
        u = win(0.65, 0.78)
        fire_arc(d, g, 650, 470, 330, 110, 170 + 60 * u, 330 + 60 * u, 22 * (1 - u * .5), u)
        fire_arc(d, g, 780, 420, 200, 140, -40 + 40 * u, 90 + 40 * u, 18 * (1 - u * .5), u)
        streak(d, g, 560, 720, 510, 16 * (1 - u), Y)
        slash(d, g, 330, 500, 40, 100, 160, u, w=12)
        slash(d, g, 900, 500, 45, -60, 160, u, w=12)
    if 0.74 < t < 0.87:
        u = win(0.74, 0.87)
        fire_line(d, g, (330, 340), (lerp(330, 600, min(1, u * 2)), lerp(340, 650, min(1, u * 2))), 24 * (1 - u * .6))
        particles(d, g, 470, 500, 220, u, 14, 8)
        streak(d, g, 360, 520, 525, 14 * (1 - u), Y)
    if 0.78 < t < 1.22:
        u = win(0.78, 1.22)
        dust(sd, -40, 320, 630, u, (248, 250, 246), 1, big=1.1)
        dust(sd, 960, 1320, 630, u, (248, 250, 246), 2, big=1.1)
    slash(d, g, 225, 505, 45, 100, 160, win(0.95, 1.12), w=12)
    slash(d, g, 930, 520, 60, 300, -110, win(1.25, 1.42), w=8)
    slash(d, g, 290, 470, 45, 100, 170, win(1.45, 1.62), w=13)
    slash(d, g, 300, 445, 48, 120, 150, win(1.55, 1.72), w=13)
    slash(d, g, 960, 470, 40, 280, -90, win(1.6, 1.75), w=8)
    slash(d, g, 330, 455, 50, 100, 170, win(1.65, 1.82), w=13)
    slash(d, g, 420, 425, 60, 200, 140, win(1.85, 2.0), w=14, sy=0.5)
    slash(d, g, 560, 520, 50, -80, 160, win(1.95, 2.1), w=14)
    slash(d, g, 573, 550, 62, -90, 180, win(2.05, 2.2), w=16)
    if 2.15 < t < 2.32:
        u = win(2.15, 2.32)
        fire_arc(d, g, 330, 470, 90, 50, 90 + 60 * u, 300 + 60 * u, 22, u)
        slash(d, g, 380, 440, 110, 200, 140, u, w=12, sy=0.3)
        streak(d, g, 320, 1060, 490, 36 * (1 - u * .5), Y)
    if 2.25 < t < 2.42:
        u = win(2.25, 2.42)
        slash(d, g, 500, 425, 110, 200, 140, u, w=14, sy=0.35)
        particles(d, g, 450, 505, 200, u, 12, 12, col=(255, 120, 40))
        fire_arc(d, g, 570, 500, 70, 40, 0, 200, 16, u)
        streak(d, g, 250, 650, 510, 20 * (1 - u), Y)
    if 2.35 < t < 2.5:
        u = win(2.35, 2.5)
        particles(d, g, 400, 490, 80, u, 8, 14)
        slash(d, g, 613, 430, 40, -90, 180, u, w=12)
        slash(d, g, 853, 480, 45, -60, 200, u, w=8)
    if 2.42 < t < 2.67:
        u = win(2.42, 2.67)
        a = -100 + 170 * min(1, u * 2)       # tall ')' crescent sweeping top -> bottom
        for col, w, r in [((200, 30, 36), 90, 260), ((240, 60, 50), 60, 248), ((255, 120, 110), 22, 225)]:
            if u < 0.85: crescent(d, 560, 440, r, -100, a, w * (1 - u * .5), col, sy=1.0)
        crescent(g, 560, 440, 260, -100, a, 120, (255, 40, 40), sy=1.0)
        crescent(d, 560, 460, 190, -85, a - 10, 34 * (1 - u), WHITE, sy=1.0)
        streak(d, g, 250, 1000, 530, 28 * (1 - u), WHITE)
        particles(d, g, 650, 520, 260, u, 10, 15)
    if 2.56 < t < 2.7:
        u = win(2.56, 2.7)
        slash(d, g, 480, 570, 90, 20, 140, u, w=16, sy=0.3)
        slash(d, g, 745, 560, 50, 0, 120, u, w=6)
        slash(d, g, 660, 380, 60, 200, 120, u, col=(220, 50, 40), w=12)
    if 2.64 < t < 2.82:
        u = win(2.64, 2.82)
        streak(d, g, -60, 1340, 330, 70 * (1 - u * .7), (255, 238, 160))
        g.ellipse([400, 230, 1040, 430], fill=tuple(int(c * (1 - u)) for c in (255, 200, 80)))
        fire_arc(d, g, 600, 500, 220, 150, 100 + 220 * u, 330 + 220 * u, 30 * (1 - u * .4), u)
        fire_arc(d, g, 610, 520, 150, 95, 300 + 220 * u, 500 + 220 * u, 24 * (1 - u * .4), u)
        fire_arc(d, g, 600, 480, 80, 50, 0 + 300 * u, 200 + 300 * u, 16, u)
    if 2.74 < t < 2.86:
        u = win(2.74, 2.86)
        fire_arc(d, g, 470, 420, 330, 190, 150 + 40 * u, 270 + 40 * u, 26 * (1 - u * .5), u)
        fire_arc(d, g, 520, 470, 260, 120, 30 + 40 * u, 150 + 40 * u, 18 * (1 - u * .5), u)
        streak(d, g, 330, 650, 560, 18 * (1 - u), WHITE)
        slash(d, g, 500, 430, 60, 200, 150, u, w=14)
    if 2.75 < t < 3.25:
        u = win(2.75, 3.25)
        dust(sd, 600, 860, 660, u, (176, 140, 96), 3, big=1.1, towers=False)
    if 2.85 < t < 3.2:
        u = win(2.85, 3.2)
        dust(sd, 160, 1100, 690, u, (160, 128, 88), 4, big=1.4, towers=False)
        fire_arc(d, g, 590, 600, 50, 60, 100 + 300 * u, 300 + 300 * u, 18 * (1 - u), u)
        streak(d, g, 520, 660, 590, 26 * (1 - u), (255, 200, 90))
        particles(d, g, 620, 390, 60, u, 6, 16)
        fire_arc(d, g, 650, 330, 90, 40, 190 + 90 * u, 350 + 90 * u, 22 * (1 - u * .7), u)
        particles(d, g, 560, 560, 60, u, 6, 17, col=(255, 180, 60))
    slash(d, g, 560, 420, 60, 200, 150, win(2.84, 3.0), w=14)
    slash(d, g, 500, 440, 60, 200, 150, win(2.95, 3.1), w=14)
    if 3.05 < t < 3.22:
        u = win(3.05, 3.22)
        fire_arc(d, g, 700, 450, 120, 60, 360 * u * 1.5, 360 * u * 1.5 + 220, 18, u)
        slash(d, g, 700, 440, 50, 120, 180, u, w=12)
        streak(d, g, 560, 720, 470, 16 * (1 - u), Y)
    if 3.15 < t < 3.32:
        u = win(3.15, 3.32)
        fire_arc(d, g, 650, 540, 90, 120, 360 * u + 90, 360 * u + 330, 20, u)
        slash(d, g, 650, 520, 60, 160, 180, u, w=12)
    if 3.25 < t < 3.42:
        u = win(3.25, 3.42)
        particles(d, g, 600, 420, 70, u, 6, 18)
        slash(d, g, 600, 420, 45, 180, 160, u, w=12)
    slash(d, g, 650, 400, 70, 180, 170, win(3.35, 3.6), w=22)
    slash(d, g, 990, 480, 40, -60, 120, win(3.38, 3.6), w=8)
    slash(d, g, 720, 390, 62, 190, 150, win(3.55, 3.7), w=16, sy=0.5)
    slash(d, g, 970, 480, 40, -80, 120, win(3.55, 3.7), w=8)
    if 3.62 < t < 3.73:
        u = win(3.62, 3.73)
        k = min(1, u * 2.2)
        fire_arc(d, g, 900, 330, 300, 235, 180, 180 - 90 * k, 34 * (1 - u * .4), u)
        fire_arc(d, g, 890, 340, 260, 210, 185, 185 - 85 * k, 16, u)
        if k > .8:
            rr = 120 + 220 * u
            g.ellipse([850 - rr, 560 - 30, 850 + rr, 560 + 30], fill=(255, 220, 90))
            d.ellipse([850 - rr * .8, 560 - 16 * (1 - u), 850 + rr * .8, 560 + 16 * (1 - u)], fill=(255, 240, 150))
            streak(d, g, 620, 1180, 562, 18 * (1 - u), (255, 252, 230))
    if 3.7 < t < 3.98:
        u = win(3.7, 3.98)
        spikes(d, g, 1080, 580, u, 11)
        fire_arc(d, g, 1110, 440, 120, 170, 190, 350, 22 * (1 - u * .6), u)
        fire_arc(d, g, 1090, 430, 80, 120, 200, 330, 12 * (1 - u * .6), u)
        streak(d, g, 860, 1060, 568, 14 * (1 - u), (255, 120, 80))
    if 3.85 < t < 4.4:
        u = win(3.85, 4.4)
        particles(d, g, 870, 420, 420, u, 26, 21)
    slash(d, g, 960, 520, 45, -60, 160, win(3.95, 4.1), w=12)
    slash(d, g, 935, 500, 40, -80, 160, win(4.05, 4.2), w=12)
    slash(d, g, 900, 480, 45, -80, 160, win(4.15, 4.3), w=12)
    slash(d, g, 830, 480, 40, -80, 160, win(4.28, 4.42), w=12)
    slash(d, g, 780, 430, 30, 200, 120, win(4.28, 4.42), w=6, sy=0.4)
    slash(d, g, 827, 440, 55, 200, 150, win(4.4, 4.55), w=14, sy=0.5)
    slash(d, g, 480, 470, 40, -90, 160, win(4.42, 4.57), w=8)
    slash(d, g, 827, 420, 50, 200, 150, win(4.5, 4.62), w=14, sy=0.5)
    slash(d, g, 587, 460, 55, -90, 180, win(4.58, 4.72), w=16)
    slash(d, g, 560, 480, 50, -90, 180, win(4.68, 4.8), w=16)
    if 4.78 < t < ACTION:
        rr = int(t * 30)
        for k, (a, b, c, e) in enumerate([(300, 560, 470, 470), (430, 520, 600, 400), (560, 430, 760, 540), (380, 420, 420, 560)]):
            bolt(d, g, a, b, c, e, rr // 2 * 7 + k)
        streak(d, g, 330, 760, 505, 10, WHITE)
        slash(d, g, 570, 500, 40, -90, 200, win(4.85, 5.05), w=12)


DIM = [(0, 0), (0.12, 0), (0.2, 0.5), (0.3, 0.8), (0.36, 1), (0.65, 1), (0.7, 0.6), (0.8, 0.35), (0.88, 0), (2.05, 0),
       (2.1, 0.5), (2.17, 0.95), (2.5, 0.92), (2.6, 0.8), (2.68, 0.4), (2.8, 0.1), (2.88, 0), (3.42, 0), (3.5, 0.4),
       (3.57, 0.92), (4.3, 0.92), (4.4, 0.7), (4.5, 0.45), (4.58, 0), (4.85, 0), (4.9, 0.55), (5.0, 0.85), (5.1, 0.9)]
VIG = [(0, 0), (0.62, 0), (0.68, 1), (0.85, 0.8), (0.9, 0), (2.6, 0), (2.66, 0.8), (2.85, 0.5), (2.92, 0), (5.1, 0)]
CZ = [(0, 1), (2.55, 1), (2.75, 1.1), (4.4, 1.12), (5.1, 1.15)]
CX = [(0, 640), (2.55, 640), (2.8, 670), (3.3, 690), (5.1, 695)]
CY = [(0, 360), (2.55, 360), (2.8, 375), (5.1, 380)]
HITS = [0.3, 0.58, 2.0, 2.47, 2.65, 3.72, 3.8, 4.9]
CPX, FPX = 8, 5            # pixel size of characters and of effects, in output px


def pixelate(layer, k, cut=90):
    """Downsample an RGBA layer to a k-px grid, hard-threshold alpha, upscale with nearest: crisp pixel art."""
    small = layer.resize((round(W / k), round(H / k)), Image.Resampling.BOX)
    a = np.asarray(small).copy()
    on = a[..., 3] > cut
    a[..., 3] = np.where(on, 255, 0)
    return Image.fromarray(a).resize((W, H), Image.Resampling.NEAREST)


_Y, _X = np.mgrid[0:H, 0:W].astype(np.float32)
VMASK = (1 - 0.75 * np.clip((((_X - W / 2) / (W / 2)) ** 2 + ((_Y - H / 2) / (H / 2)) ** 2) - 0.25, 0, 1))[..., None]


def frame(t, bg, dark, tail):
    if t >= ACTION:
        return tail
    dim = piece(t, DIM)
    base = bg * (1 - dim) + dark * dim
    z, cx, cy = piece(t, CZ), piece(t, CX), piece(t, CY)
    sh = sum(14 * math.exp(-(t - h) * 18) for h in HITS if t >= h)
    cx += sh * math.sin(t * 91); cy += sh * 0.6 * math.cos(t * 77)
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    img = img.transform((W, H), Image.Transform.AFFINE, (1 / z, 0, cx - 640 / z, 0, 1 / z, cy - 360 / z), Image.Resampling.NEAREST)
    gy = (GROUND - cy) * z + 360
    G = ((fighter_state(GK, t)[0], 0),)
    R = ((fighter_state(RK, t)[0], 0),)
    fx = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gl = Image.new('RGB', (W, H), (0, 0, 0))
    soft = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    effects(t, ImageDraw.Draw(fx), ImageDraw.Draw(gl), G, R, ImageDraw.Draw(soft))
    if soft.getbbox():                    # dust sits behind the fighters
        sm = np.asarray(soft.filter(ImageFilter.GaussianBlur(4)).resize((W // 8, H // 8), Image.Resampling.BOX)).astype(np.int16)
        noise = np.random.default_rng(int(t * 30)).integers(-12, 13, sm.shape[:2])[..., None]
        sm[..., :3] += noise                                  # grainy, pixel-chunky dust like the hand-drawn smoke
        sm[..., 3] = np.where(sm[..., 3] > 40, np.minimum(255, sm[..., 3] + 30), sm[..., 3] // 2)
        soft = Image.fromarray(sm.clip(0, 255).astype(np.uint8)).resize((W, H), Image.Resampling.NEAREST)
        img = Image.alpha_composite(img.convert('RGBA'), soft).convert('RGB')
    ghost = Image.new('RGBA', (W, H), (0, 0, 0, 0))   # smear trail on fast moves
    gd = ImageDraw.Draw(ghost)
    for keys, cl in [(GK, 'green'), (RK, 'red')]:
        if abs(fighter_state(keys, t)[0] - fighter_state(keys, t - 0.033)[0]) > 25:
            for dt in (0.045, 0.025):
                draw_fighter(gd, keys, t - dt, cl, z, gy)
    if ghost.getbbox():
        ga = np.asarray(pixelate(ghost, CPX)).copy(); ga[..., 3] = (ga[..., 3] * 0.35).astype(np.uint8)
        img = Image.alpha_composite(img.convert('RGBA'), Image.fromarray(ga)).convert('RGB')
    chars = Image.new('RGBA', (W, H), (0, 0, 0, 0))   # pixel-art stickmen: drawn smooth, then snapped to a coarse grid
    cdr = ImageDraw.Draw(chars)
    draw_fighter(cdr, GK, t, 'green', z, gy)
    draw_fighter(cdr, RK, t, 'red', z, gy)
    img = Image.alpha_composite(img.convert('RGBA'), pixelate(chars, CPX)).convert('RGB')
    fx = pixelate(fx, FPX, cut=60)
    gl = gl.resize((W // 8, H // 8), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(2.5)).resize((W, H), Image.Resampling.NEAREST)  # blocky glow
    img = Image.alpha_composite(img.convert('RGBA'), fx).convert('RGB')
    out = np.asarray(img).astype(np.float32) + np.asarray(gl).astype(np.float32) * 0.75
    v = piece(t, VIG)
    if v: out *= (1 - v) + v * VMASK
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
    beat = 60 / 161.5
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
    notes = [58.3, 58.3, 58.3, 58.3, 58.3, 58.3, 65.4, 69.3]       # Bb pedal stepping to C, C# (measured from reference)
    for j in range(int(n / SR / (beat / 2)) + 1):
        f = notes[j % 8]
        seg = sfx.T(beat / 2)
        saw = 2 * ((seg * f) % 1) - 1
        add(out, int(j * beat / 2 * SR), sfx.lp(saw, 12) * np.exp(-seg * 4) * .35)
    pad = sum(np.sin(2 * np.pi * f * t + np.sin(t * 3) * .5) for f in (233.1, 349.2, 261.6)) * .05
    return out + pad


def add(buf, i, s):
    j = min(len(buf), i + len(s))
    if i < len(buf): buf[i:j] += s[:j - i]


def audio(path):
    n = int(DUR * SR)
    mus = music(n)
    env = np.ones(n)
    a, c = int(ACTION * SR), int(0.15 * SR)                  # reference drops ~12 dB at the cut, then fades
    env[a:a + c] = np.linspace(1, 0.5, c)
    env[a + c:] = 0.5 * np.linspace(1, 0.3, n - a - c)
    mix = mus * env * 0.55
    ev = [(0.02, sfx.whoosh(0.3, 10)), (0.18, sfx.whoosh(0.25, 6)), (0.28, clang()), (0.28, sfx.boom(0.8) * .8),
          (0.56, crackle(0.4)), (0.58, sfx.whoosh(0.3, 8)), (0.8, sfx.boom(0.6) * .6), (1.32, sfx.whoosh(0.3, 12)),
          (1.4, sfx.whoosh(0.3, 12)), (1.7, sfx.whoosh(0.3, 10)), (1.98, clang(0.8) * 1.1), (2.14, crackle(0.5)),
          (2.16, sfx.whoosh(0.4, 6)), (2.4, clang(0.4) * .6), (2.62, sfx.boom(1.2) * 1.2), (2.8, crackle(0.65)),
          (2.9, sfx.whoosh(0.25, 8)), (3.1, sfx.whoosh(0.25, 8)), (3.3, sfx.whoosh(0.25, 8)), (3.44, sfx.whoosh(0.3, 10)),
          (3.6, crackle(0.4)), (3.68, sfx.boom(1.0)), (3.82, crackle(0.6)), (3.95, clang(0.5) * .7),
          (4.2, sfx.whoosh(0.25, 10)), (4.48, sfx.whoosh(0.3, 10)), (4.6, clang(0.6)), (4.8, zap()), (4.92, zap()),
          (4.98, sfx.boom(1.4) * .9), (4.98, clang(1.0) * .8)]
    for t0 in (0.30, 0.56, 1.49, 2.04, 2.25, 3.55, 3.72, 4.48):   # strongest hits measured in the reference
        snap = rng.standard_normal(int(SR * .04)) * np.exp(-sfx.T(.04) * 70)
        ev += [(t0, sfx.boom(0.7) * .9), (t0, clang(0.5) * .9), (t0, snap * 1.6)]
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
