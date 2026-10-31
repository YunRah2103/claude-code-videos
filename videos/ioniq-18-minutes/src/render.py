"""Renders 'Ioniq, 18 minutes': 10-80% in about 18 minutes on 800 volts, but only on a 350 kW charger.

Template: videos/the-trabant (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). The EPA range figure from the brief is not in the script, so it is
not shown. The car is a generic pixel hatchback with no badges or lettering; one framed photo (pixel redraw).
Shots:
  1 battery  0.00  a pixel battery fills 10% -> 80% in a flash with bolts; '18 minutes'; 18 MIN clock
  2 car      3.00  a boxy pixel hatchback rolls in; photo card; 800 V badge with arcs between the wheels
  3 charger  7.30  a tall fast charger, the cable swings in and plugs in; 350 kW; current pulses; '350 kW charger'
  4 compare 11.10  slow wallbox vs fast charger: red X and green tick; 'only as fast as the charger'
  5 teaser  14.25  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
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
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE, 'words_v1.json')     # first read: the body shots are timed on it
NEW = kit.load_words(HERE)                          # current read (captions); WARP maps it onto WORDS
GREAT, THATS = kit.at(NEW, 'sounds'), kit.at(NEW, "that's")    # cuts follow the read
BODY_END = kit.at(NEW, "what's") - 0.12
END_T = NEW[-1]['e'] + 0.3
DUR = END_T + 1.0
TEAL = (0, 190, 170)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def battery(level=0.1):
    """Upright battery (34x56) with a terminal cap; cells fill bottom-up, red/yellow/green by level."""
    img = Image.new('RGBA', (34, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((11, 0, 22, 4), fill=(170, 176, 188))
    d.rounded_rectangle((0, 4, 33, 57), 4, fill=(60, 64, 76)); d.rounded_rectangle((3, 7, 30, 54), 2, fill=(20, 21, 28))
    col = (224, 48, 58) if level < 0.25 else (255, 196, 40) if level < 0.6 else (60, 200, 90)
    n = round(level * 10)
    for i in range(n):
        y1 = 52 - i * 4.6; d.rectangle((5, y1 - 3, 28, y1), fill=col); d.line([(5, y1 - 3), (28, y1 - 3)], fill=tuple(min(255, c + 60) for c in col))
    return outline(img)


@lru_cache(None)
def bolt(col='#ffd23f'):
    img = Image.new('RGBA', (12, 18), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(7, 0), (1, 10), (5, 10), (3, 17), (11, 6), (7, 6), (9, 0)], fill=col)
    return outline(img)


@lru_cache(None)
def hatch(spin=0, port=0.0):
    """Boxy EV hatchback (96x42), nose right: flat sides, square pixel lamps, sharp creases, charge port glowing by port."""
    img = Image.new('RGBA', (96, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, hi, lo = (176, 182, 172), (220, 226, 216), (120, 126, 118)
    pts = [(3, 16), (14, 14), (22, 4), (62, 4), (76, 14), (92, 17), (93, 32), (3, 32)]
    d.polygon(pts, fill=body); d.line(pts[:-2], fill=hi)
    d.polygon([(24, 6), (44, 6), (44, 14), (17, 14)], fill=(50, 60, 76)); d.polygon([(47, 6), (61, 6), (72, 14), (47, 14)], fill=(50, 60, 76))
    d.line([(10, 22), (92, 26)], fill=lo)                                        # diagonal crease
    for x in range(84, 92, 2): d.rectangle((x, 18, x + 1, 19), fill=(240, 248, 255))     # square pixel lamps
    for x in range(3, 9, 2): d.rectangle((x, 17, x + 1, 18), fill=(224, 48, 58))
    g = int(80 + 175 * port); d.rectangle((6, 21, 10, 24), fill=(40, min(255, g), min(255, g)))   # charge port (rear quarter)
    for cx in (21, 75):
        d.pieslice((cx - 11, 24, cx + 11, 46), 180, 360, fill=(14, 14, 20))
        d.ellipse((cx - 8, 27, cx + 8, 43), fill=(26, 27, 32)); d.ellipse((cx - 5, 30, cx + 5, 40), fill=(170, 176, 188))
        for k in range(4):
            a = math.radians(spin + k * 90); d.line([(cx, 35), (cx + 4 * math.cos(a), 35 + 4 * math.sin(a))], fill=(80, 84, 96))
    return outline(img)


@lru_cache(None)
def charger(screen=0, lab=True):
    """Tall fast charger (30x86): teal-trimmed pillar, screen showing a bolt, holster, 350 KW plate."""
    img = Image.new('RGBA', (32, 88), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 0, 29, 83), fill=(220, 224, 232)); d.rectangle((2, 0, 29, 5), fill=TEAL); d.line([(3, 6), (3, 82)], fill=(250, 250, 252))
    d.rectangle((6, 12, 25, 32), fill=(20, 21, 28)); d.rectangle((8, 14, 23, 30), fill=(30, 60, 70) if not screen else (40, 120, 110))
    d.polygon([(17, 15), (11, 23), (15, 23), (13, 29), (20, 20), (16, 20), (18, 15)], fill=(255, 210, 63) if screen else (90, 100, 90))
    d.rectangle((20, 40, 28, 52), fill=(60, 64, 76))
    d.rectangle((0, 83, 31, 87), fill=(90, 94, 106))
    img = outline(img)
    if lab:
        from pixanim.grid import Grid, text_width
        g = Grid(text_width('350') + 2, 7); g.rect(0, 0, text_width('350') + 1, 6, '#1a1a2e'); g.text(1, 1, '350', '#ffd23f')
        t = g.image(outline=False); img.paste(t, (16 - t.width // 2, 60), t)
    return img


@lru_cache(None)
def wallbox():
    """Small slow wallbox (22x26) on a post, coiled cable."""
    img = Image.new('RGBA', (24, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((10, 26, 13, 59), fill=(120, 126, 138))
    d.rounded_rectangle((1, 2, 22, 26), 3, fill=(200, 204, 214)); d.rectangle((6, 8, 17, 14), fill=(40, 60, 50)); d.rectangle((8, 10, 11, 12), fill=(60, 200, 90))
    for k in range(3): d.ellipse((4 + k, 16 + k * 2, 19 - k, 24 + k), outline=(40, 42, 52))
    return outline(img)


# ================================================================== shot 1: hook, the battery fills
FILL0, FILL1 = 0.15, 1.15
def level(t): return 0.1 + 0.7 * io(prog(t, FILL0, FILL1 - FILL0))
CAM1 = Camera(W, H, [(-1.0, (540, 980, 1.3)), (0.0, (540, 980, 1.3)), (FILL1, (540, 960, 1.12), 'io'), (3.0, (540, 960, 1.18), 'io')],
              kicks=[(FILL0, 0.1, 540, 1000), (FILL1, 0.2, 540, 900), (2.21, 0.14, 820, 760)], shakes=[(0.2, 0.9, 5)])


def shot_battery(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    lv = level(t)
    blit(fg, up(battery(round(lv * 20) / 20), 11), 420, 1240, 1, 1 + 0.03 * math.sin(t * 12) * (t < FILL1), 0)
    if FILL0 <= t < FILL1 + 0.3:
        for k in range(5):
            a = t * 9 + k * 1.3
            blit(fg, up(bolt(), 7), 420 + 260 * math.cos(a), 900 + 300 * math.sin(a * 0.7), 1, 1, 15 * math.sin(a), anchor='center')
    if t >= FILL1:
        fx.burst(fg, t, FILL1, 420, 900, (60, 200, 90), n=18, seed=1); fx.ring(fg, t, FILL1, 420, 900, (60, 200, 90), r1=520)
        fx.gsparkles(fg, t, 420, 900, 600, 600, n=8, seed=2)
    pct = int(round(lv * 100 / 5) * 5)
    blit(fg, fx.big('badge', f'{pct}%', '#7fe3a0' if pct >= 80 else '#ffffff', '#1a1a2e', '#3cc85a' if pct >= 80 else '#d6d9e2', s=10),
         800, 1060, popin(t, 0.05), popin(t, 0.05), 4, anchor='center')
    if t >= 2.21:
        k = popin(t, 2.21, 0.25)
        blit(fg, fx.big('badge', '18 MIN', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 800, 820, k, k, -4 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 2.21, 800, 820, GLOW, n=14, seed=3)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, GREAT - 0.1, '10-80% in', WHITE, 480, 130, -3)
    title(cv, t, 0.3, GREAT - 0.1, '18 minutes', YEL, 610, 140, 2)
    title(cv, t, GREAT, THATS - 0.05, 'Sounds great.', GRN, 520, 120, -2)
    to = WARP(t)
    if THATS <= t < BODY_END:
        title(cv, to, 7.95, 11.0, '350 kW charger', RED, 480, 104, 2)
        title(cv, to, 11.3, 14.15, 'only as fast as', GRN, 480, 96, -2)
        title(cv, to, 11.5, 14.15, 'the charger', GRN, 600, 110, 2)
    title(cv, t, BODY_END + 0.05, END_T - 0.1, 'Slowest charger', WHITE, 480, 112, -2)
    title(cv, t, BODY_END + 0.3, END_T - 0.1, "you've waited at?", RED, 610, 104, 2)


# ================================================================== shot 2: the car, 800 volts
CARX = 500
def carx2(t): return lerp(-500, CARX, oc(prog(t, 3.05, 0.6)))
P2 = Presenter([
    (3.0, dict(path=Track([(3.0, (1300, 300)), (3.4, (930, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (3.4, dict(ground=GROUND, squash=True, arms='point', point=(CARX, GROUND - 260), look=(CARX, GROUND - 260), expr='smile', face=None)),
    (5.67, dict(arms='shock', point=None, expr='wow', squash=True)),
    (6.48, dict(arms='thumb', look=None, look_camera=True, expr='grin')),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(3.0, (540, 940, 1.08)), (3.88, (540, 920, 1.12), 'io'), (5.67, (540, 860, 1.16), 'io'), (7.3, (540, 880, 1.18))],
              kicks=[(3.65, 0.12, CARX, 1000), (4.18, 0.08, 540, 900), (5.67, 0.2, 540, 620), (6.48, 0.12, CARX, 1000)], shakes=[(5.67, 0.4, 10)])


def shot_car(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = carx2(t)
    blit(fg, up(hatch(int(x * 0.8) % 360 // 15 * 15, 0.5 + 0.5 * math.sin(t * 6)), 7), x, GROUND)
    fx.contact_shadow(fg, x, GROUND, 600, s=7)
    if 3.65 <= t < 4.3: fx.dust(fg, t, 3.65, x - 280, GROUND - 10, n=10, seed=10, dirx=-1)
    if t >= 5.67:
        d = ImageDraw.Draw(fg); r = fx.rng(int(t * 20))
        for k in range(3):                                   # electric arcs along the floor pack
            pts = [(x - 230 + i * 36, GROUND - 70 + r.uniform(-20, 20)) for i in range(14)]
            d.line(pts, fill=(140, 220, 255, 230), width=5)
        k = fx.slam(t, 5.67) * popin(t, 5.67, 0.2)
        blit(fg, fx.big('badge', '800 V', '#7fd4ff', '#1a1a2e', '#3c9ad8', s=13), 540, 620, k, k, -3 + 2 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 5.67, 540, 620, (120, 200, 255), n=18, seed=11); fx.sparkles(fg, t, 540, 620, 700, 260, n=7, seed=12)
    dg.label(fg, t, 6.48, 'SYSTEM', (x, GROUND - 90), (260, 840), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the 350 kW charger
CHX, CAR3 = 230, 700
PLUG = 7.65
def plug_xy(t):
    u = oc(prog(t, 7.35, PLUG - 7.35))
    return lerp(CHX + 70, CAR3 - 260, u), lerp(GROUND - 420, GROUND - 130, u) - 120 * math.sin(math.pi * u)
CAM3 = Camera(W, H, [(7.3, (540, 920, 1.06)), (PLUG, (480, 940, 1.14), 'io'), (8.84, (540, 920, 1.08), 'io'), (11.1, (540, 920, 1.12), 'io')],
              kicks=[(PLUG, 0.18, CAR3 - 260, GROUND - 130), (7.95, 0.14, CHX, 700), (9.27, 0.12, CHX, 900), (10.4, 0.14, 540, 640)], shakes=[(PLUG, 0.25, 10)])


def shot_charger(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    blit(fg, up(hatch(0, 1.0 if t >= PLUG else 0.3), 6), CAR3, GROUND)
    fx.contact_shadow(fg, CAR3, GROUND, 520, s=6)
    blit(fg, up(charger(int(t >= PLUG), True), 7), CHX, GROUND)
    px, py = plug_xy(t); d = ImageDraw.Draw(fg)
    sx, sy = CHX + 80, GROUND - 260
    pts = [(lerp(sx, px, i / 20), lerp(sy, py, i / 20) + 120 * math.sin(math.pi * i / 20)) for i in range(21)]
    d.line(pts, fill=(26, 26, 46, 255), width=22); d.line(pts, fill=(60, 64, 76, 255), width=14)
    d.rectangle((px - 26, py - 20, px + 26, py + 20), fill=(26, 26, 46, 255)); d.rectangle((px - 20, py - 14, px + 20, py + 14), fill=(220, 224, 232, 255))
    if t >= PLUG:
        fx.burst(fg, t, PLUG, px, py, GLOW, n=12, r0=40, r1=200, seed=20)
        for k in range(4):                                 # current pulses run down the cable
            u = ((t - PLUG) * 1.6 + k / 4) % 1; i = int(u * 20)
            d.ellipse((pts[i][0] - 14, pts[i][1] - 14, pts[i][0] + 14, pts[i][1] + 14), fill=(255, 230, 90, 255))
    if t >= 7.95:
        k = fx.slam(t, 7.95) * popin(t, 7.95, 0.2)
        blit(fg, fx.big('badge', '350 KW', '#e0303a', '#ffffff', '#b8222c', s=11), 620, 700, k, k, 3 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 7.95, 620, 700, RED, n=16, seed=21)
    if t >= 10.22:
        k = popin(t, 10.22, 0.25)
        blit(fg, up(battery(min(0.8, 0.1 + 0.7 * prog(t, 10.22, 0.6))), 5), 900, 860, k, k, 0, anchor='center')
        fx.gsparkles(fg, t, 900, 860, 260, 300, n=6, seed=22)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


P3 = Presenter([
    (8.7, dict(path=Track([(8.7, (1300, 300)), (9.1, (960, GROUND - 330), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (9.1, dict(ground=GROUND - 330, squash=True, arms='point', point=(CHX, GROUND - 500), look=(CHX, GROUND - 500), expr='smirk', face=None)),
], words=WORDS, base_size=6)


# ================================================================== shot 4: slow vs fast
SLOW, FAST = 300, 760
CAM4 = Camera(W, H, [(11.1, (540, 960, 1.04)), (12.23, (500, 980, 1.1), 'io'), (13.38, (580, 960, 1.1), 'io'), (14.25, (540, 960, 1.08), 'io')],
              kicks=[(11.3, 0.1, FAST, 900), (12.74, 0.2, SLOW, 900), (13.38, 0.2, FAST, 900)], shakes=[(12.74, 0.25, 12)])


def shot_compare(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k1 = popin(t, 11.3, 0.3); k2 = popin(t, 11.15, 0.3)
    blit(fg, up(charger(1, True), 6), FAST, GROUND, k1, k1)
    blit(fg, up(wallbox(), 7), SLOW, GROUND, k2, k2)
    if t >= 11.67: fx.rays(fg, t, 11.67, FAST, GROUND - 300, GLOW, hold=True, r=360, n=8)
    blit(fg, up(battery(min(0.8, 0.1 + 0.7 * prog(t, 11.7, 1.0))), 3), FAST + 170, GROUND, k1, k1, 0)
    blit(fg, up(battery(0.1 + 0.15 * prog(t, 11.7, 3.0)), 3), SLOW + 150, GROUND, k2, k2, 0)
    if t >= 12.74:
        k = fx.slam(t, 12.74) * popin(t, 12.74, 0.2)
        blit(fg, fx.big('xmark', s=13), SLOW, GROUND - 260, k, k, -6, anchor='center')
        fx.burst(fg, t, 12.74, SLOW, GROUND - 260, RED, n=14, seed=30)
    if t >= 13.38:
        k = fx.slam(t, 13.38) * popin(t, 13.38, 0.2)
        blit(fg, fx.big('check', s=13), FAST, GROUND - 300, k, k, 6, anchor='center')
        fx.burst(fg, t, 13.38, FAST, GROUND - 300, (60, 200, 90), n=16, seed=31); fx.gsparkles(fg, t, FAST, GROUND - 300, 400, 400, n=8, seed=32)
    if t >= 12.23:
        k = popin(t, 12.23, 0.25)
        blit(fg, fx.big('tag', 'SLOW', '#fff6e0', '#d6303a', s=8), SLOW, GROUND - 500, k, k, -5, anchor='center')
        blit(fg, fx.big('tag', 'FAST', '#fff6e0', '#1a1a2e', s=8), FAST, GROUND - 470, k, k, 5, anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== new read: hook, body on the first read's timing, question
BODY = [p for p in kit.word_pairs(NEW, WORDS) if p[0] < BODY_END - 0.3]
ANCH = [(0.0, -0.1)] + BODY + [(BODY_END - 0.01, 14.2), (BODY_END, 12.3), (END_T + 0.2, 14.2)]
WARP, N = kit.warp(ANCH), kit.unwarp(BODY)
shot_teaser, TEASE_CUES = kit.teaser(END_T, NEW)

# ================================================================== shots + transitions
SHOTS = [(-1.0, kit.retime(shot_battery, WARP)), (THATS - 0.15, kit.retime(shot_car, WARP)), (N(7.3), kit.retime(shot_charger, WARP)),
         (N(11.1), kit.retime(shot_compare, WARP)), (BODY_END, kit.retime(shot_compare, WARP)), (END_T, shot_teaser)]
TRANS = {1: (THATS - 0.15, THATS + 0.05, 'whip', dict(dx=1)), 2: (N(7.3), N(7.3) + 0.2, 'push', None), 3: (N(11.1), N(11.1) + 0.2, 'iris', (560, 660)),
         4: (BODY_END, BODY_END + 0.2, 'whip', dict(dx=-1)), 5: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'eighty': GRN, 'eighteen': YEL, 'great.': GRN, 'hyundai': YEL, '800-volt': YEL, '350': RED, 'speed.': YEL, 'fast': GRN, 'charger.': GRN,
          'slowest': RED}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.6), (FILL0, 'whoosh', 0.8), (FILL0 + 0.3, 'click', 0.4), (FILL0 + 0.6, 'click', 0.4),
    (FILL1, 'ding', 0.9), (FILL1 + 0.02, 'sparkle', 0.7), (2.21, 'stamp', 0.7),
    (3.1, 'vroom', 0.4), (3.65, 'thump', 0.5), (3.95, 'pop', 0.5), (5.67, 'boom', 0.5), (5.69, 'stamp', 0.7), (5.7, 'sparkle', 0.7), (6.48, 'pop', 0.6),
    (7.35, 'whoosh', 0.5), (PLUG, 'click', 1.0), (PLUG + 0.02, 'thump', 0.6), (7.95, 'stamp', 0.8), (9.1, 'thump', 0.4), (9.27, 'whoosh', 0.4),
    (10.22, 'pop', 0.6), (10.6, 'ding', 0.6),
    (11.15, 'pop', 0.5), (11.3, 'pop', 0.6), (11.67, 'sparkle', 0.6), (12.23, 'pop', 0.6), (12.74, 'buzzer', 0.7), (13.38, 'ding', 0.9),
    (13.4, 'sparkle', 0.7),
]
CUES = kit.warp_cues(CUES, ANCH, END_T) + [(GREAT, 'ding', 0.5)] + TEASE_CUES

kit.setup(HERE, NEW, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True,
          end=('car stuff, explained', 'tell me in the comments'))

if __name__ == '__main__':
    kit.main()
