"""Brand-origin showroom skit renderer (lamborghini-tractor-origin, toyota-loom-origin, subaru-aircraft-origin,
porsche-beetle-origin, miata-best-seller). One brand showroom; real photo exhibits slide on and off a glossy display
platform with a label above; buyer + brand-dressed salesman in front; glossy floor reflections; one unmentioned oddity
per scene in the showroom windows. Cast, poses, lip sync, captions and mix chain come from bmw-heated-seats.
Usage: python engine.py VIDEO_DIR video VOICE.wav OUT.mp4 | still T OUT.png VOICE | meta OUT.json | thumb OUT.png"""
import json, math, os, sys, subprocess, importlib.util
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import (K, FONT_B, FONT_X, OL, D, scaled, spline, clamp, prog, oc, io, ob, popin, window, mix, hexc, font)
import oddities as ODD
import sfx

VDIR = os.path.abspath(sys.argv[1])
NAME = os.path.basename(VDIR)
_spec = importlib.util.spec_from_file_location('script', os.path.join(VDIR, 'src', 'script.py'))
S = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(S)
CACHE = os.path.expanduser(f'~/.cache/{NAME}')
W, H, FPS = 1080, 1920, 30
CX = 459                                   # composition centre (left 85% of width)
WALL_Y, FEET_Y, PS = 1000, 1800, 0.9       # floor line, feet, character scale
BX, SX = 172, 748                          # buyer / salesman x
PLAT_Y, PLAT_RX, PLAT_RY, PLAT_D = 962, 334, 40, 46
WINS = {'L': (18, 318, 252, 652), 'R': (666, 318, 900, 652)}
WORDS = json.load(open(os.path.join(VDIR, 'src', 'words.json')))
DUR = round(WORDS[-1]['e'] + 2.4, 2)
B = S.BRAND

# ---- timeline
LINES = {}
for w in WORDS: LINES.setdefault(w['line'], []).append(w)
NL = len(S.LINES)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
def word_t(line, txt):
    return next(w['s'] for w in LINES[line] if txt.lower() in w['w'].lower())
FIRST = {}
for i, (_, _, sc) in enumerate(S.LINES): FIRST.setdefault(sc - 1, i)
SCENES = [0.0] + [LS[FIRST[i]] - 0.55 for i in range(1, 6)]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
T_FINAL = LS[NL - 1]
BEAT = (LE[NL - 2], T_FINAL)
T_CARD = LE[NL - 1] + 0.3
CHIP_T = {li: max(3.05, word_t(li, wd) - .05) for li, wd, _ in S.CHIPS.values()}
PUNCHES = sorted(word_t(li, wd) for li, wd in S.PUNCH)

# ---- exhibits: real photo cut-outs (cutout.py), sliding on/off the platform
@lru_cache(None)
def exhibit(key):
    im = Image.open(os.path.join(CACHE, 'cut', key + '.png')).convert('RGBA')
    return im

@lru_cache(None)
def exhibit_refl(key):
    im = exhibit(key)
    fl = ImageOps.flip(im)
    hgt = fl.height; ramp = np.clip(1 - np.arange(hgt) / (hgt * .55), 0, 1) ** 1.6 * .36
    a = (np.array(fl.getchannel('A'), np.float32) * ramp[:, None]).astype(np.uint8)
    fl = fl.filter(ImageFilter.GaussianBlur(2 * K)); fl.putalpha(Image.fromarray(a))
    return fl

SLIDE_IN, SLIDE_OUT = .55, .42
def exhibit_states(t):
    """[(key, x_offset)] currently on the platform (two during a slide)."""
    sc = scene_at(t); cur = S.SCENE_EXHIBIT[sc]
    if sc == 0: return [(cur, 0.0)]
    t0 = SCENES[sc]; prev = S.SCENE_EXHIBIT[sc - 1]
    if prev == cur: return [(cur, 0.0)]
    out = []
    ko = prog(t, t0, SLIDE_OUT)
    if ko < 1: out.append((prev, -1100 * ko ** 2))
    ki = prog(t, t0 + .2, SLIDE_IN)
    out.append((cur, 1100 * (1 - ob(ki)) if ki < 1 else 0.0))
    return out

# ================================================================ showroom background
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))

def glow_text(img, x, y, txt, size, col, glow, spacing=0.12, path=FONT_B):
    f = font(size * K, path)
    widths = [f.getlength(c) for c in txt]; total = sum(widths) + spacing * size * K * (len(txt) - 1)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    px = x * K - total / 2
    for c, cw in zip(txt, widths):
        ld.text((px, y * K), c, font=f, fill=col + (255,), anchor='lm'); px += cw + spacing * size * K
    g = lay.getchannel('A').filter(ImageFilter.GaussianBlur(14 * K))
    img.paste(Image.new('RGB', img.size, glow), (0, 0), g.point(lambda v: int(v * .9)))
    img.paste(lay, (0, 0), lay)

