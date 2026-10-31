"""Renders 'Cybertruck, bulletproof?': 3 mm stainless body, 9mm stopped, rifle rounds through, windows no help.

Template: videos/the-trabant (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). Results are from independent tests (INDEPENDENT TESTS tag); the
panels are shown on a test rig, with no shooter and no people in the line of fire. The truck and rocket are
generic pixel redraws with no badges or lettering.
Shots:
  1 hook     0.00  the wedge truck under a huge BULLETPROOF? sign with a bouncing red '?'; 'Not quite.'
  2 steel    2.10  a steel cross-section with a ruler: 3 MM; 'stainless steel'; a silver rocket lifts off: SAME ALLOY
  3 9mm      5.45  test rig panel: INDEPENDENT TESTS; two small rounds bounce off with sparkles; 'resisted 9mm'
  4 rifle    8.60  a rifle round punches through the outer skin of the cross-section; 'rifle rounds got through'
  5 windows 11.00  side glass cracks through; NO REAL PROTECTION
  6 verdict 13.30  back to the sign: NOT QUITE stamps over it
  7 teaser  15.20  shared NEXT EPISODE ending
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
Q_END = kit.at(NEW, 'its') - 0.2                    # cuts follow the read: question / body / question
BODY_END = kit.at(NEW, 'so') - 0.12
END_T = NEW[-1]['e'] + 0.3
DUR = END_T + 1.0
STEEL, STEEL_HI, STEEL_LO = (186, 190, 196), (224, 228, 234), (140, 144, 152)
GLASS = (46, 56, 72)
FRONT_WIN = [(60, 8), (88, 17), (88, 19), (60, 19)]
REAR_WIN = [(32, 14), (56, 8), (56, 19), (32, 19)]


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def truck(spin=0):
    """Angular stainless pickup (110x44), nose right: one roof peak, flat brushed panels, light bar, square arches."""
    img = Image.new('RGBA', (110, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body = [(2, 22), (4, 18), (58, 4), (104, 20), (108, 24), (108, 33), (2, 33)]
    d.polygon(body, fill=STEEL); d.line(body[1:5], fill=STEEL_HI)
    for x in range(6, 106, 7): d.line([(x, 22), (x + 3, 32)], fill=(176, 180, 188))
    d.line([(2, 25), (108, 25)], fill=STEEL_LO)
    d.polygon(FRONT_WIN, fill=GLASS); d.polygon(REAR_WIN, fill=GLASS)
    d.line([(61, 9), (70, 12)], fill=(110, 130, 160)); d.line([(34, 14), (42, 12)], fill=(110, 130, 160))
    d.line([(96, 19), (108, 23)], fill=(240, 250, 255)); d.line([(2, 21), (6, 20)], fill=(224, 48, 58))
    for cx in (22, 88):
        d.polygon([(cx - 13, 33), (cx - 10, 24), (cx + 10, 24), (cx + 13, 33)], fill=(30, 31, 38))
        d.ellipse((cx - 9, 25, cx + 9, 43), fill=(22, 22, 28)); d.ellipse((cx - 5, 29, cx + 5, 39), fill=(120, 126, 138))
        for k in range(3):
            a = math.radians(spin + k * 120); d.line([(cx, 34), (cx + 4 * math.cos(a), 34 + 4 * math.sin(a))], fill=(60, 64, 76))
    return outline(img)


@lru_cache(None)
def section(hole=0.0, dents=0):
    """Panel cross-section (70x40): brushed outer skin 3 grid px thick over a gap and an inner layer.
    hole > 0 punches the outer skin; dents (0..2) leaves shallow dimples."""
    img = Image.new('RGBA', (70, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 4, 69, 10), fill=STEEL); d.line([(0, 4), (69, 4)], fill=STEEL_HI); d.line([(0, 10), (69, 10)], fill=STEEL_LO)
    for x in range(0, 70, 5): d.line([(x, 5), (x + 2, 9)], fill=(206, 210, 216))
    d.rectangle((0, 26, 69, 30), fill=(110, 116, 128)); d.line([(0, 26), (69, 26)], fill=(150, 156, 168))
    for x in range(4, 70, 10): d.rectangle((x, 11, x + 1, 25), fill=(80, 84, 96))
    for i in range(dents): d.ellipse((18 + i * 18, 3, 24 + i * 18, 6), fill=(150, 154, 162))
    if hole > 0:
        w = int(2 + 3 * hole); d.rectangle((44 - w, 3, 44 + w, 11), fill=(0, 0, 0, 0))
        for k in range(3): d.line([(44 - w - 1, 4 + k * 3), (44 - w - 3, 2 + k * 3)], fill=STEEL_HI)
    return outline(img)


@lru_cache(None)
def rocket(flame=0):
    """Generic stainless rocket (24x80): nose, two flaps, three engine bells; flame flickers by phase."""
    img = Image.new('RGBA', (32, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(8, 14), (16, 0), (24, 14)], fill=STEEL); d.rectangle((8, 14, 24, 76), fill=STEEL)
    d.line([(9, 14), (9, 76)], fill=STEEL_HI); d.line([(23, 14), (23, 76)], fill=STEEL_LO)
    for y in range(20, 76, 8): d.line([(8, y), (24, y)], fill=(170, 174, 182))
    d.polygon([(8, 18), (3, 26), (8, 28)], fill=(120, 124, 132)); d.polygon([(24, 18), (29, 26), (24, 28)], fill=(120, 124, 132))
    d.polygon([(8, 64), (2, 76), (8, 76)], fill=(120, 124, 132)); d.polygon([(24, 64), (30, 76), (24, 76)], fill=(120, 124, 132))
    for x in (11, 16, 21): d.rectangle((x - 2, 76, x + 1, 79), fill=(60, 64, 76))
    L = 12 + (flame % 3) * 4
    d.polygon([(9, 80), (23, 80), (16, 80 + L)], fill=(255, 160, 40)); d.polygon([(12, 80), (20, 80), (16, 80 + L * 0.6)], fill=(255, 240, 160))
    return outline(img)


@lru_cache(None)
def round_(rifle=False):
    """Small projectile (10x6) or a longer pointed rifle round (18x6), pointing right."""
    w = 18 if rifle else 10
    img = Image.new('RGBA', (w, 6), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 1, w - 5, 4), fill=(200, 150, 60)); d.polygon([(w - 5, 0), (w - 1, 2), (w - 1, 3), (w - 5, 5)], fill=(176, 120, 60))
    d.line([(1, 1), (w - 6, 1)], fill=(240, 200, 120))
    return outline(img)


@lru_cache(None)
def ruler():
    img = Image.new('RGBA', (16, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 15, 49), fill=(255, 210, 63)); d.line([(0, 0), (0, 49)], fill=(255, 238, 160))
    for y in range(2, 49, 3): d.line([(9 if y % 15 == 2 else 12, y), (15, y)], fill=(26, 26, 46))
    return outline(img)


@lru_cache(None)
def sign():
    """BULLETPROOF? board on two posts."""
    from pixanim.grid import Grid, text_width
    tw = text_width('BULLETPROOF'); g = Grid(tw + 12, 15)
    g.rect(0, 0, tw + 11, 14, '#1a1a2e'); g.rect(1, 1, tw + 10, 13, '#fff6e0'); g.text(6, 4, 'BULLETPROOF', '#1a1a2e')
    return g.image()


def win_cracks(fg, ox, oy, s, hits, k):
    d = ImageDraw.Draw(fg)
    for n, (hx, hy) in enumerate(hits):
        cx, cy = ox + hx * s, oy + hy * s; r = fx.rng(10 + n)
        if k <= n * 0.3: continue
        d.ellipse((cx - 14, cy - 10, cx + 14, cy + 10), fill=(12, 14, 20, 255))
        for i in range(8):
            a = i * 0.8 + r.uniform(-0.3, 0.3); L = r.uniform(50, 110)
            d.line([(cx, cy), (cx + math.cos(a) * L, cy + math.sin(a) * L * 0.6)], fill=(230, 240, 255, 255), width=4)


# ================================================================== shot 1: hook, BULLETPROOF?
def sign_scene(fg, t, t0, tx=540, s=7):
    truck_img = up(truck(0), s); fg.paste(truck_img, (int(tx - truck_img.width / 2), GROUND - truck_img.height), truck_img)
    fx.contact_shadow(fg, tx, GROUND, 110 * s * 0.85, s=s)
    k = popin(t, t0, 0.3)
    blit(fg, up(sign(), 7), 440, 840, k, k, -3 + 1.5 * math.sin(t * 3), anchor='center')
    kq = popin(t, t0 + 0.15, 0.3) * (1 + 0.12 * math.sin(t * 9))
    blit(fg, fx.big('glyph', '?', '#e0303a', s=24), 820, 820 - 30 * abs(math.sin(t * 5)), kq, kq, 10 * math.sin(t * 4), anchor='center')
    fx.burst(fg, t, t0 + 0.15, 820, 820, RED, n=14, seed=1)


CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.26)), (0.0, (540, 960, 1.26)), (0.8, (560, 920, 1.08), 'io'), (2.1, (560, 920, 1.14), 'io')],
              kicks=[(0.1, 0.14, 540, 840), (0.3, 0.16, 900, 820), (0.86, 0.1, 540, 1000)], shakes=[(0.3, 0.25, 10)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    for sx_ in (220, 860): fx.rays(fg, t, 0.1, sx_, 300, (255, 240, 210), hold=True, r=700, n=6)
    sign_scene(fg, t, 0.05)
    fx.sparkles(fg, t, 540, 900, 900, 400, n=6, seed=2)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, Q_END - 0.1, 'Is it', WHITE, 480, 140, -3)
    title(cv, t, 0.25, Q_END - 0.1, 'bulletproof?', RED, 610, 140, 3)
    to = WARP(t)
    if Q_END <= t < BODY_END:
        title(cv, to, 2.22, 3.45, '3 mm stainless steel', YEL, 520, 88, 2)
        title(cv, to, 6.82, 8.5, 'resisted 9mm', GRN, 480, 130, -2)
        title(cv, to, 8.92, 10.9, 'rifle rounds', RED, 480, 120, 2)
        title(cv, to, 9.1, 10.9, 'got through', RED, 610, 120, -2)
    kit.photo_hq(cv, t, Q_END + 0.15, Q_END + 0.85, 'cybertruck', 540, 980, 600, 3, 'A PRODUCTION TRUCK')
    title(cv, t, BODY_END + 0.05, END_T - 0.1, 'So, would you', WHITE, 480, 120, -2)
    title(cv, t, BODY_END + 0.25, END_T - 0.1, 'still buy one?', YEL, 610, 130, 2)


# ================================================================== shot 2: 3 mm stainless, same as the rocket
SX = 500
CAM2 = Camera(W, H, [(2.1, (540, 920, 1.12)), (2.62, (520, 900, 1.16), 'io'), (3.52, (560, 900, 1.04), 'io'), (4.83, (600, 840, 1.1), 'io'), (5.45, (600, 840, 1.12))],
              kicks=[(2.22, 0.12, SX, 900), (2.62, 0.14, 300, 900), (3.52, 0.12, 540, 600), (4.23, 0.2, 820, 900), (4.83, 0.12, 820, 600)], shakes=[(4.23, 1.0, 6)])


def shot_steel(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 2.15, 0.3)
    blit(fg, up(section(), 9), SX, 1180, k, k, 0)
    if t >= 2.4:
        kr = popin(t, 2.4, 0.25)
        blit(fg, up(ruler(), 6), SX - 330, 1000, kr, kr, 0, anchor='center')
        d = ImageDraw.Draw(fg)
        d.line([(SX - 290, 1180 - 36 * 9), (SX - 200, 1180 - 36 * 9)], fill=(255, 210, 63, 255), width=5)
        d.line([(SX - 290, 1180 - 30 * 9), (SX - 200, 1180 - 30 * 9)], fill=(255, 210, 63, 255), width=5)
        blit(fg, fx.big('badge', '3 MM', '#ffd23f', '#1a1a2e', '#e8b923', s=10), SX - 180, 680, kr, kr, -4, anchor='center')
    dg.label(fg, t, 2.62, 'STAINLESS', (SX + 100, 1180 - 34 * 9), (SX + 160, 700), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=3.45)
    if t >= 3.52:                                         # the same alloy: a silver rocket lifts off beside it
        lift = ic(prog(t, 4.23, 1.4)) * 900
        blit(fg, up(rocket(int(t * 16)), 8), 840, GROUND + 100 - lift, popin(t, 3.52), popin(t, 3.52))
        if t >= 4.23:
            for kk in range(6): fx.puff(fg, t, 4.23 + kk * 0.12, 840, GROUND, seed=20 + kk, life=0.9, size=1.2, drift=((kk - 3) * 80, -60))
        k2 = popin(t, 3.52, 0.25)
        blit(fg, fx.big('tag', 'SAME ALLOY', '#fff6e0', '#1a1a2e', s=8), 420, 560, k2, k2, -4, anchor='center')
        fx.sparkles(fg, t, 840, 700, 300, 600, n=6, seed=21)
    if t >= 4.83:
        k = popin(t, 4.83, 0.25)
        blit(fg, fx.big('badge', 'STARSHIP', '#ffffff', '#1a1a2e', '#d6d9e2', s=9), 640, 720, k, k, 3, anchor='center')
        fx.burst(fg, t, 4.83, 640, 720, GLOW, n=12, seed=22)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: 9mm rounds bounce off
PX = 640
SHOTS9 = (6.82, 7.28)
def rig(fg, t, dents=0, hole=0.0):
    d = ImageDraw.Draw(fg)
    d.rectangle((PX - 20, GROUND - 40, PX + 20, GROUND), fill=(60, 120, 90, 255))
    blit(fg, up(section(hole, dents).rotate(90, expand=True), 9), PX, GROUND - 40)
CAM3 = Camera(W, H, [(5.45, (560, 900, 1.06)), (6.18, (540, 880, 1.1), 'io'), (6.82, (600, 900, 1.18), 'io'), (8.6, (580, 900, 1.14), 'io')],
              kicks=[(5.71, 0.1, 300, 640), (6.82, 0.18, PX, 900), (7.28, 0.18, PX, 900), (8.06, 0.12, 540, 600)], shakes=[(6.82, 0.2, 12), (7.28, 0.2, 12)])


def shot_9mm(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    dents = sum(t >= s0 for s0 in SHOTS9)
    rig(fg, t, dents)
    for n, s0 in enumerate(SHOTS9):
        y = 860 + n * 120; hx = PX - 6 * 9 * 0 - 130
        if s0 - 0.25 <= t < s0:
            u = prog(t, s0 - 0.25, 0.25); blit(fg, up(round_(), 7), lerp(-60, hx, u), y, 1, 1, 0, anchor='center')
        elif s0 <= t < s0 + 0.6:
            u = prog(t, s0, 0.6); blit(fg, up(round_(), 7), hx - 260 * u, y + 500 * u * u, 1, 1, 200 * u, anchor='center')
        if t >= s0:
            fx.burst(fg, t, s0, hx, y, GLOW, n=12, r0=40, r1=200, seed=30 + n); fx.glint(fg, t, s0, hx, y, r=110)
            fx.sparkles(fg, t, hx, y, 260, 200, n=5, seed=32 + n)
    if t >= 5.71:
        k = popin(t, 5.71, 0.25)
        blit(fg, fx.big('tag', 'INDEPENDENT TESTS', '#fff6e0', '#1a1a2e', s=6), 400, 600, k, k, -4, anchor='center')
    if t >= 8.06:
        k = fx.slam(t, 8.06) * popin(t, 8.06, 0.2)
        blit(fg, fx.big('check', s=12), 880, 760, k, k, 6, anchor='center'); fx.burst(fg, t, 8.06, 880, 760, (60, 200, 90), n=14, seed=34)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: rifle rounds get through the outer layer
PIERCE = 9.83
CAM4 = Camera(W, H, [(8.6, (540, 920, 1.14)), (9.27, (480, 900, 1.22), 'io'), (PIERCE, (540, 960, 1.3), 'io'), (11.0, (540, 960, 1.22), 'io')],
              kicks=[(8.92, 0.12, 300, 1000), (PIERCE, 0.26, 540, 1000), (10.38, 0.14, 540, 760)], shakes=[(PIERCE, 0.4, 16)])


def shot_rifle(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    hole = oc(prog(t, PIERCE, 0.2)) if t >= PIERCE else 0
    blit(fg, up(section(hole, 2), 10), 540, 1240)
    hx, hy = 540 + (44 - 35) * 10, 1240 - 40 * 10 + 7 * 10
    if t < PIERCE:
        u = prog(t, PIERCE - 0.6, 0.6)
        if u > 0: blit(fg, up(round_(True), 7), hx, lerp(200, hy, u), 1, 1, -90, anchor='center'); fx.speed_lines(fg, 0.6, 3, horizontal=False, col=(200, 204, 220))
    else:
        u = prog(t, PIERCE, 0.4)
        if u < 1: blit(fg, up(round_(True), 7), hx, lerp(hy, hy + 150, u), 1, 1, -90, anchor='center')
        fx.burst(fg, t, PIERCE, hx, hy, (255, 160, 40), n=16, seed=40); fx.ring(fg, t, PIERCE, hx, hy, (255, 160, 40), r1=300)
        fx.dust(fg, t, PIERCE, hx, hy, n=12, seed=41, col=(224, 228, 234))
    dg.label(fg, t, 10.38, 'OUTER LAYER', (hx - 200, hy), (300, 760), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    if t >= 10.56:
        k = fx.slam(t, 10.56) * popin(t, 10.56, 0.2)
        blit(fg, fx.big('xmark', s=12), 860, 760, k, k, -6, anchor='center'); fx.burst(fg, t, 10.56, 860, 760, RED, n=14, seed=42)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the windows
HITS = [(70, 14), (78, 16), (46, 13)]
CAM5 = Camera(W, H, [(11.0, (560, 920, 1.12)), (11.33, (640, 880, 1.3), 'io'), (12.46, (560, 900, 1.2), 'io'), (13.3, (560, 900, 1.24))],
              kicks=[(11.75, 0.14, 700, 860), (11.95, 0.14, 760, 880), (12.46, 0.14, 460, 860), (12.7, 0.16, 540, 640)])


def shot_windows(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    s = 8; tr = up(truck(0), s); ox, oy = 540 - tr.width / 2, GROUND - tr.height
    fg.paste(tr, (int(ox), int(oy)), tr); fx.contact_shadow(fg, 540, GROUND, 760, s=8)
    k = clamp((t - 11.6) / 0.9)
    win_cracks(fg, ox, oy, s, HITS, k)
    for n, (hx, hy) in enumerate(HITS):
        t0 = 11.6 + n * 0.27
        if t >= t0: fx.burst(fg, t, t0, ox + hx * s, oy + hy * s, (220, 236, 255), n=10, r0=40, r1=180, seed=50 + n); fx.glint(fg, t, t0, ox + hx * s, oy + hy * s, r=90)
    if t >= 12.7:
        k = fx.slam(t, 12.7) * popin(t, 12.7, 0.2)
        blit(fg, fx.big('badge', 'NO REAL PROTECTION', '#e0303a', '#ffffff', '#b8222c', s=7), 540, 640, k, k, -5, anchor='center')
    dg.label(fg, t, 11.33, 'WINDOWS', (ox + 74 * s, oy + 12 * s), (820, 700), '#7fd4ff', '#1a1a2e', '#3c9ad8', s=7, t1=12.6)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: verdict
NOTQ = 14.54
P6 = Presenter([
    (13.3, dict(path=Track([(13.3, (-200, 400)), (13.7, (140, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (13.7, dict(ground=GROUND, squash=True, arms='point', point=(480, 840), look=(480, 840), expr='think', face=None)),
    (NOTQ, dict(arms='shrug', point=None, look=None, look_camera=True, expr='smirk', squash=True)),
], words=WORDS, base_size=7)
CAM6 = Camera(W, H, [(13.3, (560, 920, 1.12)), (13.77, (560, 880, 1.18), 'io'), (NOTQ, (540, 880, 1.24), 'io'), (15.2, (540, 900, 1.2), 'io')],
              kicks=[(13.77, 0.14, 480, 840), (NOTQ, 0.24, 540, 900)], shakes=[(NOTQ, 0.3, 12)])


def shot_verdict(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    sign_scene(fg, t, 13.4, tx=600, s=7)
    if t >= NOTQ:
        k = popin(t, NOTQ, 0.25)
        blit(fg, fx.big('tag', 'STILL BUY ONE?', '#fff6e0', '#1a1a2e', s=8), 560, 1060, k, k, -6 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, NOTQ, 560, 1060, GLOW, n=12, seed=70)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


# ================================================================== new read: question (the sign), body on the first read's timing, question
BODY = [p for p in kit.word_pairs(NEW, WORDS) if Q_END < p[0] < BODY_END - 0.3 and p[1] >= 2.6]
ANCH = [(0.0, -0.2), (Q_END, 2.0), (Q_END + 0.01, 2.05), (kit.at(NEW, '3', 0), 2.38)] + BODY + [(BODY_END - 0.01, 13.25), (BODY_END, 13.35), (END_T + 0.2, 15.0)]
WARP, N = kit.warp(ANCH), kit.unwarp(ANCH[3:-2])
shot_teaser, TEASE_CUES = kit.teaser(END_T, NEW)

# ================================================================== shots + transitions
SHOTS = [(-1.0, kit.retime(shot_hook, WARP)), (Q_END, kit.retime(shot_steel, WARP)), (N(5.45), kit.retime(shot_9mm, WARP)),
         (N(8.6), kit.retime(shot_rifle, WARP)), (N(11.0), kit.retime(shot_windows, WARP)), (BODY_END, kit.retime(shot_verdict, WARP)), (END_T, shot_teaser)]
TRANS = {1: (Q_END, Q_END + 0.2, 'iris', (480, 840)), 2: (N(5.45), N(5.45) + 0.2, 'whip', dict(dx=1)), 3: (N(8.6), N(8.6) + 0.2, 'push', None),
         4: (N(11.0), N(11.0) + 0.2, 'whip', dict(dx=0, dy=1)), 5: (BODY_END, BODY_END + 0.2, 'push', None), 6: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'bulletproof?': RED, '3': YEL, 'stainless': YEL, 'alloy': YEL, 'starship.': YEL, 'independent': YEL, '9mm': GRN, 'rifle': RED, 'outer': RED,
          'windows': YEL, 'protection.': RED}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'stamp', 0.6), (0.2, 'pop', 0.7), (0.3, 'boom', 0.4), (0.32, 'sparkle', 0.5), (0.86, 'click', 0.4),
    (2.15, 'thump', 0.6), (2.4, 'pop', 0.6), (2.62, 'pop', 0.5), (2.7, 'pop', 0.4), (3.52, 'pop', 0.6), (4.23, 'vroom', 0.9), (4.25, 'boom', 0.3),
    (4.83, 'ding', 0.6),
    (5.71, 'stamp', 0.6), (SHOTS9[0] - 0.25, 'whoosh', 0.5), (SHOTS9[0], 'coin', 0.9), (SHOTS9[0] + 0.02, 'sparkle', 0.7),
    (SHOTS9[1] - 0.25, 'whoosh', 0.5), (SHOTS9[1], 'coin', 0.9), (SHOTS9[1] + 0.02, 'sparkle', 0.7), (8.06, 'ding', 0.9),
    (PIERCE - 0.6, 'whoosh', 0.7), (PIERCE, 'crash', 0.9), (PIERCE + 0.02, 'boom', 0.4), (10.38, 'pop', 0.6), (10.56, 'buzzer', 0.7),
    (11.33, 'pop', 0.5), (11.6, 'crash', 0.6), (11.87, 'crash', 0.5), (12.14, 'crash', 0.5), (12.7, 'stamp', 0.8),
    (13.4, 'pop', 0.6), (13.55, 'pop', 0.6), (13.7, 'thump', 0.4), (NOTQ, 'stamp', 1.0), (NOTQ + 0.02, 'buzzer', 0.4),
]
CUES = kit.warp_cues(CUES, ANCH, END_T) + [(BODY_END + 0.05, 'pop', 0.6)] + TEASE_CUES

kit.setup(HERE, NEW, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True,
          end=('car stuff, explained', 'tell me in the comments'))

if __name__ == '__main__':
    kit.main()
