"""Tyre wear bars: native 135x240 indexed pixel renderer (32-colour palette, daytime street).

python render.py still <outdir> t1 t2 ...   -> 1080x1920 PNG stills (nearest x8)
python render.py video <outdir>             -> master (yuv444p lossless, silent) + final.mp4
Every frame is drawn in palette indices at native size; the only upscale is
ffmpeg flags=neighbor x8. Animation is stepped: one unique drawing per hold of
2-4 output frames (uneven), duplicated up to 30 fps.
"""
import json, math, subprocess, sys
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / 'new-car-trap' / 'src'))
import pix  # noqa: E402  (reuse Bresenham line helper)

W, H, S, FPS = 135, 240, 8, 30
DUR = 13.0
NF = int(DUR * FPS)
T = 255  # transparent index

PAL_HEX = ['#1a1424', '#a8d8ea', '#7fb8dc', '#c8d8e2', '#24202e', '#8c9cc0', '#6f7ea6', '#c8735a',
           '#94505a', '#e0c89a', '#b09a84', '#3f9a96', '#6cd8c8', '#d0504a', '#4a6488', '#9cc4dc',
           '#5a9a4a', '#35684a', '#4a4a5a', '#33333f', '#9a94a0', '#d8d4cc', '#4a78b8', '#34518a',
           '#86b0dc', '#3a3346', '#6a5d6e', '#c88a5e', '#8e5a4e', '#9aa3b8', '#ffe040', '#e0702a']
(K, SKY1, SKY2, CLD, R0, FAR, FARS, BRK, BRKS, CRM, CRMS, TEAL, CYAN, RED, GLS, GLH,
 GRN, GRNS, ASP, ASPD, SIDE, WH, CAR, CARS, CARH, R1, R2, SK, SS, GY, BY, BO) = range(32)
B0, B1, B2, TL, MG = ASPD, ASP, FARS, CYAN, RED      # roles used by plates / close-ups
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in PAL_HEX], np.uint8)
assert len(PAL) == 32

# ------------------------------------------------------------------ drawing primitives
def R(cv, x0, y0, x1, y1, c):
    x0, x1 = max(0, x0), min(cv.shape[1] - 1, x1)
    y0, y1 = max(0, y0), min(cv.shape[0] - 1, y1)
    if x0 <= x1 and y0 <= y1:
        cv[y0:y1 + 1, x0:x1 + 1] = c


def P(cv, x, y, c):
    if 0 <= x < cv.shape[1] and 0 <= y < cv.shape[0]:
        cv[y, x] = c


def line(cv, a, b, c, th=1):
    for x, y in pix._line(a, b):
        R(cv, x, y, x + th - 1, y + th - 1, c)


def blit(cv, spr, x, y):
    h, w = spr.shape
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(w, cv.shape[1] - x), min(h, cv.shape[0] - y)
    if sx0 >= sx1 or sy0 >= sy1:
        return
    sub = spr[sy0:sy1, sx0:sx1]
    dst = cv[y + sy0:y + sy1, x + sx0:x + sx1]
    m = sub != T
    dst[m] = sub[m]


def outline(spr, c=K):
    o = spr.copy()
    op = spr != T
    p = np.pad(op, 1)
    near = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    o[(~op) & near] = c
    return o


def pad(spr, n=1):
    return np.pad(spr, n, constant_values=T)


def h01(x, y, seed=0):
    """Deterministic hash noise in [0,1)."""
    v = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return (v ^ (v >> 16)) / 2 ** 32

# ------------------------------------------------------------------ text (Press Start 2P, OFL)
FONT_PATH = HERE / 'fonts' / 'PressStart2P-Regular.ttf'
TEXT_REPORT = {}