def sky(w, h):
    """Window view: brand sky gradient, a sun, soft clouds and a distant skyline."""
    arr = grad(h * K, w * K, *B['sky']).astype(np.uint8)
    im = Image.fromarray(arr.copy()); d = D(im)
    if B.get('starfield'):
        r = np.random.default_rng(5)
        for _ in range(40): d.ell(r.uniform(0, w), r.uniform(0, h * .7), 1.6, 1.6, (255, 255, 255, 220))
        d.ell(w * .7, h * .22, 26, 26, (250, 246, 220))
    else:
        d.ell(w * .72, h * .25, 30, 30, (255, 244, 200, 230))
        for cx_, cy_ in ((w * .25, h * .18), (w * .6, h * .42)):
            for dx, r_ in ((-26, 18), (0, 24), (26, 18)): d.ell(cx_ + dx, cy_, r_, r_ * .8, (255, 255, 255, 190))
    r = np.random.default_rng(len(B['name']))
    x = 0
    while x < w:
        bw = r.uniform(18, 40); bh = r.uniform(40, 120)
        d.rect(x, h - bh, x + bw, h, (40, 48, 70) if not B.get('starfield') else (10, 16, 40))
        for wy in np.arange(h - bh + 8, h - 6, 12):
            if r.random() < .5: d.rect(x + 5, wy, x + 9, wy + 5, (255, 220, 140))
        x += bw + 2
    return im

@lru_cache(None)
def background():
    img = Image.fromarray(np.concatenate([grad(WALL_Y * K, W * K, *B['wall']),
                                          grad((H - WALL_Y) * K, W * K, *B['floor'])]).astype(np.uint8))
    d = D(img)
    tr, ac = B['trim'], B['accent']
    for x in range(-60, W, 180):                                      # tall wall panels with a soft sheen
        d.rect(x + 10, 96, x + 170, WALL_Y - 30, B['panel'])
        d.poly([(x + 22, 96), (x + 70, 96), (x + 30, WALL_Y - 30), (x + 18, WALL_Y - 30)], (255, 255, 255, 14))
    if B.get('hexes'):                                                 # faint gold hexagon wall pattern
        for row, yy in enumerate(range(110, WALL_Y - 30, 52)):
            for xx in range(-30 + (30 if row % 2 else 0), W, 60):
                pts = [(xx + 26 * math.cos(math.pi / 3 * k + math.pi / 6), yy + 26 * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)]
                d.poly(pts, None, tr + (34,), 2)
    if B.get('starfield'):
        r = np.random.default_rng(9)
        for _ in range(160):
            d.ell(r.uniform(0, W), r.uniform(100, WALL_Y - 40), r.uniform(1, 2.6), r.uniform(1, 2.6), (220, 230, 255, int(r.uniform(60, 200))))
    d.rect(0, 0, W, 78, tuple(int(c * .6) for c in B['wall'][0]))      # ceiling band with downlights
    d.rect(0, 74, W, 82, tr)
    for px in range(60, W, 120):
        d.ell(px, 60, 18, 7, (255, 248, 226))
    for name, (x0, y0, x1, y1) in WINS.items():                       # windows: frame + sky
        img.paste(sky(x1 - x0, y1 - y0), (x0 * K, y0 * K))
        d.rect(x0 - 10, y0 - 10, x1 + 10, y1 + 6, None, ol=(16, 16, 18), w=10)
    for gl in range(3):                                                # light cones onto the platform
        cone = Image.new('L', img.size, 0); cx_ = CX - 220 + gl * 220
        ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx_ - 30, 80), (cx_ + 30, 80), (cx_ + 170, PLAT_Y + 40), (cx_ - 170, PLAT_Y + 40)]], fill=60)
        cone = cone.filter(ImageFilter.GaussianBlur(26 * K))
        img = Image.composite(Image.new('RGB', img.size, (255, 248, 230)), img, cone)
    d = D(img)
    glow_text(img, CX, 196, B['name'], 112 if len(B['name']) < 9 else 84, B['namecol'], tuple(int(c * .55) for c in ac))
    d = D(img)
    d.rect(CX - 300, 268, CX + 300, 274, ac, r=3)                     # LED strip under the name
    # floor: mirrored wall (glossy), tile lines, LED trim at the wall base
    wall = img.crop((0, (WALL_Y - 420) * K, W * K, WALL_Y * K)).transpose(Image.FLIP_TOP_BOTTOM)
    wall = wall.filter(ImageFilter.GaussianBlur(3 * K))
    m = Image.fromarray((np.clip(1 - np.arange(wall.height) / wall.height, 0, 1) ** 2 * 80)[:, None].repeat(wall.width, 1).astype(np.uint8))
    img.paste(wall, (0, WALL_Y * K), m)
    d = D(img)
    for i in range(-12, 13):                                           # perspective tile seams
        d.line([(CX + i * 18, WALL_Y), (CX + i * 260, H + 200)], (255, 255, 255, 16), 2)
    for k_ in range(1, 9):
        y = WALL_Y + 900 * (k_ / 9) ** 1.6
        d.line([(0, y), (W, y)], (255, 255, 255, 14), 2)
    d.rect(0, WALL_Y - 6, W, WALL_Y + 2, ac)
    d.rect(0, WALL_Y + 2, W, WALL_Y + 14, ac + (60,))
    # platform: glossy black drum, accent LED ring, highlight
    d.ell(CX, PLAT_Y + PLAT_D + 16, PLAT_RX + 30, PLAT_RY + 14, (0, 0, 0, 120))
    d.rect(CX - PLAT_RX, PLAT_Y, CX + PLAT_RX, PLAT_Y + PLAT_D, (16, 16, 20))
    d.ell(CX, PLAT_Y + PLAT_D, PLAT_RX, PLAT_RY, (16, 16, 20))
    d.arc(CX, PLAT_Y + PLAT_D, PLAT_RX, PLAT_RY, 0, 180, ac, 5)
    d.ell(CX, PLAT_Y, PLAT_RX, PLAT_RY, (34, 34, 40), (70, 70, 80), 3)
    d.ell(CX - 60, PLAT_Y - 8, PLAT_RX * .6, PLAT_RY * .4, (255, 255, 255, 26))
    return img

