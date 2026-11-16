"""Aston Martin Cygnet skit: showroom -> parking lot -> boardroom -> showroom. Flat-vector style, 1080x1920 @30.
Same cast, caption system and mix chain as tesla-locked.
Usage: python render.py video VOICE.wav OUT.mp4 | python render.py still T OUT.png [VOICE] | python render.py meta OUT.json"""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sfx

W, H, FPS, K = 1080, 1920, 30, 2
CX = 459                                   # composition centre (left 85% of width)
DUR = 39.5
WALL_Y, FEET_Y = 940, 1880
HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/aston-cygnet/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
T_S2 = LE[5] + 0.8                         # scene cuts (whip pans)
T_S3 = LE[11] + 0.5
T_S4 = LE[15] + 0.9
WHY1 = LS[12] - 0.15                       # "Why?" card: T_S3 .. WHY1
BEAT = (LE[16], LS[17])
T_TOYOTA0 = word_t(0, 'Toyota')
T_THIRTY, T_POUNDS = word_t(3, 'thirty'), word_t(3, 'pounds')
T_TEN = word_t(4, 'ten')
T_LEATHER = word_t(5, 'leather')
T_ENG, T_HP = word_t(7, 'engine'), word_t(7, 'horsepower')
T_SPEED = LS[9]
T_EVERY = word_t(10, 'everything')
T_GRILLE, T_LIGHTS, T_LEATH2 = word_t(11, 'grille'), word_t(11, 'lights'), word_t(11, 'Leather')
T_EMIS, T_HIGH = word_t(13, 'emissions'), word_t(13, 'high')
T_BOUGHT = word_t(14, 'Toyota')
T_CORRECT = LS[15]
T_FINAL, T_FTEN = LS[17], word_t(17, 'ten')
SCENES = [0.0, T_S2, T_S3, T_S4]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)

# ---- easing
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

# ================================================================ emblems (hand-drawn, not logo files)
AM_GREEN, AM_GREEN2, AM_GREEN3 = (22, 88, 66), (52, 132, 100), (10, 52, 38)
CHROME, CHROME2 = (214, 220, 228), (120, 128, 140)
def wings(d, cx, cy, s=1.0, col=(232, 234, 238), bar=True):
    """Generic winged emblem: two swept wings with feather cuts and a centre bar."""
    for side in (-1, 1):
        pts = [(cx + side * x * s, cy + y * s) for x, y in
               [(34, -22), (120, -30), (230, -44), (300, -40), (250, -18), (300, -12), (220, 6), (250, 16), (150, 22), (34, 20)]]
        d.poly(pts, col)
        for k in range(4):
            x = 90 + k * 48
            d.line([(cx + side * x * s, cy - (26 + k * 3) * s), (cx + side * (x - 26) * s, cy + 16 * s)], (0, 0, 0, 70), max(1.5, 3 * s))
    if bar:
        d.rect(cx - 70 * s, cy - 18 * s, cx + 70 * s, cy + 18 * s, col, r=4 * s)
        d.rect(cx - 62 * s, cy - 11 * s, cx + 62 * s, cy + 11 * s, AM_GREEN3)

def toyota_ovals(d, cx, cy, s=1.0, col=(200, 204, 212), w=5):
    """Generic three-oval emblem."""
    d.ell(cx, cy, 46 * s, 30 * s, None, col, w * s)
    d.ell(cx, cy - 8 * s, 30 * s, 14 * s, None, col, w * s)
    d.ell(cx, cy + 4 * s, 12 * s, 26 * s, None, col, w * s)

# ================================================================ cars (side profile, front to the left)
CAR_CTRL = [(0.012, .15), (0.0, .30), (.012, .42), (.07, .48), (.16, .52), (.27, .57), (.37, .78), (.45, .92), (.62, .96),
            (.84, .94), (.95, .87), (.99, .72), (1.0, .50), (.995, .28), (.975, .15), (.86, .14), (.5, .15), (.14, .14)]
