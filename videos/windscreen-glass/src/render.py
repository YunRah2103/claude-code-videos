"""Renders 'car stuff, explained': why a windscreen cracks instead of shattering (14 s, loops). V2: longer read, no
held pauses, five shots.

Shots (timed to words.json, faster-whisper on out/windscreen-glass/voiceover.wav):
  1 drive   0.00  driver's view at night: road dashes and street lights rushing at us, a stone hits on frame 0, the crack starts
  2 layers  ~2.0  exploded cutaway: GLASS flies in, PLASTIC slides in, GLASS rises, they press together on 'middle'
  3 hit     ~4.2  a stone hits the cutaway: the crack stops at the plastic, the broken top glass rattles but stays stuck
  4 web     ~8.1  back on the road: the crack spreads into a spiderweb, the wipers sweep, the screen stays in one piece
  5 ask     ~10.8 garage: presenter asks, poll 'Would you have guessed that? YES / NO'; whips back to shot 1 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]
"""
import math, os, sys, random
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'assets'))
import episode as kit
from episode import W, H, RED, YEL, WHITE
from backdrops.garage import Garage
from pixanim.motion import prog, lerp, io, oc, ob
from pixanim.presenter import Presenter, Fn
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR, END_T = 14.0, 13.62
T2 = ws(6) - 0.15                                                   # 'glass'
L1, L2, L3, PRESS = T2 + 0.05, ws(8) - 0.05, ws(9) - 0.05, ws(11)  # glass, plastic, glass, pressed on 'middle'
T3 = ws(12) - 0.15                                                  # 'When a stone hits'
HIT, CAUGHT, HOLD = ws(15), ws(17), ws(18)                          # 'hits', 'plastic', 'holds'
T4 = ws(23) - 0.15                                                  # "That's why it cracks instead of shattering"
SPREAD, NOSHAT = ws(26), ws(29)
T5 = ws(30) - 0.2                                                   # 'Would you have guessed that?'
G = Garage(W, H, 1520, 9)
HOOK = ((('Your windscreen has', None),), (('PLASTIC', '#ffd93b'), ('in the middle', None)))
KEYCOL = {'windscreen': YEL, 'plastic': YEL, 'stone': YEL, 'holds': YEL, 'together': YEL, 'cracks': RED, 'shattering': RED,
          'guessed': YEL}


# ------------------------------------------------------------------ the road seen through the windscreen (216x384 grid, 5x)
VP = (108, 150)                                                     # vanishing point (grid)


