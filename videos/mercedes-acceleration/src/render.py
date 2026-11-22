"""Mercedes 'Acceleration Increase' skit: showroom -> dyno cell -> store screen -> drag strip -> backlash room -> showroom.
Flat-vector style, 1080x1920 @30. Built on bmw-heated-seats/src/render.py: same buyer, caption system, camera, whip pans
and mix chain; a new salesman (silver hair, moustache, EQ-blue tie). Real EQE 350 4MATIC photos (Wikimedia Commons,
CC BY-SA 4.0, Damian B Oh) and the three-pointed star drawn to the real logo's geometry. One background oddity in every
scene, never mentioned: a cow in a racing helmet.
Usage: python render.py video VOICE.wav OUT.mp4 | python render.py still T OUT.png [VOICE] | python render.py meta OUT.json"""
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
DUR = round(WORDS[-1]['e'] + 1.7, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/mercedes-acceleration/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
def word_e(line, txt, nth=0):
    hits = [w['e'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
T_WHAT, T_EQE, T_288 = word_t(1, 'WHAT'), word_t(2, 'EQE'), word_t(2, '288')
T_S2 = word_t(2, 'The') - 0.3              # scene cuts (whip pans)
T_349, T_UNLOCK = word_t(2, '349'), word_t(3, 'unlock')
T_S3 = LS[4] - 0.42
T_1200, T_AYEAR, T_YEAR2 = LS[4], word_t(4, 'A'), LS[5]
T_RENEW, T_STAY = LS[6], word_e(6, 'year,')
T_S4 = LS[7] - 0.42
T_61, T_60 = LS[8], word_t(8, '6.0')
T_51, T_LESS = word_t(8, '5.1'), LS[9]
T_20, T_PERYEAR = word_t(10, '$20'), word_t(10, 'Per', 1)
T_85 = word_t(11, 'eighty')
T_S5 = LS[12] - 0.45
T_NOV, T_FURIOUS = word_t(12, 'November'), word_t(12, 'furious')
T_GOOD, T_DRIVE, T_NOBODY = LS[13], word_t(14, 'Drive'), word_t(14, 'nobody')
T_NOBODY2, T_PRICE, T_ONETIME = LS[15], word_t(16, 'price'), word_t(16, 'one-time')
T_S6 = LS[17] - 0.42
T_TECH, T_OVER = LS[18], word_t(18, 'overcharged')
BEAT = (LE[18], LS[19])
T_FINAL = LS[19]
T_CARD = word_t(19, 'Yes') - 0.1           # final card (the spoken question's last words and the tail)
SCENES = [0.0, T_S2, T_S3, T_S4, T_S5, T_S6]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
_fr = np.random.default_rng(11)            # backlash bubbles (shared by picture and sound)
BUBBLES = sorted(T_S5 + .25 + _fr.uniform(0, T_DRIVE - T_S5 - .6, 9))

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

# ================================================================ emblems (hand-drawn, generic, not logo files)
GOLD, GOLD2, INK = (214, 176, 84), (150, 116, 40), (16, 16, 18)
CHROME, CHROME2 = (214, 220, 228), (120, 128, 140)
VWBLUE, P_RED = (22, 60, 130), (190, 24, 32)
ORANGE = (246, 146, 20)
def shield(d, cx, cy, s=1.0, col=GOLD, fill=INK):
    """Generic pointed shield (gold rim, dark field, gold chevron) for the Italian brand."""
    pts = [(cx - 60 * s, cy - 70 * s), (cx + 60 * s, cy - 70 * s), (cx + 58 * s, cy + 6 * s), (cx + 36 * s, cy + 48 * s),
           (cx, cy + 76 * s), (cx - 36 * s, cy + 48 * s), (cx - 58 * s, cy + 6 * s)]
    d.poly(pts, fill, col, max(2, 8 * s))
    d.line([(cx - 34 * s, cy + 18 * s), (cx, cy - 30 * s), (cx + 34 * s, cy + 18 * s)], col, max(2, 10 * s))
    d.rect(cx - 46 * s, cy - 58 * s, cx + 46 * s, cy - 46 * s, col, r=3 * s)

def crest(d, cx, cy, s=1.0):
    """Generic quartered crest (red/gold) for the Stuttgart brand."""
    d.poly([(cx - 50 * s, cy - 60 * s), (cx + 50 * s, cy - 60 * s), (cx + 48 * s, cy + 10 * s), (cx, cy + 66 * s),
            (cx - 48 * s, cy + 10 * s)], (30, 24, 16), GOLD, max(2, 7 * s))
    for (x0, y0, c) in ((-38, -46, P_RED), (4, -46, GOLD), (-38, 2, GOLD), (4, 2, P_RED)):
        d.rect(cx + x0 * s, cy + y0 * s, cx + (x0 + 34) * s, cy + (y0 + 38) * s, c, r=2 * s)

def wings(d, cx, cy, s=1.0, col=CHROME):
    """Generic winged badge for the British brand."""
    for side in (-1, 1):
        for i in range(4):
            y = cy - 18 * s + i * 12 * s
            d.line([(cx + side * 30 * s, y), (cx + side * (130 - i * 24) * s, y - 12 * s + i * 3 * s)], col, max(2, 7 * s))
    d.ell(cx, cy, 30 * s, 30 * s, (20, 34, 28), col, max(2, 6 * s))

def roundel(d, cx, cy, s=1.0):
    """Plain blue roundel for the Wolfsburg brand."""
    d.ell(cx, cy, 60 * s, 60 * s, VWBLUE, (240, 244, 250), max(2, 8 * s))
    d.ell(cx, cy, 38 * s, 38 * s, None, (240, 244, 250), max(2, 5 * s))

def bmw_badge(d, cx, cy, s=1.0):
    """Hand-drawn BMW-style roundel: black ring, silver rims, blue/white quarters."""
    d.ell(cx, cy, 60 * s, 60 * s, (18, 18, 22), (200, 206, 214), max(1, 5 * s))
    r = 36 * s
    d.ell(cx, cy, r, r, (250, 250, 252))
    for a0 in (270, 90):                                   # blue quarters: upper right and lower left
        d.d.pieslice(d.box(cx - r, cy - r, cx + r, cy + r), a0, a0 + 90, fill=(28, 105, 190))
    d.ell(cx, cy, r, r, None, (200, 206, 214), max(1, 3 * s))
    for i, ch in enumerate('BMW'):
        ang = math.radians(-140 + i * 50)
        d.text(cx + 48 * s * math.cos(ang), cy + 48 * s * math.sin(ang), ch, max(6, 15 * s), (240, 242, 246))

EQ_BLUE = (0, 160, 222)
def mb_star(d, cx, cy, s=1.0, col=CHROME, ring=True):
    """Mercedes-Benz three-pointed star in a ring, drawn to the real logo's proportions (two-tone chrome arms)."""
    R = 60 * s
    dark = tuple(int(c * .62) for c in col[:3])
    if ring:
        d.ell(cx, cy, R, R, None, col, max(1.5, 6.5 * s))
    tip, rin = R * (.93 if ring else 1.0), R * .17
    for k in range(3):
        a = math.radians(-90 + 120 * k)
        T = (cx + tip * math.cos(a), cy + tip * math.sin(a))
        Lp = (cx + rin * math.cos(a - math.radians(60)), cy + rin * math.sin(a - math.radians(60)))
        Rp = (cx + rin * math.cos(a + math.radians(60)), cy + rin * math.sin(a + math.radians(60)))
        d.poly([(cx, cy), Lp, T], col)
        d.poly([(cx, cy), T, Rp], dark)

def mb_emb(d, cx, cy, s=1.0): mb_star(d, cx, cy, s * 1.05, (196, 200, 208))
# ================================================================ cars (side profile, front to the left)
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
URUS_CTRL = [(.012, .17), (0.0, .34), (.006, .47), (.06, .55), (.20, .60), (.33, .64), (.47, .93), (.62, .965), (.79, .90),
             (.93, .74), (1.0, .69), (1.0, .43), (.99, .19), (.86, .15), (.5, .16), (.14, .15)]
TOUAREG_CTRL = [(.014, .17), (0.0, .36), (.006, .56), (.05, .63), (.20, .67), (.33, .71), (.46, .97), (.63, 1.0), (.84, .97),
                (.96, .86), (1.0, .74), (1.0, .46), (.99, .20), (.86, .16), (.5, .17), (.14, .16)]
CAYENNE_CTRL = [(.012, .17), (0.0, .35), (.006, .50), (.06, .58), (.20, .63), (.33, .67), (.47, .95), (.62, .975), (.80, .90),
                (.94, .76), (1.0, .68), (1.0, .43), (.99, .19), (.86, .15), (.5, .16), (.14, .15)]
BENTAYGA_CTRL = [(.014, .18), (0.0, .40), (.008, .60), (.06, .66), (.20, .69), (.33, .72), (.45, .98), (.62, 1.01), (.84, .99),
                 (.97, .88), (1.0, .76), (1.0, .46), (.99, .20), (.86, .16), (.5, .17), (.14, .16)]
BMW_CTRL = [(.012, .17), (0.0, .34), (.006, .50), (.06, .58), (.20, .62), (.33, .66), (.47, .94), (.60, .96), (.76, .89),
            (.90, .76), (1.0, .66), (1.0, .43), (.99, .19), (.86, .15), (.5, .16), (.14, .15)]
EQE_CTRL = [(.012, .17), (0.0, .31), (.008, .43), (.07, .49), (.18, .53), (.29, .58), (.42, .79), (.56, .835), (.72, .79),
            (.87, .65), (.985, .555), (1.0, .38), (.99, .19), (.86, .15), (.5, .16), (.14, .15)]
CARS = {
    'eqe': dict(ctrl=EQE_CTRL, col=((40, 42, 50), (118, 124, 140), (10, 10, 14)), rim=(188, 192, 200), n=5, dbl=True, cal=(40, 40, 46)),   # Obsidian Black, as in the photos
    'bmw': dict(ctrl=BMW_CTRL, col=((30, 40, 62), (84, 100, 132), (12, 16, 26)), rim=(40, 42, 48), n=5, dbl=True, cal=(28, 105, 190)),   # colours (base, highlight, low) follow the user's photos
    'touareg': dict(ctrl=TOUAREG_CTRL, col=((112, 116, 122), (176, 180, 186), (62, 66, 72)), rim=(34, 34, 38), n=5, dbl=True, cal=(40, 40, 46)),
    'cayenne': dict(ctrl=CAYENNE_CTRL, col=((232, 232, 230), (255, 255, 255), (166, 168, 174)), rim=(40, 40, 46), n=5, dbl=True, cal=(60, 60, 66)),
    'bentayga': dict(ctrl=BENTAYGA_CTRL, col=((168, 176, 188), (226, 230, 238), (98, 106, 118)), rim=(150, 154, 162), n=10, dbl=False, cal=(40, 40, 46)),
    'urus': dict(ctrl=URUS_CTRL, col=(ORANGE, (255, 196, 96), (168, 84, 6)), rim=(34, 34, 38), n=5, dbl=True, cal=ORANGE),
}

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

def suv(d, x0, ground, L, kind):
    """Touareg / Cayenne / Bentayga / Urus side profile (front to the left): same wheelbase, different skins."""
    S = CARS[kind]
    Hh = L * .42
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    lambo = kind == 'urus'
    base, hi, lo = S['col']
    sill = (22, 22, 26)
    d.ell(x0 + L * .5, ground + 4, L * .58, 15, (0, 0, 0, 90))
    body = spline([P(u, v) for u, v in S['ctrl']], 8)
    shade(d, body, hi, lo, ground - .98 * Hh, ground - .2 * Hh)
    clad = ((40, 40, 46), sill) if kind != 'bentayga' else (lo, tuple(int(c * .7) for c in lo))
    shade(d, spline([P(.02, .17), P(.5, .18), P(.98, .17), P(.99, .29), P(.5, .27), P(.01, .28)], 6), clad[0], clad[1],
          ground - .29 * Hh, ground - .16 * Hh)
    d.line(spline([P(.04, .50), P(.30, .55), P(.62, .57), P(.97, .60)], 8, closed=False), hi + (210,), 3)   # shoulder light
    if lambo:                                            # sharp Y crease along the door
        d.line([P(.30, .44), P(.52, .40), P(.80, .44)], lo, 4)
        d.line([P(.52, .40), P(.62, .30)], lo, 3)
    elif kind == 'touareg':                              # one crisp character line
        d.line([P(.05, .50), P(.97, .55)], lo, 3)
    elif kind == 'eqe':                                  # soft lower crease, no hard lines
        d.line(spline([P(.08, .36), P(.50, .34), P(.90, .38)], 6, closed=False), hi + (120,), 3)
    elif kind == 'bmw':                                  # rising swage line + air breather
        d.line([P(.08, .46), P(.97, .56)], hi + (200,), 3)
        d.poly([P(.24, .44), P(.30, .45), P(.29, .40), P(.24, .40)], (16, 18, 24))
    elif kind == 'cayenne':                              # rear haunch
        d.arc(*P(.80, .30), L * .15, Hh * .30, 200, 340, hi + (220,), 4)
    else:                                                # haunch line + chrome wing vent
        d.line(spline([P(.60, .50), P(.80, .56), P(.97, .58)], 6, closed=False), lo, 4)
        d.rect(*P(.26, .46), *P(.31, .41), CHROME, r=3)
    r = Hh * .25
    for u in (.17, .80):
        wx, wy = P(u, 0)[0], ground - r
        if lambo:                                        # angular, hexagonal arches
            hx = [P(u - .12, .17), P(u - .10, .40), P(u - .04, .50), P(u + .04, .50), P(u + .10, .40), P(u + .12, .17)]
            d.poly(hx, (14, 14, 16))
            d.line(hx, (30, 30, 34), 9)
        else:
            d.chord(wx, wy, r * 1.22, r * 1.22, 180, 360, (14, 14, 16))
            d.rect(wx - r * 1.22, wy - 2, wx + r * 1.22, ground - 4, (14, 14, 16))
            d.arc(wx, wy, r * 1.26, r * 1.26, 190, 350, (30, 30, 34), 7)
    d.poly(body, None, (24, 26, 34), 5)
    # glasshouse
    if lambo:
        gh = [P(.35, .66), P(.47, .90), P(.62, .925), P(.775, .865), P(.865, .74), P(.85, .67)]
    elif kind == 'eqe':                                  # one-bow arc from the bonnet to the tail
        gh = spline([P(.30, .60), P(.43, .775), P(.57, .815), P(.72, .77), P(.86, .645), P(.80, .60)], 5)
    elif kind == 'bmw':                                  # sloping coupe roof, Hofmeister kink
        gh = spline([P(.35, .70), P(.47, .91), P(.60, .93), P(.74, .87), P(.80, .79), P(.77, .70)], 5)
    elif kind == 'cayenne':
        gh = spline([P(.35, .70), P(.47, .91), P(.62, .935), P(.78, .87), P(.88, .76), P(.86, .71)], 5)
    else:
        top = .955 if kind == 'bentayga' else .945
        gh = spline([P(.35, .74), P(.46, top - .02), P(.63, top), P(.83, top - .03), P(.925, .85), P(.91, .76)], 5)
    shade(d, gh, (86, 106, 130), (16, 20, 30), ground - .94 * Hh, ground - .66 * Hh)
    d.poly(gh, None, (20, 22, 28), 4)
    if kind == 'eqe':
        d.poly([P(.37, .63), P(.40, .63), P(.46, .76), P(.43, .76)], (255, 255, 255, 50))
        d.poly([P(.585, .60), P(.605, .60), P(.61, .81), P(.59, .81)], (20, 20, 24))
    else:
        d.poly([P(.40, .72), P(.43, .72), P(.50, .88), P(.47, .88)], (255, 255, 255, 50))
        d.poly([P(.595, .70), P(.62, .70), P(.625, .93), P(.60, .93)], (20, 20, 24))
    # door cut, handle, mirror
    d.line([P(.34, .64), P(.31, .22)], lo, 3)
    d.line([P(.61, .66), P(.62, .21)], lo, 3)
    d.rect(*P(.52, .56), *P(.57, .535), CHROME if kind in ('touareg', 'bentayga') else (30, 30, 34), r=3)
    mv = -.09 if kind == 'eqe' else 0                    # the EQE's mirror sits lower, on the door
    d.poly(spline([P(.355, .72 + mv), P(.41, .74 + mv), P(.41, .80 + mv), P(.36, .80 + mv)], 4), (24, 24, 28) if kind != 'bentayga' else base, (24, 26, 34), 3)
    if lambo:
        d.poly([P(-.004, .20), P(.10, .22), P(.06, .40), P(.0, .42)], (18, 18, 22))           # big intake
        d.poly([P(.015, .44), P(.12, .52), P(.20, .555), P(.11, .47)], (24, 24, 28), (24, 26, 34), 3)
        d.line([P(.03, .46), P(.10, .505), P(.16, .53)], (250, 250, 255), 4)                  # Y headlight
        d.line([P(.10, .505), P(.09, .45)], (250, 250, 255), 4)
        d.poly([P(.94, .64), P(1.0, .62), P(1.0, .58), P(.95, .60)], (210, 24, 30))          # thin tail light
        d.poly([P(.90, .74), P(.99, .72), P(.99, .70), P(.92, .715)], (26, 26, 30))          # roof spoiler lip
        shield(d, *P(.035, .50), L * .00028, GOLD, INK)
    elif kind == 'touareg':
        d.poly([P(-.004, .20), P(.08, .21), P(.06, .29), P(0, .29)], (20, 20, 24))            # lower intake
        d.poly([P(-.004, .31), P(.05, .33), P(.05, .55), P(-.002, .53)], (24, 26, 30), (60, 62, 68), 3)
        for v in (.38, .44, .50):                                                              # chrome grille bars
            d.line([P(0, v), P(.05, v + .01)], CHROME, 3)
        d.poly([P(.02, .56), P(.15, .60), P(.17, .585), P(.05, .545)], (232, 238, 246), (24, 26, 34), 3)
        d.poly([P(.95, .63), P(1.0, .62), P(1.0, .58), P(.95, .59)], (200, 24, 30))
    elif kind == 'eqe':
        d.poly([P(-.004, .20), P(.10, .22), P(.08, .29), P(0, .30)], (18, 18, 22))            # lower intake
        d.poly(spline([P(-.004, .30), P(.03, .32), P(.036, .46), P(0, .45)], 3), (12, 12, 16), (70, 72, 80), 3)   # black panel grille
        for i in range(3):
            for j in range(2): d.ell(*P(.008 + j * .014, .34 + i * .04), 2, 2, (150, 154, 162))   # star-pattern dots
        d.poly([P(.02, .46), P(.15, .52), P(.16, .50), P(.04, .445)], (232, 238, 246), (24, 26, 34), 3)   # slim lamp
        d.line([P(.05, .465), P(.14, .505)], (150, 210, 255), 3)
        d.poly([P(.94, .56), P(.995, .545), P(.995, .52), P(.95, .53)], (210, 24, 34))       # tail light
        d.line([P(.90, .555), P(.995, .535)], (255, 60, 60, 160), 2)
        mb_star(d, *P(.022, .385), L * .00032, (220, 224, 232))
    elif kind == 'bmw':
        d.poly([P(-.004, .20), P(.09, .22), P(.07, .36), P(0, .38)], (18, 18, 22))            # lower intake
        d.poly(spline([P(-.004, .38), P(.035, .40), P(.04, .58), P(.0, .57)], 3), (16, 16, 20), CHROME, 4)   # kidney grille
        for v in (.43, .48, .53):
            d.line([P(.003, v), P(.034, v + .004)], (70, 74, 82), 2)
        d.poly([P(.03, .56), P(.15, .60), P(.16, .58), P(.05, .545)], (232, 238, 246), (24, 26, 34), 3)   # slim lamp
        d.line([P(.06, .565), P(.13, .585)], (140, 200, 255), 3)
        d.poly([P(.93, .64), P(1.0, .63), P(1.0, .57), P(.97, .60), P(.94, .60)], (200, 24, 30))   # L-shaped tail light
        bmw_badge(d, *P(.025, .615), L * .00018)
    elif kind == 'cayenne':
        d.poly([P(-.004, .20), P(.09, .22), P(.07, .38), P(0, .40)], (18, 18, 22))            # big intake
        d.ell(*P(.075, .53), L * .04, Hh * .055, (232, 238, 246), (24, 26, 34), 3)             # oval lamp, four dots
        for i in range(4):
            d.ell(P(.06, .53)[0] + (i % 2) * L * .03, P(.06, .53)[1] + (i // 2 - .5) * Hh * .045, 3, 3, (150, 200, 255))
        d.line([P(.935, .655), P(1.0, .64)], (210, 24, 30), 6)                                # tail light bar
    else:
        g = [P(-.006, .24), P(.035, .25), P(.04, .58), P(0, .57)]                             # tall upright grille
        d.poly(g, (30, 32, 36), CHROME, 5)
        for v in (.30, .36, .42, .48, .54):
            d.line([P(.004, v), P(.034, v + .004)], (90, 94, 100), 2)
        d.ell(*P(.07, .56), L * .03, L * .03, (236, 240, 248), CHROME, 3)                      # round lamps
        d.ell(*P(.125, .575), L * .019, L * .019, (236, 240, 248), CHROME, 3)
        d.ell(*P(.97, .62), L * .018, Hh * .05, (200, 24, 30))
    for u in (.17, .80):
        wheel(d, P(u, 0)[0], ground - r, r, S, lambo)

# ---- generic background car (for the one parked on the ceiling)
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

@lru_cache(None)
def car_layer(kind, L):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .62) * K), (0, 0, 0, 0))
    suv(D(img, ox=-L * .1, oy=-L * .56), 0, 0, L, kind)
    return img
def paste_car(img, kind, x0, ground, L):
    c = car_layer(kind, L)
    img.paste(c, (int((x0 - L * .1) * K), int((ground - L * .56) * K)), c)

# ================================================================ background oddity (comment bait, never mentioned)
# A cow in a full-face racing helmet, in the background of every scene, calmly doing something different in each.
CEIL = 84
COW_W, COW_K, HELM, HELM2 = (248, 248, 244), (28, 28, 32), (214, 30, 40), (150, 16, 24)
def cow(d, x, fy, t, s=1.0, face=-1, visor=0.0, chew=True, wave=0.0):
    """Side-view cow, facing left (face=-1) or right (+1), feet at fy. visor 0 shut .. 1 flipped up."""
    f = face
    by = fy - 104 * s
    for i, lx in enumerate((-52, -30, 34, 56)):                    # legs (far pair darker)
        c = (214, 214, 210) if i in (1, 3) else COW_W
        d.rect(x + f * lx * s - 8 * s, by + 18 * s, x + f * lx * s + 8 * s, fy - 8 * s, c, r=4 * s, ol=OL, w=3 * s)
        d.rect(x + f * lx * s - 9 * s, fy - 14 * s, x + f * lx * s + 9 * s, fy, COW_K, r=3 * s)
    sw = math.sin(t * 2.6) * 16                                     # tail swish
    d.line([(x - f * 80 * s, by - 18 * s), (x - f * (100 + sw * .3) * s, by + 20 * s), (x - f * (96 + sw) * s, by + 58 * s)], OL, 4 * s)
    d.ell(x - f * (96 + sw) * s, by + 62 * s, 7 * s, 10 * s, COW_K)
    d.ell(x, by, 86 * s, 50 * s, COW_W, OL, 4 * s)                  # body
    d.ell(x - f * 34 * s, by - 14 * s, 26 * s, 20 * s, COW_K)       # patches
    d.ell(x + f * 28 * s, by + 16 * s, 20 * s, 15 * s, COW_K)
    d.ell(x - f * 60 * s, by + 14 * s, 12 * s, 10 * s, COW_K)
    d.ell(x - f * 30 * s, by + 46 * s, 14 * s, 9 * s, (240, 170, 180), OL, 2 * s)   # udder
    hx, hy = x + f * 96 * s, by - 44 * s + (2 * s * math.sin(t * 9) if chew else 0)
    d.ell(hx + f * 34 * s, hy + 26 * s, 24 * s, 18 * s, (240, 176, 182), OL, 3 * s)  # muzzle below the visor
    d.ell(hx + f * 40 * s, hy + 24 * s, 3 * s, 3 * s, OL); d.ell(hx + f * 28 * s, hy + 24 * s, 3 * s, 3 * s, OL)
    d.ell(hx, hy, 42 * s, 38 * s, HELM, OL, 4 * s)                   # helmet
    d.chord(hx, hy, 42 * s, 38 * s, 300 if f < 0 else 200, 340 if f < 0 else 240, HELM2)
    d.line([(hx - f * 34 * s, hy - 18 * s), (hx + f * 10 * s, hy - 36 * s)], (250, 250, 250), 5 * s)   # white stripe
    vy = hy - 6 * s - visor * 22 * s                                 # visor slides up
    d.poly([(hx + f * 8 * s, vy - 10 * s), (hx + f * 42 * s, vy - 6 * s), (hx + f * 40 * s, vy + 16 * s), (hx + f * 6 * s, vy + 14 * s)],
           (40, 46, 60) if visor < .5 else (60, 70, 90, 140), OL, 3 * s)
    if visor > .5:                                                   # eye under a raised visor
        d.ell(hx + f * 24 * s, hy + 4 * s, 6 * s, 7 * s, (255, 255, 255), OL, 2 * s); d.ell(hx + f * 26 * s, hy + 5 * s, 3 * s, 3 * s, OL)
    d.line([(hx - f * 6 * s, hy + 30 * s), (hx + f * 12 * s, hy + 40 * s)], (40, 40, 44), 3 * s)   # chin strap
    if wave:                                                         # one front hoof raised (the slow wave)
        a_ = math.radians(-70 + 25 * math.sin(t * 5))
        sx_, sy_ = x + f * 60 * s, by + 10 * s
        d.line([(sx_, sy_), (sx_ + f * 70 * s * math.cos(a_), sy_ + 70 * s * math.sin(a_))], COW_W, 16 * s)
        d.ell(sx_ + f * 70 * s * math.cos(a_), sy_ + 70 * s * math.sin(a_), 9 * s, 9 * s, COW_K)
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

def showroom_life(img, t, sc):
    if sc == 0:                                             # showroom: receptionist on the phone, colleague with coffee
        reception(img, t, True)
        x = 960 - 130 * t
        if -80 < x < 1000:
            npc(img, x, 952, .34, NPC['walker'], walkst(t, 9, lp='rest', rp=(60, 210), prop={'rpose': 'cup'}, look=-1))
        cow(D(img), 905, 1000, t, .92, face=-1, visor=0.0)
    else:                                                   # back again: receptionist typing, the cow waves, visor up
        reception(img, t, False)
        cow(D(img), 905, 1000, t, .92, face=-1, visor=io(prog(t, T_S6 + .6, .4)), wave=1.0 if t > T_OVER else 0.0)

# ---- scene 2: the dyno cell (gauge locked between 288 and 349)
G_C, G_R = (CX, 300), 178
HP_MAX = 400
def hp_ang(hp): return 135 + 270 * hp / HP_MAX            # PIL degrees, clockwise from 3 o'clock

@lru_cache(None)
def bg_dyno():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (52, 56, 64), (34, 37, 44)), grad((H - WALL_Y) * K, W * K, (96, 98, 104), (132, 134, 140))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (24, 26, 30))
    for x in range(-40, W, 170):                            # acoustic wall panels
        d.rect(x + 10, 110, x + 160, WALL_Y - 70, (60, 64, 72), r=6)
        for yy in range(130, WALL_Y - 90, 26):
            d.line([(x + 24, yy), (x + 146, yy)], (48, 52, 60), 2)
    for i, x in enumerate(range(-60, W + 60, 60)):           # hazard stripe skirting
        d.poly([(x, WALL_Y - 46), (x + 30, WALL_Y - 46), (x + 60, WALL_Y - 4), (x + 30, WALL_Y - 4)], (240, 190, 30))
    d.rect(0, WALL_Y - 4, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (150, 152, 158), 2)
    cx, cy = G_C                                            # the big horsepower gauge
    d.ell(cx, cy, G_R + 34, G_R + 34, (16, 18, 22), (120, 126, 136), 8)
    d.arc(cx, cy, G_R - 14, G_R - 14, hp_ang(0), hp_ang(HP_MAX), (70, 76, 88), 22)
    for hp in range(0, HP_MAX + 1, 25):
        a = math.radians(hp_ang(hp)); r0 = G_R - (46 if hp % 100 == 0 else 34)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + (G_R - 26) * math.cos(a), cy + (G_R - 26) * math.sin(a))],
               (210, 214, 222), 5 if hp % 100 == 0 else 3)
    mb_star(d, cx, cy - 78, .36, (200, 204, 212))
    d.text(cx, cy + 128, 'HP', 34, (150, 156, 168), path=FONT_X)
    for xr in (CX - 220, CX - 150, CX + 150, CX + 220):     # dyno rollers set in the floor
        d.rect(xr - 40, 892, xr + 40, 912, (40, 42, 46), r=8)
    return img

