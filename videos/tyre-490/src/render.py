"""tyre-490: wireframe + ASCII + heat + HUD explainer (1080x1920, 30 fps).

Scenes change scale every 2-3 s: tyre macro, wide car on a long straight,
cross-section, giant test-rig drum. All timing comes from beats.json; phase 2
puts aligned word times there (words[].t, est=false) and beat starts follow
their anchor words.

  python render.py still OUTDIR 0 2.5 4.5
  python render.py video OUT.mp4 [END [START]]      (PREVIEW=0 drops the tag)
"""
import json, math, os, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, 'beats.json')))
W, H = B['size']; FPS = B['fps']
DUR = 21.0  # literal for tools/video.py preview; must match beats.json
assert abs(DUR - B['dur']) < 1e-6
PREVIEW = os.environ.get('PREVIEW', '1') == '1'


def resolve_beats(b):
    """Brief layout now; aligned anchor-word times in phase 2."""
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
def lin(x): return x
def bump(t, t0, rise=.06, fall=.45):
    return prog(t, t0, rise) * (1 - prog(t, t0 + rise, fall))


# ---- palette / fonts ----------------------------------------------------
WHITE = np.array([.92, .95, 1.0], np.float32)
FAR = np.array([.50, .56, .66], np.float32)
ACC = np.array([1.0, .36, .09], np.float32)        # the single heat accent
HOT = np.array([1.0, .86, .62], np.float32)
RED = np.array([1.0, .13, .08], np.float32)        # flaw only
XRC = np.array([.80, .88, 1.0], np.float32)
BG = np.array([.018, .02, .028], np.float32)
FD = '/usr/share/fonts/truetype/jetbrains-mono/'
def F(style, size): return ImageFont.truetype(FD + f'JetBrainsMono-{style}.ttf', size)
F_HEAD, F_VAL, F_UNIT = F('ExtraBold', 84), F('Bold', 120), F('Bold', 56)
F_LAB, F_CHIP, F_TAG, F_BTN = F('Medium', 48), F('Bold', 48), F('Regular', 30), F('Bold', 72)
TXT_X = 64                                       # safe text: x < 918, 230 < y < 1190
SCR = .16                                        # scramble-decode duration (< 0.2 s)

# ---- timeline (all anchored to beat starts) -----------------------------
TC, t1, t2, t3, TR, t4, t5, t6 = (T(x) for x in ('car', 'rpm', 'g_force', 'belts', 'rig', 'xray', 'flaw', 'poll'))
STAMP = t2 + 1.2                                 # 5,300 g slam
FLAWHIT = t5 + 1.0                               # flaw pulse punch
EARLY = (.62, .92)                               # cold-open red flaw flash (the stakes)
LOOP = DUR - .5                                  # back to the cold-open tyre: last frame -> frame 1
TRANSITIONS = [TC, t1, t2, STAMP, t3, TR, t4, t5, t6, LOOP]


def scene(t):
    if t < TC or t >= LOOP: return 'tyre'
    if t < t1 or t >= t6: return 'car'
    if TR <= t < t4: return 'rig'
    return 'tyre'


def omega(t):                                    # apparent tyre spin, rad/s (readable, not 68 rev/s)
    if t < t1 or t >= t6: return 15.0
    if t < t4: return 3 + 13 * io(prog(t, t1, 1.5))   # visible spin-up
    if t < t5: return 16 - 13 * eo(prog(t, t4, .8))
    return 3.0                                    # slow inspection turn


_TT = np.linspace(0, DUR, int(DUR * 600) + 1)
_PHI = np.concatenate([[0], np.cumsum([omega(x) for x in _TT[1:]]) * (_TT[1] - _TT[0])])
def phi(t): return float(np.interp(t, _TT, _PHI))


def _heat1(t):
    h = .3 + .35 * io(prog(t, t1, t2 - t1)) + .35 * io(prog(t, t2, STAMP - t2))
    return min(1.2, h + .5 * bump(t, STAMP, .05, .6))


def heat(t):
    if t >= LOOP: return .3
    if t < TR: return _heat1(t)
    if t < t4: return _heat1(TR) + (.8 - _heat1(TR)) * eo(prog(t, TR, .6))
    return .8 + (.12 - .8) * eo(prog(t, t4, .6))


def stretch(t):                                  # EXAGGERATED tread growth
    return .085 * io(prog(t, t1 + .4, .9)) * (1 + .25 * bump(t, STAMP, .05, .5)) * (1 - io(prog(t, t3, .5)))


def streak_amp(t):
    if t < TC: return .6 + 1.1 * (1 - eo(prog(t, 0, 1.1)))
    if t >= LOOP: return 1.7
    return {'car': 1.0 if t < t6 else 1.3, 'rig': 1.1}.get(scene(t), (.65 if t < t3 else .95) if t < t4 else .85)


def streak_speed(t): return 1.7 if scene(t) == 'car' else omega(t) / 15 + .4


def thermal_k(t):
    if t >= LOOP or t < t1: return .7
    if t < t4: return .7 + .3 * io(prog(t, t1, 1.0))
    return 1 - eo(prog(t, t4, .4))


# ---- tyre-scene camera ---------------------------------------------------
#      yaw   pitch  roll  dist  cx-off cy-off
S0 = (1.5, -.3, .22, 2.7, 0, 140)
CAMKEYS = [(0, .75, eo, (.95, -.2, 0, 4.0, 0, 0)),
           (t1, .01, lin, (.45, -.1, .06, 1.9, 40, 140)),           # macro after the wide shot
           (t1 + .02, 2.4, io, (.8, -.24, -.02, 3.3, 0, 40)),
           (t2, .6, eo, (1.15, -.2, .02, 2.9, -20, 70)),
           (t2 + .6, 1.9, io, (1.3, -.3, -.03, 3.5, 0, 0)),
           (t3, .8, eo, (.9, -.25, .03, 1.9, -20, 430)),            # dolly into the tread
           (t3 + .8, 1.7, io, (1.35, -.38, -.06, 1.7, -70, 460)),
           (t4, .01, lin, (.28, -.08, 0, 3.6, -10, -10)),           # face-on for the scan
           (t4 + .02, 1.98, io, (.52, -.16, .04, 3.2, 10, 0)),
           (t5, .6, eo, (.55, -.15, -.02, 3.1, -10, 120)),          # push toward the flaw
           (t5 + .6, 1.4, io, (1.15, -.3, .05, 2.5, -30, 160))]


KICKS = ([TC + .6, TC + 1.2, TC + 1.8] + [t3 + 1.0, t3 + 1.6, t3 + 2.2] + [TR + 1.0, TR + 1.8, TR + 2.5]
         + [t5 + .4, t5 + 1.5] + [t6 + .6, t6 + 1.2, t6 + 1.75, t6 + 2.3])


def kick(t):
    """Beat-synced camera kicks in the calmer shots (punch-in + jolt)."""
    return max([bump(t, k, .03, .3) for k in KICKS] + [0.0])


def shake(t, amp):
    return (amp * (math.sin(t * 61) * .6 + math.sin(t * 37 + 1) * .4),
            amp * (math.sin(t * 53 + 2) * .6 + math.sin(t * 29) * .4))


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
    dist -= .35 * bump(t, STAMP, .04, .5) + .25 * bump(t, FLAWHIT, .04, .45) + .3 * kick(t)
    amp = (22 * (1 - eo(prog(t, 0, 1.0))) + 3 + 26 * bump(t, STAMP, .02, .45) + 10 * bump(t, t1, .02, .3)
           + 14 * bump(t, FLAWHIT, .02, .35) + 6 * bump(t, t3, .02, .3) + 4 * bump(t, t4, .02, .3) + 22 * kick(t))
    sx, sy = shake(t, amp)
    return (yaw, pitch, roll, dist, 548 + cxo + 18 * math.sin(.5 * t) + sx,
            1215 + cyo + 12 * math.sin(.65 * t + 1) + sy, 0.0, 0.0, 0.0)


def cam(t):
    return cam_base(t - DUR) if t >= LOOP else cam_base(t)


def cam_rig(t):
    k = eo(prog(t, TR, .9))
    m = io(prog(t, TR, t4 - TR))
    yaw = .95 - .45 * m + .05 * math.sin(.8 * t)
    pitch = -.2 + .14 * k + .04 * math.sin(.7 * t)
    dist = 3.6 + 9.4 * k - 1.2 * io(prog(t, t4 - 1.1, 1.1))
    ty = -1.0 * (1 - k) - 2.4 * k
    sx, sy = shake(t, 3 + 10 * bump(t, TR, .02, .4) + 24 * kick(t))
    dist -= 1.4 * kick(t)
    return (yaw, pitch, .03 * math.sin(.9 * t), dist, 540 + 14 * math.sin(.6 * t) + sx,
            1260 + 10 * math.sin(.7 * t) + sy, 0.0, ty, 0.0)


# ---- projection --------------------------------------------------------------
def project(P, yaw, pitch, roll, dist, cx, cy, tx=0.0, ty=0.0, tz=0.0, f=1400.0):
    x, y, z = P[:, 0] - tx, P[:, 1] - ty, P[:, 2] - tz
    cyw, syw = math.cos(yaw), math.sin(yaw)
    x, z = x * cyw + z * syw, -x * syw + z * cyw
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp - z * sp, y * sp + z * cp
    cr, sr = math.cos(roll), math.sin(roll)
    x, y = x * cr - y * sr, x * sr + y * cr
    z = z + dist
    zc = np.maximum(z, .05)
    return np.c_[cx + f * x / zc, cy - f * y / zc], z


