"""Stops first: which hypercar stops first, 0-400-0 km/h? Vertical 1080x1920 @30fps, white blueprint line art.

Two original side-view hypercars (red "CHIRON", blue "NEVERA") on stacked lanes with clocks and speed counters.
Ink line art draws on over a speed-heat overlay that fades out in the first 2 s. All beats are anchored to the
user's voiceover via words.json (align.py). Audio = user's VO + user's music 18 dB under, -14 LUFS.
usage: python render.py still OUTDIR t1 t2 ... | python render.py video OUT.mp4 [END [START]] | python render.py scan
"""
import json, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'videos/new-car-trap/src'))
import sfx  # noqa: E402

DUR = 18.4                                   # voiceover (17.90 s) + 0.5 s
W, H, FPS, SR = 1080, 1920, 30, sfx.SR
OUT = ROOT / 'out/stops-first'
VO_WAV, MUSIC_WAV = OUT / 'vo.wav', OUT / 'music.wav'
WORDS = json.load(open(HERE / 'words.json'))[0]
INK = (18, 18, 22)
PAPER = (251, 251, 248)
RED, BLUE = (214, 48, 40), (36, 96, 214)
FONT = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
FONT_M = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf'
_F = {}


def font(path, size):
    if (path, size) not in _F:
        try: _F[path, size] = ImageFont.truetype(path, size)
        except OSError: _F[path, size] = ImageFont.truetype('/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf', size)
    return _F[path, size]


def ss(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def lerp(a, b, k): return a + (b - a) * k


def wt(prefix, nth=0):
    hits = [w for w in WORDS if ''.join(c for c in w['w'].lower() if c.isalnum()).startswith(prefix) and w['ok']]
    return hits[nth]['s']


def pop(t, t0, d=0.25):
    u = (t - t0) / d
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    return 1 + 0.25 * math.sin(u * math.pi) * (1 - u) - (1 - u) ** 3


# ---------------------------------------------------------------- word anchors
T_GO = wt('same')                            # launch
T_400 = wt('hour') + 0.2                     # both counters reach 400
T_BRK = wt('then')                           # braking phase
T_CHIRON, T_42 = wt('chiron'), wt('42')
T_NEVERA, T_30 = wt('nevera'), wt('30')      # blue clock freezes, blue car stops
T_12 = wt('twelve')                          # red stops, gap marker
T_RACE, T_PARK = wt('race'), wt('parked')
T_Q, T_ONE = wt('would', 1), wt('one')
END_VO = max(w['e'] for w in WORDS)
assert END_VO + 0.45 <= DUR, END_VO
LOOP0 = DUR - 0.35                           # final dissolve back into frame 0

# total record times (FACTS.md); the accel/brake split of each clock is illustrative (75 % accel)
CARS = {'red': dict(name='CHIRON', col=RED, total=41.96, stop=T_12, y=1010, hy=610),
        'blue': dict(name='NEVERA', col=BLUE, total=29.93, stop=T_30, y=1480, hy=1066)}
SPLIT = 0.75


def speed(c, t):
    """km/h on the car's own record run, mapped onto the video clock."""
    if t < T_GO: return 0.0
    if t < T_400: u = (t - T_GO) / (T_400 - T_GO); return 400 * (1 - (1 - u) ** 2.2)
    if t < T_BRK: return 400.0
    u = (t - T_BRK) / (c['stop'] - T_BRK)
    return 0.0 if u >= 1 else 400 * (1 - u) ** 0.9


def clock(c, t):
    if t < T_GO: return 0.0
    a = c['total'] * SPLIT
    if t < T_BRK: return a * (t - T_GO) / (T_BRK - T_GO)
    return min(c['total'], a + (c['total'] - a) * (t - T_BRK) / (c['stop'] - T_BRK))


VMAX = 2600.0                                # ground scroll px/s at 400 km/h
_TS = np.arange(0, DUR + 1, 1 / 240)
for c in CARS.values():
    v = np.array([speed(c, x) for x in _TS]) / 400 * VMAX
    c['dist'] = np.concatenate([[0], np.cumsum(v[:-1]) / 240])


def dist(c, t): return float(np.interp(t, _TS, c['dist']))


# ---------------------------------------------------------------- car geometry (units of car length, y up)
L = 900                                       # on-screen car length px
SS = 2                                        # supersampling for the line art
PAD, HMAX = 40, 0.31
R_W = 0.075


def cubic(p0, p1, p2, p3, n=22):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3).tolist()


def path(start, *segs):
    pts = [list(start)]
    for s in segs:
        pts += cubic(pts[-1], *s)[1:] if len(s) == 3 else [list(s[0])]
    return pts