def dyno_life(img, t):
    d = D(img); cx, cy = G_C
    lock = prog(t, T_349 - .05, .3)
    if lock > 0:                                            # locked band 288..349, hatched red
        d.arc(cx, cy, G_R - 14, G_R - 14, hp_ang(288), hp_ang(288 + 61 * oc(lock)), (220, 40, 52), 22)
        if lock >= 1:
            for hp in range(292, 349, 9):
                a = math.radians(hp_ang(hp))
                d.line([(cx + (G_R - 25) * math.cos(a), cy + (G_R - 25) * math.sin(a)),
                        (cx + (G_R - 3) * math.cos(a + .03), cy + (G_R - 3) * math.sin(a + .03))], (120, 16, 24), 3)
        a = math.radians(hp_ang(318)); px, py = cx + (G_R + 70) * math.cos(a), cy + (G_R + 70) * math.sin(a)
        s_ = popin(t, T_349, .3)
        d.rect(px - 24 * s_, py - 6 * s_, px + 24 * s_, py + 30 * s_, (236, 190, 40), r=5, ol=OL, w=3)       # padlock
        d.arc(px, py - 6 * s_, 15 * s_, 18 * s_, 180, 360, (200, 204, 212), 6)
    hp = 288 * oc(prog(t, T_S2 + .1, .9))                   # needle sweeps up to 288
    if t > T_349:                                           # tries for more, bounces off the lock
        hp = 288 + 12 * abs(math.sin((t - T_349) * 7)) * math.exp(-(t - T_349) * 1.4)
    if T_UNLOCK <= t:
        hp += 3 * math.sin(t * 40) * math.exp(-(t - T_UNLOCK) * 3)
    a = math.radians(hp_ang(hp))
    d.line([(cx - 30 * math.cos(a), cy - 30 * math.sin(a)), (cx + (G_R - 40) * math.cos(a), cy + (G_R - 40) * math.sin(a))], (255, 70, 60), 9)
    d.ell(cx, cy, 22, 22, (30, 32, 38), (200, 204, 212), 4)
    d.text(cx, cy + 80, f'{int(round(hp))}' if t < T_349 else '288', 56, (255, 255, 255))
    paste_car(img, 'eqe', CX - 260, 892, 520)              # the car on the rollers
    d = D(img)
    if t > T_S2 + .2:                                       # roller spin streaks
        for xr in (CX - 220, CX - 150, CX + 150, CX + 220):
            ph = (t * 9 + xr) % 1
            d.line([(xr - 34 + 60 * ph, 898), (xr - 20 + 60 * ph, 898)], (200, 204, 212, 160), 3)
    cow(d, 905, 1000, t, .9, face=-1)                     # the cow, reading the dyno printout
    d.rect(736, 880, 774, 926, (250, 250, 246), r=3, ol=OL, w=2)
    for k in range(3): d.line([(742, 890 + k * 9), (768, 890 + k * 9)], (150, 150, 160), 2)

