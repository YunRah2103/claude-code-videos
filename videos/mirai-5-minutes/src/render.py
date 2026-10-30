"""Renders 'Mirai, 5 minutes': fills with hydrogen in about 5 minutes, a claimed 402 miles, 59 US stations in 2023.

Template: videos/plaid-two-seconds (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json; the voiceover is out/mirai-5-minutes/voiceover.wav (clip 3 of out/voiceover/full_voiceover.wav). The
supplied read ends at 'California' (no 'Follow' line), so the end card shows it. The 402-mile range is Toyota's claim
(CLAIMED tag). The map dots are illustrative: 59 dots, most of them in California's two metro clusters, a few elsewhere.
Shots:
  1 pump     0.00  hook: a pixel H2 pump fills a tank while a timer runs to 5:00, '5 minutes'
  2 photo    3.85  garage: the pump stays left, the real Mirai photo pops in beside it, CLAIMED, 402 MILES
  3 map      7.25  a pixel US map: 2023 tag, 59 station dots pop in mostly over California, '59 stations'
  4 teaser  13.15  shared NEXT EPISODE ending ('Follow for the next one.')
"""
import math, os, sys
from functools import lru_cache
import numpy as np
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

WORDS = kit.load_words(HERE)
DUR = 17.0
END_T = 13.15
def ws(i): return WORDS[i]['s']


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def pump(lcd=0, nozzle_in=True):
    """Hydrogen pump (30x56): tall cabinet, LCD with `lcd` lit bars, H2 sign, hose and nozzle."""
    img = Image.new('RGBA', (40, 56), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 4, 27, 55), fill=(232, 236, 242)); d.rectangle((2, 4, 6, 55), fill=(200, 206, 216))
    d.rectangle((0, 0, 29, 6), fill=(60, 140, 220)); d.rectangle((0, 6, 29, 7), fill=(40, 100, 170))
    d.rectangle((6, 11, 23, 21), fill=(26, 26, 46))
    for k in range(lcd): d.rectangle((8 + k * 3, 14, 9 + k * 3, 18), fill=(90, 220, 120))
    d.rectangle((9, 25, 20, 34), fill=(60, 140, 220))                        # H2 sign panel
    d.rectangle((11, 27, 12, 32), fill=(255, 255, 255)); d.rectangle((15, 27, 16, 32), fill=(255, 255, 255)); d.rectangle((12, 29, 15, 30), fill=(255, 255, 255))
    d.rectangle((17, 31, 19, 32), fill=(255, 255, 255))
    d.rectangle((2, 50, 27, 55), fill=(120, 126, 138))
    d.line([(27, 38), (33, 40), (36, 46)], fill=(40, 42, 52), width=2)       # hose
    if nozzle_in: d.rectangle((25, 36, 30, 41), fill=(60, 64, 78))
    return outline(img)


