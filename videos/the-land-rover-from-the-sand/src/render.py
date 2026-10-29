"""Renders 'The Land Rover from the sand': a sketch in the sand, a surplus jeep, wartime aluminium, Amsterdam 1948.

Template: videos/tractors-vs-ferraris (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). Speech runs 0-17.8 s; the 'Follow' card holds to 19.6 s.
Vehicles are generic pixel redraws with no badges or lettering.
Shots:
  1 sand     0.00  a pixel finger traces a boxy 4x4 outline in the sand; 'Drawn in the sand?'
  2 farm     2.50  a farm: the surplus jeep rolls in on 'Willys Jeep'; photo card
  3 rough    5.90  close on the jeep bucking over ruts; RELIABLE check, ROUGH cross, PARTS SHORTAGE sign and wrench
  4 alloy    8.60  workbench: a steel crate gets a red X; aircraft-marked aluminium sheets slide in; a plane passes
  5 show    12.60  show stand: '30 APRIL 1948' banner drops, the sand sketch becomes the Series I on 'Series I'
  6 icon    16.00  presenter thumbs up beside it; ICON label and confetti on 'icon'
  7 teaser  18.00  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 19.6, 18.3


# ------------------------------------------------------------------ episode sprites
def _wheel(d, cx, cy, r, spin, rim, rim_sh=None):
    """Chunky off-road tyre: tread blocks that turn with `spin`, sidewall ring, painted rim with hub and nuts."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(30, 31, 36))
    for k in range(16):
        a = math.radians(k * 22.5 + spin)
        x, y = cx + (r - 0.6) * math.cos(a), cy + (r - 0.6) * math.sin(a)
        d.rectangle((x - 1, y - 1, x, y), fill=(58, 60, 68))
    d.ellipse((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), fill=(44, 46, 52))
    rr = r * 0.55
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 200, 330, fill=tuple(min(255, c + 50) for c in rim))
    d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 20, 150, fill=rim_sh or tuple(int(c * 0.7) for c in rim))
    d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(60, 63, 71))
    for k in range(5):
        a = math.radians(k * 72 + spin)
        d.point((cx + 3.2 * math.cos(a), cy + 3.2 * math.sin(a)), fill=(200, 204, 212))


@lru_cache(None)
def series1(spin=0):
    """Early 80-inch 4x4 in side view (96x58 grid), nose right: light-green aluminium panels with galvanised cappings,
    khaki canvas tilt with hoops and a side window, upright split screen, mesh grille with the lamp behind it."""
    body, shade, hi, deep = (138, 168, 116), (104, 132, 86), (186, 212, 160), (76, 98, 62)
    canvas, can_sh, can_hi = (198, 184, 140), (166, 150, 108), (226, 214, 176)
    galv = (190, 196, 204)
    img = Image.new('RGBA', (96, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 6, 46, 30), 3, fill=canvas)                                      # rear tilt
    d.line([(6, 6), (44, 6)], fill=can_hi); d.rectangle((4, 27, 46, 30), fill=can_sh)
    for x in (16, 30): d.line([(x, 7), (x, 29)], fill=can_sh)
    d.rectangle((33, 11, 43, 20), fill=(150, 176, 196)); d.line([(33, 11), (43, 11)], fill=(200, 222, 238))   # side window
    d.rectangle((46, 12, 58, 30), fill=canvas); d.line([(46, 12), (58, 12)], fill=can_hi)    # cab side screen
    d.rectangle((48, 15, 57, 24), fill=(150, 176, 196))
    d.polygon([(58, 8), (61, 8), (62, 31), (59, 31)], fill=(70, 74, 84))                     # screen frame
    d.polygon([(59, 10), (60, 10), (61, 29), (60, 29)], fill=(170, 200, 222))
    d.rectangle((2, 30, 60, 44), fill=body)                                                   # tub + door
    d.line([(2, 30), (60, 30)], fill=galv); d.line([(2, 31), (60, 31)], fill=hi)
    d.rectangle((2, 42, 60, 44), fill=shade); d.line([(46, 32), (46, 43)], fill=deep); d.line([(60, 32), (60, 43)], fill=deep)
    for y in (33, 40): d.rectangle((47, y, 48, y + 1), fill=(60, 63, 71))                    # door hinges
    d.rectangle((56, 36, 58, 36), fill=galv)                                                  # handle
    for x in range(4, 46, 6): d.point((x, 33), fill=deep)                                     # rivets
    d.polygon([(61, 27), (90, 27), (90, 33), (61, 33)], fill=body)                            # flat bonnet
    d.line([(61, 27), (90, 27)], fill=hi); d.line([(64, 29), (88, 29)], fill=shade)
    d.polygon([(62, 33), (94, 33), (94, 37), (90, 42), (62, 42)], fill=body)                  # front wing
    d.line([(62, 33), (94, 33)], fill=galv); d.rectangle((62, 40, 92, 42), fill=shade)
    d.rectangle((90, 27, 94, 41), fill=(54, 58, 66))                                          # grille mesh + lamp
    for y in range(28, 41, 2): d.line([(90, y), (94, y)], fill=(84, 88, 98))
    d.ellipse((90, 28, 95, 33), fill=(255, 238, 180)); d.point((91, 29), fill=(255, 255, 255))
    d.rectangle((92, 43, 95, 46), fill=(40, 42, 48)); d.rectangle((1, 43, 4, 46), fill=(40, 42, 48))   # bumpers
    d.rectangle((86, 34, 88, 35), fill=(255, 150, 60))                                        # side lamp
    for cx in (22, 74):                                                                       # wheel arches
        d.pieslice((cx - 13, 33, cx + 13, 59), 180, 360, fill=deep)
    for cx in (22, 74): _wheel(d, cx, 47, 10, spin, (150, 178, 128))
    return outline(img)


