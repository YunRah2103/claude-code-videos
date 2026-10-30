"""Renders 'Ioniq 6, 0.21 drag': Hyundai's claimed drag coefficient, its lowest ever, and why less drag saves energy.

Template: videos/ac-idle shot structure on shared/episode.py (as in plaid-two-seconds). Voiceover: clip 4 of
out/voiceover/full_voiceover.wav (shared/vo_split.py), aligned by align.py -> words.json. The read is 11.0 s, so the
episode runs 14 s with a longer end card. The figure is Hyundai's own ('says'), shown with a CLAIMED tag. The car is a
generic pixel saloon with no badges or lettering.
Shots:
  1 tunnel   0.00  hook: pixel wind tunnel, airflow lines slide smoothly over the car; '0.21 drag.'
  2 photo    2.10  framed real photo of an Ioniq 6; Cd 0.21 badge with a CLAIMED tag
  3 lowest   4.55  record line falls to a new low; LOWEST EVER
  4 smooth   6.70  turbulent airflow smooths out as the car passes; energy meter; 'less drag'
  5 teaser   9.95  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, NAVY, RED, YEL, GRN, WHITE, layer, finish, photo, title, draw_car
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 14.0, 10.0
CS = 7                                          # car pixel scale in the tunnel


# ------------------------------------------------------------------ the wind tunnel
def bump(u): return max(0.0, 1 - u * u) ** 0.55 if abs(u) < 1 else 0.0


def roof(x, cx):
    """Height (px above the ground) of the car's outline at screen x."""
    u = (x - cx) / (44 * CS)
    return 34 * CS * bump(u * 1.02) if abs(u) < 1 else 0.0


def tunnel(fg, t, cx, calm=lambda x: 1.0, k=1.0, speed=520):
    """Airflow lines over a car at cx: each line lifts smoothly over the roof; calm(x) 0..1 fades turbulence out."""
    d = ImageDraw.Draw(fg)
    for i, y0 in enumerate(range(GROUND - 520, GROUND - 20, 54)):
        pts = []
        for x in range(-20, W + 40, S):
            r = roof(x, cx); lift = 0.0
            if r > 0:
                depth = GROUND - y0                              # px above the ground
                lift = max(0.0, r + 36 - depth) * (0.75 + 0.25 * (depth / 520))
                lift += 50 * math.exp(-max(0, depth - r) / 140) * (r / (34 * CS))
            turb = (1 - calm(x)) * 26 * math.sin(x * 0.03 + t * 9 + i * 1.7) * math.sin(x * 0.011 + i)
            pts.append((x, y0 - lift + turb))
        ph = (t * speed + i * 37) % 120
        for j in range(len(pts) - 1):                            # moving dashes, snapped to the pixel grid
            if (pts[j][0] + ph) % 120 < 84:
                a, b = pts[j], pts[j + 1]
                d.line([(a[0], round(a[1] / 3) * 3), (b[0], round(b[1] / 3) * 3)], fill=(150, 214, 255, int(210 * k)), width=6)


@lru_cache(None)
def fan(step=0):
    """Tunnel fan (30x30): ring, hub, four blades at `step` (0..7)."""
    img = Image.new('RGBA', (30, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 29, 29), fill=(70, 73, 84)); d.ellipse((2, 2, 27, 27), fill=(24, 25, 30))
    for k in range(4):
        a = math.radians(step * 11 + k * 90)
        d.polygon([(15, 15), (15 + 12 * math.cos(a), 15 + 12 * math.sin(a)), (15 + 11 * math.cos(a + 0.5), 15 + 11 * math.sin(a + 0.5))], fill=(176, 182, 192))
    d.ellipse((12, 12, 18, 18), fill=(222, 228, 236))
    return outline(img)


def tunnel_set(fg, t):
    blit(fg, up(fan(int(t * 40) % 8), 7), 70, GROUND - 300, anchor='center')
    d = ImageDraw.Draw(fg)
    d.rectangle((0, GROUND - 600, W, GROUND - 588), fill=(70, 73, 84)); d.rectangle((0, GROUND, W, GROUND + 12), fill=(70, 73, 84))


