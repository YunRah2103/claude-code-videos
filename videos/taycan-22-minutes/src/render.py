"""Renders 'Taycan, 22 minutes': reportedly the first production car with an 800-volt system; in one test it charged
5 to 80 percent in about 22 minutes on a 270 kW charger.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, rev counter, mixer). Word times
come from align.py -> words.json (aligned on out/taycan-22-minutes/vo_final.wav, the audio that ships). The car is
a generic white pixel saloon with no badges or lettering; the real car appears only in the framed Commons photo.
'Reportedly' gets a REPORTEDLY tag on screen.
Shots:
  1 fill     0.00  a cable plugs into a battery that fills fast; REPORTEDLY tag; '22 minutes.'
  2 photo    2.60  garage: white saloon, the framed real photo (a Taycan at a charging hub), 800 V label
  3 charge   5.00  fast charger and car: 5% -> 80%, then a 22 MIN clock badge slams
  4 kw       9.20  push in on the charger: 270 kW label, charge running down the cable; '270 kilowatt'
  5 slow    11.60  slow wallbox vs fast charger: red X, green tick; 'slow charger'
  6 teaser  14.90  shared NEXT EPISODE ending
"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up
from pixanim.autos import ev, battery, bolt, charger, wallbox, plug, cable

WORDS = kit.load_words(HERE)
DUR, END_T = 16.9, 14.94


def charge_dots(d, a, b, t, t0, sag=60, n=4, speed=1.6):
    for i in range(n):
        u = ((t - t0) * speed + i / n) % 1
        x, y = lerp(a[0], b[0], u), lerp(a[1], b[1], u) + sag * math.sin(math.pi * u)
        d.rectangle((x - 9, y - 9, x + 9, y + 9), fill=(255, 210, 63)); d.rectangle((x - 4, y - 4, x + 4, y + 4), fill=(255, 250, 200))


# ================================================================== shot 1: hook, the fast fill
CLICK = 0.3
def pct(t): return int(round(5 + 75 * io(prog(t, 0.35, 1.75))))
CAM1 = Camera(W, H, [(-1.0, (540, 980, 1.16)), (0.0, (540, 980, 1.16)), (CLICK, (540, 900, 1.24), 'io'), (2.1, (540, 960, 1.18), 'io'), (2.6, (540, 960, 1.2))],
              kicks=[(CLICK, 0.18, 540, 700), (2.1, 0.2, 540, 1000)], shakes=[(CLICK, 0.2, 8), (2.1, 0.3, 12)])


def shot_fill(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    p = pct(t)
    k = popin(t, 0.0, 0.25)
    blit(fg, up(battery(round(p / 10) / 10), 10), 540, 950, k, k, 0, anchor='center')
    u = oc(prog(t, 0.0, CLICK))                                               # plug drops onto the terminal
    px, py = lerp(1000, 540, u), lerp(460, 640, u) - 120 * math.sin(math.pi * u)
    d = ImageDraw.Draw(fg)
    cable(d, (1200, 380), (px + 40, py), sag=80, w=18, col=(26, 26, 46)); cable(d, (1200, 380), (px + 40, py), sag=80, w=10, col=(44, 46, 58))
    blit(fg, up(plug(), 7).rotate(-90, expand=True), px, py, 1, 1, 0, anchor='center')
    if t >= CLICK:
        fx.ring(fg, t, CLICK, 540, 660, (60, 220, 110), r1=260); fx.burst(fg, t, CLICK, 540, 660, GLOW, n=10, seed=2)
        for i in range(3):
            v = ((t - CLICK) * 2.2 + i / 3) % 1
            blit(fg, up(bolt(), 6), 540 + 160 * math.sin(i * 2.1 + t * 3), lerp(700, 1220, v), 1, 1, 0, anchor='center')
        kk = popin(t, 0.4, 0.2) * (fx.slam(t, 2.1) if t >= 2.1 else 1)
        blit(fg, fx.big('badge', f'{p}%', '#7fe3a0' if p >= 80 else '#ffffff', '#1a1a2e', '#3cc85a' if p >= 80 else '#d6d9e2', s=10), 540, 950, kk, kk, -3, anchor='center')
    if t >= 2.1: fx.gsparkles(fg, t, 540, 950, 600, 500, n=8, seed=3)
    if t >= 1.39:
        kt = popin(t, 1.39, 0.25)
        blit(fg, fx.big('tag', 'REPORTEDLY', '#fff6e0', '#d6303a', s=6), 700, 700, kt, kt, -6 + 2 * math.sin(t * 4), anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.5, '22 minutes.', RED, 470, 150, -3)
    title(cv, t, 9.4, 11.5, '270 kilowatt', YEL, 470, 120, 2)
    title(cv, t, 12.77, 14.8, 'slow charger', GRN, 470, 120, -2)
    photo(cv, t, 2.75, 4.95, 'taycan', 540, 590, 720, rot=3, label='THE REAL CAR, CHARGING', hq=True)


# ================================================================== shot 2: the real car, 800 volts
P2 = Presenter([
    (2.55, dict(path=Track([(2.55, (-200, 500)), (2.95, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (2.95, dict(ground=GROUND, squash=True, arms='point', point=(540, 620), look=(540, 620), expr='smile', face=None)),
    (3.36, dict(arms='point', point=(800, 1060), look=(800, 1060), expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.6, (540, 960, 1.08)), (4.05, (560, 980, 1.14), 'io'), (5.0, (560, 980, 1.16))],
              kicks=[(2.8, 0.08, 540, 620), (3.36, 0.14, 800, 1060)], shakes=[(3.36, 0.2, 8)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 600, GROUND, 560, s=6)
    blit(fg, up(ev('sport', 0, True, 0.6), 6), 600, GROUND)
    if t >= 3.36:
        k = fx.slam(t, 3.36) * popin(t, 3.36, 0.2)
        blit(fg, fx.big('badge', '800 V', '#ffd23f', '#1a1a2e', '#e8b923', s=9), 800, 1090, k, k, 4, anchor='center')
        fx.burst(fg, t, 3.36, 800, 1090, GLOW, n=14, seed=21)
        for i in range(2): blit(fg, up(bolt(), 6), 640 + i * 340, 960 + 10 * math.sin(t * 9 + i), k, k, 0, anchor='center')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shots 3-4: the fast charger
CHX = 880                                               # charger x; its holster sits at grid (24, 46)
CAR_X = 380
PORT = (CAR_X - 52 * 6 + 86 * 6, GROUND - (38 - 16) * 6)
HOLSTER = (CHX - 16 * 8 + 24 * 8, GROUND - (88 - 46) * 8)
def lvl(t): return 0.05 + 0.75 * io(prog(t, 6.49, 1.6))


def charger_scene(fg, t, plate_t):
    fx.contact_shadow(fg, CAR_X, GROUND, 560, s=6)
    blit(fg, up(ev('sport', 0, True, 1.0), 6), CAR_X, GROUND)
    blit(fg, up(charger(1, '270' if t >= plate_t else ''), 8), CHX, GROUND)
    d = ImageDraw.Draw(fg)
    cable(d, HOLSTER, PORT, sag=90, w=18, col=(26, 26, 46)); cable(d, HOLSTER, PORT, sag=90, w=10, col=(44, 46, 58))
    charge_dots(d, HOLSTER, PORT, t, 5.0, sag=90, speed=1.2 if t < 9.4 else 2.2)


P3 = Presenter([
    (5.0, dict(path=Track([(5.0, (-200, 400)), (5.4, (130, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (5.4, dict(ground=GROUND, squash=True, arms='point', point=(380, 640), look=(380, 640), expr='smile', face=None)),
    (8.51, dict(arms='shock', point=None, look=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(5.0, (540, 960, 1.06)), (6.49, (480, 900, 1.12), 'io'), (8.1, (540, 900, 1.12), 'io'), (9.2, (560, 920, 1.14))],
              kicks=[(6.49, 0.1, 380, 640), (6.95, 0.12, 380, 640), (8.1, 0.12, 640, 480), (8.51, 0.2, 640, 480)], shakes=[(8.51, 0.3, 12)])


def shot_charge(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    charger_scene(fg, t, 99)
    k = popin(t, 6.0, 0.25)
    blit(fg, up(battery(round(lvl(t) * 10) / 10), 6), 380, 640, k, k, 3 * math.sin(t * 3), anchor='center')
    for txt, t0, (x, y), col in (('5%', 6.49, (200, 520), '#ffffff'), ('80%', 6.95, (560, 520), '#7fe3a0')):
        if t >= t0:
            kk = popin(t, t0, 0.25) * popout(t, 8.0)
            blit(fg, fx.big('badge', txt, col, '#1a1a2e', '#d6d9e2', s=8), x, y, kk, kk, -3, anchor='center')
            fx.burst(fg, t, t0, x, y, GLOW, n=8, r0=60, r1=200, seed=int(t0 * 10))
    if t >= 8.1:
        kk = popin(t, 8.1, 0.25) * (fx.slam(t, 8.51) if t >= 8.51 else 1)
        blit(fg, fx.big('badge', '22 MIN', '#ffd23f', '#1a1a2e', '#e8b923', s=12), 640, 480, kk, kk, -3, anchor='center')
    if t >= 8.51: fx.burst(fg, t, 8.51, 640, 480, RED, n=16, seed=31); fx.sparkles(fg, t, 640, 480, 700, 200, n=8, seed=32)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


CAM4 = Camera(W, H, [(9.2, (700, 900, 1.2)), (9.4, (760, 820, 1.34), 'io'), (11.6, (720, 860, 1.3), 'io')],
              kicks=[(9.4, 0.2, CHX, 820), (10.14, 0.1, CHX, 640), (10.54, 0.1, 640, 1100)], shakes=[(9.4, 0.25, 10)])


def shot_kw(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    charger_scene(fg, t, 9.4)
    fx.rays(fg, t, 9.4, CHX, GROUND - 400, GLOW, life=0.6)
    dg.label(fg, t, 9.4, '270 KW', (CHX, GROUND - 210), (CHX - 260, GROUND - 520), '#ffd23f', '#1a1a2e', '#e8b923', s=10)
    if t >= 9.4: fx.sparkles(fg, t, CHX, GROUND - 400, 400, 400, n=8, seed=41)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: slow vs fast
SX, FX = 300, 790
P5 = Presenter([
    (11.6, dict(path=Track([(11.6, (SX + 130, GROUND))]), size=6, legs='sit', arms='think', look=(SX, GROUND - 300), expr='sad', face=-1, ground=GROUND)),
    (12.77, dict(arms='shrug', expr='talk', look_camera=True)),
    (13.72, dict(arms='point', point=(FX, GROUND - 400), look=(FX, GROUND - 400), expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM5 = Camera(W, H, [(11.6, (540, 960, 1.04)), (12.77, (420, 980, 1.12), 'io'), (13.72, (640, 960, 1.12), 'io'), (14.95, (560, 960, 1.08), 'io')],
              kicks=[(12.77, 0.16, SX, GROUND - 330), (13.72, 0.16, FX, GROUND - 450)])


def shot_slow(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    blit(fg, up(wallbox(), 7), SX, GROUND)
    blit(fg, up(charger(1, '270'), 7), FX, GROUND)
    if 11.8 < t < 12.77 or t >= 12.77:                                         # 'zzz' while he waits at the slow one
        for i in range(3):
            u = ((t - 11.8) * 0.8 + i / 3) % 1
            blit(fg, up(kit_text('Z'), 5 + i), SX + 150 + 60 * u, GROUND - 520 - 260 * u, 1, 1, 0, anchor='center')
    if t >= 12.77:
        k = fx.slam(t, 12.77) * popin(t, 12.77, 0.2)
        blit(fg, fx.big('xmark', s=12), SX, GROUND - 330, k, k, 0, anchor='center'); fx.burst(fg, t, 12.77, SX, GROUND - 330, RED, n=12, seed=51)
    if t >= 13.72:
        k = fx.slam(t, 13.72) * popin(t, 13.72, 0.2)
        blit(fg, fx.big('check', s=13), FX, GROUND - 450, k, k, 0, anchor='center'); fx.burst(fg, t, 13.72, FX, GROUND - 450, (60, 200, 90), n=12, seed=52)
        fx.gsparkles(fg, t, FX, GROUND - 450, 400, 300, n=8, seed=53)
    dg.label(fg, t, 11.8, 'SLOW', (SX, GROUND - 200), (SX - 40, 660), '#ffffff', '#1a1a2e', '#d6d9e2', s=8)
    dg.label(fg, t, 12.0, 'FAST', (FX, GROUND - 640), (FX + 20, 560), '#7fe3a0', '#1a1a2e', '#3cc85a', s=8)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


def kit_text(ch):
    from pixanim.autos import ptext
    return ptext(ch, '#d6d9e2', True)


shot_teaser, TEASE_CUES = kit.teaser(14.9, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_fill), (2.6, shot_photo), (5.0, shot_charge), (9.2, shot_kw), (11.6, shot_slow), (14.9, shot_teaser)]
TRANS = {1: (2.6, 2.8, 'whip', dict(dx=1)), 2: (5.0, 5.2, 'push', None), 3: (9.2, 9.4, 'iris', (CHX, 820)),
         4: (11.6, 11.8, 'whip', dict(dx=0, dy=1)), 5: (14.9, 15.1, 'whip', dict(dx=1))}
KEYCOL = {'taycan': YEL, 'reportedly': RED, 'production': YEL, '800-volt': YEL, 'test': YEL, 'charged': GRN, '80': GRN,
          'about': YEL, '22': RED, '270': YEL, 'kilowatt': YEL, 'waited': YEL, 'slow': GRN, 'knows': YEL,
          'difference': GRN, 'follow': YEL}
CUES = [
    (0.0, 'whoosh', 0.5), (0.05, 'pop', 0.6), (CLICK, 'click', 1.0), (CLICK + 0.02, 'ding', 0.5), (0.4, 'pop', 0.4)] + [
    (0.5 + k * 0.2, 'click', 0.3) for k in range(8)] + [
    (1.39, 'stamp', 0.6), (2.1, 'ding', 0.9), (2.12, 'sparkle', 0.7),
    (2.75, 'pop', 0.7), (2.95, 'thump', 0.4), (3.36, 'boom', 0.4), (3.38, 'stamp', 0.8),
    (5.4, 'thump', 0.4), (6.0, 'pop', 0.5), (6.49, 'pop', 0.6), (6.95, 'pop', 0.6), (6.97, 'sparkle', 0.5), (8.1, 'pop', 0.6),
    (8.51, 'stamp', 0.9), (8.53, 'ding', 0.6),
    (9.4, 'pop', 0.7), (9.42, 'whoosh', 0.5), (10.14, 'sparkle', 0.5), (10.54, 'click', 0.4),
    (11.8, 'pop', 0.4), (12.0, 'pop', 0.4), (12.77, 'buzzer', 0.7), (12.79, 'stamp', 0.6), (13.72, 'ding', 0.9), (13.74, 'sparkle', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
