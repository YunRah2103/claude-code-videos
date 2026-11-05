"""Shared render for the ten-episode 'car stuff, explained' series (one look, called once per episode).

Template: videos/red-zone/src/render.py (itself the ac-idle import block, shot structure, captions, progress bar and
mixer via shared/episode.py + assets/dashep.py). An episode supplies three world shots and calls `build`:
    import engine as S
    S.build(HERE, words, hook=..., keycol=..., opening='push-in', focus=(x, y), point=(x, y),
            shots=(open_fn, cut_fn, key_fn), key_sentence=2, poll=('Did you know?', opts, x, y, rot), cues=[...])
Shot functions take t and return an RGBA 1080x1920 world image (props + pills, no presenter); the engine adds the
presenter (assets.explainbits.SPOT, same place in every episode), the opening move, camera, whips, the ask shot with the
recurring RPM gauge, headline, poll, captions, tag, progress bar and the loop back to frame 0.
Beats: open 0 -> T2 (sentence 2), cutaway T2 -> T3 (key sentence), key beat T3 -> T4 (final question), ask T4 -> end.
"""
import math, os, sys
from PIL import Image, ImageChops
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (ROOT, os.path.join(ROOT, 'assets')):
    if p not in sys.path: sys.path.insert(0, p)
import episode as kit
from episode import W, H, FPS
from backdrops.garage import Garage
from pixanim.motion import prog, lerp, io, oc, ob
from pixanim.presenter import Presenter, Fn
from pixanim.grid import up
from pixanim import fx, transitions as T
from assets import overlays as ov, carbits as cb, explainbits as X
import dashep as D

G = Garage(W, H, 1520, 9)
OPENINGS = ('push-in', 'whip-pan', 'pull-back', 'wipe', 'zoom-out', 'tilt', 'slow-motion', 'cut-in', 'drop-in', 'glitch-in')
CFG = {}


def sentences(words):
    """Start index of each sentence in words.json."""
    st = [0]
    for i, w in enumerate(words[:-1]):
        if w['w'][-1] in '.?!': st.append(i + 1)
    return st


def presenter(where, words, point=None, keys=()):
    (x, y), size = X.SPOT[where]
    base = dict(path=Fn(lambda t, x=x, y=y: (x, y)), size=size, legs='stand', ground=None, squash=True, visible=True)
    if point: base.update(arms='point', point=point, look=point, expr='grin')
    else: base.update(arms='shrug', expr='smile', look_camera=True)
    return Presenter([(-9, base)] + list(keys), words=words)


# ------------------------------------------------------------------ opening moves (all already moving on frame 0)
def _glitch(img, t):
    k = 1 - oc(prog(t, -0.05, 0.85))
    if k < 0.02: return img
    r, g, b = img.split(); o = int(46 * k)
    img = Image.merge('RGB', (ImageChops.offset(r, o, 0), g, ImageChops.offset(b, -o, int(6 * k))))
    rnd = __import__('random').Random(int(t * 15))
    for _ in range(int(9 * k) + 1):                                   # torn horizontal slices
        y0 = rnd.randrange(0, H - 120); h = rnd.randrange(30, 160); dx = int(rnd.uniform(-160, 160) * k)
        img.paste(img.crop((0, y0, W, y0 + h)), (dx, y0))
    return img


