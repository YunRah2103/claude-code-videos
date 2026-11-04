"""Porsche 911 (991.2, 2017 Carrera 4S) pixel sprites built from real proportions in metres.

Side view faces right; x = metres from the rear bumper, y = metres above the road.
Length 4.50 m, height 1.30 m, wheelbase 2.45 m, 20" wheels. Rear view follows a 991 C4S
rear photo: slim wraparound tail lamps joined by a light bar, raised wing over the louvred
engine lid, twin exhaust pairs at each corner.
"""
import numpy as np
from PIL import Image, ImageDraw
from pixkit import bayer, smooth

RED = np.array([(40, 4, 12), (78, 8, 18), (124, 14, 26), (170, 22, 32), (208, 38, 42), (236, 78, 70),
                (255, 150, 130), (255, 222, 205)], float)
NT = len(RED)
GLASS = np.array([(5, 6, 12), (11, 14, 26), (20, 26, 46), (36, 46, 76), (70, 90, 130), (140, 165, 205)], float)


def catmull(pts, n=10, closed=False):
    P = np.array(pts, float)
    P = np.vstack([P[-1], P, P[0], P[1]]) if closed else np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed: out.append(P[-2])
    return out


# body silhouette, rear bumper -> flyline -> roof -> windscreen -> wing -> nose
TOP = [(0.14, 0.15), (0.04, 0.26), (0.0, 0.44), (0.01, 0.66), (0.05, 0.83), (0.13, 0.915), (0.30, 0.97),
       (0.62, 1.04), (0.98, 1.12), (1.34, 1.205), (1.72, 1.274), (2.06, 1.298), (2.36, 1.282), (2.62, 1.18),
       (2.90, 1.04), (3.14, 0.93), (3.46, 0.895), (3.76, 0.895), (3.98, 0.882), (4.17, 0.835), (4.33, 0.74),
       (4.45, 0.60), (4.50, 0.44), (4.50, 0.30), (4.45, 0.20), (4.34, 0.135)]
BOTTOM = [(4.10, 0.125), (0.40, 0.14)]
DLO = [(2.84, 0.97), (2.58, 1.142), (2.36, 1.232), (2.06, 1.258), (1.74, 1.236), (1.50, 1.17), (1.33, 1.075),
       (1.25, 0.99), (1.50, 0.965), (2.30, 0.955)]
RW, FW = 1.08, 3.53
WR = (0.348, 0.338)
RIM = (0.258, 0.252)


def _nb(m): return m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)


