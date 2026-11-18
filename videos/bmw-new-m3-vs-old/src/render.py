"""BMW new M3 vs old skit: one flat, vivid BMW showroom, seven scenes. Real M3 photos (cut out by prep_cars.py) slide on
and off a display platform. Built on bmw-heated-seats/src/render.py: same cast, caption system, camera and mix chain.
One background oddity per scene (never mentioned). 1080x1920 @30.
Usage: python render.py video VOICE.wav OUT.mp4 | python render.py still T OUT.png [VOICE] | python render.py meta OUT.json"""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sfx

W, H, FPS, K = 1080, 1920, 30, 2
CX = 459                                   # composition centre (left 85% of width)
WALL_Y, FEET_Y, CEIL = 830, 1880, 84
HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
DUR = round(WORDS[-1]['e'] + 2.3, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/bmw-new-m3-vs-old/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
SC_LINE = [0, 2, 4, 6, 8, 10, 12]          # first dialogue line of each scene
SCENES = [0.0] + [LS[l] - 0.32 for l in SC_LINE[1:]]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
CAR_SC = ['e46', 'g80', 'e92', 'e46', 'g80', 'g80', 'g80']   # what is on the platform in each scene
T_FINAL = LS[14]
BEAT = (LE[13], LS[14])
T_CARD = LE[14] + 0.3                      # final caption card (last ~2 s)
T_BEST, T_E46A = word_t(0, 'best'), word_t(0, 'E46')
T_NO, T_NEW1 = LS[1], word_t(1, 'new')
T_NOSTR, T_20, T_GRILLE = word_t(2, 'nostrils'), word_t(3, 'twenty'), word_t(3, 'grille')
T_V8, T_414, T_503, T_OVER = word_t(4, 'V8'), word_t(4, 'Four'), word_t(5, 'five-oh'), word_t(5, 'over')
T_LIGHT, T_3400, T_3840, T_HEAVY, T_PRET = (word_t(6, 'lighter'), word_t(7, 'thirty-four'), word_t(7, 'thirty-eight'),
                                            word_t(7, 'heaviest'), word_t(7, 'pretend'))
T_WHY, T_ZERO, T_51, T_38, T_34 = (word_t(8, 'why'), LS[9], word_t(9, 'five-point'), word_t(9, 'three-point-eight'),
                                   word_t(9, 'three-point-four'))
T_FEEL, T_DROVE, T_PRAISE = word_t(10, 'feel'), word_t(11, 'drove'), word_t(11, 'praise')
T_PUNCH, T_AGREE = word_t(12, 'punched'), word_t(13, 'agree')

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

def bmw_badge(d, cx, cy, s=1.0):
    """Hand-drawn BMW-style roundel: black ring, silver rims, blue/white quarters."""
    d.ell(cx, cy, 60 * s, 60 * s, (18, 18, 22), (200, 206, 214), max(1, 5 * s))
    r = 36 * s
    d.ell(cx, cy, r, r, (250, 250, 252))
    for a0 in (270, 90):                                   # blue quarters: upper right and lower left
        d.d.pieslice(d.box(cx - r, cy - r, cx + r, cy + r), a0, a0 + 90, fill=(28, 105, 190))
    d.ell(cx, cy, r, r, None, (200, 206, 214), max(1, 3 * s))
    for i, ch in enumerate('BMW'):
        ang = math.radians(-140 + i * 50)
        d.text(cx + 48 * s * math.cos(ang), cy + 48 * s * math.sin(ang), ch, max(6, 15 * s), (240, 242, 246))


def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)


