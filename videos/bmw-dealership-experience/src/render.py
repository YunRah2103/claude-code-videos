"""BMW dealership experience: a whole-brand showroom walk. M5 -> 3 Series -> Z4 M40i slide across one display platform
(real photos, background removed), then the front desk. Flat-vector cast, 1080x1920 @30. Built on bmw-heated-seats/src/
render.py: same buyer, caption system, camera and mix chain; new BMW salesman. One background oddity per scene (never
mentioned). Usage: python render.py video VOICE.wav OUT.mp4 | python render.py still T OUT.png [VOICE] | python render.py meta OUT.json"""
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
DUR = round(WORDS[-1]['e'] + 2.4, 2)
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_X = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
VOICE_CACHE = os.path.expanduser('~/.cache/bmw-dealership-experience/voice.wav')

# ---- timeline from word timings
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt, nth=0):
    hits = [w['s'] for w in LINES[line] if txt.lower() in w['w'].lower()]
    return hits[nth]
# scenes: 0 M5 intro, 1 sound design, 2 3 Series + seats, 3 subscription, 4 rented warmth + Z4, 5 Supra, 6 front desk
SCENES = [0.0] + [LS[li] - 0.35 for li in (2, 6, 8, 10, 12, 14)]
T_S = SCENES
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
T_M5, T_LISTEN = word_t(1, 'M5'), word_t(1, 'Listen')
T_SPK, T_SPK2, T_ASD = word_t(3, 'speakers'), word_t(4, 'speakers'), word_t(5, 'Active')
T_REAL, T_ASSIST = word_t(5, 'real'), word_t(5, 'assisted')
T_HEAT, T_SUB, T_18 = word_t(6, 'heated'), word_t(7, 'subscription'), word_t(7, 'eighteen')
T_MONTH = word_t(8, 'month')
T_180, T_415, T_OFF = word_t(9, 'hundred'), word_t(9, 'four-fifteen'), word_t(9, 'off')
T_ALREADY = word_t(10, 'already')
T_HW, T_WARM, T_NOW = word_t(11, 'hardware'), word_t(11, 'warmth'), word_t(11, 'Now')
T_Z4, T_30, T_8SP, T_AUT = word_t(11, 'Z4'), word_t(11, 'Three'), word_t(11, 'eight'), word_t(11, 'Austria')
T_SUPRA = word_t(12, 'Supra')
T_SENG, T_SGB, T_SFAC, T_BADGE = word_t(13, 'engine'), word_t(13, 'gearbox'), word_t(13, 'factory'), word_t(13, 'badge')
T_TAKE, T_ADD, T_MUCH, T_E18 = word_t(14, 'take'), word_t(15, 'heated'), word_t(16, 'much'), LS[17]
BEAT = (LE[17], LS[18])
T_FINAL = LS[18]                           # salesman turns to the viewer
T_CARD = LE[18] + 0.35                     # final caption card (last ~2 s)
SWAPS = [(T_S[2] + 0.12, 'm5', 's3'), (T_NOW - 0.05, 's3', 'z4')]
SLIDE = 0.75


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

def crest(d, cx, cy, s=1.0):
    """Generic quartered crest (red/gold) for the Stuttgart brand."""
    d.poly([(cx - 50 * s, cy - 60 * s), (cx + 50 * s, cy - 60 * s), (cx + 48 * s, cy + 10 * s), (cx, cy + 66 * s),
            (cx - 48 * s, cy + 10 * s)], (30, 24, 16), GOLD, max(2, 7 * s))
    for (x0, y0, c) in ((-38, -46, P_RED), (4, -46, GOLD), (-38, 2, GOLD), (4, 2, P_RED)):
        d.rect(cx + x0 * s, cy + y0 * s, cx + (x0 + 34) * s, cy + (y0 + 38) * s, c, r=2 * s)

def wings(d, cx, cy, s=1.0, col=CHROME):
    """Generic winged badge for the British brand."""
    for side in (-1, 1):
        for i in range(4):
            y = cy - 18 * s + i * 12 * s
            d.line([(cx + side * 30 * s, y), (cx + side * (130 - i * 24) * s, y - 12 * s + i * 3 * s)], col, max(2, 7 * s))
    d.ell(cx, cy, 30 * s, 30 * s, (20, 34, 28), col, max(2, 6 * s))

def roundel(d, cx, cy, s=1.0):
    """Plain blue roundel for the Wolfsburg brand."""
    d.ell(cx, cy, 60 * s, 60 * s, VWBLUE, (240, 244, 250), max(2, 8 * s))
    d.ell(cx, cy, 38 * s, 38 * s, None, (240, 244, 250), max(2, 5 * s))

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

# ================================================================ platform cars (real photos, background removed)
CEIL = 84
CARS = {'m5': ('m5.png', 640, 'M5'), 's3': ('s3.png', 540, '3 SERIES'), 'z4': ('z4.png', 650, 'Z4 M40i')}
GROUND = 916

@lru_cache(None)
def car_photo(key, width):
    im = Image.open(os.path.join(HERE, '..', 'assets', CARS[key][0])).convert('RGBA')
    return im.resize((int(width * K), int(width * K * im.height / im.width)), Image.LANCZOS)

@lru_cache(None)
def model_label(txt, size=34):
    w_ = int(font(size).getlength(txt)) + 44
    lab = Image.new('RGBA', (w_ * K, 58 * K), (0, 0, 0, 0)); ld = D(lab)
    ld.rect(0, 0, w_, 56, (20, 22, 28), r=12, ol=(28, 105, 190), w=3)
    ld.text(w_ / 2, 29, txt, size, (255, 255, 255), path=FONT_X)
    return lab

@lru_cache(None)
def car_shadow(w):
    sh = Image.new('RGBA', (int((w + 120) * K), 120 * K), (0, 0, 0, 0))
    D(sh).ell(w / 2 + 60, 60, w * .5, 20, (0, 0, 0, 150))
    return sh.filter(ImageFilter.GaussianBlur(10 * K))

