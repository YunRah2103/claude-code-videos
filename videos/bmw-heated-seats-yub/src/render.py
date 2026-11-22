"""BMW heated seats (Yub): showroom -> BMW store screen -> map room -> factory line (the why) -> press conference ->
showroom. Flat-vector style, 1080x1920 @30. Built on bmw-heated-seats/src/render.py: same buyer, caption system, camera,
whip pans and mix chain; a new BMW salesman; real BMW roundel and real 2023 BMW X1 photos (Wikimedia Commons, see
CREDITS.txt); one recurring background oddity (penguin under a heat lamp) and one visual gag (the seat padlock).
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
DUR = round(WORDS[-1]['e'] + 1.45, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/bmw-yub/voice.wav')
MUSIC = os.environ.get('MUSIC', os.path.expanduser('~/.cache/bmw-yub/music.mp3'))   # user-supplied background track
MUSIC_START = float(os.environ.get('MUSIC_START', '1.0'))

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
def gap(i): return round((LE[i - 1] + LS[i]) / 2, 3)    # whip pans centred in the pause before line i
T_CLOSE = LS[2] - 0.1                      # in-scene cut: closer on the car and its seats
T_S2, T_S3, T_S4, T_S5, T_S6 = gap(3), gap(7), gap(11), gap(13), gap(16)
BEAT = (LE[16], LS[17])
T_HEATED, T_PAIDIT, T_UNDER = word_t(0, 'heated'), word_t(0, 'paid'), word_t(1, 'under')
T_INST, T_LOCK = LS[2], word_t(2, 'Locked')
T_UNLOCK, T_18, T_MONTH2, T_176 = word_t(3, 'unlock'), word_t(4, 'Eighteen'), LS[5], word_t(6, 'one')
T_SK, T_BRIT, T_GER, T_2022 = word_t(8, 'South'), word_t(8, 'Britain'), word_t(8, 'Germany'), word_t(8, '2022')
T_FOREVER, T_406 = word_t(9, 'forever'), word_t(10, 'four')
T_WHY, T_ONE, T_SWITCH, T_FEE = LS[11], LS[12], word_t(12, 'Switch'), word_t(12, 'fee')
T_PAY, T_NOT, T_2023, T_DROP, T_WON = word_t(13, 'pay'), LS[14], word_t(14, '2023'), word_t(14, 'dropped'), word_t(15, 'won')
T_REMOTE, T_105 = LS[16], word_t(16, 'hundred')
T_FINAL, T_YESNO = LS[17], word_t(17, 'Yes')
T_CARD = LE[17] + 0.25                     # final caption card
SCENES = [0.0, T_S2, T_S3, T_S4, T_S5, T_S6]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
_fr = np.random.default_rng(11)            # press-camera flashes (shared by picture and sound)
FLASHES = sorted(T_S5 + .3 + _fr.uniform(0, T_S6 - T_S5 - .6, 12))
FLASH_X = [int(x) for x in _fr.uniform(40, 760, 12)]

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

LOGO = Image.open(os.path.join(HERE, '..', 'assets', 'bmw_logo.png')).convert('RGBA')   # real BMW roundel (Wikimedia Commons)
@lru_cache(None)
def _logo(px): return LOGO.resize((px, px), Image.LANCZOS)
def bmw_badge(d, cx, cy, s=1.0):
    """Real BMW roundel (Commons File:BMW.svg), radius 62*s design px."""
    r = max(2, int(62 * s * d.k)); x, y = d.p(cx, cy)
    lg = _logo(2 * r); d.i.paste(lg, (int(x - r), int(y - r)), lg)

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
CARS = {
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
    elif kind == 'bmw':                                  # sloping coupe roof, Hofmeister kink
        gh = spline([P(.35, .70), P(.47, .91), P(.60, .93), P(.74, .87), P(.80, .79), P(.77, .70)], 5)
    elif kind == 'cayenne':
        gh = spline([P(.35, .70), P(.47, .91), P(.62, .935), P(.78, .87), P(.88, .76), P(.86, .71)], 5)
    else:
        top = .955 if kind == 'bentayga' else .945
        gh = spline([P(.35, .74), P(.46, top - .02), P(.63, top), P(.83, top - .03), P(.925, .85), P(.91, .76)], 5)
    shade(d, gh, (86, 106, 130), (16, 20, 30), ground - .94 * Hh, ground - .66 * Hh)
    d.poly(gh, None, (20, 22, 28), 4)
    d.poly([P(.40, .72), P(.43, .72), P(.50, .88), P(.47, .88)], (255, 255, 255, 50))
    d.poly([P(.595, .70), P(.62, .70), P(.625, .93), P(.60, .93)], (20, 20, 24))
    # door cut, handle, mirror
    d.line([P(.34, .64), P(.31, .22)], lo, 3)
    d.line([P(.61, .66), P(.62, .21)], lo, 3)
    d.rect(*P(.52, .56), *P(.57, .535), CHROME if kind in ('touareg', 'bentayga') else (30, 30, 34), r=3)
    d.poly(spline([P(.355, .72), P(.41, .74), P(.41, .80), P(.36, .80)], 4), (24, 24, 28) if kind != 'bentayga' else base, (24, 26, 34), 3)
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
# The same penguin follows them through all six sets: lounging in a striped deckchair under a glowing heat lamp,
# sunglasses on, sipping an iced drink through a straw, idly fanning itself with a BMW brochure.
CEIL = 84
def penguin(d, x, fy, t, s=1.0):
    S = lambda v: v * s
    d.line([(x + S(96), fy), (x + S(96), fy - S(300))], (70, 72, 80), max(2, S(7)))             # heat lamp on a pole
    d.ell(x + S(96), fy, S(30), S(8), (50, 52, 58))
    d.poly([(x + S(96), fy - S(300)), (x + S(40), fy - S(268)), (x + S(64), fy - S(240)), (x + S(110), fy - S(280))], (60, 62, 70), OL, max(2, S(3)))
    gl = .75 + .25 * math.sin(t * 3)
    d.ell(x + S(56), fy - S(250), S(60), S(40), (255, 120, 40, int(60 * gl)))
    d.ell(x + S(56), fy - S(252), S(14), S(10), (255, 170, 80))
    for k in range(4):                                                                         # warm shimmer
        yy = fy - S(220) + k * S(22); ph = t * 5 + k
        d.line([(x + S(30) + S(6) * math.sin(ph + j * .8) + j * S(12), yy + S(4) * math.cos(ph + j)) for j in range(5)], (255, 160, 90, 90), max(1, S(2)))
    for k, c in enumerate(((230, 60, 60), (250, 250, 250), (230, 60, 60), (250, 250, 250))):   # deckchair
        d.poly([(x - S(70) + k * S(30), fy - S(150) + k * S(8)), (x - S(40) + k * S(30), fy - S(146) + k * S(8)),
                (x + S(10) + k * S(16), fy - S(60)), (x - S(18) + k * S(16), fy - S(62))], c)
    d.line([(x - S(74), fy - S(150)), (x - S(8), fy)], (150, 110, 70), max(2, S(6)))
    d.line([(x + S(60), fy - S(60)), (x + S(40), fy)], (150, 110, 70), max(2, S(6)))
    d.line([(x - S(30), fy - S(60)), (x + S(70), fy - S(60))], (150, 110, 70), max(2, S(6)))
    bob = math.sin(t * 1.3) * S(2)
    bx, by = x - S(6), fy - S(118) + bob                                                       # body, reclined
    d.ell(bx, by, S(38), S(56), (24, 26, 34), OL, max(2, S(3)))
    d.ell(bx + S(6), by + S(8), S(24), S(42), (246, 246, 250))
    d.ell(bx - S(6), by - S(64), S(28), S(26), (24, 26, 34), OL, max(2, S(3)))                 # head
    d.rect(bx - S(30), by - S(72), bx + S(14), by - S(60), (12, 12, 16), r=S(5))              # sunglasses
    d.line([(bx - S(30), by - S(68)), (bx - S(36), by - S(72))], (12, 12, 16), max(1, S(3)))
    d.poly([(bx + S(14), by - S(62)), (bx + S(40), by - S(56)), (bx + S(14), by - S(50))], (250, 160, 40))   # beak
    for fx in (-S(18), S(20)):                                                                 # feet up
        d.ell(bx + fx + S(30), by + S(54), S(16), S(7), (250, 160, 40))
    d.rect(bx + S(30), by - S(30), bx + S(48), by - S(4), (190, 230, 250, 200), r=S(3))        # iced drink + straw
    d.line([(bx + S(40), by - S(30)), (bx + S(26), by - S(54))], (240, 80, 120), max(1, S(3)))
    fan = math.sin(t * 7) * 14                                                                 # brochure fan
    ang = math.radians(-120 + fan)
    fx0, fy0 = bx - S(36), by - S(6)
    d.line([(fx0, fy0), (fx0 + S(30) * math.cos(ang), fy0 + S(30) * math.sin(ang))], (24, 26, 34), max(2, S(9)))
    px, py = fx0 + S(44) * math.cos(ang), fy0 + S(44) * math.sin(ang)
    d.rect(px - S(18), py - S(22), px + S(18), py + S(22), (240, 242, 246), r=S(3), ol=(60, 64, 72), w=max(1, S(2)))
    d.ell(px, py - S(6), S(8), S(8), (28, 105, 190))

def oddity(img, t, sc):
    """Penguin spot per set (right edge, behind the salesman's shoulder line)."""
    x, fy, s = {0: (900, 990, 1.0), 1: (906, 990, .95), 2: (906, 992, .95), 3: (904, 990, .95), 4: (900, 1000, 1.0), 5: (900, 990, 1.0)}[sc]
    penguin(D(img), x, fy, t, s)

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
    else:                                                   # back again: receptionist typing
        reception(img, t, False)

def padlock(d, lx, ly, k_, open_=0.0, col=(230, 40, 50)):
    sh = 14 * k_ * open_                                                        # shackle lifts when it opens
    d.arc(lx + 6 * k_ * open_, ly - 14 * k_ - sh, 13 * k_, 15 * k_, 180, 360, (240, 240, 244), max(2, 5 * k_))
    d.rect(lx - 18 * k_, ly - 14 * k_, lx + 18 * k_, ly + 14 * k_, col, r=4, ol=(255, 255, 255), w=2)
    d.ell(lx, ly - 2 * k_, 4 * k_, 4 * k_, (255, 255, 255))

def seat_fx(img, t, sc):
    """VISUAL GAG. Driver's seat through the side glass. Scene 1: heater coils glow on 'heated', die on 'paid' and a red
    padlock snaps on. Scene 6: the padlock is off and the seat glows (BMW dropped it), then on 'Remote start' the padlock
    hops off the seat in an arc and clamps onto the bonnet, with a little engine-start icon."""
    d = D(img)
    x0, g, L = CX - 290, 894, 580
    Hh = L * .42
    def P(u, v): return (x0 + u * L, g - v * Hh)
    sx, sy = P(.50, .66)
    d.poly(spline([(sx - 26, sy), (sx - 34, sy - 74), (sx - 14, sy - 90), (sx + 10, sy - 84), (sx + 14, sy)], 4), (40, 54, 70))
    d.rect(sx - 30, sy - 112, sx + 2, sy - 92, (40, 54, 70), r=8)                               # headrest
    if sc == 0:
        on = T_HEATED - .1 <= t < T_PAIDIT + .15
        fl = on and (t < T_PAIDIT or int(t * 24) % 3 != 0)
    else:
        on = fl = True
    col = (255, 120, 40, 230) if fl else (90, 100, 112, 160)
    for i in range(3):
        y = sy - 70 + i * 18
        d.line([(sx - 24 + k * 6, y + (4 if k % 2 else -4)) for k in range(7)], col, 3)
    if fl:
        for i in range(3):                                                                      # heat waves
            x = sx - 22 + i * 14; ph = t * 6 + i
            d.line([(x + 4 * math.sin(ph + k * .9), sy - 96 - k * 9) for k in range(5)], (255, 140, 60, 200), 3)
    lx, ly = P(.72, .80)
    if sc == 0 and t >= T_PAIDIT + .1:                                                          # lock snaps on
        padlock(d, lx, ly, popin(t, T_PAIDIT + .1, .3))
    elif sc == 5 and t >= T_REMOTE:                                                             # ...and hops to the bonnet
        k_ = io(prog(t, T_REMOTE, .55))
        hx, hy = P(.22, .60)
        px, py = lx + (hx - lx) * k_, ly + (hy - ly) * k_ - 120 * math.sin(math.pi * k_)
        padlock(d, px, py, 1.15 + .25 * k_)
        if k_ >= 1:
            b = 1 + .25 * math.exp(-(t - T_REMOTE - .55) * 6)
            d.ell(hx, hy - 58, 22 * b, 22 * b, (20, 22, 28), (230, 40, 50), 4)                 # engine-start button icon
            d.arc(hx, hy - 58, 11 * b, 11 * b, 300, 600, (255, 255, 255), 3)
            d.line([(hx, hy - 72 * b + 14 * (b - 1)), (hx, hy - 60)], (255, 255, 255), 3)

# ---- scene 2: the map room
MAP_X0, MAP_Y0, MAP_S = 62, 160, 2.2
def ll(lon, lat): return (MAP_X0 + (lon + 170) * MAP_S, MAP_Y0 + (80 - lat) * MAP_S)
LAND = [
    [(-165, 65), (-140, 70), (-95, 72), (-80, 64), (-62, 56), (-64, 45), (-76, 36), (-81, 26), (-90, 29), (-97, 22), (-90, 16),
     (-82, 9), (-79, 8), (-92, 14), (-105, 20), (-117, 32), (-124, 41), (-125, 49), (-135, 58), (-150, 59), (-166, 60)],
    [(-52, 82), (-24, 80), (-20, 70), (-44, 60), (-54, 68)],
    [(-79, 9), (-62, 10), (-50, 0), (-35, -6), (-40, -22), (-56, -36), (-66, -55), (-74, -46), (-71, -18), (-81, -4)],
    [(-9, 37), (-9, 43), (-1, 46), (-3, 48), (5, 53), (8, 57), (12, 55), (20, 59), (25, 70), (40, 68), (60, 70), (80, 73),
     (110, 77), (140, 72), (170, 70), (180, 66), (160, 60), (140, 54), (135, 43), (130, 42), (129.5, 35), (126.5, 34.5),
     (126, 38), (122, 40), (121, 31), (110, 20), (106, 10), (100, 13), (98, 8), (92, 22), (80, 15), (77, 8), (72, 20),
     (58, 25), (56, 18), (44, 12), (35, 28), (35, 36), (27, 37), (23, 40), (15, 40), (12, 44), (8, 44), (3, 42), (-5, 36)],
    [(-6, 50), (1.5, 51), (1.8, 53), (-2, 58), (-6, 58), (-5, 54)],
    [(130, 31), (141, 36), (142, 44), (139, 41), (133, 34)],
    [(-17, 21), (-6, 36), (10, 37), (32, 31), (35, 28), (43, 12), (51, 12), (40, -2), (40, -15), (32, -28), (20, -35),
     (17, -29), (12, -17), (12, -5), (9, 4), (-8, 4), (-17, 14)],
    [(114, -22), (130, -12), (137, -12), (142, -11), (146, -19), (153, -27), (150, -37), (140, -38), (132, -32), (115, -34)],
    [(172.5, -34.5), (178, -37.5), (176, -41.5), (174.5, -41)],
    [(172.5, -40.5), (174, -41.5), (171, -45), (167, -46.5), (166.5, -45.5)],
    [(96, 4), (106, -6), (116, -8), (105, -2)], [(110, 1), (118, 6), (119, -3), (111, -3)]]
PINS = [(-2, 54), (10, 51), (127.5, 36.5), (174, -41), (25, -29)]       # UK, Germany, South Korea, NZ, South Africa
US = (-98, 39)

@lru_cache(None)
def bg_map():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (34, 46, 70), (48, 62, 90)), grad((H - WALL_Y) * K, W * K, (70, 70, 76), (110, 110, 116))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (24, 30, 44)); d.rect(0, CEIL - 6, W, CEIL, (16, 20, 30))
    for px in (150, 459, 768):
        d.rect(px - 60, CEIL, px + 60, CEIL + 10, (255, 246, 220))
    d.rect(36, 128, 882, 520, (20, 24, 30), r=14)                       # the map board
    d.rect(44, 136, 874, 512, (36, 92, 138), r=10)
    for lon in range(-150, 190, 30):
        d.line([ll(lon, 82), ll(lon, -62)], (60, 116, 160), 1)
    for lat in range(-60, 90, 30):
        d.line([ll(-170, lat), ll(190, lat)], (60, 116, 160), 1)
    for poly in LAND:
        d.poly(spline([ll(*p) for p in poly], 3), (214, 222, 190), (150, 160, 128), 2)
    d.rect(0, WALL_Y - 8, W, WALL_Y, (28, 105, 190))
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (124, 124, 130), 2)
    d.rect(40, 560, 300, 940, (44, 56, 80), r=6, ol=(26, 32, 46), w=3)   # filing wall + plant
    for y in range(580, 930, 70):
        d.rect(56, y, 284, y + 56, (58, 72, 100), r=4); d.rect(150, y + 24, 190, y + 30, (150, 160, 180), r=2)
    return img

