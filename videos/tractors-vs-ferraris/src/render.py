"""Renders 'Tractors vs. Ferraris': the tractor maker who found his own clutch inside a sports car.

Template: videos/ac-idle -> jaguar-rise-fall shot structure; captions, progress bar, photo cards, mixer and the
NEXT EPISODE ending now live in shared/episode.py. Word times come from align.py -> words.json (the voiceover
is the timing spine). Speech runs 0-17.0 s; the 'Follow' card holds to 18.6 s. The rival sports car is generic.
Shots:
  1 hook    0.00  a pixel tractor rolls into a garage of sports cars; 'TRACTORS VS. FERRARIS'; 2241R photo on 'tractors'
  2 rival   3.45  whip; he buys a red sports car; it breaks: smoke, x1 x2 x3 wrench counter, BROKEN stamp on 'part'
  3 clutch  7.10  iris into the clutch; it spins and is labelled on 'clutch'; a tractor clutch slides in on 'tractors': SAME PART
  4 enzo   11.05  push; he tells the rival; the rival car's bubble answers 'STICK TO TRACTORS!' and a tractor drops in
  5 build  15.30  whip; his own sports car rolls out of the light: 350 GT photo, confetti on 'sports car'
  6 teaser 17.10  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, layer, finish, draw_car, photo, title
from pixanim.motion import Track, prog, lerp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 18.6, 17.1


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def tractor(spin=0):
    """Side-view 1950s farm tractor (72x52 grid): big rear wheel, small front wheel, orange bonnet, exhaust stack."""
    img = Image.new('RGBA', (72, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, shade, hi = (240, 140, 40), (196, 100, 26), (255, 196, 110)
    d.rectangle((50, 6, 52, 22), fill=(60, 63, 71)); d.rectangle((49, 4, 53, 6), fill=(40, 42, 48))     # exhaust stack
    d.polygon([(26, 20), (66, 22), (68, 34), (26, 36)], fill=body)                                           # bonnet
    d.line([(27, 21), (65, 23)], fill=hi); d.rectangle((26, 32, 68, 35), fill=shade)
    for x in range(56, 67, 3): d.line([(x, 25), (x, 31)], fill=shade)                                         # grille slats
    d.rectangle((14, 14, 22, 18), fill=(40, 42, 48)); d.rectangle((20, 10, 22, 22), fill=(40, 42, 48))     # seat
    d.line([(26, 20), (32, 10)], fill=(60, 63, 71), width=2); d.line([(29, 9), (36, 11)], fill=(30, 32, 38), width=2)  # wheel
    d.pieslice((0, 14, 38, 52), 180, 360, fill=body); d.pieslice((3, 17, 35, 49), 180, 360, fill=(0, 0, 0, 0))  # fender
    for cx, cy, r in ((19, 34, 16), (58, 43, 8.5)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(32, 33, 38))
        for k in range(14 if r > 10 else 9):
            a = math.radians(k * (360 / (14 if r > 10 else 9)) + spin)
            d.rectangle((cx + (r - 1) * math.cos(a) - 1, cy + (r - 1) * math.sin(a) - 1, cx + (r - 1) * math.cos(a) + 1,
                         cy + (r - 1) * math.sin(a) + 1), fill=(20, 21, 26))
        d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), fill=(255, 196, 60))
        d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(196, 100, 26))
    return outline(img)


@lru_cache(None)
def clutch(tint=0):
    """Clutch disc face-on (44x44): friction ring, steel plate, damper springs, splined hub."""
    img = Image.new('RGBA', (44, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    ring = [(120, 104, 92), (150, 120, 70)][tint]
    d.ellipse((1, 1, 42, 42), fill=ring)
    for k in range(24):
        a = math.radians(k * 15); d.point((21.5 + 18 * math.cos(a), 21.5 + 18 * math.sin(a)), fill=(80, 70, 62))
    d.ellipse((8, 8, 35, 35), fill=(176, 182, 192)); d.arc((8, 8, 35, 35), 200, 320, fill=(222, 228, 236))
    for k in range(6):
        a = math.radians(k * 60 + 30); x, y = 21.5 + 9 * math.cos(a), 21.5 + 9 * math.sin(a)
        d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=(70, 120, 200)); d.line([(x - 2, y), (x + 2, y)], fill=(150, 190, 240))
    d.ellipse((16, 16, 27, 27), fill=(96, 100, 110)); d.ellipse((19, 19, 24, 24), fill=(30, 32, 38))
    for k in range(8):
        a = math.radians(k * 45); d.point((21.5 + 4 * math.cos(a), 21.5 + 4 * math.sin(a)), fill=(150, 156, 168))
    return outline(img)


def wrench(n): return fx.big('badge', f'FIX X{n}', '#ffffff', '#e0303a', '#d6d9e2', s=7)


# ================================================================== shot 1: hook, a tractor among sports cars
TR1 = 640
def tr1_x(t): return lerp(1500, TR1, oc(prog(t, 0.0, 1.0)))
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-200, 300)), (0.5, (-200, 300)), (1.0, (230, GROUND), 'ic')]), size=7, legs='auto', arms='fly',
                expr='wow', ground=None, face=1)),
    (1.0, dict(ground=GROUND, squash=True, arms='present', look=(TR1, 1000), expr='grin', face=None)),
    (1.81, dict(arms='point', point=(540, 560), look=(540, 560), expr='smile')),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (760, 1000, 1.45)), (0.0, (760, 1000, 1.45)), (1.0, (560, 980, 1.1), 'io'), (2.1, (540, 860, 1.12), 'io'),
                     (3.45, (540, 860, 1.16))],
              kicks=[(0.0, 0.1, 760, 1000), (1.0, 0.12, TR1, 1000), (2.08, 0.1, 540, 560)], shakes=[(0.0, 1.0, 6), (1.0, 0.25, 12)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    for x, col, s in ((180, 'red', 4), (900, 'silver', 4)):                      # parked sports cars in the back
        fx.contact_shadow(fg, x, GROUND - 120, 360, s=S, alpha=90)
        draw_car(fg, col, x, s, y=GROUND - 120, sy=0.85, flip=x > 540)
    x = tr1_x(t)
    fx.contact_shadow(fg, x, GROUND, 560, s=S, alpha=140)
    sr, sv = wob(t, (1.0,), 0.06)
    blit(fg, up(tractor(int((1500 - x) * 0.4) % 360), 8), x + 4 * math.sin(t * 40) * (t < 1.0), GROUND, sr, sv)
    for k in range(4):
        fx.puff(fg, t, 0.1 + k * 0.25, x + 30, GROUND - 430, seed=20 + k, life=0.9, size=0.8, drift=(140, -220), col=(90, 92, 100))
    fx.dust(fg, t, 1.0, x, GROUND - 10, n=14, seed=43)
    fx.burst(fg, t, 1.0, x, GROUND - 220, GLOW, n=12, seed=70)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 1.81, 3.35, 'tractor_2241r', 540, 560, 440, 500, -4, 'LAMBORGHINI TRACTOR, 1960', focus=(0.55, 0.62), zoom=0.35)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.75, 'Tractors vs. Ferraris', YEL, 470, 104, -3)
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 470, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: the sports car keeps breaking
CAR2 = 470
def car2_x(t): return lerp(-500, CAR2, oc(prog(t, 3.45, 0.7)))
P2 = Presenter([
    (3.4, dict(path=Track([(3.4, (1300, 400)), (3.9, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (3.9, dict(ground=GROUND, squash=True, arms='cheer1', expr='grin', face=None, look=(CAR2, 1000))),
    (4.36, dict(arms='present', look=(CAR2, 1000), expr='happy')),
    (5.64, dict(arms='shock', expr='shock', squash=True)),
    (6.31, dict(arms='shrug', expr='sad', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(3.45, (520, 1000, 1.2)), (4.4, (560, 960, 1.12), 'io'), (5.6, (500, 930, 1.22), 'io'), (7.1, (520, 900, 1.3))],
              kicks=[(4.36, 0.1, CAR2, 1000), (5.64, 0.1, CAR2, 900), (6.05, 0.08, CAR2, 900), (6.31, 0.14, CAR2, 820)],
              shakes=[(5.64, 0.3, 12), (6.31, 0.3, 16)])


def shot_rival(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car2_x(t)
    if t < 4.15: fx.speed_lines(fg, 1 - prog(t, 3.45, 0.7), 4, col=(200, 204, 214))
    fx.contact_shadow(fg, x, GROUND, 640, s=S, alpha=140)
    shake = 5 * math.sin(t * 50) if t >= 5.64 else 0
    sr, sv = wob(t, (4.15, 5.64), 0.07)
    draw_car(fg, 'red', x + shake, 7, sx=1.06 * sr, sy=0.86 * sv, dist=x + 500, lights=t < 5.6)
    fx.glint(fg, t, 4.4, CAR2 + 120, GROUND - 230, r=130)
    if t < 5.6: fx.sparkles(fg, t, CAR2, GROUND - 240, 560, 220, n=6, seed=33)
    for k in range(6):                                                            # smoke from the bonnet as it breaks
        fx.puff(fg, t, 5.64 + k * 0.18, CAR2 + 200, GROUND - 230, seed=40 + k, life=0.9, size=1.0, drift=(60, -300), col=(150, 152, 160))
    for i, t0 in enumerate((5.3, 5.64, 6.05)):                                    # repair counter: FIX X1, X2, X3
        if t0 <= t < 7.3:
            k = popin(t, t0, 0.22)
            blit(fg, wrench(i + 1), 330 + 210 * i, 640 - 90 * i, k, k, (-6, 4, -3)[i] + 3 * math.sin(t * 7), anchor='center')
            fx.burst(fg, t, t0, 330 + 210 * i, 640 - 90 * i, RED, n=8, r0=70, r1=200, seed=60 + i)
    fx.stamp_at(fg, t, 6.31, 'BROKEN', CAR2, GROUND - 260, rot=-10, s=13)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the same clutch
CL = (540, 760)
TCL = (760, 760)
P3 = Presenter([
    (7.05, dict(path=Track([(7.05, (-200, 600)), (7.5, (190, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='think', face=1, ground=None)),
    (7.5, dict(ground=GROUND, squash=True, arms='think', look=CL, expr='think', face=None)),
    (8.89, dict(arms='point', point=CL, look=CL, expr='wow', squash=True)),
    (9.96, dict(arms='shock', expr='shock', squash=True, point=None, look=TCL)),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(7.1, (540, 820, 1.35)), (8.89, (540, 780, 1.5), 'io'), (9.6, (600, 860, 1.12), 'io'), (11.05, (600, 860, 1.16))],
              kicks=[(8.28, 0.06, *CL), (8.89, 0.16, *CL), (9.96, 0.14, *TCL), (10.5, 0.08, 640, 520)], shakes=[(9.96, 0.25, 10)])


def cl_x(t): return lerp(540, 330, io(prog(t, 9.5, 0.4)))


def shot_clutch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    spin = t * 160 * (1 - 0.8 * prog(t, 8.89, 0.5))
    kc = popin(t, 7.35, 0.35)
    fx.rays(fg, t, 8.89, cl_x(t), CL[1], GLOW, life=1.0, r=520)
    blit(fg, up(clutch(0), 9), cl_x(t), CL[1], kc, kc, spin, anchor='center')
    fx.ring(fg, t, 8.89, cl_x(t), CL[1], GLOW, life=0.4, r1=330)
    dg.label(fg, t, 8.89, 'CLUTCH', (cl_x(t), CL[1] - 150), lambda t: (cl_x(t), 470), '#ffd23f', '#1a1a2e', '#e8b923', s=8, t1=9.5)
    if t >= 9.75:                                                                 # the tractor clutch slides in beside it
        tx = lerp(1400, TCL[0], oc(prog(t, 9.75, 0.3)))
        blit(fg, up(clutch(0), 9), tx, TCL[1], 1, 1, spin + 30 * (1 - prog(t, 9.75, 0.3)), anchor='center')
        blit(fg, up(tractor(0), 3), tx, TCL[1] + 290, popin(t, 9.96), popin(t, 9.96))
        if t >= 9.96:
            ke = popin(t, 9.96, 0.25)
            blit(fg, kit.text_img('=', YEL, 150), 545, TCL[1], ke, ke, anchor='center')
            kb = popin(t, 10.3, 0.3) * (1 + 0.05 * math.sin(t * 9))
            blit(fg, fx.big('badge', 'SAME PART', '#ffd23f', '#d6303a', '#e8b923', s=11), 545, 470, kb, kb, 4 * math.sin(t * 4), anchor='center')
            fx.burst(fg, t, 10.3, 545, 470, GLOW, seed=90)
            fx.sparkles(fg, t, 545, TCL[1], 760, 300, n=10, seed=91)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: 'stick to tractors'
CAR4 = 700
P4 = Presenter([
    (11.0, dict(path=Track([(11.0, (-200, 500)), (11.4, (230, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (11.4, dict(ground=GROUND, squash=True, arms='point', point=(CAR4, 1000), look=(CAR4, 1000), expr='smile', face=None)),
    (12.95, dict(arms='hips', expr='smirk', point=None, look=(CAR4, 700))),
    (14.02, dict(arms='shock', expr='shock', squash=True)),
    (14.6, dict(arms='hips', expr='sad', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(11.05, (520, 960, 1.15)), (12.95, (640, 860, 1.22), 'io'), (14.39, (560, 900, 1.12), 'io'), (15.3, (540, 880, 1.16))],
              kicks=[(11.85, 0.08, CAR4, 1000), (13.35, 0.12, 700, 560), (14.02, 0.1, 700, 560), (14.39, 0.14, 540, 520)],
              shakes=[(14.39, 0.3, 14)])


def shot_enzo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR4, GROUND, 620, s=S, alpha=140)
    hop = 30 * abs(math.sin((t - 12.95) * 14)) * (12.95 <= t < 14.7)                 # the rival car 'talks' back
    draw_car(fg, 'red', CAR4, 7, y=GROUND - hop, flip=True, sx=1.06, sy=0.86, lights=True)
    if t >= 11.27 and t < 12.9:                                                    # his complaint: a clutch in a bubble
        kb = popin(t, 11.27, 0.25) * popout(t, 12.7)
        blit(fg, fx.big('bubble', 3, s=10), 330, 760, kb, kb, anchor='center')
        blit(fg, up(clutch(0), 4), 330, 740, kb, kb, t * 90, anchor='center')
    if t >= 13.35:
        ks = popin(t, 13.35, 0.3) * (1 + 0.05 * math.sin(t * 10))
        blit(fg, fx.big('tag', 'STICK TO TRACTORS!', '#ffffff', '#d6303a', s=7), 560, 560, ks, ks, -4 + 3 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 13.35, 640, 560, RED, seed=95)
    fx.ring(fg, t, 13.35, 640, 560, (224, 48, 58), life=0.35, r1=360)
    if t >= 14.39:                                                                 # a tractor drops in on 'tractors'
        ty = lerp(-200, GROUND - 330, ic(prog(t, 14.39, 0.25)))
        sr, sv = wob(t, (14.64,), 0.08)
        blit(fg, up(tractor(0), 4), 520, ty, sr, sv)
        fx.dust(fg, t, 14.64, 520, GROUND - 330, n=12, seed=96)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: he builds his own
CAR5 = 560
def car5_x(t): return lerp(1600, CAR5, oc(prog(t, 15.71, 0.6)))
P5 = Presenter([
    (15.25, dict(path=Track([(15.25, (540, -200)), (15.6, (200, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (15.6, dict(ground=GROUND, squash=True, arms='present', look=(CAR5, 1000), expr='grin', face=None)),
    (16.28, dict(arms='cheer2', expr='grin', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(15.3, (560, 860, 1.25)), (16.3, (560, 900, 1.12), 'io'), (17.1, (560, 880, 1.16))],
              kicks=[(15.71, 0.08, CAR5, 1000), (16.28, 0.16, CAR5, 1000), (16.63, 0.08, 540, 520)], shakes=[(16.28, 0.2, 10)])


def shot_build(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car5_x(t)
    fx.rays(fg, t, 16.28, CAR5, GROUND - 200, GLOW, life=1.0, r=600)
    if t < 16.3: fx.speed_lines(fg, 1 - prog(t, 15.71, 0.6), 6, col=(200, 204, 214))
    fx.contact_shadow(fg, x, GROUND, 620, s=S, alpha=140)
    sr, sv = wob(t, (16.31,), 0.07)
    draw_car(fg, 'silver', x, 7, flip=True, dist=1600 - x, sx=1.08 * sr, sy=0.84 * sv, lights=True)
    fx.glint(fg, t, 16.4, CAR5 + 100, GROUND - 230, r=140)
    fx.sparkles(fg, t * 1.3, CAR5, GROUND - 240, 620, 260, n=10, seed=52)
    dg.label(fg, t, 16.28, 'HIS OWN', (CAR5, GROUND - 260), (CAR5 + 120, GROUND - 520), '#7fe3a0', '#1a1a2e', '#3cc85a', s=9)
    fx.confetti(fg, t, 16.28, 560, 700, n=40, seed=5)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 15.45, 17.05, 'lambo_350gt', 560, 520, 520, 390, 4, 'HIS FIRST CAR: 350 GT, 1964', focus=(0.3, 0.62), zoom=0.4)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(17.1, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.45, shot_rival), (7.1, shot_clutch), (11.05, shot_enzo), (15.3, shot_build), (17.1, shot_teaser)]
TRANS = {1: (3.45, 3.65, 'whip', dict(dx=-1)), 2: (7.1, 7.34, 'iris', (CAR2 + 150, 900)), 3: (11.05, 11.27, 'push', None),
         4: (15.3, 15.5, 'whip', dict(dx=0, dy=1)), 5: (17.1, 17.3, 'whip', dict(dx=1))}
KEYCOL = {'tractors': YEL, 'ferrari': RED, 'breaking': RED, 'part': RED, 'clutch': YEL, 'enzo': RED, 'stick': RED, 'sports': YEL,
          'car': YEL, 'built': kit.GRN, 'own': kit.GRN}
CUES = [
    (0.0, 'vroom', 0.7), (0.05, 'stamp', 0.8), (0.07, 'sparkle', 0.6), (0.3, 'thump', 0.4), (0.6, 'thump', 0.4), (1.0, 'thump', 0.9),
    (1.0, 'boom', 0.35), (1.81, 'pop', 0.8), (1.83, 'sparkle', 0.5),
    (3.5, 'vroom', 0.8), (4.15, 'screech', 0.5), (4.36, 'ding', 0.6), (4.4, 'sparkle', 0.5), (5.3, 'click', 0.6), (5.64, 'crash', 0.6),
    (5.66, 'buzzer', 0.4), (5.7, 'poof', 0.5), (6.05, 'buzzer', 0.4), (6.31, 'stamp', 1.0), (6.33, 'boom', 0.35),
    (7.35, 'pop', 0.7), (8.89, 'ding', 0.8), (8.91, 'sparkle', 0.7), (9.75, 'whoosh', 0.6), (9.96, 'thump', 0.7), (10.3, 'cha_ching', 0.8),
    (11.27, 'pop', 0.6), (13.35, 'buzzer', 0.6), (13.37, 'pop', 0.8), (14.39, 'fall', 0.7), (14.64, 'crash', 0.6), (14.66, 'boom', 0.4),
    (15.71, 'vroom', 0.9), (16.28, 'confetti', 0.8), (16.3, 'ding', 0.8), (16.32, 'sparkle', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay)

if __name__ == '__main__':
    kit.main()
