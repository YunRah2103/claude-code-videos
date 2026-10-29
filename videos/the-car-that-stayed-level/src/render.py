"""Renders 'The Car That Stayed Level': de Gaulle's DS kept level on punctured tyres in 1962.

Template: videos/ac-idle -> tractors-vs-ferraris shot structure; kit in shared/episode.py (corner rev counter on).
Word times come from align.py -> words.json. Speech runs 0-17.2 s; the card holds to 17.5 s. Serious tone: no gags,
no weapons on screen, the bodyguards' deaths shown by their bikes falling back in grey. No tyre count on screen.
The car is a generic pixel DS silhouette with no badges, built as a rig (body on its own above the wheels) so the
self-levelling suspension can be shown working; the framed photo is the presidential DS (credits.json).
Shots:
  1 hook     0.00  night road: the DS skids on two wheels throwing rim sparks, lands, and its body rises level
  2 attack   3.30  whip; tracking shot: it rolls and swerves through sparks; the escort bikes fall back in grey on 'killed'
  3 tyre     5.80  push; rear close-up: the tyre goes flat on 'punctured' but the body holds its line
  4 level    7.05  iris; garage: the tail sags, the struts glow and pump it up level on 'level'; sphere cutaway, fluid flows
  5 airport 10.35  whip; calm dusk runway: the DS rolls in, dips and settles by the aircraft; UNHARMED
  6 only DS 13.30  push; presidential DS photo; other cars roll up and are turned away; ONLY THE DS
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
REAR, FRONT, WR = 22, 80, 7                                          # wheel centres (grid x) and radius on the DS rig


# ------------------------------------------------------------------ the DS rig: body and wheels drawn separately
@lru_cache(None)
def ds_body(xray=False, lights=True):
    """DS body facing right (100x26 grid, no wheels): high tapering tail with roof-mounted indicators, domed cabin set
    well back, long falling bonnet to a low nose with twin lamps, covered rear wheel, front arch cut-out. Wheel
    centres sit at grid y 24 under the sill."""
    body, hi, deep = ((40, 44, 58), (120, 130, 156), (20, 22, 30)) if not xray else ((90, 150, 230), (170, 210, 255), (50, 100, 180))
    img = Image.new('RGBA', (100, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    shell = [(2, 13), (8, 10), (22, 8), (28, 3), (40, 1), (56, 1), (66, 4), (72, 9), (86, 12), (97, 16), (99, 19), (96, 22),
             (89, 22), (88, 18), (84, 16), (76, 16), (72, 18), (71, 22), (4, 22), (2, 19)]
    d.polygon(shell, fill=body)
    d.line([(8, 10), (22, 8)], fill=hi); d.line([(72, 9), (86, 12), (96, 16)], fill=hi); d.line([(40, 1), (56, 1)], fill=hi)
    glass = (120, 150, 190) if not xray else (200, 230, 255)
    d.polygon([(29, 4), (40, 2), (47, 2), (47, 8), (25, 8)], fill=glass); d.polygon([(50, 2), (56, 2), (64, 5), (69, 9), (50, 9)], fill=glass)
    d.line([(48, 2), (48, 9)], fill=deep)
    d.rectangle((26, 1, 28, 3), fill=(220, 50, 50))                                     # roof 'trumpet' indicator
    d.line([(6, 19), (70, 19)], fill=(214, 220, 230)); d.line([(90, 19), (96, 19)], fill=(214, 220, 230))   # chrome sill
    d.line([(10, 16), (34, 16)], fill=deep)                                             # rear spat seam
    if lights:
        d.ellipse((93, 14, 97, 18), fill=(255, 246, 190)); d.ellipse((90, 15, 93, 18), fill=(255, 236, 170))
    d.rectangle((2, 13, 4, 15), fill=(220, 40, 40))
    return outline(img)


@lru_cache(None)
def ds_wheel(spin=0, flat=0.0):
    """Wheel (16x16): flat 0..1 squashes the tyre at the bottom."""
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    f = round(3 * flat)
    d.ellipse((0, 0 + f, 15, 15), fill=(22, 22, 28))
    if f: d.rectangle((-1, 13, 16, 15), fill=(22, 22, 28))
    c = (7.5, 7.5 + f / 2)
    d.ellipse((c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4), fill=(176, 182, 192))
    for k in range(4):
        a = math.radians(spin + k * 90); d.line([c, (c[0] + 3 * math.cos(a), c[1] + 3 * math.sin(a))], fill=(96, 100, 110))
    return outline(img)


def draw_ds(cv, x, gy, s, lift=0.0, tilt=0.0, flip=False, spin=0, flat=0.0, xray=False, struts=0.0, lights=True, fluid_t=None, over=False):
    """Compose the DS at centre x on ground gy, scale s. lift raises the body (px), tilt pitches it (deg, + = tail down),
    flat deflates the rear tyre, struts 0..1 shows the glowing hydraulic struts between wheels and body (over=True draws
    them over the body, X-ray style, so the pumping reads)."""
    sg = -1 if flip else 1
    wx = {k: x + sg * (gx - 50) * s for k, gx in (('r', REAR), ('f', FRONT))}
    wc_y = gy - WR * s - s / 2
    for k in ('r', 'f'):
        fl = flat if k == 'r' else 0.0
        blit(cv, up(ds_wheel(int(spin) % 360, round(fl * 3) / 3), s), wx[k], gy)
    by = wc_y - (24 - 13) * s - lift                                      # body centre (grid y 13) above the wheel line
    def strut_pass():                                                     # hydraulic struts: wheel hub up into the body
        d = ImageDraw.Draw(cv)
        for i, k in enumerate(('r', 'f')):
            hub = (wx[k], wc_y + (flat * 1.5 * s if k == 'r' else 0))
            top = (wx[k], by + 2 * s + sg * tilt * (wx[k] - x) * 0.017)
            a = int(255 * struts)
            d.line([hub, top], fill=(26, 26, 46, a), width=int(3.4 * s)); d.line([hub, top], fill=(255, 210, 63, a), width=int(1.8 * s))
            r = 2.6 * s * (1 + 0.15 * math.sin((fluid_t or 0) * 12 + i))
            d.ellipse((top[0] - r, top[1] - r, top[0] + r, top[1] + r), fill=(90, 230, 150, a), outline=(26, 26, 46, a), width=int(s))
            d.chord((top[0] - r, top[1] - r, top[0] + r, top[1] + r), 0, 180, fill=(255, 210, 63, a), outline=(26, 26, 46, a), width=int(s))
    if struts > 0.01 and not over: strut_pass()
    img = up(ds_body(xray, lights), s)
    if xray:
        img = img.copy(); img.putalpha(img.getchannel('A').point(lambda v: int(v * 0.8)))
    blit(cv, img, x, by, 1, 1, sg * -tilt, anchor='center', flip=flip)
    if struts > 0.01 and over: strut_pass()
    return wx, wc_y, by


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
def airliner(beacon=False):
    """1960s four-engine airliner, side view (110x34), red beacon on the fin."""
    img = Image.new('RGBA', (110, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(4, 18), (12, 14), (96, 13), (106, 16), (108, 19), (100, 22), (10, 22)], fill=(222, 226, 236))
    d.polygon([(6, 16), (2, 3), (10, 3), (18, 14)], fill=(200, 206, 220))
    d.polygon([(40, 19), (70, 19), (52, 30), (44, 30)], fill=(180, 186, 200))
    for x in range(22, 92, 5): d.rectangle((x, 15, x + 1, 16), fill=(70, 110, 170))
    d.line([(10, 18), (104, 18)], fill=(60, 110, 200))
    for x in (46, 58): d.rectangle((x, 24, x + 5, 27), fill=(150, 156, 170))
    d.line([(30, 22), (30, 31)], fill=(90, 90, 100)); d.line([(84, 22), (84, 31)], fill=(90, 90, 100))
    d.ellipse((28, 29, 32, 33), fill=(26, 26, 32)); d.ellipse((82, 29, 86, 33), fill=(26, 26, 32))
    d.rectangle((3, 1, 5, 3), fill=(255, 60, 60) if beacon else (120, 40, 40))
    return outline(img)


@lru_cache(None)
def runway_world():
    """Calm dusk airfield (180x320 grid, x6): gradient sky, terminal and tower silhouettes, runway in perspective."""
    g = Image.new('RGB', (180, 320)); d = ImageDraw.Draw(g)
    for y in range(190):
        u = y / 190
        d.line([(0, y), (179, y)], fill=(int(30 + 200 * u ** 2), int(32 + 110 * u ** 2), int(70 + 60 * u)))
    d.ellipse((128, 142, 156, 170), fill=(255, 196, 120))                         # low sun
    d.rectangle((0, 176, 179, 319), fill=(40, 46, 56))
    d.rectangle((10, 160, 86, 186), fill=(30, 34, 46))                            # terminal
    for x in range(14, 84, 6): d.rectangle((x, 166, x + 3, 169), fill=(255, 220, 140))
    d.rectangle((100, 140, 106, 186), fill=(30, 34, 46)); d.rectangle((96, 134, 110, 142), fill=(60, 80, 110))   # tower
    d.polygon([(70, 186), (110, 186), (179, 319), (0, 319)], fill=(64, 68, 78))
    for i in range(10):
        u = i / 10; y0 = 190 + 130 * u ** 1.6; y1 = y0 + 3 + 6 * u
        d.rectangle((89 - u, y0, 91 + u, y1), fill=(230, 230, 236))
    return up(g, 6).convert('RGBA')


def desat(img, k):
    return Image.blend(img, ImageEnhance.Color(img).enhance(0.25), k)


def bounce(t, t0, amp, w=16.0, damp=5.0):
    """Damped suspension bounce starting at t0."""
    if t < t0: return 0.0
    u = t - t0
    return amp * math.exp(-damp * u) * math.cos(w * u)


# ================================================================== shot 1: hook, on two wheels, lands level
DSX = 540
RCX = DSX - (REAR - 50) * 6                                                    # rear contact patch (car faces left)
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (1300, 400)), (0.5, (1300, 400)), (0.9, (900, kit.ROAD_Y), 'ic')]), size=6, legs='auto', arms='fly',
                expr='shock', ground=None, face=-1)),
    (0.9, dict(ground=kit.ROAD_Y, squash=True, arms='shock', look=(DSX, 1100), expr='shock', face=None)),
    (2.45, dict(arms='hips', expr='think', look=None, look_camera=True)),
], words=WORDS, base_size=6)
CAM1 = Camera(W, H, [(-1.0, (540, 1060, 1.5)), (0.0, (540, 1060, 1.5)), (0.9, (540, 1040, 1.22), 'io'), (2.45, (520, 1040, 1.3), 'io'),
                     (3.3, (520, 1040, 1.34))],
              kicks=[(0.0, 0.12, DSX, 1100), (0.5, 0.12, DSX, 1100), (1.13, 0.1, DSX, 1100), (2.45, 0.16, DSX, 1150)],
              shakes=[(0.0, 2.45, 7), (2.45, 0.3, 14)])


def tilt1(t): return -16 * (1 - io(prog(t, 2.2, 0.25))) + 2.5 * math.sin(t * 9) * (t < 2.2)


def shot_hook(t):
    img = desat(kit.street(t, 520 * t * (1 - 0.6 * prog(t, 2.45, 0.8))), 0.35); cars = layer()
    tl = tilt1(t)
    headlights(cars, DSX - 340, kit.ROAD_Y - 90, 420, flip=True)
    fx.contact_shadow(cars, DSX, kit.ROAD_Y, 620, s=S, alpha=150)
    lift = 26 * oc(prog(t, 2.5, 0.35)) * (1 - prog(t, 3.0, 0.3)) + bounce(t, 2.45, 22)   # it lands, then rises level
    rig = layer()
    draw_ds(rig, DSX, kit.ROAD_Y, 6, lift=lift, flip=True, spin=t * 900, flat=1.0, struts=0.9 * prog(t, 2.45, 0.2) * (1 - prog(t, 3.1, 0.2)),
            fluid_t=t, over=True)
    if abs(tl) > 0.3:                                                           # skidding on the flat rear tyre: the nose lifts
        rig = rig.rotate(tl, Image.BICUBIC, center=(RCX, kit.ROAD_Y))
    cars.alpha_composite(rig)
    if t < 2.45:                                                                # rim sparks off the road
        for k in range(3):
            fx.burst(cars, t, t - 0.02 - 0.05 * k, RCX, kit.ROAD_Y - 10, (255, 210, 90), n=7, r0=10, r1=130, seed=int(t * 30) + k)
    fx.dust(cars, t, 2.45, DSX, kit.ROAD_Y - 10, n=16, seed=8)
    fx.speed_lines(cars, 0.6 * (1 - prog(t, 2.45, 0.6)), int(t * 12) % 5, col=(200, 204, 214))
    kit.ROAD.reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars); fg = layer()
    for i, t0 in enumerate((0.5, 1.13, 1.65, 1.94)):                                # muzzle-flash sparks from off-screen
        x, y = (260, 820, 380, 700)[i], (820, 860, 900, 780)[i]
        fx.burst(fg, t, t0, x, y, (255, 236, 160), n=9, r0=10, r1=130, seed=70 + i)
        fx.ring(fg, t, t0, x, y, (255, 255, 255), life=0.15, r1=90)
    if t >= 2.6:
        fx.ring(fg, t, 2.6, DSX, kit.ROAD_Y - 170, GRN, life=0.35, r1=380)
        dg.label(fg, t, 2.6, 'STILL LEVEL', (DSX, kit.ROAD_Y - 180), (DSX + 40, kit.ROAD_Y - 440), '#7fe3a0', '#1a1a2e', '#3cc85a', s=6)
    P1.draw(fg, t)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    title(cv, t, 0.05, 2.4, 'TYRES', kit.WHITE, 430, 120, -2)
    if 0.45 <= t < 2.6:
        img = kit.text_img('PUNCTURED.', RED, 150)
        k = ob(prog(t, 0.45, 0.18)) * (1 + 0.03 * math.sin(t * 9)) * min(1.0, 980 / img.width) * popout(t, 2.4)
        blit(cv, img, W / 2, 590, k, k, -4 + 1.5 * math.sin(t * 3), anchor='center')
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 430, (255, 255, 255), life=0.35, r1=520)


# ================================================================== shot 2: under fire, the escort falls back (tracking)
def swerve(t): return 80 * math.sin((t - 3.3) * 5.5)
P2 = Presenter([
    (3.3, dict(path=Track([(3.3, (540, 2100)), (3.6, (540, kit.ROAD_Y + 270), 'oc')]), size=4, legs='auto', arms='fly', expr='shock', face=1,
               ground=None)),
    (3.6, dict(ground=kit.ROAD_Y + 270, squash=True, arms='brace', look=(540, 1150), expr='shock', face=None)),
    (5.2, dict(arms='down2', expr='sad', look=(900, 1200))),
], words=WORDS, base_size=4)
CAM2 = Camera(W, H, [(3.3, (540, 1060, 1.1)), (4.4, (520, 1070, 1.16), 'io'), (5.2, (560, 1060, 1.12), 'io'), (5.85, (560, 1060, 1.1))],
              kicks=[(3.87, 0.1, 540, 900), (4.59, 0.08, 540, 1100), (5.2, 0.06, 900, 1100)], shakes=[(3.3, 1.9, 9), (5.2, 0.2, 4)])


def shot_attack(t):
    gone = prog(t, 5.2, 0.5)
    slow = 1 - 0.55 * gone                                                      # the world slows as the escort is lost
    img = desat(kit.street(t, 640 * (t - 3.3) * slow + 2000), 0.4 + 0.35 * gone); cars = layer()
    x = DSX + swerve(t) * 0.6
    roll = 3.2 * math.cos((t - 3.3) * 5.5)                                      # body pitch on the swerve
    headlights(cars, x - 260, kit.ROAD_Y - 70, 380, flip=True)
    fx.contact_shadow(cars, x, kit.ROAD_Y, 500, s=S, alpha=150)
    draw_ds(cars, x, kit.ROAD_Y, 5, lift=6 * math.sin((t - 3.3) * 11), tilt=roll, flip=True, spin=t * 900, flat=0.4)
    for i, bx0 in enumerate((DSX - 410, DSX + 410)):                               # escort bikes ahead and behind
        bx = bx0 + 1100 * ic(gone) + 16 * math.sin(t * 4 + i)
        fx.contact_shadow(cars, bx, kit.ROAD_Y, 200, s=S, alpha=120)
        blit(cars, up(bike(gone > 0.05), 6), bx, kit.ROAD_Y + 3 * math.sin(t * 20 + i), 1, 1, 0 if gone < 0.05 else 14 * gone, flip=True)
    fx.speed_lines(cars, 0.6 * slow, int(t * 12) % 5, col=(200, 204, 214))
    kit.ROAD.reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars); fg = layer()
    for i in range(8):                                                          # rounds pinging off the bodywork
        t0 = 3.35 + 0.2 * i
        px, py = x - 220 + 64 * ((i * 37) % 7), kit.ROAD_Y - 110 - 26 * (i % 3)
        fx.burst(fg, t, t0, px, py, (255, 236, 160), n=8, r0=8, r1=100, seed=80 + i)
        fx.ring(fg, t, t0, px, py, (255, 255, 255), life=0.12, r1=60)
    if t >= 3.87:
        k2 = ob(prog(t, 3.87, 0.25)) * (1 - 0.4 * gone)
        blit(fg, fx.big('badge', '2', '#ffffff', '#1a1a2e', '#d6d9e2', s=12), 540, 700, k2, k2, anchor='center')
    if t >= 4.59:
        kb = popin(t, 4.59, 0.25) * (1 - 0.4 * gone)
        blit(fg, fx.big('tag', 'ESCORT', '#fff6e0', '#1a1a2e', s=7), 540, 860, kb, kb, -3, anchor='center')
    P2.draw(fg, t)
    img.alpha_composite(fg)
    return CAM2.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 3: the tyre goes flat, the body holds its line
RX = 620                                                                        # rear wheel on screen in the close-up
CAM3 = Camera(W, H, [(5.8, (560, 960, 1.05)), (6.37, (560, 960, 1.15), 'io'), (7.1, (560, 960, 1.2))],
              kicks=[(6.37, 0.16, RX, 1100)], shakes=[(6.37, 0.3, 10)])


def shot_tyre(t):
    img = desat(GAR.frame(t), 0.4).convert('RGBA'); fg = layer()
    df = oc(prog(t, 6.37, 0.45))
    s = 14
    cx = RX - (REAR - 50) * s                                                   # place the rig so its rear wheel sits at RX
    fx.contact_shadow(fg, RX, GROUND + 150, 520, s=S, alpha=160)
    wx, wcy, by = draw_ds(fg, cx, GROUND + 150, s, lift=0.0, spin=t * 400 * (1 - df), flat=df, struts=df, fluid_t=t, over=True)
    d = ImageDraw.Draw(fg)
    if df > 0.05:                                                               # the line it keeps
        ly = by + 9 * s
        for xx in range(0, W, 60): d.line([(xx, ly), (xx + 34, ly)], fill=(90, 230, 150, int(230 * df)), width=8)
        dg.label(fg, t, 6.6, 'BODY STAYS PUT', (RX - 200, ly), (300, ly - 330), '#7fe3a0', '#1a1a2e', '#3cc85a', s=6)
    for k in range(6):                                                          # escaping air
        fx.puff(fg, t, 6.4 + k * 0.1, RX + 120, GROUND + 60, seed=90 + k, life=0.6, size=0.7, drift=(260, -60), col=(220, 224, 232))
    fx.stamp_at(fg, t, 6.37, 'PUNCTURED', 600, 470, rot=-8, s=11)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: it stays level (garage + cutaway)
CX4 = 560
P4 = Presenter([
    (7.0, dict(path=Track([(7.0, (-200, 500)), (7.4, (130, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='think', face=1, ground=None)),
    (7.4, dict(ground=GROUND, squash=True, arms='point', point=(CX4 - 300, 1000), look=(CX4, 900), expr='think', face=None)),
    (8.55, dict(arms='thumb', expr='smile', squash=True, point=None)),
    (9.31, dict(arms='present', look=(CX4, 1000), expr='smile')),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(7.05, (560, 940, 1.2)), (7.6, (420, 980, 1.34), 'io'), (8.55, (560, 900, 1.12), 'io'), (9.31, (560, 960, 1.22), 'io'),
                     (10.4, (560, 960, 1.28))],
              kicks=[(8.2, 0.06, CX4, 900), (8.55, 0.14, CX4, 600), (9.31, 0.1, CX4, 1000), (9.97, 0.08, CX4, 1000)], shakes=[(8.55, 0.2, 6)])


def lift4(t): return io(prog(t, 7.7, 0.85))                                        # 0 sagging -> 1 level


def shot_level(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    lv = lift4(t)
    s = 8
    fx.rays(fg, t, 8.55, CX4, 820, GRN, life=1.2, r=600)
    fx.contact_shadow(fg, CX4, GROUND, 820, s=S, alpha=150)
    sag = 1 - lv
    tilt = 7 * sag + bounce(t, 8.55, 2.2, w=18)                                 # tail down, then levels with a settle
    xr = prog(t, 9.31, 0.3)
    pump = (7.6 <= t < 8.7)
    wx, wcy, by = draw_ds(fg, CX4, GROUND, s, lift=-16 * sag + 10 * bounce(t, 8.55, 1.0, w=18), tilt=tilt, flat=1.0, xray=xr > 0.5,
                          struts=max(0.95 * prog(t, 7.6, 0.2) * (1 - prog(t, 8.9, 0.3)), 0.9 * xr), fluid_t=t * (3 if pump else 1),
                          lights=False, over=True)
    d = ImageDraw.Draw(fg)
    if pump:                                                                    # pump strokes: chevrons climb the struts
        for k in ('r', 'f'):
            for j in range(3):
                u = (t * 3 + j / 3) % 1
                yy = lerp(wcy, by + 40, u)
                d.polygon([(wx[k] - 26, yy + 14), (wx[k], yy - 8), (wx[k] + 26, yy + 14)], fill=(255, 236, 160, int(255 * (1 - u))))
    if xr > 0:                                                                  # fluid runs from the pump to both spheres
        pump_xy = (wx['f'] - 120, by + 20)
        for k in ('r', 'f'):
            tx, ty = wx[k], by + 6 * s
            d.line([pump_xy, (tx, ty)], fill=(255, 210, 63, int(230 * xr)), width=10)
            for j in range(6):
                u = (t * 1.6 + j / 6) % 1
                px, py = lerp(pump_xy[0], tx, u), lerp(pump_xy[1], ty, u)
                d.ellipse((px - 9, py - 9, px + 9, py + 9), fill=(255, 250, 200, int(255 * xr)))
        d.rounded_rectangle((pump_xy[0] - 40, pump_xy[1] - 30, pump_xy[0] + 40, pump_xy[1] + 30), 10, fill=(150, 156, 170, int(255 * xr)),
                            outline=INK + (255,), width=6)
        dg.label(fg, t, 9.5, 'GAS + FLUID SPHERES', (wx['r'], by + 6 * s), (CX4 - 20, GROUND - 560), '#7fe3a0', '#1a1a2e', '#3cc85a', s=6)
    kt = popin(t, 7.2, 0.3) * popout(t, 9.25)
    blit(fg, up(level_tool(-0.9 * sag + 0.08 * math.sin(t * 6) * sag), 8), CX4, 520 + 6 * math.sin(t * 2), kt, kt, -tilt, anchor='center')
    if 8.55 <= t < 9.45:
        kc = ob(prog(t, 8.55, 0.2)) * popout(t, 9.25)
        blit(fg, fx.big('check', s=10), CX4 + 330, 520, kc, kc, anchor='center')
        fx.ring(fg, t, 8.55, CX4, 520, GRN, life=0.4, r1=420)
        fx.gsparkles(fg, t, CX4, 520, 600, 160, n=8)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the airport, unharmed
RW_Y = 1280
CAR5 = Track([(10.35, (-560, 0)), (11.9, (420, 0), 'oc')])
CAM5 = Camera(W, H, [(10.35, (520, 1040, 1.18)), (11.9, (500, 1060, 1.26), 'io'), (13.35, (520, 1050, 1.3))],
              kicks=[(12.23, 0.06, 420, 1150), (12.64, 0.1, 540, 900)], follow=[(10.35, 11.9, lambda t: (CAR5.at(t)[0] + 200, 1060), 0.4)])
P5 = Presenter([
    (10.35, dict(path=Track([(10.35, (1300, 900)), (11.0, (930, RW_Y), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1,
                 ground=None)),
    (11.0, dict(ground=RW_Y, squash=True, arms='wave', look=(420, 1200), expr='smile', face=None)),
    (12.64, dict(arms='thumb', expr='happy', look=None, look_camera=True)),
], words=WORDS, base_size=6)


def shot_airport(t):
    img = runway_world().copy(); fg = layer(); d = ImageDraw.Draw(fg)
    for i in range(9):                                                          # runway edge lights chase toward the stand
        u = i / 9; y = 1188 + 780 * u ** 1.4
        on = (int(t * 10) - i) % 9 < 2
        for x in (420 - 420 * u, 660 + 420 * u):
            r = 7 + 6 * u
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 230, 120, 255) if on else (150, 120, 60, 200))
    blit(fg, up(airliner(int(t * 2.5) % 2 == 0), 6), 690, RW_Y - 40)              # waiting aircraft, beacon blinking
    x = CAR5.at(t)[0]
    stopped = t >= 11.9
    fx.contact_shadow(fg, x, RW_Y, 520, s=S, alpha=120)
    headlights(fg, x + 330, RW_Y - 80, 360)
    draw_ds(fg, x, RW_Y, 5, lift=bounce(t, 11.9, 10, w=14), tilt=-2.5 * math.exp(-(t - 11.9) * 4) * stopped, spin=x * 0.9)
    if t >= 12.23:
        ka = popin(t, 12.23, 0.3)
        blit(fg, fx.big('tag', 'THE AIRPORT', '#fff6e0', '#1a1a2e', s=8), 560, 920, ka, ka, -3 + 2 * math.sin(t * 3), anchor='center')
    if t >= 12.64:
        ku = ob(prog(t, 12.64, 0.25)) * (1 + 0.03 * math.sin(t * 6))
        blit(fg, fx.big('badge', 'UNHARMED', '#7fe3a0', '#1a1a2e', '#3cc85a', s=10), 520, 780, ku, ku, -3, anchor='center')
        fx.gsparkles(fg, t, 520, 780, 640, 180, n=8, seed=33)
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
CAM6 = Camera(W, H, [(13.3, (540, 880, 1.2)), (14.31, (540, 860, 1.12), 'io'), (16.2, (540, 840, 1.2), 'io')],
              kicks=[(13.42, 0.08, 560, 640), (14.31, 0.1, 560, 640), (15.45, 0.08, 540, 1000), (15.6, 0.12, 540, 400)])


def shot_only(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 13.42, 560, 640, GLOW, hold=True, r=600, n=12)
    for i, (x0, col) in enumerate(((300, 'red'), (800, 'blue'))):                   # other cars roll up, then are sent back
        arrive = oc(prog(t, 14.4 + 0.2 * i, 0.4)); back = ic(prog(t, 15.2 + 0.15 * i, 0.5))
        x = x0 + (-1 if i == 0 else 1) * (520 * (1 - arrive) + 600 * back)
        g = prog(t, 15.2 + 0.15 * i, 0.15)
        if arrive <= 0.01: continue
        fx.contact_shadow(fg, x, GROUND, 360, s=S, alpha=110)
        draw_car(fg, 'silver' if g > 0.5 else col, x, 4, flip=i == 1, sy=0.9, dist=x)
        if g > 0:
            kx = ob(g) * (1 - back)
            blit(fg, fx.big('xmark', s=9), x, GROUND - 120, kx, kx, anchor='center')
    photo(fg, t, 13.42, 16.1, 'ds_presidential', 560, 620, 640, 470, -3, 'THE PRESIDENTIAL CAR', focus=(0.55, 0.55), zoom=0.12)
    if t >= 15.6:
        ko = ob(prog(t, 15.6, 0.2)) * (1 + 0.04 * math.sin(t * 8))
        blit(fg, fx.big('badge', 'ONLY THE DS', '#ffd23f', '#1a1a2e', '#e8b923', s=8), 520, 430, ko, ko, -4, anchor='center')
        fx.burst(fg, t, 15.6, 520, 430, GLOW, n=14, seed=91)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.3, shot_attack), (5.8, shot_tyre), (7.05, shot_level), (10.35, shot_airport), (13.3, shot_only),
         (END_T, shot_teaser)]
TRANS = {1: (3.3, 3.5, 'whip', dict(dx=-1)), 2: (5.8, 6.0, 'push', None), 3: (7.05, 7.27, 'iris', (RX, 1000)),
         4: (10.35, 10.55, 'whip', dict(dx=1)), 5: (13.3, 13.5, 'push', None), 6: (END_T, END_T + 0.2, 'whip', dict(dx=0, dy=1))}
KEYCOL = {'1962': YEL, 'fire': RED, 'two': RED, 'bodyguards': RED, 'punctured': RED, 'stayed': GRN, 'level': GRN,
          'hydropneumatic': YEL, 'airport': YEL, 'unharmed': GRN, 'refused': RED}
CUES = [
    (0.0, 'screech', 0.9), (0.05, 'stamp', 0.6), (0.45, 'stamp', 0.9), (0.5, 'click', 0.5), (1.13, 'click', 0.5), (1.65, 'click', 0.5),
    (1.94, 'click', 0.5), (2.45, 'thump', 0.9), (2.47, 'boom', 0.3), (2.6, 'slide_down', 0.4),
    (3.35, 'screech', 0.5), (3.87, 'thump', 0.6), (4.59, 'pop', 0.4), (5.2, 'fall', 0.4),
    (6.37, 'stamp', 0.8), (6.4, 'poof', 0.8), (6.6, 'pop', 0.5),
    (7.7, 'slide_down', 0.5), (7.9, 'click', 0.4), (8.2, 'click', 0.4), (8.55, 'ding', 0.8), (8.57, 'sparkle', 0.6), (9.4, 'pop', 0.6),
    (9.6, 'click', 0.4),
    (10.45, 'vroom', 0.4), (11.9, 'thump', 0.4), (12.23, 'pop', 0.5), (12.64, 'ding', 0.8), (12.66, 'sparkle', 0.6),
    (13.42, 'pop', 0.7), (14.4, 'vroom', 0.3), (15.2, 'buzzer', 0.4), (15.35, 'buzzer', 0.4), (15.6, 'cha_ching', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='black', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
