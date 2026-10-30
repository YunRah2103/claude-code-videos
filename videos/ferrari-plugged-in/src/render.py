"""Renders 'Ferrari, plugged in': the brand's first plug-in hybrid road car, the SF90 Stradale, about 1,000 hp, and
it charges from a socket.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, rev counter, mixer). Word times
come from align.py -> words.json (aligned on out/ferrari-plugged-in/vo_final.wav, the audio that ships; the 9.6 s
read gets a 1.8 s silent hook and a little more air after each sentence). The car is a generic red pixel supercar
with no badges or lettering; the real car appears only in the framed Commons photo.
Shots:
  1 plug     0.00  garage: the red supercar rolls up to a wall socket, the plug flies over and clicks in; 'Ferrari, plugged in.'
  2 photo    4.00  the framed real photo appears beside the car; FIRST PLUG-IN tag
  3 power    6.95  a V8 with a battery beside it filling up, power counter to ~1,000 HP; 'about 1,000 horsepower'
  4 charge   9.30  back at the socket: plugged in again, charge flows along the cable, CHARGING
  5 teaser  11.55  shared NEXT EPISODE ending
"""
import math, os, sys
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
from pixanim.grid import up
from pixanim.autos import supercar, v12, battery, bolt, socket, plug, cable

WORDS = kit.load_words(HERE)
DUR, END_T = 14.2, 11.56
CS = 6
SOCK = (950, 930)                                       # wall socket (screen-ish world px)
CLICK1, CLICK2 = 1.25, 9.41                             # plug clicks in: hook, then 'plugged'


def car_x(t): return lerp(-500, 470, oc(prog(t, 0.0, 0.85)))
def port(x): return x - 54 * CS + 82 * CS, GROUND - (36 - 18) * CS     # charge flap on the front wing (grid 80..84, 17..20)


def plug_pos(t, t0):
    """Plug flies from the car's port to the socket over 0.35 s ending at t0, with an arc."""
    a, b = port(470), (SOCK[0] - 60, SOCK[1] + 6)
    u = oc(prog(t, t0 - 0.35, 0.35))
    return lerp(a[0], b[0], u), lerp(a[1], b[1], u) - 160 * math.sin(math.pi * u)


def plug_scene(fg, t, t0, lit_from, x=470):
    """Socket on the wall, plug + cable from the car; the socket glows and charge dots run once plugged."""
    blit(fg, up(socket(t >= lit_from), 7), *SOCK, 1, 1, 0, anchor='center')
    if t < t0 - 0.35: return
    px, py = plug_pos(t, t0)
    d = ImageDraw.Draw(fg); a = port(x)
    cable(d, a, (px - 50, py + 6), sag=60 + 40 * (1 - clamp((t - t0) / 0.3)), w=16, col=(26, 26, 46))
    cable(d, a, (px - 50, py + 6), sag=60 + 40 * (1 - clamp((t - t0) / 0.3)), w=9, col=(44, 46, 58))
    blit(fg, up(plug(), 6), px, py, 1, 1, 0, anchor='center')
    if t >= t0:
        fx.ring(fg, t, t0, *SOCK, (60, 220, 110), r1=220); fx.burst(fg, t, t0, *SOCK, GLOW, n=10, r0=60, r1=220, seed=int(t0 * 10))
        for i in range(4):                                                           # charge dots run to the car
            u = ((t - t0) * 1.4 + i / 4) % 1
            cx, cy = lerp(SOCK[0] - 100, a[0], u), lerp(SOCK[1], a[1], u) + 60 * math.sin(math.pi * u)
            d.rectangle((cx - 9, cy - 9, cx + 9, cy + 9), fill=(255, 210, 63)); d.rectangle((cx - 4, cy - 4, cx + 4, cy + 4), fill=(255, 250, 200))


