"""Renders 'The minivan Ford dropped': a 1972 prototype reportedly shelved after one lap, Iacocca's exit, 1983.

Template: videos/the-land-rover-from-the-sand (ac-idle shot structure on shared/episode.py). Word times come from
align.py -> words.json (the voiceover is the timing spine). Speech runs 0.6-17.1 s; 'Follow' plays over the end card.
The shelving story has a single insider source, so it is hedged on screen (REPORTEDLY). Vans, doors and signs are
generic: no logos, badges or company lettering; names appear only as plain callout labels and captions.
Shots:
  1 lap       0.00  a boxy prototype van circles a test track, the lap board ticks to 1; '1972'; 'One lap.'
  2 shelved   2.50  the van under a dust sheet on a shelf; REPORTEDLY tag, SHELVED stamp, AFTER ONE LAP; the backer
  3 exit      6.00  an office door: FIRED stamp, he walks out, the team follows; a rival HQ sign lights up
  4 vans     9.80  '1983' banner drops; two generic vans roll out, one with wood panels; pixel photos
  5 idea    13.40  the old prototype with a light bulb: FORD IDEA; a door slams on it, WALKED AWAY
  6 teaser  16.10  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.props import sheet
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid, text_width

WORDS = kit.load_words(HERE)
DUR, END_T = 18.0, 16.1


# ------------------------------------------------------------------ episode sprites
def ptext(s, col, ol=False):
    g = Grid(text_width(s) + 2, 9); g.text(1, 1, s, col if isinstance(col, str) else '#%02x%02x%02x' % col)
    return g.image(outline=ol)


def _wheel(d, cx, cy, r, spin, rim):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 27, 32))
    d.ellipse((cx - r + 1.5, cy - r + 1.5, cx + r - 1.5, cy + r - 1.5), fill=(40, 42, 48))
    rr = r * 0.6
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 200, 330, fill=tuple(min(255, c + 50) for c in rim))
    for k in range(6):
        a = math.radians(k * 60 + spin)
        d.point((cx + rr * 0.65 * math.cos(a), cy + rr * 0.65 * math.sin(a)), fill=tuple(int(c * 0.6) for c in rim))
    d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=(230, 232, 238))


VANS = {   # body, shade, hi, deep
    'proto': ((236, 214, 150), (200, 176, 112), (252, 238, 196), (150, 128, 78)),
    'red':   ((178, 40, 48), (138, 28, 36), (226, 96, 100), (96, 18, 24)),
    'blue':  ((86, 120, 170), (62, 92, 136), (146, 178, 220), (40, 60, 96)),
}


@lru_cache(None)
def van(kind='red', spin=0, wood=False):
    """Boxy front-drive minivan (100x46 grid), nose right: one-box profile with a short sloping bonnet, big
    glasshouse, sliding-door rail, square lamps. `wood` adds a woodgrain side panel. No badges."""
    body, shade, hi, deep = VANS[kind]
    img = Image.new('RGBA', (100, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = [(3, 6), (6, 3), (70, 3), (80, 14), (94, 18), (97, 22), (97, 33), (3, 33)]
    d.polygon(pts, fill=body); d.line(pts[:-2], fill=hi)
    d.rectangle((3, 28, 97, 30), fill=shade); d.rectangle((3, 31, 97, 33), fill=deep)
    for x0, x1 in ((6, 24), (27, 48), (51, 66)): d.rectangle((x0, 6, x1, 15), fill=(118, 150, 178)); d.line([(x0 + 1, 7), (x1 - 1, 7)], fill=(196, 222, 240))
    d.polygon([(69, 6), (78, 15), (69, 15)], fill=(118, 150, 178))
    d.line([(25, 4), (25, 28)], fill=deep); d.line([(49, 4), (49, 28)], fill=deep); d.line([(68, 4), (68, 28)], fill=deep)
    d.line([(27, 17), (66, 17)], fill=deep)                                                   # sliding-door rail
    if wood:
        d.rectangle((5, 19, 92, 26), fill=(150, 98, 56)); d.rectangle((5, 19, 92, 19), fill=(226, 214, 190)); d.rectangle((5, 26, 92, 26), fill=(226, 214, 190))
        for x in range(8, 92, 7): d.line([(x, 21), (x + 4, 21)], fill=(120, 76, 40)); d.line([(x + 2, 24), (x + 6, 24)], fill=(120, 76, 40))
    d.rectangle((92, 19, 97, 23), fill=(250, 248, 220)); d.rectangle((92, 24, 97, 27), fill=(220, 224, 232))   # square lamp + grille
    for y in (25, 26): d.line([(92, y), (97, y)], fill=(130, 134, 144))
    d.rectangle((2, 17, 5, 23), fill=(200, 40, 40))
    for cx in (20, 80): d.pieslice((cx - 10, 25, cx + 10, 45), 180, 360, fill=(14, 14, 20))
    for cx in (20, 80): _wheel(d, cx, 36, 8.6, spin, (200, 204, 212))
    return outline(img)


@lru_cache(None)
def exec_guy(step=0, col=(52, 58, 84)):
    """A generic 1970s executive (20x40 grid): grey hair, dark suit, tie, briefcase; `step` 0/1 swings the legs."""
    img = Image.new('RGBA', (20, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    skin, hair = (232, 186, 150), (170, 170, 176)
    d.rectangle((6, 2, 13, 10), fill=skin); d.rectangle((6, 1, 13, 3), fill=hair); d.rectangle((6, 3, 7, 6), fill=hair)
    d.point((11, 6), fill=(26, 26, 46)); d.line([(10, 9), (12, 9)], fill=(160, 100, 90))
    d.rectangle((4, 11, 15, 25), fill=col); d.polygon([(9, 11), (11, 11), (10, 13)], fill=(240, 240, 244))
    d.line([(10, 13), (10, 20)], fill=(200, 40, 48))
    lx = (2, -2) if step else (-1, 1)
    d.rectangle((6 + lx[0], 26, 9 + lx[0], 37), fill=(40, 42, 56)); d.rectangle((11 + lx[1], 26, 14 + lx[1], 37), fill=(40, 42, 56))
    d.rectangle((5 + lx[0], 37, 9 + lx[0], 39), fill=(20, 20, 26)); d.rectangle((11 + lx[1], 37, 15 + lx[1], 39), fill=(20, 20, 26))
    d.rectangle((15, 20, 19, 26), fill=(110, 70, 40)); d.line([(16, 19), (18, 19)], fill=(80, 50, 30))   # briefcase
    return outline(img)


@lru_cache(None)
def door(open_=0.0, lit=False):
    """Office door (34x56) in a frame with a plain nameplate; `open_` swings it open (narrows the leaf)."""
    img = Image.new('RGBA', (34, 56), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 33, 55), fill=(90, 70, 52)); d.rectangle((3, 3, 30, 55), fill=(20, 18, 24) if open_ else (40, 34, 30))
    if open_ < 0.98:
        w = int(27 * (1 - open_))
        d.rectangle((3, 3, 3 + w, 55), fill=(150, 104, 64))
        if w > 5: d.rectangle((5, 6, 1 + w, 26), outline=(120, 80, 48)); d.rectangle((5, 30, 1 + w, 52), outline=(120, 80, 48))
        if w > 6: d.rectangle((w - 2, 30, w, 32), fill=(255, 210, 63))
    d.rectangle((8, -1, 25, 2), fill=(214, 216, 224))
    return outline(img)


@lru_cache(None)
def neon(on=0):
    """A plain rooftop sign box (54x22) whose neon tubes flicker on: a ring and 'NEW HQ' lettering."""
    img = Image.new('RGBA', (54, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 53, 19), fill=(30, 32, 44)); d.rectangle((0, 0, 53, 19), outline=(80, 84, 100))
    for x in (8, 45): d.rectangle((x, 20, x + 1, 23), fill=(80, 84, 100))
    col = (120, 220, 255) if on else (60, 70, 86)
    d.ellipse((4, 4, 15, 15), outline=col); d.ellipse((7, 7, 12, 12), outline=col)
    t = ptext('NEW HQ', col); img.alpha_composite(t, (18, 5))
    return outline(img)


@lru_cache(None)
def bulb(on=True):
    img = Image.new('RGBA', (16, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((1, 0, 14, 13), fill=(255, 236, 120) if on else (200, 200, 190)); d.ellipse((4, 3, 7, 6), fill=(255, 255, 240))
    d.rectangle((5, 13, 10, 19), fill=(170, 176, 188)); d.line([(5, 15), (10, 15)], fill=(120, 124, 134)); d.line([(5, 17), (10, 17)], fill=(120, 124, 134))
    return outline(img)


def lapboard(n):
    return fx.big('badge', f'LAP {n}', '#1a1a2e', '#ff5a5a', '#3c3f47', s=9)


# ------------------------------------------------------------------ test track world (9 px grid)
@lru_cache(None)
def test_track():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    for y in range(110):
        u = y / 110; d.line([(0, y), (119, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip((90, 150, 210), (200, 222, 238))))
    d.polygon([(0, 100), (25, 86), (52, 96), (80, 82), (119, 94), (119, 112), (0, 112)], fill=(110, 140, 96))
    d.rectangle((0, 108, 119, 131), fill=(120, 168, 90))
    d.rectangle((10, 92, 34, 108), fill=(200, 200, 196)); d.rectangle((10, 90, 34, 92), fill=(90, 94, 110))    # test building
    for x in range(13, 33, 5): d.rectangle((x, 96, x + 2, 99), fill=(100, 130, 160))
    for x in (60, 61): d.line([(x, 70), (x, 108)], fill=(90, 94, 110))                                        # flag mast
    d.rectangle((62, 70, 72, 76), fill=(214, 48, 58))
    d.rectangle((0, 132, 119, 160), fill=(84, 86, 96))
    for x in range(0, 120, 8): d.rectangle((x, 131, x + 3, 132), fill=(214, 48, 58)); d.rectangle((x + 4, 131, x + 7, 132), fill=(240, 240, 240))
    for x in range(0, 120, 10): d.rectangle((x, 146, x + 5, 146), fill=(230, 230, 220))
    d.rectangle((0, 161, 119, 213), fill=(110, 156, 84))
    for x in range(0, 120, 4):
        for y in range(164, 214, 6): d.point((x + (y // 6) % 3, y), fill=(96, 140, 72))
    for x in (14, 102): d.polygon([(x, 170), (x + 3, 162), (x + 6, 170)], fill=(255, 140, 40))                 # cones
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


@lru_cache(None)
def offices():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    for y in range(132):
        u = y / 132; d.line([(0, y), (119, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip((22, 26, 54), (70, 64, 110))))
    r = fx.rng(8)
    for _ in range(40): d.point((int(r.uniform(0, 120)), int(r.uniform(0, 60))), fill=(220, 220, 240))
    for x0, x1, top, col in ((0, 50, 40, (60, 64, 84)), (66, 119, 52, (54, 58, 80))):
        d.rectangle((x0, top, x1, 131), fill=col)
        for x in range(x0 + 3, x1 - 2, 6):
            for y in range(top + 4, 120, 7): d.rectangle((x, y, x + 2, y + 3), fill=(255, 220, 140) if (x * 3 + y) % 5 else (70, 74, 96))
    d.rectangle((0, 132, 119, 213), fill=(84, 86, 98))
    for x in range(0, 120, 12): d.rectangle((x, 150, x + 6, 151), fill=(230, 230, 220))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


# ================================================================== shot 1: one lap
TRK_Y = 1330
def lap_x(t): return lerp(-600, 1700, prog(t, 0.0, 2.4))
def lap_n(t): return 0 if t < 1.0 else 1
CAM1 = Camera(W, H, [(-1.0, (540, 1080, 1.22)), (0.0, (540, 1080, 1.22)), (1.0, (540, 1060, 1.1), 'io'), (2.5, (540, 1040, 1.16), 'io')],
              kicks=[(0.0, 0.06, 540, 1000), (0.71, 0.1, 820, 760), (1.0, 0.16, 820, 760), (2.3, 0.1, 540, 1200)])


def shot_lap(t):
    img = test_track().copy(); fg = layer()
    x = lap_x(t)
    fx.contact_shadow(fg, x, TRK_Y, 620, s=S, alpha=120)
    blit(fg, up(van('proto', int(x * 0.8) % 360 // 15 * 15), 6), x, TRK_Y + 2 * math.sin(t * 30))
    fx.puff(fg, t, t - 0.1, x - 320, TRK_Y - 30, seed=int(t * 20) % 40, life=0.5, size=0.6, drift=(-300, -60))
    fx.speed_lines(fg, 0.3, int(t * 10) % 5, col=(220, 226, 236))
    k = popin(t, 0.1, 0.25)
    blit(fg, lapboard(lap_n(t)), 820, 760, k * (1 + 0.15 * math.exp(-(t - 1.0) * 8) * (t >= 1.0)), k, 3, anchor='center')
    fx.ring(fg, t, 1.0, 820, 760, RED, life=0.3, r1=260); fx.burst(fg, t, 1.0, 820, 760, RED, n=12, seed=1)
    if t >= 0.71:
        k = popin(t, 0.71, 0.25)
        blit(fg, fx.big('tag', '1972', '#fff6e0', '#1a1a2e', s=8), 300, 870, k, k, -5, anchor='center')
    dg.label(fg, t, 2.3, 'PROTOTYPE', (x, TRK_Y - 260), (700, 980), '#ffffff', '#1a1a2e', '#d6d9e2', s=6) if 2.3 <= t < 2.5 else None
    return finish(img, fg, CAM1, t, rim=False)


def overlay(cv, t):
    title(cv, t, 0.05, 2.4, 'One', RED, 440, 170, -3)
    title(cv, t, 0.3, 2.4, 'lap.', WHITE, 600, 130, 3)


# ================================================================== shot 2: shelved
SHELF = GROUND - 40
P2 = Presenter([
    (2.45, dict(path=Track([(2.45, (1300, 300)), (2.85, (920, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.85, dict(ground=GROUND, squash=True, arms='point', point=(480, SHELF - 200), look=(480, SHELF - 200), expr='think', face=None)),
    (3.63, dict(arms='shock', point=None, expr='shock', squash=True)),
    (4.89, dict(arms='present', look=(250, 900), expr='smile')),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.5, (540, 900, 1.14)), (3.63, (500, 920, 1.26), 'io'), (4.5, (540, 900, 1.12), 'io'), (5.07, (380, 880, 1.2), 'io'), (6.0, (420, 880, 1.22))],
              kicks=[(2.6, 0.06, 480, 900), (3.17, 0.08, 540, 520), (3.63, 0.18, 480, 900), (4.2, 0.1, 760, 600), (5.61, 0.1, 250, 820)], shakes=[(3.63, 0.3, 14)])


def shot_shelved(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    lift = 1 - 0.62 * oc(prog(t, 2.55, 0.6))                                                       # the dust sheet settles over the van
    blit(fg, up(van('proto'), 6), 480, SHELF)
    sh = up(sheet(round(lift * 20) / 20), 8)
    sh = sh.resize((int(sh.width * 1.25), sh.height), Image.NEAREST)
    blit(fg, sh, 480, SHELF + 10)
    fx.dust(fg, t, 3.15, 480, SHELF, n=14, seed=20, col=(200, 196, 186))
    if t >= 3.17:
        k = popin(t, 3.17, 0.25)
        blit(fg, fx.big('tag', 'REPORTEDLY', '#fff6e0', '#e8a000', s=8), 430, 470, k, k, -4 + 2 * math.sin(t * 5), anchor='center')
    if t >= 3.63: fx.stamp_at(fg, t, 3.63, 'SHELVED', 480, SHELF - 230, rot=-10, s=12)
    if t >= 4.2:
        k = popin(t, 4.2, 0.25) * popout(t, 4.85)
        blit(fg, fx.big('badge', 'AFTER 1 LAP', '#ffffff', '#d6303a', '#d6d9e2', s=7), 640, 600, k, k, 5, anchor='center')
    if t >= 4.89:                                                                           # the backer
        u = oc(prog(t, 4.89, 0.35))
        blit(fg, up(exec_guy(int(t * 6) % 2 if u < 1 else 0), 8), lerp(-100, 220, u), GROUND)
        dg.label(fg, t, 5.07, 'LEE IACOCCA', (220, GROUND - 330), (250, 620), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
        if t >= 5.61:
            k = popin(t, 5.61, 0.22); blit(fg, fx.big('check', s=9), 470, 640, k, k, anchor='center')
            fx.ring(fg, t, 5.61, 470, 610, (60, 200, 90), life=0.3, r1=180)
            blit(fg, fx.big('tag', 'BACKED IT', '#e8fff0', '#3cc85a', s=6), 250, 500, k, k, -3, anchor='center')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: fired; he takes the team across town
DOOR_X, NEON_X = 220, 820
def walk_x(t): return lerp(DOOR_X, 760, prog(t, 8.0, 1.6))
TEAM = [(8.28, (90, 140, 90)), (8.46, (140, 90, 60)), (8.64, (90, 100, 160)), (8.82, (150, 120, 60))]
CAM3 = Camera(W, H, [(6.0, (380, 920, 1.2)), (7.52, (300, 900, 1.3), 'io'), (8.28, (480, 940, 1.1), 'io'), (9.1, (700, 860, 1.22), 'io'), (9.8, (700, 860, 1.24))],
              kicks=[(6.28, 0.1, 540, 420), (7.52, 0.16, DOOR_X, 900), (8.77, 0.08, 500, 1000), (9.1, 0.16, NEON_X, 640)], shakes=[(7.52, 0.3, 12)])


def shot_exit(t):
    img = offices().copy(); fg = layer()
    op = oc(prog(t, 7.7, 0.25))
    blit(fg, up(door(op), 9), DOOR_X, GROUND)
    dg.label(fg, t, 6.28, 'FORD, 1978', (DOOR_X, GROUND - 500), (DOOR_X + 90, 640), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=8.0)
    if 7.52 <= t < 8.5: fx.stamp_at(fg, t, 7.52, 'FIRED', DOOR_X + 40, GROUND - 260, rot=-12, s=12)
    if t >= 7.95:                                                                          # he leaves; the team follows him out
        for i, (ts, col) in enumerate([(7.95, (52, 58, 84))] + TEAM):
            x = lerp(DOOR_X, 760 - 120 * i, oc(prog(t, ts, 1.0)))
            st = int(t * 7 + i) % 2 if prog(t, ts, 1.0) < 1 else 0
            if t >= ts: blit(fg, up(exec_guy(st, col), 8 if i == 0 else 6), x, GROUND)
    dg.label(fg, t, 8.77, 'THE TEAM', (520, GROUND - 260), (420, 760), '#7fe3a0', '#1a1a2e', '#3cc85a', s=7)
    on = t >= 9.1 and (t >= 9.3 or int(t * 30) % 2)
    blit(fg, up(neon(on), 9), NEON_X, 720)
    if t >= 9.1:
        fx.rays(fg, t, 9.1, NEON_X, 620, (120, 220, 255), life=0.5, r=380)
        fx.burst(fg, t, 9.1, NEON_X, 620, (120, 220, 255), n=14, seed=30)
        dg.label(fg, t, 9.12, 'CHRYSLER', (NEON_X, 520), (NEON_X - 80, 400), '#7fd4ff', '#1a1a2e', '#3c8cc8', s=7)
        fx.sparkles(fg, t, NEON_X, 600, 400, 200, n=6, seed=31)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: 1983, two vans
V1, V2 = 300, 780
def van1_x(t): return lerp(-500, V1, oc(prog(t, 11.13, 0.8)))
def van2_x(t): return lerp(1600, V2, oc(prog(t, 12.15, 0.6)))
CAM4 = Camera(W, H, [(9.8, (540, 900, 1.12)), (11.13, (540, 940, 1.04), 'io'), (11.87, (440, 960, 1.1), 'io'), (12.79, (640, 960, 1.1), 'io'), (13.4, (540, 940, 1.06), 'io')],
              kicks=[(9.91, 0.16, 540, 420), (10.61, 0.08, 540, 420), (11.9, 0.1, V1, 1000), (13.1, 0.1, V2, 1000)])


def shot_vans(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 9.91, 540, 400, GLOW, life=1.1, r=560)
    y = lerp(-200, 470, oc(prog(t, 9.85, 0.35)))
    blit(fg, fx.big('badge', '1983', '#ffd23f', '#1a1a2e', '#e8b923', s=16), 540, y, 1, 1, -2 + 2 * math.sin(t * 3), anchor='center')
    fx.burst(fg, t, 9.91, 540, 400, GLOW, n=16, seed=40); fx.confetti(fg, t, 9.93, 540, 400, n=30, seed=41)
    for xf, kind, wood, lab, lt, at in ((van1_x, 'red', False, 'DODGE CARAVAN', 11.87, (300, 640)), (van2_x, 'blue', True, 'PLYMOUTH VOYAGER', 12.79, (760, 780))):
        x = xf(t)
        fx.contact_shadow(fg, x, GROUND, 420, s=S, alpha=130)
        blit(fg, up(van(kind, int(x * 0.8) % 360 // 15 * 15, wood), 4), x, GROUND, flip=kind == 'blue')
        dg.label(fg, t, lt, lab, (x, GROUND - 220), at, '#ffffff', '#1a1a2e', '#d6d9e2', s=6)
    fx.dust(fg, t, 11.93, V1, GROUND, n=10, seed=42); fx.dust(fg, t, 13.15, V2, GROUND, n=10, seed=43)
    if t >= 12.9: fx.sparkles(fg, t, 540, GROUND - 160, 900, 260, n=8, seed=44)
    GAR.reflect(img, fg)
    photo(fg, t, 10.3, 11.05, 'caravan', 560, 960, 600, 420, -3, 'AN EARLY CARAVAN (1986)', focus=(0.68, 0.6), zoom=0.3, pix=4)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: a Ford idea Ford walked away from
PX = 600
P5 = Presenter([
    (13.35, dict(path=Track([(13.35, (-200, 400)), (13.75, (170, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (13.75, dict(ground=GROUND, squash=True, arms='point', point=(PX, 700), look=(PX, 700), expr='smile', face=None)),
    (15.32, dict(arms='shrug', point=None, look=(PX, 1000), expr='sad', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(13.4, (560, 900, 1.12)), (14.41, (600, 860, 1.24), 'io'), (15.32, (560, 900, 1.12), 'io'), (16.1, (560, 900, 1.16))],
              kicks=[(13.56, 0.08, PX, 1000), (14.41, 0.14, PX, 700), (15.32, 0.16, PX, 1000)], shakes=[(15.32, 0.3, 12)])


def shot_idea(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, PX, GROUND, 560, s=S, alpha=130)
    fade = 1 - 0.45 * prog(t, 15.32, 0.4)
    v = up(van('proto'), 6)
    if fade < 1: v = Image.blend(Image.new('RGBA', v.size, (0, 0, 0, 0)), v, 1.0); v.putalpha(v.getchannel('A').point(lambda a: int(a * fade)))
    blit(fg, v, PX, GROUND)
    if t >= 14.41:
        k = popin(t, 14.41, 0.25)
        on = t < 15.32 or int(t * 20) % 3 == 0 and t < 15.6
        blit(fg, up(bulb(on), 10), PX, 620, k, k, 4 * math.sin(t * 5))
        if on: fx.rays(fg, t, 14.41, PX, 520, GLOW, life=0.9, r=360)
        blit(fg, fx.big('tag', 'FORD IDEA', '#fff6e0', '#1a1a2e', s=7), PX, 360, k, k, -4, anchor='center')
    if t >= 15.32:
        fx.stamp_at(fg, t, 15.32, 'WALKED AWAY', PX, GROUND - 160, rot=-8, s=9)
        fx.puff(fg, t, 15.34, PX, GROUND - 60, seed=50, life=0.7, size=1.2)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 13.5, 14.3, 'voyager', 600, 700, 560, 400, 3, 'A 1984 VOYAGER', focus=(0.38, 0.6), zoom=0.3, pix=4)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(16.1, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_lap), (2.5, shot_shelved), (6.0, shot_exit), (9.8, shot_vans), (13.4, shot_idea), (16.1, shot_teaser)]
TRANS = {1: (2.5, 2.7, 'whip', dict(dx=1)), 2: (6.0, 6.2, 'push', None), 3: (9.8, 10.0, 'whip', dict(dx=0, dy=1)),
         4: (13.4, 13.6, 'whip', dict(dx=-1)), 5: (16.1, 16.3, 'whip', dict(dx=1))}
KEYCOL = {'1972': YEL, 'reportedly': YEL, 'shelved': YEL, 'one': RED, 'iacocca': YEL, '1978': YEL, 'fired': RED, 'took': GRN,
          'team': GRN, '1983': YEL, 'caravan': GRN, 'voyager': GRN, 'idea': YEL, 'walked': RED}
CUES = [
    (0.0, 'vroom', 0.6), (0.05, 'pop', 0.5), (0.1, 'pop', 0.6), (0.3, 'pop', 0.5), (0.71, 'stamp', 0.6), (1.0, 'ding', 0.9), (1.02, 'click', 0.6),
    (2.3, 'whoosh', 0.4),
    (2.55, 'creak', 0.5), (3.15, 'thump', 0.5), (3.17, 'pop', 0.6), (3.63, 'stamp', 0.9), (4.2, 'pop', 0.6), (4.89, 'whoosh', 0.4),
    (5.07, 'pop', 0.5), (5.61, 'ding', 0.6),
    (6.28, 'stamp', 0.6), (6.5, 'pop', 0.4), (7.52, 'stamp', 0.9), (7.53, 'buzzer', 0.4), (7.7, 'creak', 0.6),
    (8.28, 'pop', 0.4), (8.46, 'pop', 0.4), (8.64, 'pop', 0.4), (8.82, 'pop', 0.4), (8.77, 'pop', 0.5), (9.1, 'click', 0.7), (9.12, 'ding', 0.7),
    (9.14, 'sparkle', 0.7),
    (9.85, 'fall', 0.5), (9.91, 'stamp', 0.9), (9.93, 'confetti', 0.7), (10.3, 'pop', 0.6), (11.13, 'vroom', 0.7), (11.87, 'pop', 0.6),
    (12.15, 'vroom', 0.7), (12.79, 'pop', 0.6), (12.9, 'sparkle', 0.6),
    (13.56, 'pop', 0.4), (14.41, 'ding', 0.8), (14.43, 'click', 0.6), (15.32, 'stamp', 0.9), (15.34, 'poof', 0.6),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