@lru_cache(None)
def sky_crop(side):
    x0, y0, x1, y1 = WINS[side]
    return background().crop((x0 * K, y0 * K, x1 * K, y1 * K))

# ---- oddities: (function, where, scale, dx, dy from window bottom-centre)
ODDS = {
    'giraffe': (ODD.giraffe, 'sky', .95, 0, 70), 'astronaut': (ODD.astronaut, 'sky', .9, 0, -10),
    'ufo': (ODD.ufo, 'sky', .95, 0, 0), 'cow_balloon': (ODD.cow_balloon, 'sky', .95, 0, -10),
    'octopus': (ODD.octopus, 'sky', 1.0, 0, 0), 'bear': (ODD.bear, 'sky', .95, 0, 0),
    'penguin': (ODD.penguin, 'sill', 1.3, 0, 0), 'flamingo': (ODD.flamingo, 'sill', 1.15, -10, 0),
    'llama': (ODD.llama, 'sill', 1.05, 16, 0), 'cat': (lambda d, x, fy, t: ODD.cat(d, x, fy, t, push=max(0, math.sin(t * .8)) ** 4), 'sill', 1.5, 10, 0),
    'sheep': (lambda d, x, fy, t: ODD._sheep(d, x, fy, t, 1.0), 'sill', 1.45, 0, 0), 'snowman': (ODD.snowman, 'sill', .9, 0, 0),
    'dino': (ODD.dino, 'sill', .8, 0, 0), 'pigeon': (ODD.pigeon, 'sill', 1.3, 30, 0),
}

def draw_oddity(img, t, sc):
    name, side = S.ODDITIES[sc]
    fn, where, s, dx, dy = ODDS[name]
    x0, y0, x1, y1 = WINS[side]
    X, Y = (x0 + x1) / 2 + dx, y1 + dy
    tt = t - SCENES[sc] + 1.0
    if where == 'sky':
        lay = sky_crop(side).copy()
        fn(scaled(lay, X, Y, s, x0, y0), 0, 0, tt)
        img.paste(lay, (x0 * K, y0 * K))
    d = D(img)
    d.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], (16, 16, 18), 6)          # mullions over the view
    d.line([(x0, y0 + (y1 - y0) * .42), (x1, y0 + (y1 - y0) * .42)], (16, 16, 18), 6)
    d.rect(x0 - 16, y1, x1 + 16, y1 + 14, (60, 60, 66), ol=(16, 16, 18), w=3)     # sill
    if where == 'sill':
        fn(scaled(img, X, Y, s), 0, 0, tt)

def stars6(img, t):
    """Subaru only: six stars light up on the wall when the salesman says 'Six stars'."""
    if not getattr(S, 'STARS', None): return
    t0 = word_t(*S.STARS)
    if t < t0 or scene_at(t) != 4: return
    d = D(img)
    pts = [(CX + 70, 330), (CX - 10, 380), (CX + 34, 404), (CX + 96, 380), (CX + 150, 412), (CX + 60, 440)]
    pts = [(x - 40, y + 30) for x, y in pts]
    for i, (x, y) in enumerate(pts):
        k = popin(t, t0 + i * .12, .3)
        if k <= .02: continue
        r = (34 if i == 0 else 20) * k
        for a in range(4):
            ang = a * math.pi / 2
            d.poly([(x + math.cos(ang) * r, y + math.sin(ang) * r), (x + math.cos(ang + .5) * r * .28, y + math.sin(ang + .5) * r * .28),
                    (x, y), (x + math.cos(ang - .5) * r * .28, y + math.sin(ang - .5) * r * .28)], (255, 255, 255))
        d.ell(x, y, r * .5, r * .5, (200, 220, 255, 120))

# ================================================================ characters (bmw-heated-seats cast)
BUYER = dict(skin=hexc('c08862'), skin2=hexc('a06b4b'), hair=hexc('231a1c'), suit=hexc('2c3e66'), suit2=hexc('1f2c4a'),
             shirt=hexc('f7f7fa'), tie=None, pants=hexc('2b2d33'), shoe=hexc('f4f4f6'), glasses=True, hairstyle='messy', lids=0.0,
             badge=None)