def opening(kind, world, t, focus, z1=1.06):
    fx_, fy = focus
    if kind == 'push-in':
        return D.camera(world(t), t, lerp(1.0, 1.28, io(prog(t, -0.6, 2.0))), fx_, fy, 10)
    if kind == 'pull-back':
        e = io(prog(t, -0.5, 1.9)); return D.camera(world(t), t, lerp(2.1, z1, e), fx_, lerp(fy - 160, fy, e), 6)
    if kind == 'zoom-out':
        e = ob(prog(t, -0.12, 0.75)); return D.camera(world(t), t, max(1.0, lerp(3.4, z1, e)), fx_, fy, 14 * (1 - e))
    if kind == 'tilt':
        e = io(prog(t, -0.35, 1.4)); return D.camera(world(t), t, 1.32, fx_, lerp(-500, fy, e), 4)
    if kind == 'cut-in':
        z = 1.0 if t < 0.28 else 1.42 if t < 0.56 else lerp(1.8, z1, oc(prog(t, 0.56, 0.8)))
        return D.camera(world(t), t, z, fx_, fy, 16)
    if kind == 'slow-motion':                                         # speed ramp: 0.25x time, snapping to real time
        tw = t if t >= 1.1 else 0.25 * t + 0.825 * oc(prog(t, 0.6, 0.5))
        e = io(prog(t, -0.3, 1.3)); img = world(tw)
        return D.camera(img, t, lerp(1.5, z1, e), lerp(fx_ + 260, fx_, e), lerp(fy + 200, fy, e), 3)
    base = D.camera(world(t), t, z1, fx_, fy, 6)
    if kind == 'whip-pan':
        e = prog(t, -0.16, 0.42)
        return base if e >= 1 else T.whip(G.frame(t).convert('RGB'), base, io(e), dx=1)
    if kind == 'wipe':                                                # yellow diagonal bar sweeps the shot on
        e = io(prog(t, -0.25, 0.85))
        if e >= 1: return base
        bx = lerp(-700, W + 500, e); m = Image.new('L', (W, H), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(m).polygon([(0, 0), (bx + 300, 0), (bx - 300, H), (0, H)], fill=255)
        out = Image.composite(base, G.frame(t).convert('RGB'), m); d = ImageDraw.Draw(out)
        d.polygon([(bx + 300, 0), (bx + 390, 0), (bx - 210, H), (bx - 300, H)], fill=(255, 210, 63))
        d.polygon([(bx + 410, 0), (bx + 440, 0), (bx - 160, H), (bx - 190, H)], fill=(26, 26, 46))
        return out
    if kind == 'drop-in':                                             # the whole shot drops in from above and bounces
        e = prog(t, -0.3, 0.75); dy = -H * (1 - ob(e)) if e < 1 else 0
        if dy > -2:
            return D.camera(world(t), t, z1, fx_, fy, 6 + 30 * math.exp(-max(0, t - 0.45) * 6))
        out = G.frame(t).convert('RGB'); out.paste(base, (0, int(dy))); return out
    if kind == 'glitch-in':
        return _glitch(base, t)
    raise ValueError(kind)


def build(here, words, hook, keycol, opening_kind, focus, point, shots, key_sentence, poll, cues, cut_point=None,
          key_point=None, dur=None, open_keys=(), mid_keys=(), headline_y=430, cut_z=1.06):
    st = sentences(words); ws = lambda i: words[i]['s']
    T2, T3, T4 = ws(st[1]) - 0.12, ws(st[key_sentence]) - 0.12, ws(st[-1]) - 0.15
    DUR = dur or min(15.0, max(14.0, round(words[-1]['e'] + 1.25, 2)))
    END_T = DUR - 0.38
    s_open, s_cut, s_key = shots
    P1 = presenter('open', words, point, open_keys)
    P2 = presenter('mid', words, cut_point or (560, 900), mid_keys)
    P3 = presenter('mid', words, key_point or (560, 900))
    P4 = presenter('ask', words, None, [(ws(st[-1]) + 0.35, dict(arms=('aim', -12), expr='grin', squash=True))])

    def world1(t):
        img = s_open(t); P1.draw(img, t); return img.convert('RGB')

    def shot1(t): return opening(opening_kind, world1, t, focus)

    def mid(fn, P, z0):
        def shot(t):
            img = fn(t); P.draw(img, t)
            return D.camera(img.convert('RGB'), t, lerp(z0 + 0.12, z0, oc(prog(t, CFG['starts'][fn], 0.6))), 560, 960, 5)
        return shot

    def ask(t):
        img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        f = 0.3 + 0.08 * math.sin(t * 3) + 0.04 * math.sin(t * 11)
        fx.blit(fg, up(cb.rpm_gauge(cb.rpm_deg(f), 0), 4), 800, 1440 + 8 * math.sin(t * 2), anchor='center')
        img.alpha_composite(G.rim(fg)); P4.draw(img, t)
        return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T4, 0.6))), 540, 1300, 5)

    CFG['starts'] = {s_cut: T2, s_key: T3}
    scene = D.sequence([(-9, shot1), (T2, mid(s_cut, P2, cut_z)), (T3, mid(s_key, P3, 1.04)), (T4, ask)])
    q, opts, px, py, rot = poll

    def overlay(cv, t):
        ov.headline(cv, t, T2 - 0.25, hook, y=headline_y)
        if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, hook, y=headline_y)
        ov.poll(cv, t, ws(st[-1]) - 0.1, END_T - 0.1, q, px, py, 0.9, opts, rot)

    allcues = [(0.0, 'whoosh', 0.6), (T4 + 0.25, 'pop', 0.8), (ws(st[-1]) + 0.1, 'sparkle', 0.5), (END_T, 'whoosh', 0.6)] + list(cues)
    D.wire(here, words, DUR, END_T, scene, [T2, T3, T4], allcues, keycol, overlay, cap=(T2 - 0.05, 1075), lead=1 / FPS)
    CFG.update(T2=T2, T3=T3, T4=T4, DUR=DUR, END_T=END_T, st=st)
    return CFG
