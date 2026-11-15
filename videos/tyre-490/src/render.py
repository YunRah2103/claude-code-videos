"""tyre-490: wireframe + ASCII + heat + HUD explainer (1080x1920, 30 fps).

All timing comes from beats.json. Phase 2: put aligned word times into
beats.json (words[].t, est=false); beat starts then follow their anchor words.

  python render.py still OUTDIR 0 2.5 4.5
  python render.py video OUT.mp4 [END [START]]
"""
import json, math, os, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, 'beats.json')))
W, H = B['size']; FPS = B['fps']
DUR = 17.0  # literal for tools/video.py preview; must match beats.json
assert abs(DUR - B['dur']) < 1e-6
PREVIEW = os.environ.get('PREVIEW', '1') == '1'


def resolve_beats(b):
    """Estimated times now; aligned anchor-word times in phase 2."""
    beats = [dict(x) for x in b['beats']]
    for x in beats[1:]:
        w = b['words'][x['anchor_word']]
        if not w.get('est', True):
            x['start'] = w['t']
    for a, n in zip(beats, beats[1:]):
        a['end'] = n['start']
    return {x['id']: x for x in beats}


BEAT = resolve_beats(B)
def T(i): return BEAT[i]['start']


# ---- easing (same family everywhere) ------------------------------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, d): return clamp((t - a) / d)
def eo(x): return 1 - 2 ** (-10 * x) if x < 1 else 1.0       # expo out
def io(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def oc(x): return 1 - (1 - x) ** 3
def bump(t, t0, rise=.06, fall=.45):
    return prog(t, t0, rise) * (1 - prog(t, t0 + rise, fall))


# ---- palette / fonts ----------------------------------------------------
WHITE = np.array([.92, .95, 1.0], np.float32)
FAR = np.array([.50, .56, .66], np.float32)
ACC = np.array([1.0, .36, .09], np.float32)        # the single heat accent
HOT = np.array([1.0, .86, .62], np.float32)
BG = np.array([.018, .02, .028], np.float32)
FD = '/usr/share/fonts/truetype/jetbrains-mono/'
def F(style, size): return ImageFont.truetype(FD + f'JetBrainsMono-{style}.ttf', size)
F_HEAD, F_VAL, F_UNIT = F('ExtraBold', 84), F('Bold', 120), F('Bold', 56)
F_LAB, F_CHIP, F_TAG = F('Regular', 30), F('Bold', 40), F('Regular', 24)
TXT_X = 64                                       # safe text: x < 918, 230 < y < 1190

# ---- timeline (all anchored to beat starts) -----------------------------
t1, t2, t3, t4, t5, t6 = (T(x) for x in ('rpm', 'g_force', 'belts', 'xray', 'flaw', 'poll'))
STAMP = t2 + 1.15                                 # 5,300 g slam
FLAWHIT = t5 + 1.1                                # flaw pulse punch
LOOP = DUR - .5                                   # poll out, headline back in (loops to frame 1)
TRANSITIONS = [t1, t2, STAMP, t3, t4, t5, t6, LOOP - .05]


def omega(t):                                    # apparent spin, rad/s (readable, not 68 rev/s)
    if t < t1: return 15.0
    if t < t4: return 11.0 + 5.0 * io(prog(t, t1, 1.2))
    if t < t5: return 16 - 14.8 * eo(prog(t, t4, .8))
    if t < t6: return 1.2 - 1.08 * prog(t, t5, .3)
    return .12 + 14.88 * io(prog(t, t6, DUR - .3 - t6))


_TT = np.linspace(0, DUR, int(DUR * 600) + 1)
_PHI = np.concatenate([[0], np.cumsum([omega(x) for x in _TT[1:]]) * (_TT[1] - _TT[0])])
def phi(t): return float(np.interp(t, _TT, _PHI))


def _heat1(t):
    h = .3 + .35 * io(prog(t, t1, t2 - t1)) + .35 * io(prog(t, t2, STAMP - t2))
    return min(1.2, h + .5 * bump(t, STAMP, .05, .6))


def heat(t):
    if t < t4: return _heat1(t)
    h = _heat1(t4) + (.12 - _heat1(t4)) * eo(prog(t, t4, .6))
    return h + .18 * io(prog(t, t6, DUR - t6))   # ends at .3 = frame-1 value


def stretch(t):                                  # EXAGGERATED tread growth
    return .085 * io(prog(t, t1 + .25, .9)) * (1 + .25 * bump(t, STAMP, .05, .5)) * (1 - io(prog(t, t3, .5)))


def streak_amp(t):
    a = .6 + 1.1 * (1 - eo(prog(t, 0, 1.1)))
    a -= .28 * eo(prog(t, t3, .5)) + .14 * eo(prog(t, t4, .5))
    a += .27 * eo(prog(t, t6, .5)) + 1.25 * io(prog(t, DUR - .6, .6))
    return a


#      yaw   pitch  roll  dist  cx-off cy-off
S0 = (1.5, -.3, .22, 2.7, 0, 140)
CAMKEYS = [(0, .75, eo, (.95, -.2, 0, 4.0, 0, 0)),
           (t1, 1.6, io, (.7, -.2, 0, 3.6, 0, 0)),
           (t2, 2.0, io, (1.08, -.2, 0, 3.9, 0, 0)),
           (t3, .8, eo, (.9, -.25, .03, 1.9, -20, 430)),          # dolly into the tread
           (t3 + .8, 2.6, io, (1.15, -.32, -.03, 1.75, -40, 450)),
           (t4, .8, eo, (.28, -.08, 0, 3.6, -10, -10)),           # face-on for the scan
           (t4 + .8, 2.2, io, (.42, -.13, .02, 3.3, 0, 0)),
           (t5, .7, eo, (.55, -.15, -.02, 3.1, -10, 120)),          # push toward the flaw
           (t5 + .7, 1.3, io, (.62, -.18, 0, 2.8, 0, 140)),
           (t6, .8, eo, (1.0, -.2, 0, 4.1, 0, 0))]


def cam_base(t):
    st = list(S0)
    for tk, d, f, S in CAMKEYS:
        w = f(prog(t, tk, d))
        if w <= 0: break
        st = [a + (b - a) * w for a, b in zip(st, S)]
    yaw, pitch, roll, dist, cxo, cyo = st
    pitch += .06 * math.sin(.9 * t)
    roll += .035 * math.sin(1.3 * t)
    yaw += .05 * math.sin(.7 * t)
    dist -= .35 * bump(t, STAMP, .04, .5) + .25 * bump(t, FLAWHIT, .04, .45)
    amp = (22 * (1 - eo(prog(t, 0, 1.0))) + 3 + 26 * bump(t, STAMP, .02, .45) + 8 * bump(t, t1, .02, .3)
           + 14 * bump(t, FLAWHIT, .02, .35) + 6 * bump(t, t3, .02, .3))
    sx = amp * (math.sin(t * 61) * .6 + math.sin(t * 37 + 1) * .4)
    sy = amp * (math.sin(t * 53 + 2) * .6 + math.sin(t * 29) * .4)
    cx = 548 + cxo + 18 * math.sin(.5 * t) + sx
    cy = 1215 + cyo + 12 * math.sin(.65 * t + 1) + sy
    return yaw, pitch, roll, dist, cx, cy


def cam(t):
    w = io(prog(t, DUR - .6, .6))                  # last frames converge on frame 1
    a = cam_base(t)
    if w <= 0: return a
    b = cam_base(t - DUR)
    return tuple(x + (y - x) * w for x, y in zip(a, b))


# ---- geometry (generic tyre + 5-spoke wheel, no brand) -------------------
PROFILE = [(.70, -.36), (.80, -.42), (.93, -.43), (.99, -.36), (1, -.2), (1, 0), (1, .2), (.99, .36),
           (.93, .43), (.80, .42), (.70, .36)]


def ring(r, z, n=120): a = np.linspace(0, 2 * np.pi, n + 1); return np.c_[r * np.cos(a), r * np.sin(a), np.full(n + 1, z)]


def build():
    L = []                                        # (points, tag)
    for r, z in PROFILE:
        L.append((ring(r, z), 'tread' if r >= .99 else 'side'))
    for a in np.linspace(0, 2 * np.pi, 36, endpoint=False):
        L.append((np.array([[r * math.cos(a), r * math.sin(a), z] for r, z in PROFILE]), 'side'))
    for a in np.linspace(0, 2 * np.pi, 56, endpoint=False):  # chevron tread grooves
        p = [(a + .05, -.36), (a, -.12), (a + .04, 0), (a, .12), (a + .05, .36)]
        L.append((np.array([[math.cos(b), math.sin(b), z] for b, z in p]), 'tread'))
    for r, z in [(.66, -.33), (.66, .33), (.6, .3), (.6, -.3), (.2, -.12), (.09, -.14)]:
        L.append((ring(r, z, 72), 'rim'))
    for a in np.linspace(0, 2 * np.pi, 5, endpoint=False):
        for d in (-.13, .13):
            L.append((np.array([[.2 * math.cos(a + d * 1.6), .2 * math.sin(a + d * 1.6), -.12],
                                [.6 * math.cos(a + d * .45), .6 * math.sin(a + d * .45), -.28]]), 'rim'))
    return L


GEOM = build()


def project(P, yaw, pitch, roll, dist, cx, cy, f=1400.0):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    cyw, syw = math.cos(yaw), math.sin(yaw)
    x, z = x * cyw + z * syw, -x * syw + z * cyw
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp - z * sp, y * sp + z * cp
    cr, sr = math.cos(roll), math.sin(roll)
    x, y = x * cr - y * sr, x * sr + y * cr
    z = z + dist
    zc = np.maximum(z, .05)
    return np.c_[cx + f * x / zc, cy - f * y / zc], z


def spun(P, a, st, t):
    c, s = math.cos(a), math.sin(a)
    Q = P.copy()
    r = np.hypot(P[:, 0], P[:, 1])
    th = np.arctan2(P[:, 1], P[:, 0])
    m = r >= .985                                  # tread grows + ripples (exaggerated)
    grow = 1 + st * (1 + .35 * np.sin(8 * th + 40 * t)) * m
    Q[:, 0], Q[:, 1] = P[:, 0] * grow, P[:, 1] * grow
    return np.c_[Q[:, 0] * c - Q[:, 1] * s, Q[:, 0] * s + Q[:, 1] * c, Q[:, 2]]


def draw_runs(draws, xy, z, zc, fill_near, width, near_key, tag):
    seg = (z[:-1] + z[1:]) / 2
    cls = np.where(seg > zc + .12, 1, np.where(seg < zc - 1.6, 1, 0))
    cls[(z[:-1] < .3) | (z[1:] < .3)] = 2
    i = 0
    n = len(cls)
    while i < n:
        j = i
        while j + 1 < n and cls[j + 1] == cls[i]:
            j += 1
        if cls[i] != 2:
            pts = xy[i:j + 2].ravel().tolist()
            if cls[i] == 0:
                draws[near_key].line(pts, fill=fill_near, width=width)
            else:
                draws['far'].line(pts, fill=fill_near, width=2)
        i = j + 1


def wire_layers(t):
    """Motion-blurred wire layers (L images) via sub-frame accumulation."""
    yaw, pitch, roll, dist, cx, cy = cam(t)
    st = stretch(t)
    K = 6
    shutter = .6 / FPS
    acc = {k: Image.new('L', (W, H)) for k in ('near', 'far', 'tread', 'ground')}
    for k in range(K):
        ts = t - shutter * (k / (K - 1) - .5)
        a = -phi(ts)
        lay = {kk: Image.new('L', (W, H)) for kk in acc}
        dr = {kk: ImageDraw.Draw(v) for kk, v in lay.items()}
        v = int(255 * 1.7 / K)
        for P, tag in GEOM:
            xy, z = project(spun(P, a, st, ts), yaw, pitch, roll, dist, cx, cy)
            key = 'tread' if tag == 'tread' else 'near'
            draw_runs(dr, xy, z, dist, v, 3 if tag != 'rim' else 2, key, tag)
        s = phi(ts) % .7                         # rolling road: ground moves r*phi
        for xg in np.arange(-6.3, 6.3, .7) - s + .35:
            P = np.array([[xg, -1.0, zz] for zz in np.linspace(-2.2, 2.2, 9)])
            xy, z = project(P, yaw, pitch, roll, dist, cx, cy)
            fade = clamp(1 - abs(xg) / 6.3)
            draw_runs(dr, xy, z, dist + 9, int(v * .55 * fade), 2, 'ground', 'g')
        for zg in np.linspace(-2.2, 2.2, 7):
            P = np.array([[xx, -1.0, zg] for xx in np.linspace(-6.3, 6.3, 25)])
            xy, z = project(P, yaw, pitch, roll, dist, cx, cy)
            draw_runs(dr, xy, z, dist + 9, int(v * .35), 2, 'ground', 'g')
        for kk in acc:
            acc[kk] = ImageChops.add(acc[kk], lay[kk])
    contact, _ = project(np.array([[0, -1.0 - st, 0.0], [-.6, -.8, 0]]), yaw, pitch, roll, dist, cx, cy)
    top, _ = project(np.array([[0, 1.0 + st, .1], [.72, .72 + st, .3]]), yaw, pitch, roll, dist, cx, cy)
    return acc, contact, top, (yaw, pitch, roll, dist, cx, cy)


# ---- sparks (deterministic particles) ------------------------------------
_R = np.random.default_rng(7)
_N = 9000
SP = dict(tb=_R.uniform(-.6, DUR, _N), life=_R.uniform(.18, .55, _N), v=_R.uniform(700, 2100, _N),
          ang=_R.normal(0, .35, _N), keep=_R.uniform(0, 1, _N))


def spark_rate(t):
    gate = 1 - prog(t, t3 - .6, .3) + prog(t, LOOP, .15)
    r = .55 * (1 - prog(t, .6, .6)) + .55 * prog(t, DUR - .4, .4) + .12 + .25 * heat(t) + .9 * bump(t, STAMP, .02, .35)
    return r * gate


def draw_sparks(t, contact, sparks):
    (x0, y0), (x1, y1) = contact
    d = np.array([x1 - x0, y1 - y0]); d /= np.linalg.norm(d) + 1e-6
    m = (SP['tb'] <= t) & (t < SP['tb'] + SP['life'])
    idx = np.nonzero(m)[0]
    rates = np.array([spark_rate(x) for x in SP['tb'][idx]])
    idx = idx[SP['keep'][idx] < rates / 1.4]
    dr = ImageDraw.Draw(sparks)
    for i in idx:
        age = t - SP['tb'][i]
        a = SP['ang'][i] - .25
        ca, sa = math.cos(a), math.sin(a)
        vx, vy = (d[0] * ca - d[1] * sa) * SP['v'][i], (d[0] * sa + d[1] * ca) * SP['v'][i]
        def pos(tt): return x0 + vx * tt, y0 + vy * tt + 1600 * tt * tt
        k = age / SP['life'][i]
        c = (HOT * (1 - k) + ACC * k) * (1 - k ** 2)
        dr.line([pos(max(0, age - .028)), pos(age)], fill=tuple(int(255 * x) for x in c), width=3)
    return len(idx)


# ---- ASCII ----------------------------------------------------------------
CW, CH = 18, 30
COLS, ROWS = W // CW, H // CH
RAMP = " .'`-:;~=+*xo%#@"


def _atlas(chars):
    out = []
    f = F('Regular', 24)
    for c in chars:
        im = Image.new('L', (CW, CH)); ImageDraw.Draw(im).text((1, 1), c, font=f, fill=255)
        out.append(np.asarray(im, np.float32) / 255)
    return np.stack(out)


ATLAS = _atlas(RAMP)
_G = np.random.default_rng(3)
STREAK = dict(row=_G.integers(0, ROWS, 300), v=_G.uniform(45, 130, 300), L=_G.uniform(6, 30, 300),
              ph=_G.uniform(0, 400, 300), amp=_G.uniform(.5, 1.2, 300), hot=_G.uniform(0, 1, 300))
ROWW = np.ones(ROWS, np.float32)
ROWW[230 // CH:1190 // CH] = .3                # keep text zone calm


def glyphs(lum, t):
    jit = (np.random.default_rng(int(t * 15)).integers(0, 3, lum.shape) - 1) * (lum > .08)
    idx = np.clip((lum * (len(RAMP) - 1)).astype(int) + jit, 0, len(RAMP) - 1)
    g = ATLAS[idx]                                # rows, cols, CH, CW
    return g.transpose(0, 2, 1, 3).reshape(ROWS * CH, COLS * CW)


def streaks(t):
    sp = omega(t) / 15
    amp = streak_amp(t)
    c = np.arange(COLS)[None, :]
    L = STREAK['L'][:, None] * (.7 + .5 * sp)
    pos = (STREAK['ph'][:, None] - STREAK['v'][:, None] * (.7 + .6 * sp) * t) % (COLS + 60) - 30
    d = c - pos
    v = np.where((d >= 0) & (d < L), np.clip(1 - d / L, 0, 1) ** 1.3, 0) * STREAK['amp'][:, None] * amp
    lum = np.zeros((ROWS, COLS), np.float32); hotl = np.zeros_like(lum)
    np.add.at(lum, STREAK['row'], v)
    hm = (STREAK['hot'] < .12 + .2 * clamp(heat(t) - .3))[:, None]
    np.add.at(hotl, STREAK['row'], v * hm)
    lum *= ROWW[:, None]; hotl *= ROWW[:, None]
    g = glyphs(np.clip(lum, 0, 1), t)[..., None]
    k = np.clip(hotl / (lum + 1e-4), 0, 1).repeat(CH, 0).repeat(CW, 1)[..., None]
    return g * (FAR * 1.1 * (1 - k) + ACC * k), float(amp)


def ascii_of(img, t):
    cells = img.reshape(ROWS, CH, COLS, CW, 3).mean(axis=(1, 3))
    lum = cells.max(-1)
    col = cells / (lum[..., None] + 1e-4)
    g = glyphs(np.clip(lum * 2.4, 0, 1), t)
    return g[..., None] * np.clip(col, 0, 1).repeat(CH, 0).repeat(CW, 1) * 1.3


def transition_mask(t):
    m = np.zeros(ROWS, np.float32)
    for tt in TRANSITIONS:
        if abs(t - tt) < .2:
            k = (t - tt + .2) / .4                  # band sweeps top -> bottom
            r = np.arange(ROWS) / ROWS
            m = np.maximum(m, np.clip(1 - np.abs(r - (k * 1.4 - .2)) / .22, 0, 1))
    return m


# ---- HUD ------------------------------------------------------------------
GLYPHS = "!#$%&*+/<=>?@ABCDEFGHKMNRSTUVXYZ0123456789"


def scramble(s, k, seed):
    """k=1 clean text, k=0 fully scrambled into ASCII."""
    r = np.random.default_rng(seed)
    order = r.permutation(len(s))
    n = int(round((1 - clamp(k)) * len(s)))
    out = list(s)
    for i in order[:n]:
        if s[i] != ' ':
            out[i] = GLYPHS[r.integers(len(GLYPHS))]
    return ''.join(out)


def text_k(t, a, b, d=.2):
    """visibility of text living in [a, b): scramble in after a, out before b."""
    return min(prog(t, a, d), 1 - prog(t, b - d, d)) if a <= t < b else 0.0


def odometer(dr, hud, x, y, value, ndig, font, fill, dim):
    s = f"{int(10 ** ndig - 1):,}"
    asc, desc = font.getmetrics(); lh = asc + desc
    cw = font.getlength('0')
    pos = ndig - 1
    for ch in s:
        if ch == ',':
            dr.text((x, y), ',', font=font, fill=fill); x += cw; continue
        p = pos; pos -= 1
        d = int(value // 10 ** p) % 10
        r = value % 1 if p == 0 else clamp(value % 10 ** p - (10 ** p - 1))
        r = io(clamp((r - .72) / .28))            # sit, then quick roll
        lead = value < 10 ** p and p > 0
        tile = Image.new('RGBA', (int(cw) + 2, lh))
        td = ImageDraw.Draw(tile)
        c = dim if lead else fill
        td.text((0, -r * lh), str(d), font=font, fill=c)
        td.text((0, (1 - r) * lh), str((d + 1) % 10), font=font, fill=c)
        hud.alpha_composite(tile, (int(x), int(y)))
        x += cw
    return x


def bracket_box(dr, x0, y0, x1, y1, a=255):
    dr.rectangle([x0, y0, x1, y1], fill=(4, 5, 8, int(150 * a / 255)))
    c = (210, 220, 235, int(a * .5)); L = 22
    dr.rectangle([x0, y0, x1, y1], outline=(210, 220, 235, int(a * .16)), width=1)
    for (x, y, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        dr.line([(x, y + sy * L), (x, y), (x + sx * L, y)], fill=c, width=2)


def leader(dr, a, b, alpha):
    dr.line([a, b], fill=(220, 228, 240, int(140 * alpha)), width=2)
    x, y = b
    dr.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 120, 60, int(230 * alpha)), width=2)
    dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 140, 80, int(255 * alpha)))


