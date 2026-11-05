"""Renders 'car stuff, explained': the seatbelt pretensioner (loops).

Shots (timed to words.json, faster-whisper on out/seatbelt-pretensioner/voiceover.wav):
  1 pull    0.00  in the car, street rushing past the window; the presenter is already pulling the belt on frame 0 and it
                  snaps tight on 'tighten'; headline 'Your seatbelt can TIGHTEN by itself'
  2 buckle  ~2.8  buckle cutaway: crash flash, the small charge fires (CHARGE), the piston drags the buckle down; an
                  electric MOTOR pops in for 'or in some cars a motor'
  3 crash   ~6.3  back in the car: brakes, the cabin tilts, the belt snaps SNUG, a stopwatch whirs ('fraction of a second')
  4 line    ~9.1  crash timeline card: PRETENSIONER fires first, the car rolls along to the impact star -> BEFORE IMPACT
  5 ask     ~14.0 dashboard (A/C on): presenter asks, poll 'Did you know that? YES / NO'; whips back to shot 1 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]
"""
import math, os, sys
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
from pixanim.dash import Dashboard
from pixanim.street import Street
from pixanim.car import car
from pixanim.props import stopwatch
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb, seriesbits as sb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR = 16.3
END_T = 15.9                                                       # last word ends 15.82 (the read runs past 15 s even at 1.0x)
TIGHT = ws(3)                                                      # 'tighten'
T2 = ws(6) - 0.15                                                  # 'In a crash'
CRASH, CHG, MOT = ws(8), ws(11), ws(17)                            # 'crash', 'charge', 'motor'
T3 = ws(18) - 0.15                                                 # 'pulls it snug in a fraction of a second'
SNUG, FRAC = ws(20), ws(23)
T4 = ws(27) - 0.15                                                 # "That's called a pretensioner. It helps hold you back ..."
PRE, HOLD, BEFORE, IMPACT = ws(30), ws(33), ws(36), ws(38)
T5 = ws(41) - 0.15                                                 # 'Did you know your belt could move like that?'
G = Garage(W, H, 1520, 9)
DASH = Dashboard(outside=Garage(W, H, 1180, 9).base())
ST = Street()
HOOK = ((('Your seatbelt can', None),), (('TIGHTEN', '#e8343f'), ('by itself', None)))
KEYCOL = {'tighten': RED, 'crash,': RED, 'charge,': YEL, 'motor,': YEL, 'snug': YEL, 'fraction': YEL, 'pretensioner.': YEL,
          'back': YEL, 'impact': RED, 'belt': YEL}


# ------------------------------------------------------------------ the cabin: seat, belt, window onto the street
SS, SX, SY = 13, 150, 980                                         # seat scale and top-left
RET = (SX + sb.RETRACTOR[0] * SS, SY + sb.RETRACTOR[1] * SS)       # belt comes out of the seat back here
BUCK = (SX + 33 * SS, SY + 40 * SS)                                # buckle beside the far hip


@lru_cache(1)
def _cabin_mask():
    m = Image.new('RGBA', (W, H), (30, 31, 38, 255)); d = ImageDraw.Draw(m)
    d.rounded_rectangle((70, 520, 1010, 1080), 60, fill=(0, 0, 0, 0))             # side window
    d.rounded_rectangle((70, 520, 1010, 1080), 60, outline=(60, 62, 74, 255), width=22)
    d.rectangle((0, 1180, W, H), fill=(40, 41, 50, 255)); d.line((0, 1180, W, 1180), fill=(70, 72, 84, 255), width=10)   # door trim
    d.rectangle((600, 1240, 980, 1290), fill=(24, 25, 30, 255))                    # door handle recess
    return m


def belt(cv, t, slack, move, col=(70, 80, 104)):
    """Strap from the retractor across the chest to the buckle; slack bows it out, stitches scroll as it moves."""
    d = ImageDraw.Draw(cv)
    mx, my = (RET[0] + BUCK[0]) / 2 + 150 * slack, (RET[1] + BUCK[1]) / 2 + 60 * slack
    pts = [((1 - u) ** 2 * RET[0] + 2 * u * (1 - u) * mx + u * u * BUCK[0], (1 - u) ** 2 * RET[1] + 2 * u * (1 - u) * my + u * u * BUCK[1])
           for u in [i / 24 for i in range(25)]]
    d.line(pts, fill=(26, 26, 46), width=50, joint='curve'); d.line(pts, fill=col, width=34, joint='curve')
    for i in range(24):
        if (i + int(move * 3)) % 3 == 0: d.line((pts[i], pts[i + 1]), fill=(104, 118, 150), width=8)
    d.rectangle((BUCK[0] - 26, BUCK[1] - 30, BUCK[0] + 26, BUCK[1] + 24), fill=(36, 37, 44), outline=(26, 26, 46), width=6)
    d.rectangle((BUCK[0] - 10, BUCK[1] - 10, BUCK[0] + 10, BUCK[1] + 4), fill=(232, 52, 63))
    d.rectangle((RET[0] - 24, RET[1] - 20, RET[0] + 24, RET[1] + 20), fill=(110, 114, 126), outline=(26, 26, 46), width=6)