# ---- scene 3: the store screen
@lru_cache(None)
def bg_store():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (236, 238, 242), (216, 220, 226)), grad((H - WALL_Y) * K, W * K, (40, 42, 48), (70, 72, 78))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (240, 242, 246)); d.rect(0, CEIL - 6, W, CEIL, (200, 204, 210))
    for x in range(-40, W, 170):
        d.rect(x + 8, 110, x + 160, WALL_Y - 40, (228, 230, 236))
    d.rect(52, 118, 868, 600, (12, 14, 18), r=22)                       # the big wall screen
    d.rect(64, 130, 856, 588, (18, 22, 30), r=14)
    d.rect(64, 130, 856, 190, (26, 30, 40), r=14)
    mb_star(d, 100, 160, .3, (210, 214, 222))
    d.text(130, 160, 'STORE', 30, (220, 228, 240), anchor='lm', path=FONT_X)
    d.text(110, 236, 'Acceleration Increase', 50, (255, 255, 255), anchor='lm')
    d.text(110, 290, 'EQE 350 4MATIC', 30, (150, 160, 178), anchor='lm', path=FONT_X)
    d.rect(0, WALL_Y - 8, W, WALL_Y, EQ_BLUE)
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (90, 92, 98), 2)
    return img

def store_life(img, t):
    d = D(img)
    up = io(prog(t, T_1200 - .05, .35)) * (1 - io(prog(t, T_STAY, .35)))   # toggle: 288 -> 349 on paying, back on 'stay'
    tx, ty = 170, 380
    d.rect(tx - 70, ty - 36, tx + 70, ty + 36, mix((110, 116, 128), EQ_BLUE, up), r=36)
    d.ell(tx - 34 + 68 * up, ty, 30, 30, (255, 255, 255))
    hp = '349 hp' if up > .5 else '288 hp'
    d.text(tx + 110, ty, hp, 56, (255, 255, 255) if up > .5 else (170, 176, 190), anchor='lm')
    if t >= T_1200 - .05:
        k_ = popin(t, T_1200 - .05, .3)
        d.text(110, 480, '$1,200', 76 * k_, (255, 255, 255), anchor='lm')
    if t >= T_AYEAR - .05:
        d.text(430, 490, '/ year', 44 * popin(t, T_AYEAR - .05, .3), TAG, anchor='lm', path=FONT_X)
        d.text(112, 548, 'plus tax  ·  renews annually', 26, (150, 160, 178), anchor='lm', path=FONT_X)
    if T_RENEW <= t:                                         # renewal arrows spin on 'Renew'
        a0 = (t - T_RENEW) * 320
        d.arc(770, 300, 56, 56, a0, a0 + 280, EQ_BLUE, 12)
        a = math.radians(a0 + 280)
        d.ell(770 + 56 * math.cos(a), 300 + 56 * math.sin(a), 12, 12, EQ_BLUE)
    cow(d, 905, 1000, t, .9, face=-1, chew=False)          # the cow, in the queue with a credit card in its mouth
    d.rect(752, 893, 792, 913, (24, 24, 30), r=4, ol=(200, 170, 90), w=2)

