"""Lamborghini Urus vs Audi RS Q8 skit: showroom -> Audi lot -> group boardroom -> showroom. Flat-vector style, 1080x1920 @30.
Same cast, caption system and mix chain as tesla-locked / aston-cygnet.
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
DUR = round(WORDS[-1]['e'] + 2.3, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/urus-rsq8/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
T_S2 = LE[5] + 0.75                        # scene cuts (whip pans)
T_S3 = LE[11] + 0.55
T_S4 = LE[15] + 0.6
BEAT = (LE[16], LS[17])
T_LAMBO, T_AUDI0, T_COUSIN = word_t(0, 'Lamborghini'), word_t(0, 'Audi'), word_t(1, 'cousin')
T_TWO, T_DOLLARS = word_t(3, 'two'), word_t(3, 'dollars')
T_AUDI1, T_HALF = word_t(4, 'Audi'), word_t(5, 'half')
T_ENG = word_t(6, 'engine')
T_FOUR, T_V8, T_COVERS, T_SWAP = word_t(7, 'Four'), word_t(7, 'V8'), word_t(7, 'covers'), word_t(7, 'swap')
T_PLAT, T_PLAT2 = word_t(8, 'platform'), LS[9]
T_GRAND, T_POWER = word_t(10, 'hundred'), word_t(11, 'power')
T_VW, T_BADGE, T_SHAPE = LS[13], word_t(14, 'badge'), word_t(15, 'shape')
T_FINAL = LS[17]
T_CARD = LE[17] + 0.3                      # final caption card (last ~2 s)
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

# ================================================================ emblems (hand-drawn, generic, not logo files)
GOLD, GOLD2, INK = (214, 176, 84), (150, 116, 40), (16, 16, 18)
LAMBO_Y, LAMBO_Y2, LAMBO_Y3 = (250, 192, 22), (255, 226, 110), (176, 120, 6)
NARDO, NARDO2, NARDO3 = (150, 154, 158), (204, 208, 212), (92, 96, 102)
CHROME, CHROME2 = (214, 220, 228), (120, 128, 140)
AUDI_RED = (204, 20, 36)
def shield(d, cx, cy, s=1.0, col=GOLD, fill=INK):
    """Generic pointed shield (gold rim, dark field, gold chevron) for the Italian brand."""
    pts = [(cx - 60 * s, cy - 70 * s), (cx + 60 * s, cy - 70 * s), (cx + 58 * s, cy + 6 * s), (cx + 36 * s, cy + 48 * s),
           (cx, cy + 76 * s), (cx - 36 * s, cy + 48 * s), (cx - 58 * s, cy + 6 * s)]
    d.poly(pts, fill, col, max(2, 8 * s))
    d.line([(cx - 34 * s, cy + 18 * s), (cx, cy - 30 * s), (cx + 34 * s, cy + 18 * s)], col, max(2, 10 * s))
    d.rect(cx - 46 * s, cy - 58 * s, cx + 46 * s, cy - 46 * s, col, r=3 * s)

def rings(d, cx, cy, s=1.0, col=CHROME, w=7):
    """Generic four interlocking rings."""
    for i in range(4):
        d.ell(cx + (i - 1.5) * 52 * s, cy, 36 * s, 36 * s, None, col, max(1.5, w * s))

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

def wheel(d, wx, wy, r, lambo):
    d.ell(wx, wy, r, r, (20, 20, 24))
    d.ell(wx, wy, r * .9, r * .9, None, (44, 44, 50), max(2, r * .06))
    d.ell(wx, wy, r * .7, r * .7, (66, 68, 74))                         # brake disc behind the spokes
    d.chord(wx, wy, r * .64, r * .64, 200, 290, (230, 190, 30) if lambo else AUDI_RED)     # caliper
    rim = (52, 54, 60) if lambo else (196, 200, 208)                    # dark forged vs silver
    d.ell(wx, wy, r * .7, r * .7, None, rim, max(3, r * .1))
    n = 5 if lambo else 10
    for a in range(n):
        ra = math.radians(a * 360 / n + 18)
        for off in ((-.1, .1) if lambo else (0,)):
            d.line([(wx + r * .13 * math.cos(ra + off), wy + r * .13 * math.sin(ra + off)),
                    (wx + r * .66 * math.cos(ra + off * 1.4), wy + r * .66 * math.sin(ra + off * 1.4))], rim, max(2, r * (.09 if lambo else .07)))
    d.ell(wx, wy, r * .16, r * .16, rim, (90, 94, 102), 2)
    if lambo: shield(d, wx, wy, r * .0018, GOLD, INK)
    else: d.ell(wx, wy, r * .06, r * .06, CHROME)

URUS_CTRL = [(.012, .17), (0.0, .34), (.006, .47), (.06, .55), (.20, .60), (.33, .64), (.47, .93), (.62, .965), (.79, .90),
             (.93, .74), (1.0, .69), (1.0, .43), (.99, .19), (.86, .15), (.5, .16), (.14, .15)]
RSQ8_CTRL = [(.014, .17), (0.0, .36), (.006, .56), (.05, .63), (.20, .67), (.33, .71), (.47, .955), (.63, .99), (.80, .93),
             (.93, .78), (.995, .72), (1.0, .46), (.99, .20), (.86, .16), (.5, .17), (.14, .16)]
def suv(d, x0, ground, L, kind):
    """Lamborghini Urus / Audi RS Q8 side profile (front to the left): same wheelbase and stance, different skin."""
    Hh = L * .42
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    lambo = kind == 'urus'
    base, hi, lo = (LAMBO_Y, LAMBO_Y2, LAMBO_Y3) if lambo else (NARDO, NARDO2, NARDO3)
    sill = (22, 22, 26)
    d.ell(x0 + L * .5, ground + 4, L * .58, 15, (0, 0, 0, 90))
    body = spline([P(u, v) for u, v in (URUS_CTRL if lambo else RSQ8_CTRL)], 8)
    shade(d, body, hi, lo, ground - .98 * Hh, ground - .2 * Hh)
    # black lower cladding / side skirt
    shade(d, spline([P(.02, .17), P(.5, .18), P(.98, .17), P(.99, .29), P(.5, .27), P(.01, .28)], 6), (40, 40, 46), sill,
          ground - .29 * Hh, ground - .16 * Hh)
    d.line(spline([P(.04, .50), P(.30, .55), P(.62, .57), P(.97, .60)], 8, closed=False), hi + (210,), 3)   # shoulder light
    if lambo:                                            # sharp Y crease along the door
        d.line([P(.30, .44), P(.52, .40), P(.80, .44)], lo, 4)
        d.line([P(.52, .40), P(.62, .30)], lo, 3)
    else:                                                # quattro blisters over the arches
        for u in (.17, .80):
            d.arc(*P(u, .29), L * .14, Hh * .26, 195, 345, hi + (220,), 4)
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
    else:
        gh = spline([P(.35, .72), P(.47, .915), P(.63, .95), P(.79, .89), P(.885, .78), P(.87, .73)], 5)
    shade(d, gh, (86, 106, 130), (16, 20, 30), ground - .94 * Hh, ground - .66 * Hh)
    d.poly(gh, None, (20, 22, 28), 4)
    d.poly([P(.40, .70), P(.43, .70), P(.50, .88), P(.47, .88)], (255, 255, 255, 50))
    d.poly([P(.595, .66 if lambo else .72), P(.62, .66 if lambo else .72), P(.625, .93), P(.60, .93)], (20, 20, 24))
    # door cut, handle, mirror
    d.line([P(.34, .64), P(.31, .22)], lo, 3)
    d.line([P(.61, .66), P(.62, .21)], lo, 3)
    d.rect(*P(.52, .56), *P(.57, .535), (30, 30, 34) if lambo else CHROME, r=3)
    d.poly(spline([P(.355, .70), P(.41, .72), P(.41, .78), P(.36, .78)], 4), (24, 24, 28) if lambo else base, (24, 26, 34), 3)
    if lambo:
        d.poly([P(-.004, .20), P(.10, .22), P(.06, .40), P(.0, .42)], (18, 18, 22))           # big intake
        d.poly([P(.015, .44), P(.12, .52), P(.20, .555), P(.11, .47)], (24, 24, 28), (24, 26, 34), 3)
        d.line([P(.03, .46), P(.10, .505), P(.16, .53)], (250, 250, 255), 4)                  # Y headlight
        d.line([P(.10, .505), P(.09, .45)], (250, 250, 255), 4)
        d.poly([P(.94, .64), P(1.0, .62), P(1.0, .58), P(.95, .60)], (210, 24, 30))          # thin tail light
        d.poly([P(.90, .74), P(.99, .72), P(.99, .70), P(.92, .715)], (26, 26, 30))          # roof spoiler lip
        shield(d, *P(.035, .50), L * .00028, GOLD, INK)
    else:
        g = [P(-.004, .22), P(.04, .22), P(.05, .52), P(.012, .56), P(-.002, .52)]           # octagonal grille
        d.poly(g, (20, 20, 24), (60, 62, 68), 4)
        for v in (.27, .32, .37, .42, .47):
            d.line([P(.002, v), P(.045, v)], (48, 50, 56), 2)
        lamp = [P(.03, .55), P(.15, .60), P(.19, .62), P(.13, .565)]
        d.poly(lamp, (232, 238, 246), (24, 26, 34), 3)
        d.line([P(.05, .555), P(.16, .595)], (150, 210, 255), 3)
        d.rect(*P(.06, .585), *P(.10, .565), AUDI_RED, r=2)                                 # RS badge
        d.poly([P(.95, .66), P(1.0, .65), P(1.0, .60), P(.95, .61)], (200, 24, 30))
        d.line([P(.90, .63), P(.95, .64)], (200, 24, 30), 4)
    for u in (.17, .80):
        wheel(d, P(u, 0)[0], ground - r, r, lambo)

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
    up = T_SHAPE <= t < T_SHAPE + 1.4
    st = mk('cross', 'raise1' if up else 'cross', look=-1, smile=1 if up else 0, brows='up' if up else 'flat')
    st['blink'] = (t % 3.9) < .12
    npc(img, 852, 1352, .5, NPC['exec2'], st)
    img.paste(bg_board().crop((0, 990 * K, W * K, 1100 * K)), (0, 990 * K))
    d = D(img)
    for i in range(3):                                      # floating z's
        ph = (t * .6 + i / 3) % 1
        d.text(104 + ph * 40, 860 - ph * 90, 'z', 22 + 14 * ph, (240, 240, 250, int(255 * (1 - ph))))

# ---- the road behind the Audi lot: ordinary traffic, and the comment-bait gag on the near sidewalk:
# an inflatable tube man. An attendant switches its fan off, gets buried under it, the fan kicks back on
# and he ends up dangling from its arm for the rest of the scene. Never mentioned.
FAR_SW, FAR_G, NEAR_G, NEAR_SW = 536, 586, 632, 662
RL, PS = 200, .1                                            # road car length, background person scale
TX, TSEG, TN = 470, 22, 10                                  # tube man base x, segment length, segments
GAG = dict(walk=1.6, off=3.9, flat=4.5, on=6.6)
def tube_inflate(tau):
    if tau < GAG['off']: return 1.0
    if tau < GAG['on']: return 1 - oc(prog(tau, GAG['off'], GAG['flat'] - GAG['off']))
    return ob(prog(tau, GAG['on'], .35))
def tube_chain(tau):
    k = tube_inflate(tau)
    pts, ang = [(TX, NEAR_SW - 16)], 0.0
    for i in range(TN):
        wob = .55 * math.sin(tau * 7.3 + i * .55) * (i / TN) + .25 * math.sin(tau * 11.1 - i * .9) * (i / TN) ** 2
        ang = k * wob + (1 - k) * min(2.5, i * .42)          # deflated: flops over to the right
        x, y = pts[-1]
        pts.append((x + math.sin(ang) * TSEG, y - math.cos(ang) * TSEG))
    return pts, ang, k
def lot_life(img, t):
    tau = t - T_S2
    # far sidewalk: a woman pushing along, mostly behind the stats card
    npc(img, 760 - 34 * tau, FAR_SW, PS * .9, NPC['p2'], walkst(t, 9, look=-1))
    # steady traffic both ways
    for col, sp, ph, lane, fc in (((238, 238, 240), 260, 0, FAR_G, -1), ((60, 110, 200), 300, 700, FAR_G, -1),
                                  ((250, 250, 250), 240, 1200, FAR_G, -1), ((80, 80, 90), 280, 300, NEAR_G, 1),
                                  ((200, 50, 50), 320, 1000, NEAR_G, 1)):
        x = (tau * sp + ph) % 1700 - 300
        car_at(img, col, RL, x if fc > 0 else W - x, lane, fc, roof=(230, 60, 40) if col == (250, 250, 250) else None)
    d = D(img)
    d.rect(0, NEAR_SW - 26, W, NEAR_SW - 22, (214, 214, 210))           # railing
    d.rect(0, NEAR_SW - 10, W, NEAR_SW - 6, (214, 214, 210))
    for x in range(0, W, 64):
        d.rect(x, NEAR_SW - 32, x + 5, NEAR_SW + 6, (192, 192, 188))
    # walker passing on the near sidewalk early on
    npc(img, -60 + 120 * tau, NEAR_SW + 2, PS, NPC['p4'], walkst(t, 14, lp='open', rp='open', look=1))
    pts, ang, k = tube_chain(tau)
    att = NPC['victim']
    on = tau >= GAG['on']
    if not on:                                              # attendant walks over, switches it off, gets buried
        if tau < GAG['walk']:
            ax = -40
        else:
            ax = -40 + (TX + 30 + 40) * oc(prog(tau, GAG['walk'], GAG['off'] - .5 - GAG['walk']))
        if tau < GAG['off'] - .5:
            st = walkst(t, 10, look=1)
        elif tau < GAG['off']:
            st = mk('rest', (-120, 200), look=-1, brows='flat')
        elif tau < GAG['flat']:
            st = mk('up', 'up', eyes='wide', brows='up')
        else:                                               # flailing under the tube
            st = mk((60 + 40 * math.sin(tau * 13), -200), (60 + 40 * math.cos(tau * 11), -220), eyes='wide', out_lpose=True, out_rpose=True)
            ax += 6 * math.sin(tau * 5)
        if ax > -30:
            npc(img, ax, NEAR_SW + 4, PS, att, st)
    d = D(img)
    d.rect(TX - 26, NEAR_SW - 22, TX + 26, NEAR_SW + 4, (60, 64, 72), r=5, ol=(30, 30, 36), w=3)   # fan box
    for i in range(3):
        d.line([(TX - 16 + i * 16, NEAR_SW - 16), (TX - 16 + i * 16, NEAR_SW - 2)], (30, 30, 36), 3)
    RED_T = (236, 56, 50)
    d.line(pts, OL, 34); d.line(pts, RED_T, 26)
    for i in range(2, TN, 3):                               # white stripes
        d.line([pts[i], pts[i + 1]], (255, 236, 236), 26)
    # arms off segment 7
    ax_, ay_ = pts[7]
    for side in (-1, 1):
        aa = side * (1.3 + .8 * math.sin(tau * 9 + side)) * k + (1 - k) * 2.2
        L1 = 46
        e1 = (ax_ + math.sin(aa) * L1, ay_ - math.cos(aa) * L1)
        aa2 = aa + side * .7 * math.sin(tau * 13 + side * 2) * k
        e2 = (e1[0] + math.sin(aa2) * L1 * .8, e1[1] - math.cos(aa2) * L1 * .8)
        d.line([pts[7], e1, e2], OL, 20); d.line([pts[7], e1, e2], RED_T, 14)
        if on and side == 1:
            hand = e2
    # face on the top segment
    hx, hy = pts[-1]
    d.ell(hx, hy, 17, 17, RED_T, OL, 3)
    for s_ in (-1, 1):
        d.ell(hx + s_ * 6, hy - 3, 4, 5, (255, 255, 255)); d.ell(hx + s_ * 6, hy - 2, 2, 2.5, OL)
    d.arc(hx, hy + 3, 7, 5, 20, 160, OL, 3)
    if on:                                                  # the attendant, dangling from the arm
        sw = 14 * math.sin(tau * 6)
        npc_rot(img, hand[0] - 8 + sw * .4, hand[1] + 600 * PS, PS, att, mk('up', 'up', eyes='wide', brows='up'), sw)

@lru_cache(None)
def car_layer(kind, L):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .62) * K), (0, 0, 0, 0))
    suv(D(img, ox=-L * .1, oy=-L * .56), 0, 0, L, kind)
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
    arr = np.concatenate([grad(WALL_Y * K, W * K, (14, 14, 16), (36, 36, 40)), grad((H - WALL_Y) * K, W * K, (200, 202, 204), (234, 235, 236))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-40, W, 170):                          # tall wall panels with brushed trim
        d.poly([(x + 8, 80), (x + 160, 80), (x + 160, WALL_Y - 40), (x + 8, WALL_Y - 40)], (28, 28, 32))
        for yy in range(120, WALL_Y - 60, 110):                # hexagon wall relief
            d.line([(x + 30, yy), (x + 84, yy - 26), (x + 138, yy)], (44, 44, 50), 3)
        d.line([(x + 8, 80), (x + 8, WALL_Y - 40)], (70, 62, 40), 2)
    for px in (150, 459, 768):                            # pendant lights
        d.line([(px, 0), (px, 70)], (70, 74, 78), 3)
        d.chord(px, 92, 46, 28, 180, 360, (52, 52, 56))
        d.ell(px, 92, 30, 6, (255, 240, 200))
    d.rect(0, WALL_Y - 8, W, WALL_Y, GOLD)
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (214, 216, 219), 2)
    img = spot(img, CX, 120, 70, 470, 800)
    d = D(img)
    shield(d, CX, 196, 0.85, GOLD, INK)
    d.text(CX, 300, 'L A M B O R G H I N I', 40, (236, 222, 180), path=FONT_X)
    # turntable
    d.ell(CX, 905, 400, 50, (14, 16, 16))
    d.ell(CX, 897, 394, 44, (46, 46, 50), GOLD, 5)
    d.ell(CX, 897, 340, 34, (60, 60, 64))
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
    d.rect(984, 330, 1000, 536, (70, 74, 82))              # dealer pylon at the lot entrance
    d.rect(950, 300, 1080, 400, (34, 36, 40), r=6, ol=(120, 124, 132), w=3)
    rings(d, 1015, 340, .3, CHROME, 7)
    d.text(1015, 378, 'AUDI', 20, (230, 230, 236), path=FONT_X)
    return img

@lru_cache(None)
def bg_board():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (30, 38, 52), (62, 74, 92)), grad((H - WALL_Y) * K, W * K, (70, 72, 80), (46, 48, 56))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(0, W, 120):                                # glass partitions with a night skyline behind
        d.line([(x, 0), (x, WALL_Y)], (22, 26, 34), 6)
    rr = np.random.default_rng(9)
    for bx in range(-20, W, 64):
        bh = int(rr.integers(140, 360))
        d.rect(bx, WALL_Y - bh, bx + 54, WALL_Y, (40, 48, 64, 160))
        for wy in range(WALL_Y - bh + 16, WALL_Y - 10, 26):
            if rr.random() < .55: d.rect(bx + 10, wy, bx + 20, wy + 10, (255, 220, 140, 110))
    for x in range(0, W, 120):
        d.line([(x + 12, 40), (x + 70, 0)], (255, 255, 255, 30), 8)
    d.rect(0, 0, W, 60, (20, 22, 28))
    for px in (180, 459, 738):
        d.ell(px, 40, 60, 10, (255, 236, 196))
    d.rect(100, 200, 820, 720, (16, 18, 22), r=14, ol=(40, 40, 46), w=8)  # wall screen
    d.rect(0, WALL_Y - 10, W, WALL_Y, (24, 26, 32))
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

# ---- performance schedules: (time, left pose, right pose, extras)
def buyer_sched():
    return [(0.0, 'rest', 'point', dict(brows='angry', eyes='wide')),
            (T_AUDI0 - .1, 'up', 'point', dict(brows='angry', eyes='wide')),
            (LS[1], 'rest', 'point', dict(brows='angry')),
            (T_COUSIN + .1, 'hip', 'rest', dict(brows='flat', smile=-1)),
            (LS[2] - .1, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (LE[2] + .2, 'rest', 'rest', dict(brows='up')),
            (T_DOLLARS, 'head', 'head', dict(brows='up', eyes='wide', smile=-1)),
            (LS[4] - .1, 'rest', 'point', dict(brows='angry')),
            (T_HALF, 'up', 'up', dict(brows='angry', eyes='wide')),
            (LE[5] + .3, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # scene 2: baffled
            (T_S2, 'hip', 'open', dict(brows='angry')),
            (LS[6] - .1, 'hip', 'point', dict(brows='angry')),
            (LE[6] + .15, 'hip', 'rest', dict(brows='flat')),
            (T_COVERS, 'rest', 'rest', dict(brows='up', eyes='wide')),
            (LS[8] - .1, 'rest', 'point', dict(brows='angry')),
            (LE[8] + .2, 'chin', 'rest', dict(brows='up')),
            (LS[10] - .1, 'up', 'up', dict(brows='up', eyes='wide', sweat=1)),
            (T_POWER, 'shrug', 'shrug', dict(brows='worried', eyes='wide')),
            (LE[11] + .3, 'rest', 'rest', dict(brows='worried')),
            # scene 3: baffled -> deflating
            (T_S3, 'chin', 'cross', dict(brows='worried')),
            (LS[12] - .1, 'shrug', 'shrug', dict(brows='worried', eyes='wide')),
            (LE[12] + .2, 'rest', 'rest', dict(brows='worried')),
            (T_VW + .2, 'head', 'rest', dict(brows='up', eyes='wide')),
            (LS[14] - .1, 'rest', 'open', dict(brows='flat', smile=-1, tired=0.35)),
            (T_SHAPE + .1, 'head', 'head', dict(brows='worried', smile=-1, tired=0.3)),
            # scene 4: resigned
            (T_S4, 'rest', 'rest', dict(brows='worried', tired=0.5, smile=-1)),
            (LS[16] + .4, 'rest', 'open', dict(brows='flat', tired=0.5)),
            (LE[16] + .2, 'rest', 'rest', dict(brows='flat', tired=0.5)),
            (T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    s += [(LS[3] + .05, 'open', 'clasp', {}), (LE[3] + .1, 'clasp', 'clasp', {}),
          (LS[5] - .05, 'open', 'clasp', {}), (LE[5] + .1, 'clasp', 'clasp', {}),
          (LS[7] + .05, 'clasp', 'reach', {}), (LE[7], 'clasp', 'clasp', {}),
          (LS[9] - .05, 'open', 'clasp', {}), (LE[9] + .1, 'clasp', 'clasp', {}),
          (LS[13] - .05, 'present', 'clasp', {}), (LE[13] + .2, 'clasp', 'clasp', {}),
          (LS[15] - .05, 'present', 'clasp', {}), (LE[15] + .2, 'clasp', 'clasp', {}),
          (T_FINAL, 'open', 'clasp', dict(look=0)), (LE[17] + .3, 'clasp', 'clasp', dict(look=0))]
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
def board_screen(img, t):
    """Wall screen in the boardroom: the two brands, then the shared owner, the badge, the shape."""
    d = D(img)
    ek = io(prog(t, T_VW - .05, .5))                          # emblems slide down to make room for the owner box
    ey = 430 + 60 * ek
    for x_, lab, kind in ((300, 'LAMBORGHINI', 'shield'), (620, 'AUDI', 'rings')):
        glow = kind == 'shield' and t >= T_BADGE - .05
        if glow:
            gk = popin(t, T_BADGE - .05, .3)
            d.ell(x_, ey, 96 * gk, 96 * gk, (255, 214, 64, 70), (255, 214, 64), 6)
        if kind == 'shield': shield(d, x_, ey, .8 * (1 + .12 * math.sin((t - T_BADGE) * 9) * math.exp(-(t - T_BADGE) * 2) if glow else 1))
        else: rings(d, x_, ey, .65, CHROME, 7)
        d.text(x_, ey + 72, lab, 26, (230, 232, 238), path=FONT_X)
    if t < T_VW:                                              # "who owns both?"
        qk = popin(t, LS[12] + .1, .3)
        if qk > .05:
            d.text(CX + 1, ey - 4, '?', 96 * qk, TAG)
        return
    lk = prog(t, T_VW + .15, .35)                             # org-chart lines down from the owner card
    if lk > 0:
        d.line([(CX, 300), (CX, 300 + 80 * lk)], (255, 255, 255), 5)
        for x_ in (300, 620):
            d.line([(CX, 380), (CX + (x_ - CX) * lk, 380)], (255, 255, 255), 5)
            if lk >= 1: d.line([(x_, 380), (x_, ey - 72)], (255, 255, 255), 5)
    if t >= T_SHAPE - .05:                                     # the shape: Urus body traced on the screen
        sk = popin(t, T_SHAPE - .05, .3)
        c = car_layer('urus', 300)
        f_ = .6 * sk
        c2 = c.resize((max(1, int(c.width * f_)), max(1, int(c.height * f_))), Image.LANCZOS)
        X0, Y0 = CX - c2.width / K / 2, 704 - c2.height / K
        img.paste(c2, (int(X0 * K), int(Y0 * K)), c2)
        d = D(img)
        tk = prog(t, T_SHAPE + .1, .6)
        pts = [(X0 + f_ * (u * 300 + 30), Y0 + f_ * (.56 * 300 - v * .42 * 300)) for u, v in URUS_CTRL]
        sp = spline(pts, 8)
        n = max(2, int(len(sp) * tk))
        d.line(sp[:n], (255, 214, 64), 5)

def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    if sc in (0, 3):
        img = bg_showroom().copy()
        showroom_life(img, t, sc)
        paste_car(img, 'urus', CX - 290, 894, 580)
    elif sc == 1:
        img = bg_lot().copy()
        lot_life(img, t)
        paste_car(img, 'rsq8', 40, 902, 390)
        paste_car(img, 'urus', 488, 902, 390)
        d = D(img)
        pk = window(t, T_PLAT - .05, T_S3 + .1, .3, .3)
        if pk > 0:                                          # same platform: one glowing chassis under both bodies
            for x0 in (40, 488):
                a_ = int(255 * pk * (.75 + .25 * math.sin(t * 8)))
                wx0, wx1, wy = x0 + .17 * 390, x0 + .80 * 390, 902 - 390 * .42 * .25
                d.line([(wx0, wy), (wx1, wy)], (90, 220, 255, a_), 10)
                for wx in (wx0, wx1):
                    d.line([(wx, wy - 34), (wx, wy + 34)], (90, 220, 255, a_), 8)
                    d.ell(wx, wy, 13, 13, (255, 255, 255, a_))
        for x_, txt, bgc, fg in ((235, 'AUDI RS Q8', (230, 232, 236), (30, 30, 36)), (682, 'LAMBORGHINI URUS', INK, LAMBO_Y)):
            f = font(24 * K); w_ = f.getlength(txt) / K
            d.rect(x_ - w_ / 2 - 14, 680, x_ + w_ / 2 + 14, 714, bgc, r=8)
            d.text(x_, 697, txt, 24, fg)
    else:
        img = bg_board().copy()
        board_screen(img, t)
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
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
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
        punches = ((T_AUDI0, .05), (T_TWO, .03), (T_HALF, .05))
    elif sc == 1:
        z = 1.05 + 0.015 * io(prog(t, t0, 10))
        sx = 46 * (1 - oc(prog(t, t0, 1.6)))               # settle after the whip
        punches = ((T_COVERS, .03), (T_GRAND, .05))
    elif sc == 2:
        z = 1.02 + 0.04 * io(prog(t, t0, 8))
        punches = ((T_VW, .04), (T_BADGE, .03), (T_SHAPE, .03))
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_FINAL, .05),)
        pk = io(prog(t, T_FINAL - .05, .5))                # salesman turns to camera: push in on him
        z += 0.14 * pk
        sx = 150 * pk
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
def cover_icon(kind):
    """Engine cover, top view: Lamborghini (black, gold) / Audi (silver, red)."""
    im = Image.new('RGBA', (150 * K, 80 * K), (0, 0, 0, 0)); d = D(im)
    body, acc = ((22, 22, 26), GOLD) if kind == 'urus' else ((186, 190, 198), AUDI_RED)
    d.rect(6, 6, 144, 74, body, r=18, ol=(255, 255, 255), w=4)
    for x in range(30, 130, 20):
        d.line([(x, 20), (x, 60)], acc, 5)
    return im

def panel(d, x0, y0, x1, y1, a, col=(14, 16, 22)):
    d.rect(x0, y0, x1, y1, col + (int(236 * a),), r=30)

FINAL = [("Urus or RS Q8?", 92, TAG), ("Comment below.", 70, (255, 255, 255)), ("Next: another car", 66, (210, 214, 224)),
         ("that's secretly", 66, (210, 214, 224)), ("another car.", 66, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 430, 112
ONSCREEN = ['LAMBORGHINI URUS', 'AUDI RS Q8', 'AUDI?!', '≈', 'COUSIN', 'ABOUT $230K', 'ABOUT $120K', '?',
            'LAMBORGHINI URUS · 2022 US BASE', 'AUDI RS Q8 · 2022 US BASE', 'VS', 'RS Q8', 'URUS', 'ENGINE', '4.0 L V8',
            'TWIN-TURBO', 'COVERS', 'PLATFORM', 'MLB EVO', 'SWAP', '=', '+ $$$ ?', 'POWER', 'A LITTLE MORE', 'LAMBORGHINI',
            'AUDI', 'SAME OWNER:', 'VOLKSWAGEN GROUP', 'L A M B O R G H I N I'] + [f[0] for f in FINAL]

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        # the two cars as cards, the AUDI?! stamp, then "cousin"
        pa = window(t, T_LAMBO - .05, LS[3] - .05, .1, .3)
        if pa > 0:
            used = True
            put(img, photo_card('lamborghini_urus.jpg', 'LAMBORGHINI URUS', (24, 24, 28), LAMBO_Y, 360), 683, 450, popin(t, T_LAMBO, .35), pa, rot=-4)
            if t >= T_AUDI0 - .05:
                put(img, photo_card('audi_rsq8.jpg', 'AUDI RS Q8', (230, 232, 236), (24, 24, 30)), 236, 470, popin(t, T_AUDI0 - .05, .35), pa, rot=4)
            if t >= LS[1]:
                k_ = popin(t, LS[1], .3); d = D(img)
                d.ell(459, 460, 46 * k_, 46 * k_, GREEN + (int(250 * pa),), (14, 40, 24, int(255 * pa)), 5)
                d.text(459, 462, '≈', 70 * max(k_, .05), (255, 255, 255, int(255 * pa)))
            if t >= T_COUSIN:
                k_ = popin(t, T_COUSIN, .3)
                d.rect(459 - 100 * k_, 646, 459 + 100 * k_, 700, TAG + (int(250 * pa),), r=12)
                if k_ > .6: d.text(459, 673, 'COUSIN', 36, (24, 22, 20, int(255 * pa)))
        sa = window(t, T_AUDI0 + .05, LS[1] + .1, .05, .3)
        if sa > 0:
            used = True
            s = 1 + 1.1 * (1 - oc(prog(t, T_AUDI0 + .05, .14)))
            put(img, stamp_img('AUDI?!', RED), 690, 548, s * .62, sa, rot=-10)
        ta = window(t, T_TWO - .05, T_S2 + .05, .15, .3)
        if ta > 0:
            used = True
            s = popin(t, T_TWO, .35)
            sw = math.sin((t - T_TWO) * 6) * 4 * math.exp(-(t - T_TWO) * 2)
            put(img, price_tag('ABOUT $230K', 'LAMBORGHINI URUS · 2022 US BASE', TAG, 620), CX, 415, s, ta, rot=sw)
        tb = window(t, T_AUDI1 - .02, T_S2 + .05, .1, .3)
        if tb > 0:
            used = True
            t0 = T_HALF if t >= T_HALF else T_AUDI1
            s = popin(t, t0, .3)
            sw = math.sin((t - t0) * 7) * 5 * math.exp(-(t - t0) * 2.4)
            txt = 'ABOUT $120K' if t >= T_HALF else '?'
            put(img, price_tag(txt, 'AUDI RS Q8 · 2022 US BASE', (232, 234, 238), 620), CX, 600, s * .9, tb, rot=sw)
            d = D(img)
            d.ell(CX, 508, 34, 34, (24, 24, 30, int(255 * tb)), (255, 255, 255, int(255 * tb)), 4)
            d.text(CX, 509, 'VS', 30, (255, 255, 255, int(255 * tb)))
    elif sc == 1:
        ca = window(t, LS[6] - .05, T_GRAND - .02, .25, .25)
        if ca > 0:
            used = True
            al = int(255 * ca)
            panel(d, 70, 116, 850, 410, ca)
            d.text(470, 150, 'RS Q8', 34, (235, 236, 240, al))
            d.text(720, 150, 'URUS', 34, LAMBO_Y + (al,))
            d.line([(100, 176), (820, 176)], (70, 74, 84, al), 3)
            for y, lab, t_lab in ((228, 'ENGINE', T_FOUR), (304, 'COVERS', T_COVERS), (376, 'PLATFORM', T_PLAT)):
                if t < t_lab - .05: continue
                ra = min(ca, prog(t, t_lab - .05, .2))
                d.text(100, y, lab, 28, (170, 176, 190, int(255 * ra)), anchor='lm', path=FONT_X)
            if t >= T_FOUR - .05:                           # 4.0 L V8, twin-turbo, on both sides
                s = popin(t, T_FOUR, .3)
                for vx in (470, 720):
                    d.text(vx, 218, '4.0 L V8', 44 * max(s, .05), (255, 255, 255, al))
                    if t >= T_V8 - .3:
                        d.text(vx, 250, 'TWIN-TURBO', 20, (170, 176, 190, int(al * prog(t, T_V8 - .3, .2))), path=FONT_X)
                ek = popin(t, T_V8 + .2, .3)
                if ek > .05:
                    d.ell(595, 226, 24 * ek, 24 * ek, GREEN + (al,)); d.text(595, 227, '=', 40 * ek, (14, 40, 24, al))
            if t >= T_COVERS - .05:                          # the covers swap sides on "swap"
                k_ = io(prog(t, T_SWAP - .05, .55))
                for kind, x0, x1, arc in (('urus', 720, 470, -1), ('rsq8', 470, 720, 1)):
                    x = x0 + (x1 - x0) * k_; y = 304 + arc * 40 * math.sin(math.pi * k_)
                    put(img, cover_icon(kind), x, y, .62 * popin(t, T_COVERS, .3), ca)
                d = D(img)
                if t >= T_SWAP - .05:
                    d.text(595, 306, 'SWAP', 22, (255, 214, 64, int(al * prog(t, T_SWAP - .05, .2))))
            if t >= T_PLAT - .05:
                s = popin(t, T_PLAT2, .3) if t >= T_PLAT2 else 0.0
                for vx in (470, 720):
                    d.text(vx, 376, 'MLB EVO', 36 * max(popin(t, T_PLAT, .3), .05), (90, 220, 255, al))
                if s > .05:
                    d.ell(595, 376, 24 * s, 24 * s, GREEN + (al,)); d.text(595, 377, '=', 40 * s, (14, 40, 24, al))
        ga = window(t, T_GRAND - .02, T_POWER - .05, .05, .2)
        if ga > 0:
            used = True
            s = 1 + 1.0 * (1 - oc(prog(t, T_GRAND, .14)))
            put(img, stamp_img('+ $$$ ?', (255, 190, 40)), CX, 290, s * .8, ga, rot=-6)
        pa = window(t, T_POWER - .05, T_S3 + .05, .2, .2)
        if pa > 0:                                           # no figures: shape only
            used = True
            al = int(255 * pa)
            panel(d, 70, 136, 850, 400, pa)
            d.text(CX, 176, 'POWER', 34, (235, 236, 240, al))
            for i, (lab, frac, col) in enumerate((('RS Q8', .86, NARDO2), ('URUS', .93, LAMBO_Y))):
                y = 240 + i * 70
                k_ = io(prog(t, T_POWER + i * .15, .5))
                d.text(110, y, lab, 28, (200, 204, 214, al), anchor='lm', path=FONT_X)
                d.rect(250, y - 20, 250 + 560 * frac * k_, y + 20, col + (al,), r=10)
            if t >= T_POWER + .45:
                k_ = popin(t, T_POWER + .45, .3)
                d.rect(560 - 140 * k_, 352, 560 + 140 * k_, 390, TAG + (al,), r=10)
                if k_ > .6: d.text(560, 371, 'A LITTLE MORE', 26, (24, 22, 20, al))
    elif sc == 2:
        if t >= T_VW - .05:                                  # the reveal card
            used = True
            k_ = popin(t, T_VW - .05, .35)
            put(img, owner_card(), CX, 320, k_, 1.0, rot=-2 * math.exp(-(t - T_VW) * 3))
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

@lru_cache(None)
def owner_card():
    c = Image.new('RGBA', (640 * K, 150 * K), (0, 0, 0, 0)); d = D(c)
    d.rect(8, 10, 636, 146, (0, 0, 0, 90), r=22)
    d.rect(0, 0, 628, 136, (246, 247, 250), r=22, ol=TAG, w=6)
    d.text(314, 40, 'SAME OWNER:', 32, (110, 116, 130), path=FONT_X)
    d.text(314, 92, 'VOLKSWAGEN GROUP', 56, (18, 22, 34))
    return c

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
    add(T_LAMBO, sfx.pop(), .35); add(T_AUDI0 + .05, sfx.stamp(), .55)
    add(LS[1], sfx.pop(), .25); add(T_COUSIN, sfx.ding(1320, .6), .14)
    add(T_TWO - .05, sfx.whoosh(), .3); add(T_DOLLARS + .2, sfx.cha_ching(), .35)
    add(T_AUDI1, sfx.pop(), .3); add(T_HALF, sfx.pop(), .4); add(T_HALF + .05, sfx.coin_clink(), .2)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    add(T_S2 + .4, sfx.vroom(), .12)
    for k_ in range(4): add(T_S2 + .8 + k_ * 2.3, sfx.whoosh(.9, 60), .09)     # passing traffic
    add(T_S2 + GAG['off'], sfx.slide_down(), .07); add(T_S2 + GAG['on'], sfx.whoosh(.3, 12), .08)   # tube man (quiet)
    for k_ in range(3): add(T_S2 + .9 + k_ * 3.7, chirp(), .5)
    add(T_FOUR, sfx.pop(), .3); add(T_V8 + .2, sfx.ding(), .16)
    add(T_COVERS, sfx.pop(), .3); add(T_SWAP, sfx.whoosh(.35, 14), .3)
    add(T_PLAT, sfx.pop(), .3); add(T_PLAT2, sfx.ding(1760), .16)
    add(T_GRAND, sfx.stamp(), .45); add(T_POWER, sfx.slide_down(), .18)
    add(T_VW - .05, sfx.boom(), .4); add(T_VW, sfx.stamp(), .4)
    add(T_BADGE, sfx.sparkle(), .3); add(T_SHAPE, sfx.sparkle(), .25); add(T_SHAPE + .1, sfx.ding(), .18)
    for k_ in range(3): add(T_S4 + .05 + k_ * .42, step(), .3)
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