SWEEPS = []                                                  # (start) light sweeps across the car body; filled below
def put_car(img, key, cx, label_a=1.0, blur=0.0, s=1.0, t=None, dy=0.0):
    w = int(CARS[key][1] * s)
    ph = car_photo(key, w)
    if t is not None and blur <= .05:
        for ts in SWEEPS:
            if ts <= t < ts + .9: ph = light_sweep(ph, prog(t, ts, .9))
    if blur > .05:                                           # motion smear while sliding
        r = int(blur * 18 * K)
        ph = ph.resize((max(1, ph.width // (1 + r // 8)), ph.height), Image.BILINEAR).resize(ph.size, Image.BILINEAR)
    sh = car_shadow(w)
    img.alpha_composite(sh, (int((cx - w / 2 - 60) * K), int((GROUND - 66) * K)))
    if blur <= .05:                                          # mirror image on the glossy turntable / floor
        rf = car_reflection(key, w)
        img.alpha_composite(rf, (int(cx * K - rf.width / 2), int((GROUND - 4) * K)))
    x0, y0 = int(cx * K - ph.width / 2), int((GROUND + dy) * K - ph.height)
    img.alpha_composite(ph, (x0, y0))
    if label_a > 0.02:
        lab = model_label(CARS[key][2])
        if label_a < 1: lab = lab.copy(); lab.putalpha(lab.getchannel('A').point(lambda v: int(v * label_a)))
        img.alpha_composite(lab, (int(cx * K - lab.width / 2), int(GROUND * K - ph.height) - lab.height - 22 * K))

def car_state(t):
    """[(key, x offset, blur)] on the platform at time t: the old car slides out left, the new one in from the right."""
    cur = 'm5'
    for ts, a, b in SWAPS:
        if t < ts: return [(cur, 0, 0)]
        k = prog(t, ts, SLIDE)
        if k < 1:
            e = io(k); v = math.sin(math.pi * k)
            return [(a, -1100 * e, v), (b, 1100 * (1 - e), v)]
        cur = b
    return [(cur, 0, 0)]

def platform(img, t):
    led_ring(img, t)
    rev = math.sin(math.pi * prog(t, T_REV, 2.6)) if T_REV <= t < T_REV + 2.6 else 0.0
    for key, dx, bl in car_state(t):
        la = 1.0 if key != 'm5' else popin(t, T_M5 - .1, .3) if t < T_M5 + .3 else 1.0   # first label after the 3 s hook
        put_car(img, key, CX + dx, min(1.0, max(0.0, la)), bl, t=t, dy=(rev * 2.5 * math.sin(t * 90) if key == 'm5' else 0.0))

# ================================================================ background oddities (comment bait, never mentioned)
# 1 a penguin in a bow tie mopping the showroom floor   2 a potted cactus in headphones, bopping to the "engine"
# 3 a pineapple in sunglasses sunbathing under a heat lamp   4 a hamster in a wheel powering a floor lamp
# 5 a giraffe's head poking down through a ceiling tile, chewing   6 an octopus polishing the platform with four cloths
# 7 a goat in a headset working the front desk computer
def penguin(d, x, fy, t, s=.9):
    x = x - 18 * math.sin(t * 1.1); wob = math.sin(t * 7) * 4
    d.ell(x + 60 * s, fy - 4, 62 * s, 9 * s, (190, 220, 240, 150))                       # wet patch
    d.ell(x - 14 * s, fy - 6, 14 * s, 6 * s, (244, 150, 40)); d.ell(x + 14 * s, fy - 6, 14 * s, 6 * s, (244, 150, 40))
    d.ell(x, fy - 62 * s, 38 * s, 58 * s, (26, 28, 34), OL, 3)
    d.ell(x + 4 * s, fy - 56 * s, 25 * s, 44 * s, (248, 248, 250))
    d.ell(x + 2 * s, fy - 128 * s + wob * .3, 28 * s, 26 * s, (26, 28, 34), OL, 3)
    d.ell(x + 12 * s, fy - 132 * s + wob * .3, 6 * s, 6 * s, (255, 255, 255)); d.ell(x + 14 * s, fy - 132 * s + wob * .3, 3 * s, 3 * s, OL)
    d.poly([(x + 24 * s, fy - 126 * s), (x + 44 * s, fy - 120 * s), (x + 24 * s, fy - 114 * s)], (244, 150, 40))
    d.poly([(x - 10 * s, fy - 104 * s), (x + 14 * s, fy - 96 * s), (x - 10 * s, fy - 88 * s)], (200, 30, 40))     # bow tie
    d.poly([(x + 34 * s, fy - 104 * s), (x + 14 * s, fy - 88 * s), (x - 10 * s, fy - 104 * s)], (200, 30, 40))
    mx = x + 70 * s + wob * 3
    d.line([(x + 20 * s, fy - 80 * s), (mx, fy - 14)], (150, 112, 74), 6 * s)            # mop
    for i in range(-4, 5):
        d.line([(mx, fy - 16), (mx + i * 5 * s + wob, fy - 2)], (220, 220, 210), 4 * s)
    d.ell(x + 28 * s, fy - 78 * s, 9 * s, 16 * s, (26, 28, 34))                            # flipper on the handle

def cactus(d, x, fy, t, s=.9):
    sw = math.sin(t * 9.5) * 7 * s
    d.poly([(x - 34 * s, fy - 60 * s), (x + 34 * s, fy - 60 * s), (x + 26 * s, fy), (x - 26 * s, fy)], (196, 98, 60), OL, 3)
    d.rect(x - 40 * s, fy - 72 * s, x + 40 * s, fy - 56 * s, (214, 116, 74), r=4, ol=OL, w=3)
    cx_, top = x + sw, fy - 210 * s
    d.rect(cx_ - 22 * s, top, cx_ + 22 * s, fy - 70 * s, (70, 150, 80), r=22 * s, ol=OL, w=3)
    d.rect(cx_ - 58 * s, fy - 170 * s, cx_ - 38 * s, fy - 120 * s, (70, 150, 80), r=10 * s, ol=OL, w=3)
    d.rect(cx_ - 58 * s, fy - 130 * s, cx_ - 18 * s, fy - 112 * s, (70, 150, 80), r=9 * s)
    d.rect(cx_ + 38 * s, fy - 190 * s, cx_ + 58 * s, fy - 140 * s, (70, 150, 80), r=10 * s, ol=OL, w=3)
    d.rect(cx_ + 18 * s, fy - 150 * s, cx_ + 58 * s, fy - 132 * s, (70, 150, 80), r=9 * s)
    d.arc(cx_, top + 26 * s, 34 * s, 34 * s, 180, 360, (24, 24, 28), 7 * s)                # headphones
    for sd in (-1, 1):
        d.rect(cx_ + sd * 34 * s - 10 * s, top + 16 * s, cx_ + sd * 34 * s + 10 * s, top + 50 * s, (24, 24, 28), r=6 * s)
    d.line([(cx_ - 12 * s, top + 70 * s), (cx_ - 4 * s, top + 70 * s)], OL, 4 * s); d.line([(cx_ + 4 * s, top + 70 * s), (cx_ + 12 * s, top + 70 * s)], OL, 4 * s)
    for i in range(2):                                       # music notes drifting up
        ph = (t * .7 + i * .5) % 1
        nx, ny = x + 60 * s + i * 24 * s, fy - 220 * s - ph * 110 * s
        a = int(255 * math.sin(math.pi * ph))
        d.ell(nx, ny, 9 * s, 7 * s, (30, 30, 40, a)); d.line([(nx + 8 * s, ny), (nx + 8 * s, ny - 30 * s)], (30, 30, 40, a), 3 * s)

def pineapple(d, x, fy, t, s=.9):
    glow = .75 + .25 * math.sin(t * 3)
    d.line([(x + 70 * s, fy), (x + 70 * s, fy - 250 * s)], (90, 90, 96), 6 * s)            # heat lamp
    d.line([(x + 70 * s, fy - 250 * s), (x + 30 * s, fy - 262 * s)], (90, 90, 96), 6 * s)
    d.chord(x + 22 * s, fy - 250 * s, 34 * s, 26 * s, 0, 180, (60, 60, 66))
    d.ell(x + 22 * s, fy - 236 * s, 22 * s, 8 * s, mix((255, 120, 40), (255, 220, 120), glow))
    d.poly([(x + 22 * s - 20 * s, fy - 230 * s), (x + 22 * s + 20 * s, fy - 230 * s), (x + 80 * s, fy - 60 * s), (x - 40 * s, fy - 60 * s)],
           (255, 150, 60, int(46 * glow)))
    for sd in (-1, 1):                                       # deckchair
        d.line([(x + sd * 50 * s, fy), (x - sd * 40 * s, fy - 70 * s)], (150, 112, 74), 6 * s)
    for i, c in enumerate(((40, 120, 200), (250, 250, 250), (40, 120, 200), (250, 250, 250))):
        d.poly([(x - 64 * s + i * 22 * s, fy - 56 * s - i * 26 * s), (x - 42 * s + i * 22 * s, fy - 56 * s - i * 26 * s - 26 * s),
                (x - 20 * s + i * 22 * s, fy - 40 * s - i * 26 * s - 26 * s), (x - 42 * s + i * 22 * s, fy - 40 * s - i * 26 * s)], c)
    px, py = x - 6 * s, fy - 116 * s
    d.ell(px, py, 30 * s, 42 * s, (226, 170, 50), OL, 3)
    for k_ in range(-2, 3):
        d.line([(px - 26 * s, py + k_ * 14 * s - 10 * s), (px + 26 * s, py + k_ * 14 * s + 10 * s)], (170, 116, 30), 2 * s)
    for a in (-30, 0, 30):
        r_ = math.radians(a - 90 - 25)
        d.poly([(px - 8 * s, py - 38 * s), (px + 8 * s, py - 38 * s), (px + math.cos(r_) * 50 * s, py - 38 * s + math.sin(r_) * 50 * s)], (70, 150, 70))
    d.rect(px - 22 * s, py - 16 * s, px + 22 * s, py - 4 * s, (20, 20, 24), r=5 * s)       # sunglasses
    d.arc(px, py + 8 * s, 10 * s, 7 * s, 20, 160, OL, 3 * s)

def hamster(d, x, fy, t, s=.9):
    r_, cy = 62 * s, fy - 70 * s
    d.line([(x - 40 * s, fy), (x, cy)], (120, 124, 130), 6 * s); d.line([(x + 40 * s, fy), (x, cy)], (120, 124, 130), 6 * s)
    d.ell(x, cy, r_, r_, None, (150, 156, 166), 6 * s)
    for i in range(8):
        a = t * 9 + i * math.pi / 4
        d.line([(x, cy), (x + math.cos(a) * r_, cy + math.sin(a) * r_)], (170, 176, 186), 2 * s)
    hb = abs(math.sin(t * 18)) * 6 * s
    d.ell(x, cy + 36 * s - hb, 26 * s, 20 * s, (214, 160, 100), OL, 3)
    d.ell(x + 20 * s, cy + 28 * s - hb, 13 * s, 12 * s, (214, 160, 100), OL, 3)
    d.ell(x + 26 * s, cy + 26 * s - hb, 3 * s, 3 * s, OL); d.ell(x + 14 * s, cy + 18 * s - hb, 6 * s, 6 * s, (240, 180, 170))
    d.line([(x + r_, fy - 4), (x + 110 * s, fy - 4)], (30, 30, 34), 3 * s)                  # cable to the lamp
    lx = x + 120 * s; glow = .55 + .45 * abs(math.sin(t * 9))
    d.line([(lx, fy), (lx, fy - 190 * s)], (60, 60, 66), 6 * s); d.ell(lx, fy - 2, 26 * s, 6 * s, (60, 60, 66))
    d.ell(lx, fy - 204 * s, 60 * s, 60 * s, (255, 236, 160, int(60 * glow)))
    d.poly([(lx - 30 * s, fy - 190 * s), (lx + 30 * s, fy - 190 * s), (lx + 18 * s, fy - 236 * s), (lx - 18 * s, fy - 236 * s)],
           mix((180, 170, 140), (255, 240, 180), glow), OL, 3)

def giraffe(d, x, t):
    chew = math.sin(t * 8) * 4; sway = math.sin(t * 1.3) * 10
    d.rect(x - 70, CEIL - 6, x + 70, CEIL + 4, (40, 42, 46))                                 # the hole
    d.poly([(x + 70, CEIL), (x + 150, CEIL + 60), (x + 140, CEIL + 72), (x + 62, CEIL + 12)], (226, 228, 232), OL, 3)  # hanging tile
    hx, hy = x + sway, CEIL + 300
    d.poly([(x - 34, CEIL), (x + 34, CEIL), (hx + 30, hy - 40), (hx - 30, hy - 40)], (240, 196, 96), OL, 4)
    for py_ in (CEIL + 60, CEIL + 150, CEIL + 230):
        k_ = (py_ - CEIL) / 300
        d.ell(x + sway * k_ - 8, py_, 14, 18, (168, 108, 50)); d.ell(x + sway * k_ + 14, py_ + 40, 10, 12, (168, 108, 50))
    for sd in (-1, 1):
        d.line([(hx + sd * 16, hy - 50), (hx + sd * 22, hy - 92)], (168, 108, 50), 6); d.ell(hx + sd * 22, hy - 94, 7, 7, (120, 70, 30))
        d.ell(hx + sd * 46, hy - 50, 20, 9, (240, 196, 96), OL, 3)
    d.ell(hx, hy - 30, 40, 44, (240, 196, 96), OL, 4)
    d.ell(hx, hy + 24 + chew * .3, 30, 26, (222, 176, 110), OL, 3)
    for sd in (-1, 1):
        d.ell(hx + sd * 18, hy - 40, 8, 9, (255, 255, 255), OL, 2); d.ell(hx + sd * 18, hy - 38, 4, 5, OL)
    d.line([(hx + 10, hy + 36 + chew), (hx + 34, hy + 50 + chew)], (70, 150, 70), 4)          # leaf stalk
    d.ell(hx + 40, hy + 54 + chew, 12, 7, (70, 150, 70))

def octopus(d, x, fy, t, s=.85):
    for i in range(8):
        a0 = math.pi * (0.15 + 0.7 * i / 7)
        L = 90 * s; ph = t * 5 + i
        pts = [(x + math.cos(a0) * 30 * s * (1 if i < 4 else -1) * 0 + (i - 3.5) * 12 * s, fy - 40 * s)]
        for j in range(1, 5):
            u = j / 4
            pts.append((pts[0][0] + (i - 3.5) * 22 * s * u + math.sin(ph + u * 3) * 14 * s * u, fy - 40 * s + u * 36 * s - (abs(i - 3.5) > 2.5) * u * 70 * s))
        d.line(pts, (170, 80, 170), 12 * s)
        if i in (0, 1, 6, 7):                                # cloths on four arms, polishing
            ex, ey = pts[-1]
            d.ell(ex + math.sin(t * 12 + i) * 6 * s, ey, 16 * s, 11 * s, (250, 214, 70), OL, 2)
    d.ell(x, fy - 88 * s, 46 * s, 54 * s, (186, 92, 186), OL, 3)
    for sd in (-1, 1):
        d.ell(x + sd * 18 * s, fy - 84 * s, 10 * s, 12 * s, (255, 255, 255), OL, 2); d.ell(x + sd * 18 * s, fy - 82 * s, 5 * s, 6 * s, OL)
    d.arc(x, fy - 64 * s, 10 * s, 6 * s, 20, 160, OL, 3 * s)

def goat(d, x, fy, t, s=.9):
    tap = math.sin(t * 16) * 4
    d.rect(x - 70 * s, fy - 230 * s, x + 30 * s, fy - 160 * s, (30, 32, 36), r=5, ol=(80, 84, 90), w=2)   # monitor
    d.rect(x - 22 * s, fy - 160 * s, x - 14 * s, fy - 140 * s, (60, 64, 70))
    gx, gy = x + 70 * s, fy - 190 * s
    d.ell(gx, gy + 70 * s, 50 * s, 46 * s, (236, 234, 228), OL, 3)                        # body behind the desk
    for sd in (-1, 1):
        d.poly([(gx + sd * 14 * s, gy - 34 * s), (gx + sd * 40 * s, gy - 74 * s), (gx + sd * 24 * s, gy - 30 * s)], (150, 130, 100), OL, 2)
        d.ell(gx + sd * 40 * s, gy - 18 * s, 18 * s, 8 * s, (226, 222, 214), OL, 2)
    d.poly(spline([(gx - 28 * s, gy - 30 * s), (gx + 28 * s, gy - 30 * s), (gx + 18 * s, gy + 34 * s), (gx - 18 * s, gy + 34 * s)], 6),
           (240, 238, 232), OL, 3)
    d.poly([(gx - 8 * s, gy + 30 * s), (gx + 8 * s, gy + 30 * s), (gx, gy + 60 * s)], (200, 196, 186))  # beard
    for sd in (-1, 1):
        d.ell(gx + sd * 12 * s, gy - 8 * s, 8 * s, 6 * s, (230, 200, 60), OL, 2); d.rect(gx + sd * 12 * s - 6 * s, gy - 9 * s, gx + sd * 12 * s + 6 * s, gy - 7 * s, OL)
    d.arc(gx, gy - 4 * s, 32 * s, 30 * s, 190, 350, (24, 24, 28), 5 * s)                   # headset
    d.line([(gx - 30 * s, gy), (gx - 14 * s, gy + 26 * s)], (24, 24, 28), 3 * s); d.ell(gx - 12 * s, gy + 28 * s, 5 * s, 5 * s, (24, 24, 28))
    for sd, ph in ((-1, 0), (1, math.pi)):                  # hooves on the keyboard
        d.ell(gx - 50 * s + sd * 16 * s, fy - 128 * s - (tap if sd < 0 else -tap), 10 * s, 8 * s, (90, 80, 70))
    d.rect(x - 110 * s, fy - 132 * s, x + 150 * s, fy - 118 * s, (150, 112, 74))            # desk
    d.rect(x - 100 * s, fy - 118 * s, x + 140 * s, fy, (110, 80, 54), ol=(70, 48, 30), w=2)
    d.rect(x - 60 * s, fy - 142 * s, x + 10 * s, fy - 132 * s, (200, 204, 210), r=2)       # keyboard

def oddity(img, t, sc):
    d = D(img)
    if sc == 0: penguin(d, 862, 1004, t)
    elif sc == 1: cactus(d, 852, 1000, t)
    elif sc == 2: pineapple(d, 108, 1004, t)
    elif sc == 3: hamster(d, 92, 1004, t)
    elif sc == 4: giraffe(d, 846, t)
    elif sc == 5: octopus(d, 836, 1000, t)
    else: goat(d, 130, 1000, t)

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

def couple(img, t, a='cust1', b='cust2'):
    nod = math.sin(t * 2.4) * 3
    st1 = mk('point', 'rest', look=-1, brows='up', smile=1); st1['dy'] = nod; st1['blink'] = (t % 3.3) < .12
    st2 = mk('rest', (-70, -110), out_rpose=True, look=-1, brows='flat'); st2['blink'] = ((t + 1) % 3.6) < .12
    npc(img, 806, 982, .42, NPC[a], st1)
    npc(img, 884, 988, .40, NPC[b], st2)


# ================================================================ sets
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def spot(img, cx, top, w0, w1, h, a=55):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    cone = cone.filter(ImageFilter.GaussianBlur(28 * K))
    return Image.composite(Image.new('RGB', img.size, (255, 250, 238)), img, cone)

BRANDS = {
    'bmw': dict(wall=((222, 226, 232), (242, 244, 247)), floor=((58, 62, 70), (96, 100, 108)), panel=(234, 236, 240),
               relief=(210, 214, 222), trim=(28, 105, 190), ceil=(236, 238, 242), name='B M W', namecol=(30, 34, 42),
               emb=bmw_badge, pend=(150, 459, 768)),
    'vw': dict(wall=((196, 206, 220), (226, 232, 240)), floor=((186, 190, 196), (224, 226, 230)), panel=(210, 218, 230),
               relief=(184, 194, 210), trim=(30, 90, 170), ceil=(232, 234, 238), name='V O L K S W A G E N', namecol=(26, 54, 110),
               emb=roundel, pend=(150, 459)),
    'porsche': dict(wall=((22, 22, 24), (48, 48, 52)), floor=((72, 74, 78), (112, 114, 118)), panel=(34, 34, 38), relief=(54, 54, 60),
                    trim=P_RED, ceil=(40, 40, 44), name='P O R S C H E', namecol=(236, 236, 240), emb=crest, pend=(150, 459)),
    'bentley': dict(wall=((58, 36, 24), (94, 62, 40)), floor=((36, 66, 54), (60, 94, 78)), panel=(76, 48, 32), relief=(108, 74, 48),
                    trim=(196, 170, 110), ceil=(48, 30, 20), name='B E N T L E Y', namecol=(236, 226, 196), emb=wings, pend=(150, 459, 768)),
    'lambo': dict(wall=((14, 14, 16), (36, 36, 40)), floor=((200, 202, 204), (234, 235, 236)), panel=(28, 28, 32), relief=(44, 44, 50),
                  trim=GOLD, ceil=(20, 20, 22), name='L A M B O R G H I N I', namecol=(236, 222, 180), emb=shield, pend=(150, 459)),
}

@lru_cache(None)
def bg_showroom(brand, turntable=True):
    B = BRANDS[brand]
    arr = np.concatenate([grad(WALL_Y * K, W * K, *B['wall']), grad((H - WALL_Y) * K, W * K, *B['floor'])])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(-40, W, 170):                          # tall wall panels with a relief pattern
        d.poly([(x + 8, 110), (x + 160, 110), (x + 160, WALL_Y - 40), (x + 8, WALL_Y - 40)], B['panel'])
        for yy in range(150, WALL_Y - 60, 110):
            d.line([(x + 30, yy), (x + 84, yy - 26), (x + 138, yy)], B['relief'], 3)
        d.line([(x + 8, 110), (x + 8, WALL_Y - 40)], B['trim'] + (120,), 2)
    d.rect(0, 0, W, CEIL, B['ceil'])                      # ceiling band with a light strip
    d.rect(0, CEIL - 6, W, CEIL, tuple(int(c * .7) for c in B['ceil']))
    for px in B['pend']:                                  # pendant lights
        d.line([(px, CEIL), (px, CEIL + 40)], (70, 74, 78), 3)
        d.chord(px, CEIL + 62, 46, 28, 180, 360, (52, 52, 56))
        d.ell(px, CEIL + 62, 30, 6, (255, 240, 200))
    d.rect(0, WALL_Y - 8, W, WALL_Y, B['trim'])
    d.rect(0, WALL_Y, W, WALL_Y + 6, (20, 20, 22))
    for i, y in enumerate(range(WALL_Y + 60, H, 140)):
        d.line([(0, y + i * 12), (W, y + i * 12)], tuple(min(255, c + 12) for c in B['floor'][1]), 2)
    img = spot(img, CX, 140, 70, 470, 800)
    d = D(img)
    B['emb'](d, CX, 236, 0.85)
    d.text(CX, 336, B['name'], 40, B['namecol'], path=FONT_X)
    if turntable:
        d.ell(CX, 905, 400, 50, (14, 16, 16))
        d.ell(CX, 897, 394, 44, (46, 46, 50), B['trim'], 5)
        d.ell(CX, 897, 340, 34, (60, 60, 64))
    return img

# ================================================================ characters (tesla-locked cast)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0)
SALES = dict(skin=hexc('e9bd98'), skin2=hexc('cf9f7c'), hair=hexc('b9bec8'), suit=hexc('2e323a'), suit2=hexc('1c1f25'),
             shirt=hexc('dbe8f6'), tie=hexc('1c69be'), pants=hexc('2e323a'), shoe=hexc('1a1a1e'), glasses=False, hairstyle='part',
             lids=0.45, bmw=True)       # BMW salesman: charcoal suit, pale-blue shirt, BMW-blue tie, roundel pin, pocket square
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
    if c.get('badge', not c['glasses'] and not c.get('bmw')):                  # dealer name badge with a tiny wing mark
        d.rect(x + 46, top + 92, x + 100, top + 118, (245, 245, 248), r=4)
        shield(d, x + 73, top + 105, 0.13, GOLD2, INK)
    if c.get('bmw'):                                     # roundel lapel pin + pale-blue pocket square
        bmw_badge(d, x - 74, top + 64, 0.2)
        d.poly([(x - 100, top + 128), (x - 60, top + 128), (x - 70, top + 112), (x - 84, top + 118), (x - 92, top + 110)], (196, 220, 246))
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
# ---- performance schedules: (time, left pose, right pose, extras). Buyer starts keen, gets incredulous, then defeated.
def buyer_sched():
    A, Wd = dict(brows='angry', eyes='wide'), dict(brows='up', eyes='wide', sweat=1)
    keen = dict(brows='up', smile=1)
    return [(0.0, 'rest', 'raise1', keen),                                # frame 1: walking in, waving
            (LE[0] + .2, 'rest', 'rest', keen),
            (T_LISTEN, 'rest', 'rest', dict(brows='up', eyes='wide')),
            (LS[2] - .05, 'head', 'head', dict(brows='worried', eyes='wide')),
            (LE[2] + .2, 'rest', 'rest', dict(brows='flat')),
            (LS[4] - .05, 'up', 'up', Wd),
            (LE[4] + .2, 'rest', 'point', dict(brows='up', eyes='wide')),
            (T_REAL, 'cross', 'cross', dict(brows='angry', smile=-1)),
            (LS[6] - .05, 'rest', 'point', dict(brows='flat')),
            (T_SUB, 'head', 'rest', dict(brows='up', eyes='wide')),
            (LS[8] - .05, 'up', 'up', dict(brows='angry', eyes='wide', sweat=1)),
            (LE[8] + .15, 'shrug', 'shrug', A),
            (T_OFF, 'head', 'head', dict(brows='worried', eyes='wide', sweat=1)),
            (LS[10] - .05, 'point', 'point', dict(brows='angry', eyes='wide', sweat=1)),
            (LE[10] + .2, 'hip', 'hip', dict(brows='angry')),
            (T_NOW, 'rest', 'rest', dict(brows='flat')),
            (T_30, 'chin', 'rest', dict(brows='angry')),
            (LS[12] - .05, 'point', 'rest', dict(brows='angry', smile=-1)),
            (LE[12] + .2, 'chin', 'rest', dict(brows='angry')),
            (T_BADGE, 'head', 'head', dict(brows='up', eyes='wide')),
            # front desk: resigned
            (T_S[6], 'rest', 'rest', dict(brows='flat', tired=.3)),
            (LS[14] + .1, 'rest', 'offer', dict(brows='flat', tired=.3)),
            (LE[14] + .2, 'rest', 'rest', dict(brows='flat', tired=.3)),
            (LS[16] - .05, 'cross', 'cross', dict(brows='flat', tired=.5, smile=-1)),
            (T_E18 + .3, 'head', 'rest', dict(brows='worried', tired=.4, smile=-1)),
            (T_FINAL - .1, 'rest', 'rest', dict(brows='flat', tired=.5, look=0))]

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = {3: 'open', 5: 'open', 7: 'offer', 9: 'open', 11: 'offer', 13: 'offer', 15: 'offer', 17: 'open'}
    for li, g in G.items():
        s += [(LS[li] - .05, g, 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]
    s += [(LS[1] - .05, 'open', 'clasp', {}), (T_M5 - .1, 'present', 'clasp', {}), (T_LISTEN, 'raise1', 'clasp', {}),
          (LE[1] + .3, 'clasp', 'clasp', {}),
          (T_NOW - .1, 'present', 'clasp', {}), (T_30, 'open', 'clasp', {}), (LE[11] + .2, 'clasp', 'clasp', {}),
          (T_FINAL - .05, 'open', 'clasp', dict(look=0)), (LE[18] + .3, 'clasp', 'clasp', dict(look=0))]
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
# ================================================================ polished showroom (v2): glass, graphite feature wall, glossy floor
MBLUE1, MBLUE2, MRED = (90, 170, 230), (30, 60, 140), (220, 40, 40)
FEAT = (238, 680)                                           # graphite feature wall span (x)
def _lin(a, b, n): return np.linspace(a, b, n)[:, None]

def _outside(w, h, seed=5):
    """Blurred daytime view through the glass: sky, distant towers, trees, a road with a parked car shape."""
    sky = np.zeros((h, w, 3))
    for c, (c0, c1) in enumerate(((150, 238), (186, 236), (226, 240))):
        sky[..., c] = _lin(c0, c1, h)
    im = Image.fromarray(sky.astype(np.uint8)); d = ImageDraw.Draw(im, 'RGBA')
    rng = np.random.default_rng(seed)
    x = 0
    while x < w:                                             # far towers
        bw = int(rng.uniform(.05, .12) * w); bh = int(rng.uniform(.25, .55) * h)
        g_ = rng.uniform(196, 222); col = (int(g_ - 6), int(g_), int(g_ + 10), 255)
        d.rectangle([x, h * .72 - bh, x + bw, h * .72], fill=col)
        for yy in range(int(h * .72 - bh) + 10, int(h * .72) - 10, 18):
            d.line([(x + 6, yy), (x + bw - 6, yy)], fill=(236, 240, 246, 70), width=3)
        x += bw + int(rng.uniform(.0, .04) * w)
    for i in range(14):                                      # trees
        tx, tr = rng.uniform(0, w), rng.uniform(.05, .1) * w
        d.ellipse([tx - tr, h * .70 - tr * 1.6, tx + tr, h * .74], fill=(84, 130, 80, 255))
    d.rectangle([0, h * .73, w, h], fill=(150, 152, 156, 255))
    d.rectangle([0, h * .80, w, h * .815], fill=(236, 236, 236, 255))
    return im.filter(ImageFilter.GaussianBlur(w * .022))

def _glass(img, x0, x1, y0, y1):
    """Window bay with mullions, outside view and reflection streaks (design coords)."""
    w, h = int((x1 - x0) * K), int((y1 - y0) * K)
    img.paste(_outside(w, h), (int(x0 * K), int(y0 * K)))
    d = D(img)
    st = Image.new('RGBA', img.size, (0, 0, 0, 0)); sd = D(st)
    for k_ in range(3):                                      # diagonal reflection streaks
        sx_ = x0 + (x1 - x0) * (.15 + .32 * k_)
        sd.poly([(sx_, y0), (sx_ + 50, y0), (sx_ - 120, y1), (sx_ - 170, y1)], (255, 255, 255, 46))
    img.alpha_composite(st.filter(ImageFilter.GaussianBlur(6 * K)))
    for mx in np.linspace(x0, x1, 3)[1:-1]:
        d.rect(mx - 5, y0, mx + 5, y1, (226, 228, 232))
    d.rect(x0, y0 + (y1 - y0) * .42 - 4, x1, y0 + (y1 - y0) * .42 + 4, (226, 228, 232))
    d.rect(x0 - 8, y0 - 8, x1 + 8, y0, (214, 216, 222)); d.rect(x0 - 8, y1, x1 + 8, y1 + 8, (214, 216, 222))

def _glow(img, draw_fn, radius, strength=1.0):
    g = Image.new('RGBA', img.size, (0, 0, 0, 0)); draw_fn(D(g))
    gb = g.filter(ImageFilter.GaussianBlur(radius * K))
    if strength != 1: gb.putalpha(gb.getchannel('A').point(lambda v: min(255, int(v * strength))))
    img.alpha_composite(gb); img.alpha_composite(g)

def _plant(d, x, fy, s=1.0):
    d.poly([(x - 34 * s, fy - 120 * s), (x + 34 * s, fy - 120 * s), (x + 26 * s, fy), (x - 26 * s, fy)], (232, 232, 234), (150, 150, 156), 3)
    for i in range(9):
        a = math.radians(-90 + (i - 4) * 16)
        L = (200 + 60 * math.cos(i * 1.7)) * s
        bx, by = x, fy - 118 * s
        tx, ty = bx + math.cos(a) * L * .55, by + math.sin(a) * L
        d.poly([(bx - 6 * s, by), (tx, ty), (bx + 6 * s, by)], (54 + i * 4, 120 + i * 5, 66))

@lru_cache(None)
def bg_bmw(desk=False):
    TOP = 128
    floor = np.zeros(((H - WALL_Y) * K, W * K, 3))
    for c, (c0, c1) in enumerate(((212, 150), (214, 154), (220, 162))):
        floor[..., c] = _lin(c0, c1, (H - WALL_Y) * K)
    wall = np.zeros((WALL_Y * K, W * K, 3))
    for c, (c0, c1) in enumerate(((240, 222), (241, 224), (244, 230))):
        wall[..., c] = _lin(c0, c1, WALL_Y * K)
    img = Image.fromarray(np.concatenate([wall, floor]).astype(np.uint8)).convert('RGBA'); d = D(img)
    # ceiling: dark coffer with LED strips converging to the vanishing point, downlights
    d.rect(0, 0, W, TOP, (36, 38, 44))
    for i in range(-6, 7):
        d.line([(CX + i * 180, 0), (CX + i * 120, TOP)], (58, 60, 68), 3)
    _glow(img, lambda g: [g.rect(0, TOP - 10, W, TOP - 4, (255, 255, 255, 230))], 8)
    for px in (CX - 330, CX, CX + 330):
        _glow(img, lambda g, px=px: g.ell(px, TOP - 40, 26, 7, (255, 246, 222, 255)), 10)
    # glass bays either side, graphite feature wall in the middle
    _glass(img, 0, FEAT[0] - 24, TOP + 30, WALL_Y - 70)
    _glass(img, FEAT[1] + 24, W, TOP + 30, WALL_Y - 70)
    d = D(img)
    d.rect(FEAT[0], TOP, FEAT[1], WALL_Y, (48, 51, 58))
    for x in range(FEAT[0] + 14, FEAT[1], 22):              # vertical slats
        d.line([(x, TOP + 4), (x, WALL_Y - 4)], (58, 62, 70), 3)
    d.rect(FEAT[0] - 6, TOP, FEAT[0], WALL_Y, (30, 32, 38)); d.rect(FEAT[1], TOP, FEAT[1] + 6, WALL_Y, (30, 32, 38))
    halo = Image.new('RGBA', img.size, (0, 0, 0, 0)); D(halo).ell(CX, 262, 120, 120, (190, 220, 255, 150))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(40 * K)))
    d = D(img); bmw_badge(d, CX, 262, 1.15)
    _glow(img, lambda g: g.text(CX, 380, 'B M W', 44, (255, 255, 255, 255), path=FONT_X), 6, 1.2)
    # M stripe along the wall base, LED cove light, skirting
    d = D(img)
    for i, col in enumerate((MBLUE1, MBLUE2, MRED)):
        d.rect(0, WALL_Y - 60 + i * 12, W, WALL_Y - 50 + i * 12, col)
    d.rect(0, WALL_Y - 22, W, WALL_Y, (250, 250, 252))
    _glow(img, lambda g: g.rect(0, WALL_Y - 2, W, WALL_Y + 2, (255, 255, 255, 255)), 10, 1.5)
    # floor: reflection of the wall, then perspective tile joints
    refl = img.crop((0, (WALL_Y - 330) * K, W * K, WALL_Y * K)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(5 * K))
    fa = Image.fromarray((np.linspace(110, 0, refl.height)[:, None] * np.ones((1, refl.width))).astype(np.uint8))
    refl.putalpha(fa); img.alpha_composite(refl, (0, WALL_Y * K))
    d = D(img)
    vy = WALL_Y - 420
    for i in range(-12, 13):
        x2 = CX + i * 260
        d.line([(CX + (x2 - CX) * (WALL_Y - vy) / (H - vy), WALL_Y), (x2, H)], (255, 255, 255, 30), 2)
    y, step = WALL_Y + 40, 40
    while y < H:
        d.line([(0, y), (W, y)], (255, 255, 255, 26), 2); step *= 1.35; y += step
    # planters at the far edges
    _plant(d, 26, WALL_Y + 30, 1.1); _plant(d, 1056, WALL_Y + 30, 1.1)
    if not desk:                                             # turntable: chrome rim, glossy top (LED ring drawn per frame)
        d.ell(CX, 922, 418, 60, (0, 0, 0, 70))
        d.ell(CX, 912, 410, 54, (120, 124, 132)); d.ell(CX, 908, 410, 50, (176, 180, 188))
        d.ell(CX, 900, 404, 46, (34, 36, 42))
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); D(sh).ell(CX - 80, 892, 260, 22, (255, 255, 255, 40))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10 * K)))
    img = spot(img.convert('RGB'), CX, TOP, 60, 430, 790, 40).convert('RGBA')
    return img