def hud_layer(t, top, cnt_sparks, elems, anchors):
    hud = Image.new('RGBA', (W, H))
    dr = ImageDraw.Draw(hud)
    drift = (6 * math.sin(1.1 * t), 5 * math.sin(.8 * t + 1))
    # headline (frame 1 fully legible)
    k = max(text_k(t, -1, t1), prog(t, LOOP, .25))
    tl = t if t < DUR / 2 else t - DUR             # end frames match frame 1
    if k > 0:
        elems.append('headline')
        s = 1 + .05 * (1 - eo(prog(tl, 0, .5)))
        y = 262
        for i, line in enumerate(["WHAT DOES", "490 KM/H DO", "TO A TYRE?"]):
            txt = scramble(line, k, 11 + i + int(t * 20))
            xx = TXT_X + drift[0] * .5
            yy = y + i * 98 * s + drift[1] * .5
            if i == 1:                             # heat underline sweep under 490 KM/H
                u = eo(prog(tl, .05, .5))
                dr.rectangle([xx, yy + 90, xx + 404 * u, yy + 96], fill=(255, 92, 23, int(255 * k)))
                dr.text((xx, yy), txt[:8], font=F_HEAD, fill=(255, 112, 44, int(255 * k)))
                dr.text((xx + F_HEAD.getlength(txt[:8]), yy), txt[8:], font=F_HEAD, fill=(240, 244, 250, int(255 * k)))
            else:
                dr.text((xx, yy), txt, font=F_HEAD, fill=(240, 244, 250, int(255 * k)))
    # rpm callout
    k = text_k(t, t1, t2)
    if k > 0:
        elems.append('rpm_callout')
        x0, y0 = TXT_X - 20 + drift[0], 300 + drift[1]
        bracket_box(dr, x0, y0, x0 + 680, y0 + 330, int(255 * min(1, k * 2)))
        lab = scramble("ROTATION // EACH TYRE", k, 21 + int(t * 20))
        dr.text((x0 + 28, y0 + 24), lab, font=F_LAB, fill=(150, 160, 175, int(255 * k)))
        v = 4100 * eo(prog(t, t1 + .05, 1.25))
        xe = odometer(dr, hud, x0 + 24, y0 + 64, v, 4, F_VAL, (244, 247, 252, int(255 * k)), (70, 76, 88, int(255 * k)))
        dr.text((xe + 14, y0 + 116), "rpm", font=F_UNIT, fill=(244, 247, 252, int(255 * k)))
        revs = 4100 / 60 * (t - t1)
        dr.text((x0 + 28, y0 + 205), scramble(f"REVS {revs:07.1f}  @ 490 KM/H", k, 5), font=F_LAB,
                fill=(150, 160, 175, int(255 * k)))
        ks = prog(t, t1 + .45, .2) * k
        if ks > 0:
            dr.rectangle([x0 + 24, y0 + 254, x0 + 24 + 14 + F_CHIP.getlength("STRETCH: EXAGGERATED"), y0 + 306],
                         outline=(255, 92, 23, int(255 * ks)), width=2)
            dr.text((x0 + 32, y0 + 258), scramble("STRETCH: EXAGGERATED", ks, 9), font=F_CHIP,
                    fill=(255, 112, 44, int(255 * ks)))
        leader(dr, (x0 + 680, y0 + 330), tuple(top[0]), k)
    # g callout -> 5,300 g stamp
    k = text_k(t, t2, t3)
    if k > 0:
        elems.append('g_callout')
        x0, y0 = TXT_X - 20 + drift[0], 300 + drift[1]
        bracket_box(dr, x0, y0, x0 + 700, y0 + 300, int(255 * min(1, k * 2)))
        dr.text((x0 + 28, y0 + 24), scramble("LOAD AT THE TREAD", k, 31 + int(t * 20)), font=F_LAB,
                fill=(150, 160, 175, int(255 * k)))
        v = 5300 * eo(prog(t, t2 + .08, STAMP - t2 - .1))
        sl = 1 + .9 * (1 - oc(prog(t, STAMP, .16))) if t >= STAMP else 1
        col = (255, 112, 44, int(255 * k)) if t >= STAMP else (244, 247, 252, int(255 * k))
        if sl > 1.01:                              # slam: draw scaled stamp
            tile = Image.new('RGBA', (700, 200))
            td = ImageDraw.Draw(tile)
            td.text((10, 10), "5,300 g", font=F_VAL, fill=col)
            tile = tile.resize((int(700 * sl), int(200 * sl)), Image.BILINEAR)
            hud.alpha_composite(tile, (int(x0 + 14 - 350 * (sl - 1) * .3), int(y0 + 54 - 100 * (sl - 1) * .5)))
        else:
            xe = odometer(dr, hud, x0 + 24, y0 + 64, v, 4, F_VAL, col, (70, 76, 88, int(255 * k)))
            dr.text((xe + 14, y0 + 116), "g", font=F_UNIT, fill=col)
        dr.text((x0 + 28, y0 + 214), scramble("ROUGHLY, AT 490 KM/H", k, 6), font=F_CHIP,
                fill=(200, 208, 220, int(255 * k)))
        leader(dr, (x0 + 700, y0 + 300), tuple(top[1]), k)
    LAB, WHT, ORG, REDC = (150, 160, 175), (240, 244, 250), (255, 112, 44), (255, 64, 46)
    def A(c, a): return c + (int(255 * a),)
    revs = 4100 / 60 * max(0.0, t - t1)
    # belts callout
    k = text_k(t, t3 + .15, t4)
    if k > 0:
        elems.append('belts_callout')
        x0, y0 = TXT_X - 20 + drift[0], 290 + drift[1]
        bracket_box(dr, x0, y0, x0 + 760, y0 + 330, int(255 * min(1, k * 2)))
        dr.text((x0 + 28, y0 + 24), scramble(f"CROSS-SECTION // REVS {revs:07.1f}", k, 41 + int(t * 20)),
                font=F_LAB, fill=A(LAB, k))
        dr.text((x0 + 24, y0 + 64), scramble("REINFORCED", k, 42), font=F_HEAD, fill=A(WHT, k))
        dr.text((x0 + 24, y0 + 156), scramble("BELTS", k, 43), font=F_HEAD, fill=A(ORG, k))
        dr.text((x0 + 28, y0 + 262), scramble("TO WITHSTAND ~5,300 g", k, 44), font=F_CHIP, fill=A((200, 208, 220), k))
        if 'belt' in anchors:
            leader(dr, (x0 + 560, y0 + 330), anchors['belt'], k)
    # x-ray callout
    k = text_k(t, t4 + .1, t5)
    if k > 0:
        elems.append('xray_callout')
        x0, y0 = TXT_X - 20 + drift[0], 290 + drift[1]
        pn, pct = anchors.get('pass', (2, 100.0))
        bracket_box(dr, x0, y0, x0 + 760, y0 + 330, int(255 * min(1, k * 2)))
        dr.text((x0 + 28, y0 + 24), scramble(f"QUALITY CHECK // PASS {pn}/2  {pct:05.1f}%", k, 51 + int(t * 20)),
                font=F_LAB, fill=A(LAB, k))
        dr.text((x0 + 24, y0 + 64), scramble("EVERY TYRE", k, 52), font=F_HEAD, fill=A(WHT, k))
        dr.text((x0 + 24, y0 + 156), scramble("X-RAYED", k, 53), font=F_HEAD, fill=A(WHT, k))
        dr.text((x0 + 28, y0 + 262), scramble("EVERY SINGLE ONE", k, 54), font=F_CHIP, fill=A((200, 208, 220), k))
        if 'scan' in anchors:
            leader(dr, (x0 + 760, y0 + 330), anchors['scan'], k)
    # flaw callout + lock-on brackets
    k = text_k(t, t5 + .1, t6)
    if k > 0 and 'flaw' in anchors:
        elems.append('flaw_callout')
        x0, y0 = TXT_X - 20 + drift[0], 290 + drift[1]
        fx, fy = anchors['flaw']
        bracket_box(dr, x0, y0, x0 + 760, y0 + 330, int(255 * min(1, k * 2)))
        dr.text((x0 + 28, y0 + 24), scramble(f"INSPECTION // ANGLE {anchors['flaw_ang']:05.1f} DEG", k, 61 + int(t * 20)),
                font=F_LAB, fill=A(LAB, k))
        dr.text((x0 + 24, y0 + 64), scramble("EVEN A", k, 62), font=F_HEAD, fill=A(WHT, k))
        dr.text((x0 + 24, y0 + 156), scramble("TINY FLAW", k, 63), font=F_HEAD, fill=A(REDC, k))
        dr.text((x0 + 28, y0 + 262), scramble("IS DANGEROUS", k, 64), font=F_CHIP, fill=A((200, 208, 220), k))
        dr.line([(x0 + 560, y0 + 330), (fx, fy)], fill=A((255, 120, 110), .6 * k), width=2)
        sz = 34 + 120 * (1 - eo(prog(t, t5 + .2, .5))) + 6 * math.sin(t * 9)
        for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            cx_, cy_ = fx + sx * sz, fy + sy * sz
            dr.line([(cx_, cy_ - sy * 16), (cx_, cy_), (cx_ - sx * 16, cy_)], fill=A(REDC, k), width=3)
    # poll
    k = text_k(t, t6, LOOP)
    if k > 0:
        elems += ['question', 'poll']
        for i, line in enumerate(["WOULD YOU", "RIDE IT?"]):
            dr.text((TXT_X + drift[0] * .5, 262 + i * 98 + drift[1] * .5), scramble(line, k, 71 + i + int(t * 20)),
                    font=F_HEAD, fill=A(WHT, k))
        for i, lab in enumerate(["YES", "NO"]):
            ki = eo(prog(t, t6 + .3 + .12 * i, .35)) * k
            if ki <= 0: continue
            x = TXT_X + i * 360 - 60 * (1 - ki) + drift[0]
            y = 520 + drift[1]
            sel = (i == 0 and 15.1 <= t < 15.9) or (i == 1 and 15.9 <= t < LOOP - .1)
            dr.rectangle([x, y, x + 320, y + 124], fill=A(WHT, .92 * ki) if sel else (6, 7, 10, int(170 * ki)),
                         outline=A(WHT, .8 * ki), width=2)
            tw = F_BTN.getlength(lab)
            dr.text((x + 160 - tw / 2, y + 20), lab, font=F_BTN, fill=A((10, 12, 16) if sel else WHT, ki))
        dr.text((TXT_X + drift[0], 680 + drift[1]), scramble("COMMENT: YES OR NO?", k, 75), font=F_CHIP,
                fill=A((170, 178, 190), k))
    # tiny tags
    dr.text((40, 36), "Yub", font=F_TAG, fill=(200, 205, 215, 200)); elems.append('yub_tag')
    if PREVIEW:
        dr.text((W - 140, H - 60), "PREVIEW", font=F_TAG, fill=(255, 255, 255, 110))
    return hud


