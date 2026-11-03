"""F1 aerodynamics explainer in isometric pixel art, presented by Main Guy. 1080x1920.
Usage: python render.py video VOICE.wav WORDS.json OUT.mp4
       python render.py still WORDS.json OUTDIR t1 t2 ..."""
import importlib.util, json, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m


ip = _load('iso_preview', ROOT / 'iso-preview' / 'src' / 'render.py')     # Iso engine + props
sys.path.insert(0, str(ROOT / 'new-car-trap' / 'src'))
import pix, sfx                                                             # Main Guy sprite + sound effects

C, col, hr, BAYER, Iso, tex, night = ip.C, ip.col, ip.hr, ip.BAYER, ip.Iso, ip.tex, ip.night
W, H, SC = 108, 192, 10
OW, OH = W * SC, H * SC
FPS, SR = 30, 44100

FONT = dict(ip.FONT)
FONT["'"] = ["1", "1", "0", "0", "0", "0", "0"]
FONT['/'] = ["00001", "00010", "00010", "00100", "01000", "01000", "10000"]
FONT['J'] = ["00111", "00010", "00010", "00010", "10010", "10010", "01100"]
FONT['Z'] = ["11111", "00001", "00010", "00100", "01000", "10000", "11111"]
FONT['Q'] = ["01110", "10001", "10001", "10001", "10101", "10010", "01101"]


def tw(s): return sum(len(FONT[ch][0]) for ch in s) + len(s) - 1


def text(c, s, x, y, cl, outline='#0a0a12'):
    L = C(layer=True)
    for ch in s:
        g = FONT[ch]
        for j, row in enumerate(g):
            for i, b in enumerate(row):
                if b == '1': L.px(x + i, y + j, cl)
        x += len(g[0]) + 1
    if outline:
        d = ip.sr.dilate(L.m)
        c.a[d & ~L.m] = col(outline)
    c.a[L.m] = L.a[L.m]


