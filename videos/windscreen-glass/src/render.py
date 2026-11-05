"""Renders 'car stuff, explained': why a windscreen cracks instead of shattering (13 s, loops).

Shots (timed to words.json, faster-whisper on out/windscreen-glass/voiceover.wav; the mixer holds a 1.4 s pause after
'middle.' so the layer cutaway can breathe, and the words after it are shifted to match):
  1 screen  0.00  a windscreen with a stone chip, the crack already spreading on frame 0; headline
  2 layers  1.95  three-layer cutaway builds up: GLASS / PLASTIC / GLASS callouts
  3 stop    ~5.5  a stone hits, the crack runs through the top glass and stops at the plastic: DOESN'T SHATTER
  4 ask     ~8.7  garage: presenter asks, poll 'Would you have guessed that? YES / NO'; whips back to shot 1 (loop)
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
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb
import dashep as D

GAP_T, GAP_D = 4.25, 1.4                            # held pause after 'middle.'
WORDS = kit.shift_words(kit.load_words(HERE), GAP_T, GAP_D)
def ws(i): return WORDS[i]['s']

DUR, END_T = 13.0, 12.62
T2 = 1.95
L1, L2, L3 = ws(6) - 0.05, ws(8) - 0.05, ws(11) - 0.1            # glass, plastic, glass ('middle')
T3 = ws(12) - 0.3                                                   # "That's why"
HIT, STOP = ws(15) - 0.12, ws(18) - 0.1                             # stone hits on 'cracks'; caught by 'shattering'
T4 = ws(19) - 0.2
G = Garage(W, H, 1520, 9)
HOOK = ((('Your windscreen has', None),), (('PLASTIC', '#ffd93b'), ('in the middle', None)))
KEYCOL = {'windscreen': YEL, 'two': YEL, 'plastic': YEL, 'cracks': RED, 'shattering': RED, 'guessed': YEL}


# ------------------------------------------------------------------ shot 1: the cracking windscreen
WS_S, WS_C = 9, (540, 840)
CHIP = (WS_C[0] - 60 * WS_S + 76 * WS_S + 4, WS_C[1] - 38 * WS_S + 40 * WS_S + 4)
P1 = Presenter([(-9, dict(path=Fn(lambda t: (200, 1640)), size=7, legs='stand', arms='point', point=CHIP, expr='shock',
                          ground=None, look=CHIP))], words=WORDS)


def crack1(t): return 0.18 + 0.82 * oc(prog(t, -0.3, 2.0)) + 0.04 * math.sin(t * 9)


def shot_screen(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(cb.windscreen(crack1(t), t=t), WS_S), WS_C[0], WS_C[1], anchor='center')
    for t0 in (-0.6, 0.0, 0.6, 1.2):                                   # the crack creeps out in small jumps
        fx.ring(fg, t, t0, *CHIP, (236, 244, 252), life=0.4, r1=260)
    gx = lerp(-300, 1400, prog(t, -0.5, 1.4))                          # sunlight glare sweeping across the glass
    if -300 < gx < 1400:
        ImageDraw.Draw(fg).polygon([(gx, 560), (gx + 140, 560), (gx - 60, 1120), (gx - 200, 1120)], fill=(255, 255, 255, 70))
    img.alpha_composite(G.rim(fg)); P1.draw(img, t)
    z = lerp(1.7, 1.1, oc(prog(t, -0.4, 1.4))); sh = 10 + 16 * math.exp(-max(0, t) * 2)
    return D.camera(img.convert('RGB'), t, z, CHIP[0] - 60, CHIP[1], sh)


# ------------------------------------------------------------------ shots 2 + 3: the cutaway
LS, LC, LH = 6, (640, 780), (20, 12, 20)
LW = 110
TOP = LC[1] - (sum(LH) + 4) * LS // 2
def layer_y(i): return TOP + (2 + sum(LH[:i]) + LH[i] / 2) * LS
STONE = Image.new('RGBA', (5, 5), (0, 0, 0, 0)); ImageDraw.Draw(STONE).ellipse((0, 0, 4, 4), fill=(150, 146, 140), outline=(60, 58, 56))
def layer_k(t, i): return fx.popin(t, (L1, L2, L3)[i], 0.3)


def shot_layers(t, stop_shot=False):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    crack = oc(prog(t, HIT, 0.5)) if stop_shot else 0
    stop = oc(prog(t, HIT + 0.45, 0.6)) if stop_shot else 0
    full = cb.glass_layers(crack, stop, t, LW, LH)
    x0 = LC[0] - full.width * LS // 2
    ImageDraw.Draw(fg).rounded_rectangle((30, TOP - 120, 1050, TOP + full.height * LS + 120), 36, fill=(18, 20, 28, 235),
                                         outline=(90, 96, 112, 255), width=8)          # diagram card, as in the reference split panels
    for i in range(3):                                                 # each layer drops in on its word
        k = 1.0 if stop_shot else layer_k(t, i)
        if k < 0.01: continue
        y0 = 2 + sum(LH[:i]); top = 0 if i == 0 else y0; bot = y0 + LH[i] + (2 if i == 2 else 0)
        fg.alpha_composite(up(full.crop((0, top, full.width, bot)), LS), (x0, max(0, TOP + top * LS + int((1 - k) * -260))))
    if stop_shot:
        u = prog(t, HIT - 0.35, 0.35)                                  # the stone flies in and hits the top glass
        if u < 1: fx.blit(fg, up(STONE, 9), lerp(940, LC[0] + 6, u), lerp(300, TOP + 10, u), anchor='center')
        fx.burst(fg, t, HIT, LC[0], TOP + 20, (236, 244, 252), n=10, r0=60, r1=220)
        fx.ring(fg, t, HIT + 0.45, LC[0], layer_y(1), (255, 210, 63), life=0.45, r1=300)
    img.alpha_composite(G.rim(fg)); P2.draw(img, t)
    if not stop_shot:
        for i, (txt, body) in enumerate((('GLASS', '#ffffff'), ('PLASTIC', '#ffd23f'), ('GLASS', '#ffffff'))):
            cb.pill(img, t, (L1, L2, L3)[i] + 0.15, T3 - 0.1, txt, (x0 + 80, layer_y(i)), (150, layer_y(i) + (i - 1) * 40),
                    body, '#1a1a2e', '#d6d9e2' if i != 1 else '#e8b923', s=5)
    else:
        cb.pill(img, t, STOP, T4 - 0.1, "DOESN'T SHATTER", (LC[0] + 60, layer_y(1)), (470, 470), '#5adc78', '#1a1a2e', '#2f9a4c')
    z = lerp(1.2, 1.06, oc(prog(t, T3 if stop_shot else T2, 0.6))) + (0.05 * math.exp(-(t - HIT) * 6) if stop_shot and t >= HIT else 0)
    return D.camera(img.convert('RGB'), t, z, 560, 800, 4 + (16 * math.exp(-(t - HIT) * 5) if stop_shot and t >= HIT else 0))


P2 = Presenter([(-9, dict(path=Fn(lambda t: (190, 1660)), size=6, legs='stand', arms='point', point=(LC[0] - 200, LC[1]), expr='smile',
                          ground=None, squash=True)),
                (HIT, dict(arms='shock', expr='shock', squash=True)),
                (STOP + 0.1, dict(arms='cheer', expr='grin', squash=True))], words=WORDS)


# ------------------------------------------------------------------ shot 4: the question
P4 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (300, 1600)), size=9, legs='stand', arms='shrug', expr='smile', ground=1600,
                          look_camera=True, squash=True)),
                (ws(22), dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(cb.windscreen(1.0, t=t), 3), 790, 1570 + 8 * math.sin(t * 2), anchor='bottom')
    img.alpha_composite(G.rim(fg)); P4.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T4, 0.6))), 540, 1300, 5)


SCENE = D.sequence([(-9, shot_screen), (T2, shot_layers), (T3, lambda t: shot_layers(t, True)), (T4, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.25, HOOK, y=440)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, HOOK, y=440)
    ov.poll(cv, t, ws(19) - 0.1, END_T - 0.1, 'Would you have guessed that?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.0, 'glass_crack', 0.8), (0.05, 'whoosh', 0.5), (0.6, 'glass_crack', 0.6), (1.2, 'glass_crack', 0.5),
        (L1, 'thump', 0.5), (L1 + 0.15, 'pop', 0.6), (L2, 'thump', 0.5), (L2 + 0.15, 'pop', 0.7), (L3, 'thump', 0.5), (L3 + 0.15, 'pop', 0.6),
        (HIT - 0.35, 'whoosh', 0.5), (HIT, 'glass_crack', 1.0), (HIT + 0.02, 'thump', 0.4), (HIT + 0.45, 'ding', 0.7),
        (STOP, 'pop', 0.7), (STOP + 0.02, 'sparkle', 0.6), (ws(19) - 0.1, 'pop', 0.8), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4], CUES, KEYCOL, overlay, cap=(T2, 1100), gap=(GAP_T, GAP_D))

if __name__ == '__main__':
    D.cli()