def side(L):
    s = L / 4.5
    w, h = int(4.62 * s) + 8, int(1.46 * s) + 8
    gy = h - 3
    X = lambda x: 4 + x * s
    Y = lambda y: gy - y * s
    P = lambda pts: [(X(x), Y(y)) for x, y in pts]

    def mask(fn):
        im = Image.new('L', (w, h), 0); fn(ImageDraw.Draw(im)); return np.asarray(im) > 0

    def circ(d, c, r0, r): d.ellipse([X(c) - r * s, Y(r0) - r * s, X(c) + r * s, Y(r0) + r * s], fill=1)

    body = mask(lambda d: d.polygon(P(catmull(TOP, 8) + BOTTOM), fill=1))
    arch = mask(lambda d: [circ(d, RW, WR[0], WR[0] + 0.045), circ(d, FW, WR[1], WR[1] + 0.045)])
    lip = mask(lambda d: [circ(d, RW, WR[0], WR[0] + 0.045 + 2.2 / s), circ(d, FW, WR[1], WR[1] + 0.045 + 2.2 / s)])
    glass = mask(lambda d: d.polygon(P(catmull(DLO, 8, closed=True)), fill=1))
    frame = _nb(glass) & ~glass
    if s > 50: frame |= _nb(frame) & ~glass
    well = body & arch
    body = body & ~arch
    rr, cc = np.mgrid[0:h, 0:w]
    ym = (gy - rr) / s; xm = (cc - 4) / s
    toprow = np.argmax(body | glass, axis=0); d = rr - toprow[None, :]
    # paint: sky reflection above a curved horizon line that hugs the hips, road reflection below
    hz = 0.56 + 0.04 * np.exp(-((xm - 1.0) / 0.8) ** 2)
    up = ym > hz
    v = np.where(up, 0.58 + 0.22 * smooth(0.0, 0.35, ym - hz), 0.40 - 0.24 * smooth(0.0, 0.45, hz - ym))
    v = np.where(up & (ym - hz < 0.035), 0.86, v)
    v = np.where(~up & (hz - ym < 0.03), 0.22, v)
    v += np.where(d == 0, 0.30, np.where(d == 1, 0.14, 0))
    v -= 0.22 * (ym < 0.22)
    # 911 signature: haunch highlight arcs over the rear wheel, wing crest over the front wheel
    hr = np.hypot((xm - RW) / 1.0, (ym - WR[0]) / 0.82)
    v += 0.42 * np.exp(-((hr - 0.60) / 0.035) ** 2) * (ym > 0.55) * (xm < 1.95)
    v -= 0.14 * np.exp(-((hr - 0.70) / 0.05) ** 2) * (ym > 0.6) * (xm < 1.95) * (xm > 0.3)
    fr = np.hypot((xm - FW) / 1.0, (ym - WR[1]) / 1.0)
    v += 0.36 * np.exp(-((fr - 0.50) / 0.03) ** 2) * (ym > 0.62) * (xm > 3.05)
    v[lip & body] = 0.18
    lipt = lip & body & (ym > WR[0] + 0.1)
    ex = mask(lambda d: (d.line(P([(2.86, 0.955), (2.92, 0.60), (2.90, 0.17)]), fill=1),
                         d.line(P([(1.80, 0.96), (1.76, 0.55), (1.82, 0.17)]), fill=1)))
    v[ex & body] = 0.12
    hand = mask(lambda d: d.rectangle([X(2.06), Y(0.845), X(2.30), Y(0.82)], fill=1))
    v[hand & body] = 0.9
    v[np.roll(hand, 1, 0) & ~hand & body] = 0.1
    sill = mask(lambda d: d.polygon(P([(1.46, 0.135), (3.12, 0.125), (3.12, 0.19), (1.46, 0.20)]), fill=1)) & body
    bpil = mask(lambda d: d.line(P([(1.93, 0.958), (1.99, 1.256)]), fill=1, width=max(1, int(0.05 * s))))
    intake = mask(lambda d: d.polygon(P([(4.26, 0.16), (4.47, 0.19), (4.50, 0.36), (4.30, 0.34)]), fill=1)) & body
    led = mask(lambda d: d.line(P([(4.22, 0.43), (4.49, 0.45)]), fill=1, width=max(1, int(0.025 * s)))) & body
    hl = catmull([(3.84, 0.885), (4.06, 0.88), (4.24, 0.83), (4.38, 0.74), (4.43, 0.65), (4.33, 0.61),
                  (4.14, 0.67), (3.92, 0.79)], 8, closed=True)
    head = mask(lambda d: d.polygon(P(hl), fill=1)) & body
    ring = _nb(head) & ~head & body
    hli = mask(lambda d: d.ellipse([X(4.18), Y(0.80), X(4.32), Y(0.69)], fill=1)) & head
    dw = max(1, s * 0.025); dh = max(0, s * 0.012)
    drl = mask(lambda d: [d.rectangle([X(x0), Y(y0) - dh, X(x0) + dw, Y(y0)], fill=1)
                          for x0, y0 in ((3.98, 0.83), (4.08, 0.80), (4.36, 0.66), (4.30, 0.63))]) & head
    tail = mask(lambda d: d.polygon(P([(0.005, 0.80), (0.06, 0.895), (0.34, 0.965), (0.36, 0.93), (0.09, 0.86),
                                       (0.02, 0.76)]), fill=1)) & body
    refl = mask(lambda d: d.rectangle([X(0.01), Y(0.40), X(0.10), Y(0.37)], fill=1)) & body
    pipes = mask(lambda d: d.rectangle([X(0.10), Y(0.21), X(0.26), Y(0.16)], fill=1))
    mhead = mask(lambda d: d.polygon(P(catmull([(2.74, 0.99), (2.93, 0.985), (2.99, 1.02), (2.95, 1.055),
                                                (2.78, 1.06), (2.72, 1.03)], 6, closed=True)), fill=1))
    mstalk = mask(lambda d: d.line(P([(2.88, 0.99), (2.92, 0.94)]), fill=1, width=max(1, int(0.03 * s))))
    wing = mask(lambda d: d.polygon(P([(0.14, 0.925), (0.60, 1.045), (0.61, 1.075), (0.15, 0.955)]), fill=1))
    wingp = mask(lambda d: [d.line(P([(x, 0.90 + (x - 0.14) * 0.24), (x, 0.95 + (x - 0.14) * 0.24)]), fill=1,
                                   width=max(1, int(0.025 * s))) for x in (0.30, 0.46)])
    louv = mask(lambda d: d.line(P([(0.28, 0.945), (0.66, 1.03)]), fill=1, width=max(1, int(0.02 * s)))) & body
    allm = body | glass | well | mhead | mstalk | pipes
    # ---- pseudo-3D surface normals from the silhouette (for environment-mapped paint)
    anyb = body.any(0)
    tb = np.where(anyb, np.argmax(body, 0), h); bb = np.where(anyb, h - 1 - np.argmax(body[::-1], 0), 0)
    dt = np.clip((rr - tb[None, :]) / s, 0, 9); db = np.clip((bb[None, :] - rr) / s, 0, 9)
    anyr = body.any(1)
    lft = np.where(anyr, np.argmax(body, 1), 0); rgt = np.where(anyr, w - 1 - np.argmax(body[:, ::-1], 1), w)
    dl = np.clip((cc - lft[:, None]) / s, 0, 9); dr = np.clip((rgt[:, None] - cc) / s, 0, 9)
    ny = 0.88 * np.exp(-dt / 0.09) - 0.85 * np.exp(-db / 0.06)
    ny += 0.42 * np.exp(-((xm - 0.85) / 0.62) ** 2 - ((ym - 0.86) / 0.11) ** 2)       # broad rear hips
    ny += 0.25 * np.exp(-((xm - 3.75) / 0.40) ** 2 - ((ym - 0.80) / 0.07) ** 2)       # front wing crest
    ny -= 0.14 * np.exp(-((ym - 0.40) / 0.08) ** 2)
    nx = 0.85 * np.exp(-dr / 0.13) - 0.85 * np.exp(-dl / 0.13)
    for (wc, r0, ra) in ((RW, WR[0], WR[0] + 0.045), (FW, WR[1], WR[1] + 0.045)):
        ddx, ddy = xm - wc, ym - r0
        dist = np.hypot(ddx, ddy) + 1e-6
        da = dist - ra
        mag = 0.62 * np.exp(-np.clip(da, 0, 9) / 0.07) * (da > 0) * (da < 0.35) * (ddy > -0.05)
        nx += mag * ddx / dist; ny += mag * ddy / dist
    nx = np.clip(nx, -0.96, 0.96); ny = np.clip(ny, -0.96, 0.96)
    k = np.sqrt(np.clip(nx ** 2 + ny ** 2, 0, None)); over = k > 0.97
    nx = np.where(over, nx / k * 0.97, nx); ny = np.where(over, ny / k * 0.97, ny)
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0.03, 1))
    lines = (ex | np.roll(hand, 1, 0) & ~hand | mask(lambda d: d.ellipse([X(3.62), Y(0.86), X(3.80), Y(0.80)], outline=1))) & body
    fuel = mask(lambda d: d.ellipse([X(3.62), Y(0.86), X(3.80), Y(0.80)], outline=1)) & body
    seats = mask(lambda d: (d.ellipse([X(2.14), Y(1.17), X(2.32), Y(1.02)], fill=1),
                            d.polygon(P([(1.86, 0.96), (2.02, 1.16), (2.14, 1.14), (2.04, 0.96)]), fill=1),
                            d.ellipse([X(2.50), Y(1.07), X(2.62), Y(0.95)], outline=1),
                            d.polygon(P([(1.42, 0.97), (1.60, 1.10), (1.70, 1.08), (1.60, 0.97)]), fill=1))) & glass
    return dict(s=s, w=w, h=h, gy=gy, v=v, nx=nx, ny=ny, nz=nz, lines=lines, fuel=fuel, seats=seats, handm=hand & body, body=body, glass=glass, well=well, frame=frame & ~glass,
                trim=(sill | bpil | intake | louv) & (body | glass), mhead=mhead & ~glass, mstalk=mstalk & ~body,
                head=head, ring=ring, hli=hli, drl=drl, led=led, tail=tail, refl=refl, pipes=pipes & ~body,
                wing=wing & ~body, wingp=wingp & ~body, lipt=lipt, a=allm, ym=ym, xm=xm, d=d,
                wheels=[(X(RW), Y(WR[0]), WR[0] * s, RIM[0] * s), (X(FW), Y(WR[1]), WR[1] * s, RIM[1] * s)])


