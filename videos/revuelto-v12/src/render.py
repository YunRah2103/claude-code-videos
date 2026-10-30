"""Renders 'Revuelto V12': a 6.5-litre V12 plus three electric motors, 1,001 hp, unveiled 2023 as the Aventador's
successor.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, rev counter, mixer). Word times
come from align.py -> words.json (aligned on out/revuelto-v12/vo_final.wav, the audio that ships). Cars are
generic pixel wedges with no badges or lettering; the real car appears only in the framed Commons photo.
Shots:
  1 hook     0.00  a pixel V12 fires cylinder by cylinder; three motors pop in around it; 'Three motors, one V12.'
  2 power    5.55  garage: the framed real photo pops in, the power counter runs to 1,001 HP; '1,001 horsepower'
  3 unveil   8.45  2023 badge with confetti; the dark predecessor silhouette fades into the new lime wedge
  4 finished 13.25 the wedge revs with the V12 glowing over it; 'V12 isn't finished'
  5 teaser   15.60 shared NEXT EPISODE ending
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
from pixanim.autos import supercar, v12, motor

WORDS = kit.load_words(HERE)
DUR, END_T = 17.3, 15.64
VO = os.path.join(HERE, '..', '..', '..', 'out', 'revuelto-v12', 'vo_final.wav')


def firing(t): return int(t * 24) % 12   # cylinder that glows: a quick ripple along both banks


# ================================================================== shot 1: hook, one V12 and three motors
MOT = ((250, 640), (830, 640), (540, 1290))          # motor positions around the engine
MOT_T = (3.96, 4.36, 4.77)                            # 'three', 'electric', 'motors'
P1 = Presenter([
    (1.7, dict(path=Track([(1.7, (1300, 380)), (2.1, (900, 1500), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.1, dict(ground=1500, squash=True, arms='point', point=(540, 960), look=(540, 960), expr='smirk', face=None)),
    (3.96, dict(arms='cheer', point=None, look=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.22)), (0.0, (540, 960, 1.22)), (2.0, (540, 940, 1.12), 'io'), (3.9, (540, 960, 1.04), 'io'),
                     (5.6, (540, 960, 1.08), 'io')],
              kicks=[(0.1, 0.12, 540, 960), (2.98, 0.1, 540, 960), (3.96, 0.08, *MOT[0]), (4.36, 0.08, *MOT[1]), (4.77, 0.14, 540, 1100)],
              shakes=[(0.1, 0.3, 10), (4.77, 0.3, 10)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 0.05, 0.3)
    shake = 3 * math.sin(t * 60) if t > 0.1 else 0
    blit(fg, up(v12(firing(t)), 11), 540 + shake, 960, k, k, 0, anchor='center')
    fx.rays(fg, t, 0.1, 540, 960, GLOW, life=0.7)
    if t >= 0.1: fx.puff(fg, t, 0.12, 900, 980, seed=3, drift=(160, -200))
    dg.label(fg, t, 2.01, '6.5 L V12', (540, 760), (540, 520), '#ffd23f', '#1a1a2e', '#e8b923', s=9, t1=3.8)
    for i, ((x, y), t0) in enumerate(zip(MOT, MOT_T)):
        if t < t0: continue
        on = 0.6 + 0.4 * math.sin(t * 9 + i)
        kk = popin(t, t0, 0.25)
        blit(fg, up(motor(round(on * 4) / 4), 9), x, y + 6 * math.sin(t * 5 + i), kk, kk, 0, anchor='center')
        fx.burst(fg, t, t0, x, y, (60, 200, 90), n=10, r0=70, r1=240, seed=10 + i)
        fx.ring(fg, t, t0, x, y, GLOW, r1=260)
        u = clamp((t - t0) / 0.25)                                       # glowing link into the engine
        if u > 0:
            d = ImageDraw.Draw(fg); ex, ey = lerp(x, 540, 0.55 * u), lerp(y, 960, 0.55 * u)
            d.line((x, y, ex, ey), fill=(26, 26, 46), width=22)
            d.line((x, y, ex, ey), fill=(255, 210, 63) if int(t * 10 + i) % 2 else (255, 240, 160), width=10)
    if t >= 4.77: fx.gsparkles(fg, t, 540, 960, 900, 700, n=10, seed=17)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.95, 'Three motors,', YEL, 470, 130, -3)
    title(cv, t, 0.3, 1.95, 'one V12.', YEL, 620, 130, 2)
    title(cv, t, 7.56, 8.35, '1,001 horsepower', RED, 1090, 110, -2)
    title(cv, t, 13.8, 15.5, "V12 isn't finished", GRN, 520, 110, 2)
    photo(cv, t, 5.7, 8.35, 'revuelto', 540, 640, 860, rot=-3, label='THE REAL CAR (2023)', hq=True)


# ================================================================== shot 2: 1,001 horsepower
def hp(t): return int(round(1001 * oc(prog(t, 6.64, 0.9))))
P2 = Presenter([
    (5.5, dict(path=Track([(5.5, (-200, 600)), (5.9, (170, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (5.9, dict(ground=GROUND, squash=True, arms='point', point=(540, 700), look=(540, 700), expr='smile', face=None)),
    (7.56, dict(arms='shock', point=None, look=None, look_camera=True, expr='shock', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(5.55, (540, 960, 1.1)), (7.5, (540, 990, 1.16), 'io'), (8.45, (540, 990, 1.18))],
              kicks=[(5.75, 0.08, 540, 700), (6.64, 0.1, 540, 1100), (7.56, 0.2, 540, 1100)], shakes=[(7.56, 0.35, 14)])


def shot_power(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 760, GROUND, 520, s=6)
    blit(fg, up(supercar('wedge', int(t * 40) % 360 // 15 * 15 if t > 7.56 else 0, True), 6), 760, GROUND)
    if t >= 6.64:
        k = popin(t, 6.64, 0.25) * popout(t, 7.5, 0.12)                   # counter, then the title takes its place
        blit(fg, fx.big('badge', f'{hp(t):,} HP', '#ffd23f', '#1a1a2e', '#e8b923', s=12), 540, 1100, k, k, -2 + 2 * math.sin(t * 5), anchor='center')
        fx.sparkles(fg, t, 540, 1100, 760, 200, n=8, seed=21)
    if t >= 7.56:
        fx.burst(fg, t, 7.56, 540, 1100, RED, n=18, seed=22); fx.ring(fg, t, 7.56, 540, 1100, GLOW, r1=520)
        for k in range(4): fx.puff(fg, t, 7.56 + k * 0.05, 470, GROUND - 40, seed=23 + k, drift=(-260, -80), col=(200, 204, 214))
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: unveiled 2023, successor to the old V12
MORPH = 12.39                                          # 'Aventador.': the old silhouette fades into the new car
P3 = Presenter([
    (8.4, dict(path=Track([(8.4, (1300, 500)), (8.8, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (8.8, dict(ground=GROUND, squash=True, arms='point', point=(540, 640), look=(540, 640), expr='grin', face=None)),
    (10.5, dict(arms='point', point=(400, GROUND - 150), look=(400, GROUND - 150), expr='smile')),
    (MORPH, dict(arms='shock', point=None, look=(400, GROUND - 150), expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(8.45, (540, 900, 1.12)), (10.4, (460, 1000, 1.16), 'io'), (MORPH, (420, 1020, 1.22), 'io'), (13.3, (440, 1010, 1.24))],
              kicks=[(9.37, 0.14, 540, 640), (11.31, 0.1, 400, 880), (MORPH, 0.16, 400, 1050)], shakes=[(MORPH, 0.25, 10)])


def shot_unveil(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= 9.37:
        k = popin(t, 9.37, 0.25) * popout(t, 10.35)
        blit(fg, fx.big('badge', '2023', '#ffffff', '#1a1a2e', '#d6d9e2', s=13), 540, 640, k, k, -3, anchor='center')
        fx.burst(fg, t, 9.37, 540, 640, GLOW, n=14, seed=31)
        fx.confetti(fg, t, 9.37, 540, 600, n=30, seed=32)
    x = 400
    if t >= 10.4:
        a = 1 - clamp((t - MORPH) / 0.45)                                   # old silhouette fades out ...
        k = popin(t, 10.4, 0.25)
        fx.contact_shadow(fg, x, GROUND, 520, s=6)
        if a > 0:
            old = up(supercar('old'), 6)
            if a < 1: old.putalpha(old.getchannel('A').point(lambda v: int(v * a)))
            blit(fg, old, x, GROUND, k, k)
        if t >= MORPH:                                                      # ... while the new wedge fades in
            new = up(supercar('wedge', 0, True), 6); b = clamp((t - MORPH) / 0.45)
            if b < 1: new.putalpha(new.getchannel('A').point(lambda v: int(v * b)))
            blit(fg, new, x, GROUND)
            fx.dust(fg, t, MORPH, x, GROUND - 20, n=14, seed=33)
            fx.gsparkles(fg, t, x, GROUND - 150, 620, 260, n=8, seed=34)
        dg.label(fg, t, 10.6, 'OLD V12', (x - 60, GROUND - 170), (300, 700), '#ffffff', '#1a1a2e', '#d6d9e2', s=8, t1=MORPH - 0.05)
    if t >= 11.31:
        dg.label(fg, t, 11.31, 'HYBRID', (x + 120, GROUND - 160), (620, 640), '#7fe3a0', '#1a1a2e', '#3cc85a', s=9, t1=13.2)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: the V12 isn't finished
REV = 14.68
P4 = Presenter([
    (13.25, dict(path=Track([(13.25, (-200, 500)), (13.6, (180, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (13.6, dict(ground=GROUND, squash=True, arms='point', point=(640, 760), look=(640, 760), expr='smirk', face=None)),
    (REV, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(13.25, (560, 960, 1.12)), (REV, (600, 980, 1.2), 'io'), (15.6, (600, 980, 1.26), 'io')],
              kicks=[(13.85, 0.1, 640, 760), (REV, 0.24, 640, 1000)], shakes=[(REV, 0.6, 16)])


def shot_finished(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 13.3, 640, 760, GLOW, hold=True, r=520)
    k = popin(t, 13.3, 0.3)
    blit(fg, up(v12(firing(t * (2 if t > REV else 1))), 8), 640, 760, k, k, 2 * math.sin(t * 4), anchor='center')
    fx.contact_shadow(fg, 660, GROUND, 520, s=6)
    rev = t >= REV
    blit(fg, up(supercar('wedge', int(t * 60) % 360 // 15 * 15 if rev else 0, True), 6), 660 + (4 * math.sin(t * 70) if rev else 0), GROUND)
    if rev:
        for k2 in range(5): fx.puff(fg, t, REV + k2 * 0.08, 360, GROUND - 50, seed=40 + k2, drift=(-300, -60), col=(200, 204, 214))
        fx.ring(fg, t, REV, 640, 760, GLOW, r1=560); fx.burst(fg, t, REV, 640, 760, GLOW, n=16, seed=45)
        fx.sparkles(fg, t, 640, 760, 700, 400, n=8, seed=46)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


shot_teaser, TEASE_CUES = kit.teaser(15.6, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (5.55, shot_power), (8.45, shot_unveil), (13.25, shot_finished), (15.6, shot_teaser)]
TRANS = {1: (5.55, 5.75, 'whip', dict(dx=1)), 2: (8.45, 8.65, 'push', None), 3: (13.25, 13.45, 'iris', (540, 960)),
         4: (15.6, 15.8, 'whip', dict(dx=1))}
KEYCOL = {'revuelto': YEL, '6.5-litre': YEL, 'v12': YEL, 'motors': GRN, 'together': GRN, '1,001': RED, 'unveiled': YEL,
          '2023': YEL, 'hybrid': GRN, 'aventador': RED, 'proof': YEL, 'finished': GRN, 'follow': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.6), (0.1, 'vroom', 0.9), (0.3, 'pop', 0.5),
    (2.01, 'pop', 0.6), (2.1, 'thump', 0.4), (2.98, 'click', 0.5),
    (3.96, 'pop', 0.7), (4.36, 'pop', 0.7), (4.77, 'pop', 0.7), (4.79, 'sparkle', 0.7), (4.8, 'ding', 0.6),
    (5.75, 'pop', 0.6), (5.9, 'thump', 0.4), (6.64, 'whoosh', 0.5), (7.56, 'boom', 0.5), (7.58, 'stamp', 0.8), (7.6, 'vroom', 0.7),
    (8.8, 'thump', 0.4), (9.37, 'pop', 0.8), (9.39, 'confetti', 0.7), (10.4, 'pop', 0.5), (10.6, 'click', 0.4), (11.31, 'pop', 0.6),
    (MORPH, 'whoosh', 0.6), (MORPH + 0.02, 'sparkle', 0.8),
    (13.6, 'thump', 0.4), (13.85, 'click', 0.4), (REV, 'vroom', 1.0), (REV + 0.02, 'ding', 0.6), (REV + 0.04, 'sparkle', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='yellow', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
