"""Tesla 'locked battery' showroom skit. Flat-vector style, 1080x1920 @30.
Usage: python render.py video VOICE.wav OUT.mp4   |   python render.py still T OUT.png"""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sfx

W, H, FPS, K = 1080, 1920, 30, 2          # K = supersample factor for drawing
CX = 459                                   # composition centre (left 85% of width)
DUR = 43.0
WALL_Y, FEET_Y = 940, 1880
WORDS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'words.json')))
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'

# ---- timeline derived from word timings (never hand-typed seconds for speech)
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt):
    for w in LINES[line]:
        if txt.lower() in w['w'].lower():
            return w['s']
    raise KeyError(txt)
CARD0 = LE[9] + 0.15                       # time card: after "No way."
CARD1 = LS[10] - 0.05
BEAT1 = (LE[11], LS[12])                   # silence beat 1
BEAT2 = (LE[17], LS[18])                   # silence beat 2
T_SIXTY, T_75 = word_t(2, 'sixty'), word_t(2, 'seventy')
T_LOCK, T_FOUR, T_DOLL = word_t(4, 'Locked'), word_t(6, 'Four'), word_t(6, 'dollars')
T_DONE, T_FREE = word_t(12, 'Done'), word_t(12, 'Free')
T_MY75 = word_t(13, 'seventy')
T_16 = word_t(16, 'sixteenth')
T_LOCK2 = LS[18]
STORM0, STORM1 = CARD0, LS[14]

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
        self.d.polygon(P, fill=fill)
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
    rng_ = range(m) if closed else range(m - 1)
    for i in rng_:
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        if not closed:
            p0 = P[max(i - 1, 0)]; p3 = P[min(i + 2, m - 1)]
        for j in range(n):
            t = j / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    return out

# ================================================================ static set
TESLA_RED = (204, 0, 0)
def tesla_logo(d, cx, cy, s=1.0, col=TESLA_RED):
    """Tesla 'T' emblem: arched cap with a gap, shield-shaped stem."""
    up, lo = [], []
    for i in range(41):
        x = -1 + i / 20
        up.append((cx + x * 112 * s, cy + (-78 + 22 * x * x) * s))
        lo.append((cx + x * 112 * s, cy + (-56 + 16 * x * x - 6 * (1 - x * x)) * s))
    d.poly(spline(up[::4] + lo[::-4], 6), col)
    stem = [(-40, -48), (-22, -36), (-12, -40), (-14, 0), (-8, 70), (0, 96), (8, 70), (14, 0), (12, -40), (22, -36), (40, -48), (0, -50)]
    d.poly(spline([(cx + x * s, cy + y * s) for x, y in stem], 6), col)

def model_s(d, x0, ground, L=760, col='red', badge='60', glow=0.0):
    Hh = L / 3.45
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    body_c = {'red': ((178, 18, 27), (222, 52, 60), (120, 10, 16))}[col]
    ctrl = [(0.0, .25), (.004, .40), (.05, .48), (.17, .53), (.31, .58), (.44, .87), (.56, .91), (.67, .86),
            (.81, .70), (.93, .59), (.99, .55), (1.0, .44), (.993, .27), (.96, .17), (.86, .15), (.70, .16),
            (.30, .16), (.12, .15), (.03, .17)]
    body = spline([P(u, v) for u, v in ctrl], 8)
    d.poly(body, body_c[0], (40, 10, 14), 5)
    # lower shade + shoulder highlight
    d.poly(spline([P(.03, .19), P(.5, .18), P(.97, .19), P(.99, .30), P(.5, .29), P(.01, .30)], 6), body_c[2])
    d.line(spline([P(.06, .47), P(.30, .55), P(.62, .60), P(.92, .56)], 8, closed=False), body_c[1], 5)
    # greenhouse
    gh = spline([P(.33, .60), P(.445, .83), P(.56, .865), P(.665, .82), P(.775, .66), P(.75, .605)], 6)
    d.poly(gh, (28, 36, 48), (20, 20, 26), 4)
    d.poly([P(.52, .61), P(.535, .61), P(.545, .86), P(.53, .86)], (20, 20, 26))
    d.line([P(.40, .76), P(.47, .84)], (120, 140, 165), 5)   # glass glint
    # door seams, handles, lights
    for u in (.335, .53, .74):
        d.line([P(u, .58), P(u - .006, .22)], (110, 12, 18), 3)
    for u in (.44, .64):
        d.rect(*P(u, .50), *P(u + .05, .48), (230, 230, 235), r=3)
    d.poly(spline([P(.005, .41), P(.07, .45), P(.09, .43), P(.01, .38)], 4), (245, 248, 255))
    d.poly([P(.955, .53), P(.995, .51), P(.996, .47), P(.95, .49)], (255, 70, 70))
    # badge on trunk
    bx, by = P(.885, .50)
    if glow > 0:
        d.ell(bx, by, 60 + 30 * glow, 40 + 20 * glow, (255, 230, 120, int(150 * glow)))
    d.rect(bx - 40, by - 22, bx + 40, by + 22, (232, 234, 238), r=8, ol=(60, 60, 70), w=3)
    d.text(bx, by + 1, badge, 30, (30, 30, 36))
    # wheels
    for u in (.19, .785):
        wx, wy = P(u, 0)[0], ground - 58
        d.ell(wx, wy, 60, 60, (24, 24, 28))
        d.ell(wx, wy, 40, 40, (176, 180, 190), (90, 92, 100), 3)
        for a in range(5):
            r = math.radians(a * 72 + 18)
            d.line([(wx, wy), (wx + 36 * math.cos(r), wy + 36 * math.sin(r))], (110, 112, 122), 7)
        d.ell(wx, wy, 9, 9, TESLA_RED)