def cabin(t, speed, slack, move, P, tilt=0.0, extra=None):
    img = ST.frame(t, t * speed).convert('RGBA')
    img.alpha_composite(_cabin_mask())
    fx.blit(img, up(sb.seat(), SS), SX + 20 * SS, SY + 51 * SS, anchor='bottom')
    P.draw(img, t)
    belt(img, t, slack, move)
    if extra: extra(img)
    if tilt: img = img.rotate(tilt, resample=Image.NEAREST, center=(540, 1400), fillcolor=(20, 20, 26))
    return img


def guy_path(lurch):
    return Fn(lambda t: (SX + 23 * SS + lurch(t), SY + 46 * SS))


# ------------------------------------------------------------------ shot 1: pulling the belt
P1 = Presenter([(-9, dict(path=guy_path(lambda t: 0), size=8, legs="sit", arms='point', point=BUCK, expr='smile', ground=None,
                          face=1, look=BUCK)),
                (TIGHT, dict(arms='shock', expr='wow', squash=True, look_camera=True))], words=WORDS)


def slack1(t): return 1.0 - oc(prog(t, TIGHT - 0.05, 0.18)) if t < T2 else 0.0


def shot_pull(t):
    k = 1 - oc(prog(t, TIGHT - 0.05, 0.18))
    move = t * 12 * k + 3                                           # webbing already sliding on frame 0
    img = cabin(t, 1400, 0.55 + 0.45 * math.sin(t * 7) * k if k > 0 else 0, move, P1)
    if t >= TIGHT:
        fx.ring(img, t, TIGHT, BUCK[0] - 100, BUCK[1] - 120, (255, 90, 90), life=0.4, r1=380)
        fx.burst(img, t, TIGHT, BUCK[0] - 100, BUCK[1] - 120, (255, 210, 63), n=12, r0=120, r1=420)
    z = lerp(1.7, 1.1, oc(prog(t, -0.2, 1.1))); sh = 12 + 22 * math.exp(-max(0, t) * 2) + (24 * math.exp(-(t - TIGHT) * 6) if t >= TIGHT else 0)
    return D.camera(img.convert('RGB'), t, z, BUCK[0] - 80, BUCK[1] - 200, sh)


# ------------------------------------------------------------------ shot 2: inside the buckle
BC, BS = (430, 760), 6


def fire(t): return prog(t, CHG - 0.05, 0.7)


def card(fg, box):
    ImageDraw.Draw(fg).rounded_rectangle(box, 36, fill=(18, 20, 28, 235), outline=(90, 96, 112, 255), width=8)


P2 = Presenter([(-9, dict(path=Fn(lambda t: (900, 1720)), size=7, legs='stand', arms='point', point=BC, expr='smile', ground=1720, look=BC)),
                (CRASH, dict(arms='shock', expr='shock', squash=True)),
                (CHG + 0.2, dict(arms='point', expr='wow')),
                (MOT, dict(arms='cheer', expr='grin', squash=True))], words=WORDS)


