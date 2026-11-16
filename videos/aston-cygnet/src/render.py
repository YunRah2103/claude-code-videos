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
T_ASTON = word_t(0, 'Aston')
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
def shade(d, pts, c0, c1, v0, v1):
    """Fill a polygon with a vertical gradient c0 (design y v0) -> c1 (design y v1)."""
    m = Image.new('L', d.i.size, 0)
    ImageDraw.Draw(m).polygon([d.p(*q) for q in pts], fill=255)
    y0, y1 = d.p(0, v0)[1], d.p(0, v1)[1]
    h, w = d.i.size[1], d.i.size[0]
    a = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    g = np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3)).astype(np.uint8)
    d.i.paste(Image.fromarray(g), (0, 0), m)

def wheel(d, wx, wy, r, aston):
    d.ell(wx, wy, r, r, (22, 22, 26))
    d.ell(wx, wy, r * .9, r * .9, None, (46, 46, 52), max(2, r * .06))
    d.ell(wx, wy, r * .68, r * .68, (58, 60, 66))                       # brake disc behind the spokes
    if aston:
        d.chord(wx, wy, r * .62, r * .62, 200, 290, (214, 170, 60))     # caliper
    rim = CHROME if aston else (184, 188, 196)
    d.ell(wx, wy, r * .68, r * .68, None, rim, max(3, r * .1))
    n = 10 if aston else 5
    for a in range(n):
        ra = math.radians(a * 360 / n + 18)
        for off in ((0,) if aston else (-.09, .09)):
            d.line([(wx + r * .12 * math.cos(ra + off), wy + r * .12 * math.sin(ra + off)),
                    (wx + r * .64 * math.cos(ra + off * 1.6), wy + r * .64 * math.sin(ra + off * 1.6))], rim, max(2, r * (.07 if aston else .09)))
    d.ell(wx, wy, r * .15, r * .15, rim, (80, 84, 92), 2)
    d.ell(wx, wy, r * .07, r * .07, AM_GREEN if aston else (200, 40, 40))

