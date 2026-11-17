"""Mercedes EQE 'Acceleration Increase' skit: dealer lot -> service bay -> dyno room -> finance office -> Mercedes showroom.
Flat-vector style, 1080x1920 @30. Built on bmw-heated-seats/src/render.py: same cast, caption system, camera, whip pans
and mix chain. One background oddity per scene (never mentioned).
Usage: python render.py video VOICE.wav OUT.mp4 | still T OUT.png [VOICE] | meta OUT.json | thumb OUT.png [VOICE]"""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sfx

W, H, FPS, K = 1080, 1920, 30, 2
CX = 459                                   # composition centre (left 85% of width)
WALL_Y, FEET_Y = 940, 1880
HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
DUR = round(WORDS[-1]['e'] + 2.4, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/mercedes-acceleration-subscription/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
def cut(a, b): return (LE[a] + LS[b]) / 2 + .05     # scene cut (whip pan) between two lines
T_HOOK = 3.0                                          # no cards, labels or overlays before this
T_BOUGHT, T_SIXTY0, T_HP0 = word_t(0, 'bought'), word_t(0, 'sixty'), word_t(0, 'horsepower')
T_CLOSE = LS[1] - 0.12                                # in-scene cut: closer on the car as he names the feature
T_AI = word_t(1, 'Acceleration')
T_S2, T_S3, T_S4, T_S5 = cut(1, 2), cut(3, 4), cut(5, 6), cut(7, 8)
T_MOTORS, T_NO, T_SAME, T_UNLOCK = word_t(2, 'motors'), LS[3], word_t(3, 'Same'), word_t(3, 'unlock')
T_HOW, T_60HP = LS[4], LS[5]
T_288, T_348, T_SEC = word_t(5, 'Two-eighty'), word_t(5, 'three-forty'), word_t(5, 'second')
T_60M, T_600, T_TEN, T_GV = LS[6], word_t(7, 'six'), word_t(7, 'ten'), word_t(7, 'Great')
T_RENT, T_OWN, T_STAY = word_t(8, 'renting'), word_t(8, 'own'), word_t(9, 'two-eighty')
BEAT = (LE[9], LS[10])
T_FINAL = LS[10]
T_CARD = LE[10] + 0.3                                 # final caption card (last ~2 s)
SCENES = [0.0, T_S2, T_S3, T_S4, T_S5]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
def BADGE(d, x, y): merc_star(d, x, y, .17, GOLD2)    # dealer name-badge mark
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, d): return clamp((t - a) / d)
def oc(x): return 1 - (1 - x) ** 3
def io(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def ob(x):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def popin(t, t0, d=0.3): return 0.0 if t < t0 else ob(prog(t, t0, d))
def window(t, a, b, fi=0.2, fo=0.25): return min(prog(t, a, fi), 1 - prog(t, b - fo, fo)) if a <= t <= b else 0.0
def mix(c1, c2, k): return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))
def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

@lru_cache(None)
def font(size, path=FONT_B): return ImageFont.truetype(path, int(size))

class D:
    """ImageDraw in 1x design coordinates on a K-times supersampled image."""
    def __init__(self, img, k=K, ox=0, oy=0):
        self.i, self.d, self.k, self.ox, self.oy = img, ImageDraw.Draw(img, 'RGBA'), k, ox, oy
    def p(self, x, y): return ((x - self.ox) * self.k, (y - self.oy) * self.k)
    def box(self, x0, y0, x1, y1): return [*self.p(x0, y0), *self.p(x1, y1)]
    def ell(self, cx, cy, rx, ry, fill, ol=None, w=4):
        self.d.ellipse(self.box(cx - rx, cy - ry, cx + rx, cy + ry), fill=fill, outline=ol, width=int(w * self.k) if ol else 0)
    def rect(self, x0, y0, x1, y1, fill, r=0, ol=None, w=4):
        self.d.rounded_rectangle(self.box(x0, y0, x1, y1), radius=r * self.k, fill=fill, outline=ol, width=int(w * self.k) if ol else 0)
    def poly(self, pts, fill, ol=None, w=4):
        P = [self.p(*q) for q in pts]
        if fill is not None: self.d.polygon(P, fill=fill)
        if ol: self.d.line(P + [P[0]], fill=ol, width=int(w * self.k), joint='curve')
    def line(self, pts, col, w):
        self.d.line([self.p(*q) for q in pts], fill=col, width=int(w * self.k), joint='curve')
        for q in (pts[0], pts[-1]):
            self.ell(q[0], q[1], w / 2, w / 2, col)
    def chord(self, cx, cy, rx, ry, a0, a1, fill):
        self.d.chord(self.box(cx - rx, cy - ry, cx + rx, cy + ry), a0, a1, fill=fill)
    def arc(self, cx, cy, rx, ry, a0, a1, col, w):
        self.d.arc(self.box(cx - rx, cy - ry, cx + rx, cy + ry), a0, a1, fill=col, width=int(w * self.k))
    def text(self, x, y, s, size, fill, anchor='mm', path=FONT_B, stroke=0, sc=None):
        self.d.text(self.p(x, y), s, font=font(size * self.k, path), fill=fill, anchor=anchor,
                    stroke_width=int(stroke * self.k), stroke_fill=sc)

def spline(pts, n=10, closed=True):
    """Catmull-Rom through control points -> smooth polygon."""
    P = list(pts); out = []
    m = len(P)
    for i in (range(m) if closed else range(m - 1)):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        if not closed:
            p0 = P[max(i - 1, 0)]; p3 = P[min(i + 2, m - 1)]
        for j in range(n):
            t = j / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    return out

# ================================================================ emblems (hand-drawn, generic, not logo files)
GOLD, GOLD2, INK = (214, 176, 84), (150, 116, 40), (16, 16, 18)
CHROME, CHROME2 = (214, 220, 228), (120, 128, 140)
VWBLUE, P_RED = (22, 60, 130), (190, 24, 32)
ORANGE = (246, 146, 20)
def shade(d, pts, c0, c1, v0, v1):
    """Fill a polygon with a vertical gradient c0 (design y v0) -> c1 (design y v1)."""
    m = Image.new('L', d.i.size, 0)
    ImageDraw.Draw(m).polygon([d.p(*q) for q in pts], fill=255)
    y0, y1 = d.p(0, v0)[1], d.p(0, v1)[1]
    h, w = d.i.size[1], d.i.size[0]
    a = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    g = np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3)).astype(np.uint8)
    d.i.paste(Image.fromarray(g), (0, 0), m)

# outline control points (u along length, v height as a fraction of 0.42 L); one shared wheelbase and stance
# ================================================================ brand marks (simple hand-drawn shapes, not logo files)
def merc_star(d, cx, cy, s=1.0, col=CHROME, ring=True):
    r = 60 * s
    if ring: d.ell(cx, cy, r, r, None, col, max(2, 7 * s))
    for a in (-90, 30, 150):
        ra = math.radians(a); ex, ey = cx + r * .92 * math.cos(ra), cy + r * .92 * math.sin(ra)
        pl, pr = math.radians(a + 90), math.radians(a - 90)
        d.poly([(ex, ey), (cx + 9 * s * math.cos(pl), cy + 9 * s * math.sin(pl)), (cx + 9 * s * math.cos(pr), cy + 9 * s * math.sin(pr))], col)
def toyota_mark(d, cx, cy, s=1.0, col=CHROME, w=None):
    w = w or max(2, 6 * s)
    d.ell(cx, cy, 64 * s, 42 * s, None, col, w)
    d.ell(cx, cy - 12 * s, 40 * s, 18 * s, None, col, w)
    d.ell(cx, cy + 6 * s, 15 * s, 34 * s, None, col, w)
def polestar_mark(d, cx, cy, s=1.0, col=(210, 160, 70)):
    r, n = 52 * s, 13 * s
    d.poly([(cx, cy - r), (cx + n, cy - n), (cx, cy), (cx - n, cy - n)], col)
    d.poly([(cx, cy + r), (cx + n, cy + n), (cx, cy), (cx - n, cy + n)], col)
    d.poly([(cx - r, cy), (cx - n, cy - n), (cx, cy), (cx - n, cy + n)], col)
    d.poly([(cx + r, cy), (cx + n, cy - n), (cx, cy), (cx + n, cy + n)], col)
def wheel(d, wx, wy, r, S, lambo=False):
    d.ell(wx, wy, r, r, (20, 20, 24))
    d.ell(wx, wy, r * .9, r * .9, None, (44, 44, 50), max(2, r * .06))
    d.ell(wx, wy, r * .7, r * .7, (66, 68, 74))                         # brake disc behind the spokes
    d.chord(wx, wy, r * .64, r * .64, 200, 290, S['cal'])               # caliper
    rim = S['rim']
    d.ell(wx, wy, r * .7, r * .7, None, rim, max(3, r * .1))
    n = S['n']
    for a in range(n):
        ra = math.radians(a * 360 / n + 18)
        for off in ((-.1, .1) if S['dbl'] else (0,)):
            d.line([(wx + r * .13 * math.cos(ra + off), wy + r * .13 * math.sin(ra + off)),
                    (wx + r * .66 * math.cos(ra + off * 1.4), wy + r * .66 * math.sin(ra + off * 1.4))], rim, max(2, r * (.09 if S['dbl'] else .07)))
    d.ell(wx, wy, r * .16, r * .16, rim, (90, 94, 102), 2)
    if lambo: shield(d, wx, wy, r * .0018, GOLD, INK)
    else: d.ell(wx, wy, r * .06, r * .06, CHROME)
# ================================================================ cars (side profile, front to the left; colours follow the user's photos)
EQE_CTRL = [(.012, .13), (0.0, .25), (.008, .35), (.05, .42), (.20, .49), (.31, .54), (.50, .73), (.63, .72), (.80, .61),
            (.93, .51), (1.0, .47), (1.0, .28), (.99, .14), (.86, .11), (.5, .12), (.14, .11)]
P2_CTRL = [(.012, .17), (0.0, .30), (.008, .43), (.05, .50), (.21, .56), (.32, .60), (.48, .81), (.66, .80), (.84, .71),
           (.95, .63), (1.0, .59), (1.0, .32), (.99, .17), (.86, .14), (.5, .15), (.14, .14)]
TUNDRA_POLY = [(.004, .22), (0.0, .60), (.02, .655), (.25, .675), (.305, .69), (.385, .955), (.405, .965), (.62, .965),
               (.635, .95), (.645, .68), (1.0, .68), (1.003, .64), (.998, .23), (.94, .20), (.06, .20)]
CARS = {
    'eqe': dict(col=((150, 152, 158), (214, 216, 222), (82, 84, 92)), rim=(40, 42, 48), n=10, dbl=False, cal=(70, 72, 78), r=.21, wu=(.17, .78)),
    'polestar': dict(col=((226, 230, 234), (255, 255, 255), (156, 162, 170)), rim=(44, 46, 52), n=5, dbl=True, cal=(70, 72, 78), r=.24, wu=(.17, .80)),
    'tundra': dict(col=((178, 18, 28), (232, 60, 64), (104, 8, 16)), rim=(24, 24, 28), n=6, dbl=False, cal=(40, 40, 44), r=.25, wu=(.16, .80)),
}

