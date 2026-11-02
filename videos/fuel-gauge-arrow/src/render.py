"""Renders 'Why is there an arrow on your fuel gauge?': the arrow next to the pump icon shows the fuel-cap side.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, mixer). Looping format: no outro
card; the last shot replays the cold open's run-up, so the last frame flows into frame 0. Voiceover: out/fuel-gauge-arrow/
voiceover.wav (clip 1 of out/voiceover/full_voiceover.wav, see voiceover.py); words.json is aligned to it.
Shots (v2: ~1.5 s beats, detailed worlds, choreographed presenter):
  1 pump     0.00  cold open: he rolls up, hops out, drags the nozzle over the roof to the wrong side, the hose snaps him back
  2 dash     2.55  the shared dashboard with a fuel dial: camera pushes into the dial, he flies in and points, the arrow glows;
                   'FUEL CAP SIDE' leader label; the real gauge photo pops in over it
  3 left     5.30  top-down forecourt: left-arrow inset, the red car pulls in, the left flap opens, the nozzle flies in
  4 right    6.95  same forecourt, right-arrow inset, the blue car, the right flap
  5 ask      8.60  'Did you already know that?': he shrugs to camera, big '?', YES / NO poll (mid-video comment prompt)
  6 right   10.10  side view: he pulls in on the correct side and plugs the nozzle in first time; share sticker
  7 loop    12.70  replays the cold-open run-up, so the last frame matches frame 0
"""
import math, os, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, draw_car, headline, sticker
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter, reach, Fn
from pixanim.guy import guy
from pixanim.dash import Dashboard, _gauge_face, _text, S as DS
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline
from pixanim.autos import ptext

WORDS = kit.load_words(HERE)
DUR = 13.4
END_T = 12.70                                          # loop pre-roll starts here (no end card)
def ws(i): return WORDS[i]['s']
HOOK = ((('Why is there an', None),), (('ARROW', '#ffd23f'), ('on', None)), (('your fuel gauge?', None),))
NOZ = (40, 42, 50)


# ------------------------------------------------------------------ side-view props (garage scale 9)
@lru_cache(None)
def pump(lit=0, holster=True):
    """Fuel pump (32x64): red cabinet with a lit price screen, keypad, canopy cap, hose holster on the left."""
    img = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((1, 0, 30, 7), fill=(240, 240, 236)); d.rectangle((1, 5, 30, 7), fill=(214, 48, 58)); d.line((2, 1, 29, 1), fill=WHITE)
    d.rectangle((4, 8, 27, 58), fill=(214, 48, 58)); d.rectangle((4, 8, 7, 58), fill=(240, 92, 100)); d.rectangle((23, 8, 27, 58), fill=(160, 30, 40))
    d.rectangle((8, 12, 22, 22), fill=(20, 24, 30))
    scr = (90, 220, 120) if lit else (60, 170, 90)
    d.rectangle((9, 13, 21, 21), fill=scr); d.line((10, 15, 19, 15), fill=(200, 255, 210)); d.line((10, 18, 16, 18), fill=(30, 90, 50))
    for i in range(3):
        for j in range(2): d.rectangle((9 + i * 4, 26 + j * 4, 11 + i * 4, 28 + j * 4), fill=(240, 240, 236))
    d.rectangle((9, 38, 22, 44), fill=(255, 217, 59)); d.rectangle((11, 40, 20, 42), fill=(214, 150, 20))
    d.rectangle((0, 30, 4, 42), fill=(46, 48, 56)); d.point((1, 31), fill=(110, 116, 128))
    if holster: d.rectangle((0, 33, 3, 40), fill=NOZ)
    d.rectangle((2, 58, 29, 63), fill=(120, 126, 138)); d.line((2, 58, 29, 58), fill=(176, 182, 192))
    return outline(img)


@lru_cache(None)
def nozzle(rot=0):
    """Pump nozzle (12x8), spout pointing right."""
    img = Image.new('RGBA', (12, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 1, 6, 5), fill=NOZ); d.rectangle((1, 2, 5, 3), fill=(90, 94, 106)); d.rectangle((2, 5, 4, 7), fill=NOZ)
    d.rectangle((6, 2, 11, 3), fill=(176, 182, 192)); d.point((11, 3), fill=(120, 126, 138))
    return outline(img)


