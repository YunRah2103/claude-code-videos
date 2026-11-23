"""Mercedes 'Acceleration Increase' skit: showroom -> the road (the subscription expires mid-drive) -> online store /
The Drive -> showroom. Flat-vector style, 1080x1920 @30. Built on bmw-heated-seats/src/render.py: same buyer, caption
system, camera, whip pans and mix chain; new salesman, Mercedes-Benz showroom, EQE 350 sedan, user-supplied music bed.
One background oddity (never mentioned): a penguin pushing a lawn mower, in every set it can reach.
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
DUR = round(WORDS[-1]['e'] + 1.9, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
CACHE = os.path.expanduser('~/.cache/mercedes-acceleration')
VOICE_CACHE = os.path.join(CACHE, 'voice.wav')
MUSIC = os.environ.get('MUSIC', os.path.join(CACHE, 'music.mp3'))   # user-supplied background track (not committed)

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
T_WHAT = LS[1]
T_CLOSE = LS[2] - 0.1                      # in-scene cut: closer on the car
T_288, T_349, T_1200 = word_t(2, '288'), word_t(2, '349'), word_t(3, '1,200')
T_S2 = LE[3] + 0.12                        # whip to the road
T_EXP = LS[4] - 0.3                        # the subscription expires
T_STOP = LE[4] + 0.15                      # car has stalled
T_S3 = LS[5] - 0.3
T_NOV, T_DRIVE = word_t(5, 'November'), word_t(6, 'Drive')
T_NOBODY, T_BUY = word_t(6, 'nobody'), word_t(6, 'buy')
T_S4 = LS[7] - 0.3
T_TECH, T_OVER = word_t(7, 'technically'), word_t(7, 'overcharged')
BEAT = (LE[7], LS[8])
T_FINAL = LS[8]
T_CARD = LE[8] + 0.25                      # final question card (last ~1.6 s)
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

# ================================================================ Mercedes-Benz star and the EQE 350 sedan (front to the left)
CHROME, CHROME2 = (214, 220, 228), (120, 128, 140)
EQ_BLUE = (0, 168, 226)
def mb_star(d, cx, cy, s=1.0, col=CHROME, col2=None, ring=True, bg=None):
    """Three-pointed star in a ring, drawn as shaded kites."""
    R = 60 * s; col2 = col2 or tuple(int(c * .72) for c in col)
    if bg: d.ell(cx, cy, R, R, bg)
    if ring: d.ell(cx, cy, R, R, None, col, max(1, 7 * s))
    for a in (-90, 30, 150):
        ra = math.radians(a); ux, uy = math.cos(ra), math.sin(ra)
        tip = (cx + ux * R * .9, cy + uy * R * .9)
        back = (cx - ux * R * .1, cy - uy * R * .1)
        w = R * .14
        lft, rgt = (cx - uy * w, cy + ux * w), (cx + uy * w, cy - ux * w)
        d.poly([tip, lft, back], col); d.poly([tip, back, rgt], col2)

def shade(d, pts, c0, c1, v0, v1):
    """Fill a polygon with a vertical gradient c0 (design y v0) -> c1 (design y v1)."""
    m = Image.new('L', d.i.size, 0)
    ImageDraw.Draw(m).polygon([d.p(*q) for q in pts], fill=255)
    y0, y1 = d.p(0, v0)[1], d.p(0, v1)[1]
    h, w = d.i.size[1], d.i.size[0]
    a = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    g = np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3)).astype(np.uint8)
    d.i.paste(Image.fromarray(g), (0, 0), m)

# EQE 350 sedan, proportions from the real car (4946 mm long, 1510 mm tall, 3120 mm wheelbase): P(u, v) = fractions of L.
EQE_BODY = [(.022, .052), (.004, .088), (0.0, .125), (.008, .158), (.035, .178), (.12, .196), (.22, .210), (.275, .218),
            (.37, .283), (.50, .305), (.62, .300), (.75, .262), (.86, .222), (.95, .204), (.99, .190), (1.0, .160),
            (.996, .100), (.975, .056), (.80, .046), (.50, .044), (.20, .046)]
PAINT = [(.31, (246, 248, 252)), (.215, (208, 214, 224)), (.196, (168, 175, 188)), (.135, (206, 211, 220)),
         (.126, (122, 128, 142)), (.05, (62, 66, 78))]                                # high-tech silver, horizon reflection
EQE_S = dict(rim=(206, 210, 218), rim2=(120, 126, 136), n=10, cal=(40, 40, 46))
WR = .071                                                                             # wheel radius / L

def paint(d, pts, x0, ground, L, stops):
    """Fill pts with a multi-stop vertical gradient; stops are (v, colour) top to bottom."""
    m = Image.new('L', d.i.size, 0)
    ImageDraw.Draw(m).polygon([d.p(*q) for q in pts], fill=255)
    h, w = d.i.size[1], d.i.size[0]
    ys = np.array([d.p(0, ground - v * L)[1] for v, _ in stops])
    yy = np.arange(h)
    col = np.stack([np.interp(yy, ys, [c[i] for _, c in stops]) for i in range(3)], -1)
    d.i.paste(Image.fromarray(np.broadcast_to(col[:, None, :], (h, w, 3)).astype(np.uint8)), (0, 0), m)

def wheel(d, wx, wy, r, S, spin=0.0, blur=0.0):
    """Tyre, dark disc behind, ten-spoke AMG-style rim; when blur>0 the spokes smear into a disc."""
    d.ell(wx, wy, r, r, (22, 22, 26))
    d.ell(wx, wy, r * .96, r * .96, None, (40, 40, 46), max(2, r * .05))
    d.ell(wx, wy, r * .72, r * .72, (34, 36, 42))
    d.ell(wx, wy, r * .5, r * .5, (82, 84, 90))                                       # brake disc
    d.chord(wx, wy, r * .48, r * .48, 205, 285, S['cal'])
    rim, rim2 = S['rim'], S['rim2']
    for a in range(S['n']):
        ra = math.radians(a * 360 / S['n']) + spin
        for off, c in ((-.07, rim), (.07, rim2)):
            d.poly([(wx + r * .16 * math.cos(ra), wy + r * .16 * math.sin(ra)),
                    (wx + r * .70 * math.cos(ra + off), wy + r * .70 * math.sin(ra + off)),
                    (wx + r * .70 * math.cos(ra), wy + r * .70 * math.sin(ra))], c)
    d.ell(wx, wy, r * .72, r * .72, None, rim, max(2, r * .07))
    if blur > 0:
        d.ell(wx, wy, r * .70, r * .70, mix((34, 36, 42), (150, 154, 164), blur * .85))
        for k_ in (.3, .5):
            d.arc(wx, wy, r * k_, r * k_, 0, 360, mix((80, 84, 92), (196, 200, 208), blur), max(2, r * .04))
    d.ell(wx, wy, r * .17, r * .17, (40, 42, 48), rim, max(1, r * .03))
    mb_star(d, wx, wy, r * .0021, (214, 218, 226), ring=False)

def eqe(d, x0, ground, L, spin=0.0, blur=0.0):
    """EQE 350 4MATIC sedan side profile, front to the left. Returns the side-glass polygon."""
    def P(u, v): return (x0 + u * L, ground - v * L)
    sh = Image.new('L', d.i.size, 0)                                                  # soft contact shadow
    ImageDraw.Draw(sh).ellipse(d.box(x0 + .02 * L, ground - .018 * L, x0 + .98 * L, ground + .018 * L), fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(10 * d.k))
    d.i.paste(Image.new('RGBA', d.i.size, (8, 8, 12, 255)), (0, 0), sh)
    body = spline([P(u, v) for u, v in EQE_BODY], 8)
    paint(d, body, x0, ground, L, PAINT)
    # rocker panel and lower diffuser in satin black
    d.poly(spline([P(.24, .046), P(.74, .046), P(.745, .07), P(.24, .072)], 4), (30, 32, 38))
    d.poly([P(.905, .056), P(.972, .058), P(.98, .072), P(.91, .07)], (40, 42, 50))
    d.line(spline([P(.035, .176), P(.30, .205), P(.70, .202), P(.97, .192)], 8, closed=False), (252, 253, 255), 2)   # shoulder
    d.line(spline([P(.27, .102), P(.55, .108), P(.73, .112)], 6, closed=False), (232, 236, 242), 2)                 # lower crease
    # wheel arches
    for u in (.19, .80):
        wx, wy = P(u, WR)
        d.chord(wx, wy, L * WR * 1.13, L * WR * 1.13, 180, 360, (18, 18, 22))
    d.poly(body, None, (28, 30, 38), 3)
    # glasshouse: chrome surround, dark glass, black pillars
    dlo = spline([P(.292, .214), P(.375, .274), P(.50, .292), P(.62, .287), P(.735, .256), P(.805, .222), P(.79, .214),
                  P(.55, .211)], 6)
    d.poly(dlo, (196, 202, 212))
    gh = spline([P(.302, .217), P(.378, .269), P(.50, .286), P(.618, .281), P(.728, .252), P(.785, .222), P(.77, .217),
                 P(.55, .2145)], 6)
    paint(d, gh, x0, ground, L, [(.29, (70, 86, 108)), (.25, (34, 42, 56)), (.215, (16, 18, 26))])
    d.poly([P(.548, .214), P(.565, .214), P(.565, .285), P(.548, .286)], (16, 16, 20))   # B-pillar
    d.poly([P(.69, .217), P(.70, .217), P(.72, .262), P(.705, .266)], (16, 16, 20))     # rear quarter glass split
    d.poly([P(.33, .222), P(.345, .222), P(.40, .272), P(.385, .275)], (96, 114, 138))  # glint
    # doors, handles, mirror
    d.line([P(.305, .205), P(.300, .060)], (128, 134, 146), 2)
    d.line([P(.556, .205), P(.562, .056)], (128, 134, 146), 2)
    d.line(spline([P(.705, .205), P(.715, .15), P(.745, .12)], 4, closed=False), (128, 134, 146), 2)
    for u in (.455, .675):
        d.rect(*P(u, .184), *P(u + .045, .178), (236, 238, 242), r=2)
    d.poly(spline([P(.288, .218), P(.325, .226), P(.33, .246), P(.296, .244)], 4), (30, 32, 38), (20, 22, 28), 2)
    # front: black-panel grille with the star, slim headlamp with DRL, intake; rear: slim lamp
    d.poly(spline([P(.004, .118), P(.034, .126), P(.038, .168), P(.010, .160)], 3), (12, 12, 16), (70, 74, 84), 2)
    mb_star(d, *P(.020, .144), L * .00022, (236, 240, 246))
    d.poly(spline([P(.02, .168), P(.11, .192), P(.125, .186), P(.04, .162)], 3), (20, 22, 28), (40, 42, 50), 2)
    d.line([P(.035, .168), P(.115, .188)], (190, 230, 255), max(2, L * .004))
    d.poly([P(.02, .068), P(.085, .070), P(.08, .086), P(.012, .084)], (40, 42, 50))
    d.poly(spline([P(.925, .200), P(.995, .186), P(.998, .172), P(.93, .186)], 3), (208, 28, 36), (90, 10, 14), 2)
    d.text(*P(.93, .14), 'EQE 350', max(6, L * .014), (90, 96, 108), path=FONT_X)
    for u in (.19, .80):
        wheel(d, *P(u, WR), L * WR, EQE_S, spin, blur)
    return gh

def paste_rot(img, layer, cx, cy, rot=0.0, flip=False):
    if flip: layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
    if rot: layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(cx * K - layer.width / 2), int(cy * K - layer.height / 2)), layer)

@lru_cache(None)
def car_layer(L):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .62) * K), (0, 0, 0, 0))
    eqe(D(img, ox=-L * .1, oy=-L * .56), 0, 0, L)
    return img
def paste_car(img, x0, ground, L):
    c = car_layer(L)
    img.paste(c, (int((x0 - L * .1) * K), int((ground - L * .56) * K)), c)

# ================================================================ the oddity: a penguin pushing a lawn mower (never mentioned)
def penguin(d, x, fy, t, s=1.0, walking=True):
    """Penguin facing left, pushing a red push-mower ahead of it, grass clippings flying."""
    ph = t * 9 if walking else 0.0
    bob = abs(math.sin(ph)) * 4 * s
    mx = x - 92 * s                                                     # mower
    d.ell(mx - 30 * s, fy - 12 * s, 13 * s, 13 * s, (30, 30, 34)); d.ell(mx + 30 * s, fy - 12 * s, 13 * s, 13 * s, (30, 30, 34))
    d.rect(mx - 44 * s, fy - 44 * s, mx + 44 * s, fy - 16 * s, (214, 40, 40), r=8 * s, ol=(60, 16, 16), w=max(1, 3 * s))
    d.rect(mx - 14 * s, fy - 60 * s, mx + 14 * s, fy - 42 * s, (40, 40, 44), r=4 * s)
    d.line([(mx + 30 * s, fy - 40 * s), (x - 14 * s, fy - 96 * s - bob)], (60, 60, 66), max(2, 5 * s))    # handle
    if walking:
        for i in range(5):                                             # clippings
            k_ = (t * 2.3 + i * .21) % 1
            d.ell(mx - 50 * s - k_ * 70 * s, fy - 20 * s - math.sin(k_ * math.pi) * 40 * s + i * 3 * s, 3 * s, 2 * s, (80, 170, 60))
    for side in (-1, 1):                                               # feet
        fx = x + side * 12 * s + (math.sin(ph + (0 if side < 0 else math.pi)) * 8 * s if walking else 0)
        d.ell(fx - 6 * s, fy - 4 * s, 15 * s, 6 * s, (246, 160, 40))
    cy = fy - 58 * s - bob
    d.ell(x, cy, 34 * s, 54 * s, (24, 26, 34))
    d.ell(x - 9 * s, cy + 6 * s, 22 * s, 42 * s, (246, 246, 248))
    d.ell(x - 4 * s, cy - 54 * s, 24 * s, 24 * s, (24, 26, 34))
    d.ell(x - 14 * s, cy - 58 * s, 7 * s, 7 * s, (255, 255, 255)); d.ell(x - 16 * s, cy - 58 * s, 3.5 * s, 3.5 * s, (10, 10, 12))
    d.poly([(x - 24 * s, cy - 54 * s), (x - 42 * s, cy - 48 * s), (x - 24 * s, cy - 44 * s)], (246, 160, 40))
    d.line([(x - 18 * s, cy - 18 * s), (x - 14 * s, cy - 38 * s - 0 * s)], (24, 26, 34), max(2, 9 * s))        # flipper on the handle

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


# ================================================================ sets
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)


CEIL = 84
MB = dict(wall=((228, 230, 234), (246, 247, 249)), floor=((36, 38, 44), (74, 78, 88)), panel=(238, 240, 243),
          relief=(218, 220, 226), trim=EQ_BLUE, ceil=(30, 32, 36), name='M E R C E D E S - B E N Z', namecol=(28, 30, 36))

@lru_cache(None)
def bg_showroom():
    B = MB
    arr = np.concatenate([grad(WALL_Y * K, W * K, *B['wall']), grad((H - WALL_Y) * K, W * K, *B['floor'])])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-40, W, 170):                          # tall wall panels, flowing horizontal relief
        d.poly([(x + 8, 110), (x + 160, 110), (x + 160, WALL_Y - 40), (x + 8, WALL_Y - 40)], B['panel'])
        for yy in range(170, WALL_Y - 60, 90):
            d.line(spline([(x + 22, yy), (x + 84, yy - 14), (x + 146, yy)], 4, closed=False), B['relief'], 3)
    d.rect(0, 0, W, CEIL, B['ceil'])
    d.rect(0, CEIL - 6, W, CEIL, EQ_BLUE)                 # blue light strip
    for px in (150, 459, 768):                            # ring lights
        d.line([(px, CEIL), (px, CEIL + 34)], (70, 74, 78), 3)
        d.ell(px, CEIL + 52, 52, 14, None, (255, 252, 240), 6)
    d.rect(0, WALL_Y - 8, W, WALL_Y, EQ_BLUE)
    d.rect(0, WALL_Y, W, WALL_Y + 6, (14, 14, 16))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], tuple(min(255, c + 14) for c in B['floor'][1]), 2)
    img = spot(img, CX, 140, 70, 470, 800)
    d = D(img)
    mb_star(d, CX, 232, 1.15, (120, 126, 136), (84, 88, 98))
    d.text(CX, 336, B['name'], 34, B['namecol'], path=FONT_X)
    d.ell(CX, 905, 400, 50, (14, 16, 16))
    d.ell(CX, 897, 394, 44, (46, 46, 50), EQ_BLUE, 5)
    d.ell(CX, 897, 340, 34, (60, 60, 64))
    d.rect(842, 520, 1000, 640, (20, 22, 28), r=10)       # wall screen: the EQ badge
    d.text(921, 580, 'EQ', 64, EQ_BLUE)
    return img

# ---- scene 2: the road. The car stays centred; the world scrolls by and stops when the subscription runs out.
ROAD_L, ROAD_X0, ROAD_G = 840, CX - 420, 1590
V0 = 2600.0                                               # scroll speed, px/s, with the extra power
def pos(t):
    if t < T_EXP: return V0 * (t - T_S2)
    D_ = T_STOP - T_EXP; u = min(t - T_EXP, D_)
    return V0 * (T_EXP - T_S2) + V0 * (u - u * u / (2 * D_))
def speed(t):
    return V0 if t < T_EXP else V0 * max(0.0, 1 - (t - T_EXP) / (T_STOP - T_EXP))

@lru_cache(None)
def sky():
    img = Image.fromarray(np.concatenate([grad(1180 * K, W * K, (120, 176, 230), (250, 214, 176)),
                                          grad((H - 1180) * K, W * K, (70, 140, 70), (54, 110, 56))]).astype(np.uint8))
    d = D(img)
    for cx_, cy_, r_ in ((160, 300, 70), (240, 280, 90), (330, 310, 64), (760, 220, 80), (850, 200, 100), (940, 230, 70)):
        d.ell(cx_, cy_, r_ * 1.3, r_ * .7, (255, 255, 255, 220))
    return img

def strip(d, off, period, fn):
    """Draw a repeating background element so it scrolls with offset off (px)."""
    o = off % period
    for k_ in range(-1, int(W / period) + 2):
        fn(k_ * period + o - period, int((off - o) / period) - k_)

def road_world(t):
    img = sky().copy(); d = D(img)
    p = pos(t)
    def hill(x, i): d.ell(x + 200, 1180, 330, 200 + (i % 3) * 50, (126, 168, 120))
    strip(d, p * .08, 520, hill)
    def bld(x, i):                                        # town: buildings with windows
        hh = 300 + (i * 97) % 260; col = [(196, 186, 170), (172, 182, 196), (214, 200, 180), (160, 166, 176)][i % 4]
        d.rect(x, 1200 - hh, x + 210, 1200, col, ol=(90, 90, 100), w=3)
        for wy in range(1200 - hh + 30, 1180, 70):
            for wx in (x + 30, x + 90, x + 150):
                d.rect(wx, wy, wx + 34, wy + 40, (120, 150, 190))
    strip(d, p * .3, 260, bld)
    d.rect(0, 1200, W, 1250, (180, 178, 172))                                       # pavement
    def tree(x, i):
        d.rect(x + 46, 1080, x + 58, 1230, (110, 76, 50))
        d.ell(x + 52, 1060, 60, 70, [(70, 150, 70), (60, 130, 66)][i % 2], (40, 90, 40), 3)
    strip(d, p * .55, 380, tree)
    d.rect(0, 1250, W, 1268, (230, 230, 226))                                       # kerb
    d.rect(0, 1268, W, 1700, (64, 66, 72))                                          # road
    def dash(x, i): d.rect(x, 1462, x + 120, 1476, (240, 240, 236))
    strip(d, p, 260, dash)
    d.rect(0, 1700, W, 1716, (230, 230, 226))
    # the penguin mows the verge: it scrolls past while the car is fast, then overtakes once it has stalled
    PX = 900 - pos(T_STOP) * .55 + 110 * (T_STOP - T_S2)
    px = PX + p * .55 - 110 * (t - T_S2)
    if -200 < px < W + 200:
        penguin(D(img), px, 1236, t, .78)
    return img

def road_car(img, t, f):
    """EQE with the buyer at the wheel (seen through the glass), pitched and shaken by the stall."""
    L = ROAD_L
    lay = Image.new('RGBA', (int(L * 1.2) * K, int(L * .62) * K), (0, 0, 0, 0))
    ld = D(lay, ox=-L * .1, oy=-L * .56)
    sp = speed(t)
    gh = eqe(ld, 0, 0, L, spin=-pos(t) / (L * WR), blur=clamp(sp / 900 - .2))
    # buyer inside, masked to the glass
    s = .29
    jolt = 0.0
    for tj, amp in ((T_EXP, 1.0), (T_STOP - .05, 1.4)):
        if t >= tj: jolt += amp * math.exp(-(t - tj) * 5) * math.sin((t - tj) * 18)
    st = dict(lpose=POSES['up'], rpose=POSES['up'], out_lpose=True, out_rpose=True, look=-1,
              mouth=float(MOUTH['B'][min(f, len(MOUTH['B']) - 1)]) if MOUTH else 0.0)
    if t < T_EXP: st.update(brows='up', smile=1)                           # enjoying the extra power
    else: st.update(brows='worried', eyes='wide', sweat=t)
    st['blink'] = (t % 2.9) < .1
    X = L * .45 - 46 * max(0.0, jolt) + 10 * min(0.0, jolt)
    FY = -.248 * L + 905 * s + (math.sin(t * 40) * 2 if sp > 300 else 0) - 8 * abs(jolt)
    body = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    person(D(body, k=K * s, ox=(-L * .1 - X) / s, oy=FEET_Y - (FY + L * .56) / s), 0, FEET_Y, BUYER, st)
    m = Image.new('L', lay.size, 0)
    ImageDraw.Draw(m).polygon([ld.p(*q) for q in gh], fill=255)
    lay.paste(body, (0, 0), Image.fromarray(np.minimum(np.array(m), np.array(body.getchannel('A')))))
    tint = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(tint).polygon([ld.p(*q) for q in gh], fill=(120, 150, 190, 46))
    lay.alpha_composite(tint)                                                  # glass tint
    # pitch: nose dives on the expiry and the stall, rocks back
    rot = 0.0
    for tj, amp in ((T_EXP, 2.2), (T_STOP - .05, 3.2)):
        if t >= tj: rot -= amp * math.exp(-(t - tj) * 4) * math.sin((t - tj) * 11 + .4)
    vib = math.sin(t * 47) * 2 if sp > 300 else 0
    paste_rot(img, lay, ROAD_X0 + L * .5, ROAD_G - L * .25 + vib, rot)
    d = D(img)
    if t >= T_STOP - .1:                                                       # sad puffs from under the car
        for i in range(4):
            k_ = prog(t, T_STOP - .1 + i * .12, .9)
            if 0 < k_ < 1:
                d.ell(ROAD_X0 + L * (.55 + .12 * i) + 40 * k_, ROAD_G - 20 - 90 * k_, 30 + 50 * k_, 22 + 36 * k_,
                      (200, 200, 204, int(200 * (1 - k_))))

# ---- scene 3: the online store on a big wall screen
@lru_cache(None)
def bg_store():
    img = Image.fromarray(np.concatenate([grad(WALL_Y * K, W * K, (30, 34, 44), (52, 58, 72)),
                                          grad((H - WALL_Y) * K, W * K, (60, 62, 70), (92, 96, 104))]).astype(np.uint8))
    d = D(img)
    d.rect(34, 120, 884, 890, (12, 12, 16), r=24)                             # screen bezel
    d.rect(50, 136, 868, 874, (246, 247, 249), r=14)
    d.rect(50, 136, 868, 212, (16, 18, 22), r=14); d.rect(50, 190, 868, 212, (16, 18, 22))
    mb_star(d, 100, 174, .38, (230, 234, 240))
    d.text(140, 174, 'ONLINE STORE', 34, (240, 242, 246), anchor='lm', path=FONT_X)
    d.rect(86, 240, 832, 520, (232, 234, 238), r=14)                          # product image: the EQE
    eqe(d, 180, 500, 560)
    d.text(86, 572, 'Acceleration Increase', 46, (20, 22, 28), anchor='lm')
    d.text(86, 628, 'EQE 350 4MATIC: 288 hp to 349 hp', 32, (90, 94, 104), anchor='lm', path=FONT_X)
    d.text(86, 690, '$1,200/year', 56, (20, 22, 28), anchor='lm')
    d.text(426, 694, '(plus tax)', 30, (110, 114, 124), anchor='lm', path=FONT_X)
    d.rect(86, 748, 832, 836, EQ_BLUE, r=14)
    d.text(459, 792, 'BUY', 48, (255, 255, 255))
    d.rect(0, WALL_Y, W, WALL_Y + 8, (14, 14, 18))
    return img

# ================================================================ characters (tesla-locked cast)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('e9b48e'), skin2=hexc('cf9670'), hair=hexc('b9bcc4'), suit=hexc('5a606c'), suit2=hexc('41464f'),
             shirt=hexc('f7f7fa'), tie=hexc('00a8e2'), pants=hexc('4a4f58'), shoe=hexc('1e1e22'), glasses=False, hairstyle='bald',
             lids=0.55, mustache=True, badge=True)            # new salesman: grey suit, silver fringe, moustache, EQ-blue tie
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
        mb_star(d, x + 73, top + 105, 0.17, (60, 64, 72))
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
    elif c['hairstyle'] == 'bald':                        # silver fringe round the sides, shiny dome
        for s_ in (-1, 1):
            d.chord(hx + s_ * 52, hy - 18, 24, 40, 90 if s_ > 0 else 180, 270 if s_ > 0 else 360, c['hair'])
            d.chord(hx + s_ * 56, hy - 8, 18, 34, 0, 360, c['hair'])
        d.ell(hx - 24, hy - 58, 16, 9, (255, 255, 255, 110))
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
        d.line([(ex - s * 14, ey + inner), (ex + s * 14, ey + outer)], c['hair'] if c['hairstyle'] in ('messy', 'bald') else c['skin2'], 6)
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
    if c.get('mustache'):
        d.poly(spline([(hx - 30, my_ - 4), (hx - 8, my_ - 16), (hx, my_ - 12), (hx + 8, my_ - 16), (hx + 30, my_ - 4),
                       (hx + 10, my_ - 8), (hx - 10, my_ - 8)], 4), c['hair'], OL, 2)
    if st.get('frazzled'):                                 # after the stall: hair blown up, soot on the cheeks
        for px_ in (-60, -30, 0, 30, 60):
            d.poly([(hx + px_ - 14, hy - 80), (hx + px_ * 1.5, hy - 150 - abs(px_) * .3), (hx + px_ + 14, hy - 80)], c['hair'])
        for s_ in (-1, 1):
            d.ell(hx + s_ * 40, hy + 26, 16, 9, (60, 60, 64, 140))
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
    A, Wd = dict(brows='angry', eyes='wide'), dict(brows='angry', eyes='wide', sweat=1)
    return [(0.0, 'rest', 'hip', dict(brows='up', smile=1)),                 # proud owner, strolling in
            (T_WHAT - .08, 'up', 'up', dict(brows='up', eyes='wide')),       # jumps
            (LE[1] + .2, 'rest', 'rest', dict(brows='angry')),
            (T_288 - .05, 'chin', 'rest', dict(brows='worried')),
            (T_349 - .05, 'point', 'point', A),
            (T_1200 - .05, 'head', 'head', Wd),
            # online store
            (T_S3, 'rest', 'rest', dict(brows='angry', sweat=1)),
            (T_NOV - .05, 'point', 'rest', Wd),
            (T_NOBODY - .05, 'up', 'up', dict(brows='up', eyes='wide', sweat=1)),
            (T_BUY + .05, 'head', 'head', dict(brows='worried', eyes='wide', sweat=1)),
            # showroom: wrecked
            (T_S4, 'rest', 'rest', dict(brows='worried', tired=0.4, sweat=1)),
            (T_TECH, 'shrug', 'shrug', dict(brows='angry', tired=0.2)),
            (T_OVER + .1, 'cross', 'cross', dict(brows='angry', smile=-1)),
            (T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide'))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {0: 'open', 2: 'present', 3: 'offer', 5: 'present', 6: 'open', 7: 'open'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
    s += [(T_FINAL, 'open', 'clasp', dict(look=0)), (LE[8] + .3, 'clasp', 'clasp', dict(look=0))]
    return sorted(s, key=lambda e: e[0])

BS, SS_ = buyer_sched(), sales_sched()
HOPS = {'B': [(T_WHAT - .05, 70), (T_NOBODY, 40)], 'S': []}                 # physical jumps
def hop(who, t):
    return sum(-a * math.sin(math.pi * prog(t, t0, .38)) for t0, a in HOPS[who] if t0 <= t < t0 + .38)

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
def stand(img, t, sc, f):
    d = D(img)
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.1), 120, 11           # already in shot, strolling up to the car
    elif sc == 3:
        walk_k, bx0, dur_w = prog(t, t_in, .9), 20, 6           # limps back in
    else:
        walk_k, bx0, dur_w = prog(t, t_in, .6), -80, 14         # storming after the salesman
    bx = bx0 + (270 - bx0) * oc(walk_k)
    if sc == 2 and t >= T_BUY:                                  # staggers back on 'buy it'
        bx -= 70 * oc(prog(t, T_BUY, .35))
    for who, x, sched, cfg in (('S', 670, SS_, SALES), ('B', bx, BS, BUYER)):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[who][min(f, len(MOUTH[who]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        st['dy'] = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3 + (-4 if talking(who, t) and (f // 4) % 2 else 0) + hop(who, t)
        if who == 'B' and walk_k < 1:
            st['walk'] = t * dur_w
            st['dy'] -= abs(math.sin(t * dur_w)) * (5 if sc == 3 else 10)
        if who == 'B' and sc == 3:
            st['frazzled'] = 1
        if st.get('sweat'):
            st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)

def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    f = int(round(t * FPS))
    if sc in (0, 3):
        img = bg_showroom().copy()
        reception(img, t, sc == 0)
        penguin(D(img), 1010 - 70 * (t - SCENES[sc]) - (0 if sc == 0 else 260), 932, t, .5)
        paste_car(img, CX - 345, 900, 690)
    elif sc == 1:
        img = road_world(t); road_car(img, t, f)
        return img
    else:
        img = bg_store().copy()
    stand(img, t, sc, f)
    return img

def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0 and t < T_CLOSE:
        z = 1.08 - 0.05 * oc(prog(t, 0, 1.6))
        sx = -30 + 30 * io(prog(t, 0, 2.5))                # slow drift so frame 1 is already moving
        punches = ((T_WHAT, .07),)
    elif sc == 0:                                          # closer on the car
        z = 1.2 + 0.04 * io(prog(t, T_CLOSE, 4))
        sx = -40
        punches = ((T_CLOSE, .05), (T_349, .04), (T_1200, .05))
    elif sc == 1:                                          # road: chase cam, then creep in on the stalled driver
        z = 1.02 + 0.14 * io(prog(t, T_STOP - .2, 1.0))
        sy = 110 * io(prog(t, T_STOP - .2, 1.0)); sx = -60 * io(prog(t, T_STOP - .2, 1.0))
        punches = ((T_EXP, .05),)
        if speed(t) > 300: sx += math.sin(t * 53) * 3; sy += math.sin(t * 41) * 3
    elif sc == 2:
        z = 1.04 + 0.03 * io(prog(t, t0, 4))
        sx = 46 * (1 - oc(prog(t, t0, 1.2)))
        punches = ((T_NOV, .04), (T_NOBODY, .05), (T_BUY, .06))
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_OVER, .05), (T_FINAL, .05))
        pk = io(prog(t, T_FINAL - .05, .5))                # salesman turns to camera: push in on him
        z += 0.14 * pk
        sx = 150 * pk
    for tj, amp in (((T_EXP, 18), (T_STOP - .05, 26)) if sc == 1 else ((T_WHAT, 12), (T_BUY, 12))):
        if tj <= t < tj + .6:                              # handheld jolt
            k_ = 1 - prog(t, tj, .6)
            sx += amp * k_ * math.sin(t * 61); sy += amp * .7 * k_ * math.sin(t * 47 + 1)
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
CHIPS1 = [('YOU PAID FOR', '288 HP', GREEN, 'T_288'), ('THE MOTORS CAN MAKE', '349 HP', RED, 'T_349')]
CARD3 = (("Mercedes spokesperson", 46, INK2), ("to The Drive, April 2023:", 46, INK2),
         ("no one was allowed", 60, DRED), ("to buy it.", 60, DRED))
FINAL = [("Would you pay", 74, TAG), ("$1,200 a year", 84, TAG), ("for 0.9 seconds?", 74, TAG),
         ("Yes, or no?", 80, (255, 255, 255)), ("Comment below.", 60, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 440, 112
HUD_ON, HUD_OFF = ('ACCELERATION INCREASE', 'ACTIVE'), ('SUBSCRIPTION', 'EXPIRED')
ONSCREEN = (['M E R C E D E S - B E N Z', 'EQ', 'ONLINE STORE', 'Acceleration Increase', 'EQE 350 4MATIC: 288 hp to 349 hp',
             '$1,200/year', '(plus tax)', 'BUY', 'ACCELERATION INCREASE', '$1,200/year', '349 HP', '288 HP', '0-60 5.1 s',
             '0-60 6.0 s', 'LISTED NOV 2022', 'NOT FOR SALE', '$0.00', 'TOTAL CHARGED', *HUD_ON, *HUD_OFF]
            + [x for r in CHIPS1 for x in r[:2]] + [r[0] for r in CARD3] + [f[0] for f in FINAL])

def chip_rows(d, t, rows, y0, a):
    al = int(255 * a)
    for i, (lab, chip, col, tn) in enumerate(rows):
        t_lab = globals()[tn]
        if t < t_lab - .05: continue
        ra = min(a, prog(t, t_lab - .05, .2))
        k_ = popin(t, t_lab - .05, .3)
        w_ = font(40 * K).getlength(chip) / K
        y = y0 + i * 96
        d.text(110, y, lab, 34, (220, 224, 234, int(255 * ra)), anchor='lm', path=FONT_X)
        d.rect(800 - (w_ + 40) * k_, y - 34, 800, y + 34, col + (al,), r=14)
        if k_ > .6: d.text(800 - (w_ + 40) / 2, y + 1, chip, 40, (255, 255, 255, al))
    if t >= T_349 + .15:                                    # the gap between them is locked
        k_ = popin(t, T_349 + .15, .3)
        lx, ly = 470, y0 + 48
        d.arc(lx, ly - 12 * k_, 12 * k_, 14 * k_, 180, 360, (240, 240, 244, al), 5)
        d.rect(lx - 17 * k_, ly - 12 * k_, lx + 17 * k_, ly + 14 * k_, (230, 40, 50, al), r=4, ol=(255, 255, 255, al), w=2)

def hud(img, t):
    """Road HUD: power gauge, 0-60 time and the subscription chip; flips when it expires."""
    a = window(t, T_S2 + .15, T_S3 + .05, .15, .2)
    if a <= 0: return False
    d = D(img); al = int(255 * a)
    panel(d, 70, 150, 848, 560, a)
    exp_k = prog(t, T_EXP, .5)
    hp = 349 - 61 * io(exp_k)
    cx_, cy_, R = 250, 400, 150                             # gauge
    d.arc(cx_, cy_, R, R, 160, 380, (70, 74, 84, al), 18)
    d.arc(cx_, cy_, R, R, 160, 160 + 220 * 288 / 349, (70, 200, 120, al), 18)
    if hp > 289: d.arc(cx_, cy_, R, R, 160 + 220 * 288 / 349, 160 + 220 * hp / 349, (255, 214, 64, al), 18)
    ang = math.radians(160 + 220 * hp / 349 + (math.sin(t * 40) * 1.5 if t < T_EXP else 0))
    d.line([(cx_, cy_), (cx_ + (R - 30) * math.cos(ang), cy_ + (R - 30) * math.sin(ang))], (240, 60, 60, al), 8)
    d.ell(cx_, cy_, 14, 14, (240, 242, 246, al))
    d.text(cx_, cy_ + 70, '349 HP' if t < T_EXP + .25 else '288 HP', 50, (255, 255, 255, al))
    d.text(620, 250, (HUD_ON if t < T_EXP else HUD_OFF)[0], 30, (210, 214, 224, al), path=FONT_X)
    on = t < T_EXP
    col = GREEN if on else RED
    k_ = 1.0 if on else popin(t, T_EXP, .3)
    d.rect(620 - 130 * k_, 290, 620 + 130 * k_, 360, col + (al,), r=16)
    if k_ > .6: d.text(620, 326, (HUD_ON if on else HUD_OFF)[1], 40, (255, 255, 255, al))
    d.text(620, 450, '0-60 5.1 s' if t < T_EXP + .25 else '0-60 6.0 s', 56,
           ((255, 255, 255) if on else (255, 120, 120)) + (al,))
    return True

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        ca = window(t, T_288 - .1, T_1200 + .1, .15, .2)        # (after the 3 s hook) what you paid for vs the motors
        if ca > 0:
            used = True
            panel(d, 70, 250, 848, 540, ca)
            chip_rows(d, t, CHIPS1, 336, ca)
        ta = window(t, T_1200 - .05, T_S2 + .05, .1, .2)
        if ta > 0:
            used = True
            sw = math.sin((t - T_1200) * 6) * 4 * math.exp(-(t - T_1200) * 2)
            put(img, price_tag('$1,200/year', 'ACCELERATION INCREASE', TAG, 600), CX, 420, popin(t, T_1200 - .05, .35) * .95, ta,
                rot=sw - 3)
    elif sc == 1:
        used = hud(img, t)
    elif sc == 2:
        if t >= T_NOV - .05:                                   # stamp on the store listing
            used = True
            a = window(t, T_NOV - .05, T_S4 + .05, .05, .2)
            put(img, stamp_img('LISTED NOV 2022', (226, 48, 58), 46), 640, 290, popin(t, T_NOV - .05, .3), a, rot=-8)
        if t >= T_BUY - .1:                                    # nobody was allowed to buy it
            used = True
            a = window(t, T_BUY - .1, T_S4 + .05, .05, .2)
            put(img, stamp_img('NOT FOR SALE', (226, 48, 58), 70), 470, 792, 1.6 - .6 * oc(prog(t, T_BUY - .1, .25)), a, rot=6)
        ca = window(t, T_DRIVE - .1, T_S4 + .05, .12, .2)
        if ca > 0:
            used = True
            put(img, info_card(CARD3, 720), CX, 520, popin(t, T_DRIVE - .1, .35), ca, rot=-1.5)
    else:
        ra = window(t, T_OVER - .05, T_FINAL - .1, .1, .2)
        if ra > 0:                                             # the receipt
            used = True
            put(img, price_tag('$0.00', 'TOTAL CHARGED', (250, 250, 248), 520), CX, 560, popin(t, T_OVER - .05, .35), ra, rot=4)
    if t >= T_CARD:                                            # final question
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(FINAL):
            k_ = popin(t, T_CARD + .06 * i, .25)
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
def load_music(n, SR):
    """User's background track, mono float, level-matched; a tape-stop when the subscription expires, back at the store."""
    if not os.path.exists(MUSIC): return np.zeros(n)
    m = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', MUSIC, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    m = m / (np.sqrt(np.mean(m[:SR * 30] ** 2)) + 1e-9) * 0.055
    T_ = np.arange(n) / SR
    rate = np.ones(n)
    a, b = int(T_EXP * SR), int(T_S3 * SR)
    rate[a:b] = np.clip(1 - (T_[a:b] - T_EXP) / 0.75, 0, 1) ** 1.5
    p = np.cumsum(rate) / SR
    p[b:] = T_[b:]                                          # resumes in place at the next scene
    out = np.interp(p * SR, np.arange(len(m)), m, right=0.0)
    out[a:b] *= np.clip(rate[a:b] * 3, 0, 1)
    return out