# ================================================================ showroom (flat, vivid BMW blue)
NAVY, BLUE, BLUE2 = (10, 24, 64), (0, 98, 200), (0, 78, 170)
M_LB, M_DB, M_RED = (0, 166, 226), (34, 44, 128), (228, 30, 38)
FLOOR = ((214, 222, 234), (244, 246, 250))
PLAT_Y = 812                                   # car ground line on the platform
@lru_cache(None)
def bg_showroom():
    arr = np.concatenate([grad(WALL_Y * K, W * K, BLUE, BLUE2), grad((H - WALL_Y) * K, W * K, *FLOOR)])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-60, W + 60, 180):                      # flat wall panels
        d.rect(x + 10, CEIL + 30, x + 170, WALL_Y - 80, (8, 110, 214), r=10)
        d.rect(x + 10, CEIL + 30, x + 30, WALL_Y - 80, (30, 128, 226), r=6)
    d.rect(0, 0, W, CEIL, NAVY)                            # ceiling with a dashed light strip
    for x in range(10, W, 90):
        d.rect(x, CEIL - 34, x + 54, CEIL - 22, (250, 246, 226), r=4)
    d.rect(0, CEIL, W, CEIL + 10, (6, 16, 44))
    for i, c in enumerate((M_LB, M_DB, M_RED)):            # M stripes along the base of the wall
        d.rect(0, WALL_Y - 64 + i * 18, W, WALL_Y - 46 + i * 18, c)
    d.rect(0, WALL_Y - 10, W, WALL_Y, (238, 240, 244))
    d.rect(0, WALL_Y, W, WALL_Y + 8, (150, 158, 172))
    for i, y in enumerate(range(WALL_Y + 70, H, 150)):     # glossy floor seams
        d.line([(0, y + i * 14), (W, y + i * 14)], (200, 208, 222), 3)
    for cx_ in (CX - 300, CX, CX + 300):                   # spotlights onto the platform
        img = spot(img, cx_, CEIL, 30, 230, PLAT_Y - CEIL, a=42)
    d = D(img)
    bmw_badge(d, CX - 205, 262, 1.2)
    d.text(CX + 52, 266, 'BMW', 150, (255, 255, 255), path=FONT_B)
    d.ell(CX, PLAT_Y + 6, 420, 52, (14, 18, 30))           # display platform with a blue LED rim
    d.ell(CX, PLAT_Y - 2, 414, 46, (52, 58, 74), M_LB, 5)
    d.ell(CX, PLAT_Y - 2, 360, 36, (64, 70, 86))
    return img.convert('RGBA')

# ---- real car cut-outs (prepared by prep_cars.py), ground = bottom of the tyres
CAR_FILES = {'e46': ('e46.png', 720), 'e92': ('e92.png', 720), 'g80': ('g80_side.png', 720)}
CAR_LABEL = {'e46': ('BMW M3 E46', '2001–2006'), 'e92': ('BMW M3 E92', '2008–2013'),
             'g80': ('BMW M3 G80', 'NEW · 2021–')}
@lru_cache(None)
def car_img(key):
    fn, w = CAR_FILES[key]
    im = Image.open(os.path.join(HERE, '..', 'assets', fn)).convert('RGBA')
    im = im.crop(im.getchannel('A').getbbox())
    if key == 'g80': im = im.transpose(Image.FLIP_LEFT_RIGHT)      # all cars face the same way (right)
    return im.resize((w * K, int(im.height * w / im.width) * K), Image.LANCZOS)

@lru_cache(None)
def plaque(key):
    t1, t2 = CAR_LABEL[key]
    w = int(max(font(46).getlength(t1), font(30, FONT_X).getlength(t2))) + 70
    im = Image.new('RGBA', (w * K, 128 * K), (0, 0, 0, 0)); d = D(im)
    d.rect(4, 8, w - 4, 124, (0, 0, 0, 70), r=16)
    d.rect(0, 0, w - 8, 116, (255, 255, 255), r=16, ol=NAVY, w=5)
    for i, c in enumerate((M_LB, M_DB, M_RED)):
        d.rect(24 + i * 22, 14, 42 + i * 22, 20, c)
    d.text((w - 8) / 2, 50, t1, 46, NAVY)
    d.text((w - 8) / 2, 92, t2, 30, (228, 30, 38) if 'NEW' in t2 else (90, 98, 116), path=FONT_X)
    return im

def car_slot(t):
    """[(key, x offset), ...] for the platform: the old car slides off right, the new one in from the left."""
    sc = scene_at(t); cur = CAR_SC[sc]
    out = []
    if sc > 0 and CAR_SC[sc - 1] != cur and t < SCENES[sc] + .6:
        k_out = prog(t, SCENES[sc] - .3, .45)
        out.append((CAR_SC[sc - 1], 1300 * k_out ** 2.2))
        k_in = prog(t, SCENES[sc] + .02, .58)
        if k_in > 0: out.append((cur, -1300 * (1 - oc(k_in))))
        return out
    nxt = sc + 1 < len(SCENES) and CAR_SC[sc + 1] != cur and t >= SCENES[sc + 1] - .3
    if nxt:
        return [(cur, 1300 * prog(t, SCENES[sc + 1] - .3, .45) ** 2.2)]
    if sc == 0: return [(cur, 0.0)]
    return [(cur, 0.0)]

