"""Yub car-skit engine: one renderer for every video in the series. Built from bmw-heated-seats/src/render.py (same cast,
poses, lip sync, word-by-word captions, camera punches, whip pans, mix chain). A video folder holds cfg.py (script, six
sets, photos, cards, oddity), words.json and assets/ (Wikimedia Commons photos + brand logo).
Usage: python engine.py VIDEO_DIR video VOICE.wav OUT.mp4 | still T OUT.png VOICE | meta OUT.json | thumb OUT.png VOICE"""
import importlib.util, json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import sfx

W, H, FPS, K = 1080, 1920, 30, 2
CX = 459                                   # composition centre (left 85% of width)
WALL_Y, FEET_Y, CEIL = 940, 1880, 84
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VDIR = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.environ['YUB_VIDEO'])
os.environ['YUB_VIDEO'] = VDIR             # pool workers re-import with the same video
_spec = importlib.util.spec_from_file_location('cfg', os.path.join(VDIR, 'cfg.py'))
C = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(C)
ASSETS = os.path.join(VDIR, 'assets')
MUSIC = os.path.expanduser('~/.cache/yub/music.mp3')
WORDS = json.load(open(os.path.join(VDIR, 'words.json')))
DUR = round(WORDS[-1]['e'] + 2.3, 2)

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
NL = len(C.LINES)
def word_t(line, txt=None, nth=0):
    if txt is None: return LS[line]
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
def T_(ref):                                # ref: line index, (line, word) or (line, word, offset)
    if isinstance(ref, (int, float)): return LS[int(ref)]
    return word_t(ref[0], ref[1]) + (ref[2] if len(ref) > 2 else 0.0)
FIRST = {}
for i, l in enumerate(C.LINES): FIRST.setdefault(l[2], i)
NSC = len(C.SETS)
SCENES = [0.0] + [LS[FIRST[s]] - 0.5 for s in range(1, NSC)]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
def scene_end(sc): return SCENES[sc + 1] if sc + 1 < NSC else DUR
LAST = NL - 1
T_FINAL = LS[LAST]
BEAT = (LE[LAST - 1], LS[LAST])
T_CARD = LE[LAST] + 0.3
OVERLAY_START = 3.0                         # no overlays during the hook

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

def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)
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
    ph = Image.open(os.path.join(ASSETS, name)).convert('RGB')
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

# ================================================================ photos and logos (Wikimedia Commons files in assets/)
@lru_cache(None)
def photo_fill(name, w, h, fx=0.5, fy=0.5):
    """Photo cropped to fill w x h (design px) at K scale. fx/fy pick the crop centre."""
    ph = Image.open(os.path.join(ASSETS, name)).convert('RGB')
    r = w / h
    if ph.width / ph.height > r:
        cw = int(ph.height * r); x0 = int((ph.width - cw) * fx); box = (x0, 0, x0 + cw, ph.height)
    else:
        ch = int(ph.width / r); y0 = int((ph.height - ch) * fy); box = (0, y0, ph.width, y0 + ch)
    return ph.crop(box).resize((int(w * K), int(h * K)), Image.LANCZOS)

@lru_cache(None)
def logo_img(name, h, white=False):
    lg = Image.open(os.path.join(ASSETS, name)).convert('RGBA')
    lg = lg.crop(lg.getbbox())
    s = h * K / lg.height
    lg = lg.resize((max(1, int(lg.width * s)), int(h * K)), Image.LANCZOS)
    if white:
        a = lg.getchannel('A'); lg = Image.new('RGBA', lg.size, (255, 255, 255, 255)); lg.putalpha(a)
    return lg

def put_logo(img, cx, cy, h, white=False, name=None):
    lg = logo_img(name or C.BRAND['logo'], h, white)
    img.alpha_composite(lg, (int(cx * K - lg.width / 2), int(cy * K - lg.height / 2)))
    return lg.width / K

def framed(img, name, x0, y0, w, h, frame=(14, 14, 18), bw=10, r=8, fx=0.5, fy=0.5, glow=None):
    d = D(img)
    if glow:
        g = Image.new('RGBA', img.size, (0, 0, 0, 0)); D(g).rect(x0 - 30, y0 - 30, x0 + w + 30, y0 + h + 30, glow, r=40)
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(26 * K)))
        d = D(img)
    d.rect(x0 - bw + 6, y0 - bw + 10, x0 + w + bw + 6, y0 + h + bw + 10, (0, 0, 0, 70), r=r + 4)
    d.rect(x0 - bw, y0 - bw, x0 + w + bw, y0 + h + bw, frame, r=r + 4)
    img.paste(photo_fill(name, w, h, fx, fy), (int(x0 * K), int(y0 * K)))

def base(top0, top1, fl0, fl1, horizon=WALL_Y):
    arr = np.concatenate([grad(horizon * K, W * K, top0, top1), grad((H - horizon) * K, W * K, fl0, fl1)])
    return Image.fromarray(arr.astype(np.uint8)).convert('RGBA')

def floor_lines(d, col, step=140):
    for i, y in enumerate(range(WALL_Y + 60, H, step)):
        d.line([(0, y + i * 12), (W, y + i * 12)], col, 2)

def plant(d, x, fy, s=1.0):
    d.rect(x - 34 * s, fy - 70 * s, x + 34 * s, fy, (60, 58, 64), r=8, ol=OL, w=3)
    for i, (a, l) in enumerate(((-60, 150), (-30, 190), (0, 210), (30, 185), (60, 150), (-80, 110), (80, 110))):
        ang = math.radians(a - 90)
        ex, ey = x + math.cos(ang) * l * s, fy - 70 * s + math.sin(ang) * l * s
        d.poly(spline([(x, fy - 70 * s), ((x + ex) / 2 - 14 * s, (fy - 70 * s + ey) / 2), (ex, ey),
                       ((x + ex) / 2 + 14 * s, (fy - 70 * s + ey) / 2)], 5), ((46, 128, 72), (60, 150, 86))[i % 2], OL, 2)

def pendant(d, px, col=(52, 52, 56)):
    d.line([(px, CEIL), (px, CEIL + 40)], (70, 74, 78), 3)
    d.chord(px, CEIL + 62, 46, 28, 180, 360, col)
    d.ell(px, CEIL + 62, 30, 6, (255, 240, 200))

def cloud(d, x, y, s=1.0, col=(255, 255, 255, 230)):
    for dx, dy, r in ((-50, 8, 34), (-14, -10, 44), (30, 0, 38), (64, 12, 26)):
        d.ell(x + dx * s, y + dy * s, r * s, r * s * .8, col)

def sky(top, bot):
    return base(top, bot, (70, 72, 78), (110, 112, 118))

# ---------------------------------------------------------------- 1 showroom: LED wall with the photo, lit logo fascia
@lru_cache(None)
def bg_showroom(sc):
    S, B = C.SETS[sc], C.BRAND
    img = base(*B['wall'], *B['floor']); d = D(img)
    for x in range(-40, W, 170):                                   # wall panels
        d.rect(x + 8, 110, x + 160, WALL_Y - 40, B['panel'])
        d.line([(x + 8, 110), (x + 8, WALL_Y - 40)], B['accent'] + (90,), 2)
    d.rect(0, 0, W, CEIL, B['ceil']); d.rect(0, CEIL - 6, W, CEIL, tuple(int(c * .7) for c in B['ceil']))
    for px in (150, 459, 768): pendant(d, px)
    img = spot(img, CX, 140, 70, 470, 800); d = D(img)
    framed(img, S['photo'], 92, 150, 736, 414, frame=(12, 12, 14), bw=14, fy=S.get('fy', .55), glow=B['accent'] + (120,))
    d = D(img)
    d.rect(250, 612, 668, 712, B['fascia'], r=16, ol=B['accent'], w=4)
    put_logo(img, CX, 662, 64, white=B.get('logo_white', False))
    d = D(img)
    d.rect(0, WALL_Y - 8, W, WALL_Y, B['accent']); d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    ref = photo_fill(S['photo'], 736, 414, .5, S.get('fy', .55)).transpose(Image.FLIP_TOP_BOTTOM).convert('RGBA')
    ref.putalpha(Image.linear_gradient('L').resize(ref.size).point(lambda v: int((255 - v) * .22)))
    img.alpha_composite(ref, (92 * K, (WALL_Y + 8) * K))                   # glossy floor reflection
    d = D(img)
    floor_lines(d, tuple(min(255, c + 14) for c in B['floor'][1]))
    plant(d, 46, 950, 1.0); plant(d, 880, 950, .9)
    return img