# ---- geometry: generic tyre + 5-spoke wheel (no brand) -----------------------
PROFILE = [(.70, -.36), (.80, -.42), (.93, -.43), (.99, -.36), (1, -.2), (1, 0), (1, .2), (.99, .36),
           (.93, .43), (.80, .42), (.70, .36)]


def ring(r, z, n=120, c=(0, 0)):
    a = np.linspace(0, 2 * np.pi, n + 1)
    return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a), np.full(n + 1, z)]


def build():
    L = []
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


def spun(P, a, st, t, flat=True):
    c, s = math.cos(a), math.sin(a)
    Q = P.copy()
    r = np.hypot(P[:, 0], P[:, 1])
    th = np.arctan2(P[:, 1], P[:, 0])
    m = r >= .985                                  # tread grows + ripples (exaggerated)
    grow = 1 + st * (1 + .35 * np.sin(8 * th + 40 * t)) * m
    Q[:, 0], Q[:, 1] = P[:, 0] * grow, P[:, 1] * grow
    x, y = Q[:, 0] * c - Q[:, 1] * s, Q[:, 0] * s + Q[:, 1] * c
    z = Q[:, 2]
    if flat:
        near_patch = np.exp(-((y + 1) / .16) ** 2) * (np.abs(x) < .6)
        z = z * (1 + .07 * near_patch * (np.abs(z) > .3))   # sidewall bulge
        y = np.maximum(y, -.975)                          # flat contact patch
    return np.c_[x, y, z]


def draw_runs(draws, xy, z, zc, fill, width, near_key, tol=.12, ftol=1.6):
    seg = (z[:-1] + z[1:]) / 2
    cls = np.where(seg > zc + tol, 1, np.where(seg < zc - ftol, 1, 0))
    cls[(z[:-1] < .3) | (z[1:] < .3)] = 2
    i, n = 0, len(cls)
    while i < n:
        j = i
        while j + 1 < n and cls[j + 1] == cls[i]:
            j += 1
        if cls[i] != 2:
            pts = xy[i:j + 2].ravel().tolist()
            if cls[i] == 0:
                draws[near_key].line(pts, fill=fill, width=width)
            else:
                draws['far'].line(pts, fill=fill, width=2)
        i = j + 1


def blur_acc(t, camf, draw_fn, keys, K=6):
    """Motion blur: accumulate K sub-frame draws into L layers."""
    shutter = .6 / FPS
    acc = {k: Image.new('L', (W, H)) for k in keys}
    v = int(255 * 1.7 / K)
    for k in range(K):
        ts = t - shutter * (k / (K - 1) - .5)
        lay = {kk: Image.new('L', (W, H)) for kk in keys}
        draw_fn(ts, camf(ts), {kk: ImageDraw.Draw(im) for kk, im in lay.items()}, v)
        for kk in keys:
            acc[kk] = ImageChops.add(acc[kk], lay[kk])
    return acc


def draw_tyre(ts, cv, dr, v, ground=True):
    st = stretch(ts)
    a = -phi(ts)
    for P, tag in GEOM:
        xy, z = project(spun(P, a, st, ts), *cv)
        draw_runs(dr, xy, z, cv[3], v, 3 if tag != 'rim' else 2, 'tread' if tag == 'tread' else 'near')
    if not ground: return
    s = phi(ts) % .7                               # rolling road: ground moves r*phi
    for xg in np.arange(-6.3, 6.3, .7) - s + .35:
        P = np.array([[xg, -1.0, zz] for zz in np.linspace(-2.2, 2.2, 9)])
        xy, z = project(P, *cv)
        draw_runs(dr, xy, z, cv[3] + 9, int(v * .55 * clamp(1 - abs(xg) / 6.3)), 2, 'ground')
    for zg in np.linspace(-2.2, 2.2, 7):
        P = np.array([[xx, -1.0, zg] for xx in np.linspace(-6.3, 6.3, 25)])
        xy, z = project(P, *cv)
        draw_runs(dr, xy, z, cv[3] + 9, int(v * .35), 2, 'ground')


def tyre_points(t, cv):
    st = stretch(t)
    contact, _ = project(np.array([[0, -1.0 - st, 0.0], [-.6, -.8, 0]]), *cv)
    top, _ = project(np.array([[0, 1.0 + st, .1], [.72, .72 + st, .3]]), *cv)
    return contact, top


# ---- stone (g beat): 1 kg stone in the tread, its weight at ~5,300 g ----------
def _stone():
    g = (1 + 5 ** .5) / 2
    V = np.array([(-1, g, 0), (1, g, 0), (-1, -g, 0), (1, -g, 0), (0, -1, g), (0, 1, g), (0, -1, -g), (0, 1, -g),
                  (g, 0, -1), (g, 0, 1), (-g, 0, -1), (-g, 0, 1)], float)
    V0 = V.copy()
    V *= np.random.default_rng(5).uniform(.8, 1.15, (12, 1)) * .085 / np.linalg.norm(V0[0])
    E = [(i, j) for i in range(12) for j in range(i + 1, 12) if np.linalg.norm(V0[i] - V0[j]) < 2.1]
    return V, E


STONE_V, STONE_E = _stone()


def stone_k(t): return prog(t, t2 + .2, .25) * (1 - prog(t, t3 - .15, .15)) if t2 <= t < t3 else 0.0


def g_val(t): return 5300 * eo(prog(t, t2 + .08, STAMP - t2 - .1))


def draw_stone(t, cv, dr, k):
    base = np.array([0, 1.03 + stretch(t) + .07, -.05])
    xy, z = project(STONE_V + base, *cv)
    for i, j in STONE_E:
        dr['near'].line([tuple(xy[i]), tuple(xy[j])], fill=int(255 * k), width=3)
    ln = .15 + .35 * (g_val(t) / 5300)             # outward pull grows with the g counter
    a, b = project(np.array([base + [0, .1, 0], base + [0, .1 + ln, 0]]), *cv)[0]
    dr['acc'].line([tuple(a), tuple(b)], fill=int(230 * k), width=4)
    hl, hr = project(np.array([base + [-.05, .05 + ln, 0], base + [.05, .05 + ln, 0]]), *cv)[0]
    dr['acc'].line([tuple(hl), tuple(b), tuple(hr)], fill=int(230 * k), width=4)
    return tuple(xy.mean(0)), tuple(b)


# ---- car (generic wireframe hypercar, no brand shapes) ------------------------
CAR_V = 45.0                                     # visual travel speed (stylised)


def _car():
    L = []
    xs = np.linspace(-2.25, 2.25, 25)
    ang = np.linspace(0, np.pi, 11)
    PX = [-2.25, -1.9, -1.2, -.5, .1, .75, 1.4, 2.0, 2.25]     # generic mid-engine wedge profile
    PY = [.78, .86, .95, 1.12, 1.12, .82, .62, .48, .38]
    def h(x): return float(np.interp(x, PX, PY))
    def w(x): return 1.0 - .14 * clamp((x - 1.3) / .95) ** 1.5 - .06 * clamp((-x - 1.7) / .55)
    secs = []
    for x in xs:
        hh, ww = h(x), w(x)
        secs.append([(x, .14 + (hh - .14) * abs(math.sin(a)) ** .8,
                      ww * math.copysign(abs(math.cos(a)) ** .6, math.cos(a)) * (1 - .35 * math.sin(a) ** 4))
                     for a in ang])
    for i, s in enumerate(secs):
        if i % 2 == 0:
            L.append((np.array(s + [s[0]]), 'body'))
    for k in range(len(ang)):
        L.append((np.array([s[k] for s in secs]), 'body'))
    for wx in (-1.35, 1.35):
        for sz in (-1, 1):
            arch = [(wx + .45 * math.cos(a), .34 + .45 * math.sin(a), sz * (w(wx) + .01)) for a in np.linspace(0, np.pi, 14)]
            L.append((np.array(arch), 'body'))
    for sz in (-1, 1):
        L.append((np.array([(-2.25, .95, sz * .9), (-2.0, .95, sz * .9), (-1.9, .7, sz * .6)]), 'body'))
    L.append((np.array([(-2.25, .95, -.9), (-2.25, .95, .9)]), 'body'))
    L.append((np.array([(2.12, .42, -.72), (2.2, .4, 0), (2.12, .42, .72)]), 'light'))
    L.append((np.array([(-2.27, .72, -.85), (-2.27, .72, .85)]), 'tail'))
    return L, w, secs


CAR_GEOM, CAR_W, CAR_SECS = _car()
WHEEL_POS = [(wx, sz * (CAR_W(wx) - .12)) for wx in (-1.35, 1.35) for sz in (-1, 1)]
CAR_WHEEL = [ring(.34, 0, 40), ring(.24, 0, 30)] + [
    np.array([[.06 * math.cos(a), .06 * math.sin(a), 0], [.23 * math.cos(a), .23 * math.sin(a), 0]])
    for a in np.linspace(0, 2 * np.pi, 5, endpoint=False)]


def travel(t): return CAR_V * t


def car_offset(t):                               # poll: car blasts past, then the camera locks on
    if t < t6: return 0.0
    return -14 + 17 * oc(prog(t, t6, 1.2)) - 3 * io(prog(t, t6 + 1.2, .9)) + 1.6 * math.sin(2.2 * (t - t6)) * prog(t, t6 + 1.2, .5)