# ---- scene 4: the drag strip (night)
@lru_cache(None)
def bg_strip():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (14, 18, 40), (44, 40, 70)), grad((H - WALL_Y) * K, W * K, (46, 48, 54), (30, 31, 36))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    rng = np.random.default_rng(5)
    for x, y in zip(rng.uniform(0, W, 50), rng.uniform(20, 560, 50)):
        d.ell(x, y, 2, 2, (230, 230, 255, 160))
    for x in range(0, W, 36):                                # grandstand crowd silhouettes
        h_ = 20 + (x * 37 % 23)
        d.ell(x + 18, WALL_Y - 96 - h_ * .3, 13, 15, (24, 24, 40)); d.rect(x + 4, WALL_Y - 86, x + 32, WALL_Y - 40, (24, 24, 40), r=8)
    d.rect(0, WALL_Y - 44, W, WALL_Y, (90, 92, 100))                     # concrete wall
    for x in range(0, W, 120): d.rect(x, WALL_Y - 44, x + 60, WALL_Y, (200, 30, 40))
    for xb in (230, 690):                                    # timing boards on poles
        d.rect(xb - 8, 470, xb + 8, WALL_Y - 44, (60, 62, 70))
        d.rect(xb - 170, 150, xb + 170, 470, (12, 12, 16), r=14, ol=(90, 94, 104), w=6)
    d.text(230, 196, '288 HP', 40, (200, 204, 214), path=FONT_X)
    d.text(690, 196, '349 HP', 40, (200, 204, 214), path=FONT_X)
    d.line([(0, WALL_Y + 40), (W, WALL_Y + 40)], (240, 240, 240), 6)    # start line + lane lines
    for xl in (-200, 459, 1120):
        d.line([(CX + (xl - CX) * .3, WALL_Y + 6), (xl, H)], (230, 200, 40), 6)
    return img

