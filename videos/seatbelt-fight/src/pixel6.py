"""6-second PIXEL stickman fight test (no VO, no captions) -> out/seatbelt-fight/pixel-fight6.mp4

Motion reuses fight6.py (mocap move library, key-aligned segments, 6-frame bone-direction cross-fades,
stage solve, foot-plant IK, contact IK) with a new 12-beat sheet (pixel6_choreo.json). New here:
contact frames re-found from effector speed (full extension after the speed peak) with the defender's
reaction started on that frame; figures drawn on 1s at 30 fps, effects on 2s, held to 60 fps output.
Look: whole scene drawn at 270x480 in a fixed 32-colour palette (Bayer-dithered gradients, 1-px dark
outlines), 6 parallax layers moved in whole pixels, nearest-neighbour 4x upscale to 1080x1920.
Usage: python pixel6.py [--drawings 0,40,...]   (preview PNGs of single 30 fps drawings)
"""
import json, math, os, subprocess, sys, types
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import cairo  # noqa: F401
except ImportError:  # fight6's flat-vector drawing is not used here; only its motion pipeline
    sys.modules['cairo'] = types.ModuleType('cairo')
import fight6 as F6  # noqa: E402
from fight6 import I, proj, head_c, ease, sample, mv  # noqa: E402
import sfx  # noqa: E402

F6.SHEET = os.path.join(HERE, '../pixel6_choreo.json')
OUT = F6.OUT
W, H, UP, FPS = 270, 480, 4, 60
NDRAW = 180                                   # 6.0 s of 30 fps drawings
S0 = 0.235                                    # wide-shot scale (px per world unit): figure ~205 px = 43 %
GY0 = 420                                     # ground row of the wide shot
D = {'hero': 1, 'opp': -1}

# ---------------------------------------------------------------- palette (32 colours)
PAL_HEX = ['#1b1435', '#2c1f52', '#4a2c6e', '#7a3a78', '#b8506e', '#e5795f', '#f6b26b', '#ffe2a0',   # 0-7 dusk sky
           '#3a2a5c', '#4f3570', '#23324a', '#2f4a5a', '#3e6b5e', '#5f8f5a', '#8fb35a', '#c9cf6a',   # 8-15 hills / meadow
           '#6b4a3a', '#9c6b4a', '#0c0716', '#8a5a3c', '#6a4230', '#1a1210', '#f2efe8', '#b9b6c4',   # 16-23 dirt, ink, hero
           '#15141c', '#8e1c2a', '#5e1020', '#ffffff', '#ffd84a', '#ff8a2a', '#e8332a', '#2bb3a6']   # 24-31 opp, fx, car
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in PAL_HEX], np.uint8)
INK, SKIN, SKIN2, HAIR, TEE, TEE2, SHORTS, RED, RED2 = 18, 19, 20, 21, 22, 23, 24, 25, 26
WHITE, YEL, ORA, FIRE, CAR = 27, 28, 29, 30, 31
CLEAR = 255
B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def bayer(h, w, y0=0, x0=0):
    return B4[(np.arange(h)[:, None] + y0) % 4, (np.arange(w)[None, :] + x0) % 4]


def vgrad(h, w, cols, y_a, y_b, y0=0):
    """Vertical Bayer-dithered gradient through palette indices cols between rows y_a..y_b."""
    y = np.arange(h)[:, None] + y0
    t = np.clip((y - y_a) / max(y_b - y_a, 1), 0, 1) * (len(cols) - 1)
    i = np.minimum(np.floor(t).astype(int), len(cols) - 2); f = t - i
    c = np.array(cols)
    return np.where(f * 16 > bayer(h, w, y0), c[i + 1], c[i]).astype(np.uint8) * np.ones((1, w), np.uint8)


def paste(dst, L, x, y):
    h, w = L.shape; Hh, Ww = dst.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, Ww), min(y + h, Hh)
    if x1 <= x0 or y1 <= y0: return
    src = L[y0 - y:y1 - y, x0 - x:x1 - x]; m = src != CLEAR
    dst[y0:y1, x0:x1][m] = src[m]


def ridge(w, base, amps, rng):
    x = np.arange(w)
    y = np.full(w, float(base))
    for a, per in amps:
        y += a * np.sin(2 * math.pi * x / per + rng.uniform(0, 6.3))
    return np.round(y).astype(int)


# ---------------------------------------------------------------- world layers (painted once)
LW, LH = 1600, 700


class Layer:
    def __init__(s, a, p, img):
        s.p, s.img = p, img


