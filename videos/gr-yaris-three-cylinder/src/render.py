"""Renders 'GR Yaris, three cylinders': 1.6-litre turbo triple, 257 hp, and the AWD split per drive mode.

Template: videos/ac-idle shot structure on shared/episode.py (as in plaid-two-seconds). Voiceover: clip 2 of
out/voiceover/full_voiceover.wav (shared/vo_split.py), aligned by align.py -> words.json. The engine and car are
generic pixel art with no badges or lettering; the split bar reads front/rear torque shares as the script states them.
Shots:
  1 fire     0.00  hook: a pixel three-cylinder fires 1-2-3; 'Three cylinders.'
  2 photo    1.85  framed real photo of a GR Yaris; 1.6 L label, TURBO tag
  3 power    4.60  the triple with its turbo spooling; 257 HP counter; '257 horsepower'
  4 normal   7.10  garage: car + split bar 60/40, DEFAULT
  5 sport   10.85  night street: the bar slides to 30/70, SPORT
  6 track   14.35  street, faster: 50/50, TRACK
  7 teaser  16.55  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title, draw_car, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 18.3, 16.6
FIRE = ((0.15, 0), (0.55, 1), (0.95, 2), (1.35, 0), (1.6, 1), (1.85, 2))   # hook: the three cylinders fire in turn


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def triple(phase=0, flame=(0, 0, 0), turbo=-1):
    """Three-cylinder cutaway (64x50): block, three bores with pistons at `phase` (0..11, 120 deg apart),
    flame 0..1 per chamber, crank below. turbo >= 0 adds the snail housing with its wheel at that step (0..3)."""
    img = Image.new('RGBA', (64, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((4, 4, 45, 40), fill=(120, 126, 138)); d.rectangle((4, 4, 45, 7), fill=(150, 156, 170))   # block + head
    d.rectangle((2, 0, 47, 4), fill=(96, 100, 110))
    d.rectangle((6, 41, 43, 47), fill=(70, 73, 84))                                                     # sump
    for i in range(3):
        x0 = 8 + i * 12
        d.rectangle((x0, 8, x0 + 9, 34), fill=(24, 25, 30))                                             # bore
        a = math.radians((phase * 30 + i * 120) % 360)
        top = 13 + round(7 * (1 - math.cos(a)))                                                         # piston top
        if flame[i] > 0:
            f = flame[i]
            d.rectangle((x0, 8, x0 + 9, top - 1), fill=(255, int(140 + 90 * f), 40))
            d.rectangle((x0 + 3, 8, x0 + 6, max(8, top - 3)), fill=(255, 250, 200))
        d.rectangle((x0, top, x0 + 9, top + 6), fill=(200, 204, 214)); d.line([(x0, top + 2), (x0 + 9, top + 2)], fill=(150, 156, 170))
        cx, cy = x0 + 4.5 + 3 * math.sin(a), 42 - 3 * math.cos(a)                                      # con-rod to crank
        d.line([(x0 + 4.5, top + 6), (cx, cy)], fill=(176, 182, 192), width=2)
        d.rectangle((x0 + 3, 4, x0 + 6, 7), fill=(255, 220, 90) if flame[i] > 0.6 else (200, 204, 214))  # spark plug
    d.line([(8, 42), (42, 42)], fill=(150, 156, 170))
    if turbo >= 0:
        d.rectangle((45, 14, 50, 18), fill=(150, 156, 170))
        d.ellipse((48, 10, 63, 25), fill=(176, 182, 192)); d.ellipse((51, 13, 60, 22), fill=(60, 63, 72))
        for k in range(4):
            a = math.radians(turbo * 22 + k * 90)
            d.line([(55.5, 17.5), (55.5 + 4 * math.cos(a), 17.5 + 4 * math.sin(a))], fill=(222, 228, 236))
    return outline(img)


def flames(t):
    out = [0.0, 0.0, 0.0]
    for tf, i in FIRE:
        if 0 <= t - tf < 0.3: out[i] = max(out[i], 1 - (t - tf) / 0.3)
    return tuple(round(f * 4) / 4 for f in out)


def engine_at(fg, t, x, y, s, turbo=-1, spin=6.0):
    ph = int(t * spin * 12) % 12
    blit(fg, up(triple(ph, flames(t), turbo), s), x, y)


@lru_cache(None)
def split_bar(front):
    """Torque split bar (100x22): yellow FRONT share, green REAR share."""
    img = Image.new('RGBA', (100, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 99, 21), 4, fill=(26, 26, 46))
    fx_ = 2 + round(96 * front / 100)
    d.rectangle((2, 2, fx_ - 1, 19), fill=(255, 210, 63)); d.rectangle((fx_, 2, 97, 19), fill=(90, 220, 120))
    d.line([(4, 4), (fx_ - 3, 4)], fill=(255, 238, 160)); d.line([(fx_ + 2, 4), (95, 4)], fill=(170, 240, 190))
    d.rectangle((fx_ - 1, 0, fx_, 21), fill=(26, 26, 46))
    return img


# ================================================================== shot 1: hook, three cylinders fire in turn
CAM1 = Camera(W, H, [(-1.0, (540, 940, 1.2)), (0.0, (540, 940, 1.2)), (1.0, (540, 900, 1.3), 'io'), (1.9, (540, 880, 1.36), 'io')],
              kicks=[(tf, 0.07, 300 + i * 108 * 1, 760) for tf, i in FIRE[:3]] + [(1.35, 0.12, 540, 900)], shakes=[(0.15, 1.8, 4)])
EX, EY, ES = 540, 1180, 9


def cyl_x(i, x=EX, s=ES): return x - 32 * s + (12.5 + i * 12) * s


def shot_fire(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 0.0, 0.3)
    engine_at(fg, t, EX, EY, ES)
    for tf, i in FIRE[:3]:
        if t >= tf:
            kc = popin(t, tf, 0.2) * popout(t, 1.75)
            blit(fg, fx.big('badge', str(i + 1), '#ffd23f', '#1a1a2e', '#e8b923', s=10), 540 + (i - 1) * 190, 650, kc, kc, -4 + 4 * i, anchor='center')
            fx.burst(fg, t, tf, cyl_x(i), 760, GLOW, n=8, r0=40, r1=200, seed=10 + i)
    for tf, i in FIRE:
        if t >= tf: fx.puff(fg, t, tf, cyl_x(i) + 260, EY - 330, seed=20 + int(tf * 10), life=0.5, drift=(140, -120))
    fx.sparkles(fg, t, 540, 740, 600, 200, n=5, seed=12)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.8, 'Three cylinders.', YEL, 470, 104, -3)
    title(cv, t, 4.95, 7.0, '257 horsepower', RED, 470, 104, 3)


# ================================================================== shot 2: the real car
P2 = Presenter([
    (1.8, dict(path=Track([(1.8, (-200, 300)), (2.15, (150, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (2.15, dict(ground=GROUND, squash=True, arms='point', point=(400, 900), look=(400, 900), expr='smile', face=None)),
    (3.64, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(1.85, (540, 860, 1.06)), (2.99, (540, 840, 1.12), 'io'), (4.6, (560, 860, 1.14), 'io')],
              kicks=[(2.0, 0.1, 560, 760), (2.99, 0.08, 300, 1100), (3.64, 0.14, 800, 1100)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 1.9, 560, 760, GLOW, hold=True, r=620)
    photo(fg, t, 2.0, 9.0, 'yaris', 560, 760, 880, 0, 3, 'THE REAL CAR', fit=True)
    dg.label(fg, t, 1.95, '1.6 L', (420, 900), (330, 1120), '#ffffff', '#1a1a2e', '#d6d9e2', s=9)
    if t >= 2.99:
        k = popin(t, 2.99, 0.25)
        blit(fg, up(triple(int(t * 72) % 12, flames(t - 2.99 + 0.15), -1), 3), 600, 1170, k, k, 0)
    if t >= 3.64:
        k = fx.slam(t, 3.64) * popin(t, 3.64, 0.2)
        blit(fg, fx.big('tag', 'TURBO', '#fff6e0', '#d6303a', s=9), 820, 1110, k, k, 6, anchor='center')
        fx.burst(fg, t, 3.64, 820, 1110, RED, n=10, seed=21)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: 257 hp
def hp(t): return int(257 * oc(prog(t, 4.95, 1.0)))
P3 = Presenter([
    (4.55, dict(path=Track([(4.55, (1300, 300)), (4.9, (930, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='wow', face=-1, ground=None)),
    (4.9, dict(ground=GROUND, squash=True, arms='point', point=(480, 900), look=(480, 900), expr='talk', face=None)),
    (5.93, dict(arms='cheer', point=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(4.6, (540, 900, 1.1)), (5.93, (520, 820, 1.18), 'io'), (7.1, (520, 840, 1.2))],
              kicks=[(4.66, 0.1, 480, 1000), (4.95, 0.12, 480, 640), (5.93, 0.22, 480, 640)], shakes=[(4.66, 2.4, 3), (5.93, 0.3, 12)])


def shot_power(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    spin = 6 + 10 * prog(t, 4.66, 1.2)
    ph = int(t * spin * 12) % 12
    fl = tuple(round(max(0, math.sin(t * spin * 2 * math.pi / 3 + i * 2.1)) * 4) / 4 for i in range(3))
    blit(fg, up(triple(ph, fl, int(t * 40) % 4), 8), 480, 1180)
    fx.puff(fg, t, 4.7 + (int((t - 4.7) * 6) / 6), 790, 940, seed=int(t * 6), life=0.4, drift=(160, -140))
    if t >= 4.95:
        k = popin(t, 4.95, 0.25) * (1 + 0.06 * (hp(t) == 257) * math.sin(t * 18))
        blit(fg, fx.big('badge', f'{hp(t)} HP', '#ffd23f' if hp(t) == 257 else '#ffffff', '#1a1a2e', '#e8b923', s=13), 480, 640, k, k, -3, anchor='center')
        fx.sparkles(fg, t, 480, 640, 700, 240, n=7, seed=31)
    if t >= 5.93:
        fx.burst(fg, t, 5.93, 480, 640, GLOW, n=18, seed=32); fx.ring(fg, t, 5.93, 480, 640, GLOW, r1=480)
        fx.confetti(fg, t, 5.93, 480, 600, n=30, seed=33)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shots 4-6: the AWD split
def front_share(t):
    """Front torque share: 60 by default, 30 once Sport sends 70 to the rear, 50 in Track."""
    f = lerp(60, 30, oc(prog(t, 12.25, 0.5)))
    f = lerp(f, 50, oc(prog(t, 14.41, 0.5)))
    return int(round(f / 5) * 5)


def awd(fg, t, cx, gy, s, t_in):
    """Car with glowing torque rings on each axle (sized by share) and the split bar above it."""
    f = front_share(t)
    wx = [cx - 45 * s + gx * s for gx, _ in ((21, 41), (69, 41))]
    wy = gy - 9 * s
    for x, share in ((wx[1], f), (wx[0], 100 - f)):                       # front wheel is on the right
        r = 40 + 2.2 * share + 8 * math.sin(t * 10 + x)
        col = (255, 210, 63, 90) if x == wx[1] else (90, 220, 120, 90)
        ImageDraw.Draw(fg).ellipse((x - r, wy - r, x + r, wy + r), outline=col[:3] + (200,), width=S)
    k = popin(t, t_in + 0.1, 0.3); by = gy - 440
    blit(fg, up(split_bar(f), 8), 540, by, k, k, 0, anchor='center')
    fxs = 140 + 768 * f / 100                                               # screen x of the split line
    for val, cx in ((f, (140 + fxs) / 2), (100 - f, (fxs + 940) / 2)):
        blit(fg, fx.big('label', f'{val}%', '#ffffff', s=8), cx, by, k, k, anchor='center')
    blit(fg, fx.big('label', 'FRONT', '#ffd23f', s=7), 250, by - 140, k, k, anchor='center')
    blit(fg, fx.big('label', 'REAR', '#5adc78', s=7), 840, by - 140, k, k, anchor='center')


def mode_badge(fg, t, t0, text, col, gy):
    if t >= t0:
        k = fx.slam(t, t0) * popin(t, t0, 0.2); y = gy - 700
        blit(fg, fx.big('badge', text, col, '#1a1a2e', '#e8b923', s=11), 540, y, k, k, -4 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, t0, 540, y, GLOW, n=14, seed=int(t0 * 10))


P4 = Presenter([
    (7.05, dict(path=Track([(7.05, (-200, 300)), (7.4, (110, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (7.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 680), look=(540, 680), expr='smile', face=None)),
    (8.42, dict(arms='point', point=(800, 1080), look=(800, 1080), expr='wow')),
    (9.75, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(7.1, (540, 900, 1.08)), (8.42, (580, 880, 1.14), 'io'), (10.85, (560, 880, 1.18), 'io')],
              kicks=[(7.33, 0.1, 540, 740), (8.42, 0.14, 800, 1100), (9.24, 0.1, 800, 1100), (9.75, 0.12, 540, 480)])


def shot_normal(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    draw_car(fg, 'red', 560, 7, sy=1 + 0.01 * math.sin(t * 4))
    fx.contact_shadow(fg, 560, GROUND, 600, s=7)
    awd(fg, t, 560, GROUND, 7, 7.2)
    if t >= 8.42: fx.sparkles(fg, t, 790, 1100, 260, 160, n=5, seed=41)
    mode_badge(fg, t, 9.75, 'DEFAULT', '#ffffff', GROUND)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


CAM5 = Camera(W, H, [(10.85, (540, 900, 1.12)), (12.25, (520, 920, 1.18), 'io'), (14.35, (540, 900, 1.14), 'io')],
              kicks=[(11.29, 0.16, 540, 450), (12.25, 0.14, 330, 1100), (13.38, 0.12, 330, 1100)], shakes=[(11.29, 0.3, 8)])


def shot_sport(t):
    img = street(t, (t - 10.85) * 900); fg = layer()
    draw_car(fg, 'red', 560, 6, y=ROAD_Y, dist=t * 900, lights=True, rot=-1.5 * (t > 12.25) * math.exp(-(t - 12.25) * 3))
    fx.speed_lines(fg, 0.5, int(t * 12) % 5, col=(200, 204, 220))
    awd(fg, t, 560, ROAD_Y, 6, 10.85)
    mode_badge(fg, t, 11.29, 'SPORT', '#e0303a', ROAD_Y)
    if t >= 12.25: fx.ring(fg, t, 12.25, 290, ROAD_Y - 54, (90, 220, 120), r1=300)
    return CAM5.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


CAM6 = Camera(W, H, [(14.35, (540, 900, 1.18)), (15.29, (540, 900, 1.12), 'io'), (16.6, (540, 900, 1.16), 'io')],
              kicks=[(14.41, 0.18, 540, 450), (15.29, 0.14, 540, 760)], shakes=[(14.41, 0.3, 10)])


def shot_track(t):
    img = street(t, (t - 14.35) * 1600 + 3000); fg = layer()
    fx.speed_lines(fg, 0.9, int(t * 14) % 5, col=(220, 224, 236))
    draw_car(fg, 'red', 560, 6, y=ROAD_Y, dist=t * 1600, lights=True)
    awd(fg, t, 560, ROAD_Y, 6, 14.3)
    mode_badge(fg, t, 14.41, 'TRACK', '#5adc78', ROAD_Y)
    if t >= 15.29:                                   # 'evenly': the split line lands dead centre
        fx.ring(fg, t, 15.29, 540, ROAD_Y - 440, GLOW, r1=360); fx.burst(fg, t, 15.29, 540, ROAD_Y - 440, GLOW, n=14, seed=61)
        fx.gsparkles(fg, t, 540, ROAD_Y - 440, 760, 200, n=8, seed=62)
    return CAM6.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


shot_teaser, TEASE_CUES = kit.teaser(16.55, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_fire), (1.85, shot_photo), (4.6, shot_power), (7.1, shot_normal), (10.85, shot_sport), (14.35, shot_track), (16.55, shot_teaser)]
TRANS = {1: (1.85, 2.05, 'whip', dict(dx=1)), 2: (4.6, 4.8, 'iris', (480, 900)), 3: (7.1, 7.3, 'push', None),
         4: (10.85, 11.05, 'whip', dict(dx=0, dy=1)), 5: (14.35, 14.55, 'whip', dict(dx=1)), 6: (16.55, 16.75, 'whip', dict(dx=1))}
KEYCOL = {'toyota': YEL, 'yaris': YEL, '1.6-litre': YEL, 'three-cylinder': YEL, '257': RED,
          'all-wheel': GRN, 'goes': GRN, '60': YEL, 'front': YEL, 'default': YEL, 'sport': RED, '70': GRN, 'rear': GRN,
          'track': GRN, 'evenly': GRN}
CUES = [
    (0.0, 'whoosh', 0.4)] + [(tf, 'thump', 0.6) for tf, _ in FIRE] + [(tf, 'pop', 0.5) for tf, _ in FIRE[:3]] + [
    (0.15, 'vroom', 0.5), (1.9, 'pop', 0.5), (2.0, 'sparkle', 0.5), (2.05, 'pop', 0.5), (2.99, 'pop', 0.6), (3.64, 'stamp', 0.7),
    (4.66, 'vroom', 0.9), (4.95, 'pop', 0.6)] + [(5.0 + k * 0.17, 'click', 0.35) for k in range(5)] + [
    (5.93, 'ding', 0.9), (5.95, 'confetti', 0.7),
    (7.2, 'pop', 0.6), (8.42, 'slide_down', 0.4), (9.75, 'stamp', 0.6),
    (10.9, 'vroom', 0.7), (11.29, 'stamp', 0.8), (12.25, 'slide_down', 0.5), (12.27, 'whoosh', 0.5), (13.38, 'pop', 0.5),
    (14.41, 'stamp', 0.8), (14.43, 'vroom', 0.8), (15.29, 'pop', 0.6), (15.31, 'sparkle', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
