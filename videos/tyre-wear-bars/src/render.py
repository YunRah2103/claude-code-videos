"""Tyre wear bars: native 135x240 indexed pixel renderer (16-colour palette).

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
import pix  # noqa: E402  (reuse the approved main-guy sprite + poses)

W, H, S, FPS = 135, 240, 8, 30
DUR = 13.0
NF = int(DUR * FPS)
T = 255  # transparent index

PAL_HEX = ['#120e1a', '#1f2236', '#2e3550', '#4a5677',   # 0 ink, 1-3 garage blues
           '#24202e', '#3a3346', '#6a5d6e',              # 4-6 rubber shadow/mid/highlight
           '#7a2f7e', '#d64fb0',                         # 7-8 neon purple/magenta
           '#c88a5e', '#8e5a4e',                         # 9-10 skin / skin shadow
           '#d8d4cc', '#9aa3b8',                         # 11-12 white, cool grey
           '#ffe040', '#e0702a',                         # 13-14 wear bar yellow/orange
           '#44c2b0']                                    # 15 teal
K, B0, B1, B2, R0, R1, R2, PU, MG, SK, SS, WH, GY, BY, BO, TL = range(16)
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in PAL_HEX], np.uint8)

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
    sx1, sy1 = min(w, W - x), min(h, H - y)
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

# ------------------------------------------------------------------ tyre (side view, 64x64)
NB = 12


def _tyre_geom(n=64):
    c = (n - 1) / 2
    yy, xx = np.mgrid[0:n, 0:n]
    dx, dy = xx - c, yy - c
    r = np.hypot(dx, dy)
    th = np.arctan2(-dy, dx) % (2 * np.pi)
    return xx, yy, dx, dy, r, th


@lru_cache(None)
def tyre_core(lit=False):
    n = 64
    xx, yy, dx, dy, r, th = _tyre_geom(n)
    rng = np.random.default_rng(11)
    lo = 0.20 + rng.random(NB) * 0.07          # irregular groove edges per block
    hi = 0.80 - rng.random(NB) * 0.07
    ro = 31.6 - rng.integers(0, 2, NB)         # ragged block heights
    phase = ((th - np.pi / 2) / (2 * np.pi / NB)) % NB
    blk = np.floor(phase).astype(int) % NB
    fr = phase - np.floor(phase)
    nrm = np.cos(th - 3 * np.pi / 4)           # light from upper-left
    spr = np.full((n, n), T, np.uint8)
    in_blk = (fr > lo[blk]) & (fr < hi[blk])
    edge = np.minimum(fr - lo[blk], hi[blk] - fr)
    rout = ro[blk] - (edge < 0.06) * 1.0       # staircase bevel at block corners
    tread = (r >= 26) & (r <= rout) & in_blk
    spr[tread] = R1
    spr[tread & (r >= rout - 1.3) & (nrm > 0.25)] = R2
    spr[tread & (nrm < -0.45)] = R0
    groove_floor = (r >= 26) & (r < 27.6) & ~in_blk
    spr[groove_floor] = R0
    # the wear bar, inside the top groove (block boundary 0 is centred at 90 degrees)
    g0 = ((phase < 0.27) | (phase > NB - 0.27)) & (r >= 27.6) & (r < 29.7)
    spr[g0] = (BY if lit else R1)
    if lit:
        spr[g0 & (r >= 28.8)] = BY
        spr[g0 & (r < 28.8)] = BO
    side = (r >= 18) & (r < 26)
    spr[side] = R1
    spr[side & (r >= 23) & (nrm > 0.35)] = R2
    shadow = side & (nrm < -0.3)
    spr[shadow] = R0
    tex = shadow & (np.vectorize(h01)(xx, yy, 3) < 0.07)  # rubber texture only in shadow
    spr[tex] = K
    spr[(r >= 18) & (r < 19.2)] = R0                       # bead seat
    # TWI triangle on the sidewall, aimed at the barred groove
    tri = (dy < 0) & (r >= 20.5) & (r < 24.5) & (np.abs(dx) <= (24.5 - r) * 0.75)
    spr[tri] = GY
    lip = (r >= 16) & (r < 18)
    spr[lip] = GY
    spr[lip & (nrm > 0.2)] = WH
    spr[lip & (nrm < -0.3)] = B2
    dish = r < 16
    spr[dish] = B2
    sp = (np.degrees(th) - 18) % 72
    hole = dish & (r > 5.5) & (r < 14) & (sp > 14) & (sp < 58)
    spr[hole] = K
    spr[hole & (r > 12.5) & (nrm < 0)] = B1
    spoke = dish & ~hole & (r >= 4)
    spr[spoke & (nrm > 0.3)] = GY
    hub = r < 4
    spr[hub] = GY
    spr[hub & (nrm > 0.2)] = WH
    for k in range(5):
        a = np.radians(18 + 72 * k + 36)
        P(spr, int(round(31.5 + 2.6 * math.cos(a))), int(round(31.5 - 2.6 * math.sin(a))), K)
    return spr


@lru_cache(None)
def tyre(lit=False):
    return outline(pad(tyre_core(lit)))


@lru_cache(None)
def tyre_rot(i):
    """16 pre-baked angles (22.5 degree steps), RotSprite-style."""
    return outline(pad(rotsprite(tyre_core(False), i * 22.5))) if i else tyre(False)

# ------------------------------------------------------------------ presenter (reuses pix.guy)
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
    g = stand(expr, pose)
    s = np.full((54, 48), T, np.uint8)
    s[:40] = g[:40]
    # knees up and spread (jeans), hands stay in front
    for x0, x1 in ((13, 23), (25, 35)):
        R(s, x0, 35, x1, 43, R1)
        R(s, x0 + 1, 35, x1 - 1, 35, R2)
        R(s, x0, 36, x0 + 1, 36, R2)
        R(s, x1, 38, x1, 43, R0)
        R(s, x0, 42, x1, 43, R0)
        for x, y in ((x0, 35), (x1, 35), (x0, 43), (x1, 43)):
            s[y, x] = T
    R(s, 23, 41, 24, 43, R0)
    for x0, x1 in ((15, 21), (27, 33)):
        R(s, x0, 44, x1, 48, R1)
        R(s, x1 - 1, 44, x1, 48, R0)
    for x0, x1 in ((11, 21), (27, 37)):
        R(s, x0, 49, x1, 51, WH)
        R(s, x0, 51, x1, 51, GY)
        R(s, x0 + 1, 49, x0 + 3, 49, GY)
    hands = g[:46] == SK
    hands[:35] = False
    s[:46][hands] = SK
    return outline(s)

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
OILCAN = outline(pad(_spr([
    '      gg  ',
    '     gt   ',
    ' tttttt   ',
    'tTTTTTTt  ',
    'tTTTTTTtk ',
    'tTTTTTTt  ',
    'tttttttt  ',
    ' kkkkkk   '], {'t': TL, 'T': B2, 'g': GY, 'k': B1})))
TOOLBOX = outline(pad(_spr([
    '   bbbbb    ',
    '  bb   bb   ',
    'pppppppppppp',
    'pMMMMMMMMMMp',
    'pMMMgggMMMMp',
    'pppppppppppp',
    'PPPPPPPPPPPP'], {'p': PU, 'M': PU, 'g': GY, 'b': B2, 'P': B1})))


@lru_cache(None)
def oilcan_tilted():
    return outline(rotsprite(pad(OILCAN[1:-1, 1:-1], 3), -22))

# ------------------------------------------------------------------ garage background (calm)
FLOOR = 172


@lru_cache(None)
def garage(neon_on=True):
    cv = np.full((H, W), B1, np.uint8)
    # ceiling shadow with a staircase edge
    for x in range(W):
        R(cv, x, 0, x, 3 + (x // 9) % 2, B0)
    # garage door: dark with bold slats (shading steps, no speckle)
    R(cv, 8, 66, 126, FLOOR - 1, B0)
    for y in range(74, FLOOR - 1, 12):
        R(cv, 9, y, 125, y, B1)
    R(cv, 8, 66, 126, 66, B2)
    R(cv, 7, 66, 7, FLOOR - 1, B2)
    R(cv, 127, 66, 127, FLOOR - 1, B0)
    # floor
    R(cv, 0, FLOOR, W - 1, H - 1, B1)
    R(cv, 0, FLOOR, W - 1, FLOOR, B2)
    R(cv, 0, 214, W - 1, H - 1, B0)
    line(cv, (30, FLOOR + 1), (0, 205), B0)
    line(cv, (104, FLOOR + 1), (134, 205), B0)
    # neon tube (prop 1)
    c1, c2 = (MG, PU) if neon_on else (PU, PU)
    R(cv, 26, 58, 108, 59, c1)
    R(cv, 24, 57, 25, 60, PU); R(cv, 109, 57, 110, 60, PU)
    R(cv, 26, 60, 108, 60, c2)
    blit(cv, TOOLBOX, 10, FLOOR - 6)                # prop 2 (far left, clear of the tyre)
    return cv

# ------------------------------------------------------------------ timeline / stepping
HOLDS = [3, 2, 4, 3, 3, 2, 4, 3, 2]
SYNC = [0, 45, 90, 96, 180, 239, 270, 330, 360]   # frames that must start a new drawing


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

# ------------------------------------------------------------------ scenes
TX_END, TY = 64, FLOOR - 63
BAR_XY = (TX_END + 32, TY + 3)


def scene_hook(f, text=True):
    t = f / FPS
    cv = garage(True).copy()
    # roll in from the right, 0.0-0.8 s, pre-baked angles only
    p = min(1.0, t / 0.8)
    x = TX_END + int(round((150 - TX_END) * (1 - p) ** 2))
    moving = x != TX_END
    y = TY - (1 if 0.8 <= t < 0.95 else 0)
    ang = int(round(-(x - TX_END) / (2 * math.pi * 32) * 16)) % 16
    lit = t >= 1.5
    # ragged contact shadow
    R(cv, x + 8, FLOOR + 1, x + 55, FLOOR + 2, B0)
    R(cv, x + 14, FLOOR + 3, x + 49, FLOOR + 3, B0)
    spr = tyre_rot(ang) if moving else tyre(lit)
    blit(cv, spr, x - 1, y - 1)
    bx, by = BAR_XY
    if lit and text:
        k = KEY_IDX[KEY_OF[f]]
        for i, (sx, sy) in enumerate(((-6, -3), (6, -4), (-8, 2), (8, 1))):
            if (k + i) % 3 != 0:
                P(cv, bx + sx, by + sy, BY)
        if t >= 1.7:
            blit(cv, ARROW_DN, bx - 4, by - 17 + (k % 2))
    blit(cv, oilcan_tilted(), 112, FLOOR + 14)
    pose = 'point' if t >= 1.45 else ('talkR' if t >= 0.5 else 'down')
    blit(cv, crouch(mouth(f), pose), 6, FLOOR + 16 - 54)
    if text:
        box = (14, 10, 120, 53)
        if t < 0.07:
            grow_plate(cv, box, 0.5)
        else:
            text_box(cv, 'hook_headline', ['HIDDEN', 'BAR'], box, size=16)
    # whole-pixel camera nudge on the ping
    if 1.5 <= t < 1.6:
        cv = np.roll(cv, 1, axis=1)
    elif 1.6 <= t < 1.7:
        cv = np.roll(cv, -1, axis=0)
    return cv


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


def scene_reveal(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    if t < 3.2:                          # stepped punch-in: x2 then x4 (integer nearest)
        src = scene_hook(89, text=False)
        z = 2 if t < 3.1 else 4
        cw, ch = -(-W // z), H // z
        bx, by = BAR_XY
        x0 = min(max(0, bx - cw // 2), W - cw); y0 = min(max(0, by - ch // 2 + 6), H - ch)
        crop = src[y0:y0 + ch, x0:x0 + cw]
        return np.repeat(np.repeat(crop, z, 0), z, 1)[:H, :W].copy()
    cv, gx, floor = tread_closeup(t, k)
    settle = 3 if t < 3.27 else (1 if t < 3.37 else 0)   # whole-pixel camera settle
    # TWI mark (embossed), blinking with uneven holds after 4.4 s
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
    if t >= 3.5:
        a = 0 if k % 2 else 1
        line(cv, (gx, 52), (gx, floor - 22 - a), WH, 2)
        for i in range(4):
            R(cv, gx - i, floor - 21 - a - 4 + i + 1, gx + 1 + i, floor - 21 - a - 4 + i + 1, WH)
    box = (8, 14, 126, 46)
    if t < 3.4:
        grow_plate(cv, box, 0.55)
    else:
        text_box(cv, 'reveal_label', ['TREAD WEAR', 'INDICATOR'], box)
    if settle:
        cv = np.vstack([cv[settle:], np.full((settle, W), B0, np.uint8)])
    return cv


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


def scene_progress(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = garage(k % 7 != 3).copy()
    R(cv, 0, 62, W - 1, FLOOR + 6, B0)
    full = 72
    bar_top_depth = 9
    # worn tread steps down unevenly, reaching flush at 7.97 s (the click)
    steps = [(6.0, 72), (6.35, 63), (6.6, 52), (6.9, 43), (7.15, 35), (7.45, 26), (7.7, 17), (7.97, 9)]
    depth = [d for ts, d in steps if t >= ts][-1]
    worn_frac = (full - depth) / (full - bar_top_depth)
    flush = t >= 7.97
    tread_panel(cv, 4, 72, 61, full, 0.0, 'NEW', False, k)
    bar_y = tread_panel(cv, 70, 72, 61, depth, worn_frac, 'WORN', flush and t < 8.4, k)
    if flush:                                   # level line across the worn panel
        for x in range(71, 130, 3):
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


def scene_payoff(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = garage(True).copy()
    rows = [(9.0, 'pay_find', ['FIND TWI'], icon_twi),
            (9.37, 'pay_look', ['LOOK IN', 'THE GROOVE'], icon_groove),
            (9.8, 'pay_time', ['10 SECONDS'], icon_clock)]
    for i, (t0, name, lines, icon) in enumerate(rows):
        y = 20 + i * 38
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
    blit(cv, stand(mouth(f), 'point' if t < 10.2 else 'talkL'), 44, H - 62)
    blit(cv, oilcan_tilted(), 112, FLOOR + 14)
    return cv


def scene_end(f):
    t = f / FPS
    k = KEY_IDX[KEY_OF[f]]
    cv = garage(k % 5 != 2).copy()
    text_box(cv, 'end_question', ['HAVE YOU EVER', 'LOOKED FOR', 'YOURS?'], (8, 10, 126, 54))
    yes, no = (10, 66, 62, 90), (72, 66, 124, 90)
    if t < 11.07:
        grow_plate(cv, yes, 0.5, border=TL); grow_plate(cv, no, 0.5, border=MG)
    else:
        picked = t >= 11.75
        text_box(cv, 'poll_yes', ['YES'], yes, border=TL, bg=K if not picked else B1)
        text_box(cv, 'poll_no', ['NO'], no, border=MG)
        for (x0, y0, x1, y1), c in ((yes, TL), (no, MG)):
            R(cv, x0 + 4, y0 + 8, x0 + 9, y0 + 13, c); R(cv, x0 + 5, y0 + 9, x0 + 8, y0 + 12, K)
        if picked:
            R(cv, yes[0] + 5, yes[1] + 9, yes[0] + 8, yes[1] + 12, BY)
        cx = [(110, 120), (80, 104), (56, 92), (40, 84)][min(3, int((t - 11.3) / 0.12)) if t >= 11.3 else 0]
        if t >= 11.3:
            blit(cv, CURSOR, cx[0] - 10, cx[1] - 4)
    blit(cv, stand(mouth(f), 'shrug' if t < 11.9 else 'wave1' if k % 2 else 'wave2'), 44, H - 62)
    if t >= 12.0:                                    # NEXT EPISODE card, final 1.0 s only
        y = [204, 184, 170][min(2, int((t - 12.0) / 0.07))]
        R(cv, 6, y, 128, y + 50, B2)
        R(cv, 7, y + 1, 127, y + 49, K)
        R(cv, 7, y + 1, 127, y + 3, MG)
        if y == 170:
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