def draw_cars(img, t):
    for key, off in car_slot(t):
        if abs(off) > 1250: continue
        car = car_img(key)
        speed = abs(off) / 1300
        if speed > .04:                                   # horizontal motion blur while sliding
            nw = max(8, int(car.width / (1 + 14 * speed)))
            car = car.resize((nw, car.height), Image.BILINEAR).resize((car.width, car.height), Image.BILINEAR)
        x0 = int((CX + off) * K - car.width / 2)
        gy = PLAT_Y + 14                                  # tyres sit on the front half of the platform top
        y0 = int(gy * K - car.height + 3 * K)             # 3 px: the outline ring below the tyres
        hw = car.width / K * .47
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sd = D(sh)
        sd.ell(CX + off, gy - 2, hw * 1.04, 20, (0, 0, 0, 90))            # soft ambient shadow
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10 * K)))
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sd = D(sh)
        sd.ell(CX + off, gy - 3, hw * .96, 7, (0, 0, 0, 210))             # tight contact shadow under the tyres
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3 * K)))
        img.alpha_composite(car, (x0, y0))
        pl = plaque(key)                                  # model label hangs above the car and travels with it
        py = PLAT_Y - 330                                 # same plaque height for every car
        img.alpha_composite(pl, (int((CX + off * 1.0) * K - pl.width / 2), int(py * K - pl.height / 2)))
        d = D(img)
        d.line([(CX + off - 60, CEIL + 10), (CX + off - 60, py - 58)], (30, 36, 52), 3)
        d.line([(CX + off + 60, CEIL + 10), (CX + off + 60, py - 58)], (30, 36, 52), 3)

# ================================================================ background oddities (one per scene, never mentioned)
def giraffe(d, t):                       # scene 1: a giraffe's head hanging down through a ceiling tile, chewing a brochure
    x, y0 = 900, CEIL + 4
    dip = 40 * oc(prog(t, .2, 1.4)) + 6 * math.sin(t * 1.3)
    Y, SP = (240, 190, 70), (176, 108, 40)
    d.rect(x - 70, y0 - 4, x + 70, y0 + 10, (20, 26, 40))
    neck = [(x - 22, y0), (x + 22, y0), (x + 18, y0 + 150 + dip), (x - 18, y0 + 150 + dip)]
    d.poly(neck, Y, OL, 3)
    for k_, (sx_, sy_) in enumerate(((-6, 40), (8, 90), (-8, 130))):
        d.ell(x + sx_, y0 + sy_ + dip * (sy_ / 150), 9, 12, SP)
    hy = y0 + 190 + dip
    d.ell(x, hy, 36, 50, Y, OL, 3)
    d.ell(x, hy + 40, 26, 22, (226, 170, 90), OL, 3)
    for s in (-1, 1):
        d.ell(x + s * 40, hy - 30, 16, 8, Y, OL, 3)                       # ears
        d.line([(x + s * 12, hy - 46), (x + s * 14, hy - 66)], SP, 6); d.ell(x + s * 14, hy - 68, 7, 7, SP)   # ossicones (upside-down)
        if (t % 3.3) > .12: d.ell(x + s * 14, hy + 4, 5, 5, OL)
        else: d.line([(x + s * 14 - 5, hy + 4), (x + s * 14 + 5, hy + 4)], OL, 3)
    chew = math.sin(t * 9) * 4
    d.rect(x - 34 + chew, hy + 52, x + 6 + chew, hy + 84, (255, 255, 255), r=3, ol=OL, w=2)   # brochure in its mouth
    d.rect(x - 28 + chew, hy + 58, x - 4 + chew, hy + 64, BLUE)

def snail(d, t):                         # scene 2: a snail on a skateboard rolling slowly along the floor
    k_ = prog(t, SCENES[1], SCENES[2] - SCENES[1])
    x, fy = 1010 - 150 * k_, WALL_Y + 70
    for i in range(6):
        d.ell(x + 40 + i * 22, fy - 1, 10, 3, (190, 230, 255, 160 - i * 25))   # slime trail
    d.rect(x - 52, fy - 16, x + 52, fy - 8, (226, 48, 58), r=4, ol=OL, w=2)
    for s in (-1, 1): d.ell(x + s * 34, fy - 2, 8, 8, (40, 40, 48))
    d.poly(spline([(x - 50, fy - 18), (x - 60, fy - 40), (x - 56, fy - 60), (x - 44, fy - 64), (x - 40, fy - 30), (x + 40, fy - 18)], 6), (150, 220, 120), OL, 3)
    d.ell(x + 6, fy - 52, 34, 34, (230, 150, 60), OL, 3)
    d.arc(x + 6, fy - 52, 20, 20, 0, 300, (176, 96, 30), 5); d.arc(x + 8, fy - 50, 9, 9, 0, 300, (176, 96, 30), 4)
    for s in (0, 1):
        d.line([(x - 52, fy - 58), (x - 62 - s * 10, fy - 88)], (150, 220, 120), 4); d.ell(x - 62 - s * 10, fy - 90, 5, 5, OL)
    d.rect(x - 70, fy - 74, x - 46, fy - 66, (20, 20, 24), r=3)        # tiny sunglasses