def car(d, x0, ground, L, kind):
    """Mercedes EQE sedan / Polestar 2 fastback / Toyota Tundra pickup."""
    S = CARS[kind]; Hh = L * .42
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    base, hi, lo = S['col']
    d.ell(x0 + L * .5, ground + 4, L * .58, 15, (0, 0, 0, 90))
    if kind == 'tundra':
        body = [P(u, v) for u, v in TUNDRA_POLY]
        shade(d, body, hi, lo, ground - .97 * Hh, ground - .2 * Hh)
        d.poly([P(.645, .68), P(.995, .68), P(.995, .64), P(.65, .64)], lo)                     # bed rail
        d.line([P(.66, .62), P(.99, .62)], (60, 6, 10), 3)
        d.line([P(.07, .52), P(.62, .53)], hi + (200,), 3)                                       # shoulder light
        d.line([P(.645, .66), P(.645, .24)], (60, 6, 10), 4)                                      # cab / bed gap
        d.rect(*P(.97, .60), *P(1.0, .40), (200, 26, 30), r=3)                                   # tall tail lamp
    else:
        body = spline([P(u, v) for u, v in (EQE_CTRL if kind == 'eqe' else P2_CTRL)], 8)
        shade(d, body, hi, lo, ground - .8 * Hh, ground - .15 * Hh)
        d.line(spline([P(.05, .40), P(.30, .45), P(.62, .47), P(.96, .46)], 8, closed=False), hi + (210,), 3)
    sill = (22, 22, 26)
    lowc = sill if kind != 'eqe' else lo
    shade(d, [P(.03, .13 if kind != 'tundra' else .21), P(.97, .13 if kind != 'tundra' else .21), P(.97, .22 if kind != 'tundra' else .30),
              P(.03, .22 if kind != 'tundra' else .30)], (40, 40, 46) if kind != 'eqe' else lo, lowc, ground - .3 * Hh, ground - .1 * Hh)
    r = Hh * S['r']
    for u in S['wu']:
        wx, wy = P(u, 0)[0], ground - r
        d.chord(wx, wy, r * 1.2, r * 1.2, 180, 360, (14, 14, 16))
        d.rect(wx - r * 1.2, wy - 2, wx + r * 1.2, ground - 4, (14, 14, 16))
        if kind == 'eqe': d.arc(wx, wy, r * 1.24, r * 1.24, 190, 350, lo, 6)
        else: d.arc(wx, wy, r * 1.3, r * 1.3, 185, 355, (26, 26, 30), 16 if kind == 'tundra' else 12)   # black arch cladding
    d.poly(body, None, (24, 26, 34), 5)
    if kind == 'eqe':                                     # one-bow cab-forward glasshouse
        gh = spline([P(.31, .545), P(.47, .70), P(.63, .695), P(.80, .585), P(.86, .52), P(.60, .515)], 5)
    elif kind == 'polestar':                              # frameless glass, sloping fastback
        gh = spline([P(.33, .605), P(.48, .78), P(.66, .77), P(.82, .68), P(.86, .62), P(.60, .60)], 5)
    else:                                                 # upright crew cab, two windows
        gh = [P(.315, .70), P(.39, .93), P(.615, .93), P(.625, .70)]
    shade(d, gh, (86, 106, 130), (16, 20, 30), ground - .9 * Hh, ground - .5 * Hh)
    d.poly(gh, None, (20, 22, 28) if kind != 'polestar' else (40, 42, 50), 4)
    pil = {'eqe': (.575, .52, .70), 'polestar': (.585, .60, .78), 'tundra': (.50, .70, .93)}[kind]
    d.poly([P(pil[0] - .012, pil[1]), P(pil[0] + .012, pil[1]), P(pil[0] + .012, pil[2]), P(pil[0] - .012, pil[2])], (20, 20, 24))
    d.poly([P(.40, pil[1] + .03), P(.43, pil[1] + .03), P(.47, pil[2] - .05), P(.44, pil[2] - .05)], (255, 255, 255, 50))
    door = {'eqe': ((.33, .53, .30, .14), (.585, .51, .60, .13)), 'polestar': ((.34, .59, .31, .16), (.59, .59, .61, .15)),
            'tundra': ((.31, .68, .30, .24), (.505, .69, .505, .24))}[kind]
    for a_, b_, c_, e_ in door: d.line([P(a_, b_), P(c_, e_)], lo, 3)
    hu = {'eqe': (.50, .43), 'polestar': (.51, .50), 'tundra': (.45, .60)}[kind]
    d.rect(*P(hu[0], hu[1] + .015), *P(hu[0] + .05, hu[1] - .01), (40, 40, 46) if kind != 'eqe' else hi, r=3)
    my = {'eqe': .55, 'polestar': .61, 'tundra': .71}[kind]
    d.poly(spline([P(.325, my), P(.37, my + .02), P(.37, my + .07), P(.33, my + .07)], 4), (24, 24, 28) if kind != 'eqe' else base, (24, 26, 34), 3)
    if kind == 'eqe':
        d.poly([P(.005, .33), P(.035, .34), P(.035, .25), P(.004, .24)], (14, 14, 18))                 # black panel grille
        d.poly([P(.015, .40), P(.11, .45), P(.13, .43), P(.04, .38)], (236, 242, 250), (24, 26, 34), 3)   # slim lamp
        d.line([P(.03, .395), P(.11, .435)], (150, 210, 255), 3)
        d.poly([P(.935, .50), P(1.0, .475), P(1.0, .455), P(.94, .48)], (200, 24, 30))                # thin tail bar
        merc_star(d, *P(.018, .30), L * .00018, CHROME)
    elif kind == 'polestar':
        d.poly([P(.005, .30), P(.04, .31), P(.04, .22), P(.004, .21)], (24, 24, 28))
        d.poly([P(.02, .46), P(.12, .52), P(.14, .50), P(.05, .44)], (236, 242, 250), (24, 26, 34), 3)
        d.line([P(.06, .475), P(.10, .50)], (255, 255, 255), 3); d.line([P(.08, .47), P(.08, .505)], (255, 255, 255), 3)   # hammer DRL
        d.poly([P(.94, .62), P(1.0, .59), P(1.0, .56), P(.95, .59)], (210, 24, 30))                  # light-bar tail
        polestar_mark(d, *P(.03, .40), L * .00016)
    else:
        g = [P(0.0, .30), P(.035, .30), P(.04, .62), P(.002, .60)]                                     # huge grille
        d.poly(g, (22, 22, 26), CHROME, 5)
        for v in (.36, .42, .48, .54):
            d.line([P(.004, v), P(.036, v + .004)], (70, 74, 80), 3)
        d.poly([P(.03, .60), P(.14, .64), P(.15, .60), P(.04, .57)], (236, 242, 250), (24, 26, 34), 3)
        d.poly([P(.002, .30), P(.08, .30), P(.07, .22), P(.006, .22)], CHROME2)                          # chrome bumper
        toyota_mark(d, *P(.02, .50), L * .00016, CHROME)
        d.rect(*P(.60, .25), *P(.66, .22), (60, 62, 68), r=2)                                           # step
    for u in S['wu']:
        wheel(d, P(u, 0)[0], ground - r, r, S)

@lru_cache(None)
def car_layer(kind, L):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .62) * K), (0, 0, 0, 0))
    car(D(img, ox=-L * .1, oy=-L * .56), 0, 0, L, kind)
    return img
def paste_car(img, kind, x0, ground, L):
    c = car_layer(kind, L)
    img.paste(c, (int((x0 - L * .1) * K), int((ground - L * .56) * K)), c)
SED_CTRL = [(0.0, .20), (0.01, .40), (.07, .47), (.26, .52), (.36, .76), (.62, .78), (.78, .54), (.97, .49), (1.0, .34),
            (.99, .18), (.9, .15), (.1, .15)]
@lru_cache(None)
def road_car(col, L, roof=None):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .7) * K), (0, 0, 0, 0))
    d = D(img, ox=-L * .1, oy=-L * .6)
    Hh = L * .34
    def P(u, v): return (u * L, -v * Hh)
    lo = tuple(int(c * .62) for c in col); hi = tuple(min(255, int(c * 1.25) + 20) for c in col)
    body = spline([P(u, v) for u, v in SED_CTRL], 8)
    shade(d, body, hi, lo, -.78 * Hh, -.15 * Hh)
    d.poly(body, None, (24, 26, 34), 3)
    gl = spline([P(.38, .53), P(.43, .72), P(.6, .74), P(.73, .53)], 4)
    shade(d, gl, (90, 110, 134), (20, 26, 36), -.74 * Hh, -.53 * Hh)
    d.line([P(.56, .53), P(.565, .74)], lo, 4)
    d.poly([P(.0, .38), P(.06, .44), P(.08, .38)], (250, 250, 236))
    d.poly([P(.98, .44), P(1.0, .44), P(1.0, .34), P(.98, .34)], (230, 50, 40))
    r = Hh * .3
    for u in (.2, .8):
        d.ell(u * L, -r, r, r, (22, 22, 26)); d.ell(u * L, -r, r * .55, r * .55, (170, 174, 182))
    return img

def paste_rot(img, layer, cx, cy, rot=0.0, flip=False):
    if flip: layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
    if rot: layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(cx * K - layer.width / 2), int(cy * K - layer.height / 2)), layer)

# ================================================================ background oddities (comment bait, never mentioned)
# 1 lot: a goat on a parked car's roof, chewing the sale bunting.   2 service bay: a penguin gliding by on a mechanic's creeper.
# 3 dyno room: an octopus in a headset typing on the dyno computer with every arm.   4 finance office: a raccoon slowly
# spinning in an office chair.   5 showroom: a giraffe's head poking down through the ceiling tiles, chewing a plant.
CEIL = 84
def goat(d, x, fy, t, s=1.0):
    C1, C2 = (238, 234, 222), (196, 190, 176)
    for lx in (-34, -20, 22, 36):
        d.line([(x + lx * s, fy - 50 * s), (x + lx * s, fy)], C2, 8 * s); d.ell(x + lx * s, fy, 5 * s, 3 * s, (40, 36, 34))
    d.ell(x, fy - 66 * s, 52 * s, 28 * s, C1, OL, 3)
    d.poly([(x + 48 * s, fy - 80 * s), (x + 62 * s, fy - 96 * s), (x + 54 * s, fy - 72 * s)], C1, OL, 2)   # tail
    chew = math.sin(t * 9) * 3 * s
    hx, hy = x - 52 * s, fy - 104 * s + math.sin(t * 1.4) * 2
    d.line([(x - 30 * s, fy - 76 * s), (hx + 6 * s, hy + 10 * s)], OL, 26 * s); d.line([(x - 30 * s, fy - 76 * s), (hx + 6 * s, hy + 10 * s)], C1, 20 * s)
    for side in (-1, 1):
        d.line([(hx + side * 6 * s, hy - 14 * s), (hx + side * 16 * s + 8 * s, hy - 36 * s)], (150, 130, 100), 5 * s)   # horns
    d.ell(hx, hy, 20 * s, 17 * s, C1, OL, 2)
    d.rect(hx - 34 * s, hy - 4 * s, hx - 4 * s, hy + 14 * s + chew, C1, r=7 * s, ol=OL, w=2)
    d.poly([(hx - 26 * s, hy + 14 * s), (hx - 18 * s, hy + 34 * s), (hx - 12 * s, hy + 14 * s)], C2, OL, 2)   # beard
    d.ell(hx + 14 * s, hy - 6 * s, 12 * s, 5 * s, C2, OL, 2)                                               # ear
    if (t % 3.2) > .12: d.ell(hx - 4 * s, hy - 5 * s, 3.5 * s, 3 * s, OL)
    return hx - 34 * s, hy + 6 * s + chew                                                                 # mouth (bunting end)