def city_car(d, x0, ground, L, kind):
    """Toyota iQ / Aston Martin Cygnet side profile (front to the left): same body, different face and trim."""
    Hh = L / 2.0
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    aston = kind == 'cygnet'
    if aston: base, hi, lo, sill = AM_GREEN, (64, 146, 112), (10, 50, 36), (8, 34, 26)
    else: base, hi, lo, sill = (210, 213, 218), (250, 251, 253), (150, 154, 162), (96, 100, 108)
    d.ell(x0 + L * .5, ground + 4, L * .58, 15, (0, 0, 0, 90))
    body = spline([P(u, v) for u, v in CAR_CTRL], 8)
    shade(d, body, hi, lo, ground - .96 * Hh, ground - .2 * Hh)
    shade(d, spline([P(.02, .16), P(.5, .17), P(.98, .16), P(.99, .27), P(.5, .25), P(.01, .26)], 6), lo, sill,
          ground - .27 * Hh, ground - .15 * Hh)
    d.line(spline([P(.03, .43), P(.30, .47), P(.62, .49), P(.97, .50)], 8, closed=False), hi + (200,), 3)   # shoulder light
    d.line(spline([P(.06, .33), P(.5, .34), P(.95, .33)], 8, closed=False), lo + (160,), 3)                 # lower crease
    # wheel wells + arch lips
    r = Hh * .21
    for u in (.165, .825):
        wx, wy = P(u, 0)[0], ground - r
        d.chord(wx, wy, r * 1.2, r * 1.2, 180, 360, (16, 16, 18))
        d.rect(wx - r * 1.2, wy - 2, wx + r * 1.2, ground - 4, (16, 16, 18))
        d.arc(wx, wy, r * 1.24, r * 1.24, 190, 350, hi, 4)
    d.poly(body, None, (24, 26, 34), 5)
    # glass with reflections, black pillars
    gh = spline([P(.29, .60), P(.38, .78), P(.455, .885), P(.62, .915), P(.83, .895), P(.925, .83), P(.955, .66), P(.94, .60)], 6)
    shade(d, gh, (86, 106, 130), (18, 24, 34), ground - .92 * Hh, ground - .6 * Hh)
    d.poly(gh, None, (20, 22, 28), 4)
    for u0, u1 in ((.33, .37), (.70, .76)):
        d.poly([P(u0, .62), P(u0 + .03, .62), P(u1 + .05, .86), P(u1 + .015, .86)], (255, 255, 255, 46))
    d.poly([P(.585, .60), P(.612, .60), P(.622, .91), P(.594, .91)], (22, 22, 26))
    d.poly([P(.875, .60), P(.90, .60), P(.905, .88), P(.88, .89)], (22, 22, 26))
    if aston:                                           # tan leather through the glass
        d.poly(spline([P(.64, .62), P(.66, .80), P(.71, .82), P(.70, .62)], 4), (176, 112, 66))
        d.line([P(.665, .66), P(.68, .79)], (120, 70, 40), 2)
    # door, handle, mirror, fuel flap
    d.line([P(.27, .57), P(.25, .20)], lo, 3)
    d.line([P(.62, .58), P(.63, .20)], lo, 3)
    d.rect(*P(.50, .505), *P(.56, .478), CHROME if aston else (176, 180, 188), r=3)
    d.poly(spline([P(.30, .61), P(.36, .63), P(.36, .69), P(.31, .69)], 4), base, (24, 26, 34), 3)
    d.ell(*P(.80, .54), L * .018, L * .018, None, lo, 2)
    if aston:
        g = spline([P(-.006, .43), P(.04, .43), P(.05, .30), P(.035, .19), P(-.002, .18)], 4)
        d.poly(g, (20, 22, 26), CHROME, 5)
        for v in (.22, .26, .30, .34, .38):
            d.line([P(.002, v), P(.04, v)], CHROME2, 2)
        d.poly([P(.25, .38), P(.33, .40), P(.33, .43), P(.25, .42)], CHROME)          # side strake
        lamp = spline([P(.02, .46), P(.10, .51), P(.17, .52), P(.10, .45)], 4)
        d.poly(lamp, (240, 246, 255), (24, 26, 34), 3)
        d.line([P(.05, .47), P(.14, .505)], (110, 200, 255), 3)
        wings(d, *P(.10, .54), 0.075, CHROME, bar=False)
        d.poly([P(.975, .58), P(.998, .58), P(.998, .78), P(.965, .76)], (210, 30, 40), (60, 10, 14), 3)
    else:
        d.poly(spline([P(-.002, .21), P(.035, .22), P(.04, .32), P(.0, .32)], 4), (36, 38, 44))
        d.ell(*P(.03, .24), L * .012, L * .012, (240, 240, 230))
        lamp = spline([P(.015, .44), P(.09, .48), P(.19, .54), P(.17, .49), P(.08, .42)], 4)
        d.poly(lamp, (232, 238, 246), (24, 26, 34), 3)
        d.ell(*P(.09, .465), L * .02, L * .02, (196, 210, 228), (110, 120, 136), 2)
        d.ell(*P(.155, .505), 5, 5, (255, 190, 60))
        toyota_ovals(d, *P(.02, .40), 0.16, (120, 124, 132), 3)
        d.poly([P(.97, .55), P(.998, .55), P(.998, .80), P(.96, .78)], (230, 60, 50), (60, 10, 14), 3)
    for u in (.165, .825):
        wheel(d, P(u, 0)[0], ground - r, r, aston)

# ---- generic background cars for the road (facing right)
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
    if roof:
        d.rect(*P(.47, .86), *P(.56, .76), roof, r=3)
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

def car_at(img, col, L, x, ground, facing=1, rot=0.0, lift=0.0, roof=None):
    """x = car centre. Rotation is about the body centre."""
    paste_rot(img, road_car(col, L, roof), x, ground - .25 * L - lift, rot * facing, flip=facing < 0)

