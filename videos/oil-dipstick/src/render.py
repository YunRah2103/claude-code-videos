"""Renders 'car stuff, explained' ep 1: the two marks on the oil dipstick (14 s, loops).

Shots (timed to words.json, faster-whisper on out/oil-dipstick/voiceover.wav):
  1 hold    0.00  engine bay behind; presenter already swinging a dipstick up on frame 0; headline TWO MARKS
  2 marks   T2    dipstick close-up: MIN / MAX glow + callouts; on 'top mark' the film rises to MAX and the mark flashes
  3 sump    T3    engine cutaway: oil rises past normal, crank froths, TOO MUCH = DAMAGE; on 'engine off' it stops, settles
  4 ask     T4    garage: presenter asks, poll 'Do you check yours? YES / NO'; whips back to shot 1 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]
"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'assets'))
import episode as kit
from episode import W, H, RED, YEL, WHITE
from backdrops.garage import Garage
from pixanim.motion import prog, lerp, io, oc
from pixanim.presenter import Presenter, Fn
from pixanim.engine import Engine, crank_angle, CAVITY
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb, garagebits as gb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']
def we(i): return WORDS[i]['e']

DUR, END_T = 14.0, 13.62
T2, T3, T4 = 2.3, ws(14) - 0.25, ws(33) - 0.6           # close-up, 'Too much', 'Do you check yours?'
TOP, OFF = ws(12), ws(29)                              # 'top' (mark), 'with the engine off'
G = Garage(W, H, 1520, 9)
ENG = Engine()
HOOK = ((('Your dipstick', None),), (('has', None), ('TWO MARKS', '#ffd23f')))
KEYCOL = {'both': YEL, 'top': RED, 'much': RED, 'little.': YEL, 'level': YEL, 'off.': YEL, 'yours?': YEL}


def pulse(t, rate=7.0): return 0.55 + 0.45 * math.sin(t * rate)


# ------------------------------------------------------------------ engine with an oil sump fill
SUMP_X, SUMP_Y0, SUMP_Y1 = (108, 176), 186, 210       # crankcase interior (engine grid)
LV_OK, LV_HIGH = 206, 193                              # oil surface rows: normal / overfilled (crank dunked)


def oil_engine(t, level, theta, firing=True, froth=0.0, shake=(0, 0)):
    g = ENG.frame(t, theta=theta, firing=firing, shake=shake, as_grid=True).copy()
    lay = Image.new('RGBA', g.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); px = g.load()
    for x in range(SUMP_X[0], SUMP_X[1] + 1):
        top = round(level + 1.2 * math.sin(x * 0.45 + t * 6) * (0.4 + froth))
        for y in range(max(top, SUMP_Y0), SUMP_Y1 + 1):
            c = px[x, y][:3]
            if c == CAVITY: d.point((x, y), fill=gb.OIL + (255,))
            elif abs(c[0] - c[2]) < 30 and c[0] > 90: d.point((x, y), fill=gb.OIL + (120,))   # steel parts seen through oil
        if SUMP_Y0 <= top <= SUMP_Y1 and px[x, top][:3] == CAVITY: d.point((x, top), fill=gb.OIL_HI + (255,))
    if froth > 0.05:                                    # crank whipping the oil into foam
        for k in range(int(26 * froth)):
            a = (k * 37 + t * 90) % 68; y = level - 1 - ((k * 13 + t * 40) % 6)
            d.point((SUMP_X[0] + a, y), fill=(255, 236, 190, 230))
    g.alpha_composite(lay)
    return up(g, 5).crop((0, 0, W, H))


# ------------------------------------------------------------------ shot 1: presenter holds the dipstick up
P1 = Presenter([(-9, dict(path=Fn(lambda t: (250, 1640)), size=7, legs='stand', arms=('aim', -58), expr='grin', ground=None,
                          look_camera=True, squash=True)),
                (ws(3) - 0.05, dict(arms=('aim', -70), expr='wow', squash=True))], words=WORDS)


def stick_swing(t): return 28 * math.sin(t * 7 + 1.2) * math.exp(-max(0, t) * 0.5) + 5 * math.sin(t * 2.3)


def shot_hold(t):
    img = oil_engine(t, LV_OK, crank_angle(t, [(0, 2.0)]), firing=True)
    dim = Image.new("RGBA", (W, H), (8, 10, 18, 40)); img.alpha_composite(dim)
    hx, hy = P1.hand(t)
    rays = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.rays(rays, t + 9, 0, hx, hy - 280, (255, 210, 63, 46), hold=True, r=620, n=10)   # slow translucent sunburst behind the stick
    img.alpha_composite(rays)
    P1.draw(img, t)
    dip = up(gb.dipstick(0.6, pulse(t, 9) * oc(prog(t, ws(3) - 0.1, 0.3))), 6).transpose(Image.ROTATE_180)  # handle in hand
    fx.blit(img, dip, hx + 4, hy + 40, 1, 1, stick_swing(t), anchor='bottom')
    if t > ws(3) - 0.1:
        fx.sparkles(img, t, hx + 10, hy - 300, 260, 340, n=9, seed=4)
    z = lerp(1.5, 1.04, oc(prog(t, -0.5, 1.4))); sh = 16 + 28 * math.exp(-max(0, t) * 1.6)
    return D.camera(img.convert('RGB'), t, z, 420, 1100, sh)


# ------------------------------------------------------------------ shot 2: dipstick close-up
DS = 16
STICK_Y = 900                                           # blade row on screen
TIP_X = 70
def mark_x(row): return TIP_X + (gb.DIP_H - 1 - row) * DS + DS / 2   # rotated stick: tip on the left, handle off right


def shot_marks(t):
    img = G.frame(t).convert('RGBA')
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lvl = lerp(0.55, 1.0, io(prog(t, TOP - 0.1, 0.5)))
    flash = 0.5 + 0.5 * math.sin(t * 16) if t > TOP else 0
    stick = up(gb.dipstick(lvl, pulse(t, 8)), DS).transpose(Image.ROTATE_270)  # tip left, handle right
    sx = TIP_X + (stick.width / 2); bob = 6 * math.sin(t * 2.2)
    fx.blit(fg, stick, sx, STICK_Y + bob, 1, 1, 0, anchor='center')
    if flash:
        ImageDraw.Draw(fg).rectangle((mark_x(gb.DIP_MAX) - 30, STICK_Y - 60, mark_x(gb.DIP_MAX) + 30, STICK_Y + 60),
                                     outline=RED + (int(220 * flash),), width=9)
    for row, col in ((gb.DIP_MAX, (232, 52, 63)), (gb.DIP_MIN, (60, 200, 90))):
        fx.ring(fg, (t - T2) % 0.8, 0, mark_x(row) - 5, STICK_Y + bob, col, life=0.55, r1=140)
    img.alpha_composite(G.rim(fg))
    cb.pill(img, t, T2 + 0.25, T3 - 0.1, 'MIN', (mark_x(gb.DIP_MIN) - 5, STICK_Y + bob - 55), (mark_x(gb.DIP_MIN) - 20, 620),
            '#3cc85a', '#ffffff', '#1f8a3a')
    cb.pill(img, t, T2 + 0.45, T3 - 0.1, 'MAX', (mark_x(gb.DIP_MAX) - 5, STICK_Y + bob - 55), (mark_x(gb.DIP_MAX) + 60, 620),
            '#e8343f', '#ffffff', '#a01c26')
    z = lerp(1.25, 1.06, oc(prog(t, T2, 0.6))) + 0.03 * oc(prog(t, TOP, 0.4))
    return D.camera(img.convert('RGB'), t, z, 560, 900, 5 + 6 * flash)


# ------------------------------------------------------------------ shot 3: overfilled sump
PROFILE = [(0, 2.5), (T3, 5.0), (OFF, 5.0), (OFF + 0.9, 0.0)]
P3 = Presenter([(-9, dict(visible=False, path=Fn(lambda t: (150, 1650)))),
                (T3 + 0.3, dict(visible=True, size=5, legs='stand', arms='point', point=(700, 1000), expr='smile', ground=None,
                                squash=True)),
                (ws(20) - 0.1, dict(arms='shock', expr='shock', squash=True)),       # 'bad'
                (OFF, dict(arms=('aim', 10), expr='grin', squash=True))], words=WORDS)


def level_tool(cv, t, k):
    """Spirit level on the floor: the bubble swings and settles in the middle (level ground)."""
    if k <= 0: return
    x0, y0, w = 330, 1290, 420
    d = ImageDraw.Draw(cv)
    d.rectangle((x0 - 9, y0 - 9, x0 + w + 9, y0 + 63), fill=(26, 26, 46)); d.rectangle((x0, y0, x0 + w, y0 + 54), fill=(255, 210, 63))
    d.rectangle((x0 + w / 2 - 90, y0 + 9, x0 + w / 2 + 90, y0 + 45), fill=(26, 26, 46))
    d.rectangle((x0 + w / 2 - 81, y0 + 18, x0 + w / 2 + 81, y0 + 36), fill=(170, 230, 120))
    off = 60 * math.cos((t - OFF) * 6) * math.exp(-(t - OFF) * 2.2)
    bx = x0 + w / 2 + off
    d.rectangle((bx - 27, y0 + 18, bx + 27, y0 + 36), fill=(235, 255, 220))
    for xx in (x0 + w / 2 - 36, x0 + w / 2 + 36): d.rectangle((xx - 3, y0 + 12, xx + 3, y0 + 42), fill=(26, 26, 46))


def shot_sump(t):
    rise = oc(prog(t, T3 + 0.1, 1.2)); calm = io(prog(t, OFF, 1.0))
    level = lerp(LV_OK, LV_HIGH, rise)
    hot = rise * (1 - calm)
    sh = (round(1.5 * hot * math.sin(t * 47)), 0)
    img = oil_engine(t, level, crank_angle(t, PROFILE), firing=t < OFF, froth=hot, shake=sh)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if hot > 0.02:
        fx.ring(fg, (t - T3) % 0.5, 0, 710, 1000, (255, 120, 60), life=0.4, r1=220)
    level_tool(fg, t, prog(t, OFF - 0.2, 0.3))
    img.alpha_composite(fg)
    if t >= OFF:                                           # engine off: green tick pops beside the level
        k = fx.popin(t, OFF + 0.6, 0.3); fx.blit(img, up(cb.tick(), 10), 860, 1330, k, k, anchor='center')
    P3.draw(img, t)
    cb.pill(img, t, we(23) + 0.05, T4 - 0.15, 'TOO MUCH = DAMAGE', (700, 980), (500, 470), '#e8343f', '#ffffff', '#a01c26')
    z = lerp(1.22, 1.08, oc(prog(t, T3, 0.7))) + 0.05 * hot
    return D.camera(img.convert('RGB'), t, z, 640, 1000, 4 + 9 * hot)


# ------------------------------------------------------------------ shot 4: the question
P4 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (300, 1600)), size=9, legs='stand', arms='shrug', expr='smile', ground=1600,
                          look_camera=True, squash=True)),
                (ws(35) + 0.2, dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = G.frame(t).convert('RGBA')
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(gb.dipstick(0.6, pulse(t, 6)), 6), 800, 1420 + 10 * math.sin(t * 2), 1, 1, 8 * math.sin(t * 1.7), anchor='center')
    img.alpha_composite(G.rim(fg)); P4.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T4, 0.6))), 540, 1300, 5)


SCENE = D.sequence([(-9, shot_hold), (T2, shot_marks), (T3, shot_sump), (T4, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.25, HOOK, y=430)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, HOOK, y=430)
    ov.poll(cv, t, ws(33) - 0.1, END_T - 0.1, 'Do you check yours?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.0, 'whoosh', 0.7), (0.05, 'click', 1.0), (ws(3), 'pop', 0.8), (ws(3), 'sparkle', 0.5), (T2 + 0.25, 'click', 0.9),
        (T2 + 0.45, 'click', 0.9), (TOP, 'beep', 0.8), (T3 + 0.1, 'vroom', 0.7), (ws(20), 'buzzer', 0.5),
        (we(23) + 0.05, 'pop', 0.7), (OFF, 'click', 1.0), (OFF + 0.05, 'poof', 0.5), (OFF + 0.6, 'ding', 0.5),
        (ws(33) - 0.1, 'pop', 0.8), (ws(35), 'click', 0.8), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4], CUES, KEYCOL, overlay, cap=(T2 - 0.05, 1075))

if __name__ == '__main__':
    D.cli()
