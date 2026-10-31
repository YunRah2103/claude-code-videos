"""Renders 'Five minutes to fill, nowhere to fill': the hydrogen Toyota Mirai and the 2023 US station count.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, photo cards, mixer, CLI).
Voiceover: the supplied OpenAI.fm 'cedar' read, trimmed and tightened by align.py; words.json is its forced alignment.
Problem, then cause: the fast refuel, the empty search, the car, the station map, California, then a question.
Car, pumps and map are generic pixel props with no badges or lettering; map dot positions are illustrative (59 total).
The real photo (Commons, see ../assets/credits.json) pops in over shot 3 once ../assets/mirai_duesseldorf.jpg exists.
Shots:
  1 fill      0.00  hook: the car rolls in, the nozzle clicks home, the stopwatch sweeps; '5 MIN'; title 'so where?'
  2 search    2.10  night street: the car drives past petrol pumps, each crossed out NO H2; '?'
  3 mirai     3.75  the car in the garage (+ framed real photo); HYDROGEN label, H2 pump slides in, 5 MIN slam
  4 map       7.35  wall map: 2023 calendar slams, 59 station dots pop in with a counter
  5 calif    11.60  he walks the map toward California, the camera follows; CALIFORNIA badge, the cluster pulses
  6 question 13.15  dashboard: H2 LOW blinks, the nearest station shrinks into the distance; '?'
  7 teaser   15.95  shared NEXT EPISODE ending (~1 s), end card asks for comments
"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, HERE)
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, title, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.props import plug, stopwatch
from pixanim.autos import ev, year_cal
from pixanim.dash import Dashboard
from pixanim import fx, diagram as dg, sprites
from pixanim.fx import blit, popin, popout
from pixanim.grid import up
from mirai_props import pump, map_base, DOTS, proj

WORDS = kit.load_words(HERE)
DUR, END_T = 17.0, 15.95
PHOTO = 'mirai_duesseldorf'
HAS_PHOTO = os.path.isfile(os.path.join(HERE, '..', 'assets', PHOTO + '.jpg'))
H2 = (127, 212, 255)
PETROL = (224, 48, 58)


def car_img(s, spin=0, lights=False, port=0.0): return up(ev('air', int(spin) % 360, lights, port), s)


def flap(cx, s, gy=GROUND): return (cx - 52 * s + 86 * s, gy - 38 * s + 16.5 * s)   # front-wing filler flap of ev('air')


def hose(fg, a, b, sag=60, col=(26, 27, 32)):
    """Fuel hose: a sagging pixel line from a to b."""
    d = ImageDraw.Draw(fg); pts = []
    for k in range(13):
        u = k / 12; x = lerp(a[0], b[0], u); y = lerp(a[1], b[1], u) + sag * math.sin(u * math.pi)
        pts.append((round(x / S) * S, round(y / S) * S))
    d.line(pts, fill=col, width=S + 3)


def flow(fg, t, t0, a, b, sag, n=4, s=4):
    """Hydrogen bubbles running along the hose from a (pump) to b (car)."""
    if t < t0: return
    for k in range(n):
        v = ((t - t0) * 1.6 + k / n) % 1
        x = lerp(a[0], b[0], v); y = lerp(a[1], b[1], v) + sag * math.sin(v * math.pi) - 14
        r = s * 2
        ImageDraw.Draw(fg).ellipse((x - r, y - r, x + r, y + r), fill=H2 + (230,), outline=(26, 26, 46, 255), width=3)


# ================================================================== shot 1: five-minute fill (hook)
CAR1, S1 = 380, 7
PUMP1 = 900
HOLD1 = (PUMP1 - 20, GROUND - 140)
FLAP1 = flap(CAR1, S1)
CLICK_T = 0.6
WATCH1 = (840, 700)
def car1_x(t): return lerp(-480, CAR1, oc(prog(t, -1.0, 1.35)))
def watch1(t): return oc(prog(t, CLICK_T, 1.35))
ROOF1 = GROUND - 34 * S1
P1 = Presenter([
    (0.7, dict(path=Track([(0.7, (-200, 380)), (1.05, (330, ROOF1), 'oc')]), size=6, legs='auto', arms='fly', expr='wow', face=1, ground=None)),
    (1.05, dict(ground=ROOF1, squash=True, arms='point', point=WATCH1, look=WATCH1, expr='grin', face=None)),
], words=WORDS, base_size=6)
CAM1 = Camera(W, H, [(-1.0, (560, 980, 1.2)), (0.0, (560, 980, 1.2)), (CLICK_T, (600, 960, 1.26), 'io'), (1.29, (600, 900, 1.12), 'io'), (2.2, (600, 900, 1.16))],
              kicks=[(CLICK_T, 0.12, *FLAP1), (1.29, 0.16, *WATCH1)], shakes=[(CLICK_T, 0.18, 7), (1.29, 0.25, 10)])


def shot_fill(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car1_x(t)
    blit(fg, up(pump(hose=False), 8), PUMP1, GROUND); fx.contact_shadow(fg, PUMP1, GROUND, 200, s=8)
    fx.contact_shadow(fg, x, GROUND, 640, s=7)
    blit(fg, car_img(S1, x * 0.9, port=1.0 if t >= CLICK_T else 0.0), x, GROUND)
    fx.puff(fg, t, 0.2, x - 360, GROUND - 30, seed=11, drift=(-160, -60))
    u = oc(prog(t, 0.25, CLICK_T - 0.25))                 # nozzle travels from the pump to the flap
    fl = flap(x, S1)
    px, py = lerp(HOLD1[0], fl[0] + 30, u), lerp(HOLD1[1], fl[1], u) - 120 * math.sin(u * math.pi)
    hose(fg, (PUMP1 - 40, GROUND - 120), (px + 30, py), sag=80 * (1 - 0.4 * u))
    blit(fg, up(plug(), 6).transpose(Image.FLIP_LEFT_RIGHT), px, py, anchor='center')
    flow(fg, t, CLICK_T, (PUMP1 - 40, GROUND - 120), (px + 30, py), 48)
    if t >= CLICK_T:
        fx.burst(fg, t, CLICK_T, *fl, H2, n=10, r0=40, r1=180, seed=4)
        k = popin(t, CLICK_T, 0.25) * (1 + 0.06 * math.exp(-max(0, t - 1.95) * 6) * (watch1(t) >= 1))
        blit(fg, up(stopwatch(watch1(t)), 6), *WATCH1, k, k, -4, anchor='center')
        if watch1(t) >= 1: fx.sparkles(fg, t, *WATCH1, 320, 320, n=6, seed=6)
    if t >= 1.29:
        k = fx.slam(t, 1.29) * popin(t, 1.29, 0.2)
        blit(fg, fx.big('badge', '5 MIN', '#ffd23f', '#1a1a2e', '#e8b923', s=10), WATCH1[0] - 20, WATCH1[1] + 200, k, k, 4, anchor='center')
        fx.ring(fg, t, 1.29, *WATCH1, GLOW, r1=360); fx.burst(fg, t, 1.29, *WATCH1, GLOW, n=14, seed=5)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: nowhere to fill (night street)
S2, CAR2 = 4, 470
PUMP_T = (2.47, 2.92)                                      # each pump is crossed out on 'can't' and 'anywhere'
V2 = 1300                                                  # street scroll speed, px/s
def pump2_x(t, k): return 700 + V2 * (PUMP_T[k] - t)          # each pump is mid-frame when it is crossed out
CAM2 = Camera(W, H, [(2.1, (540, 1000, 1.22)), (3.42, (520, 960, 1.3), 'io'), (3.95, (520, 960, 1.32))],
              kicks=[(PUMP_T[0], 0.1, 700, 900), (PUMP_T[1], 0.12, 500, 900), (3.42, 0.16, CAR2, ROAD_Y - 260)])


def shot_search(t):
    img = street(t, (t - 2.1) * V2); fg = layer()
    for k in range(2):
        x = pump2_x(t, k)
        if -200 < x < W + 200:
            blit(fg, up(pump(cap=PETROL), 5), x, ROAD_Y - 120); fx.contact_shadow(fg, x, ROAD_Y - 120, 130, s=5)
            if t >= PUMP_T[k]:
                kx = fx.slam(t, PUMP_T[k]) * popin(t, PUMP_T[k], 0.2)
                blit(fg, fx.big('xmark', s=11), x, ROAD_Y - 200, kx, kx, 0, anchor='center')
                blit(fg, fx.big('tag', 'NO H2', s=6), x, ROAD_Y - 360, kx, kx, -6 + 3 * math.sin(t * 5), anchor='center')
                fx.burst(fg, t, PUMP_T[k], x, ROAD_Y - 200, RED, n=10, seed=20 + k)
    y = ROAD_Y + 20 + 3 * math.sin(t * 9)
    blit(fg, car_img(S2, t * 900, lights=True), CAR2, y)
    kit.headlights(fg, CAR2 + 200, y - 60)
    fx.puff(fg, t, 2.15, CAR2 - 220, y - 20, seed=60, drift=(-300, -40), col=(200, 204, 214))
    fx.speed_lines(fg, 0.7, int(t * 12) % 5, col=(200, 204, 220))
    for i in range(3):
        t0 = 3.42 + i * 0.1
        if t >= t0:
            kq = popin(t, t0, 0.25)
            blit(fg, fx.big('glyph', '?', '#e0303a', s=11), CAR2 - 160 + i * 150, ROAD_Y - 300 - 50 * (i == 1), kq, kq, 10 * math.sin(t * 6 + i), anchor='center')
    return CAM2.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 3: the Mirai (real photo + hydrogen + 5 minutes)
S3, CAR3 = 7, 430
FLAP3 = flap(CAR3, S3)
PUMP3_X = 920
HYD_T, PUMP_IN, FIVE_T = 4.87, 5.73, 6.47
def pump3_x(t): return lerp(1300, PUMP3_X, oc(prog(t, PUMP_IN, 0.4)))
WATCH3 = (820, 560)
P3 = Presenter([
    (3.7, dict(path=Track([(3.7, (-220, GROUND)), (4.25, (130, GROUND), 'oc')]), size=6, legs='auto', arms='talkR', expr='talk', face=1, ground=GROUND)),
    (4.25, dict(squash=True, arms='point', point=(CAR3, GROUND - 200), look=(CAR3, GROUND - 200), expr='smile', face=None)),
    (HYD_T, dict(arms='pointup', point=(400, 800), look=(400, 800), expr='wow')),
    (FIVE_T, dict(arms='cheer', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(3.75, (540, 900, 1.08)), (HYD_T, (540, 940, 1.14), 'io'), (FIVE_T, (620, 860, 1.14), 'io'), (7.4, (620, 860, 1.18))],
              kicks=[(4.2, 0.08, 540, 640), (HYD_T, 0.1, 300, 880), (FIVE_T, 0.2, *WATCH3)], shakes=[(FIVE_T, 0.3, 12)])


def shot_mirai(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR3, GROUND, 640, s=7)
    blit(fg, car_img(S3, 0, port=0.6 if t >= PUMP_IN + 0.4 else 0.0), CAR3, GROUND, 1, 1 + 0.008 * math.sin(t * 4))
    if t >= HYD_T:                                          # hydrogen: bubbles rise from the car, label pops
        fx.gsparkles(fg, t, CAR3 - 120, GROUND - 260, 420, 200, n=10, seed=33, col='#7fd4ff')
    dg.label(fg, t, HYD_T, 'HYDROGEN', (CAR3 - 140, GROUND - 160), (400, 800), '#7fd4ff', '#1a1a2e', '#4fa8d8', s=8, t1=FIVE_T - 0.45)
    if t >= PUMP_IN:
        x = pump3_x(t)
        blit(fg, up(pump(hose=False), 8), x, GROUND); fx.contact_shadow(fg, x, GROUND, 200, s=8)
        fx.dust(fg, t, PUMP_IN + 0.4, x - 60, GROUND - 10, seed=8, dirx=-1)
        a = (x - 40, GROUND - 120)
        hose(fg, a, (FLAP3[0] + 30, FLAP3[1]), sag=70)
        blit(fg, up(plug(), 6).transpose(Image.FLIP_LEFT_RIGHT), FLAP3[0] + 30, FLAP3[1], anchor='center')
        flow(fg, t, PUMP_IN + 0.4, a, (FLAP3[0] + 30, FLAP3[1]), 40)
    if t >= FIVE_T - 0.35:
        k = popin(t, FIVE_T - 0.35, 0.25)
        blit(fg, up(stopwatch(oc(prog(t, FIVE_T - 0.35, 0.6))), 6), *WATCH3, k, k, 4, anchor='center')
    if t >= FIVE_T:
        k = fx.slam(t, FIVE_T) * popin(t, FIVE_T, 0.2)
        blit(fg, fx.big('badge', '5 MIN', '#ffd23f', '#1a1a2e', '#e8b923', s=11), WATCH3[0] - 40, WATCH3[1] + 220, k, k, -4, anchor='center')
        fx.ring(fg, t, FIVE_T, *WATCH3, GLOW, r1=400); fx.burst(fg, t, FIVE_T, *WATCH3, GLOW, n=16, seed=34)
        fx.sparkles(fg, t, *WATCH3, 420, 420, n=7, seed=35)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shots 4-5: the map, then California
MX, MY = 90, 300                                            # map top-left on screen (100x58 grid at S)
def dot_xy(lat, lon): x, y = proj(lon, lat); return (MX + x * S, MY + y * S)
CA_PT = dot_xy(36.0, -119.8)
YEAR_T, COUNT_T, COUNT_D = 7.6, 9.07, 1.5
def n_dots(t): return int(len(DOTS) * clamp((t - COUNT_T) / COUNT_D))
def dot_t(i): return COUNT_T + COUNT_D * (i + 1) / len(DOTS)
WALK0, WALK1, CA_T = 11.6, 12.35, 12.39
P4 = Presenter([
    (7.3, dict(path=Track([(7.3, (1300, 400)), (7.7, (900, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (7.7, dict(ground=GROUND, squash=True, arms='point', point=(540, 600), look=(540, 600), expr='smile', face=None)),
    (8.86, dict(arms='shrug', point=None, look=None, look_camera=True, expr='smirk', squash=True)),
    (COUNT_T, dict(arms='point', point=(540, 560), look=(540, 560), expr='wow')),
    (WALK0, dict(path=Track([(WALK0, (900, GROUND)), (WALK1, (300, GROUND), 'io')]), legs='auto', arms='point', point=CA_PT, look=CA_PT, expr='talk')),
    (WALK1, dict(squash=True, legs='stand', arms='pointup', point=CA_PT, look=CA_PT, expr='grin')),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(7.35, (540, 820, 1.04)), (COUNT_T, (540, 760, 1.1), 'io'), (11.05, (540, 800, 1.02), 'io'),
                     (WALK0, (560, 820, 1.04)), (WALK1, (330, 760, 1.42), 'io'), (13.2, (330, 740, 1.48))],
              kicks=[(7.45, 0.08, 540, 560), (YEAR_T, 0.14, 860, 330), (COUNT_T, 0.1, 540, 560), (11.05, 0.12, 540, 560), (CA_T, 0.2, *CA_PT)],
              shakes=[(YEAR_T, 0.2, 8), (CA_T, 0.3, 10)])


def shot_map(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 7.45, 0.3)
    if k > 0.02:
        m = up(map_base(), S)
        blit(fg, m, MX + m.width / 2, MY + m.height, k, k, 0)
        d = ImageDraw.Draw(fg)
        for i, (lat, lon, ca) in enumerate(DOTS[:n_dots(t)]):
            x, y = dot_xy(lat, lon)
            kd = popin(t, dot_t(i), 0.18); pulse = 1 + 0.35 * math.exp(-max(0, t - CA_T) * 4) * ca * (t >= CA_T)
            r = 8 * kd * pulse; col = (255, 77, 109) if ca else (255, 210, 63)
            d.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=(26, 26, 46)); d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        if 0 < n_dots(t) < len(DOTS):
            x, y = dot_xy(*DOTS[n_dots(t) - 1][:2]); fx.sparkles(fg, t, x, y, 80, 80, n=3, seed=n_dots(t))
    if t >= YEAR_T:                                         # 2023 calendar slams onto the map corner
        ky = fx.slam(t, YEAR_T) * popin(t, YEAR_T, 0.2)
        blit(fg, up(year_cal(2023), 6), 860, 360, ky, ky, 6, anchor='center')
        fx.burst(fg, t, YEAR_T, 860, 360, GLOW, n=12, seed=41)
    if COUNT_T <= t < WALK0 + 0.2:                          # counter ticks up with the dots
        kc = popin(t, COUNT_T, 0.25) * popout(t, WALK0, 0.2) * (1 + 0.08 * math.exp(-max(0, t - COUNT_T - COUNT_D) * 5) * (n_dots(t) == len(DOTS)))
        blit(fg, fx.big('badge', f'{n_dots(t)} STATIONS', '#ffffff' if n_dots(t) < len(DOTS) else '#ffd23f', '#1a1a2e', '#d6d9e2', s=9),
             470, 950, kc, kc, -3, anchor='center')
        if COUNT_T + COUNT_D <= t < WALK0: fx.ring(fg, t, COUNT_T + COUNT_D, 470, 950, GLOW, r1=360)
    if t >= 11.05: fx.ring(fg, t, 11.05, 540, 560, WHITE, life=0.4, r1=520)
    if t >= CA_T:
        fx.ring(fg, t, CA_T, *CA_PT, RED, r1=300); fx.burst(fg, t, CA_T, *CA_PT, GLOW, n=14, seed=44)
        kb = popin(t, CA_T, 0.25)
        blit(fg, fx.big('badge', 'CALIFORNIA', '#ffd23f', '#1a1a2e', '#e8b923', s=6), CA_PT[0] + 40, CA_PT[1] - 230, kb, kb, -5, anchor='center')
        fx.sparkles(fg, t, *CA_PT, 260, 260, n=6, seed=45)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 6: the question (dashboard)
D = Dashboard(outside=GAR.base())
NEAR_T, FAR_T, OFF_T = 14.35, 15.12, 15.53
FAR = (560, 300)                                            # through the windscreen
def far_scale(t): return lerp(5, 1.4, io(prog(t, NEAR_T, FAR_T + 0.3 - NEAR_T)))
P6 = Presenter([
    (13.1, dict(path=Track([(13.1, (1300, 700)), (13.5, (780, 1160), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (13.5, dict(ground=1160, squash=True, arms='think', look=(400, 800), expr='think', face=None)),
    (NEAR_T, dict(arms='pointup', point=FAR, look=FAR, expr='wow')),
    (OFF_T, dict(arms='shrug', point=None, look=None, look_camera=True, expr='smirk', squash=True)),
], words=WORDS, base_size=6)
CAM6 = Camera(W, H, [(13.15, (540, 900, 1.08)), (NEAR_T, (560, 800, 1.14), 'io'), (FAR_T, (560, 760, 1.2), 'io'), (16.0, (560, 760, 1.22))],
              kicks=[(13.22, 0.08, 790, 985), (NEAR_T, 0.1, *FAR), (OFF_T, 0.16, 780, 900)])


def shot_question(t):
    low = int(t * 3) % 2 == 0
    img = D.frame(t, rpm_deg=200 + 6 * math.sin(t * 7), speed_deg=170, lcd='H2 LOW' if low else '      ')
    fg = layer()
    if t >= NEAR_T:
        ks = far_scale(t) * popin(t, NEAR_T, 0.25)
        blit(fg, up(pump(), 1), FAR[0], FAR[1] + 40, ks, ks, 0)
        dg.label(fg, t, NEAR_T + 0.1, 'NEAREST H2', (FAR[0], FAR[1] - 30 * far_scale(t)), (FAR[0] - 160, FAR[1] - 100), '#7fd4ff', '#1a1a2e', '#4fa8d8', s=6)
    if t >= FAR_T: fx.speed_lines(fg, 0.5, int(t * 12) % 5, horizontal=False, col=(200, 204, 220))
    if t >= OFF_T:
        kq = popin(t, OFF_T, 0.25) * (1 + 0.1 * math.sin(t * 9))
        blit(fg, fx.big('glyph', '?', '#e0303a', s=16), 300, 760, kq, kq, 8 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, OFF_T, 300, 760, seed=91)
    P6.draw(fg, t)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)


def overlay(cv, t):
    title(cv, t, 0.1, 2.05, 'fills up in 5 min', WHITE, 360, 110, -3)
    title(cv, t, 0.9, 3.6, 'so where?', YEL, 500, 150, 3)
    kit.photo_hq(cv, t, 3.95, 6.3, PHOTO, 540, 560, 720, rot=-3, label='THE MIRAI')
    if not HAS_PHOTO: title(cv, t, 4.2, 6.3, 'the Mirai', YEL, 560, 130, -3)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_fill), (2.1, shot_search), (3.75, shot_mirai), (7.35, shot_map), (WALK0, shot_map), (13.15, shot_question), (END_T, shot_teaser)]
TRANS = {1: (2.1, 2.3, 'whip', dict(dx=1)), 2: (3.75, 3.95, 'push', None), 3: (7.35, 7.55, 'whip', dict(dx=0, dy=1)),
         5: (13.15, 13.35, 'iris', CA_PT), 6: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'five': YEL, 'anywhere': RED, "can't": RED, 'mirai': YEL, 'hydrogen': GRN, '2023': YEL, '59': RED,
          'california': YEL, 'long': RED, 'way': RED, 'would': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'vroom', 0.5), (0.3, 'screech', 0.25), (0.25, 'whoosh', 0.3), (CLICK_T, 'click', 0.9), (CLICK_T + 0.02, 'thump', 0.5),
    (CLICK_T + 0.05, 'pop', 0.5)] + [(0.7 + k * 0.2, 'click', 0.3) for k in range(6)] + [
    (0.9, 'pop', 0.6), (1.05, 'thump', 0.4), (1.29, 'stamp', 0.8), (1.31, 'sparkle', 0.6), (1.95, 'ding', 0.8),
    (2.1, 'whoosh', 0.6), (2.15, 'vroom', 0.5), (PUMP_T[0], 'buzzer', 0.4), (PUMP_T[0] + 0.02, 'stamp', 0.6),
    (PUMP_T[1], 'buzzer', 0.4), (PUMP_T[1] + 0.02, 'stamp', 0.6), (3.42, 'pop', 0.5), (3.52, 'pop', 0.5), (3.62, 'pop', 0.5),
    (3.75, 'whoosh', 0.5), (3.95, 'pop', 0.7), (3.97, 'sparkle', 0.6), (4.25, 'thump', 0.4), (HYD_T, 'pop', 0.6), (HYD_T + 0.05, 'sparkle', 0.5),
    (PUMP_IN, 'slide_down', 0.5), (PUMP_IN + 0.4, 'thump', 0.5), (PUMP_IN + 0.42, 'click', 0.6), (FIVE_T - 0.35, 'pop', 0.5),
    (FIVE_T, 'stamp', 0.9), (FIVE_T + 0.02, 'ding', 0.6),
    (7.35, 'whoosh', 0.6), (7.45, 'pop', 0.7), (7.7, 'thump', 0.4), (YEAR_T, 'stamp', 0.8), (8.86, 'pop', 0.4), (COUNT_T, 'pop', 0.6)] + [
    (dot_t(i), 'click', 0.18) for i in range(0, len(DOTS), 4)] + [
    (COUNT_T + COUNT_D, 'cha_ching', 0.6), (11.05, 'whoosh', 0.4), (WALK0, 'slide_down', 0.3), (CA_T, 'boom', 0.4), (CA_T + 0.02, 'ding', 0.8),
    (CA_T + 0.04, 'sparkle', 0.6), (13.15, 'whoosh', 0.6), (13.5, 'thump', 0.4), (NEAR_T, 'pop', 0.6), (NEAR_T + 0.1, 'pop', 0.4),
    (FAR_T, 'whoosh', 0.5), (OFF_T, 'pop', 0.7), (OFF_T + 0.02, 'sparkle', 0.5),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', loud=True, crisp=True,
          end=('car stuff, explained', 'would you? tell me below'))

if __name__ == '__main__':
    kit.main()
