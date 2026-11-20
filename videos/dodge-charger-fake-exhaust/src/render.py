"""Dodge Charger fake-exhaust skit: Dodge showroom -> garage -> night car meet -> recording studio -> suburban street at
dawn -> drag strip at night. Flat-vector style, 1080x1920 @30. Built on bmw-heated-seats/src/render.py: same cast, caption
system, camera, whip pans and mix chain. Every location is a layered, living set with one background oddity (never mentioned).
Usage: python render.py video VOICE.wav OUT.mp4 | python render.py still T OUT.png [VOICE] | python render.py meta OUT.json
       | python render.py thumb OUT.png"""
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
DUR = round(WORDS[-1]['e'] + 2.3, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/dodge/voice.wav')
PHOTO = os.path.join(HERE, '..', 'assets', 'charger.jpg')        # the one real car (user / Wikimedia Commons photo)
HAS_PHOTO = os.path.exists(PHOTO)

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
FIRST = {2: 1, 4: 2, 8: 3, 10: 4, 12: 5}                   # first line of each scene -> scene index
SCENES = [0.0] + [LS[li] - 0.32 for li in sorted(FIRST)]
T_S2, T_S3, T_S4, T_S5, T_S6 = SCENES[1:]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
T_FAKE, T_HELL = word_t(0, 'fake'), word_t(0, 'Hellcat')
T_SPK, T_NOT = word_t(1, 'speaker'), word_t(1, 'Not')
T_SPKS, T_TUNE, T_AMP, T_GAS = word_t(3, 'Speakers'), word_t(3, 'tuning'), word_t(3, 'amp'), word_t(3, 'gas')
T_LOUD, T_HUND, T_DB, T_SAME = word_t(4, 'loud'), word_t(5, 'hundred'), word_t(5, 'decibels'), word_t(5, 'Same')
T_FRATZ, T_LOGO = LS[6], word_t(7, 'Fratzog')
T_REC, T_ITSELF, T_REVIEW, T_GEARS = word_t(8, 'recording'), word_t(9, 'itself'), word_t(9, 'Reviewers'), word_t(9, 'gears')
T_LOUDER, T_DRAG, T_STEALTH, T_NEIGH = word_t(10, 'louder'), word_t(11, 'Drag'), word_t(11, 'Stealth'), word_t(11, 'neighbours')
T_FASTER = word_t(12, 'faster')
T_ZERO, T_33, T_39 = word_t(13, 'zero'), word_t(13, 'three', 0), word_t(13, 'three', 2)
T_WINS = word_t(14, 'wins')
BEAT = (LE[14], LS[15])
T_FINAL = LS[15]
T_CARD = LE[15] + 0.3                      # final caption card (last ~2 s)
T_RACE = T_ZERO - 0.15                     # drag race launch

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


# ================================================================ cars
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

# ================================================================ the Charger (side profile, front to the left; generic drawing)
CHG_CTRL = [(.004, .18), (0.0, .34), (.004, .47), (.03, .52), (.17, .56), (.34, .60), (.47, .86), (.58, .91), (.70, .88),
            (.86, .70), (.97, .62), (1.0, .57), (1.0, .32), (.985, .18), (.86, .15), (.5, .16), (.14, .15)]
RED_CHG = ((196, 22, 32), (250, 92, 92), (110, 10, 16))
GREY_CHG = ((70, 74, 84), (150, 156, 168), (28, 30, 36))
CHG_S = dict(rim=(36, 38, 44), n=5, dbl=True, cal=(220, 30, 40))

def charger(d, x0, ground, L, col=RED_CHG, gas=False, lit=True):
    """2-door Charger fastback: blunt nose with the pass-through wing slot, light bar, full-width tail light."""
    Hh = L * .36
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    base, hi, lo = col
    d.ell(x0 + L * .5, ground + 4, L * .58, 14, (0, 0, 0, 90))
    body = spline([P(u, v) for u, v in CHG_CTRL], 8)
    shade(d, body, hi, lo, ground - .95 * Hh, ground - .2 * Hh)
    shade(d, spline([P(.02, .17), P(.5, .18), P(.98, .17), P(.99, .27), P(.5, .25), P(.01, .26)], 6), (34, 34, 40), (16, 16, 20),
          ground - .27 * Hh, ground - .16 * Hh)                                             # black sill
    d.line(spline([P(.03, .47), P(.30, .50), P(.62, .53), P(.97, .55)], 8, closed=False), hi + (220,), 3)   # shoulder light
    d.line([P(.06, .40), P(.30, .43)], lo, 3)                                              # lower crease
    if not gas:                                                                            # twin hood stripes on the EV
        d.poly([P(.05, .525), P(.33, .595), P(.33, .58), P(.06, .515)], (20, 20, 24, 200))
    r = Hh * .30
    for u in (.165, .80):
        wx, wy = P(u, 0)[0], ground - r
        d.chord(wx, wy, r * 1.2, r * 1.2, 180, 360, (14, 14, 16))
        d.rect(wx - r * 1.2, wy - 2, wx + r * 1.2, ground - 4, (14, 14, 16))
        d.arc(wx, wy, r * 1.24, r * 1.24, 190, 350, (26, 26, 30), 7)
    d.poly(body, None, (24, 26, 34), 5)
    gh = spline([P(.38, .62), P(.48, .83), P(.58, .875), P(.69, .845), P(.79, .70), P(.76, .63)], 5)
    shade(d, gh, (90, 110, 136), (14, 18, 28), ground - .9 * Hh, ground - .6 * Hh)
    d.poly(gh, None, (20, 22, 28), 4)
    d.poly([P(.42, .64), P(.45, .64), P(.51, .80), P(.48, .80)], (255, 255, 255, 50))
    d.line([P(.37, .60), P(.35, .22)], lo, 3)                                              # long coupe door
    d.line([P(.70, .62), P(.71, .22)], lo, 3)
    d.rect(*P(.58, .52), *P(.63, .50), (30, 30, 34), r=3)
    d.poly(spline([P(.385, .64), P(.43, .67), P(.43, .72), P(.39, .72)], 4), (24, 24, 28), (24, 26, 34), 3)
    d.poly([P(-.004, .19), P(.07, .20), P(.06, .31), P(0, .32)], (18, 18, 22))           # lower intake
    d.poly([P(.004, .48), P(.10, .535), P(.10, .51), P(.006, .455)], (16, 16, 20))       # the wing slot through the nose
    lb = (255, 250, 240) if lit else (200, 204, 212)
    d.line([P(.002, .43), P(.03, .44)], lb, 5)                                             # front light bar
    if lit: d.ell(*P(.012, .435), 26, 12, (255, 250, 230, 60))
    d.poly([P(.01, .37), P(.025, .41), P(.04, .37)], (230, 40, 48) if lit else (120, 30, 36))   # little lit badge (generic)
    d.line([P(.975, .545), P(1.0, .54)], (255, 40, 48), 7)                                 # full-width tail light
    if lit: d.ell(*P(.995, .54), 22, 10, (255, 40, 48, 70))
    if gas:                                                                                # gas car: quad tailpipes, hood scoop
        for dv in (.21, .25):
            d.rect(*P(.985, dv + .02), *P(1.012, dv), (190, 194, 202), r=3, ol=(60, 60, 66), w=2)
        d.poly([P(.12, .565), P(.20, .585), P(.20, .61), P(.13, .59)], (20, 20, 24))
    for u in (.165, .80):
        wheel(d, P(u, 0)[0], ground - r, r, CHG_S)

@lru_cache(None)
def charger_layer(L, col=RED_CHG, gas=False, lit=True):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .55) * K), (0, 0, 0, 0))
    charger(D(img, ox=-L * .1, oy=-L * .5), 0, 0, L, col, gas, lit)
    return img
def paste_charger(img, x0, ground, L, col=RED_CHG, gas=False, lit=True):
    c = charger_layer(L, col, gas, lit)
    img.paste(c, (int((x0 - L * .1) * K), int((ground - L * .5) * K)), c)

def fratzog(d, cx, cy, s, col):
    """Generic split-triangle mark (hand drawn, not the logo file)."""
    for dx in (-1, 1):
        d.poly([(cx + dx * 6 * s, cy - 40 * s), (cx + dx * 46 * s, cy + 30 * s), (cx + dx * 6 * s, cy + 30 * s)], None, col, 7 * s)

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

BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('1f1f25'), suit2=hexc('0c0c10'),
             shirt=hexc('f7f7fa'), tie=hexc('d01824'), pants=hexc('1f1f25'), shoe=hexc('1a1a1e'), glasses=False, hairstyle='part', lids=0.45,
             piping=hexc('d01824'))                     # Dodge black and red: red tie, lapel piping, pocket square, badge
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
        d.line([(x + s * 42, top - 14), (x + s * 8, top + 200)], c.get('piping', c['suit2']), 6)
        d.poly([(x + s * 42, top - 14), (x + s * 70, top + 70), (x + s * 50, top + 80), (x + s * 14, top + 190)], c['suit2'])
    for by in (230, 290):
        d.ell(x + 2, top + by, 7, 7, c['suit2'])
    if c.get('badge', not c['glasses']):                  # dealer name badge with a tiny wing mark
        d.rect(x + 46, top + 92, x + 100, top + 118, (245, 245, 248), r=4)
        if c.get('piping'):
            d.rect(x + 54, top + 98, x + 92, top + 112, c['piping'], r=3)
            d.poly([(x - 100, top + 110), (x - 62, top + 110), (x - 74, top + 92), (x - 88, top + 96)], c['piping'])
        else:
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


# ================================================================ helpers for layered sets
def rng_for(seed): return np.random.default_rng(seed)
def glow(img, cx, cy, r, col, a=120):
    """Soft additive-looking light blob (screen blend of a blurred disc)."""
    m = Image.new('L', (int(r * 4 * K), int(r * 4 * K)), 0)
    ImageDraw.Draw(m).ellipse([r * K, r * K, r * 3 * K, r * 3 * K], fill=a)
    m = m.filter(ImageFilter.GaussianBlur(r * K * .45))
    layer = Image.new('RGB', m.size, col)
    x, y = int((cx - 2 * r) * K), int((cy - 2 * r) * K)
    box = (x, y, x + m.width, y + m.height)
    base = img.crop(box).convert('RGB')
    from PIL import ImageChops
    lit = ImageChops.screen(base, layer)
    img.paste(Image.composite(lit, base, m), (x, y))

def cone(img, x, top, w0, w1, h, col, a=40, blur=20):
    c = Image.new('L', img.size, 0)
    ImageDraw.Draw(c).polygon([(p * K, q * K) for p, q in [(x - w0, top), (x + w0, top), (x + w1, top + h), (x - w1, top + h)]], fill=a)
    c = c.filter(ImageFilter.GaussianBlur(blur * K))
    return Image.composite(Image.new('RGB', img.size, col), img, c)

