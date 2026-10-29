"""Renders 'Why did cars grow fins?': Cadillac's 1948 tailfins, the P-38 story, the jet-age fin war.

Template: videos/tractors-vs-ferraris (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). Speech runs 0-17.9 s; the 'Follow' card holds to 18.7 s.
All cars are generic pixel cars; brand names are only spoken (and so appear in the transcript captions).
Shots:
  1 hook      0.00  a car sprouts fins on 'tailfins', rockets up, drops back down as the 1948 car; 1948 photo card
  2 p38       3.00  sky: a twin-tail fighter flies past on 'fighter planes'; its tail shape drops onto the car on 'P-38'
  3 fifties   6.50  calendar flips 1950-1959 while the fins grow; jets streak over on 'jets'; 1959 fin photo
  4 everyone  9.95  night street: four generic cars roll by, each sprouting fins on a brand name
  5 war      13.10  boardroom: two designers argue over a fin model; WAR? stamp on 'war'
  6 teaser   15.95  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, layer, finish, photo, title, headlights
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.car import car, wheel_deg
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid

WORDS = kit.load_words(HERE)
DUR, END_T = 18.7, 17.05


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def fin_car(col='red', h=0, wd=0, lights=False):
    """Shared side-view car with a tailfin of height h (grid px) swept back over the rear deck; tail lamp at its base."""
    c = car(col, wd, lights)
    pad = 18
    img = Image.new('RGBA', (c.width, c.height + pad), (0, 0, 0, 0))
    if h > 0:
        a = c.getchannel('A').load()
        def top(x): return next(y for y in range(c.height) if a[x, y] > 0)
        body, shade, hi, _ = kit_pal(col)
        y0, y1 = top(4) + pad + 1, top(20) + pad + 1
        f = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(f)
        tip = (1, y0 - h)
        d.polygon([(3, y0 + 2), tip, (4, y0 - h + 1), (22, y1 + 1), (22, y1 + 3)], fill=body)
        d.line([tip, (21, y1)], fill=hi)
        d.rectangle((2, y0 - 1, 3, y0 + 2), fill=(255, 60, 60))
        img.alpha_composite(outline(f))
    img.alpha_composite(c, (0, pad))
    return img


def kit_pal(col):
    from pixanim.car import PAL
    return PAL[col]


def draw_fcar(cv, col, x, s, h, y=GROUND, dist=0.0, lights=False, sx=1.06, sy=0.86, rot=0.0, flip=False):
    blit(cv, up(fin_car(col, int(round(h)), wheel_deg(dist, s) // 30 * 30, lights), s), x, y, sx, sy, rot, flip=flip)


@lru_cache(None)
def p38(prop=0):
    """Twin-boom fighter in plan view, nose right (64x58 grid): wings, central pod, two booms with twin tails."""
    img = Image.new('RGBA', (64, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    sv, sh, hi = (186, 192, 204), (132, 138, 152), (232, 236, 244)
    d.polygon([(30, 1), (38, 1), (40, 57), (30, 57)], fill=sv); d.line([(38, 2), (40, 56)], fill=sh)   # wing
    for y in (14, 40):                                                                                 # booms + engines
        d.rectangle((6, y, 48, y + 4), fill=sv); d.line([(6, y), (48, y)], fill=hi)
        d.rectangle((42, y - 1, 50, y + 5), fill=sh)
        d.rectangle((3, y - 4, 9, y + 8), fill=sv); d.line([(3, y - 4), (3, y + 8)], fill=(255, 210, 63))  # twin tail fins
        e = 3 + 2 * math.cos(math.radians(prop))
        d.ellipse((50, y + 2 - e, 53, y + 2 + e), fill=(60, 63, 71))                                     # spinning props
    d.rectangle((4, 16, 9, 42), fill=sh)                                                               # tailplane
    d.polygon([(24, 24), (52, 25), (58, 29), (52, 33), (24, 34)], fill=sv)                             # central pod
    d.line([(26, 25), (52, 26)], fill=hi); d.rectangle((40, 27, 46, 31), fill=(120, 170, 220))
    d.ellipse((32, 6, 36, 10), fill=(61, 127, 214)); d.point((34, 8), fill=(255, 255, 255))           # wing stars
    d.ellipse((32, 48, 36, 52), fill=(61, 127, 214)); d.point((34, 50), fill=(255, 255, 255))
    return outline(img)


@lru_cache(None)
def jet():
    """Small 1950s swept-wing jet in side/plan mix (30x14), nose right."""
    img = Image.new('RGBA', (30, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(0, 6), (24, 5), (29, 7), (24, 9), (0, 8)], fill=(200, 206, 216))
    d.polygon([(8, 7), (16, 7), (6, 13)], fill=(150, 156, 168)); d.polygon([(8, 6), (16, 6), (6, 0)], fill=(176, 182, 192))
    d.polygon([(0, 6), (4, 6), (0, 1)], fill=(150, 156, 168))
    return outline(img)


@lru_cache(None)
def calendar(year):
    g = Grid(30, 30)
    g.rect(0, 3, 29, 29, '#f8f6ee'); g.rect(0, 3, 29, 9, '#d6303a')
    for x in (6, 14, 22): g.rect(x, 0, x + 1, 5, '#3c3f47')
    g.text(4, 15, str(year), '#1a1a2e')
    for x in range(3, 27, 4): g.px(x, 26, '#c8ccd4')
    return g.image()


@lru_cache(None)
def designer(suit, pose=0, face=1):
    """Generic 1950s designer (20x44): suit, tie, hair; pose 0 arms down, 1 one arm jabbing, 2 both arms up."""
    img = Image.new('RGBA', (20, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    skin, hair = (240, 196, 160), (60, 44, 36)
    d.rectangle((6, 1, 13, 9), fill=skin); d.rectangle((6, 0, 13, 2), fill=hair); d.rectangle((6, 0, 7, 5), fill=hair)
    d.point((11, 5), fill=(26, 26, 46)); d.line([(10, 8), (12, 8)], fill=(150, 60, 60))
    d.rectangle((5, 10, 14, 27), fill=suit); d.polygon([(9, 10), (10, 10), (11, 16), (9, 18), (8, 16)], fill=(214, 48, 58))
    d.rectangle((6, 28, 9, 41), fill=(40, 42, 50)); d.rectangle((10, 28, 13, 41), fill=(40, 42, 50))
    d.rectangle((5, 41, 9, 43), fill=(20, 20, 26)); d.rectangle((10, 41, 15, 43), fill=(20, 20, 26))
    if pose == 0: d.rectangle((14, 11, 16, 24), fill=suit)
    if pose == 1: d.line([(14, 12), (19, 6)], fill=suit, width=3); d.rectangle((17, 3, 19, 5), fill=skin)
    if pose == 2:
        d.line([(14, 12), (18, 2)], fill=suit, width=3); d.line([(5, 12), (1, 2)], fill=suit, width=3)
        d.rectangle((17, 0, 19, 2), fill=skin); d.rectangle((0, 0, 2, 2), fill=skin)
    else:
        d.rectangle((3, 11, 5, 24), fill=suit)
    img = outline(img)
    return img if face > 0 else img.transpose(Image.FLIP_LEFT_RIGHT)


@lru_cache(None)
def sky():
    """Daytime sky with an airfield horizon (120x214 grid at 9 px)."""
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    for y in range(214):
        u = min(1, y / 120)
        d.line([(0, y), (119, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip((40, 92, 176), (170, 210, 240))))
    d.rectangle((0, 118, 119, 131), fill=(110, 150, 96)); d.rectangle((0, 118, 119, 119), fill=(140, 176, 120))
    d.rectangle((0, 132, 119, 213), fill=(70, 72, 80))
    for x in range(0, 120, 12): d.rectangle((x, 160, x + 6, 161), fill=(230, 230, 236))
    for x, y, w in ((10, 112, 12), (60, 114, 20), (96, 111, 10)): d.rectangle((x, y, x + w, 117), fill=(150, 164, 176))   # hangars
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


@lru_cache(None)
def cloud(k):
    g = Image.new('RGBA', (34, 12), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for x, y, r in ((8, 7, 5), (16, 5, 6), (25, 7, 5))[: 2 + k % 2]: d.ellipse((x - r, y - r, x + r, y + r), fill=(250, 252, 255))
    d.rectangle((3, 7, 30, 11), fill=(250, 252, 255)); d.rectangle((3, 10, 30, 11), fill=(214, 224, 238))
    return up(g, S)


@lru_cache(None)
def boardroom():
    """Wood-panelled 1950s boardroom wall, window and long table (120x214 grid at 9 px)."""
    img = Image.new('RGB', (120, 214), (70, 46, 36)); d = ImageDraw.Draw(img)
    for x in range(0, 120, 10): d.line([(x, 0), (x, 131)], fill=(56, 36, 28))
    d.rectangle((0, 60, 119, 61), fill=(96, 66, 50))
    d.rectangle((70, 20, 108, 56), fill=(26, 30, 52)); d.rectangle((70, 20, 108, 21), fill=(130, 100, 80))
    for x, y in ((76, 30), (86, 40), (98, 28), (92, 50), (80, 46)): d.point((x, y), fill=(255, 230, 150))
    d.line([(89, 20), (89, 56)], fill=(130, 100, 80)); d.line([(70, 38), (108, 38)], fill=(130, 100, 80))
    d.rectangle((12, 24, 40, 50), fill=(232, 228, 214)); d.line([(15, 45), (22, 38), (28, 41), (37, 28)], fill=(214, 48, 58))   # sales chart
    d.rectangle((0, 132, 119, 213), fill=(46, 30, 26))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


# ================================================================== shot 1: hook, the car sprouts fins and rockets up
CX1 = 620
def fin1(t): return 9 * oc(prog(t, 0.8, 0.3))
def lift1(t):
    if t < 0.95: return 0.0
    if t < 1.73: return -2400 * ic(prog(t, 0.95, 0.4)) if t < 1.45 else -2400 * (1 - oc(prog(t, 1.45, 0.28)))
    return 0.0
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-200, 300)), (0.2, (-200, 300)), (0.6, (140, GROUND), 'ic')]), size=7, legs='auto', arms='fly',
                expr='wow', ground=None, face=1)),
    (0.6, dict(ground=GROUND, squash=True, arms='point', point=(CX1 - 250, 900), look=(CX1, 900), expr='grin', face=None)),
    (0.95, dict(arms='shock', expr='shock', look=(CX1, 300), point=None, squash=True)),
    (1.75, dict(arms='present', look=(CX1, 1000), expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (600, 1000, 1.35)), (0.0, (600, 1000, 1.35)), (0.95, (560, 900, 1.1), 'io'), (1.73, (560, 920, 1.15), 'io'),
                     (3.0, (560, 880, 1.22))],
              kicks=[(0.0, 0.1, 600, 1000), (0.8, 0.12, CX1 - 260, 950), (1.73, 0.16, CX1, 1000), (2.6, 0.06, 540, 560)],
              shakes=[(0.95, 0.4, 10), (1.73, 0.3, 16)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    ly = lift1(t)
    fx.contact_shadow(fg, CX1, GROUND, 640 * (1 + ly / 3000), s=S, alpha=140)
    if 0.95 <= t < 1.73:                                                           # rocket flames under the fins
        for k in range(3):
            fl = 120 + 60 * math.sin(t * 60 + k)
            d = ImageDraw.Draw(fg); bx = CX1 - 250 + k * 30
            d.polygon([(bx - 30, GROUND + ly - 60), (bx + 30, GROUND + ly - 60), (bx, GROUND + ly + fl)], fill=(255, 160 + 30 * k, 40, 230))
        for k in range(8):
            fx.puff(fg, t, 0.95 + k * 0.08, CX1 - 220, GROUND - 40, seed=10 + k, life=0.8, size=1.1, drift=(-200 + 60 * k, -80), col=(200, 202, 210))
    sr, sv = wob(t, (0.8, 1.73), 0.08)
    draw_fcar(fg, 'red', CX1, 7, fin1(t), y=GROUND + ly, sx=1.06 * sr, sy=0.86 * sv)
    for k, tx in enumerate((CX1 - 300, CX1 - 270)):
        fx.burst(fg, t, 0.8, tx, GROUND - 330, GLOW, n=10, r0=40, r1=220, seed=20 + k)
    fx.dust(fg, t, 1.73, CX1, GROUND - 10, n=16, seed=43)
    fx.ring(fg, t, 1.73, CX1, GROUND - 200, (90, 220, 120), life=0.4, r1=500)
    if t >= 1.73:
        k = popin(t, 1.73, 0.25) * popout(t, 2.55)
        blit(fg, fx.big('badge', '1948', '#7fe3a0', '#1a1a2e', '#3cc85a', s=12), CX1 + 120, 700, k, k, -6 + 3 * math.sin(t * 6), anchor='center')
        fx.sparkles(fg, t, CX1, 700, 500, 220, n=8, seed=11)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 2.6, 2.95, 'cadillac_1948', 560, 560, 600, 460, -3, 'A 1948 MODEL', focus=(0.5, 0.55), zoom=0.1)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.7, 'Why did cars grow fins?', YEL, 470, 96, -3)
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 470, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: the fighter-plane story (sky)
CAR2 = 600
def plane_x(t):
    if t < 4.6: return lerp(-500, 560, oc(prog(t, 3.75, 0.85)))
    return 560 + 900 * ic(prog(t, 6.0, 0.5))
def fin2(t): return 9 + 5 * oc(prog(t, 5.88, 0.3))
P2 = Presenter([
    (2.95, dict(path=Track([(2.95, (1300, 300)), (3.35, (840, 1000), 'oc'), (6.6, (860, 980))]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (3.99, dict(arms='point', point=(560, 520), look=(560, 520), expr='wow')),
    (5.22, dict(arms='point', point=(CAR2 - 250, 1000), look=(CAR2 - 250, 1000), expr='grin')),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(3.0, (540, 900, 1.12)), (3.99, (540, 760, 1.18), 'io'), (5.0, (420, 640, 1.35), 'io'), (5.6, (520, 860, 1.15), 'io'),
                     (6.5, (520, 900, 1.2))],
              kicks=[(3.99, 0.1, 560, 520), (5.22, 0.1, 300, 600), (5.88, 0.16, CAR2 - 250, 1000)], shakes=[(4.0, 0.4, 8), (5.88, 0.25, 12)])


def shot_p38(t):
    img = sky().copy()
    for k in range(4):
        blit(img, cloud(k), (k * 330 + 160 - t * (40 + 25 * k)) % 1500 - 200, 260 + 140 * k)
    fg = layer()
    fx.contact_shadow(fg, CAR2, GROUND, 640, s=S, alpha=120)
    sr, sv = wob(t, (5.88,), 0.1)
    draw_fcar(fg, 'red', CAR2, 7, fin2(t), sx=1.06 * sr, sy=0.86 * sv)
    px = plane_x(t)
    if 3.75 <= t:
        fx.speed_lines(fg, 0.4, int(t * 10) % 5, col=(230, 236, 246)) if t < 4.6 else None
        blit(fg, up(p38(int(t * 2000) % 360), 9), px, 760, 1, 1, 4 * math.sin(t * 3))
    if 4.0 <= t < 4.95: fx.stamp_at(fg, t, 4.05, 'REPORTEDLY', 470, 360, rot=-6, s=8)
    dg.label(fg, t, 5.0, 'TWIN TAIL', (px - 250, 560), (300, 330), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    if 5.22 <= t < 5.95:                                                          # the tail shape drops onto the car
        u = io(prog(t, 5.22, 0.66))
        gx, gy = lerp(px - 250, CAR2 - 260, u), lerp(560, GROUND - 330, u)
        g = Image.new('RGBA', (14, 16), (0, 0, 0, 0)); ImageDraw.Draw(g).polygon([(1, 15), (2, 0), (5, 1), (13, 15)], fill=(255, 210, 63, 230))
        blit(fg, up(g, 9), gx, gy, 1, 1, 0, anchor='center')
        fx.sparkles(fg, t * 2, gx, gy, 200, 200, n=5, seed=12)
    fx.burst(fg, t, 5.88, CAR2 - 260, GROUND - 330, GLOW, seed=13)
    fx.ring(fg, t, 5.88, CAR2 - 260, GROUND - 330, (255, 255, 255), life=0.3, r1=260)
    P2.draw(fg, t)
    photo(fg, t, 6.0, 6.45, 'p38', 560, 520, 600, 420, 3, 'THE TWIN-TAIL P-38 FIGHTER', focus=(0.5, 0.5), zoom=0.05)
    return finish(img, fg, CAM2, t, rim=False)


# ================================================================== shot 3: the fifties, fins grow
CAR3 = 660
YEARS = [(6.77, 1950), (7.3, 1952), (7.9, 1954), (8.42, 1956), (8.9, 1957), (9.25, 1958), (9.57, 1959)]
def year3(t): return max([y for ts, y in YEARS if t >= ts] or [1950])
def fin3(t): return 8 + 14 * clamp((year3(t) - 1950) / 9) + 2 * oc(prog(t, 8.42, 0.2))
P3 = Presenter([
    (6.45, dict(path=Track([(6.45, (-200, 500)), (6.85, (130, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (6.85, dict(ground=GROUND, squash=True, arms='present', look=(CAR3 - 250, 900), expr='smile', face=None)),
    (7.99, dict(arms='cheer1', expr='wow', squash=True)),
    (9.25, dict(arms='point', point=(700, 330), look=(700, 330), expr='grin')),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(6.5, (560, 900, 1.15)), (7.9, (520, 860, 1.28), 'io'), (8.9, (520, 820, 1.3)), (9.25, (560, 760, 1.12), 'io'),
                     (10.0, (560, 760, 1.15))],
              kicks=[(6.77, 0.08, 760, 560), (7.99, 0.14, CAR3 - 260, 900), (8.42, 0.14, CAR3 - 260, 880), (9.25, 0.1, 600, 330)],
              shakes=[(8.42, 0.25, 10)])


def shot_fifties(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR3, GROUND, 640, s=S, alpha=140)
    flips = [ts for ts, _ in YEARS if t >= ts]
    sr, sv = wob(t, tuple(flips[-1:]) or (0,), 0.05)
    draw_fcar(fg, 'blue', CAR3, 7, fin3(t), sx=1.06 * sr, sy=0.86 * sv)
    for ts, _ in YEARS: fx.burst(fg, t, ts, CAR3 - 290, GROUND - 400, GLOW, n=8, r0=40, r1=180, seed=int(ts * 10))
    kc = popin(t, 6.6, 0.3)
    if kc > 0:
        f = prog(t, flips[-1], 0.12) if flips else 1                       # quick page flip
        blit(fg, up(calendar(year3(t)), 9), 690, 600, kc, kc * (0.4 + 0.6 * f), -4, anchor='center')
    dg.label(fg, t, 7.99, 'BIGGER', (CAR3 - 290, GROUND - 420), (230, 640), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    dg.label(fg, t, 8.42, 'SHARPER', (CAR3 - 300, GROUND - 480), (430, 470), '#ff8a8a', '#1a1a2e', '#e0303a', s=8)
    if t >= 9.2:
        for k in range(3):
            u = prog(t, 9.2 + 0.12 * k, 0.6)
            if 0 < u < 1:
                blit(fg, up(jet(), 8), lerp(-200, 1300, u), 300 + 90 * k, 1, 1, -8)
                fx.speed_lines(fg, 0.3, k, col=(220, 224, 232))
    fx.sparkles(fg, t, CAR3 - 260, GROUND - 400, 300, 260, n=6, seed=14)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 8.9, 9.9, 'fin_1959', 760, 1000, 420, 360, 5, 'BY 1959', focus=(0.5, 0.45), zoom=0.1)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: everyone copies (night street)
BRANDS = [(10.46, 'blue', 180), (10.88, 'silver', 540), (11.33, 'yellow', 900), (12.01, 'black', 1260)]
def scroll4(t): return 520 * (t - 9.95)
def x4(t, i):
    """Car i is centred as its brand is spoken: the convoy slides left one slot per name."""
    ts = [9.95] + [tb for tb, _, _ in BRANDS] + [13.1]
    k = next((j for j in range(len(ts) - 1) if t < ts[j + 1]), len(ts) - 2)
    off = [-0.7, 0, 1, 2, 3, 3.5][k] + ([-0.7, 0, 1, 2, 3, 3.5][k + 1] - [-0.7, 0, 1, 2, 3, 3.5][k]) * io(prog(t, ts[k], min(0.35, ts[k + 1] - ts[k])))
    return 540 + 400 * (i - off)
CAM4 = Camera(W, H, [(9.95, (540, 1000, 1.25)), (11.0, (600, 1000, 1.2), 'io'), (12.4, (540, 980, 1.1), 'io'), (13.1, (540, 980, 1.12))],
              kicks=[(tb, 0.08, 540, 1000) for tb, _, _ in BRANDS] + [(12.8, 0.12, 540, 900)])
P4 = Presenter([
    (9.95, dict(path=Track([(9.95, (540, -200)), (10.3, (540, 700), 'oc'), (13.1, (560, 680))]), size=5, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (12.8, dict(arms='cheer2', expr='wow', squash=True)),
], words=WORDS, base_size=5)


def shot_everyone(t):
    sc = scroll4(t)
    img = kit.street(t, sc); cars = layer()
    for i, (tb, col, x0) in enumerate(BRANDS):
        x = x4(t, i)
        h = 10 * oc(prog(t, tb, 0.25))
        headlights(cars, x + 190, kit.ROAD_Y - 40, 220)
        fx.contact_shadow(cars, x, kit.ROAD_Y, 400, s=S, alpha=150)
        draw_fcar(cars, col, x, 4, h, y=kit.ROAD_Y, dist=sc, lights=True)
    kit.ROAD.reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars)
    fg = layer()
    for i, (tb, col, x0) in enumerate(BRANDS):
        x = x4(t, i)
        fx.burst(fg, t, tb, x - 100, kit.ROAD_Y - 130, GLOW, n=10, r0=30, r1=160, seed=30 + i)
        if t >= tb:
            k = popin(t, tb, 0.22)
            blit(fg, fx.big('check', s=7), x, kit.ROAD_Y - 290, k, k, anchor='center')
    if t >= 12.8:
        k = popin(t, 12.8, 0.3) * (1 + 0.05 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'FINS FOR ALL', '#ffd23f', '#d6303a', '#e8b923', s=8), 540, 760, k, k, -4, anchor='center')
        fx.confetti(fg, t, 12.8, 540, 700, n=30, seed=7)
    fx.sparkles(fg, t, 540, kit.ROAD_Y - 120, 900, 160, n=8, seed=15)
    P4.draw(fg, t)
    return finish(img, fg, CAM4, t, rim=False)


# ================================================================== shot 5: the boardroom war
TBL = GROUND - 120
P5 = Presenter([
    (13.05, dict(path=Track([(13.05, (1300, 300)), (13.45, (960, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (13.45, dict(ground=GROUND, squash=True, arms='hips', look=(540, 800), expr='smirk', face=None)),
    (14.85, dict(arms='shock', expr='shock', squash=True, look=None, look_camera=True)),
], words=WORDS, base_size=6)
CAM5 = Camera(W, H, [(13.1, (540, 900, 1.15)), (14.3, (540, 860, 1.3), 'io'), (14.85, (540, 860, 1.25), 'io'), (16.0, (540, 860, 1.28))],
              kicks=[(13.41, 0.08, 540, 800), (14.32, 0.1, 540, 800), (14.85, 0.2, 540, 600)], shakes=[(14.85, 0.5, 18)])


def shot_war(t):
    img = boardroom().copy(); fg = layer()
    d = ImageDraw.Draw(fg)
    d.rectangle((90, TBL - 40, 990, TBL), fill=(120, 76, 50)); d.rectangle((90, TBL - 40, 990, TBL - 32), fill=(160, 108, 72))
    d.rectangle((140, TBL, 170, GROUND), fill=(90, 56, 38)); d.rectangle((910, TBL, 940, GROUND), fill=(90, 56, 38))
    hot = t >= 14.32
    for i, (x, suit, face) in enumerate(((300, (60, 70, 110), 1), (780, (110, 84, 60), -1))):
        pose = (2 if int(t * 6 + i) % 2 else 1) if hot else (1 if int(t * 3 + i) % 2 else 0)
        hop = 18 * abs(math.sin(t * 12 + i)) if hot else 0
        blit(fg, up(designer(suit, pose, face), 9), x, TBL - hop)
    fh = 10 + 4 * math.sin(t * 5) * hot                                            # fin model on the table between them
    draw_fcar(fg, 'red', 540, 3, fh, y=TBL - 40, sx=1.06, sy=0.86)
    for i, (x, ch) in enumerate(((330, '!'), (750, '?'))):
        if t >= 13.4 + 0.3 * i:
            k = popin(t, 13.4 + 0.3 * i, 0.2)
            blit(fg, fx.big('glyph', ch, '#e0303a', s=12), x, 640 + 12 * math.sin(t * 10 + i), k, k, 10 * math.sin(t * 8 + i), anchor='center')
    if hot:
        for k in range(5): fx.puff(fg, t, 14.32 + k * 0.15, 540, TBL - 200, seed=50 + k, life=0.7, size=0.8, drift=(0, -300), col=(230, 232, 240))
    fx.stamp_at(fg, t, 14.85, 'WAR?', 540, 470, rot=-10, s=11)
    fx.ring(fg, t, 14.85, 540, 520, (224, 48, 58), life=0.35, r1=420)
    fx.burst(fg, t, 14.85, 540, 520, RED, seed=51)
    P5.draw(fg, t)
    return finish(img, fg, CAM5, t, rim=False)


shot_teaser, TEASE_CUES = kit.teaser(15.95, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.0, shot_p38), (6.5, shot_fifties), (9.95, shot_everyone), (13.1, shot_war), (15.95, shot_teaser)]
TRANS = {1: (3.0, 3.2, 'whip', dict(dx=0, dy=-1)), 2: (6.5, 6.7, 'iris', (CAR2 - 260, GROUND - 330)), 3: (9.95, 10.15, 'whip', dict(dx=-1)),
         4: (13.1, 13.3, 'push', None), 5: (15.95, 16.15, 'whip', dict(dx=1))}
KEYCOL = {'fins': YEL, 'fins?': YEL, 'tailfins': YEL, '1948': GRN, 'reportedly': RED, 'p-38': YEL, 'bigger': YEL, 'sharper': YEL,
          'jets': YEL, 'volvo': GRN, 'war': RED, 'gm': RED}
CUES = [
    (0.0, 'stamp', 0.8), (0.05, 'sparkle', 0.6), (0.8, 'pop', 0.9), (0.82, 'sparkle', 0.6), (0.95, 'vroom', 0.9), (0.97, 'whoosh', 0.7),
    (1.45, 'fall', 0.6), (1.73, 'crash', 0.5), (1.74, 'boom', 0.5), (1.76, 'ding', 0.6), (2.6, 'pop', 0.7),
    (3.75, 'whoosh', 0.8), (3.99, 'vroom', 0.6), (4.05, 'stamp', 0.8), (5.0, 'pop', 0.6), (5.22, 'slide_down', 0.6), (5.88, 'thump', 0.8),
    (5.9, 'sparkle', 0.7), (6.0, 'pop', 0.6),
    (6.6, 'pop', 0.6)] + [(ts, 'click', 0.6) for ts, _ in YEARS] + [
    (7.99, 'pop', 0.6), (8.42, 'stamp', 0.6), (8.9, 'pop', 0.6), (9.2, 'whoosh', 0.8), (9.32, 'whoosh', 0.6),
    ] + [(tb, 'ding', 0.6) for tb, _, _ in BRANDS] + [(tb + 0.02, 'pop', 0.5) for tb, _, _ in BRANDS] + [
    (12.8, 'confetti', 0.7), (12.82, 'cha_ching', 0.6),
    (13.4, 'pop', 0.6), (13.7, 'pop', 0.6), (14.32, 'buzzer', 0.5), (14.85, 'stamp', 1.0), (14.87, 'boom', 0.5), (14.9, 'crash', 0.4),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
