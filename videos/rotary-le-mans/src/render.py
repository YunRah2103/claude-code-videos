"""Renders 'Rotary at Le Mans': the four-rotor car that started 23rd and won in 1991.

Template: videos/ac-idle -> tractors-vs-ferraris shot structure; captions, progress bar, photo cards, mixer and the
NEXT EPISODE ending live in shared/episode.py (corner rev counter on). Word times come from align.py -> words.json
(the tightened voiceover is the timing spine). Speech runs 0-17.3 s; the card holds to 17.6 s. The race car is a
generic orange/green prototype: no sponsor text, no badges.
Shots:
  1 hook    0.00  a Wankel spins like a propeller in the garage spotlight; COULDN'T WIN slams on 'couldn't'
  2 1991    2.75  whip; scoreboard flips to 1991; CAN'T WIN tag is crossed out on 'wrong'
  3 grid    5.30  push; camera runs down a 23-car grid to the prototype at the back; 23RD on '23rd'
  4 rotors  7.85  iris; night: four rotors pop in one by one; 700 HP counter rolls up to redline
  5 finish 10.35  whip; the car blasts through the checkered flag on 'crossed'; JUNE 23 tag, confetti
  6 win    13.30  push; podium in the spotlight: trophy rises, FIRST badge on 'first', flag and confetti on 'win'
  7 teaser 16.30  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, layer, finish, draw_car, title, headlights
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 17.6, 16.3
ORANGE, GREEN = (255, 132, 40), (38, 168, 104)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def proto(spin=0, lights=True):
    """Side-view 1990s Le Mans prototype (100x34 grid): long low tub, bubble canopy, tall rear wing, orange nose and
    green tail split by a white stripe, roundel number. Generic livery, no lettering."""
    img = Image.new('RGBA', (100, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body = [(2, 24), (6, 19), (24, 16), (40, 12), (52, 8), (64, 8), (72, 12), (90, 14), (96, 17), (97, 24), (92, 27), (6, 27)]
    d.polygon(body, fill=ORANGE)
    d.polygon([(52, 8), (64, 8), (72, 12), (90, 14), (96, 17), (97, 24), (92, 27), (46, 27), (40, 12)], fill=GREEN)   # green tail
    d.line([(40, 12), (46, 27)], fill=(250, 250, 250), width=2)                                                     # stripe
    d.polygon([(41, 12), (52, 6), (62, 6), (66, 10), (58, 12)], fill=(30, 34, 46))                                 # canopy
    d.line([(46, 9), (55, 7)], fill=(150, 190, 240))
    d.rectangle((88, 3, 99, 5), fill=(30, 34, 46)); d.line([(92, 5), (92, 14)], fill=(30, 34, 46), width=2)       # rear wing
    d.line([(6, 20), (38, 14)], fill=(255, 196, 130))                                                              # shoulder light
    d.line([(8, 26), (90, 26)], fill=(200, 96, 26))
    d.ellipse((62, 15, 72, 25), fill=(250, 250, 250)); d.text((63, 15), '55', fill=(26, 26, 46))                   # roundel
    if lights:
        d.ellipse((3, 19, 8, 23), fill=(255, 246, 190))
    for cx in (17, 80):
        r = 8
        d.ellipse((cx - r, 26 - r, cx + r, 26 + r), fill=(28, 28, 34))
        d.ellipse((cx - 5, 21, cx + 5, 31), fill=(176, 182, 192))
        for k in range(5):
            a = math.radians(spin + k * 72)
            d.line([(cx, 26), (cx + 4 * math.cos(a), 26 + 4 * math.sin(a))], fill=(96, 100, 110))
        d.ellipse((cx - 1, 25, cx + 1, 27), fill=(40, 42, 48))
    return outline(img)


def _epi(R, e, n=72, cx=0.0, cy=0.0):
    return [(cx + R * math.cos(a) + e * math.cos(3 * a), cy + R * math.sin(a) + e * math.sin(3 * a))
            for a in (2 * math.pi * k / n for k in range(n))]


@lru_cache(None)
def wankel(step):
    """Wankel cutaway (64x48 grid): epitrochoid housing, Reuleaux rotor on its eccentric shaft, spark plugs and a
    firing flash. step 0..59 is one shaft revolution (the rotor turns a third)."""
    th = 2 * math.pi * step / 60
    img = Image.new('RGBA', (64, 48), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    c = (32, 24); R, e = 20, 3.2
    d.polygon(_epi(R + 3, e, cx=c[0], cy=c[1]), fill=(96, 100, 110))
    d.polygon(_epi(R + 1, e, cx=c[0], cy=c[1]), fill=(176, 182, 192))
    d.polygon(_epi(R, e, cx=c[0], cy=c[1]), fill=(28, 30, 40))
    rc = (c[0] + e * math.cos(th), c[1] + e * math.sin(th)); ph = th / 3
    verts = [(rc[0] + (R - 0.5) * math.cos(ph + k * 2 * math.pi / 3), rc[1] + (R - 0.5) * math.sin(ph + k * 2 * math.pi / 3)) for k in range(3)]
    pts = []
    for k in range(3):                                                  # bulged flanks between the apex seals
        a, b = verts[k], verts[(k + 1) % 3]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, ny = mx - rc[0], my - rc[1]; nl = math.hypot(nx, ny) or 1
        for u in range(8):
            s = u / 8; bulge = 2.2 * math.sin(math.pi * s)
            pts.append((a[0] + (b[0] - a[0]) * s + nx / nl * bulge, a[1] + (b[1] - a[1]) * s + ny / nl * bulge))
    fire = (step % 20) < 4
    if fire:                                                            # combustion pocket lights up on the plug side
        d.polygon(_epi(R, e, cx=c[0], cy=c[1])[60:72] + _epi(R, e, cx=c[0], cy=c[1])[0:6] + [(c[0] + 6, c[1])], fill=(255, 170, 40))
    d.polygon(pts, fill=(232, 52, 63))
    d.polygon([(rc[0] + (R - 6) * math.cos(ph + k * 2 * math.pi / 3), rc[1] + (R - 6) * math.sin(ph + k * 2 * math.pi / 3)) for k in range(3)],
              fill=(181, 34, 44))
    for v in verts: d.point(v, fill=(255, 230, 140))                    # apex seals
    d.ellipse((rc[0] - 5, rc[1] - 5, rc[0] + 5, rc[1] + 5), fill=(255, 210, 63))   # rotor gear
    d.ellipse((c[0] - 2, c[1] - 2, c[0] + 2, c[1] + 2), fill=(60, 63, 71))          # eccentric shaft
    for py in (17, 27):                                                 # twin spark plugs
        d.rectangle((60, py, 63, py + 3), fill=(220, 220, 228)); d.point((59, py + 1), fill=(255, 240, 160) if fire else (90, 90, 100))
    d.rectangle((0, 10, 6, 14), fill=(70, 74, 84)); d.rectangle((0, 34, 6, 38), fill=(70, 74, 84))   # ports
    return outline(img)


@lru_cache(None)
def flag(ph):
    """Waving checkered flag (26x30 grid) on a pole; ph 0..11 is the wave phase."""
    img = Image.new('RGBA', (26, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((1, 0, 2, 29), fill=(200, 204, 214))
    for x in range(3, 26):
        off = round(1.6 * math.sin((x / 4.0) + ph * math.pi / 6))
        for y in range(1, 15):
            if ((x - 3) // 3 + (y - 1) // 3) % 2 == 0:
                d.point((x, y + off), fill=(250, 250, 250))
            else:
                d.point((x, y + off), fill=(26, 26, 30))
    return outline(img)


@lru_cache(None)
def trophy():
    """Gold cup with handles on a plinth (24x30)."""
    img = Image.new('RGBA', (24, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    gold, shade, hi = (255, 200, 50), (214, 150, 20), (255, 236, 150)
    d.pieslice((3, -6, 21, 16), 0, 180, fill=gold); d.rectangle((3, 0, 21, 5), fill=gold)
    d.line([(6, 2), (6, 9)], fill=hi); d.arc((0, 1, 7, 9), 90, 270, fill=shade); d.arc((17, 1, 24, 9), 270, 90, fill=shade)
    d.rectangle((10, 15, 14, 21), fill=shade); d.rectangle((7, 21, 17, 23), fill=gold)
    d.rectangle((5, 24, 19, 29), fill=(60, 50, 40)); d.rectangle((8, 26, 16, 27), fill=(214, 150, 20))
    return outline(img)


@lru_cache(None)
def japan_flag():
    img = Image.new('RGBA', (24, 16), (250, 250, 250, 255)); d = ImageDraw.Draw(img)
    d.ellipse((7, 3, 16, 12), fill=(214, 30, 50))
    return outline(img)


def big_text(txt, col, sz=150): return kit.text_img(txt, col, sz)


# ================================================================== shot 1: hook, the Wankel spins like a propeller
EC = (560, 760)
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-220, 400)), (0.2, (-220, 400)), (0.62, (210, GROUND), 'ic')]), size=7, legs='auto', arms='fly',
                expr='wow', ground=None, face=1)),
    (0.62, dict(ground=GROUND, squash=True, arms='point', point=EC, look=EC, expr='grin', face=None)),
    (1.64, dict(arms='shock', expr='shock', squash=True, point=None)),
    (2.3, dict(arms='hips', expr='smirk', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (560, 760, 1.5)), (0.0, (560, 760, 1.5)), (0.6, (540, 860, 1.08), 'io'), (1.6, (560, 800, 1.18), 'io'),
                     (2.8, (560, 790, 1.24))],
              kicks=[(0.0, 0.12, *EC), (0.62, 0.1, 210, 1000), (1.64, 0.18, *EC), (2.3, 0.1, *EC)], shakes=[(0.0, 0.4, 8), (1.64, 0.35, 14)])


def rev1(t): return 1.0 + 2.2 * oc(prog(t, 0.0, 0.5)) + 1.5 * (t >= 1.64) * math.exp(-(t - 1.64) * 2)


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 0.0, *EC, GLOW, hold=True, r=620, n=12)
    step = int(t * 60 * rev1(t)) % 60
    k = popin(t, 0.0, 0.35)
    tilt = 8 * math.sin(t * 2.2)
    for g, a in ((3, 50), (2, 80), (1, 130)):                                    # propeller blur: ghosts of earlier steps
        gh = up(wankel((step - g * 4) % 60), 9).copy(); gh.putalpha(gh.getchannel('A').point(lambda v, a=a: v * a // 255))
        blit(fg, gh, EC[0], EC[1], k, k, tilt - g * 9, anchor='center')
    blit(fg, up(wankel(step), 9), EC[0], EC[1], k, k, tilt, anchor='center')
    for i in range(4):                                                           # exhaust flames on each firing
        if (step + i * 5) % 20 < 4:
            fx.burst(fg, t, t - 0.01, EC[0] - 290, EC[1] - 80 + i * 50, (255, 150, 40), n=6, r0=10, r1=80, seed=10 + i)
    fx.sparkles(fg, t * 1.5, *EC, 640, 520, n=10, seed=11)
    fx.ring(fg, t, 1.64, *EC, RED, life=0.4, r1=460)
    fx.burst(fg, t, 1.64, *EC, RED, n=14, seed=12)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.6, 'THE ENGINE THEY SAID', kit.WHITE, 470, 92, -2)
    if 1.64 <= t < 2.75:
        img = big_text("COULDN'T WIN", RED, 150)
        k = ob(prog(t, 1.64, 0.18)) * (1 + 0.04 * math.sin(t * 10)) * min(1.0, 980 / img.width)
        blit(cv, img, W / 2, 470, k, k, -5 + 2 * math.sin(t * 4), anchor='center')
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 470, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: 1991, they proved them wrong
P2 = Presenter([
    (2.7, dict(path=Track([(2.7, (1300, 500)), (3.05, (830, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (3.05, dict(ground=GROUND, squash=True, arms='point', point=(540, 640), look=(540, 640), face=None, expr='smile')),
    (4.75, dict(arms='cheer', expr='grin', squash=True, point=None, look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.75, (540, 820, 1.2)), (3.95, (540, 760, 1.28), 'io'), (5.3, (540, 800, 1.18), 'io')],
              kicks=[(2.95, 0.14, 540, 640), (3.95, 0.08, 540, 640), (4.75, 0.16, 540, 1000)], shakes=[(4.75, 0.25, 12)])


def year_at(t):
    """Scoreboard rolls 1986 -> 1991, landing on '1991' as he says it."""
    return 1986 + int(round(5 * oc(prog(t, 2.8, 0.45))))


def shot_1991(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 2.95, 540, 640, GLOW, life=1.2, r=600)
    k = popin(t, 2.78, 0.3)
    flip = abs(math.cos((t - 2.8) * math.pi * 11)) if t < 3.25 else 1.0        # digits flip while rolling
    board = fx.big('badge', str(year_at(t)), '#1a1a2e', '#ffd23f', '#11111c', s=16)
    blit(fg, board, 540, 640, k, k * max(0.15, flip), -3 + 2 * math.sin(t * 3), anchor='center')
    fx.burst(fg, t, 3.25, 540, 640, GLOW, n=14, seed=21)
    if t >= 3.95:                                                                # CAN'T WIN tag, crossed out on 'wrong'
        kt = popin(t, 3.95, 0.25)
        blit(fg, fx.big('tag', "CAN'T WIN", '#fff6e0', '#d6303a', t >= 4.75, s=11), 540, 900, kt, kt, 4 * math.sin(t * 5), anchor='center')
    if t >= 4.75:
        kx = ob(prog(t, 4.75, 0.2))
        blit(fg, fx.big('xmark', s=14), 540, 900, kx, kx, anchor='center')
        fx.burst(fg, t, 4.75, 540, 900, RED, n=16, seed=22)
    fx.confetti(fg, t, 4.75, 540, 600, n=40, seed=23)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the grid, 23rd at the back
GRID = [(i, ('red', 'blue', 'silver', 'yellow')[i % 4]) for i in range(22)]
X23W = 400 + 22 * 170 + 200                                                     # the prototype's grid slot (world x)
def cam3_x(t): return lerp(540, X23W, io(prog(t, 5.35, 1.4)))              # dolly from pole to the back of the grid
P3 = Presenter([
    (5.3, dict(path=Track([(5.3, (1300, 300)), (6.2, (1300, 300)), (6.6, (880, kit.ROAD_Y), 'oc')]), size=6, legs='auto', arms='fly',
               expr='wow', face=-1, ground=None)),
    (6.6, dict(ground=kit.ROAD_Y, squash=True, arms='point', point=(540, kit.ROAD_Y - 200), look=(540, kit.ROAD_Y - 200), face=None, expr='grin')),
    (6.84, dict(arms='cheer', squash=True, look=None, look_camera=True)),
], words=WORDS, base_size=6)


def shot_grid(t):
    cx = cam3_x(t)
    world = kit.street(t, 0).crop((0, 0, W, H))
    img = world.copy(); fg = layer()
    ox = cx - W / 2                                                              # the grid world scrolls past the camera
    d = ImageDraw.Draw(fg)
    for i, col in GRID:                                                          # grid boxes and cars, two staggered rows
        x = 400 + i * 170 - ox; y = kit.ROAD_Y - (60 if i % 2 else 0)
        if -300 < x < W + 300:
            d.rectangle((x - 140, y - 4, x + 140, y + 2), fill=(240, 240, 240, 150))
            kit.draw_car(fg, col, x, 3, y=y, sx=1.1, sy=0.75)
            blit(fg, fx.big('badge', str(i + 1), '#ffffff', '#1a1a2e', '#d6d9e2', s=4), x, y - 140, anchor='center')
    x23 = X23W - ox
    fx.rays(fg, t, 6.84, x23, kit.ROAD_Y - 120, GLOW, life=1.0, r=420)
    vib = 3 * math.sin(t * 60)
    fx.contact_shadow(fg, x23, kit.ROAD_Y, 520, s=S, alpha=140)
    blit(fg, up(proto(0), 5), x23, kit.ROAD_Y + vib * 0.3, 1, 1)
    for k in range(5):
        fx.puff(fg, t, 5.6 + k * 0.3, x23 - 260, kit.ROAD_Y - 40, seed=30 + k, life=0.8, size=0.6, drift=(-200, -80), col=(120, 122, 130))
    if t >= 6.84:
        kb = popin(t, 6.84, 0.25) * (1 + 0.05 * math.sin(t * 9))
        blit(fg, fx.big('badge', '23RD', '#ffd23f', '#1a1a2e', '#e8b923', s=12), x23, kit.ROAD_Y - 330, kb, kb, -6 + 3 * math.sin(t * 5),
             anchor='center')
        fx.burst(fg, t, 6.84, x23, kit.ROAD_Y - 330, GLOW, seed=31)
    fx.sparkles(fg, t, x23, kit.ROAD_Y - 120, 560, 200, n=6, seed=32)
    P3.draw(fg, t)
    kit.ROAD.reflect(img, fg, depth=160, strength=0.3)
    img.alpha_composite(fg)
    cam = Camera(W, H, [(5.3, (540, 960, 1.15)), (6.84, (540, 900, 1.3), 'io'), (7.9, (540, 900, 1.32))],
                 kicks=[(6.84, 0.14, x23 - ox, kit.ROAD_Y - 200)], shakes=[(5.35, 1.5, 3)])
    return cam.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: four rotors, 700 horsepower (night)
RC = [(300, 720), (780, 720), (300, 1060), (780, 1060)]
ROT_T = (8.07, 8.25, 8.43, 8.61)
P4 = Presenter([
    (7.85, dict(path=Track([(7.85, (540, -200)), (8.2, (540, GROUND + 80), 'ic')]), size=6, legs='auto', arms='fly', expr='grin', face=1,
                ground=None, visible=False)),
    (9.18, dict(path=Track([(9.18, (-200, 1300)), (9.5, (190, GROUND + 160), 'oc')]), visible=True, ground=GROUND + 160, squash=True,
                arms='cheer', expr='wow')),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(7.85, (540, 900, 1.25)), (8.7, (540, 900, 1.1), 'io'), (9.18, (540, 860, 1.18), 'io'), (10.4, (540, 860, 1.25))],
              kicks=[(8.07, 0.06, *RC[0]), (8.25, 0.06, *RC[1]), (8.43, 0.06, *RC[2]), (8.61, 0.08, *RC[3]), (9.18, 0.16, 540, 600)],
              shakes=[(9.18, 0.8, 9)])


def hp_at(t): return int(round(700 * oc(prog(t, 9.18, 0.55)) / 10) * 10)


def shot_rotors(t):
    img = kit.street(t, 60 * t).convert('RGBA')
    img = Image.blend(img, Image.new('RGBA', (W, H), (6, 8, 20, 255)), 0.45); fg = layer()
    step0 = int(t * 60 * 3.2)
    for i, ((x, y), t0) in enumerate(zip(RC, ROT_T)):
        k = popin(t, t0, 0.3)
        if k <= 0.02: continue
        fx.ring(fg, t, t0, x, y, GRN, life=0.35, r1=260)
        blit(fg, up(wankel((step0 + i * 15) % 60), 6), x, y, k, k, 0, anchor='center')
        blit(fg, fx.big('badge', str(i + 1), '#7fe3a0', '#1a1a2e', '#3cc85a', s=6), x + 150, y - 130, k, k, -6, anchor='center')
    if t >= 8.84:                                                                # they lock together into one engine
        fx.sparkles(fg, t * 1.4, 540, 890, 900, 700, n=12, seed=41)
    if t >= 9.18:
        kh = ob(prog(t, 9.18, 0.2)) * (1 + 0.04 * math.sin(t * 12))
        blit(fg, big_text(f'{hp_at(t)} HP', YEL, 170), 540, 470, kh, kh, -4 + 2 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 9.18, 540, 470, GLOW, n=16, seed=42)
        fx.speed_lines(fg, 0.7, int(t * 12) % 5, col=(255, 210, 120))
    P4.draw(fg, t)
    img.alpha_composite(fg)
    return CAM4.apply(img.convert('RGB'), t, (8, 10, 20))


# ================================================================== shot 5: June 23, across the line
FINISH_X = 760
CAR5 = Track([(10.35, (-120, 0)), (12.16, (FINISH_X - 360, 0)), (12.9, (1900, 0), 'ic')])
def car5_x(t): return CAR5.at(t)[0]
P5 = Presenter([
    (10.35, dict(path=Track([(10.35, (FINISH_X - 40, -200)), (10.7, (FINISH_X - 40, kit.ROAD_Y - 330), 'oc')]), size=5, legs='stand',
                 arms='wave', expr='grin', face=-1, ground=kit.ROAD_Y - 330)),
    (12.16, dict(arms='cheer', expr='wow', squash=True)),
], words=WORDS, base_size=5)
CAM5 = Camera(W, H, [(10.35, (540, 1080, 1.25)), (12.16, (FINISH_X, 1080, 1.38), 'io'), (13.3, (640, 1080, 1.2), 'io')],
              kicks=[(10.85, 0.08, 540, 480), (12.16, 0.2, FINISH_X, kit.ROAD_Y - 120)], shakes=[(12.16, 0.4, 16)])


def shot_finish(t):
    sc = 260 * (t - 10.35)
    img = kit.street(t, sc).convert('RGBA'); cars = layer(); d = ImageDraw.Draw(cars)
    for i in range(14):                                                          # checkered line painted across the road
        d.rectangle((FINISH_X - 18 + (i % 2) * 18, kit.ROAD_Y - 120 + i * 12, FINISH_X + (i % 2) * 18, kit.ROAD_Y - 108 + i * 12),
                    fill=(250, 250, 250))
    d.rectangle((FINISH_X - 48, kit.ROAD_Y - 330, FINISH_X - 32, kit.ROAD_Y), fill=(60, 63, 71))     # marshal's stand
    x = car5_x(t)
    headlights(cars, x + 380, kit.ROAD_Y - 100, 520)
    fx.contact_shadow(cars, x, kit.ROAD_Y, 600, s=S, alpha=150)
    blit(cars, up(proto(int(-x * 1.2) % 360), 7), x, kit.ROAD_Y, 1.08, 0.92)
    if t > 10.6: fx.speed_lines(cars, 0.8, int(t * 12) % 5, col=(220, 224, 234))
    kit.ROAD.reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars)
    fg = layer()
    blit(fg, up(flag(int(t * 14) % 12), 7), FINISH_X - 130, kit.ROAD_Y - 330 - 40 * (t >= 12.16) * math.sin((t - 12.16) * 18))
    if t >= 10.85:
        kd = popin(t, 10.85, 0.25) * popout(t, 12.0)
        blit(fg, fx.big('tag', 'JUNE 23, 1991', '#fff6e0', '#1a1a2e', s=8), 560, 700, kd, kd, -4 + 3 * math.sin(t * 5), anchor='center')
    fx.burst(fg, t, 12.16, FINISH_X, kit.ROAD_Y - 160, GLOW, n=18, r0=60, r1=420, seed=51)
    fx.ring(fg, t, 12.16, FINISH_X, kit.ROAD_Y - 160, (255, 255, 255), life=0.3, r1=380)
    fx.confetti(fg, t, 12.16, FINISH_X, 520, n=60, seed=52)
    if t >= 12.4:
        kp = popin(t, 12.4, 0.25) * (1 + 0.05 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'P1', '#ffd23f', '#1a1a2e', '#e8b923', s=14), 420, 700, kp, kp, -5, anchor='center')
    P5.draw(fg, t)
    img.alpha_composite(fg)
    return CAM5.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 6: first Japanese manufacturer
POD = (540, GROUND - 60)
P6 = Presenter([
    (13.3, dict(path=Track([(13.3, (-200, 400)), (13.7, (190, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (13.7, dict(ground=GROUND, squash=True, arms='present', look=(540, 700), expr='grin', face=None)),
    (14.9, dict(arms='cheer', expr='wow', squash=True, look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM6 = Camera(W, H, [(13.3, (540, 860, 1.3)), (13.8, (540, 840, 1.12), 'io'), (14.9, (540, 760, 1.22), 'io'), (16.3, (540, 780, 1.28))],
              kicks=[(13.47, 0.12, 540, 520), (14.22, 0.08, 540, 560), (14.9, 0.18, 540, 620), (15.81, 0.1, 540, 900)],
              shakes=[(14.9, 0.35, 14)])


def shot_win(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    fx.rays(fg, t, 13.4, 540, 620, GLOW, hold=True, r=700, n=14)
    for x0, x1, h, col in ((160, 300, 60, (150, 156, 170)), (300, 780, 130, (255, 200, 50)), (780, 920, 40, (196, 120, 70))):
        d.rectangle((x0, GROUND - h, x1, GROUND), fill=col); d.rectangle((x0, GROUND - h, x1, GROUND - h + 8), fill=(255, 255, 255, 90))
    blit(fg, fx.big('glyph', '1', '#1a1a2e', s=8), 540, GROUND - 40, anchor='center')
    sr, sv = wob(t, (13.5,), 0.07)
    blit(fg, up(proto(0), 5), 540, GROUND - 130 - 120 * (1 - oc(prog(t, 13.3, 0.3))), sr, sv)
    ty = lerp(GROUND - 260, 700, oc(prog(t, 13.47, 0.5)))
    kt = popin(t, 13.47, 0.3)
    blit(fg, up(trophy(), 10), 540, ty + 10 * math.sin(t * 3), kt, kt, 4 * math.sin(t * 2), anchor='center')
    fx.glint(fg, t, 13.9, 540, ty - 60, r=150)
    if t >= 13.8:
        kj = popin(t, 13.8, 0.25)
        blit(fg, up(japan_flag(), 9), 830, 640 + 8 * math.sin(t * 4), kj, kj, 6 * math.sin(t * 3), anchor='center')
    if t >= 14.9:
        kf = ob(prog(t, 14.9, 0.2)) * (1 + 0.05 * math.sin(t * 10))
        blit(fg, fx.big('badge', '1ST JAPANESE WIN', '#ffd23f', '#d6303a', '#e8b923', s=7), 500, 470, kf, kf, -4 + 2 * math.sin(t * 5),
             anchor='center')
        fx.burst(fg, t, 14.9, 500, 470, GLOW, seed=61)
    fx.confetti(fg, t, 14.9, 540, 400, n=70, seed=62)
    fx.sparkles(fg, t * 1.3, 540, 560, 700, 500, n=12, seed=63)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (2.75, shot_1991), (5.3, shot_grid), (7.85, shot_rotors), (10.35, shot_finish), (13.3, shot_win),
         (END_T, shot_teaser)]
TRANS = {1: (2.75, 2.95, 'whip', dict(dx=-1)), 2: (5.3, 5.5, 'push', None), 3: (7.85, 8.07, 'iris', (EC[0], EC[1])),
         4: (10.35, 10.55, 'whip', dict(dx=1)), 5: (13.3, 13.5, 'push', None), 6: (END_T, END_T + 0.2, 'whip', dict(dx=0, dy=1))}
KEYCOL = {"couldn't": RED, '1991': YEL, 'wrong': RED, '787b': YEL, '23rd': YEL, 'four': GRN, 'rotors': GRN,
          '700': YEL, 'first': YEL, 'japanese': YEL, 'manufacturer': YEL, 'crossed': GRN}
CUES = [
    (0.0, 'vroom', 0.9), (0.05, 'stamp', 0.6), (0.07, 'sparkle', 0.6), (0.62, 'thump', 0.8), (1.64, 'stamp', 1.0), (1.66, 'boom', 0.5),
    (2.3, 'buzzer', 0.4),
    (2.8, 'click', 0.5), (2.9, 'click', 0.5), (3.0, 'click', 0.5), (3.1, 'click', 0.5), (3.25, 'ding', 0.8), (3.27, 'sparkle', 0.6),
    (3.95, 'pop', 0.7), (4.75, 'stamp', 1.0), (4.77, 'confetti', 0.8),
    (5.4, 'vroom', 0.6), (6.6, 'thump', 0.5), (6.84, 'cha_ching', 0.8), (6.86, 'sparkle', 0.6),
    (8.07, 'pop', 0.7), (8.25, 'pop', 0.7), (8.43, 'pop', 0.7), (8.61, 'pop', 0.8), (9.18, 'vroom', 1.0), (9.2, 'boom', 0.5),
    (10.45, 'vroom', 0.9), (10.85, 'pop', 0.6), (11.6, 'screech', 0.3), (12.16, 'boom', 0.7), (12.17, 'confetti', 1.0), (12.4, 'ding', 0.8),
    (13.47, 'slide_down', 0.6), (13.8, 'pop', 0.6), (14.9, 'cha_ching', 0.9), (14.92, 'confetti', 0.9), (15.81, 'ding', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