def paint_layers(road=False):
    rng = np.random.default_rng(7)
    sky = vgrad(LH, W, [0, 1, 2, 3, 4, 5, 6], 10, 330)
    st = rng.integers(0, W, 40), rng.integers(4, 170, 40)
    sky[st[1], st[0]] = np.where(rng.random(40) < .3, 7, 23)
    yy, xx = np.mgrid[0:LH, 0:W]                            # moon: high left, never behind the heads
    sky[(xx - 44) ** 2 + (yy - 52) ** 2 <= 12 ** 2] = 7
    sky[(xx - 48) ** 2 + (yy - 49) ** 2 <= 3] = 6; sky[(xx - 40) ** 2 + (yy - 57) ** 2 <= 2] = 6
    for cx, cy, cw in ((190, 120, 70), (80, 175, 90), (230, 205, 60)):          # flat dusk cloud bands
        for k in range(3):
            y0 = cy + k * 4; x0 = cx - cw // 2 + k * 9 - 4; x1 = cx + cw // 2 - k * 7
            sky[y0:y0 + 4, x0:x1] = 3 if k < 2 else 4
        sky[cy + 12:cy + 13, cx - cw // 2 + 18:cx + cw // 2 - 20] = 5
    layers = [Layer('sky', 0.0, sky)]
    X = np.arange(LW)

    def band(top, col, rim=None, fill_to=LH):
        L = np.full((LH, LW), CLEAR, np.uint8)
        for x in range(LW):
            L[top[x]:fill_to, x] = col
            if rim is not None: L[top[x], x] = rim
        return L
    far = band(ridge(LW, 286, [(16, 410), (7, 133), (3, 47)], rng), 2, 3)
    far[300:] = np.where(far[300:] != CLEAR, np.where(bayer(LH - 300, LW, 300) < 6, 8, 2), CLEAR)
    layers.append(Layer('far', 0.12, far))
    mid = band(ridge(LW, 318, [(9, 300), (4, 91)], rng), 11, 9)
    for tx in rng.choice(np.arange(60, LW - 60, 23), 26, replace=False):          # pixel trees on the hills
        r = int(rng.integers(7, 14)); ty = 318 - int(rng.integers(8, 26))
        mid[ty:322, tx - 1:tx + 2] = INK
        for (ox, oy, rr) in ((0, -r, r), (-r // 2 - 2, -r // 2, r * 2 // 3), (r // 2 + 2, -r // 2, r * 2 // 3)):
            m = (xx[:, :1] * 0 + (np.arange(LH)[:, None] - (ty + oy))) ** 2 + (X[None, :] - (tx + ox)) ** 2 <= rr * rr
            mid[m] = 10
            m2 = m & ((np.arange(LH)[:, None] - (ty + oy) + X[None, :] - (tx + ox)) < -rr // 2)
            mid[m2] = 11
    layers.append(Layer('mid', 0.3, mid))
    nr = band(ridge(LW, 344, [(5, 70), (3, 23), (2, 11)], rng), 12, 13)
    nr[352:] = CLEAR
    layers.append(Layer('near', 0.6, nr))
    g = np.full((LH, LW), CLEAR, np.uint8)
    g[348:] = vgrad(LH - 348, LW, [14, 13, 12, 11], 348, 520, 348)
    if road:                                                  # asphalt road for the transition
        g[392:452] = vgrad(60, LW, [1, 0], 392, 452, 392)
        g[391] = 23; g[452] = INK
        for x in range(0, LW, 40): g[421:424, x:x + 20] = 7
    else:                                                     # dirt path the fighters stand on
        top = 398 + np.round(3 * np.sin(X / 37)).astype(int); bot = 446 + np.round(3 * np.sin(X / 53 + 1)).astype(int)
        for x in range(LW):
            g[top[x]:bot[x], x] = 16
            g[top[x], x] = 17
        d = bayer(LH, LW) < 4
        g[(g == 16) & d & (np.arange(LH)[:, None] < 406)] = 17
    for _ in range(900):                                       # grass tufts and flowers
        x, y = int(rng.integers(0, LW)), int(rng.integers(352, LH))
        if g[y, x] in (16, 17, 0, 1, 7, 23): continue
        c = 15 if y < 380 else (14 if y < 470 else 13)
        g[y - 2:y, x] = c; g[y - 1, x - 1] = c
        if rng.random() < .06: g[y - 3, x] = 4 if rng.random() < .5 else 7
    layers.append(Layer('ground', 1.0, g))
    fg = np.full((LH, LW), CLEAR, np.uint8)
    for _ in range(260):                                        # dark foreground grass at the bottom edge
        x = int(rng.integers(0, LW)); hgt = int(rng.integers(8, 22)); lean = rng.uniform(-.5, .5)
        for k in range(hgt):
            yy_ = 480 + 30 - k; xx_ = int(round(x + lean * k * k / hgt))
            if 0 <= xx_ < LW: fg[yy_, xx_] = 10 if k < hgt - 3 else 11
    layers.append(Layer('fg', 1.5, fg))
    return layers


def draw_world(img, layers, cx, gy, push):
    for L in layers:
        if L.p == 0:
            img[:] = L.img[:H]; continue
        ox = int(round(cx * S0 * L.p)); oy = int(round((gy - GY0) * L.p + push * 9 * L.p))
        paste(img, L.img, W // 2 - LW // 2 - ox, oy)


# ---------------------------------------------------------------- pixel figures
def cap(dr, p0, p1, r0, r1, col, ink=True):
    p0, p1 = np.asarray(p0[:2], float), np.asarray(p1[:2], float)
    for rr0, rr1, c in (((r0 + 1, r1 + 1, INK),) if ink else ()) + ((r0, r1, col),):
        d = p1 - p0; n = np.linalg.norm(d)
        if n > .5:
            nn = np.array([-d[1], d[0]]) / n
            dr.polygon([tuple(p0 + nn * rr0), tuple(p1 + nn * rr1), tuple(p1 - nn * rr1), tuple(p0 - nn * rr0)], fill=c)
        dr.ellipse([p0[0] - rr0, p0[1] - rr0, p0[0] + rr0, p0[1] + rr0], fill=c)
        dr.ellipse([p1[0] - rr1, p1[1] - rr1, p1[0] + rr1, p1[1] + rr1], fill=c)


def disc(dr, c, r, col, ink=True):
    if ink: dr.ellipse([c[0] - r - 1, c[1] - r - 1, c[0] + r + 1, c[1] + r + 1], fill=INK)
    dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=col)


def to_screen(P, cam):
    cx, gy, s = cam
    Q = proj(P)
    return np.stack([(Q[:, 0] - cx) * s + W / 2, Q[:, 1] * s + gy, Q[:, 2]], -1), s


def draw_fighter(img, P, cam, hero, d, mask=None):
    """Thick-limbed pixel silhouette. Hero: brown skin, dark hair, white tee, black shorts, white shoes.
    Opponent: solid dark red. Parts painted far-to-near, each with a 1-px ink outline."""
    S, s = to_screen(P, cam)
    lay = Image.new('L', (W, H), CLEAR); dr = ImageDraw.Draw(lay)
    Jn = lambda n: S[I[n]]
    zl = np.mean([Jn(n)[2] for n in ('lhumerus', 'lfemur', 'lclavicle')])
    zr = np.mean([Jn(n)[2] for n in ('rhumerus', 'rfemur', 'rclavicle')])
    near = 'l' if zl < zr else 'r'
    parts = []
    for k in 'lr':
        parts.append((np.mean([Jn(k + n)[2] for n in ('femur', 'tibia')]), 'leg', k))
        parts.append((np.mean([Jn(k + n)[2] for n in ('humerus', 'radius', 'hand')]), 'arm', k))
    zt = (Jn('root')[2] + Jn('thorax')[2]) / 2
    parts += [(zt, 'torso', ''), (zt - 1, 'head', '')]
    R = lambda r: max(1.0, r * s)
    for _, kind, k in sorted(parts, key=lambda p: -p[0]):
        nk = k == near
        sk = (SKIN if nk else SKIN2) if hero else (RED if nk else RED2)
        if kind == 'leg':
            hip, kn, an, ball = (Jn(k + n) for n in ('hipjoint', 'femur', 'tibia', 'foot'))
            cap(dr, hip, kn, R(40), R(32), sk); cap(dr, kn, an, R(31), R(21), sk, ink=False)
            if hero: cap(dr, hip, hip + (kn - hip) * 0.7, R(44), R(36), SHORTS, ink=False)
            tip = ball + (ball - an) * 0.45
            cap(dr, an, tip, R(23), R(17), (TEE if nk else TEE2) if hero else sk)
            if hero:
                dn = np.array([0, R(14), 0]); cap(dr, an + dn, tip + dn * .6, R(7), R(5), INK, ink=False)
        elif kind == 'arm':
            sh, el, wr, hd = (Jn(k + n) for n in ('clavicle', 'humerus', 'radius', 'hand'))
            cap(dr, sh, el, R(29), R(25), sk); cap(dr, el, wr, R(25), R(21), sk, ink=False)
            disc(dr, hd, R(25), sk)
            if hero: cap(dr, sh, sh + (el - sh) * .5, R(32), R(29), TEE if nk else TEE2, ink=False)
        elif kind == 'torso':
            root, ub, th, ln = Jn('root'), Jn('upperback'), Jn('thorax'), Jn('lowerneck')
            col = TEE if hero else sk
            cap(dr, ln, head_xy(S), R(20), R(20), SKIN if hero else sk)
            cap(dr, root, ub, R(50), R(56), col); cap(dr, ub, th, R(56), R(50), col, ink=False)
            if hero: cap(dr, root, root, R(48), R(48), SHORTS)
        else:
            c = head_xy(S); r = R(F6.R_HEAD)
            disc(dr, c, r, SKIN if hero else sk)
            a = np.array(c[:2])
            if hero:                                      # hair cap over the back and top of the head
                hb = lay.crop((0, 0, W, H))
                hd_ = ImageDraw.Draw(hb); hd_.ellipse([a[0] - r - d * r * .35, a[1] - r * 1.15, a[0] + r - d * r * .35, a[1] + r * .55], fill=HAIR)
                hb = np.array(hb); m = disk_mask(a, r)
                arr = np.array(lay); arr[m] = hb[m]; lay = Image.fromarray(arr); dr = ImageDraw.Draw(lay)
                ex, ey = int(round(a[0] + d * r * .55)), int(round(a[1] - r * .02))
                dr.rectangle([ex - (1 if d < 0 else 0), ey, ex + (0 if d < 0 else 1), ey + 1], fill=INK)
    arr = np.array(lay)
    m = arr != CLEAR
    img[m] = arr[m]
    if mask is not None: mask |= m
    return S


def head_xy(S):
    a, b = S[I['upperneck']], S[I['head']]
    return a + (b - a) * 0.5


def disk_mask(c, r):
    yy, xx = np.mgrid[0:H, 0:W]
    return (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r


def shadow(img, P, cam):
    S, s = to_screen(P, cam)
    xs = [S[I[k + 'tibia']][0] for k in 'lr']; cx = (min(xs) + max(xs)) / 2; w = (max(xs) - min(xs)) / 2 + 70 * s
    y = cam[1] + 2
    yy, xx = np.mgrid[0:H, 0:W]
    m = ((xx - cx) / max(w, 1)) ** 2 + ((yy - y) / max(4, 14 * s)) ** 2 <= 1
    img[m & (bayer(H, W) < 9)] = 11


# ---------------------------------------------------------------- pixel effects (drawn on 2s)
def jag(dr, c, r, col, rng, n=14, amt=.35):
    pts = []
    for j in range(n):
        a = 2 * math.pi * j / n + rng.uniform(-.1, .1); rr = r * (1 + amt * (rng.random() - .5) * 2 * (j % 2 + .5))
        pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    dr.polygon(pts, fill=col)


def fx_spark(dr, c, e, z, seed):
    rng = np.random.default_rng(seed); a0 = rng.uniform(0, .4)
    if e == 0:
        dr.rectangle([c[0] - 2 * z, c[1] - 2 * z, c[0] + 2 * z, c[1] + 2 * z], fill=WHITE)
    for j in range(8):
        a = a0 + j * math.pi / 4; L = (1.0 if j % 2 == 0 else .6) * z
        ca, sa = math.cos(a), math.sin(a)
        if e == 0:
            dr.line([(c[0] + 3 * z * ca, c[1] + 3 * z * sa), (c[0] + 10 * L * ca, c[1] + 10 * L * sa)], fill=YEL, width=max(1, int(2 * z)))
        elif e == 1:
            dr.line([(c[0] + 8 * z * ca, c[1] + 8 * z * sa), (c[0] + 15 * L * ca, c[1] + 15 * L * sa)], fill=YEL, width=max(1, int(z)))
        elif e == 2 and j % 2 == 0:
            x, y = c[0] + 18 * z * ca, c[1] + 18 * z * sa; dr.rectangle([x - z, y - z, x + z, y + z], fill=ORA)
        elif e == 3 and j % 4 == 0:
            x, y = c[0] + 21 * z * ca, c[1] + 21 * z * sa + 2; dr.rectangle([x, y, x + z, y + z], fill=FIRE)


def fx_fire(dr, c, e, z, seed, big=False):
    rng = np.random.default_rng(seed)
    if e == 0:
        jag(dr, c, 11 * z, FIRE, rng); jag(dr, c, 8 * z, ORA, rng); jag(dr, c, 5 * z, YEL, rng, 10); disc(dr, c, 2.5 * z, WHITE, False)
    elif e == 1:
        jag(dr, c, 17 * z, FIRE, rng, 18, .45); jag(dr, c, 12 * z, ORA, rng, 16); jag(dr, c, 7 * z, YEL, rng, 12)
        if big: disc(dr, c, 4 * z, WHITE, False)
    elif e in (2, 3):
        k = e - 2
        for j in range(7):                                    # flame tongues breaking off, rising
            a = 2 * math.pi * j / 7 + rng.uniform(-.3, .3); rr = (15 + 6 * k) * z
            p = (c[0] + rr * math.cos(a), c[1] + rr * math.sin(a) - 5 * z * (k + 1))
            jag(dr, p, (6 - 2 * k) * z, FIRE if k else ORA, rng, 8, .5)
            if not k: jag(dr, p, 3 * z, YEL, rng, 6)
        if not k: jag(dr, c, 8 * z, FIRE, rng, 12, .5)


def fx_slash(dr, pts, e, z):
    """Slash arc along the striking limb's last positions (2-3 frames: bright, thinner, breaking up)."""
    n = len(pts)
    if n < 2: return
    lo = [0, n // 3, 2 * n // 3][e]
    for j in range(max(lo, 1), n):
        u = j / (n - 1)
        w = max(1, int(round((8 if e == 0 else 5 if e == 1 else 2) * z * u ** .8)))
        if e == 2 and j % 2: continue
        dr.line([tuple(pts[j - 1]), tuple(pts[j])], fill=YEL if e else WHITE, width=w + (2 if e == 0 else 0))
        if e == 0: dr.line([tuple(pts[j - 1]), tuple(pts[j])], fill=WHITE, width=w)
    if e == 0:
        dr.line([tuple(p) for p in pts[max(1, n // 2):]], fill=WHITE, width=max(1, int(z)))


def fx_dust(dr, c, e, z, d):
    for j, (ox, r) in enumerate(((-9, 3), (0, 4), (9, 3))):
        x = c[0] + (ox + d * 2) * z * (1 + .6 * e); y = c[1] - (2 + 3 * e) * z - (j == 1) * 2 * z
        rr = (r + 1.5 * e) * z
        dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=23 if e < 2 else 17)


# ---------------------------------------------------------------- motion (fight6 pipeline + speed-found contacts)
def refine_contacts(segs, contacts, sh):
    S, X = sh['fight_story_frames'], sh['crossfade']
    for k in contacts:
        A, _ = F6.compose(segs[k['att']], sh['start'][k['att']]['x'], D[k['att']], S, X)
        v = np.r_[0, np.linalg.norm(np.diff(A[:, I[k['eff']]], axis=0), axis=1)] * FPS
        c = k['c']; lo, hi = max(1, c - 12), min(S - 2, c + 8)
        p = lo + int(np.argmax(v[lo:c + 3]))
        f = p
        while f < hi and v[f] > 0.4 * v[p]: f += 1             # full extension: speed falls after the peak
        nc = int(np.clip(f, c - 6, c + 6))
        k.update(c_planned=c, c=nc, peak=p, vpeak=float(v[p]))
        k['seg'].dx_end = nc - 4
        if k.get('rseg'): k['rseg'].start = nc                 # reaction starts on the contact frame
    for who in segs: segs[who].sort(key=lambda g: g.start)


def separate(Wd, contacts, gap=230.0):
    """Stage spacing: where the bodies would overlap, ease both fighters apart (smoothed, so it reads as
    footwork; the foot-plant IK that runs afterwards keeps planted feet locked). Fly-out frames excluded."""
    from scipy.ndimage import maximum_filter1d
    h, o = Wd['hero'], Wd['opp']
    g = np.minimum(o[:, I['thorax'], 0] - h[:, I['thorax'], 0], o[:, 0, 0] - h[:, 0, 0])
    need = np.clip(gap - g, 0, None)
    fin = [k for k in contacts if k['finisher']]
    if fin: need[fin[0]['c'] + 1:] = 0
    need = gaussian_filter1d(maximum_filter1d(need, 13), 5, mode='nearest')
    h[:, :, 0] -= need[:, None] / 2; o[:, :, 0] += need[:, None] / 2
    return need


def build_motion():
    sh, segs, contacts = F6.load_sheet()
    S, X = sh['fight_story_frames'], sh['crossfade']
    fx = {b['n']: b['contact'].get('fx', 'spark') for b in sh['beats'] if b.get('contact')}
    for k in contacts: k['fx'] = fx[k['beat']]
    refine_contacts(segs, contacts, sh)
    F6.solve_stage(segs, contacts, sh)
    Wd, sl = {}, {}
    for w in ('hero', 'opp'):
        Wd[w], sl[w] = F6.compose(segs[w], sh['start'][w]['x'], D[w], S, X)
    separate(Wd, contacts)
    for w in ('hero', 'opp'):
        Wd[w] = F6.plant(Wd[w], sl[w])
    Wd = F6.layer_proc(Wd, contacts)
    times = list(range(0, S, 2))
    for k in contacts:
        j = int(np.argmin([abs(t - k['c']) for t in times])); times[j] = k['c']
    draws = []
    for t in times:
        draws.append(t)
        draws += [t] * sum(k['hitstop'] for k in contacts if k['c'] == t)
    assert len(draws) == sh['fight_drawings'], (len(draws), sh['fight_drawings'])
    for k in contacts:
        k['d'] = draws.index(k['c'])
    return sh, segs, contacts, Wd, draws, sl


# ---------------------------------------------------------------- film
TRD = NDRAW - 144                                             # transition drawings (1.2 s)


class Film:
    def __init__(s):
        s.sh, s.segs, s.contacts, s.Wd, s.draws, s.slide = build_motion()
        s.ND = len(s.draws)
        s.fin = [k for k in s.contacts if k['finisher']][0]
        s.layers = paint_layers(); s.roadl = paint_layers(road=True)
        s.camera(); s.dust_events()

    def pose(s, who, t):
        return s.Wd[who][int(min(max(t, 0), len(s.Wd[who]) - 1))]

    def camera(s):
        N = s.ND; hx = np.zeros(N); ox = np.zeros(N)
        for d, t in enumerate(s.draws):
            hx[d] = proj(s.pose('hero', t))[I['thorax'], 0]; ox[d] = proj(s.pose('opp', t))[I['thorax'], 0]
        fd = s.fin['d']; hs = s.fin['hitstop']
        wo = np.array([.5 if d < fd else .5 - .3 * ease((d - fd - hs) / 4, 'io') for d in range(N)])
        ox = np.where(np.arange(N) > fd + hs, np.minimum(ox, hx + 700), ox)          # don't chase the flying body
        cx = gaussian_filter1d(hx * (1 - wo) + ox * wo, 3, mode='nearest')
        u0 = np.clip(np.arange(N) / 22, 0, 1)
        cx += 70 * (1 - u0 * u0 * (3 - 2 * u0))                 # opening truck-in
        push = np.clip(np.arange(N) / (N - 1), 0, 1)
        sc = S0 * (1 + 0.07 * push)
        for k in s.contacts:                                   # gentle push-ins on the strikes
            if not k['finisher']:
                sc = sc * (1 + 0.05 * k['size'] * np.exp(-((np.arange(N) - k['d'] + 3) / 6) ** 2))
        sc = gaussian_filter1d(sc, 2, mode='nearest')
        gy = np.full(N, float(GY0)) + 10 * push
        # finisher: whip into a close-up on the impact over 3 drawings, hold the hit-stop, snap back out
        t = s.fin['c']; Ph = proj(s.pose('hero', t)); Po = proj(s.pose('opp', t))
        IP = (Ph[I[s.fin['eff']], :2] + proj(np.array([head_c(s.pose('opp', t))]))[0, :2]) / 2
        s.IP = IP
        close = (IP[0], 0.40)
        cams = []
        for d in range(N):
            c = (cx[d], gy[d], sc[d])
            tgt = (close[0], 250 - IP[1] * close[1], close[1])
            if fd - 3 <= d < fd:
                u = ease((d - fd + 3) / 3, 'in'); c = tuple(c[j] + (tgt[j] - c[j]) * u for j in range(3))
            elif fd <= d <= fd + hs:
                u = (d - fd) / max(hs, 1); c = (tgt[0], tgt[1] + 4 * u, tgt[2] * (1 + .03 * u))
            elif fd + hs < d <= fd + hs + 4:
                u = ease((d - fd - hs) / 4, 'snap'); a = cams[fd + hs]
                c = tuple(a[j] + (c[j] - a[j]) * u for j in range(3))
            cams.append(c)
        s.cams, s.push = cams, push

    def dust_events(s):
        ev = []; S = len(s.Wd['hero'])
        for who in ('hero', 'opp'):
            A = s.Wd[who]; last = -99
            for side in 'lr':
                y = A[:, I[side + 'tibia'], 1]
                vy = np.r_[0, np.diff(y)] * FPS
                for f in range(2, S):
                    if y[f - 2] > 75 and y[f] <= 62 and vy[f - 1] < -250 and f - last > 30:
                        ev.append((f, who, side)); last = f
            for sg in s.segs[who]:
                if sg.slide and sg.start < S and sg.start - last > 8:
                    ev.append((int(sg.start) + 2, who, 'l')); last = sg.start
        s.dust = sorted(ev)

    # -------------------------------------------------------------- fight drawing
    def fight(s, d):
        t = s.draws[d]; cx, gy, sc = s.cams[d]; cam = (cx, gy, sc)
        img = np.zeros((H, W), np.uint8)
        draw_world(img, s.layers, cx, gy, s.push[d])
        Ph, Po = s.pose('hero', t), s.pose('opp', t)
        shadow(img, Po, cam); shadow(img, Ph, cam)
        draw_fighter(img, Po, cam, False, -1)
        draw_fighter(img, Ph, cam, True, 1)
        pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
        z = sc / S0
        for k in s.contacts:                                   # slash arcs: 3 frames on 2s from 2 drawings before contact
            e = (d - (k['d'] - 2)) // 2
            if 0 <= e < 3:
                A = s.Wd[k['att']]; f1 = min(t, k['c']); f0 = max(0, k['c'] - 12)
                pts = [to_screen(A[f], cam)[0][I[k['eff']], :2] for f in range(f0, f1 + 1)]
                fx_slash(dr, pts, e, z * (0.7 if k['evade'] else 1.0))
        for k in s.contacts:                                   # sparks / fire on the contact
            if k['evade']: continue
            e = (d - k['d']) // 2; P = to_screen(s.Wd[k['att']][k['c']], cam)[0][I[k['eff']], :2]
            if k['fx'] == 'fire':
                if 0 <= e < 4: fx_fire(dr, P, e, z * k['size'] ** .5, k['beat'], k['finisher'])
            elif 0 <= e < 4:
                fx_spark(dr, P, e, z * k['size'] ** .5, k['beat'])
        for f, who, side in s.dust:                            # dust puffs on landings
            d0 = s.draws.index(min(s.draws, key=lambda x: abs(x - f)))
            e = (d - d0) // 2
            if 0 <= e < 3:
                Pp = to_screen(s.Wd[who][min(f, len(s.Wd[who]) - 1)], cam)[0][I[side + 'tibia']]
                fx_dust(dr, (Pp[0], gy), e, z, D[who])
        return np.array(pil)

    def flash(s, img, kind):
        """Finisher flash: one colour frame then one dark frame; figures as hard silhouettes."""
        t = s.draws[-1]; cam = s.cams[-1]
        m = np.zeros((H, W), bool); tmp = img.copy()
        draw_fighter(tmp, s.pose('hero', t), cam, True, 1, m); draw_fighter(tmp, s.pose('opp', t), cam, False, -1, m)
        out = np.full((H, W), YEL if kind == 0 else INK, np.uint8)
        if kind == 0: out[bayer(H, W) < 3] = WHITE
        out[m] = INK if kind == 0 else YEL
        return out

    # -------------------------------------------------------------- transition
    def tr_hero(s, i):
        rd = mv('ready'); t = (i / FPS) % (2 * rd.dur); t = 2 * rd.dur - t if t > rd.dur else t
        P = sample(rd, t, False).copy(); P[:, [0, 2]] -= P[0, [0, 2]]
        return P

    def face(s, i):
        """Close-up: the hero's face turns into the headlights; two light dots in each eye."""
        img = vgrad(H, W, [0, 1, 2], 0, 300)
        img[330:] = vgrad(H - 330, W, [1, 0], 330, 480, 330)
        k = min(1.0, (i + 2) / 10)
        yy, xx = np.mgrid[0:H, 0:W]
        g = np.clip(1 - np.hypot(xx - 300, (yy - 250) * 1.3) / (150 + 120 * k), 0, 1) * 16 * (0.4 + 0.6 * k)
        img[g > bayer(H, W) + 0.5] = 6; img[g > bayer(H, W) + 8] = 7
        pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
        r = 70 + 1.0 * i; c = np.array([118.0 - 0.5 * i, 236.0])
        dr.polygon([(c[0] - 95, 480), (c[0] - 60, c[1] + r * .95), (c[0] + 70, c[1] + r * .95), (c[0] + 105, 480)], fill=INK)
        dr.polygon([(c[0] - 93, 480), (c[0] - 58, c[1] + r * 1.0), (c[0] + 68, c[1] + r * 1.0), (c[0] + 103, 480)], fill=TEE)
        cap(dr, (c[0] - 4, c[1] + r * .5), (c[0] + 2, c[1] + r * 1.05), r * .42, r * .42, SKIN2)
        disc(dr, c, r, SKIN)
        dr.polygon([(c[0] + r * .93, c[1] - r * .05), (c[0] + r * 1.12, c[1] + r * .2), (c[0] + r * .92, c[1] + r * .3)], fill=SKIN)
        img = np.array(pil)
        head = disk_mask(c, r)
        lit = np.clip((xx - (c[0] - r * .1)) / (r * 1.1), 0, 1) * 16 * k
        img[head & (lit > bayer(H, W))] = 17                    # warm headlight wash on the face
        hair = head & ((xx - (c[0] - r * .62)) ** 2 / (r * 1.0) ** 2 + (yy - (c[1] - r * .62)) ** 2 / (r * .62) ** 2 <= 1)
        img[hair] = HAIR
        img[head & ~disk_mask(c, r - 2) & (xx > c[0] + r * .2) & ~hair] = 7     # rim light
        pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
        dr.ellipse([c[0] - r * .3, c[1] + r * .02, c[0] - r * .1, c[1] + r * .32], fill=SKIN2)       # ear
        shock = i >= 5
        for ex, ew in ((c[0] + r * .2, r * .17), (c[0] + r * .62, r * .12)):
            ey = c[1] + r * .0; eh = ew * (1.0 if shock else .7)
            dr.line([(ex - ew, ey - eh - (5 if shock else 3)), (ex + ew, ey - eh - (7 if shock else 2))], fill=HAIR, width=3)
            dr.ellipse([ex - ew, ey - eh, ex + ew, ey + eh], fill=INK)
            dr.ellipse([ex - ew + 1, ey - eh + 1, ex + ew - 1, ey + eh - 1], fill=TEE)
            pr = ew * .55
            dr.ellipse([ex + ew * .25 - pr, ey - pr, ex + ew * .25 + pr, ey + pr], fill=INK)
            for dx in (-0.3, 0.45):                            # headlight reflections (two lamps)
                px, py = ex + ew * .25 + dx * pr, ey - pr * .35
                dr.rectangle([px - 1, py - 1, px + (1 if k > .6 else 0), py + (1 if k > .6 else 0)], fill=WHITE)
            dr.point([(ex + ew * .25, ey + pr * .3)], fill=7)
        mx, my = c[0] + r * .52, c[1] + r * .52
        if shock: dr.ellipse([mx - 4, my - 3, mx + 4, my + 5], fill=INK)
        else: dr.line([(mx - 6, my), (mx + 5, my - 1)], fill=INK, width=2)
        return np.array(pil)

    def car_x(s, i):
        """World x of the car's front bumper; enters at speed, cartoon-brakes to a stop beside the hero."""
        v, i0, i1, stop = 2600 / FPS, 40, 62, 240.0
        brake = v * (i1 - i0) / 2
        if i <= i0: return stop + brake + v * (i0 - i)
        if i <= i1: u = (i - i0) / (i1 - i0); return stop + brake * (1 - u) ** 2
        return stop

    def car_pitch(s, i):
        if i < 40: return 0.0
        if i <= 62: return math.radians(7) * ease((i - 40) / 6, 'out')
        t = (i - 62) / FPS
        return math.radians(7) * math.exp(-t * 9) * math.cos(t * 26)

    def road(s, i, cx, cam_s, gy, beam=True):
        img = np.zeros((H, W), np.uint8)
        draw_world(img, s.roadl, cx, gy, 0)
        cam = (cx, gy, cam_s)
        X = lambda wx: (wx - cx) * cam_s + W / 2
        x0 = s.car_x(i); p = s.car_pitch(i)
        if i > 40:                                             # skid marks
            a, b = X(s.car_x(40)), X(x0)
            for off in (160, 640):
                img[int(gy) + 1:int(gy) + 3, int(max(0, b + off * cam_s)):int(max(0, min(W, a + off * cam_s)))] = INK
        Ph = s.tr_hero(i)
        shadow(img, Ph, cam)
        m = np.zeros((H, W), bool)
        draw_fighter(img, Ph, cam, True, 1, m)
        dist = max(0.0, 1 - (x0 - 240) / 1800)
        if beam:                                               # headlight cone, dithered, toward the hero
            yy, xx = np.mgrid[0:H, 0:W]
            hx, hy = X(x0 + 30), gy - 180 * cam_s - 120 * math.sin(p) * cam_s
            dxp = hx - xx; spread = np.abs(yy - hy) < 6 + dxp * .28
            inten = np.clip(1 - dxp / 260, 0, 1) * (dxp > 0) * spread * 9 * (0.5 + 0.5 * dist)
            on = inten > bayer(H, W)
            img[on & (img != INK) & ~m] = np.where(img[on & (img != INK) & ~m] < 8, 6, 7)
            rim = m & ~np.roll(m, -1, 1) & (bayer(H, W) < 16 * dist)                    # headlight rim on the hero
            img[rim] = 7
        s.draw_car(img, x0, p, cam)
        return img

    def draw_car(s, img, x0, p, cam):
        cx, gy, sc = cam
        pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
        c, sn = math.cos(-p), math.sin(-p)

        def T(pts):
            out = []
            for x, y in pts:
                x, y = x - 120, y
                x, y = x * c - y * sn, x * sn + y * c
                out.append(((x0 + 120 + x - cx) * sc + W / 2, y * sc + gy))
            return out
        body = [(30, -95), (10, -150), (40, -215), (190, -240), (300, -365), (590, -370), (700, -245), (790, -230), (800, -150), (780, -95)]
        dr.polygon(T(body), fill=CAR, outline=INK)
        dr.polygon(T([(318, -340), (440, -345), (440, -250), (250, -250)]), fill=23, outline=INK)
        dr.polygon(T([(460, -345), (575, -345), (650, -250), (460, -250)]), fill=23, outline=INK)
        dr.polygon(T([(20, -125), (800, -125), (795, -95), (30, -95)]), fill=12)
        dr.line(T([(60, -205), (690, -235)]), fill=WHITE, width=1)
        hl = T([(36, -180)])[0]; r = 22 * sc
        dr.ellipse([hl[0] - r, hl[1] - r, hl[0] + r, hl[1] + r], fill=WHITE, outline=YEL)
        tl = T([(776, -205), (798, -175)]); dr.rectangle([min(tl[0][0], tl[1][0]), tl[0][1], max(tl[0][0], tl[1][0]), tl[1][1]], fill=FIRE)
        for wx in (x0 + 160, x0 + 640):
            q = ((wx - cx) * sc + W / 2, -70 * sc + gy)
            disc(dr, q, 70 * sc, INK, False); disc(dr, q, 32 * sc, 23, False)
        img[:] = np.array(pil)

    def transition(s, j):
        """j = transition drawing 0..35: face close-up (0-11), whip pan (12-16), brake (17-35)."""
        i = 2 * j
        if j < 12:
            return s.face(j)
        cs, gy = 0.225, 452.0
        rest = (W / 2 - 45) / cs
        if j < 17:                                             # whip pan along the road toward the car
            u = ease((j - 11) / 6, 'out')
            cx = (-1400 + (rest + 1400) * u)
            img = s.road(i, cx, cs, gy, beam=False)
            sm = img.copy(); step = 14 - 2 * (j - 12)          # horizontal pixel smear in the pan direction
            for x in range(W):
                sm[:, x] = img[:, (x // step) * step]
            return sm
        return s.road(i, rest, cs, gy)

    def drawing(s, d):
        return s.fight(d) if d < s.ND else s.transition(min(d - s.ND, TRD - 4))   # last 4 drawings: freeze

    def frame(s, o, cache):
        d = o // 2
        if d not in cache:
            cache.clear(); cache[d] = s.drawing(d)
        img = cache[d]
        if d == s.ND - 1:                                      # finisher flash = the cut (2 output frames)
            img = s.flash(img, o % 2)
        return img


def upscale(idx):
    return PAL[np.repeat(np.repeat(idx, UP, 0), UP, 1)]


# ---------------------------------------------------------------- chiptune sound
SR = sfx.SR


def crush(x, bits=4, hold=4):
    x = np.repeat(x[::hold], hold)[:len(x)]
    q = 2 ** (bits - 1)
    return np.round(np.clip(x, -1, 1) * q) / q


def sq(f, d, duty=.5):
    ph = np.cumsum(np.broadcast_to(f, (int(SR * d),))) / SR
    return np.where(ph % 1 < duty, 1.0, -1.0)


def chip_thump(d=.22):
    t = np.arange(int(SR * d)) / SR
    s = sq(260 * np.exp(-t * 18) + 45, d) * np.exp(-t * 16) * .7
    n = np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t * 60)
    return crush(s + n * .6, 4, 6)


def chip_bass(d=.45, f=55):
    t = np.arange(int(SR * d)) / SR
    ph = np.cumsum(f * (1 + .6 * np.exp(-t * 20))) / SR
    tri = 2 * np.abs(2 * (ph % 1) - 1) - 1
    return crush(tri * np.exp(-t * 6), 5, 2) * 1.1


def chip_whoosh(d=.2, up=True):
    t = np.arange(int(SR * d)) / SR
    hold = (np.linspace(14, 3, len(t)) if up else np.linspace(3, 14, len(t))).astype(int)
    n = np.random.default_rng(int(d * 1000)).standard_normal(len(t)); y = np.zeros(len(t)); k = 0
    while k < len(t):
        y[k:k + hold[k]] = n[k]; k += hold[k]
    return crush(sfx.lp(y, 3) * np.sin(np.pi * t / d) ** 2, 4, 1) * .8


def chip_screech(d=.6):
    t = np.arange(int(SR * d)) / SR
    f = 1700 + 160 * np.sin(2 * np.pi * 23 * t) - 500 * t
    return crush(sq(f, d, .25) * np.minimum(1, t * 30) * np.exp(-t * 2.5), 4, 2) * .45


def audio(F, path):
    n = int(SR * NDRAW * 2 / FPS); mix = np.zeros(n)

    def put(sig, t, g=1.0):
        i = max(0, int(round(t * SR)))
        if i < n: seg = sig[:n - i]; mix[i:i + len(seg)] += seg * g
    tof = lambda d: 2 * d / FPS
    for k in F.contacts:
        dp = F.draws.index(min(F.draws, key=lambda x: abs(x - k['peak'])))
        put(chip_whoosh(.16 if k['size'] < 1 else .22), tof(dp) - .1, .5 + .2 * min(k['size'], 1.5))
        if not k['evade']:
            put(chip_thump(.22 if not k['finisher'] else .35), tof(k['d']), .8 + .3 * k['size'])
            put(chip_bass(.6 if k['finisher'] else .4, 45 if k['finisher'] else 55), tof(k['d']), .6 + .3 * k['size'])
    for f, who, side in F.dust:
        d0 = F.draws.index(min(F.draws, key=lambda x: abs(x - f)))
        put(crush(sfx.lp(np.random.default_rng(f).standard_normal(int(SR * .08)), 8) * np.hanning(int(SR * .08)), 4, 4), tof(d0), .25)
    t0 = tof(F.ND)
    put(sfx.boom(1.0), t0 - 2 / FPS, .8)                                        # flash cut
    put(chip_whoosh(.28, False), t0 + tof(12) - .05, 1.0)                      # whip pan
    put(crush(sq(70 + 40 * np.linspace(0, 1, int(SR * .5)), .5) * np.linspace(0, .4, int(SR * .5)), 4, 8), t0 + tof(10), .5)
    put(chip_screech(.55), t0 + 40 / FPS, .9)                                   # cartoon brake
    put(chip_thump(.18), t0 + 62 / FPS, .5)
    put(F6.record_scratch(), tof(NDRAW - 4) - .02, 1.0)                          # freeze
    fade = np.ones(n); fade[-int(SR * .02):] = np.linspace(1, 0, int(SR * .02)); mix *= fade
    g, ceil = 1.0 / np.abs(mix).max(), 10 ** (-2.0 / 20)
    for _ in range(10):
        y = np.tanh(mix * g / ceil) * ceil
        F6.hook.write_wav(path + '.tmp.wav', y)
        r = subprocess.run(['ffmpeg', '-nostats', '-i', path + '.tmp.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        Il = float(r.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])
        P = float(r.split('True peak:')[1].split('Peak:')[1].split('dBFS')[0])
        if abs(Il + 14) < 0.4 and P <= -1.0: break
        g *= 10 ** ((-14 - Il) / 20)
        if P > -1.0: ceil *= 10 ** ((-1.3 - P) / 20)
    os.remove(path + '.tmp.wav'); F6.hook.write_wav(path, y)
    return Il, P


# ---------------------------------------------------------------- report + main
def report(F):
    print('drawings: fight %d (story %d), transition %d; output frames %d' % (F.ND, len(F.Wd['hero']), TRD, NDRAW * 2))
    for k in F.contacts:
        print('beat %2d %-4s %-11s -> %-4s planned %3d speed-found %3d (peak %3d, %4.0f u/s) out %3d hitstop %d%s' % (
            k['beat'], k['att'], k['seg'].m.name, k['dfn'], k['c_planned'], k['c'], k['peak'], k['vpeak'], 2 * k['d'],
            k['hitstop'], ' EVADE' if k['evade'] else (' -> ' + k['rseg'].m.name if k.get('rseg') else '')))
    hit = set()
    for k in F.contacts: hit.update(range(k['c'] - 6, k['c'] + 8))
    gaps = [(abs(F.Wd['opp'][f][I['thorax'], 0] - F.Wd['hero'][f][I['thorax'], 0]), f) for f in range(len(F.Wd['hero'])) if f not in hit]
    print('min torso gap outside contacts: %.0f (body width ~110) at story %d' % min(gaps))
    sl = []
    for who in ('hero', 'opp'):
        A = F.Wd[who]
        for side in 'lr':
            an = A[:, I[side + 'tibia']]; v = np.linalg.norm(np.diff(an[:, [0, 2]], axis=0), axis=1)
            on = (an[1:, 1] < 50) & (v > 1.5) & ~F.slide[who][1:]
            sl.append(int(on.sum()))
    print('foot-sliding story frames (ankle down, >1.5 u/frame, not a slide move): hero %d/%d opp %d/%d' % tuple(sl))
    fs = [d for d in range(F.ND) if any(abs(d - k['d']) < 1 for k in F.contacts)]
    print('flash output frames:', [2 * F.ND - 2, 2 * F.ND - 1])


def main():
    os.makedirs(OUT, exist_ok=True)
    F = Film(); report(F)
    pal = np.zeros(256, bool)
    if '--drawings' in sys.argv:
        for d in map(int, sys.argv[sys.argv.index('--drawings') + 1].split(',')):
            Image.fromarray(upscale(F.drawing(d))).resize((270 * 2, 480 * 2), Image.NEAREST).save(os.path.join(OUT, 'p6_%03d.png' % d))
        return
    wav = os.path.join(OUT, 'pixel-fight6-sfx.wav')
    Il, P = audio(F, wav); print('audio I=%.1f LUFS TP=%.1f dBTP' % (Il, P))
    mp4 = os.path.join(OUT, 'pixel-fight6.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W * UP, H * UP),
           '-r', str(FPS), '-i', '-', '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow',
           '-crf', '16', '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '256k',
           '-t', '6.000', '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE); cache = {}
    for o in range(NDRAW * 2):
        idx = F.frame(o, cache); pal[np.unique(idx)] = True
        pr.stdin.write(upscale(idx).tobytes())
    pr.stdin.close(); pr.wait()
    print('palette colours used: %d ->' % pal.sum(), mp4)


if __name__ == '__main__':
    main()
