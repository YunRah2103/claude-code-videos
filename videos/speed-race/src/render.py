"""Speed race: could a stickman outrun an F1 car? Vertical 1080x1920 @30fps, 15 s, pixel art.

A side-scrolling road shot: the caped stickman sprints on the left third while a cheetah, a bullet train and an
F1 car overtake him, each with a bigger effect. Reuses the stick-duel fighter/FX, the brake road art, the
new-car-trap pixel font/Grid and sound effects, and the brake explainer's TTS + alignment.
usage: python render.py still OUTDIR t1 t2 ... | python render.py video OUT.mp4 [END [START]] | python render.py scan
"""
import importlib.util, json, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('duel', ROOT / 'videos/stick-duel/src/render.py')
duel = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(duel)
sys.path.insert(0, str(ROOT / 'videos/new-car-trap/src'))
import pix, sfx  # noqa: E402

DUR = 15.0
W, H, FPS, SR = 1080, 1920, 30, sfx.SR
duel.W, duel.H = W, H                        # duel's pixelate / pixel_fx / pixel_glow read these
G = 12                                       # art grid: background, characters and sprites (90 x 160 cells)
FPX = 8                                      # FX grid
VO = ROOT / 'out/speed-race/vo'
LINES = json.load(open(HERE / 'script.json'))
WORDS = json.load(open(HERE / 'words.json'))
LEAD = 0.2                                   # trim the clip's leading silence so the voice starts at 0.0
pix.FONT.update({'Q': ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
                 'Z': ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
                 'J': ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
                 "'": ["1", "1", "0", "0", "0", "0", "0"], ':': ["0", "1", "0", "0", "0", "1", "0"],
                 '/': ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
                 'u': ["0000", "0000", "1001", "1001", "1001", "1011", "0101"],
                 'b': ["1000", "1000", "1110", "1001", "1001", "1001", "1110"]})


