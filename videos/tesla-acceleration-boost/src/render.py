"""Tesla Acceleration Boost skit: Tesla lot -> driveway at night -> the Tesla app -> drag strip -> finance office. Flat-vector
style, 1080x1920 @30. Built on bmw-heated-seats/src/render.py: same cast, caption system, camera, whip pans and mix chain.
One background oddity per scene (never mentioned). User photos in ../assets are shown as cards.
Usage: python render.py video VOICE.wav OUT.mp4 | still T OUT.png [VOICE] | thumb OUT.png [VOICE] | meta OUT.json"""
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
DUR = round(WORDS[-1]['e'] + 2.2, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/tesla-acceleration-boost/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
HOOK = 3.0                                 # no cards, labels or overlays before this
T_CLOSE = LS[1] - 0.12                     # in-scene cut: closer on the salesman and the car
T_S2 = LS[2] - 0.4                         # scene cuts (whip pans)
T_S3 = LS[4] - 0.4
T_S4 = LS[6] - 0.45
T_S5 = LS[8] - 0.45
BEAT = (LE[9], LS[10])
T_PAID, T_2000, T_FASTER = word_t(0, 'paid'), word_t(0, '$2,000'), word_t(0, 'faster')
T_AB = word_t(1, 'Acceleration')
T_HOW, T_MOTOR = LS[2], word_t(2, 'motor')
T_NO, T_SAMEC, T_SAMEM, T_SW = LS[3], word_t(3, 'car'), word_t(3, 'motors'), word_t(3, 'software')
T_FAST, T_LOCKED = word_t(4, 'fast'), word_t(4, 'locked')
T_RES, T_ZERO, T_44, T_39 = word_t(5, 'reserved'), word_t(5, 'Zero'), word_t(5, '4.4'), word_t(5, '3.9')
T_HALF = word_t(6, 'half')
T_400, T_GREAT = word_t(7, '$400'), word_t(7, 'Great')
T_PIECES = word_t(8, 'pieces'); T_PIECES2 = T_PIECES + .4
T_SLOW, T_FREE = word_t(9, 'slow'), word_t(9, 'free')
T_FINAL = LS[10]
T_CARD = LE[10] + 0.3                      # final caption card (last ~2 s)
T_LAUNCH = T_GREAT - 0.05                  # drag-strip launch on "Great value"
T_TREE = LS[6] + 0.2                       # start-light countdown
SCENES = [0.0, T_S2, T_S3, T_S4, T_S5]
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

# ================================================================ emblem (hand-drawn)
INK = (16, 16, 18)
CHROME = (214, 220, 228)
TESLA_RED = (220, 24, 32)
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


# Tesla Model 3 side profile (front to the left), Stealth Grey like the user's photo: no grille, slim headlamp, one-piece
# black glass roof, flush handles, fastback with a short trunk lip, aero wheel covers.
M3_CTRL = [(.012, .17), (0.0, .30), (.004, .38), (.03, .43), (.12, .475), (.24, .51), (.31, .535), (.45, .715), (.56, .735),
           (.67, .705), (.80, .60), (.92, .545), (.985, .52), (1.0, .46), (.996, .26), (.97, .17), (.86, .15), (.5, .15), (.14, .15)]
M3_COL = ((92, 96, 104), (168, 174, 184), (40, 42, 48))
def m3_wheel(d, wx, wy, r, spin=0.0):
    d.ell(wx, wy, r, r, (18, 18, 22))
    d.ell(wx, wy, r * .74, r * .74, (128, 132, 140), (60, 62, 68), max(2, r * .05))     # aero cover
    for a in range(5):                                                                   # turbine blades
        ra = math.radians(a * 72 + spin)
        d.poly([(wx + r * .18 * math.cos(ra), wy + r * .18 * math.sin(ra)),
                (wx + r * .70 * math.cos(ra + .25), wy + r * .70 * math.sin(ra + .25)),
                (wx + r * .70 * math.cos(ra + .55), wy + r * .70 * math.sin(ra + .55)),
                (wx + r * .22 * math.cos(ra + .5), wy + r * .22 * math.sin(ra + .5))], (54, 56, 62))
    d.ell(wx, wy, r * .2, r * .2, (176, 180, 188), (60, 62, 68), 2)
    tesla_logo(d, wx, wy + r * .01, r * .0011, (40, 40, 46))

def model3(d, x0, ground, L, spin=0.0, lights=False):
    Hh = L * .42
    def P(u, v): return (x0 + u * L, ground - v * Hh)
    base, hi, lo = M3_COL
    d.ell(x0 + L * .5, ground + 4, L * .56, 14, (0, 0, 0, 100))
    body = spline([P(u, v) for u, v in M3_CTRL], 8)
    shade(d, body, hi, lo, ground - .74 * Hh, ground - .2 * Hh)
    shade(d, spline([P(.02, .17), P(.5, .165), P(.98, .17), P(.99, .25), P(.5, .23), P(.01, .25)], 6), (36, 38, 44), (22, 22, 26),
          ground - .25 * Hh, ground - .16 * Hh)
    d.line(spline([P(.05, .44), P(.30, .50), P(.62, .53), P(.95, .52)], 8, closed=False), hi + (220,), 3)   # shoulder light
    d.line(spline([P(.22, .33), P(.5, .31), P(.75, .33)], 6, closed=False), lo + (160,), 3)                 # lower door sculpt
    r = Hh * .21
    for u in (.18, .80):
        wx, wy = P(u, 0)[0], ground - r
        d.chord(wx, wy, r * 1.2, r * 1.2, 180, 360, (14, 14, 16))
        d.rect(wx - r * 1.2, wy - 2, wx + r * 1.2, ground - 4, (14, 14, 16))
    d.poly(body, None, (22, 24, 30), 5)
    gh = spline([P(.325, .555), P(.45, .70), P(.56, .72), P(.67, .69), P(.80, .59), P(.76, .565)], 5)   # black glass roof
    shade(d, gh, (70, 86, 106), (12, 14, 20), ground - .72 * Hh, ground - .55 * Hh)
    d.poly(gh, None, (14, 14, 18), 4)
    d.poly([P(.39, .58), P(.42, .58), P(.49, .69), P(.46, .69)], (255, 255, 255, 46))                  # glint
    d.poly([P(.545, .56), P(.565, .56), P(.565, .72), P(.545, .72)], (12, 12, 16))                      # B-pillar
    d.line([P(.335, .55), P(.325, .19)], lo, 3)                                                          # door cuts
    d.line([P(.555, .555), P(.56, .17)], lo, 3)
    d.line(spline([P(.73, .56), P(.72, .40), P(.70, .30)], 4, closed=False), lo, 3)
    for u in (.45, .655):                                                                                # flush handles
        d.rect(*P(u, .47), *P(u + .045, .455), (52, 54, 60), r=3)
    d.poly(spline([P(.33, .57), P(.385, .585), P(.38, .625), P(.335, .62)], 4), base, (22, 24, 30), 3)   # mirror
    d.poly(spline([P(.006, .40), P(.10, .45), P(.115, .44), P(.02, .385)], 4), (238, 244, 252), (22, 24, 30), 3)   # slim lamp
    d.line([P(.02, .40), P(.10, .44)], (170, 210, 255), 2)
    d.poly([P(.005, .22), P(.09, .225), P(.08, .27), P(.003, .27)], (22, 22, 26))                     # lower intake slot
    d.poly([P(.935, .54), P(.99, .515), P(.995, .48), P(.94, .505)], (210, 26, 34))                    # tail lamp
    d.rect(*P(.905, .44), *P(.93, .41), lo, r=2)                                                        # charge-port door
    if lights:
        d.poly([P(.0, .42), P(-.55, .34), P(-.55, .62)], (255, 248, 210, 40))                           # headlight beam
    for u in (.18, .80):
        m3_wheel(d, P(u, 0)[0], ground - r, r, spin)

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

@lru_cache(None)
def car_layer(L, spin, lights=False):
    img = Image.new('RGBA', (int(L * 1.75) * K, int(L * .62) * K), (0, 0, 0, 0))
    model3(D(img, ox=-L * .65, oy=-L * .56), 0, 0, L, spin, lights)
    return img
def paste_car(img, x0, ground, L, spin=0, lights=False):
    c = car_layer(L, int(spin) % 72, lights)
    img.paste(c, (int((x0 - L * .65) * K), int((ground - L * .56) * K)), c)
def paste_road(img, col, L, x0, g, flip=False):
    paste_rot(img, road_car(col, L), x0 + .5 * L, g - .25 * L, flip=flip)

def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))
def two_band(y, top, bot):
    return Image.fromarray(np.concatenate([grad(y * K, W * K, *top), grad((H - y) * K, W * K, *bot)]).astype(np.uint8))
