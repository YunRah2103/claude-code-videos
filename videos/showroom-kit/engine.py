"""Showroom skit engine shared by the car-twin videos (honda-prologue-is-a-chevy, tesla-fsd-subscription, gr86-vs-brz,
outlander-is-a-rogue, blazer-ev-no-carplay). Built on bmw-heated-seats/src/render.py: same cast, poses, lip sync,
captions, cards and mix chain. New here: real car photos on a glossy display platform that slide out and in on topic
changes, floor reflections of the cars and the two characters, a vivid per-brand showroom, a salesman dressed for the
brand, one background oddity per scene, a hook that is moving and speaking from frame 1, and a thumbnail mode.
An episode's src/render.py calls engine.main(SRC) with script.py (dialogue) and show.py (cars, scenes, cards) in SRC.
Usage (from the episode's src): python render.py video VOICE.wav OUT.mp4 | still T OUT.png [VOICE] | meta OUT.json
                                | thumb OUT.png"""
import importlib.util, json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import sfx

W, H, FPS, K = 1080, 1920, 30, 2
CX = 459                                   # composition centre (left 85% of the width; the right edge is platform UI)
CEIL, WALL_Y, FEET_Y = 84, 600, 1760
PLAT_Y = 736                               # platform top: car tyres touch this line
BUYER_X, SALES_X = 236, 690
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
CARS_DIR = os.path.expanduser('~/.cache/showroom/cars')
CLEAN = 3.0                                # no title, label, card or overlay before this (captions only)
CARD_Y = 1468                              # cards sit over the legs, below the captions
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



# ================================================================ episode setup
def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def words_of(text): return text.replace('...', '').split()

def setup(src):
    """Load script.py, show.py and words.json from an episode's src dir and derive the timeline."""
    g = globals()
    g['HERE'] = src
    g['SCRIPT'] = _load(os.path.join(src, 'script.py'), 'script')
    g['SHOW'] = _load(os.path.join(src, 'show.py'), 'show')
    g['WORDS'] = json.load(open(os.path.join(src, 'words.json')))
    L = {}
    for w in WORDS: L.setdefault(w['line'], []).append(w)
    g['LINES'] = L
    g['LS'] = {k: v[0]['s'] for k, v in L.items()}; g['LE'] = {k: v[-1]['e'] for k, v in L.items()}
    g['DUR'] = round(WORDS[-1]['e'] + 2.3, 2)
    SL = SCRIPT.LINES; n = len(SL)
    starts = [0.0]
    for li in range(1, n):
        if SL[li][2] != SL[li - 1][2]: starts.append(round((LE[li - 1] + LS[li]) / 2, 3))
    g['SCENES'] = starts
    g['NSC'] = len(starts)
    g['T_FINAL'] = LS[n - 1]; g['BEAT'] = (LE[n - 2], LS[n - 1]); g['T_CARD'] = LE[n - 1] + 0.3
    em = []
    for li, (_, text, *_r) in enumerate(SL):
        for i, w in enumerate(words_of(text)):
            if w.startswith('*'): em.append(L[li][i]['s'])
    g['EMPH'] = sorted(em)
    g['BRAND'] = BRANDS[SHOW.BRAND]
    so = SHOW.SALES
    g['SALES'] = dict(SALES0, suit=hexc(so['suit']), suit2=tuple(int(c * .72) for c in hexc(so['suit'])),
                      shirt=hexc(so.get('shirt', 'f7f7fa')), tie=hexc(so['tie']) if so.get('tie') else None,
                      pants=hexc(so.get('pants', so['suit'])), badge=hexc(so.get('badge', 'ffffff')))
    g['VOICE_CACHE'] = os.path.expanduser(f'~/.cache/{os.path.basename(os.path.dirname(os.path.abspath(src)))}/voice.wav')
    g['CHUNKS'] = chunks()
    g['BS'], g['SS_'] = buyer_sched(), sales_sched()
    g['CARDS'] = [dict(c, sc=i, t0=max(CLEAN, when(c.get('at'), i)), t1=when(c.get('until'), i, end=True))
                  for i, s in enumerate(SHOW.SCENES) for c in s.get('cards', ())]
    for c in CARDS:                                          # a chip panel opens with its first row, never empty
        refs = [r[3] for r in c.get('rows', ()) if c['kind'] == 'chips' and r[3] is not None]
        if refs: c['t0'] = max(c['t0'], min(when(r, c['sc']) for r in refs))
    assert len(SHOW.SCENES) == NSC, (len(SHOW.SCENES), NSC)