# ================================================================ background people
def cast(skin, hair, suit, pants=None, shoe='26262a', shirt='f4f4f6', tie=None, glasses=False, style='part', badge=False):
    sk = hexc(skin); su = hexc(suit)
    return dict(skin=sk, skin2=tuple(int(c * .86) for c in sk), hair=hexc(hair), suit=su, suit2=tuple(int(c * .72) for c in su),
                shirt=hexc(shirt), tie=hexc(tie) if tie else None, pants=hexc(pants or suit), shoe=hexc(shoe),
                glasses=glasses, hairstyle=style, lids=0.0, badge=badge)
NPC = dict(recep=cast('8d5a3b', '111014', '1c1d22', tie='0d4f3a', badge=True),
           cleaner=cast('e8b996', '5a3a22', '3f6f8f', pants='2f4f68', shirt='dfe8ee', style='messy'),
           walker=cast('f2d0b0', 'b04a2a', '6b4a8a', pants='2a2a30', style='messy'),
           cust1=cast('c58c64', '2b1d16', 'b8452f', pants='30343c'),
           cust2=cast('f0c9a8', 'd9b36a', '2f5d4a', pants='d8d0c0', glasses=True),
           exec1=cast('dcae8c', '9a9a9a', '2a2a2e', tie='6a1020'),
           exec2=cast('6e4630', '151212', '23304a', tie='c9a24a', glasses=True),
           victim=cast('e6b490', '3a2a1a', 'e0a030', pants='3a4a6a', style='messy'),
           p2=cast('9c6a48', '111111', 'c03040', pants='222222', style='messy'),
           p3=cast('f2c8a6', 'e0c070', '4a8ac0', pants='303030'),
           p4=cast('7a4c34', '1a1a1a', '40a060', pants='1a1a1a', style='messy'),
           p5=cast('e0b090', '603018', '808890', pants='404050'))

def mk(lp='rest', rp='rest', **kw):
    st = dict(lpose=POSES[lp] if isinstance(lp, str) else lp, rpose=POSES[rp] if isinstance(rp, str) else rp,
              out_lpose=lp in OUTBEND if isinstance(lp, str) else False, out_rpose=rp in OUTBEND if isinstance(rp, str) else False)
    st.update(kw)
    return st

def npc(img, X, FY, s, cfg, st):
    """Draw a cast member at scale s with feet at (X, FY)."""
    person(D(img, k=K * s, ox=-X / s, oy=FEET_Y - FY / s), 0, FEET_Y, cfg, st)

def npc_rot(img, X, CY, s, cfg, st, rot):
    """Rotated cast member (for the flying pedestrian); (X, CY) = body centre."""
    S = int(1300 * s * K) + 2
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    person(D(lay, k=K * s, ox=-650, oy=FEET_Y - 450 - 650), 0, FEET_Y, cfg, st)
    paste_rot(img, lay, X, CY, rot)

def walkst(t, rate=11, **kw):
    st = mk(**kw); st['walk'] = t * rate; st['dy'] = -abs(math.sin(t * rate)) * 10
    return st

def stars(d, x, y, t, s=1.0):
    for i in range(3):
        a = t * 5 + i * 2.1
        sx, sy = x + math.cos(a) * 22 * s, y + math.sin(a) * 7 * s
        pts = [(sx + math.cos(math.radians(k * 72 - 90)) * (8 if k % 1 == 0 else 3) * s, sy + math.sin(math.radians(k * 72 - 90)) * 8 * s) for k in range(5)]
        d.poly([pts[j] for j in (0, 2, 4, 1, 3)], (255, 220, 60))