@lru_cache(None)
def flap(open_=0.0):
    """Fuel flap (14x8) seen side-on: closed = yellow-lit square, open = swung out showing the black cap."""
    img = Image.new('RGBA', (14, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((6, 0, 13, 7), fill=(30, 30, 36)); d.ellipse((8, 2, 11, 5), fill=(90, 94, 104))
    if open_ < 0.5:
        d.rectangle((6, 0, 13, 7), fill=(255, 217, 59)); d.rectangle((7, 1, 12, 2), fill=(255, 240, 160))
    else:
        w = round(6 * open_); d.rectangle((6 - w, 0, 6, 7), fill=(255, 217, 59))
    return outline(img)


def head_in_car(fg, x, s, expr='grin'):
    """His head in the driver's window (side-on car facing right)."""
    g = up(guy(expr, 'down', 'stand', (1, 0)), s).crop((0, 0, 48 * s, 20 * s))
    blit(fg, g, x + 6 * s, GROUND - 31 * s, anchor='bottom')


def hose(fg, a, b, slack=120, taut=False, hot=False):
    """Rubber hose from a to b: a sagging curve when slack, a straight band when taut (glowing red just before it snaps)."""
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (0 if taut else slack))
    pts = [(lerp(lerp(a[0], mid[0], u), lerp(mid[0], b[0], u), u), lerp(lerp(a[1], mid[1], u), lerp(mid[1], b[1], u), u)) for u in [i / 20 for i in range(21)]]
    d = ImageDraw.Draw(fg)
    d.line(pts, fill=(14, 14, 20), width=26, joint='curve'); d.line(pts, fill=(54, 56, 66), width=14, joint='curve')
    d.line([(x, y - 4) for x, y in pts], fill=(90, 94, 106), width=4)
    if hot: d.line(pts, fill=(255, 90, 90), width=6)


# ================================================================== shot 1: wrong side, the hose drags him back
CAR_S = 6
PUMP_X = 820
ARRIVE, OUT, GRAB, SNAP = 0.5, 0.72, 1.12, 1.78
def car_x1(t): return lerp(-560, 400, oc(prog(t, -0.95, ARRIVE + 0.95)))
FLAP1 = lambda t: (car_x1(t) - 33 * CAR_S + 20, GROUND - 120 * CAR_S / 5)
HOLSTER = (PUMP_X - 140, GROUND - 9 * 28)
NOZ1 = Track([(GRAB, HOLSTER), (GRAB + 0.18, (HOLSTER[0] - 60, HOLSTER[1] - 120), 'oc'), (1.62, (330, GROUND - 330), 'io'),
              (SNAP, (300, GROUND - 320), 'io'), (SNAP + 0.16, (HOLSTER[0] - 40, HOLSTER[1] - 60), 'oc'), (SNAP + 0.5, HOLSTER, 'oc')], smooth=True)
P1 = Presenter([
    (-5, dict(path=Track([(OUT, (430, GROUND - 230)), (OUT + 0.16, (560, GROUND - 330), 'oc'), (GRAB - 0.02, reach(HOLSTER, 40, 7, 1).at(0), 'ic')],
                         smooth=True), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None, visible=False, look=HOLSTER)),
    (OUT, dict(visible=True)),
    (GRAB - 0.02, dict(path=reach(NOZ1.at, 40, 7, -1), arms=('aim', 40), face=-1, expr='smirk', squash=True, look=None, legs='run1')),
    (1.42, dict(expr='think', arms=('aim', 10), legs='run2')),
    (SNAP, dict(path=Track([(SNAP, (330 + 30, GROUND - 310)), (SNAP + 0.3, (700, GROUND - 250), 'oc'), (SNAP + 0.55, (620, GROUND), 'ic')], smooth=True),
                arms='flail', legs='fly', expr='shock', squash=True, face=1)),
    (SNAP + 0.55, dict(ground=GROUND, squash=True, arms='shrug', legs='stand', expr='sad', look_camera=True)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-2.0, (480, 900, 1.22)), (0.0, (520, 900, 1.28)), (ARRIVE, (540, 920, 1.32), 'oc'), (GRAB, (560, 860, 1.36), 'io'),
                     (SNAP, (500, 860, 1.42), 'io'), (2.6, (560, 900, 1.32), 'io')],
              kicks=[(ARRIVE, 0.06, 400, 1100), (GRAB, 0.06, *HOLSTER), (SNAP, 0.22, 330, 860)], shakes=[(ARRIVE, 0.2, 8), (SNAP, 0.5, 26)])


def shot_pump(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, -3, PUMP_X, GROUND - 330, (255, 210, 63, 26), hold=True, r=700)
    holding = GRAB <= t < SNAP + 0.5
    blit(fg, up(pump(int(t * 4) % 2, not holding), 9), PUMP_X, GROUND - 6)
    x = car_x1(t)
    draw_car(fg, 'red', x, CAR_S, dist=x, lights=True, brake=0 <= t - ARRIVE < 0.5)
    if t < OUT: head_in_car(fg, x + 20, CAR_S)
    fo = clamp((t - (OUT + 0.1)) / 0.15)
    fx_, fy_ = FLAP1(t); blit(fg, up(flap(round(fo * 4) / 4), CAR_S), fx_, fy_ + 50)
    if t < ARRIVE:
        fx.speed_lines(fg, 0.8 * (1 - prog(t, -0.95, ARRIVE + 0.95)), int(t * 12) % 5, col=(200, 204, 220))
        for k in range(3): fx.puff(fg, t, -0.3 + k * 0.2, x - 290, GROUND - 24, seed=10 + k, drift=(-280, -40))
    else:
        fx.dust(fg, t, ARRIVE, x + 220, GROUND, n=10, seed=11, dirx=1)
    nx, ny = NOZ1.at(t) if t >= GRAB else HOLSTER
    taut = 1.45 <= t < SNAP
    if t >= GRAB - 0.05: hose(fg, (PUMP_X - 140, GROUND - 9 * 34), (nx + 10, ny), slack=140, taut=taut, hot=taut and int(t * 14) % 2 == 0)
    blit(fg, up(nozzle(), 9), nx, ny + 36, 1, 1, -20 if taut else 0, anchor='center')
    if 1.45 <= t < SNAP:                                 # strain marks on the hose
        k = int(t * 16) % 2
        for i in range(3): blit(fg, fx.big('glyph', '!', '#ffd23f', s=5), 480 + i * 90, GROUND - 520 - 20 * k, 1, 1, 0, anchor='center')
    if t >= SNAP:
        fx.burst(fg, t, SNAP, 330, GROUND - 320, RED, n=16, seed=12); fx.ring(fg, t, SNAP, 330, GROUND - 320, GLOW, r1=420)
        fx.sparkles(fg, t + 0.3, 620, GROUND - 330, 260, 120, n=6, seed=13)       # dizzy stars over his head
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: the fuel dial in the real dashboard
class FuelDash(Dashboard):
    """The shared dashboard with a fuel gauge in the speedometer's place (E..F dial, pump icon with the side arrow)."""
    FUEL = Dashboard.SPEEDO
    ARROW = (FUEL[0] - 12 * DS, FUEL[1] + 13 * DS)    # screen px of the arrow tip

    def _grid(self):
        img = super()._grid(); d = ImageDraw.Draw(img)
        sx, sy = self.FUEL[0] // DS, self.FUEL[1] // DS
        d.ellipse((sx - 31, sy - 31, sx + 31, sy + 31), fill=(12, 13, 17))
        _gauge_face(d, sx, sy, 30, majors=5)
        _text(d, sx - 19, sy + 4, 'E', (232, 52, 63)); _text(d, sx + 16, sy + 4, 'F', (236, 240, 248))
        return img

    def frame(self, t, rpm_deg=205, fuel=0.2, glow=0):
        img = super().frame(t, rpm_deg=rpm_deg, speed_deg=225 - 270 * fuel, lcd='42 MI')   # the speedo needle is the fuel needle
        ov = Image.new('RGBA', (216, 386), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        sx, sy = self.FUEL[0] // DS, self.FUEL[1] // DS
        ic_ = (255, 217, 59) if glow else (150, 156, 170)
        px, py = sx - 4, sy + 9                          # pump icon
        d.rectangle((px, py, px + 6, py + 9), fill=ic_); d.rectangle((px + 1, py + 1, px + 5, py + 3), fill=(15, 16, 22))
        d.line([(px + 7, py + 2), (px + 9, py + 4), (px + 9, py + 8)], fill=ic_)
        ac = (255, 217, 59) if glow else (110, 116, 132)
        d.polygon([(px - 3, py + 1), (px - 8, py + 4), (px - 3, py + 8)], fill=ac)
        if glow == 2: d.rounded_rectangle((px - 11, py - 3, px + 12, py + 12), 3, outline=(255, 217, 59))
        img.alpha_composite(ov.resize((216 * DS, 386 * DS), Image.NEAREST).crop((0, 0, 1080, 1920)))
        if glow:
            g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            fx.ring(g, t, GLOW_T, *self.ARROW, GLOW, r1=140)
            img.alpha_composite(g)
        return img


@lru_cache(None)
def fdash(): return FuelDash(outside=GAR.base())


T2 = 2.55
GLOW_T = ws(12)                                        # 'side'
FX, FY = FuelDash.FUEL
P2 = Presenter([
    (T2, dict(path=Track([(T2, (1400, 560)), (T2 + 0.35, (1010, 760), 'oc'), (GLOW_T - 0.05, (1000, 1130), 'io')], smooth=True),
              size=5, legs='auto', arms='fly', expr='grin', face=-1, hover=6)),
    (GLOW_T - 0.05, dict(ground=1130, squash=True, arms='point', point=FuelDash.ARROW, look=FuelDash.ARROW, expr='wow', legs='stand')),
    (ws(15), dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=5)
CAM2 = Camera(W, H, [(T2, (560, 900, 1.0)), (T2 + 0.5, (700, 880, 1.45), 'io'), (GLOW_T, (800, 900, 2.0), 'io'), (ws(15), (790, 880, 2.05)),
                     (5.4, (720, 860, 1.6), 'io')],
              kicks=[(T2 + 0.05, 0.06, 560, 900), (GLOW_T, 0.18, *FuelDash.ARROW), (ws(15), 0.08, FX, FY)])


def fuel2(t): return 0.2 + 0.015 * math.sin(t * 3)


def shot_dash(t):
    D = fdash()
    g = 0 if t < GLOW_T else (2 if int(t * 6) % 2 == 0 else 1)
    img = D.frame(t, rpm_deg=205 + 1.2 * math.sin(t * 31), fuel=fuel2(t), glow=g)
    fg = layer()
    if t >= GLOW_T:
        fx.rays(fg, t, GLOW_T, *FuelDash.ARROW, (255, 210, 63, 40), hold=True, r=300)
        fx.burst(fg, t, GLOW_T, *FuelDash.ARROW, GLOW, n=12, r0=40, r1=180, seed=21, s=5)
        fx.sparkles(fg, t, *FuelDash.ARROW, 160, 120, n=5, seed=22, s=5)
        dg.label(fg, t, GLOW_T + 0.1, 'FUEL CAP SIDE', FuelDash.ARROW, (FX - 60, FY - 175), '#ffd23f', '#1a1a2e', '#e8b923', s=4)
    fx.glint(fg, t, T2 + 0.6, FX, FY, r=150)
    P2.draw(fg, t)
    img.alpha_composite(fg)
    return CAM2.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shots 3-4: top-down forecourt, left then right
FS = 9                                                 # forecourt grid scale (120x214 grid)


@lru_cache(None)
def forecourt():
    """Top-down petrol-station lane (120x214 grid): asphalt, kerbed pump islands on both sides, canopy lights, lane arrows."""
    rng = np.random.default_rng(7)
    a = rng.integers(0, 6, (214, 120))
    base = np.stack([30 + a, 31 + a, 37 + a, np.full_like(a, 255)], -1).astype(np.uint8)
    img = Image.fromarray(base, 'RGBA'); d = ImageDraw.Draw(img)
    for y in range(4, 214, 18): d.rectangle((59, y, 60, y + 9), fill=(214, 200, 120))           # centre dashes
    for x0 in (2, 100):                                                                          # pump islands
        d.rectangle((x0, 40, x0 + 17, 176), fill=(150, 156, 170)); d.rectangle((x0 + 1, 41, x0 + 16, 175), fill=(118, 124, 136))
        for y in (70, 132):
            d.rectangle((x0 + 4, y, x0 + 13, y + 16), fill=(214, 48, 58)); d.rectangle((x0 + 5, y + 1, x0 + 12, y + 4), fill=(240, 240, 236))
            d.rectangle((x0 + 6, y + 7, x0 + 11, y + 10), fill=(60, 170, 90))
        for y in (44, 172): d.rectangle((x0 + 6, y - 2, x0 + 11, y + 2), fill=(255, 217, 59))
    for y in (10, 200):                                                                          # canopy light panels
        for x in (24, 50, 76): d.rectangle((x, y, x + 18, y + 3), fill=(232, 236, 244))
    d.polygon([(56, 196), (64, 196), (60, 188)], fill=(214, 200, 120)); d.rectangle((58, 196, 61, 206), fill=(214, 200, 120))
    return up(img.convert('RGBA'), FS).crop((0, 0, W, H))


@lru_cache(None)
def topcar(col, side, open_=0.0):
    """Top-down car (32x58, nose up): shaded body, glass, roof highlight, mirrors, lights; fuel flap on `side` opening 0..1."""
    body, shade, hi, deep = {'red': ((232, 52, 63), (181, 34, 44), (255, 122, 128), (140, 24, 32)),
                             'blue': ((61, 127, 214), (43, 95, 168), (122, 176, 240), (30, 66, 120))}[col]
    img = Image.new('RGBA', (42, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(img); o = 5
    for y in (9, 41):
        for x in (o, o + 28): d.rectangle((x - 1, y, x + 4, y + 9), fill=(22, 22, 28))
    d.rounded_rectangle((o + 1, 1, o + 30, 56), 8, fill=deep)
    d.rounded_rectangle((o + 2, 1, o + 29, 55), 8, fill=body)
    d.rectangle((o + 2, 8, o + 4, 50), fill=shade); d.rectangle((o + 27, 8, o + 29, 50), fill=hi)
    d.line((o + 8, 4, o + 23, 4), fill=hi)                                                         # bonnet highlight
    d.line((o + 15, 5, o + 15, 13), fill=shade); d.line((o + 16, 5, o + 16, 13), fill=hi)
    d.polygon([(o + 5, 16), (o + 26, 16), (o + 24, 22), (o + 7, 22)], fill=(110, 142, 170))         # windscreen
    d.line((o + 8, 17, o + 14, 17), fill=(196, 222, 240)); d.line((o + 7, 19, o + 10, 19), fill=(196, 222, 240))
    d.rectangle((o + 7, 23, o + 24, 39), fill=shade); d.rectangle((o + 9, 24, o + 22, 38), fill=body)    # roof
    d.line((o + 10, 25, o + 21, 25), fill=hi); d.line((o + 10, 26, o + 13, 26), fill=hi)
    d.polygon([(o + 7, 40), (o + 24, 40), (o + 26, 45), (o + 5, 45)], fill=(90, 120, 150))            # rear screen
    d.line((o + 8, 41, o + 12, 41), fill=(170, 200, 224))
    d.line((o + 3, 30, o + 4, 30), fill=deep); d.line((o + 27, 30, o + 28, 30), fill=deep)          # door gaps
    d.rectangle((o - 1, 19, o + 1, 21), fill=shade); d.rectangle((o + 30, 19, o + 32, 21), fill=hi)  # mirrors
    for x in (o + 4, o + 23): d.rectangle((x, 1, x + 4, 2), fill=(255, 248, 210))
    for x in (o + 4, o + 23): d.rectangle((x, 54, x + 4, 55), fill=(255, 70, 70))
    fy = 42; w = round(5 * open_)
    if side == 'L':
        if open_ > 0: d.rectangle((o + 2, fy, o + 3, fy + 5), fill=(20, 20, 26)); d.rectangle((o + 2 - w, fy - 1, o + 2, fy), fill=(255, 217, 59))
        else: d.rectangle((o + 2, fy, o + 3, fy + 5), fill=(255, 217, 59))
    else:
        if open_ > 0: d.rectangle((o + 28, fy, o + 29, fy + 5), fill=(20, 20, 26)); d.rectangle((o + 29, fy - 1, o + 29 + w, fy), fill=(255, 217, 59))
        else: d.rectangle((o + 28, fy, o + 29, fy + 5), fill=(255, 217, 59))
    return outline(img)


@lru_cache(None)
def mini_gauge(side, glow):
    """Inset fuel gauge (52x34) for the forecourt shots: E..F arc, needle low, pump icon and the side arrow."""
    img = Image.new('RGBA', (52, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 51, 33), 6, fill=(26, 26, 46)); d.rounded_rectangle((2, 2, 49, 31), 5, fill=(15, 16, 22), outline=(132, 138, 150))
    cx, cy, R = 26, 28, 20
    for k in range(5):
        a = math.radians(160 - 140 * k / 4); d.line([(cx + (R - 4) * math.cos(a), cy - (R - 4) * math.sin(a)), (cx + R * math.cos(a), cy - R * math.sin(a))],
                                                    fill=(232, 52, 63) if k == 0 else (226, 230, 238))
    a = math.radians(145); d.line([(cx, cy), (cx + 15 * math.cos(a), cy - 15 * math.sin(a))], fill=(255, 96, 40), width=2)
    ic_ = (255, 217, 59) if glow else (200, 204, 214)
    px, py = 23, 11
    d.rectangle((px, py, px + 5, py + 8), fill=ic_); d.rectangle((px + 1, py + 1, px + 4, py + 3), fill=(15, 16, 22))
    ac = (255, 217, 59) if glow else (110, 116, 132)
    if side == 'L': d.polygon([(px - 3, py + 1), (px - 8, py + 4), (px - 3, py + 8)], fill=ac)
    else: d.polygon([(px + 9, py + 1), (px + 14, py + 4), (px + 9, py + 8)], fill=ac)
    return outline(img)


def lane_shot(t0, t1, side, col, t_arrow, t_open, dx):
    """One forecourt beat: the car pulls into the lane, the inset gauge's arrow glows, the flap on that side opens and the
    pump nozzle flies across to it; he swoops in from the same side and points."""
    stop_y = 1060
    def car_y(t): return lerp(2300, stop_y, oc(prog(t, t0 - 0.1, 0.7)))
    sgn = -1 if side == 'L' else 1
    flap_at = lambda t: (540 + sgn * 132, car_y(t) + 155)
    pump_at = (540 + sgn * 445, 1260)
    noz = Track([(t_open + 0.05, pump_at), (t_open + 0.35, (lambda p: (p[0] + sgn * 30, p[1]))(flap_at(t_open + 1)), 'oc')])
    P = Presenter([
        (t0, dict(path=Track([(t0, (540 - sgn * 900, 300)), (t0 + 0.45, (540 + sgn * 330, 900), 'oc')], smooth=True), size=6, legs='auto',
                  arms='fly', expr='grin', face=sgn, hover=10, trail=True)),
        (t_arrow, dict(arms='point', point=(540, 640), look=(540, 640), expr='talk')),
        (t_open, dict(arms='point', point=lambda t: flap_at(t), look=lambda t: flap_at(t), expr='wow', squash=True)),
        (t_open + 0.6, dict(arms='cheer', point=None, look=None, look_camera=True, expr='happy', squash=True)),
    ], words=WORDS, base_size=6)
    cam = Camera(W, H, [(t0, (540, 980, 1.05)), (t_arrow, (540, 900, 1.12), 'io'), (t_open, (540 + sgn * 60, 1060, 1.22), 'io'), (t1, (540 + sgn * 40, 1040, 1.26))],
                 kicks=[(t_arrow, 0.12, 540, 640), (t_open, 0.14, *flap_at(t_open + 1))], shakes=[(t0 + 0.6, 0.15, 6)])

    def shot(t):
        img = forecourt().copy(); fg = layer()
        y = car_y(t)
        for k in range(2):                                # headlight cones on the asphalt
            hx = 540 - 85 + k * 170
            ImageDraw.Draw(fg).polygon([(hx - 20, y - 260), (hx + 20, y - 260), (hx + 90, y - 700), (hx - 90, y - 700)], fill=(255, 244, 200, 26))
        o = oc(clamp((t - t_open) / 0.2)) if t >= t_open else 0
        blit(fg, up(topcar(col, side, round(o * 4) / 4), FS), 540, y + 261)
        if t < t0 + 0.6: fx.speed_lines(fg, 0.5 * (1 - prog(t, t0, 0.6)), int(t * 12) % 5, horizontal=False, col=(200, 204, 220))
        if t >= t_open + 0.05:
            nx, ny = noz.at(t)
            hose(fg, pump_at, (nx, ny), slack=0, taut=False)
            blit(fg, up(nozzle(), FS), nx, ny, 1, 1, 0 if side == 'R' else 180, anchor='center')
        if t >= t_open:
            fa = flap_at(t)
            fx.ring(fg, t, t_open, *fa, GLOW, r1=260); fx.burst(fg, t, t_open, *fa, GLOW, n=12, seed=31 + dx)
            fx.sparkles(fg, t, *fa, 220, 220, n=6, seed=33 + dx)
        if t >= t_open + 0.4:
            kc = popin(t, t_open + 0.4)
            blit(fg, fx.big('check'), fa[0] + sgn * 120, fa[1] - 200, kc, kc, anchor='center')
        k = popin(t, t_arrow - 0.15, 0.25)                # inset gauge with the arrow
        if k > 0:
            g = 2 if t >= t_arrow and int(t * 6) % 2 == 0 else int(t >= t_arrow)
            if t >= t_arrow: fx.rays(fg, t, t_arrow, 540, 640, (255, 210, 63, 30), hold=True, r=360)
            blit(fg, up(mini_gauge(side, g), 9), 540, 640, k, k, -2 * sgn + math.sin(t * 3), anchor='center')
        P.draw(fg, t)
        img.alpha_composite(fg)
        return cam.apply(img.convert('RGB'), t, (14, 15, 18))
    cues = [(t0, 'vroom', 0.5), (t0 + 0.55, 'screech', 0.3), (t_arrow, 'ding', 0.6), (t_arrow - 0.15, 'pop', 0.5),
            (t_open, 'click', 0.8), (t_open + 0.05, 'whoosh', 0.4), (t_open + 0.35, 'thump', 0.4), (t_open + 0.4, 'ding', 0.7), (t_open + 0.42, 'sparkle', 0.6)]
    return shot, cues


T3, T4 = 5.30, 6.95
shot_left, LEFT_CUES = lane_shot(T3, T4, 'L', 'red', ws(18), ws(20), 0)
shot_rightlane, RIGHT_CUES = lane_shot(T4, 8.6, 'R', 'blue', ws(22), ws(24), 5)


# ================================================================== shot 5: did you know? (poll)
T5 = 8.60
shot_ask, ASK_CUES = kit.ask(T5, WORDS, lambda fg, t: (fx.rays(fg, t, T5, 740, 700, (255, 210, 63, 30), hold=True, r=600),
                                                      blit(fg, up(mini_gauge('L', int(t * 3) % 2), 9), 790, GROUND - 10, 1, 1, 3 * math.sin(t * 2))))


# ================================================================== shot 6: right side first time
T6 = 10.10
ARR6 = T6 + 0.6
PLUG = ARR6 + 0.75
def car_x6(t): return lerp(-560, 660, oc(prog(t, T6 - 0.2, 0.8)))
FLAP6 = lambda t: (car_x6(t) - 33 * CAR_S + 30, GROUND - 120 * CAR_S / 5 + 44)
HOL6 = (300, GROUND - 210)
NOZ6 = Track([(ARR6 + 0.2, HOL6), (ARR6 + 0.45, (420, GROUND - 330), 'oc'), (PLUG, (FLAP6(20)[0] + 50, FLAP6(20)[1]), 'ic')], smooth=True)
P6 = Presenter([
    (T6, dict(path=Track([(T6, (1300, 760)), (ARR6 + 0.15, reach(HOL6, 20, 7, -1).at(0), 'oc')], smooth=True), size=7, legs='auto', arms='fly',
              expr='grin', face=-1, hover=8, trail=True)),
    (ARR6 + 0.2, dict(path=reach(NOZ6.at, 20, 7, -1), arms=('aim', 20), face=-1, expr='smirk', legs='fly')),
    (PLUG, dict(squash=True, expr='happy', arms=('aim', 10))),
    (PLUG + 0.5, dict(path=Track([(PLUG + 0.5, reach(NOZ6.at(PLUG), 20, 7, -1).at(0)), (PLUG + 0.85, (930, GROUND), 'oc')], smooth=True),
                      arms='thumb', legs='auto', expr='grin', look_camera=True, ground=GROUND, face=-1, squash=True)),
], words=WORDS, base_size=7)
CAM6 = Camera(W, H, [(T6, (560, 940, 1.2)), (ARR6, (520, 960, 1.28), 'oc'), (PLUG - 0.3, (600, 960, 1.32), 'io'), (END_T, (640, 960, 1.26), 'io')],
              kicks=[(ARR6, 0.08, 470, 1100), (PLUG, 0.16, *FLAP6(20)), (PLUG + 0.85, 0.08, 930, 1000)], shakes=[(ARR6, 0.15, 6), (PLUG, 0.2, 8)])


def shot_right(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= PLUG: fx.rays(fg, t, PLUG, *FLAP6(20), (90, 220, 120, 34), hold=True, r=700)
    x = car_x6(t)
    draw_car(fg, 'red', x, CAR_S, dist=x, lights=True, brake=0 <= t - ARR6 < 0.4)
    fo = clamp((t - ARR6) / 0.15)
    fx_, fy_ = FLAP6(t); blit(fg, up(flap(round(fo * 4) / 4), CAR_S), fx_, fy_ + 6)
    if t < ARR6: fx.speed_lines(fg, 0.6 * (1 - prog(t, T6, 0.6)), int(t * 12) % 5, col=(200, 204, 220))
    holding = t >= ARR6 + 0.2
    nx, ny = NOZ6.at(t) if holding else HOL6
    blit(fg, up(pump(1, not holding), 8), 170, GROUND + 40, flip=True)         # near-side pump, in front of the car, holster towards it
    if holding: hose(fg, (290, GROUND - 220), (nx, ny), slack=90)
    blit(fg, up(nozzle(), 8), nx - 20, ny, 1, 1, 0, anchor='center', flip=True)
    if t >= PLUG:
        fx.ring(fg, t, PLUG, fx_, fy_, GRN, r1=420); fx.burst(fg, t, PLUG, fx_, fy_, GRN, n=16, seed=51)
        fx.sparkles(fg, t, 520, GROUND - 300, 760, 420, n=12, seed=52); fx.confetti(fg, t, PLUG, 540, 500, n=40, seed=53)
        k = popin(t, PLUG + 0.1)
        blit(fg, fx.big('check'), fx_ - 40, fy_ - 300, k * 1.3, k * 1.3, anchor='center')
        dg.label(fg, t, PLUG + 0.15, 'RIGHT SIDE!', (fx_, fy_), (700, GROUND - 430), '#7fe3a0', '#1a1a2e', '#3c9e5a', s=7)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


# ================================================================== loop: the cold-open run-up again
def shot_loop(t): return shot_pump(t - DUR)


def overlay(cv, t):
    headline(cv, t, 2.35, HOOK, y=500, sz=100)
    if t >= END_T and t - DUR > -0.45: headline(cv, max(-0.35, t - DUR), 2.35, HOOK, y=500, sz=100)
    kit.photo_hq(cv, t, ws(15) - 0.05, T3 - 0.1, 'fuel_gauge', 330, 760, 420, rot=-5, label='THE REAL THING', crop=(0.36, 0.0, 1.0, 1.0))
    sticker(cv, t, T5 + 0.35, T6 - 0.1, ('Did you already know that?',), 400, opts=(('YES', (60, 170, 90)), ('NO', (214, 48, 58))))
    sticker(cv, t, ws(31) - 0.05, END_T - 0.1, ('Send this to the friend who', 'always parks on the wrong side.'), 400, rot=2, w=980)


# ================================================================== shots + transitions
SHOTS = [(-3.0, shot_pump), (T2, shot_dash), (T3, shot_left), (T4, shot_rightlane), (T5, shot_ask), (T6, shot_right), (END_T, shot_loop)]
TRANS = {1: (T2, T2 + 0.22, 'iris', (560, 900)), 2: (T3, T3 + 0.2, 'whip', dict(dx=0, dy=-1)), 3: (T4, T4 + 0.2, 'whip', dict(dx=-1)),
         4: (T5, T5 + 0.2, 'whip', dict(dx=0, dy=1)), 5: (T6, T6 + 0.2, 'push', None), 6: (END_T, END_T + 0.2, 'whip', dict(dx=-1))}
KEYCOL = {'arrow': YEL, 'side': YEL, 'left': YEL, 'right': YEL, 'know': GRN, 'friend': YEL, 'wrong': RED}
CUES = [(0.0, 'vroom', 0.5), (ARRIVE, 'screech', 0.5), (ARRIVE + 0.05, 'thump', 0.4), (OUT, 'click', 0.5), (OUT + 0.15, 'whoosh', 0.4),
        (GRAB, 'click', 0.7), (1.4, 'creak', 0.7), (SNAP, 'boing', 1.0), (SNAP + 0.02, 'crash', 0.3), (SNAP + 0.55, 'thump', 0.6),
        (T2 + 0.05, 'whoosh', 0.4), (T2 + 0.35, 'pop', 0.4), (GLOW_T, 'ding', 0.8), (GLOW_T + 0.02, 'sparkle', 0.7), (GLOW_T + 0.1, 'pop', 0.5),
        (ws(15) - 0.05, 'pop', 0.7), (T5 + 0.35, 'pop', 0.7), (T6, 'vroom', 0.6), (ARR6, 'screech', 0.3), (ARR6 + 0.2, 'click', 0.6),
        (ARR6 + 0.25, 'whoosh', 0.4), (PLUG, 'thump', 0.5), (PLUG + 0.02, 'ding', 0.9), (PLUG + 0.04, 'sparkle', 0.8),
        (PLUG + 0.05, 'confetti', 0.6), (ws(31), 'pop', 0.6)] + LEFT_CUES + RIGHT_CUES + ASK_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=False, loud=True, crisp=True,
          end=False, flash=False, tag='corner')

if __name__ == '__main__':
    kit.main()