@lru_cache(None)
def battery(level):
    img = Image.new('RGBA', (24, 12), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 21, 11), fill=(26, 26, 46)); d.rectangle((21, 3, 23, 8), fill=(26, 26, 46))
    d.rectangle((2, 2, 2 + round(17 * level), 9), fill=(90, 220, 120))
    return img


# ================================================================== shot 1: hook, the wind tunnel
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.2)), (0.0, (540, 960, 1.2)), (1.0, (560, 940, 1.28), 'io'), (2.1, (560, 930, 1.32), 'io')],
              kicks=[(0.06, 0.08, 540, 900), (1.0, 0.12, 560, 930), (1.37, 0.12, 560, 930)])


def shot_tunnel(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    tunnel_set(fg, t)
    draw_car(fg, 'silver', 560, CS)
    fx.contact_shadow(fg, 560, GROUND, 620, s=CS)
    tunnel(fg, t, 560, k=popin(t, 0.05, 0.4))
    fx.sparkles(fg, t, 560, GROUND - 260, 640, 160, n=5, seed=1)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.05, '0.21 drag.', YEL, 470, 130, -3)
    title(cv, t, 6.79, 9.9, 'less drag', GRN, 470, 130, 2)


# ================================================================== shot 2: the real car, 0.21
P2 = Presenter([
    (2.05, dict(path=Track([(2.05, (1300, 300)), (2.4, (930, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.4, dict(ground=GROUND, squash=True, arms='point', point=(500, 760), look=(500, 760), expr='smile', face=None)),
    (3.14, dict(arms='point', point=(330, 1110), look=(330, 1110), expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(2.1, (540, 860, 1.06)), (3.14, (500, 900, 1.14), 'io'), (4.55, (500, 900, 1.16), 'io')],
              kicks=[(2.2, 0.1, 500, 760), (3.14, 0.2, 330, 1110), (3.6, 0.1, 600, 1080)], shakes=[(3.14, 0.25, 10)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 2.15, 500, 760, GLOW, hold=True, r=640)
    photo(fg, t, 2.2, 9.0, 'ioniq6', 500, 760, 900, 0, 3, 'THE REAL CAR', fit=True)
    if t >= 3.14:
        k = fx.slam(t, 3.14) * popin(t, 3.14, 0.2)
        blit(fg, fx.big('badge', 'CD 0.21', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 330, 1110, k, k, -4, anchor='center')
        fx.burst(fg, t, 3.14, 330, 1110, GLOW, n=14, seed=21); fx.sparkles(fg, t, 330, 1110, 500, 160, n=6, seed=22)
    if t >= 3.6:
        k = popin(t, 3.6, 0.25)
        blit(fg, fx.big('tag', 'CLAIMED', '#fff6e0', '#d6303a', s=7), 640, 1180, k, k, 8, anchor='center')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the lowest it has ever achieved
PTS = [(140, 560), (300, 660), (440, 640), (580, 760), (720, 820), (880, 960)]   # a falling record line (no values)
def drawn(t): return oc(prog(t, 4.6, 0.9))
P3 = Presenter([
    (4.5, dict(path=Track([(4.5, (-200, 300)), (4.85, (130, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (4.85, dict(ground=GROUND, squash=True, arms='point', point=(880, 960), look=(880, 960), expr='smile', face=None)),
    (5.5, dict(arms='cheer', point=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(4.55, (540, 860, 1.08)), (5.5, (620, 900, 1.18), 'io'), (6.7, (620, 900, 1.2), 'io')],
              kicks=[(4.69, 0.1, 540, 700), (5.5, 0.22, 880, 960), (5.78, 0.1, 620, 640)], shakes=[(5.5, 0.3, 10)])


def shot_lowest(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    k = popin(t, 4.55, 0.25)
    if k > 0.02:
        d.rectangle((100, 480, 990, 1080), fill=(18, 19, 23, 230), outline=(150, 156, 170), width=6)
        for y in range(540, 1080, 90): d.line([(110, y), (980, y)], fill=(40, 42, 52), width=3)
        u = drawn(t) * (len(PTS) - 1); n = int(u)
        pts = PTS[:n + 1] + ([(lerp(PTS[n][0], PTS[n + 1][0], u - n), lerp(PTS[n][1], PTS[n + 1][1], u - n))] if n < len(PTS) - 1 else [])
        if len(pts) > 1: d.line(pts, fill=(150, 214, 255), width=12)
        for p in pts[:-1]: d.rectangle((p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12), fill=(150, 214, 255))
        if drawn(t) >= 1:
            ks = popin(t, 5.5, 0.25)
            blit(fg, fx.big('star'), 880, 960, ks * 1.2, ks * 1.2, 8 * math.sin(t * 5), anchor='center')
            fx.burst(fg, t, 5.5, 880, 960, GLOW, n=14, seed=31); fx.ring(fg, t, 5.5, 880, 960, GLOW, r1=300)
    if t >= 5.5:
        kb = fx.slam(t, 5.5) * popin(t, 5.5, 0.2)
        blit(fg, fx.big('badge', 'LOWEST EVER', '#ffd23f', '#1a1a2e', '#e8b923', s=9), 540, 640, kb, kb, -3 + 2 * math.sin(t * 5), anchor='center')
        fx.sparkles(fg, t, 540, 640, 760, 220, n=7, seed=32)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: less drag, less energy
def car_x4(t): return lerp(-380, 1460, prog(t, 6.75, 3.15))
CAM4 = Camera(W, H, [(6.7, (540, 920, 1.14)), (8.15, (560, 900, 1.2), 'io'), (9.95, (560, 900, 1.16), 'io')],
              kicks=[(6.79, 0.12, 540, 860), (7.62, 0.08, 540, 900), (8.15, 0.14, 820, 600), (9.37, 0.1, 540, 860)])


def shot_smooth(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    tunnel_set(fg, t)
    cx = car_x4(t)
    draw_car(fg, 'silver', cx, CS, dist=cx)
    fx.contact_shadow(fg, cx, GROUND, 620, s=CS)
    tunnel(fg, t, cx, calm=lambda x: 1.0 if x < cx - 300 else 0.0 if x > cx + 360 else 1 - (x - cx + 300) / 660)
    if t >= 8.15:                                    # energy meter: barely moves
        k = popin(t, 8.15, 0.25)
        blit(fg, up(battery(round((1 - 0.08 * prog(t, 8.15, 1.6)) * 17) / 17), 10), 820, 600, k, k, 0, anchor='center')
        blit(fg, fx.big('label', 'ENERGY', '#5adc78', s=7), 480, 600, k, k, anchor='center')
        fx.gsparkles(fg, t, 820, 600, 360, 160, n=6, seed=41)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


shot_teaser, TEASE_CUES = kit.teaser(9.95, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_tunnel), (2.1, shot_photo), (4.55, shot_lowest), (6.7, shot_smooth), (9.95, shot_teaser)]
TRANS = {1: (2.1, 2.3, 'whip', dict(dx=1)), 2: (4.55, 4.75, 'push', None), 3: (6.7, 6.9, 'whip', dict(dx=0, dy=1)), 4: (9.95, 10.15, 'whip', dict(dx=1))}
KEYCOL = {'hyundai': YEL, 'ioniq': YEL, 'drag': YEL, '0.21': YEL, 'lowest': GRN, 'achieved': YEL,
          'energy': GRN, 'pushing': YEL, 'air': YEL}
CUES = [
    (0.0, 'whoosh', 0.7), (0.05, 'pop', 0.5), (0.4, 'whoosh', 0.3), (1.0, 'whoosh', 0.4), (1.37, 'pop', 0.4),
    (2.2, 'pop', 0.7), (2.22, 'sparkle', 0.5), (3.14, 'stamp', 0.8), (3.16, 'sparkle', 0.6), (3.6, 'pop', 0.5),
    (4.6, 'slide_down', 0.5), (5.5, 'ding', 0.9), (5.52, 'stamp', 0.6), (5.78, 'sparkle', 0.5),
    (6.75, 'whoosh', 0.8), (6.79, 'pop', 0.5), (7.6, 'whoosh', 0.5), (8.15, 'pop', 0.6), (8.17, 'sparkle', 0.5), (9.37, 'ding', 0.5),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