def creeper_penguin(d, x, fy, t, s=1.0):
    d.rect(x - 60 * s, fy - 22 * s, x + 60 * s, fy - 10 * s, (200, 40, 40), r=5, ol=OL, w=2)              # creeper board
    for wx in (-48, -16, 16, 48): d.ell(x + wx * s, fy - 5 * s, 6 * s, 6 * s, (30, 30, 34))
    lean = math.sin(t * 3) * 3
    by = fy - 22 * s
    d.ell(x + lean, by - 52 * s, 32 * s, 52 * s, (26, 28, 36), OL, 3)
    d.ell(x + lean - 4 * s, by - 46 * s, 22 * s, 40 * s, (248, 248, 246))
    d.ell(x + lean, by - 108 * s, 24 * s, 22 * s, (26, 28, 36), OL, 3)
    d.ell(x + lean - 8 * s, by - 106 * s, 12 * s, 12 * s, (248, 248, 246))
    d.poly([(x + lean - 22 * s, by - 106 * s), (x + lean - 40 * s, by - 100 * s), (x + lean - 22 * s, by - 96 * s)], (246, 160, 30), OL, 1.5)
    if (t % 2.9) > .12: d.ell(x + lean - 12 * s, by - 110 * s, 3.5 * s, 3.5 * s, OL)
    flap = math.sin(t * 10) * 14 * s
    d.line([(x + lean + 26 * s, by - 70 * s), (x + lean + 44 * s, by - 30 * s - flap)], (26, 28, 36), 10 * s)
    d.rect(x + lean + 4 * s, by - 136 * s, x + lean + 30 * s, by - 126 * s, (250, 210, 60), r=3)         # tiny hard hat
    d.chord(x + lean, by - 126 * s, 24 * s, 16 * s, 180, 360, (250, 210, 60))

def octopus(d, x, fy, t, s=1.0):
    P1, P2 = (176, 88, 196), (140, 60, 160)
    d.rect(x - 110 * s, fy - 120 * s, x + 110 * s, fy - 104 * s, (120, 84, 56), ol=OL, w=2)              # desk
    d.rect(x - 100 * s, fy - 104 * s, x - 86 * s, fy, (90, 62, 40)); d.rect(x + 86 * s, fy - 104 * s, x + 100 * s, fy, (90, 62, 40))
    d.rect(x - 60 * s, fy - 230 * s, x + 50 * s, fy - 150 * s, (24, 26, 32), r=6, ol=(90, 94, 104), w=3)  # monitor
    for i in range(4):
        d.line([(x - 50 * s, fy - 216 * s + i * 16 * s), (x - 50 * s + ((t * 90 + i * 37) % 90) * s, fy - 216 * s + i * 16 * s)], (90, 230, 140), 3)
    d.rect(x - 8 * s, fy - 150 * s, x + 4 * s, fy - 122 * s, (60, 64, 70))
    d.rect(x - 70 * s, fy - 128 * s, x + 40 * s, fy - 120 * s, (40, 42, 48), r=2)                         # keyboard
    hx, hy = x + 80 * s, fy - 190 * s + math.sin(t * 1.5) * 4
    for i in range(8):                                                                                    # arms, half typing
        a0 = -2.6 + i * .42
        typing = i < 5
        ex = (x - 60 * s + i * 22 * s) if typing else hx + 70 * s * math.cos(a0 + 1.5 + math.sin(t * 2 + i) * .3)
        ey = (fy - 128 * s - abs(math.sin(t * 14 + i * 1.7)) * 10 * s) if typing else hy + 60 * s + 50 * s * math.sin(a0 + 1.5 + math.sin(t * 2 + i) * .3)
        pts = spline([(hx, hy + 20 * s), ((hx + ex) / 2 + 10 * s * math.sin(t * 3 + i), (hy + ey) / 2 + 20 * s), (ex, ey)], 5, closed=False)
        d.line(pts, OL, 13 * s); d.line(pts, P1, 9 * s)
    d.ell(hx, hy - 10 * s, 40 * s, 46 * s, P1, OL, 3)
    d.ell(hx + 12 * s, hy - 26 * s, 12 * s, 14 * s, P2)
    for side in (-1, 1):
        d.ell(hx + side * 14 * s, hy + 6 * s, 9 * s, 10 * s, (255, 255, 255), OL, 2)
        if (t % 3.6) > .12: d.ell(hx + side * 14 * s - 3 * s, hy + 7 * s, 4 * s, 5 * s, OL)
    d.arc(hx, hy - 12 * s, 44 * s, 46 * s, 200, 340, (30, 30, 34), 5)                                     # headset
    d.ell(hx - 42 * s, hy - 4 * s, 9 * s, 13 * s, (30, 30, 34))
    d.line([(hx - 40 * s, hy + 6 * s), (hx - 26 * s, hy + 28 * s)], (30, 30, 34), 3)

def raccoon_chair(d, x, fy, t, s=1.0):
    spin = (math.floor(t / 4) + io(clamp((t % 4 - 2.8) / 1.2))) % 1   # sits facing out, then one slow spin every 4 s
    face = math.cos(spin * 2 * math.pi)
    d.line([(x, fy - 10 * s), (x, fy - 70 * s)], (40, 40, 44), 8 * s)
    for a in range(5):
        ra = math.radians(a * 72 + spin * 360); ex = x + 46 * s * math.cos(ra)
        d.line([(x, fy - 10 * s), (ex, fy - 6 * s + 4 * s * math.sin(ra))], (40, 40, 44), 6 * s); d.ell(ex, fy - 2 * s, 6 * s, 5 * s, (24, 24, 28))
    bw = 50 * s * (.45 + .55 * abs(face))
    d.rect(x - 56 * s, fy - 92 * s, x + 56 * s, fy - 70 * s, (40, 42, 50), r=8, ol=OL, w=2)              # seat
    G1, G2 = (128, 126, 130), (70, 68, 74)
    if face < 0:                                            # facing away: chair back hides him, tail sticks out
        d.ell(x + 30 * s * math.sin(spin * 6.28), fy - 96 * s, 14 * s, 30 * s, G1, OL, 2)
        d.rect(x - bw, fy - 230 * s, x + bw, fy - 90 * s, (40, 42, 50), r=16, ol=OL, w=3)
        d.ell(x, fy - 236 * s, 22 * s, 14 * s, G1, OL, 2)
        for k_ in range(4): d.line([(x - 12 * s + k_ * 8 * s, fy - 244 * s), (x - 12 * s + k_ * 8 * s, fy - 230 * s)], G2, 3)
        return
    d.rect(x - bw, fy - 230 * s, x + bw, fy - 90 * s, (40, 42, 50), r=16, ol=OL, w=3)
    sx = 18 * s * math.sin(spin * 2 * math.pi)
    d.ell(x + sx, fy - 126 * s, 34 * s, 40 * s, G1, OL, 3)
    d.ell(x + sx, fy - 120 * s, 20 * s, 26 * s, (196, 194, 196))
    hx, hy = x + sx, fy - 186 * s
    for side in (-1, 1): d.poly([(hx + side * 14 * s, hy - 18 * s), (hx + side * 28 * s, hy - 40 * s), (hx + side * 32 * s, hy - 12 * s)], G1, OL, 2)
    d.ell(hx, hy, 34 * s, 28 * s, G1, OL, 3)
    d.ell(hx, hy - 2 * s, 30 * s, 10 * s, (34, 32, 38))                                                     # bandit mask
    for side in (-1, 1):
        if (t % 3.1) > .12: d.ell(hx + side * 12 * s, hy - 2 * s, 4 * s, 4 * s, (255, 255, 255))
    d.ell(hx, hy + 14 * s, 6 * s, 4 * s, OL)
    d.rect(hx - 34 * s, hy + 32 * s, hx - 6 * s, hy + 58 * s, (250, 250, 248), r=4, ol=OL, w=2)             # holding a coffee
    d.ell(hx + 40 * s, fy - 110 * s, 12 * s, 34 * s, G1, OL, 2)
    for k_ in range(3): d.line([(hx + 30 * s, fy - 130 * s + k_ * 18 * s), (hx + 50 * s, fy - 130 * s + k_ * 18 * s)], G2, 5 * s)

def giraffe(d, x, t, s=1.0):
    C1, SP = (240, 196, 92), (176, 112, 46)
    drop = 1 - math.exp(-max(0, t - T_S5) * 1.5)
    top = CEIL - 4
    ny = top + (330 + 40 * math.sin(t * .8)) * s * drop
    d.rect(x - 70 * s, CEIL - 10, x + 70 * s, CEIL + 2, (40, 40, 44))                                     # the lifted tile gap
    d.poly([(x + 70 * s, CEIL - 6), (x + 150 * s, CEIL - 26), (x + 150 * s, CEIL - 12), (x + 70 * s, CEIL + 4)], (228, 228, 230), OL, 2)
    d.line([(x, top), (x - 6 * s, ny - 20 * s)], OL, 40 * s); d.line([(x, top), (x - 6 * s, ny - 20 * s)], C1, 34 * s)
    for k_ in range(int((ny - top) / (34 * s)) + 1):
        d.ell(x - 3 * s + (6 if k_ % 2 else -6) * s, top + 18 * s + k_ * 34 * s, 9 * s, 10 * s, SP)
    hx, hy = x - 14 * s, ny
    for side in (-1, 1):
        d.line([(hx + side * 12 * s, hy - 26 * s), (hx + side * 14 * s, hy - 44 * s)], C1, 6 * s); d.ell(hx + side * 14 * s, hy - 46 * s, 6 * s, 6 * s, SP)
    d.ell(hx, hy - 6 * s, 24 * s, 26 * s, C1, OL, 3)
    chew = math.sin(t * 8) * 3 * s
    d.rect(hx - 50 * s, hy - 6 * s, hx - 6 * s, hy + 22 * s + chew, C1, r=10 * s, ol=OL, w=2)
    d.ell(hx - 40 * s, hy + 4 * s, 3 * s, 2.5 * s, OL)
    if (t % 3.4) > .12: d.ell(hx - 6 * s, hy - 12 * s, 4 * s, 5 * s, OL)
    d.line([(hx - 44 * s, hy + 18 * s + chew), (hx - 60 * s, hy + 34 * s)], (60, 150, 70), 4)               # a leaf from the plant
    d.ell(hx - 62 * s, hy + 38 * s, 10 * s, 6 * s, (70, 170, 80))
# ================================================================ background people
def cast(skin, hair, suit, pants=None, shoe='26262a', shirt='f4f4f6', tie=None, glasses=False, style='part', badge=False):
    sk = hexc(skin); su = hexc(suit)
    return dict(skin=sk, skin2=tuple(int(c * .86) for c in sk), hair=hexc(hair), suit=su, suit2=tuple(int(c * .72) for c in su),
                shirt=hexc(shirt), tie=hexc(tie) if tie else None, pants=hexc(pants or suit), shoe=hexc(shoe),
                glasses=glasses, hairstyle=style, lids=0.0, badge=badge)
