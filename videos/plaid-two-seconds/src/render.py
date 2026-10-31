"""Renders 'Plaid, two seconds': a claimed 1.99 s to 60 mph, three motors, a claimed 1,000+ hp.

Template: videos/the-trabant (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). Speech runs 0.1-14.8 s; the supplied read has no 'Follow' line, so
the end card shows it. Both performance figures are company claims (CLAIMED tags). The car is a generic pixel
saloon with no badges or lettering.
Shots:
  1 timer    0.00  dashboard close-up: the LCD counts 2.00 -> 0.00 while the speedo sweeps; 'Faster than you can blink'
  2 claimed  2.20  garage: silver saloon, CLAIMED tag, 0-60 MPH label, a giant 1.99 S stopwatch stamps down
  3 launch   6.45  night street: the saloon launches with speed lines and a camera punch; JUNE 2021; THREE MOTORS
  4 power    9.85  cutaway: three motors light up in turn, the power counter runs to 1,000+ HP; CLAIMED stamp
  5 blink   13.20  he blinks and the car is already gone: a blur streaks past; BLINK
  6 teaser  14.95  shared NEXT EPISODE ending
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
from pixanim import autos
from pixanim.street import Street

WORDS = kit.load_words(HERE, 'words_v1.json')     # first read: the body shots are timed on it
NEW = kit.load_words(HERE)                          # current read (captions); WARP maps it onto WORDS
Q_END, BODY_END, END_T = 3.35, 15.95, 18.45
DUR = END_T + 1.0


# ------------------------------------------------------------------ episode sprites
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


@lru_cache(None)
def motor(on=0.0):
    """Electric motor (26x22): finned can, copper windings window, glowing when `on` (0..1)."""
    img = Image.new('RGBA', (26, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 2, 21, 21), 4, fill=(120, 126, 138))
    for y in range(4, 21, 3): d.line([(1, y), (20, y)], fill=(150, 156, 170))
    d.rectangle((21, 9, 25, 13), fill=(200, 204, 214))
    g = int(80 + 175 * on)
    d.rectangle((6, 7, 15, 16), fill=(min(255, 150 + g // 3), min(255, 80 + g // 2), 40))
    for x in range(7, 15, 2): d.line([(x, 8), (x, 15)], fill=(min(255, 200 + g // 5), min(255, 120 + g // 2), 60))
    if on > 0.5: d.rectangle((9, 0, 12, 2), fill=(255, 230, 90))
    return outline(img)


@lru_cache(None)
def eye(open_=1.0):
    """Big cartoon eye (40x24) that closes as open_ -> 0."""
    img = Image.new('RGBA', (40, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    h = max(1, int(10 * open_))
    if h > 1:
        d.ellipse((2, 12 - h, 37, 12 + h), fill=(248, 248, 244))
        r = min(7, h); d.ellipse((13, 12 - r, 26, 12 + r), fill=(60, 120, 200)); d.ellipse((17, 12 - r // 2, 22, 12 + r // 2), fill=(16, 16, 24))
        d.point((15, 12 - r // 2), fill=(255, 255, 255))
    d.line([(1, 12 - h), (38, 12 - h)], fill=(26, 26, 46), width=2)
    if h <= 1: d.line([(1, 12), (38, 12)], fill=(26, 26, 46), width=3)
    for k in range(5): d.line([(6 + k * 7, 12 - h), (4 + k * 7, 8 - h)], fill=(26, 26, 46))
    return img


# ================================================================== shot 1: hook, the dashboard countdown
DASH = Dashboard()
def countdown(t): return max(0.0, 2.0 - clamp((t - 0.15) / 1.85) * 2.0)
CAM1 = Camera(W, H, [(-1.0, (560, 880, 1.25)), (0.0, (560, 880, 1.25)), (1.0, (600, 920, 1.32), 'io'), (2.2, (580, 920, 1.38), 'io')],
              kicks=[(0.15, 0.1, 560, 880), (1.0, 0.08, 790, 985), (2.0, 0.2, 560, 1000)], shakes=[(1.4, 0.6, 5), (2.0, 0.25, 12)])


def shot_timer(t):
    u = clamp((t - 0.15) / 1.85)
    sweep = 225 - 250 * io(u) + 2 * math.sin(t * 40) * (0.2 < u < 1)
    img = DASH.frame(t, rpm_deg=225 - 230 * min(1, u * 1.6) + 4 * math.sin(t * 33), speed_deg=sweep, lcd=f'{countdown(t):.2f}')
    fg = layer()
    v = countdown(t)
    k = popin(t, 0.1, 0.25) * (1 + 0.06 * (v == 0) * math.sin(t * 20))
    blit(fg, fx.big('badge', f'{v:.2f} S', '#ffffff' if v > 0 else '#ffd23f', '#1a1a2e', '#d6d9e2', s=11), 560, 1080, k, k, -3, anchor='center')
    blit(fg, up(stopwatch(1 - v / 2), 7), 250, 990, popin(t, 0.25), popin(t, 0.25), 6 * math.sin(t * 9), anchor='center')
    fx.sparkles(fg, t, 560, 1080, 700, 200, n=6, seed=1)
    if t >= 2.0:
        fx.burst(fg, t, 2.0, 560, 1080, GLOW, n=16, seed=2); fx.ring(fg, t, 2.0, 560, 1080, GLOW)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, 0.05, Q_END - 0.1, 'Four-door car', WHITE, 480, 108, -3)
    title(cv, t, 0.3, Q_END - 0.1, 'vs supercar?', YEL, 610, 120, 3)
    to = WARP(t)
    if Q_END <= t < BODY_END:
        title(cv, to, 7.0 + 1.86, 9.75, 'three motors', GRN, 560, 120, -3)
        title(cv, to, 11.94, 13.1, 'claimed', RED, 380, 120, 3)
    title(cv, t, BODY_END + 0.05, END_T - 0.1, 'What would you do', WHITE, 480, 96, -2)
    title(cv, t, BODY_END + 0.3, END_T - 0.1, 'with 1.99 s?', YEL, 610, 120, 2)


# ================================================================== shot 0: the question, four-door vs supercar at the line
GREEN = 2.3
CAM0 = Camera(W, H, [(-1.0, (540, 1000, 1.3)), (0.0, (540, 1000, 1.3)), (1.6, (540, 980, 1.14), 'io'), (GREEN, (560, 1000, 1.22), 'io'), (Q_END, (640, 1000, 1.12), 'io')],
              kicks=[(0.87, 0.1, 300, 1100), (1.64, 0.12, 780, 1100), (GREEN, 0.24, 540, 1050)], shakes=[(GREEN, 0.5, 14)])


def shot_q(t):
    go = t >= GREEN
    scroll = 0 if not go else 2200 * ic(prog(t, GREEN, 0.9)) + max(0, t - GREEN - 0.9) * 2200
    img = street(t, scroll); fg = layer()
    stage = 0 if t < 0.6 else 4 if go else min(3, 1 + int((t - 0.6) / 0.45))
    blit(fg, up(autos.light_tree(stage), 6), 540, ROAD_Y - 150, popin(t, 0.1), popin(t, 0.1))
    u = ic(prog(t, GREEN, 1.0)) if go else 0
    k1, k2 = popin(t, 0.87, 0.25), popin(t, 1.64, 0.25)
    shk = 3 * math.sin(t * 60)
    draw_car(fg, 'silver', 250 + 1600 * u * 1.05, 4, y=ROAD_Y - 40 + shk * (not go), dist=scroll, lights=True, sx=k1, sy=k1)
    blit(fg, up(autos.supercar('wedge', int(scroll) % 360 // 30 * 30, True), 4), 790 + 1600 * u, ROAD_Y + 30 - shk * (not go), k2, k2)
    if go:
        fx.speed_lines(fg, 0.9, int(t * 12) % 5, col=(200, 204, 220)); fx.ring(fg, t, GREEN, 540, ROAD_Y - 330, (60, 230, 90), r1=520)
        for k in range(5): fx.puff(fg, t, GREEN + k * 0.05, 200, ROAD_Y - 20, seed=60 + k, drift=(-300, -60), col=(200, 204, 214))
    if t >= 0.87: fx.burst(fg, t, 0.87, 260, ROAD_Y - 120, GLOW, n=8, r0=60, r1=220, seed=61)
    if t >= 1.64: fx.burst(fg, t, 1.64, 800, ROAD_Y - 60, RED, n=8, r0=60, r1=220, seed=62)
    if t >= 0.87:
        k = popin(t, 0.87, 0.25) * popout(t, GREEN)
        blit(fg, fx.big('tag', '4 DOORS', '#fff6e0', '#1a1a2e', s=7), 260, ROAD_Y - 330, k, k, -5, anchor='center')
    if t >= 1.64:
        k = popin(t, 1.64, 0.25) * popout(t, GREEN)
        blit(fg, fx.big('tag', 'SUPERCAR', '#fff6e0', '#d6303a', s=7), 820, ROAD_Y - 300, k, k, 5, anchor='center')
    return CAM0.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 2: a claimed 1.99 s
CAR_X = 330
P2 = Presenter([
    (2.15, dict(path=Track([(2.15, (1300, 300)), (2.55, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.55, dict(ground=GROUND, squash=True, arms='point', point=(CAR_X, GROUND - 260), look=(CAR_X, GROUND - 260), expr='smirk', face=None)),
    (4.35, dict(arms='shock', point=None, look=(560, 560), expr='wow', squash=True)),
    (5.3, dict(arms='thumb', look=None, look_camera=True, expr='grin')),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.2, (540, 900, 1.12)), (2.9, (480, 940, 1.2), 'io'), (4.35, (540, 820, 1.18), 'io'), (6.45, (540, 820, 1.24))],
              kicks=[(2.36, 0.1, 300, 700), (2.9, 0.08, CAR_X, 1000), (4.35, 0.22, 540, 560), (5.59, 0.1, 540, 560)], shakes=[(4.35, 0.3, 14)])


def shot_claimed(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    draw_car(fg, 'silver', CAR_X, 7, sy=1 + 0.02 * math.sin(t * 3))
    fx.contact_shadow(fg, CAR_X, GROUND, 560, s=7)
    if t >= 2.36:
        k = popin(t, 2.36, 0.25)
        blit(fg, fx.big('tag', 'CLAIMED', '#fff6e0', '#d6303a', s=9), 380, 660, k, k, -6 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 2.36, 380, 660, RED, n=10, seed=11)
    dg.label(fg, t, 2.9, '0-60 MPH', (CAR_X + 260, GROUND - 200), (720, 820), '#ffffff', '#1a1a2e', '#d6d9e2', s=8, t1=4.25)
    if t >= 4.35:
        k = fx.slam(t, 4.35) * popin(t, 4.35, 0.2)
        blit(fg, up(stopwatch(prog(t, 4.35, 1.2) * 0.99), 12), 540, 560, k, k, -4 + 2 * math.sin(t * 4), anchor='center')
        blit(fg, fx.big('badge', '1.99 S', '#ffd23f', '#1a1a2e', '#e8b923', s=13), 540, 860, k, k, 3, anchor='center')
        fx.ring(fg, t, 4.35, 540, 620, GLOW, r1=520); fx.burst(fg, t, 4.35, 540, 620, GLOW, n=18, seed=12)
        fx.sparkles(fg, t, 540, 640, 760, 460, n=8, seed=13)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: launch on the night street
LAUNCH = 6.71
def car_x3(t): return 300 + (0 if t < LAUNCH else 2600 * ic(prog(t, LAUNCH, 1.3)))
CAM3 = Camera(W, H, [(6.45, (540, 980, 1.15)), (LAUNCH, (420, 1040, 1.3), 'io'), (7.4, (620, 980, 1.1), 'oc'), (9.85, (560, 960, 1.16), 'io')],
              kicks=[(LAUNCH, 0.24, 300, 1080), (7.51, 0.1, 540, 520), (8.86, 0.14, 540, 760)], shakes=[(LAUNCH, 0.5, 16)])


def shot_launch(t):
    fast = t >= LAUNCH
    scroll = 0 if not fast else 2400 * ic(prog(t, LAUNCH, 1.0)) + max(0, t - LAUNCH - 1.0) * 2400
    img = street(t, scroll); fg = layer()
    if t < 8.2:
        x = car_x3(t); sq = 1 - 0.05 * math.exp(-max(0, t - LAUNCH) * 8) * fast
        draw_car(fg, 'silver', x, 4, y=ROAD_Y, dist=x, lights=True, sx=1 / sq, sy=sq, rot=2 * math.exp(-max(0, t - LAUNCH) * 6) * fast)
        if fast:
            for k in range(6): fx.puff(fg, t, LAUNCH + k * 0.05, x - 160, ROAD_Y - 20, seed=20 + k, drift=(-300, -60), col=(200, 204, 214))
    else:                                           # car loops back in, holds centre under the motor icons
        x = lerp(-300, 540, oc(prog(t, 8.2, 0.5)))
        draw_car(fg, 'silver', x, 4, y=ROAD_Y, dist=t * 900, lights=True)
    if fast: fx.speed_lines(fg, 1.0 - 0.4 * prog(t, 8.8, 1.0), int(t * 12) % 5, col=(200, 204, 220))
    if fast and t < 7.4: fx.ring(fg, t, LAUNCH, 300, ROAD_Y - 80, GLOW, r1=500)
    if t >= 7.51:
        k = popin(t, 7.51, 0.25) * popout(t, 8.6)
        blit(fg, fx.big('badge', 'JUNE 2021', '#ffffff', '#1a1a2e', '#d6d9e2', s=11), 540, 520, k, k, -3, anchor='center')
        fx.burst(fg, t, 7.51, 540, 520, GLOW, n=12, seed=21)
    for i in range(3):                              # three motors pop in one after another
        t0 = 8.86 + i * 0.12
        if t >= t0:
            k = popin(t, t0, 0.25)
            blit(fg, up(motor(1.0 if int(t * 6 + i) % 3 else 0.6), 7), 340 + i * 200, 900 + 10 * math.sin(t * 6 + i), k, k, 0, anchor='center')
            fx.burst(fg, t, t0, 340 + i * 200, 900, (60, 200, 90), n=8, r0=60, r1=200, seed=22 + i)
    if t >= 8.86: fx.gsparkles(fg, t, 540, 900, 700, 200, n=8, seed=25)
    return CAM3.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: three motors, 1,000+ hp claimed
MX = (400, 620, 840)
def hp(t): return int(1000 * oc(prog(t, 10.34, 0.9)))
P4 = Presenter([
    (9.8, dict(path=Track([(9.8, (-200, 400)), (10.2, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (10.2, dict(ground=GROUND, squash=True, arms='point', point=(540, 900), look=(540, 900), expr='smile', face=None)),
    (11.03, dict(arms='cheer', point=None, expr='wow', squash=True)),
    (11.94, dict(arms='shrug', look=None, look_camera=True, expr='smirk')),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(9.85, (540, 900, 1.1)), (10.34, (540, 820, 1.22), 'io'), (11.94, (560, 860, 1.16), 'io'), (13.2, (560, 860, 1.2))],
              kicks=[(10.02, 0.08, 540, 900), (10.34, 0.1, 540, 560), (11.03, 0.18, 540, 560), (12.44, 0.14, 760, 720)], shakes=[(11.03, 0.4, 10)])


def shot_power(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    for i, x in enumerate(MX):
        on = clamp((t - 10.02 - i * 0.18) / 0.2)
        k = popin(t, 9.95 + i * 0.08, 0.25)
        blit(fg, up(motor(on), 9), x, 980 + 4 * math.sin(t * 30) * on, k, k, 0, anchor='center')
        if on > 0: fx.ring(fg, t, 10.02 + i * 0.18, x, 980, GLOW, life=0.3, r1=200)
    if t >= 10.02:
        d = ImageDraw.Draw(fg)
        for x in MX[:2]:
            ph = (t * 4) % 1
            d.rectangle((x + 110, 975, x + 130, 985), fill=(255, 210, 63, int(255 * (0.5 + 0.5 * math.sin(t * 12 + x)))))
    if t >= 10.34:
        k = popin(t, 10.34, 0.25)
        blit(fg, fx.big('badge', f'{hp(t):,}+ HP' if hp(t) >= 1000 else f'{hp(t)} HP', '#ffd23f', '#1a1a2e', '#e8b923', s=13), 540, 560, k, k, -2 + 2 * math.sin(t * 5), anchor='center')
        fx.sparkles(fg, t, 540, 560, 760, 260, n=8, seed=40)
    if t >= 11.03: fx.burst(fg, t, 11.03, 540, 560, GLOW, n=18, seed=41); fx.confetti(fg, t, 11.03, 540, 500, n=30, seed=42)
    if t >= 12.44: fx.stamp_at(fg, t, 12.44, 'CLAIMED', 760, 720, rot=-10, s=9)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: blink and it's gone
def lid(t):
    u = (t - 14.32) / 0.3
    return 1.0 if u < 0 or u > 1 else abs(1 - 2 * u)
P5 = Presenter([
    (13.2, dict(path=Track([(13.2, (300, GROUND))]), size=8, legs='stand', arms='point', point=(640, 600), look=(640, 600), expr='talk', face=1, ground=GROUND)),
    (14.32, dict(expr='happy', arms='talkB', look=None)),
    (14.62, dict(expr='shock', arms='shock', look_camera=True, squash=True)),
], words=WORDS, base_size=8)
CAM5 = Camera(W, H, [(13.2, (540, 900, 1.22)), (14.32, (460, 880, 1.32), 'io'), (14.95, (500, 880, 1.28), 'io')],
              kicks=[(13.38, 0.1, 760, 560), (14.32, 0.12, 300, 900), (14.5, 0.2, 540, 1000)], shakes=[(14.5, 0.3, 14)])


def shot_blink(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    o = lid(t)
    k = popin(t, 13.3, 0.25)
    blit(fg, up(eye(o), 12), 640, 600, k, k, 0, anchor='center')
    if t >= 14.42:                                 # the car is gone before the eye opens again: a silver streak
        u = prog(t, 14.42, 0.25)
        if u < 1:
            draw_car(fg, 'silver', lerp(-600, 1700, u), 6, sx=1.6, sy=0.9, dist=u * 3000)
        fx.speed_lines(fg, 1 - prog(t, 14.5, 0.5), 7, col=(220, 224, 236))
        fx.dust(fg, t, 14.5, 540, GROUND, n=12, seed=50)
    if t >= 14.55:
        k = fx.slam(t, 14.55) * popin(t, 14.55, 0.2)
        blit(fg, fx.big('badge', 'BLINK!', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 540, 840, k, k, 4, anchor='center')
        fx.sparkles(fg, t, 760, 820, 500, 200, n=6, seed=51)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== new read: question, body on the first read's timing, question
BODY = [p for p in kit.word_pairs(NEW, WORDS) if Q_END < p[0] < BODY_END - 1]
ANCH = [(Q_END - 0.05, BODY[0][1] - (BODY[0][0] - Q_END + 0.05))] + BODY + [(BODY_END - 0.01, 12.9), (BODY_END, 4.25), (END_T + 0.2, 6.4)]
WARP, N = kit.warp(ANCH), kit.unwarp(BODY)
shot_teaser, TEASE_CUES = kit.teaser(END_T, NEW)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_q), (Q_END, kit.retime(shot_timer, WARP)), (N(2.2), kit.retime(shot_claimed, WARP)), (N(6.45), kit.retime(shot_launch, WARP)),
         (N(9.85), kit.retime(shot_power, WARP)), (BODY_END, kit.retime(shot_claimed, WARP)), (END_T, shot_teaser)]
TRANS = {1: (Q_END, Q_END + 0.2, 'whip', dict(dx=0, dy=1)), 2: (N(2.2), N(2.2) + 0.2, 'whip', dict(dx=1)), 3: (N(6.45), N(6.45) + 0.2, 'push', None),
         4: (N(9.85), N(9.85) + 0.2, 'whip', dict(dx=0, dy=1)), 5: (BODY_END, BODY_END + 0.2, 'iris', (540, 980)), 6: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'four-door': YEL, 'supercar': RED, 'plaid': YEL, 'claimed': RED, '60': YEL, '1.99': YEL, 'launched': YEL, '2021,': YEL, 'motors.': GRN,
          '1,000': YEL, 'company.': RED, 'do': YEL, 'seconds?': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (0.15, 'vroom', 0.7)] + [(0.15 + k * 0.37, 'click', 0.5) for k in range(5)] + [
    (2.0, 'ding', 0.9), (2.02, 'sparkle', 0.6),
    (2.36, 'stamp', 0.6), (2.9, 'pop', 0.6), (4.35, 'boom', 0.5), (4.37, 'stamp', 0.8), (4.4, 'sparkle', 0.7), (5.3, 'pop', 0.4),
    (6.56, 'pop', 0.5), (LAUNCH, 'vroom', 1.0), (LAUNCH + 0.05, 'screech', 0.4), (7.51, 'pop', 0.7), (8.2, 'whoosh', 0.4),
    (8.86, 'pop', 0.6), (8.98, 'pop', 0.6), (9.1, 'pop', 0.6), (9.12, 'sparkle', 0.6),
    (10.02, 'click', 0.6), (10.2, 'click', 0.6), (10.38, 'click', 0.6), (10.34, 'whoosh', 0.5), (11.03, 'ding', 0.9), (11.05, 'confetti', 0.7),
    (12.44, 'stamp', 0.8),
    (13.3, 'pop', 0.5), (14.32, 'click', 0.4), (14.42, 'whoosh', 0.9), (14.5, 'vroom', 0.6), (14.55, 'stamp', 0.7),
]
Q_CUES = [(0.0, 'whoosh', 0.4), (0.1, 'pop', 0.5), (0.6, 'click', 0.5), (1.05, 'click', 0.5), (1.5, 'click', 0.5), (0.87, 'pop', 0.6),
          (1.64, 'vroom', 0.6), (GREEN, 'ding', 0.6), (GREEN + 0.02, 'vroom', 1.0), (GREEN + 0.05, 'screech', 0.4)]
CUES = Q_CUES + kit.warp_cues(CUES, ANCH, END_T) + TEASE_CUES

kit.setup(HERE, NEW, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True,
          end=('car stuff, explained', 'tell me in the comments'))

if __name__ == '__main__':
    kit.main()