def wheel(rgb, a, cx, cy, r, rim, ang, blur=0.0, env=(0, 0, 0)):
    x0, x1 = int(cx - r - 1), int(cx + r + 2); y0, y1 = int(cy - r - 1), int(cy + r + 2)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = xx - cx + 0.5, yy - cy + 0.5
    dist = np.hypot(dx, dy); th = np.arctan2(-dy, dx)
    env = np.array(env, float)
    out = np.zeros(dist.shape + (3,)); m = dist <= r
    out[:] = (16, 16, 20)
    out[(dist > rim + 0.5) & (dist < rim + 0.5 + max(1.0, r * 0.1))] = (30, 30, 36)
    out[(dist > r - 1.2) & (dy < -r * 0.5)] = (44, 46, 54)
    inner = dist < rim
    out[inner] = (26, 28, 34)
    out[inner & (dist > rim * 0.30) & (dist < rim * 0.92)] = (58, 60, 68)
    cal = inner & (dist > rim * 0.50) & (dist < rim * 0.95) & (th > 0.15) & (th < 1.05)
    out[cal] = (214, 30, 36); out[cal & (dist > rim * 0.83)] = (150, 18, 24)
    n = 1 if blur < 0.05 else 11
    acc = np.zeros(dist.shape)
    for k in range(n):
        a2 = ang + blur * (k / max(1, n - 1) - 0.5)
        ph = np.cos(5 * (th - a2))
        acc += (np.abs(ph - 0.80) < 0.16) | (ph > 0.96)
    acc /= n
    spoke = inner & (dist > rim * 0.2)
    shade = 0.78 + 0.32 * (-dy / max(r, 1))
    sp = np.array((176, 182, 196)) * shade[..., None] * 0.85 + env * 0.25
    k = (acc * (1.0 if blur < 0.05 else 1.25)).clip(0, 1)[..., None] * spoke[..., None]
    out = out * (1 - k) + sp * k
    out[(dist > rim - 1.0) & (dist <= rim)] = np.array((214, 218, 230)) * 0.88 + env * 0.2
    out[dist < rim * 0.24] = (140, 142, 150); out[dist < rim * 0.12] = (20, 20, 24)
    Hh, Wd = a.shape
    sy0, sx0 = max(y0, 0), max(x0, 0); sy1, sx1 = min(y1, Hh), min(x1, Wd)
    sub = (slice(sy0 - y0, sy1 - y0), slice(sx0 - x0, sx1 - x0))
    mm = m[sub]
    rgb[sy0:sy1, sx0:sx1][mm] = out[sub][mm]
    a[sy0:sy1, sx0:sx1][mm] = 1.0