NPC = dict(recep=cast('8d5a3b', '111014', '1c1d22', tie='0d4f3a', badge=True),
           walker=cast('f2d0b0', 'b04a2a', '6b4a8a', pants='2a2a30', style='messy'),
           cust1=cast('c58c64', '2b1d16', 'b8452f', pants='30343c'),
           cust2=cast('f0c9a8', 'd9b36a', '2f5d4a', pants='d8d0c0', glasses=True),
           cust3=cast('7a4c34', '1a1a1a', '40a060', pants='1a1a1a', style='messy'),
           cust4=cast('e0b090', '603018', '808890', pants='404050'))

def mk(lp='rest', rp='rest', **kw):
    st = dict(lpose=POSES[lp] if isinstance(lp, str) else lp, rpose=POSES[rp] if isinstance(rp, str) else rp,
              out_lpose=lp in OUTBEND if isinstance(lp, str) else False, out_rpose=rp in OUTBEND if isinstance(rp, str) else False)
    st.update(kw)
    return st

def npc(img, X, FY, s, cfg, st):
    """Draw a cast member at scale s with feet at (X, FY)."""
    person(D(img, k=K * s, ox=-X / s, oy=FEET_Y - FY / s), 0, FEET_Y, cfg, st)

def walkst(t, rate=11, **kw):
    st = mk(**kw); st['walk'] = t * rate; st['dy'] = -abs(math.sin(t * rate)) * 10
    return st

def reception(img, t, phone):
    if phone:
        st = mk('rest', (-46, -128), prop={'rpose': 'phone'}, look=1, brows='up',
                mouth=(.5 + .5 * math.sin(t * 17)) if (t % 3.1) < 1.9 else 0.0, smile=1)
    else:
        jig = math.sin(t * 23) * 6
        st = mk((-40 + jig, 220), (-40 - jig, 220), look=1, eyes='', brows='flat')
    st['blink'] = (t % 4.1) < .12
    npc(img, 96, 1004, .40, NPC['recep'], st)
    d = D(img)
    d.rect(150, 806, 214, 852, (30, 32, 36), r=4, ol=(80, 84, 90), w=2)   # monitor
    d.rect(176, 852, 188, 880, (60, 64, 70))
    d.rect(-10, 878, 222, 892, (150, 112, 74))                            # desk top + front
    d.rect(-10, 892, 210, 990, (96, 68, 46), ol=(60, 40, 26), w=3)
    d.rect(-10, 930, 210, 936, (196, 170, 120))

def couple(img, t, a='cust1', b='cust2'):
    nod = math.sin(t * 2.4) * 3
    st1 = mk('point', 'rest', look=-1, brows='up', smile=1); st1['dy'] = nod; st1['blink'] = (t % 3.3) < .12
    st2 = mk('rest', (-70, -110), out_rpose=True, look=-1, brows='flat'); st2['blink'] = ((t + 1) % 3.6) < .12
    npc(img, 806, 982, .42, NPC[a], st1)
    npc(img, 884, 988, .40, NPC[b], st2)

# ================================================================ sets
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)
def floor_lines(d, col):
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], col, 2)

# ---- scene 1: the dealer lot (outdoors)
BUNT = [(x, 150 + 30 * math.sin(x / 1080 * math.pi)) for x in range(-20, 1120, 60)]
@lru_cache(None)
def bg_lot():
    arr = np.concatenate([grad(600 * K, W * K, (126, 170, 214), (214, 228, 238)), grad((WALL_Y - 600) * K, W * K, (214, 228, 238), (214, 228, 238)),
                          grad((H - WALL_Y) * K, W * K, (88, 90, 96), (132, 134, 140))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for cx_, cy_, r_ in ((150, 260, 60), (220, 250, 80), (300, 268, 56), (760, 210, 50), (830, 196, 70)):
        d.ell(cx_, cy_, r_, r_ * .6, (250, 252, 255))                                  # clouds
    d.rect(-10, 420, W + 10, WALL_Y, (58, 62, 70))                                   # the dealership building
    d.rect(-10, 420, W + 10, 470, (30, 32, 38))
    for x in range(20, W, 120):                                                       # glass front
        d.rect(x, 500, x + 104, WALL_Y - 10, (96, 126, 156), ol=(40, 44, 52), w=3)
        d.poly([(x + 10, 510), (x + 40, 510), (x + 10, 600)], (255, 255, 255, 40))
    merc_star(d, CX - 230, 445, .32, (240, 242, 246))
    d.text(CX + 20, 445, 'MERCEDES-BENZ', 34, (240, 242, 246), path=FONT_X)
    d.rect(0, WALL_Y - 6, W, WALL_Y, (40, 42, 48))
    for x in range(-200, W + 200, 190):                                               # parking bay lines
        d.line([(x, WALL_Y + 20), (x - 160, H)], (226, 226, 220), 5)
    d.line([(-10, 106), (-10, 980)], (90, 94, 100), 8); d.line([(W + 4, 120), (W + 4, 980)], (90, 94, 100), 8)
    return img

def lot_life(img, t):
    d = D(img)
    paste_rot(img, road_car((40, 44, 52), 330), 850, 900)                             # parked car: the goat's stage
    d = D(img)
    mx, my = goat(d, 860, 900 - 330 * .34 * .76 + 4, t, 1.25)
    pts = [(x, y + 6 * math.sin(t * 3 + x * .02)) for x, y in BUNT]
    d.line(pts, (60, 60, 66), 3)
    cols = [(226, 48, 58), (255, 214, 64), (40, 120, 220), (250, 250, 250)]
    for i, (x, y) in enumerate(pts[:-1]):
        sw = 10 * math.sin(t * 4 + i * .9)
        if i == len(pts) - 3: continue                                                # this flag is in the goat's mouth
        d.poly([(x + 6, y), (x + 50, y + 2), (x + 28 + sw, y + 48)], cols[i % 4], OL, 2)
    gx, gy = pts[-3]                                                                   # torn strand down to the goat
    d.line(spline([(gx + 20, gy), (gx + 6, (gy + my) / 2), (mx, my)], 5, closed=False), (60, 60, 66), 3)
    d.poly([(mx - 4, my - 2), (mx - 40, my + 14 + 4 * math.sin(t * 9)), (mx - 10, my + 26)], cols[(len(pts) - 3) % 4], OL, 2)

# ---- scene 2: the service bay
@lru_cache(None)
def bg_garage():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (118, 124, 134), (150, 156, 164)), grad((H - WALL_Y) * K, W * K, (96, 100, 108), (140, 144, 150))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (60, 64, 72))
    for px in (150, 459, 768):
        d.rect(px - 90, CEIL, px + 90, CEIL + 12, (250, 252, 240))
    d.rect(30, 140, 420, WALL_Y, (70, 76, 86), ol=(40, 44, 52), w=4)                 # roller door
    for y in range(160, WALL_Y, 34): d.line([(34, y), (416, y)], (90, 96, 106), 4)
    d.rect(480, 170, 880, 440, (176, 150, 112), ol=(110, 90, 60), w=4)               # pegboard with tools
    for i in range(5):
        x = 520 + i * 74
        d.line([(x, 210), (x + 8, 330)], (60, 64, 72), 10); d.ell(x + 8, 210, 14, 10, None, (60, 64, 72), 6)
    d.rect(520, 360, 640, 420, (200, 40, 40), r=6); d.rect(680, 350, 840, 420, (60, 64, 72), r=6)
    d.rect(760, 560, 900, WALL_Y, (190, 30, 36), r=6, ol=OL, w=3)                     # tool chest
    for y in range(590, WALL_Y - 20, 64): d.rect(774, y, 886, y + 50, (210, 44, 50), r=4); d.rect(800, y + 22, 860, y + 28, (230, 230, 230), r=2)
    d.text(CX, 108, 'SERVICE', 30, (240, 242, 246), path=FONT_X)
    d.rect(0, WALL_Y - 8, W, WALL_Y, (250, 200, 40))
    floor_lines(d, (150, 154, 160))
    for x in range(-100, W, 60): d.line([(x, WALL_Y + 16), (x + 30, WALL_Y + 16)], (250, 200, 40), 6)
    return img

def garage_life(img, t):
    d = D(img)
    creeper_penguin(d, 990 - 55 * (t - T_S2), 1040, t, 1.5)

# ---- scene 3: the dyno room
@lru_cache(None)
def bg_dyno():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (26, 30, 40), (40, 46, 58)), grad((H - WALL_Y) * K, W * K, (46, 48, 56), (78, 80, 88))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (16, 18, 24))
    d.rect(60, 120, 858, 520, (10, 12, 16), r=20)                                     # the big screen
    d.rect(72, 132, 846, 508, (18, 24, 36), r=14)
    merc_star(d, 116, 168, .26, (200, 206, 216))
    d.text(150, 168, 'ACCELERATION INCREASE', 28, (220, 228, 240), anchor='lm', path=FONT_X)
    d.rect(0, WALL_Y - 6, W, WALL_Y, (60, 200, 240))
    for u in (.17, .78):                                                              # roller pits
        x = CX - 290 + 580 * u
        d.rect(x - 90, 880, x + 90, 914, (20, 22, 26), r=8); d.ell(x - 30, 900, 26, 12, (90, 94, 104)); d.ell(x + 30, 900, 26, 12, (90, 94, 104))
    floor_lines(d, (86, 88, 96))
    return img

def gauge(d, t, cx=CX, cy=400, R=180):
    k_ = io(prog(t, T_348 - .1, .5))
    hp = '348' if k_ > .5 else '288'
    for i in range(31):
        a = math.radians(180 + i * 6)
        c = (226, 48, 58) if i > 22 else (210, 216, 228)
        d.line([(cx + R * math.cos(a), cy + R * math.sin(a)), (cx + (R - (24 if i % 5 == 0 else 12)) * math.cos(a), cy + (R - (24 if i % 5 == 0 else 12)) * math.sin(a))], c, 4)
    v = .55 + .25 * k_ if t >= T_288 - .1 else .1 + .45 * io(prog(t, T_S3, .8))
    v += .006 * math.sin(t * 40) * (t >= T_60HP)
    a = math.radians(180 + 180 * v)
    d.line([(cx, cy), (cx + (R - 30) * math.cos(a), cy + (R - 30) * math.sin(a))], (255, 120, 40), 8)
    d.ell(cx, cy, 16, 16, (230, 232, 240))
    if t >= T_288 - .1:
        d.text(cx - 30, cy + 66, hp, 64 * (1 + .25 * max(0, 1 - (t - T_348) * 3) * (t >= T_348)), (255, 214, 64) if hp == '348' else (255, 255, 255))
        d.text(cx + 60, cy + 70, 'HP', 32, (180, 190, 210), path=FONT_X)

def dyno_life(img, t):
    d = D(img)
    gauge(d, t)
    octopus(d, 880, 1004, t, .9)

def wheel_spin(img, t):
    """Motion streaks over the wheels while the car runs on the dyno."""
    if not (T_60HP - .2 <= t < T_S4): return
    d = D(img); r = 580 * .42 * CARS['eqe']['r']
    for u in CARS['eqe']['wu']:
        wx, wy = CX - 290 + 580 * u, 894 - r
        for k_ in range(3):
            a0 = (t * 900 + k_ * 120) % 360
            d.arc(wx, wy, r * .6, r * .6, a0, a0 + 70, (230, 232, 240, 150), 5)

