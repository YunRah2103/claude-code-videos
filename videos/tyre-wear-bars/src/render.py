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
    small = n < 40
    t0 = Rr - 2.6 if small else 0.81 * Rr
    gin = Rr - 1.2 if small else t0 + 1.2          # groove depth
    if small:
        in_blk = in_blk | (r < gin)
    tread = (r >= t0) & (r <= rout) & in_blk
    spr[tread] = R1
    spr[tread & (r >= rout - 1.3) & (nrm > 0.25)] = R2
    spr[tread & (nrm < -0.45)] = R0
    spr[(r >= t0) & (r < gin) & ~in_blk] = R0
    g0 = ((phase < 0.27) | (phase > nb - 0.27)) & (r >= gin) & (r < (Rr + 0.2 if small else t0 + 2.6))
    spr[g0] = R1
    if lit:
        spr[g0] = BO
        spr[g0 & (r >= t0 + 1.9)] = BY
    rim = 0.66 if small else 0.56
    side = (r >= rim * Rr) & (r < t0)
    spr[side] = R1
    spr[side & (r >= 0.72 * Rr) & (nrm > 0.35)] = R2
    shadow = side & (nrm < -0.3)
    spr[shadow] = R0
    spr[shadow & (np.vectorize(h01)(xx, yy, 3) < 0.07)] = K       # texture only in shadow
    if n >= 40:
        tri = (dy < 0) & (r >= 0.64 * Rr) & (r < 0.77 * Rr) & (np.abs(dx) <= (0.77 * Rr - r) * 0.75)
        spr[tri] = GY
    lip = (r >= (rim - 0.07) * Rr) & (r < rim * Rr + 0.6)
    spr[lip] = GY
    spr[lip & (nrm > 0.2)] = WH
    spr[lip & (nrm < -0.3)] = FARS
    dish = r < (rim - 0.07) * Rr
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
def tyre_rot(n, i, lit=False):
    """16 pre-baked angles (22.5 degree steps), RotSprite-style; i>0 turns clockwise."""
    return outline(pad(rotsprite(tyre_core(n, lit), -i * 22.5))) if i % 16 else tyre(n, lit)