TREE = (459, 610)
def strip_life(img, t):
    d = D(img)
    x0, y0 = TREE                                            # starting tree: ambers count down, then green
    d.rect(x0 - 6, y0, x0 + 6, WALL_Y - 44, (60, 62, 70)); d.rect(x0 - 40, y0 - 200, x0 + 40, y0 + 10, (20, 20, 24), r=8)
    k = (t - T_S4) / .28
    for i in range(4):
        on = (i < 3 and int(k) == i) or (i == 3 and k >= 3)
        col = (60, 200, 80) if i == 3 else (250, 170, 30)
        d.ell(x0, y0 - 170 + i * 50, 17, 17, col if on else tuple(c // 5 for c in col))
    for xb, tv, tt in ((230, '6.0', T_60), (690, '5.1', T_51)):      # times arrive as they are said
        if t >= tt - .05:
            s_ = popin(t, tt - .05, .3)
            d.text(xb, 330, tv, 140 * s_, (255, 80, 60) if tv == '6.0' else (90, 230, 120), path=FONT_B)
            d.text(xb, 430, 'SEC 0-60 MPH', 26 * s_, (160, 164, 176), path=FONT_X)
    cow(d, 910, 1010, t, .92, face=-1, visor=0.0)            # the cow, staged in the next lane
    if t > T_S4 + .9:                                       # a little heat shimmer behind it
        for i in range(3):
            y = 940 + i * 12
            d.line([(990 + 8 * math.sin(t * 9 + i + j * .7), y - j * 6) for j in range(5)], (200, 200, 220, 60), 3)

# ---- scene 5: the backlash room (November 2022, then the spokesperson)
@lru_cache(None)
def bg_backlash():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (30, 34, 48), (40, 46, 64)), grad((H - WALL_Y) * K, W * K, (58, 60, 68), (92, 94, 100))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (18, 20, 28))
    for i, (x, y) in enumerate(((120, 160), (340, 160), (560, 160), (780, 160))):     # wall of monitors
        d.rect(x - 100, y - 10, x + 100, y + 120, (10, 12, 16), r=8, ol=(70, 76, 90), w=4)
        d.rect(x - 90, y, x + 90, y + 110, (24, 34, 54), r=4)
        mb_star(d, x - 60, y + 30, .22, (170, 176, 190))
        d.rect(x - 30, y + 22, x + 70, y + 36, (80, 96, 126), r=4); d.rect(x - 30, y + 50, x + 40, y + 62, (60, 74, 100), r=4)
        d.text(x, y + 90, '$1,200/yr', 24, (255, 110, 100), path=FONT_X)
    d.rect(0, WALL_Y - 8, W, WALL_Y, EQ_BLUE)
    d.rect(0, WALL_Y, W, WALL_Y + 6, (14, 16, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (110, 112, 120), 2)
    d.rect(560, 820, 860, 900, (70, 52, 38), r=6, ol=(40, 30, 20), w=3)               # desk
    return img

COMMENTS = ['$1,200 A YEAR?!', 'For power it already has?', 'Hard pass.', 'A subscription. For speed.', 'Unbelievable.',
            'No thanks, Mercedes.', 'Who asked for this?', 'My car. My horsepower.', 'Absolutely not.']
def backlash_life(img, t):
    d = D(img)
    for i, (bt, txt) in enumerate(zip(BUBBLES, COMMENTS)):  # angry comment bubbles rise and fade
        if not (bt <= t < bt + 2.4): continue
        k_ = popin(t, bt, .25); a = int(255 * min(1, (bt + 2.4 - t) / .5))
        x = 110 + (i * 211) % 560; y = 820 - (i % 3) * 62 - (t - bt) * 34
        w_ = font(26).getlength(txt) + 70
        d.rect(x - 10, y - 26 * k_, x + w_ * k_, y + 26 * k_, (255, 255, 255, a), r=14)
        d.ell(x + 16, y, 13 * k_, 13 * k_, (236, 60, 60, a))                         # angry face
        d.line([(x + 9, y - 6), (x + 14, y - 3)], (30, 10, 10, a), 2); d.line([(x + 23, y - 6), (x + 18, y - 3)], (30, 10, 10, a), 2)
        if k_ > .7: d.text(x + 38, y, txt, 26, (30, 32, 40, a), anchor='lm', path=FONT_X)
    cow(d, 905, 1000, t, .9, face=-1, chew=True)           # the cow at the desk, on the phone
    d.rect(764, 846, 782, 892, (24, 24, 28), r=4, ol=(90, 90, 100), w=2)

# ================================================================ sets
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)