F_BTN = F('Bold', 72)


# ---- cross-section (belts beat) --------------------------------------------
def _mirror(half):                                # left half (u<0) -> full closed-order list
    return half + [(-u, v) for u, v in reversed(half)]


def _top():                                       # tread top with 4 grooves
    pts = [(-.66, 1.0)]
    for c in (-.45, -.15, .15, .45):
        pts += [(c - .04, 1.0), (c - .03, .93), (c + .03, .93), (c + .04, 1.0)]
    return pts + [(.66, 1.0)]


_OUT_L = [(-.70, 0), (-.80, .15), (-.92, .40), (-.98, .62), (-.95, .82), (-.84, .95)]
SEC_OUT = _OUT_L + _top() + [(-u, v) for u, v in reversed(_OUT_L)]
SEC_LIN = _mirror([(-.58, .06), (-.66, .18), (-.78, .40), (-.84, .56), (-.78, .66), (-.62, .69)])
SEC_PLY = _mirror([(-.62, .02), (-.73, .17), (-.85, .40), (-.91, .59), (-.87, .72), (-.72, .755)])
BELTS = [(.80, .78), (.85, .74), (.905, .82)]     # (v, half-width): two steel belts + cap ply


def sec_k(t): return prog(t, t3 + .02, .3) * (1 - prog(t, t4 - .12, .12))