@lru_cache(None)
def car_reflection(key, width):
    ph = car_photo(key, width)
    r = ph.transpose(Image.FLIP_TOP_BOTTOM).crop((0, 0, ph.width, ph.height // 2)).filter(ImageFilter.GaussianBlur(2 * K))
    a = np.array(r.getchannel('A')).astype(float) * np.linspace(.38, 0, r.height)[:, None]
    r.putalpha(Image.fromarray(a.astype(np.uint8)))
    return r

@lru_cache(None)
def _sweep_band(w, h):
    xx = np.arange(w)[None, :]; yy = np.arange(h)[:, None]
    return xx + yy * .55                                     # diagonal coordinate

def light_sweep(ph, k):
    """Specular band crossing the car photo, k in [0, 1]."""
    w, h = ph.size
    u = _sweep_band(w, h)
    c = -0.3 * w + k * 1.9 * w
    band = np.clip(1 - np.abs(u - c) / (0.07 * w), 0, 1) ** 2 * 120
    a = (band * np.array(ph.getchannel('A')) / 255).astype(np.uint8)
    lay = Image.new('RGBA', ph.size, (255, 255, 255, 0)); lay.putalpha(Image.fromarray(a))
    out = ph.copy(); out.alpha_composite(lay); return out

def led_ring(img, t):
    g = Image.new('RGBA', img.size, (0, 0, 0, 0)); gd = D(g)
    gd.arc(CX, 906, 406, 49, 0, 180, (60, 150, 240, 230), 4)
    a0 = (t * 70) % 360                                      # a bright chase running round the ring
    gd.arc(CX, 906, 406, 49, a0, a0 + 40, (200, 235, 255, 255), 6)
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(5 * K))); img.alpha_composite(g)

