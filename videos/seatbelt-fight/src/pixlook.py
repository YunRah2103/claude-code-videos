"""Pixel-stickman look for pixel6.py: palette, painted parallax world, stick figures, effects, face, car.

Everything draws palette indices into a 270x480 uint8 buffer (255 = transparent in layers).
Backdrop layers are painted at half resolution and doubled (chunky painterly clusters); figures and
effects are drawn at full 270x480 resolution. Big hits dim the backdrop through DIM (a palette remap).
"""
import math
import numpy as np, cv2
from PIL import Image, ImageDraw

W, H = 270, 480
S0, GY0 = 0.235, 420
LW, LH = 1600, 700
CLEAR = 255

PAL_HEX = ['#5aa6d8', '#93cbea', '#cfe6ee', '#f4f6f2', '#a9b8c4', '#6f8fa0', '#4d8a92', '#3a6f78',   # 0-7 sky, clouds, far hills
           '#24533e', '#2f7a3e', '#4f9e38', '#7fc23a', '#b9de5c', '#e2d88e', '#b4a060', '#6b4a2a',   # 8-15 greens, path, trunk
           '#121014', '#1c2626', '#27383a', '#38504a', '#56645e', '#f2efe8', '#8a5a3c', '#c08458',   # 16-23 ink, dim, tee, skin
           '#1a1210', '#9a1e2c', '#ffffff', '#ffe680', '#ffa030', '#e8332a', '#8a1420', '#2bb3a6']   # 24-31 hair, opp, fx, car
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in PAL_HEX], np.uint8)
INK, TEE, SKIN, LIT, HAIR, RED, RED2 = 16, 21, 22, 23, 24, 25, 30
WHITE, YEL, ORA, FIRE, CAR = 26, 27, 28, 29, 31
DIM = np.arange(256, dtype=np.uint8)
DIM[:16] = [20, 20, 20, 19, 19, 18, 18, 17, 17, 17, 18, 18, 19, 19, 18, 17]
DIM[17:21] = [16, 17, 17, 18]
B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def bayer(h, w, y0=0, x0=0):
    return B4[(np.arange(h)[:, None] + y0) % 4, (np.arange(w)[None, :] + x0) % 4]


BAY = bayer(H, W)


def vgrad(h, w, cols, y_a, y_b, y0=0):
    y = np.arange(h)[:, None] + y0
    t = np.clip((y - y_a) / max(y_b - y_a, 1), 0, 1) * (len(cols) - 1)
    i = np.minimum(np.floor(t).astype(int), len(cols) - 2); f = t - i
    c = np.array(cols)
    return (np.where(f * 16 > bayer(h, w, y0), c[i + 1], c[i]) * np.ones((1, w), int)).astype(np.uint8)