def catenary(x0, y0, x1, y1, sag, n=24):
    return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n + sag * 4 * (i / n) * (1 - i / n)) for i in range(n + 1)]

def rings(d, cx, cy, t, t0, t1, col=(255, 70, 70), n=3, rate=1.6, rmax=230):
    """Expanding sound arcs to the right of a point while t0 <= t < t1."""
    if not t0 <= t < t1: return
    for i in range(n):
        ph = ((t - t0) * rate + i / n) % 1
        r = 30 + rmax * ph
        a = int(220 * (1 - ph) * min(1, (t1 - t) * 4))
        d.arc(cx, cy, r, r * .8, -50, 50, col + (a,), 7 - 4 * ph)

def zzz(d, x, y, t, a=1.0, s=1.0):
    for i in range(3):
        ph = (t * .5 + i / 3) % 1
        d.text(x + 26 * ph * s + i * 4, y - 70 * ph * s, 'z', (22 + 12 * ph) * s, (250, 250, 255, int(230 * a * (1 - ph))), path=FONT_X)

# ================================================================ background oddities (comment bait, never mentioned)
# 1 showroom: a penguin pushing a shopping trolley full of fish.   2 garage: a chicken in headphones nodding on the shelf.
# 3 car meet: a grandma doing a burnout on a mobility scooter.   4 studio: a cow singing in the vocal booth.
# 5 dawn street: a horse in a nightcap looking out of an upstairs window.   6 drag strip: a giraffe in ear defenders in the stands.
def penguin_trolley(d, x, fy, t, s=1.0):
    wob = math.sin(t * 9) * 4 * s
    # trolley in front (to the left: it pushes leftwards)
    tx = x - 120 * s
    for wx in (tx - 44 * s, tx + 44 * s):
        d.ell(wx, fy - 8 * s, 9 * s, 9 * s, (40, 40, 44))
    d.poly([(tx - 64 * s, fy - 120 * s), (tx + 60 * s, fy - 120 * s), (tx + 48 * s, fy - 30 * s), (tx - 52 * s, fy - 30 * s)],
           (200, 206, 214, 90), (120, 126, 136), 3 * s)
    for i in range(5):
        fx_ = tx - 44 * s + i * 22 * s; fy_ = fy - 128 * s - (i % 2) * 12 * s
        d.ell(fx_, fy_, 20 * s, 9 * s, (120, 150, 176), OL, 2)
        d.poly([(fx_ + 18 * s, fy_), (fx_ + 30 * s, fy_ - 9 * s), (fx_ + 30 * s, fy_ + 9 * s)], (120, 150, 176))
        d.ell(fx_ - 10 * s, fy_ - 2 * s, 2 * s, 2 * s, OL)
    for yy in (-100, -70, -45):
        d.line([(tx - 58 * s, fy + yy * s), (tx + 52 * s, fy + yy * s)], (120, 126, 136), 2)
    d.line([(tx + 60 * s, fy - 120 * s), (x - 20 * s, fy - 110 * s)], (120, 126, 136), 4 * s)      # handle
    # penguin
    d.ell(x, fy - 70 * s + wob * .3, 40 * s, 70 * s, (28, 30, 38), OL, 3)
    d.ell(x - 8 * s, fy - 62 * s + wob * .3, 28 * s, 54 * s, (246, 246, 250))
    d.ell(x - 4 * s, fy - 138 * s, 28 * s, 26 * s, (28, 30, 38), OL, 3)
    d.ell(x - 14 * s, fy - 142 * s, 6 * s, 6 * s, (255, 255, 255)); d.ell(x - 16 * s, fy - 142 * s, 3 * s, 3 * s, OL)
    d.poly([(x - 30 * s, fy - 136 * s), (x - 50 * s, fy - 130 * s), (x - 30 * s, fy - 126 * s)], (250, 160, 40))
    d.line([(x - 30 * s, fy - 96 * s), (x - 20 * s, fy - 110 * s)], (28, 30, 38), 10 * s)       # flipper on the handle
    for side in (-1, 1):
        d.ell(x + side * 14 * s + (wob if side > 0 else -wob) * .5, fy - 4 * s, 16 * s, 6 * s, (250, 160, 40))

def chicken_dj(d, x, fy, t, s=1.0):
    bob = abs(math.sin(t * 6.3)) * 8 * s
    d.ell(x, fy - 34 * s, 40 * s, 32 * s, (250, 248, 240), OL, 3)
    d.poly([(x + 30 * s, fy - 52 * s), (x + 56 * s, fy - 70 * s), (x + 50 * s, fy - 40 * s)], (250, 248, 240), OL, 3)  # tail
    hx, hy = x - 30 * s, fy - 78 * s + bob
    d.line([(x - 20 * s, fy - 50 * s), (hx, hy)], (250, 248, 240), 22 * s)
    d.ell(hx, hy, 20 * s, 20 * s, (250, 248, 240), OL, 3)
    d.poly([(hx - 6 * s, hy - 18 * s), (hx, hy - 32 * s), (hx + 6 * s, hy - 20 * s), (hx + 12 * s, hy - 30 * s), (hx + 14 * s, hy - 14 * s)], (226, 40, 46))
    d.poly([(hx - 18 * s, hy), (hx - 34 * s, hy + 5 * s), (hx - 18 * s, hy + 9 * s)], (250, 180, 40))
    d.ell(hx - 6 * s, hy + 16 * s, 5 * s, 8 * s, (226, 40, 46))
    d.ell(hx - 6 * s, hy - 4 * s, 3 * s, 3 * s, OL)
    d.arc(hx, hy - 2 * s, 25 * s, 25 * s, 180, 360, (30, 30, 34), 5 * s)                  # headphones
    d.ell(hx + 22 * s, hy, 8 * s, 12 * s, (220, 40, 46), OL, 2)
    for side in (-8, 8):
        d.line([(x + side * s, fy - 6 * s), (x + side * s, fy)], (250, 180, 40), 3 * s)
    for i in range(2):                                                                      # music notes
        ph = (t * .7 + i * .5) % 1
        d.text(hx + 30 * s + 30 * ph * s, hy - 30 * s - 60 * ph * s, '♪', 30 * s, (255, 230, 120, int(255 * (1 - ph))), path=FONT_X)

def grandma_burnout(d, x, fy, t, s=1.0):
    sh = math.sin(t * 40) * 2 * s
    for i in range(6):                                                                      # tyre smoke drifting right/up
        ph = (t * .6 + i / 6) % 1
        d.ell(x + 70 * s + 140 * ph * s, fy - 20 * s - 90 * ph * s, (24 + 50 * ph) * s, (18 + 40 * ph) * s,
              (220, 220, 230, int(150 * (1 - ph))))
    d.ell(x + 58 * s, fy - 16 * s, 22 * s, 22 * s, (30, 30, 34))
    d.ell(x - 50 * s, fy - 16 * s, 22 * s, 22 * s, (30, 30, 34))
    d.poly([(x - 80 * s, fy - 30 * s + sh), (x + 84 * s, fy - 30 * s + sh), (x + 74 * s, fy - 62 * s + sh), (x - 70 * s, fy - 62 * s + sh)],
           (210, 40, 50), OL, 3)
    d.line([(x - 60 * s, fy - 60 * s + sh), (x - 74 * s, fy - 150 * s + sh)], (60, 60, 66), 6 * s)   # tiller
    d.rect(x - 98 * s, fy - 160 * s + sh, x - 54 * s, fy - 134 * s + sh, (190, 150, 90), r=4, ol=OL, w=2)   # basket
    d.line([(x - 90 * s, fy - 158 * s + sh), (x - 66 * s, fy - 168 * s + sh)], (230, 230, 236), 4 * s)    # flag
    d.poly([(x - 66 * s, fy - 168 * s + sh), (x - 30 * s, fy - 176 * s + sh + math.sin(t * 12) * 4), (x - 64 * s, fy - 188 * s + sh)], (255, 214, 64))
    d.ell(x + 12 * s, fy - 110 * s + sh, 34 * s, 48 * s, (230, 140, 170), OL, 3)          # cardigan
    d.ell(x + 8 * s, fy - 176 * s + sh, 26 * s, 28 * s, (240, 200, 170), OL, 3)
    d.ell(x + 20 * s, fy - 202 * s + sh, 18 * s, 14 * s, (220, 220, 226), OL, 2)           # grey bun
    d.chord(x + 8 * s, fy - 182 * s + sh, 28 * s, 26 * s, 180, 360, (220, 220, 226))
    for side in (-1, 1):
        d.ell(x + side * 11 * s - 2 * s, fy - 176 * s + sh, 8 * s, 8 * s, None, (90, 90, 100), 2)
    d.arc(x + 4 * s, fy - 162 * s + sh, 10 * s, 6 * s, 20, 160, OL, 3)                     # grin
    d.line([(x - 6 * s, fy - 120 * s + sh), (x - 66 * s, fy - 146 * s + sh)], (230, 140, 170), 12 * s)    # arm on the tiller

def cow_singer(d, x, y, t, s=1.0):
    sing = .5 + .5 * math.sin(t * 7)
    d.ell(x, y + 150 * s, 110 * s, 90 * s, (250, 250, 250), OL, 3)                       # shoulders
    d.ell(x - 40 * s, y + 140 * s, 34 * s, 26 * s, (30, 30, 34)); d.ell(x + 50 * s, y + 170 * s, 26 * s, 20 * s, (30, 30, 34))
    for side in (-1, 1):
        d.poly([(x + side * 40 * s, y - 50 * s), (x + side * 70 * s, y - 90 * s), (x + side * 56 * s, y - 44 * s)], (240, 230, 200), OL, 2)  # horns
        d.ell(x + side * 74 * s, y - 20 * s, 26 * s, 12 * s, (250, 250, 250), OL, 3)       # ears
    d.ell(x, y, 62 * s, 70 * s, (250, 250, 250), OL, 3)
    d.ell(x + 24 * s, y - 30 * s, 22 * s, 18 * s, (30, 30, 34))
    d.ell(x, y + 42 * s, 46 * s, 30 * s, (246, 180, 190), OL, 3)
    for side in (-1, 1):
        d.ell(x + side * 16 * s, y + 38 * s, 5 * s, 6 * s, (150, 80, 90))
        d.ell(x + side * 22 * s, y - 14 * s, 8 * s, 9 * s, OL)
    d.ell(x, y + 64 * s, (10 + 8 * sing) * s, (4 + 12 * sing) * s, (90, 30, 40))
    d.arc(x, y - 10 * s, 72 * s, 74 * s, 190, 350, (30, 30, 34), 6 * s)                  # headphones
    for side in (-1, 1): d.ell(x + side * 70 * s, y - 6 * s, 12 * s, 18 * s, (40, 40, 46), OL, 2)
    for i in range(2):
        ph = (t * .6 + i * .5) % 1
        d.text(x + 90 * s + 50 * ph * s, y - 40 * s - 90 * ph * s, '♫', 36 * s, (255, 230, 140, int(255 * (1 - ph))), path=FONT_X)