# ------------------------------------------------------------------ small sprites
def _spr(rows, cmap):
    a = np.full((len(rows), max(len(r) for r in rows)), T, np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in cmap:
                a[y, x] = cmap[ch]
    return a


ARROW_DN = outline(pad(_spr(['  ww  ', '  ww  ', '  ww  ', 'wwwwww', ' wwww ', '  ww  '], {'w': WH})))
ARROW_L = outline(pad(_spr(['   w    ', '  ww    ', ' wwwwwww', 'wwwwwwww', ' wwwwwww', '  ww    ', '   w    '], {'w': WH})))
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
CAR_X, CAR_Y = 8, 146           # sprite origin on screen (8 px headroom for the waving arm)
CW_ = 120
WHEEL_N = 26
WHEELS = (24, 95)               # wheel centres, car-local x
WHEEL_CY = 8 + 30               # car-local y (sprite coords)
GROUND = CAR_Y + WHEEL_CY + 13
STOP_STEP = 5                   # front wheel stops turned 5 x 22.5 deg: the bar faces front-low, visible
_TOP = [(0, 22), (2, 19), (5, 15), (9, 11), (13, 8), (20, 5.4), (30, 4), (44, 3.4), (58, 3.6), (68, 4.6),
        (74, 6), (82, 10), (90, 15.5), (94, 17), (104, 18), (112, 19), (116, 21), (119, 24)]


def car_top(x):
    return int(round(np.interp(x, *zip(*_TOP))))


def _belt(x):
    return 19 if x < 60 else 18


@lru_cache(None)
def car_body():
    o = 8
    s = np.full((o + 38, CW_), T, np.uint8)
    arch = lambda x, y, rr: any((x - wc) ** 2 + (y - 30) ** 2 < rr * rr for wc in WHEELS)
    for x in range(CW_):
        top = car_top(x)
        bot = 33 if x < 6 or x > 113 else 35
        for y in range(top, bot + 1):
            if arch(x, y, 15.5):
                continue
            b = _belt(x)
            if y <= b - 1 and 9 <= x <= 91:
                c = GLS
            elif y <= b + 1:
                c = CARH
            elif y <= 26:
                c = CAR
            elif y == 27:
                c = CAR if (x % 2) else CARS                   # hand dither into the lower panel
            else:
                c = CARS
            s[y + o, x] = c
        if top <= bot:
            s[top + o, x] = CARH                               # roof / pillar highlight
            if top + 1 <= bot and s[top + o + 1, x] == GLS:
                s[top + o + 1, x] = CAR                        # window frame
    # pillars, trim, glass shading
    for x in range(9, 92):
        t0 = car_top(x) + 2
        b = _belt(x)
        if s[t0 + o, x] == GLS:
            s[t0 + o, x] = ASPD                                # dark interior under the roof
        if s[b + o, x] in (CARH, CAR):
            s[b + o, x] = GY                                   # chrome beltline
    for x0, x1 in ((9, 13), (29, 31), (56, 59)):               # C-, rear quarter, B-pillars
        for x in range(x0, x1 + 1):
            for y in range(car_top(x) + 1, _belt(x)):
                s[y + o, x] = CARS if x == x1 else CAR
    for x in range(74, 92):                                    # A-pillar follows the windscreen rake
        y = car_top(x) + 1
        s[y + o, x] = CAR; s[y + o + 1, x] = CAR
    for x0 in (16, 35, 62):                                    # sky reflection bands on glass
        for i in range(8):
            for w in (0, 1, 3):
                x, y = x0 + i + w, o + 15 - i * 2
                if 0 <= y < s.shape[0] and s[y, x] == GLS:
                    s[y, x] = GLH
    # shoulder reflection streak, broken by hand
    for x in range(8, 112):
        if s[o + 22, x] == CAR and (x // 9) % 3 != 2 and x % 9 != 0:
            s[o + 22, x] = CARH
    for x in range(14, 106, 2):
        if s[o + 23, x] == CAR and (x // 9) % 3 == 0:
            s[o + 23, x] = WH
    # door seams, handles, fuel cap, mirror
    for x, y0, y1 in ((31, 17, 33), (59, 17, 34), (91, 16, 30)):
        for y in range(y0, y1 + 1):
            if s[y + o, x] not in (T, GLS):
                s[y + o, x] = CARS
    for hx in (46, 80):
        R(s, hx, o + 24, hx + 3, o + 24, GY); R(s, hx, o + 25, hx + 3, o + 25, CARS)
    R(s, 14, o + 21, 16, o + 23, CARS); P(s, 15, o + 22, CAR)
    R(s, 86, o + 12, 91, o + 15, CAR); R(s, 86, o + 12, 91, o + 12, CARH); R(s, 91, o + 13, 91, o + 15, CARS)
    # rear spoiler, tail light, rear bumper
    R(s, 9, o + 6, 17, o + 7, CAR); R(s, 8, o + 6, 12, o + 6, CARH)
    R(s, 0, o + 19, 4, o + 24, RED); R(s, 0, o + 23, 4, o + 24, BRKS); P(s, 1, o + 20, CRM)
    R(s, 0, o + 28, 7, o + 31, GY); R(s, 0, o + 31, 7, o + 31, FARS); R(s, 1, o + 32, 6, o + 33, ASPD)
    # headlight, grille, front bumper, badge
    for y, (a, b) in zip(range(19, 23), ((110, 116), (109, 117), (109, 117), (111, 116))):
        R(s, a, o + y, b, o + y, CRM)
    R(s, 113, o + 20, 115, o + 20, WH); R(s, 109, o + 22, 111, o + 22, CRMS)
    R(s, 111, o + 26, 119, o + 29, K)
    for x in range(112, 119, 2):
        R(s, x, o + 27, x, o + 28, GY)
    R(s, 108, o + 31, 119, o + 32, GY); R(s, 108, o + 33, 118, o + 33, ASPD)
    P(s, 116, o + 24, GY)
    # wheel arch flares (highlight on the upper lip, shadow below) + dark arch lining
    for x in range(CW_):
        for y in range(10, 36):
            for wc in WHEELS:
                d = math.hypot(x - wc, y - 30)
                if 15.5 <= d < 16.6 and s[y + o, x] not in (T,):
                    s[y + o, x] = CARH if y < 25 else CARS
                if 13.6 <= d < 15.5 and y <= 33:
                    s[y + o, x] = K
    # rocker panel
    R(s, 40, o + 33, 80, o + 34, ASPD); R(s, 40, o + 32, 80, o + 32, CARS)
    for x, y in pix._line((24, o + 3), (21, o - 1)):            # short antenna
        P(s, x, y, FARS)
    return s


def arm(s, pose, k):
    """Presenter's arm out of the driver window (sprite coords)."""
    if pose == 'point':                                         # down at the front tyre
        R(s, 80, 25, 82, 27, WH)
        for x, y in pix._line((82, 27), (92, 30)):
            R(s, x, y, x + 1, y + 1, SK)
        R(s, 91, 30, 93, 32, SK); R(s, 94, 32, 95, 32, SK); P(s, 92, 32, SS)
    elif pose in ('wave1', 'wave2'):
        R(s, 82, 21, 84, 23, WH)
        hx = 88 if pose == 'wave1' else 91
        for x, y in pix._line((84, 19), (hx, 4)):
            R(s, x, y, x + 1, y + 1, SK)
        R(s, hx - 1, 1, hx + 2, 4, SK); P(s, hx + 2, 1, T)


def car_sprite(expr, pose, k):
    s = car_body().copy()
    hd = head(expr)
    y0, y1, x0, x1 = 8 + 6, 8 + 19, 60, 86
    win = (s[y0:y1, x0:x1] == GLS) | (s[y0:y1, x0:x1] == GLH) | (s[y0:y1, x0:x1] == ASPD)
    sub = np.full((y1 - y0, x1 - x0), T, np.uint8)
    blit(sub, hd, 8, 1)
    m = win & (sub != T)
    s[y0:y1, x0:x1][m] = sub[m]
    if pose:
        arm(s, pose, k)
    return outline(s)

# ------------------------------------------------------------------ the street (parallax layers, textured)
NW, FWD, CW = 420, 300, 400
F_CLOUD, F_FAR, F_NEAR, F_ROAD, F_FRONT = 0.1, 0.3, 0.6, 1.0, 1.3
SIDEWALK = 150
HN = np.vectorize(h01)


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
        for dx, dy, r in ((0, 0, 8), (-9, 3, 6), (10, 2, 7), (4, -4, 6), (-15, 5, 4), (16, 5, 4)):
            _disc(a, cx + dx * s, cy + dy * s, r * s, CLD)
        for x in range(int(cx - 22 * s), int(cx + 24 * s)):
            for y in range(cy - 2, min(70, cy + 12)):
                xx = x % CW
                if a[y, xx] == CLD and (y > cy + 3 or (y > cy and h01(x, y, 8) < 0.35)):
                    a[y, xx] = GLH                             # ragged cool underside
    return a


@lru_cache(None)
def far_layer():
    a = np.full((H, FWD), T, np.uint8)
    rng = np.random.default_rng(3)
    x = 0
    while x < FWD:
        w = int(rng.integers(14, 30)); top = int(rng.integers(62, 110))
        x1 = min(FWD - 1, x + w - 2)
        R(a, x, top, x1, SIDEWALK, FAR)
        R(a, x1 - 2, top + 2, x1, SIDEWALK, FARS)
        R(a, x, top, x1, top, FARS)
        for yy in range(top + 5, SIDEWALK - 4, 6):
            for xx in range(x + 2, x1 - 3, 4):
                if h01(xx, yy, 5) < 0.7:
                    R(a, xx, yy, xx + 1, yy + 2, FARS if h01(xx, yy, 6) < 0.85 else GLH)
        if rng.random() < 0.35:
            R(a, x + w // 2, top - 7, x + w // 2, top - 1, FARS); P(a, x + w // 2 - 1, top - 5, FARS)
        if rng.random() < 0.3:
            R(a, x + 3, top - 4, x + 8, top - 1, FARS)
        x += w
    return a


def _window(a, xx, yy, kind, seed):
    R(a, xx - 1, yy - 1, xx + 7, yy + 9, CRM if kind != 'cream' else WH)   # frame
    R(a, xx, yy, xx + 6, yy + 8, GLS)
    R(a, xx, yy, xx + 6, yy + 1, ASPD)                                       # lintel shadow inside
    for i in range(4):
        P(a, xx + 1 + i, yy + 7 - i * 2, GLH); P(a, xx + 2 + i, yy + 7 - i * 2, GLH)
    R(a, xx + 3, yy, xx + 3, yy + 8, CRM if kind != 'cream' else WH)        # mullion
    R(a, xx, yy + 4, xx + 6, yy + 4, CRM if kind != 'cream' else WH)        # transom
    v = h01(xx, yy, seed)
    if v < 0.3:                                                              # curtains
        R(a, xx, yy, xx, yy + 8, RED); R(a, xx + 6, yy, xx + 6, yy + 8, RED)
    elif v < 0.45:
        R(a, xx, yy + 2, xx + 6, yy + 3, CRMS)                               # half-drawn blind
    R(a, xx - 2, yy + 10, xx + 8, yy + 10, CRMS if kind == 'cream' else CRM)  # sill
    R(a, xx - 1, yy + 11, xx + 7, yy + 11, K)
    if h01(xx, yy, seed + 1) < 0.3:                                          # flower box
        R(a, xx, yy + 9, xx + 6, yy + 10, BRKS)
        for i in range(0, 7, 2):
            P(a, xx + i, yy + 8, RED if (i // 2) % 2 else GRN)


def _facade(a, x, w, top, kind, rng):
    body, shade = {'brick': (BRK, BRKS), 'cream': (CRM, CRMS), 'teal': (TEAL, GLS)}[kind]
    x1 = min(NW - 1, x + w - 1)
    R(a, x, top, x1, SIDEWALK - 1, body)
    # surface texture
    for y in range(top + 3, 128):
        for xx in range(x, x1 + 1):
            if kind == 'brick':
                row = (y - top) // 3
                if (y - top) % 3 == 2 or (xx + (row % 2) * 3) % 6 == 0:
                    a[y, xx] = BRKS                                          # mortar coursing
                elif h01(xx // 6, row, 4) < 0.12:
                    a[y, xx] = CRMS if h01(xx // 6, row, 5) < 0.3 else BRKS  # odd bricks
            elif kind == 'cream':
                if (y - top) % 7 == 6 and h01(xx // 9, y, 7) < 0.8:
                    a[y, xx] = CRMS                                          # render joints
                elif h01(xx, y, 3) < 0.035:
                    a[y, xx] = CRMS                                          # weathering stains
            else:
                if (xx - x) % 7 == 0:
                    a[y, xx] = GLS                                           # cladding seams
                elif h01(xx, y, 2) < 0.03:
                    a[y, xx] = CYAN
    R(a, x1 - 2, top + 3, x1, SIDEWALK - 1, shade)                           # shadow side
    # cornice with dentils
    R(a, x, top, x1, top + 2, CRMS if kind != 'cream' else BRKS)
    for xx in range(x, x1 + 1, 2):
        P(a, xx, top + 2, K)
    R(a, x - 1, top - 1, x1 + 1, top - 1, CRM)
    # rooftop clutter
    r = h01(x, top, 9)
    if r < 0.35:
        R(a, x + 5, top - 7, x + 12, top - 2, GY); R(a, x + 6, top - 6, x + 11, top - 6, K)
        for xx in range(x + 6, x + 12, 2): R(a, xx, top - 5, xx, top - 3, FARS)
    elif r < 0.65:
        R(a, x1 - 10, top - 10, x1 - 6, top - 2, BRK); R(a, x1 - 11, top - 11, x1 - 5, top - 10, K)
        for y in range(top - 9, top - 2, 3): R(a, x1 - 10, y, x1 - 6, y, BRKS)
    else:
        R(a, x + 8, top - 3, x + 8, top - 1, K); _disc(a, x + 9, top - 6, 3, GY); P(a, x + 9, top - 6, FARS)
    for yy in range(top + 8, 112, 15):                                       # upper windows
        for xx in range(x + 5, x1 - 9, 12):
            _window(a, xx, yy, kind, x)
    # shopfront
    R(a, x + 1, 127, x1 - 1, 128, K)
    R(a, x + 3, 129, x1 - 4, SIDEWALK - 1, GLS)
    R(a, x + 3, 129, x1 - 4, 130, ASPD)
    for xx in range(x + 3, x1 - 4, 9):                                        # display frames
        R(a, xx, 129, xx, SIDEWALK - 1, K if kind == 'brick' else GY)
    for i in range(6):
        P(a, x + 7 + i, 145 - i * 2, GLH); P(a, x + 8 + i, 145 - i * 2, GLH)
    for xx in range(x + 6, x1 - 6, 5):                                        # goods on display
        if h01(xx, 1, x) < 0.5:
            R(a, xx, 142, xx + 2, 146, [RED, CRM, TEAL, BO if False else GRN][int(h01(xx, 2, x) * 4)])
    dx = x + w // 2 - 3
    R(a, dx, 133, dx + 5, SIDEWALK - 1, ASPD); R(a, dx, 133, dx + 5, 133, K)   # door
    R(a, dx + 1, 135, dx + 4, 140, GLS); P(a, dx + 4, 142, GY)
    if kind != 'brick':                                                       # striped awning
        for xx in range(x + 1, x1):
            c = RED if (xx // 3) % 2 else WH
            R(a, xx, 119, xx, 124 + ((xx // 3) % 2), c)
            if c == WH:
                P(a, xx, 119, CLD)
        R(a, x + 1, 118, x1 - 1, 118, K)
        R(a, x + 1, 120, x1 - 1, 120, BRKS if kind == 'cream' else GLS)
    else:
        R(a, x + 6, 120, x1 - 8, 125, K); R(a, x + 7, 121, x1 - 9, 124, CRM)   # sign board
        for xx in range(x + 9, x1 - 11, 3):
            R(a, xx, 122, xx + 1, 123, BRKS)                                  # pixel "lettering"
        R(a, x1 - 4, 112, x1 - 4, 115, K); R(a, x1 - 7, 115, x1 - 1, 119, RED)   # hanging sign


@lru_cache(None)
def near_layer():
    a = np.full((H, NW), T, np.uint8)
    rng = np.random.default_rng(21)
    kinds = ['brick', 'cream', 'teal', 'brick', 'cream', 'brick', 'teal', 'cream']
    x, i = 0, 0
    while x < NW - 30:
        w = int(rng.integers(40, 58)) if NW - x - 58 > 40 else NW - x
        _facade(a, x, w, int(rng.integers(64, 90)), kinds[i % len(kinds)], rng)
        x += w; i += 1
    for tx in (70, 205, 330):                                                 # leafy street trees
        R(a, tx, 120, tx + 2, SIDEWALK - 1, BRKS); P(a, tx, 128, K); P(a, tx + 2, 135, K)
        R(a, tx - 2, SIDEWALK - 1, tx + 4, SIDEWALK - 1, K)
        leaf = np.zeros((40, 44), bool)
        for dx, dy, r in ((0, 0, 11), (-9, 6, 8), (10, 5, 8), (-4, -7, 7), (6, -6, 7), (0, 10, 7)):
            yy, xx = np.mgrid[0:40, 0:44]
            leaf |= (xx - 22 - dx) ** 2 + (yy - 20 - dy) ** 2 <= r * r
        for yy, xx in zip(*np.nonzero(leaf)):
            gx, gy = tx + 1 + xx - 22, 108 + yy - 20
            edge = not (leaf[min(39, yy + 2), xx] and leaf[yy, min(43, xx + 2)])
            lit = (xx - 22) + (yy - 20) < -4
            n = h01(gx // 2, gy // 2, 11)
            c = GRNS if (not lit and (n < 0.75 or edge)) else (GRNS if n < 0.18 else GRN)
            if lit and n > 0.9:
                c = CYAN if False else GRN
            a[gy, gx % NW] = c
        for k_ in range(10):                                                  # hand-placed leaf clumps
            gx = tx + int((h01(k_, tx, 1) - 0.5) * 24); gy = 100 + int(h01(k_, tx, 2) * 14)
            R(a, gx, gy, gx + 1, gy, GRN); P(a, gx, gy + 1, GRNS)
    for lx in (138, 280, 400):                                                # lamp posts
        R(a, lx, 98, lx, SIDEWALK - 1, GY); R(a, lx + 1, 100, lx + 1, SIDEWALK - 1, FARS)
        R(a, lx - 2, 95, lx + 3, 97, K); R(a, lx - 1, 98, lx + 2, 98, CRM)
        R(a, lx - 1, SIDEWALK - 3, lx + 2, SIDEWALK - 1, K)
    # pavement tiles with joints, cracks and a drain
    R(a, 0, SIDEWALK, NW - 1, 157, SIDE)
    for xx in range(NW):
        for yy in range(SIDEWALK, 158):
            if (xx + (3 if yy > 153 else 0)) % 9 == 0 or yy == 153:
                a[yy, xx] = CRMS
            elif h01(xx, yy, 13) < 0.04:
                a[yy, xx] = CRMS
    return outline(a)


@lru_cache(None)
def road_strip():
    """Asphalt with grit, cracks, patches, worn lane paint and a manhole (wraps every 256 px)."""
    rw = 256
    a = np.full((46, rw), ASP, np.uint8)
    yy, xx = np.mgrid[0:46, 0:rw]
    n = HN(xx, yy, 17)
    a[n < 0.07] = ASPD
    a[(n > 0.985)] = SIDE
    a[0:3] = ASPD                                                             # gutter
    a[3, ::2] = ASPD
    R(a, 150, 8, 176, 13, ASPD); R(a, 151, 9, 175, 12, ASP)                   # tar patch
    for x, y in pix._line((30, 6), (44, 16)) + pix._line((44, 16), (52, 15)) + pix._line((200, 30), (214, 38)):
        P(a, x, y, ASPD)
    _disc(a, 92, 22, 5, ASPD); _disc(a, 92, 22, 4, FARS)                      # manhole
    for i in range(-3, 4, 2):
        R(a, 89, 22 + i, 95, 22 + i, ASPD)
    for x0 in range(0, rw, 32):                                               # lane dashes (worn)
        R(a, x0, 41, x0 + 11, 42, WH)
        for x in range(x0, x0 + 12):
            if h01(x, 41, 3) < 0.25: P(a, x, 41 + int(h01(x, 4, 3) * 2), CLD if False else SIDE)
    return a


@lru_cache(None)
def front_strip():
    fw = 280
    a = np.full((33, fw), SIDE, np.uint8)
    a[0] = GY; a[1:3] = CRMS
    for x in range(0, fw, 5):
        a[1, x] = K                                                           # kerb stone joints
    for x in range(fw):
        for y in range(3, 33):
            if (x + (7 if y > 17 else 0)) % 14 == 0 or y == 17:
                a[y, x] = CRMS
            elif h01(x, y, 23) < 0.05:
                a[y, x] = CRMS
    for x, y in pix._line((60, 6), (66, 12)) + pix._line((66, 12), (64, 16)):
        a[y, x] = ASPD                                                         # crack
    R(a, 180, 4, 190, 9, K)
    for x in range(181, 190, 2):
        R(a, x, 5, x, 8, FARS)                                                 # drain grate
    return a


@lru_cache(None)
def traffic_light(green):
    s = np.full((64, 7), T, np.uint8)
    R(s, 3, 14, 3, 63, GY); R(s, 4, 16, 4, 63, FARS)
    R(s, 0, 0, 6, 15, K); R(s, 1, 1, 5, 14, ASPD)
    R(s, 2, 2, 4, 4, RED if not green else BRKS)
    R(s, 2, 6, 4, 8, R1)
    R(s, 2, 10, 4, 12, GRN if green else GRNS)
    if not green: P(s, 2, 2, WH)
    else: P(s, 2, 10, WH)
    R(s, 1, 30, 5, 34, CRM); R(s, 2, 31, 4, 33, CYAN)                          # pedestrian button box
    return outline(s)


PEOPLE = [(150, 9, RED, SK, K, False), (95, -7, TEAL, SS, BRK, True), (40, 11, CRM, SK, BRKS, False),
          (128, -10, GRN, SS, K, True)]
CIRC = 2 * math.pi * 13
STOP_D = STOP_STEP / 16 * CIRC + CIRC     # wheel angle lands on STOP_STEP when stopped
LIGHT_WX = int(126 + STOP_D * F_NEAR)


def drive_dist(t):
    v0 = STOP_D / 1.05
    if t < 0.8: return v0 * t
    if t < 1.3:
        u = t - 0.8
        return v0 * 0.8 + v0 * u - v0 * u * u
    if t < 11.9: return STOP_D
    u = t - 11.9
    return STOP_D + 60 * u * u


def _hscroll(cv, strip, off, y0):
    idx = (np.arange(W) + off) % strip.shape[1]
    sub = strip[:, idx]
    m = sub != T
    cv[y0:y0 + strip.shape[0]][m] = sub[m]


def street(t, k):
    d = drive_dist(t)
    cv = np.full((H, W), SKY1, np.uint8)
    for x in range(W):                                # sky: two tones with a hand-dithered seam
        b = 30 + (x // 7) % 3
        R(cv, x, 0, x, b, SKY2)
        if x % 2 == 0: P(cv, x, b + 1, SKY2)
        if x % 4 == 1: P(cv, x, b + 3, SKY2)
    _hscroll(cv, clouds(), int(d * F_CLOUD + t * 3), 0)
    _hscroll(cv, far_layer(), int(d * F_FAR), 0)
    _hscroll(cv, near_layer(), int(d * F_NEAR), 0)
    near_off = int(d * F_NEAR)
    for i, (wx, sp, c, sk, hc, flip) in enumerate(PEOPLE):
        blit(cv, person(c, sk, hc, (k + i) % 2, flip), int(wx + sp * t) - near_off, SIDEWALK - 10)
    blit(cv, traffic_light(t >= 11.8), LIGHT_WX - near_off, 94)
    for i, (bx, by, sp) in enumerate(((20, 44, 16), (34, 50, 16), (90, 30, -12))):
        blit(cv, BIRD[(k + i) % 2], int((bx + sp * t) % 170) - 20, by + (k + i) % 2)
    R(cv, 0, 158, W - 1, 158, GY); R(cv, 0, 159, W - 1, 159, K)
    _hscroll(cv, road_strip(), int(d * F_ROAD), 160)
    # car shadow (ragged, under the sills)
    R(cv, CAR_X + 8, GROUND - 1, CAR_X + 112, GROUND, K)
    R(cv, CAR_X + 4, GROUND + 1, CAR_X + 116, GROUND + 1, ASPD)
    _hscroll(cv, front_strip(), int(d * F_FRONT), 206)
    off = int(d * F_FRONT)
    for px in (-30, 110, 250):                        # planters with shrubs
        x = px - off
        R(cv, x, 226, x + 14, 233, BRKS); R(cv, x, 226, x + 14, 226, BRK); R(cv, x + 1, 234, x + 14, 234, ASPD)
        for xx in range(x + 2, x + 14, 4): R(cv, xx, 228, xx, 232, BRK)
        for dx, r in ((3, 4), (8, 5), (12, 3)):
            for yy in range(223 - r, 227):
                for xx in range(x + dx - r, x + dx + r + 1):
                    if (xx - x - dx) ** 2 + (yy - 223) ** 2 <= r * r:
                        lit = (xx - x - dx) + (yy - 223) < -1 and h01(xx, yy, 2) < 0.7
                        P(cv, xx, yy, GRN if lit else GRNS)
            P(cv, x + dx, 220 - r + 3, RED)
    wx = int(150 - 13 * t - d * F_FRONT)              # dog walker on the near pavement
    fr = k % 2
    blit(cv, person(BRK, SK, K, fr, True), wx, 214)
    dog = _spr(['k      ', 'kbbbbb ', ' bbbbbt', ' b  b  ' if fr else '  bb   '], {'b': BRKS, 'k': K, 't': BRKS})
    blit(cv, outline(pad(dog)), wx - 12, 226)
    R(cv, wx - 5, 223 + fr, wx, 223 + fr, K)
    hyd = outline(pad(_spr([' gg ', 'rrrr', 'grrg', ' rr ', ' rB ', ' rB ', 'rrrr'], {'r': RED, 'g': GY, 'B': BRKS})))
    blit(cv, hyd, 60 - off, 214)
    return cv


BAR_POS = [0, 0]


def car_layer(cv, t, k, expr, pose, lit=False):
    d = drive_dist(t)
    moving = 0.0 < t < 1.3 or t > 11.9
    bob = 1 if moving and k % 2 else 0
    blit(cv, car_sprite(expr, pose, k), CAR_X, CAR_Y + bob)
    ang = int(round(d / CIRC * 16)) % 16
    for i, wc in enumerate(WHEELS):
        spr = tyre_rot(WHEEL_N, ang, lit and i == 1 and not moving)
        x0, y0 = CAR_X + wc - 13 - 1, CAR_Y + WHEEL_CY - 13 - 1
        blit(cv, spr, x0, y0)
        if i == 1:
            ys, xs = np.nonzero(tyre_rot(WHEEL_N, STOP_STEP, True) == BY)
            BAR_POS[:] = [x0 + int(xs.mean()), y0 + int(ys.mean())]
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
    bx, by = BAR_POS
    if lit and text:
        for i, (sx, sy) in enumerate(((-5, -2), (5, -3), (-7, 2), (7, 1))):
            if (k + i) % 3 != 0:
                P(cv, bx + sx, by + sy, BY)
        if t >= 1.7:
            blit(cv, ARROW_L, bx + 5 + (k % 2), by - 4)
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
        bx, by = BAR_POS
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
