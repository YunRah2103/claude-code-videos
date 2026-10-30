"""Renders 'R1T gear tunnel': a hidden tunnel behind the rear seats, reached by folding the armrest and sliding a door up.

Template: videos/plaid-two-seconds (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json; the voiceover is out/rivian-gear-tunnel/voiceover.wav (clip 4 of out/voiceover/full_voiceover.wav; its
first 1.1 s is the tail of the 2 s join gap). The mixer holds a 2.0 s pause before 'Follow for the next one' (GAP)
for the recap beat; later words are shifted to match. The truck and cabin are generic pixel drawings, no lettering.
Shots:
  1 hatch    0.00  hook: rear bench, the armrest folds down, a door slides up, the tunnel glows, 'A hidden tunnel.'
  2 photo    2.00  garage: the real R1T photo pops in, HIDDEN tag
  3 cutaway  3.90  side cutaway of a generic pickup: the tunnel slot between the rear seats and the bed, 'behind the rear seats'
  4 cabin    7.05  back in the cabin: he folds the armrest (folding down) and slides the door (sliding a door up)
  5 recap   10.20  cutaway again: a bag slides into the tunnel from the cabin side, GEAR TUNNEL label, tick
  6 teaser  12.55  shared NEXT EPISODE ending ('Follow for the next one.')
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline
from pixanim.sprites import check

RAW = kit.load_words(HERE)
GAP = (10.2, 2.0)                                     # pause inserted between 'up.' and 'Follow'
WORDS = kit.shift_words(RAW, *GAP)
DUR = 17.0
END_T = 12.55
def ws(i): return WORDS[i]['s']


# ------------------------------------------------------------------ episode sprites
SEAT, SEAT_D, TRIM, HOLE = (70, 74, 86), (52, 56, 66), (120, 126, 138), (16, 16, 24)


@lru_cache(None)
def bench(fold=0.0, door=0.0):
    """Rear bench seen from the front (90x64): two seat backs, a centre armrest that folds down (`fold` 0..1)
    and, behind it, a pass-through door that slides up (`door` 0..1) onto a glowing tunnel with a bag inside."""
    img = Image.new('RGBA', (90, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for x0 in (0, 56):                                                            # outer seat backs
        d.rounded_rectangle((x0, 0, x0 + 33, 44), 5, fill=SEAT)
        for y in range(6, 42, 7): d.line([(x0 + 4, y), (x0 + 29, y)], fill=SEAT_D)
        d.rounded_rectangle((x0 + 6, -2, x0 + 27, 6), 3, fill=SEAT_D)              # headrest stub
    d.rectangle((34, 0, 55, 44), fill=SEAT_D)                                     # centre back
    d.rounded_rectangle((0, 42, 89, 63), 5, fill=(60, 64, 76))                     # cushion
    for x in (30, 60): d.line([(x, 46), (x, 62)], fill=SEAT_D)
    # opening behind the armrest
    d.rectangle((36, 6, 53, 40), fill=HOLE)
    if door > 0 and 6 + round(34 * (1 - door)) <= 38:
        gy = 6 + round(34 * (1 - door))
        d.rectangle((37, gy, 52, 39), fill=(40, 46, 66))
        d.rectangle((37, gy, 52, gy + 1), fill=(255, 217, 59))                     # tunnel light strip
        by = max(gy + 3, 22)
        if by <= 33:                                                              # a duffel bag inside
            d.rounded_rectangle((40, by, 49, 37), 2, fill=(214, 90, 60)); d.line([(42, by + 2), (47, by + 2)], fill=(255, 160, 120))
    hd = round(34 * (1 - door))                                                   # the door panel slides up out of view
    if hd > 0:
        d.rectangle((36, 6, 53, 6 + hd), fill=TRIM)
        for y in range(8, 6 + hd, 4): d.line([(38, y), (51, y)], fill=(150, 156, 170))
        d.rectangle((43, 4 + hd, 46, 5 + hd), fill=(60, 64, 76))                  # pull tab
    # armrest: upright it covers the opening; folded it lies flat on the cushion
    h = round(34 * (1 - fold)); y1 = 41
    if fold < 1:
        d.rounded_rectangle((34, y1 - max(h, 4), 55, y1), 3, fill=(150, 156, 170))
        d.line([(36, y1 - max(h, 4) + 2), (53, y1 - max(h, 4) + 2)], fill=(200, 204, 214))
    if fold > 0:
        L = round(20 * fold)
        d.rounded_rectangle((34, y1 - 1, 55, y1 + L), 3, fill=(150, 156, 170))
        d.line([(36, y1), (53, y1)], fill=(200, 204, 214))
        if L > 10:                                                                # cupholders
            d.ellipse((37, y1 + L - 9, 43, y1 + L - 3), fill=(40, 42, 52)); d.ellipse((46, y1 + L - 9, 52, y1 + L - 3), fill=(40, 42, 52))
    return outline(img)


@lru_cache(None)
def truck(tunnel=0, bag=-1.0):
    """Side cutaway of a generic pickup (120x46): cab, rear seat, the tunnel slot behind it (pulsing when
    `tunnel`), open bed. bag 0..1 slides a bag along the tunnel (drawn as a box entering the slot)."""
    img = Image.new('RGBA', (120, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, dark, glass = (124, 138, 120), (86, 98, 84), (150, 190, 220)
    d.rounded_rectangle((2, 18, 117, 36), 4, fill=body)                           # lower body
    d.polygon([(14, 18), (26, 4), (60, 4), (64, 18)], fill=body)                   # cab
    d.polygon([(18, 17), (27, 7), (42, 7), (42, 17)], fill=glass); d.rectangle((45, 7, 59, 17), fill=glass)
    d.rectangle((2, 24, 117, 25), fill=dark)
    d.rectangle((2, 20, 5, 22), fill=(255, 240, 200)); d.rectangle((114, 20, 117, 23), fill=(220, 60, 60))
    # cutaway window into the rear seat and tunnel
    d.rectangle((44, 18, 66, 33), fill=(30, 32, 40))
    d.polygon([(47, 32), (47, 16), (52, 12), (55, 12), (54, 32)], fill=(70, 74, 86))   # rear seat back
    d.rectangle((44, 28, 56, 32), fill=(60, 64, 76))                               # cushion
    g = (255, 217, 59) if tunnel else (180, 160, 80)
    d.rectangle((58, 22, 66, 33), fill=(40, 46, 66)); d.rectangle((58, 22, 66, 23), fill=g); d.rectangle((58, 32, 66, 33), fill=g)
    d.rectangle((57, 22, 57, 33), fill=g); d.rectangle((67, 22, 67, 33), fill=g)
    d.rectangle((68, 12, 115, 18), fill=dark); d.rectangle((70, 14, 113, 18), fill=(46, 50, 60))   # bed
    if bag >= 0:
        bx = round(lerp(48, 59, bag))
        d.rounded_rectangle((bx, 26, bx + 6, 31), 1, fill=(214, 90, 60))
    for cx in (22, 96):                                                           # wheels
        d.ellipse((cx - 9, 27, cx + 9, 45), fill=(30, 32, 40)); d.ellipse((cx - 5, 31, cx + 5, 41), fill=(150, 156, 170))
        d.ellipse((cx - 2, 34, cx + 2, 38), fill=(60, 64, 76))
    return outline(img)


# ================================================================== shot 1: hook, the secret door
FOLD1, DOOR1 = 0.25, 0.95
CAM1 = Camera(W, H, [(-1.0, (540, 900, 1.02)), (0.0, (540, 900, 1.02)), (DOOR1, (540, 880, 1.1), 'io'), (2.1, (540, 860, 1.16), 'io')],
              kicks=[(FOLD1 + 0.35, 0.12, 540, 980), (DOOR1 + 0.35, 0.2, 540, 700)], shakes=[(DOOR1 + 0.35, 0.3, 10)])


def shot_hatch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    f = oc(prog(t, FOLD1, 0.35)); dr = io(prog(t, DOOR1, 0.35))
    blit(fg, up(bench(round(f * 8) / 8, round(dr * 12) / 12), 10), 540, 1180)
    if t >= DOOR1 + 0.35:
        fx.ring(fg, t, DOOR1 + 0.35, 540, 760, GLOW, r1=360)
        fx.burst(fg, t, DOOR1 + 0.35, 540, 760, GLOW, n=14, r0=200, r1=420, seed=2); fx.sparkles(fg, t, 540, 760, 300, 340, n=8, seed=3)
    if t >= FOLD1 + 0.35: fx.dust(fg, t, FOLD1 + 0.35, 540, 1000, n=8, seed=4)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t, rim=False)


# ================================================================== shot 2: the real truck
T2 = 2.0
P2 = Presenter([
    (T2 - 0.05, dict(path=Track([(T2 - 0.05, (-200, 300)), (T2 + 0.4, (200, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (T2 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(560, 640), look=(560, 640), expr='smirk', face=None)),
    (ws(5), dict(arms='shock', point=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(T2, (540, 900, 1.08)), (3.9, (540, 880, 1.16), 'io')],
              kicks=[(T2 + 0.1, 0.08, 560, 640), (ws(5), 0.16, 700, 1080)], shakes=[(ws(5), 0.25, 8)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= ws(5):                                     # 'hidden'
        k = fx.slam(t, ws(5)) * popin(t, ws(5), 0.2)
        blit(fg, fx.big('tag', 'HIDDEN', '#fff6e0', '#d6303a', s=10), 700, 1090, k, k, -6 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, ws(5), 700, 1090, RED, n=12, seed=21)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: cutaway, behind the rear seats
T3 = 3.9
B0 = ws(8)                                            # 'behind'
TX, TY, TS = 540, 1060, 8                             # truck centre-bottom and scale
def slot(): return TX - 60 * TS + 62 * TS, TY - 46 * TS + 27 * TS   # tunnel centre on screen (grid 62, 27)
CAM3 = Camera(W, H, [(T3, (540, 880, 1.0)), (B0, (540, 880, 1.03), 'io'), (ws(10), (540, 860, 1.08), 'io'), (7.05, (540, 860, 1.1))],
              kicks=[(T3 + 0.1, 0.08, 540, 860), (B0, 0.1, *slot()), (ws(11), 0.16, *slot())], shakes=[(ws(11), 0.25, 8)])


def shot_cutaway(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, T3 + 0.05, 0.3)
    blit(fg, up(truck(int(t >= B0 and int(t * 6) % 2 == 0)), TS), TX, TY, k, k)
    fx.contact_shadow(fg, TX, TY, 900, s=8)
    sx, sy = slot()
    if t >= B0:
        d = ImageDraw.Draw(fg); r = 70 + 10 * math.sin(t * 8)
        d.rectangle((sx - r, sy - r - 10, sx + r, sy + r + 10), outline=(255, 217, 59, 230), width=9)
        fx.ring(fg, t, B0, sx, sy, GLOW, r1=300)
    dg.label(fg, t, ws(10), 'REAR SEATS', (sx - 70, sy - 40), (sx - 200, sy - 300), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    dg.label(fg, t, ws(11), 'BED', (sx + 200, sy - 90), (sx + 250, sy - 300), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    if t >= ws(11): fx.sparkles(fg, t, sx, sy, 260, 200, n=6, seed=31)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: in the cabin, fold and slide
T4 = 7.05
FOLD4, DOOR4 = ws(20), ws(25)                         # 'folding', 'sliding'
P4 = Presenter([
    (T4 - 0.05, dict(path=Track([(T4 - 0.05, (1300, 300)), (T4 + 0.4, (900, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (T4 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 860), look=(540, 860), expr='smile', face=None)),
    (DOOR4, dict(arms='point', point=(540, 700), look=(540, 700), expr='wow')),
    (DOOR4 + 0.7, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(T4, (540, 900, 1.02)), (FOLD4, (540, 920, 1.08), 'io'), (DOOR4, (540, 860, 1.14), 'io'), (10.2, (540, 860, 1.18))],
              kicks=[(ws(16), 0.08, 540, 860), (FOLD4 + 0.35, 0.14, 540, 980), (DOOR4 + 0.35, 0.18, 540, 700)], shakes=[(DOOR4 + 0.35, 0.25, 8)])


def shot_cabin(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    f = oc(prog(t, FOLD4, 0.35)); dr = io(prog(t, DOOR4, 0.4))
    k = popin(t, T4 + 0.05, 0.3)
    blit(fg, up(bench(round(f * 8) / 8, round(dr * 12) / 12), 9), 540, 1180, k, k)
    dg.arrow_to(fg, t, FOLD4 - 0.15, (540, 930), angle=90, dist=150, s=7, t1=FOLD4 + 0.4)
    dg.arrow_to(fg, t, DOOR4 - 0.15, (540, 760), angle=-90, dist=150, s=7, t1=DOOR4 + 0.5)
    if t >= DOOR4 + 0.4:
        fx.ring(fg, t, DOOR4 + 0.4, 540, 800, GLOW, r1=340)
        fx.burst(fg, t, DOOR4 + 0.4, 540, 760, GLOW, n=14, seed=41); fx.sparkles(fg, t, 540, 760, 360, 300, n=6, seed=42)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t, rim=False)


# ================================================================== shot 5: recap, gear goes in
T5 = 10.2
CAM5 = Camera(W, H, [(T5, (540, 880, 1.02)), (T5 + 1.0, (540, 860, 1.1), 'io'), (END_T, (540, 860, 1.12))],
              kicks=[(T5 + 0.3, 0.08, *slot()), (T5 + 1.1, 0.16, *slot())])


def shot_recap(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    bag = clamp((t - T5 - 0.3) / 0.8)
    blit(fg, up(truck(int(int(t * 6) % 2 == 0), round(bag * 10) / 10), TS), TX, TY)
    fx.contact_shadow(fg, TX, TY, 900, s=8)
    sx, sy = slot()
    dg.label(fg, t, T5 + 0.1, 'GEAR TUNNEL', (sx, sy - 60), (sx, sy - 360), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    if t >= T5 + 1.1:
        k = fx.slam(t, T5 + 1.1) * popin(t, T5 + 1.1, 0.2)
        blit(fg, up(check(), 10), sx + 260, sy - 120, k, k, 0, anchor='center')
        fx.burst(fg, t, T5 + 1.1, sx + 260, sy - 120, GRN, n=14, seed=51); fx.confetti(fg, t, T5 + 1.1, sx, sy - 200, n=24, seed=52)
    fx.sparkles(fg, t, sx, sy, 300, 220, n=6, seed=53)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)


def overlay(cv, t):
    title(cv, t, 0.05, 1.95, 'A hidden', YEL, 380, 130, -3)
    title(cv, t, 0.2, 1.95, 'tunnel.', YEL, 520, 130, 2)
    kit.photo_hq(cv, t, T2 + 0.1, 3.8, 'r1t', 560, 640, 800, rot=-3, label='THE REAL TRUCK')
    title(cv, t, B0, 7.0, 'behind the', GRN, 380, 116, -2)
    title(cv, t, ws(10), 7.0, 'rear seats', GRN, 510, 116, 2)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hatch), (T2, shot_photo), (T3, shot_cutaway), (T4, shot_cabin), (T5, shot_recap), (END_T, shot_teaser)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (T4, T4 + 0.2, 'iris', (540, 860)),
         4: (T5, T5 + 0.2, 'whip', dict(dx=0, dy=1)), 5: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'rivian': YEL, 'hidden': YEL, 'behind': GRN, 'seats': GRN, 'inside': YEL, 'armrest': YEL, 'door': YEL}
CUES = [(0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (FOLD1, 'creak', 0.6), (FOLD1 + 0.35, 'thump', 0.6), (DOOR1, 'slide_down', 0.5),
        (DOOR1 + 0.35, 'ding', 0.8), (DOOR1 + 0.37, 'sparkle', 0.8),
        (T2 + 0.1, 'pop', 0.7), (T2 + 0.4, 'thump', 0.4), (ws(5), 'stamp', 0.7),
        (T3 + 0.05, 'pop', 0.5), (B0, 'ding', 0.6), (ws(10), 'pop', 0.6), (ws(11), 'pop', 0.6), (ws(11) + 0.02, 'sparkle', 0.6),
        (T4 + 0.4, 'thump', 0.4), (FOLD4, 'creak', 0.6), (FOLD4 + 0.35, 'thump', 0.6), (DOOR4, 'slide_down', 0.5), (DOOR4 + 0.4, 'ding', 0.7),
        (DOOR4 + 0.42, 'sparkle', 0.7), (T5 + 0.1, 'pop', 0.6), (T5 + 0.3, 'whoosh', 0.5), (T5 + 1.1, 'ding', 0.8), (T5 + 1.12, 'confetti', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, gap=GAP, crisp=True)

if __name__ == '__main__':
    kit.main()
