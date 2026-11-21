"""Shared engine for "The real [Brand] dealership experience" skits (1080x1920 @30). Lifted from bmw-heated-seats/src/render.py:
same cast (buyer/salesman), jointed poses, lip sync, word-by-word captions, camera punches, whip pans and loudness chain.
Episode files (EPDIR/scenes.py) supply sets, photo displays, cutaways, gags, cues and overrides."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sfx

W, H, FPS, K = 1080, 1920, 30, 2
CX = 459                                   # composition centre (left 85% of width)
WALL_Y, FEET_Y = 940, 1880
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'

# ---- episode + timeline from word timings
EPDIR = os.path.abspath(os.environ['EPDIR'])
sys.path.insert(0, EPDIR)
import script as SCRIPT
HERE = os.path.join(EPDIR, 'src')                          # photo_card() reads HERE/../assets
WORDS = json.load(open(os.path.join(EPDIR, 'words.json')))
LINES = {}
for _w in WORDS:
    LINES.setdefault(_w['line'], []).append(_w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
NL = len(LINES)
SCN = {li: SCRIPT.LINES[li][2] for li in range(NL)}
SC_FIRST = {}
for li in range(NL): SC_FIRST.setdefault(SCN[li], li)
NSC = len(SC_FIRST)
SCENES = [0.0] + [LS[SC_FIRST[sc]] - 0.42 for sc in sorted(SC_FIRST)[1:]]     # index i = scene i + 1
T_CARD = WORDS[-1]['e'] + 0.4                                 # final card (last ~2 s)
DUR = round(WORDS[-1]['e'] + 2.6, 2)
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
def speaking(t):
    for w in WORDS:
        if w['s'] - .08 <= t <= w['e'] + .12: return w['spk']
    return None
def last_line(t):
    k = [li for li in range(NL) if LS[li] - .05 <= t]
    return k[-1] if k else 0
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
BADGE = [lambda d, x, y: d.rect(x - 14, y - 7, x + 14, y + 7, (200, 30, 40), r=3)]   # episode replaces the dealer badge mark
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
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('1c1d22'), suit2=hexc('0e0f12'),
             shirt=hexc('f7f7fa'), tie=hexc('111114'), pants=hexc('1c1d22'), shoe=hexc('3a2a22'), glasses=False, hairstyle='part', lids=0.45)
OL = (26, 26, 46)
POSES = {'rest': (10, 323), 'clasp': (-100, 286), 'open': (120, 170), 'point': (235, 70), 'up': (70, -290),
         'head': (-92, -158), 'shrug': (128, 108), 'cross': (-176, 168), 'thanks': (-100, 92), 'raise1': (40, -230),
         'offer': (210, 120), 'chin': (-70, -110), 'hip': (90, 230), 'present': (240, -230), 'phone': (-46, -128), 'reach': (70, -250), 'show': (150, -140)}
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
        BADGE[0](d, x + 73, top + 105)
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
    ph = Image.open(os.path.join(EPDIR, 'assets', name)).convert('RGB')
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


@lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - CX) / (W * .62)) ** 2 + ((yy - 1100) / (H * .55)) ** 2)
    a = np.clip((r - .55) * 1.6, 0, 1) * 255
    return Image.fromarray(np.dstack([np.zeros((H, W, 3)), a]).astype(np.uint8), 'RGBA')



# ================================================================ episode hooks (render.py sets EP = scenes module)
EP = None

# ---- photos (Wikimedia Commons, see CREDITS.txt): cover-cropped, graded per episode, slow Ken Burns drift
@lru_cache(None)
def photo(name, w, h, k=K):
    ph = Image.open(os.path.join(EPDIR, 'assets', name)).convert('RGB')
    fx, fy = EP.FOCUS.get(name, (0.5, 0.5))
    Wp, Hp = int(w * k), int(h * k)
    s = max(Wp / ph.width, Hp / ph.height)
    ph = ph.resize((max(Wp, round(ph.width * s)), max(Hp, round(ph.height * s))), Image.LANCZOS)
    x0, y0 = int((ph.width - Wp) * fx), int((ph.height - Hp) * fy)
    return EP.grade(ph.crop((x0, y0, x0 + Wp, y0 + Hp)))

def display(img, name, x0, y0, w, h, t, t0=0.0, a=1.0, drift=1):
    """Paste a photo into a 1x box on the K-scale world with a slow sideways drift."""
    big = photo(name, int(w * 1.08), int(h * 1.08))
    k = io(clamp((t - t0) / 9.0))
    k = k if drift >= 0 else 1 - k
    ox, oy = int((big.width - w * K) * k), int((big.height - h * K) * .5)
    crop = big.crop((ox, oy, ox + int(w * K), oy + int(h * K)))
    pos = (int(x0 * K), int(y0 * K))
    if a >= .999: img.paste(crop, pos)
    elif a > 0: img.paste(crop, pos, Image.new('L', crop.size, int(255 * a)))

def show_seq(img, seq, box, t, t_scene):
    """seq = [(t_from, name), ...]; crossfades 0.25 s between entries."""
    x0, y0, w, h = box
    cur = [i for i, (tf, _) in enumerate(seq) if t >= tf] or [0]
    i = cur[-1]
    if i > 0 and t < seq[i][0] + .25:
        display(img, seq[i - 1][1], x0, y0, w, h, t, t_scene)
        display(img, seq[i][1], x0, y0, w, h, t, seq[i][0], io(prog(t, seq[i][0], .25)))
    else:
        display(img, seq[i][1], x0, y0, w, h, t, seq[i][0] if i else t_scene)

def screen_frame(d, x0, y0, x1, y1, bez=(18, 18, 20), glow=None):
    if glow: d.rect(x0 - 26, y0 - 26, x1 + 26, y1 + 26, glow, r=34)
    d.rect(x0 - 14, y0 - 14, x1 + 14, y1 + 14, bez, r=20)

@lru_cache(None)
def logo_img(name, h):
    lg = Image.open(os.path.join(EPDIR, 'assets', name)).convert('RGBA')
    s = h * K / lg.height
    return lg.resize((max(1, int(lg.width * s)), int(h * K)), Image.LANCZOS)

def paste_logo(img, name, cx, cy, h, a=1.0):
    lg = logo_img(name, h)
    if a < 1:
        lg = lg.copy(); lg.putalpha(lg.getchannel('A').point(lambda v: int(v * a)))
    img.paste(lg, (int(cx * K - lg.width / 2), int(cy * K - lg.height / 2)), lg)

# ---- shared car-cabin set (front view through the windscreen; road recedes in the rear window)
def cabin_base(roof, trim, seat):
    img = Image.new('RGB', (W * K, H * K), roof); d = D(img)
    d.poly([(110, 300), (808, 300), (860, 800), (60, 800)], (150, 190, 228))          # rear window (sky; road drawn live)
    d.rect(0, 0, W, 250, roof)
    d.poly([(0, 0), (130, 0), (110, 300), (60, 800), (0, 900)], trim)                 # C-pillars
    d.poly([(W, 0), (790, 0), (808, 300), (860, 800), (W, 900)], trim)
    d.rect(0, 790, W, H, seat)                                                      # rear bench
    for x in (130, 459, 788):
        d.rect(x - 90, 760, x + 90, 1000, mix(seat, (255, 255, 255), .08), r=40)
    return img

def road_life(img, t, speed, sky=(150, 190, 228), ground=(70, 74, 80), side=(108, 150, 96), vp=(459, 470), phase=0.0):
    """Road receding through the rear window. speed = scroll rate (0 = parked); phase = distance already driven."""
    lay = Image.new('RGB', img.size, sky); d = D(lay)
    d.rect(0, vp[1], W, 820, side)
    d.poly([(vp[0] - 8, vp[1]), (vp[0] + 8, vp[1]), (860, 820), (60, 820)], ground)
    for i in range(10):
        u = (i / 10 + phase) % 1.0
        y = vp[1] + (820 - vp[1]) * (1 - u) ** 2
        w_ = 2 + 16 * (1 - u) ** 2
        y2 = y - 4 - 30 * (1 - u) ** 2
        d.poly([(vp[0] - w_ * .5, y2), (vp[0] + w_ * .5, y2), (vp[0] + w_, y), (vp[0] - w_, y)], (240, 230, 160))
        for s in (-1, 1):                                       # trees / posts sliding away
            sx = vp[0] + s * (40 + 520 * (1 - u) ** 2)
            hh = 20 + 260 * (1 - u) ** 2
            d.rect(sx - 3 - 8 * (1 - u), y - hh, sx + 3 + 8 * (1 - u), y, (90, 70, 50))
            d.ell(sx, y - hh, 10 + 60 * (1 - u) ** 2, 10 + 50 * (1 - u) ** 2, (64, 120, 70))
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).polygon([(p * K, q * K) for p, q in [(110, 300), (808, 300), (860, 800), (60, 800)]], fill=255)
    img.paste(lay, (0, 0), mask)

def cabin_front(img, t, dash, accent, screen=None, wheel_x=262, roof_console=False, trim=(196, 160, 120), accent2=(200, 30, 40)):
    d = D(img)
    d.poly([(0, 1380), (W, 1380), (W, H), (0, H)], dash)
    d.rect(0, 1366, W, 1392, mix(dash, (255, 255, 255), .15), r=10)
    d.poly([(0, 0), (70, 0), (40, 1390), (0, 1390)], mix(dash, (0, 0, 0), .2))      # A-pillars (windscreen frame)
    d.poly([(W, 0), (W - 70, 0), (W - 40, 1390), (W, 1390)], mix(dash, (0, 0, 0), .2))
    d.rect(0, 0, W, 46, mix(dash, (0, 0, 0), .2))
    if screen:                                                                     # centre screen
        x0, y0, x1, y1 = screen
        d.rect(x0 - 8, y0 - 8, x1 + 8, y1 + 8, (10, 10, 12), r=14)
        d.rect(x0, y0, x1, y1, accent, r=8)
    d.rect(0, 1396, W, 1424, trim)                                                  # dash trim strip
    for i in range(6): d.rect(0, 1440 + i * 80, W, 1444 + i * 80, mix(dash, (0, 0, 0), .15))
    d.ell(wheel_x, 1476, 176, 76, None, (12, 12, 14), 40)                           # steering wheel rim
    d.ell(wheel_x, 1470, 172, 72, None, mix(dash, (255, 255, 255), .22), 30)
    d.rect(wheel_x - 56, 1432, wheel_x + 56, 1520, mix(dash, (255, 255, 255), .12), r=24)
    d.ell(wheel_x, 1470, 16, 16, accent2)
    if roof_console:
        d.rect(400, 46, 518, 92, (40, 40, 44), r=10)

# ---- performance schedules built from the script, with episode overrides
A_ = dict(brows='angry', eyes='wide'); WD_ = dict(brows='angry', eyes='wide', sweat=1)
EXCL = [('up', 'up', A_), ('point', 'point', A_), ('head', 'head', WD_), ('shrug', 'shrug', A_), ('up', 'point', WD_)]
QUES = [('shrug', 'shrug', dict(brows='up')), ('open', 'rest', dict(brows='up')), ('point', 'rest', dict(brows='worried')),
        ('rest', 'open', dict(brows='up'))]
STAT = [('rest', 'open', dict(brows='flat')), ('point', 'rest', dict(brows='flat')), ('open', 'rest', dict(brows='flat'))]
SGEST = [('open', 'clasp'), ('show', 'clasp'), ('clasp', 'offer'), ('open', 'open'), ('clasp', 'open')]
def build_scheds():
    B, S = [(0.0, *EP.B_START)], [(0.0, 'clasp', 'clasp', {})]
    ce = cq = cs = cg = 0
    for li in range(NL):
        spk, text, _ = SCRIPT.LINES[li]
        t0, t1 = LS[li] - .08, LE[li] + .15
        nxt_same = li + 1 < NL and SCRIPT.LINES[li + 1][0] == spk and LS[li + 1] - LE[li] < .6
        if spk == 'B':
            if li in EP.POSE: e = EP.POSE[li]
            elif text.endswith('!'): e = EXCL[ce % len(EXCL)]; ce += 1
            elif text.endswith('?'): e = QUES[cq % len(QUES)]; cq += 1
            else: e = STAT[cs % len(STAT)]; cs += 1
            ex = dict(EP.mood(li)); ex.update(e[2])
            B.append((t0, e[0], e[1], ex))
            if not nxt_same: B.append((t1, 'rest', 'rest', EP.mood(li)))
        else:
            if li in EP.POSE: e = EP.POSE[li]
            elif ' app' in text.lower(): e = ('clasp', 'offer', dict(prop={'rpose': 'phone'}))
            else: g = SGEST[cg % len(SGEST)]; cg += 1; e = (g[0], g[1], {})
            S.append((t0, e[0], e[1], e[2]))
            if not nxt_same: S.append((t1, 'clasp', 'clasp', {}))
            if li in EP.REACT: B.append((LS[li] + .25 if EP.REACT[li][3:] == ('early',) else LE[li] - .05, *EP.REACT[li][:3]))
    for who, t, lp, rp, ex in EP.EXTRA_POSES:
        (B if who == 'B' else S).append((t, lp, rp, ex))
    return sorted(B, key=lambda e: e[0]), sorted(S, key=lambda e: e[0])

BS = SS_ = None
def performers(img, t, sc):
    P = EP.STAGE.get(sc + 1, {})
    s_ = P.get('s', 1.0)
    bx1, sxp, fy = P.get('bx', 270), P.get('sx', 670), P.get('fy', FEET_Y)
    t_in = SCENES[sc]
    walk = P.get('walk', 'in' if sc else 'none')
    if walk == 'in':   k, bx0, rate = prog(t, t_in, .8), P.get('bx0', -70), 12
    elif walk == 'slow': k, bx0, rate = prog(t, t_in, 1.2), P.get('bx0', 60), 7
    else:              k, bx0, rate = 1.0, bx1, 0
    if sc == 0: k, bx0, rate = prog(t, 0, 1.1), 150, 11          # frame 1: already walking in, mid-sentence
    bx = bx0 + (bx1 - bx0) * oc(k)
    f = int(round(t * FPS))
    for who, x, sched, cfg in (('S', sxp, SS_, EP.SALES), ('B', bx, BS, BUYER)):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[who][min(f, len(MOUTH[who]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        st['dy'] = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3 + (-4 if talking(who, t) and (f // 4) % 2 else 0)
        if who == 'B' and k < 1 and rate:
            st['walk'] = t * rate; st['dy'] -= abs(math.sin(t * rate)) * 10
        if st.get('sweat'): st['sweat'] = t
        jx, jy = EP.jolt(t, sc + 1, who)
        if s_ == 1.0 and not (jx or jy):
            person(D(img), x, fy + st.pop('fy_off', 0), cfg, st)
        else:
            npc(img, x + jx, fy + jy, s_, cfg, st)

def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    img = EP.background(sc + 1, t).copy()
    EP.behind(img, t, sc + 1)
    performers(img, t, sc)
    EP.front(img, t, sc + 1)
    return img

def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    C = EP.CAM.get(sc + 1, {})
    z = C.get('z', 1.05) + 0.01 * math.sin((t - t0) * .55)
    fol = C.get('follow', 45)
    li = last_line(t)
    def tgt(l): return (fol if SCRIPT.LINES[l][0] == 'S' else -fol) if SCN[l] == sc + 1 else 0
    k = io(prog(t, LS[li] - .15, .6))
    sx = C.get('sx', 0) + tgt(max(0, li - 1)) * (1 - k) + tgt(li) * k
    sy = C.get('sy', 0)
    sx += 46 * (1 - oc(prog(t, t0, 1.2))) if sc else 0
    if sc == 0: z += 0.05 * (1 - oc(prog(t, 0, 1.4)))           # frame 1 already moving: settle from a push-in
    for tp, amt in EP.PUNCH:
        if tp <= t < tp + .5: z += amt * (1 - oc(prog(t, tp, .5)))
    for tp, d_, amp in EP.SHAKE:
        if tp <= t < tp + d_:
            k_ = 1 - prog(t, tp, d_)
            sx += amp * k_ * math.sin(t * 61); sy += amp * .7 * k_ * math.sin(t * 47 + 1)
    return EP.cam_extra(t, sc + 1, z, sx, sy)

def shoot(t, sc=None):
    wimg = world(t, sc)
    z, sx, sy = camera(t if sc is None else max(t, SCENES[sc]))
    ax, ay = CX * K, 1150 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    return wimg.resize((W, H), Image.BILINEAR if EP.FAST else Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')

def cutaway(t, c):
    """Full-frame real close-up (t0, t1, photo, label): slow push-in, label chip."""
    t0, t1, name, label = c
    big = photo(name, int(W * 1.16), int(H * 1.16), k=1)
    z = 1 + .14 * prog(t, t0, t1 - t0)
    cw, ch = big.width / z, big.height / z
    x0, y0 = (big.width - cw) / 2, (big.height - ch) * .45
    img = big.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA'); f = font(40)
    tw = f.getlength(label)
    d.rounded_rectangle((CX - tw / 2 - 26, 228, CX + tw / 2 + 26, 300), 16, fill=(12, 12, 16, 210))
    d.text((CX, 264), label, font=f, fill=(255, 255, 255), anchor='mm')
    return img

# ================================================================ frame
TR = 0.4
def frame(n):
    t = n / FPS
    tr = next((s for s in SCENES[1:] if s - TR / 2 <= t < s + TR / 2), None)
    i_new = SCENES.index(tr) if tr is not None else None
    if tr is None or i_new in EP.HARD_CUT:
        img = shoot(t)
        if tr is not None and t >= tr:
            img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.5 * (1 - prog(t, tr, TR / 2)))
    else:                                                   # whip pan with motion smear
        k = io(prog(t, tr - TR / 2, TR))
        a, b = shoot(min(t, tr - .001), i_new - 1), shoot(max(t, tr), i_new)
        img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        off = int(W * k)
        img.alpha_composite(a, (-off, 0)); img.alpha_composite(b, (W - off, 0))
        bl = math.sin(math.pi * k)
        if bl > .05:
            smear = img.resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
            img = Image.blend(img, smear, min(.85, bl))
    c = next((c for c in EP.CUTAWAYS if c[0] <= t < c[1]), None)
    if c is not None:
        cut = cutaway(t, c)
        a = min(prog(t, c[0], .12), 1 - prog(t, c[1] - .12, .12))
        img = Image.blend(img, cut, a) if a < 1 else cut
    for tf, amt in EP.FLASH:
        if tf <= t < tf + .3:
            img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), amt * (1 - prog(t, tf, .3)))
    ov = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    used = EP.overlays(ov, t)
    if t >= T_CARD:
        used = True; final_card(ov, t)
    if used:
        img.alpha_composite(ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA'))
    if t >= T_CARD:
        k_ = io(prog(t, T_CARD, 1.0)) * .45
        v = vignette()
        img.alpha_composite(Image.merge('RGBA', (*v.split()[:3], v.getchannel('A').point(lambda p: int(p * k_)))))
    captions(img, t)
    return img.convert('RGB').tobytes()

FINAL_Y0, FINAL_DY = 430, 104
def final_card(img, t):
    fa = prog(t, T_CARD, .25); d = D(img)
    rows = EP.FINAL
    d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(rows) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
    for i, (txt, size, col) in enumerate(rows):
        k_ = popin(t, T_CARD + .08 * i, .3)
        if k_ > .05:
            d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))

def final_boxes():
    out = []
    for i, (txt, size, _) in enumerate(EP.FINAL):
        f = font(size); bb = f.getbbox(txt, anchor='mm', stroke_width=4)
        y = FINAL_Y0 + FINAL_DY * i; cap = f.getbbox('H')[3] - f.getbbox('H')[1]
        out.append(dict(text=txt, x0=CX + bb[0], x1=CX + bb[2], y0=y + bb[1], y1=y + bb[3], cap_height=cap))
    return out

def thumbnail(t, out):
    """Hook frame + big series title, no captions."""
    img = shoot(t)
    ov = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    EP.overlays(ov, t)
    img.alpha_composite(ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA'))
    d = ImageDraw.Draw(img, 'RGBA')
    d.rectangle((0, 1420, W, H), fill=(10, 10, 14, 200))
    y = 1530
    for txt, size, col in EP.THUMB:
        f = font(size)
        while f.getlength(txt) > 940: size -= 4; f = font(size)
        d.text((W / 2, y), txt, font=f, fill=col, anchor='mm', stroke_width=10, stroke_fill=(10, 10, 16))
        y += size * 1.12
    img.convert('RGB').save(out)

# ================================================================ audio
def build_audio(voice, music, out_wav):
    SR = sfx.SR
    def load(p):
        return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                            capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR)
    v = load(voice); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    T_ = np.arange(n) / SR
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    def step(): return sfx.thump(.12) * .5
    for k_ in range(4): add(0.02 + k_ * .27, step(), .45)
    for i, s_ in enumerate(SCENES[1:], 1):
        if i in EP.HARD_CUT: add(s_ - .02, sfx.thump(), .4)
        else: add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .3)
        if EP.STAGE.get(i + 1, {}).get('walk', 'in') in ('in', 'slow'):
            for k_ in range(3): add(s_ + .08 + k_ * .26, step(), .35)
    EP.cues(add, sfx)
    add(T_CARD, sfx.pop(), .35); add(T_CARD + .05, sfx.ding(1320, .8), .14)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s[:len(fxa) - i]
    # background music (user-supplied track): looped to length, ducked under dialogue, lifted on the end card
    m = load(music)
    m = np.tile(m, int(np.ceil(n / len(m))))[:n]
    vr = np.sqrt(np.mean(v[np.abs(v) > 1e-3] ** 2)); mr = np.sqrt(np.mean(m ** 2)) + 1e-9
    act = np.convolve((np.abs(v) > .02).astype(float), np.ones(int(SR * .25)) / (SR * .25), mode='same')
    duck = 0.11 + 0.07 * (1 - np.clip(act * 3, 0, 1))
    duck = np.convolve(duck, np.ones(int(SR * .08)) / (SR * .08), mode='same')
    duck = np.where(T_ >= T_CARD, 0.26, duck)
    fade = np.clip(T_ / .4, 0, 1) * np.clip((DUR - T_) / 1.2, 0, 1)
    mixd = v + fxa[:n] * 0.5 + m / mr * vr * duck * fade
    mixd = np.clip(mixd / max(1.0, np.abs(mixd).max() / 0.95), -1, 1)
    tmp = out_wav + '.pre.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', tmp],
                   input=mixd.astype(np.float64).tobytes(), check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    mm = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={mm['input_i']}:measured_TP={mm['input_tp']}:measured_LRA={mm['input_lra']}"
          f":measured_thresh={mm['input_thresh']}:offset={mm['target_offset']}")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', af, '-ar', '48000', '-ac', '2', tmp + '2.wav'], check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', tmp + '2.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = float(r.split('I:')[-1].split('LUFS')[0]); tp = float(r.split('Peak:')[-1].split('dBFS')[0])
    g = min(-14.0 - I, -1.5 - tp)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp + '2.wav', '-af', f'volume={g:.2f}dB', out_wav], check=True)
    os.remove(tmp); os.remove(tmp + '2.wav')

# ================================================================ CLI
def _init(voice):
    load_mouth(voice)

def main(ep):
    global EP, BS, SS_
    EP = ep
    BS, SS_ = build_scheds()
    BADGE[0] = EP.badge
    mode = sys.argv[1]
    if mode == 'still':
        load_mouth(sys.argv[4] if len(sys.argv) > 4 else EP.VOICE)
        Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif mode == 'sheet':                                   # contact sheet of N stills across the cut
        load_mouth(EP.VOICE)
        ts = [float(x) for x in sys.argv[3].split(',')]
        cols = 6; th = (180, 320); sheet = Image.new('RGB', (cols * th[0], ((len(ts) + cols - 1) // cols) * (th[1] + 24)), 'white')
        dd = ImageDraw.Draw(sheet)
        with Pool(os.cpu_count(), initializer=_init, initargs=(EP.VOICE,)) as pool:
            bufs = pool.map(frame, [int(x * FPS) for x in ts])
        for i, (x, b) in enumerate(zip(ts, bufs)):
            im = Image.frombytes('RGB', (W, H), b).resize(th, Image.LANCZOS)
            sheet.paste(im, ((i % cols) * th[0], (i // cols) * (th[1] + 24) + 24))
            dd.text(((i % cols) * th[0] + 4, (i // cols) * (th[1] + 24) + 4), f'{x:.1f}s', fill='black')
        sheet.save(sys.argv[2])
    elif mode == 'thumb':
        load_mouth(EP.VOICE); thumbnail(float(sys.argv[2]), sys.argv[3])
    elif mode == 'meta':
        json.dump(dict(captions=caption_boxes(), final=final_boxes(), onscreen=EP.ONSCREEN, duration=DUR, size=[W, H], fps=FPS),
                  open(sys.argv[2], 'w'), indent=1)
    elif mode in ('video', 'clip'):
        voice, music, out = sys.argv[2], sys.argv[3], sys.argv[4]
        t_a, t_b = (float(sys.argv[5]), float(sys.argv[6])) if mode == 'clip' else (0.0, DUR)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        wav = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(voice, music, wav)
        f0, f1 = int(t_a * FPS), int(min(t_b, DUR) * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', f'{t_a:.3f}', '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
                               '-maxrate', '13M', '-bufsize', '26M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                               '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(voice,)) as pool:
            for i, buf in enumerate(pool.imap(frame, range(f0, f1), chunksize=4)):
                ff.stdin.write(buf)
                if i % 300 == 0: print(f'frame {i}/{f1 - f0}', flush=True)
        ff.stdin.close(); ff.wait()
        os.remove(wav)
        print('done', out)