def ellipse(cx, cy, rx, ry, a0=0, a1=360, n=40, tilt=0):
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        x, y = rx * math.cos(a), ry * math.sin(a)
        ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
        out.append([cx + x * ct - y * st, cy + x * st + y * ct])
    return out


def chiron():
    sil = path((0.03, 0.045), ((0.015, 0.075),), ((0.0, 0.10),),
               ((-0.004, 0.135), (0.0, 0.165), (0.02, 0.182)), ((0.07, 0.19),),
               ((0.16, 0.198), (0.28, 0.218), (0.36, 0.246)),
               ((0.42, 0.266), (0.52, 0.272), (0.575, 0.262)),
               ((0.625, 0.252), (0.67, 0.215), (0.715, 0.186)),
               ((0.78, 0.174), (0.88, 0.163), (0.945, 0.145)),
               ((0.985, 0.134), (1.002, 0.115), (1.0, 0.092)),
               ((1.0, 0.064), (0.99, 0.05), (0.97, 0.045)), ((0.03, 0.045),))
    strokes = [
        (sil, 3),
        (path((0.47, 0.243), ((0.52, 0.252), (0.56, 0.252), (0.60, 0.243)), ((0.645, 0.214),), ((0.665, 0.196),),
              ((0.60, 0.192),), ((0.525, 0.196),), ((0.47, 0.243),)), 2),                        # side window
        (path((0.505, 0.255), ((0.40, 0.245), (0.355, 0.13), (0.42, 0.088)),
              ((0.47, 0.062), (0.56, 0.068), (0.66, 0.074))), 6),                                  # the C-line
        (path((0.488, 0.236), ((0.405, 0.222), (0.38, 0.13), (0.43, 0.102)),
              ((0.48, 0.08), (0.56, 0.085), (0.65, 0.088))), 2),
        (path((0.30, 0.17), ((0.33, 0.20), (0.37, 0.205), (0.395, 0.19)), ((0.37, 0.14), (0.36, 0.11), (0.38, 0.095)),
              ((0.33, 0.10), (0.29, 0.13), (0.30, 0.17))), 2),                                     # intake inside the C
        (path((0.715, 0.186), ((0.77, 0.178), (0.86, 0.17), (0.93, 0.142))), 1),                   # hood crease
        (path((0.60, 0.192), ((0.61, 0.15), (0.62, 0.11), (0.64, 0.082))), 1),                     # door seam
        (ellipse(0.958, 0.09, 0.017, 0.038, tilt=-6), 3),                                          # tall oval front opening
        *[(path((0.946, y), ((0.97, y),)), 1) for y in (0.07, 0.08, 0.09, 0.10, 0.11)],
        (path((0.872, 0.152), ((0.945, 0.134),)), 3), (path((0.875, 0.143), ((0.94, 0.128),)), 1),  # headlight slit
        (path((0.0, 0.178), ((0.09, 0.195),)), 4),                                                 # spoiler lip
        (path((0.004, 0.158), ((0.05, 0.164),)), 3),                                               # tail light
        (path((0.655, 0.21), ((0.68, 0.218), (0.69, 0.205), (0.672, 0.198))), 2),                  # mirror
        (path((0.10, 0.19), ((0.20, 0.20), (0.30, 0.22), (0.37, 0.248))), 1),                      # engine cover line
    ]
    strokes += [(path((x, 0.048), ((x - 0.006, 0.08),)), 1) for x in (0.035, 0.05, 0.065)]       # diffuser fins
    return dict(sil=sil, strokes=strokes, wheels=(0.205, 0.80), spokes=10)


