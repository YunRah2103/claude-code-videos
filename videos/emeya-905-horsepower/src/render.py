"""Renders 'Emeya, 905 horsepower': up to 905 hp, a claimed sub-2.8 s 0-60, and a claimed 93 miles in five minutes.

Template: videos/ac-idle shot structure on shared/episode.py (as in plaid-two-seconds). Voiceover: clip 5 of
out/voiceover/full_voiceover.wav (shared/vo_split.py), aligned by align.py -> words.json. The acceleration and charging
figures are Lotus's claims ('claims', 'says'), shown with CLAIMED tags. The car and charger are generic pixel props
with no badges or lettering.
Shots:
  1 launch   0.00  hook: night street, the car launches off the line, the timer stops at 2.80; 'Under 2.8 seconds.'
  2 photo    2.95  framed real photo of a Lotus Emeya; CLAIMED tag; 0-60 MPH label; 'claims'
  3 power    5.75  the 905 HP counter fills; 2.8 S stopwatch slams down
  4 charge   7.70  garage: plugged in, the range counter adds 93 MI
  5 fast    10.20  charger close-up: 5 MIN clock, 350 KW label
  6 teaser  13.55  shared NEXT EPISODE ending
"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title, draw_car, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.props import charger, plug, bolt, stopwatch
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up

WORDS = kit.load_words(HERE)
DUR, END_T = 16.4, 13.6


def cable(fg, a, b, sag=60, col=(26, 27, 32)):
    d = ImageDraw.Draw(fg); pts = []
    for k in range(13):
        u = k / 12; x = lerp(a[0], b[0], u); y = lerp(a[1], b[1], u) + sag * math.sin(u * math.pi)
        pts.append((round(x / S) * S, round(y / S) * S))
    d.line(pts, fill=col, width=S + 3)


# ================================================================== shot 1: hook, the launch
GO = 0.1
def timer(t): return min(2.8, max(0.0, t - GO))
def car_x1(t): return 260 + 1500 * ic(prog(t, GO, 2.6)) ** 1.0
CAM1 = Camera(W, H, [(-1.0, (520, 980, 1.25)), (0.0, (520, 980, 1.25)), (0.6, (600, 1000, 1.32), 'io'), (2.95, (560, 960, 1.18), 'io')],
              kicks=[(GO, 0.22, 260, 1080), (1.18, 0.1, 540, 700), (2.9, 0.22, 540, 700)], shakes=[(GO, 0.5, 16), (2.9, 0.3, 10)])


def shot_launch(t):
    img = street(t, 2200 * ic(prog(t, GO, 1.2)) + max(0, t - GO - 1.2) * 1800); fg = layer(); d = ImageDraw.Draw(fg)
    sl = 120 - 2200 * ic(prog(t, GO, 1.2)) - max(0, t - GO - 1.2) * 1800       # start line drifts away with the street
    for k in range(10):
        for j in range(2):
            d.rectangle((sl + j * 18, ROAD_Y - 120 + k * 18, sl + j * 18 + 17, ROAD_Y - 103 + k * 18), fill=(240, 240, 244) if (k + j) % 2 else (26, 26, 46))
    x = min(car_x1(t), 760)
    sq = 1 - 0.05 * math.exp(-max(0, t - GO) * 8) * (t > GO)
    draw_car(fg, 'yellow', x, 4, y=ROAD_Y, dist=t * 2000, lights=True, sx=1 / sq, sy=sq, rot=2 * math.exp(-max(0, t - GO) * 5) * (t > GO))
    if t > GO:
        for k in range(5): fx.puff(fg, t, GO + k * 0.06, x - 170, ROAD_Y - 20, seed=10 + k, drift=(-320, -60), col=(200, 204, 214))
        fx.speed_lines(fg, min(1.0, (t - GO) * 1.5), int(t * 14) % 5, col=(200, 204, 220))
    k = popin(t, 0.0, 0.25) * (1 + 0.12 * math.exp(-(t - 2.9) * 6) * (t > 2.9))
    v = timer(t)
    blit(fg, up(stopwatch(v / 2.8 * 0.99), 6), 300, 870, k, k, -6, anchor='center')
    if t >= 2.9: fx.burst(fg, t, 2.9, 640, 880, GLOW, n=16, seed=11); fx.ring(fg, t, 2.9, 640, 880, GLOW, r1=420)
    blit(fg, fx.big('badge', f'{v:.2f} S', '#ffd23f' if v >= 2.8 else '#ffffff', '#1a1a2e', '#e8b923', s=10), 640, 880, k, k, 3, anchor='center')
    return CAM1.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, 0.05, 2.9, 'Under 2.8', RED, 390, 126, -3)
    title(cv, t, 0.3, 2.9, 'seconds.', RED, 540, 126, 2)
    title(cv, t, 3.3, 5.7, 'claims', GRN, 420, 130, 3)


# ================================================================== shot 2: the real car
P2 = Presenter([
    (2.9, dict(path=Track([(2.9, (1300, 300)), (3.25, (930, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (3.25, dict(ground=GROUND, squash=True, arms='shrug', look_camera=True, expr='smirk', face=None)),
    (4.34, dict(arms='point', point=(320, 1110), look=(320, 1110), expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(2.95, (540, 880, 1.06)), (4.34, (500, 900, 1.14), 'io'), (5.75, (500, 900, 1.16), 'io')],
              kicks=[(3.05, 0.1, 500, 780), (3.3, 0.14, 700, 1040), (4.34, 0.12, 320, 1110), (5.03, 0.08, 320, 1110)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 3.0, 500, 780, GLOW, hold=True, r=640)
    photo(fg, t, 3.05, 9.0, 'emeya', 500, 780, 900, 0, -3, 'THE REAL CAR', fit=True)
    if t >= 3.3:
        k = fx.slam(t, 3.3) * popin(t, 3.3, 0.2)
        blit(fg, fx.big('tag', 'CLAIMED', '#fff6e0', '#d6303a', s=9), 720, 1040, k, k, -8, anchor='center')
        fx.burst(fg, t, 3.3, 720, 1040, RED, n=10, seed=21)
    if t >= 4.34:
        k = popin(t, 4.34, 0.25)
        blit(fg, fx.big('badge', '0-60 MPH', '#ffffff', '#1a1a2e', '#d6d9e2', s=8), 320, 1110, k, k, 4, anchor='center')
        fx.sparkles(fg, t, 320, 1110, 420, 140, n=5, seed=22)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: 905 hp, under 2.8 s
def hp(t): return int(905 * oc(prog(t, 5.8, 1.0)))
P3 = Presenter([
    (5.7, dict(path=Track([(5.7, (-200, 300)), (6.05, (130, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='wow', face=1, ground=None)),
    (6.05, dict(ground=GROUND, squash=True, arms='point', point=(540, 640), look=(540, 640), expr='talk', face=None)),
    (6.76, dict(arms='cheer', point=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(5.75, (540, 880, 1.1)), (6.13, (540, 820, 1.2), 'io'), (7.7, (540, 840, 1.22), 'io')],
              kicks=[(5.82, 0.1, 540, 640), (6.13, 0.22, 640, 1000), (6.76, 0.12, 540, 640)], shakes=[(6.13, 0.3, 12)])


def shot_power(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    k = popin(t, 5.78, 0.25)
    if k > 0.02:                                    # power bar fills with the counter
        x0, y0, x1, y1 = 180, 760, 900, 840
        d.rectangle((x0 - 9, y0 - 9, x1 + 9, y1 + 9), fill=(26, 26, 46)); d.rectangle((x0, y0, x1, y1), fill=(40, 42, 52))
        d.rectangle((x0, y0, x0 + int((x1 - x0) * hp(t) / 905) // S * S, y1), fill=(255, 210, 63))
        for xx in range(x0 + 72, x1, 72): d.line([(xx, y0), (xx, y1)], fill=(26, 26, 46), width=3)
        blit(fg, fx.big('badge', f'{hp(t)} HP', '#ffd23f' if hp(t) == 905 else '#ffffff', '#1a1a2e', '#e8b923', s=12), 540, 620, k, k, -3, anchor='center')
        blit(fg, fx.big('tag', 'UP TO', '#fff6e0', '#1a1a2e', s=6), 250, 470, k, k, -10, anchor='center')
    if hp(t) == 905: fx.sparkles(fg, t, 540, 620, 760, 220, n=7, seed=31)
    if t >= 6.13:
        ks = fx.slam(t, 6.13) * popin(t, 6.13, 0.2)
        blit(fg, up(stopwatch(0.93), 6), 660, 1030, ks, ks, 6)
        blit(fg, fx.big('badge', '2.8 S', '#e0303a', '#ffffff', '#a82028', s=10), 660, 1110, ks, ks, -4, anchor='center')
        fx.burst(fg, t, 6.13, 660, 1000, RED, n=14, seed=32); fx.dust(fg, t, 6.13, 660, 1130, n=10, seed=33)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: 93 miles of range
CH_X, CAR4 = 190, 690
PORT = (CAR4 - 44 * 7 + 40, GROUND - 190)
def miles(t): return int(93 * oc(prog(t, 8.66, 1.2)))
P4 = Presenter([
    (7.65, dict(path=Track([(7.65, (1300, 300)), (8.0, (930, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (8.0, dict(ground=GROUND, squash=True, arms='point', point=(PORT[0], PORT[1]), look=(PORT[0], PORT[1]), expr='smile', face=None)),
    (9.75, dict(arms='thumb', point=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(7.7, (540, 940, 1.1)), (8.66, (520, 940, 1.16), 'io'), (10.2, (540, 920, 1.14), 'io')],
              kicks=[(8.08, 0.1, 540, 900), (8.66, 0.14, PORT[0], PORT[1]), (8.9, 0.16, 600, 700), (9.75, 0.1, 600, 700)])


def shot_charge(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    on = t >= 8.66
    blit(fg, up(charger(0.5 + 0.5 * math.sin(t * 9) if on else 0.2, 3 if on else 1), 7), CH_X, GROUND)
    fx.contact_shadow(fg, CH_X, GROUND, 170, s=7)
    draw_car(fg, 'yellow', CAR4, 7, flip=True)
    fx.contact_shadow(fg, CAR4, GROUND, 600, s=7)
    u = oc(prog(t, 8.3, 0.36)); hold = (CH_X + 30, GROUND - 190)
    px, py = lerp(hold[0], PORT[0], u), lerp(hold[1], PORT[1], u) - 120 * math.sin(u * math.pi)
    cable(fg, (CH_X + 70, GROUND - 120), (px - 40, py), sag=90 * (1 - 0.5 * u))
    blit(fg, up(plug(), 7), px, py, anchor='center')
    if on:
        for k in range(3):
            v = ((t - 8.66) * 1.4 + k / 3) % 1
            blit(fg, up(bolt(), 4), lerp(CH_X + 70, PORT[0] - 40, v), lerp(GROUND - 120, PORT[1], v) + 70 * math.sin(v * math.pi), anchor='center')
        k = popin(t, 8.9, 0.25) * (1 + 0.1 * (miles(t) == 93) * math.exp(-(t - 9.86) * 5))
        blit(fg, fx.big('badge', f'+{miles(t)} MI', '#ffd23f' if miles(t) == 93 else '#ffffff', '#1a1a2e', '#e8b923', s=11), 600, 700, k, k, -3, anchor='center')
        if miles(t) == 93: fx.gsparkles(fg, t, 600, 700, 600, 200, n=7, seed=41)
    if t >= 9.75: dg.label(fg, t, 9.75, 'RANGE', (CAR4, GROUND - 330), (330, 860), '#5adc78', '#1a1a2e', '#3fb85f', s=7)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: five minutes, 350 kW
CAM5 = Camera(W, H, [(10.2, (530, 820, 1.16)), (11.52, (520, 800, 1.22), 'io'), (13.6, (530, 820, 1.26), 'io')],
              kicks=[(10.38, 0.16, 760, 660), (11.52, 0.2, 300, 520), (12.61, 0.1, 300, 900)], shakes=[(11.52, 0.3, 10)])


def shot_fast(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    blit(fg, up(charger(0.5 + 0.5 * math.sin(t * 9), int(t * 4) % 4), 12), 300, GROUND)
    fx.contact_shadow(fg, 300, GROUND, 280, s=12)
    if t >= 10.38:
        k = fx.slam(t, 10.38) * popin(t, 10.38, 0.2)
        blit(fg, up(stopwatch(prog(t, 10.38, 2.6) * 0.99), 8), 720, 760, k, k, 6, anchor='center')
        blit(fg, fx.big('badge', '5 MIN', '#ffffff', '#1a1a2e', '#d6d9e2', s=9), 720, 1000, k, k, -3, anchor='center')
        fx.burst(fg, t, 10.38, 720, 760, GLOW, n=12, seed=51)
    dg.label(fg, t, 11.52, '350 KW', (300, GROUND - 520), (330, 420), '#ffd23f', '#1a1a2e', '#e8b923', s=9)
    if t >= 11.52:
        for i in range(3): blit(fg, up(bolt(), 7), 150 + i * 150, 640 - 20 * math.sin(t * 7 + i), 1, 1, 10 * math.sin(t * 5 + i))
        fx.sparkles(fg, t, 330, 480, 600, 200, n=6, seed=52)
    if t >= 12.61: fx.ring(fg, t, 12.61, 300, 900, GLOW, r1=360)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(13.55, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_launch), (2.95, shot_photo), (5.75, shot_power), (7.7, shot_charge), (10.2, shot_fast), (13.55, shot_teaser)]
TRANS = {1: (2.95, 3.15, 'whip', dict(dx=1)), 2: (5.75, 5.95, 'iris', (540, 640)), 3: (7.7, 7.9, 'push', None),
         4: (10.2, 10.4, 'whip', dict(dx=0, dy=1)), 5: (13.55, 13.75, 'whip', dict(dx=1))}
KEYCOL = {'emeya': YEL, 'up': YEL, '905': YEL, '0': YEL, 'claims': GRN, '60': YEL, 'hour': YEL, '2.8': RED, 'says': GRN,
          'adds': YEL, '93': YEL, 'range': GRN, 'minutes': YEL, '350': YEL}
CUES = [
    (0.0, 'pop', 0.5), (GO, 'vroom', 1.0), (GO + 0.05, 'screech', 0.5)] + [(0.1 + k * 0.4, 'click', 0.35) for k in range(7)] + [
    (1.18, 'whoosh', 0.4), (2.9, 'ding', 0.9), (2.92, 'sparkle', 0.6),
    (3.05, 'pop', 0.7), (3.3, 'stamp', 0.8), (4.34, 'pop', 0.6),
    (5.82, 'slide_down', 0.4)] + [(5.85 + k * 0.18, 'click', 0.3) for k in range(5)] + [(6.13, 'stamp', 0.9), (6.76, 'ding', 0.6),
    (8.0, 'thump', 0.4), (8.66, 'click', 0.9), (8.9, 'pop', 0.6)] + [(9.0 + k * 0.2, 'click', 0.3) for k in range(4)] + [(9.86, 'ding', 0.6),
    (10.38, 'stamp', 0.7), (11.52, 'pop', 0.7), (11.55, 'sparkle', 0.6), (12.61, 'whoosh', 0.4),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='yellow', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