def city_car(d, x0, ground, L, kind):
    """Toyota iQ / Aston Martin Cygnet: same body, different face, lights and trim."""
    Hh = L / 2.0
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    aston = kind == 'cygnet'
    body = (AM_GREEN, AM_GREEN2, AM_GREEN3) if aston else ((226, 229, 234), (250, 251, 253), (176, 180, 188))
    d.ell(x0 + L * .5, ground + 4, L * .56, 16, (0, 0, 0, 70))
    d.poly(spline([P(u, v) for u, v in CAR_CTRL], 8), body[0], (24, 26, 34), 5)
    d.poly(spline([P(.02, .16), P(.5, .17), P(.98, .16), P(.99, .30), P(.5, .28), P(.01, .29)], 6), body[2])
    d.line(spline([P(.06, .46), P(.30, .52), P(.62, .55), P(.95, .55)], 8, closed=False), body[1], 4)
    # glass
    gh = [P(.29, .60), P(.38, .78), P(.455, .885), P(.62, .915), P(.83, .895), P(.925, .83), P(.955, .66), P(.94, .60)]
    d.poly(spline(gh, 6), (30, 40, 54), (20, 22, 28), 4)
    d.poly([P(.585, .60), P(.61, .60), P(.62, .91), P(.595, .91)], body[0])
    d.line([P(.36, .70), P(.43, .82)], (130, 150, 175), 5)
    if aston:                                           # leather interior glimpse: tan seat through the glass
        d.poly(spline([P(.64, .62), P(.66, .80), P(.71, .82), P(.70, .62)], 4), (176, 112, 66))
        d.line([P(.665, .66), P(.68, .79)], (120, 70, 40), 2)
    # door, handle, mirror
    d.line([P(.27, .57), P(.25, .20)], tuple(int(c * .7) for c in body[0]), 3)
    d.line([P(.62, .58), P(.63, .20)], tuple(int(c * .7) for c in body[0]), 3)
    d.rect(*P(.50, .50), *P(.56, .475), CHROME if aston else (190, 194, 200), r=3)
    d.poly([P(.30, .62), P(.35, .63), P(.35, .68), P(.30, .67)], body[0], (24, 26, 34), 3)
    if aston:
        # signature grille at the nose (chrome frame, horizontal bars) + side strake
        g = spline([P(-.005, .41), P(.035, .41), P(.045, .30), P(.03, .21), P(.0, .20)], 4)
        d.poly(g, (24, 26, 30), CHROME, 4)
        for v in (.24, .28, .32, .36):
            d.line([P(.003, v), P(.035, v)], CHROME2, 2)
        d.poly([P(.15, .40), P(.24, .42), P(.24, .44), P(.15, .43)], CHROME)
        d.poly(spline([P(.03, .46), P(.10, .50), P(.16, .49), P(.08, .44)], 4), (250, 252, 255), (24, 26, 34), 3)
        d.line([P(.05, .465), P(.13, .485)], (120, 200, 255), 2)
        wings(d, *P(.05, .515), 0.08, CHROME, bar=False)
        d.poly([P(.975, .58), P(.998, .58), P(.998, .78), P(.965, .76)], (210, 30, 40), (60, 10, 14), 3)
    else:
        d.poly(spline([P(.0, .26), P(.03, .27), P(.04, .33), P(.0, .33)], 4), (40, 42, 48))
        d.poly(spline([P(.02, .43), P(.13, .50), P(.17, .47), P(.11, .41)], 4), (238, 242, 248), (24, 26, 34), 3)
        d.ell(*P(.10, .455), 6, 6, (255, 190, 60))
        toyota_ovals(d, *P(.03, .37), 0.18, (150, 154, 162), 4)
        d.poly([P(.97, .55), P(.998, .55), P(.998, .80), P(.96, .78)], (230, 60, 50), (60, 10, 14), 3)
    # wheels
    r = Hh * .19
    for u in (.165, .825):
        wx, wy = P(u, 0)[0], ground - r
        d.ell(wx, wy, r, r, (22, 22, 26))
        d.ell(wx, wy, r * .66, r * .66, CHROME if aston else (170, 174, 182), (80, 84, 92), 3)
        for a in range(10 if aston else 5):
            ra = math.radians(a * (36 if aston else 72) + 18)
            d.line([(wx, wy), (wx + r * .6 * math.cos(ra), wy + r * .6 * math.sin(ra))], (96, 100, 110), 3 if aston else 6)
        d.ell(wx, wy, r * .14, r * .14, AM_GREEN if aston else (60, 62, 70))

@lru_cache(None)
def car_layer(kind, L):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .62) * K), (0, 0, 0, 0))
    city_car(D(img, ox=-L * .1, oy=-L * .56), 0, 0, L, kind)
    return img
def paste_car(img, kind, x0, ground, L):
    c = car_layer(kind, L)
    img.paste(c, (int((x0 - L * .1) * K), int((ground - L * .56) * K)), c)

# ================================================================ sets
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)

@lru_cache(None)
def bg_showroom():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (16, 22, 20), (38, 46, 44)), grad((H - WALL_Y) * K, W * K, (200, 202, 204), (234, 235, 236))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-40, W, 170):                          # tall wall panels with brushed trim
        d.rect(x + 8, 80, x + 160, WALL_Y - 40, (30, 38, 36), r=6)
        d.line([(x + 8, 80), (x + 8, WALL_Y - 40)], (54, 64, 60), 2)
    for px in (150, 459, 768):                            # pendant lights
        d.line([(px, 0), (px, 70)], (70, 74, 78), 3)
        d.chord(px, 92, 46, 28, 180, 360, (60, 66, 64))
        d.ell(px, 92, 30, 6, (255, 240, 200))
    d.rect(0, WALL_Y - 8, W, WALL_Y, (196, 170, 120))
    d.rect(0, WALL_Y, W, WALL_Y + 6, AM_GREEN)
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (214, 216, 219), 2)
    img = spot(img, CX, 120, 70, 470, 800)
    d = D(img)
    wings(d, CX, 210, 0.95, (236, 228, 205))
    d.text(CX, 300, 'A S T O N   M A R T I N', 40, (236, 228, 205), path=FONT_X)
    # turntable
    d.ell(CX, 905, 400, 50, (14, 16, 16))
    d.ell(CX, 897, 394, 44, (50, 56, 54), (196, 170, 120), 5)
    d.ell(CX, 897, 340, 34, (62, 68, 66))
    # plinth sign + plant
    d.rect(812, 760, 905, 905, (28, 34, 32), r=8, ol=(196, 170, 120), w=3)
    d.text(858, 800, 'CYGNET', 17, (236, 228, 205), path=FONT_X)
    d.rect(40, 820, 98, 900, (60, 64, 62), r=6)
    for a in range(-60, 61, 20):
        r_ = math.radians(a - 90)
        d.line([(69, 822), (69 + 70 * math.cos(r_), 822 + 90 * math.sin(r_))], (40, 96, 60), 9)
    return img