def nevera():
    sil = path((0.025, 0.05), ((0.0, 0.088),),
               ((-0.006, 0.128), (0.0, 0.155), (0.015, 0.166)), ((0.055, 0.17),),
               ((0.18, 0.19), (0.36, 0.238), (0.50, 0.261)),
               ((0.56, 0.27), (0.625, 0.266), (0.672, 0.246)),
               ((0.73, 0.216), (0.78, 0.178), (0.84, 0.157)),
               ((0.91, 0.146), (0.965, 0.132), (0.99, 0.106)),
               ((1.006, 0.084), (1.0, 0.06), (0.978, 0.05)), ((0.025, 0.05),))
    strokes = [
        (sil, 3),
        (path((0.27, 0.205), ((0.40, 0.236), (0.55, 0.256), (0.645, 0.241)), ((0.722, 0.196),),
              ((0.62, 0.186), (0.45, 0.188), (0.27, 0.205))), 2),                                  # teardrop canopy
        (path((0.585, 0.25), ((0.59, 0.22), (0.595, 0.20), (0.60, 0.188))), 1),                    # B-pillar
        (path((0.66, 0.178), ((0.56, 0.16), (0.44, 0.13), (0.335, 0.088))), 3),                    # door blade
        (path((0.66, 0.158), ((0.56, 0.14), (0.46, 0.115), (0.37, 0.083))), 1),
        (path((0.335, 0.088), ((0.30, 0.10), (0.285, 0.13), (0.30, 0.155)), ((0.33, 0.15), (0.36, 0.13), (0.37, 0.083))), 2),
        (path((0.006, 0.148), ((0.03, 0.153), (0.05, 0.157), (0.075, 0.16))), 7),                 # full-width light bar
        (path((0.895, 0.137), ((0.94, 0.127), (0.975, 0.112), (0.992, 0.098))), 4),                # front light bar
        (path((0.93, 0.058), ((0.995, 0.066),)), 2),                                               # splitter
        (path((0.72, 0.205), ((0.745, 0.21), (0.75, 0.198), (0.733, 0.193))), 2),                  # camera mirror
        (path((0.06, 0.168), ((0.20, 0.186), (0.34, 0.226), (0.47, 0.25))), 1),                    # shoulder line
    ]
    strokes += [(path((x, 0.053), ((x - 0.005, 0.082),)), 1) for x in (0.03, 0.045, 0.06)]
    return dict(sil=sil, strokes=strokes, wheels=(0.19, 0.81), spokes=5)


CARS['red'].update(chiron()); CARS['blue'].update(nevera())
SW, SH = L + 2 * PAD, int(HMAX * L) + 2 * PAD
GY_S = PAD + HMAX * L                         # sprite y of the ground


def to_px(p, k=SS): return ((PAD + p[0] * L) * k, (GY_S - p[1] * L) * k)


def plen(pts): return float(sum(math.dist(a, b) for a, b in zip(pts, pts[1:])))


def partial(pts, f):
    if f >= 1: return pts
    tot, acc, out = plen(pts) * f, 0.0, [pts[0]]
    for a, b in zip(pts, pts[1:]):
        dd = math.dist(a, b)
        if acc + dd >= tot:
            k = (tot - acc) / dd if dd else 0; out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)); break
        out.append(b); acc += dd
    return out


HEAT = np.array([(30, 60, 220), (0, 190, 230), (40, 200, 90), (250, 225, 40), (250, 130, 20), (230, 30, 30)], np.float32)


def heat_map(w, h):
    """Speed-heat (pressure-map style): hot at the nose, cold at the tail, warm along the top."""
    x = np.linspace(0, 1, w)[None, :]; y = np.linspace(0, 1, h)[:, None]
    v = np.clip(0.85 * x ** 1.6 + 0.25 * (1 - y) * x + 0.05, 0, 1) * (len(HEAT) - 1)
    i = np.clip(v.astype(int), 0, len(HEAT) - 2); f = (v - i)[..., None]
    return HEAT[i] * (1 - f) + HEAT[i + 1] * f


_HEAT = heat_map(SW * SS, SH * SS)


def body_sprite(c, p=1.0, heat=0.0):
    """RGBA body at 1x: tint fill (+ heat overlay), ink strokes drawn on to fraction p, wheel arches cut out."""
    key = (p >= 1, heat <= 0)
    if key == (True, True) and 'body' in c: return c['body']
    w, h = SW * SS, SH * SS
    sil = [to_px(q) for q in c['sil']]
    mask = Image.new('L', (w, h)); ImageDraw.Draw(mask).polygon(sil, fill=255)
    m = np.asarray(mask, np.float32)[..., None] / 255
    tint = np.array(c['col'], np.float32) * 0.22 + np.array(PAPER, np.float32) * 0.78
    hm = np.roll(_HEAT, int(60 * math.sin(c.get('_t', 0) * 5)), 1) if heat > 0 else _HEAT   # shimmering heat
    rgb = tint * (1 - heat) + hm * heat
    a = m * 255 * (0.96 * (1 - heat) + 0.92 * heat)
    img = Image.fromarray(np.concatenate([np.broadcast_to(rgb, (h, w, 3)), a], 2).astype(np.uint8))
    d = ImageDraw.Draw(img)
    n = len(c['strokes'])
    for k, (pts, lw) in enumerate(c['strokes']):
        f = (p - 0.25 * k / n) / 0.75 if p < 1 else 1
        if f <= 0: continue
        q = partial([to_px(x) for x in pts], min(1, f))
        if len(q) > 1: d.line(q, fill=INK + (255,), width=lw * 2 * SS // 2 + SS, joint='curve')
    arr = np.array(img)
    yy, xx = np.mgrid[0:h, 0:w]
    for xw in c['wheels']:                                    # wheel arches
        cx, cy = to_px((xw, R_W)); r = (R_W + 0.013) * L * SS
        arr[(xx - cx) ** 2 + (yy - cy) ** 2 < r * r] = 0
    img = Image.fromarray(arr); d = ImageDraw.Draw(img)
    for xw in c['wheels']:
        cx, cy = to_px((xw, R_W)); r = (R_W + 0.013) * L * SS
        arc = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-180, 1, 6)]
        top = [q for q in arc if q[1] <= to_px((0, 0.047))[1]]
        top = partial(top, min(1, p * 1.3))
        if len(top) > 1: d.line(top, fill=INK + (255,), width=3 * SS, joint='curve')
    out = img.resize((SW, SH), Image.Resampling.LANCZOS)
    if key == (True, True): c['body'] = out
    return out