@lru_cache(None)
def sketch_lines(col=(150, 112, 64)):
    """Groove of the 4x4 silhouette as if drawn with a finger: 2 px dark groove with a light lip (series1 grid)."""
    a = series1().getchannel('A').load(); w, h = series1().size
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); p = img.load()
    lip = tuple(min(255, c + 70) for c in col)
    for y in range(h):
        for x in range(w):
            if a[x, y] and any(not (0 <= x + dx < w and 0 <= y + dy < h) or not a[x + dx, y + dy] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                p[x, y] = col + (255,)
                if y > 0 and not a[x, y - 1]: p[x, y - 1] = lip + (255,)
    for cx in (22, 74):                                                                        # wheels as circles
        ImageDraw.Draw(img).ellipse((cx - 6, 41, cx + 6, 53), outline=col)
    return img


def sketch_reveal(level, col=(150, 112, 64)):
    """Sketch revealed left-to-right up to `level` (0..1); returns the image and the pen's grid x."""
    img = sketch_lines(col).copy()
    cut = int(img.width * level)
    if cut < img.width: ImageDraw.Draw(img).rectangle((cut, 0, img.width, img.height), fill=(0, 0, 0, 0))
    return img, cut


@lru_cache(None)
def jeep(spin=0):
    """Wartime light utility jeep in side view (92x52 grid), nose right: olive drab, slotted grille, flat wings,
    split windscreen up, canvas seats, steering wheel, jerrycan, rear spare, hood star."""
    body, shade, hi, deep = (100, 108, 62), (76, 82, 46), (138, 148, 92), (56, 60, 34)
    img = Image.new('RGBA', (92, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 22, 6, 42), fill=(32, 33, 38)); d.rectangle((1, 23, 5, 41), fill=(48, 50, 56))   # spare
    d.rectangle((2, 30, 4, 34), fill=shade)
    d.rectangle((7, 24, 14, 34), fill=deep); d.rectangle((8, 25, 13, 27), fill=shade)          # jerrycan
    d.rounded_rectangle((6, 26, 60, 40), 2, fill=body)                                          # tub
    d.line([(7, 26), (59, 26)], fill=hi); d.rectangle((6, 38, 60, 40), fill=shade)
    d.polygon([(34, 26), (46, 26), (44, 31), (36, 31)], fill=(0, 0, 0, 0))                     # side cut-out
    d.line([(36, 31), (44, 31)], fill=deep)
    d.rectangle((18, 16, 22, 26), fill=(70, 62, 46)); d.rectangle((16, 22, 28, 26), fill=(84, 74, 54))   # rear seat
    d.rectangle((36, 15, 40, 26), fill=(70, 62, 46)); d.rectangle((34, 22, 46, 26), fill=(84, 74, 54))   # driver seat
    d.line([(52, 25), (48, 16)], fill=(40, 42, 48)); d.ellipse((44, 13, 51, 17), outline=(30, 31, 36))   # wheel
    d.polygon([(58, 4), (61, 4), (61, 26), (58, 26)], fill=(64, 68, 50))                        # screen frame
    d.rectangle((59, 6, 60, 20), fill=(160, 190, 210))
    d.rectangle((60, 22, 86, 30), fill=body); d.line([(60, 22), (86, 22)], fill=hi)            # bonnet
    d.line([(62, 25), (84, 25)], fill=shade)
    d.polygon([(70, 24), (72, 24), (73, 22), (74, 24), (76, 24), (74, 26), (75, 28), (73, 27), (71, 28), (72, 26)], fill=(236, 236, 228))  # star
    d.rectangle((86, 22, 90, 38), fill=deep)                                                     # slotted grille
    for y in range(23, 38, 2): d.line([(86, y), (90, y)], fill=(40, 42, 30))
    d.ellipse((87, 23, 91, 27), fill=(255, 240, 180)); d.point((88, 24), fill=(255, 255, 255))
    d.polygon([(60, 30), (91, 30), (91, 33), (87, 37), (60, 37)], fill=body)                    # front wing
    d.line([(60, 30), (91, 30)], fill=hi); d.rectangle((60, 35, 88, 37), fill=shade)
    d.rectangle((89, 38, 92, 41), fill=(40, 42, 48))                                             # bumper
    for cx in (20, 74): d.pieslice((cx - 12, 30, cx + 12, 54), 180, 360, fill=deep)
    for cx in (20, 74): _wheel(d, cx, 42, 9, spin, (92, 100, 56))
    return outline(img)


@lru_cache(None)
def hand():
    """A pointing hand seen from above (24x40): white cuff, shaded knuckles and nails, index finger down."""
    img = Image.new('RGBA', (24, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    skin, sh, hi, nail = (236, 190, 150), (204, 156, 118), (250, 214, 180), (250, 220, 210)
    d.rectangle((3, 0, 20, 12), fill=(248, 248, 250)); d.rectangle((3, 9, 20, 12), fill=(214, 216, 224))   # cuff
    d.rounded_rectangle((3, 13, 21, 27), 3, fill=skin); d.line([(5, 14), (19, 14)], fill=hi)
    for x in (13, 16, 19): d.rounded_rectangle((x - 2, 21, x, 29), 1, fill=skin); d.line([(x, 22), (x, 28)], fill=sh)   # curled fingers
    d.rounded_rectangle((3, 18, 7, 25), 2, fill=sh)                                                          # thumb
    d.rounded_rectangle((8, 24, 12, 39), 2, fill=skin); d.line([(12, 25), (12, 38)], fill=sh)               # index finger
    d.line([(9, 25), (9, 37)], fill=hi); d.rectangle((9, 36, 11, 38), fill=nail)
    return outline(img)


@lru_cache(None)
def wrench():
    img = Image.new('RGBA', (26, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((5, 3, 21, 5), fill=(176, 182, 192)); d.line([(5, 3), (21, 3)], fill=(222, 228, 236))
    d.ellipse((0, 0, 7, 7), fill=(176, 182, 192)); d.rectangle((0, 3, 2, 4), fill=(0, 0, 0, 0))
    d.ellipse((19, 0, 25, 7), fill=(176, 182, 192)); d.ellipse((21, 2, 23, 5), fill=(0, 0, 0, 0))
    return outline(img)


@lru_cache(None)
def alu_sheet(k):
    """Aluminium sheet (44x26) stamped with a wartime aircraft roundel and a serial stencil."""
    img = Image.new('RGBA', (44, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 43, 25), fill=(196, 202, 212)); d.line([(0, 0), (43, 0)], fill=(236, 240, 246))
    for x in range(4, 44, 9): d.line([(x, 1), (x - 3, 24)], fill=(214, 220, 230))
    cx, cy = (12, 13) if k % 2 == 0 else (30, 13)
    for r, c in ((8, (40, 64, 140)), (6, (240, 240, 236)), (3, (200, 40, 48))): d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    for x in range(22 if k % 2 == 0 else 3, 40 if k % 2 == 0 else 20, 4): d.rectangle((x, 20, x + 2, 22), fill=(60, 63, 71))
    for x in range(2, 44, 6): d.point((x, 2), fill=(130, 136, 148)); d.point((x, 23), fill=(130, 136, 148))   # rivets
    return outline(img)


@lru_cache(None)
def crate():
    img = Image.new('RGBA', (34, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 33, 23), fill=(150, 108, 66))
    for y in (7, 15): d.line([(0, y), (33, y)], fill=(118, 82, 48))
    d.rectangle((3, 2, 30, 5), fill=(60, 63, 71)); d.rectangle((3, 10, 30, 13), fill=(80, 84, 92)); d.rectangle((3, 18, 30, 21), fill=(60, 63, 71))
    return outline(img)


@lru_cache(None)
def plane():
    """Small wartime aircraft silhouette (40x14), nose right."""
    img = Image.new('RGBA', (40, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(0, 6), (34, 5), (39, 7), (34, 9), (0, 8)], fill=(150, 160, 120))
    d.polygon([(16, 7), (26, 7), (20, 13)], fill=(120, 130, 96)); d.polygon([(0, 7), (6, 7), (2, 1)], fill=(120, 130, 96))
    d.ellipse((22, 5, 26, 9), fill=(40, 64, 140)); d.point((24, 7), fill=(200, 40, 48))
    return outline(img)


def _bg(rows):
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    for y in range(214):
        c = next(c for y1, c in rows if y < y1)
        d.line([(0, y), (119, y)], fill=c(y) if callable(c) else c)
    return img, d


def _sky(y): return tuple(int(a + (b - a) * min(1, y / 110)) for a, b in zip((70, 140, 214), (196, 226, 246)))


@lru_cache(None)
def beach():
    img, d = _bg([(58, _sky), (70, (60, 120, 170)), (73, (236, 240, 244)), (214, (226, 196, 140))])
    for x in range(0, 120, 3):
        for y in range(76, 214, 5): d.point((x + (y // 5) % 3, y), fill=(206, 174, 120))
    d.ellipse((90, 12, 104, 26), fill=(255, 236, 160))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


@lru_cache(None)
def farm():
    img, d = _bg([(100, _sky), (214, (110, 150, 80))])
    d.polygon([(0, 104), (30, 92), (60, 100), (90, 88), (119, 98), (119, 112), (0, 112)], fill=(90, 130, 70))
    d.rectangle((0, 112, 119, 131), fill=(122, 160, 86))
    d.rectangle((82, 76, 110, 104), fill=(170, 60, 50)); d.polygon([(80, 76), (96, 64), (112, 76)], fill=(120, 44, 40))   # barn
    d.rectangle((92, 88, 100, 104), fill=(90, 34, 30)); d.line([(92, 88), (100, 104)], fill=(236, 230, 220)); d.line([(100, 88), (92, 104)], fill=(236, 230, 220))
    for x in range(0, 120, 8): d.rectangle((x, 116, x + 1, 128), fill=(150, 112, 70))                                     # fence
    d.line([(0, 119), (119, 119)], fill=(150, 112, 70)); d.line([(0, 124), (119, 124)], fill=(150, 112, 70))
    d.rectangle((0, 132, 119, 213), fill=(130, 100, 64))                                                                   # muddy track
    for x in range(0, 120, 7):
        for y in range(136, 214, 9): d.rectangle((x + (y // 9) % 4, y, x + 2 + (y // 9) % 4, y + 1), fill=(108, 82, 52))
    for x, y in ((14, 20), (50, 30)): d.rectangle((x, y, x + 16, y + 4), fill=(250, 252, 255)); d.rectangle((x + 4, y - 3, x + 11, y), fill=(250, 252, 255))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


# ================================================================== shot 1: hook, drawn in the sand
SX, SY, SS = 540, 1290, 10
def draw_lvl(t): return clamp((t - 0.05) / 1.8)
CAM1 = Camera(W, H, [(-1.0, (330, 1000, 1.45)), (0.0, (330, 1000, 1.45)), (1.2, (540, 980, 1.12), 'io'), (1.96, (540, 960, 1.0), 'io'), (2.5, (540, 960, 1.04))],
              kicks=[(0.0, 0.08, 330, 1000), (1.07, 0.06, 540, 1000), (1.96, 0.14, 540, 1000)])


def shot_sand(t):
    img = beach().copy(); fg = layer()
    d = ImageDraw.Draw(img)                                                       # sea glints and a foam line that washes in
    for i in range(12):
        x = (i * 97 + t * 60 * (1 + i % 3)) % 1180 - 50
        d.rectangle((x, 540 + (i * 23) % 80, x + 36, 546 + (i * 23) % 80), fill=(200, 226, 246))
    fy = 657 + 12 * math.sin(t * 2.4)
    d.rectangle((0, fy - 9, W, fy), fill=(244, 248, 250)); d.rectangle((0, fy, W, fy + 18), fill=(204, 186, 136))
    sk, cut = sketch_reveal(draw_lvl(t))
    blit(fg, up(sk, SS), SX, SY)
    if t < 2.1:                                                                  # the finger rides the drawing edge
        x0 = SX - 48 * SS + cut * SS
        a = sketch_lines().getchannel('A').load()
        ys = [y for y in range(58) if a[min(95, cut), y]] or [29]
        fy = SY - 58 * SS + ys[int(t * 7) % len(ys)] * SS
        blit(fg, up(hand(), 9), x0 + 20, fy + 30, 1, 1, -12)
    fx.sparkles(fg, t, SX, SY - 290, 900, 400, n=8, seed=60) if t > 1.96 else None
    fx.ring(fg, t, 1.96, SX, SY - 290, GLOW, life=0.4, r1=560)
    fx.burst(fg, t, 1.96, SX, SY - 290, GLOW, n=14, r0=300, r1=600, seed=61)
    return finish(img, fg, CAM1, t, rim=False)


def overlay(cv, t):
    title(cv, t, 0.05, 2.4, 'Drawn in the', WHITE, 470, 100, -2)
    title(cv, t, 0.3, 2.4, 'sand?', YEL, 600, 140, 3)


# ================================================================== shot 2: the farm and the surplus jeep
def jeep_x(t): return lerp(-500, 560, oc(prog(t, 4.4, 0.7)))
P2 = Presenter([
    (2.45, dict(path=Track([(2.45, (1300, 300)), (2.85, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.85, dict(ground=GROUND, squash=True, arms='present', look=(400, 900), expr='smile', face=None)),
    (4.56, dict(arms='point', point=(560, 1000), look=(560, 1000), expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.5, (540, 900, 1.12)), (4.4, (540, 920, 1.12)), (5.1, (520, 940, 1.2), 'io'), (5.9, (520, 940, 1.22))],
              kicks=[(3.51, 0.06, 900, 800), (4.1, 0.08, 400, 700), (5.1, 0.12, 560, 1000)])


def shot_farm(t):
    img = farm().copy(); fg = layer()
    x = jeep_x(t)
    fx.contact_shadow(fg, x, GROUND, 560, s=S, alpha=130)
    sr, sv = wob(t, (5.1,), 0.07)
    blit(fg, up(jeep(int(x * 0.8) % 360 // 15 * 15), 7), x, GROUND + 4 * math.sin(t * 30) * (t < 5.1), sr, sv)
    for k in range(5): fx.puff(fg, t, 4.45 + k * 0.12, x - 300, GROUND - 30, seed=70 + k, life=0.7, size=0.8, drift=(-200, -80), col=(170, 140, 100))
    fx.dust(fg, t, 5.1, x, GROUND - 10, n=12, seed=71, col=(170, 140, 100))
    if t >= 4.1:
        k = popin(t, 4.1, 0.25) * popout(t, 5.0)
        blit(fg, fx.big('tag', 'WAR SURPLUS', '#fff6e0', '#3c6e2a', s=8), 400, 700, k, k, -6 + 3 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 4.1, 400, 700, GLOW, n=10, seed=72)
    dg.label(fg, t, 3.51, 'MAURICE WILKS', (900, 760), (700, 520), '#ffd23f', '#1a1a2e', '#e8b923', s=7)
    P2.draw(fg, t)
    photo(fg, t, 5.05, 5.85, 'willys', 540, 560, 600, 440, -3, 'A WARTIME JEEP', focus=(0.5, 0.55), zoom=0.05)
    return finish(img, fg, CAM2, t, rim=False)


# ================================================================== shot 3: reliable, but rough; parts shortage
JX = 470
CAM3 = Camera(W, H, [(5.9, (520, 1000, 1.3)), (6.85, (520, 1000, 1.38), 'io'), (7.43, (600, 900, 1.15), 'io'), (8.6, (600, 900, 1.18))],
              kicks=[(6.11, 0.08, JX, 1000), (6.85, 0.14, JX, 1000), (7.43, 0.12, 760, 640), (8.21, 0.08, 760, 640)],
              shakes=[(6.85, 0.6, 12)])
P3 = Presenter([
    (5.9, dict(path=Track([(5.9, (850, GROUND)), (6.0, (850, GROUND))]), size=7, legs='stand', arms='hips', look=(JX, 1000), expr='smile', face=-1, ground=GROUND)),
    (6.11, dict(arms='thumb', expr='grin', squash=True)),
    (6.85, dict(arms='shock', expr='shock', squash=True)),
    (7.43, dict(arms='shrug', expr='sad', look=(760, 640))),
], words=WORDS, base_size=7)


def shot_rough(t):
    img = farm().copy(); fg = layer()
    rough = t >= 6.85
    bump = 26 * abs(math.sin(t * 16)) if rough else 0
    rot = 4 * math.sin(t * 13) if rough else 0
    fx.contact_shadow(fg, JX, GROUND, 560, s=S, alpha=130)
    blit(fg, up(jeep(int(t * 400) % 360 // 15 * 15), 7), JX, GROUND - bump, 1, 1, rot)
    if rough:
        for k in range(6): fx.puff(fg, t, 6.85 + k * 0.15, JX - 280, GROUND - 20, seed=80 + k, life=0.6, size=0.8, drift=(-160, -120), col=(170, 140, 100))
    if t >= 6.11:
        k = popin(t, 6.11, 0.25)
        blit(fg, fx.big('check', s=9), JX - 160, 640, k, k, anchor='center'); fx.ring(fg, t, 6.11, JX - 160, 640, (60, 200, 90), life=0.3, r1=160)
    if t >= 6.85:
        k = popin(t, 6.85, 0.25)
        blit(fg, fx.big('xmark', s=9), JX + 160, 640, k, k, 6 * math.sin(t * 9), anchor='center'); fx.burst(fg, t, 6.85, JX + 160, 640, RED, seed=81)
    if t >= 7.43:                                                                # parts shortage sign + spinning wrench
        k = popin(t, 7.43, 0.3) * (1 + 0.04 * math.sin(t * 8))
        blit(fg, fx.big('tag', 'PARTS SHORTAGE', '#fff6e0', '#d6303a', s=7), 600, 420, k, k, -5 + 3 * math.sin(t * 5), anchor='center')
        blit(fg, up(wrench(), 9), 820, 760, k, k, t * 300, anchor='center')
        fx.burst(fg, t, 7.43, 600, 420, RED, seed=82)
    if t >= 8.21: fx.stamp_at(fg, t, 8.21, 'SOLD OUT', 600, 560, rot=8, s=8)
    P3.draw(fg, t)
    return finish(img, fg, CAM3, t, rim=False)


# ================================================================== shot 4: steel scarce, aircraft aluminium
BENCH = GROUND - 160
SHEETS = [(10.69, 0), (10.95, 1), (11.2, 2)]
P4 = Presenter([
    (8.55, dict(path=Track([(8.55, (-200, 500)), (8.95, (160, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (8.95, dict(ground=GROUND, squash=True, arms='point', point=(780, BENCH - 150), look=(780, BENCH - 150), expr='think', face=None)),
    (10.69, dict(arms='present', look=(540, BENCH - 150), expr='grin', point=None)),
    (11.69, dict(arms='point', point=(700, 380), look=(700, 380), expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(8.6, (560, 900, 1.12)), (9.81, (680, 860, 1.3), 'io'), (10.69, (560, 860, 1.12), 'io'), (12.6, (560, 840, 1.16))],
              kicks=[(9.43, 0.08, 780, 900), (9.81, 0.14, 780, 900)] + [(ts, 0.08, 560, BENCH - 120) for ts, _ in SHEETS] + [(11.69, 0.1, 700, 380)],
              shakes=[(9.81, 0.25, 10)])


def shot_alloy(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    d.rectangle((260, BENCH, 1000, BENCH + 30), fill=(150, 104, 66)); d.rectangle((260, BENCH, 1000, BENCH + 6), fill=(190, 140, 96))
    for x in (290, 950): d.rectangle((x, BENCH + 30, x + 24, GROUND), fill=(110, 72, 44))
    kc = popin(t, 8.7, 0.3) * popout(t, 10.4)
    if kc > 0:
        blit(fg, up(crate(), 9), 780, BENCH, kc, kc)
        blit(fg, fx.big('tag', 'STEEL', '#fff6e0', '#3c3f47', s=6), 780, BENCH - 250, kc, kc, -4, anchor='center')
        if t >= 9.81:
            kx = popin(t, 9.81, 0.25); blit(fg, fx.big('xmark', s=14), 780, BENCH - 110, kx * kc, kx * kc, anchor='center')
            fx.burst(fg, t, 9.81, 780, BENCH - 110, RED, seed=90)
    for i, (ts, k) in enumerate(SHEETS):                                           # sheets slide in and stack
        if t >= ts:
            u = oc(prog(t, ts, 0.35))
            blit(fg, up(alu_sheet(k), 9), lerp(1500, 600 - 20 * i, u), BENCH - 14 * i, 1, 1, lerp(-20, -2 + 2 * i, u))
            fx.dust(fg, t, ts + 0.35, 600, BENCH - 14 * i, n=6, seed=91 + i, col=(220, 224, 232))
    if t >= 11.0: fx.sparkles(fg, t, 600, BENCH - 120, 400, 160, n=6, seed=94)
    dg.label(fg, t, 11.2, 'ALUMINIUM ALLOY', (600, BENCH - 200), (520, 560), '#7fe3a0', '#1a1a2e', '#3cc85a', s=7)
    if t >= 11.6:
        u = prog(t, 11.6, 0.9)
        if u < 1: blit(fg, up(plane(), 9), lerp(-300, 1400, u), 400 - 60 * u, 1, 1, -6); fx.speed_lines(fg, 0.3, int(t * 10) % 5, col=(220, 224, 232))
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the show stand, sketch to Series I
STAND = GROUND - 60
def morph(t): return clamp((t - 14.27) / 0.35)
CAM5 = Camera(W, H, [(12.6, (540, 860, 1.12)), (14.27, (540, 900, 1.2), 'io'), (15.47, (540, 880, 1.12), 'io'), (16.0, (540, 880, 1.14))],
              kicks=[(12.78, 0.1, 540, 420), (13.37, 0.1, 540, 420), (14.27, 0.16, 540, STAND - 200)], shakes=[(14.27, 0.25, 10)])


def shot_show(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    d.ellipse((140, STAND - 40, 940, STAND + 80), fill=(60, 63, 71)); d.ellipse((140, STAND - 50, 940, STAND + 60), fill=(150, 156, 168))
    fx.rays(fg, t, 14.27, 540, STAND - 220, GLOW, life=1.0, r=560)
    m = morph(t)
    if m < 1: blit(fg, up(sketch_lines((236, 214, 160)), 7), 540, STAND, 1, 1)
    if m > 0:
        car_ = up(series1(int(t * 60) % 360 // 15 * 15), 7).copy()
        car_.putalpha(car_.getchannel('A').point(lambda v: int(v * m)))
        sr, sv = wob(t, (14.3,), 0.07)
        blit(fg, car_, 540, STAND, sr, sv)
    fx.burst(fg, t, 14.27, 540, STAND - 200, GLOW, n=14, seed=95); fx.ring(fg, t, 14.27, 540, STAND - 200, (255, 255, 255), life=0.3, r1=420)
    if t >= 12.78:                                                                 # banner drops in
        y = lerp(-200, 420, oc(prog(t, 12.78, 0.35)))
        blit(fg, fx.big('badge', '30 APRIL', '#ffd23f', '#1a1a2e', '#e8b923', s=9), 500, y - 110, 1, 1, -3 + 2 * math.sin(t * 4), anchor='center')
        if t >= 13.37:
            k = popin(t, 13.37, 0.25)
            blit(fg, fx.big('badge', '1948', '#ffd23f', '#d6303a', '#e8b923', s=13), 500, 470, k, k, 3, anchor='center')
            fx.burst(fg, t, 13.37, 540, 470, GLOW, seed=96)
    dg.label(fg, t, 14.4, 'SERIES I', (400, STAND - 300), (300, 720), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    if t >= 14.4: fx.sparkles(fg, t, 540, STAND - 200, 700, 260, n=8, seed=97)
    dg.label(fg, t, 15.47, 'AMSTERDAM', (760, STAND - 60), (780, 760), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    GAR.reflect(img, fg)
    photo(fg, t, 15.0, 15.9, 'series1', 540, 1000, 560, 420, 4, 'AN EARLY SERIES I', focus=(0.5, 0.55), zoom=0.05)
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: from a sketch to an icon
CAR6 = 590
P6 = Presenter([
    (15.95, dict(path=Track([(15.95, (-200, 400)), (16.3, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (16.3, dict(ground=GROUND, squash=True, arms='present', look=(CAR6, 1000), expr='grin', face=None)),
    (16.71, dict(arms='thumb', look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM6 = Camera(W, H, [(16.0, (560, 900, 1.12)), (17.38, (560, 920, 1.18), 'io'), (18.0, (560, 920, 1.19))],
              kicks=[(16.28, 0.08, CAR6, 1000), (16.71, 0.1, 200, 900), (17.38, 0.16, CAR6, 900)], shakes=[(17.38, 0.2, 8)])


def shot_icon(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 17.38, CAR6, GROUND - 220, GLOW, life=1.0, r=600)
    fx.contact_shadow(fg, CAR6, GROUND, 620, s=S, alpha=140)
    blit(fg, up(series1(), 7), CAR6, GROUND)
    if t >= 16.28:                                                                  # the sand sketch, framed on the wall
        k = popin(t, 16.28, 0.25) * popout(t, 17.3)
        card = Image.new('RGBA', (300, 190), (236, 214, 160, 255)); ImageDraw.Draw(card).rectangle((0, 0, 299, 189), outline=(26, 26, 46), width=6)
        card.alpha_composite(up(sketch_lines(), 3), (24, 30))
        blit(fg, card, 760, 560, k, k, 4, anchor='center')
    dg.label(fg, t, 17.38, 'ICON', (CAR6, GROUND - 330), (CAR6 + 80, 560), '#7fe3a0', '#1a1a2e', '#3cc85a', s=11)
    fx.confetti(fg, t, 17.38, 600, 640, n=40, seed=9)
    fx.sparkles(fg, t * 1.3, CAR6, GROUND - 220, 640, 260, n=8, seed=98)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(18.0, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_sand), (2.5, shot_farm), (5.9, shot_rough), (8.6, shot_alloy), (12.6, shot_show), (16.0, shot_icon), (18.0, shot_teaser)]
TRANS = {1: (2.5, 2.7, 'whip', dict(dx=-1)), 2: (5.9, 6.05, 'push', None), 3: (8.6, 8.8, 'whip', dict(dx=0, dy=1)),
         4: (12.6, 12.8, 'iris', (600, BENCH - 60)), 5: (16.0, 16.2, 'whip', dict(dx=1)), 6: (18.0, 18.2, 'whip', dict(dx=1))}
KEYCOL = {'sand': YEL, 'sketched': YEL, 'wilks': YEL, 'jeep': YEL, 'reliable': RED, 'rough': RED, 'parts': RED, 'scarce': RED,
          'aircraft': GRN, 'wartime': GRN, 'aluminium': GRN, '1948': YEL, 'series': YEL, 'i': YEL, 'amsterdam': YEL, 'icon': GRN}
CUES = [
    (0.0, 'whoosh', 0.5), (0.05, 'stamp', 0.6), (0.3, 'pop', 0.8), (0.32, 'sparkle', 0.5), (0.6, 'click', 0.3), (1.1, 'click', 0.3),
    (1.96, 'ding', 0.8), (1.98, 'sparkle', 0.7),
    (2.9, 'thump', 0.5), (3.51, 'pop', 0.6), (4.1, 'stamp', 0.6), (4.45, 'vroom', 0.7), (5.1, 'thump', 0.6), (5.05, 'pop', 0.6),
    (6.11, 'ding', 0.6), (6.85, 'buzzer', 0.5), (6.87, 'crash', 0.4), (7.0, 'thump', 0.4), (7.2, 'thump', 0.4), (7.43, 'pop', 0.8),
    (7.45, 'click', 0.6), (8.21, 'stamp', 0.7),
    (8.75, 'pop', 0.5), (9.43, 'thump', 0.5), (9.81, 'buzzer', 0.6)] + [(ts, 'slide_down', 0.5) for ts, _ in SHEETS] + [
    (11.2, 'pop', 0.6), (11.6, 'whoosh', 0.8), (11.62, 'vroom', 0.4),
    (12.78, 'fall', 0.5), (12.9, 'thump', 0.6), (13.37, 'stamp', 0.8), (14.27, 'boom', 0.5), (14.29, 'ding', 0.8), (14.3, 'sparkle', 0.8),
    (14.4, 'pop', 0.6), (15.0, 'pop', 0.6), (15.47, 'pop', 0.5),
    (16.3, 'thump', 0.5), (16.28, 'pop', 0.6), (16.71, 'click', 0.5), (17.38, 'confetti', 0.9), (17.4, 'ding', 0.8), (17.42, 'sparkle', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
