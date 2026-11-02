"""Renders 'Why is there an arrow on your fuel gauge?': the arrow next to the pump icon shows the fuel-cap side.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, mixer). Looping format: no outro
card; the last shot replays the cold open's run-up, so the last frame flows into frame 0. Voiceover: out/fuel-gauge-arrow/
voiceover.wav (clip 1 of out/voiceover/full_voiceover.wav, see voiceover.py); words.json is aligned to it.
Shots:
  1 pump     0.00  cold open: he rolls up with the pump on the far side, stretches the hose over the roof, it snaps back
  2 gauge    2.55  close-up fuel gauge, the arrow by the pump icon glows; the real gauge photo pops in
  3 split    5.35  split screen, top-down cars: left arrow opens the left flap, right arrow the right flap
  4 ask      8.65  'Did you already know that?': big '?', YES / NO poll sticker (mid-video comment prompt)
  5 right   10.10  he pulls in on the correct side first time, sparkles, share sticker
  6 loop    12.70  replays the cold-open run-up, so the last frame matches frame 0
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, draw_car, headline, sticker
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.guy import guy
from pixanim import fx
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline
from pixanim.autos import ptext

WORDS = kit.load_words(HERE)
DUR = 13.4
END_T = 12.70                                          # loop pre-roll starts here (no end card)
def ws(i): return WORDS[i]['s']
NAVYC = (26, 26, 46)
HOOK = ((('Why is there an', None),), (('ARROW', '#ffd23f'), ('on', None)), (('your fuel gauge?', None),))


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def pump(lit=0):
    """Fuel pump (30x60): red body, lit screen, nozzle holster on the left side (nozzle drawn separately)."""
    img = Image.new('RGBA', (30, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 0, 27, 6), fill=(240, 240, 236)); d.rectangle((2, 4, 27, 6), fill=(214, 48, 58))
    d.rectangle((4, 7, 25, 55), fill=(214, 48, 58)); d.rectangle((4, 7, 7, 55), fill=(240, 92, 100))
    d.rectangle((21, 7, 25, 55), fill=(160, 30, 40))
    d.rectangle((8, 11, 21, 20), fill=(20, 24, 30)); d.rectangle((9, 12, 20, 19), fill=(90, 220, 120) if lit else (40, 90, 60))
    for i in range(3): d.rectangle((9 + i * 4, 24, 11 + i * 4, 26), fill=(240, 240, 236))
    d.rectangle((0, 30, 4, 40), fill=(46, 48, 56))
    d.rectangle((2, 55, 27, 59), fill=(120, 126, 138))
    return outline(img)


@lru_cache(None)
def flap(open_=0.0):
    """Fuel flap (8x8) seen side-on: closed = body-coloured square, open = swung out showing the black cap."""
    img = Image.new('RGBA', (14, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((6, 0, 13, 7), fill=(30, 30, 36)); d.ellipse((8, 2, 11, 5), fill=(90, 94, 104))
    wdt = max(1, round(8 * (1 - open_)))
    d.rectangle((6 - (8 - wdt) if open_ > 0.5 else 6, 0, 6 + wdt - 1 if open_ <= 0.5 else 6, 7), fill=(255, 217, 59))
    return outline(img)


@lru_cache(None)
def topcar(col, side, open_=0.0):
    """Top-down car (34x60, nose up); fuel flap on `side` ('L'/'R') at the rear quarter, swinging open 0..1."""
    body, shade, hi = {'red': ((232, 52, 63), (181, 34, 44), (255, 122, 128)), 'blue': ((61, 127, 214), (43, 95, 168), (122, 176, 240))}[col]
    img = Image.new('RGBA', (44, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img); o = 5
    for y in (10, 42): d.rectangle((o - 1, y, o + 2, y + 9), fill=(26, 27, 32)); d.rectangle((o + 31, y, o + 34, y + 9), fill=(26, 27, 32))
    d.rounded_rectangle((o + 1, 2, o + 32, 57), 7, fill=body)
    d.rectangle((o + 3, 6, o + 30, 9), fill=hi)
    d.polygon([(o + 6, 16), (o + 27, 16), (o + 25, 22), (o + 8, 22)], fill=(126, 158, 184))
    d.rectangle((o + 8, 23, o + 25, 40), fill=shade); d.rectangle((o + 9, 24, o + 24, 26), fill=hi)
    d.polygon([(o + 8, 41), (o + 25, 41), (o + 27, 46), (o + 6, 46)], fill=(126, 158, 184))
    d.rectangle((o + 4, 2, o + 8, 3), fill=(255, 248, 200)); d.rectangle((o + 25, 2, o + 29, 3), fill=(255, 248, 200))
    d.rectangle((o + 4, 56, o + 8, 57), fill=(255, 80, 80)); d.rectangle((o + 25, 56, o + 29, 57), fill=(255, 80, 80))
    fy = 44; ow = round(5 * open_)
    if side == 'L':
        d.rectangle((o + 1, fy, o + 2, fy + 5), fill=(30, 30, 36) if open_ > 0 else (255, 217, 59))
        if open_ > 0: d.rectangle((o + 1 - ow, fy - 1, o, fy), fill=(255, 217, 59))
    else:
        d.rectangle((o + 31, fy, o + 32, fy + 5), fill=(30, 30, 36) if open_ > 0 else (255, 217, 59))
        if open_ > 0: d.rectangle((o + 33, fy - 1, o + 33 + ow, fy), fill=(255, 217, 59))
    return outline(img)


@lru_cache(None)
def gauge(side='L', glow=0, needle=8):
    """Fuel gauge face (96x62): E..F arc, needle step 0..20, pump icon with the side arrow (glow 0/1/2)."""
    img = Image.new('RGBA', (96, 62), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 95, 61), 10, fill=(20, 21, 28), outline=(150, 156, 170))
    cx, cy, R = 48, 50, 38
    for k in range(9):
        a = math.radians(160 - 140 * k / 8); r0 = R - (6 if k % 4 == 0 else 3)
        d.line([(cx + r0 * math.cos(a), cy - r0 * math.sin(a)), (cx + R * math.cos(a), cy - R * math.sin(a))],
               fill=(255, 80, 80) if k == 0 else (226, 230, 238))
    img.alpha_composite(ptext('E', (255, 90, 90)), (6, 34)); img.alpha_composite(ptext('F', (226, 230, 238)), (83, 34))
    a = math.radians(160 - 140 * needle / 20)
    d.line([(cx, cy), (cx + (R - 4) * math.cos(a), cy - (R - 4) * math.sin(a))], fill=(255, 96, 40), width=2)
    d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(176, 182, 192))
    ic_ = (255, 217, 59) if glow else (200, 204, 214)
    px, py = 42, 22                                     # pump icon
    d.rectangle((px, py, px + 9, py + 13), fill=ic_); d.rectangle((px + 2, py + 2, px + 7, py + 5), fill=(20, 21, 28))
    d.line([(px + 10, py + 3), (px + 13, py + 6), (px + 13, py + 11)], fill=ic_)
    ac = (255, 217, 59) if glow else (150, 156, 170)
    if side == 'L': d.polygon([(px - 3, py + 1), (px - 9, py + 7), (px - 3, py + 13)], fill=ac)
    else: d.polygon([(px + 16, py + 1), (px + 22, py + 7), (px + 16, py + 13)], fill=ac)
    if glow == 2:
        d.rounded_rectangle((px - 12, py - 3, px + 25, py + 16), 4, outline=(255, 217, 59))
    return outline(img)


def head_in_car(fg, x, s):
    """His head in the driver's window (the car is side-on, facing right)."""
    g = up(guy('grin', 'down', 'stand', (1, 0)), s).crop((0, 0, 48 * s, 20 * s))
    blit(fg, g, x + 6 * s, GROUND - 31 * s, anchor='bottom')


