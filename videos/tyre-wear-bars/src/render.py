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

PAL_HEX = ['#171a2e', '#a8d8ea', '#7fb8dc', '#c8d8e2', '#24202e', '#8c9cc0', '#6f7ea6', '#c8735a',
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

# ------------------------------------------------------------------ presenter, full body (crouch by the tyre)
GUY_MAP = {'#231a1c': K, '#4f3d42': R1, '#c08862': SK, '#a06b4b': SS, '#d4917a': SS, '#6e2f33': K,
           '#12121c': K, '#ffffff': WH, '#a9b0bb': GY, '#d3d8e0': WH, '#7b8491': B2, '#f7f7fa': WH,
           '#d6d9e2': GY, '#2b2d33': R1, '#1f2025': R0, '#454852': R2, '#16171b': K, '#f4f4f6': WH,
           '#cfd2da': GY, '#b9bcc6': GY, '#1a1a2e': K, '#3a1418': K}
_GM = {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)): v for h, v in GUY_MAP.items()}


def to_idx(img):
    a = np.array(img.convert('RGBA'))
    out = np.full(a.shape[:2], T, np.uint8)
    for y, x in zip(*np.nonzero(a[..., 3] > 0)):
        c = tuple(int(v) for v in a[y, x, :3])
        if c not in _GM:
            _GM[c] = int(np.argmin(((PAL.astype(int) - c) ** 2).sum(1)))
        out[y, x] = _GM[c]
    return out


@lru_cache(None)
def stand(expr, pose):
    return to_idx(pix.guy(expr, False, pose))


@lru_cache(None)
def crouch(expr, pose):
    """Front-view squat: full torso to the waist, thighs out to wide knees, shins down to the shoes."""
    g = stand(expr, pose)
    s = np.full((57, 48), T, np.uint8)
    s[:44] = g[:44]
    R(s, 16, 44, 31, 46, R1); R(s, 16, 44, 31, 44, K)                # waistband + seat
    R(s, 22, 46, 25, 48, R0)                                         # crotch shadow
    for (hx, hy), (kx, ky) in (((19, 46), (8, 49)), ((28, 46), (39, 49))):
        for x, y in pix._line((hx, hy), (kx, ky)):                   # thighs out to the knees
            R(s, x - 2, y - 1, x + 2, y + 2, R1)
        R(s, kx - 2, ky - 2, kx + 2, ky - 2, R2)                     # knee highlight (warm)
        sx = kx + (2 if kx < 24 else -2)
        for x, y in pix._line((kx, ky), (sx, 53)):                   # shins
            R(s, x - 2, y, x + 1, y, R1)
            P(s, x + (1 if kx < 24 else -2), y, R0)                  # cool shadow side
        R(s, sx - 4, 53, sx + 4, 55, WH); R(s, sx - 4, 55, sx + 4, 55, GY); R(s, sx - 3, 53, sx - 1, 53, GY)
    hands = g[:50] == SK                                             # hands stay in front of the knees
    hands[:40] = False
    s[:50][hands] = SK
    return outline(s)

# ------------------------------------------------------------------ the car (side view, faces right)
CAR_X, CAR_Y = 8, 149           # sprite origin on screen (8 px headroom for the waving arm)
CW_ = 120
WHEEL_N = 20
WHEELS = (20, 96)               # wheel centres, car-local x
WHEEL_CY = 8 + 30               # car-local y (sprite coords)
GROUND = CAR_Y + WHEEL_CY + 9
WR = WHEEL_N // 2            # wheel radius
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
            if arch(x, y, 11.6):
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
                if 11.6 <= d < 12.7 and s[y + o, x] not in (T,):
                    s[y + o, x] = CARH if y < 27 else CARS
                if 10.5 <= d < 11.6 and y <= 33:
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
        for x, y in pix._line((82, 27), (89, 29)):
            R(s, x, y, x + 1, y + 1, SK)
        R(s, 89, 29, 91, 31, SK); R(s, 92, 31, 93, 31, SK); P(s, 90, 31, SS)
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

# ------------------------------------------------------------------ the street (parallax layers, hand-textured)
NW, FWD, CW = 420, 300, 400
F_CLOUD, F_FAR, F_NEAR, F_ROAD, F_FRONT = 0.1, 0.3, 0.6, 1.0, 1.3
SIDEWALK = 150
ROAD_Y, FRONT_Y = 158, 206
HN = np.vectorize(h01)
# 3-tone wall ramps (light, mid, dark): light is warmer, shadow cooler (hue-shifted)
RAMP = {'brick': (SK, BRK, BRKS), 'cream': (CRM, CRMS, R2), 'teal': (CYAN, TEAL, GLS)}
MAX_EDGE = 19                   # chip limit in the layers (verify fails above 20)


def _disc(a, cx, cy, r, c):
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.5:
                if 0 <= y < a.shape[0]:
                    a[y, x % a.shape[1]] = c


