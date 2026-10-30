"""Renders 'Tourbillon, gauges in the wheel': 1,800 hp from a V16 and three motors; gauges that stay still.

Template: videos/plaid-two-seconds (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json; the voiceover is out/tourbillon-wheel-gauges/voiceover.wav (clip 2 of out/voiceover/full_voiceover.wav).
The mixer holds a 1.3 s pause before 'Follow for the next one' (GAP) so the wheel beat can land; the words after it
are shifted by the same amount. The wheel and engine are generic pixel drawings with no lettering or logos.
Shots:
  1 wheel    0.00  hook: a pixel steering wheel turns while the hub gauges stay still, 'Gauges that never move.'
  2 photo    1.75  garage: the real Tourbillon photo slides in, the hp counter runs to 1,800
  3 engine   3.70  cutaway: sixteen cylinders light up bank by bank, then three motors glow, 'V16 and three motors'
  4 hub      6.60  close-up: the wheel swings lock to lock, the hub dials hold level, FIXED / ALWAYS VISIBLE tags
  5 teaser  12.60  shared NEXT EPISODE ending ('Follow for the next one.')
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

RAW = kit.load_words(HERE)
GAP = (11.2, 1.3)                                     # pause inserted before 'Follow' (between 'turns.' and 'Follow')
WORDS = kit.shift_words(RAW, *GAP)
DUR = 17.0
END_T = 12.6
def ws(i): return WORDS[i]['s']


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def rim(deg=0):
    """Steering wheel rim and three spokes (64x64 grid), rotated by `deg` (NEAREST keeps the pixels square)."""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 61, 61), fill=(40, 42, 52)); d.ellipse((8, 8, 55, 55), fill=(0, 0, 0, 0))
    d.arc((3, 3, 60, 60), 200, 340, fill=(90, 94, 108), width=2)                 # leather highlight
    d.rectangle((29, 2, 34, 6), fill=(214, 60, 60))                              # top-dead-centre stripe
    for a in (180, 0, 270):                                                      # spokes left, right, down
        r = math.radians(a)
        d.line([(32 + 14 * math.cos(r), 32 + 14 * math.sin(r)), (32 + 27 * math.cos(r), 32 + 27 * math.sin(r))], fill=(150, 156, 170), width=5)
    d.ellipse((17, 17, 46, 46), fill=(0, 0, 0, 0))
    img = img.rotate(-deg, resample=Image.NEAREST)
    return outline(img)


@lru_cache(None)
def hub(needle=0.0, glow=0):
    """Fixed hub cluster (30x30): two small dials and a centre bar; needles at `needle` 0..1."""
    img = Image.new('RGBA', (30, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 29, 29), fill=(60, 64, 78)); d.ellipse((2, 2, 27, 27), fill=(26, 26, 36))
    for cx in (9, 20):
        d.ellipse((cx - 6, 9, cx + 6, 21), fill=(236, 236, 230)); d.ellipse((cx - 5, 10, cx + 5, 20), fill=(16, 18, 26))
        for k in range(7):
            a = math.radians(225 - k * 45); d.point((cx + 4 * math.cos(a), 15 - 4 * math.sin(a)), fill=(236, 236, 230))
        a = math.radians(225 - 270 * needle * (0.8 if cx == 9 else 1))
        d.line([(cx, 15), (cx + 4 * math.cos(a), 15 - 4 * math.sin(a))], fill=(255, 96, 40))
    d.rectangle((12, 23, 17, 25), fill=(90, 220, 120) if glow else (40, 80, 50))
    return outline(img)


def wheel(fg, t, x, y, deg, s, needle):
    blit(fg, up(rim(round(deg / 3) * 3), s), x, y, anchor='center')
    blit(fg, up(hub(round(needle * 20) / 20, int(t * 3) % 2), s), x, y, anchor='center')


@lru_cache(None)
def motor(on=0.0):
    """Electric motor (26x22): finned can, copper windings window, glowing when `on` (0..1)."""
    img = Image.new('RGBA', (26, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 2, 21, 21), 4, fill=(120, 126, 138))
    for y in range(4, 21, 3): d.line([(1, y), (20, y)], fill=(150, 156, 170))
    d.rectangle((21, 9, 25, 13), fill=(200, 204, 214))
    g = int(80 + 175 * on)
    d.rectangle((6, 7, 15, 16), fill=(min(255, 150 + g // 3), min(255, 80 + g // 2), 40))
    for x in range(7, 15, 2): d.line([(x, 8), (x, 15)], fill=(min(255, 200 + g // 5), min(255, 120 + g // 2), 60))
    if on > 0.5: d.rectangle((9, 0, 12, 2), fill=(255, 230, 90))
    return outline(img)


@lru_cache(None)
def v16(lit=0):
    """V16 seen from above (86x40): two banks of eight cylinders, the first `lit` glowing (left bank first)."""
    img = Image.new('RGBA', (86, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 4, 85, 35), 4, fill=(96, 100, 112)); d.rectangle((2, 18, 83, 21), fill=(70, 74, 86))   # block, valley
    for bank in range(2):
        for c in range(8):
            n = bank * 8 + c; x = 4 + c * 10; y = 7 if bank == 0 else 23
            on = n < lit
            d.rectangle((x, y, x + 7, y + 8), fill=(255, 196, 70) if on else (150, 156, 170))
            d.rectangle((x + 2, y + 2, x + 5, y + 6), fill=(255, 240, 160) if on else (120, 126, 138))
    d.rectangle((84, 14, 85, 25), fill=(200, 204, 214))
    return outline(img)


# ================================================================== shot 1: hook, the wheel turns, the gauges don't
def steer1(t): return 70 * math.sin(max(0, t - 0.15) * 3.2) * min(1, max(0, t) * 2)
CAM1 = Camera(W, H, [(-1.0, (540, 940, 1.12)), (0.0, (540, 940, 1.12)), (1.0, (540, 960, 1.2), 'io'), (2.0, (540, 960, 1.24))],
              kicks=[(0.15, 0.1, 540, 1000), (0.75, 0.08, 540, 1000), (1.25, 0.12, 540, 1000)])


def shot_wheel(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 0.0, 0.25)
    d = ImageDraw.Draw(fg)
    d.rectangle((0, 1180, W, 1260), fill=(30, 32, 40, 255)); d.rectangle((0, 1180, W, 1186), fill=(70, 74, 86, 255))   # dash top
    wheel(fg, t, 540, 1000, steer1(t), 10, 0.35 + 0.05 * math.sin(t * 9))
    for side in (-1, 1):                                # motion arcs on the rim, never on the hub
        a0 = 200 if side < 0 else -20
        if abs(steer1(t + 0.02) - steer1(t)) > 0.6:
            d.arc((540 - 350, 1000 - 350, 540 + 350, 1000 + 350), a0, a0 + 40, fill=(255, 255, 255, 120), width=9)
    if t >= 0.55:
        kk = popin(t, 0.55, 0.25)
        blit(fg, fx.big('tag', 'STILL', '#fff6e0', '#2f9e52', s=8), 540, 1000 + 200, kk, kk, 3 * math.sin(t * 4), anchor='center')
    fx.sparkles(fg, t, 540, 1000, 300, 200, n=5, seed=4)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 2: the real car slides in, 1,800 hp
T2 = 1.75
HP0 = ws(3)                                           # '1,800'
def hp(t): return int(1800 * oc(prog(t, HP0, 1.1)))
P2 = Presenter([
    (T2 - 0.05, dict(path=Track([(T2 - 0.05, (-200, 300)), (T2 + 0.4, (220, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (T2 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 600), look=(540, 600), expr='wow', face=None)),
    (HP0 + 1.1, dict(arms='shock', point=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(T2, (540, 900, 1.1)), (3.7, (540, 880, 1.18), 'io')],
              kicks=[(T2 + 0.15, 0.08, 540, 600), (HP0 + 1.1, 0.18, 760, 1080)], shakes=[(HP0 + 1.1, 0.3, 10)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= HP0:
        k = popin(t, HP0, 0.25) * (fx.slam(t, HP0 + 1.1, k=0.5) if t >= HP0 + 1.1 else 1)
        blit(fg, fx.big('badge', f'{hp(t):,} HP', '#ffd23f', '#d6303a', '#e8b923', s=11), 700, 1100, k, k, 3 + 2 * math.sin(t * 5), anchor='center')
        if t >= HP0 + 1.1: fx.burst(fg, t, HP0 + 1.1, 700, 1100, RED, n=16, seed=21); fx.ring(fg, t, HP0 + 1.1, 700, 1100, GLOW)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: V16 + three motors
T3 = 3.7
V0, M0 = ws(7), ws(9)                                 # 'V16', 'three'
def lit(t): return int(16 * clamp((t - V0) / 0.75))
MX = (300, 540, 780)
CAM3 = Camera(W, H, [(T3, (540, 900, 1.06)), (V0, (540, 860, 1.14), 'io'), (M0, (540, 940, 1.1), 'io'), (6.6, (540, 940, 1.14), 'io')],
              kicks=[(V0, 0.12, 540, 700), (V0 + 0.75, 0.16, 540, 700)] + [(M0 + 0.2 * i, 0.08, MX[i], 1050) for i in range(3)],
              shakes=[(V0 + 0.75, 0.35, 10)])


def shot_engine(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, T3 + 0.05, 0.3)
    n = lit(t)
    blit(fg, up(v16(n), 9), 540, 790 + 3 * math.sin(t * 40) * (n == 16), k, k, 0, anchor='center')
    if n == 16:
        fx.ring(fg, t, V0 + 0.75, 540, 790, GLOW, r1=600); fx.burst(fg, t, V0 + 0.75, 540, 790, GLOW, n=18, seed=31)
        fx.sparkles(fg, t, 540, 790, 820, 400, n=8, seed=32)
    for i, x in enumerate(MX):
        t0 = M0 + 0.2 * i
        if t >= t0 - 0.1:
            kk = popin(t, t0 - 0.1, 0.25); on = clamp((t - t0) / 0.15)
            blit(fg, up(motor(round(on * 4) / 4), 8), x, 1100 + 3 * math.sin(t * 30) * on, kk, kk, 0, anchor='center')
            if t >= t0: fx.ring(fg, t, t0, x, 1100, (90, 220, 120), life=0.3, r1=200); fx.burst(fg, t, t0, x, 1100, (90, 220, 120), n=8, r0=80, r1=220, seed=33 + i)
    if t >= M0 + 0.4:
        d = ImageDraw.Draw(fg)                          # current flowing from the motors up to the engine
        for i, x in enumerate(MX):
            for j in range(4):
                yy = 1030 - ((t * 400 + j * 60 + i * 20) % 140)
                d.rectangle((x - 5, yy, x + 5, yy + 14), fill=(120, 240, 150, 200))
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: the hub stays put as the wheel turns
T4 = 6.6
G0, VIS, TURN = ws(13), ws(22), ws(25)                # 'gauges', 'visible', 'wheel' (turns)
def steer4(t):
    u = max(0.0, t - (ws(19) - 0.2))                   # starts turning on 'so'
    return 120 * math.sin(u * 2.4) * min(1, u * 1.5) + (200 * io(prog(t, TURN, 0.8)) if t >= TURN else 0)
P4 = Presenter([
    (T4 - 0.05, dict(path=Track([(T4 - 0.05, (1300, 400)), (T4 + 0.4, (900, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (T4 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 760), look=(540, 760), expr='smile', face=None)),
    (VIS, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(T4, (540, 820, 1.1)), (G0, (540, 760, 1.3), 'io'), (ws(19), (540, 820, 1.12), 'io'), (TURN, (540, 800, 1.2), 'io'),
                     (END_T, (540, 800, 1.26), 'io')],
              kicks=[(G0, 0.14, 540, 760), (ws(17), 0.1, 540, 760), (VIS, 0.14, 540, 520), (TURN, 0.12, 540, 760)], shakes=[(TURN + 0.8, 0.25, 8)])


def shot_hub(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    d.rectangle((0, 1180, W, 1260), fill=(30, 32, 40, 255)); d.rectangle((0, 1180, W, 1186), fill=(70, 74, 86, 255))
    k = popin(t, T4 + 0.05, 0.3)
    deg = steer4(t)
    blit(fg, up(rim(round(deg / 3) * 3), 11), 540, 760, k, k, 0, anchor='center')
    blit(fg, up(hub(round((0.4 + 0.25 * math.sin(t * 2)) * 20) / 20, int(t * 3) % 2), 11), 540, 760, k, k, 0, anchor='center')
    if t >= G0:
        kk = popin(t, G0, 0.2)
        hl = 110 * kk + 8 * math.sin(t * 8)                 # highlight ring around the fixed hub
        d.ellipse((540 - hl - 60, 760 - hl - 60, 540 + hl + 60, 760 + hl + 60), outline=(255, 217, 59, 230), width=9)
    dg.label(fg, t, ws(15), 'FIXED HUB', (540, 640), (540, 340), '#ffd23f', '#1a1a2e', '#e8b923', s=8, t1=ws(19) + 0.6)
    if t >= VIS:
        kk = popin(t, VIS, 0.25)
        blit(fg, fx.big('tag', 'ALWAYS VISIBLE', '#fff6e0', '#2f9e52', s=8), 540, 380, kk, kk, -4 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, VIS, 540, 380, GRN, n=12, seed=41)
    if t >= TURN + 0.8:
        fx.stamp_at(fg, t, TURN + 0.8, 'STILL LEVEL', 540, 960, rot=-8, s=8, col='#2f9e52')
        fx.sparkles(fg, t, 540, 760, 500, 400, n=8, seed=42); fx.confetti(fg, t, TURN + 0.8, 540, 600, n=24, seed=43)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)


def overlay(cv, t):
    title(cv, t, 0.05, 1.7, 'Gauges that', YEL, 440, 124, -3)
    title(cv, t, 0.2, 1.7, 'never move.', YEL, 580, 124, 2)
    kit.photo_hq(cv, t, T2 + 0.1, 3.6, 'tourbillon', 540, 690, 860, rot=3, label='THE REAL CAR', crop=(0.0, 0.27, 1.0, 1.0))
    title(cv, t, V0, 6.5, 'V16 and', RED, 420, 116, -2)
    title(cv, t, M0 - 0.1, 6.5, 'three motors', RED, 550, 116, 2)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_wheel), (T2, shot_photo), (T3, shot_engine), (T4, shot_hub), (END_T, shot_teaser)]
TRANS = {1: (T2, T2 + 0.2, 'push', None), 2: (T3, T3 + 0.2, 'whip', dict(dx=1)), 3: (T4, T4 + 0.2, 'iris', (540, 760)),
         4: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'tourbillon': YEL, '1,800': RED, 'v16': RED, 'motors': YEL, 'gauges': YEL, 'steering': YEL, 'visible': GRN, 'turns': YEL}
CUES = [(0.0, 'whoosh', 0.4), (0.05, 'pop', 0.6), (0.15, 'creak', 0.4), (0.75, 'creak', 0.4), (0.55, 'pop', 0.5), (1.25, 'creak', 0.4),
        (T2 + 0.1, 'whoosh', 0.6), (T2 + 0.15, 'pop', 0.6), (T2 + 0.4, 'thump', 0.4)] + [(HP0 + 0.1 * k, 'click', 0.4) for k in range(10)] + [
        (HP0 + 1.1, 'ding', 0.9), (HP0 + 1.12, 'sparkle', 0.6), (T3 + 0.05, 'pop', 0.5)] + [
        (V0 + 0.05 * k, 'click', 0.45) for k in range(15)] + [(V0 + 0.75, 'vroom', 0.9), (V0 + 0.77, 'boom', 0.4)] + [
        (M0 + 0.2 * i, 'pop', 0.7) for i in range(3)] + [(M0 + 0.45, 'sparkle', 0.6),
        (T4 + 0.4, 'thump', 0.4), (G0, 'ding', 0.6), (ws(15), 'pop', 0.6), (ws(19), 'creak', 0.5), (VIS, 'stamp', 0.6), (VIS + 0.02, 'sparkle', 0.6),
        (TURN, 'creak', 0.6), (TURN + 0.8, 'stamp', 0.8), (TURN + 0.82, 'confetti', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, gap=GAP, crisp=True)

if __name__ == '__main__':
    kit.main()