def horse_window(d, x, y, t, s=1.0):
    tw = math.sin(t * 3) * 3
    d.ell(x + 10 * s, y + 70 * s, 54 * s, 40 * s, (150, 96, 60), OL, 3)                  # neck
    d.poly(spline([(x - 30 * s, y - 20 * s), (x + 26 * s, y - 36 * s), (x + 40 * s, y + 20 * s), (x - 20 * s, y + 60 * s),
                   (x - 60 * s, y + 50 * s), (x - 56 * s, y + 10 * s)], 4), (160, 104, 66), OL, 3)
    d.ell(x - 48 * s, y + 40 * s, 22 * s, 18 * s, (120, 76, 50))
    d.ell(x - 52 * s, y + 36 * s, 4 * s, 3 * s, OL)
    d.ell(x + 2 * s, y - 6 * s, 6 * s, 6 * s, OL)
    d.line([(x - 8 * s, y - 12 * s), (x + 8 * s, y - 14 * s)], (120, 76, 50), 3 * s)        # sleepy lid
    d.poly([(x + 18 * s, y - 34 * s), (x + 30 * s, y - 60 * s + tw), (x + 34 * s, y - 30 * s)], (160, 104, 66), OL, 2)
    d.poly([(x - 10 * s, y - 30 * s), (x + 40 * s, y - 44 * s), (x + 90 * s, y - 10 * s + tw), (x + 70 * s, y - 50 * s)], (120, 150, 220), OL, 2)  # nightcap
    d.ell(x + 92 * s, y - 6 * s + tw, 9 * s, 9 * s, (255, 255, 255), OL, 2)
    d.line([(x + 18 * s, y - 30 * s), (x + 36 * s, y + 4 * s)], (60, 40, 30), 5 * s)        # mane

def giraffe(d, x, fy, t, s=1.0):
    sw = math.sin(t * 1.3) * 10 * s
    hx, hy = x + sw, fy - 300 * s
    d.line([(x, fy), (hx, hy + 30 * s)], OL, 40 * s); d.line([(x, fy), (hx, hy + 30 * s)], (240, 190, 90), 32 * s)
    for i in range(5):
        k_ = i / 5
        d.ell(x + (hx - x) * k_ + 4 * s, fy + (hy - fy) * k_, 7 * s, 9 * s, (170, 110, 50))
    d.ell(hx - 18 * s, hy + 10 * s, 26 * s, 16 * s, (240, 190, 90), OL, 3)
    d.ell(hx, hy, 30 * s, 24 * s, (240, 190, 90), OL, 3)
    for side in (-1, 1):
        d.line([(hx + side * 8 * s, hy - 20 * s), (hx + side * 10 * s, hy - 40 * s)], (170, 110, 50), 5 * s)
    d.ell(hx - 6 * s, hy - 4 * s, 4 * s, 4 * s, OL)
    d.arc(hx, hy - 8 * s, 30 * s, 26 * s, 180, 360, (30, 30, 34), 5 * s)                  # ear defenders
    for side in (-1, 1): d.ell(hx + side * 30 * s, hy - 2 * s, 9 * s, 13 * s, (226, 40, 46), OL, 2)

# ================================================================ sets
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))
def stack(*parts):
    """Vertical gradient bands: (height, c0, c1) ... -> PIL image W x sum(h)."""
    return Image.fromarray(np.concatenate([grad(int(h) * K, W * K, c0, c1) for h, c0, c1 in parts]).astype(np.uint8))
def spot(img, cx, top, w0, w1, h, a=55):
    return cone(img, cx, top, w0, w1, h, (255, 250, 238), a, 28)

# ---- 1 Dodge showroom: street windows, red feature wall with a live screen, track lights, polished floor
SW = (0, 560, 120, 900)                                                  # street window
def mullions(d):
    x0, x1, y0, y1 = SW
    for x in range(x0, x1 + 1, 140):
        d.rect(x - 5, y0, x + 5, y1, (58, 62, 70))
    d.rect(x0, 470, x1, 478, (58, 62, 70))
    for i in range(4):
        d.poly([(40 + i * 140, y1 - 40), (90 + i * 140, y1 - 40), (130 + i * 140, y0 + 40), (80 + i * 140, y0 + 40)], (255, 255, 255, 26))

@lru_cache(None)
def bg_showroom():
    img = stack((WALL_Y, (238, 238, 240), (222, 222, 226)), (H - WALL_Y, (186, 188, 194), (126, 128, 136)))
    x0, x1, y0, y1 = SW
    out = Image.fromarray(grad((y1 - y0) * K, (x1 - x0) * K, (118, 176, 234), (214, 236, 250)).astype(np.uint8))
    od = D(out, ox=x0, oy=y0)
    for bx, bw, bh, c in ((0, 120, 300, (176, 196, 216)), (110, 90, 400, (160, 182, 206)), (190, 150, 250, (186, 204, 222)),
                          (330, 110, 430, (166, 186, 210)), (430, 140, 300, (178, 198, 218))):
        od.rect(bx, y1 - 120 - bh, bx + bw, y1 - 120, c)
        for wy in range(y1 - 104 - bh, y1 - 150, 34):
            for wx in range(bx + 12, bx + bw - 16, 26):
                od.rect(wx, wy, wx + 12, wy + 18, (222, 234, 246))
    for tx in (60, 210, 350, 500):
        od.rect(tx - 6, y1 - 200, tx + 6, y1 - 118, (110, 80, 60))
        for dx, dy, r in ((0, -236, 52), (-34, -204, 40), (34, -206, 42)):
            od.ell(tx + dx, y1 + dy, r, r, (78, 150, 92)); od.ell(tx + dx - 12, y1 + dy - 14, r * .5, r * .4, (118, 192, 118))
    od.rect(x0, y1 - 120, x1, y1 - 98, (206, 206, 200))
    od.rect(x0, y1 - 98, x1, y1, (108, 110, 118))
    for x in range(0, 560, 90): od.rect(x, y1 - 52, x + 50, y1 - 46, (240, 240, 236))
    img.paste(out, (x0 * K, y0 * K))
    d = D(img)
    img.paste(Image.fromarray(grad((WALL_Y - 8 - 84) * K, (W - 560) * K, (200, 26, 36), (128, 12, 20)).astype(np.uint8)), (560 * K, 84 * K))
    d = D(img)
    for k_ in range(2):                                                  # diagonal racing stripes across the red wall
        o = k_ * 46
        d.poly([(560, 700 + o), (W, 520 + o), (W, 548 + o), (560, 728 + o)], (24, 20, 22, 200))
    d.text(815, 200, 'D O D G E', 70, (255, 255, 255), path=FONT_B)
    d.rect(628, 300, 1032, 540, (16, 16, 20), r=10, ol=(40, 40, 46), w=6)                   # wall screen (content is live)
    mullions(d)
    d.rect(0, 0, W, 84, (44, 46, 52)); d.rect(0, 78, W, 84, (24, 24, 28))
    for px in (120, 300, 640, 880):                                      # track lights
        d.rect(px - 60, 84, px + 60, 92, (30, 30, 34))
        d.poly([(px - 14, 92), (px + 14, 92), (px + 22, 130), (px - 6, 134)], (34, 34, 38))
        d.ell(px + 8, 132, 14, 6, (255, 244, 210))
    d.rect(0, WALL_Y - 8, W, WALL_Y, (200, 26, 36)); d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    vx, vy = CX, 640                                                     # floor tiles converge on a vanishing point
    for xb in range(-1600, 2700, 170):
        k0 = (WALL_Y - vy) / (H - vy)
        d.line([(vx + (xb - vx) * k0, WALL_Y + 6), (xb, H)], (210, 212, 218, 90), 2)
    for i, y in enumerate((990, 1060, 1160, 1300, 1490, 1740)):
        d.line([(0, y), (W, y)], (210, 212, 218, 90), 2)
    for x in (1000,):                                                     # potted plant
        d.poly([(x - 34, 940), (x + 34, 940), (x + 26, 860), (x - 26, 860)], (60, 60, 66))
        for a in range(-60, 61, 24):
            ra = math.radians(a - 90)
            d.line([(x, 862), (x + 70 * math.cos(ra), 862 + 110 * math.sin(ra))], (60, 140, 80), 12)
            d.ell(x + 74 * math.cos(ra), 862 + 116 * math.sin(ra), 16, 26, (80, 170, 96))
    d.rect(596, 790, 650, 940, (40, 40, 46), r=6)                          # brochure stand
    for i in range(3): d.rect(602, 800 + i * 44, 644, 836 + i * 44, ((220, 30, 40), (240, 240, 244), (30, 30, 34))[i], r=3)
    img = spot(img, CX, 132, 70, 470, 800)
    d = D(img)
    d.ell(CX, 905, 400, 50, (14, 16, 16))
    d.ell(CX, 897, 394, 44, (60, 60, 66), (200, 26, 36), 5)
    d.ell(CX, 897, 340, 34, (74, 74, 80))
    return img

def showroom_life(img, t):
    x0, x1, y0, y1 = SW                                                   # traffic outside the window
    for i, (spd, off, col) in enumerate(((150, 0, (60, 120, 210)), (-110, 420, (240, 200, 60)))):
        cx_ = (off + spd * t) % 900 - 220
        L = 190 if i == 0 else 160
        c = road_car(col, L)
        ly = y1 - 40 - (0 if i == 0 else 30)
        lay = c.transpose(Image.FLIP_LEFT_RIGHT) if spd > 0 else c
        box = (int((cx_ - L * .1) * K), int((ly - L * .6) * K))
        win = img.crop((0, y0 * K, x1 * K, y1 * K))
        win.paste(lay, (box[0], box[1] - y0 * K), lay)
        img.paste(win, (0, y0 * K))
    d = D(img)
    mullions(d)
    for i in range(24):                                                   # wall screen: a live red waveform
        h = 10 + 50 * abs(math.sin(t * (3 + i % 5) + i * .7)) * (1.3 if t < LE[0] else .6)
        d.rect(650 + i * 15.5, 400 - h, 660 + i * 15.5, 400 + h, (230, 40, 48) if i % 3 else (255, 255, 255))
    d.text(830, 518, 'FRATZONIC', 24, (255, 255, 255, 220), path=FONT_X)
    reception(img, t, True)
    x = 980 - 120 * t
    if -80 < x < 1000:
        npc(img, x, 952, .34, NPC['walker'], walkst(t, 9, lp='rest', rp=(60, 210), prop={'rpose': 'cup'}, look=-1))
    d = D(img)
    for i, (bx, col) in enumerate(((1036, (226, 40, 48)), (1062, (30, 30, 34)), (1046, (255, 255, 255)))):   # balloons
        sw_ = math.sin(t * 1.4 + i) * 10
        d.line([(1000, 860), (bx + sw_, 680 - i * 30)], (120, 120, 126), 2)
        d.ell(bx + sw_, 650 - i * 30, 26, 32, col, OL, 3)
    penguin_trolley(d, 990 - 40 * t, 980, t, .62)