def cam_car(t):
    if t < t6:
        k = eo(prog(t, TC, .7))
        tgt = np.array([-1.35, .34, -.95]) * (1 - k) + np.array([0, .55, 0]) * k
        yaw = -.55 * (1 - k) - .12 + .3 * io(prog(t, TC, t1 - TC))   # side profile, like the jaguar
        pitch, dist, roll = -.1 - .32 * k, 1.4 + 7.0 * k, .12 * (1 - k)
        amp = 6 + 22 * (1 - k)
    else:
        tgt = np.array([-car_offset(t), .6, 0])
        yaw, pitch, dist, roll = -.1 + .2 * io(prog(t, t6, 2.4)), -.42, 8.6, 0.0
        amp = 6 + 14 * bump(t, t6 + .45, .1, .6)
    sx, sy = shake(t, amp)
    dist += .5 * math.sin(1.7 * t) - 1.1 * kick(t)   # breathing chase dolly + kicks
    sx, sy = sx + 30 * kick(t) * math.sin(t * 71), sy + 22 * kick(t) * math.cos(t * 63)
    yaw += .12 * math.sin(1.1 * t)
    return (yaw, pitch + .05 * math.sin(1.4 * t), roll + .05 * math.sin(1.2 * t), dist,
            540 + 50 * math.sin(1.3 * t) + sx, 1180 + 28 * math.sin(1.9 * t) + sy, *tgt)


def draw_car(ts, cv, dr, v):
    d = travel(ts)
    zc = project(np.array([[0.0, .6, 0.0]]), *cv)[1][0]
    for P, tag in CAR_GEOM:
        xy, z = project(P, *cv)
        draw_runs(dr, xy, z, zc, v, 3 if tag != 'body' else 2, 'acc' if tag == 'tail' else 'near', tol=2.2, ftol=6)
    a = -d / .34
    c, s = math.cos(a), math.sin(a)
    for wx, wz in WHEEL_POS:
        for P in CAR_WHEEL:
            Q = np.c_[wx + P[:, 0] * c - P[:, 1] * s, .34 + P[:, 0] * s + P[:, 1] * c, np.full(len(P), wz)]
            xy, z = project(Q, *cv)
            draw_runs(dr, xy, z, zc, v, 2, 'near', tol=2.2, ftol=6)
    # the long straight: edges, lane dashes, ruler ticks; scrolls past the car
    for zz in (-3.5, 3.5):
        P = np.c_[np.linspace(-40, 260, 60), np.zeros(60), np.full(60, zz)]
        xy, z = project(P, *cv)
        draw_runs(dr, xy, z, cv[3] + 400, v, 2, 'ground', ftol=1e9)
    for x0 in np.arange(-42, 260, 6) - d % 6:
        for zz in (-1.75, 1.75):
            xy, z = project(np.array([[x0, 0, zz], [x0 + 3, 0, zz]]), *cv)
            draw_runs(dr, xy, z, cv[3] + 400, int(v * clamp(1 - x0 / 260)), 3, 'ground', ftol=1e9)
    for x0 in np.arange(-40, 120, 1.0) - d % 1:
        big = round(x0 + d) % 5 == 0
        xy, z = project(np.array([[x0, 0, 3.6], [x0, 0, 3.6 + (.7 if big else .3)]]), *cv)
        draw_runs(dr, xy, z, cv[3] + 400, int(v * .8 * clamp(1 - x0 / 120)), 2, 'ground', ftol=1e9)


MARK_EVERY = 10.0


