"""Renders 'Jesko, 0-400-0': the Jesko Absolut was reportedly timed at 27.83 s from 0 to 400 km/h and back to zero.

Template: videos/plaid-two-seconds (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json; the voiceover is out/jesko-0-400-0/voiceover.wav (clip 6 of out/voiceover/full_voiceover.wav). The
mixer holds a 2.6 s pause before 'Follow for the next one' (GAP) for the recap beat; later words are shifted to
match. 27.83 s was checked against CarExpert's report (2 July 2024: Orebro runway, driver Markus Lundh); the
script hedges it as 'reportedly' (REPORTEDLY tag). The car is a generic pixel coupe, no badges or lettering.
Shots:
  1 sweep    0.00  hook: the speedo sweeps 0 -> 400 -> 0 while a timer races to 27.83, '27.83 seconds'
  2 photo    2.10  garage: the real Jesko Absolut photo pops in, 'reportedly', the 27.83 S stopwatch slams down
  3 run      5.20  night street: 0 KM/H, launch, the counter climbs to 400, brakes glow, back to 0
  4 recap    9.50  garage: 0-400-0 badge, stopwatch 27.83, REPORTEDLY stamp
  5 teaser  12.45  shared NEXT EPISODE ending ('Follow for the next one.')
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, title, draw_car, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.dash import Dashboard
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

RAW = kit.load_words(HERE)
GAP = (9.5, 2.6)                                      # pause inserted between 'zero.' and 'Follow'
WORDS = kit.shift_words(RAW, *GAP)
DUR = 17.0
END_T = 12.45
def ws(i): return WORDS[i]['s']


@lru_cache(None)
def stopwatch(frac=0.0):
    """Pixel stopwatch (34x40): crown, two buttons, white dial, red hand at `frac` of a turn."""
    img = Image.new('RGBA', (34, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((14, 0, 19, 4), fill=(200, 204, 214)); d.rectangle((12, 4, 21, 6), fill=(150, 156, 170))
    d.rectangle((3, 6, 7, 9), fill=(150, 156, 170)); d.rectangle((26, 6, 30, 9), fill=(150, 156, 170))
    d.ellipse((0, 6, 33, 39), fill=(150, 156, 170)); d.ellipse((2, 8, 31, 37), fill=(248, 248, 244))
    for k in range(12):
        a = math.radians(k * 30)
        d.point((16.5 + 12 * math.sin(a), 22.5 - 12 * math.cos(a)), fill=(26, 26, 46))
    a = math.radians(frac * 360)
    d.line([(16.5, 22.5), (16.5 + 11 * math.sin(a), 22.5 - 11 * math.cos(a))], fill=(224, 48, 58), width=2)
    d.ellipse((15, 21, 18, 24), fill=(26, 26, 46))
    d.arc((4, 10, 29, 35), 200, 260, fill=(255, 255, 255))
    return outline(img)


def sdeg(kmh): return 225 - 270 * kmh / 400        # speedo needle for 0..400 km/h


# ================================================================== shot 1: hook, 0 -> 400 -> 0 in one sweep
DASH = Dashboard()
def hook_kmh(t):
    u = clamp((t - 0.1) / 1.8)
    return 400 * (io(u / 0.62) if u < 0.62 else 1 - io((u - 0.62) / 0.38))
CAM1 = Camera(W, H, [(-1.0, (560, 880, 1.22)), (0.0, (560, 880, 1.22)), (1.0, (600, 920, 1.3), 'io'), (2.2, (580, 920, 1.36), 'io')],
              kicks=[(0.1, 0.1, 560, 880), (1.2, 0.14, 790, 985), (1.9, 0.2, 560, 1000)], shakes=[(1.0, 0.4, 6), (1.9, 0.25, 12)])


def shot_sweep(t):
    v = hook_kmh(t)
    img = DASH.frame(t, rpm_deg=225 - 250 * (v / 400) + 4 * math.sin(t * 33), speed_deg=sdeg(v), lcd=f'{int(v)}')
    fg = layer()
    sec = 27.83 * clamp((t - 0.1) / 1.8)
    k = popin(t, 0.1, 0.25) * (fx.slam(t, 1.9, k=0.5) if t >= 1.9 else 1)
    blit(fg, fx.big('badge', f'{sec:.2f} S', '#ffffff' if t < 1.9 else '#ffd23f', '#1a1a2e', '#d6d9e2', s=11), 560, 1080, k, k, -3, anchor='center')
    blit(fg, up(stopwatch(sec / 60), 7), 250, 990, popin(t, 0.25), popin(t, 0.25), 6 * math.sin(t * 9), anchor='center')
    if t >= 1.9: fx.burst(fg, t, 1.9, 560, 1080, GLOW, n=16, seed=2); fx.ring(fg, t, 1.9, 560, 1080, GLOW)
    fx.sparkles(fg, t, 560, 1080, 700, 200, n=6, seed=1)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 2: the real car, reportedly 27.83 s
T2 = 2.1
SW = ws(7)                                            # '27.83'
P2 = Presenter([
    (T2 - 0.05, dict(path=Track([(T2 - 0.05, (1300, 300)), (T2 + 0.4, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (T2 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 600), look=(540, 600), expr='smirk', face=None)),
    (ws(4), dict(arms='shrug', point=None, look_camera=True, expr='think')),
    (SW, dict(arms='shock', expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(T2, (540, 900, 1.08)), (SW, (520, 920, 1.14), 'io'), (5.2, (520, 920, 1.18), 'io')],
              kicks=[(T2 + 0.15, 0.08, 540, 600), (ws(4), 0.1, 540, 440), (SW, 0.2, 360, 1060)], shakes=[(SW, 0.3, 12)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= SW:
        k = fx.slam(t, SW) * popin(t, SW, 0.2)
        blit(fg, up(stopwatch(prog(t, SW, 1.2) * 0.46), 7), 200, 1060, k, k, -4 + 2 * math.sin(t * 4), anchor='center')
        blit(fg, fx.big('badge', '27.83 S', '#ffd23f', '#d6303a', '#e8b923', s=11), 470, 1090, k, k, 3, anchor='center')
        fx.ring(fg, t, SW, 400, 1080, GLOW, r1=420); fx.burst(fg, t, SW, 400, 1080, GLOW, n=16, seed=12)
        fx.sparkles(fg, t, 400, 1080, 600, 200, n=6, seed=13)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the run, 0 -> 400 -> 0
T3 = 5.2
GO, TOP, BRK, STOP = ws(10) + 0.1, ws(12) + 0.3, ws(14), WORDS[17]['e']   # '0', '400', 'and', 'zero.'
def kmh(t):
    if t < GO: return 0.0
    if t < TOP: return 400 * io(prog(t, GO, TOP - GO))
    if t < BRK: return 400.0
    return 400 * (1 - oc(prog(t, BRK, STOP - BRK)))
def scroll3(t):                                        # integrate the speed for the road scroll
    n = 40; dt = max(0.0, t - GO) / n
    return sum(kmh(GO + (i + 0.5) * dt) for i in range(n)) * dt * 9
def car_x3(t): return 320 + 180 * clamp(kmh(t) / 400) - (60 * math.sin(prog(t, BRK, 0.3) * math.pi) if t >= BRK else 0)
CAM3 = Camera(W, H, [(T3, (540, 980, 1.12)), (GO, (420, 1040, 1.24), 'io'), (GO + 0.6, (600, 980, 1.08), 'oc'), (BRK, (560, 980, 1.14), 'io'),
                     (9.5, (540, 980, 1.2), 'io')],
              kicks=[(ws(10), 0.1, 540, 560), (GO, 0.22, 320, 1080), (TOP, 0.16, 540, 560), (BRK, 0.16, 500, 1080), (STOP, 0.16, 540, 560)],
              shakes=[(GO, 0.5, 14), (BRK, 0.6, 10)])


def shot_run(t):
    v = kmh(t)
    img = street(t, scroll3(t)); fg = layer()
    x = car_x3(t); braking = BRK <= t < STOP + 0.3
    sq = 1 - 0.05 * math.exp(-max(0, t - GO) * 8) * (t >= GO)
    draw_car(fg, 'red', x, 4, y=ROAD_Y, dist=scroll3(t), lights=True, brake=braking, sx=1 / sq, sy=sq,
             rot=(2 * math.exp(-max(0, t - GO) * 6) if t >= GO else 0) - (2.5 * math.sin(prog(t, BRK, 0.5) * math.pi) if t >= BRK else 0))
    if v > 30: fx.speed_lines(fg, min(1.0, v / 300), int(t * 12) % 5, col=(200, 204, 220))
    if t >= GO:
        for k in range(4): fx.puff(fg, t, GO + k * 0.05, x - 170, ROAD_Y - 20, seed=20 + k, drift=(-300, -60), col=(200, 204, 214))
    if braking:
        d = ImageDraw.Draw(fg)                           # brake glow on the discs + sparks
        for wx in (x - 110, x + 105):
            r = 26 + 4 * math.sin(t * 40)
            d.ellipse((wx - r, ROAD_Y - 52 - r, wx + r, ROAD_Y - 52 + r), outline=(255, 120, 40, 230), width=7)
        fx.dust(fg, t, BRK, x + 100, ROAD_Y - 10, n=10, seed=30, dirx=1, col=(255, 200, 90))
    k = popin(t, ws(10), 0.25)
    blit(fg, fx.big('badge', f'{int(v)} KM/H', '#ffd23f' if v >= 399.5 else '#ffffff', '#1a1a2e', '#d6d9e2', s=12), 430, 600, k, k, -2, anchor='center')
    if t >= TOP: fx.burst(fg, t, TOP, 480, 600, GLOW, n=16, seed=31); fx.ring(fg, t, TOP, 480, 600, GLOW)
    if t >= STOP: fx.burst(fg, t, STOP, 480, 600, (90, 220, 120), n=16, seed=32); fx.sparkles(fg, t, 480, 600, 700, 200, n=6, seed=33)
    dg.label(fg, t, BRK, 'BRAKING', (x, ROAD_Y - 160), (x + 60, ROAD_Y - 420), '#ffffff', '#d6303a', '#d6d9e2', s=7, t1=STOP + 0.2)
    return CAM3.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: recap
T4 = 9.5
P4 = Presenter([
    (T4 - 0.05, dict(path=Track([(T4 - 0.05, (-200, 400)), (T4 + 0.4, (200, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (T4 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(600, 640), look=(600, 640), expr='wow', face=None)),
    (T4 + 1.5, dict(arms='thumb', point=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(T4, (540, 900, 1.08)), (T4 + 0.9, (560, 860, 1.16), 'io'), (END_T, (560, 860, 1.2))],
              kicks=[(T4 + 0.2, 0.1, 560, 480), (T4 + 0.9, 0.16, 640, 820), (T4 + 1.5, 0.14, 700, 1060)], shakes=[(T4 + 0.9, 0.25, 8)])


def shot_recap(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= T4 + 0.2:
        k = popin(t, T4 + 0.2, 0.25)
        blit(fg, fx.big('badge', '0-400-0 KM/H', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), 560, 480, k, k, -3 + 2 * math.sin(t * 4), anchor='center')
        fx.burst(fg, t, T4 + 0.2, 560, 480, GLOW, n=12, seed=41)
    if t >= T4 + 0.9:
        k = fx.slam(t, T4 + 0.9) * popin(t, T4 + 0.9, 0.2)
        blit(fg, up(stopwatch(0.46), 7), 640, 880, k, k, 4 * math.sin(t * 4), anchor='center')
        blit(fg, fx.big('badge', '27.83 S', '#ffd23f', '#d6303a', '#e8b923', s=12), 640, 1080, k, k, 3, anchor='center')
        fx.ring(fg, t, T4 + 0.9, 640, 880, GLOW, r1=480); fx.sparkles(fg, t, 640, 880, 600, 500, n=8, seed=42)
    if t >= T4 + 1.5:
        fx.stamp_at(fg, t, T4 + 1.5, 'REPORTEDLY', 600, 640, rot=-8, s=7, col='#2f9e52')
        fx.confetti(fg, t, T4 + 1.5, 600, 500, n=30, seed=43)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)


def overlay(cv, t):
    title(cv, t, 0.05, 2.05, '27.83 seconds', RED, 520, 124, -3)
    kit.photo_hq(cv, t, T2 + 0.1, 5.1, 'jesko', 540, 740, 840, rot=3, label='THE REAL CAR', crop=(0.0, 0.33, 1.0, 1.0))
    title(cv, t, ws(4), 5.1, 'reportedly', GRN, 420, 116, -3)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_sweep), (T2, shot_photo), (T3, shot_run), (T4, shot_recap), (END_T, shot_teaser)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (T4, T4 + 0.2, 'iris', (540, 980)),
         4: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'jesko': YEL, 'reportedly': GRN, '27.83': RED, '0': YEL, '400': RED, 'zero': YEL}
CUES = [(0.0, 'whoosh', 0.4), (0.05, 'pop', 0.6), (0.1, 'vroom', 0.9)] + [(0.1 + k * 0.2, 'click', 0.4) for k in range(9)] + [
        (1.2, 'screech', 0.5), (1.9, 'ding', 0.9), (1.92, 'sparkle', 0.6),
        (T2 + 0.1, 'pop', 0.7), (T2 + 0.4, 'thump', 0.4), (ws(4), 'pop', 0.6), (SW, 'boom', 0.5), (SW + 0.02, 'stamp', 0.8), (SW + 0.04, 'sparkle', 0.6),
        (ws(10), 'pop', 0.6), (GO, 'vroom', 1.0), (GO + 0.05, 'screech', 0.3), (TOP, 'ding', 0.8), (BRK, 'screech', 0.9), (STOP, 'thump', 0.6),
        (STOP + 0.02, 'ding', 0.6),
        (T4 + 0.2, 'pop', 0.6), (T4 + 0.4, 'thump', 0.4), (T4 + 0.9, 'stamp', 0.8), (T4 + 0.92, 'sparkle', 0.6), (T4 + 1.5, 'stamp', 0.8),
        (T4 + 1.52, 'confetti', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=True, loud=True, gap=GAP, crisp=True)

if __name__ == '__main__':
    kit.main()