def word_t(line, txt=None, nth=0):
    if txt is None: return LS[line]
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]

def when(ref, sc, end=False):
    """Card timing: None -> scene start / end, int -> line start, (line, word) -> word start, (line, None) -> line end."""
    if ref is None:
        return (SCENES[sc] + .35) if not end else (SCENES[sc + 1] + .05 if sc + 1 < NSC else T_CARD)
    if isinstance(ref, int): return LS[ref] - .05
    if ref[1] is None: return LE[ref[0]] + .1
    return word_t(*ref) - .05

def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)

# ================================================================ emblems (hand-drawn generic shapes)
OL = (26, 26, 46)
def em_h(d, cx, cy, s=1.0, col=(226, 230, 236)):
    """Flared H inside a wide rounded trapezoid."""
    d.poly(spline([(cx - 74 * s, cy - 56 * s), (cx + 74 * s, cy - 56 * s), (cx + 62 * s, cy + 50 * s), (cx - 62 * s, cy + 50 * s)], 3),
           None, col, max(2, 9 * s))
    for side in (-1, 1):
        d.poly([(cx + side * 44 * s, cy - 42 * s), (cx + side * 26 * s, cy - 42 * s), (cx + side * 22 * s, cy + 38 * s),
                (cx + side * 36 * s, cy + 38 * s)], col)
    d.rect(cx - 26 * s, cy - 8 * s, cx + 26 * s, cy + 6 * s, col)
def em_t(d, cx, cy, s=1.0, col=(226, 32, 40)):
    """Arched T with a stem."""
    d.poly(spline([(cx - 70 * s, cy - 44 * s), (cx, cy - 62 * s), (cx + 70 * s, cy - 44 * s), (cx + 66 * s, cy - 32 * s),
                   (cx, cy - 46 * s), (cx - 66 * s, cy - 32 * s)], 3), col)
    d.poly([(cx - 30 * s, cy - 40 * s), (cx + 30 * s, cy - 40 * s), (cx + 10 * s, cy - 28 * s), (cx + 6 * s, cy + 64 * s),
            (cx - 6 * s, cy + 64 * s), (cx - 10 * s, cy - 28 * s)], col)
def em_ovals(d, cx, cy, s=1.0, col=(236, 234, 228)):
    for rx, ry, dy in ((70, 46, 0), (44, 18, -20), (20, 46, 2)):
        d.ell(cx, cy + dy * s, rx * s, ry * s, None, col, max(1.5, 8 * s))
def em_diamonds(d, cx, cy, s=1.0, col=(232, 16, 36)):
    """Three diamonds meeting at the centre."""
    for a in (-90, 30, 150):
        r = math.radians(a); ux, uy = math.cos(r), math.sin(r); px, py = -uy, ux
        L, Wd = 62 * s, 22 * s
        d.poly([(cx, cy), (cx + ux * L / 2 + px * Wd, cy + uy * L / 2 + py * Wd), (cx + ux * L, cy + uy * L),
                (cx + ux * L / 2 - px * Wd, cy + uy * L / 2 - py * Wd)], col)
def em_bowtie(d, cx, cy, s=1.0, col=(242, 190, 40)):
    pts = [(-88, -12), (-34, -12), (-26, -34), (26, -34), (34, -12), (88, -12), (76, 14), (26, 14), (20, 34), (-30, 34),
           (-26, 14), (-76, 14)]
    d.poly([(cx + x * s, cy + y * s) for x, y in pts], col, (120, 90, 20), max(1.5, 4 * s))