@lru_cache(None)
def background():
    img = Image.new('RGB', (W * K, H * K))
    a = np.linspace(0, 1, WALL_Y * K)[:, None, None]
    wall = (np.array([22, 24, 30]) * (1 - a) + np.array([44, 48, 56]) * a)
    b = np.linspace(0, 1, (H - WALL_Y) * K)[:, None, None]
    floor = (np.array([206, 209, 215]) * (1 - b) + np.array([236, 238, 241]) * b)
    arr = np.concatenate([np.broadcast_to(wall, (WALL_Y * K, W * K, 3)), np.broadcast_to(floor, ((H - WALL_Y) * K, W * K, 3))])
    img = Image.fromarray(arr.astype(np.uint8))
    d = D(img)
    for x in range(-60, W, 150):                      # wall panels
        d.line([(x, 0), (x, WALL_Y - 4)], (54, 58, 66), 2)
    d.rect(0, WALL_Y - 8, W, WALL_Y, (190, 196, 205))
    d.rect(0, WALL_Y, W, WALL_Y + 6, TESLA_RED)
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):  # floor tiles
        d.line([(0, y + i * 12), (W, y + i * 12)], (220, 223, 228), 2)
    # spotlight cone (blurred)
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(CX - 70, 0), (CX + 70, 0), (CX + 470, 900), (CX - 470, 900)]], fill=60)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    img = Image.composite(Image.new('RGB', img.size, (255, 255, 255)), img, cone)
    d = D(img)
    tesla_logo(d, CX, 190, 1.0)
    d.text(CX, 318, 'T E S L A', 46, (235, 236, 240), path=FONT_X)
    # turntable + car
    d.ell(CX, 905, 420, 52, (16, 16, 20))
    d.ell(CX, 897, 414, 46, (52, 56, 64), TESLA_RED, 5)
    d.ell(CX, 897, 360, 36, (64, 68, 78))
    return img

@lru_cache(None)
def car_layer(badge, glow10):
    img = Image.new('RGBA', (900 * K, 300 * K), (0, 0, 0, 0))
    model_s(D(img, ox=CX - 450, oy=600), CX - 380, 890, badge=badge, glow=glow10 / 10)
    return img

# ================================================================ characters
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('1c1d22'), suit2=hexc('0e0f12'),
             shirt=hexc('f7f7fa'), tie=hexc('111114'), pants=hexc('1c1d22'), shoe=hexc('3a2a22'), glasses=False, hairstyle='part', lids=0.45)
OL = (26, 26, 46)
POSES = {'rest': (10, 323), 'clasp': (-100, 286), 'open': (120, 170), 'point': (235, 70), 'up': (70, -290),
         'head': (-92, -158), 'phone': (-46, -128), 'shrug': (128, 108), 'cross': (-176, 168), 'tablet': (-70, 150),
         'thanks': (-100, 92), 'raise1': (40, -230)}
UA, FA = 168, 158

OUTBEND = {'up', 'head', 'raise1', 'phone'}
def ik(S, T, side, out=False):
    dx, dy = T[0] - S[0], T[1] - S[1]
    d_ = max(1e-3, min(math.hypot(dx, dy), UA + FA - 2))
    a = (UA * UA + d_ * d_ - FA * FA) / (2 * d_)        # distance from shoulder to elbow foot
    h = math.sqrt(max(0, UA * UA - (a * a)))
    mx, my = S[0] + dx / d_ * a, S[1] + dy / d_ * a
    px, py = -dy / d_, dx / d_
    if (out and px * side < 0) or (not out and py < 0):
        px, py = -px, -py
    return (mx + px * h, my + py * h), (S[0] + dx / d_ * d_, S[1] + dy / d_ * d_)