def sec_view(t):
    k = eo(prog(t, t3, .7))
    dist = 3.25 + 6 * (1 - k) - 1.7 * io(prog(t, t4 - .3, .3))
    m = io(prog(t, t3, 3.5))
    return (.3 + .32 * m + .04 * math.sin(1.1 * t), .32 - .12 * m, .02 * math.sin(.9 * t), dist,
            480 + 10 * math.sin(.7 * t), 1110 + 8 * math.sin(.8 * t))


def _p3(pts, z): a = np.array(pts, float); return np.c_[a[:, 0], a[:, 1] - .5, np.full(len(a), z)]


def section_layers(t, k):
    v = sec_view(t)
    lay = {n: Image.new('L', (W, H)) for n in ('sec', 'secb', 'belt', 'fill')}
    d = {n: ImageDraw.Draw(im) for n, im in lay.items()}
    def P(pts, z): return [tuple(p) for p in project(_p3(pts, z), *v)[0]]
    zf, zb = -.12, .32
    for pts in (SEC_OUT, SEC_LIN, SEC_PLY):
        d['sec'].line(P(pts, zf), fill=int(235 * k), width=3 if pts is SEC_OUT else 2)
        d['secb'].line(P(pts, zb), fill=int(200 * k), width=2)
    for a, b in zip(P(SEC_OUT, zf)[::2], P(SEC_OUT, zb)[::2]):
        d['secb'].line([a, b], fill=int(160 * k), width=2)
    for su in (-1, 1):                            # bead cores
        ring_pts = [(su * .64 + .045 * math.cos(a), .06 + .045 * math.sin(a)) for a in np.linspace(0, 6.3, 20)]
        d['sec'].line(P(ring_pts, zf), fill=int(235 * k), width=2)
    d['fill'].polygon(P(SEC_OUT, zf), fill=255)
    d['fill'].polygon(P(SEC_LIN, zf), fill=0)
    for i, (bv, hw) in enumerate(BELTS):
        g = io(prog(t, t3 + .7 + .35 * i, .4))
        us = np.linspace(-hw, hw, 40)
        pts = P([(u, bv - .05 * u * u) for u in us], zf)
        d['sec'].line(pts, fill=int(220 * k * (1 - g)), width=3)
        d['belt'].line(pts, fill=int(255 * k * g), width=7)
        d['belt'].line(P([(u, bv - .05 * u * u) for u in us], zb), fill=int(150 * k * g), width=3)
    ka = prog(t, t3 + 2.4, .25) * k               # outward pull the belts resist
    if ka > 0:
        for u in (-.55, -.275, 0, .275, .55):
            L = .12 + .05 * math.sin(9 * t + u * 4)
            a, b = P([(u, 1.05), (u, 1.05 + L)], zf)
            d['sec'].line([a, b], fill=int(230 * ka), width=3)
            hx, hy = P([(u - .035, 1.0 + L), (u + .035, 1.0 + L)], zf)
            d['sec'].line([hx, b, hy], fill=int(230 * ka), width=3)
    anchor = P([(.45, .85 - .05 * .45 * .45)], zf)[0]
    return lay, anchor