def wheel_sprite(c, blur=0.0, heat=0.0, alpha=1.0):
    """Wheel at 1x (unrotated): tyre, rim, spokes (blurred into rings when fast), caliper drawn separately."""
    r = R_W * L; n = int(2 * r + 8); k = SS; img = Image.new('RGBA', (n * k, n * k)); d = ImageDraw.Draw(img)
    o = n * k / 2; R = r * k
    def circ(rr, **kw): d.ellipse([o - rr, o - rr, o + rr, o + rr], **kw)
    tyre = tuple(int(x) for x in np.array([60, 62, 70]) * (1 - heat) + np.array(HEAT[0]) * heat)
    circ(R, fill=tyre + (255,), outline=INK + (255,), width=3 * k)
    circ(R * 0.74, fill=PAPER + (255,), outline=INK + (255,), width=2 * k)
    circ(R * 0.6, outline=(150, 150, 150, 255), width=1 * k)
    sp = c['spokes']
    if blur < 1:
        a = int(255 * (1 - blur))
        for j in range(sp):
            ang = 2 * math.pi * j / sp
            for off in ((-0.09, 0.09) if sp == 5 else (0,)):
                x0, y0 = o + math.cos(ang + off * 0.6) * R * 0.17, o + math.sin(ang + off * 0.6) * R * 0.17
                x1, y1 = o + math.cos(ang + off) * R * 0.72, o + math.sin(ang + off) * R * 0.72
                d.line([x0, y0, x1, y1], fill=INK + (a,), width=(3 if sp == 5 else 2) * k)
    if blur > 0:
        for rr in (0.3, 0.42, 0.55, 0.66):
            circ(R * rr, outline=(110, 110, 120, int(200 * blur)), width=1 * k)
    circ(R * 0.16, fill=PAPER + (255,), outline=INK + (255,), width=2 * k)
    circ(R * 0.05, fill=INK + (255,))
    out = img.resize((n, n), Image.Resampling.LANCZOS)
    if alpha < 1:
        a = np.array(out); a[..., 3] = (a[..., 3] * alpha).astype(np.uint8); out = Image.fromarray(a)
    return out


def caliper(d, cx, cy, col):
    r = R_W * L * 0.62
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-150, -84, 6)]
    d.line(pts, fill=col, width=9, joint='curve')


# ---------------------------------------------------------------- scene
def grid(w, h):
    img = Image.new('RGB', (w, h), PAPER); d = ImageDraw.Draw(img)
    for x in range(0, w, 30): d.line([x, 0, x, h], fill=(232, 238, 244) if x % 150 else (214, 224, 236), width=1)
    for y in range(0, h, 30): d.line([0, y, w, y], fill=(232, 238, 244) if y % 150 else (214, 224, 236), width=1)
    return img


GRID = None


def build_bg():
    img = Image.new('RGB', (W, H), PAPER); d = ImageDraw.Draw(img)
    for x in range(0, W, 30): d.line([x, 0, x, H], fill=(232, 238, 244) if x % 150 else (214, 224, 236), width=1)
    for y in range(0, H, 30): d.line([0, y, W, y], fill=(232, 238, 244) if y % 150 else (214, 224, 236), width=1)
    y = 1560
    d.line([60, y, 1020, y], fill=INK, width=3); d.line([60, y + 64, 1020, y + 64], fill=INK, width=1)
    for x in (60, 560, 1020): d.line([x, y, x, y + 64], fill=INK, width=1)
    d.text((76, y + 32), '0 → 400 → 0 KM/H', font=font(FONT_B, 28), fill=INK, anchor='lm')
    d.text((576, y + 32), 'MAKER-REPORTED TIMES', font=font(FONT_B, 24), fill=(110, 110, 120), anchor='lm')
    return img