def showroom_life(img, t, sc):
    f = int(t * FPS)
    # receptionist behind the desk (left): on the phone in scene 1, typing in scene 4
    if sc == 0:
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
    if sc == 0:
        # cleaner polishing the rear of the car, a colleague crossing with a coffee
        wob = math.sin(t * 9)
        st = mk((150 + 26 * wob, 110 + 16 * math.cos(t * 9)), 'rest', prop={'lpose': 'cloth'}, look=-1, smile=1)
        st['blink'] = (t % 3.7) < .12; st['dy'] = math.sin(t * 9) * 3
        npc(img, 812, 978, .42, NPC['cleaner'], st)
        x = 960 - 130 * t
        if -80 < x < 1000:
            npc(img, x, 952, .34, NPC['walker'], walkst(t, 9, lp='rest', rp=(60, 210), prop={'rpose': 'cup'}, look=-1))
    else:
        # a couple admiring the car on the right
        nod = math.sin(t * 2.4) * 3
        st1 = mk('point', 'rest', look=-1, brows='up', smile=1); st1['dy'] = nod; st1['blink'] = (t % 3.3) < .12
        st2 = mk('rest', (-70, -110), out_rpose=True, look=-1, brows='flat'); st2['blink'] = ((t + 1) % 3.6) < .12
        npc(img, 806, 982, .42, NPC['cust1'], st1)
        npc(img, 884, 988, .40, NPC['cust2'], st2)

def board_life(img, t):
    # two board members at the table ends: one asleep, one fist-pumps on "Correct."
    bob = math.sin(t * 1.3) * 5
    st = mk('cross', 'cross', look=0, smile=0); st['blink'] = True; st['dy'] = bob
    npc(img, 70, 1352, .5, NPC['exec1'], st)
    up = T_CORRECT <= t < T_CORRECT + 1.4
    st = mk('cross', 'raise1' if up else 'cross', look=-1, smile=1 if up else 0, brows='up' if up else 'flat')
    st['blink'] = (t % 3.9) < .12
    npc(img, 852, 1352, .5, NPC['exec2'], st)
    img.paste(bg_board().crop((0, 990 * K, W * K, 1100 * K)), (0, 990 * K))
    d = D(img)
    for i in range(3):                                      # floating z's
        ph = (t * .6 + i / 3) % 1
        d.text(104 + ph * 40, 860 - ph * 90, 'z', 22 + 14 * ph, (240, 240, 250, int(255 * (1 - ph))))