PIN_T = None
def map_life(img, t):
    d = D(img)
    pin_t = [T_BRIT, T_GER, T_SK, T_2022 + .1, T_2022 + .25]                  # UK, Germany, S. Korea, NZ, South Africa
    for i, (lon, lat) in enumerate(PINS):
        k_ = popin(t, pin_t[i] - .05, .3)
        if k_ <= 0: continue
        x, y = ll(lon, lat)
        pulse = 1 + .25 * max(0, math.sin((t - pin_t[i]) * 5))
        d.ell(x, y, 13 * k_ * pulse, 13 * k_ * pulse, (255, 255, 255, 90))
        d.line([(x, y), (x, y - 26 * k_)], (40, 40, 44), 3)
        d.ell(x, y - 30 * k_, 10 * k_, 10 * k_, (230, 40, 50), (255, 255, 255), 2)
    k_ = popin(t, T_2022 + .45, .3)
    if k_ > 0:                                                            # not the US
        x, y = ll(*US)
        d.ell(x, y, 46 * k_, 46 * k_, None, (230, 40, 50), 8)
        d.line([(x - 32 * k_, y + 32 * k_), (x + 32 * k_, y - 32 * k_)], (230, 40, 50), 8)

# ---- scene 3: the subscription screen
SEAT_ICON = (230, 236, 244)
def seat_icon(d, x, y, s, col):
    d.poly(spline([(x - 30 * s, y + 40 * s), (x - 40 * s, y - 50 * s), (x - 18 * s, y - 64 * s), (x + 4 * s, y - 54 * s), (x - 4 * s, y + 20 * s)], 4), col)
    d.rect(x - 34 * s, y - 92 * s, x - 6 * s, y - 70 * s, col, r=8 * s)
    d.rect(x - 34 * s, y + 24 * s, x + 54 * s, y + 46 * s, col, r=10 * s)