@lru_cache(None)
def text_mask(s, size):
    f = ImageFont.truetype(str(FONT_PATH), size)
    l, t, r, b = f.getbbox(s)
    im = Image.new('L', (r + 4, b + 4), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = '1'
    d.text((0, 0), s, font=f, fill=255)
    a = np.array(im)
    assert set(np.unique(a)) <= {0, 255}, 'antialiased text'
    m = a > 0
    return m


def lum(c):
    v = PAL[c] / 255.0
    v = np.where(v <= 0.03928, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def text_box(cv, name, lines, box, size=8, fg=WH, bg=K, border=B2, lead=4, pad_=3, align='center'):
    """Solid plate + text. Raises (FAIL) if any line overflows or is clipped."""
    x0, y0, x1, y1 = box
    masks = [text_mask(s, size) for s in lines]
    ws = [int(m.any(0).nonzero()[0].max() + 1) if m.any() else 0 for m in masks]
    hs = [int(m.any(1).nonzero()[0].max() + 1) if m.any() else 0 for m in masks]
    iw, ih = x1 - x0 + 1 - 2 * pad_, y1 - y0 + 1 - 2 * pad_
    th = len(lines) * size + (len(lines) - 1) * lead
    inside = x0 >= 0 and y0 >= 0 and x1 < W and y1 < H
    fits = inside and max(ws) <= iw and th <= ih and max(hs) <= size
    cr = contrast(fg, bg)
    TEXT_REPORT[name] = dict(lines=lines, plate=list(box), widths=ws, inner_w=iw, text_h=th, inner_h=ih,
                             fits=bool(fits), contrast=round(float(cr), 2))
    if not fits:
        raise SystemExit(f'TEXT OVERFLOW/CLIP: {name} {lines} widths={ws} inner={iw}x{ih} box={box}')
    keep = [(x, y, cv[y, x]) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    R(cv, x0, y0, x1, y1, border)
    R(cv, x0 + 1, y0 + 1, x1 - 1, y1 - 1, bg)
    for x, y, c in keep:                      # chipped corners: plates aren't perfect boxes
        cv[y, x] = c
    y = y0 + pad_ + (ih - th) // 2
    for m, w in zip(masks, ws):
        x = x0 + pad_ + ((iw - w) // 2 if align == 'center' else 0)
        ys, xs = np.nonzero(m)
        before = len(xs)
        ok = (x + xs >= x0 + pad_) & (x + xs <= x1 - pad_) & (y + ys >= y0 + pad_) & (y + ys <= y1 - pad_)
        if ok.sum() != before:
            raise SystemExit(f'TEXT CLIPPED: {name}')
        cv[y + ys, x + xs] = fg
        y += size + lead


def grow_plate(cv, box, frac, border=B2, bg=K):
    """Stepped plate entrance (whole-pixel widths, no text yet)."""
    x0, y0, x1, y1 = box
    cx, hw = (x0 + x1) // 2, int((x1 - x0) * frac / 2)
    R(cv, cx - hw, y0, cx + hw, y1, border)
    R(cv, cx - hw + 1, y0 + 1, cx + hw - 1, y1 - 1, bg)

# ------------------------------------------------------------------ RotSprite-style rotation
def scale2x(a):
    p = np.pad(a, 1, mode='edge')
    B, D, E, F, Hh = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:], p[2:, 1:-1]
    out = np.empty((a.shape[0] * 2, a.shape[1] * 2), a.dtype)
    out[0::2, 0::2] = np.where((D == B) & (B != F) & (D != Hh), D, E)
    out[0::2, 1::2] = np.where((B == F) & (B != D) & (F != Hh), F, E)
    out[1::2, 0::2] = np.where((D == Hh) & (D != B) & (Hh != F), D, E)
    out[1::2, 1::2] = np.where((Hh == F) & (D != Hh) & (B != F), F, E)
    return out


def rotsprite(spr, deg):
    big = scale2x(scale2x(scale2x(spr)))                     # x8 with edge-aware smoothing of the grid
    im = Image.fromarray(big, 'L').rotate(deg, resample=Image.NEAREST, fillcolor=T)
    return np.array(im)[4::8, 4::8].copy()                   # back to native, centre-sampled

# ------------------------------------------------------------------ tyre (side view, n x n)
def _tyre_geom(n):
    c = (n - 1) / 2
    yy, xx = np.mgrid[0:n, 0:n]
    dx, dy = xx - c, yy - c
    r = np.hypot(dx, dy)
    th = np.arctan2(-dy, dx) % (2 * np.pi)
    return xx, yy, dx, dy, r, th


@lru_cache(None)
def tyre_core(n=28, lit=False):
    """Chunky tread blocks with ragged edges; the wear bar sits in the top groove."""
    xx, yy, dx, dy, r, th = _tyre_geom(n)
    Rr = n / 2 - 0.4
    nb = 10 if n < 40 else 12
    rng = np.random.default_rng(11 + n)
    lo = 0.20 + rng.random(nb) * 0.07
    hi = 0.80 - rng.random(nb) * 0.07
    ro = Rr + 0.1 - rng.integers(0, 2, nb) * (0.7 if n < 40 else 1.0)
    phase = ((th - np.pi / 2) / (2 * np.pi / nb)) % nb
    blk = np.floor(phase).astype(int) % nb
    fr = phase - np.floor(phase)
    nrm = np.cos(th - 3 * np.pi / 4)           # light from upper-left (warm highlight, cool shadow)
    spr = np.full((n, n), T, np.uint8)
    in_blk = (fr > lo[blk]) & (fr < hi[blk])
    edge = np.minimum(fr - lo[blk], hi[blk] - fr)
    rout = ro[blk] - (edge < 0.06) * 1.0
    t0 = 0.81 * Rr
    tread = (r >= t0) & (r <= rout) & in_blk
    spr[tread] = R1
    spr[tread & (r >= rout - 1.3) & (nrm > 0.25)] = R2
    spr[tread & (nrm < -0.45)] = R0
    spr[(r >= t0) & (r < t0 + 1.2) & ~in_blk] = R0
    g0 = ((phase < 0.27) | (phase > nb - 0.27)) & (r >= t0 + 1.2) & (r < t0 + 2.6)
    spr[g0] = R1
    if lit:
        spr[g0] = BO
        spr[g0 & (r >= t0 + 1.9)] = BY
    side = (r >= 0.56 * Rr) & (r < t0)
    spr[side] = R1
    spr[side & (r >= 0.72 * Rr) & (nrm > 0.35)] = R2
    shadow = side & (nrm < -0.3)
    spr[shadow] = R0
    spr[shadow & (np.vectorize(h01)(xx, yy, 3) < 0.07)] = K       # texture only in shadow
    if n >= 40:
        tri = (dy < 0) & (r >= 0.64 * Rr) & (r < 0.77 * Rr) & (np.abs(dx) <= (0.77 * Rr - r) * 0.75)
        spr[tri] = GY
    lip = (r >= 0.5 * Rr) & (r < 0.56 * Rr + 0.6)
    spr[lip] = GY
    spr[lip & (nrm > 0.2)] = WH
    spr[lip & (nrm < -0.3)] = FARS
    dish = r < 0.5 * Rr
    spr[dish] = FARS
    sp = (np.degrees(th) - 18) % 72
    hole = dish & (r > 0.17 * Rr) & (r < 0.44 * Rr) & (sp > 14) & (sp < 58)
    spr[hole] = K
    spr[dish & ~hole & (r >= 0.12 * Rr) & (nrm > 0.3)] = GY
    spr[r < 0.13 * Rr + 0.5] = WH
    return spr


@lru_cache(None)
def tyre(n=28, lit=False):
    return outline(pad(tyre_core(n, lit)))


@lru_cache(None)
def tyre_rot(n, i):
    """16 pre-baked angles (22.5 degree steps), RotSprite-style; i>0 turns clockwise."""
    return outline(pad(rotsprite(tyre_core(n, False), -i * 22.5))) if i % 16 else tyre(n, False)

# ------------------------------------------------------------------ small sprites
def _spr(rows, cmap):
    a = np.full((len(rows), max(len(r) for r in rows)), T, np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in cmap:
                a[y, x] = cmap[ch]
    return a


ARROW_DN = outline(pad(_spr(['  ww  ', '  ww  ', '  ww  ', 'wwwwww', ' wwww ', '  ww  '], {'w': WH})))
CURSOR = outline(pad(_spr(['w    ', 'ww   ', 'www  ', 'wwww ', 'wwwww', 'www  ', 'w ww ', '  ww '], {'w': WH})))

# ------------------------------------------------------------------ presenter (mini head in the car)
@lru_cache(None)
def head(expr='smile'):
    """Main guy at car scale: dark messy hair, brown skin, silver square glasses, white tee."""
    s = np.full((15, 12), T, np.uint8)
    P(s, 4, 0, K); P(s, 7, 0, K)                      # cowlicks
    R(s, 2, 1, 9, 3, K); R(s, 1, 2, 10, 4, K)
    R(s, 3, 1, 5, 1, R1)                              # hair sheen
    R(s, 2, 4, 9, 11, SK)
    R(s, 1, 4, 1, 6, K); R(s, 10, 4, 10, 5, K); P(s, 2, 4, K); P(s, 9, 4, K)
    R(s, 9, 6, 9, 9, SS)                              # cool shadow side of face
    for x0 in (2, 6):                                 # glasses
        R(s, x0, 5, x0 + 2, 7, GY)
        P(s, x0 + 1, 6, SK if expr == 'blink' else K)
    P(s, 5, 6, GY); P(s, 2, 5, WH)
    if expr == 'blink':
        R(s, 3, 7, 3, 7, GY); R(s, 7, 7, 7, 7, GY)
    P(s, 6, 8, SS)                                    # nose
    if expr == 'talk':
        R(s, 4, 9, 6, 10, K); P(s, 5, 10, RED)
    else:
        P(s, 3, 9, SS); P(s, 7, 9, SS); R(s, 4, 10, 6, 10, K)
    R(s, 3, 11, 8, 11, SK); R(s, 4, 12, 7, 12, SS)
    R(s, 1, 13, 10, 14, WH); R(s, 8, 13, 10, 14, GY)  # tee shoulders
    return outline(s)


@lru_cache(None)
def person(shirt, skin, hair, frame, flip=False):
    """Pedestrian, 2-frame walk cycle."""
    legs = ['  dd  ', ' d  d ', 'd    d'] if frame else ['  dd  ', '  dd  ', '  dd  ']
    rows = ['  hh  ', ' hhhh ', ' ssss ', ' ssss ', '  ss  ', ' cccc ', 'cccccc', 'scccc s'[:6], ' cccc ',
            ' cccc ', ' dddd ', ' dddd '] + legs + ['kk  kk' if frame else ' kkkk ']
    s = _spr(rows, {'h': hair, 's': skin, 'c': shirt, 'd': GLS, 'k': K})
    return outline(s[:, ::-1] if flip else s)


BIRD = [_spr(['k   k', ' k k ', '  k  '], {'k': K}), _spr(['     ', 'kk kk', '  k  '], {'k': K})]

# ------------------------------------------------------------------ the car (side view, faces right)
CAR_X, CAR_Y = 9, 144           # sprite origin on screen (sprite has 8 px headroom for the arm)
WHEEL_N = 28
WHEELS = (22, 94)               # wheel centres, car-local x
WHEEL_CY = 8 + 31               # car-local y
GROUND = CAR_Y + 8 + 45


def _car_top(x):
    if x < 4: return 22
    if x < 15: return 20 - (x - 4) * 14 // 11
    if x < 80: return 2 + (1 if x < 22 or x > 74 else 0)
    if x < 96: return 3 + (x - 80) * 15 // 16
    if x < 114: return 18 + (x - 96) // 6
    return 21 + (x - 114)


@lru_cache(None)
def car_body():
    s = np.full((54, 118), T, np.uint8)
    o = 8
    for x in range(118):
        top = _car_top(x)
        for y in range(top, 37):
            arch = any((x - wc) ** 2 + (y - 31) ** 2 < 15 ** 2 for wc in WHEELS)
            if not arch:
                s[y + o, x] = CAR
        if 0 <= top < 37:
            s[top + o, x] = CARH
    # shading: warm-ish highlight shoulder, cool lower body
    for x in range(118):
        for y in range(28, 37):
            if s[y + o, x] == CAR:
                s[y + o, x] = CARS
        if s[18 + o, x] == CAR:
            s[18 + o, x] = CARH
    # greenhouse
    for x in range(14, 93):
        for y in range(_car_top(x) + 2, 17):
            if s[y + o, x] in (CAR, CARH):
                s[y + o, x] = GLS
    R(s, 14, o + 2, 21, o + 16, CAR)                 # C-pillar
    for x in range(14, 22):                           # keep the rear slope
        for y in range(_car_top(x) + 2, _car_top(x) + 4):
            if s[y + o, x] == GLS: s[y + o, x] = CAR
    R(s, 50, o + 3, 53, o + 16, CAR); R(s, 53, o + 3, 53, o + 16, CARS)   # B-pillar
    for x0 in (26, 58):                               # hand-placed window glints
        for i in range(6):
            P(s, x0 + i, o + 13 - i * 2, GLH); P(s, x0 + i + 1, o + 13 - i * 2, GLH)
    R(s, 14, o + 17, 92, o + 17, CARS)               # beltline
    R(s, 52, o + 18, 52, o + 33, CARS); R(s, 85, o + 18, 85, o + 30, CARS)   # door seams
    R(s, 43, o + 21, 46, o + 21, GY); R(s, 76, o + 21, 79, o + 21, GY)       # handles
    R(s, 88, o + 13, 92, o + 16, CAR); R(s, 88, o + 13, 92, o + 13, CARH)    # mirror
    R(s, 110, o + 21, 115, o + 23, CRM); P(s, 114, o + 21, WH)              # headlight
    R(s, 1, o + 21, 3, o + 25, RED)                                          # tail light
    R(s, 106, o + 30, 117, o + 33, GY); R(s, 106, o + 33, 117, o + 33, FARS)  # bumpers
    R(s, 0, o + 30, 9, o + 33, GY); R(s, 0, o + 33, 9, o + 33, FARS)
    R(s, 36, o + 35, 80, o + 36, K)                  # sill shadow
    for wc in WHEELS:                                 # dark wheel-arch lining
        for x in range(wc - 16, wc + 17):
            for y in range(16, 37):
                d = (x - wc) ** 2 + (y - 31) ** 2
                if 15 ** 2 <= d < 16.5 ** 2 and 0 <= x < 118 and s[y + o, x] != T:
                    s[y + o, x] = K
    return s


def arm(s, pose, k):
    """Presenter's arm out of the driver window (car-local, sprite coords)."""
    if pose == 'point':                              # down toward the front tyre
        pts = [(80, 24), (82, 25), (84, 26), (86, 27), (88, 28), (89, 29)]
        R(s, 78, 22, 80, 24, WH)
        for x, y in pts:
            R(s, x, y, x + 1, y + 1, SK)
        R(s, 89, 29, 91, 31, SK); R(s, 92, 31, 93, 31, SK)
    elif pose in ('wave1', 'wave2'):                 # up over the roof
        R(s, 82, 20, 84, 22, WH)
        hx = 88 if pose == 'wave1' else 91
        for x, y in pix._line((84, 18), (hx, 4)):
            R(s, x, y, x + 1, y + 1, SK)
        R(s, hx - 1, 1, hx + 2, 4, SK)


def car_sprite(expr, pose, k):
    s = car_body().copy()
    hd = head(expr)
    win = s[8 + 4:8 + 17, 60:84] == GLS
    sub = np.full((13, 24), T, np.uint8)
    blit(sub, hd, 8, 0)
    s[12:25, 60:84][win & (sub != T)] = sub[win & (sub != T)]
    if pose:
        arm(s, pose, k)
    return outline(s)

# ------------------------------------------------------------------ the street (parallax layers)
NW, FWD, CW = 420, 300, 400
F_CLOUD, F_FAR, F_NEAR, F_ROAD, F_FRONT = 0.1, 0.3, 0.6, 1.0, 1.3
SIDEWALK = 150


def _disc(a, cx, cy, r, c):
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.5:
                if 0 <= y < a.shape[0]:
                    a[y, x % a.shape[1]] = c


@lru_cache(None)
def clouds():
    a = np.full((70, CW), T, np.uint8)
    for cx, cy, s in ((40, 30, 1.0), (150, 18, 0.8), (250, 40, 1.2), (340, 24, 0.9)):
        for dx, dy, r in ((0, 0, 8), (-9, 3, 6), (10, 2, 7), (4, -4, 6)):
            _disc(a, cx + dx * s, cy + dy * s, r * s, CLD)
        for x in range(int(cx - 16 * s), int(cx + 18 * s)):
            for y in range(cy + 2, cy + 12):
                if a[y, x % CW] == CLD and (y + 1 >= 70 or a[y + 1, x % CW] == T or y > cy + 5):
                    a[y, x % CW] = GLH
    return a


@lru_cache(None)
def far_layer():
    a = np.full((H, FWD), T, np.uint8)
    rng = np.random.default_rng(3)
    x = 0
    while x < FWD:
        w = int(rng.integers(16, 32)); top = int(rng.integers(66, 112))
        R(a, x, top, min(FWD - 1, x + w - 2), SIDEWALK, FAR)
        R(a, x + w - 4, top + 2, min(FWD - 1, x + w - 2), SIDEWALK, FARS)
        if rng.random() < 0.6:
            for yy in range(top + 6, SIDEWALK - 6, 9):
                for xx in range(x + 3, x + w - 6, 6):
                    R(a, xx, yy, xx + 2, yy + 3, FARS)
        if rng.random() < 0.3:                       # antenna
            R(a, x + w // 2, top - 6, x + w // 2, top - 1, FARS)
        x += w
    return a


def _facade(a, x, w, top, kind, rng):
    body, shade = {'brick': (BRK, BRKS), 'cream': (CRM, CRMS), 'teal': (TEAL, GLS)}[kind]
    x1 = min(NW - 1, x + w - 1)
    R(a, x, top, x1, SIDEWALK - 1, body)
    R(a, x1 - 2, top + 3, x1, SIDEWALK - 1, shade)
    R(a, x, top, x1, top + 2, CRMS if kind != 'cream' else BRKS)    # cornice
    R(a, x - 1, top + 2, x1 + 1, top + 2, K)
    for yy in range(top + 8, 116, 15):                              # upper windows
        for xx in range(x + 4, x1 - 8, 12):
            R(a, xx, yy, xx + 6, yy + 8, GLS)
            P(a, xx + 1, yy + 1, GLH); P(a, xx + 2, yy + 1, GLH); P(a, xx + 1, yy + 2, GLH)
            R(a, xx - 1, yy + 9, xx + 7, yy + 9, CRMS if kind == 'cream' else CRM)
    # shopfront
    R(a, x + 3, 128, x1 - 4, SIDEWALK - 1, GLS)
    R(a, x + 3, 128, x1 - 4, 128, K)
    R(a, x + w // 2 - 3, 132, x + w // 2 + 2, SIDEWALK - 1, ASPD)    # door
    for i in range(5):
        P(a, x + 6 + i, 140 - i * 2, GLH)
    if kind != 'brick':                                              # striped awning
        for xx in range(x + 1, x1):
            c = RED if (xx // 3) % 2 else WH
            R(a, xx, 120, xx, 126 + ((xx // 3) % 2), c)
        R(a, x + 1, 119, x1 - 1, 119, K)
    else:
        R(a, x + 6, 121, x1 - 8, 125, K); R(a, x + 7, 122, x1 - 9, 124, CRM)   # blank sign board


@lru_cache(None)
def near_layer():
    a = np.full((H, NW), T, np.uint8)
    rng = np.random.default_rng(21)
    kinds = ['brick', 'cream', 'teal', 'brick', 'cream', 'brick', 'teal', 'cream']
    x, i = 0, 0
    while x < NW - 30:
        w = int(rng.integers(40, 58)) if NW - x - 58 > 40 else NW - x
        _facade(a, x, w, int(rng.integers(64, 92)), kinds[i % len(kinds)], rng)
        x += w; i += 1
    for tx in (70, 205, 330):                                        # street trees
        R(a, tx, 122, tx + 2, SIDEWALK - 1, BRKS)
        for dx, dy, r in ((0, 0, 11), (-8, 6, 8), (9, 5, 8)):
            _disc(a, tx + 1 + dx, 110 + dy, r, GRN)
        for y in range(96, 124):
            for xx in range(tx - 18, tx + 20):
                if a[y, xx % NW] == GRN and ((xx - tx) + (y - 110) > 9 or y > 117):
                    a[y, xx % NW] = GRNS
    for lx in (138, 280, 400):                                       # lamp posts
        R(a, lx, 98, lx, SIDEWALK - 1, GY); R(a, lx - 2, 96, lx + 3, 97, K); R(a, lx - 1, 98, lx + 2, 98, CRM)
    R(a, 0, SIDEWALK, NW - 1, 157, SIDE)                             # sidewalk
    for xx in range(0, NW, 16):
        R(a, xx, SIDEWALK + 1, xx, 157, CRMS)
    return outline(a)


@lru_cache(None)
def traffic_light(green):
    s = np.full((64, 7), T, np.uint8)
    R(s, 3, 14, 3, 63, GY)
    R(s, 0, 0, 6, 15, K)
    R(s, 2, 2, 4, 4, RED if not green else R1)
    R(s, 2, 6, 4, 8, R1)
    R(s, 2, 10, 4, 12, GRN if green else R1)
    if not green: P(s, 2, 2, WH)
    else: P(s, 2, 10, WH)
    return outline(s)


# pedestrians: world x on the near layer, walking speed (px/s), colours
PEOPLE = [(150, 9, RED, SK, K, False), (95, -7, TEAL, SS, BRK, True), (40, 11, CRM, SK, BRKS, False),
          (128, -10, GRN, SS, K, True)]
LIGHT_WX = 178                  # traffic light sits ahead of the stopped car


def drive_dist(t):
    v0 = 88 / 1.05              # stops at exactly 88 px: wheel angle returns to 0 (bar on top)
    if t < 0.8: return v0 * t
    if t < 1.3:
        u = t - 0.8
        return v0 * 0.8 + v0 * u - v0 * u * u
    if t < 11.9: return 88.0
    u = t - 11.9
    return 88.0 + 60 * u * u


def street(t, k):
    d = drive_dist(t)
    cv = np.full((H, W), SKY1, np.uint8)
    for x in range(W):                                # sky: two tones, staircase boundary
        R(cv, x, 0, x, 30 + (x // 7) % 3, SKY2)
    for layer, f, wrap, y0 in ((clouds(), F_CLOUD, CW, 0), (far_layer(), F_FAR, FWD, 0), (near_layer(), F_NEAR, NW, 0)):
        off = int(d * f + (t * 3 if layer.shape[0] == 70 else 0))
        idx = (np.arange(W) + off) % wrap
        sub = layer[:, idx]
        m = sub != T
        cv[y0:y0 + layer.shape[0]][m] = sub[m]
    near_off = int(d * F_NEAR)
    for i, (wx, sp, c, sk, hc, flip) in enumerate(PEOPLE):
        x = int(wx + sp * t) - near_off
        fr = (k + i) % 2
        blit(cv, person(c, sk, hc, fr, flip), x, SIDEWALK - 10)
    blit(cv, traffic_light(t >= 11.8), LIGHT_WX - near_off, 94)
    for i, (bx, by, sp) in enumerate(((20, 44, 16), (34, 50, 16), (90, 30, -12))):
        x = int((bx + sp * t) % 170) - 20
        blit(cv, BIRD[(k + i) % 2], x, by + (k + i) % 2)
    # road
    R(cv, 0, 158, W - 1, 158, GY); R(cv, 0, 159, W - 1, 159, ASPD)
    R(cv, 0, 160, W - 1, 205, ASP)
    R(cv, 0, 160, W - 1, 162, ASPD)
    off = int(d * F_ROAD)
    for x in range(-40, W + 40, 32):
        xx = x - off % 32
        R(cv, xx, 201, xx + 11, 202, WH)
    R(cv, CAR_X + 6, GROUND - 1, CAR_X + 110, GROUND + 1, ASPD)       # car shadow
    # front sidewalk (fastest layer)
    R(cv, 0, 206, W - 1, 206, GY); R(cv, 0, 207, W - 1, H - 1, SIDE)
    R(cv, 0, 207, W - 1, 208, CRMS)
    off = int(d * F_FRONT)
    for x in range(-60, W + 60, 28):
        R(cv, x - off % 28, 209, x - off % 28, H - 1, CRMS)
    R(cv, 0, 224, W - 1, 224, CRMS)                  # paving course line
    for px in (-30, 110, 250):                       # planters with shrubs (fast parallax)
        x = px - int(d * F_FRONT)
        R(cv, x, 226, x + 14, 233, BRKS); R(cv, x, 226, x + 14, 226, BRK)
        for dx, r in ((3, 4), (8, 5), (12, 3)):
            for yy in range(223 - r, 227):
                for xx in range(x + dx - r, x + dx + r + 1):
                    if (xx - x - dx) ** 2 + (yy - 223) ** 2 <= r * r:
                        P(cv, xx, yy, GRNS if yy > 223 or xx > x + dx + 1 else GRN)
        R(cv, x + 1, 234, x + 14, 234, ASPD)
    wx = int(150 - 13 * t - d * F_FRONT)             # dog walker on the near pavement
    fr = k % 2
    blit(cv, person(BRK, SK, K, fr, True), wx, 214)
    dog = _spr(['k  ', 'kbbbbb ', ' bbbbbt', ' b  b  ' if fr else '  bb   '], {'b': BRKS, 'k': K, 't': BRKS})
    blit(cv, outline(pad(dog)), wx - 12, 226)
    R(cv, wx - 5, 223 + fr, wx, 223 + fr, K)          # lead
    hx = 60 - int(d * F_FRONT)                       # hydrant
    hyd = outline(pad(_spr([' gg ', 'rrrr', 'grrg', ' rr ', ' rr ', ' rr ', 'rrrr'], {'r': RED, 'g': GY})))
    blit(cv, hyd, hx, 214)
    return cv


def car_layer(cv, t, k, expr, pose, lit=False):
    d = drive_dist(t)
    moving = 0.0 < t < 1.3 or t > 11.9
    bob = 1 if moving and k % 2 else 0
    blit(cv, car_sprite(expr, pose, k), CAR_X, CAR_Y + bob)
    ang = int(round(d / (2 * math.pi * 14) * 16)) % 16
    for i, wc in enumerate(WHEELS):
        spr = tyre(WHEEL_N, lit and i == 1) if ang == 0 else tyre_rot(WHEEL_N, ang)
        blit(cv, spr, CAR_X + wc - 14 - 1, CAR_Y + WHEEL_CY - 14 - 1)
    return cv


FRONT_WHEEL = (CAR_X + WHEELS[1], CAR_Y + WHEEL_CY)


def hud_brackets(cv, x0, y0, x1, y1, c=CYAN, n=5):
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        R(cv, min(x, x + sx * n), y, max(x, x + sx * n), y, c)
        R(cv, x, min(y, y + sy * n), x, max(y, y + sy * n), c)

# ------------------------------------------------------------------ timeline / stepping
HOLDS = [3, 2, 4, 3, 3, 2, 4, 3, 2]
SYNC = [0, 45, 90, 104, 110, 180, 239, 270, 330, 360]   # frames that must start a new drawing


def key_frames():
    keys, f, i = [], 0, 0
    sync = sorted(SYNC)
    while f < NF:
        keys.append(f)
        nxt = f + HOLDS[i % len(HOLDS)]
        i += 1
        later = [s for s in sync if f < s < nxt]
        f = later[0] if later else nxt
    return keys


KEYS = key_frames()
KEY_OF = np.zeros(NF, int)
for a, b in zip(KEYS, KEYS[1:] + [NF]):
    KEY_OF[a:b] = a
KEY_IDX = {k: i for i, k in enumerate(KEYS)}

TIMING = json.load(open(HERE / 'build' / 'timing.json')) if (HERE / 'build' / 'timing.json').exists() else None


def mouth(f):
    """talk/smile from the real VO envelope over this hold."""
    if TIMING is None:
        return 'smile'
    rms = TIMING['rms30']
    k = KEY_OF[f]
    nxt = KEYS[KEY_IDX[k] + 1] if KEY_IDX[k] + 1 < len(KEYS) else NF
    v = max(rms[k:nxt] or [0])
    if v > 0.18 * max(rms):
        return 'talk' if KEY_IDX[k] % 2 == 0 else 'smile'
    t = k / FPS
    if 2.15 <= t < 2.3 or 10.3 <= t < 10.45:
        return 'blink'
    return 'smile'

def tread_closeup(t, k):
    cv = np.full((H, W), B0, np.uint8)
    R(cv, 0, 0, W - 1, 6, K)
    top, floor = 78, 146
    grooves = [(14, 23), (60, 74), (111, 120)]
    rng = np.random.default_rng(5)
    edges = [-1] + [g for gg in grooves for g in gg] + [W]
    blocks = [(edges[i] + 1, edges[i + 1] - 1) for i in range(0, len(edges), 2)]
    for bi, (x0, x1) in enumerate(blocks):
        R(cv, x0, top, x1, floor, R1)
        # ragged top edge: 0-2 px steps every 3-5 px
        x = x0
        while x <= x1:
            w = int(rng.integers(3, 6)); d = int(rng.integers(0, 3))
            R(cv, x, top, min(x1, x + w - 1), top + d - 1, B0) if d else None
            R(cv, x, top + d, min(x1, x + w - 1), top + d + 2, R2)
            x += w
        R(cv, x0, top, x0, top + 1, B0); R(cv, x1, top, x1, top + 2, B0)   # chipped corners
        R(cv, x1 - 2, top + 4, x1, floor, R0)                                 # shadow side
        R(cv, x0, top + 4, x0, floor - 6, R2)                                 # lit side
        for yy in range(top + 6, floor, 2):                                   # texture in shadow only
            if h01(bi, yy, 9) < 0.35:
                P(cv, x1 - 1 - (yy // 2) % 2, yy, K)
        cx = (x0 + x1) // 2                                                   # zig-zag sipe
        if x1 - x0 > 12:
            for i, yy in enumerate(range(top + 10, top + 46)):
                P(cv, cx + (1 if (i // 3) % 2 else 0), yy, R0)
        R(cv, x0 + 2, floor - 5, x1 - 3, floor - 4, R0)
    for gx0, gx1 in grooves:
        R(cv, gx0, top + 4, gx1, floor, R0)
        R(cv, gx0, top + 4, gx0, floor, K)
        for yy in range(top + 8, floor, 7):
            if h01(gx0, yy, 2) < 0.5:
                P(cv, gx1, yy, K)
    # the bar, bottom of the middle groove (brightest, most saturated)
    gx0, gx1 = grooves[1]
    R(cv, gx0 + 1, floor - 14, gx1 - 1, floor, BO)
    R(cv, gx0 + 1, floor - 14, gx1 - 1, floor - 9, BY)
    R(cv, gx0 + 2, floor - 14, gx0 + 4, floor - 14, WH if (k % 4 == 0) else BY)  # hand-placed glint
    P(cv, gx0 + 1, floor - 14, R0); P(cv, gx1 - 1, floor - 14, R0)
    # sidewall below
    R(cv, 0, floor + 1, W - 1, 214, R1)
    R(cv, 0, floor + 1, W - 1, floor + 3, R0)
    R(cv, 0, floor + 9, W - 1, floor + 9, R2)
    R(cv, 0, 205, W - 1, 214, R0)
    for x in range(0, W, 3):
        if h01(x, 1, 4) < 0.5:
            P(cv, x, 206 + (x % 4), K)
    R(cv, 0, 215, W - 1, H - 1, B0)
    return cv, (gx0 + gx1) // 2, floor


def tread_panel(cv, x0, y0, w, depth, worn_frac, label, flush_flash, k):
    """Cross-section: two blocks either side of a groove with the bar at the bottom."""
    floor = y0 + 96
    bar_h = 9
    gx0, gx1 = x0 + w // 2 - 7, x0 + w // 2 + 6
    R(cv, x0, y0, x0 + w - 1, floor + 8, B0)
    top = floor - depth
    rng = np.random.default_rng(x0)
    rough = 2 if worn_frac < 0.6 else (1 if worn_frac < 0.95 else 0)
    for bx0, bx1 in ((x0 + 3, gx0 - 1), (gx1 + 1, x0 + w - 4)):
        R(cv, bx0, top, bx1, floor, R1)
        x = bx0
        while x <= bx1:
            ww = int(rng.integers(3, 6)); d = int(rng.integers(0, rough + 1))
            if d:
                R(cv, x, top, min(bx1, x + ww - 1), top + d - 1, B0)
            R(cv, x, top + d, min(bx1, x + ww - 1), top + d + 1, R2)
            x += ww
        R(cv, bx1 - 1, top + 3, bx1, floor, R0)
        R(cv, bx0, top + 3, bx0, floor, R2)
        for yy in range(top + 4, floor, 3):
            if h01(bx0, yy, 7) < 0.4:
                P(cv, bx1 - 1, yy, K)
    R(cv, gx0, min(top + 2, floor - bar_h), gx1, floor, R0)
    R(cv, gx0, min(top + 2, floor - bar_h), gx0, floor, K)
    bar_c = BY if not flush_flash or k % 2 == 0 else BO
    R(cv, gx0 + 1, floor - bar_h + 1, gx1 - 1, floor, BO)
    R(cv, gx0 + 1, floor - bar_h + 1, gx1 - 1, floor - bar_h + 3, bar_c)
    R(cv, x0, floor + 1, x0 + w - 1, floor + 8, R1)
    R(cv, x0, floor + 1, x0 + w - 1, floor + 2, R0)
    return floor - bar_h + 1


def icon_twi(cv, x, y, k):
    R(cv, x, y, x + 21, y + 21, R1)
    R(cv, x, y, x + 21, y + 2, R2)
    R(cv, x + 19, y + 3, x + 21, y + 21, R0)
    for i in range(5):
        R(cv, x + 10 - i, y + 7 + i, x + 11 + i, y + 7 + i, BY)
    for a in range(0, 360, 20):                 # magnifier ring
        P(cv, int(round(x + 11 + 8 * math.cos(math.radians(a)))), int(round(y + 10 + 8 * math.sin(math.radians(a)))), GY)
    line(cv, (x + 17, y + 16), (x + 21, y + 20), WH, 2)


def icon_groove(cv, x, y, k):
    R(cv, x, y + 2, x + 8, y + 21, R1); R(cv, x, y + 2, x + 8, y + 3, R2); R(cv, x + 7, y + 4, x + 8, y + 21, R0)
    R(cv, x + 13, y + 3, x + 21, y + 21, R1); R(cv, x + 13, y + 3, x + 21, y + 4, R2); R(cv, x + 20, y + 5, x + 21, y + 21, R0)
    R(cv, x + 9, y + 4, x + 12, y + 21, R0)
    R(cv, x + 9, y + 16, x + 12, y + 21, BO); R(cv, x + 9, y + 16, x + 12, y + 17, BY)


def icon_clock(cv, x, y, k):
    cx, cy = x + 10, y + 12
    for yy in range(-9, 10):
        for xx in range(-9, 10):
            d = xx * xx + yy * yy
            if d <= 81:
                P(cv, cx + xx, cy + yy, K if d > 64 else (GY if xx + yy > 6 else WH))
    R(cv, cx - 2, y, cx + 2, y + 1, GY)
    line(cv, (cx, cy), (cx, cy - 6), K)
    hand = [(cx + 5, cy - 3), (cx + 6, cy), (cx + 5, cy + 3)][k % 3]
    line(cv, (cx, cy), hand, BO)


# ------------------------------------------------------------------ scenes
def scene_hook(f, text=True):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = street(t, k)
    lit = t >= 1.5
    pose = 'point' if t >= 1.35 else None
    car_layer(cv, t, k, mouth(f), pose, lit)
    bx, by = FRONT_WHEEL[0], FRONT_WHEEL[1] - 13
    if lit and text:
        for i, (sx, sy) in enumerate(((-5, -2), (5, -3), (-7, 2), (7, 1))):
            if (k + i) % 3 != 0:
                P(cv, bx + sx, by + sy, BY)
        if t >= 1.7:
            blit(cv, ARROW_DN, bx - 4, by - 12 + (k % 2))
    if text:
        box = (14, 10, 120, 53)
        if t < 0.07:
            grow_plate(cv, box, 0.5)
        else:
            text_box(cv, 'hook_headline', ['HIDDEN', 'BAR'], box, size=16)
    if 1.5 <= t < 1.6:                     # whole-pixel camera nudge on the ping
        cv = np.roll(cv, 1, axis=1)
    elif 1.6 <= t < 1.7:
        cv = np.roll(cv, -1, axis=0)
    return cv


def scene_reveal(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    if t < 3.45:                            # analysis: scan beam sweeps the car, HUD locks onto the tyre
        cv = street(t, k)
        car_layer(cv, t, k, mouth(f), None, True)
        sx = 6 + int((t - 3.0) / 0.45 * 124)
        R(cv, sx, 140, sx, 200, CYAN)
        R(cv, sx - 2, 140, sx - 2, 200, GLH)
        steps = [(4, 136, 130, 204), (60, 150, 128, 202), (84, 162, 122, 202)]
        b = steps[min(2, int((t - 3.0) / 0.15))]
        hud_brackets(cv, *b)
        text_box(cv, 'reveal_scan', ['SCANNING'], (26, 10, 108, 26), border=CYAN)
        return cv
    if t < 3.65:                            # stepped punch-in x2 then x4 (integer nearest)
        src = street(t, k); car_layer(src, t, k, 'smile', None, True)
        z = 2 if t < 3.55 else 4
        cw, ch = -(-W // z), H // z
        bx, by = FRONT_WHEEL
        x0 = min(max(0, bx - cw // 2), W - cw); y0 = min(max(0, by - ch // 2), H - ch)
        crop = src[y0:y0 + ch, x0:x0 + cw]
        cv = np.repeat(np.repeat(crop, z, 0), z, 1)[:H, :W].copy()
        hud_brackets(cv, 10, 40, 124, 200, n=8)
        return cv
    cv, gx, floor = tread_closeup(t, k)
    settle = 3 if t < 3.72 else (1 if t < 3.8 else 0)
    blink_on = t >= 4.4 and (k % 3 != 2)
    tri_c = BY if blink_on else GY
    for i in range(5):
        R(cv, gx - i, 160 + i, gx + i, 160 + i, tri_c)
    m = text_mask('TWI', 8)
    ys, xs = np.nonzero(m)
    w = int(m.any(0).nonzero()[0].max() + 1)
    cv[168 + ys + 1, gx - w // 2 + xs + 1] = R0
    cv[168 + ys, gx - w // 2 + xs] = BY if blink_on else R2
    TEXT_REPORT['reveal_twi_mark'] = dict(lines=['TWI'], plate='sidewall (embossed mark, not a caption)',
                                          widths=[w], inner_w=W, fits=True,
                                          contrast=round(float(contrast(BY, R1)), 2))
    if t >= 3.85:
        a = 0 if k % 2 else 1
        line(cv, (gx, 52), (gx, floor - 22 - a), WH, 2)
        for i in range(4):
            R(cv, gx - i, floor - 24 - a + i, gx + 1 + i, floor - 24 - a + i, WH)
    hud_brackets(cv, 3, 50, 131, 222, n=8)
    box = (8, 14, 126, 46)
    if t < 3.8:
        grow_plate(cv, box, 0.55)
    else:
        text_box(cv, 'reveal_label', ['TREAD WEAR', 'INDICATOR'], box)
    if settle:
        cv = np.vstack([cv[settle:], np.full((settle, W), B0, np.uint8)])
    return cv


def scene_progress(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = street(t, k)
    car_layer(cv, t, k, mouth(f), None)
    R(cv, 2, 54, 132, 178, CYAN)            # HUD analysis panel over the live street
    R(cv, 3, 55, 131, 177, K)
    full = 72
    steps = [(6.0, 72), (6.35, 63), (6.6, 52), (6.9, 43), (7.15, 35), (7.45, 26), (7.7, 17), (7.97, 9)]
    depth = [d for ts, d in steps if t >= ts][-1]
    worn_frac = (full - depth) / (full - 9)
    flush = t >= 7.97
    tread_panel(cv, 5, 72, 60, full, 0.0, 'NEW', False, k)
    bar_y = tread_panel(cv, 70, 72, 60, depth, worn_frac, 'WORN', flush and t < 8.4, k)
    if flush:
        for x in range(71, 129, 3):
            R(cv, x, bar_y - 2, x + 1, bar_y - 2, WH)
    text_box(cv, 'prog_new', ['NEW'], (14, 58, 54, 72))
    text_box(cv, 'prog_worn', ['WORN'], (80, 58, 120, 72), fg=BY if flush else WH)
    box = (4, 186, 130, 228)
    if flush and t < 8.05:
        grow_plate(cv, box, 0.6)
    elif flush:
        text_box(cv, 'prog_caption', ['FLUSH = AT THE', 'LEGAL MINIMUM', 'WHERE YOU LIVE'], box, lead=4)
    if 7.97 <= t < 8.04:
        cv = np.roll(cv, 1, axis=0)
    return cv


def scene_payoff(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = street(t, k)
    car_layer(cv, t, k, mouth(f), 'point' if t < 10.3 else None, True)
    rows = [(9.0, 'pay_find', ['FIND TWI'], icon_twi),
            (9.37, 'pay_look', ['LOOK IN', 'THE GROOVE'], icon_groove),
            (9.8, 'pay_time', ['10 SECONDS'], icon_clock)]
    for i, (t0, name, lines, icon) in enumerate(rows):
        y = 12 + i * 38
        if t < t0:
            continue
        if t < t0 + 0.1:
            grow_plate(cv, (4, y, 130, y + 31), 0.5)
            continue
        R(cv, 4, y, 130, y + 31, B2)
        R(cv, 5, y + 1, 129, y + 30, K)
        R(cv, 6, y + 4, 30, y + 27, B1)
        icon(cv, 7, y + 5, k)
        text_box(cv, name, lines, (32, y + 2, 128, y + 29), border=K)
    return cv


def scene_end(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = street(t, k)
    pose = ('wave1' if k % 2 else 'wave2') if t >= 11.5 else None
    car_layer(cv, t, k, mouth(f), pose)
    text_box(cv, 'end_question', ['HAVE YOU EVER', 'LOOKED FOR', 'YOURS?'], (8, 8, 126, 52))
    yes, no = (10, 60, 62, 84), (72, 60, 124, 84)
    if t < 11.07:
        grow_plate(cv, yes, 0.5, border=TL); grow_plate(cv, no, 0.5, border=MG)
    else:
        picked = t >= 11.75
        text_box(cv, 'poll_yes', ['YES'], yes, border=TL, bg=K if not picked else B0)
        text_box(cv, 'poll_no', ['NO'], no, border=MG)
        for (x0, y0, x1, y1), c in ((yes, TL), (no, MG)):
            R(cv, x0 + 4, y0 + 8, x0 + 9, y0 + 13, c); R(cv, x0 + 5, y0 + 9, x0 + 8, y0 + 12, K)
        if picked:
            R(cv, yes[0] + 5, yes[1] + 9, yes[0] + 8, yes[1] + 12, BY)
        if t >= 11.3:
            cx = [(110, 112), (80, 98), (56, 86), (40, 78)][min(3, int((t - 11.3) / 0.12))]
            blit(cv, CURSOR, cx[0] - 10, cx[1] - 4)
    if t >= 12.0:                           # NEXT EPISODE card, final 1.0 s only (slides in from the right)
        x = [96, 40, 0][min(2, int((t - 12.0) / 0.07))]
        y = 92
        R(cv, 6 + x, y, 128 + x, y + 50, B2)
        R(cv, 7 + x, y + 1, 127 + x, y + 49, K)
        R(cv, 7 + x, y + 1, 127 + x, y + 3, MG)
        if x == 0:
            text_box(cv, 'next_title', ['NEXT EPISODE'], (10, y + 7, 124, y + 22), border=K)
            text_box(cv, 'next_follow', ['FOLLOW'], (40, y + 27, 94, y + 44), border=TL, fg=WH)
    return cv


def frame_idx(f):
    t = KEY_OF[f] / FPS
    k = KEY_OF[f]
    if t < 3.0:
        return scene_hook(k)
    if t < 6.0:
        return scene_reveal(k)
    if t < 9.0:
        return scene_progress(k)
    if t < 11.0:
        return scene_payoff(k)
    return scene_end(k)


@lru_cache(maxsize=4)
def _key_rgb(k):
    return PAL[frame_idx(k)]


def frame_rgb(f):
    return _key_rgb(KEY_OF[f])


def all_native():
    return [frame_rgb(f) for f in range(NF)]


def encode(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    master, final = out / 'master_silent_yuv444.mp4', out / 'final.mp4'
    color = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']
    vf = f'scale={W * S}:{H * S}:flags=neighbor:out_color_matrix=bt709:out_range=tv'
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-vf', vf, '-c:v', 'libx264', '-preset', 'slow', '-qp', '0',
                           '-pix_fmt', 'yuv444p', *color, '-r', str(FPS), '-movflags', '+faststart', str(master)],
                          stdin=subprocess.PIPE)
    for f in range(NF):
        ff.stdin.write(frame_rgb(f).tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit('master encode failed')
    mix = HERE / 'build' / 'mix.wav'
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', str(master)]
    cmd += ['-i', str(mix)] if mix.exists() else ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono']
    cmd += ['-map', '0:v', '-map', '1:a', '-vf', 'scale=flags=neighbor+full_chroma_inp,format=yuv420p',
            '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', '13', *color, '-r', str(FPS),
            '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{DUR:.3f}', '-movflags', '+faststart', str(final)]
    if subprocess.run(cmd).returncode:
        raise SystemExit('final encode failed')
    json.dump(TEXT_REPORT, open(out / 'text_report.json', 'w'), indent=1)
    print('wrote', master, final, 'with audio' if mix.exists() else 'SILENT (no mix.wav)')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        Path(sys.argv[2]).mkdir(parents=True, exist_ok=True)
        for ts in sys.argv[3:]:
            f = min(NF - 1, int(round(float(ts) * FPS)))
            Image.fromarray(frame_rgb(f)).resize((W * S, H * S), Image.NEAREST).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        encode(sys.argv[2])