def car_markers(t, cv):
    """Ruler posts flying by: (screen xy, label, depth) for the HUD."""
    d = travel(t)
    out = []
    for n in range(int(d // MARK_EVERY) - 1, int(d // MARK_EVERY) + 6):
        x = n * MARK_EVERY - d
        xy, z = project(np.array([[x, 0, 4.4], [x, 1.6, 4.4]]), *cv)
        if z.min() > .5:
            out.append((xy, f"{n * MARK_EVERY:.0f} M", z[0]))
    return out


# ---- rig: generic giant drum dyno (original design) -----------------------------
DRUM_R, DRUM_C = 3.0, (0.0, -4.0)


def _box(x0, x1, y0, y1, z0, z1):
    c = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    return [np.array([c[i], c[j]]) for i in range(8) for j in range(i + 1, 8) if bin(i ^ j).count('1') == 1]


def _rig_static():
    L = _box(-4.6, 4.6, -7.6, -7.2, -2.2, 2.2)                    # base
    for zz in (-1.35, 1.35):                                      # drum pedestals
        L += _box(-.7, .7, -7.2, -4.0, zz - .25, zz + .25)
    for zz in (-1.0, 1.0):                                        # tyre carriage: columns + crossbeam
        L += _box(-3.2, -2.8, -7.2, 3.4, zz - .2, zz + .2)
        L += _box(2.8, 3.2, -7.2, 3.4, zz - .2, zz + .2)
    L += _box(-3.2, 3.2, 3.0, 3.6, -1.2, 1.2)
    for zz in (-.75, .75):                                        # load cylinders down to the hub
        for xx in (-.12, .12):
            L.append(np.array([[xx, 3.0, zz], [xx, .2, zz]]))
        L.append(np.array([[-.25, .2, zz], [.25, .2, zz], [0, 0, zz * .6]]))
    return L


RIG_STATIC = _rig_static()


def draw_rig(ts, cv, dr, v):
    draw_tyre(ts, cv, dr, v, ground=False)
    cx0, cy0 = DRUM_C
    for r, zz in [(DRUM_R, -.8), (DRUM_R, .8), (DRUM_R * .92, -.82), (DRUM_R * .92, .82), (.5, -.86), (.5, .86)]:
        xy, z = project(ring(r, zz, 160, (cx0, cy0)), *cv)
        draw_runs(dr, xy, z, cv[3], v, 3, 'near', tol=1.2, ftol=6)
    a = phi(ts) / DRUM_R                             # surface speed matches the tyre
    for th in np.linspace(0, 2 * np.pi, 72, endpoint=False) + a:
        P = np.array([[cx0 + DRUM_R * math.cos(th), cy0 + DRUM_R * math.sin(th), zz] for zz in (-.8, .8)])
        xy, z = project(P, *cv)
        draw_runs(dr, xy, z, cv[3], int(v * .8), 2, 'tread', tol=1.2, ftol=6)
    for th in np.linspace(0, 2 * np.pi, 10, endpoint=False) + a:
        for zz in (-.84, .84):
            P = np.array([[cx0 + .5 * math.cos(th), cy0 + .5 * math.sin(th), zz],
                          [cx0 + DRUM_R * .92 * math.cos(th), cy0 + DRUM_R * .92 * math.sin(th), zz]])
            xy, z = project(P, *cv)
            draw_runs(dr, xy, z, cv[3], v, 2, 'near', tol=1.2, ftol=6)
    for P in RIG_STATIC:
        xy, z = project(P, *cv)
        draw_runs(dr, xy, z, cv[3], int(v * .7), 2, 'near', tol=1.2, ftol=6)


# ---- sparks (deterministic particles) ------------------------------------
_R = np.random.default_rng(7)
_N = 11000
SP = dict(tb=_R.uniform(-.6, DUR, _N), life=_R.uniform(.18, .55, _N), v=_R.uniform(700, 2100, _N),
          ang=_R.normal(0, .35, _N), keep=_R.uniform(0, 1, _N))


def spark_rate(t):
    on = (t < TC - .5) or (t1 + .3 < t < t2 - .5) or (TR + .6 < t < t4 - .5) or (t >= LOOP)
    if not on: return 0.0
    r = .55 * (1 - prog(t, .6, .6)) + .55 * (t >= LOOP) + .12 + .25 * heat(t)
    return r * (1.1 if scene(t) == 'rig' else 1)


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
_NS = 520
STREAK = dict(row=_G.integers(0, ROWS, _NS), v=_G.uniform(55, 150, _NS), L=_G.uniform(6, 30, _NS),
              ph=_G.uniform(0, 400, _NS), amp=_G.uniform(.5, 1.2, _NS), hot=_G.uniform(0, 1, _NS))
ROWW = np.ones(ROWS, np.float32)
ROWW[230 // CH:1190 // CH] = .3                  # keep text zone calm


def glyphs(lum, t):
    jit = (np.random.default_rng(int(t * 30)).integers(0, 3, lum.shape) - 1) * (lum > .08)
    idx = np.clip((lum * (len(RAMP) - 1)).astype(int) + jit, 0, len(RAMP) - 1)
    g = ATLAS[idx]
    return g.transpose(0, 2, 1, 3).reshape(ROWS * CH, COLS * CW)


def streaks(t):
    sp = streak_speed(t)
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


def ascii_of(img, t, gain=2.4):
    cells = img.reshape(ROWS, CH, COLS, CW, 3).mean(axis=(1, 3))
    lum = cells.max(-1)
    col = cells / (lum[..., None] + 1e-4)
    g = glyphs(np.clip(lum * gain, 0, 1), t)
    return g[..., None] * np.clip(col, 0, 1).repeat(CH, 0).repeat(CW, 1) * 1.3


def transition_mask(t):
    m = np.zeros(ROWS, np.float32)
    for tt in TRANSITIONS:
        if abs(t - tt) < .2:
            k = (t - tt + .2) / .4                  # band sweeps top -> bottom
            r = np.arange(ROWS) / ROWS
            m = np.maximum(m, np.clip(1 - np.abs(r - (k * 1.4 - .2)) / .22, 0, 1))
    return m


# ---- thermal skin -----------------------------------------------------------
def _quads():
    A = np.linspace(0, 2 * np.pi, 73)
    Q, PF, LA = [], [], []
    pf = [.45, .6, .8, .95, 1, 1, .95, .8, .6, .45]
    for j in range(len(PROFILE) - 1):
        (r0, z0), (r1, z1) = PROFILE[j], PROFILE[j + 1]
        for i in range(72):
            a0, a1 = A[i], A[i + 1]
            Q.append([[r0 * math.cos(a0), r0 * math.sin(a0), z0], [r1 * math.cos(a0), r1 * math.sin(a0), z1],
                      [r1 * math.cos(a1), r1 * math.sin(a1), z1], [r0 * math.cos(a1), r0 * math.sin(a1), z0]])
            PF.append(pf[j]); LA.append(i)
    return np.array(Q), np.array(PF), np.array(LA)


QUADS, QPF, QLA = _quads()
QTEX = .5 + .5 * np.sin(QLA * 1.7) * np.cos(QLA * .45)


def _lut(stops):
    x = np.linspace(0, 1, 256)
    return np.stack([np.interp(x, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], -1).astype(np.float32)


THERM_LUT = _lut([(0, (0, 0, 0)), (.2, (.16, .01, .04)), (.45, (.55, .06, .04)), (.7, tuple(ACC)),
                  (.88, (1, .62, .25)), (1, tuple(HOT))])


def thermal_layer(t, cv):
    P = spun(QUADS.reshape(-1, 3), -phi(t), stretch(t), t)
    xy, z = project(P, *cv)
    xy, z = xy.reshape(-1, 4, 2), z.reshape(-1, 4)
    c = P.reshape(-1, 4, 3).mean(1)
    dth = np.angle(np.exp(1j * (np.arctan2(c[:, 1], c[:, 0]) + np.pi / 2)))
    T = np.clip(heat(t) * QPF * (.42 + .5 * np.exp(-(dth / .7) ** 2) + .12 * QTEX) * .9, 0, 1)
    im = Image.new('L', (W, H)); d = ImageDraw.Draw(im)
    for i in np.argsort(-z.mean(1)):
        if z[i].min() < .3: continue
        d.polygon([tuple(p) for p in xy[i]], fill=int(255 * T[i]))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(2)))


# ---- LiDAR --------------------------------------------------------------------
_LG = np.random.default_rng(21)
LG_X, LG_Z = _LG.uniform(-1, 1, 10000), _LG.uniform(-1, 1, 10000)


def splat(xy, v, out):
    x, y = xy[:, 0].astype(int), xy[:, 1].astype(int)
    m = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1) & (v > .01)
    x, y, v = x[m], y[m], v[m]
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        np.add.at(out, (y + dy, x + dx), v)
    return out


def lidar_ground(t, cv, y0=-1.0, sx=7.0, sz=3.2, scroll=None, ring_s=1.0):
    scroll = phi(t) if scroll is None else scroll
    x = (LG_X * sx - scroll + sx) % (2 * sx) - sx
    z = LG_Z * sz
    xy, zc = project(np.c_[x, np.full_like(x, y0), z], *cv)
    d = np.hypot(x, z)
    ring = sum(np.exp(-((d - ((t * .55 + o) % 1) * sx) / (.1 * ring_s)) ** 2) for o in (0, .5))
    v = (.3 + 1.4 * ring) * np.clip(1 - np.abs(x) / sx, 0, 1) * np.clip(1 - np.abs(z) / sz, 0, 1)
    v = v * (zc > .4) * np.clip(2.5 * ring_s / np.maximum(zc, .4), 0, 1.3)
    return np.minimum(splat(xy, v, np.zeros((H, W), np.float32)), 1.2)


_LT = np.random.default_rng(22)
_ang, _pj = _LT.uniform(0, 2 * np.pi, 16000), _LT.uniform(0, len(PROFILE) - 1.001, 16000)
_j = _pj.astype(int); _f = _pj - _j
_pr = np.array(PROFILE)
_r = _pr[_j, 0] * (1 - _f) + _pr[_j + 1, 0] * _f
_zz = _pr[_j, 1] * (1 - _f) + _pr[_j + 1, 1] * _f
LT_P = np.c_[_r * np.cos(_ang), _r * np.sin(_ang), _zz]
TH_F = .95 + phi(t5 + .6)                         # flaw lands upper-right of the hub during its beat
TH_E = 1.0 + phi(sum(EARLY) / 2)                  # same kind of flaw, cold-open flash
def flaw_local(th): return np.array([.86 * math.cos(th), .86 * math.sin(th), -.43])


def lidar_tyre_k(t): return prog(t, t5 - .1, .3) * (1 - prog(t, t6 - .2, .2)) if t < t6 else 0.0


def lidar_tyre(t, cv):
    P = spun(LT_P, -phi(t), 0, t)
    xy, z = project(P, *cv)
    sx = -1.2 + 2.4 * (((t - t5) * 1.6) % 1)         # sweeping scan plane
    v = (.45 + 1.6 * np.exp(-((P[:, 0] - sx) / .06) ** 2)) * np.clip(3.2 / np.maximum(z, .5), 0, 1.2)
    v = v * np.random.default_rng(int(t * 30)).uniform(.45, 1.25, len(v))   # LiDAR return shimmer
    near_f = np.linalg.norm(LT_P - flaw_local(TH_F), axis=1) < .07
    pc = splat(xy[~near_f], v[~near_f], np.zeros((H, W), np.float32))
    pr = splat(xy[near_f], np.full(near_f.sum(), 1.0), np.zeros((H, W), np.float32))
    return np.minimum(pc, 1.2), np.minimum(pr, 1.5)


def flaw_screen(t, th):
    a = -phi(t)
    xy, _ = project(spun(flaw_local(th)[None], a, 0, t), *cam(t))
    return tuple(xy[0]), math.degrees(th + a) % 360


# ---- CFD airflow (potential flow + circulation + wake) -------------------------
FY = np.arange(70, H - 40, 22, dtype=np.float32)
FPH = np.random.default_rng(31).uniform(0, 40, len(FY))
TXTMASK = np.ones((H, W), np.float32); TXTMASK[230:1190, :918] = .35


def flow_amp(t):
    sc = scene(t)
    if sc == 'car': return 0.0
    if sc == 'rig': return .8
    if t < t3 or t >= LOOP: return 1.0
    return .85 if t < TR else .45


def flow_layers(t, ob, amp, spin=None):
    ox, oy, a = ob
    n, steps, ds = len(FY), 80, 16.0
    x = np.full(n, W + 30.0); y = FY.copy()
    X, Y, S = np.zeros((steps, n)), np.zeros((steps, n)), np.zeros((steps, n))
    alive = np.ones(n, bool)
    G = .35 * a * (omega(t) / 15 if spin is None else spin)
    for i in range(steps):
        zx, zy = x - ox, y - oy
        r2 = np.maximum(zx * zx + zy * zy, 1)
        a2r4 = a * a / (r2 * r2)
        vx = -(1 - a2r4 * (zx * zx - zy * zy)) - G * zy / r2
        vy = 2 * a2r4 * zx * zy + G * zx / r2
        wk = (zx < 0) * np.exp(-(zy / (1.1 * a)) ** 2) * np.clip(-zx / a, 0, 1)
        vy += .45 * wk * np.sin(zx / (.8 * a) * np.pi + 7 * t)
        sp = np.hypot(vx, vy) + 1e-6
        alive &= r2 > (a * 1.02) ** 2
        X[i], Y[i], S[i] = x, y, sp * alive
        x = x + vx / sp * ds; y = y + vy / sp * ds
    fl = Image.new('L', (W, H)); fh = Image.new('L', (W, H))
    dl, dh = ImageDraw.Draw(fl), ImageDraw.Draw(fh)
    rate = 34 * (.7 + .3 * streak_speed(t))
    for j in range(n):
        d = dh if oy + .45 * a < FY[j] < oy + 1.5 * a else dl
        vis = ((np.arange(steps) + FPH[j] - rate * t) % 9) < 5.5     # moving dashes
        for i in range(steps - 1):
            if vis[i] and S[i, j] > 0 and S[i + 1, j] > 0:
                b = min(1.0, .45 + .5 * S[i, j]) * amp
                d.line([(X[i, j], Y[i, j]), (X[i + 1, j], Y[i + 1, j])], fill=int(255 * b), width=2)
    return np.asarray(fl, np.float32) / 255 * TXTMASK, np.asarray(fh, np.float32) / 255 * TXTMASK


# ---- cross-section (belts beat) --------------------------------------------
def _mirror(half): return half + [(-u, v) for u, v in reversed(half)]


def _top():
    pts = [(-.66, 1.0)]
    for c in (-.45, -.15, .15, .45):
        pts += [(c - .04, 1.0), (c - .03, .93), (c + .03, .93), (c + .04, 1.0)]
    return pts + [(.66, 1.0)]


_OUT_L = [(-.70, 0), (-.80, .15), (-.92, .40), (-.98, .62), (-.95, .82), (-.84, .95)]
SEC_OUT = _OUT_L + _top() + [(-u, v) for u, v in reversed(_OUT_L)]
SEC_LIN = _mirror([(-.58, .06), (-.66, .18), (-.78, .40), (-.84, .56), (-.78, .66), (-.62, .69)])
SEC_PLY = _mirror([(-.62, .02), (-.73, .17), (-.85, .40), (-.91, .59), (-.87, .72), (-.72, .755)])
BELTS = [(.80, .78), (.85, .74), (.905, .82)]


def sec_k(t): return prog(t, t3 + .02, .3) * (1 - prog(t, TR - .12, .12)) if t3 <= t < TR else 0.0


def sec_view(t):
    k = eo(prog(t, t3, .7))
    dist = 3.25 + 6 * (1 - k) - 1.7 * io(prog(t, TR - .3, .3)) - .25 * io(prog(t, t3 + .7, 1.6))
    m = io(prog(t, t3, TR - t3))
    sx, sy = shake(t, 2 + 6 * bump(t, t3 + .7, .05, .3) + 22 * kick(t))
    dist -= .5 * kick(t)
    return (.0 + 1.1 * m + .09 * math.sin(1.9 * t), .36 - .2 * m + .04 * math.sin(1.3 * t), .04 * math.sin(1.1 * t),
            dist, 480 + 24 * math.sin(.9 * t) + sx, 1110 + 14 * math.sin(1.1 * t) + sy)


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
    for su in (-1, 1):
        rp = [(su * .64 + .045 * math.cos(a), .06 + .045 * math.sin(a)) for a in np.linspace(0, 6.3, 20)]
        d['sec'].line(P(rp, zf), fill=int(235 * k), width=2)
    d['fill'].polygon(P(SEC_OUT, zf), fill=255)
    d['fill'].polygon(P(SEC_LIN, zf), fill=0)
    for i, (bv, hw) in enumerate(BELTS):
        g = io(prog(t, t3 + .5 + .3 * i, .35))
        us = np.linspace(-hw, hw, 40)
        pts = P([(u, bv - .05 * u * u) for u in us], zf)
        d['sec'].line(pts, fill=int(220 * k * (1 - g)), width=3)
        d['belt'].line(pts, fill=int(255 * k * g), width=7)
        d['belt'].line(P([(u, bv - .05 * u * u) for u in us], zb), fill=int(150 * k * g), width=3)
    ka = prog(t, t3 + 1.6, .25) * k
    if ka > 0:
        for u in (-.55, -.275, 0, .275, .55):
            L = .12 + .05 * math.sin(9 * t + u * 4)
            a, b = P([(u, 1.05), (u, 1.05 + L)], zf)
            d['sec'].line([a, b], fill=int(230 * ka), width=3)
            hx, hy = P([(u - .035, 1.0 + L), (u + .035, 1.0 + L)], zf)
            d['sec'].line([hx, b, hy], fill=int(230 * ka), width=3)
    return lay, P([(.45, .85 - .05 * .45 * .45)], zf)[0]


def section_obstacle(t):
    v = sec_view(t)
    return v[4], v[5] - 130, 1400 * .55 / v[3]


# ---- x-ray scan -------------------------------------------------------------
XCOL = np.arange(W, dtype=np.float32)
VFADE = np.clip(np.minimum((np.arange(H) - 380) / 200, (1820 - np.arange(H)) / 200), 0, 1).astype(np.float32)


def xray_state(t):
    if t < t4 + .15 or t > t5 - .05: return None
    if t < t4 + 1.0:
        s = io(prog(t, t4 + .15, .8)); x = -40 + 1160 * s; pn = 1
    else:
        s = io(prog(t, t4 + 1.0, .9)); x = 1120 - 1160 * s; pn = 2
    return np.clip((x - XCOL) / 40, 0, 1), x, pn, 100 * s


def xray_of(img, t):
    cells = img.reshape(ROWS, CH, COLS, CW, 3).mean(axis=(1, 3)).max(-1)
    return glyphs(np.clip(cells * 3.2, 0, 1), t + .5)[..., None] * XRC * 1.35 + .02


# ---- HUD ------------------------------------------------------------------
GLYPHS = "!#$%&*+/<=>?@ABCDEFGHKMNRSTUVXYZ0123456789"
LABC, WHT, ORG, REDC, SUBC = (150, 160, 175), (240, 244, 250), (255, 112, 44), (255, 64, 46), (200, 208, 220)
def A(c, a): return c + (int(255 * clamp(a)),)


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


def text_k(t, a, b, d=SCR):
    return min(prog(t, a, d), 1 - prog(t, b - d, d)) if a <= t < b else 0.0


def odometer(dr, hud, x, y, value, ndig, font, fill, dim, comma=True):
    s = f"{int(10 ** ndig - 1):,}" if comma else str(int(10 ** ndig - 1))
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


def bracket_box(dr, x0, y0, x1, y1, k):
    a = min(1, k * 2)
    x1 = x0 + (x1 - x0) * (.9 + .1 * eo(k))       # box snaps open
    dr.rectangle([x0, y0, x1, y1], fill=(4, 5, 8, int(150 * a)))
    c = (210, 220, 235, int(a * 128)); L = 26
    dr.rectangle([x0, y0, x1, y1], outline=(210, 220, 235, int(a * 40)), width=1)
    for (x, y, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        dr.line([(x, y + sy * L), (x, y), (x + sx * L, y)], fill=c, width=3)


def leader(dr, a, b, alpha, col=(255, 120, 60)):
    k = eo(alpha)
    b = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    dr.line([a, b], fill=(220, 228, 240, int(140 * alpha)), width=2)
    x, y = b
    dr.ellipse([x - 8, y - 8, x + 8, y + 8], outline=col + (int(230 * alpha),), width=3)
    dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col + (int(255 * alpha),))


def big_lines(dr, x, y, lines, k, seed):
    for i, (txt, col) in enumerate(lines):
        dr.text((x, y + i * 92), scramble(txt, k, seed + i), font=F_HEAD, fill=A(col, k))


def hud_layer(t, elems, an):
    hud = Image.new('RGBA', (W, H))
    dr = ImageDraw.Draw(hud)
    dx, dy = 6 * math.sin(1.1 * t), 5 * math.sin(.8 * t + 1)
    x0, y0 = TXT_X - 20 + dx, 280 + dy
    sd = int(t * 30)                              # re-roll scramble glyphs every frame
    # headline: frame 1 fully legible; returns for the loop
    k = max(text_k(t, -1, TC), prog(t, LOOP, SCR))
    tl = t if t < DUR / 2 else t - DUR
    if k > 0:
        elems.append('headline')
        s = 1 + .05 * (1 - eo(prog(tl, 0, .5)))
        for i, line in enumerate(["WHAT DOES", "490 KM/H DO", "TO A TYRE?"]):
            txt = scramble(line, k, 11 + i + sd)
            xx, yy = TXT_X + dx * .5, 262 + i * 98 * s + dy * .5
            if i == 1:
                u = eo(prog(tl, .05, .5))
                dr.rectangle([xx, yy + 90, xx + 404 * u, yy + 96], fill=A(ORG, k))
                dr.text((xx, yy), txt[:8], font=F_HEAD, fill=A(ORG, k))
                dr.text((xx + F_HEAD.getlength(txt[:8]), yy), txt[8:], font=F_HEAD, fill=A(WHT, k))
            else:
                dr.text((xx, yy), txt, font=F_HEAD, fill=A(WHT, k))
    # car: 136 m / second
    k = text_k(t, TC + .1, t1)
    if k > 0:
        elems.append('speed_callout')
        bracket_box(dr, x0, y0, x0 + 840, y0 + 330, k)
        dr.text((x0 + 28, y0 + 22), scramble("AT 490 KM/H, ABOUT", k, 21 + sd), font=F_LAB, fill=A(LABC, k))
        v = 136 * eo(prog(t, TC + .15, .9))
        xe = odometer(dr, hud, x0 + 24, y0 + 84, v, 3, F_VAL, A(WHT, k), A((70, 76, 88), k), comma=False)
        dr.text((xe + 18, y0 + 136), scramble("M / SECOND", k, 22 + sd), font=F_UNIT, fill=A(ORG, k))
        dr.text((x0 + 28, y0 + 252), scramble(f"DISTANCE {136 * (t - TC):06.1f} M", k, 23), font=F_LAB,
                fill=A(SUBC, k))
    # rpm
    k = text_k(t, t1 + .1, t2)
    if k > 0:
        elems.append('rpm_callout')
        bracket_box(dr, x0, y0, x0 + 760, y0 + 390, k)
        dr.text((x0 + 28, y0 + 22), scramble("ROTATION, EACH TYRE", k, 31 + sd), font=F_LAB, fill=A(LABC, k))
        v = 4100 * io(prog(t, t1 + .1, 1.5))
        xe = odometer(dr, hud, x0 + 24, y0 + 84, v, 4, F_VAL, A(WHT, k), A((70, 76, 88), k))
        dr.text((xe + 14, y0 + 136), "rpm", font=F_UNIT, fill=A(WHT, k))
        dr.text((x0 + 28, y0 + 238), scramble(f"REVS {4100 / 60 * max(0, t - t1):06.1f}", k, 32), font=F_LAB,
                fill=A(SUBC, k))
        ks = prog(t, t1 + .45, SCR) * k
        if ks > 0:
            tw = F_CHIP.getlength("STRETCH: EXAGGERATED")
            dr.rectangle([x0 + 24, y0 + 306, x0 + 48 + tw, y0 + 370], outline=A(ORG, ks), width=2)
            dr.text((x0 + 36, y0 + 310), scramble("STRETCH: EXAGGERATED", ks, 33 + sd), font=F_CHIP, fill=A(ORG, ks))
        leader(dr, (x0 + 760, y0 + 390), an['top'], k)
    # g + stone
    k = text_k(t, t2 + .1, t3)
    if k > 0:
        elems.append('g_callout')
        bracket_box(dr, x0, y0, x0 + 840, y0 + 390, k)
        dr.text((x0 + 28, y0 + 22), scramble("LOAD AT THE TREAD", k, 41 + sd), font=F_LAB, fill=A(LABC, k))
        v = g_val(t)
        sl = 1 + .9 * (1 - oc(prog(t, STAMP, .16))) if t >= STAMP else 1
        col = ORG if t >= STAMP else WHT
        if sl > 1.01:
            tile = Image.new('RGBA', (700, 200))
            ImageDraw.Draw(tile).text((10, 10), "5,300 g", font=F_VAL, fill=A(col, k))
            tile = tile.resize((int(700 * sl), int(200 * sl)), Image.BILINEAR)
            hud.alpha_composite(tile, (int(x0 + 14 - 350 * (sl - 1) * .3), int(y0 + 74 - 100 * (sl - 1) * .5)))
        else:
            xe = odometer(dr, hud, x0 + 24, y0 + 84, v, 4, F_VAL, A(col, k), A((70, 76, 88), k))
            dr.text((xe + 14, y0 + 136), "g", font=F_UNIT, fill=A(col, k))
        dr.text((x0 + 28, y0 + 238), scramble(f"1 KG STONE ~ {max(1, v) / 1000:.1f} TONNES", k, 42), font=F_LAB,
                fill=A(SUBC, k))
        for i in range(6):                        # 5.3 tonnes as tonne blocks, filling with the counter
            f = clamp(v / 1000 - i)                # last block fills to 0.3 (5.3 t)
            bx, by = x0 + 28 + i * 66, y0 + 310
            dr.rectangle([bx, by, bx + 54, by + 56], outline=A(SUBC, .5 * k), width=2)
            if f > 0:
                dr.rectangle([bx + 4, by + 4, bx + 4 + 46 * f, by + 52], fill=A(ORG, .85 * k))
        tw = F_CHIP.getlength("ROUGHLY")
        dr.rectangle([x0 + 440, y0 + 306, x0 + 464 + tw, y0 + 370], outline=A(SUBC, k), width=2)
        dr.text((x0 + 452, y0 + 310), scramble("ROUGHLY", k, 43 + sd), font=F_CHIP, fill=A(SUBC, k))
        if 'stone' in an:
            leader(dr, (x0 + 840, y0 + 390), an['stone'], k)
    # belts
    k = text_k(t, t3 + .15, TR)
    if k > 0:
        elems.append('belts_callout')
        bracket_box(dr, x0, y0, x0 + 840, y0 + 350, k)
        dr.text((x0 + 28, y0 + 22), scramble(f"CROSS-SECTION  REVS {4100 / 60 * (t - t1):05.0f}", k, 51 + sd),
                font=F_LAB, fill=A(LABC, k))
        big_lines(dr, x0 + 24, y0 + 84, [("REINFORCED", WHT), ("BELTS", ORG)], k, 52)
        dr.text((x0 + 28, y0 + 278), scramble("TO WITHSTAND ~5,300 g", k, 54), font=F_LAB, fill=A(SUBC, k))
        if 'belt' in an:
            leader(dr, (x0 + 600, y0 + 350), an['belt'], k)
    # rig
    k = text_k(t, TR + .1, t4)
    if k > 0:
        elems.append('rig_callout')
        bracket_box(dr, x0, y0, x0 + 840, y0 + 450, k)
        dr.text((x0 + 28, y0 + 22), scramble("TEST RIG // DRUM", k, 61 + sd), font=F_LAB, fill=A(LABC, k))
        dr.text((x0 + 28, y0 + 128), scramble("UP TO", k, 62), font=F_CHIP, fill=A(SUBC, k))
        v = 511 * io(prog(t, TR + .2, 1.6))
        xe = odometer(dr, hud, x0 + 210, y0 + 84, v, 3, F_VAL, A(WHT, k), A((70, 76, 88), k), comma=False)
        dr.text((xe + 14, y0 + 136), "KM/H", font=F_UNIT, fill=A(ORG, k))
        dr.text((x0 + 28, y0 + 248), scramble("BUILT FOR SPACE", k, 63), font=F_CHIP, fill=A(WHT, k))
        dr.text((x0 + 28, y0 + 306), scramble("SHUTTLE TYRES", k, 64), font=F_CHIP, fill=A(WHT, k))
        dr.text((x0 + 28, y0 + 376), scramble(f"DRUM {math.degrees(phi(t) / DRUM_R) % 360:05.1f} DEG", k, 65),
                font=F_LAB, fill=A(LABC, k))
        if 'rigc' in an:
            leader(dr, (x0 + 840, y0 + 450), an['rigc'], k)
    # x-ray
    k = text_k(t, t4 + .1, t5)
    if k > 0:
        elems.append('xray_callout')
        pn, pct = an.get('pass', (2, 100.0))
        bracket_box(dr, x0, y0, x0 + 840, y0 + 350, k)
        dr.text((x0 + 28, y0 + 22), scramble(f"PASS {pn}/2  {pct:05.1f}%", k, 71 + sd), font=F_LAB, fill=A(LABC, k))
        big_lines(dr, x0 + 24, y0 + 84, [("EVERY TYRE", WHT), ("X-RAYED", WHT)], k, 72)
        dr.text((x0 + 28, y0 + 278), scramble("EVERY SINGLE ONE", k, 74), font=F_LAB, fill=A(SUBC, k))
        if 'scan' in an:
            leader(dr, (x0 + 840, y0 + 350), an['scan'], k)
    # flaw
    k = text_k(t, t5 + .1, t6)
    if k > 0 and 'flaw' in an:
        elems.append('flaw_callout')
        fx, fy = an['flaw']
        bracket_box(dr, x0, y0, x0 + 840, y0 + 350, k)
        dr.text((x0 + 28, y0 + 22), scramble(f"ANGLE {an['flaw_ang']:05.1f} DEG", k, 81 + sd), font=F_LAB,
                fill=A(LABC, k))
        big_lines(dr, x0 + 24, y0 + 84, [("EVEN A", WHT), ("TINY FLAW", REDC)], k, 82)
        dr.text((x0 + 28, y0 + 278), scramble("IS DANGEROUS", k, 84), font=F_LAB, fill=A(SUBC, k))
        leader(dr, (x0 + 600, y0 + 350), (fx, fy), k, (255, 70, 50))
        sz = 34 + 120 * (1 - eo(prog(t, t5 + .2, .5))) + 6 * math.sin(t * 9)
        for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            cx_, cy_ = fx + sx * sz, fy + sy * sz
            dr.line([(cx_, cy_ - sy * 16), (cx_, cy_), (cx_ - sx * 16, cy_)], fill=A(REDC, k), width=3)
    # poll
    k = text_k(t, t6 + .1, LOOP)
    if k > 0:
        elems += ['question', 'poll']
        for i, line in enumerate(["WOULD YOU", "RIDE IT?"]):
            dr.text((TXT_X + dx * .5, 262 + i * 98 + dy * .5), scramble(line, k, 91 + i + sd), font=F_HEAD,
                    fill=A(WHT, k))
        for i, lab in enumerate(["YES", "NO"]):
            ki = eo(prog(t, t6 + .35 + .1 * i, .3)) * k
            if ki <= 0: continue
            x = TXT_X + i * 360 - 60 * (1 - ki) + dx
            y = 520 + dy
            sel = (i == 0 and t6 + 1.0 <= t < t6 + 1.75) or (i == 1 and t6 + 1.75 <= t < LOOP - .1)
            dr.rectangle([x, y, x + 320, y + 124], fill=A(WHT, .92 * ki) if sel else (6, 7, 10, int(170 * ki)),
                         outline=A(WHT, .8 * ki), width=2)
            tw = F_BTN.getlength(lab)
            dr.text((x + 160 - tw / 2, y + 20), lab, font=F_BTN, fill=A((10, 12, 16) if sel else WHT, ki))
        dr.text((TXT_X + dx, 680 + dy), scramble("COMMENT: YES OR NO?", k, 95), font=F_CHIP, fill=A((170, 178, 190), k))
    # scene labels: ruler posts on the straight
    for xy, lab, z in an.get('marks', []):
        (px, py), (qx, qy) = xy
        a = clamp(1.6 - z / 40) * .9
        dr.line([(px, py), (qx, qy)], fill=A(WHT, a), width=3)
        dr.line([(qx, qy), (qx + 30, qy)], fill=A(ORG, a), width=3)
        if 0 < qx < 860 and qy > 240:
            dr.text((qx + 36, qy - 28), lab, font=F_CHIP, fill=A(WHT, a))
    dr.text((40, 36), "Yub", font=F_TAG, fill=(200, 205, 215, 200)); elems.append('yub_tag')
    if PREVIEW:
        dr.text((W - 150, H - 64), "PREVIEW", font=F_TAG, fill=(255, 255, 255, 110))
    return hud


# ---- frame ----------------------------------------------------------------
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - .55 * (((XX - W / 2) / (W * .75)) ** 2 + ((YY - H * .55) / (H * .7)) ** 2)).clip(.35, 1)[..., None]


