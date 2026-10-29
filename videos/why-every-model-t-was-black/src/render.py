"""Renders 'Why Every Model T Was Black': any colour, as long as it was black (about 1914-1925).

Template: videos/ac-idle -> tractors-vs-ferraris shot structure; kit in shared/episode.py (corner rev counter on).
Word times come from align.py -> words.json (Gemini TTS read: the supplied cedar file stopped mid-script).
Speech runs 0-17.5 s; the card holds to 17.8 s. The sales-meeting quote has no confirmed date, so none is shown.
The car is a generic pixel 1910s tourer (no badge, no script on the radiator); the framed photo is a 1915 tourer
with its radiator cropped out (credits.json).
Shots:
  1 hook     0.00  the tourer flickers through colours, then a spray wipe paints it black; ANY COLOUR YOU WANT...
  2 swatch   2.00  whip; a paint-chip board fills with colours, each is crossed out until black glows: ONLY BLACK
  3 era      5.85  push; 1914 -> 1925 timeline fills black over an assembly line of black cars; photo; THE BLACK ERA
  4 why      9.80  iris; CHEAP / TOUGH / MOISTURE pop in; rain beads off the black paint
  5 myth    12.50  whip; DRIED FASTER? bubble, then a records ledger and a red X on "don't"
  6 teaser  16.40  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, layer, finish, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 17.8, 16.4
PAINTS = {'black': ((34, 36, 44), (70, 74, 88), (16, 16, 22)), 'red': ((214, 48, 58), (255, 120, 120), (140, 24, 32)),
          'blue': ((61, 127, 214), (122, 176, 240), (30, 66, 120)), 'green': ((60, 170, 100), (130, 220, 160), (30, 100, 60)),
          'yellow': ((255, 196, 40), (255, 232, 130), (160, 106, 10)), 'grey': ((130, 136, 148), (190, 196, 206), (80, 84, 96))}
SWATCH = ('red', 'blue', 'green', 'yellow', 'grey', 'black')


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def tourer(paint='black', spin=0):
    """1910s open tourer, side view (86x52 grid): tall body, fabric top up, upright screen, plain brass radiator,
    running board, flat fenders, big wooden-spoked wheels."""
    body, hi, deep = PAINTS[paint]
    img = Image.new('RGBA', (86, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(10, 10), (14, 4), (46, 4), (48, 10)], fill=(46, 44, 40)); d.line([(14, 4), (46, 4)], fill=(90, 86, 80))   # top
    for x in (14, 30, 46): d.line([(x, 5), (x - 1 if x < 30 else x + 1, 20)], fill=(70, 66, 60))
    d.polygon([(6, 20), (8, 14), (50, 14), (52, 20), (70, 20), (72, 30), (6, 32)], fill=body)                   # tub + bonnet
    d.line([(8, 15), (50, 15)], fill=hi); d.line([(52, 21), (70, 21)], fill=hi)
    d.line([(50, 8), (52, 20)], fill=(200, 210, 230)); d.line([(51, 8), (53, 20)], fill=(150, 170, 200))       # windscreen
    d.rectangle((70, 16, 76, 32), fill=(214, 160, 40)); d.rectangle((71, 18, 75, 31), fill=(60, 56, 50))        # plain brass radiator
    for y in range(19, 31, 2): d.line([(71, y), (75, y)], fill=(110, 100, 80))
    d.ellipse((76, 20, 82, 26), fill=(214, 160, 40)); d.ellipse((77, 21, 81, 25), fill=(255, 246, 200))         # lamp
    d.rectangle((14, 34, 64, 35), fill=(60, 60, 66))                                                           # running board
    for cx, r in ((15, 11), (66, 11)):
        d.chord((cx - 14, 26, cx + 14, 52), 180, 360, fill=deep)                                                # fender
        d.ellipse((cx - r, 40 - r, cx + r, 40 + r), fill=(26, 26, 30))
        d.ellipse((cx - r + 2, 40 - r + 2, cx + r - 2, 40 + r - 2), fill=(196, 140, 70))
        for k in range(10):
            a = math.radians(spin + k * 36); d.line([(cx, 40), (cx + (r - 2) * math.cos(a), 40 + (r - 2) * math.sin(a))], fill=(120, 80, 40))
        d.ellipse((cx - 2, 38, cx + 2, 42), fill=(214, 160, 40))
    return outline(img)


@lru_cache(None)
def spray_gun():
    img = Image.new('RGBA', (26, 18), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((6, 3, 22, 8), fill=(176, 182, 192)); d.rectangle((20, 4, 25, 7), fill=(96, 100, 110))
    d.polygon([(8, 8), (12, 8), (10, 17), (6, 17)], fill=(60, 63, 71)); d.rectangle((2, 0, 8, 5), fill=(34, 36, 44))
    return outline(img)


@lru_cache(None)
def ledger(open_=1.0):
    """Old records ledger (44x32) with ruled lines."""
    img = Image.new('RGBA', (44, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 2, 43, 31), fill=(120, 64, 40)); d.rectangle((2, 0, 21, 29), fill=(250, 244, 226)); d.rectangle((22, 0, 41, 29), fill=(244, 236, 214))
    for y in range(4, 28, 3):
        d.line([(4, y), (19, y)], fill=(170, 170, 190)); d.line([(24, y), (39, y)], fill=(170, 170, 190))
    d.line([(21, 0), (21, 29)], fill=(150, 120, 90))
    return outline(img)


@lru_cache(None)
def droplet():
    img = Image.new('RGBA', (6, 9), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(3, 0), (5, 5), (3, 8), (1, 5)], fill=(120, 190, 255)); d.point((2, 5), fill=(220, 240, 255))
    return img


def two_tone(cv, t, t0, t1, parts, y, sz=120, rot=-2.0):
    """One title line of differently coloured words, popping in at t0 and out at t1."""
    if not (t0 <= t < t1 + 0.2): return
    imgs = [kit.text_img(s, c, sz) for s, c in parts]
    line = Image.new('RGBA', (sum(i.width for i in imgs) - 50 * (len(imgs) - 1), max(i.height for i in imgs)), (0, 0, 0, 0)); x = 0
    for i in imgs: line.alpha_composite(i, (x, 0)); x += i.width - 50
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2) * min(1.0, 1000 / line.width) * (1 + 0.025 * math.sin(t * 8))
    blit(cv, line, W / 2, y, k, k, rot + 1.5 * math.sin(t * 3), anchor='center')


# ================================================================== shot 1: hook, any colour... painted black
CX1 = 540
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (1300, 300)), (0.15, (1300, 300)), (0.5, (900, GROUND), 'ic')]), size=7, legs='auto', arms='fly',
                expr='grin', face=-1, ground=None)),
    (0.5, dict(ground=GROUND, squash=True, arms=('aim', 170), look=(CX1, 1000), expr='grin', face=None)),
    (1.5, dict(arms='thumb', expr='smirk', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.45)), (0.0, (540, 960, 1.45)), (0.5, (560, 940, 1.18), 'io'), (2.05, (560, 920, 1.22))],
              kicks=[(0.0, 0.12, CX1, 1000), (0.5, 0.08, 900, 1000), (1.0, 0.14, CX1, 1000)], shakes=[(1.0, 0.3, 10)])


def wipe1(t): return oc(prog(t, 0.95, 0.45))                                    # 0 colourful -> 1 black, left to right


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 0.0, CX1, 860, GLOW, hold=True, r=620, n=12)
    fx.contact_shadow(fg, CX1, GROUND, 680, s=S, alpha=150)
    col = SWATCH[int(t * 9) % 5]
    sr, sv = wob(t, (0.0, 1.0), 0.06)
    a = up(tourer(col), 8); b = up(tourer('black'), 8)
    w = wipe1(t)
    if 0 < w < 1:                                                               # the spray wipe crosses the car
        m = Image.new('L', a.size, 0); ImageDraw.Draw(m).rectangle((0, 0, int(a.width * w), a.height), fill=255)
        a = a.copy(); a.paste(b, (0, 0), m)
    elif w >= 1: a = b
    blit(fg, a, CX1, GROUND, sr, sv)
    if 0.9 <= t < 1.5:
        gx = CX1 - a.width / 2 + a.width * w
        blit(fg, up(spray_gun(), 8), gx + 40, 600, 1, 1, -30, flip=True, anchor='center')
        for k in range(10):                                                      # paint mist
            fx.puff(fg, t, 0.95 + k * 0.05, gx, 820 + 30 * (k % 4), seed=10 + k, life=0.45, size=0.6, drift=(30, 160), col=(40, 42, 50))
    if t >= 1.4:
        fx.glint(fg, t, 1.45, CX1 + 120, GROUND - 300, r=160)
        fx.sparkles(fg, t, CX1, GROUND - 240, 700, 300, n=8, seed=12)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    two_tone(cv, t, 0.05, 1.95, (('ANY COLOUR', YEL),), 430, 150, -3)
    two_tone(cv, t, 0.3, 1.95, (('YOU WANT...', kit.WHITE),), 590, 120, 2)
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 430, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: the swatch board, crossed out
BOARD = (540, 700)
CHIP_T = (2.1, 2.3, 2.5, 2.7, 2.9, 3.36)                                         # chips land up to 'colour'
CROSS_T = (4.47, 4.62, 4.77, 4.92, 5.07)                                         # crossed out on 'as long as it was'
def chip_xy(i): return BOARD[0] - 300 + (i % 3) * 300, BOARD[1] - 130 + (i // 3) * 260
P2 = Presenter([
    (2.0, dict(path=Track([(2.0, (-200, 400)), (2.35, (170, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (2.35, dict(ground=GROUND, squash=True, arms='present', look=BOARD, expr='grin', face=None)),
    (4.47, dict(arms='point', point=lambda t: chip_xy(min(4, int((t - 4.47) / 0.15))), look=BOARD, expr='smirk')),
    (5.2, dict(arms='cheer', expr='wow', squash=True, point=None, look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.0, (540, 860, 1.25)), (2.6, (540, 840, 1.12), 'io'), (5.2, (560, 820, 1.2), 'io'), (5.9, (560, 820, 1.25))],
              kicks=[(3.36, 0.08, *BOARD), (5.2, 0.16, *chip_xy(5))], shakes=[(5.2, 0.25, 10)])


def shot_swatch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    kb = popin(t, 2.0, 0.3)
    if kb > 0.02:
        bw, bh = int(920 * kb), int(620 * kb)
        d.rounded_rectangle((BOARD[0] - bw / 2, BOARD[1] - bh / 2, BOARD[0] + bw / 2, BOARD[1] + bh / 2), 20, fill=(250, 246, 236),
                            outline=(26, 26, 46), width=8)
    for i, (name, t0) in enumerate(zip(SWATCH, CHIP_T)):
        k = popin(t, t0, 0.22)
        if k <= 0.02: continue
        x, y = chip_xy(i); body = PAINTS[name][0]
        hot = name == 'black' and t >= 5.2
        r = 105 * k * (1.12 + 0.05 * math.sin(t * 9) if hot else 1)
        d.rounded_rectangle((x - r, y - r, x + r, y + r), 16, fill=body + (255,), outline=(26, 26, 46), width=8)
        d.rectangle((x - r + 16, y - r + 14, x - r + 50, y - r + 22), fill=PAINTS[name][1] + (255,))
        if i < 5 and t >= CROSS_T[i]:
            kx = ob(prog(t, CROSS_T[i], 0.15))
            blit(fg, fx.big('xmark', s=13), x, y, kx, kx, anchor='center')
            fx.burst(fg, t, CROSS_T[i], x, y, RED, n=8, r0=40, r1=160, seed=20 + i)
    if t >= 5.2:
        x, y = chip_xy(5)
        fx.rays(fg, t, 5.2, x, y, GLOW, life=1.0, r=380)
        blit(fg, fx.big('check', s=10), x + 90, y - 90, 1, 1, anchor='center')
        ks = ob(prog(t, 5.25, 0.18))
        blit(fg, fx.big('stamp', 'ONLY BLACK', '#e0303a', '#fff6e0', s=9), 540, 330 + 8 * math.sin(t * 5), ks, ks, -6, anchor='center')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: 1914-1925, the black era (assembly line)
TL = (230, 850, 580)                                                            # timeline x0, x1, y
def era(t): return oc(prog(t, 6.25, 0.95))                                     # fills from 1914 to 1925 as he says it
P3 = Presenter([
    (5.85, dict(path=Track([(5.85, (1300, 300)), (6.2, (940, GROUND + 40), 'oc')]), size=6, legs='auto', arms='fly', expr='grin', face=-1,
                ground=None)),
    (6.2, dict(ground=GROUND + 40, squash=True, arms='point', point=(TL[0], TL[2]), look=(540, TL[2]), expr='smile', face=None)),
    (7.14, dict(point=(TL[1], TL[2]), expr='wow')),
    (8.21, dict(arms='cheer', expr='grin', point=None, look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(5.85, (540, 860, 1.2)), (7.14, (540, 820, 1.12), 'io'), (8.21, (540, 880, 1.2), 'io'), (9.85, (540, 880, 1.24))],
              kicks=[(6.25, 0.08, TL[0], TL[2]), (7.14, 0.1, TL[1], TL[2]), (8.21, 0.14, 540, TL[2]), (8.75, 0.08, 540, 400)])


def shot_era(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    belt_y = GROUND - 120                                                       # assembly line: black cars roll across
    d.rectangle((0, belt_y, W, belt_y + 44), fill=(60, 63, 71)); d.rectangle((0, belt_y, W, belt_y + 8), fill=(150, 156, 170))
    for x in range(int(-(t * 260) % 80) - 80, W, 80): d.rectangle((x, belt_y + 14, x + 40, belt_y + 22), fill=(40, 42, 48))
    for k in range(4):
        x = (t * 260 + k * 420) % (4 * 420) - 300
        blit(fg, up(tourer('black', int(-x) % 360), 4), x, belt_y)
    kl = popin(t, 5.9, 0.3)                                                     # timeline
    if kl > 0.02:
        x0, x1, y = TL
        d.rounded_rectangle((x0 - 20, y - 40, x1 + 20, y + 40), 30, fill=(250, 246, 236), outline=(26, 26, 46), width=8)
        xe = x0 + (x1 - x0) * era(t)
        if xe > x0 + 10: d.rounded_rectangle((x0, y - 22, xe, y + 22), 20, fill=(26, 26, 30))
        for i in range(12): d.line([(x0 + (x1 - x0) * i / 11, y + 26), (x0 + (x1 - x0) * i / 11, y + 36)], fill=(26, 26, 46), width=4)
        for txt, x, t0 in (('1914', x0, 6.25), ('1925', x1, 7.14)):
            k = popin(t, t0, 0.25)
            blit(fg, fx.big('badge', txt, '#ffd23f', '#1a1a2e', '#e8b923', s=7), x, y - 110, k, k, -4, anchor='center')
    if t >= 8.21:
        fx.ring(fg, t, 8.21, 540, TL[2], GRN, life=0.4, r1=500)
        kb = ob(prog(t, 8.75, 0.2))
        blit(fg, fx.big('badge', 'THE BLACK ERA', '#7fe3a0', '#1a1a2e', '#3cc85a', s=8), 540, 400, kb, kb, -3 + 2 * math.sin(t * 4), anchor='center')
        fx.gsparkles(fg, t, 540, 400, 700, 120, n=8, seed=31)
    photo(fg, t, 7.4, 9.75, 'model_t_tourer_crop', 330, 790, 360, 340, -4, 'A REAL ONE, 1915', focus=(0.5, 0.5), zoom=0.05)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: why black: cheap, tough, moisture
WHY = ((260, 520, 10.09, 'CHEAP', '$'), (540, 470, 10.57, 'TOUGH', '!'), (820, 520, 11.54, 'MOISTURE', None))
P4 = Presenter([
    (9.8, dict(path=Track([(9.8, (-200, 700)), (10.1, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (10.1, dict(ground=GROUND, squash=True, arms='present', look=(540, 600), expr='smile', face=None)),
    (11.96, dict(arms='thumb', expr='grin', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(9.8, (540, 860, 1.25)), (10.3, (540, 840, 1.12), 'io'), (12.55, (540, 840, 1.18))],
              kicks=[(10.09, 0.08, 260, 520), (10.57, 0.08, 540, 470), (11.54, 0.1, 820, 520)])


def shot_why(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 600, GROUND, 600, s=S, alpha=140)
    blit(fg, up(tourer('black'), 7), 600, GROUND)
    if t >= 11.3:                                                               # rain beads and bounces off the paint
        r = fx.rng(7)
        for k in range(26):
            x = 330 + r.uniform(0, 560); ph = (t * 1.4 + r.uniform(0, 1)) % 1
            y = lerp(200, GROUND - 330, ph) if ph < 0.8 else GROUND - 330 - 60 * math.sin((ph - 0.8) / 0.2 * math.pi)
            blit(fg, up(droplet(), 6), x + (40 * (ph - 0.8) / 0.2 if ph >= 0.8 else 0), y, anchor='center')
        fx.glint(fg, t, 11.6, 700, GROUND - 300, r=150)
    for i, (x, y, t0, word, glyph) in enumerate(WHY):
        k = ob(prog(t, t0, 0.22))
        if k <= 0.02: continue
        blit(fg, fx.big('badge', word, '#7fe3a0', '#1a1a2e', '#3cc85a', s=7), x, y + 130, k, k, (-4, 3, -3)[i], anchor='center')
        if glyph: blit(fg, fx.big('glyph', glyph, '#ffd23f', s=14), x, y, k, k, 8 * math.sin(t * 4 + i), anchor='center')
        else: blit(fg, up(droplet(), 16), x, y, k, k, anchor='center')
        blit(fg, fx.big('check', s=6), x + 110, y + 60, k, k, anchor='center')
        fx.burst(fg, t, t0, x, y, GRN, n=10, r0=40, r1=180, seed=40 + i)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the myth, crossed out
BUB = (620, 560)
P5 = Presenter([
    (12.5, dict(path=Track([(12.5, (-200, 500)), (12.85, (230, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='think', face=1, ground=None)),
    (12.85, dict(ground=GROUND, squash=True, arms='think', look=BUB, expr='think', face=None)),
    (15.05, dict(arms='point', point=(700, 1000), look=(700, 1000), expr='smirk')),
    (15.43, dict(arms='hips', expr='smirk', point=None, look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(12.5, (560, 860, 1.25)), (13.89, (600, 760, 1.25), 'io'), (15.05, (600, 860, 1.12), 'io'), (16.45, (600, 860, 1.18))],
              kicks=[(13.89, 0.1, *BUB), (15.05, 0.08, 700, 1000), (15.43, 0.2, *BUB)], shakes=[(15.43, 0.35, 14)])


def shot_myth(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    kb = popin(t, 12.7, 0.3)
    if kb > 0.02:
        blit(fg, fx.big('bubble', 3, s=24), BUB[0], BUB[1], kb, kb, 2 * math.sin(t * 2), anchor='center')
    if t >= 13.89:
        kq = ob(prog(t, 13.89, 0.2))
        blit(fg, fx.big('tag', 'DRIED FASTER?', '#fff6e0', '#1a1a2e', s=8), BUB[0], BUB[1] - 20, kq, kq, -3, anchor='center')
    if t >= 15.05:                                                              # the records come up
        kl = ob(prog(t, 15.05, 0.25))
        blit(fg, up(ledger(), 9), 720, GROUND - 40 + 30 * (1 - kl), kl, kl)
        fx.sparkles(fg, t, 720, GROUND - 180, 400, 200, n=6, seed=51)
    if t >= 15.43:
        kx = ob(prog(t, 15.43, 0.16))
        blit(fg, fx.big('xmark', s=26), BUB[0], BUB[1], kx, kx, -4, anchor='center')
        fx.burst(fg, t, 15.43, *BUB, RED, n=18, seed=52)
        fx.ring(fg, t, 15.43, *BUB, (224, 48, 58), life=0.35, r1=460)
        ks = ob(prog(t, 15.6, 0.18))
        blit(fg, fx.big('stamp', 'MYTH', '#e0303a', '#fff6e0', s=12), BUB[0] + 120, BUB[1] + 330, ks, ks, -10, anchor='center')
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (2.0, shot_swatch), (5.85, shot_era), (9.8, shot_why), (12.5, shot_myth), (END_T, shot_teaser)]
TRANS = {1: (2.0, 2.2, 'whip', dict(dx=-1)), 2: (5.85, 6.05, 'push', None), 3: (9.8, 10.02, 'iris', (540, TL[2])),
         4: (12.5, 12.7, 'whip', dict(dx=1)), 5: (END_T, END_T + 0.2, 'whip', dict(dx=0, dy=1))}
KEYCOL = {'colour': YEL, 'black': RED, '1914': GRN, '1925': GRN, 'cheap': GRN, 'tough': GRN, 'moisture': GRN,
          'faster': YEL, "don't": RED, 'records': RED}
CUES = [
    (0.0, 'sparkle', 0.8), (0.05, 'stamp', 0.6), (0.3, 'pop', 0.6), (0.5, 'thump', 0.6), (0.95, 'whoosh', 0.9), (1.0, 'poof', 0.6),
    (1.45, 'ding', 0.8), (1.47, 'sparkle', 0.6),
    (2.1, 'pop', 0.5), (2.3, 'pop', 0.5), (2.5, 'pop', 0.5), (2.7, 'pop', 0.5), (2.9, 'pop', 0.5), (3.36, 'pop', 0.7),
    (4.47, 'click', 0.7), (4.62, 'click', 0.7), (4.77, 'click', 0.7), (4.92, 'click', 0.7), (5.07, 'click', 0.7), (5.2, 'stamp', 1.0),
    (5.22, 'boom', 0.4),
    (6.25, 'pop', 0.6), (6.3, 'slide_down', 0.5), (7.14, 'pop', 0.6), (7.4, 'pop', 0.5), (8.21, 'ding', 0.8), (8.75, 'cha_ching', 0.6),
    (10.09, 'cha_ching', 0.8), (10.57, 'thump', 0.8), (11.54, 'pop', 0.7), (11.6, 'sparkle', 0.6),
    (12.7, 'pop', 0.6), (13.89, 'pop', 0.7), (15.05, 'slide_down', 0.5), (15.43, 'buzzer', 0.8), (15.45, 'stamp', 0.9), (15.6, 'stamp', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='black', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