def build_audio(voice, out_wav):
    SR = sfx.SR
    v = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rng = np.random.default_rng(3); T_ = np.arange(n) / SR
    def lpf(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
    # music bed ducked under the dialogue
    venv = lpf(np.abs(v), int(SR * .12)); venv = np.clip(venv / (venv.max() + 1e-9) * 6, 0, 1)
    duck = 1 - .55 * lpf(venv, int(SR * .2))
    music = load_music(n, SR) * duck
    # road: EV motor whine follows the speed, tyre roar, then silence
    sp = np.array([speed(t) / V0 if SCENES[1] <= t < SCENES[2] else 0.0 for t in T_])
    sp = lpf(sp, int(SR * .03))
    ph = np.cumsum(2 * np.pi * (180 + 520 * sp) / SR)
    whine = (np.sin(ph) * .5 + np.sin(ph * 2.01) * .25) * sp * .05
    roar = lpf(rng.standard_normal(n), 30) * sp * .12
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def tick(): return click(4200, 5200, .03) * .5
    def power_down(d=0.9):
        tt = np.arange(int(SR * d)) / SR; f = 520 * np.exp(-tt * 3.2) + 30
        return np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-tt * 1.5) * np.minimum(1, (d - tt) * 20)
    def mower(d):
        tt = np.arange(int(SR * d)) / SR
        s = ((tt * 62) % 1 * 2 - 1) * (1 + .3 * np.sin(2 * np.pi * 9 * tt))
        return lpf(s, 8) * np.minimum(1, tt * 4) * np.minimum(1, (d - tt) * 6)
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    for k_ in range(3): add(0.05 + k_ * 0.36, step(), .45)
    add(T_WHAT - .05, sfx.boom(.5), .35); add(T_WHAT, sfx.pop(), .3)
    add(T_CLOSE, sfx.whoosh(.3, 14), .3)
    add(T_288 - .05, sfx.pop(), .35); add(T_288, sfx.ding(1320, .5), .14)
    add(T_349 - .05, sfx.pop(), .35); add(T_349 + .2, click(900, 1400, .08), .7)
    add(T_1200 - .05, sfx.pop(), .3); add(T_1200 + .3, sfx.cha_ching(), .35)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    add(T_S2 - .05, sfx.vroom(), .35)
    add(T_EXP - .03, sfx.buzzer(), .4); add(T_EXP, power_down(), .3); add(T_EXP + .05, sfx.thump(.2), .4)
    add(T_STOP - .05, sfx.thump(), .5); add(T_STOP, sfx.poof(), .35)
    add(T_STOP + .1, mower(T_S3 - T_STOP - .1), .05)
    for k_ in range(3): add(T_S3 + .05 + k_ * .2, step(), .35)
    add(T_NOV - .05, sfx.stamp(), .35)
    add(T_DRIVE - .1, sfx.pop(), .3)
    add(T_BUY - .1, sfx.stamp(), .4); add(T_BUY, sfx.buzzer(.3), .25)
    for k_ in range(3): add(T_S4 + .05 + k_ * .4, step(), .3)
    add(T_OVER - .05, sfx.pop(), .3); add(T_OVER + .15, sfx.ding(1760), .16)
    for k_ in range(2): add(BEAT[0] + .1 + k_ * .25, tick(), .6)
    add(T_CARD, sfx.pop(), .35); add(T_CARD + .1, sfx.ding(1568, .9), .15)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s
    mixd = v * 1.0 + fxa[:n] * 0.55 + music + whine + roar
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