def ghost(d, t):                         # scene 3: a bedsheet ghost reading the newspaper on a bench
    x, fy = 112, WALL_Y + 84
    d.rect(x - 70, fy - 52, x + 70, fy - 40, (130, 86, 50), r=4, ol=OL, w=2)
    for s in (-1, 1): d.rect(x + s * 56 - 5, fy - 42, x + s * 56 + 5, fy, (90, 60, 36))
    bob = math.sin(t * 1.8) * 3
    body = spline([(x - 40, fy - 46), (x - 44, fy - 120 + bob), (x - 30, fy - 160 + bob), (x, fy - 170 + bob), (x + 30, fy - 160 + bob),
                   (x + 44, fy - 120 + bob), (x + 40, fy - 46), (x + 20, fy - 54), (x, fy - 44), (x - 20, fy - 54)], 6)
    d.poly(body, (250, 250, 252), OL, 3)
    for s in (-1, 1): d.ell(x - 4 + s * 12, fy - 136 + bob, 5, 7, OL)
    turn = (t % 4) < .25
    d.poly([(x + 6, fy - 120 + bob), (x + 70, fy - 132 + bob), (x + 70 + (6 if turn else 0), fy - 70 + bob), (x + 6, fy - 66 + bob)],
           (236, 232, 220), OL, 2)
    for i in range(5): d.line([(x + 16, fy - 114 + i * 10 + bob), (x + 60, fy - 120 + i * 10 + bob)], (150, 150, 150), 2)

def penguin(d, t):                       # scene 4: a penguin standing in an ice bucket, sweating
    x, fy = 930, WALL_Y + 96
    d.poly([(x - 56, fy - 70), (x + 56, fy - 70), (x + 44, fy), (x - 44, fy)], (200, 206, 216), OL, 3)
    d.rect(x - 60, fy - 76, x + 60, fy - 64, (230, 234, 240), r=4, ol=OL, w=2)
    sway = math.sin(t * 2.2) * 3
    d.ell(x + sway, fy - 120, 38, 56, (24, 26, 34), OL, 3)
    d.ell(x + sway, fy - 110, 26, 44, (250, 250, 252))
    d.ell(x + sway, fy - 182, 28, 26, (24, 26, 34), OL, 3)
    for s in (-1, 1): d.ell(x + sway + s * 10, fy - 186, 6, 7, (255, 255, 255)); d.ell(x + sway + s * 10, fy - 185, 3, 4, OL)
    d.poly([(x + sway - 9, fy - 174), (x + sway + 9, fy - 174), (x + sway, fy - 162)], (246, 160, 30), OL, 2)
    for s in (-1, 1): d.ell(x + sway + s * 34, fy - 120, 10, 30, (24, 26, 34))
    for i in range(3):                                     # ice cubes
        d.rect(x - 40 + i * 28, fy - 82 - (i % 2) * 8, x - 18 + i * 28, fy - 62 - (i % 2) * 8, (200, 236, 255), r=4, ol=(120, 170, 210), w=2)
    ph = (t * .9) % 1                                      # a sweat drop
    d.ell(x + sway + 26, fy - 196 + 40 * ph, 4, 6, (110, 190, 255, int(255 * (1 - ph))))

def duck(d, t):                          # scene 5: a giant rubber duck bobbing in a paddling pool
    x, fy = 110, WALL_Y + 100
    bob = math.sin(t * 2.6) * 5; tilt = math.sin(t * 1.3) * 4
    d.ell(x, fy - 26, 96, 30, (60, 170, 240), OL, 3)
    d.ell(x, fy - 34, 84, 20, (150, 220, 255))
    d.ell(x + 6, fy - 72 + bob, 64, 40, (255, 214, 40), OL, 3)
    d.poly([(x + 54, fy - 90 + bob), (x + 80, fy - 112 + bob), (x + 66, fy - 70 + bob)], (255, 214, 40), OL, 3)
    d.ell(x - 18 + tilt, fy - 126 + bob, 34, 32, (255, 214, 40), OL, 3)
    d.ell(x - 22 + tilt, fy - 134 + bob, 6, 7, OL)
    d.poly([(x - 46 + tilt, fy - 124 + bob), (x - 76 + tilt, fy - 116 + bob), (x - 46 + tilt, fy - 108 + bob)], (246, 120, 30), OL, 2)