@lru_cache(None)
def bg_pay():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (232, 234, 238), (212, 216, 222)), grad((H - WALL_Y) * K, W * K, (150, 152, 158), (188, 190, 196))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (238, 240, 244)); d.rect(0, CEIL - 6, W, CEIL, (200, 204, 210))
    for x in range(-40, W, 170):
        d.rect(x + 8, 110, x + 160, WALL_Y - 40, (224, 226, 232))
    d.rect(52, 118, 868, 560, (16, 18, 24), r=22)                       # the big wall screen
    d.rect(64, 130, 856, 548, (22, 30, 44), r=14)
    d.rect(64, 130, 856, 190, (30, 44, 66), r=14)
    bmw_badge(d, 104, 160, .32)
    d.text(140, 160, 'STORE', 30, (220, 228, 240), anchor='lm', path=FONT_X)
    seat_icon(d, 200, 360, 1.25, SEAT_ICON)
    d.text(340, 300, 'Heated seats', 52, (255, 255, 255), anchor='lm')
    d.rect(0, WALL_Y - 8, W, WALL_Y, (28, 105, 190))
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    d.rect(300, 700, 620, 940, (60, 64, 72), r=6, ol=(30, 32, 36), w=3)  # counter with a card terminal
    d.rect(300, 700, 620, 716, (28, 105, 190))
    d.rect(430, 650, 490, 700, (36, 38, 44), r=6); d.rect(438, 658, 482, 676, (120, 200, 160), r=3)
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (200, 202, 208), 2)
    return img

