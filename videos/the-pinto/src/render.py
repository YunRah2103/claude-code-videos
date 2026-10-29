"""Renders 'The Pinto': a cheap car, a fuel tank that could rupture, a recall and a criminal trial. Serious tone.

Template: videos/ac-idle -> jaguar-rise-fall shot structure; shared/episode.py holds captions, progress bar, photo
cards, mixer and the NEXT EPISODE ending. Word times: align.py -> words.json. Speech runs 0-22.2 s; 'Follow' to 23.9 s.
The documents claim is attributed on screen ('CAMPAIGNERS SAY'). No recall size is shown (sources disagree).
Shots:
  1 hook    0.00  'The Ford Pinto' title; a pixel Pinto rolls in; real photo on 'Pinto'; CHEAP tag on 'cheap'
  2 tank    2.95  whip; the rear tank glows (FUEL TANK); a car hits the rear on 'crash'; flames on 'fire'
  3 ledger  7.75  push; CAMPAIGNERS SAY; a cost ledger with question marks; the scale tips on 'weighed'
  4 recall 12.55  whip; 1978 badge, real 1978 Pinto photo; RECALLED stamp slams on 'recalled'
  5 court  15.75  push; 1980 badge; the gavel falls on 'jury'; NOT GUILTY on 'not guilty'; CRIMINAL CASE label
  6 lesson 20.20  whip; CHEAP tag struck through; EXPENSIVE LESSON badge
  7 teaser 22.35  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, WHITE, layer, finish, draw_car, photo, title
from pixanim.motion import Track, prog, lerp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import Grid, up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 23.9, 22.35
ORANGE = (255, 138, 61)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def pinto(spin=0, tank=False):
    """Side-view 1970s fastback hatch (92x36), front to the right; `tank` reveals the fuel tank behind the rear axle."""
    img = Image.new('RGBA', (92, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, shade, hi, deep = (190, 140, 66), (150, 106, 46), (232, 190, 116), (110, 76, 32)
    d.polygon([(2, 27), (2, 19), (6, 16), (30, 7), (50, 6), (56, 7), (66, 15), (84, 17), (89, 20), (89, 27)], fill=body)
    d.line([(6, 16), (30, 7), (50, 6)], fill=hi); d.line([(66, 15), (84, 17), (88, 19)], fill=hi)
    d.rectangle((3, 23, 88, 24), fill=shade); d.rectangle((4, 25, 88, 27), fill=deep)
    d.polygon([(33, 8), (49, 7), (49, 14), (22, 14)], fill=(84, 118, 160)); d.polygon([(52, 8), (56, 8), (64, 14), (52, 14)], fill=(84, 118, 160))
    d.line([(30, 13), (36, 9)], fill=(170, 200, 230)); d.line([(54, 13), (57, 10)], fill=(170, 200, 230))
    d.line([(50, 14), (50, 24)], fill=deep); d.rectangle((44, 17, 46, 17), fill=(220, 220, 214))
    d.rectangle((84, 21, 90, 26), fill=(196, 198, 204)); d.rectangle((0, 21, 4, 26), fill=(196, 198, 204))   # chrome bumpers
    d.rectangle((85, 18, 88, 20), fill=(255, 246, 200)); d.rectangle((3, 18, 5, 21), fill=(200, 40, 40))
    if tank:
        d.rectangle((4, 24, 15, 31), fill=(255, 200, 60)); d.rectangle((5, 25, 14, 25), fill=(255, 240, 160))
    for cx in (17, 72):
        d.ellipse((cx - 8, 20, cx + 8, 36), fill=(22, 23, 28))
        d.ellipse((cx - 7, 21, cx + 7, 35), fill=(32, 33, 38))
        d.ellipse((cx - 4, 24, cx + 4, 32), fill=(176, 182, 192))
        for k in range(4):
            a = math.radians(k * 90 + spin); d.line([(cx, 28), (cx + 4 * math.cos(a), 28 + 4 * math.sin(a))], fill=(110, 114, 124))
    return outline(img)


@lru_cache(None)
def flame(i, size=1.0):
    """Pixel fire (24x34), flickering by frame index i."""
    r = np.random.default_rng(i % 7)
    img = Image.new('RGBA', (24, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for col, w, h in (((224, 48, 58), 11, 32), (ORANGE, 8, 24), ((255, 217, 59), 5, 15)):
        tip = (12 + r.integers(-3, 4), 33 - h * size)
        d.polygon([(12 - w, 33), tip, (12 + w, 33)], fill=col)
        d.polygon([(12 - w + 2, 33), (12 - w + r.integers(0, 4), 33 - h * 0.6 * size), (12, 33)], fill=col)
    return outline(img)


@lru_cache(None)
def ledger():
    """Cost ledger sheet (110x52): two cost rows, both unknown."""
    g = Grid(110, 52)
    g.rect(1, 1, 108, 50, '#f4f1e8'); g.rect(1, 1, 108, 9, '#d8d2c2')
    g.text(28, 3, 'COST LEDGER', '#1a1a2e')
    for y in (21, 37): g.rect(4, y, 105, y, '#b8b2a2')
    g.text(5, 13, 'FIX THE CARS', '#1a1a2e'); g.text(92, 13, '$?', '#d6303a')
    g.text(5, 29, 'PAY CLAIMS', '#1a1a2e'); g.text(92, 29, '$?', '#d6303a')
    g.rect(78, 41, 104, 47, '#ffd23f'); g.text(82, 41, '?', '#d6303a'); g.text(88, 41, '?', '#d6303a'); g.text(94, 41, '?', '#d6303a')
    return g.image()


@lru_cache(None)
def gavel():
    img = Image.new('RGBA', (40, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((18, 12, 22, 38), fill=(140, 90, 50)); d.line([(19, 12), (19, 38)], fill=(186, 130, 80))
    d.rectangle((6, 4, 34, 14), fill=(120, 74, 40)); d.rectangle((6, 4, 34, 6), fill=(176, 120, 72))
    d.rectangle((4, 3, 7, 15), fill=(214, 180, 90)); d.rectangle((33, 3, 36, 15), fill=(214, 180, 90))
    return outline(img)


def draw_pinto(cv, x, s, y=GROUND, dist=0.0, tank=False, sx=1.0, sy=1.0, rot=0.0):
    blit(cv, up(pinto(int(dist / (7.5 * s) * 57.3) // 15 * 15 % 360, tank), s), x, y, sx, sy, rot)


def fire(cv, t, t0, x, y, s=8, n=3, grow=0.8):
    if t < t0: return
    g = min(1.0, 0.4 + (t - t0) / grow)
    for k in range(n):
        blit(cv, up(flame(int(t * 14) + k * 3, 0.7 + 0.3 * g), s), x + (k - (n - 1) / 2) * 9 * s, y, g, g * (1 + 0.1 * math.sin(t * 20 + k)))


# ================================================================== shot 1: hook, the cheap car
CAR1 = 560
def car1_x(t): return lerp(1600, CAR1, oc(prog(t, 0.0, 0.8)))
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-200, 300)), (0.4, (-200, 300)), (0.9, (180, GROUND), 'ic')]), size=7, legs='auto', arms='fly',
                expr='smile', ground=None, face=1)),
    (0.9, dict(ground=GROUND, squash=True, arms='present', look=(CAR1, 1000), expr='smile', face=None)),
    (2.26, dict(arms='point', point=(CAR1 + 60, 820), look=(CAR1, 820), expr='smirk')),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (700, 1000, 1.45)), (0.0, (700, 1000, 1.45)), (0.8, (560, 960, 1.12), 'io'), (2.26, (580, 900, 1.2), 'io'),
                     (2.95, (580, 900, 1.24))],
              kicks=[(0.0, 0.1, 700, 1000), (0.8, 0.1, CAR1, 1000), (0.96, 0.08, 540, 560), (2.26, 0.12, CAR1, 820)], shakes=[(0.8, 0.2, 8)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car1_x(t)
    if t < 0.8: fx.speed_lines(fg, 1 - prog(t, 0.0, 0.8), 3, col=(200, 204, 214))
    fx.contact_shadow(fg, x, GROUND, 620, s=S, alpha=140)
    sr, sv = wob(t, (0.8,), 0.06)
    draw_pinto(fg, x, 7, dist=1600 - x, sx=sr, sy=sv)
    fx.dust(fg, t, 0.8, x, GROUND - 10, n=12, seed=43)
    if t >= 2.26:
        k = popin(t, 2.26, 0.3)
        blit(fg, fx.big('tag', 'CHEAP', '#fff6e0', '#d6303a', s=10), CAR1 + 80, 860, k, k, -8 + 3 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 2.26, CAR1 + 80, 860, GLOW, n=10, seed=71)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 0.96, 2.2, 'pinto', 540, 560, 560, 420, -3, 'FORD PINTO, 1970s', focus=(0.45, 0.55))
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 0.92, 'The Ford Pinto', YEL, 470, 112, -3)
    fx.ring(cv, t, 0.05, 540, 470, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: the tank, the crash, the fire
CAR2 = 640
TANK = (CAR2 - 46 * 7 + 10 * 7, GROUND - 60)
def hit_x(t): return lerp(-700, CAR2 - 630, ic(prog(t, 4.6, 0.37))) - 60 * oc(prog(t, 4.97, 0.4))
P2 = Presenter([
    (2.9, dict(path=Track([(2.9, (1300, 400)), (3.3, (960, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (3.3, dict(ground=GROUND, squash=True, arms='point', point=TANK, look=TANK, expr='think', face=None)),
    (4.97, dict(arms='shock', expr='shock', squash=True, point=None)),
    (6.35, dict(arms='brace', expr='sad', look=TANK)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(2.95, (560, 980, 1.15)), (3.83, (420, 1000, 1.4), 'io'), (4.6, (420, 1000, 1.25), 'io'), (5.3, (460, 980, 1.18), 'io'),
                     (6.35, (380, 1000, 1.38), 'io'), (7.75, (400, 990, 1.45))],
              kicks=[(3.83, 0.12, *TANK), (4.97, 0.16, *TANK), (6.35, 0.12, *TANK), (7.0, 0.1, *TANK)], shakes=[(4.97, 0.45, 26), (7.0, 0.3, 10)])


def shot_tank(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    jolt = 40 * oc(prog(t, 4.97, 0.2)) * (1 - prog(t, 5.2, 0.5))
    fx.contact_shadow(fg, CAR2, GROUND, 620, s=S, alpha=140)
    draw_pinto(fg, CAR2 + jolt, 7, tank=t >= 3.6, rot=-2 * oc(prog(t, 4.97, 0.15)) * (1 - prog(t, 5.15, 0.3)))
    if 3.6 <= t < 5.0: fx.ring(fg, t % 0.6 + 3.6, 3.6, *TANK, ORANGE, life=0.5, r1=140)
    dg.label(fg, t, 3.83, 'FUEL TANK', TANK, (TANK[0] + 40, 700), '#ffd23f', '#1a1a2e', '#e8b923', s=8, t1=6.2)
    if t >= 4.6:                                                                 # a silver car runs into the rear
        hx = hit_x(t)
        draw_car(fg, 'silver', hx, 6, dist=hx + 700, lights=True, brake=t > 4.97)
    fx.burst(fg, t, 4.97, TANK[0] - 30, GROUND - 120, (255, 255, 255), n=14, seed=72)
    fx.dust(fg, t, 4.97, TANK[0] - 30, GROUND - 10, n=16, seed=44)
    if t >= 5.24:                                                                 # leak drips, then fire
        for k in range(4):
            dy = ((t - 5.24) * 300 + k * 40) % 120
            blit(fg, fx.big('star', '#ffd23f', s=3), TANK[0] + 20 * k - 30, GROUND - 40 + dy * 0.3, anchor='center')
    fire(fg, t, 6.35, TANK[0], GROUND - 20, s=8, n=3 if t < 7.0 else 5)
    fx.rays(fg, t, 7.0, *TANK, (224, 48, 58), life=0.7, r=520)
    fx.ring(fg, t, 7.0, *TANK, (224, 48, 58), life=0.35, r1=380)
    for k in range(5):
        fx.puff(fg, t, 6.5 + k * 0.2, TANK[0], GROUND - 250, seed=50 + k, life=1.0, size=1.2, drift=(40, -320), col=(70, 72, 80))
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: campaigners say, the cost ledger
LED = (540, 640)
SCALE = (540, 920)
P3 = Presenter([
    (7.7, dict(path=Track([(7.7, (-200, 500)), (8.1, (190, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='think', face=1, ground=None)),
    (8.1, dict(ground=GROUND, squash=True, arms='think', look=LED, expr='think', face=None)),
    (9.38, dict(arms='point', point=LED, look=LED, expr='smile')),
    (10.48, dict(arms='think', look=SCALE, expr='think', point=None)),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(7.75, (540, 820, 1.2)), (9.38, (540, 700, 1.3), 'io'), (10.48, (540, 820, 1.12), 'io'), (12.55, (540, 820, 1.16))],
              kicks=[(8.05, 0.1, 540, 400), (9.38, 0.12, *LED), (10.48, 0.1, *SCALE), (10.88, 0.1, 540, 790)])


def tilt(t): return 14 * oc(prog(t, 10.48, 0.5)) * math.cos((t - 10.48) * 5) * math.exp(-max(0, t - 10.48) * 1.2) if t > 10.48 else 0


def shot_ledger(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= 8.05:                                                                 # the claim is theirs: say so on screen
        k = popin(t, 8.05, 0.3)
        blit(fg, fx.big('badge', 'CAMPAIGNERS SAY', '#ffffff', '#1a1a2e', '#d6d9e2', s=8), 540, 380, k, k, -2, anchor='center')
    if t >= 9.38:
        kl = popin(t, 9.38, 0.35)
        blit(fg, up(ledger(), 6), LED[0], LED[1] + 8 * math.sin(t * 2), kl, kl, 2 * math.sin(t * 1.5), anchor='center')
        fx.burst(fg, t, 9.38, *LED, GLOW, n=10, seed=73)
    if t >= 10.48:                                                                # balance scale: fix vs pay, tipping back and forth
        d = ImageDraw.Draw(fg); a = math.radians(tilt(t))
        ks = popin(t, 10.48, 0.3); L = 230 * ks
        d.rectangle((SCALE[0] - 8, SCALE[1], SCALE[0] + 8, GROUND - 10), fill=(140, 146, 158), outline=(26, 26, 46), width=4)
        d.rectangle((SCALE[0] - 70, GROUND - 24, SCALE[0] + 70, GROUND - 6), fill=(140, 146, 158), outline=(26, 26, 46), width=4)
        ends = [(SCALE[0] + sgn * L * math.cos(a), SCALE[1] + sgn * L * math.sin(a)) for sgn in (-1, 1)]
        d.line([ends[0], ends[1]], fill=(26, 26, 46), width=16); d.line([ends[0], ends[1]], fill=(200, 204, 212), width=8)
        for (ex, ey), txt in zip(ends, ('FIX', 'PAY')):
            d.line([(ex, ey), (ex, ey + 70)], fill=(26, 26, 46), width=4)
            blit(fg, fx.big('badge', txt, '#ffd23f', '#1a1a2e', '#e8b923', s=7), ex, ey + 110, ks, ks, anchor='center')
    if t >= 10.88:
        kq = popin(t, 10.88, 0.3) * (1 + 0.08 * math.sin(t * 7))
        blit(fg, fx.big('glyph', '?', '#e0303a', s=14), 540, 790, kq, kq, 8 * math.sin(t * 4), anchor='center')
        fx.ring(fg, t, 10.88, 540, 790, (224, 48, 58), life=0.35, r1=220)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: 1978 recall
CAR4 = 540
P4 = Presenter([
    (12.5, dict(path=Track([(12.5, (1300, 500)), (12.9, (900, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (12.9, dict(ground=GROUND, squash=True, arms='present', look=(CAR4, 1000), expr='smile', face=None)),
    (14.53, dict(arms='shock', expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(12.55, (540, 820, 1.2)), (14.2, (540, 940, 1.15), 'io'), (15.75, (540, 960, 1.22))],
              kicks=[(12.95, 0.12, 540, 420), (14.53, 0.16, CAR4, 980)], shakes=[(14.53, 0.3, 18)])


def shot_recall(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR4, GROUND, 620, s=S, alpha=140)
    sr, sv = wob(t, (14.53,), 0.08)
    draw_pinto(fg, CAR4, 7, sx=sr, sy=sv)
    if t >= 12.95:
        k = popin(t, 12.95, 0.3) * popout(t, 14.4)
        blit(fg, fx.big('badge', '1978', '#ffd23f', '#1a1a2e', '#e8b923', s=14), 540, 400, k, k, 3 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 12.95, 540, 400, GLOW, seed=74)
    fx.stamp_at(fg, t, 14.53, 'RECALLED', CAR4, GROUND - 200, rot=-10, s=10)
    fx.dust(fg, t, 14.53, CAR4, GROUND - 10, n=16, seed=45)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 13.15, 14.45, 'pinto_wagon', 540, 700, 560, 420, 3, '1978 FORD PINTO WAGON', focus=(0.5, 0.55), zoom=0.15)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: 1980 criminal trial
GAV = (700, 760)
P5 = Presenter([
    (15.7, dict(path=Track([(15.7, (-200, 500)), (16.1, (240, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (16.1, dict(ground=GROUND, squash=True, arms='hips', look=GAV, expr='think', face=None)),
    (18.2, dict(arms='shrug', expr='wow', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(15.75, (540, 820, 1.2)), (17.35, (620, 820, 1.3), 'io'), (18.2, (540, 860, 1.16), 'io'), (20.2, (540, 860, 1.22))],
              kicks=[(16.23, 0.12, 540, 400), (17.35, 0.16, *GAV), (18.2, 0.12, 540, 640)], shakes=[(17.6, 0.25, 16)])


def gavel_rot(t): return 60 - 105 * ic(prog(t, 17.35, 0.25)) + 15 * oc(prog(t, 17.6, 0.2))


def shot_court(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)                                                        # the bench
    d.rectangle((420, GROUND - 330, 1000, GROUND), fill=(110, 72, 40), outline=(26, 26, 46), width=8)
    d.rectangle((420, GROUND - 330, 1000, GROUND - 300), fill=(150, 100, 56))
    for x in range(470, 1000, 110): d.rectangle((x, GROUND - 270, x + 70, GROUND - 40), outline=(80, 52, 28), width=6)
    d.ellipse((GAV[0] - 70, GROUND - 350, GAV[0] + 130, GROUND - 320), fill=(80, 52, 28))
    if t >= 16.23:
        k = popin(t, 16.23, 0.3) * popout(t, 17.3)
        blit(fg, fx.big('badge', '1980', '#ffd23f', '#1a1a2e', '#e8b923', s=14), 540, 400, k, k, -3 + 3 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 16.23, 540, 400, GLOW, seed=75)
    blit(fg, up(gavel(), 8), GAV[0] + 60, GROUND - 480, 1, 1, gavel_rot(t), anchor='center')
    fx.ring(fg, t, 17.6, GAV[0], GROUND - 340, (255, 255, 255), life=0.3, r1=260)
    fx.burst(fg, t, 17.6, GAV[0], GROUND - 340, (255, 255, 255), n=10, seed=76)
    if t >= 18.2:
        kn = popin(t, 18.2, 0.3) * (1 + 0.04 * math.sin(t * 8))
        blit(fg, fx.big('badge', 'NOT GUILTY', '#ffffff', '#1a1a2e', '#d6d9e2', s=11), 540, 420, kn, kn, 3 * math.sin(t * 3), anchor='center')
    dg.label(fg, t, 19.0, 'CRIMINAL CASE', (760, GROUND - 330), (720, 620), '#ffffff', '#d6303a', '#d6d9e2', s=7)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: cheap car, expensive lesson
CAR6 = 560
P6 = Presenter([
    (20.15, dict(path=Track([(20.15, (1300, 500)), (20.5, (920, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (20.5, dict(ground=GROUND, squash=True, arms='point', point=(CAR6, 900), look=(CAR6, 900), expr='smile', face=None)),
    (21.35, dict(arms='hips', expr='sad', look=None, look_camera=True, point=None)),
], words=WORDS, base_size=6)
CAM6 = Camera(W, H, [(20.2, (540, 900, 1.3)), (21.35, (540, 820, 1.15), 'io'), (22.35, (540, 820, 1.2))],
              kicks=[(20.45, 0.1, CAR6, 900), (21.35, 0.14, 540, 520)])


def shot_lesson(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR6, GROUND, 620, s=S, alpha=140)
    draw_pinto(fg, CAR6, 7)
    if t >= 20.45:
        k = popin(t, 20.45, 0.25)
        blit(fg, fx.big('tag', 'CHEAP', '#fff6e0', '#d6303a', t >= 20.95, s=10), CAR6 + 60, 860, k, k, -8, anchor='center')
    if t >= 21.35:
        ke = popin(t, 21.35, 0.3) * (1 + 0.04 * math.sin(t * 8))
        blit(fg, fx.big('badge', 'EXPENSIVE LESSON', '#e0303a', '#ffffff', '#a8202a', s=9), 540, 520, ke, ke, -3, anchor='center')
        fx.burst(fg, t, 21.35, 540, 520, RED, seed=77)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (2.95, shot_tank), (7.75, shot_ledger), (12.55, shot_recall), (15.75, shot_court), (20.2, shot_lesson),
         (END_T, shot_teaser)]
TRANS = {1: (2.95, 3.15, 'whip', dict(dx=-1)), 2: (7.75, 7.97, 'push', None), 3: (12.55, 12.75, 'whip', dict(dx=1)),
         4: (15.75, 15.97, 'push', None), 5: (20.2, 20.4, 'whip', dict(dx=-1)), 6: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'pinto': YEL, 'cheap': YEL, 'tank': ORANGE, 'rupture': RED, 'crash': RED, 'fire': RED, 'deadly': RED, 'campaigners': YEL,
          'documents': YEL, 'weighed': YEL, 'cost': RED, '1978': YEL, 'recalled': RED, '1980': YEL, 'jury': YEL, 'guilty': kit.GRN,
          'criminal': RED, 'expensive': RED, 'lesson': RED}
CUES = [
    (0.0, 'vroom', 0.8), (0.05, 'stamp', 0.7), (0.8, 'thump', 0.6), (0.96, 'pop', 0.8), (2.26, 'pop', 0.7), (2.28, 'coin', 0.6),
    (3.3, 'thump', 0.4), (3.83, 'ding', 0.6), (4.6, 'screech', 0.6), (4.97, 'crash', 1.0), (4.97, 'boom', 0.5), (6.35, 'poof', 0.6),
    (6.37, 'boom', 0.5), (7.0, 'boom', 0.45),
    (8.05, 'pop', 0.7), (9.38, 'slide_down', 0.5), (9.4, 'pop', 0.6), (10.48, 'creak', 0.6), (10.88, 'pop', 0.7), (10.9, 'buzzer', 0.3),
    (12.95, 'pop', 0.8), (13.15, 'pop', 0.6), (14.53, 'stamp', 1.0), (14.55, 'boom', 0.45),
    (16.23, 'pop', 0.8), (17.6, 'stamp', 0.9), (17.62, 'boom', 0.4), (18.2, 'ding', 0.6), (19.0, 'pop', 0.6),
    (20.45, 'pop', 0.6), (20.95, 'click', 0.6), (21.35, 'stamp', 0.8),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver')

if __name__ == '__main__':
    kit.main()