# ---- shot list: cut to whoever speaks (two-camera sitcom grammar), wide for car swaps / props, car close-up on the rev
T_REV = LE[1] + .08                                         # the real M5 recording starts here
SHOT_LINES = {0: 'W', 1: 'S', 2: 'B', 3: 'S', 4: 'B', 5: 'M', 6: 'W', 7: 'S', 8: 'B', 9: 'M', 10: 'B', 11: 'S',
              12: 'B', 13: 'M', 14: 'W', 15: 'S', 16: 'B', 17: 'S', 18: 'F'}
def _shots():
    s = [(0.0, 'W')]
    for li, k in SHOT_LINES.items():
        if li: s.append((LS[li] - .06, k))
    s += [(T_M5 - .15, 'M'), (T_REV, 'C'), (T_NOW - .12, 'W')]
    return sorted(s)
SHOTS = _shots()
SHOT_T = [s[0] for s in SHOTS]
SWEEPS[:] = [0.4, T_M5 - .1, T_REV + .3, SWAPS[0][0] + SLIDE + .1, LS[9] + 1.0, SWAPS[1][0] + SLIDE + .1, T_SENG,
             T_S[6] + .8, T_TAKE]
def shot_at(t):
    i = max(j for j, s in enumerate(SHOTS) if s[0] <= t)
    return SHOTS[i][1], SHOTS[i][0]