def _blob(a, cx, cy, rx, ry, seed, fn):
    """Ragged clustered shape; calls fn(x, y) for each pixel inside."""
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1.0 - 0.45 * h01(x // 2, y // 2, seed) and 0 <= y < a.shape[0]:
                fn(x % a.shape[1], y)


def chip_edges(a, maxrun=MAX_EDGE, seed=0):
    """Hand-made look: no perfectly straight edge longer than maxrun. A 1 px chip/notch is cut into
    the side of the edge that stays constant, at irregular spacing (9-maxrun px)."""
    for b in (a, a.T):
        hgt, wid = b.shape
        for y in range(hgt - 1):
            up, dn = b[y], b[y + 1]
            ru = rd = 0
            lim = 13 + int(h01(y, seed, 31) * (maxrun - 13))
            for x in range(1, wid):
                d0, d1 = up[x - 1] != dn[x - 1], up[x] != dn[x]
                ru = ru + 1 if d0 and d1 and up[x] == up[x - 1] else 0
                rd = rd + 1 if d0 and d1 and dn[x] == dn[x - 1] else 0
                if ru + 1 >= lim:
                    up[x] = dn[x]
                    ru = rd = 0; lim = 13 + int(h01(x, y + seed, 32) * (maxrun - 13))
                elif rd + 1 >= lim:
                    dn[x] = up[x]
                    ru = rd = 0; lim = 13 + int(h01(x, y + seed, 33) * (maxrun - 13))
    return a


@lru_cache(None)
def sky():
    """Two blues and a horizon haze, joined by hand-dithered seams. Open sky is not a structure."""
    a = np.full((H, W), SKY2, np.uint8)
    for y in range(H):
        base, other = (SKY2, SKY1) if y < 26 else ((SKY1, GLH) if y < 58 else (GLH, SKY1))
        a[y] = base
        if y in (22, 24, 54, 56):                    # transition dithers
            a[y, (np.arange(W) + y) % 2 == 0] = other
        elif y in (25, 57):
            a[y, (np.arange(W) + y) % 3 != 0] = other
    return a


@lru_cache(None)
def clouds():
    a = np.full((70, CW), T, np.uint8)
    puffs = []
    for cx, cy, s in ((40, 30, 1.0), (150, 18, 0.8), (250, 40, 1.2), (340, 24, 0.9)):
        for dx, dy, r in ((0, 0, 8), (-9, 3, 6), (10, 2, 7), (4, -4, 6), (-15, 5, 4), (16, 5, 4)):
            puffs.append((cx + dx * s, cy + dy * s, r * s))
    for px, py, r in puffs:
        _disc(a, px, py, r, CLD)
    for px, py, r in puffs:                           # each puff: lit cap, cool belly (clustered)
        for y in range(int(py - r), int(py + r) + 1):
            for x in range(int(px - r), int(px + r) + 1):
                dd = (x - px) ** 2 + (y - py) ** 2
                if 0 <= y < 70 and a[y, x % CW] != T and (r * 0.55) ** 2 < dd <= r * r and y > py + 1:
                    a[y, x % CW] = GLH if (y > py + r * 0.5 or (x + y) % 2) else CLD
                elif 0 <= y < 70 and a[y, x % CW] != T and y == int(py) and (x % 3 == 0):
                    a[y, x % CW] = GLH
    return chip_edges(a, seed=2)


@lru_cache(None)
def far_layer():
    a = np.full((H, FWD), T, np.uint8)
    rng = np.random.default_rng(3)
    x = 0
    while x < FWD:
        w = int(rng.integers(14, 30)); top = int(rng.integers(62, 108))
        x1 = min(FWD - 1, x + w - 2)
        cx, tops = x, {}
        while cx <= x1:                               # stepped, uneven roofline
            sw = int(rng.integers(5, 12)); off = int(rng.integers(0, 2))
            for c in range(cx, min(x1, cx + sw - 1) + 1):
                tops[c] = top + off
            cx += sw
        for c in range(x, x1 + 1):
            R(a, c, tops[c], c, SIDEWALK, FAR)
        for y in range(top, SIDEWALK + 1):            # jagged shadow side
            wd = 2 + int(h01(x, y // 4, 5) * 2)
            for c in range(x1 - wd + 1, x1 + 1):
                if a[y, c] != T: a[y, c] = FARS
        for y in range(top + 1, top + 16):            # sunlit edge cluster
            if h01(x, y // 3, 6) < 0.6 and a[y, x] != T: a[y, x] = GLH
        yy = top + 6
        while yy < SIDEWALK - 3:                      # floor ledges with gaps
            for c in range(x, x1 + 1):
                if h01(c, yy, 7) > 0.12 and a[yy, c] == FAR: a[yy, c] = FARS
            for c in range(x + 2, x1 - 3, 4 + int(h01(x, yy, 9) * 2)):   # uneven windows
                if h01(c, yy, 8) < 0.7:
                    R(a, c, yy + 2, c + int(h01(c, yy, 4) * 2), yy + 4 + int(h01(c, yy, 3) * 2),
                      GLH if h01(c, yy, 2) > 0.9 else FARS)
            yy += 8 + int(h01(x, yy, 8) * 3)
        r = rng.random()
        if r < 0.35:                                  # aerial
            for y in range(top - 8, top): P(a, x + w // 2, y, FARS)
            R(a, x + w // 2 - 2, top - 6, x + w // 2 + 2, top - 6, FARS)
        elif r < 0.6:                                 # water tank on legs
            R(a, x + 3, top - 6, x + 7, top - 3, FARS); P(a, x + 3, top - 2, FARS); P(a, x + 7, top - 2, FARS)
        x += w
    return chip_edges(a, seed=1)


def _window(a, xx, yy, ww, wh, kind, seed):
    light, mid, dark = RAMP[kind]
    frame = CRMS if kind == 'cream' else CRM
    R(a, xx - 1, yy - 1, xx + ww, yy + wh, frame)
    R(a, xx, yy, xx + ww - 1, yy + wh - 1, GLS)
    R(a, xx, yy, xx + ww - 1, yy, ASPD)               # shadow under the lintel, inside
    for i in range(min(ww, wh) // 2):                 # hand-placed glint
        P(a, xx + 1 + i, yy + wh - 2 - i * 2, GLH)
    if ww >= 7:
        R(a, xx + ww // 2, yy, xx + ww // 2, yy + wh - 1, frame)
    if wh >= 9:
        R(a, xx, yy + wh // 2, xx + ww - 1, yy + wh // 2, frame)
    for i in range(ww + 2):                           # chipped frame paint
        if h01(xx + i, yy, seed + 5) < 0.12: P(a, xx - 1 + i, yy - 1, mid)
    v = h01(xx, yy, seed)
    if v < 0.22:                                      # curtains, drooping
        c = RED if h01(xx, yy, seed + 1) < 0.5 else CRM
        R(a, xx, yy + 1, xx, yy + wh - 1, c); R(a, xx + ww - 1, yy + 1, xx + ww - 1, yy + wh - 1, c)
        P(a, xx + 1, yy + wh - 1, c); P(a, xx + ww - 2, yy + wh - 1, c)
    elif v < 0.36:                                    # half-drawn blind
        R(a, xx, yy + 1, xx + ww - 1, yy + 2 + int(h01(xx, yy, 7) * 3), CRMS)
    elif v < 0.44:                                    # open shutters, slatted
        sc = [GRN, RED, TEAL, BRKS][int(h01(xx, yy, seed + 2) * 4)]
        for sx in (xx - 3, xx + ww + 1):
            R(a, sx, yy - 1, sx + 1, yy + wh, sc)
            for y in range(yy, yy + wh, 2): P(a, sx + (1 if sx < xx else 0), y, K)
    # sill: lit top, dithered shadow beneath, occasional flower box or dirt streak
    R(a, xx - 2, yy + wh + 1, xx + ww + 1, yy + wh + 1, light)
    P(a, xx - 2 + int(h01(xx, yy, 9) * (ww + 3)), yy + wh + 1, mid)
    for c in range(xx - 1, xx + ww + 1):
        if (c + yy) % 2 == 0: P(a, c, yy + wh + 2, dark)
    if h01(xx, yy, seed + 3) < 0.3:
        R(a, xx, yy + wh - 1, xx + ww - 1, yy + wh, BRKS)
        for i in range(0, ww, 2): P(a, xx + i, yy + wh - 2, RED if (i // 2) % 2 else GRN)
    elif h01(xx, yy, seed + 4) < 0.5:
        sx = xx + int(h01(xx, yy, 6) * ww)
        for i in range(3, 4 + int(h01(xx, yy, 8) * 6)):
            if i % 2 or h01(sx, i, 2) < 0.5: P(a, sx, yy + wh + i, dark)


def _coursing(a, cx, cy, rx, ry, seed):
    """A clustered patch of exposed brick courses with uneven joints."""
    def f(x, y):
        row = y // 3
        jog = 1 if h01(row, x // 6, seed) < 0.2 else 0
        if y % 3 == 2 or (x + (row % 2) * 3 + jog) % 6 == 0:
            a[y, x] = BRKS
        elif a[y, x] not in (GLS,):
            a[y, x] = BRK if h01(x // 6, row, seed + 1) > 0.15 else SK
    _blob(a, cx, cy, rx, ry, seed, f)


def _facade(a, x, w, top, kind, rng):
    light, mid, dark = RAMP[kind]
    x1 = min(NW - 1, x + w - 1)
    cx, tops = x, {}
    while cx <= x1:                                   # ragged parapet
        sw = int(rng.integers(6, 14)); off = 1 if rng.random() < 0.4 else 0
        for c in range(cx, min(x1, cx + sw - 1) + 1):
            tops[c] = top + off
        cx += sw
    for c in range(x, x1 + 1):
        R(a, c, tops[c], c, SIDEWALK - 1, mid)
        P(a, c, tops[c], light if c < x + w * 0.6 else mid)
    ct = top + 4                                      # projecting cornice
    R(a, x - 1, ct, x1 + 1, ct, light)
    for c in range(x - 1, x1 + 2):
        P(a, c, ct + 1, dark)
        if c % 2: P(a, c, ct + 2, dark)               # dithered shadow under the ledge
        if (c + 1) % 4 == 0: P(a, c, ct + 3, dark)
    for y in range(ct + 1, SIDEWALK - 1):             # jagged lit edge (left) and shadow edge (right)
        lw = 1 + int(h01(x, y // 8, 1) * 2)
        if lw: R(a, x, y, x + lw - 1, y, light)
        dw = 2 + int(h01(x1, y // 8, 2) * 2)
        R(a, x1 - dw + 1, y, x1, y, dark)
    for i in range(2):                                # warm sunlit clusters, upper left
        bx, by = x + 5 + int(h01(x, i, 3) * w * 0.3), ct + 6 + int(h01(x, i, 4) * 14)
        _blob(a, bx, by, 3 + h01(x, i, 5) * 3, 2 + h01(x, i, 6) * 2, x + i,
              lambda px, py: a.__setitem__((py, px), light) if a[py, px] == mid else None)
    # material texture (clustered, never all-over)
    if kind == 'brick':
        for i in range(3):
            _coursing(a, x + 4 + h01(x, i, 7) * (w - 8), ct + 8 + h01(x, i, 8) * 30, 5 + h01(x, i, 9) * 5,
                      3 + h01(x, i, 10) * 3, x + i)
        for i in range(2):                            # chipped / missing bricks
            bx, by = x + 3 + int(h01(x, i, 11) * (w - 8)), ct + 5 + int(h01(x, i, 12) * 34)
            R(a, bx, by, bx + 2, by, R2); P(a, bx + 1, by + 1, light)
    else:
        for i in range(2 if kind == 'cream' else 1):  # peeling paint revealing brick
            bx, by = x + 6 + h01(x, i, 13) * (w - 12), ct + 10 + h01(x, i, 14) * 28
            rx, ry = 4 + h01(x, i, 15) * 3, 3 + h01(x, i, 16) * 2
            rx, ry = rx * 0.75, ry * 0.8
            _coursing(a, bx, by, rx, ry, x + 7 * i)
            for k_ in range(10):                      # curled paint edge
                ang = k_ * 0.63
                P(a, int(bx + (rx + 0.6) * math.cos(ang)), int(by + (ry + 0.6) * math.sin(ang)), light)
        if kind == 'teal':
            for c in range(x + 3, x1 - 2, 7):         # cladding seams, broken
                for y in range(ct + 4, 116):
                    if a[y, c] == mid and h01(c, y // 5, 17) > 0.25: a[y, c] = dark
    for i in range(1):                                # crack
        px, py = x + 4 + int(h01(x, i, 18) * (w - 8)), ct + 8 + int(h01(x, i, 19) * 30)
        for j in range(5 + int(h01(x, i, 20) * 4)):
            if a[py, px] in (mid, light): a[py, px] = dark
            px += 1 if h01(px, py, 21) < 0.5 else 0; py += 1
    for i in range(2):                                # rising damp / dirt patches (dithered)
        bx = x + 4 + int(h01(x, i, 22) * (w - 8))
        _blob(a, bx, 113 + h01(x, i, 23) * 4, 4 + h01(x, i, 24) * 3, 3, x + 30 + i,
              lambda px, py: a.__setitem__((py, px), dark) if a[py, px] == mid and (px + py) % 2 else None)
    # uneven windows
    yy = ct + 7
    while yy < 104:
        wh = 7 + int(h01(x, yy, 25) * 3)
        xx = x + 4 + int(h01(x, yy, 26) * 3)
        while xx < x1 - 9:
            ww = 5 + int(h01(xx, yy, 27) * 3)
            if h01(xx, yy, 28) < 0.88:
                _window(a, xx, yy + int(h01(xx, yy, 29) * 2), ww, wh, kind, x)
            else:                                     # bricked-up opening
                _coursing(a, xx + ww / 2, yy + wh / 2, ww / 2 + 0.5, wh / 2 + 0.5, xx)
            xx += ww + 5 + int(h01(xx, yy, 30) * 4)
        yy += wh + 6 + int(h01(x, yy, 31) * 3)
    # drainpipe with brackets, hopper and shoe
    px = x + 1 if h01(x, 0, 32) < 0.5 else x1 - 1
    for y in range(ct + 2, SIDEWALK - 1):
        a[y, px] = GY
        if (y - ct) % (11 + int(h01(x, 1, 33) * 3)) == 0: R(a, px, y, px + (1 if px == x + 1 else -1), y, K)
    R(a, px - 1, ct + 1, px + 1, ct + 2, GY); P(a, px - 1, ct + 2, FARS)
    P(a, px + (1 if px == x + 1 else -1), SIDEWALK - 2, GY)
    # rooftop clutter breaking the skyline
    for i in range(1 + (h01(x, top, 34) < 0.35)):
        r = h01(x, i, 35); rx = x + 3 + int(h01(x, i, 36) * (w - 12))
        tt = tops.get(rx, top)
        if r < 0.3:                                   # chimney with pots
            hh = 5 + int(h01(x, i, 37) * 5)
            R(a, rx, tt - hh, rx + 4, tt - 1, BRK); R(a, rx + 3, tt - hh, rx + 4, tt - 1, BRKS)
            R(a, rx - 1, tt - hh - 1, rx + 5, tt - hh, CRMS)
            P(a, rx + 1, tt - hh - 2, BRKS); P(a, rx + 3, tt - hh - 2, BRKS)
            for y in range(tt - hh + 2, tt - 1, 3): R(a, rx, y, rx + 2, y, BRKS)
        elif r < 0.5:                                 # vent box
            R(a, rx, tt - 4, rx + 5, tt - 1, GY); R(a, rx + 4, tt - 4, rx + 5, tt - 1, FARS)
            for c in range(rx + 1, rx + 4, 2): R(a, c, tt - 3, c, tt - 2, K)
        elif r < 0.7:                                 # aerial
            for y in range(tt - 9, tt): P(a, rx + 2, y, K)
            R(a, rx, tt - 8, rx + 4, tt - 8, K); R(a, rx + 1, tt - 6, rx + 3, tt - 6, K)
        elif r < 0.85:                                # satellite dish
            _disc(a, rx + 2, tt - 4, 2.4, GY); P(a, rx + 2, tt - 4, FARS); R(a, rx + 2, tt - 2, rx + 2, tt - 1, K)
        else:                                         # rooftop sign on legs
            R(a, rx, tt - 8, rx + 8, tt - 4, RED); R(a, rx + 1, tt - 7, rx + 7, tt - 7, CRM)
            P(a, rx + 1, tt - 3, K); P(a, rx + 7, tt - 3, K); P(a, rx + 7, tt - 2, K)
    # shopfront
    for c in range(x + 1, x1):
        P(a, c, 127, K); P(a, c, 128, K if h01(c, 3, x) > 0.1 else dark)
    R(a, x + 3, 129, x1 - 4, SIDEWALK - 1, GLS)
    R(a, x + 3, 129, x1 - 4, 130, ASPD)
    fx = x + 3
    while fx < x1 - 4:                                # uneven display frames
        R(a, fx, 129, fx, SIDEWALK - 1, K if kind == 'brick' else GY)
        fx += 7 + int(h01(fx, 4, x) * 4)
    for i in range(6):
        P(a, x + 7 + i, 145 - i * 2, GLH); P(a, x + 8 + i, 145 - i * 2, GLH)
    for xx in range(x + 6, x1 - 6, 5):                # goods on display
        if h01(xx, 1, x) < 0.5:
            hgt = 3 + int(h01(xx, 3, x) * 3)
            R(a, xx, 146 - hgt, xx + 2, 146, [RED, CRM, TEAL, GRN][int(h01(xx, 2, x) * 4)])
    dx = x + w // 2 - 3
    R(a, dx, 133, dx + 5, SIDEWALK - 1, ASPD); R(a, dx, 133, dx + 5, 133, K)
    R(a, dx + 1, 135, dx + 4, 140, GLS); P(a, dx + 4, 142, GY)
    if kind != 'brick':                               # awning with ruffled, folded edge
        for xx in range(x + 1, x1):
            st = (xx // 3) % 2
            c, cs = (RED, BRKS) if st else (WH, CLD)
            ln = 123 + ((xx % 3) == 1) + (1 if h01(xx, 5, x) < 0.25 else 0)
            for y in range(119, ln + 1):
                a[y, xx] = cs if (xx % 3 == 2 and y > 120) else c
            if h01(xx, 6, x) < 0.2: P(a, xx, ln + 1, c)
        for c in range(x, x1 + 1):
            P(a, c, 118 - (1 if h01(c // 4, 7, x) < 0.25 else 0), K)
    else:                                             # fascia sign + hanging sign
        R(a, x + 6, 120, x1 - 8, 125, K); R(a, x + 7, 121, x1 - 9, 124, CRM)
        for xx in range(x + 9, x1 - 11, 3):
            R(a, xx, 122, xx + 1, 123 - (1 if h01(xx, 8, x) < 0.3 else 0), BRKS)
        R(a, x1 - 4, 112, x1 - 4, 115, K); R(a, x1 - 7, 115, x1 - 1, 119, RED); P(a, x1 - 6, 116, CRM)
    for c in range(x, x1 + 1):                        # plinth with chips
        P(a, c, SIDEWALK - 1, dark if h01(c, 9, x) > 0.15 else mid)
    return tops


def _wire(a, x0, y0, x1, y1, sag, c=ASPD):
    n = max(2, x1 - x0)
    for i in range(n + 1):
        u = i / n
        y = y0 + (y1 - y0) * u + 4 * sag * u * (1 - u)
        P(a, (x0 + i) % NW, int(round(y)), c)


@lru_cache(None)
def near_layer():
    a = np.full((H, NW), T, np.uint8)
    rng = np.random.default_rng(21)
    kinds = ['brick', 'cream', 'teal', 'brick', 'cream', 'brick', 'teal', 'cream']
    x, i, corners = 0, 0, []
    while x < NW - 30:
        w = int(rng.integers(40, 58)) if NW - x - 58 > 40 else NW - x
        top = int(rng.integers(64, 90))
        _facade(a, x, w, top, kinds[i % len(kinds)], rng)
        corners.append((x + w - 3, top + 8))
        x += w; i += 1
    for j, ((ax, ay), (bx, by)) in enumerate(zip(corners, corners[1:])):   # a few sagging wires
        if j % 2 == 0:
            _wire(a, ax, ay + 3, bx, by + 6, 6)
    for tx in (70, 205, 330):                                     # leafy street trees
        for y in range(120, SIDEWALK):
            R(a, tx, y, tx + 2, y, BRKS)
            if h01(tx, y // 3, 3) < 0.5: P(a, tx, y, SK)          # lit bark
            if h01(tx, y, 4) < 0.15: P(a, tx + 1, y, K)            # knots
        R(a, tx - 2, SIDEWALK - 1, tx + 4, SIDEWALK - 1, K)
        leaf = np.zeros((40, 44), bool)
        yy_, xx_ = np.mgrid[0:40, 0:44]
        for dx, dy, r in ((0, 0, 11), (-9, 6, 8), (10, 5, 8), (-4, -7, 7), (6, -6, 7), (0, 10, 7)):
            leaf |= (xx_ - 22 - dx) ** 2 + (yy_ - 20 - dy) ** 2 <= r * r
        for yy, xx in zip(*np.nonzero(leaf)):
            gx, gy = tx + 1 + xx - 22, 108 + yy - 20
            edge = not (leaf[min(39, yy + 2), xx] and leaf[yy, min(43, xx + 2)])
            lit = (xx - 22) + (yy - 20) < -4
            n = h01(gx // 2, gy // 2, 11)
            a[gy, gx % NW] = GRNS if (not lit and (n < 0.75 or edge)) else (GRNS if n < 0.18 else GRN)
        for k_ in range(10):
            gx = tx + int((h01(k_, tx, 1) - 0.5) * 24); gy = 100 + int(h01(k_, tx, 2) * 14)
            R(a, gx, gy, gx + 1, gy, GRN); P(a, gx, gy + 1, GRNS)
    for lx in (138, 280, 400):                                    # lamp posts: rings, base, little banner
        for y in range(98, SIDEWALK):
            P(a, lx, y, GY); P(a, lx + 1, y, FARS)
        for y in range(104, SIDEWALK - 4, 9 + int(h01(lx, 0, 3) * 3)):
            R(a, lx - 1, y, lx + 2, y, K)
        R(a, lx - 2, 95, lx + 3, 97, K); R(a, lx - 1, 98, lx + 2, 98, CRM)
        R(a, lx - 1, SIDEWALK - 4, lx + 2, SIDEWALK - 1, K); P(a, lx, SIDEWALK - 3, GY)
        R(a, lx + 2, 104, lx + 5, 111, RED); P(a, lx + 5, 111, T); P(a, lx + 4, 110, BRKS); R(a, lx + 3, 106, lx + 4, 106, CRM)
    # pavement: staggered slabs, chipped, cracked
    R(a, 0, SIDEWALK, NW - 1, 157, SIDE)
    for xx in range(NW):
        for yy in range(SIDEWALK, 158):
            if (xx + (4 if yy > 153 else 0)) % 9 == 0 or (yy == 153 and h01(xx, 1, 40) > 0.12):
                a[yy, xx] = CRMS
            elif yy == SIDEWALK and h01(xx, 2, 41) < 0.18:
                a[yy, xx] = CRMS
    for xx in range(NW):                                           # buildings' shade on the pavement
        if a[SIDEWALK, xx] == SIDE and (xx % 2 == 0 or h01(xx, 3, 42) < 0.3): a[SIDEWALK, xx] = CRMS
        if a[SIDEWALK + 1, xx] == SIDE and (xx + 1) % 4 == 0: a[SIDEWALK + 1, xx] = CRMS
    for cx_ in range(15, NW, 37):                                  # cracks / oil stain clusters
        for j in range(4):
            P(a, cx_ + j, SIDEWALK + 2 + (j % 3), CRMS)
    return chip_edges(outline(a), seed=3)


@lru_cache(None)
def road_strip():
    """Kerb, gutter and asphalt: clustered grit, wavy wheel tracks, cracks, patch, manhole, drains."""
    rw, rh = 256, FRONT_Y - ROAD_Y
    a = np.full((rh, rw), ASP, np.uint8)
    a[0] = GY
    a[1] = K
    for x in range(rw):
        if h01(x, 0, 50) < 0.14 or x % 12 == 7: a[0, x] = CRMS if h01(x, 1, 50) < 0.5 else SIDE   # chipped kerb
        if h01(x, 1, 51) < 0.12 or x % 13 == 9: a[1, x] = FARS
        a[2, x] = ASPD if x % 10 != 6 and h01(x, 2, 51) > 0.1 else ASP
        a[3, x] = ASPD if (x + (x // 7)) % 2 else ASP
    for dx in (40, 170):                                          # gutter drains
        R(a, dx, 1, dx + 6, 3, K)
        for c in range(dx + 1, dx + 6, 2): R(a, c, 2, c, 3, FARS)
    for base in (15, 23, 31):                                     # patchy worn wheel tracks
        x = 0
        while x < rw:
            ln = 6 + int(h01(x, base, 52) * 14)
            if h01(x, base, 57) < 0.6:
                for xx in range(x, min(rw, x + ln)):
                    yc = base + int(round(math.sin(xx / 17 + base) * 1.5))
                    for y in (yc, yc + 1):
                        if (xx + y) % 2 == 0: a[y, xx] = ASPD
            x += ln + 3 + int(h01(x, base, 58) * 10)
    for i in range(26):                                           # debris washed into the gutter
        gx = int(h01(i, 5, 59) * rw)
        for j in range(3 + int(h01(i, 6, 59) * 4)):
            P(a, (gx + j * 2 + int(h01(i, j, 60) * 2)) % rw, 4 + int(h01(j, i, 61) * 6), ASPD if j % 3 else SIDE)
    cells = [(cx, cy) for cy in range(4, rh - 3, 8) for cx in range(0, rw, 8)]
    for i, (cx, cy) in enumerate(cells):                          # grit: one small cluster per 8 px cell
        gx, gy = cx + int(h01(i, 0, 53) * 5), cy + int(h01(i, 1, 53) * 5)
        c = ASPD if i % 4 else SIDE
        for j in range(2 + int(h01(i, 2, 53) * 3)):
            P(a, (gx + int(h01(i, j, 54) * 3)) % rw, gy + int(h01(j, i, 55) * 2), c)
    R(a, 150, 9, 176, 13, ASPD); R(a, 151, 10, 175, 12, ASP)      # tar patch, ragged corners
    P(a, 150, 9, ASP); P(a, 176, 13, ASP); P(a, 163, 9, ASP)
    for x, y in pix._line((30, 7), (44, 17)) + pix._line((44, 17), (52, 16)) + pix._line((200, 32), (214, 40)):
        P(a, x, y, ASPD)
    _disc(a, 92, 24, 5, ASPD); _disc(a, 92, 24, 4, FARS)          # manhole
    for i in range(-3, 4, 2):
        R(a, 89, 24 + i, 95, 24 + i, ASPD)
    for x0 in range(0, rw, 32):                                   # worn lane dashes
        R(a, x0, 43, x0 + 11, 44, WH)
        for x in range(x0, x0 + 12):
            if h01(x, 43, 3) < 0.22: P(a, x, 43 + int(h01(x, 4, 3) * 2), SIDE)
        P(a, x0, 43, ASP); P(a, x0 + 11, 44, ASP)
    for x in range(rw):                                           # near gutter
        a[rh - 1, x] = ASPD if h01(x, 9, 56) > 0.2 and x % 9 != 4 else ASP
        if (x + 1) % 2 == 0 and h01(x, 10, 56) < 0.5: a[rh - 2, x] = ASPD
    return chip_edges(a, seed=4)


@lru_cache(None)
def front_strip():
    fw, fh = 280, H - FRONT_Y
    a = np.full((fh, fw), SIDE, np.uint8)
    a[0] = GY; a[1:3] = CRMS
    for x in range(fw):
        if h01(x, 0, 60) < 0.14 or x % 11 == 3: a[0, x] = SIDE if h01(x, 1, 60) < 0.6 else CRMS
        if x % (5 + int(h01(x // 5, 2, 60) * 2)) == 0: a[1, x] = K
    for x in range(fw):                                           # slabs 12x12, staggered, chipped
        for y in range(3, fh):
            row = (y - 3) // 12
            if (y - 3) % 12 == 0 and h01(x, y, 61) > 0.1:
                a[y, x] = CRMS
            elif (x + row * 6) % 12 == 0 and h01(x, y, 62) > 0.1:
                a[y, x] = CRMS
    for x, y in pix._line((60, 6), (66, 12)) + pix._line((66, 12), (64, 17)) + pix._line((150, 20), (157, 26)):
        a[y, x] = ASPD
    for i in range(10):                                           # stains in clusters
        sx, sy = int(h01(i, 3, 63) * fw), 6 + int(h01(i, 4, 63) * (fh - 9))
        for j in range(3):
            if (sx + j + sy) % 2 == 0: a[sy + j % 2, (sx + j) % fw] = CRMS
    R(a, 180, 4, 190, 9, K)
    for x in range(181, 190, 2): R(a, x, 5, x, 8, FARS)
    return chip_edges(a, seed=5)


@lru_cache(None)
def traffic_light(green):
    s = np.full((64, 9), T, np.uint8)
    for y in range(14, 64):
        P(s, 4, y, GY); P(s, 5, y, FARS)
    for y in range(18, 62, 9):                       # pole rings (protrude, break the outline)
        R(s, 3, y, 6, y, K)
    R(s, 1, 0, 7, 15, K); R(s, 2, 1, 6, 14, ASPD)
    R(s, 3, 2, 5, 4, RED if not green else BRKS)
    R(s, 3, 6, 5, 8, R1)
    R(s, 3, 10, 5, 12, GRN if green else GRNS)
    P(s, 3, 2 if not green else 10, WH)
    R(s, 2, 30, 6, 34, CRM); R(s, 3, 31, 5, 33, CYAN)   # pedestrian button
    R(s, 3, 60, 6, 63, K)                               # base
    return outline(s)


PEOPLE = [(150, 9, RED, SK, K, False), (95, -7, TEAL, SS, BRK, True), (40, 11, CRM, SK, BRKS, False),
          (128, -10, GRN, SS, K, True)]
CIRC = 2 * math.pi * WR
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


SKY_SENTINEL = 254


# ------------------------------------------------------------------ street life (all stepped on key times)
PIGEON = [_spr([' gk', 'ggg', ' k '], {'g': GY, 'k': K}), _spr(['   ', 'ggg', 'gkk'], {'g': GY, 'k': K})]
TREES_WX = (70, 205, 330)
STEAM_WX = ((58, 72), (176, 80), (300, 70))          # rooftop vents/chimneys (world x, y)


def sun(cv, k):
    cx, cy = 112, 66
    for y in range(cy - 5, cy + 6):
        for x in range(cx - 5, cx + 6):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d <= 25:
                P(cv, x, y, WH if d <= 12 or (x + y) % 2 else CLD)
    for i in range(8):                                # rays, two stepped lengths
        ang = math.radians(i * 45 + (k % 2) * 22.5)
        for rr in range(8, 10 + (i + k) % 2):
            P(cv, int(round(cx + rr * math.cos(ang))), int(round(cy - rr * math.sin(ang))), CLD)


def bunting(cv, near_off, k):
    span = 60
    for y0, sag, cols in ((110, 5, (RED, CRM, TEAL, GRN)),):
        start = (near_off // span) * span - span
        for wx0 in range(start, near_off + W + span, span):
            for i in range(span + 1):
                u = i / span
                x = wx0 + i - near_off
                y = int(round(y0 + 4 * sag * u * (1 - u) + (3 if (wx0 // span) % 2 else 0) * u))
                P(cv, x, y, ASPD)
                if i % 6 == 3 and 2 < i < span - 2:
                    c = cols[(i // 6 + wx0 // span) % 4]
                    fl = (k + i // 6) % 2
                    R(cv, x - 1, y + 1, x + 1, y + 1, c)
                    P(cv, x + (fl if fl else 0) - (0 if fl else 0), y + 2, c)
                    P(cv, x - 1 + fl * 2, y + 2, c)
                    P(cv, x - 1 + fl, y + 3, c)


def leaves(cv, near_off, t):
    for j, tx in enumerate(TREES_WX):
        for n in range(3):
            age = (t * 0.45 + n / 3 + j * 0.21) % 1.0
            x = tx - near_off + int(math.sin((age + n) * 9) * 4) - 6 + n * 6
            y = 104 + int(age * 46)
            if y < SIDEWALK + 2:
                P(cv, x, y, GRN if n % 2 else BRK); P(cv, x + 1, y + (1 if int(age * 12) % 2 else 0), GRNS)


def steam(cv, near_off, t):
    for j, (wx, wy) in enumerate(STEAM_WX):
        for n in range(3):
            age = (t * 0.8 + n / 3 + j * 0.3) % 1.0
            x = wx - near_off + int(age * 6) + (n % 2)
            y = wy - int(age * 14)
            r = 1 if age < 0.4 else 2
            for yy in range(y - r, y + r + 1):
                for xx in range(x - r, x + r + 1):
                    if (xx - x) ** 2 + (yy - y) ** 2 <= r * r and (age < 0.7 or (xx + yy) % 2):
                        P(cv, xx, yy, CLD if age < 0.5 else GLH)


def cyclist(cv, t, k):
    if not 8.9 <= t < 12.6:
        return
    x = int(-14 + (t - 8.9) * 42)
    s = np.full((13, 13), T, np.uint8)
    fr = k % 2
    for cx in (2, 10):
        for a_ in range(0, 360, 45):
            P(s, int(round(cx + 2 * math.cos(math.radians(a_)))), int(round(10 + 2 * math.sin(math.radians(a_)))), K)
        P(s, cx + (1 if fr else 0), 10 - (0 if fr else 1), GY)
    for p in pix._line((2, 10), (6, 7)) + pix._line((6, 7), (10, 10)) + pix._line((6, 7), (9, 6)):
        P(s, *p, RED)
    R(s, 5, 3, 7, 6, TEAL); R(s, 6, 0, 7, 2, SK); P(s, 6, 0, K); P(s, 7, 0, K)
    R(s, 8, 4, 9, 5, SK)
    P(s, 5 + fr, 7, GLS); P(s, 6 - fr, 8, GLS)
    blit(cv, outline(s), x, SIDEWALK - 6)


def pigeons(cv, near_off, k):
    for j, wx in enumerate((112, 120, 250)):
        blit(cv, outline(pad(PIGEON[(k + j) % 3 == 0])), wx - near_off, SIDEWALK + 1)


def exhaust(cv, t, k, moving):
    rate = 2.2 if moving else 1.1
    for n in range(3):
        age = (t * rate + n / 3) % 1.0
        if not moving and age > 0.6:
            continue
        x = CAR_X + 1 - int(age * (16 if moving else 8)) - n
        y = CAR_Y + 41 - int(age * 5)
        r = 1 if age < 0.35 else 2
        for yy in range(y - r, y + r + 1):
            for xx in range(x - r, x + r + 1):
                if (xx - x) ** 2 + (yy - y) ** 2 <= r * r and (age < 0.5 or (xx + yy + k) % 2):
                    P(cv, xx, yy, CLD if age < 0.45 else GLH)


def street(t, k, sentinel=False, dist=None):
    """Background only. sentinel=True fills open sky with 254 so verify can skip it."""
    d = drive_dist(t) if dist is None else dist
    cv = np.full((H, W), SKY_SENTINEL, np.uint8) if sentinel else sky().copy()
    if not sentinel:
        sun(cv, k)                                    # behind the clouds and rooftops
    _hscroll(cv, clouds(), int(d * F_CLOUD + t * 3), 0)
    _hscroll(cv, far_layer(), int(d * F_FAR), 0)
    _hscroll(cv, near_layer(), int(d * F_NEAR), 0)
    bunting(cv, int(d * F_NEAR), k)
    leaves(cv, int(d * F_NEAR), t)
    pigeons(cv, int(d * F_NEAR), k)
    near_off = int(d * F_NEAR)
    for i, (wx, sp, c, sk, hc, flip) in enumerate(PEOPLE):
        blit(cv, person(c, sk, hc, (k + i) % 2, flip), int(wx + sp * t) - near_off, SIDEWALK - 10)
    blit(cv, traffic_light(t >= 11.8), LIGHT_WX - near_off - 1, 94)
    cyclist(cv, t, k)
    for i, (bx, by, sp) in enumerate(((20, 44, 16), (34, 50, 16), (90, 30, -12))):
        blit(cv, BIRD[(k + i) % 2], int((bx + sp * t) % 170) - 20, by + (k + i) % 2)
    _hscroll(cv, road_strip(), int(d * F_ROAD), ROAD_Y)
    for x in range(CAR_X + 6, CAR_X + 114):           # ragged contact shadow under the car
        if h01(x, 0, 70) > 0.1 and x % 8 != 5: P(cv, x, GROUND - 1, K)
        if h01(x, 1, 70) > (0.12 if CAR_X + 12 < x < CAR_X + 108 else 0.4) and x % 9 != 2: P(cv, x, GROUND, ASPD)
        if h01(x, 2, 70) > 0.6 and CAR_X + 16 < x < CAR_X + 104: P(cv, x, GROUND + 1, ASPD)
    _hscroll(cv, front_strip(), int(d * F_FRONT), FRONT_Y)
    off = int(d * F_FRONT)
    for px in (-30, 110, 250):                        # planters with shrubs
        x = px - off
        R(cv, x, 226, x + 14, 233, BRKS); R(cv, x, 226, x + 14, 226, BRK); R(cv, x + 1, 234, x + 14, 234, ASPD)
        P(cv, x + 14, 226, BRKS); P(cv, x, 233, ASPD)
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
    exhaust(cv, t, k, moving)
    blit(cv, car_sprite(expr, pose, k), CAR_X, CAR_Y + bob)
    ang = int(round(d / CIRC * 16)) % 16
    for i, wc in enumerate(WHEELS):
        spr = tyre_rot(WHEEL_N, ang, lit and i == 1 and not moving)
        x0, y0 = CAR_X + wc - WR - 1, CAR_Y + WHEEL_CY - WR - 1
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
SYNC = [0, 45, 90, 93, 96, 99, 101, 113, 150, 152, 180, 231, 232, 270, 330, 360]   # frames that must start a new drawing


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


# ------------------------------------------------------------------ clean hero tyre (hook, zoom, fresh vs worn)
@lru_cache(None)
def tyre_clean(n, lit=True, depth=None, bar_h=None, wear=0.0, pulse=0, nb=18):
    """Side-on tyre: chunky chipped tread blocks, navy outline, ONE rim-light colour (GLH),
    flat shadow tones (no speckle), big wear bar in the top groove. wear=1 -> blocks level with bar."""
    Rr = n / 2 - 1.0
    D = depth or max(6, int(round(0.2 * Rr)))
    Hb = bar_h or max(3, int(round(D * 0.42)))
    c = (n - 1) / 2
    yy, xx = np.mgrid[0:n, 0:n]
    dx, dy = xx - c, yy - c
    r = np.hypot(dx, dy)
    th = np.arctan2(-dy, dx) % (2 * np.pi)
    nrm = np.cos(th - 3 * np.pi / 4)
    phase = ((th - np.pi / 2) / (2 * np.pi / nb)) % nb
    blk = np.floor(phase).astype(int) % nb
    fr = phase - np.floor(phase)
    rng = np.random.default_rng(7 + n)
    lo = 0.16 + rng.random(nb) * 0.06
    hi = 0.84 - rng.random(nb) * 0.06
    base = Rr - D                                         # groove floor radius
    top = Rr - wear * (D - Hb)                            # block top radius (wears down to the bar)
    chipL = rng.random(nb) < 0.6                          # chipped corners, different per block
    chipR = rng.random(nb) < 0.6
    dent = rng.random(nb) * 0.6 + 0.2                     # small bite out of the block face
    in_blk = (fr > lo[blk]) & (fr < hi[blk])
    edge_l, edge_r = fr - lo[blk], hi[blk] - fr
    rtop = top - np.where((edge_l < 0.07) & chipL[blk], 1.2, 0) - np.where((edge_r < 0.07) & chipR[blk], 1.2, 0)
    rtop = rtop - np.where((np.abs(fr - dent[blk]) < 0.04) & (wear < 0.9), 0.8, 0)
    spr = np.full((n, n), T, np.uint8)
    body = r <= base
    tread = (r > base) & (r <= rtop) & in_blk
    spr[tread] = R1
    spr[tread & (nrm < -0.3)] = R0
    spr[tread & (r > rtop - 1.2) & (nrm > -0.2)] = GLH          # the single rim light
    g0 = ((phase < lo[0]) | (phase > nb - (1 - hi[nb - 1]))) & (r > base) & (r <= base + Hb)
    g0 &= ~in_blk
    side = body & (r >= 0.6 * Rr)
    spr[side] = R1
    spr[side & (nrm < -0.25)] = R0
    spr[side & (r >= base - 1.2) & (nrm > -0.2)] = R2            # tread shoulder catches light
    spr[side & (r < 0.62 * Rr + 0.6)] = R0                       # bead line
    if n >= 120:                                                  # sipes + raised sidewall lettering
        mid = (fr > lo[blk] + 0.3 * (hi[blk] - lo[blk])) & (fr < hi[blk] - 0.3 * (hi[blk] - lo[blk]))
        zig = np.abs(((r - base) / 3) % 2 - 1) < 0.5
        sip = tread & (np.abs(fr - 0.5) < 0.012 + 0.012 * zig) & (r < rtop - 2)
        spr[sip] = R0
        ring = side & (np.abs(r - 0.78 * Rr) < 1.6) & (((th * Rr * 0.78 / 5).astype(int) % 3) != 0)
        spr[ring & (nrm > -0.25)] = R2
        spr[ring & (nrm <= -0.25)] = R1
        spr[side & (np.abs(r - 0.7 * Rr) < 0.6)] = R0
    if n >= 40:                                                   # TWI triangle aimed at the bar groove
        a0, a1 = base - 0.2 * Rr, base - 0.06 * Rr
        tri = (dy < 0) & (r >= a0) & (r < a1) & (np.abs(dx) <= (a1 - r) * 0.8)
        spr[tri] = GY
    lip = (r >= 0.53 * Rr) & (r < 0.6 * Rr)
    spr[lip] = GY
    spr[lip & (nrm > 0.25)] = WH
    spr[lip & (nrm < -0.3)] = FARS
    dish = r < 0.53 * Rr
    spr[dish] = FARS
    sp = (np.degrees(th) - 18) % 72
    hole = dish & (r > 0.16 * Rr) & (r < 0.46 * Rr) & (sp > 13) & (sp < 59)
    spr[hole] = K
    spr[dish & ~hole & (r >= 0.12 * Rr) & (nrm > 0.3)] = GY
    hub = r < 0.13 * Rr + 0.5
    spr[hub] = GY
    spr[hub & (nrm > 0.2)] = WH
    if lit:
        a, b = (BY, BO) if pulse == 0 else (BO, BY)
        spr[g0] = a
        spr[g0 & (r <= base + max(1, Hb * 0.35))] = b if pulse == 0 else BY
        if pulse == 1:
            spr[g0 & (r > base + Hb - 1.0)] = BY
    else:
        spr[g0] = R1
    return outline(pad(spr))


def bar_xy(n, cx, cy, depth=None, bar_h=None):
    """Screen position of the bar centre for a tyre_clean drawn centred at (cx, cy)."""
    Rr = n / 2 - 1.0
    D = depth or max(6, int(round(0.2 * Rr)))
    Hb = bar_h or max(3, int(round(D * 0.42)))
    return cx, int(round(cy - (Rr - D + Hb / 2)))


def put_tyre(cv, spr, cx, cy):
    blit(cv, spr, cx - spr.shape[1] // 2, cy - spr.shape[0] // 2)


# haze: the street recedes into soft blues so the hero tyre reads first
_HL = np.array([lum(i) for i in range(32)])
HAZE = np.where(_HL > 0.5, GLH, np.where(_HL > 0.24, FAR, FARS)).astype(np.uint8)
for _c in (SKY1, SKY2, CLD, GLH):
    HAZE[_c] = _c


def haze_bg(t, k, ground=True):
    st = street(t, k, dist=STOP_D)
    cv = HAZE[st]
    if ground:
        cv[FRONT_Y:] = st[FRONT_Y:]
    return cv

# ------------------------------------------------------------------ scenes
HOOK_N, HOOK_C = 82, (91, 173)          # tyre fills ~60% of the frame width
FLUSH_F = 231                           # "...level with the BAR" (7.70 s, VO syllable onset) -> flash + click
FLUSH_T = FLUSH_F / FPS


def scene_hook(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = haze_bg(t, k)
    cx, cy = HOOK_C
    pulse = 1 if (t >= 1.5 and k % 2) else 0
    R(cv, cx - 34, cy + 40, cx + 34, cy + 42, ASPD)                 # contact shadow on the pavement
    for x in range(cx - 38, cx + 39, 3):
        P(cv, x, cy + 43, ASPD)
    put_tyre(cv, tyre_clean(HOOK_N, True, pulse=pulse), cx, cy)
    bx, by = bar_xy(HOOK_N, cx, cy)
    if t >= 1.5:                                                    # ping: sparkle burst
        for i, (sx, sy) in enumerate(((-7, -3), (7, -4), (-9, 1), (9, 0), (0, -8))):
            if (k + i) % 3 != 0:
                P(cv, bx + sx, by + sy, BY)
    blit(cv, ARROW_DN, bx - 4, by - 18 + (k % 2))
    pose = 'point' if t >= 1.3 else 'talkR'
    blit(cv, outline(pad(stand(mouth(f), pose))), -1, cy + 44 - 61)
    text_box(cv, 'hook_headline', ['HIDDEN'], (14, 8, 120, 31), size=16)
    text_box(cv, 'hook_headline_2', ['BAR'], (38, 33, 96, 56), size=16, fg=BY if t >= 1.5 and k % 2 else WH)
    if 1.5 <= t < 1.6:
        cv = np.roll(cv, 1, axis=1)
    return cv


ZOOM_STEPS = [(3.0, 124), (3.1, 176), (3.2, 248), (3.3, 330)]


def scene_zoom(f):
    """3.0-5.0 s: clean stepped re-draws (not upscales) closing in on the barred groove."""
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    n = [nn for ts, nn in ZOOM_STEPS if t >= ts][-1]
    cv = haze_bg(t, k, ground=False)
    Rr = n / 2 - 1
    target_bar_y = 104
    D = max(6, int(round(0.2 * Rr))); Hb = max(3, int(round(D * 0.42)))
    cy = int(round(target_bar_y + (Rr - D + Hb / 2)))
    pulse = k % 2 if t >= 3.3 else 0
    put_tyre(cv, tyre_clean(n, True, pulse=pulse), 67, cy)
    bx, by = bar_xy(n, 67, cy)
    if n == 330:
        blink = t >= 4.4 and (k % 3 != 2)
        m = text_mask('TWI', 8)
        ys, xs = np.nonzero(m)
        w = int(m.any(0).nonzero()[0].max() + 1)
        ty = by + 42
        cv[ty + ys + 1, bx - w // 2 + xs + 1] = R0
        cv[ty + ys, bx - w // 2 + xs] = BY if blink else R2
        if blink:                                                   # triangle lights with the text
            for i in range(6):
                R(cv, bx - i, by + 30 + i, bx + i, by + 30 + i, BY)
        TEXT_REPORT['zoom_twi_mark'] = dict(lines=['TWI'], plate='sidewall (embossed mark, not a caption)',
                                            widths=[w], inner_w=W, fits=True,
                                            contrast=round(float(contrast(BY, R1)), 2))
        if 3.35 <= t < 3.75:                                        # one clean scan pass
            sx = 4 + int((t - 3.35) / 0.4 * 126)
            R(cv, sx, 60, sx, 200, CYAN)
        hud_brackets(cv, bx - 14, by - 12, bx + 14, by + 12, c=CYAN, n=4)
        a = k % 2
        line(cv, (bx, 50), (bx, by - 16 - a), WH, 2)
        for i in range(4):
            R(cv, bx - i, by - 18 - a + i, bx + 1 + i, by - 18 - a + i, WH)
        text_box(cv, 'reveal_label', ['TREAD WEAR', 'INDICATOR'], (8, 14, 126, 46))
    return cv


def tread_closeup(t, k):
    """5.0-6.0 s cross-section: chipped irregular blocks, grooves lighter than blocks, big pulsing bar."""
    cv = np.full((H, W), B0, np.uint8)
    top, floor = 78, 150
    grooves = [(16, 27), (55, 79), (108, 119)]
    rng = np.random.default_rng(5)
    edges = [-1] + [g for gg in grooves for g in gg] + [W]
    blocks = [(edges[i] + 1, edges[i + 1] - 1) for i in range(0, len(edges), 2)]
    lay = np.full((H, W), T, np.uint8)
    for gx0, gx1 in grooves:                                        # grooves: lighter than the blocks
        R(lay, gx0, top + 6, gx1, floor, R2)
        R(lay, gx0, top + 6, gx0 + 1, floor, FAR)
        R(lay, gx1, top + 10, gx1, floor, R1)
    for bi, (x0, x1) in enumerate(blocks):
        R(lay, x0, top, x1, floor, R1)
        x = x0
        while x <= x1:                                              # ragged top, 0-2 px steps
            w = int(rng.integers(3, 7)); d = int(rng.integers(0, 3))
            if d:
                R(lay, x, top, min(x1, x + w - 1), top + d - 1, T)
            R(lay, x, top + d, min(x1, x + w - 1), top + d, GLH)    # single rim light
            x += w
        for cy_ in (top, top + 1, top + 2):                         # chipped corners
            if rng.random() < 0.7: lay[cy_, x0] = T
            if rng.random() < 0.7: lay[cy_, x1] = T
        for _ in range(2):                                          # bites out of the side walls
            yy = int(rng.integers(top + 8, floor - 10))
            side = x0 if rng.random() < 0.5 else x1
            R(lay, side, yy, side, yy + int(rng.integers(1, 4)), T)
        R(lay, x1 - 2, top + 4, x1 - 1, floor - 1, R0)              # flat shadow side, no speckle
        if x1 - x0 > 12:
            cx = (x0 + x1) // 2
            for i, yy in enumerate(range(top + 10, top + 40)):      # zig-zag sipe
                lay[yy, cx + ((i // 3) % 2)] = R0
    gx0, gx1 = grooves[1]
    bh = 30                                                         # 2-3x the old bar
    pulse = k % 2
    a, b = (BY, BO) if pulse == 0 else (BO, BY)
    R(lay, gx0 + 2, floor - bh, gx1 - 2, floor, a)
    R(lay, gx0 + 2, floor - 8, gx1 - 2, floor, b if pulse == 0 else BO)
    R(lay, gx0 + 2, floor - bh, gx1 - 2, floor - bh + 2, BY)
    lay[floor - bh, gx0 + 2] = T; lay[floor - bh, gx1 - 2] = T
    lay = outline(lay)
    m = lay != T
    cv[m] = lay[m]
    R(cv, 0, floor + 1, W - 1, 214, R1)                             # sidewall
    R(cv, 0, floor + 1, W - 1, floor + 3, R0)
    for x in range(0, W):
        if (x // 5) % 3 != 1: P(cv, x, floor + 9, R2)
    R(cv, 0, 205, W - 1, 214, R0)
    R(cv, 0, 215, W - 1, H - 1, B0)
    return cv, (gx0 + gx1) // 2, floor


def scene_tread(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv, gx, floor = tread_closeup(t, k)
    settle = 2 if t < 5.07 else 0
    blink = (k % 3 != 2)
    for i in range(5):
        R(cv, gx - i, 160 + i, gx + i, 160 + i, BY if blink else GY)
    m = text_mask('TWI', 8)
    ys, xs = np.nonzero(m)
    w = int(m.any(0).nonzero()[0].max() + 1)
    cv[168 + ys + 1, gx - w // 2 + xs + 1] = R0
    cv[168 + ys, gx - w // 2 + xs] = BY if blink else R2
    TEXT_REPORT['reveal_twi_mark'] = dict(lines=['TWI'], plate='sidewall (embossed mark, not a caption)',
                                          widths=[w], inner_w=W, fits=True, contrast=round(float(contrast(BY, R1)), 2))
    a = k % 2
    line(cv, (gx, 50), (gx, floor - 36 - a), WH, 2)
    for i in range(4):
        R(cv, gx - i, floor - 38 - a + i, gx + 1 + i, floor - 38 - a + i, WH)
    hud_brackets(cv, 3, 50, 131, 222, n=8)
    text_box(cv, 'reveal_label', ['TREAD WEAR', 'INDICATOR'], (8, 14, 126, 46))
    if settle:
        cv = np.vstack([cv[settle:], np.full((settle, W), B0, np.uint8)])
    return cv


PROG_N, PROG_D, PROG_HB, PROG_NB = 64, 12, 5, 10
PROG_C = ((33, 132), (101, 132))
WEAR_STEPS = [(6.0, 0.0), (6.35, 0.18), (6.7, 0.36), (7.0, 0.52), (7.3, 0.7), (7.5, 0.85), (FLUSH_T, 1.0)]


def scene_progress(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = haze_bg(t, k)
    wear = [w for ts, w in WEAR_STEPS if t >= ts - 1e-6][-1]
    flush = f >= FLUSH_F
    for (cx, cy), wv in zip(PROG_C, (0.0, wear)):
        R(cv, cx - 26, cy + 31, cx + 26, cy + 32, ASPD)
        put_tyre(cv, tyre_clean(PROG_N, True, PROG_D, PROG_HB, wv, pulse=k % 2, nb=PROG_NB), cx, cy)
    cx, cy = PROG_C[1]
    bx, by = bar_xy(PROG_N, cx, cy, PROG_D, PROG_HB)
    if f == FLUSH_F:                                                # the one-frame white flash
        spr = tyre_clean(PROG_N, True, PROG_D, PROG_HB, 1.0, nb=PROG_NB)
        ys, xs = np.nonzero(spr != T)
        y0, x0 = cy - spr.shape[0] // 2, cx - spr.shape[1] // 2
        cv[np.clip(y0 + ys, 0, H - 1), np.clip(x0 + xs, 0, W - 1)] = WH
    for (tx, ty) in PROG_C:                                         # bar-top level guide on both tyres
        if f == FLUSH_F and tx == cx:
            continue
        _, tby = bar_xy(PROG_N, tx, ty, PROG_D, PROG_HB)
        ly = tby - PROG_HB // 2 - 1
        for x in range(tx - 14, tx + 15, 3):
            R(cv, x, ly, x + 1, ly, WH if (flush or tx != cx) else GLH)
    text_box(cv, 'prog_new', ['NEW'], (4, 62, 61, 84), size=16)
    text_box(cv, 'prog_worn', ['WORN'], (64, 62, 133, 84), size=16, fg=BY if flush else WH)
    if t >= FLUSH_T + 0.1:
        text_box(cv, 'prog_caption', ['FLUSH = AT THE', 'LEGAL MINIMUM', 'WHERE YOU LIVE'], (4, 186, 130, 228), lead=4)
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
    yes, no = (4, 58, 66, 86), (69, 58, 131, 86)
    picked = t >= 11.75
    text_box(cv, 'poll_yes', ['YES'], yes, size=16, border=BY if picked else TL, fg=BY if picked else WH)
    text_box(cv, 'poll_no', ['NO'], no, size=16, border=MG)
    if t >= 11.3:
        cx = [(110, 100), (80, 90), (56, 82), (38, 76)][min(3, int((t - 11.3) / 0.12))]
        blit(cv, CURSOR, cx[0] - 2, cx[1] - 2)
    if t >= 12.0:                                    # NEXT EPISODE card, final 1.0 s only (pops in whole)
        text_box(cv, 'next_card', ['NEXT EPISODE', 'FOLLOW'], (6, 96, 128, 128), border=MG)
    return cv


def frame_idx(f):
    k = KEY_OF[f]
    t = k / FPS
    if t < 3.0:
        return scene_hook(k)
    if t < 5.0:
        return scene_zoom(k)
    if t < 6.0:
        return scene_tread(k)
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
            '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', '12', *color, '-r', str(FPS),
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
