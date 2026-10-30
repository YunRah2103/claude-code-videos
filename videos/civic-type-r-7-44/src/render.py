"""Renders 'Type R, 7:44.881': an April 2023 Nurburgring lap, reported as the fastest front-wheel-drive production car.

Template: videos/plaid-two-seconds (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json; the voiceover is out/civic-type-r-7-44/voiceover.wav (clip 5 of out/voiceover/full_voiceover.wav). The
mixer holds a 0.6 s pause before 'Follow for the next one' (GAP); later words are shifted to match. The record is
'reported' (REPORTED tag). The track is a generic pixel loop and the car a generic hatch, no badges or lettering.
Shots:
  1 lap      0.00  hook: top-down green circuit, a pixel car laps it while the timer runs to 7:44.881, '7:44.881'
  2 photo    4.55  garage: the real Type R photo pops in, APRIL 2023 tag
  3 flag     7.90  a winner's flag waves, REPORTED, FASTEST, the front wheels glow, 'front-wheel drive', the car blasts off
  4 teaser  13.25  shared NEXT EPISODE ending ('Follow for the next one.')
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, title, draw_car
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

RAW = kit.load_words(HERE)
GAP = (12.3, 0.6)                                     # pause inserted between 'track.' and 'Follow'
WORDS = kit.shift_words(RAW, *GAP)
DUR = 17.0
END_T = 13.25
def ws(i): return WORDS[i]['s']


# ------------------------------------------------------------------ episode sprites
TW, TH, TS = 100, 104, 8                              # circuit grid and scale


def loop(u):
    """Closed, twisty circuit (grid coords) at lap fraction u."""
    a = 2 * math.pi * u
    r = 1 + 0.18 * math.sin(3 * a + 0.6) + 0.1 * math.sin(5 * a + 1.3)
    return 50 + 40 * r * math.cos(a), 52 + 44 * r * math.sin(a) * (0.9 + 0.1 * math.cos(2 * a))


@lru_cache(None)
def circuit():
    img = Image.new('RGBA', (TW, TH), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, TW - 1, TH - 1), 8, fill=(56, 132, 70))
    for k in range(40):                                                           # grass tufts and trees
        x, y = (k * 37) % (TW - 6) + 3, (k * 53) % (TH - 6) + 3
        d.rectangle((x, y, x + 1, y + 1), fill=(76, 160, 88))
    pts = [loop(i / 240) for i in range(241)]
    d.line(pts, fill=(240, 240, 236), width=9); d.line(pts, fill=(84, 88, 98), width=7)
    for i in range(0, 240, 6): d.line([pts[i], pts[i + 3]], fill=(214, 60, 60), width=1)        # kerbs
    x, y = loop(0)
    for k in range(4): d.rectangle((x - 3 + k * 2, y - 4, x - 2 + k * 2, y + 3), fill=(255, 255, 255) if k % 2 else (26, 26, 46))
    return outline(img)


@lru_cache(None)
def topcar():
    """Top-down hatch (14x8), nose to the right."""
    img = Image.new('RGBA', (14, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 0, 4, 7), fill=(30, 32, 40)); d.rectangle((9, 0, 11, 7), fill=(30, 32, 40))
    d.rounded_rectangle((0, 1, 13, 6), 2, fill=(240, 242, 246)); d.rectangle((5, 2, 9, 5), fill=(80, 140, 200))
    d.rectangle((12, 2, 13, 5), fill=(255, 240, 180)); d.rectangle((0, 3, 1, 4), fill=(214, 60, 60))
    return outline(img)


@lru_cache(None)
def flag(ph=0):
    """Big chequered winner's flag (40x46) on a pole, cloth rippling with phase 0..7."""
    img = Image.new('RGBA', (40, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 2, 45), fill=(200, 204, 214)); d.rectangle((0, 0, 2, 1), fill=(255, 217, 59))
    for gx in range(9):
        for gy in range(6):
            dy = round(2 * math.sin((gx - ph) * 0.9)) * gx // 4
            d.rectangle((3 + gx * 4, 2 + gy * 4 + dy, 6 + gx * 4, 5 + gy * 4 + dy), fill=(248, 248, 244) if (gx + gy) % 2 else (26, 26, 46))
    return outline(img)