def desk_front(img):
    """Reception counter (glossy white, BMW-blue underglow) in front of the salesman; monitor on top."""
    d = D(img)
    _glow(img, lambda g: g.rect(530, 1890, 990, 1900, (60, 150, 240, 255)), 12, 1.4)
    d = D(img)
    d.rect(506, 1300, 1004, 1330, (252, 252, 254), r=8, ol=(170, 174, 182), w=3)
    top = np.zeros((590 * K, 476 * K, 3))
    for c, (c0, c1) in enumerate(((244, 206), (245, 208), (248, 214))):
        top[..., c] = _lin(c0, c1, 590 * K)
    img.paste(Image.fromarray(top.astype(np.uint8)), (518 * K, 1330 * K))
    d = D(img)
    d.rect(518, 1330, 994, 1920, None, ol=(170, 174, 182), w=3)
    for i, col in enumerate((MBLUE1, MBLUE2, MRED)):
        d.rect(518, 1380 + i * 10, 994, 1388 + i * 10, col)
    bmw_badge(d, 756, 1560, 0.9)
    d.rect(856, 1190, 974, 1282, (24, 26, 30), r=8, ol=(110, 114, 120), w=3)
    d.rect(866, 1200, 964, 1272, (40, 90, 160), r=4)
    d.rect(906, 1282, 924, 1300, (150, 154, 160))