# ---- scene 4: the finance office
@lru_cache(None)
def bg_office():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (222, 214, 198), (236, 230, 218)), grad((H - WALL_Y) * K, W * K, (120, 92, 70), (150, 118, 92))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (236, 232, 224)); d.rect(0, CEIL - 6, W, CEIL, (200, 194, 182))
    d.rect(40, 150, 330, 560, (180, 214, 236), ol=(120, 110, 96), w=8)                # window with blinds
    for y in range(160, 556, 22): d.line([(46, y), (324, y)], (236, 236, 230), 9)
    d.rect(400, 150, 860, 470, (24, 26, 32), r=12)                                    # wall screen
    d.rect(412, 162, 848, 458, (30, 40, 58), r=8)
    merc_star(d, 630, 270, .7, (210, 216, 228))
    d.text(630, 380, 'PAYMENT OPTIONS', 32, (220, 228, 240), path=FONT_X)
    d.rect(150, 700, 640, 730, (140, 100, 64), r=4, ol=OL, w=3)                         # desk
    d.rect(170, 730, 620, WALL_Y, (116, 82, 52), ol=OL, w=3)
    d.rect(200, 640, 290, 700, (240, 240, 236), r=4); d.rect(420, 610, 520, 700, (40, 44, 52), r=6)   # papers + monitor
    d.rect(0, WALL_Y - 8, W, WALL_Y, (150, 120, 90))
    floor_lines(d, (160, 128, 100))
    return img

def office_life(img, t):
    raccoon_chair(D(img), 880, 1010, t, 1.4)

# ---- scene 5: the Mercedes showroom
@lru_cache(None)
def bg_showroom():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (34, 36, 42), (58, 60, 68)), grad((H - WALL_Y) * K, W * K, (196, 198, 202), (230, 231, 233))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-40, W, 170):
        d.rect(x + 8, 110, x + 160, WALL_Y - 40, (44, 46, 54))
        d.line([(x + 8, 110), (x + 8, WALL_Y - 40)], (120, 124, 134, 120), 2)
    d.rect(0, 0, W, CEIL, (236, 236, 238))
    for x in range(0, W, 120): d.line([(x, 0), (x, CEIL)], (200, 200, 204), 2)       # ceiling tiles
    d.rect(0, CEIL - 6, W, CEIL, (190, 190, 194))
    for px in (150, 459):
        d.line([(px, CEIL), (px, CEIL + 40)], (70, 74, 78), 3)
        d.chord(px, CEIL + 62, 46, 28, 180, 360, (52, 52, 56)); d.ell(px, CEIL + 62, 30, 6, (255, 240, 200))
    d.rect(0, WALL_Y - 8, W, WALL_Y, (190, 194, 204))
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    floor_lines(d, (240, 240, 242))
    img = spot(img, CX, 140, 70, 470, 800)
    d = D(img)
    merc_star(d, CX, 236, 1.0, (226, 230, 236))
    d.text(CX, 336, 'MERCEDES-BENZ', 40, (236, 238, 242), path=FONT_X)
    d.ell(CX, 905, 400, 50, (14, 16, 16)); d.ell(CX, 897, 394, 44, (46, 46, 50), (200, 204, 214), 5); d.ell(CX, 897, 340, 34, (60, 60, 64))
    d.rect(790, 840, 910, 1000, (60, 62, 70), r=8)                                     # planter for the giraffe
    for i in range(6): d.ell(820 + i * 16, 820 - (i % 2) * 20, 26, 18, (60, 150, 70), OL, 2)
    return img

def showroom_life(img, t):
    reception(img, t, (t % 6) < 3)
    giraffe(D(img), 870, t, 1.25)
# ================================================================ characters (tesla-locked cast)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('1c1d22'), suit2=hexc('0e0f12'),
             shirt=hexc('f7f7fa'), tie=hexc('111114'), pants=hexc('1c1d22'), shoe=hexc('3a2a22'), glasses=False, hairstyle='part', lids=0.45)
OL = (26, 26, 46)
POSES = {'rest': (10, 323), 'clasp': (-100, 286), 'open': (120, 170), 'point': (235, 70), 'up': (70, -290),
         'head': (-92, -158), 'shrug': (128, 108), 'cross': (-176, 168), 'thanks': (-100, 92), 'raise1': (40, -230),
         'offer': (210, 120), 'chin': (-70, -110), 'hip': (90, 230), 'present': (240, -230), 'phone': (-46, -128), 'reach': (70, -250)}
UA, FA = 168, 158
OUTBEND = {'up', 'head', 'raise1', 'chin', 'reach'}
def ik(S, T, side, out=False):
    dx, dy = T[0] - S[0], T[1] - S[1]
    d_ = max(1e-3, min(math.hypot(dx, dy), UA + FA - 2))
    a = (UA * UA + d_ * d_ - FA * FA) / (2 * d_)
    h = math.sqrt(max(0, UA * UA - (a * a)))
    mx, my = S[0] + dx / d_ * a, S[1] + dy / d_ * a
    px, py = -dy / d_, dx / d_
    if (out and px * side < 0) or (not out and py < 0):
        px, py = -px, -py
    return (mx + px * h, my + py * h), (S[0] + dx / d_ * d_, S[1] + dy / d_ * d_)

def person(d, x, fy, c, st):
    dy, walk = st.get('dy', 0), st.get('walk', None)
    for side in (-1, 1):
        sw = 0 if walk is None else math.sin(walk + (0 if side < 0 else math.pi)) * 26
        lift = 0 if walk is None else max(0, math.sin(walk + (0 if side < 0 else math.pi))) * 14
        hx_, kx = x + side * 40, x + side * 40 + sw
        d.poly([(hx_ - 38, fy - 470 + dy), (hx_ + 38, fy - 470 + dy), (kx + 36, fy - 26 - lift), (kx - 36, fy - 26 - lift)], c['pants'], OL, 4)
        d.ell(kx + side * 12, fy - 16 - lift, 50, 20, c['shoe'], OL, 4)
    top = fy - 800 + dy
    jacket = spline([(x - 40, top - 14), (x - 112, top), (x - 128, top + 50), (x - 116, top + 200), (x - 104, top + 352),
                     (x, top + 362), (x + 104, top + 352), (x + 116, top + 200), (x + 128, top + 50), (x + 112, top), (x + 40, top - 14)], 6)
    d.poly(jacket, c['suit'], OL, 5)
    d.poly([(x - 42, top - 14), (x + 42, top - 14), (x, top + 170)], c['shirt'])
    if c['tie']:
        d.poly([(x - 11, top - 6), (x + 11, top - 6), (x + 8, top + 10), (x - 8, top + 10)], c['tie'])
        d.poly([(x - 8, top + 10), (x + 8, top + 10), (x + 16, top + 150), (x, top + 172), (x - 16, top + 150)], c['tie'])
    for s in (-1, 1):
        d.line([(x + s * 42, top - 14), (x + s * 8, top + 200)], c['suit2'], 6)
        d.poly([(x + s * 42, top - 14), (x + s * 70, top + 70), (x + s * 50, top + 80), (x + s * 14, top + 190)], c['suit2'])
    for by in (230, 290):
        d.ell(x + 2, top + by, 7, 7, c['suit2'])
    if c.get('badge', not c['glasses']):                  # dealer name badge with a tiny wing mark
        d.rect(x + 46, top + 92, x + 100, top + 118, (245, 245, 248), r=4)
        BADGE(d, x + 73, top + 105)
    hx = x + st.get('look', 0) * 0.3
    hy = top - 105
    d.rect(x - 26, top - 40, x + 26, top - 4, c['skin2'])
    for s in (-1, 1):
        d.ell(hx + s * 66, hy + 6, 15, 21, c['skin'], OL, 4)
    d.ell(hx, hy, 68, 84, c['skin'], OL, 5)
    if c['hairstyle'] == 'messy':
        d.chord(hx, hy - 4, 74, 92, 180, 360, c['hair'])
        for px_, py_ in ((-50, -70), (-18, -92), (16, -96), (46, -78)):
            d.poly([(hx + px_ - 24, hy - 50), (hx + px_ + 8, hy + py_ - 14), (hx + px_ + 26, hy - 52)], c['hair'])
        d.poly([(hx - 74, hy - 8), (hx - 66, hy - 50), (hx - 52, hy - 20)], c['hair'])
        d.poly([(hx + 74, hy - 8), (hx + 66, hy - 50), (hx + 52, hy - 20)], c['hair'])
    else:
        d.chord(hx, hy - 6, 72, 90, 180, 360, c['hair'])
        d.poly(spline([(hx - 20, hy - 96), (hx + 60, hy - 90), (hx + 78, hy - 40), (hx + 40, hy - 54), (hx - 10, hy - 60)], 5), c['hair'])
        d.poly([(hx - 72, hy - 6), (hx - 64, hy - 52), (hx - 50, hy - 24)], c['hair'])
    ey, look = hy - 2, st.get('look', 0)
    wide = 1.25 if st.get('eyes') == 'wide' else 1.0
    lids = c['lids'] if st.get('eyes') != 'wide' else 0.0
    lids = max(lids, st.get('tired', 0.0))
    for s in (-1, 1):
        ex = hx + s * 27
        if st.get('blink'):
            d.line([(ex - 12, ey + 2), (ex + 12, ey + 2)], OL, 5)
        else:
            d.ell(ex, ey, 13 * wide, 15 * wide, (255, 255, 255), OL, 3)
            d.ell(ex + look * 4, ey + 2, 6.5, 7.5, OL)
            if lids:
                d.chord(ex, ey, 14 * wide, 16 * wide, 180, 360, c['skin'])
                d.rect(ex - 14, ey - 16 * wide, ex + 14, ey - 16 * wide + 32 * wide * lids * 0.7, c['skin'])
                d.line([(ex - 14, ey - 16 + 32 * lids * 0.7), (ex + 14, ey - 16 + 32 * lids * 0.7)], OL, 4)
    b = st.get('brows', 'flat')
    for s in (-1, 1):
        ex = hx + s * 27
        inner, outer = {'flat': (-26, -26), 'up': (-40, -38), 'angry': (-18, -32), 'worried': (-38, -24)}[b]
        d.line([(ex - s * 14, ey + inner), (ex + s * 14, ey + outer)], c['hair'] if c['hairstyle'] == 'messy' else c['skin2'], 6)
    if c['glasses']:
        for s in (-1, 1):
            d.rect(hx + s * 27 - 21, ey - 19, hx + s * 27 + 21, ey + 19, None, r=8, ol=(150, 158, 170), w=5)
        d.line([(hx - 6, ey - 4), (hx + 6, ey - 4)], (150, 158, 170), 4)
    d.arc(hx, hy + 22, 7, 6, 20, 160, c['skin2'], 4)
    m, my_ = st.get('mouth', 0.0), hy + 46
    if m > 0.08:
        mh = 6 + 20 * m
        d.ell(hx, my_ + mh * 0.3, 15 + 6 * m, mh, (92, 26, 34), OL, 3)
        d.chord(hx, my_ + mh * 0.3 + mh * 0.5, 10 + 4 * m, mh * 0.45, 180, 360, (214, 98, 104))
    else:
        sm = st.get('smile', 0)
        if sm > 0:
            d.arc(hx, my_ - 8, 20, 14, 20, 160, OL, 5)
        elif sm < 0:
            d.arc(hx, my_ + 10, 18, 10, 200, 340, OL, 5)
        else:
            d.line([(hx - 14, my_), (hx + 14, my_)], OL, 5)
    if st.get('sweat'):
        ph = st['sweat']
        for i, (sx_, sy_) in enumerate(((-80, -40), (84, -20))):
            yy = hy + sy_ + (ph * 60 + i * 30) % 50
            d.ell(hx + sx_, yy, 8, 12, (120, 190, 240), (40, 90, 150), 2)
    for side, key in ((-1, 'lpose'), (1, 'rpose')):
        S = (x + side * 108, top + 30)
        ox, oy = st[key]
        T = (S[0] + side * ox, S[1] + oy)
        E, T = ik(S, T, side, st.get('out_' + key, False))
        d.line([S, E, T], OL, 56)
        d.line([S, E, T], c['suit'], 46)
        dx, dy_ = T[0] - E[0], T[1] - E[1]; n = math.hypot(dx, dy_) or 1
        d.ell(T[0] - dx / n * 6, T[1] - dy_ / n * 6, 21, 21, c['shirt'], OL, 3)
        d.ell(T[0] + dx / n * 10, T[1] + dy_ / n * 10, 21, 21, c['skin'], OL, 4)
        prop = st.get('prop', {}).get(key)
        hx2, hy2 = T[0] + dx / n * 10, T[1] + dy_ / n * 10
        if prop == 'phone':
            d.rect(hx2 - 11, hy2 - 44, hx2 + 11, hy2 + 8, (24, 24, 28), r=5, ol=(90, 90, 100), w=3)
        elif prop == 'cup':
            d.rect(hx2 - 15, hy2 - 44, hx2 + 15, hy2 + 4, (246, 246, 244), r=4, ol=OL, w=3)
            d.rect(hx2 - 15, hy2 - 32, hx2 + 15, hy2 - 18, (150, 96, 56))
        elif prop == 'cloth':
            d.ell(hx2, hy2 - 4, 28, 18, (250, 214, 70), OL, 3)
        elif prop == 'fob':                                 # black key fob, buttons facing out
            d.rect(hx2 - 16, hy2 - 58, hx2 + 16, hy2 - 2, (30, 30, 34), r=10, ol=(120, 124, 132), w=3)
            for by_ in (-46, -32): d.ell(hx2, hy2 + by_, 6, 5, (90, 94, 102))
            d.ell(hx2, hy2 - 16, 6, 5, (210, 40, 46))
        elif prop == 'card':                                # black credit card
            d.rect(hx2 - 6, hy2 - 52, hx2 + 70, hy2 - 4, (24, 24, 30), r=6, ol=(200, 170, 90), w=3)
            d.rect(hx2 + 4, hy2 - 40, hx2 + 22, hy2 - 28, (210, 180, 100), r=2)