def person(d, x, fy, c, st):
    """st: lpose,rpose (ox,oy targets) ; mouth 0..1 ; blink ; brows ; eyes ; smile ; walk ; dy ; look ; sweat ; prop."""
    dy, walk = st.get('dy', 0), st.get('walk', None)
    # legs + shoes
    for side in (-1, 1):
        sw = 0 if walk is None else math.sin(walk + (0 if side < 0 else math.pi)) * 26
        lift = 0 if walk is None else max(0, math.sin(walk + (0 if side < 0 else math.pi))) * 14
        hx_, kx = x + side * 40, x + side * 40 + sw
        d.poly([(hx_ - 38, fy - 470 + dy), (hx_ + 38, fy - 470 + dy), (kx + 36, fy - 26 - lift), (kx - 36, fy - 26 - lift)], c['pants'], OL, 4)
        d.ell(kx + side * 12, fy - 16 - lift, 50, 20, c['shoe'], OL, 4)
    top = fy - 800 + dy
    # torso (jacket)
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
    if not c['glasses']:                                  # Tesla name badge
        d.rect(x + 50, top + 92, x + 96, top + 118, (245, 245, 248), r=4)
        tesla_logo(d, x + 73, top + 104, 0.1)
    # neck + head
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
    # eyes
    ey, look = hy - 2, st.get('look', 0)
    wide = 1.25 if st.get('eyes') == 'wide' else 1.0
    lids = c['lids'] if st.get('eyes') != 'wide' else 0.0
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
    # brows
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
    # mouth
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
    # arms (in front of torso)
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
            d.rect(hx2 - 12, hy2 - 46, hx2 + 12, hy2 + 12, (24, 24, 28), r=6, ol=(90, 90, 100), w=3)
        elif prop == 'tablet':
            d.rect(hx2 - 70, hy2 - 92, hx2 + 40, hy2 + 4, (24, 24, 28), r=10, ol=(90, 90, 100), w=3)
            g = st.get('tablet_glow', 0)
            d.rect(hx2 - 62, hy2 - 84, hx2 + 32, hy2 - 4, mix((40, 60, 90), (80, 220, 120), g), r=6)

