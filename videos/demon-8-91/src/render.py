"""Renders 'Demon, 8.91': 1,025 hp, an NHRA-certified 8.91 s quarter mile at 151 mph.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, rev counter, mixer). Word times
come from align.py -> words.json (aligned on out/demon-8-91/vo_final.wav, the audio that ships; the read had no
outro, so align.py appends the same voice's 'Follow for the next one.'). The car is a generic pixel coupe with no
badges or lettering; the real car appears only in the framed Commons photo (a showroom shot: Commons has no
openly licensed photo of a Demon 170 at a drag strip).
Shots:
  1 tree     0.00  night drag strip: the light tree counts down, green, the coupe launches; '8.91 seconds.'
  2 power    3.10  garage: the framed real photo pops in; the power counter runs to 1,025 HP
  3 quarter  5.95  the quarter mile: timer runs, CERTIFIED stamp, 8.91 S slams at the finish line
  4 speed   11.70  speedometer close-up: the needle hits 151, camera punch and speed lines; '151 miles an hour'
  5 teaser  14.45  shared NEXT EPISODE ending
"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.dash import Dashboard
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up
from pixanim.autos import muscle, light_tree

WORDS = kit.load_words(HERE)
DUR, END_T = 16.5, 14.46
CS = 4                                                 # car scale on the street


def spin(x): return int(x * 0.5) % 360 // 15 * 15


def finish_line(fg, x):
    d = ImageDraw.Draw(fg)
    for j in range(8):
        for i in range(2):
            d.rectangle((x + i * 18, ROAD_Y - 70 + j * 18, x + i * 18 + 17, ROAD_Y - 70 + j * 18 + 17), fill=(244, 244, 244) if (i + j) % 2 else (26, 26, 34))


# ================================================================== shot 1: hook, the light tree
GO = 1.05
def stage1(t): return 0 if t < 0.15 else 1 if t < 0.45 else 2 if t < 0.75 else 3 if t < GO else 4
def car_x1(t): return 300 if t < GO else 300 + 2200 * ic(prog(t, GO, 1.1))
CAM1 = Camera(W, H, [(-1.0, (520, 1000, 1.25)), (0.0, (520, 1000, 1.25)), (GO, (440, 1060, 1.35), 'io'), (1.8, (560, 1000, 1.15), 'oc'), (3.1, (540, 980, 1.18))],
              kicks=[(0.15, 0.06, 540, 800), (0.45, 0.06, 540, 800), (0.75, 0.06, 540, 800), (GO, 0.24, 300, 1080), (1.91, 0.12, 540, 1000)],
              shakes=[(GO, 0.6, 16)])


def shot_tree(t):
    scroll = 0 if t < GO else 1600 * ic(prog(t, GO, 1.0)) + max(0, t - GO - 1.0) * 1600
    img = street(t, scroll); fg = layer()
    st = stage1(t)
    blit(fg, up(light_tree(st), 9), 560, ROAD_Y - 160, 1, 1, 0)
    if st >= 1: fx.ring(fg, t, [0.15, 0.45, 0.75, GO][st - 1], 560, 700, GLOW if st < 4 else (60, 220, 110), life=0.25, r1=200)
    if t < 2.6:
        x = car_x1(t); launch = math.exp(-max(0, t - GO) * 5) * (t >= GO)
        blit(fg, up(muscle(spin(x), True, round(launch * 4) / 4), CS), x + (3 * math.sin(t * 70) if t < GO else 0), ROAD_Y + 20)
        if t >= GO:
            for k in range(6): fx.puff(fg, t, GO + k * 0.06, x - 150, ROAD_Y - 10, seed=20 + k, drift=(-300, -80), col=(214, 216, 224))
            fx.speed_lines(fg, 1.0 - 0.6 * prog(t, 1.8, 0.8), int(t * 12) % 5, col=(200, 204, 220))
        else:
            fx.puff(fg, t, 0.3, x - 160, ROAD_Y - 10, seed=19, drift=(-120, -100))
    if t >= 1.91: fx.sparkles(fg, t, 560, 760, 700, 300, n=6, seed=6)
    return CAM1.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, GO, 2.95, '8.91 seconds.', RED, 560, 140, -3)   # lands on the green light
    title(cv, t, 12.13, 14.3, '151 miles an hour', YEL, 520, 110, 2)
    photo(cv, t, 3.2, 5.85, 'demon', 540, 640, 820, rot=-3, label='THE REAL CAR', hq=True)


# ================================================================== shot 2: 1,025 horsepower
def hp(t): return int(round(1025 * oc(prog(t, 3.43, 1.0))))
P2 = Presenter([
    (3.05, dict(path=Track([(3.05, (1300, 500)), (3.45, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (3.45, dict(ground=GROUND, squash=True, arms='point', point=(540, 640), look=(540, 640), expr='smile', face=None)),
    (4.48, dict(arms='shock', point=None, look=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(3.1, (540, 960, 1.1)), (4.48, (540, 1000, 1.16), 'io'), (5.95, (540, 1000, 1.2))],
              kicks=[(3.3, 0.08, 540, 640), (3.43, 0.08, 400, 1150), (4.48, 0.2, 400, 1150)], shakes=[(4.48, 0.35, 14)])


def shot_power(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 4.48, 400, 1150, GLOW, life=0.8)
    if t >= 3.43:
        k = popin(t, 3.43, 0.25) * (fx.slam(t, 4.48) if t >= 4.48 else 1)
        blit(fg, fx.big('badge', f'{hp(t):,} HP', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 400, 1150, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
        fx.sparkles(fg, t, 400, 1150, 600, 200, n=8, seed=21)
    if t >= 4.48:
        fx.burst(fg, t, 4.48, 400, 1150, RED, n=18, seed=22); fx.confetti(fg, t, 4.5, 400, 900, n=24, seed=23)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the quarter mile
RUN0, RUN1 = 6.3, 9.3                                  # timer runs 0.00 -> 8.91 while the car covers the strip
def run(t): return clamp((t - RUN0) / (RUN1 - RUN0))
def timer(t): return 8.91 * run(t)
def dist(t): return 6200 * io(run(t)) ** 1.15             # world scroll: the car stays near centre, the strip moves
LINE_X = 760
P3 = Presenter([
    (9.4, dict(path=Track([(9.4, (1300, 300)), (9.8, (880, ROAD_Y + 20), 'oc')]), size=5, legs='auto', arms='fly', expr='wow', face=-1, ground=None)),
    (9.8, dict(ground=ROAD_Y + 20, squash=True, arms='cheer', look_camera=True, expr='grin', face=None)),
], words=WORDS, base_size=5)
CAM3 = Camera(W, H, [(5.95, (540, 1000, 1.12)), (RUN0, (500, 1040, 1.2), 'io'), (RUN1, (620, 1000, 1.24), 'io'), (11.7, (580, 980, 1.16), 'io')],
              kicks=[(6.22, 0.08, 540, 640), (7.35, 0.14, 760, 760), (RUN1, 0.26, 540, 760)], shakes=[(RUN1, 0.4, 14), (6.35, 0.4, 10)])


def shot_quarter(t):
    sc = dist(t); img = street(t, sc); fg = layer()
    x = lerp(220, 520, oc(run(t)))
    if t >= RUN1:
        x = 520 + (t - RUN1) * 1400
    if RUN1 - 0.5 < t < RUN1 + 0.6:
        finish_line(fg, LINE_X + (RUN1 - t) * 1200)
    fast = RUN0 <= t < RUN1 + 0.6
    if x < 1300:
        blit(fg, up(muscle(spin(sc + x), True, 0.0), CS), x + (2 * math.sin(t * 60) if fast else 0), ROAD_Y + 20)
    if fast:
        fx.speed_lines(fg, 0.5 + 0.5 * run(t), int(t * 12) % 5, col=(200, 204, 220))
        fx.puff(fg, t, RUN0, 120, ROAD_Y - 10, seed=31, drift=(-300, -60), col=(214, 216, 224))
    dg.label(fg, t, 6.22, 'QUARTER MILE', (x + 120, ROAD_Y - 120), (540, 640), '#ffffff', '#1a1a2e', '#d6d9e2', s=8, t1=RUN1 - 0.15)
    v = timer(t)
    if t >= 6.0:
        k = popin(t, 6.0, 0.25) * (fx.slam(t, RUN1) if t >= RUN1 else 1)
        blit(fg, fx.big('badge', f'{v:.2f} S', '#ffd23f' if t >= RUN1 else '#ffffff', '#1a1a2e', '#e8b923' if t >= RUN1 else '#d6d9e2', s=12 if t >= RUN1 else 10),
             540, 800, k, k, -2, anchor='center')
    if t >= 7.35: fx.stamp_at(fg, t, 7.35, 'CERTIFIED', 760, 960, rot=-10, s=8)
    if t >= RUN1:
        fx.burst(fg, t, RUN1, 540, 800, GLOW, n=18, seed=33); fx.ring(fg, t, RUN1, 540, 800, GLOW, r1=520)
        fx.confetti(fg, t, RUN1 + 0.05, 540, 700, n=30, seed=34)
    if t >= 10.34: fx.sparkles(fg, t, 540, 800, 700, 260, n=8, seed=35)
    P3.draw(fg, t)
    return CAM3.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: 151 mph
DASH = Dashboard()
HIT, PUNCH = 12.13, 13.35
def mph(t): return int(round(151 * oc(prog(t, 11.75, HIT - 11.75 + 0.25))))
CAM4 = Camera(W, H, [(11.7, (720, 900, 1.3)), (HIT, (790, 860, 1.42), 'io'), (PUNCH, (780, 880, 1.5), 'io'), (14.5, (760, 900, 1.36), 'io')],
              kicks=[(HIT, 0.16, 790, 800), (PUNCH, 0.3, 790, 800)], shakes=[(HIT, 0.3, 10), (PUNCH, 0.6, 18)])


def shot_speed(t):
    v = mph(t)
    sdeg = 225 - 270 * v / 180 + (1.5 * math.sin(t * 50) if v >= 151 else 0)
    img = DASH.frame(t, rpm_deg=225 - 230 * min(1, v / 120) + 3 * math.sin(t * 40), speed_deg=sdeg, lcd=f'{v}')
    fg = layer()
    if t >= HIT:
        fx.ring(fg, t, HIT, 790, 800, GLOW, r1=360); fx.burst(fg, t, HIT, 790, 800, GLOW, n=14, seed=41)
        k = popin(t, HIT, 0.25)
        blit(fg, fx.big('badge', '151 MPH', '#ffd23f', '#1a1a2e', '#e8b923', s=8), 590, 690, k, k, 3, anchor='center')
    if t >= PUNCH:
        fx.speed_lines(fg, 1.0 - 0.7 * prog(t, PUNCH, 1.0), int(t * 14) % 5, col=(230, 232, 240))
        fx.sparkles(fg, t, 790, 900, 700, 400, n=8, seed=42)
    img.alpha_composite(fg)
    out = CAM4.apply(img.convert('RGB'), t, (14, 15, 18))
    if PUNCH <= t < PUNCH + 0.12:                                     # finish-line flash on the punch
        out = Image.blend(out, Image.new('RGB', (W, H), (255, 255, 255)), 0.55 * (1 - (t - PUNCH) / 0.12))
    return out


shot_teaser, TEASE_CUES = kit.teaser(14.45, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_tree), (3.1, shot_power), (5.95, shot_quarter), (11.7, shot_speed), (14.45, shot_teaser)]
TRANS = {1: (3.1, 3.3, 'whip', dict(dx=1)), 2: (5.95, 6.15, 'push', None), 3: (11.7, 11.9, 'iris', (790, 800)),
         4: (14.45, 14.65, 'whip', dict(dx=1))}
KEYCOL = {'dodge': YEL, '170': RED, '1,025': RED, 'quarter-mile': YEL, 'certified': GRN, 'nhra': GRN,
          '8.91': RED, '151': YEL, 'hour': GRN, 'follow': YEL}
CUES = [
    (0.0, 'whoosh', 0.3), (0.15, 'click', 0.7), (0.45, 'click', 0.7), (0.75, 'click', 0.7), (GO, 'ding', 0.8),
    (GO, 'vroom', 1.0), (GO + 0.02, 'pop', 0.7), (GO + 0.04, 'screech', 0.6), (1.91, 'stamp', 0.9), (1.93, 'sparkle', 0.6),
    (3.2, 'pop', 0.6), (3.45, 'thump', 0.4), (3.43, 'whoosh', 0.4), (4.48, 'boom', 0.5), (4.5, 'stamp', 0.8), (4.52, 'confetti', 0.6),
    (6.0, 'pop', 0.5), (6.22, 'pop', 0.6), (RUN0, 'vroom', 1.0), (7.35, 'stamp', 0.8), (8.1, 'click', 0.4),
    (RUN1, 'ding', 0.9), (RUN1 + 0.02, 'boom', 0.4), (RUN1 + 0.05, 'confetti', 0.7), (9.8, 'thump', 0.4), (10.34, 'sparkle', 0.6),
    (11.75, 'vroom', 0.8), (HIT, 'ding', 0.7), (HIT + 0.02, 'pop', 0.6), (PUNCH, 'whoosh', 1.0), (PUNCH + 0.02, 'boom', 0.4),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='yellow', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