LIGHT = np.array((0.30, 0.78, 0.55)); LIGHT = LIGHT / np.linalg.norm(LIGHT)


def paint(c, env, env2, streak, gloss, cc):
    """Clear-coated Guards Red: diffuse + environment reflection (night sky / city horizon / wet road) + key spec."""
    nx, ny, nz = c['nx'], c['ny'], c['nz']
    ry, rx = 2 * nz * ny, 2 * nz * nx
    rz = 2 * nz * nz - 1
    lights = 0.45 + 0.55 * np.maximum(0, np.cos(2 * np.pi * (cc * 0.8 + rx * 26 - streak) / 41.0)) ** 3
    sky = (env[None, None, :] * 0.85 + 14) * (0.45 + 1.0 * smooth(0.05, 0.85, ry))[..., None]
    hor = (env2[None, None, :] * 0.6 + 110) * (1.6 * np.exp(-((ry - 0.11) / 0.05) ** 2) * lights)[..., None]
    gnd = np.array((34, 12, 20))[None, None, :] * np.ones_like(ry)[..., None]
    refl = np.where((ry > 0)[..., None], sky, gnd) + hor
    fres = (0.30 + 0.5 * (1 - nz) ** 2)[..., None] * gloss
    dif = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    base = np.array((214, 22, 30)) * (0.30 + 0.62 * dif)[..., None]
    spec = np.clip(rx * LIGHT[0] + ry * LIGHT[1] + rz * LIGHT[2], 0, 1) ** 40
    col = base * (1 - fres * 0.5) + refl * fres + (np.array((255, 236, 226)) * spec[..., None] * 1.1)
    col += (np.where(c['d'] == 0, 70, np.where(c['d'] == 1, 30, 0)) * c['body'])[..., None]
    col[c['lines']] *= 0.35
    col[c['handm']] = col[c['handm']] * 0.6 + 90
    return np.clip(col, 0, 255)