def pay_life(img, t):
    d = D(img)
    tx, ty = 420, 420
    k_ = 1.0 - .5 * max(0.0, math.sin(math.pi * prog(t, T_UNLOCK, .5)))   # buyer's tap: toggle twitches, snaps back to OFF
    d.rect(tx - 70, ty - 36, tx + 70, ty + 36, mix((60, 200, 110), (110, 116, 128), k_), r=36)
    d.ell(tx + 34 - 68 * k_, ty, 30, 30, (255, 255, 255))
    d.text(tx + 110, ty, 'OFF', 40, (255, 255, 255), anchor='lm')
    seat_icon(d, 200, 360, 1.25, (90, 98, 112))
    padlock(d, 236, 330, .9)
    if int(t * 3) % 2 == 0: d.text(340, 500, 'PAYMENT REQUIRED', 30, (240, 90, 90), anchor='lm', path=FONT_X)
    if T_18 <= t and int(t * 8) % 2 == 0:
        d.ell(460, 667, 8, 8, (255, 90, 90))                                # card terminal blinking

# ---- scene 4: the factory line (the why): identical cars, every one with heaters fitted, every switch off
@lru_cache(None)
def bg_factory():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (196, 202, 210), (170, 176, 186)), grad((H - WALL_Y) * K, W * K, (92, 96, 104), (128, 132, 140))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, CEIL, (60, 64, 72)); d.rect(0, CEIL - 6, W, CEIL, (40, 42, 48))
    for x in range(0, W, 120):                                            # roof trusses
        d.line([(x, CEIL), (x + 60, CEIL + 50), (x + 120, CEIL)], (110, 114, 122), 4)
    for x in range(60, W, 300):                                           # high windows
        d.rect(x, 170, x + 200, 330, (210, 228, 240), r=6, ol=(120, 126, 136), w=4)
        d.line([(x + 100, 170), (x + 100, 330)], (120, 126, 136), 4)
    bmw_badge(d, CX, 450, .9)
    d.text(CX, 552, 'PLANT', 40, (40, 44, 52), path=FONT_X)
    for x in range(0, W, 60):                                             # yellow/black safety band
        d.poly([(x, WALL_Y - 30), (x + 30, WALL_Y - 30), (x + 10, WALL_Y), (x - 20, WALL_Y)], (250, 200, 40))
    d.rect(0, 620, W, 700, (70, 74, 82)); d.rect(0, 690, W, 700, (40, 42, 48))   # overhead conveyor rail
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (140, 144, 152), 2)
    return img

