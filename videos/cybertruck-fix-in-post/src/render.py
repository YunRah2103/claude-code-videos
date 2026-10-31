"""Renders 'Cybertruck, fix it in post': the 2019 reveal, a steel ball, two broken windows on the demo truck.

Template: videos/the-trabant (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). Speech runs 0.0-13.1 s; the supplied read has no 'Follow' line, so
the end card shows it. Framed as a demo at a reveal (DEMO TRUCK tag), not a production failure. The truck is a
generic pixel wedge with no badges or lettering; the thrower is an anonymous figure (no likeness).
Shots:
  1 reveal   0.00  a steel ball streaks across the stage; 'We'll fix it in post'; the wedge truck under spotlights;
                   REVEAL, 2019, DEMO TRUCK; photo card of a later production truck (pixel redraw)
  2 throw    3.30  an anonymous figure winds up and throws the ball; it arcs to the driver's window
  3 driver   6.20  the window cracks, then shatters: camera punch, glass sparkles; 'driver's window'
  4 rear     8.00  a second ball hits the rear window: it cracks too; 'then the rear'
  5 post    10.30  he shrugs; quote bubble 'We'll fix it in post'; tape slaps over both windows: FIXED IN POST?
  6 teaser  14.20  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
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
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE, 'words_v1.json')     # first read: the body shots are timed on it
NEW = kit.load_words(HERE)                          # current read (captions); WARP maps it onto WORDS
Q_END = kit.at(NEW, 'at', 1) - 0.25                 # cuts follow the read: question / body / question
BODY_END = kit.at(NEW, 'would') - 0.12
END_T = NEW[-1]['e'] + 0.3
DUR = END_T + 1.0
STEEL, STEEL_HI, STEEL_LO = (186, 190, 196), (224, 228, 234), (140, 144, 152)
GLASS = (46, 56, 72)
FRONT_WIN = [(60, 8), (88, 17), (88, 19), (60, 19)]
REAR_WIN = [(32, 14), (56, 8), (56, 19), (32, 19)]
DRIVER_HIT, REAR_HIT = (73, 15), (44, 15)            # impact points (grid units)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def truck(spin=0):
    """Angular stainless pickup (110x44), nose right: one roof peak, flat brushed panels, light bar, square arches."""
    img = Image.new('RGBA', (110, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body = [(2, 22), (4, 18), (58, 4), (104, 20), (108, 24), (108, 33), (2, 33)]
    d.polygon(body, fill=STEEL); d.line(body[1:5], fill=STEEL_HI)
    for x in range(6, 106, 7): d.line([(x, 22), (x + 3, 32)], fill=(176, 180, 188))          # brushed grain
    d.line([(2, 25), (108, 25)], fill=STEEL_LO)
    d.polygon(FRONT_WIN, fill=GLASS); d.polygon(REAR_WIN, fill=GLASS)
    d.line([(61, 9), (70, 12)], fill=(110, 130, 160)); d.line([(34, 14), (42, 12)], fill=(110, 130, 160))
    d.line([(96, 19), (108, 23)], fill=(240, 250, 255)); d.line([(2, 21), (6, 20)], fill=(224, 48, 58))   # light bars
    for cx in (22, 88):
        d.polygon([(cx - 13, 33), (cx - 10, 24), (cx + 10, 24), (cx + 13, 33)], fill=(30, 31, 38))
        d.ellipse((cx - 9, 25, cx + 9, 43), fill=(22, 22, 28)); d.ellipse((cx - 5, 29, cx + 5, 39), fill=(120, 126, 138))
        for k in range(3):
            a = math.radians(spin + k * 120); d.line([(cx, 34), (cx + 4 * math.cos(a), 34 + 4 * math.sin(a))], fill=(60, 64, 76))
    return outline(img)


@lru_cache(None)
def ball():
    img = Image.new('RGBA', (12, 12), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 11, 11), fill=(150, 156, 168)); d.ellipse((2, 2, 8, 8), fill=(200, 206, 216)); d.rectangle((3, 3, 4, 4), fill=(255, 255, 255))
    return outline(img)


@lru_cache(None)
def figure(ph=0):
    """Anonymous presenter figure (16x30): dark jacket and trousers, no face detail. ph 0 wind-up, 1 release."""
    img = Image.new('RGBA', (20, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((6, 0, 13, 7), fill=(200, 160, 130)); d.rectangle((6, 0, 13, 2), fill=(50, 40, 34))
    d.rectangle((5, 8, 14, 19), fill=(34, 36, 46)); d.rectangle((6, 19, 9, 29), fill=(26, 28, 36)); d.rectangle((10, 19, 13, 29), fill=(26, 28, 36))
    if ph == 0: d.line([(6, 10), (1, 4)], fill=(34, 36, 46), width=3); d.line([(14, 10), (17, 15)], fill=(34, 36, 46), width=3)
    else: d.line([(14, 10), (19, 7)], fill=(34, 36, 46), width=3); d.line([(6, 10), (2, 16)], fill=(34, 36, 46), width=3)
    return outline(img)


@lru_cache(None)
def bubble_img(txt):
    """Speech bubble with the quote in the caption font."""
    f = kit.font(56); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); w = int(d0.textlength(txt, font=f)) + 70
    img = Image.new('RGBA', (w, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, w - 5, 120), 34, fill=(255, 255, 255), outline=(26, 26, 46), width=8)
    d.polygon([(60, 112), (110, 112), (50, 165)], fill=(255, 255, 255)); d.line([(60, 116), (50, 165), (110, 116)], fill=(26, 26, 46), width=8)
    d.text((35, 22), txt, font=f, fill=(224, 48, 58))
    return img


def cracks(fg, ox, oy, s, hit, k, seed, shattered=False):
    """Spider-web cracks drawn at screen scale around a grid impact point; k 0..1 grows them."""
    if k <= 0: return
    cx, cy = ox + hit[0] * s, oy + hit[1] * s
    d = ImageDraw.Draw(fg); r = fx.rng(seed)
    if shattered: d.ellipse((cx - 60, cy - 40, cx + 60, cy + 40), fill=(12, 14, 20, 255))
    for i in range(9):
        a = i * 0.7 + r.uniform(-0.3, 0.3); L = r.uniform(70, 150) * k
        pts = [(cx, cy)]
        for j in range(1, 5): pts.append((cx + math.cos(a + r.uniform(-0.2, 0.2)) * L * j / 4, cy + math.sin(a + r.uniform(-0.2, 0.2)) * L * j / 4 * 0.6))
        d.line(pts, fill=(230, 240, 255, 255), width=4)
    for rr in (0.35, 0.7):
        ring = [(cx + math.cos(i * 0.7) * 120 * rr * k, cy + math.sin(i * 0.7) * 72 * rr * k) for i in range(10)]
        d.line(ring, fill=(200, 216, 240, 255), width=3)


def truck_at(fg, x, y, s, t, drv=0.0, drv_sh=False, rear=0.0, tape=0.0):
    img = up(truck(0), s); ox, oy = x - img.width / 2, y - img.height
    fg.paste(img, (int(ox), int(oy)), img)
    cracks(fg, ox, oy, s, DRIVER_HIT, drv, 3, drv_sh); cracks(fg, ox, oy, s, REAR_HIT, rear, 7)
    if tape > 0:
        for hit, rot in ((DRIVER_HIT, 20), (REAR_HIT, -15)):
            tp = fx.big('tag', 'FIXED', '#f0e6c8', '#1a1a2e', s=4)
            blit(fg, tp, ox + hit[0] * s, oy + hit[1] * s, tape, tape, rot, anchor='center')
    return ox, oy


# ================================================================== shot 1: hook, the reveal
TX = 540
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.28)), (0.0, (540, 960, 1.28)), (0.9, (540, 960, 1.1), 'io'), (3.3, (540, 940, 1.16), 'io')],
              kicks=[(0.85, 0.16, 900, 760), (1.17, 0.12, TX, 1000), (1.81, 0.12, 300, 700)], shakes=[(0.85, 0.25, 10)])


def shot_reveal(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    for sx_ in (240, 840): fx.rays(fg, t, 1.1, sx_, 300, (255, 240, 210), hold=True, r=700, n=6)
    truck_at(fg, TX, GROUND, 7, t)
    fx.contact_shadow(fg, TX, GROUND, 740, s=7)
    if t < 1.0:                                           # the hook: a ball whips across the frame
        u = prog(t, 0.05, 0.8); bx, by = lerp(-100, 1180, u), lerp(1020, 820, u) - 110 * math.sin(math.pi * u)
        for g in range(5): blit(fg, up(ball(), 13 - g * 2), bx - g * 70, by + g * 12, 1, 1, 0, anchor='center')
        fx.speed_lines(fg, 0.7, 2, col=(200, 204, 220))
    if t >= 1.17:
        k = popin(t, 1.17, 0.25) * popout(t, 1.75)
        blit(fg, fx.big('badge', 'REVEAL', '#ffd23f', '#1a1a2e', '#e8b923', s=10), 540, 760, k, k, -3, anchor='center')
        fx.burst(fg, t, 1.17, 540, 760, GLOW, n=14, seed=1)
    if t >= 1.81:
        k = popin(t, 1.81, 0.25) * popout(t, 2.45)
        blit(fg, fx.big('badge', '2019', '#ffffff', '#1a1a2e', '#d6d9e2', s=11), 300, 740, k, k, -6, anchor='center')
        blit(fg, fx.big('tag', 'DEMO TRUCK', '#fff6e0', '#1a1a2e', s=7), 780, 760, k, k, 5, anchor='center')
    fx.sparkles(fg, t, 540, 900, 900, 300, n=6, seed=2)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, Q_END - 0.1, 'Steel ball vs', WHITE, 480, 130, -3)
    title(cv, t, 0.3, Q_END - 0.1, 'Cybertruck?', RED, 610, 140, 3)
    to = WARP(t)
    if Q_END <= t < BODY_END:
        title(cv, to, 6.42, 7.95, "driver's window", YEL, 480, 104, -2)
        title(cv, to, 8.14, 10.25, 'then the rear', RED, 480, 110, 2)
    kit.photo_hq(cv, t, kit.at(NEW, 'reveal') + 0.05, kit.at(NEW, 'chief') - 0.1, 'cybertruck', 540, 960, 600, -3, 'A LATER PRODUCTION TRUCK')
    title(cv, t, BODY_END + 0.05, END_T - 0.1, 'Would you trust', WHITE, 480, 110, -2)
    title(cv, t, BODY_END + 0.3, END_T - 0.1, 'that window?', YEL, 610, 130, 2)


# ================================================================== shot 2: the throw
FIGX = 230
THROW, HIT = 4.23, 4.93
TX2, S2 = 660, 6
def ball_xy(t):
    u = prog(t, THROW, HIT - THROW); ox = TX2 - 55 * S2; oy = GROUND - 44 * S2
    tx, ty = ox + DRIVER_HIT[0] * S2, oy + DRIVER_HIT[1] * S2
    return lerp(FIGX + 60, tx, u), lerp(GROUND - 300, ty, u) - 240 * math.sin(math.pi * u)
CAM2 = Camera(W, H, [(3.3, (540, 960, 1.08)), (3.78, (420, 960, 1.18), 'io'), (THROW, (440, 960, 1.16), 'io'), (HIT, (640, 940, 1.22), 'io'), (6.2, (640, 940, 1.26))],
              kicks=[(3.41, 0.1, FIGX, 900), (THROW, 0.14, FIGX, 900), (HIT, 0.22, 800, 900)], shakes=[(HIT, 0.3, 14)])


def shot_throw(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    ox, oy = truck_at(fg, TX2, GROUND, S2, t, drv=0.25 * popin(t, HIT, 0.15))
    k = popin(t, 3.35, 0.25)
    blit(fg, up(figure(int(t >= THROW)), 9), FIGX, GROUND, k, k)
    if t < THROW:
        blit(fg, up(ball(), 7), FIGX - 60, GROUND - 260, k, k, 0, anchor='center')
    elif t < HIT + 0.6:
        if t < HIT: bx, by = ball_xy(t)
        else:
            u = prog(t, HIT, 0.6); hx, hy = ball_xy(HIT); bx, by = hx - 200 * u, hy + 300 * u * u
        blit(fg, up(ball(), 7), bx, by, 1, 1, 0, anchor='center')
        if t < HIT: fx.speed_lines(fg, 0.5, 4, col=(190, 194, 210))
    if t >= HIT:
        hx, hy = ball_xy(HIT); fx.ring(fg, t, HIT, hx, hy, (220, 236, 255), r1=260); fx.burst(fg, t, HIT, hx, hy, (220, 236, 255), n=12, seed=10)
    dg.label(fg, t, 3.6, 'CHIEF DESIGNER', (FIGX, GROUND - 280), (440, 680), '#ffffff', '#1a1a2e', '#d6d9e2', s=6, t1=4.9)
    if t >= 4.49:
        k = popin(t, 4.49, 0.25)
        blit(fg, fx.big('tag', 'STEEL BALL', '#fff6e0', '#1a1a2e', s=7), 760, 800, k, k, 4, anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the driver's window shatters
SHAT = 7.14
CAM3 = Camera(W, H, [(6.2, (580, 920, 1.2)), (6.85, (620, 900, 1.34), 'io'), (SHAT, (620, 900, 1.38)), (7.5, (560, 920, 1.16), 'oc'), (8.0, (560, 920, 1.18))],
              kicks=[(6.42, 0.1, 660, 880), (SHAT, 0.3, 660, 880)], shakes=[(SHAT, 0.45, 18)])


def shot_driver(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    grow = 0.25 + 0.75 * oc(prog(t, 6.4, 0.7))
    ox, oy = truck_at(fg, 540, GROUND, 8, t, drv=grow if t < SHAT else 1.0, drv_sh=t >= SHAT)
    hx, hy = ox + DRIVER_HIT[0] * 8, oy + DRIVER_HIT[1] * 8
    if t >= SHAT:
        r = fx.rng(20)
        for i in range(26):                                  # glass shards spill and twinkle
            u = prog(t, SHAT, 0.9); a = r.uniform(0, 6.28); v = r.uniform(120, 420)
            x = hx + math.cos(a) * v * u; y = hy + math.sin(a) * v * u * 0.6 + 700 * u * u
            if y < GROUND + 40:
                sz = int(r.integers(2, 4)) * 6
                ImageDraw.Draw(fg).rectangle((x, y, x + sz, y + sz), fill=(210, 230, 255, 255) if (i + int(t * 12)) % 3 else (255, 255, 255, 255))
        fx.burst(fg, t, SHAT, hx, hy, (220, 236, 255), n=18, seed=21); fx.glint(fg, t, SHAT, hx, hy)
        fx.sparkles(fg, t, hx, hy + 120, 500, 320, n=9, seed=22)
        k = fx.slam(t, SHAT + 0.05) * popin(t, SHAT + 0.05, 0.2)
        blit(fg, fx.big('badge', 'SHATTERED', '#e0303a', '#ffffff', '#b8222c', s=9), 560, 790, k, k, -6, anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: then the rear window
HIT2 = 9.41
def ball2(t):
    u = prog(t, 8.6, HIT2 - 8.6); ox = 540 - 55 * 7; oy = GROUND - 44 * 7
    tx, ty = ox + REAR_HIT[0] * 7, oy + REAR_HIT[1] * 7
    return lerp(-100, tx, u), lerp(GROUND - 260, ty, u) - 200 * math.sin(math.pi * u)
CAM4 = Camera(W, H, [(8.0, (540, 920, 1.08)), (8.74, (460, 920, 1.2), 'io'), (HIT2, (460, 920, 1.24), 'io'), (10.3, (540, 920, 1.12), 'io')],
              kicks=[(8.14, 0.1, 540, 900), (HIT2, 0.26, 420, 900), (9.72, 0.12, 540, 640)], shakes=[(HIT2, 0.4, 16)])


def shot_rear(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    rear = 0 if t < HIT2 else 0.35 + 0.65 * oc(prog(t, HIT2, 0.35))
    ox, oy = truck_at(fg, 540, GROUND, 7, t, drv=1.0, drv_sh=True, rear=rear)
    if 8.6 <= t < HIT2:
        bx, by = ball2(t); blit(fg, up(ball(), 7), bx, by, 1, 1, 0, anchor='center'); fx.speed_lines(fg, 0.5, 6, col=(190, 194, 210))
    if t >= HIT2:
        hx, hy = ox + REAR_HIT[0] * 7, oy + REAR_HIT[1] * 7
        fx.burst(fg, t, HIT2, hx, hy, (220, 236, 255), n=16, seed=30); fx.ring(fg, t, HIT2, hx, hy, (220, 236, 255), r1=300)
        fx.sparkles(fg, t, hx, hy, 420, 260, n=8, seed=31); fx.glint(fg, t, HIT2 + 0.05, hx, hy, r=140)
    if t >= 9.72:
        k = popin(t, 9.72, 0.25)
        blit(fg, fx.big('badge', 'TWO FOR TWO', '#ffd23f', '#1a1a2e', '#e8b923', s=9), 540, 640, k, k, 4 + 2 * math.sin(t * 5), anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: fix it in post
TAPE = 13.0
P5 = Presenter([
    (10.25, dict(path=Track([(10.25, (1300, 300)), (10.65, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (10.65, dict(ground=GROUND, squash=True, arms='point', point=(420, 960), look=(420, 960), expr='smirk', face=None)),
    (11.23, dict(arms='shrug', point=None, look=None, look_camera=True, expr='smirk', squash=True)),
    (TAPE, dict(arms='thumb', expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(10.3, (540, 920, 1.1)), (11.23, (560, 900, 1.14), 'io'), (12.08, (540, 820, 1.12), 'io'), (TAPE, (520, 900, 1.14), 'io'), (14.2, (540, 900, 1.18), 'io')],
              kicks=[(10.58, 0.08, 880, 900), (11.23, 0.12, 880, 900), (12.08, 0.16, 540, 600), (TAPE, 0.18, 420, 960), (13.35, 0.12, 540, 640)])


def shot_post(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    tape = popin(t, TAPE, 0.25)
    truck_at(fg, 470, GROUND, 6, t, drv=1.0, drv_sh=True, rear=1.0, tape=tape)
    if t >= 12.08:
        k = popin(t, 12.08, 0.3) * (1 + 0.02 * math.sin(t * 7))
        blit(fg, bubble_img("We'll fix it in post."), 500, 640, k, k, -2, anchor='center')
        fx.burst(fg, t, 12.08, 540, 640, GLOW, n=12, seed=40)
    if t >= TAPE:
        fx.sparkles(fg, t, 420, 860, 600, 300, n=8, seed=41); fx.dust(fg, t, TAPE, 420, 900, n=8, seed=42)
    if t >= 13.35:
        fx.stamp_at(fg, t, 13.35, 'IN POST?', 560, 830, rot=-8, s=8)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== new read: question (the ball in slow motion), body on the first read's timing, question
BODY = [p for p in kit.word_pairs(NEW, WORDS) if 7.7 < p[0] < BODY_END - 0.3]
ANCH = ([(0.0, -0.2), (Q_END, 0.95), (kit.at(NEW, '2019', 0), 1.81), (kit.at(NEW, 'reveal', 0), 2.6), (kit.at(NEW, 'the', 1), 3.41), (kit.at(NEW, 'chief', 0), 3.49),
          (kit.at(NEW, 'designer', 0), 3.78), (kit.at(NEW, 'did', 0), 4.23), (kit.at(NEW, 'that', 0), 5.45)] + BODY +
        [(BODY_END - 0.01, 13.3), (BODY_END, 6.6), (END_T + 0.2, 7.95)])
WARP, N = kit.warp(ANCH), kit.unwarp(ANCH[:-2])
shot_teaser, TEASE_CUES = kit.teaser(END_T, NEW)

# ================================================================== shots + transitions
SHOTS = [(-1.0, kit.retime(shot_reveal, WARP)), (N(3.3), kit.retime(shot_throw, WARP)), (N(6.2), kit.retime(shot_driver, WARP)),
         (N(8.0), kit.retime(shot_rear, WARP)), (N(10.3), kit.retime(shot_post, WARP)), (BODY_END, kit.retime(shot_driver, WARP)), (END_T, shot_teaser)]
TRANS = {1: (N(3.3), N(3.3) + 0.2, 'whip', dict(dx=1)), 2: (N(6.2), N(6.2) + 0.2, 'iris', (800, 900)), 3: (N(8.0), N(8.0) + 0.2, 'push', None),
         4: (N(10.3), N(10.3) + 0.2, 'whip', dict(dx=0, dy=1)), 5: (BODY_END, BODY_END + 0.2, 'iris', (540, 900)), 6: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'throw': YEL, 'cybertruck?': RED, '2019': YEL, 'designer': YEL, 'exactly': YEL, "driver's": YEL, 'shattered.': RED, 'rear': RED, 'too.': RED,
          'response:': YEL, 'post.': RED, 'trusted': YEL}
CUES = [
    (0.0, 'whoosh', 0.9), (0.05, 'pop', 0.5), (0.3, 'pop', 0.5), (0.85, 'thump', 0.6), (1.1, 'click', 0.5), (1.17, 'ding', 0.6), (1.81, 'pop', 0.6),
    (1.85, 'stamp', 0.4), (2.35, 'pop', 0.5),
    (3.35, 'pop', 0.5), (3.6, 'pop', 0.5), (THROW, 'whoosh', 0.8), (4.49, 'pop', 0.5), (HIT, 'thump', 0.9), (HIT + 0.02, 'crash', 0.3),
    (6.42, 'creak', 0.5), (SHAT, 'crash', 1.0), (SHAT + 0.02, 'boom', 0.4), (SHAT + 0.05, 'sparkle', 0.9), (SHAT + 0.08, 'stamp', 0.6),
    (8.6, 'whoosh', 0.7), (HIT2, 'crash', 0.9), (HIT2 + 0.05, 'sparkle', 0.7), (9.72, 'pop', 0.6),
    (10.6, 'thump', 0.4), (11.23, 'slide_down', 0.4), (12.08, 'pop', 0.8), (TAPE, 'stamp', 0.7), (TAPE + 0.05, 'sparkle', 0.7), (13.35, 'stamp', 0.8),
]
CUES = kit.warp_cues(CUES, ANCH, END_T) + TEASE_CUES

kit.setup(HERE, NEW, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True,
          end=('car stuff, explained', 'tell me in the comments'))

if __name__ == '__main__':
    kit.main()