# ---- performance schedules: (time, left pose, right pose, extras). Buyer escalates per showroom, then deflates.
# ---- performance schedules: (time, left pose, right pose, extras). Buyer outraged throughout, salesman deadpan.
A, WD = dict(brows='angry', eyes='wide'), dict(brows='angry', eyes='wide', sweat=1)
def buyer_sched():
    return [(0.0, 'point', 'up', A),                                    # frame 1: already mid-rant
            (T_SIXTY0 - .1, 'up', 'up', WD),
            (LE[0] + .15, 'rest', 'point', dict(brows='angry')),
            (T_AI + .3, 'head', 'rest', dict(brows='up', eyes='wide', smile=-1)),
            (LE[1] + .3, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # service bay
            (T_S2, 'rest', 'rest', dict(brows='angry')),
            (LS[2] - .05, 'shrug', 'shrug', A),
            (LE[2] + .15, 'rest', 'rest', dict(brows='angry')),
            (T_UNLOCK, 'head', 'head', dict(brows='worried', eyes='wide', sweat=1)),
            # dyno room
            (T_S3, 'rest', 'rest', dict(brows='angry')),
            (LS[4] - .05, 'point', 'rest', A),
            (LE[4] + .15, 'rest', 'rest', dict(brows='angry')),
            (T_348, 'up', 'up', dict(brows='up', eyes='wide')),
            (T_SEC, 'hip', 'hip', dict(brows='angry', smile=-1)),
            # finance office: the peak
            (T_S4, 'rest', 'rest', dict(brows='angry')),
            (LS[6] - .1, 'up', 'up', WD),
            (LE[6] + .15, 'point', 'point', WD),
            (T_TEN, 'head', 'head', WD),
            (T_GV, 'up', 'up', WD),
            (LE[7] + .2, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # showroom: the last outburst, then he stews
            (T_S5, 'rest', 'rest', dict(brows='angry')),
            (LS[8] - .05, 'point', 'up', WD),
            (T_OWN, 'up', 'up', WD),
            (LE[8] + .2, 'cross', 'cross', dict(brows='angry', smile=-1)),
            (T_STAY, 'hip', 'hip', dict(brows='worried', eyes='wide')),
            (T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {1: 'open', 3: 'offer', 5: 'present', 7: 'open', 9: 'offer'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
    s += [(T_348, 'present', 'clasp', {}), (T_GV, 'open', 'open', {}),
          (T_FINAL, 'open', 'clasp', dict(look=0)), (LE[10] + .3, 'clasp', 'clasp', dict(look=0))]
    return sorted(s, key=lambda e: e[0])

BS, SS_ = buyer_sched(), sales_sched()
def pose_at(sched, t, tr=0.2):
    i = max(j for j, e in enumerate(sched) if e[0] <= t)
    cur, prev = sched[i], sched[max(0, i - 1)]
    k = io(prog(t, cur[0], tr))
    lp = [a + (b - a) * k for a, b in zip(POSES[prev[1]], POSES[cur[1]])]
    rp = [a + (b - a) * k for a, b in zip(POSES[prev[2]], POSES[cur[2]])]
    ex = dict(cur[3]) if k > 0.5 else dict(prev[3])
    src = cur if k > 0.5 else prev
    ex['out_lpose'], ex['out_rpose'] = src[1] in OUTBEND, src[2] in OUTBEND
    ex['prop'] = cur[3].get('prop', {}) if k > 0.6 else prev[3].get('prop', {})
    return lp, rp, ex

# ---- lip sync: voice RMS per frame gated by who is talking
MOUTH = None
def load_mouth(voice):
    global MOUTH
    raw = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                                       capture_output=True, check=True).stdout, np.float32)
    n = int(DUR * FPS) + 2; hop = 48000 // FPS
    rms = np.array([np.sqrt((np.mean(raw[i * hop:(i + 1) * hop] ** 2) if i * hop < len(raw) else 0) + 1e-9) for i in range(n)])
    lev = np.clip((20 * np.log10(rms) + 38) / 22, 0, 1)
    M = {'S': np.zeros(n), 'B': np.zeros(n)}
    for w in WORDS:
        a, b = int((w['s'] - .03) * FPS), int((w['e'] + .03) * FPS) + 1
        M[w['spk']][a:b] = lev[a:b]
    f = np.arange(n)
    for k_ in M:
        M[k_] = M[k_] * (0.75 + 0.25 * np.abs(np.sin(f * 1.9)))
    MOUTH = M

def talking(spk, t):
    return any(w['spk'] == spk and w['s'] - .05 <= t <= w['e'] + .05 for w in WORDS)

# ================================================================ world per scene
CAR_X, CAR_G, CAR_L = CX - 290, 894, 580
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    if sc == 0:
        img = bg_lot().copy(); lot_life(img, t); paste_car(img, 'eqe', CAR_X, CAR_G, CAR_L)
    elif sc == 1:
        img = bg_garage().copy(); paste_car(img, 'eqe', CAR_X, CAR_G, CAR_L); garage_life(img, t)
    elif sc == 2:
        img = bg_dyno().copy(); dyno_life(img, t)
        sh = 2 * math.sin(t * 50) if t >= T_60HP - .2 else 0                  # the car hums on the rollers
        paste_car(img, 'eqe', CAR_X + sh, CAR_G, CAR_L); wheel_spin(img, t)
    elif sc == 3:
        img = bg_office().copy(); office_life(img, t)
    else:
        img = bg_showroom().copy(); paste_car(img, 'eqe', CAR_X, CAR_G, CAR_L); showroom_life(img, t)
    d = D(img)
    f = int(round(t * FPS))
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.25), 150, 11   # already in shot, mid-rant
    elif sc == 4:
        walk_k, bx0, dur_w = prog(t, t_in, .8), 40, 11
    else:
        walk_k, bx0, dur_w = prog(t, t_in, .75), -60, 13    # hurrying after the salesman
    bx = bx0 + (270 - bx0) * oc(walk_k)
    for who, x, sched, cfg, spk in (('S', 670, SS_, SALES, 'S'), ('B', bx, BS, BUYER, 'B')):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[spk][min(f, len(MOUTH[spk]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        breathe = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3
        st['dy'] = breathe + (-4 if talking(spk, t) and (f // 4) % 2 else 0)
        if who == 'B' and walk_k < 1:
            st['walk'] = t * dur_w
            st['dy'] -= abs(math.sin(t * dur_w)) * 10
        if st.get('sweat'):
            st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
    return img

def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0 and t < T_CLOSE:
        z = 1.10 - 0.07 * oc(prog(t, 0, 1.6)) + 0.01 * math.sin(t * .5)       # frame 1 already pulling back
        sx = 30 * (1 - oc(prog(t, 0, 1.6)))
        punches = ((T_BOUGHT, .03), (T_SIXTY0, .05), (T_HP0, .04))
    elif sc == 0:                                          # closer on the car
        z = 1.18 + 0.03 * io(prog(t, T_CLOSE, 3))
        sx = -40
        punches = ((T_CLOSE, .05), (T_AI, .03))
    elif sc in (1, 2, 3):
        z = 1.05 + 0.015 * io(prog(t, t0, 5))
        sx = 46 * (1 - oc(prog(t, t0, 1.4)))               # settle after the whip
        punches = {1: ((T_MOTORS, .04), (T_SAME, .03), (T_UNLOCK, .04)), 2: ((T_288, .04), (T_348, .06), (T_SEC, .03)),
                   3: ((T_60M, .07), (T_TEN, .05), (T_GV, .04))}[sc]
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_RENT, .04), (T_OWN, .06), (T_FINAL, .05))
        pk = io(prog(t, T_FINAL - .05, .5))                # salesman turns to camera: push in on him
        z += 0.14 * pk
        sx = 150 * pk
    if sc == 3 and T_60M - .05 <= t < T_60M + .7:          # handheld jolt on the outburst
        k_ = 1 - prog(t, T_60M - .05, .75)
        sx += 14 * k_ * math.sin(t * 61); sy += 10 * k_ * math.sin(t * 47 + 1)
    if sc == 2 and t >= T_60HP - .2: sx += 2 * math.sin(t * 43); sy += 2 * math.sin(t * 37)   # dyno rumble
    if sc == 1: sx += -30 * io(prog(t, t0 + 1.2, 3.5))     # slow drift across the bay
    for tp, amt in punches:
        if tp <= t < tp + .5:
            z += amt * (1 - oc(prog(t, tp, .5)))
    return z, sx, sy
def shoot(t, sc=None):
    """World through the camera, 1x RGBA."""
    wimg = world(t, sc)
    z, sx, sy = camera(t if sc is None else max(t, SCENES[sc]))
    ax, ay = CX * K, 1150 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    return wimg.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')

# ================================================================ overlays
GREEN, TAG, RED = (70, 200, 120), (255, 214, 64), (226, 48, 58)
def put(img, layer, cx, cy, s=1.0, a=1.0, rot=0.0):
    if rot: layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    if s <= 0.02 or a <= 0: return
    if s != 1: layer = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.LANCZOS)
    if a < 1: layer.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
    img.alpha_composite(layer, (int(cx * K - layer.width / 2), int(cy * K - layer.height / 2)))

@lru_cache(None)
def price_tag(txt, sub, col, w=560):
    tag = Image.new('RGBA', (w * K, 190 * K), (0, 0, 0, 0)); td = D(tag)
    td.poly([(40, 24), (w - 30, 24), (w - 6, 95), (w - 30, 166), (40, 166), (10, 95)], col, (40, 30, 10), 6)
    td.ell(46, 95, 12, 12, (40, 30, 10))
    td.text(w / 2 + 10, 66, sub, 28, (40, 34, 26), path=FONT_X)
    size = 64
    while font(size).getlength(txt) > w - 110: size -= 2
    td.text(w / 2 + 10, 122, txt, size, (30, 24, 20))
    return tag

@lru_cache(None)
def photo_card(name, label, bar, fg, w=400):
    ph = Image.open(os.path.join(HERE, '..', 'assets', name)).convert('RGB')
    h = min(int(w * ph.height / ph.width), 300)
    sh = int(ph.width * h / w)                              # centre-crop tall photos to the card ratio
    top = (ph.height - sh) // 2
    ph = ph.crop((0, top, ph.width, top + sh)).resize((w * K, h * K), Image.LANCZOS)
    card = Image.new('RGBA', ((w + 28) * K, (h + 84) * K), (0, 0, 0, 0)); cd = D(card)
    cd.rect(6, 8, w + 26, h + 82, (0, 0, 0, 90), r=10)
    cd.rect(0, 0, w + 20, h + 74, (250, 250, 248), r=10)
    card.paste(ph, (10 * K, 10 * K))
    cd.rect(10, h + 18, w + 10, h + 64, bar, r=8)
    cd.text(w / 2 + 10, h + 42, label, 28, fg)
    return card

@lru_cache(None)
def stamp_img(txt, col, size=96):
    f = font(size * K); w_ = int(f.getlength(txt) / K) + 90
    st_ = Image.new('RGBA', (w_ * K, int(size * 1.9) * K), (0, 0, 0, 0)); sd = D(st_)
    sd.rect(14, 14, w_ - 14, size * 1.9 - 14, None, r=18, ol=col + (255,), w=11)
    sd.text(w_ / 2, size * .95 + 4, txt, size, col + (255,))
    return st_

@lru_cache(None)
def info_card(rows, w=700):
    """Yellow scene card; rows = ((text, size, colour), ...), each row shrunk to fit."""
    sizes = []
    for txt, size, _ in rows:
        while font(size).getlength(txt) > w - 64: size -= 2
        sizes.append(size)
    hh = 36 + sum(int(s * 1.28) for s in sizes)
    c = Image.new('RGBA', ((w + 16) * K, (hh + 16) * K), (0, 0, 0, 0)); d = D(c)
    d.rect(10, 14, w + 14, hh + 14, (0, 0, 0, 90), r=22)
    d.rect(0, 0, w, hh, TAG, r=22, ol=(40, 30, 10), w=6)
    y = 18
    for (txt, _, col), s in zip(rows, sizes):
        y += s * .64; d.text(w / 2, y, txt, s, col); y += s * .64
    return c

def panel(d, x0, y0, x1, y1, a, col=(14, 16, 22)):
    d.rect(x0, y0, x1, y1, col + (int(236 * a),), r=30)

INK2, DRED = (24, 20, 16), (176, 20, 30)
def chip_rows(d, t, rows, y0, a, two_line=False):
    al = int(255 * a)
    for i, (lab, chip, col, tn) in enumerate(rows):
        t_lab = globals()[tn]
        if t < t_lab - .05: continue
        ra = min(a, prog(t, t_lab - .05, .2))
        k_ = popin(t, t_lab - .05, .3)
        w_ = font(32 * K).getlength(chip) / K
        if two_line:
            y = y0 + i * 130
            d.text(110, y, lab, 34, (220, 224, 234, int(255 * ra)), anchor='lm', path=FONT_X)
            d.rect(106, y + 30, 106 + (w_ + 36) * k_, y + 86, col + (al,), r=12)
            if k_ > .6: d.text(106 + (w_ + 36) / 2, y + 59, chip, 32, (255, 255, 255, al))
        else:
            y = y0 + i * 76
            d.text(110, y, lab, 34, (220, 224, 234, int(255 * ra)), anchor='lm', path=FONT_X)
            d.rect(770 - (w_ + 36) * k_, y - 28, 770, y + 28, col + (al,), r=12)
            if k_ > .6: d.text(770 - (w_ + 36) / 2, y + 1, chip, 32, (255, 255, 255, al))

def scene_card(img, t, rows, t0, t1, y=700, wob=None):
    a = window(t, t0, t1, .1, .3)
    if a <= 0: return False
    s = popin(t, t0, .35)
    if wob is not None and t >= wob: s *= 1 + .06 * math.sin((t - wob) * 14) * math.exp(-(t - wob) * 4)
    put(img, info_card(rows), CX, y, s, a, rot=-1.5)
    return True
CARD3 = (("288 hp → 348 hp", 62, INK2), ("+60 hp", 70, DRED), ("0-60: about 0.9 s quicker", 50, INK2))
CARD4 = (("$60/month", 66, INK2), ("$600/year", 66, INK2), ("$1,950 one time", 62, DRED))
CHIPS2 = [('NEW MOTORS', 'NO', RED, 'T_NO'), ('SOFTWARE', 'UNLOCK', GREEN, 'T_UNLOCK')]
FINAL = [("Would you pay $60/month", 64, TAG), ("for 60 hp?", 80, TAG), ("Comment below.", 70, (255, 255, 255)),
         ("Next: another car", 64, (210, 214, 224)), ("that's secretly", 64, (210, 214, 224)), ("another car.", 64, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 410, 104
THUMB = [("$60/MONTH", 150, TAG), ("FOR HORSEPOWER", 78, (255, 255, 255)), ("I ALREADY OWN?!", 78, (255, 255, 255))]
ONSCREEN = (['MERCEDES-BENZ', 'SERVICE', 'ACCELERATION INCREASE', 'PAYMENT OPTIONS', '288', '348', 'HP', 'EQE 350 4MATIC',
             '$60/month', 'SAME CAR', '$10', 'PER HP, PER YEAR', 'GREAT VALUE', '288 hp', '?']
            + [r[0] for c in (CARD3, CARD4) for r in c] + [x for r in CHIPS2 for x in r[:2]] + [f[0] for f in FINAL]
            + [f[0] for f in THUMB])
def overlays(t):
    if t < T_HOOK: return None                               # hook: nothing on screen but the scene for 3 s
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        pa = window(t, max(T_HOOK, T_AI - .1), T_S2 + .05, .1, .3)
        if pa > 0:                                           # the real car, and the bill
            used = True
            put(img, photo_card('eqe.jpg', 'EQE 350 4MATIC', (24, 30, 44), (255, 255, 255), 440), CX, 400,
                popin(t, max(T_HOOK, T_AI - .1), .35), pa, rot=-2)
            sw = math.sin((t - T_AI) * 6) * 4 * math.exp(-(t - T_AI) * 2)
            put(img, price_tag('$60/month', 'ACCELERATION INCREASE', TAG), CX, 720, popin(t, T_AI + .25, .35) * .9, pa, rot=sw - 3)
    elif sc == 1:
        pa = window(t, T_NO - .1, T_S3 + .05, .1, .3)
        if pa > 0:
            used = True
            put(img, photo_card('eqe_frunk.jpg', 'SAME CAR', (24, 30, 44), (255, 255, 255), 420), CX, 390,
                popin(t, T_SAME - .1, .35), pa * (t >= T_SAME - .1), rot=2)
            d = D(img)
            panel(d, 80, 640, 830, 820, pa)
            chip_rows(d, t, CHIPS2, 692, pa)
    elif sc == 2:
        used = scene_card(img, t, CARD3, T_SEC - .2, T_S4 + .05, 760, wob=T_SEC + .2)
    elif sc == 3:
        used = scene_card(img, t, CARD4, T_60M + .3, T_TEN - .1, 640, wob=T_600)
        ta = window(t, T_TEN - .1, T_S5 + .05, .1, .25)
        if ta > 0:
            used = True
            sw = math.sin((t - T_TEN) * 6) * 4 * math.exp(-(t - T_TEN) * 2)
            put(img, price_tag('$10', 'PER HP, PER YEAR', TAG), CX, 560, popin(t, T_TEN - .1, .35) * .9, ta, rot=sw - 3)
            k_ = popin(t, T_GV - .05, .3)
            if k_ > 0: put(img, stamp_img('GREAT VALUE', RED, 80), CX + 20, 780, (2.2 - 1.2 * k_) * .9, ta * min(1, k_ * 2), rot=8)
    else:
        fa = window(t, T_STAY - .1, T_FINAL + .05, .2, .25)
        if fa > 0:
            used = True
            put(img, price_tag('288 hp', 'NOBODY\'S FORCING YOU', (230, 232, 238)), CX, 520, popin(t, T_STAY - .1, .35) * .9, fa, rot=3)
            k_ = popin(t, LE[9] - .1, .3)
            if k_ > .05:
                d = D(img); d.text(CX, 720, '?', 120 * k_, TAG + (int(255 * fa),), stroke=6, sc=(10, 10, 16, int(255 * fa)))
    if t >= T_CARD:                                          # final caption
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(FINAL):
            k_ = popin(t, T_CARD + .08 * i, .3)
            if k_ > .05:
                d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if used else None

def thumbnail():
    """Upload thumbnail: the dyno shot at 348 hp, punched in, with its own headline (not a frame from the video)."""
    t = T_348 + .6
    img = shoot(t)
    img = img.resize((int(W * 1.12), int(H * 1.12)), Image.LANCZOS).crop((int(W * .06) - 40, int(H * .04), int(W * .06) - 40 + W, int(H * .04) + H))
    ov = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0)); d = D(ov)
    d.rect(0, 1180, W, 1660, (12, 14, 20, 215))
    y = 1270
    for txt, size, col in THUMB:
        while font(size).getlength(txt) > 800: size -= 4
        d.text(CX, y, txt, size, col, stroke=6, sc=(10, 10, 16)); y += size * 1.12 + 10
    put(ov, photo_card('eqe.jpg', 'EQE 350 4MATIC', (24, 30, 44), (255, 255, 255), 360), 300, 1010, 1.0, 1.0, rot=-6)
    ov = ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA')
    img = img.convert('RGBA'); img.alpha_composite(ov)
    return img.convert('RGB')
def final_boxes():
    """Final caption text boxes (frame coordinates) for the safe-zone check."""
    out = []
    for i, (txt, size, _) in enumerate(FINAL):
        f = font(size); bb = f.getbbox(txt, anchor='mm', stroke_width=4)
        y = FINAL_Y0 + FINAL_DY * i
        cap = f.getbbox('H')[3] - f.getbbox('H')[1]
        out.append(dict(text=txt, x0=CX + bb[0], x1=CX + bb[2], y0=y + bb[1], y1=y + bb[3], cap_height=cap))
    return out

# ================================================================ captions (tesla-locked system)
def ctext(w): return w['w'].lstrip('.')
CAP_Y = 1128
CAP_SIZE = 78
def chunks():
    out = []
    for ln in sorted(LINES):
        cur = []
        for w in LINES[ln]:
            if cur and font(CAP_SIZE).getlength(' '.join(ctext(x) for x in cur + [w])) > 800:
                out.append(cur); cur = []                   # split rather than shrink below the min text size
            cur.append(w)
            if w['w'][-1] in '.?!,' or len(cur) == 3:
                out.append(cur); cur = []
        if cur: out.append(cur)
    res = []
    for i, c in enumerate(out):
        nxt = out[i + 1][0]['s'] if i + 1 < len(out) else DUR
        end = nxt if nxt - c[-1]['e'] < 0.6 else c[-1]['e'] + 0.45
        res.append(dict(words=c, s=c[0]['s'], e=T_CARD if i == len(out) - 1 else min(end, T_CARD)))
    return res
CHUNKS = chunks()
def cap_size(ws):
    size = CAP_SIZE
    while font(size).getlength(' '.join(ws)) > 800 and size > 60: size -= 2
    return size

@lru_cache(None)
def caption_img(ci, active):
    ws = [ctext(w) for w in CHUNKS[ci]['words']]
    f = font(cap_size(ws))
    total = f.getlength(' '.join(ws)); sp = f.getlength(' ')
    img = Image.new('RGBA', (W, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = (W - total) / 2
    for i, w in enumerate(ws):
        col = (255, 214, 64) if i == active else (255, 255, 255)
        d.text((x, 100), w, font=f, fill=col, anchor='lm', stroke_width=9, stroke_fill=(16, 16, 28))
        x += f.getlength(w) + sp
    return img

def caption_boxes():
    res = []
    for ci, c in enumerate(CHUNKS):
        a = np.array(caption_img(ci, -1).getchannel('A'))
        ys, xs = np.nonzero(a > 8)
        ox, oy = CX - W // 2, CAP_Y - 100
        ws = [ctext(w) for w in c['words']]
        size = cap_size(ws)
        cap_h = font(size).getbbox('H')[3] - font(size).getbbox('H')[1]
        res.append(dict(text=' '.join(ws), s=c['s'], e=c['e'], x0=int(xs.min() + ox), x1=int(xs.max() + ox),
                        y0=int(ys.min() + oy), y1=int(ys.max() + oy), cap_height=int(cap_h)))
    return res

def captions(img, t):
    if t >= T_CARD: return                                  # final caption owns the screen
    live = [ci for ci, c in enumerate(CHUNKS) if c['s'] - 0.02 <= t < c['e']]
    for ci in live[-1:]:
        c = CHUNKS[ci]
        if True:
            act = -1
            for i, w in enumerate(c['words']):
                if w['s'] - .02 <= t: act = i
            ci_img = caption_img(ci, act)
            s = 0.86 + 0.14 * ob(prog(t, c['s'], .12))
            if s != 1:
                ci_img = ci_img.resize((int(W * s), int(200 * s)), Image.LANCZOS)
            img.alpha_composite(ci_img, (int(CX - ci_img.width / 2), int(CAP_Y - ci_img.height / 2)))


# ================================================================ frame
TR = 0.4                                                    # whip-pan length
def frame(n):
    t = n / FPS
    tr = next((s for s in SCENES[1:] if s - TR / 2 <= t < s + TR / 2), None)
    if tr is None:
        img = shoot(t)
    else:                                                   # whip pan: old scene out left, new in from right, motion blur
        k = io(prog(t, tr - TR / 2, TR))
        sc_new = SCENES.index(tr)
        a, b = shoot(min(t, tr - .001), sc_new - 1), shoot(max(t, tr), sc_new)
        img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        off = int(W * k)
        img.alpha_composite(a, (-off, 0)); img.alpha_composite(b, (W - off, 0))
        bl = math.sin(math.pi * k)
        if bl > .05:
            smear = img.resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
            img = Image.blend(img, smear, min(.85, bl))
    if T_CLOSE <= t < T_CLOSE + .3:                         # hard cut closer on the car, with a flash
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.45 * (1 - prog(t, T_CLOSE, .3)))
    ov = overlays(t)
    if ov is not None:
        ov = ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA')
        img.alpha_composite(ov)
    if BEAT[0] + .1 <= t < T_FINAL:                         # the beat: room dims, everyone waits
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.22 * io(prog(t, BEAT[0] + .1, .5)))
    if T_FINAL <= t < T_FINAL + .5:
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.25 * (1 - prog(t, T_FINAL, .5)))
    if t >= T_CARD:                                         # ending vignette
        k_ = io(prog(t, T_CARD, 1.0)) * .45
        v = vignette()
        img.alpha_composite(Image.merge('RGBA', (*v.split()[:3], v.getchannel('A').point(lambda p: int(p * k_)))))
    captions(img, t)
    return img.convert('RGB').tobytes()

@lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - CX) / (W * .62)) ** 2 + ((yy - 1100) / (H * .55)) ** 2)
    a = np.clip((r - .55) * 1.6, 0, 1) * 255
    return Image.fromarray(np.dstack([np.zeros((H, W, 3)), a]).astype(np.uint8), 'RGBA')