SALES = {k: (hexc(v) if isinstance(v, str) and k not in ('hairstyle', 'hat') else v) for k, v in S.SALES.items()}
SALES.setdefault('glasses', False); SALES.setdefault('tie', None)
POSES = {'rest': (10, 323), 'clasp': (-100, 286), 'open': (120, 170), 'point': (235, 70), 'up': (70, -290),
         'head': (-92, -158), 'shrug': (128, 108), 'cross': (-176, 168), 'thanks': (-100, 92), 'raise1': (40, -230),
         'offer': (210, 120), 'chin': (-70, -110), 'hip': (90, 230), 'present': (240, -230), 'phone': (-46, -128), 'reach': (70, -250)}
UA, FA = 168, 158
OUTBEND = {'up', 'head', 'raise1', 'chin', 'reach'}
def ik(S_, T, side, out=False):
    dx, dy = T[0] - S_[0], T[1] - S_[1]
    d_ = max(1e-3, min(math.hypot(dx, dy), UA + FA - 2))
    a = (UA * UA + d_ * d_ - FA * FA) / (2 * d_)
    h = math.sqrt(max(0, UA * UA - (a * a)))
    mx, my = S_[0] + dx / d_ * a, S_[1] + dy / d_ * a
    px, py = -dy / d_, dx / d_
    if (out and px * side < 0) or (not out and py < 0):
        px, py = -px, -py
    return (mx + px * h, my + py * h), (S_[0] + dx / d_ * d_, S_[1] + dy / d_ * d_)

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
    if c.get('badge'):                                    # dealer name badge with a brand-colour stripe
        d.rect(x + 46, top + 92, x + 100, top + 118, (245, 245, 248), r=4)
        d.rect(x + 50, top + 96, x + 96, top + 103, c['badge'], r=2)
    if c.get('pocket'):                                   # pocket square
        d.poly([(x - 98, top + 98), (x - 62, top + 98), (x - 70, top + 78), (x - 84, top + 86), (x - 92, top + 76)], c['pocket'], OL, 2)
        d.line([(x - 102, top + 100), (x - 58, top + 100)], c['suit2'], 4)
    if c.get('pin'):                                      # lapel star pin
        px, py = x - 54, top + 60
        d.poly([(px + 12 * math.cos(a * math.pi / 5 - math.pi / 2) * (1 if a % 2 == 0 else .45),
                 py + 12 * math.sin(a * math.pi / 5 - math.pi / 2) * (1 if a % 2 == 0 else .45)) for a in range(10)], c['pin'], OL, 1.5)
    hx = x + st.get('look', 0) * 0.3
    hy = top - 105
    d.rect(x - 26, top - 40, x + 26, top - 4, c['skin2'])
    for s in (-1, 1):
        d.ell(hx + s * 66, hy + 6, 15, 21, c['skin'], OL, 4)
    d.ell(hx, hy, 68, 84, c['skin'], OL, 5)
    hs = c['hairstyle']
    if hs == 'messy':
        d.chord(hx, hy - 4, 74, 92, 180, 360, c['hair'])
        for px_, py_ in ((-50, -70), (-18, -92), (16, -96), (46, -78)):
            d.poly([(hx + px_ - 24, hy - 50), (hx + px_ + 8, hy + py_ - 14), (hx + px_ + 26, hy - 52)], c['hair'])
        d.poly([(hx - 74, hy - 8), (hx - 66, hy - 50), (hx - 52, hy - 20)], c['hair'])
        d.poly([(hx + 74, hy - 8), (hx + 66, hy - 50), (hx + 52, hy - 20)], c['hair'])
    elif hs == 'slick':                                   # slicked back, glossy
        d.chord(hx, hy - 8, 72, 92, 180, 360, c['hair'])
        d.poly(spline([(hx - 70, hy - 30), (hx - 50, hy - 96), (hx + 30, hy - 104), (hx + 74, hy - 50), (hx + 70, hy - 26), (hx, hy - 66)], 5), c['hair'])
        d.arc(hx - 4, hy - 66, 46, 26, 200, 320, (255, 255, 255, 90), 4)
    else:
        d.chord(hx, hy - 6, 72, 90, 180, 360, c['hair'])
        d.poly(spline([(hx - 20, hy - 96), (hx + 60, hy - 90), (hx + 78, hy - 40), (hx + 40, hy - 54), (hx - 10, hy - 60)], 5), c['hair'])
        d.poly([(hx - 72, hy - 6), (hx - 64, hy - 52), (hx - 50, hy - 24)], c['hair'])
    if c.get('hat') == 'cap':                             # flat driving cap
        d.poly(spline([(hx - 76, hy - 40), (hx - 60, hy - 100), (hx + 20, hy - 112), (hx + 78, hy - 70), (hx + 80, hy - 44)], 5), c['hatcol'], OL, 4)
        d.poly([(hx - 80, hy - 44), (hx - 112, hy - 36), (hx - 104, hy - 28), (hx - 70, hy - 34)], c['hatcol'], OL, 3)
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
        d.line([(ex - s * 14, ey + inner), (ex + s * 14, ey + outer)], c['hair'] if hs == 'messy' else c['skin2'], 6)
    if c.get('shades'):                                   # dark sunglasses
        for s in (-1, 1):
            d.rect(hx + s * 27 - 23, ey - 14, hx + s * 27 + 23, ey + 14, (14, 14, 18), r=9, ol=(200, 170, 80), w=3)
            d.line([(hx + s * 27 - 14, ey - 6), (hx + s * 27 - 4, ey - 10)], (255, 255, 255, 150), 3)
        d.line([(hx - 6, ey - 6), (hx + 6, ey - 6)], (200, 170, 80), 4)
    elif c['glasses']:
        fc = c.get('frame', (150, 158, 170))
        for s in (-1, 1):
            d.rect(hx + s * 27 - 21, ey - 19, hx + s * 27 + 21, ey + 19, None, r=8, ol=fc, w=5)
        d.line([(hx - 6, ey - 4), (hx + 6, ey - 4)], fc, 4)
    d.arc(hx, hy + 22, 7, 6, 20, 160, c['skin2'], 4)
    m, my_ = st.get('mouth', 0.0), hy + 46
    if m > 0.08:
        mh = 6 + 20 * m
        d.ell(hx, my_ + mh * 0.3, 15 + 6 * m, mh, (92, 26, 34), OL, 3)
        d.chord(hx, my_ + mh * 0.3 + mh * 0.5, 10 + 4 * m, mh * 0.45, 180, 360, (214, 98, 104))
    else:
        sm = st.get('smile', 0)
        if sm > 0: d.arc(hx, my_ - 8, 20, 14, 20, 160, OL, 5)
        elif sm < 0: d.arc(hx, my_ + 10, 18, 10, 200, 340, OL, 5)
        else: d.line([(hx - 14, my_), (hx + 14, my_)], OL, 5)
    if st.get('sweat'):
        ph = st['sweat']
        for i, (sx_, sy_) in enumerate(((-80, -40), (84, -20))):
            yy = hy + sy_ + (ph * 60 + i * 30) % 50
            d.ell(hx + sx_, yy, 8, 12, (120, 190, 240), (40, 90, 150), 2)
    for side, key in ((-1, 'lpose'), (1, 'rpose')):
        S_ = (x + side * 108, top + 30)
        ox, oy = st[key]
        T = (S_[0] + side * ox, S_[1] + oy)
        E, T = ik(S_, T, side, st.get('out_' + key, False))
        d.line([S_, E, T], OL, 56)
        d.line([S_, E, T], c['suit'], 46)
        dx, dy_ = T[0] - E[0], T[1] - E[1]; n = math.hypot(dx, dy_) or 1
        d.ell(T[0] - dx / n * 6, T[1] - dy_ / n * 6, 21, 21, c['shirt'], OL, 3)
        d.ell(T[0] + dx / n * 10, T[1] + dy_ / n * 10, 21, 21, c['skin'], OL, 4)

