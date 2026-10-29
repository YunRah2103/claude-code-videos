"""Renders 'The first hybrid': the 1997 launch in Japan, a petrol engine plus two motors through a planetary gear.

Template: videos/the-land-rover-from-the-sand (ac-idle shot structure on shared/episode.py). Word times come from
align.py -> words.json (the voiceover is the timing spine). Speech runs 0.4-16.7 s; the read has no 'Follow' line,
so the end card shows it. Cars are generic pixel redraws with no badges or lettering. 'First' is Toyota's claim and
is shown as such ('KNOWN AS THE FIRST').
Shots:
  1 merge     0.00  a petrol engine and an electric motor fly together and fuse into one glowing unit; '1997'
  2 launch    1.90  a showroom: the 1997 banner drops, the hybrid rolls out; IN JAPAN; KNOWN AS THE FIRST; photo
  3 gear      6.60  diagram: engine + two motor-generators feeding a turning planetary gear, power dots flowing
  4 line      9.90  a production line; counter climbs to 20,000 in 1998
  5 today    13.60  night street: today's hybrids roll past, each with a leaf tag; the original leads them
  6 teaser   16.50  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title, street, draw_car, headlights, ROAD_Y, ROAD
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid, text_width

WORDS = kit.load_words(HERE)
DUR, END_T = 18.4, 16.7


# ------------------------------------------------------------------ episode sprites
def ptext(s, col, ol=False):
    g = Grid(text_width(s) + 2, 9); g.text(1, 1, s, col if isinstance(col, str) else '#%02x%02x%02x' % col)
    return g.image(outline=ol)


def _wheel(d, cx, cy, r, spin, rim):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 27, 32))
    d.ellipse((cx - r + 1.5, cy - r + 1.5, cx + r - 1.5, cy + r - 1.5), fill=(40, 42, 48))
    rr = r * 0.6
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 200, 330, fill=tuple(min(255, c + 50) for c in rim))
    for k in range(5):
        a = math.radians(k * 72 + spin)
        d.line([(cx + 1.2 * math.cos(a), cy + 1.2 * math.sin(a)), (cx + rr * math.cos(a), cy + rr * math.sin(a))], fill=tuple(int(c * 0.65) for c in rim))
    d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=(230, 232, 238))


@lru_cache(None)
def hybrid(spin=0):
    """Tall, compact late-90s hybrid saloon (96x42 grid), nose right, in pale silver-green: short rounded nose,
    high roofline with a long glasshouse, stubby boot, aero wheel covers. No emblem."""
    body, shade, hi, deep = (176, 196, 186), (136, 156, 148), (222, 238, 230), (96, 112, 106)
    img = Image.new('RGBA', (96, 42), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = [(3, 18), (8, 14), (20, 13), (28, 3), (60, 2), (72, 12), (86, 16), (93, 20), (94, 29), (3, 29)]
    d.polygon(pts, fill=body); d.line(pts[:-2], fill=hi)
    d.rectangle((3, 24, 94, 26), fill=shade); d.rectangle((3, 27, 94, 29), fill=deep)
    d.polygon([(22, 12), (30, 5), (44, 5), (44, 12)], fill=(118, 150, 178)); d.polygon([(47, 12), (47, 5), (59, 4), (69, 12)], fill=(118, 150, 178))
    d.line([(31, 6), (43, 6)], fill=(196, 222, 240)); d.line([(45, 4), (45, 13)], fill=deep)
    d.line([(45, 14), (45, 24)], fill=deep); d.line([(70, 14), (70, 24)], fill=deep); d.line([(21, 14), (21, 24)], fill=deep)
    d.rectangle((36, 16, 39, 16), fill=hi); d.rectangle((60, 16, 63, 16), fill=hi)
    d.polygon([(86, 17), (92, 19), (92, 21), (86, 20)], fill=(250, 248, 220))                    # swept lamp
    d.rectangle((88, 23, 94, 25), fill=(80, 90, 100))                                             # slim intake
    d.rectangle((2, 17, 5, 21), fill=(200, 50, 50))
    d.rectangle((66, 18, 69, 21), fill=(60, 180, 110))                                            # small green leaf decal
    for cx in (20, 76): d.pieslice((cx - 10, 20, cx + 10, 40), 180, 360, fill=(14, 14, 20))
    for cx in (20, 76): _wheel(d, cx, 31, 8.6, spin, (196, 204, 212))
    return outline(img)


@lru_cache(None)
def petrol():
    """Petrol engine icon (40x34): block with four cylinder heads, red rocker cover, intake runners, pulley, sump."""
    img = Image.new('RGBA', (40, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((4, 12, 35, 28), fill=(140, 146, 158)); d.line([(4, 12), (35, 12)], fill=(190, 196, 208))
    d.rounded_rectangle((6, 4, 33, 12), 2, fill=(214, 48, 58)); d.line([(8, 5), (31, 5)], fill=(255, 120, 122))
    for x in (10, 17, 24, 31): d.rectangle((x - 1, 1, x + 1, 4), fill=(110, 116, 128))
    for y in (16, 20, 24): d.line([(6, y), (33, y)], fill=(118, 124, 136))
    d.ellipse((0, 16, 9, 25), fill=(70, 74, 86)); d.ellipse((3, 19, 6, 22), fill=(170, 176, 188))
    d.rectangle((8, 28, 31, 32), fill=(90, 94, 106))
    return outline(img)


@lru_cache(None)
def motor(spin=0, col=(60, 140, 220)):
    """Electric motor-generator icon (34x30): cylinder housing with copper windings, cooling fins, shaft, bolt."""
    img = Image.new('RGBA', (34, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    hi = tuple(min(255, c + 70) for c in col); sh = tuple(int(c * 0.65) for c in col)
    d.rounded_rectangle((3, 3, 28, 27), 6, fill=col); d.line([(6, 4), (25, 4)], fill=hi); d.line([(6, 26), (25, 26)], fill=sh)
    for x in range(7, 26, 3): d.line([(x, 6), (x, 24)], fill=sh)
    d.ellipse((9, 9, 22, 21), fill=(200, 120, 50)); d.ellipse((12, 12, 19, 18), fill=(240, 170, 90))
    a = math.radians(spin); d.line([(15.5, 15), (15.5 + 3 * math.cos(a), 15 + 3 * math.sin(a))], fill=(120, 60, 20))
    d.rectangle((28, 13, 33, 16), fill=(170, 176, 188))
    d.polygon([(16, 7), (12, 15), (16, 15), (13, 23), (20, 13), (16, 13), (19, 7)], fill=(255, 230, 80))
    return outline(img)


@lru_cache(None)
def planetary(deg=0):
    """Planetary gear set (60x60): toothed ring, three planets on a carrier, sun gear; `deg` turns it."""
    img = Image.new('RGBA', (60, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    c = 30
    for k in range(36):                                                                  # ring gear teeth (outside)
        a = math.radians(k * 10 + deg * 0.4)
        d.rectangle((c + 28 * math.cos(a) - 1, c + 28 * math.sin(a) - 1, c + 28 * math.cos(a) + 1, c + 28 * math.sin(a) + 1), fill=(170, 176, 188))
    d.ellipse((c - 27, c - 27, c + 27, c + 27), fill=(150, 156, 168)); d.ellipse((c - 22, c - 22, c + 22, c + 22), fill=(30, 32, 40))
    for k in range(3):                                                                   # carrier + planets
        a = math.radians(k * 120 + deg * 0.6)
        px, py = c + 13 * math.cos(a), c + 13 * math.sin(a)
        d.line([(c, c), (px, py)], fill=(90, 160, 110), width=2)
        d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=(90, 200, 120))
        for j in range(8):
            b = math.radians(j * 45 - deg * 1.5)
            d.point((px + 7.5 * math.cos(b), py + 7.5 * math.sin(b)), fill=(60, 140, 80))
        d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(30, 60, 40))
    d.ellipse((c - 6, c - 6, c + 6, c + 6), fill=(255, 200, 60))                          # sun
    for j in range(10):
        b = math.radians(j * 36 + deg)
        d.point((c + 6.5 * math.cos(b), c + 6.5 * math.sin(b)), fill=(200, 140, 30))
    d.ellipse((c - 2, c - 2, c + 2, c + 2), fill=(120, 80, 20))
    return outline(img)


@lru_cache(None)
def fused(pulse=0):
    """The merged hybrid unit (52x34): engine block and motor housing joined by a glowing coupling."""
    img = Image.new('RGBA', (60, 36), (0, 0, 0, 0))
    img.alpha_composite(petrol(), (0, 1)); img.alpha_composite(motor(pulse * 30), (26, 4))
    d = ImageDraw.Draw(img); d.rectangle((34, 14, 40, 22), fill=(255, 220, 90))
    return img


def counter(n, col='#ff5a5a'):
    return fx.big('badge', f'{n:,}'.replace(',', ' '), '#1a1a2e', col, '#3c3f47', s=11)


# ------------------------------------------------------------------ worlds (9 px grid)
@lru_cache(None)
def showroom():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    for y in range(132):
        u = y / 132; d.line([(0, y), (119, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip((120, 170, 220), (210, 226, 240))))
    d.rectangle((8, 40, 111, 131), fill=(220, 222, 228)); d.rectangle((8, 40, 111, 46), fill=(60, 64, 76))
    d.rectangle((14, 54, 105, 128), fill=(120, 150, 180))
    for x in range(14, 106, 23): d.line([(x, 54), (x, 128)], fill=(220, 222, 228))
    d.line([(14, 90), (105, 90)], fill=(220, 222, 228))
    for x in range(20, 100, 23): d.line([(x, 60), (x + 8, 84)], fill=(170, 200, 226))
    for x in (30, 60, 90): d.rectangle((x - 3, 56, x + 3, 58), fill=(255, 250, 220))
    d.rectangle((0, 132, 119, 213), fill=(150, 154, 164))
    for x in range(0, 120, 12): d.line([(x, 132), (x - 20, 213)], fill=(136, 140, 150))
    for x in range(0, 120, 16):                                                           # potted plants
        pass
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


@lru_cache(None)
def factory():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 119, 131), fill=(54, 58, 72))
    for x in range(0, 120, 24):
        d.rectangle((x + 2, 10, x + 20, 40), fill=(80, 96, 124)); d.rectangle((x + 4, 12, x + 18, 38), fill=(120, 150, 190))
        d.line([(x + 11, 12), (x + 11, 38)], fill=(80, 96, 124)); d.line([(x + 4, 25), (x + 18, 25)], fill=(80, 96, 124))
    d.rectangle((0, 50, 119, 53), fill=(90, 200, 120))
    for x in range(0, 120, 12): d.rectangle((x, 54, x + 1, 120), fill=(76, 80, 96))
    for x in range(6, 120, 24):                                                          # robot arms
        d.rectangle((x, 54, x + 2, 70), fill=(255, 170, 40)); d.line([(x + 1, 70), (x + 8, 80)], fill=(255, 170, 40), width=2)
    d.rectangle((0, 132, 119, 213), fill=(70, 72, 84))
    d.rectangle((0, 128, 119, 135), fill=(40, 42, 50))
    for x in range(0, 120, 6): d.rectangle((x, 129, x + 3, 130), fill=(100, 104, 116))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


# ================================================================== shot 1: two engines merge
MX, MY = 540, 1000
MERGE_T = 1.3
def eng_pos(t): u = io(prog(t, 0.0, MERGE_T)); return lerp(160, MX - 80, u), MY - 220 * math.sin(math.pi * u) * 0.5
def mot_pos(t): u = io(prog(t, 0.1, MERGE_T - 0.1)); return lerp(920, MX + 100, u), MY - 220 * math.sin(math.pi * u) * 0.5
CAM1 = Camera(W, H, [(-1.0, (540, 980, 1.2)), (0.0, (540, 980, 1.2)), (1.2, (540, 960, 1.06), 'io'), (1.9, (540, 960, 1.14), 'io')],
              kicks=[(0.0, 0.06, 540, 900), (0.51, 0.08, 540, 700), (MERGE_T, 0.2, MX, MY - 120)], shakes=[(MERGE_T, 0.3, 14)])


def shot_merge(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, MERGE_T, MX, MY - 130, (120, 230, 160), hold=True, r=580)
    if t < MERGE_T:
        for pos, spr, sd in ((eng_pos(t), petrol(), 1), (mot_pos(t), motor(int(t * 600) % 360 // 30 * 30), -1)):
            blit(fg, up(spr, 12), pos[0], pos[1], 1, 1, sd * 8 * math.sin(t * 6), anchor='center')
            fx.puff(fg, t, t - 0.05, pos[0] - sd * 120, pos[1], seed=int(t * 30) % 40 + (sd > 0) * 40, life=0.4, size=0.5, drift=(-sd * 200, -40),
                    col=(170, 172, 180) if sd > 0 else (140, 200, 255))
    else:
        k = 1 + 0.25 * math.exp(-(t - MERGE_T) * 6) + 0.03 * math.sin(t * 8)
        blit(fg, up(fused(int(t * 8) % 12), 13), MX, MY, k, k, 0, anchor='center')
        fx.sparkles(fg, t, MX, MY, 640, 380, n=9, seed=2)
    fx.ring(fg, t, MERGE_T, MX, MY, (120, 230, 160), life=0.4, r1=560)
    fx.burst(fg, t, MERGE_T, MX, MY, (120, 230, 160), n=18, r0=200, r1=600, seed=3)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.85, 'Two', YEL, 420, 150, -3)
    title(cv, t, 0.25, 1.85, 'engines,', WHITE, 560, 110, 2)
    title(cv, t, 0.45, 1.85, 'one car.', WHITE, 680, 110, -2)


# ================================================================== shot 2: 1997, the launch
def car2_x(t): return lerp(360, 560, oc(prog(t, 2.71, 0.9)))
P2 = Presenter([
    (1.85, dict(path=Track([(1.85, (1300, 400)), (2.25, (900, GROUND + 40), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.25, dict(ground=GROUND + 40, squash=True, arms='present', look=(540, 1000), expr='smile', face=None)),
    (4.85, dict(arms='point', point=(400, 470), look=(400, 470), expr='grin')),
    (5.87, dict(arms='thumb', point=None, look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(1.9, (540, 920, 1.14)), (2.71, (540, 960, 1.2), 'io'), (3.54, (560, 900, 1.12), 'io'), (5.27, (520, 860, 1.16), 'io'), (6.6, (540, 900, 1.2))],
              kicks=[(2.05, 0.12, 540, 400), (2.71, 0.12, 540, 1000), (3.54, 0.08, 760, 640), (4.85, 0.1, 400, 470), (5.87, 0.12, 540, 1000)])


def shot_launch(t):
    img = showroom().copy(); fg = layer()
    x = car2_x(t)
    fx.contact_shadow(fg, x, GROUND + 40, 620, s=S, alpha=120)
    sr, sv = wob(t, (3.6,), 0.06)
    blit(fg, up(hybrid(int(x * 0.8) % 360 // 15 * 15), 7), x, GROUND + 40, sr, sv)
    fx.dust(fg, t, 3.6, x, GROUND + 30, n=8, seed=20, col=(220, 224, 232))
    if t >= 1.95:                                                                       # banner drops
        y = lerp(-200, 360, oc(prog(t, 1.95, 0.35)))
        blit(fg, fx.big('badge', '1997', '#7fe3a0', '#1a1a2e', '#3cc85a', s=14), 540, y, 1, 1, -2 + 2 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 2.05, 540, 360, (60, 200, 90), n=14, seed=21)
    if t >= 2.71: fx.sparkles(fg, t, x, GROUND - 120, 700, 220, n=7, seed=22)
    if t >= 3.54:
        k = popin(t, 3.54, 0.25) * popout(t, 4.7)
        blit(fg, fx.big('tag', 'LAUNCHED IN JAPAN', '#fff6e0', '#d6303a', s=7), 600, 620, k, k, 4, anchor='center')
    if t >= 4.85:
        k = popin(t, 4.85, 0.25)
        blit(fg, fx.big('tag', 'KNOWN AS THE FIRST', '#fff6e0', '#1a1a2e', s=7), 520, 580, k, k, -4 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 4.85, 520, 580, GLOW, n=10, seed=23)
    if t >= 5.27:
        k = popin(t, 5.27, 0.25)
        blit(fg, fx.big('badge', 'MASS-PRODUCED HYBRID', '#7fe3a0', '#1a1a2e', '#3cc85a', s=6), 520, 690, k, k, 2, anchor='center')
    fx.confetti(fg, t, 5.87, 540, 600, n=30, seed=24)
    P2.draw(fg, t)
    photo(fg, t, 3.0, 3.5, 'prius', 560, 980, 620, 440, -3, 'FIRST GENERATION, 1997', focus=(0.5, 0.55), pix=4)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: engine + two motors through a planetary gear
GX, GY = 540, 860
ENG, MG1, MG2, WHL = (230, 640), (230, 1060), (850, 640), (850, 1060)
def gear_deg(t): return (t - 6.6) * 260
def flow(fg, t, t0, a, b, col, n=5):
    if t < t0: return
    d = ImageDraw.Draw(fg); k = min(1, (t - t0) / 0.3)
    d.line([a, (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)], fill=col + (255,), width=14)
    for i in range(n):
        u = ((t - t0) * 1.4 + i / n) % 1 * k
        x, y = lerp(a[0], b[0], u), lerp(a[1], b[1], u)
        d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=(255, 255, 255, 255))
CAM3 = Camera(W, H, [(6.6, (560, 960, 1.18)), (7.62, (360, 820, 1.3), 'io'), (8.61, (560, 960, 1.08), 'io'), (9.9, (560, 960, 1.12))],
              kicks=[(7.23, 0.1, ENG[0], ENG[1]), (8.44, 0.1, MG1[0], MG1[1]), (8.61, 0.1, MG2[0], MG2[1]), (9.22, 0.14, GX, GY)])


def shot_gear(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    flow(fg, t, 7.4, ENG, (GX, GY), (214, 48, 58))
    flow(fg, t, 8.5, MG1, (GX, GY), (60, 140, 220))
    flow(fg, t, 8.7, MG2, (GX, GY), (60, 140, 220))
    flow(fg, t, 9.22, (GX, GY), WHL, (60, 200, 90))
    blit(fg, up(planetary(int(gear_deg(t)) % 360 // 4 * 4), 9), GX, GY, 1, 1, 0, anchor='center')
    dg.label(fg, t, 6.9, 'PLANETARY GEAR', (GX, GY - 280), (GX, 450), '#ffd23f', '#1a1a2e', '#e8b923', s=6)
    for (x, y), ts, spr, lab, col in ((ENG, 7.23, petrol(), 'PETROL', '#ff5a5a'), (MG1, 8.44, motor(int(t * 500) % 360 // 30 * 30), 'MOTOR 1', '#7fd4ff'),
                                      (MG2, 8.61, motor(int(t * 500) % 360 // 30 * 30, (90, 120, 230)), 'MOTOR 2', '#7fd4ff')):
        if t >= ts:
            k = popin(t, ts, 0.25)
            blit(fg, up(spr, 8), x, y, k, k, 3 * math.sin(t * 9 + x) if spr is not None else 0, anchor='center')
            blit(fg, fx.big('label', lab, col, s=6), x, y + 170, k, k, anchor='center')
            fx.burst(fg, t, ts, x, y, GLOW, n=10, r0=80, r1=260, seed=int(x + y) % 90)
    if t >= 9.22:                                                                      # out to a wheel
        k = popin(t, 9.22, 0.25)
        img_w = Image.new('RGBA', (24, 24), (0, 0, 0, 0)); _wheel(ImageDraw.Draw(img_w), 12, 12, 11, gear_deg(t), (196, 204, 212))
        blit(fg, up(outline(img_w), 9), WHL[0], WHL[1], k, k, 0, anchor='center')
        blit(fg, fx.big('label', 'WHEELS', '#7fe3a0', s=6), WHL[0], WHL[1] + 170, k, k, anchor='center')
        fx.sparkles(fg, t, GX, GY, 700, 600, n=8, seed=30)
    if t >= 8.94:
        k = popin(t, 8.94, 0.25)
        blit(fg, fx.big('badge', 'WORKING TOGETHER', '#ffd23f', '#1a1a2e', '#e8b923', s=6), GX, 330, k, k, -3, anchor='center')
    GAR.reflect(img, fg)
    photo(fg, t, 9.45, 9.85, 'cutaway', 540, 900, 600, 430, -3, 'A FIRST-GENERATION CUTAWAY', pix=4)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: the line, 20,000 by 1998
LINE_Y = GROUND + 40
def line_scroll(t): return (t - 9.9) * 520 * (1 + 0.8 * io(prog(t, 11.0, 0.5)))
def built(t): return 0 if t < 10.3 else min(20000, int(20000 * io(prog(t, 10.3, 1.04))))
CAM4 = Camera(W, H, [(9.9, (540, 940, 1.14)), (11.34, (540, 820, 1.24), 'io'), (12.32, (540, 900, 1.12), 'io'), (13.6, (560, 900, 1.16))],
              kicks=[(10.02, 0.1, 540, 400), (11.34, 0.18, 540, 520), (12.79, 0.1, 760, 700)], shakes=[(11.34, 0.3, 10)])


def shot_line(t):
    img = factory().copy(); fg = layer()
    sc = line_scroll(t)
    for i in range(-1, 3):
        x = (i * 720 + sc) % 2160 - 540
        fx.contact_shadow(fg, x, LINE_Y, 600, s=S, alpha=120)
        blit(fg, up(hybrid(int(sc) % 360 // 30 * 30), 6), x, LINE_Y)
        if 200 < x < 900 and int(t * 8) % 3 == 0: fx.burst(fg, t, t - 0.02, x, LINE_Y - 240, GLOW, n=5, r0=20, r1=120, seed=i + int(t * 8))
    if t >= 10.02:
        k = popin(t, 10.02, 0.25) * popout(t, 11.2)
        blit(fg, fx.big('badge', '1998', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 540, 420, k, k, -3, anchor='center')
    if t >= 10.3:
        k = popin(t, 10.3, 0.25) * (1 + 0.15 * math.exp(-(t - 11.34) * 8) * (t >= 11.34))
        blit(fg, counter(built(t)), 540, 560, k, k, 2, anchor='center')
        blit(fg, fx.big('label', 'BUILT', '#ffffff', s=8), 540, 690, k, k, anchor='center')
    fx.ring(fg, t, 11.34, 540, 560, RED, life=0.35, r1=380); fx.burst(fg, t, 11.34, 540, 560, RED, n=16, seed=40)
    fx.confetti(fg, t, 11.36, 540, 500, n=30, seed=41)
    if t >= 11.09:
        k = popin(t, 11.09, 0.22)
        blit(fg, fx.big('tag', 'ABOUT', '#fff6e0', '#1a1a2e', s=6), 250, 440, k, k, -8, anchor='center')
    if t >= 12.79:
        k = popin(t, 12.79, 0.25)
        blit(fg, fx.big('badge', 'IN JAPAN ALONE', '#ffffff', '#d6303a', '#d6d9e2', s=7), 600, 820, k, k, 3, anchor='center')
    return finish(img, fg, CAM4, t, rim=False)


# ================================================================== shot 5: today's hybrids owe it something
def scroll5(t): return (t - 13.6) * 260
CARS5 = [(0, 'blue', 13.7), (1, 'red', 14.0), (2, 'silver', 14.3), (3, 'yellow', 14.6)]
P5 = Presenter([
    (13.55, dict(path=Track([(13.55, (-200, 300)), (13.95, (180, ROAD_Y - 60), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (13.95, dict(ground=ROAD_Y - 60, squash=True, arms='present', look=(600, 900), expr='smile', face=None)),
    (15.69, dict(arms='thumb', look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM5 = Camera(W, H, [(13.6, (560, 980, 1.12)), (14.4, (600, 1000, 1.2), 'io'), (15.69, (560, 960, 1.12), 'io'), (16.5, (560, 960, 1.16))],
              kicks=[(14.4, 0.1, 600, 1000), (15.14, 0.08, 600, 900), (15.69, 0.14, 540, 520)])


def shot_today(t):
    sc = scroll5(t)
    img = street(t, sc); fg = layer()
    lead_x = lerp(-400, 820, oc(prog(t, 13.65, 1.2)))
    for i, col, ts in CARS5:                                                            # a queue of modern hybrids behind it
        x = lead_x - 470 * (i + 1) + 200 * oc(prog(t, ts, 0.8))
        if -400 < x < 1400:
            headlights(fg, x + 200, ROAD_Y - 70)
            draw_car(fg, col, x, 5, ROAD_Y, dist=sc + x, lights=True)
            if t >= ts + 0.3:
                kk = popin(t, ts + 0.3, 0.2)
                blit(fg, fx.big('tag', 'HYBRID', '#e8fff0', '#3cc85a', s=5), x, ROAD_Y - 250, kk, kk, -4, anchor='center')
    headlights(fg, lead_x + 270, ROAD_Y - 80)
    blit(fg, up(hybrid(int(sc) % 360 // 30 * 30), 5), lead_x, ROAD_Y)
    dg.label(fg, t, 14.4, 'THE ORIGINAL', (lead_x, ROAD_Y - 220), (760, 760), '#ffd23f', '#1a1a2e', '#e8b923', s=7)
    if t >= 15.69:
        fx.sparkles(fg, t, lead_x, ROAD_Y - 120, 500, 200, n=8, seed=50)
        fx.gsparkles(fg, t, 540, 600, 900, 300, n=8, seed=51)
    fx.burst(fg, t, 15.69, 540, 520, (60, 200, 90), n=14, seed=52)
    if t >= 15.69:
        k = popin(t, 15.69, 0.25)
        blit(fg, fx.big('badge', 'OWES IT SOMETHING', '#7fe3a0', '#1a1a2e', '#3cc85a', s=6), 540, 520, k, k, -3, anchor='center')
    P5.draw(fg, t)
    ROAD.reflect(img, fg)
    return finish(img, fg, CAM5, t, rim=False)


shot_teaser, TEASE_CUES = kit.teaser(16.5, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_merge), (1.9, shot_launch), (6.6, shot_gear), (9.9, shot_line), (13.6, shot_today), (16.5, shot_teaser)]
TRANS = {1: (1.9, 2.1, 'iris', (MX, MY)), 2: (6.6, 6.8, 'whip', dict(dx=1)), 3: (9.9, 10.1, 'push', None),
         4: (13.6, 13.8, 'whip', dict(dx=-1)), 5: (16.5, 16.7, 'whip', dict(dx=1))}
KEYCOL = {'1997': GRN, 'prius': YEL, 'japan': YEL, 'first': YEL, 'hybrid': GRN, 'petrol': RED, 'two': YEL, 'motors': YEL,
          '1998': YEL, '20,000': RED, 'alone': YEL, 'something': YEL}
CUES = [
    (0.0, 'whoosh', 0.6), (0.05, 'pop', 0.6), (0.25, 'pop', 0.5), (0.45, 'pop', 0.5), (0.51, 'stamp', 0.6), (0.3, 'vroom', 0.4),
    (MERGE_T, 'boom', 0.8), (MERGE_T + 0.01, 'ding', 0.8), (MERGE_T + 0.03, 'sparkle', 0.9),
    (1.95, 'fall', 0.5), (2.05, 'stamp', 0.7), (2.71, 'vroom', 0.6), (3.0, 'pop', 0.6), (3.54, 'pop', 0.6), (4.85, 'stamp', 0.6),
    (5.27, 'pop', 0.6), (5.87, 'confetti', 0.7), (5.89, 'ding', 0.6),
    (6.9, 'pop', 0.5), (7.23, 'pop', 0.7), (7.4, 'vroom', 0.4), (8.44, 'pop', 0.7), (8.61, 'pop', 0.7), (8.94, 'ding', 0.6), (9.22, 'click', 0.6),
    (9.24, 'sparkle', 0.6),
    (10.02, 'stamp', 0.6), (10.3, 'pop', 0.6)] + [(10.35 + i * 0.1, 'click', 0.25) for i in range(10)] + [
    (11.09, 'pop', 0.5), (11.34, 'cha_ching', 0.8), (11.36, 'confetti', 0.7), (12.79, 'stamp', 0.6),
    (13.65, 'vroom', 0.5), (14.0, 'pop', 0.4), (14.3, 'pop', 0.4), (14.4, 'pop', 0.6), (14.6, 'pop', 0.4), (15.69, 'ding', 0.8), (15.71, 'sparkle', 0.8),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