# ---- the road behind the parking lot: traffic, then a hit-and-run and a flipped car (background only)
FAR_SW, FAR_G, NEAR_G, NEAR_SW = 536, 586, 632, 662
LT = dict(hit=3.6, flip=4.0, land=5.0, bump=6.8)
RL, PS = 200, .085                                          # road car length, pedestrian scale
def lot_life(img, t):
    tau = t - T_S2
    d = D(img)
    hit, flip, land, bump = (LT[k] for k in ('hit', 'flip', 'land', 'bump'))
    def brake_x(tt):                                        # front bumper of the red car
        if tt < hit: return 240 + 520 * (tt - hit)
        e = min(tt - hit, 1.2); return 240 + 520 * e - 215 * e * e
    if tau > hit:                                           # skid marks
        for dy in (-3, -14):
            d.line([(250, NEAR_G + dy), (brake_x(tau) - 50, NEAR_G + dy)], (28, 28, 32, 180), 5)
    # far sidewalk: a stroller (mostly behind the stats card later)
    npc(img, 760 - 34 * tau, FAR_SW, PS * .92, NPC['p2'], walkst(t, 9, look=-1))
    # far lane (leftbound)
    car_at(img, (238, 238, 240), RL, 1040 - 260 * tau, FAR_G, -1)
    if 2.2 < tau < flip:                                    # the car that swerves and flips
        car_at(img, (60, 110, 200), RL, 1160 - 330 * (tau - 2.2), FAR_G, -1, rot=-7 * prog(tau, 3.7, .3))
    elif tau >= flip:
        k_ = prog(tau, flip, land - flip)
        x = 566 + 90 * (1 - oc(k_)) - 24 * prog(tau, land, .5)
        lift = 70 * 4 * k_ * (1 - k_)
        car_at(img, (60, 110, 200), RL, x, FAR_G + 8 * k_, -1, rot=-(540 * oc(k_)) if tau < land else -180, lift=lift)
        if land <= tau < land + .6:                         # sparks
            rr = np.random.default_rng(int(t * FPS))
            for _ in range(12):
                a = rr.uniform(-2.6, -.5); v = rr.uniform(24, 70) * (1 + (tau - land) * 2)
                d.line([(x + 70, FAR_G), (x + 70 + math.cos(a) * v, FAR_G + math.sin(a) * v)], (255, 200, 60), 3)
        if tau >= land:                                     # smoke column (stays under the card)
            for i in range(8):
                ph = ((tau - land) * .5 + i / 8) % 1
                d.ell(x + 20 * math.sin(i * 2 + tau) + ph * 30, FAR_G - 40 - ph * 70, 16 + 26 * ph, 14 + 22 * ph,
                      (120, 120, 126, int(170 * (1 - ph))))
    if tau > 6.0:                                           # van stuck behind it, honking
        x = 1180 - 300 * min(tau - 6.0, 1.0) + 150 * min(tau - 6.0, 1.0) ** 2
        car_at(img, (250, 250, 250), 220, max(x, 880), FAR_G, -1, roof=(230, 60, 40))
    # the pedestrian: walking on his phone, stepping out, launched, landed in the far lane
    v = NPC['victim']
    if tau < 2.4:
        npc(img, 120 + 45 * tau, NEAR_SW, PS, v, walkst(t, 9, rp='phone', prop={'rpose': 'phone'}, look=1))
    elif tau < hit:
        k_ = prog(tau, 2.4, hit - 2.4)
        npc(img, 228 + 12 * k_, NEAR_SW - 34 * k_, PS, v, walkst(t, 7, rp='phone', prop={'rpose': 'phone'}, look=1))
    elif tau < hit + 1.0:
        e = tau - hit
        x = 240 + 300 * e; y = (NEAR_SW - 34) + (FAR_G + 8 - NEAR_SW + 34) * e - 440 * e * (1 - e)
        npc_rot(img, x, y - 450 * PS, PS, v, mk('up', 'up', eyes='wide', brows='up'), 810 * e)
        px, py = 250 + 420 * e, 610 - 520 * e * (1 - e) - 30 * e
        d = D(img); d.rect(px - 4, py - 6, px + 4, py + 6, (24, 24, 28))
    else:
        e = tau - hit - 1.0
        bounce = 14 * math.sin(e / .3 * math.pi) if e < .3 else 0
        thumbs = tau > 8.5
        st = mk('rest', 'raise1' if thumbs else 'rest', eyes='' if thumbs else 'wide', smile=1 if thumbs else -1)
        st['blink'] = not thumbs and (tau % 1.2) < .6
        npc_rot(img, 540, FAR_G - 4 - bounce, PS, v, st, 90)
        d = D(img)
        if not thumbs:
            stars(d, 500, FAR_G - 26, tau, 1.3)
        d.rect(664, FAR_G - 10, 672, FAR_G + 2, (24, 24, 28))
    # near lane (rightbound)
    car_at(img, (80, 80, 90), RL, -220 + 260 * (tau + 1.5), NEAR_G, 1)
    if 2.4 < tau:
        xf = brake_x(tau)
        shake = math.sin(tau * 80) * 4 if bump <= tau < bump + .3 else 0
        car_at(img, (210, 30, 36), RL, xf - RL / 2 + shake, NEAR_G, 1)
        if tau > hit + 1.2 and (tau * 2.5) % 1 < .5:        # hazards
            d.ell(xf - RL + 4, NEAR_G - 40, 7, 7, (255, 170, 30)); d.ell(xf - 4, NEAR_G - 40, 7, 7, (255, 170, 30))
        if hit <= tau < hit + .25:                          # impact flash
            k_ = prog(tau, hit, .25)
            for i in range(8):
                a = math.radians(i * 45)
                d.line([(244 + 16 * math.cos(a), 600 + 16 * math.sin(a)), (244 + (24 + 40 * k_) * math.cos(a), 600 + (24 + 40 * k_) * math.sin(a))],
                       (255, 230, 90, int(255 * (1 - k_))), 5)
    if tau > 5.5:                                           # taxi rear-ends the red car
        stop = brake_x(9) - RL - RL / 2
        xt = min(-220 + 340 * (tau - 5.5), stop)
        car_at(img, (250, 200, 30), RL, xt, NEAR_G, 1, roof=(40, 40, 40))
        for th in (7.0, 8.1, 9.5):                          # honk lines
            if th <= tau < th + .35:
                for j in range(3):
                    d.arc(xt + RL / 2 + 6, NEAR_G - 60, 12 + j * 11, 12 + j * 11, 300, 60, (255, 255, 255, 230), 4)
    # near sidewalk: panic, a guy filming, a helper, and an oblivious jogger
    if tau > 4.6:
        x = 700 + 130 * math.sin((tau - 4.6) * 1.7)
        npc(img, x, NEAR_SW, PS, NPC['p2'], walkst(t, 22, lp='up', rp='up', look=1 if math.cos((tau - 4.6) * 1.7) > 0 else -1, eyes='wide'))
    filming = tau > 5.2
    npc(img, 860, NEAR_SW, PS, NPC['p3'], mk('rest', 'raise1' if filming else 'phone', prop={'rpose': 'phone'}, look=-1))
    if tau > 5.5:
        x = 60 + min(1, (tau - 5.5) / 1.4) * 360
        st = walkst(t, 20, lp='up', rp='up', eyes='wide') if tau < 6.9 else mk('up' if (tau * 3) % 2 < 1 else 'rest', 'up', eyes='wide')
        npc(img, x, NEAR_SW, PS, NPC['p5'], st)
    npc(img, -60 + 110 * tau, NEAR_SW + 2, PS, NPC['p4'], walkst(t, 16, lp='open', rp='open', look=1))
    d = D(img)
    d.rect(0, NEAR_SW - 26, W, NEAR_SW - 22, (214, 214, 210))
    d.rect(0, NEAR_SW - 10, W, NEAR_SW - 6, (214, 214, 210))
    for x in range(0, W, 64):
        d.rect(x, NEAR_SW - 32, x + 5, NEAR_SW + 6, (192, 192, 188))

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
    return img