def x0_of(c, t):
    """Screen x of the car's tail: pulled forward on launch, settles back under braking."""
    a = ss((t - T_GO) / (T_400 - T_GO + 0.6)); b = ss((t - T_BRK) / (c['stop'] - T_BRK))
    park = -40 * ss((t - T_RACE - 0.15) / (T_PARK - T_RACE - 0.1)) if c['name'] == 'NEVERA' else 0   # reverses into a bay
    return 40 + 90 * a - 70 * b + park


def pitch(c, t):
    """Body pitch in degrees (+ = nose down) and lift in px: squat on launch, dive under braking, rebound at stop."""
    sq = -1.4 * math.exp(-max(0, t - T_GO) * 2.5) * (t >= T_GO)
    dive = 1.6 * ss((t - T_BRK) / 0.35) * (t < c['stop'])
    reb = 0.0
    if t >= c['stop']:
        u = t - c['stop']; reb = 1.6 * math.exp(-u * 5) * math.cos(u * 16)
    return sq + dive + reb


def draw_lane(img, c, t, draw_p, heat):
    d = ImageDraw.Draw(img)
    gy = c['y']; dd = dist(c, t); x0 = x0_of(c, t); v = speed(c, t)
    off = int(dd * 0.4) % 150                                             # blueprint grid scrolls in the lane (parallax)
    img.paste(GRID.crop((off, gy - 300, off + W, gy)), (0, gy - 300))
    d.line([0, gy, W, gy], fill=INK, width=3)
    for k in range(-1, W // 60 + 2):                                     # scrolling distance ticks
        x = k * 60 - dd % 60
        d.line([x, gy + 4, x - 14, gy + 18], fill=(120, 120, 130), width=2)
    sx = 40 + L + 14 - dd                                                 # start line, left behind on launch
    if sx > -20:
        for y in range(gy - 200, gy, 22): d.line([sx, y, sx, y + 12], fill=INK, width=3)
        d.text((sx + 8, gy - 26), 'START', font=font(FONT_B, 22), fill=INK)
    if v > 40:                                                            # ink speed lines behind the car
        amt = min(1, v / 300)
        rng = np.random.default_rng(3 if c['name'] == 'CHIRON' else 4)
        for k in range(16):
            yy = gy - 20 - rng.uniform(0, 0.27 * L); ln = rng.uniform(80, 320) * amt
            xx = x0 + 30 - ((rng.uniform(0, 700) + dd * 0.9) % 700) * 0.5
            d.line([xx - ln, yy, xx, yy], fill=(40, 40, 48), width=2 if k % 3 else 3)
    d.ellipse([x0 + 20, gy - 12, x0 + L - 10, gy + 8], fill=(214, 214, 214))  # ground shadow
    ang = -math.degrees((dd + x0) / (R_W * L))
    w_px = v / 400 * VMAX / (R_W * L) / FPS                                # rad per frame
    blur = min(1, max(0, (w_px - 0.25) / 0.5))
    ws = wheel_sprite(c, blur, heat, 0.35 + 0.65 * min(1, draw_p))
    ws = ws.rotate(ang, Image.Resampling.BICUBIC)
    pa = pitch(c, t)
    jit = (math.sin(t * 157 + gy) * 1.2 * min(1, v / 300)) if v > 60 else 0       # road buzz at speed
    if t < T_GO or (c['name'] == 'CHIRON' and t > c['stop'] + 0.4): jit = 1.6 * math.sin(t * 70 + gy)   # W16 idle
    if c['name'] == 'NEVERA' and t >= T_RACE:                                     # parking bay draws on behind it
        u = ss((t - T_RACE) / 0.35); bx0, bx1 = 20 - 14, 20 + L + 14
        for xb in (bx0, bx1): d.line([xb, gy, xb, gy - 150 * u], fill=BLUE, width=6)
        for xx in range(int(bx0), int(lerp(bx0, bx1, u)), 40): d.line([xx, gy + 6, xx + 22, gy + 6], fill=BLUE, width=6)
    for xw in c['wheels']:
        cx, cy = x0 + xw * L, gy - R_W * L
        well = R_W * L + 10
        d.pieslice([cx - well, cy - well, cx + well, cy + well], 180, 360, fill=(70, 70, 78))
        img.alpha_composite(ws, (int(cx - ws.width / 2), int(cy - ws.height / 2)))
        caliper(d, cx, cy, c['col'] if heat < 0.5 else INK)
    body = body_sprite(c, draw_p, heat)
    piv = (PAD + 0.5 * L, GY_S)
    lift = -abs(pa) * 1.5
    body = body.rotate(-pa, Image.Resampling.BICUBIC, center=piv)
    img.alpha_composite(body, (int(x0 - PAD), int(round(gy - GY_S + lift + jit))))


# ---------------------------------------------------------------- UI
BOXES = []
SAFE = (0, 0.12 * H, 0.85 * W, 0.62 * H)


def text(img, xy, s, f, col=INK, anchor='la', sc=1.0, box=True):
    if sc <= 0: return
    if sc != 1:
        f = font(f.path, max(4, int(f.size * sc)))
    d = ImageDraw.Draw(img); d.text(xy, s, font=f, fill=col, anchor=anchor)
    if box: BOXES.append(d.textbbox(xy, s, font=f, anchor=anchor))


def lane_header(img, c, t):
    hy = c['hy']; col = c['col']; d = ImageDraw.Draw(img)
    hi = pop(t, T_CHIRON if c['name'] == 'CHIRON' else T_NEVERA, 0.3) if t >= T_CHIRON - 0.01 else 0
    text(img, (60, hy), c['name'], font(FONT, 58), col)
    v = speed(c, t)
    text(img, (62, hy + 72), f'{int(round(v)):3d} KM/H', font(FONT_M, 40), (70, 70, 80))
    cl = clock(c, t); done = t >= c['stop']
    sc = 1 + 0.15 * math.sin(math.pi * (t - c['stop']) / 0.3) if done and t < c['stop'] + 0.3 else 1
    if done:
        bb = d.textbbox((900, hy + 4), f'{cl:05.2f} s', font=font(FONT_M, 76), anchor='ra')
        d.rectangle([bb[0] - 14, bb[1] - 10, bb[2] + 14, bb[3] + 12], fill=col)
        text(img, (900, hy + 4), f'{cl:05.2f} s', font(FONT_M, 76), PAPER, 'ra', sc)
    else:
        text(img, (900, hy + 4), f'{cl:05.2f} s', font(FONT_M, 76), INK, 'ra')
        if T_GO <= t < T_BRK:                                             # fast-forward marker while time is compressed
            x = 470
            for k in range(2): d.polygon([(x + k * 22, hy + 22), (x + k * 22 + 20, hy + 40), (x + k * 22, hy + 58)], fill=(150, 150, 160))
    if 0 < hi and t < (T_42 if c['name'] == 'CHIRON' else T_30) + 0.6:   # highlight while the voice names the car
        d.line([60, hy + 66, 60 + 250 * min(1, hi), hy + 66], fill=col, width=6)


PXS = 19.0                                   # timeline px per record second


def timeline(img, t, a):
    d = ImageDraw.Draw(img)
    for k, key in enumerate(('red', 'blue')):
        c = CARS[key]; y = 372 + k * 62
        d.rectangle([60, y, 60 + 42 * PXS + 6, y + 36], outline=(190, 196, 206), width=2)
        n = clock(c, t) * PXS
        if n > 1: d.rectangle([60, y, 60 + n, y + 36], fill=c['col'])
        text(img, (70 if n > 130 else 60 + n + 10, y + 18), c['name'], font(FONT_B, 24), PAPER if n > 130 else c['col'], 'lm')
    if t >= T_42:                                                         # the record named by the voice
        x = 60 + 41.96 * PXS; s = pop(t, T_42, 0.25)
        for y in range(352, 420, 12): d.line([x, y, x, y + 7], fill=INK, width=3)
        text(img, (x, 346), '≈42 s', font(FONT_B, 30), RED, 'rb', s)
    if t >= T_30:
        x = 60 + 29.93 * PXS; s = pop(t, T_30, 0.25)
        for y in range(434, 482, 12): d.line([x, y, x, y + 7], fill=INK, width=3)
        text(img, (x - 10, 497), '≈30 s', font(FONT_B, 30), BLUE, 'rt', s)
    if t >= T_12:                                                         # the 12 s gap, dimension-line style
        u = ss((t - T_12) / 0.3); xa, xb = 60 + 29.93 * PXS, 60 + 41.96 * PXS
        y = 520; xm = lerp(xa, xb, u)
        d.line([xa, 470, xa, y + 14], fill=INK, width=2); d.line([xb, 410, xb, y + 14], fill=INK, width=2)
        d.line([xa, y, xm, y], fill=INK, width=4)
        if u > 0.9:
            d.polygon([(xa, y), (xa + 16, y - 9), (xa + 16, y + 9)], fill=INK)
            d.polygon([(xb, y), (xb - 16, y - 9), (xb - 16, y + 9)], fill=INK)
        q = wt('quicker'); qs = 1 + 0.2 * math.sin(min(1, max(0, (t - q) / 0.5)) * math.pi)
        text(img, ((xa + xb) / 2, y + 12), '12 s', font(FONT, 52), INK, 'mt', pop(t, T_12 + 0.1, 0.3) * qs)


def panel(img, t):
    if t < T_GO:                                                          # hook: frame 1
        out = ss((t - (T_GO - 0.25)) / 0.25)
        dy = -int(60 * out)
        if out < 1:
            col = tuple(int(lerp(a, b, out)) for a, b in zip(INK, PAPER))
            text(img, (56, 268 + dy), 'WHICH STOPS', font(FONT, 114), col)
            text(img, (56, 396 + dy), 'FIRST?', font(FONT, 114), col)
            d = ImageDraw.Draw(img)
            if out == 0: d.line([60, 540 + dy, 60 + 420 * ss(t / 0.8), 540 + dy], fill=RED, width=10)
        return
    if t >= T_Q:                                                          # question + poll
        text(img, (60, 268), 'WOULD YOU TAKE', font(FONT, 74), INK, sc=pop(t, T_Q, 0.25))
        text(img, (60, 352), 'THE ELECTRIC ONE?', font(FONT, 74), BLUE, sc=pop(t, wt('electric'), 0.25))
        d = ImageDraw.Draw(img)
        for k, (lab, x, col) in enumerate((('YES', 60, BLUE), ('NO', 470, RED))):
            s = pop(t, wt('electric') + 0.12 * k, 0.25)
            if s <= 0: continue
            w, h = 380 * s, 110 * s; cx, cy = x + 190, 520
            d.rounded_rectangle([cx - w / 2 + 8, cy - h / 2 + 10, cx + w / 2 + 8, cy + h / 2 + 10], 18, fill=INK)
            d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 18, fill=PAPER, outline=INK, width=6)
            BOXES.append((cx - w / 2, cy - h / 2, cx + w / 2 + 8, cy + h / 2 + 10))
            text(img, (cx, cy), lab, font(FONT, 64), col, 'mm', s)
        return
    a = ss((t - T_GO) / 0.25)
    lab = '0 → 400 KM/H' if t < T_BRK else '400 → 0  BRAKING' if t < T_12 + 0.4 else 'NEVERA STOPS FIRST'
    sw = max(T_GO, T_BRK if t >= T_BRK else 0, T_12 + 0.4 if t >= T_12 + 0.4 else 0)
    text(img, (60, 270), lab, font(FONT, 64), BLUE if 'NEVERA' in lab else INK, sc=pop(t, sw, 0.22) * a if a < 1 else pop(t, sw, 0.22))
    timeline(img, t, a)