def showroom_car(img, t):
    shake = math.sin(t * 55) * 2 if t < LE[0] else 0
    paste_charger(img, CX - 290, 894 + shake, 580)
    d = D(img)
    rings(d, CX - 290 + 580 + 6, 810, t, 0.0, LE[0] + .2, (230, 40, 48), 3, 1.8, 200)      # the "exhaust" roaring at the hook

# ---- 2 garage: brick wall, car up on the lift (no tailpipes), the speaker rig on the bench, pegboard, shelves
RIG = dict(spk=((110, 700, 220, 852), (230, 700, 340, 852)), chamber=(360, 760, 560, 852), amp=(580, 786, 724, 852))
@lru_cache(None)
def bg_garage():
    img = stack((WALL_Y, (164, 94, 66), (122, 66, 48)), (H - WALL_Y, (150, 150, 152), (104, 104, 110)))
    d = D(img)
    for r_, y in enumerate(range(80, WALL_Y, 30)):                       # bricks
        d.line([(0, y), (W, y)], (186, 132, 104, 160), 3)
        for x in range((r_ % 2) * 40, W, 80):
            d.line([(x, y), (x, y + 30)], (186, 132, 104, 160), 3)
    d.rect(0, 150, 230, WALL_Y, (120, 130, 146), ol=(60, 66, 76), w=6)   # roll-up door
    for y in range(160, WALL_Y, 34): d.line([(4, y), (226, y)], (90, 98, 112), 3)
    d.rect(840, 150, 1070, 470, (204, 170, 120), r=4, ol=(120, 90, 60), w=4)   # pegboard + tools
    for yy in range(166, 466, 22):
        for xx in range(856, 1066, 22): d.ell(xx, yy, 2, 2, (150, 120, 84))
    for i, x in enumerate(range(866, 1060, 36)):                         # spanners
        d.line([(x, 190), (x, 290 + i * 6)], (110, 116, 126), 9); d.ell(x, 186, 12, 12, None, (110, 116, 126), 6)
    d.line([(880, 340), (1000, 340)], (120, 80, 50), 12); d.rect(990, 318, 1030, 362, (70, 74, 82), r=4)      # hammer
    d.poly([(880, 400), (1040, 380), (1040, 420), (880, 440)], (190, 196, 206), (90, 96, 104), 3)             # saw
    for y in (560, 720):                                                 # shelves with cans and boxes
        d.rect(850, y, 1080, y + 12, (110, 76, 50))
        for i, x in enumerate(range(870, 1070, 52)):
            if y == 560 and 960 < x < 1040: continue
            col = ((220, 40, 48), (60, 120, 200), (240, 200, 60), (90, 160, 90))[i % 4]
            d.rect(x, y - 54, x + 38, y, col, r=4, ol=OL, w=2); d.rect(x, y - 44, x + 38, y - 34, (240, 240, 240))
    d.rect(0, 0, W, 70, (60, 56, 56))
    for x0_ in (120, 560):
        d.rect(x0_, 74, x0_ + 300, 90, (90, 90, 96), r=4)
    for px in (170, 750):                                                # lift posts and arms
        d.rect(px - 22, 300, px + 22, WALL_Y, (238, 188, 40), ol=(120, 90, 20), w=4)
        d.rect(px - 30, WALL_Y - 12, px + 30, WALL_Y, (90, 90, 96))
    paste_charger(img, CX - 280, 590, 560, GREY_CHG, lit=False)
    d = D(img)
    for px, ax in ((170, 250), (750, 650)):
        d.rect(min(px, ax) - 4, 596, max(px, ax) + 4, 610, (200, 160, 30), ol=(120, 90, 20), w=3)
    rx = CX - 280 + 560                                                  # rear: the chamber where tailpipes would be
    d.rect(rx - 70, 586, rx - 6, 612, (30, 30, 36), r=6, ol=(220, 40, 48), w=3)
    for i in range(3): d.ell(rx - 56 + i * 20, 599, 6, 6, (70, 70, 80))
    d.rect(0, WALL_Y - 6, W, WALL_Y + 6, (60, 60, 64))
    for ox, oy, rx_, ry_ in ((150, 1300, 120, 30), (840, 1500, 90, 22), (560, 1720, 140, 28)):
        d.ell(ox, oy, rx_, ry_, (70, 70, 76, 120))
    d.rect(0, 1000, W, 1012, (240, 200, 40))
    d.rect(80, 852, 840, 870, (156, 104, 62), ol=(96, 62, 36), w=3)       # workbench
    d.rect(92, 870, 828, 1000, (110, 74, 46), ol=(70, 46, 28), w=3)
    for x in (240, 460, 680): d.rect(x - 60, 900, x + 60, 960, (126, 86, 54), r=4, ol=(70, 46, 28), w=2); d.rect(x - 14, 924, x + 14, 932, (200, 200, 206))
    for (a, b, c_, e) in RIG['spk']:
        d.rect(a, b, c_, e, (30, 30, 36), r=8, ol=(10, 10, 12), w=4)
    a, b, c_, e = RIG['chamber']
    d.rect(a, b, c_, e, (70, 80, 96), r=24, ol=(30, 34, 42), w=5)
    for i in range(3): d.ell(a + 46 + i * 54, (b + e) / 2, 16, 16, (24, 26, 32), (120, 130, 146), 3)
    a, b, c_, e = RIG['amp']
    d.rect(a, b, c_, e, (24, 24, 28), r=6, ol=(70, 70, 78), w=3)
    for i in range(3): d.ell(a + 26 + i * 30, e - 18, 8, 8, (180, 184, 190))
    d.line([(220, 840), (300, 880), (360, 830)], (20, 20, 22), 5)        # cables
    d.line([(560, 830), (590, 870), (620, 846)], (20, 20, 22), 5)
    return img

def garage_life(img, t):
    d = D(img)
    if int(t * 13) % 7 == 0 or int(t * 5) % 9 == 0:                       # one flickering tube
        d.rect(560, 74, 860, 90, (90, 90, 96), r=4)
    else:
        d.rect(560, 74, 860, 90, (250, 252, 240), r=4)
        d.ell(710, 100, 190, 20, (255, 255, 230, 40))
    d.rect(120, 74, 420, 90, (250, 252, 240), r=4); d.ell(270, 100, 190, 20, (255, 255, 230, 40))
    live = 1.0 if (LS[3] <= t <= LE[3] + .3 or t < SCENES[1] + .4) else .35
    for (a, b, c_, e) in RIG['spk']:                                      # cones pump
        cx_, pk = (a + c_) / 2, 1 + .08 * live * abs(math.sin(t * 31))
        d.ell(cx_, b + 48, 32 * pk, 32 * pk, (60, 60, 70), (10, 10, 12), 4); d.ell(cx_, b + 48, 12 * pk, 12 * pk, (20, 20, 24))
        d.ell(cx_, b + 116, 20 * pk, 20 * pk, (60, 60, 70), (10, 10, 12), 3)
    a, b, c_, e = RIG['amp']
    lv = int(1 + 9 * live * abs(math.sin(t * 9)))
    for i in range(10):
        d.rect(a + 12 + i * 12, b + 12, a + 20 + i * 12, b + 26, ((80, 220, 110) if i < 6 else (250, 200, 50) if i < 8 else (240, 50, 50)) if i < lv else (50, 50, 56))
    rx = CX - 280 + 560
    if t > T_TUNE:
        d.rect(rx - 70, 586, rx - 6, 612, None, r=6, ol=(255, 80, 80, int(150 + 100 * math.sin(t * 8))), w=4)
    for txt, tt, (a, b, c_, e) in (('SPEAKERS', T_SPKS, (110, 700, 340, 852)), ('TUNING CHAMBER', T_TUNE, RIG['chamber']),
                                     ('AMPLIFIER', T_AMP, RIG['amp'])):
        if t >= tt - .05:
            k_ = popin(t, tt - .05, .3)
            w_ = font(30 * K, FONT_X).getlength(txt) / K + 30
            cx_ = (a + c_) / 2; y = b - 40 - {'SPEAKERS': 30, 'TUNING CHAMBER': 0, 'AMPLIFIER': 84}[txt]
            d.rect(cx_ - w_ / 2 * k_, y - 24 * k_, cx_ + w_ / 2 * k_, y + 24 * k_, (255, 255, 255), r=10, ol=OL, w=3)
            if k_ > .6: d.text(cx_, y, txt, 30, OL, path=FONT_X)
            d.line([(cx_, y + 24 * k_), (cx_, b - 4)], (255, 255, 255), 3)
    chicken_dj(d, 1000, 560, t, .9)

