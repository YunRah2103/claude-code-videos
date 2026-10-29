"""Renders 'The Mascot With a Secret': the Spirit of Ecstasy, its sculptor, and the model Rolls-Royce names.

Template: videos/ac-idle -> tractors-vs-ferraris shot structure; kit in shared/episode.py (corner rev counter on).
Word times come from align.py -> words.json. Speech runs 0-19.25 s; the card holds to 19.5 s. The claim that
Eleanor Thornton was the model stays hedged ('ROLLS-ROYCE SAYS'); no person is shown, and the ship scene is a wake
streak and a soft flash, then calm. Car and grille are generic (no badge, no lettering); the framed photo is the real
mascot (credits.json).
Shots:
  1 hook      0.00  rain at night: the mascot glows on a long bonnet; THE FACE / ON THE BONNET; photo on 'Spirit of Ecstasy'
  2 1911      3.30  whip; calendar pages flip to 1911; SINCE 1911
  3 sculptor  4.70  push; workshop: he studies the figure on its plinth, chisel sparks; CHARLES SYKES tag
  4 claim     6.90  iris; an empty portrait frame with '?'; ROLLS-ROYCE SAYS stamp; ELEANOR THORNTON name plate
  5 1915      9.70  whip; an office desk and typewriter; the calendar turns to 1915 and the colour drains
  6 ship     13.60  push; night sea: a wake streak reaches the ship on 'torpedoed', soft flash, calm; OFF CRETE, 1915
  7 story    15.45  whip; sunrise on the bonnet: the figure shines; A STORY
  8 teaser   18.10  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw, ImageEnhance
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, layer, finish, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 19.5, 18.1
SILVER, SHADE, SHINE = (214, 220, 230), (130, 136, 150), (250, 252, 255)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def figure():
    """Winged figure leaning into the wind (24x32): robes streaming back like wings, on a round base."""
    img = Image.new('RGBA', (24, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(9, 10), (2, 2), (0, 6), (4, 14), (10, 16)], fill=SILVER)          # robe-wing, back
    d.polygon([(10, 11), (6, 4), (4, 9), (8, 16)], fill=SHADE)
    d.polygon([(10, 9), (15, 7), (17, 10), (15, 22), (12, 28), (9, 28), (10, 18)], fill=SILVER)   # body leaning forward
    d.line([(15, 8), (16, 14)], fill=SHINE)
    d.ellipse((14, 3, 20, 9), fill=SILVER); d.point((19, 6), fill=SHADE)          # head, looking ahead
    d.line([(12, 18), (14, 26)], fill=SHADE)
    d.rectangle((7, 28, 16, 31), fill=SHADE); d.rectangle((8, 28, 15, 28), fill=SHINE)
    return outline(img)


@lru_cache(None)
def bonnet():
    """Long luxury bonnet seen from the side-front (110x40): upright chrome grille with slats, headlamp, wing."""
    img = Image.new('RGBA', (110, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(0, 14), (80, 10), (92, 12), (92, 36), (0, 36)], fill=(70, 78, 104))               # bonnet + wing
    d.line([(0, 14), (80, 10)], fill=(200, 210, 236)); d.line([(0, 15), (80, 11)], fill=(150, 160, 190)); d.line([(0, 22), (84, 20)], fill=(50, 56, 76))
    d.rectangle((88, 8, 108, 36), fill=SILVER); d.rectangle((90, 10, 106, 34), fill=(60, 64, 76))  # grille shell
    for x in range(91, 106, 3): d.line([(x, 10), (x, 34)], fill=(200, 206, 216))
    d.rectangle((88, 8, 108, 9), fill=SHINE)
    d.ellipse((70, 24, 82, 34), fill=SILVER); d.ellipse((72, 26, 80, 32), fill=(255, 246, 200))     # headlamp
    return outline(img)


@lru_cache(None)
def page(year, tint=1.0):
    """Tear-off calendar page (44x50) with a big year."""
    img = Image.new('RGBA', (44, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 43, 49), fill=(250, 246, 236)); d.rectangle((0, 0, 43, 9), fill=(214, 48, 58))
    for x in (8, 18, 26, 36): d.rectangle((x, 1, x + 1, 4), fill=(60, 60, 70))
    for r in range(3):
        for c in range(6): d.rectangle((4 + c * 6, 34 + r * 5, 7 + c * 6, 36 + r * 5), fill=(200, 204, 214))
    img = outline(img)
    big = up(img, 8)
    txt = kit.text_img(str(year), (26, 26, 46), 120)
    txt = txt.resize((int(txt.width * 0.9), int(txt.height * 0.9)), Image.LANCZOS)
    big.alpha_composite(txt, (int(big.width / 2 - txt.width / 2), 92))
    if tint < 1: big = Image.blend(big, ImageEnhance.Color(big).enhance(0.0), 1 - tint)
    return big


@lru_cache(None)
def portrait():
    """Empty gilt portrait frame (40x52) holding only a '?'."""
    img = Image.new('RGBA', (40, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 39, 51), fill=(214, 160, 40)); d.rectangle((2, 2, 37, 49), fill=(255, 210, 90))
    d.rectangle((5, 5, 34, 46), fill=(40, 44, 58))
    for k in range(6): d.point((3 + 6 * k, 1), fill=(255, 240, 170))
    return outline(img)


@lru_cache(None)
def typewriter(key=0):
    """Desk typewriter (40x26) with paper; key 0..3 picks which key is down."""
    img = Image.new('RGBA', (40, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((10, 0, 30, 10), fill=(250, 246, 236)); d.line([(13, 3), (26, 3)], fill=(150, 150, 160)); d.line([(13, 5), (22, 5)], fill=(150, 150, 160))
    d.rectangle((4, 9, 36, 13), fill=(60, 63, 71)); d.rectangle((2, 10, 4, 12), fill=(176, 182, 192))
    d.polygon([(4, 13), (36, 13), (39, 24), (1, 24)], fill=(40, 44, 54))
    for r in range(3):
        for c in range(8):
            down = (r * 8 + c) % 4 == key
            d.rectangle((6 + c * 4, 15 + r * 3 + down, 8 + c * 4, 16 + r * 3 + down), fill=(220, 224, 232))
    return outline(img)


@lru_cache(None)
def liner():
    """Early-1900s steamship, side view (100x34): dark hull, white decks, two funnels."""
    img = Image.new('RGBA', (100, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(2, 20), (98, 20), (92, 33), (8, 33)], fill=(30, 32, 40)); d.line([(4, 22), (96, 22)], fill=(170, 60, 60))
    d.rectangle((18, 12, 82, 20), fill=(236, 236, 240)); d.rectangle((30, 6, 70, 12), fill=(226, 228, 236))
    for x in range(20, 80, 4): d.point((x, 15), fill=(255, 220, 140))
    for x in (40, 56): d.rectangle((x, 0, x + 5, 7), fill=(196, 120, 50)); d.rectangle((x, 0, x + 5, 1), fill=(30, 30, 36))
    d.line([(10, 20), (14, 4)], fill=(150, 150, 160)); d.line([(90, 20), (86, 4)], fill=(150, 150, 160))
    return outline(img)


def rain(cv, t, seed=3, n=90, a=110):
    d = ImageDraw.Draw(cv); r = fx.rng(seed)
    xs, ys, sp = r.uniform(-200, W + 200, n), r.uniform(0, H, n), r.uniform(1800, 2600, n)
    for x, y, v in zip(xs, ys, sp):
        yy = (y + v * t) % (H + 200) - 100; xx = x - 0.25 * (yy - y)
        d.line([(xx, yy), (xx - 14, yy + 56)], fill=(190, 205, 235, a), width=3)


def two_tone(cv, t, t0, t1, parts, y, sz=120, rot=-2.0):
    """One title line made of differently coloured words, popping in at t0 and out at t1."""
    if not (t0 <= t < t1 + 0.2): return
    imgs = [kit.text_img(s, c, sz) for s, c in parts]
    wsum = sum(i.width for i in imgs) - 50 * (len(imgs) - 1)
    line = Image.new('RGBA', (wsum, max(i.height for i in imgs)), (0, 0, 0, 0)); x = 0
    for i in imgs: line.alpha_composite(i, (x, 0)); x += i.width - 50
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2) * min(1.0, 1000 / line.width) * (1 + 0.025 * math.sin(t * 8))
    blit(cv, line, W / 2, y, k, k, rot + 1.5 * math.sin(t * 3), anchor='center')


# ================================================================== shot 1: hook, the face on the bonnet (rain)
FIG = (860, 960)                                                      # figure stands on the grille shell
FIG_BASE = GROUND + 230 - 40 * 9 + 8 * 9
CAM1 = Camera(W, H, [(-1.0, (820, 900, 1.7)), (0.0, (820, 900, 1.7)), (1.0, (620, 980, 1.12), 'io'), (3.3, (600, 980, 1.18))],
              kicks=[(0.0, 0.14, FIG[0], 900), (1.5, 0.1, FIG[0], 900), (2.71, 0.08, 540, 1000)], shakes=[(0.0, 0.3, 6)])
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-200, 600)), (0.7, (-200, 600)), (1.1, (190, GROUND + 120), 'oc')]), size=6, legs='auto', arms='fly',
                expr='wow', face=1, ground=None)),
    (1.1, dict(ground=GROUND + 120, squash=True, arms='point', point=FIG, look=FIG, expr='wow', face=None)),
    (2.71, dict(arms='present', expr='smile')),
], words=WORDS, base_size=6)


def bonnet_scene(t, wet=True, warm=0.0):
    img = kit.street(t, 30 * t).convert('RGBA')
    if warm: img = Image.blend(img, Image.new('RGBA', (W, H), (255, 170, 90, 255)), 0.22 * warm)
    fg = layer()
    fx.rays(fg, t, 0.0, FIG[0], FIG_BASE - 150, (200, 220, 255) if not warm else GLOW, hold=True, r=520, n=10)
    blit(fg, up(bonnet(), 9), 470, GROUND + 230)
    glow = 1 + 0.06 * math.sin(t * 5)
    halo = Image.new('RGBA', (360, 360), (0, 0, 0, 0)); ImageDraw.Draw(halo).ellipse((0, 0, 359, 359), fill=(230, 240, 255, 60))
    blit(fg, halo, FIG[0], FIG_BASE - 150, glow, glow, anchor='center')
    blit(fg, up(figure(), 10), FIG[0], FIG_BASE + 6, 1, 1, -2 * math.sin(t * 1.5))
    fx.glint(fg, t, int(t / 1.4) * 1.4 + 0.2, FIG[0] + 30, FIG_BASE - 230, r=110)
    fx.sparkles(fg, t, FIG[0], FIG_BASE - 150, 380, 300, n=7, seed=11)
    if wet: rain(fg, t)
    return img, fg


def shot_hook(t):
    img, fg = bonnet_scene(t)
    photo(fg, t, 1.55, 3.25, 'mascot_crop', 330, 560, 420, 380, -5, 'SPIRIT OF ECSTASY', focus=(0.45, 0.4), zoom=0.1)
    P1.draw(fg, t)
    img.alpha_composite(fg)
    return CAM1.apply(img.convert('RGB'), t, (14, 15, 18))


def overlay(cv, t):
    two_tone(cv, t, 0.05, 1.45, (('THE ', kit.WHITE), ('FACE', YEL)), 430, 150, -3)
    two_tone(cv, t, 0.35, 1.45, (('ON THE BONNET.', kit.WHITE),), 590, 110, 2)
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 430, (255, 255, 255), life=0.35, r1=520)


# ================================================================== shot 2: 1911 on the calendar
CAM2 = Camera(W, H, [(3.3, (540, 860, 1.2)), (3.6, (540, 860, 1.12), 'io'), (4.75, (540, 860, 1.18))], kicks=[(3.6, 0.16, 540, 760)],
              shakes=[(3.6, 0.2, 10)])
P2 = Presenter([
    (3.3, dict(path=Track([(3.3, (1300, 400)), (3.6, (860, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (3.6, dict(ground=GROUND, squash=True, arms='cheer', expr='grin', face=None, look_camera=True)),
], words=WORDS, base_size=7)


def shot_1911(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 3.6, 540, 760, GRN, life=1.0, r=600)
    yr = 1905 + int(round(6 * oc(prog(t, 3.3, 0.3))))
    for back in range(2):                                                       # torn pages fly off as it rolls
        u = (t - 3.3) * 6 - back * 0.5
        if 0 < u % 1 < 0.9 and t < 3.6:
            blit(fg, page(yr - 1 - back), 540 + 500 * (u % 1), 760 - 300 * (u % 1), 0.9, 0.9, 40 * (u % 1), anchor='center')
    kp = popin(t, 3.3, 0.2)
    blit(fg, page(yr), 540, 760, kp, kp * (1 if t >= 3.6 else max(0.2, abs(math.cos((t - 3.3) * 30)))), -3, anchor='center')
    if t >= 3.6:
        kb = ob(prog(t, 3.6, 0.2)) * (1 + 0.04 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'SINCE 1911', '#7fe3a0', '#1a1a2e', '#3cc85a', s=10), 540, 440, kb, kb, -4, anchor='center')
        fx.burst(fg, t, 3.6, 540, 760, GRN, n=16, seed=21)
        fx.gsparkles(fg, t, 540, 760, 560, 500, n=10, seed=22)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the sculptor's workshop
PL = (600, GROUND)
P3 = Presenter([
    (4.7, dict(path=Track([(4.7, (-200, 500)), (5.05, (210, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='think', face=1, ground=None)),
    (5.05, dict(ground=GROUND, squash=True, arms='think', look=(PL[0], 700), expr='think', face=None)),
    (5.77, dict(arms='point', point=(PL[0], 720), look=(PL[0], 720), expr='wow')),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(4.7, (560, 860, 1.25)), (5.6, (560, 840, 1.15), 'io'), (6.95, (560, 820, 1.22))],
              kicks=[(4.84, 0.08, PL[0], 700), (5.77, 0.12, PL[0], 520)])


def shot_sculptor(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    fx.rays(fg, t, 4.8, PL[0], 700, (220, 230, 255), hold=True, r=560, n=10)
    d.rectangle((PL[0] - 120, GROUND - 230, PL[0] + 120, GROUND), fill=(90, 74, 60)); d.rectangle((PL[0] - 140, GROUND - 250, PL[0] + 140, GROUND - 222), fill=(120, 100, 80))
    blit(fg, up(figure(), 16), PL[0], GROUND - 245 + 4 * math.sin(t * 2))
    for i, t0 in enumerate((4.85, 5.1, 5.35, 5.6, 5.85, 6.1, 6.35)):                # chisel taps: chips and sparks
        px, py = PL[0] + (-90, 70, -40, 100, -110, 40, 0)[i], 560 + (40, 120, 230, 300, 180, 70, 360)[i]
        fx.burst(fg, t, t0, px, py, (255, 236, 180), n=6, r0=8, r1=90, seed=30 + i)
        fx.dust(fg, t, t0, px, py, n=5, seed=40 + i, life=0.5)
    dg.label(fg, t, 5.77, 'SCULPTOR: CHARLES SYKES', (PL[0], 560), (520, 470), '#fff6e0', '#1a1a2e', '#d6d9e2', s=6)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: Rolls-Royce says (hedged)
PF = (560, 720)
P4 = Presenter([
    (6.9, dict(path=Track([(6.9, (1300, 500)), (7.3, (940, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='think', face=-1, ground=None)),
    (7.3, dict(ground=GROUND, squash=True, arms='think', look=PF, expr='think', face=None)),
    (8.7, dict(arms='present', look=(PF[0], 1060), expr='smile')),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(6.9, (560, 860, 1.25)), (7.51, (560, 820, 1.15), 'io'), (9.75, (560, 840, 1.2))],
              kicks=[(7.51, 0.14, *PF), (8.7, 0.1, PF[0], 1060)], shakes=[(7.51, 0.2, 8)])


def shot_claim(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    kf = popin(t, 6.95, 0.3)
    blit(fg, up(portrait(), 12), PF[0], PF[1], kf, kf, -2 + 1.5 * math.sin(t * 2), anchor='center')
    kq = popin(t, 7.1, 0.3) * (1 + 0.06 * math.sin(t * 7))
    blit(fg, fx.big('glyph', '?', '#ffd23f', s=20), PF[0], PF[1], kq, kq, 6 * math.sin(t * 3), anchor='center')
    if t >= 7.51:
        ks = ob(prog(t, 7.51, 0.16))
        blit(fg, fx.big('stamp', 'ROLLS-ROYCE SAYS', '#e0303a', '#fff6e0', s=6), PF[0] - 20, PF[1] - 360, ks, ks, -7, anchor='center')
        fx.ring(fg, t, 7.51, PF[0], PF[1] - 360, (224, 48, 58), life=0.3, r1=360)
    P4.draw(fg, t)                                                                  # name plate stays in front of him
    if t >= 8.7:
        kn = popin(t, 8.7, 0.3)
        blit(fg, fx.big('tag', 'ELEANOR THORNTON', '#fff6e0', '#1a1a2e', s=7), PF[0] - 20, PF[1] + 340, kn, kn, 2 * math.sin(t * 3), anchor='center')
        fx.sparkles(fg, t, PF[0], PF[1] + 340, 640, 120, n=6, seed=51)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the office, 1915
P5 = Presenter([
    (9.7, dict(path=Track([(9.7, (-200, 600)), (10.05, (180, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (10.05, dict(ground=GROUND, squash=True, arms='present', look=(560, 900), expr='smile', face=None)),
    (12.23, dict(arms='down2', expr='sad', look=(760, 560))),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(9.7, (560, 900, 1.2)), (11.0, (560, 880, 1.25), 'io'), (12.6, (640, 760, 1.35), 'io'), (13.65, (640, 760, 1.38))],
              kicks=[(10.16, 0.06, 560, 900), (12.6, 0.1, 760, 560)])


def shot_office(t):
    drain = io(prog(t, 12.25, 0.8))
    base = GAR.frame(t).convert('RGBA')
    img = Image.blend(base, ImageEnhance.Color(base).enhance(0.0), 0.7 * drain) if drain > 0 else base
    fg = layer(); d = ImageDraw.Draw(fg)
    d.rectangle((300, GROUND - 260, 860, GROUND - 230), fill=(120, 84, 56)); d.rectangle((330, GROUND - 230, 360, GROUND), fill=(90, 62, 40))
    d.rectangle((800, GROUND - 230, 830, GROUND), fill=(90, 62, 40))
    key = int(t * 12) % 4 if t < 12.2 else 0
    blit(fg, up(typewriter(key), 9), 580, GROUND - 255)
    if t < 12.2:
        for i in range(3):
            if int(t * 12 + i) % 3 == 0: fx.burst(fg, t, t - 0.01, 520 + 60 * i, GROUND - 400, (255, 255, 255), n=3, r0=10, r1=40, seed=60 + i)
    if t >= 10.58:
        ko = popin(t, 10.58, 0.25) * popout(t, 12.1)
        blit(fg, fx.big('tag', "MANAGING DIRECTOR'S OFFICE", '#fff6e0', '#1a1a2e', s=5), 560, 620, ko, ko, -3, anchor='center')
    if t >= 12.6:
        kc = popin(t, 12.6, 0.3)
        blit(fg, page(1915, round(1 - drain, 1)), 760, 560, kc * 0.75, kc * 0.75, 3, anchor='center')
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: the ship, then calm
SEA_Y = 1180
SHIP = (640, SEA_Y + 20)
CAM6 = Camera(W, H, [(13.6, (560, 1000, 1.2)), (14.21, (600, 1000, 1.3), 'io'), (15.5, (600, 980, 1.22), 'io')],
              kicks=[(14.21, 0.06, *SHIP)])


@lru_cache(None)
def sea_base():
    img = Image.new('RGBA', (W, H), (10, 14, 30, 255)); d = ImageDraw.Draw(img)
    for y in range(0, SEA_Y, 6):
        u = y / SEA_Y; d.rectangle((0, y, W, y + 6), fill=(int(10 + 30 * u), int(14 + 40 * u), int(30 + 70 * u)))
    d.ellipse((780, 300, 880, 400), fill=(236, 236, 220)); d.ellipse((800, 300, 900, 400), fill=(18, 26, 52))   # crescent moon
    d.rectangle((0, SEA_Y, W, H), fill=(12, 26, 48))
    return img


def shot_ship(t):
    img = sea_base().copy(); fg = layer(); d = ImageDraw.Draw(img)
    for i in range(14):                                                           # moving wave lines + moon path
        y = SEA_Y + 24 + i * 40; off = (t * (40 + i * 6)) % 160
        for x in range(-160, W, 160): d.line([(x + off, y), (x + off + 60, y)], fill=(40, 70, 110), width=4)
        d.line([(850 - 20 * i, y), (870 + 20 * i, y)], fill=(120, 130, 150), width=3)
    calm = prog(t, 14.6, 0.6)
    sink = 30 * ic(prog(t, 14.4, 1.0))
    blit(fg, up(liner(), 7), SHIP[0], SHIP[1] + sink, 1, 1, -2 * calm)
    if t < 14.3:                                                                  # the wake streak runs toward the hull
        x1 = lerp(-100, SHIP[0] - 200, prog(t, 13.65, 0.6))
        d2 = ImageDraw.Draw(fg)
        for k in range(14):
            x = x1 - k * 34
            if x > -40: d2.ellipse((x - 11, SEA_Y + 70 - 7, x + 11, SEA_Y + 70 + 7), fill=(230, 240, 255, 240 - k * 15))
    fx.ring(fg, t, 14.21, SHIP[0] - 200, SEA_Y + 60, (255, 230, 180), life=0.5, r1=300)
    if t >= 14.87:
        kc = popin(t, 14.87, 0.3)
        blit(fg, fx.big('tag', 'OFF CRETE, 1915', '#fff6e0', '#1a1a2e', s=8), 540, 760, kc, kc, -2, anchor='center')
    img.alpha_composite(fg)
    out = img.convert('RGB')
    if calm > 0: out = Image.blend(out, ImageEnhance.Color(out).enhance(0.3), 0.5 * calm)
    return CAM6.apply(out, t, (10, 14, 30))


# ================================================================== shot 7: a story (sunrise, no rain)
CAM7 = Camera(W, H, [(15.45, (760, 920, 1.35)), (16.37, (620, 960, 1.15), 'io'), (18.1, (620, 960, 1.2))],
              kicks=[(16.37, 0.1, FIG[0], 900), (17.42, 0.16, 540, 760)], shakes=[(17.42, 0.2, 8)])
P7 = Presenter([
    (15.45, dict(path=Track([(15.45, (-200, 500)), (15.85, (190, GROUND + 120), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=1,
                 ground=None)),
    (15.85, dict(ground=GROUND + 120, squash=True, arms='point', point=FIG, look=FIG, expr='smile', face=None)),
    (17.42, dict(arms='present', expr='grin', look=None, look_camera=True, point=None)),
], words=WORDS, base_size=6)


def shot_story(t):
    img, fg = bonnet_scene(t, wet=False, warm=oc(prog(t, 15.45, 0.8)))
    if t >= 17.42:
        ks = ob(prog(t, 17.42, 0.2)) * (1 + 0.04 * math.sin(t * 8))
        blit(fg, fx.big('badge', 'A STORY', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 470, 640, ks, ks, -5, anchor='center')
        fx.burst(fg, t, 17.42, 470, 640, GLOW, n=16, seed=71)
        fx.confetti(fg, t, 17.42, 560, 520, n=30, seed=72)
    P7.draw(fg, t)
    img.alpha_composite(fg)
    return CAM7.apply(img.convert('RGB'), t, (14, 15, 18))


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.3, shot_1911), (4.7, shot_sculptor), (6.9, shot_claim), (9.7, shot_office), (13.6, shot_ship),
         (15.45, shot_story), (END_T, shot_teaser)]
TRANS = {1: (3.3, 3.5, 'whip', dict(dx=-1)), 2: (4.7, 4.9, 'push', None), 3: (6.9, 7.12, 'iris', (PL[0], 600)),
         4: (9.7, 9.9, 'whip', dict(dx=1)), 5: (13.6, 13.8, 'push', None), 6: (15.45, 15.65, 'whip', dict(dx=0, dy=-1)),
         7: (END_T, END_T + 0.2, 'whip', dict(dx=0, dy=1))}
KEYCOL = {'spirit': YEL, 'ecstasy': YEL, '1911': GRN, 'since': GRN, 'sculptor': YEL, 'says': RED, 'thornton': YEL,
          'director': YEL, '1915': RED, 'torpedoed': RED, 'figure': YEL, 'story': YEL}
CUES = [
    (0.0, 'sparkle', 0.9), (0.05, 'stamp', 0.6), (0.35, 'pop', 0.6), (1.1, 'thump', 0.5), (1.55, 'pop', 0.7), (1.57, 'sparkle', 0.5),
    (3.32, 'click', 0.4), (3.4, 'click', 0.4), (3.48, 'click', 0.4), (3.6, 'ding', 0.8), (3.62, 'sparkle', 0.6),
    (4.85, 'click', 0.5), (5.1, 'click', 0.5), (5.35, 'click', 0.5), (5.6, 'click', 0.5), (5.77, 'pop', 0.6), (5.85, 'click', 0.4),
    (6.95, 'pop', 0.5), (7.51, 'stamp', 1.0), (8.7, 'pop', 0.6), (8.72, 'sparkle', 0.5),
    (9.8, 'click', 0.3), (10.0, 'click', 0.3), (10.2, 'click', 0.3), (10.58, 'pop', 0.5), (11.0, 'click', 0.3), (11.4, 'click', 0.3), (12.6, 'thump', 0.4),
    (13.65, 'whoosh', 0.5), (14.21, 'boom', 0.35), (14.87, 'pop', 0.4),
    (15.5, 'sparkle', 0.7), (16.37, 'ding', 0.5), (17.42, 'cha_ching', 0.7), (17.44, 'confetti', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