# ---------------------------------------------------------------- 2 gallery: museum wall, two framed photos, rope
@lru_cache(None)
def bg_gallery(sc):
    S = C.SETS[sc]
    img = base((86, 30, 34), (120, 48, 50), (120, 78, 46), (164, 112, 70)); d = D(img)
    d.rect(0, 0, W, CEIL, (40, 20, 20)); d.rect(0, CEIL - 6, W, CEIL, (24, 12, 12))
    d.rect(0, 700, W, WALL_Y, (70, 24, 28)); d.rect(0, 696, W, 704, (196, 160, 96))
    for x in range(0, W, 90): d.rect(x + 10, 720, x + 80, WALL_Y - 20, None, r=4, ol=(96, 40, 42), w=3)
    for i, (ph, lab) in enumerate(zip(S['photos'], S['labels'])):
        x0 = 70 + i * 420
        img = spot(img, x0 + 180, 120, 40, 260, 520, 70); d = D(img)
        d.rect(x0 + 130, 116, x0 + 230, 130, (196, 160, 96), r=4)           # picture light
        framed(img, ph, x0, 190, 360, 250, frame=(196, 160, 96), bw=16, r=2, fy=S.get('fy', .55))
        d = D(img)
        d.rect(x0 + 90, 500, x0 + 270, 556, (236, 226, 204), r=4, ol=(150, 120, 70), w=2)
        d.text(x0 + 180, 528, lab, 30, (50, 36, 26), path=FONT_X)
    put_logo(img, CX, 630, 54, white=C.BRAND.get('logo_white_on_dark', True))
    d = D(img)
    for i, y in enumerate(range(WALL_Y + 40, H, 60)):                       # parquet
        d.line([(0, y + i * 6), (W, y + i * 6)], (136, 90, 54), 3)
    for x in (130, 790):                                                    # stanchions + velvet rope
        d.rect(x - 6, 880, x + 6, 1000, (200, 170, 100)); d.ell(x, 1000, 30, 8, (180, 150, 86)); d.ell(x, 876, 12, 12, (220, 190, 120))
    d.line(spline([(130, 890), (300, 950), (460, 965), (620, 950), (790, 890)], 6, closed=False), (150, 20, 36), 10)
    return img

# ---------------------------------------------------------------- 3 track: grandstand, kerbs, big screen with the photo
@lru_cache(None)
def bg_track(sc):
    S = C.SETS[sc]
    img = base((70, 140, 220), (176, 214, 244), (64, 66, 72), (98, 100, 106)); d = D(img)
    for x, y, s in ((140, 120, 1.0), (520, 90, .8), (860, 160, 1.1)): cloud(d, x, y, s)
    d.poly([(0, 640), (200, 600), (420, 630), (640, 590), (900, 620), (W, 600), (W, 760), (0, 760)], (88, 140, 96))
    for i in range(16):                                                    # grandstand with crowd
        y = 640 + i * 18
        d.rect(-10, y, W + 10, y + 18, ((140, 146, 156), (120, 126, 136))[i % 2])
        rng = np.random.default_rng(i)
        for x in range(10, W, 26):
            c = [(230, 60, 60), (60, 110, 220), (250, 210, 70), (240, 240, 240), (40, 40, 48)][rng.integers(5)]
            d.ell(x + rng.integers(-6, 6), y + 4, 8, 8, c)
    d.rect(-10, 610, W + 10, 640, (40, 44, 52))
    for x in range(-20, W, 120): d.line([(x, 610), (x + 10, 640)], (70, 74, 82), 4)
    lw = put_logo(img, 210, 625, 22, white=True); d = D(img)
    d.rect(0, 924, W, WALL_Y, (240, 240, 240))
    for x in range(0, W, 80): d.rect(x, 924, x + 40, WALL_Y, (220, 40, 40))
    d.rect(560, 380, 580, 610, (60, 64, 72)); d.rect(780, 380, 800, 610, (60, 64, 72))
    framed(img, S['photo'], 480, 170, 400, 225, frame=(18, 18, 22), bw=12, fy=S.get('fy', .55))
    d = D(img)
    for i in range(10):                                                    # checkered banner
        for j in range(2):
            d.rect(40 + i * 30, 180 + j * 30, 70 + i * 30, 210 + j * 30, (20, 20, 24) if (i + j) % 2 else (250, 250, 250))
    d.line([(40, 180), (40, 600)], (80, 80, 86), 6)
    for i, y in enumerate(range(WALL_Y + 140, H, 220)):
        d.rect(CX - 40, y, CX + 40, y + 70, (236, 236, 236, 160))
    return img

# ---------------------------------------------------------------- 4 office: night skyline, wall screen with photo/chart
@lru_cache(None)
def bg_office(sc):
    S = C.SETS[sc]
    img = base((16, 22, 46), (40, 44, 78), (56, 48, 44), (92, 80, 72)); d = D(img)
    rng = np.random.default_rng(5)
    x = -10
    while x < W:                                                            # skyline
        bw_, bh = rng.integers(60, 140), rng.integers(160, 520)
        d.rect(x, WALL_Y - bh, x + bw_, WALL_Y, (26, 32, 58))
        for wy in range(int(WALL_Y - bh + 14), WALL_Y - 10, 26):
            for wx in range(int(x + 10), int(x + bw_ - 10), 20):
                if rng.random() < .45: d.rect(wx, wy, wx + 9, wy + 13, (255, 220, 140, 200))
        x += bw_ + rng.integers(4, 20)
    d.ell(860, 170, 46, 46, (250, 246, 220)); d.ell(876, 160, 40, 40, (16, 22, 46))   # moon
    for x in range(0, W + 1, 270): d.rect(x - 8, 0, x + 8, WALL_Y, (30, 30, 36))      # mullions
    d.rect(0, 0, W, CEIL, (24, 24, 30))
    d.rect(80, 150, 840, 600, (10, 10, 14), r=16)                                     # wall screen
    if S.get('photo'):
        img.paste(photo_fill(S['photo'], 740, 430, .5, S.get('fy', .55)), (90 * K, 160 * K)); d = D(img)
    else:
        d.rect(90, 160, 830, 590, (24, 30, 48), r=10)
        d.text(120, 200, S.get('title', ''), 34, (220, 226, 240), anchor='lm', path=FONT_X)
        put_logo(img, 760, 200, 36, white=True); d = D(img)
        for k_ in range(5): d.line([(130, 560 - k_ * 80), (800, 560 - k_ * 80)], (50, 60, 84), 2)
    d.rect(0, 880, W, 940, (60, 42, 30)); d.rect(0, 876, W, 884, (120, 90, 64))       # boardroom table edge
    floor_lines(d, (104, 90, 80))
    plant(d, 40, 950, .9)
    return img