# ---- x-ray scan -------------------------------------------------------------
XRC = np.array([.80, .88, 1.0], np.float32)
XCOL = np.arange(W, dtype=np.float32)
VFADE = np.clip(np.minimum((np.arange(H) - 380) / 200, (1820 - np.arange(H)) / 200), 0, 1).astype(np.float32)


def xray_state(t):
    if t < t4 + .3 or t > t4 + 2.95: return None
    if t < t4 + 1.7:
        s = io(prog(t, t4 + .3, 1.3)); x = -40 + 1160 * s; pn = 1
    else:
        s = io(prog(t, t4 + 1.7, 1.2)); x = 1120 - 1160 * s; pn = 2
    return np.clip((x - XCOL) / 40, 0, 1), x, pn, 100 * s


def xray_of(img, t):
    cells = img.reshape(ROWS, CH, COLS, CW, 3).mean(axis=(1, 3)).max(-1)
    g = glyphs(np.clip(cells * 3.2, 0, 1), t + .5)
    return g[..., None] * XRC * 1.35 + .02


# ---- flaw -------------------------------------------------------------------
RED = np.array([1.0, .13, .08], np.float32)
TH_F = .95 + phi(t5 + .6)                         # lands upper-right of the hub during the beat


def flaw_screen(t):
    a = -phi(t)
    P = np.array([[.86 * math.cos(TH_F), .86 * math.sin(TH_F), -.43]])
    xy, _ = project(spun(P, a, 0, t), *cam(t))
    return tuple(xy[0]), math.degrees(TH_F + a) % 360