def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    desk = sc == 6
    img = bg_bmw(desk).copy()
    oddity(img, t, sc)
    if desk:                                                 # the sold Z4 waits at the back, small
        put_car(img, 'z4', 520, 0.0, s=.5, t=t)
        if t >= T_TAKE:
            put(img, stamp_img('SOLD', (210, 30, 40), 44), 560, 700, popin(t, T_TAKE, .3), 1.0, rot=-8)
    else:
        platform(img, t)
    d = D(img)
    f = int(round(t * FPS))
    if sc == 0:
        walk_k, bx0, dur_w = prog(t, 0, 1.3), 110, 11       # frame 1: already walking in
    elif sc == 6:
        walk_k, bx0, dur_w = prog(t, T_S[6], .9), 40, 9
    else:
        walk_k, bx0, dur_w = 1.0, 270, 11
    bx = bx0 + (270 - bx0) * oc(walk_k)
    for who, x, sched, cfg, spk in (('S', 690 if desk else 670, SS_, SALES, 'S'), ('B', bx, BS, BUYER, 'B')):
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
        if who == 'S' and desk:
            desk_front(img); d = D(img)
    return img

SHOT_P = {'W': (1.03, 0, 0), 'M': (1.2, 0, 0), 'S': (1.48, 130, 0), 'B': (1.48, -200, 0), 'C': (1.7, 0, -184)}
PUNCH = {0: ((T_M5, .03),), 1: ((T_SPK2, .06), (T_ASSIST, .03)), 2: ((T_SUB, .03), (T_18, .04)),
         3: ((T_MONTH, .07), (T_415, .03), (T_OFF, .05)), 4: ((T_ALREADY, .06), (T_WARM, .03), (T_Z4, .03)),
         5: ((T_SFAC, .02), (T_BADGE, .05)), 6: ((T_MUCH, .04), (T_E18, .05))}
