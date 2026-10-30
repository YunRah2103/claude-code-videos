"""Renders 'Ford GT, 2016': a class win at Le Mans in 2016, 50 years after the first overall win there in 1966.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, rev counter, mixer). Word times
come from align.py -> words.json (aligned on out/ford-gt-2016/vo_final.wav, the audio that ships; the 8.5 s read
gets a 1.8 s silent hook, more air after each sentence, and the same voice's 'Follow for the next one.'). The racers
are generic pixel coupes with plain number roundels and no badges or sponsor text; the real car appears only in
the framed Commons photo.
Shots:
  1 finish   0.00  night circuit: the blue GT crosses the line under the chequered flag; '2016'
  2 photo    2.90  garage: the framed real photo of the 2016 car at Le Mans; CLASS WIN and LE MANS tags
  3 years    6.40  a calendar flips back from 2016 to 1966; -50 YEARS; the 1960s racer rolls in; '50 years'
  4 trophy  10.35  the trophy shines; 'Le Mans'
  5 teaser  11.65  shared NEXT EPISODE ending
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
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up
from pixanim.autos import racer, flag, trophy, year_cal

WORDS = kit.load_words(HERE)
DUR, END_T = 15.0, 11.67
CS = 4


def spin(x): return int(x * 0.5) % 360 // 15 * 15


def finish_line(fg, x, top=ROAD_Y - 80, rows=8):
    d = ImageDraw.Draw(fg)
    for j in range(rows):
        for i in range(2):
            d.rectangle((x + i * 18, top + j * 18, x + i * 18 + 17, top + j * 18 + 17), fill=(244, 244, 244) if (i + j) % 2 else (26, 26, 34))


# ================================================================== shot 1: hook, across the line
CROSS = 1.0                                             # nose crosses the line
LINE_X = 620
def car_x1(t): return lerp(-500, 1700, (t + 0.2) / 2.6)
CAM1 = Camera(W, H, [(-1.0, (540, 1000, 1.2)), (0.0, (540, 1000, 1.2)), (CROSS, (600, 1040, 1.3), 'io'), (2.9, (560, 1000, 1.18), 'io')],
              kicks=[(0.05, 0.1, 540, 700), (CROSS, 0.22, LINE_X, 1060), (2.04, 0.14, 540, 760)], shakes=[(CROSS, 0.4, 14)])


def shot_finish(t):
    img = street(t, t * 1500); fg = layer()
    finish_line(fg, LINE_X - 18 - t * 1500 % 1 * 0)                       # the line is painted on the road
    x = car_x1(t)
    blit(fg, up(racer('68', spin(t * 1500), True), CS), x, ROAD_Y + 20)
    fx.speed_lines(fg, 0.7, int(t * 12) % 5, col=(200, 204, 220))
    blit(fg, up(flag(int(t * 12) % 8), 9), LINE_X + 160, ROAD_Y - 330, 1, 1, -8 + 10 * math.sin(t * 9), anchor='center')
    if t >= CROSS:
        fx.burst(fg, t, CROSS, LINE_X, ROAD_Y - 150, GLOW, n=16, seed=2); fx.ring(fg, t, CROSS, LINE_X, ROAD_Y - 150, GLOW, r1=520)
        fx.confetti(fg, t, CROSS, 540, 600, n=50, seed=3)
    if t >= 2.04:
        k = popin(t, 2.04, 0.25)
        blit(fg, fx.big('badge', 'CLASS WIN', '#7fe3a0', '#1a1a2e', '#3cc85a', s=9), 540, 780, k, k, -3, anchor='center')
    return CAM1.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, 0.05, 2.8, '2016', YEL, 500, 220, -3)
    title(cv, t, 6.78, 8.6, '50 years', RED, 470, 140, 2)
    title(cv, t, 10.4, 11.6, 'Le Mans', GRN, 470, 150, -2)
    photo(cv, t, 3.0, 6.3, 'fordgt', 540, 600, 900, rot=-3, label='THE REAL CAR, LE MANS 2016', hq=True)


# ================================================================== shot 2: the real car
P2 = Presenter([
    (2.85, dict(path=Track([(2.85, (1300, 500)), (3.25, (960, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (3.25, dict(ground=GROUND, squash=True, arms='point', point=(540, 600), look=(540, 600), expr='smile', face=None)),
    (3.9, dict(arms='cheer', point=None, look=None, look_camera=True, expr='wow', squash=True)),
    (4.7, dict(arms='thumb', expr='grin')),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.9, (540, 960, 1.08)), (4.7, (540, 980, 1.14), 'io'), (6.4, (540, 980, 1.18), 'io')],
              kicks=[(3.1, 0.08, 540, 600), (3.9, 0.14, 420, 950), (4.7, 0.14, 420, 950)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 420, GROUND, 460, s=5)
    blit(fg, up(racer('68', 0, True), 5), 420, GROUND)
    if t >= 3.9:
        k = popin(t, 3.9, 0.25) * popout(t, 4.6, 0.12)
        blit(fg, fx.big('tag', 'CLASS WIN', '#fff6e0', '#1a1a2e', s=7), 420, 950, k, k, -6 + 2 * math.sin(t * 4), anchor='center')
        fx.burst(fg, t, 3.9, 320, 950, GLOW, n=10, seed=11)
    if t >= 4.7:
        k = popin(t, 4.7, 0.25)
        blit(fg, fx.big('badge', 'LE MANS', '#ffffff', '#1a1a2e', '#d6d9e2', s=8), 420, 950, k, k, 4, anchor='center')
        fx.sparkles(fg, t, 540, 1050, 700, 200, n=6, seed=12)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the calendar flips back 50 years
F0, F1 = 6.78, 7.6                                      # '50' .. 'after': 2016 -> 1966
def year(t): return 2016 - int(round(50 * io(prog(t, F0, F1 - F0))))
OLD_IN = 9.48                                           # '1966.'
P3 = Presenter([
    (6.35, dict(path=Track([(6.35, (-200, 500)), (6.75, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (6.75, dict(ground=GROUND, squash=True, arms='point', point=(560, 640), look=(560, 640), expr='smile', face=None)),
    (F1, dict(arms='shock', point=None, look=None, look_camera=True, expr='wow', squash=True)),
    (OLD_IN, dict(arms='point', point=(640, GROUND - 120), look=(640, GROUND - 120), expr='grin')),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(6.4, (560, 900, 1.1)), (F1, (560, 760, 1.2), 'io'), (OLD_IN, (600, 960, 1.1), 'io'), (10.4, (600, 960, 1.14))],
              kicks=[(F0, 0.1, 560, 640), (F1, 0.22, 560, 640), (8.28, 0.1, 820, 900), (OLD_IN, 0.18, 640, 1050)], shakes=[(F1, 0.3, 12)])


def shot_years(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    y = year(t); flipping = F0 <= t < F1
    k = popin(t, 6.45, 0.3) * (fx.slam(t, F1, k=0.8) if t >= F1 else 1)
    sq = 1 - 0.3 * abs(math.sin(t * 40)) if flipping else 1                  # pages flicking over
    blit(fg, up(year_cal(y), 11), 560, 640, k, k * sq, 0, anchor='center')
    if flipping:
        for i in range(3): fx.puff(fg, t, F0 + i * 0.2, 560, 420, seed=30 + i, life=0.5, size=0.6, drift=(80 - 80 * i, -160), col=(240, 240, 236))
    if t >= F0:
        kk = popin(t, F0, 0.25)
        blit(fg, fx.big('badge', '-50 YEARS', '#ffffff', '#d6303a', '#d6d9e2', s=7), 740, 870, kk, kk, 6 + 2 * math.sin(t * 5), anchor='center')
    if t >= F1: fx.burst(fg, t, F1, 560, 640, GLOW, n=16, seed=33); fx.ring(fg, t, F1, 560, 640, GLOW, r1=480)
    dg.label(fg, t, 8.28, 'FIRST OVERALL WIN', (480, 880), (460, 1010), '#ffd23f', '#1a1a2e', '#e8b923', s=7, t1=OLD_IN - 0.1)
    if t >= OLD_IN:
        x = lerp(1500, 640, oc(prog(t, OLD_IN, 0.5)))
        fx.contact_shadow(fg, x, GROUND, 460, s=5)
        blit(fg, up(racer('2', spin(x), True, old=True), 5), x, GROUND)
        if t >= OLD_IN + 0.5: fx.dust(fg, t, OLD_IN + 0.5, x - 200, GROUND, n=10, seed=34)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: the trophy
CAM4 = Camera(W, H, [(10.35, (540, 900, 1.08)), (10.4, (540, 880, 1.18), 'io'), (11.7, (540, 880, 1.24), 'io')],
              kicks=[(10.4, 0.2, 540, 880)], shakes=[(10.4, 0.25, 10)])


def shot_trophy(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 10.4, 540, 900, GLOW, hold=True, r=620, n=12)
    k = fx.slam(t, 10.4, k=0.8) * popin(t, 10.4, 0.25)
    blit(fg, up(trophy(), 16), 540, 900 + 8 * math.sin(t * 3), k, k, 2 * math.sin(t * 2), anchor='center')
    fx.burst(fg, t, 10.4, 540, 900, GLOW, n=18, seed=41); fx.sparkles(fg, t, 540, 900, 600, 520, n=10, seed=42)
    fx.glint(fg, t, 10.7, 540, 820, r=150)
    fx.confetti(fg, t, 10.45, 540, 600, n=40, seed=43)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


shot_teaser, TEASE_CUES = kit.teaser(11.65, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_finish), (2.9, shot_photo), (6.4, shot_years), (10.35, shot_trophy), (11.65, shot_teaser)]
TRANS = {1: (2.9, 3.1, 'whip', dict(dx=1)), 2: (6.4, 6.6, 'push', None), 3: (10.35, 10.55, 'iris', (540, 900)),
         4: (11.65, 11.85, 'whip', dict(dx=1))}
KEYCOL = {'2016': YEL, 'gt': YEL, 'class': GRN, 'mans': GRN, '50': RED, "ford's": YEL, 'overall': GRN, 'win': YEL, '1966': RED, 'follow': YEL}
CUES = [
    (0.0, 'vroom', 0.8), (0.05, 'pop', 0.7), (0.3, 'whoosh', 0.6), (CROSS, 'whoosh', 0.9), (CROSS + 0.02, 'ding', 0.8),
    (CROSS + 0.04, 'confetti', 0.8), (2.04, 'pop', 0.7), (2.06, 'sparkle', 0.5),
    (3.0, 'pop', 0.7), (3.25, 'thump', 0.4), (3.9, 'pop', 0.6), (4.7, 'pop', 0.6), (4.72, 'sparkle', 0.5),
    (6.45, 'pop', 0.6), (6.75, 'thump', 0.4), (F0, 'whoosh', 0.6)] + [(F0 + k * 0.08, 'click', 0.35) for k in range(10)] + [
    (F1, 'stamp', 0.9), (F1 + 0.02, 'ding', 0.6), (8.28, 'pop', 0.6), (OLD_IN, 'vroom', 0.8), (OLD_IN + 0.5, 'thump', 0.4),
    (10.4, 'boom', 0.4), (10.42, 'ding', 0.9), (10.44, 'confetti', 0.8), (10.46, 'sparkle', 0.8),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
