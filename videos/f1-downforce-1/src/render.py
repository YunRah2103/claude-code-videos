"""f1-downforce-1: what downforce is (14.0 s, loops). Isometric F1 look from videos/f1-aero v3 via shared/assets/isof1.

Beats (from words.json, faster-whisper on out/f1-downforce-1/voiceover.wav):
  0.00  cold open   6-car race, follow-cam on the blue car already at speed; headline THIS FORMULA ONE / CAR COULD DRIVE /
                    UPSIDE DOWN (UPSIDE DOWN yellow); lap board + track map
  T1    wings       close-up on a straight: FRONT WING then REAR WING light up with callout pills; REPORTEDLY pill
  T2    downforce   dark-blue wind-tunnel lab, cyan ring, red arrows slam down; headline DOWNFORCE
  T3    ceiling     split frame: the car on the road below, the same car driving across the ceiling above; '?' pill
  T4    poll        'Would it stay on the ceiling?' YES / NO; END_T..DUR crossfades back into frame 0 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <voiceover.wav> <out.mp4>
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from assets import overlays as ov
from assets.isof1 import shots as SH, hud as HD, series
from assets.isof1.engine import Iso
from pixanim.motion import prog, lerp, io

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR, END_T = 14.0, 13.6
T1, T2, T3, T4 = ws(8) - 0.5, ws(16) - 0.1, ws(21) - 0.1, ws(32) - 0.15
HIT = T2 + 0.22
TAU0 = 1.6                                       # race clock at frame 0: cars already flying
HOOK = ((('THIS FORMULA ONE', False),), (('CAR COULD DRIVE', False),), (('UPSIDE DOWN', True),))
DOWNF = ((('DOWNFORCE', True),),)


def wing_cam(t):
    u = io(prog(t, T1, T2 - T1)); k = lerp(3.5, 4.1, u)
    return (108 - (15 - 6.5) * k, 200 - ((15 + 6.5) / 2 - 3) * k), k


def world(t):
    if t < T1:
        a, I, _ = SH.race(TAU0 + t, k=lerp(5.0, 2.0, 1 - (1 - prog(t, 0, 1.3)) ** 2)); SH.speed_lines(a, t, n=56)   # zoom out off the car
    elif t < T2:
        cam, k = wing_cam(t)
        hi = ('fw',) if t < ws(10) + 0.35 else ('rw',)
        a, I = SH.straight_car(t, 120, cam, k, hi=hi)
    elif t < T3:
        a, I = SH.downforce(t, HIT)
    else:
        a, I = SH.ceiling_split(t)
        if t >= T4: a = a * (1 - 0.35 * io(prog(t, T4, 0.4)))
    return HD.upscale(a)


def presenter_pose(t):
    if t < T1: return 'point', None
    if t < T2: return 'talkR', None
    if t < T3: return ('cheer1' if int(t * 5) % 2 else 'cheer2') if HIT <= t < HIT + 1.0 else 'point', None
    if t < T4: return 'shock', 'shock'
    return 'shrug', None


def overlay(cv, t):
    if t < T1:                                                      # race HUD only on the race shot
        HD.board(cv, TAU0 + t); HD.track_map(cv, TAU0 + t)
    HD.headline(cv, t, -0.45, T1 - 0.2, HOOK, y=400, sz=96)
    if T1 <= t < T2:
        cam, k = wing_cam(t)
        I = Iso(None, cam[0], cam[1], k)
        HD.pill(cv, t, ws(8), ws(10) - 0.1, 'REPORTEDLY', 300, 420, HD.YEL, 44, rot=-3)
        fx, fy = HD.scr(I.p(28, 14, 2)); rx, ry = HD.scr(I.p(1.5, 0.5, 8.5))
        HD.pill(cv, t, ws(10) - 0.05, T2 - 0.15, 'FRONT WING', fx, fy - 140, HD.YEL)
        HD.pill(cv, t, ws(10) + 0.35, T2 - 0.15, 'REAR WING', rx + 40, ry - 140, HD.YEL)
    HD.headline(cv, t, ws(20) - 0.1, T3 - 0.15, DOWNF, y=400, sz=130)
    HD.pill(cv, t, T3 + 0.15, T4 - 0.1, '?', 680, 640, HD.YEL, 90, rot=6)
    g = io(prog(t, T4, 0.5))
    ov.poll(cv, t, T4, END_T - 0.22, 'Would it stay on the ceiling?', ov.SAFE_CX, lerp(820, 760, g), lerp(0.7, 0.95, g))
    arms, expr = presenter_pose(t)
    HD.presenter(cv, t, WORDS, arms, expr)


CUES = [(0.0, 'whoosh', 0.9), (0.02, 'vroom', 0.7), (ws(8), 'pop', 0.4), (ws(10) - 0.05, 'pop', 0.5), (ws(10) + 0.35, 'pop', 0.5),
        (HIT, 'thump', 1.0), (HIT, 'boom', 0.5), (ws(20), 'ding', 0.5), (T3 + 0.15, 'pop', 0.5), (T4, 'pop', 0.7)]

series.setup(HERE, WORDS, DUR, END_T, world, overlay, CUES, [T1, T2, T3, T4, END_T], bar_car='blue')

if __name__ == '__main__':
    series.main()