BRANDS = {
    'honda': dict(wall=((22, 24, 30), (40, 42, 50)), panel=(30, 32, 40), led=(236, 30, 44), ceil=(16, 16, 20), name='H O N D A',
                  namecol=(250, 250, 252), emb=em_h, embcol=(232, 234, 240), floor=((26, 26, 30), (8, 8, 10)), plat=(232, 30, 44)),
    'tesla': dict(wall=((228, 230, 236), (248, 248, 250)), panel=(238, 240, 244), led=(232, 24, 38), ceil=(250, 250, 252), name='T E S L A',
                  namecol=(18, 18, 22), emb=em_t, embcol=(226, 26, 36), floor=((40, 42, 48), (10, 10, 12)), plat=(240, 240, 248)),
    'toyota': dict(wall=((20, 20, 24), (36, 36, 42)), panel=(28, 28, 34), led=(240, 16, 34), ceil=(14, 14, 16), name='T O Y O T A',
                   namecol=(250, 250, 252), emb=em_ovals, embcol=(236, 236, 240), floor=((28, 28, 32), (8, 8, 10)), plat=(240, 16, 34)),
    'mitsubishi': dict(wall=((34, 36, 42), (58, 60, 68)), panel=(44, 46, 54), led=(236, 12, 30), ceil=(22, 22, 26),
                       name='M I T S U B I S H I', namecol=(250, 250, 252), emb=em_diamonds, embcol=(236, 16, 36),
                       floor=((30, 30, 34), (8, 8, 10)), plat=(236, 12, 30)),
    'chevrolet': dict(wall=((14, 26, 54), (26, 44, 84)), panel=(20, 34, 66), led=(250, 196, 40), ceil=(10, 18, 38), name='C H E V R O L E T',
                      namecol=(250, 250, 252), emb=em_bowtie, embcol=(244, 192, 42), floor=((24, 28, 38), (6, 8, 12)), plat=(250, 196, 40)),
}

# ================================================================ showroom
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def glow(img, draw_fn, blur=18, gain=1.0):
    """Draw shapes on a black layer, blur it and add it (screen) for neon/LED glow."""
    lay = Image.new('RGB', img.size, (0, 0, 0)); draw_fn(D(lay))
    g_ = lay.filter(ImageFilter.GaussianBlur(blur * K))
    a = np.asarray(img).astype(np.int16) + (np.asarray(g_).astype(np.int16) * gain).astype(np.int16) + np.asarray(lay).astype(np.int16) // 2
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

@lru_cache(None)
def bg_showroom():
    B = BRAND
    arr = np.concatenate([grad(WALL_Y * K, W * K, *B['wall']), grad((H - WALL_Y) * K, W * K, *B['floor'])])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-60, W, 190):                                # tall wall panels
        d.rect(x + 10, CEIL + 20, x + 180, WALL_Y - 26, B['panel'], r=6)
    d.rect(0, 0, W, CEIL, B['ceil'])
    d.rect(0, WALL_Y - 10, W, WALL_Y, tuple(int(c * .6) for c in B['panel']))
    def leds(g):
        for x in range(-60, W, 190):
            g.line([(x + 10, CEIL + 40), (x + 10, WALL_Y - 40)], B['led'], 5)
        g.line([(0, CEIL + 3), (W, CEIL + 3)], (255, 246, 226), 6)          # ceiling light strip
        g.line([(0, WALL_Y - 12), (W, WALL_Y - 12)], B['led'], 6)
    img = glow(img, leds, 16, 1.3)
    # spotlight cones onto the platform
    cone = Image.new('L', img.size, 0); cd = ImageDraw.Draw(cone)
    for sx in (CX - 230, CX + 230):
        cd.polygon([(p * K, q * K) for p, q in [(sx - 40, CEIL), (sx + 40, CEIL), (sx + 300, PLAT_Y + 40), (sx - 300, PLAT_Y + 40)]], fill=46)
    cone = cone.filter(ImageFilter.GaussianBlur(30 * K))
    img = Image.composite(Image.new('RGB', img.size, (255, 248, 232)), img, cone)
    d = D(img)
    for px in (130, CX, 788):                                    # pendant spots
        d.line([(px, CEIL), (px, CEIL + 26)], (70, 74, 78), 3)
        d.rect(px - 26, CEIL + 24, px + 26, CEIL + 50, (36, 36, 40), r=6); d.ell(px, CEIL + 50, 20, 5, (255, 244, 210))
    # brand emblem and name on the wall, lit
    def sign(g):
        B['emb'](g, CX, 168, 0.95, B['embcol'])
        g.text(CX, 268, B['name'], 62 if len(B['name']) < 14 else 50, B['namecol'], path=FONT_B)
    img = glow(img, sign, 10, .55)
    d = D(img); B['emb'](d, CX, 168, 0.95, B['embcol'])
    d.text(CX, 268, B['name'], 62 if len(B['name']) < 14 else 50, B['namecol'], path=FONT_B)
    # glossy floor: mirrored wall strip, fading out
    strip = img.crop((0, (WALL_Y - 300) * K, W * K, WALL_Y * K)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(3 * K))
    m = Image.fromarray((np.linspace(110, 0, strip.height)[:, None] * np.ones((1, strip.width))).astype(np.uint8))
    img.paste(strip, (0, WALL_Y * K), m)
    d = D(img)
    for i, y in enumerate((640, 700, 790, 920, 1090, 1320, 1620)):                   # floor seams in perspective
        d.line([(0, y), (W, y)], (255, 255, 255, 14 + i * 2), 2)
    for k_ in range(-8, 9):
        d.line([(CX + k_ * 60, WALL_Y), (CX + k_ * 260, H)], (255, 255, 255, 12), 2)
    # platform: glossy black disc with an LED rim
    d.ell(CX, PLAT_Y + 26, 452, 62, (0, 0, 0, 120))
    d.ell(CX, PLAT_Y + 12, 446, 54, (12, 12, 14))
    d.ell(CX, PLAT_Y, 440, 48, (30, 30, 34))
    hl = Image.new('L', img.size, 0); ImageDraw.Draw(hl).ellipse([(CX - 300) * K, (PLAT_Y - 40) * K, (CX + 140) * K, (PLAT_Y - 4) * K], fill=60)
    img = Image.composite(Image.new('RGB', img.size, (255, 255, 255)), img, hl.filter(ImageFilter.GaussianBlur(14 * K)))
    img = glow(img, lambda g: g.arc(CX, PLAT_Y + 4, 444, 52, 0, 180, BRAND['plat'], 5), 10, 1.0)
    return img

