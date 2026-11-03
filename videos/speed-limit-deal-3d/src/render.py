"""Renders 'speed-limit-deal-3d': the German 155 mph gentleman's agreement, as a 3D pixel test of the 2D format.

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, mixer), same as the 2D
episodes. The world is a Three.js scene (scene3d.js, built from shared/assets/pix3d) rendered at 270x480 in Chromium
and upscaled 4x nearest; text, chips, stamp, poll, tag and progress bar are drawn sharp at 1080x1920 on top
(shared/assets/overlays.py), all inside the TikTok text safe zone (12-62 % height, left 85 % width).
The presenter is the 2D pixel sprite (shared/pixanim/presenter), a flat billboard pinned to a 3D floor point.
Shots (3D camera rigs in scene3d.js; times from words.json, faster-whisper on the shipped voiceover):
  1 cold open 0.00  three cars rev, launch and slam into the force wall at a glowing 155 (shake + slow push-in)
  2 deal      4.60  handshake icon between the cars; BMW / MERCEDES / AUDI chips; NO LAW; SECRET DEAL stamp (camera punch)
  3 limit     7.70  dial fills to 155 with the red limit line; framed real photo; poll sticker from ~8.9 s to the end
  4 porsche  10.20  a generic orange sports car zips past the wall: PORSCHE (REPORTEDLY NEVER JOINED)
  5 unlock   11.50  DRIVER'S PACKAGE key opens the padlock, the wall shatters: SOME MODELS (no speed number)
  6 poll     12.75  poll grows, presenter points at the viewer; whips back to the cold open so the end loops
    python render.py frames3d | still <dir> t... | safecheck | video <voiceover.wav> <out.mp4> [t0 t1]
"""
import json, math, os, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
import episode as kit
from episode import W, H, RED, YEL, GRN, WHITE
from pixanim.motion import Track, prog, lerp, clamp, oc, io, ob
from pixanim.presenter import Presenter, Fn
from assets import overlays as ov

OUT = os.path.join(ROOT, 'out', 'speed-limit-deal-3d')
F3D = os.path.join(OUT, 'frames3d')
WORDS = kit.load_words(HERE)
DUR, END_T, FPS = 13.95, 13.55, 60
def ws(i): return WORDS[i]['s']
T2, T3, T4, T5, T6 = 4.6, 7.7, 10.2, 11.5, 12.75
SLAM, STAMP, FILL1, ZIP, TURN, OPEN = 1.30, 6.85, 8.35, 10.35, 11.95, 12.12
POLL0 = ws(25) + 0.05                       # "miles": poll sticker pops in, stays to the end
HOOK = ((('Your BMW', None),), (('could go', None), ('FASTER', '#ffd93b')))
KEYCOL = {'faster': YEL, 'reportedly': YEL, 'no': RED, 'law,': RED, 'law': RED, "gentleman's": YEL, 'agreement': YEL,
          '155': RED, 'porsche': YEL, 'never': RED, 'some': YEL, 'unlocked': GRN, 'remove': RED, 'limit': RED}
PHOTO, PHOTO_LABEL = 'autobahn', 'A GERMAN AUTOBAHN'


# ------------------------------------------------------------------ 3D frames + anchors
_A = {}
def anchors():
    if not _A: _A.update(json.load(open(os.path.join(F3D, 'anchors.json'))))
    return _A
def anchor(name, t):
    n = str(min(round(t * FPS), round(DUR * FPS) - 1)); a = anchors().get(n)
    return tuple(a[name][:2]) if a else (W / 2, H / 2)


P = Presenter([
    (-9, dict(visible=False, path=Fn(lambda t: anchor('host', t)))),
    (2.25, dict(visible=True, path=Fn(lambda t: anchor('host', t)), size=5, legs='stand', arms='point', squash=True,
                point=lambda t: anchor('carM', t), expr='smile', ground=None)),
    (ws(9), dict(arms='shrug', expr='smirk')),
    (T2, dict(arms='point', point=lambda t: anchor('hand', t), expr='smile')),
    (STAMP, dict(arms='shock', expr='shock', squash=True)),
    (T3, dict(visible=False)),
    (T6, dict(visible=True, arms=('aim', -12), expr='grin', look_camera=True, point=None, look=None, squash=True)),
    (END_T, dict(visible=False)),
], words=WORDS)


def shot(t):
    """One continuous 3D take (the cuts are camera moves inside scene3d.js): load + upscale, then the presenter."""
    ov.reset()
    n = min(max(round(t * FPS), 0), round(DUR * FPS) - 1)
    img = ov.upscale(os.path.join(F3D, f'f_{n}.png')).convert('RGBA')
    if P.get('visible', t, True): P.draw(img, t)
    return img.convert('RGB')


def photo(cv, t, t0, t1, x, y, w, rot):
    if not (t0 <= t < t1 + 0.2) or not os.path.isfile(os.path.join(HERE, '..', 'assets', PHOTO + '.jpg')): return
    k = kit.popin(t, t0, 0.3) * kit.popout(t, t1, 0.2)
    ov.place(cv, kit.hq_card(PHOTO, w, PHOTO_LABEL, rot, (0.0, 0.3, 0.4, 1.0)), x, y + 6 * math.sin(t * 2.2), k, 0, 'photo')