def side_frame(c, ang, blur=0.0, env=(30, 60, 90), env2=None, streak=0.0, lights=True, spoiler=False, gloss=1.0):
    h, w = c['h'], c['w']
    rr, cc = np.mgrid[0:h, 0:w]
    env = np.array(env, float); env2 = env if env2 is None else np.array(env2, float)
    per = max(60, int(c['s'] * 2.2))
    band = np.maximum(0, 1 - np.abs(((cc + 0.55 * rr - streak) % per) - per / 2) / max(2.5, c['s'] * 0.09))
    band2 = np.maximum(0, 1 - np.abs(((cc + 0.35 * rr - streak * 0.6) % (per * 1.7)) - per * 0.85) / max(1.5, c['s'] * 0.035))
    rgb = paint(c, env, env2, streak, gloss, cc)
    e = np.zeros((h, w, 3))
    gtop = np.where(c['glass'].any(0), np.argmax(c['glass'], 0), 0)
    gd = (rr - gtop[None, :]) / max(1, 0.26 * c['s'])
    gv = 0.52 - 0.36 * np.clip(gd, 0, 1) + band * 0.45 + band2 * 0.4
    gi = np.clip(np.floor(gv * 5 + (bayer(h, w) - 0.5) * 0.5), 0, 5).astype(int)
    rgb = np.clip(np.floor(rgb / 11 + (bayer(h, w)[..., None] - 0.5) * 0.55 + 0.5) * 11, 0, 255)
    G = GLASS[gi] * 0.85 + env * 0.18
    G = np.where(c['seats'][..., None], G * 0.35, G)
    rgb = np.where(c['glass'][..., None], G, rgb)
    rgb[c['frame']] = np.array((168, 172, 184)) * 0.7 + env * 0.3
    rgb[c['well']] = (5, 3, 7)
    rgb[c['trim']] = (14, 14, 18)
    rgb[c['lipt']] = RED[5] * 0.8 + env * 0.2
    m = c['mhead']
    rgb[m] = RED[3] * 0.85 + env * 0.15
    rgb[m & ~np.roll(m, 1, 0)] = RED[6]
    rgb[m & ~np.roll(m, -1, 0)] = RED[1]
    rgb[c['mstalk']] = (14, 14, 18)
    rgb[c['pipes']] = (150, 152, 160)
    a = c['a'].astype(float).copy()
    if spoiler:
        for k_, col in (('wingp', (14, 14, 18)), ('wing', (20, 20, 26))):
            mm = c[k_]; rgb[mm] = col; a[mm] = 1
        rgb[c['wing'] & ~np.roll(c['wing'], 1, 0)] = RED[4]
    rgb[c['head']] = np.array((150, 158, 176)) * 0.8 + env * 0.2
    rgb[c['head'] & ~np.roll(c['head'], -2, 0)] = (70, 76, 96)
    rgb[c['ring']] = np.array((206, 212, 224)) * 0.85 + env * 0.15
    if lights:
        rgb[c['hli']] = (150, 170, 210); e[c['hli']] = (90, 110, 160)
        rgb[c['drl']] = (255, 255, 255); e[c['drl']] = (255, 255, 255)
        rgb[c['led']] = (255, 240, 220); e[c['led']] = (230, 200, 160)
        rgb[c['tail']] = (255, 44, 50); e[c['tail']] = (255, 30, 34)
        rgb[c['refl']] = (200, 20, 30); e[c['refl']] = (120, 10, 16)
    else:
        rgb[c['tail']] = (120, 16, 22)
    for (cx, cy, r, rim) in c['wheels']:
        wheel(rgb, a, cx, cy, r, rim, ang, blur, env)
    return dict(rgb=rgb, a=a, e=e)