@lru_cache(1)
def _skyline():
    img = Image.new('RGBA', (216, 384), (0, 0, 0, 0)); d = ImageDraw.Draw(img); rnd = random.Random(3)
    for y in range(0, VP[1] + 1):                                   # night sky gradient
        k = y / VP[1]; d.line((0, y, 216, y), fill=(int(18 + 22 * k), int(22 + 22 * k), int(40 + 34 * k)))
    x = 0
    while x < 216:                                                  # city blocks on the horizon, a few lit windows
        bw, bh = rnd.randint(8, 18), rnd.randint(8, 30)
        d.rectangle((x, VP[1] - bh, x + bw, VP[1]), fill=(28, 30, 44))
        for _ in range(bw * bh // 30):
            d.point((x + rnd.randint(1, bw - 1), VP[1] - rnd.randint(2, bh - 1)), fill=(255, 214, 120) if rnd.random() < 0.7 else (140, 200, 255))
        x += bw + rnd.randint(0, 3)
    d.point((40, 30), fill=(240, 240, 250)); d.ellipse((168, 20, 178, 30), fill=(236, 236, 220)); d.ellipse((171, 19, 181, 29), fill=(26, 30, 50))
    return img


def road(t):
    img = _skyline().copy(); d = ImageDraw.Draw(img); y1 = 236
    d.polygon([(VP[0] - 3, VP[1]), (VP[0] + 3, VP[1]), (250, y1), (-34, y1)], fill=(42, 44, 52))
    d.line((VP[0] - 3, VP[1], -34, y1), fill=(200, 200, 190)); d.line((VP[0] + 3, VP[1], 250, y1), fill=(200, 200, 190))
    for k in range(7):                                              # centre dashes rushing towards us
        z = ((k + t * 4.6) % 7) / 7; z2 = min(1, z + 0.06)
        ya, yb = VP[1] + (y1 - VP[1]) * z ** 2, VP[1] + (y1 - VP[1]) * z2 ** 2
        wa, wb = 0.5 + 4 * z ** 2, 0.5 + 4 * z2 ** 2
        d.polygon([(VP[0] - wa, ya), (VP[0] + wa, ya), (VP[0] + wb, yb), (VP[0] - wb, yb)], fill=(255, 214, 90))
    for k in range(4):                                              # street lights sweeping past both sides
        z = ((k + t * 2.4) % 4) / 4; sx = 1 + 150 * z ** 2; y = VP[1] + (y1 - VP[1]) * z ** 2
        for side in (-1, 1):
            x = VP[0] + side * (6 + sx); top = y - (6 + 120 * z ** 2)
            d.line((x, y, x, top), fill=(70, 74, 86), width=max(1, int(3 * z)))
            r = 1 + 4 * z; d.ellipse((x - r, top - r, x + r, top + r), fill=(255, 226, 150))
    z = ((t + 0.6) * 0.55) % 1                                       # an oncoming car's headlights, growing as it nears
    x, y = VP[0] - 4 - 40 * z ** 2, VP[1] + (y1 - VP[1]) * z ** 2 - 2; r = 1 + 6 * z ** 2
    for dx in (-r * 1.6, r * 1.6):
        d.ellipse((x + dx - r * 1.8, y - r * 1.2, x + dx + r * 1.8, y + r * 1.2), fill=(255, 250, 220, int(70 * z)))
        d.ellipse((x + dx - r, y - r * 0.6, x + dx + r, y + r * 0.6), fill=(255, 252, 235))
    d.rectangle((0, y1, 216, 384), fill=(16, 17, 21))
    return img.resize((W, H), Image.NEAREST)


WS_S, WS_C = 9, (540, 860)
WS_TOP = WS_C[1] - 38 * WS_S
CHIP = (WS_C[0] - 60 * WS_S + 76 * WS_S + 4, WS_TOP + 40 * WS_S + 4)
STONE = Image.new('RGBA', (5, 5), (0, 0, 0, 0)); ImageDraw.Draw(STONE).ellipse((0, 0, 4, 4), fill=(150, 146, 140), outline=(60, 58, 56))


def cabin(fg, t):
    """Dashboard top under the windscreen and the rim of the steering wheel."""
    d = ImageDraw.Draw(fg)
    d.polygon([(0, 1150), (1080, 1150), (1080, 1920), (0, 1920)], fill=(32, 33, 39)); d.line((0, 1152, 1080, 1152), fill=(62, 64, 74), width=9)
    for r, col in ((380, (20, 21, 26)), (340, (46, 48, 56)), (300, (20, 21, 26))):
        d.ellipse((260 - r, 1560 - r, 260 + r, 1560 + r), outline=col, width=36 if r != 340 else 18)


def drive_view(t, crack, wiper=0.0, stone_t=None):
    img = road(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(cb.windscreen(crack, t=t, clear=True, wiper=wiper), WS_S), WS_C[0], WS_C[1], anchor='center')
    if stone_t is not None and stone_t - 0.45 <= t < stone_t:       # the stone, flicked up by a car ahead, grows as it nears
        u = prog(t, stone_t - 0.45, 0.45)
        fx.blit(fg, up(STONE, max(2, round(2 + 14 * u ** 2))), lerp(VP[0] * 5 + 40, CHIP[0], u), lerp(VP[1] * 5 + 10, CHIP[1], u), anchor='center')
    if stone_t is not None and t >= stone_t:
        fx.burst(fg, t, stone_t, *CHIP, (236, 244, 252), n=12, r0=40, r1=260); fx.ring(fg, t, stone_t, *CHIP, (255, 255, 255), life=0.35, r1=280)
    cabin(fg, t)
    img.alpha_composite(fg)
    return img


# ------------------------------------------------------------------ shot 1: the stone hits
P1 = Presenter([(-9, dict(path=Fn(lambda t: (850, 1350)), size=7, legs='stand', arms='point', point=CHIP, expr='shock',
                          ground=1350, look=CHIP)),
                (ws(1), dict(arms='flail', squash=True)),
                (ws(4), dict(arms='point', expr='smile'))], words=WORDS)


STONE_T = 0.3                                                       # a tiny chip crack is already there on frame 0
def crack1(t): return 0.08 + 0.92 * oc(prog(t, STONE_T, 1.6))


def shot_drive(t):
    img = drive_view(t, crack1(t), 0.5 - 0.5 * math.cos((t + 0.6) * 4.4), stone_t=STONE_T)   # wipers on: the driver jumps
    gx = lerp(-400, 1500, ((t + 0.5) * 0.8) % 1)                       # street-light glare sliding over the glass
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).polygon([(gx, 600), (gx + 160, 600), (gx - 40, 1110), (gx - 200, 1110)], fill=(255, 240, 210, 60))
    img.alpha_composite(gl); P1.draw(img, t)
    z = lerp(1.55, 1.08, oc(prog(t, -0.5, 1.5))); sh = 8 + (26 * math.exp(-(t - STONE_T) * 4) if t >= STONE_T else 0)
    bump = 16 * math.sin(t * 17) * math.sin(t * 5.3)                  # road bumps
    return D.camera(img.convert('RGB'), t, z, CHIP[0] - 80, CHIP[1] + 40 + bump, sh)