# ---- performance schedules
def _buyer_pose(text, k):
    if text.endswith('?!') or text.endswith('!'):
        return [('up', 'up'), ('head', 'head'), ('point', 'up')][k % 3], dict(brows='up', eyes='wide')
    if text.endswith('?'):
        return [('shrug', 'shrug'), ('rest', 'point'), ('chin', 'rest')][k % 3], dict(brows='up')
    return [('rest', 'open'), ('hip', 'point')][k % 2], dict(brows='flat', smile=1 if k % 2 else 0)

def buyer_sched():
    s = [(0.0, 'point', 'up', dict(brows='up', eyes='wide'))]                     # frame 1: already mid-reaction
    REACT = [('head', 'head', dict(brows='up', eyes='wide', sweat=1)), ('hip', 'hip', dict(brows='up')),
             ('chin', 'rest', dict(brows='worried')), ('cross', 'cross', dict(brows='flat', smile=-1)),
             ('rest', 'point', dict(brows='up', eyes='wide'))]
    kb = kr = 0
    for li, (spk, text, sc) in enumerate(S.LINES):
        if spk == 'B':
            (lp, rp), ex = _buyer_pose(text, kb); kb += 1
            s += [(LS[li] - .05, lp, rp, ex), (LE[li] + .2, 'rest', 'rest', dict(brows=ex['brows']))]
        elif li < NL - 1:
            pw = [w for l_, w in S.PUNCH if l_ == li]
            tr = word_t(li, pw[0]) if pw else (LS[li] + LE[li]) / 2
            lp, rp, ex = REACT[kr % len(REACT)]; kr += 1
            s += [(tr - .05, lp, rp, ex), (LE[li] + .3, 'rest', 'rest', dict(brows='flat'))]
    s += [(T_FINAL - .1, 'rest', 'rest', dict(brows='up', look=-1))]
    return sorted(s, key=lambda e: e[0])

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', {})]
    G = ['present', 'open', 'offer']
    k = 0
    for li, (spk, text, sc) in enumerate(S.LINES):
        if spk == 'S' and li < NL - 1:
            s += [(LS[li] - .05, G[k % 3], 'clasp', {}), (LE[li] + .2, 'clasp', 'clasp', {})]; k += 1
    s += [(T_FINAL, 'open', 'open', dict(look=0)), (LE[NL - 1] + .3, 'clasp', 'clasp', dict(look=0))]
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
    return lp, rp, ex

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
    for k_ in M: M[k_] = M[k_] * (0.75 + 0.25 * np.abs(np.sin(f * 1.9)))
    MOUTH = M

def talking(spk, t):
    return any(w['spk'] == spk and w['s'] - .05 <= t <= w['e'] + .05 for w in WORDS)