@lru_cache(None)
def bg_lot():
    HOR = 700
    arr = np.concatenate([grad(HOR * K, W * K, (96, 150, 206), (236, 214, 186)), grad((H - HOR) * K, W * K, (98, 100, 106), (70, 72, 78))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.ell(820, 300, 90, 90, (255, 236, 200, 120)); d.ell(820, 300, 52, 52, (255, 246, 222))
    for cx_, cy_, s in ((180, 190, 1.0), (640, 130, .8)):  # clouds
        for dx, dy, r in ((0, 0, 50), (50, -20, 60), (110, 0, 46), (55, 14, 50)):
            d.ell(cx_ + dx * s, cy_ + dy * s, r * s, r * .7 * s, (250, 246, 240, 200))
    rng = np.random.default_rng(5); x = -20
    while x < W:                                          # skyline
        bw, bh = rng.integers(70, 150), rng.integers(120, 330)
        col = mix((130, 150, 176), (160, 168, 186), rng.random())
        d.rect(x, HOR - bh, x + bw, HOR + 4, col)
        for wy in range(int(HOR - bh + 20), HOR - 10, 34):
            for wx in range(int(x + 12), int(x + bw - 14), 26):
                d.rect(wx, wy, wx + 12, wy + 16, (176, 192, 214))
        x += bw + rng.integers(4, 20)
    d.rect(0, HOR - 6, W, HOR + 30, (64, 112, 70))           # hedge strip
    for hx in range(-10, W, 34):
        d.ell(hx, HOR - 4, 26, 18, (72, 124, 78))
    d.rect(0, HOR + 30, W, HOR + 44, (190, 190, 186))         # kerb
    for k_, lx in enumerate((300, 640)):                      # bay lines in perspective
        d.poly([(lx - 4, HOR + 44), (lx + 4, HOR + 44), (lx + (lx - CX) * .9 + 8, 1010), (lx + (lx - CX) * .9 - 8, 1010)], (236, 236, 230))
    d.poly([(-20, 1000), (W, 1000), (W, 1014), (-20, 1014)], (236, 236, 230))
    for px_ in (70, 870):                                     # lamp posts
        d.rect(px_ - 5, 170, px_ + 5, HOR + 40, (60, 64, 72))
        d.line([(px_, 176), (px_ + (40 if px_ < CX else -40), 166)], (60, 64, 72), 8)
        d.ell(px_ + (52 if px_ < CX else -52), 170, 22, 9, (240, 240, 226))
    for y in range(1100, H, 210):
        d.line([(0, y), (W, y + 20)], (84, 86, 92), 3)
    return img

@lru_cache(None)
def bg_board():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (58, 38, 28), (92, 62, 42)), grad((H - WALL_Y) * K, W * K, (64, 60, 70), (44, 42, 50))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(0, W, 120):                                # walnut panels
        d.line([(x, 0), (x, WALL_Y)], (44, 28, 20), 4)
        for k_ in range(6):
            yy = 60 + k_ * 150
            d.line([(x + 20, yy), (x + 100, yy + 30)], (106, 72, 50), 2)
    d.rect(0, 0, W, 60, (30, 22, 18))
    for px in (180, 459, 738):
        d.ell(px, 40, 60, 10, (255, 236, 196))
    d.rect(100, 200, 820, 720, (16, 18, 22), r=14, ol=(40, 40, 46), w=8)  # wall screen
    d.rect(0, WALL_Y - 10, W, WALL_Y, (36, 24, 18))
    img = spot(img, CX, 40, 260, 520, 900, 30)
    d = D(img)
    # long table (behind the cast) + chair backs
    d.poly([(-40, 1040), (W + 40, 1040), (W + 40, 1092), (-40, 1092)], (70, 44, 30))
    d.poly([(-40, 1000), (W + 40, 1000), (W + 40, 1044), (-40, 1044)], (122, 82, 56), (40, 26, 18), 4)
    for cxh in (60, 860):
        d.rect(cxh - 60, 860, cxh + 60, 1010, (26, 26, 30), r=26)
    for gx in (300, 620):
        d.rect(gx - 14, 950, gx + 14, 1000, (190, 220, 240, 150), r=4)
    d.rect(880, 820, 940, 1000, (60, 46, 38), r=6)
    for a in range(-70, 71, 20):
        r_ = math.radians(a - 90)
        d.line([(910, 822), (910 + 80 * math.cos(r_), 822 + 110 * math.sin(r_))], (46, 110, 66), 10)
    return img

# ================================================================ characters (tesla-locked cast)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('1c1d22'), suit2=hexc('0e0f12'),
             shirt=hexc('f7f7fa'), tie=hexc('111114'), pants=hexc('1c1d22'), shoe=hexc('3a2a22'), glasses=False, hairstyle='part', lids=0.45)
