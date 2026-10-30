"""Renders 'BYD, 400 km in 5 minutes': a claimed megawatt charger, 1,000 kW, twice a rival's peak.

Template: videos/ac-idle shot structure on shared/episode.py (as in plaid-two-seconds). Voiceover: clip 1 of
out/voiceover/full_voiceover.wav (shared/vo_split.py), aligned by align.py -> words.json. All figures are BYD's
claims (CLAIMED stamp, 'claims' title). Charger and cars are generic pixel props with no badges or lettering.
Shots:
  1 plug     0.00  hook: a pixel charger plugs into the car, the range counter jumps to 400 KM; '400 km in 5 minutes'
  2 photo    3.25  framed real photo of BYD's megawatt charging site; 400 KM and 5 MIN badges pop
  3 power    6.35  power columns: 1,000 kW label, 2X slam, the rival's peak fills to half
  4 claims  10.95  the 1,000 kW badge gets a CLAIMED stamp; 'claims'
  5 race    13.45  night street: two charged cars race; RACE IS ON
  6 teaser  16.25  shared NEXT EPISODE ending
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
DUR, END_T = 18.0, 16.3


def cable(fg, a, b, sag=60, col=(26, 27, 32)):
    """Charging cable: a sagging pixel line from a to b."""
    d = ImageDraw.Draw(fg); pts = []
    for k in range(13):
        u = k / 12; x = lerp(a[0], b[0], u); y = lerp(a[1], b[1], u) + sag * math.sin(u * math.pi)
        pts.append((round(x / S) * S, round(y / S) * S))
    d.line(pts, fill=col, width=S + 3)


# ================================================================== shot 1: plug in, range jumps
CH_X, CAR1 = 200, 700
PORT = (CAR1 - 44 * 7 + 40, GROUND - 190)
PLUG_T = 0.35
def km(t): return int(400 * oc(prog(t, 0.6, 2.0)))
P1 = Presenter([
    (1.85, dict(path=Track([(1.85, (1300, 200)), (2.2, (930, GROUND - 10), 'oc')]), size=6, legs='auto', arms='fly', expr='wow', face=-1, ground=None)),
    (2.2, dict(ground=GROUND - 10, squash=True, arms='point', point=(CH_X, GROUND - 300), look=(CH_X, GROUND - 300), expr='grin', face=None)),
], words=WORDS, base_size=6)
CAM1 = Camera(W, H, [(-1.0, (520, 940, 1.22)), (0.0, (520, 940, 1.22)), (PLUG_T, (430, 960, 1.3), 'io'), (2.6, (560, 880, 1.1), 'io'), (3.3, (560, 880, 1.14))],
              kicks=[(PLUG_T, 0.14, PORT[0], PORT[1]), (1.98, 0.08, CH_X, 900), (2.6, 0.2, 640, 820)], shakes=[(PLUG_T, 0.2, 8), (2.6, 0.3, 12)])


def shot_plug(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    on = t >= PLUG_T
    blit(fg, up(charger(0.5 + 0.5 * math.sin(t * 9) if on else 0.0, min(3, int(max(0, t - PLUG_T) * 4))), 7), CH_X, GROUND)
    fx.contact_shadow(fg, CH_X, GROUND, 170, s=7)
    draw_car(fg, 'blue', CAR1, 7, flip=True, sy=1 + 0.01 * math.sin(t * 4))
    fx.contact_shadow(fg, CAR1, GROUND, 600, s=7)
    hold = (CH_X + 30, GROUND - 190)
    u = oc(prog(t, 0.05, PLUG_T - 0.05))
    px, py = lerp(hold[0], PORT[0], u), lerp(hold[1], PORT[1], u) - 140 * math.sin(u * math.pi)
    cable(fg, (CH_X + 70, GROUND - 120), (px - 40, py), sag=90 * (1 - 0.5 * u))
    blit(fg, up(plug(), 7), px, py, anchor='center')
    if on:
        for k in range(3):                             # bolts run down the cable
            v = ((t - PLUG_T) * 1.4 + k / 3) % 1
            bx = lerp(CH_X + 70, PORT[0] - 40, v); by = lerp(GROUND - 120, PORT[1], v) + 70 * math.sin(v * math.pi)
            blit(fg, up(bolt(), 4), bx, by, anchor='center')
        fx.burst(fg, t, PLUG_T, PORT[0], PORT[1], GLOW, n=10, r0=40, r1=200, seed=4)
    if t >= 0.6:
        k = popin(t, 0.6, 0.25) * (1 + 0.08 * (km(t) == 400) * math.exp(-(t - 2.6) * 5))
        col = '#ffd23f' if km(t) == 400 else '#ffffff'
        blit(fg, fx.big('badge', f'{km(t)} KM', col, '#1a1a2e', '#d6d9e2', s=11), CAR1 - 60, GROUND - 440, k, k, -3, anchor='center')
    if t >= 2.6:
        fx.ring(fg, t, 2.6, CAR1 - 60, GROUND - 440, GLOW, r1=420); fx.burst(fg, t, 2.6, CAR1 - 60, GROUND - 440, GLOW, n=16, seed=5)
        fx.sparkles(fg, t, CAR1 - 60, GROUND - 440, 600, 200, n=7, seed=6)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 3.15, '400 km in', YEL, 380, 130, -3)
    title(cv, t, 0.3, 3.15, '5 minutes', YEL, 530, 130, 2)
    title(cv, t, 11.03, 13.4, 'claims', RED, 400, 130, 3)


# ================================================================== shot 2: the real charger
P2 = Presenter([
    (3.2, dict(path=Track([(3.2, (1250, 300)), (3.55, (940, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (3.55, dict(ground=GROUND, squash=True, arms='point', point=(540, 760), look=(540, 760), expr='smile', face=None)),
    (5.21, dict(arms='cheer', point=None, look=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(3.25, (540, 860, 1.06)), (3.88, (520, 900, 1.12), 'io'), (6.35, (540, 900, 1.16), 'io')],
              kicks=[(3.4, 0.1, 540, 760), (3.88, 0.1, 300, 1080), (5.21, 0.12, 640, 1080)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 3.3, 540, 760, GLOW, hold=True, r=620)
    photo(fg, t, 3.4, 9.0, 'charger', 540, 760, 900, 0, -3, 'A MEGAWATT CHARGING SITE', fit=True)
    if t >= 3.88:
        k = popin(t, 3.88, 0.25)
        blit(fg, fx.big('badge', '400 KM', '#ffd23f', '#1a1a2e', '#e8b923', s=10), 260, 1130, k, k, -4, anchor='center')
        fx.burst(fg, t, 3.88, 260, 1130, GLOW, n=10, seed=21)
    if t >= 5.21:
        k = fx.slam(t, 5.21) * popin(t, 5.21, 0.2)
        blit(fg, up(stopwatch(prog(t, 5.21, 1.0) * 0.99), 5), 640, 1080, k, k, 5, anchor='bottom')
        blit(fg, fx.big('badge', '5 MIN', '#ffffff', '#1a1a2e', '#d6d9e2', s=9), 640, 1130, k, k, 3, anchor='center')
        fx.sparkles(fg, t, 450, 1100, 600, 180, n=6, seed=22)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: 1,000 kW, twice the rival's peak
COL = ((360, 700), (720, 350))
def fill(t, i): return oc(prog(t, 6.68, 1.2)) if i == 0 else oc(prog(t, 9.38, 0.9))
P3 = Presenter([
    (6.3, dict(path=Track([(6.3, (-200, 400)), (6.65, (120, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (6.65, dict(ground=GROUND, squash=True, arms='point', point=(360, 500), look=(360, 500), expr='wow', face=None)),
    (9.38, dict(arms='point', point=(720, 830), look=(720, 830), expr='smirk')),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(6.35, (540, 900, 1.08)), (8.19, (480, 760, 1.16), 'io'), (9.38, (600, 900, 1.12), 'io'), (11.0, (600, 900, 1.14))],
              kicks=[(6.68, 0.1, 360, 1000), (7.85, 0.1, 360, 480), (8.19, 0.22, 540, 420), (9.38, 0.1, 720, 830)], shakes=[(8.19, 0.3, 12)])


def shot_power(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    for i, (x, hmax) in enumerate(COL):
        k = popin(t, 6.45 + i * 0.12, 0.25)
        if k <= 0.02: continue
        hgt = int(hmax * fill(t, i)) // S * S
        d.rectangle((x - 99, GROUND - hmax - 9, x + 99, GROUND), fill=(26, 26, 46))
        d.rectangle((x - 90, GROUND - hmax, x + 90, GROUND - 9), fill=(40, 42, 52))
        top = GROUND - 9 - hgt
        c1, c2 = ((255, 210, 63), (255, 238, 160)) if i == 0 else ((176, 182, 192), (222, 228, 236))
        if hgt > 0:
            d.rectangle((x - 90, top, x + 90, GROUND - 9), fill=c1); d.rectangle((x - 72, top + 9, x - 54, GROUND - 18), fill=c2)
        if i == 0 and 0 < fill(t, 0) < 1 or (i == 0 and t > 7.9):
            blit(fg, up(bolt(), 6), x + 4 * math.sin(t * 20), top - 20 - 10 * math.sin(t * 7), 1, 1, 8 * math.sin(t * 5))
    dg.label(fg, t, 7.29, '1,000 KW', (360, GROUND - 720), (360, 360), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    if t >= 8.19:
        k = fx.slam(t, 8.19) * popin(t, 8.19, 0.2)
        blit(fg, fx.big('badge', '2X', '#e0303a', '#ffffff', '#a82028', s=14), 740, 560, k, k, 8 + 3 * math.sin(t * 6), anchor='center')
        fx.ring(fg, t, 8.19, 740, 560, RED, r1=400); fx.burst(fg, t, 8.19, 740, 560, GLOW, n=16, seed=31)
    if t >= 9.38: dg.label(fg, t, 9.5, 'RIVAL PEAK', (720, GROUND - 360), (800, 740), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    if fill(t, 0) >= 1: fx.sparkles(fg, t, 360, GROUND - 600, 300, 400, n=6, seed=32)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: claimed
P4 = Presenter([
    (10.95, dict(path=Track([(10.95, (860, GROUND))]), size=8, legs='stand', arms='talkB', look=(420, 800), expr='talk', face=-1, ground=GROUND)),
    (11.48, dict(arms='shrug', look=None, look_camera=True, expr='smirk', squash=True)),
    (12.6, dict(arms='point', point=(420, 760), look=(420, 760), expr='wow', squash=True)),
], words=WORDS, base_size=8)
CAM4 = Camera(W, H, [(10.95, (540, 880, 1.2)), (12.6, (500, 840, 1.3), 'io'), (13.45, (500, 840, 1.34))],
              kicks=[(11.03, 0.1, 420, 780), (11.48, 0.08, 860, 900), (12.6, 0.24, 420, 760)], shakes=[(12.6, 0.3, 14)])


def shot_claim(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 11.0, 0.25)
    blit(fg, fx.big('badge', '1,000 KW', '#ffd23f', '#1a1a2e', '#e8b923', s=12), 420, 800, k, k, -3 + 2 * math.sin(t * 4), anchor='center')
    blit(fg, up(bolt(), 8), 420 + 300, 640, k, k, 12 * math.sin(t * 5), anchor='center')
    for i in range(2):
        if t >= 11.48 + i * 0.12:
            kq = popin(t, 11.48 + i * 0.12, 0.25)
            blit(fg, fx.big('glyph', '?', '#e0303a', s=12), 760 + i * 120, 620 - i * 60, kq, kq, 10 * math.sin(t * 6 + i), anchor='center')
    if t >= 12.6: fx.stamp_at(fg, t, 12.6, 'CLAIMED', 420, 820, rot=-10, s=11)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the race to charge faster
CAM5 = Camera(W, H, [(13.45, (540, 980, 1.18)), (14.82, (620, 1000, 1.26), 'io'), (16.3, (560, 980, 1.2), 'io')],
              kicks=[(14.1, 0.14, 540, 640), (14.82, 0.2, 640, 1050)], shakes=[(14.82, 0.4, 10)])
def race_x(t, i): return lerp(-250, 760 if i else 520, oc(prog(t, 13.5 + 0.1 * i, 0.9))) + (0 if t < 14.82 else (180 if i == 0 else -60) * io(prog(t, 14.82, 0.8)))


def shot_race(t):
    img = street(t, (t - 13.45) * 1500); fg = layer()
    for i, col in ((1, 'red'), (0, 'blue')):
        x = race_x(t, i); y = ROAD_Y - 90 * i
        draw_car(fg, col, x, 4, y=y, dist=t * 1500, lights=True)
        blit(fg, up(bolt(), 5), x, y - 230 - 10 * math.sin(t * 8 + i), 1, 1, 10 * math.sin(t * 6 + i))
        fx.puff(fg, t, 13.6 + i * 0.1, x - 180, y - 20, seed=60 + i, drift=(-300, -40), col=(200, 204, 214))
    fx.speed_lines(fg, 0.8 + 0.2 * (t > 14.82), int(t * 12) % 5, col=(200, 204, 220))
    if t >= 14.1:
        k = popin(t, 14.1, 0.25)
        blit(fg, fx.big('badge', 'RACE IS ON', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 540, 620, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 14.1, 540, 620, GLOW, n=14, seed=61); fx.sparkles(fg, t, 540, 620, 760, 220, n=7, seed=62)
    if t >= 14.82: fx.ring(fg, t, 14.82, 640, 1000, GLOW, r1=520)
    return CAM5.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


shot_teaser, TEASE_CUES = kit.teaser(16.25, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_plug), (3.25, shot_photo), (6.35, shot_power), (10.95, shot_claim), (13.45, shot_race), (16.25, shot_teaser)]
TRANS = {1: (3.25, 3.45, 'whip', dict(dx=1)), 2: (6.35, 6.55, 'push', None), 3: (10.95, 11.15, 'iris', (420, 800)),
         4: (13.45, 13.65, 'whip', dict(dx=0, dy=1)), 5: (16.25, 16.45, 'whip', dict(dx=1))}
KEYCOL = {'byd': YEL, 'megawatt': YEL, 'add': GRN, '400': YEL, 'five': YEL, '1,000': YEL, 'twice': GRN, 'power': YEL,
          'supercharger': YEL, 'claimed': RED, 'course': RED, 'race': YEL, 'faster': GRN, 'on': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (0.3, 'pop', 0.4), (PLUG_T, 'click', 0.9), (PLUG_T + 0.02, 'thump', 0.5),
    (0.6, 'pop', 0.5)] + [(0.7 + k * 0.32, 'click', 0.35) for k in range(6)] + [
    (1.9, 'whoosh', 0.4), (2.2, 'thump', 0.4), (2.6, 'ding', 0.9), (2.62, 'sparkle', 0.7),
    (3.4, 'pop', 0.7), (3.42, 'sparkle', 0.5), (3.88, 'pop', 0.6), (5.21, 'stamp', 0.6), (5.25, 'click', 0.5),
    (6.45, 'pop', 0.5), (6.57, 'pop', 0.5), (6.68, 'slide_down', 0.4), (7.29, 'pop', 0.6), (7.9, 'ding', 0.5),
    (8.19, 'boom', 0.45), (8.21, 'stamp', 0.8), (9.38, 'slide_down', 0.4), (9.5, 'pop', 0.5),
    (11.03, 'pop', 0.6), (11.48, 'pop', 0.5), (11.6, 'pop', 0.5), (12.6, 'stamp', 0.9),
    (13.5, 'vroom', 0.9), (14.1, 'pop', 0.7), (14.12, 'sparkle', 0.6), (14.82, 'vroom', 0.7), (14.84, 'whoosh', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
