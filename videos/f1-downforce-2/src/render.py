"""f1-downforce-2: grip and drag (14.0 s, loops). Isometric F1 look from videos/f1-aero v3 via shared/assets/isof1.

Beats (from words.json, faster-whisper on out/f1-downforce-2/voiceover.wav):
  0.00  cold open   the blue car carving a corner of the circuit, GRIP meter filling; headline SUCKS THE CAR DOWN
  T1    press       wind-tunnel lab: red arrows slam the car onto the floor (thud on 'onto')
  T2    grip        GRIP HARDER: the aero car turns in while the no-aero car runs wide into the gravel (SLIDES OFF)
  T3    drag        CREATES DRAG: turbulent wake behind the car, red DRAG arrow (no speed number: not source-confirmed)
  T4    poll        'Grip or speed?' YES / NO; END_T..DUR crossfades back into frame 0 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <voiceover.wav> <out.mp4>
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from assets import overlays as ov
from assets.isof1 import shots as SH, hud as HD, series, race as R
from pixanim.motion import prog, lerp, io

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR, END_T = 14.0, 13.6
T1, T2, T3, T4 = ws(4) - 0.25, ws(7) - 0.15, ws(17) - 0.15, ws(28) + 0.75
HIT = ws(4)
TAU0 = R.corner_tau(0) - 0.55                       # frame 0: the blue car is turning into a corner
SUCKS = ((('SUCKS THE CAR', False),), (('DOWN', True),))
GRIPH = ((('GRIP', True), (' HARDER', False)),)
DRAGH = ((('CREATES ', False), ('DRAG', True)),)


def world(t):
    if t < T1: a, I, _ = SH.race(TAU0 + t, k=lerp(3.6, 2.1, io(prog(t, -0.4, 1.6)))); SH.speed_lines(a, t)   # zoom out off the car
    elif t < T2: a, I = SH.downforce(t, HIT)
    elif t < T3: a, I, _, _ = SH.corner(t - T2)
    elif t < T4: a, I = SH.drag(t)
    else:
        a, I, _ = SH.race(TAU0 + t - T4 + 6.0, k=1.7); a = a * (1 - 0.35 * io(prog(t, T4, 0.4)))
    return HD.upscale(a)


def pose(t):
    if t < T1: return 'point', None
    if t < T2: return 'brace', None
    if t < T3: return ('point', None) if t < T2 + 1.25 else ('shock', 'shock')
    if t < T4: return 'shrug', None
    return 'think', None


def overlay(cv, t):
    if t < T1 or t >= T4:
        tau = TAU0 + t if t < T1 else TAU0 + t - T4 + 6.0
        HD.board(cv, tau); HD.track_map(cv, tau)
    HD.headline(cv, t, -0.45, T2 - 0.15, SUCKS, y=380, sz=110)
    if t < T1: HD.meter(cv, 0.15 + 0.85 * io(prog(t, -0.3, 1.5)), 'GRIP', HD.GRN)
    if T2 <= t < T3:
        HD.headline(cv, t, T2, T3 - 0.15, GRIPH, y=380, sz=120)
        HD.meter(cv, 0.4 + 0.6 * io(prog(t, T2, 1.0)), 'GRIP', HD.GRN)
        _, I, (pg, pa), dust = SH.corner(t - T2)
        gx, gy = HD.scr(I.p(pg[0], pg[1], 12)); ax, ay = HD.scr(I.p(pa[0], pa[1], 12))
        HD.pill(cv, t, T2 + 0.2, T3 - 0.15, 'NO AERO', gx, gy - 60, HD.GREY, 40)
        HD.pill(cv, t, T2 + 0.35, T3 - 0.15, 'AERO', ax, ay - 60, HD.CYAN, 40)
        if dust: HD.pill(cv, t, T2 + 1.25, T3 - 0.15, 'SLIDES OFF', 470, 620, HD.RED, 52, rot=-3)
    if T3 <= t < T4:
        HD.headline(cv, t, T3, T4 - 0.15, DRAGH, y=380, sz=120)
        _, I = SH.drag(t)
        a, b = HD.scr(I.p(34, 6.5, 6)), HD.scr(I.p(6, 6.5, 6))
        HD.drag_arrow(cv, (a[0], a[1] - 260), (b[0], b[1] - 260), 'DRAG', HD.RED, io(prog(t, ws(21) - 0.1, 0.3)))
    g = io(prog(t, T4, 0.5))
    ov.poll(cv, t, T4, END_T - 0.22, 'Grip or speed?', ov.SAFE_CX, lerp(820, 760, g), lerp(0.7, 0.95, g))
    arms, expr = pose(t)
    HD.presenter(cv, t, WORDS, arms, expr)


CUES = [(0.0, 'whoosh', 0.9), (0.02, 'vroom', 0.7), (HIT, 'thump', 1.0), (HIT, 'boom', 0.45), (T2 + 0.2, 'pop', 0.5),
        (T2 + 0.35, 'pop', 0.5), (T2 + 1.2, 'screech', 0.7), (T2 + 1.25, 'pop', 0.6), (ws(21) - 0.1, 'buzzer', 0.35), (T4, 'pop', 0.7)]

series.setup(HERE, WORDS, DUR, END_T, world, overlay, CUES, [T1, T2, T3, T4, END_T], bar_car='blue')

if __name__ == '__main__':
    series.main()