# ---- frame ----------------------------------------------------------------
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - .55 * (((XX - W / 2) / (W * .75)) ** 2 + ((YY - H * .55) / (H * .7)) ** 2)).clip(.35, 1)[..., None]


def blur(im, r): return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255
def L(im): return np.asarray(im, np.float32)[..., None] / 255


def small_blur(arr, r):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)).resize((W, H), Image.BILINEAR), np.float32) / 255


def frame(t, info=None):
    elems = ['tyre']
    anchors = {}
    acc, contact, top, camv = wire_layers(t)
    h = heat(t)
    sk = sec_k(t)
    if sk > .02:                                  # tyre falls behind the section: dim + defocus
        near, tread = blur(acc['near'], 5 * sk)[..., None], blur(acc['tread'], 5 * sk)[..., None]
        dim = 1 - .7 * sk
        near, tread = near * dim, tread * dim
    else:
        near, tread, dim = L(acc['near']), L(acc['tread']), 1.0
    far = blur(acc['far'], 3)[..., None] * dim
    gnd = blur(acc['ground'], 1.2)[..., None] * dim
    tcol = WHITE * (1 - min(1, h * .75)) + ACC * min(1, h * .75)
    img = BG + near * WHITE + far * FAR * .7 + gnd * FAR * .6 + tread * tcol
    gl = Image.new('L', (W, H)); g = ImageDraw.Draw(gl)
    (cx0, cy0) = contact[0]
    rr = 70 + 60 * h
    g.ellipse([cx0 - rr * 1.8, cy0 - rr * .6, cx0 + rr * 1.8, cy0 + rr * .6], fill=int(200 * min(1, h) * dim))
    glow = small_blur(L(gl).repeat(3, 2), 10)
    img += glow * ACC * 1.1 + small_blur(tread.repeat(3, 2), 6) * ACC * h * 1.4
    if sk > .02:
        elems.append('section')
        lay, anchors['belt'] = section_layers(t, sk)
        fl = L(lay['fill'])[..., 0].reshape(ROWS, CH, COLS, CW).mean(axis=(1, 3))
        img += glyphs(fl * .28 * sk, t)[..., None] * FAR * .55          # ASCII rubber texture
        bl = L(lay['belt'])
        img += L(lay['sec']) * WHITE + blur(lay['secb'], 2.5)[..., None] * FAR * .8
        img += bl * (ACC * .6 + HOT * .4) + small_blur(bl.repeat(3, 2), 5) * ACC * 1.6
    kf = prog(t, t5 + .15, .2) * (1 - prog(t, t6 - .15, .15))
    if kf > 0:
        elems.append('flaw_marker')
        (fx, fy), anchors['flaw_ang'] = flaw_screen(t)
        anchors['flaw'] = (fx, fy)
        rl = Image.new('L', (W, H)); rd = ImageDraw.Draw(rl)
        pulse = .5 + .5 * math.sin(2 * math.pi * 2.2 * (t - t5)) + bump(t, FLAWHIT, .03, .4)
        r = 5 + 4 * pulse
        rd.ellipse([fx - r, fy - r, fx + r, fy + r], fill=int(255 * kf))
        frac = ((t - t5) * 1.3) % 1
        rr = 12 + 70 * frac
        rd.ellipse([fx - rr, fy - rr, fx + rr, fy + rr], outline=int(255 * kf * (1 - frac)), width=3)
        gs = 1 + .5 * bump(t, FLAWHIT, .03, .5)
        rd.line([(fx + x * gs, fy + y * gs) for x, y in [(-16, -7), (-7, 2), (0, -4), (8, 6), (17, 0)]],
                fill=int(255 * kf), width=2)
        rlf = L(rl)
        img += rlf * RED * 1.3 + small_blur(rlf.repeat(3, 2), 4) * RED * (1.4 + pulse)
    sp = Image.new('RGB', (W, H))
    n = draw_sparks(t, contact, sp)
    if n: elems.append('sparks')
    sp = np.asarray(sp, np.float32) / 255
    img += sp + small_blur(sp, 3) * 1.2
    st, amp = streaks(t)
    if amp > .05: elems.append('ascii_streaks')
    img += st
    img += small_blur(img, 5) * .35 + small_blur(img, 22) * .45          # bloom
    xs = xray_state(t)
    if xs is not None:
        elems.append('xray_scan')
        m, x, pn, pct = xs
        anchors['pass'] = (pn, pct)
        mm = m[None, :, None]
        img = img * (1 - mm) + xray_of(img, t) * mm
        if -20 < x < W + 20:
            prof = np.exp(-((XCOL - x) / 5) ** 2) * 1.3 + np.exp(-((XCOL - x) / 70) ** 2) * .22
            img += prof[None, :, None] * VFADE[:, None, None] * XRC
            anchors['scan'] = (x, camv[5])
    m = transition_mask(t)
    if m.max() > 0:
        mm = m.repeat(CH)[:, None, None]
        img = img * (1 - mm) + ascii_of(img, t) * mm
    img *= VIG
    img += np.random.default_rng(int(t * FPS)).normal(0, .012, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    out.alpha_composite(hud_layer(t, top, n, elems, anchors))
    if info is not None: info.extend(elems)
    return np.asarray(out.convert('RGB'))


def _work(i):
    info = []
    return frame(i / FPS, info).tobytes(), info


def main():
    mode = sys.argv[1]
    if mode == 'still':
        d = sys.argv[2]; os.makedirs(d, exist_ok=True)
        for s in sys.argv[3:]:
            Image.fromarray(frame(float(s))).save(os.path.join(d, f'f_{s}.png'))
        return
    from multiprocessing import Pool
    out = sys.argv[2]
    end = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    start = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    idx = range(int(round(start * FPS)), int(round(end * FPS)))
    log = []
    with Pool(int(os.environ.get('JOBS', os.cpu_count() or 2))) as pool:
        for i, (buf, info) in zip(idx, pool.imap(_work, idx, chunksize=2)):
            p.stdin.write(buf)
            log.append({'f': i, 't': round(i / FPS, 3), 'n': len(info), 'elems': info})
    p.stdin.close(); p.wait()
    json.dump(log, open(os.path.splitext(out)[0] + '_elements.json', 'w'))
    print('max elements/frame:', max(x['n'] for x in log))
    sys.exit(p.returncode)


if __name__ == '__main__':
    main()
