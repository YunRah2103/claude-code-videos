"""Renders 'Bugatti, on an envelope': a 16-cylinder idea reportedly sketched in 1997, running by 2001.

Template: videos/the-trabant (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). The envelope sketch is hedged (REPORTEDLY); the 2001 output is
'about' 1,000 hp (the brief gives about 1,000 PS). No brand marks on screen: the engine is a generic pixel W16.
Shots:
  1 envelope  0.00  an envelope unfolds and a pencil sketch slides out; 1997; 'Drawn on an envelope'; REPORTEDLY
  2 sketch    2.60  the sketch fills the frame: sixteen circles pencil in, in a W; 16-CYLINDER; ENVELOPE stamp
  3 turbos    5.10  four pixel turbochargers pop in round the engine and spool up; 4 TURBOS
  4 W16       6.40  the W-shaped engine assembles, cylinders light up in turn; 'Sixteen cylinders'; a giant W
  5 2001      8.40  a 2001 banner unrolls over a test stand; the power counter runs to about 1,000 HP
  6 back     12.50  he flips the envelope: the sketch on the back sparkles; photo of the finished engine
  7 teaser   15.20  shared NEXT EPISODE ending
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

WORDS = kit.load_words(HERE)
DUR, END_T = 17.2, 15.3
PENCIL = (60, 90, 170)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def envelope(flap=0.0, back=False):
    """Cream envelope (60x40). flap 0 = closed (point down), 1 = open (point up). back=True shows the sketched rear."""
    img = Image.new('RGBA', (60, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 24, 59, 63), fill=(240, 230, 204)); d.line([(0, 24), (59, 24)], fill=(252, 246, 228))
    d.polygon([(0, 63), (30, 44), (59, 63)], fill=(226, 214, 184)); d.line([(0, 63), (30, 44), (59, 63)], fill=(206, 192, 160))
    if back: _doodle(d, 8, 30, 44, 26, 1.0)
    else:
        d.rectangle((46, 28, 54, 36), fill=(214, 48, 58)); d.rectangle((48, 30, 52, 34), fill=(255, 220, 140))   # stamp
        for y in (46, 50, 54): d.line([(10, y), (34, y)], fill=(170, 160, 140))
    fy = 24 + 18 * (1 - 2 * flap)                     # flap tip moves from inside (y 42) to above (y 6)
    d.polygon([(0, 24), (59, 24), (30, fy)], fill=(232, 220, 190)); d.line([(0, 24), (30, fy), (59, 24)], fill=(200, 186, 150))
    return outline(img)


def _doodle(d, x0, y0, w, h, p):
    """Pencil W16 doodle: a crank circle, four banks fanning into a W, sixteen little circles; p reveals it."""
    cx, cy = x0 + w / 2, y0 + h - 3
    d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), outline=PENCIL)
    for b, ang in enumerate((-62, -22, 22, 62)):
        if p < b * 0.2: continue
        a = math.radians(ang); L = h * 0.9 * min(1, (p - b * 0.2) / 0.2)
        d.line([(cx, cy), (cx + L * math.sin(a), cy - L * math.cos(a))], fill=PENCIL)
        for k in range(4):
            if p < 0.8 + k * 0.05 and p < 1: continue
            r = h * (0.35 + 0.17 * k); px, py = cx + r * math.sin(a), cy - r * math.cos(a)
            d.ellipse((px - 1.5, py - 1.5, px + 1.5, py + 1.5), outline=PENCIL)


@lru_cache(None)
def sketch(p=1.0):
    """Big sheet (110x80) with the doodle drawn to progress p, plus '16 CYL' scribble."""
    img = Image.new('RGBA', (110, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 109, 79), fill=(244, 236, 212))
    for y in range(8, 80, 8): d.line([(2, y), (107, y)], fill=(222, 214, 196))
    d.line([(10, 0), (10, 79)], fill=(230, 160, 160))
    _doodle(d, 18, 8, 74, 66, p)
    if p >= 1:
        for x in range(80, 100, 3): d.line([(x, 70), (x + 2, 72)], fill=PENCIL)
    return outline(img)


@lru_cache(None)
def turbo(ang=0):
    """Turbocharger (30x26): snail housing with a spinning compressor wheel, inlet flange."""
    img = Image.new('RGBA', (30, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 25, 25), fill=(170, 176, 188)); d.arc((2, 2, 25, 25), 180, 300, fill=(220, 226, 236))
    d.rectangle((20, 4, 29, 10), fill=(150, 156, 170))
    d.ellipse((8, 8, 19, 19), fill=(60, 64, 76))
    for k in range(6):
        a = math.radians(ang + k * 60)
        d.line([(13.5, 13.5), (13.5 + 5 * math.cos(a), 13.5 + 5 * math.sin(a))], fill=(214, 220, 230))
    d.ellipse((12, 12, 15, 15), fill=(240, 200, 60))
    return outline(img)


BANKS = (-62, -22, 22, 62)
@lru_cache(None)
def w16(lit=-1, ph=0):
    """Front view W16 (100x70): crankcase, four cylinder banks fanned into a W, 4 lamps per bank; cylinder `lit`
    (0..15) glows, plus the previous two dimmer."""
    img = Image.new('RGBA', (100, 74), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy = 50, 62
    d.rounded_rectangle((26, 54, 74, 72), 4, fill=(110, 116, 128)); d.line([(26, 54), (74, 54)], fill=(160, 166, 178))
    for b, ang in enumerate(BANKS):
        a = math.radians(ang); ux, uy = math.sin(a), -math.cos(a); nx, ny = -uy, ux
        pts = [(cx + nx * 6, cy + ny * 6), (cx + ux * 56 + nx * 6, cy + uy * 56 + ny * 6), (cx + ux * 56 - nx * 6, cy + uy * 56 - ny * 6), (cx - nx * 6, cy - ny * 6)]
        d.polygon(pts, fill=(150, 156, 168)); d.line(pts[1:3], fill=(214, 48, 58), width=3)
        for k in range(4):
            i = b * 4 + k; r = 22 + 9 * k
            px, py = cx + ux * r, cy + uy * r
            hot = 1.0 if i == lit else 0.5 if lit >= 0 and i in ((lit - 1) % 16, (lit - 2) % 16) else 0
            col = (255, 230, 90) if hot == 1 else (230, 140, 50) if hot else (60, 64, 76)
            d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=col)
    d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(70, 74, 86))
    a = math.radians(ph * 45); d.line([(cx, cy), (cx + 5 * math.cos(a), cy + 5 * math.sin(a))], fill=(220, 224, 232), width=2)
    return outline(img)


@lru_cache(None)
def banner(txt, u=1.0):
    """Red ribbon banner that unrolls from the centre (u 0..1)."""
    full = fx.big('badge', txt, '#e0303a', '#ffffff', '#b8222c', s=1)
    w = max(2, int(full.width * u)); return full.crop(((full.width - w) // 2, 0, (full.width + w) // 2, full.height))


# ================================================================== shot 1: hook, the envelope
EX, EY = 540, 1060
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.3)), (0.0, (540, 960, 1.3)), (0.7, (540, 940, 1.14), 'io'), (2.6, (540, 900, 1.2), 'io')],
              kicks=[(0.2, 0.12, EX, EY), (0.9, 0.12, EX, 760), (2.21, 0.1, 800, 820)], shakes=[(0.2, 0.2, 8)])


def shot_envelope(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fl = oc(prog(t, 0.2, 0.4))
    out = oc(prog(t, 0.6, 0.45))
    if out > 0:                                       # sketch rises out of the envelope, behind its front
        k = 0.35 + 0.12 * out
        blit(fg, up(sketch(clamp((t - 0.7) / 1.2)), 9), EX, EY - 60 - 200 * out, k, k, -4 * out, anchor='bottom')
    blit(fg, up(envelope(fl), 8), EX, EY + 200, 1, 1, 2 * math.sin(t * 3))
    if t >= 0.9: fx.sparkles(fg, t, EX, EY - 300, 600, 300, n=7, seed=1)
    fx.ring(fg, t, 0.2, EX, EY, GLOW, r1=420)
    if t >= 0.14:
        k = popin(t, 0.14, 0.25)
        blit(fg, fx.big('badge', '1997', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), 300, 820, k, k, -6, anchor='center')
    if t >= 2.21:
        k = popin(t, 2.21, 0.25)
        blit(fg, fx.big('tag', 'REPORTEDLY', '#fff6e0', '#e8a000', s=7), 760, 840, k, k, 5, anchor='center')
        fx.burst(fg, t, 2.21, 760, 840, GLOW, n=10, seed=2)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.5, 'Drawn on', YEL, 380, 130, -3)
    title(cv, t, 0.3, 2.5, 'an envelope', YEL, 520, 120, 2)
    title(cv, t, 6.52, 8.35, 'Sixteen cylinders', GRN, 470, 110, -3)
    title(cv, t, 11.04, 12.45, 'about 1,000 horsepower', RED, 470, 96, 2)


# ================================================================== shot 2: the sketch
P2 = Presenter([
    (2.55, dict(path=Track([(2.55, (1300, 300)), (2.95, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.95, dict(ground=GROUND, squash=True, arms='point', point=(480, 800), look=(480, 800), expr='smile', face=None)),
    (3.89, dict(arms=('aim', -30), expr='wow', squash=True)),
    (4.49, dict(arms='thumb', look=None, look_camera=True, expr='grin')),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.6, (540, 860, 1.1)), (3.07, (480, 820, 1.24), 'io'), (4.49, (540, 880, 1.14), 'io'), (5.1, (540, 880, 1.18))],
              kicks=[(2.65, 0.08, 480, 800), (3.07, 0.12, 480, 760), (3.89, 0.1, 480, 760), (4.49, 0.16, 800, 1080)], shakes=[(4.5, 0.25, 10)])


def shot_sketch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    p = clamp((t - 2.65) / 1.3)
    blit(fg, up(sketch(round(p * 40) / 40), 8), 480, 1120, 1, 1, -2 + math.sin(t * 2), anchor='bottom')
    if p < 1:                                          # pencil tip follows the drawing
        a = math.radians(BANKS[min(3, int(p * 5))]); r = 360 * ((p * 5) % 1)
        tx, ty = 480 + r * math.sin(a), 1060 - r * math.cos(a)
        ImageDraw.Draw(fg).line([(tx, ty), (tx + 90, ty - 160)], fill=(240, 196, 60), width=22)
        ImageDraw.Draw(fg).polygon([(tx, ty), (tx + 10, ty - 30), (tx - 8, ty - 22)], fill=(40, 40, 50))
        fx.dust(fg, t, t - 0.05, tx, ty, n=3, seed=int(t * 30), col=(120, 140, 200), life=0.3)
    dg.label(fg, t, 3.07, '16-CYLINDER', (480, 700), (500, 470), '#ffffff', '#1a1a2e', '#d6d9e2', s=8)
    if t >= 4.49:
        fx.stamp_at(fg, t, 4.49, 'ON AN ENVELOPE', 800, 1080, rot=-8, s=7)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: four turbos
TPOS = [(270, 640), (810, 640), (270, 1080), (810, 1080)]
CAM3 = Camera(W, H, [(5.1, (540, 880, 1.16)), (5.46, (540, 860, 1.26), 'io'), (6.4, (540, 860, 1.3), 'io')],
              kicks=[(5.22, 0.12, 540, 860), (5.46, 0.14, 540, 860), (5.9, 0.08, 540, 860)])


def shot_turbos(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    blit(fg, up(w16(-1, int(t * 12) % 8), 6), 540, 1080, 1, 1, 0)
    for i, (x, y) in enumerate(TPOS):
        t0 = 5.22 + i * 0.12
        if t < t0: continue
        k = popin(t, t0, 0.25); spin = int((t - t0) ** 2 * 1800) % 360 // 15 * 15
        blit(fg, up(turbo(spin), 9), x, y + 6 * math.sin(t * 5 + i), k, k, 0, anchor='center')
        fx.burst(fg, t, t0, x, y, (120, 200, 255), n=8, r0=60, r1=200, seed=10 + i)
        if t > t0 + 0.4: fx.puff(fg, t, t0 + 0.4 + (int(t * 5) % 3) * 0.2, x, y - 100, seed=14 + i, life=0.6, size=0.6, drift=(0, -160), col=(200, 220, 255))
    if t >= 5.46:
        k = popin(t, 5.46, 0.25)
        blit(fg, fx.big('badge', '4 TURBOS', '#7fd4ff', '#1a1a2e', '#3c9ad8', s=11), 540, 420, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
        fx.sparkles(fg, t, 540, 860, 800, 600, n=8, seed=16)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: the W16 assembles and fires
def lit(t): return -1 if t < 7.0 else int((t - 7.0) * 18) % 16
CAM4 = Camera(W, H, [(6.4, (540, 900, 1.2)), (6.94, (540, 880, 1.1), 'io'), (7.76, (540, 860, 1.14), 'io'), (8.4, (540, 860, 1.18))],
              kicks=[(6.52, 0.14, 540, 900), (6.94, 0.1, 540, 900), (7.76, 0.2, 540, 700)], shakes=[(7.0, 1.4, 4)])


def shot_w16(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    u = oc(prog(t, 6.45, 0.5))
    for b in range(4):                                  # banks slide in from the four corners, then lock
        ox, oy = (-700, -400, 400, 700)[b] * (1 - u), -500 * (1 - u)
        if u < 1: blit(fg, up(w16(-1, 0), 8).crop((b * 200, 0, b * 200 + 200, 592)), 540 - 400 + b * 200 + 100 + ox, 1180 + oy, 1, 1, 0)
    if u >= 1:
        sh = 3 * math.sin(t * 70) if t >= 7.0 else 0
        blit(fg, up(w16(lit(t), int(t * 18) % 8), 8), 540 + sh, 1180, 1, 1, 0)
        fx.ring(fg, t, 6.95, 540, 900, GLOW, r1=520)
    if t >= 7.0: fx.sparkles(fg, t, 540, 900, 800, 500, n=8, seed=20)
    if t >= 7.76:
        k = fx.slam(t, 7.76) * popin(t, 7.76, 0.2)
        blit(fg, fx.big('glyph', 'W', '#ffd23f', s=24), 540, 600, k, k, 4 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 7.76, 540, 700, GLOW, n=16, seed=21)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: 2001, about 1,000 hp
def power(t): return int(1000 * oc(prog(t, 10.71, 1.1)))
P5 = Presenter([
    (8.35, dict(path=Track([(8.35, (-200, 400)), (8.75, (170, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (8.75, dict(ground=GROUND, squash=True, arms='point', point=(600, 500), look=(600, 500), expr='smile', face=None)),
    (11.28, dict(arms='cheer', point=None, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(8.4, (540, 900, 1.14)), (8.86, (560, 760, 1.24), 'io'), (10.71, (580, 900, 1.12), 'io'), (11.28, (580, 860, 1.22), 'io'), (12.5, (580, 860, 1.26))],
              kicks=[(8.86, 0.16, 600, 500), (10.71, 0.1, 620, 1000), (11.28, 0.2, 600, 760), (11.88, 0.1, 600, 760)], shakes=[(10.71, 1.7, 6)])


def shot_2001(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    d.rectangle((380, GROUND - 120, 860, GROUND - 100), fill=(60, 120, 90, 255))          # test stand
    for x in (400, 820): d.rectangle((x, GROUND - 100, x + 20, GROUND), fill=(60, 120, 90, 255))
    run = t >= 10.71
    blit(fg, up(w16(lit(t) if run else -1, int(t * 18) % 8), 6), 620 + (3 * math.sin(t * 70) if run else 0), GROUND - 120)
    if run:
        for k in range(8): fx.puff(fg, t, 10.75 + k * 0.25, 900, GROUND - 400, seed=30 + k, life=0.8, size=0.8, drift=(160, -260))
    if t >= 8.86:
        u = oc(prog(t, 8.86, 0.45)); k = popin(t, 8.86, 0.2) * popout(t, 10.95)
        blit(fg, up(banner('2001', u), 13), 600, 500, k, k, -3 + 2 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 8.86, 600, 500, RED, n=14, seed=31)
    dg.label(fg, t, 9.94, 'FIRST VERSION', (620, GROUND - 300), (820, 760), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=10.95)
    if t >= 11.04:
        k = popin(t, 11.04, 0.25); v = power(t)
        blit(fg, fx.big('badge', f'{v:,} HP', '#ffd23f', '#1a1a2e', '#e8b923', s=12), 600, 760, k, k, 2 * math.sin(t * 5), anchor='center')
        fx.sparkles(fg, t, 600, 760, 760, 240, n=7, seed=32)
    if t >= 11.88: fx.confetti(fg, t, 11.88, 600, 640, n=30, seed=33); fx.ring(fg, t, 11.88, 600, 760, GLOW)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: the back of an envelope
FLIP = 14.19
P6 = Presenter([
    (12.5, dict(path=Track([(12.5, (330, GROUND))]), size=8, legs='stand', arms='present', look=(680, 820), expr='talk', face=1, ground=GROUND)),
    (13.35, dict(arms='point', point=(680, 820), look=(680, 820), expr='smile')),
    (14.63, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=8)
CAM6 = Camera(W, H, [(12.5, (560, 900, 1.16)), (13.35, (600, 860, 1.24), 'io'), (FLIP, (600, 860, 1.3), 'io'), (15.2, (600, 880, 1.24), 'io')],
              kicks=[(12.67, 0.1, 680, 820), (FLIP, 0.18, 680, 820), (14.63, 0.14, 680, 820)])


def shot_back(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    f = prog(t, FLIP - 0.15, 0.3); sx = abs(math.cos(f * math.pi))
    blit(fg, up(envelope(0.0, back=f > 0.5), 8), 680, 980, max(0.04, sx), 1, -4 + 2 * math.sin(t * 2), anchor='center')
    if f > 0.5:
        fx.rays(fg, t, FLIP, 680, 1000, GLOW, hold=True, r=480)
        fx.sparkles(fg, t, 680, 1000, 640, 440, n=9, seed=40)
        fx.burst(fg, t, FLIP, 680, 1000, GLOW, n=16, seed=41)
    if t >= 13.35:
        k = popin(t, 13.35, 0.25) * popout(t, 14.0)
        blit(fg, fx.big('tag', 'BEST ENGINES', '#fff6e0', '#1a1a2e', s=8), 680, 560, k, k, 4, anchor='center')
    photo(fg, t, 12.67, 13.3, 'w16', 640, 860, 640, 460, -3, 'THE PRODUCTION W16', pix=4)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(15.2, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_envelope), (2.6, shot_sketch), (5.1, shot_turbos), (6.4, shot_w16), (8.4, shot_2001), (12.5, shot_back), (15.2, shot_teaser)]
TRANS = {1: (2.6, 2.8, 'push', None), 2: (5.1, 5.3, 'whip', dict(dx=1)), 3: (6.4, 6.6, 'iris', (540, 900)), 4: (8.4, 8.6, 'whip', dict(dx=0, dy=1)),
         5: (12.5, 12.7, 'push', None), 6: (15.2, 15.4, 'whip', dict(dx=1))}
KEYCOL = {'1997,': YEL, 'reportedly': YEL, '16-cylinder': YEL, 'envelope.': YEL, 'turbochargers.': GRN, 'cylinders,': GRN, 'w': YEL,
          '2001,': YEL, 'version': YEL, '1,000': RED, 'best': YEL, 'back': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (0.14, 'pop', 0.6), (0.2, 'creak', 0.6), (0.6, 'slide_down', 0.5), (0.9, 'sparkle', 0.6),
    (1.26, 'pop', 0.3), (2.21, 'stamp', 0.6),
    (2.65, 'click', 0.5), (3.07, 'pop', 0.6), (3.4, 'click', 0.4), (3.89, 'pop', 0.5), (4.49, 'stamp', 0.8),
    (5.22, 'pop', 0.6), (5.34, 'pop', 0.6), (5.46, 'pop', 0.6), (5.58, 'pop', 0.6), (5.5, 'whoosh', 0.6), (5.9, 'sparkle', 0.5),
    (6.45, 'whoosh', 0.5), (6.95, 'thump', 0.8), (7.0, 'vroom', 0.8), (7.76, 'stamp', 0.9), (7.78, 'sparkle', 0.7),
    (8.86, 'ding', 0.7), (9.94, 'pop', 0.6), (10.71, 'vroom', 1.0), (11.28, 'whoosh', 0.5), (11.88, 'confetti', 0.8), (11.9, 'ding', 0.8),
    (12.67, 'pop', 0.5), (13.35, 'pop', 0.6), (FLIP - 0.15, 'whoosh', 0.6), (FLIP, 'sparkle', 0.9), (14.63, 'ding', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