def blur(im, r): return np.asarray(im.filter(ImageFilter.GaussianBlur(float(r))), np.float32) / 255
def L(im): return np.asarray(im, np.float32)[..., None] / 255


def small_blur(arr, r):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)).resize((W, H), Image.BILINEAR), np.float32) / 255


def red_marker(fx, fy, t, t0, kf):
    rl = Image.new('L', (W, H)); rd = ImageDraw.Draw(rl)
    pulse = .5 + .5 * math.sin(2 * math.pi * 2.2 * (t - t0)) + bump(t, FLAWHIT, .03, .4)
    r = 5 + 4 * pulse
    rd.ellipse([fx - r, fy - r, fx + r, fy + r], fill=int(255 * kf))
    frac = ((t - t0) * 1.3) % 1
    rr = 12 + 70 * frac
    rd.ellipse([fx - rr, fy - rr, fx + rr, fy + rr], outline=int(255 * kf * (1 - frac)), width=3)
    gs = 1 + .5 * bump(t, FLAWHIT, .03, .5)
    rd.line([(fx + x * gs, fy + y * gs) for x, y in [(-16, -7), (-7, 2), (0, -4), (8, 6), (17, 0)]],
            fill=int(255 * kf), width=2)
    rlf = L(rl)
    return rlf * RED * 1.3 + small_blur(rlf.repeat(3, 2), 4) * RED * (1.4 + pulse)