def shot_buckle(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if CRASH <= t < CRASH + 0.5:                                    # crash alarm: red flash over the garage
        fg.alpha_composite(Image.new('RGBA', (W, H), (232, 52, 63, int(90 * (1 - prog(t, CRASH, 0.5))))))
    card(fg, (60, 300, 1020, 1060))
    f = fire(t)
    fx.blit(fg, up(sb.buckle(f, t), BS), BC[0], BC[1], anchor='center')
    cy = BC[1] + (77 - 40) * BS
    if t >= CHG - 0.05:
        fx.burst(fg, t, CHG - 0.05, BC[0], cy, (255, 200, 80), n=14, r0=60, r1=360)
        fx.ring(fg, t, CHG - 0.05, BC[0], cy, (255, 230, 120), life=0.4, r1=300)
        fx.puff(fg, t, CHG, BC[0] + 40, cy, seed=4, life=0.8, size=0.8, drift=(160, -60))
    if f > 0:                                                        # downward arrows: the webbing is yanked in
        d = ImageDraw.Draw(fg); bob = 14 * math.sin(t * 16)
        for dx in (-130, 130):
            x, y = BC[0] + dx, BC[1] - 120 + bob
            d.polygon([(x - 34, y), (x + 34, y), (x, y + 50)], fill=(255, 217, 59), outline=(26, 26, 46))
            d.rectangle((x - 12, y - 60, x + 12, y), fill=(255, 217, 59), outline=(26, 26, 46))
    if t >= MOT - 0.25:                                              # 'or in some cars a motor'
        k = fx.popin(t, MOT - 0.25, 0.3)
        fx.blit(fg, up(sb.motor(t), 9), 780, 760, k, k, anchor='center')
        fx.sparkles(fg, t, 780, 760, 280, 200, n=4, seed=13)
    img.alpha_composite(G.rim(fg)); P2.draw(img, t)
    cb.pill(img, t, CHG + 0.1, T3 - 0.1, 'CHARGE', (BC[0] + 30, cy), (720, 1000), '#ffb347', '#1a1a2e', '#d9822b', s=6)
    cb.pill(img, t, MOT + 0.05, T3 - 0.1, 'MOTOR', (780, 720), (780, 470), '#7cc4ff', '#1a1a2e', '#4a90d9', s=6)
    z = lerp(1.2, 1.05, oc(prog(t, T2, 0.6))) + (0.06 * math.exp(-(t - CHG) * 6) if t >= CHG else 0)
    sh = 4 + (22 * math.exp(-(t - CRASH) * 5) if t >= CRASH else 0) + (18 * math.exp(-(t - CHG) * 5) if t >= CHG else 0)
    return D.camera(img.convert('RGB'), t, z, 540, 760, sh)


# ------------------------------------------------------------------ shot 3: the crash, seen from the seat
def lurch3(t):
    return 70 * math.sin(math.pi * prog(t, T3, SNUG - T3 + 0.05)) if t < SNUG + 0.05 else -10 * math.exp(-(t - SNUG) * 4)


P3 = Presenter([(-9, dict(path=guy_path(lurch3), size=8, legs="sit", arms='flail', expr='shock', ground=None, face=1)),
                (SNUG, dict(arms='down', expr='wow', squash=True, look_camera=True)),
                (FRAC, dict(arms='talk', expr='grin'))], words=WORDS)


def shot_crash(t):
    brake = oc(prog(t, T3, 0.6))
    slack = 0.6 * (1 - oc(prog(t, SNUG - 0.08, 0.12)))
    sw = (lambda im: (fx.blit(im, up(stopwatch(t * 4 % 1), 9), 820, 760, anchor='center'),
                      fx.ring(im, t % 0.6, 0, 820, 760, (255, 210, 63), life=0.4, r1=240))) if t >= FRAC - 0.2 else None
    img = cabin(t, lerp(2600, 300, brake), slack, t * 4, P3, tilt=-4 * math.sin(math.pi * prog(t, T3, 1.0)), extra=sw)
    if t >= SNUG:
        fx.ring(img, t, SNUG, BUCK[0] - 100, BUCK[1] - 140, (255, 210, 63), life=0.4, r1=420)
        fx.burst(img, t, SNUG, BUCK[0] - 100, BUCK[1] - 140, (255, 255, 255), n=10, r0=120, r1=380)
    cb.pill(img, t, SNUG + 0.05, T4 - 0.1, 'SNUG', (BUCK[0] - 90, BUCK[1] - 150), (420, 640), '#5adc78', '#1a1a2e', '#2f9a4c', s=7)
    sh = 6 + 30 * math.exp(-max(0, t - T3) * 3) + (22 * math.exp(-(t - SNUG) * 6) if t >= SNUG else 0)
    return D.camera(img.convert('RGB'), t, lerp(1.25, 1.08, oc(prog(t, T3, 0.5))), 540, 1050, sh)


# ------------------------------------------------------------------ shot 4: the timeline
LX0, LX1, LY = 170, 900, 860
def star(d, cx, cy, r, col):
    d.polygon([(cx + (r if i % 2 == 0 else r * 0.45) * math.cos(math.radians(i * 36 - 90)),
                cy + (r if i % 2 == 0 else r * 0.45) * math.sin(math.radians(i * 36 - 90))) for i in range(10)], fill=col, outline=(26, 26, 46))


P4 = Presenter([(-9, dict(path=Fn(lambda t: (170, 1720)), size=7, legs='stand', arms='point', point=(LX0, LY), expr='smile', ground=1720,
                          look=(LX0, LY))),
                (HOLD, dict(arms=('aim', -20), expr='grin', squash=True)),
                (IMPACT, dict(arms='shock', expr='shock', squash=True))], words=WORDS)


def shot_line(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    card(fg, (60, 440, 1020, 1060))
    d.rounded_rectangle((LX0, LY - 14, LX1, LY + 14), 14, fill=(60, 62, 74), outline=(26, 26, 46), width=6)
    u = io(prog(t, T4 + 0.3, IMPACT - T4 - 0.3)); cx = lerp(LX0, LX1 - 60, u)
    d.rounded_rectangle((LX0, LY - 14, cx, LY + 14), 14, fill=(255, 210, 63))
    fx.blit(fg, up(sb.buckle(1.0 if t >= PRE else 0.0, t), 3), LX0 + 10, LY - 30, anchor='bottom')
    if t >= PRE: fx.ring(fg, t, PRE, LX0 + 10, LY - 150, (255, 210, 63), life=0.4, r1=220)
    if t < IMPACT: star(d, LX1 - 20, LY - 90, 70 + 8 * math.sin(t * 12), (255, 120, 60))
    else:
        star(d, LX1 - 20, LY - 90, 110, (255, 220, 90)); fx.burst(fg, t, IMPACT, LX1 - 20, LY - 90, (255, 120, 60), n=16, r0=80, r1=420)
    fx.blit(fg, up(car('red', int(t * 900) % 360), 3), cx, LY - 20, rot=-4 * math.sin(t * 20) if t >= IMPACT else 0)
    fx.speed_lines(fg, 0.6 if PRE < t < IMPACT else 0, int(t * 10) % 5, col=(80, 84, 98))
    img.alpha_composite(G.rim(fg)); P4.draw(img, t)
    cb.pill(img, t, PRE + 0.05, T5 - 0.1, 'PRETENSIONER', (LX0 + 10, LY - 140), (440, 560), '#ffd23f', '#1a1a2e', '#e8b923', s=6)
    cb.pill(img, t, BEFORE, T5 - 0.1, 'BEFORE IMPACT', (lerp(LX0, LX1, 0.55), LY + 14), (560, 990), '#ff6b6b', '#1a1a2e', '#c0392b', s=6)
    z = lerp(1.18, 1.04, oc(prog(t, T4, 0.5))) + (0.06 * math.exp(-(t - IMPACT) * 6) if t >= IMPACT else 0)
    return D.camera(img.convert('RGB'), t, z, 540, 900, 4 + (26 * math.exp(-(t - IMPACT) * 5) if t >= IMPACT else 0))


# ------------------------------------------------------------------ shot 5: the question, on the dashboard
P5 = Presenter([(-9, dict(path=Fn(lambda t: (250, 1700)), size=9, legs='stand', arms='shrug', expr='smile', ground=1700, look_camera=True,
                          squash=True)),
                (ws(47), dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.12 + 0.015 * math.sin(t * 9)), ac_on=True).copy()
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(sb.buckle(0.5 + 0.5 * math.sin(t * 3), t), 4), 830, 1780 + 10 * math.sin(t * 4), anchor='bottom')
    fx.sparkles(fg, t, 830, 1620, 300, 300, n=4, seed=41)
    img.alpha_composite(fg); P5.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T5, 0.6))), 540, 1200, 5)