def credit_line():
    cr = os.path.join(HERE, '..', 'assets', 'credits.json')
    c = json.load(open(cr)) if os.path.isfile(cr) else []
    return 'Photo: ' + c[0]['attribution'] if c else ''


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.25, HOOK, y=400)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, HOOK, y=400)     # loop: settles back to frame 0
    # beat 1: the hedge stays on screen while it is said
    ov.chip(cv, t, ws(8), T2 - 0.25, 'REPORTEDLY', 250, 640, YEL, 50, rot=-4)
    # beat 2: the deal
    for i, (nm, a) in enumerate((('BMW', 'carL'), ('MERCEDES', 'carM'), ('AUDI', 'carR'))):
        x, y = anchor(a, t)
        ov.chip(cv, t, ws(12 + i) - 0.05, T3 - 0.2, nm, x, 905 - 60 * (i == 1), WHITE, 50)
    ov.chip(cv, t, ws(15) - 0.05, T3 - 0.2, 'NO LAW', 230, 345, RED, 56, rot=-5)
    ov.chip(cv, t, ws(15) + 0.25, T3 - 0.2, 'REPORTEDLY', 660, 335, YEL, 50, rot=4)
    ov.stamp(cv, t, STAMP, T3 - 0.2, ('SECRET', 'DEAL'), 470, 600, rot=-12, scale=0.78)
    # beat 3: the limit
    photo(cv, t, ws(24) + 0.05, T4 - 0.15, 260, 560, 380, -6)
    ov.chip(cv, t, FILL1 - 0.05, T4 - 0.15, '155 MPH LIMIT', 660, 310, RED, 50, rot=3)
    # beat 4: the one that never joined
    ov.chip(cv, t, ws(28) - 0.1, T5 - 0.1, 'PORSCHE', 540, 470, YEL, 60, sub='(REPORTEDLY NEVER JOINED)', rot=-3)
    # beat 5: unlock
    ov.chip(cv, t, T5 + 0.05, T6 - 0.15, "DRIVER'S PACKAGE", 430, 560, YEL, 54, rot=-3)
    ov.chip(cv, t, ws(32) - 0.05, T6 - 0.15, 'SOME MODELS', 520, 360, GRN, 56, rot=3)
    # the poll: small from beat 3, grows big for the question, pops out with the loop whip
    g = io(prog(t, T6 - 0.1, 0.35))
    ov.poll(cv, t, POLL0, DUR - 0.32, 'Remove the limit?', lerp(670, ov.SAFE_CX, g), lerp(985, 860, g), lerp(0.5, 0.97, g))
    if t >= END_T and credit_line(): ov.credit(cv, credit_line(), 1150)


def captions(cv, t): ov.captions(cv, t, 1100)


SHOTS = [(-3.0, shot), (T2, shot), (T3, shot), (T4, shot), (T5, shot), (T6, shot), (END_T, shot)]   # marks for the bar
CUES = [(0.0, 'vroom', 0.7), (0.42, 'whoosh', 0.7), (0.5, 'vroom', 0.5), (SLAM, 'crash', 0.9), (SLAM, 'boom', 0.6),
        (SLAM + 0.02, 'thump', 0.8), (SLAM + 0.05, 'ding', 0.5), (ws(8), 'pop', 0.4), (3.55, 'vroom', 0.4), (3.92, 'thump', 0.6),
        (4.72, 'pop', 0.6), (ws(12), 'pop', 0.5), (ws(13), 'pop', 0.5), (ws(14), 'pop', 0.5), (ws(15), 'buzzer', 0.35),
        (STAMP, 'stamp', 1.0), (STAMP + 0.01, 'boom', 0.4), (7.85, 'whoosh', 0.4)] + [
        (7.85 + 0.035 * k, 'click', 0.25) for k in range(14)] + [
        (FILL1, 'ding', 0.8), (ws(24) + 0.05, 'pop', 0.6), (POLL0, 'pop', 0.7), (ZIP, 'vroom', 0.8), (ZIP + 0.1, 'whoosh', 0.8),
        (T5 + 0.05, 'whoosh', 0.5), (TURN, 'click', 1.0), (TURN + 0.1, 'click', 0.8), (OPEN, 'crash', 0.6), (OPEN + 0.02, 'sparkle', 0.8),
        (OPEN + 0.3, 'vroom', 0.5), (T6, 'pop', 0.7), (END_T, 'whoosh', 0.6)]

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, {}, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=False, loud=True, crisp=True,
          end=False, flash=False, tag='corner')
kit.sway = lambda cv, t: cv                                  # no 2D handheld resample: it would break the 4x pixel grid
kit.series_tag = lambda cv, t: ov.tag(cv)
kit.captions = captions
kit.credit_img = lambda: None                                # credit drawn inside the safe zone by overlay()


def safecheck(step=0.05):
    bad = []
    for i in range(int(DUR / step)):
        kit.frame(round(i * step * FPS))
        bad += [(round(i * step, 2), lab, b) for lab, b in ov.violations()]
    print(f'safe zone {ov.SAFE}: {len(bad)} violations'); [print(*b) for b in bad[:20]]
    return not bad


if __name__ == '__main__':
    if sys.argv[1] == 'frames3d':
        subprocess.run(['node', os.path.join(ROOT, 'shared', 'assets', 'pix3d', 'render3d.mjs'), os.path.join(HERE, 'scene3d.js'), F3D,
                        str(FPS), '0', str(DUR)] + sys.argv[2:], check=True)
    elif sys.argv[1] == 'safecheck':
        raise SystemExit(0 if safecheck() else 1)
    elif sys.argv[1] == 'safestill':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]:
            im = Image.frombytes('RGB', (W, H), kit.frame(round(float(ts) * FPS))).convert('RGBA'); ov.draw_safe(im)
            im.convert('RGB').save(f'{sys.argv[2]}/safe_{ts}.png')
    else:
        kit.main()