GROUND = 860                               # horizon line for the outdoor sets
CAR_G, CAR_X, CAR_L = 930, CX - 290, 580

# ================================================================ background oddities (comment bait, never mentioned)
# 1 lot: a man in a three-piece suit standing on a parked car's roof, calmly eating cereal.
# 2 driveway: the neighbour mowing his lawn at night in a bathrobe and slippers, head torch on, glass of red wine in hand.
# 3 app/cafe: a scuba diver in full gear reading the financial pages over an espresso.
# 4 drag strip: a businessman in a racing helmet riding an office chair down the next lane on a fire extinguisher.
# 5 finance office: a banker feeding cash into a shredder while sipping champagne.
NPC = dict(cereal=cast('d8a47e', '2a1c14', '3b3f4a', tie='7a1420'),
           robe=cast('e8b896', '8a8a8a', '6e4a7a', pants='e8b896', shoe='c9b48a', shirt='6e4a7a', style='messy'),
           diver=cast('c08862', '1a1a1a', '16181c', shirt='16181c', shoe='f0c020'),
           racer=cast('f0c9a8', '603018', '2c3446', tie='c0a040'),
           banker=cast('7a4c34', '1a1a1a', '22252e', tie='b08a2a', shirt='f4f4f6'))

def cereal_man(img, t, x, fy, s):
    k_ = .5 + .5 * math.sin(t * 2.6)                          # spoon goes bowl -> mouth -> bowl
    st = mk((-88, 150), (-88 - 4 * k_, 140 - 230 * k_), prop={'lpose': 'bowl', 'rpose': 'spoon'}, look=0, brows='flat',
            mouth=.6 * max(0, math.sin(t * 2.6 - 1.2)))
    st['out_rpose'] = k_ > .5; st['blink'] = (t % 3.7) < .12; st['lids'] = .3
    npc(img, x, fy, s, NPC['cereal'], st)

def robe_man(img, t, x0, fy, s):
    x = x0 + 30 * math.sin(t * .9)                            # pushing the mower back and forth
    d = D(img)
    d.poly([(x - 20 * s, fy - 840 * s), (x - 520 * s, fy - 1000 * s), (x - 520 * s, fy - 520 * s)], (255, 250, 210, 40))   # head-torch beam
    d.rect(x - 470 * s, fy - 110 * s, x - 200 * s, fy - 20 * s, (200, 34, 34), r=16 * s, ol=(40, 10, 10), w=3)   # mower deck
    d.rect(x - 420 * s, fy - 170 * s, x - 300 * s, fy - 110 * s, (40, 40, 44), r=8 * s)
    for wx in (x - 440 * s, x - 230 * s):
        d.ell(wx, fy - 14 * s, 34 * s, 34 * s, (24, 24, 28))
    d.line([(x - 230 * s, fy - 90 * s), (x - 168 * s, fy - 570 * s)], (60, 60, 66), 14 * s)   # handle up to his hand
    st = mk((60, 200), (90, 20), prop={'rpose': 'wine'}, look=-1, brows='flat', mouth=0.0)
    st['blink'] = (t % 4.3) < .12; st['lids'] = .5
    npc(img, x, fy, s, NPC['robe'], st)
    hx, hy = x - 0.3 * s, fy - 905 * s - 40 * s               # head torch strap + lamp
    d = D(img)
    d.line([(hx - 70 * s, hy), (hx + 70 * s, hy)], (30, 30, 34), 12 * s)
    d.ell(hx - 20 * s, hy, 18 * s, 14 * s, (250, 250, 230), (30, 30, 34), 3)