def crab(d, t):                          # scene 6: a crab in a tie walking sideways with a briefcase
    k_ = prog(t, SCENES[5], SCENES[6] - SCENES[5])
    x, fy = 20 + 180 * k_, WALL_Y + 70
    R = (232, 70, 52)
    for s in (-1, 1):
        for i in range(3):
            ph = math.sin(t * 14 + i + (s > 0) * 1.5) * 6
            d.line([(x + s * 26, fy - 26 + i * 4), (x + s * (46 + i * 6), fy - 14 + ph), (x + s * (54 + i * 6), fy)], R, 4)
    d.ell(x, fy - 30, 42, 24, R, OL, 3)
    d.poly([(x - 4, fy - 30), (x + 4, fy - 30), (x + 6, fy - 12), (x, fy - 6), (x - 6, fy - 12)], NAVY)   # tie
    for s in (-1, 1):
        d.line([(x + s * 14, fy - 50), (x + s * 16, fy - 70)], R, 4); d.ell(x + s * 16, fy - 74, 7, 7, (255, 255, 255), OL, 2)
        d.ell(x + s * 17, fy - 74, 3, 3, OL)
    d.line([(x + 36, fy - 38), (x + 62, fy - 50)], R, 6); d.ell(x + 66, fy - 52, 12, 9, R, OL, 2)
    d.rect(x + 54, fy - 44, x + 96, fy - 14, (110, 66, 36), r=4, ol=OL, w=2)      # briefcase
    d.line([(x + 66, fy - 44), (x + 66, fy - 52), (x + 84, fy - 52), (x + 84, fy - 44)], OL, 3)

def cactus(d, t):                        # scene 7: a cactus in sunglasses jogging on a tiny treadmill
    x, fy = 920, WALL_Y + 96
    d.poly([(x - 70, fy - 20), (x + 70, fy - 20), (x + 76, fy), (x - 76, fy)], (60, 64, 76), OL, 3)
    for i in range(8):
        bx_ = x - 66 + ((i * 18 - t * 90) % 136)
        d.line([(bx_, fy - 18), (bx_, fy - 4)], (110, 116, 130), 3)
    d.line([(x + 60, fy - 20), (x + 70, fy - 130)], (60, 64, 76), 6); d.rect(x + 46, fy - 140, x + 84, fy - 124, (60, 64, 76), r=4)
    hop = abs(math.sin(t * 7)) * 8
    d.poly([(x - 34, fy - 60 - hop), (x + 34, fy - 60 - hop), (x + 26, fy - 22 - hop), (x - 26, fy - 22 - hop)], (204, 102, 60), OL, 3)
    G2 = (70, 170, 80)
    d.rect(x - 22, fy - 170 - hop, x + 22, fy - 58 - hop, G2, r=22, ol=OL, w=3)
    d.rect(x - 52, fy - 136 - hop, x - 34, fy - 96 - hop, G2, r=9, ol=OL, w=3); d.rect(x - 40, fy - 106 - hop, x - 20, fy - 92 - hop, G2)
    d.rect(x + 34, fy - 150 - hop, x + 52, fy - 112 - hop, G2, r=9, ol=OL, w=3); d.rect(x + 20, fy - 124 - hop, x + 40, fy - 110 - hop, G2)
    d.rect(x - 20, fy - 150 - hop, x + 20, fy - 138 - hop, (20, 20, 24), r=4)
    d.line([(x - 6, fy - 120 - hop), (x + 6, fy - 120 - hop)], OL, 3)
    d.rect(x - 24, fy - 166 - hop, x + 24, fy - 158 - hop, (228, 30, 38), r=3)   # sweatband

ODD = [giraffe, snail, ghost, penguin, duck, crab, cactus]