# ================================================================== shot 1: wrong side, the hose stretches and snaps
CAR_S = 5
PUMP_X = 790
ARRIVE = 0.55
def car_x1(t): return lerp(-420, 440, oc(prog(t, -0.9, ARRIVE + 0.9)))
OUT = 0.75                                              # he hops out
STRETCH0, SNAP = 1.0, 1.75
P1 = Presenter([
    (-5, dict(path=Track([(OUT, (470, GROUND - 160)), (OUT + 0.3, (300, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin',
              face=-1, ground=None, visible=False)),
    (OUT, dict(visible=True)),
    (OUT + 0.3, dict(ground=GROUND, squash=True, arms='catch', expr='talk', face=1)),
    (STRETCH0, dict(arms=('aim', 30), expr='think', look=(PUMP_X, GROUND - 400))),
    (SNAP, dict(arms='shock', expr='shock', squash=True, look=None, look_camera=True)),
    (SNAP + 0.45, dict(arms='shrug', expr='sad')),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-2.0, (520, 980, 1.06)), (0.0, (540, 960, 1.12)), (ARRIVE, (560, 960, 1.16), 'oc'), (2.6, (560, 960, 1.22), 'io')],
              kicks=[(ARRIVE, 0.06, 440, 1100), (SNAP, 0.16, 600, 820)], shakes=[(ARRIVE, 0.2, 6), (SNAP, 0.45, 18)])


def nozzle_pos(t):
    """Holster on the pump, pulled toward the near-side flap over the roof, then snapping back with a wobble."""
    home = (PUMP_X - 70, GROUND - 260)
    flap_at = (car_x1(t) - 33 * CAR_S, GROUND - 120)
    if t < STRETCH0: return home
    if t < SNAP:
        k = io(prog(t, STRETCH0, SNAP - STRETCH0)) * 0.82
        return (lerp(home[0], flap_at[0], k), lerp(home[1], flap_at[1], k) - 260 * math.sin(k * math.pi / 0.82 * 0.9))
    u = t - SNAP; w = math.exp(-u * 6) * math.cos(u * 26)
    return (home[0] + (flap_at[0] - home[0]) * 0.3 * w, home[1] + 80 * w)


def shot_pump(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    blit(fg, up(pump(int(t * 3) % 2), 9), PUMP_X, GROUND - 40)
    x = car_x1(t); moving = t < ARRIVE
    draw_car(fg, 'red', x, CAR_S, dist=x, lights=True, brake=0 <= t - ARRIVE < 0.4)
    head_in_car(fg, x + 20, CAR_S) if t < OUT else None
    fo = clamp((t - (OUT + 0.15)) / 0.15)
    blit(fg, up(flap(round(fo * 4) / 4), CAR_S), x - 33 * CAR_S, GROUND - 100)
    if moving:
        fx.speed_lines(fg, 0.7 * (1 - prog(t, -0.9, ARRIVE + 0.9)), int(t * 12) % 5, col=(200, 204, 220))
        for k in range(3): fx.puff(fg, t, -0.3 + k * 0.25, x - 230, GROUND - 20, seed=10 + k, drift=(-260, -40))
    else:
        fx.dust(fg, t, ARRIVE, x + 180, GROUND, n=8, seed=11, dirx=1)
    nx, ny = nozzle_pos(t); hx, hy = PUMP_X - 72, GROUND - 330
    d = ImageDraw.Draw(fg)                              # hose: sagging when slack, a taut straight band when stretched
    taut = STRETCH0 <= t < SNAP
    mid = ((hx + nx) / 2, (hy + ny) / 2 + (0 if taut else 120))
    pts = [(lerp(lerp(hx, mid[0], u), lerp(mid[0], nx, u), u), lerp(lerp(hy, mid[1], u), lerp(mid[1], ny, u), u)) for u in [i / 16 for i in range(17)]]
    d.line(pts, fill=(16, 16, 22), width=22); d.line(pts, fill=(60, 62, 72), width=12)
    if taut and t > SNAP - 0.35: d.line(pts, fill=(255, 90, 90), width=6)            # about to snap: hose glows red
    blit(fg, up(Image.new('RGBA', (5, 9), (40, 42, 50)), 9), nx, ny + 40, anchor='center')
    if t >= SNAP:
        fx.burst(fg, t, SNAP, nx, ny, RED, n=14, seed=12); fx.ring(fg, t, SNAP, nx, ny, GLOW)
        k = popin(t, SNAP + 0.05, 0.2)
        blit(fg, fx.big('glyph', '!', '#e0303a', s=18), 300, GROUND - 330, k, k, 8 * math.sin(t * 9), anchor='center')
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: the gauge close-up
T2 = 2.55
GLOW_T = ws(12)                                        # 'side'
CAM2 = Camera(W, H, [(T2, (540, 760, 1.0)), (GLOW_T, (470, 700, 1.12), 'io'), (5.4, (500, 720, 1.16), 'io')],
              kicks=[(T2 + 0.05, 0.08, 540, 700), (GLOW_T, 0.14, 420, 640), (ws(15), 0.1, 420, 640)])


def shot_gauge(t):
    img = Image.new('RGBA', (W, H), (14, 15, 20, 255)); d = ImageDraw.Draw(img)
    for y in range(0, H, 36): d.line((0, y, W, y), fill=(19, 20, 26))
    fg = layer()
    g = 2 if t >= GLOW_T and int(t * 6) % 2 == 0 else (1 if t >= GLOW_T else 0)
    blit(fg, up(gauge('L', g, 3 + round(1.5 * math.sin(t * 2))), 10), 540, 1020)
    if t >= GLOW_T:
        fx.ring(fg, t, GLOW_T, 400, 640, GLOW, r1=360); fx.burst(fg, t, GLOW_T, 400, 640, GLOW, n=12, seed=21)
        fx.sparkles(fg, t, 420, 640, 360, 220, n=6, seed=22)
        kd = popin(t, GLOW_T + 0.15)
        blit(fg, fx.big('badge', 'FUEL CAP SIDE', '#ffd23f', '#1a1a2e', '#e8b923', s=6), 540, 360, kd, kd, -3 + 2 * math.sin(t * 4), anchor='center')
    img.alpha_composite(fg)
    return CAM2.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 3: left arrow / right arrow
T3 = 5.35
LT, RT = ws(20), ws(24)                                # 'left' side, 'right' side
CAM3 = Camera(W, H, [(T3, (540, 900, 1.0)), (8.6, (540, 900, 1.04), 'io')],
              kicks=[(LT, 0.08, 270, 900), (RT, 0.08, 810, 900)])


def _half(side, t_open, col):
    def draw(p, t):
        dd = ImageDraw.Draw(p)
        on = t >= t_open
        g = up(gauge(side, 2 if on and int(t * 6) % 2 == 0 else int(on), 4), 4)
        p.alpha_composite(g, ((p.width - g.width) // 2, 40))
        o = oc(clamp((t - t_open) / 0.25))
        c = up(topcar(col, side, round(o * 4) / 4), 9)
        bob = 4 * math.sin(t * 3 + (0 if side == 'L' else 1))
        p.alpha_composite(c, ((p.width - c.width) // 2, int(370 + bob)))
        if on:
            fx.ring(p, t, t_open, p.width // 2 + (-150 if side == 'L' else 150), 800, GLOW, r1=200)
            fx.sparkles(p, t, p.width // 2 + (-150 if side == 'L' else 150), 800, 160, 160, n=5, seed=31 if side == 'L' else 32)
    return draw


def shot_split(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    kit.split_panel(fg, t, T3, (40, 450, 525, 1310), _half('L', LT, 'red'), badge='LEFT')
    kit.split_panel(fg, t, T3 + 0.12, (555, 450, 1040, 1310), _half('R', RT, 'blue'), badge='RIGHT')
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: did you know? (poll)
T4 = 8.65
shot_ask, ASK_CUES = kit.ask(T4, WORDS, lambda fg, t: blit(fg, up(gauge('L', 1, 4), 5), 800, GROUND))


# ================================================================== shot 5: right side first time
T5 = 10.10
ARR5 = T5 + 0.75
def car_x5(t): return lerp(-420, 440, oc(prog(t, T5, 0.75)))
P5 = Presenter([
    (T5, dict(path=Track([(T5, (900, GROUND))]), size=7, legs='auto', arms='wave', expr='grin', face=-1, ground=GROUND)),
    (ARR5, dict(arms='thumb', expr='grin', squash=True, look_camera=True)),
    (ARR5 + 0.6, dict(arms='cheer', expr='happy', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(T5, (540, 960, 1.12)), (ARR5, (520, 980, 1.18), 'oc'), (END_T, (520, 980, 1.22), 'io')],
              kicks=[(ARR5, 0.08, 440, 1100), (ARR5 + 0.3, 0.1, 300, 1000)], shakes=[(ARR5, 0.15, 5)])


def shot_right(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car_x5(t)
    draw_car(fg, 'red', x, CAR_S, dist=x, lights=True, brake=0 <= t - ARR5 < 0.4)
    fo = clamp((t - ARR5) / 0.15)
    blit(fg, up(flap(round(fo * 4) / 4), CAR_S), x - 33 * CAR_S, GROUND - 100)
    blit(fg, up(pump(1), 7), 110, GROUND + 50)                       # the pump is on the near side this time
    if t >= ARR5 + 0.2:                                              # short hose straight to the open flap
        dd = ImageDraw.Draw(fg); a, b = (170, GROUND - 170), (x - 33 * CAR_S + 10, GROUND - 120)
        dd.line([a, ((a[0] + b[0]) / 2, b[1] + 40), b], fill=(16, 16, 22), width=20, joint='curve'); dd.line([a, ((a[0] + b[0]) / 2, b[1] + 40), b], fill=(60, 62, 72), width=10, joint='curve')
    if t >= ARR5 + 0.3:
        fx.ring(fg, t, ARR5 + 0.3, x - 160, GROUND - 120, GRN); fx.burst(fg, t, ARR5 + 0.3, x - 160, GROUND - 120, GRN, n=12, seed=51)
        fx.sparkles(fg, t, 440, GROUND - 240, 700, 360, n=10, seed=52)
        k = popin(t, ARR5 + 0.3)
        blit(fg, fx.big('check'), x - 160, GROUND - 330, k, k, anchor='center')
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== loop: the cold-open run-up again
def shot_loop(t): return shot_pump(t - DUR)


def overlay(cv, t):
    headline(cv, t, 2.35, HOOK, y=620, sz=100)
    if t >= END_T: headline(cv, max(-0.35, t - DUR), 2.35, HOOK, y=620, sz=100) if t - DUR > -0.45 else None
    kit.photo_hq(cv, t, ws(15) - 0.05, T3 - 0.1, 'fuel_gauge', 540, 720, 470, rot=-4, label='THE REAL THING', crop=(0.36, 0.0, 1.0, 1.0))
    sticker(cv, t, T4 + 0.35, T5 - 0.1, ('Did you already know that?',), 560, opts=(('YES', (60, 170, 90)), ('NO', (214, 48, 58))))
    sticker(cv, t, ws(31) - 0.05, END_T - 0.1, ('Send this to the friend who', 'always parks on the wrong side.'), 560, rot=2, w=980)


# ================================================================== shots + transitions
SHOTS = [(-3.0, shot_pump), (T2, shot_gauge), (T3, shot_split), (T4, shot_ask), (T5, shot_right), (END_T, shot_loop)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (T4, T4 + 0.2, 'whip', dict(dx=0, dy=1)),
         4: (T5, T5 + 0.2, 'whip', dict(dx=1)), 5: (END_T, END_T + 0.2, 'whip', dict(dx=-1))}
KEYCOL = {'arrow': YEL, 'side': YEL, 'left': YEL, 'right': YEL, 'know': GRN, 'friend': YEL, 'wrong': RED}
CUES = [(-0.0, 'vroom', 0.5), (ARRIVE, 'screech', 0.5), (ARRIVE + 0.05, 'thump', 0.4), (OUT + 0.3, 'thump', 0.3),
        (OUT + 0.2, 'click', 0.5), (STRETCH0, 'creak', 0.6), (SNAP, 'boing', 1.0), (SNAP + 0.02, 'crash', 0.25),
        (SNAP + 0.05, 'pop', 0.6), (T2 + 0.05, 'pop', 0.5), (GLOW_T, 'ding', 0.7), (GLOW_T + 0.02, 'sparkle', 0.6),
        (ws(15) - 0.05, 'pop', 0.7), (LT, 'click', 0.7), (LT + 0.02, 'ding', 0.5), (RT, 'click', 0.7), (RT + 0.02, 'ding', 0.5),
        (T4 + 0.35, 'pop', 0.7), (T5, 'vroom', 0.6), (ARR5, 'screech', 0.3), (ARR5 + 0.3, 'ding', 0.9), (ARR5 + 0.32, 'sparkle', 0.8),
        (ARR5 + 0.6, 'confetti', 0.5), (ws(31), 'pop', 0.6), (DUR - 0.05, 'vroom', 0.0)] + ASK_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=False, loud=True, crisp=True,
          end=False, flash=False, tag='corner')

if __name__ == '__main__':
    kit.main()