def ui(img, t):
    BOXES.clear()
    panel(img, t)
    for c in CARS.values(): lane_header(img, c, t)
    if T_GO <= t < T_Q:
        text(img, (60, 540), 'separate record runs', font(FONT_B, 28), (110, 110, 120), sc=pop(t, T_GO + 0.2, 0.25))
    if t >= T_PARK:                                                       # "already parked"
        c = CARS['blue']; s = pop(t, T_PARK, 0.3); cx, cy = x0_of(c, t) + 0.5 * L, c['y'] - 0.27 * L - 60
        d = ImageDraw.Draw(img); r = 46 * s
        if r > 2:
            d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], 14, fill=BLUE, outline=INK, width=4)
            text(img, (cx, cy + 2), 'P', font(FONT, int(70)), PAPER, 'mm', s, box=False)
    text(img, (918, 236), 'Yub', font(FONT_B, 26), (120, 120, 130), 'rt')


# ---------------------------------------------------------------- frame
BG = None


def render(t):
    global BG, GRID
    if BG is None: BG = build_bg(); GRID = grid(W + 150, H)
    img = BG.convert('RGBA')
    draw_p = 0.12 + 0.88 * ss(t / 1.5)
    heat = 1 - ss((t - 0.5) / 1.5)
    for c in CARS.values(): c['_t'] = t; draw_lane(img, c, t, draw_p, heat)
    ui(img, t)
    out = img.convert('RGB')
    sh = 0
    if T_GO <= t < T_GO + 0.5: sh = 6 * math.exp(-(t - T_GO) * 8) * math.sin(t * 95)
    for c in CARS.values():
        if c['stop'] <= t < c['stop'] + 0.3: sh += 5 * math.exp(-(t - c['stop']) * 12) * math.sin(t * 110)
    if sh:
        out = Image.fromarray(np.roll(np.asarray(out), int(sh), 0))
    return np.asarray(out)


