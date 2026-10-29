"""Renders 'The Car That Stayed Level': de Gaulle's DS kept level on punctured tyres in 1962.

Template: videos/ac-idle -> tractors-vs-ferraris shot structure; kit in shared/episode.py (corner rev counter on).
Word times come from align.py -> words.json. Speech runs 0-17.2 s; the card holds to 17.5 s. Serious tone: no gags,
no weapons on screen, the bodyguards' deaths shown by their bikes falling back in grey. No tyre count on screen.
The car is a generic pixel DS silhouette with no badges; the framed photo is the presidential DS (credits.json).
Shots:
  1 hook     0.00  night road: the DS skids on two wheels throwing rim sparks; TYRES / PUNCTURED.
  2 attack   3.30  whip; it swerves through muzzle-flash sparks; two escort bikes fall back in grey on 'killed'
  3 tyre     5.80  push; wheel close-up: the tyre sags and hisses on 'punctured'
  4 level    7.05  iris; garage: the sagging DS rises level, spirit-level bubble centres on 'level', sphere cutaway
  5 airport 10.35  whip; calm dusk runway: the DS rolls in to the waiting aircraft; UNHARMED on 'unharmed'
  6 only DS 13.30  push; presidential DS photo; other cars greyed out on 'any other car'
  7 teaser  16.15  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw, ImageEnhance
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, layer, finish, draw_car, photo, title, headlights
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 17.5, 16.15
INK = (24, 25, 34)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def ds(spin=0, sag=0.0, lights=True, ghost=False):
    """Side-view DS silhouette (100x34 grid): long sloping nose, domed roof, covered rear wheel, chrome sill.
    sag 0..1 drops the tail (punctured, before the suspension levels it). ghost draws the X-ray body for the cutaway."""
    img = Image.new('RGBA', (100, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, hi, deep = ((40, 44, 58), (110, 118, 140), (20, 22, 30)) if not ghost else ((90, 150, 230), (170, 210, 255), (50, 100, 180))
    dy = round(3 * sag)
    shell = [(3, 22), (8, 17), (26, 13), (34, 6 + 0), (44, 3), (62, 3), (74, 7), (88, 13 + dy), (97, 17 + dy), (98, 22 + dy), (94, 26 + dy),
             (6, 26)]
    d.polygon(shell, fill=body)
    d.line([(8, 17), (26, 13)], fill=hi); d.line([(44, 3), (62, 3)], fill=hi)
    d.polygon([(36, 7), (45, 4), (52, 4), (52, 12), (32, 12)], fill=(120, 150, 190) if not ghost else (200, 230, 255))   # windscreen
    d.polygon([(55, 4), (61, 4), (71, 8), (73, 12), (55, 12)], fill=(120, 150, 190) if not ghost else (200, 230, 255))
    d.line([(53, 4), (53, 12)], fill=deep)
    d.line([(8, 23), (94, 23 + dy)], fill=(214, 220, 230))                            # chrome strip
    if lights: d.ellipse((2, 17, 7, 21), fill=(255, 246, 190))
    d.rectangle((95, 18 + dy, 98, 20 + dy), fill=(220, 40, 40))
    for cx, covered in ((18, False), (80, True)):
        cy = 27 + (dy if covered else 0)
        d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(22, 22, 28))
        if not covered:
            d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(176, 182, 192))
            for k in range(4):
                a = math.radians(spin + k * 90); d.line([(cx, cy), (cx + 3 * math.cos(a), cy + 3 * math.sin(a))], fill=(96, 100, 110))
        else:
            d.chord((cx - 9, cy - 11, cx + 9, cy + 3), 180, 360, fill=body)            # rear wheel spat
    return outline(img)


@lru_cache(None)
def bike(grey=False):
    """Escort motorcycle with a white-helmeted rider, side view (40x34)."""
    img = Image.new('RGBA', (40, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    c = (lambda col: (int(sum(col) / 3),) * 3) if grey else (lambda col: col)
    for cx in (8, 32):
        d.ellipse((cx - 6, 21, cx + 6, 33), fill=c((26, 26, 32))); d.ellipse((cx - 2, 25, cx + 2, 29), fill=c((150, 156, 170)))
    d.polygon([(8, 25), (14, 19), (28, 18), (32, 25), (20, 24)], fill=c((120, 130, 160)))
    d.rectangle((17, 16, 25, 19), fill=c((40, 46, 64)))
    d.line([(29, 18), (31, 11)], fill=c((200, 204, 214)))
    d.polygon([(16, 17), (19, 8), (25, 8), (26, 16)], fill=c((70, 100, 170)))         # rider's coat
    d.ellipse((18, 1, 26, 9), fill=c((236, 236, 240)))                              # helmet
    d.line([(24, 11), (30, 12)], fill=c((70, 100, 170)), width=2)
    return outline(img)


@lru_cache(None)
def wheel_close(deflate=0.0, spin=0):
    """Big wheel close-up (40x40): tyre squashes flat at the bottom as it deflates."""
    img = Image.new('RGBA', (40, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    flat = round(6 * deflate)
    d.ellipse((1, 1, 38, 38 - 0), fill=(26, 26, 32))
    d.rectangle((0, 38 - flat, 39, 39), fill=(0, 0, 0, 0))
    if flat: d.rectangle((1, 36 - flat, 38, 38 - flat), fill=(26, 26, 32))
    d.ellipse((9, 9 - flat // 2, 30, 30 - flat // 2), fill=(176, 182, 192))
    for k in range(5):
        a = math.radians(spin + k * 72); c = (19.5, 19.5 - flat // 2)
        d.line([c, (c[0] + 9 * math.cos(a), c[1] + 9 * math.sin(a))], fill=(96, 100, 110), width=2)
    d.ellipse((17, 17 - flat // 2, 22, 22 - flat // 2), fill=(60, 63, 71))
    return outline(img)


@lru_cache(None)
def level_tool(off):
    """Spirit level (64x14): green vial, bubble offset -1..1."""
    img = Image.new('RGBA', (64, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 2, 63, 12), fill=(255, 200, 50)); d.rectangle((0, 2, 63, 4), fill=(255, 236, 150))
    d.rounded_rectangle((18, 4, 46, 10), 3, fill=(150, 230, 120))
    d.line([(28, 4), (28, 10)], fill=INK); d.line([(36, 4), (36, 10)], fill=INK)
    bx = 32 + round(11 * off)
    d.ellipse((bx - 3, 5, bx + 3, 9), fill=(236, 255, 230))
    return outline(img)


@lru_cache(None)
def airliner():
    """1960s four-engine airliner, side view (110x34)."""
    img = Image.new('RGBA', (110, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(4, 18), (12, 14), (96, 13), (106, 16), (108, 19), (100, 22), (10, 22)], fill=(222, 226, 236))
    d.polygon([(6, 16), (2, 3), (10, 3), (18, 14)], fill=(200, 206, 220))
    d.polygon([(40, 19), (70, 19), (52, 30), (44, 30)], fill=(180, 186, 200))
    for x in range(22, 92, 5): d.rectangle((x, 15, x + 1, 16), fill=(70, 110, 170))
    d.line([(10, 18), (104, 18)], fill=(60, 110, 200))
    for x in (46, 58): d.rectangle((x, 24, x + 5, 27), fill=(150, 156, 170))
    d.line([(30, 22), (30, 31)], fill=(90, 90, 100)); d.line([(84, 22), (84, 31)], fill=(90, 90, 100))
    d.ellipse((28, 29, 32, 33), fill=(26, 26, 32)); d.ellipse((82, 29, 86, 33), fill=(26, 26, 32))
    return outline(img)


@lru_cache(None)
def runway_world():
    """Calm dusk airfield (180x320 grid, x6): gradient sky, terminal and tower silhouettes, runway in perspective."""
    g = Image.new('RGB', (180, 320)); d = ImageDraw.Draw(g)
    for y in range(200):
        u = y / 200
        d.line([(0, y), (179, y)], fill=(int(30 + 200 * u ** 2), int(32 + 110 * u ** 2), int(70 + 60 * u)))
    d.ellipse((120, 150, 150, 180), fill=(255, 196, 120))                         # low sun
    d.rectangle((0, 186, 179, 319), fill=(40, 46, 56))
    d.rectangle((14, 170, 90, 196), fill=(30, 34, 46))                            # terminal
    for x in range(18, 88, 6): d.rectangle((x, 176, x + 3, 179), fill=(255, 220, 140))
    d.rectangle((100, 150, 106, 196), fill=(30, 34, 46)); d.rectangle((96, 144, 110, 152), fill=(60, 80, 110))   # tower
    d.polygon([(70, 196), (110, 196), (179, 319), (0, 319)], fill=(64, 68, 78))
    for i in range(10):
        u = i / 10; y0 = 200 + 120 * u ** 1.6; y1 = y0 + 3 + 6 * u
        d.rectangle((89 - u, y0, 91 + u, y1), fill=(230, 230, 236))
    for i in range(9):
        u = i / 9; y = 198 + 120 * u ** 1.4
        for x in (70 - 70 * u, 110 + 70 * u): d.rectangle((x, y, x + 1, y + 1), fill=(255, 210, 90))
    return up(g, 6).convert('RGBA')


def desat(img, k):
    return Image.blend(img, ImageEnhance.Color(img).enhance(0.25), k)


# ================================================================== shot 1: hook, on two wheels
DSX = 540
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (1300, 400)), (0.5, (1300, 400)), (0.9, (880, kit.ROAD_Y), 'ic')]), size=6, legs='auto', arms='fly',
                expr='shock', ground=None, face=-1)),
    (0.9, dict(ground=kit.ROAD_Y, squash=True, arms='shock', look=(DSX, 1100), expr='shock', face=None)),
    (2.4, dict(arms='hips', expr='think', look=None, look_camera=True)),
], words=WORDS, base_size=6)
CAM1 = Camera(W, H, [(-1.0, (540, 1080, 1.45)), (0.0, (540, 1080, 1.45)), (0.9, (540, 1060, 1.22), 'io'), (3.3, (540, 1040, 1.3))],
              kicks=[(0.0, 0.12, DSX, 1150), (0.5, 0.12, DSX, 1150), (1.13, 0.1, DSX, 1150), (2.4, 0.12, DSX, 1200)],
              shakes=[(0.0, 2.4, 7), (2.4, 0.25, 12)])


def tilt1(t): return -14 * (1 - io(prog(t, 2.2, 0.25))) + 2 * math.sin(t * 9) * (t < 2.2)


def shot_hook(t):
    img = desat(kit.street(t, 520 * t), 0.35); cars = layer()
    tl = tilt1(t)
    headlights(cars, DSX - 340, kit.ROAD_Y - 90, 420, flip=True)
    fx.contact_shadow(cars, DSX, kit.ROAD_Y, 600, s=S, alpha=150)
    blit(cars, up(ds(int(t * 900) % 360, 0.6 * (t < 2.4)), 7), DSX, kit.ROAD_Y + (40 if tl < -4 else 0), 1.06, 0.95, tl, flip=True)
    if t < 2.4:                                                                    # rim sparks off the road
        for k in range(3):
            fx.burst(cars, t, t - 0.02 - 0.05 * k, DSX + 300, kit.ROAD_Y - 10, (255, 210, 90), n=6, r0=10, r1=110, seed=int(t * 30) + k)
    fx.speed_lines(cars, 0.6, int(t * 12) % 5, col=(200, 204, 214))
    kit.ROAD.reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars); fg = layer()
    for i, t0 in enumerate((0.5, 1.13, 1.65, 1.94)):                                # muzzle-flash sparks from off-screen
        fx.burst(fg, t, t0, (260, 820, 380, 700)[i], (780, 820, 900, 760)[i], (255, 236, 160), n=8, r0=10, r1=120, seed=70 + i)
        fx.ring(fg, t, t0, (260, 820, 380, 700)[i], (780, 820, 900, 760)[i], (255, 255, 255), life=0.15, r1=80)
    P1.draw(fg, t)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, 0.05, 3.1, 'TYRES', kit.WHITE, 430, 120, -2)
    if 0.45 <= t < 3.3:
        img = kit.text_img('PUNCTURED.', RED, 150)
        k = ob(prog(t, 0.45, 0.18)) * (1 + 0.03 * math.sin(t * 9)) * min(1.0, 980 / img.width) * popout(t, 3.1)
        blit(cv, img, W / 2, 590, k, k, -4 + 1.5 * math.sin(t * 3), anchor='center')
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 430, (255, 255, 255), life=0.35, r1=520)


# ================================================================== shot 2: under fire, the escort falls back
def swerve(t): return 70 * math.sin((t - 3.3) * 5.5)
P2 = Presenter([
    (3.3, dict(path=Track([(3.3, (-200, 1300)), (3.6, (150, GROUND + 260), 'oc')]), size=5, legs='auto', arms='fly', expr='shock', face=1,
               ground=None)),
    (3.6, dict(ground=GROUND + 260, squash=True, arms='brace', look=(540, 1150), expr='shock', face=None)),
    (5.2, dict(arms='down2', expr='sad', look=(900, 1200))),
], words=WORDS, base_size=5)
CAM2 = Camera(W, H, [(3.3, (540, 1060, 1.08)), (5.2, (540, 1060, 1.14), 'io'), (5.85, (540, 1060, 1.16))],
              kicks=[(3.87, 0.08, 540, 1100), (4.59, 0.08, 540, 1100)], shakes=[(3.3, 1.9, 9), (5.2, 0.2, 4)])


def shot_attack(t):
    gone = prog(t, 5.2, 0.5)
    img = desat(kit.street(t, 640 * t), 0.4 + 0.3 * gone); cars = layer()
    x = DSX + swerve(t) * 0.6; rot = 3 * math.cos((t - 3.3) * 5.5)
    headlights(cars, x - 250, kit.ROAD_Y - 70, 380, flip=True)
    fx.contact_shadow(cars, x, kit.ROAD_Y, 460, s=S, alpha=150)
    blit(cars, up(ds(int(t * 900) % 360, 0.5), 5), x, kit.ROAD_Y, 1.06, 0.95, rot, flip=True)
    for i, bx0 in enumerate((DSX - 400, DSX + 400)):                               # escort bikes ahead and behind
        bx = bx0 + 1100 * ic(gone) + 16 * math.sin(t * 4 + i)
        fx.contact_shadow(cars, bx, kit.ROAD_Y, 200, s=S, alpha=120)
        blit(cars, up(bike(gone > 0.05), 6), bx, kit.ROAD_Y, 1, 1, 0 if gone < 0.05 else 14 * gone, flip=True)
    fx.speed_lines(cars, 0.6, int(t * 12) % 5, col=(200, 204, 214))
    kit.ROAD.reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars); fg = layer()
    for i in range(7):                                                              # rounds pinging off the bodywork
        t0 = 3.35 + 0.22 * i
        fx.burst(fg, t, t0, x - 200 + 70 * ((i * 37) % 7), kit.ROAD_Y - 120 - 30 * (i % 3), (255, 236, 160), n=7, r0=8, r1=90, seed=80 + i)
    if t >= 3.87:
        k2 = popin(t, 3.87, 0.25) * (1 - 0.4 * gone)
        blit(fg, fx.big('badge', '2', '#ffffff', '#1a1a2e', '#d6d9e2', s=12), 540, 700, k2, k2, anchor='center')
    P2.draw(fg, t)
    img.alpha_composite(fg)
    return CAM2.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 3: the tyre gives way
WC = (540, 900)
CAM3 = Camera(W, H, [(5.8, (540, 900, 1.15)), (6.37, (540, 920, 1.35), 'io'), (7.1, (540, 930, 1.4))],
              kicks=[(6.37, 0.16, *WC)], shakes=[(6.37, 0.3, 10)])


def shot_tyre(t):
    img = desat(GAR.frame(t), 0.4).convert('RGBA'); fg = layer()
    df = oc(prog(t, 6.37, 0.45))
    fx.contact_shadow(fg, WC[0], WC[1] + 380, 700, s=S, alpha=160)
    blit(fg, up(wheel_close(round(df * 6) / 6, int(t * 240 * (1 - df)) % 360), 18), WC[0], WC[1] + 360 + 0 * df)
    for k in range(6):                                                              # escaping air
        fx.puff(fg, t, 6.4 + k * 0.1, WC[0] + 300, WC[1] + 300, seed=90 + k, life=0.6, size=0.7, drift=(260, -60), col=(220, 224, 232))
    fx.stamp_at(fg, t, 6.37, 'PUNCTURED', WC[0], WC[1] - 330, rot=-8, s=11)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: it stays level (garage + cutaway)
CX4 = 540
P4 = Presenter([
    (7.0, dict(path=Track([(7.0, (-200, 500)), (7.4, (160, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='think', face=1, ground=None)),
    (7.4, dict(ground=GROUND, squash=True, arms='point', point=(CX4, 900), look=(CX4, 900), expr='think', face=None)),
    (8.55, dict(arms='thumb', expr='smile', squash=True, point=None)),
    (9.31, dict(arms='present', look=(CX4, 1000), expr='smile')),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(7.05, (540, 900, 1.25)), (8.55, (540, 880, 1.15), 'io'), (9.31, (560, 940, 1.35), 'io'), (10.4, (560, 940, 1.4))],
              kicks=[(8.2, 0.06, CX4, 900), (8.55, 0.14, CX4, 600), (9.31, 0.1, CX4, 1000), (9.97, 0.08, CX4, 1000)])


def lift4(t): return io(prog(t, 7.6, 0.95))                                        # 0 sagging -> 1 level


def shot_level(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    lv = lift4(t)
    fx.rays(fg, t, 8.55, CX4, 900, GRN, life=1.2, r=560)
    fx.contact_shadow(fg, CX4, GROUND, 700, s=S, alpha=150)
    sag = 1 - lv
    rise = -30 * ob(prog(t, 7.6, 0.6)) * (1 - prog(t, 8.3, 0.3))
    blit(fg, up(ds(0, round(sag * 4) / 4, False), 7), CX4, GROUND + rise, 1.06, 0.95, -4 * sag, flip=True)
    xr = prog(t, 9.31, 0.3)                                                         # X-ray: the body turns to blueprint
    if xr > 0:
        gh = up(ds(0, 0, False, True), 7).copy(); gh.putalpha(gh.getchannel('A').point(lambda a: int(a * 0.85 * xr)))
        blit(fg, gh, CX4, GROUND, 1.06, 0.95, 0, flip=True)
        d = ImageDraw.Draw(fg)
        pulse = 1 + 0.12 * math.sin(t * 10)
        sph = [(CX4 - 220, GROUND - 120), (CX4 + 250, GROUND - 120)]
        d.line([sph[0], sph[1]], fill=(255, 210, 63, int(220 * xr)), width=8)
        for i, (sx, sy) in enumerate(sph):
            k = popin(t, 9.4 + 0.12 * i, 0.3) * pulse
            r = 46 * k
            d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(90, 230, 150, 255), outline=INK + (255,), width=6)
            d.chord((sx - r, sy - r, sx + r, sy + r), 0, 180, fill=(255, 210, 63, 255), outline=INK + (255,), width=6)
        dg.label(fg, t, 9.5, 'GAS + FLUID SPHERES', sph[1], (CX4 + 20, GROUND - 560), '#7fe3a0', '#1a1a2e', '#3cc85a', s=6)
    kt = popin(t, 7.2, 0.3) * popout(t, 9.25)
    blit(fg, up(level_tool(-0.9 * (1 - lv) + 0.05 * math.sin(t * 6) * (1 - lv)), 8), CX4, 560 + 6 * math.sin(t * 2), kt, kt,
         -6 * (1 - lv), anchor='center')
    if 8.55 <= t < 9.45:
        kc = ob(prog(t, 8.55, 0.2)) * popout(t, 9.25)
        blit(fg, fx.big('check', s=10), CX4 + 330, 560, kc, kc, anchor='center')
        fx.ring(fg, t, 8.55, CX4, 560, GRN, life=0.4, r1=420)
        fx.gsparkles(fg, t, CX4, 560, 600, 160, n=8)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the airport, unharmed
def car5_x(t): return lerp(-500, 470, oc(prog(t, 10.4, 1.7)))
RW_Y = 1500
CAM5 = Camera(W, H, [(10.35, (540, 1180, 1.25)), (12.2, (520, 1200, 1.32), 'io'), (13.35, (520, 1200, 1.36))],
              kicks=[(12.23, 0.06, 470, 1300), (12.64, 0.1, 540, 700)])
P5 = Presenter([
    (10.35, dict(path=Track([(10.35, (1300, 1000)), (11.0, (900, RW_Y), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1,
                 ground=None)),
    (11.0, dict(ground=RW_Y, squash=True, arms='present', look=(470, 1300), expr='smile', face=None)),
    (12.64, dict(arms='thumb', expr='happy', look=None, look_camera=True)),
], words=WORDS, base_size=6)


def shot_airport(t):
    img = runway_world().copy(); fg = layer()
    blit(fg, up(airliner(), 6), 640, 1260)                                          # waiting aircraft at the stand
    x = car5_x(t)
    fx.contact_shadow(fg, x, RW_Y, 560, s=S, alpha=120)
    blit(fg, up(ds(int(x * 0.6) % 360, 0.0), 6), x, RW_Y, 1.06, 0.95)
    if t >= 12.23:
        ka = popin(t, 12.23, 0.3)
        blit(fg, fx.big('tag', 'THE AIRPORT', '#fff6e0', '#1a1a2e', s=8), 560, 1120, ka, ka, -3 + 2 * math.sin(t * 3), anchor='center')
    if t >= 12.64:
        ku = ob(prog(t, 12.64, 0.25)) * (1 + 0.03 * math.sin(t * 6))
        blit(fg, fx.big('badge', 'UNHARMED', '#7fe3a0', '#1a1a2e', '#3cc85a', s=10), 520, 990, ku, ku, -3, anchor='center')
        fx.gsparkles(fg, t, 520, 990, 640, 180, n=8, seed=33)
    fx.sparkles(fg, t, x, RW_Y - 120, 520, 180, n=6, seed=34)
    P5.draw(fg, t)
    img.alpha_composite(fg)
    return CAM5.apply(img.convert('RGB'), t, (20, 24, 40))


# ================================================================== shot 6: no other car
P6 = Presenter([
    (13.3, dict(path=Track([(13.3, (-200, 600)), (13.7, (180, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (13.7, dict(ground=GROUND, squash=True, arms='point', point=(560, 640), look=(560, 640), expr='smile', face=None)),
    (14.31, dict(arms='hips', expr='smirk', look=None, look_camera=True, point=None)),
], words=WORDS, base_size=7)
CAM6 = Camera(W, H, [(13.3, (540, 880, 1.2)), (14.31, (540, 860, 1.12), 'io'), (16.2, (540, 860, 1.18))],
              kicks=[(13.42, 0.08, 560, 640), (14.31, 0.1, 560, 640), (15.45, 0.08, 540, 1000)])


def shot_only(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 13.42, 560, 640, GLOW, hold=True, r=600, n=12)
    for i, (x, col) in enumerate(((300, 'red'), (780, 'blue'))):                       # the other cars grey out
        g = prog(t, 15.2 + 0.15 * i, 0.3)
        fx.contact_shadow(fg, x, GROUND, 360, s=S, alpha=110)
        draw_car(fg, 'silver' if g > 0.5 else col, x, 4, flip=i == 1, sx=1.0, sy=0.9)
        if g > 0:
            kx = ob(g)
            blit(fg, fx.big('xmark', s=9), x, GROUND - 120, kx, kx, anchor='center')
    photo(fg, t, 13.42, 16.1, 'ds_presidential', 560, 620, 640, 470, -3, 'THE PRESIDENTIAL CAR', focus=(0.55, 0.55), zoom=0.12)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.3, shot_attack), (5.8, shot_tyre), (7.05, shot_level), (10.35, shot_airport), (13.3, shot_only),
         (END_T, shot_teaser)]
TRANS = {1: (3.3, 3.5, 'whip', dict(dx=-1)), 2: (5.8, 6.0, 'push', None), 3: (7.05, 7.27, 'iris', (WC[0], WC[1])),
         4: (10.35, 10.55, 'whip', dict(dx=1)), 5: (13.3, 13.5, 'push', None), 6: (END_T, END_T + 0.2, 'whip', dict(dx=0, dy=1))}
KEYCOL = {'1962': YEL, 'fire': RED, 'two': RED, 'bodyguards': RED, 'punctured': RED, 'stayed': GRN, 'level': GRN,
          'hydropneumatic': YEL, 'airport': YEL, 'unharmed': GRN, 'refused': RED}
CUES = [
    (0.0, 'screech', 0.9), (0.05, 'stamp', 0.6), (0.45, 'stamp', 0.9), (0.5, 'click', 0.5), (1.13, 'click', 0.5), (1.65, 'click', 0.5),
    (1.94, 'click', 0.5), (2.4, 'thump', 0.9), (2.42, 'boom', 0.3),
    (3.35, 'screech', 0.5), (3.87, 'thump', 0.6), (5.2, 'fall', 0.4),
    (6.37, 'stamp', 0.8), (6.4, 'poof', 0.8),
    (7.6, 'slide_down', 0.4), (8.55, 'ding', 0.8), (8.57, 'sparkle', 0.6), (9.4, 'pop', 0.6), (9.52, 'pop', 0.6), (9.6, 'click', 0.4),
    (10.45, 'vroom', 0.4), (12.23, 'pop', 0.5), (12.64, 'ding', 0.8), (12.66, 'sparkle', 0.6),
    (13.42, 'pop', 0.7), (14.31, 'click', 0.4), (15.2, 'buzzer', 0.4), (15.35, 'buzzer', 0.4),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