# ================================================================ car photos on the platform
@lru_cache(None)
def car_img(name, w):
    im = Image.open(os.path.join(CARS_DIR, name + '.png')).convert('RGBA')
    h = int(w * im.height / im.width)
    return im.resize((int(w * K), int(h * K)), Image.LANCZOS)

@lru_cache(None)
def car_refl(name, w):
    c = car_img(name, w).transpose(Image.FLIP_TOP_BOTTOM)
    h = c.height
    g = np.clip(1 - np.arange(h) / (h * .55), 0, 1) ** 1.6 * .42
    a = (np.asarray(c.getchannel('A')).astype(np.float32) * g[:, None]).astype(np.uint8)
    c = c.filter(ImageFilter.GaussianBlur(1.5 * K)); c.putalpha(Image.fromarray(a))
    return c

@lru_cache(None)
def label_img(text, sub):
    f = font(26 * K, FONT_X); fs = font(18 * K, FONT_X)
    w = int(max(f.getlength(text), fs.getlength(sub)) / K) + 44
    im = Image.new('RGBA', (w * K, 72 * K), (0, 0, 0, 0)); d = D(im)
    d.rect(0, 0, w, 66, (10, 10, 14, 235), r=10, ol=BRAND['plat'] + (255,), w=3)
    d.text(w / 2, 22, sub, 18, (190, 194, 204), path=FONT_X)
    d.text(w / 2, 46, text, 26, (255, 255, 255), path=FONT_X)
    return im

def slots(n):
    return [(CX, 500)] if n == 1 else [(CX - 202, 372), (CX + 202, 372)]

def car_offsets(t, sc):
    """(car set scene index, x offset, speed) for the sets visible at time t: out to the right, in from the left."""
    T = SCENES[sc]
    out = []
    if sc > 0 and t < T + .34:
        k = io(prog(t, T - .2, .54)); out.append((sc - 1, 1150 * k, 1150 * 4 * k * (1 - k)))
    t0 = T + .06 if sc > 0 else -0.25
    k = prog(t, t0, .7)
    if k > 0:
        x = -1150 * (1 - oc(k)); out.append((sc, x, 1150 * 3 * (1 - k) ** 2 / .7 * (1 if k < 1 else 0)))
    return out

def draw_cars(img, t, sc):
    for csc, xo, v in car_offsets(t, sc):
        keys = SHOW.SCENES[csc]['cars']
        sl = slots(len(keys))
        for (cx, w), key in reversed(list(zip(sl, keys))):
            spec = SHOW.CARS[key]
            w_ = int(w * spec.get('scale', 1.0)); x = cx + spec.get('dx', 0) + xo
            c = car_img(spec['img'], w_)
            ch = c.height / K
            top = PLAT_Y + 6 - ch
            D(img).ell(x, PLAT_Y + 2, w_ * .5, 16, (0, 0, 0, 170))
            r = car_refl(spec['img'], w_)
            img.paste(r, (int((x - w_ / 2) * K), int((PLAT_Y + 4) * K)), r)
            if v > 900:                                                        # motion blur ghosts while sliding
                for g in (3, 2, 1):
                    gh = c.copy(); gh.putalpha(c.getchannel('A').point(lambda p: int(p * .22)))
                    img.paste(gh, (int((x - w_ / 2 - g * v * .009) * K), int(top * K)), gh)
            img.paste(c, (int((x - w_ / 2) * K), int(top * K)), c)
            la = prog(t, CLEAN, .3) * (1 if xo == 0 else max(0, 1 - abs(xo) / 300))
            if la > 0:
                lab = label_img(spec['label'], spec.get('sub', ''))
                if la < 1:
                    lab = lab.copy(); lab.putalpha(lab.getchannel('A').point(lambda p: int(p * la)))
                ly = top - 30 + spec.get('label_dy', 0)
                img.paste(lab, (int(x * K - lab.width / 2), int((ly - 36) * K)), lab)

