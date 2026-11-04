"""f1-downforce-3: straight mode, corner mode, and the question (15.0 s, loops). Look: shared/assets/isof1.

Beats (from words.json, faster-whisper on out/f1-downforce-3/voiceover.wav):
  0.00  cold open   rear-wing close-up on a straight, the flap opening flat: STRAIGHT MODE: LOW DRAG; headline MAXIMUM DOWNFORCE?
  T1    top speed   TOP SPEED headline, wing flat; on 'snaps' the flap snaps back up (snap) -> CORNER MODE: GRIP
  T2    corner      the blue car turns into a corner of the circuit with the pill still up; lap board + track map
  T3    poll        big poll 'Would you drive it UPSIDE DOWN?' with large YES / NO over the ceiling split
  T5    point       the presenter points at the viewer; END_T..DUR crossfades back into frame 0 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <voiceover.wav> <out.mp4>
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from assets import overlays as ov
from assets.isof1 import shots as SH, hud as HD, series, race as R
from assets.isof1.engine import ease
from pixanim.motion import prog, lerp, io

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR, END_T = 15.0, 14.6
T1, SNAP, T2, T3, T5 = ws(9) - 0.2, ws(20), ws(22) - 0.1, ws(25) - 0.2, 13.0
TAU_C = R.corner_tau(0) - 0.4
CAM = (128, 214)                                    # rear-wing close-up
MAXD = ((('MAXIMUM', False),), (('DOWNFORCE?', True),))
TOPS = ((('TOP ', False), ('SPEED', True)),)


def flap(t):
    if t < SNAP: return ease((t + 0.45) / 0.9)       # opening during the cold open (already moving on frame 0)
    return 1 - ease((t - SNAP) / 0.12)                # snaps shut


def world(t):
    if t < T2:
        u = 1 - (1 - prog(t, 0, 1.6)) ** 1.6; k = lerp(11.5, 5.0, u)              # ease-out push from the wing: fastest on frame 0
        cam = (lerp(40, CAM[0], u), lerp(270, CAM[1], u))                          # with a sideways pan
        a, I = SH.straight_car(t, 240 if t < SNAP else 110, cam, k, flap=flap(t), hi=('rw',))
        if t < T1 + 0.5: SH.speed_lines(a, t, n=96, speed=4.0)
    elif t < T3:
        a, I, _ = SH.race(TAU_C + t - T2, k=1.9)
    else:
        a, I = SH.ceiling_split(t); a = a * (1 - 0.4 * io(prog(t, T3, 0.4)))
    return HD.upscale(a)


def pose(t):
    if t < T1: return 'point', None
    if t < T2: return ('talkR', None) if t < SNAP else ('point', 'wow')
    if t < T3: return 'point', None
    if t < T5: return 'shrug', None
    return ('aim', -8), 'grin'


def overlay(cv, t):
    if T2 <= t < T3:
        HD.board(cv, TAU_C + t - T2); HD.track_map(cv, TAU_C + t - T2)
    HD.headline(cv, t, -0.45, T1 - 0.15, MAXD, y=380, sz=110)
    HD.pill(cv, t, -0.45, SNAP - 0.1, 'STRAIGHT MODE: LOW DRAG', 470, 640, HD.CYAN, 44, rot=-2)
    HD.headline(cv, t, T1, T2 - 0.15, TOPS, y=380, sz=130)
    HD.pill(cv, t, SNAP + 0.05, T3 - 0.15, 'CORNER MODE: GRIP', 630, 640, HD.YEL, 46, rot=2)
    g = io(prog(t, T3, 0.5))
    ov.poll(cv, t, T3, END_T - 0.22, 'Would you drive it UPSIDE DOWN?', ov.SAFE_CX, lerp(840, 770, g), lerp(0.8, 1.0, g))
    arms, expr = pose(t)
    HD.presenter(cv, t, WORDS, arms, expr, gaze=(0, 0) if t >= T5 else (1, 0))


CUES = [(0.0, 'whoosh', 0.9), (0.02, 'vroom', 0.7), (0.1, 'click', 0.4), (SNAP, 'snap', 1.0), (SNAP + 0.02, 'thump', 0.5),
        (SNAP + 0.05, 'pop', 0.5), (T3, 'pop', 0.7), (T5, 'ding', 0.4)]

series.setup(HERE, WORDS, DUR, END_T, world, overlay, CUES, [T1, T2, T3, END_T], bar_car='blue')

if __name__ == '__main__':
    series.main()