def tyre_frame(t, elems, an, rig=False):
    cvf = cam_rig if rig else cam
    cv = cvf(t)
    keys = ('near', 'far', 'tread', 'ground')
    acc = blur_acc(t, cvf, draw_rig if rig else draw_tyre, keys)
    contact, top = tyre_points(t, cv)
    an['top'] = tuple(top[0])
    h = heat(t)
    sk = sec_k(t)
    if sk > .02:                                  # tyre falls behind the section: dim + defocus
        near, tread = blur(acc['near'], 5 * sk)[..., None], blur(acc['tread'], 5 * sk)[..., None]
        dim = 1 - .5 * sk
        near, tread = near * dim, tread * dim
    else:
        near, tread, dim = L(acc['near']), L(acc['tread']), 1.0
    far = blur(acc['far'], 3)[..., None] * dim
    gnd = blur(acc['ground'], 1.2)[..., None] * dim
    tcol = WHITE * (1 - min(1, h * .75)) + ACC * min(1, h * .75)
    img = BG + near * WHITE + far * FAR * .7 + gnd * FAR * .35 + tread * tcol
    tk = thermal_k(t) * dim
    if tk > .02:
        img += THERM_LUT[thermal_layer(t, cv)] * tk * .8
    lk = lidar_tyre_k(t)
    if lk > 0:
        pc, pr = lidar_tyre(t, cv)
        img = img * (1 - .6 * lk) + pc[..., None] * XRC * lk + pr[..., None] * RED * 1.4 * lk
    if rig:
        img += lidar_ground(t, cv, y0=-7.6, sx=14, sz=8, scroll=0.0, ring_s=4)[..., None] * XRC * .8
        an['rigc'] = tuple(contact[0])
    else:
        img += lidar_ground(t, cv)[..., None] * XRC * .9 * dim
    gl = Image.new('L', (W, H)); g = ImageDraw.Draw(gl)
    (cx0, cy0) = contact[0]
    rr = (70 + 60 * h) * (4 / max(cv[3], 1.5)) ** .6
    g.ellipse([cx0 - rr * 1.8, cy0 - rr * .6, cx0 + rr * 1.8, cy0 + rr * .6], fill=int(200 * min(1, h) * dim))
    img += small_blur(L(gl).repeat(3, 2), 10) * ACC * 1.1 + small_blur(tread.repeat(3, 2), 6) * ACC * h * 1.4
    if sk > .02:
        elems.append('section')
        lay, an['belt'] = section_layers(t, sk)
        fl = L(lay['fill'])[..., 0].reshape(ROWS, CH, COLS, CW).mean(axis=(1, 3))
        img += glyphs(fl * (.5 + .25 * math.sin(t * 40)) * sk, t)[..., None] * FAR * 1.0   # ASCII flicker
        bl = L(lay['belt'])
        img += L(lay['sec']) * WHITE + blur(lay['secb'], 2.5)[..., None] * FAR * .8
        img += bl * (ACC * .6 + HOT * .4) + small_blur(bl.repeat(3, 2), 5) * ACC * 1.6
        by = an['belt'][1]
        tg = np.clip(1 - np.abs(YY - by) / 260, 0, 1) ** 1.4 * blur(lay['fill'], 3) * sk
        gsum = sum(io(prog(t, t3 + .5 + .3 * i, .35)) for i in range(3)) / 3
        img += THERM_LUT[(np.clip(tg * (.35 + .65 * gsum), 0, 1) * 255).astype(np.uint8)] * .75
    sk_ = stone_k(t)
    if sk_ > 0:
        elems.append('stone')
        sl = {kk: Image.new('L', (W, H)) for kk in ('near', 'acc')}
        an['stone'], _ = draw_stone(t, cv, {kk: ImageDraw.Draw(v) for kk, v in sl.items()}, sk_)
        sa = L(sl['acc'])
        img += L(sl['near']) * WHITE + sa * ACC * 1.2 + small_blur(sa.repeat(3, 2), 4) * ACC
    kf = prog(t, t5 + .15, .2) * (1 - prog(t, t6 - .15, .15)) if t5 <= t < t6 else 0.0
    if kf > 0:
        elems.append('flaw_marker')
        (fx, fy), an['flaw_ang'] = flaw_screen(t, TH_F)
        an['flaw'] = (fx, fy)
        img += red_marker(fx, fy, t, t5, kf)
    ke = bump(t, EARLY[0], .04, EARLY[1] - EARLY[0] - .04)
    if ke > 0:                                    # early stake: 0.3 s red flaw flash (part of the tyre)
        (fx, fy), _ = flaw_screen(t, TH_E)
        img += red_marker(fx, fy, t, EARLY[0], ke) * 1.3
    if sk > .5:
        ob = section_obstacle(t)
    else:
        ob = (contact[0][0], contact[0][1] - 1400 / cv[3], 1400 * 1.08 / cv[3])
    sp = Image.new('RGB', (W, H))
    n = draw_sparks(t, contact, sp)
    if n: elems.append('sparks')
    sp = np.asarray(sp, np.float32) / 255
    img += sp + small_blur(sp, 3) * 1.2
    return img, flow_amp(t), ob, h


