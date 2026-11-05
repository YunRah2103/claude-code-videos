"""Renders 'car stuff, explained': why tyres are black (loops).

Shots (timed to words.json, faster-whisper on out/tyres-black/voiceover.wav):
  1 spin    0.00  garage close-up: a black tyre already spinning on frame 0, dust flicking off; headline 'Why are tyres BLACK?'
  2 filler  ~1.9  'not just for looks': cutaway of pale rubber; carbon black pours in, particles fill it -> CARBON BLACK
  3 sun     ~6.3  the sun fires UV rays at the tyre, a shield pops up and they bounce off -> SUN PROTECTION
  4 wear    ~8.1  side by side on rollers: pale tyre vs black tyre, the pale wear bar drains fast -> WEARS FASTER
  5 ask     ~10.7 dashboard (A/C on, needle idling): presenter asks, poll 'Would you have guessed that? YES / NO'; loops
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
from pixanim.motion import prog, lerp, io, oc, ob
from pixanim.presenter import Presenter, Fn
from pixanim.dash import Dashboard
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb, seriesbits as sb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR = 14.9
END_T = 14.5                                           # last word ends 14.42; 0.4 s whip back to frame 0
T2 = ws(4) - 0.15                                                  # "It's not just for looks"
FILL, CB = ws(10), ws(12)                                          # 'filler', 'carbon'
LAST = ws(16)                                                      # 'last longer'
T3 = ws(18) - 0.15                                                 # 'and protects it from sunlight'
PROT = ws(19)
T4 = ws(23) - 0.15                                                 # 'Without it, tyres would wear out faster'
WEAR = ws(27)
T5 = ws(30) - 0.15                                                 # 'Did you know ... Would you have guessed that?'
ASK = ws(40)
G = Garage(W, H, 1520, 9)
DASH = Dashboard(outside=Garage(W, H, 1180, 9).base())
HOOK = ((('Why are tyres', None),), (('BLACK?', '#ffd93b'),))
KEYCOL = {'black': YEL, 'black?': YEL, 'looks.': YEL, 'carbon': YEL, 'longer': YEL, 'sunlight.': YEL, 'faster.': RED,
          'job': YEL, 'guessed': YEL}


def spin(t): return t * 720                                       # tyre rotation (deg)


# ------------------------------------------------------------------ shot 1: the spinning tyre
TC = (600, 1160)                                                   # tyre centre on screen
P1 = Presenter([(-9, dict(path=Fn(lambda t: (170, 1700)), size=6, legs='stand', arms='point', point=TC, expr='wow', ground=1700, look=TC)),
                (ws(3), dict(arms='cheer', expr='grin', squash=True))], words=WORDS)


def shot_spin(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.speed_lines(fg, 1.0, int(t * 12) % 6, col=(70, 72, 84))
    bob = 6 * math.sin(t * 31)
    fx.blit(fg, up(sb.tyre(spin(t)), 15), TC[0], TC[1] + bob, anchor='center')
    for k in range(6):                                             # dust and rubber crumbs flicking off the tread
        t0 = math.floor(t / 0.3) * 0.3 - k * 0.3
        fx.dust(fg, t, t0, TC[0] + 360, TC[1] + 240, n=6, seed=5 + int(t0 * 10) % 7, life=0.6, dirx=900, col=(120, 116, 110))
    fx.ring(fg, t % 0.5, 0, TC[0], TC[1], (255, 210, 63), life=0.45, r1=470)
    img.alpha_composite(G.rim(fg)); P1.draw(img, t)
    z = lerp(1.7, 1.08, oc(prog(t, -0.2, 1.1))); sh = 12 + 22 * math.exp(-max(0, t) * 2)
    return D.camera(img.convert('RGB'), t, z, TC[0], TC[1] - 120, sh)


# ------------------------------------------------------------------ shot 2: carbon black goes into the rubber
BC, BS = (560, 720), 9                                            # rubber block centre + scale
def filled(t): return io(prog(t, FILL, CB + 0.5 - FILL))


P2 = Presenter([(-9, dict(path=Fn(lambda t: (170, 1720)), size=7, legs='stand', arms='shrug', expr='smirk', ground=1720, look_camera=True,
                          squash=True)),
                (FILL, dict(arms='point', point=BC, expr='smile', look=BC)),
                (CB, dict(arms='cheer', expr='grin', squash=True)),
                (LAST, dict(arms=('aim', 30), expr='smile'))], words=WORDS)


def card(fg, box):
    ImageDraw.Draw(fg).rounded_rectangle(box, 36, fill=(18, 20, 28, 235), outline=(90, 96, 112, 255), width=8)


def shot_filler(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    card(fg, (60, 470, 1020, 1030))
    k = filled(t)
    fx.blit(fg, up(sb.rubber_block(t, k), BS), BC[0], BC[1] + 20, anchor='center')
    d = ImageDraw.Draw(fg)
    if FILL - 0.1 <= t < CB + 0.7:                                 # the black filler pours in from a sack above
        sx = BC[0] + 20 * math.sin(t * 5)
        d.polygon([(sx - 70, 420), (sx + 70, 420), (sx + 40, 500), (sx - 40, 500)], fill=(40, 40, 46), outline=(110, 114, 126))
        for j in range(16):
            y = 510 + ((t * 900 + j * 37) % 200); x = sx + 18 * math.sin(j * 2.3 + t * 9)
            d.rectangle((x - 9, y - 9, x + 9, y + 9), fill=(10, 10, 12), outline=(80, 80, 92))
    if t < FILL:                                                   # 'not just for looks': a sparkly paint swatch gets crossed out
        fx.sparkles(fg, t, BC[0], BC[1], 700, 300, n=6, seed=11)
        u = oc(prog(t, ws(7), 0.25))
        if u > 0: d.line((BC[0] - 300, BC[1] - 160, BC[0] - 300 + 600 * u, BC[1] - 160 + 380 * u), fill=(232, 52, 63), width=36)
    if t >= CB: fx.burst(fg, t, CB, BC[0], BC[1] + 40, (255, 210, 63), n=14, r0=200, r1=520)
    if t >= LAST:                                                   # 'last longer': a tick and a long life bar
        fx.blit(fg, up(sb.wear_bar(oc(prog(t, LAST, 0.6))), 9), BC[0], 990, anchor='center')
        fx.sparkles(fg, t, BC[0], 990, 600, 80, n=5, seed=17)
    img.alpha_composite(G.rim(fg)); P2.draw(img, t)
    cb.pill(img, t, CB + 0.05, T3 - 0.1, 'CARBON BLACK', (BC[0] + 120, BC[1] + 40), (560, 330), '#ffd23f', '#1a1a2e', '#e8b923', s=6)
    z = lerp(1.2, 1.05, oc(prog(t, T2, 0.6))) + (0.06 * math.exp(-(t - CB) * 6) if t >= CB else 0)
    return D.camera(img.convert('RGB'), t, z, 560, 900, 4 + (16 * math.exp(-(t - CB) * 5) if t >= CB else 0))


# ------------------------------------------------------------------ shot 3: sunlight bounces off
SUN, TY = (820, 560), (430, 1120)


def shot_sun(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    fx.rays(fg, t, T3, SUN[0], SUN[1], (255, 220, 90), life=9, hold=True, r=460, n=12)
    sh_k = fx.popin(t, PROT, 0.3)
    for j in range(5):                                             # UV rays shooting at the tyre, bouncing off the shield
        u = ((t - T3) * 1.8 + j / 5) % 1
        a = (SUN[0] - 60 - j * 30, SUN[1] + 80); b = (TY[0] + 120 - j * 40, TY[1] - 220)
        hitp = 0.62 if sh_k > 0.5 else 1.0
        if u < hitp:
            x, y = lerp(a[0], b[0], u), lerp(a[1], b[1], u)
            d.line((x, y, x - (b[0] - a[0]) * 0.12, y - (b[1] - a[1]) * 0.12), fill=(190, 120, 255), width=18)
        else:
            v = (u - hitp) / (1 - hitp); x0, y0 = lerp(a[0], b[0], hitp), lerp(a[1], b[1], hitp)
            d.line((x0 + 300 * v, y0 - 260 * v, x0 + 300 * v + 50, y0 - 260 * v - 40), fill=(190, 120, 255), width=14)
            fx.ring(fg, v * 0.3, 0, x0, y0, (220, 190, 255), life=0.3, r1=90)
    fx.blit(fg, up(sb.sun(t), 9), SUN[0], SUN[1], rot=0, anchor='center')
    fx.blit(fg, up(sb.tyre(spin(t) * 0.3), 11), TY[0], TY[1], anchor='center')
    if sh_k > 0:
        fx.blit(fg, up(sb.shield(prog(t, PROT + 0.1, 0.4)), 12), lerp(TY[0], TY[0] + 230, 1), TY[1] - 300, sh_k, sh_k, anchor='center')
        fx.ring(fg, t, PROT, TY[0] + 230, TY[1] - 300, (120, 190, 255), life=0.4, r1=300)
        fx.sparkles(fg, t, TY[0] + 230, TY[1] - 300, 300, 300, n=5, seed=23)
    img.alpha_composite(G.rim(fg))
    cb.pill(img, t, PROT + 0.15, T4 - 0.1, 'SUN PROTECTION', (TY[0] + 230, TY[1] - 300), (300, 600), '#7cc4ff', '#1a1a2e', '#4a90d9', s=6)
    z = lerp(1.25, 1.05, oc(prog(t, T3, 0.5))) + (0.05 * math.exp(-(t - PROT) * 6) if t >= PROT else 0)
    return D.camera(img.convert('RGB'), t, z, 600, 900, 5 + (14 * math.exp(-(t - PROT) * 5) if t >= PROT else 0))


# ------------------------------------------------------------------ shot 4: pale vs black on rollers
LT, BT = (300, 1080), (790, 1080)


def shot_wear(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    u = prog(t, T4 + 0.3, T5 - T4 - 0.4)
    pale_life, black_life = 1 - 0.85 * io(u), 1 - 0.18 * io(u)
    for (cx, cy), light, life in ((LT, 1.0, pale_life), (BT, 0.0, black_life)):
        d.rectangle((cx - 230, cy + 250, cx + 230, cy + 290), fill=(60, 62, 72))           # rolling road drum
        for k in range(8):
            x = cx - 230 + ((k * 60 - t * 900) % 460); d.rectangle((x, cy + 256, x + 24, cy + 284), fill=(110, 114, 126))
        fx.blit(fg, up(sb.tyre(spin(t) * 1.2, light, 1 - life), 9), cx, cy + 6 * math.sin(t * 40 + cx), anchor='center')
        fx.dust(fg, t, math.floor(t / 0.25) * 0.25, cx - 200, cy + 240, n=5, seed=int(t * 4) % 9, life=0.5, dirx=-700,
                col=(206, 190, 156) if light else (60, 60, 66))
        fx.blit(fg, up(sb.wear_bar(life, (232, 52, 63) if life < 0.4 else (90, 220, 120), 40), 9), cx, cy - 330, anchor='center')
    if t >= WEAR: fx.ring(fg, t, WEAR, LT[0], LT[1], (255, 90, 90), life=0.45, r1=360)
    img.alpha_composite(G.rim(fg))
    cb.pill(img, t, WEAR, T5 - 0.1, 'WEARS FASTER', (LT[0], LT[1] - 330), (400, 560), '#ff6b6b', '#1a1a2e', '#c0392b', s=6)
    z = lerp(1.18, 1.04, oc(prog(t, T4, 0.5))) + (0.05 * math.exp(-(t - WEAR) * 6) if t >= WEAR else 0)
    return D.camera(img.convert('RGB'), t, z, 540, 950, 4 + (18 * math.exp(-(t - WEAR) * 5) if t >= WEAR else 0))


# ------------------------------------------------------------------ shot 5: the question, on the dashboard
P5 = Presenter([(-9, dict(path=Fn(lambda t: (250, 1700)), size=9, legs='stand', arms='shrug', expr='smile', ground=1700, look_camera=True,
                          squash=True)),
                (ASK, dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.12 + 0.015 * math.sin(t * 9)), ac_on=True).copy()
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(sb.tyre(spin(t) * 0.4), 6), 830, 1640, anchor='center')
    fx.sparkles(fg, t, 830, 1640, 300, 300, n=4, seed=41)
    img.alpha_composite(fg); P5.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T5, 0.6))), 540, 1200, 5)


SCENE = D.sequence([(-9, shot_spin), (T2, shot_filler), (T3, shot_sun), (T4, shot_wear), (T5, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.2, HOOK, y=440)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.2, HOOK, y=440)
    ov.poll(cv, t, T5 + 0.1, END_T - 0.1, 'Would you have guessed that?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.02, 'screech', 1.0), (0.05, 'whoosh', 0.5), (ws(3), 'pop', 0.6), (ws(7), 'buzzer', 0.4),
        (FILL, 'slide_down', 0.5), (CB, 'stamp', 0.8), (CB + 0.05, 'pop', 0.7), (LAST, 'ding', 0.5),
        (PROT, 'boing', 0.6), (PROT + 0.15, 'pop', 0.6), (PROT + 0.05, 'sparkle', 0.6),
        (T4 + 0.1, 'screech', 0.7), (WEAR, 'buzzer', 0.5), (WEAR + 0.05, 'pop', 0.7),
        (T5 + 0.1, 'pop', 0.8), (ASK, 'sparkle', 0.5), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4, T5], CUES, KEYCOL, overlay, cap=(T2, 1100, ((ASK - 0.05, 99),)))

if __name__ == '__main__':
    D.cli()