def camera(t):
    sc = scene_at(t); kind, t0 = shot_at(t)
    if kind == 'F':                                          # salesman turns to the viewer: slow push in on him
        pk = io(prog(t, t0, 1.6)); z, sx, sy = 1.3 + .22 * pk, 160, 0
    else:
        z, sx, sy = SHOT_P[kind]
        if sc == 6 and kind == 'S': sx = 160
        z += 0.03 * io(prog(t, t0, 4))                       # slow creep in every shot
    if t < 1.6: z += 0.07 * (1 - oc(prog(t, 0, 1.6)))       # frame 1: already moving (pull-out as he walks in)
    sx += 3 * math.sin(t * .9); sy += 2 * math.sin(t * 1.3 + 1)          # handheld breathing
    if T_REV <= t < T_REV + 2.6:                             # the M5 revs: the camera rattles with it
        e = math.sin(math.pi * prog(t, T_REV, 2.6)) ** .6
        sx += 7 * e * math.sin(t * 73); sy += 5 * e * math.sin(t * 59 + 2)
    if sc == 3 and T_MONTH - .2 <= t < T_MONTH + .7:         # outburst shake
        k_ = 1 - prog(t, T_MONTH - .2, .9)
        sx += 12 * k_ * math.sin(t * 61); sy += 9 * k_ * math.sin(t * 47 + 1)
    for tp, amt in PUNCH[sc]:
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
GREEN, TAG, RED, BLUE = (70, 200, 120), (255, 214, 64), (226, 48, 58), (28, 105, 190)
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
CARD4 = (("$18/month", 66, INK2), ("$180/year", 66, INK2), ("$415 unlimited", 66, DRED))
CHIPS5 = [('HARDWARE', 'YOURS', GREEN, 'T_HW'), ('WARMTH', 'RENTED', RED, 'T_WARM')]
CHIPS5B = [('ENGINE', '3.0L INLINE-SIX', BLUE, 'T_30'), ('GEARBOX', '8-SPEED AUTO', BLUE, 'T_8SP'),
           ('BUILT IN', 'AUSTRIA', BLUE, 'T_AUT')]
CHIPS6 = [('ENGINE', 'SAME', GREEN, 'T_SENG'), ('GEARBOX', 'SAME', GREEN, 'T_SGB'), ('FACTORY', 'SAME', GREEN, 'T_SFAC'),
          ('BADGE', 'DIFFERENT', RED, 'T_BADGE')]
FINAL = [("Would you pay a monthly", 62, TAG), ("fee for heated seats?", 66, TAG), ("Comment below.", 70, (255, 255, 255)),
         ("Next: another car", 64, (210, 214, 224)), ("that's secretly", 64, (210, 214, 224)), ("another car.", 64, (210, 214, 224))]
FINAL_Y0, FINAL_DY = 410, 104
ONSCREEN = (['B M W', 'M5', '3 SERIES', 'Z4 M40i', 'ACTIVE SOUND DESIGN', 'HEATED SEATS', '$18/month', 'SEATS: OFF', 'SOLD',
             'TOYOTA GR SUPRA'] + [r[0] for r in CARD4] + [x for r in CHIPS5 + CHIPS5B + CHIPS6 for x in r[:2]]
            + [f[0] for f in FINAL])

def chip_rows(d, t, rows, y0, a, x0=110, x1=800):
    al = int(255 * a)
    for i, (lab, chip, col, tn) in enumerate(rows):
        t_lab = globals()[tn]
        if t < t_lab - .05: continue
        ra = min(a, prog(t, t_lab - .05, .2))
        k_ = popin(t, t_lab - .05, .3)
        w_ = font(32 * K).getlength(chip) / K
        y = y0 + i * 76
        d.text(x0, y, lab, 34, (220, 224, 234, int(255 * ra)), anchor='lm', path=FONT_X)
        d.rect(x1 - (w_ + 36) * k_, y - 28, x1, y + 28, col + (al,), r=12)
        if k_ > .6: d.text(x1 - (w_ + 36) / 2, y + 1, chip, 32, (255, 255, 255, al))

def chip_panel(img, t, rows, t0, t1, y0):
    a = window(t, t0, t1, .15, .25)
    if a <= 0: return False
    d = D(img)
    panel(d, 80, y0 - 52, 830, y0 + 76 * (len(rows) - 1) + 52, a)
    chip_rows(d, t, rows, y0, a)
    return True