# ---- fine ASCII (jaguar-style): shaded solid -> dense luminance-mapped glyphs ---
CW2, CH2 = 12, 20
COLS2, ROWS2 = W // CW2, H // CH2


def _fine_atlas():
    chars = [chr(c) for c in range(33, 127)]
    f = F('Medium', 17)
    gl = []
    for c in chars:
        im = Image.new('L', (CW2, CH2)); ImageDraw.Draw(im).text((0, 0), c, font=f, fill=255)
        gl.append(np.asarray(im, np.float32) / 255)
    gl = np.stack([np.zeros((CH2, CW2), np.float32)] + gl)
    cov = gl.mean(axis=(1, 2))
    order = np.argsort(cov)
    levels = 12
    buckets = [order[(cov[order] >= np.quantile(cov, i / levels) - 1e-6) & (cov[order] <= np.quantile(cov, (i + 1) / levels) + 1e-6)]
               for i in range(levels)]
    buckets[0] = np.array([0])                    # darkest = blank
    n = max(len(b) for b in buckets)
    tab = np.stack([np.resize(b, n) for b in buckets])
    return gl, tab, np.array([len(b) for b in buckets])


FATLAS, FTAB, FLEN = _fine_atlas()


def ascii_fine(rgb, t, gain=1.6):
    cells = rgb.reshape(ROWS2, CH2, COLS2, CW2, 3).mean(axis=(1, 3))
    lum = cells.max(-1)
    rnd = np.random.default_rng(int(t * 30)).integers(0, 1 << 30, lum.shape)   # shimmer every frame
    jit = (rnd >> 20) % 7 - 3                     # +-3 density levels: jaguar-style sparkle
    lv = np.clip((lum * gain * (FTAB.shape[0] - 1)).astype(int) + jit * (lum > .06), 0, FTAB.shape[0] - 1)
    idx = FTAB[lv, rnd % FLEN[lv]]
    g = FATLAS[idx].transpose(0, 2, 1, 3).reshape(ROWS2 * CH2, COLS2 * CW2)
    col = np.clip(cells / (lum[..., None] + 1e-4), 0, 1).repeat(CH2, 0).repeat(CW2, 1)
    return g[..., None] * col * np.clip(.55 + lum.repeat(CH2, 0).repeat(CW2, 1)[..., None] * 1.2, 0, 1.5)


LIGHT = np.array([-.25, .75, -.6]); LIGHT /= np.linalg.norm(LIGHT)