def diver(img, t, x, fy, s):
    d = D(img)
    d.rect(x - 150 * s, fy - 470 * s, x - 10 * s, fy - 450 * s, (60, 44, 32))      # high cafe table
    d.rect(x - 86 * s, fy - 450 * s, x - 74 * s, fy, (40, 30, 24))
    d.ell(x - 80 * s, fy - 6 * s, 50 * s, 10 * s, (40, 30, 24))
    d.rect(x - 130 * s, fy - 500 * s, x - 100 * s, fy - 470 * s, (246, 246, 244), r=4)           # espresso cup
    d.rect(x + 54 * s, fy - 640 * s, x + 90 * s, fy - 300 * s, (230, 230, 232), r=10 * s, ol=(60, 60, 66), w=3)   # air tank
    page = math.sin(t * .7) > .85
    st = mk((-60, 120), (-60, 120), prop={'lpose': 'paper', 'rpose': 'paper2' if page else None}, look=0, brows='flat')
    st['blink'] = (t % 3.9) < .12
    npc(img, x, fy, s, NPC['diver'], st)
    hx, hy = x, fy - 905 * s                                   # mask, snorkel, flippers
    d = D(img)
    d.rect(hx - 56 * s, hy - 40 * s, hx + 56 * s, hy + 6 * s, (120, 200, 230, 200), r=16 * s, ol=(20, 20, 24), w=8 * s)
    d.line([(hx + 60 * s, hy - 20 * s), (hx + 74 * s, hy - 150 * s), (hx + 50 * s, hy - 160 * s)], (250, 140, 20), 12 * s)
    for side in (-1, 1):
        d.poly([(x + side * 40 * s - 30 * s, fy - 30 * s), (x + side * 40 * s + 30 * s, fy - 30 * s),
                (x + side * 70 * s + 50 * s, fy + 10 * s), (x + side * 70 * s - 70 * s, fy + 10 * s)], (240, 200, 30), (30, 30, 34), 3)

def racer(img, t, x, fy, s):
    d = D(img)
    puff = (t * 8) % 1
    for i in range(6):                                         # extinguisher jet behind him
        k_ = (i + puff) / 6
        d.ell(x + (120 + 330 * k_) * s, fy - 420 * s + 30 * math.sin(i * 2 + t * 9) * s, (30 + 90 * k_) * s, (24 + 60 * k_) * s,
              (246, 248, 250, int(220 * (1 - k_))))
    d.rect(x - 70 * s, fy - 120 * s, x + 70 * s, fy - 90 * s, (30, 30, 34), r=8 * s)            # office chair
    d.rect(x - 60 * s, fy - 330 * s, x - 30 * s, fy - 100 * s, (30, 30, 34), r=8 * s)
    d.line([(x, fy - 90 * s), (x, fy - 30 * s)], (90, 90, 96), 10 * s)
    for dx in (-60, 0, 60):
        d.line([(x, fy - 30 * s), (x + dx * s, fy - 10 * s)], (60, 60, 66), 8 * s); d.ell(x + dx * s, fy - 6 * s, 10 * s, 10 * s, (20, 20, 24))
    st = mk((-40, 200), (120, 140), prop={'rpose': 'extinguisher'}, look=-1, brows='angry', eyes='wide')
    st['dy'] = 0
    npc(img, x, fy - 110 * s, s * .92, NPC['racer'], st)
    hx, hy = x - 4 * s, fy - 110 * s - 905 * s * .92            # full-face racing helmet over the head
    d = D(img)
    d.ell(hx, hy - 8 * s, 82 * s, 92 * s, (240, 240, 244), (20, 20, 24), 4)
    d.rect(hx - 60 * s, hy - 24 * s, hx + 50 * s, hy + 18 * s, (30, 40, 60), r=14 * s)
    d.line([(hx - 78 * s, hy - 60 * s), (hx + 78 * s, hy - 60 * s)], TESLA_RED, 10 * s)
    for i in range(3):                                         # tie flapping
        d.line([(hx + 10 * s, hy + 140 * s), (hx + (60 + 20 * i) * s, hy + (150 + 10 * math.sin(t * 20 + i)) * s)], (192, 160, 64), 8 * s)

def banker(img, t, x, fy, s):
    feed = (t * .8) % 1
    sip = math.sin(t * 1.3) > .6
    st = mk((-88, -90) if sip else (-60, 170), (150, 150 + 40 * feed), prop={'lpose': 'flute', 'rpose': 'cash'}, look=1,
            brows='flat', smile=1)
    st['out_lpose'] = sip; st['blink'] = (t % 3.3) < .12; st['lids'] = .35
    npc(img, x, fy, s, NPC['banker'], st)
    d = D(img)
    sx = x + 300 * s                                           # shredder beside him, cash going in
    d.rect(sx - 80 * s, fy - 300 * s, sx + 80 * s, fy, (60, 64, 72), r=8 * s, ol=(30, 32, 36), w=3)
    d.rect(sx - 90 * s, fy - 336 * s, sx + 90 * s, fy - 290 * s, (36, 38, 44), r=6 * s)
    d.rect(sx - 60 * s, fy - 322 * s, sx + 60 * s, fy - 310 * s, (12, 12, 14))
    d.rect(sx - 30 * s, fy - (372 - 40 * feed) * s, sx + 30 * s, fy - 322 * s, (150, 200, 140), ol=(60, 100, 60), w=2)
    rng = np.random.default_rng(int(t * 12))
    for i in range(12):                                        # green strips spilling out the front
        y = fy - 280 * s + ((t * 300 + i * 37) % 260) * s
        xx = sx - 70 * s + (i % 6) * 26 * s
        d.line([(xx, y), (xx + rng.uniform(-8, 8) * s, y + 30 * s)], (110, 170, 110), 4 * s)

# ================================================================ sets
def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)

def wordmark(d, x, y, size, col): d.text(x, y, 'T E S L A', size, col, path=FONT_X)

# ---- scene 1: Tesla store lot, daytime
@lru_cache(None)
def bg_lot():
    img = two_band(GROUND, ((92, 148, 214), (198, 222, 242)), ((84, 86, 92), (120, 122, 128))); d = D(img)
    for cx_, cy_, r_ in ((150, 120, 70), (230, 110, 50), (760, 170, 60), (840, 150, 80)):
        d.ell(cx_, cy_, r_ * 1.4, r_ * .6, (255, 255, 255, 170))
    d.rect(-10, 260, W + 10, GROUND, (236, 238, 241))                               # store facade
    d.rect(-10, 260, W + 10, 380, (246, 247, 249)); d.line([(-10, 380), (W + 10, 380)], (200, 204, 210), 3)
    tesla_logo(d, 150, 322, .36)
    wordmark(d, 470, 322, 66, (24, 24, 28))
    shade(d, [(-10, 410), (W + 10, 410), (W + 10, GROUND - 6), (-10, GROUND - 6)], (40, 50, 64), (86, 100, 118), 410, GROUND)
    for x in range(-10, W, 160): d.rect(x, 410, x + 10, GROUND - 6, (210, 214, 220))
    for x in range(-200, W, 260): d.poly([(x, GROUND - 6), (x + 90, 410), (x + 140, 410), (x + 50, GROUND - 6)], (255, 255, 255, 30))
    for i, x in enumerate(range(-40, W + 200, 190)):                                 # angled parking bays
        d.poly([(x, GROUND + 20), (x + 8, GROUND + 20), (x - 140, H), (x - 160, H)], (232, 232, 226))
    for x in (40, 120):                                                              # Superchargers
        d.rect(x, 640, x + 48, GROUND + 30, (240, 242, 244), r=14, ol=(150, 154, 160), w=3)
        d.rect(x, 640, x + 48, 690, TESLA_RED, r=14)
        d.line([(x + 48, 760), (x + 70, 820), (x + 58, 870)], (30, 30, 34), 6)
    return img