# ================================================================ cast
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


# ================================================================ characters (tesla-locked cast)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES0 = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('1c1d22'), suit2=hexc('0e0f12'),
             shirt=hexc('f7f7fa'), tie=hexc('111114'), pants=hexc('1c1d22'), shoe=hexc('3a2a22'), glasses=False, hairstyle='part', lids=0.45)
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
    if c.get('badge'):                                      # dealer name badge in the brand colour
        d.rect(x + 46, top + 92, x + 100, top + 118, (245, 245, 248), r=4)
        bc = c['badge'] if isinstance(c['badge'], tuple) else (200, 30, 40)
        d.rect(x + 51, top + 97, x + 65, top + 113, bc, r=2)
        d.line([(x + 70, top + 101), (x + 94, top + 101)], (90, 90, 100), 3); d.line([(x + 70, top + 109), (x + 88, top + 109)], (150, 150, 160), 3)
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



MOUTH = None
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


# ---- performance schedules generated from the pose tag on each script line
B_POSE = {'shock': ('head', 'head', dict(brows='up', eyes='wide', sweat=1)),
          'point': ('point', 'rest', dict(brows='angry', eyes='wide')),
          'up': ('up', 'up', dict(brows='angry', eyes='wide', sweat=1)),
          'shrug': ('shrug', 'shrug', dict(brows='up')),
          'ask': ('rest', 'open', dict(brows='worried')),
          'angry': ('point', 'point', dict(brows='angry', eyes='wide')),
          'chin': ('chin', 'rest', dict(brows='worried', smile=-1)),
          'hip': ('hip', 'point', dict(brows='up', eyes='wide')),
          'final': ('rest', 'open', dict(brows='up', look=0))}
S_POSE = {'open': 'open', 'present': 'present', 'offer': 'offer', 'clasp': 'clasp', 'final': 'open'}

def buyer_sched():
    SL = SCRIPT.LINES; n = len(SL)
    s = [(-0.4, 'rest', 'rest', dict(brows='angry', eyes='wide'))]          # frame 1: arms already on their way up
    for li, (spk, _, _, tag) in enumerate(SL):
        if spk != 'B': continue
        lp, rp, ex = B_POSE[tag]
        s.append((-0.08 if li == 0 else LS[li] - .08, lp, rp, ex))
        nxt = next((LS[j] for j in range(li + 1, n) if SL[j][0] == 'B'), DUR)
        if li == n - 2:
            s.append((LE[li] + .2, 'rest', 'rest', dict(brows='up', look=0)))
        elif nxt - LE[li] > 2.2:
            s.append((LE[li] + .2, 'cross', 'cross', dict(brows='angry', smile=-1)))
        else:
            s.append((LE[li] + .2, 'rest', 'rest', dict(brows='angry')))
    return sorted(s, key=lambda e: e[0])

def sales_sched():
    SL = SCRIPT.LINES; n = len(SL)
    s = [(0.0, 'clasp', 'clasp', {})]
    for li, (spk, _, _, tag) in enumerate(SL):
        if spk != 'S': continue
        ex = dict(look=0) if li == n - 1 else {}
        s += [(LS[li] - .05, S_POSE[tag], 'clasp', ex), (LE[li] + .25, 'clasp', 'clasp', ex)]
    return sorted(s, key=lambda e: e[0])

