"""Renders 'How old are your tyres?': read the DOT date code (last four digits = week + year).

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, mixer). Looping format: no outro
card; the last shot replays the cold open's roll-in, so the last frame flows into frame 0. Voiceover: out/tyre-birthday/
voiceover.wav (clip 2 of out/voiceover/full_voiceover.wav, see ../../fuel-gauge-arrow/src/voiceover.py).
The age warning stays hedged ('tyres age, even if you barely drive'); no replacement age is stated anywhere.
Shots (v2: ~1.5 s beats, detailed worlds, choreographed presenter):
  1 cake     0.00  cold open: a tyre rolls in wearing a birthday cake with a lit candle, party burst; hairline cracks; he crash-lands
  2 car      2.40  garage: he flies to a parked car and points as the camera dives into its front tyre
  3 dot      3.20  sidewall close-up: DOT lights up, then the last four digits (leader labels); real DOT photo; comment sticker
  4 code     7.55  '1822' slams in and splits into 18 = week and 22 = year; a calendar flips to week 18 of 2022
  5 age     10.45  time-lapse street: the parked car, sun and moon racing over, magnifier on the tyre as cracks creep
  6 torch   11.80  garage: he checks the tyre with a torch, the magnifier shows the code; share sticker
  7 loop    13.25  replays the cold-open roll-in, so the last frame matches frame 0
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, draw_car, headline, sticker, title, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter, reach
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline
from pixanim.autos import ptext

WORDS = kit.load_words(HERE)
DUR = 13.9
END_T = 13.25
def ws(i): return WORDS[i]['s']
HOOK = ((('How', None), ('OLD', '#ff5a5a'), ('are', None)), (('your tyres?', None),))
WIDE = False
RUB, RUB2, RUB_HI, RIMC = (30, 31, 37), (46, 48, 56), (70, 73, 84), (190, 196, 206)
CRACKS = [[(0.80, 0.05), (0.86, 0.12), (0.83, 0.2), (0.88, 0.27)], [(0.62, 1.9), (0.7, 2.0), (0.66, 2.1), (0.74, 2.22)],
          [(0.78, 3.3), (0.84, 3.38), (0.8, 3.5)], [(0.66, 4.3), (0.74, 4.4), (0.7, 4.52), (0.78, 4.6)],
          [(0.8, 5.4), (0.86, 5.5), (0.82, 5.6)], [(0.64, 1.0), (0.72, 1.1), (0.7, 1.2)]]


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def tyre(rot=0, crack=0.0):
    """Side-on tyre (64x64): tread blocks, sidewall, five-spoke rim at angle `rot` (deg, step 10); hairline cracks 0..1."""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(img); c = 31.5
    d.ellipse((0, 0, 63, 63), fill=RUB)
    for k in range(24):                                  # tread blocks turn with the wheel
        a = math.radians(rot + k * 15)
        x, y = c + 30 * math.cos(a), c + 30 * math.sin(a)
        d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=RUB2)
    d.ellipse((5, 5, 58, 58), fill=RUB2); d.arc((6, 6, 57, 57), 200, 290, fill=RUB_HI)
    d.ellipse((15, 15, 48, 48), fill=RIMC); d.ellipse((18, 18, 45, 45), fill=(140, 146, 158))
    for k in range(5):
        a = math.radians(rot + k * 72)
        d.line([(c, c), (c + 12 * math.cos(a), c + 12 * math.sin(a))], fill=RIMC, width=3)
    d.ellipse((28, 28, 35, 35), fill=(226, 230, 238))
    n = crack * len(CRACKS)
    for i, cr in enumerate(CRACKS):
        if i >= n: break
        part = min(1, n - i); pts = cr[:max(2, round(len(cr) * part))]
        d.line([(c + r * 31 * math.cos(a + math.radians(rot)), c + r * 31 * math.sin(a + math.radians(rot))) for r, a in pts], fill=(222, 226, 236), width=1)
    return outline(img)


@lru_cache(None)
def cake(ph=0):
    """Birthday cake (30x28) with one lit candle; flame flickers with phase 0..2."""
    img = Image.new('RGBA', (30, 28), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 25, 29, 27), fill=(226, 230, 238))
    d.rectangle((3, 14, 26, 25), fill=(244, 160, 190)); d.rectangle((3, 19, 26, 20), fill=(250, 240, 230))
    d.rectangle((3, 12, 26, 15), fill=(255, 248, 240))
    for x in (5, 10, 16, 22): d.rectangle((x, 15, x + 1, 16 + (x % 3)), fill=(255, 248, 240))
    for x in (6, 13, 20, 24): d.point((x, 22), fill=(255, 90, 90)); d.point((x + 2, 17), fill=(90, 180, 255))
    d.rectangle((14, 4, 15, 11), fill=(120, 200, 255)); d.point((14, 6), fill=WHITE); d.point((15, 9), fill=WHITE)
    fl = [(14, 0, 15, 3), (13, 0, 15, 3), (14, 0, 16, 3)][ph]
    d.ellipse(fl, fill=(255, 210, 63)); d.point((14 + (ph == 2), 2), fill=(255, 120, 40))
    return outline(img)


@lru_cache(None)
def sidewall(dot=0, num=0):
    """Sidewall close-up (160x52): a band of the tyre wall with raised lettering 'DOT 4B JX 1822'; dot/num highlight 0..2."""
    img = Image.new('RGBA', (160, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((-80, 8, 239, 327), fill=RUB); d.ellipse((-70, 16, 229, 317), fill=RUB2)
    d.arc((-70, 16, 229, 317), 220, 320, fill=RUB_HI)
    for k in range(13): d.rectangle((6 + k * 12, 10 + abs(k - 6) * 1.0, 10 + k * 12, 13 + abs(k - 6) * 1.0), fill=(40, 41, 48))
    def word(txt, x, y, hi):
        col = (255, 217, 59) if hi else (176, 180, 192)
        g = ptext(txt, col); g = g.resize((g.width * 2, g.height * 2), Image.NEAREST)
        if hi == 2:
            d.rounded_rectangle((x - 3, y - 3, x + g.width + 1, y + g.height + 1), 3, outline=(255, 217, 59))
        img.alpha_composite(g, (x, y))
        return x + g.width + 6
    x = word('DOT', 16, 24, dot)
    x = word('4B', x, 24, 0); x = word('JX', x, 24, 0) if WIDE else x
    word('1822', x + 2, 24, num)
    return img


@lru_cache(None)
def calendar(week, year):
    """Desk calendar page (44x46): red binder header 'WEEK', big week number, year underneath."""
    img = Image.new('RGBA', (44, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 4, 43, 45), fill=(250, 250, 246)); d.rectangle((0, 4, 43, 13), fill=(214, 48, 58))
    for x in (9, 33): d.rectangle((x, 0, x + 1, 7), fill=(120, 124, 134))
    hw = ptext('WEEK', (255, 255, 255)); img.alpha_composite(hw, (22 - hw.width // 2, 5))
    n = ptext(str(week), (26, 26, 46)); n = n.resize((n.width * 2, n.height * 2), Image.NEAREST)
    img.alpha_composite(n, (22 - n.width // 2, 16))
    y = ptext(str(year), (214, 48, 58)); img.alpha_composite(y, (22 - y.width // 2, 35))
    return outline(img)


@lru_cache(None)
def clock(step=0):
    """Wall clock (24x24): minute hand at step*30 deg, hour hand at step*2.5 deg."""
    img = Image.new('RGBA', (24, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img); c = 11.5
    d.ellipse((0, 0, 23, 23), fill=(214, 48, 58)); d.ellipse((2, 2, 21, 21), fill=(250, 250, 246))
    for k in range(12):
        a = math.radians(k * 30); d.point((c + 8 * math.cos(a), c + 8 * math.sin(a)), fill=(26, 26, 46))
    for ang, ln, col in ((step * 30 - 90, 8, (26, 26, 46)), (step * 2.5 - 90, 5, (214, 48, 58))):
        a = math.radians(ang); d.line([(c, c), (c + ln * math.cos(a), c + ln * math.sin(a))], fill=col, width=1)
    return outline(img)


# ================================================================== shot 1: the birthday tyre rolls in
TS = 7
LAND = 0.45
def tyre_x1(t): return lerp(1500, 540, oc(prog(t, -0.9, LAND + 0.9)))
def rot1(t): return round(-(tyre_x1(t) - 540) / (32 * TS) * 57.3 / 10) * 10
CR1 = ws(5)                                            # 'Bet': cracks start
P1 = Presenter([
    (-5, dict(path=Track([(1.05, (-200, 420)), (1.25, (60, 640), 'oc'), (1.45, (190, GROUND), 'ic')], smooth=True), size=7, legs='auto', arms='fly',
              expr='wow', face=1, ground=None, visible=False, trail=True)),
    (1.05, dict(visible=True)),
    (1.45, dict(ground=GROUND, squash=True, arms='shock', expr='shock', look=(540, 900))),
    (1.95, dict(arms='point', point=(600, 980), look=(600, 980), expr='talk')),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-2.0, (600, 960, 1.18)), (0.0, (580, 960, 1.22)), (LAND, (540, 940, 1.28), 'oc'), (CR1, (520, 980, 1.36), 'io'),
                     (2.6, (480, 980, 1.3), 'io')],
              kicks=[(LAND, 0.12, 540, 900), (CR1, 0.16, 600, 980), (1.45, 0.06, 190, 1100)], shakes=[(LAND, 0.3, 12), (CR1, 0.35, 10)])


def shot_cake(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = tyre_x1(t); bounce = 0 if t < LAND else 40 * abs(math.sin((t - LAND) * 9)) * math.exp(-(t - LAND) * 5)
    cy = GROUND - 64 * TS + 14 - bounce * 1.4
    fx.rays(fg, t, -3, x, cy - 120, (255, 160, 200, 26), hold=True, r=620)
    cr = clamp((t - CR1) / 0.9) if t >= CR1 else 0
    fx.contact_shadow(fg, x, GROUND, 460)
    blit(fg, up(tyre(rot1(t), round(cr * 12) / 12), TS), x, GROUND - bounce)
    blit(fg, up(cake(int(t * 10) % 3), 9), x + 4 * math.sin(t * 6), cy, 1, 1, 6 * math.sin(t * 5) * (1 if t < LAND + 0.6 else 0.3))
    fx.sparkles(fg, t, x, cy - 260, 220, 140, n=5, seed=3)
    if t < LAND:
        fx.speed_lines(fg, 0.8 * (1 - prog(t, -0.9, LAND + 0.9)), int(t * 12) % 5, col=(200, 204, 220))
        for k in range(3): fx.puff(fg, t, -0.3 + k * 0.2, x + 280, GROUND - 20, seed=10 + k, drift=(260, -40))
    else:
        fx.dust(fg, t, LAND, x, GROUND, n=12, seed=11)
        fx.confetti(fg, t, LAND, x, cy - 200, n=36, seed=14)
    if t >= CR1:
        for i, (a, r) in enumerate(((-30, 0.85), (200, 0.8), (120, 0.82))):      # red glints on each new crack
            px, py = x + r * 31 * TS * math.cos(math.radians(a)), GROUND - 32 * TS + r * 31 * TS * math.sin(math.radians(a))
            if t >= CR1 + i * 0.25: fx.ring(fg, t, CR1 + i * 0.25, px, py, RED, r1=160); fx.burst(fg, t, CR1 + i * 0.25, px, py, RED, n=8, r0=40, r1=160, seed=12 + i)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: dive into a real car's tyre
T2 = 2.40
CS2, CX2 = 9, 470
WHEEL2 = (CX2 + 24 * CS2, GROUND - 9 * CS2)            # front wheel centre (car.WHEELS)
P2 = Presenter([
    (T2, dict(path=Track([(T2, (1300, 500)), (T2 + 0.3, (WHEEL2[0] + 200, GROUND - 260), 'oc')], smooth=True), size=6, legs='auto', arms='fly',
              expr='grin', face=-1, hover=8, trail=True)),
    (T2 + 0.3, dict(arms='point', point=WHEEL2, look=WHEEL2, expr='talk')),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(T2, (560, 1000, 1.0)), (T2 + 0.3, (WHEEL2[0], WHEEL2[1] - 40, 1.4), 'io'), (3.3, (WHEEL2[0] - 20, WHEEL2[1], 3.2), 'ic')],
              kicks=[(T2 + 0.3, 0.06, *WHEEL2)])


def shot_car(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    draw_car(fg, 'blue', CX2, CS2, lights=True)
    fx.ring(fg, t, T2 + 0.3, *WHEEL2, GLOW, r1=200)
    dg.label(fg, t, T2 + 0.3, 'SIDEWALL', WHEEL2, (WHEEL2[0] - 80, WHEEL2[1] - 330), '#ffd23f', '#1a1a2e', '#e8b923', s=6)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the sidewall code
T3 = 3.20
DOT_T, NUM_T = ws(12), ws(17)                          # 'DOT', 'last'
PH0, PH1 = DOT_T + 0.35, NUM_T - 0.05                  # photo on screen
CM0 = NUM_T + 0.7                                      # comment sticker
DOTP, NUMP = (270, 650), (774, 650)
P3 = Presenter([
    (T3, dict(path=Track([(T3, (1300, 1500)), (T3 + 0.35, (900, 1250), 'oc')], smooth=True), size=6, legs='auto', arms='fly', expr='grin',
              face=-1, hover=8, ground=None)),
    (T3 + 0.35, dict(arms='point', point=DOTP, look=DOTP, expr='talk')),
    (NUM_T, dict(path=Track([(NUM_T, (900, 1250)), (NUM_T + 0.3, (330, 1250), 'io')]), point=NUMP, look=NUMP, face=1, expr='wow', squash=True)),
    (CM0, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin')),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(T3, (520, 760, 1.4)), (T3 + 0.4, (540, 860, 1.05), 'oc'), (DOT_T + 0.1, (440, 860, 1.12), 'io'), (NUM_T, (640, 860, 1.12), 'io'),
                     (7.6, (560, 900, 1.04), 'io')],
              kicks=[(DOT_T, 0.16, *DOTP), (NUM_T, 0.16, *NUMP)])


def shot_dot(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    dot = 2 if t >= DOT_T and int(t * 6) % 2 == 0 else int(t >= DOT_T)
    num = 2 if t >= NUM_T and int(t * 6) % 2 == 0 else int(t >= NUM_T)
    blit(fg, up(sidewall(dot, num), 6), 540, 780 + 6 * math.sin(t * 2))
    fx.glint(fg, t, T3 + 0.2, 540, 600, r=420, life=0.6)
    if t >= DOT_T:
        fx.rays(fg, t, DOT_T, *DOTP, (255, 210, 63, 30), hold=t < NUM_T, r=320)
        fx.ring(fg, t, DOT_T, *DOTP, GLOW, r1=300); fx.burst(fg, t, DOT_T, *DOTP, GLOW, n=10, seed=21)
        dg.label(fg, t, DOT_T + 0.05, 'DOT', DOTP, (240, 400), '#ffd23f', '#1a1a2e', '#e8b923', s=9)
    if t >= NUM_T:
        fx.rays(fg, t, NUM_T, *NUMP, (255, 90, 90, 34), hold=True, r=360)
        fx.ring(fg, t, NUM_T, *NUMP, RED, r1=360); fx.burst(fg, t, NUM_T, *NUMP, RED, n=12, seed=22)
        fx.sparkles(fg, t, *NUMP, 360, 160, n=6, seed=23)
        dg.label(fg, t, NUM_T + 0.1, 'WEEK AND YEAR', NUMP, (640, 420), '#ffffff', '#d6303a', '#ffd0d0', s=8)
    P3.draw(fg, t)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: 1822 = week 18 of 2022
T4 = 7.55
SPLIT, WK, YR = ws(30), ws(31), ws(33)                # 'week', '18', '2022'
P4 = Presenter([
    (T4, dict(path=Track([(T4, (-200, 400)), (T4 + 0.35, (150, 640), 'oc')], smooth=True), size=6, legs='auto', arms='fly', expr='grin',
              face=1, ground=None, trail=True, hover=10)),
    (T4 + 0.35, dict(squash=True, arms='point', point=(540, 700), look=(540, 700), expr='talk')),
    (WK, dict(point=(300, 1070), look=(300, 1070), expr='wow', squash=True)),
    (YR, dict(arms='cheer', point=None, look=None, look_camera=True, expr='happy', squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(T4, (540, 940, 1.0)), (SPLIT, (540, 900, 1.08), 'io'), (WK, (480, 900, 1.12), 'io'), (YR, (600, 920, 1.12), 'io'), (10.5, (540, 920, 1.08), 'io')],
              kicks=[(ws(28), 0.14, 540, 1070), (SPLIT, 0.1, 540, 700), (WK, 0.14, 300, 1070), (YR, 0.14, 780, 1070)],
              shakes=[(ws(28), 0.25, 12)])


def shot_code(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    sp = oc(prog(t, SPLIT, 0.35))
    t28 = ws(28) - 0.05
    if t >= t28:
        fx.rays(fg, t, t28, 540, 1070, (255, 210, 63, 30), hold=True, r=600)
        k0 = popin(t, t28, 0.25) * fx.slam(t, t28, k=0.5)
        lx, rx = lerp(392, 270, sp), lerp(688, 810, sp)
        blit(fg, fx.big('badge', '18', '#ffd23f', '#1a1a2e', '#e8b923', s=16), lx, 1070, k0, k0, -3 * sp + 2 * math.sin(t * 4), anchor='center')
        blit(fg, fx.big('badge', '22', '#ffd23f', '#d6303a', '#e8b923', s=16), rx, 1070, k0, k0, 3 * sp - 2 * math.sin(t * 4), anchor='center')
        if t < SPLIT + 0.1: fx.burst(fg, t, t28, 540, 1070, GLOW, n=14, seed=30)
        else: fx.burst(fg, t, SPLIT, 540, 1070, WHITE, n=10, seed=35)
        if t >= WK:
            kw = popin(t, WK); blit(fg, fx.big('label', 'WEEK', '#ffffff'), 280, 1225, kw, kw, anchor='center')
        if t >= YR:
            ky = popin(t, YR); blit(fg, fx.big('label', 'YEAR', '#ff5a5a'), 800, 1225, ky, ky, anchor='center')
    if t >= SPLIT - 0.1:                               # calendar flips through the weeks to 18, torn pages flying off
        kc = popin(t, SPLIT - 0.1)
        wk = 18 if t >= WK else max(1, min(17, int(1 + (t - SPLIT) / (WK - SPLIT) * 17)))
        blit(fg, up(calendar(wk, 2022), 10), 540, 900, kc, kc, -2 + 2 * math.sin(t * 3))
        if SPLIT <= t < WK + 0.4:
            for j in range(4):                         # torn pages tumbling away
                u = ((t - SPLIT) * 3 + j / 4) % 1
                pg = up(calendar(max(1, wk - 1 - j), 2022), 10)
                blit(fg, pg, 540 + u * (300 + 90 * j) * (1 if j % 2 else -1), 900 - 300 * u + 900 * u * u, 1 - 0.4 * u, 1 - 0.4 * u, 220 * u * (1 if j % 2 else -1))
        if t >= WK: fx.burst(fg, t, WK, 540, 650, GLOW, n=12, seed=31); fx.ring(fg, t, WK, 540, 650, GLOW)
        if t >= YR: fx.confetti(fg, t, YR, 540, 500, n=36, seed=32)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: time-lapse, tyres age anyway
T5 = 10.45
CS5, CX5 = 6, 520
WHEEL5 = (CX5 + 24 * CS5, ROAD_Y - 9 * CS5)
MAG = (760, 620)
CAM5 = Camera(W, H, [(T5, (540, 980, 1.05)), (11.8, (600, 900, 1.2), 'io')],
              kicks=[(ws(36), 0.14, *MAG), (ws(40), 0.1, *MAG)])


def shot_age(t):
    u = (t - T5) * 2.2                                 # day/night cycles
    day = 0.5 + 0.5 * math.cos(u * 2 * math.pi)
    img = street(t, 0)
    tint = Image.new('RGBA', (W, H), (255, 200, 120, int(70 * day)))
    img.alpha_composite(tint)
    fg = layer(); d = ImageDraw.Draw(fg)
    a = u * 2 * math.pi                                # sun and moon racing across the sky
    for k, col in ((0, (255, 210, 63)), (math.pi, (226, 230, 238))):
        sx, sy = 540 - 460 * math.cos(a + k), 560 - 300 * math.sin(a + k)
        if sy < 620: d.ellipse((sx - 46, sy - 46, sx + 46, sy + 46), fill=col + (255,), outline=(26, 26, 46), width=8)
    draw_car(fg, 'silver', CX5, CS5, y=ROAD_Y)
    cr = clamp((t - T5 - 0.1) / 1.2)                   # magnifier on the front tyre: cracks creep
    k = popin(t, T5 + 0.1)
    if k > 0:
        d.line([WHEEL5, MAG], fill=(232, 236, 244), width=10)
        lens = Image.new('RGBA', (420, 420), (0, 0, 0, 0)); ld = ImageDraw.Draw(lens)
        ld.ellipse((0, 0, 419, 419), fill=(40, 42, 50)); ld.ellipse((14, 14, 405, 405), fill=(20, 21, 28))
        tyr = up(tyre(0, round(cr * 12) / 12), 6); lens.alpha_composite(tyr, (210 - tyr.width // 2, 210 - tyr.height // 2))
        m = Image.new('L', lens.size, 0); ImageDraw.Draw(m).ellipse((14, 14, 405, 405), fill=255)
        ring = Image.new('RGBA', lens.size, (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse((0, 0, 419, 419), outline=(232, 236, 244), width=14)
        lens2 = Image.new('RGBA', lens.size, (0, 0, 0, 0)); lens2.paste(lens, (0, 0), m); lens2.alpha_composite(ring)
        blit(fg, lens2, *MAG, k, k, 0, anchor='center')
        if cr > 0.1: fx.ring(fg, t, T5 + 0.5, *MAG, RED, r1=300)
    kc = popin(t, T5 + 0.25)
    blit(fg, up(clock(int((t - T5) * 30) % 120), 9), 220, 560, kc, kc, 4 * math.sin(t * 12), anchor='center')
    img.alpha_composite(fg)
    return CAM5.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 6: the torch check
T6 = 11.80
CS6, CX6 = 8, 380
WHEEL6 = (CX6 + 24 * CS6, GROUND - 9 * CS6)
HAND6 = (WHEEL6[0] + 230, WHEEL6[1] - 120)
P6 = Presenter([
    (T6, dict(path=Track([(T6, (1300, 500)), (T6 + 0.35, reach(HAND6, 200, 7, -1).at(0), 'oc')], smooth=True), size=7, legs='auto', arms='fly',
              expr='grin', face=-1, hover=6, trail=True)),
    (T6 + 0.35, dict(arms=('aim', 200), squash=True, look=WHEEL6, expr='think', legs='stand', ground=GROUND)),
    (T6 + 1.0, dict(arms='thumb', look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM6 = Camera(W, H, [(T6, (560, 1000, 1.2)), (T6 + 0.4, (WHEEL6[0] + 100, WHEEL6[1] - 80, 1.5), 'io'), (END_T, (WHEEL6[0] + 120, WHEEL6[1] - 120, 1.4), 'io')],
              kicks=[(T6 + 0.4, 0.1, *WHEEL6), (T6 + 1.0, 0.08, *WHEEL6)])


def shot_torch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    draw_car(fg, 'blue', CX6, CS6, lights=False)
    if t >= T6 + 0.38:
        a = int(110 * clamp((t - T6 - 0.38) / 0.12))
        ImageDraw.Draw(fg).polygon([HAND6, (WHEEL6[0] - 60, WHEEL6[1] - 110), (WHEEL6[0] - 40, WHEEL6[1] + 90)], fill=(255, 244, 190, a))
        k = popin(t, T6 + 0.45)
        blit(fg, up(sidewall(1, 2), 3), WHEEL6[0] - 10, WHEEL6[1] - 300, k, k, -3, anchor='center')
        dg.label(fg, t, T6 + 0.5, 'WEEK 18 / 2022', WHEEL6, (WHEEL6[0] + 30, WHEEL6[1] - 460), '#ffd23f', '#1a1a2e', '#e8b923', s=5)
        fx.sparkles(fg, t, *WHEEL6, 240, 200, n=6, seed=51)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


def shot_loop(t): return shot_cake(t - DUR)


def overlay(cv, t):
    headline(cv, t, 2.25, HOOK, y=400, sz=104)
    if t >= END_T and t - DUR > -0.45: headline(cv, max(-0.35, t - DUR), 2.25, HOOK, y=400, sz=104)
    kit.photo_hq(cv, t, PH0, PH1, 'dot_code', 540, 1060, 640, rot=-3, label='A REAL DOT CODE')
    sticker(cv, t, CM0, T4 - 0.1, ("Reply with YOUR tyre's", '4-digit code below'), 1130, rot=-2)
    title(cv, t, ws(37), T6 - 0.1, 'even if you barely drive', WHITE, 330, 84, -2)
    sticker(cv, t, T6 + 0.1, END_T - 0.05, ('Send this to someone', 'who never checks.'), 420, rot=2)


SHOTS = [(-3.0, shot_cake), (T2, shot_car), (T3, shot_dot), (T4, shot_code), (T5, shot_age), (T6, shot_torch), (END_T, shot_loop)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.22, 'iris', (WHEEL2[0], WHEEL2[1])), 3: (T4, T4 + 0.2, 'push', None),
         4: (T5, T5 + 0.2, 'whip', dict(dx=1)), 5: (T6, T6 + 0.2, 'push', None), 6: (END_T, END_T + 0.2, 'whip', dict(dx=-1))}
KEYCOL = {'old': RED, 'checked': YEL, 'dot': YEL, 'four': RED, 'numbers': RED, '1822': RED, '18': YEL, '2022': RED, 'age': RED, 'week': YEL, 'year': RED}
CUES = [(0.0, 'whoosh', 0.6), (LAND, 'thump', 0.7), (LAND + 0.02, 'confetti', 0.6), (LAND + 0.03, 'pop', 0.5), (CR1, 'creak', 0.8),
        (CR1 + 0.05, 'crash', 0.25), (CR1 + 0.25, 'click', 0.5), (CR1 + 0.5, 'click', 0.5), (1.05, 'whoosh', 0.4), (1.45, 'thump', 0.5),
        (T2, 'whoosh', 0.5), (T2 + 0.3, 'pop', 0.5), (T3 - 0.3, 'whoosh', 0.6), (DOT_T, 'ding', 0.8), (DOT_T + 0.02, 'sparkle', 0.6),
        (PH0, 'pop', 0.7), (NUM_T, 'ding', 0.8), (NUM_T + 0.1, 'pop', 0.5), (CM0, 'pop', 0.7), (T4 + 0.35, 'thump', 0.4),
        (ws(28) - 0.05, 'stamp', 0.8), (ws(28) - 0.03, 'boom', 0.4), (SPLIT, 'whoosh', 0.5)] + [
        (SPLIT + 0.06 * k, 'click', 0.3) for k in range(int((WK - SPLIT) / 0.06))] + [
        (WK, 'ding', 0.8), (YR, 'cha_ching', 0.6), (YR + 0.02, 'confetti', 0.6), (T5 + 0.1, 'pop', 0.5), (T5, 'whoosh', 0.5)] + [
        (T5 + 0.15 + 0.1 * k, 'click', 0.3) for k in range(13)] + [
        (ws(37), 'pop', 0.5), (T6, 'whoosh', 0.4), (T6 + 0.38, 'click', 0.8), (T6 + 0.45, 'pop', 0.5), (T6 + 1.0, 'ding', 0.6), (T6 + 0.1, 'pop', 0.6)]

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=False, loud=True, crisp=True,
          end=False, flash=False, tag='corner')

if __name__ == '__main__':
    kit.main()