def lot_life(img, t):
    paste_road(img, (238, 238, 232), 360, 735, GROUND + 80)
    cereal_man(img, t, 915, GROUND + 80 - .78 * .34 * 360 + 14, .30)   # standing on the roof

# ---- scene 2: driveway at night, plugged in
@lru_cache(None)
def bg_drive():
    img = two_band(GROUND, ((8, 12, 34), (36, 38, 72)), ((50, 50, 58), (82, 82, 90))); d = D(img)
    rng = np.random.default_rng(5)
    for _ in range(60): d.ell(rng.uniform(0, W), rng.uniform(0, 300), 2, 2, (255, 255, 240, int(rng.uniform(80, 220))))
    d.ell(900, 150, 50, 50, (240, 236, 210)); d.ell(916, 140, 9, 9, (214, 208, 186)); d.ell(888, 168, 6, 6, (214, 208, 186))
    d.poly([(20, 360), (420, 170), (820, 360)], (32, 28, 38))                         # house
    d.rect(60, 360, 790, GROUND, (66, 62, 78))
    for y in range(380, GROUND, 26): d.line([(60, y), (790, y)], (58, 54, 70), 2)
    d.rect(300, 560, 720, GROUND, (96, 92, 104), ol=(40, 38, 48), w=4)               # garage door
    for y in range(600, GROUND, 60): d.line([(300, y), (720, y)], (70, 66, 80), 3)
    img = spot(img, 280, 520, 20, 360, 420, 70); d = D(img)
    d.ell(280, 520, 16, 16, (255, 230, 160)); d.ell(280, 520, 40, 40, (255, 220, 140, 60))
    d.rect(90, 450, 250, 620, (255, 210, 120), ol=(36, 32, 44), w=6)                 # lit window
    d.line([(170, 450), (170, 620)], (36, 32, 44), 5); d.line([(90, 535), (250, 535)], (36, 32, 44), 5)
    d.rect(744, 600, 778, 660, (236, 238, 240), r=8, ol=(30, 30, 34), w=3)          # Wall Connector
    d.rect(752, 612, 770, 630, (40, 50, 70), r=3)
    d.line([(761, 660), (770, 760), (722, 800), (706, CAR_G - 228)], (24, 24, 28), 6)   # cable to the charge port
    d.rect(790, GROUND - 40, W + 10, GROUND + 4, (230, 230, 226))                    # neighbour's picket fence
    for x in range(796, W + 20, 26): d.poly([(x, GROUND - 40), (x + 9, GROUND - 56), (x + 18, GROUND - 40)], (230, 230, 226))
    d.rect(790, GROUND + 4, W + 10, GROUND + 160, (28, 58, 36))                       # neighbour's lawn
    for x in range(800, W, 18): d.line([(x, GROUND + 160), (x + 4, GROUND + 140)], (40, 80, 46), 3)
    return img

def drive_life(img, t):
    robe_man(img, t, 905, GROUND + 150, .30)

