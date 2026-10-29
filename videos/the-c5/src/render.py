"""Renders 'The C5': a £399 mail-order electric trike, launched January 1985 and stopped three months later.

Template: videos/the-land-rover-from-the-sand (ac-idle shot structure on shared/episode.py). Word times come from
align.py -> words.json (the voiceover is the timing spine). Speech runs 0-17.1 s; the read has no 'Follow' line,
so the end card shows it. No top speed or sales total is shown (the sources give neither). Vehicles are generic pixel
redraws with no badges or lettering.
Shots:
  1 arrive    0.00  a low-slung white trike rolls into the garage; JANUARY 1985; 'The C5.'
  2 price     3.60  ELECTRIC bolt, a mail-order parcel drops, the £399 price tag pops; pixel photo
  3 rain      7.40  night traffic in the rain: a rider low on the trike under passing lorries; NO WEATHER PROTECTION
  4 stopped  10.80  a sales graph flatlines; the production sign flips to STOPPED; MARCH and ~3 MONTHS
  5 timing   14.80  IDEA (tick) vs TIMING (cross) either side of the trike
  6 teaser   16.85  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title, street, ROAD_Y, ROAD, headlights
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid, text_width

WORDS = kit.load_words(HERE)
DUR, END_T = 18.75, 17.15


# ------------------------------------------------------------------ episode sprites
def ptext(s, col, ol=False):
    g = Grid(text_width(s) + 2, 9); g.text(1, 1, s, col if isinstance(col, str) else '#%02x%02x%02x' % col)
    return g.image(outline=ol)


def _wheel(d, cx, cy, r, spin, rim=(60, 63, 74)):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 27, 32))
    rr = r * 0.62
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    for k in range(3):
        a = math.radians(k * 120 + spin)
        d.line([(cx, cy), (cx + rr * math.cos(a), cy + rr * math.sin(a))], fill=(140, 146, 160))
    d.point((cx, cy), fill=(230, 232, 238))


@lru_cache(None)
def trike(spin=0, rider=False, wet=False):
    """Low recumbent electric trike (72x30 grid), nose right: white wedge shell over a black chassis tub, small
    front wheel, large rear wheel, tiny screen, under-seat handlebar. `rider` seats a figure in a rain jacket."""
    img = Image.new('RGBA', (72, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if rider:                                                                           # rider sits reclined, head up high
        d.rectangle((22, 10, 32, 21), fill=(230, 180, 40) if wet else (60, 110, 190))   # jacket
        d.line([(23, 11), (31, 11)], fill=(255, 220, 110) if wet else (110, 160, 230))
        d.rectangle((30, 16, 44, 19), fill=(40, 46, 70)); d.rectangle((44, 16, 46, 22), fill=(30, 30, 36))       # legs to pedals
        d.ellipse((22, 2, 30, 10), fill=(232, 186, 150))
        d.pieslice((21, 1, 31, 11), 180, 360, fill=(230, 180, 40) if wet else (40, 40, 50))                    # hood or hair
        d.point((28, 6), fill=(26, 26, 46))
    shell = [(4, 20), (10, 16), (28, 14), (34, 17), (52, 20), (66, 23), (68, 26), (4, 26)]
    d.polygon(shell, fill=(236, 238, 242)); d.line(shell[:-2], fill=(255, 255, 255))
    d.rectangle((4, 24, 68, 27), fill=(40, 42, 50))                                      # black chassis tub
    d.line([(10, 22), (60, 23)], fill=(190, 194, 204))
    d.polygon([(33, 17), (36, 11), (38, 11), (37, 17)], fill=(150, 180, 210))            # tiny screen
    d.rectangle((62, 21, 65, 23), fill=(255, 244, 200))                                  # lamp
    d.rectangle((4, 20, 6, 22), fill=(214, 48, 58))
    d.rectangle((36, 26, 40, 30), fill=(30, 30, 36))                                     # under-seat bar
    _wheel(d, 12, 27, 6.5, spin); _wheel(d, 62, 29, 4.2, spin * 1.5)
    if wet:
        for x in range(8, 66, 7): d.point((x, 18 + (x % 3)), fill=(170, 200, 240))
    return outline(img)


@lru_cache(None)
def lorry(col=(150, 60, 50)):
    """Generic box lorry (110x60 grid), nose right: tall box body, cab with window, big wheels."""
    img = Image.new('RGBA', (110, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 4, 78, 46), fill=(200, 204, 214)); d.line([(0, 4), (78, 4)], fill=(236, 240, 246))
    for x in range(8, 78, 12): d.line([(x, 6), (x, 44)], fill=(176, 180, 190))
    d.polygon([(80, 14), (98, 14), (106, 28), (106, 48), (80, 48)], fill=col)
    d.polygon([(84, 17), (96, 17), (102, 28), (84, 28)], fill=(120, 150, 180))
    d.rectangle((102, 34, 108, 38), fill=(255, 244, 200)); d.rectangle((0, 46, 108, 50), fill=(40, 42, 50))
    for cx in (16, 34, 92): d.ellipse((cx - 9, 42, cx + 9, 60), fill=(26, 27, 32)); d.ellipse((cx - 4, 47, cx + 4, 55), fill=(150, 156, 168))
    return outline(img)


@lru_cache(None)
def parcel():
    img = Image.new('RGBA', (34, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 4, 33, 25), fill=(196, 150, 96)); d.polygon([(0, 4), (6, 0), (39, 0), (33, 4)], fill=(220, 176, 120))
    d.rectangle((15, 0, 18, 25), fill=(236, 220, 180)); d.rectangle((3, 9, 12, 15), fill=(250, 250, 246))
    for y in (11, 13): d.line([(4, y), (11, y)], fill=(120, 124, 134))
    d.rectangle((24, 8, 30, 14), fill=(214, 48, 58))                                    # stamp
    return outline(img)


@lru_cache(None)
def price_tag():
    img = Image.new('RGBA', (52, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(0, 12), (10, 0), (51, 0), (51, 23), (10, 23)], fill=(255, 236, 120)); d.line([(10, 1), (50, 1)], fill=(255, 250, 200))
    d.ellipse((6, 9, 11, 14), fill=(26, 26, 46))
    t = ptext('£399', (26, 26, 46)); t = t.resize((t.width * 2 // 2, t.height), Image.NEAREST); img.alpha_composite(t, (16, 7))
    return outline(img)


@lru_cache(None)
def battery(level=1.0):
    img = Image.new('RGBA', (20, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((6, 0, 13, 3), fill=(150, 156, 168)); d.rectangle((0, 3, 19, 29), fill=(60, 64, 76))
    h = int(23 * level)
    if h > 0: d.rectangle((3, 27 - h, 16, 26), fill=(90, 220, 120))
    d.polygon([(11, 7), (6, 17), (10, 17), (8, 25), (14, 14), (10, 14), (13, 7)], fill=(255, 236, 90))
    return outline(img)


def graph(u):
    """Sales chart (70x44): axes, a line that rises then slides to a flat trickle, drawn up to u (0..1)."""
    img = Image.new('RGBA', (70, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 69, 45), fill=(250, 250, 246)); d.rectangle((0, 0, 69, 45), outline=(26, 26, 46))
    for y in range(8, 40, 8): d.line([(6, y), (66, y)], fill=(220, 222, 230))
    d.line([(6, 4), (6, 40)], fill=(26, 26, 46)); d.line([(6, 40), (66, 40)], fill=(26, 26, 46))
    pts = [(6, 34), (12, 12), (18, 18), (26, 28), (34, 34), (42, 37), (50, 38), (58, 38), (66, 38)]
    n = u * (len(pts) - 1); k = int(n)
    line = pts[:k + 1] + ([(lerp(pts[k][0], pts[k + 1][0], n - k), lerp(pts[k][1], pts[k + 1][1], n - k))] if k + 1 < len(pts) else [])
    if len(line) > 1: d.line(line, fill=(214, 48, 58), width=2)
    return outline(img)


@lru_cache(None)
def prod_sign(flip=0):
    """Hanging factory sign (60x22) flipping over: flip 0 shows IN PRODUCTION (green), 1 shows STOPPED (red)."""
    img = Image.new('RGBA', (72, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    on = flip < 0.5
    d.rectangle((0, 0, 71, 21), fill=(60, 200, 90) if on else (214, 48, 58)); d.rectangle((2, 2, 69, 19), outline=(255, 255, 255))
    for i, w in enumerate(('IN PRODUCTION' if on else 'STOPPED').split()):
        t = ptext(w, (255, 255, 255))
        img.alpha_composite(t, (36 - t.width // 2, (7 if on else 7) + (i * 6 - 3 if on else 0)))
    img = outline(img)
    sq = abs(math.cos(math.pi * flip))
    return img.resize((img.width, max(1, int(22 * sq))), Image.NEAREST)


@lru_cache(None)
def clock():
    img = Image.new('RGBA', (30, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 29, 29), fill=(250, 250, 246)); d.ellipse((0, 0, 29, 29), outline=(26, 26, 46))
    for k in range(12):
        a = math.radians(k * 30); d.point((15 + 12 * math.cos(a), 15 + 12 * math.sin(a)), fill=(26, 26, 46))
    d.line([(15, 15), (15, 6)], fill=(26, 26, 46), width=2); d.line([(15, 15), (21, 18)], fill=(214, 48, 58))
    return outline(img)


@lru_cache(None)
def bulb():
    img = Image.new('RGBA', (16, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((1, 0, 14, 13), fill=(255, 236, 120)); d.ellipse((4, 3, 7, 6), fill=(255, 255, 240))
    d.rectangle((5, 13, 10, 19), fill=(170, 176, 188)); d.line([(5, 15), (10, 15)], fill=(120, 124, 134)); d.line([(5, 17), (10, 17)], fill=(120, 124, 134))
    return outline(img)


# ================================================================== shot 1: the C5 rolls in
CX1 = 540
def trike1_x(t): return lerp(-400, CX1, oc(prog(t, 0.0, 1.2)))
P1 = Presenter([
    (1.4, dict(path=Track([(1.4, (1300, 300)), (1.8, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (1.8, dict(ground=GROUND, squash=True, arms='point', point=(CX1, GROUND - 120), look=(CX1, GROUND - 120), expr='smile', face=None)),
    (2.99, dict(arms='present', expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (420, 1060, 1.3)), (0.0, (420, 1060, 1.3)), (1.2, (540, 1040, 1.2), 'io'), (2.4, (560, 980, 1.1), 'io'), (3.6, (560, 980, 1.14))],
              kicks=[(0.61, 0.08, 760, 760), (1.2, 0.12, CX1, 1100), (2.03, 0.08, 540, 620), (2.99, 0.16, CX1, 1100)], shakes=[(1.2, 0.2, 8)])


def shot_arrive(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = trike1_x(t)
    fx.contact_shadow(fg, x, GROUND, 520, s=S, alpha=130)
    sr, sv = wob(t, (1.2, 2.99), 0.06)
    blit(fg, up(trike(int(x * 0.9) % 360 // 15 * 15), 8), x, GROUND, sr, sv)
    fx.dust(fg, t, 1.2, x, GROUND - 10, n=10, seed=1)
    if t >= 0.61:
        k = popin(t, 0.61, 0.25) * popout(t, 2.6)
        blit(fg, fx.big('tag', 'JANUARY 1985', '#fff6e0', '#1a1a2e', s=7), 540, 820, k, k, 4, anchor='center')
    dg.label(fg, t, 2.03, 'SIR CLIVE SINCLAIR', (CX1, GROUND - 240), (520, 900), '#ffffff', '#1a1a2e', '#d6d9e2', s=6, t1=2.9)
    if t >= 2.99:
        fx.rays(fg, t, 2.99, x, GROUND - 120, GLOW, life=0.7, r=460)
        fx.burst(fg, t, 2.99, x, GROUND - 120, GLOW, n=14, seed=2); fx.sparkles(fg, t, x, GROUND - 120, 600, 200, n=7, seed=3)
        k = popin(t, 2.99, 0.25)
        blit(fg, fx.big('badge', 'LAUNCHED', '#ffd23f', '#1a1a2e', '#e8b923', s=8), 540, 860, k, k, -3, anchor='center')
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.4, 'The', WHITE, 440, 110, -3)
    title(cv, t, 0.25, 2.4, 'C5.', YEL, 590, 180, 3)


# ================================================================== shot 2: electric, mail order, £399
TX = 540
CAM2 = Camera(W, H, [(3.6, (540, 960, 1.14)), (4.4, (380, 900, 1.22), 'io'), (5.56, (720, 900, 1.22), 'io'), (6.1, (540, 880, 1.16), 'io'), (7.4, (540, 880, 1.2))],
              kicks=[(4.4, 0.12, 300, 640), (5.56, 0.12, 780, 700), (6.1, 0.18, 540, 560)], shakes=[(6.1, 0.25, 10)])


def shot_price(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, TX, GROUND, 520, s=S, alpha=130)
    blit(fg, up(trike(), 7), TX, GROUND)
    if t >= 4.03:
        k = popin(t, 4.03, 0.25) * popout(t, 5.3)
        blit(fg, fx.big('tag', 'SMALL', '#fff6e0', '#1a1a2e', s=7), TX + 260, GROUND - 260, k, k, 6, anchor='center')
    if t >= 4.4:
        k = popin(t, 4.4, 0.25)
        blit(fg, up(battery(round(clamp((t - 4.4) / 0.8), 2)), 10), 300, 760, k, k, 4 * math.sin(t * 5), anchor='center')
        blit(fg, fx.big('label', 'ELECTRIC', '#7fe3a0', s=6), 300, 940, k, k, anchor='center')
        fx.burst(fg, t, 4.4, 300, 760, (60, 200, 90), n=12, seed=10)
    if t >= 5.4:                                                                        # parcel drops in
        y = lerp(-200, 760, oc(prog(t, 5.4, 0.35)))
        blit(fg, up(parcel(), 9), 780, y, 1, 1, -6, anchor='center')
        fx.dust(fg, t, 5.75, 780, 860, n=8, seed=11, col=(196, 150, 96))
        if t >= 5.56: blit(fg, fx.big('label', 'MAIL ORDER', '#ffffff', s=6), 780, 940, 1, 1, anchor='center')
    if t >= 6.1:
        k = popin(t, 6.1, 0.3) * (1 + 0.04 * math.sin(t * 8))
        blit(fg, up(price_tag(), 11), 540, 520, k, k, -5 + 3 * math.sin(t * 4), anchor='center')
        fx.ring(fg, t, 6.1, 540, 520, (60, 200, 90), life=0.35, r1=420); fx.burst(fg, t, 6.1, 540, 520, GLOW, n=16, seed=12)
        fx.sparkles(fg, t, 540, 520, 700, 300, n=7, seed=13)
    GAR.reflect(img, fg)
    photo(fg, t, 6.6, 7.35, 'c5', 540, 1000, 600, 420, 3, 'THE REAL C5', focus=(0.5, 0.6), pix=4)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: exposed, in the rain
RX = 420
def scroll3(t): return (t - 7.4) * 260
def lorry_x(t, t0): return lerp(1700, -900, prog(t, t0, 1.6))
CAM3 = Camera(W, H, [(7.4, (480, 1000, 1.2)), (8.27, (420, 1060, 1.34), 'io'), (9.78, (520, 1000, 1.16), 'io'), (10.8, (520, 1000, 1.2))],
              kicks=[(7.69, 0.08, RX, ROAD_Y), (8.27, 0.14, RX, ROAD_Y - 60), (9.78, 0.12, 540, 600)], shakes=[(8.3, 0.4, 8), (9.4, 0.4, 8)])


def shot_rain(t):
    sc = scroll3(t)
    img = street(t, sc); fg = layer()
    dark = Image.new('RGBA', (W, H), (10, 14, 30, 90)); img.alpha_composite(dark)
    for t0, col in ((7.7, (150, 60, 50)), (8.9, (60, 90, 150))):                         # lorries towering past
        x = lorry_x(t, t0)
        if -900 < x < 1800:
            headlights(fg, x - 380, ROAD_Y - 70, flip=True)
            blit(fg, up(lorry(col), 7), x, ROAD_Y - 40, flip=True)
            fx.puff(fg, t, t - 0.1, x + 400, ROAD_Y - 90, seed=int(t * 10) % 30, life=0.5, size=0.7, drift=(300, -40), col=(160, 170, 190))
    bob = 3 * math.sin(t * 14)
    blit(fg, up(trike(int(sc) % 360 // 15 * 15, rider=True, wet=True), 6), RX, ROAD_Y + 70 + bob)
    d = ImageDraw.Draw(fg); r = fx.rng(int(t * 30))                                    # rain
    for _ in range(140):
        x, y = r.uniform(0, W + 200), r.uniform(0, H)
        d.line([(x, y), (x - 18, y + 54)], fill=(170, 200, 240, 150), width=3)
    for _ in range(10):
        x = r.uniform(0, W); d.ellipse((x - 14, ROAD_Y - 6, x + 14, ROAD_Y + 4), outline=(190, 210, 240, 200), width=3)
    if t >= 8.27:
        k = popin(t, 8.27, 0.25) * popout(t, 9.6)
        blit(fg, fx.big('tag', 'EXPOSED', '#fff6e0', '#d6303a', s=8), RX, 640, k, k, -5 + 3 * math.sin(t * 6), anchor='center')
    if t >= 9.78:
        k = popin(t, 9.78, 0.25)
        blit(fg, fx.big('badge', 'NO WEATHER PROTECTION', '#ffffff', '#d6303a', '#d6d9e2', s=7), 540, 600, k, k, 3, anchor='center')
        fx.burst(fg, t, 9.78, 540, 600, RED, n=12, seed=20)
    if t >= 10.37:
        k = popin(t, 10.37, 0.2); blit(fg, fx.big('xmark', s=10), RX + 260, ROAD_Y - 300, k, k, anchor='center')
    ROAD.reflect(img, fg)
    return finish(img, fg, CAM3, t, rim=False)


# ================================================================== shot 4: sales trickle, production stopped
GRX, SGX = 330, 720
P4 = Presenter([
    (10.75, dict(path=Track([(10.75, (1300, 400)), (11.15, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (11.15, dict(ground=GROUND, squash=True, arms='point', point=(GRX, 800), look=(GRX, 800), expr='sad', face=None)),
    (12.64, dict(arms='shock', point=None, look=(SGX, 520), expr='shock', squash=True)),
    (13.9, dict(arms='shrug', expr='sad')),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(10.8, (540, 900, 1.14)), (11.66, (400, 860, 1.26), 'io'), (12.64, (640, 760, 1.2), 'io'), (13.9, (540, 860, 1.12), 'io'), (14.8, (540, 860, 1.16))],
              kicks=[(10.89, 0.08, GRX, 800), (11.66, 0.12, GRX, 900), (12.64, 0.2, SGX, 520), (13.02, 0.1, 300, 1040), (13.9, 0.12, 540, 1100)],
              shakes=[(12.64, 0.3, 12)])


def shot_stopped(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 10.85, 0.3)
    blit(fg, up(graph(clamp((t - 10.95) / 1.0)), 9), GRX, 820, k, k, -3, anchor='center')
    blit(fg, fx.big('label', 'SALES', '#ffffff', s=6), GRX, 560, k, k, anchor='center')
    if t >= 11.66:
        kt = popin(t, 11.66, 0.25) * popout(t, 12.5)
        blit(fg, fx.big('tag', 'A TRICKLE', '#fff6e0', '#d6303a', s=7), GRX + 80, 1060, kt, kt, -4, anchor='center')
    d = ImageDraw.Draw(fg)
    for x in (SGX - 200, SGX + 200): d.line([(x, 220), (x, 420)], fill=(150, 156, 168, 255), width=6)
    fl = io(prog(t, 12.5, 0.3))
    blit(fg, up(prod_sign(round(fl * 12) / 12), 7), SGX, 520, 1, 1, 0, anchor='center')
    if t >= 12.64:
        fx.burst(fg, t, 12.64, SGX, 520, RED, n=14, seed=30); fx.ring(fg, t, 12.64, SGX, 520, RED, life=0.3, r1=380)
    if t >= 13.02:
        kk = popin(t, 13.02, 0.25)
        blit(fg, fx.big('badge', 'MARCH 1985', '#ffffff', '#d6303a', '#d6d9e2', s=7), 600, 720, kk, kk, 4, anchor='center')
    if t >= 13.9:
        kk = popin(t, 13.9, 0.25)
        blit(fg, fx.big('tag', 'ABOUT 3 MONTHS IN', '#fff6e0', '#1a1a2e', s=5), 540, 1080, kk, kk, -3, anchor='center')
        fx.burst(fg, t, 13.9, 540, 1080, GLOW, n=10, seed=31)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: idea right, timing wrong
P5 = Presenter([
    (14.75, dict(path=Track([(14.75, (540, -200)), (15.15, (540, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (15.15, dict(ground=GROUND, squash=True, arms='point', point=(250, 640), look=(250, 640), expr='smile', face=None)),
    (16.37, dict(point=(830, 640), look=(830, 640), expr='sad')),
    (16.82, dict(arms='shrug', point=None, look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(14.8, (540, 900, 1.12)), (15.8, (480, 860, 1.1), 'io'), (16.82, (600, 860, 1.1), 'io'), (16.85, (600, 860, 1.1))],
              kicks=[(15.38, 0.1, 250, 640), (15.8, 0.12, 250, 640), (16.37, 0.1, 830, 640), (16.82, 0.14, 830, 640)])


def shot_timing(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 760, GROUND, 460, s=S, alpha=120)
    blit(fg, up(trike(), 6), 760, GROUND)
    if t >= 15.38:
        k = popin(t, 15.38, 0.25)
        fx.rays(fg, t, 15.38, 250, 600, GLOW, life=0.9, r=320)
        blit(fg, up(bulb(), 10), 250, 680, k, k, 4 * math.sin(t * 4))
        blit(fg, fx.big('label', 'IDEA', '#ffffff', s=7), 250, 780, k, k, anchor='center')
    if t >= 15.8:
        k = popin(t, 15.8, 0.22); blit(fg, fx.big('check', s=10), 250, 380, k, k, anchor='center')
        fx.ring(fg, t, 15.8, 250, 350, (60, 200, 90), life=0.3, r1=220)
    if t >= 16.37:
        k = popin(t, 16.37, 0.25)
        blit(fg, up(clock(), 9), 830, 650, k, k, -4 + 4 * math.sin(t * 9), anchor='center')
        blit(fg, fx.big('label', 'TIMING', '#ffffff', s=7), 830, 780, k, k, anchor='center')
    if t >= 16.82:
        k = popin(t, 16.82, 0.2); blit(fg, fx.big('xmark', s=10), 830, 380, k, k, anchor='center')
        fx.burst(fg, t, 16.82, 830, 400, RED, n=12, seed=40)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 14.85, 15.35, 'c5b', 330, 640, 520, 380, 3, 'A SURVIVING C5', focus=(0.5, 0.6), pix=4)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(16.85, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_arrive), (3.6, shot_price), (7.4, shot_rain), (10.8, shot_stopped), (14.8, shot_timing), (16.85, shot_teaser)]
TRANS = {1: (3.6, 3.8, 'whip', dict(dx=1)), 2: (7.4, 7.6, 'whip', dict(dx=-1)), 3: (10.8, 11.0, 'push', None),
         4: (14.8, 15.0, 'whip', dict(dx=0, dy=1)), 5: (16.85, 17.05, 'whip', dict(dx=1))}
KEYCOL = {'1985': YEL, 'sinclair': YEL, 'c5': YEL, 'electric': GRN, 'mail': YEL, '£399': GRN, 'exposed': RED, 'protection': RED,
          'weather': RED, 'trickle': RED, 'production': RED, 'stopped': RED, 'march': YEL, 'months': YEL, 'right': GRN, 'wrong': RED}
CUES = [
    (0.0, 'vroom', 0.3), (0.05, 'pop', 0.5), (0.25, 'pop', 0.7), (0.61, 'pop', 0.6), (1.2, 'thump', 0.5), (1.8, 'thump', 0.4),
    (2.03, 'pop', 0.5), (2.99, 'ding', 0.8), (3.01, 'sparkle', 0.7),
    (4.03, 'pop', 0.5), (4.4, 'click', 0.7), (4.42, 'sparkle', 0.5), (5.4, 'fall', 0.5), (5.75, 'thump', 0.6), (6.1, 'cha_ching', 0.9),
    (6.12, 'sparkle', 0.7), (6.6, 'pop', 0.6),
    (7.7, 'vroom', 0.7), (8.27, 'pop', 0.6), (8.9, 'vroom', 0.7), (9.78, 'stamp', 0.7), (10.37, 'buzzer', 0.5),
    (10.85, 'pop', 0.6), (11.66, 'slide_down', 0.6), (12.5, 'creak', 0.5), (12.64, 'stamp', 0.9), (12.66, 'buzzer', 0.4), (13.02, 'pop', 0.6),
    (13.9, 'pop', 0.6),
    (15.15, 'thump', 0.5), (15.38, 'ding', 0.6), (15.8, 'ding', 0.8), (16.37, 'click', 0.6), (16.82, 'buzzer', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
