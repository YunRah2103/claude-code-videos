"""Renders 'The car named after a son': the Ferrari Dino and Alfredo 'Dino' Ferrari.

Template: videos/tractors-vs-ferraris (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). Speech runs 0-17.0 s; the 'Follow' card holds to 18.9 s.
The car is a generic pixel car; the 'DINO' badge is plain pixel lettering, no real logo.
Shot 3 is deliberately quiet: no presenter, sparkles, camera punches or sound effects while his death is mentioned.
Shots:
  1 hook     0.00  a dark garage; a DINO badge fades in, slow push-in; 'The name had a face.'
  2 sketch   3.40  a sketchbook: a V6 diagram draws itself; V6 label on 'V6'; engine photo on 'engine'
  3 quiet    7.00  dim garage, one empty chair in a soft light; slow drift only
  4 car     11.30  a car rolls out of the dark into the light on 'Dino'; 1968 tag; the badge flies onto it on 'name'
  5 badge   14.40  close on the badge; glint on 'badge'
  6 teaser  17.10  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, draw_car, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid

WORDS = kit.load_words(HERE)
DUR, END_T = 18.9, 17.6


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def badge():
    """Generic oval name badge (48x20): bevelled two-tone gold rim, deep enamel with a soft gradient, DINO in raised
    gold capitals with a drop shadow. Plain lettering, no real logo."""
    w, h = 48, 20
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 9, fill=(176, 128, 20))                     # dark gold base
    d.rounded_rectangle((0, 0, w - 1, h - 3), 9, fill=(232, 185, 35))                     # gold rim
    d.rounded_rectangle((1, 1, w - 2, 5), 4, fill=(255, 226, 120))                        # top bevel highlight
    d.rounded_rectangle((3, 3, w - 4, h - 5), 6, fill=(20, 28, 70))                       # enamel
    for y in range(4, h - 5):
        c = (24 + y * 2, 36 + y * 3, 92 + y * 5)
        d.line([(5 if y in (4, h - 6) else 4, y), (w - 6 if y in (4, h - 6) else w - 5, y)], fill=c)
    d.line([(8, 4), (w - 9, 4)], fill=(90, 120, 200))                                     # enamel gloss line
    g = Grid(26, 9); g.text(1, 1, 'DINO', '#7a5a10'); sh = g.image(outline=False)
    g = Grid(26, 9); g.text(1, 1, 'DINO', '#ffd23f'); fg = g.image(outline=False)
    img.alpha_composite(sh, (12, 6)); img.alpha_composite(fg, (11, 5))
    for x in range(12, 36):                                                                # top-light on the letters
        for y in range(5, 14):
            r, gg, b, a = img.getpixel((x, y))
            if a and (r, gg, b) == (255, 210, 63) and img.getpixel((x, y - 1))[:3] != (255, 210, 63): img.putpixel((x, y), (255, 244, 170, 255))
    for x in (6, w - 7): d.rectangle((x, 9, x + 1, 10), fill=(232, 185, 35))              # side studs
    return outline(img)


def shine(img, u, width=0.18):
    """Diagonal light sweep across a sprite: u 0..1 moves the band from left to right."""
    if not 0 < u < 1: return img
    w, h = img.size
    band = Image.new('L', (w, h), 0); d = ImageDraw.Draw(band)
    x = -0.3 * w + 1.6 * w * u
    d.polygon([(x, 0), (x + width * w, 0), (x + width * w - 0.4 * h, h), (x - 0.4 * h, h)], fill=150)
    m = Image.composite(band, Image.new('L', (w, h), 0), img.getchannel('A'))
    out = img.copy(); out.alpha_composite(Image.merge('RGBA', (*[Image.new('L', (w, h), 255)] * 3, m)))
    return out


@lru_cache(None)
def sketch(level=100):
    """Open sketchbook (110x72): a V6 drawn in blue ink on the left page, notes on the right; level = % revealed."""
    img = Image.new('RGBA', (110, 72), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 2, 109, 71), fill=(120, 84, 56)); d.rectangle((2, 0, 107, 68), fill=(248, 244, 228))
    d.line([(55, 0), (55, 68)], fill=(214, 206, 186))
    for y in range(4, 68, 6): d.ellipse((53, y, 57, y + 3), outline=(110, 114, 124))
    for y in range(10, 66, 6): d.line([(60, y), (104, y)], fill=(222, 228, 240))
    ink, lt = (40, 70, 160), (120, 150, 210)
    ink_img = Image.new('RGBA', img.size, (0, 0, 0, 0)); k = ImageDraw.Draw(ink_img)
    cx, cy = 28, 54                                                            # front view of the V: crank, two banks
    k.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), outline=ink); k.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=ink)
    for sgn in (-1, 1):
        a = math.radians(90 + sgn * 32)
        bx, by = cx - 30 * math.cos(a), cy - 30 * math.sin(a)
        px, py = -math.sin(a) * 7, math.cos(a) * 7
        k.polygon([(cx - 8 * math.cos(a) + px, cy - 8 * math.sin(a) + py), (bx + px, by + py), (bx - px, by - py),
                   (cx - 8 * math.cos(a) - px, cy - 8 * math.sin(a) - py)], outline=ink)
        pp = 18 + 3 * sgn
        k.rectangle((cx - pp * math.cos(a) - 4, cy - pp * math.sin(a) - 3, cx - pp * math.cos(a) + 4, cy - pp * math.sin(a) + 3), fill=lt)
        k.line([(cx, cy), (cx - pp * math.cos(a), cy - pp * math.sin(a))], fill=ink)
    for i in range(3):                                                          # plan view: three cylinders per bank
        for j, x0 in enumerate((8, 34)):
            k.ellipse((x0 + i * 6, 8 + j * 3, x0 + i * 6 + 4, 12 + j * 3), outline=ink)
    k.line([(8, 20), (48, 20)], fill=lt)
    for x, y, w in ((62, 8, 24), (62, 14, 36), (62, 20, 30), (62, 32, 38), (62, 38, 20), (62, 50, 32)):
        k.line([(x, y), (x + w, y)], fill=lt)                                   # handwriting squiggles
        for xx in range(x, x + w, 3): k.point((xx, y - 1), fill=lt)
    g = Grid(20, 9); g.text(1, 1, 'V6', '#2846a0'); v6 = g.image(outline=False)
    ink_img.alpha_composite(v6, (82, 22))
    m = Image.new('L', img.size, 0); ImageDraw.Draw(m).rectangle((0, 0, int(110 * level / 100), 72), fill=255)
    img.paste(ink_img, (0, 0), Image.composite(ink_img.getchannel('A'), Image.new('L', img.size, 0), m))
    return outline(img)


@lru_cache(None)
def pencil():
    img = Image.new('RGBA', (6, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((1, 0, 4, 19), fill=(255, 196, 40)); d.rectangle((1, 0, 4, 2), fill=(232, 120, 140))
    d.polygon([(1, 20), (4, 20), (2.5, 25)], fill=(240, 214, 170)); d.point((2, 25), fill=(40, 42, 48))
    return outline(img)


@lru_cache(None)
def chair():
    """Plain wooden workshop chair (22x36)."""
    img = Image.new('RGBA', (22, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    wood, dark, hi = (150, 104, 66), (110, 72, 44), (190, 140, 96)
    d.rectangle((3, 0, 5, 35), fill=dark); d.rectangle((3, 0, 18, 3), fill=wood); d.rectangle((3, 6, 18, 8), fill=wood)
    d.rectangle((2, 18, 20, 21), fill=wood); d.line([(2, 18), (20, 18)], fill=hi)
    d.rectangle((17, 18, 19, 35), fill=dark); d.rectangle((6, 22, 7, 35), fill=wood); d.rectangle((14, 22, 15, 35), fill=wood)
    d.line([(4, 28), (18, 28)], fill=dark)
    return outline(img)


@lru_cache(None)
def dim_base():
    """The garage set, darkened: the frame used for the quiet shot (static base, the light cone is added per frame)."""
    return Image.blend(GAR.frame(0.0), Image.new('RGB', (W, H), (6, 6, 9)), 0.72).convert('RGBA')


@lru_cache(None)
def cone():
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.polygon([(470, 0), (610, 0), (860, GROUND + 40), (220, GROUND + 40)], fill=(255, 236, 190, 46))
    d.ellipse((240, GROUND - 40, 840, GROUND + 70), fill=(255, 236, 190, 60))
    return c.filter(ImageFilter.GaussianBlur(30))


# ================================================================== shot 1: hook, the badge in the dark
BX, BY = 540, 860
CAM1 = Camera(W, H, [(-1.0, (540, 860, 1.0)), (0.0, (540, 860, 1.0)), (3.4, (540, 860, 1.32), 'io')], kicks=[(0.76, 0.14, BX, BY), (2.16, 0.06, BX, BY), (2.87, 0.08, BX, BY)],
              shakes=[(0.76, 0.2, 8)])
P1 = Presenter([
    (1.8, dict(path=Track([(1.8, (-200, 600)), (2.16, (170, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (2.16, dict(ground=GROUND, squash=True, arms='point', point=(BX, BY), look=(BX, BY), expr='smile', face=None)),
], words=WORDS, base_size=7)


def shot_hook(t):
    img = dim_base().copy()
    if t >= 0.0:                                                                   # spotlight clunks on at frame 0
        c = cone().copy(); c.putalpha(c.getchannel('A').point(lambda v: int(v * (1.6 + 0.2 * math.sin(t * 3))))); img.alpha_composite(c)
    fg = layer()
    a = oc(prog(t, 0.0, 0.7))
    fx.rays(fg, t, 0.76, BX, BY, GLOW, life=1.4, r=560)
    k = lerp(1.35, 1.0, oc(prog(t, 0.0, 0.7))) * (1 + 0.06 * popin(t, 0.76, 0.3) * popout(t, 1.05))
    b = shine(up(badge(), 15), prog(t, 0.8, 0.7)).copy() if t >= 0 else up(badge(), 15).copy()
    b.putalpha(b.getchannel('A').point(lambda v: int(v * a)))
    blit(fg, b, BX, BY + 10 * math.sin(t * 2), k, k, 0, anchor='center')
    fx.ring(fg, t, 0.76, BX, BY, GLOW, life=0.45, r1=460)
    fx.burst(fg, t, 0.76, BX, BY, GLOW, n=14, r0=260, r1=520, seed=23)
    if t >= 0.76: fx.sparkles(fg, t, BX, BY, 720, 320, n=8, seed=21)
    for i in range(14):                                                            # dust motes in the beam
        u = (t * 0.08 + i * 0.07) % 1
        ImageDraw.Draw(fg).rectangle((440 + (i * 41) % 220, 160 + u * 1000, 446 + (i * 41) % 220, 166 + u * 1000), fill=(255, 240, 200, 80))
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.9, 'The name had a', WHITE, 470, 96, -2)
    title(cv, t, 0.35, 2.9, 'face.', RED, 590, 132, 3)


# ================================================================== shot 2: the sketchbook
SK = (540, 900)
def ink(t): return clamp((t - 3.5) / 2.0)
CAM2 = Camera(W, H, [(3.4, (540, 900, 1.02)), (5.72, (560, 880, 1.1), 'io'), (6.2, (540, 880, 1.04), 'io'), (7.0, (540, 880, 1.06))],
              kicks=[(3.99, 0.06, 540, 900), (5.72, 0.14, 860, 760), (6.2, 0.08, 540, 560)])
P2 = Presenter([
    (3.35, dict(path=Track([(3.35, (1300, 400)), (3.75, (930, GROUND + 230), 'oc')]), size=6, legs='auto', arms='fly', expr='think', face=-1, ground=None)),
    (3.75, dict(ground=GROUND + 230, squash=True, arms='think', look=SK, expr='think', face=None)),
    (5.72, dict(arms='point', point=(860, 760), look=(860, 760), expr='wow', squash=True)),
], words=WORDS, base_size=6)


def shot_sketch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    d.rectangle((0, GROUND - 60, W, GROUND + 260), fill=(96, 68, 46)); d.rectangle((0, GROUND - 60, W, GROUND - 48), fill=(130, 94, 64))
    lv = int(ink(t) * 100) // 4 * 4
    k = popin(t, 3.45, 0.3)
    blit(fg, up(sketch(lv), 8), SK[0], SK[1] + 250, k, k, -2, anchor='bottom')
    if 3.5 <= t < 5.6:                                                         # the pencil rides the reveal edge
        px = SK[0] - 440 + 880 * ink(t)
        blit(fg, up(pencil(), 9), px + 30, SK[1] - 60 + 120 * math.sin(t * 9), 1, 1, -25)
    dg.label(fg, t, 5.72, 'EARLY V6', (820, 700), (700, 480), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    fx.sparkles(fg, t, 860, 700, 300, 200, n=6, seed=22) if t > 5.72 else None
    P2.draw(fg, t)
    photo(fg, t, 6.2, 6.95, 'dino_engine', 540, 560, 560, 420, -3, 'A DINO V6 ENGINE', focus=(0.5, 0.5), zoom=0.1)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the quiet chair (no punches, no sparkles)
CAM3 = Camera(W, H, [(7.0, (540, 980, 1.08)), (11.3, (540, 1000, 1.24), 'io')])


def shot_quiet(t):
    img = dim_base().copy()
    breathe = 0.85 + 0.15 * math.sin(t * 1.6)
    c = cone().copy(); c.putalpha(c.getchannel('A').point(lambda v: int(v * breathe))); img.alpha_composite(c)
    fg = layer()
    fx.contact_shadow(fg, 540, GROUND, 260, s=S, alpha=110)
    blit(fg, up(chair(), 9), 540, GROUND)
    for i, (txt, t0) in enumerate((('1956', 7.6), ('24', 9.01))):           # soft fade-ins, no pop
        a = clamp((t - t0) / 0.6)
        if a > 0:
            im = fx.big('label', txt, '#e8e4dc', s=10).copy()
            im.putalpha(im.getchannel('A').point(lambda v: int(v * a * 0.9)))
            blit(fg, im, 540, 470 + 150 * i, 1, 1, 0, anchor='center')
    for k in range(10):                                                         # dust drifting in the light
        u = (t * 0.06 + k * 0.1) % 1
        ImageDraw.Draw(fg).rectangle((440 + (k * 37) % 220, 300 + u * 800, 445 + (k * 37) % 220, 305 + u * 800), fill=(255, 240, 200, 70))
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t, rim=False)


# ================================================================== shot 4: the car rolls into the light
CAR4 = 500
def car_x(t): return lerp(-500, CAR4, oc(prog(t, 11.35, 0.75)))
def light4(t): return 0.25 + 0.75 * oc(prog(t, 11.45, 0.6))
P4 = Presenter([
    (11.75, dict(path=Track([(11.75, (1300, 300)), (12.1, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (12.1, dict(ground=GROUND, squash=True, arms='present', look=(CAR4, 1000), expr='smile', face=None)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(11.3, (540, 960, 1.15)), (12.3, (560, 960, 1.15), 'io'), (13.47, (540, 940, 1.22), 'io'), (14.4, (540, 940, 1.24))],
              kicks=[(12.1, 0.08, CAR4, 1000), (12.46, 0.1, 760, 640), (13.99, 0.12, CAR4 + 60, GROUND - 120)])


def shot_car(t):
    img = Image.blend(GAR.frame(t), Image.new('RGB', (W, H), (6, 6, 9)), 0.72 * (1 - light4(t))).convert('RGBA')
    fg = layer()
    x = car_x(t)
    fx.rays(fg, t, 11.9, CAR4, GROUND - 200, GLOW, life=0.9, r=420)
    fx.contact_shadow(fg, x, GROUND, 620, s=S, alpha=140)
    sr, sv = wob(t, (12.1,), 0.06)
    draw_car(fg, 'red', x, 8, dist=x + 500, lights=True, sx=sr, sy=sv)
    if t >= 12.46:
        k = popin(t, 12.46, 0.25) * popout(t, 13.4)
        blit(fg, fx.big('badge', '1968', '#7fe3a0', '#1a1a2e', '#3cc85a', s=11), 760, 640, k, k, -5 + 3 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 12.46, 760, 640, (90, 220, 120), seed=40)
    if t >= 13.47:                                                             # the badge flies onto the car's flank
        u = io(prog(t, 13.47, 0.5)); bx, by = lerp(540, CAR4 + 60, u), lerp(420, GROUND - 120, u); sc = lerp(9, 3, u)
        blit(fg, up(badge(), max(3, int(round(sc)))), bx, by, 1, 1, 0, anchor='center')
        fx.glint(fg, t, 13.99, CAR4 + 60, GROUND - 120, r=120)
        fx.ring(fg, t, 13.99, CAR4 + 60, GROUND - 120, (90, 220, 120), life=0.35, r1=220)
    if t >= 13.99: fx.sparkles(fg, t, CAR4, GROUND - 200, 600, 240, n=7, seed=41)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 12.75, 13.45, 'dino_246', 560, 560, 600, 420, 3, 'THE DINO ROAD CAR', focus=(0.5, 0.55), zoom=0.05)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: close on the badge
P5 = Presenter([
    (14.4, dict(path=Track([(14.4, (180, GROUND)), (14.5, (180, GROUND))]), size=8, legs='stand', arms='present', look=(600, 900), expr='smile', face=1, ground=GROUND)),
    (16.12, dict(arms='thumb', look=None, look_camera=True, expr='smile')),
], words=WORDS, base_size=8)
BADGE_Y = GROUND + 160 - 17 * 16
CAM5 = Camera(W, H, [(14.4, (600, 900, 1.05)), (17.1, (600, 900, 1.2), 'io')], kicks=[(15.32, 0.06, 640, 840)])


def shot_badge(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 760, GROUND + 160, 1300, s=S, alpha=150)
    draw_car(fg, 'red', 760 - 30 * prog(t, 14.4, 2.7), 16, y=GROUND + 160, lights=True)     # the car fills the frame, drifting slowly
    blit(fg, shine(up(badge(), 8), prog(t, 15.2, 0.6)), 680 - 30 * prog(t, 14.4, 2.7), BADGE_Y, 1, 1, 0, anchor='center')
    fx.glint(fg, t, 15.32, 680, BADGE_Y, r=220, life=0.6)
    fx.sparkles(fg, t, 680, BADGE_Y, 500, 200, n=5, seed=50)
    dg.label(fg, t, 16.12, 'A STORY', (680, BADGE_Y - 90), (700, 420), '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(17.1, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.4, shot_sketch), (7.0, shot_quiet), (11.3, shot_car), (14.4, shot_badge), (17.1, shot_teaser)]
TRANS = {1: (3.4, 3.6, 'whip', dict(dx=-1)), 2: (7.0, 7.4, 'push', None), 3: (11.3, 11.6, 'push', None),
         4: (14.4, 14.6, 'iris', (CAR4 + 60, GROUND - 120)), 5: (17.1, 17.3, 'whip', dict(dx=1))}
KEYCOL = {'dino': YEL, 'son.': RED, 'son': RED, 'v6': YEL, '24': RED, '1956': RED, 'name': GRN, '1968': GRN, 'badge': YEL, 'story': YEL}
CUES = [
    (0.0, 'click', 0.9), (0.02, 'boom', 0.45), (0.05, 'stamp', 0.5), (0.76, 'ding', 0.8), (0.78, 'sparkle', 0.7), (0.9, 'sparkle', 0.4), (2.16, 'thump', 0.5),
    (3.45, 'pop', 0.6), (3.6, 'click', 0.4), (4.4, 'click', 0.4), (5.0, 'click', 0.4), (5.72, 'pop', 0.7), (5.74, 'sparkle', 0.5), (6.2, 'pop', 0.6),
    (11.4, 'vroom', 0.5), (12.1, 'thump', 0.5), (12.46, 'ding', 0.6), (12.75, 'pop', 0.5), (13.47, 'whoosh', 0.5), (13.99, 'stamp', 0.6),
    (14.0, 'sparkle', 0.6), (15.32, 'sparkle', 0.6), (16.12, 'pop', 0.5),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='red', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