def noise(h, w, cell, rng):
    g = rng.random((h // cell + 3, w // cell + 3)).astype(np.float32)
    return cv2.resize(g, ((w // cell + 3) * cell, (h // cell + 3) * cell), interpolation=cv2.INTER_CUBIC)[:h, :w]


def paste(dst, L, x, y):
    h, w = L.shape; Hh, Ww = dst.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, Ww), min(y + h, Hh)
    if x1 <= x0 or y1 <= y0: return
    src = L[y0 - y:y1 - y, x0 - x:x1 - x]; m = src != CLEAR
    dst[y0:y1, x0:x1][m] = src[m]


def ridge(w, base, amps, rng):
    x = np.arange(w); y = np.full(w, float(base))
    for a, per in amps:
        y += a * np.sin(2 * math.pi * x / per + rng.uniform(0, 6.3))
    return np.round(y).astype(int)


class Layer:
    def __init__(s, p, img):
        s.p, s.img = p, img


def blobs(h, w, circles):
    yy, xx = np.mgrid[0:h, 0:w]
    m = np.zeros((h, w), bool)
    for cx, cy, r in circles:
        x0, x1, y0, y1 = max(0, int(cx - r)), min(w, int(cx + r) + 1), max(0, int(cy - r)), min(h, int(cy + r) + 1)
        if x1 > x0 and y1 > y0:
            m[y0:y1, x0:x1] |= (xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2 <= r * r
    return m


def shade(m, n, levels, top, span):
    """Colour a blob: lighter at the top-left, noise-broken into painterly clusters."""
    h, w = m.shape
    yy = np.arange(h)[:, None] + np.zeros((1, w))
    v = np.clip((yy - top) / max(span, 1), 0, 1) * 0.8 + (n - 0.5) * 0.7
    k = np.clip((v * len(levels)).astype(int), 0, len(levels) - 1)
    return np.array(levels, np.uint8)[k]


def paint_layers(road=False, seed=7):
    """Painted at half resolution, then doubled (chunky clusters)."""
    rng = np.random.default_rng(seed)
    h2, w2, sw = LH // 2, LW // 2, W // 2
    sky = vgrad(h2, sw, [0, 1, 2], 0, 160)
    for cx, cy, sc in ((40, 70, 1.0), (115, 52, .8), (95, 105, .7)):            # cumulus heaps
        cs = [(cx + rng.uniform(-28, 28) * sc, cy + rng.uniform(-6, 10) * sc, rng.uniform(7, 15) * sc) for _ in range(14)]
        m = blobs(h2, sw, cs)
        lv = shade(m, noise(h2, sw, 4, rng), [3, 3, 2, 4, 5], cy - 16 * sc, 34 * sc)
        sky[m] = lv[m]
    layers = [Layer(0.0, np.repeat(np.repeat(sky, 2, 0), 2, 1)[:LH])]

    def band(top, levels, cell, span):
        L = np.full((h2, w2), CLEAR, np.uint8)
        n = noise(h2, w2, cell, rng); yy = np.arange(h2)[:, None]
        m = yy >= top[None, :]
        lv = shade(m, n, levels, top.min(), span)
        L[m] = lv[m]
        return L
    far = band(ridge(w2, 143, [(9, 210), (4, 67), (2, 23)], rng), [5, 6, 6, 7], 5, 30)
    mid = band(ridge(w2, 158, [(5, 150), (2, 45)], rng), [11, 10, 9, 9, 8], 4, 30)
    for tx in rng.choice(np.arange(20, w2 - 20, 9), 40, replace=False):          # small round trees on the hills
        ty = 156 - int(rng.integers(0, 8)); r = rng.uniform(3, 6)
        cs = [(tx + rng.uniform(-r, r), ty - rng.uniform(0, r), r * rng.uniform(.6, 1)) for _ in range(4)]
        m = blobs(h2, w2, cs); lv = shade(m, noise(h2, w2, 2, rng), [11, 10, 9, 8], ty - 2 * r, 3 * r)
        mid[m] = lv[m]
    near = np.full((h2, w2), CLEAR, np.uint8)
    for tx in (90, 330, 560, 760):                                              # big painterly trees
        if road and tx in (330,): continue
        near[100:178, tx - 3:tx + 4] = 15; near[100:178, tx + 2:tx + 4] = 8
        cs = [(tx + rng.uniform(-30, 30), 70 + rng.uniform(-28, 30), rng.uniform(9, 18)) for _ in range(22)]
        m = blobs(h2, w2, cs); lv = shade(m, noise(h2, w2, 3, rng), [12, 11, 10, 9, 9, 8], 40, 80)
        near[m] = lv[m]
    bush = band(ridge(w2, 172, [(3, 40), (2, 13), (1, 5)], rng), [12, 11, 10, 9], 3, 10)
    bush[180:] = CLEAR
    near[bush != CLEAR] = bush[bush != CLEAR]
    g = np.full((h2, w2), CLEAR, np.uint8)
    n = noise(h2 - 174, w2, 12, rng)
    gl = shade(np.ones_like(n, bool), n, [12, 11, 10, 9], 0, 160)
    g[174:] = gl
    yy = np.arange(174, h2)[:, None]
    if road:
        g[196:226] = np.where(bayer(30, w2) < 5, 17, 18); g[195] = 13; g[226] = 16
        for x in range(0, w2, 20): g[210:212, x:x + 10] = 13
    else:
        top = 199 + np.round(2 * np.sin(np.arange(w2) / 19)).astype(int)
        bot = 223 + np.round(2 * np.sin(np.arange(w2) / 27 + 1)).astype(int)
        pn = noise(h2, w2, 6, rng)
        for x in range(w2):
            col = np.where(pn[top[x]:bot[x], x] > .62, 14, 13)
            g[top[x]:bot[x], x] = col
    for _ in range(220):                                                        # flowers and grass flecks
        x, y = int(rng.integers(0, w2)), int(rng.integers(176, h2))
        if g[y, x] in (13, 14, 16, 17, 18): continue
        g[y, x] = int(rng.choice([WHITE, YEL, FIRE, 12, 12, 12, 8]))
    fg = np.full((LH, LW), CLEAR, np.uint8)
    for _ in range(300):                                                        # foreground grass (full res)
        x = int(rng.integers(0, LW)); hgt = int(rng.integers(8, 24)); lean = rng.uniform(-.6, .6)
        for k in range(hgt):
            yy_, xx_ = 512 - k, int(round(x + lean * k * k / hgt))
            if 0 <= xx_ < LW: fg[yy_, xx_] = 8 if k < hgt - 4 else 9
    up = lambda a: np.repeat(np.repeat(a, 2, 0), 2, 1)
    layers += [Layer(0.1, up(far)), Layer(0.25, up(mid)), Layer(0.5, up(near)), Layer(1.0, up(g)), Layer(1.4, fg)]
    return layers


def draw_world(img, layers, cx, gy, push=0.0):
    for L in layers:
        if L.p == 0:
            img[:] = L.img[:H]; continue
        ox = int(round(cx * S0 * L.p)); oy = int(round((gy - GY0) * L.p + push * 9 * L.p))
        paste(img, L.img, W // 2 - LW // 2 - ox, oy)


def dim(img, k):
    """Dim the backdrop by k in [0,1] with an ordered-dither ramp (pixel fade, no blending)."""
    if k <= 0: return img
    m = BAY < k * 16
    img[m] = DIM[img[m]]
    return img


# ---------------------------------------------------------------- stick figures
def cap(dr, p0, p1, r0, r1, col):
    p0, p1 = np.asarray(p0[:2], float), np.asarray(p1[:2], float)
    d = p1 - p0; n = np.linalg.norm(d)
    if n > .5:
        nn = np.array([-d[1], d[0]]) / n
        dr.polygon([tuple(p0 + nn * r0), tuple(p1 + nn * r1), tuple(p1 - nn * r1), tuple(p0 - nn * r0)], fill=col)
    dr.ellipse([p0[0] - r0, p0[1] - r0, p0[0] + r0, p0[1] + r0], fill=col)
    dr.ellipse([p1[0] - r1, p1[1] - r1, p1[0] + r1, p1[1] + r1], fill=col)


def disc(dr, c, r, col):
    dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=col)


R_HEAD = 76


def draw_stick(img, S, s, I, hero, mask=None):
    """Thin solid stickman: big round head, tapered limbs. Hero: black with a white tee and white shoes.
    Opponent: dark red with a 1-px ink outline. Far-side limbs a shade darker so crossings read."""
    lay = Image.new('L', (W, H), CLEAR); dr = ImageDraw.Draw(lay)
    J = lambda n: S[I[n]]
    zl = np.mean([J(n)[2] for n in ('lhumerus', 'lfemur')]); zr = np.mean([J(n)[2] for n in ('rhumerus', 'rfemur')])
    near = 'l' if zl < zr else 'r'
    R = lambda r: max(1.0, r * s)
    base = INK if hero else RED
    far = 18 if hero else RED2
    a, b = J('lowerneck'), J('head')
    u = (b[:2] - a[:2]) / max(np.linalg.norm(b[:2] - a[:2]), 1e-6)
    hc = a[:2] + u * R_HEAD * 0.95
    order = sorted([(np.mean([J(k + n)[2] for n in ('femur', 'tibia')]), 'leg', k) for k in 'lr'] +
                   [(np.mean([J(k + n)[2] for n in ('humerus', 'hand')]), 'arm', k) for k in 'lr'] +
                   [((J('root')[2] + J('thorax')[2]) / 2, 'torso', '')], key=lambda p: -p[0])
    for _, kind, k in order:
        col = base if k in (near, '') else far
        if kind == 'leg':
            hip, kn, an, ball = (J(k + n) for n in ('hipjoint', 'femur', 'tibia', 'foot'))
            cap(dr, hip, kn, R(19), R(16), col); cap(dr, kn, an, R(16), R(12), col)
            tip = ball + (ball - an) * 0.5
            cap(dr, an, tip, R(13), R(10), (TEE if k == near else 19) if hero else col)
        elif kind == 'arm':
            sh, el, wr, hd = (J(k + n) for n in ('clavicle', 'humerus', 'radius', 'hand'))
            cap(dr, sh, el, R(16), R(14), col); cap(dr, el, hd, R(14), R(12), col); disc(dr, hd, R(18), col)
        else:
            root, th = J('root'), J('thorax')
            if hero:
                cap(dr, root, th, R(30), R(34), INK); cap(dr, root + (th - root) * .2, th, R(25), R(29), TEE)
            else:
                cap(dr, root, th, R(24), R(27), col)
            cap(dr, th, hc, R(13), R(13), base)
            disc(dr, hc, R(R_HEAD), base)
    arr = np.array(lay); m = arr != CLEAR
    if not hero:                                                     # 1-px ink outline
        o = np.zeros_like(m)
        o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
        img[o & ~m] = INK
    img[m] = arr[m]
    if mask is not None: mask |= m
    return hc


def shadow(img, xs, gy, s):
    cx = (min(xs) + max(xs)) / 2; w = (max(xs) - min(xs)) / 2 + 60 * s
    x0, x1 = int(max(0, cx - w - 1)), int(min(W, cx + w + 2)); y0, y1 = int(max(0, gy - 6)), int(min(H, gy + 6))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = ((xx - cx) / max(w, 1)) ** 2 + ((yy - gy - 1) / max(2.5, 10 * s)) ** 2 <= 1
    sub = img[y0:y1, x0:x1]; mm = m & (BAY[y0:y1, x0:x1] < 10)
    sub[mm] = 8


# ---------------------------------------------------------------- effects (pixel art, on 2s)
def jag_poly(c, rx, ry, ang, rng, n=18, amt=.3):
    ca, sa = math.cos(ang), math.sin(ang); pts = []
    for j in range(n):
        a = 2 * math.pi * j / n
        k = 1 + amt * (rng.random() - .5) * 2
        x, y = rx * k * math.cos(a), ry * k * math.sin(a)
        pts.append((c[0] + x * ca - y * sa, c[1] + x * sa + y * ca))
    return pts


def bits(dr, c, rng, n, r0, r1, col, sz, fall=0.0, ang=None):
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi) if ang is None else ang + rng.uniform(-1.0, 1.0)
        r = rng.uniform(r0, r1); x, y = c[0] + r * math.cos(a), c[1] + r * math.sin(a) + fall
        q = max(1, int(round(sz * rng.uniform(.6, 1.2))))
        dr.rectangle([x, y, x + q - 1, y + q - 1], fill=col)


def fx_crescent(dr, pts, e, z, out_dir):
    """Big crescent slash along the striking limb's path: thick white blade, red trailing edge."""
    P = np.array(pts, float)
    if len(P) < 3: return
    n = len(P); lo = [0, n // 4, n // 2][e]; P = P[lo:]
    if len(P) < 3: return
    T = [12, 8, 4][e] * z
    tang = np.gradient(P, axis=0); tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-6)
    nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
    nrm *= np.sign((nrm * out_dir).sum(1, keepdims=True) + 1e-6)
    u = np.linspace(0, 1, len(P)); th = T * np.sin(np.pi * np.clip(u * .85 + .1, 0, 1)) ** .7
    if e == 0:
        red = P + nrm * (th[:, None] + 2)
        dr.polygon([tuple(p) for p in P] + [tuple(p) for p in red[::-1]], fill=FIRE)
    outer = P + nrm * th[:, None]
    dr.polygon([tuple(p) for p in P] + [tuple(p) for p in outer[::-1]], fill=WHITE if e < 2 else 3)


def fx_streak(dr, c, e, z, d, seed, big):
    """Fire streak along the strike direction with a dithered pixel glow and red bits."""
    rng = np.random.default_rng(seed + 100 * e)
    L = (95 if big else 60) * z; hgt = (13 if big else 9) * z; ang = 0 if d > 0 else math.pi
    back = (c[0] - d * L * .35, c[1])
    if e == 0:
        dr.polygon(jag_poly(back, L * .8, hgt * 1.3, ang, rng), fill=FIRE)
        dr.polygon(jag_poly(back, L * .65, hgt * .9, ang, rng), fill=ORA)
        dr.polygon(jag_poly(back, L * .45, hgt * .5, ang, rng, 12), fill=YEL)
        dr.polygon(jag_poly(c, 14 * z, 14 * z, 0, rng, 14, .45), fill=ORA)
        dr.polygon(jag_poly(c, 8 * z, 8 * z, 0, rng, 10, .3), fill=WHITE)
        bits(dr, c, rng, 10, 12 * z, 26 * z, FIRE, 2 * z)
    elif e == 1:
        fwd = (c[0] + d * L * .25, c[1] - 2 * z)
        dr.polygon(jag_poly(fwd, L * 1.0, hgt * 1.1, ang, rng, 22, .45), fill=FIRE)
        dr.polygon(jag_poly(fwd, L * .8, hgt * .6, ang, rng, 18), fill=ORA)
        dr.polygon(jag_poly(fwd, L * .55, hgt * .25, ang, rng, 12), fill=WHITE if big else YEL)
        bits(dr, c, rng, 16, 18 * z, 40 * z, FIRE, 2 * z, 0, None)
    elif e == 2:
        for j in range(6):
            p = (c[0] + d * rng.uniform(-.2, 1.1) * L, c[1] + rng.uniform(-1.5, 1.5) * hgt - 4 * z)
            dr.polygon(jag_poly(p, rng.uniform(6, 14) * z, rng.uniform(2, 5) * z, ang, rng, 10, .4), fill=int(rng.choice([FIRE, ORA])))
        bits(dr, c, rng, 14, 26 * z, 52 * z, RED2, 2 * z, 6 * z)
    else:
        bits(dr, c, rng, 10, 30 * z, 60 * z, int(rng.choice([FIRE, RED2])), 1.5 * z, 14 * z)


def glow(img, c, r, k):
    """Dithered pixel glow (ordered dither of the glow colour, no alpha)."""
    x0, x1, y0, y1 = int(max(0, c[0] - r)), int(min(W, c[0] + r)), int(max(0, c[1] - r)), int(min(H, c[1] + r))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    v = np.clip(1 - np.hypot(xx - c[0], (yy - c[1]) * 1.6) / r, 0, 1) * 16 * k
    sub = img[y0:y1, x0:x1]; m = v > BAY[y0:y1, x0:x1] + 1
    sub[m & (sub != INK) & (sub != RED) & (sub != TEE)] = YEL


def fx_spark(dr, c, e, z, d, seed):
    rng = np.random.default_rng(seed + 10 * e)
    if e == 0:
        for a, L in ((0, 16), (math.pi / 2, 12), (math.pi, 16), (-math.pi / 2, 12)):
            ca, sa = math.cos(a), math.sin(a)
            dr.polygon([(c[0] + L * z * ca, c[1] + L * z * sa), (c[0] - 3 * z * sa, c[1] + 3 * z * ca),
                        (c[0] - L * .3 * z * ca, c[1] - L * .3 * z * sa), (c[0] + 3 * z * sa, c[1] - 3 * z * ca)], fill=WHITE)
        bits(dr, c, rng, 8, 8 * z, 18 * z, FIRE, 2 * z, 0, 0 if d > 0 else math.pi)
    elif e == 1:
        dr.polygon(jag_poly(c, 7 * z, 7 * z, 0, rng, 10, .5), fill=YEL)
        bits(dr, c, rng, 10, 14 * z, 26 * z, FIRE, 2 * z, 2 * z, 0 if d > 0 else math.pi)
    elif e == 2:
        bits(dr, c, rng, 8, 22 * z, 34 * z, RED2, 2 * z, 6 * z, 0 if d > 0 else math.pi)
    else:
        bits(dr, c, rng, 4, 28 * z, 40 * z, RED2, 1, 12 * z, 0 if d > 0 else math.pi)


def fx_dust(dr, c, e, z, d):
    for j, (ox, r) in enumerate(((-8, 3), (0, 4), (8, 3))):
        x = c[0] + (ox + d * 2) * z * (1 + .7 * e); y = c[1] - (2 + 3 * e) * z - (j == 1) * 2 * z
        rr = (r + 1.5 * e) * z
        dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=3 if e == 0 else (2 if e == 1 else 4))


# ---------------------------------------------------------------- transition art
def face(i):
    """Close-up: the hero's face turns into the oncoming headlights; two light dots in each eye."""
    img = np.where(BAY < 8, 17, 16).astype(np.uint8)
    k = min(1.0, (i + 2) / 10)
    yy, xx = np.mgrid[0:H, 0:W]
    g = np.clip(1 - np.hypot(xx - 300, (yy - 240) * 1.3) / (130 + 140 * k), 0, 1) * 16 * (0.5 + 0.5 * k)
    img[g > BAY + .5] = ORA; img[g > BAY + 5] = YEL; img[g > BAY + 11] = WHITE
    pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
    r = 70 + 1.0 * i; c = np.array([116.0 - 0.5 * i, 232.0])
    dr.polygon([(c[0] - 96, 480), (c[0] - 62, c[1] + r * .93), (c[0] + 70, c[1] + r * .93), (c[0] + 106, 480)], fill=INK)
    dr.polygon([(c[0] - 94, 480), (c[0] - 60, c[1] + r * .98), (c[0] + 68, c[1] + r * .98), (c[0] + 104, 480)], fill=TEE)
    cap(dr, (c[0] - 4, c[1] + r * .5), (c[0] + 2, c[1] + r * 1.05), r * .42, r * .42, 15)
    disc(dr, c, r + 1, INK); disc(dr, c, r, SKIN)
    dr.polygon([(c[0] + r * .93, c[1] - r * .05), (c[0] + r * 1.12, c[1] + r * .2), (c[0] + r * .92, c[1] + r * .3)], fill=SKIN)
    img = np.array(pil)
    head = (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r
    lit = np.clip((xx - (c[0] - r * .1)) / (r * 1.1), 0, 1) * 16 * k
    img[head & (lit > BAY)] = LIT                                # warm headlight wash
    hair = head & ((xx - (c[0] - r * .62)) ** 2 / r ** 2 + (yy - (c[1] - r * .62)) ** 2 / (r * .62) ** 2 <= 1)
    img[hair] = HAIR
    img[head & ((xx - c[0]) ** 2 + (yy - c[1]) ** 2 > (r - 2) ** 2) & (xx > c[0] + r * .2) & ~hair] = YEL   # rim light
    pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
    dr.ellipse([c[0] - r * .3, c[1] + r * .02, c[0] - r * .1, c[1] + r * .32], fill=15)
    shock = i >= 5
    for ex, ew in ((c[0] + r * .2, r * .17), (c[0] + r * .62, r * .12)):
        ey = c[1]; eh = ew * (1.0 if shock else .7)
        dr.line([(ex - ew, ey - eh - (5 if shock else 3)), (ex + ew, ey - eh - (7 if shock else 2))], fill=HAIR, width=3)
        dr.ellipse([ex - ew, ey - eh, ex + ew, ey + eh], fill=INK)
        dr.ellipse([ex - ew + 1, ey - eh + 1, ex + ew - 1, ey + eh - 1], fill=TEE)
        pr = ew * .55
        dr.ellipse([ex + ew * .25 - pr, ey - pr, ex + ew * .25 + pr, ey + pr], fill=INK)
        for dx in (-0.3, 0.45):                                  # headlight reflections (two lamps)
            px, py = ex + ew * .25 + dx * pr, ey - pr * .35
            dr.rectangle([px - 1, py - 1, px + (1 if k > .6 else 0), py + (1 if k > .6 else 0)], fill=WHITE)
        dr.point([(ex + ew * .25, ey + pr * .3)], fill=YEL)
    mx, my = c[0] + r * .52, c[1] + r * .52
    if shock: dr.ellipse([mx - 4, my - 3, mx + 4, my + 5], fill=INK)
    else: dr.line([(mx - 6, my), (mx + 5, my - 1)], fill=INK, width=2)
    return np.array(pil)


def draw_car(img, x0, p, cam):
    cx, gy, sc = cam
    pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
    c, sn = math.cos(-p), math.sin(-p)

    def T(pts):
        out = []
        for x, y in pts:
            x = x - 120; x, y = x * c - y * sn, x * sn + y * c
            out.append(((x0 + 120 + x - cx) * sc + W / 2, y * sc + gy))
        return out
    body = [(30, -95), (10, -150), (40, -215), (190, -240), (300, -365), (590, -370), (700, -245), (790, -230), (800, -150), (780, -95)]
    dr.polygon(T(body), fill=CAR, outline=INK)
    dr.polygon(T([(318, -340), (440, -345), (440, -250), (250, -250)]), fill=2, outline=INK)
    dr.polygon(T([(460, -345), (575, -345), (650, -250), (460, -250)]), fill=2, outline=INK)
    dr.polygon(T([(20, -125), (800, -125), (795, -95), (30, -95)]), fill=7)
    dr.line(T([(60, -205), (690, -235)]), fill=WHITE, width=1)
    hl = T([(36, -180)])[0]; r = 22 * sc
    dr.ellipse([hl[0] - r, hl[1] - r, hl[0] + r, hl[1] + r], fill=WHITE, outline=YEL)
    tl = T([(776, -205), (798, -175)])
    dr.rectangle([min(tl[0][0], tl[1][0]), tl[0][1], max(tl[0][0], tl[1][0]), tl[1][1]], fill=FIRE)
    for wx in (x0 + 160, x0 + 640):
        q = ((wx - cx) * sc + W / 2, -70 * sc + gy)
        disc(dr, q, 70 * sc, INK); disc(dr, q, 32 * sc, 5)
    img[:] = np.array(pil)