# ---- scene 3: the Tesla app on a giant phone in a cafe
PH_X0, PH_Y0, PH_X1, PH_Y1 = CX - 210, 110, CX + 210, 880
@lru_cache(None)
def bg_app():
    img = two_band(WALL_Y, ((104, 70, 50), (132, 92, 64)), ((196, 186, 168), (222, 214, 198))); d = D(img)
    for r_, y in enumerate(range(100, WALL_Y, 40)):                                   # brick wall
        d.line([(0, y), (W, y)], (88, 58, 42), 3)
        for x in range((r_ % 2) * 60, W, 120): d.line([(x, y), (x, y + 40)], (88, 58, 42), 3)
    d.rect(0, 0, W, 84, (40, 30, 24))
    for px in (120, 820):
        d.line([(px, 84), (px, 140)], (30, 30, 30), 3); d.chord(px, 160, 40, 26, 180, 360, (30, 30, 30)); d.ell(px, 160, 24, 6, (255, 230, 170))
    for x in range(0, W, 120):                                                        # checker floor
        for i, y in enumerate(range(WALL_Y, H, 120)):
            if (x // 120 + i) % 2: d.rect(x, y, x + 120, y + 120, (176, 166, 150))
    d.rect(PH_X0 + 14, PH_Y0 + 20, PH_X1 + 14, PH_Y1 + 20, (0, 0, 0, 90), r=60)      # phone shadow
    d.rect(PH_X0, PH_Y0, PH_X1, PH_Y1, (20, 20, 24), r=60, ol=(90, 92, 100), w=5)
    d.rect(PH_X0 + 16, PH_Y0 + 16, PH_X1 - 16, PH_Y1 - 16, (14, 15, 18), r=46)
    d.rect(CX - 50, PH_Y0 + 30, CX + 50, PH_Y0 + 58, (0, 0, 0), r=14)                # island
    ph = Image.open(os.path.join(HERE, '..', 'assets', 'model3_grey.jpg')).convert('RGB')
    w_ = PH_X1 - PH_X0 - 32; h_ = 220
    sc_ = max(w_ / ph.width, h_ / ph.height)
    ph = ph.resize((int(ph.width * sc_ * K), int(ph.height * sc_ * K)), Image.LANCZOS)
    l_ = (ph.width - w_ * K) // 2; tp_ = (ph.height - h_ * K) // 2
    img.paste(ph.crop((l_, tp_, l_ + w_ * K, tp_ + h_ * K)), ((PH_X0 + 16) * K, (PH_Y0 + 80) * K)); d = D(img)
    d.text(PH_X0 + 40, PH_Y0 + 340, 'Upgrades', 40, (255, 255, 255), anchor='lm')
    d.rect(PH_X0 + 32, PH_Y0 + 380, PH_X1 - 32, PH_Y1 - 40, (32, 34, 40), r=22)
    d.text(PH_X0 + 56, PH_Y0 + 426, 'Acceleration Boost', 31, (255, 255, 255), anchor='lm', path=FONT_X)
    d.text(PH_X0 + 56, PH_Y0 + 476, '0-60 MPH', 26, (150, 156, 168), anchor='lm', path=FONT_X)
    d.text(PH_X0 + 56, PH_Y0 + 596, '$2,000', 46, (255, 255, 255), anchor='lm')
    return img

def padlock(d, x, y, s, col=(255, 255, 255)):
    d.arc(x, y - 16 * s, 14 * s, 16 * s, 180, 360, col, 5 * s)
    d.rect(x - 20 * s, y - 16 * s, x + 20 * s, y + 16 * s, col, r=4 * s)

def app_life(img, t):
    d = D(img)
    y = PH_Y0 + 525
    if t >= T_44 - .05:
        d.text(PH_X0 + 56, y, '4.4 s', 40, (170, 174, 184), anchor='lm')
        if t >= T_39 - .05:
            k_ = popin(t, T_39 - .05, .3)
            d.line([(PH_X0 + 52, y), (PH_X0 + 52 + 98 * min(1, k_), y)], (230, 60, 60), 5)
            d.text(PH_X0 + 176, y, '→', 40, (170, 174, 184), anchor='lm')
            d.text(PH_X0 + 232, y, '3.9 s', 40 * k_, (90, 220, 130), anchor='lm')
    by = PH_Y1 - 96                                                                    # locked upgrade button
    jig = 6 * math.sin(t * 40) * math.exp(-(t - T_LOCKED) * 5) if t >= T_LOCKED else 0
    d.rect(PH_X0 + 56 + jig, by - 34, PH_X1 - 56 + jig, by + 34, (62, 106, 225), r=34)
    padlock(d, PH_X0 + 112 + jig, by + 2, .8)
    d.text(CX + 26 + jig, by, 'Upgrade', 32, (255, 255, 255))
    if t >= T_RES - .05:                                                               # the "reserved" stamp
        k_ = popin(t, T_RES - .05, .25)
        st_ = stamp_img('RESERVED', (226, 48, 58), 64)
        lay = st_.rotate(-12, resample=Image.BICUBIC, expand=True)
        sc_ = 1.6 - .6 * min(1, k_)
        lay = lay.resize((max(1, int(lay.width * sc_)), max(1, int(lay.height * sc_))), Image.LANCZOS)
        img.alpha_composite(lay, (int(CX * K - lay.width / 2), int((PH_Y1 - 96) * K - lay.height / 2))) if img.mode == 'RGBA' else \
            img.paste(lay, (int(CX * K - lay.width / 2), int((PH_Y1 - 96) * K - lay.height / 2)), lay)
    diver(img, t, 880, WALL_Y + 50, .32)

# ---- scene 4: drag strip at dusk
@lru_cache(None)
def bg_strip():
    img = two_band(GROUND, ((246, 150, 96), (255, 214, 160)), ((44, 44, 48), (74, 74, 78))); d = D(img)
    d.poly([(-10, 520), (W + 10, 600), (W + 10, GROUND), (-10, GROUND)], (70, 72, 82))   # grandstand
    rng = np.random.default_rng(9)
    for r_ in range(7):
        y0 = 540 + r_ * 44
        d.line([(-10, y0 + 30), (W + 10, y0 + 30 + 80 * (1 - r_ / 7) * 0)], (90, 92, 104), 3)
        for x in range(-10, W, 22):
            if rng.random() < .8:
                d.ell(x + rng.uniform(-4, 4), y0 + 18 + x * 80 / W * (1 - r_ / 7) * 0, 8, 10,
                      tuple(int(c) for c in rng.choice([(200, 60, 60), (60, 90, 180), (230, 200, 80), (240, 240, 240), (40, 40, 44)])))
    for lx in (60, 1000):                                                              # light towers
        d.line([(lx, 120), (lx, 560)], (50, 50, 56), 8); d.rect(lx - 40, 100, lx + 40, 140, (255, 250, 220), ol=(50, 50, 56), w=4)
    d.rect(560, 170, 900, 440, (14, 14, 18), r=10, ol=(70, 70, 76), w=6)               # timing board
    d.text(730, 214, '0-60 MPH', 38, (255, 190, 60), path=FONT_X)
    d.text(600, 300, 'STOCK', 36, (200, 200, 206), anchor='lm', path=FONT_X); d.text(860, 300, '4.4 s', 44, (255, 190, 60), anchor='rm')
    d.text(600, 384, 'BOOST', 36, (200, 200, 206), anchor='lm', path=FONT_X); d.text(860, 384, '3.9 s', 44, (90, 220, 130), anchor='rm')
    d.rect(-10, GROUND, W + 10, GROUND + 6, (230, 230, 230))
    d.rect(-10, CAR_G + 26, W + 10, CAR_G + 34, (236, 236, 236))                       # lane line
    d.rect(CAR_X - 30, GROUND + 6, CAR_X - 18, CAR_G + 26, (240, 240, 240))           # start line
    for k_ in range(40): d.line([(rng.uniform(-10, W), CAR_G + rng.uniform(-30, 20)), (rng.uniform(-10, W), CAR_G + rng.uniform(-30, 20))], (30, 30, 32, 90), 6)   # rubber
    d.line([(150, 420), (150, GROUND + 20)], (40, 40, 44), 12)                          # the start lights
    d.rect(118, 420, 182, 760, (30, 30, 34), r=10)
    return img

TREE = [(470, (255, 190, 40)), (540, (255, 190, 40)), (610, (255, 190, 40)), (690, (60, 230, 90))]
def strip_life(img, t):
    d = D(img)
    for i, (y, col) in enumerate(TREE):
        on = (T_TREE + i * .45 <= t < T_LAUNCH - .05) if i < 3 else t >= T_LAUNCH - .05
        d.ell(150, y, 24, 24, col if on else (60, 58, 50))
    racer(img, t, 1060 - 175 * (t - T_S4), GROUND + 46, .26)

# ---- scene 5: finance office
@lru_cache(None)
def bg_office():
    img = two_band(WALL_Y, ((226, 220, 210), (242, 238, 230)), ((70, 74, 86), (98, 102, 114))); d = D(img)
    d.rect(0, 0, W, 84, (210, 206, 198))
    d.rect(0, 700, W, WALL_Y, (120, 84, 56)); d.rect(0, 692, W, 704, (90, 60, 40))
    for x in range(30, W, 140): d.rect(x, 730, x + 110, WALL_Y - 26, (110, 76, 50), ol=(90, 60, 40), w=3)
    d.rect(540, 150, 900, 560, (150, 190, 230), ol=(60, 60, 66), w=10)                 # window with a skyline
    for bx, bh in ((560, 180), (610, 260), (680, 140), (730, 300), (800, 200), (850, 240)):
        d.rect(bx, 560 - bh, bx + 46, 552, (96, 120, 150))
    d.line([(720, 150), (720, 560)], (60, 60, 66), 8)
    d.rect(90, 180, 390, 480, (250, 250, 250), ol=(40, 40, 44), w=8)                  # framed brand panel
    tesla_logo(d, 240, 300, .5); wordmark(d, 240, 420, 34, (24, 24, 28))
    d.rect(150, 800, 760, 830, (92, 62, 40), r=6)                                      # desk
    d.rect(170, 830, 740, WALL_Y + 40, (120, 84, 56), ol=(80, 54, 36), w=4)
    d.rect(300, 784, 440, 800, (250, 250, 248)); d.rect(320, 778, 450, 792, (240, 240, 236))   # contract
    d.line([(460, 790), (520, 770)], (24, 24, 28), 5)
    d.rect(560, 680, 700, 780, (24, 24, 28), r=6); d.rect(620, 780, 640, 800, (40, 40, 44))  # monitor
    return img

def office_life(img, t):
    banker(img, t, 830, WALL_Y + 40, .34)

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
    if c.get('badge', not c['glasses']):                  # dealer name badge with a tiny T mark
        d.rect(x + 46, top + 92, x + 100, top + 118, (245, 245, 248), r=4)
        tesla_logo(d, x + 73, top + 105, 0.1)
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
        elif prop == 'bowl':                                # cereal bowl
            d.chord(hx2, hy2 - 30, 44, 36, 0, 180, (240, 240, 236)); d.ell(hx2, hy2 - 30, 44, 10, (250, 220, 140), OL, 3)
            for i in range(5): d.ell(hx2 - 30 + i * 15, hy2 - 33 + (i % 2) * 4, 6, 4, (210, 150, 60))
        elif prop == 'spoon':
            d.line([(hx2, hy2), (hx2 - 30, hy2 - 50)], (200, 204, 210), 7); d.ell(hx2 - 34, hy2 - 56, 11, 8, (200, 204, 210))
        elif prop in ('wine', 'flute'):                     # red wine / champagne glass
            fl = prop == 'flute'
            d.line([(hx2, hy2 - 10), (hx2, hy2 - 40)], (230, 236, 240), 4)
            d.poly([(hx2 - (10 if fl else 22), hy2 - 40), (hx2 + (10 if fl else 22), hy2 - 40), (hx2 + (12 if fl else 26), hy2 - (110 if fl else 84)),
                    (hx2 - (12 if fl else 26), hy2 - (110 if fl else 84))], (230, 236, 240, 150), (120, 130, 140), 2)
            d.poly([(hx2 - (10 if fl else 22), hy2 - 42), (hx2 + (10 if fl else 22), hy2 - 42), (hx2 + (11 if fl else 24), hy2 - 70),
                    (hx2 - (11 if fl else 24), hy2 - 70)], (240, 210, 110) if fl else (130, 20, 40))
        elif prop == 'paper':                               # broadsheet, financial pages
            d.rect(hx2 - 20, hy2 - 150, hx2 + 190, hy2 + 20, (236, 228, 206), ol=(90, 86, 76), w=3)
            d.rect(hx2 - 8, hy2 - 138, hx2 + 178, hy2 - 112, (40, 40, 44))
            for i in range(6): d.line([(hx2 - 6, hy2 - 96 + i * 18), (hx2 + 80, hy2 - 96 + i * 18)], (150, 146, 136), 4)
            d.line([(hx2 + 96, hy2 - 30), (hx2 + 120, hy2 - 70), (hx2 + 140, hy2 - 50), (hx2 + 176, hy2 - 100)], (200, 40, 40), 5)
        elif prop == 'extinguisher':
            d.rect(hx2 - 20, hy2 - 30, hx2 + 20, hy2 + 90, (210, 30, 30), r=14, ol=OL, w=3)
            d.line([(hx2, hy2 - 30), (hx2 + 50, hy2 - 50)], (30, 30, 34), 8)
        elif prop == 'cash':                                # banknote
            d.rect(hx2 - 10, hy2 - 14, hx2 + 80, hy2 + 30, (150, 200, 140), r=3, ol=(60, 100, 60), w=3)
            d.ell(hx2 + 35, hy2 + 8, 12, 12, (110, 160, 110))
        elif prop == 'cup':
            d.rect(hx2 - 15, hy2 - 44, hx2 + 15, hy2 + 4, (246, 246, 244), r=4, ol=OL, w=3)
            d.rect(hx2 - 15, hy2 - 32, hx2 + 15, hy2 - 18, (150, 96, 56))
        elif prop == 'cloth':
            d.ell(hx2, hy2 - 4, 28, 18, (250, 214, 70), OL, 3)
        elif prop == 'card':                                # black credit card
            d.rect(hx2 - 6, hy2 - 52, hx2 + 70, hy2 - 4, (24, 24, 30), r=6, ol=(200, 170, 90), w=3)
            d.rect(hx2 + 4, hy2 - 40, hx2 + 22, hy2 - 28, (210, 180, 100), r=2)


# ---- performance schedules: (time, left pose, right pose, extras). Buyer furious from frame 1, then bitter.
def buyer_sched():
    A, Wd = dict(brows='angry', eyes='wide'), dict(brows='angry', eyes='wide', sweat=1)
    return [(0.0, 'point', 'up', A),                                     # frame 1: already mid-complaint
            (T_PAID - .05, 'head', 'point', A),
            (T_2000 - .1, 'up', 'up', Wd),
            (T_FASTER - .05, 'point', 'point', Wd),
            (LE[0] + .15, 'rest', 'point', dict(brows='angry')),
            (T_AB, 'cross', 'cross', dict(brows='angry', smile=-1)),
            # driveway
            (T_S2, 'rest', 'rest', dict(brows='angry')),
            (T_HOW - .05, 'shrug', 'shrug', A),
            (T_MOTOR - .1, 'point', 'rest', A),
            (T_NO, 'rest', 'rest', dict(brows='up', eyes='wide')),
            (T_SW, 'head', 'head', Wd),
            # the app
            (T_S3, 'rest', 'rest', dict(brows='angry')),
            (LS[4] - .05, 'point', 'rest', dict(brows='angry', eyes='wide')),
            (T_LOCKED - .1, 'chin', 'rest', dict(brows='worried', eyes='wide')),
            (T_RES, 'rest', 'rest', dict(brows='up', eyes='wide', smile=-1)),
            (T_39, 'head', 'head', Wd),
            # drag strip: the peak
            (T_S4, 'rest', 'rest', dict(brows='angry')),
            (LS[6] - .1, 'up', 'up', Wd),
            (T_HALF, 'point', 'point', Wd),
            (LE[6] + .1, 'rest', 'rest', dict(brows='angry')),
            (T_400, 'head', 'head', dict(brows='up', eyes='wide', sweat=1)),
            (T_LAUNCH + .1, 'hip', 'hip', dict(brows='angry', smile=-1)),
            # finance office: bitter, then quiet
            (T_S5, 'rest', 'rest', dict(brows='angry')),
            (LS[8] - .05, 'point', 'point', A),
            (LE[8] + .15, 'cross', 'cross', dict(brows='angry', smile=-1)),
            (T_SLOW, 'rest', 'rest', dict(brows='worried', tired=0.35, smile=-1)),
            (T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {1: 'open', 3: 'offer', 5: 'present', 7: 'open', 9: 'offer'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
    s += [(T_SW, 'present', 'clasp', {}), (T_GREAT, 'thanks', 'clasp', {}),
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
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    if sc == 0:
        img = bg_lot().copy(); lot_life(img, t)
        paste_car(img, CAR_X, CAR_G, CAR_L)
    elif sc == 1:
        img = bg_drive().copy(); drive_life(img, t)
        paste_car(img, CAR_X, CAR_G, CAR_L, lights=True)
    elif sc == 2:
        img = bg_app().copy(); app_life(img, t)
    elif sc == 3:
        img = bg_strip().copy(); strip_life(img, t)
        lk = clamp(t - T_LAUNCH, 0, 3)
        x = CAR_X - 900 * lk ** 2 - (6 * math.sin(t * 50) if T_TREE < t < T_LAUNCH else 0)
        if x > -CAR_L * 1.3:
            if lk > 0:                                                  # launch: tyre haze behind the car
                d = D(img)
                for i in range(5): d.ell(x + CAR_L * (1 + i * .12) + 40, CAR_G - 20 - i * 6, 40 + i * 30, 26 + i * 8, (230, 230, 234, int(150 * (1 - i / 5))))
            paste_car(img, x, CAR_G, CAR_L, spin=-lk * 900)
    else:
        img = bg_office().copy(); office_life(img, t)
    d = D(img)
    f = int(round(t * FPS))
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.25), 150, 11      # already in shot, mid-complaint
    elif sc == 4:
        walk_k, bx0, dur_w = prog(t, t_in, .9), 60, 9       # stomping in
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
        z = 1.10 - 0.06 * oc(prog(t, 0, 1.6)) + 0.01 * math.sin(t * .5)   # moving from frame 1
        sx = -24 * oc(prog(t, 0, 1.6))
        punches = ((T_PAID, .03), (T_2000, .05), (T_FASTER, .04))
    elif sc == 0:                                          # closer on the salesman and the car
        z = 1.17 + 0.03 * io(prog(t, T_CLOSE, 2))
        sx = 60
        punches = ((T_CLOSE, .05), (T_AB, .04))
    elif sc in (1, 2, 3):
        z = 1.05 + 0.015 * io(prog(t, t0, 6))
        sx = 46 * (1 - oc(prog(t, t0, 1.4)))               # settle after the whip
        punches = {1: ((T_MOTOR, .03), (T_SAMEM, .04), (T_SW, .04)), 2: ((T_LOCKED, .04), (T_RES, .06), (T_39, .04)),
                   3: ((T_HALF, .06), (T_400, .04), (T_LAUNCH, .05))}[sc]
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_PIECES, .05), (T_FINAL, .05))
        pk = io(prog(t, T_FINAL - .05, .5))                # salesman turns to camera: push in on him
        z += 0.14 * pk
        sx = 150 * pk
    if sc == 3 and T_LAUNCH <= t < T_LAUNCH + .9:          # launch rumble
        k_ = 1 - prog(t, T_LAUNCH, .9)
        sx += 12 * k_ * math.sin(t * 61); sy += 9 * k_ * math.sin(t * 47 + 1)
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
CARD4 = (("$2,000 / 0.5 s", 70, INK2), ("= about $400", 70, DRED), ("per 0.1 s", 70, DRED), ("One-time payment", 44, INK2))
CHIPS2 = [('MOTORS', 'SAME', GREEN, 'T_SAMEM'), ('UPGRADE', 'SOFTWARE', RED, 'T_SW')]
CHIPS5 = [('THE CAR', 'PAID', GREEN, 'T_PIECES'), ('THE SPEED', '$2,000 EXTRA', RED, 'T_PIECES2')]
FINAL = [("Comment below.", 84, TAG), ("Next: another car", 66, (255, 255, 255)), ("that's secretly", 66, (255, 255, 255)),
         ("another car.", 66, (255, 255, 255))]
FINAL_Y0, FINAL_DY = 470, 112
ONSCREEN = (['T E S L A', 'Upgrades', 'Acceleration Boost', '0-60 MPH', '$2,000', 'Upgrade', 'RESERVED', '4.4 s', '3.9 s',
             'STOCK', 'BOOST', 'ACCELERATION BOOST', 'TESLA MODEL 3', 'SAME CAR, SAME HARDWARE', 'ALREADY FITTED', '?']
            + [r[0] for r in CARD4] + [x for r in CHIPS2 + CHIPS5 for x in r[:2]] + [f[0] for f in FINAL])

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
    s = popin(t, t0, .35)
    if t >= T_400: s *= 1 + .06 * math.sin((t - T_400) * 14) * math.exp(-(t - T_400) * 4)
    put(img, info_card(rows), CX, y, s, a, rot=-1.5)
    return True

def overlays(t):
    if t < HOOK: return None                                 # hook rule: nothing over the first 3 s
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        pa = window(t, HOOK, T_AB - .1, .15, .2)              # the real car
        if pa > 0:
            used = True
            put(img, photo_card('model3_grey.jpg', 'TESLA MODEL 3', (24, 24, 28), (255, 255, 255), 440), CX, 420,
                popin(t, HOOK, .35), pa, rot=-2)
        ta = window(t, T_AB - .1, T_S2 + .05, .1, .25)
        if ta > 0:
            used = True
            sw = math.sin((t - T_AB) * 6) * 4 * math.exp(-(t - T_AB) * 2)
            put(img, price_tag('$2,000', 'ACCELERATION BOOST', TAG), CX, 470, popin(t, T_AB - .1, .35) * .95, ta, rot=sw - 3)
    elif sc == 1:
        pa = window(t, T_NO - .1, T_S3 + .05, .1, .3)
        if pa > 0:                                           # same car, same hardware
            used = True
            put(img, photo_card('model3_cutaway.jpg', 'SAME CAR, SAME HARDWARE', (24, 24, 28), (255, 255, 255), 440), CX, 390,
                popin(t, T_NO - .1, .35), pa, rot=-2)
            d = D(img)
            panel(d, 80, 650, 830, 830, pa)
            chip_rows(d, t, CHIPS2, 702, pa)
    elif sc == 3:
        used = scene_card(img, t, CARD4, T_400 - .1, T_LAUNCH + .1, 640)   # clears before the launch
    elif sc == 4:
        pa = window(t, T_PIECES - .1, T_FINAL - .1, .1, .3)
        if pa > 0:
            used = True
            put(img, photo_card('battery_pack.jpg', 'ALREADY FITTED', (24, 24, 28), (255, 255, 255), 400), CX, 380,
                popin(t, T_PIECES - .1, .35), pa, rot=2)
            d = D(img)
            panel(d, 70, 610, 830, 880, pa)
            chip_rows(d, t, CHIPS5, 660, pa, two_line=True)
        fa = window(t, T_FINAL - .05, T_CARD + .05, .2, .25)
        if fa > 0:
            used = True
            put(img, photo_card('model3_grey.jpg', 'TESLA MODEL 3', (24, 24, 28), (255, 255, 255), 380), CX, 430,
                popin(t, T_FINAL - .05, .35), fa, rot=3)
            k_ = popin(t, T_FINAL + .4, .3)
            if k_ > .05:
                d = D(img); d.text(CX, 720, '?', 120 * k_, TAG + (int(255 * fa),), stroke=6, sc=(10, 10, 16, int(255 * fa)))
    if t >= T_CARD:                                          # final caption
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(50, FINAL_Y0 - 100, 868, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 90, (12, 14, 20, int(225 * fa)), r=34)
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
    air = lpf(rng.standard_normal(n), 60) * 0.10
    traffic = lpf(rng.standard_normal(n), 400) * 0.6 * (0.6 + 0.4 * np.sin(2 * np.pi * .13 * T_))
    chirp = np.sin(2 * np.pi * 4300 * T_) * ((T_ * 18) % 1 < .25) * ((T_ * .9) % 1 < .45) * 0.010
    mower = (0.012 * np.sign(np.sin(2 * np.pi * 52 * T_)) + 0.006 * np.sin(2 * np.pi * 104 * T_))
    mower = lpf(mower, 30) * (0.7 + 0.3 * np.sin(2 * np.pi * .9 * T_))
    murmur = lpf(rng.standard_normal(n), 25) * 0.10 * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * .7 * T_)))
    crowd = lpf(rng.standard_normal(n), 14) * 0.08
    hum = 0.005 * np.sin(2 * np.pi * 60 * T_) + 0.003 * np.sin(2 * np.pi * 120 * T_)
    grind = lpf(rng.standard_normal(n), 6) * 0.03 * ((T_ * .8) % 1 < .5)
    bed = (air + (traffic * .3) * env(0, T_S2) + (chirp + mower) * env(T_S2, T_S3) + murmur * env(T_S3, T_S4)
           + crowd * env(T_S4, T_S5) + (hum + grind) * env(T_S5, DUR + 1))
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def tick(): return click(4200, 5200, .03) * .5
    def beep(f, d=.18): tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.minimum(1, (d - tt) * 60) * .5
    def ev_launch(d=2.4):
        """Electric launch: rising inverter whine + motor hum + tyre chirp, no engine."""
        tt = np.arange(int(SR * d)) / SR
        f = 220 + 2600 * (1 - np.exp(-tt * 1.1))
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = (np.sin(ph) * .35 + np.sin(ph * 2.01) * .15 + np.sin(ph * .25) * .5) * np.minimum(1, tt * 30) * np.exp(-np.maximum(0, tt - 1.2) * 2.5)
        s[:int(SR * .3)] += (rng.standard_normal(int(SR * .3)) * np.exp(-np.arange(int(SR * .3)) / SR * 14)) * .5
        return s
    def sting():
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
    for k_ in range(4): add(0.0 + k_ * 0.28, step(), .5)        # frame 1: stomping in
    add(T_2000, sfx.cha_ching(), .22)
    add(T_FASTER, sfx.whoosh(.3, 20), .2)
    add(T_CLOSE, sfx.whoosh(.3, 14), .3)
    add(T_AB - .1, sfx.pop(), .35); add(T_AB + .2, sfx.ding(1320, .6), .14)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    for s_ in SCENES[1:4]:                                  # buyer hurrying in
        for k_ in range(3): add(s_ + .08 + k_ * .25, step(), .35)
    for k_ in range(3): add(T_S5 + .05 + k_ * .32, step(), .35)
    add(T_NO - .1, sfx.pop(), .3); add(T_SAMEM - .05, sfx.ding(1568, .5), .12); add(T_SW - .05, sfx.buzzer(.25), .2)
    add(T_LOCKED, click(900, 1400, .08), .7); add(T_LOCKED + .05, sfx.thump(.2), .3)
    add(T_RES - .05, sfx.stamp(), .4)
    add(T_44 - .05, tick(), .6); add(T_39 - .05, sfx.pop(), .3)
    for i in range(3):
        if T_TREE + i * .45 < T_LAUNCH - .1: add(T_TREE + i * .45, beep(880), .25)
    add(T_LAUNCH - .05, beep(1760, .3), .3)
    add(T_LAUNCH, ev_launch(), .55)
    add(T_400 - .1, sfx.stamp(), .32); add(T_400 + .3, sfx.cha_ching(), .3)
    add(T_PIECES - .1, sfx.pop(), .3); add(T_PIECES + .1, sfx.buzzer(.25), .18)
    for k_ in range(2): add(BEAT[0] + .2 + k_ * .35, tick(), .6)
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

def thumb(path):
    """Cover frame: furious buyer, deadpan salesman, the car, one big money line. No captions."""
    t = T_2000 + .25
    img = shoot(t)
    ov = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0)); d = D(ov)
    d.rect(0, 0, W, 800, (8, 10, 16, 165))
    d.text(CX, 170, '$2,000', 240, TAG, stroke=12, sc=(10, 10, 16))
    d.text(CX, 350, 'TO GO FASTER?!', 104, (255, 255, 255), stroke=9, sc=(10, 10, 16))
    put(ov, photo_card('model3_grey.jpg', 'SAME CAR. SAME MOTORS.', RED, (255, 255, 255), 600), CX, 640, 1.0, 1.0, rot=-3)
    img.alpha_composite(ov.resize((W, H), Image.LANCZOS))
    img.convert('RGB').save(path)

def _init(voice):
    load_mouth(voice)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        load_mouth(sys.argv[4] if len(sys.argv) > 4 else VOICE_CACHE)
        Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif mode == 'thumb':
        load_mouth(sys.argv[3] if len(sys.argv) > 3 else VOICE_CACHE)
        thumb(sys.argv[2])
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