# ---- 3 night car meet: skyline, stars, light poles, string lights, food truck, crowd with phones, the grandma burnout
@lru_cache(None)
def bg_meet():
    img = stack((620, (8, 10, 32), (54, 36, 86)), (H - 620, (78, 78, 92), (58, 58, 70)))
    d = D(img); r = rng_for(5)
    for _ in range(90):
        x, y = r.uniform(0, W), r.uniform(0, 420); d.ell(x, y, r.uniform(1, 2.6), r.uniform(1, 2.6), (255, 255, 240, int(r.uniform(90, 230))))
    d.ell(930, 150, 48, 48, (250, 246, 220)); d.ell(912, 140, 9, 9, (226, 222, 196)); d.ell(944, 168, 6, 6, (226, 222, 196))
    x = -20
    while x < W:                                                         # skyline with lit windows
        bw, bh = r.uniform(60, 130), r.uniform(120, 300)
        d.rect(x, 620 - bh, x + bw, 620, (24, 24, 50))
        for wy in range(int(640 - bh), 600, 22):
            for wx in range(int(x + 10), int(x + bw - 10), 18):
                if r.uniform() < .35: d.rect(wx, wy, wx + 8, wy + 10, (255, 214, 120, 200))
        x += bw + 6
    for i in range(-6, 12):                                              # parking bay lines
        d.line([(i * 120 + 60, 640), (i * 120 - 180, WALL_Y + 60)], (230, 230, 236, 90), 4)
    for px in (40, 1040):                                                # light poles + cones
        d.rect(px - 7, 210, px + 7, 940, (70, 72, 80))
        d.rect(px - 40, 200, px + 40, 216, (90, 92, 100), r=4)
        img = cone(img, px, 214, 30, 200, 760, (255, 220, 160), 50, 30); d = D(img)
        d.ell(px, 218, 30, 6, (255, 240, 200))
    tx0, ty0 = 740, 520                                                  # food truck
    d.rect(tx0, ty0, 1100, 790, (80, 180, 170), r=14, ol=OL, w=4)
    d.rect(tx0 + 50, ty0 + 50, tx0 + 240, ty0 + 130, (255, 220, 130), r=6, ol=OL, w=3)
    d.ell(tx0 + 150, ty0 + 108, 26, 34, (60, 40, 30))
    for i in range(8): d.poly([(tx0 + 40 + i * 28, ty0 + 40), (tx0 + 68 + i * 28, ty0 + 40), (tx0 + 64 + i * 28, ty0 + 60), (tx0 + 44 + i * 28, ty0 + 60)], (226, 40, 48) if i % 2 else (255, 255, 255))
    d.rect(tx0 + 30, ty0 - 50, tx0 + 260, ty0 - 4, (30, 30, 34), r=8)
    d.text(tx0 + 145, ty0 - 27, 'BURGERS', 32, (255, 214, 64), path=FONT_B)
    for wx in (tx0 + 60, tx0 + 280): d.ell(wx, 790, 30, 30, (24, 24, 28)); d.ell(wx, 790, 12, 12, (150, 150, 160))
    paste_rot(img, road_car((240, 140, 30), 300), 110, 640, flip=False)
    paste_rot(img, road_car((140, 70, 200), 250), 560, 650, flip=True)
    d = D(img)
    return img

CROWD = [(x, 760 + (i % 3) * 8, ((40, 36, 60), (30, 40, 56), (54, 40, 50))[i % 3]) for i, x in enumerate(range(250, 720, 46))]
def meet_life(img, t):
    d = D(img)
    for i, (x, y, col) in enumerate(CROWD):                               # crowd behind the hero car, phones up
        bob = math.sin(t * 2.5 + i) * 3
        d.ell(x, y - 40, 26, 44, col); d.ell(x, y - 98 + bob, 18, 20, col)
        if i % 3 == 0 and (t * 1.3 + i) % 3 < 2.2:
            d.line([(x + 10, y - 60), (x + 26, y - 110 + bob)], col, 9)
            d.rect(x + 18, y - 136 + bob, x + 38, y - 104 + bob, (200, 230, 255), r=3)
    pts = catenary(40, 250, 1040, 250, 90)                               # string lights
    d.line(pts, (30, 30, 36), 3)
    for i, (x, y) in enumerate(pts[1:-1]):
        on = (int(t * 4) + i) % 5 != 0
        col = ((255, 90, 90), (255, 214, 90), (110, 220, 255), (150, 255, 150))[i % 4]
        d.ell(x, y + 10, 8, 10, col if on else (80, 80, 90))
        if on: d.ell(x, y + 10, 16, 18, col + (60,))
    grandma_burnout(d, 900, 900, t, .62)

def meet_car(img, t):
    rev = T_HUND - .1 <= t < LE[5] + .2
    shake = math.sin(t * 60) * 3 if rev else 0
    paste_charger(img, CX - 290, 900 + shake, 580)
    d = D(img)
    d.poly([(CX - 290, 760), (CX - 600, 700), (CX - 600, 860)], (255, 250, 220, 40))   # headlight beam
    rings(d, CX - 290 + 580 + 6, 816, t, T_HUND - .1, LE[5] + .3, (255, 90, 90), 4, 2.2, 260)

# ---- 4 recording studio: foam walls, vocal booth (with the cow), DAW screen, tape machine, mixing desk
@lru_cache(None)
def bg_studio():
    img = stack((WALL_Y, (48, 46, 60), (32, 30, 42)), (H - WALL_Y, (96, 64, 46), (58, 38, 28)))
    d = D(img)
    for x0_, x1_ in ((0, 130), (660, 1080)):                              # acoustic foam
        for i, y in enumerate(range(110, 760, 60)):
            for j, x in enumerate(range(x0_, x1_, 60)):
                d.rect(x + 2, y + 2, x + 58, y + 58, (64, 62, 80))
                for k_ in range(3):
                    if (i + j) % 2: d.line([(x + 10 + k_ * 18, y + 6), (x + 10 + k_ * 18, y + 54)], (82, 80, 100), 5)
                    else: d.line([(x + 6, y + 10 + k_ * 18), (x + 54, y + 10 + k_ * 18)], (82, 80, 100), 5)
    booth = Image.fromarray(grad(460 * K, 500 * K, (126, 100, 148), (86, 68, 108)).astype(np.uint8))
    bd = D(booth, ox=140, oy=180)
    for y in range(190, 640, 50):
        for x in range(150, 640, 50): bd.rect(x, y, x + 46, y + 46, (110, 88, 132))
    bd.line([(470, 640), (470, 470)], (40, 40, 46), 6); bd.line([(470, 470), (420, 420)], (40, 40, 46), 5)
    bd.rect(404, 386, 432, 436, (60, 60, 66), r=12); bd.ell(400, 440, 30, 30, None, (200, 200, 210, 160), 3)
    img.paste(booth, (140 * K, 180 * K))
    d = D(img)
    d.rect(132, 172, 648, 648, None, r=8, ol=(20, 20, 26), w=16)
    d.poly([(170, 210), (230, 210), (190, 600), (150, 600)], (255, 255, 255, 18))
    d.rect(680, 250, 1050, 470, (14, 14, 18), r=8, ol=(40, 40, 46), w=6)    # DAW screen frame
    d.rect(856, 470, 874, 520, (40, 40, 46))
    d.rect(680, 540, 880, 720, (150, 150, 158), r=8, ol=OL, w=3)             # tape machine
    for rx_ in (730, 830):
        d.ell(rx_, 600, 40, 40, (40, 40, 46), (20, 20, 24), 3); d.ell(rx_, 600, 10, 10, (190, 190, 200))
    d.rect(700, 660, 860, 700, (60, 60, 66), r=4)
    d.rect(906, 520, 1030, 720, (30, 30, 36), r=10, ol=OL, w=3)              # studio monitor
    d.ell(968, 570, 30, 30, (60, 60, 70)); d.ell(968, 660, 42, 42, (60, 60, 70)); d.ell(968, 660, 14, 14, (20, 20, 24))
    d.poly([(0, 780), (W, 780), (W, 900), (0, 900)], (36, 36, 46))           # mixing desk
    d.rect(0, 900, W, 980, (22, 22, 28))
    for i, x in enumerate(range(20, 1070, 36)):
        for j, c in enumerate(((240, 80, 80), (250, 200, 60), (90, 180, 250))):
            d.ell(x, 796 + j * 18, 6, 6, c)
        d.line([(x, 856), (x, 892)], (14, 14, 18), 4)
    d.rect(0, 980, W, 990, (16, 16, 20))
    return img

def studio_life(img, t):
    d = D(img)
    on = (int(t * 2) % 2 == 0)
    d.rect(690, 150, 860, 206, (220, 30, 40) if on else (110, 20, 26), r=8, ol=(30, 30, 34), w=3)
    d.text(775, 178, 'ON AIR', 30, (255, 255, 255) if on else (190, 150, 150), path=FONT_B)
    if on: d.ell(775, 178, 110, 40, (255, 60, 60, 40))
    for k_ in range(3):                                                   # DAW: waveform generated live, scrolling
        y = 300 + k_ * 56
        d.rect(690, y - 22, 1040, y + 22, (26, 26, 34))
        pts = [(x, y + 18 * math.sin(x * .09 + t * 9 + k_) * abs(math.sin(x * .013 + t * 2))) for x in range(694, 1036, 4)]
        d.line(pts, ((230, 60, 60), (250, 200, 60), (90, 200, 250))[k_], 3)
    d.line([(1000, 270), (1000, 460)], (255, 255, 255), 2)
    cow_singer(d, 290, 360, t, .9)
    for i, x in enumerate(range(20, 1070, 36)):                            # faders move
        fy = 874 + 12 * math.sin(t * 1.7 + i * .6)
        d.rect(x - 10, fy - 6, x + 10, fy + 6, (200, 204, 212), r=2)

# ---- 5 suburban street at dawn: sky, sun, power line with birds, three houses, fences, the horse upstairs
HOUSES = [dict(x0=-40, x1=300, top=460, peak=330, body=(214, 178, 146), roof=(96, 60, 60), win=((40, 520, 120, 590), (180, 520, 260, 590), (40, 640, 120, 710))),
          dict(x0=320, x1=650, top=480, peak=360, body=(152, 182, 206), roof=(62, 72, 96), win=((360, 530, 440, 600), (520, 530, 600, 600))),
          dict(x0=670, x1=1100, top=450, peak=316, body=(232, 214, 170), roof=(126, 72, 52), win=((820, 490, 930, 580), (720, 640, 800, 710), (960, 490, 1060, 580)))]
@lru_cache(None)
def bg_street():
    img = stack((300, (70, 90, 160), (232, 150, 150)), (420, (232, 150, 150), (255, 210, 150)), (H - 720, (66, 70, 84), (46, 48, 58)))
    glow(img, 560, 730, 160, (255, 220, 160), 150)
    d = D(img)
    d.ell(560, 730, 90, 90, (255, 236, 170))
    for cx_, cy_, rw in ((180, 170, 120), (760, 120, 90), (980, 260, 70)):
        d.ell(cx_, cy_, rw, rw * .3, (255, 200, 200, 150)); d.ell(cx_ + rw * .4, cy_ - 12, rw * .6, rw * .28, (255, 214, 214, 160))
    for h in HOUSES:
        d.rect(h['x0'], h['top'], h['x1'], 760, h['body'], ol=OL, w=4)
        d.poly([(h['x0'] - 24, h['top']), ((h['x0'] + h['x1']) / 2, h['peak']), (h['x1'] + 24, h['top'])], h['roof'], OL, 4)
        d.rect(h['x1'] - 90, h['peak'] + 30, h['x1'] - 60, h['top'] - 10, (110, 90, 90), ol=OL, w=3)   # chimney
        for (a, b, c_, e) in h['win']:
            d.rect(a, b, c_, e, (44, 54, 84), ol=OL, w=4); d.line([((a + c_) / 2, b), ((a + c_) / 2, e)], OL, 3)
    d.rect(200, 640, 270, 760, (120, 70, 50), ol=OL, w=3)                 # doors, garage
    d.rect(380, 620, 600, 760, (220, 224, 230), ol=OL, w=4)
    for y in range(640, 760, 24): d.line([(384, y), (596, y)], (180, 184, 190), 3)
    d.rect(960, 640, 1030, 760, (60, 90, 70), ol=OL, w=3)
    for x in (305, 660):                                                  # bushes between houses
        for dx in (-30, 0, 30): d.ell(x + dx, 730, 40, 34, (60, 120, 70), OL, 2)
    img2 = stack((80, (110, 170, 100), (80, 140, 84)),)
    img.paste(img2, (0, 760 * K))
    d = D(img)
    for x in range(0, W, 26):                                             # picket fence
        d.poly([(x, 790), (x + 18, 790), (x + 18, 744), (x + 9, 732), (x, 744)], (246, 244, 236), OL, 2)
    d.rect(0, 760, W, 768, (246, 244, 236)); d.rect(0, 778, W, 784, (246, 244, 236))
    d.rect(0, 840, W, 868, (196, 196, 200)); d.rect(0, 868, W, 876, (140, 140, 146))
    for x in range(-40, W, 160): d.rect(x, 1010, x + 90, 1020, (230, 226, 200))
    d.rect(592, 770, 604, 840, (90, 70, 60)); d.rect(570, 742, 626, 776, (40, 70, 140), r=10, ol=OL, w=3)   # mailbox
    d.line([(46, 860), (46, 300)], (60, 60, 66), 10)                       # street lamp (still on)
    d.line([(46, 300), (110, 300)], (60, 60, 66), 8)
    d.chord(110, 318, 28, 18, 180, 360, (60, 60, 66))
    pts = catenary(-20, 170, 1100, 190, 60)                               # power line + pole
    d.line(pts, (40, 36, 50), 3)
    d.rect(1004, 150, 1018, 760, (110, 80, 60)); d.rect(970, 166, 1052, 176, (110, 80, 60))
    return img

