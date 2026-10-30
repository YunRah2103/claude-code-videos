"""Renders 'GT3 RS, 860 kg': downforce at 177 mph, the rear wing that opens above 62 mph, minus 30 percent.

Template: videos/ac-idle shot structure on shared/episode.py (as in plaid-two-seconds). Voiceover: clip 3 of
out/voiceover/full_voiceover.wav (shared/vo_split.py), aligned by align.py -> words.json. The supplied read has no
'Follow' line for this episode, so the end card shows it. The car is a generic pixel coupe with no badges or lettering.
Shots:
  1 press    0.00  hook: night street at 177 MPH, an invisible hand pushes the car onto the tarmac; '860 kg of downforce.'
  2 photo    2.25  framed real photo of a 911 GT3 RS
  3 weight   4.65  garage: an 860 KG weight presses the car down, tyres squash
  4 wing     7.80  street: speed climbs, the rear wing rises at 62 MPH; 'opens above 62 mph'
  5 pedal   11.55  dashboard: nearly full throttle, needle near the redline
  6 cut     13.50  wing open: the downforce bar drops 30 percent; -30%
  7 teaser  16.30  shared NEXT EPISODE ending
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
from pixanim.dash import Dashboard
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 18.0, 16.35


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def wing(rise=0.0):
    """Rear wing (22x16): two swan-neck posts and a plank; rise 0..1 lifts the plank and flattens its angle."""
    img = Image.new('RGBA', (22, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    top = 9 - round(6 * rise)
    for x in (6, 15): d.line([(x, 15), (x, top + 1)], fill=(44, 46, 58), width=2)
    tilt = round(3 * (1 - rise))
    d.polygon([(1, top + tilt), (20, top - 1), (20, top + 1), (1, top + tilt + 2)], fill=(44, 46, 58))
    d.line([(2, top + tilt), (19, top - 1)], fill=(92, 96, 110))
    d.rectangle((0, top + tilt - 1, 1, top + tilt + 3), fill=(28, 30, 40)); d.rectangle((20, top - 2, 21, top + 2), fill=(28, 30, 40))
    return outline(img)


@lru_cache(None)
def hand(a=110):
    """Ghostly flat hand (34x30) pressing down: fingers point down, outline only, alpha `a`."""
    img = Image.new('RGBA', (34, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    fill, edge = (200, 216, 255, a), (240, 246, 255, 235)
    for i in range(4):
        x = 7 + i * 6
        d.rounded_rectangle((x, 12, x + 4, 28 - abs(i - 1.5) * 2), 2, fill=fill, outline=edge)
    d.rounded_rectangle((6, 2, 31, 16), 4, fill=fill, outline=edge)
    d.rounded_rectangle((0, 8, 8, 13), 2, fill=fill, outline=edge)                     # thumb
    d.line([(10, 5), (14, 5)], fill=(255, 255, 255, a)); d.line([(12, 8), (20, 8)], fill=(255, 255, 255, a // 2))
    return img


@lru_cache(None)
def weight_block():
    """Gym weight (30x26): trapezoid with a handle loop on top."""
    img = Image.new('RGBA', (30, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.arc((9, 0, 20, 12), 180, 360, fill=(44, 46, 58), width=3)
    d.polygon([(5, 7), (24, 7), (29, 25), (0, 25)], fill=(44, 46, 58))
    d.polygon([(7, 9), (22, 9), (25, 23), (4, 23)], fill=(70, 73, 84))
    d.line([(8, 10), (5, 22)], fill=(110, 114, 126))
    return outline(img)


@lru_cache(None)
def arrow_down(col=(255, 210, 63)):
    img = Image.new('RGBA', (10, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((3, 0, 6, 8), fill=col); d.polygon([(0, 8), (9, 8), (5, 15), (4, 15)], fill=col)
    return outline(img)


def car_wing(fg, cx, gy, s, rise, dist=0.0, lights=False, sy=1.0, col='silver'):
    """The coupe with its rear wing (rear is on the left)."""
    blit(fg, up(wing(round(rise * 8) / 8), s), cx - 45 * s + 12 * s, gy - int(20 * s * sy))
    draw_car(fg, col, cx, s, y=gy, dist=dist, lights=lights, sx=1 / sy ** 0.3, sy=sy)


def arrows(fg, t, cx, top, n, k=1.0, s=7, spread=110, col=(255, 210, 63)):
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * spread
        y = top + 30 * ((t * 2.2 + i * 0.3) % 1)
        blit(fg, up(arrow_down(col), s), x, y, k, k, anchor='center')


# ================================================================== shot 1: hook, the invisible hand
def mph(t): return int(177 * oc(prog(t, 0.2, 1.1)))
PRESS = 0.6
def squash(t): return 1 - 0.07 * oc(prog(t, PRESS, 0.25)) + 0.02 * math.sin(t * 30) * (t > PRESS)
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.22)), (0.0, (540, 960, 1.22)), (PRESS, (540, 940, 1.32), 'io'), (2.3, (540, 920, 1.36), 'io')],
              kicks=[(0.25, 0.08, 540, 640), (PRESS, 0.2, 540, 900), (1.35, 0.1, 540, 640)], shakes=[(0.0, 2.3, 4), (PRESS, 0.3, 14)])


def shot_press(t):
    img = street(t, t * 2600); fg = layer()
    fx.speed_lines(fg, 1.0, int(t * 14) % 5, col=(200, 204, 220))
    sq = squash(t)
    car_wing(fg, 540, ROAD_Y, 6, 0.0, dist=t * 2600, lights=True, sy=sq)
    hy = lerp(560, ROAD_Y - 168 + 14 * (1 - sq) / 0.07, oc(prog(t, 0.1, PRESS - 0.1)))
    blit(fg, up(hand(int(120 + 30 * math.sin(t * 8)) // 10 * 10), 10), 540, hy, popin(t, 0.05, 0.3), popin(t, 0.05, 0.3), anchor='bottom')
    if t >= PRESS:
        fx.dust(fg, t, PRESS, 540, ROAD_Y, n=14, seed=3); fx.ring(fg, t, PRESS, 540, ROAD_Y - 40, GLOW, r1=420)
        arrows(fg, t, 540, ROAD_Y - 400, 4, popin(t, PRESS, 0.2), s=6, spread=300)
    k = popin(t, 0.2, 0.25)
    blit(fg, fx.big('badge', f'{mph(t)} MPH', '#ffd23f' if mph(t) == 177 else '#ffffff', '#1a1a2e', '#e8b923', s=7), 790, 760, k, k, 3, anchor='center')
    return CAM1.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, 0.05, 2.2, '860 kg of', RED, 400, 116, -3)
    title(cv, t, 0.3, 2.2, 'downforce.', RED, 540, 116, 2)
    title(cv, t, 8.6, 11.45, 'opens above 62 mph', YEL, 450, 100, -2)


# ================================================================== shot 2: the real car
P2 = Presenter([
    (2.2, dict(path=Track([(2.2, (1300, 300)), (2.55, (930, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.55, dict(ground=GROUND, squash=True, arms='point', point=(520, 780), look=(520, 780), expr='wow', face=None)),
    (3.95, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(2.25, (540, 860, 1.06)), (3.41, (520, 840, 1.12), 'io'), (4.65, (520, 840, 1.14), 'io')],
              kicks=[(2.4, 0.1, 520, 780), (2.78, 0.08, 520, 780), (3.95, 0.12, 760, 1100)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 2.3, 520, 780, GLOW, hold=True, r=640)
    photo(fg, t, 2.4, 9.0, 'gt3rs', 520, 780, 900, 0, -3, 'THE REAL CAR, 2022', fit=True)
    if t >= 3.41: fx.sparkles(fg, t, 520, 780, 800, 400, n=8, seed=21)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: 860 kg presses it down
def kg(t): return int(860 * oc(prog(t, 5.03, 0.8)))
DROP = 5.03
def wy(t): return lerp(-200, GROUND - 330, ic(prog(t, 4.75, DROP - 4.75)))
def sq3(t): return 1 - 0.08 * oc(prog(t, DROP, 0.2)) + 0.025 * math.sin((t - DROP) * 40) * math.exp(-(t - DROP) * 5) * (t > DROP)
P3 = Presenter([
    (4.6, dict(path=Track([(4.6, (-200, 300)), (4.95, (110, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (4.95, dict(ground=GROUND, squash=True, arms='shock', look=(560, 700), expr='shock', face=None)),
    (5.81, dict(arms='point', point=(560, 640), look=(560, 640), expr='wow')),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(4.65, (560, 880, 1.1)), (DROP, (560, 920, 1.18), 'io'), (7.8, (560, 900, 1.22), 'io')],
              kicks=[(DROP, 0.24, 560, 1000), (5.81, 0.1, 560, 600), (6.44, 0.12, 560, 1100)], shakes=[(DROP, 0.4, 16)])


def shot_weight(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    sq = sq3(t) if t >= DROP else 1.0
    car_wing(fg, 560, GROUND, 7, 0.0, sy=sq)
    fx.contact_shadow(fg, 560, GROUND, 620, s=7)
    y = wy(t) + (GROUND - 350 * sq - (GROUND - 350)) if t >= DROP else wy(t)
    blit(fg, up(weight_block(), 9), 560, y)
    if t >= DROP:
        fx.dust(fg, t, DROP, 560, GROUND, n=16, seed=31); fx.burst(fg, t, DROP, 560, GROUND - 330, GLOW, n=14, seed=32)
        k = popin(t, DROP, 0.25)
        blit(fg, fx.big('badge', f'{kg(t)} KG', '#ffd23f' if kg(t) == 860 else '#ffffff', '#1a1a2e', '#e8b923', s=10), 560, y - 140, k, k, -3, anchor='center')
    if t >= 6.44:
        arrows(fg, t, 560, GROUND - 120, 2, popin(t, 6.44, 0.2), s=6, spread=440, col=(90, 220, 120))
        fx.sparkles(fg, t, 560, 600, 700, 200, n=6, seed=33)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: the wing opens above 62 mph
OPEN = 10.1
def speed4(t): return int(lerp(30, 62, oc(prog(t, 8.0, OPEN - 8.0))) + 6 * oc(prog(t, OPEN, 1.4)))
def rise4(t): return oc(prog(t, OPEN, 0.45))
CAM4 = Camera(W, H, [(7.8, (540, 940, 1.16)), (8.28, (380, 960, 1.3), 'io'), (OPEN, (360, 940, 1.38), 'io'), (11.55, (520, 930, 1.2), 'io')],
              kicks=[(8.02, 0.08, 310, 1000), (8.6, 0.12, 330, 930), (OPEN, 0.24, 330, 900), (10.96, 0.1, 700, 700)], shakes=[(OPEN, 0.3, 10)])


def shot_wing(t):
    img = street(t, (t - 7.8) * 900); fg = layer()
    fx.speed_lines(fg, 0.4 + 0.5 * prog(t, 8.0, 3.0), int(t * 12) % 5, col=(200, 204, 220))
    car_wing(fg, 560, ROAD_Y, 6, rise4(t), dist=t * 1100, lights=True)
    dg.label(fg, t, 8.28, 'REAR WING', (560 - 45 * 6 + 22 * 6, ROAD_Y - 26 * 6), (250, 1010), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=9.8)
    v = speed4(t); k = popin(t, 7.95, 0.25) * (1 + 0.1 * math.exp(-(t - OPEN) * 6) * (t > OPEN))
    blit(fg, fx.big('badge', f'{v} MPH', '#ffd23f' if v >= 62 else '#ffffff', '#1a1a2e', '#e8b923', s=9), 430, 800, k, k, 3, anchor='center')
    if t >= OPEN:
        fx.burst(fg, t, OPEN, 330, ROAD_Y - 220, GLOW, n=14, seed=41); fx.ring(fg, t, OPEN, 330, ROAD_Y - 220, GLOW, r1=300)
        fx.sparkles(fg, t, 330, ROAD_Y - 260, 300, 160, n=6, seed=42)
    return CAM4.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 5: nearly full throttle
DASH = Dashboard()
def thr(t): return oc(prog(t, 11.79, 0.6)) * 0.95
CAM5 = Camera(W, H, [(11.55, (560, 900, 1.16)), (12.34, (560, 920, 1.24), 'io'), (13.5, (560, 920, 1.28), 'io')],
              kicks=[(11.79, 0.1, 560, 900), (12.34, 0.2, 760, 1080)], shakes=[(12.34, 1.1, 6)])


def shot_pedal(t):
    u = thr(t)
    img = DASH.frame(t, rpm_deg=210 - 215 * u + 3 * math.sin(t * 40) * u, speed_deg=150 - 120 * u, lcd=f'{int(u * 100):02d}%').convert('RGBA')
    fg = layer(); d = ImageDraw.Draw(fg)
    k = popin(t, 11.65, 0.25)
    if k > 0.02:                                    # throttle bar
        x0, y0, x1, y1 = 180, 1120, 900, 1200
        d.rectangle((x0 - 9, y0 - 9, x1 + 9, y1 + 9), fill=(26, 26, 46)); d.rectangle((x0, y0, x1, y1), fill=(40, 42, 52))
        d.rectangle((x0, y0, x0 + int((x1 - x0) * u) // S * S, y1), fill=(224, 48, 58) if u > 0.85 else (255, 210, 63))
        blit(fg, fx.big('label', 'THROTTLE', '#ffffff', s=7), 540, y0 - 50, k, k, anchor='center')
    if t >= 12.34:
        kb = fx.slam(t, 12.34) * popin(t, 12.34, 0.2)
        blit(fg, fx.big('badge', 'NEARLY FULL', '#e0303a', '#ffffff', '#a82028', s=8), 560, 560, kb, kb, -4 + 2 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 12.34, 560, 560, RED, n=14, seed=51)
    img.alpha_composite(fg)
    return CAM5.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 6: it cuts downforce by 30 percent
def df(t): return int(round(100 - 30 * oc(prog(t, 14.63, 0.9))))
P6 = Presenter([
    (13.45, dict(path=Track([(13.45, (1300, 300)), (13.8, (940, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (13.8, dict(ground=GROUND, squash=True, arms='point', point=(460, 700), look=(460, 700), expr='smile', face=None)),
    (15.52, dict(arms='cheer', point=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM6 = Camera(W, H, [(13.5, (540, 900, 1.1)), (14.63, (480, 860, 1.18), 'io'), (16.3, (500, 860, 1.22), 'io')],
              kicks=[(13.77, 0.1, 360, 900), (14.63, 0.12, 460, 620), (15.52, 0.24, 460, 480)], shakes=[(15.52, 0.3, 12)])


def shot_cut(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    car_wing(fg, 460, GROUND, 6, 1.0, sy=1 - 0.05 * df(t) / 100)
    fx.contact_shadow(fg, 460, GROUND, 540, s=6)
    n = 4 if df(t) > 85 else 3
    arrows(fg, t, 460, GROUND - 480, n, 0.6 + 0.4 * df(t) / 100, s=6, spread=130)
    k = popin(t, 13.6, 0.25)
    if k > 0.02:                                    # downforce bar
        x0, y0, x1, y1 = 160, 620, 760, 690
        d.rectangle((x0 - 9, y0 - 9, x1 + 9, y1 + 9), fill=(26, 26, 46)); d.rectangle((x0, y0, x1, y1), fill=(40, 42, 52))
        d.rectangle((x0, y0, x0 + int((x1 - x0) * df(t) / 100) // S * S, y1), fill=(255, 210, 63))
        if df(t) < 100: d.rectangle((x0 + int((x1 - x0) * df(t) / 100) // S * S, y0, x1, y1), fill=(120, 40, 46))
        blit(fg, fx.big('label', 'DOWNFORCE', '#ffffff', s=7), 460, y0 - 50, k, k, anchor='center')
    if t >= 15.52:
        kb = fx.slam(t, 15.52) * popin(t, 15.52, 0.2)
        blit(fg, fx.big('badge', '-30%', '#e0303a', '#ffffff', '#a82028', s=14), 640, 470, kb, kb, 6 + 2 * math.sin(t * 6), anchor='center')
        fx.ring(fg, t, 15.52, 640, 470, RED, r1=420); fx.burst(fg, t, 15.52, 640, 470, GLOW, n=16, seed=61)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(16.3, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_press), (2.25, shot_photo), (4.65, shot_weight), (7.8, shot_wing), (11.55, shot_pedal), (13.5, shot_cut), (16.3, shot_teaser)]
TRANS = {1: (2.25, 2.45, 'whip', dict(dx=1)), 2: (4.65, 4.85, 'whip', dict(dx=0, dy=1)), 3: (7.8, 8.0, 'push', None),
         4: (11.55, 11.75, 'iris', (560, 940)), 5: (13.5, 13.7, 'whip', dict(dx=1)), 6: (16.3, 16.5, 'whip', dict(dx=1))}
KEYCOL = {'177': YEL, 'porsche': YEL, 'gt3': YEL, '860': RED, 'downforce': RED, 'wing': YEL,
          'opens': YEL, '62': YEL, 'hour': YEL, 'nearly': YEL, 'full': RED, 'does': YEL, '30': RED}
CUES = [
    (0.0, 'vroom', 0.8), (0.05, 'whoosh', 0.5), (0.2, 'pop', 0.5)] + [(0.25 + k * 0.2, 'click', 0.3) for k in range(5)] + [
    (PRESS, 'boom', 0.5), (PRESS + 0.02, 'thump', 0.8), (1.35, 'ding', 0.6),
    (2.4, 'pop', 0.7), (2.42, 'sparkle', 0.5), (3.41, 'sparkle', 0.5), (3.95, 'pop', 0.4),
    (4.75, 'fall', 0.6), (DROP, 'crash', 0.5), (DROP + 0.02, 'thump', 0.9), (5.81, 'ding', 0.6), (6.44, 'pop', 0.5),
    (7.9, 'vroom', 0.6), (8.28, 'pop', 0.5), (OPEN, 'creak', 0.7), (OPEN + 0.05, 'ding', 0.7), (10.96, 'pop', 0.4),
    (11.79, 'vroom', 1.0), (12.34, 'stamp', 0.8),
    (13.6, 'pop', 0.5), (14.63, 'slide_down', 0.6), (15.52, 'stamp', 0.9), (15.54, 'sparkle', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