BRANDS = {
    'mb': dict(wall=((228, 231, 235), (246, 247, 249)), floor=((26, 28, 32), (58, 60, 66)), panel=(240, 241, 244),
               relief=(222, 225, 230), trim=EQ_BLUE, ceil=(240, 241, 243), name='Mercedes-Benz', namecol=(22, 24, 30),
               emb=mb_emb, pend=(150, 459, 768)),
    'bmw': dict(wall=((222, 226, 232), (242, 244, 247)), floor=((58, 62, 70), (96, 100, 108)), panel=(234, 236, 240),
               relief=(210, 214, 222), trim=(28, 105, 190), ceil=(236, 238, 242), name='B M W', namecol=(30, 34, 42),
               emb=bmw_badge, pend=(150, 459, 768)),
    'vw': dict(wall=((196, 206, 220), (226, 232, 240)), floor=((186, 190, 196), (224, 226, 230)), panel=(210, 218, 230),
               relief=(184, 194, 210), trim=(30, 90, 170), ceil=(232, 234, 238), name='V O L K S W A G E N', namecol=(26, 54, 110),
               emb=roundel, pend=(150, 459)),
    'porsche': dict(wall=((22, 22, 24), (48, 48, 52)), floor=((72, 74, 78), (112, 114, 118)), panel=(34, 34, 38), relief=(54, 54, 60),
                    trim=P_RED, ceil=(40, 40, 44), name='P O R S C H E', namecol=(236, 236, 240), emb=crest, pend=(150, 459)),
    'bentley': dict(wall=((58, 36, 24), (94, 62, 40)), floor=((36, 66, 54), (60, 94, 78)), panel=(76, 48, 32), relief=(108, 74, 48),
                    trim=(196, 170, 110), ceil=(48, 30, 20), name='B E N T L E Y', namecol=(236, 226, 196), emb=wings, pend=(150, 459, 768)),
    'lambo': dict(wall=((14, 14, 16), (36, 36, 40)), floor=((200, 202, 204), (234, 235, 236)), panel=(28, 28, 32), relief=(44, 44, 50),
                  trim=GOLD, ceil=(20, 20, 22), name='L A M B O R G H I N I', namecol=(236, 222, 180), emb=shield, pend=(150, 459)),
}

@lru_cache(None)
def bg_showroom(brand, turntable=True):
    B = BRANDS[brand]
    arr = np.concatenate([grad(WALL_Y * K, W * K, *B['wall']), grad((H - WALL_Y) * K, W * K, *B['floor'])])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-40, W, 170):                          # tall wall panels with a relief pattern
        d.poly([(x + 8, 110), (x + 160, 110), (x + 160, WALL_Y - 40), (x + 8, WALL_Y - 40)], B['panel'])
        for yy in range(150, WALL_Y - 60, 110):
            d.line([(x + 30, yy), (x + 84, yy - 26), (x + 138, yy)], B['relief'], 3)
        d.line([(x + 8, 110), (x + 8, WALL_Y - 40)], B['trim'] + (120,), 2)
    d.rect(0, 0, W, CEIL, B['ceil'])                      # ceiling band with a light strip
    d.rect(0, CEIL - 6, W, CEIL, tuple(int(c * .7) for c in B['ceil']))
    for px in B['pend']:                                  # pendant lights
        d.line([(px, CEIL), (px, CEIL + 40)], (70, 74, 78), 3)
        d.chord(px, CEIL + 62, 46, 28, 180, 360, (52, 52, 56))
        d.ell(px, CEIL + 62, 30, 6, (255, 240, 200))
    d.rect(0, WALL_Y - 8, W, WALL_Y, B['trim'])
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], tuple(min(255, c + 12) for c in B['floor'][1]), 2)
    img = spot(img, CX, 140, 70, 470, 800)
    d = D(img)
    B['emb'](d, CX, 236, 0.85)
    d.text(CX, 336, B['name'], 40, B['namecol'], path=FONT_X)
    if turntable:
        d.ell(CX, 905, 400, 50, (14, 16, 16))
        d.ell(CX, 897, 394, 44, (46, 46, 50), B['trim'], 5)
        d.ell(CX, 897, 340, 34, (60, 60, 64))
    return img

# ================================================================ characters (series buyer, new salesman)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('e9b896'), skin2=hexc('cc9a78'), hair=hexc('c9ccd2'), suit=hexc('2b2e36'), suit2=hexc('1a1c22'),
             shirt=hexc('f7f7fa'), tie=hexc('00a0de'), pants=hexc('2b2e36'), shoe=hexc('1a1a1e'), glasses=False, hairstyle='part', lids=0.5,
             mustache=hexc('9a9ea6'))
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
        mb_star(d, x + 73, top + 105, 0.17, (90, 96, 110))
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
    if c.get('mustache'):                                 # neat salt-and-pepper moustache
        mc = c['mustache']
        d.poly(spline([(hx - 34, hy + 40), (hx - 16, hy + 28), (hx, hy + 32), (hx + 16, hy + 28), (hx + 34, hy + 40), (hx, hy + 38)], 4), mc, OL, 2)
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
        elif prop == 'card':                                # black credit card
            d.rect(hx2 - 6, hy2 - 52, hx2 + 70, hy2 - 4, (24, 24, 30), r=6, ol=(200, 170, 90), w=3)
            d.rect(hx2 + 4, hy2 - 40, hx2 + 22, hy2 - 28, (210, 180, 100), r=2)