# ---------------- rear view ----------------
def rear(Wpx):
    s = Wpx / 1.85
    w, h = int(Wpx) + 8, int(1.42 * s) + 8
    gy = h - 3; cx = w / 2
    X = lambda x: cx + x * s
    Y = lambda y: gy - y * s
    half = [(0.0, 1.30), (0.22, 1.29), (0.36, 1.23), (0.46, 1.10), (0.53, 0.99), (0.66, 0.965), (0.82, 0.93),
            (0.905, 0.86), (0.925, 0.70), (0.92, 0.50), (0.90, 0.30), (0.86, 0.15)]
    pts = catmull(half, 6)
    full = ([(X(x), Y(y)) for x, y in pts] + [(X(0.80), Y(0.12)), (X(-0.80), Y(0.12))]
            + [(X(-x), Y(y)) for x, y in reversed(pts)])

    def mask(fn):
        im = Image.new('L', (w, h), 0); fn(ImageDraw.Draw(im)); return np.asarray(im) > 0

    def sym(poly): return [(X(x), Y(y)) for x, y in poly]

    def rect(d, xa, ya, xb, yb): d.rectangle([min(X(xa), X(xb)), Y(max(ya, yb)), max(X(xa), X(xb)), Y(min(ya, yb))], fill=1)
    body = mask(lambda d: d.polygon(full, fill=1))
    glass = mask(lambda d: d.polygon(sym([(-0.36, 1.06), (0.36, 1.06), (0.24, 1.24), (-0.24, 1.24)]), fill=1)) & body
    grille = mask(lambda d: d.polygon(sym([(-0.44, 0.93), (0.44, 0.93), (0.42, 1.03), (-0.42, 1.03)]), fill=1)) & body
    wing = mask(lambda d: d.polygon(sym([(-0.62, 1.035), (0.62, 1.035), (0.60, 1.085), (-0.60, 1.085)]), fill=1))
    lamps = mask(lambda d: [d.polygon(sym([(sg * 0.40, 0.845), (sg * 0.905, 0.86), (sg * 0.915, 0.80), (sg * 0.42, 0.815)]), fill=1)
                            for sg in (-1, 1)]) & body
    bar = mask(lambda d: rect(d, -0.42, 0.825, 0.42, 0.838)) & body
    badge = mask(lambda d: [rect(d, x, 0.775, x + 0.025, 0.79) for x in np.linspace(-0.22, 0.20, 7)]) & body
    refl = mask(lambda d: [rect(d, sg * 0.62, 0.41, sg * 0.80, 0.43) for sg in (-1, 1)]) & body
    diff = mask(lambda d: d.polygon(sym([(-0.86, 0.13), (0.86, 0.13), (0.90, 0.30), (-0.90, 0.30)]), fill=1)) & body
    plate = mask(lambda d: rect(d, -0.26, 0.44, 0.26, 0.56)) & body
    pipes = mask(lambda d: [d.ellipse([X(o - 0.055), Y(0.27), X(o + 0.055), Y(0.19)], fill=1) for o in (-0.70, -0.57, 0.57, 0.70)])
    pin = mask(lambda d: [d.ellipse([X(o - 0.035), Y(0.255), X(o + 0.035), Y(0.205)], fill=1) for o in (-0.70, -0.57, 0.57, 0.70)])
    tyres = mask(lambda d: [rect(d, sg * 0.60, 0.0, sg * 0.90, 0.17) for sg in (-1, 1)])
    rr, cc = np.mgrid[0:h, 0:w]
    ym = (gy - rr) / s; xm = (cc - cx) / s
    toprow = np.argmax(body, axis=0); d = rr - toprow[None, :]
    ax = np.abs(xm)
    v = 0.18 + 0.50 * smooth(0.25, 0.95, ym) - 0.28 * smooth(0.62, 0.93, ax)
    v += np.where(d == 0, 0.42, np.where(d == 1, 0.18, 0))
    v += 0.42 * np.exp(-((ax - 0.74) / 0.13) ** 2 - ((ym - 0.92) / 0.035) ** 2)
    v += 0.25 * np.exp(-((ax - 0.20) / 0.40) ** 2 - ((ym - 0.70) / 0.06) ** 2)
    v -= 0.20 * (ym < 0.38)
    return dict(s=s, w=w, h=h, gy=gy, v=v, body=body, glass=glass, grille=grille, wing=wing & ~glass, lamps=lamps,
                bar=bar, badge=badge, refl=refl, diff=diff, plate=plate, pipes=pipes, pin=pin, tyres=tyres & ~body,
                a=body | tyres | wing, ym=ym)


