"""Renders 'A110, 1,103 kg': a light aluminium car with its engine behind the seats, 249 hp, Britain's Best Car 2020.

Template: videos/ac-idle shot structure on shared/episode.py (as in plaid-two-seconds). Voiceover: clip 6 of
out/voiceover/full_voiceover.wav (shared/vo_split.py), aligned by align.py -> words.json. The read is 12.2 s and has no
'Follow' line, so the episode runs 15 s and the end card shows it. The car is a generic pixel coupe with no badges.
Shots:
  1 scale    0.00  hook: the car on a scale that settles on 1,103 KG; '1,103 kg'
  2 photo    3.70  framed real photo of an Alpine A110; ALUMINIUM tag
  3 cutaway  5.55  x-ray cutaway: the engine sits behind the seats; 'engine behind the seats'
  4 power    7.55  249 HP counter as it pulls away down the street
  5 trophy   9.60  2020 badge, a trophy pops in, confetti; "Britain's Best Car"
  6 teaser  12.30  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title, draw_car, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 15.0, 12.35


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def scale_base():
    """Weighing platform (110x8) with a ribbed top."""
    img = Image.new('RGBA', (110, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 2, 109, 7), fill=(70, 73, 84)); d.rectangle((2, 0, 107, 2), fill=(150, 156, 170))
    for x in range(6, 106, 6): d.line([(x, 0), (x, 1)], fill=(110, 114, 126))
    d.rectangle((4, 7, 9, 7), fill=(26, 26, 46)); d.rectangle((100, 7, 105, 7), fill=(26, 26, 46))
    return outline(img)


@lru_cache(None)
def seat():
    img = Image.new('RGBA', (9, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 4, 12), 2, fill=(44, 46, 58)); d.rectangle((0, 9, 8, 13), fill=(44, 46, 58))
    d.line([(1, 1), (1, 10)], fill=(92, 96, 110))
    return outline(img)


@lru_cache(None)
def engine(glow=0):
    """Compact engine block (16x11): head, four bolt glints, glowing when `glow` (0..3)."""
    img = Image.new('RGBA', (16, 11), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 3, 15, 10), fill=(120, 126, 138)); d.rectangle((1, 0, 14, 3), fill=(176, 182, 192))
    for k in range(4): d.point((3 + k * 3, 1), fill=(255, 220, 90) if k < glow else (96, 100, 110))
    d.rectangle((2, 5, 13, 8), fill=(70, 73, 84)); d.line([(2, 5), (13, 5)], fill=(150, 156, 170))
    return outline(img)


@lru_cache(None)
def trophy():
    """Gold cup (26x32) with handles, stem and a two-step base."""
    img = Image.new('RGBA', (26, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    gold, shade, hi = (255, 196, 40), (214, 150, 20), (255, 232, 130)
    d.arc((0, 3, 9, 14), 90, 270, fill=gold, width=2); d.arc((16, 3, 25, 14), 270, 90, fill=gold, width=2)
    d.pieslice((4, -10, 21, 18), 0, 180, fill=gold); d.rectangle((4, 0, 21, 4), fill=gold)
    d.rectangle((15, 1, 19, 12), fill=shade); d.line([(7, 1), (7, 10)], fill=hi)
    d.rectangle((11, 18, 14, 23), fill=shade)
    d.rectangle((7, 23, 18, 26), fill=gold); d.rectangle((5, 27, 20, 31), fill=(70, 73, 84))
    d.point((12, 7), fill=(255, 255, 255)); d.point((11, 8), fill=hi)
    return outline(img)


# ================================================================== shot 1: hook, the scale
def kg(t): return 1103 if t >= 1.9 else int(1103 * oc(prog(t, 0.1, 1.8)) + 37 * math.sin(t * 40) * (t < 1.9))
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.22)), (0.0, (540, 960, 1.22)), (1.0, (560, 920, 1.3), 'io'), (3.7, (540, 900, 1.24), 'io')],
              kicks=[(0.1, 0.12, 540, 1000), (1.9, 0.24, 540, 760), (2.95, 0.1, 540, 760)], shakes=[(1.9, 0.3, 12)])


def shot_scale(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    drop = oc(prog(t, 0.0, 0.25))
    blit(fg, up(scale_base(), 8), 540, GROUND)
    sq = 1 - 0.04 * math.exp(-max(0, t - 0.25) * 7) * (t > 0.25)
    draw_car(fg, 'blue', 540, 7, y=GROUND - 48 - int(300 * (1 - drop)), sx=1 / sq, sy=sq)
    if t >= 0.25: fx.dust(fg, t, 0.25, 540, GROUND - 48, n=12, seed=1)
    k = popin(t, 0.1, 0.25) * (1 + 0.12 * math.exp(-(t - 1.9) * 6) * (t > 1.9))
    blit(fg, fx.big('badge', f'{kg(t):,} KG', '#e0303a' if t >= 1.9 else '#ffffff', '#ffffff' if t >= 1.9 else '#1a1a2e',
                    '#a82028' if t >= 1.9 else '#d6d9e2', s=11), 540, 760, k, k, -3 + 2 * math.sin(t * 4), anchor='center')
    if t >= 1.9:
        fx.ring(fg, t, 1.9, 540, 760, RED, r1=460); fx.burst(fg, t, 1.9, 540, 760, GLOW, n=16, seed=2)
        fx.sparkles(fg, t, 540, 760, 760, 220, n=7, seed=3)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 3.6, '1,103 kg', RED, 450, 140, -3)
    title(cv, t, 5.85, 7.5, 'engine behind', YEL, 410, 110, -2)
    title(cv, t, 6.0, 7.5, 'the seats', YEL, 540, 110, 2)
    title(cv, t, 11.18, 12.25, "Britain's Best Car", GRN, 430, 96, -2)


# ================================================================== shot 2: the real car, aluminium body
P2 = Presenter([
    (3.65, dict(path=Track([(3.65, (1300, 300)), (4.0, (930, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (4.0, dict(ground=GROUND, squash=True, arms='point', point=(500, 760), look=(500, 760), expr='smile', face=None)),
    (4.96, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(3.7, (540, 860, 1.06)), (4.51, (500, 880, 1.12), 'io'), (5.55, (500, 880, 1.14), 'io')],
              kicks=[(3.8, 0.1, 500, 760), (4.51, 0.16, 330, 1100), (4.96, 0.08, 500, 760)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 3.75, 500, 760, GLOW, hold=True, r=640)
    photo(fg, t, 3.8, 9.0, 'a110', 500, 740, 780, 0, -3, 'THE REAL CAR', fit=True)
    if t >= 4.51:
        k = fx.slam(t, 4.51) * popin(t, 4.51, 0.2)
        blit(fg, fx.big('badge', 'ALUMINIUM', '#d6d9e2', '#1a1a2e', '#a6acb8', s=9), 360, 1110, k, k, -4, anchor='center')
        fx.burst(fg, t, 4.51, 360, 1110, (220, 226, 236), n=12, seed=21); fx.sparkles(fg, t, 360, 1110, 500, 140, n=6, seed=22)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: cutaway, engine behind the seats
CX3, CS3 = 540, 9
def gx(x): return CX3 - 45 * CS3 + x * CS3
def gy(y): return GROUND - (50 - y) * CS3
P3 = Presenter([
    (5.5, dict(path=Track([(5.5, (-200, 300)), (5.85, (110, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='wow', face=1, ground=None)),
    (5.85, dict(ground=GROUND, squash=True, arms='point', point=(gx(29), gy(30)), look=(gx(29), gy(30)), expr='talk', face=None)),
    (6.71, dict(arms='point', point=(gx(46), gy(28)), look=(gx(46), gy(28)), expr='smile')),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(5.55, (540, 960, 1.08)), (6.15, (460, 960, 1.22), 'io'), (6.71, (580, 960, 1.22), 'io'), (7.55, (540, 960, 1.16), 'io')],
              kicks=[(5.85, 0.16, gx(29), gy(30)), (6.38, 0.1, gx(29), gy(30)), (6.77, 0.12, gx(46), gy(28))])


def shot_cutaway(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    car = layer(); draw_car(car, 'blue', CX3, CS3)
    xr = clamp((t - 5.6) / 0.3)                                 # body fades to an x-ray ghost
    a = car.getchannel('A').point(lambda v: int(v * (1 - 0.55 * xr)))
    car.putalpha(a); fg.alpha_composite(car)
    fx.contact_shadow(fg, CX3, GROUND, 760, s=CS3)
    if xr > 0:
        d = ImageDraw.Draw(fg)
        for x in range(gx(4), gx(86), 27): d.line([(x, gy(18)), (x, gy(46))], fill=(120, 190, 255, int(60 * xr)), width=2)
        k = popin(t, 5.85, 0.3)
        blit(fg, up(engine(int(t * 8) % 4 if t > 6.15 else 0), CS3), gx(29), gy(36) + 4 * math.sin(t * 30) * (t > 6.15), k, k)
        ks = popin(t, 6.3, 0.3)
        for sx in (44, 50): blit(fg, up(seat(), CS3), gx(sx), gy(35), ks, ks)
        if t >= 6.15: fx.ring(fg, t, 6.15, gx(29), gy(30), GLOW, r1=260)
        if t >= 6.38:
            ka = popin(t, 6.38, 0.25)
            blit(fg, fx.big('arrow'), gx(37.5), gy(26), ka, ka, 0, anchor='center', flip=True)
    dg.label(fg, t, 6.0, 'ENGINE', (gx(29), gy(25)), (330, 790), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    dg.label(fg, t, 6.71, 'SEATS', (gx(47), gy(22)), (830, 790), '#ffffff', '#1a1a2e', '#d6d9e2', s=8)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: 249 hp
def hp(t): return int(249 * oc(prog(t, 7.98, 0.84)))
def car_x4(t): return 420 + 900 * ic(prog(t, 8.9, 0.7))
CAM4 = Camera(W, H, [(7.55, (540, 960, 1.14)), (7.98, (520, 940, 1.24), 'io'), (8.82, (560, 940, 1.2), 'io'), (9.6, (600, 960, 1.16), 'io')],
              kicks=[(7.73, 0.1, 420, 1000), (7.98, 0.14, 540, 620), (8.82, 0.22, 540, 620)], shakes=[(8.9, 0.4, 10)])


def shot_power(t):
    img = street(t, 300 * t + 1800 * ic(prog(t, 8.9, 0.7))); fg = layer()
    x = car_x4(t)
    draw_car(fg, 'blue', x, 5, y=ROAD_Y, dist=x + t * 300, lights=True, rot=1.5 * math.exp(-max(0, t - 8.9) * 5) * (t > 8.9))
    for k in range(4): fx.puff(fg, t, 7.7 + k * 0.3, x - 230, ROAD_Y - 30, seed=40 + k, life=0.6, drift=(-200, -80), col=(200, 204, 214))
    if t >= 8.9: fx.speed_lines(fg, 0.9, int(t * 14) % 5, col=(200, 204, 220))
    if t >= 7.98:
        k = popin(t, 7.98, 0.25) * (1 + 0.08 * (hp(t) == 249) * math.sin(t * 18))
        blit(fg, fx.big('badge', f'{hp(t)} HP', '#ffd23f' if hp(t) == 249 else '#ffffff', '#1a1a2e', '#e8b923', s=11), 540, 620, k, k, -3, anchor='center')
    if t >= 8.82: fx.burst(fg, t, 8.82, 540, 620, GLOW, n=16, seed=41); fx.sparkles(fg, t, 540, 620, 700, 220, n=7, seed=42)
    return CAM4.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 5: Britain's Best Car, 2020
P5 = Presenter([
    (9.55, dict(path=Track([(9.55, (1300, 300)), (9.9, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (9.9, dict(ground=GROUND, squash=True, arms='point', point=(460, 700), look=(460, 700), expr='smile', face=None)),
    (10.89, dict(arms='cheer', point=None, look_camera=True, expr='wow', squash=True)),
    (11.87, dict(arms='thumb', expr='grin')),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(9.6, (540, 880, 1.1)), (10.89, (500, 840, 1.2), 'io'), (12.3, (500, 840, 1.24), 'io')],
              kicks=[(9.92, 0.12, 250, 640), (10.89, 0.24, 460, 800), (11.59, 0.12, 460, 800)], shakes=[(10.89, 0.3, 12)])


def shot_trophy(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    draw_car(fg, 'blue', 460, 6, y=GROUND)
    fx.contact_shadow(fg, 460, GROUND, 540, s=6)
    if t >= 10.89:
        k = fx.slam(t, 10.89) * popin(t, 10.89, 0.2)
        fx.rays(fg, t, 10.89, 460, 760, GLOW, hold=True, r=520)
        blit(fg, up(trophy(), 10), 460, 900 + 10 * math.sin(t * 4), k, k, 4 * math.sin(t * 3))
        fx.burst(fg, t, 10.89, 460, 760, GLOW, n=18, seed=51); fx.confetti(fg, t, 10.89, 460, 560, n=50, seed=52)
        fx.sparkles(fg, t, 460, 760, 520, 360, n=8, seed=53)
    if t >= 9.92:
        k = popin(t, 9.92, 0.25); x = lerp(460, 280, oc(prog(t, 10.89, 0.3)))
        blit(fg, fx.big('badge', '2020', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), x, 610, k, k, -4 + 2 * math.sin(t * 5), anchor='center')
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(12.3, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_scale), (3.7, shot_photo), (5.55, shot_cutaway), (7.55, shot_power), (9.6, shot_trophy), (12.3, shot_teaser)]
TRANS = {1: (3.7, 3.9, 'whip', dict(dx=1)), 2: (5.55, 5.75, 'iris', (540, 960)), 3: (7.55, 7.75, 'push', None),
         4: (9.6, 9.8, 'whip', dict(dx=0, dy=1)), 5: (12.3, 12.5, 'whip', dict(dx=1))}
KEYCOL = {'alpine': YEL, '1,103': RED, 'aluminium': YEL, 'engine': YEL, 'behind': YEL,
          'seats': YEL, 'makes': YEL, '249': YEL, '2020': YEL, 'won': GRN, 'best': GRN}
CUES = [
    (0.0, 'whoosh', 0.5), (0.25, 'thump', 0.9), (0.27, 'crash', 0.3)] + [(0.3 + k * 0.2, 'click', 0.35) for k in range(8)] + [
    (1.9, 'ding', 0.9), (1.92, 'stamp', 0.6), (2.95, 'sparkle', 0.5),
    (3.8, 'pop', 0.7), (3.82, 'sparkle', 0.5), (4.51, 'stamp', 0.7), (4.96, 'pop', 0.4),
    (5.85, 'pop', 0.6), (6.0, 'pop', 0.5), (6.15, 'vroom', 0.5), (6.3, 'pop', 0.5), (6.71, 'pop', 0.5),
    (7.7, 'vroom', 0.5), (7.98, 'pop', 0.6)] + [(8.05 + k * 0.15, 'click', 0.3) for k in range(5)] + [(8.82, 'ding', 0.7), (8.9, 'vroom', 1.0),
    (9.92, 'pop', 0.6), (10.89, 'cha_ching', 0.6), (10.9, 'confetti', 0.9), (11.18, 'sparkle', 0.6), (11.87, 'ding', 0.5),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