def street_life(img, t):
    d = D(img)
    awake = T_DRAG + .15 <= t < T_STEALTH + .25
    glow_on = (255, 214, 120)
    d.ell(110, 324, 18, 8, (255, 230, 170)); d.ell(110, 330, 40, 22, (255, 230, 170, 60))
    for hi, h in enumerate(HOUSES):
        for wi, (a, b, c_, e) in enumerate(h['win']):
            if hi == 2 and wi == 0:                                       # the horse's window (always awake)
                d.rect(a + 4, b + 4, c_ - 4, e - 4, (255, 226, 160))
                horse_window(d, (a + c_) / 2 - 6, (b + e) / 2 + 6, t, .62)
                continue
            if awake:
                d.rect(a + 4, b + 4, c_ - 4, e - 4, glow_on)
                if (hi + wi) % 2 == 0:                                    # angry neighbour pops up
                    k_ = popin(t, T_DRAG + .2 + .1 * (hi + wi), .25)
                    cx_, cy_ = (a + c_) / 2, e - 6 - 26 * k_
                    d.ell(cx_, cy_, 20, 22, (230, 190, 160), OL, 3)
                    d.line([(cx_ - 12, cy_ - 8), (cx_ - 2, cy_ - 4)], OL, 3); d.line([(cx_ + 12, cy_ - 8), (cx_ + 2, cy_ - 4)], OL, 3)
            elif (hi + wi) % 2 == 0:
                zzz(d, c_ - 10, b + 10, t + hi + wi, 1.0, .8)
    pts = catenary(-20, 170, 1100, 190, 60)
    for i, bx in enumerate((300, 360, 420, 640, 700)):                    # birds sit, then scatter on the rev
        j = int(bx / 1120 * 24); by = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * ((bx / 1120 * 24) % 1)
        if t < T_DRAG + .1:
            d.ell(bx, by - 10, 12, 10, (40, 36, 50)); d.ell(bx - 9, by - 18, 7, 7, (40, 36, 50))
        else:
            k_ = t - T_DRAG - .1; fx = bx + (60 + i * 30) * k_ * (1 if i % 2 else -1); fy = by - 160 * k_ - 10
            fl = math.sin(t * 30 + i) * 10
            d.line([(fx - 14, fy - fl), (fx, fy), (fx + 14, fy - fl)], (40, 36, 50), 4)
    if awake:                                                             # the dog yaps in the yard
        hop = abs(math.sin(t * 14)) * 14
        d.ell(160, 812 - hop, 30, 18, (240, 230, 220), OL, 3); d.ell(186, 796 - hop, 16, 15, (240, 230, 220), OL, 3)
        d.text(222, 770, 'WOOF', 22, (255, 255, 255), path=FONT_X)
    else:
        d.ell(160, 812, 30, 14, (240, 230, 220), OL, 3); d.ell(186, 806, 15, 12, (240, 230, 220), OL, 3)
        zzz(d, 200, 790, t, .9, .6)

def street_car(img, t):
    rev = T_DRAG - .05 <= t < T_STEALTH
    paste_charger(img, CX - 290, 900 + (math.sin(t * 60) * 3 if rev else 0), 580)
    d = D(img)
    rings(d, CX - 290 + 586, 816, t, T_DRAG - .05, T_STEALTH, (255, 90, 90), 4, 2.2, 260)
    if t >= T_STEALTH:                                                    # stealth: a calm, quiet glow
        d.ell(CX - 290 + 586, 816, 30, 24, (110, 230, 160, int(120 * popin(t, T_STEALTH, .3) / 1.1)))

