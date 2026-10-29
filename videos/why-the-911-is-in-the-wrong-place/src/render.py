"""Renders 'Why the 911 Is in the Wrong Place': the engine behind the rear axle, on purpose.

Template: videos/ac-idle -> tractors-vs-ferraris shot structure; kit in shared/episode.py (corner rev counter on).
Word times come from align.py -> words.json. Speech runs 0-17.2 s; the card holds to 17.5 s. 'Helps grip,
especially in winter' is Porsche's own explanation; no 356 history; generations are numbered, not dated.
The coupe is a generic pixel fastback (no crest, no script); the framed photo is a 901/911 engine lid with the
script and badge cropped out (credits.json).
Shots:
  1 hook     0.00  a front-engined car glows at the nose; the fastback lights up its rear wheels; WRONG PLACE, ON PURPOSE.
  2 axle     2.10  whip; the shell fades to blueprint and the flat-six slides in behind the rear axle; vents photo; 1963
  3 winter   6.20  push; snowy road: weight arrows press on the rear wheels, it grips, he punches the air
  4 quote    9.90  iris; the engine slides forward and the car turns into a box: X on 'no longer'; it snaps back on '911'
  5 gens    13.95  whip; eight generations, one per beat, then the line-up: STILL THERE
  6 teaser  16.15  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, layer, finish, draw_car, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 17.5, 16.15
BLUE = ((90, 150, 230), (170, 210, 255), (50, 100, 180))
GENS = [((214, 220, 230), None, 0), ((255, 196, 40), 'duck', 0), ((214, 48, 58), 'whale', 1), ((61, 127, 214), None, 1),
        ((60, 170, 100), 'duck', 1), ((34, 36, 44), 'wing', 1), ((255, 132, 40), 'wing', 2), ((236, 236, 240), 'wing', 2)]
REAR_AXLE = 24                                                       # grid x of the rear wheel centre


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def coupe(col=(214, 220, 230), spoiler=None, flare=0, spin=0, xray=False):
    """Generic rear-engined fastback, facing right (100x32 grid): short nose with round lamp bumps, roofline running in
    one slope to the tail, flared rear arches by `flare`, spoiler None/'duck'/'whale'/'wing'. xray: blueprint shell."""
    body, hi, deep = (col, tuple(min(255, c + 60) for c in col), tuple(c * 3 // 5 for c in col)) if not xray else BLUE
    img = Image.new('RGBA', (100, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    shell = [(3, 21), (6, 15), (18, 10), (34, 5), (48, 4), (58, 6), (68, 12), (86, 14), (95, 16), (98, 21), (97, 26), (3, 26)]
    d.polygon(shell, fill=body)
    if flare: d.chord((REAR_AXLE - 13, 14 - flare, REAR_AXLE + 13, 30), 180, 360, fill=body)
    d.line([(18, 10), (34, 5), (48, 4)], fill=hi); d.line([(70, 13), (86, 14)], fill=hi)
    win = (120, 150, 190) if not xray else (200, 230, 255)
    d.polygon([(36, 7), (48, 6), (56, 7), (64, 12), (36, 12)], fill=win); d.line([(50, 6), (50, 12)], fill=deep)
    d.ellipse((86, 13, 92, 18), fill=hi); d.point((89, 15), fill=(255, 246, 200))      # lamp bump
    d.line([(6, 22), (96, 22)], fill=deep)
    if spoiler == 'duck': d.polygon([(4, 14), (12, 11), (12, 13), (5, 16)], fill=body)
    if spoiler == 'whale': d.rectangle((2, 9, 14, 11), fill=deep); d.rectangle((6, 11, 10, 14), fill=deep)
    if spoiler == 'wing': d.rectangle((1, 6, 13, 8), fill=(30, 32, 40)); d.line([(7, 8), (7, 13)], fill=(30, 32, 40), width=2)
    d.rectangle((1, 18, 4, 20), fill=(220, 40, 40))
    for cx in (REAR_AXLE, 80):
        d.ellipse((cx - 8, 18, cx + 8, 34), fill=(24, 24, 30))
        d.ellipse((cx - 5, 21, cx + 5, 31), fill=(176, 182, 192))
        for k in range(5):
            a = math.radians(spin + k * 72); d.line([(cx, 26), (cx + 4 * math.cos(a), 26 + 4 * math.sin(a))], fill=(96, 100, 110))
        d.ellipse((cx - 1, 25, cx + 1, 27), fill=(40, 42, 48))
    return outline(img)


@lru_cache(None)
def flat_six(glow=0):
    """Flat-six seen from the side (22x14): horizontally opposed cylinder banks, fan housing on top."""
    img = Image.new('RGBA', (22, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 4, 19, 11), fill=(150, 156, 170))
    for x in range(3, 19, 3): d.rectangle((x, 5, x + 1, 10), fill=(110, 114, 124))
    d.rectangle((6, 0, 15, 4), fill=(60, 63, 71)); d.ellipse((8, 0, 13, 4), fill=(96, 100, 110))
    d.rectangle((0, 7, 2, 9), fill=(255, 140, 40) if glow else (96, 100, 110))
    return outline(img)


@lru_cache(None)
def inline_four():
    img = Image.new('RGBA', (16, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((1, 4, 14, 13), fill=(150, 156, 170))
    for x in range(2, 14, 3): d.rectangle((x, 0, x + 1, 4), fill=(110, 114, 124))
    return outline(img)


def arrow_down(cv, x, y, k, col=(255, 210, 63)):
    d = ImageDraw.Draw(cv); h = 150 * k; w = 34 * k
    d.rectangle((x - w / 2, y - h, x + w / 2, y - 50 * k), fill=col + (255,), outline=(26, 26, 46, 255), width=6)
    d.polygon([(x - w * 1.6, y - 54 * k), (x + w * 1.6, y - 54 * k), (x, y)], fill=col + (255,), outline=(26, 26, 46, 255))


def snow(cv, t, seed=5, n=110):
    d = ImageDraw.Draw(cv); r = fx.rng(seed)
    for x, y, v, s in zip(r.uniform(0, W, n), r.uniform(0, H, n), r.uniform(120, 260, n), r.integers(2, 5, n)):
        yy = (y + v * t) % H; xx = (x + 40 * math.sin(t * 1.5 + y)) % W
        d.rectangle((xx, yy, xx + s * 3, yy + s * 3), fill=(240, 246, 255, 220))


def two_tone(cv, t, t0, t1, parts, y, sz=120, rot=-2.0):
    if not (t0 <= t < t1 + 0.2): return
    imgs = [kit.text_img(s, c, sz) for s, c in parts]
    line = Image.new('RGBA', (sum(i.width for i in imgs) - 50 * (len(imgs) - 1), max(i.height for i in imgs)), (0, 0, 0, 0)); x = 0
    for i in imgs: line.alpha_composite(i, (x, 0)); x += i.width - 50
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2) * min(1.0, 1000 / line.width) * (1 + 0.025 * math.sin(t * 8))
    blit(cv, line, W / 2, y, k, k, rot + 1.5 * math.sin(t * 3), anchor='center')


SC = 7                                                                # coupe scale in the garage shots
def axle_x(cx): return cx - 50 * SC + REAR_AXLE * SC                  # screen x of the rear axle for a coupe centred at cx


# ================================================================== shot 1: hook, wrong place on purpose
C1 = 600
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-200, 300)), (0.3, (-200, 300)), (0.7, (180, GROUND), 'ic')]), size=7, legs='auto', arms='fly', expr='grin',
                face=1, ground=None)),
    (0.7, dict(ground=GROUND, squash=True, arms='point', point=(axle_x(C1), GROUND - 100), look=(C1, 1000), expr='grin', face=None)),
    (1.62, dict(arms='cheer', expr='wow', squash=True, point=None)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (700, 1040, 1.45)), (0.0, (700, 1040, 1.45)), (0.7, (560, 960, 1.15), 'io'), (2.15, (560, 940, 1.2))],
              kicks=[(0.0, 0.12, axle_x(C1), 1080), (1.0, 0.1, C1, 1000), (1.62, 0.14, axle_x(C1), 1080)], shakes=[(0.0, 2.1, 6)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    kit.draw_car(fg, 'silver', 280, 3, y=GROUND - 160, sy=0.9)                     # an ordinary car behind: engine up front
    d = ImageDraw.Draw(fg); g = 0.5 + 0.5 * math.sin(t * 8)
    d.ellipse((380 - 40, GROUND - 260, 380 + 40, GROUND - 180), fill=(255, 120, 40, int(90 + 80 * g)))
    blit(fg, up(inline_four(), 4), 390, GROUND - 190)
    fx.contact_shadow(fg, C1, GROUND, 720, s=S, alpha=150)
    shake = 3 * math.sin(t * 70)
    blit(fg, up(coupe(spin=int(t * 2200) % 360), SC), C1 + shake, GROUND, 1.0, 1.0, -1.5)
    ax = axle_x(C1)
    for k in range(10):                                                          # burnout smoke off the rear tyres
        fx.puff(fg, t, 0.05 + k * 0.18, ax - 40, GROUND - 30, seed=10 + k, life=0.9, size=1.1, drift=(-320, -140), col=(200, 202, 210))
    fx.burst(fg, t, t - 0.02, ax, GROUND - 10, (255, 200, 90), n=5, r0=10, r1=80, seed=int(t * 40))
    fx.ring(fg, t, 1.62, ax, GROUND - 100, RED, life=0.35, r1=300)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    two_tone(cv, t, 0.05, 2.0, (('WRONG PLACE,', kit.WHITE),), 430, 130, -3)
    two_tone(cv, t, 0.4, 2.0, (('ON PURPOSE.', RED),), 590, 150, 2)
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 430, (255, 255, 255), life=0.35, r1=520)


# ================================================================== shot 2: shell fades, engine slides in behind the axle
C2 = 560
def fade2(t): return io(prog(t, 2.3, 0.5))
def slide2(t): return oc(prog(t, 3.49, 0.45))                                # engine slides in on 'engine'
P2 = Presenter([
    (2.1, dict(path=Track([(2.1, (1300, 400)), (2.45, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (2.45, dict(ground=GROUND, squash=True, arms='point', point=(axle_x(C2), GROUND - 130), look=(axle_x(C2), GROUND - 130), expr='smile', face=None)),
    (5.17, dict(arms='thumb', expr='grin', point=None, look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.1, (560, 960, 1.2)), (3.49, (440, 980, 1.3), 'io'), (4.6, (440, 980, 1.34)), (5.17, (540, 900, 1.15), 'io'),
                     (6.25, (540, 900, 1.2))],
              kicks=[(3.94, 0.1, axle_x(C2), 1080), (4.55, 0.14, axle_x(C2), 1080), (5.17, 0.1, 540, 500)])


def shot_axle(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    f = fade2(t)
    fx.contact_shadow(fg, C2, GROUND, 720, s=S, alpha=150)
    solid = up(coupe(), SC); ghost = up(coupe(xray=True), SC)
    if f < 1: blit(fg, solid, C2, GROUND)
    if f > 0:
        g = ghost.copy(); g.putalpha(g.getchannel('A').point(lambda a: int(a * 0.9 * f))); blit(fg, g, C2, GROUND)
    ax = axle_x(C2); d = ImageDraw.Draw(fg)
    if f > 0.5:                                                                 # the rear axle line
        d.line([(ax, GROUND - 230), (ax, GROUND - 20)], fill=(255, 210, 63, 255), width=8)
    s = slide2(t)
    ex = lerp(-300, ax - 7 * SC - 30, s)
    if t >= 3.4: blit(fg, up(flat_six(int(t * 8) % 2 if s >= 1 else 0), SC), ex, GROUND - 80)
    if s >= 1: fx.burst(fg, t, 3.94, ax - 80, GROUND - 120, GLOW, n=10, r0=40, r1=160, seed=21)
    dg.label(fg, t, 3.94, 'BEHIND THE REAR AXLE', (ax - 70, GROUND - 160), (430, GROUND - 430), '#ffd23f', '#1a1a2e', '#e8b923', s=5, t1=4.95)
    photo(fg, t, 4.45, 6.15, 'porsche_vents_crop', 680, 560, 440, 330, 4, 'REAR ENGINE LID', focus=(0.5, 0.5), zoom=0.0)
    if t >= 5.17:
        ky = ob(prog(t, 5.17, 0.2))
        blit(fg, fx.big('badge', '1963', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 300, 470, ky, ky, -6, anchor='center')
        fx.burst(fg, t, 5.17, 300, 470, GLOW, n=14, seed=22)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: winter grip
C3 = 520
def scroll3(t): return 420 * (t - 6.2)
P3 = Presenter([
    (6.2, dict(path=Track([(6.2, (1300, 900)), (6.55, (900, kit.ROAD_Y + 10), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1,
               ground=None)),
    (6.55, dict(ground=kit.ROAD_Y + 10, squash=True, arms='point', point=(C3, kit.ROAD_Y - 200), look=(C3, kit.ROAD_Y - 120), expr='smile', face=None)),
    (8.31, dict(arms='cheer', expr='grin', squash=True, point=None, look=None, look_camera=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(6.2, (540, 1040, 1.2)), (7.38, (500, 1060, 1.32), 'io'), (8.31, (540, 1000, 1.18), 'io'), (9.95, (540, 1000, 1.22))],
              kicks=[(6.6, 0.1, axle_x(C3) - 40, kit.ROAD_Y - 120), (8.31, 0.16, C3, kit.ROAD_Y - 100), (9.36, 0.08, 540, 700)],
              shakes=[(8.31, 0.25, 10)])


def shot_winter(t):
    img = kit.street(t, scroll3(t)).convert('RGBA')
    img = Image.blend(img, Image.new('RGBA', (W, H), (200, 214, 236, 255)), 0.18)
    d = ImageDraw.Draw(img)
    d.rectangle((0, kit.ROAD_Y - 6, W, kit.ROAD_Y + 26), fill=(236, 242, 252))      # snow on the road edge
    for x in range(int(-scroll3(t) % 90) - 90, W, 90): d.rectangle((x, kit.ROAD_Y + 2, x + 40, kit.ROAD_Y + 8), fill=(200, 212, 230))
    cars = layer()
    fx.contact_shadow(cars, C3, kit.ROAD_Y, 620, s=S, alpha=120)
    grip = t >= 8.31
    blit(cars, up(coupe((214, 48, 58), 'duck', 1, int(scroll3(t) * 1.6) % 360), 6), C3, kit.ROAD_Y + 3 * math.sin(t * 30) * (not grip))
    ax = C3 - 50 * 6 + REAR_AXLE * 6
    for k in range(6):                                                          # snow spray off the rear tyre
        fx.puff(cars, t, 6.25 + k * 0.28, ax - 30, kit.ROAD_Y - 10, seed=30 + k, life=0.7, size=0.6, drift=(-260, -120), col=(240, 244, 252))
    kit.ROAD.reflect(img, cars, depth=140, strength=0.25)
    img.alpha_composite(cars); fg = layer()
    if t >= 6.6:                                                                # weight presses on the driven wheels
        k = ob(prog(t, 6.6, 0.25)) * (1 + 0.08 * math.sin(t * 12))
        arrow_down(fg, ax, kit.ROAD_Y - 220, k)
        blit(fg, fx.big('badge', 'WEIGHT', '#ffd23f', '#1a1a2e', '#e8b923', s=6), ax, kit.ROAD_Y - 430, k, k, -4, anchor='center')
    if grip:
        kg = ob(prog(t, 8.31, 0.2))
        blit(fg, fx.big('badge', 'GRIP', '#7fe3a0', '#1a1a2e', '#3cc85a', s=11), 600, 620, kg, kg, -5 + 2 * math.sin(t * 5), anchor='center')
        fx.ring(fg, t, 8.31, ax, kit.ROAD_Y - 40, GRN, life=0.35, r1=260)
        fx.gsparkles(fg, t, ax, kit.ROAD_Y - 40, 300, 100, n=8, seed=33)
    if t >= 9.36:
        kw = popin(t, 9.36, 0.25)
        blit(fg, fx.big('snowflake', s=14), 860, 560, kw, kw, t * 60, anchor='center')
    snow(fg, t)
    P3.draw(fg, t)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: move it and it's no longer a 911
C4 = 560
def fwd4(t): return io(prog(t, 11.13, 0.5)) * (1 - io(prog(t, 13.09, 0.25)))   # engine moves forward, then snaps back
P4 = Presenter([
    (9.9, dict(path=Track([(9.9, (-200, 500)), (10.25, (160, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (10.25, dict(ground=GROUND, squash=True, arms='present', look=(C4, 1000), expr='smile', face=None)),
    (11.13, dict(arms='point', point=lambda t: (lerp(axle_x(C4) - 40, C4 + 300, fwd4(t)), GROUND - 140), look=(C4, 1000), expr='think')),
    (12.23, dict(arms='shock', expr='shock', squash=True, point=None)),
    (13.09, dict(arms='cheer', expr='grin', squash=True, look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(9.9, (560, 940, 1.25)), (10.55, (560, 900, 1.12), 'io'), (12.23, (560, 900, 1.2), 'io'), (14.0, (560, 900, 1.16), 'io')],
              kicks=[(10.55, 0.08, 540, 470), (12.23, 0.16, C4, 1000), (13.09, 0.18, C4, 1000)], shakes=[(12.23, 0.3, 12)])


def shot_quote(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, C4, GROUND, 720, s=S, alpha=150)
    m = fwd4(t)
    boxy = 12.0 <= t < 13.09
    sr, sv = wob(t, (12.0, 13.09), 0.08)
    if boxy:
        kit.draw_car(fg, 'used', C4, 7, sx=sr, sy=sv)                           # it turns into any old car
    else:
        blit(fg, up(coupe((214, 220, 230), None, 0, 0, m > 0.05), SC), C4, GROUND, sr, sv)
        ex = lerp(axle_x(C4) - 7 * SC - 30, C4 + 200, m)
        if m > 0.05: blit(fg, up(flat_six(), SC), ex, GROUND - 80)
    if t >= 10.55:
        kq = popin(t, 10.55, 0.3) * popout(t, 12.1)
        blit(fg, fx.big('tag', 'CHIEF DESIGNER:', '#fff6e0', '#1a1a2e', s=7), 540, 470, kq, kq, -3, anchor='center')
    if t >= 12.23 and t < 13.09:
        kx = ob(prog(t, 12.23, 0.16))
        blit(fg, fx.big('xmark', s=20), C4, GROUND - 160, kx, kx, anchor='center')
        blit(fg, fx.big('stamp', 'NO LONGER A 911', '#e0303a', '#fff6e0', s=7), 540, 520, kx, kx, -6, anchor='center')
        fx.burst(fg, t, 12.23, C4, GROUND - 160, RED, n=16, seed=41)
    if t >= 13.09:
        fx.rays(fg, t, 13.09, C4, GROUND - 160, GLOW, life=0.9, r=600)
        fx.burst(fg, t, 13.09, C4, GROUND - 160, GLOW, n=18, seed=42)
        fx.sparkles(fg, t, C4, GROUND - 180, 760, 260, n=10, seed=43)
        kn = ob(prog(t, 13.09, 0.2))
        blit(fg, fx.big('badge', '911', '#ffd23f', '#1a1a2e', '#e8b923', s=14), 540, 520, kn, kn, -4, anchor='center')
    fx.poof(fg, t, 12.0, C4, GROUND - 160)
    fx.poof(fg, t, 13.09, C4, GROUND - 160)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: eight generations, one per beat, then the line-up
GEN_T = [13.95 + 0.2 * i for i in range(8)]                                    # rapid cards across 'Eight generations later'
LINE_T = 15.6


def shot_gens(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t < LINE_T:
        i = max(0, min(7, int((t - 13.95) / 0.2)))
        col, sp, fl = GENS[i]
        fx.rays(fg, t, GEN_T[i], 540, 900, col, life=0.25, r=620, n=12)
        k = ob(prog(t, GEN_T[i], 0.12))
        fx.contact_shadow(fg, 540, GROUND, 700, s=S, alpha=150)
        blit(fg, up(coupe(col, sp, fl), 7), 540, GROUND, k, k)
        blit(fg, fx.big('badge', f'GEN {i + 1}', '#ffffff', '#1a1a2e', '#d6d9e2', s=11), 540, 560, k, k, (-5, 4)[i % 2], anchor='center')
        cam = Camera(W, H, [(13.9, (540, 900, 1.15)), (LINE_T, (540, 900, 1.15))], kicks=[(g, 0.1, 540, 900) for g in GEN_T])
    else:
        for i, (col, sp, fl) in enumerate(GENS):                                # the line-up, two rows
            row = i // 4; x = 165 + (i % 4) * 250; y = GROUND - 400 + row * 230
            k = popin(t, LINE_T + 0.04 * i, 0.2)
            blit(fg, up(coupe(col, sp, fl, int(t * 300) % 360), 3), x, y, k, k)
        kb = ob(prog(t, 15.64, 0.2)) * (1 + 0.04 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'STILL THERE', '#7fe3a0', '#1a1a2e', '#3cc85a', s=10), 540, 520, kb, kb, -4, anchor='center')
        fx.confetti(fg, t, 15.64, 540, 520, n=40, seed=51)
        cam = Camera(W, H, [(LINE_T, (540, 900, 1.12)), (16.2, (540, 900, 1.02), 'io')], kicks=[(15.64, 0.12, 540, 520)])
    GAR.reflect(img, fg)
    return finish(img, fg, cam, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (2.1, shot_axle), (6.2, shot_winter), (9.9, shot_quote), (13.95, shot_gens), (END_T, shot_teaser)]
TRANS = {1: (2.1, 2.3, 'whip', dict(dx=-1)), 2: (6.2, 6.4, 'push', None), 3: (9.9, 10.12, 'iris', (axle_x(C3), kit.ROAD_Y - 100)),
         4: (13.95, 14.1, 'whip', dict(dx=1)), 5: (END_T, END_T + 0.2, 'whip', dict(dx=0, dy=1))}
KEYCOL = {'front': RED, 'behind': YEL, 'rear': YEL, 'axle': YEL, '1963': YEL, 'weight': YEL, 'grip': GRN, 'winter': GRN,
          'designer': YEL, 'longer': RED, 'eight': YEL, 'generations': YEL, 'still': GRN}
CUES = [
    (0.0, 'vroom', 1.0), (0.05, 'screech', 0.7), (0.4, 'stamp', 0.9), (0.7, 'thump', 0.6), (1.62, 'boom', 0.5),
    (2.3, 'whoosh', 0.5), (3.49, 'slide_down', 0.7), (3.94, 'click', 0.8), (3.96, 'ding', 0.6), (4.45, 'pop', 0.7), (4.55, 'thump', 0.5),
    (5.17, 'cha_ching', 0.7),
    (6.3, 'vroom', 0.6), (6.6, 'thump', 0.8), (8.31, 'ding', 0.8), (8.33, 'sparkle', 0.7), (9.36, 'sparkle', 0.7),
    (10.55, 'pop', 0.6), (11.13, 'slide_down', 0.6), (12.0, 'poof', 0.7), (12.23, 'buzzer', 0.8), (12.25, 'stamp', 0.8),
    (13.09, 'poof', 0.6), (13.1, 'vroom', 0.8), (13.12, 'sparkle', 0.7),
] + [(g, 'pop', 0.6) for g in GEN_T] + [(15.6, 'cha_ching', 0.7), (15.64, 'confetti', 0.8)] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='yellow', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