# ------------------------------------------------------------------ shots 2 + 3: the cutaway
LS, LC, LH, LW = 6, (600, 760), (20, 12, 20), 110
TOP = LC[1] - (sum(LH) + 4) * LS // 2
X0 = LC[0] - (LW + 4) * LS // 2
def band_y(i): return TOP + (2 + sum(LH[:i])) * LS            # pressed position (top edge) of layer i
def layer_mid(i, t): return band_y(i) + LH[i] * LS / 2 + layer_off(i, t)[1]


def layer_off(i, t):
    """(dx, dy) of layer i: flies in on its word, spread apart until 'middle', then pressed together."""
    spread = 16 * LS * (1 - io(prog(t, PRESS, 0.22))) * (i - 1)
    k = oc(prog(t, (L1, L2, L3)[i], 0.32))
    fly = ((0, -700), (900, 0), (0, 700))[i]
    return fly[0] * (1 - k), fly[1] * (1 - k) + spread


def cutaway(fg, t, crack=0.0, stop=0.0, shards=0.0, build=True):
    full = cb.glass_layers(crack, stop, t, LW, LH, shards=shards)
    ImageDraw.Draw(fg).rounded_rectangle((30, TOP - 150, 1050, TOP + full.height * LS + 150), 36, fill=(18, 20, 28, 235),
                                         outline=(90, 96, 112, 255), width=8)          # diagram card
    for i in range(3):
        if build and t < (L1, L2, L3)[i]: continue
        dx, dy = layer_off(i, t) if build else (0, 0)
        y0 = 2 + sum(LH[:i]); top = 0 if i == 0 else y0; bot = y0 + LH[i] + (2 if i == 2 else 0)
        fg.alpha_composite(up(full.crop((0, top, full.width, bot)), LS), (int(X0 + dx), int(TOP + top * LS + dy)))
    if build and t >= PRESS:
        fx.ring(fg, t, PRESS, LC[0], band_y(1) + LH[1] * LS // 2, (255, 210, 63), life=0.4, r1=420)
        fx.sparkles(fg, t, LC[0], band_y(1), 640, 300, n=6, seed=21)


P2 = Presenter([(-9, dict(path=Fn(lambda t: (190, 1660)), size=6, legs='stand', arms='point', point=(X0 + 60, LC[1]), expr='smile',
                          ground=None, squash=True)),
                (PRESS, dict(arms='cheer', expr='grin', squash=True)),
                (T3, dict(arms='point', expr='smile')),
                (HIT, dict(arms='shock', expr='shock', squash=True)),
                (HOLD, dict(arms='cheer', expr='grin', squash=True))], words=WORDS)


def shot_layers(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    cutaway(fg, t)
    img.alpha_composite(G.rim(fg)); P2.draw(img, t)
    for i, (txt, body, shade) in enumerate((('GLASS', '#ffffff', '#d6d9e2'), ('PLASTIC', '#ffd23f', '#e8b923'), ('GLASS', '#ffffff', '#d6d9e2'))):
        t0 = (L1, L2, L3)[i] + 0.2
        cb.pill(img, t, t0, T3 - 0.1, txt, lambda t, i=i: (X0 + 70 + layer_off(i, t)[0], layer_mid(i, t)),
                lambda t, i=i: (150, layer_mid(i, t) + (i - 1) * 30), body, '#1a1a2e', shade, s=5)
    z = lerp(1.18, 1.05, oc(prog(t, T2, 0.6))) + (0.05 * math.exp(-(t - PRESS) * 6) if t >= PRESS else 0)
    return D.camera(img.convert('RGB'), t, z, 560, 800, 4 + (14 * math.exp(-(t - PRESS) * 6) if t >= PRESS else 0))


def shot_hit(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    crack, stop = oc(prog(t, HIT, 0.45)), oc(prog(t, CAUGHT - 0.1, 0.5))
    shards = (1.0 if t < T4 - 0.3 else 0.0) if t >= HOLD else 0.0
    cutaway(fg, t, crack, stop, shards, build=False)
    u = prog(t, HIT - 0.4, 0.4)                                              # the stone flies in and hits the top glass
    if t < HIT: fx.blit(fg, up(STONE, 10), lerp(1000, LC[0] + 6, u), lerp(260, TOP + 12, u ** 1.4), anchor='center')
    else: fx.burst(fg, t, HIT, LC[0], TOP + 20, (236, 244, 252), n=12, r0=60, r1=260)
    if t >= CAUGHT - 0.1: fx.ring(fg, t, CAUGHT - 0.1, LC[0], band_y(1) + LH[1] * LS // 2, (255, 210, 63), life=0.45, r1=340)
    if t >= HOLD:                                                            # the plastic pulls the pieces back: little up-arrows
        d = ImageDraw.Draw(fg); yb = band_y(1) - 4                          # arrows point from the pieces into the plastic
        for j in range(5):
            x = X0 + 120 + j * 120; bob = 8 * math.sin(t * 9 + j); tri = [(x - 20, yb - 34 + bob), (x + 20, yb - 34 + bob), (x, yb + bob)]
            d.polygon(tri, fill=(255, 255, 255, 235), outline=(26, 26, 46)); d.line((x, yb - 70 + bob, x, yb - 34 + bob), fill=(26, 26, 46), width=12)
            d.line((x, yb - 70 + bob, x, yb - 34 + bob), fill=(255, 255, 255), width=6)
    img.alpha_composite(G.rim(fg)); P2.draw(img, t)
    cb.pill(img, t, CAUGHT, T4 - 0.1, 'PLASTIC', (X0 + 70, band_y(1) + LH[1] * LS // 2), (150, band_y(1) + 40), '#ffd23f', '#1a1a2e', '#e8b923', s=5)
    cb.pill(img, t, ws(20) - 0.05, T4 - 0.1, 'PIECES STAY PUT', (LC[0] - 40, TOP + 40), (470, 470), '#5adc78', '#1a1a2e', '#2f9a4c')
    z = lerp(1.12, 1.05, oc(prog(t, T3, 0.6))) + (0.06 * math.exp(-(t - HIT) * 6) if t >= HIT else 0)
    return D.camera(img.convert('RGB'), t, z, 560, 800, 4 + (18 * math.exp(-(t - HIT) * 5) if t >= HIT else 0))


# ------------------------------------------------------------------ shot 4: the spiderweb that stays in one piece
P4 = Presenter([(-9, dict(path=Fn(lambda t: (850, 1350)), size=7, legs='stand', arms='point', point=CHIP, expr='smile', ground=1350,
                          look=CHIP)),
                (NOSHAT, dict(arms='cheer', expr='grin', squash=True, look_camera=True))], words=WORDS)


def shot_web(t):
    crack = 1.0 + io(prog(t, SPREAD - 0.1, 1.2))
    wiper = 0.5 - 0.5 * math.cos(max(0, t - T4) * 4.2) if t < NOSHAT + 0.6 else 0
    img = drive_view(t, crack, wiper, stone_t=SPREAD - 0.1); P4.draw(img, t)
    cb.pill(img, t, NOSHAT, T5 - 0.1, "DOESN'T SHATTER", CHIP, (430, 470), '#5adc78', '#1a1a2e', '#2f9a4c')
    sh = 4 + (20 * math.exp(-(t - SPREAD) * 5) if t >= SPREAD else 0)
    return D.camera(img.convert('RGB'), t, lerp(1.2, 1.1, oc(prog(t, T4, 0.6))), CHIP[0] - 80, CHIP[1] + 40, sh)


# ------------------------------------------------------------------ shot 5: the question
P5 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (300, 1600)), size=9, legs='stand', arms='shrug', expr='smile', ground=1600,
                          look_camera=True, squash=True)),
                (ws(33), dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(cb.windscreen(2.0, t=t), 3), 790, 1570 + 8 * math.sin(t * 2), anchor='bottom')
    fx.sparkles(fg, t, 790, 1460, 360, 200, n=4, seed=41)
    img.alpha_composite(G.rim(fg)); P5.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T5, 0.6))), 540, 1300, 5)