OL = (26, 26, 46)
POSES = {'rest': (10, 323), 'clasp': (-100, 286), 'open': (120, 170), 'point': (235, 70), 'up': (70, -290),
         'head': (-92, -158), 'shrug': (128, 108), 'cross': (-176, 168), 'thanks': (-100, 92), 'raise1': (40, -230),
         'offer': (210, 120), 'chin': (-70, -110), 'hip': (90, 230), 'present': (240, -230)}
UA, FA = 168, 158
OUTBEND = {'up', 'head', 'raise1', 'chin'}
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
    if not c['glasses']:                                  # dealer name badge with a tiny wing mark
        d.rect(x + 46, top + 92, x + 100, top + 118, (245, 245, 248), r=4)
        wings(d, x + 73, top + 105, 0.1, AM_GREEN, bar=False)
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
        if prop == 'card':                                # black credit card
            d.rect(hx2 - 6, hy2 - 52, hx2 + 70, hy2 - 4, (24, 24, 30), r=6, ol=(200, 170, 90), w=3)
            d.rect(hx2 + 4, hy2 - 40, hx2 + 22, hy2 - 28, (210, 180, 100), r=2)

# ---- performance schedules: (time, left pose, right pose, extras)
def buyer_sched():
    return [(0.0, 'rest', 'point', dict(brows='angry', eyes='wide')),
            (LS[1], 'rest', 'point', dict(brows='angry')),
            (LS[2] - .1, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (LE[2] + .2, 'rest', 'rest', dict(brows='up')),
            (T_POUNDS, 'rest', 'rest', dict(brows='up', eyes='wide', smile=-1)),
            (LS[4] - .1, 'up', 'up', dict(brows='angry', eyes='wide')),
            (LS[5] + .2, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # scene 2
            (T_S2, 'hip', 'open', dict(brows='angry')),
            (LS[6] - .1, 'hip', 'point', dict(brows='angry')),
            (LE[6] + .15, 'hip', 'rest', dict(brows='flat')),
            (T_HP, 'rest', 'rest', dict(brows='up', eyes='wide')),
            (LS[8] - .1, 'rest', 'point', dict(brows='angry')),
            (LE[8] + .2, 'rest', 'rest', dict(brows='up')),
            (LS[10] - .1, 'up', 'up', dict(brows='up', eyes='wide', sweat=1)),
            (LE[10] + .3, 'rest', 'rest', dict(brows='worried')),
            # scene 3
            (T_S3, 'chin', 'cross', dict(brows='worried')),
            (LS[12] - .1, 'shrug', 'shrug', dict(brows='worried', eyes='wide')),
            (LE[12] + .2, 'rest', 'rest', dict(brows='worried')),
            (LS[14] - .1, 'rest', 'open', dict(brows='flat', smile=-1, tired=0.35)),
            (T_CORRECT + .1, 'head', 'head', dict(brows='worried', eyes='wide')),
            # scene 4: resigned, card out, shut down
            (T_S4, 'rest', 'rest', dict(brows='worried', tired=0.5, smile=-1)),
            (LS[16] + .15, 'rest', 'offer', dict(brows='flat', tired=0.5, prop={'rpose': 'card'})),
            (T_FTEN + .1, 'head', 'head', dict(brows='worried', eyes='wide', smile=-1))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    s += [(LS[3] + .05, 'open', 'clasp', {}), (LE[3] + .1, 'clasp', 'clasp', {}),
          (LS[7] + .05, 'present', 'clasp', {}), (LE[7], 'clasp', 'clasp', {}),
          (T_GRILLE - .1, 'present', 'clasp', {}), (LE[11] + .1, 'clasp', 'clasp', {}),
          (LS[13] + .05, 'present', 'clasp', {}), (LE[13] + .1, 'clasp', 'clasp', {}),
          (LS[17] + .05, 'open', 'clasp', {}), (LE[17] + .3, 'clasp', 'clasp', {})]
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
def board_screen(d, t):
    """Wall screen in the boardroom: emblem, then the average-emissions chart."""
    x0, y0, x1, y1 = 112, 212, 808, 708
    ck = prog(t, T_EMIS - .1, .3)
    if ck < 1:
        a = int(255 * (1 - ck))
        wings(d, CX, 430, 0.9, (236, 228, 205, a))
        d.text(CX, 520, 'A S T O N   M A R T I N', 34, (236, 228, 205, a), path=FONT_X)
    if ck <= 0: return
    A = int(255 * ck)
    d.text(CX, 262, 'AVERAGE CO₂', 46, (240, 240, 245, A))
    base = 640
    d.line([(150, base), (770, base)], (120, 124, 134, A), 4)
    bars = [('VANTAGE', 250, 300, (210, 64, 60)), ('VANQUISH', 450, 330, (210, 64, 60)), ('CYGNET', 650, 92, (70, 200, 120))]
    for i, (name, bx, bh, col) in enumerate(bars):
        if name == 'CYGNET':
            k_ = oc(prog(t, T_BOUGHT, .35))
            if k_ <= 0: continue
            yb = base - bh - (1 - k_) * 360          # drops in from above
            d.rect(bx - 62, yb, bx + 62, yb + bh, col + (A,), r=10)
            d.text(bx, base + 28, name, 26, (240, 240, 245, int(A * k_)))
            continue
        k_ = io(prog(t, T_EMIS + i * .15, .5))
        d.rect(bx - 62, base - bh * k_, bx + 62, base, col + (A,), r=10)
        d.text(bx, base + 28, name, 26, (240, 240, 245, A))
    # target and average lines (no figures: shape only)
    ty = 470
    for xx in range(150, 770, 36):
        d.line([(xx, ty), (xx + 18, ty)], (90, 220, 130, A), 5)
    d.text(156, ty - 22, 'TARGET', 22, (90, 220, 130, A), anchor='lm')
    ak = prog(t, T_HIGH - .1, .25)
    if ak > 0:
        drop = io(prog(t, T_BOUGHT + .25, .7))
        ay = 325 + (520 - 325) * drop
        blink = 1.0 if drop > 0 or (t * 4) % 1 < .6 else .45
        col = mix((255, 80, 80), (120, 240, 160), drop)
        d.line([(150, ay), (770, ay)], col + (int(A * ak * blink),), 7)
        d.text(764, ay + (24 if drop > .5 else -24), 'AVERAGE', 24, col + (int(A * ak * blink),), anchor='rm')

def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    if sc in (0, 3):
        img = bg_showroom().copy()
        paste_car(img, 'cygnet', CX - 290, 894, 580)
    elif sc == 1:
        img = bg_lot().copy()
        paste_car(img, 'iq', 40, 868, 390)
        paste_car(img, 'cygnet', 488, 868, 390)
        d = D(img)
        for x_, txt, bgc in ((235, 'TOYOTA iQ', (230, 232, 236)), (682, 'ASTON MARTIN CYGNET', AM_GREEN)):
            f = font(24 * K); w_ = f.getlength(txt) / K
            d.rect(x_ - w_ / 2 - 14, 638, x_ + w_ / 2 + 14, 676, bgc, r=8)
            d.text(x_, 657, txt, 24, (30, 30, 36) if bgc != AM_GREEN else (240, 236, 220))
    else:
        img = bg_board().copy()
        board_screen(D(img), t)
    d = D(img)
    f = int(round(t * FPS))
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.25), -40, 11
    elif sc == 3:
        walk_k, bx0, dur_w = prog(t, t_in, 1.1), 40, 7      # tired shuffle back in
    else:
        walk_k, bx0, dur_w = 1.0, 270, 0
    bx = bx0 + (270 - bx0) * oc(walk_k)
    for who, x, sched, cfg, spk in (('S', 670, SS_, SALES, 'S'), ('B', bx, BS, BUYER, 'B')):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[spk][min(f, len(MOUTH[spk]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1), **ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        breathe = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3
        st['dy'] = breathe + (-4 if talking(spk, t) and (f // 4) % 2 else 0)
        if who == 'B' and walk_k < 1:
            st['walk'] = t * dur_w
            st['dy'] -= abs(math.sin(t * dur_w)) * (10 if sc == 0 else 5)
        if st.get('sweat'):
            st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
    return img

def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0:
        z = 1.07 - 0.05 * oc(prog(t, 0, 1.4)) + 0.01 * math.sin(t * .5)
        punches = ((T_TOYOTA0, .05), (T_THIRTY, .03), (T_TEN, .05))
    elif sc == 1:
        z = 1.05 + 0.015 * io(prog(t, t0, 10))
        sx = 46 * (1 - oc(prog(t, t0, 1.6)))               # settle after the whip
        punches = ((T_HP, .03), (T_EVERY, .05))
    elif sc == 2:
        z = 1.02 + 0.04 * io(prog(t, WHY1, 8))
        punches = ((T_HIGH, .03), (T_BOUGHT, .04), (T_CORRECT, .03))
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_FINAL, .06),)
        z += 0.10 * io(prog(t, T_FINAL + .4, 2.6))
    for tp, amt in punches:
        if tp <= t < tp + .5:
            z += amt * (1 - oc(prog(t, tp, .5)))
    if T_FINAL <= t < T_FINAL + .3:
        k_ = 1 - prog(t, T_FINAL, .3)
        sx, sy = math.sin(t * 90) * 10 * k_, math.cos(t * 77) * 8 * k_
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
def stamp_img(txt, col, size=96):
    f = font(size * K); w_ = int(f.getlength(txt) / K) + 90
    st_ = Image.new('RGBA', (w_ * K, int(size * 1.9) * K), (0, 0, 0, 0)); sd = D(st_)
    sd.rect(14, 14, w_ - 14, size * 1.9 - 14, None, r=18, ol=col + (255,), w=11)
    sd.text(w_ / 2, size * .95 + 4, txt, size, col + (255,))
    return st_

@lru_cache(None)
def leather_badge():
    b = Image.new('RGBA', (520 * K, 220 * K), (0, 0, 0, 0)); d = D(b)
    d.rect(14, 14, 506, 206, (128, 72, 40), r=34, ol=(60, 30, 14), w=6)
    for i in range(-4, 12):                               # quilted diamonds
        d.line([(30 + i * 44, 30), (30 + i * 44 + 150, 190)], (104, 56, 30), 4)
        d.line([(30 + i * 44 + 150, 30), (30 + i * 44, 190)], (104, 56, 30), 4)
    d.rect(30, 30, 490, 190, None, r=24, ol=(232, 196, 140), w=3)
    for xx in range(44, 480, 22):                          # stitching
        d.line([(xx, 40), (xx + 10, 40)], (240, 214, 160), 3)
        d.line([(xx, 180), (xx + 10, 180)], (240, 214, 160), 3)
    d.text(260, 112, '+ LEATHER', 70, (255, 244, 222), stroke=4, sc=(70, 34, 14))
    return b

@lru_cache(None)
def inset(kind):
    r = 118
    im = Image.new('RGBA', (2 * r * K + 8 * K, 2 * r * K + 8 * K), (0, 0, 0, 0)); d = D(im, ox=-r - 4, oy=-r - 4)
    d.ell(0, 0, r, r, (24, 28, 30))
    if kind == 'grille':
        d.ell(0, 0, r - 6, r - 6, AM_GREEN)
        g = spline([(-84, -46), (84, -46), (78, 10), (40, 56), (0, 66), (-40, 56), (-78, 10)], 6)
        d.poly(g, (20, 22, 26), CHROME, 9)
        for y in range(-32, 56, 15):
            d.line([(-80, y), (80, y)], CHROME2, 4)
        d.poly(g, None, CHROME, 9)
        wings(d, 0, -64, 0.2, CHROME, bar=False)
    elif kind == 'lights':
        d.ell(0, 0, r - 6, r - 6, AM_GREEN)
        lamp = spline([(-90, -10), (-20, -46), (80, -40), (96, -6), (40, 30), (-70, 30)], 6)
        d.poly(lamp, (250, 252, 255), (30, 34, 40), 7)
        d.ell(-30, -6, 24, 24, (200, 220, 240), (120, 130, 150), 4)
        d.ell(34, -10, 20, 20, (200, 220, 240), (120, 130, 150), 4)
        d.line([(-74, 18), (70, 12)], (120, 200, 255), 6)
    else:
        d.ell(0, 0, r - 6, r - 6, (138, 80, 44))
        for i in range(-5, 6):
            d.line([(i * 40 - 120, -120), (i * 40 + 120, 120)], (108, 60, 32), 5)
            d.line([(i * 40 + 120, -120), (i * 40 - 120, 120)], (108, 60, 32), 5)
        for i in range(-5, 6):
            for j in range(-5, 6):
                if abs(i) + abs(j) < 6: d.ell(i * 40 + (j % 2) * 20, j * 20 + 0, 3, 3, (232, 196, 140))
    # crisp ring mask
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse([4 * K, 4 * K, im.width - 4 * K, im.height - 4 * K], fill=255)
    im.putalpha(Image.fromarray(np.minimum(np.array(im.getchannel('A')), np.array(m))))
    D(im, ox=-r - 4, oy=-r - 4).ell(0, 0, r - 2, r - 2, None, (255, 255, 255), 7)
    return im

def panel(d, x0, y0, x1, y1, a, col=(14, 16, 22)):
    d.rect(x0, y0, x1, y1, col + (int(236 * a),), r=30)

ONSCREEN = ['ASTON MARTIN', 'CYGNET', 'TOYOTA iQ', 'ASTON MARTIN CYGNET', '£30,995', 'ASTON MARTIN CYGNET · 2011',
            'FROM ABOUT £10,000', 'TOYOTA iQ · 2011', 'TOYOTA', '+ LEATHER', 'ENGINE', '1.33 L', '97 HP', '0–62 MPH', '11.8 s',
            'SAME', 'NEW', 'GRILLE', 'LIGHTS', 'LEATHER', 'WHY?', 'AVERAGE CO₂', 'VANTAGE', 'VANQUISH', 'TARGET', 'AVERAGE', '✓']

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        # "TOYOTA" stamp slapped across the car
        sa = window(t, T_TOYOTA0 + .05, LS[3] - .1, .05, .3)
        if sa > 0:
            used = True
            s = 1 + 1.1 * (1 - oc(prog(t, T_TOYOTA0 + .05, .14)))
            put(img, stamp_img('TOYOTA', RED), CX, 760, s, sa, rot=-9)
        # price tags
        ta = window(t, T_THIRTY - .05, LS[5] + .15, .15, .3)
        if ta > 0:
            used = True
            s = popin(t, T_THIRTY, .35)
            sw = math.sin((t - T_THIRTY) * 6) * 4 * math.exp(-(t - T_THIRTY) * 2)
            put(img, price_tag('£30,995', 'ASTON MARTIN CYGNET · 2011', TAG), CX, 415, s, ta, rot=sw)
        tb = window(t, T_TEN - .02, LS[5] + .15, .1, .3)
        if tb > 0:
            used = True
            s = popin(t, T_TEN, .3)
            sw = math.sin((t - T_TEN) * 7) * 5 * math.exp(-(t - T_TEN) * 2.4)
            put(img, price_tag('FROM ABOUT £10,000', 'TOYOTA iQ · 2011', (232, 234, 238), 700), CX, 560, s * .8, tb, rot=sw)
        la = window(t, T_LEATHER - .02, T_S2 + .05, .05, .2)
        if la > 0:
            used = True
            s = popin(t, T_LEATHER, .35)
            put(img, leather_badge(), CX, 520, s * .9, la, rot=4 * math.exp(-(t - T_LEATHER) * 3))
    elif sc == 1:
        ca = window(t, LS[6] - .05, LS[11] - .05, .25, .3)
        if ca > 0:
            used = True
            al = int(255 * ca)
            shake = math.sin(t * 70) * 6 * (1 - prog(t, T_EVERY, .4)) if T_EVERY <= t < T_EVERY + .4 else 0
            ox = shake
            panel(d, 70 + ox, 206, 850 + ox, 592, ca)
            d.text(470 + ox, 254, 'TOYOTA iQ', 34, (235, 236, 240, al))
            d.text(720 + ox, 254, 'CYGNET', 34, (190, 230, 205, al))
            d.line([(100 + ox, 286), (820 + ox, 286)], (70, 74, 84, al), 3)
            rows = [(370, 'ENGINE', '97 HP', '1.33 L', T_ENG, T_HP), (476, '0–62 MPH', '11.8 s', '', T_SPEED, T_SPEED + .25)]
            for y, lab, val, sub, t_lab, t_val in rows:
                if t < t_lab - .05: continue
                ra = min(ca, prog(t, t_lab - .05, .2))
                d.text(110 + ox, y, lab, 30, (170, 176, 190, int(255 * ra)), anchor='lm', path=FONT_X)
                for vx in ((470, 720) if sub else ()):
                    d.text(vx + ox, y - 22, sub, 26, (170, 176, 190, int(255 * ra)))
                if t >= t_val - .05:
                    s = popin(t, t_val, .3)
                    for vx in (470, 720):
                        d.text(vx + ox, y + 18 * (1 if sub else 0), val, 52 * max(s, .05), (255, 255, 255, int(255 * ca)))
                    ek = popin(t, t_val + .25, .3)
                    if ek > .05:
                        d.ell(595 + ox, y + (9 if sub else 0), 26 * ek, 26 * ek, GREEN + (al,))
                        d.text(595 + ox, y + (9 if sub else 0) + 1, '=', 44 * ek, (14, 40, 24, al))
            if t >= T_EVERY:
                s = popin(t, T_EVERY, .3)
                d.text(595 + ox, 548, 'SAME', 40 * max(s, .05), GREEN + (al,))
        # three "NEW" insets with leader lines to the Cygnet
        for i, (kind, tw, cx_, tx, ty) in enumerate((('grille', T_GRILLE, 170, 496, 810), ('lights', T_LIGHTS, 459, 523, 774),
                                                     ('leather', T_LEATH2, 748, 749, 728))):
            ia = window(t, tw - .05, T_S3 + .05, .08, .2)
            if ia <= 0: continue
            used = True
            s = popin(t, tw, .32)
            lk = prog(t, tw + .1, .2)
            if lk > 0:
                sx_, sy_ = cx_, 470 + 118
                d.line([(sx_, sy_), (sx_ + (tx - sx_) * lk, sy_ + (ty - sy_) * lk)], (255, 255, 255, int(230 * ia)), 5)
                d.ell(tx, ty, 9 * lk, 9 * lk, TAG + (int(255 * ia),), (30, 30, 30, int(255 * ia)), 3)
            put(img, inset(kind), cx_, 470, s, ia)
            d = D(img)
            if s > .3:
                d.rect(cx_ - 46, 330, cx_ + 46, 368, RED + (int(255 * ia),), r=10)
                d.text(cx_, 350, 'NEW', 28, (255, 255, 255, int(255 * ia)))
    elif sc == 2:
        # the "Why?" card, then a corner tag while the question is asked
        wk = window(t, T_S3 - .05, WHY1 + .3, .05, .3)
        if wk > 0:
            used = True
            d.rect(0, 0, W, H, (10, 12, 18, int(215 * wk)))
            s = 1 + 0.9 * (1 - oc(prog(t, T_S3 + .1, .18)))
            d.text(CX, 760, 'WHY?', 250 * s, TAG + (int(255 * wk),), stroke=10, sc=(20, 20, 26, int(255 * wk)))
            for i in range(12):                             # radiating ticks
                an = math.radians(i * 30 + (t - T_S3) * 20)
                r0, r1 = 230, 260 + 30 * math.sin(t * 9 + i)
                d.line([(CX + r0 * math.cos(an), 760 + r0 * math.sin(an)), (CX + r1 * math.cos(an), 760 + r1 * math.sin(an))],
                       TAG + (int(160 * wk),), 8)
        tk = window(t, WHY1 + .1, LE[12] + .4, .2, .3)
        if tk > 0:
            used = True
            d.rect(60, 120, 260, 190, TAG + (int(240 * tk),), r=16)
            d.text(160, 156, 'WHY?', 48, (24, 22, 20, int(255 * tk)))
        ck = window(t, T_CORRECT, T_S4 + .05, .05, .25)
        if ck > 0:
            used = True
            s = popin(t, T_CORRECT, .3)
            d.ell(740, 760, 74 * s, 74 * s, GREEN + (int(250 * ck),), (14, 40, 24, int(255 * ck)), 6)
            d.text(740, 764, '✓', 92 * s, (255, 255, 255, int(255 * ck)))
    else:
        fa = window(t, T_FTEN - .02, DUR + 1, .08, .1)
        if fa > 0:
            used = True
            s = popin(t, T_FTEN, .32)
            sw = math.sin((t - T_FTEN) * 6) * 5 * math.exp(-(t - T_FTEN) * 2)
            put(img, price_tag('FROM ABOUT £10,000', 'TOYOTA iQ · 2011', (232, 234, 238), 700), CX, 450, s * .9, fa, rot=sw)
    return img if used else None

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
        res.append(dict(words=c, s=c[0]['s'], e=DUR if i == len(out) - 1 else end))
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
    if T_S3 <= t < WHY1 + .1: return                       # "Why?" card owns the screen
    for ci, c in enumerate(CHUNKS):
        if c['s'] - 0.02 <= t < c['e']:
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
    ov = overlays(t)
    if ov is not None:
        ov = ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA')
        img.alpha_composite(ov)
    if BEAT[0] + .1 <= t < T_FINAL:                         # the beat: room dims, everyone waits
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.22 * io(prog(t, BEAT[0] + .1, .5)))
    if T_FINAL <= t < T_FINAL + .5:
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.25 * (1 - prog(t, T_FINAL, .5)))
    if t >= T_FTEN:                                         # ending vignette
        k_ = io(prog(t, T_FTEN, 1.5)) * .35
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
    outside = lpf(rng.standard_normal(n), 300) * 1.0 * (0.7 + 0.3 * np.sin(T_ * .7)) + lpf(rng.standard_normal(n), 25) * .03
    board = lpf(rng.standard_normal(n), 90) * 0.07 + 0.006 * np.sin(2 * np.pi * 60 * T_) + 0.003 * np.sin(2 * np.pi * 120 * T_)
    bed = room * (env(-1, T_S2) + env(T_S4, DUR + 1)) + outside * env(T_S2, T_S3) + board * env(T_S3, T_S4)
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def tick(): return click(4200, 5200, .03) * .5
    def chirp():
        tt = np.arange(int(SR * .12)) / SR
        return np.sin(2 * np.pi * np.cumsum(3200 + 1400 * np.sin(tt * 60)) / SR) * np.exp(-tt * 30) * .3
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
    cues = []
    def add(t0, s, vol): cues.append((int(t0 * SR), s * vol))
    for k_ in range(4): add(0.02 + k_ * 0.3, step(), .5)
    add(T_TOYOTA0 + .05, sfx.stamp(), .55)
    add(T_THIRTY - .05, sfx.whoosh(), .3); add(T_POUNDS + .1, sfx.cha_ching(), .35)
    add(T_TEN, sfx.pop(), .4); add(T_TEN + .05, sfx.buzzer(), .12)
    add(T_LEATHER, sfx.sparkle(), .35)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    add(T_S2 + .4, sfx.vroom(), .10)
    for k_ in range(3): add(T_S2 + .9 + k_ * 4.1, chirp(), .5)
    add(T_ENG, sfx.pop(), .3); add(T_HP + .25, sfx.ding(), .16)
    add(T_SPEED, sfx.pop(), .3); add(T_SPEED + .5, sfx.ding(1760), .16)
    add(T_EVERY, sfx.boom(.6), .25)
    for tw in (T_GRILLE, T_LIGHTS, T_LEATH2): add(tw, sfx.pop(), .35)
    add(T_S3 + .1, sfx.boom(), .45); add(T_S3 + .1, sfx.thump(), .5)
    for i in range(2): add(T_EMIS + i * .15, sfx.pop(), .25)
    add(T_HIGH, sfx.buzzer(), .14)
    add(T_BOUGHT, sfx.fall(), .3); add(T_BOUGHT + .35, sfx.thump(), .3); add(T_BOUGHT + .3, sfx.slide_down(), .2)
    add(T_CORRECT, sfx.ding(), .25)
    for k_ in range(3): add(T_S4 + .05 + k_ * .42, step(), .3)
    add(LS[16] + .3, sfx.coin_clink(), .2)
    for k_ in range(3): add(BEAT[0] + .25 + k_ * .4, tick(), .6)
    add(T_FINAL - .02, sting(), .8); add(T_FTEN, sfx.stamp(), .3)
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
    if mode == 'still':
        load_mouth(sys.argv[4] if len(sys.argv) > 4 else VOICE_CACHE)
        Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif mode == 'meta':
        json.dump(dict(captions=caption_boxes(), onscreen=ONSCREEN, duration=DUR, size=[W, H], fps=FPS),
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