def office_life(img, t, sc):
    S = C.SETS[sc]
    if not S.get('bars'): return
    d = D(img); t0 = SCENES[sc] + .3
    n = len(S['bars']); bw_ = 560 / n
    mx = max(v for _, v in S['bars'])
    for i, (lab, v) in enumerate(S['bars']):
        k_ = oc(prog(t, t0 + i * .15, .6))
        h_ = 320 * v / mx * k_
        x0 = 150 + i * bw_ + 14
        col = C.BRAND['accent'] if i == S.get('hi', n - 1) else (110, 120, 140)
        d.rect(x0, 560 - h_, x0 + bw_ - 28, 560, col, r=6)
        d.text(x0 + (bw_ - 28) / 2, 578, lab, 22, (200, 206, 220), path=FONT_X)

# ---------------------------------------------------------------- 5 factory: trusses, robot arms, moving line
@lru_cache(None)
def bg_factory(sc):
    S = C.SETS[sc]
    img = base((52, 62, 78), (92, 104, 120), (96, 98, 104), (140, 142, 148)); d = D(img)
    for x in range(0, W, 180):                                              # roof trusses
        d.line([(x, CEIL), (x + 90, 200), (x + 180, CEIL)], (40, 48, 60), 6)
    d.rect(0, CEIL, W, CEIL + 12, (40, 48, 60)); d.rect(0, 196, W, 206, (40, 48, 60))
    for px in (120, 459, 800):
        d.line([(px, 206), (px, 250)], (30, 30, 34), 3); d.chord(px, 270, 50, 26, 180, 360, (230, 200, 60)); d.ell(px, 270, 34, 6, (255, 250, 220))
    d.rect(180, 300, 740, 360, C.BRAND['fascia'], r=8)                     # logo banner
    put_logo(img, CX, 330, 38, white=C.BRAND.get('logo_white', False)); d = D(img)
    framed(img, S['photo'], 600, 420, 300, 180, frame=(24, 26, 30), bw=10, fy=S.get('fy', .55))
    d = D(img)
    d.rect(0, 840, W, 900, (50, 54, 60)); d.rect(0, 836, W, 846, (230, 190, 40))
    d.rect(0, WALL_Y - 8, W, WALL_Y, (230, 190, 40))
    for x in range(0, W, 60): d.poly([(x, WALL_Y), (x + 30, WALL_Y), (x + 10, WALL_Y + 22), (x - 20, WALL_Y + 22)], (30, 30, 34))
    floor_lines(d, (156, 158, 164))
    return img

def factory_life(img, t, sc):
    d = D(img)
    for x in range(0, W + 60, 60):                                         # rollers moving
        xx = (x + t * 80) % (W + 60) - 30
        d.ell(xx, 870, 14, 14, (90, 94, 100), (30, 30, 34), 2)
    for i, bx in enumerate((150, 430)):                                     # robot arms welding
        a1 = -60 + 25 * math.sin(t * 1.6 + i * 2); a2 = 70 + 30 * math.sin(t * 2.3 + i)
        sx_, sy_ = bx, 830
        ex, ey = sx_ + 150 * math.cos(math.radians(a1 - 90 + 90)) * .0 + 120 * math.sin(math.radians(a1)), sy_ - 150 * math.cos(math.radians(a1))
        tx, ty = ex + 110 * math.sin(math.radians(a1 + a2)), ey - 110 * math.cos(math.radians(a1 + a2))
        d.rect(sx_ - 40, 800, sx_ + 40, 840, (230, 120, 30), r=8, ol=OL, w=3)
        d.line([(sx_, sy_ - 20), (ex, ey)], OL, 34); d.line([(sx_, sy_ - 20), (ex, ey)], (240, 140, 40), 26)
        d.line([(ex, ey), (tx, ty)], OL, 26); d.line([(ex, ey), (tx, ty)], (240, 140, 40), 18)
        d.ell(ex, ey, 18, 18, (60, 60, 66), OL, 3)
        if int(t * 10 + i * 3) % 4 != 0:
            for k_ in range(6):
                a = t * 37 + k_ * 1.1 + i
                d.line([(tx, ty), (tx + math.cos(a) * 30, ty + math.sin(a) * 30 + 10)], (255, 230, 120), 3)
            d.ell(tx, ty, 10, 10, (255, 255, 230))

# ---------------------------------------------------------------- 6 lot: sunset, palms, pennants, billboard
@lru_cache(None)
def bg_lot(sc):
    S = C.SETS[sc]
    img = base((52, 40, 110), (250, 150, 90), (58, 58, 66), (96, 96, 104)); d = D(img)
    d.ell(760, 760, 120, 120, (255, 214, 120)); d.ell(760, 760, 90, 90, (255, 236, 170))
    d.poly([(0, 820), (160, 760), (330, 800), (520, 740), (720, 800), (900, 760), (W, 790), (W, WALL_Y), (0, WALL_Y)], (70, 46, 90))
    for px, ph_ in ((40, 520), (960, 460)):                                # palm silhouettes
        d.line([(px, WALL_Y), (px + 20, WALL_Y - ph_)], (34, 22, 50), 18)
        for a in (-150, -110, -70, -30, 10):
            r_ = math.radians(a); tx, ty = px + 20 + math.cos(r_) * 120, WALL_Y - ph_ + math.sin(r_) * 50 + 40
            d.line(spline([(px + 20, WALL_Y - ph_), ((px + 20 + tx) / 2, WALL_Y - ph_ - 30), (tx, ty)], 5, closed=False), (34, 22, 50), 14)
    d.rect(200, 470, 216, WALL_Y, (40, 40, 48)); d.rect(560, 470, 576, WALL_Y, (40, 40, 48))
    framed(img, S['photo'], 90, 170, 600, 320, frame=(240, 240, 240), bw=12, r=4, fy=S.get('fy', .55))
    d = D(img)
    d.rect(770, 300, 830, WALL_Y, (60, 62, 70))                             # logo pylon
    d.rect(710, 210, 890, 320, (250, 250, 252), r=10, ol=C.BRAND['accent'], w=5)
    put_logo(img, 800, 265, 50); d = D(img)
    for x in range(0, W, 220):                                              # parking lines
        d.poly([(x + 40, WALL_Y + 20), (x + 52, WALL_Y + 20), (x - 80, H), (x - 100, H)], (230, 230, 230, 150))
    return img

def lot_life(img, t, sc):
    d = D(img)
    pts = [(x, 140 + 30 * math.sin(x / 1080 * math.pi) * 0 + 40 * (1 - math.cos(x / 540 * math.pi)) / 2) for x in range(0, W + 1, 60)]
    d.line(pts, (40, 40, 48), 3)
    cols = [(230, 50, 50), (250, 210, 60), (60, 130, 230), (250, 250, 250)]
    for i, (x, y) in enumerate(pts[:-1]):
        fl = 8 * math.sin(t * 6 + i)
        d.poly([(x + 6, y), (x + 50, y + 3), (x + 28 + fl, y + 44)], cols[i % 4])