def char_layer(cfg, st):
    """Person at PS scale on a tight RGBA layer; returns (layer, design x0, design y0) with feet at FEET_Y."""
    wdt, top = 380, FEET_Y - 1120 * PS
    lay = Image.new('RGBA', (int(2 * wdt * K), int((FEET_Y - top + 24) * K)), (0, 0, 0, 0))
    person(scaled(lay, wdt, FEET_Y - top, PS), 0, 0, cfg, st)
    return lay, top

def paste_person(img, x, cfg, st):
    lay, top = char_layer(cfg, st)
    x0 = int((x - 380) * K); y0 = int(top * K)
    fl = ImageOps.flip(lay).crop((0, int(24 * K), lay.width, int(24 * K) + int(260 * K)))   # feet-first mirror image
    a = np.array(fl.getchannel('A'), np.float32) * (np.clip(1 - np.arange(fl.height) / fl.height, 0, 1) ** 1.8 * .34)[:, None]
    fl.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.paste(fl, (x0, int((FEET_Y - 2) * K)), fl)
    img.paste(lay, (x0, y0), lay)

# ================================================================ world
def label_img(txt):
    return _label(txt)
@lru_cache(None)
def _label(txt):
    f = font(30 * K, FONT_X); tw = f.getlength(txt) / K
    w_, h_ = int(tw + 56), 54
    im = Image.new('RGBA', (w_ * K, h_ * K), (0, 0, 0, 0)); d = D(im)
    d.rect(2, 2, w_ - 2, h_ - 2, (14, 14, 18, 235), r=10, ol=B['accent'], w=3)
    d.text(w_ / 2, h_ / 2 + 1, txt, 30, (255, 255, 255), path=FONT_X)
    return im