@lru_cache(None)
def bg_lot():
    SKY = 516
    arr = np.concatenate([grad(SKY * K, W * K, (96, 150, 206), (236, 214, 186)), grad((H - SKY) * K, W * K, (98, 100, 106), (70, 72, 78))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.ell(820, 250, 90, 90, (255, 236, 200, 120)); d.ell(820, 250, 52, 52, (255, 246, 222))
    for cx_, cy_, s in ((180, 150, 1.0), (640, 100, .8)):
        for dx, dy, r in ((0, 0, 50), (50, -20, 60), (110, 0, 46), (55, 14, 50)):
            d.ell(cx_ + dx * s, cy_ + dy * s, r * s, r * .7 * s, (250, 246, 240, 200))
    rng = np.random.default_rng(5); x = -20
    while x < W:                                          # skyline
        bw, bh = rng.integers(70, 150), rng.integers(110, 300)
        col = mix((130, 150, 176), (160, 168, 186), rng.random())
        d.rect(x, SKY - bh, x + bw, SKY + 4, col)
        for wy in range(int(SKY - bh + 20), SKY - 14, 30):
            for wx in range(int(x + 12), int(x + bw - 14), 24):
                d.rect(wx, wy, wx + 11, wy + 14, (176, 192, 214))
        x += bw + rng.integers(4, 20)
    d.rect(0, SKY, W, 540, (196, 194, 188))                # far sidewalk
    d.rect(0, 540, W, 642, (62, 64, 70))                   # road
    d.rect(0, 542, W, 545, (236, 236, 230)); d.rect(0, 637, W, 640, (236, 236, 230))
    for x in range(-20, W, 80):
        d.rect(x, 594, x + 40, 598, (240, 220, 120))
    d.rect(0, 642, W, 666, (196, 194, 188))                # near sidewalk
    d.rect(0, 666, W, 674, (170, 170, 166))                # kerb
    for lx in (300, 640):                                  # bay lines in perspective
        d.poly([(lx - 4, 674), (lx + 4, 674), (lx + (lx - CX) * .9 + 8, 1010), (lx + (lx - CX) * .9 - 8, 1010)], (236, 236, 230))
    d.poly([(-20, 1000), (W, 1000), (W, 1014), (-20, 1014)], (236, 236, 230))
    for px_ in (40, 900):                                  # lamp posts on the far side
        d.rect(px_ - 4, 300, px_ + 4, 532, (60, 64, 72))
        d.line([(px_, 304), (px_ + (34 if px_ < CX else -34), 296)], (60, 64, 72), 7)
        d.ell(px_ + (44 if px_ < CX else -44), 300, 18, 7, (240, 240, 226))
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
          (LS[7] + .05, 'clasp', 'reach', {}), (LE[7], 'clasp', 'clasp', {}),
          (T_GRILLE - .1, 'clasp', 'reach', {}), (LE[11] + .1, 'clasp', 'clasp', {}),
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
        showroom_life(img, t, sc)
        paste_car(img, 'cygnet', CX - 290, 894, 580)
    elif sc == 1:
        img = bg_lot().copy()
        lot_life(img, t)
        paste_car(img, 'iq', 40, 902, 390)
        paste_car(img, 'cygnet', 488, 902, 390)
        d = D(img)
        for x_, txt, bgc in ((235, 'TOYOTA iQ', (230, 232, 236)), (682, 'ASTON MARTIN CYGNET', AM_GREEN)):
            f = font(24 * K); w_ = f.getlength(txt) / K
            d.rect(x_ - w_ / 2 - 14, 680, x_ + w_ / 2 + 14, 714, bgc, r=8)
            d.text(x_, 697, txt, 24, (30, 30, 36) if bgc != AM_GREEN else (240, 236, 220))
    else:
        img = bg_board().copy()
        board_screen(D(img), t)
        board_life(img, t)
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
def photo_card(name, label, bar):
    ph = Image.open(os.path.join(HERE, '..', 'assets', name)).convert('RGB')
    w = 400; h = int(w * ph.height / ph.width)
    ph = ph.resize((w * K, h * K), Image.LANCZOS)
    card = Image.new('RGBA', ((w + 28) * K, (h + 84) * K), (0, 0, 0, 0)); cd = D(card)
    cd.rect(6, 8, w + 26, h + 82, (0, 0, 0, 90), r=10)
    cd.rect(0, 0, w + 20, h + 74, (250, 250, 248), r=10)
    card.paste(ph, (10 * K, 10 * K))
    cd.rect(10, h + 18, w + 10, h + 64, bar, r=8)
    cd.text(w / 2 + 10, h + 42, label, 28, (24, 24, 30) if bar != AM_GREEN else (240, 236, 220))
    return card

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

ONSCREEN = ['=', 'ASTON MARTIN', 'CYGNET', 'TOYOTA iQ', 'ASTON MARTIN CYGNET', '£30,995', 'ASTON MARTIN CYGNET · 2011',
            'FROM ABOUT £10,000', 'TOYOTA iQ · 2011', 'TOYOTA', '+ LEATHER', 'ENGINE', '1.33 L', '97 HP', '0–62 MPH', '11.8 s',
            'SAME', 'NEW', 'GRILLE', 'LIGHTS', 'LEATHER', 'WHY?', 'AVERAGE CO₂', 'VANTAGE', 'VANQUISH', 'TARGET', 'AVERAGE', '✓']

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        # the real cars, side by side: Cygnet photo, then the iQ it is built on, then the TOYOTA stamp
        pa = window(t, T_ASTON - .05, LS[3] - .05, .1, .3)
        if pa > 0:
            used = True
            put(img, photo_card('aston_cygnet.jpg', 'ASTON MARTIN CYGNET', AM_GREEN), 683, 450, popin(t, T_ASTON, .35), pa, rot=-4)
            if t >= T_TOYOTA0 - .05:
                put(img, photo_card('toyota_iq.jpg', 'TOYOTA iQ', (230, 232, 236)), 236, 470, popin(t, T_TOYOTA0 - .05, .35), pa, rot=4)
            if t >= LS[1]:
                k_ = popin(t, LS[1], .3); d = D(img)
                d.ell(459, 460, 46 * k_, 46 * k_, GREEN + (int(250 * pa),), (14, 40, 24, int(255 * pa)), 5)
                d.text(459, 464, '=', 70 * max(k_, .05), (255, 255, 255, int(255 * pa)))
        sa = window(t, T_TOYOTA0 + .05, LS[3] - .05, .05, .3)
        if sa > 0:
            used = True
            s = 1 + 1.1 * (1 - oc(prog(t, T_TOYOTA0 + .05, .14)))
            put(img, stamp_img('TOYOTA', RED), 690, 548, s * .62, sa, rot=-10)
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
            panel(d, 70 + ox, 136, 850 + ox, 432, ca)
            d.text(470 + ox, 174, 'TOYOTA iQ', 34, (235, 236, 240, al))
            d.text(720 + ox, 174, 'CYGNET', 34, (190, 230, 205, al))
            d.line([(100 + ox, 202), (820 + ox, 202)], (70, 74, 84, al), 3)
            rows = [(266, 'ENGINE', '97 HP', '1.33 L', T_ENG, T_HP), (352, '0–62 MPH', '11.8 s', '', T_SPEED, T_SPEED + .25)]
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
                d.text(595 + ox, 404, 'SAME', 40 * max(s, .05), GREEN + (al,))
        # three "NEW" insets with leader lines to the Cygnet
        for i, (kind, tw, cx_, tx, ty) in enumerate((('grille', T_GRILLE, 170, 496, 844), ('lights', T_LIGHTS, 459, 523, 808),
                                                     ('leather', T_LEATH2, 748, 749, 762))):
            ia = window(t, tw - .05, T_S3 + .05, .08, .2)
            if ia <= 0: continue
            used = True
            s = popin(t, tw, .32)
            lk = prog(t, tw + .1, .2)
            if lk > 0:
                sx_, sy_ = cx_, 318 + 118
                d.line([(sx_, sy_), (sx_ + (tx - sx_) * lk, sy_ + (ty - sy_) * lk)], (255, 255, 255, int(230 * ia)), 5)
                d.ell(tx, ty, 9 * lk, 9 * lk, TAG + (int(255 * ia),), (30, 30, 30, int(255 * ia)), 3)
            put(img, inset(kind), cx_, 318, s, ia)
            d = D(img)
            if s > .3:
                d.rect(cx_ - 46, 176, cx_ + 46, 214, RED + (int(255 * ia),), r=10)
                d.text(cx_, 196, 'NEW', 28, (255, 255, 255, int(255 * ia)))
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
    def horn(d=.32):
        tt = np.arange(int(SR * d)) / SR
        return (np.sign(np.sin(2 * np.pi * 415 * tt)) + np.sign(np.sin(2 * np.pi * 520 * tt))) * .25 * np.minimum(1, (d - tt) * 30)
    L0 = T_S2
    for k_ in range(3): add(L0 + 1.0 + k_ * 1.6, sfx.whoosh(.9, 60), .10)      # passing cars
    add(L0 + LT['hit'] - .35, sfx.screech(), .14); add(L0 + LT['hit'], sfx.thump(), .22); add(L0 + LT['hit'] + .02, sfx.pop(), .10)
    add(L0 + LT['hit'] + 1.0, sfx.fall(), .10)
    add(L0 + LT['flip'] - .3, sfx.screech(.5), .12); add(L0 + LT['land'], sfx.crash(), .26)
    add(L0 + LT['bump'], sfx.crash(.4), .12)
    for th in (7.0, 8.1, 9.5): add(L0 + th, horn(), .10)
    add(L0 + 7.4, horn(.5), .06)
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
