"""Renders 'Lucid, 749 miles': a 2025 single-charge drive from St Moritz to Munich, helped by hand-picked drivers,
cool weather and a long downhill; the official EPA rating is 512 miles.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, rev counter, mixer). Word times
come from align.py -> words.json (aligned on out/lucid-749-miles/vo_final.wav, the audio that ships). The car is a
generic pixel saloon with no badges or lettering; the real car appears only in the framed Commons photo.
Shots:
  1 odo      0.00  dashboard close-up: the trip counter runs past 700 to 749 while the battery drains; '749 miles, one charge.'
  2 car      3.30  garage: silver saloon; the framed real photo slides in; 2025 badge
  3 route    5.55  pixel map of the Alps: the route draws itself from St Moritz to Munich; 'St Moritz to Munich'
  4 helped   8.90  a long downhill under falling snow: HAND-PICKED, COOL, DOWNHILL tags pop in turn
  5 epa     12.50  749 next to a 512 EPA label; 'OFFICIAL' stamp; '512 official'
  6 teaser  15.45  shared NEXT EPISODE ending
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
from pixanim.dash import Dashboard
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline
from pixanim.autos import ev, battery, ptext

WORDS = kit.load_words(HERE)
DUR, END_T = 17.2, 15.49
SPR = 6                                                # ev sprite scale in the garage


# ================================================================== shot 1: hook, the trip counter
DASH = Dashboard()
def miles(t): return int(round(749 * io(prog(t, 0.1, 2.95))))
CAM1 = Camera(W, H, [(-1.0, (700, 900, 1.3)), (0.0, (700, 900, 1.3)), (2.0, (760, 940, 1.4), 'io'), (3.3, (720, 940, 1.36), 'io')],
              kicks=[(0.1, 0.1, 790, 985), (2.98, 0.22, 700, 1110)], shakes=[(2.98, 0.3, 12)])


def shot_odo(t):
    m = miles(t)
    img = DASH.frame(t, rpm_deg=210 + 3 * math.sin(t * 9), speed_deg=150 + 4 * math.sin(t * 2), lcd=f'{m}')
    fg = layer()
    lvl = 1 - 0.92 * m / 749
    k = popin(t, 0.15, 0.25)
    blit(fg, up(battery(round(lvl * 10) / 10), 5), 470, 1060, k, k, -4, anchor='center')
    k2 = popin(t, 0.25, 0.25) * popout(t, 2.9, 0.12)
    blit(fg, fx.big('badge', 'MILES', '#ffffff', '#1a1a2e', '#d6d9e2', s=6), 790, 1050, k2, k2, 3, anchor='center')
    if m >= 700:
        fx.burst(fg, t, 2.62, 790, 985, GLOW, n=10, seed=2)
    if t >= 2.98:
        kk = fx.slam(t, 2.98) * popin(t, 2.98, 0.2)
        blit(fg, fx.big('badge', '749 MI', '#ffd23f', '#1a1a2e', '#e8b923', s=10), 700, 1110, kk, kk, -3, anchor='center')
        fx.ring(fg, t, 2.98, 700, 1110, GLOW, r1=420); fx.sparkles(fg, t, 700, 1110, 600, 160, n=8, seed=3)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, 0.05, 2.7, '749 miles,', YEL, 470, 130, -3)
    title(cv, t, 0.3, 2.7, 'one charge.', YEL, 620, 130, 2)
    title(cv, t, 6.4, 8.8, 'St Moritz to Munich', GRN, 470, 110, -2)
    title(cv, t, 13.98, 15.3, '512 official', RED, 470, 120, 2)
    x = lerp(1500, 560, oc(prog(t, 3.45, 0.45)))                              # the photo slides in from the right
    photo(cv, t, 3.45, 5.45, 'lucid', x, 640, 860, rot=3, label='THE REAL CAR', hq=True)


# ================================================================== shot 2: the car, 2025
CAR_X = 560
P2 = Presenter([
    (3.25, dict(path=Track([(3.25, (-200, 500)), (3.65, (160, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (3.65, dict(ground=GROUND, squash=True, arms='point', point=(560, 640), look=(560, 640), expr='smile', face=None)),
    (4.82, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin')),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(3.3, (540, 960, 1.1)), (5.55, (560, 980, 1.18), 'io')],
              kicks=[(3.5, 0.1, 560, 640), (4.82, 0.12, 640, 1100)], shakes=[])


def shot_car(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 640, GROUND, 560, s=SPR)
    blit(fg, up(ev('air', 0, True), SPR), 640, GROUND)
    k = popin(t, 3.4, 0.25)
    blit(fg, fx.big('tag', '2025', '#fff6e0', '#1a1a2e', s=9), 820, 1080, k, k, -6 + 2 * math.sin(t * 4), anchor='center')
    if t >= 4.82: fx.gsparkles(fg, t, 640, GROUND - 120, 600, 200, n=6, seed=12)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the route draws itself
MS = 6                                                  # map pixel scale
MW, MH = 160, 200
ROUTE = [(40, 160), (50, 150), (46, 138), (58, 128), (70, 120), (74, 106), (88, 98), (94, 84), (104, 76), (110, 62), (118, 52), (124, 40)]
ST_MORITZ, MUNICH = ROUTE[0], ROUTE[-1]
R0, R1 = 6.36, 8.17                                     # 'St' .. 'Germany.'


@lru_cache(None)
def map_base():
    """Pixel relief map (160x200): lowland at the top, the Alps below, lakes, a dotted border."""
    img = Image.new('RGBA', (MW, MH), (54, 78, 64, 255)); d = ImageDraw.Draw(img)
    import numpy as np
    rng = np.random.default_rng(7)
    for _ in range(900):
        x, y = rng.integers(0, MW), rng.integers(0, MH)
        d.point((x, y), fill=(62, 90, 72) if y < 90 else (70, 84, 80))
    for _ in range(60):                                                         # mountains, denser to the south
        x, y = rng.integers(0, MW), rng.integers(95, MH)
        h = rng.integers(6, 14)
        d.polygon([(x - h, y), (x, y - h), (x + h, y)], fill=(120, 124, 136))
        d.polygon([(x - h // 3, y - h + h // 3), (x, y - h), (x + h // 3, y - h + h // 3)], fill=(240, 244, 250))
    d.ellipse((96, 66, 110, 74), fill=(60, 120, 190)); d.ellipse((20, 112, 36, 118), fill=(60, 120, 190))   # lakes
    for x in range(0, MW, 4): d.point((x, 92 + int(4 * math.sin(x / 9))), fill=(230, 230, 236))           # border
    return img


@lru_cache(None)
def map_frame(u):
    img = map_base().copy(); d = ImageDraw.Draw(img)
    seg = [(a, b) for a, b in zip(ROUTE, ROUTE[1:])]
    total = sum(math.dist(a, b) for a, b in seg); left = total * u
    pts = [ROUTE[0]]
    for a, b in seg:
        L = math.dist(a, b)
        if left >= L: pts.append(b); left -= L
        else:
            pts.append((a[0] + (b[0] - a[0]) * left / L, a[1] + (b[1] - a[1]) * left / L)); break
    if len(pts) > 1:
        d.line(pts, fill=(26, 26, 46), width=5); d.line(pts, fill=(255, 210, 63), width=3)
    for (x, y), on in ((ST_MORITZ, True), (MUNICH, u >= 1)):
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(26, 26, 46)); d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(224, 48, 58) if on else (150, 150, 160))
    return up(img, MS), pts[-1]


MX0, MY0 = W / 2 - MW * MS / 2, 380
CAM3 = Camera(W, H, [(5.55, (540, 960, 1.04)), (R0, (480, 1150, 1.14), 'io'), (R1, (640, 760, 1.14), 'io'), (8.9, (600, 800, 1.1), 'io')],
              kicks=[(6.61, 0.1, MX0 + ST_MORITZ[0] * MS, MY0 + ST_MORITZ[1] * MS), (7.73, 0.14, MX0 + MUNICH[0] * MS, MY0 + MUNICH[1] * MS)])


def shot_route(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    u = round(io(prog(t, R0, R1 - R0)) * 90) / 90
    m, tip = map_frame(u)
    k = popin(t, 5.6, 0.3)
    blit(fg, m, W / 2, MY0 + MH * MS / 2, k, k, 0, anchor='center')
    ox, oy = MX0, MY0
    if u > 0 and t < R1 + 0.2:
        blit(fg, up(ev('air', int(t * 400) % 360 // 15 * 15, True), 2), ox + tip[0] * MS, oy + tip[1] * MS + 6)
    sx, sy = ox + ST_MORITZ[0] * MS, oy + ST_MORITZ[1] * MS
    mx, my = ox + MUNICH[0] * MS, oy + MUNICH[1] * MS
    dg.label(fg, t, 6.61, 'ST MORITZ', (sx, sy), (sx + 140, sy + 160), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    dg.label(fg, t, 7.73, 'MUNICH', (mx, my), (mx - 160, my - 130), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    for txt, (x, y), t0 in (('SWITZERLAND', (ox + 110 * MS, oy + 150 * MS), 6.98), ('GERMANY', (ox + 40 * MS, oy + 50 * MS), 8.17)):
        if t >= t0:
            kk = popin(t, t0, 0.25); blit(fg, up(ptext(txt, '#ffffff', True), 5), x, y, kk, kk, 0, anchor='center')
    if t >= R1: fx.burst(fg, t, R1, mx, my, GLOW, n=14, seed=31); fx.sparkles(fg, t, mx, my, 300, 200, n=6, seed=32)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: what helped
SLOPE = lambda x: 760 + 0.42 * x                       # road surface y at screen x (falls to the right)
def car_x4(t): return lerp(120, 1240, io(prog(t, 11.42, 1.0))) if t >= 11.42 else 120 + 30 * math.sin(t * 2)
HELP = (('HAND-PICKED', 8.98, (420, 470), -4), ('COOL WEATHER', 10.11, (650, 640), 3), ('DOWNHILL', 11.42, (560, 1220), -3))
P4 = Presenter([
    (8.85, dict(path=Track([(8.85, (1300, 400)), (9.25, (880, 1180), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (9.25, dict(ground=1180, squash=True, arms='point', point=(330, 470), look=(330, 470), expr='smile', face=None)),
    (10.11, dict(arms='shrug', point=None, look=(720, 620), expr='talk')),
    (11.42, dict(arms='point', point=(600, 1000), look=(600, 1000), expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(8.9, (540, 960, 1.08)), (11.4, (540, 960, 1.12), 'io'), (12.5, (640, 1060, 1.16), 'io')],
              kicks=[(8.98, 0.1, 330, 470), (10.11, 0.1, 720, 620), (11.42, 0.14, 420, 1000)])


@lru_cache(None)
def hill():
    img = Image.new('RGBA', (W // 3, H // 3), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (W // 3, 0), (W // 3, H // 3), (0, H // 3)], fill=(28, 34, 52))                    # night sky
    for i, (x, h) in enumerate(((40, 120), (150, 160), (270, 110), (330, 140))):                          # far peaks
        d.polygon([(x - h, 330), (x, 330 - h), (x + h, 330)], fill=(60, 66, 84))
        d.polygon([(x - h // 4, 330 - h + h // 4), (x, 330 - h), (x + h // 4, 330 - h + h // 4)], fill=(220, 226, 236))
    pts = [(0, SLOPE(0) / 3), (W // 3, SLOPE(W) / 3), (W // 3, H // 3), (0, H // 3)]
    d.polygon(pts, fill=(52, 56, 66)); d.line(pts[:2], fill=(120, 126, 138), width=2)
    for x in range(0, W // 3, 12): d.line([(x, SLOPE(x * 3) / 3 + 6), (x + 5, SLOPE(x * 3 + 15) / 3 + 6)], fill=(240, 210, 80))
    d.polygon([(0, SLOPE(0) / 3 + 10), (W // 3, SLOPE(W) / 3 + 10), (W // 3, H // 3), (0, H // 3)], fill=(150, 160, 182))   # snow bank
    for x in range(0, W // 3, 7): d.line([(x, SLOPE(x * 3) / 3 + 11), (x + 4, SLOPE(x * 3 + 12) / 3 + 11)], fill=(214, 222, 236))
    return up(img, 3)


def shot_helped(t):
    img = Image.new('RGBA', (W, H)); img.paste(hill()); fg = layer()
    fx.flakes(fg, t, 10.11, 720, 300, n=18, seed=41, spread=900, life=2.4, rise=-900)
    x = car_x4(t)
    car = up(ev('air', int(x * 0.6) % 360 // 15 * 15, True), 3).rotate(-23, resample=Image.NEAREST, expand=True)
    blit(fg, car, x, SLOPE(x) + 66, anchor='bottom')
    if t >= 11.42: fx.speed_lines(fg, 0.6 * (1 - prog(t, 12.1, 0.4)), int(t * 12) % 5, col=(220, 224, 236))
    for txt, t0, (bx, by), r in HELP:
        if t < t0: continue
        k = popin(t, t0, 0.25)
        blit(fg, fx.big('badge', txt, '#7fe3a0', '#1a1a2e', '#3cc85a', s=8), bx, by, k, k, r + 2 * math.sin(t * 4), anchor='center')
        fx.burst(fg, t, t0, bx, by, (60, 200, 90), n=10, r0=80, r1=260, seed=int(t0 * 10))
    P4.draw(fg, t)
    img.alpha_composite(fg)
    return CAM4.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 5: 512 official
P5 = Presenter([
    (12.45, dict(path=Track([(12.45, (-200, 500)), (12.85, (170, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (12.85, dict(ground=GROUND, squash=True, arms='point', point=(540, 1000), look=(540, 1000), expr='smile', face=None)),
    (13.98, dict(arms='shrug', point=None, look=None, look_camera=True, expr='smirk', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(12.5, (540, 900, 1.1)), (13.98, (600, 920, 1.18), 'io'), (15.5, (600, 920, 1.2))],
              kicks=[(12.6, 0.1, 540, 700), (13.98, 0.2, 760, 980), (14.68, 0.1, 760, 980)], shakes=[(13.98, 0.25, 10)])


def shot_epa(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 12.6, 0.25)
    blit(fg, fx.big('badge', '749 MI', '#ffd23f', '#1a1a2e', '#e8b923', s=12), 540, 720, k, k, -3 + 2 * math.sin(t * 3), anchor='center')
    dg.label(fg, t, 12.69, 'ONE DRIVE', (540, 790), (400, 880), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=13.9)
    if t >= 13.98:
        kk = fx.slam(t, 13.98) * popin(t, 13.98, 0.2)
        blit(fg, fx.big('badge', '512 EPA', '#ffffff', '#1a1a2e', '#d6d9e2', s=11), 760, 980, kk, kk, 4, anchor='center')
        fx.burst(fg, t, 13.98, 760, 980, RED, n=16, seed=51)
    if t >= 14.68: fx.stamp_at(fg, t, 14.68, 'OFFICIAL', 700, 1140, rot=-8, s=8)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(15.45, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_odo), (3.3, shot_car), (5.55, shot_route), (8.9, shot_helped), (12.5, shot_epa), (15.45, shot_teaser)]
TRANS = {1: (3.3, 3.5, 'whip', dict(dx=1)), 2: (5.55, 5.75, 'iris', (540, 960)), 3: (8.9, 9.1, 'push', None),
         4: (12.5, 12.7, 'whip', dict(dx=0, dy=1)), 5: (15.45, 15.65, 'whip', dict(dx=1))}
KEYCOL = {'2025': YEL, 'lucid': YEL, 'grand': YEL, '749': YEL, 'single': GRN, 'route': YEL, 'moritz': GRN, 'switzerland': GRN, 'munich': GRN, 'long': YEL,
          'hand-picked': YEL, 'cool': GRN, 'downhill': YEL, 'epa': RED, 'rating': YEL, '512': RED, 'follow': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.6), (0.3, 'pop', 0.5)] + [(0.15 + k * 0.29, 'click', 0.45) for k in range(9)] + [
    (2.62, 'ding', 0.6), (2.98, 'stamp', 0.9), (3.0, 'sparkle', 0.7),
    (3.45, 'whoosh', 0.6), (3.4, 'pop', 0.6), (3.65, 'thump', 0.4), (4.82, 'ding', 0.6), (4.84, 'sparkle', 0.5),
    (5.6, 'pop', 0.5), (R0, 'whoosh', 0.4), (6.61, 'pop', 0.7), (6.98, 'pop', 0.5), (7.73, 'pop', 0.7), (R1, 'ding', 0.8), (R1 + 0.02, 'sparkle', 0.7),
    (8.98, 'pop', 0.7), (9.25, 'thump', 0.4), (10.11, 'pop', 0.7), (10.13, 'sparkle', 0.5), (11.42, 'pop', 0.7), (11.45, 'whoosh', 0.8),
    (12.6, 'pop', 0.6), (12.85, 'thump', 0.4), (12.69, 'click', 0.4), (13.98, 'stamp', 0.8), (14.0, 'buzzer', 0.4), (14.68, 'stamp', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