@lru_cache(None)
def tank(level=0.0):
    """H2 tank (44x20): a capsule that fills from the left with glowing blue gas, `level` 0..1."""
    img = Image.new('RGBA', (44, 20), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 43, 19), 9, fill=(176, 182, 192))
    d.rounded_rectangle((2, 2, 41, 17), 7, fill=(40, 44, 58))
    if level > 0:
        x1 = 2 + round(39 * level)
        m = Image.new('L', (44, 20), 0); ImageDraw.Draw(m).rounded_rectangle((2, 2, 41, 17), 7, fill=255)
        g = Image.new('RGBA', (44, 20), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        gd.rectangle((2, 2, x1, 17), fill=(80, 170, 255)); gd.rectangle((2, 4, x1, 6), fill=(170, 220, 255))
        img.paste(g, (0, 0), Image.composite(g.getchannel('A'), Image.new('L', (44, 20), 0), m))
    d.rectangle((43, 8, 43, 11), fill=(120, 126, 138))
    return outline(img)


# ------------------------------------------------------------------ US map (rough contiguous outline, lon/lat -> grid)
OUT = [(-124.7, 48.4), (-123, 49), (-95, 49), (-94.8, 49.4), (-89.5, 48), (-84.8, 46.5), (-83.5, 46.1), (-82.4, 43), (-79, 43.3),
       (-76.5, 44), (-75, 45), (-71.5, 45), (-70, 46.7), (-67.8, 47), (-67, 44.8), (-70.2, 43.6), (-70.6, 42), (-70, 41.7), (-71.9, 41.3),
       (-73.9, 40.6), (-74, 39.6), (-75.5, 38.5), (-76, 37), (-75.6, 35.3), (-76.5, 34.7), (-78.6, 33.9), (-80.9, 32), (-81.5, 30.5),
       (-80.2, 27), (-80.1, 25.4), (-81.2, 25.2), (-82.7, 27.5), (-82.8, 29.2), (-84.3, 30), (-86.5, 30.4), (-89.6, 30.2), (-89.4, 29),
       (-91.5, 29.5), (-93.8, 29.7), (-95, 29.2), (-97.2, 27.6), (-97.4, 25.9), (-99.1, 26.4), (-101.4, 29.8), (-103.3, 29),
       (-104.5, 29.6), (-106.5, 31.8), (-108.2, 31.3), (-111, 31.3), (-114.8, 32.5), (-117.1, 32.5), (-118.5, 34), (-120.6, 34.6),
       (-121.9, 36.6), (-122.5, 37.8), (-123.7, 39), (-124.2, 40.4), (-124.2, 42), (-124, 46.3)]
CA = [(-124.2, 42), (-120, 42), (-120, 39), (-114.6, 35), (-114.8, 32.5), (-117.1, 32.5), (-118.5, 34), (-120.6, 34.6), (-121.9, 36.6),
      (-122.5, 37.8), (-123.7, 39), (-124.2, 40.4)]
MW, MH = 104, 60                                       # map grid (x9 on screen)
def g(lon, lat): return ((lon + 126) * MW / 60, (50 - lat) * MH / 27)


def _stations():
    r = np.random.default_rng(7); pts = []
    for (lon, lat, n, sp) in [(-118.1, 34.0, 26, 0.6), (-122.0, 37.6, 18, 0.5), (-121.4, 38.7, 4, 0.3), (-117.1, 33.0, 3, 0.2),
                              (-119.7, 36.6, 2, 0.4)]:
        pts += [(lon + r.normal(0, sp), lat + r.normal(0, sp * 0.8)) for _ in range(n)]
    pts += [(-71.6, 42.2), (-72.9, 41.5), (-74.3, 40.7), (-84.4, 33.8), (-111.9, 33.4), (-97.4, 30.4)]   # a few elsewhere
    order = np.random.default_rng(3).permutation(len(pts))
    return [pts[i] for i in order]
ST = _stations()                                      # 59 dots


@lru_cache(None)
def usmap(ca_glow=0):
    img = Image.new('RGBA', (MW, MH), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([g(*p) for p in OUT], fill=(70, 120, 90), outline=(120, 190, 140))
    d.polygon([g(*p) for p in CA], fill=(90, 160, 110) if not ca_glow else (110, 200, 130), outline=(255, 217, 59) if ca_glow else (120, 190, 140))
    return outline(img)


# ================================================================== shot 1: hook, the pump fills the tank in 5:00
F0, F1 = 0.15, ws(9) + 0.3                            # fill runs until just after 'minutes.'
def fill(t): return clamp((t - F0) / (F1 - F0))
CAM1 = Camera(W, H, [(-1.0, (540, 900, 1.02)), (0.0, (540, 900, 1.02)), (1.6, (540, 910, 1.08), 'io'), (3.9, (540, 900, 1.12), 'io')],
              kicks=[(F0, 0.1, 300, 900), (1.6, 0.08, 720, 880), (ws(8), 0.12, 540, 600), (F1, 0.2, 720, 880)], shakes=[(F1, 0.3, 10)])


def shot_pump(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    u = fill(t)
    k = popin(t, 0.0, 0.25)
    blit(fg, up(pump(round(u * 5)), 11), 290, GROUND, k, k)
    blit(fg, up(tank(round(u * 39) / 39), 11), 760, 900 + 2 * math.sin(t * 20) * (0 < u < 1), k, k, 0, anchor='center')
    d = ImageDraw.Draw(fg)
    if 0 < u < 1:                                     # gas flowing along the hose into the tank
        for j in range(6):
            xx = 470 + ((t * 600 + j * 50) % 280)
            d.rectangle((xx, 1000 - (xx - 440) * 0.35, xx + 14, 1012 - (xx - 440) * 0.35), fill=(120, 200, 255, 220))
    sec = round(300 * u)
    kk = popin(t, F0, 0.25) * (fx.slam(t, F1, k=0.5) if t >= F1 else 1)
    blit(fg, fx.big('badge', f'{sec // 60}:{sec % 60:02d}', '#ffffff' if u < 1 else '#ffd23f', '#1a1a2e', '#d6d9e2', s=12), 760, 690, kk, kk, -3, anchor='center')
    if t >= F1:
        fx.burst(fg, t, F1, 760, 690, GLOW, n=16, seed=2); fx.ring(fg, t, F1, 760, 900, (80, 170, 255), r1=520)
        fx.stamp_at(fg, t, F1 + 0.1, 'FULL', 760, 1060, rot=-8, s=7, col='#2f9e52')
    fx.sparkles(fg, t, 760, 900, 520, 200, n=6, seed=1)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: the real car beside the pump, a claimed 402 miles
T2 = 3.85
MI = ws(17)                                           # '402'
def miles(t): return int(402 * oc(prog(t, MI, 0.7)))
P2 = Presenter([
    (T2 - 0.05, dict(path=Track([(T2 - 0.05, (1300, 300)), (T2 + 0.4, (900, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (T2 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(600, 700), look=(600, 700), expr='smile', face=None)),
    (MI + 0.7, dict(arms='thumb', point=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(T2, (540, 900, 1.08)), (ws(11), (560, 880, 1.14), 'io'), (7.3, (540, 900, 1.18), 'io')],
              kicks=[(T2 + 0.1, 0.08, 620, 680), (ws(11), 0.12, 420, 330), (MI + 0.7, 0.16, 560, 1080)], shakes=[(MI + 0.7, 0.25, 8)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    blit(fg, up(pump(5), 9), 130, GROUND)
    if t >= MI:
        k = popin(t, MI, 0.25) * (fx.slam(t, MI + 0.7, k=0.5) if t >= MI + 0.7 else 1)
        blit(fg, fx.big('badge', f'{miles(t)} MILES', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 520, 1090, k, k, 3 + 2 * math.sin(t * 5), anchor='center')
        if t >= MI + 0.7: fx.burst(fg, t, MI + 0.7, 520, 1090, GLOW, n=16, seed=21); fx.sparkles(fg, t, 520, 1090, 600, 160, n=6, seed=22)
    if t >= ws(11):
        fx.stamp_at(fg, t, ws(11), 'CLAIMED', 420, 330, rot=-8, s=8, col='#2f9e52')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: 59 stations, mostly in California
T3 = 7.25
D0 = ws(25)                                           # '59'
MX0, MY0, MS = 540 - MW * 9 // 2, 780 - MH * 9 // 2, 9
def ndots(t): return int(59 * clamp((t - D0) / 0.9))
def scr(lon, lat): x, y = g(lon, lat); return MX0 + x * MS, MY0 + y * MS
CAM3 = Camera(W, H, [(T3, (540, 860, 1.0)), (D0, (540, 860, 1.02), 'io'), (ws(31), (330, 840, 1.25), 'io'), (END_T, (330, 840, 1.28))],
              kicks=[(ws(21), 0.1, 460, 420), (D0 + 0.9, 0.14, 540, 760), (ws(31), 0.12, *scr(-119, 35.5))], shakes=[(D0 + 0.9, 0.25, 8)])


def shot_map(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, T3 + 0.05, 0.3)
    ca = int(t >= ws(31) and int(t * 6) % 2 == 0)
    blit(fg, up(usmap(ca), MS), 540, 780, k, k, 0, anchor='center')
    d = ImageDraw.Draw(fg)
    n = ndots(t)
    for i, (lon, lat) in enumerate(ST[:n]):
        x, y = scr(lon, lat); t0 = D0 + 0.9 * i / 59
        r = 6 * (1 + 0.8 * math.exp(-(t - t0) * 12))
        d.rectangle((x - r - 3, y - r - 3, x + r + 3, y + r + 3), fill=(26, 26, 46, 255))
        d.rectangle((x - r, y - r, x + r, y + r), fill=(255, 217, 59, 255))
        d.rectangle((x - r, y - r, x - r + 3, y - r + 3), fill=(255, 250, 210, 255))
    if t >= ws(21):
        kk = popin(t, ws(21), 0.25) * popout(t, ws(31))
        blit(fg, fx.big('badge', '2023' if t < D0 else f'2023: {n}', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), 460, 420, kk, kk, -3, anchor='center')
    if t >= D0 + 0.9: fx.burst(fg, t, D0 + 0.9, 540, 1150, GLOW, n=14, seed=31)
    if t >= ws(31):
        cx, cy = scr(-119.5, 36)
        fx.ring(fg, t, ws(31), cx, cy, GLOW, r1=300); fx.sparkles(fg, t, cx, cy, 260, 300, n=8, seed=32)
        dg.label(fg, t, ws(31) + 0.1, 'CALIFORNIA', (cx, cy - 40), (cx + 60, cy - 230), '#ffd23f', '#1a1a2e', '#e8b923', s=7)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)


def overlay(cv, t):
    title(cv, t, 0.05, 3.8, '5 minutes', RED, 430, 140, -3)
    kit.photo_hq(cv, t, T2 + 0.1, 7.15, 'mirai', 600, 660, 760, rot=-3, label='THE REAL CAR')
    title(cv, t, D0, 13.05, '59 stations', YEL, 1190, 116, 2)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_pump), (T2, shot_photo), (T3, shot_map), (END_T, shot_teaser)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'iris', (540, 760)), 3: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'mirai': YEL, '5': RED, 'claims': GRN, '402': RED, '2023': YEL, '59': YEL, 'us': YEL, 'california': GRN}
CUES = [(0.0, 'whoosh', 0.4), (0.05, 'pop', 0.6), (F0, 'click', 0.5)] + [(F0 + 0.3 * k, 'click', 0.35) for k in range(1, int((F1 - F0) / 0.3))] + [
        (F1, 'ding', 0.9), (F1 + 0.1, 'stamp', 0.7), (F1 + 0.12, 'sparkle', 0.6),
        (T2 + 0.1, 'pop', 0.7), (T2 + 0.4, 'thump', 0.4), (ws(11), 'stamp', 0.7), (MI, 'whoosh', 0.4)] + [
        (MI + 0.1 * k, 'click', 0.35) for k in range(7)] + [(MI + 0.7, 'ding', 0.8), (MI + 0.72, 'sparkle', 0.6),
        (T3 + 0.05, 'pop', 0.6), (ws(21), 'pop', 0.6)] + [(D0 + 0.9 * i / 12, 'pop', 0.35) for i in range(12)] + [
        (D0 + 0.9, 'stamp', 0.6), (D0 + 0.92, 'sparkle', 0.6), (ws(31), 'whoosh', 0.5), (ws(32), 'pop', 0.6), (ws(33), 'ding', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