SCENE = D.sequence([(-9, shot_drive), (T2, shot_layers), (T3, shot_hit), (T4, shot_web), (T5, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.2, HOOK, y=440)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.2, HOOK, y=440)
    ov.poll(cv, t, T5 + 0.1, END_T - 0.1, 'Would you have guessed that?', ov.SAFE_CX, 640, 0.9)


CUES = [(STONE_T, 'glass_crack', 1.0), (STONE_T, 'thump', 0.4), (0.05, 'whoosh', 0.5), (0.7, 'glass_crack', 0.4),
        (L1, 'whoosh', 0.5), (L1 + 0.2, 'pop', 0.6), (L2, 'whoosh', 0.5), (L2 + 0.2, 'pop', 0.7), (L3, 'whoosh', 0.5), (L3 + 0.2, 'pop', 0.6),
        (PRESS, 'stamp', 0.8), (PRESS + 0.02, 'sparkle', 0.6),
        (HIT - 0.4, 'whoosh', 0.5), (HIT, 'glass_crack', 1.0), (HIT + 0.02, 'thump', 0.5), (CAUGHT, 'ding', 0.7), (CAUGHT + 0.05, 'pop', 0.6),
        (HOLD, 'snap', 0.5), (HOLD + 0.2, 'snap', 0.4), (ws(20) - 0.05, 'pop', 0.7), (ws(20), 'sparkle', 0.5),
        (SPREAD - 0.1, 'glass_crack', 0.9), (SPREAD + 0.3, 'glass_crack', 0.5), (T4 + 0.1, 'creak', 0.3),
        (NOSHAT, 'pop', 0.7), (NOSHAT + 0.02, 'sparkle', 0.7), (T5 + 0.1, 'pop', 0.8), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4, T5], CUES, KEYCOL, overlay, cap=(T2, 1100))

if __name__ == '__main__':
    D.cli()