# ================================================================ world
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    img = bg_showroom().copy()
    draw_cars(img, t, sc)
    od = SHOW.SCENES[sc]['odd']
    name, kw = (od, {}) if isinstance(od, str) else od
    fn = ODD[name]
    fn(img, t, t - SCENES[sc], **kw) if kw else fn(img, t, t - SCENES[sc])
    pl = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = D(pl)
    f = int(round(t * FPS))
    walk_k = prog(t, 0, .8)
    bx = 150 + (BUYER_X - 150) * oc(walk_k)                 # the buyer is still stepping in on frame 1
    for who, x, sched, cfg in (('S', SALES_X, SS_, SALES), ('B', bx, BS, BUYER)):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[who][min(f, len(MOUTH[who]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        breathe = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3
        st['dy'] = breathe + (-4 if talking(who, t) and (f // 4) % 2 else 0)
        if who == 'B' and walk_k < 1:
            st['walk'] = t * 12; st['dy'] -= abs(math.sin(t * 12)) * 8
        if st.get('sweat'): st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
        D(img).ell(x, FEET_Y - 8, 150, 20, (0, 0, 0, 110))                   # contact shadow
    # glossy floor: mirror the lower legs and shoes under the characters
    band = 230
    r = pl.crop((0, (FEET_Y - band) * K, W * K, FEET_Y * K)).transpose(Image.FLIP_TOP_BOTTOM)
    a = np.asarray(r.getchannel('A')).astype(np.float32) * (np.clip(1 - np.arange(r.height) / (r.height * .8), 0, 1) ** 1.4 * .36)[:, None]
    r.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.paste(r, (0, (FEET_Y - 14) * K), r)
    img.paste(pl, (0, 0), pl)
    return img

def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0:                                             # hook: pull out from close on the buyer as the car lands
        z = 1.16 - 0.11 * oc(prog(t, 0, 1.3)) + 0.02 * io(prog(t, 1.3, 6))
        sx = -90 * (1 - oc(prog(t, 0, 1.3)))
    else:
        z = (1.10 if sc % 2 else 1.04) + 0.025 * io(prog(t, t0, 6))
        sx = (-36 if sc % 2 else 24) * io(prog(t, t0, 6))
    punches = [(tp, .045) for tp in EMPH] + [(s_ + .5, .05) for s_ in SCENES[1:]]
    if t >= T_FINAL - .05:                                  # salesman turns to camera: push in on him
        pk = io(prog(t, T_FINAL - .05, .5))
        z += 0.16 * pk; sx = sx * (1 - pk) + 180 * pk
    for tp, amt in punches:
        if tp <= t < tp + .45: z += amt * (1 - oc(prog(t, tp, .45)))
    return z, sx, sy

def shoot(t, sc=None):
    wimg = world(t, sc)
    z, sx, sy = camera(t)
    ax, ay = CX * K, 1180 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    return wimg.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))

# ================================================================ overlays
GREEN, TAG, RED = (40, 190, 100), (255, 214, 64), (226, 48, 58)
INK2, DRED = (24, 20, 16), (176, 20, 30)
ROWCOL = {'ink': INK2, 'red': DRED, 'green': (18, 128, 62), 'blue': (24, 84, 190)}
CHIPCOL = {'green': GREEN, 'red': RED, 'gold': (226, 160, 20), 'blue': (40, 110, 220), 'grey': (96, 100, 112)}
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

def _unused_photo_card(name, label, bar, fg, w=400):
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


def rows_of(rows): return tuple((txt, size, ROWCOL[c]) for txt, size, c in rows)

def chip_panel(img, t, c, a):
    rows = c['rows']; two = c.get('two_line', False)
    step = 128 if two else 78
    y0 = CARD_Y - (len(rows) - 1) * step / 2 - (24 if two else 0)
    d = D(img)
    d.rect(64, y0 - 62, 836, y0 + (len(rows) - 1) * step + (100 if two else 58), (12, 14, 20, int(236 * a)), r=30)
    if c.get('title'):
        pass
    al = int(255 * a)
    for i, (lab, chip, col, ref) in enumerate(rows):
        t_r = max(c['t0'], when(ref, c['sc'])) if ref is not None else c['t0'] + .15 * i
        if t < t_r: continue
        ra = min(a, prog(t, t_r, .2)); k_ = popin(t, t_r, .3)
        w_ = font(32 * K).getlength(chip) / K
        cc = CHIPCOL[col]
        if two:
            y = y0 + i * step
            d.text(100, y, lab, 34, (226, 230, 240, int(255 * ra)), anchor='lm', path=FONT_X)
            d.rect(96, y + 28, 96 + (w_ + 36) * k_, y + 84, cc + (al,), r=12)
            if k_ > .6: d.text(96 + (w_ + 36) / 2, y + 57, chip, 32, (255, 255, 255, al))
        else:
            y = y0 + i * step
            d.text(100, y, lab, 34, (226, 230, 240, int(255 * ra)), anchor='lm', path=FONT_X)
            d.rect(800 - (w_ + 36) * k_, y - 28, 800, y + 28, cc + (al,), r=12)
            if k_ > .6: d.text(800 - (w_ + 36) / 2, y + 1, chip, 32, (255, 255, 255, al))

def overlays(t):
    if t < CLEAN: return None                               # nothing over the hook
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    used = False
    if t < T_CARD:
        for c in CARDS:
            if not (c['t0'] <= t <= c['t1']): continue
            a = window(t, c['t0'], c['t1'], .1, .25)
            if a <= 0: continue
            used = True
            if c['kind'] == 'card':
                put(img, info_card(rows_of(c['rows'])), CX, c.get('y', CARD_Y), popin(t, c['t0'], .35), a, rot=c.get('rot', -1.5))
            elif c['kind'] == 'chips':
                chip_panel(img, t, c, a)
            elif c['kind'] == 'stamp':
                k_ = prog(t, c['t0'], .22)
                put(img, stamp_img(c['text'], CHIPCOL[c.get('col', 'red')], c.get('size', 96)), CX, c.get('y', CARD_Y),
                    1.9 - .9 * oc(k_), a * min(1, k_ * 3), rot=c.get('rot', -8))
    if t >= T_CARD:                                          # final caption
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img); F = final_rows()
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(F) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(F):
            k_ = popin(t, T_CARD + .08 * i, .3)
            if k_ > .05:
                d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if used else None

FINAL_Y0, FINAL_DY = 420, 104
def final_rows():
    q = SHOW.FINAL_Q
    return [(q[0], 76, TAG)] + ([(q[1], 80, TAG)] if len(q) > 1 else []) + [
        ("Comment below.", 70, (255, 255, 255)), ("Next: another car", 64, (210, 214, 224)),
        ("that's secretly", 64, (210, 214, 224)), ("another car.", 64, (210, 214, 224))]

def final_boxes():
    out = []
    for i, (txt, size, _) in enumerate(final_rows()):
        f = font(size); bb = f.getbbox(txt, anchor='mm', stroke_width=4)
        y = FINAL_Y0 + FINAL_DY * i
        cap = f.getbbox('H')[3] - f.getbbox('H')[1]
        out.append(dict(text=txt, x0=CX + bb[0], x1=CX + bb[2], y0=y + bb[1], y1=y + bb[3], cap_height=cap))
    return out

def onscreen():
    txt = [BRAND['name']]
    for k, v in SHOW.CARS.items(): txt += [v['label'], v.get('sub', '')]
    for c in CARDS:
        if c['kind'] == 'card': txt += [r[0] for r in c['rows']]
        elif c['kind'] == 'chips': txt += [x for r in c['rows'] for x in r[:2]]
        else: txt.append(c['text'])
    return [x for x in txt if x] + [r[0] for r in final_rows()]

# ================================================================ frame
def streak(img, t):
    """A bright light sweep across the frame on each topic change."""
    for T in SCENES[1:]:
        if T - .12 <= t < T + .3:
            k = prog(t, T - .12, .42)
            x = -400 + 1900 * io(k)
            lay = Image.new('L', (W, H), 0)
            ImageDraw.Draw(lay).polygon([(x, 0), (x + 160, 0), (x - 260, H), (x - 420, H)], fill=int(120 * math.sin(math.pi * k)))
            lay = lay.filter(ImageFilter.GaussianBlur(26))
            img = Image.composite(Image.new('RGB', (W, H), (255, 255, 255)), img, lay)
    return img

def frame(n):
    t = n / FPS
    img = shoot(t)
    img = ImageEnhance.Color(ImageEnhance.Contrast(img).enhance(1.07)).enhance(1.12)   # vivid grade
    img = streak(img, t).convert('RGBA')
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

# ================================================================ audio
def build_audio(voice, out_wav):
    SR = sfx.SR
    v = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rng = np.random.default_rng(3); T_ = np.arange(n) / SR
    def lpf(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
    bed = lpf(rng.standard_normal(n), 60) * 0.10 + 0.004 * np.sin(2 * np.pi * 110 * T_)
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def tick(): return click(4200, 5200, .03) * .5
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
    add(0.0, sfx.whoosh(.4, 16), .5); add(.42, sfx.thump(.25), .4)              # the car lands on the platform on frame 1
    for s_ in SCENES[1:]:
        add(s_ - .22, sfx.whoosh(.45, 18), .45); add(s_ + .08, sfx.whoosh(.4, 14), .35); add(s_ + .62, sfx.thump(), .35)
    for c in CARDS:
        if c['kind'] == 'stamp': add(c['t0'], sfx.stamp(), .35)
        else: add(c['t0'], sfx.pop(), .28)
        if c['kind'] == 'chips':
            for i, (_, _, col, ref) in enumerate(c['rows']):
                tr = max(c['t0'], when(ref, c['sc'])) if ref is not None else c['t0'] + .15 * i
                add(tr, sfx.ding(1568 if col == 'green' else 1320, .5) if col in ('green', 'gold', 'blue') else
                    sfx.buzzer(.22) if col == 'red' else sfx.pop(), .16 if col != 'red' else .2)
    for tp in EMPH: add(tp, sfx.thump(.2), .22)
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


# ================================================================ captions
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


# ================================================================ thumbnail
def thumb(out):
    """Vertical thumbnail: big 2-4 word headline, the real car(s), the buyer's shocked face. Readable at small size."""
    T = SHOW.THUMB
    img = bg_showroom().copy()
    keys = T['cars']; gy = 1130
    sl = [(CX + 40, 800)] if len(keys) == 1 else [(CX - 175, 560), (CX + 245, 560)]
    d = D(img); d.ell(CX + 30, gy + 22, 500, 66, (8, 8, 10)); d.ell(CX + 30, gy + 8, 494, 58, (30, 30, 34))
    d.arc(CX + 30, gy + 12, 496, 60, 0, 180, BRAND['plat'], 5)
    for (cx, w), key in reversed(list(zip(sl, keys))):
        spec = SHOW.CARS[key]; w_ = int(w * spec.get('scale', 1.0)); c = car_img(spec['img'], w_)
        D(img).ell(cx, gy, w_ * .5, 22, (0, 0, 0, 170))
        r = car_refl(spec['img'], w_); img.paste(r, (int((cx - w_ / 2) * K), int((gy + 4) * K)), r)
        img.paste(c, (int((cx - w_ / 2) * K), int((gy + 6 - c.height / K) * K)), c)
        lab = label_img(spec['label'], spec.get('sub', ''))
        img.paste(lab, (int(cx * K - lab.width / 2), int((gy + 30) * K)), lab)
    st = dict(lpose=POSES['head'], rpose=POSES['head'], out_lpose=True, out_rpose=True, mouth=1.0, look=0, brows='up',
              eyes='wide', sweat=0.3)
    npc(img, 770, 2830, 1.45, BUYER, st)                     # the buyer's shocked face, big, bottom right
    img = img.resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Color(ImageEnhance.Contrast(img).enhance(1.1)).enhance(1.15).convert('RGBA')
    ov = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0)); d = D(ov)
    lines = T['headline']; y = 360
    for i, ln in enumerate(lines):
        size = 170
        while font(size).getlength(ln) > 980: size -= 4
        col = TAG if i == len(lines) - 1 else (255, 255, 255)
        d.text(W / 2, y, ln, size, col, stroke=14, sc=(10, 10, 16)); y += size * 1.02
    ov = ov.resize((W, H), Image.LANCZOS); img.alpha_composite(ov)
    img.convert('RGB').save(out)

def _init(voice):
    load_mouth(voice)

def main(src):
    setup(src)
    mode = sys.argv[1]
    if mode == 'still':
        load_mouth(sys.argv[4] if len(sys.argv) > 4 else VOICE_CACHE)
        Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif mode == 'meta':
        json.dump(dict(captions=caption_boxes(), final=final_boxes(), onscreen=onscreen(), duration=DUR, size=[W, H], fps=FPS,
                       scenes=SCENES, first_word=WORDS[0]['s']), open(sys.argv[2], 'w'), indent=1)
    elif mode == 'thumb':
        thumb(sys.argv[2])
    elif mode == 'video':
        voice, out = sys.argv[2], sys.argv[3]
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        wav = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(voice, wav)
        nf = int(DUR * FPS)
        a, b = (int(x) for x in sys.argv[4].split(':')) if len(sys.argv) > 4 else (0, nf)   # optional frame range for checks
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', f'{a / FPS:.3f}', '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                               '-maxrate', '13M', '-bufsize', '26M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                               '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(voice,)) as pool:
            for i, buf in enumerate(pool.imap(frame, range(a, b), chunksize=4)):
                ff.stdin.write(buf)
                if i % 150 == 0: print(f'frame {a + i}/{nf}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', out)

from oddities import ODD
