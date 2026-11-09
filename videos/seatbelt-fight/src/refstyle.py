"""Reference-matched painted pixel look for pixel6.py (see ../STYLE.md).

Everything is painted in RGB at the art resolution (set_res; default 180x320, upscaled 6x nearest) and
pasted at whole-pixel offsets. Backdrop: 6 parallax layers painted by code with noise-driven clumps on
colour ramps (hand banding, no ordered dither), in three detail scales (wide / medium / close) and a dusk
variant. Figures: thin pixel lines (Bresenham + square brush) redrawn every frame. Effects: soft streaky
fire and sparks with glowing embers, clean crescent slashes, dust, navy dark cuts.
"""
import math
import numpy as np, cv2
from PIL import Image, ImageDraw

W, H = 180, 320


def set_res(w, h):
    global W, H, VIG, NOISE
    W, H, VIG, NOISE = w, h, None, None


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.uint8)


def ramp(*hexes):
    return np.array([rgb(h) for h in hexes], np.uint8)


# ---------------------------------------------------------------- noise + painting helpers
def vnoise(h, w, cy, cx, rng):
    cy, cx = max(1, int(cy)), max(1, int(cx))
    g = rng.random((h // cy + 3, w // cx + 3)).astype(np.float32)
    return cv2.resize(g, ((w // cx + 3) * cx, (h // cy + 3) * cy), interpolation=cv2.INTER_CUBIC)[:h, :w]


def fbm(h, w, rng, cells, amps):
    return sum(a * vnoise(h, w, cy, cx, rng) for (cy, cx), a in zip(cells, amps))


def tone(v, R):
    k = np.clip((np.asarray(v) * len(R)).astype(int), 0, len(R) - 1)
    return R[k]


def put(L, m, cols):
    L[m, :3] = cols[m] if np.ndim(cols) == 3 else cols
    L[m, 3] = 255


def ridge(w, base, spec, rng, peaks=0, ph=(18, 40), pw=(40, 90)):
    x = np.arange(w); y = np.full(w, float(base))
    for a, per in spec:
        y += a * np.sin(2 * math.pi * x / per + rng.uniform(0, 6.3))
    for _ in range(peaks):
        c, hgt, wd = rng.uniform(0, w), rng.uniform(*ph), rng.uniform(*pw)
        y -= hgt * np.clip(1 - np.abs(x - c) / wd, 0, 1) ** 1.3
    return np.round(y).astype(int)


def puffs(L, circles, R, rng, edge=None, light=(-.6, -.8), cell=4, rough=.35, dark_edge=0, namp=.45):
    """Clumped round puffs (foliage or cloud billows): lit from the top-left, noisy edges, optional dark
    scribble edge (foliage) or a darker-tone rim (cloud billows)."""
    h, w = L.shape[:2]
    n = vnoise(h, w, cell, cell, rng)
    for cx, cy, r in circles:
        x0, x1, y0, y1 = int(max(0, cx - r - 2)), int(min(w, cx + r + 3)), int(max(0, cy - r - 2)), int(min(h, cy + r + 3))
        if x1 <= x0 or y1 <= y0 or r < 1: continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = (xx - cx) / r, (yy - cy) / r
        d = np.hypot(dx, dy); nn = n[y0:y1, x0:x1] - .5
        m = d + nn * rough <= 1
        v = .58 - .32 * (dx * light[0] + dy * light[1]) - d * .22 + nn * namp
        k = np.clip((np.clip(v, 0, .999) * len(R)).astype(int) - dark_edge * (d + nn * rough > .8), 0, len(R) - 1)
        sub = L[y0:y1, x0:x1]
        sub[m, :3] = R[k][m]; sub[m, 3] = 255
        if edge is not None:
            e = m & (d + nn * rough > .84) & (dy > -.25)
            sub[e, :3] = edge; sub[e, 3] = 255


# ---------------------------------------------------------------- palettes (muted, many tones)
PALS = {
    'day': dict(
        sky=ramp('#7ea4c6', '#89adcc', '#95b6d1', '#a1bfd6', '#aec8da', '#bbd1df', '#c9d9e3', '#d6e1e7'),
        cloud=ramp('#78828d', '#8b949d', '#9ea6ad', '#b1b7bc', '#c4c8cb', '#d6d8d8', '#e6e6e2', '#f2f1ec'),
        far=ramp('#4a6a73', '#55777d', '#618487', '#6e9191', '#7c9e9c', '#8caba7', '#9db8b2'),
        hill=ramp('#203a32', '#27463a', '#2f5241', '#385e48', '#426b4f', '#4d7856', '#5a845e'),
        gy=ramp('#2e4729', '#3a5630', '#476637', '#55763e', '#648545', '#74944e', '#87a259', '#9daf68', '#b2bc79'),
        gb=ramp('#233d36', '#2d4b3f', '#385a48', '#446952', '#51785c', '#5f8766', '#6f9572', '#82a27e'),
        trunk=ramp('#33261c', '#433224', '#54402d', '#665036', '#78603f'),
        path=ramp('#8f845a', '#a19564', '#b2a66f', '#c1b47b', '#cec189', '#d9cd98'),
        rut=ramp('#6f6646', '#807652'),
        flowers=ramp('#d94a3f', '#e48fb6', '#e9c955', '#efece2', '#b3a6dd'),
        edge=rgb('#17301f'), road=False),
    'dusk': dict(
        sky=ramp('#26294a', '#30305a', '#3d3866', '#4c406f', '#5e4874', '#735076', '#8b5a74', '#a46670', '#bc776c', '#cf8c6c'),
        cloud=ramp('#2e2c47', '#3c3854', '#4c4460', '#5e506a', '#735c70', '#8c6873', '#a77773', '#c18874'),
        far=ramp('#2b2f48', '#323752', '#3a3f5b', '#434863', '#4d516b', '#585a72'),
        hill=ramp('#171e26', '#1c252c', '#212c32', '#273438', '#2d3c3e', '#344444'),
        gy=ramp('#1e2a26', '#24322b', '#2b3b30', '#334435', '#3c4d3a', '#46573f', '#516046', '#5d6a4e'),
        gb=ramp('#18222a', '#1e2a30', '#243237', '#2b3a3e', '#334345', '#3c4b4c'),
        trunk=ramp('#1c1716', '#25201d', '#2f2924', '#3a332c'),
        path=ramp('#2f2d37', '#36343e', '#3e3c46', '#47454e', '#504e56'),
        rut=ramp('#24222b', '#2a2831'),
        flowers=ramp('#8e3a3e', '#94667c', '#9c8a52', '#a3a19c', '#6f6a8e'),
        edge=rgb('#0e1418'), road=True)}


def paint_world(seed=11, kind='day', zoom=1.0):
    """6 parallax layers for the art resolution. zoom scales feature sizes (wide 1.0, medium ~1.6,
    close ~2.4) so closer shots get bigger, chunkier painting instead of a scaled bitmap."""
    P = PALS[kind]; rng = np.random.default_rng(seed + int(zoom * 10))
    u = H / 320.0
    LW, LH = int(W * 4.4), int(H * 1.7)
    Z = zoom * u
    hor = int(H * (0.50 + 0.08 * (zoom - 1)))
    hil = int(H * (0.58 + 0.06 * (zoom - 1)))
    mead = int(H * (0.66 + 0.05 * (zoom - 1)))
    yy = np.arange(LH)[:, None] + np.zeros((1, LW))
    layers = []
    # 1 sky with tall billowing clouds (p .03)
    L = np.zeros((LH, LW, 4), np.uint8)
    wob = vnoise(LH, LW, 6 * Z, 26 * Z, rng) * 10 * u
    put(L, np.ones((LH, LW), bool), tone(np.clip((yy + wob) / (hor * 1.05), 0, .999), P['sky']))
    for cx in np.linspace(LW * .06, LW * .94, 7) + rng.uniform(-20, 20, 7) * u:
        top = H * rng.uniform(.06, .26); base = hor - 4 * u; wd = rng.uniform(26, 40) * Z
        cs = []
        for j in range(int(11 + 3 * zoom)):                                    # stacked billows, narrowing upward
            t = rng.uniform(0, 1); y = base - (base - top) * t ** .8
            half = wd * (1 - .55 * t)
            cs.append((cx + rng.uniform(-half, half) * .8, y, rng.uniform(.6, .95) * wd * (1 - .4 * t)))
        cs.sort(key=lambda c: -c[1])
        puffs(L, cs, P['cloud'][1:] if kind == 'day' else P['cloud'], rng, light=(-.55, -.85), cell=6 * Z, rough=.18, dark_edge=0, namp=.16)
    layers.append((0.03, L))
    # 2 far mountains (p .12): peaks, horizontal brush streaks
    L = np.zeros((LH, LW, 4), np.uint8)
    top = ridge(LW, hor, [(6 * Z, 230 * Z), (3 * Z, 70 * Z)], rng, peaks=int(6 / zoom) + 2, ph=(14 * Z, 34 * Z), pw=(36 * Z, 80 * Z))
    n = fbm(LH, LW, rng, ((5 * Z, 28 * Z), (2 * Z, 9 * Z), (1, 3)), (.5, .3, .2))
    put(L, yy >= top[None, :], tone(np.clip(.85 - np.clip((yy - top) / (60 * Z), 0, 1) * .5 + (n - .5) * .55, 0, .999), P['far']))
    layers.append((0.12, L))
    # 3 darker hill layer with small trees (p .28)
    L = np.zeros((LH, LW, 4), np.uint8)
    top = ridge(LW, hil, [(7 * Z, 200 * Z), (4 * Z, 70 * Z), (1.5 * Z, 19 * Z)], rng, peaks=3, ph=(8 * Z, 18 * Z), pw=(40 * Z, 80 * Z))
    n = fbm(LH, LW, rng, ((4 * Z, 22 * Z), (2 * Z, 8 * Z), (1, 3)), (.5, .3, .2))
    put(L, yy >= top[None, :], tone(np.clip(.8 - np.clip((yy - top) / (50 * Z), 0, 1) * .55 + (n - .5) * .6, 0, .999), P['hill']))
    step = max(4, int(9 * Z))
    for tx in rng.choice(np.arange(10, LW - 10, step), int(len(np.arange(10, LW - 10, step)) * .5), replace=False):
        r = rng.uniform(3, 6) * Z; ty = top[tx] + 1
        puffs(L, [(tx + rng.uniform(-r, r), ty - rng.uniform(r * .3, r * 1.3), r * rng.uniform(.6, 1)) for _ in range(3)],
              P['hill'], rng, cell=2 * Z)
    layers.append((0.28, L))
    # 4 big trees + hedge (p .55)
    L = np.zeros((LH, LW, 4), np.uint8)
    G = np.concatenate([P['gb'][:5], P['gy'][2:]])
    for tx, hg in ((LW * .5 + 70 * Z, .9), (LW * .2, .75), (LW * .8, .8)):
        tx = int(tx); base = mead + int(2 * Z); th = int(H * .27 * hg * min(zoom, 1.6))
        tw = max(2, int(4 * Z * hg))
        for k in range(-tw, tw + 1):
            col = P['trunk'][min(len(P['trunk']) - 1, int((k + tw) / (2 * tw + 1) * len(P['trunk'])))]
            L[max(0, base - th):base, tx + k, :3] = col; L[max(0, base - th):base, tx + k, 3] = 255
        cs = [(tx + rng.uniform(-36, 36) * u * hg * min(zoom, 1.6), base - th + rng.uniform(-22, 34) * u * hg * min(zoom, 1.6), rng.uniform(8, 14) * u * hg * min(zoom, 1.6)) for _ in range(30)]
        cs.sort(key=lambda c: c[1] - .3 * c[0])
        puffs(L, cs, G, rng, edge=P['edge'], cell=3 * Z)
    for bx in np.arange(0, LW, 46 * Z):
        cs = [(bx + rng.uniform(-24, 24) * Z, mead - rng.uniform(0, 10) * Z, rng.uniform(6, 13) * Z) for _ in range(6)]
        puffs(L, cs, G, rng, edge=P['edge'], cell=3 * Z)
    layers.append((0.55, L))
    # 5 meadow (p 1.0): varied greens in two hue families, streaks, flowers, worn path or road
    L = np.zeros((LH, LW, 4), np.uint8)
    n = fbm(LH, LW, rng, ((3 * Z, 26 * Z), (2 * Z, 9 * Z), (1, 3)), (.45, .35, .2))
    fam = vnoise(LH, LW, 3 * Z, 20 * Z, rng) > .5
    v = np.clip(.85 - np.clip((yy - mead) / (H * .5), 0, 1) * .55 + (n - .5) * .65, 0, .999)
    m = yy >= mead
    put(L, m & fam, tone(v, P['gy'])); put(L, m & ~fam, tone(v, P['gb']))
    xs = np.arange(LW)
    py = int(H * .885)
    pc = py + np.round((3 * np.sin(xs / (60 * Z)) + 2 * np.sin(xs / (21 * Z) + 1)) * u).astype(int)
    pw = np.maximum(4, ((13 + 3 * np.sin(xs / (37 * Z))) * Z * (1.6 if P['road'] else 1))).astype(int)
    pn = fbm(LH, LW, rng, ((2 * Z, 9 * Z), (1, 3)), (.6, .4))
    for x in xs:
        y0, y1 = pc[x] - pw[x] // 2, pc[x] + pw[x] // 2
        if y1 >= LH or y0 < 1: continue
        col = tone(np.clip(.55 + (pn[y0:y1, x] - .5) * 1.2 + np.linspace(.25, -.25, y1 - y0), 0, .999), P['path'])
        col[pn[y0:y1, x] > .72] = P['rut'][int(x) % 2]                    # worn ruts and pebbles
        L[y0:y1, x, :3] = col; L[y0:y1, x, 3] = 255
        if P['road']:
            if (x // max(2, int(10 * Z))) % 2 == 0 and pn[pc[x], x] < .78: L[pc[x]:pc[x] + max(1, int(Z)), x, :3] = (150, 136, 100)
        else:
            for yy_ in (y0 - 1, y1):
                if rng.random() < .5: L[yy_, x, :3] = P['gy'][3]
    for _ in range(int(LW * LH / 220)):
        x, y = int(rng.integers(0, LW)), int(rng.integers(mead + 2, LH))
        if abs(y - pc[x]) <= pw[x] // 2 + 1: continue
        L[y, x, :3] = P['flowers'][rng.choice(5, p=[.32, .26, .26, .1, .06])]
    for _ in range(int(LW * LH / 120)):
        x, y = int(rng.integers(0, LW)), int(rng.integers(mead + 2, LH))
        if abs(y - pc[x]) <= pw[x] // 2 + 1: continue
        hh = int(rng.integers(1, 2 + max(1, int(2 * Z * (y - mead) / H * 3))))
        L[max(0, y - hh):y, x, :3] = P['gb'][int(rng.integers(0, 3))] if rng.random() < .6 else P['gy'][-2]
    layers.append((1.0, L))
    # 6 foreground grass blades + flower heads (p 1.4)
    L = np.zeros((LH, LW, 4), np.uint8)
    yb = H + int(8 * u)
    for _ in range(int(LW * .9)):
        x = int(rng.integers(0, LW)); hh = int(rng.integers(4, 16) * Z); lean = rng.uniform(-.5, .5)
        col = P['gb'][int(rng.integers(0, 3))]
        for k in range(hh):
            y, x2 = yb - k, int(round(x + lean * k * k / max(hh, 1)))
            if 0 <= x2 < LW and 0 <= y < LH: L[y, x2, :3] = col; L[y, x2, 3] = 255
        if rng.random() < .08 and 0 <= yb - hh < LH:
            L[yb - hh, x, :3] = P['flowers'][int(rng.integers(0, 3))]; L[yb - hh, x, 3] = 255
    layers.append((1.4, L))
    return dict(layers=layers, LW=LW, LH=LH, zoom=zoom, ground=py)


def compose(world, ox_px, oy_px, tilt=0.0, smear=0):
    """Paste the layers at whole-pixel parallax offsets. tilt (px) lowers the far layers more than the
    near ones (low camera). smear > 1 duplicates columns for a whip pan (pixel smear, no resampling)."""
    img = np.zeros((H, W, 3), np.uint8); LW, LH = world['LW'], world['LH']
    for p, L in world['layers']:
        x = W // 2 - LW // 2 - int(round(ox_px * p)); y = int(round(oy_px * p + tilt * (1 - min(p, 1))))
        if p < .05: y = min(0, max(H - LH, y))                     # the sky always covers the frame
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + LW, W), min(y + LH, H)
        if x1 <= x0 or y1 <= y0: continue
        src = L[y0 - y:y1 - y, x0 - x:x1 - x]; m = src[..., 3] > 0
        img[y0:y1, x0:x1][m] = src[..., :3][m]
    if smear > 1:
        img = img[:, (np.arange(W) // smear) * smear]
    return img


NAVY = np.array([14, 19, 28], np.float32)


def dark_grade(img):
    c = img.astype(np.float32) * np.array([.09, .11, .13]) + NAVY
    return (np.round(c / 3) * 3).clip(0, 255).astype(np.uint8)


VIG = None


def vignette(img):
    global VIG
    if VIG is None or VIG.shape[:2] != img.shape[:2]:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.hypot((xx - W / 2) / (W * .62), (yy - H / 2) / (H * .62))
        VIG = np.where(d > 1.12, .9, np.where(d > 1.0, .95, 1.0)).astype(np.float32)[..., None]
    return (img * VIG).astype(np.uint8)


# ---------------------------------------------------------------- pixel lines (no AA)
def brush(img, x, y, w, col, mask=None):
    o = -(w // 2); x0, y0 = x + o, y + o
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + w)
    if xb > xa and yb > ya:
        img[ya:yb, xa:xb] = col
        if mask is not None: mask[ya:yb, xa:xb] = True


def pline(img, p0, p1, w, col, mask=None):
    x0, y0 = int(round(p0[0])), int(round(p0[1])); x1, y1 = int(round(p1[0])), int(round(p1[1]))
    if max(abs(x1 - x0), abs(y1 - y0)) > 4 * (W + H): return
    dx, dy = abs(x1 - x0), -abs(y1 - y0); sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1); err = dx + dy
    while True:
        brush(img, x0, y0, w, col, mask)
        if x0 == x1 and y0 == y1: break
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy


def pdisc(img, c, r, col, mask=None):
    cx, cy = int(round(c[0])), int(round(c[1])); rr = int(math.ceil(r))
    for dy in range(-rr, rr + 1):
        span = int(math.floor(math.sqrt(max(0, r * r - dy * dy)) + .5)); y = cy + dy
        if 0 <= y < H:
            xa, xb = max(0, cx - span), min(W, cx + span + 1)
            if xb > xa:
                img[y, xa:xb] = col
                if mask is not None: mask[y, xa:xb] = True


def polymask(pts):
    lay = Image.new('L', (W, H), 0)
    ImageDraw.Draw(lay).polygon([(int(round(x)), int(round(y))) for x, y in pts], fill=1)
    return np.array(lay, bool)


def ppoly(img, pts, col, mask=None):
    m = polymask(pts); img[m] = col
    if mask is not None: mask |= m
    return m


def blend(img, m, col, a, q=6):
    if not np.any(m): return
    c = img[m].astype(np.float32) * (1 - a) + np.asarray(col, np.float32) * a
    img[m] = (np.round(c / q) * q).clip(0, 255).astype(np.uint8)


# ---------------------------------------------------------------- Verlet cloth chains
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
        s.P = s.P + V + np.array([-d * 90.0 * s.back, s.g]) * dt * dt
        s.P[0] = a; s.Q[0] = a
        for _ in range(8):
            for i in range(1, s.n):
                v = s.P[i] - s.P[i - 1]; Ln = max(np.linalg.norm(v), 1e-6)
                s.P[i] = s.P[i - 1] + v / Ln * s.seg
            s.P[:, 1] = np.minimum(s.P[:, 1], -2.0)
            s.P[1:, 0] -= d * np.clip(d * (s.P[1:, 0] - a[0]) + 10, 0, None) * .5
        return s.P.copy()


def draw_cloth(img, pts, w0, w1, cols, mask=None, folds=0):
    P = np.asarray(pts, float); n = len(P)
    t = np.gradient(P, axis=0); t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
    nn = np.stack([-t[:, 1], t[:, 0]], 1)
    wd = np.linspace(w0, w1, n)[:, None] / 2
    A, B = P + nn * wd, P - nn * wd
    ppoly(img, list(map(tuple, A)) + list(map(tuple, B[::-1])), cols[0], mask)
    ppoly(img, list(map(tuple, P)) + list(map(tuple, B[::-1])), cols[1], mask)
    for f in range(folds):
        F = P + nn * wd * ((f + 1) / (folds + 1) * 2 - 1) * .8
        for i in range(2, n): pline(img, F[i - 1], F[i], 1, cols[2])


# ---------------------------------------------------------------- figures
INKC = rgb('#141218'); SKIN = rgb('#8a5a3c'); SKIN2 = rgb('#6b4330'); HAIR = rgb('#1c1412')
TEE = rgb('#f2efe8'); TEE2 = rgb('#c4c0c8'); SHORTS = rgb('#18181e'); SHOE = rgb('#eeeeea')
CAPE = (rgb('#b9473e'), rgb('#8f3430'), rgb('#5e1f22')); SCARF = (rgb('#e5b13c'), rgb('#b5852a'), rgb('#7a5a1c'))
STEEL = (rgb('#e9eef2'), rgb('#aab4bd'), rgb('#5d6670'), rgb('#3b2a1e'))


BODY = {True: (rgb('#1c1518'), rgb('#3b3237')), False: (rgb('#141218'), rgb('#2e2b35'))}


def draw_figure(img, S, I, hero, cloth, mask=None, lim=2, prev=None, blade=None, hr=6.0, flash=False):
    """Pure pixel stickman from whole-pixel joint positions S (Nx3, z = depth): equal-width limb lines,
    one torso line, a big round head. Far-side limbs a shade lighter so crossings read. The hero wears a
    gold scarf, the opponent a red cape (both Verlet chains). prev = previous frame (smear streaks on fast
    limbs); blade = (hand, tip) for the hero's weapon."""
    J = lambda n: S[I[n]][:2]
    zl = np.mean([S[I[n]][2] for n in ('lhumerus', 'lfemur')]); zr = np.mean([S[I[n]][2] for n in ('rhumerus', 'rfemur')])
    near = 'l' if zl < zr else 'r'; far = 'r' if near == 'l' else 'l'
    a, b = J('lowerneck'), J('head')
    u = (b - a) / max(np.linalg.norm(b - a), 1e-6)
    hc = a + u * hr * 1.1
    col, col2 = BODY[hero]
    if flash: col = col2 = rgb('#fbf8f0')                           # white hit flash on the struck body
    if cloth is not None and not hero:
        draw_cloth(img, cloth, max(2, hr * .5), hr * 2.2, CAPE, mask, folds=1)

    def smear(k, c, joints):
        if prev is None: return
        A1, B0, B1 = prev[I[k + joints[1]]][:2], J(k + joints[0]), J(k + joints[1])
        mv_ = np.linalg.norm(B1 - A1)
        if 4 < mv_ < 8 * hr:
            pline(img, A1, B1, max(1, lim - 1), c, mask); pline(img, (A1 + B0) / 2, B1, 1, c, mask)

    def leg(k, c):
        smear(k, c, ('femur', 'tibia'))
        hip, kn, an, ft = J(k + 'hipjoint'), J(k + 'femur'), J(k + 'tibia'), J(k + 'foot')
        pline(img, hip, kn, lim, c, mask); pline(img, kn, an, lim, c, mask)
        pline(img, an, an + (ft - an) * 1.2, lim, c, mask)

    def arm(k, c):
        smear(k, c, ('humerus', 'hand'))
        sh, el, hd = J(k + 'clavicle'), J(k + 'humerus'), J(k + 'hand')
        pline(img, sh, el, lim, c, mask); pline(img, el, hd, lim, c, mask)
        brush(img, int(round(hd[0])), int(round(hd[1])), lim + 1, c, mask)
    arm(far, col2); leg(far, col2)
    if cloth is not None and hero:
        draw_cloth(img, cloth, max(2, hr * .35), max(3, hr * .8), SCARF, mask)
    pline(img, J('root'), J('thorax'), lim + 1, col, mask); pline(img, J('thorax'), hc, lim, col, mask)
    leg(near, col); arm(near, col)
    if hero and blade is not None:
        h0, tip = np.asarray(blade[0], float), np.asarray(blade[1], float)
        dv = (tip - h0) / max(np.linalg.norm(tip - h0), 1e-6); nv = np.array([-dv[1], dv[0]])
        pline(img, h0 - dv * 2, h0 + dv * 2, lim, STEEL[3], mask)
        pline(img, h0 + dv * 2, tip, max(1, lim - 1), STEEL[1], mask)
        pline(img, h0 + dv * 2 - nv, tip - nv, 1, STEEL[0], mask)
        pline(img, h0 + dv * 2 + nv * 2, h0 + dv * 2 - nv * 2, 1, STEEL[2], mask)
    pdisc(img, hc, hr, col, mask)
    return hc, hr


# ---------------------------------------------------------------- effects
def fx_impact(img, c, age, z, d):
    """Punch impact: a big pixel star on the contact frames, shrinking into short rays, then dots."""
    if age >= 7: return
    k = [1.0, 1.0, .75, .55, .4, .3, .2][age]
    for a, L_ in ((0, 1.0), (math.pi / 2, .8), (math.pi, 1.0), (-math.pi / 2, .8)):
        L_ *= 15 * z * k; ca, sa = math.cos(a), math.sin(a)
        w = max(1.0, 3.2 * z * k)
        pts = [(c[0] + ca * L_, c[1] + sa * L_), (c[0] - sa * w, c[1] + ca * w), (c[0] - ca * w, c[1] - sa * w), (c[0] + sa * w, c[1] - ca * w)]
        if age < 4: ppoly(img, pts, (255, 255, 255))
    if age < 2: pdisc(img, c, 3.5 * z, (255, 250, 220))
    for j in range(8):                                                   # thin diagonal rays, growing outward
        a = math.pi / 4 + j * math.pi / 4 + (0 if d > 0 else .2)
        r0, r1 = (6 + age * 3) * z, (11 + age * 4.5) * z
        if 1 <= age < 6 and j % 2 == 0:
            pline(img, (c[0] + math.cos(a) * r0, c[1] + math.sin(a) * r0), (c[0] + math.cos(a) * r1, c[1] + math.sin(a) * r1), 1, (255, 244, 200))


def fx_trail(img, pts, w):
    """Speed trail behind a fist/foot: a tapered pale strip along its last positions, brightest at the tip."""
    P = np.asarray(pts, float)
    if len(P) < 2 or np.linalg.norm(P[-1] - P[0]) < 4: return
    for i in range(1, len(P)):
        u = i / (len(P) - 1)
        m = np.zeros((H, W), bool); pline(np.zeros((H, W, 3), np.uint8), P[i - 1], P[i], max(1, int(round(w * u))), (0, 0, 0), m)
        blend(img, m, (255, 252, 238), .25 + .55 * u)


def fx_shock(img, c, age, z, d):
    """Shock lines flung out behind the struck head, in the hit direction."""
    if age >= 8: return
    for j, a in enumerate((-.5, -.15, .2, .55)):
        ang = (0 if d > 0 else math.pi) + a
        r0, r1 = (10 + age * 4) * z, (18 + age * 6) * z * (1 - .2 * (j % 2))
        if age > 5 and j % 2: continue
        pline(img, (c[0] + math.cos(ang) * r0, c[1] + math.sin(ang) * r0), (c[0] + math.cos(ang) * r1, c[1] + math.sin(ang) * r1), 1, (255, 255, 255))


WHITE = np.array([255, 255, 255], np.float32)
GLOW = np.array([220, 238, 255], np.float32)
FIRE = ramp('#fff6d8', '#ffe08a', '#ffb347', '#ff7a2e', '#e8432e', '#a8242a')
NOISE = None


def soft_glow(img, c, r, col, a, seed=0, levels=3):
    """Soft clumped glow: noise-modulated radial falloff, blended in a few quantised levels."""
    global NOISE
    if NOISE is None or NOISE.shape != (H, W):
        NOISE = vnoise(H, W, 3, 3, np.random.default_rng(5))
    x0, x1, y0, y1 = int(max(0, c[0] - r)), int(min(W, c[0] + r + 1)), int(max(0, c[1] - r)), int(min(H, c[1] + r + 1))
    if x1 <= x0 or y1 <= y0 or r < 1: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    f = np.clip(1 - np.hypot(xx - c[0], yy - c[1]) / r, 0, 1) * (.7 + .6 * np.roll(NOISE, seed % 17, 1)[y0:y1, x0:x1])
    sub = img[y0:y1, x0:x1]
    for i in range(levels):
        m = f > (i + .5) / (levels + .5)
        if m.any():
            cc = sub[m].astype(np.float32) * (1 - a) + np.asarray(col, np.float32) * a
            sub[m] = (np.round(cc / 6) * 6).clip(0, 255).astype(np.uint8)


def crescent_cov(path, th, ss=4):
    P = np.asarray(path, float)
    t = np.gradient(P, axis=0); t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
    nn = np.stack([-t[:, 1], t[:, 0]], 1); O = P + nn * th[:, None]
    x0, y0 = int(max(0, min(P[:, 0].min(), O[:, 0].min()) - 3)), int(max(0, min(P[:, 1].min(), O[:, 1].min()) - 3))
    x1, y1 = int(min(W, max(P[:, 0].max(), O[:, 0].max()) + 4)), int(min(H, max(P[:, 1].max(), O[:, 1].max()) + 4))
    if x1 <= x0 or y1 <= y0: return None
    lay = Image.new('L', ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    ImageDraw.Draw(lay).polygon([((x - x0) * ss, (y - y0) * ss) for x, y in list(P) + list(O[::-1])], fill=255)
    a = np.array(lay, np.float32).reshape(y1 - y0, ss, x1 - x0, ss).mean((1, 3)) / 255
    full = np.zeros((H, W), np.float32); full[y0:y1, x0:x1] = a
    return full


def trim_arc(P, maxlen):
    """Keep the last part of the path whose arc length is <= maxlen (never longer than the weapon)."""
    P = np.asarray(P, float)
    if len(P) < 2: return P
    seg = np.r_[0, np.linalg.norm(np.diff(P, axis=0), axis=1)]
    from_end = np.cumsum(seg[::-1])[::-1] - seg
    return P[from_end <= maxlen]


def fx_slash(img, path, age, life, side, z=1.0, red=False, maxlen=1e9):
    P = trim_arc(path, maxlen)
    if len(P) < 3: return
    grow = min(1.0, (age + 1) / 3); P = P[:max(3, int(len(P) * grow))]
    k = max(0.0, 1 - max(0, age - 3) / max(life - 3, 1))
    P = P[int(len(P) * (1 - k) * .7):]
    if len(P) < 3: return
    u = np.linspace(0, 1, len(P))
    th = (3.4 * z * k + .5) * np.sin(np.pi * np.clip(u * .9 + .08, 0, 1)) ** .8 * side
    cov = crescent_cov(P, th)
    if cov is None: return
    halo = cv2.dilate((cov > .05).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (cov < .05)
    blend(img, halo, GLOW, .18 * k)
    blend(img, (cov > .05) & (cov <= .4), WHITE, .45)
    blend(img, (cov > .4) & (cov <= .75), WHITE, .8)
    img[cov > .75] = (255, 255, 255)
    if red:
        img[(cov > .05) & (cov <= .4) & (np.roll(cov, int(np.sign(side)), 0) > .75)] = (232, 64, 50)


def ember(img, x, y, col, glow=True):
    if not (0 <= x < W and 0 <= y < H): return
    if glow:
        m = np.zeros((H, W), bool); m[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = True
        blend(img, m, col, .3)
    img[y, x] = col


def fx_fire(img, c, age, z, d, seed, big=False, life=20):
    """Soft streaky fire: clumped glow halo + flame streaks along the strike, rising licks, glowing embers."""
    if age >= life: return
    rng = np.random.default_rng(seed)
    k = 1 - age / life
    R = (8 + age * 1.8) * z * (1.3 if big else 1)
    soft_glow(img, c, R * 1.5, FIRE[4], .2 * k, seed)
    soft_glow(img, c, R * .9, FIRE[3], .32 * k, seed + 3)
    if age < 7: soft_glow(img, c, R * .45, FIRE[1], .55, seed + 5)
    for j in range(16 if big else 11):
        ang = (0 if d > 0 else math.pi) * (1 if j % 4 else 0) + (rng.normal(0, .35) if j % 4 else -math.pi / 2 + rng.normal(0, .5))
        Ls = rng.uniform(.5, 1.0) * R * 1.5 * min(1, (age + 2) / 4)
        st = rng.uniform(0, .4) * R + age * 1.0 * z
        p0 = (c[0] + math.cos(ang) * st, c[1] + math.sin(ang) * st - age * .5 * z)
        p1 = (c[0] + math.cos(ang) * (st + Ls), c[1] + math.sin(ang) * (st + Ls) - age * .9 * z)
        if age > life * .7 and j % 2: continue
        col = FIRE[min(5, int(j % 3 + age / life * 3.5))]
        pline(img, p0, p1, 2 if (j % 3 == 0 and age < 8) else 1, col)
    for j in range(22 if big else 14):
        a = rng.uniform(0, 2 * math.pi); sp = rng.uniform(1.0, 2.8) * z
        x = c[0] + math.cos(a) * sp * age * 1.2; y = c[1] + math.sin(a) * sp * age * .8 + .05 * age * age
        if age < life - (j % 5):
            ember(img, int(x), int(y), (FIRE[4] if j % 3 else FIRE[3]), glow=(j % 3 == 0))


def fx_spark(img, c, age, z, d, seed, life=12):
    if age >= life: return
    rng = np.random.default_rng(seed); k = 1 - age / life
    soft_glow(img, c, (6 + age) * z, FIRE[1], .35 * k, seed)
    if age < 5:
        for j in range(7):
            a = (0 if d > 0 else math.pi) + rng.normal(0, .8)
            r0, r1 = (2 + age * 1.5) * z, (6 + age * 3) * z * rng.uniform(.7, 1.2)
            pline(img, (c[0] + math.cos(a) * r0, c[1] + math.sin(a) * r0), (c[0] + math.cos(a) * r1, c[1] + math.sin(a) * r1),
                  1, (255, 250, 230) if j % 2 else FIRE[1])
    for j in range(12):
        a = (0 if d > 0 else math.pi) + rng.normal(0, 1.0); sp = rng.uniform(1.2, 3) * z
        x = c[0] + math.cos(a) * sp * age * 1.3; y = c[1] + math.sin(a) * sp * age + .06 * age * age
        if age < life - (j % 4): ember(img, int(x), int(y), FIRE[4] if j % 2 else FIRE[3], glow=(j % 4 == 0))


def fx_dust(img, c, age, z, d, col=(206, 198, 166)):
    if age >= 12: return
    for j, ox in enumerate((-5, 0, 5)):
        r = (1.5 + age * .4) * z
        x = c[0] + (ox * (1 + age * .12) + d * age * .3) * z; y = c[1] - (1 + age * .35) * z - (j == 1)
        m = np.zeros((H, W), bool); pdisc(np.zeros((H, W, 3), np.uint8), (x, y), r, (0, 0, 0), m)
        blend(img, m, col, .55 * (1 - age / 12))


# ---------------------------------------------------------------- transition art (same pixel rules)
SKINR = ramp('#4f3124', '#62402d', '#774f37', '#8a5a3c', '#a06c48', '#b98058', '#d09a6c')
HAIRR = ramp('#120c0a', '#1c1412', '#2a1f1a', '#3a2c24')
TEER = ramp('#9a96a0', '#b3b0b8', '#cac7cc', '#dedbdc', '#efece6', '#f8f6f0')


def shade_region(img, m, R, light_x, light_y, cx, cy, r, k_light, nz, ambient=.35, namp=.12):
    """Clumped ramp shading for a round-ish region lit by the headlights (from light_x, light_y)."""
    yy, xx = np.mgrid[0:H, 0:W]
    nx, ny = (xx - cx) / r, (yy - cy) / r
    lam = np.clip(nx * light_x + ny * light_y, -1, 1)
    v = ambient + .5 * k_light * (lam + 1) / 2 + (nz - .5) * namp - np.hypot(nx, ny) * .12
    img[m] = tone(np.clip(v, 0, .999), R)[m]


def outline(img, m, col):
    o = np.zeros_like(m)
    o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    img[o & ~m] = col


def face(i, bg):
    """Close-up of the stickman hero's round head: black pixel head with a 1-px warm rim from the
    headlights, two white eyes that widen, each catching the two headlights; gold scarf below."""
    img = bg.copy()
    k = min(1.0, (i + 3) / 18)
    soft_glow(img, (W * 1.1, H * .4), W * (0.6 + .5 * k), (255, 214, 150), .22 * k, 3, levels=4)
    soft_glow(img, (W * 1.05, H * .4), W * (0.35 + .3 * k), (255, 238, 196), .3 * k, 7, levels=3)
    yy, xx = np.mgrid[0:H, 0:W]
    r = W * .27; c = np.array([W * .46 - i * .08, H * .44])
    col = BODY[True][0]
    pline(img, (c[0] - r * .1, c[1] + r * .9), (c[0] - r * .45, H + 4), max(3, int(r * .12)), col)          # neck + torso line
    sc_ = [(c[0] - r * .55, c[1] + r * 1.05), (c[0] + r * .35, c[1] + r * 1.0), (c[0] + r * .3, c[1] + r * 1.28), (c[0] - r * .6, c[1] + r * 1.32)]
    m = polymask(sc_); img[m] = SCARF[0]; img[m & (yy > c[1] + r * 1.17)] = SCARF[1]
    tail = polymask([(c[0] - r * .55, c[1] + r * 1.08), (c[0] - r * 1.3 - i * .3, c[1] + r * 1.45), (c[0] - r * 1.2 - i * .3, c[1] + r * 1.7), (c[0] - r * .5, c[1] + r * 1.3)])
    img[tail] = SCARF[1]
    head = ((xx - c[0]) / r) ** 2 + ((yy - c[1]) / r) ** 2 <= 1
    img[head] = col
    lit = head & (((xx - c[0] - r * .35) / r) ** 2 + ((yy - c[1] + r * .1) / r) ** 2 > .62) & (xx > c[0] + r * .2)
    img[lit] = rgb('#3a2c2a') if k < .5 else rgb('#5a4034')                                                   # warm light on the lit side
    if k > .3: img[head & ~np.roll(head, -1, 1) & (xx > c[0])] = (255, 220, 160)                             # rim
    shock = i >= 8
    for ex, ew in ((c[0] + r * .2, r * .2), (c[0] + r * .62, r * .15)):
        ey = c[1] - r * .05; eh = ew * (1.25 if shock else .7)
        e = ((xx - ex) / ew) ** 2 + ((yy - ey) / eh) ** 2 <= 1
        img[e] = (240, 238, 232)
        pr = max(1.6, ew * .45)
        img[((xx - (ex + ew * .3)) ** 2 + (yy - ey) ** 2 <= pr * pr) & e] = col
        for dx in (-.35, .45):                                           # two headlight reflections in each eye
            px, py = int(round(ex + ew * .3 + dx * pr)), int(round(ey - pr * .45))
            if 0 <= py < H and 0 <= px < W: img[py, px] = (255, 252, 236)
    return img


CARR = ramp('#123f3e', '#175450', '#1e6b64', '#278479', '#35a090', '#52b9a6', '#86d1c0')


def draw_car(img, x0, p, cam_x, sc, gy):
    """Pixel car in the same style: 1-px ink outline, clumped ramp shading (top lit), windows reflecting
    the dusk sky, glowing headlight."""
    c, sn = math.cos(-p), math.sin(-p)

    def T(pts):
        out = []
        for x, y in pts:
            x = x - 120; x, y = x * c - y * sn, x * sn + y * c
            out.append((int(round((x0 + 120 + x) * sc)) - cam_x + W // 2, int(round(y * sc)) + gy))
        return out
    body = [(30, -95), (10, -150), (40, -215), (190, -240), (300, -365), (590, -370), (700, -245), (790, -230), (800, -150), (780, -95)]
    m = polymask(T(body))
    yy, xx = np.mgrid[0:H, 0:W]
    ys = np.where(m)[0]
    if len(ys):
        nz = vnoise(H, W, 2, 4, np.random.default_rng(3))
        v = .85 - (yy - ys.min()) / max(ys.max() - ys.min(), 1) * .7 + (nz - .5) * .3
        img[m] = tone(np.clip(v, 0, .999), CARR)[m]
    sky = ramp('#4c406f', '#735076', '#a46670', '#cf8c6c')
    for win in ([(318, -340), (440, -345), (440, -250), (250, -250)], [(460, -345), (575, -345), (650, -250), (460, -250)]):
        w = polymask(T(win)); wy = np.where(w)[0]
        if len(wy): img[w] = tone(np.clip((yy - wy.min()) / max(1, wy.max() - wy.min()), 0, .999), sky)[w]
        outline(img, w, INKC)
    img[polymask(T([(20, -125), (800, -125), (795, -95), (30, -95)]))] = CARR[1]
    pline(img, *T([(70, -205), (690, -230)]), 1, CARR[6])
    outline(img, m, INKC)
    for wx in (160, 640):
        q = T([(wx, -70)])[0]
        pdisc(img, q, 70 * sc, INKC); pdisc(img, q, 44 * sc, rgb('#2a2c34')); pdisc(img, q, 26 * sc, rgb('#7c8590')); pdisc(img, q, 10 * sc, rgb('#3d424c'))
    hl = T([(36, -180)])[0]
    soft_glow(img, hl, 26 * sc * 4, (255, 230, 170), .35, 11)
    pdisc(img, hl, max(2, 22 * sc), (255, 250, 222))
    tl = T([(782, -200)])[0]; soft_glow(img, tl, 60 * sc, (232, 51, 42), .3, 4); pdisc(img, tl, max(1.5, 14 * sc), (232, 60, 48))
    return hl