SCENE = D.sequence([(-9, shot_pull), (T2, shot_buckle), (T3, shot_crash), (T4, shot_line), (T5, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.2, HOOK, y=440)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR + 1 / 60), T2 - 0.2, HOOK, y=440)
    ov.poll(cv, t, T5 + 0.1, END_T - 0.1, 'Did you know that?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.0, 'click', 1.0), (0.05, 'whoosh', 0.5), (TIGHT, 'snap', 0.9), (TIGHT + 0.02, 'click', 0.8),
        (CRASH, 'crash', 0.5), (CHG - 0.05, 'thump', 0.9), (CHG, 'poof', 0.6), (CHG + 0.1, 'pop', 0.6), (CHG + 0.15, 'click', 0.8),
        (MOT - 0.25, 'hum', 0.4), (MOT + 0.05, 'pop', 0.6),
        (T3 + 0.05, 'screech', 0.8), (SNUG - 0.08, 'snap', 1.0), (SNUG, 'click', 0.9), (FRAC - 0.2, 'ding', 0.4),
        (PRE, 'click', 0.8), (PRE + 0.05, 'pop', 0.7), (HOLD, 'sparkle', 0.4), (BEFORE, 'pop', 0.7), (IMPACT, 'crash', 0.7),
        (T5 + 0.1, 'pop', 0.8), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4, T5], CUES, KEYCOL, overlay, lead=1 / 60, cap=(T2, 1100, ((T5, 99),)))

if __name__ == '__main__':
    D.cli()