def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    img = background().copy()
    draw_oddity(img, t, sc)
    stars6(img, t)
    d = D(img)
    for key, off in exhibit_states(t):
        ex = exhibit(key)
        cx = CX + off
        ew, eh = ex.width / K, ex.height / K
        x0, y0 = cx - ew / 2, PLAT_Y + 10 - eh
        lb = label_img(S.EXHIBITS[key]['label'])
        ly = 560 if eh < 300 else PLAT_Y + 10 - eh - 46
        ly = min(ly, 590)
        for sx_ in (-1, 1):                                                       # label hangs on two wires
            d.line([(cx + sx_ * (lb.width / K / 2 - 24), 286), (cx + sx_ * (lb.width / K / 2 - 24), ly - 20)], (120, 120, 130), 2)
        img.paste(lb, (int((cx - lb.width / K / 2) * K), int((ly - lb.height / K / 2) * K)), lb)
        rf = exhibit_refl(key)
        img.paste(rf, (int(x0 * K), int((PLAT_Y + 4) * K)), rf)
        d.ell(cx, PLAT_Y + 6, ew * .46, 12, (0, 0, 0, 110))                     # contact shadow
        img.paste(ex, (int(x0 * K), int(y0 * K)), ex)
    f = int(round(t * FPS))
    walk_k = prog(t, 0, 1.3)
    bx = 120 + (BX - 120) * oc(walk_k) if sc == 0 else BX
    for who, x, sched, cfg in (('S', SX, SS_, SALES), ('B', bx, BS, BUYER)):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[who][min(f, len(MOUTH[who]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        st['dy'] = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3 + (-4 if talking(who, t) and (f // 4) % 2 else 0)
        if who == 'B' and sc == 0 and walk_k < 1:
            st['walk'] = t * 11; st['dy'] -= abs(math.sin(t * 11)) * 10
        if st.get('sweat'): st['sweat'] = t
        paste_person(img, x, cfg, st)
    return img

FRAMES = [(1.02, 0, 0), (1.08, -10, 0), (1.04, 30, 0), (1.10, 20, 0), (1.03, -20, 0), (1.06, 0, 0)]
def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    z, sx, sy = FRAMES[sc]
    z += 0.025 * io(prog(t, t0, 6))                                      # slow push
    if sc == 0: z += 0.06 * (1 - oc(prog(t, 0, 1.4)))                    # frame 1 already moving
    for tp in PUNCHES:
        if tp <= t < tp + .5: z += .04 * (1 - oc(prog(t, tp, .5)))
    pk = io(prog(t, T_FINAL - .05, .6))                                  # salesman turns to camera: push in on him
    z += 0.16 * pk; sx += (SX - CX - 60) * pk
    return z, sx, sy

def shoot(t):
    wimg = world(t)
    z, sx, sy = camera(t)
    ax, ay = CX * K, 1150 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    return wimg.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')

# ================================================================ overlays
TAG = (255, 214, 64)
@lru_cache(None)
def chip_img(txt):
    size = 42
    while font(size * K).getlength(txt) / K > 640: size -= 2
    tw = font(size * K).getlength(txt) / K
    w_, h_ = int(tw + 70), size + 44
    im = Image.new('RGBA', (w_ * K, h_ * K), (0, 0, 0, 0)); d = D(im)
    d.rect(4, 6, w_ - 2, h_ - 2, (0, 0, 0, 120), r=h_ / 2)
    d.rect(2, 2, w_ - 6, h_ - 6, B['accent'], r=h_ / 2 - 2, ol=(255, 255, 255), w=4)
    d.rect(10, 8, w_ - 14, h_ / 2, (255, 255, 255, 50), r=h_ / 2 - 8)
    dark = sum(B['accent']) > 420
    d.text((w_ - 4) / 2, (h_ - 4) / 2 + 1, txt, size, (16, 16, 20) if dark else (255, 255, 255))
    return im

def put(img, layer, cx, cy, s=1.0, a=1.0, rot=0.0):
    if rot: layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    if s <= 0.02 or a <= 0: return
    if s != 1: layer = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.LANCZOS)
    if a < 1: layer.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
    img.alpha_composite(layer, (int(cx * K - layer.width / 2), int(cy * K - layer.height / 2)))

FINAL = [(S.FINAL[0], 84, TAG), (S.FINAL[1], 64, (255, 255, 255)), (S.FINAL[2], 64, (255, 255, 255))]
FINAL_Y0, FINAL_DY = 560, 110
ONSCREEN = ([B['name']] + [e['label'] for e in S.EXHIBITS.values()] + [c[2] for c in S.CHIPS.values()] + [f[0] for f in FINAL])

def overlays(t):
    used = False
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    sc = scene_at(t)
    for li, wd, txt in S.CHIPS.values():
        t0 = CHIP_T[li]; end = min(SCENES[sc + 1] if sc + 1 < 6 else BEAT[0], t0 + 3.2)
        if S.LINES[li][2] - 1 != sc: continue
        a = window(t, t0, end, .12, .25)
        if a > 0:
            used = True
            put(img, chip_img(txt), CX, 458, popin(t, t0, .35), a, rot=-2 + math.sin((t - t0) * 5) * 2 * math.exp(-(t - t0) * 2))
    if t >= T_CARD:
        used = True
        fa = prog(t, T_CARD, .25)
        d = D(img)
        d.rect(60, FINAL_Y0 - 92, 858, FINAL_Y0 + FINAL_DY * 2 + 84, (12, 14, 20, int(228 * fa)), r=34, ol=B['accent'] + (int(255 * fa),), w=5)
        for i, (txt, size, col) in enumerate(FINAL):
            k_ = popin(t, T_CARD + .08 * i, .3)
            if k_ > .05:
                d.text(CX, FINAL_Y0 + FINAL_DY * i, txt, size * k_, col + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if used else None

def final_boxes():
    out = []
    for i, (txt, size, _) in enumerate(FINAL):
        f = font(size); bb = f.getbbox(txt, anchor='mm', stroke_width=4)
        y = FINAL_Y0 + FINAL_DY * i
        cap = f.getbbox('H')[3] - f.getbbox('H')[1]
        out.append(dict(text=txt, x0=CX + bb[0], x1=CX + bb[2], y0=y + bb[1], y1=y + bb[3], cap_height=cap))
    return out

# ================================================================ captions (bmw-heated-seats system)
def ctext(w): return w['w'].lstrip('.')
CAP_Y, CAP_SIZE = 1128, 78
def chunks():
    out = []
    for ln in sorted(LINES):
        cur = []
        for w in LINES[ln]:
            if cur and font(CAP_SIZE).getlength(' '.join(ctext(x) for x in cur + [w])) > 800:
                out.append(cur); cur = []
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
    if t >= T_CARD: return
    live = [ci for ci, c in enumerate(CHUNKS) if c['s'] - 0.02 <= t < c['e']]
    for ci in live[-1:]:
        c = CHUNKS[ci]
        act = -1
        for i, w in enumerate(c['words']):
            if w['s'] - .02 <= t: act = i
        ci_img = caption_img(ci, act)
        s = 0.86 + 0.14 * ob(prog(t, c['s'], .12))
        if s != 1: ci_img = ci_img.resize((int(W * s), int(200 * s)), Image.LANCZOS)
        img.alpha_composite(ci_img, (int(CX - ci_img.width / 2), int(CAP_Y - ci_img.height / 2)))

# ================================================================ frame
@lru_cache(None)
def vignette(strength=1.0):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - CX) / (W * .62)) ** 2 + ((yy - 1050) / (H * .58)) ** 2)
    a = np.clip((r - .62) * 1.3, 0, 1) * 200 * strength
    return Image.fromarray(np.dstack([np.zeros((H, W, 3)), a]).astype(np.uint8), 'RGBA')

def frame(n):
    t = n / FPS
    img = shoot(t)
    sc = scene_at(t)
    if sc and SCENES[sc] <= t < SCENES[sc] + .18:                          # hard cut flash at each scene change
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.3 * (1 - prog(t, SCENES[sc], .18)))
    img.alpha_composite(vignette())
    ov = overlays(t)
    if ov is not None:
        img.alpha_composite(ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA'))
    if BEAT[0] + .1 <= t < T_FINAL:                                       # the beat: room dims, everyone waits
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.2 * io(prog(t, BEAT[0] + .1, .5)))
    if T_FINAL <= t < T_FINAL + .45:
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.22 * (1 - prog(t, T_FINAL, .45)))
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
    room = lpf(rng.standard_normal(n), 60) * 0.10
    pad = sum(np.sin(2 * np.pi * f * T_) for f in (110, 164.8, 220)) * 0.004 * (0.6 + 0.4 * np.sin(2 * np.pi * T_ / 8))
    bed = room + pad                                                    # quiet; room left for the user's own music
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def sting():
        d = 2.4; tt = np.arange(int(SR * d)) / SR
        s = np.zeros_like(tt)
        for f in (73.4, 110.0, 146.8, 174.6, 220.0):
            for det in (-0.6, 0.6): s += ((tt * (f + det)) % 1 * 2 - 1)
        s = lpf(s, 6) * np.exp(-tt * 2.2) * np.minimum(1, tt * 200) * .09
        s += np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 5) * .9
        s += (rng.standard_normal(len(tt)) - lpf(rng.standard_normal(len(tt)), 4)) * np.exp(-tt * 2.6) * .25
        return s
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    for k_ in range(4): add(0.02 + k_ * 0.32, step(), .45)                # buyer hurrying in (frame 1)
    for sc in range(1, 6):
        t0 = SCENES[sc]
        add(t0, click(5200, 6400, .04), .5)                               # cut
        if S.SCENE_EXHIBIT[sc] != S.SCENE_EXHIBIT[sc - 1]:
            add(t0 - .05, sfx.whoosh(.45, 18), .5); add(t0 + .2, sfx.whoosh(.5, 14), .4)
            add(t0 + .2 + SLIDE_IN * .7, sfx.thump(), .4); add(t0 + .2 + SLIDE_IN * .8, sfx.ding(1568, .5), .1)
        else:
            add(t0 + .05, sfx.pop(), .2)
    for li in CHIP_T: add(CHIP_T[li], sfx.pop(), .32); add(CHIP_T[li] + .06, sfx.ding(2093, .5), .1)
    for name, li, wd, vol in getattr(S, 'SFX', []):
        add(word_t(li, wd), getattr(sfx, name)(), vol)
    for k_ in range(2): add(BEAT[0] + .2 + k_ * .4, click(4200, 5200, .03) * .5, .6)
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
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', tmp + '2.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = float(r.split('I:')[-1].split('LUFS')[0]); tp = float(r.split('Peak:')[-1].split('dBFS')[0])
    g = min(-14.0 - I, -1.5 - tp)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp + '2.wav', '-af', f'volume={g:.2f}dB', out_wav], check=True)
    os.remove(tmp); os.remove(tmp + '2.wav')

