"""speed-limit-deal: everything the 2D and 3D versions share (one script, voice, timings, text and sound).

Timings come from words.json (faster-whisper on the shipped voiceover, out/speed-limit-deal-2d/voiceover.wav).
Each version supplies anchor(name, t) -> (x, y) in 1080x1920 px for: host, carL, carM, carR, hand, dial.
    0.00 cold open  cars already rolling, slam the glowing wall at 1.2 s; headline 'Your BMW could go FASTER'
    4.30 deal       handshake, BMW / MERCEDES / AUDI chips, NO LAW, REPORTEDLY, SECRET DEAL stamp; poll from 6.5 s
    7.75 limit      gauge fills to 155 + red limit line, '155 MPH LIMIT', framed real photo
   10.30 porsche    generic orange sports car zips past: PORSCHE (REPORTEDLY NEVER JOINED)
   11.70 unlock     DRIVER'S PACKAGE key opens the wall: SOME MODELS
   12.95 poll       poll grows for the last 2 s, presenter points at the viewer; loops back to frame 0
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import RED, YEL, GRN, WHITE
from pixanim.motion import prog, lerp, io
from pixanim.presenter import Presenter, Fn
from assets import overlays as ov

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR, END_T, FPS = 14.1, 13.78, 60
SLAM, BUMP, T2, STAMP, T3, FILL0, FILL1 = 1.2, 3.6, 4.3, ws(19), 7.75, 7.85, 8.3
T4, ZIP, T5, TURN, OPEN, T6 = 10.3, 10.4, 11.7, 12.25, ws(35), 12.95
POLL0, GROW0, POLL_OUT = 6.5, DUR - 2.0, DUR - 0.22
HOOK = ((('Your BMW', None),), (('could go', None), ('FASTER', '#ffd93b')))
HEAD_Y, CAP_Y = 440, 1075
KEYCOL = {'faster': YEL, 'reportedly': YEL, 'no': RED, 'law,': RED, 'law': RED, "gentleman's": YEL, 'agreement': YEL,
          '155': RED, 'porsche': YEL, 'never': RED, 'some': YEL, 'unlocked': GRN, 'remove': RED, 'limit': RED}
PHOTO, PHOTO_LABEL, PHOTO_CROP = 'autobahn', 'A GERMAN AUTOBAHN', (0.0, 0.3, 0.4, 1.0)


def presenter(anchor):
    return Presenter([
        (-9, dict(visible=False, path=Fn(lambda t: anchor('host', t)))),
        (2.1, dict(visible=True, path=Fn(lambda t: anchor('host', t)), size=5, legs='stand', arms='point', squash=True,
                   point=lambda t: anchor('carM', t), expr='smile', ground=None)),
        (ws(9), dict(arms='shrug', expr='smirk')),
        (T2, dict(arms='point', point=lambda t: anchor('hand', t), expr='smile')),
        (STAMP, dict(arms='shock', expr='shock', squash=True)),
        (T3, dict(visible=False)),
        (T6, dict(visible=True, arms=('aim', -12), expr='grin', look_camera=True, point=None, look=None, squash=True)),
        (END_T, dict(visible=False)),
    ], words=WORDS)


def photo(cv, t, t0, t1, x, y, w, rot, photo_dir):
    if not (t0 <= t < t1 + 0.2) or not os.path.isfile(os.path.join(photo_dir, PHOTO + '.jpg')): return
    k = kit.popin(t, t0, 0.3) * kit.popout(t, t1, 0.2)
    import math
    ov.place(cv, kit.hq_card(PHOTO, w, PHOTO_LABEL, rot, PHOTO_CROP), x, y + 6 * math.sin(t * 2.2), k, 0, 'photo')


def credit_line(photo_dir):
    cr = os.path.join(photo_dir, 'credits.json')
    c = json.load(open(cr)) if os.path.isfile(cr) else []
    return 'Photo: ' + c[0]['attribution'] if c else ''


def overlay(cv, t, anchor, photo_dir):
    """All sharp text and stickers (1080x1920, inside the safe zone). The headline is the only title, shown in the
    cold open and again on the loop frames, so the last frame matches frame 0."""
    ov.headline(cv, t, T2 - 0.25, HOOK, y=HEAD_Y)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, HOOK, y=HEAD_Y)
    ov.chip(cv, t, ws(8), T2 - 0.25, 'REPORTEDLY', 210, 640, YEL, 46, rot=-4)
    for i, nm in enumerate(('BMW', 'MERCEDES', 'AUDI')):          # plain text chips, one per car, left to right
        ov.chip(cv, t, ws(12 + i) - 0.05, T3 - 0.2, nm, (190, 450, 730)[i], 880 - 50 * (i == 1), WHITE, 48)
    ov.chip(cv, t, ws(15) - 0.05, T3 - 0.2, 'NO LAW', 220, 330, RED, 56, rot=-5)
    ov.chip(cv, t, ws(15) + 0.25, T3 - 0.2, 'REPORTEDLY', 650, 320, YEL, 46, rot=4)
    ov.stamp(cv, t, STAMP, T3 - 0.2, ('SECRET', 'DEAL'), 470, 500, rot=-12, scale=0.7)
    photo(cv, t, ws(24) + 0.05, T4 - 0.15, 240, 580, 340, -6, photo_dir)
    ov.chip(cv, t, FILL1 - 0.05, T4 - 0.15, '155 MPH LIMIT', 680, 345, RED, 48, rot=3)
    ov.chip(cv, t, ws(28) - 0.1, T5 - 0.1, 'PORSCHE', 470, 420, YEL, 60, sub='(REPORTEDLY NEVER JOINED)', rot=-3)
    ov.chip(cv, t, T5 + 0.05, T6 - 0.15, "DRIVER'S PACKAGE", 430, 330, YEL, 52, rot=-3)
    ov.chip(cv, t, ws(32) - 0.05, T6 - 0.15, 'SOME MODELS', 520, 480, GRN, 56, rot=3)
    g = io(prog(t, GROW0, DUR - 0.5 - GROW0))                 # small from 6.5 s, grows over the last 2 s
    ov.poll(cv, t, POLL0, POLL_OUT, 'Remove the limit?', lerp(675, ov.SAFE_CX, g), lerp(990, 820, g), lerp(0.48, 0.95, g))
    cl = credit_line(photo_dir)
    if t >= DUR - 0.8 and cl: ov.credit(cv, cl, 1165)


def captions(cv, t):
    """Spoken-word captions, one line at a time; none while the headline already shows the same words."""
    if t < ws(5) - 0.05 or t >= END_T: return
    ov.captions(cv, t, CAP_Y)


SHOT_MARKS = [T2, T3, T4, T5, T6, END_T]
CUES = [(0.0, 'vroom', 0.8), (0.3, 'whoosh', 0.7), (SLAM, 'crash', 0.9), (SLAM, 'boom', 0.6), (SLAM + 0.02, 'thump', 0.8),
        (SLAM + 0.05, 'ding', 0.5), (ws(8), 'pop', 0.4), (BUMP - 0.35, 'vroom', 0.4), (BUMP, 'thump', 0.6),
        (T2 + 0.1, 'pop', 0.6), (ws(12), 'pop', 0.5), (ws(13), 'pop', 0.5), (ws(14), 'pop', 0.5), (ws(15), 'buzzer', 0.35),
        (POLL0, 'pop', 0.7), (STAMP, 'stamp', 1.0), (STAMP + 0.01, 'boom', 0.4), (FILL0, 'whoosh', 0.4)] + [
        (FILL0 + 0.03 * k, 'click', 0.25) for k in range(14)] + [
        (FILL1, 'ding', 0.8), (ws(24) + 0.05, 'pop', 0.6), (ZIP, 'vroom', 0.8), (ZIP + 0.1, 'whoosh', 0.8),
        (T5 + 0.05, 'whoosh', 0.5), (TURN, 'click', 1.0), (TURN + 0.1, 'click', 0.8), (OPEN, 'crash', 0.6),
        (OPEN + 0.02, 'sparkle', 0.8), (OPEN + 0.3, 'vroom', 0.5), (T6, 'pop', 0.7), (END_T, 'whoosh', 0.6)]


def setup(here, shot, anchor, bar_car):
    """Wire the shared kit (progress bar, tag, mixer, CLI) for one version."""
    photo_dir = os.path.join(here, '..', 'assets')
    shots = [(-3.0, shot)] + [(m, shot) for m in SHOT_MARKS]
    kit.setup(here, WORDS, DUR, END_T, shots, {}, CUES, KEYCOL, overlay=lambda cv, t: overlay(cv, t, anchor, photo_dir),
              bar_car=bar_car, gauge=False, loud=True, crisp=True, end=False, flash=False, tag='corner')
    kit.sway = lambda cv, t: cv                              # no handheld resample: keeps the pixel grid exact
    kit.series_tag = lambda cv, t: ov.tag(cv)
    kit.captions = captions
    kit.credit_img = lambda: None                            # credit drawn inside the safe zone by overlay()


def safecheck(step=0.05):
    bad = []
    for i in range(int(DUR / step)):
        kit.frame(round(i * step * FPS))
        bad += [(round(i * step, 2), lab, b) for lab, b in ov.violations()]
    print(f'safe zone {ov.SAFE}: {len(bad)} violations'); [print(*b) for b in bad[:20]]
    return not bad
