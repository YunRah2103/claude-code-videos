"""Toyota GR Supra vs BMW Z4 skit: showroom -> parts counter -> Graz factory line -> showroom. Flat-vector style, 1080x1920 @30.
Same cast, caption system and mix chain as tesla-locked / aston-cygnet / urus-rsq8 (built on urus-rsq8/src/render.py).
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
VOICE_CACHE = os.path.expanduser('~/.cache/supra-z4-v2/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
T_S2 = (LE[5] + LS[6]) / 2                 # scene cuts (whip pans) in the retimed gaps
T_S3 = (LE[9] + LS[10]) / 2
T_S4 = (LE[13] + LS[14]) / 2
BEAT = (LE[14], LS[15])
T_SUPRA, T_BMW0 = word_t(0, 'Supra'), word_t(0, 'BMW')
T_OLD, T_TOY2 = word_t(2, 'old'), word_t(2, 'Toyota')
T_WHAT, T_PLAT, T_GEAR = word_t(4, 'BMW'), word_t(5, 'platform'), word_t(5, 'gearbox')
T_SW = word_t(6, 'switches')
T_WIN, T_LOCK, T_PARK, T_ALL = word_t(7, 'Window'), word_t(7, 'Lock'), word_t(7, 'Parking'), word_t(7, 'All')
T_TDO, T_SUSP, T_BODY = word_t(8, 'Toyota'), word_t(9, 'suspension'), word_t(9, 'body')
T_AUS, T_Z4 = word_t(11, 'Austria'), word_t(11, 'Z4')
T_SOBMW, T_SAYS = word_t(12, 'BMW'), word_t(13, 'Supra')
T_REAL = word_t(14, 'real')
T_FINAL = LS[15]
T_HOOK = max(LE[0] + 0.15, 3.05)            # v2: no cards/labels until the spoken hook has landed (>= 3 s)
T_CARD = LE[15] + 0.3                      # final caption card (last ~2 s)
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

# ================================================================ emblems (hand-drawn, generic shapes)
GOLD, GOLD2, INK = (214, 176, 84), (150, 116, 40), (16, 16, 18)
TRED, TRED2 = (204, 30, 40), (150, 18, 26)
BMWBLUE = (30, 110, 200)
CHROME, CHROME2 = (214, 220, 228), (120, 128, 140)
def toyota(d, cx, cy, s=1.0, col=(236, 234, 228), w=8):
    """Three-oval mark (outer ring, horizontal and vertical inner ovals)."""
    for rx, ry, dy in ((70, 46, 0), (44, 18, -20), (20, 46, 2)):
        d.ell(cx, cy + dy * s, rx * s, ry * s, None, col, max(1.5, w * s))
def roundel(d, cx, cy, s=1.0):
    """Generic blue/white quartered roundel."""
    d.ell(cx, cy, 40 * s, 40 * s, (22, 22, 26), (200, 204, 210), max(1.5, 3 * s))
    d.ell(cx, cy, 27 * s, 27 * s, (255, 255, 255))
    d.d.pieslice(d.box(cx - 27 * s, cy - 27 * s, cx + 27 * s, cy + 27 * s), 180, 270, fill=BMWBLUE)
    d.d.pieslice(d.box(cx - 27 * s, cy - 27 * s, cx + 27 * s, cy + 27 * s), 0, 90, fill=BMWBLUE)

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

def wheel(d, wx, wy, r, caliper, rim=(48, 50, 56), face=(170, 174, 182), n=10):
    d.ell(wx, wy, r, r, (20, 20, 24))
    d.ell(wx, wy, r * .9, r * .9, None, (44, 44, 50), max(2, r * .06))
    d.ell(wx, wy, r * .7, r * .7, (66, 68, 74))                         # brake disc behind the spokes
    if caliper: d.chord(wx, wy, r * .64, r * .64, 200, 290, caliper)
    d.ell(wx, wy, r * .7, r * .7, None, rim, max(3, r * .1))
    for a in range(n):
        ra = math.radians(a * 360 / n + 18)
        d.line([(wx + r * .13 * math.cos(ra), wy + r * .13 * math.sin(ra)),
                (wx + r * .66 * math.cos(ra + .08), wy + r * .66 * math.sin(ra + .08))], face if a % 2 == 0 else rim, max(2, r * .08))
    d.ell(wx, wy, r * .16, r * .16, rim, (90, 94, 102), 2)

# outline: (u along length, h above ground as a fraction of length)
SUPRA_CTRL = [(0.0, .085), (.004, .132), (.03, .160), (.10, .180), (.19, .208), (.27, .210), (.33, .224), (.385, .240),
              (.455, .292), (.53, .316), (.60, .311), (.67, .288), (.73, .262), (.79, .258), (.87, .234), (.94, .236),
              (.962, .224), (.988, .18), (1.0, .12), (.997, .075), (.975, .055), (.94, .05), (.07, .05), (.03, .055), (.006, .065)]
Z4_CTRL = [(0.0, .085), (.006, .14), (.04, .166), (.14, .188), (.27, .212), (.40, .236), (.60, .238), (.80, .240), (.93, .238),
           (.975, .218), (.997, .17), (1.0, .11), (.995, .072), (.97, .055), (.94, .05), (.07, .05), (.03, .055), (.006, .066)]
MK4_CTRL = [(0.0, .08), (.006, .125), (.05, .158), (.17, .183), (.30, .205), (.38, .218), (.455, .282), (.54, .301), (.63, .296),
            (.72, .262), (.82, .232), (.93, .224), (.985, .205), (1.0, .13), (.997, .072), (.975, .055), (.94, .05), (.07, .05),
            (.03, .055), (.006, .062)]
def coupe(d, x0, ground, L, kind, col):
    """GR Supra (A90) / BMW Z4 (G29, roof down) / previous Supra (A80) side profile, front to the left."""
    def P(u, h): return (x0 + u * L, ground - h * L)
    hi = tuple(min(255, int(c * 1.08) + 16) for c in col); lo = tuple(int(c * .74) for c in col)
    ctrl, wheels, r = {'supra': (SUPRA_CTRL, (.19, .765), .079), 'z4': (Z4_CTRL, (.19, .78), .081),
                       'mk4': (MK4_CTRL, (.18, .785), .072)}[kind]
    d.ell(x0 + L * .5, ground + 4, L * .56, 14, (0, 0, 0, 90))
    if kind == 'z4':                                     # windscreen frame + headrests + stowed soft top
        d.poly([P(.40, .235), P(.468, .318), P(.484, .318), P(.43, .236)], (30, 30, 34), (24, 26, 34), 3)
        for u in (.555, .615):
            d.poly(spline([P(u - .03, .236), P(u - .02, .29), P(u + .015, .296), P(u + .03, .237)], 4), (32, 32, 36), (24, 26, 34), 3)
        d.poly(spline([P(.64, .236), P(.68, .262), P(.78, .262), P(.82, .238)], 4), (28, 28, 30), (24, 26, 34), 3)
    if kind == 'mk4':                                    # the big hoop wing
        for u in (.86, .95):
            d.poly([P(u, .22), P(u + .012, .22), P(u + .02, .278), P(u + .008, .278)], lo, (24, 26, 34), 3)
        d.poly(spline([P(.83, .276), P(.92, .29), P(1.0, .288), P(1.0, .272), P(.92, .27), P(.83, .264)], 4), col, (24, 26, 34), 3)
    body = spline([P(u, h) for u, h in ctrl], 6)
    shade(d, body, hi, lo, ground - .30 * L, ground - .06 * L)
    d.line(spline([P(.05, .150), P(.30, .19), P(.55, .205), P(.85, .205)], 6, closed=False), (255, 255, 255, 170), 3)
    d.line(spline([P(.08, .139), P(.5, .147), P(.93, .155)], 6, closed=False), lo, 3)
    for u in wheels:                                     # arches
        wx, wy = P(u, r)
        d.chord(wx, wy, r * L * 1.2, r * L * 1.2, 180, 360, (14, 14, 16))
        d.rect(wx - r * L * 1.2, wy - 2, wx + r * L * 1.2, ground - 6, (14, 14, 16))
    d.poly(body, None, (24, 26, 34), 5)
    if kind != 'z4':
        gl = [(.40, .243), (.458, .287), (.53, .302), (.60, .297), (.665, .276), (.712, .252), (.56, .248)] if kind == 'supra' else \
             [(.395, .222), (.458, .278), (.54, .29), (.625, .285), (.70, .258), (.73, .235), (.55, .226)]
        g = spline([P(*q) for q in gl], 4)
        shade(d, g, (86, 106, 130), (16, 20, 30), ground - .30 * L, ground - .24 * L)
        d.poly(g, None, (20, 22, 28), 4)
        d.poly([P(.45, .25), P(.49, .287), P(.515, .29), P(.48, .25)], (255, 255, 255, 50))
        d.line([P(.585, .30), P(.605, .249)], (20, 20, 24), 6)
    else:
        d.poly([P(.42, .236), P(.47, .31), P(.474, .31), P(.44, .236)], (120, 150, 170, 180))
    d.line([P(.375, .235), P(.37, .15), P(.385, .07)], lo, 3)                      # door cut, handle, mirror
    d.line([P(.66, .24), P(.665, .15), P(.64, .07)], lo, 3)
    d.rect(*P(.565, .212), *P(.605, .203), lo, r=2)
    d.poly(spline([P(.395, .248), P(.435, .238), P(.44, .26), P(.40, .262)], 4), (24, 24, 28), (24, 26, 34), 3)
    if kind == 'supra':
        d.poly(spline([P(.012, .150), P(.06, .168), P(.14, .181), P(.11, .163), P(.04, .142)], 4), (30, 32, 38), (24, 26, 34), 3)
        d.line([P(.03, .152), P(.10, .168)], (240, 245, 255), 3)
        d.poly([P(.005, .07), P(.08, .075), P(.10, .11), P(.02, .115)], (22, 22, 26), (24, 26, 34), 3)
        d.poly([P(.28, .17), P(.30, .175), P(.27, .11), P(.255, .108)], (22, 22, 26))
        d.poly([P(.955, .205), P(.99, .19), P(.995, .175), P(.95, .19)], (200, 30, 36), (24, 26, 34), 3)
    elif kind == 'z4':
        d.poly(spline([P(.015, .150), P(.05, .170), P(.11, .182), P(.09, .158), P(.04, .138)], 4), (30, 32, 38), (24, 26, 34), 3)
        d.line([P(.03, .15), P(.09, .172)], (240, 245, 255), 3)
        d.poly([P(0.0, .10), P(.03, .10), P(.03, .135), P(.006, .135)], (20, 20, 24), (60, 62, 68), 3)
        for i in range(3):
            d.line([P(.27 + i * .018, .175), P(.254 + i * .018, .12)], (22, 22, 26), 3)
        d.poly([P(.95, .225), P(.99, .205), P(.997, .18), P(.95, .2)], (200, 30, 36), (24, 26, 34), 3)
    else:
        d.poly(spline([P(.01, .135), P(.06, .160), P(.12, .172), P(.09, .15), P(.03, .128)], 4), (220, 225, 235), (24, 26, 34), 3)
        d.poly([P(.01, .07), P(.10, .075), P(.10, .10), P(.015, .105)], (22, 22, 26))
        d.poly([P(.94, .215), P(.995, .2), P(.998, .17), P(.94, .18)], (230, 60, 50), (24, 26, 34), 3)
    d.line([P(.25, .052), P(.70, .052)], (20, 20, 24), 5)
    for u in wheels:
        wx, wy = P(u, r)
        wheel(d, wx, wy, r * L, TRED if kind == 'supra' else (70, 74, 90) if kind == 'z4' else None,
              face=(170, 174, 182) if kind != 'mk4' else (214, 216, 222), n=10 if kind != 'mk4' else 5)

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

NPC['clerk'] = cast('e0b090', '5a3a22', 'c8202c', pants='2a2a30', shirt='f4f4f6', style='messy')
NPC['worker1'] = cast('c58c64', '2b1d16', '3a5a8a', pants='3a5a8a', shirt='3a5a8a', style='messy')
NPC['worker2'] = cast('f0c9a8', 'b04a2a', '3a5a8a', pants='3a5a8a', shirt='3a5a8a', style='part')

# ---- the comment-bait gag, parts counter (never mentioned): a cat on the top shelf paws boxes off the edge.
# The parts clerk catches the first two without looking up; the third lands on his head.
SHELF_Y, BOX_X, CAT_X, CLERK_X, CLERK_FY, CLERK_S = 536, 900, 978, 912, 1186, .45
GRAV = 3600
def drops(): return [T_S2 + 1.3, T_S2 + 4.3, T_S2 + 7.5]
def cat(d, x, y, t, push=0.0, col=(236, 150, 60), s=1.0):
    """Sitting ginger cat facing left; push 0..1 reaches its paw out to the left."""
    tail = math.sin(t * 3) * 14 * s
    tl = spline([(x + 30 * s, y - 10 * s), (x + 62 * s, y - 30 * s), (x + 66 * s + tail, y - 72 * s)], 5, closed=False)
    d.line(tl, OL, 14 * s); d.line(tl, col, 8 * s)
    d.ell(x + 10 * s, y - 34 * s, 36 * s, 34 * s, col, OL, 3.5)
    paw = 50 * push * s
    d.line([(x - 6 * s, y - 30 * s), (x - 20 * s - paw, y - 10 * s - 8 * push * s)], OL, 17 * s)
    d.line([(x - 6 * s, y - 30 * s), (x - 20 * s - paw, y - 10 * s - 8 * push * s)], col, 10 * s)
    hx, hy = x - 14 * s, y - 78 * s
    for sd in (-1, 1):
        d.poly([(hx + sd * 10 * s, hy - 16 * s), (hx + sd * 24 * s, hy - 36 * s), (hx + sd * 26 * s, hy - 8 * s)], col, OL, 3)
    d.ell(hx, hy, 28 * s, 24 * s, col, OL, 3.5)
    for sd in (-1, 1):
        if push > .5: d.line([(hx - 6 * s + sd * 11 * s - 5 * s, hy - 2 * s), (hx - 6 * s + sd * 11 * s + 5 * s, hy - 2 * s)], OL, 3)
        else: d.ell(hx - 6 * s + sd * 11 * s, hy - 2 * s, 4 * s, 6 * s, OL)
    d.ell(hx - 7 * s, hy + 8 * s, 4 * s, 3 * s, (230, 120, 130))
    for k in (-1, 1):
        d.line([(hx - 22 * s, hy + 6 * s), (hx - 42 * s, hy + 6 * s + k * 5 * s)], OL, 1.6)
    for i in range(3):
        d.line([(x - 4 * s + 14 * i * s, y - 52 * s), (x + 2 * s + 14 * i * s, y - 30 * s)], (196, 112, 40), 4 * s)

def box(d, cx, by, w=74, h=58, col=(196, 152, 98), rot=0):
    d.rect(cx - w / 2, by - h, cx + w / 2, by, col, r=3, ol=OL, w=3.5)
    d.rect(cx - w * .12, by - h, cx + w * .12, by - h * .45, (216, 176, 120))
    d.rect(cx - w * .36, by - h * .40, cx + w * .10, by - h * .14, (250, 250, 248), r=2)
    for i in range(6):
        xx = cx - w * .32 + i * w * .065
        d.line([(xx, by - h * .36), (xx, by - h * .18)], OL, 1.6 if i % 2 else 2.6)

def parts_life(img, t):
    ds = drops()
    hit = ds[2] + math.sqrt(2 * (CLERK_FY - 995 * CLERK_S - SHELF_Y) / GRAV)
    catch = [d_ + math.sqrt(2 * (CLERK_FY - 1020 * CLERK_S - SHELF_Y) / GRAV) for d_ in ds[:2]]
    up = any(c - .35 < t < c + .6 for c in catch)
    dazed = t >= hit
    st = mk('up' if up else 'clasp', 'up' if up else 'clasp', look=-1 if not up else 0, brows='up' if dazed else 'flat',
            eyes='wide' if dazed else '', smile=-1 if dazed else 0)
    st['blink'] = (not dazed) and (t % 3.3) < .12
    st['dy'] = 4 * math.sin(t * 2)
    npc(img, CLERK_X, CLERK_FY, CLERK_S, NPC['clerk'], st)
    img.paste(bg_parts().crop((0, 930 * K, W * K, 1200 * K)), (0, 930 * K))      # counter in front of the clerk
    d = D(img)
    if dazed and t < hit + 3.5: stars(d, CLERK_X, CLERK_FY - 1010 * CLERK_S, t, 1.4)
    for i, d0 in enumerate(ds):                             # caught boxes stack up on the counter
        if i < 2 and t > catch[i] + .6: box(d, 760 + i * 4, 930 - i * 58)
    push = max([clamp(1 - abs(t - (d0 - .1)) / .25) for d0 in ds] + [0])
    nxt = next((i for i, d0 in enumerate(ds) if t < d0), None)
    if nxt is not None: box(d, BOX_X, SHELF_Y)
    cat(d, CAT_X, SHELF_Y, t, push, s=.9)
    for i, d0 in enumerate(ds):
        if t < d0: continue
        ft = t - d0
        y = SHELF_Y + .5 * GRAV * ft * ft
        if i < 2:
            yc = CLERK_FY - 1020 * CLERK_S
            if y < yc: box(d, BOX_X, y)
            elif t < catch[i] + .6: box(d, BOX_X + 6, yc + 6)
        else:
            yh = CLERK_FY - 995 * CLERK_S
            if y < yh: box(d, BOX_X + 4, y)
            else:
                bt = t - hit
                by = yh - 150 * bt + .5 * GRAV * bt * bt
                if by < 930: box(d, BOX_X + 4 + 170 * bt, by)
    # counter-top props: a window motor and a switch panel
    d.rect(150, 880, 340, 926, (80, 84, 92), r=6, ol=OL, w=3)
    for i in range(3): d.rect(168 + i * 58, 892, 210 + i * 58, 914, (30, 30, 36), r=4, ol=(120, 124, 130), w=2)
    d.ell(560, 894, 30, 30, (150, 154, 160), OL, 3); d.rect(560, 882, 680, 906, (120, 124, 130), r=4, ol=OL, w=3)

LINE_CARS = [('supra', (240, 240, 238), 'SUPRA'), ('z4', (40, 92, 172), 'Z4'), ('supra', (196, 30, 34), 'SUPRA'),
             ('z4', (240, 240, 238), 'Z4'), ('supra', (40, 44, 52), 'SUPRA'), ('z4', (150, 30, 40), 'Z4')]
def factory_life(img, t):
    tau = t - T_S3
    sp, gap, L = 52, 400, 330
    d = D(img)
    for i, (kind, col, lab) in enumerate(LINE_CARS):        # both cars come down the same line
        x = (i * gap + tau * sp) % (gap * len(LINE_CARS)) - 380
        if -380 < x < W + 40:
            d.line([(x + L / 2, 560), (x + L / 2, 690)], (60, 60, 66), 4)
            d.rect(x + L / 2 - 84, 690, x + L / 2 + 84, 744, (255, 255, 255), r=8, ol=OL, w=3)
            d.text(x + L / 2, 718, lab, 40, TRED if lab == 'SUPRA' else BMWBLUE)
            paste_car(img, kind, x, 924, L, col)
            d = D(img)
    for rx, ph, side in ((96, 0.0, 1), (1000, 1.4, -1)):    # welding robots
        a = math.sin((t + ph) * 2.2) * .35
        sx, sy = rx, 892
        ex, ey = sx + side * math.sin(.5 + a) * 150, sy - math.cos(.5 + a) * 150
        hx, hy = ex + side * math.sin(1.6 - a) * 130, ey + math.cos(1.6 - a) * 50
        d.rect(rx - 46, 900, rx + 46, 932, (60, 62, 66), r=4, ol=OL, w=3)
        d.line([(sx, sy), (ex, ey)], OL, 44); d.line([(sx, sy), (ex, ey)], (240, 120, 30), 36)
        d.line([(ex, ey), (hx, hy)], OL, 34); d.line([(ex, ey), (hx, hy)], (240, 120, 30), 26)
        d.ell(ex, ey, 22, 22, (70, 70, 74), OL, 3); d.ell(sx, sy, 26, 26, (70, 70, 74), OL, 3)
        if (t * 5 + ph) % 1 < .55:
            for j in range(6):
                ang = j * 1.05 + t * 13
                d.line([(hx, hy), (hx + math.cos(ang) * 28, hy + math.sin(ang) * 28)], (255, 220, 90), 3)
    for x, cfg, ph in ((300, 'worker1', 0), (640, 'worker2', 1.7)):   # line workers with tablets
        st = mk('rest', (-46, -128), look=-1 if x > 400 else 1, brows='flat', prop={'rpose': 'phone'})
        st['blink'] = ((t + ph) % 3.5) < .12; st['dy'] = 3 * math.sin(t * 2 + ph)
        npc(img, x, 958, .30, NPC[cfg], st)

@lru_cache(None)
def car_layer(kind, L, col):
    img = Image.new('RGBA', (int(L * 1.2) * K, int(L * .5) * K), (0, 0, 0, 0))
    coupe(D(img, ox=-L * .1, oy=-L * .42), 0, 0, L, kind, col)
    return img
def paste_car(img, kind, x0, ground, L, col):
    c = car_layer(kind, L, col)
    img.paste(c, (int((x0 - L * .1) * K), int((ground - L * .42) * K)), c)

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
    for x in range(-40, W, 170):                          # tall wall panels with a red trim line
        d.poly([(x + 8, 80), (x + 160, 80), (x + 160, WALL_Y - 40), (x + 8, WALL_Y - 40)], (28, 28, 32))
        for yy in range(120, WALL_Y - 60, 110):
            d.line([(x + 30, yy), (x + 138, yy)], (40, 40, 46), 3)
        d.line([(x + 8, 80), (x + 8, WALL_Y - 40)], (90, 30, 34), 2)
    for px in (150, 459, 768):                            # pendant lights
        d.line([(px, 0), (px, 70)], (70, 74, 78), 3)
        d.chord(px, 92, 46, 28, 180, 360, (52, 52, 56))
        d.ell(px, 92, 30, 6, (255, 240, 200))
    d.rect(0, WALL_Y - 8, W, WALL_Y, TRED)
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], (214, 216, 219), 2)
    img = spot(img, CX, 120, 70, 470, 800)
    d = D(img)
    toyota(d, CX - 40, 196, .95, (236, 234, 228), 9)
    d.text(CX + 92, 192, 'GR', 56, TRED)
    d.text(CX, 300, 'T O Y O T A', 44, (236, 234, 228), path=FONT_X)
    d.ell(CX, 905, 400, 50, (14, 16, 16))                 # turntable
    d.ell(CX, 897, 394, 44, (46, 46, 50), TRED, 5)
    d.ell(CX, 897, 340, 34, (60, 60, 64))
    return img

@lru_cache(None)
def bg_parts():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (196, 205, 200), (168, 178, 174)), grad((H - WALL_Y) * K, W * K, (190, 188, 182), (214, 212, 206))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, 40, (70, 76, 80))
    for x in (200, 540, 880):
        d.rect(x - 120, 40, x + 120, 56, (250, 250, 236), r=4, ol=OL, w=2)
    rng = np.random.default_rng(4)
    for bx in (10, 360, 710):                             # steel shelving full of parts boxes
        d.rect(bx, 90, bx + 340, 930, (110, 118, 126), ol=OL, w=3)
        d.rect(bx + 10, 100, bx + 330, 930, (74, 80, 88))
        for sy in (300, SHELF_Y, 760):
            for j in range(int(rng.integers(2, 4))):
                bw, bh = int(rng.integers(64, 100)), int(rng.integers(48, 90))
                bxx = bx + 56 + j * 100 + int(rng.integers(0, 10))
                if bx == 710 and sy == SHELF_Y and bxx > 840: continue      # the cat's spot stays clear
                box(d, bxx, sy, bw, bh, col=[(196, 152, 98), (178, 136, 88), (210, 170, 118)][j % 3])
            d.rect(bx, sy, bx + 340, sy + 14, (140, 148, 156), ol=OL, w=3)
    d.rect(-10, 930, W + 10, 1200, (64, 72, 84), ol=OL, w=4)             # parts counter
    d.rect(-10, 916, W + 10, 940, (210, 214, 218), ol=OL, w=4)
    d.rect(300, 990, 620, 1060, (204, 30, 40), r=8)
    d.text(460, 1026, 'PARTS', 44, (255, 255, 255))
    return img

@lru_cache(None)
def bg_factory():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (150, 160, 168), (196, 202, 206)), grad((H - WALL_Y) * K, W * K, (178, 180, 182), (206, 208, 210))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(0, W, 180):                            # roof lights + trusses
        d.rect(x + 14, 40, x + 166, 150, (206, 226, 238), r=2, ol=OL, w=3)
        d.line([(x + 90, 40), (x + 90, 150)], (120, 130, 138), 4)
    d.line([(0, 160), (W, 160)], (80, 86, 92), 10)
    for x in range(0, W + 90, 90):
        d.line([(x, 160), (x + 45, 200), (x + 90, 160)], (80, 86, 92), 5)
    d.line([(0, 200), (W, 200)], (80, 86, 92), 8)
    for x in (130, 540, 950):
        d.line([(x, 200), (x, 250)], (40, 40, 44), 3)
        d.poly([(x - 40, 274), (x - 16, 250), (x + 16, 250), (x + 40, 274)], (230, 180, 40), OL, 3)
        d.ell(x, 276, 34, 7, (255, 248, 220))
    d.rect(0, 540, W, 560, (90, 96, 104))                 # overhead rail for the plates
    d.rect(250, 448, 830, 528, (34, 38, 46), r=8, ol=OL, w=3)              # hall sign with the Austrian flag
    for i, c in enumerate(((237, 41, 57), (255, 255, 255), (237, 41, 57))):
        d.rect(272, 462 + i * 17, 340, 479 + i * 17, c)
    d.text(580, 489, 'GRAZ · AUSTRIA', 46, (255, 255, 255))
    d.rect(0, 928, W, 962, (60, 62, 66), ol=OL, w=3)                      # conveyor + safety stripes
    for x in range(-40, W + 40, 60):
        d.poly([(x, 962), (x + 30, 962), (x + 60, 988), (x + 30, 988)], (240, 196, 40))
    for y in range(1100, H, 210):
        d.line([(0, y), (W, y + 20)], (190, 192, 194), 3)
    return img

# ================================================================ characters (tesla-locked cast, unchanged)
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
        toyota(d, x + 73, top + 105, 0.2, TRED, 3)
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
            (T_BMW0 - .1, 'up', 'point', dict(brows='angry', eyes='wide')),
            (LS[1], 'hip', 'rest', dict(brows='angry', smile=-1)),
            (LS[2] - .1, 'up', 'up', dict(brows='angry', eyes='wide', sweat=1)),
            (LE[2] + .2, 'cross', 'cross', dict(brows='angry', smile=-1)),
            (LS[4] - .1, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (LE[4] + .2, 'hip', 'rest', dict(brows='angry')),
            (T_GEAR, 'chin', 'rest', dict(brows='worried')),
            # scene 2: baffled
            (T_S2, 'hip', 'rest', dict(brows='angry')),
            (LS[6] - .1, 'rest', 'point', dict(brows='up', eyes='wide')),
            (LE[6] + .2, 'cross', 'cross', dict(brows='angry', smile=-1)),
            (T_PARK, 'head', 'head', dict(brows='up', eyes='wide')),
            (LS[8] - .1, 'shrug', 'shrug', dict(brows='worried', eyes='wide')),
            (LE[8] + .2, 'chin', 'rest', dict(brows='worried')),
            # scene 3: baffled -> deflating
            (T_S3, 'rest', 'rest', dict(brows='worried')),
            (LS[10] - .1, 'rest', 'open', dict(brows='worried')),
            (LE[10] + .2, 'chin', 'rest', dict(brows='worried')),
            (LS[12] - .1, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (LE[12] + .2, 'head', 'head', dict(brows='worried', smile=-1, tired=0.3)),
            # scene 4: resigned
            (T_S4, 'rest', 'rest', dict(brows='worried', tired=0.5, smile=-1)),
            (LS[14] + .1, 'rest', 'open', dict(brows='flat', tired=0.5)),
            (LE[14] + .2, 'rest', 'rest', dict(brows='flat', tired=0.5)),
            (T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    for ln, pose in ((1, 'open'), (3, 'open'), (5, 'open'), (7, 'present'), (9, 'open'), (11, 'present'), (13, 'open')):
        s += [(LS[ln] - .05, pose, 'clasp', {}), (LE[ln] + .1, 'clasp', 'clasp', {})]
    s += [(T_FINAL, 'open', 'clasp', dict(look=0)), (LE[15] + .3, 'clasp', 'clasp', dict(look=0))]
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
WHITE = (240, 240, 238)
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    if sc in (0, 3):
        img = bg_showroom().copy()
        showroom_life(img, t, sc)
        paste_car(img, 'supra', CX - 300, 894, 600, WHITE)
    elif sc == 1:
        img = bg_parts().copy()
        parts_life(img, t)
    else:
        img = bg_factory().copy()
        factory_life(img, t)
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
        if who == 'B' and LS[2] <= t <= LE[2]:               # real heat: hopping on the spot
            st['dy'] -= abs(math.sin((t - LS[2]) * 9)) * 14
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
        punches = ((T_BMW0, .05), (T_TOY2, .05), (T_PLAT, .03), (T_GEAR, .03))
        if LS[2] <= t <= LE[2]:
            sx, sy = math.sin(t * 61) * 7, math.cos(t * 47) * 5
    elif sc == 1:
        z = 1.05 + 0.015 * io(prog(t, t0, 10))
        sx = 46 * (1 - oc(prog(t, t0, 1.6)))               # settle after the whip
        punches = ((T_SW, .04), (T_ALL, .03), (T_TDO, .03))
    elif sc == 2:
        z = 1.02 + 0.04 * io(prog(t, t0, 8))
        punches = ((T_AUS, .03), (T_SOBMW, .05), (T_SAYS, .03))
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        punches = ((T_REAL, .03),)
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
    ph = Image.open(os.path.join(HERE, '..', '..', 'supra-z4', 'assets', name)).convert('RGB')
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

def panel(d, x0, y0, x1, y1, a, col=(14, 16, 22)):
    d.rect(x0, y0, x1, y1, col + (int(236 * a),), r=30)

FINAL = [("Real Supra", 92, TAG), ("or BMW?", 92, TAG), ("Comment below.", 70, (255, 255, 255)),
         ("Next: another car", 64, (210, 214, 224)), ("that's secretly", 64, (210, 214, 224)), ("another car.", 64, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 400, 104
PARTS = [("Window motors:", "BMW", 'T_WIN'), ("Lock switches:", "BMW", 'T_LOCK'), ("Parking brake switch:", "BMW", 'T_PARK')]
TOYO = [("Suspension tuning:", "TOYOTA", 'T_SUSP'), ("Body:", "TOYOTA", 'T_BODY')]
SHARED = [("ENGINE", 'T_WHAT'), ("PLATFORM", 'T_PLAT'), ("GEARBOX", 'T_GEAR')]
ONSCREEN = (['TOYOTA GR SUPRA', 'BMW Z4', 'BMW?!', '=', 'BMW B58', 'TOYOTA 2JZ', 'OLD SUPRA · ENGINE', 'NEW GR SUPRA · ENGINE',
             'VS', 'SHARED WITH THE BMW Z4', 'ENGINE', 'PLATFORM', 'GEARBOX', 'BMW', 'THE PARTS', 'WHAT TOYOTA DID',
             'TOYOTA', 'Built in Graz, Austria,', 'next to the BMW Z4', 'BMW?', 'SUPRA', 'Z4', 'REAL SUPRA?', 'GR',
             'T O Y O T A', 'PARTS', 'GRAZ · AUSTRIA'] + [a + ' ' + b for a, b, _ in PARTS + TOYO] + [f[0] for f in FINAL])

def row(d, x, y, label, chip, chipcol, al, maxw=740, size=52):
    """'Label: CHIP' on one line, label white, chip as a coloured pill; shrinks to fit but never below 48 px."""
    while size > 48 and font(size).getlength(label) + font(size).getlength(chip) + 60 > maxw: size -= 1
    d.text(x, y, label, size, (255, 255, 255, al), anchor='lm')
    cx0 = x + font(size).getlength(label) + 18; cw = font(size).getlength(chip) + 28
    d.rect(cx0, y - size * .62, cx0 + cw, y + size * .62, chipcol + (al,), r=12)
    d.text(cx0 + cw / 2, y + 2, chip, size, (255, 255, 255, al))

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    if sc == 0:
        # the user's photos: the GR Supra, then the BMW Z4 it is built with
        pa = window(t, T_HOOK, LS[2] - .05, .1, .3)
        if pa > 0:
            used = True
            put(img, photo_card('toyota_supra.jpg', 'TOYOTA GR SUPRA', TRED, (255, 255, 255), 380), 683, 450, popin(t, T_HOOK, .35), pa, rot=-4)
            if t >= T_HOOK + .25:
                put(img, photo_card('bmw_z4.jpg', 'BMW Z4', (230, 232, 236), (24, 24, 30), 380), 236, 470, popin(t, T_HOOK + .25, .35), pa, rot=4)
            if t >= max(LS[1], T_HOOK + .5):
                k_ = popin(t, max(LS[1], T_HOOK + .5), .3); d = D(img)
                d.ell(459, 460, 46 * k_, 46 * k_, GREEN + (int(250 * pa),), (14, 40, 24, int(255 * pa)), 5)
                d.text(459, 462, '=', 70 * max(k_, .05), (255, 255, 255, int(255 * pa)))
                k2 = popin(t, max(LS[1], T_HOOK + .5) + .25, .3)
                d.rect(459 - 150 * k2, 650, 459 + 150 * k2, 716, TAG + (int(250 * pa),), r=12)
                if k2 > .6: d.text(459, 684, 'BMW B58', 50, (24, 22, 20, int(255 * pa)))
        sa = window(t, T_HOOK + .35, T_HOOK + 1.4, .05, .3)
        if sa > 0:
            used = True
            s = 1 + 1.1 * (1 - oc(prog(t, T_HOOK + .35, .14)))
            put(img, stamp_img('BMW?!', RED), 690, 548, s * .62, sa, rot=-10)
        ta = window(t, T_OLD - .05, LS[4] - .05, .15, .3)
        if ta > 0:                                           # old engine vs new engine
            used = True
            s = popin(t, T_OLD, .35)
            sw = math.sin((t - T_OLD) * 6) * 4 * math.exp(-(t - T_OLD) * 2)
            put(img, price_tag('TOYOTA 2JZ', 'OLD SUPRA · ENGINE', (232, 234, 238), 620), CX, 415, s, ta, rot=sw)
            if t >= LS[3] - .05:
                s2 = popin(t, LS[3] - .05, .3)
                sw2 = math.sin((t - LS[3]) * 7) * 5 * math.exp(-(t - LS[3]) * 2.4)
                put(img, price_tag('BMW B58', 'NEW GR SUPRA · ENGINE', TAG, 620), CX, 610, s2 * .92, ta, rot=sw2)
                d = D(img)
                d.ell(CX, 512, 34, 34, (24, 24, 30, int(255 * ta)), (255, 255, 255, int(255 * ta)), 4)
                d.text(CX, 513, 'VS', 30, (255, 255, 255, int(255 * ta)))
        ca = window(t, LS[4] - .05, T_S2 + .05, .25, .25)
        if ca > 0:                                           # what else is shared
            used = True
            al = int(255 * ca)
            panel(d, 56, 116, 862, 476, ca)
            d.text(CX, 172, 'SHARED WITH THE BMW Z4', 48, TAG + (al,))
            d.line([(90, 210), (828, 210)], (70, 74, 84, al), 3)
            for i, (lab, tn) in enumerate(SHARED):
                tl = globals()[tn]
                if t < tl - .05: continue
                ra = int(al * prog(t, tl - .05, .2)); y = 266 + i * 82
                k_ = popin(t, tl - .05, .3)
                d.text(100, y, lab, 54 * max(k_, .3), (255, 255, 255, ra), anchor='lm')
                d.rect(640, y - 32, 820, y + 32, BMWBLUE + (ra,), r=12)
                d.text(730, y + 2, 'BMW', 50 * max(k_, .3), (255, 255, 255, ra))
    elif sc == 1:
        ca = window(t, T_SW - .05, LS[8] - .05, .25, .25)
        if ca > 0:
            used = True
            al = int(255 * ca)
            panel(d, 50, 116, 868, 436, ca)
            d.text(CX, 170, 'THE PARTS', 48, TAG + (al,))
            d.line([(84, 208), (834, 208)], (70, 74, 84, al), 3)
            for i, (a_, b_, tn) in enumerate(PARTS):
                tl = globals()[tn]
                if t < tl - .05: continue
                ra = int(al * prog(t, tl - .05, .15))
                row(d, 84, 262 + i * 76, a_, b_, BMWBLUE, ra, 750)
        ta = window(t, LS[8] - .05, T_S3 + .05, .25, .25)
        if ta > 0:
            used = True
            al = int(255 * ta)
            panel(d, 50, 116, 868, 360, ta)
            d.text(CX, 170, 'WHAT TOYOTA DID', 48, (255, 130, 130, al))
            d.line([(84, 208), (834, 208)], (70, 74, 84, al), 3)
            for i, (a_, b_, tn) in enumerate(TOYO):
                tl = globals()[tn]
                if t < tl - .05: continue
                row(d, 84, 262 + i * 76, a_, b_, TRED, int(al * prog(t, tl - .05, .15)), 750)
    elif sc == 2:
        ca = window(t, T_AUS - .08, T_S4 + .05, .25, .25)
        if ca > 0:
            used = True
            al = int(255 * ca)
            panel(d, 50, 116, 868, 340, ca)
            for i, c in enumerate(((237, 41, 57), (255, 255, 255), (237, 41, 57))):
                d.rect(84, 150 + i * 16, 156, 166 + i * 16, c + (al,))
            d.text(176, 174, 'Built in Graz, Austria,', 54, (255, 255, 255, al), anchor='lm')
            hl = TAG if t >= T_Z4 - .05 else (255, 255, 255)
            d.text(84, 278, 'next to the BMW Z4', 66, hl + (al,), anchor='lm')
        sa = window(t, T_SOBMW - .05, T_SAYS - .05, .05, .2)
        if sa > 0:
            used = True
            s = 1 + 1.1 * (1 - oc(prog(t, T_SOBMW - .05, .14)))
            put(img, stamp_img('BMW?', BMWBLUE), CX, 640, s * .7, sa, rot=-8)
        sb = window(t, T_SAYS - .05, T_S4 + .05, .05, .25)
        if sb > 0:
            used = True
            s = 1 + 1.1 * (1 - oc(prog(t, T_SAYS - .05, .14)))
            put(img, stamp_img('SUPRA', TRED), CX, 640, s * .7, sb, rot=6)
    else:
        ta = window(t, LS[14] - .05, T_CARD, .15, .3)
        if ta > 0:
            used = True
            s = popin(t, LS[14] - .05, .35)
            put(img, price_tag('REAL SUPRA?', 'TOYOTA GR SUPRA', TAG, 620), CX, 430, s, ta,
                rot=math.sin((t - LS[14]) * 6) * 4 * math.exp(-(t - LS[14]) * 2))
    if t >= T_CARD:                                          # final caption
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(FINAL):
            k_ = popin(t, T_CARD + .06 * i, .3)
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
    outside = lpf(rng.standard_normal(n), 300) * 1.0 * (0.7 + 0.3 * np.sin(T_ * .7)) + lpf(rng.standard_normal(n), 25) * .03
    board = lpf(rng.standard_normal(n), 90) * 0.07 + 0.006 * np.sin(2 * np.pi * 60 * T_) + 0.003 * np.sin(2 * np.pi * 120 * T_)
    bed = room * (env(-1, T_S2) + env(T_S4, DUR + 1)) + board * env(T_S2, T_S3) + outside * .6 * env(T_S3, T_S4)
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
    add(T_HOOK, sfx.pop(), .35); add(T_HOOK + .35, sfx.stamp(), .55)
    add(LS[1], sfx.pop(), .25); add(LS[1] + .25, sfx.ding(1320, .6), .14)
    add(T_OLD - .05, sfx.whoosh(), .3); add(T_TOY2, sfx.thump(), .3); add(LS[3] - .05, sfx.pop(), .3)
    add(LS[4] - .05, sfx.whoosh(.35, 14), .25)
    for tt_ in (T_WHAT, T_PLAT, T_GEAR): add(tt_, sfx.pop(), .32)
    for s_ in SCENES[1:]:                                   # scene-change accent: whoosh + soft thump
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
    add(T_SW - .05, sfx.pop(), .3)
    for tt_ in (T_WIN, T_LOCK, T_PARK): add(tt_, sfx.pop(), .32)
    add(T_ALL, sfx.ding(1568, .5), .14)
    add(LS[8] - .05, sfx.whoosh(.35, 14), .25); add(T_SUSP, sfx.pop(), .3); add(T_BODY, sfx.pop(), .3)
    for k_ in range(6): add(T_S3 + .4 + k_ * 1.3, click(1800, 2600, .05), .12)      # welding robots (quiet)
    add(T_AUS - .08, sfx.ding(), .2); add(T_Z4, sfx.pop(), .3)
    add(T_SOBMW, sfx.stamp(), .45); add(T_SAYS, sfx.stamp(), .45)
    for k_ in range(3): add(T_S4 + .05 + k_ * .42, step(), .3)
    add(LS[14] - .05, sfx.pop(), .3)
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