def unproject(sx, sy, cv, f=1400.0):
    """Camera ray for screen points -> world origin and direction (inverse of project)."""
    yaw, pitch, roll, dist, cx, cy, tx, ty, tz = cv
    def back(x3, y3, z3):
        cr, sr = math.cos(roll), math.sin(roll)
        x1, y2 = x3 * cr + y3 * sr, -x3 * sr + y3 * cr
        z2 = z3 - dist
        cp, sp = math.cos(pitch), math.sin(pitch)
        y, z1 = y2 * cp + z2 * sp, -y2 * sp + z2 * cp
        c, s_ = math.cos(yaw), math.sin(yaw)
        return np.stack([x1 * c - z1 * s_ + tx, y + ty, x1 * s_ + z1 * c + tz])
    o = back(np.zeros_like(sx), np.zeros_like(sx), np.zeros_like(sx))
    p = back((sx - cx) / f, -(sy - cy) / f, np.ones_like(sx))
    return o, p - o


CELL_Y, CELL_X = np.mgrid[0:ROWS2, 0:COLS2].astype(np.float64)


def asphalt_cells(t, cv):
    """Hashed ASCII asphalt per glyph cell, rushing past at road speed."""
    o, d = unproject(CELL_X * CW2 + CW2 / 2, CELL_Y * CH2 + CH2 / 2, cv)
    with np.errstate(divide='ignore', invalid='ignore'):
        k = -o[1] / d[1]
    x, z = o[0] + k * d[0], o[2] + k * d[2]
    ok = (k > 0) & (np.abs(z) < 3.6) & (x < 160) & (x > -60)
    ix, iz = np.floor((x + travel(t)) / .5), np.floor(z / .35)
    hsh = (np.sin(ix * 12.9898 + iz * 78.233) * 43758.5453) % 1
    v = np.where(hsh > .55, .05 + .22 * (hsh - .55) / .45, .0)     # sparse, dim: car stays the subject
    v = np.where(ok, v * np.clip(1.4 - np.nan_to_num(k) / 60, 0, 1), 0)
    return v.repeat(CH2, 0).repeat(CW2, 1).astype(np.float32)


def car_shade(t, cv):
    """Shaded solid car + road as an RGB luminance image (input to the glyph pass)."""
    im = Image.new('RGB', (W, H)); d = ImageDraw.Draw(im)
    d_tr = travel(t)
    # road: lane dashes, edges, ruler ticks, faint cross grid (all rush past)
    polys = []
    for x0 in np.arange(-30, 220, 6) - d_tr % 6:
        for zz in (-1.75, 1.75):
            polys.append(([[x0, 0, zz - .15], [x0 + 3, 0, zz - .15], [x0 + 3, 0, zz + .15], [x0, 0, zz + .15]], .8))
    for zz in (-3.5, 3.5):
        polys.append(([[-30, 0, zz - .15], [220, 0, zz - .15], [220, 0, zz + .15], [-30, 0, zz + .15]], .75))
    for x0 in np.arange(-30, 120, 1.0) - d_tr % 1:
        big = round(x0 + d_tr) % 5 == 0
        polys.append(([[x0, 0, 3.7], [x0 + .14, 0, 3.7], [x0 + .14, 0, 3.7 + (1.0 if big else .45)], [x0, 0, 3.7 + (1.0 if big else .45)]], 1.0))
    for P, v in polys:
        xy, z = project(np.array(P, float), *cv)
        if z.min() < .4: continue
        fade = clamp(1.6 - z.mean() / 90)
        c = int(255 * v * fade)
        d.polygon([tuple(p) for p in xy], fill=(c, c, c))
    # body quads, painter-sorted, Lambert + rim
    S = np.array(CAR_SECS)                         # (nsec, nang, 3)
    quads = []
    for i in range(S.shape[0] - 1):
        for j in range(S.shape[1] - 1):
            q = np.array([S[i, j], S[i + 1, j], S[i + 1, j + 1], S[i, j + 1]])
            quads.append((q, j))
    for cap in (0, S.shape[0] - 1):                # nose / tail caps
        quads.append((S[cap], -1))
    items = []
    for q, j in quads:
        xy, z = project(q, *cv)
        if z.min() < .3: continue
        n = np.cross(q[1] - q[0], q[-1] - q[0]) if len(q) == 4 else np.array([1.0, 0, 0])
        n = n / (np.linalg.norm(n) + 1e-9)
        cq = q.mean(0)
        if n @ (cq - [cq[0], .45, 0]) < 0: n = -n     # outward normals
        lam = max(0.0, n @ LIGHT)
        glass = 4 <= j <= 6 and abs(q[:, 0].mean() + .3) < 1.0
        xm = q[:, 0].mean()
        v = (.12 if glass else .45 + .55 * lam ** 1.2) * (1.0 if j >= 0 else .5)
        if j in (0, 1, 8, 9): v *= .45                             # dark rocker
        if j in (1, 2, 7, 8) and -.9 < xm < .2: v = .05            # side intake
        if j in (3, 6): v = min(1, v * 1.3)                        # shoulder highlight
        items.append((z.mean(), xy, v))
    for _, xy, v in sorted(items, key=lambda x: -x[0]):
        c = int(255 * min(1, v))
        d.polygon([tuple(p) for p in xy], fill=(c, c, c))
    # wheels: dark discs with bright spinning spokes
    a = -d_tr / .34
    for wx, wz in WHEEL_POS:
        disc = np.c_[wx + .34 * np.cos(np.linspace(0, 6.3, 28)), .34 + .34 * np.sin(np.linspace(0, 6.3, 28)), np.full(28, wz)]
        xy, z = project(disc, *cv)
        if z.min() < .3: continue
        d.polygon([tuple(p) for p in xy], fill=(18, 18, 18))
        rim = np.c_[wx + .25 * np.cos(np.linspace(0, 6.3, 24)), .34 + .25 * np.sin(np.linspace(0, 6.3, 24)), np.full(24, wz)]
        d.line([tuple(p) for p in project(rim, *cv)[0]], fill=(210, 210, 210), width=4)
        for k in range(5):
            b = a + k * 2 * math.pi / 5
            xy, _ = project(np.array([[wx, .34, wz], [wx + .24 * math.cos(b), .34 + .24 * math.sin(b), wz]]), *cv)
            d.line([tuple(p) for p in xy], fill=(245, 245, 245), width=6)
    # tail lights (heat accent)
    xy, z = project(np.array([(-2.27, .66, -.85), (-2.27, .66, .85), (-2.27, .78, .85), (-2.27, .78, -.85)]), *cv)
    if z.min() > .3:
        d.polygon([tuple(p) for p in xy], fill=(255, 92, 23))
    out = np.asarray(im, np.float32) / 255
    return np.maximum(out, asphalt_cells(t, cv)[..., None])


def car_frame(t, elems, an):
    cv = cam_car(t)
    shade = car_shade(t, cv)
    img = BG + ascii_fine(shade, t, gain=1.9) * WHITE   # the car + straight, in ASCII
    acc = blur_acc(t, cam_car, draw_car, ('near', 'far', 'ground', 'acc'), K=3)
    img += L(acc['near']) * WHITE * .45             # faint wire edges for definition
    ta = L(acc['acc'])
    img += small_blur(ta.repeat(3, 2), 5) * ACC * 1.6
    img += lidar_ground(t, cv, y0=0.0, sx=40, sz=14, scroll=travel(t), ring_s=6)[..., None] * XRC * .25
    an['marks'] = car_markers(t, cv)
    c, _ = project(np.array([[0.0, .6, 0.0]]), *cv)
    return img, flow_amp(t), (c[0][0], c[0][1], 1400 * 2.0 / cv[3]), .3


def frame(t, info=None):
    elems = ['scene']
    an = {}
    sc = scene(t)
    if sc == 'car':
        img, fa, ob, h = car_frame(t, elems, an)
        spin = 1.0
    else:
        img, fa, ob, h = tyre_frame(t, elems, an, rig=(sc == 'rig'))
        spin = None
    if fa > .02:
        fl, fh = flow_layers(t, ob, fa, spin)
        img += fl[..., None] * FAR * 1.5 + small_blur(fl[..., None].repeat(3, 2), 3) * FAR * .5
        img += fh[..., None] * ACC * (.4 + .6 * min(1, h)) + small_blur(fh[..., None].repeat(3, 2), 3) * ACC * .5
    st, amp = streaks(t)
    img += st
    if amp > .05 or fa > .02: elems.append('airflow')   # ASCII streaks + CFD lines
    img += small_blur(img, 5) * .35 + small_blur(img, 22) * .45          # bloom
    xs = xray_state(t)
    if xs is not None:
        elems.append('xray_scan')
        m, x, pn, pct = xs
        an['pass'] = (pn, pct)
        mm = m[None, :, None]
        img = img * (1 - mm) + xray_of(img, t) * mm
        if -20 < x < W + 20:
            prof = np.exp(-((XCOL - x) / 5) ** 2) * 1.3 + np.exp(-((XCOL - x) / 70) ** 2) * .22
            img += prof[None, :, None] * VFADE[:, None, None] * XRC
            an['scan'] = (x, cam(t)[5])
    m = transition_mask(t)
    if m.max() > 0:
        mm = m.repeat(CH)[:, None, None]
        img = img * (1 - mm) + ascii_of(img, t) * mm
    img *= VIG
    img += np.random.default_rng(int(t * FPS)).normal(0, .012, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    out.alpha_composite(hud_layer(t, elems, an))
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
