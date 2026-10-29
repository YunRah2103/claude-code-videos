"""Renders 'Smaller on purpose': the 1959 Mini, a whole car squeezed into a tiny space by turning the engine sideways.

Template: videos/ac-idle -> jaguar-rise-fall shot structure; shared/episode.py holds captions, progress bar, photo
cards, mixer and the NEXT EPISODE ending. Word times: align.py -> words.json (voice includes 'Follow for the next one').
Speech runs 0-20.1 s; the teaser starts at 18.55 and the 'Follow' card shows from 19.0 to 20.6 s.
The 'fits four adults' claim is not used on screen; the callout says 'ROOM FOR PASSENGERS' as in the script.
Shots:
  1 hook    0.00  'Smaller on purpose' in yellow; 1959 badge; an empty fuel pump gets an EMPTY stamp on 'fuel'
  2 squeeze 3.30  whip; ENGINEER badge; a huge pixel car is squeezed into a small box on 'tiny space'
  3 engine  8.85  iris; top-down plan: the engine rotates sideways on 'sideways'; seats pop in, ROOM FOR PASSENGERS
  4 heater 12.65  push; the Mini in the cold; HEATER: OPTIONAL EXTRA tag, frost flakes, he shivers
  5 loved  15.05  whip; the Mini rolls in; real 1959 Mini photo; hearts; MOST LOVED badge on 'loved'
  6 teaser 18.55  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, layer, finish, draw_car, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, ob, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T, TEASE = 20.6, 19.0, 18.55
NAVY = (26, 26, 46)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def mini(spin=0):
    """Side-view 1959 Mini (62x34): short boxy body, white roof, tiny wheels pushed to the corners."""
    img = Image.new('RGBA', (62, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, shade, hi, deep = (232, 52, 63), (181, 34, 44), (255, 122, 128), (140, 24, 32)
    d.rounded_rectangle((2, 13, 59, 27), 3, fill=body)
    d.polygon([(10, 13), (14, 4), (48, 4), (52, 13)], fill=body); d.rectangle((13, 3, 49, 5), fill=(244, 244, 240))
    d.polygon([(15, 12), (17, 6), (30, 6), (30, 12)], fill=(84, 118, 160)); d.polygon([(33, 6), (46, 6), (49, 12), (33, 12)], fill=(84, 118, 160))
    d.line([(18, 11), (21, 7)], fill=(170, 200, 230)); d.line([(36, 11), (39, 7)], fill=(170, 200, 230))
    d.line([(4, 14), (57, 14)], fill=hi); d.rectangle((3, 23, 58, 24), fill=shade); d.rectangle((4, 25, 58, 27), fill=deep)
    d.line([(31, 13), (31, 24)], fill=deep); d.line([(4, 15), (4, 25)], fill=deep); d.line([(57, 15), (57, 25)], fill=deep)  # seams
    d.rectangle((0, 22, 3, 26), fill=(200, 204, 212)); d.rectangle((58, 22, 61, 26), fill=(200, 204, 212))
    d.ellipse((55, 16, 59, 20), fill=(255, 246, 200)); d.rectangle((3, 17, 4, 20), fill=(200, 40, 40))
    for cx in (12, 50):
        d.ellipse((cx - 6, 22, cx + 6, 34), fill=(22, 23, 28)); d.ellipse((cx - 3, 25, cx + 3, 31), fill=(190, 194, 204))
        a = math.radians(spin); d.line([(cx, 28), (cx + 3 * math.cos(a), 28 + 3 * math.sin(a))], fill=(110, 114, 124))
    return outline(img)


@lru_cache(None)
def pump(empty=False):
    """1950s fuel pump (26x52)."""
    img = Image.new('RGBA', (26, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((3, 10, 19, 50), fill=(61, 127, 214)); d.rectangle((3, 10, 5, 50), fill=(122, 176, 240))
    d.ellipse((2, 0, 20, 14), fill=(244, 244, 240)); d.ellipse((6, 3, 16, 11), fill=(255, 210, 63))
    d.rectangle((6, 16, 16, 26), fill=(30, 32, 38)); d.rectangle((7, 17, 15, 25), fill=(60, 63, 71) if empty else (60, 200, 90))
    d.line([(10, 21), (14, 18) if not empty else (8, 24)], fill=(224, 48, 58), width=1)
    d.rectangle((1, 48, 21, 51), fill=(40, 42, 48))
    d.line([(19, 30), (24, 32), (24, 44)], fill=(30, 32, 38), width=2); d.rectangle((21, 26, 25, 30), fill=(176, 182, 192))
    return outline(img)


def hearts(fg, t, t0, x, y, n=7, seed=5, life=1.3):
    """Pixel hearts that pop out of a point and float up (as in jaguar-rise-fall)."""
    if not (t0 <= t < t0 + life): return
    r = np.random.default_rng(seed); p = (t - t0) / life
    for i in range(n):
        dx, sp, ph = r.uniform(-260, 260), r.uniform(260, 520), r.uniform(0, 6)
        k = ob(clamp(p * 4)) * (1 - ic(clamp((p - 0.6) / 0.4)))
        blit(fg, fx.big('heart', s=8), x + dx * oc(clamp(p * 2)) + 18 * math.sin(t * 7 + ph), y - sp * p, k, k, anchor='center')


# ================================================================== shot 1: hook, 1959 and no fuel
PUMP = (700, GROUND)
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-200, 300)), (0.4, (-200, 300)), (0.9, (300, GROUND), 'ic')]), size=7, legs='auto', arms='fly',
                expr='wow', ground=None, face=1)),
    (0.9, dict(ground=GROUND, squash=True, arms='present', look=(700, 900), expr='smile', face=None)),
    (2.09, dict(arms='point', point=(700, 820), look=(700, 820), expr='think')),
    (2.56, dict(arms='shrug', expr='sad', point=None, look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (540, 800, 1.3)), (0.22, (540, 760, 1.25)), (1.5, (560, 900, 1.12), 'io'), (2.56, (640, 920, 1.25), 'io'),
                     (3.3, (640, 920, 1.3))],
              kicks=[(0.0, 0.1, 540, 470), (0.22, 0.14, 540, 640), (2.09, 0.08, 700, 820), (2.56, 0.14, 700, 820)], shakes=[(2.56, 0.25, 12)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, PUMP[0], GROUND, 260, s=S, alpha=140)
    sr, sv = wob(t, (2.56,), 0.08)
    blit(fg, up(pump(t >= 2.4), 9), PUMP[0], GROUND, sr, sv)
    if 0.22 <= t < 2.0:
        k = popin(t, 0.22, 0.3) * popout(t, 1.85)
        blit(fg, fx.big('badge', '1959', '#ffd23f', '#1a1a2e', '#e8b923', s=14), 400, 600, k, k, 3 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 0.22, 400, 600, GLOW, seed=70)
    fx.stamp_at(fg, t, 2.56, 'EMPTY', PUMP[0], GROUND - 330, rot=-12, s=12)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.0, 'Smaller on purpose', YEL, 400, 108, -3)
    fx.ring(cv, t, 0.05, 540, 400, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: fit a whole car into a tiny space
BOX = (620, GROUND)
def squeeze(t): return 1 - 0.6 * io(prog(t, 7.24, 0.8))       # big car -> fits the box on 'tiny space'
P2 = Presenter([
    (3.25, dict(path=Track([(3.25, (-200, 500)), (3.65, (160, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (3.65, dict(ground=GROUND, squash=True, arms='thumb', expr='grin', face=None, look_camera=True)),
    (5.43, dict(arms='pointup', expr='smile', look=(540, 500), look_camera=False)),
    (6.66, dict(arms='brace', expr='wow', look=BOX, squash=True)),
    (8.03, dict(arms='cheer1', expr='grin', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(3.3, (540, 860, 1.15)), (5.43, (540, 760, 1.2), 'io'), (6.66, (560, 940, 1.05), 'io'), (8.03, (600, 980, 1.2), 'io'),
                     (8.85, (600, 980, 1.25))],
              kicks=[(3.56, 0.1, 540, 480), (5.43, 0.1, 540, 480), (6.66, 0.08, 620, 900), (8.03, 0.16, *BOX)], shakes=[(7.3, 0.7, 6)])


def shot_squeeze(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if 3.56 <= t < 6.5:
        k = popin(t, 3.56, 0.3) * popout(t, 6.3)
        blit(fg, fx.big('badge', 'ENGINEER', '#ffffff', '#1a1a2e', '#d6d9e2', s=11), 540, 470, k, k, -3 + 2 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 3.56, 540, 470, GLOW, seed=71)
    if 5.43 <= t < 6.5:
        k = popin(t, 5.43, 0.25) * popout(t, 6.3)
        blit(fg, fx.big('tag', 'ONE JOB', '#fff6e0', '#d6303a', s=9), 560, 620, k, k, 6, anchor='center')
    if t >= 6.2:                                                                 # the box, then the big car squeezed into it
        kb = popin(t, 6.2, 0.3); d = ImageDraw.Draw(fg)
        bw, bh = 300 * kb, 240 * kb
        d.rectangle((BOX[0] - bw, BOX[1] - bh, BOX[0] + bw, BOX[1]), fill=(150, 112, 66), outline=NAVY, width=8)
        d.rectangle((BOX[0] - bw, BOX[1] - bh, BOX[0] + bw, BOX[1] - bh + 30 * kb), fill=(186, 144, 90))
        sq = squeeze(t)
        cx = BOX[0] + 30 * math.sin(t * 30) * (7.24 <= t < 8.0)
        draw_car(fg, 'red', cx, 12, y=lerp(BOX[1] - bh + 40, BOX[1] - 40, io(prog(t, 7.24, 0.8))), sx=sq * (1 + 0.1 * math.sin(t * 25) * (7.24 <= t < 8.0)),
                 sy=sq * (1 - 0.1 * math.sin(t * 25) * (7.24 <= t < 8.0)))
        d = ImageDraw.Draw(fg)
        d.rectangle((BOX[0] - bw, BOX[1] - bh * 0.5, BOX[0] + bw, BOX[1]), fill=(150, 112, 66), outline=NAVY, width=8)  # box front
        for x in (-0.6, 0, 0.6): d.line([(BOX[0] + x * bw, BOX[1] - bh * 0.5 + 20), (BOX[0] + x * bw, BOX[1] - 20)], fill=(120, 86, 48), width=6)
    dg.label(fg, t, 7.59, 'TINY SPACE', (BOX[0] + 250, GROUND - 120), (BOX[0] + 120, 640), '#ffd23f', '#1a1a2e', '#e8b923', s=9)
    if t >= 8.03: fx.sparkles(fg, t, *BOX, 600, 300, n=8, seed=32)
    fx.burst(fg, t, 8.03, BOX[0], GROUND - 260, GLOW, seed=72)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the engine turns sideways (top-down plan)
PLAN = (540, 760)
def eng_rot(t): return 90 * ob(prog(t, 9.87, 0.5))
P3 = Presenter([
    (8.8, dict(path=Track([(8.8, (1300, 600)), (9.2, (900, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (9.2, dict(ground=GROUND, squash=True, arms='point', point=(540, 560), look=(540, 560), expr='think', face=None)),
    (9.87, dict(arms='cheer1', expr='wow', point=None, squash=True)),
    (11.35, dict(arms='point', point=(540, 880), look=(540, 880), expr='grin')),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(8.85, (540, 700, 1.35)), (9.87, (540, 640, 1.3), 'io'), (11.0, (540, 800, 1.08), 'io'), (12.65, (540, 800, 1.12))],
              kicks=[(9.61, 0.08, 540, 520), (9.87, 0.16, 540, 520), (11.35, 0.1, 540, 880), (11.69, 0.08, 540, 1060)])


def shot_engine(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    x0, y0, x1, y1 = PLAN[0] - 230, PLAN[1] - 420, PLAN[0] + 230, PLAN[1] + 340         # car seen from above, nose up
    d.rounded_rectangle((x0 - 10, y0 - 10, x1 + 10, y1 + 10), 70, fill=NAVY)
    d.rounded_rectangle((x0, y0, x1, y1), 64, fill=(232, 52, 63))
    d.rounded_rectangle((x0 + 40, y0 + 230, x1 - 40, y1 - 70), 30, fill=(244, 244, 240))  # roof / cabin
    for wx, wy in ((x0 - 12, y0 + 70), (x1 - 18, y0 + 70), (x0 - 12, y1 - 140), (x1 - 18, y1 - 140)):
        d.rectangle((wx, wy, wx + 30, wy + 80), fill=(22, 23, 28))
    # bay line moves forward when the engine turns: more cabin
    bay = lerp(y0 + 330, y0 + 210, io(prog(t, 10.0, 0.6)))
    d.rectangle((x0 + 20, bay, x1 - 20, bay + 10), fill=(26, 26, 46))
    eng = Image.new('RGBA', (120, 300), (0, 0, 0, 0)); de = ImageDraw.Draw(eng)
    de.rectangle((0, 0, 119, 299), fill=(140, 146, 158), outline=NAVY, width=8)
    for k in range(4): de.ellipse((30, 25 + 68 * k, 90, 85 + 68 * k), fill=(90, 96, 108), outline=NAVY, width=5)
    blit(fg, eng, PLAN[0], y0 + 160 + lerp(70, 0, prog(t, 9.87, 0.5)), 1, 1, eng_rot(t), anchor='center')
    fx.ring(fg, t, 9.87, PLAN[0], y0 + 160, GLOW, life=0.35, r1=260)
    dg.label(fg, t, 9.61, 'ENGINE', (PLAN[0] + 100, y0 + 160), (PLAN[0] + 330, y0 + 60), '#ffd23f', '#1a1a2e', '#e8b923', s=7, t1=11.2)
    for i, (sx, sy) in enumerate(((-90, -40), (90, -40), (-90, 150), (90, 150))):      # seats pop into the freed space
        ts = 11.35 + 0.1 * i
        if t >= ts:
            k = popin(t, ts, 0.25); sxp, syp = PLAN[0] + sx, PLAN[1] + sy
            blit(fg, fx.big('badge', ' ', '#3d7fd6', '#3d7fd6', '#2b5fa8', s=11), sxp, syp, k, k * 1.5, anchor='center')
    if t >= 11.69:
        kr = popin(t, 11.69, 0.3)
        blit(fg, fx.big('badge', 'ROOM FOR PASSENGERS', '#7fe3a0', '#1a1a2e', '#3cc85a', s=6), 540, 1130, kr, kr, 2 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 11.69, 540, 1130, (60, 200, 90), seed=73)
    if t >= 11.35: fx.sparkles(fg, t, PLAN[0], PLAN[1] + 50, 360, 300, n=6, seed=33)
    P3.draw(fg, t)
    photo(fg, t, 10.45, 11.3, 'mini_engine', 800, 1060, 500, 360, 3, 'SIDEWAYS A-SERIES ENGINE', focus=(0.5, 0.5))
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: heating was optional
CAR4 = 600
P4 = Presenter([
    (12.6, dict(path=Track([(12.6, (-200, 500)), (13.0, (220, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (13.0, dict(ground=GROUND, squash=True, arms='brace', expr='shock', face=None, look=(CAR4, 900))),
    (14.19, dict(arms='shrug', expr='smirk', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(12.65, (540, 900, 1.2)), (13.69, (560, 820, 1.25), 'io'), (15.05, (560, 860, 1.2))],
              kicks=[(12.92, 0.1, CAR4, 900), (13.69, 0.14, 600, 560), (14.19, 0.08, 600, 560)])


def shot_heater(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR4, GROUND, 480, s=S, alpha=140)
    blit(fg, up(mini(0), 9), CAR4 + 3 * math.sin(t * 50), GROUND)                 # it shivers
    fx.flakes(fg, t, 12.92, CAR4, GROUND - 330, n=12, spread=500, life=2.0, rise=-300, s=7)
    if t >= 12.92:
        kh = popin(t, 12.92, 0.25)
        blit(fg, fx.big('snowflake', s=12), 860, 520 + 10 * math.sin(t * 3), kh, kh, t * 40, anchor='center')
    if t >= 13.69:
        k = popin(t, 13.69, 0.3) * (1 + 0.04 * math.sin(t * 8))
        blit(fg, fx.big('tag', 'HEATER: OPTIONAL EXTRA', '#fff6e0', '#d6303a', s=6), 560, 600, k, k, -5, anchor='center')
        fx.burst(fg, t, 13.69, 560, 600, (127, 212, 255), seed=74)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: one of the most loved cars ever made
CAR5 = 640
def car5_x(t): return lerp(1500, CAR5, oc(prog(t, 15.1, 0.6)))
P5 = Presenter([
    (15.0, dict(path=Track([(15.0, (540, -200)), (15.4, (220, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (15.4, dict(ground=GROUND, squash=True, arms='present', look=(CAR5, 1000), expr='grin', face=None)),
    (17.07, dict(arms='cheer2', expr='happy', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(15.05, (560, 860, 1.25)), (16.0, (560, 820, 1.12), 'io'), (18.55, (560, 840, 1.18))],
              kicks=[(15.7, 0.1, CAR5, 1000), (17.07, 0.14, 540, 600), (17.42, 0.08, 540, 600)])


def shot_loved(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car5_x(t)
    if t < 15.7: fx.speed_lines(fg, 1 - prog(t, 15.1, 0.6), 4, col=(200, 204, 214))
    fx.contact_shadow(fg, x, GROUND, 480, s=S, alpha=140)
    sr, sv = wob(t, (15.7,), 0.07)
    blit(fg, up(mini(int((1500 - x) * 0.6) % 360), 9), x, GROUND, sr, sv, flip=True)
    fx.rays(fg, t, 17.07, 540, 600, (255, 120, 150), life=1.0, r=560)
    if t >= 17.07:
        k = popin(t, 17.07, 0.3) * (1 + 0.05 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'MOST LOVED', '#7fe3a0', '#1a1a2e', '#3cc85a', s=12), 540, 600, k, k, 4 * math.sin(t * 4), anchor='center')
    hearts(fg, t, 17.07, 560, 900, n=9, seed=4)
    fx.sparkles(fg, t, CAR5, GROUND - 200, 480, 220, n=6, seed=35)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 15.4, 16.95, 'mini_1959', 560, 560, 560, 420, -3, 'MORRIS MINI-MINOR, 1959', focus=(0.5, 0.55), zoom=0.1)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(TEASE, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.3, shot_squeeze), (8.85, shot_engine), (12.65, shot_heater), (15.05, shot_loved), (TEASE, shot_teaser)]
TRANS = {1: (3.3, 3.5, 'whip', dict(dx=-1)), 2: (8.85, 9.08, 'iris', (BOX[0], GROUND - 200)), 3: (12.65, 12.87, 'push', None),
         4: (15.05, 15.25, 'whip', dict(dx=0, dy=1)), 5: (TEASE, TEASE + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'1959': YEL, 'fuel': RED, 'issigonis': YEL, 'job': YEL, 'whole': YEL, 'tiny': YEL, 'space': YEL, 'engine': YEL,
          'sideways': YEL, 'room': kit.GRN, 'passengers': kit.GRN, 'heating': (127, 212, 255), 'optional': YEL, 'extra': YEL,
          'loved': (255, 120, 150), 'ever': YEL, 'follow': YEL, 'next': YEL}
CUES = [
    (0.05, 'stamp', 0.8), (0.07, 'sparkle', 0.6), (0.22, 'pop', 0.8), (0.24, 'ding', 0.6), (0.9, 'thump', 0.5), (2.56, 'stamp', 1.0),
    (2.58, 'buzzer', 0.4), (2.6, 'poof', 0.5),
    (3.56, 'pop', 0.8), (5.43, 'pop', 0.7), (6.2, 'thump', 0.6), (6.66, 'vroom', 0.6), (7.24, 'creak', 0.8), (7.6, 'slide_down', 0.6),
    (7.59, 'pop', 0.6), (8.03, 'thump', 0.8), (8.05, 'ding', 0.7), (8.07, 'sparkle', 0.6),
    (9.61, 'pop', 0.6), (9.87, 'whoosh', 0.7), (10.1, 'click', 0.8), (10.12, 'boom', 0.35), (11.35, 'pop', 0.6), (11.45, 'pop', 0.6),
    (11.55, 'pop', 0.6), (11.65, 'pop', 0.6), (11.69, 'ding', 0.8), (11.71, 'sparkle', 0.6),
    (12.92, 'sparkle', 0.6), (13.69, 'pop', 0.8), (14.19, 'click', 0.5),
    (15.1, 'vroom', 0.8), (15.4, 'pop', 0.7), (15.7, 'thump', 0.6), (17.07, 'ding', 0.8), (17.09, 'sparkle', 0.8), (17.1, 'confetti', 0.5),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay)

if __name__ == '__main__':
    kit.main()