# ---------------------------------------------------------------- 7 garage: pegboard, chest, tyres, lift, poster
@lru_cache(None)
def bg_garage(sc):
    S = C.SETS[sc]
    img = base((150, 156, 162), (176, 180, 186), (110, 112, 116), (150, 150, 152)); d = D(img)
    d.rect(0, 0, W, CEIL, (60, 64, 70))
    for px in (180, 540, 900): d.rect(px - 90, CEIL + 10, px + 90, CEIL + 24, (250, 252, 255)); d.rect(px - 96, CEIL, px + 96, CEIL + 10, (90, 94, 100))
    d.rect(40, 150, 420, 560, (196, 160, 110), r=4, ol=(130, 100, 60), w=4)   # pegboard
    for x in range(60, 410, 24):
        for y in range(170, 550, 24): d.ell(x, y, 2.5, 2.5, (150, 116, 76))
    for i, x in enumerate(range(80, 400, 54)):                                # tools
        c = ((200, 40, 40), (60, 60, 66), (230, 180, 40))[i % 3]
        d.line([(x, 200), (x, 330 + (i % 2) * 40)], c, 10); d.ell(x, 200, 14, 14, None, c, 6)
        d.rect(x - 16, 400, x + 16, 470 - (i % 3) * 20, (90, 94, 100), r=4)
    framed(img, S['photo'], 470, 150, 400, 300, frame=(240, 240, 240), bw=10, r=2, fx=S.get('fx', .5), fy=S.get('fy', .55))
    d = D(img)
    put_logo(img, 670, 520, 44); d = D(img)
    d.rect(60, 640, 300, WALL_Y, (200, 30, 36), r=6, ol=OL, w=3)              # tool chest
    for y in range(660, WALL_Y - 20, 46): d.rect(80, y, 280, y + 36, (220, 50, 56), r=4); d.rect(150, y + 14, 210, y + 20, (200, 200, 206), r=3)
    for i in range(3): d.ell(740, WALL_Y - 34 - i * 52, 70, 26, (30, 30, 34), (10, 10, 12), 3); d.ell(740, WALL_Y - 34 - i * 52, 34, 12, (70, 70, 76))
    d.rect(0, WALL_Y - 6, W, WALL_Y, (230, 190, 40))
    d.ell(560, 1300, 120, 26, (90, 92, 96, 120)); d.ell(200, 1600, 90, 20, (90, 92, 96, 100))
    floor_lines(d, (130, 130, 134))
    return img

# ---------------------------------------------------------------- 8 farm: hills, barn, fence, billboard
@lru_cache(None)
def bg_farm(sc):
    S = C.SETS[sc]
    img = base((90, 170, 236), (196, 226, 246), (120, 92, 56), (150, 116, 74)); d = D(img)
    d.ell(860, 150, 60, 60, (255, 236, 150))
    for x, y, s in ((200, 130, 1.0), (600, 200, .8)): cloud(d, x, y, s)
    d.poly(spline([(-100, 760), (200, 640), (500, 720), (800, 630), (1180, 720), (1180, 950), (-100, 950)], 6), (110, 170, 80))
    d.poly(spline([(-100, 860), (300, 760), (700, 820), (1180, 760), (1180, 950), (-100, 950)], 6), (90, 150, 64))
    d.rect(700, 620, 900, WALL_Y, (180, 40, 36), ol=(110, 24, 20), w=4)       # barn
    d.poly([(680, 630), (800, 540), (920, 630)], (120, 30, 26), (80, 20, 16), 4)
    d.rect(760, 760, 840, WALL_Y, (240, 236, 226)); d.line([(760, 760), (840, WALL_Y)], (180, 40, 36), 6); d.line([(840, 760), (760, WALL_Y)], (180, 40, 36), 6)
    d.rect(200, 400, 214, 800, (90, 70, 50)); d.rect(560, 400, 574, 800, (90, 70, 50))
    framed(img, S['photo'], 70, 170, 600, 330, frame=(250, 248, 240), bw=12, r=2, fy=S.get('fy', .55))
    d = D(img)
    put_logo(img, 370, 540, 40); d = D(img)
    for x in range(-20, W, 90):                                             # fence
        d.rect(x, 860, x + 14, WALL_Y, (150, 116, 76))
    d.rect(-10, 880, W, 890, (170, 134, 90)); d.rect(-10, 910, W, 920, (170, 134, 90))
    for i, y in enumerate(range(WALL_Y + 50, H, 90)): d.line([(0, y + i * 8), (W, y + i * 8)], (130, 100, 62), 6)
    return img

# ---------------------------------------------------------------- 9 charging station at dusk
@lru_cache(None)
def bg_charging(sc):
    S = C.SETS[sc]
    img = base((20, 30, 70), (90, 80, 140), (40, 42, 50), (70, 72, 80)); d = D(img)
    rng = np.random.default_rng(2)
    for _ in range(40): d.ell(rng.integers(0, W), rng.integers(100, 500), 2, 2, (255, 255, 255, 180))
    d.poly([(-20, 120), (W + 20, 120), (W + 20, 190), (-20, 190)], (230, 232, 236))
    d.rect(-20, 190, W + 20, 204, C.BRAND['accent'])
    for x in range(60, W, 160): d.rect(x, 204, x + 100, 212, (200, 240, 255))
    put_logo(img, CX, 155, 40); d = D(img)
    for x in (40, 1040): d.rect(x - 14, 204, x + 14, WALL_Y, (190, 194, 200))
    framed(img, S['photo'], 150, 270, 600, 330, frame=(14, 14, 18), bw=12, fy=S.get('fy', .55), glow=(80, 200, 255, 90))
    d = D(img)
    for x in (130, 790):
        d.rect(x - 34, 680, x + 34, WALL_Y, (240, 242, 246), r=10, ol=OL, w=3)
        d.rect(x - 22, 700, x + 22, 744, (20, 30, 40), r=4)
        d.line([(x + 30, 780), (x + 60, 860), (x + 20, 920)], (30, 30, 34), 6)
    floor_lines(d, (80, 82, 90))
    for x in range(0, W, 240): d.rect(x + 20, WALL_Y + 30, x + 140, WALL_Y + 40, (80, 200, 255, 120))
    return img

def charging_life(img, t, sc):
    d = D(img)
    for i, x in enumerate((130, 790)):
        k_ = (t * .3 + i * .4) % 1
        d.rect(x - 18, 736 - 32 * k_, x + 18, 740, (80, 230, 140))
        if int(t * 2 + i) % 2: d.ell(x, 690, 5, 5, (80, 230, 140))