# ================================================================== shot 1: hook, the lap and the timer
L0, L1 = 0.1, WORDS[8]['e']                        # the timer runs out as '44.881' ends
LAP = 7 * 60 + 44.881
def lap_u(t): return clamp((t - L0) / (L1 - L0))
def clock(t):
    v = LAP * io(lap_u(t)) if t < L1 else LAP
    return f'{int(v // 60)}:{v % 60:06.3f}'
CX, CY = 540, 1000
def on_screen(u): x, y = loop(u); return CX - TW * TS / 2 + x * TS, CY - TH * TS / 2 + y * TS
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.0)), (0.0, (540, 960, 1.0)), (2.0, (540, 960, 1.04), 'io'), (4.6, (540, 960, 1.08), 'io')],
              kicks=[(L0, 0.08, 540, 860), (ws(6), 0.1, CX, CY), (ws(8), 0.12, CX, CY), (L1, 0.2, CX, CY)], shakes=[(L1, 0.3, 10)])


def shot_lap(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 0.0, 0.25)
    blit(fg, up(circuit(), TS), CX, CY, k, k, 0, anchor='center')
    u = io(lap_u(t))
    for gh in range(4, 0, -1):                        # motion ghosts behind the car
        x, y = on_screen(max(0.0, u - gh * 0.012))
        c = up(topcar(), 6); c.putalpha(c.getchannel('A').point(lambda a: a * (5 - gh) // 8))
        blit(fg, c, x, y, 1, 1, 0, anchor='center')
    x, y = on_screen(u); x2, y2 = on_screen(min(1.0, u + 0.004) if u < 1 else 1.0)
    ang = -math.degrees(math.atan2(y2 - y, x2 - x)) if u < 1 else 0
    blit(fg, up(topcar(), 6), x, y, 1, 1, round(ang / 15) * 15, anchor='center')
    kk = popin(t, L0, 0.25) * (fx.slam(t, L1, k=0.4) if t >= L1 else 1)
    blit(fg, fx.big('badge', clock(t), '#ffffff' if t < L1 else '#ffd23f', '#1a1a2e', '#d6d9e2', s=9), CX, CY, kk, kk, -2, anchor='center')
    if t >= L1:
        fx.burst(fg, t, L1, CX, CY, GLOW, n=16, seed=2); fx.confetti(fg, t, L1, CX, CY - 100, n=30, seed=3)
        fx.sparkles(fg, t, CX, CY, 500, 160, n=6, seed=4)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 2: the real car, April 2023
T2 = 4.55
AP = ws(15)                                           # 'April'
P2 = Presenter([
    (T2 - 0.05, dict(path=Track([(T2 - 0.05, (1300, 300)), (T2 + 0.4, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (T2 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 620), look=(540, 620), expr='wow', face=None)),
    (AP, dict(arms='thumb', point=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(T2, (540, 900, 1.08)), (7.9, (540, 880, 1.16), 'io')],
              kicks=[(T2 + 0.15, 0.08, 540, 620), (ws(13), 0.1, 540, 620), (AP, 0.16, 400, 1090)], shakes=[(AP, 0.25, 8)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= AP:
        k = fx.slam(t, AP) * popin(t, AP, 0.2)
        blit(fg, fx.big('badge', 'APRIL 2023', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), 400, 1090, k, k, -4, anchor='center')
        fx.burst(fg, t, AP, 400, 1090, GLOW, n=12, seed=21)
    if t >= ws(13): blit(fg, up(topcar(), 5), 200 + 60 * ((t - ws(13)) % 2), 300, 1, 1, 0, anchor='center')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: winner's flag, front-wheel drive
T3 = 7.9
RP, FA, FW, PR, AR = ws(19), ws(22), ws(23), ws(24), ws(26)   # reported, fastest, front-wheel-drive, production, around
CAR_X = 500
def car_x3(t): return CAR_X if t < AR else CAR_X + 2200 * ic(prog(t, AR, 1.0))
CAM3 = Camera(W, H, [(T3, (540, 900, 1.06)), (FW, (560, 960, 1.08), 'io'), (AR, (600, 960, 1.1), 'io'), (END_T, (560, 940, 1.14), 'io')],
              kicks=[(ws(17), 0.08, 820, 900), (RP, 0.12, 380, 420), (FA, 0.14, 600, 580), (FW, 0.12, CAR_X + 150, 1150), (AR, 0.2, CAR_X, 1100)],
              shakes=[(AR, 0.4, 12)])


def shot_flag(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, T3 + 0.05, 0.3)
    blit(fg, up(flag(int(t * 10) % 8), 8), 820, GROUND, k, k, -3 + 3 * math.sin(t * 3))
    if t >= FW - 0.45:                                # the hatch rolls in, front wheels glow, then it blasts off
        x = lerp(-400, CAR_X, oc(prog(t, FW - 0.45, 0.4))) if t < AR else car_x3(t)
        draw_car(fg, 'silver', x, 6, dist=x, lights=True)
        if t >= AR:
            fx.speed_lines(fg, 1 - prog(t, AR + 0.6, 0.8), int(t * 12) % 5, col=(220, 224, 236))
            for j in range(3): fx.puff(fg, t, AR + j * 0.06, CAR_X - 260, GROUND - 20, seed=60 + j, drift=(-300, -60), col=(200, 204, 214))
    if t >= FW and t < AR + 0.2:                       # front axle glow (car nose to the right)
        d = ImageDraw.Draw(fg); fxw = car_x3(t) + 6 * 26
        for r in (70, 52):
            d.ellipse((fxw - r, GROUND - 70 - r, fxw + r, GROUND - 70 + r), outline=(255, 217, 59, 200 if r == 70 else 255), width=8)
        fx.ring(fg, t, FW, fxw, GROUND - 70, GLOW, r1=260)
    if t >= RP:
        kk = popin(t, RP, 0.25)
        blit(fg, fx.big('tag', 'REPORTED', '#fff6e0', '#d6303a', s=9), 380, 420, kk, kk, -6 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, RP, 380, 420, RED, n=10, seed=31)
    if t >= FA:
        kk = fx.slam(t, FA) * popin(t, FA, 0.2)
        blit(fg, fx.big('badge', 'FASTEST', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 600, 580, kk, kk, 3, anchor='center')
        fx.ring(fg, t, FA, 600, 580, GLOW, r1=480); fx.sparkles(fg, t, 600, 580, 700, 200, n=8, seed=32)
    if t >= AR + 0.6: fx.confetti(fg, t, AR + 0.6, 540, 500, n=40, seed=33)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)


def overlay(cv, t):
    title(cv, t, 0.05, 4.5, '7:44.881', RED, 430, 150, -3)
    kit.photo_hq(cv, t, T2 + 0.1, 7.8, 'civic', 540, 640, 820, rot=-3, label='THE REAL CAR')
    title(cv, t, FW, 12.6, 'front-wheel drive', YEL, 740, 112, 2)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_lap), (T2, shot_photo), (T3, shot_flag), (END_T, shot_teaser)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (END_T, END_T + 0.2, 'iris', (540, 980))}
KEYCOL = {'civic': YEL, '44.881': RED, 'lap': YEL, 'nürburgring': YEL, 'april': GRN, 'reported': RED, 'fastest': YEL, 'front-wheel-drive': YEL, 'track': GRN}
CUES = [(0.0, 'whoosh', 0.4), (0.05, 'pop', 0.6), (L0, 'vroom', 0.8)] + [(L0 + 0.5 * k, 'whoosh', 0.25) for k in range(1, 8)] + [
        (L1, 'ding', 0.9), (L1 + 0.02, 'confetti', 0.7), (L1 + 0.04, 'stamp', 0.5),
        (T2 + 0.1, 'pop', 0.7), (T2 + 0.4, 'thump', 0.4), (AP, 'stamp', 0.7),
        (T3 + 0.05, 'pop', 0.6), (RP, 'stamp', 0.6), (FA, 'ding', 0.8), (FA + 0.02, 'sparkle', 0.6), (FW, 'pop', 0.6), (FW + 0.1, 'pop', 0.4),
        (FW - 0.45, 'vroom', 0.5), (AR, 'vroom', 1.0), (AR + 0.05, 'screech', 0.4), (AR + 0.6, 'confetti', 0.8),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, gap=GAP, crisp=True)

if __name__ == '__main__':
    kit.main()