F0 = None


def frame(t):
    global F0
    a = render(t)
    if t >= LOOP0:
        if F0 is None: F0 = render(0.0).astype(np.float32)
        k = ss((t - LOOP0) / (DUR - 1 / FPS - LOOP0))
        a = (a.astype(np.float32) * (1 - k) + F0 * k).astype(np.uint8)
    return a


# ---------------------------------------------------------------- audio
def read_wav(p):
    with wave.open(str(p)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        ch, sr = w.getnchannels(), w.getframerate()
    x = x.reshape(-1, ch).mean(1)
    return np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)


def lufs(x):
    """Integrated loudness (ITU-R BS.1770) via ffmpeg ebur128 on a mono float signal."""
    tmp = OUT / '_lufs.wav'; write_wav(tmp, x)
    r = subprocess.run(['ffmpeg', '-nostats', '-i', str(tmp), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    tmp.unlink()
    return float(r.rsplit('I:', 1)[1].split('LUFS')[0])


def write_wav(p, x):
    pcm = (np.stack([x, x], 1).clip(-1, 1) * 32767).astype(np.int16)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def add(buf, i, s):
    i = max(0, i); j = min(len(buf), i + len(s))
    if i < len(buf): buf[i:j] += s[:j - i]


def tick(): return sfx.fade(np.sign(np.sin(2 * np.pi * 1800 * sfx.T(0.02))) * 0.12)


def audio(path):
    n = int(DUR * SR)
    vo = np.zeros(n); add(vo, 0, read_wav(VO_WAV))
    mus = np.zeros(n); add(mus, 0, read_wav(MUSIC_WAV))
    L_vo, L_mu = lufs(vo), lufs(mus)
    mus *= 10 ** ((L_vo - 18 - L_mu) / 20)                                # music 18 dB under the voice
    fo = np.clip((DUR - np.arange(n) / SR) / 1.6, 0, 1); mus *= fo * fo   # fade the music out at the end
    mus *= np.clip(np.arange(n) / SR / 0.05, 0, 1)
    fx = np.zeros(n)
    ev = [(0.0, sfx.whoosh(0.4, 20) * .5), (T_GO - 0.05, sfx.vroom(1.2) * .9), (T_GO, sfx.whoosh(0.6, 8) * .6),
          (T_BRK, sfx.screech(0.6) * .35), (T_30, sfx.ding(1568, 0.5) * .5), (T_12, sfx.ding(1175, 0.6) * .5),
          (T_12 + 0.1, sfx.stamp() * .5), (T_42, sfx.pop() * .4), (T_PARK, sfx.pop() * .5),
          (T_Q, sfx.pop() * .4), (wt('electric'), sfx.pop() * .5), (wt('electric') + 0.12, sfx.pop() * .5), (LOOP0, sfx.whoosh(0.5, 16) * .4)]
    for k in range(10): ev.append((T_GO + k * 0.2, tick() * 0.6))
    for t0, s in ev: add(fx, int(t0 * SR), s)
    fx *= 10 ** ((L_vo - 12 - lufs(fx)) / 20)                             # effects sit 12 dB under the voice
    mix = vo + mus + fx
    g = 10 ** ((-13.4 - lufs(mix)) / 20); mix *= g                          # -14 LUFS after AAC (measured)
    pk = np.abs(mix).max()
    if pk > 0.89: mix = np.tanh(mix / 0.89) * 0.89                        # soft-limit peaks to about -1 dBFS
    write_wav(path, mix)
    print(f'audio: vo {L_vo:.1f} LUFS, music gain {L_vo - 18 - L_mu:+.1f} dB, mix gain {20 * math.log10(g):+.1f} dB')


def main():
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: Image.fromarray(frame(float(s))).save(out / f'f_{s}.png')
        return
    if mode == 'scan':
        bad = []
        for i in range(int(DUR * FPS)):
            t = i / FPS
            img = Image.new('RGBA', (W, H)); ui(img, t)
            for c in CARS.values(): speed(c, t), clock(c, t), pitch(c, t), x0_of(c, t)
            for b in BOXES:
                if b[0] < SAFE[0] or b[1] < SAFE[1] or b[2] > SAFE[2] or b[3] > SAFE[3]: bad.append((round(t, 2), b))
        print('anchors', {k: round(v, 2) for k, v in dict(go=T_GO, k400=T_400, brk=T_BRK, s30=T_30, s12=T_12, park=T_PARK,
                                                             q=T_Q, end_vo=END_VO).items()})
        print('safe-zone violations:', len(bad), bad[:5])
        return
    dst = Path(sys.argv[2]); dst.parent.mkdir(parents=True, exist_ok=True)
    t_end = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    t_start = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    wav = dst.with_suffix('.wav'); audio(wav)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-ss', str(t_start), '-i', str(wav), '-t', str(t_end - t_start), '-c:v', 'libx264', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                          '-shortest', str(dst)], stdin=subprocess.PIPE)
    for i in range(int(round(t_start * FPS)), int(round(t_end * FPS))):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); sys.exit(p.wait())


if __name__ == '__main__':
    main()
