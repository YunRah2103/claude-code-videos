"""Reference-matched pixel look for pixel6.py (see ../STYLE.md).

Everything is painted in RGB at the art resolution (270x480) and later upscaled 4x nearest-neighbour.
Backdrop: 6 parallax layers painted by code with noise-driven clumped shading and hand-painted colour
banding (no ordered dither). Figures: clean pixel lines (Bresenham + fixed square brush) redrawn every
frame from whole-pixel joint positions. Effects: crescent slashes with pixel-shaded edges, red/orange
bursts with single-pixel embers, dust; dark navy grade for flash cuts.
"""
import math
import numpy as np, cv2
from PIL import Image, ImageDraw

W, H = 270, 480
LW, LH = 1000, 760          # layer canvas (x centred on world x = 0; rows match the screen at the wide shot)


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.uint8)


def ramp(*hexes):
    return np.array([rgb(h) for h in hexes], np.uint8)


# ---------------------------------------------------------------- noise + painting helpers
def vnoise(h, w, cy, cx, rng):
    g = rng.random((h // cy + 3, w // cx + 3)).astype(np.float32)
    return cv2.resize(g, ((w // cx + 3) * cx, (h // cy + 3) * cy), interpolation=cv2.INTER_CUBIC)[:h, :w]


def fbm(h, w, rng, cells=((24, 24), (8, 8), (3, 3)), amps=(.55, .3, .15)):
    return sum(a * vnoise(h, w, cy, cx, rng) for (cy, cx), a in zip(cells, amps))


def tone(v, R):
    """Quantise a shading value in [0,1] onto a colour ramp (hand-painted banding, no dither)."""
    k = np.clip((v * len(R)).astype(int), 0, len(R) - 1)
    return R[k]


def put(L, m, cols):
    L[m, :3] = cols[m] if cols.ndim == 3 else cols
    L[m, 3] = 255


def ridge(w, base, spec, rng, peaks=0):
    x = np.arange(w); y = np.full(w, float(base))
    for a, per in spec:
        y += a * np.sin(2 * math.pi * x / per + rng.uniform(0, 6.3))
    for _ in range(peaks):                                   # pointed peaks like painted mountains
        c, hgt, wd = rng.uniform(0, w), rng.uniform(18, 40), rng.uniform(40, 90)
        y -= hgt * np.clip(1 - np.abs(x - c) / wd, 0, 1) ** 1.3
    return np.round(y).astype(int)


def clumps(L, circles, R, rng, outline=None, light=(-.6, -.8)):
    """Foliage: overlapping round clumps, each lit from the top-left, with a dark scribble edge."""
    h, w = L.shape[:2]
    n = vnoise(h, w, 5, 5, rng)
    for cx, cy, r in circles:
        x0, x1, y0, y1 = int(max(0, cx - r - 1)), int(min(w, cx + r + 2)), int(max(0, cy - r - 1)), int(min(h, cy + r + 2))
        if x1 <= x0 or y1 <= y0: continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = (xx - cx) / r, (yy - cy) / r
        d = np.hypot(dx, dy)
        m = d + (n[y0:y1, x0:x1] - .5) * .35 <= 1
        v = .55 - .45 * (dx * light[0] + dy * light[1]) / 1.0 * .6 - d * .25 + (n[y0:y1, x0:x1] - .5) * .3
        sub = L[y0:y1, x0:x1]
        sub[m, :3] = tone(np.clip(v, 0, .999), R)[m]; sub[m, 3] = 255
        if outline is not None:
            e = m & (d + (n[y0:y1, x0:x1] - .5) * .35 > .86) & (dy > -.2)
            sub[e, :3] = outline; sub[e, 3] = 255


# ---------------------------------------------------------------- world
SKY = ramp('#6c9fcb', '#7aaad2', '#89b5d8', '#99c0de', '#aacbe3', '#bcd7e9', '#cfe3ee')
CLOUD = ramp('#8b939b', '#9fa7ae', '#b5bbc0', '#cbcfd1', '#dfe1e0', '#f0f0ec')
FAR = ramp('#335d5d', '#3e6c69', '#4b7b75', '#598b82', '#699a8f', '#7caa9e')
MID = ramp('#26503a', '#2e5f40', '#386f46', '#43804c', '#509153', '#5fa25c')
TREE = ramp('#1d4628', '#245630', '#2d6837', '#387b3e', '#468f47', '#56a352')
TRUNK = ramp('#3e2c1f', '#4f3828', '#614632', '#73553c')
BUSH = ramp('#2c6232', '#357439', '#418841', '#4f9c49', '#60b053', '#74c25e')
MEADOW = ramp('#3f8634', '#4a953a', '#56a33f', '#64b146', '#74bd4e', '#87c858', '#a2d468', '#c4de86', '#dfe6a2')
PATH = ramp('#b9ad62', '#c9bd70', '#d7cc82', '#e3da96', '#ece4ac')
GRASS = ramp('#24582a', '#2e6a2f', '#397c36')
FLOWERS = ramp('#e2453c', '#ec8fbf', '#f2cf48', '#f4f1e6', '#b6a8e6')


def paint_world(seed=11, road=False):
    rng = np.random.default_rng(seed)
    layers = []
    # 1 sky + clouds (p .04): banded gradient, wobbly band edges; cumulus painted in grey-white clumps
    L = np.zeros((LH, LW, 4), np.uint8)
    yy = np.arange(LH)[:, None] + np.zeros((1, LW))
    wob = vnoise(LH, LW, 10, 40, rng) * 14
    v = 1 - np.clip((yy + wob) / 300, 0, 1)
    put(L, np.ones((LH, LW), bool), tone(1 - v, SKY))
    for cx, cy, sc in ((-300, 120, 1.1), (-120, 95, .9), (40, 140, 1.25), (220, 105, 1.0), (380, 135, .9)):
        cx += LW // 2
        env = np.zeros((LH, LW), np.float32)
        for _ in range(16):
            px, py, r = cx + rng.uniform(-70, 70) * sc, cy + rng.uniform(-35, 25) * sc, rng.uniform(16, 34) * sc
            x0, x1, y0, y1 = int(max(0, px - r)), int(min(LW, px + r)), int(max(0, py - r)), int(min(LH, py + r))
            sy, sx = np.mgrid[y0:y1, x0:x1]
            env[y0:y1, x0:x1] = np.maximum(env[y0:y1, x0:x1], 1 - np.hypot((sx - px) / r, (sy - py) / r))
        n = fbm(LH, LW, rng, ((18, 18), (8, 8), (4, 4)), (.6, .3, .1))
        m = (env > .02) & (env + (n - .5) * .45 > .12) & (yy < cy + 40 * sc)
        top = cy - 50 * sc
        sh = np.clip(1 - (yy - top) / (95 * sc), 0, 1) * .8 + (n - .5) * .4 + env * .2
        put(L, m, tone(np.clip(sh, 0, .999), CLOUD))
    layers.append((0.04, L))
    # 2 far mountains (p .15): pointed peaks, horizontal brush-streak shading
    L = np.zeros((LH, LW, 4), np.uint8)
    top = ridge(LW, 262, [(8, 230), (4, 70)], rng, peaks=7)
    n = fbm(LH, LW, rng, ((6, 30), (3, 10), (2, 4)), (.5, .3, .2))
    m = yy >= top[None, :]
    v = .85 - np.clip((yy - top[None, :]) / 70, 0, 1) * .55 + (n - .5) * .55
    put(L, m, tone(np.clip(v, 0, .999), FAR))
    layers.append((0.15, L))
    # 3 mid hills (p .3)
    L = np.zeros((LH, LW, 4), np.uint8)
    top = ridge(LW, 290, [(9, 260), (5, 90), (2, 23)], rng, peaks=3)
    n = fbm(LH, LW, rng, ((5, 26), (3, 9), (2, 3)), (.5, .3, .2))
    m = yy >= top[None, :]
    v = .9 - np.clip((yy - top[None, :]) / 60, 0, 1) * .6 + (n - .5) * .6
    put(L, m, tone(np.clip(v, 0, .999), MID))
    for tx in rng.choice(np.arange(20, LW - 20, 11), 34, replace=False):     # small trees along the hills
        ty = top[tx] + 2; r = rng.uniform(4, 8)
        clumps(L, [(tx + rng.uniform(-r, r), ty - rng.uniform(r * .4, r * 1.4), r * rng.uniform(.6, 1)) for _ in range(4)], MID, rng)
    layers.append((0.3, L))
    # 4 big tree + bushes (p .55)
    L = np.zeros((LH, LW, 4), np.uint8)
    for tx, hgt in ((LW // 2 + 60, 1.0), (LW // 2 - 330, .8), (LW // 2 + 380, .75)):
        if road and tx == LW // 2 + 60: tx += 120
        base = 330; th = int(150 * hgt)
        for k in range(-5, 6):                                   # trunk: vertical bark stripes, 4 tones
            col = TRUNK[[0, 0, 1, 2, 3, 3, 3, 2, 1, 1, 0][k + 5]]
            L[base - th:base, tx + k, :3] = col; L[base - th:base, tx + k, 3] = 255
        for k in (-1, 1):                                         # two big branches
            for j in range(26):
                x, y = tx + k * j, base - th + 40 - int(j * .7)
                L[y:y + 3, x:x + 2, :3] = TRUNK[1]; L[y:y + 3, x:x + 2, 3] = 255
        cc = [(tx + rng.uniform(-48, 48) * hgt, base - th + rng.uniform(-30, 50) * hgt, rng.uniform(10, 19) * hgt) for _ in range(30)]
        cc.sort(key=lambda c: c[1] - .3 * c[0])
        clumps(L, cc, TREE, rng, outline=rgb('#163a21'))
    for bx in range(0, LW, 70):                                   # hedge of bushes along the field edge
        cc = [(bx + rng.uniform(-30, 30), 322 + rng.uniform(-14, 6), rng.uniform(8, 16)) for _ in range(6)]
        clumps(L, cc, BUSH, rng, outline=rgb('#22512a'))
    layers.append((0.55, L))
    # 5 meadow + yellow path + flowers (p 1.0)
    L = np.zeros((LH, LW, 4), np.uint8)
    n = fbm(LH, LW, rng, ((4, 30), (2, 10), (1, 3)), (.45, .35, .2))
    m = yy >= 326
    v = .8 - np.clip((yy - 326) / 260, 0, 1) * .55 + (n - .5) * .6
    put(L, m, tone(np.clip(v, 0, .999), MEADOW))
    xs = np.arange(LW)
    pc = 384 + np.round(5 * np.sin(xs / 61) + 3 * np.sin(xs / 23 + 1)).astype(int)
    pw = (14 + 3 * np.sin(xs / 37)).astype(int)
    for x in xs:
        if road:
            y0, y1 = 372, 400
            L[y0:y1, x, :3] = (52, 50, 58); L[y0:y1, x, 3] = 255
            L[y0, x, :3] = (120, 116, 108); L[y1 - 1, x, :3] = (34, 32, 38)
            if (x // 12) % 2 == 0: L[385:387, x, :3] = (226, 214, 150)
        else:
            y0, y1 = pc[x] - pw[x] // 2, pc[x] + pw[x] // 2
            vv = .55 + (n[y0:y1, x] - .5) * 1.1 + np.linspace(.2, -.2, y1 - y0)
            L[y0:y1, x, :3] = tone(np.clip(vv, 0, .999), PATH); L[y0:y1, x, 3] = 255
    for _ in range(2600):                                         # tiny flower pixels (red, pink, yellow, white)
        x, y = int(rng.integers(0, LW)), int(rng.integers(334, LH))
        if not road and abs(y - pc[x]) < pw[x] // 2 + 1: continue
        if road and 370 <= y <= 401: continue
        c = FLOWERS[rng.choice(5, p=[.32, .25, .28, .1, .05])]
        L[y, x, :3] = c
        if rng.random() < .25 and y + 1 < LH: L[y + 1, x, :3] = GRASS[2]
    for _ in range(1400):                                         # short grass strokes
        x, y = int(rng.integers(0, LW)), int(rng.integers(332, LH))
        if not road and abs(y - pc[x]) < pw[x] // 2 + 2: continue
        if road and 368 <= y <= 402: continue
        hh = int(rng.integers(1, 3 if y < 400 else 5))
        L[y - hh:y, x, :3] = GRASS[int(rng.integers(0, 3))] if rng.random() < .6 else MEADOW[-1]
    layers.append((1.0, L))
    # 6 foreground grass blades (p 1.4)
    L = np.zeros((LH, LW, 4), np.uint8)
    for _ in range(420):
        x = int(rng.integers(0, LW)); hh = int(rng.integers(6, 22)); lean = rng.uniform(-.5, .5)
        col = GRASS[int(rng.integers(0, 3))]
        for k in range(hh):
            y, xx_ = 492 - k, int(round(x + lean * k * k / hh))
            if 0 <= xx_ < LW: L[y, xx_, :3] = col; L[y, xx_, 3] = 255
    layers.append((1.4, L))
    return layers


def grade_layers(layers, mul, add=(0, 0, 0), step=4):
    out = []
    for p, L in layers:
        G = L.copy()
        c = np.clip(L[..., :3].astype(np.float32) * np.array(mul) + np.array(add), 0, 255)
        G[..., :3] = (np.round(c / step) * step).clip(0, 255).astype(np.uint8)
        out.append((p, G))
    return out


def compose(layers, ox_px, oy_px):
    """Paste the layers with whole-pixel parallax offsets (no resampling)."""
    img = np.zeros((H, W, 3), np.uint8)
    for p, L in layers:
        x = W // 2 - LW // 2 - int(round(ox_px * p)); y = int(round(oy_px * p))
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + LW, W), min(y + LH, H)
        if x1 <= x0 or y1 <= y0: continue
        src = L[y0 - y:y1 - y, x0 - x:x1 - x]; m = src[..., 3] > 0
        img[y0:y1, x0:x1][m] = src[..., :3][m]
    return img


NAVY = np.array([14, 19, 28], np.float32)


def dark_grade(img):
    """Flash-cut grade: dark blue-black with the painting still faintly readable."""
    c = img.astype(np.float32) * np.array([.09, .11, .13]) + NAVY
    return (np.round(c / 3) * 3).clip(0, 255).astype(np.uint8)


VIG = None


def vignette(img):
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.hypot((xx - W / 2) / (W * .62), (yy - H / 2) / (H * .62))
        VIG = np.where(d > 1.12, .9, np.where(d > 1.0, .95, 1.0)).astype(np.float32)[..., None]
    return (img * VIG).astype(np.uint8)


# ---------------------------------------------------------------- pixel lines (no AA)
def brush(img, x, y, w, col, mask=None):
    o = -(w // 2)
    x0, y0 = x + o, y + o
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + w)
    if xb > xa and yb > ya:
        img[ya:yb, xa:xb] = col
        if mask is not None: mask[ya:yb, xa:xb] = True


def pline(img, p0, p1, w, col, mask=None):
    x0, y0 = int(round(p0[0])), int(round(p0[1])); x1, y1 = int(round(p1[0])), int(round(p1[1]))
    dx, dy = abs(x1 - x0), -abs(y1 - y0); sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1); err = dx + dy
    while True:
        brush(img, x0, y0, w, col, mask)
        if x0 == x1 and y0 == y1: break
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy


def pdisc(img, c, r, col, mask=None):
    cx, cy = int(round(c[0])), int(round(c[1]))
    rr = int(math.ceil(r))
    for dy in range(-rr, rr + 1):
        span = int(math.floor(math.sqrt(max(0, r * r - dy * dy)) + .5))
        y = cy + dy
        if 0 <= y < H:
            xa, xb = max(0, cx - span), min(W, cx + span + 1)
            if xb > xa:
                img[y, xa:xb] = col
                if mask is not None: mask[y, xa:xb] = True


def ppoly(img, pts, col, mask=None):
    lay = Image.new('L', (W, H), 0)
    ImageDraw.Draw(lay).polygon([(int(round(x)), int(round(y))) for x, y in pts], fill=1)
    m = np.array(lay, bool)
    img[m] = col
    if mask is not None: mask |= m
    return m


# ---------------------------------------------------------------- Verlet cloth chains (cape, scarf, hair)
class Chain:
    def __init__(s, n, seg, grav=2600.0, damp=.9, back=1.0):
        s.n, s.seg, s.g, s.damp, s.back = n, seg, grav, damp, back
        s.P = None

    def step(s, anchor, d, dt=1 / 60):
        a = np.array(anchor, float)
        if s.P is None:
            s.P = np.array([a + [-d * s.seg * i * .6, s.seg * i * .8] for i in range(s.n)]); s.Q = s.P.copy()
        V = (s.P - s.Q) * s.damp
        s.Q = s.P.copy()
        acc = np.array([-d * 90.0 * s.back, s.g])                  # gravity + a little drift behind
        s.P = s.P + V + acc * dt * dt
        s.P[0] = a; s.Q[0] = a
        for _ in range(8):
            for i in range(1, s.n):
                v = s.P[i] - s.P[i - 1]; L = max(np.linalg.norm(v), 1e-6)
                s.P[i] = s.P[i - 1] + v / L * s.seg
            s.P[:, 1] = np.minimum(s.P[:, 1], -2.0)                 # stays above the ground (y up is negative)
            fwd = d * (s.P[1:, 0] - a[0])                            # keep it behind the body
            s.P[1:, 0] -= d * np.clip(fwd + 10, 0, None) * .5
        return s.P.copy()


def draw_cloth(img, pts, w0, w1, cols, mask=None, folds=0):
    """Cloth strip along a chain: narrow at the anchor, wide at the tail, two tones + fold lines."""
    P = np.asarray(pts, float); n = len(P)
    t = np.gradient(P, axis=0); t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
    nn = np.stack([-t[:, 1], t[:, 0]], 1)
    wd = np.linspace(w0, w1, n)[:, None] / 2
    A, B = P + nn * wd, P - nn * wd
    ppoly(img, list(map(tuple, A)) + list(map(tuple, B[::-1])), cols[0], mask)
    ppoly(img, list(map(tuple, P)) + list(map(tuple, B[::-1])), cols[1], mask)       # shaded half
    for f in range(folds):
        u = (f + 1) / (folds + 1)
        F = P + nn * wd * (u * 2 - 1) * .8
        for i in range(1, n):
            if i > 1: pline(img, F[i - 1], F[i], 1, cols[2])


# ---------------------------------------------------------------- figures
INKC = rgb('#141218'); SKIN = rgb('#8a5a3c'); SKIN2 = rgb('#6b4330'); HAIR = rgb('#1c1412')
TEE = rgb('#f2efe8'); TEE2 = rgb('#c4c0c8'); SHORTS = rgb('#18181e'); SHOE = rgb('#eeeeea')
CAPE = (rgb('#b9473e'), rgb('#8f3430'), rgb('#5e1f22')); SCARF = (rgb('#e5b13c'), rgb('#b5852a'), rgb('#7a5a1c'))


def draw_figure(img, S, I, hero, cloth, mask=None, lim=2):
    """Thin pixel stick figure from whole-pixel joint positions S (Nx3 screen, z = depth)."""
    J = lambda n: S[I[n]][:2]
    zl = np.mean([S[I[n]][2] for n in ('lhumerus', 'lfemur')]); zr = np.mean([S[I[n]][2] for n in ('rhumerus', 'rfemur')])
    near = 'l' if zl < zr else 'r'; far = 'r' if near == 'l' else 'l'
    a, b = J('lowerneck'), J('head')
    u = (b - a) / max(np.linalg.norm(b - a), 1e-6)
    sc = np.linalg.norm(J('thorax') - J('root')) / 23.0             # 1.0 = torso 23 px
    hr = max(4.0, 9.5 * sc)            # big round head (~20 % of the figure, like the reference)
    hc = a + u * hr * 1.15
    limb = INKC if not hero else SKIN
    limb2 = INKC if not hero else SKIN2
    if not hero and cloth is not None:
        draw_cloth(img, cloth, max(2, 5 * sc), 30 * sc, CAPE, mask, folds=1)

    def leg(k, col):
        hip, kn, an, ft = J(k + 'hipjoint'), J(k + 'femur'), J(k + 'tibia'), J(k + 'foot')
        pline(img, hip, kn, lim, col, mask); pline(img, kn, an, lim, col, mask)
        toe = an + (ft - an) * 1.4
        pline(img, an, toe, lim, (SHOE if k == near else TEE2) if hero else col, mask)
        if hero: pline(img, an + [0, 1], toe + [0, 1], 1, INKC, mask)

    def arm(k, col):
        sh, el, hd = J(k + 'clavicle'), J(k + 'humerus'), J(k + 'hand')
        pline(img, sh, el, lim, col, mask); pline(img, el, hd, lim, col, mask)
        brush(img, int(round(hd[0])), int(round(hd[1])), lim + 1, col, mask)
    arm(far, limb2); leg(far, limb2)
    root, th = J('root'), J('thorax')
    if hero:
        if cloth is not None: draw_cloth(img, cloth, 2, max(3, 8 * sc), SCARF, mask, folds=0)
        sh_mid = (J('lclavicle') + J('rclavicle')) / 2
        tw = max(4, int(round(8 * sc)))
        pline(img, root + (th - root) * .25, sh_mid, tw, TEE, mask)                          # white tee block
        pline(img, root + (th - root) * .25 + [-1, 0], sh_mid + [-1, 0], 1, TEE2, mask)
        for k in 'lr':                                                                         # black shorts block
            pline(img, root, root + (J(k + 'femur') - root) * .55, max(3, int(round(5 * sc))), SHORTS, mask)
        pline(img, root, root + (th - root) * .3, tw, SHORTS, mask)
        pline(img, sh_mid, hc, lim, SKIN, mask)
    else:
        pline(img, root, th, lim + 1, INKC, mask); pline(img, th, hc, lim, INKC, mask)
    leg(near, limb); arm(near, limb)
    pdisc(img, hc, hr, SKIN if hero else INKC, mask)
    if hero:                                                          # dark hair over the top/back of the head
        d = 1 if S[I['head']][0] >= S[I['lowerneck']][0] - 50 else -1
        cx, cy = int(round(hc[0])), int(round(hc[1]))
        r = int(round(hr))
        for dy in range(-r, 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= hr * hr and (dy < -r * .25 or d * dx < -r * .3):
                    if 0 <= cy + dy < H and 0 <= cx + dx < W: img[cy + dy, cx + dx] = HAIR
        ex = cx + d * max(1, int(round(r * .45)))
        if 0 <= cy < H and 0 <= ex < W: img[cy, ex] = INKC
    return hc, hr


# ---------------------------------------------------------------- effects
WHITE = np.array([255, 255, 255], np.float32)
GLOW = np.array([220, 238, 255], np.float32)
FIRE = ramp('#fff6d8', '#ffd65a', '#ff9a2a', '#e8432e', '#9a1e22')
EMBER = ramp('#ff5a3a', '#ff9a2a', '#e8332a')


def blend(img, m, col, a):
    if not m.any(): return
    c = img[m].astype(np.float32) * (1 - a) + np.asarray(col, np.float32) * a
    img[m] = (np.round(c / 6) * 6).clip(0, 255).astype(np.uint8)


def crescent_cov(path, th, ss=4):
    """Coverage (0..1) of a crescent built on a path, rasterised at ss x and box-averaged (pixel shading)."""
    P = np.asarray(path, float)
    t = np.gradient(P, axis=0); t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
    nn = np.stack([-t[:, 1], t[:, 0]], 1)
    O = P + nn * th[:, None]
    x0, y0 = int(max(0, min(P[:, 0].min(), O[:, 0].min()) - 3)), int(max(0, min(P[:, 1].min(), O[:, 1].min()) - 3))
    x1, y1 = int(min(W, max(P[:, 0].max(), O[:, 0].max()) + 4)), int(min(H, max(P[:, 1].max(), O[:, 1].max()) + 4))
    if x1 <= x0 or y1 <= y0: return None
    lay = Image.new('L', ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    pts = [((x - x0) * ss, (y - y0) * ss) for x, y in list(P) + list(O[::-1])]
    ImageDraw.Draw(lay).polygon(pts, fill=255)
    a = np.array(lay, np.float32).reshape(y1 - y0, ss, x1 - x0, ss).mean((1, 3)) / 255
    full = np.zeros((H, W), np.float32); full[y0:y1, x0:x1] = a
    return full


def fx_slash(img, path, age, life, side, z=1.0, red=False):
    """Clean white crescent: sweeps in over 2 frames, holds, then thins and fades. Soft 1-2 px edge
    from pixel-shaded coverage levels, and a slight glow."""
    P = np.asarray(path, float)
    if len(P) < 3: return
    n = len(P)
    grow = min(1.0, (age + 1) / 3)
    P = P[:max(3, int(n * grow))]
    k = max(0.0, 1 - max(0, age - 3) / max(life - 3, 1))
    lo = int(len(P) * (1 - k) * .7)
    P = P[lo:]
    if len(P) < 3: return
    u = np.linspace(0, 1, len(P))
    th = (4.2 * z * k + .5) * np.sin(np.pi * np.clip(u * .9 + .08, 0, 1)) ** .8 * side
    cov = crescent_cov(P, th)
    if cov is None: return
    halo = cv2.dilate((cov > .05).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (cov < .05)
    blend(img, halo, GLOW, .16 * k)
    blend(img, (cov > .05) & (cov <= .4), WHITE, .45)
    blend(img, (cov > .4) & (cov <= .75), WHITE, .78)
    m = cov > .75; img[m] = (255, 255, 255)
    if red:                                                            # red trailing edge on the big hits
        inner = (cov > .05) & (cov <= .4) & (np.roll(cov, int(np.sign(side)), 0) > .75)
        img[inner] = (232, 64, 50)


def fx_burst(img, c, age, z, seed, fire=False, big=False):
    """Red/orange spark or fire burst with scattered single-pixel embers that fall."""
    rng = np.random.default_rng(seed)
    cx, cy = c
    life = 18 if fire else 12
    if age >= life: return
    if age < (6 if fire else 4):                                       # hot core blob, jagged, expanding
        r = (3 + age * (1.6 if fire else 1.5)) * z * (1.1 if big else 1)
        nn = 14
        for li, (f, col) in enumerate(((1.0, FIRE[3]), (.75, FIRE[2]), (.5, FIRE[1]), (.25, FIRE[0]))):
            if fire is False and li == 0: continue
            pts = []
            for j in range(nn):
                a = 2 * math.pi * j / nn
                rr = r * f * (1 + .35 * (rng.random() - .5) * 2)
                pts.append((cx + rr * math.cos(a) * (1.6 if fire else 1), cy + rr * math.sin(a) - (age * .8 if fire else 0)))
            ppoly(img, pts, col)
    if fire and 2 <= age < 12:                                         # flame licks rising
        for j in range(6):
            a = rng.uniform(0, 2 * math.pi); rr = (6 + age * 1.8) * z
            x, y = cx + rr * math.cos(a) * 1.4, cy + rr * math.sin(a) * .7 - age * 1.5
            s = max(1, int((4 - age / 4) * z))
            img[int(np.clip(y, 0, H - 1)):int(np.clip(y + s, 0, H)), int(np.clip(x, 0, W - 1)):int(np.clip(x + s, 0, W))] = FIRE[2 if j % 2 else 3]
    for j in range(22 if fire else 14):                                # embers: single pixels with gravity
        a = rng.uniform(0, 2 * math.pi); sp = rng.uniform(1.2, 3.2) * z
        x = cx + math.cos(a) * sp * age * 1.2; y = cy + math.sin(a) * sp * age * .9 + .06 * age * age
        if 0 <= x < W and 0 <= y < H and age < life - (j % 4):
            if j % 5 == 0:                                             # a few larger glowing embers
                g = np.zeros((H, W), bool); g[max(0, int(y) - 2):int(y) + 3, max(0, int(x) - 2):int(x) + 3] = True
                blend(img, g, EMBER[0], .3)
                img[int(y):int(y) + 2, int(x):int(x) + 2] = EMBER[0]
            else:
                img[int(y), int(x)] = EMBER[j % 3]


def fx_dust(img, c, age, z, d):
    if age >= 12: return
    for j, ox in enumerate((-5, 0, 5)):
        r = (1.5 + age * .35) * z
        x = c[0] + (ox * (1 + age * .12) + d * age * .3) * z; y = c[1] - (1 + age * .35) * z - (j == 1)
        cov = np.zeros((H, W), bool); pdisc(np.zeros((H, W, 3), np.uint8), (x, y), r, (0, 0, 0), cov)
        blend(img, cov, (222, 214, 182), .6 * (1 - age / 12))


def fx_streak(img, c, age, z, d, seed, big):
    """Long horizontal fire streak through the hit (big hits only)."""
    if age >= 10: return
    rng = np.random.default_rng(seed + 7)
    L = (70 if big else 45) * z * (0.6 + age * .12); hh = (6 if big else 4) * z * (1 - age / 12)
    x0 = c[0] - d * L * .45
    for li, (f, col) in enumerate(((1.0, FIRE[3]), (.7, FIRE[2]), (.4, FIRE[1]), (.15, FIRE[0]))):
        pts = []
        for j in range(20):
            t = j / 19; xx = x0 + d * L * t
            amp = hh * f * math.sin(math.pi * t) ** .6 * (1 + .3 * (rng.random() - .5))
            pts.append((xx, c[1] - amp))
        for j in range(19, -1, -1):
            t = j / 19; xx = x0 + d * L * t
            amp = hh * f * math.sin(math.pi * t) ** .6 * (1 + .3 * (rng.random() - .5))
            pts.append((xx, c[1] + amp))
        ppoly(img, pts, col)


# ---------------------------------------------------------------- transition art
def face(i, bg):
    """Hero close-up, pixel portrait: headlights wash in from the right; two light dots in each eye."""
    img = bg.copy()
    k = min(1.0, (i + 3) / 20)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot((xx - 300) / 1.0, (yy - 230) * 1.25)
    for rr, col, a in ((260, (255, 196, 110), .25), (190, (255, 214, 140), .35), (130, (255, 236, 186), .5)):
        blend(img, d < rr * (0.55 + 0.45 * k), col, a * k)
    r = 56; c = (112 - i * .25, 236)
    ppoly(img, [(c[0] - 80, 480), (c[0] - 52, c[1] + r * .95), (c[0] + 58, c[1] + r * .95), (c[0] + 92, 480)], TEE)
    ppoly(img, [(c[0] - 80, 480), (c[0] - 52, c[1] + r * .95), (c[0] - 20, c[1] + r * .95), (c[0] - 34, 480)], TEE2)
    pline(img, (c[0] - 2, c[1] + r * .6), (c[0] + 2, c[1] + r * 1.0), 26, SKIN2)
    pdisc(img, c, r + 1, INKC); pdisc(img, c, r, SKIN)
    ppoly(img, [(c[0] + r * .93, c[1] - r * .05), (c[0] + r * 1.12, c[1] + r * .22), (c[0] + r * .9, c[1] + r * .3)], SKIN)
    head = (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r
    for lo, col in ((.05, rgb('#a36c48')), (.45, rgb('#c08458')), (.8, rgb('#e0aa74'))):     # banded warm light
        img[head & ((xx - c[0]) / r > lo + (1 - k) * .6)] = col
    hair = head & (((xx - (c[0] - r * .6)) / r) ** 2 + ((yy - (c[1] - r * .6)) / (r * .62)) ** 2 <= 1)
    img[hair] = HAIR
    img[hair & ((xx - (c[0] - r * .6)) / r > .55) & (yy % 3 == 0)] = rgb('#3a2a22')
    pdisc(img, (c[0] - r * .22, c[1] + r * .16), r * .12, SKIN2)                              # ear
    shock = i >= 8
    for ex, ew in ((c[0] + r * .22, r * .16), (c[0] + r * .64, r * .11)):
        ey = c[1]; eh = ew * (1.0 if shock else .65)
        pline(img, (ex - ew, ey - eh - (5 if shock else 3)), (ex + ew, ey - eh - (7 if shock else 2)), 2, HAIR)
        ppoly(img, [(ex + ew * math.cos(a), ey + eh * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16)], INKC)
        ppoly(img, [(ex + (ew - 1) * math.cos(a), ey + (eh - 1) * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16)], TEE)
        pr = max(2.0, ew * .55)
        pdisc(img, (ex + ew * .25, ey), pr, INKC)
        for dx in (-.35, .45):                                          # headlight reflections (two lamps)
            px, py = int(round(ex + ew * .25 + dx * pr)), int(round(ey - pr * .35))
            img[py:py + (2 if k > .5 else 1), px:px + (2 if k > .5 else 1)] = (255, 255, 240)
    mx, my = c[0] + r * .52, c[1] + r * .52
    if shock: pdisc(img, (mx, my + 1), 3.2, INKC)
    else: pline(img, (mx - 5, my), (mx + 4, my - 1), 2, INKC)
    return img


CARC = ramp('#1e7f78', '#27a096', '#3dbcae', '#7fd8cc')


def draw_car(img, x0, p, cam_x, sc, gy):
    c, sn = math.cos(-p), math.sin(-p)

    def T(pts):
        out = []
        for x, y in pts:
            x = x - 120; x, y = x * c - y * sn, x * sn + y * c
            out.append((int(round((x0 + 120 + x) * sc)) - cam_x + W // 2, int(round(y * sc)) + gy))
        return out
    body = [(30, -95), (10, -150), (40, -215), (190, -240), (300, -365), (590, -370), (700, -245), (790, -230), (800, -150), (780, -95)]
    ppoly(img, T([(x, y + 6) for x, y in body]), INKC)
    ppoly(img, T(body), CARC[1])
    ppoly(img, T([(40, -215), (190, -240), (300, -365), (590, -370), (700, -245), (790, -230), (790, -205), (40, -190)]), CARC[2])
    ppoly(img, T([(318, -340), (440, -345), (440, -250), (250, -250)]), rgb('#9fc6d8'))
    ppoly(img, T([(460, -345), (575, -345), (650, -250), (460, -250)]), rgb('#9fc6d8'))
    ppoly(img, T([(330, -335), (380, -338), (330, -262), (290, -262)]), rgb('#d6eef4'))
    ppoly(img, T([(20, -125), (800, -125), (795, -95), (30, -95)]), CARC[0])
    pline(img, *T([(60, -200), (690, -228)]), 1, CARC[3])
    hl = T([(36, -180)])[0]; pdisc(img, hl, max(2, 22 * sc), (255, 250, 220))
    tl = T([(780, -200)])[0]; pdisc(img, tl, max(1.5, 14 * sc), (232, 51, 42))
    for wx in (160, 640):
        q = T([(wx, -70)])[0]
        pdisc(img, q, 70 * sc, INKC); pdisc(img, q, 30 * sc, rgb('#8a9098')); pdisc(img, q, 12 * sc, rgb('#4a4e56'))
    return T([(36, -180)])[0]