# ================================================================== shot 1: hook, plugged in
P1 = Presenter([
    (1.85, dict(path=Track([(1.85, (-200, 500)), (2.25, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (2.25, dict(ground=GROUND, squash=True, arms='point', point=(470, 1000), look=(470, 1000), expr='grin', face=None)),
    (3.1, dict(arms='thumb', point=None, look=None, look_camera=True, expr='smirk')),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (520, 1000, 1.18)), (0.0, (520, 1000, 1.18)), (0.85, (560, 980, 1.14), 'io'), (CLICK1, (760, 960, 1.26), 'io'),
                     (2.4, (560, 960, 1.12), 'io'), (4.0, (560, 960, 1.14))],
              kicks=[(0.85, 0.1, 470, 1100), (CLICK1, 0.22, *SOCK), (2.75, 0.1, 470, 1000)], shakes=[(0.85, 0.2, 8), (CLICK1, 0.25, 10)])


def shot_plug(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car_x(t); stop = t >= 0.85
    fx.contact_shadow(fg, x + 20, GROUND, 600, s=CS)
    rock = math.exp(-max(0, t - 0.85) * 6) * stop
    blit(fg, up(supercar('rosso', int(x * 0.5) % 360 // 15 * 15, True, 1.0 if t >= CLICK1 else 0.3), CS), x, GROUND, 1, 1, -2 * rock * math.sin(t * 20))
    if not stop: fx.speed_lines(fg, 0.5, int(t * 12) % 5, col=(200, 204, 220))
    else: fx.dust(fg, t, 0.85, x + 200, GROUND, n=10, seed=4)
    plug_scene(fg, t, CLICK1, CLICK1)
    if t >= 2.6:                                                    # battery once the hook title has gone
        k = popin(t, 2.6, 0.25)
        lvl = 0.2 + 0.6 * prog(t, 2.6, 1.4)
        blit(fg, up(battery(round(lvl * 10) / 10), 5), 470, 700, k, k, 4 * math.sin(t * 3), anchor='center')
        blit(fg, up(bolt(), 6), 560, 640, k, k, 10, anchor='center')
    dg.label(fg, t, 2.75, 'PLUG-IN HYBRID', port(470), (620, 590), '#7fe3a0', '#1a1a2e', '#3cc85a', s=8, t1=3.9)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.6, 'Ferrari,', YEL, 470, 130, -3)
    title(cv, t, CLICK1, 2.6, 'plugged in.', YEL, 620, 130, 2)
    title(cv, t, 7.42, 9.2, 'about 1,000 horsepower', RED, 470, 100, -2)
    photo(cv, t, 4.15, 6.85, 'sf90', 470, 600, 700, rot=-4, label='THE REAL CAR', hq=True)


# ================================================================== shot 2: the real car beside the pixel one
P2 = Presenter([
    (4.0, dict(path=Track([(4.0, (1300, 500)), (4.4, (930, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (4.4, dict(ground=GROUND, squash=True, arms='point', point=(470, 660), look=(470, 660), expr='smile', face=None)),
    (5.18, dict(arms='cheer', point=None, look=None, look_camera=True, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(4.0, (540, 960, 1.08)), (5.18, (540, 980, 1.14), 'io'), (6.95, (540, 980, 1.18), 'io')],
              kicks=[(4.2, 0.08, 470, 660), (5.18, 0.14, 540, 1000)])


def shot_photo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 560, GROUND, 520, s=5)
    blit(fg, up(supercar('rosso', 0, True), 5), 560, GROUND)
    if t >= 4.43:
        k = popin(t, 4.43, 0.25) * popout(t, 6.8)
        blit(fg, fx.big('tag', 'FIRST PLUG-IN', '#fff6e0', '#d6303a', s=7), 520, 950, k, k, -5 + 2 * math.sin(t * 4), anchor='center')
    if t >= 5.18: fx.sparkles(fg, t, 560, GROUND - 120, 600, 200, n=8, seed=21); fx.confetti(fg, t, 5.2, 560, 800, n=24, seed=22)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: about 1,000 hp, battery beside the engine
def hp(t): return int(round(1000 * oc(prog(t, 7.61, 0.6)) / 10) * 10)
def lvl3(t): return 0.1 + 0.9 * io(prog(t, 7.2, 1.6))
CAM3 = Camera(W, H, [(6.95, (540, 960, 1.04)), (8.11, (540, 940, 1.14), 'io'), (9.3, (540, 940, 1.16))],
              kicks=[(7.13, 0.08, 400, 960), (7.61, 0.12, 540, 1110), (8.11, 0.2, 540, 1110)], shakes=[(8.11, 0.3, 12)])


def shot_power(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 7.0, 0.3)
    blit(fg, up(v12(int(t * 20) % 8, n=4), 9), 370, 930, k, k, 0, anchor='center')
    k2 = popin(t, 7.13, 0.3)
    blit(fg, up(battery(round(lvl3(t) * 10) / 10), 7), 820, 930, k2, k2, 3 * math.sin(t * 3), anchor='center')
    if t >= 7.2:                                                    # bolts hop from the battery to the engine
        for i in range(3):
            u = ((t - 7.2) * 1.6 + i / 3) % 1
            blit(fg, up(bolt(), 5), lerp(720, 520, u), 930 - 90 * math.sin(math.pi * u), 1, 1, 0, anchor='center')
    dg.label(fg, t, 7.2, 'V8', (370, 800), (300, 690), '#ffffff', '#1a1a2e', '#d6d9e2', s=9)
    dg.label(fg, t, 7.4, 'BATTERY', (820, 790), (760, 690), '#7fe3a0', '#1a1a2e', '#3cc85a', s=8)
    if t >= 7.61:
        kk = popin(t, 7.61, 0.25) * (fx.slam(t, 8.11) if t >= 8.11 else 1)
        blit(fg, fx.big('badge', f'{hp(t):,} HP', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 540, 1110, kk, kk, -2 + 2 * math.sin(t * 5), anchor='center')
    if t >= 8.11:
        fx.burst(fg, t, 8.11, 540, 1110, RED, n=18, seed=31); fx.ring(fg, t, 8.11, 540, 1110, GLOW, r1=480)
        fx.sparkles(fg, t, 540, 960, 900, 500, n=8, seed=32)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: plugged in to charge
P4 = Presenter([
    (9.3, dict(path=Track([(9.3, (-200, 400)), (9.7, (140, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (9.7, dict(ground=GROUND, squash=True, arms='point', point=SOCK, look=SOCK, expr='smile', face=None)),
    (9.91, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(9.3, (620, 960, 1.14)), (CLICK2, (760, 960, 1.26), 'io'), (11.6, (600, 960, 1.16), 'io')],
              kicks=[(CLICK2, 0.22, *SOCK), (9.91, 0.12, 470, 700)], shakes=[(CLICK2, 0.25, 10)])


def shot_charge(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 490, GROUND, 600, s=CS)
    blit(fg, up(supercar('rosso', 0, True, 1.0), CS), 470, GROUND)
    plug_scene(fg, t, CLICK2, CLICK2)
    if t >= 9.91:
        k = popin(t, 9.91, 0.25)
        blit(fg, up(battery(round((0.3 + 0.7 * prog(t, 9.91, 1.5)) * 10) / 10), 6), 470, 680, k, k, 3 * math.sin(t * 3), anchor='center')
        blit(fg, fx.big('badge', 'CHARGING', '#7fe3a0', '#1a1a2e', '#3cc85a', s=8), 760, 560, k, k, 4, anchor='center')
        fx.gsparkles(fg, t, 470, 700, 500, 300, n=8, seed=41)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


shot_teaser, TEASE_CUES = kit.teaser(11.55, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_plug), (4.0, shot_photo), (6.95, shot_power), (9.3, shot_charge), (11.55, shot_teaser)]
TRANS = {1: (4.0, 4.2, 'whip', dict(dx=1)), 2: (6.95, 7.15, 'iris', (540, 960)), 3: (9.3, 9.5, 'push', None),
         4: (11.55, 11.75, 'whip', dict(dx=1))}
KEYCOL = {'plug-in': GRN, 'car': YEL, 'sf90': RED, 'about': YEL, '1,000': RED,
          'plugged': GRN, 'can': YEL, 'charge': YEL, 'follow': YEL}
CUES = [
    (0.0, 'vroom', 0.7), (0.05, 'pop', 0.6), (0.85, 'screech', 0.5), (0.87, 'thump', 0.4), (CLICK1 - 0.35, 'whoosh', 0.5), (CLICK1, 'click', 1.0),
    (CLICK1 + 0.02, 'ding', 0.7), (CLICK1 + 0.04, 'sparkle', 0.6), (CLICK1 + 0.1, 'pop', 0.5),
    (2.25, 'thump', 0.4), (2.75, 'pop', 0.6), (3.1, 'sparkle', 0.4),
    (4.15, 'pop', 0.7), (4.4, 'thump', 0.4), (4.43, 'pop', 0.6), (5.18, 'ding', 0.7), (5.2, 'confetti', 0.6),
    (7.0, 'pop', 0.5), (7.13, 'pop', 0.5), (7.2, 'click', 0.4), (7.4, 'click', 0.4), (7.61, 'whoosh', 0.4), (8.11, 'boom', 0.5),
    (8.13, 'stamp', 0.8), (8.15, 'vroom', 0.6),
    (9.7, 'thump', 0.4), (CLICK2 - 0.35, 'whoosh', 0.5), (CLICK2, 'click', 1.0), (CLICK2 + 0.02, 'ding', 0.6), (9.91, 'pop', 0.6),
    (9.93, 'sparkle', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=True, loud=True, crisp=True)

if __name__ == '__main__':
    kit.main()