# ---------------------------------------------------------------- 10 vault: round door, gold, money shelves
@lru_cache(None)
def bg_vault(sc):
    S = C.SETS[sc]
    img = base((44, 48, 56), (70, 74, 84), (60, 62, 68), (96, 98, 104)); d = D(img)
    for y in range(120, WALL_Y, 60):
        for x in range(-30 + (y // 60 % 2) * 60, W, 120): d.rect(x, y, x + 116, y + 56, (54, 58, 68), r=3)
    d.rect(0, 0, W, CEIL, (30, 32, 38))
    framed(img, S['photo'], 70, 150, 520, 300, frame=(196, 160, 96), bw=12, r=4, fy=S.get('fy', .55))
    d = D(img)
    put_logo(img, 330, 520, 42, white=True); d = D(img)
    d.ell(820, 420, 170, 170, (120, 124, 134), OL, 5); d.ell(820, 420, 140, 140, (150, 154, 164), OL, 3)   # vault door
    d.ell(820, 420, 40, 40, (90, 94, 104), OL, 3)
    for a in range(0, 360, 60):
        r_ = math.radians(a); d.line([(820, 420), (820 + math.cos(r_) * 110, 420 + math.sin(r_) * 110)], (90, 94, 104), 12)
    for row in range(3):                                                     # gold stacks
        for i in range(5 - row):
            x = 640 + i * 60 + row * 30; y = WALL_Y - 30 - row * 30
            d.poly([(x, y), (x + 54, y), (x + 46, y - 26), (x + 8, y - 26)], (230, 190, 60), (150, 110, 30), 2)
    d.rect(40, 620, 420, WALL_Y, (70, 54, 40), ol=OL, w=3)                  # money shelves
    for y in (650, 730, 810, 890):
        d.rect(50, y + 50, 410, y + 60, (110, 84, 60))
        for x in range(60, 400, 46): d.rect(x, y + 14, x + 40, y + 50, (110, 170, 110), r=3, ol=(60, 110, 60), w=2)
    floor_lines(d, (110, 112, 118))
    return img

SETS = dict(showroom=(bg_showroom, None), gallery=(bg_gallery, None), track=(bg_track, None), office=(bg_office, office_life),
            factory=(bg_factory, factory_life), lot=(bg_lot, lot_life), garage=(bg_garage, None), farm=(bg_farm, None),
            charging=(bg_charging, charging_life), vault=(bg_vault, None))

# ================================================================ background oddities (one per video, never mentioned)
def penguin(d, x, fy, t, s=1.0):
    """A penguin mopping the floor, very seriously."""
    bob = abs(math.sin(t * 5)) * 3 * s
    d.ell(x + 40 * s, fy - 2, 70 * s, 10 * s, (200, 230, 250, 140))                  # wet patch
    mx = x + 50 * s + 26 * math.sin(t * 3.2) * s
    d.line([(x + 10 * s, fy - 70 * s - bob), (mx, fy - 6)], (150, 110, 70), 5)
    for k_ in range(7): d.line([(mx - 18 * s + k_ * 6 * s, fy - 8), (mx - 22 * s + k_ * 7 * s, fy)], (236, 236, 226), 4)
    for side in (-1, 1): d.ell(x + side * 14 * s, fy - 2, 14 * s, 6 * s, (246, 160, 40))
    d.ell(x, fy - 56 * s - bob, 38 * s, 56 * s, (24, 24, 30), OL, 3)
    d.ell(x + 6 * s, fy - 50 * s - bob, 26 * s, 44 * s, (250, 250, 250))
    hy = fy - 118 * s - bob
    d.ell(x, hy, 28 * s, 26 * s, (24, 24, 30), OL, 3)
    d.ell(x + 10 * s, hy + 2 * s, 14 * s, 14 * s, (250, 250, 250))
    if (t % 3.2) > .12: d.ell(x + 12 * s, hy, 3.5 * s, 3.5 * s, OL)
    d.poly([(x + 22 * s, hy + 4 * s), (x + 42 * s, hy + 9 * s), (x + 22 * s, hy + 13 * s)], (246, 160, 40), OL, 1.5)
    d.line([(x + 20 * s, fy - 80 * s - bob), (x + 12 * s, fy - 66 * s - bob)], (24, 24, 30), 10 * s)   # flipper on the mop
    d.rect(x - 34 * s, fy - 4, x - 14 * s, fy, (250, 214, 40))                         # tiny wet-floor sign
    d.poly([(x - 60 * s, fy), (x - 48 * s, fy - 40 * s), (x - 36 * s, fy)], (250, 214, 40), OL, 2)

def pony(d, x, fy, t, s=1.0):
    """A small horse plugged into a charging cable, battery icon filling over its head."""
    B1, B2 = (150, 96, 56), (110, 66, 36)
    for lx in (-34, -18, 26, 40):
        d.line([(x + lx * s, fy - 60 * s), (x + lx * s, fy)], B2, 9); d.ell(x + lx * s, fy, 6 * s, 3 * s, (40, 30, 24))
    d.ell(x + 4 * s, fy - 78 * s, 56 * s, 30 * s, B1, OL, 3)
    sw = math.sin(t * 3) * 10
    d.line(spline([(x + 58 * s, fy - 86 * s), (x + 78 * s, fy - 70 * s + sw * .3), (x + 74 * s + sw, fy - 30 * s)], 5, closed=False), (60, 36, 20), 10)
    nk = [(x - 36 * s, fy - 90 * s), (x - 54 * s, fy - 140 * s)]
    d.line(nk, OL, 30 * s); d.line(nk, B1, 24 * s)
    hx, hy = x - 62 * s, fy - 150 * s + math.sin(t * 1.5) * 2
    d.rect(hx - 36 * s, hy - 10 * s, hx + 8 * s, hy + 14 * s, B1, r=10 * s, ol=OL, w=2)
    d.poly([(hx + 2 * s, hy - 14 * s), (hx + 6 * s, hy - 34 * s), (hx + 12 * s, hy - 12 * s)], B1, OL, 2)
    d.line([(hx + 6 * s, hy - 16 * s), (hx + 2 * s, hy + 10 * s), (x - 44 * s, fy - 110 * s)], (60, 36, 20), 8)   # mane
    if (t % 2.9) > .12: d.ell(hx - 6 * s, hy - 2 * s, 3 * s, 3 * s, OL)
    cx_, cy_ = x + 20 * s, fy - 84 * s                                                       # plug in its side
    d.rect(cx_ - 8 * s, cy_ - 6 * s, cx_ + 8 * s, cy_ + 6 * s, (40, 40, 46), r=3)
    d.line(spline([(cx_, cy_), (cx_ + 50 * s, cy_ + 40 * s), (cx_ + 90 * s, fy - 4), (cx_ + 150 * s, fy - 30 * s)], 6, closed=False), (30, 30, 34), 5)
    bx, by = hx + 10 * s, hy - 70 * s                                                         # battery icon
    lvl = (t * .08) % 1
    d.rect(bx - 30 * s, by - 14 * s, bx + 26 * s, by + 14 * s, (20, 24, 30, 200), r=4, ol=(255, 255, 255), w=3)
    d.rect(bx + 26 * s, by - 6 * s, bx + 32 * s, by + 6 * s, (255, 255, 255))
    d.rect(bx - 26 * s, by - 10 * s, bx - 26 * s + 48 * s * lvl, by + 10 * s, (80, 230, 120))

def pig(d, x, fy, t, s=1.0):
    """A pig in a bow tie calmly feeding banknotes into a paper shredder."""
    P1, P2 = (246, 170, 180), (220, 130, 144)
    d.rect(x + 40 * s, fy - 80 * s, x + 110 * s, fy, (60, 64, 72), r=6, ol=OL, w=3)        # shredder
    d.rect(x + 36 * s, fy - 96 * s, x + 114 * s, fy - 80 * s, (40, 42, 48), r=4)
    ph = (t * 1.2) % 1
    nx = x + 75 * s
    if ph < .6:
        d.rect(nx - 22 * s, fy - 130 * s + 40 * ph * s, nx + 22 * s, fy - 96 * s, (120, 180, 120), ol=(60, 110, 60), w=2)
    for k_ in range(5):
        yy = fy - 70 * s + ((t * 60 + k_ * 17) % 60) * s
        d.line([(nx - 20 * s + k_ * 10 * s, fy - 80 * s), (nx - 22 * s + k_ * 10 * s, min(fy - 6, yy))], (120, 180, 120), 3)
    for lx in (-30, -12, 18, 34):
        d.line([(x + lx * s, fy - 44 * s), (x + lx * s, fy)], P2, 10)
    d.ell(x, fy - 66 * s, 56 * s, 40 * s, P1, OL, 3)
    hx, hy = x + 30 * s, fy - 112 * s + math.sin(t * 2) * 2
    d.ell(hx, hy, 30 * s, 28 * s, P1, OL, 3)
    for side in (-1, 1): d.poly([(hx + side * 12 * s, hy - 20 * s), (hx + side * 24 * s, hy - 40 * s), (hx + side * 26 * s, hy - 14 * s)], P2, OL, 2)
    d.ell(hx + 14 * s, hy + 6 * s, 13 * s, 10 * s, P2, OL, 2)
    for side in (-1, 1): d.ell(hx + 14 * s + side * 4 * s, hy + 6 * s, 2 * s, 3 * s, OL)
    if (t % 3.4) > .12:
        for side in (-1, 1): d.ell(hx - 2 * s + side * 10 * s, hy - 8 * s, 3 * s, 3 * s, OL)
    d.poly([(hx - 20 * s, hy + 24 * s), (hx - 6 * s, hy + 32 * s), (hx - 20 * s, hy + 40 * s)], (30, 30, 36))   # bow tie
    d.poly([(hx + 8 * s, hy + 24 * s), (hx - 6 * s, hy + 32 * s), (hx + 8 * s, hy + 40 * s)], (30, 30, 36))
    d.line([(x + 30 * s, fy - 80 * s), (nx - 20 * s, fy - 110 * s + 40 * min(ph, .6) * s)], P1, 12 * s)        # trotter on the note

def chicken_tractor(d, x, fy, t, s=1.0):
    """A chicken driving a tiny orange tractor, very slowly."""
    d.rect(x - 50 * s, fy - 60 * s, x + 30 * s, fy - 26 * s, (240, 130, 30), r=6, ol=OL, w=3)
    d.rect(x + 10 * s, fy - 92 * s, x + 50 * s, fy - 40 * s, (240, 130, 30), r=4, ol=OL, w=3)
    d.line([(x - 40 * s, fy - 60 * s), (x - 44 * s, fy - 92 * s)], (40, 40, 44), 5)
    for k_ in range(3):
        ph = (t * 1.5 + k_ * .33) % 1
        d.ell(x - 44 * s - 6 * ph * s, fy - 96 * s - 40 * ph * s, (5 + 8 * ph) * s, (5 + 8 * ph) * s, (120, 120, 126, int(160 * (1 - ph))))
    rot = t * 3
    for wx, r_ in ((x + 30 * s, 34 * s), (x - 46 * s, 18 * s)):
        d.ell(wx, fy - r_, r_, r_, (30, 30, 34), OL, 2); d.ell(wx, fy - r_, r_ * .5, r_ * .5, (240, 130, 30))
        d.line([(wx, fy - r_), (wx + math.cos(rot) * r_ * .5, fy - r_ + math.sin(rot) * r_ * .5)], OL, 3)
    hx, hy = x - 8 * s, fy - 100 * s + abs(math.sin(t * 6)) * 3          # the chicken at the wheel
    d.ell(hx, hy + 14 * s, 22 * s, 20 * s, (250, 250, 246), OL, 2)
    d.ell(hx + 10 * s, hy - 12 * s, 14 * s, 14 * s, (250, 250, 246), OL, 2)
    d.poly([(hx + 4 * s, hy - 24 * s), (hx + 10 * s, hy - 34 * s), (hx + 16 * s, hy - 24 * s)], (220, 40, 40))
    d.poly([(hx + 22 * s, hy - 14 * s), (hx + 34 * s, hy - 10 * s), (hx + 22 * s, hy - 6 * s)], (246, 170, 40), OL, 1.5)
    d.ell(hx + 20 * s, hy - 2 * s, 4 * s, 5 * s, (220, 40, 40))
    if (t % 2.7) > .12: d.ell(hx + 14 * s, hy - 14 * s, 2.5 * s, 2.5 * s, OL)
    d.line([(hx + 14 * s, hy + 10 * s), (x + 22 * s, fy - 80 * s)], (40, 40, 44), 3); d.ell(x + 22 * s, fy - 80 * s, 8 * s, 3 * s, (40, 40, 44))

def jet_snail(d, x, fy, t, s=1.0):
    """A snail with a jet engine strapped to its back (engine at the rear), crawling slowly."""
    d.poly(spline([(x - 70 * s, fy), (x - 76 * s, fy - 20 * s), (x - 60 * s, fy - 30 * s), (x + 50 * s, fy - 22 * s), (x + 64 * s, fy)], 5), (170, 200, 140), OL, 2)
    d.line([(x - 66 * s, fy - 26 * s), (x - 80 * s, fy - 58 * s)], (150, 180, 120), 5); d.line([(x - 56 * s, fy - 28 * s), (x - 62 * s, fy - 62 * s)], (150, 180, 120), 5)
    d.ell(x - 80 * s, fy - 60 * s, 5 * s, 5 * s, OL); d.ell(x - 62 * s, fy - 64 * s, 5 * s, 5 * s, OL)
    d.ell(x, fy - 52 * s, 40 * s, 36 * s, (200, 130, 70), OL, 3)
    d.arc(x, fy - 52 * s, 24 * s, 22 * s, 0, 300, (140, 80, 40), 4); d.arc(x, fy - 52 * s, 10 * s, 9 * s, 0, 300, (140, 80, 40), 3)
    d.rect(x + 10 * s, fy - 104 * s, x + 90 * s, fy - 74 * s, (170, 176, 186), r=14 * s, ol=OL, w=2)   # jet engine on the back
    d.ell(x + 12 * s, fy - 89 * s, 8 * s, 15 * s, (60, 64, 72), OL, 2)
    d.rect(x + 30 * s, fy - 76 * s, x + 40 * s, fy - 60 * s, (60, 60, 66))
    fl = 20 + 10 * math.sin(t * 40)
    d.poly([(x + 90 * s, fy - 98 * s), (x + (90 + fl) * s, fy - 89 * s), (x + 90 * s, fy - 80 * s)], (255, 150, 40))
    d.poly([(x + 90 * s, fy - 94 * s), (x + (90 + fl * .6) * s, fy - 89 * s), (x + 90 * s, fy - 84 * s)], (255, 240, 160))
    d.ell(x + 30 * s, fy - 2, 70 * s, 4 * s, (200, 230, 250, 90))                                  # slime trail

ODD = dict(penguin=penguin, pony=pony, pig=pig, chicken_tractor=chicken_tractor, jet_snail=jet_snail)
def oddity(img, t, sc):
    x = C.ODD_X[sc] if hasattr(C, 'ODD_X') else 850
    drift = C.ODD_DRIFT * (t - SCENES[sc]) if hasattr(C, 'ODD_DRIFT') else 0
    ODD[C.ODDITY](D(img), x + drift, 990, t, C.ODD_S)

# ================================================================ performance schedules
MOODS = {'angry': ('point', 'up', dict(brows='angry', eyes='wide')),
         'furious': ('up', 'up', dict(brows='angry', eyes='wide', sweat=1)),
         'shock': ('head', 'head', dict(brows='up', eyes='wide', sweat=1)),
         'confused': ('shrug', 'shrug', dict(brows='worried')),
         'curious': ('chin', 'rest', dict(brows='up')),
         'point': ('rest', 'point', dict(brows='angry', eyes='wide')),
         'impressed': ('hip', 'hip', dict(brows='up', eyes='wide', smile=1)),
         'deflated': ('rest', 'open', dict(brows='flat', tired=0.45)),
         'cross': ('cross', 'cross', dict(brows='angry', smile=-1)),
         'worried': ('chin', 'rest', dict(brows='worried', eyes='wide', smile=-1)),
         'calm': ('rest', 'rest', dict(brows='flat'))}
def mood(m): a, b, ex = MOODS[m]; return a, b, dict(ex)

def buyer_sched():
    s = [(0.0,) + mood(C.LINES[0][3])]
    listen = 'cross'
    for li, ln in enumerate(C.LINES):
        spk, _, sc, m = ln[:4]
        if spk == 'B':
            a, b, ex = mood(m)
            s.append((LS[li] - .08, a, b, ex))
            if len(ln) > 4: s.append((T_((li, ln[4])), ) + mood(ln[5]))     # mid-line beat
            s.append((LE[li] + .15, 'rest', 'rest', dict(ex, eyes='')))
            listen = 'calm' if m in ('deflated', 'impressed', 'curious') else 'cross'
        elif m:
            s.append((T_((li, ln[4])) if len(ln) > 4 else LE[li] - .1,) + mood(m))
        if li + 1 < NL and C.LINES[li + 1][2] != sc:
            s.append((SCENES[C.LINES[li + 1][2]], 'rest', 'rest', dict(brows='angry')))
    s.append((T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide')))
    return sorted(s, key=lambda e: e[0])

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = ['open', 'present', 'offer']
    k = 0
    for li, ln in enumerate(C.LINES[:-1]):
        if ln[0] == 'S':
            s += [(LS[li] - .05, G[k % 3], 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]; k += 1
    s += [(T_FINAL, 'open', 'clasp', dict(look=0)), (LE[LAST] + .3, 'clasp', 'clasp', dict(look=0))]
    return sorted(s, key=lambda e: e[0])

BS, SS_ = buyer_sched(), sales_sched()

# ================================================================ world per scene
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    bgf, life = SETS[C.SETS[sc]['kind']]
    img = bgf(sc).copy()
    if life: life(img, t, sc)
    oddity(img, t, sc)
    d = D(img)
    f = int(round(t * FPS))
    t_in = SCENES[sc]
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.25), 150, 11
    elif sc == NSC - 1:
        walk_k, bx0, dur_w = prog(t, t_in, 1.0), 40, 8
    else:
        walk_k, bx0, dur_w = prog(t, t_in, .75), -60, 13
    bx = bx0 + (270 - bx0) * oc(walk_k)
    for who, x, sched, cfg, spk in (('S', 670, SS_, SALES, 'S'), ('B', bx, BS, BUYER, 'B')):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[spk][min(f, len(MOUTH[spk]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        st['dy'] = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3 + (-4 if talking(spk, t) and (f // 4) % 2 else 0)
        if who == 'B' and walk_k < 1:
            st['walk'] = t * dur_w
            st['dy'] -= abs(math.sin(t * dur_w)) * 10
        if st.get('sweat'): st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
    return img

PUNCH = [(T_(r), a) for r, a in C.PUNCH]
def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0:
        z = 1.08 - 0.05 * oc(prog(t, 0, 1.4)) + 0.01 * math.sin(t * .5)
        if hasattr(C, 'CLOSE') and t >= T_(C.CLOSE):
            z = 1.16 + 0.03 * io(prog(t, T_(C.CLOSE), 5)); sx = -40
    elif sc < NSC - 1:
        z = 1.05 + 0.015 * io(prog(t, t0, 7))
        sx = 46 * (1 - oc(prog(t, t0, 1.4))) + C.SETS[sc].get('drift', 0) * io(prog(t, t0 + 1.2, 5))
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        pk = io(prog(t, T_FINAL - .05, .5))
        z += 0.14 * pk; sx = 150 * pk
    for tp, amt in PUNCH + [(T_FINAL, .05)]:
        if tp <= t < tp + .5: z += amt * (1 - oc(prog(t, tp, .5)))
    for tp in [T_(r) for r in getattr(C, 'SHAKE', [])]:
        if tp - .05 <= t < tp + .7:
            k_ = 1 - prog(t, tp - .05, .75); sx += 14 * k_ * math.sin(t * 61); sy += 10 * k_ * math.sin(t * 47 + 1)
    return z, sx, sy

def shoot(t, sc=None):
    wimg = world(t, sc)
    z, sx, sy = camera(t if sc is None else max(t, SCENES[sc]))
    ax, ay = CX * K, 1150 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    return wimg.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')

# ================================================================ overlays
INK2, DRED = (24, 20, 16), (176, 20, 30)
def rows_of(rows): return tuple((t_, s_, DRED if c == 'red' else INK2) for t_, s_, c in rows)
CARDS = []
for c in C.CARDS:
    c = dict(c); c['t0'] = T_(c['at'])
    c['t1'] = T_(c['until']) if c.get('until') is not None else scene_end(scene_at(c['t0'])) + .05
    assert c['t0'] >= OVERLAY_START, ('overlay inside the hook', c)
    CARDS.append(c)

@lru_cache(None)
def stat_img(big, sub, col):
    bs = 150
    while font(bs).getlength(big) > 700: bs -= 4
    w_ = max(int(font(bs).getlength(big)), int(font(44).getlength(sub))) + 100
    im = Image.new('RGBA', (w_ * K, 290 * K), (0, 0, 0, 0)); d = D(im)
    d.rect(8, 12, w_ - 2, 288, (0, 0, 0, 100), r=30); d.rect(0, 0, w_ - 10, 276, (14, 16, 22, 235), r=30, ol=col, w=6)
    d.text((w_ - 10) / 2, 116, big, bs, col, stroke=4, sc=(0, 0, 0))
    d.text((w_ - 10) / 2, 226, sub, 44, (255, 255, 255), path=FONT_X)
    return im

def overlays(t):
    if t < OVERLAY_START: return None
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    used = False
    for c in CARDS:
        a = window(t, c['t0'], c['t1'], .1, .25)
        if a <= 0: continue
        used = True
        s = popin(t, c['t0'], .35)
        x, y, rot = c.get('x', CX), c.get('y', 520), c.get('rot', -2)
        if c['kind'] == 'photo':
            put(img, photo_card(c['img'], c['label'], c.get('bar', (24, 30, 44)), (255, 255, 255), c.get('w', 440)), x, y, s, a, rot)
        elif c['kind'] == 'info':
            put(img, info_card(rows_of(c['rows'])), x, y, s, a, rot=-1.5)
        elif c['kind'] == 'tag':
            sw = math.sin((t - c['t0']) * 6) * 4 * math.exp(-(t - c['t0']) * 2)
            put(img, price_tag(c['txt'], c['sub'], TAG), x, y, s * .9, a, rot=sw - 3)
        elif c['kind'] == 'stamp':
            put(img, stamp_img(c['txt'], c.get('col', RED)), x, y, (2.2 - 1.2 * oc(prog(t, c['t0'], .22))), a, rot=c.get('rot', -8))
        elif c['kind'] == 'stat':
            put(img, stat_img(c['big'], c['sub'], c.get('col', TAG)), x, y, s, a, rot=c.get('rot', 0))
    if t >= T_CARD:
        used = True
        fa = prog(t, T_CARD, .25); d = D(img)
        n = len(C.FINAL)
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (n - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(C.FINAL):
            k_ = popin(t, T_CARD + .08 * i, .3)
            col = TAG if col == 'tag' else (255, 255, 255) if col == 'white' else (210, 214, 224)
            if k_ > .05:
                d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if used else None

FINAL_Y0, FINAL_DY = 430, 104
def final_boxes():
    out = []
    for i, (txt, size, _) in enumerate(C.FINAL):
        f = font(size); bb = f.getbbox(txt, anchor='mm', stroke_width=4)
        y = FINAL_Y0 + FINAL_DY * i; cap = f.getbbox('H')[3] - f.getbbox('H')[1]
        out.append(dict(text=txt, x0=CX + bb[0], x1=CX + bb[2], y0=y + bb[1], y1=y + bb[3], cap_height=cap))
    return out

def onscreen():
    o = [C.BRAND.get('name', '')] + [f[0] for f in C.FINAL]
    for c in C.CARDS:
        o += [c.get(k, '') for k in ('label', 'txt', 'sub', 'big')] + [r[0] for r in c.get('rows', ())]
    for S in C.SETS:
        o += list(S.get('labels', [])) + [S.get('title', '')] + [b[0] for b in S.get('bars', [])]
    return [x for x in o if x]

# ================================================================ frame
TR = 0.4
def frame(n):
    t = n / FPS
    tr = next((s for s in SCENES[1:] if s - TR / 2 <= t < s + TR / 2), None)
    if tr is None:
        img = shoot(t)
    else:
        k = io(prog(t, tr - TR / 2, TR)); sc_new = SCENES.index(tr)
        a, b = shoot(min(t, tr - .001), sc_new - 1), shoot(max(t, tr), sc_new)
        img = Image.new('RGBA', (W, H), (0, 0, 0, 255)); off = int(W * k)
        img.alpha_composite(a, (-off, 0)); img.alpha_composite(b, (W - off, 0))
        bl = math.sin(math.pi * k)
        if bl > .05:
            smear = img.resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
            img = Image.blend(img, smear, min(.85, bl))
    if hasattr(C, 'CLOSE') and T_(C.CLOSE) <= t < T_(C.CLOSE) + .3:
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.45 * (1 - prog(t, T_(C.CLOSE), .3)))
    ov = overlays(t)
    if ov is not None:
        img.alpha_composite(ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA'))
    if BEAT[0] + .1 <= t < T_FINAL:
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.22 * io(prog(t, BEAT[0] + .1, .5)))
    if T_FINAL <= t < T_FINAL + .5:
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.25 * (1 - prog(t, T_FINAL, .5)))
    if t >= T_CARD:
        k_ = io(prog(t, T_CARD, 1.0)) * .45; v = vignette()
        img.alpha_composite(Image.merge('RGBA', (*v.split()[:3], v.getchannel('A').point(lambda p: int(p * k_)))))
    captions(img, t)
    return img.convert('RGB').tobytes()

# ================================================================ thumbnail
def thumb(out):
    img = shoot(T_(C.THUMB_T)).convert('RGBA')
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    for y in range(0, 1000): sd.line([(0, y), (W, y)], (0, 0, 0, int(200 * (1 - y / 1000) ** 1.2)))
    img.alpha_composite(sh)
    big = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    put(big, photo_card(C.THUMB_PHOTO, C.THUMB_LABEL, C.BRAND['accent'], (255, 255, 255), 620), CX, 770, 1.0, 1.0, -3)
    d = D(big)
    put_logo(big, CX, 110, 70, white=C.BRAND.get('logo_white_on_dark', True))
    d = D(big)
    y = 240
    for txt, col in C.THUMB:
        size = 120
        while font(size).getlength(txt) > 860: size -= 4
        d.text(CX, y, txt, size, TAG if col == 'tag' else (255, 255, 255), stroke=10, sc=(10, 10, 16)); y += size * 1.08
    img.alpha_composite(big.resize((W, H), Image.LANCZOS))
    img.convert('RGB').save(out)

# ================================================================ audio
def build_audio(voice, out_wav):
    SR = sfx.SR
    def dec(path, ss=0.0):
        return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(ss), '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                            capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    v = dec(voice)
    n = int(DUR * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rng = np.random.default_rng(3); T_a = np.arange(n) / SR
    def lpf(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
    bed = lpf(rng.standard_normal(n), 60) * 0.10 + 0.004 * np.sin(2 * np.pi * 110 * T_a)
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def sting():
        d = 2.4; tt = np.arange(int(SR * d)) / SR; s = np.zeros_like(tt)
        for f in (73.4, 110.0, 146.8, 174.6, 220.0):
            for det in (-0.6, 0.6): s += ((tt * (f + det)) % 1 * 2 - 1)
        s = lpf(s, 6) * np.exp(-tt * 2.2) * np.minimum(1, tt * 200) * .09
        s += np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 5) * .9
        s += (rng.standard_normal(len(tt)) - lpf(rng.standard_normal(len(tt)), 4)) * np.exp(-tt * 2.6) * .25
        return s
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    for k_ in range(4): add(0.02 + k_ * 0.3, step(), .5)
    for s_ in SCENES[1:]:
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .35)
        for k_ in range(3): add(s_ + .08 + k_ * .25, step(), .35)
    for c in CARDS:
        snd = dict(photo=(sfx.pop(), .3), info=(sfx.stamp(), .3), tag=(sfx.cha_ching(), .3), stamp=(sfx.stamp(), .4),
                   stat=(sfx.ding(1320, .6), .18))[c['kind']]
        add(c['t0'] - .03, *snd)
    for ref, name, vol in getattr(C, 'SFX', []):
        add(T_(ref), getattr(sfx, name)(), vol)
    for k_ in range(2): add(BEAT[0] + .2 + k_ * .4, click(4200, 5200, .03) * .5, .6)
    add(T_FINAL - .02, sting(), .7); add(T_CARD, sfx.pop(), .35)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s
    # user's background track: under the dialogue, ducked while anyone speaks, faded at the end
    mus = np.zeros(n)
    if os.path.exists(MUSIC):
        m = dec(MUSIC, getattr(C, 'MUSIC_SS', 0.0))[:n]; mus[:len(m)] = m
        mus /= (np.sqrt(np.mean(mus ** 2)) + 1e-9)
        env = np.zeros(n)
        for w in WORDS: env[int((w['s'] - .1) * SR):int((w['e'] + .15) * SR)] = 1
        env = lpf(env, int(SR * .12))
        mus *= (0.075 - 0.045 * env) * np.clip((DUR - T_a) / 1.5, 0, 1)
    mixd = v * 1.0 + fxa[:n] * 0.55 + bed * 0.4 + mus
    mixd = np.clip(mixd / max(1.0, np.abs(mixd).max() / 0.95), -1, 1)
    tmp = out_wav + '.pre.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', tmp], input=mixd.tobytes(), check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', af, '-ar', '48000', '-ac', '2', tmp + '2.wav'], check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', tmp + '2.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = float(r.split('I:')[-1].split('LUFS')[0]); tp = float(r.split('Peak:')[-1].split('dBFS')[0])
    g = min(-14.0 - I, -1.5 - tp)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp + '2.wav', '-af', f'volume={g:.2f}dB', out_wav], check=True)
    os.remove(tmp); os.remove(tmp + '2.wav')

def _init(voice): load_mouth(voice)

if __name__ == '__main__':
    mode = sys.argv[2]
    if mode == 'still':
        load_mouth(sys.argv[5]); Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[3]) * FPS))).save(sys.argv[4])
    elif mode == 'sheet':                                    # contact sheet of times: sheet OUT.png VOICE t1 t2 ...
        load_mouth(sys.argv[4]); ts = [float(x) for x in sys.argv[5:]]
        cols = 4; rows_ = (len(ts) + cols - 1) // cols; tw, th = 270, 480
        S = Image.new('RGB', (tw * cols, th * rows_))
        for i, tt in enumerate(ts):
            S.paste(Image.frombytes('RGB', (W, H), frame(int(tt * FPS))).resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
        S.save(sys.argv[3])
    elif mode == 'thumb':
        load_mouth(sys.argv[4]); thumb(sys.argv[3])
    elif mode == 'meta':
        json.dump(dict(captions=caption_boxes(), final=final_boxes(), onscreen=onscreen(), duration=DUR, size=[W, H], fps=FPS,
                       scenes=SCENES), open(sys.argv[3], 'w'), indent=1)
    elif mode == 'video':
        voice, out = sys.argv[3], sys.argv[4]
        t_end = float(sys.argv[5]) if len(sys.argv) > 5 else DUR
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        wav = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(voice, wav)
        nf = int(min(DUR, t_end) * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-maxrate', '13M',
                               '-bufsize', '26M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
                               '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(voice,)) as pool:
            for i, buf in enumerate(pool.imap(frame, range(nf), chunksize=4)):
                ff.stdin.write(buf)
                if i % 300 == 0: print(f'frame {i}/{nf}', flush=True)
        ff.stdin.close(); ff.wait(); os.remove(wav)
        print('done', out)