# ================================================================ audio
def build_audio(voice, out_wav):
    SR = sfx.SR
    v = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rng = np.random.default_rng(3); T_ = np.arange(n) / SR
    def lpf(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
    # per-scene beds (quiet; room left for the user's own music), crossfaded at the whip pans
    def env(a, b, f=.25): return np.clip(np.minimum((T_ - a) / f + .5, (b - T_) / f + .5), 0, 1)
    room = lpf(rng.standard_normal(n), 60) * 0.10 + 0.004 * np.sin(2 * np.pi * 110 * T_)
    hum = 0.005 * np.sin(2 * np.pi * 60 * T_) + 0.003 * np.sin(2 * np.pi * 120 * T_)
    bed = room + hum * (env(T_S3, T_S5))                     # quiet; room left for the user's own music
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def tick(): return click(4200, 5200, .03) * .5
    def sting():
        """Final sting: low brass-ish stab (detuned saws) + sub hit + bright crash tail."""
        d = 2.4; tt = np.arange(int(SR * d)) / SR
        s = np.zeros_like(tt)
        for f in (73.4, 110.0, 146.8, 174.6, 220.0):
            for det in (-0.6, 0.6):
                s += ((tt * (f + det)) % 1 * 2 - 1)
        s = lpf(s, 6) * np.exp(-tt * 2.2) * np.minimum(1, tt * 200) * .09
        s += np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 5) * .9
        s += (rng.standard_normal(len(tt)) - lpf(rng.standard_normal(len(tt)), 4)) * np.exp(-tt * 2.6) * .25
        return s
    T0 = np.arange(n) / SR
    wind = lpf(rng.standard_normal(n), 200) * 0.25 * env(0, T_S2)                       # outdoors: wind + far traffic
    whine = np.zeros(n)                                                                    # dyno: electric-motor whine
    m = (T0 >= T_60HP - .2) & (T0 < T_S4)
    fr = 180 + 260 * np.clip((T0 - T_60HP) / 4.5, 0, 1) + 140 * (T0 >= T_348)
    whine[m] = (np.sin(2 * np.pi * np.cumsum(fr) / SR) * .03 + np.sin(4 * np.pi * np.cumsum(fr) / SR) * .012)[m]
    bed = bed + wind + whine * np.clip((T0 - T_60HP + .2) / .4, 0, 1) * np.clip((T_S4 - T0) / .2, 0, 1)
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    for k_ in range(4): add(0.02 + k_ * 0.3, step(), .5)
    add(T_SIXTY0, sfx.pop(), .25); add(T_HP0 + .2, sfx.thump(.2), .3)
    add(T_CLOSE, sfx.whoosh(.3, 14), .3)
    add(T_AI - .1, sfx.pop(), .35); add(T_AI + .3, sfx.cha_ching(), .3)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    for s_ in SCENES[1:4]:                                  # buyer hurrying in
        for k_ in range(3): add(s_ + .08 + k_ * .25, step(), .35)
    for k_ in range(3): add(T_S5 + .05 + k_ * .3, step(), .3)
    add(T_NO - .05, sfx.buzzer(.25), .22); add(T_SAME, sfx.pop(), .3)
    add(T_UNLOCK - .05, click(900, 1400, .08), .7); add(T_UNLOCK + .05, sfx.ding(1320, .6), .14)
    add(T_288, sfx.pop(), .25); add(T_348 - .05, sfx.sparkle(), .25); add(T_SEC - .2, sfx.stamp(), .3)
    add(T_60M + .3, sfx.stamp(), .32); add(T_600, sfx.cha_ching(), .3)
    add(T_TEN - .1, sfx.pop(), .35); add(T_GV - .05, sfx.stamp(), .4)
    add(T_OWN, sfx.thump(.3), .35)
    add(T_STAY - .1, sfx.pop(), .25)
    for k_ in range(2): add(BEAT[0] + .2 + k_ * .4, tick(), .6)
    add(T_FINAL - .02, sting(), .7); add(T_CARD, sfx.pop(), .35)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s
    mixd = v * 1.0 + fxa[:n] * 0.55 + bed * 0.6
    mixd = np.clip(mixd / max(1.0, np.abs(mixd).max() / 0.95), -1, 1)
    tmp = out_wav + '.pre.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', tmp],
                   input=mixd.astype(np.float64).tobytes(), check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', af, '-ar', '48000', '-ac', '2', tmp + '2.wav'], check=True)
    # loudnorm can land short of target: trim the last dB with a static gain, keeping >= 1.5 dB true-peak headroom
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', tmp + '2.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = float(r.split('I:')[-1].split('LUFS')[0]); tp = float(r.split('Peak:')[-1].split('dBFS')[0])
    g = min(-14.0 - I, -1.5 - tp)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp + '2.wav', '-af', f'volume={g:.2f}dB', out_wav], check=True)
    os.remove(tmp); os.remove(tmp + '2.wav')

def _init(voice):
    load_mouth(voice)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'thumb':                                      # upload thumbnail: own still + headline, never a video frame
        load_mouth(sys.argv[3] if len(sys.argv) > 3 else VOICE_CACHE)
        thumbnail().save(sys.argv[2]); print('thumb', sys.argv[2])
    if mode == 'still':
        load_mouth(sys.argv[4] if len(sys.argv) > 4 else VOICE_CACHE)
        Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif mode == 'meta':
        json.dump(dict(captions=caption_boxes(), final=final_boxes(), onscreen=ONSCREEN, duration=DUR, size=[W, H], fps=FPS),
                  open(sys.argv[2], 'w'), indent=1)
    elif mode == 'video':
        voice, out = sys.argv[2], sys.argv[3]
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        wav = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(voice, wav)
        nf = int(DUR * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-maxrate', '13M',
                               '-bufsize', '26M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
                               '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(voice,)) as pool:
            for i, buf in enumerate(pool.imap(frame, range(nf), chunksize=4)):
                ff.stdin.write(buf)
                if i % 150 == 0: print(f'frame {i}/{nf}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', out)