# ---- performance schedules: (time, left pose, right pose, extras). Buyer escalates per showroom, then deflates.
def buyer_sched():
    A, Wd = dict(brows='angry', eyes='wide'), dict(brows='angry', eyes='wide', sweat=1)
    return [(0.0, 'rest', 'point', dict(brows='up')),                    # frame 1: walking in, pointing at the car
            (T_WHAT - .1, 'up', 'up', Wd),
            (LE[1] + .15, 'rest', 'point', dict(brows='angry')),
            (T_288, 'chin', 'rest', dict(brows='worried')),
            # dyno cell
            (T_S2, 'rest', 'rest', dict(brows='angry')),
            (T_349, 'hip', 'point', dict(brows='up', eyes='wide')),
            (LS[3] - .05, 'point', 'up', A),
            (LE[3] + .2, 'rest', 'rest', dict(brows='angry')),
            # store screen
            (T_S3, 'rest', 'rest', dict(brows='flat')),
            (T_1200 + .1, 'chin', 'rest', dict(brows='worried')),
            (T_YEAR2 - .05, 'head', 'head', Wd),
            (LE[5] + .2, 'up', 'up', Wd),
            (T_STAY, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # drag strip
            (T_S4, 'rest', 'rest', dict(brows='angry')),
            (LS[7] - .05, 'shrug', 'shrug', A),
            (LE[7] + .15, 'rest', 'rest', dict(brows='angry')),
            (T_51, 'chin', 'rest', dict(brows='worried')),
            (T_LESS - .05, 'point', 'point', A),
            (LE[9] + .15, 'head', 'rest', dict(brows='worried', smile=-1)),
            (T_PERYEAR, 'head', 'head', dict(brows='worried', eyes='wide', sweat=1)),
            (LS[11] - .05, 'up', 'up', Wd),
            (LE[11] + .2, 'point', 'point', Wd),
            # backlash room: glee, then the floor drops out
            (T_S5, 'rest', 'rest', dict(brows='angry')),
            (T_FURIOUS, 'hip', 'hip', dict(brows='up', smile=1)),
            (T_GOOD - .05, 'up', 'raise1', dict(brows='up', eyes='wide', smile=1)),
            (LE[13] + .2, 'hip', 'hip', dict(brows='up', smile=1)),
            (T_NOBODY, 'rest', 'rest', dict(brows='flat', eyes='wide')),
            (T_NOBODY2 - .05, 'head', 'head', dict(brows='up', eyes='wide', sweat=1)),
            (LE[15] + .2, 'chin', 'rest', dict(brows='worried')),
            # back at the showroom: deflated
            (T_S6, 'rest', 'rest', dict(brows='worried', tired=0.4, smile=-1)),
            (LS[17] + .05, 'shrug', 'shrug', dict(brows='worried', tired=0.3)),
            (LE[17] + .2, 'rest', 'rest', dict(brows='flat', tired=0.5, smile=-1)),
            (T_OVER, 'rest', 'rest', dict(brows='flat', tired=0.6)),
            (T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {0: 'open', 2: 'present', 4: 'offer', 6: 'open', 8: 'present', 10: 'offer', 12: 'open', 14: 'present', 16: 'open', 18: 'offer'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
    s += [(T_349, 'point', 'clasp', {}), (T_61, 'raise1', 'clasp', {}),
          (T_FINAL, 'open', 'clasp', dict(look=0)), (LE[19] + .3, 'clasp', 'clasp', dict(look=0))]
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
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    if sc in (0, 5):
        img = bg_showroom('mb').copy()
        showroom_life(img, t, sc)
        paste_car(img, 'eqe', CX - 290, 894, 580)
    elif sc == 1:
        img = bg_dyno().copy(); dyno_life(img, t)
    elif sc == 2:
        img = bg_store().copy(); store_life(img, t)
    elif sc == 3:
        img = bg_strip().copy(); strip_life(img, t)
    else:
        img = bg_backlash().copy(); backlash_life(img, t)
    d = D(img)
    f = int(round(t * FPS))
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.3), 120, 11       # already striding in on frame 1
    elif sc == 5:
        walk_k, bx0, dur_w = prog(t, t_in, 1.0), 40, 7      # tired shuffle back in
    else:
        walk_k, bx0, dur_w = prog(t, t_in, .7), -60, 13     # hurrying after the salesman
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
            st['dy'] -= abs(math.sin(t * dur_w)) * (5 if sc == 5 else 10)
        if st.get('sweat'):
            st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
    return img

def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0:
        z = 1.10 - 0.07 * oc(prog(t, 0, 1.6)) + 0.01 * math.sin(t * .5)   # moving on frame 1
        sx = 30 * (1 - oc(prog(t, 0, 1.6)))
        punches = ((T_WHAT, .05), (T_EQE, .03))
    elif sc in (1, 2, 3, 4):
        z = 1.05 + 0.015 * io(prog(t, t0, 7))
        sx = 46 * (1 - oc(prog(t, t0, 1.4)))               # settle after the whip
        punches = {1: ((T_349, .05), (T_UNLOCK, .03)), 2: ((T_1200, .04), (T_YEAR2, .07), (T_STAY, .03)),
                   3: ((T_60, .03), (T_51, .04), (T_PERYEAR, .03), (T_85, .06)),
                   4: ((T_FURIOUS, .03), (T_NOBODY, .06), (T_NOBODY2, .05))}[sc]
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_OVER, .04), (T_FINAL, .05))
        pk = io(prog(t, T_FINAL - .05, .5))                # salesman turns to camera: push in on him
        z += 0.14 * pk
        sx = 150 * pk
    if sc == 2 and T_YEAR2 - .05 <= t < T_YEAR2 + .7:                   # the room shakes on 'A YEAR?!'
        k_ = 1 - prog(t, T_YEAR2 - .05, .75)
        sx += 14 * k_ * math.sin(t * 61); sy += 10 * k_ * math.sin(t * 47 + 1)
    if sc == 3 and T_85 <= t < T_85 + .7:
        k_ = 1 - prog(t, T_85, .7)
        sx += 12 * k_ * math.sin(t * 57); sy += 9 * k_ * math.sin(t * 43 + 1)
    if sc == 4: sx += -26 * io(prog(t, t0 + 1.2, 5))                    # slow drift along the wall of monitors
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
GREY = (110, 116, 128)
CARD_MATH = (("$1,200 ÷ 61 hp", 60, INK2), ("≈ $20 per hp,", 64, DRED), ("per year", 64, DRED))
CARD_NOV = (("November 2022:", 54, INK2), ("listed on the US store", 54, INK2), ("EQE and EQS: $1,200/year", 50, DRED))
CARD_DRIVE = (("Mercedes to The Drive, April 2023:", 44, INK2), ("“no one was allowed", 56, DRED), ("to purchase the upgrade.”", 56, DRED))
CHIPS_D = [('YOU PAID FOR', '288 HP', GREY, 'T_S2'), ('MOTORS CAN MAKE', '349 HP', RED, 'T_349')]
CHIPS_S = [('PAY EVERY YEAR', '349 HP', GREEN, 'T_RENEW'), ('STOP PAYING', 'BACK TO 288 HP', RED, 'T_STAY')]
CHIPS_T = [('PRICING', 'CHANGED', EQ_BLUE, 'T_PRICE'), ('ONE-TIME PURCHASE', 'ADDED', GREEN, 'T_ONETIME')]
FINAL = [("Would you pay $1,200", 70, TAG), ("a year to be", 70, TAG), ("0.9 seconds faster?", 76, TAG),
         ("YES or NO?", 84, (255, 255, 255)), ("Comment below.", 60, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 430, 112
ONSCREEN = (['Mercedes-Benz', 'STORE', 'Acceleration Increase', 'EQE 350 4MATIC', '288 hp', '349 hp', '$1,200', '/ year',
             'plus tax  ·  renews annually', 'HP', '288', '288 HP', '349 HP', '6.0', '5.1', 'SEC 0-60 MPH', '$1,200/yr', '+61 HP',
             '-0.9 s', '$84,900', 'EQE STARTING PRICE (2022)', 'NEVER OVERCHARGED'] + COMMENTS
            + [r[0] for c in (CARD_MATH, CARD_NOV, CARD_DRIVE) for r in c] + [x for r in CHIPS_D + CHIPS_S + CHIPS_T for x in r[:2]]
            + [f[0] for f in FINAL])

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

def scene_card(img, t, rows, t0, t1, y=700, wobble=()):
    a = window(t, t0, t1, .1, .3)
    if a <= 0: return False
    s = popin(t, t0, .35)
    for tp in wobble:
        if t >= tp: s *= 1 + .06 * math.sin((t - tp) * 14) * math.exp(-(t - tp) * 4)
    put(img, info_card(rows), CX, y, s, a, rot=-1.5)
    return True

@lru_cache(None)
def sticker(txt, col, size=92):
    f = font(size * K); w_ = int(f.getlength(txt) / K) + 70
    st_ = Image.new('RGBA', ((w_ + 12) * K, (size + 66) * K), (0, 0, 0, 0)); sd = D(st_)
    sd.rect(8, 10, w_ + 10, size + 62, (0, 0, 0, 90), r=20)
    sd.rect(0, 0, w_, size + 52, col, r=20, ol=(16, 16, 22), w=6)
    sd.text(w_ / 2, (size + 52) / 2 + 2, txt, size, (255, 255, 255), stroke=3, sc=(16, 16, 22))
    return st_

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        pa = window(t, T_EQE - .05, T_S2 + .05, .1, .25)       # (after the 3 s hook) the real car
        if pa > 0:
            used = True
            put(img, photo_card('eqe_front.jpg', 'EQE 350 4MATIC', (18, 20, 26), (255, 255, 255), 460), CX, 420,
                popin(t, T_EQE - .05, .35), pa, rot=-2)
            if t >= T_288 - .05:
                put(img, sticker('288 HP', GREY, 72), CX + 210, 640, popin(t, T_288 - .05, .3), pa, rot=4)
    elif sc == 1:
        pa = window(t, T_S2 + .3, T_S3 + .05, .15, .25)
        if pa > 0:
            used = True
            panel(d, 80, 530, 830, 690, pa)
            chip_rows(d, t, CHIPS_D, 572, pa)
    elif sc == 2:
        pa = window(t, T_RENEW - .05, T_S4 + .05, .15, .25)
        if pa > 0:
            used = True
            panel(d, 80, 660, 830, 820, pa)
            chip_rows(d, t, CHIPS_S, 702, pa)
    elif sc == 3:
        ka = window(t, T_61 - .05, T_LESS - .05, .1, .2)
        if ka > 0:
            used = True; put(img, sticker('+61 HP', GREEN), CX, 720, popin(t, T_61 - .05, .3), ka, rot=-4)
        ka = window(t, T_LESS - .05, T_20 - .1, .1, .2)
        if ka > 0:
            used = True; put(img, sticker('-0.9 s', EQ_BLUE), CX, 720, popin(t, T_LESS - .05, .3), ka, rot=3)
        used = scene_card(img, t, CARD_MATH, T_20 - .1, T_85 - .05, 700, (T_PERYEAR,)) or used
        ta = window(t, T_85 - .05, T_S5 + .05, .1, .25)
        if ta > 0:
            used = True
            sw = math.sin((t - T_85) * 6) * 4 * math.exp(-(t - T_85) * 2)
            put(img, price_tag('$84,900', 'EQE STARTING PRICE (2022)', TAG, 600), CX, 690, popin(t, T_85 - .05, .35) * .95, ta, rot=sw - 3)
    elif sc == 4:
        used = scene_card(img, t, CARD_NOV, T_S5 + .3, T_DRIVE - .1, 430)
        used = scene_card(img, t, CARD_DRIVE, T_DRIVE - .1, T_PRICE - .05, 430, (T_NOBODY,)) or used
        ca = window(t, T_PRICE - .05, T_S6 + .05, .2, .25)
        if ca > 0:
            used = True
            panel(d, 70, 360, 830, 660, ca)
            chip_rows(d, t, CHIPS_T, 410, ca, two_line=True)
    else:
        fa = window(t, T_TECH - .05, T_FINAL + .05, .2, .25)
        if fa > 0:
            used = True
            put(img, photo_card('eqe_rear.jpg', 'EQE 350 4MATIC', (18, 20, 26), (255, 255, 255), 400), CX, 430,
                popin(t, T_TECH - .05, .35), fa, rot=3)
            if t >= T_OVER - .05:
                put(img, stamp_img('NEVER OVERCHARGED', GREEN, 56), CX, 470, popin(t, T_OVER - .05, .3) * .95, fa, rot=-8)
    if t >= T_CARD:                                          # final card
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(FINAL):
            k_ = popin(t, T_CARD + .08 * i, .3)
            if k_ > .05:
                d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if used else None
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
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    def whine(d, f0, f1):                                   # electric-motor whine for the dyno and the launch
        tt = np.arange(int(SR * d)) / SR; f = f0 + (f1 - f0) * (tt / d) ** .7
        ph = 2 * np.pi * np.cumsum(f) / SR
        return (np.sin(ph) + .4 * np.sin(2 * ph) + .15 * np.sin(3.01 * ph)) * np.minimum(1, tt * 8) * np.minimum(1, (d - tt) * 6) * .5
    for k_ in range(4): add(0.02 + k_ * 0.3, step(), .5)
    add(T_WHAT, sfx.thump(.25), .3)
    add(T_EQE - .05, sfx.pop(), .35); add(T_EQE + .05, sfx.sparkle(), .12)
    add(T_288 - .05, sfx.pop(), .3)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    for s_ in SCENES[1:5]:                                  # buyer hurrying in
        for k_ in range(3): add(s_ + .08 + k_ * .22, step(), .35)
    for k_ in range(3): add(T_S6 + .05 + k_ * .4, step(), .3)
    add(T_S2 + .1, whine(1.0, 180, 900), .22)              # needle sweep to 288
    add(T_349 - .05, click(900, 1400, .08), .7); add(T_349, sfx.buzzer(.3), .25)   # hits the lock
    add(T_1200 - .05, sfx.pop(), .3); add(T_1200 + .25, sfx.cha_ching(), .35)
    add(T_AYEAR - .05, sfx.pop(), .25)
    add(T_YEAR2, sfx.thump(.35), .4)
    add(T_RENEW - .05, sfx.ding(1320, .6), .14); add(T_STAY, click(1800, 2600, .05), .8); add(T_STAY + .05, sfx.slide_down(), .3)
    for k_ in range(3): add(T_S4 + .02 + k_ * .28, tone(880, .12, 18, .5), .5)
    add(T_S4 + .86, tone(1320, .3, 6, .6), .5); add(T_S4 + .9, whine(1.4, 300, 1500), .2)
    add(T_61 - .05, sfx.pop(), .32); add(T_60 - .05, tick(), .7); add(T_51 - .05, sfx.ding(1568, .5), .16)
    add(T_LESS - .05, sfx.pop(), .3)
    add(T_20 - .1, sfx.stamp(), .3); add(T_PERYEAR, sfx.coin_clink(), .3)
    add(T_85 - .05, sfx.pop(), .35); add(T_85 + .3, sfx.cha_ching(), .38)
    add(T_S5 + .3, sfx.stamp(), .3)
    for bt in BUBBLES: add(bt, sfx.ding(2093, .25), .09); add(bt, sfx.pop(), .12)
    add(T_GOOD, sfx.sparkle(), .14)
    add(T_DRIVE - .1, sfx.stamp(), .32); add(T_NOBODY, sfx.screech(.3), .14)
    add(T_PRICE - .05, sfx.ding(1760), .16); add(T_ONETIME - .05, sfx.ding(2093), .16)
    add(T_TECH - .05, sfx.pop(), .25); add(T_OVER - .05, sfx.stamp(), .3)
    for k_ in range(2): add(BEAT[0] + .2 + k_ * .35, tick(), .6)
    add(T_FINAL - .02, sting(), .6); add(T_CARD, sfx.pop(), .35)
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