@lru_cache(None)
def speaker_icon():
    """Car-audio speaker with sound waves and a label: the 'Active Sound Design' prop."""
    c = Image.new('RGBA', (460 * K, 300 * K), (0, 0, 0, 0)); d = D(c)
    d.rect(10, 14, 450, 296, (0, 0, 0, 80), r=26)
    d.rect(0, 0, 440, 284, (246, 247, 250), r=26, ol=(28, 105, 190), w=6)
    d.rect(60, 70, 150, 160, (40, 44, 52), r=10)
    d.poly([(150, 70), (220, 26), (220, 204), (150, 160)], (40, 44, 52))
    for i, r_ in enumerate((40, 74, 108)):
        d.arc(232, 115, r_, r_ * 1.1, -50, 50, (28, 105, 190), 10)
    d.rect(20, 222, 420, 270, (28, 105, 190), r=12)
    d.text(220, 246, 'ACTIVE SOUND DESIGN', 30, (255, 255, 255))
    return c

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    used = False
    sc = scene_at(t)
    # (nothing before 3 s: the first overlay is the speaker at ~11 s)
    if sc == 1:
        a = window(t, T_SPK - .05, T_S[2] + .05, .12, .25)
        if a > 0:
            used = True
            wob = 1 + .05 * math.sin(t * 22) * (t < T_ASD)        # pulses while the "engine" plays
            put(img, speaker_icon(), CX, 520, popin(t, T_SPK - .05, .35) * .95 * wob, a, rot=-2)
    elif sc == 2:
        pa = window(t, T_HEAT - .05, T_18 - .05, .12, .2)
        if pa > 0:                                             # the seats, already fitted in the car
            used = True
            put(img, photo_card('bmw_3series_seats.jpg', 'HEATED SEATS', (24, 30, 44), (255, 255, 255), 420), CX, 420,
                popin(t, T_HEAT - .05, .35), pa, rot=-2)
        ta = window(t, T_18 - .05, T_S[3] + .05, .1, .25)
        if ta > 0:
            used = True
            sw = math.sin((t - T_18) * 6) * 4 * math.exp(-(t - T_18) * 2)
            put(img, price_tag('$18/month', 'HEATED SEATS', TAG), CX, 480, popin(t, T_18 - .05, .35) * .9, ta, rot=sw - 3)
    elif sc == 3:
        a = window(t, T_180 - .1, T_S[4] + .05, .1, .25)
        if a > 0:
            used = True
            s = popin(t, T_180 - .1, .35)
            if t >= T_415: s *= 1 + .06 * math.sin((t - T_415) * 14) * math.exp(-(t - T_415) * 4)
            put(img, info_card(CARD4, 600), CX, 470, s, a, rot=-1.5)
            if t >= T_OFF - .05:
                put(img, stamp_img('SEATS: OFF', RED, 70), CX + 30, 600, popin(t, T_OFF - .05, .25), a, rot=-9)
    elif sc == 4:
        used |= chip_panel(img, t, CHIPS5, T_HW - .1, T_NOW - .1, 300)
        used |= chip_panel(img, t, CHIPS5B, T_30 - .1, T_S[5] + .05, 1400)
    elif sc == 5:
        pa = window(t, T_SUPRA - .1, T_S[6] + .05, .12, .25)
        if pa > 0:                                             # the Toyota, for comparison
            used = True
            put(img, photo_card('toyota_supra.jpg', 'TOYOTA GR SUPRA', (200, 30, 40), (255, 255, 255), 360), CX, 300,
                popin(t, T_SUPRA - .1, .35) * .9, pa, rot=2)
        used |= chip_panel(img, t, CHIPS6, T_SENG - .1, T_S[6] + .05, 1340)
    else:
        ta = window(t, T_E18 - .05, T_FINAL - .1, .1, .25)
        if ta > 0:
            used = True
            sw = math.sin((t - T_E18) * 6) * 4 * math.exp(-(t - T_E18) * 2)
            put(img, price_tag('$18/month', 'HEATED SEATS', TAG), CX, 520, popin(t, T_E18 - .05, .35) * .9, ta, rot=sw + 3)
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
TR = 0.4                                                    # whip-pan length (into the front desk only)
def frame(n):
    t = n / FPS
    tr = T_S[6] if T_S[6] - TR / 2 <= t < T_S[6] + TR / 2 else None
    if tr is None:
        img = shoot(t)                                      # showroom scenes: hard cuts between framings
    else:                                                   # whip pan: showroom out left, desk in from right, motion blur
        k = io(prog(t, tr - TR / 2, TR))
        a, b = shoot(min(t, tr - .001), 5), shoot(max(t, tr), 6)
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
ENGINE = os.path.expanduser('~/.cache/bmw-dealership-experience/m5_engine.opus')   # user-supplied, kept outside git
def engine_clip(sr):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', ENGINE, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                                        capture_output=True, check=True).stdout, np.float32).astype(np.float64)
def build_audio(voice, out_wav):
    SR = sfx.SR
    v = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rng = np.random.default_rng(3); T_ = np.arange(n) / SR
    def lpf(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
    # quiet showroom room tone; room left for the user's own music
    room = lpf(rng.standard_normal(n), 60) * 0.10 + 0.004 * np.sin(2 * np.pi * 110 * T_)
    bed = room + (0.004 * np.sin(2 * np.pi * 60 * T_)) * (T_ >= T_S[6])
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
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
    for k_ in range(4): add(0.02 + k_ * 0.3, step(), .5)                 # buyer walking in from frame 1
    add(T_M5 - .1, sfx.pop(), .3)
    eng = engine_clip(SR)                                    # the real M5 Competition recording (user-supplied)
    vr = np.sqrt(np.mean(v[np.abs(v) > .02] ** 2)); er = np.sqrt(np.mean(eng[:int(SR * 3.5)] ** 2))
    eng = eng * (vr / er) * 1.15
    dk = np.ones(len(eng)); tt_ = np.arange(len(eng)) / SR                       # full for the rev, ducked under the next lines
    dk = np.where(tt_ < LS[2] - T_REV - .1, 1.0, .22) * np.clip((6.5 - tt_) / 1.5, 0, 1)
    add(T_REV, eng * dk / .55, .55)
    add(T_SPK, click(900, 1400, .08), .5); add(T_SPK + .05, sfx.pop(), .3)
    tin = eng[int(SR * .5):int(SR * 2.3)]; tin = tin - lpf(tin, 24)               # same rev, thin 'through the speakers'
    add(T_ASD, tin * np.linspace(1, 0, len(tin)) / .55, .3)
    add(T_HEAT - .05, sfx.pop(), .3); add(T_18 - .05, sfx.pop(), .35); add(T_18 + .3, sfx.cha_ching(), .3)
    for ts, _, _ in SWAPS:                                    # cars sliding across the platform
        add(ts - .05, sfx.whoosh(.6, 16), .45); add(ts + SLIDE - .1, sfx.thump(.2), .3)
    for s_ in T_S[1:6]:                                       # hard-cut accents
        add(s_ - .02, sfx.thump(.15), .18)
    add(T_180 - .1, sfx.stamp(), .3); add(T_415 + .25, sfx.cha_ching(), .35)
    add(T_OFF - .05, click(1800, 2600, .05), .8); add(T_OFF, sfx.slide_down(), .3)
    add(T_HW - .1, sfx.pop(), .25); add(T_HW + .05, sfx.ding(1320, .6), .12); add(T_WARM, sfx.buzzer(.25), .2)
    for tn in (T_30, T_8SP, T_AUT): add(tn - .05, sfx.pop(), .22)
    add(T_SUPRA - .1, sfx.pop(), .3)
    for tn in (T_SENG, T_SGB, T_SFAC): add(tn - .05, sfx.ding(1568, .4), .1)
    add(T_BADGE - .05, sfx.buzzer(.25), .22)
    add(T_S[6] - .22, sfx.whoosh(.45, 18), .5); add(T_S[6] + .12, sfx.thump(), .3)
    for k_ in range(3): add(T_S[6] + .08 + k_ * .3, step(), .35)
    add(T_TAKE, sfx.stamp(), .3); add(T_E18 - .05, sfx.pop(), .35); add(T_E18 + .35, sfx.cha_ching(), .3)
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