# ---- 6 drag strip at night: floodlights, grandstand with crowd (and giraffe), scoreboard, the tree, the race
@lru_cache(None)
def bg_strip():
    img = stack((560, (6, 8, 24), (36, 26, 60)), (H - 560, (74, 74, 86), (56, 56, 66)))
    d = D(img); r = rng_for(8)
    for _ in range(60):
        d.ell(r.uniform(0, W), r.uniform(0, 300), 1.6, 1.6, (255, 255, 240, int(r.uniform(80, 220))))
    d.poly([(130, 640), (950, 640), (900, 430), (180, 430)], (60, 62, 76))       # grandstand
    for i, y in enumerate(range(440, 640, 26)):
        d.line([(180 - (y - 430) * .24, y), (900 + (y - 430) * .24, y)], (80, 82, 96), 3)
        for x in np.arange(190 - (y - 430) * .24, 890 + (y - 430) * .24, 15):
            c = ((240, 80, 80), (250, 210, 80), (90, 180, 250), (240, 240, 240), (120, 220, 140))[int(r.uniform(0, 5))]
            d.ell(x + r.uniform(-3, 3), y - 6, 6, 7, c)
    d.rect(150, 600, 930, 640, (220, 40, 48))
    d.text(540, 620, 'FRIDAY NIGHT DRAGS', 28, (255, 255, 255), path=FONT_B)
    for px in (70, 1010):                                                 # floodlight towers
        d.line([(px - 30, 900), (px, 130), (px + 30, 900)], (90, 92, 104), 6)
        for y in range(200, 880, 70): d.line([(px - 30 + (y - 130) / 770 * 0, y), (px + 30, y + 35)], (90, 92, 104), 3)
        d.rect(px - 60, 100, px + 60, 160, (60, 62, 70), r=6)
        for i in range(3):
            for j in range(2): d.ell(px - 38 + i * 38, 116 + j * 28, 14, 10, (255, 252, 230))
        glow(img, px, 130, 110, (255, 250, 220), 160); d = D(img)
        img = cone(img, px, 140, 50, 360, 800, (255, 250, 230), 34, 30); d = D(img)
    d.rect(380, 190, 640, 330, (16, 16, 22), r=8, ol=(70, 72, 84), w=5)          # scoreboard
    d.rect(500, 330, 520, 430, (60, 62, 70))
    d.text(450, 220, 'LEFT', 26, (250, 200, 60), path=FONT_X); d.text(570, 220, 'RIGHT', 26, (250, 200, 60), path=FONT_X)
    d.line([(510, 200), (510, 320)], (60, 60, 70), 3)
    d.rect(0, 640, W, 700, (204, 204, 210)); d.rect(0, 690, W, 700, (150, 150, 158))   # concrete wall
    for x in range(0, W, 120): d.rect(x, 650, x + 60, 680, (220, 40, 48) if (x // 120) % 2 else (40, 40, 48))
    d.line([(0, 820), (W, 820)], (240, 240, 240), 4); d.line([(0, 920), (W, 920)], (240, 240, 240), 4)
    d.rect(150, 700, 160, 940, (255, 255, 255))                                    # start line
    d.rect(96, 470, 108, 760, (70, 72, 80))                                        # the tree
    d.rect(76, 470, 128, 700, (30, 30, 36), r=8)
    return img

def strip_lights(d, t):
    seq = [T_RACE - .9, T_RACE - .6, T_RACE - .3]
    for i, ts in enumerate(seq):
        on = ts <= t < T_RACE + .2
        for side in (-1, 1):
            d.ell(102 + side * 13, 500 + i * 46, 11, 11, (255, 180, 40) if on else (70, 50, 20))
    g = t >= T_RACE
    for side in (-1, 1): d.ell(102 + side * 13, 640, 11, 11, (80, 255, 120) if g else (20, 60, 30))
    if g: d.ell(102, 640, 40, 20, (80, 255, 120, 60))
    if t >= T_RACE + 1.75:                                                # EV lane wins (near lane = right lane)
        k_ = popin(t, T_RACE + 1.75, .3)
        d.rect(536, 250 - 30 * k_, 604, 250 + 30 * k_, (80, 220, 110), r=6)
        if k_ > .6: d.text(570, 250, 'WIN', 28, (10, 30, 14), path=FONT_B)

def race_x(t, acc, x0):
    if t < T_RACE: return x0 + (math.sin(t * 3) * 2)
    tt = t - T_RACE
    return x0 + .5 * acc * tt * tt
def strip_cars(img, t):
    d = D(img)
    gx = race_x(t, 520, 40)                                               # far lane: gas Scat Pack
    if gx < 1200:
        sh = math.sin(t * 50) * 2
        paste_charger(img, gx, 812 + sh, 420, GREY_CHG, gas=True)
        d = D(img)
        rx = gx + 420
        for i in range(5):                                                # tailpipe smoke + flame on launch
            ph = (t * 1.5 + i / 5) % 1
            d.ell(rx + 10 - 60 * ph - (gx - 40) * .2, 760 - 40 * ph, 14 + 30 * ph, 10 + 20 * ph, (200, 200, 210, int(120 * (1 - ph))))
        if T_RACE <= t < T_RACE + 1.2 and int(t * 20) % 2:
            d.poly([(rx + 2, 770), (rx + 40, 762), (rx + 2, 756)], (255, 160, 40))
    ex = race_x(t, 700, 20)                                               # near lane: the Daytona (EV)
    if ex < 1300:
        paste_charger(img, ex, 912, 520)
        d = D(img)
        if t >= T_RACE - 1.2:
            rings(d, ex + 526, 842, t, T_RACE - 1.2, T_RACE + 2.5, (255, 90, 90), 3, 2.4, 160)
    if T_RACE <= t < T_RACE + 2.4:                                        # speed lines
        for i in range(6):
            y = 760 + i * 30; x = (t * 2400 + i * 300) % 1400 - 200
            d.line([(x, y), (x + 140, y)], (255, 255, 255, 90), 3)

def strip_life(img, t):
    d = D(img)
    strip_lights(d, t)
    giraffe(d, 840, 640, t, 1.0)
    r = (int(t * 7) * 7919) % 97                                          # phone flashes in the stands
    for i in range(3):
        x = 200 + ((r + i * 37) * 13) % 680; y = 450 + ((r + i * 17) * 7) % 160
        d.ell(x, y, 10, 10, (255, 255, 255, 230))


# ---- performance schedules: (time, left pose, right pose, extras)
def buyer_sched():
    A, Wd = dict(brows='angry', eyes='wide'), dict(brows='up', eyes='wide', sweat=1)
    return [(0.0, 'point', 'up', A),                                     # frame 1: already mid-shout
            (T_FAKE - .05, 'up', 'up', A),
            (T_HELL - .05, 'head', 'head', Wd),
            (LE[0] + .15, 'rest', 'point', dict(brows='angry')),
            (T_SPK, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (LE[1] + .2, 'rest', 'rest', dict(brows='worried')),
            # garage
            (T_S2, 'rest', 'rest', dict(brows='up')),
            (LS[2] - .05, 'up', 'point', Wd),
            (LE[2] + .15, 'rest', 'rest', dict(brows='up')),
            (T_TUNE, 'chin', 'rest', dict(brows='worried')),
            (T_GAS, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            # night meet
            (T_S3, 'rest', 'rest', dict(brows='up')),
            (LS[4] - .05, 'open', 'open', dict(brows='up', smile=1)),
            (T_HUND - .05, 'head', 'head', Wd),
            (LE[5] + .1, 'rest', 'rest', dict(brows='up', eyes='wide')),
            (LS[6] - .05, 'chin', 'rest', dict(brows='worried')),
            (T_LOGO, 'rest', 'point', dict(brows='up', smile=1)),
            # studio
            (T_S4, 'rest', 'rest', dict(brows='flat')),
            (LS[8] - .05, 'point', 'rest', dict(brows='angry')),
            (LE[8] + .15, 'cross', 'cross', dict(brows='angry')),
            (T_ITSELF, 'cross', 'cross', dict(brows='up')),
            (T_GEARS, 'shrug', 'shrug', dict(brows='worried', eyes='wide')),
            # dawn street
            (T_S5, 'rest', 'rest', dict(brows='up', smile=1)),
            (LS[10] - .05, 'up', 'up', dict(brows='up', eyes='wide', smile=1)),
            (LE[10] + .15, 'rest', 'rest', dict(smile=1)),
            (T_DRAG, 'up', 'up', dict(brows='up', eyes='wide', smile=1)),
            (T_STEALTH, 'head', 'rest', dict(brows='worried', sweat=1)),
            # drag strip
            (T_S6, 'hip', 'hip', dict(brows='flat', smile=1)),
            (LS[12] - .05, 'hip', 'point', dict(brows='flat', smile=1)),
            (LE[12] + .15, 'hip', 'hip', dict(smile=1)),
            (T_RACE, 'rest', 'rest', dict(brows='up', eyes='wide')),
            (T_39, 'head', 'head', Wd),
            (LS[14] - .05, 'up', 'up', Wd),
            (LE[14] + .15, 'rest', 'rest', dict(brows='up', eyes='wide')),
            (T_FINAL + .05, 'rest', 'open', dict(brows='up', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {1: 'open', 3: 'present', 5: 'open', 7: 'offer', 9: 'open', 11: 'present', 13: 'open'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
    s += [(T_FINAL, 'clasp', 'clasp', dict(look=0))]
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
SETS = {0: (bg_showroom, showroom_life, showroom_car), 1: (bg_garage, garage_life, None), 2: (bg_meet, meet_life, meet_car),
        3: (bg_studio, studio_life, None), 4: (bg_street, street_life, street_car), 5: (bg_strip, strip_life, strip_cars)}
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    bg, life, car = SETS[sc]
    img = bg().copy()
    life(img, t)
    if car: car(img, t)
    d = D(img)
    f = int(round(t * FPS))
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.25), 150, 11   # already in shot, mid-complaint
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

PUNCH = {0: ((T_FAKE, .03), (T_HELL, .05), (T_NOT, .03)), 1: ((LS[2], .05), (T_GAS, .04)),
         2: ((T_HUND, .06), (T_SAME, .03), (T_LOGO, .03)), 3: ((T_REC, .04), (T_GEARS, .04)),
         4: ((T_DRAG, .06), (T_STEALTH, .03)), 5: ((T_RACE, .05), (T_39, .04), (T_WINS, .05), (T_FINAL, .05))}
def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0:
        z = 1.06 - 0.03 * oc(prog(t, 0, 1.6)) + 0.01 * math.sin(t * .5)        # frame 1 already pushing
    else:
        z = 1.05 + 0.02 * io(prog(t, t0, 7))
        sx = 46 * (1 - oc(prog(t, t0, 1.4)))                                   # settle after the whip
    if sc == 5:
        sx += 30 * io(prog(t, T_RACE, 2.0))                                    # follow the race a little
        pk = io(prog(t, T_FINAL - .05, .5))                                    # buyer asks the viewer: push in
        z += 0.14 * pk; sx -= 160 * pk
    rev = (sc == 0 and t < LE[0]) or (sc == 2 and T_HUND <= t < LE[5]) or (sc == 4 and T_DRAG <= t < T_STEALTH) \
        or (sc == 5 and T_RACE <= t < T_RACE + .5)
    if rev:                                                                   # the "exhaust" rattles the camera
        sx += 3 * math.sin(t * 71); sy += 3 * math.sin(t * 53 + 1)
    for tp, amt in PUNCH[sc]:
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
CARD_PHOTO_NONE = (("2026 Charger Daytona", 60, INK2), ("Scat Pack: electric", 60, DRED))
CARD_FRATZ = (("Fratzonic", 70, DRED), ("named after Dodge's", 50, INK2), ("Fratzog logo", 56, INK2))
CARD_REC = (("Dodge says it generates", 50, INK2), ("the sound itself:", 50, INK2), ("not a recording", 60, DRED))
CARD_EV = (("Daytona Scat Pack (EV)", 50, DRED), ("670 hp, 627 lb-ft", 50, INK2), ("0-60: 3.3 s (targeted)", 50, INK2))
CARD_GAS = (("Charger Scat Pack (gas)", 50, INK2), ("550 hp, 531 lb-ft", 50, INK2), ("0-60: 3.9 s", 50, INK2))
CARD_REDEYE = (("Dodge says it's also", 52, INK2), ("quicker than the", 52, INK2), ("Charger Hellcat Redeye", 52, DRED))
CHIPS5 = [('DRAG / DONUT / TRACK', 'LOUDER', RED, 'T_DRAG'), ('STEALTH', 'QUIET', GREEN, 'T_STEALTH')]
FINAL = [("Fake exhaust or", 74, TAG), ("real engine?", 80, TAG), ("Comment below.", 70, (255, 255, 255)),
         ("Next: another car that's", 58, (210, 214, 224)), ("secretly doing", 58, (210, 214, 224)),
         ("something strange.", 58, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 400, 100
PHOTO_LABEL = '2026 CHARGER DAYTONA SCAT PACK'
ONSCREEN = (['D O D G E', 'FRATZONIC', 'SPEAKERS', 'TUNING CHAMBER', 'AMPLIFIER', 'BURGERS', 'ON AIR', 'LEFT', 'RIGHT', 'WIN',
             'WOOF', 'FRIDAY NIGHT DRAGS', 'NOT AN EXHAUST', 'NO EXHAUST GAS', '126 dB', 'Dodge says', 'SAME AS THE HELLCAT V8',
             'RPM', 'V8: gear shifts', 'Fratzonic: no shifts', 'reviewers say', PHOTO_LABEL, 'FAKE EXHAUST?!']
            + [r[0] for c in (CARD_PHOTO_NONE, CARD_FRATZ, CARD_REC, CARD_EV, CARD_GAS, CARD_REDEYE) for r in c]
            + [x for r in CHIPS5 for x in r[:2]] + [f[0] for f in FINAL])

def chip_rows(d, t, rows, y0, a):
    al = int(255 * a)
    for i, (lab, chip, col, tn) in enumerate(rows):
        t_lab = globals()[tn]
        if t < t_lab - .05: continue
        ra = min(a, prog(t, t_lab - .05, .2))
        k_ = popin(t, t_lab - .05, .3)
        w_ = font(32 * K).getlength(chip) / K
        y = y0 + i * 76
        d.text(110, y, lab, 34, (220, 224, 234, int(255 * ra)), anchor='lm', path=FONT_X)
        d.rect(810 - (w_ + 36) * k_, y - 28, 810, y + 28, col + (al,), r=12)
        if k_ > .6: d.text(810 - (w_ + 36) / 2, y + 1, chip, 32, (255, 255, 255, al))

def card(img, t, rows, t0, t1, y=520, rot=-1.5):
    a = window(t, t0, t1, .1, .3)
    if a <= 0: return False
    put(img, info_card(rows), CX, y, popin(t, t0, .35), a, rot=rot)
    return True

def stamp(img, t, txt, col, t0, t1, y, rot=-6, size=84):
    a = window(t, t0, t1, .05, .25)
    if a <= 0: return False
    k_ = 1 + .6 * (1 - oc(prog(t, t0, .22)))
    put(img, stamp_img(txt, col, size), CX, y, k_, a, rot=rot)
    return True

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0 and t >= 3.0:                                  # nothing in the first 3 s but captions
        pa = window(t, LS[1] - .15, T_S2 + .05, .1, .3)
        if pa > 0:                                            # the one real car
            used = True
            if HAS_PHOTO:
                put(img, photo_card('charger.jpg', PHOTO_LABEL, (176, 20, 30), (255, 255, 255), 600), CX, 430,
                    popin(t, LS[1] - .15, .35), pa, rot=-2)
            else:
                put(img, info_card(CARD_PHOTO_NONE), CX, 430, popin(t, LS[1] - .15, .35), pa, rot=-2)
        used |= stamp(img, t, 'NOT AN EXHAUST', RED, T_NOT - .03, T_S2 + .05, 720, size=60)
    elif sc == 1:
        used = stamp(img, t, 'NO EXHAUST GAS', RED, T_GAS - .03, T_S3 + .05, 460, rot=-5, size=64)
    elif sc == 2:
        ma = window(t, T_HUND - .1, T_FRATZ - .05, .15, .25)
        if ma > 0:                                            # decibel meter fills to 126 dB
            used = True
            d = D(img)
            panel(d, 90, 300, 830, 600, ma)
            fill = io(prog(t, T_HUND, 1.0))
            d.rect(130, 470, 790, 520, (50, 52, 60, int(255 * ma)), r=14)
            for i in range(int(22 * fill)):
                c = (80, 220, 110) if i < 12 else (250, 200, 50) if i < 18 else (240, 50, 50)
                d.rect(136 + i * 29.6, 476, 160 + i * 29.6, 514, c + (int(255 * ma),), r=4)
            k_ = popin(t, T_HUND + 1.0, .3)
            if fill > .95 and k_ > .05:
                d.text(CX, 390, '126 dB', 104 * k_, TAG + (int(255 * ma),), stroke=6, sc=(10, 10, 16, int(255 * ma)))
            d.text(CX, 560, 'Dodge says', 30, (220, 224, 234, int(255 * ma)), path=FONT_X)
            if t >= T_SAME - .05:
                k_ = popin(t, T_SAME - .05, .3)
                w_ = font(34 * K).getlength('SAME AS THE HELLCAT V8') / K + 50
                d.rect(CX - w_ / 2 * k_, 640 - 34 * k_, CX + w_ / 2 * k_, 640 + 34 * k_, RED + (int(255 * ma),), r=14)
                if k_ > .6: d.text(CX, 641, 'SAME AS THE HELLCAT V8', 34, (255, 255, 255, int(255 * ma)))
        fa = window(t, T_FRATZ - .05, T_S4 + .05, .1, .3)
        if fa > 0:
            used = True
            put(img, info_card(CARD_FRATZ), CX + 40, 520, popin(t, T_FRATZ - .05, .35), fa, rot=-1.5)
            if t >= T_LOGO - .05:
                k_ = popin(t, T_LOGO - .05, .35)
                d = D(img)
                d.ell(170, 430, 74 * k_, 74 * k_, (255, 255, 255, int(255 * fa)), OL + (int(255 * fa),), 5)
                fratzog(d, 170, 434, .9 * k_, (200, 24, 32, int(255 * fa)))
    elif sc == 3:
        used = card(img, t, CARD_REC, LS[9] + .05, T_REVIEW - .05, 470)
        ga = window(t, T_REVIEW - .05, T_S5 + .05, .15, .25)
        if ga > 0:                                            # RPM over time: a V8 shifts gears, the speaker never does
            used = True
            d = D(img); al = int(255 * ga)
            panel(d, 80, 280, 840, 700, ga)
            d.text(110, 320, 'RPM', 30, (220, 224, 234, al), anchor='lm', path=FONT_X)
            d.line([(120, 640), (800, 640)], (120, 124, 136, al), 3); d.line([(120, 640), (120, 340)], (120, 124, 136, al), 3)
            rv = prog(t, T_REVIEW, 1.4)
            saw = []
            for i in range(int(68 * rv) + 1):
                u = i / 68; g = min(3, int(u * 4)); uu = u * 4 - g
                saw.append((120 + 680 * u, 600 - 220 * (.25 + .75 * uu) + g * 10))
            if len(saw) > 1: d.line(saw, (170, 176, 190, al), 6)
            smooth = [(120 + 680 * u, 600 - 240 * (u ** .6)) for u in np.linspace(0, rv, 40)]
            if len(smooth) > 1: d.line(smooth, RED + (al,), 8)
            d.text(800, 380, 'Fratzonic: no shifts', 30, RED + (al,), anchor='rm', path=FONT_X)
            d.text(800, 676, 'V8: gear shifts', 30, (200, 204, 214, al), anchor='rm', path=FONT_X)
            d.text(110, 676, 'reviewers say', 26, (220, 224, 234, al), anchor='lm', path=FONT_X)
    elif sc == 4:
        ca = window(t, T_DRAG - .1, T_S6 + .05, .2, .25)
        if ca > 0:
            used = True
            d = D(img)
            panel(d, 80, 330, 840, 540, ca)
            chip_rows(d, t, CHIPS5, 395, ca)
            d.text(CX, 515, 'Dodge says', 26, (220, 224, 234, int(255 * ca)), path=FONT_X)
    else:
        used = card(img, t, CARD_EV, T_33 - .1, T_WINS - .05, 360, -1.5)
        used |= card(img, t, CARD_GAS, T_39 - .1, T_WINS - .05, 620, 1.2)
        used |= card(img, t, CARD_REDEYE, T_WINS - .05, BEAT[1] - .05, 500, -1.5)
    if t >= T_CARD:                                           # final caption
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(40, FINAL_Y0 - 90, 878, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
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
    if T_RACE <= t < T_RACE + .25:                          # launch flash
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.3 * (1 - prog(t, T_RACE, .25)))
    ov = overlays(t)
    if ov is not None:
        ov = ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA')
        img.alpha_composite(ov)
    if BEAT[0] + .1 <= t < T_FINAL:                         # the beat: everyone waits
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.22 * io(prog(t, BEAT[0] + .1, .4)))
    if T_FINAL <= t < T_FINAL + .5:
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.2 * (1 - prog(t, T_FINAL, .5)))
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

# ================================================================ thumbnail
def thumbnail(out):
    img = bg_meet().copy()
    meet_life(img, 3.0)
    big = Image.new('RGBA', img.size, (0, 0, 0, 0))
    if HAS_PHOTO:                                           # the real Charger, big, mid-frame
        ph = Image.open(PHOTO).convert('RGB')
        w_ = 980; h_ = int(w_ * ph.height / ph.width)
        ph = ph.resize((w_ * K, h_ * K), Image.LANCZOS)
        fr = Image.new('RGBA', ((w_ + 24) * K, (h_ + 24) * K), (255, 255, 255, 255))
        fr.paste(ph, (12 * K, 12 * K))
        paste_rot(img, fr, 540, 760, rot=-3)
    else:
        paste_charger(img, 60, 1000, 960)
    d = D(img)
    rings(d, 60 + 966, 870, 0.3, 0, 9, (255, 80, 80), 4, 1, 260)
    npc(img, 720, 2560, 1.7, BUYER, mk('up', 'shrug', brows='up', eyes='wide', mouth=1.0, look=-1, sweat=.4))
    d = D(img)
    for i, (txt, size, col) in enumerate((('FAKE', 230, TAG), ('EXHAUST?!', 170, (255, 255, 255)))):
        d.text(540, 190 + i * 200, txt, size, col, stroke=12, sc=(10, 10, 16))
    img.resize((W, H), Image.LANCZOS).save(out)

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
    def rumble(d, f0=34.0, f1=52.0, amp=1.0, burble=1.0):
        """Synthetic V8-style rumble (the 'speaker' sound): harmonic stack with lumpy firing modulation."""
        tt = np.arange(int(SR * d)) / SR
        f = f0 + (f1 - f0) * np.clip(tt / d, 0, 1) ** .6
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = sum(np.sin(ph * k + k * .7) / k ** .7 for k in range(1, 10))
        s *= 1 + .45 * burble * np.sign(np.sin(ph * .5)) * (0.6 + 0.4 * np.sin(ph * .25))
        s = lpf(s, 10)
        env = np.minimum(1, tt * 10) * np.minimum(1, (d - tt) * 3)
        return s / 6 * env * amp
    def woof():
        a = tone(420, .09, 30, .7) + tone(300, .09, 20, .5); return np.concatenate([a, np.zeros(int(SR * .06)), a * .8])
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    add(0.0, rumble(LE[0] + .2, 30, 60), .55)                  # frame 1: the "exhaust" is already roaring
    add(T_NOT, sfx.stamp(), .3)
    add(LS[1] - .15, sfx.pop(), .3)
    for s_ in SCENES[1:]:                                       # scene change: whoosh + soft thump + hurried steps
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
        for k_ in range(3): add(s_ + .08 + k_ * .25, step(), .35)
    for tt_ in (T_SPKS, T_TUNE, T_AMP): add(tt_, sfx.pop(), .3)
    add(LS[3], rumble(LE[3] - LS[3], 30, 34, .5, .6), .25)      # the rig on the bench idles under the line
    add(T_GAS - .03, sfx.stamp(), .32); add(T_GAS, sfx.buzzer(.25), .18)
    add(T_HUND - .1, rumble(LE[5] - T_HUND + .4, 32, 78), .9)  # the big 126 dB rev
    add(T_HUND + 1.0, sfx.ding(1320, .6), .15)
    add(T_SAME - .05, sfx.pop(), .3)
    add(T_FRATZ - .05, sfx.pop(), .3); add(T_LOGO - .05, sfx.sparkle(), .25)
    add(T_REC, click(900, 1400, .08), .5)
    add(LS[9] + .05, sfx.pop(), .3); add(T_REVIEW - .05, sfx.pop(), .25)
    add(T_GEARS - .1, sfx.slide_down(), .2)
    add(T_DRAG - .05, rumble(T_STEALTH - T_DRAG + .1, 36, 70), .9)   # rev at dawn: neighbours wake
    add(T_DRAG + .1, sfx.whoosh(.5, 30), .25)                  # birds scatter
    for k_ in range(3): add(T_DRAG + .4 + k_ * .5, woof(), .35)
    add(T_STEALTH - .02, sfx.slide_down(), .25); add(T_STEALTH, rumble(1.2, 28, 28, .25, .2), .3)
    for i in range(3): add(T_RACE - .9 + i * .3, tick(), .9)   # the tree: three ambers, then green
    add(T_RACE, sfx.ding(1760, .5), .2)
    add(T_RACE, rumble(2.6, 40, 95, 1.0, 1.2), .7); add(T_RACE, sfx.vroom(1.4), .45)
    add(T_RACE + .02, sfx.screech(.35), .25)
    add(T_33 - .1, sfx.pop(), .3); add(T_39 - .1, sfx.pop(), .3)
    add(T_WINS - .05, sfx.stamp(), .3)
    for k_ in range(2): add(BEAT[0] + .2 + k_ * .3, tick(), .6)
    add(T_FINAL - .02, sting(), .6); add(T_CARD, sfx.pop(), .35)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s
    duck = np.ones(n)                                           # keep words on top of the rumbles
    for w in WORDS:
        duck[int(max(0, w['s'] - .05) * SR):int((w['e'] + .05) * SR)] = .55
    cs = np.cumsum(np.concatenate([[0.0], duck])); kk = 2400
    duck = np.concatenate([duck[:kk // 2], (cs[kk:] - cs[:-kk]) / kk, duck[-(kk - kk // 2):]])[:n]
    mixd = v * 1.0 + fxa[:n] * 0.55 * duck + bed * 0.6
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
    elif mode == 'thumb':
        thumbnail(sys.argv[2])
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