# ---- performance schedules: (time, left pose, right pose, extras)
def buyer_sched():
    A, Wd = dict(brows='angry', eyes='wide'), dict(brows='angry', eyes='wide', sweat=1)
    SM = dict(brows='up', smile=1)
    return [(0.0, 'hip', 'present', SM),                                  # frame 1: already pitching his car
            (T_E46A - .1, 'hip', 'raise1', dict(brows='up', smile=1)),
            (T_NO, 'rest', 'rest', dict(brows='flat')),
            (T_NEW1, 'head', 'head', dict(brows='up', eyes='wide')),
            (LS[2] - .05, 'point', 'point', A),
            (T_NOSTR - .05, 'up', 'up', Wd),
            (LS[3] + .2, 'rest', 'rest', dict(brows='angry')),
            (T_20, 'cross', 'cross', dict(brows='up', smile=1)),
            (LS[4] - .05, 'present', 'hip', dict(brows='up', smile=1)),
            (T_414 - .05, 'up', 'up', dict(brows='up', eyes='wide')),
            (LE[4] + .15, 'rest', 'rest', dict(brows='flat')),
            (T_503, 'head', 'rest', dict(brows='worried', eyes='wide')),
            (LS[6] - .05, 'point', 'hip', A),
            (LE[6] + .2, 'cross', 'cross', dict(brows='up', smile=1)),
            (T_3840, 'cross', 'cross', dict(brows='flat', smile=1)),
            (T_PRET, 'hip', 'hip', dict(brows='up')),
            (LS[8] - .05, 'shrug', 'shrug', Wd),
            (LE[8] + .15, 'rest', 'rest', dict(brows='angry')),
            (T_38, 'chin', 'rest', dict(brows='worried', eyes='wide')),
            (T_34, 'head', 'head', dict(brows='worried', eyes='wide', sweat=1)),
            (LS[10] - .05, 'thanks', 'thanks', dict(brows='worried', eyes='wide')),
            (LE[10] + .15, 'rest', 'rest', dict(brows='worried')),
            (T_DROVE, 'cross', 'cross', dict(brows='flat', smile=-1)),
            (LS[12] - .05, 'point', 'rest', dict(brows='angry', tired=.3, smile=-1)),
            (LE[12] + .1, 'rest', 'rest', dict(brows='flat', tired=.3)),
            (T_AGREE - .1, 'shrug', 'shrug', dict(brows='up', eyes='wide')),
            (T_FINAL + .05, 'rest', 'rest', dict(brows='up', eyes='wide', look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {1: 'open', 3: 'present', 5: 'offer', 7: 'open', 9: 'present', 11: 'open', 13: 'open'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
    s += [(T_HEAVY, 'raise1', 'clasp', {}), (T_FINAL, 'open', 'clasp', dict(look=0)), (LE[14] + .3, 'clasp', 'clasp', dict(look=0))]
    return sorted(s, key=lambda e: e[0])


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


# ---- performance schedules: (time, left pose, right pose, extras). Buyer escalates per showroom, then deflates.

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


# ================================================================ world
def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    img = bg_showroom().copy()
    d = D(img)
    ODD[sc](d, t)
    draw_cars(img, t)
    d = D(img)
    f = int(round(t * FPS))
    bx = 270 - 40 * (1 - oc(prog(t, 0, 1.0)))             # frame 1: buyer still stepping in
    for who, x, sched, cfg, spk in (('S', 670, SS_, SALES, 'S'), ('B', bx, BS, BUYER, 'B')):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[spk][min(f, len(MOUTH[spk]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        breathe = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3
        st['dy'] = breathe + (-4 if talking(spk, t) and (f // 4) % 2 else 0)
        if who == 'B' and t < 1.0:
            st['walk'] = t * 11
            st['dy'] -= abs(math.sin(t * 11)) * 8
        if st.get('sweat'):
            st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
    return img

# per-scene framing: (zoom, x shift); alternating wide / closer so each cut reads
FRAMING = [(1.06, 0), (1.12, 30), (1.04, -10), (1.13, -30), (1.06, 20), (1.15, -40), (1.05, 0)]
PUNCH = {0: ((T_BEST, .03), (T_NO, .03)), 1: ((T_NOSTR, .06), (T_20, .03)), 2: ((T_414, .04), (T_503, .05)),
         3: ((T_LIGHT, .04), (T_HEAVY, .05)), 4: ((T_WHY, .06), (T_38, .04), (T_34, .05)), 5: ((T_FEEL, .05), (T_PRAISE, .03)),
         6: ((T_PUNCH, .06), (T_AGREE, .03))}
def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    z0, sx = FRAMING[sc]
    z = z0 + 0.02 * io(prog(t, t0, 6))                     # slow push in every scene
    if sc == 0: z = z0 + 0.06 * (1 - oc(prog(t, 0, 1.6)))  # frame 1 already moving: easing out of a closer start
    sy = 0.0
    if sc == 6:
        pk = io(prog(t, T_FINAL - .05, .5))                # salesman turns to camera: push in on him
        z += 0.14 * pk; sx += 150 * pk
    for tp, amt in PUNCH[sc]:
        if tp <= t < tp + .5:
            z += amt * (1 - oc(prog(t, tp, .5)))
    if sc == 6 and T_PUNCH - .02 <= t < T_PUNCH + .45:     # tiny jolt on "punched"
        k_ = 1 - prog(t, T_PUNCH - .02, .47)
        sx += 10 * k_ * math.sin(t * 61); sy += 8 * k_ * math.sin(t * 47 + 1)
    return z, sx, sy

def shoot(t):
    wimg = world(t)
    z, sx, sy = camera(t)
    ax, ay = CX * K, 760 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    return wimg.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')

# ================================================================ overlays (none in the first 3 s)
GREEN, TAG, RED = (70, 200, 120), (255, 214, 64), (226, 48, 58)
def put(img, layer, cx, cy, s=1.0, a=1.0, rot=0.0):
    if rot: layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    if s <= 0.02 or a <= 0: return
    if s != 1: layer = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.LANCZOS)
    if a < 1: layer.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
    img.alpha_composite(layer, (int(cx * K - layer.width / 2), int(cy * K - layer.height / 2)))


# stat panels: (scene, title, rows[(label, value, colour, time-name, bar fraction or None)])
PANELS = {
    1: ('THE GRILLE', [('Liked the new kidney grille', '≈20%', RED, 'T_20', .20)]),
    2: ('HORSEPOWER', [('E92 M3 · V8', '414 hp', M_DB, 'T_414', 414 / 523), ('New M3 Competition', '503 hp', M_LB, 'T_503', 503 / 523),
                       ('Comp xDrive (2025 on)', '≈523 hp', M_LB, 'T_OVER', 1.0)]),
    3: ('WEIGHT', [('E46 M3', '≈3,400 lb', GREEN, 'T_3400', 3400 / 3890), ('New M3', '≈3,840 lb', RED, 'T_3840', 3840 / 3890)]),
    4: ('0-60 MPH', [('E46 M3', '≈5.1 s', M_DB, 'T_51', 5.1 / 5.1), ('New M3 Competition', '≈3.8 s', M_LB, 'T_38', 3.8 / 5.1),
                     ('Competition xDrive', '≈3.4 s', M_LB, 'T_34', 3.4 / 5.1)]),
}
CHIPS = {3: ('HEAVIEST M3 EVER', RED, 'T_HEAVY'), 5: ('REVIEWS: CRITICISM → PRAISE', GREEN, 'T_PRAISE')}
PAN_X0, PAN_X1, PAN_Y0 = 90, 830, 96
def stat_panel(d, t, sc, a):
    title, rows = PANELS[sc]
    h = 62 + 84 * len(rows)
    d.rect(PAN_X0, PAN_Y0, PAN_X1, PAN_Y0 + h, (255, 255, 255, int(244 * a)), r=26, ol=NAVY + (int(255 * a),), w=5)
    d.text(PAN_X0 + 30, PAN_Y0 + 40, title, 34, NAVY + (int(255 * a),), anchor='lm')
    for i, c in enumerate((M_LB, M_DB, M_RED)):
        d.rect(PAN_X1 - 120 + i * 30, PAN_Y0 + 34, PAN_X1 - 96 + i * 30, PAN_Y0 + 44, c + (int(255 * a),))
    for i, (lab, val, col, tn, frac) in enumerate(rows):
        tl = globals()[tn]
        if t < tl - .08: continue
        k_ = oc(prog(t, tl - .08, .45)); ra = min(a, prog(t, tl - .08, .15))
        y = PAN_Y0 + 84 + i * 84
        d.text(PAN_X0 + 30, y, lab, 30, (60, 66, 84, int(255 * ra)), anchor='lm', path=FONT_X)
        bw = (PAN_X1 - PAN_X0 - 60) * frac * k_
        d.rect(PAN_X0 + 30, y + 20, PAN_X0 + 30 + max(bw, 24), y + 52, col + (int(255 * ra),), r=12)
        vs = 1 + .18 * (1 - oc(prog(t, tl - .08, .3)))
        d.text(PAN_X1 - 30, y + 4, val, 40 * vs, (16, 18, 28, int(255 * ra)), anchor='rm')

def chip(d, t, sc, a):
    txt, col, tn = CHIPS[sc]
    tl = globals()[tn]
    if t < tl - .05: return
    k_ = popin(t, tl - .05, .3); ra = min(a, prog(t, tl - .05, .12))
    w_ = font(40).getlength(txt) + 60
    y = PAN_Y0 + (62 + 84 * len(PANELS[sc][1]) + 50 if sc in PANELS else 60)
    d.rect(CX - w_ / 2 * k_, y - 34 * k_, CX + w_ / 2 * k_, y + 34 * k_, col + (int(255 * ra),), r=18, ol=(10, 12, 20, int(255 * ra)), w=4)
    if k_ > .6: d.text(CX, y + 1, txt, 40, (255, 255, 255, int(255 * ra)))

def overlays(t):
    if t < 3.0: return None
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    d = D(img)
    used = False
    sc = scene_at(t)
    end = SCENES[sc + 1] - .05 if sc + 1 < len(SCENES) else T_CARD
    if sc in PANELS:
        t0 = globals()[PANELS[sc][1][0][3]] - .3
        a = window(t, t0, end, .2, .25)
        if a > 0: used = True; stat_panel(d, t, sc, a)
    if sc in CHIPS:
        a = window(t, globals()[CHIPS[sc][2]] - .05, end, .1, .25)
        if a > 0: used = True; chip(d, t, sc, a)
    if t >= T_CARD:                                          # final caption
        used = True
        fa = prog(t, T_CARD, .25)
        d.rect(50, FINAL_Y0 - 90, 868, FINAL_Y0 + FINAL_DY * (len(FINAL) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(FINAL):
            k_ = popin(t, T_CARD + .08 * i, .3)
            if k_ > .05:
                d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if used else None

FINAL = [("Old M3 or new M3?", 76, TAG), ("Comment below.", 70, (255, 255, 255))]
FINAL_Y0, FINAL_DY = 520, 110
ONSCREEN = (['BMW'] + [x for v in CAR_LABEL.values() for x in v] + [p[0] for p in PANELS.values()]
            + [x for p in PANELS.values() for r in p[1] for x in r[:2]] + [c[0] for c in CHIPS.values()] + [f[0] for f in FINAL])

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
def frame(n):
    t = n / FPS
    img = shoot(t)
    for s_ in SCENES[1:]:                                   # hard cut to the new framing, with a quick flash
        if s_ <= t < s_ + .18:
            img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.3 * (1 - prog(t, s_, .18)))
    ov = overlays(t)
    if ov is not None:
        ov = ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA')
        img.alpha_composite(ov)
    if BEAT[0] + .1 <= t < T_FINAL:                         # the beat: room dims, everyone waits
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.2 * io(prog(t, BEAT[0] + .1, .4)))
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
    hum = 0.005 * np.sin(2 * np.pi * 60 * T_) + 0.003 * np.sin(2 * np.pi * 120 * T_)
    bed = room + hum * .5                                     # quiet; room left for the user's own music
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
    def rev(d=0.9, f0=70, f1=190):
        """Engine blip for the sliding car: rising saw-ish growl, low-passed."""
        tt = np.arange(int(SR * d)) / SR
        f = f0 + (f1 - f0) * np.sin(np.pi * np.clip(tt / d * 1.2, 0, 1)) ** 2
        ph = np.cumsum(f) / SR
        x = np.sin(2 * np.pi * ph) + .5 * np.sin(4 * np.pi * ph) + .3 * np.sign(np.sin(6 * np.pi * ph))
        return lpf(x, 12) * np.sin(np.pi * tt / d) ** .7 * .5
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    for k_ in range(3): add(0.02 + k_ * 0.3, step(), .45)               # buyer stepping in on frame 1
    for i, s_ in enumerate(SCENES[1:], 1):                  # car change: whoosh + engine blip + platform thump
        add(s_ - .3, sfx.whoosh(.5, 18), .45); add(s_ + .12, sfx.thump(), .3)
        if CAR_SC[i] != CAR_SC[i - 1]: add(s_ - .1, rev(), .5)
    for tn in ('T_20', 'T_414', 'T_503', 'T_OVER', 'T_3400', 'T_3840', 'T_51', 'T_38', 'T_34'):
        add(globals()[tn] - .08, sfx.pop(), .22)            # stat rows popping in
    add(T_NOSTR, sfx.buzzer(.2), .2)
    add(T_HEAVY - .05, sfx.stamp(), .3)
    add(T_34 + .2, sfx.ding(1568, .6), .14)
    add(T_PRAISE - .05, sfx.ding(1760), .14)
    add(T_PUNCH, sfx.thump(.2), .35)
    for k_ in range(2): add(BEAT[0] + .15 + k_ * .3, tick(), .6)
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