def factory_life(img, t):
    d = D(img)
    off = (t - T_S4) * 70                                                 # line creeps right
    for i in range(-1, 4):
        x0 = -260 + i * 330 + off % 330
        y0 = 700
        d.line([(x0 + 120, 700), (x0 + 120, 760)], (40, 42, 48), 5)       # hanger
        d.rect(x0 + 10, 760, x0 + 250, 880, (236, 238, 242), r=40, ol=OL, w=4)   # simplified body shell
        d.poly([(x0 + 60, 760), (x0 + 90, 712), (x0 + 200, 712), (x0 + 230, 760)], (190, 200, 214), OL, 4)
        d.ell(x0 + 60, 884, 26, 26, (30, 30, 34)); d.ell(x0 + 200, 884, 26, 26, (30, 30, 34))
        seat_icon(d, x0 + 130, 818, .42, (90, 98, 112))
        hot = t >= T_SWITCH and (i + int((t - T_SWITCH) * 3)) % 4 == 0      # one car at a time flicks ON (for a fee)
        if hot:
            for j in range(3):
                xx = x0 + 120 + j * 10
                d.line([(xx + 3 * math.sin(t * 8 + k), 770 - k * 7) for k in range(4)], (255, 140, 60), 3)
        else:
            padlock(d, x0 + 160, 790, .55)

