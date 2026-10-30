"""Renders 'Rimac Nevera, 1,914 hp': four motors, 1,914 hp, a claimed 8.58 s quarter mile at 167 mph.

Template: videos/plaid-two-seconds (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json; the voiceover is out/rimac-nevera-1914/voiceover.wav (clip 1 of out/voiceover/full_voiceover.wav).
The quarter-mile time is Rimac's claim (CLAIMED tag). The car is a generic pixel coupe, no badges or lettering.
Shots:
  1 motors   0.00  four pixel motors light up one by one (Four / electric / motors), 'Four motors.'
  2 photo    1.90  garage: the real Nevera photo pops in, the hp counter runs to 1,914, '1,914 horsepower'
  3 quarter  6.35  night street: CLAIMED, the car launches, the 1/4-mile timer runs to 8.58 and stamps, 'claimed'
  4 speed   10.55  dashboard: the speedo sweeps to 167, '167 MPH' slams in
  5 teaser  13.35  shared NEXT EPISODE ending ('Follow for the next one.')
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, title, draw_car, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.dash import Dashboard
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR = 17.0
END_T = 13.35
def ws(i): return WORDS[i]['s']


# ------------------------------------------------------------------ episode sprites
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
def flag(ph=0):
    """Chequered finish flag on a pole (22x30), cloth rippling with phase 0..3."""
    img = Image.new('RGBA', (22, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 1, 29), fill=(200, 204, 214))
    for gx in range(5):
        for gy in range(4):
            dy = round(math.sin((gx + ph) * 1.4))
            d.rectangle((2 + gx * 4, 1 + gy * 3 + dy, 5 + gx * 4, 3 + gy * 3 + dy), fill=(248, 248, 244) if (gx + gy) % 2 else (26, 26, 46))
    return outline(img)


# ================================================================== shot 1: hook, four motors light up
MX = [(330, 760), (750, 760), (330, 1060), (750, 1060)]
LIT = [ws(0), ws(1), ws(2), ws(2) + 0.36]            # Four / electric / motors, then the fourth
CAM1 = Camera(W, H, [(-1.0, (540, 900, 1.12)), (0.0, (540, 900, 1.12)), (1.3, (540, 920, 1.2), 'io'), (2.1, (540, 920, 1.24))],
              kicks=[(LIT[0], 0.1, *MX[0]), (LIT[1], 0.1, *MX[1]), (LIT[2], 0.1, *MX[2]), (LIT[3], 0.16, *MX[3])], shakes=[(LIT[3], 0.35, 10)])


def shot_motors(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    for i, (x, y) in enumerate(MX):
        on = clamp((t - LIT[i]) / 0.15)
        k = popin(t, LIT[i] - 0.12, 0.25) * (1 + 0.05 * on * math.sin(t * 18 + i))
        blit(fg, up(motor(round(on * 4) / 4), 11), x, y + 3 * math.sin(t * 30) * on, k, k, 0, anchor='center')
        if t >= LIT[i]:
            fx.ring(fg, t, LIT[i], x, y, GLOW, life=0.35, r1=260); fx.burst(fg, t, LIT[i], x, y, GLOW, n=10, r0=120, r1=300, seed=3 + i)
            d = ImageDraw.Draw(fg)                    # bolts of current between lit motors
            if i % 2 == 1 and t >= LIT[i - 1]:
                for b in range(3):
                    yy = y - 20 + b * 20 + 6 * math.sin(t * 40 + b)
                    d.rectangle((MX[i - 1][0] + 150, yy, x - 150, yy + 8), fill=(255, 220, 90, int(140 + 100 * math.sin(t * 30 + b))))
    fx.sparkles(fg, t, 540, 910, 760, 520, n=8, seed=4)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 2: the real car, 1,914 hp
T2 = 1.9
HP0 = ws(4)                                            # '1,914'
def hp(t): return int(1914 * oc(prog(t, HP0 + 0.05, 1.5)))
P2 = Presenter([
    (T2 - 0.05, dict(path=Track([(T2 - 0.05, (1300, 300)), (T2 + 0.4, (860, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (T2 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 640), look=(540, 640), expr='wow', face=None)),
    (ws(8), dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(T2, (540, 900, 1.1)), (3.6, (540, 900, 1.16), 'io'), (6.35, (540, 880, 1.2), 'io')],
              kicks=[(T2 + 0.4, 0.06, 860, 1100), (ws(5), 0.12, 300, 1060), (ws(8), 0.08, 860, 1000)], shakes=[(HP0 + 1.55, 0.25, 8)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= HP0:
        k = popin(t, HP0, 0.25) * (fx.slam(t, HP0 + 1.55, k=0.5) if t >= HP0 + 1.55 else 1)
        blit(fg, fx.big('badge', f'{hp(t):,} HP', '#ffd23f', '#d6303a', '#e8b923', s=11), 440, 1110, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
        if t >= HP0 + 1.55: fx.burst(fg, t, HP0 + 1.55, 440, 1110, RED, n=16, seed=21); fx.ring(fg, t, HP0 + 1.55, 440, 1110, GLOW)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the claimed quarter mile
T3 = 6.35
GO, FIN = ws(15), ws(19) + 0.25                        # 'quarter' -> 'seconds.'
def lcd3(t): return 8.58 * clamp((t - GO) / (FIN - GO))
def car_x3(t): return 220 + 1500 * ic(prog(t, GO, FIN - GO)) if t < FIN + 0.6 else lerp(-300, 380, oc(prog(t, FIN + 0.6, 0.4)))
CAM3 = Camera(W, H, [(T3, (540, 980, 1.15)), (GO, (400, 1040, 1.26), 'io'), (GO + 0.6, (600, 980, 1.1), 'oc'), (10.6, (560, 960, 1.16), 'io')],
              kicks=[(ws(11), 0.12, 540, 560), (GO, 0.2, 260, 1080), (FIN, 0.22, 540, 760)], shakes=[(GO, 0.4, 14), (FIN, 0.3, 12)])


def shot_quarter(t):
    fast = GO <= t < FIN + 0.6
    scroll = 0 if t < GO else 2600 * ic(prog(t, GO, 0.9)) + max(0, t - GO - 0.9) * 2600
    img = street(t, scroll); fg = layer()
    x = car_x3(t)
    draw_car(fg, 'silver', x, 4, y=ROAD_Y, dist=x + scroll, lights=True, brake=t >= FIN and t < FIN + 0.6)
    if fast:
        fx.speed_lines(fg, 1.0, int(t * 12) % 5, col=(200, 204, 220))
        for k in range(4): fx.puff(fg, t, GO + k * 0.06, 160, ROAD_Y - 20, seed=30 + k, drift=(-300, -60), col=(200, 204, 214))
    if t >= ws(11): fx.burst(fg, t, ws(11), 540, 420, GRN, n=12, seed=31)   # 'claims' (the title pops over it)
    if t >= GO - 0.25:                                 # timer board
        k = popin(t, GO - 0.25, 0.25)
        v = lcd3(t)
        blit(fg, fx.big('badge', f'{v:.2f} S', '#ffffff' if v < 8.58 else '#ffd23f', '#1a1a2e', '#d6d9e2', s=12), 540, 700, k, k, 2, anchor='center')
        dg.label(fg, t, GO, '1/4 MILE', (540, 760), (540, 470), '#ffffff', '#1a1a2e', '#d6d9e2', s=8, t1=FIN)
    if t >= FIN - 0.4:
        k = popin(t, FIN - 0.4, 0.25)
        blit(fg, up(flag(int(t * 8) % 4), 8), 900, ROAD_Y - 10, k, k, 0)
    if t >= FIN:
        fx.stamp_at(fg, t, FIN, 'CLAIMED', 760, 900, rot=-10, s=9, col='#2f9e52')
        fx.sparkles(fg, t, 540, 700, 760, 260, n=8, seed=33); fx.confetti(fg, t, FIN, 540, 640, n=24, seed=34)
    return CAM3.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: 167 mph on the speedo
T4 = 10.55
DASH = Dashboard()
SP = ws(22)                                            # '167'
def speed_deg(t): return 225 - 228 * io(clamp((t - T4 - 0.1) / (SP + 0.3 - T4))) + 2 * math.sin(t * 37)
CAM4 = Camera(W, H, [(T4, (560, 880, 1.22)), (SP, (600, 920, 1.32), 'io'), (13.4, (580, 920, 1.36), 'io')],
              kicks=[(T4 + 0.1, 0.08, 560, 880), (SP + 0.3, 0.22, 560, 1000), (ws(25), 0.1, 560, 1000)], shakes=[(SP + 0.3, 0.4, 12)])


def shot_speed(t):
    v = int(167 * io(clamp((t - T4 - 0.1) / (SP + 0.3 - T4))))
    img = DASH.frame(t, rpm_deg=225 - 230 * min(1, (t - T4) * 0.9) + 5 * math.sin(t * 33), speed_deg=speed_deg(t), lcd=f'{v}')
    fg = layer()
    if t >= SP + 0.3:
        k = fx.slam(t, SP + 0.3) * popin(t, SP + 0.3, 0.2)
        blit(fg, fx.big('badge', '167 MPH', '#ffd23f', '#d6303a', '#e8b923', s=13), 560, 1030, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, SP + 0.3, 560, 1030, RED, n=18, seed=41); fx.ring(fg, t, SP + 0.3, 560, 1030, GLOW, r1=520)
        fx.sparkles(fg, t, 560, 1080, 800, 260, n=8, seed=42)
    fx.speed_lines(fg, 0.5 * clamp((t - T4) / 0.6), int(t * 12) % 5, col=(200, 204, 220))
    img.alpha_composite(fg)
    return CAM4.apply(img.convert('RGB'), t, (14, 15, 18))


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)


def overlay(cv, t):
    title(cv, t, 0.05, 1.85, 'Four motors.', YEL, 400, 130, -3)
    kit.photo_hq(cv, t, T2 + 0.15, 6.15, 'nevera', 540, 640, 820, rot=-3, label='THE REAL CAR')
    title(cv, t, HP0, 4.5, '1,914 horsepower', RED, 990, 108, 2)
    title(cv, t, ws(11), GO - 0.05, 'claimed', GRN, 380, 130, 3)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_motors), (T2, shot_photo), (T3, shot_quarter), (T4, shot_speed), (END_T, shot_teaser)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (T4, T4 + 0.2, 'whip', dict(dx=0, dy=1)),
         4: (END_T, END_T + 0.2, 'iris', (540, 980))}
KEYCOL = {'motors': YEL, '1,914': RED, 'nevera': YEL, 'claims': GRN, 'quarter': YEL, '8.58': RED, '167': RED}
CUES = [(0.0, 'whoosh', 0.4)] + [(t, 'pop', 0.6) for t in LIT] + [(LIT[3], 'vroom', 0.6), (LIT[3] + 0.02, 'sparkle', 0.6),
    (T2 + 0.15, 'pop', 0.7), (T2 + 0.4, 'thump', 0.4), (HP0, 'click', 0.5)] + [(HP0 + 0.1 * k, 'click', 0.4) for k in range(1, 15)] + [
    (HP0 + 1.55, 'ding', 0.9), (HP0 + 1.57, 'sparkle', 0.7), (ws(8), 'pop', 0.5),
    (ws(11), 'stamp', 0.6), (GO - 0.25, 'pop', 0.5), (GO, 'vroom', 1.0), (GO + 0.05, 'screech', 0.4)] + [
    (GO + 0.2 + 0.25 * k, 'click', 0.35) for k in range(int((FIN - GO - 0.2) / 0.25))] + [
    (FIN, 'stamp', 0.8), (FIN + 0.02, 'confetti', 0.6), (FIN + 0.6, 'whoosh', 0.4),
    (T4 + 0.1, 'vroom', 0.7), (SP + 0.3, 'boom', 0.5), (SP + 0.32, 'stamp', 0.7), (SP + 0.35, 'sparkle', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