def ctext(c, s, y, cl, outline='#0a0a12'): text(c, s, (W - tw(s)) // 2, y, cl, outline)


# ============================== the F1 car ==============================
L_CAR, W_CAR = 30, 13
LIVERY = dict(body='#2a5ad8', accent='#f6d84a', wing='#22242e', floor='#121218', tyre='#1a1a20',
              helmet='#f04a4a', dark='#202028', ghost='#9aa0b0')


def shades(h, hi=None):
    c = col(h)
    if hi is not None: c = c * (1 - hi) + col('#ffe64a') * hi
    return (np.clip(c * 1.25 + 12, 0, 255), c, c * .72)


def parts(flap_open=0.0):
    fo = flap_open
    return [
        ('floor', 4, 2, 1.0, 22, 9, .6, 'floor'), ('diff', 0, 3, 1.0, 4, 7, 1.4, 'floor'),
        ('rtyre', 2.5, -0.9, 0, 5.5, 3, 4.6, 'tyre'), ('rtyre', 2.5, 10.9, 0, 5.5, 3, 4.6, 'tyre'),
        ('ftyre', 21, -0.4, 0, 4.5, 2.6, 4, 'tyre'), ('ftyre', 21, 10.8, 0, 4.5, 2.6, 4, 'tyre'),
        ('body', 8, 2.3, 1.6, 11, 8.4, 2.6, 'body'), ('body', 12, 4, 1.6, 9, 5, 3.4, 'body'),
        ('body', 20, 5, 1.8, 6, 3, 2.2, 'body'), ('body', 26, 5.4, 1.4, 3, 2.2, 1.6, 'accent'),
        ('body', 5, 4.5, 1.6, 8, 4, 4.4, 'body'), ('body', 10, 5.2, 5.6, 3, 2.6, 1.4, 'accent'),
        ('body', 4.5, 6.3, 5.6, 6, .5, 1.8, 'body'), ('body', 9, 2.3, 4.2, 9, .4, .3, 'accent'),
        ('body', 9, 10.3, 4.2, 9, .4, .3, 'accent'),
        ('helmet', 14, 5.6, 4.8, 2.2, 1.8, 1.6, 'helmet'), ('halo', 15.5, 4.6, 6.2, 2.5, 3.8, .5, 'dark'),
        ('fw', 26.5, -0.6, .7, 3.5, 14.2, .6, 'wing'),
        ('fw', 26.2 + fo * .4, -0.6, 1.3 + fo * .2, 1.6 + fo * .8, 14.2, .5 - fo * .3, 'accent'),
        ('fw', 26.2, -0.9, .7, 3.8, .4, 2.2, 'wing'), ('fw', 26.2, 13.6, .7, 3.8, .4, 2.2, 'wing'),
        ('rw', 0, 0.6, 2.2, 3.2, .5, 6.4, 'wing'), ('rw', 0, 11.9, 2.2, 3.2, .5, 6.4, 'wing'),
        ('rw', 1.5, 6.2, 2.2, .6, .6, 4.2, 'dark'),
        ('rw', 0.4, 1.1, 6.4, 2.8, 10.8, .6, 'wing'),
        ('rw', 0.2 + fo * .2, 1.1, 7.4 + fo * .5, 1.4 + fo * 1.2, 10.8, .9 - fo * .65, 'accent'),
    ]


def to_world(d, X0, Y0, lx, ly, dlx, dly):
    if d == '+x': return X0 + lx, Y0 + ly, dlx, dly
    if d == '-x': return X0 + L_CAR - lx - dlx, Y0 + W_CAR - ly - dly, dlx, dly
    if d == '+y': return X0 + W_CAR - ly - dly, Y0 + lx, dly, dlx
    return X0 + ly, Y0 + L_CAR - lx - dlx, dly, dlx


def f1(I, X0, Y0, d, t, Z=0.0, hi=(), flap=0.0, squash=0.0, ghost=False, spin=18, shadow=True):
    """Draw the F1 car with its footprint at (X0, Y0); d = travel direction."""
    ax = d[1] == 'x'
    if shadow:
        fx, fy = (L_CAR, W_CAR) if ax else (W_CAR, L_CAR)
        I.shade([(X0 - 1, Y0 - 1, 0), (X0 + fx + 1, Y0 - 1, 0), (X0 + fx + 1, Y0 + fy + 1, 0), (X0 - 1, Y0 + fy + 1, 0)],
                .5 if Z < 1 else .5 + min(.35, Z * .04))
    blink = .5 + .5 * math.sin(t * 14)
    items = []
    for name, lx, ly, lz, dlx, dly, dlz, ck in parts(flap):
        X, Y, dx, dy = to_world(d, X0, Y0, lx, ly, dlx, dly)
        z = Z + lz - (squash * .5 if name not in ('rtyre', 'ftyre') else 0)
        dz = dlz - (squash if name in ('rtyre', 'ftyre') else 0)
        if name in ('rtyre', 'ftyre'): z = Z * (Z > 1) + lz
        h_ = (.25 + .6 * blink) if name in hi else None
        cl = 'ghost' if ghost else ck
        items.append((X + dx / 2 + Y + dy / 2 + z * .02, name, X, Y, z, dx, dy, dz, shades(LIVERY[cl], h_)))
    for _, name, X, Y, z, dx, dy, dz, (tp, lf, rt) in sorted(items, key=lambda q: q[0]):
        I.box(X, Y, z, dx, dy, dz, tp, lf, rt)
        if name in ('rtyre', 'ftyre') and not ghost:          # rim on the visible tyre face
            r = 1.5 if name == 'ftyre' else 1.8
            cx, cy, cz = (X + dx / 2, Y + dy + .05, z + dz / 2) if ax else (X + dx + .05, Y + dy / 2, z + dz / 2)
            pts = [((cx + r * math.cos(a), cy, cz + r * math.sin(a)) if ax else (cx, cy + r * math.cos(a), cz + r * math.sin(a)))
                   for a in np.linspace(0, 6.283, 12)]
            I.poly(pts, '#5a5e6a')
            a = t * spin
            hub = (cx + r * .6 * math.cos(a), cy, cz + r * .6 * math.sin(a)) if ax else (cx, cy + r * .6 * math.cos(a), cz + r * .6 * math.sin(a))
            I.c.px(*I.p(*hub), '#d8dce4')


def car_at(cx, cy, d):
    return (cx - L_CAR / 2, cy - W_CAR / 2) if d[1] == 'x' else (cx - W_CAR / 2, cy - L_CAR / 2)


# ============================== track ==============================
TX, TY, TR, HW = 100, 46, 13, 8       # rounded-rectangle centreline: size, corner radius, half width


def track_sdf(X, Y):
    qx = np.abs(X - TX / 2) - TX / 2 + TR; qy = np.abs(Y - TY / 2) - TY / 2 + TR
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - TR


def track_ground(X, Y, t=0):
    d = track_sdf(X, Y)
    a = tex(X, Y, '#6ab448', '#5ea840', 8)
    corner = (np.abs(X - TX / 2) > TX / 2 - TR - 2) & (np.abs(Y - TY / 2) > TY / 2 - TR - 2)
    gravel = corner & (d > HW + 1) & (d < HW + 9)
    a[gravel] = tex(X, Y, '#e0cc98', '#d4be88', 2)[gravel]
    road = np.abs(d) < HW; a[road] = tex(X, Y, '#4e4e5a', '#4a4a56', 3)[road]
    kerb = corner & (np.abs(d) >= HW) & (np.abs(d) < HW + 1.6)
    stripe = ((np.floor((X + Y) / 2.5)) % 2).astype(bool)
    a[kerb & stripe] = col('#e8402a'); a[kerb & ~stripe] = col('#f4f4f4')
    edge = ~corner & (np.abs(d) >= HW) & (np.abs(d) < HW + .7); a[edge] = col('#f4f4f4')
    start = road & (np.abs(X - 30) < 1.6) & (Y > TY - HW)
    a[start] = np.where(((np.floor(X * 1.3) + np.floor(Y * 1.3)) % 2).astype(bool)[start][:, None], col('#f4f4f4'), col('#1a1a20'))
    return a


def path(s):
    """Position + direction along the centreline (s in track units)."""
    sx, sy, q = TX - 2 * TR, TY - 2 * TR, math.pi * TR / 2
    per = 2 * sx + 2 * sy + 4 * q; s %= per
    segs = [('l', TR, TY, sx, '+x'), ('a', TX - TR, TY - TR, 0, None), ('l', TX, TY - TR, sy, '-y'), ('a', TX - TR, TR, 1, None),
            ('l', TX - TR, 0, sx, '-x'), ('a', TR, TR, 2, None), ('l', 0, TR, sy, '+y'), ('a', TR, TY - TR, 3, None)]
    for kind, a, b, n, d in segs:
        ln = n if kind == 'l' else q
        if s <= ln:
            if kind == 'l':
                u = s
                if d == '+x': return a + u, b, d
                if d == '-y': return a, b - u, d
                if d == '-x': return a - u, b, d
                return a, b + u, d
            th = s / q * math.pi / 2
            ang = [math.pi / 2, 0, -math.pi / 2, math.pi][n] - th
            dirs = [('+x', '-y'), ('-y', '-x'), ('-x', '+y'), ('+y', '+x')][n]
            return a + TR * math.cos(ang), b + TR * math.sin(ang), dirs[0] if th < math.pi / 4 else dirs[1]
        s -= ln
    return TR, TY, '+x'


def wide_track(t, speed=60, labels=False, dim=1.0):
    c = C(); I = Iso(c, 34, 66, .74)
    I.ground(lambda X, Y: track_ground(X, Y, t))
    stand = lambda: [I.box(18, TY + 12 + j * 3, j * 2.5, 64, 3, 2.5, '#9aa0b0', '#7a8090', '#5a6070') for j in range(3)]
    I.add(TY + 12 + 30, stand)
    I.add(-20, lambda: I.box(30, -22, 0, 40, 8, 7, '#e8e8f0', '#c8c8d4', '#a8a8b8'))
    for k, (X, Y) in enumerate(((-16, -10), (-14, 30), (112, -8), (114, 40), (50, 23), (40, 20), (60, 26), (-18, 56), (118, 18))):
        I.add(X + Y, lambda X=X, Y=Y: ip.tree(I, X, Y))
    x, y, d = path(t * speed)
    X0, Y0 = car_at(x, y, d)
    I.add(x + y, lambda: f1(I, X0, Y0, d, t))
    I.draw()
    for i in range(30):                                   # crowd colours on the grandstand
        px_, py_ = I.p(18 + hr(i, 3) * 64, TY + 13 + (i % 3) * 3, 2.6 + (i % 3) * 2.5)
        c.px(px_, py_ - 1, ['#f04a4a', '#f6d84a', '#4a8af0', '#f4f4f4'][i % 4])
    if labels:
        for (X, Y, s_) in ((TX - 2, 2, 'GRIP'), (2, TY - 2, 'GRIP'), (TX / 2, TY + 1, 'SPEED'), (TX / 2, -1, 'SPEED')):
            px_, py_ = I.p(X, Y, 6)
            text(c, s_, int(min(W - tw(s_) - 2, max(2, px_ - tw(s_) // 2))), py_ - 8, '#f6d84a' if s_ == 'GRIP' else '#7ae8ff')
    c.a *= dim
    return c


# ============================== close-up straight ==============================
def straight_ground(scroll, kerbs=True):
    def g(X, Y):
        Xs = X + scroll
        a = tex(Xs, Y, '#6ab448', '#5ea840', 8)
        road = (Y > -10) & (Y < 24); a[road] = tex(Xs, Y, '#4e4e5a', '#4a4a56', 3)[road]
        if kerbs:
            for y0 in (-10, 22):
                k = (Y >= y0) & (Y < y0 + 2); st = ((np.floor(Xs / 3)) % 2).astype(bool)
                a[k & st] = col('#e8402a'); a[k & ~st] = col('#f4f4f4')
        a[road & (np.abs(Y - 7) < .3) & ((Xs % 16) < 8)] = col('#8a8a96')
        return a
    return g


def closeup(t, Z=0, hi=(), flap=0., squash=0., k=2.2, scroll_speed=90, flow=None, under=False, cam=(35, 75)):
    c = C(); I = Iso(c, cam[0], cam[1], k)
    I.ground(straight_ground(t * scroll_speed))
    if flow == 'under' or under:
        airflow(I, t, under=True, Z=Z)
    f1(I, 0, 0, '+x', t, Z, hi, flap, squash)
    if flow and flow != 'under': airflow(I, t, kind=flow, Z=Z)
    return c, I


def body_h(lx):
    if lx < 0 or lx > 30: return 0
    if lx < 3.4: return 8.3
    if lx < 13: return 6.2
    if lx < 17: return 6.6
    if lx < 26: return 3.6
    return 2.2


def airflow(I, t, kind='over', Z=0, under=False):
    """Moving dashes of air (car faces +X, so air streams toward -X)."""
    cl = '#c8f6ff'
    if under:
        for ly in (3, 5.5, 8, 10.5):
            for X in np.arange(-6, 36, .5):
                if (X + t * 90) % 5 < 2.4: I.c.px(*I.p(X, ly, Z + .4), '#7ae8ff')
        return
    lanes = {'over': [(-2.5, 1.5), (3, 1.5), (6.5, 1.5), (10, 1.5), (15.5, 1.5)],
             'front': [(1, 0), (4, 0), (6.5, 0), (9, 0), (12, 0)],
             'rear': [(3, 0), (6.5, 0), (10, 0)],
             'drag': [(0, 1), (3, 1), (6.5, 1), (10, 1), (13, 1)]}[kind]
    for ly, zb in lanes:
        for X in np.arange(-14, 44, .5):
            if (X + t * 26) % 7 > 3.2: continue
            lx = X; y = ly; z = Z + max(zb + 1.5, body_h(lx) + .9) if 0 < lx < 31 and 1 < ly < 12 else Z + zb + 1.5
            if kind == 'front' and 20 < lx < 32:              # air split around the front tyres
                y = ly + (-(ly < 6.5) * 2 + (ly > 6.5) * 2) * min(1, (32 - lx) / 6) * (abs(ly - 6.5) > 1)
            if kind == 'rear' and lx < 4: z = Z + 8.5 + (4 - lx) * 1.2
            if kind == 'drag' and lx > 30: z = Z + zb + 2.5
            if kind == 'drag' and 30 < lx < 34: continue
            I.c.px(*I.p(X, y, z), cl)


def arrow_down(c, x, y, h, cl='#ff5a4a', w=5):
    c.rect(x - 1, y, 3, h, cl)
    for j in range(w): c.rect(x - w + j + 1, y + h + j, (w - j) * 2 - 1, 1, cl)


def arrow_h(c, x, y, ln, cl, left=True):
    c.rect(min(x, x + (-ln if left else ln)), y - 1, ln, 3, cl)
    tip = x - ln if left else x + ln
    for j in range(4): c.rect(tip + (j if left else -j - 1), y - j, 1, 2 * j + 1, cl)


def bar(c, x, y, w, h, frac, cl, label):
    c.rect(x - 1, y - 1, w + 2, h + 2, '#0a0a12'); c.rect(x, y, w, h, '#2a2c38')
    hh = int(h * min(1, frac)); c.rect(x, y + h - hh, w, hh, cl)
    text(c, label, int(min(W - tw(label) - 2, max(2, x + w // 2 - tw(label) // 2))), y + h + 3, '#ffffff')


def text2(c, s, x, y, cl, outline='#0a0a12'):
    """Double-size pixel text."""
    L = C(layer=True)
    for ch in s:
        g = FONT[ch]
        for j, row in enumerate(g):
            for i, b in enumerate(row):
                if b == '1': L.rect(x + i * 2, y + j * 2, 2, 2, cl)
        x += (len(g[0]) + 1) * 2
    d = ip.sr.dilate(L.m); c.a[d & ~L.m] = col(outline); c.a[L.m] = L.a[L.m]


def ctext2(c, s, y, cl): text2(c, s, (W - tw(s) * 2) // 2, y, cl)


def ease(u): u = min(1, max(0, u)); return u * u * (3 - 2 * u)


# ============================== timing from the aligned voiceover ==============================
WORDS = []
LINE_T = []


def load_words(path):
    global WORDS, LINE_T
    WORDS = json.load(open(path))
    n = max(w['line'] for w in WORDS) + 1
    LINE_T = [min(w['s'] for w in WORDS if w['line'] == i) for i in range(n)]


def wt(line, idx):
    return [w for w in WORDS if w['line'] == line][idx]['s']


def cur_line(t):
    k = 0
    for i, s in enumerate(LINE_T):
        if t >= s - .12: k = i
    return k


# ============================== scenes ==============================
def sc0(t, lt):
    c = wide_track(t + 1.2)
    if wt(0, 6) <= t < wt(0, 6) + .5: c.a[:] = c.a[::-1]               # "upside down" flip gag
    return c


def sc1(t, lt):
    c, I = closeup(t, flow='over' if t >= wt(1, 6) - .1 else None)
    return c


def airfoil(c, fy, t):
    x0, y0, x1, y1 = 6, 44, 102, 126
    c.rect(x0 - 1, y0 - 1, x1 - x0 + 2, y1 - y0 + 2, '#0a0a12')
    c.grad(y0, y1, ['#e8f6fc', '#c8e8f8', '#a8d4ee'], x0, x1)
    cx, cy, ch = 22, 86, 64
    xs = np.linspace(0, 1, 40)
    yt = .6 * (.2969 * np.sqrt(xs) - .126 * xs - .3516 * xs ** 2 + .2843 * xs ** 3 - .1015 * xs ** 4)
    yc = np.where(xs < .4, .04 / .16 * (.8 * xs - xs ** 2), .04 / .36 * (.2 + .8 * xs - xs ** 2))
    up = [(cx + x * ch, cy - fy * (yc[i] + yt[i]) * ch) for i, x in enumerate(xs)]
    lo = [(cx + x * ch, cy - fy * (yc[i] - yt[i]) * ch) for i, x in enumerate(xs)][::-1]
    for k, y_off in enumerate((-26, -18, -11, 11, 18, 26)):
        top = y_off < 0
        suction = top == (fy > 0)
        for x in range(x0 + 1, x1 - 1):
            u = (x - cx) / ch
            bump = (5 if abs(y_off) < 15 else 3) * math.exp(-((u - .3) / .35) ** 2)
            y = cy + y_off + (-bump if top else bump) * (1 if suction else .4) * (1 if top else 1)
            spd = 60 if suction else 30
            if (x - t * spd + k * 7) % 9 < 5: c.px(x, y, '#3a8ac8' if suction else '#7ab0d8')
    c.poly(up + lo, '#2a2c38'); c.poly(up[:20] + [(up[19][0], up[19][1] + fy * 1.5)] + [(up[0][0], up[0][1] + fy)], '#4a4e60')
    if abs(fy) > .6:
        if fy > 0:
            ax, ay = 80, 72
            c.rect(ax - 2, ay - 18, 5, 18, '#3ac860')
            for j in range(6): c.rect(ax - j, ay - 24 + j, 2 * j + 1, 1, '#3ac860')
            text(c, 'LIFT', ax - 30, ay - 20, '#2a9a48', '#ffffff')
            text(c, 'PLANE WING', x0 + 3, y0 + 3, '#1a2a4a', None)
        else:
            ax, ay = 80, 96
            c.rect(ax - 2, ay, 5, 16, '#e8402a')
            for j in range(6): c.rect(ax - 5 + j, ay + 16 + j, 11 - 2 * j, 1, '#e8402a')
            text(c, 'F1 WING', x0 + 3, y0 + 3, '#1a2a4a', None)
            text(c, 'DOWN', ax - 26, ay + 10, '#c8302a', '#ffffff')


def flipstate(t, events):
    """events: list of (time, target fy); returns current fy with a 0.35 s flip animation."""
    fy = events[0][1]; prev = fy
    for te, target in events:
        if t >= te:
            u = ease((t - te) / .35); fy = prev + (target - prev) * u; prev = target
    return fy


def sc2(t, lt):
    c, I = closeup(t, flow='over'); c.a *= .35
    fy = flipstate(t, [(0, 1), (wt(2, 9), -1), (wt(3, 0) - .1, 1), (wt(3, 6), -1)])
    airfoil(c, fy, t)
    return c


def sc4(t, lt):
    sq = .8 * ease(lt / .3)
    c, I = closeup(t, squash=sq)
    for i in range(7):
        ph = min(1, lt * 2.5 - i * .12)
        if ph <= 0: continue
        x = 18 + i * 11; y = 30 + (i % 2) * 8 + ph * 26
        arrow_down(c, x, y, 10, '#ff5a4a', 4)
    if lt > .2:
        sh = int(2 * math.sin(lt * 60) * max(0, .5 - lt))
        c.a[:] = np.roll(c.a, sh, 1)
        ctext2(c, 'DOWNFORCE', 110, '#f6d84a')
    return c


def sc5(t, lt):
    sq = .6 + .25 * math.sin(lt * 6)
    c, I = closeup(t, squash=sq, hi=('rtyre', 'ftyre') if lt > 1 else ())
    for i, x in enumerate((30, 52, 74)):
        arrow_down(c, x, 44 + int(3 * math.sin(lt * 6 + i)), 10, '#ff5a4a', 4)
    bar(c, 92, 56, 8, 50, min(1, lt / 2.6), '#3ac860', 'GRIP')
    return c


def corner_ground(X, Y):
    R = 16
    a = tex(X, Y, '#6ab448', '#5ea840', 8)
    dA = np.where(X <= 0, np.abs(Y), 1e9)
    q = (X > 0) & (Y < R); rr = np.hypot(X, Y - R)
    dArc = np.where(q, np.abs(rr - R), 1e9)
    dB = np.where(Y >= R, np.abs(X - R), 1e9)
    d = np.minimum(np.minimum(dA, dArc), dB)
    outside = q & (rr < R) | (X > 0) & (Y < 0) & ~q
    grav = (X > -4) & (Y < R + 4) & (rr < R - HW) & ~(np.abs(Y) < HW) & (X > 0) | ((X > 0) & (Y < -HW) & (Y > -HW - 10) & (X < 40))
    a[grav] = tex(X, Y, '#e0cc98', '#d4be88', 2)[grav]
    road = d < HW; a[road] = tex(X, Y, '#4e4e5a', '#4a4a56', 3)[road]
    kerb = q & (np.abs(d) >= HW) & (np.abs(d) < HW + 1.6)
    st = ((np.floor((X + Y) / 2.5)) % 2).astype(bool)
    a[kerb & st] = col('#e8402a'); a[kerb & ~st] = col('#f4f4f4')
    return a


def corner_path(s):
    R = 16; q = math.pi * R / 2
    if s < 0: return s, 0, '+x'
    if s < q:
        th = s / R; return R * math.sin(th), R - R * math.cos(th), '+x' if th < math.pi / 4 else '+y'
    return R, R + (s - q), '+y'


def sc6(t, lt):
    c = C(); I = Iso(c, 54, 84, 1.25)
    I.ground(corner_ground)
    gx = -70 + 55 * min(lt, 1.25) + max(0, min(lt, 2.4) - 1.25) * 30 * (1 - (min(lt, 2.4) - 1.25) / 2.3)
    wig = math.sin(lt * 18) * 1.2 * (1.3 < lt < 2.4)
    s = -70 + 46 * max(0, lt - .5)
    x, y, d = corner_path(s)
    X0, Y0 = car_at(x, y, d)
    gX, gY = car_at(gx, wig, '+x')
    I.add(gx + wig, lambda: f1(I, gX, gY, '+x', t, ghost=True))
    I.add(x + y, lambda: f1(I, X0, Y0, d, t))
    I.draw()
    if 1.3 < lt < 2.8:
        for i in range(6):
            ph = (lt * 3 + i / 6) % 1
            px_, py_ = I.p(gx - 14 - ph * 6, 6.5 + (i - 3) * 2, 1 + ph * 3)
            c.disc(px_, py_, 1 + ph * 2, '#e8d8b0' if ph < .5 else '#c8b890')
    px_, py_ = I.p(gx, 6.5, 9); text(c, 'NO AERO', px_ - 18, py_ - 8, '#c8ccd8')
    px_, py_ = I.p(x, y, 9); text(c, 'AERO', px_ - 10, py_ - 8, '#7ae8ff')
    return c


def sc7(t, lt):
    c, I = closeup(t, hi=('fw',), flow='front', k=2.6, cam=(9, 56))
    text(c, 'FRONT WING', 46, 122, '#f6d84a')
    return c


def sc8(t, lt):
    c, I = closeup(t, hi=('rw',), flow='rear', k=2.6, cam=(61, 82))
    arrow_down(c, 58, 34 + int(2 * math.sin(lt * 8)), 10, '#ff5a4a', 4)
    text(c, 'REAR WING', 50, 122, '#f6d84a')
    return c


def sc9(t, lt):
    Z = 7 * ease(lt / .9)
    c, I = closeup(t, Z=Z, hi=('floor', 'diff') if lt > .8 else ())
    if lt > .9: text(c, 'THE FLOOR', W - tw('THE FLOOR') - 3, 124, '#f6d84a')
    return c


def sc10(t, lt):
    ts = wt(10, 7)
    Z = 7 if t < ts else 7 * (1 - ease((t - ts) / .35))
    c, I = closeup(t, Z=Z, hi=('floor', 'diff'), flow='under')
    if t < ts:
        for x in (36, 54, 72):
            px_ = x; py_ = 108
            arrow_down(c, px_, py_ + int((t * 4) % 3), 5, '#7ae8ff', 3)
        text(c, 'FAST AIR', W - tw('FAST AIR') - 3, 122, '#7ae8ff'); text(c, 'LOW PRESSURE', W - tw('LOW PRESSURE') - 3, 132, '#f6d84a')
    else:
        ctext2(c, 'SUCKED', 110, '#f6d84a')
    return c


def sc11(t, lt):
    dur = LINE_T[12] - LINE_T[11]
    u = min(1, lt / (dur - .4))
    c, I = closeup(t, flow='over', squash=.5 * u, scroll_speed=90 + 120 * u)
    bar(c, 8, 52, 9, 52, .55, '#9aa0b0', 'WEIGHT')
    f = u * 1.05; over = f > .55
    bar(c, 90, 52, 9, 52, f, '#f6d84a' if over and int(t * 8) % 2 else '#3a8af0', 'DOWN')
    spd = int(120 + 210 * u); s_ = f'{spd} KM/H'
    text(c, s_, W - tw(s_) - 3, 148, '#ffffff')
    return c


def sc12(t, lt):
    c, I = closeup(t, scroll_speed=200, flow='over')
    c.a[:] = c.a[::-1]                                     # the whole road becomes the ceiling
    c.a *= .7
    for i in range(6):                                      # tunnel lights streaking past
        x = (i * 31 - t * 160) % 150 - 20
        c.rect(x, 186 - 30, 14, 2, '#ffd98a'); c.glow(x + 7, 157, 10, '#ffd98a', .3, 4)
    c.rect(0, 160, W, 32, '#14141c')
    if lt > .6: ctext2(c, 'IT STICKS', 112, '#f6d84a')
    return c


def sc13(t, lt):
    tk = wt(13, 7)
    c, I = closeup(t, flow='drag', scroll_speed=90 if t < tk else 60)
    if lt > .4:
        ln = 14 + int(3 * math.sin(t * 9)); arrow_h(c, 70, 70, ln + 10, '#ff5a4a', left=True)
        text(c, 'DRAG', 74, 66, '#ff5a4a')
    spd = 340 if t < tk else int(340 - 40 * ease((t - tk) / .8)); s_ = f'{spd} KM/H'
    text(c, s_, W - tw(s_) - 3, 148, '#ffffff' if t < tk else '#ff8a7a')
    return c


def sc14(t, lt):
    tb = wt(14, 10)
    fl = ease(lt / .4) if t < tb else 1 - ease((t - tb) / .35)
    straight = t < tb
    c, I = closeup(t, flap=fl, hi=('fw', 'rw') if abs(fl - .5) < .45 or lt < .6 else (), scroll_speed=150 if straight else 70,
                   flow='over' if straight else None)
    s_ = 'STRAIGHT MODE' if straight else 'CORNER MODE'
    text(c, s_, W - tw(s_) - 3, 138, '#7ae8ff' if straight else '#f6d84a')
    spd = int(300 + 45 * ease(lt / 2)) if straight else int(345 - 150 * ease((t - tb) / 1.2)); s2 = f'{spd} KM/H'
    text(c, s2, W - tw(s2) - 3, 148, '#ffffff')
    return c


def sc15(t, lt): return wide_track(t + 1.2, labels=True)


def sc16(t, lt):
    c = wide_track(t + 1.2, dim=.45)
    ctext2(c, 'UPSIDE', 56, '#f6d84a'); ctext2(c, 'DOWN?', 76, '#f6d84a')
    return c


SCENES = {0: sc0, 1: sc1, 2: sc2, 3: sc2, 4: sc4, 5: sc5, 6: sc6, 7: sc7, 8: sc8, 9: sc9, 10: sc10, 11: sc11,
          12: sc12, 13: sc13, 14: sc14, 15: sc15, 16: sc16}
POSE = {0: 'point', 1: 'talkR', 2: 'talkB', 3: 'pointup', 4: 'cheer', 5: 'point', 6: 'shock', 7: 'point', 8: 'hips',
        9: 'pointup', 10: 'talkB', 11: 'shrug', 12: 'shock', 13: 'sad', 14: 'point', 15: 'cheer', 16: 'wave'}
KEY = {'DOWNFORCE', 'DOWNFORCE.', 'AIR.', 'WING', 'FLOOR.', 'GRIP', 'DRAG,', 'DRAG.', 'DRAG', 'CEILING,', 'UPSIDE', 'DOWN.', 'DOWN?',
       'CORNERS.', 'STRAIGHTS.', 'STRAIGHTS,', 'TIRES'}


# ============================== presenter + captions ==============================
_GUY = {}


def guy(expr, pose):
    k = (expr, pose)
    if k not in _GUY: _GUY[k] = np.asarray(pix.guy(expr, False, pose).convert('RGBA')).astype(np.float32)
    return _GUY[k]


def presenter(c, t, line):
    talking = any(w['s'] <= t < w['e'] for w in WORDS)
    p = POSE.get(line, 'down')
    if p == 'cheer': p = 'up1' if int(t * 5) % 2 else 'up2'
    if p == 'wave': p = 'wave1' if int(t * 4) % 2 else 'wave2'
    if p == 'pointup' and line == 3 and t >= wt(3, 6): p = 'point'
    if line in (6,) and t < LINE_T[6] + 1.3: p = 'point'
    if line == 13 and t < wt(13, 7): p = 'talkR'
    if talking: e = 'talk' if int(t * 11) % 2 == 0 else 'smile'
    else: e = 'blink' if (t % 3.1) < .12 else 'smile'
    if p == 'shock' and not talking: e = 'shock'
    if p == 'sad': e = 'sadtalk' if talking and int(t * 11) % 2 == 0 else 'sad'
    g = guy(e, p)
    bob = int((t * 1.7) % 1 < .5) if not talking else 0
    x0, y0 = -6, H - 60 + bob
    a = g[..., 3:4] / 255; ys, xs = slice(max(0, y0), min(H, y0 + 60)), slice(max(0, x0), x0 + 48)
    gs = g[(ys.start - y0):(ys.stop - y0), (xs.start - x0):(xs.stop - x0)]
    m = gs[..., 3] > 128
    reg = c.a[ys, xs]; reg[m] = gs[..., :3][m]


def captions(c, t):
    line = [w for w in WORDS if w['s'] - .05 <= t]
    if not line: return
    li = line[-1]['line']
    ws = [w for w in WORDS if w['line'] == li]
    groups, cur = [], []
    for w in ws:
        if cur and (len(cur) == 3 or tw(' '.join(x['w'].upper().strip('.,') for x in cur + [w])) > 100):
            groups.append(cur); cur = []
        cur.append(w)
    if cur: groups.append(cur)
    for gi, g in enumerate(groups):
        end = groups[gi + 1][0]['s'] if gi + 1 < len(groups) else g[-1]['e'] + .3
        if g[0]['s'] - .05 <= t < end:
            words = [w['w'].upper() for w in g]
            disp = ' '.join(x.strip('.,') for x in words)
            x = (W - tw(disp)) // 2
            for wd in words:
                s_ = wd.strip('.,')
                cl = '#f6d84a' if wd in KEY or s_ in KEY else '#ffffff'
                pop_ = (t - g[0]['s']) < .08
                text(c, s_, x, 26 - pop_, cl)
                x += tw(s_) + 4


def frame(t):
    line = cur_line(t)
    lt = t - LINE_T[line]
    c = SCENES[line](t, lt)
    presenter(c, t, line)
    captions(c, t)
    a = np.clip(c.a, 0, 255)
    end = WORDS[-1]['e'] + .9
    a = a * max(0, min(1, t / .25, (end - t) / .5))
    return Image.fromarray(np.repeat(np.repeat(a, SC, 0), SC, 1).astype(np.uint8))


# ============================== audio ==============================
def audio(voice_path, out_path, dur):
    with wave.open(str(voice_path)) as w:
        vr = w.getframerate(); v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    n = int(SR * dur); tt = np.arange(n) / SR
    voice = np.interp(tt, np.arange(len(v)) / vr, v, right=0)
    rng = np.random.default_rng(3); noise = rng.standard_normal(n)
    lp = lambda x, k: np.convolve(x, np.ones(k) / k, 'same')
    tri = lambda f: 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * tt))
    music = np.zeros(n); beat = 60 / 112 / 2
    chords = [(220, 261.6, 329.6), (174.6, 220, 261.6), (261.6, 329.6, 392), (196, 246.9, 293.7)]
    for i in range(int(dur / beat)):
        s0 = i * beat; ch = chords[(i // 8) % 4]; f = ch[[0, 1, 2, 1, 2, 1, 0, 2][i % 8]] * 2
        m = (tt >= s0) & (tt < s0 + beat)
        music[m] += tri(f)[m] * np.exp(-(tt[m] - s0) * 8) * .05
        if i % 2 == 0: music[m] += np.exp(-(tt[m] - s0) * 30) * np.sin(2 * np.pi * 55 * (tt[m] - s0)) * .1
        if i % 4 == 2: music[m] += lp(noise, 2)[m] * np.exp(-(tt[m] - s0) * 40) * .04
        if i % 8 == 0:
            m2 = (tt >= s0) & (tt < s0 + beat * 8); music[m2] += tri(ch[0] / 2)[m2] * .03
    env = np.convolve(np.abs(voice) > .02, np.ones(int(SR * .25)) / (SR * .25), 'same')
    music *= 1 - .55 * np.clip(env * 3, 0, 1)                       # duck under the voice
    ph = np.cumsum(90 + 25 * np.sin(tt * .9)) / SR
    engine = lp(np.sign(np.sin(2 * np.pi * ph)) * .5 + np.sin(4 * np.pi * ph) * .3, 6) * .025
    cues = [(LINE_T[i] - .05, 'whoosh', .35) for i in range(1, len(LINE_T))]
    cues += [(wt(4, 2), 'boom', .5), (wt(4, 2) + .1, 'ding', .35), (LINE_T[6] + 1.3, 'screech', .5),
             (wt(10, 7) + .3, 'thump', .7), (wt(14, 0), 'whoosh', .5), (wt(14, 10), 'stamp', .4),
             (wt(0, 6), 'whoosh', .4), (LINE_T[12] + .6, 'pop', .4), (LINE_T[16], 'sparkle', .4), (.2, 'vroom', .5)]
    fx = sfx.render(cues, dur)
    fx = np.interp(tt, np.arange(len(fx)) / sfx.SR, fx)
    mix = voice * 1.0 + music * .9 + engine + fx * .6
    mix *= np.clip(np.minimum(tt / .2, (dur - tt) / .5), 0, 1)
    mix = np.clip(mix / max(1e-6, np.abs(mix).max()) * .89, -1, 1)
    with wave.open(str(out_path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.c_[mix, mix] * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        load_words(sys.argv[2]); out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        for s_ in sys.argv[4:]: frame(float(s_)).save(out / f'f_{s_}.png')
    else:
        voice, words, out = sys.argv[2], sys.argv[3], Path(sys.argv[4]); load_words(words)
        dur = WORDS[-1]['e'] + 1.0
        wav = out.with_suffix('.wav'); audio(voice, wav, dur)
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}',
                              '-r', str(FPS), '-i', '-', '-i', str(wav), '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                              str(out)], stdin=subprocess.PIPE)
        for i in range(int(dur * FPS)): p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