# ---- scene 4: the press conference
@lru_cache(None)
def bg_press():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (22, 36, 66), (30, 50, 88)), grad((H - WALL_Y) * K, W * K, (52, 54, 60), (90, 92, 100))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for r_, y in enumerate(range(130, WALL_Y - 20, 96)):                 # step-and-repeat backdrop
        for x in range(60 + (r_ % 2) * 80, W, 160):
            bmw_badge(d, x, y, .26)
    d.rect(0, 0, W, CEIL, (14, 18, 28))
    for px in (150, 459, 768):
        d.poly([(px - 40, CEIL), (px + 40, CEIL), (px + 160, WALL_Y), (px - 160, WALL_Y)], (255, 250, 230, 18))
    ph = Image.open(os.path.join(HERE, '..', 'assets', 'x1_exterior.jpg')).convert('RGB')
    sw_, sh_ = 560, 316                                                   # projected photo screen
    ph = ph.resize((sw_ * K, int(sw_ * ph.height / ph.width) * K), Image.LANCZOS)
    ph = ph.crop((0, (ph.height - sh_ * K) // 2, sw_ * K, (ph.height - sh_ * K) // 2 + sh_ * K))
    d.rect(CX - sw_ / 2 - 12, 150, CX + sw_ / 2 + 12, 150 + sh_ + 24, (10, 12, 16), r=10)
    img.paste(ph, (int((CX - sw_ / 2) * K), 162 * K))
    d = D(img)
    d.rect(0, WALL_Y - 4, W, WALL_Y + 6, (14, 16, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (100, 102, 110), 2)
    d.poly([(CX - 90, 700), (CX + 90, 700), (CX + 74, 950), (CX - 74, 950)], (30, 34, 44), (14, 16, 22), 4)   # podium
    d.rect(CX - 100, 690, CX + 100, 712, (40, 46, 58), r=6)
    bmw_badge(d, CX, 800, .5)
    for dx in (-24, 0, 24):                                                # microphones
        d.line([(CX + dx, 690), (CX + dx * 1.4, 640)], (30, 30, 34), 4); d.ell(CX + dx * 1.4, 634, 9, 12, (40, 40, 44))
    return img

def press_life(img, t):
    d = D(img)
    for i, x in enumerate(range(10, 800, 70)):                            # front row of reporters (backs of heads)
        bob = math.sin(t * 2 + i) * 2
        y = 1000 + (i % 2) * 12
        d.ell(x, y + 40, 40, 34, (36, 40, 52)); d.ell(x, y - 6 + bob, 24, 26, ((40, 30, 26), (90, 60, 40), (20, 20, 24))[i % 3])
        if i % 3 == 1:
            d.rect(x - 22, y - 50 + bob, x + 22, y - 22 + bob, (30, 30, 34), r=4); d.ell(x, y - 36 + bob, 9, 9, (80, 90, 110))
    for ft, fx in zip(FLASHES, FLASH_X):
        if ft <= t < ft + .12:
            a = int(255 * (1 - (t - ft) / .12))
            d.ell(fx, 960, 60, 60, (255, 255, 255, a // 2)); d.ell(fx, 960, 22, 22, (255, 255, 255, a))

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

# ================================================================ characters (tesla-locked cast)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('e6b48e'), skin2=hexc('c9946e'), hair=hexc('b9bdc6'), suit=hexc('9aa1ab'), suit2=hexc('7c838e'),
             shirt=hexc('f7f7fa'), tie=hexc('1c69be'), pants=hexc('7c838e'), shoe=hexc('1a1a1e'), glasses=False, hairstyle='part',
             lids=0.5, badge=True)              # BMW salesman (new for this episode): silver hair, light-grey suit, BMW-blue tie
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
        shield(d, x + 73, top + 105, 0.13, GOLD2, INK)
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
        elif prop == 'card':                                # black credit card
            d.rect(hx2 - 6, hy2 - 52, hx2 + 70, hy2 - 4, (24, 24, 30), r=6, ol=(200, 170, 90), w=3)
            d.rect(hx2 + 4, hy2 - 40, hx2 + 22, hy2 - 28, (210, 180, 100), r=2)


# ---- performance schedules: (time, left pose, right pose, extras). Buyer escalates per showroom, then deflates.
def buyer_sched():
    A, Wd = dict(brows='angry', eyes='wide'), dict(brows='angry', eyes='wide', sweat=1)
    return [(0.0, 'rest', 'rest', dict(brows='up')),                     # frame 1: walking in, puzzled
            (T_HEATED, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (T_PAIDIT, 'head', 'rest', dict(brows='angry', eyes='wide')),
            (LS[1] - .05, 'point', 'rest', A),
            (T_UNDER, 'point', 'up', Wd),
            (LE[1] + .15, 'rest', 'rest', dict(brows='angry')),
            (T_LOCK, 'head', 'head', dict(brows='worried', eyes='wide', sweat=1)),
            (LE[2] + .25, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # BMW store screen
            (T_S2, 'rest', 'rest', dict(brows='angry')),
            (LS[3] - .05, 'shrug', 'point', A),
            (T_18, 'head', 'head', dict(brows='up', eyes='wide', sweat=1)),
            (T_MONTH2 - .05, 'up', 'up', Wd),
            (LE[5] + .1, 'rest', 'point', dict(brows='angry')),
            (T_176, 'chin', 'rest', dict(brows='worried', smile=-1)),
            # map room
            (T_S3, 'rest', 'rest', dict(brows='angry')),
            (LS[7] - .05, 'up', 'point', A),
            (LE[7] + .1, 'rest', 'rest', dict(brows='angry')),
            (T_2022, 'hip', 'hip', dict(brows='up')),
            (LS[9] - .05, 'shrug', 'shrug', dict(brows='worried')),
            (T_406, 'head', 'head', Wd),
            (LE[10] + .2, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # factory: the why
            (T_S4, 'rest', 'rest', dict(brows='angry')),
            (LS[11] - .05, 'up', 'up', Wd),
            (LE[11] + .1, 'rest', 'rest', dict(brows='angry')),
            (T_FEE, 'head', 'rest', dict(brows='worried', eyes='wide')),
            # press conference: the twist, then smug
            (T_S5, 'rest', 'rest', dict(brows='flat')),
            (LS[13] - .05, 'chin', 'rest', dict(brows='up')),
            (T_DROP, 'hip', 'hip', dict(brows='up', eyes='wide')),
            (LS[15] - .05, 'up', 'up', dict(brows='up', eyes='wide', smile=1)),
            (LE[15] + .2, 'hip', 'hip', dict(brows='flat', smile=1)),
            # back at the showroom: smug, then deflated, then asks the viewer
            (T_S6, 'hip', 'hip', dict(brows='flat', smile=1)),
            (T_REMOTE + .3, 'head', 'head', dict(brows='worried', eyes='wide', smile=-1)),
            (LE[16] + .2, 'rest', 'rest', dict(brows='worried', tired=0.5, smile=-1)),
            (T_FINAL, 'rest', 'open', dict(brows='up', look=0)),
            (T_YESNO - .05, 'open', 'open', dict(brows='up', eyes='wide', look=0)),
            (LE[17] + .3, 'rest', 'rest', dict(brows='flat', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {0: 'open', 2: 'present', 4: 'open', 6: 'offer', 8: 'present', 10: 'open', 12: 'present', 14: 'open', 16: 'offer'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
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
        img = bg_showroom('bmw').copy()
        showroom_life(img, t, sc)
        oddity(img, t, sc)
        paste_car(img, 'bmw', CX - 290, 894, 580)
        seat_fx(img, t, sc)
    else:
        img = {1: bg_pay, 2: bg_map, 3: bg_factory, 4: bg_press}[sc]().copy()
        {1: pay_life, 2: map_life, 3: factory_life, 4: press_life}[sc](img, t)
        oddity(img, t, sc)
    d = D(img)
    f = int(round(t * FPS))
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.25), 150, 11   # already in shot, mid-complaint
    elif sc == 5:
        walk_k, bx0, dur_w = prog(t, t_in, 1.1), 40, 7      # smug stroll back in
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
            st['dy'] -= abs(math.sin(t * dur_w)) * (5 if sc == 5 else 10)
        if st.get('sweat'):
            st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
    return img

def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0 and t < T_CLOSE:
        z = 1.07 - 0.05 * oc(prog(t, 0, 1.4)) + 0.01 * math.sin(t * .5)
        punches = ((T_HEATED, .03), (T_PAIDIT, .04), (T_UNDER, .04))
    elif sc == 0:                                          # closer on the car and the seats
        z = 1.18 + 0.03 * io(prog(t, T_CLOSE, 3))
        sx = -40
        punches = ((T_CLOSE, .05), (T_LOCK, .04))
    elif sc in (1, 2, 3, 4):
        z = 1.05 + 0.015 * io(prog(t, t0, 7))
        sx = 46 * (1 - oc(prog(t, t0, 1.4)))               # settle after the whip
        punches = {1: ((T_18, .05), (T_MONTH2, .06), (T_176, .03)), 2: ((T_SK, .03), (T_2022, .03), (T_406, .05)),
                   3: ((T_ONE, .03), (T_FEE, .05)), 4: ((T_2023, .04), (T_DROP, .04), (T_WON, .06))}[sc]
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_REMOTE, .04), (T_105, .05))
        pk = io(prog(t, T_FINAL - .05, .5))                # buyer turns to camera: push in on him
        z += 0.14 * pk
        sx = -150 * pk
    if sc == 1 and T_MONTH2 - .05 <= t < T_MONTH2 + .6:                # handheld jolt on 'A month?!'
        k_ = 1 - prog(t, T_MONTH2 - .05, .65)
        sx += 14 * k_ * math.sin(t * 61); sy += 10 * k_ * math.sin(t * 47 + 1)
    if sc == 2: sx += -30 * io(prog(t, t0 + 1.4, 4))                   # slow drift across the map
    if sc == 3: sx += 24 * io(prog(t, t0, 5))                          # drift along the line
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
GX = 190                                   # x of the press-room padlock beat
CARD_MAP = (("From 2022:", 56, INK2), ("UK, Germany, South Korea,", 50, INK2), ("NZ, South Africa...", 50, INK2), ("Not the US.", 58, DRED))
CARD_DROP = (("September 2023:", 54, INK2), ("BMW drops the", 54, INK2), ("heated-seat subscription", 54, DRED))
CHIPS1 = [('HEATERS', 'INSTALLED', GREEN, 'T_INST'), ('SOFTWARE', 'LOCKED', RED, 'T_LOCK')]
CHIPS4 = [('EVERY CAR', 'HEATERS FITTED', GREEN, 'T_ONE'), ('SWITCH ON', 'LATER', GREEN, 'T_SWITCH'), ('PRICE', 'A FEE', RED, 'T_FEE')]
FINAL = [("Would you pay monthly", 66, TAG), ("for what's already", 66, TAG), ("in your car?", 72, TAG),
         ("YES or NO?", 92, (255, 255, 255)), ("Comment below.", 60, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 430, 112
TAGS = {'18': ('$18/month', 'HEATED SEATS · SOUTH KOREA'), '176': ('≈$176/year', 'OR PAY YEARLY'),
        '406': ('≈$406 forever', 'ONE-TIME UNLOCK'), '105': ('$105/year', 'REMOTE ENGINE START · US')}
ONSCREEN = (['B M W', 'STORE', 'Heated seats', 'OFF', 'PAYMENT REQUIRED', 'PLANT', 'WHY?', 'LOW UPTAKE', 'DROPPED', 'YES', 'NO',
             '2023 BMW X1 sDrive18i', 'HEATERS: FITTED']
            + [x for v in TAGS.values() for x in v] + [r[0] for c in (CARD_MAP, CARD_DROP) for r in c]
            + [x for r in CHIPS1 + CHIPS4 for x in r[:2]] + [f[0] for f in FINAL])

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

def scene_card(img, t, rows, t0, t1, y=700):
    a = window(t, t0, t1, .1, .3)
    if a <= 0: return False
    put(img, info_card(rows), CX, y, popin(t, t0, .35), a, rot=-1.5)
    return True

def tag(img, t, key, t0, t1, y, rot=-3, col=TAG):
    a = window(t, t0 - .05, t1, .1, .25)
    if a <= 0: return False
    sw = math.sin((t - t0) * 6) * 4 * math.exp(-(t - t0) * 2)
    put(img, price_tag(*TAGS[key], col), CX, y, popin(t, t0 - .05, .35) * .9, a, rot=sw + rot)
    return True

def stamp(img, t, txt, col, t0, t1, x, y, rot=-8, size=80):
    a = window(t, t0, t1, .05, .25)
    if a <= 0: return False
    k_ = popin(t, t0, .25)
    put(img, stamp_img(txt, col, size), x, y, 1.6 - .6 * k_ if t < t0 + .25 else 1.0, a, rot=rot)
    return True

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    u = []
    sc = scene_at(t)
    if sc == 0:                                              # nothing before 3 s: the hook plays clean
        a = window(t, T_UNDER - .05, T_INST - .05, .1, .2)
        if a > 0:
            u.append(1); put(img, photo_card('x1_exterior.jpg', '2023 BMW X1 sDrive18i', (24, 30, 44), (255, 255, 255), 460),
                             CX, 430, popin(t, T_UNDER - .05, .35), a, rot=-2)
        pa = window(t, T_INST - .1, T_S2 + .05, .1, .3)
        if pa > 0:                                           # the real seats' cabin, heaters fitted
            u.append(1)
            put(img, photo_card('x1_interior.jpg', 'HEATERS: FITTED', (24, 30, 44), (255, 255, 255), 440), CX, 400,
                popin(t, T_INST - .1, .35), pa, rot=-2)
            d = D(img); panel(d, 80, 640, 830, 820, pa); chip_rows(d, t, CHIPS1, 692, pa)
    elif sc == 1:
        u.append(tag(img, t, '18', T_18, T_S3 + .05, 600))
        u.append(stamp(img, t, 'MONTHLY', RED, T_MONTH2, T_176, 700, 760, -10))
        u.append(tag(img, t, '176', T_176, T_S3 + .05, 800, 2, (255, 255, 255)))
    elif sc == 2:
        u.append(scene_card(img, t, CARD_MAP, T_2022 + .35, T_406 - .05, 720))
        u.append(tag(img, t, '406', T_406, T_S4 + .05, 700, -3))
    elif sc == 3:
        k_ = popin(t, T_WHY + .3, .3)
        a = window(t, T_WHY + .3, T_ONE, .1, .2)
        if a > 0:
            u.append(1); d = D(img)
            d.text(CX, 470, 'WHY?', 150 * k_, TAG + (int(255 * a),), stroke=8, sc=(10, 10, 16, int(255 * a)))
        ca = window(t, T_ONE - .05, T_S5 + .05, .15, .25)
        if ca > 0:
            u.append(1); d = D(img); panel(d, 80, 130, 830, 370, ca); chip_rows(d, t, CHIPS4, 180, ca)
    elif sc == 4:
        u.append(stamp(img, t, 'LOW UPTAKE', RED, T_NOT, T_2023 - .05, CX, 520, -6, 72))
        u.append(scene_card(img, t, CARD_DROP, T_2023 - .05, T_S6 + .05, 520))
        u.append(stamp(img, t, 'DROPPED', GREEN, T_DROP, T_S6 + .05, CX + 150, 680, 8, 64))
        ka = window(t, T_WON - .1, T_S6 + .05, .1, .2)
        if ka > 0:                                           # visual gag beat: the seat padlock pops open
            u.append(1); d = D(img)
            d.rect(GX - 92, 640, GX + 92, 810, (14, 16, 22, int(230 * ka)), r=24)
            seat_icon(d, GX - 10, 740, .9, (255, 150, 60))
            padlock(d, GX + 40, 700, 1.1, open_=io(prog(t, T_WON - .1, .3)), col=GREEN)
    else:
        u.append(tag(img, t, '105', T_105, T_FINAL - .05, 560, -3))
        if t >= T_YESNO - .05 and t < T_CARD:
            u.append(1); d = D(img)
            for i, (txt, col) in enumerate((('YES', GREEN), ('NO', RED))):
                k_ = popin(t, T_YESNO - .05 + i * .3, .3)
                if k_ <= .02: continue
                cx = CX - 170 + i * 340
                d.rect(cx - 130 * k_, 560 - 70 * k_, cx + 130 * k_, 560 + 70 * k_, col, r=24, ol=(255, 255, 255), w=6)
                d.text(cx, 560, txt, 84 * k_, (255, 255, 255), stroke=4, sc=(10, 10, 16))
    if t >= T_CARD:                                          # final caption
        u.append(1)
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(FINAL):
            k_ = popin(t, T_CARD + .06 * i, .3)
            if k_ > .05:
                d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if any(u) else None

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
    bed = room + hum * (env(T_S4, T_S6))                     # factory/press hum
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
    for k_ in range(4): add(0.02 + k_ * 0.3, step(), .5)
    add(T_HEATED, sfx.sparkle(), .18)                        # seat heater glows...
    add(T_PAIDIT + .1, click(900, 1400, .08), .7); add(T_PAIDIT + .15, sfx.thump(.2), .3)   # ...and the lock snaps on
    add(T_UNDER - .05, sfx.pop(), .3)
    add(T_CLOSE, sfx.whoosh(.3, 14), .3)
    add(T_INST - .1, sfx.pop(), .35); add(T_INST + .05, sfx.ding(1320, .6), .14)
    add(T_LOCK, click(900, 1400, .08), .7); add(T_LOCK + .05, sfx.buzzer(.2), .2)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    for s_ in SCENES[1:5]:                                  # buyer hurrying in
        for k_ in range(3): add(s_ + .08 + k_ * .25, step(), .35)
    for k_ in range(3): add(T_S6 + .05 + k_ * .42, step(), .3)
    add(T_UNLOCK, click(1800, 2600, .05), .8); add(T_UNLOCK + .1, sfx.buzzer(.25), .22)
    add(T_18 - .05, sfx.pop(), .35); add(T_18 + .3, sfx.cha_ching(), .3)
    add(T_MONTH2, sfx.stamp(), .35)
    add(T_176 - .05, sfx.pop(), .3); add(T_176 + .3, sfx.coin_clink(), .3)
    for tp in (T_BRIT, T_GER, T_SK, T_2022 + .1, T_2022 + .25): add(tp - .05, sfx.pop(), .2)
    add(T_2022 + .35, sfx.stamp(), .3); add(T_2022 + .45, sfx.buzzer(.25), .18)
    add(T_406 - .05, sfx.pop(), .35); add(T_406 + .3, sfx.cha_ching(), .38)
    add(T_WHY + .3, sfx.pop(), .3)
    for tp in (T_ONE, T_SWITCH): add(tp - .05, sfx.pop(), .3)
    add(T_SWITCH + .1, sfx.ding(1568, .5), .12); add(T_FEE - .05, sfx.cha_ching(), .3)
    add(T_NOT, sfx.stamp(), .32); add(T_2023 - .05, sfx.stamp(), .32); add(T_DROP, sfx.stamp(), .3)
    for ft in FLASHES: add(ft, click(3200, 4400, .05), .35)
    add(T_WON - .1, click(1400, 2000, .06), .6); add(T_WON, sfx.confetti(), .25)
    add(T_REMOTE, sfx.whoosh(.35, 20), .3); add(T_REMOTE + .55, click(900, 1400, .08), .8); add(T_REMOTE + .6, sfx.thump(.2), .35)
    add(T_105 - .05, sfx.pop(), .35); add(T_105 + .3, sfx.cha_ching(), .35)
    for k_ in range(2): add(BEAT[0] + .15 + k_ * .3, tick(), .6)
    add(T_YESNO - .05, sfx.pop(), .3); add(T_YESNO + .25, sfx.pop(), .3)
    add(T_CARD - .02, sting(), .55); add(T_CARD, sfx.pop(), .35)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s
    # background music (user-supplied track), ducked under the dialogue, fades at the ends
    mus = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(MUSIC_START), '-i', MUSIC, '-t', str(DUR), '-ac', '1',
                                        '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    mus = np.pad(mus, (0, max(0, n - len(mus))))[:n]
    mus /= max(1e-6, np.sqrt(np.mean(mus ** 2)))
    env_v = lpf(np.abs(v), int(SR * .08)); env_v = env_v / max(1e-6, env_v.max())
    duck = 1 - 0.55 * np.clip(env_v * 6, 0, 1)
    duck = lpf(duck, int(SR * .12))
    fade_ = np.clip(T_ / .25, 0, 1) * np.clip((DUR - T_) / 1.0, 0, 1)
    mixd = v * 1.0 + fxa[:n] * 0.5 + bed * 0.4 + mus * 0.055 * duck * fade_
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