# ================================================================ thumbnail
def thumbnail(out):
    img = background().copy()
    key = S.THUMB_EXHIBIT
    ex = exhibit(key); s = 1.42
    ex = ex.resize((int(ex.width * s), int(ex.height * s)), Image.LANCZOS)
    ew, eh = ex.width / K, ex.height / K
    rf = ImageOps.flip(ex); a = np.array(rf.getchannel('A'), np.float32) * (np.clip(1 - np.arange(rf.height) / (rf.height * .5), 0, 1) * .35)[:, None]
    rf.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.paste(rf, (int((CX + 40 - ew / 2) * K), int((PLAT_Y + 60) * K)), rf)
    img.paste(ex, (int((CX + 40 - ew / 2) * K), int((PLAT_Y + 56 - eh) * K)), ex)
    st = dict(lpose=POSES['up'], rpose=POSES['raise1'], out_lpose=True, out_rpose=True, mouth=1.0, eyes='wide', brows='up',
              look=1, sweat=.3)
    person(scaled(img, 290, 2560, 1.6), 0, 0, BUYER, st)               # the buyer's shocked face, big, lower left
    img = img.resize((W, H), Image.LANCZOS).convert('RGBA')
    img.alpha_composite(vignette(1.4))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    y = 120
    for i, ln in enumerate(S.HEADLINE):
        size = 200
        while font(size).getlength(ln) > 1000: size -= 4
        f = font(size)
        bb = f.getbbox(ln, anchor='mt', stroke_width=14)
        d.rounded_rectangle((W / 2 + bb[0] - 18, y + bb[1] - 10, W / 2 + bb[2] + 18, y + bb[3] + 10), 22,
                            fill=(12, 12, 16, 220) if i == 0 else B['accent'] + (255,))
        d.text((W / 2, y), ln, font=f, fill=(255, 255, 255) if i == 0 else TAG, anchor='mt', stroke_width=12, stroke_fill=(10, 10, 14))
        y += bb[3] - bb[1] + 34
    lay = lay.rotate(3, resample=Image.BICUBIC, center=(W / 2, 300))
    img.alpha_composite(lay)
    img.convert('RGB').save(out)

def _init(voice): load_mouth(voice)

if __name__ == '__main__':
    mode = sys.argv[2]
    if mode == 'still':
        load_mouth(sys.argv[5])
        Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[3]) * FPS))).save(sys.argv[4])
    elif mode == 'meta':
        json.dump(dict(captions=caption_boxes(), final=final_boxes(), onscreen=ONSCREEN, duration=DUR, size=[W, H], fps=FPS,
                       scenes=SCENES), open(sys.argv[3], 'w'), indent=1)
    elif mode == 'thumb':
        thumbnail(sys.argv[3])
    elif mode == 'video':
        voice, out = sys.argv[3], sys.argv[4]
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