def rear_frame(c, env=(30, 50, 90), brake=0.0, glow=1.0):
    h, w = c['h'], c['w']
    env = np.array(env, float)
    idx = np.clip(np.floor(c['v'] * (NT - 0.4) + (bayer(h, w) - 0.5) * 0.5), 0, NT - 1).astype(int)
    rgb = RED[idx] * 0.85 + env * (0.08 + 0.22 * smooth(0.5, 1.0, c['ym']))[..., None]
    e = np.zeros((h, w, 3))
    rgb[c['glass']] = GLASS[2] * 0.8 + env * 0.25
    rgb[c['glass'] & ~np.roll(c['glass'], 1, 0)] = GLASS[4]
    rgb[c['grille']] = (12, 12, 16)
    rgb[c['grille'] & ((np.arange(w)[None, :] % 2) == 0)] = (36, 36, 44)
    rgb[c['wing']] = (22, 22, 28); rgb[c['wing'] & ~np.roll(c['wing'], 1, 0)] = RED[5]
    rgb[c['diff']] = (16, 16, 20); rgb[c['plate']] = (200, 204, 212)
    rgb[c['plate'] & ~np.roll(c['plate'], 2, 1)] = (40, 70, 170)
    rgb[c['pipes']] = (176, 178, 188); rgb[c['pin']] = (8, 8, 10)
    rgb[c['tyres']] = (14, 14, 18)
    rgb[c['badge']] = (190, 190, 200)
    k = glow * (0.85 + 0.6 * brake)
    rgb[c['lamps']] = (255, 60, 60); e[c['lamps']] = np.array((255, 30, 34)) * k
    rgb[c['bar']] = (255, 50, 54); e[c['bar']] = np.array((255, 26, 30)) * k * 0.9
    rgb[c['refl']] = (190, 20, 30); e[c['refl']] = np.array((120, 10, 16)) * k
    return dict(rgb=rgb, a=c['a'].astype(float), e=e)