# ---- performance schedules: (time, left pose, right pose, extras)
def buyer_sched():
    return [(0.0, 'rest', 'rest', dict(brows='flat')),
            (LS[1] - .1, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (LS[2] + .3, 'rest', 'rest', dict(brows='up')),
            (LS[3] - .1, 'rest', 'open', dict(brows='up')),
            (LS[5] - .1, 'rest', 'point', dict(brows='angry')),
            (LS[7] - .1, 'up', 'up', dict(brows='angry', eyes='wide')),
            (LS[9] - .1, 'cross', 'cross', dict(brows='angry', smile=-1)),
            (CARD1 - .2, 'raise1', 'phone', dict(brows='worried', eyes='wide', sweat=1, prop={'rpose': 'phone'})),
            (LE[10] + .2, 'rest', 'phone', dict(brows='worried', eyes='wide', sweat=1, prop={'rpose': 'phone'})),
            (T_DONE + .3, 'rest', 'phone', dict(brows='up', eyes='wide', prop={'rpose': 'phone'})),
            (LS[13] - .1, 'up', 'up', dict(brows='up', eyes='wide', smile=1)),
            (LS[15] - .1, 'thanks', 'thanks', dict(brows='up', smile=1)),
            (LS[17] - .1, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (T_LOCK2 + .15, 'head', 'head', dict(brows='worried', eyes='wide', smile=-1))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    for ln in (0, 2, 6, 12, 14):
        s += [(LS[ln] + .05, 'open', 'clasp', {}), (LE[ln] - .1, 'clasp', 'clasp', {})]
    s += [(T_LOCK - .05, 'clasp', 'raise1', {}), (LE[4], 'clasp', 'clasp', {})]
    s += [(LS[10] + 1.0, 'clasp', 'phone', dict(prop={'rpose': 'phone'})),
          (BEAT1[0] + .05, 'tablet', 'tablet', dict(prop={'lpose': 'tablet'}, tglow=1)),
          (LS[12] + .9, 'open', 'clasp', {}), (LE[12], 'clasp', 'clasp', {}),
          (T_16 - .2, 'clasp', 'raise1', {}), (LE[16], 'clasp', 'clasp', {})]
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
    for k_ in M:   # flap a little so held vowels still move
        f = np.arange(n)
        M[k_] = M[k_] * (0.75 + 0.25 * np.abs(np.sin(f * 1.9)))
    MOUTH = M

def talking(spk, t):
    return any(w['spk'] == spk and w['s'] - .05 <= t <= w['e'] + .05 for w in WORDS)

# ================================================================ overlays (drawn on 1x-coord, K supersampled RGBA)
GREEN, GREY, LOCKRED = (64, 200, 110), (92, 96, 106), (226, 48, 58)
def battery(d, t, a, cells_on, lock_state, lock_t, lock_k, unlock_k):
    """5 cells x 15 kWh; cells_on=4 or 5. lock_state: None | 'locked' | 'opening'."""
    x0, x1, y0, y1 = 112, 772, 392, 520
    al = int(255 * a)
    d.rect(x0 - 6, y0 - 6, x1 + 6, y1 + 6, (20, 22, 28, al), r=22, ol=(240, 240, 245, al), w=8)
    d.rect(x1 + 6, y0 + 34, x1 + 34, y1 - 34, (240, 240, 245, al), r=8)
    cw = (x1 - x0 - 12 * 6) / 5
    for i in range(5):
        cx0 = x0 + 12 + i * (cw + 12)
        col = GREEN if i < 4 else mix(GREY, GREEN, cells_on - 4)
        d.rect(cx0, y0 + 12, cx0 + cw, y1 - 12, col + (al,), r=10)
        if i == 4 and cells_on < 1 and lock_state:
            for k_ in range(4):
                xx = cx0 + 10 + k_ * 30
                d.line([(xx, y1 - 18), (xx + 28, y0 + 18)], (70, 74, 82, al), 6)
    if lock_state:
        cx_, cy_ = x0 + 12 + 4 * (cw + 12) + cw / 2, (y0 + y1) / 2
        s = lock_k
        sh = 34 * unlock_k
        lockc = LOCKRED if lock_state == 'locked' else (240, 200, 60)
        d.arc(cx_, cy_ - 20 * s - sh, 28 * s, 36 * s, 180, 360, (235, 235, 240, al), 12 * s)
        d.line([(cx_ - 28 * s, cy_ - 20 * s - sh), (cx_ - 28 * s, cy_ - 4 * s - sh * (1 - unlock_k))], (235, 235, 240, al), 12 * s)
        d.line([(cx_ + 28 * s, cy_ - 20 * s - sh), (cx_ + 28 * s, cy_ - 2 * s)], (235, 235, 240, al), 12 * s)
        d.rect(cx_ - 46 * s, cy_ - 6 * s, cx_ + 46 * s, cy_ + 56 * s, lockc + (al,), r=10 * s, ol=(30, 10, 14, al), w=5)
        d.ell(cx_, cy_ + 20 * s, 8 * s, 8 * s, (40, 10, 14, al))
        d.rect(cx_ - 4 * s, cy_ + 22 * s, cx_ + 4 * s, cy_ + 40 * s, (40, 10, 14, al))

def label(d, x, y, s, size, a, fill=(255, 255, 255), bg=(20, 22, 28)):
    al = int(255 * a)
    f = font(size * K); w_ = f.getlength(s) / K
    d.rect(x - w_ / 2 - 22, y - size * .72, x + w_ / 2 + 22, y + size * .72, bg + (int(225 * a),), r=16)
    d.text(x, y + 2, s, size, fill + (al,))

ONSCREEN = ['TESLA', 'MODEL S 60', 'MODEL S 75', '75 kWh BATTERY', 'YOU PAID: 60 kWh', '15 kWh', '$4,500 – $9,000',
            'FLORIDA, SEPTEMBER 2017.', 'HURRICANE IRMA', 'HURRICANE IRMA · FLORIDA 2017', 'UNLOCKING…', 'FREE',
            'RANGE', '210 mi', '249 mi', 'SEPT', '16']

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    any_ = False
    # ---- act 1 battery reveal: from "sixty" until card; act 2 from L11; final from Then what
    a1 = window(t, T_SIXTY - .1, CARD0 + .1, .25, .3)
    a2 = window(t, LS[11] - .1, LS[13] + .3, .25, .3)
    a3 = window(t, LE[17] - .2, DUR + 1, .25, .1)
    a = max(a1, a2, a3)
    if a > 0:
        any_ = True
        d.rect(70, 270, 850, 860 if a1 else 640, (14, 16, 22, int(242 * a)), r=30)
        lab_a = min(a, prog(t, T_75, .2)) if a1 else a
        d.text(CX, 330, '75 kWh BATTERY', 54, (255, 255, 255, int(255 * lab_a)))
        if a1 or a3:
            lock_state = 'locked' if (a1 and t >= T_LOCK) or (a3 and t >= T_LOCK2) else None
            cells = 4 if (a1 or t >= T_LOCK2) else 5
            lk = 1 + 0.7 * (1 - oc(prog(t, T_LOCK if a1 else T_LOCK2, .16)))
            battery(d, t, a, cells, lock_state, 0, lk, 0)
            if a1:
                pa = min(a, prog(t, T_SIXTY, .25))
                d.line([(124, 548), (124, 566), (632, 566), (632, 548)], (255, 255, 255, int(255 * pa)), 5)
                d.text(378, 602, 'YOU PAID: 60 kWh', 48, (255, 255, 255, int(255 * pa)))
                la = min(a, prog(t, T_75 + .4, .25))
                d.text(706, 602, '15 kWh', 48, (255, 120, 120, int(255 * la)))
        else:   # act 2: locked -> unlocking progress -> open
            if t < T_DONE:
                battery(d, t, a, 4, 'locked', 0, 1, 0)
                pk = prog(t, BEAT1[0], T_DONE - BEAT1[0] - .05)
                if pk > 0:
                    d.rect(160, 560, 760, 600, (60, 64, 72, int(255 * a)), r=20)
                    d.rect(160, 560, 160 + 600 * io(pk), 600, GREEN + (int(255 * a),), r=20)
            else:
                uk = oc(prog(t, T_DONE, .3))
                battery(d, t, a, 4 + uk, 'opening' if uk < 1 else None, 0, 1, uk)
                if uk < 1:
                    battery(d, t, a * (1 - uk), 4 + uk, 'opening', 0, 1 + uk * .5, uk)
                for i in range(10):    # sparkle burst on the freed cell
                    pk = prog(t, T_DONE, .7)
                    if 0 < pk < 1:
                        r_ = 30 + 160 * oc(pk); an = i * 36
                        d.ell(705 + r_ * math.cos(math.radians(an)), 456 + r_ * math.sin(math.radians(an)) * .6, 9 * (1 - pk), 9 * (1 - pk), (255, 230, 120, 255))
            if t < T_DONE:
                d.text(CX, 625, 'UNLOCKING…', 48, (255, 255, 255, int(255 * a * prog(t, BEAT1[0], .2)))) if t >= BEAT1[0] else None
    # price tag
    ta = window(t, T_FOUR - .05, CARD0 + .1, .2, .3)
    if ta > 0:
        any_ = True
        s = popin(t, T_FOUR, .35)
        sw = math.sin((t - T_FOUR) * 6) * 4 * math.exp(-(t - T_FOUR) * 2)
        tag = Image.new('RGBA', (640 * K, 200 * K), (0, 0, 0, 0)); td = D(tag)
        td.poly([(40, 30), (600, 30), (630, 100), (600, 170), (40, 170), (10, 100)], (255, 214, 64), (40, 30, 10), 6)
        td.ell(48, 100, 12, 12, (40, 30, 10))
        td.text(325, 102, '$4,500 – $9,000', 66, (30, 24, 20))
        tag = tag.rotate(sw, resample=Image.BICUBIC, expand=False)
        if s > 0.02:
            tag = tag.resize((max(1, int(tag.width * s)), max(1, int(tag.height * s))), Image.LANCZOS)
            tag.putalpha(tag.getchannel('A').point(lambda v: int(v * ta)))
            img.alpha_composite(tag, (int((CX - 320 * s) * K), int((750 - 100 * s) * K)))
    # FREE stamp
    fa = window(t, T_FREE - .02, LS[13] + .3, .05, .3)
    if fa > 0:
        any_ = True
        s = 1 + 1.2 * (1 - oc(prog(t, T_FREE, .14)))
        st_ = Image.new('RGBA', (460 * K, 200 * K), (0, 0, 0, 0)); sd = D(st_)
        sd.rect(20, 20, 440, 180, None, r=20, ol=(70, 200, 110, 255), w=12)
        sd.text(230, 104, 'FREE', 110, (70, 200, 110, 255))
        st_ = st_.rotate(-8, resample=Image.BICUBIC, expand=True)
        st_ = st_.resize((int(st_.width * s), int(st_.height * s)), Image.LANCZOS)
        st_.putalpha(st_.getchannel('A').point(lambda v: int(v * fa)))
        img.alpha_composite(st_, (int(CX * K - st_.width / 2), int(760 * K - st_.height / 2)))
    # range meter after "My car says seventy-five"
    ra = window(t, T_MY75 - .1, LS[16] - .1, .25, .3)
    if ra > 0:
        any_ = True
        al = int(255 * ra)
        d.rect(90, 300, 830, 640, (14, 16, 22, int(242 * ra)), r=30)
        d.text(CX, 360, 'RANGE', 52, (255, 255, 255, al))
        k_ = io(prog(t, T_MY75 + .5, 1.2))
        miles = int(round(210 + 39 * k_))
        d.rect(140, 430, 780, 500, (60, 64, 72, al), r=34)
        d.rect(140, 430, 140 + 640 * (210 / 249) + 640 * (39 / 249) * k_, 500, GREEN + (al,), r=34)
        d.rect(140, 430, 140 + 640 * (210 / 249), 500, (40, 150, 80, al), r=34)
        d.text(260, 574, '210 mi', 56, (190, 196, 205, al))
        d.text(470, 574, '→', 56, (255, 255, 255, al))
        d.text(670, 574, f'{miles} mi' if k_ < 1 else '249 mi', 64, (110, 240, 150, al))
    # calendar "SEPT 16"
    ca = window(t, T_16 - .05, LE[17] - .1, .05, .3)
    if ca > 0:
        any_ = True
        s = popin(t, T_16, .35)
        cal = Image.new('RGBA', (300 * K, 320 * K), (0, 0, 0, 0)); cd = D(cal)
        cd.rect(10, 20, 290, 310, (250, 250, 252, 255), r=24, ol=OL, w=6)
        cd.rect(10, 20, 290, 110, LOCKRED + (255,), r=24)
        cd.rect(10, 80, 290, 110, LOCKRED + (255,))
        cd.text(150, 68, 'SEPT', 54, (255, 255, 255, 255))
        cd.text(150, 212, '16', 130, (30, 30, 40, 255))
        if s > 0.02:
            cal = cal.resize((int(cal.width * s), int(cal.height * s)), Image.LANCZOS)
            cal.putalpha(cal.getchannel('A').point(lambda v: int(v * ca)))
            img.alpha_composite(cal, (int(CX * K - cal.width / 2), int(470 * K - cal.height / 2)))
    # time card + banner
    if CARD0 - .05 <= t <= LS[14]:
        any_ = True
        ck = window(t, CARD0, CARD1 + .25, .25, .35)
        if ck > 0:
            d.rect(0, 0, W, H, (8, 14, 30, int(190 * ck)))
            s = 0.9 + 0.1 * oc(prog(t, CARD0, .4))
            spiral(d, CX, 560, 120 * s, t, ck)
            d.text(CX, 780, 'FLORIDA, SEPTEMBER 2017.', 52, (220, 228, 245, int(255 * ck)))
            d.text(CX, 870, 'HURRICANE IRMA', 96 * s, (255, 255, 255, int(255 * ck)))
        ba = window(t, CARD1 + .1, LS[14], .3, .3)
        if ba > 0:
            label(d, CX, 268, 'HURRICANE IRMA · FLORIDA 2017', 48, ba, bg=(150, 30, 40))
    if not any_:
        return None
    return img

def spiral(d, cx, cy, r, t, a):
    al = int(255 * a)
    for arm in range(2):
        pts = []
        for i in range(40):
            th = i / 39 * 3.6 + arm * math.pi + t * 3
            rr = r * (0.15 + 0.85 * i / 39)
            pts.append((cx + rr * math.cos(th), cy + rr * math.sin(th)))
        d.line(pts, (255, 255, 255, al), 16)
    d.ell(cx, cy, r * .16, r * .16, (8, 14, 30, al), (255, 255, 255, al), 6)

# ================================================================ world + camera
def storm_k(t): return window(t, STORM0, STORM1 + .8, .5, 1.2)

def world(t):
    img = background().copy()
    sk = storm_k(t)
    d = D(img)
    if sk > 0:  # rain behind the glass wall
        tint = Image.new('RGBA', (W * K, WALL_Y * K), (30, 50, 90, int(110 * sk)))
        img.paste(Image.alpha_composite(img.crop((0, 0, W * K, WALL_Y * K)).convert('RGBA'), tint).convert('RGB'), (0, 0))
        d = D(img)
        rr = np.random.default_rng(int(t * FPS))
        for _ in range(70):
            x, y = rr.uniform(-100, W), rr.uniform(0, WALL_Y - 40)
            d.line([(x, y), (x + 22, y + 70)], (190, 210, 240, int(120 * sk)), 3)
    # car with badge
    unlocked = (T_MY75 <= t < T_LOCK2)
    glow = 0.0
    if T_MY75 <= t < T_MY75 + 1.2: glow = 1 - prog(t, T_MY75, 1.2)
    if T_LOCK2 <= t < T_LOCK2 + .8: glow = 1 - prog(t, T_LOCK2, .8)
    car = car_layer('75' if unlocked else '60', int(round(glow * 10)))
    img.paste(car, (int((CX - 450) * K), 600 * K), car)
    d = D(img)
    # characters
    f = int(round(t * FPS))
    walk_k = prog(t, 0, 1.25)
    bx = -40 + (270 + 40) * oc(walk_k)
    for who, x, sched, cfg, spk in (('S', 670, SS_, SALES, 'S'), ('B', bx, BS, BUYER, 'B')):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[spk][min(f, len(MOUTH[spk]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1), **{k: v for k, v in ex.items() if k not in ('tglow',)})
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        breathe = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3
        st['dy'] = breathe + (-4 if talking(spk, t) and (f // 4) % 2 else 0)
        if who == 'B' and walk_k < 1:
            st['walk'] = t * 11
            st['dy'] -= abs(math.sin(t * 11)) * 10
        if st.get('sweat'):
            st['sweat'] = t
        if who == 'S':
            st['tablet_glow'] = clamp(prog(t, BEAT1[0] + .2, BEAT1[1] - BEAT1[0]))
        person(d, x, FEET_Y, cfg, st)
    # lightning flashes
    for lt in (CARD0 + .05, LS[10] - .02):
        if lt <= t < lt + .25:
            k_ = 1 - prog(t, lt, .25)
            img = Image.blend(img, Image.new('RGB', img.size, (230, 236, 255)), 0.45 * k_)
    return img

def camera(t):
    z = 1.014 + 0.012 * math.sin(t * 0.35)
    for t0, amt in ((T_LOCK, .05), (T_DOLL, .03), (T_DONE, .04), (T_LOCK2, .07)):
        if t >= t0: z += amt * (1 - oc(prog(t, t0, .5))) * (1 if t < t0 + .5 else 0)
    if t >= T_LOCK2 + .3: z += 0.04 * io(prog(t, T_LOCK2 + .3, 2.5))
    sx = sy = 0.0
    if T_LOCK2 <= t < T_LOCK2 + .3:
        k_ = 1 - prog(t, T_LOCK2, .3)
        sx, sy = math.sin(t * 90) * 10 * k_, math.cos(t * 77) * 8 * k_
    return z, sx, sy

# ================================================================ captions
def chunks():
    out = []
    for ln in sorted(LINES):
        cur = []
        for w in LINES[ln]:
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
def ctext(w): return w['w'].lstrip('.')
CAP_Y = 1128
CAP_SIZE = 78

@lru_cache(None)
def caption_img(ci, active):
    ws = [ctext(w) for w in CHUNKS[ci]['words']]
    size = CAP_SIZE
    while font(size).getlength(' '.join(ws)) > 800 and size > 60: size -= 2
    f = font(size)
    total = f.getlength(' '.join(ws)); sp = f.getlength(' ')
    img = Image.new('RGBA', (W, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = (W - total) / 2
    for i, w in enumerate(ws):
        col = (255, 214, 64) if i == active else (255, 255, 255)
        d.text((x, 100), w, font=f, fill=col, anchor='lm', stroke_width=9, stroke_fill=(16, 16, 28))
        x += f.getlength(w) + sp
    return img

def caption_boxes():
    """Exact bounding boxes (px) of each caption, for tools/preflight.py."""
    res = []
    for ci, c in enumerate(CHUNKS):
        a = np.array(caption_img(ci, -1).getchannel('A'))
        ys, xs = np.nonzero(a > 8)
        ox, oy = CX - W // 2, CAP_Y - 100
        size = CAP_SIZE
        ws = ' '.join(ctext(w) for w in c['words'])
        while font(size).getlength(ws) > 800 and size > 60: size -= 2
        cap_h = font(size).getbbox('H')[3] - font(size).getbbox('H')[1]
        res.append(dict(text=ws, s=c['s'], e=c['e'], x0=int(xs.min() + ox), x1=int(xs.max() + ox),
                        y0=int(ys.min() + oy), y1=int(ys.max() + oy), cap_height=int(cap_h)))
    return res

def captions(img, t):
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
def frame(n):
    t = n / FPS
    wimg = world(t)
    z, sx, sy = camera(t)
    ax, ay = CX * K, 1150 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    img = wimg.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')
    ov = overlays(t)
    if ov is not None:
        ov = ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA')
        img.alpha_composite(ov)
    # dim during the second silence beat, red flash on the final lock
    if BEAT2[0] <= t < T_LOCK2:
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.18 * io(prog(t, BEAT2[0], BEAT2[1] - BEAT2[0])))
    if T_LOCK2 <= t:
        k_ = 0.18 * (1 - prog(t, T_LOCK2, .6)) if t < T_LOCK2 + .6 else 0
        base = 0.0
        img = Image.blend(img, Image.new('RGBA', img.size, (200, 0, 20, 255)), k_ + base)
    captions(img, t)
    return img.convert('RGB').tobytes()

# ================================================================ audio
def build_audio(voice, out_wav):
    SR = sfx.SR
    v = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rng = np.random.default_rng(3); T_ = np.arange(n) / SR
    def lpf(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
    # showroom room tone: soft filtered noise + faint HVAC hum (quiet bed)
    room = lpf(rng.standard_normal(n), 60) * 0.10 + 0.004 * np.sin(2 * np.pi * 110 * T_)
    # storm bed: rain hiss + wind swell
    sk = np.array([storm_k(x) for x in T_[::480]]); sk = np.interp(T_, T_[::480], sk)
    rain = (rng.standard_normal(n) - lpf(rng.standard_normal(n), 3)) * 0.05
    wind = lpf(rng.standard_normal(n), 400) * 1.2 * (0.6 + 0.4 * np.sin(T_ * 0.9))
    bed = room + sk * (rain + wind)
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def clunk():
        a = click(1800, 2600, .08); b = tone(70, .45, 9, 1.0); b[:int(SR * .3)] += tone(140, .3, 14, .5)
        out = np.zeros(int(SR * .5)); out[:len(a)] += a; out[int(SR * .035):int(SR * .035) + len(b)] += b[:len(out) - int(SR * .035)]
        return out * 0.9
    def unlock():
        a, b = click(2600, 3600), click(3200, 4300)
        out = np.zeros(int(SR * .25)); out[:len(a)] += a; out[int(SR * .11):int(SR * .11) + len(b)] += b
        return out * .8
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def ring():
        tt = np.arange(int(SR * .9)) / SR
        return (np.sin(2 * np.pi * 440 * tt) + np.sin(2 * np.pi * 480 * tt)) * (np.sin(2 * np.pi * 20 * tt) > 0) * .18 * np.minimum(1, (0.9 - tt) * 20)
    def thunder():
        tt = np.arange(int(SR * 2.4)) / SR
        return lpf(rng.standard_normal(len(tt)), 180) * 9 * np.exp(-tt * 1.6) * np.minimum(1, tt * 30)
    def tick(): return click(4200, 5200, .03) * .5
    cues = []
    def add(t0, s, vol):
        i = int(t0 * SR); cues.append((i, s * vol))
    for k_ in range(4): add(0.05 + k_ * 0.3, step(), .5)
    add(T_SIXTY - .1, sfx.pop(), .35)
    add(T_75, sfx.ding(), .18)
    add(T_LOCK, clunk(), .7)
    add(T_FOUR - .05, sfx.whoosh(), .3)
    add(T_DOLL + .1, sfx.cha_ching(), .35)
    add(CARD0, thunder(), .8); add(CARD0, sfx.whoosh(.5, 30), .35)
    add(LS[10] - .9, ring(), .6)
    add(LS[10] - .02, thunder(), .45)
    for k_ in range(9): add(BEAT1[0] + .12 + k_ * .13, click(3000 + 300 * (k_ % 3), 4100, .03), .22)
    add(T_DONE - .02, unlock(), .7); add(T_DONE + .05, sfx.sparkle(), .3)
    add(T_FREE, sfx.stamp(), .5)
    add(T_MY75, sfx.ding(), .3)
    add(LS[15], sfx.confetti(), .25)
    add(T_16, sfx.pop(), .35)
    for k_ in range(3): add(BEAT2[0] + .2 + k_ * .38, tick(), .6)
    add(T_LOCK2, clunk(), 1.0); add(T_LOCK2 + .03, sfx.thump(), .5)
    fxa = np.zeros(n + SR * 3)
    for i, s in cues: fxa[i:i + len(s)] += s
    mixd = v * 1.0 + fxa[:n] * 0.55 + bed * 0.6
    mixd = np.clip(mixd / max(1.0, np.abs(mixd).max() / 0.95), -1, 1)
    tmp = out_wav + '.pre.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', tmp],
                   input=mixd.astype(np.float64).tobytes(), check=True)
    # two-pass loudnorm to -14 LUFS, -1.5 dBTP
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', af, '-ar', '48000', '-ac', '2', out_wav], check=True)
    os.remove(tmp)

def _init(voice):
    load_mouth(voice)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        load_mouth(sys.argv[4] if len(sys.argv) > 4 else os.path.expanduser('~/.cache/tesla-locked/voice.wav'))
        t = float(sys.argv[2])
        Image.frombytes('RGB', (W, H), frame(int(t * FPS))).save(sys.argv[3])
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
                               '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-maxrate', '12M',
                               '-bufsize', '24M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
                               '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(voice,)) as pool:
            for i, buf in enumerate(pool.imap(frame, range(nf), chunksize=4)):
                ff.stdin.write(buf)
                if i % 150 == 0: print(f'frame {i}/{nf}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', out)