def ss(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def lerp(a, b, k): return a + (b - a) * k


def wt(prefix, nth=0):
    """Absolute time a word starts (prefix match on letters/digits, case-insensitive)."""
    hits = [w for w in WORDS[0] if ''.join(c for c in w['w'].lower() if c.isalnum()).startswith(prefix)]
    return hits[nth]['s'] - LEAD


def pop(t, t0, d=0.25):
    u = (t - t0) / d
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    return 1 + 0.25 * math.sin(u * math.pi) * (1 - u) - (1 - u) ** 3


piece = duel.piece

# ---------------------------------------------------------------- word anchors (all times derive from these)
T_SPR, T_45 = wt('sprinter'), wt('45')
T_CH, T_DBL = wt('cheetah'), wt('double')
T_BUL, T_300 = wt('bullet'), wt('300')
T_F1, T_CAN, T_350 = wt('f1', 1), wt('can'), wt('350')
T_YOU, T_LOSE = wt('you', 1), wt('lose')
T_WHO, T_RACE = wt('who'), wt('race')
END_VO = WORDS[0][-1]['e'] - LEAD
assert END_VO + 1.0 <= DUR, END_VO
T_CPASS = wt('roughly')                      # cheetah's nose passes the runner
T_CB = T_CPASS + 0.3                         # ...and it bursts away
T_TPASS = T_BUL + 0.1                        # train nose passes
T_FPASS = T_CAN                              # F1 blasts past: the big hit
FZ = 0.35                                    # freeze-frame length on "You"
T_LAND = T_FPASS + 1.05
T_POLL = END_VO + 0.05
HOOK = wt('top') - 0.3                         # cold open ends: rewind to the start of the ladder
LOOP0 = DUR - 0.75                           # last 0.75 s dissolve into frame 0 so the clip loops


def sc(t):
    """Scene clock: holds still for the freeze on "You", then continues."""
    if t < T_YOU: return t
    if t < T_YOU + FZ: return T_YOU
    return t - FZ


def rs(t): return t - FZ if t > T_YOU else t   # a real-time anchor expressed on the scene clock


# ---------------------------------------------------------------- background (art grid 90 x 160, scrolling layers)
TW = 240                                     # layer tile width in cells (art + its mirror: seamless)
SKY0, ART0, TRK0, ROAD0, FG0 = 0, 52, 103, 114, 132
GY = 1500                                    # runner's feet
LANE_FAR, LANE_NEAR = 1452, 1560             # F1 (behind him) and cheetah (in front) wheel/feet lines


def road_art():
    """The brake video's 120x68 road painting (sampled from duel.build_bg on the art grid)."""
    duel.W, duel.H = 1280, 720
    big, _ = duel.build_bg()
    duel.W, duel.H = W, H
    return big[(np.arange(68) * 720 / 68 + 720 / 136).astype(int)][:, (np.arange(120) * 1280 / 120 + 1280 / 240).astype(int)]


def tile(a): return np.concatenate([a, a[:, ::-1]], 1)


def build_layers():
    art = road_art().astype(np.float32)
    rnd = np.random.default_rng(8)
    far = np.zeros((TRK0, TW, 3), np.float32)                       # sky extension + scenery strip
    top, seam = np.array((104, 168, 226), np.float32), art[0, :, :].mean(0)
    for y in range(ART0):
        k = (y / ART0) ** 0.8
        far[y] = lerp(top, seam, k)
        if y % 6 == 3 and y < ART0 - 6: far[y, (np.arange(TW) // 2 + y) % 4 == 0] = lerp(top, seam, min(1, k + 0.12))   # dithered bands
    scen = tile(art[:51])
    far[ART0:ART0 + 51] = scen
    for x in range(TW):                                             # round off the clouds cut by the art's top edge
        if scen[0, x].sum() > 690:
            run = [xx for xx in range(max(0, x - 9), min(TW, x + 10)) if scen[0, xx].sum() > 690]
            r = min(9, len(run) / 2)
            cx = (run[0] + run[-1]) / 2
            hgt = int(max(0, r * math.sqrt(max(0, 1 - ((x - cx) / (r + .5)) ** 2))))
            for k in range(hgt):
                far[ART0 - 1 - k, x] = (243, 244, 242) if k < hgt - 1 and (x - cx) < r * .4 else (224, 225, 228)
    clouds = []                                                     # small high clouds (slow drift)
    for cx, cy, r in [(20, 14, 5), (27, 12, 6), (34, 15, 4), (110, 22, 5), (117, 20, 6), (124, 23, 4), (180, 9, 4), (186, 8, 5), (193, 10, 3)]:
        clouds.append((cx, cy, r))
    trk = np.zeros((ROAD0 - TRK0, TW, 3), np.float32)               # grass bank + railway behind the road
    for y in range(ROAD0 - TRK0):
        for x in range(TW):
            c = (64, 138, 64) if rnd.random() > .15 else (52, 118, 56)
            if y == 0: c = (90, 160, 80)
            if y in (5, 6, 7): c = (128, 122, 116) if rnd.random() > .3 else (108, 104, 100)     # ballast
            if y == 6 and x % 3 == 0: c = (110, 76, 50)                                          # sleepers
            if y == 5: c = (206, 212, 222) if x % 2 else (172, 178, 190)                         # rail
            if y in (9, 10): c = (60, 130, 60) if y == 10 else (90, 160, 80)
            trk[y, x] = c
    road = np.zeros((FG0 - ROAD0, TW, 3), np.float32)
    for y in range(FG0 - ROAD0):
        for x in range(TW):
            c = (74, 76, 86) if rnd.random() > .12 else (66, 68, 78)
            if y in (0, FG0 - ROAD0 - 1): c = (190, 188, 176)
            if y in (8, 9) and (x // 6) % 2 == 0: c = (240, 200, 70)
            road[y, x] = c
    fg = np.zeros((H // G - FG0, TW, 3), np.float32)
    for y in range(H // G - FG0):
        for x in range(TW):
            c = (60, 130, 60) if rnd.random() > .2 else (50, 112, 54)
            if y == 0: c = (90, 160, 80)
            if y > 14: c = (122, 92, 64) if rnd.random() > .25 else (104, 78, 56)                 # dirt shoulder
            if y == 14: c = (84, 140, 64)
            fg[y, x] = c
    for _ in range(60):                                             # tufts and flowers
        x, y = rnd.integers(0, TW), rnd.integers(2, 13)
        fg[y, x] = (36, 92, 48); fg[y - 1, x] = (36, 92, 48)
        if rnd.random() < .4: fg[y - 2, x] = [(246, 170, 200), (255, 230, 120), (250, 250, 240)][rnd.integers(3)]
    for _ in range(40):
        x, y = rnd.integers(0, TW), rnd.integers(16, H // G - FG0)
        fg[y, x] = (148, 120, 90)
    return dict(far=far, clouds=clouds, trk=trk, road=road, fg=fg)


# world scroll (camera tracks the runner): speed profile in scene time, integrated once
V0 = 4.5 * 110 * 2.4                         # leg cycle matches the arm pump (4.5 Hz) at Z = 2.4


def vmul(s):
    return piece(s, [(0, 1), (T_FPASS, 1), (T_FPASS + 0.12, 0.25), (T_LAND, 0.25), (T_LAND + 0.3, 0),
                     (rs(T_WHO) - 0.1, 0), (rs(T_WHO) + 0.45, 1), (99, 1)])


_ST = np.arange(0, DUR + 2, 1 / 600)
_SC = np.concatenate([[0], np.cumsum([V0 * vmul(s) / 600 for s in _ST[:-1]])])


def S(s): return float(np.interp(s, _ST, _SC))
def V(s): return V0 * vmul(s)


def bg_frame(L, s):
    off = S(s)
    canvas = np.zeros((H // G, W // G, 3), np.float32)
    def put(layer, y0, f):
        o = int(round(off * f / G)); idx = (np.arange(W // G) + o) % TW
        canvas[y0:y0 + layer.shape[0]] = layer[:, idx]
    put(L['far'], SKY0, 0.3)
    cl = int(round(off * 0.12 / G))
    for cx, cy, r in L['clouds']:
        x = (cx - cl) % TW
        if x > W // G + 8: continue
        for yy in range(cy - r, cy + r + 1):
            for xx in range(int(x - r * 1.6), int(x + r * 1.6) + 1):
                if 0 <= xx < W // G and ((xx - x) / 1.6) ** 2 + (yy - cy) ** 2 <= r * r:
                    canvas[yy, xx] = (250, 251, 250) if yy < cy else (226, 230, 238)
    put(L['trk'], TRK0, 0.7)
    if s < HOOK or T_FPASS - 0.04 <= s < T_FPASS + 0.4:          # anime speed backdrop: everything but the road burns
        k = np.linspace(0, 1, ROAD0)[:, None, None]
        canvas[:ROAD0] = (1 - k) * np.array((18, 20, 52)) + k * np.array((84, 40, 130))
        rr = np.random.default_rng(int(s * 30))
        for _ in range(26):
            y = rr.integers(40, ROAD0); x = rr.integers(-20, W // G); ln = rr.integers(8, 30)
            canvas[y, max(0, x):max(0, min(W // G, x + ln))] = (255, 210, 90) if rr.random() < .4 else (150, 200, 255) if rr.random() < .5 else (255, 255, 255)
    put(L['road'], ROAD0, 1.0)
    put(L['fg'], FG0, 1.35)
    return np.repeat(np.repeat(canvas, G, 0), G, 1)


# ---------------------------------------------------------------- sprites (pix.Grid style: chunky, dark outline)
def gline(g, x0, y0, x1, y1, c, w=2):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x, y = round(lerp(x0, x1, i / n)), round(lerp(y0, y1, i / n))
        for dx in range(w):
            g.px(x + dx, y, c)


GALLOP = [  # front legs (near, far), rear legs (near, far) foot positions; body arch
    (((37, 14), (35, 16)), ((3, 13), (1, 11)), 0),       # full stretch, airborne
    (((31, 16), (28, 16)), ((6, 15), (4, 14)), 0),       # front feet strike
    (((22, 16), (19, 15)), ((19, 15), (16, 16)), 1),     # gathered, back arched
    (((26, 15), (24, 16)), ((14, 16), (11, 16)), 0)]     # rear feet strike, pushing off


def cheetah(ph):
    g = pix.Grid(40, 18)
    B, D, L, K, HI = '#e8a840', '#b8742a', '#fbe6b4', '#3a2618', '#f8c968'
    (f1, f2), (r1, r2), arch = GALLOP[ph]
    gline(g, 26, 9, *f2, D, 2); gline(g, 11, 9, *r2, D, 2)                     # far legs, shaded
    for x in range(9, 31):                                                     # body: deep chest, tucked waist
        u = (x - 20) / 11
        t_ = 5 - arch + round(1.5 * u * u); b = 10 - (1 if 12 < x < 20 else 0) + (1 if x > 23 else 0)
        g.rect(x, t_, x, b, B); g.px(x, t_, HI); g.rect(x, b - 1, x, b, L)
    g.disc(33, 6 - arch, 2.6, B); g.rect(34, 6 - arch, 37, 8 - arch, B); g.rect(35, 8 - arch, 37, 8 - arch, L)
    g.px(31, 3 - arch, D); g.px(32, 3 - arch, D); g.px(34, 5 - arch, K); g.px(37, 6 - arch, K)
    gline(g, 34, 6 - arch, 33, 8 - arch, K, 1)                                 # tear mark
    gline(g, 28, 9, *f1, B, 2); gline(g, 13, 9, *r1, B, 2)                     # near legs
    for p in (f1, f2, r1, r2): g.px(p[0], p[1], K); g.px(p[0] + 1, p[1], K)    # paws
    tail = [(9, 6), (6, 5 + arch), (3, 5 + 2 * arch), (1, 3 + 3 * arch)]
    for (ax, ay), (bx, by) in zip(tail, tail[1:]): gline(g, ax, ay, bx, by, B)
    g.px(1, 3 + 3 * arch, K); g.px(2, 3 + 3 * arch, K); g.px(4, 5 + 2 * arch, K)
    for sx, sy in [(12, 6), (15, 8), (17, 6), (20, 7), (23, 6), (25, 8), (28, 6), (14, 6), (22, 9), (19, 5), (27, 8), (16, 9)]:
        if g.g[sy - arch][sx] is not None: g.px(sx, sy - arch, K)
    return pix.up(g.image(), G)


def _train_car(g, ox, w, nose=0, mirror=False):
    """One train car on grid g at ox. nose>0 draws a long tapered nose of that length on the leading end."""
    def X(x): return ox + (w - 1 - x if mirror else x)
    for x in range(w):
        tp, bt = 3, 16
        if nose and x >= w - nose:
            u = (x - (w - nose)) / nose
            tp = 3 + round(10 * u ** 1.7); bt = 16 - round(3 * max(0, (u - .75) / .25) ** 2)
        for y in range(tp, bt + 1):
            c = '#eef1f5'
            if y <= tp + 1: c = '#c8ced6'
            if 11 <= y <= 12: c = '#2f6fd0'
            if y >= bt - 1: c = '#969cab'
            g.px(X(x), y, c)
        if not nose or x < w - nose - 2:
            if 6 <= 8 and x % 6 not in (0, 5) and 2 < x < w - 2:
                for y in (6, 7): g.px(X(x), y, '#2c3e66')
        elif x < w - 6:
            for y in (tp + 1, tp + 2): g.px(X(x), y, '#2c3e66')            # windshield on the nose
    if nose: g.px(X(w - 3), 14, '#ffe27a'); g.px(X(w - 4), 14, '#ffe27a')
    for bx in (6, w - 12 - nose // 2):
        g.rect(X(bx) if not mirror else X(bx + 6), 17, (X(bx) if not mirror else X(bx + 6)) + 6, 17, '#30323c')
        g.px((X(bx) if not mirror else X(bx + 6)) + 1, 18, '#30323c'); g.px((X(bx) if not mirror else X(bx + 6)) + 5, 18, '#30323c')


def train():
    lens = [70, 60, 60, 70]
    g = pix.Grid(sum(lens) + 6, 19)
    ox = 0
    for i, ln in enumerate(lens):
        _train_car(g, ox, ln, nose=30 if i in (0, 3) else 0, mirror=(i == 0))
        if i == 1: gline(g, ox + 26, 2, ox + 30, 0, '#30323c', 1); gline(g, ox + 34, 2, ox + 30, 0, '#30323c', 1)   # pantograph
        ox += ln
        if i < 3: g.rect(ox, 6, ox + 1, 14, '#30323c'); ox += 2
    return pix.up(g.image(), G)


def f1car(ph):
    g = pix.Grid(64, 16)
    R, RD, K = '#e23a32', '#9e2026', '#22232a'
    g.rect(0, 0, 3, 8, K); g.rect(0, 0, 7, 2, R); g.rect(0, 2, 7, 2, RD)       # rear wing
    for x in range(6, 58):                                                     # tub + engine cover + nose
        if x < 30: tp = 4 + (x - 6) // 8
        elif x < 40: tp = 7
        else: tp = 8 + (x - 40) // 7
        bt = 11 if x < 46 else 10
        g.rect(x, tp, x, bt, R); g.rect(x, bt, x, bt, RD)
    g.rect(22, 2, 26, 4, R); g.rect(23, 3, 25, 3, K)                          # airbox
    g.disc(32, 5, 2.2, '#f2c94c'); g.rect(32, 5, 34, 5, K)                    # helmet + visor
    gline(g, 28, 3, 38, 6, '#3a3c46', 1)                                       # halo
    g.rect(8, 12, 54, 12, K)                                                   # floor
    g.rect(54, 12, 63, 13, R); g.rect(60, 10, 63, 13, RD)                     # front wing + endplate
    g.rect(10, 8, 26, 8, '#f4f4f4')                                            # plain stripe (no livery)
    for cx, r in ((11, 4.6), (50, 4.0)):
        g.disc(cx, 11, r, K); g.disc(cx, 11, r * .5, '#8a909c'); g.px(cx, 11, '#e2e5ea')
        if ph: g.px(cx, 9, '#5d636e'); g.px(cx, 13, '#5d636e')
        else: g.px(cx - 2, 11, '#5d636e'); g.px(cx + 2, 11, '#5d636e')
    return pix.up(g.image(), G)


# ---------------------------------------------------------------- motion of the racers (scene clock)
Z = 2.4                                        # character scale: fills the vertical frame
RX = 330                                       # runner's screen x (left third)


def runner_keys():
    f = T_FPASS
    k = [(0.0, RX, 0, 'dash', 1), (HOOK - 0.1, RX, 0, 'dash', 1), (HOOK + 0.15, RX, 0, 'run', 1), (T_CH - 0.1, RX, 0, 'run', 1), (T_CH + 0.1, RX + 12, 0, 'dash', 1),
         (T_CB, RX + 12, 0, 'dash', 1), (T_CB + 0.15, RX - 12, 0, 'run', 1), (T_TPASS - 0.05, RX, 0, 'run', 1), (T_TPASS + 0.1, RX - 24, -30, 'knock', 1),
         (T_TPASS + 0.3, RX, 0, 'run', 1),
         (f - 0.18, RX, 0, 'run', 1), (f, RX - 10, 0, 'guardup', 1),
         (f + 0.15, RX + 60, -170, 'knock', 1, -70), (f + 0.4, RX + 140, -300, 'tuck', 1, -330),
         (f + 0.65, RX + 190, -280, 'tuck', 1, -560), (f + 0.88, RX + 200, -130, 'tuck', 1, -680),
         (T_LAND, RX + 190, 0, 'land', 1, -720), (T_LAND + 0.25, RX + 180, 0, 'crouch', 1, -720),
         (T_LAND + 0.55, RX + 170, 0, 'stand', 1, -720), (rs(T_WHO) - 0.15, RX + 160, 0, 'stand', 1, -720),
         (rs(T_WHO) + 0.1, RX + 150, 0, 'crouch', 1, -720), (rs(T_WHO) + 0.45, RX, 0, 'run', 1, -720), (DUR + 1, RX, 0, 'run', 1, -720)]
    return k


RK = runner_keys()
CH_IMG = [cheetah(k) for k in range(4)]
TR_IMG = train()
F1_IMG = f1car(0), f1car(1)
SHOCKS = [(T_TPASS, 900), (T_FPASS, 2600)]


def boost(s):                                  # extra wind on the cape when a shockwave hits
    return sum(a * math.exp(-(s - t0) * 3) for t0, a in SHOCKS if s >= t0)


_fs = duel.fighter_state


def _fighter_state(keys, t):
    r = _fs(keys, t)
    if keys is RK:                             # world coords: the camera scrolls with him, so his legs really step
        x, y, pts, f, vx, rot = r
        return x + S(t), y, pts, f, vx + V(t) + boost(t), rot
    return r


duel.fighter_state = _fighter_state


class Shift:
    """ImageDraw proxy that moves world x back to the screen."""
    def __init__(self, d, dx): self.d, self.dx = d, dx

    def _m(self, xy):
        if xy and isinstance(xy[0], (tuple, list)): return [(p[0] - self.dx, p[1]) for p in xy]
        return [v - self.dx if i % 2 == 0 else v for i, v in enumerate(xy)]

    def line(self, xy, **k): self.d.line(self._m(xy), **k)
    def polygon(self, xy, **k): self.d.polygon(self._m(xy), **k)
    def ellipse(self, xy, **k): self.d.ellipse(self._m(xy), **k)
    def rectangle(self, xy, **k): self.d.rectangle(self._m(xy), **k)


def draw_runner(d, s):
    duel.draw_fighter(Shift(d, S(s)), RK, s, 'cape', Z, GY)


def runner_xy(s):
    x, y = _fs(RK, s)[:2]
    return x, GY - 40 * duel.SCALE * Z + y * Z


def cheetah_x(s):                              # nose x: rushes in, runs neck and neck, then bursts away
    return piece(s, [(T_CH - 0.5, -700), (T_CH - 0.05, RX + 120), (T_CB, RX + 250), (T_CB + 0.45, W + 700)])


def train_x(s):                                # nose screen x (train runs right)
    return piece(s, [(T_TPASS - 0.35, -100), (T_TPASS, RX + 200), (T_TPASS + 0.35, RX + 380), (T_TPASS + 1.3, 3700), (T_TPASS + 3.3, 11700)])


def f1_x(s):                                   # streaks in, slow-motion side by side as it blows him away, then gone
    if s < HOOK: return RX + 330 + 90 * s        # cold open: neck and neck, the car creeping ahead
    if s < T_YOU: return piece(s, [(T_FPASS - 0.3, -900), (T_FPASS, RX + 380), (T_FPASS + 0.35, RX + 520), (T_YOU, 1100)])
    a = s - T_YOU
    return 1100 + 240 * a + 2600 * a * a


# ---------------------------------------------------------------- FX
def hspeedlines(d, s, amt, seed=5):
    if amt <= 0: return
    rr = np.random.default_rng(seed)
    for _ in range(int(40 * amt)):
        y = rr.uniform(700, 1880); ln = rr.uniform(120, 340) * (0.6 + amt * 0.6); sp = rr.uniform(1800, 3200)
        x = (rr.uniform(0, W + 900) - sp * s) % (W + 900) - 450
        d.line([(x, y), (x + ln, y)], fill=(255, 255, 255, 220), width=int(rr.uniform(4, 9)))


def kick_dust(sd, s):
    """Dust kicked up behind his feet, drifting back with the ground."""
    if V(s) < 300: return
    step = 1 / 9
    for k in range(6):
        tk = (math.floor(s / step) - k) * step; a = s - tk
        if a < 0 or a > 0.55 or abs(_fs(RK, tk)[1]) > 3: continue
        x = RX - 40 - V(tk) * a * 0.8 + (k % 2) * 20; y = GY - 12 - 50 * a
        duel.puff(sd, x, y, 16 + 60 * a, (214, 200, 176), 220 * (1 - a / 0.55))


def overtake_fx(fd, gld, sd, s):
    cx = cheetah_x(s)
    if T_CH - 0.6 < s < T_DBL + 0.6:                     # cheetah: dust plume + streak
        for k in range(8):
            a = k * 0.06
            x = cheetah_x(s - a) - 330
            if -200 < x < W + 200: duel.puff(sd, x - a * 400, LANE_NEAR - 20 - 90 * a, 30 + 110 * a, (220, 200, 160), 230 * (1 - a / 0.5))
        duel.streak(fd, gld, cx - 900, cx - 380, LANE_NEAR - 100, 26, (255, 200, 120))
    if T_CB <= s < T_CB + 0.4:                           # the cheetah's burst
        u = (s - T_CB) / 0.4; duel.shock(fd, gld, RX + 260, LANE_NEAR - 120, u, (255, 230, 150), 520)
        duel.dust(sd, RX - 100, RX + 300, LANE_NEAR, u, (220, 200, 160), 5, big=0.8, towers=False)
        duel.speedlines(fd, RX + 200, LANE_NEAR - 200, u, 31)
    tx = train_x(s)
    if T_TPASS - 0.4 < s < T_TPASS + 1.6:                # train: wind streaks along its body
        for k, yy in enumerate((1180, 1240, 1300)):
            duel.streak(fd, gld, tx - 3200 - k * 200, tx - 3200 + 900, yy, 10, (210, 235, 255))
    if T_TPASS <= s < T_TPASS + 0.5:
        u = (s - T_TPASS) / 0.5
        duel.shock(fd, gld, RX + 40, GY - 160, u, (210, 235, 255), 700)
        duel.shock(fd, gld, RX + 40, GY - 160, min(1, u * 1.6), (255, 255, 255), 420)
        duel.particles(fd, gld, RX + 20, GY - 30, 420, u, 18, 11, col=(246, 170, 200))
    fx_ = f1_x(s)
    if s < HOOK:                                         # cold open: pulsing shockwaves, sparks, wind
        u = (s % 0.9) / 0.9
        if u < 0.5: duel.shock(fd, gld, RX + 40, GY - 150, u * 2, (255, 230, 150), 620)
        duel.streak(fd, gld, fx_ - 1400, fx_ - 760, LANE_FAR - 110, 30, (255, 150, 60))
        rr = np.random.default_rng(int(s * 30))
        for _ in range(14):
            x, y = RX - 200 + rr.uniform(-250, 400), LANE_FAR - 6 - rr.uniform(0, 60)
            fd.line([(x, y), (x - rr.uniform(40, 120), y + rr.uniform(-10, 10))], fill=(255, 230, 120, 255), width=6)
        if s < 0.25: duel.speedlines(fd, RX + 60, GY - 300, s / 0.25, 3)
    if (s < HOOK or T_F1 < s < T_YOU) and fx_ > -800:                  # F1: exhaust heat + rooster tail of dust
        for k in range(9):
            a = k * 0.05; x = f1_x(s - a) - 760
            duel.puff(sd, x - a * 300, LANE_FAR - 30 - 120 * a, 40 + 140 * a, (226, 220, 206), 240 * (1 - a / 0.45))
        if s < T_FPASS + 0.3: duel.streak(fd, gld, fx_ - 1900, fx_ - 700, LANE_FAR - 110, 34, (255, 150, 60))
    if T_FPASS <= s < T_FPASS + 0.75:                    # the biggest shockwave
        u = (s - T_FPASS) / 0.75
        for r, col in ((1500, (255, 255, 255)), (1000, (255, 200, 70)), (620, (255, 130, 40))):
            duel.shock(fd, gld, RX + 60, GY - 150, min(1, u * 1500 / r), col, r)
        duel.speedlines(fd, RX + 60, GY - 300, min(1, u * 1.6), 77)
        duel.particles(fd, gld, RX + 60, GY - 40, 700, u, 30, 9, col=(255, 230, 120))
    if T_FPASS <= s < T_FPASS + 0.9:                     # sparks scraped off the car's floor
        a = s - T_FPASS; rr = np.random.default_rng(42)
        for _ in range(30):
            vx, vy, life = rr.uniform(-1600, -300), rr.uniform(-900, -200), rr.uniform(.3, .8)
            if a > life: continue
            x, y = RX + 300 + vx * a, LANE_FAR - 10 + vy * a + 1400 * a * a
            col = (255, 255, 255) if a < life * .3 else ((255, 230, 120) if a < life * .65 else (255, 130, 40))
            fd.line([(x, y), (x - vx * .02, y - (vy + 2800 * a) * .02)], fill=col + (255,), width=6)
            gld.line([(x, y), (x - vx * .02, y - (vy + 2800 * a) * .02)], fill=col, width=14)
    if T_LAND <= s < T_LAND + 0.6:                       # landing: dust ring + rocks
        u = (s - T_LAND) / 0.6; x = runner_xy(T_LAND)[0]
        duel.dust(sd, x - 220, x + 220, GY, u, (214, 200, 176), 3, big=0.7, towers=False)
        duel.shock(fd, gld, x, GY - 10, u, (255, 255, 255), 300)


def soften(img, soft, s):
    """duel's chunky, grainy dust treatment (same as the fight)."""
    if not soft.getbbox(): return img
    sm = np.asarray(soft.filter(ImageFilter.GaussianBlur(4)).resize((W // 8, H // 8), Image.Resampling.BOX)).astype(np.int16)
    sm[..., :3] += np.random.default_rng(int(s * 30)).integers(-12, 13, sm.shape[:2])[..., None]
    sm[..., 3] = np.where(sm[..., 3] > 40, np.minimum(255, sm[..., 3] + 30), sm[..., 3] // 2)
    return Image.alpha_composite(img, Image.fromarray(sm.clip(0, 255).astype(np.uint8)).resize((W, H), Image.Resampling.NEAREST))


def speed_amt(s):
    return piece(s, [(0, .7), (HOOK, .7), (HOOK + 0.3, .45), (T_CH - .5, .45), (T_CPASS, .8), (T_DBL + .4, .5), (T_TPASS, 1), (T_TPASS + 1, .55),
                     (T_FPASS - .3, .7), (T_FPASS, 1.3), (T_LAND, .4), (T_LAND + .3, 0), (rs(T_WHO), 0), (rs(T_WHO) + .5, .45), (99, .45)])


# ---------------------------------------------------------------- scene + camera
def scene(s, L):
    base = Image.fromarray(bg_frame(L, s).clip(0, 255).astype(np.uint8)).convert('RGBA')
    tx = train_x(s)
    if -200 < tx < W + TR_IMG.width + 200:
        base.alpha_composite(TR_IMG, (int(tx - TR_IMG.width) // G * G, (TRK0 + 6) * G - TR_IMG.height))
    fx_ = f1_x(s)
    if -800 < fx_ < W + 800:
        spr = F1_IMG[int((fx_ + S(s)) / 60) % 2]
        base.alpha_composite(spr, (int(fx_ - spr.width) // G * G, LANE_FAR - spr.height))
    fx = Image.new('RGBA', (W, H)); fd = ImageDraw.Draw(fx)
    gl = Image.new('RGB', (W, H)); gld = ImageDraw.Draw(gl)
    soft = Image.new('RGBA', (W, H)); sd = ImageDraw.Draw(soft)
    kick_dust(sd, s); overtake_fx(fd, gld, sd, s)
    base = soften(base, soft, s)
    ghost = Image.new('RGBA', (W, H))
    if abs(_fs(RK, s)[0] - _fs(RK, s - 0.033)[0]) + abs(_fs(RK, s)[1] - _fs(RK, s - 0.033)[1]) > 8:   # smear trail when he's thrown
        gd = ImageDraw.Draw(ghost)
        for dt in (0.06, 0.03): draw_runner(gd, s - dt)
        ga = np.asarray(duel.pixelate(ghost, G)).copy(); ga[..., 3] = (ga[..., 3] * 0.35).astype(np.uint8)
        base = Image.alpha_composite(base, Image.fromarray(ga))
    chars = Image.new('RGBA', (W, H)); draw_runner(ImageDraw.Draw(chars), s)
    cpx = duel.pixelate(chars, G)
    if s < HOOK or T_FPASS - 0.04 <= s < T_FPASS + 0.4:          # light 1-cell rim so he reads on the dark backdrop
        m = np.asarray(cpx)[..., 3] > 0; ring = np.zeros_like(m)
        for dy, dx in ((G, 0), (-G, 0), (0, G), (0, -G)): ring |= np.roll(np.roll(m, dy, 0), dx, 1)
        rim = np.zeros((H, W, 4), np.uint8); rim[ring & ~m] = (250, 250, 246, 255)
        base = Image.alpha_composite(base, Image.fromarray(rim))
    base = Image.alpha_composite(base, cpx)
    cx = cheetah_x(s)
    if -500 < cx < W + 500:
        ph = int(s / 0.06) % 4; spr = CH_IMG[ph]
        base.alpha_composite(spr, (int(cx - spr.width) // G * G, LANE_NEAR - spr.height - (G if ph == 0 else 0)))
    if not T_FPASS <= s < T_FPASS + 2 / FPS: hspeedlines(fd, s, speed_amt(s))
    if T_TPASS < s < T_TPASS + 1.4 or T_FPASS < s < T_YOU: duel.ambient(fd, s * 5, n=14)   # leaves ripped up by the wind
    fxp = duel.pixel_fx(fx, FPX)
    out = Image.alpha_composite(base, fxp).convert('RGB')
    o = np.asarray(out).astype(np.float32) + np.asarray(duel.pixel_glow(gl, FPX)).astype(np.float32) * 0.75
    return o, np.asarray(cpx)[..., 3] > 0, np.asarray(fxp)[..., 3] > 0


def zoom(img, z, cx, cy):
    cx = min(max(cx, W / 2 / z), W - W / 2 / z); cy = min(max(cy, H / 2 / z), H - H / 2 / z)
    return img.transform((W, H), Image.Transform.AFFINE, (1 / z, 0, cx - W / 2 / z, 0, 1 / z, cy - H / 2 / z), Image.Resampling.NEAREST)


BASEZ = 1.5
PUNCH = [(T_CB, 0.06, 10), (T_TPASS, 0.08, 18), (T_FPASS, 0.16, 40), (T_LAND, 0.05, 12)]


def camera(s):
    z, sh = (1.12 + 0.04 * math.exp(-(s % 0.9) * 10), 14.0) if s < HOOK else (1.0, 0.0)   # cold open: tight, shaking
    if T_FPASS - 0.05 <= s < T_FPASS + 0.4: z += 0.1                              # hard cut in for the F1 pass
    for t0, a, amp in PUNCH:
        if s >= t0:
            e = math.exp(-(s - t0) * 9); z += a * e; sh += amp * e
    z += 0.06 * ss((s - (T_FPASS - 0.5)) / 0.5) * (1 - ss((s - T_FPASS) / 0.3))      # push in as the F1 arrives
    cx = 480 + sh * math.sin(s * 91); cy = 1240 + sh * 0.6 * math.cos(s * 77)
    return z * BASEZ, round(cx / G) * G, round(cy / G) * G


# ---------------------------------------------------------------- UI (pixel font, TikTok safe zone)
BOXES = []
SAFE = (0, 0.12 * H, 0.85 * W, 0.62 * H)


def outline(img, k):
    a = np.asarray(img)[..., 3] > 0
    pad = np.pad(a, k); ring = np.zeros_like(pad)
    for dy in (-k, 0, k):
        for dx in (-k, 0, k): ring |= np.roll(np.roll(pad, dy, 0), dx, 1)
    out = Image.new('RGBA', (img.width + 2 * k, img.height + 2 * k))
    o = np.zeros((*ring.shape, 4), np.uint8); o[ring] = (16, 16, 28, 255)
    out = Image.fromarray(o); out.alpha_composite(img, (k, k))
    return out


def text(txt, s, col='#ffffff'): return outline(pix.up(pix.label(txt, col), s), s)


def plain(txt, s, col):
    g = pix.Grid(pix.text_width(txt), 7); g.text(0, 0, txt, col)
    return pix.up(g.image(outline=False), s)


def paste(img, spr, cx, cy, sc=1.0, left=False):
    if sc <= 0: return
    if sc != 1: spr = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.Resampling.NEAREST)
    x = int(cx if left else cx - spr.width / 2); y = int(cy - spr.height / 2)
    img.alpha_composite(spr, (x, y)); BOXES.append((x, y, x + spr.width, y + spr.height))


COUNT = [(T_DBL, 45, 93), (T_300, 93, 320), (T_350, 320, 350)]


def counter(img, t):
    if t >= T_YOU - 0.05: return
    lab = 'YOU' if t < T_SPR else 'TOP SPRINTER' if t < T_CH else 'CHEETAH' if t < T_BUL else 'BULLET TRAIN' if t < T_F1 else 'F1 CAR'
    switch = max([0] + [a for a in (T_SPR, T_CH, T_BUL, T_F1) if a <= t])
    v, pk, tick = 45, 0, None
    for t0, a, b in COUNT:
        if t >= t0: v = round(lerp(a, b, ss((t - t0) / 0.45))); pk = t0
    s = pop(t, pk + 0.45, 0.2) if pk and t < pk + 0.65 else 1
    num = str(v) + ('+' if v == 350 else '')
    col = '#ffd23f' if v < 300 else '#ff5a3c'
    paste(img, text(lab, 6, '#ffffff'), 48, 268, pop(t, switch - 0.01, 0.18) if switch else 1, left=True)
    n = text(num, 16, col)
    if s != 1: n = n.resize((int(n.width * (1 + 0.25 * (s - 1) + 0.0)), int(n.height * (1 + 0.25 * (s - 1)))), Image.Resampling.NEAREST)
    shake = int(6 * math.sin(t * 120)) if pk and pk <= t < pk + 0.45 else 0
    paste(img, n, 40 + shake, 400, left=True)
    paste(img, text('KM/H', 6, '#ffffff'), 40 + n.width + 12, 446, left=True)


BARS = [('YOU', 45, '#f4f6fa', '45'), ('CHEETAH', 93, '#ffa63d', '93'), ('TRAIN', 320, '#5aa0ff', '320'), ('F1', 350, '#ff4040', '350+')]


def bar_chart(img, t):
    t0 = T_LOSE + 0.15
    if not (t0 <= t < T_POLL + 0.1): return
    out = 1 - ss((t - T_POLL + 0.15) / 0.2)
    d = ImageDraw.Draw(img)
    pnl = int(out * 31) * G // 2
    if pnl < G: return
    y0, y1 = 816 - pnl, 816 + pnl                                    # dark panel opens/closes in whole cells
    d.rectangle([12, y0, 906, y1], fill=(16, 16, 28, 210))
    d.rectangle([12, y0, 906, y0 + 5], fill=(250, 250, 240, 255)); d.rectangle([12, y1 - 5, 906, y1], fill=(250, 250, 240, 255))
    if out < 0.99: return
    for k, (lab, v, col, vs) in enumerate(BARS):
        tk = t0 + k * 0.14; y = 690 + k * 84
        if t < tk: continue
        paste(img, text(lab, 5, '#ffffff'), 30, y + 30, pop(t, tk, 0.15), left=True)
        cells = max(1, round(v / 350 * 40)); n = min(cells, int(cells * (t - tk) / 0.3) + 1)
        x0 = 264
        d.rectangle([x0 - 6, y + 6, x0 + n * G + 6, y + 60], fill=(16, 16, 28, 255))
        d.rectangle([x0, y + 12, x0 + n * G, y + 54], fill=col)
        d.rectangle([x0, y + 12, x0 + n * G, y + 21], fill=(255, 255, 255, 255) if k else (200, 204, 214, 255))
        if n == cells: paste(img, text(vs, 5, col), x0 + n * G + 16, y + 33, pop(t, tk + 0.3, 0.15), left=True)


def poll(img, t):
    if t < T_POLL: return
    d = ImageDraw.Draw(img)
    for k, (lab, x) in enumerate((('CHEETAH', 252), ('F1 CAR', 672))):
        s = pop(t, T_POLL + k * 0.12, 0.2)
        if s <= 0: continue
        w, h = int(372 * s) // G * G, int(132 * s) // G * G
        press = k == 0 and T_POLL + 0.9 <= t < T_POLL + 1.05
        dy = 6 if press else 0
        d.rectangle([x - w // 2 - 6, 900 - h // 2 - 6 + dy, x + w // 2 + 6, 900 + h // 2 + 18], fill=(16, 16, 28, 255))
        d.rectangle([x - w // 2, 900 - h // 2 + dy, x + w // 2, 900 + h // 2 + dy], fill=(255, 210, 63, 255) if t >= T_POLL + 0.9 and k == 0 else (250, 250, 244, 255))
        BOXES.append((x - w // 2 - 6, 900 - h // 2 - 6, x + w // 2 + 6, 900 + h // 2 + 18))
        if s >= 1: paste(img, plain(lab, 6, '#1a1a2e'), x, 900 + dy)
    if t >= T_POLL + 0.9: paste(img, outline(pix.up(pix.check(), 6), 6), 252 + 150, 820, pop(t, T_POLL + 0.9, 0.2))


def ui(img, t):
    BOXES.clear()
    if t < T_SPR - 0.3:                                              # the hook is on screen from the first frame
        s = 1 if t < T_SPR - 0.45 else 1 - ss((t - (T_SPR - 0.45)) / 0.15)
        b = 1 + 0.06 * math.exp(-max(0, t - wt('f1')) * 10) if t >= wt('f1') else 1
        jx = (int(t * 15) % 2 * 2 - 1) * 6 if t < HOOK else 0                     # the caption shudders with the car
        paste(img, text('COULD YOU OUTRUN', 9), 459 + jx, 562, s * b)
        paste(img, text('AN F1 CAR?', 12, '#ffd23f'), 459 - jx, 670, s * b)
    counter(img, t)
    if T_YOU <= t < T_WHO:
        sh = int(10 * math.exp(-(t - T_YOU) * 8) * math.sin(t * 90))
        paste(img, text('YOU LOSE', 16, '#ff4848'), 459 + sh, 540, pop(t, T_YOU, 0.2))
    bar_chart(img, t)
    if t >= T_WHO:
        paste(img, text('WHO WOULD', 12), 459, 500, pop(t, T_WHO, 0.2))
        paste(img, text('YOU RACE?', 12, '#ffd23f'), 459, 620, pop(t, wt('you', 2), 0.2))
    poll(img, t)
    paste(img, text('Yub', 4, '#e8ecf4'), 852, 264)


# ---------------------------------------------------------------- frame
def render(t, L):
    s = sc(t)
    o, cmask, fmask = scene(s, L)
    z, cx, cy = camera(s)
    img = zoom(Image.fromarray(o.clip(0, 255).astype(np.uint8)), z, cx, cy)
    out = np.asarray(img).astype(np.float32)
    dk = 0.55 * ss((s - (T_FPASS - 0.3)) / 0.25) * (s < T_FPASS)                  # dark-flash cut into the F1 hit
    if dk: out *= 1 - dk
    if s < HOOK:                                                                    # cold open: constant colour shudder
        k = 4 + int(4 * math.exp(-(s % 0.9) * 8)); out[..., 0] = np.roll(out[..., 0], k, 1); out[..., 2] = np.roll(out[..., 2], -k, 1)
    if HOOK <= t < HOOK + 0.22:                                                     # VHS rewind back to the start
        rr = np.random.default_rng(int(t * 30)); g = out.mean(2, keepdims=True); out = out * 0.4 + g * 0.6
        for y0 in range(0, H, 48):
            out[y0:y0 + 48] = np.roll(out[y0:y0 + 48], int(rr.integers(-90, 90)), 1)
        for _ in range(6):
            y = int(rr.integers(0, H - 12)); out[y:y + 12] = 235
    for hb, amp in ((T_TPASS, 6), (T_FPASS, 14)):                                  # colour-split shudder
        if hb <= s < hb + 0.3:
            k = int(amp * (1 - (s - hb) / 0.3)); out[..., 0] = np.roll(out[..., 0], k, 1); out[..., 2] = np.roll(out[..., 2], -k, 1)
    if T_FPASS <= s < T_FPASS + 1 / FPS:                                          # impact frames (duel style)
        sil = np.asarray(zoom(Image.fromarray(((cmask | fmask) * 255).astype(np.uint8)), z, cx, cy)) > 0
        out = np.repeat(np.where(sil[..., None], np.float32(250), np.float32(12)), 3, axis=2)
    elif T_FPASS + 1 / FPS <= s < T_FPASS + 2 / FPS:
        sil = np.asarray(zoom(Image.fromarray((cmask * 255).astype(np.uint8)), z, cx, cy)) > 0
        fm = np.asarray(zoom(Image.fromarray((fmask * 255).astype(np.uint8)), z, cx, cy)) > 0
        out = np.full_like(out, 244); out[fm] = (230, 40, 40); out[sil] = 12
    elif T_FPASS + 2 / FPS <= s < T_FPASS + 0.18:
        k = 0.6 * (1 - (s - T_FPASS - 2 / FPS) / (0.18 - 2 / FPS)); out = out * (1 - k) + 255 * k
    if T_YOU <= t < T_YOU + FZ + 0.25:                                             # freeze frame: cold, desaturated
        k = 1 if t < T_YOU + FZ else 1 - (t - T_YOU - FZ) / 0.25
        g = out.mean(2, keepdims=True)
        out = out * (1 - 0.75 * k) + (g * np.array([0.8, 0.9, 1.15]) * 0.85) * 0.75 * k
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8)).convert('RGBA')
    if HOOK <= t < HOOK + 0.22:
        d = ImageDraw.Draw(img)
        for x0 in (380, 470):
            d.polygon([(x0, 960), (x0 + 84, 900), (x0 + 84, 1020)], fill=(250, 250, 244, 255), outline=(16, 16, 28, 255), width=8)
    ui(img, t)
    return np.asarray(img.convert('RGB'))


F0 = None


def frame(t, L):
    global F0
    a = render(t, L)
    if t >= LOOP0:                                                                  # loop: dissolve into the opening frame
        if F0 is None: F0 = render(0.0, L).astype(np.float32)
        k = ss((t - LOOP0) / (DUR - 1 / FPS - LOOP0))
        a = (a.astype(np.float32) * (1 - k) + F0 * k).astype(np.uint8)
    return a


# ---------------------------------------------------------------- audio
def add(buf, i, s):
    i = max(0, i); j = min(len(buf), i + len(s))
    if i < len(buf): buf[i:j] += s[:j - i]


def read_vo():
    with wave.open(str(VO / 'line_00.wav')) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; sr = w.getframerate()
    x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    return x[int(LEAD * SR):]


def doppler(d, tc, f0, saw=True, k=6.0):
    """Engine/whine that rises as it approaches and drops as it passes at tc (seconds into the clip)."""
    t = sfx.T(d)
    f = f0 * (1 + 0.28 * np.tanh((tc - t) * k))
    ph = np.cumsum(f) / SR
    tone = (2 * (ph % 1) - 1) if saw else np.sign(np.sin(2 * np.pi * ph))
    amp = 1 / (1 + ((t - tc) * k * 0.9) ** 2)
    wind = sfx.lp(np.random.default_rng(int(f0)).standard_normal(len(t)), 8) * 2
    return sfx.fade((sfx.lp(tone, 4) * 0.6 + wind * 0.5) * amp, 0.02, 0.1)


def chip_whoosh(d=0.3, f0=300, f1=1400):
    t = sfx.T(d); f = f0 * (f1 / f0) ** (t / d)
    return sfx.fade(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.sin(np.pi * t / d) * 0.18)


def scratch(d=0.4):
    t = sfx.T(d)
    f = 500 + 1400 * np.abs(np.sin(2 * np.pi * 4 * t))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + sfx.lp(np.random.default_rng(3).standard_normal(len(t)), 3) * 0.5
    return sfx.fade(s * np.abs(np.sin(2 * np.pi * 4 * t)) ** 0.5 * np.exp(-t * 2)) * 0.9


def horn(d=0.5):
    t = sfx.T(d)
    s = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (330, 415))
    return sfx.fade(sfx.lp(s, 10) * np.minimum(1, t / 0.03) * 0.12, 0.01, 0.08)


def tick():
    return sfx.fade(np.sign(np.sin(2 * np.pi * 1800 * sfx.T(0.02))) * 0.12)


def audio(path):
    n = int(DUR * SR)
    vo = np.zeros(n); add(vo, 0, read_vo())
    mus = duel.music(n)
    speak = np.convolve(np.abs(vo) > 0.02, np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    env = 0.22 * (1 - 0.45 * np.clip(speak * 3, 0, 1))
    mix = mus * env + vo * 1.2
    te = sfx.T(HOOK); fe = 300 + 30 * np.sin(2 * np.pi * 5 * te) + 20 * te                 # cold open: engine scream
    eng = sfx.lp(2 * ((np.cumsum(fe) / SR) % 1) - 1, 3) * 0.5 + sfx.lp(np.random.default_rng(2).standard_normal(len(te)), 6) * 0.6
    eng *= np.minimum(1, (HOOK - te) / 0.12)
    ev = [(0.0, sfx.fade(eng) * .55), (0.0, sfx.boom(0.9) * 1.0), (0.0, duel.clang(0.4) * .3),
          (HOOK, chip_whoosh(0.3, 1600, 200) * 1.2), (HOOK, scratch(0.3) * .7),
          (T_SPR, sfx.pop() * .4),
          (T_CH - 0.7, doppler(1.6, 0.7 + T_CPASS - T_CH, 520, saw=False) * .55), (T_CPASS, sfx.whoosh(0.5, 10) * .8),
          (T_TPASS - 0.6, horn(0.55)), (T_TPASS - 0.9, doppler(2.6, 0.9, 180) * .9), (T_TPASS, sfx.boom(0.7) * .55),
          (T_F1 - 0.1, sfx.vroom(0.9) * .7), (T_FPASS - 0.9, doppler(1.8, 0.9, 420, k=9) * 1.1),
          (T_FPASS, sfx.boom(1.4) * 1.2), (T_FPASS, sfx.crash(0.9) * .8), (T_FPASS, duel.clang(0.5) * .3),
          (T_FPASS + 0.15, sfx.whoosh(0.6, 6) * .8), (T_LAND, sfx.thump(0.3) * .9),
          (T_YOU, scratch(0.45)), (T_YOU + FZ, chip_whoosh(0.4, 1400, 200)),
          (T_WHO, sfx.pop() * .5), (wt('you', 2), sfx.pop() * .5), (T_POLL, sfx.pop() * .5), (T_POLL + 0.12, sfx.pop() * .5),
          (T_POLL + 0.9, sfx.ding(1568, 0.4) * .4), (LOOP0, chip_whoosh(0.6, 200, 1600) * .8)]
    for t0, a, b in COUNT:                                                       # counter roll: ticks then a ding
        for k in range(9): ev.append((t0 + k * 0.05, tick()))
        ev.append((t0 + 0.45, sfx.ding(1175 + 200 * COUNT.index((t0, a, b)), 0.4) * .35))
    for lab_t in (T_CH, T_BUL, T_F1): ev.append((lab_t, sfx.pop() * .35))
    for k in range(4): ev.append((T_LOSE + 0.15 + k * 0.14, sfx.pop() * .4))
    for t0, s in ev: add(mix, int(t0 * SR), s)
    rr = np.random.default_rng(7)                                                 # footfalls while he runs
    for i in range(int(DUR * 9)):
        tt = i / 9; s_ = sc(tt)
        if V(s_) > 400 and abs(_fs(RK, s_)[1]) < 3:
            add(mix, int(tt * SR), sfx.lp(rr.standard_normal(int(SR * .03)), 6) * np.exp(-sfx.T(.03) * 120) * .25)
    mix = np.tanh(mix * 1.6) * 0.9                                         # hotter, denser mix for phone speakers
    pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def main():
    mode = sys.argv[1]
    L = build_layers()
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: Image.fromarray(frame(float(s), L)).save(out / f'f_{s}.png')
        return
    if mode == 'scan':                                                          # frame-logic scan + safe-zone check
        bad = []
        for i in range(int(DUR * FPS)):
            t = i / FPS; s = sc(t)
            for fn in (runner_xy, cheetah_x, train_x, f1_x, camera, speed_amt, V): fn(s)
            img = Image.new('RGBA', (W, H)); ui(img, t)
            for b in BOXES:
                if b[0] < SAFE[0] or b[1] < SAFE[1] or b[2] > SAFE[2] or b[3] > SAFE[3]: bad.append((round(t, 2), b))
        print('anchors', {k: round(v, 2) for k, v in dict(spr=T_SPR, ch=T_CH, cpass=T_CPASS, tpass=T_TPASS, fpass=T_FPASS,
                                                             you=T_YOU, who=T_WHO, poll=T_POLL, end_vo=END_VO).items()})
        print('safe-zone violations:', len(bad), bad[:5])
        return
    dst = Path(sys.argv[2]); dst.parent.mkdir(parents=True, exist_ok=True)
    t_end = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    t_start = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    wav = dst.with_suffix('.wav'); audio(wav)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-ss', str(t_start), '-i', str(wav), '-t', str(t_end - t_start), '-c:v', 'libx264', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-af', 'loudnorm=I=-11:TP=-1.0:LRA=7', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                          '-shortest', str(dst)], stdin=subprocess.PIPE)
    for i in range(int(round(t_start * FPS)), int(round(t_end * FPS))):
        p.stdin.write(frame(i / FPS, L).tobytes())
    p.stdin.close(); sys.exit(p.wait())


if __name__ == '__main__':
    main()
